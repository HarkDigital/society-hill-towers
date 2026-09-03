#!/usr/bin/env python3
"""The Schuylkill's real course -> schuylkill.json, for the river carve and the water sheet
through Fairmount Park.

OSM maps the river as waterway=river ways (145 fragments across the city, side channels
around the islands included) and its surface as riverbank multipolygons that neither
packed tier carries north of the Fairmount dam, so the model's channel through the park
followed a hand-drawn polyline that wandered up to 500 m off the water. This bake asks
Overpass for the named waterway ways over the city (cached in lidar_cache/), projects them
into the model frame (philly_frame.py) and writes:

  lines  every fragment as [[x, z], ...] simplified to 3 m: the app's schuylkillCut() carves
         the terrain within 60..95 m of the nearest one
  polys  the river's outline: the natural=water river multipolygons OSM keeps around those
         ways (a second cached Overpass query), polygonised, the faces the waterway threads
         kept, united with the fragments buffered HALF_W (so a gap in the outline still
         carries water), clipped to the modelled reach (Z_MIN..Z_MAX), as [{"ring", "holes"}]
         in the model frame. The app carves the terrain to the outline (inside to the bed, a
         40 m ramp outside) and draws it flat at the river level, so the shoreline is the
         outline itself and not the 25 m ground grid surfacing through the sheet

Data (c) OpenStreetMap contributors, ODbL (see ../DATA-LICENSE.md). Needs shapely."""
import json, os, sys, time
from shapely.geometry import LineString, Polygon, MultiPolygon, box
from shapely.ops import unary_union, polygonize
from philly_frame import to_xz
try:
    import provenance
except Exception:
    provenance = None
import overpass

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
CACHE = os.path.join('lidar_cache', 'schuylkill_ways.json')
CACHE_OUTLINE = os.path.join('lidar_cache', 'schuylkill_outline_raw.json')
QUERY = '[out:json][timeout:90];way["waterway"="river"]["name"~"Schuylkill",i](39.85,-75.30,40.09,-75.12);out geom;'
HALF_W = 60.0            # metres each side of the centreline where the outline has a gap
Z_MIN, Z_MAX = -13000.0, 7500.0   # the modelled reach of the river
QUERY_OUTLINE = ('[out:json][timeout:180];way["waterway"="river"]["name"~"Schuylkill",i](39.85,-75.30,40.09,-75.12)->.w;'
                 '(rel(around.w:60)["natural"="water"];way(around.w:60)["natural"="water"];way(around.w:60)["waterway"="riverbank"];);out geom;')
OUT = 'schuylkill.json'


def main():
    if os.path.exists(CACHE) and '--force' not in sys.argv:
        data = json.load(open(CACHE))
    else:
        data = overpass.fetch(QUERY)
        os.makedirs('lidar_cache', exist_ok=True)
        json.dump(data, open(CACHE, 'w'))
        if provenance:
            provenance.record('bake_schuylkill.overpass', 'overpass waterway=river Schuylkill', {'query': QUERY}, len(data.get('elements', [])))
    ways = [w for w in data.get('elements', []) if w.get('type') == 'way' and w.get('geometry')]
    lines = []
    for w in ways:
        pts = [to_xz(g['lat'], g['lon']) for g in w['geometry']]
        if len(pts) < 2:
            continue
        ls = LineString(pts).simplify(3.0)
        lines.append([[round(x, 1), round(z, 1)] for x, z in ls.coords])
    # the outline: OSM's natural=water river multipolygons around the waterway, polygonised
    if os.path.exists(CACHE_OUTLINE) and '--force' not in sys.argv:
        raw = json.load(open(CACHE_OUTLINE))
    else:
        raw = overpass.fetch(QUERY_OUTLINE)
        json.dump(raw, open(CACHE_OUTLINE, 'w'))
        if provenance:
            provenance.record('bake_schuylkill.overpass', 'overpass natural=water around the Schuylkill', {'query': QUERY_OUTLINE}, len(raw.get('elements', [])))
    edges = []
    for e in raw.get('elements', []):
        if e.get('type') == 'way' and e.get('geometry') and (e.get('tags') or {}).get('water') not in ('rapids', 'fish_pass', 'stream'):
            edges.append(LineString([to_xz(g['lat'], g['lon']) for g in e['geometry']]))
        elif e.get('type') == 'relation' and (e.get('tags') or {}).get('water') in ('river', 'canal', None):
            for m in e.get('members', []):
                if m.get('type') == 'way' and m.get('geometry') and m.get('role') in ('outer', 'inner', ''):
                    edges.append(LineString([to_xz(g['lat'], g['lon']) for g in m['geometry']]))
    thread = unary_union([LineString(l) for l in lines if len(l) >= 2]).buffer(25.0)
    faces = [f for f in polygonize(unary_union(edges)) if f.area > 2000 and f.intersects(thread)]
    ribbon = unary_union([LineString(l).buffer(HALF_W, cap_style=2, join_style=2) for l in lines if len(l) >= 2])
    water = unary_union(faces + [ribbon]).intersection(box(-16000, Z_MIN, 4000, Z_MAX)).simplify(1.5)
    geoms = list(water.geoms) if isinstance(water, MultiPolygon) else [water]
    polys = []
    for g in sorted(geoms, key=lambda g: -g.area):
        if g.area < 5000:
            continue
        ring = [[round(x, 1), round(z, 1)] for x, z in g.exterior.coords][:-1]
        holes = [[[round(x, 1), round(z, 1)] for x, z in h.coords][:-1] for h in g.interiors if Polygon(h).area > 300]
        polys.append({'ring': ring, 'holes': holes})
    out = {'src': 'OpenStreetMap waterway=river ways named Schuylkill and the natural=water polygons around them, via Overpass (ODbL), model frame (philly_frame.py)',
           'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'half_w': HALF_W, 'z_range': [Z_MIN, Z_MAX],
           'lines': lines, 'polys': polys}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    zs = [p[1] for l in lines for p in l]
    print(f'{OUT}: {len(lines)} fragments ({sum(len(l) for l in lines)} pts, z {min(zs):.0f}..{max(zs):.0f}), '
          f'{len(faces)} outline faces, {len(polys)} water polygons ({sum(len(p["ring"]) for p in polys)} ring pts, '
          f'{sum(len(p["holes"]) for p in polys)} island holes) over {water.area / 1e4:.1f} ha, {os.path.getsize(OUT):,} bytes', flush=True)


if __name__ == '__main__':
    main()
