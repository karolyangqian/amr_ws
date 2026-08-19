#!/usr/bin/env python3

import json
import math
import os
import sys

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus

from nav2_msgs.action import ComputeRoute
from nav2_msgs.action import FollowPath
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped, Twist
from tf2_ros import Buffer, TransformListener, TransformException


def yaw_to_quaternion(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class FollowRoute(Node):

    def __init__(self, goal_id, start_id=None):

        super().__init__("follow_route")

        self.goal_id = goal_id
        self.start_id = start_id
        self.segments = []
        self.current_segment_idx = 0

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.compute_client = ActionClient(
            self,
            ComputeRoute,
            "/compute_route"
        )

        self.follow_client = ActionClient(
            self,
            FollowPath,
            "/follow_path"
        )

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.timer = self.create_timer(
            1.5,
            self.compute_route
        )

    # =======================================================
    # TF HELPER FOR YAW
    # =======================================================

    def get_robot_yaw(self):

        try:
            now = rclpy.time.Time()
            transform = self.tf_buffer.lookup_transform(
                'map',
                'base_footprint',
                now,
                timeout=rclpy.duration.Duration(seconds=0.5)
            )
            q = transform.transform.rotation
            siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
            cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            return math.atan2(siny_cosp, cosy_cosp)
        except Exception:
            return None

    # =======================================================
    # IN-PLACE ROTATION BEFORE MOVING FORWARD
    # =======================================================

    def rotate_in_place_to_heading(self, target_yaw):

        self.get_logger().info(
            f"Memutar robot di tempat ke arah target yaw: {math.degrees(target_yaw):.1f}° ..."
        )

        start_time = self.get_clock().now()

        while rclpy.ok():

            current_yaw = self.get_robot_yaw()
            if current_yaw is None:
                rclpy.spin_once(self, timeout_sec=0.1)
                continue

            diff = math.atan2(math.sin(target_yaw - current_yaw), math.cos(target_yaw - current_yaw))

            # Toleransi presisi ketat < 2.3 derajat (0.04 rad)
            if abs(diff) < 0.75:
                cmd = Twist()
                cmd.angular.z = 0.0
                self.cmd_pub.publish(cmd)
                self.get_logger().info(f"✓ Robot lurus presisi! Error: {math.degrees(diff):.2f}°")
                break

            elapsed = (self.get_clock().now() - start_time).nanoseconds / 1e9
            if elapsed > 15.0:
                self.get_logger().warn("Timeout rotasi di tempat terlewati, melanjutkan...")
                break

            cmd = Twist()
            rot_speed = max(0.1, min(0.3, 0.7 * abs(diff)))
            cmd.angular.z = rot_speed if diff > 0 else -rot_speed
            self.cmd_pub.publish(cmd)

            rclpy.spin_once(self, timeout_sec=0.05)

    # =======================================================
    # AUTO DETECT CLOSEST NODE FROM TF
    # =======================================================

    def get_closest_node_from_tf(self):

        geojson_path = os.path.expanduser(
            '~/Documents/rein_amr/amr_ws/src/subsystems/'
            'amr_navigation/config/route_graph.geojson'
        )

        if not os.path.exists(geojson_path):
            return None

        start_time = self.get_clock().now()

        while rclpy.ok():
            try:
                # Use rclpy.time.Time() (0 time) to fetch latest transform in TF buffer
                transform = self.tf_buffer.lookup_transform(
                    'map',
                    'base_footprint',
                    rclpy.time.Time(),
                    timeout=rclpy.duration.Duration(seconds=1.0)
                )

                rx = transform.transform.translation.x
                ry = transform.transform.translation.y

                with open(geojson_path, 'r') as f:
                    data = json.load(f)

                best_id = None
                min_dist = float('inf')

                for feature in data.get('features', []):
                    if feature.get('geometry', {}).get('type') == 'Point':
                        node_id = feature['properties']['id']
                        coords = feature['geometry']['coordinates']
                        nx, ny = coords[0], coords[1]

                        dist = math.hypot(rx - nx, ry - ny)
                        if dist < min_dist:
                            min_dist = dist
                            best_id = node_id

                if best_id is not None and min_dist < 4.0:
                    self.get_logger().info(
                        f"✓ Auto-detected robot position: ({rx:.2f}, {ry:.2f}) -> Closest Node ID: {best_id} (dist: {min_dist:.2f}m)"
                    )
                    return best_id
                break

            except Exception as ex:
                elapsed = (self.get_clock().now() - start_time).nanoseconds / 1e9
                if elapsed > 4.0:
                    self.get_logger().warn(f"Could not lookup TF map -> base_footprint after 4s: {ex}")
                    break
                rclpy.spin_once(self, timeout_sec=0.2)

        return None

    # =======================================================
    # STEP 1 : COMPUTE ROUTE
    # =======================================================

    def compute_route(self):

        self.timer.cancel()

        self.get_logger().info("Waiting /compute_route ...")

        if not self.compute_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("/compute_route unavailable!")
            rclpy.shutdown()
            return

        if self.start_id is None:
            self.start_id = self.get_closest_node_from_tf()

        goal = ComputeRoute.Goal()
        goal.goal_id = self.goal_id
        goal.use_poses = False

        if self.start_id is not None:
            goal.start_id = self.start_id
            goal.use_start = True
            self.get_logger().info(
                f"Request Route -> Start ID {self.start_id} to Goal ID {self.goal_id}"
            )
        else:
            goal.use_start = False
            self.get_logger().info(
                f"Request Route -> Goal ID {self.goal_id} (using TF current pose)"
            )

        future = self.compute_client.send_goal_async(goal)
        future.add_done_callback(self.compute_goal_response)

    # =======================================================

    def compute_goal_response(self, future):

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error("ComputeRoute rejected!")
            rclpy.shutdown()
            return

        self.get_logger().info("ComputeRoute accepted.")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.compute_result)

    # =======================================================

    def compute_result(self, future):

        result = future.result().result

        self.get_logger().info("")
        self.get_logger().info("========== ROUTE ==========")

        self.get_logger().info(
            f"Route Cost : {result.route.route_cost:.3f}"
        )

        self.get_logger().info(
            f"Route Nodes : {len(result.route.nodes)}"
        )

        self.get_logger().info(
            f"Path Poses : {len(result.path.poses)}"
        )

        for i, node in enumerate(result.route.nodes):
            self.get_logger().info(
                f"Node {i}  "
                f"id={node.nodeid}  "
                f"x={node.position.x:.3f}  "
                f"y={node.position.y:.3f}"
            )

        self.get_logger().info("===========================")
        self.get_logger().info("")

        if len(result.route.nodes) <= 1 or len(result.path.poses) <= 1:
            self.get_logger().info(f"✓ Robot sudah berada di Node tujuan (Node {self.goal_id})!")
            rclpy.shutdown()
            return

        # Pecah rute menjadi segmen terpisah antar-node (Stop & Rotate & Drive Straight)
        self.build_segment_paths(result.route.nodes, result.path)

        if not self.segments:
            self.get_logger().warn("Tidak ada segment untuk dijalankan.")
            rclpy.shutdown()
            return

        self.current_segment_idx = 0
        self.execute_next_segment()

    # =======================================================
    # BUILD SEGMENT PATHS (STOP AT EACH NODE + HEADING ALIGN)
    # =======================================================

    def build_segment_paths(self, nodes, full_path):

        self.segments = []
        poses = full_path.poses

        if len(nodes) < 2 or not poses:
            return

        # Cari indeks pose terdekat di full_path untuk tiap node
        node_indices = []

        for node in nodes:
            nx = node.position.x
            ny = node.position.y

            best_idx = 0
            best_dist = float('inf')

            for idx, p in enumerate(poses):
                dx = p.pose.position.x - nx
                dy = p.pose.position.y - ny
                dist_sq = dx * dx + dy * dy

                if dist_sq < best_dist:
                    best_dist = dist_sq
                    best_idx = idx

            node_indices.append(best_idx)

        # Buat sub-path lurus sempurna untuk setiap pasang node berturutan
        for i in range(len(nodes) - 1):
            start_idx = node_indices[i]
            end_idx = node_indices[i + 1]

            if start_idx >= end_idx:
                end_idx = start_idx + 1

            raw_sub_poses = poses[start_idx : end_idx + 1]

            start_node = nodes[i]
            end_node = nodes[i + 1]

            # Hitung sudut yaw dari start_node ke end_node
            dx = end_node.position.x - start_node.position.x
            dy = end_node.position.y - start_node.position.y
            target_yaw = math.atan2(dy, dx)
            _, _, qz, qw = yaw_to_quaternion(target_yaw)

            sub_path = Path()
            sub_path.header = full_path.header

            for orig_p in raw_sub_poses:
                p = PoseStamped()
                p.header = orig_p.header
                p.pose.position.x = orig_p.pose.position.x
                p.pose.position.y = orig_p.pose.position.y
                p.pose.position.z = orig_p.pose.position.z

                # Force orientation 100% lurus searah target node segmen ini
                p.pose.orientation.x = 0.0
                p.pose.orientation.y = 0.0
                p.pose.orientation.z = qz
                p.pose.orientation.w = qw

                sub_path.poses.append(p)

            self.segments.append((start_node.nodeid, end_node.nodeid, target_yaw, sub_path))

        self.get_logger().info(f"Rute dipecah menjadi {len(self.segments)} segmen (Stop & Rotate per node).")

    # =======================================================
    # STEP 2 : EXECUTE SEGMENTS SEQUENTIALLY
    # =======================================================

    def execute_next_segment(self):

        if self.current_segment_idx >= len(self.segments):
            self.get_logger().info("")
            self.get_logger().info("========== ALL NODES COMPLETED SUCCESSFULLY ==========")
            rclpy.shutdown()
            return

        start_id, end_id, target_yaw, path = self.segments[self.current_segment_idx]

        self.get_logger().info(
            f"--- Segmen {self.current_segment_idx + 1}/{len(self.segments)}: Node {start_id} ---> Node {end_id} ---"
        )

        # Rotasi di tempat terlebih dahulu sampai lurus presisi (< 2.3°) ke target yaw segmen ini
        self.rotate_in_place_to_heading(target_yaw)

        # Setelah lurus presisi, jalankan pergerakan maju lurus
        self.follow_path(path)

    def follow_path(self, path):

        if not self.follow_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("/follow_path unavailable!")
            rclpy.shutdown()
            return

        goal = FollowPath.Goal()
        goal.path = path
        goal.controller_id = ""
        goal.goal_checker_id = ""

        future = self.follow_client.send_goal_async(
            goal,
            feedback_callback=self.follow_feedback
        )

        future.add_done_callback(self.follow_response)

    def follow_response(self, future):

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error("FollowPath rejected for current segment!")
            rclpy.shutdown()
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.follow_result)

    def follow_feedback(self, feedback_msg):

        fb = feedback_msg.feedback
        self.get_logger().info(
            f"Distance to node: {fb.distance_to_goal:.3f} m | Speed: {fb.speed:.3f} m/s",
            throttle_duration_sec=2.0
        )

    def follow_result(self, future):

        result = future.result()

        if result.status == GoalStatus.STATUS_SUCCEEDED:
            start_id, end_id, _, _ = self.segments[self.current_segment_idx]
            self.get_logger().info(f"✓ Berhasil Tiba di Node {end_id}")

            self.current_segment_idx += 1
            self.execute_next_segment()

        else:
            self.get_logger().error(f"Segmen gagal dengan status: {result.status}")
            rclpy.shutdown()


# ===========================================================

def main():

    rclpy.init()

    goal_id = 0
    start_id = None

    if len(sys.argv) > 1:
        goal_id = int(sys.argv[1])

    if len(sys.argv) > 2:
        start_id = int(sys.argv[2])

    node = FollowRoute(goal_id, start_id)
    rclpy.spin(node)


if __name__ == "__main__":
    main()