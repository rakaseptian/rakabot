#!/bin/bash
set -e

echo "=== AkarAI Wan 2.2 Animate Serverless Worker ==="

# Cari lokasi ComfyUI di Network Volume
POSSIBLE_PATHS=(
    "/runpod-volume/runpod-slim/ComfyUI"
    "/runpod-volume/ComfyUI"
    "/workspace/runpod-slim/ComfyUI"
    "/workspace/ComfyUI"
)

COMFY_DIR=""
for p in "${POSSIBLE_PATHS[@]}"; do
    if [ -f "$p/main.py" ]; then
        COMFY_DIR="$p"
        echo "[OK] ComfyUI ditemukan di: $COMFY_DIR"
        break
    fi
done

if [ -z "$COMFY_DIR" ]; then
    echo "[FATAL] ComfyUI tidak ditemukan di Network Volume!"
    echo "Isi /runpod-volume:"
    ls -la /runpod-volume 2>/dev/null || echo "(/runpod-volume kosong atau belum di-mount)"
    echo "Isi /workspace:"
    ls -la /workspace 2>/dev/null || echo "(/workspace kosong)"
    exit 1
fi

# Cari Python environment yang punya PyTorch & CUDA
# RTX 50-series bisa pakai nama venv aneh (.venv-cu128 walau PyTorch cu130), jadi probe file.
PYTHON_BIN="python3"
for candidate in \
    "$COMFY_DIR/.venv/bin/python3" \
    "$COMFY_DIR/.venv-cu130/bin/python3" \
    "$COMFY_DIR/.venv-cu128/bin/python3" \
    "$COMFY_DIR/venv/bin/python3" \
    /runpod-volume/venv/bin/python3; do
    if [ -f "$candidate" ]; then
        PYTHON_BIN="$candidate"
        echo "[OK] Pakai python ComfyUI: $PYTHON_BIN"
        break
    fi
done

# Install dependency yang kadang hilang di venv ComfyUI (sqlalchemy dipakai app/assets).
# Hanya jalan kalau modul belum ada, supaya startup tetap cepat.
echo "Cek dependency sqlalchemy di venv ComfyUI..."
"$PYTHON_BIN" -c "import sqlalchemy" 2>/dev/null \
  || "$PYTHON_BIN" -m pip install --no-cache-dir sqlalchemy 2>&1 | tail -5

# Handler harus menulis file input/output ke ComfyUI yang sama.
export COMFY_ROOT="$COMFY_DIR"

# Pastikan workflow_api.json terpasang
if [ -f "/workflow_api.json" ]; then
    export WORKFLOW_PATH="/workflow_api.json"
fi

echo "COMFY_ROOT=$COMFY_ROOT"
echo "WORKFLOW_PATH=$WORKFLOW_PATH"

# Jalankan ComfyUI di background (terpisah dari session shell)
echo "Mulai ComfyUI..."
cd "$COMFY_DIR"
setsid "$PYTHON_BIN" main.py \
    --listen 127.0.0.1 \
    --port 8188 \
    --disable-auto-launch \
    > /tmp/comfyui.log 2>&1 < /dev/null &

COMFY_PID=$!
echo "ComfyUI PID: $COMFY_PID"
sleep 5
echo "--- cek awal comfyui.log ---"
tail -20 /tmp/comfyui.log 2>/dev/null || true

# Jangan tunggu ComfyUI di fase init serverless.
# RunPod bisa menandai worker unhealthy kalau handler belum start cepat.
# Handler sendiri akan wait_for_comfy() saat job masuk.
echo "Mulai RunPod Serverless Handler segera..."
exec python3 /handler.py
