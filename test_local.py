#!/usr/bin/env python3
"""
Test request ke RunPod serverless endpoint.

Cara pakai:
  1. Set env:
       export RUNPOD_ENDPOINT_ID=xxxxx
       export RUNPOD_API_KEY=xxxxx
  2. Siapkan file test:
       test_ref.png   (foto referensi)
       test_motion.mp4 (video referensi, 720x1280, max 15 detik)
  3. Jalankan:
       python3 test_local.py
"""
import os
import json
import time
import base64
import urllib.request
import urllib.error

ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")
API_KEY = os.environ.get("RUNPOD_API_KEY")

if not ENDPOINT_ID or not API_KEY:
    print("ERROR: set RUNPOD_ENDPOINT_ID dan RUNPOD_API_KEY dulu")
    raise SystemExit(1)

RUN_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"
STATUS_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status"

IMG = os.environ.get("TEST_IMAGE", "test_ref.png")
VID = os.environ.get("TEST_VIDEO", "test_motion.mp4")


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def post(url, payload, timeout=120):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(url, timeout=60):
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def main():
    for p in (IMG, VID):
        if not os.path.exists(p):
            print(f"ERROR: file tidak ada: {p}")
            raise SystemExit(1)

    print(f"image: {IMG} ({os.path.getsize(IMG)} bytes)")
    print(f"video: {VID} ({os.path.getsize(VID)} bytes)")

    payload = {
        "input": {
            "image": f"data:image/png;base64,{b64(IMG)}",
            "video": f"data:video/mp4;base64,{b64(VID)}",
            "positive_prompt": (
                "The character is dancing in the room "
                "same person from the reference image "
                "same background same clothes"
            ),
            "negative_prompt": (
                "changing face, changing clothes, changing background, "
                "morphing, blurry, distorted"
            ),
            "seed": 12345,
        }
    }

    size_mb = len(json.dumps(payload)) / 1024 / 1024
    print(f"payload size: {size_mb:.2f} MB")
    if size_mb > 9:
        print("WARNING: payload > 9MB, bisa kena limit RunPod (/run max 10MB)")

    print("\nSubmit job...")
    res = post(RUN_URL, payload)
    job_id = res.get("id")
    print(f"job_id: {job_id}  status: {res.get('status')}")

    if not job_id:
        print("GAGAL submit:", json.dumps(res, indent=2))
        raise SystemExit(1)

    print("\nPolling...")
    start = time.time()
    while True:
        time.sleep(10)
        st = get(f"{STATUS_URL}/{job_id}")
        status = st.get("status")
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] {status}")

        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        if elapsed > 3600:
            print("TIMEOUT")
            break

    print("\n=== HASIL ===")
    print(json.dumps(st, indent=2)[:2000])

    output = st.get("output") or {}
    if output.get("video"):
        out = output["video"]
        if output.get("type") == "base64":
            with open("result.mp4", "wb") as f:
                f.write(base64.b64decode(out))
            print("\nVideo tersimpan: result.mp4")
        else:
            print(f"\nVideo URL: {out}")


if __name__ == "__main__":
    main()
