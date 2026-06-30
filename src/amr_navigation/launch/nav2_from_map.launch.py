import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_nav2 = get_package_share_directory('nav2_bringup')
    pkg_desc = get_package_share_directory('amr_description')

    nav2_params = os.path.join(pkg_desc, 'config', 'nav2_params_minimal.yaml')

    map_arg = DeclareLaunchArgument(
        'map',
        default_value='/home/amr/maps/lab_mapping_1.yaml',
        description='Full path to map yaml file'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false'
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': 'true',
            'map': LaunchConfiguration('map'),
            # slam tidak dipakai, kita pakai map + AMCL
            'slam': 'false',
            'params_file': nav2_params,
        }.items()
    )

    # RViz minimal (optional, kalau mau dari launch ini juga)
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=[],
        output='screen',
    )

    return LaunchDescription([map_arg, use_sim_time_arg, nav2, rviz])
