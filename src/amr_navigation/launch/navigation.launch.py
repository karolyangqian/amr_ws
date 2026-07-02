import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_desc = get_package_share_directory('amr_description')
    pkg_nav2 = get_package_share_directory('nav2_bringup')

    default_map = os.path.join(pkg_desc, 'maps', 'peta_ruangan_baru.yaml')
    nav2_params = os.path.join(pkg_desc, 'config', 'nav2_params.yaml')

    map_arg = DeclareLaunchArgument(
        'map',
        default_value=default_map,
        description='Full path to map yaml file to load'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock (true for Gazebo, false for hardware)'
    )

    rviz_arg = DeclareLaunchArgument(
        'rviz', default_value='true', description='Launch RViz navigation view'
    )

    rviz_cfg = os.path.join(pkg_desc, 'rviz', 'navigation.rviz')

    # Nav2 bringup lengkap: map_server + AMCL + navigation stack
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map':          LaunchConfiguration('map'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file':  nav2_params,
            'slam':         'False',
            'autostart':    'True',
        }.items()
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_cfg],
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}],
        condition=IfCondition(LaunchConfiguration('rviz')),
        output='screen',
    )

    return LaunchDescription([
        map_arg,
        use_sim_time_arg,
        rviz_arg,
        nav2,
        rviz,
    ])
