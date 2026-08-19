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

        self.get_logger().info('✓ TriggerRoute Service Server is online.')

    def handle_trigger_route(self, request, response):
        goal_id = request.goal_node_id
        start_id = request.start_node_id

        self.get_logger().info(f"Service Request Received: Target Goal ID = {goal_id}")

        script_path = os.path.join(
            './scripts/follow_route.py'
        )

        if not os.path.exists(script_path):
            response.success = False
            response.message = f"Script not found at: {script_path}"
            self.get_logger().error(response.message)
            return response

        # Construct execution command
        cmd = ['python3', script_path, str(goal_id)]
        if start_id > 0:
            cmd.append(str(start_id))

        try:
            self.get_logger().info(f"Executing: {' '.join(cmd)}")

            # Synchronously wait for python script completion
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Stream output logs to ROS 2 terminal
            for line in process.stdout:
                line_str = line.strip()
                if line_str:
                    self.get_logger().info(f"[follow_route]: {line_str}")

            process.wait()

            if process.returncode == 0:
                response.success = True
                response.message = f"Successfully reached Node {goal_id}"
                self.get_logger().info(response.message)
            else:
                response.success = False
                response.message = f"Process failed with exit code {process.returncode}"
                self.get_logger().error(response.message)

        except Exception as e:
            response.success = False
            response.message = f"Execution exception: {str(e)}"
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