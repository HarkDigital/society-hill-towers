#!/usr/bin/env python3
"""Surface parking around the sports complex -> parking_south.json, drawn as asphalt flats
by the outer-districts builder. The lots between Broad Street, Pattison Avenue, Hartranft
Street and the port (NRG's lots, Citizens Bank Park's, the Linc's, Lot P, Lot M East) are
what that neighbourhood mostly is, and the wide fetch never pulled amenity=parking, so
the model painted them as lawn. Ways only, surface lots only (multi-storey garages are
buildings); ring coordinates in the model frame, simplified to 1.5 m.
Cached raw answer in lidar_cache/parking_south_raw.json (delete to refetch)."""
import json, os
from overpass import fetch
from philly_frame import LON0, LAT0, KX, KZ

S, N, W, E = 39.893, 39.915, -75.185, -75.140
CACHE = 'lidar_cache/parking_south_raw.json'
if os.path.exists(CACHE):
    raw = json.load(open(CACHE))
else:
    raw = fetch(f'[out:json][timeout:120];(way["amenity"="parking"]({S},{W},{N},{E}););(._;>;);out body qt;')
    os.makedirs('lidar_cache', exist_ok=True)
    json.dump(raw, open(CACHE, 'w'))
nodes = {el['id']: ((el['lon'] - LON0) * KX, (LAT0 - el['lat']) * KZ) for el in raw['elements'] if el.get('type') == 'node'}
polys = []
try:
    from shapely.geometry import Polygon
except ImportError:
    Polygon = None
for el in raw['elements']:
    t = el.get('tags') or {}
    if el.get('type') != 'way' or t.get('amenity') != 'parking': continue
    if t.get('parking') in ('multi-storey', 'underground', 'rooftop'): continue
    pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts) >= 2 and pts[0] == pts[-1]: pts = pts[:-1]
    if len(pts) < 3: continue
    if Polygon is not None:
        pg = Polygon(pts)
        if not pg.is_valid: pg = pg.buffer(0)
        if pg.is_empty or pg.area < 400: continue
        if pg.geom_type == 'MultiPolygon': pg = max(pg.geoms, key=lambda g: g.area)
        pts = list(pg.simplify(1.5).exterior.coords)[:-1]
    flat = []
    for x, z in pts: flat.extend([round(x, 1), round(z, 1)])
    polys.append(flat)
# the fill: the complex is asphalt end to end, so the lots west of 7th Street are closed
# over the streets and plazas between them (buffer 90 m, erode 60 m) into a district sheet
# the builder lays under everything; the stadiums' own footprints cover their holes
fill = []
if Polygon is not None:
    from shapely.ops import unary_union
    lots = [Polygon([(fl[i], fl[i + 1]) for i in range(0, len(fl), 2)]) for fl in polys]
    lots = [l for l in lots if l.centroid.x < -700]
    u = unary_union([l.buffer(90, join_style=2) for l in lots]).buffer(-60, join_style=2)
    for g in (u.geoms if u.geom_type == 'MultiPolygon' else [u]):
        if g.area < 10000: continue
        ring = list(g.simplify(3).exterior.coords)[:-1]
        flat = []
        for x, z in ring: flat.extend([round(x, 1), round(z, 1)])
        fill.append(flat)
json.dump({'src': 'OpenStreetMap amenity=parking (ODbL), model frame', 'polys': polys, 'fill': fill}, open('parking_south.json', 'w'), separators=(',', ':'))
print(f'fill: {len(fill)} sheets, {sum(len(f) // 2 for f in fill)} points', flush=True)
print(f'parking_south.json: {len(polys)} lots, {os.path.getsize("parking_south.json"):,} bytes', flush=True)
