import time
import serial

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu


class ImuSerialNode(Node):
    def __init__(self):
        super().__init__('imu_serial_node')

        self.declare_parameter('port', '/dev/ttyACM1')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('frame_id', 'imu_link')

        port = self.get_parameter('port').get_parameter_value().string_value
        baud = self.get_parameter('baud').get_parameter_value().integer_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value

        self.pub = self.create_publisher(Imu, '/imu/data', 10)

        try:
            self.ser = serial.Serial(port, baudrate=baud, timeout=0.1)
            time.sleep(2.0)
            self.get_logger().info(f'Opened serial port {port} @ {baud}')
        except Exception as e:
            self.get_logger().error(f'Failed to open serial port {port}: {e}')
            raise

        self.timer = self.create_timer(0.01, self.timer_callback)

    def timer_callback(self):
        try:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                return

            parts = line.split()
            if len(parts) != 6:
                return

            ax, ay, az, gx, gy, gz = map(float, parts)

            msg = Imu()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id

            msg.linear_acceleration.x = ax
            msg.linear_acceleration.y = ay
            msg.linear_acceleration.z = az

            msg.angular_velocity.x = gx
            msg.angular_velocity.y = gy
            msg.angular_velocity.z = gz

            msg.orientation.x = 0.0
            msg.orientation.y = 0.0
            msg.orientation.z = 0.0
            msg.orientation.w = 1.0

            msg.orientation_covariance[0] = -1.0

            msg.angular_velocity_covariance[0] = 0.004
            msg.angular_velocity_covariance[4] = 0.004
            msg.angular_velocity_covariance[8] = 0.004

            msg.linear_acceleration_covariance[0] = 0.1
            msg.linear_acceleration_covariance[4] = 0.1
            msg.linear_acceleration_covariance[8] = 0.1

            self.pub.publish(msg)

        except Exception as e:
            self.get_logger().warn(f'Error reading/parsing serial: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = ImuSerialNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()