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

# Cari Python environment yang punya PyTorch.
# RTX 50-series bisa pakai nama venv aneh (.venv-cu128 walau PyTorch cu130),
# jadi cari semua kandidat lalu PILIH yang benar-benar bisa import torch.
echo "Mencari python ComfyUI yang punya torch..."
CANDIDATES=(
    "$COMFY_DIR/.venv/bin/python3"
    "$COMFY_DIR/.venv-cu130/bin/python3"
    "$COMFY_DIR/.venv-cu128/bin/python3"
    "$COMFY_DIR/venv/bin/python3"
    "/runpod-volume/runpod-slim/.venv/bin/python3"
    "/runpod-volume/venv/bin/python3"
)
# Tambah hasil pencarian otomatis (venv bisa ada di lokasi tak terduga)
while IFS= read -r found; do
    CANDIDATES+=("$found")
done < <(find /runpod-volume /workspace -maxdepth 5 -type f -path "*/.venv*/bin/python3" 2>/dev/null | head -20)
while IFS= read -r found; do
    CANDIDATES+=("$found")
done < <(find /runpod-volume /workspace -maxdepth 5 -type f -path "*/venv/bin/python3" 2>/dev/null | head -20)

PYTHON_BIN=""
for candidate in "${CANDIDATES[@]}"; do
    [ -f "$candidate" ] || continue
    if "$candidate" -c "import torch" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        echo "[OK] Python ComfyUI ditemukan: $PYTHON_BIN"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[FATAL] Tidak menemukan python ComfyUI yang punya torch!"
    echo "Kandidat yang dicoba:"
    for c in "${CANDIDATES[@]}"; do echo "  - $c"; done
    exit 1
fi

# Export python ComfyUI supaya handler bisa dipakai diagnosa
export COMFY_PYTHON="$PYTHON_BIN"

# Pasang semua dependency ComfyUI dari requirements.txt (paling aman & lengkap)
if [ -f "$COMFY_DIR/requirements.txt" ]; then
    echo "Install ComfyUI requirements.txt ..."
    "$PYTHON_BIN" -m pip install --no-cache-dir -r "$COMFY_DIR/requirements.txt" 2>&1 | tail -5
fi

# Install dependency ringan yang kadang hilang di venv ComfyUI.
for mod in sqlalchemy filelock alembic; do
    "$PYTHON_BIN" -c "import $mod" >/dev/null 2>&1 || {
        echo "Install modul hilang: $mod"
        "$PYTHON_BIN" -m pip install --no-cache-dir "$mod" 2>&1 | tail -3
    }
done

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
