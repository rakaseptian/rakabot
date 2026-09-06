#!/usr/bin/env python3
"""
Download semua model Wan 2.2 Animate ke direktori target.

URL sudah DIVERIFIKASI (HTTP 200) per 2026-09-06.

Cara pakai:
  python3 download_models.py /comfyui/models
  python3 download_models.py /runpod-volume/ComfyUI/models

Total download: ~31GB
"""
import os
import sys
import time
import urllib.request

# (url, subfolder, filename, perkiraan_MB)
MODELS = [
    (
        "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/"
        "Wan22Animate/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors",
        "diffusion_models",
        "Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors",
        17549,
    ),
    (
        "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/"
        "umt5-xxl-enc-bf16.safetensors",
        "text_encoders",
        "umt5-xxl-enc-bf16.safetensors",
        10835,
    ),
    (
        "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/"
        "split_files/vae/wan_2.1_vae.safetensors",
        "vae",
        "wan_2.1_vae.safetensors",
        242,
    ),
    (
        "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/"
        "split_files/clip_vision/clip_vision_h.safetensors",
        "clip_vision",
        "clip_vision_h.safetensors",
        1205,
    ),
    (
        "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/"
        "Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors",
        "loras",
        "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors",
        703,
    ),
    (
        "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/"
        "LoRAs/Wan22_relight/WanAnimate_relight_lora_fp16.safetensors",
        "loras",
        "WanAnimate_relight_lora_fp16.safetensors",
        1370,
    ),
]


def human(n):
    return f"{n/1024/1024:.1f} MB" if n < 1024**3 else f"{n/1024**3:.2f} GB"


def download(url, dest, expect_mb):
    if os.path.exists(dest):
        size = os.path.getsize(dest)
        print(f"[SKIP] sudah ada: {os.path.basename(dest)} ({human(size)})")
        return True

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    print(f"[GET ] {os.path.basename(dest)} (~{expect_mb} MB)")

    start = time.time()
    last = 0
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            total = int(r.headers.get("content-length", 0))
            with open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done = f.tell()
                    # progress tiap 500MB
                    if done - last > 500 * 1024 * 1024:
                        last = done
                        pct = done / total * 100 if total else 0
                        print(f"       {human(done)} / {human(total)} ({pct:.0f}%)")
        os.replace(tmp, dest)
        size = os.path.getsize(dest)
        print(f"[OK  ] {os.path.basename(dest)} ({human(size)}, "
              f"{time.time()-start:.0f}s)")
        return True
    except Exception as e:
        print(f"[ERR ] {os.path.basename(dest)}: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    base = sys.argv[1]
    exts = {
        "diffusion_models": "models/diffusion_models",
        "text_encoders": "models/text_encoders",
        "vae": "models/vae",
        "clip_vision": "models/clip_vision",
        "loras": "models/loras",
    }

    print(f"Target: {base}")
    print(f"Total model: {len(MODELS)}\n")

    ok = 0
    for url, sub, fn, mb in MODELS:
        dest = os.path.join(base, exts[sub], fn)
        if download(url, dest, mb):
            ok += 1
        print()

    print(f"Selesai: {ok}/{len(MODELS)} model berhasil.")
    return 0 if ok == len(MODELS) else 1


if __name__ == "__main__":
    sys.exit(main())
