#!/bin/bash
# Start ComfyUI di pod dengan DB terpisah (hindari lock volume)
cd /workspace/runpod-slim/ComfyUI
rm -f /tmp/comfy_pod2.db
setsid ./.venv-cu128/bin/python3 main.py \
  --listen 127.0.0.1 \
  --port 8188 \
  --disable-auto-launch \
  --database-url "sqlite:////tmp/comfy_pod2.db" \
  > /tmp/c3.log 2>&1 < /dev/null &
disown
echo "comfy started, pid=$!"
