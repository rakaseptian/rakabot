# Project: MOTION CONTROL

> **Status: 🔒 TERKUNCI** — Jangan ubah tanpa izin Pak Raka.

Nama resmi project ini: **motion-control**.
Dikunci: **15 September 2026**.

---

## Apa ini?

Workflow render video gerakan (motion control) yang **berhasil** memperbaiki
masalah **gerakan tangan aneh di detik-detik awal** — dan sekarang jadi
**acuan tetap** untuk semua render selanjutnya.

## Spesifikasi

| Parameter | Nilai |
|---|---|
| Resolusi | **720×1280** |
| FPS | **30** |
| Durasi maks | 14,57 detik (437 frame) |
| Steps | **6** |
| CFG | 1 |
| Scheduler | dpm++_sde, shift 5.0 |
| **POSE** | `WanVideoUniAnimateDWPoseDetector` `[402]` → `[62].pose_images` |
| **FACE** | `PoseAndFaceDetection` `[401]` → `[62].face_images` |
| face_strength | **1.0** (wajah tidak diubah) |
| pose_strength | 1.0 |
| context_frames / overlap | 81 / 32 |
| blocks_to_swap | 30 |

**File produksi:** `/home/ubuntu/rakabot-serverless/workflow_serverless_animate.json`
**md5 terkunci:** `fc029cad3e7bc48791d62b5c22af39c0` (25 node, 8858 byte)

## Kenapa berhasil?

Masalah lama: node `MimicMotionGetPoses` (`[200]`) memakai **`np.polyfit`
untuk skala global** (`a=0,755`) yang dihitung sekali untuk semua frame →
salah di frame awal → tangan tampak aneh/kaku/melayang.

Solusi: ganti ke `WanVideoUniAnimateDWPoseDetector` (`[402]`) yang mendeteksi
pose **per frame**. Wajah **tidak disentuh** (`[401]` + `face_strength 1.0`).

## Bukti keberhasilan

| Uji | Hasil |
|---|---|
| Uji 90 frame | `/tmp/wan_media/hasil_28a635f2.mp4` |
| Render penuh | `/tmp/wan_media/hasil_5fd6a628.mp4` (437 frame, 14,57 dtk) |
| Verifikasi | 437 frame — **0 gelap, 0 blur, 0 macet** |
| Biaya | **$0,45** (39 menit di RTX 5090) |
| Perbandingan | Tangan jauh lebih rileks & anatomis di **semua** frame |

## 🔒 Aturan penguncian

1. **JANGAN ubah** `workflow_serverless_animate.json` tanpa izin eksplisit Pak Raka.
2. **Sebelum & sesudah** render, jalankan pemeriksa:
   ```bash
   python3 /home/ubuntu/rakabot-serverless/projects/motion-control/cek_workflow_motion_control.py
   ```
   - ✅ hijau → aman dipakai render
   - ❌ merah → **tanya Pak Raka dulu**, jangan render
3. Kalau Pak Raka **menyetujui** perubahan, kunci ulang:
   ```bash
   python3 .../cek_workflow_motion_control.py --kunci
   ```
4. **Backup pose lama** (MimicMotion): `arsip/motion-control/workflow_SEBELUM_motion_control.json`
   (salinan sahih dari `git HEAD~1`, md5 `66892a57117a`)

## Berkas di folder ini

| File | Fungsi |
|---|---|
| `workflow_MOTION_CONTROL_KUNCI.json` | Salinan acuan terkunci (pembanding) |
| `workflow_motion_control.json` | Salinan kerja |
| `MANIFEST_KUNCI.json` | Metadata + md5 terkunci |
| `cek_workflow_motion_control.py` | Pemeriksa + pengunci ulang |
| `README.md` | Dokumen ini |

## Catatan operasional

- Bot mengirim workflow ke worker lewat **payload `workflow_json`** yang dibaca
  dari **file lokal** — bukan dari template Vast. Jadi cukup ganti file lokal,
  tanpa update template/workergroup.
- Host yang sudah punya cache image `:v3` = **45511** (render berikutnya instan).
- Keep-alive ping (opsi hemat): `/home/ubuntu/rakabot/keepalive_guard.py`.

## Arsip lengkap

Salinan cadangan tersimpan permanen di `/home/ubuntu/rakabot/arsip/motion-control/`:

| File | Isi |
|---|---|
| `workflow_SEBELUM_motion_control.json` | Produksi LAMA (pose MimicMotion `[200]`), dari git HEAD~1 |
| `workflow_yang_dipromosikan.json` | Workflow pose baru yang jadi acuan |
| `vast_wan.py.SEBELUM_OPTIOND` | Kode bot sebelum perubahan Opsi D |
| `.env.SEBELUM_OPTIOND` | Konfigurasi sebelum perubahan Opsi D |

> ⚠️ **Catatan koreksi (15-09-2026):** pernah ada file bernama
> `/tmp/workflow_PRODUKSI_MimicMotion_*.json` yang **salah label** — isinya
> ternyata workflow uji 90 frame (pose baru), bukan produksi MimicMotion.
> Sudah diganti dengan salinan sahih dari git.
