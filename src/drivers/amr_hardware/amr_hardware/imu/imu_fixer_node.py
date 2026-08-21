import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

# Matriks kovariansi 3x3 (row-major) dengan nilai variansi realistis BNO08x
# Roll & Pitch diberi variansi tinggi (1e6) untuk robot mobile 2D
_COV_ORIENT = [
    1e6, 0.0, 0.0,
    0.0, 1e6, 0.0,
    0.0, 0.0, 0.004   # ~3.6 deg uncertainty untuk Game Rotation Vector
]

_COV_GYRO = [
    1e6, 0.0, 0.0,
    0.0, 1e6, 0.0,
    0.0, 0.0, 0.0003  # Noise density Gyroscope Z BNO08x
]

_COV_ACCEL = [
    0.01, 0.0,  0.0,
    0.0,  0.01, 0.0,
    0.0,  0.0,  1e6   # Sumbu Z tidak digunakan pada navigasi planar 2D
]


class ImuFixerNode(Node):
    def __init__(self):
        super().__init__('imu_fixer_node')

        self.declare_parameter('frame_id', 'imu_link')
        self._frame_id = self.get_parameter('frame_id').value

        self.create_subscription(Imu, '/imu/data', self._imu_cb, 10)
        self._pub = self.create_publisher(Imu, '/imu/data_fixed', 10)

        self.get_logger().info('imu_fixer_node started — /imu/data -> /imu/data_fixed')

    def _imu_cb(self, msg: Imu):
        # 1. Update timestamp & frame
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id

        # 2. Normalisasi Quaternion untuk mencegah error komputasi di EKF
        q = msg.orientation
        norm_sq = q.x**2 + q.y**2 + q.z**2 + q.w**2
        
        if norm_sq > 1e-6:
            norm = math.sqrt(norm_sq)
            msg.orientation.x /= norm
            msg.orientation.y /= norm
            msg.orientation.z /= norm
            msg.orientation.w /= norm
        else:
            # Fallback jika quaternion bernilai invalid/nol
            msg.orientation.x = 0.0
            msg.orientation.y = 0.0
            msg.orientation.z = 0.0
            msg.orientation.w = 1.0

        # 3. Masukkan matriks kovariansi
        msg.orientation_covariance = _COV_ORIENT
        msg.angular_velocity_covariance = _COV_GYRO
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