#!/bin/bash
# Sync amr_ws source ke NUC — jalankan dari laptop sebelum deploy
# Usage: ./scripts/sync_to_nuc.sh [--full]
#   --full  : sync juga build/ & install/ (tidak disarankan, beda arsitektur)

NUC_USER="amr"
NUC_IP="amr-nuc.local"
NUC_PATH="/home/amr/amr_ws"
LOCAL_WS="$(cd "$(dirname "$0")/.." && pwd)"

EXCLUDES=(--exclude build --exclude install --exclude log --exclude __pycache__ --exclude "*.pyc")

if [[ "$1" == "--full" ]]; then
  EXCLUDES=()
  echo "[sync] Mode FULL — termasuk build/install/log"
fi

echo "[sync] Memeriksa koneksi ke ${NUC_USER}@${NUC_IP}..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${NUC_USER}@${NUC_IP}" true 2>/dev/null; then
  echo "[ERROR] Tidak bisa terhubung ke NUC. Pastikan:"
  echo "  1. NUC menyala dan terhubung WiFi"
  echo "  2. SSH key sudah di-copy: ssh-copy-id amr@${NUC_IP}"
  exit 1
fi

echo "[sync] Sumber  : ${LOCAL_WS}/"
echo "[sync] Tujuan  : ${NUC_USER}@${NUC_IP}:${NUC_PATH}/"
echo "[sync] Mulai transfer..."

rsync -avz --progress \
  "${EXCLUDES[@]}" \
  "${LOCAL_WS}/" \
  "${NUC_USER}@${NUC_IP}:${NUC_PATH}/"

if [[ $? -eq 0 ]]; then
  echo ""
  echo "[sync] SELESAI. Selanjutnya di NUC:"
  echo "  ssh ${NUC_USER}@${NUC_IP}"
  echo "  cd ~/amr_ws && colcon build --symlink-install"
else
  echo "[ERROR] rsync gagal."
  exit 1
fi
