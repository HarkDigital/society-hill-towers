#!/usr/bin/env python3
"""osm_city_raw.json -> city.b64 : the far ring (rest of Philadelphia) at 0.7 m units.
city.b64 is a derivative database of OpenStreetMap data (ODbL): see ../DATA-LICENSE.md.
Same body layout as wide.b64 (n, h*5, minH*5, type, attr, roof, pts...; magic 0x5348545B) but scale 0.7 and with
rowhouse rows MERGED into block strips (shapely union) so the whole city fits the
artifact's 16 MB page budget. Buildings inside the wide box are skipped (covered),
and so are area rings (parks/water/aprons) whose centroid sits inside it - pack_wide
owns those; they used to be packed by both tiers and z-fought.
Guards: an int16 saturation in clip() is fatal (city.b64 is not written); a missing
join LUT (lidar_city_heights.json, lidar_cache/opa_city.json, lidar_cache/roof_city.json)
is fatal unless --allow-missing, because a repack without one silently dropped every
measured height / OPA facade attribute / roof colour from the far ring.
Rings over budget (32 vertices per building, 90 per area) are Douglas-Peucker'd down
(shapely simplify with a doubling tolerance), not strided every k-th vertex.
Frame: philly_frame.py (the scene's own projection). This script used to hardcode
KX=85350, which put the far ring up to ~1.1 m east of the scene at its 16.5 km edge;
the committed city.b64 keeps that offset until the next rerun.
Run with the scratchpad venv python (needs shapely)."""
import argparse, json, math, struct, base64, sys
from shapely.geometry import Polygon, LineString, box as sbox
from shapely.ops import unary_union, polygonize
from philly_frame import LON0, LAT0, KX, KZ

ap = argparse.ArgumentParser(description='osm_city_raw.json -> city.b64 (far ring)')
ap.add_argument('--allow-missing', action='store_true',
                help='pack even when a join LUT (LiDAR heights / OPA attrs / roof colours) is missing; '
                     'the affected attributes are dropped from the far ring')
ARGS = ap.parse_args()

S = 0.7
WIDE = (-3700, 2300, -4480, 6400)
CITY = (-12000, 16500, -21700, 9700)
BT = {'generic': 0, 'house': 1, 'residential': 1, 'terrace': 1, 'apartments': 2, 'detached': 1, 'semidetached_house': 1,
      'commercial': 3, 'retail': 3, 'office': 3, 'hotel': 3, 'industrial': 4, 'warehouse': 4, 'garage': 4, 'parking': 4,
      'church': 5, 'cathedral': 5, 'chapel': 5, 'school': 6, 'civic': 6, 'hospital': 6, 'university': 6}
HDEF = {'house': 8.0, 'residential': 8.0, 'detached': 7.5, 'terrace': 8.5, 'semidetached_house': 8.0, 'apartments': 11,
        'garage': 3.5, 'garages': 3.5, 'shed': 3, 'commercial': 7.5, 'retail': 7.5, 'office': 10, 'industrial': 8,
        'warehouse': 9, 'church': 13, 'cathedral': 15, 'chapel': 9, 'school': 10, 'hospital': 14, 'university': 12}
RT = {'motorway': 0, 'motorway_link': 0, 'trunk': 1, 'trunk_link': 1, 'primary': 2, 'secondary': 3, 'tertiary': 4, 'residential': 5}
RW = {0: 16, 1: 14, 2: 12, 3: 10, 4: 9, 5: 7}

raw = json.load(open('osm_city_raw.json'))
els = raw['elements']
nodes = {}
for el in els:
    if el.get('type') == 'node':
        nodes[el['id']] = ((el['lon'] - LON0) * KX, (LAT0 - el['lat']) * KZ)

SAT = []      # (record, value) for every clip() that fell outside int16 - fatal after packing
_rec = None   # the record being packed right now, for the saturation report
def clip(v):
    r = int(round(v))
    if r > 32767 or r < -32767:
        SAT.append((_rec, v))
        return max(-32767, min(32767, r))
    return r
def inBox(x, z, B): return B[0] <= x <= B[1] and B[2] <= z <= B[3]

def ring_budget(pg, budget, tol):
    """Exterior ring of pg as [(x, z), ...] with at most `budget` vertices: Douglas-Peucker
    (shapely simplify, topology-preserving) with a doubling tolerance. Replaces the old
    every-k-th-vertex stride, which kept vertices by position rather than shape (a corner
    could vanish) and did not even hold the budget (len // budget is 1 up to 2*budget-1)."""
    ext = list(pg.exterior.coords)[:-1]
    t = tol
    while len(ext) > budget and t < 4096:
        sp = list(pg.simplify(t).exterior.coords)[:-1]
        if len(sp) < len(ext): ext = sp
        t *= 2
    if len(ext) > budget:   # DP could not get there (degenerate ring): uniform stride as a last resort
        ext = ext[::-(-len(ext) // budget)]
    return ext

# join LUTs. A missing one used to WARN and continue, so a repack silently dropped every
# attribute it carried from the far ring; now fatal unless --allow-missing.
def _load(p, what):
    try:
        return json.load(open(p))
    except FileNotFoundError:
        if ARGS.allow_missing:
            print(f'WARNING: {p} missing - every {what} dropped from city.b64 (--allow-missing)', flush=True)
            return {}
        sys.exit(f'ERROR: {p} missing - every {what} would be silently dropped from city.b64; '
                 f'regenerate it or pass --allow-missing')
# 2022-LiDAR measured heights per OSM way (lidar_join.py). Measured wins over
# levels-derived guesses and type defaults; an explicit height tag survives only
# when TALLER (spires LiDAR under-reads, towers finished after the 2022 flight).
LIDAR_H = {int(k): v for k, v in _load('lidar_city_heights.json', 'LiDAR-measured height').items()}
# OPA facade attrs + sampled roof palette indices per way (Tier-1 facade pass)
OPA_A = {int(k): v for k, v in _load('lidar_cache/opa_city.json', 'OPA facade attribute').items()}
ROOF_I = {int(k): v for k, v in _load('lidar_cache/roof_city.json', 'sampled roof colour').items()}

def attr_word(wid, h):
    fa = OPA_A.get(wid)
    if not fa: return -1
    u, m, e, st = fa
    fq = 0
    if st and h:
        r = h / st
        if 2.2 <= r <= 5.2:
            fq = min(25, max(1, int(round((min(r, 4.6) - 2.2) / 0.1)) + 1))
    return (u & 7) | ((m & 7) << 3) | ((e & 15) << 6) | (fq << 10)

def parseH(t, wid=None):
    h = t.get('height')
    tag = None
    if h:
        try: tag = max(3, float(str(h).replace('m', '').strip()))
        except ValueError: pass
    m = LIDAR_H.get(wid)
    if m is not None:
        return max(tag, m) if tag else m
    if tag is not None:
        return tag
    lv = t.get('building:levels')
    if lv:
        try: return max(3, float(lv) * 3.2 + 1.2)
        except ValueError: pass
    return HDEF.get(t.get('building'), 7.0)

merge_groups = {}   # (cellx, cellz, hbucket) -> [Polygon]
solo = []           # (poly, h, btype) kept individual (tall / churches)
n_in = 0
ways = [el for el in els if el.get('type') == 'way']
for el in ways:
    t = el.get('tags') or {}
    if 'building' not in t: continue
    pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts) >= 2 and pts[0] == pts[-1]: pts = pts[:-1]
    if len(pts) < 3: continue
    cx = sum(p[0] for p in pts) / len(pts); cz = sum(p[1] for p in pts) / len(pts)
    if inBox(cx, cz, WIDE) or not inBox(cx, cz, CITY): continue
    try: pg = Polygon(pts)
    except Exception: continue
    if not pg.is_valid: pg = pg.buffer(0)
    if pg.is_empty or pg.area < 30: continue
    h = parseH(t, el['id'])
    if h < 5 and pg.area < 60: continue   # sheds/garages: invisible at far-ring distances
    bt = BT.get(t.get('building'), 0)
    aw_ = attr_word(el['id'], h)
    rw_ = ROOF_I.get(el['id'], -1)
    n_in += 1
    if h > 20 or bt == 5:
        solo.append((pg, h, bt, aw_, rw_))
    else:
        key = (int(cx // 400), int(cz // 400), int(round(h / 4)))
        merge_groups.setdefault(key, []).append((pg, aw_, rw_))

body = []
nb = 0
def emit(pg, h, mh, bt, aw_=-1, rw_=-1):
    global nb, _rec
    ext = ring_budget(pg, 32, 1.0)
    if len(ext) < 3: return
    _rec = ('building', bt, round(h, 1), tuple(round(c) for c in (pg.centroid.x, pg.centroid.y)))
    body.extend([len(ext), clip(min(6500, h) * 5), clip(mh * 5), bt, aw_, rw_])
    for x, z in ext: body.extend([clip(x / S), clip(z / S)])
    nb += 1

from collections import Counter
for (gx, gz, hb), members in merge_groups.items():
    h = max(4, hb * 4)
    pgs = [m[0] for m in members]
    aws = Counter(m[1] for m in members if m[1] != -1)
    rws = Counter(m[2] for m in members if m[2] != -1)
    aw_ = aws.most_common(1)[0][0] if aws else -1
    rw_ = rws.most_common(1)[0][0] if rws else -1
    merged = unary_union([p.buffer(1.8, join_style=2) for p in pgs]).buffer(-1.8, join_style=2)
    geoms = list(merged.geoms) if merged.geom_type == 'MultiPolygon' else [merged]
    for g in geoms:
        if g.is_empty or g.area < 70: continue
        emit(Polygon(g.exterior).simplify(1.35), h, 0, 1 if h <= 12 else 2, aw_, rw_)
for pg, h, bt, aw_, rw_ in solo:
    emit(pg.simplify(0.8), h, 0, bt, aw_, rw_)
print(f'buildings: {n_in} in -> {nb} packed', flush=True)

# roads (+ runways/taxiways as gray ribbons). Ways are SPLIT into runs at bbox exits
# (point-filtering grew phantom chords across excursions) and long ways are split, not
# truncated; local classes keep their runs OUTSIDE the wide box instead of vanishing
# entirely when any point touches it.
nr = 0
RES_BOX = (-9500, 9500, -13500, 9700)

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

CITYM = (CITY[0] - 300, CITY[1] + 300, CITY[2] - 300, CITY[3] + 300)
WIDEM = (WIDE[0] - 150, WIDE[1] + 150, WIDE[2] - 150, WIDE[3] + 150)
for el in ways:
    t = el.get('tags') or {}
    rt = None; w = None
    if t.get('highway') in RT:
        rt = RT[t['highway']]
        w = RW[rt]
    elif t.get('aeroway') == 'runway': rt, w = 5, 45
    elif t.get('aeroway') == 'taxiway': rt, w = 5, 16
    if rt is None: continue
    raw = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(raw) < 2: continue
    if rt == 5 and t.get('highway') == 'residential' and not any(inBox(p[0], p[1], RES_BOX) for p in raw):
        continue
    for run in _runs(raw, lambda q: inBox(q[0], q[1], CITYM)):
        subruns = _runs(run, lambda q: not inBox(q[0], q[1], WIDEM)) if t.get('highway') in ('residential', 'tertiary') else [run]
        for sub in subruns:
            pts = list(LineString(sub).simplify(1.6).coords) if len(sub) > 2 else sub
            if len(pts) < 2: continue
            _rec = ('road', el['id'], t.get('highway') or t.get('aeroway'), t.get('name'))
            for c0 in range(0, len(pts) - 1, 119):
                chunk = pts[c0:c0 + 120]
                if len(chunk) < 2: continue
                body_road = [len(chunk), clip(w * 10), rt]
                for x, z in chunk: body_road.extend([clip(x / S), clip(z / S)])
                body.extend(body_road)
                nr += 1
print(f'roads: {nr}', flush=True)

# areas: parks/green (0), water (1), aprons as concrete (2). Rings are clipped to the
# city box geometrically (intersection), which is what keeps them inside int16; a ring
# whose (unclipped, vertex-mean) centroid lies inside the wide box belongs to pack_wide.
na = 0
n_wide = 0
cityBox = sbox(CITY[0], CITY[2], CITY[1], CITY[3])
def emitArea(pg, kind, cxz):
    global na, _rec
    if pg.is_empty or pg.area < 4000: return
    ext = ring_budget(pg, 90, 2.0)
    if len(ext) < 3: return
    _rec = ('area', kind, tuple(round(c) for c in cxz))
    body.extend([len(ext), kind])
    for x, z in ext: body.extend([clip(x / S), clip(z / S)])
    na += 1

def ring_cent(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

GREEN = ('park', 'golf_course', 'nature_reserve')
WIDE_KINDS = ('park', 'garden', 'playground', 'pitch')   # what process_osm.py / pack_wide.py pack as areas
def wideOwns(t): return t.get('leisure') in WIDE_KINDS or t.get('natural') == 'water'
LU = ('grass', 'cemetery', 'forest', 'recreation_ground')
wayById = {el['id']: el for el in ways}
for el in ways:
    t = el.get('tags') or {}
    kind = None
    if t.get('leisure') in GREEN or t.get('landuse') in LU: kind = 0
    elif t.get('natural') == 'water': kind = 1
    elif t.get('aeroway') == 'apron': kind = 2
    if kind is None: continue
    pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts) >= 2 and pts[0] == pts[-1]: pts = pts[:-1]
    if len(pts) < 3: continue
    cxz = ring_cent(pts)
    # pack_wide's, but only for the kinds process_osm.py gives scene_wide.json (park, garden,
    # playground, pitch, water): a cemetery, golf course, forest or apron in the wide box would
    # otherwise belong to nobody
    if inBox(cxz[0], cxz[1], WIDE) and wideOwns(t): n_wide += 1; continue
    try: pg = Polygon(pts).buffer(0)
    except Exception: continue
    geoms = list(pg.geoms) if pg.geom_type == 'MultiPolygon' else [pg]
    for g in geoms: emitArea(g.intersection(cityBox).simplify(1.2) if not g.is_empty else g, kind, cxz)
# water + park relations: polygonize outer member ways
for el in els:
    if el.get('type') != 'relation': continue
    t = el.get('tags') or {}
    kind = 1 if t.get('natural') == 'water' else (0 if t.get('leisure') == 'park' else None)
    if kind is None: continue
    lines = []
    for m in el.get('members', []):
        if m.get('type') == 'way' and m.get('role') in ('outer', ''):
            w2 = wayById.get(m['ref'])
            if not w2: continue
            pts = [nodes[n] for n in w2.get('nodes', []) if n in nodes]
            if len(pts) >= 2: lines.append(LineString(pts))
    if not lines: continue
    try:
        for g in polygonize(unary_union(lines)):
            cxz = ring_cent(list(g.exterior.coords)[:-1])
            if inBox(cxz[0], cxz[1], WIDE) and wideOwns(t): n_wide += 1; continue   # pack_wide's, for the kinds it packs
            gg = g.intersection(cityBox)
            geoms = list(gg.geoms) if gg.geom_type == 'MultiPolygon' else [gg]
            for g2 in geoms:
                if g2.geom_type == 'Polygon': emitArea(g2.simplify(1.5), kind, cxz)
    except Exception: pass
print(f'areas: {na} ({n_wide} left to pack_wide: centroid inside the wide box)', flush=True)

if SAT:
    print(f'ERROR: {len(SAT)} coordinate(s) saturated int16 (|v| > 32767 at {S} m units, i.e. beyond '
          f'+/-{32767 * S:.0f} m); city.b64 NOT written. Offending records:', file=sys.stderr, flush=True)
    shown = set()
    for rec, v in SAT:
        if rec in shown: continue
        shown.add(rec)
        print(f'   {rec}  value {v:.0f} ({v * S:.0f} m)', file=sys.stderr, flush=True)
        if len(shown) >= 12: break
    sys.exit(1)

hdr = struct.pack('<4i', 0x5348545B, nb, nr, na)
blob = hdr + struct.pack('<%dh' % len(body), *body)
b64 = base64.b64encode(blob).decode()
open('city.b64', 'w').write(b64)
print(f'city.b64: {len(b64)/1e6:.2f} MB base64 ({nb} buildings, {nr} roads, {na} areas)', flush=True)
