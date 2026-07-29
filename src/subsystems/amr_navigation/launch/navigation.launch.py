import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, LifecycleNode


def generate_launch_description():
    pkg_desc = get_package_share_directory('amr_navigation')
    pkg_nav2 = get_package_share_directory('nav2_bringup')

    default_map = os.path.join(pkg_desc, 'maps', 'peta_ruangan_baru.yaml')
    nav2_params = os.path.join(pkg_desc, 'config', 'nav2_params.yaml')
    default_rviz_cfg = os.path.join(pkg_desc, 'rviz', 'navigation.rviz')

    # --- Launch Arguments ---
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
        'rviz',
        default_value='true',
        description='Launch RViz navigation view'
    )

    rviz_cfg_arg = DeclareLaunchArgument(
        'rviz_config',
        default_value=default_rviz_cfg,
        description='Full path to the RViz configuration file'
    )

    # Launch Configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    show_rviz = LaunchConfiguration('rviz')
    rviz_config_file = LaunchConfiguration('rviz_config')

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

    # ============================================================
    # 10. RViz2 - Visualisasi dengan panel 2D Pose Estimate & Nav2 Goal
    # ============================================================
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_nav',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(show_rviz)
    )

    # ============================================================
    # LAUNCH DESCRIPTION
    # ============================================================
    return LaunchDescription([
        # Arguments
        map_arg,
        use_sim_time_arg,
        rviz_arg,
        rviz_cfg_arg,

        # nav2 bringup
        nav2,

        # RViz
        rviz_node,
    ])
