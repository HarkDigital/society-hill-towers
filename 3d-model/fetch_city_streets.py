#!/usr/bin/env python3
"""Tiled Overpass fetch for the street classes the far ring was missing, into
city_streets_raw.json (Round 87).

fetch_city.py's query keeps only motorway..residential, so the far ring never
had `unclassified`, `living_street` or `pedestrian` - and in Fairmount Park those
ARE the connecting drives (Lemon Hill Drive, Waterworks Drive, Aquarium Drive,
Sedgley Drive are all `unclassified`). Measured over the park's own rings, the
far ring's class list carries 68 per cent of the road length against the wide
tier's 90, and a quarter of its run endpoints dangle in the grass a median 27 m
from the nearest other road. That is why the park reads as disconnected arcs.

This is a supplement rather than a wider fetch_city.py query on purpose: the 92
tiles in city_tiles/ are keyed by tile name, not by query, so widening that query
means refetching 510 MB of buildings, parks and water to get a few megabytes of
streets. The classes here are exactly the ones fetch_wide.py adds and
pack_wide.py draws, so the two tiers end up with the same class set.

Boxes are fetch_city.py's, kept in step by hand (it runs its fetch at import, so
it cannot be imported). Per-tile checkpoints in city_streets_tiles/ via
overpass.py. Plain python3; pack_city.py merges the result.
"""
import json
from overpass import fetch_tiles, grid_tiles

# lat S, lat N, lon W, lon E, rows, cols — fetch_city.py BOXES
BOXES = [
    ('west-sw-airport', 39.860, 39.990, -75.285, -75.185, 5, 4),
    ('north',           39.986, 40.050, -75.190, -75.060, 3, 5),
    ('northeast',       40.050, 40.140, -75.130, -74.955, 4, 6),
    ('northwest',       39.990, 40.100, -75.285, -75.190, 4, 3),
    ('river-wards',     39.915, 40.050, -75.118, -74.990, 4, 3),
    ('nw-gap',          40.050, 40.100, -75.190, -75.130, 3, 3),
]

CLASSES = 'unclassified|living_street|pedestrian'


def tileQuery(bbox):
    # `out geom` rather than an "out body" with the node recursion: the recursion took
    # minutes a tile on a loaded mirror for a few hundred ways, and the geometry is all this
    # needs. Ways come back carrying a `geometry` array, which pack_city.py converts
    # (bake_rail.py reads the same shape).
    return f'''[out:json][timeout:180];
(
  way["highway"~"^({CLASSES})$"]({bbox});
);
out geom;'''


def main():
    tiles = []
    for name, S, N, W, E, ROWS, COLS in BOXES:
        tiles += grid_tiles(name, S, N, W, E, ROWS, COLS)
    elements = fetch_tiles(tiles, tileQuery, 'city_streets_tiles', rounds=3, pause=5)
    json.dump({'elements': elements}, open('city_streets_raw.json', 'w'))
    ways = sum(1 for e in elements if e.get('type') == 'way')
    print(f'city_streets_raw.json written ({len(elements)} elements, {ways} ways)', flush=True)


if __name__ == '__main__':
    main()
