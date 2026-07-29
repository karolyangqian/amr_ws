from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('robot_id',             default_value=''),
        DeclareLaunchArgument('port',                 default_value='41234'),
        DeclareLaunchArgument('status_topic',         default_value='/robot/status'),
        DeclareLaunchArgument('battery_voltage_max',  default_value='-1.0'),
        DeclareLaunchArgument('status_stale_timeout', default_value='10.0'),

        Node(
            package='amr_discovery',
            executable='discovery_node',
            name='discovery_node',
            parameters=[{
                'robot_id':             LaunchConfiguration('robot_id'),
                'port':                 LaunchConfiguration('port'),
                'status_topic':         LaunchConfiguration('status_topic'),
                'battery_voltage_max':  LaunchConfiguration('battery_voltage_max'),
                'status_stale_timeout': LaunchConfiguration('status_stale_timeout'),
            }],
            output='screen',
        ),
    ])
