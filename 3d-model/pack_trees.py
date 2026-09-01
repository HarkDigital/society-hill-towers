#!/usr/bin/env python3
"""lidar_cache/phl_trees_raw.json -> trees.b64 + tree_names.json : the real PPR
tree inventory packed for the app (int16, 0.2 m units, wide tier only).
Layout: Int32[4] header (magic 0x53485454 'SHTT', nTrees, nNames, 0), then
Int16 x4 per tree: x*5, z*5, dbh_inches, nameIdx.
tree_names.json: {"names": [common...], "latin": [botanical...], "g": [groupIdx...]}
Filtering: clip to the wide box, drop dead/stump rows, dedupe within 0.6 m, and
reject trees inside a building footprint (lidar_cache/phl_footprints_local.json,
holes = courtyards stay plantable). Groups drive canopy hue/shape at runtime.
Frame: philly_frame.py (the scene's own projection). This script used to hardcode
KX=85350, which put its output up to ~1.1 m east of the scene at the far ring
(~0.25 m at the wide box edge); the committed trees.b64 keeps that offset until
the next rerun."""
import base64, json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
from philly_frame import LON0, LAT0, KX, KZ   # the one scene frame
WIDE = (-3700, 2300, -4480, 6400)    # pack_wide.py wide bbox, local meters
MAGIC = 0x53485454                   # 'SHTT'
DEAD = re.compile(r'stump|dead|vacan|removal|removed|no tree|planting site', re.I)

# species group by name (first match wins); groups drive canopy hue/shape/size
GROUPS = [
    (1, r'plane|sycamore'), (2, r'maple|boxelder'), (3, r'\boak'),
    (4, r'cherry|pear|plum|crabapple|serviceberry|hawthorn|redbud|dogwood|magnolia|lilac|crape|fringetree|smoketree'),
    (5, r'locust|pagoda'), (6, r'zelkova|elm|hackberry|hornbeam'), (7, r'ginkgo'),
    (8, r'linden|basswood'),
    (9, r'pine|spruce|\bfir\b|cedar|juniper|arborvitae|cypress|hemlock|holly|yew'),
    (10, r'birch|poplar|aspen|willow|sweetgum|tulip|sassafras|katsura'),
    (11, r'ailanthus|mulberry|catalpa|paulownia|amur|osage'),
]
GROUPS = [(g, re.compile(rx, re.I)) for g, rx in GROUPS]

def group_of(name):
    for g, rx in GROUPS:
        if rx.search(name):
            return g
    return 0

def tcase(s):
    return ' '.join(w and w[0].upper() + w[1:].lower() for w in s.split())

def pretty(raw):
    """'PLATANUS X ACERIFOLIA - LONDON PLANETREE' -> ('London Planetree', 'Platanus × acerifolia')"""
    if 'UNKNOWN' in raw.upper().replace(' ', ''):
        return 'Unknown Species', ''
    latin, common = (raw.split(' - ', 1) + [''])[:2] if ' - ' in raw else ('', raw)
    lw = latin.strip().lower().split()
    latin = ' '.join(['×' if w == 'x' else (w.capitalize() if i == 0 else w) for i, w in enumerate(lw)])
    return tcase(common.strip() or raw), latin

def ring_grid(fps, cell=12):
    grid = {}
    boxes = []
    for i, (_h, _a, rings) in enumerate(fps):
        o = rings[0]
        xs = o[0::2]; zs = o[1::2]
        boxes.append((min(xs), max(xs), min(zs), max(zs)))
        x0, x1, z0, z1 = boxes[-1]
        if x1 < WIDE[0] - 5 or x0 > WIDE[1] + 5 or z1 < WIDE[2] - 5 or z0 > WIDE[3] + 5:
            continue
        for gx in range(int(x0 // cell), int(x1 // cell) + 1):
            for gz in range(int(z0 // cell), int(z1 // cell) + 1):
                grid.setdefault((gx, gz), []).append(i)
    return grid, boxes

def pip_flat(x, z, flat):
    inside = False
    n = len(flat) // 2
    j = n - 1
    for i in range(n):
        xi, zi = flat[i * 2], flat[i * 2 + 1]
        xj, zj = flat[j * 2], flat[j * 2 + 1]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside

def main():
    raw = json.load(open(os.path.join(CACHE, 'phl_trees_raw.json')))['trees']
    fp_path = os.path.join(CACHE, 'phl_footprints_local.json')
    fps = json.load(open(fp_path))['fps'] if os.path.exists(fp_path) else []
    grid, boxes = ring_grid(fps) if fps else ({}, [])
    print(f'{len(raw)} raw trees, {len(fps)} footprints for rejection', flush=True)

    kept = []
    names = {}          # (common, latin) -> idx
    name_list = []
    seen = {}           # 0.6 m dedupe grid
    n_clip = n_dead = n_dupe = n_bldg = 0
    for lon, lat, dbh, nm in raw:
        if DEAD.search(nm or ''):
            n_dead += 1
            continue
        x = (lon - LON0) * KX
        z = (LAT0 - lat) * KZ
        if not (WIDE[0] <= x <= WIDE[1] and WIDE[2] <= z <= WIDE[3]):
            n_clip += 1
            continue
        key = (int(x / 0.6), int(z / 0.6))
        if key in seen:
            n_dupe += 1
            continue
        gkey = (int(x // 12), int(z // 12))
        hit = False
        for i in grid.get(gkey, ()):
            b = boxes[i]
            if not (b[0] <= x <= b[1] and b[2] <= z <= b[3]):
                continue
            rings = fps[i][2]
            if pip_flat(x, z, rings[0]) and not any(pip_flat(x, z, h) for h in rings[1:]):
                hit = True
                break
        if hit:
            n_bldg += 1
            continue
        seen[key] = 1
        common, latin = pretty(nm)
        nk = (common, latin)
        if nk not in names:
            names[nk] = len(name_list)
            name_list.append(nk)
        d = int(round(dbh)) if dbh and dbh > 0 else 6
        kept.append((x, z, max(1, min(60, d)), names[nk]))

    body = bytearray(struct.pack('<4i', MAGIC, len(kept), len(name_list), 0))
    for x, z, d, ni in kept:
        xi = int(round(x * 5)); zi = int(round(z * 5))
        assert -32767 <= xi <= 32767 and -32767 <= zi <= 32767, (x, z)
        body += struct.pack('<4h', xi, zi, d, ni)
    b64 = base64.b64encode(bytes(body)).decode('ascii')
    open(os.path.join(HERE, 'trees.b64'), 'w').write(b64)
    meta = {'names': [c for c, _l in name_list],
            'latin': [l for _c, l in name_list],
            'g': [group_of(f'{l} {c}') for c, l in name_list]}
    json.dump(meta, open(os.path.join(HERE, 'tree_names.json'), 'w'), separators=(',', ':'))

    from collections import Counter
    gc = Counter(meta['g'][ni] for _x, _z, _d, ni in kept)
    print(f'kept {len(kept)}  (clipped {n_clip}, dead {n_dead}, dupes {n_dupe}, in-building {n_bldg})')
    print(f'{len(name_list)} species; group counts {dict(sorted(gc.items()))}')
    print(f"trees.b64 {len(b64) / 1e6:.2f} MB, tree_names.json {os.path.getsize(os.path.join(HERE, 'tree_names.json')) / 1e3:.1f} KB", flush=True)

if __name__ == '__main__':
    main()
