import math
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from action_msgs.msg import GoalStatus

from nav2_msgs.action import NavigateToPose
from amr_msgs.msg import MissionCommand, MissionStatus, RobotStatus


class MissionExecutor(Node):

    def __init__(self):
        super().__init__('mission_executor_node')

        # ── Parameter: daftar stasiun ──────────────────────────────────────
        self.declare_parameter('station_names', ['A', 'B', 'C'])
        station_names = self.get_parameter('station_names').value

        self.stations: dict[str, tuple[float, float, float]] = {}
        for name in station_names:
            self.declare_parameter(f'station_{name}_x',   0.0)
            self.declare_parameter(f'station_{name}_y',   0.0)
            self.declare_parameter(f'station_{name}_yaw', 0.0)
            self.stations[name] = (
                self.get_parameter(f'station_{name}_x').value,
                self.get_parameter(f'station_{name}_y').value,
                self.get_parameter(f'station_{name}_yaw').value,
            )
        self.get_logger().info(f'Loaded stations: {list(self.stations.keys())}')

        # ── State misi ────────────────────────────────────────────────────
        self._lock           = threading.Lock()
        self._state          = MissionStatus.IDLE
        self._queue: list[str] = []
        self._original_queue: list[str] = []
        self._loop           = False
        self._current        = ''
        self._done_count     = 0
        self._msg_text       = ''
        self._mode           = RobotStatus.MODE_IDLE
        self._error_code     = RobotStatus.ERROR_NONE

        # ── Nav2 action client ────────────────────────────────────────────
        cb_group = ReentrantCallbackGroup()
        self._nav = ActionClient(self, NavigateToPose, 'navigate_to_pose',
                                 callback_group=cb_group)
        self._cancel_nav = threading.Event()   # set = batalkan navigasi aktif
        self._new_cmd    = threading.Event()   # set = ada perintah baru

        # ── Pub / Sub ─────────────────────────────────────────────────────
        self.create_subscription(
            MissionCommand, '/mission/command',
            self._on_command, 10,
            callback_group=cb_group)
        self._status_pub = self.create_publisher(MissionStatus, '/mission/status', 10)
        self._robot_pub  = self.create_publisher(RobotStatus,  '/robot/status',   10)

        self.create_timer(0.5, self._pub_status)
        self.create_timer(1.0, self._pub_robot)

        # ── Thread misi berjalan di background ────────────────────────────
        t = threading.Thread(target=self._mission_loop, daemon=True)
        t.start()

        self.get_logger().info('mission_executor_node ready')

    # ──────────────────────────────────────────────────────────────────────
    # Callback: perintah misi masuk
    # ──────────────────────────────────────────────────────────────────────
    def _on_command(self, msg: MissionCommand):
        invalid = [s for s in msg.stations if s not in self.stations]
        if invalid:
            self.get_logger().warn(f'Unknown stations ignored: {invalid}')
            return
        if not msg.stations:
            self.get_logger().warn('Empty station list, ignoring')
            return

        with self._lock:
            self._cancel_nav.set()          # batalkan nav aktif kalau ada
            self._queue          = list(msg.stations)
            self._original_queue = list(msg.stations)
            self._loop           = msg.loop
            self._done_count     = 0
            self._current        = ''
            self._state          = MissionStatus.NAVIGATING
            self._msg_text       = 'Mission received: ' + ' → '.join(msg.stations)
            self._mode           = RobotStatus.MODE_AUTO
            self._error_code     = RobotStatus.ERROR_NONE

        self.get_logger().info(self._msg_text)
        self._new_cmd.set()

    # ──────────────────────────────────────────────────────────────────────
    # Loop utama misi (thread terpisah)
    # ──────────────────────────────────────────────────────────────────────
    def _mission_loop(self):
        while rclpy.ok():
            # Tunggu sampai ada perintah baru
            self._new_cmd.wait()
            self._new_cmd.clear()
            self._cancel_nav.clear()

            while True:
                with self._lock:
                    if self._state == MissionStatus.IDLE:
                        break
                    if not self._queue:
                        if self._loop:
                            self._queue = list(self._original_queue)
                            self.get_logger().info('Loop mode: restarting mission')
                        else:
                            self._state    = MissionStatus.COMPLETED
                            self._msg_text = 'All stations completed'
                            self._mode     = RobotStatus.MODE_IDLE
                            self.get_logger().info('Mission completed')
                            break
                    target = self._queue[0]
                    self._current = target
                    self._state   = MissionStatus.NAVIGATING
                    self._msg_text = f'Navigating to {target}'

                self.get_logger().info(f'→ {target}  {self.stations[target]}')

                success = self._go_to(target)

                # Cek apakah dibatalkan oleh perintah baru
                if self._cancel_nav.is_set():
                    break

                with self._lock:
                    if not success:
                        self._state      = MissionStatus.FAILED
                        self._msg_text   = f'Navigation to {target} failed'
                        self._error_code = RobotStatus.ERROR_NAV
                        self._mode       = RobotStatus.MODE_IDLE
                        self.get_logger().error(self._msg_text)
                        break
                    self._queue.pop(0)
                    self._done_count += 1
                    self._state    = MissionStatus.ARRIVED
                    self._msg_text = f'Arrived at {target}'
                    self.get_logger().info(self._msg_text)

    # ──────────────────────────────────────────────────────────────────────
    # Navigasi ke satu stasiun — blocking sampai sampai / gagal / dibatalkan
    # ──────────────────────────────────────────────────────────────────────
    def _go_to(self, station: str) -> bool:
        if not self._nav.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('NavigateToPose server tidak tersedia')
            return False

        x, y, yaw = self.stations[station]
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp    = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        goal.pose.pose.orientation.z = math.sin(yaw / 2.0)
        goal.pose.pose.orientation.w = math.cos(yaw / 2.0)

        done  = threading.Event()
        store = [None]   # [True/False/None]
        handle_box = [None]

        def _on_response(fut):
            h = fut.result()
            if not h.accepted:
                store[0] = False
                done.set()
                return
            handle_box[0] = h
            h.get_result_async().add_done_callback(_on_result)

        def _on_result(fut):
            store[0] = (fut.result().status == GoalStatus.STATUS_SUCCEEDED)
            done.set()

        self._nav.send_goal_async(goal).add_done_callback(_on_response)

        # Tunggu selesai, tapi cek cancel setiap 100 ms
        while not done.wait(timeout=0.1):
            if self._cancel_nav.is_set():
                if handle_box[0] is not None:
                    handle_box[0].cancel_goal_async()
                done.wait()          # tunggu cancel confirm dari server
                return False

        return bool(store[0])

    # ──────────────────────────────────────────────────────────────────────
    # Publishers
    # ──────────────────────────────────────────────────────────────────────
    def _pub_status(self):
        msg = MissionStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        with self._lock:
            msg.state           = self._state
            msg.current_station = self._current
            msg.remaining       = list(self._queue)
            msg.stations_done   = self._done_count
            msg.message         = self._msg_text
        self._status_pub.publish(msg)

    def _pub_robot(self):
        msg = RobotStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        with self._lock:
            msg.mode       = self._mode
            msg.error_code = self._error_code
        # battery sensor belum ada → -1 sebagai penanda "tidak tersedia"
        msg.battery_percent = -1.0
        msg.battery_voltage = -1.0
        msg.is_charging     = False
        msg.status_message  = self._msg_text
        self._robot_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = MissionExecutor()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
