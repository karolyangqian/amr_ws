import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_desc  = get_package_share_directory('amr_description')
    pkg_lidar = get_package_share_directory('ydlidar_ros2_driver')

    urdf_file        = os.path.join(pkg_desc, 'urdf', 'amr.urdf.xacro')
    front_lidar_yaml = os.path.join(pkg_desc, 'config', 'front_lidar.yaml')
    ekf_yaml         = os.path.join(pkg_desc, 'config', 'ekf.yaml')

    robot_desc = ParameterValue(Command(['xacro ', urdf_file]), value_type=str)

    args = [
        DeclareLaunchArgument('front_lidar_port', default_value='/dev/amr_lidar_front'),
        DeclareLaunchArgument('wheel_separation',  default_value='0.445'),
        DeclareLaunchArgument('teensy_port',       default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('use_teensy',        default_value='true'),
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

    # Front LiDAR langsung ke /scan — tidak pakai rear + merger
    lidar_front = LifecycleNode(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='lidar_front',
        namespace='/',
        parameters=[front_lidar_yaml,
                    {'port': LaunchConfiguration('front_lidar_port')}],
        remappings=[('/scan', '/scan')],
        output='screen',
        emulate_tty=True,
    )

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
        condition=IfCondition(LaunchConfiguration('use_teensy')),
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

    return LaunchDescription(args + [
        rsp, jsp,
        lidar_front,
        microros_agent,
        odom_node,
        imu_fixer,
        cmd_vel_inverter,
        ekf,
        estop,
        imu_static_tf,
    ])
