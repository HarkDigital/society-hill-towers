#!/usr/bin/env python3
"""The tidal Delaware's real outline -> delaware.json, for the river beyond the modelled
ground and the shoreline where the DEM does not reach.

OSM maps the Delaware's surface two ways: below the airport as natural=coastline (the
estuary's coast, one strand up both banks from Delaware Bay that ends near Tinicum) and
above it as unnamed natural=water + water=river multipolygons in reaches, so no packed tier
ever carried the river and the model showed it only where a DEM cell dipped below the water
plane: the far ring's ground box ends about 500 m south of the airport's shore and the river
past Fort Mifflin simply stopped (Round 55 coda). This bake asks Overpass for both (the
coastline ways and the river water outlines over the estuary from Marcus Hook to Bristol,
cached in lidar_cache/), projects every edge into the model frame (philly_frame.py),
polygonises the whole network against the query box and keeps the faces the river's own
centreline threads (OSM's waterway=river ways named Delaware River, a third cached query;
the river is a chain of faces where the reaches meet, and a land face would swallow the
box, so faces over MAX_FACE are never water), then writes:

  polys   the river's outline within RADIUS of the origin, as [{"ring", "holes"}] in the
          model frame, simplified to 4 m and whole metres: the app's delawareAt() decides river or land for
          the far ground's cells beyond the DEM grids
  beyond  the same outline minus the far ring's ground box: the app draws these flat at
          the river level over the apron, so the river runs on to the fog past the world
          the camera can reach (Wilmington's reach one way, Bristol's the other)

Data (c) OpenStreetMap contributors, ODbL (see ../DATA-LICENSE.md). Needs shapely."""
import json, os, sys, time
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, box
from shapely.ops import unary_union, polygonize
from philly_frame import to_xz
try:
    import provenance
except Exception:
    provenance = None
import overpass

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
CACHE = os.path.join('lidar_cache', 'delaware_coastline_raw.json')
CACHE_WATER = os.path.join('lidar_cache', 'delaware_water_raw.json')
CACHE_LINE = os.path.join('lidar_cache', 'delaware_ways.json')
BBOX = (39.70, -75.70, 40.25, -74.60)          # S, W, N, E: Marcus Hook to Bristol, both banks
QUERY = '[out:json][timeout:180];way["natural"="coastline"](%s,%s,%s,%s);out geom;' % BBOX
QUERY_WATER = ('[out:json][timeout:240];(rel["natural"="water"]["water"="river"](%s,%s,%s,%s);way["natural"="water"]["water"="river"](%s,%s,%s,%s);'
               'rel["waterway"="riverbank"](%s,%s,%s,%s);way["waterway"="riverbank"](%s,%s,%s,%s););out geom;') % (BBOX * 4)
QUERY_LINE = '[out:json][timeout:180];way["waterway"="river"]["name"~"Delaware River",i](%s,%s,%s,%s);out geom;' % BBOX
MAX_FACE = 400e6   # m2: the river's faces run 1 to 240 km2 inside the box; the two land faces are 2,500 each
RADIUS = 48000.0                                # the fog closes at 40 km; the sheets run a little past it
FAR_BOX = (-12000.0, -21700.0, 16500.0, 9700.0)  # the far ring's ground box (app.js RING_W, the terrain's extent; the flight bounds run 200 m past it)
# points out on the river, a check after the bake: every one must land on water
SEEDS = [(39.9453, -75.1380), (39.8850, -75.1650), (39.8560, -75.2450), (39.8480, -75.3000), (39.8380, -75.3500),
         (39.8150, -75.4000), (39.7950, -75.4400), (39.9700, -75.0950), (40.0950, -74.8500), (40.1300, -74.7800)]
OUT = 'delaware.json'


def rings_of(g):
    ring = [[int(round(x)), int(round(z))] for x, z in g.exterior.coords][:-1]   # whole metres: a shoreline the far ground samples at 100 m
    holes = [[[int(round(x)), int(round(z))] for x, z in h.coords][:-1] for h in g.interiors if Polygon(h).area > 300]
    return {'ring': ring, 'holes': holes}


def as_polys(geom, min_area):
    geoms = list(geom.geoms) if isinstance(geom, MultiPolygon) else ([geom] if not geom.is_empty else [])
    return [rings_of(g) for g in sorted(geoms, key=lambda g: -g.area) if g.area >= min_area and len(g.exterior.coords) >= 4]


def main():
    if os.path.exists(CACHE) and '--force' not in sys.argv:
        data = json.load(open(CACHE))
    else:
        data = overpass.fetch(QUERY)
        os.makedirs('lidar_cache', exist_ok=True)
        json.dump(data, open(CACHE, 'w'))
        if provenance:
            provenance.record('bake_delaware.overpass', 'overpass natural=coastline over the tidal Delaware', {'query': QUERY}, len(data.get('elements', [])))
    if os.path.exists(CACHE_WATER) and '--force' not in sys.argv:
        raw = json.load(open(CACHE_WATER))
    else:
        raw = overpass.fetch(QUERY_WATER)
        json.dump(raw, open(CACHE_WATER, 'w'))
        if provenance:
            provenance.record('bake_delaware.overpass', 'overpass natural=water river outlines over the tidal Delaware', {'query': QUERY_WATER}, len(raw.get('elements', [])))
    lines = []
    def add(geom):
        pts = [to_xz(g['lat'], g['lon']) for g in geom]
        if len(pts) >= 2:
            lines.append(LineString(pts))
    for w in data.get('elements', []):
        if w.get('type') == 'way' and w.get('geometry'):
            add(w['geometry'])
    n_coast = len(lines)
    for e in raw.get('elements', []):
        if e.get('type') == 'way' and e.get('geometry'):
            add(e['geometry'])
        elif e.get('type') == 'relation':
            for m in e.get('members', []):
                if m.get('type') == 'way' and m.get('geometry') and m.get('role') in ('outer', 'inner', ''):
                    add(m['geometry'])
    s, wl, n, e = BBOX
    (bx0, bz0), (bx1, bz1) = to_xz(n, wl), to_xz(s, e)     # the query box in the model frame (z grows south)
    frame = box(min(bx0, bx1), min(bz0, bz1), max(bx0, bx1), max(bz0, bz1))
    graph = unary_union(lines + [frame.exterior])
    faces = list(polygonize(graph))
    if os.path.exists(CACHE_LINE) and '--force' not in sys.argv:
        ways = json.load(open(CACHE_LINE))
    else:
        ways = overpass.fetch(QUERY_LINE)
        json.dump(ways, open(CACHE_LINE, 'w'))
        if provenance:
            provenance.record('bake_delaware.overpass', 'overpass waterway=river Delaware River', {'query': QUERY_LINE}, len(ways.get('elements', [])))
    thread = unary_union([LineString([to_xz(g['lat'], g['lon']) for g in w['geometry']]) for w in ways.get('elements', []) if w.get('type') == 'way' and len(w.get('geometry') or []) >= 2]).buffer(25.0)
    water_faces = [f for f in faces if f.area < MAX_FACE and f.intersects(thread)]
    if not water_faces:
        sys.exit('no face under the centreline: the query box or the centreline query is off')
    seeds = [Point(*to_xz(la, lo)) for la, lo in SEEDS]
    water = unary_union(water_faces).intersection(Point(0, 0).buffer(RADIUS, 64)).simplify(4.0)
    bx0, bz0, bx1, bz1 = FAR_BOX
    beyond = water.difference(box(bx0 + 5, bz0 + 5, bx1 - 5, bz1 - 5)).simplify(4.0)   # 5 m into the box: the sheets overlap at the seam, no hairline
    polys, beyond_polys = as_polys(water, 5000), as_polys(beyond, 5000)
    out = {'src': 'OpenStreetMap natural=coastline ways over the tidal Delaware via Overpass (ODbL), polygonised against the query box, the river faces kept by seed points, model frame (philly_frame.py)',
           'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'bbox': list(BBOX), 'radius': RADIUS, 'far_box': list(FAR_BOX),
           'polys': polys, 'beyond': beyond_polys}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print(f'{OUT}: {n_coast} coastline ways + {len(lines) - n_coast} water outline ways, {len(faces)} faces, {len(water_faces)} river faces under the centreline, '
          f'{len(polys)} river polygons ({sum(len(p["ring"]) for p in polys)} ring pts, {sum(len(p["holes"]) for p in polys)} holes) over {water.area / 1e6:.1f} km2, '
          f'{len(beyond_polys)} beyond the box ({beyond.area / 1e6:.1f} km2), {os.path.getsize(OUT):,} bytes', flush=True)
    seeds_missed = [SEEDS[i] for i, p in enumerate(seeds) if not water.intersects(p)]
    if seeds_missed:
        print('seeds not on water (a reach the coastline does not enclose?):', seeds_missed)


if __name__ == '__main__':
    main()
