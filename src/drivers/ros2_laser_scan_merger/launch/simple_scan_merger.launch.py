import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_merger = get_package_share_directory('ros2_laser_scan_merger')
    config = os.path.join(pkg_merger, 'config', 'simple_scan_merger.yaml')

    return LaunchDescription([
        Node(
            package='ros2_laser_scan_merger',
            executable='simple_scan_merger',
            name='simple_scan_merger',
            parameters=[config],
            output='screen',
            respawn=True,
            respawn_delay=2.0,
        )
    ])
