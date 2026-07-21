import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_amr = get_package_share_directory('amr_description')
    pkg_slam = get_package_share_directory('slam_toolbox')

    slam_params_file = os.path.join(
        pkg_amr,
        'config',
        'mapper_params_online_async.yaml'
    )

    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    use_lifecycle_manager = LaunchConfiguration('use_lifecycle_manager')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true'
        ),

        DeclareLaunchArgument(
            'autostart',
            default_value='true',
            description='Automatically configure and activate slam_toolbox'
        ),

        DeclareLaunchArgument(
            'use_lifecycle_manager',
            default_value='false',
            description='Use lifecycle manager for slam_toolbox'
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_slam, 'launch', 'online_async_launch.py')
            ),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'autostart': autostart,
                'use_lifecycle_manager': use_lifecycle_manager,
                'slam_params_file': slam_params_file,
            }.items()
        ),
    ])