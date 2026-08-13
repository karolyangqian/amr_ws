"""
nav2_route_test.launch.py
==========================
Launch Nav2 + RViz dengan peta peta_ruangan_dalam.yaml untuk
menguji track_route.py / test_nav_through_2nodes.py TANPA Gazebo.

Usage:
    ros2 launch amr_bringup nav2_route_test.launch.py

Setelah launch:
  1. Klik "2D Pose Estimate" di RViz → klik posisi awal robot di peta
  2. Di terminal lain: python3 scripts/track_route.py 4
"""

import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    pkg_nav = get_package_share_directory('amr_navigation')

    # ── File paths ─────────────────────────────────────────────────────────────
    map_file     = os.path.join(pkg_nav, 'maps',   'peta_ruangan_dalam.yaml')
    nav2_params  = os.path.join(pkg_nav, 'config', 'nav2_params.yaml')
    rviz_file    = os.path.join(pkg_nav, 'rviz',   'navigation.rviz')
    route_graph  = os.path.join(pkg_nav, 'config', 'route_graph.geojson')

    # ── Nav2 full stack (AMCL + planner + controller + route_server) ───────────
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav, 'launch', 'navigation.launch.py')),
        launch_arguments={
            'use_sim_time': 'False',
            'map':          map_file,
            'slam':         'False',
            'rviz':         'False',   # RViz kita buka sendiri di bawah
        }.items())

    # ── RViz dengan config navigation ─────────────────────────────────────────
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': False}],
        output='screen')

    return LaunchDescription([
        nav2,
        rviz,
    ])
