#!/usr/bin/env python3

import sys
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from nav2_msgs.action import ComputeRoute, NavigateThroughPoses
from geometry_msgs.msg import PoseStamped

class RouteNavigator(Node):
    def __init__(self):
        super().__init__('route_navigator')
        
        # 1. Action Client for Route Server
        self._route_client = ActionClient(self, ComputeRoute, '/compute_route')
        
        # 2. Action Client for Nav2 Controller Stack
        self._nav_client = ActionClient(self, NavigateThroughPoses, '/navigate_through_poses')

    def execute_route(self, start_id, goal_id):
        # Wait for action servers
        self.get_logger().info("Waiting for /compute_route server...")
        self._route_client.wait_for_server()
        
        self.get_logger().info("Waiting for /navigate_through_poses server...")
        self._nav_client.wait_for_server()

        # Send goal to Route Server
        route_goal = ComputeRoute.Goal()
        route_goal.start_id = start_id
        route_goal.goal_id = goal_id

        self.get_logger().info(f"Computing route from Node {start_id} to Node {goal_id}...")
        future = self._route_client.send_goal_async(route_goal)
        rclpy.spin_until_future_complete(self, future)

        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Route computation goal rejected!")
            return

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        route_result = result_future.result().result

        # Extract Poses from Route
        poses = route_result.path.poses

        if not poses:
            self.get_logger().error("Route Server returned empty path!")
            return
        # Fix: Ensure every pose has the correct frame_id and timestamp
        for pose in poses:
            if not pose.header.frame_id:
                pose.header.frame_id = 'map'
            pose.header.stamp = self.get_clock().now().to_msg()

        self.get_logger().info(f"Route found with {len(poses)} waypoints. Sending to Nav2...")

        # Prepare NavigateThroughPoses Goal
        nav_goal = NavigateThroughPoses.Goal()
        nav_goal.poses = poses

        # Send to Nav2 NavigateThroughPoses action
        send_nav_future = self._nav_client.send_goal_async(
            nav_goal,
            feedback_callback=self._feedback_callback
        )
        rclpy.spin_until_future_complete(self, send_nav_future)
        nav_handle = send_nav_future.result()

        if not nav_handle.accepted:
            self.get_logger().error("Navigation goal rejected!")
            return

        self.get_logger().info("Robot is moving along the topological route...")
        nav_result_future = nav_handle.get_result_async()
        rclpy.spin_until_future_complete(self, nav_result_future)

        self.get_logger().info("Navigation completed!")

    def _feedback_callback(self, feedback_msg):
        distance = feedback_msg.feedback.distance_remaining
        self.get_logger().info(f"Distance remaining: {distance:.2f} m", throttle_duration_sec=2.0)


def main():
    rclpy.init()
    
    if len(sys.argv) < 3:
        print("Usage: ros2 run amr_navigation send_route_goal.py <start_id> <goal_id>")
        return

    start_id = int(sys.argv[1])
    goal_id = int(sys.argv[2])

    node = RouteNavigator()
    node.execute_route(start_id, goal_id)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()