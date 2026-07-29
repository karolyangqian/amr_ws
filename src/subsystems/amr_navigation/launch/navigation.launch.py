import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
<<<<<<< HEAD
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, LifecycleNode


def generate_launch_description():
    pkg_desc = get_package_share_directory('amr_description')

    default_map = os.path.join(pkg_desc, 'maps', 'peta_ruangan_baru.yaml')
    nav2_params = os.path.join(pkg_desc, 'config', 'nav2_params.yaml')
    default_rviz_cfg = os.path.join(pkg_desc, 'rviz', 'navigation.rviz')

    # --- Launch Arguments ---
=======
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_nav  = get_package_share_directory('amr_navigation')
    pkg_nav2 = get_package_share_directory('nav2_bringup')

    default_map = os.path.join(pkg_nav, 'maps', 'peta_ruangan_baru.yaml')
    nav2_params = os.path.join(pkg_nav, 'config', 'nav2_params.yaml')

>>>>>>> origin/refactor/tidy-up
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
<<<<<<< HEAD
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
    map_yaml = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')
    show_rviz = LaunchConfiguration('rviz')
    rviz_config_file = LaunchConfiguration('rviz_config')

    # ============================================================
    # 1. MAP SERVER - Load peta statis
    # ============================================================
    map_server_node = LifecycleNode(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'yaml_filename': map_yaml, 'use_sim_time': use_sim_time}
        ]
    )

    # ============================================================
    # 2. AMCL - Lokalisasi
    # ============================================================
    amcl_node = LifecycleNode(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': use_sim_time}
        ]
    )

    # ============================================================
    # 3. PLANNER SERVER - Global path (A*)
    # ============================================================
    planner_server_node = LifecycleNode(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': use_sim_time}
        ]
    )

    # ============================================================
    # 4. CONTROLLER SERVER - Local controller (DWB)
    # ============================================================
    controller_server_node = LifecycleNode(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': use_sim_time}
        ],
        remappings=[
            ('cmd_vel', '/cmd_vel_nav'),  # Output murni dari DWB langsung ke inverter
        ]
    )

    # ============================================================
    # 5. SMOOTHER SERVER - Haluskan global path
    # ============================================================
    smoother_server_node = LifecycleNode(
        package='nav2_smoother',
        executable='smoother_server',
        name='smoother_server',
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': use_sim_time}
        ]
    )

    # ============================================================
    # 6. BEHAVIOR SERVER - Recovery behaviors
    # ============================================================
    behavior_server_node = LifecycleNode(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': use_sim_time}
        ],
        remappings=[
            ('cmd_vel', '/cmd_vel_nav'),  # Recovery juga lewat inverter
        ]
    )

    # ============================================================
    # 7. BT NAVIGATOR - Eksekutor goal
    # ============================================================
    bt_navigator_node = LifecycleNode(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': use_sim_time}
        ]
    )

    # ============================================================
    # 8. Waypoint follower
    # ============================================================
    wp_follower_node = LifecycleNode(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower', 
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': use_sim_time}
        ],
    )

    # ============================================================
    # 9. VEL SMOOTHER
    # ============================================================
    vel_smoother_node = LifecycleNode(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother', 
        namespace='',
        output='screen',
        parameters=[
            nav2_params,
            {'use_sim_time': use_sim_time}
        ],
        remappings=[
            ('cmd_vel', 'cmd_vel_nav'), 
            ('cmd_vel_smoothed', 'cmd_vel')
        ]
    )

    # ============================================================
    # 10. LIFECYCLE MANAGER LOCALIZATION (map_server + amcl)
    # ============================================================
    lifecycle_manager_localization = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        namespace='',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': [
                'map_server',
                'amcl',
            ],
            'bond_timeout': 20.0,
            'attempt_respawn_reconnection': True,
            'bond_respawn_max_duration': 30.0,
        }]
    )

    # ============================================================
    # 11. LIFECYCLE MANAGER NAVIGATION (stack navigasi)
    # ============================================================
    lifecycle_manager_navigation = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        namespace='',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': [
                'planner_server',
                'controller_server',
                'smoother_server',
                'behavior_server',
                'bt_navigator',
                'waypoint_follower',  
                'velocity_smoother',  
            ],
            'bond_timeout': 20.0,
            'attempt_respawn_reconnection': True,
            'bond_respawn_max_duration': 30.0,
        }]
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

        # Nav2 Lifecycle Nodes
        map_server_node,
        amcl_node,
        planner_server_node,
        controller_server_node,
        smoother_server_node,
        behavior_server_node,
        bt_navigator_node,
        wp_follower_node,
        vel_smoother_node,

        # Lifecycle Managers
        lifecycle_manager_localization,
        lifecycle_manager_navigation,

        # RViz
        rviz_node,
    ])
=======
        'rviz', default_value='true', description='Launch RViz navigation view'
    )

    rviz_cfg = os.path.join(pkg_nav, 'rviz', 'navigation.rviz')

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
>>>>>>> origin/refactor/tidy-up
