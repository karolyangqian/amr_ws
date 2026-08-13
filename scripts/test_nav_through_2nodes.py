#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateThroughPoses
from action_msgs.msg import GoalStatus


class TestNavigateThroughPoses(Node):

    def __init__(self):
        super().__init__("test_nav_through_2nodes")

        self.client = ActionClient(
            self,
            NavigateThroughPoses,
            "/navigate_through_poses"
        )

        self.last_remaining = -1

        self.timer = self.create_timer(1.0, self.send_goal)

    def send_goal(self):

        self.timer.cancel()

        self.get_logger().info("Waiting for NavigateThroughPoses server...")

        if not self.client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("NavigateThroughPoses server not available!")
            rclpy.shutdown()
            return

        goal = NavigateThroughPoses.Goal()

        stamp = self.get_clock().now().to_msg()

        # =====================================================
        # NODE 1
        # =====================================================

        p1 = PoseStamped()

        p1.header.frame_id = "map"
        p1.header.stamp = stamp

        p1.pose.position.x = -5.8108
        p1.pose.position.y = 2.4441
        p1.pose.position.z = 0.0

        p1.pose.orientation.x = 0.0
        p1.pose.orientation.y = 0.0
        p1.pose.orientation.z = 0.6275439653744435
        p1.pose.orientation.w = 0.7758

        # =====================================================
        # NODE 2
        # =====================================================

        p2 = PoseStamped()

        p2.header.frame_id = "map"
        p2.header.stamp = stamp

        p2.pose.position.x = -4.477038860321045
        p2.pose.position.y = 5.895949363708496
        p2.pose.position.z = 0.0

        p2.pose.orientation.x = 0.0
        p2.pose.orientation.y = 0.0
        p2.pose.orientation.z = -0.09348496919237513
        p2.pose.orientation.w = 0.9956206910943046



        # =====================================================
        # NODE 3
        # =====================================================

        p3 = PoseStamped()

        p3.header.frame_id = "map"
        p3.header.stamp = stamp

        p3.pose.position.x = -2.7824912071228027
        p3.pose.position.y = 4.461612701416016
        p3.pose.position.z = 0.0

        p3.pose.orientation.x = 0.0
        p3.pose.orientation.y = 0.0
        p3.pose.orientation.z = -0.7798853392723842
        p3.pose.orientation.w = 0.6259224054050135


        # =====================================================
        # NODE 4
        # =====================================================

        p4 = PoseStamped()

        p4.header.frame_id = "map"
        p4.header.stamp = stamp

        p4.pose.position.x = -2.602130889892578
        p4.pose.position.y = 1.6059731245040894
        p4.pose.position.z = 0.0

        p4.pose.orientation.x = 0.0
        p4.pose.orientation.y = 0.0
        p4.pose.orientation.z = 0.9933341724892616
        p4.pose.orientation.w = 0.1152702119590038

        goal.poses.append(p1)
        goal.poses.append(p2)
        goal.poses.append(p3)
        

        self.get_logger().info("======================================")
        self.get_logger().info("Sending NavigateThroughPoses")

        self.get_logger().info(
            f"Node 1 : ({p1.pose.position.x:.3f}, "
            f"{p1.pose.position.y:.3f})"
        )

        self.get_logger().info(
            f"Node 2 : ({p2.pose.position.x:.3f}, "
            f"{p2.pose.position.y:.3f})"
        )
        
        self.get_logger().info(
            f"Node 3 : ({p3.pose.position.x:.3f}, "
            f"{p3.pose.position.y:.3f})"
        )

        self.get_logger().info(
            f"Node 4 : ({p4.pose.position.x:.3f}, "
            f"{p4.pose.position.y:.3f})"
        )

        self.get_logger().info("======================================")

        future = self.client.send_goal_async(
            goal,
            feedback_callback=self.feedback_callback
        )

        future.add_done_callback(self.goal_response)

    def goal_response(self, future):

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error("Goal Rejected!")
            rclpy.shutdown()
            return

        self.get_logger().info("Goal Accepted!")

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):

        fb = feedback_msg.feedback

        pose = fb.current_pose.pose.position

        self.get_logger().info(
            f"Robot : ({pose.x:.3f}, {pose.y:.3f})"
        )

        remaining = fb.number_of_poses_remaining

        if remaining != self.last_remaining:

            self.last_remaining = remaining

            self.get_logger().info(
                f"Remaining Waypoints : {remaining}"
            )

            if remaining == 4:
                self.get_logger().warn("=========== NODE 1 TERCAPAI ===========")

            elif remaining == 3:
                self.get_logger().warn("=========== NODE 2 TERCAPAI ===========")

            elif remaining == 2:
                self.get_logger().warn("=========== NODE 3 TERCAPAI ===========")

            elif remaining == 1:
                self.get_logger().warn("=========== NODE 4 TERCAPAI ===========")

            elif remaining == 0:
                self.get_logger().warn("=========== NODE 5 TERCAPAI ===========")
    def result_callback(self, future):

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
                f"Status : {result.status}"
            )

        rclpy.shutdown()


def main():

    rclpy.init()

    node = TestNavigateThroughPoses()

    rclpy.spin(node)


if __name__ == "__main__":
    main()