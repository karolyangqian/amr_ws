#!/bin/bash
# Setup udev rules supaya port USB selalu sama setiap reboot.
# Jalankan: bash amr_ws/scripts/setup_udev.sh
#
# Hasil: /dev/amr_lidar_front  → lidar depan
#        /dev/amr_lidar_rear   → lidar belakang
#        /dev/amr_motor        → ZLAC8015D RS485
#        /dev/amr_imu          → Teensy (IMU)

set -e

RULES_FILE="/etc/udev/rules.d/99-amr.rules"

echo "=== AMR USB udev setup ==="
echo ""
echo "Script ini akan membantu membuat udev rules agar port USB robot"
echo "tidak bertukar setelah reboot."
echo ""

# Fungsi: baca atribut device dari path ttyUSBx
get_attr() {
    local dev="$1"
    udevadm info --name="$dev" --attribute-walk 2>/dev/null | \
        grep -E "ATTRS{idVendor}|ATTRS{idProduct}|ATTRS{serial}" | head -3
}

# Fungsi: ambil nilai atribut spesifik
get_val() {
    local dev="$1" attr="$2"
    udevadm info --name="$dev" --attribute-walk 2>/dev/null | \
        grep "ATTRS{${attr}}" | head -1 | sed 's/.*=="\(.*\)"/\1/'
}

# Tampilkan semua device yang terhubung sekarang
echo "=== Device USB terhubung sekarang: ==="
for dev in /dev/ttyUSB* /dev/ttyACM*; do
    [ -e "$dev" ] || continue
    vendor=$(get_val "$dev" "idVendor")
    product=$(get_val "$dev" "idProduct")
    serial=$(get_val "$dev" "serial")
    printf "  %-18s  vendor=%-6s  product=%-6s  serial=%s\n" \
        "$dev" "$vendor" "$product" "$serial"
done
echo ""

# Deteksi per device
declare -A VENDOR PRODUCT SERIAL

for role in lidar_front lidar_rear motor imu; do
    case $role in
        lidar_front) label="Lidar DEPAN  (USB0 default)" ;;
        lidar_rear)  label="Lidar BELAKANG (USB1 default)" ;;
        motor)       label="Motor ZLAC8015D (USB2 default)" ;;
        imu)         label="Teensy IMU (ACM0 default)" ;;
    esac

    echo "--- $label ---"
    read -rp "  Masukkan path device (misal /dev/ttyUSB0, atau ENTER skip): " dev_path
    [ -z "$dev_path" ] && echo "  Skip." && continue
    [ ! -e "$dev_path" ] && echo "  $dev_path tidak ditemukan, skip." && continue

    VENDOR[$role]=$(get_val "$dev_path" "idVendor")
    PRODUCT[$role]=$(get_val "$dev_path" "idProduct")
    SERIAL[$role]=$(get_val "$dev_path" "serial")

    echo "  → vendor=${VENDOR[$role]}  product=${PRODUCT[$role]}  serial=${SERIAL[$role]}"
    echo ""
done

# Generate rules file
echo "=== Membuat $RULES_FILE ==="

LINES=()
LINES+=("# AMR USB udev rules — auto-generated oleh setup_udev.sh")
LINES+=("# Edit manual kalau perlu ganti port/device")
LINES+=("")

for role in lidar_front lidar_rear motor imu; do
    [ -z "${VENDOR[$role]}" ] && continue
    symlink="amr_${role}"
    MATCH="SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"${VENDOR[$role]}\", ATTRS{idProduct}==\"${PRODUCT[$role]}\""
    if [ -n "${SERIAL[$role]}" ]; then
        MATCH="${MATCH}, ATTRS{serial}==\"${SERIAL[$role]}\""
    fi
    LINES+=("${MATCH}, SYMLINK+=\"${symlink}\", MODE=\"0666\"")
done

# Tulis ke file sementara dulu
TMP=$(mktemp)
printf '%s\n' "${LINES[@]}" > "$TMP"

echo ""
cat "$TMP"
echo ""

read -rp "Install rules di atas ke $RULES_FILE ? [y/N] " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    sudo cp "$TMP" "$RULES_FILE"
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo ""
    echo "=== Done! ==="
    echo "Cabut dan colok ulang USB, lalu cek: ls -la /dev/amr_*"
    echo ""
    echo "Update bringup.launch.py kalau mau pakai symlink:"
    echo "  front_lidar_port: /dev/amr_lidar_front"
    echo "  rear_lidar_port:  /dev/amr_lidar_rear"
    echo "  motor_port:       /dev/amr_motor"
    echo "  imu_port:         /dev/amr_imu"
else
    echo "Dibatalkan. File sementara ada di: $TMP"
fi

rm -f "$TMP"
