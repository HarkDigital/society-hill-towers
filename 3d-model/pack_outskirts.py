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
import json, math, struct, base64, sys
from collections import Counter
from shapely.geometry import Polygon, LineString, box as sbox
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

body = []
nb = 0
def emit(pg, h, mh, bt):
    global nb, _rec
    ext = ring_budget(pg, 16, 1.5)
    if len(ext) < 3: return
    _rec = ('building', bt, round(h, 1), tuple(round(c) for c in (pg.centroid.x, pg.centroid.y)))
    body.extend([len(ext), clip(min(6500, h) * 5), clip(mh * 5), bt])
    for x, z in ext: body.extend([clip(x / S), clip(z / S)])
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
        for c0 in range(0, len(pts) - 1, 119):
            chunk = pts[c0:c0 + 120]
            if len(chunk) < 2: continue
            body.extend([len(chunk), clip(w * 10), rt])
            for x, z in chunk: body.extend([clip(x / S), clip(z / S)])
            nr += 1
print(f'roads: {nr}', flush=True)

# ---- areas: parks / green (0), water (1); clipped to the far-ring box
na = 0
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
        body.extend([len(ext), kind])
        for x, z in ext: body.extend([clip(x / S), clip(z / S)])
        na += 1
print(f'areas: {na}', flush=True)

if SAT:
    for rec, v in SAT[:12]: print('  SATURATED', rec, round(v, 1))
    sys.exit(f'ERROR: {len(SAT)} int16 saturations; outskirts.b64 not written')
blob = struct.pack('<4i', MAGIC, nb, nr, na) + struct.pack('<%dh' % len(body), *body)
open('outskirts.b64', 'w').write(base64.b64encode(blob).decode('ascii'))
print(f'outskirts.b64: {len(blob):,} bytes binary, {len(blob) * 4 // 3:,} base64 ({nb} buildings, {nr} roads, {na} areas)', flush=True)
