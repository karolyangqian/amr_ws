import subprocess

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Bool
from diagnostic_msgs.msg import DiagnosticStatus, KeyValue


WARN_V     = 37.2   # V — peringatan, segera charge
LIMIT_V    = 35.5   # V — stop misi baru
SHUTDOWN_V = 34.5   # V — motor sudah dimatikan firmware, minta shutdown NUC


class BatteryMonitorNode(Node):

    def __init__(self):
        super().__init__('battery_monitor_node')

        self._shutdown_triggered = False

        self.create_subscription(Float32, '/battery_voltage', self._cb, 10)

        self._pub_status   = self.create_publisher(DiagnosticStatus, '/battery_status', 10)
        self._pub_low      = self.create_publisher(Bool, '/battery_low', 10)
        self._pub_critical = self.create_publisher(Bool, '/battery_critical', 10)

        # Watchdog: jika tidak ada data voltage > 30 detik, log peringatan
        self._last_reading = self.get_clock().now()
        self.create_timer(15.0, self._watchdog)

        self.get_logger().info(
            f'battery_monitor started | WARN={WARN_V}V LIMIT={LIMIT_V}V SHUTDOWN={SHUTDOWN_V}V'
        )

    def _cb(self, msg: Float32):
        self._last_reading = self.get_clock().now()
        v = msg.data

        status = DiagnosticStatus()
        status.name = 'Battery'
        status.hardware_id = 'CUBEBATT_LiFePO4_36V'
        status.values = [KeyValue(key='voltage_V', value=f'{v:.2f}')]

        is_low      = v < LIMIT_V
        is_critical = v < SHUTDOWN_V

        if v < 10.0:
            # Bacaan tidak valid (ZLAC belum siap)
            return

        if is_critical:
            status.level   = DiagnosticStatus.ERROR
            status.message = f'CRITICAL {v:.1f}V — motor dimatikan, charge segera!'
            self.get_logger().error(status.message)
            if not self._shutdown_triggered:
                self._shutdown_triggered = True
                self._request_nuc_shutdown()
        elif is_low:
            status.level   = DiagnosticStatus.WARN
            status.message = f'LOW {v:.1f}V — hentikan misi baru, segera charge'
            self.get_logger().warn(status.message)
        elif v < WARN_V:
            status.level   = DiagnosticStatus.WARN
            status.message = f'WARNING {v:.1f}V — baterai lemah, charge soon'
            self.get_logger().warn(status.message, throttle_duration_sec=30.0)
        else:
            status.level   = DiagnosticStatus.OK
            status.message = f'OK {v:.1f}V'
            self.get_logger().info(status.message, throttle_duration_sec=60.0)

        self._pub_status.publish(status)
        self._pub_low.publish(Bool(data=is_low))
        self._pub_critical.publish(Bool(data=is_critical))

    def _watchdog(self):
        elapsed = (self.get_clock().now() - self._last_reading).nanoseconds / 1e9
        if elapsed > 30.0:
            self.get_logger().warn(
                f'Tidak ada data /battery_voltage selama {elapsed:.0f}s — cek koneksi ZLAC',
                throttle_duration_sec=30.0,
            )

    def _request_nuc_shutdown(self):
        self.get_logger().fatal('Tegangan KRITIS — meminta NUC shutdown dalam 10 detik!')
        try:
            subprocess.Popen(['sudo', 'shutdown', '-h', '+1',
                              'AMR battery critical — auto shutdown'])
        except Exception as e:
            self.get_logger().error(f'Gagal trigger shutdown: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = BatteryMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
