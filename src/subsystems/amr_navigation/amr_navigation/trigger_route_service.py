#!/usr/bin/env python3

import os
import subprocess
import rclpy
from rclpy.node import Node
from amr_msgs.srv import TriggerRoute


class TriggerRouteService(Node):

    def __init__(self):
        super().__init__('trigger_route_service')

        self.srv = self.create_service(
            TriggerRoute,
            '/trigger_route',
            self.handle_trigger_route
        )

        self.get_logger().info('✓ TriggerRoute Service Server is online (Explicit Dual-Node Mode).')

    def handle_trigger_route(self, request, response):
        goal_id = request.goal_node_id
        start_id = request.start_node_id

        self.get_logger().info(
            f"Service Request Received: Start Node ID = {start_id} ➔ Goal Node ID = {goal_id}"
        )

        # 1. Validation Guard: Check explicit parameters
        if start_id < 0 or goal_id < 0:
            response.success = False
            response.message = f"Invalid Node IDs received: start_node_id={start_id}, goal_node_id={goal_id}. Both must be >= 0."
            self.get_logger().error(response.message)
            return response

        if start_id == goal_id:
            response.success = False
            response.message = f"Start Node ID ({start_id}) and Goal Node ID ({goal_id}) are identical."
            self.get_logger().warn(response.message)
            return response

        # 2. Locate script path
        script_path = os.path.join(
            './scripts/follow_route.py'
        )

        if not os.path.exists(script_path):
            response.success = False
            response.message = f"Execution script not found at: {script_path}"
            self.get_logger().error(response.message)
            return response

        # 3. Construct command: python3 scripts/follow_route.py <goal_id> <start_id>
        cmd = ['python3', script_path, str(goal_id), str(start_id)]

        try:
            self.get_logger().info(f"Executing command: {' '.join(cmd)}")

            # Execute subprocess and capture output logs
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Stream stdout line by line to terminal log
            if process.stdout:
                for line in process.stdout:
                    line_str = line.strip()
                    if line_str:
                        self.get_logger().info(f"[follow_route]: {line_str}")

            process.wait()

            # 4. Check exit code status
            if process.returncode == 0:
                response.success = True
                response.message = f"Successfully navigated from Node {start_id} to Node {goal_id}"
                self.get_logger().info(f"✓ {response.message}")
            else:
                response.success = False
                response.message = f"follow_route.py failed with exit code {process.returncode}"
                self.get_logger().error(f"✕ {response.message}")

        except Exception as e:
            response.success = False
            response.message = f"Execution exception occurred: {str(e)}"
            self.get_logger().error(response.message)

        return response


def main(args=None):
    rclpy.init(args=args)
    node = TriggerRouteService()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()