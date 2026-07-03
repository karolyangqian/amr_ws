# amr_ws
Warehouse Autonomous Mobile Robot (AMR) written using ROS 2

## Project Dependencies
- https://github.com/mich1342/ros2_laser_scan_merger.git by mich1342
- https://github.com/YDLIDAR/ydlidar_ros2_driver.git by 
Shenzhen Yuedeng Technology Co.,Ltd.

## System Requirements
1. Linux Ubuntu 22.04
2. ROS 2 Humble
3. 2x YDLidar connected via USB
4. 1x Teensy connected via USB
5. ZLAC8105D Motor Driver
6. WiFi

## How to Setup
1. Install all ROS 2 dependencies:
    ```
    rosdep install --from-paths src --ignore-src -r -y
    ```
2. Clone and build YDLidar-SDK:
    ```
    git clone https://github.com/YDLIDAR/YDLidar-SDK.git
    cd YDLidar-SDK
    mkdir build
    cd build
    cmake ..
    make
    sudo make install
    ```
3. Build the ROS 2 workspace
    ```
    cd amr_ws
    colcon build --symlink install
    ```
4. Source the project from inside the workspace `amr_ws`
    ```
    source install/setup.bash
    ```
5. Ready to go


## Topic List 
### Emergency Stop button for Ramp System 
~ ros2 topic echo /es
'
