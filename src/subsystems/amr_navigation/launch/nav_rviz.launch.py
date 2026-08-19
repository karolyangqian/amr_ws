import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, LifecycleNode


def generate_launch_description():
    pkg_nav = get_package_share_directory('amr_navigation')

    default_rviz_cfg = os.path.join(pkg_nav, 'rviz', 'navigation.rviz')


    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='False',
        description='Use simulation clock (true for Gazebo, false for hardware)'
    )


    rviz_cfg_arg = DeclareLaunchArgument(
        'rviz_config',
        default_value=default_rviz_cfg,
        description='Full path to the RViz configuration file'
    )

    # Launch Configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    rviz_config_file = LaunchConfiguration('rviz_config')


    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_nav',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )


    return LaunchDescription([
        # Arguments
        use_sim_time_arg,
        rviz_cfg_arg,

        # RViz
        rviz_node,
    ])
