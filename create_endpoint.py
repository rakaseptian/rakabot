#!/usr/bin/env python3
"""
Buat Serverless Endpoint di RunPod + attach Network Volume 7p0yl3jbav.

Endpoint akan pakai image ghcr.io/rakaseptian/rakabot:latest
Model & ComfyUI dibaca dari Network Volume (mount /runpod-volume).

Cara pakai:
  python3 create_endpoint.py
"""
import os
import json
import time
import urllib.request
import urllib.error

# ---- KONFIGURASI ----
API_KEY = ''
with open('/home/ubuntu/rakabot/.env') as f:
    for line in f:
        if line.startswith('RUNPOD_API_KEY='):
            API_KEY = line.strip().split('=', 1)[1]

IMAGE = 'ghcr.io/rakaseptian/rakabot:latest'
VOLUME_ID = '7p0yl3jbav'      # Network Volume 100GB (EU-RO-1)
DATACENTER = 'EU-RO-1'         # HARUS sama dengan volume!

# GPU: RTX 5090 32GB (sudah terbukti di pod)
GPU_IDS = ['NVIDIA GeForce RTX 5090']

ENDPOINT_NAME = 'akarai-wan22-animate'

# ---- API HELPER ----
def api(method, path, payload=None, timeout=60, retries=3):
    url = f'https://rest.runpod.io/v1{path}'
    for attempt in range(retries):
        try:
            data = json.dumps(payload).encode() if payload else None
            req = urllib.request.Request(
                url, data=data, method=method,
                headers={
                    'Authorization': f'Bearer {API_KEY}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0',
                })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f'  [HTTP {e.code}] {body[:200]}')
            if attempt == retries - 1:
                raise
            time.sleep(2)
        except Exception as e:
            print(f'  [ERR] {e}')
            if attempt == retries - 1:
                raise
            time.sleep(2)


def main():
    print('=== BUAT SERVERLESS ENDPOINT ===')
    print(f'Image  : {IMAGE}')
    print(f'Volume : {VOLUME_ID} ({DATACENTER})')
    print(f'GPU    : {GPU_IDS}')
    print()

    # 1. Buat template
    print('[1/3] Membuat template...')
    tpl_payload = {
        'name': f'{ENDPOINT_NAME}-tpl-{int(time.time())}',
        'imageName': IMAGE,
        'isServerless': True,
        'containerDiskInGb': 20,
        'volumeInGb': 0,
        'volumeMountPath': '/runpod-volume',
        # CATATAN schema RunPod:
        #   env   = OBJECT  {...}
        #   ports = ARRAY   [...]
        'env': {
            'MODE': 'volume',
            'RUNPOD_DEBUG_LEVEL': 'debug',
        },
    }

    try:
        tpl = api('POST', '/templates', tpl_payload)
        tpl_id = tpl.get('id')
        print(f'  Template ID: {tpl_id}')
    except Exception as e:
        print(f'  GAGAL buat template: {e}')
        return 1

    # 2. Buat endpoint
    print('[2/3] Membuat endpoint...')
    ep_payload = {
        'name': ENDPOINT_NAME,
        'templateId': tpl_id,
        'gpuTypeIds': GPU_IDS,
        'networkVolumeId': VOLUME_ID,
        'computeType': 'GPU',
        'workersMin': 0,
        'workersMax': 3,
        'idleTimeout': 5,
        'scalerType': 'QUEUE_DELAY',
        'scalerValue': 4,
        'flashboot': True,
    }

    try:
        ep = api('POST', '/endpoints', ep_payload)
        ep_id = ep.get('id')
        print(f'  Endpoint ID: {ep_id}')
    except Exception as e:
        print(f'  GAGAL buat endpoint: {e}')
        return 1

    # 3. Simpan config
    print('[3/3] Menyimpan config...')
    cfg = {
        'endpoint_id': ep_id,
        'endpoint_name': ENDPOINT_NAME,
        'template_id': tpl_id,
        'image': IMAGE,
        'volume_id': VOLUME_ID,
        'datacenter': DATACENTER,
        'gpu': GPU_IDS,
        'run_url': f'https://api.runpod.ai/v2/{ep_id}/run',
        'status_url': f'https://api.runpod.ai/v2/{ep_id}/status',
    }
    with open('/home/ubuntu/rakabot-serverless/endpoint_config.json', 'w') as f:
        json.dump(cfg, f, indent=2)

    print()
    print('=== SELESAI ===')
    print(json.dumps(cfg, indent=2))
    print()
    print(f'Cek status: https://www.runpod.io/console/serverless/{ep_id}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
