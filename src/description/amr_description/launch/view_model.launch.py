import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('amr_description')
    urdf_file = os.path.join(pkg, 'urdf', 'amr.urdf.xacro')
    rviz_file = os.path.join(pkg, 'rviz', 'amr_model_view.rviz')

    rviz_arg = DeclareLaunchArgument(
        'rviz_config',
        default_value=rviz_file,
        description='Path to the RViz config file'
    )

    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]), value_type=str
    )

    return LaunchDescription([
        rviz_arg,
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen'
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            output='screen'
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', LaunchConfiguration('rviz_config')],
            output='screen'
        ),
    ])