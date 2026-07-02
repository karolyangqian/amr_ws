# AMR (Autonomous Mobile Robot) – Project Memory

## Project overview
- Ini adalah workspace utama ROS 2 untuk AMR (Autonomous Mobile Robot) gudang payload heavy-duty (≈1000 kg).
- Fokus: navigasi, kontrol, dan integrasi sensor/aktor di sisi host (NUC) menggunakan ROS 2 Humble.
- Robot: differential drive dengan driver motor ZLAC8015D (RS485), 2× YDLIDAR Tmini Pro (front/rear), 2× IMU BNO08x, 2× ultrasonic, dan Teensy 4.1 sebagai bridge micro-ROS.

## Environment & stack
- Host OS: Ubuntu 22.04 LTS.
- ROS: ROS 2 Humble, build dengan `colcon`.
- Workspace root: `~/Documents/Kuliah/SMT8/Penrek/Codebase/amr_ws`
- Struktur paket utama:
  - `amr_bringup`: launch file untuk bringup hardware + SLAM/Nav2.
  - `amr_hardware`: node hardware-level (cmd_vel inverter, emergency stop, IMU fixer, Teensy bridge, teleop, dsb).
  - `amr_description`: URDF/xacro, mesh, config SLAM (slam_toolbox), EKF, Nav2, RViz.
  - `amr_navigation`: launch & config Nav2 stack (global/local planner, costmap).
  - `amr_mission`: mission executor, station recorder.
  - `amr_msgs`: custom message & service untuk status/mission.
  - `amr_odom`: odometry khusus ZLAC (encoder-based) dan eksperimen odom lain.
  - `ydlidar_ros2_driver`: driver LiDAR YDLIDAR Tmini Pro.
  - dll. (imu_serial, ros2_laser_scan_merger, dsb).

- Peran hardware:
  - NUC: jalanin semua node ROS 2 + micro-ROS agent (via Docker).
  - Teensy 4.1: firmware micro-ROS, handle ZLAC (RS485), IMU, ultrasonic.
  - Motor driver ZLAC8015D: Modbus RTU via RS485 (Teensy atau USB-RS485 NUC).
  - LiDAR: 2× YDLIDAR via USB (CP210x), dibedakan dengan udev rules (KERNELS path).

- Ada repositori terpisah untuk firmware low-level di:
  - `~/Documents/Kuliah/SMT8/Penrek/Codebase/firmware_teensy`

## What I want Claude to help with (di folder ini)
- Menulis dan refactor node ROS 2 (Python/C++) untuk:
  - hardware interface (ZLAC driver node, Teensy bridge),
  - odometry (encoder + IMU + dead-reckoning),
  - integrasi LiDAR (single atau merge 2 LiDAR),
  - pipeline SLAM (slam_toolbox) dan Nav2 (global/local planner).
- Debugging:
  - topik (`ros2 topic list/echo/hz`),
  - TF frames (`map/odom/base_link/laser`),
  - masalah integrasi sensor/aktor (mis. LiDAR hilang, odom drift, TF mismatch).
- Mendesain, tuning, dan dokumentasi:
  - parameter odometry (wheel radius, wheel separation, linear_to_rpm/angular_to_rpm),
  - parameter Nav2 (costmap, DWB/TEB local planner, recovery),
  - konfigurasi EKF (robot_localization).
- Menyusun dan merangkum eksperimen:
  - SLAM run (peta gudang, peta ruangan),
  - uji odom (IMU-only vs encoder),
  - uji Nav2 (tracking, obstacle avoidance),
  - catatan tuning (goal → setup → run → observasi → kesimpulan).

## Workflow & boundaries
- Di direktori ini, fokus ke *host-side / ROS 2 stack*:
  - Launch file (amr_bringup, amr_description, amr_navigation).
  - Node Python/C++ di paket amr_*.
  - Konfigurasi YAML untuk SLAM, Nav2, EKF, sensor.
- Detail firmware MCU low-level (timing Modbus, interrupt, dsb.) berada di `firmware_teensy` dan **tidak dimodifikasi** dari sini kecuali saya minta eksplisit.
- Asumsi saat memberi perintah:
  - Saya berada di root workspace: `~/Documents/Kuliah/SMT8/Penrek/Codebase/amr_ws`
  - Build dengan:
    - `colcon build --symlink-install` (bisa dibatasi `--packages-select` kalau perlu).
  - Source environment:
    - `source install/setup.bash`
  - Launch contoh:
    - `ros2 launch amr_bringup bringup.launch.py`
    - `ros2 launch amr_bringup bringup_minimal.launch.py`
    - `ros2 launch amr_description amr_slam.launch.py`
    - `ros2 launch amr_navigation navigation.launch.py` / `navigation_minimal.launch.py`

- Prefer step-by-step debugging:
  - Cek dulu device di `/dev` (udev symlink: `/dev/amr_lidar_front`, `/dev/amr_lidar_rear`, `/dev/amr_teensy`, `/dev/amr_motor`).
  - Cek topic & TF sebelum menyarankan perubahan besar di kode.
  - Utamakan solusi incremental yang bisa diuji cepat (bukan refactor massal).

## Style & preferences
- Penjelasan: singkat, teknis, langsung ke poin (Bahasa Indonesia).
- Saat bantu eksperimen:
  - Strukturkan catatan: **goal → setup → run → observasi → kesimpulan → next step**.
  - Output mudah di-copy ke laporan atau markdown internal.
- Saat menyarankan perubahan:
  - Sebutkan file yang diubah (path relatif dari `amr_ws/src`).
  - Tunjukkan patch atau isi file secara lengkap jika perubahan besar.
  - Jelaskan risiko ke pipeline SLAM/Nav2 yang sudah ada.
