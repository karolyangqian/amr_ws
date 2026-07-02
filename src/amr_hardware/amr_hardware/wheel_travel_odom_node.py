import math

from amr_msgs import msg
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

# Firmware mengirim CUMULATIVE distance sejak boot (bukan delta per pesan).
# Node ini menghitung selisih antar pesan untuk mendapat delta yang benar.
# Guard: abaikan jika delta antar pesan > MAX (misal saat Teensy reboot → spike negatif besar)
_MAX_DELTA_M = 0.5


class WheelTravelOdomNode(Node):

    def __init__(self):
        super().__init__('wheel_travel_odom_node')

        self.declare_parameter('wheel_separation', 0.445)
        self.declare_parameter('odom_frame',       'odom')
        self.declare_parameter('base_frame',       'base_footprint')
        self.declare_parameter('publish_tf',       True)

        self.wheel_sep   = self.get_parameter('wheel_separation').value
        self.odom_frame  = self.get_parameter('odom_frame').value
        self.base_frame  = self.get_parameter('base_frame').value
        self.publish_tf_ = self.get_parameter('publish_tf').value

        # Pose
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0

        # Cumulative dari pesan sebelumnya (None = belum ada pesan)
        self.prev_l = None
        self.prev_r = None

        self.last_time = self.get_clock().now()

        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)

        if self.publish_tf_:
            self.tf_broadcaster = TransformBroadcaster(self)
            self.create_timer(0.05, self._tf_timer_cb)  # 20 Hz

        self.create_subscription(Float32MultiArray, '/wheel_travel', self._cb, 10)
        self.get_logger().info(
            f'wheel_travel_odom_node started (cumulative mode) | '
            f'wheel_sep={self.wheel_sep} m | publish_tf={self.publish_tf_}')

    # ── TF timer: publish TF terus-menerus 20 Hz ────────────────────────────
    def _tf_timer_cb(self):
        self._broadcast_tf(self.get_clock().now())

    def _broadcast_tf(self, stamp):
        q_z = math.sin(self.theta / 2.0)
        q_w = math.cos(self.theta / 2.0)
        t = TransformStamped()
        t.header.stamp            = stamp.to_msg()
        t.header.frame_id         = self.odom_frame
        t.child_frame_id          = self.base_frame
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.z    = q_z
        t.transform.rotation.w    = q_w
        self.tf_broadcaster.sendTransform(t)

    # ── Callback: hitung delta dari cumulative ───────────────────────────────
    def _cb(self, msg: Float32MultiArray):
        if len(msg.data) < 2:
            return

        # data[0]=roda kanan, data[1]=roda kiri (firmware)
        # Fix 1: roda kiri sign inverted di firmware dead-reckoning
        # Fix 2: scale ×10 (ZLAC CMD = direct RPM, bukan ×0.1 RPM)
        # curr_l = float(msg.data[0]) * 10.0
        # curr_r = -float(msg.data[1]) * 10.0

        LINEAR_SCALE = 0.955

        # curr_r = float(msg.data[0]) * LINEAR_SCALE
        # curr_l = float(msg.data[1]) * LINEAR_SCALE

        curr_r = -float(msg.data[0]) * LINEAR_SCALE
        curr_l = -float(msg.data[1]) * LINEAR_SCALE

        # Pesan pertama: simpan sebagai baseline, jangan integrasikan
        if self.prev_l is None:
            self.prev_l = curr_l
            self.prev_r = curr_r
            self.get_logger().info(
                f'First /wheel_travel received: L={curr_l:.4f} R={curr_r:.4f} (baseline set)')
            return

        delta_l = curr_l - self.prev_l
        delta_r = curr_r - self.prev_r

        self.get_logger().info(
            f"dL={delta_l:.4f}, dR={delta_r:.4f}",
            throttle_duration_sec=0.2
        )
        self.prev_l = curr_l
        self.prev_r = curr_r

        # Guard: buang spike besar (Teensy reboot, noise, overflow)
        if (math.isnan(delta_l) or math.isnan(delta_r) or
                math.isinf(delta_l) or math.isinf(delta_r) or
                abs(delta_l) > _MAX_DELTA_M or abs(delta_r) > _MAX_DELTA_M):
            self.get_logger().warn(
                f'Delta terlalu besar, dibuang: dL={delta_l:.4f} dR={delta_r:.4f}',
                throttle_duration_sec=2.0)
            return

        now = self.get_clock().now()
        dt  = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        delta_s     = (delta_l + delta_r) / 2.0
        # delta_theta = (delta_r - delta_l) / self.wheel_sep  # data[0]=roda kanan fisik, data[1]=kiri
        delta_theta = (delta_l - delta_r) / self.wheel_sep
        theta_mid   = self.theta + delta_theta / 2.0

        self.x     += delta_s * math.cos(theta_mid)
        self.y     += delta_s * math.sin(theta_mid)
        self.theta += delta_theta

        v = delta_s / dt if dt > 0.001 else 0.0
        w = delta_theta / dt if dt > 0.001 else 0.0

        q_z = math.sin(self.theta / 2.0)
        q_w = math.cos(self.theta / 2.0)

        odom = Odometry()
        odom.header.stamp            = now.to_msg()
        odom.header.frame_id         = self.odom_frame
        odom.child_frame_id          = self.base_frame
        odom.pose.pose.position.x    = self.x
        odom.pose.pose.position.y    = self.y
        odom.pose.pose.orientation.z = q_z
        odom.pose.pose.orientation.w = q_w
        odom.pose.covariance[0]  = 0.01
        odom.pose.covariance[7]  = 0.01
        odom.pose.covariance[14] = 1e9
        odom.pose.covariance[21] = 1e9
        odom.pose.covariance[28] = 1e9
        odom.pose.covariance[35] = 0.05
        odom.twist.twist.linear.x  = v
        odom.twist.twist.angular.z = w
        odom.twist.covariance[0]  = 0.01
        odom.twist.covariance[35] = 0.05
        self.odom_pub.publish(odom)


def main(args=None):
    rclpy.init(args=args)
    node = WheelTravelOdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
