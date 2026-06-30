import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('amr_mission')
    default_stations = os.path.join(pkg, 'config', 'stations.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'stations_yaml',
            default_value=default_stations,
            description='Path ke file YAML yang berisi koordinat stasiun',
        ),

        Node(
            package='amr_mission',
            executable='mission_executor_node',
            name='mission_executor_node',
            parameters=[LaunchConfiguration('stations_yaml')],
            output='screen',
            emulate_tty=True,
        ),
    ])
