import socket
import threading
import time
from typing import Optional

import rclpy
from rclpy.node import Node

from interfaces.amr_msgs.msg import RobotStatus

from client.amr_discovery.amr_discovery.protocol import (
    DEFAULT_PORT,
    RobotStatusSnapshot,
    build_reply,
    encode_reply,
    parse_request,
)

# Konvensi amr_ws untuk "sensor belum tersedia" (lihat mission_executor_node)
UNAVAILABLE = -1.0

MODE_NAMES = {
    RobotStatus.MODE_IDLE:      'IDLE',
    RobotStatus.MODE_MANUAL:    'MANUAL',
    RobotStatus.MODE_AUTO:      'AUTO',
    RobotStatus.MODE_EMERGENCY: 'EMERGENCY',
}

ERROR_NAMES = {
    RobotStatus.ERROR_NONE:  'NONE',
    RobotStatus.ERROR_MOTOR: 'MOTOR',
    RobotStatus.ERROR_LIDAR: 'LIDAR',
    RobotStatus.ERROR_IMU:   'IMU',
    RobotStatus.ERROR_NAV:   'NAV',
}


class DiscoveryNode(Node):

    def __init__(self):
        super().__init__('discovery_node')

        self.declare_parameter('robot_id', '')
        self.declare_parameter('port', DEFAULT_PORT)
        self.declare_parameter('status_topic', '/robot/status')
        self.declare_parameter('battery_voltage_max', UNAVAILABLE)
        self.declare_parameter('status_stale_timeout', 10.0)

        self._robot_id = self.get_parameter('robot_id').value or socket.gethostname()
        self._port = int(self.get_parameter('port').get_parameter_value().integer_value)
        self._battery_voltage_max = float(self.get_parameter('battery_voltage_max').get_parameter_value().double_value)
        self._stale_timeout = float(self.get_parameter('status_stale_timeout').get_parameter_value().double_value)

        self._lock = threading.Lock()
        self._last_status: Optional[RobotStatus] = None
        self._last_status_at: Optional[float] = None

        self.create_subscription(
            RobotStatus,
            self.get_parameter('status_topic').get_parameter_value().string_value,
            self._on_status,
            10,
        )

        self._stop_event = threading.Event()
        self._sock = self._open_socket()
        self._server_thread = threading.Thread(target=self._serve_forever, daemon=True)
        self._server_thread.start()

        self.get_logger().info(
            f'discovery_node started | robot_id={self._robot_id} port={self._port}'
        )

    # ------------------------------------------------------------------
    # ROS callback
    # ------------------------------------------------------------------
    def _on_status(self, msg: RobotStatus):
        with self._lock:
            self._last_status = msg
            self._last_status_at = time.monotonic()

    # ------------------------------------------------------------------
    # UDP server (thread terpisah dari executor rclpy)
    # ------------------------------------------------------------------
    def _open_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('', self._port))
        sock.settimeout(1.0)
        return sock

    def _serve_forever(self):
        while not self._stop_event.is_set():
            try:
                raw, addr = self._sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break

            request = parse_request(raw)
            if request is None:
                self.get_logger().warn(
                    f'Paket discovery tidak valid dari {addr}', throttle_duration_sec=10.0
                )
                continue

            self._reply_to(addr, request.nonce)

    def _reply_to(self, addr, nonce: Optional[str]):
        reply = build_reply(
            robot_id=self._robot_id,
            ip=self._get_local_ip(),
            nonce=nonce,
            timestamp=time.time(),
            status=self._snapshot_status(),
        )
        try:
            self._sock.sendto(encode_reply(reply), addr)
        except OSError as e:
            self.get_logger().warn(f'Gagal kirim reply ke {addr}: {e}')

    def _snapshot_status(self) -> RobotStatusSnapshot:
        with self._lock:
            msg = self._last_status
            age = (None if self._last_status_at is None
                   else time.monotonic() - self._last_status_at)

        voltage_max = self._value_or_none(self._battery_voltage_max)

        if msg is None or age is None or age > self._stale_timeout:
            return RobotStatusSnapshot(battery_voltage_max=voltage_max)

        return RobotStatusSnapshot(
            mode=MODE_NAMES.get(msg.mode),
            error_code=ERROR_NAMES.get(msg.error_code),
            battery_percent=self._value_or_none(msg.battery_percent),
            battery_voltage=self._value_or_none(msg.battery_voltage),
            battery_voltage_max=voltage_max,
            is_charging=msg.is_charging,
            status_message=msg.status_message or None,
        )

    @staticmethod
    def _value_or_none(value: float) -> Optional[float]:
        return None if value < 0 else float(value)

    @staticmethod
    def _get_local_ip() -> Optional[str]:
        # "Connect" UDP tidak benar-benar mengirim paket, hanya dipakai untuk
        # membaca IP interface yang akan dipakai OS keluar ke LAN.
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(('8.8.8.8', 80))
            return probe.getsockname()[0]
        except OSError:
            return None
        finally:
            probe.close()

    # ------------------------------------------------------------------
    def destroy_node(self):
        self._stop_event.set()
        self._sock.close()
        self._server_thread.join(timeout=2.0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DiscoveryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
