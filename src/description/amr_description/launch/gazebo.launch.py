import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg        = get_package_share_directory('amr_description')
    pkg_gazebo = get_package_share_directory('gazebo_ros')

    urdf_file  = os.path.join(pkg, 'urdf', 'amr.urdf.xacro')
    rviz_file  = os.path.join(pkg, 'rviz', 'amr_config.rviz')

    world_arg = DeclareLaunchArgument(
        'world',
        default_value='/usr/share/gazebo-11/worlds/willowgarage.world',
        description='Full path to Gazebo world file'
    )

    robot_desc = ParameterValue(Command(['xacro ', urdf_file]), value_type=str)

    return LaunchDescription([
        world_arg,

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo, 'launch', 'gazebo.launch.py')
            ),
            launch_arguments={'world': LaunchConfiguration('world')}.items()
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_desc, 'use_sim_time': True}],
            output='screen'
        ),

        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-topic', 'robot_description',
                '-entity', 'amr',
                '-x', '0.0',
                '-y', '0.0',
                '-z', '0.15'
            ],
            output='screen'
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_file],
            parameters=[{'use_sim_time': True}],
            output='screen'
        ),
    ])