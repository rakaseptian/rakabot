#!/usr/bin/env python3
"""TEST B v3 - Serverless client: queue_endpoint_request TIDAK di-await,
kembalikan ServerlessRequest (Future). Ambil hasil via await req."""
import asyncio, json, time
from vastai import Serverless

KEY = "90743be058bc5260d15ca2b73cba807fd74adfa5fdb072b3251b42371a236e03"

WF = {
    "3": {"class_type": "KSampler", "inputs": {
        "seed": 0, "steps": 20, "cfg": 8, "sampler_name": "euler",
        "scheduler": "normal", "denoise": 1,
        "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
        "latent_image": ["5", 0]}},
    "4": {"class_type": "CheckpointLoaderSimple",
          "inputs": {"ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"}},
    "5": {"class_type": "EmptyLatentImage",
          "inputs": {"width": 512, "height": 512, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a cat", "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry", "clip": ["4", 1]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage",
          "inputs": {"filename_prefix": "srvtest", "images": ["8", 0]}},
}


async def main():
    t0 = time.time()
    s = Serverless(KEY)
    eps = await s.get_endpoints()
    ep = eps[0]
    print(f"[{time.time()-t0:6.1f}s] endpoint={getattr(ep,'name',None)}", flush=True)

    # PENTING: JANGAN await — queue_endpoint_request mengembalikan Future
    req = s.queue_endpoint_request(
        ep, "/generate/sync",
        {"input": {"request_id": "testB3", "workflow_json": WF}},
        cost=10000, timeout=1800.0, worker_timeout=1800.0)
    print(f"[{time.time()-t0:6.1f}s] queued, type={type(req).__name__}", flush=True)

    last = None
    while not req.done():
        await asyncio.sleep(10)
        st = getattr(req, "status", "?")
        if st != last:
            print(f"[{time.time()-t0:6.1f}s]   status={st}", flush=True)
            last = st

    if req.exception():
        print(f"[{time.time()-t0:6.1f}s] EXC: {req.exception()}", flush=True)
    else:
        res = req.result()
        print(f"[{time.time()-t0:6.1f}s] === HASIL ===", flush=True)
        print(json.dumps(res, indent=1)[:3000], flush=True)
    await s.close()


asyncio.run(main())
