import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.substitutions import Command, LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import LifecycleNode, Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_desc   = get_package_share_directory('amr_description')
    pkg_merger = get_package_share_directory('ros2_laser_scan_merger')

    urdf_file        = os.path.join(pkg_desc,   'urdf',   'amr.urdf.xacro')
    ekf_yaml         = os.path.join(pkg_desc, 'config', 'ekf.yaml')
    front_lidar_yaml = os.path.join(pkg_desc,   'config', 'front_lidar.yaml')
    rear_lidar_yaml  = os.path.join(pkg_desc,   'config', 'rear_lidar.yaml')
    merger_config    = os.path.join(pkg_merger, 'config', 'params.yaml')

    robot_desc = ParameterValue(Command(['xacro ', urdf_file]), value_type=str)

    args = [
        DeclareLaunchArgument('front_lidar_port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('rear_lidar_port',  default_value='/dev/ttyUSB1'),
        DeclareLaunchArgument('motor_port',       default_value='/dev/ttyUSB2'),
        DeclareLaunchArgument('teensy_port',      default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('use_teensy',        default_value='true'),
    ]

    # microros belum dipanggil - Rein
    # udah ya rein - bri
    microros_agent = ExecuteProcess(
        cmd=[
            'docker', 'run', '--rm', '--net=host',
            '--device', LaunchConfiguration('teensy_port'),
            'microros/micro-ros-agent:humble',
            'serial', '--dev', LaunchConfiguration('teensy_port'), '-b', '115200',
        ],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_teensy')),
    )

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
        condition=UnlessCondition(LaunchConfiguration('use_teensy')),
    )

    pc_to_scan = Node(
        package='pointcloud_to_laserscan',
        executable='pointcloud_to_laserscan_node',
        name='pointcloud_to_laserscan',
        parameters=[merger_config],
        output='screen',
        condition=UnlessCondition(LaunchConfiguration('use_teensy')),
    )

    scan_relay = Node(
        package='amr_hardware',
        executable='scan_relay_node',
        name='scan_relay_node',
        output='screen',
        condition=UnlessCondition(LaunchConfiguration('use_teensy')),
    )

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
        condition=UnlessCondition(LaunchConfiguration('use_teensy')),
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
        condition=IfCondition(LaunchConfiguration('use_teensy')),
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
        condition=IfCondition(LaunchConfiguration('use_teensy')),
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

    return LaunchDescription(args + [
        microros_agent,
        chmod_ports,
        rsp,
        jsp,
        lidar_front,
        lidar_rear,
        laser_merger,
        pc_to_scan,
        scan_relay,
        wheel_odom,
        odom_node,
        imu_fixer,
        imu_static_tf,
        cmd_vel_inverter,
        ekf,
        estop,
        zlac_delayed,
    ])
