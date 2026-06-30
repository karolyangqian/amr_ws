#!/bin/bash
# Preflight check sebelum launch robot.
# Jalankan: bash amr_ws/scripts/preflight_check.sh
# Cek semua hardware dan ROS environment sudah siap.

PASS=0; FAIL=0; WARN=0

ok()   { echo "  [OK]   $1"; ((PASS++)); }
fail() { echo "  [FAIL] $1"; ((FAIL++)); }
warn() { echo "  [WARN] $1"; ((WARN++)); }

echo "=========================================="
echo "  AMR Preflight Check"
echo "=========================================="
echo ""

# ── 1. ROS2 Environment ─────────────────────────────────────────────────
echo "[ ROS2 Environment ]"
if [ -n "$ROS_DISTRO" ]; then
    ok "ROS_DISTRO = $ROS_DISTRO"
else
    fail "ROS2 belum di-source (source /opt/ros/humble/setup.bash)"
fi

WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$WS/install/setup.bash" ]; then
    ok "Workspace install ditemukan: $WS"
else
    fail "Workspace belum di-build: colcon build dulu"
fi
echo ""

# ── 2. USB Devices ──────────────────────────────────────────────────────
echo "[ USB Devices ]"

# Coba symlink dulu, fallback ke /dev/ttyUSBx
check_dev() {
    local sym="$1" fallback="$2" label="$3"
    if [ -e "$sym" ]; then
        ok "$label → $sym"
    elif [ -e "$fallback" ]; then
        warn "$label → $fallback (symlink $sym belum ada, jalankan setup_udev.sh)"
    else
        fail "$label tidak ditemukan ($sym / $fallback)"
    fi
}

check_dev /dev/amr_lidar_front /dev/ttyUSB0 "Lidar depan"
check_dev /dev/amr_lidar_rear  /dev/ttyUSB1 "Lidar belakang"
check_dev /dev/amr_motor       /dev/ttyUSB2 "Motor ZLAC8015D"
# Teensy opsional — tidak ada = warn saja
if [ -e /dev/amr_imu ] || [ -e /dev/ttyACM0 ]; then
    ok "Teensy IMU → $([ -e /dev/amr_imu ] && echo /dev/amr_imu || echo /dev/ttyACM0) (use_imu:=true)"
else
    warn "Teensy IMU tidak ditemukan (ok jika use_imu:=false)"
fi
echo ""

# ── 3. Permissions ──────────────────────────────────────────────────────
echo "[ Permissions ]"
if groups | grep -q "dialout"; then
    ok "User ada di group 'dialout'"
else
    fail "User tidak ada di group 'dialout' → sudo usermod -aG dialout $USER"
fi

if groups | grep -q "docker"; then
    ok "User ada di group 'docker'"
else
    warn "User tidak ada di group 'docker' (diperlukan untuk micro-ros-agent Docker)"
fi
echo ""

# ── 4. Required ROS packages ────────────────────────────────────────────
echo "[ ROS Packages ]"
PKGS="robot_state_publisher robot_localization nav2_bringup slam_toolbox joint_state_publisher"
for pkg in $PKGS; do
    if ros2 pkg list 2>/dev/null | grep -q "^${pkg}$"; then
        ok "$pkg"
    else
        fail "$pkg tidak terinstall → sudo apt install ros-humble-$pkg"
    fi
done
echo ""

# ── 5. AMR workspace packages ───────────────────────────────────────────
echo "[ AMR Packages ]"
AMR_PKGS="amr_msgs amr_hardware amr_odom amr_description amr_bringup amr_navigation amr_mission"
for pkg in $AMR_PKGS; do
    if [ -d "$WS/install/$pkg" ]; then
        ok "$pkg"
    else
        fail "$pkg belum di-build → colcon build --packages-select $pkg"
    fi
done
echo ""

# ── 6. Docker / micro-ROS ───────────────────────────────────────────────
echo "[ micro-ROS Agent ]"
if command -v micro_ros_agent_docker &>/dev/null; then
    ok "micro_ros_agent_docker tersedia"
else
    fail "micro_ros_agent_docker tidak ada → jalankan scripts/install_microros.sh"
fi

if docker images microros/micro-ros-agent 2>/dev/null | grep -q humble; then
    ok "Docker image microros/micro-ros-agent:humble tersedia"
else
    warn "Docker image belum ter-pull → docker pull microros/micro-ros-agent:humble"
fi
echo ""

# ── Summary ─────────────────────────────────────────────────────────────
echo "=========================================="
echo "  PASS: $PASS   WARN: $WARN   FAIL: $FAIL"
echo "=========================================="
if [ $FAIL -gt 0 ]; then
    echo "  → Ada $FAIL masalah kritis, selesaikan dulu sebelum launch."
    exit 1
elif [ $WARN -gt 0 ]; then
    echo "  → Ada $WARN warning, robot bisa jalan tapi mungkin ada issue."
    exit 0
else
    echo "  → Semua OK! Siap launch: ros2 launch amr_bringup bringup.launch.py"
    exit 0
fi
