#!/usr/bin/env python3
"""osm_city_raw.json -> city.b64 : the far ring (rest of Philadelphia) at 0.7 m units.
Same body layout as wide.b64 (n, h*5, minH*5, type, pts...) but scale 0.7 and with
rowhouse rows MERGED into block strips (shapely union) so the whole city fits the
artifact's 16 MB page budget. Buildings inside the wide box are skipped (covered).
Run with the scratchpad venv python (needs shapely)."""
import json, math, struct, base64, sys
from shapely.geometry import Polygon, LineString, box as sbox
from shapely.ops import unary_union, polygonize

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
        nodes[el['id']] = ((el['lon'] + 75.144748) * 85350, (39.945474 - el['lat']) * 110574)

def clip(v): return max(-32767, min(32767, int(round(v))))
def inBox(x, z, B): return B[0] <= x <= B[1] and B[2] <= z <= B[3]

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
    h = parseH(t)
    if h < 5 and pg.area < 60: continue   # sheds/garages: invisible at far-ring distances
    bt = BT.get(t.get('building'), 0)
    n_in += 1
    if h > 20 or bt == 5:
        solo.append((pg, h, bt))
    else:
        key = (int(cx // 400), int(cz // 400), int(round(h / 4)))
        merge_groups.setdefault(key, []).append(pg)

body = []
nb = 0
def emit(pg, h, mh, bt):
    global nb
    ext = list(pg.exterior.coords)[:-1]
    if len(ext) < 3 or len(ext) > 32:
        if len(ext) > 32: ext = ext[::max(1, len(ext) // 32)]
        if len(ext) < 3: return
    body.extend([len(ext), clip(min(6500, h) * 5), clip(mh * 5), bt])
    for x, z in ext: body.extend([clip(x / S), clip(z / S)])
    nb += 1

for (gx, gz, hb), pgs in merge_groups.items():
    h = max(4, hb * 4)
    merged = unary_union([p.buffer(1.8, join_style=2) for p in pgs]).buffer(-1.8, join_style=2)
    geoms = list(merged.geoms) if merged.geom_type == 'MultiPolygon' else [merged]
    for g in geoms:
        if g.is_empty or g.area < 70: continue
        emit(Polygon(g.exterior).simplify(1.35), h, 0, 1 if h <= 12 else 2)
for pg, h, bt in solo:
    emit(pg.simplify(0.8), h, 0, bt)
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
            for c0 in range(0, len(pts) - 1, 119):
                chunk = pts[c0:c0 + 120]
                if len(chunk) < 2: continue
                body_road = [len(chunk), clip(w * 10), rt]
                for x, z in chunk: body_road.extend([clip(x / S), clip(z / S)])
                body.extend(body_road)
                nr += 1
print(f'roads: {nr}', flush=True)

# areas: parks/green (0), water (1), aprons as concrete (2)
na = 0
cityBox = sbox(CITY[0], CITY[2], CITY[1], CITY[3])
def emitArea(pg, kind):
    global na
    if pg.is_empty or pg.area < 4000: return
    ext = list(pg.exterior.coords)[:-1]
    if len(ext) < 3: return
    if len(ext) > 90: ext = ext[::max(1, len(ext) // 90)]
    if len(ext) < 3: return
    body.extend([len(ext), kind])
    for x, z in ext: body.extend([clip(x / S), clip(z / S)])
    na += 1

GREEN = ('park', 'golf_course', 'nature_reserve')
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
    try: pg = Polygon(pts).buffer(0)
    except Exception: continue
    geoms = list(pg.geoms) if pg.geom_type == 'MultiPolygon' else [pg]
    for g in geoms: emitArea(g.intersection(cityBox).simplify(1.2) if not g.is_empty else g, kind)
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
            gg = g.intersection(cityBox)
            geoms = list(gg.geoms) if gg.geom_type == 'MultiPolygon' else [gg]
            for g2 in geoms:
                if g2.geom_type == 'Polygon': emitArea(g2.simplify(1.5), kind)
    except Exception: pass
print(f'areas: {na}', flush=True)

hdr = struct.pack('<4i', 0x53485459, nb, nr, na)
blob = hdr + struct.pack('<%dh' % len(body), *body)
b64 = base64.b64encode(blob).decode()
open('city.b64', 'w').write(b64)
print(f'city.b64: {len(b64)/1e6:.2f} MB base64 ({nb} buildings, {nr} roads, {na} areas)', flush=True)
