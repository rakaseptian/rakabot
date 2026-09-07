#!/bin/bash
# Start ComfyUI dengan DB terpisah (hindari lock volume antar pod)
cd /workspace/runpod-slim/ComfyUI
rm -f /tmp/comfy5090.db
nohup setsid ./.venv-cu128/bin/python3 main.py \
  --listen 127.0.0.1 \
  --port 8188 \
  --disable-auto-launch \
  --database-url "sqlite:////tmp/comfy5090.db" \
  > /tmp/comfy5090.log 2>&1 < /dev/null &
disown
echo "started"
