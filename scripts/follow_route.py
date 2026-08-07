#!/usr/bin/env python3
"""
track_route.py – Mengambil path dari route_server lalu mengirimkannya
ke /navigate_through_poses agar robot bergerak fisik.

Usage:
    python3 scripts/track_route.py [goal_id]
    # default goal_id = 4  (node terakhir dari rute 0->1->2->3->4)
"""

import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import ComputeRoute, FollowPath
from geometry_msgs.msg import PoseStamped


class RouteRunner(Node):
    def __init__(self, goal_id: int):
        super().__init__('track_route')
        self.goal_id = goal_id
        self._compute_client = ActionClient(self, ComputeRoute, '/compute_route')
        self._follow_client  = ActionClient(self, FollowPath, '/follow_path')
        self.timer = self.create_timer(0.5, self._step1_compute_route)

    # ── STEP 1: minta route_server hitung jalur ──────────────────────────────
    def _step1_compute_route(self):
        self.timer.cancel()

        self.get_logger().info('Menunggu action server /compute_route ...')
        if not self._compute_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('/compute_route tidak tersedia!')
            rclpy.shutdown()
            return

        goal = ComputeRoute.Goal()
        goal.goal_id = self.goal_id
        goal.use_poses = False
        goal.use_start = False

        self.get_logger().info(f'Menghitung rute ke goal_id={self.goal_id} ...')
        fut = self._compute_client.send_goal_async(goal)
        fut.add_done_callback(self._on_compute_goal_response)

    def _on_compute_goal_response(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error('compute_route: Goal ditolak oleh route_server!')
            rclpy.shutdown()
            return
        self.get_logger().info('compute_route: Goal diterima, menunggu path ...')
        handle.get_result_async().add_done_callback(self._on_compute_result)

    def _on_compute_result(self, future):
        result = future.result().result
        path_poses = result.path.poses

        if not path_poses:
            self.get_logger().error('Tidak ada path yang dikembalikan oleh route_server!')
            rclpy.shutdown()
            return

        # ── Info rute ────────────────────────────────────────────────────────
        self.get_logger().info(
            f'Planning time: {result.planning_time.sec}.{result.planning_time.nanosec:09d} detik'
        )
        self.get_logger().info(
            f'Route cost: {result.route.route_cost:.4f}'
        )
        self.get_logger().info(
            f'Total node dalam rute: {len(result.route.nodes)}'
        )
        for i, n in enumerate(result.route.nodes):
            status = '✓ START' if i == 0 else ('✓ GOAL' if i == len(result.route.nodes) - 1 else '  waypoint')
            self.get_logger().info(
                f'  Node [{i}] id={n.nodeid}  pos=({n.position.x:.4f}, {n.position.y:.4f})  {status}'
            )
        # ─────────────────────────────────────────────────────────────────────

        self.get_logger().info(
            f'Path berhasil dihitung: {len(path_poses)} titik. '
            f'Mengirim ke /navigate_through_poses ...')
            
        print("===== TYPE ROUTE NODE 0 =====")
        print(type(result.route.nodes[0]))
        print("===== ROUTE NODE 0 =====")
        print(result.route.nodes[0])
        print("=========================")

        print("===== FIRST POSE =====")
        print(path_poses[0])
        print("======================")
        
        for i, p in enumerate(path_poses[:5]):
            self.get_logger().info(
                f"{i}: frame='{p.header.frame_id}' "
                f"x={p.pose.position.x:.3f} "
                f"y={p.pose.position.y:.3f}"
            )
            
        self._step2_follow(result.path)

    # ── STEP 2: kirim path langsung ke local controller ──────────────────────
    def _step2_follow(self, path):
        if not self._follow_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('/follow_path tidak tersedia!')
            rclpy.shutdown()
            return

        # Set frame_id dan stamp pada header path
        stamp = self.get_clock().now().to_msg()
        path.header.frame_id = 'map'
        path.header.stamp = stamp
        for p in path.poses:
            p.header.frame_id = 'map'
            p.header.stamp = stamp

        goal = FollowPath.Goal()
        goal.path = path
        goal.controller_id = ''   # kosong → pakai controller default

        self.get_logger().info(
            f'Mengirim {len(path.poses)} pose langsung ke /follow_path (skip global planner)...')
        fut = self._follow_client.send_goal_async(goal)
        fut.add_done_callback(self._on_follow_goal_response)

    def _on_follow_goal_response(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error('/follow_path: Goal ditolak!')
            rclpy.shutdown()
            return
        self.get_logger().info('Robot MULAI BERGERAK mengikuti rute!')
        handle.get_result_async().add_done_callback(self._on_follow_result)

    def _on_follow_result(self, future):
        self.get_logger().info('Navigasi selesai! Robot telah menempuh seluruh rute.')
        rclpy.shutdown()


def main():
    rclpy.init()
    goal_id = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    node = RouteRunner(goal_id)
    rclpy.spin(node)


if __name__ == '__main__':
    main()
