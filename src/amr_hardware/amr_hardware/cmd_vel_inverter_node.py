import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool


class CmdVelInverterNode(Node):
    """
    Menerima perintah Nav2 di /cmd_vel_nav2 (konvensi ROS standar),
    membalik linear.x DAN angular.z (karena Teensy firmware punya konvensi
    terbalik: +linear = mundur, +angular = kanan),
    lalu publish ke /cmd_vel yang disubscribe Teensy.

    Teleop tidak melewati node ini — teleop publish langsung ke /cmd_vel
    dengan konvensi yang sudah disesuaikan.

    Juga menerima /emergency_stop (Bool) — jika True, kirim zero Twist
    untuk menghentikan robot sampai estop dicabut.
    """

    def __init__(self):
        super().__init__('cmd_vel_inverter_node')

        self._estop = False

        self.create_subscription(Twist, '/cmd_vel_nav2',      self._cmd_cb,   10)
        self.create_subscription(Bool,  '/emergency_stop',    self._estop_cb, 10)

        self._pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.get_logger().info(
            'cmd_vel_inverter_node started — '
            '/cmd_vel_nav2 → invert(linear.x, angular.z) → /cmd_vel')

    def _estop_cb(self, msg: Bool):
        self._estop = msg.data
        if self._estop:
            self._pub.publish(Twist())  # kirim zero langsung

    def _cmd_cb(self, msg: Twist):
        out = Twist()
        if self._estop:
            self._pub.publish(out)
            return

        out.linear.x  = msg.linear.x  * -1.0  # koreksi arah linear ZLAC
        out.angular.z = msg.angular.z * -1.0  # koreksi arah putaran ZLAC

        # out.linear.x  = msg.linear.x 
        # out.angular.z = msg.angular.z 


        self._pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelInverterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
