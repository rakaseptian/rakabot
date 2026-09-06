# AkarAI Studio - Wan 2.2 Animate Serverless Worker

Worker RunPod Serverless untuk video Wan 2.2 Animate (Mode MOVE).

## Alur

```
Telegram Bot --> POST /run --> Worker
                                |
                                v
                        simpan ref.png + motion.mp4
                        patch workflow_api.json
                        submit ke ComfyUI internal :8188
                        polling /history
                        ambil MP4 hasil
                                |
                                v
Telegram Bot <-- /status <-- return video (S3 URL / base64)
```

## Ringkasan Revisi (v2)

| Item | v1 (salah) | v2 (sekarang) |
|---|---|---|
| Model di image | Ya (40GB) | **Tidak** (~8GB image) |
| Model disimpan | - | Network Volume `/runpod-volume` |
| URL model | 4 dari 6 salah (404) | **Semua 200 OK** |
| Cold start | 1-3 menit | Lebih cepat (model sudah di volume) |

## Isi Folder

| File | Fungsi |
|---|---|
| `Dockerfile` | Build image (~8GB) + ComfyUI + custom node |
| `handler.py` | Entry point RunPod serverless |
| `start.sh` | Symlink model dari volume, start ComfyUI + worker |
| `download_models.py` | Download 6 model (~31GB) ke target folder |
| `workflow_api.json` | Workflow API (30 node) |
| `fix_widget_names.py` | Konversi `value_N` → nama widget asli |
| `fetch_and_fix.sh` | Ambil `object_info.json` dari pod + jalankan fix |
| `patches/apply_patches.py` | Patch lazy `PromptServer.instance` |
| `test_local.py` | Test endpoint end-to-end |
| `requirements.txt` | runpod, requests, boto3 |

## PENTING - Kerjakan Ini Dulu

### 1. Fix nama widget (WAJIB sebelum build)

`workflow_api.json` sekarang masih pakai nama generik
(`value_0`, `value_2`). ComfyUI butuh nama asli
(`positive_prompt`, `negative_prompt`, `steps`, `cfg`).

```bash
# Nyalakan pod ComfyUI dulu, catat POD_ID
cd /home/ubuntu/rakabot-serverless
./fetch_and_fix.sh <POD_ID>

# Verifikasi: node 65 harus punya positive_prompt & negative_prompt
python3 -c "
import json
d=json.load(open('workflow_api.json'))
print(list(d['65']['inputs'].keys()))
"
```

### 2. Pilih mode model

**MODE=volume (direkomendasikan)**
- Buat Network Volume di RunPod (~50GB, ~$3.5/bulan)
- Download model ke volume (jalankan sekali):
  ```bash
  python3 download_models.py /runpod-volume/ComfyUI/models
  ```
- Attach volume ke endpoint di Console
- Image tetap kecil (~8GB), cold start cepat

**MODE=bundle**
- Tanpa volume, model ikut di image
- Build: `docker build --build-arg MODE=bundle -t ... .`
- Image jadi ~40GB (butuh registry kuota besar)

## Build & Deploy

```bash
# Build
docker build -t akarai-wan22-animate:latest .

# Push
docker tag akarai-wan22-animate:latest <user>/akarai-wan22-animate:latest
docker push <user>/akarai-wan22-animate:latest
```

### Setting Endpoint di RunPod Console

| Setting | Nilai |
|---|---|
| Type | Serverless |
| GPU | RTX 5090 / 48GB+ VRAM |
| Container Image | `<user>/akarai-wan22-animate:latest` |
| Network Volume | (MODE=volume) pilih volume yang sudah diisi model |
| Min Workers | 0 (hemat) |
| Max Workers | 3 (sesuai kebutuhan) |
| Idle Timeout | 5 detik |
| FlashBoot | ON |

### Environment Variables (opsional)

```
BUCKET_ENDPOINT_URL       = https://xxx.r2.cloudflarestorage.com
BUCKET_ACCESS_KEY_ID      = xxx
BUCKET_SECRET_ACCESS_KEY  = xxx
BUCKET_NAME               = akarai-output
MODE                      = volume   (default)
```

Kalau S3 tidak diset, output dikembalikan sebagai base64.
Peringatan: video 15 detik ~5-15MB, base64 jadi ~2x lipat.

## Test

```bash
export RUNPOD_ENDPOINT_ID=xxxxx
export RUNPOD_API_KEY=xxx

# Siapkan file test
#   test_ref.png    -> foto referensi
#   test_motion.mp4 -> video referensi 720x1280, max 15 detik

python3 test_local.py
```

## Catatan Penting

1. **Batas request RunPod**: 10MB (`/run`), 20MB (`/runsync`).
   Video 15 detik + foto bisa mendekati batas. Kalau mentok,
   pakai presigned URL (belum diimplement di handler v1).

2. **Cold start** tetap ada (~30-90 detik) untuk load model ke VRAM.
   FlashBoot membantu.

3. **Durasi video** dibatasi 15 detik (437 frame @30fps).

4. **Workflow belum diuji di serverless** — baru diuji di pod.
   Setelah endpoint jadi, wajib test end-to-end dulu.

## Status

- [x] Struktur folder
- [x] handler.py (valid syntax)
- [x] Dockerfile revisi (model tidak di-bundle)
- [x] URL model diverifikasi (6/6 HTTP 200)
- [x] download_models.py
- [x] start.sh (symlink volume)
- [ ] **Fix nama widget** (butuh pod hidup)
- [ ] Build & push image
- [ ] Deploy endpoint
- [ ] Test end-to-end
