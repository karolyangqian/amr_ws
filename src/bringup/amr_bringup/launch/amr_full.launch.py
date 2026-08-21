import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    bringup_dir = get_package_share_directory('amr_bringup')
    navigation_dir = get_package_share_directory('amr_navigation')

    bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_dir, 'launch', 'bringup.launch.py')
        )
    )

    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(navigation_dir, 'launch', 'navigation.launch.py')
        ),
        launch_arguments={'rviz': 'false'}.items()
    )

    # Jeda 3 detik menggunakan TimerAction untuk navigasi agar bringup (sensor/odometri) siap duluan
    delayed_navigation_launch = TimerAction(
        period=3.0,
        actions=[navigation_launch]
    )

    # 5. Susun LaunchDescription untuk dieksekusi oleh ROS 2
    return LaunchDescription([
        bringup_launch,
        delayed_navigation_launch
    ])
