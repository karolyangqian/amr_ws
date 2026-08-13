#!/usr/bin/env python3

import sys

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus

from nav2_msgs.action import ComputeRoute
from nav2_msgs.action import FollowPath


class FollowRoute(Node):

    def __init__(self, goal_id):

        super().__init__("follow_route")

        self.goal_id = goal_id

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

        self.timer = self.create_timer(
            1.0,
            self.compute_route
        )

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

        goal = ComputeRoute.Goal()

        goal.goal_id = self.goal_id
        goal.use_start = False
        goal.use_poses = False

        self.get_logger().info(
            f"Request Route -> Goal ID {self.goal_id}"
        )

        future = self.compute_client.send_goal_async(goal)

        future.add_done_callback(
            self.compute_goal_response
        )

    # =======================================================

    def compute_goal_response(self, future):

        goal_handle = future.result()

        if not goal_handle.accepted:

            self.get_logger().error("ComputeRoute rejected!")

            rclpy.shutdown()
            return

        self.get_logger().info(
            "ComputeRoute accepted."
        )

        result_future = goal_handle.get_result_async()

        result_future.add_done_callback(
            self.compute_result
        )

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

        self.follow_path(result.path)

    # =======================================================
    # STEP 2 : FOLLOW PATH
    # =======================================================

    def follow_path(self, path):

        self.get_logger().info(
            "Waiting /follow_path ..."
        )

        if not self.follow_client.wait_for_server(timeout_sec=5.0):

            self.get_logger().error(
                "/follow_path unavailable!"
            )

            rclpy.shutdown()
            return

        goal = FollowPath.Goal()

        goal.path = path

        # gunakan plugin default
        goal.controller_id = ""
        goal.goal_checker_id = ""

        self.get_logger().info(
            "Sending path to Controller Server..."
        )

        future = self.follow_client.send_goal_async(
            goal,
            feedback_callback=self.follow_feedback
        )

        future.add_done_callback(
            self.follow_response
        )

    # =======================================================

    def follow_response(self, future):

        goal_handle = future.result()

        if not goal_handle.accepted:

            self.get_logger().error(
                "FollowPath rejected!"
            )

            rclpy.shutdown()
            return

        self.get_logger().info(
            "FollowPath accepted."
        )

        result_future = goal_handle.get_result_async()

        result_future.add_done_callback(
            self.follow_result
        )

    # =======================================================

    def follow_feedback(self, feedback_msg):

        fb = feedback_msg.feedback

        self.get_logger().info(
            f"Distance : {fb.distance_to_goal:.3f} m"
        )

        self.get_logger().info(
            f"Speed    : {fb.speed:.3f} m/s"
        )

    # =======================================================

    def follow_result(self, future):

        result = future.result()

        if result.status == GoalStatus.STATUS_SUCCEEDED:

            self.get_logger().info("")
            self.get_logger().info("========== SUCCESS ==========")

        elif result.status == GoalStatus.STATUS_ABORTED:

            self.get_logger().error("")
            self.get_logger().error("========== ABORTED ==========")

        elif result.status == GoalStatus.STATUS_CANCELED:

            self.get_logger().warn("")
            self.get_logger().warn("========== CANCELED ==========")

        else:

            self.get_logger().warn(
                f"Status = {result.status}"
            )

        rclpy.shutdown()


# ===========================================================

def main():

    rclpy.init()

    goal_id = 4

    if len(sys.argv) > 1:

        goal_id = int(sys.argv[1])

    node = FollowRoute(goal_id)

    rclpy.spin(node)


if __name__ == "__main__":
    main()