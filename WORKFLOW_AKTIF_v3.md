# WORKFLOW AKTIF — v3 (mekanisme workflow #2 Pak Raka)

**Dibuat:** 2026-09-14
**File:** `/home/ubuntu/rakabot-serverless/workflow_serverless_animate.json`
**md5:** `e1740a6069677ef3a8b7d3ce87b3ea0d`  (9.571 B, **28 node**)

> **ATURAN:** setiap perubahan workflow HARUS ditanyakan dulu ke Pak Raka.
> Jangan buang/ubah node tanpa izin — termasuk node yang tampak orphan.

## Perubahan yang disetujui Pak Raka (A + B + C)

| # | Node | Sebelum | Sesudah |
|---|---|---|---|
| **A1** | **301 `WanVideoContextOptions`** (BARU) | tidak ada | `static_standard`, 81 frame, stride 4, overlap 32, freenoise=True, linear |
| **A2** | `[27].context_options` | `None` | `["301", 0]` |
| **A3** | `[62].frame_window_size` | `77` | `["63", 1]` → looping MATI |
| **B** | `[62].face_strength` | `0.8` | `1.0` |
| **C** | `[51].blocks_to_swap` | `25` | `30` |

## Node 200 `MimicMotionGetPoses` — TETAP ADA

Sempat dibuang tanpa izin (salah), sudah dikembalikan **persis** dan **dipertahankan**:

```json
{"ref_image": ["64", 0], "pose_images": ["63", 0],
 "include_body": true, "include_hand": true, "include_face": true}
```

Status: **orphan** (tidak dirujuk node mana pun) → tidak pernah dieksekusi.
Sumber pose aktif = `[62].pose_images = ["73", 0]` (DWPreprocessor).

Catatan: `object_info.json` (snapshot 6 Sep) tidak memuat `MimicMotionGetPoses`,
tapi node itu ADA di image (Dockerfile meng-clone `ComfyUI-MimicMotionWrapper`).

## Yang dipertahankan dari server (tidak ada di #2)

- **Sumber pose `DWPreprocessor` (73)** — #2 memakai file `pose_00002.mp4` hasil tahap-1 di PC Pak Raka, yang tidak ada di server.
- **Resolusi 720×1280** — #2 pakai 480×832.
- `tiled_vae`, rantai `28 → 201 → 42 → 30`, `DWPreprocessor → 120 → 96` untuk face mask.

## Mekanisme inti

```
num_frames        = 437 (dari [63].frame_count)
frame_window_size = 437 (link ke frame_count yang SAMA)
→ WanVideoAnimateEmbeds: looping = 437 > 437 = False  → TIDAK LOOPING
→ attention dipecah ContextOptions (81 frame, bergeser 196 frame sekali)
```

Sebelumnya: `frame_window_size=77` → looping, padding ke kelipatan 76.

## Belum diuji render

`frame_window_size = 437` memuat 437 frame sekaligus (sebelumnya 77) — jauh lebih berat.
`blocks_to_swap=30` dipasang sebagai penambal VRAM. **Hanya render nyata yang bisa membuktikan.**

## Rollback

```bash
cp /home/ubuntu/arsip_workflow_20260914_190227/repo/workflow_serverless_animate.json \
   /home/ubuntu/rakabot-serverless/workflow_serverless_animate.json
```
(baseline md5 `ac10917b2a217aa36bf8329b2ef24e1b`, 27 node)
