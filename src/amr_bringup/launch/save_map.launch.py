import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    home = os.path.expanduser('~')
    default_path = os.path.join(home, 'peta_baru')

    return LaunchDescription([
        DeclareLaunchArgument(
            'map_path',
            default_value=default_path,
            description='Path output peta tanpa ekstensi, contoh: ~/peta_gudang'
        ),

        ExecuteProcess(
            cmd=[
                'ros2', 'run', 'nav2_map_server', 'map_saver_cli',
                '-f', LaunchConfiguration('map_path'),
            ],
            output='screen',
        ),
    ])
