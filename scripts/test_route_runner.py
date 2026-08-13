#!/usr/bin/env python3
"""test_route_runner.py

Utility script that sends a goal to the Nav2 *ComputeAndTrackRoute* action.
It requests the route graph for the given ``goal_id`` (default 4) and lets the
Nav2 stack handle the actual navigation.  The script uses ROS‑2 asynchronous
callbacks, which avoids the dead‑lock that occurs when ``spin_until_future_complete``
is called sequentially in a single thread.

Usage:
    source /opt/ros/humble/setup.bash
    source install/setup.bash
    python3 scripts/test_route_runner.py [goal_id]

The script will log the progress and exit when the navigation finishes.
"""

import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from nav2_msgs.action import ComputeAndTrackRoute


class RouteRunner(Node):
    """Node that requests a route and lets Nav2 execute it.

    It connects to the ``/compute_and_track_route`` action server, sends a goal,
    and prints status messages via the ROS logger.
    """

    def __init__(self, goal_id: int):
        super().__init__('test_route_runner')
        self.goal_id = goal_id
        self._client = ActionClient(self, ComputeAndTrackRoute,
                                    '/compute_and_track_route')
        # Start the process after a short delay so ROS is fully up
        self.timer = self.create_timer(0.5, self._start)

    def _start(self):
        self.timer.cancel()  # run only once
        if not self._client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Action server /compute_and_track_route not available')
            rclpy.shutdown()
            return

        goal_msg = ComputeAndTrackRoute.Goal()
        goal_msg.goal_id = self.goal_id
        goal_msg.use_poses = False
        goal_msg.use_start = False
        self.get_logger().info(f'Sending ComputeAndTrackRoute goal_id={self.goal_id}')
        send_future = self._client.send_goal_async(goal_msg)
        send_future.add_done_callback(self._goal_response_cb)

    def _goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected by route_server')
            rclpy.shutdown()
            return
        self.get_logger().info('Goal accepted – waiting for result…')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._result_cb)

    def _result_cb(self, future):
        result = future.result().result
        # ``result.success`` is a boolean field in ComputeAndTrackRoute.Result
        if getattr(result, 'success', False) or getattr(result, 'status', 0) == 0:
            self.get_logger().info('Navigation completed successfully')
        else:
            self.get_logger().warn('Navigation finished with failure')
        rclpy.shutdown()


def main(argv=None):
    rclpy.init()
    goal_id = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    node = RouteRunner(goal_id)
    rclpy.spin(node)

if __name__ == '__main__':
    main()
