#!/usr/bin/env python3
import sys
import rclpy
from rclpy.node import Node
from nav2_msgs.srv import LoadMap
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QVBoxLayout, QLabel

class MapSwitcherGUI(QWidget):
    def __init__(self, node: Node):
        super().__init__()
        self.node = node
        # Create client attached to the ROS 2 node
        self.client = self.node.create_client(LoadMap, '/map_server/load_map')
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Nav2 Dynamic Map Switcher')
        self.resize(400, 120)

        layout = QVBoxLayout()
        self.label = QLabel('Current Map: Active', self)
        layout.addWidget(self.label)

        self.btn = QPushButton('Select & Load New Map (.yaml)', self)
        self.btn.clicked.connect(self.select_map)
        layout.addWidget(self.btn)

        self.setLayout(layout)

    def select_map(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Map YAML File", "", "YAML Files (*.yaml)"
        )
        if file_name:
            self.label.setText(f"Loading: {file_name}")
            self.change_map_service(file_name)

    def change_map_service(self, map_path):
        if not self.client.wait_for_service(timeout_sec=3.0):
            self.label.setText("Error: /map_server/load_map service offline!")
            return

        request = LoadMap.Request()
        request.map_url = map_path

        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self.node, future)

        if future.result() is not None:
            if future.result().result == 0:
                self.label.setText(f"Loaded: {map_path.split('/')[-1]}")
            else:
                self.label.setText(f"Failed (Error code: {future.result().result})")
        else:
            self.label.setText("Service call failed!")

def main(args=None):
    # Initialize ROS 2
    rclpy.init(args=args)
    ros_node = Node('rviz_map_switcher_gui')

    # Initialize PyQt Application
    app = QApplication(sys.argv)
    ex = MapSwitcherGUI(ros_node)
    ex.show()
    
    # Run GUI loop and shutdown ROS 2 on exit
    exit_code = app.exec_()
    ros_node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()