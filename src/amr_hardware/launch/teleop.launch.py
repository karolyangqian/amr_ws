from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('port',             default_value='/dev/ttyUSB2'),
        DeclareLaunchArgument('wheel_radius',     default_value='0.064'),
        DeclareLaunchArgument('wheel_separation', default_value='0.58'),
        DeclareLaunchArgument('max_rpm',          default_value='150.0'),
        DeclareLaunchArgument('linear_speed',     default_value='0.3'),
        DeclareLaunchArgument('angular_speed',    default_value='0.5'),

        # Driver node: /cmd_vel → ZLAC RPM
        Node(
            package='amr_hardware',
            executable='zlac_driver_node',
            name='zlac_driver_node',
            parameters=[{
                'port':             LaunchConfiguration('port'),
                'wheel_radius':     LaunchConfiguration('wheel_radius'),
                'wheel_separation': LaunchConfiguration('wheel_separation'),
                'max_rpm':          LaunchConfiguration('max_rpm'),
            }],
            output='screen',
        ),

        # Keyboard teleop: keyboard → /cmd_vel
        # Jalankan di terminal yang sama (butuh stdin interaktif)
        Node(
            package='amr_hardware',
            executable='teleop_keyboard_node',
            name='teleop_keyboard_node',
            parameters=[{
                'linear_speed':  LaunchConfiguration('linear_speed'),
                'angular_speed': LaunchConfiguration('angular_speed'),
            }],
            output='screen',
        ),
    ])
