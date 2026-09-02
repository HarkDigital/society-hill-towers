#!/usr/bin/env python3
"""osm_outskirts_raw.json -> outskirts.b64 : the towns across the city line at 1.0 m units.
outskirts.b64 is a derivative database of OpenStreetMap data (ODbL): see ../DATA-LICENSE.md.
Same body layout as city.b64's no-attribute form (magic 0x53485459: building n, h*5, minH*5,
type, n x (x, z); road n, w*10, class, pts; area n, kind, pts) at scale 1.0, decoded by the
far ring's raiseRing() in app.js. No LiDAR, OPA or roof join exists across the line, so
heights come from OSM tags and type defaults. Rows are merged into block strips like the far
ring but with a 3 m bridge instead of 1.8 m: detached suburban houses fuse into rows, which
from the city line read as streets of houses, and the record count matters more than the
gaps between them. Everything whose centroid an older fetch box owns (fetch_city's six boxes,
the wide box, the south box as far east as pack_wide packs it) is skipped: those tiers draw it.
Guards: an int16 saturation in clip() is fatal (outskirts.b64 is not written).
Frame: philly_frame.py. Needs shapely."""
import json, math, os, struct, base64, sys
from collections import Counter
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.ops import unary_union
from philly_frame import LON0, LAT0, KX, KZ

S = 1.0
MAGIC = 0x53485459
CITY = (-12000, 16500, -21700, 9700)      # pack_city.py CITY: the far-ring box, the terrain's extent
# fetch boxes other tiers already pack (lat S, lat N, lon W, lon E)
# fetch boxes other tiers actually PACK (lat S, lat N, lon W, lon E). fetch_south.py fetches to
# -75.100, but pack_wide.py packs buildings only inside WIDE (x <= 2300, lon -75.118), so the
# south box counts as owned only that far east: its Gloucester City strip beyond is ours
OWNED_LL = [
    (39.860, 39.990, -75.285, -75.185), (39.986, 40.050, -75.190, -75.060), (40.050, 40.140, -75.130, -74.955),
    (39.990, 40.100, -75.285, -75.190), (39.915, 40.050, -75.118, -74.990), (40.050, 40.100, -75.190, -75.130),   # fetch_city.py
    (39.915, 39.986, -75.188, -75.118),                                                                            # fetch_wide.py
    (39.890, 39.9155, -75.190, -75.118),                                                                           # fetch_south.py, as far as pack_wide packs it
]
def ll_box(s, n, w, e): return ((w - LON0) * KX, (e - LON0) * KX, (LAT0 - n) * KZ, (LAT0 - s) * KZ)
OWNED = [ll_box(*b) for b in OWNED_LL]
# pack_wide carries roads 200 m past WIDE (x <= 2500) and admits area rings within 500 m of it
ROAD_OWNED = OWNED[:-1] + [(OWNED[-1][0], 2500, OWNED[-1][2], OWNED[-1][3])]
AREA_OWNED = OWNED[:-1] + [(OWNED[-1][0], 2800, OWNED[-1][2], OWNED[-1][3])]
def inBox(x, z, B): return B[0] <= x <= B[1] and B[2] <= z <= B[3]
def owned(x, z, boxes=OWNED): return any(inBox(x, z, B) for B in boxes)
def ours(x, z, boxes=OWNED): return inBox(x, z, CITY) and not owned(x, z, boxes)

BT = {'generic': 0, 'house': 1, 'residential': 1, 'terrace': 1, 'apartments': 2, 'detached': 1, 'semidetached_house': 1,
      'commercial': 3, 'retail': 3, 'office': 3, 'hotel': 3, 'industrial': 4, 'warehouse': 4, 'garage': 4, 'parking': 4,
      'church': 5, 'cathedral': 5, 'chapel': 5, 'school': 6, 'civic': 6, 'hospital': 6, 'university': 6}
HDEF = {'house': 8.0, 'residential': 8.0, 'detached': 7.5, 'terrace': 8.5, 'semidetached_house': 8.0, 'apartments': 11,
        'garage': 3.5, 'garages': 3.5, 'shed': 3, 'commercial': 7.5, 'retail': 7.5, 'office': 10, 'industrial': 8,
        'warehouse': 9, 'church': 13, 'cathedral': 15, 'chapel': 9, 'school': 10, 'hospital': 14, 'university': 12}
RT = {'motorway': 0, 'motorway_link': 0, 'trunk': 1, 'trunk_link': 1, 'primary': 2, 'secondary': 3, 'tertiary': 4, 'residential': 5}
RW = {0: 16, 1: 14, 2: 12, 3: 10, 4: 9, 5: 7}

raw = json.load(open('osm_outskirts_raw.json'))
els = raw['elements']
nodes = {}
for el in els:
    if el.get('type') == 'node':
        nodes[el['id']] = ((el['lon'] - LON0) * KX, (LAT0 - el['lat']) * KZ)
ways = [el for el in els if el.get('type') == 'way']

SAT = []
_rec = None
def clip(v):
    r = int(round(v))
    if r > 32767 or r < -32767:
        SAT.append((_rec, v))
        return max(-32767, min(32767, r))
    return r

def ring_budget(pg, budget, tol):
    """Exterior ring with at most `budget` vertices: Douglas-Peucker with a doubling tolerance."""
    ext = list(pg.exterior.coords)[:-1]
    t = tol
    while len(ext) > budget and t < 4096:
        sp = list(pg.simplify(t).exterior.coords)[:-1]
        if len(sp) < len(ext): ext = sp
        t *= 2
    if len(ext) > budget:
        ext = ext[::-(-len(ext) // budget)]
    return ext

def parseH(t):
    h = t.get('height')
    if h:
        try: return max(3, float(str(h).replace('m', '').strip()))
        except ValueError: pass
    lv = t.get('building:levels')
    if lv:
        try: return max(3, float(lv) * 3.2 + 1.2)
        except ValueError: pass
    return HDEF.get(t.get('building'), 7.0)

# ---- buildings: block strips (rows and near-neighbours fused) + solo talls / churches
merge_groups = {}
solo = []
n_in = n_owned = 0
for el in ways:
    t = el.get('tags') or {}
    if 'building' not in t: continue
    pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts) >= 2 and pts[0] == pts[-1]: pts = pts[:-1]
    if len(pts) < 3: continue
    cx = sum(p[0] for p in pts) / len(pts); cz = sum(p[1] for p in pts) / len(pts)
    if not inBox(cx, cz, CITY): continue
    if owned(cx, cz): n_owned += 1; continue
    try: pg = Polygon(pts)
    except Exception: continue
    if not pg.is_valid: pg = pg.buffer(0)
    if pg.is_empty or pg.area < 30: continue
    h = parseH(t)
    if h < 5 and pg.area < 60: continue
    bt = BT.get(t.get('building'), 0)
    n_in += 1
    if h > 20 or bt == 5:
        solo.append((pg, h, bt))
    else:
        merge_groups.setdefault((int(cx // 400), int(cz // 400), int(round(h / 4))), []).append(pg)

body_b, body_r, body_a = [], [], []   # buildings, roads, areas: the blob is laid out in that order
nb = 0
packed_polys = []   # every emitted footprint, for the filler's collision tests
def emit(pg, h, mh, bt):
    global nb, _rec
    ext = ring_budget(pg, 16, 1.5)
    if len(ext) < 3: return
    _rec = ('building', bt, round(h, 1), tuple(round(c) for c in (pg.centroid.x, pg.centroid.y)))
    body_b.extend([len(ext), clip(min(6500, h) * 5), clip(mh * 5), bt])
    for x, z in ext: body_b.extend([clip(x / S), clip(z / S)])
    packed_polys.append(Polygon(ext))
    nb += 1

for (gx, gz, hb), pgs in merge_groups.items():
    h = max(4, hb * 4)
    merged = unary_union([p.buffer(3.0, join_style=2) for p in pgs]).buffer(-3.0, join_style=2)
    geoms = list(merged.geoms) if merged.geom_type == 'MultiPolygon' else [merged]
    for g in geoms:
        if g.is_empty or g.area < 70: continue
        emit(Polygon(g.exterior).simplify(2.0), h, 0, 1 if h <= 12 else 2)
for pg, h, bt in solo:
    emit(pg.simplify(1.0), h, 0, bt)
print(f'buildings: {n_in} in ({n_owned} owned by other tiers) -> {nb} packed', flush=True)

# ---- roads: runs split where a way leaves our ground (pack_city's _runs: a neighbour of a
# kept point stays so the ribbon reaches the seam, but no chord ever spans an excursion)
def _runs(pts, keepFn):
    runs, cur = [], []
    for i, q in enumerate(pts):
        keep = keepFn(q) or (i > 0 and keepFn(pts[i - 1])) or (i + 1 < len(pts) and keepFn(pts[i + 1]))
        if keep: cur.append(q)
        else:
            if len(cur) > 1: runs.append(cur)
            cur = []
    if len(cur) > 1: runs.append(cur)
    return runs

nr = 0
packed_roads = []   # (pts, width, class) for the filler's street marching
for el in ways:
    t = el.get('tags') or {}
    if t.get('highway') not in RT: continue
    rt = RT[t['highway']]; w = RW[rt]
    pts_raw = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts_raw) < 2: continue
    for run in _runs(pts_raw, lambda q: ours(q[0], q[1], ROAD_OWNED)):
        pts = list(LineString(run).simplify(2.5).coords) if len(run) > 2 else run
        if len(pts) < 2: continue
        _rec = ('road', el['id'], t.get('highway'), t.get('name'))
        packed_roads.append((pts, w, rt))
        for c0 in range(0, len(pts) - 1, 119):
            chunk = pts[c0:c0 + 120]
            if len(chunk) < 2: continue
            body_r.extend([len(chunk), clip(w * 10), rt])
            for x, z in chunk: body_r.extend([clip(x / S), clip(z / S)])
            nr += 1
print(f'roads: {nr}', flush=True)

# ---- areas: parks / green (0), water (1); clipped to the far-ring box
na = 0
packed_areas = []   # (polygon, kind) for the filler's exclusions
cityBox = sbox(CITY[0], CITY[2], CITY[1], CITY[3])
GREEN = ('park', 'golf_course', 'nature_reserve')
LU = ('grass', 'cemetery', 'forest', 'recreation_ground')
for el in ways:
    t = el.get('tags') or {}
    kind = None
    if t.get('leisure') in GREEN or t.get('landuse') in LU: kind = 0
    elif t.get('natural') == 'water': kind = 1
    if kind is None: continue
    pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts) >= 2 and pts[0] == pts[-1]: pts = pts[:-1]
    if len(pts) < 3: continue
    cx = sum(p[0] for p in pts) / len(pts); cz = sum(p[1] for p in pts) / len(pts)
    if not ours(cx, cz, AREA_OWNED): continue
    try: pg = Polygon(pts)
    except Exception: continue
    if not pg.is_valid: pg = pg.buffer(0)
    pg = pg.intersection(cityBox)
    geoms = list(pg.geoms) if pg.geom_type == 'MultiPolygon' else [pg] if pg.geom_type == 'Polygon' else []
    for g in geoms:
        if g.is_empty or g.area < 6000: continue
        ext = ring_budget(g, 60, 2.5)
        if len(ext) < 3: continue
        _rec = ('area', kind, (round(cx), round(cz)))
        body_a.extend([len(ext), kind])
        for x, z in ext: body_a.extend([clip(x / S), clip(z / S)])
        packed_areas.append((g, kind))
        na += 1
print(f'areas: {na}', flush=True)

# ---- the filler: streets of houses where OpenStreetMap maps the land use but few of the
# buildings (osm_landuse_raw.json, fetch_landuse.py). Along every street inside residential
# land use beyond the city line, 11 m deep strips of houses at a 14 m pitch, fused six at a
# time; along the main roads through commercial and industrial land use, boxes at 40 and 60 m.
# Only where real footprints are thin (under 10% of the ground within 150 m), never on a real
# footprint, a road, a park or water, and never inside the city line. From the flight limit,
# 2 km out, a strip of eight-metre houses reads as the street it stands in; nobody will
# look for their own house across the river
INFILL_H = {'res': (8.0, 1), 'com': (7.0, 3), 'ind': (8.0, 4)}
n_inf = 0
if os.path.exists('osm_landuse_raw.json') and os.path.exists('city_limit.json'):
    from shapely import contains_xy
    from shapely.strtree import STRtree
    sys.path.insert(0, 'tests')
    import _common as C
    limit = json.load(open('city_limit.json'))
    cityPoly = Polygon(limit['city'])
    outside = cityBox.difference(cityPoly.buffer(60))
    LU_KIND = {'residential': 'res', 'commercial': 'com', 'retail': 'com', 'industrial': 'ind'}
    lraw = json.load(open('osm_landuse_raw.json'))
    lnodes = {el['id']: ((el['lon'] - LON0) * KX, (LAT0 - el['lat']) * KZ) for el in lraw['elements'] if el.get('type') == 'node'}
    lus, luKinds = [], []
    for el in lraw['elements']:
        t = el.get('tags') or {}
        if el.get('type') != 'way' or t.get('landuse') not in LU_KIND: continue
        pts = [lnodes[n] for n in el.get('nodes', []) if n in lnodes]
        if len(pts) >= 2 and pts[0] == pts[-1]: pts = pts[:-1]
        if len(pts) < 3: continue
        try: pg = Polygon(pts)
        except Exception: continue
        if not pg.is_valid: pg = pg.buffer(0)
        pg = pg.intersection(outside)
        for g in (pg.geoms if pg.geom_type == 'MultiPolygon' else [pg] if pg.geom_type == 'Polygon' else []):
            if g.area >= 4000: lus.append(g); luKinds.append(LU_KIND[t['landuse']])
    luTree = STRtree(lus)
    # what already stands beyond the line: this tier plus the far ring's and the wide tier's slivers
    existing = list(packed_polys)
    for name in ('city.b64', 'wide.b64'):
        if not os.path.exists(name): continue
        for rec in C.walk_scene(name)['buildings']:
            pts = rec[-1]
            if len(pts) < 3: continue
            cx = sum(p[0] for p in pts) / len(pts); cz = sum(p[1] for p in pts) / len(pts)
            if not contains_xy(cityPoly, cx, cz):
                try: existing.append(Polygon(pts))
                except Exception: pass
    exTree = STRtree(existing)
    cov = {}
    for pg in existing:
        c = pg.centroid; key = (int(c.x // 100), int(c.y // 100)); cov[key] = cov.get(key, 0.0) + pg.area
    def covered(x, z):
        gx, gz = int(x // 100), int(z // 100)
        return sum(cov.get((gx + i, gz + j), 0.0) for i in (-1, 0, 1) for j in (-1, 0, 1)) / 90000.0
    # streets to march along: this tier's plus the far ring's beyond the line
    segs = []
    for pts, w, rt in packed_roads:
        for i in range(len(pts) - 1): segs.append((pts[i], pts[i + 1], w, rt))
    if os.path.exists('city.b64'):
        for rec in C.walk_scene('city.b64')['roads']:
            pts = rec[-1]
            if len(pts) < 2 or contains_xy(cityPoly, *pts[len(pts) // 2]): continue
            for i in range(len(pts) - 1): segs.append((pts[i], pts[i + 1], rec[1], rec[2]))
    ribbons = [LineString([a, b]).buffer(w / 2 + 2) for a, b, w, rt in segs]
    rbTree = STRtree(ribbons)
    excl = [g for g, k in packed_areas]
    if os.path.exists('city.b64'):
        for rec in C.walk_scene('city.b64')['areas']:
            if len(rec[-1]) >= 3:
                try: excl.append(Polygon(rec[-1]))
                except Exception: pass
    exclTree = STRtree(excl)
    placed = {}
    WHY = {'city': 0, 'covered': 0, 'landuse': 0, 'footprint': 0, 'road': 0, 'park_water': 0, 'placed': 0, 'ok': 0, 'no_landuse_segments': 0, 'grid_segments': 0}
    # a dense grid of residential streets is a neighbourhood whether or not anyone drew the
    # land use around it: a class-5 segment with at least GRID_N other street segments within
    # 120 m of its midpoint counts as residential land (a lone lane through fields does not)
    GRID_N = 8
    segTree = STRtree([LineString([a, b]) for a, b, w, rt in segs])
    NKIND = {'res': 0, 'com': 0, 'ind': 0}
    def placed_hit(rect):
        c = rect.centroid; gx, gz = int(c.x // 100), int(c.y // 100)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for q in placed.get((gx + i, gz + j), ()):
                    if q.intersects(rect): return True
        return False
    def place(rect, kind):
        c = rect.centroid; placed.setdefault((int(c.x // 100), int(c.y // 100)), []).append(rect)
        h0, bt = INFILL_H[kind]
        emit(rect, h0 - 0.5 + ((c.x * 0.37 + c.y * 0.11) % 1.0) * 1.5, 0, bt)
    for a, b, w, rt in segs:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 20: continue
        dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = -dz, dx
        seg = LineString([a, b])
        kinds = {luKinds[i] for i in luTree.query(seg) if lus[i].intersects(seg)}
        grid = False
        if not kinds:
            WHY['no_landuse_segments'] += 1
            if rt == 5 and not contains_xy(cityPoly, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2):
                m2 = Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2).buffer(120)
                if len(segTree.query(m2)) - 1 >= GRID_N: grid = True; WHY['grid_segments'] += 1
            if not grid: continue
        kind = 'res' if (grid or 'res' in kinds) else ('com' if 'com' in kinds else 'ind')
        if kind != 'res' and rt > 4: continue   # commerce and industry only along the main roads
        step, along, deep, setback = {'res': (14.0, 9.0, 11.0, 9.0), 'com': (40.0, 24.0, 18.0, 12.0), 'ind': (60.0, 36.0, 26.0, 14.0)}[kind]
        off = w / 2 + setback + deep / 2
        for side in (1, -1):
            run = []
            def flush():
                global n_inf
                if not run: return
                t0, t1 = run[0] - along / 2, run[-1] + along / 2
                cx0, cz0 = a[0] + dx * t0 + nx * side * off, a[1] + dz * t0 + nz * side * off
                cx1, cz1 = a[0] + dx * t1 + nx * side * off, a[1] + dz * t1 + nz * side * off
                hx, hz = nx * side * deep / 2, nz * side * deep / 2
                strip = Polygon([(cx0 - hx, cz0 - hz), (cx1 - hx, cz1 - hz), (cx1 + hx, cz1 + hz), (cx0 + hx, cz0 + hz)])
                place(strip, kind); n_inf += 1; NKIND[kind] += 1
                run.clear()
            t = along / 2 + 3
            while t + along / 2 < L - 3:
                cx, cz = a[0] + dx * t + nx * side * off, a[1] + dz * t + nz * side * off
                ok = False
                if contains_xy(cityPoly, cx, cz) or not inBox(cx, cz, CITY): WHY['city'] += 1   # never inside the line, never past the box edge (the grid fallback follows streets to it)
                elif covered(cx, cz) >= 0.10: WHY['covered'] += 1
                elif not grid and not any(luKinds[i] == kind and contains_xy(lus[i], cx, cz) for i in luTree.query(Point(cx, cz))): WHY['landuse'] += 1
                else:
                    ax, az = dx * along / 2, dz * along / 2
                    hx, hz = nx * side * deep / 2, nz * side * deep / 2
                    rect = Polygon([(cx - ax - hx, cz - az - hz), (cx + ax - hx, cz + az - hz), (cx + ax + hx, cz + az + hz), (cx - ax + hx, cz - az + hz)])
                    pad = rect.buffer(3)
                    if any(existing[i].intersects(pad) for i in exTree.query(pad)): WHY['footprint'] += 1
                    elif any(ribbons[i].intersects(rect) for i in rbTree.query(rect)): WHY['road'] += 1
                    elif any(excl[i].intersects(rect) for i in exclTree.query(rect)): WHY['park_water'] += 1
                    elif placed_hit(rect): WHY['placed'] += 1
                    else: ok = True; WHY['ok'] += 1
                if ok:
                    run.append(t)
                    if len(run) >= 6: flush()
                else:
                    flush()
                t += step
            flush()
    print(f'filler: {n_inf} strips along {len(segs)} street segments inside {len(lus)} land-use polygons; by kind {NKIND}; slots {WHY}', flush=True)
else:
    print('filler: skipped (osm_landuse_raw.json or city_limit.json missing)', flush=True)
body = body_b + body_r + body_a

if SAT:
    for rec, v in SAT[:12]: print('  SATURATED', rec, round(v, 1))
    sys.exit(f'ERROR: {len(SAT)} int16 saturations; outskirts.b64 not written')
blob = struct.pack('<4i', MAGIC, nb, nr, na) + struct.pack('<%dh' % len(body), *body)
open('outskirts.b64', 'w').write(base64.b64encode(blob).decode('ascii'))
print(f'outskirts.b64: {len(blob):,} bytes binary, {len(blob) * 4 // 3:,} base64 ({nb} buildings, {nr} roads, {na} areas)', flush=True)
