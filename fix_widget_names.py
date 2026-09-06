#!/usr/bin/env python3
"""
Perbaiki nama widget di workflow_api.json.

Masalah: converter GUI->API menghasilkan nama generik (value_0, value_1)
padahal ComfyUI API butuh nama asli widget (misal: positive_prompt, steps, cfg).

Cara pakai:
  python3 fix_widget_names.py object_info.json workflow_api.json

Ambil object_info.json dari pod yang hidup:
  curl -s https://<POD>-8188.proxy.runpod.net/object_info -o object_info.json
"""
import json
import sys
from collections import OrderedDict


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def get_input_names(node_info):
    """Kembalikan daftar nama input berurutan: required dulu, lalu optional."""
    names = []
    inp = node_info.get('input', {})
    for grp in ('required', 'optional'):
        for k, v in (inp.get(grp) or {}).items():
            names.append((k, v))
    return names


def is_link_input(spec):
    """Cek apakah spec ini input bertipe link (LIST of type names)."""
    if not isinstance(spec, list) or len(spec) == 0:
        return False
    first = spec[0]
    return isinstance(first, (list, str)) and not isinstance(first, dict)


def fix(api, object_info):
    stats = {'fixed': 0, 'skipped': 0, 'no_info': 0}

    for nid, node in api.items():
        ctype = node.get('class_type')
        if ctype not in object_info:
            stats['no_info'] += 1
            continue

        spec_names = get_input_names(object_info[ctype])
        # Hanya nama widget (bukan link input)
        widget_names = [k for k, v in spec_names
                        if not (isinstance(v, list) and len(v) > 0
                                and isinstance(v[0], list))]

        inputs = node.get('inputs', {})

        # Kumpulkan value_N yang belum punya nama asli
        generic = {}
        for k in list(inputs.keys()):
            if k.startswith('value_'):
                generic[int(k.split('_')[1])] = inputs.pop(k)

        if not generic:
            continue

        # Pasangkan value_N dengan nama widget urut ke-N
        # (nilai widget muncul berurutan sesuai deklarasi, link dilewati)
        avail = [n for n in widget_names if n not in inputs]
        for idx in sorted(generic.keys()):
            if idx < len(avail):
                inputs[avail[idx]] = generic[idx]
                stats['fixed'] += 1
            else:
                # tidak ada slot, simpan apa adanya
                inputs[f'value_{idx}'] = generic[idx]
                stats['skipped'] += 1

    return stats


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    oi_path = sys.argv[1]
    api_path = sys.argv[2]

    object_info = load_json(oi_path)
    api = load_json(api_path)

    stats = fix(api, object_info)

    with open(api_path, 'w', encoding='utf-8') as f:
        json.dump(api, f, indent=1)

    print(f"fixed   : {stats['fixed']}")
    print(f"skipped : {stats['skipped']}")
    print(f"no_info : {stats['no_info']}")

    # Print node kritis untuk verifikasi
    print()
    for nid in ('57', '63', '65', '62', '27', '22', '300'):
        if nid in api:
            print(nid, api[nid]['class_type'])
            print('   ', json.dumps(api[nid]['inputs'])[:300])


if __name__ == '__main__':
    main()
