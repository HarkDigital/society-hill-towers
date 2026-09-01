#!/usr/bin/env python3
"""Tiled Overpass fetch for the REST of Philadelphia beyond the wide box:
University City / West / Southwest + airport (A), North Philly (B),
the Northeast (C), Roxborough / Germantown / Chestnut Hill (D).
Writes osm_city_raw.json and a coarse 150 m dem_city.json.
The wide box (39.915..39.986, -75.188..-75.118) is fetched already; tiles
inside it are skipped at pack time (dedup by element id here).
Per-tile checkpoints in city_tiles/ via overpass.py (the logic lived here and
was lifted out so fetch_wide/fetch_south checkpoint the same way): reruns only
touch missing tiles, and a tile still missing after the retry rounds now aborts
the run (it used to print a WARNING and write the partial extract anyway)."""
import json, math, time, urllib.request, urllib.parse
import os
from overpass import fetch_tiles, grid_tiles
from philly_frame import LAT0 as lat0, LON0 as lon0, KX as kx, KZ as kz

# lat S, lat N, lon W, lon E, rows, cols
BOXES = [
    ('west-sw-airport', 39.860, 39.990, -75.285, -75.185, 5, 4),
    ('north',           39.986, 40.050, -75.190, -75.060, 3, 5),
    ('northeast',       40.050, 40.140, -75.130, -74.955, 4, 6),
    ('northwest',       39.990, 40.100, -75.285, -75.190, 4, 3),
    # the river wards east of the wide box: Fishtown's east end, Port Richmond,
    # Bridesburg, Tacony. The original four boxes left this rectangle uncovered
    # (wide stops at -75.118, 'north' starts at 39.986) — the Round 36 bare patch.
    ('river-wards',     39.915, 40.050, -75.118, -74.990, 4, 3),
    # East Mount Airy, West Oak Lane, Cedarbrook: above 40.050 the 'northeast'
    # box only starts at -75.130 and 'northwest' only reaches -75.190 — this
    # wedge between them was never fetched (the Round 40 bare patch).
    ('nw-gap',          40.050, 40.100, -75.190, -75.130, 3, 3),
]

tiles = []
for name, S, N, W, E, ROWS, COLS in BOXES:
    tiles += grid_tiles(name, S, N, W, E, ROWS, COLS)

def tileQuery(bbox):
    return f'''[out:json][timeout:180];
(
  way["building"]({bbox});
  way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|secondary|tertiary|residential)$"]({bbox});
  way["leisure"~"^(park|golf_course|nature_reserve)$"]({bbox});
  relation["leisure"="park"]({bbox});
  relation["leisure"="nature_reserve"]({bbox});
  way["natural"="water"]({bbox});
  relation["natural"="water"]({bbox});
  way["landuse"~"^(grass|cemetery|forest|recreation_ground)$"]({bbox});
  way["aeroway"~"^(runway|taxiway|apron)$"]({bbox});
);
(._;>;);
out body qt;'''

elements = fetch_tiles(tiles, tileQuery, 'city_tiles', rounds=3, pause=5)
json.dump({'elements': elements}, open('osm_city_raw.json', 'w'))
print(f'osm_city_raw.json written ({len(elements)} elements)', flush=True)

# coarse 150 m DEM over the whole city bbox (single grid; wide/core grids win where present)
# — checkpointed like the tiles: skip when already fetched
if os.path.exists('dem_city.json'):
    print('dem_city.json exists — skipping the DEM refetch', flush=True)
    raise SystemExit
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
