# WORKFLOW AKTIF — v4 (sesuai workflow TERBARU Pak Raka)

**Dibuat:** 2026-09-14
**File:** `/home/ubuntu/rakabot-serverless/workflow_serverless_animate.json`
**md5:** `9f5faa316e5f6edbdc9155119580f064`  (9.561 B, **28 node**)
**Commit:** `1a74aa8`

> **ATURAN:** setiap perubahan workflow HARUS ditanyakan dulu ke Pak Raka.
> Jangan buang/ubah node tanpa izin — termasuk node yang tampak orphan.
> **Acuan = workflow TERBARU Pak Raka**, bukan commit lama.

## Riwayat versi

| Versi | md5 | Isi |
|---|---|---|
| baseline | `ac10917b…` | 27 node, sebelum v3 |
| v3 | `e1740a60…` | mekanisme #2 (ContextOptions + looping mati) + face_strength 1.0 + blocks_to_swap 30 |
| **v4 (aktif)** | **`9f5faa31…`** | v3 **+ 5 item** mengikuti workflow terbaru Pak Raka |

## 5 item yang disamakan dengan workflow terbaru Pak Raka

| # | Item | Node | Sebelum | Sesudah |
|---|---|---|---|---|
| 1 | Resolusi internal | `[150]` INTConstant | 720 | **480** |
| 1 | Resolusi internal | `[151]` INTConstant | 1280 | **832** |
| 1 | Cara pas gambar | `[64]` ImageResizeKJv2 | `pad_edge_pixel` / `top` | **`crop` / `center`** |
| 2 | base_precision | `[22]` WanVideoModelLoader | `fp16_fast` | **`bf16`** |
| 3 | force_offload | `[62]` WanVideoAnimateEmbeds | `False` | **`True`** |
| 4 | tiled_vae | `[62]` WanVideoAnimateEmbeds | `True` | **`False`** |
| 5 | Model | `[22]` WanVideoModelLoader | `..._fp8_e4m3fn_scaled_KJ` (v1) | **`..._fp8_scaled_e4m3fn_KJ_v2`** |

**8 baris diff** (item 1 mencakup 4 baris karena `[64]` ikut menyesuaikan cara crop).

## Model v2 — wajib build image

- v2: `Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors` = **17,3 GB**
- v1: `Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors` = 18,4 GB
- **v2 lebih kecil 1,1 GB.** v1 **DIPERTAHANKAN** di image supaya rollback tidak perlu rebuild.
- Ditambahkan ke: `Dockerfile.vast` (baris ~119), `provision_wan_animate.sh`, `download_models.py`
- Build via GH Actions (push ke `main` → `.github/workflows/build-vast-image.yml`)
- Image: `ghcr.io/rakaseptian/akarai-wan22-animate:latest`

## Yang DIPERTAHANKAN dari v3 (mekanisme #2)

| Node | Nilai | Fungsi |
|---|---|---|
| `[301]` WanVideoContextOptions | `static_standard` 81/4/32 freenoise linear | attention bergeser utk video panjang |
| `[27].context_options` | `["301", 0]` | aktifkan ContextOptions |
| `[62].frame_window_size` | `["63", 1]` | **looping MATI** (link ke jumlah frame) |
| `[51].blocks_to_swap` | `30` | antisipasi VRAM |
| `[62].face_strength` | `1.0` | sesuai #2 |
| `[27].steps` | `6` | sesuai #2 |

**Mekanisme inti:**
```
num_frames = 437, frame_window_size = 437 (link sama)
→ looping = 437 > 437 = False  → TIDAK LOOPING
→ attention dipecah ContextOptions (81 frame, stride 4, overlap 32)
```

## Yang dipertahankan dari server (tidak ada di #2)

- **Sumber pose `DWPreprocessor` (73)** — #2 memakai file `pose_00002.mp4`/`face_00002.mp4` hasil tahap-1 di PC Pak Raka (drive `D:\`), tidak ada di server.
- Rantai `28 → 201 → 42 → 30`, `DWPreprocessor → 120 → 96` untuk face mask.
- Node `[200]` `MimicMotionGetPoses` — **ADA & utuh** (orphan, tidak dieksekusi).

## ⚠️ Belum diuji render

Perubahan ini **belum pernah dirender**. Yang perlu dibuktikan render nyata:
- 480×832 + `tiled_vae=False` + 437 frame → apakah VRAM cukup (risiko OOM).
- `bf16` + model v2 → apakah lebih lambat dari v1/fp16_fast.
- ContextOptions 81 frame pada resolusi baru.

Render uji sebelumnya (instance 51015200) **gagal di sisi penyedia** — instance hilang, host berpindah, tidak pernah benar-benar render.

## Rollback

**Workflow saja (tanpa rebuild):**
```bash
cp /tmp/wf.v3_SEBELUM_5ITEM_20260914_202432.json \
   /home/ubuntu/rakabot-serverless/workflow_serverless_animate.json
```
(v3 md5 `e1740a6069677ef3a8b7d3ce87b3ea0d`)

**Penuh ke baseline:**
```bash
cp /home/ubuntu/arsip_workflow_20260914_190227/repo/workflow_serverless_animate.json \
   /home/ubuntu/rakabot-serverless/workflow_serverless_animate.json
```
(baseline md5 `ac10917b2a217aa36bf8329b2ef24e1b`, 27 node)

**Catatan:** model v1 masih ada di image, jadi kembali ke v1 tidak perlu rebuild.
