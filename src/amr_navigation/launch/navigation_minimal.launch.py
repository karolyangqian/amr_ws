"""
navigation_minimal.launch.py — Nav2 untuk skenario SLAM live / saved map.

Sequence:
  T1: ros2 launch amr_bringup bringup_minimal.launch.py
  T2: ros2 launch amr_description amr_slam.launch.py       ← mapping (opsional, kalau mau SLAM live)
  T3: ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/cmd_vel_raw
  T4: ros2 launch amr_navigation navigation_minimal.launch.py \
         slam:=False map:=/home/amr/maps/lab_mapping_1.yaml rviz:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.actions import SetRemap  # ← penting

def generate_launch_description():
    pkg_desc = get_package_share_directory('amr_description')
    pkg_nav2 = get_package_share_directory('nav2_bringup')

    # Pastikan nama file persis dengan yang ada di amr_description/config
    nav2_params = os.path.join(pkg_desc, 'config', 'nav2_params_minimal.yaml')

    args = [
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument(
            'slam', default_value='false',
            description='true = pakai /map dari slam_toolbox live; false = pakai saved map + AMCL'
        ),
        DeclareLaunchArgument(
            'map', default_value='',
            description='Path ke saved map.yaml (kosong = pakai slam live)'
        ),
        DeclareLaunchArgument('rviz', default_value='true'),
    ]

    nav2 = GroupAction([
        # Remap semua output /cmd_vel dari Nav2 ke /cmd_vel_nav2.
        # cmdvel_inverter_node (di bringup) akan subscribe /cmd_vel_nav2,
        # invert, lalu forward ke /cmd_vel (Teensy).
        SetRemap('/cmd_vel', '/cmd_vel_nav2'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_nav2, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'params_file':  nav2_params,
                'slam':         LaunchConfiguration('slam'),
                'autostart':    'True',
                'map':          LaunchConfiguration('map'),
            }.items(),
        ),
    ])

    rviz_cfg = os.path.join(pkg_desc, 'rviz', 'navigation.rviz')
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_cfg] if os.path.exists(rviz_cfg) else [],
        condition=IfCondition(LaunchConfiguration('rviz')),
        output='screen',
    )

    return LaunchDescription(args + [nav2, rviz])