#!/usr/bin/env python3
"""
RunPod Serverless handler - Wan 2.2 Animate (Mode MOVE).

Menerima request:
{
  "input": {
    "image": "data:image/png;base64,...",      # foto referensi (wajib)
    "video": "data:video/mp4;base64,...",      # video referensi (wajib)
    "positive_prompt": "...",                  # opsional
    "negative_prompt": "...",                  # opsional
    "seed": 12345                              # opsional
  }
}

Mengembalikan:
{
  "video": "base64..." atau "https://s3.../out.mp4",
  "filename": "out.mp4",
  "type": "base64" | "s3_url"
}
"""
import os
import io
import json
import time
import base64
import uuid
import shutil
import logging
import urllib.request
import urllib.error

import runpod

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ===================== KONFIGURASI =====================
COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
COMFY_URL = f"http://{COMFY_HOST}"

# Direktori ComfyUI
COMFY_ROOT = os.environ.get("COMFY_ROOT", "/comfyui")
INPUT_DIR = os.path.join(COMFY_ROOT, "input")
OUTPUT_DIR = os.path.join(COMFY_ROOT, "output")
WORKFLOW_PATH = os.environ.get("WORKFLOW_PATH", "/workflow_api.json")

# Batasan
MAX_DURATION_SEC = 15
TARGET_FPS = 30
MAX_FRAMES = 450          # 15 detik @ 30fps

# S3 / R2 (opsional)
S3_ENDPOINT = os.environ.get("BUCKET_ENDPOINT_URL")
S3_KEY = os.environ.get("BUCKET_ACCESS_KEY_ID")
S3_SECRET = os.environ.get("BUCKET_SECRET_ACCESS_KEY")
S3_BUCKET = os.environ.get("BUCKET_NAME")

DEFAULT_POS = (
    "The character is dancing in the room "
    "same person from the reference image "
    "same background same clothes"
)
DEFAULT_NEG = (
    "changing face, changing clothes, changing background, "
    "morphing, blurry, distorted"
)

log.info(f"COMFY_URL={COMFY_URL} COMFY_ROOT={COMFY_ROOT}")


# ===================== HELPER =====================
def _b64_to_bytes(data_uri):
    """Terima 'data:...;base64,XXX' atau raw base64 -> bytes."""
    if isinstance(data_uri, str) and "," in data_uri[:64]:
        data_uri = data_uri.split(",", 1)[1]
    return base64.b64decode(data_uri)


def _comfy_post(path, payload, timeout=60):
    req = urllib.request.Request(
        f"{COMFY_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _comfy_get(path, timeout=60):
    with urllib.request.urlopen(f"{COMFY_URL}{path}", timeout=timeout) as r:
        return json.loads(r.read())


def wait_for_comfy(timeout=300):
    """Tunggu ComfyUI siap."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            _comfy_get("/system_stats", timeout=5)
            log.info("ComfyUI ready")
            return True
        except Exception:
            time.sleep(2)
    raise RuntimeError("ComfyUI tidak siap dalam waktu yang ditentukan")


def upload_input(filename, data):
    """Simpan file ke ComfyUI/input."""
    os.makedirs(INPUT_DIR, exist_ok=True)
    path = os.path.join(INPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)
    log.info(f"saved input: {path} ({len(data)} bytes)")
    return filename


def load_workflow():
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def patch_workflow(wf, ref_image, ref_video, pos, neg, seed):
    """Ganti placeholder dengan nilai nyata."""
    for nid, node in wf.items():
        inputs = node.get("inputs", {})

        # LoadImage (57) -> foto referensi
        if node.get("class_type") == "LoadImage":
            for k in list(inputs.keys()):
                if inputs[k] == "__REF_IMAGE__" or (
                    isinstance(inputs[k], str)
                    and inputs[k].lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                ):
                    inputs[k] = ref_image

        # VHS_LoadVideo (63) -> video referensi
        if node.get("class_type") == "VHS_LoadVideo":
            for k in list(inputs.keys()):
                if inputs[k] == "__REF_VIDEO__" or (
                    isinstance(inputs[k], str)
                    and inputs[k].lower().endswith((".mp4", ".mov", ".webm"))
                ):
                    inputs[k] = ref_video

        # WanVideoTextEncodeCached (65) -> prompt
        if node.get("class_type") == "WanVideoTextEncodeCached":
            if "positive_prompt" in inputs:
                inputs["positive_prompt"] = pos
            elif inputs.get("value_2") == "__POS_PROMPT__":
                inputs["value_2"] = pos
            if "negative_prompt" in inputs:
                inputs["negative_prompt"] = neg
            elif inputs.get("value_3") == "__NEG_PROMPT__":
                inputs["value_3"] = neg

        # Sampler seed (jika ada)
        if node.get("class_type") == "WanVideoSampler":
            for k in ("seed", "noise_seed"):
                if k in inputs and isinstance(inputs[k], int):
                    inputs[k] = seed

    return wf


def collect_outputs(history, prompt_id):
    """Ambil file output video dari history ComfyUI."""
    entry = history.get(prompt_id)
    if not entry:
        return []
    outs = []
    for nid, out in (entry.get("outputs") or {}).items():
        for key in ("gifs", "videos", "images"):
            for item in (out.get(key) or []):
                fn = item.get("filename")
                sub = item.get("subfolder", "")
                ftype = item.get("type", "output")
                if not fn:
                    continue
                if not fn.lower().endswith((".mp4", ".webm", ".mov", ".gif")):
                    continue
                path = os.path.join(OUTPUT_DIR, sub, fn) if ftype == "output" \
                    else os.path.join(INPUT_DIR, sub, fn)
                if os.path.exists(path):
                    outs.append(path)
    return outs


def upload_to_s3(path, key):
    """Upload ke S3/R2 via boto3 (jika terinstall & env lengkap)."""
    try:
        import boto3
    except ImportError:
        return None
    if not (S3_ENDPOINT and S3_KEY and S3_SECRET and S3_BUCKET):
        return None
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_KEY,
            aws_secret_access_key=S3_SECRET,
        )
        s3.upload_file(path, S3_BUCKET, key)
        return f"{S3_ENDPOINT}/{S3_BUCKET}/{key}"
    except Exception as e:
        log.error(f"S3 upload gagal: {e}")
        return None


# ===================== HANDLER =====================
def handler(job):
    inp = job.get("input", {}) or {}

    # --- Validasi input ---
    if not inp.get("image"):
        return {"error": "field 'image' wajib diisi (foto referensi)"}
    if not inp.get("video"):
        return {"error": "field 'video' wajib diisi (video referensi)"}

    run_id = uuid.uuid4().hex[:12]
    t0 = time.time()

    try:
        wait_for_comfy()

        # 1. Decode & simpan input
        img_bytes = _b64_to_bytes(inp["image"])
        vid_bytes = _b64_to_bytes(inp["video"])

        ref_image = f"ref_{run_id}.png"
        ref_video = f"motion_{run_id}.mp4"
        upload_input(ref_image, img_bytes)
        upload_input(ref_video, vid_bytes)

        # 2. Load & patch workflow
        wf = load_workflow()
        wf = patch_workflow(
            wf,
            ref_image=ref_image,
            ref_video=ref_video,
            pos=inp.get("positive_prompt") or DEFAULT_POS,
            neg=inp.get("negative_prompt") or DEFAULT_NEG,
            seed=int(inp.get("seed") or time.time()),
        )

        # 3. Submit ke ComfyUI
        client_id = uuid.uuid4().hex
        res = _comfy_post("/prompt", {"prompt": wf, "client_id": client_id})
        prompt_id = res.get("prompt_id")
        if not prompt_id:
            return {"error": f"gagal submit prompt: {res}"}
        log.info(f"prompt_id={prompt_id}")

        # 4. Poll history
        timeout = int(os.environ.get("JOB_TIMEOUT", 3600))
        start = time.time()
        while True:
            if time.time() - start > timeout:
                return {"error": "timeout menunggu ComfyUI"}
            time.sleep(5)
            try:
                hist = _comfy_get(f"/history/{prompt_id}", timeout=30)
            except Exception:
                continue
            if prompt_id not in hist:
                continue

            entry = hist[prompt_id]
            status = entry.get("status", {})
            if status.get("completed"):
                break
            if status.get("status_str") == "error":
                return {"error": f"ComfyUI error: {status}"}

        # 5. Ambil output
        out_files = collect_outputs(hist, prompt_id)
        if not out_files:
            return {"error": "tidak ada file video output ditemukan"}

        out_path = out_files[0]
        log.info(f"output: {out_path}")

        # 6. Return (S3 atau base64)
        s3_url = upload_to_s3(out_path, f"{run_id}.mp4")
        if s3_url:
            return {
                "video": s3_url,
                "type": "s3_url",
                "filename": os.path.basename(out_path),
                "elapsed": round(time.time() - t0, 1),
            }

        with open(out_path, "rb") as f:
            data = f.read()
        return {
            "video": base64.b64encode(data).decode(),
            "type": "base64",
            "filename": os.path.basename(out_path),
            "elapsed": round(time.time() - t0, 1),
        }

    except Exception as e:
        log.exception("handler error")
        return {"error": str(e)}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
