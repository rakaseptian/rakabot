#!/usr/bin/env python3
"""
Audit isi (value-based): bandingkan SEMUA nilai widget workflow UI punya user
dengan workflow_api.json (serverless). Tidak pakai nama field (urutan object_info
tidak bisa dipercaya), tapi cek keberadaan nilai.
"""
import json, sys

UI_PATH = sys.argv[1]
API_PATH = sys.argv[2]

ui = json.load(open(UI_PATH))
api = json.load(open(API_PATH))
ui_nodes = {str(n["id"]): n for n in ui["nodes"]}

# Nilai yang wajar berbeda: placeholder test
TEST_ONLY = {"97963.png", "VID_20260905_095149_031.mp4",
             "test_ref_small.jpg", "test_motion_small.mp4",
             "__REF_IMAGE__", "__REF_VIDEO__"}

print("=" * 74)
print("AUDIT ISI: nilai widget UI punya user  vs  API serverless")
print("=" * 74)

missing_global = []

for nid in sorted(set(ui_nodes) & set(api), key=lambda x: int(x)):
    n = ui_nodes[nid]
    ctype = n["type"]
    wv = n.get("widgets_values")
    if not wv:
        continue

    api_inp = api[nid]["inputs"]

    # Kumpulkan SEMUA nilai di API node ini (scalar + elemen link)
    api_vals = set()
    for v in api_inp.values():
        if isinstance(v, list):
            for e in v:
                api_vals.add(json.dumps(e))
        else:
            api_vals.add(json.dumps(v))

    pairs = list(wv.items()) if isinstance(wv, dict) else [(None, v) for v in wv]
    missing = []
    for fname, val in pairs:
        # lewati field preview/UI-only
        if isinstance(fname, str) and fname.lower() in ("videopreview", "output", "preview"):
            continue
        if isinstance(val, str) and ("<tr>" in val or val.startswith("<")):
            continue
        if val in TEST_ONLY:
            continue
        if json.dumps(val) not in api_vals:
            missing.append((fname, val))

    if missing:
        print(f"\n[node {nid}] {ctype}")
        for fname, val in missing:
            print(f"   ⚠ {str(fname):24} = {json.dumps(val)[:56]}")
        missing_global.extend([(nid, ctype, f, v) for f, v in missing])

print("\n" + "=" * 74)
if not missing_global:
    print("✅ SEMUA nilai widget punya user ADA di versi API serverless")
    print("   (kecuali nama file input test yang memang diganti placeholder)")
else:
    print(f"⚠ Nilai punya user yang TIDAK ADA di API: {len(missing_global)}")
print("=" * 74)
