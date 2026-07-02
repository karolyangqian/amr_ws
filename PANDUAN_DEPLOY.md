# Panduan Deploy AMR — Lab

## Persiapan sebelum berangkat ke lab
- [ ] Firmware Teensy sudah di-upload (`pio run -t upload`)
- [ ] Laptop: `colcon build` sudah jalan tanpa error
- [ ] Bawa: kabel USB-A (LiDAR ×2, ZLAC ×1), USB-C / micro-USB (Teensy ×1)

---

## Fase 0 — Saat tiba di lab

### 0.1 Colokkan semua USB ke NUC (default assignment)
| Port | Perangkat |
|---|---|
| `/dev/ttyUSB0` | LiDAR depan (Tmini Pro) |
| `/dev/ttyUSB1` | LiDAR belakang (Tmini Pro) |
| `/dev/ttyUSB2` | Motor driver ZLAC8015D (RS485) |
| `/dev/ttyACM0` | Teensy 4.1 — IMU (opsional, jika terpasang) |

> Kalau urutan colok berbeda, port bisa bertukar.
> Cek dengan: `ls /dev/ttyUSB* /dev/ttyACM*`
> Lalu sesuaikan argumen launch di Fase 1.
>
> **Catatan:** Pastikan ModemManager tidak aktif:
> `sudo systemctl disable --now ModemManager`

### 0.2 Preflight check
```bash
source /opt/ros/humble/setup.bash
source ~/Documents/Kuliah/SMT8/Penrek/Codebase/amr_ws/install/setup.bash
bash ~/Documents/Kuliah/SMT8/Penrek/Codebase/amr_ws/scripts/preflight_check.sh
```
Semua `[OK]` sebelum lanjut. Kalau ada `[FAIL]`, selesaikan dulu.

---

## Fase 1 — Mapping (teleop keliling arena)

Butuh **3 terminal**. Source workspace di setiap terminal baru:
```bash
source /opt/ros/humble/setup.bash
source ~/Documents/Kuliah/SMT8/Penrek/Codebase/amr_ws/install/setup.bash
```

### Terminal 1 — Launch semua hardware
```bash
ros2 launch amr_bringup bringup.launch.py \
  front_lidar_port:=/dev/ttyUSB0 \
  rear_lidar_port:=/dev/ttyUSB1 \
  motor_port:=/dev/ttyUSB2
```
Tunggu sampai log tidak ada error merah. Ciri siap:
- `zlac_driver_node started on /dev/ttyUSB2`
- `zlac_odom_node started` ← dari driver node
- LiDAR berputar (cek fisik)
- LED Teensy **menyala solid** (agent tersambung)

### Terminal 2 — Launch SLAM Toolbox
```bash
ros2 launch amr_description amr_slam.launch.py
```
Tunggu log `slam_toolbox` muncul tanpa error.

### Terminal 3 — Teleop keyboard
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
Gunakan keyboard untuk gerakkan robot berkeliling arena.

> **Cek odom sebelum mulai gerak** (terminal baru):
> ```bash
> ros2 run tf2_ros tf2_echo odom base_link
> ```
> Harus muncul transform, bukan error.

### Verifikasi mapping berjalan
Buka RViz di terminal terpisah:
```bash
rviz2
```
Add display: `Map` (topic `/map`) dan `TF`. Peta harus terbentuk saat robot bergerak.

---

## Fase 2 — Simpan peta

Setelah selesai keliling, **jangan matikan node**. Di terminal baru:
```bash
ros2 launch amr_bringup save_map.launch.py \
  map_path:=$HOME/peta_gudang_$(date +%Y%m%d)
```
Akan menghasilkan dua file: `peta_gudang_YYYYMMDD.pgm` dan `.yaml`.

Salin map ke folder maps workspace:
```bash
cp ~/peta_gudang_*.pgm ~/peta_gudang_*.yaml \
   ~/Documents/Kuliah/SMT8/Penrek/Codebase/amr_ws/src/amr_description/maps/

# Build ulang agar map terdaftar di install/
cd ~/Documents/Kuliah/SMT8/Penrek/Codebase/amr_ws
colcon build --packages-select amr_description
source install/setup.bash
```

Matikan semua terminal dari Fase 1 & 2 (Ctrl+C).

---

## Fase 3 — Navigasi dengan waypoint

### Terminal 1 — Hardware (sama seperti Fase 1)
```bash
ros2 launch amr_bringup bringup.launch.py \
  front_lidar_port:=/dev/ttyUSB0 \
  rear_lidar_port:=/dev/ttyUSB1 \
  motor_port:=/dev/ttyUSB2
```

### Terminal 2 — Nav2 dengan peta yang sudah disimpan
```bash
ros2 launch amr_navigation navigation.launch.py \
  map:=$HOME/peta_gudang_YYYYMMDD.yaml
```
Atau pakai map default di workspace:
```bash
ros2 launch amr_navigation navigation.launch.py
```

Tunggu RViz terbuka dan Nav2 lifecycle node `active`.

### Terminal 3 — Set initial pose di RViz
1. Di RViz, klik **2D Pose Estimate**
2. Klik+drag di posisi robot sekarang di peta (arahkan ke heading robot)
3. Gerakkan robot sedikit dengan teleop → AMCL akan konvergen

### Terminal 3 — Jalankan misi waypoint
```bash
ros2 launch amr_mission mission.launch.py
```
Ikuti instruksi di terminal (pilih stasiun tujuan).

---

## Troubleshooting cepat

| Gejala | Kemungkinan penyebab | Fix |
|---|---|---|
| TF error `odom → base_link` | EKF tidak dapat `/imu/data` | Cek LED Teensy, cek `ros2 topic hz /imu/data` |
| Robot tidak bergerak saat teleop | ZLAC tidak enable | Cek log Terminal 1, coba reconnect USB motor |
| Peta tidak terbentuk / hitam semua | LiDAR tidak publish `/scan` | `ros2 topic hz /scan` — harus ~10 Hz |
| `[FAIL] Motor ZLAC tidak ditemukan` | Port salah | Cek `ls /dev/ttyUSB*`, sesuaikan argumen launch |
| LED Teensy berkedip cepat | BNO080 tidak terdeteksi | Cek wiring I2C (SDA=18, SCL=19, PS0=GND, PS1=GND) |
| Nav2 tidak mau kirim goal | Initial pose belum di-set | Ulangi langkah 2D Pose Estimate |

---

## Port assignment — cara identifikasi manual
```bash
# Colok satu perangkat, lalu:
dmesg | tail -5
# Cari baris: "ttyUSBx: USB Serial Device" atau "ttyACMx"
```
