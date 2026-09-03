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
  water  the union of the fragments buffered HALF_W each side, clipped to the reach the
         tiers leave dry (Z_MIN..Z_MAX, the dam to East Falls), as {"ring", "holes"} in the
         model frame, drawn flat at the river level by "Raising the rest of Philadelphia"

Data (c) OpenStreetMap contributors, ODbL (see ../DATA-LICENSE.md). Needs shapely."""
import json, os, sys, time
from shapely.geometry import LineString, Polygon, MultiPolygon, box
from shapely.ops import unary_union
from philly_frame import to_xz
try:
    import provenance
except Exception:
    provenance = None
import overpass

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
CACHE = os.path.join('lidar_cache', 'schuylkill_ways.json')
QUERY = '[out:json][timeout:90];way["waterway"="river"]["name"~"Schuylkill",i](39.85,-75.30,40.09,-75.12);out geom;'
HALF_W = 65.0            # metres each side of the centreline: the park reach is 110-170 m across
Z_MIN, Z_MAX = -6600.0, -2250.0   # East Falls (the NW patch's own river takes over) to the Fairmount dam
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
    # the water sheet: buffered fragments, one union, the reach the tiers leave dry
    buf = unary_union([LineString(l).buffer(HALF_W, cap_style=2, join_style=2) for l in lines if len(l) >= 2])
    clip = box(-9000, Z_MIN, 0, Z_MAX)
    water = buf.intersection(clip)
    if isinstance(water, MultiPolygon):
        water = max(water.geoms, key=lambda g: g.area)
    water = water.simplify(2.0)
    ring = [[round(x, 1), round(z, 1)] for x, z in water.exterior.coords][:-1]
    holes = [[[round(x, 1), round(z, 1)] for x, z in h.coords][:-1] for h in water.interiors if Polygon(h).area > 400]
    out = {'src': 'OpenStreetMap waterway=river ways named Schuylkill via Overpass (ODbL), model frame (philly_frame.py)',
           'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'half_w': HALF_W, 'z_range': [Z_MIN, Z_MAX],
           'lines': lines, 'water': {'ring': ring, 'holes': holes}}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    zs = [p[1] for l in lines for p in l]
    print(f'{OUT}: {len(lines)} fragments ({sum(len(l) for l in lines)} pts, z {min(zs):.0f}..{max(zs):.0f}), '
          f'water ring {len(ring)} pts + {len(holes)} island holes over {water.area / 1e4:.1f} ha, {os.path.getsize(OUT):,} bytes', flush=True)


if __name__ == '__main__':
    main()
