#!/usr/bin/env python3
"""Land-use polygons over the whole far-ring box -> osm_landuse_raw.json, for the filler
across the city line. OpenStreetMap maps residential, commercial, industrial and retail
land use across the suburbs even where it maps few of the buildings, so
pack_outskirts.py raises synthetic strips of houses and sheds along the streets inside
those polygons wherever real footprints are thin. Ways only (landuse multipolygon
relations are rare at this scale); 4 x 4 tiles checkpointed in landuse_tiles/."""
import json
from overpass import fetch_tiles, grid_tiles

# the far-ring box (pack_city.py CITY) in lat/lon
tiles = grid_tiles('landuse', 39.858, 40.141, -75.285, -74.951, 4, 4)

def tileQuery(bbox):
    return f'''[out:json][timeout:180];
(
  way["landuse"~"^(residential|commercial|industrial|retail)$"]({bbox});
);
(._;>;);
out body qt;'''

elements = fetch_tiles(tiles, tileQuery, 'landuse_tiles', rounds=3, pause=3)
json.dump({'elements': elements}, open('osm_landuse_raw.json', 'w'))
print(f'osm_landuse_raw.json written ({len(elements)} elements)', flush=True)
