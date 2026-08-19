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

## How to Run with Docker (Recommended)

Dengan Docker, Anda tidak perlu menginstal ROS 2 atau dependensi driver secara native pada PC host. Seluruh sistem robot, driver, dan visualisasi dapat berjalan langsung di container.

### 1. Setup Awal (Sekali saja)
Hubungkan perangkat USB (LiDAR, Motor, Teensy) ke PC, lalu jalankan script setup udev rules di host agar symlink `/dev/amr_*` terbuat:
```bash
bash scripts/setup_udev.sh
```

Izinkan akses GUI (RViz2) dari container ke X Server host:
```bash
xhost +local:docker
```

### 2. Jalankan Sistem
Di root workspace (`amr_ws`), jalankan perintah:
```bash
docker compose up --build
```
*Perintah ini akan membuild image, mengompilasi workspace menggunakan `colcon build`, mendeteksi hardware USB, menjalankan standalone `micro-ros-agent`, dan meluncurkan launch file `bringup.launch.py`.*

### 3. Membuka Terminal Baru (Development & Debugging)
Untuk melakukan debug, teleop, SLAM, atau perintah ROS 2 lainnya, buka tab terminal baru di host dan jalankan:
```bash
docker compose exec -u dev amr_ros2 bash
```
> [!IMPORTANT]
> Pastikan menggunakan opsi `-u dev` agar terminal berjalan sebagai user `dev`. Jika Anda masuk sebagai `root`, file-file yang ter-build atau terbuat di dalam workspace (yang di-mount dari host) akan dimiliki oleh root, yang dapat menyebabkan kendala permission di host.

Terminal ini sudah **otomatis di-source** dengan ROS 2 Humble dan workspace AMR. Contoh perintah yang bisa langsung Anda jalankan:
* **Teleop Keyboard**: `ros2 run teleop_twist_keyboard teleop_twist_keyboard`
* **SLAM Toolbox**: `ros2 launch amr_description amr_slam.launch.py`
* **RViz2**: `rviz2` (akan muncul di monitor host secara native)

## DIRECTORY STRUCTURE, FORMATS, AND CONVENTIONS

### SRC Directory Structure
```
./src
├── bringup         # Bringup launch (`launch/`) and final robot YAML params (`config/<subsystem_name>/`)
├── client          # Network communication protocols for telemetry and robot access via Flutter applications
├── description     # Physical robot description (transforms, URDF, STL, etc.)
├── drivers         # Packages managing hardware communication and hardware data preprocessing
├── interfaces      # .msg, .action, .srv
├── missions        # Robot mission configurations
└── subsystems      # Robot subsystems: localization, navigation, SLAM, odometry, vision, safety, etc.
```

### Directory Hierarchy
```
./src
├── <package_category_folder>
│   └── <package_name>
```

### Naming Format
| Folder Location | Package Name (package.xml) | Example
| --- | --- | --- | 
| `interfaces/` | `<robot>_<domain>_interfaces` | `amr_mission_interfaces` |
| `drivers/` | `<vendor>_<device>_driver` or `<protocol>_bridge` | `teensy_mcu_driver` or `socketcan_bridge` |
| `subsystems/` | `<robot>_<subsystem>` | `amr_navigation` |
| `bringup/` | `<robot>_bringup` | `amr_bringup` |

## How to Setup (Native)
1. Install all ROS 2 dependencies:
    ```bash
    rosdep install --from-paths src --ignore-src -r -y
    ```
2. Clone and build YDLidar-SDK:
    ```bash
    git clone https://github.com/YDLIDAR/YDLidar-SDK.git
    cd YDLidar-SDK
    mkdir build
    cd build
    cmake ..
    make
    sudo make install
    ```
3. Build the ROS 2 workspace
    ```bash
    cd amr_ws
    colcon build --symlink-install
    ```
4. Source the project from inside the workspace `amr_ws`
    ```bash
    source install/setup.bash
    ```
5. Ready to go

## Features and How to Run Each
### 1. Feature SLAM Mapping

0. Prepare 4 terminal and setup each terminal
    ```bash
    cd amr_ws
    ```
    
1. Source each terminal
    ```bash
    source /opt/ros/humble/setup.bash
    source ./install/setup.bash
    ```

2. In terminal 1, launch all hardware (bringup the system)
    ```bash
    ros2 launch amr_bringup bringup.launch.py \
    front_lidar_port:=/dev/ttyUSB0 \
    rear_lidar_port:=/dev/ttyUSB1 \
    motor_port:=/dev/ttyUSB2
    ```

3. In terminal 2, run Launch SLAM Toolbox
    ```bash
    ros2 launch amr_navigation amr_slam.launch.py
    ```
    Wait until the error disappear from the log `slam_toolbox`.

4. In terminal 3, run Teleop Keyboard / Wifi Node

    ```bash
    ros2 run amr_teleop teleop_keyboard_node # if using keyboard
    ```
    or 
    ```bash
    ros2 run amr_teleop teleop_wifi_node # if using wifi
    ```

5. In terminal 4, save map after mapping.
    **Don't End the Nodes before**
    ```bash
    ros2 launch amr_bringup save_map.launch.py \
        map_path:=$HOME/map_$(date +%Y%m%d)
    ```
    This will result in two files: `map_YYYYMMDD.pgm` dan `map_YYYYMMDD.yaml`.

### 2. Feature Nav2
0. Prepare 2 terminal and setup each terminal
    ```bash
    cd amr_ws
    ```
    
1. Source each terminal
    ```bash
    source /opt/ros/humble/setup.bash
    source ./install/setup.bash
    ```

2. In terminal 1, launch all hardware (bringup the system)
    ```bash
    ros2 launch amr_bringup bringup.launch.py \
    front_lidar_port:=/dev/ttyUSB0 \
    rear_lidar_port:=/dev/ttyUSB1 \
    motor_port:=/dev/ttyUSB2
    ```
3. In terminal 2, launch navigation
    ```bash
    ros2 launch amr_navigation navigation.launch.py \
    map:=$HOME/map_YYYYMMDD.yaml \ 
    slam:=false \ # if true, it will open slam_toolbox for SLAM
    use_sim_time:=false # make it true if using gazebo, else keep it
    ```
    Then, you may:  
    a. In RViz, click **2D Pose Estimate**  
    b. Click and drag at the robot's current position on the map (pointing in the direction the robot is facing)  
    c. Move the robot slightly using teleop → AMCL will converge  

## Quick Troubleshooting

| Symptom | Possible Cause | Fix |
|---|---|---|
| TF error `odom → base_link` | EKF not receiving `/imu/data` | Check Teensy LED, check `ros2 topic hz /imu/data` |
| Robot does not move during teleop | ZLAC not enabled | Check Terminal 1 logs, try reconnecting motor USB |
| Map not forming / completely black | LiDAR not publishing `/scan` | `ros2 topic hz /scan` — should be ~10 Hz |
| `[FAIL] ZLAC motor not found` | Incorrect port | Check `ls /dev/ttyUSB*`, adjust launch arguments |
| Teensy LED flashing rapidly | BNO080 not detected | Check I2C wiring (SDA=18, SCL=19, PS0=GND, PS1=GND) |
| Nav2 won't send goal | Initial pose not set | Repeat "2D Pose Estimate" step |

## Authors
1. Reinhard Iven Wiennata (13223009)
2. Karol Yangqian Poetracahya (13523093)
3. Brian A. Hadian (13523048)


## Command fast 
### Terminal 1 
```
# 1. Beri izin port
sudo chmod 666 /dev/ttyUSB* /dev/ttyACM*

# 2. Masuk & source workspace
cd ~/Documents/rein_amr/amr_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

# 3. Launch Bringup
ros2 launch amr_bringup bringup.launch.py \
  front_lidar_port:=/dev/ttyUSB0 \
  rear_lidar_port:=/dev/ttyUSB1 \
  teensy_port:=/dev/ttyACM0
```


### Terminal 2
```
cd ~/Documents/rein_amr/amr_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch amr_navigation navigation.launch.py
```

### TErminal 3 
```
cd ~/Documents/rein_amr/amr_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 action send_goal /compute_and_track_route nav2_msgs/action/ComputeAndTrackRoute "{
  goal_id: 4,
  use_poses: false,
  use_start: false
}"    
```
```
# Pastikan semua node Nav2 dan route_server sudah hidup
source /opt/ros/humble/setup.bash
source install/setup.bash

# Kirim goal ke action yang memang ada
ros2 action send_goal /compute_and_track_route \
  nav2_msgs/action/ComputeAndTrackRoute \
  "{goal_id: 4, use_poses: false, use_start: false}"
```

```
sudo chmod 666 /dev/ttyACM0

sudo docker run --rm -it --net=host --privileged -v /dev:/dev microros/micro-ros-agent:humble serial --dev /dev/ttyACM0 -b 115200

```

### need to check akan mengeluarkan goal_id , use_poses ,use_start 
```
ros2 interface show nav2_msgs/action/ComputeRoute

```

### need to check akan mengeluarkan active [3]

```
ros2 lifecycle get /route_server

```


### track route 

```
cd ~/Documents/rein_amr/amr_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

python3 scripts/track_route.py 4

```


### need to check NAvigate through poses 
```
ros2 action list | grep navigate_through_poses
```

### debugging using two waypoint 
```
cd ~/Documents/rein_amr/amr_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

python3 scripts/test_nav_through_2nodes.py
```


## Command Simulation 
```
cd ~/Documents/rein_amr/amr_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

# Akan membuka Gazebo, memunculkan URDF Robot, menjalankan Nav2, dan RViz sekaligus
ros2 launch amr_bringup simulation.launch.py

```


### route editor 

```
cd ~/Documents/rein_amr/amr_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

python3 src/subsystems/amr_navigation/amr_navigation/route_editor.py
```


### route follow 
```
python3 scripts/follow_route.py 0
```