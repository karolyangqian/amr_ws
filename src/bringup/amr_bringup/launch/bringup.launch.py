import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_desc  = get_package_share_directory('amr_description')
    pkg_lidar = get_package_share_directory('ydlidar_ros2_driver')
    pkg_merger = get_package_share_directory('ros2_laser_scan_merger')
    pkg_discovery = get_package_share_directory('amr_discovery')

    urdf_file        = os.path.join(pkg_desc, 'urdf', 'amr.urdf.xacro')
    front_lidar_yaml = os.path.join(pkg_desc, 'config', 'front_lidar.yaml')
    rear_lidar_yaml  = os.path.join(pkg_desc,   'config', 'rear_lidar.yaml')
    ekf_yaml         = os.path.join(pkg_desc, 'config', 'ekf.yaml')
    merger_config    = os.path.join(pkg_merger, 'config', 'params.yaml')

    robot_desc = ParameterValue(Command(['xacro ', urdf_file]), value_type=str)

    args = [
        DeclareLaunchArgument('front_lidar_port', default_value='/dev/amr_lidar_front'),
        DeclareLaunchArgument('rear_lidar_port',  default_value='/dev/amr_lidar_rear'),
        DeclareLaunchArgument('motor_port',       default_value='/dev/amr_motor'),
        DeclareLaunchArgument('teensy_port',       default_value='/dev/amr_mcu'),
        DeclareLaunchArgument('wheel_separation',  default_value='0.445'),
        DeclareLaunchArgument('use_teensy',        default_value='true'),
        DeclareLaunchArgument('use_camera',        default_value='false'),
    ]

    # Beri akses ke semua port secara otomatis saat launch
    chmod_ports = ExecuteProcess(
        cmd=['bash', '-c',
             'sudo chmod 666 /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyUSB2 /dev/ttyACM0 2>/dev/null || true'],
        output='screen',
    )

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



    # Front LiDAR langsung ke /front_scan + pakai rear + merger
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
        condition=IfCondition(LaunchConfiguration('use_camera')),   
    )

    scan_relay = Node(
        package='amr_hardware',
        executable='scan_relay_node',
        name='scan_relay_node',
        output='screen',
    )

    # Odom: IMU gyro + cmd_vel_raw dead-reckoning
    odom_node = Node(
        package='amr_hardware',
        executable='odom_node',
        name='odom_node',
        parameters=[{
            'wheel_base': LaunchConfiguration('wheel_separation'),
            'wheel_circ': 0.359,
            'publish_tf': False,
            'odom_frame': 'odom',
            'base_frame': 'base_link',
        }],
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

    # cmd_vel_raw → invert → /cmd_vel → Teensy → ZLAC
    cmd_vel_inverter = Node(
        package='amr_hardware',
        executable='cmd_vel_inverter_node',
        name='cmd_vel_inverter_node',
        output='screen',
    )

    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        parameters=[ekf_yaml],
        output='screen',
    )

    estop = Node(
        package='amr_hardware',
        executable='emergency_stop_node',
        name='emergency_stop_node',
        parameters=[{
            'stop_distance': 0.25,
            'warn_distance': 0.45,
            'scan_topic':    '/scan',
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

    imu_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='imu_static_tf',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', '0',
            '--frame-id', 'base_link', '--child-frame-id', 'imu_link',
        ],
    )

    # zlac ditrue false aja - Rein
    # udah ya rein - bri

    zlac_driver = Node(
        package='amr_hardware',
        executable='zlac_driver_node',
        name='zlac_driver_node',
        parameters=[{
            'port':            LaunchConfiguration('motor_port'),
            'accel_time_ms':   200,
            'decel_time_ms':   200,
            'cmd_vel_timeout': 1000.0,
            'max_reg':         250,
        }],
        output='screen',
        condition=UnlessCondition(LaunchConfiguration('use_teensy')),
    )

    # Delay 3 detik agar chmod dan node lain selesai init sebelum ZLAC konek
    zlac_delayed = TimerAction(period=3.0, actions=[zlac_driver])

    discovery_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_discovery, 'launch', 'discovery.launch.py')
        )
    )

    return LaunchDescription(args + [
        chmod_ports,
        rsp,
        jsp,
        lidar_front,
        lidar_rear,
        laser_merger,
        odom_node,
        wheel_odom,
        imu_fixer,
        cmd_vel_inverter,
        ekf,
        # estop,
        imu_static_tf,
        pc_to_scan,
        scan_relay,
        zlac_delayed,
        discovery_launch,
    ])
