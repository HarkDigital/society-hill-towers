#!/usr/bin/env python3
"""Tiled Overpass fetch for the towns across the city line: the three strips of the
far-ring box that fetch_city.py / fetch_wide.py / fetch_south.py never covered.
  south: lat 39.858-39.915 east of -75.185: the Navy Yard's south half and, across the
         river, Gloucester City, Camden's Fairview and Morgan Village, Brooklawn,
         Westville, Bellmawr, Mount Ephraim, Audubon, Oaklyn, Haddon Township
  east:  lat 39.915-40.050 east of -74.990: Pennsauken's east half, Merchantville,
         Cherry Hill's west edge
  north: lat 40.100-40.141 west of -75.130: Whitemarsh, Springfield, Wyndmoor,
         Cheltenham's north, Abington
Writes osm_outskirts_raw.json; pack_outskirts.py packs it into outskirts.b64 and skips
anything whose centroid the older fetch boxes already own. No DEM: dem_city.json's
150 m grid covers the whole far-ring box. Water and park RELATIONS are not pulled
(the Delaware's multipolygon alone would drag in the whole river); ways only.
Per-tile checkpoints in outskirts_tiles/ via overpass.py."""
import json
from overpass import fetch_tiles, grid_tiles

# lat S, lat N, lon W, lon E, rows, cols
BOXES = [
    ('south', 39.858, 39.915, -75.185, -74.951, 3, 7),
    ('east',  39.915, 40.050, -74.990, -74.951, 4, 1),
    ('north', 40.100, 40.141, -75.285, -75.130, 1, 5),
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
  way["natural"="water"]({bbox});
  way["landuse"~"^(grass|cemetery|forest|recreation_ground)$"]({bbox});
);
(._;>;);
out body qt;'''

elements = fetch_tiles(tiles, tileQuery, 'outskirts_tiles', rounds=3, pause=5)
json.dump({'elements': elements}, open('osm_outskirts_raw.json', 'w'))
print(f'osm_outskirts_raw.json written ({len(elements)} elements)', flush=True)
