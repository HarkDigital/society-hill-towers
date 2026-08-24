#!/usr/bin/env python3
"""Tiled Overpass fetch for the REST of Philadelphia beyond the wide box:
University City / West / Southwest + airport (A), North Philly (B),
the Northeast (C), Roxborough / Germantown / Chestnut Hill (D).
Writes osm_city_raw.json and a coarse 150 m dem_city.json.
The wide box (39.915..39.986, -75.188..-75.118) is fetched already; tiles
inside it are skipped at pack time (dedup by element id here)."""
import json, math, time, urllib.request, urllib.parse

# lat S, lat N, lon W, lon E, rows, cols
BOXES = [
    ('west-sw-airport', 39.860, 39.990, -75.285, -75.185, 5, 4),
    ('north',           39.986, 40.050, -75.190, -75.060, 3, 5),
    ('northeast',       40.050, 40.140, -75.130, -74.955, 4, 6),
    ('northwest',       39.990, 40.100, -75.285, -75.190, 4, 3),
]
MIRRORS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
           'https://overpass.private.coffee/api/interpreter']
import os
os.makedirs('city_tiles', exist_ok=True)

def fetch(q):
    data = urllib.parse.urlencode({'data': q}).encode()
    last = None
    for attempt in range(10):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'sht-3d-model/1.0'})
            with urllib.request.urlopen(req, timeout=190) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(min(120, 12 + 14 * attempt))
    raise last

tiles = []
for name, S, N, W, E, ROWS, COLS in BOXES:
    for i in range(ROWS):
        for j in range(COLS):
            s = S + (N - S) * i / ROWS; n = S + (N - S) * (i + 1) / ROWS
            w = W + (E - W) * j / COLS; e = W + (E - W) * (j + 1) / COLS
            tiles.append((f'{name}-{i}-{j}', f'{s:.5f},{w:.5f},{n:.5f},{e:.5f}'))

def tileQuery(bbox):
    return f'''[out:json][timeout:180];
(
  way["building"]({bbox});
  way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|secondary|tertiary|residential)$"]({bbox});
  way["leisure"~"^(park|golf_course|nature_reserve)$"]({bbox});
  relation["leisure"="park"]({bbox});
  way["natural"="water"]({bbox});
  relation["natural"="water"]({bbox});
  way["landuse"~"^(grass|cemetery|forest|recreation_ground)$"]({bbox});
  way["aeroway"~"^(runway|taxiway|apron)$"]({bbox});
);
(._;>;);
out body qt;'''

for rnd in range(3):   # per-tile checkpoints: rerun rounds only touch missing tiles
    missing = [(tid, bbox) for tid, bbox in tiles if not os.path.exists(f'city_tiles/{tid}.json')]
    if not missing: break
    print(f'round {rnd}: {len(missing)} tiles to fetch', flush=True)
    for tid, bbox in missing:
        t0 = time.time()
        try:
            d = fetch(tileQuery(bbox))
        except Exception as e:
            print(f'{tid} FAILED this round: {e}', flush=True)
            continue
        json.dump(d, open(f'city_tiles/{tid}.json', 'w'))
        print(f'{tid} {bbox}: {len(d.get("elements", []))} elements ({time.time()-t0:.0f}s)', flush=True)
        time.sleep(5)

elements, seen = [], set()
missing = [tid for tid, _ in tiles if not os.path.exists(f'city_tiles/{tid}.json')]
if missing:
    print(f'WARNING: {len(missing)} tiles still missing: {missing[:8]}', flush=True)
for tid, _ in tiles:
    p = f'city_tiles/{tid}.json'
    if not os.path.exists(p): continue
    for el in json.load(open(p)).get('elements', []):
        k = (el['type'], el['id'])
        if k in seen: continue
        seen.add(k); elements.append(el)
json.dump({'elements': elements}, open('osm_city_raw.json', 'w'))
print(f'osm_city_raw.json written ({len(elements)} elements)', flush=True)

# coarse 150 m DEM over the whole city bbox (single grid; wide/core grids win where present)
lat0, lon0 = 39.945473644755005, -75.14474803850973
kx = 111320 * math.cos(math.radians(lat0)); kz = 110574
xs = list(range(-12000, 16501, 150)); zs = list(range(-21700, 9701, 150))
pts = [(x, z) for z in zs for x in xs]
elev = {}
for i in range(0, len(pts), 100):
    chunk = pts[i:i + 100]
    locs = '|'.join(f'{lat0 - z / kz:.6f},{lon0 + x / kx:.6f}' for x, z in chunk)
    url = 'https://api.opentopodata.org/v1/ned10m?locations=' + locs
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                d = json.load(r)
            for (x, z), res in zip(chunk, d['results']): elev[(x, z)] = res['elevation']
            break
        except Exception:
            time.sleep(3 + attempt * 3)
    time.sleep(1.05)
    if i % 3000 == 0: print(f'dem {i}/{len(pts)}', flush=True)
json.dump({'x0': xs[0], 'z0': zs[0], 'cell': 150, 'nx': len(xs), 'nz': len(zs),
           'rows': [[elev.get((x, z)) for x in xs] for z in zs]}, open('dem_city.json', 'w'))
print('dem_city.json written', flush=True)
