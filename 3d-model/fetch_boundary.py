#!/usr/bin/env python3
"""Philadelphia's city line from OpenStreetMap (relation 188022, admin_level 8) in the
model frame -> city_limit.json:
  city:   the boundary ring, simplified to 40 m (the state line runs mid-Delaware)
  bound:  the flight limit: the city line buffered BUFFER_M, simplified 120 m and
          clipped to the far-ring box less 300 m. The camera clamps to it (fly,
          orbit pan, shared links) and SEPTA vehicles beyond it are off the map.
The raw relation is cached in lidar_cache/phila_boundary_raw.json (delete to refetch).
Needs shapely; Overpass through overpass.py's mirror rotation."""
import json, os, sys
from shapely.geometry import LineString, box as sbox
from shapely.ops import linemerge, unary_union, polygonize
from philly_frame import LON0, LAT0, KX, KZ
from overpass import fetch

BUFFER_M = 2000
RECT = (-12000, 16500, -21700, 9700)   # pack_city.py CITY
CACHE = 'lidar_cache/phila_boundary_raw.json'

if os.path.exists(CACHE):
    raw = json.load(open(CACHE))
else:
    raw = fetch('[out:json][timeout:120];relation(188022);out geom;')
    os.makedirs('lidar_cache', exist_ok=True)
    json.dump(raw, open(CACHE, 'w'))
rel = raw['elements'][0]
if rel.get('tags', {}).get('name') != 'Philadelphia':
    sys.exit('ERROR: relation 188022 is not Philadelphia any more: ' + str(rel.get('tags')))
lines = [LineString([((g['lon'] - LON0) * KX, (LAT0 - g['lat']) * KZ) for g in m['geometry']])
         for m in rel['members'] if m.get('type') == 'way' and m.get('role') == 'outer' and m.get('geometry')]
polys = sorted(polygonize(linemerge(unary_union(lines))), key=lambda p: p.area, reverse=True)
if not polys or not 300e6 < polys[0].area < 420e6:
    sys.exit('ERROR: the assembled boundary is not Philadelphia-sized: %s' % [round(p.area / 1e6, 1) for p in polys])
city = polys[0]
rect = sbox(RECT[0] + 300, RECT[2] + 300, RECT[1] - 300, RECT[3] - 300)
bound = city.buffer(BUFFER_M, join_style=1).simplify(120).intersection(rect)
if bound.geom_type == 'MultiPolygon':
    bound = max(bound.geoms, key=lambda g: g.area)
out = {
    'src': 'OpenStreetMap relation 188022 (ODbL), model frame (philly_frame.py)',
    'buffer_m': BUFFER_M,
    'city': [[round(x, 1), round(z, 1)] for x, z in list(city.simplify(40).exterior.coords)[:-1]],
    'bound': [[round(x), round(z)] for x, z in list(bound.exterior.coords)[:-1]],
}
json.dump(out, open('city_limit.json', 'w'), separators=(',', ':'))
print('city_limit.json: city %.1f km2, %d ring points; bound %.1f km2, %d points, buffer %d m'
      % (city.area / 1e6, len(out['city']), bound.area / 1e6, len(out['bound']), BUFFER_M), flush=True)
