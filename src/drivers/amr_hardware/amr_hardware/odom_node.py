import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster


class OdomNode(Node):
    """
    Dead-reckoning odom dari /cmd_vel_raw saja.
    Tidak butuh IMU, tidak butuh encoder.
    Publish /odom + TF odom -> base_footprint @ 50 Hz.
    """

    def __init__(self):
        super().__init__('odom_node')

        self.declare_parameter('publish_tf',  True)
        self.declare_parameter('odom_frame',  'odom')
        self.declare_parameter('base_frame',  'base_footprint')
        # parameter lama — dibiarkan agar launch file existing tidak error
        self.declare_parameter('wheel_base',  0.445)
        self.declare_parameter('wheel_circ',  0.359)

        self.pub_tf = self.get_parameter('publish_tf').value
        self.oframe = self.get_parameter('odom_frame').value
        self.bframe = self.get_parameter('base_frame').value

        self.x  = 0.0
        self.y  = 0.0
        self.th = 0.0

        self._vx = 0.0
        self._wz = 0.0
        self._last_time = self.get_clock().now()

        self.odom_pub       = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.create_subscription(Twist, '/cmd_vel_raw', self._cmd_cb, 10)
        self.create_subscription(Twist, '/cmd_vel',     self._cmd_cb, 10)

        # Timer 50 Hz — publish terus meskipun belum ada cmd (default 0)
        self.create_timer(0.02, self._timer_cb)

        self.get_logger().info(
            f'odom_node aktif — dead reckoning /cmd_vel_raw + /cmd_vel → '
            f'TF {self.oframe} -> {self.bframe}, publish_tf={self.pub_tf}')

    def _cmd_cb(self, msg: Twist):
        self._vx = msg.linear.x
        self._wz = msg.angular.z

    def _timer_cb(self):
        now  = self.get_clock().now()
        dt   = (now.nanoseconds - self._last_time.nanoseconds) / 1e9
        self._last_time = now

        if dt <= 0.0 or dt > 1.0:
            return

        vx = self._vx
        wz = self._wz

        self.th += wz * dt
        self.x  += vx * math.cos(self.th) * dt
        self.y  += vx * math.sin(self.th) * dt

        qz = math.sin(self.th * 0.5)
        qw = math.cos(self.th * 0.5)

        odom = Odometry()
        odom.header.stamp            = now.to_msg()
        odom.header.frame_id         = self.oframe
        odom.child_frame_id          = self.bframe
        odom.pose.pose.position.x    = self.x
        odom.pose.pose.position.y    = self.y
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        # Covariance besar — ini dead reckoning, bukan sensor fusion
        odom.pose.covariance[0]      = 0.5   # x
        odom.pose.covariance[7]      = 0.5   # y
        odom.pose.covariance[35]     = 0.3   # yaw
        odom.twist.twist.linear.x    = vx
        odom.twist.twist.angular.z   = wz
        odom.twist.covariance[0]     = 0.3
        odom.twist.covariance[35]    = 0.3
        self.odom_pub.publish(odom)

        if self.pub_tf:
            t = TransformStamped()
            t.header.stamp             = now.to_msg()
            t.header.frame_id          = self.oframe
            t.child_frame_id           = self.bframe
            t.transform.translation.x  = self.x
            t.transform.translation.y  = self.y
            t.transform.rotation.z     = qz
            t.transform.rotation.w     = qw
            self.tf_broadcaster.sendTransform(t)


def main(args=None):
    rclpy.init(args=args)
    node = OdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
