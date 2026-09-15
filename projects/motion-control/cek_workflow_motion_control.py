#!/usr/bin/env python3
"""Periksa apakah workflow produksi masih SESUAI acuan project 'motion-control'.

Pakai:
    python3 cek_workflow_motion_control.py          # periksa + lapor
    python3 cek_workflow_motion_control.py --kunci  # kunci ulang (butuh izin Pak Raka)

Jalankan SEBELUM dan SESUDAH setiap render, atau kapan pun curiga workflow berubah.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from datetime import datetime

PROJ = pathlib.Path("/home/ubuntu/rakabot-serverless/projects/motion-control")
MANIFEST = PROJ / "MANIFEST_KUNCI.json"
PRODUKSI = pathlib.Path("/home/ubuntu/rakabot-serverless/workflow_serverless_animate.json")
ACUAN = PROJ / "workflow_MOTION_CONTROL_KUNCI.json"

HARUS = {
    "pose_node": "WanVideoUniAnimateDWPoseDetector",
    "pose_slot_ke_62": ["402", 0],
    "face_node": "PoseAndFaceDetection",
    "face_slot_ke_62": ["401", 1],
    "face_strength": 1.0,
    "pose_strength": 1.0,
    "steps": 6,
    "fps": 30,
    "cfg": 1,
    "frame_load_cap": 0,
}


def md5(p: pathlib.Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def periksa(verbose: bool = True) -> tuple[bool, list[str]]:
    masalah: list[str] = []
    if not PRODUKSI.exists():
        return False, [f"file produksi tidak ada: {PRODUKSI}"]

    man = json.loads(MANIFEST.read_text())
    d = json.loads(PRODUKSI.read_text())

    # 1. md5 harus sama dgn acuan terkuncil
    m_now, m_ref = md5(PRODUKSI), man["md5"]
    if m_now != m_ref:
        masalah.append(f"md5 BERUBAH: sekarang {m_now}, acuan {m_ref}")

    # 2. acuan & produksi harus identik
    if ACUAN.exists() and md5(ACUAN) != m_now:
        masalah.append("salinan acuan berbeda dari file produksi")

    # 3. cek isi kunci
    try:
        if d["402"]["class_type"] != HARUS["pose_node"]:
            masalah.append(f"pose node = {d['402']['class_type']}")
        if d["62"]["inputs"]["pose_images"] != HARUS["pose_slot_ke_62"]:
            masalah.append(f"pose_images = {d['62']['inputs']['pose_images']}")
        if d["401"]["class_type"] != HARUS["face_node"]:
            masalah.append(f"face node = {d['401']['class_type']}")
        if d["62"]["inputs"]["face_images"] != HARUS["face_slot_ke_62"]:
            masalah.append(f"face_images = {d['62']['inputs']['face_images']}")
        for node, key, nama in (
            ("62", "face_strength", "face_strength"),
            ("62", "pose_strength", "pose_strength"),
            ("27", "steps", "steps"),
            ("27", "cfg", "cfg"),
            ("30", "frame_rate", "fps"),
            ("63", "frame_load_cap", "frame_load_cap"),
        ):
            v = d[node]["inputs"][key]
            if v != HARUS[nama]:
                masalah.append(f"{nama} = {v} (harus {HARUS[nama]})")
    except KeyError as e:
        masalah.append(f"struktur workflow berubah, kunci hilang: {e}")

    if verbose:
        print(f"project      : {man['project']}")
        print(f"status       : {man['status']}")
        print(f"file produksi: {PRODUKSI}")
        print(f"md5 sekarang : {m_now}")
        print(f"md5 acuan    : {m_ref}")
        print(f"pose         : {d.get('402', {}).get('class_type')} "
              f"-> {d.get('62', {}).get('inputs', {}).get('pose_images')}")
        print(f"face         : {d.get('401', {}).get('class_type')} "
              f"-> {d.get('62', {}).get('inputs', {}).get('face_images')} "
              f"(strength {d.get('62', {}).get('inputs', {}).get('face_strength')})")
        print()
        if masalah:
            print("❌ WORKFLOW BERUBAH DARI ACUAN:")
            for m in masalah:
                print(f"   - {m}")
            print("\n   TANYAKAN IZIN PAK RAKA sebelum melanjutkan render.")
        else:
            print("✅ WORKFLOW SESUAI ACUAN 'motion-control' — aman dipakai render.")
    return (not masalah), masalah


def kunci_ulang() -> None:
    """Jadikan file produksi saat ini sebagai acuan baru (HANYA dgn izin Pak Raka)."""
    man = json.loads(MANIFEST.read_text())
    b = PRODUKSI.read_bytes()
    ACUAN.write_bytes(b)
    (PROJ / "workflow_motion_control.json").write_bytes(b)
    man["md5"] = hashlib.md5(b).hexdigest()
    man["ukuran_byte"] = len(b)
    man["dikunci_pada"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    man["catatan"] = ("DIKUNCI ULANG. Perubahan sebelumnya sudah disetujui Pak Raka. "
                      + man["catatan"])
    MANIFEST.write_text(json.dumps(man, indent=2, ensure_ascii=False))
    print(f"✅ Acuan 'motion-control' dikunci ulang. md5 baru: {man['md5']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kunci", action="store_true",
                    help="kunci ulang acuan = file produksi saat ini (butuh izin Pak Raka)")
    a = ap.parse_args()
    if a.kunci:
        kunci_ulang()
        sys.exit(0)
    ok, _ = periksa()
    sys.exit(0 if ok else 1)
