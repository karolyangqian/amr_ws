#!/bin/bash
# Install micro-ROS agent untuk ROS2 Humble
# Jalankan sekali: bash ~/Documents/Kuliah/SMT8/Penrek/Codebase/amr_ws/scripts/install_microros.sh
#
# Menggunakan Docker untuk menghindari konflik versi fastcdr.

set -e

echo "=== Installing micro-ROS agent via Docker ==="

# 1. Cek Docker sudah terinstall
if ! command -v docker &>/dev/null; then
    echo "[INFO] Docker not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
    sudo usermod -aG docker "$USER"
    echo "[INFO] Docker installed. Anda mungkin perlu logout+login agar group docker aktif."
    echo "       Lanjutkan dengan: newgrp docker"
else
    echo "[INFO] Docker sudah terinstall: $(docker --version)"
fi

# 2. Pull image micro-ros-agent Humble
echo ""
echo "=== Pulling micro-ros/micro-ros-agent:humble ==="
docker pull microros/micro-ros-agent:humble

# 3. Buat wrapper script supaya bisa dipanggil langsung
WRAPPER="/usr/local/bin/micro_ros_agent_docker"
echo ""
echo "=== Membuat wrapper script di $WRAPPER ==="
sudo tee "$WRAPPER" > /dev/null << 'EOF'
#!/bin/bash
# Wrapper: jalankan micro-ros-agent via Docker
# Usage: micro_ros_agent_docker serial --dev /dev/ttyACM0 -b 6000000
exec docker run --rm \
    --net=host \
    --privileged \
    -v /dev:/dev \
    microros/micro-ros-agent:humble \
    "$@"
EOF
sudo chmod +x "$WRAPPER"

echo ""
echo "=== Done! ==="
echo ""
echo "Test manual:"
echo "  micro_ros_agent_docker serial --dev /dev/ttyACM0 -b 6000000"
echo ""
echo "Atau via ROS2 launch (bringup.launch.py sudah dikonfigurasi untuk Docker)."
