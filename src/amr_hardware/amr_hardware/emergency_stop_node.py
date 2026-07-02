import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool


class EmergencyStopNode(Node):

    def __init__(self):
        super().__init__('emergency_stop_node')

        self.declare_parameter('stop_distance', 0.25)   # meter — jarak kritis
        self.declare_parameter('warn_distance', 0.45)   # meter — mulai warning
        self.declare_parameter('scan_topic', '/scan')

        self._stop_d = self.get_parameter('stop_distance').value
        self._warn_d = self.get_parameter('warn_distance').value
        scan_topic   = self.get_parameter('scan_topic').value

        self._active = False

        scan_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.create_subscription(LaserScan, scan_topic, self._scan_cb, scan_qos)
        self._cmd_pub   = self.create_publisher(Twist, '/cmd_vel', 10)
        self._estop_pub = self.create_publisher(Bool, '/emergency_stop', 10)

        self.get_logger().info(
            f'emergency_stop_node | stop={self._stop_d}m  warn={self._warn_d}m'
        )

    def _scan_cb(self, msg: LaserScan):
        valid = [r for r in msg.ranges if msg.range_min < r < msg.range_max]
        if not valid:
            return

        min_d = min(valid)
        triggered = min_d < self._stop_d

        if triggered and not self._active:
            self._active = True
            self.get_logger().error(
                f'EMERGENCY STOP — obstacle {min_d:.3f} m  (threshold {self._stop_d} m)'
            )
        elif not triggered and self._active:
            self._active = False
            self.get_logger().warn('Emergency stop cleared')
        elif min_d < self._warn_d and not self._active:
            self.get_logger().warn(f'Obstacle warning: {min_d:.3f} m', throttle_duration_sec=1.0)

        self._estop_pub.publish(Bool(data=triggered))

        if triggered:
            self._cmd_pub.publish(Twist())   # 0, 0 — full stop


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
