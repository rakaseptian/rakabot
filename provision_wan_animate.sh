#!/bin/bash
# Provisioning script untuk Vast.ai serverless worker (ComfyUI + Wan 2.2 Animate 14B).
# Dipasang via env PROVISIONING_SCRIPT=<raw url>. Jalan Phase 9, setelah Supervisor.
# Tujuan: worker standar (vastai/comfy) jadi mampu menjalankan workflow Wan22Animate.

set -uo pipefail

WORKSPACE_DIR="${WORKSPACE:-/workspace}"
COMFYUI_DIR="${WORKSPACE_DIR}/ComfyUI"
MODELS_DIR="${COMFYUI_DIR}/models"
NODES_DIR="${COMFYUI_DIR}/custom_nodes"
CKPTS_DIR="${NODES_DIR}/comfyui_controlnet_aux/ckpts"
MODEL_LOG="${MODEL_LOG:-/var/log/portal/comfyui.log}"
PARALLEL=4

log() { echo "[provision $(date '+%H:%M:%S')] $*" | tee -a "$MODEL_LOG"; }

# ---- daftar custom node ----
NODES=(
  "kijai/ComfyUI-WanVideoWrapper"
  "kijai/ComfyUI-KJNodes"
  "Kosinkadink/ComfyUI-VideoHelperSuite"
  "Fannovel16/comfyui_controlnet_aux"
)

# ---- daftar model: "url|tujuan" ----
MODELS=(
  "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/Wan22Animate/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors|${MODELS_DIR}/diffusion_models/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors"
  "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors|${MODELS_DIR}/vae/wan_2.1_vae.safetensors"
  "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors|${MODELS_DIR}/text_encoders/umt5-xxl-enc-bf16.safetensors"
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors|${MODELS_DIR}/clip_vision/clip_vision_h.safetensors"
  "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors|${MODELS_DIR}/loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
  "https://huggingface.co/hr16/yolox-onnx/resolve/main/yolox_l.torchscript.pt|${CKPTS_DIR}/hr16/yolox-onnx/yolox_l.torchscript.pt"
  "https://huggingface.co/hr16/DWPose-TorchScript-BatchSize5/resolve/main/dw-ll_ucoco_384_bs5.torchscript.pt|${CKPTS_DIR}/hr16/DWPose-TorchScript-BatchSize5/dw-ll_ucoco_384_bs5.torchscript.pt"
)

fetch() {
  local url="$1" out="$2" tmp
  mkdir -p "$(dirname "$out")"
  if [ -s "$out" ]; then log "SKIP ada: $(basename "$out")"; return 0; fi
  tmp="${out}.part"
  for attempt in 1 2 3; do
    if curl -fsSL --retry 2 --connect-timeout 30 --max-time 3600 -o "$tmp" "$url"; then
      if [ -s "$tmp" ]; then mv "$tmp" "$out"; log "OK $(basename "$out") ($(du -h "$out" | cut -f1))"; return 0; fi
    fi
    log "retry $attempt gagal: $(basename "$out")"; sleep $((attempt * 5))
  done
  log "GAGAL: $url"; rm -f "$tmp"; return 1
}

main() {
  log "mulai provisioning"
  [ -f /venv/main/bin/activate ] && . /venv/main/bin/activate
  # CATATAN: CKPTS_DIR TIDAK dibuat di sini — kalau dibuat lebih dulu, `git clone`
  # ke folder comfyui_controlnet_aux akan gagal (dir tujuan tidak kosong).
  # Folder ckpts dibuat otomatis oleh fetch() lewat mkdir -p.
  mkdir -p "$MODELS_DIR"/{diffusion_models,vae,text_encoders,clip_vision,loras} "$NODES_DIR"

  # 1. custom nodes
  for repo in "${NODES[@]}"; do
    name="$(basename "$repo")"
    if [ -d "$NODES_DIR/$name/.git" ]; then
      log "node ada: $name"; (cd "$NODES_DIR/$name" && git pull --ff-only -q) || true
    elif [ -d "$NODES_DIR/$name" ] && [ ! -f "$NODES_DIR/$name/__init__.py" ]; then
      # clone parsial/gagal: ambil isi repo ke temp lalu timpa (jangan hapus ckpts)
      log "perbaiki node: $name"
      rm -rf "/tmp/fix_$name"
      if git clone --depth 1 -q "https://github.com/${repo}.git" "/tmp/fix_$name"; then
        tar -C "/tmp/fix_$name" -cf - . | tar -C "$NODES_DIR/$name" -xf -
        log "node diperbaiki: $name"
      else
        log "perbaikan gagal: $name"
      fi
    else
      log "clone node: $name"
      git clone --depth 1 -q "https://github.com/${repo}.git" "$NODES_DIR/$name" || log "clone gagal: $name"
    fi
    if [ -f "$NODES_DIR/$name/requirements.txt" ]; then
      python -m pip install -q -r "$NODES_DIR/$name/requirements.txt" 2>&1 | tail -3 | tee -a "$MODEL_LOG"
    fi
  done

  # comfyui_controlnet_aux butuh torch/numpy JANGAN diupgrade — buang baris itu
  if [ -f "$NODES_DIR/comfyui_controlnet_aux/requirements.txt" ]; then
    grep -viE '^(torch|torchvision|numpy)' "$NODES_DIR/comfyui_controlnet_aux/requirements.txt" \
      > /tmp/cnaux.txt
    python -m pip install -q -r /tmp/cnaux.txt 2>&1 | tail -3 | tee -a "$MODEL_LOG"
  fi

  # 2. model (paralel, dibatasi)
  local pids=() failed=0
  for entry in "${MODELS[@]}"; do
    while [ "$(jobs -rp | wc -l)" -ge "$PARALLEL" ]; do wait -n; done
    fetch "${entry%%|*}" "${entry##*|}" &
    pids+=($!)
  done
  for pid in "${pids[@]}"; do wait "$pid" || failed=1; done

  # 3. bersihkan cache pip
  rm -rf /root/.cache/pip "$MODELS_DIR"/../.cache 2>/dev/null || true

  if [ "$failed" -eq 1 ]; then
    log "PERINGATAN: ada download gagal (worker tetap lanjut)"
  fi
  log "selesai provisioning; node: $(ls "$NODES_DIR" | tr '\n' ' ')"
}

main
