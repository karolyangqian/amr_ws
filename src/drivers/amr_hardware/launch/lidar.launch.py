import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node


def generate_launch_description():
    pkg_hardware = get_package_share_directory('amr_hardware')
    pkg_merger = get_package_share_directory('ros2_laser_scan_merger')

    front_lidar_yaml = os.path.join(pkg_hardware, 'config', 'front_lidar.yaml')
    rear_lidar_yaml  = os.path.join(pkg_hardware, 'config', 'rear_lidar.yaml')
    merger_config    = os.path.join(pkg_merger, 'config', 'params.yaml')

    front_lidar_port_arg = DeclareLaunchArgument('front_lidar_port', default_value='/dev/amr_lidar_front')
    rear_lidar_port_arg  = DeclareLaunchArgument('rear_lidar_port',  default_value='/dev/amr_lidar_rear')

    ydlidar_front_lifecycle_node = LifecycleNode(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='lidar_front',
        namespace='/',
        parameters=[front_lidar_yaml,
                    {'port': LaunchConfiguration('front_lidar_port')}],
        remappings=[('/scan', '/front_scan')],
        output='screen',
        emulate_tty=True,
    )

    ydlidar_rear_lifecycle_node = LifecycleNode(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='lidar_rear',
        namespace='/',
        parameters=[rear_lidar_yaml,
                    {'port': LaunchConfiguration('rear_lidar_port')}],
        remappings=[('/scan', '/rear_scan')],
        output='screen',
        emulate_tty=True,
    )

    scan_merger_node = Node(
        package='ros2_laser_scan_merger',
        executable='ros2_laser_scan_merger',
        name='ros2_laser_scan_merger',
        parameters=[merger_config],
        output='screen',
        respawn=True,
        respawn_delay=2.0,
    )

    scan_relay_node = Node(
        package='amr_hardware',
        executable='scan_relay_node',
        name='scan_relay_node',
        output='screen',
    )

    return LaunchDescription([
        front_lidar_port_arg,
        rear_lidar_port_arg,

        # Front LiDAR (Tmini Pro) -> /front_scan
        ydlidar_front_lifecycle_node,

        # Rear LiDAR (Tmini Pro) -> /rear_scan
        ydlidar_rear_lifecycle_node,

        # Laser Scan Merger: /front_scan + /rear_scan -> /scan
        scan_merger_node,

        # Scan Relay: /scan (BEST_EFFORT) -> /scan_reliable (RELIABLE)
        # scan_relay_node,
    ])
