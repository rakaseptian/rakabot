#!/bin/bash
set -e

# ============================================================
# Script untuk mengambil object_info.json dari pod ComfyUI
# lalu memperbaiki nama widget di workflow_api.json
#
# Cara pakai:
#   ./fetch_and_fix.sh <POD_ID>
#   contoh: ./fetch_and_fix.sh 9bbyiffp5dqyn8
# ============================================================

POD_ID="${1:-9bbyiffp5dqyn8}"
URL="https://${POD_ID}-8188.proxy.runpod.net/object_info"

echo "Ambil object_info dari: $URL"

if ! curl -s --max-time 120 "$URL" -o object_info.json; then
    echo "GAGAL: tidak bisa ambil object_info. Pod mati atau URL salah?"
    exit 1
fi

# Cek file valid JSON
if ! python3 -c "import json; json.load(open('object_info.json'))" 2>/dev/null; then
    echo "GAGAL: object_info.json tidak valid (kemungkinan pod mati / 404)"
    head -c 200 object_info.json
    exit 1
fi

SIZE=$(stat -c%s object_info.json)
echo "object_info.json OK (${SIZE} bytes)"

echo ""
echo "Perbaiki nama widget..."
python3 fix_widget_names.py object_info.json workflow_api.json

echo ""
echo "SELESAI. Cek output di atas."
echo "Pastikan node 65 punya key 'positive_prompt' & 'negative_prompt'"
echo "bukan 'value_2' / 'value_3'."
