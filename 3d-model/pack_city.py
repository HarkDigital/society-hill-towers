#!/usr/bin/env python3
"""osm_city_raw.json -> city.b64 : the far ring (rest of Philadelphia) at 0.7 m units.
city.b64 is a derivative database of OpenStreetMap data (ODbL): see ../DATA-LICENSE.md.
Same body layout as wide.b64 (n, h*5, minH*5, type, attr, roof, pts...; magic 0x5348545C, the roof word packing the colour index with a form and rise, see roof_word) but scale 0.7 and with
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
import argparse, json, math, os, struct, base64, sys
from pack_common import dedupe_stacked, nudge_coplanar   # Round 71: no two walls on one plane facing the same way
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
# Round 87 adds unclassified, living_street and pedestrian, from city_streets_raw.json: they
# are exactly the classes pack_wide.py already draws, and in Fairmount Park they ARE the
# connecting drives (Lemon Hill, Waterworks, Aquarium and Sedgley Drives are all
# `unclassified`). Without them the far ring carried 68 per cent of the park's road length
# against the wide tier's 90, and a quarter of its run endpoints dangled in the grass.
RT = {'motorway': 0, 'motorway_link': 0, 'trunk': 1, 'trunk_link': 1, 'primary': 2, 'secondary': 3, 'tertiary': 4,
      'residential': 5, 'unclassified': 5, 'living_street': 5, 'pedestrian': 6}
RW = {0: 16, 1: 14, 2: 12, 3: 10, 4: 9, 5: 7, 6: 5}
# the classes the wide tier also draws: their runs are cut OUT of the wide box so the two
# tiers never pave the same street twice
LOCAL_CLASSES = ('residential', 'tertiary', 'unclassified', 'living_street', 'pedestrian')

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
# roof FORMS: the LiDAR streaming pass (fetch_lidar_roofs.py) where it resolved a building,
# else the OSM roof:shape tag (roof_tags.py); both optional, the app's lottery covers the rest.
# Packed into the roof word with the colour index: (idx + 1) & 0x1FF | form << 9 | rise << 12,
# form 0 unresolved, 1 gable, 2 hip, 3 skillion, 4 measured or tagged flat; rise in half metres
def _opt(p):
    try: return json.load(open(p))
    except FileNotFoundError: return None
ROOF_LIDAR = {int(k): v for k, v in (_opt('lidar_city_roofs.json') or {}).items()}
ROOF_TAG = {int(k): v for k, v in ((_opt('lidar_cache/roof_shapes.json') or {}).get('byId', {})).items()}
print(f'roof forms: {len(ROOF_LIDAR)} LiDAR-measured, {len(ROOF_TAG)} OSM-tagged', flush=True)
TAGFORM = {0: 4, 1: 1, 2: 2, 3: 3}
def roof_form(wid):
    m = ROOF_LIDAR.get(wid)
    if m and m[0] in (0, 1, 2):
        return (4 if m[0] == 0 else m[0], max(0.0, float(m[2]) - float(m[1])))
    t = ROOF_TAG.get(wid)
    return (TAGFORM.get(t, 0), 0.0) if t is not None else (0, 0.0)
def roof_word(idx, form, rise):
    v = ((idx + 1) & 0x1FF) | ((form & 7) << 9) | (min(15, max(0, int(round(rise * 2)))) << 12)
    return v - 65536 if v > 32767 else v

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
    rf_ = roof_form(el['id'])
    n_in += 1
    if h > 20 or bt == 5:
        solo.append((pg, h, bt, aw_, rw_, rf_))
    else:
        key = (int(cx // 400), int(cz // 400), int(round(h / 4)))
        merge_groups.setdefault(key, []).append((pg, aw_, rw_, rf_))

body = []
nb = 0
pending = []   # (poly, h, mh, bt, aw_, rw_, rf_): every strip and solo, guarded before it is emitted (Round 71)
def emit(pg, h, mh, bt, aw_=-1, rw_=-1, rf_=(0, 0.0)):
    global nb, _rec
    ext = ring_budget(pg, 32, 1.0)
    if len(ext) < 3: return
    _rec = ('building', bt, round(h, 1), tuple(round(c) for c in (pg.centroid.x, pg.centroid.y)))
    body.extend([len(ext), clip(min(6500, h) * 5), clip(mh * 5), bt, aw_, roof_word(rw_, rf_[0], rf_[1])])
    for x, z in ext: body.extend([clip(x / S), clip(z / S)])
    nb += 1

from collections import Counter
# Every piece of a merged cell takes the attributes of ITS OWN members (Round 65). The cell
# used to hand all its strips one OPA attribute word and one roof colour, the most common
# in the whole 400 m cell, and the mode of a palette histogram is dark: the tar-roof greys
# collapse into three or four bins while the light roofs scatter across many, so the far
# ring's roofs shipped at half the luminance of the same blocks' per-building colours
# (north of York Street 0.104 against 0.206 in the app's register, the outer districts next
# door at 0.228) and every strip in a cell wore one era's facade. Now the attribute word is
# the mode among the piece's members and the roof colour is the sampled colour of the member
# whose luminance, in the register the app draws (roofInv, a 2.364 power that compresses the
# darks), is nearest the members' mean: a strip reads like its own houses, and the colour is
# always one a roof in it was measured as. (The palette entry nearest the mean sRGB colour
# was tried first and landed at 0.183: averaging light and dark roofs in sRGB and snapping
# to the palette leans dark once the power curve is applied.)
ROOF_PAL = _opt('lidar_cache/roof_palette.json')
def _roof_lum(rgb):
    inv = lambda t: min(1.0, (max(t, 4) / 31.5) ** 2.364 / 255)   # app.js roofInv
    return 0.2126 * inv(rgb[0]) + 0.7152 * inv(rgb[1]) + 0.0722 * inv(rgb[2])
ROOF_LUM = [_roof_lum(c) for c in ROOF_PAL] if ROOF_PAL else None
def roof_pick(idxs):
    idxs = [i for i in idxs if i is not None and i >= 0]
    if not idxs: return -1
    if not ROOF_LUM: return Counter(idxs).most_common(1)[0][0]
    mean = sum(ROOF_LUM[i] for i in idxs) / len(idxs)
    return min(idxs, key=lambda i: (abs(ROOF_LUM[i] - mean), i))
def attr_pick(members):
    aws = Counter(m[1] for m in members if m[1] != -1)
    return aws.most_common(1)[0][0] if aws else -1
for (gx, gz, hb), members in merge_groups.items():
    h = max(4, hb * 4)
    pgs = [m[0] for m in members]
    merged = unary_union([p.buffer(1.8, join_style=2) for p in pgs]).buffer(-1.8, join_style=2)
    geoms = list(merged.geoms) if merged.geom_type == 'MultiPolygon' else [merged]
    for g in geoms:
        if g.is_empty or g.area < 70: continue
        # a roof form only when this piece is one building (a strip of merged rows stays flat)
        mine = [m for m in members if g.contains(m[0].representative_point())] if len(members) > 1 else members
        if not mine: mine = members
        aw_ = attr_pick(mine)
        rw_ = roof_pick([m[2] for m in mine])
        rf_ = mine[0][3] if len(mine) == 1 else (0, 0.0)
        pending.append((Polygon(g.exterior).simplify(1.35), h, 0, 1 if h <= 12 else 2, aw_, rw_, rf_))
for pg, h, bt, aw_, rw_, rf_ in solo:
    pending.append((pg.simplify(0.8), h, 0, bt, aw_, rw_, rf_))
# Round 71 (Mike: a tower at East Falls still flickered): the guards pack_wide.py has carried
# since the outer districts' z-fight rounds. Two outlines of one building (OSM draws some
# twice, or a tower over its own podium) keep only the taller; a smaller record whose wall
# lies on a larger one's plane facing the same way (a tower flush with the block strip its
# podium merged into, two neighbouring outlines drawn over each other) is inset 1.05 m per
# link, over this packer's 0.7 m grid, so the wall hides where they overlap and sits
# imperceptibly recessed where it rises above
items = []
for i, (pg, h, mh, bt, aw_, rw_, rf_) in enumerate(pending):
    ring = [(x, z) for x, z in list(pg.exterior.coords)[:-1]]
    if len(ring) < 3: continue
    items.append((pg.centroid.x, pg.centroid.y, pg.area, float(h), float(mh), ['c', ring, i]))
kept, n_dropped = dedupe_stacked(items)
n_nudged = 0
for _pass in range(4):
    _n = nudge_coplanar(kept, 1.5 * S)
    n_nudged += _n
    if not _n: break
for it in kept:
    pg, h, mh, bt, aw_, rw_, rf_ = pending[it[5][2]]
    try: pg2 = Polygon(it[5][1])
    except Exception: pg2 = pg
    if pg2.is_empty or not pg2.is_valid: pg2 = pg
    emit(pg2, h, mh, bt, aw_, rw_, rf_)
print(f'buildings: {n_in} in -> {nb} packed ({n_dropped} stacked duplicates dropped, {n_nudged} coplanar walls inset)', flush=True)

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

# the supplementary street classes (fetch_city_streets.py). That fetch uses `out geom`, so a
# way carries its own coordinates rather than node ids; they are projected into the same
# `nodes` table under synthetic ids so the loop below needs no special case.
road_ways = list(ways)
if os.path.exists('city_streets_raw.json'):
    _st = json.load(open('city_streets_raw.json'))['elements']
    _sid = -1
    _n_st = 0
    for el in _st:
        if el.get('type') != 'way':
            continue
        geom = el.get('geometry') or []
        if len(geom) < 2:
            continue
        ids = []
        for g in geom:
            if g is None or 'lon' not in g:
                continue
            nodes[_sid] = ((g['lon'] - LON0) * KX, (LAT0 - g['lat']) * KZ)
            ids.append(_sid)
            _sid -= 1
        if len(ids) < 2:
            continue
        road_ways.append({'type': 'way', 'id': el.get('id'), 'nodes': ids, 'tags': el.get('tags') or {}})
        _n_st += 1
    print(f'city_streets_raw.json: {_n_st} supplementary street ways', flush=True)
else:
    print('city_streets_raw.json missing - the far ring keeps the pre-Round-87 class list', flush=True)

for el in road_ways:
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
    # Round 88: a local way is cut out of the wide margin only when the wide extract carries it,
    # which means a node inside the wide box (Overpass returns whole ways that touch the bbox, and
    # fetch_wide's bbox is the box). A way running alongside the edge inside the 150 m band never
    # reached the wide set, so cutting it here left it in neither tier: 139 ways and 13.9 km
    # (Napoli Way, Genoa Drive, South 24th Street, Bambrey Terrace) plus 26 and 1.7 km of the
    # supplementary classes. The page's far ring cedes a margin segment only where a wide
    # segment really lies along it (wideOwned), so what stays here is never paved twice.
    inWideAny = any(inBox(p[0], p[1], WIDE) for p in raw)
    for run in _runs(raw, lambda q: inBox(q[0], q[1], CITYM)):
        subruns = _runs(run, lambda q: not inBox(q[0], q[1], WIDEM)) if (t.get('highway') in LOCAL_CLASSES and inWideAny) else [run]
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

hdr = struct.pack('<4i', 0x5348545C, nb, nr, na)
blob = hdr + struct.pack('<%dh' % len(body), *body)
b64 = base64.b64encode(blob).decode()
open('city.b64', 'w').write(b64)
print(f'city.b64: {len(b64)/1e6:.2f} MB base64 ({nb} buildings, {nr} roads, {na} areas)', flush=True)
