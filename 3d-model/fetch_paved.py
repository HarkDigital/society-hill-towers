#!/usr/bin/env python3
"""The paved ground over the whole far-ring box -> osm_paved_raw.json, for pack_paved.py.
Since Round 52 every unbuilt surface is the meadow, and the port terminals, the rail
yards, the big-box lots and every surface parking lot in the city were green. No extract
held them (the wide extract's amenity=parking ways are almost all garages, parking_south.json
covers only the sports complex), so this fetch asks for them citywide: surface parking
(amenity=parking minus the multi-storey / underground / rooftop kinds, which are buildings),
the paved land uses that fetch_landuse.py leaves out (railway, port, depot, garages,
brownfield, construction, quarry, landfill), airport aprons and man_made=works. Ways only,
like the landuse fetch; 4 x 4 tiles checkpointed in paved_tiles/ so a broken run resumes.
Run with OVERPASS_MIRRORS=https://overpass-api.de/api/interpreter (the other mirrors time
out on this box); provenance.jsonl is written by fetch_tiles."""
import json
from collections import Counter
from overpass import fetch_tiles, grid_tiles

# the far-ring box (pack_city.py CITY) in lat/lon, the same tiling as fetch_landuse.py
tiles = grid_tiles('paved', 39.858, 40.141, -75.285, -74.951, 4, 4)

def tileQuery(bbox):
    return f'''[out:json][timeout:180];
(
  way["amenity"="parking"]["parking"!~"^(multi-storey|underground|rooftop|carports|garage_boxes)$"]({bbox});
  way["landuse"~"^(railway|port|depot|garages|brownfield|construction|quarry|landfill)$"]({bbox});
  way["aeroway"="apron"]({bbox});
  way["man_made"="works"]({bbox});
);
(._;>;);
out body qt;'''

elements = fetch_tiles(tiles, tileQuery, 'paved_tiles', rounds=3, pause=3)
json.dump({'elements': elements}, open('osm_paved_raw.json', 'w'))
print(f'osm_paved_raw.json written ({len(elements)} elements)', flush=True)

# the count per tag, for the report (a way can carry more than one of these)
tags = Counter()
for el in elements:
    if el.get('type') != 'way':
        continue
    t = el.get('tags') or {}
    if t.get('amenity') == 'parking':
        tags['amenity=parking'] += 1
    if t.get('landuse'):
        tags['landuse=' + t['landuse']] += 1
    if t.get('aeroway') == 'apron':
        tags['aeroway=apron'] += 1
    if t.get('man_made') == 'works':
        tags['man_made=works'] += 1
for k, n in sorted(tags.items(), key=lambda kv: -kv[1]):
    print(f'  {k}: {n}')
