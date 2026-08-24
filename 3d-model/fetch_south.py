#!/usr/bin/env python3
"""South extension: the sports complex and the Walt Whitman Bridge (lat 39.890-39.915), plus DEM rows."""
import json, math, time, urllib.request, urllib.parse
S, N, W, E = 39.890, 39.9155, -75.190, -75.100
MIRRORS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
def fetch(q):
    data = urllib.parse.urlencode({'data': q}).encode(); last = None
    for attempt in range(6):
        try:
            req = urllib.request.Request(MIRRORS[attempt % 2], data=data, headers={'User-Agent': 'sht-3d-model/1.0'})
            with urllib.request.urlopen(req, timeout=180) as r: return json.load(r)
        except Exception as e: last = e; time.sleep(8 + 8 * attempt)
    raise last
elements, seen = [], set()
for j in range(3):
    w = W + (E - W) * j / 3; e = W + (E - W) * (j + 1) / 3
    bbox = f'{S:.5f},{w:.5f},{N:.5f},{e:.5f}'
    q = f'''[out:json][timeout:170];
(
  way["building"]({bbox}); relation["building"]({bbox});
  way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|secondary|tertiary|residential|unclassified|service)$"]({bbox});
  way["leisure"~"^(park|stadium|pitch|garden)$"]({bbox}); relation["leisure"="stadium"]({bbox});
  way["man_made"="pier"]({bbox}); way["natural"="water"]({bbox});
  way["bridge"="yes"]["highway"~"motorway|trunk"]({bbox});
);
(._;>;);
out body qt;'''
    d = fetch(q); new = 0
    for el in d.get('elements', []):
        k = (el['type'], el['id'])
        if k in seen: continue
        seen.add(k); elements.append(el); new += 1
    print(f'tile {j}: +{new} (total {len(elements)})', flush=True); time.sleep(6)
json.dump({'elements': elements}, open('osm_south_raw.json', 'w'))
print('osm_south_raw.json written', flush=True)
lat0, lon0 = 39.945473644755005, -75.14474803850973
kx = 111320 * math.cos(math.radians(lat0)); kz = 110574
xs = list(range(-4000, 2801, 50)); zs = list(range(3550, 6401, 50))
pts = [(x, z) for z in zs for x in xs]; elev = {}
for i in range(0, len(pts), 100):
    chunk = pts[i:i + 100]
    locs = '|'.join(f'{lat0 - z / kz:.6f},{lon0 + x / kx:.6f}' for x, z in chunk)
    for attempt in range(5):
        try:
            with urllib.request.urlopen('https://api.opentopodata.org/v1/ned10m?locations=' + locs, timeout=40) as r: d = json.load(r)
            for (x, z), res in zip(chunk, d['results']): elev[(x, z)] = res['elevation']
            break
        except Exception: time.sleep(3 + attempt * 3)
    time.sleep(1.05)
json.dump({'x0': xs[0], 'z0': zs[0], 'cell': 50, 'nx': len(xs), 'nz': len(zs), 'rows': [[elev.get((x, z)) for x in xs] for z in zs]}, open('dem_south.json', 'w'))
print('dem_south.json written', flush=True)
