#!/usr/bin/env python3
"""Fetch a 50 m USGS NED 10 m grid over the hilly northwest (East Falls,
Manayunk/Roxborough, the Wissahickon valley, Chestnut Hill) and write
dem_nw.json in the same {x0, z0, cell, nx, nz, rows} format as the other grids.
The far tier's dem_city.json is a 150 m grid — too coarse for the gorge.

The patch FEATHERS to dem_city near its border: within FEATHER meters of the
patch edge the value blends toward dem_city's bilinear interpolation, so every
consumer (app demAbs, bake_overpasses dem_abs) can simply sample this grid
first with no seam logic of its own.

Checkpointed like fetch_city.py's DEM: elevations accumulate in
lidar_cache/dem_nw_elev.json so reruns resume. Run with plain python3."""
import json, math, os, time, urllib.request
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
os.makedirs(CACHE, exist_ok=True)
CKPT = os.path.join(CACHE, 'dem_nw_elev.json')

lat0, lon0 = 39.945473644755005, -75.14474803850973
kx = 111320 * math.cos(math.radians(lat0)); kz = 110574
X0, X1, Z0, Z1, CELL = -10600, -2600, -15600, -6600, 50
FEATHER = 250.0

xs = list(range(X0, X1 + 1, CELL))
zs = list(range(Z0, Z1 + 1, CELL))
pts = [(x, z) for z in zs for x in xs]
print(f'{len(xs)}x{len(zs)} = {len(pts)} samples', flush=True)

elev = {}
if os.path.exists(CKPT):
    elev = {tuple(map(int, k.split(','))): v for k, v in json.load(open(CKPT)).items()}
    print(f'resuming with {len(elev)} cached samples', flush=True)

def save_ckpt():
    with open(CKPT + '.tmp', 'w') as f:
        json.dump({f'{x},{z}': v for (x, z), v in elev.items()}, f)
    os.replace(CKPT + '.tmp', CKPT)

todo = [p for p in pts if p not in elev]
for i in range(0, len(todo), 100):
    chunk = todo[i:i + 100]
    locs = '|'.join(f'{lat0 - z / kz:.6f},{lon0 + x / kx:.6f}' for x, z in chunk)
    url = 'https://api.opentopodata.org/v1/ned10m?locations=' + locs
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                d = json.load(r)
            for (x, z), res in zip(chunk, d['results']):
                elev[(x, z)] = res['elevation']
            break
        except Exception:
            time.sleep(4 + attempt * 4)
    time.sleep(1.05)
    if (i // 100) % 20 == 0:
        save_ckpt()
        print(f'dem_nw {len(elev)}/{len(pts)}', flush=True)
save_ckpt()
if provenance: provenance.record('fetch_dem_nw.opentopodata', 'https://api.opentopodata.org/v1/ned10m', f'ned10m {CELL} m grid x {X0}..{X1} z {Z0}..{Z1}', len(elev))
missing = sum(1 for p in pts if p not in elev)
if missing:
    raise SystemExit(f'{missing} samples still missing after fetch — rerun to resume')

# ---- feather toward dem_city near the border ----
demc = json.load(open(os.path.join(HERE, 'dem_city.json')))
def sample_city(x, z):
    fx = (x - demc['x0']) / demc['cell']; fz = (z - demc['z0']) / demc['cell']
    if fx < 0 or fz < 0 or fx > demc['nx'] - 1 or fz > demc['nz'] - 1:
        return None
    i = max(0, min(demc['nx'] - 2, int(fx))); j = max(0, min(demc['nz'] - 2, int(fz)))
    tx = max(0.0, min(1.0, fx - i)); tz = max(0.0, min(1.0, fz - j))
    r0, r1 = demc['rows'][j], demc['rows'][j + 1]
    v = lambda a: 4.0 if a is None else a
    a = v(r0[i]) * (1 - tx) + v(r0[i + 1]) * tx
    b = v(r1[i]) * (1 - tx) + v(r1[i + 1]) * tx
    return a * (1 - tz) + b * tz

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

rows = []
n_feather = 0
for z in zs:
    row = []
    for x in xs:
        v = elev.get((x, z))
        edge = min(x - X0, X1 - x, z - Z0, Z1 - z)
        if v is None:
            row.append(None)
            continue
        w = smooth(edge / FEATHER)
        if w < 1.0:
            c = sample_city(x, z)
            if c is not None:
                v = c * (1 - w) + v * w
                n_feather += 1
        row.append(round(v, 2))
    rows.append(row)

out = {'x0': X0, 'z0': Z0, 'cell': CELL, 'nx': len(xs), 'nz': len(zs), 'rows': rows}
with open(os.path.join(HERE, 'dem_nw.json'), 'w') as f:
    json.dump(out, f, separators=(',', ':'))
kb = os.path.getsize(os.path.join(HERE, 'dem_nw.json')) / 1e3
print(f'dem_nw.json written ({len(xs)}x{len(zs)}, {n_feather} feathered border samples, {kb:.0f} KB)', flush=True)
