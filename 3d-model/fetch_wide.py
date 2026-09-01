#!/usr/bin/env python3
"""Tiled Overpass fetch for the wide area (Center City, South Philly, NoLibs, Fishtown/Kensington)
plus a 50 m elevation grid. Writes osm_wide_raw.json and dem_wide.json.
Tiles checkpoint in wide_tiles/ (overpass.py): a rerun refetches only the tiles that
failed, and a tile still missing after the retry rounds aborts the run instead of
writing a partial extract."""
import json, math, time, urllib.request, urllib.parse, sys
from overpass import fetch_tiles, grid_tiles
from philly_frame import LAT0 as lat0, LON0 as lon0, KX as kx, KZ as kz
S, N, W, E = 39.915, 39.986, -75.188, -75.118
ROWS, COLS = 4, 4

def tileQuery(bbox):
    return f'''[out:json][timeout:170];
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

elements = fetch_tiles(grid_tiles('wide', S, N, W, E, ROWS, COLS), tileQuery, 'wide_tiles', pause=6)
json.dump({'elements': elements}, open('osm_wide_raw.json', 'w'))
print(f'osm_wide_raw.json written ({len(elements)} elements)', flush=True)

# elevation grid, 50 m, via OpenTopoData ned10m
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
