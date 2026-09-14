# AkarAI Studio — Wan 2.2 Animate Serverless Worker

Worker serverless **Vast.ai** untuk video Wan 2.2 Animate (Mode MOVE).

> **Jalur produksi = Vast.ai.** File jalur RunPod lama sudah dihapus
> (arsip: `/home/ubuntu/arsip_runpod_20260914_203850/`). Jalur RunPod **tidak dipakai**.

## Alur

```
Bot Telegram (rakabot) --> vast_wan.py --> Vast.ai Serverless Endpoint 36584
                                              |
                                              v
                                    pyworker (BACKEND=comfyui-json)
                                    terima workflow_json dari payload
                                              |
                                              v
                                    ComfyUI internal :18188
                                              |
                                              v
                                    video hasil --> Telegram
```

## Isi Folder

| File | Fungsi |
|---|---|
| **`Dockerfile.vast`** | **Build image produksi** — ComfyUI + custom node + model (~36GB) |
| `.github/workflows/build-vast-image.yml` | CI build & push ke GHCR (otomatis saat `Dockerfile.vast` berubah) |
| `provision_wan_animate.sh` | Unduh model saat worker pertama nyala (Phase 9) |
| `download_models.py` | Daftar model + unduhan manual |
| **`workflow_serverless_animate.json`** | **Workflow aktif** — dikirim `vast_wan.py` sebagai `workflow_json` |
| `workflow_api.json` | Disalin ke image (`Dockerfile.vast:178`); juga dipakai benchmark |
| `patches/apply_patches.py` | Patch custom node |
| `requirements.txt` | Dependensi Python (dipakai `Dockerfile.vast:43`) |
| `audit_workflow.py` | Audit nilai workflow vs acuan |
| `fix_widget_names.py` | Konversi `value_N` → nama widget asli |
| `README.md` | Dokumen ini |

## Image

- Registry: `ghcr.io/rakaseptian/akarai-wan22-animate:latest`
- Base: `vastai/comfy:v0.34.0-cuda-13.2-py312`
- Build: push ke `main` yang menyentuh `Dockerfile.vast` → GH Actions jalan otomatis
- **Tidak ada `ENTRYPOINT`/`CMD`** → worker memakai **pyworker bawaan image dasar**
  (`BACKEND=comfyui-json`), yang menerima `workflow_json` **dari payload**.

## Model di image

| Model | Ukuran |
|---|---|
| `Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors` (v1) | 18,4 GB |
| `Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors` (v2) | 17,3 GB |
| `umt5-xxl-enc-bf16.safetensors` | 10,8 GB |
| `wan_2.1_vae.safetensors` | 0,25 GB |
| `clip_vision_h.safetensors` | 1,2 GB |
| LoRA relight + lightx2v | ~1,4 GB |
| SD1.5 (benchmark saja) | ~2 GB |

**v1 dipertahankan** supaya rollback tidak perlu rebuild image.

## Setting Endpoint (Vast.ai)

| Setting | Nilai |
|---|---|
| Endpoint ID | `36584` (`wan22-video`) |
| Workergroup | `46741` |
| Backend | `comfyui-json` |
| GPU | RTX 5090 / 48GB+ VRAM |
| Min Workers | 0 (hemat) |
| Kriteria host | RAM ≥ 64 GB, bw ≥ 1000, cuda ≥ 13.0 |

## Deploy / Update

```bash
cd /home/ubuntu/rakabot-serverless

# 1. Ubah Dockerfile.vast / workflow
# 2. Commit & push → GH Actions build otomatis
git add -A && git commit -m "..." && git push origin main

# 3. Pantau build
#    https://github.com/rakaseptian/rakabot/actions
```

**Workflow** (`workflow_serverless_animate.json`) dibaca **FRESH dari disk tiap render**
oleh `vast_wan.py` — perubahan workflow **tidak butuh rebuild image**.

## Batas

- Durasi video referensi maks **14,57 detik** (`VIDEO_DUR_MAX`, `bot.py:100`)
- 437 frame @30fps

## Catatan Penting

1. **`workflow_api.json` dipakai `Dockerfile.vast:178`** — jangan hapus, build akan gagal.
2. **`requirements.txt` dipakai `Dockerfile.vast:43`** — meski isinya `runpod==1.7.9`,
   jangan hapus tanpa mengganti isinya.
3. Jalur RunPod (handler.py/start.sh/Dockerfile) **sudah dihapus** —
   riwayat git tetap menyimpannya bila perlu dipulihkan.
4. `object_info.json` adalah snapshot **usang** (6 Sep) — jangan dijadikan acuan.
