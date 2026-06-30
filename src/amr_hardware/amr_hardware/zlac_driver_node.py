"""
zlac_driver_node — motor control via NUC USB-RS485 (PL2303 / amr_motor).

Write-only path: hanya kirim RPM, tidak baca encoder (adapter DE hardwired HIGH).
Odom ditangani odom_node (dead reckoning dari /cmd_vel_raw).

Subscribe : /cmd_vel_raw     (geometry_msgs/Twist)
            /emergency_stop  (std_msgs/Bool)
"""

import signal
import threading
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

from amr_hardware.zlac8015d.ZLAC8015D import Controller as ZLACController

# Empirical dari teleop_keyboard.py: set_rpm(-50,+50) berhasil gerak ~0.5 m/s
# → LINEAR_TO_RPM = 50 / 0.5 = 100 register_units per m/s
LINEAR_TO_RPM = 100.0
WHEEL_SEP     = 0.445   # m — jarak antar roda


class ZlacDriverNode(Node):

    def __init__(self):
        super().__init__('zlac_driver_node')

        self.declare_parameter('port',           '/dev/amr_motor')
        self.declare_parameter('accel_time_ms',   200)
        self.declare_parameter('decel_time_ms',   200)
        self.declare_parameter('cmd_vel_timeout',  0.25)
        self.declare_parameter('max_reg',          250)

        port          = self.get_parameter('port').value
        accel_ms      = self.get_parameter('accel_time_ms').value
        decel_ms      = self.get_parameter('decel_time_ms').value
        self._timeout = self.get_parameter('cmd_vel_timeout').value
        self._max_reg = self.get_parameter('max_reg').value

        self.get_logger().info(f'Connecting ZLAC on {port} …')
        try:
            self.zlac = ZLACController(port=port)
            self.zlac.clear_alarm()
            time.sleep(0.3)
            self.zlac.set_accel_time(accel_ms, accel_ms)
            self.zlac.set_decel_time(decel_ms, decel_ms)
            self.zlac.set_mode(3)
            time.sleep(0.2)
            self.zlac.enable_motor()
            time.sleep(0.2)
            self.get_logger().info('ZLAC ready: ALRM_CLR → MODE=3 → ENABLE')
        except Exception as e:
            self.get_logger().error(f'ZLAC init failed: {e}')
            raise

        self._vx       = 0.0
        self._wz       = 0.0
        self._last_cmd = self.get_clock().now()
        self._estop    = False
        self._stopped  = True

        self.create_subscription(Twist, '/cmd_vel_raw',    self._cmd_cb,   10)
        self.create_subscription(Twist, '/cmd_vel',        self._cmd_cb,   10)
        self.create_subscription(Bool,  '/emergency_stop', self._estop_cb, 10)
        self.create_timer(0.05, self._timer_cb)  # 20 Hz

        self.get_logger().info(
            f'zlac_driver_node aktif | port={port} | max_reg={self._max_reg}')

    # ── Sign convention (dari teleop_keyboard.py yg terbukti jalan) ──────────
    # Forward (vx>0): left register NEGATIF, right register POSITIF
    # Rumus: v_left = vx - wz*D/2 ; left_reg = -v_left * SCALE
    #        v_right = vx + wz*D/2 ; right_reg = +v_right * SCALE
    def _compute_regs(self, vx: float, wz: float):
        v_left  = vx - wz * WHEEL_SEP / 2.0
        v_right = vx + wz * WHEEL_SEP / 2.0
        cap = self._max_reg
        left_reg  = int(max(-cap, min(cap, -v_left  * LINEAR_TO_RPM)))
        right_reg = int(max(-cap, min(cap, +v_right * LINEAR_TO_RPM)))
        return left_reg, right_reg

    def _send(self, vx: float, wz: float):
        l, r = self._compute_regs(vx, wz)
        try:
            self.zlac.set_rpm(l, r)
        except Exception as e:
            self.get_logger().warn(f'ZLAC write: {e}', throttle_duration_sec=2.0)

    def _cmd_cb(self, msg: Twist):
        self._vx       = msg.linear.x
        self._wz       = msg.angular.z
        self._last_cmd = self.get_clock().now()
        self._stopped  = False

    def _estop_cb(self, msg: Bool):
        self._estop = msg.data
        if self._estop:
            self._send(0.0, 0.0)

    def _timer_cb(self):
        if self._estop:
            self._send(0.0, 0.0)  # keep sending to prevent ZLAC offline timeout
            return
        dt = (self.get_clock().now().nanoseconds - self._last_cmd.nanoseconds) / 1e9
        if dt > self._timeout:
            self._stopped = True
            self._send(0.0, 0.0)  # always send 0 — never go silent, ZLAC offline=1s
            return
        self._stopped = False
        self._send(self._vx, self._wz)

    def destroy_node(self):
        # Blokir SIGINT/SIGTERM selama cleanup supaya pymodbus tidak ter-interrupt
        # di tengah pengiriman RPM=0.
        old_int  = signal.signal(signal.SIGINT,  signal.SIG_IGN)
        old_term = signal.signal(signal.SIGTERM, signal.SIG_IGN)
        for attempt in range(3):
            try:
                self.zlac.set_rpm(0, 0)
                time.sleep(0.05)
                print('[zlac_driver_node] ZLAC stopped (RPM=0).')
                break
            except Exception:
                time.sleep(0.05)
        signal.signal(signal.SIGINT,  old_int)
        signal.signal(signal.SIGTERM, old_term)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ZlacDriverNode()

    # Event untuk shutdown bersih — sinyal set flag, bukan raise exception.
    _stop = threading.Event()
    signal.signal(signal.SIGINT,  lambda s, f: _stop.set())
    signal.signal(signal.SIGTERM, lambda s, f: _stop.set())

    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        while not _stop.is_set():
            executor.spin_once(timeout_sec=0.05)
    finally:
        # Blokir sinyal lagi agar destroy_node tidak ter-interrupt dua kali.
        signal.signal(signal.SIGINT,  signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
