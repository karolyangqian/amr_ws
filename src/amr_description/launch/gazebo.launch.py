import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg        = get_package_share_directory('amr_description')
    pkg_gazebo = get_package_share_directory('gazebo_ros')
    
    urdf_file  = os.path.join(pkg, 'urdf', 'amr.urdf.xacro')
    rviz_file  = os.path.join(pkg, 'rviz', 'amr_config.rviz')
    
    # KUNCI UTAMA: Kita arahkan langsung ke root instalasi Gazebo 11
    world_file = '/usr/share/gazebo-11/worlds/willowgarage.world'

    robot_desc = ParameterValue(Command(['xacro ', urdf_file]), value_type=str)

    return LaunchDescription([
        # Load Willow Garage World
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_gazebo, 'launch', 'gazebo.launch.py')
            ),
            # Lempar argumen world ke Gazebo
            launch_arguments={'world': world_file}.items()
        ),

        # Robot State Publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_desc, 'use_sim_time': True}],
            output='screen'
        ),

        # Spawn robot di tengah ruangan utama Willow Garage
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-topic', 'robot_description',
                '-entity', 'amr',
                '-x', '0.0', # <-- Kembalikan ke 0.0
                '-y', '0.0', # <-- Kembalikan ke 0.0
                '-z', '0.15'
            ],
            output='screen'
        ),

        # Buka RViz2 Otomatis
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_file],
            parameters=[{'use_sim_time': True}],
            output='screen'
        ),
    ])