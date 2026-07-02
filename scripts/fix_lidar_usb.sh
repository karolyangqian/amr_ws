#!/bin/bash
# Fix CP210x duplicate serial conflict — jalankan sebelum bringup
# Solusi: unbind/rebind device kedua sambil ttyUSB1 di-hold → dapat ttyUSB2

set -e

DRIVER_PATH="/sys/bus/usb/drivers/cp210x"

echo "[fix_lidar_usb] Mencari dua CP210x device..."

INTERFACES=$(ls "$DRIVER_PATH" | grep -E '^[0-9]+-[0-9.]+:1\.0$' | sort)
COUNT=$(echo "$INTERFACES" | wc -l)

if [ "$COUNT" -lt 2 ]; then
    echo "[fix_lidar_usb] Hanya $COUNT CP210x device, tidak perlu fix."
    ls /dev/ttyUSB* 2>/dev/null
    exit 0
fi

SECOND=$(echo "$INTERFACES" | tail -1)
echo "[fix_lidar_usb] Interfaces: $(echo $INTERFACES | tr '\n' ' ')"
echo "[fix_lidar_usb] Rebinding: $SECOND"

# Hold ttyUSB1 open agar slot-nya tidak langsung dipakai ulang
# → device yang di-rebind dapat ttyUSB2
python3 -c "
import time, sys
try:
    f = open('/dev/ttyUSB1', 'rb', buffering=0)
    time.sleep(4)
    f.close()
except:
    time.sleep(4)
" &
HOLDER=$!

sleep 0.3  # tunggu holder buka device

echo "$SECOND" | sudo tee "$DRIVER_PATH/unbind" > /dev/null
sleep 0.5
echo "$SECOND" | sudo tee "$DRIVER_PATH/bind" > /dev/null
sleep 0.5

wait $HOLDER 2>/dev/null || true

echo "[fix_lidar_usb] Port sekarang:"
ls /dev/ttyUSB*

REAR_PORT=$(ls /dev/ttyUSB* | tail -1)
echo "[fix_lidar_usb] ✓ Front LiDAR → /dev/ttyUSB0"
echo "[fix_lidar_usb] ✓ Rear LiDAR  → $REAR_PORT"
echo "$REAR_PORT" > /tmp/amr_rear_lidar_port
