#!/bin/bash
# Sync firmware_teensy ke NUC lalu build + upload

NUC_USER="amr"
NUC_IP="amr-nuc.local"
NUC_FW_PATH="/home/amr/firmware_teensy"
LOCAL_FW="$(cd "$(dirname "$0")/../../firmware_teensy" && pwd)"

echo "[sync_firmware] Memeriksa koneksi ke ${NUC_USER}@${NUC_IP}..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${NUC_USER}@${NUC_IP}" true 2>/dev/null; then
    echo "[ERROR] Tidak bisa terhubung ke NUC."
    exit 1
fi

echo "[sync_firmware] Sumber : ${LOCAL_FW}/"
echo "[sync_firmware] Tujuan : ${NUC_USER}@${NUC_IP}:${NUC_FW_PATH}/"

rsync -avz --progress \
    --exclude ".pio/build" \
    --exclude ".pio/libdeps" \
    --exclude "__pycache__" \
    "${LOCAL_FW}/" \
    "${NUC_USER}@${NUC_IP}:${NUC_FW_PATH}/"

if [[ $? -ne 0 ]]; then
    echo "[ERROR] rsync gagal."
    exit 1
fi

echo ""
echo "[sync_firmware] Sync selesai."

# Tanya apakah mau langsung build + upload
read -rp "Build dan upload ke Teensy sekarang? [y/N] " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo "[sync_firmware] Build + upload via SSH..."
    ssh "${NUC_USER}@${NUC_IP}" \
        "cd ${NUC_FW_PATH} && ~/.local/bin/pio run -t upload"
    echo "[sync_firmware] Upload selesai."
fi
