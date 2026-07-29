# // emergency_stop_node.py
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool
from amr_msgs.msg import RobotStatus  # Mengimpor pesan status untuk memperbarui mode sistem

import os
import subprocess
import threading
import time

class EmergencyStopNode(Node):

    def __init__(self):
        super().__init__('emergency_stop_node')

        self.declare_parameter('stop_distance', 0.25)   # meter — jarak kritis
        self.declare_parameter('warn_distance', 0.45)   # meter — mulai warning
        self.declare_parameter('scan_topic', '/scan_reliable')

        self._stop_d = self.get_parameter('stop_distance').value
        self._warn_d = self.get_parameter('warn_distance').value
        scan_topic   = self.get_parameter('scan_topic').value

        self._active = False
        
        # --- STATE WATCHDOG MONITOR ---
        self._last_scan_time = self.get_clock().now()
        self._lidar_timeout_threshold = 0.5  # Deteksi putus jika > 0.5 detik tanpa data
        self._running = True

        # QoS Profile
        scan_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        
        # Subscriptions & Publishers
        self.create_subscription(LaserScan, scan_topic, self._scan_cb, scan_qos)
        self._cmd_pub   = self.create_publisher(Twist, '/cmd_vel', 10)
        self._estop_pub = self.create_publisher(Bool, '/emergency_stop', 10)
        self._robot_status_pub = self.create_publisher(RobotStatus, '/robot/status', 10)

        self.get_logger().info(
            f'emergency_stop_node | stop={self._stop_d}m  warn={self._warn_d}m | Watchdog Aktif (60Hz)'
        )

        # turn on for doing health check loop and trigger_estop
        # --- RUN 60 HZ HEALTH CHECK ON BACKGROUND THREAD ---
        # self._watchdog_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        # self._watchdog_thread.start()

    def _scan_cb(self, msg: LaserScan):
        # Update timestamp deteksi masuk ke sensor watchdog
        self._last_scan_time = self.get_clock().now()

        valid = [r for r in msg.ranges if msg.range_min < r < msg.range_max]
        if not valid:
            return

        min_d = min(valid)
        triggered = min_d < self._stop_d

        if triggered and not self._active:
            # self._trigger_estop(f"Obstacle detected closer than threshold: {min_d:.3f} m")
            pass
        elif not triggered and self._active:
            # Tetap biarkan dilepaskan secara aman jika sensor mendeteksi jalur sudah clear
            pass
        elif min_d < self._warn_d and not self._active:
            self.get_logger().warn(f'Obstacle warning: {min_d:.3f} m', throttle_duration_sec=1.0)

        if triggered:
            self._cmd_pub.publish(Twist())   # 0, 0 — full stop

    def _trigger_estop(self, reason_msg, error_code=RobotStatus.ERROR_NONE):
        """Memaksa sistem memasuki mode Emergency Stop secara instan"""
        self._active = True
        self.get_logger().error(f"🚨 [WATCHDOG ESTOP]: {reason_msg}")
        
        # Kirim sinyal estop
        self._estop_pub.publish(Bool(data=True))
        self._cmd_pub.publish(Twist()) # Force Stop

        # Publish status robot ke sistem
        status = RobotStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.mode = RobotStatus.MODE_EMERGENCY
        status.error_code = error_code
        status.status_message = f"ESTOP: {reason_msg}"
        self._robot_status_pub.publish(status)

    def _health_check_loop(self):
        """Loop eksekusi 60Hz untuk memonitor integritas hardware dan sistem OS"""
        rate = 60.0
        interval = 1.0 / rate

        while self._running and rclpy.ok():
            start_time = time.time()
            
            # --- 1. MONITOR TIMEOUT LASERSCAN (LiDAR Check) ---
            time_since_last_scan = (self.get_clock().now() - self._last_scan_time).nanoseconds / 1e9
            if time_since_last_scan > self._lidar_timeout_threshold:
                self._trigger_estop(
                    f"LiDAR data stream frozen/lost for {time_since_last_scan:.2f}s!", 
                    RobotStatus.ERROR_LIDAR
                )

            # --- 2. MONITOR KONEKSI VITAL PERIPHERAL USB PATHS ---
            # Meniru mekanika runtime preflight_check.sh
            vital_ports = ['/dev/ttyUSB0'] # Lidar & Motor Drivers
            for port in vital_ports:
                if not os.path.exists(port):
                    self._trigger_estop(
                        f"Hardware link missing: {port} disconnected!", 
                        RobotStatus.ERROR_MOTOR if "USB2" in port else RobotStatus.ERROR_LIDAR
                    )

            # --- 3. MONITOR INTEGRITAS ROS WORKSPACE ENVIRONMENT ---
            if "ROS_DISTRO" not in os.environ:
                self._trigger_estop("ROS Environment variable un-sourced!", RobotStatus.ERROR_NONE)

            # Penyeimbang jeda loop agar berjalan presisi mendekati target frekuensi 60Hz
            elapsed = time.time() - start_time
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def destroy_node(self):
        self._running = False
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = EmergencyStopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()