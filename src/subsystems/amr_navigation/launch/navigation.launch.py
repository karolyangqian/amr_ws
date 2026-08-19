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
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    default_map = os.path.join(pkg_nav, 'maps', 'lantai1.yaml')
    nav2_params = os.path.join(pkg_nav, 'config', 'nav2_params.yaml')
    default_rviz_cfg = os.path.join(pkg_nav, 'rviz', 'navigation.rviz')
    route_graph_file = os.path.join(pkg_nav,'config','route_graph_luar.geojson')

    # --- Launch Arguments ---
    map_arg = DeclareLaunchArgument(
        'map',
        default_value=default_map,
        description='Full path to map yaml file to load'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='False',
        description='Use simulation clock (true for Gazebo, false for hardware)'
    )

    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='False',
        description='Launch RViz navigation view'
    )

    rviz_cfg_arg = DeclareLaunchArgument(
        'rviz_config',
        default_value=default_rviz_cfg,
        description='Full path to the RViz configuration file'
    )

    slam_arg = DeclareLaunchArgument(
        'slam', 
        default_value='False',
        description='true = pakai /map dari slam_toolbox live; false = pakai saved map + AMCL'
    )

    # Launch Configurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    show_rviz = LaunchConfiguration('rviz')
    rviz_config_file = LaunchConfiguration('rviz_config')

    # Nav2 bringup lengkap: map_server + AMCL + navigation stack
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_bringup, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map':          LaunchConfiguration('map'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file':  nav2_params,
            'slam':         LaunchConfiguration('slam'),
            'autostart':    'True',
        }.items()
    )

    # ============================================================
    # NAV2 ROUTE SERVER
    # ============================================================
    route_server = LifecycleNode(
        package='nav2_route',
        executable='route_server',
        name='route_server',
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {
                'use_sim_time': use_sim_time,
                'graph_filepath': route_graph_file,
            }
        ]
    )
    # ============================================================
    # ROUTE SERVER LIFECYCLE MANAGER
    # ============================================================
    route_lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='route_lifecycle_manager',
        namespace='',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': [
                'route_server'
            ]
        }]
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2_nav',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
        condition=IfCondition(show_rviz)
    )


    return LaunchDescription([
        # Arguments
        map_arg,
        use_sim_time_arg,
        rviz_arg,
        rviz_cfg_arg,
        slam_arg,

        # nav2 bringup
        nav2,

        # Nav2 Route Server
        route_server,
        route_lifecycle_manager,

        # RViz
        rviz_node,
    ])
