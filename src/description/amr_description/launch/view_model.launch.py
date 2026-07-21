import os
from ament_index_python.packages import get_package_share_directory
from launch_ros.parameter_descriptions import ParameterValue
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command


def generate_launch_description():
    pkg = get_package_share_directory('amr_description')
    urdf_file = os.path.join(pkg, 'urdf', 'amr.urdf.xacro')
    rviz_file = os.path.join(pkg, 'rviz', 'amr_config.rviz')

    front_lidar_param = os.path.join(pkg, 'config', 'front_lidar.yaml')
    rear_lidar_param  = os.path.join(pkg, 'config', 'rear_lidar.yaml')

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': ParameterValue(
                Command(['xacro ', urdf_file]), value_type=str)}],
            output='screen'
        ),

        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            output='screen'
        ),

        # Node(
        #     package='joint_state_publisher',
        #     executable='joint_state_publisher',
        #     parameters=[{'robot_description': ParameterValue(
        #         Command(['xacro ', urdf_file]), value_type=str)}],
        #     output='screen'
        # ),

        Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            name='ydlidar_front_node',
            parameters=[front_lidar_param],
            remappings=[('/scan', '/front_scan')],
            output='screen'
        ),

        Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            name='ydlidar_rear_node',
            parameters=[rear_lidar_param],
            remappings=[('/scan', '/rear_scan')],
            output='screen'
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_file],
            output='screen'
        ),
    ])