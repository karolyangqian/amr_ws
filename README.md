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
