import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu


# BNO08x covariance per sensor type (diagonal 3x3, row-major):
# - Orientasi (SH2_ROTATION_VECTOR fusion): sangat akurat, yaw sedikit lebih noisy
#   karena magnetometer bisa terpengaruh motor/logam di sekitar robot
# - Gyro (SH2_GYROSCOPE_CALIBRATED): akurat, noise kecil
# - Linear accel (SH2_LINEAR_ACCELERATION): lebih noisy, dipakai hanya sebagai koreksi
_COV_ORIENT = [
    1e-5, 0.0,  0.0,
    0.0,  1e-5, 0.0,
    0.0,  0.0,  1e-4,   # yaw sedikit lebih longgar (mag interference dari motor)
]
_COV_GYRO = [
    1e-5, 0.0,  0.0,
    0.0,  1e-5, 0.0,
    0.0,  0.0,  1e-5,
]
_COV_ACCEL = [
    5e-3, 0.0,  0.0,
    0.0,  5e-3, 0.0,
    0.0,  0.0,  5e-3,   # lebih noisy — EKF tidak over-trust linear accel
]


class ImuFixerNode(Node):
    """
    Menerima /imu/data dari Teensy (micro-ROS, tanpa timestamp & covariance),
    menambahkan timestamp PC + covariance, lalu re-publish ke /imu/data_fixed
    agar dapat dikonsumsi oleh robot_localization EKF.
    """

    def __init__(self):
        super().__init__('imu_fixer_node')

        self.declare_parameter('frame_id', 'imu_link')
        self._frame_id = self.get_parameter('frame_id').value

        self.create_subscription(Imu, '/imu/data', self._imu_cb, 10)
        self._pub = self.create_publisher(Imu, '/imu/data_fixed', 10)

        self.get_logger().info('imu_fixer_node started — /imu/data → /imu/data_fixed')

    def _imu_cb(self, msg: Imu):
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id

        # Normalisasi quaternion — mencegah TF_DENORMALIZED_QUATERNION dan EKF NaN
        q = msg.orientation
        norm = math.sqrt(q.x**2 + q.y**2 + q.z**2 + q.w**2)
        if norm > 1e-6:
            msg.orientation.x /= norm
            msg.orientation.y /= norm
            msg.orientation.z /= norm
            msg.orientation.w /= norm
        else:
            msg.orientation.x = 0.0
            msg.orientation.y = 0.0
            msg.orientation.z = 0.0
            msg.orientation.w = 1.0

        msg.orientation_covariance         = _COV_ORIENT
        msg.angular_velocity_covariance    = _COV_GYRO
        msg.linear_acceleration_covariance = _COV_ACCEL

        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ImuFixerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
