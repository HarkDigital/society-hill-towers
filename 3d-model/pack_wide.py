#!/usr/bin/env python3
"""scene_wide.json -> wide.b64 : compact int16 binary (0.2 m units) for the outer districts.
wide.b64 is a derivative database of OpenStreetMap data (ODbL): see ../DATA-LICENSE.md.
Layout: Int32[4] header (magic 0x5348545D, nBuildings, nRoads, nAreas), then Int16 body:
  building: n, h*5, minH*5, type, attr, roof, x1,z1,...
  road: n, w*10, type, pts...   area: n, kind, pts...
attr packs the OPA facade word u(3)|mat(3)|era(4)|floorH(5) (-1 = none); roof is
the sampled roof-palette index (-1 = none). The 0x53485458 format (no attr/roof
words) is still decoded by the app. Buildings inside the core bbox are dropped.
Guards: an int16 saturation in clip() is fatal (wide.b64 is not written) - the body
holds +/-6553 m, and the 2.5 km2 Fairmount Park ring reaches z = -7685 m, so area
rings are clipped to that box geometrically (shapely; without it the old silent
clamp is gone and the pack aborts instead). Rings over budget (48 vertices per
building/part, 120 per area) are Douglas-Peucker'd down with a doubling tolerance,
not strided every k-th vertex. Optional inputs (scene_south.json, parts_wide.json,
wide_landmarks_research.json) are fatal when missing unless --allow-missing, since
a silent skip dropped the whole south extension / every 3D part / the glass flags.
Frame: philly_frame.py for the research glass spots (they used KX=85350).
Wall colours: when bake_wall_colors.py has run for real (wall_palette.json not a dry run),
wide_walls.b64 is written beside wide.b64: Int32[4] header (magic 0x53485457, nBuildings,
nPalette, bytesPerRecord), the palette as nPalette sRGB byte triples, then the records
planar in wide.b64's building order (parts included): nBuildings palette index bytes (255
for none), then, when bytesPerRecord is 2, nBuildings facade hint bytes (the bake's trim
class in bits 0-1 and window class in bits 2-3, 0 for a building without a colour). A
fourth header word of 0 is the old one-byte layout, indices only."""
import argparse, json, math, os, struct, base64, sys
from philly_frame import LON0, LAT0, KX, KZ

ap = argparse.ArgumentParser(description='scene_wide.json -> wide.b64 (outer districts)')
ap.add_argument('--allow-missing', action='store_true',
                help='pack even when an optional input (scene_south.json, parts_wide.json, '
                     'wide_landmarks_research.json) is missing; what it carried is dropped')
ARGS = ap.parse_args()

CORE = (-640, 770, -520, 850)        # x0, x1, z0, z1 of the detailed core extract
WIDE = (-3700, 2300, -4480, 6400)    # wide bbox in local meters (south to the stadiums + Walt Whitman Bridge)
REPR = 32767 / 5                     # 6553.4 m: the largest |coordinate| the int16 0.2 m body can hold
BT = {'generic': 0, 'house': 1, 'residential': 1, 'terrace': 1, 'apartments': 2, 'detached': 1, 'semidetached_house': 1,
      'commercial': 3, 'retail': 3, 'office': 3, 'hotel': 3, 'industrial': 4, 'warehouse': 4, 'garage': 4, 'parking': 4,
      'church': 5, 'worship': 5, 'school': 6, 'civic': 6, 'hospital': 6, 'university': 6, 'roof': 7, 'ship': 7, 'stadium': 8, 'arena': 9}
RT = {'motorway': 0, 'motorway_link': 0, 'trunk': 1, 'trunk_link': 1, 'primary': 2, 'secondary': 3, 'tertiary': 4,
      'residential': 5, 'living_street': 5, 'unclassified': 5, 'pedestrian': 6}
AK = {'park': 0, 'water': 1, 'pier': 2}

def _optional(path, what):
    """An input whose absence used to be skipped silently, dropping `what` from wide.b64."""
    try:
        return json.load(open(path))
    except FileNotFoundError:
        if ARGS.allow_missing:
            print(f'WARNING: {path} missing - {what} dropped from wide.b64 (--allow-missing)', flush=True)
            return None
        sys.exit(f'ERROR: {path} missing - {what} would be silently dropped from wide.b64; '
                 f'regenerate it or pass --allow-missing')

d = json.load(open('scene_wide.json'))
# Mapillary block-face wall colours (bake_wall_colors.py): a palette index per scene
# building, carried on the building as _wall through the south merge below and written
# as wide_walls.b64 in wide.b64's record order; the facade hint byte rides along as
# _hint the same way when the bake wrote the *_hint arrays. A dry-run bake or a missing
# pair leaves the existing wide_walls.b64 untouched.
def _wall_colors():
    try:
        pal, col = json.load(open('wall_palette.json')), json.load(open('wall_colors.json'))
    except FileNotFoundError:
        print('WARNING: wall_palette.json / wall_colors.json missing - wide_walls.b64 left as it is', flush=True)
        return None
    if pal.get('dry_run'):
        print('WARNING: wall_palette.json is a dry run - wide_walls.b64 left as it is', flush=True)
        return None
    return pal['wall'], col
_walls = _wall_colors()
_hinted = bool(_walls) and 'wide_hint' in _walls[1]
def _wall_of(col, tag, i):
    """(_wall, _hint) of building i of scene `tag` from wall_colors.json (-1, 0 past its end)."""
    idx, hint = col[tag], col.get(tag + '_hint') or ()
    return (idx[i] if i < len(idx) else -1), (hint[i] if i < len(hint) else 0)
if _walls:
    for _i, _b in enumerate(d['buildings']):
        _b['_wall'], _b['_hint'] = _wall_of(_walls[1], 'wide', _i)
_south = _optional('scene_south.json', 'the south extension (stadium complex, Walt Whitman Bridge)')
if _south is not None:
    seenB = set(tuple(map(tuple, b['poly'][:3])) for b in d['buildings'])
    for _j, b in enumerate(_south['buildings']):
        if tuple(map(tuple, b['poly'][:3])) in seenB: continue
        if _walls: b['_wall'], b['_hint'] = _wall_of(_walls[1], 'south', _j)
        if (b.get('name') or '') == 'Xfinity Mobile Arena': b['t'] = 'arena'
        d['buildings'].append(b)
    d['roads'] += _south['roads']; d['areas'] += _south['areas']
    print('merged south scene')
_parts = _optional('parts_wide.json', 'the 3D building parts (skyscraper shafts, crowns, podiums)') or []
_research = _optional('wide_landmarks_research.json', 'the research glass-tower flags') or []

def cent(p): return sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p)
def area(p):
    a = 0
    for i in range(len(p)):
        u, v = p[i], p[(i + 1) % len(p)]
        a += u[0] * v[1] - v[0] * u[1]
    return abs(a / 2)
def simplify(pts, tol):
    # Douglas-Peucker on a closed ring (keeps at least 4 points)
    if len(pts) <= 4: return pts
    def dp(seg):
        if len(seg) < 3: return seg
        a, b = seg[0], seg[-1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz) or 1e-9
        best, bi = -1, -1
        for i in range(1, len(seg) - 1):
            p = seg[i]
            dist = abs((p[0] - a[0]) * dz - (p[1] - a[1]) * dx) / L
            if dist > best: best, bi = dist, i
        if best > tol: return dp(seg[:bi + 1])[:-1] + dp(seg[bi:])
        return [a, b]
    # split at the farthest point from pts[0] to make two open chains
    far = max(range(1, len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    out = dp(pts[:far + 1])[:-1] + dp(pts[far:] + [pts[0]])[:-1]
    return out if len(out) >= 3 else pts
def simplify_budget(pts, budget, tol):
    """Douglas-Peucker a closed ring down to at most `budget` vertices by doubling the
    tolerance from `tol`. Replaces the every-k-th-vertex stride, which kept vertices by
    position rather than shape (a corner could vanish) and did not even hold the budget
    (len // budget is 1 up to 2*budget-1 vertices)."""
    t = tol
    while len(pts) > budget and t < 4096:
        sp = simplify(pts, t)
        if len(sp) < len(pts): pts = sp
        t *= 2
    if len(pts) > budget:   # DP could not get there (degenerate ring): uniform stride as a last resort
        pts = pts[::-(-len(pts) // budget)]
    return pts

SAT = []      # (record, value) for every clip() that fell outside int16 - fatal after packing
_rec = None   # the record being packed right now, for the saturation report
def clip(v):
    r = int(round(v))
    if r > 32767 or r < -32767:
        SAT.append((_rec, v))
        return max(-32767, min(32767, r))
    return r
def touchesCore(poly, m=2):
    return any(CORE[0] - m <= q[0] <= CORE[1] + m and CORE[2] - m <= q[1] <= CORE[3] + m for q in poly)
def pip(x, z, poly):
    inside = False; j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]; xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi: inside = not inside
        j = i
    return inside

# geometric clip of area rings to the representable box (shapely optional)
try:
    from shapely.geometry import Polygon as _SPoly, box as _sbox
    _clipBox = _sbox(-(REPR - 1), -(REPR - 1), REPR - 1, REPR - 1)   # 1 m inside so rounding never lands on 32767
    HAVE_SHAPELY = True
except ImportError:
    HAVE_SHAPELY = False
    print('WARNING: shapely not importable - area rings are NOT clipped to the int16 box; '
          'a ring past +/-6552 m (Fairmount Park) aborts the pack', flush=True)

def clip_area(poly):
    """[(x, z), ...] -> the rings of poly inside the representable box. A ring entirely
    inside comes back untouched (byte-identical pack); one crossing the box is cut by
    intersection, so the far edge is a straight cut instead of a clamped, self-crossing zigzag."""
    if max(abs(c) for q in poly for c in q) <= REPR - 1 or not HAVE_SHAPELY:
        return [poly]
    try:
        g = _SPoly(poly).buffer(0).intersection(_clipBox)
    except Exception:
        return [poly]
    parts = list(g.geoms) if hasattr(g, 'geoms') else [g]
    return [[list(q) for q in p.exterior.coords[:-1]]
            for p in parts if p.geom_type == 'Polygon' and not p.is_empty and p.area >= 4]

# building:part centroids indexed on a 50 m grid: outlines that contain a part are dropped
partCells = {}
for pt in _parts:
    if len(pt['poly']) >= 3:
        cx, cz = cent(pt['poly']); partCells.setdefault((int(cx // 50), int(cz // 50)), []).append((cx, cz))
def containsPart(poly):
    xs = [q[0] for q in poly]; zs = [q[1] for q in poly]
    for gx in range(int(min(xs) // 50), int(max(xs) // 50) + 1):
        for gz in range(int(min(zs) // 50), int(max(zs) // 50) + 1):
            for (cx, cz) in partCells.get((gx, gz), []):
                if pip(cx, cz, poly): return True
    return False
def attr_word(b, h):
    """u(3)|mat(3)|era(4)|floorH(5): floorH quantized (2.2 + (q-1)*0.1 m), 0 = none."""
    fa = b.get('fa')
    if not fa: return -1
    u, m, e, st = fa
    fq = 0
    if st and h:
        r = h / st
        if 2.2 <= r <= 5.2:
            fq = min(25, max(1, int(round((min(r, 4.6) - 2.2) / 0.1)) + 1))
    return (u & 7) | ((m & 7) << 3) | ((e & 15) << 6) | (fq << 10)

# roof forms: scene buildings carry no OSM id, so each is matched to the nearest building
# way centroid (roof_tags.py's list, 4 m) and looks up the LiDAR pass, then the OSM tag.
# The roof word packs the sampled colour index with the form and rise: (idx + 1) & 0x1FF |
# form << 9 | rise << 12 (form 0 unresolved, 1 gable, 2 hip, 3 skillion, 4 known flat)
def _opt(p):
    try: return json.load(open(p))
    except FileNotFoundError: return None
_rs = _opt('lidar_cache/roof_shapes.json') or {'byId': {}, 'ways': []}
ROOF_TAG = {int(k): v for k, v in _rs['byId'].items()}
ROOF_LIDAR = {int(k): v for k, v in (_opt('lidar_city_roofs.json') or {}).items()}
_wgrid = {}
for wx, wz, wid in _rs['ways']:
    _wgrid.setdefault((int(wx // 20), int(wz // 20)), []).append((wx, wz, wid))
def way_at(cx, cz):
    best, bid = 16.0, None
    for gx in (-1, 0, 1):
        for gz in (-1, 0, 1):
            for wx, wz, wid in _wgrid.get((int(cx // 20) + gx, int(cz // 20) + gz), ()):
                d2 = (wx - cx) ** 2 + (wz - cz) ** 2
                if d2 < best: best, bid = d2, wid
    return bid
TAGFORM = {0: 4, 1: 1, 2: 2, 3: 3}
n_form = 0
def roof_word(b, cx, cz):
    global n_form
    rp = b.get('rp')
    idx = -1 if rp is None else rp
    form, rise = 0, 0.0
    wid = way_at(cx, cz)
    if wid is not None:
        m = ROOF_LIDAR.get(wid)
        if m and m[0] in (0, 1, 2): form, rise = (4 if m[0] == 0 else m[0]), max(0.0, float(m[2]) - float(m[1]))
        elif wid in ROOF_TAG: form = TAGFORM.get(ROOF_TAG[wid], 0)
    if form: n_form += 1
    v = ((idx + 1) & 0x1FF) | ((form & 7) << 9) | (min(15, max(0, int(round(rise * 2)))) << 12)
    return v - 65536 if v > 32767 else v

# Stacked building:part ways on one footprint (OSM models several towers as a pile of
# coincident prisms of different heights: the Comcast Technology Center has nine) draw
# coplanar walls that z-fight from every angle. Among records whose centroids sit within
# 2.5 m, whose areas agree within 20 % and whose height ranges overlap, only the tallest
# is packed; the shorter ones were hidden inside it anyway.
def dedupe_stacked(items):
    """items: [(cx, cz, area, h, minH, rec)]; returns the kept recs in input order."""
    grid = {}
    for idx, it in enumerate(items):
        grid.setdefault((int(it[0] // 20), int(it[1] // 20)), []).append(idx)
    drop = set()
    for idx, it in enumerate(items):
        if idx in drop: continue
        kx, kz = int(it[0] // 20), int(it[1] // 20)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in grid.get((kx + dx, kz + dz), ()):
                    if j == idx or j in drop: continue
                    q = items[j]
                    if math.hypot(q[0] - it[0], q[1] - it[1]) < 2.5 and min(it[2], q[2]) > 0.8 * max(it[2], q[2]) \
                            and min(it[3], q[3]) - max(it[4], q[4]) > 1.0:
                        drop.add(j if q[3] <= it[3] else idx)
    return [it[5] for idx, it in enumerate(items) if idx not in drop], len(drop)

body = []
recs = []                             # (cx, cz, area, h, minH, (record, wall byte, hint byte)) before the stacked-part dedupe
walls = []                            # one byte per building record, in body order
hints = []                            # and its facade hint byte, 0 without a colour
nb = nr = na = 0
dropped_dup = dropped_outline = 0
for b in d['buildings']:
    poly = b['poly']
    if len(poly) < 3: continue
    cx, cz = cent(poly)
    if touchesCore(poly): dropped_dup += 1; continue
    if partCells and containsPart(poly): dropped_outline += 1; continue
    if not (WIDE[0] <= cx <= WIDE[1] and WIDE[2] <= cz <= WIDE[3]): continue
    if area(poly) < 12: continue
    sp = simplify_budget(simplify(poly, 0.35), 48, 0.7)
    h = max(2.5, min(6500, b['h']))
    _rec = ('building', b.get('name'), b.get('t'), round(cx), round(cz))
    rec = [len(sp), clip(h * 5), 0, BT.get(b.get('t') or 'generic', 0), attr_word(b, h), roof_word(b, cx, cz)]
    for q in sp: rec += [clip(q[0] * 5), clip(q[1] * 5)]
    w = b.get('_wall', -1)
    hb = b.get('_hint', 0)
    recs.append((cx, cz, area(sp), h, 0.0, (rec, w if 0 <= w < 255 else 255, hb if 0 < hb < 16 else 0)))
# 3D-mapped building parts (skyscraper shafts, crowns, podiums) from building:part ways;
# parts of research-flagged glass towers get type 10 (reflective glass material)
glassSpots = []
for res in _research:
    for bb in res.get('buildings', []):
        if bb.get('glass') and bb.get('lat') and bb.get('lon'):
            glassSpots.append(((bb['lon'] - LON0) * KX, (LAT0 - bb['lat']) * KZ))
def isGlass(cx, cz):
    return any(math.hypot(cx - gx, cz - gz) < 75 for gx, gz in glassSpots)
for pt in _parts:
    poly = pt['poly']
    if len(poly) < 3 or area(poly) < 8: continue
    cx, cz = cent(poly)
    if CORE[0] <= cx <= CORE[1] and CORE[2] <= cz <= CORE[3]: continue
    sp = simplify_budget(simplify(poly, 0.3), 48, 0.6)
    _rec = ('part', pt.get('name'), round(cx), round(cz))
    rec = [len(sp), clip(min(6500, pt['h']) * 5), clip(pt['minH'] * 5), 10 if isGlass(cx, cz) else 3, -1, -1]
    for q in sp: rec += [clip(q[0] * 5), clip(q[1] * 5)]
    recs.append((cx, cz, area(sp), float(pt['h']), float(pt['minH']), (rec, 255, 0)))
kept, dropped_stacked = dedupe_stacked(recs)
for rec, wb, hb in kept:
    body += rec
    walls.append(wb)
    hints.append(hb)
    nb += 1
def simplify_open(pts, tol):
    # open-polyline Douglas-Peucker. The old code fed roads through the CLOSED-ring
    # simplify() (appending pts[0], slicing [:-1]) which amputated the real final
    # segment of every road — the model-wide "roads stop mid-block" bug.
    if len(pts) <= 2: return pts
    def dp(seg):
        if len(seg) < 3: return seg
        a, b = seg[0], seg[-1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz) or 1e-9
        best, bi = -1, -1
        for i in range(1, len(seg) - 1):
            p = seg[i]
            dist = abs((p[0] - a[0]) * dz - (p[1] - a[1]) * dx) / L
            if dist > best: best, bi = dist, i
        if best > tol: return dp(seg[:bi + 1])[:-1] + dp(seg[bi:])
        return [a, b]
    return dp(pts)

def runs_of(pts, box, m):
    # split at bbox exits instead of filtering points (a filtered way that leaves and
    # re-enters otherwise grows a phantom straight chord across the excursion)
    inb = lambda q: box[0] - m <= q[0] <= box[1] + m and box[2] - m <= q[1] <= box[3] + m
    runs, cur = [], []
    for i, q in enumerate(pts):
        keep = inb(q) or (i > 0 and inb(pts[i - 1])) or (i + 1 < len(pts) and inb(pts[i + 1]))
        if keep: cur.append(q)
        else:
            if len(cur) > 1: runs.append(cur)
            cur = []
    if len(cur) > 1: runs.append(cur)
    return runs

for r in d['roads']:
    if r['t'] not in RT or len(r['pts']) < 2: continue
    for pts in runs_of(r['pts'], WIDE, 200):
        pts = simplify_open(pts, 0.6) if len(pts) > 3 else pts
        if len(pts) < 2: continue
        _rec = ('road', r.get('name'), r['t'], tuple(round(c) for c in pts[0]))
        body += [len(pts), clip(r['w'] * 10), RT[r['t']]]
        for q in pts: body += [clip(q[0] * 5), clip(q[1] * 5)]
        nr += 1
n_clipped = 0
for a in d['areas']:
    if a['kind'] not in AK or len(a['poly']) < 3: continue
    cx, cz = cent(a['poly'])
    if touchesCore(a['poly']): continue
    if not (WIDE[0] - 500 <= cx <= WIDE[1] + 500 and WIDE[2] - 500 <= cz <= WIDE[3] + 500): continue
    rings = clip_area(a['poly'])
    if rings != [a['poly']]: n_clipped += 1
    for ring in rings:
        sp = simplify_budget(simplify(ring, 0.8), 120, 1.6)
        if len(sp) < 3: continue
        _rec = ('area', a['kind'], round(cx), round(cz))
        body += [len(sp), AK[a['kind']]]
        for q in sp: body += [clip(q[0] * 5), clip(q[1] * 5)]
        na += 1
if SAT:
    print(f'ERROR: {len(SAT)} coordinate(s) saturated int16 (|v| > 32767 at 0.2 m units, i.e. beyond '
          f'+/-{REPR:.0f} m); wide.b64 NOT written. Offending records:', file=sys.stderr, flush=True)
    shown = set()
    for rec, v in SAT:
        if rec in shown: continue
        shown.add(rec)
        print(f'   {rec}  value {v:.0f} ({v / 5:.0f} m)', file=sys.stderr, flush=True)
        if len(shown) >= 12: break
    sys.exit(1)
print(f'roof forms attached: {n_form} of {nb} buildings', flush=True)
buf = struct.pack('<4i', 0x5348545D, nb, nr, na) + struct.pack('<%dh' % len(body), *body)
b64 = base64.b64encode(buf).decode('ascii')
open('wide.b64', 'w').write(b64)
if _walls:
    pal = [tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5)) for hx in _walls[0]]
    walls = [w if w < len(pal) else 255 for w in walls]
    hints = [h if w < 255 else 0 for w, h in zip(walls, hints)]   # no colour, no hint
    assert len(walls) == nb == len(hints), (len(walls), len(hints), nb)
    bpr = 2 if _hinted else 0
    wb = struct.pack('<4i', 0x53485457, nb, len(pal), bpr) + bytes(v for c in pal for v in c) + bytes(walls) \
        + (bytes(hints) if _hinted else b'')
    open('wide_walls.b64', 'w').write(base64.b64encode(wb).decode('ascii'))
    print(f'wall colours: {sum(1 for w in walls if w < 255)} of {nb} buildings from Mapillary block faces'
          + (f', {sum(1 for h in hints if h)} with a facade hint byte' if _hinted else '')
          + f' -> wide_walls.b64 ({len(wb):,} bytes)', flush=True)
print(f'buildings {nb} roads {nr} areas {na} -> {len(buf)/1e6:.2f} MB binary, {len(b64)/1e6:.2f} MB base64; '
      f'dropped {dropped_dup} core-duplicates, {dropped_outline} outlines with 3D parts, {dropped_stacked} stacked parts on one footprint; {n_clipped} area ring(s) clipped to the int16 box')
