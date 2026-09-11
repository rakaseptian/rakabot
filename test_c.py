#!/usr/bin/env python3
"""TEST C - workflow Wan 2.2 Animate penuh via serverless.
Input = URL publik (foto + video) yang otomatis didownload worker."""
import asyncio, json, time
from vastai import Serverless

KEY = open("/home/ubuntu/rakabot/.env").read()
import re
KEY = re.search(r'VAST_API_KEY=(\S+)', KEY).group(1)

WF = json.load(open("/home/ubuntu/rakabot-serverless/workflow_serverless_animate.json"))
IMG, VID = [l.strip() for l in open("/tmp/testc_urls.txt") if l.strip()]

WF["57"]["inputs"]["image"] = IMG
WF["63"]["inputs"]["video"] = VID


async def main():
    t0 = time.time()
    def log(m): print(f"[{time.time()-t0:7.1f}s] {m}", flush=True)

    s = Serverless(KEY)
    eps = await s.get_endpoints()
    ep = eps[0]
    log(f"endpoint={getattr(ep,'name',None)}")

    req = s.queue_endpoint_request(
        ep, "/generate/sync",
        {"input": {"request_id": f"testC_{int(time.time())}", "workflow_json": WF}},
        cost=10000, timeout=3600.0, worker_timeout=3600.0)

    last = None
    while not req.done():
        await asyncio.sleep(15)
        st = getattr(req, "status", "?")
        if st != last:
            log(f"  status={st}"); last = st

    if req.exception():
        log(f"EXC: {req.exception()}")
    else:
        res = req.result()
        log("=== HASIL ===")
        print(json.dumps(res, indent=1)[:4000], flush=True)
    await s.close()


asyncio.run(main())
