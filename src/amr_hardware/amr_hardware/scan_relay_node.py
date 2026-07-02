"""
scan_relay_node — jembatan QoS antara LiDAR dan Nav2.

YDLidar publish /scan dengan BEST_EFFORT.
Nav2 costmap subscribe dengan RELIABLE → tidak pernah terima scan → costmap kosong.

Node ini subscribe /scan (BEST_EFFORT) lalu republish ke /scan_reliable (RELIABLE)
sehingga Nav2 bisa terima data LiDAR dengan benar.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from sensor_msgs.msg import LaserScan


QOS_BE = QoSProfile(
    depth=10,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    durability=DurabilityPolicy.VOLATILE,
)

QOS_RE = QoSProfile(
    depth=10,
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    durability=DurabilityPolicy.VOLATILE,
)


class ScanRelayNode(Node):

    def __init__(self):
        super().__init__('scan_relay_node')

        self._pub = self.create_publisher(LaserScan, '/scan_reliable', QOS_RE)
        self.create_subscription(LaserScan, '/scan', self._cb, QOS_BE)

        self.get_logger().info(
            'scan_relay_node aktif: /scan (BEST_EFFORT) → /scan_reliable (RELIABLE)')

    def _cb(self, msg: LaserScan):
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ScanRelayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
