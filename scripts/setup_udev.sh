#!/bin/bash
set -e

TARGET_FILE="/etc/udev/rules.d/99-amr.rules"

# Cek privilege root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Script ini harus dijalankan dengan hak akses root (gunakan sudo)." >&2
    exit 1
fi

# Konfirmasi jika file sudah ada
if [ -f "$TARGET_FILE" ]; then
    read -r -p "File '$TARGET_FILE' sudah ada. Timpa (overwrite)? [y/N]: " response
    case "$response" in
        [yY][eE][sS]|[yY])
            echo "Menimpa file..."
            ;;
        *)
            echo "Dibatalkan. Tidak ada perubahan yang dilakukan."
            exit 0
            ;;
    esac
fi

# Menulis rules ke target file
cat << 'EOF' > "$TARGET_FILE"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="0001", SYMLINK+="amr_lidar_front", MODE="0666"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="0002", SYMLINK+="amr_lidar_rear", MODE="0666"
SUBSYSTEM=="tty", ATTRS{idVendor}=="16c0", ATTRS{idProduct}=="0483", ATTRS{serial}=="14948810", SYMLINK+="amr_mcu", MODE="0666"
EOF

echo "Rules berhasil ditulis ke $TARGET_FILE."

# Reload dan aktivasi udev rules
echo "Memuat ulang dan memicu udev rules..."
udevadm control --reload-rules
udevadm trigger

echo "Selesai. Symlink perangkat telah aktif."