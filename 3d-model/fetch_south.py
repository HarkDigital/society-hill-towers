#!/usr/bin/env python3
"""South extension: the sports complex and the Walt Whitman Bridge (lat 39.890-39.915), plus DEM rows.
Tiles checkpoint in south_tiles/ (overpass.py): a rerun refetches only the tiles that
failed, and a tile still missing after the retry rounds aborts the run instead of
writing a partial extract."""
import json, math, time, urllib.request, urllib.parse
from overpass import fetch_tiles, grid_tiles
from philly_frame import LAT0 as lat0, LON0 as lon0, KX as kx, KZ as kz
S, N, W, E = 39.890, 39.9155, -75.190, -75.100

def tileQuery(bbox):
    return f'''[out:json][timeout:170];
(
  way["building"]({bbox}); relation["building"]({bbox});
  way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|secondary|tertiary|residential|unclassified|service)$"]({bbox});
  way["leisure"~"^(park|stadium|pitch|garden)$"]({bbox}); relation["leisure"="stadium"]({bbox});
  way["man_made"="pier"]({bbox}); way["natural"="water"]({bbox});
  way["bridge"="yes"]["highway"~"motorway|trunk"]({bbox});
);
(._;>;);
out body qt;'''

elements = fetch_tiles(grid_tiles('south', S, N, W, E, 1, 3), tileQuery, 'south_tiles', pause=6)
json.dump({'elements': elements}, open('osm_south_raw.json', 'w'))
print(f'osm_south_raw.json written ({len(elements)} elements)', flush=True)
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
if provenance: provenance.record('fetch_south.dem', 'https://api.opentopodata.org/v1/ned10m', f'ned10m 50 m grid x {xs[0]}..{xs[-1]} z {zs[0]}..{zs[-1]}', len(elev))
json.dump({'x0': xs[0], 'z0': zs[0], 'cell': 50, 'nx': len(xs), 'nz': len(zs), 'rows': [[elev.get((x, z)) for x in xs] for z in zs]}, open('dem_south.json', 'w'))
print('dem_south.json written', flush=True)
