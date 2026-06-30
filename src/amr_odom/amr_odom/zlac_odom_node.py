import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

from amr_hardware.zlac8015d.ZLAC8015D import Controller as ZLACController


class ZlacOdomNode(Node):

    def __init__(self):
        super().__init__('zlac_odom_node')

        self.declare_parameter('port', '/dev/ttyUSB2')
        self.declare_parameter('wheel_radius', 0.105)
        self.declare_parameter('wheel_separation', 0.58)
        self.declare_parameter('cpr', 16385)
        self.declare_parameter('odom_frame',  'odom')
        self.declare_parameter('base_frame',  'base_link')
        self.declare_parameter('publish_tf',  True)

        port            = self.get_parameter('port').value
        self.R          = self.get_parameter('wheel_radius').value
        self.b          = self.get_parameter('wheel_separation').value
        self.cpr        = self.get_parameter('cpr').value
        self.odom_frame  = self.get_parameter('odom_frame').value
        self.base_frame  = self.get_parameter('base_frame').value
        self.publish_tf_ = self.get_parameter('publish_tf').value

        self.zlac = ZLACController(port=port)

        l0, r0 = self.zlac.get_wheels_tick()
        self.last_tick_L = int(l0)
        self.last_tick_R = int(r0)
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0
        self.last_time = self.get_clock().now()

        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.create_timer(0.02, self.timer_callback)
        self.get_logger().info('zlac_odom_node started')

    def timer_callback(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        if dt <= 0.0:
            return
        self.last_time = now

        try:
            tick_L, tick_R = self.zlac.get_wheels_tick()
        except Exception as e:
            self.get_logger().warn(f'get_wheels_tick failed: {e}')
            return

        tick_L = int(tick_L)
        tick_R = int(tick_R)

        delta_L = tick_L - self.last_tick_L
        delta_R = tick_R - self.last_tick_R
        self.last_tick_L = tick_L
        self.last_tick_R = tick_R

        # Ticks → meter, koreksi sign:
        # maju = L_cmd negatif (L ticks turun), R_cmd positif (R ticks naik)
        m_per_tick = (2.0 * math.pi * self.R) / self.cpr
        dist_L = -delta_L * m_per_tick
        dist_R =  delta_R * m_per_tick

        # Kinematika differential drive
        delta_s     = (dist_L + dist_R) * 0.5
        delta_theta = (dist_R - dist_L) / self.b

        # Integrasi pose (metode midpoint / RK2)
        theta_mid  = self.theta + delta_theta * 0.5
        self.x    += delta_s * math.cos(theta_mid)
        self.y    += delta_s * math.sin(theta_mid)
        self.theta = theta_mid + delta_theta * 0.5

        # Kecepatan sesaat
        v = delta_s / dt
        w = delta_theta / dt

        # Quaternion dari yaw
        q_z = math.sin(self.theta * 0.5)
        q_w = math.cos(self.theta * 0.5)

        # --- Publish TF odom → base_link ---
        t = TransformStamped()
        t.header.stamp        = now.to_msg()
        t.header.frame_id     = self.odom_frame
        t.child_frame_id      = self.base_frame
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.x    = 0.0
        t.transform.rotation.y    = 0.0
        t.transform.rotation.z    = q_z
        t.transform.rotation.w    = q_w
        if self.publish_tf_:
            self.tf_broadcaster.sendTransform(t)

        # --- Publish /odom ---
        odom = Odometry()
        odom.header.stamp    = now.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id  = self.base_frame

        odom.pose.pose.position.x    = self.x
        odom.pose.pose.position.y    = self.y
        odom.pose.pose.position.z    = 0.0
        odom.pose.pose.orientation.x = 0.0
        odom.pose.pose.orientation.y = 0.0
        odom.pose.pose.orientation.z = q_z
        odom.pose.pose.orientation.w = q_w

        # Covariance diagonal (6x6, row-major): x, y, z, roll, pitch, yaw
        odom.pose.covariance[0]  = 0.01   # x
        odom.pose.covariance[7]  = 0.01   # y
        odom.pose.covariance[14] = 1e9    # z  (tidak relevan 2D)
        odom.pose.covariance[21] = 1e9    # roll
        odom.pose.covariance[28] = 1e9    # pitch
        odom.pose.covariance[35] = 0.01   # yaw

        odom.twist.twist.linear.x  = v
        odom.twist.twist.angular.z = w

        odom.twist.covariance[0]  = 0.01  # vx
        odom.twist.covariance[7]  = 1e9   # vy (diff drive, selalu ~0)
        odom.twist.covariance[14] = 1e9   # vz
        odom.twist.covariance[21] = 1e9   # wx
        odom.twist.covariance[28] = 1e9   # wy
        odom.twist.covariance[35] = 0.01  # wz

        self.odom_pub.publish(odom)


def main(args=None):
    rclpy.init(args=args)
    node = ZlacOdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
