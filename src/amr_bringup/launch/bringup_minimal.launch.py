import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_desc   = get_package_share_directory('amr_description')
    pkg_merger = get_package_share_directory('ros2_laser_scan_merger')

    urdf_file        = os.path.join(pkg_desc,   'urdf',   'amr.urdf.xacro')
    front_lidar_yaml = os.path.join(pkg_desc,   'config', 'front_lidar.yaml')
    rear_lidar_yaml  = os.path.join(pkg_desc,   'config', 'rear_lidar.yaml')
    merger_config    = os.path.join(pkg_merger, 'config', 'params.yaml')

    robot_desc = ParameterValue(Command(['xacro ', urdf_file]), value_type=str)

    args = [
        DeclareLaunchArgument('front_lidar_port', default_value='/dev/amr_lidar_front'),
        DeclareLaunchArgument('rear_lidar_port',  default_value='/dev/amr_lidar_rear'),
    ]

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': False}],
        output='screen',
    )

    jsp = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        parameters=[{'robot_description': robot_desc}],
        output='screen',
    )

    lidar_front = LifecycleNode(
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

    lidar_rear = LifecycleNode(
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

    laser_merger = Node(
        package='ros2_laser_scan_merger',
        executable='ros2_laser_scan_merger',
        name='ros2_laser_scan_merger',
        parameters=[merger_config],
        output='screen',
        respawn=True,
        respawn_delay=2.0,
    )

    pc_to_scan = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        parameters=[merger_config],
        output='screen',
    )

    scan_relay = Node(
        package='amr_hardware',
        executable='scan_relay_node',
        name='scan_relay_node',
        output='screen',
    )

    cmd_vel_inverter = Node(
        package='amr_hardware',
        executable='cmd_vel_inverter_node',
        name='cmd_vel_inverter_node',
        output='screen',
    )

    wheel_odom = Node(
        package='amr_hardware',
        executable='wheel_travel_odom_node',
        name='wheel_travel_odom_node',
        parameters=[{
            'wheel_separation': 0.445,
            'odom_frame':       'odom',
            'base_frame':       'base_footprint',
            'publish_tf':       True,
        }],
        output='screen',
    )

    imu_fixer = Node(
        package='amr_hardware',
        executable='imu_fixer_node',
        name='imu_fixer_node',
        parameters=[{'frame_id': 'imu_link'}],
        output='screen',
    )

    return LaunchDescription(args + [
        rsp,
        jsp,
        lidar_front,
        lidar_rear,
        laser_merger,
        pc_to_scan,
        scan_relay,
        wheel_odom,
        imu_fixer,
        cmd_vel_inverter,
    ])
