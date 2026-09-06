#!/usr/bin/env python3
"""
Patch lazy PromptServer.instance.

Masalah:
  ComfyUI 0.30 tidak mengekspos PromptServer.instance di decorator scope
  (saat modul di-import). Custom node Kijai & VHS mengaksesnya langsung
  di level modul, sehingga import gagal.

Solusi:
  Ubah akses langsung `server.PromptServer.instance` menjadi lazy function
  yang baru dipanggil saat first-use (setelah server terbentuk).

Terbukti bekerja di pod gunz1stgoe4ew8 (WanVideoWrapper + VHS load sukses).
"""
import os
import re
import sys

COMFY_ROOT = os.environ.get("COMFY_ROOT", "/comfyui")

TARGETS = [
    # (relative path, pola lama, pola baru)
    (
        "custom_nodes/ComfyUI-WanVideoWrapper/latent_preview.py",
        r"serv\s*=\s*server\.PromptServer\.instance",
        None,  # auto-generate
    ),
    (
        "custom_nodes/ComfyUI-VideoHelperSuite/videohelpersuite/latent_preview.py",
        r"server\.PromptServer\.instance",
        None,
    ),
    (
        "custom_nodes/ComfyUI-VideoHelperSuite/videohelpersuite/utils.py",
        r"server\.PromptServer\.instance",
        None,
    ),
    (
        "custom_nodes/ComfyUI-VideoHelperSuite/videohelpersuite/server.py",
        r"server\.PromptServer\.instance",
        None,
    ),
]


def make_lazy(name="_ps_instance"):
    """Kembalikan helper function definition."""
    return f'''
def {name}():
    """Lazy accessor untuk PromptServer.instance (patch by AkarAI)."""
    import server as _srv
    return _srv.PromptServer.instance

'''


def patch_file(path):
    if not os.path.exists(path):
        print(f"[SKIP] tidak ada: {path}")
        return False

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()

    if "Lazy accessor untuk PromptServer.instance" in src:
        print(f"[OK]   sudah dipatch: {path}")
        return True

    # Cari pola yang cocok
    patterns = [
        r"serv\s*=\s*server\.PromptServer\.instance",
        r"server\.PromptServer\.instance",
    ]

    matched = False
    for pat in patterns:
        if re.search(pat, src):
            matched = True
            break

    if not matched:
        print(f"[SKIP] tidak ada pola: {path}")
        return False

    # Sisipkan helper function setelah import server
    lazy_def = make_lazy()

    if re.search(r"^import server\s*$", src, re.M):
        src = re.sub(
            r"^import server\s*$",
            "import server\n" + lazy_def,
            src,
            count=1,
            flags=re.M,
        )
    elif re.search(r"^from comfy\.cli_args import", src, re.M):
        # sisipkan di bawah baris import terakhir sebelum dipakai
        src = lazy_def + src
    else:
        src = lazy_def + src

    # Ganti pemakaian langsung dengan pemanggilan lazy
    src = re.sub(r"serv\s*=\s*server\.PromptServer\.instance", "serv = _ps_instance()", src)
    src = re.sub(r"\bserver\.PromptServer\.instance\b", "_ps_instance()", src)

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"[FIX]  dipatch: {path}")
    return True


def main():
    print(f"COMFY_ROOT = {COMFY_ROOT}")
    ok = 0
    for rel, pat, _ in TARGETS:
        full = os.path.join(COMFY_ROOT, rel)
        if patch_file(full):
            ok += 1
    print(f"\nSelesai. {ok}/{len(TARGETS)} file dipatch.")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
