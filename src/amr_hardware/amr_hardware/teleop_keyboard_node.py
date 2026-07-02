import select
import sys
import termios
import tty
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


BANNER = """\r
=== AMR Teleop Keyboard ===\r
  W : Maju       S : Mundur\r
  A : Kiri       D : Kanan\r
  SPACE : Stop   Q / Ctrl+C : Keluar\r
  I : Linear +   K : Linear -\r
  J : Angular +  L : Angular -\r
===========================\r
"""

LINEAR_MIN  = 0.05
LINEAR_MAX  = 1.0
LINEAR_STEP = 0.05

ANGULAR_MIN  = 0.1
ANGULAR_MAX  = 2.0
ANGULAR_STEP = 0.1


class TeleopKeyboardNode(Node):

    def __init__(self):
        super().__init__('teleop_keyboard_node')

        self.declare_parameter('linear_speed',  0.3)
        self.declare_parameter('angular_speed', 0.2)
        self.declare_parameter('publish_rate',  20.0)

        self.linear_speed  = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self._lin     = 0.0
        self._ang     = 0.0
        self._lock    = threading.Lock()
        self._running = True

        rate = self.get_parameter('publish_rate').value
        self.create_timer(1.0 / rate, self._publish_cmd)

        self._kbd_thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        self._kbd_thread.start()

        sys.stdout.write(BANNER)
        self._print_speeds()

    def _print_speeds(self):
        sys.stdout.write(
            f'\rLinear: {self.linear_speed:.2f} m/s  '
            f'Angular: {self.angular_speed:.2f} rad/s        \r\n'
        )
        sys.stdout.flush()

    def _keyboard_loop(self):
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while self._running:
                ready = select.select([sys.stdin], [], [], 0.1)[0]
                if ready:
                    ch = sys.stdin.read(1).lower()
                    self._handle_key(ch)
                else:
                    with self._lock:
                        self._lin = 0.0
                        self._ang = 0.0
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def _handle_key(self, ch):
        with self._lock:
            if ch == 'w':
                self._lin = -self.linear_speed
                self._ang =  0.0
                sys.stdout.write('\r[MAJU]      \r')
            elif ch == 's':
                self._lin =  self.linear_speed
                self._ang =  0.0
                sys.stdout.write('\r[MUNDUR]    \r')
            elif ch == 'a':
                self._lin =  0.0
                self._ang = -self.angular_speed
                sys.stdout.write('\r[KIRI]      \r')
            elif ch == 'd':
                self._lin =  0.0
                self._ang =  self.angular_speed
                sys.stdout.write('\r[KANAN]     \r')
            elif ch == ' ':
                self._lin =  0.0
                self._ang =  0.0
                sys.stdout.write('\r[STOP]      \r')
            elif ch == 'i':
                self.linear_speed = min(self.linear_speed + LINEAR_STEP, LINEAR_MAX)
                sys.stdout.write(
                    f'\rLinear: {self.linear_speed:.2f} m/s  '
                    f'Angular: {self.angular_speed:.2f} rad/s        \r')
            elif ch == 'k':
                self.linear_speed = max(self.linear_speed - LINEAR_STEP, LINEAR_MIN)
                sys.stdout.write(
                    f'\rLinear: {self.linear_speed:.2f} m/s  '
                    f'Angular: {self.angular_speed:.2f} rad/s        \r')
            elif ch == 'j':
                self.angular_speed = min(self.angular_speed + ANGULAR_STEP, ANGULAR_MAX)
                sys.stdout.write(
                    f'\rLinear: {self.linear_speed:.2f} m/s  '
                    f'Angular: {self.angular_speed:.2f} rad/s        \r')
            elif ch == 'l':
                self.angular_speed = max(self.angular_speed - ANGULAR_STEP, ANGULAR_MIN)
                sys.stdout.write(
                    f'\rLinear: {self.linear_speed:.2f} m/s  '
                    f'Angular: {self.angular_speed:.2f} rad/s        \r')
            elif ch in ('q', '\x03'):
                self._lin =  0.0
                self._ang =  0.0
                self._running = False
                sys.stdout.write('\r[KELUAR]    \r\n')
            sys.stdout.flush()

    def _publish_cmd(self):
        with self._lock:
            lin = self._lin
            ang = self._ang

        msg = Twist()
        msg.linear.x  = lin
        msg.angular.z = ang
        self.cmd_pub.publish(msg)

        if not self._running:
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = TeleopKeyboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        stop = Twist()
        node.cmd_pub.publish(stop)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
