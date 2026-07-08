# // teleop_wifi_node.py
import socket
import sys
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

BANNER = """\r
=== AMR Wi-Fi Teleop Receiver ===\r
Listening for smartphone controller input...\r
\r
[ESTOP OVERRIDE]:\r
  Send "~" from your app to reset manual lock after E-Stop clears.\r
=================================\r
"""

class TeleopWifiNode(Node):

    def __init__(self):
        super().__init__('teleop_wifi_node')

        # Declare parameters for network configuration and speed
        self.declare_parameter('ip', '0.0.0.0')         
        self.declare_parameter('port', 5005)           
        self.declare_parameter('linear_speed', 0.3)
        self.declare_parameter('angular_speed', 0.4)
        self.declare_parameter('publish_rate', 20.0)

        self.ip            = self.get_parameter('ip').value
        self.port          = self.get_parameter('port').value
        self.linear_speed  = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value

        # --- STATE LOCK UNTUK EMERGENCY ---
        self._estop_active = False  # Status langsung dari topik /emergency_stop
        self._user_locked  = False  # Status penguncian input kontrol smartphone

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Subscribe ke status emergency stop
        self.create_subscription(Bool, '/emergency_stop', self._estop_cb, 10)

        self._lin     = 0.0
        self._ang     = 0.0
        self._lock    = threading.Lock()
        self._running = True

        # Timer matching your exact message dispatch rate
        rate = self.get_parameter('publish_rate').value
        self.create_timer(1.0 / rate, self._publish_cmd)

        # Set up the UDP Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((self.ip, self.port))
            self.sock.settimeout(0.5) 
        except Exception as e:
            self.get_logger().error(f"Failed to bind UDP socket to {self.ip}:{self.port} - {e}")
            sys.exit(1)

        # Run the network listener on a daemon thread
        self._net_thread = threading.Thread(target=self._network_loop, daemon=True)
        self._net_thread.start()

        sys.stdout.write(BANNER)
        self.get_logger().info(f"UDP Server up on {self.ip}:{self.port}")

    def _estop_cb(self, msg: Bool):
        with self._lock:
            self._estop_active = msg.data
            # Jika E-stop aktif, otomatis kunci input pengguna
            if self._estop_active and not self._user_locked:
                self._user_locked = True
                self._lin = 0.0
                self._ang = 0.0
                sys.stdout.write('\r[🚨 ESTOP ACTIVE - WIFI TELEOP LOCKED]               \r')
                sys.stdout.flush()

    def _network_loop(self):
        while self._running:
            try:
                data, addr = self.sock.recvfrom(64)
                command = data.decode('utf-8').strip().lower()
                self._handle_command(command)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self.get_logger().warn(f"Socket read error: {e}")

    def _handle_command(self, cmd):
        with self._lock:
            # --- MEKANISME RECOVERY / UNLOCK ---
            if cmd == '~':
                if self._estop_active:
                    sys.stdout.write('\r[⚠️ GAGAL] Sensor masih mendeteksi bahaya! Tidak bisa unlock. \r')
                elif self._user_locked:
                    self._user_locked = False
                    sys.stdout.write('\r[✅ UNLOCKED] Wi-Fi teleop aktif kembali.                 \r')
                else:
                    sys.stdout.write('\r[INFO] Wi-Fi teleop sudah dalam kondisi bebas kunci.         \r')
                sys.stdout.flush()
                return

            # --- JIKA TERKUNCI, ABAIKAN INPUT GERAKAN DI BAWAH INI ---
            if self._user_locked:
                if cmd in ('w', 'a', 's', 'd', 'o', 'p', 'm', 'n'):
                    sys.stdout.write('\r[🔒 LOCKED] Kirim `~` untuk unlock (Pastikan E-stop Clear)  \r')
                    sys.stdout.flush()
                return

            # --- CARDINAL DIRECTIONS ---
            if cmd == 'w':    # Forward
                self._lin = self.linear_speed
                self._ang = 0.0
            elif cmd == 's':  # Backward
                self._lin = -self.linear_speed
                self._ang = 0.0
            elif cmd == 'a':  # Turn Left Pivot
                self._lin = 0.0
                self._ang = self.angular_speed
            elif cmd == 'd':  # Turn Right Pivot
                self._lin = 0.0
                self._ang = -self.angular_speed

            # --- DIAGONAL MECHANICS ---
            elif cmd == 'o':  # Forward-Left Diagonal
                self._lin = self.linear_speed
                self._ang = self.angular_speed
            elif cmd == 'p':  # Forward-Right Diagonal
                self._lin = self.linear_speed
                self._ang = -self.angular_speed
            elif cmd == 'm':  # Backward-Left Diagonal
                self._lin = -self.linear_speed
                self._ang = self.angular_speed
            elif cmd == 'n':  # Backward-Right Diagonal
                self._lin = -self.linear_speed
                self._ang = -self.angular_speed

            # --- STOP MECHANIC ---
            elif cmd in ('stop', ' '):
                self._lin = 0.0
                self._ang = 0.0
                
            # --- STATUS DUMP ON TERMINAL ---
            sys.stdout.write(f'\r[CMD Recv: {cmd.upper()}] Lin: {self._lin:.2f} Ang: {self._ang:.2f}      \r')
            sys.stdout.flush()

    def _publish_cmd(self):
        with self._lock:
            # Proteksi lapis kedua: paksa data ke nol jika interlock aktif
            if self._user_locked or self._estop_active:
                lin = 0.0
                ang = 0.0
            else:
                lin = self._lin
                ang = self._ang

        msg = Twist()
        msg.linear.x  = lin
        msg.angular.z = ang
        self.cmd_pub.publish(msg)

        if not self._running:
            self.sock.close()
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = TeleopWifiNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stop = Twist()
        node.cmd_pub.publish(stop)
        node._running = False
        node.sock.close()
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()