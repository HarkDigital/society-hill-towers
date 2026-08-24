#!/usr/bin/env python3
"""Tiled Overpass fetch for the wide area (Center City, South Philly, NoLibs, Fishtown/Kensington)
plus a 50 m elevation grid. Writes osm_wide_raw.json and dem_wide.json."""
import json, math, time, urllib.request, urllib.parse, sys
S, N, W, E = 39.915, 39.986, -75.188, -75.118
ROWS, COLS = 4, 4
MIRRORS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
elements, seen = [], set()
def fetch(q):
    data = urllib.parse.urlencode({'data': q}).encode()
    last = None
    for attempt in range(6):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'sht-3d-model/1.0'})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception as e:
            last = e; time.sleep(8 + 8 * attempt)
    raise last
for i in range(ROWS):
    for j in range(COLS):
        s = S + (N - S) * i / ROWS; n = S + (N - S) * (i + 1) / ROWS
        w = W + (E - W) * j / COLS; e = W + (E - W) * (j + 1) / COLS
        bbox = f'{s:.5f},{w:.5f},{n:.5f},{e:.5f}'
        q = f'''[out:json][timeout:170];
(
  way["building"]({bbox});
  relation["building"]({bbox});
  way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|secondary|tertiary|residential|living_street|unclassified|pedestrian|service)$"]({bbox});
  way["railway"~"^(rail|light_rail|subway)$"]({bbox});
  way["leisure"~"^(park|garden|pitch|playground)$"]({bbox});
  relation["leisure"="park"]({bbox});
  way["man_made"="pier"]({bbox});
  way["natural"="water"]({bbox});
  way["landuse"~"^(grass|cemetery|recreation_ground)$"]({bbox});
);
(._;>;);
out body qt;'''
        t0 = time.time()
        d = fetch(q)
        new = 0
        for el in d.get('elements', []):
            k = (el['type'], el['id'])
            if k in seen: continue
            seen.add(k); elements.append(el); new += 1
        print(f'tile {i},{j} {bbox}: +{new} elements ({time.time()-t0:.0f}s), total {len(elements)}', flush=True)
        time.sleep(6)
json.dump({'elements': elements}, open('osm_wide_raw.json', 'w'))
print('osm_wide_raw.json written', flush=True)

# elevation grid, 50 m, via OpenTopoData ned10m
lat0, lon0 = 39.945473644755005, -75.14474803850973
kx = 111320 * math.cos(math.radians(lat0)); kz = 110574
xs = list(range(-4000, 2801, 50)); zs = list(range(-4600, 3500, 50))
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
        except Exception as ex:
            time.sleep(3 + attempt * 3)
    time.sleep(1.05)
    if i % 2000 == 0: print(f'dem {i}/{len(pts)}', flush=True)
json.dump({'x0': xs[0], 'z0': zs[0], 'cell': 50, 'nx': len(xs), 'nz': len(zs),
           'rows': [[elev.get((x, z)) for x in xs] for z in zs]}, open('dem_wide.json', 'w'))
print('dem_wide.json written', flush=True)
