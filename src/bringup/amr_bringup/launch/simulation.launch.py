"""
simulation.launch.py
=====================
One-shot launch untuk mode simulasi Gazebo + Nav2 + Route Server.
TIDAK memanggil bringup.launch.py agar node hardware tidak dijalankan.

Usage:
    ros2 launch amr_bringup simulation.launch.py

Yang dijalankan (simulasi-only):
  1. Gazebo Ignition  (world indoor.sdf)
  2. ROS–Gazebo bridge
  3. Robot State Publisher
  4. Joint State Publisher
  5. Spawn robot
  6. EKF  (robot_localization)
  7. IMU static TF
  8. Nav2 navigation  (AMCL + route_server + costmap)
  9. RViz2
"""

import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    # ── Package directories ───────────────────────────────────────────────────
    pkg_sim        = get_package_share_directory('amr_simulation')
    pkg_desc       = get_package_share_directory('amr_description')
    pkg_nav        = get_package_share_directory('amr_navigation')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # ── File paths ────────────────────────────────────────────────────────────
    urdf_file  = os.path.join(pkg_desc, 'urdf', 'amr.urdf.xacro')
    rviz_file  = os.path.join(pkg_nav,  'rviz', 'navigation.rviz')
    bridge_cfg = os.path.join(pkg_sim,  'config', 'gz_bridge.yaml')
    world_file = os.path.join(pkg_sim,  'worlds', 'indoor.sdf')
    ekf_yaml   = os.path.join(pkg_nav,  'config', 'ekf.yaml')

    # ── Arguments ─────────────────────────────────────────────────────────────
    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Open RViz2 if true')

    slam_arg = DeclareLaunchArgument(
        'slam', default_value='False',
        description='Use SLAM instead of AMCL if true')

    map_arg = DeclareLaunchArgument(
        'map', default_value=os.path.join(pkg_nav, 'maps', 'gz_indoor.yaml'),
        description='Full path to map file')

    # ── Gazebo resource path ───────────────────────────────────────────────────
    pkg_desc_parent = os.path.abspath(os.path.join(pkg_desc, '..'))
    set_gz_resource_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=[pkg_desc_parent, ':',
               os.environ.get('IGN_GAZEBO_RESOURCE_PATH', '')])

    # ── Robot description ─────────────────────────────────────────────────────
    robot_desc = ParameterValue(
        Command(['xacro ', urdf_file]), value_type=str)

    # ── 1. Gazebo Ignition ────────────────────────────────────────────────────
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': f'-r -v 2 {world_file}'}.items())

    # ── 2. ROS–Gazebo bridge ──────────────────────────────────────────────────
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_cfg}],
        output='screen')

    # ── 3. Robot State Publisher ──────────────────────────────────────────────
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True,
        }],
        output='screen')

    # ── 4. Joint State Publisher ──────────────────────────────────────────────
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True,
        }],
        output='screen')

    # ── 5. Spawn robot in Gazebo ──────────────────────────────────────────────
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'amr',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.15',
        ],
        output='screen')

    # ── 6. EKF (robot_localization) ───────────────────────────────────────────
    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        parameters=[ekf_yaml, {'use_sim_time': True}],
        output='screen')

    # ── 7. IMU static TF ─────────────────────────────────────────────────────
    imu_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='imu_static_tf',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', '0',
            '--frame-id', 'base_link', '--child-frame-id', 'imu_link',
        ],
        parameters=[{'use_sim_time': True}])

    # ── 8. Nav2 navigation (AMCL + route_server + costmap) ───────────────────
    #    Delay 4 s agar Gazebo + RSP + bridge siap lebih dulu
    nav2_navigation = TimerAction(
        period=4.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_nav, 'launch', 'navigation.launch.py')),
                launch_arguments={
                    'use_sim_time': 'True',
                    'slam': LaunchConfiguration('slam'),
                    'rviz': 'False',
                    'map': LaunchConfiguration('map'),
                }.items()),
        ])

    # ── 9. RViz2 ─────────────────────────────────────────────────────────────
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': True}],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_rviz')))

    # ── 10. Scan Merger (for AMCL) ────────────────────────────────────────────
    pkg_merger = get_package_share_directory('ros2_laser_scan_merger')
    simple_scan_merger_config = os.path.join(pkg_merger, 'config', 'simple_scan_merger.yaml')
    
    simple_scan_merger = Node(
        package='ros2_laser_scan_merger',
        executable='simple_scan_merger',
        name='simple_scan_merger',
        parameters=[simple_scan_merger_config, {'use_sim_time': True}],
        output='screen'
    )

    return LaunchDescription([
        set_gz_resource_path,
        use_rviz_arg,
        slam_arg,
        map_arg,
        gz_sim,
        bridge,
        robot_state_publisher,
        joint_state_publisher,
        spawn_entity,
        ekf,
        imu_static_tf,
        simple_scan_merger,
        nav2_navigation,
        rviz,
    ])
