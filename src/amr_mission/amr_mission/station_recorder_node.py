"""
Station Recorder — simpan pose AMCL ke file YAML stations.yaml

Cara pakai:
  1. Jalankan SLAM/Nav2 + AMCL
  2. ros2 run amr_mission station_recorder_node
  3. Drive robot ke posisi stasiun yang diinginkan
  4. Kirim nama stasiun:
       ros2 topic pub --once /record_station std_msgs/msg/String '{data: "A"}'
  5. Ulangi untuk tiap stasiun
  6. Hasilnya otomatis tersimpan di ~/stations_recorded.yaml
     Salin isinya ke amr_mission/config/stations.yaml lalu rebuild
"""
import math
import os

import rclpy
import yaml
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.node import Node
from std_msgs.msg import String


class StationRecorder(Node):

    def __init__(self):
        super().__init__('station_recorder_node')

        self.declare_parameter(
            'output_yaml',
            os.path.expanduser('~/stations_recorded.yaml'),
        )
        self._out = self.get_parameter('output_yaml').value
        self._pose: PoseWithCovarianceStamped | None = None
        self._stations: dict = {}

        if os.path.exists(self._out):
            self._load_existing()

        self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose', self._pose_cb, 10)
        self.create_subscription(
            String, '/record_station', self._record_cb, 10)

        self.get_logger().info(
            f'station_recorder_node ready\n'
            f'  Output  : {self._out}\n'
            f'  Record  : ros2 topic pub --once /record_station '
            f"std_msgs/msg/String '{{data: \"A\"}}'"
        )

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _pose_cb(self, msg: PoseWithCovarianceStamped):
        self._pose = msg

    def _record_cb(self, msg: String):
        name = msg.data.strip()
        if not name:
            self.get_logger().warn('Nama stasiun kosong, abaikan')
            return
        if self._pose is None:
            self.get_logger().warn('Belum ada pose dari /amcl_pose')
            return

        p   = self._pose.pose.pose
        yaw = 2.0 * math.atan2(p.orientation.z, p.orientation.w)

        self._stations[name] = {
            'x':   round(p.position.x, 4),
            'y':   round(p.position.y, 4),
            'yaw': round(yaw, 4),
        }
        self._save()
        self.get_logger().info(
            f'Saved "{name}": x={p.position.x:.3f}  y={p.position.y:.3f}  '
            f'yaw={math.degrees(yaw):.1f}°'
        )

    # ── Load / Save ───────────────────────────────────────────────────────

    def _load_existing(self):
        try:
            with open(self._out) as f:
                data = yaml.safe_load(f)
            params = (
                data.get('mission_executor_node', {})
                    .get('ros__parameters', {})
            )
            for n in params.get('station_names', []):
                self._stations[n] = {
                    'x':   params.get(f'station_{n}_x',   0.0),
                    'y':   params.get(f'station_{n}_y',   0.0),
                    'yaw': params.get(f'station_{n}_yaw', 0.0),
                }
            self.get_logger().info(
                f'Loaded {len(self._stations)} existing stations from {self._out}'
            )
        except Exception as e:
            self.get_logger().warn(f'Could not load existing file: {e}')

    def _save(self):
        names  = sorted(self._stations.keys())
        params: dict = {'station_names': names}
        for n, v in sorted(self._stations.items()):
            params[f'station_{n}_x']   = v['x']
            params[f'station_{n}_y']   = v['y']
            params[f'station_{n}_yaw'] = v['yaw']

        out_data = {'mission_executor_node': {'ros__parameters': params}}
        with open(self._out, 'w') as f:
            yaml.dump(out_data, f, default_flow_style=False, sort_keys=False)

        self.get_logger().info(
            f'→ Tersimpan di {self._out}\n'
            f'  Salin ke amr_mission/config/stations.yaml lalu: '
            f'colcon build --packages-select amr_mission'
        )


def main(args=None):
    rclpy.init(args=args)
    node = StationRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
