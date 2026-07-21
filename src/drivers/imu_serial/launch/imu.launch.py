from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('port',     default_value='/dev/teensy'),
        DeclareLaunchArgument('baud',     default_value='115200'),
        DeclareLaunchArgument('frame_id', default_value='imu_link'),

        Node(
            package='imu_serial',
            executable='imu_serial_node',
            name='imu_serial_node',
            parameters=[{
                'port':     LaunchConfiguration('port'),
                'baud':     LaunchConfiguration('baud'),
                'frame_id': LaunchConfiguration('frame_id'),
            }],
            output='screen',
        ),
    ])
