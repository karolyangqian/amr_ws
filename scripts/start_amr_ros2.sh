#!/bin/bash
# Source the main ROS 2 installation
source /opt/ros/humble/setup.bash

# Source your specific workspace (if applicable)
source /home/amr/amr_ws/install/setup.bash

# Set specific ROS environment variables
export ROS_DOMAIN_ID=0

# Execute the launch command
ros2 launch amr_bringup bringup.launch.py
ros2 launch amr_navigation navigation.launch.py rviz:=false