#!/bin/bash
set -e

# 1. Pastikan permission device serial terbuka di dalam container
chmod 666 /dev/ttyUSB* /dev/ttyACM* /dev/amr_* 2>/dev/null || true

# 2. Source environment global ROS 2 Humble
source /opt/ros/humble/setup.bash

# 3. Source workspace lokal jika sudah ter-build
if [ -f "/home/dev/amr_ws/install/setup.bash" ]; then
    source /home/dev/amr_ws/install/setup.bash
fi

# 4. Jalankan command sebagai user 'dev' (gosu menjaga PID 1 untuk sinyal Ctrl+C)
exec gosu dev "$@"
