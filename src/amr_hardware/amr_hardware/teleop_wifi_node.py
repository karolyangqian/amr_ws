# // teleop_wifi_receiver.py
import socket
import sys
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

BANNER = """\r
=== AMR Wi-Fi Teleop Receiver ===\r
Listening for smartphone controller input...\r
=================================\r
"""

class TeleopWifiNode(Node):

    def __init__(self):
        super().__init__('teleop_wifi_node')

        # Declare parameters for network configuration and speed
        self.declare_parameter('ip', '0.0.0.0')         # 0.0.0.0 listens to all local network interfaces
        self.declare_parameter('port', 5005)           # Choose a port matching your Flutter app
        self.declare_parameter('linear_speed', 0.4)
        self.declare_parameter('angular_speed', 0.3)
        self.declare_parameter('publish_rate', 20.0)

        self.ip            = self.get_parameter('ip').value
        self.port          = self.get_parameter('port').value
        self.linear_speed  = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

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
            # Set a timeout so the loop doesn't block forever when shutting down
            self.sock.settimeout(0.5) 
        except Exception as e:
            self.get_logger().error(f"Failed to bind UDP socket to {self.ip}:{self.port} - {e}")
            sys.exit(1)

        # Run the network listener on a daemon thread
        self._net_thread = threading.Thread(target=self._network_loop, daemon=True)
        self._net_thread.start()

        sys.stdout.write(BANNER)
        self.get_logger().info(f"UDP Server up on {self.ip}:{self.port}")

    def _network_loop(self):
        while self._running:
            try:
                # Expect small string chunks from the phone app
                data, addr = self.sock.recvfrom(64)
                command = data.decode('utf-8').strip().lower()
                self._handle_command(command)
            except socket.timeout:
                # Socket timeout reached with no packet; loop and check if self._running is still True
                continue
            except Exception as e:
                if self._running:
                    self.get_logger().warn(f"Socket read error: {e}")

    def _handle_command(self, cmd):
        with self._lock:
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
        # Emergency safety stop on exit
        stop = Twist()
        node.cmd_pub.publish(stop)
        node._running = False
        node.sock.close()
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()