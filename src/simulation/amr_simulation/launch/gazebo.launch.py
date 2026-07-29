import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_desc            = get_package_share_directory('amr_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    urdf_file = os.path.join(pkg_desc, 'urdf', 'amr.urdf.xacro')
    rviz_file = os.path.join(pkg_desc, 'rviz', 'amr_config.rviz')

    pkg_sim             = get_package_share_directory('amr_simulation')
    bridge_config = os.path.join(pkg_sim, 'config', 'gz_bridge.yaml')

    pkg_desc_share_parent = os.path.abspath(os.path.join(get_package_share_directory('amr_description'), '..'))
                                                                                      
    set_gz_resource_path = SetEnvironmentVariable(                                    
        name='IGN_GAZEBO_RESOURCE_PATH',                                              
        value=[pkg_desc_share_parent, ':', os.environ.get('IGN_GAZEBO_RESOURCE_PATH', '')] 
    )      

    world_arg = DeclareLaunchArgument(
        'world',
        # default_value='empty.sdf',
        default_value=os.path.join(pkg_sim, 'worlds', 'indoor.sdf'),
        description='Gazebo Sim world file or Fuel '
    )

    robot_desc = ParameterValue(Command(['xacro ', urdf_file]), value_type=str)

    # Launch Gazebo Sim
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': ['-r -v 4 ', LaunchConfiguration('world')]}.items()
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': True}],
        output='screen'
    )

    # Spawn Robot in Gazebo Sim
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'amr',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.15'
        ],
        output='screen'
    )

    # ROS-Gazebo Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config}],
        output='screen'
    )

    # RViz2
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    return LaunchDescription([
        set_gz_resource_path,
        world_arg,
        gz_sim,
        # robot_state_publisher,
        spawn_entity,
        bridge,
        rviz
    ])