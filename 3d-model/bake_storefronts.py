#!/usr/bin/env python3
"""lidar_cache/shops_raw.json (fetch_shops.py) + the scene extracts -> storefronts.b64: one
storefront per ground-floor business, hung on the street-facing wall of the footprint it
stands in. storefronts.b64 is a derivative database of OpenStreetMap data (ODbL): see
../DATA-LICENSE.md. storefronts.json carries the same rows in plain units for inspection
(it does not ship).

Footprints are what the app actually draws: every scene.json building, plus scene_wide.json
and scene_south.json buildings the way pack_wide.py packs them (a wide or south footprint
touching the core box CORE is the core's duplicate and is skipped, the south set is
deduplicated against the wide set by its first three vertices, and anything outside the
WIDE box or under 12 m2 is not in wide.b64). Roads come from all three files; a storefront
faces a street (trunk, primary, secondary, tertiary, residential, living street,
unclassified, pedestrian, and their links), and only when no wall faces a street does a
service road (a strip mall's parking aisle) count. Expressways, footways, steps and
cycleways never do.

Per business: the nearest footprint within 30 m (distance 0 when the point is inside), or
the next nearest that has a facade at all (a theatre's mapped centre lands in the
auditorium block behind its own lobby building). Its ring is simplified first: rowhouse
fronts in the extracts are often chopped into 1-2 m jogs, and without this a 4.6 m front is
three edges too short to count while the party wall beside it wins. SIMPLIFY lists the
tolerances tried in turn (0.5 m, then 1.2 m for the fronts that are still jagged), so a
storefront sits at most that far from the drawn wall. A wall qualifies as a facade when it
is at least MIN_EDGE long and a road centreline lies within NEAR_ROAD of its midpoint IN
FRONT of it: the vector from the midpoint to the nearest point of the road makes less than
60 degrees with the outward normal, and the straight line between them crosses no other
footprint (a party wall "faces" the street beyond the neighbours; a wall on an alley does
not face the avenue across the block). Candidate roads compete on sidewalk depth, the
centreline distance less half the road's width, so a 4 m alley 3 m behind a shop and a 13 m
avenue 8 m in front of it are judged by the same yardstick; when two walls tie within TIE
metres (a corner building on two streets) the wall nearer the business point wins, since a
mapped shop node usually sits at its door. The storefront sits at the business point's
projection onto that edge, clamped so the whole width stays on the edge; width =
min(edge - 1, 12), never under 4. The line of sight is checked again from that spot (a long
wall can be clear at its midpoint and hidden behind an annex where the shop is), and a
blocked spot falls through to the next wall. One storefront per 4 m of edge (the first
ones in fetch order keep their place).

Record (8 x int16 after an Int32[4] header: magic 0x53485446 'SHTF', n, 0, 0):
  x/0.2, z/0.2, atan2(nz, nx)*1000 (outward normal, radians), width*10, kind,
  colour 0..15 (a sha1 of the name, so a shop keeps its colour across rebuilds),
  ground-floor height*10 (4.2 m, 3.6 m when the building is under 8 m),
  flags: bit0 awning (kinds 1 2 3 6 7 8), bit1 sign (all), bit2 full-glass front
  (all but 4 5 9, which get a half-glass front).
Guards: an int16 saturation is fatal (storefronts.b64 is not written). Needs shapely."""
import base64, hashlib, json, math, os, struct, sys
from collections import Counter
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.strtree import STRtree

MAGIC = 0x53485446
S = 0.2
CORE = (-640, 770, -520, 850)        # pack_wide.py CORE: wide/south footprints touching it are dropped there
WIDE = (-3700, 2300, -4480, 6400)    # pack_wide.py WIDE: footprints outside it are not in wide.b64
NEAR_BUILDING = 30.0
NEAR_ROAD = 35.0
SIMPLIFY = (0.5, 1.2)                # ring simplification tolerances tried in turn (max deviation from the drawn wall)
MIN_EDGE = 3.0
FACING_COS = 0.5                     # cos 60 degrees: the road must be in front of the wall, not off its end
TIE = 1.5                            # walls within this much sidewalk depth of the best are a tie
CAP_PITCH = 4.0                      # one storefront per this much edge
STREET = {'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link',
          'residential', 'living_street', 'unclassified', 'pedestrian'}
SERVICE = {'service'}
AWNING = {1, 2, 3, 6, 7, 8}
HALF_GLASS = {4, 5, 9}
IN = 'lidar_cache/shops_raw.json'
OUT_B64, OUT_JSON = 'storefronts.b64', 'storefronts.json'


def touchesCore(poly, m=2):
    return any(CORE[0] - m <= q[0] <= CORE[1] + m and CORE[2] - m <= q[1] <= CORE[3] + m for q in poly)


def cent(poly):
    return sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly)


def area2(poly):
    """Twice the signed shoelace area in the (x, z) frame: positive when the ring runs
    counter-clockwise with x right and z up, which fixes which side is outward."""
    a = 0.0
    for i in range(len(poly)):
        x0, z0 = poly[i]; x1, z1 = poly[(i + 1) % len(poly)]
        a += x0 * z1 - x1 * z0
    return a


# ---- footprints: the drawn set
rings, heights, tiers = [], [], []
seenB = set()
n_core_dup = n_outside = 0
for path, tier in (('scene.json', 'core'), ('scene_wide.json', 'wide'), ('scene_south.json', 'south')):
    d = json.load(open(path))
    for b in d['buildings']:
        poly = [tuple(q) for q in b['poly']]
        if len(poly) >= 2 and poly[0] == poly[-1]: poly = poly[:-1]
        if len(poly) < 3: continue
        if tier != 'core':
            if touchesCore(poly): n_core_dup += 1; continue
            cx, cz = cent(poly)
            if not (WIDE[0] <= cx <= WIDE[1] and WIDE[2] <= cz <= WIDE[3]): n_outside += 1; continue
            if abs(area2(poly)) / 2 < 12: continue
            key = tuple(poly[:3])
            if key in seenB: continue
            seenB.add(key)
        rings.append(poly); heights.append(float(b.get('h') or 0)); tiers.append(tier)
polys = []
for ring in rings:
    try:
        pg = Polygon(ring)
        if not pg.is_valid: pg = pg.buffer(0)
    except Exception:
        pg = Polygon()
    polys.append(pg)
bTree = STRtree(polys)
print(f'footprints: {len(rings)} ({n_core_dup} wide/south core duplicates and {n_outside} outside the wide box skipped)', flush=True)

# ---- roads: streets first, service roads as the fallback
roadLines, roadGroup, roadHalf = [], [], []
for path in ('scene.json', 'scene_wide.json', 'scene_south.json'):
    for r in json.load(open(path))['roads']:
        t = r.get('t')
        if t in STREET: g = 0
        elif t in SERVICE: g = 1
        else: continue
        pts = [tuple(q) for q in r['pts']]
        if len(pts) < 2: continue
        try: line = LineString(pts)
        except Exception: continue
        if line.length < 1: continue
        roadLines.append(line); roadGroup.append(g); roadHalf.append(float(r.get('w') or 7) / 2)
rTree = STRtree(roadLines)
print(f'roads: {roadGroup.count(0)} streets, {roadGroup.count(1)} service roads', flush=True)


def wall_ring(bi, tol):
    """The footprint's ring with the jogs under `tol` metres ironed out, same winding."""
    pg = polys[bi]
    if pg.is_empty or pg.geom_type != 'Polygon': return rings[bi]
    sp = pg.simplify(tol, preserve_topology=True)
    if sp.is_empty or sp.geom_type != 'Polygon' or len(sp.exterior.coords) < 4: return rings[bi]
    return list(sp.exterior.coords)[:-1]


_dupOf = {}
def is_duplicate(bi, bj):
    """A second footprint over the same ground (an OSM outline drawn twice) is not a blocker."""
    key = (bi, bj)
    if key not in _dupOf:
        try:
            inter = polys[bi].intersection(polys[bj]).area
            _dupOf[key] = inter > 0.5 * min(polys[bi].area, polys[bj].area)
        except Exception:
            _dupOf[key] = False
    return _dupOf[key]


def clear_line(bi, mx, mz, nx, nz, qx, qz):
    """No other footprint stands between the wall (0.3 m proud of it) and the road."""
    seg = LineString([(mx + nx * 0.3, mz + nz * 0.3), (qx, qz)])
    for j in bTree.query(seg):
        j = int(j)
        if j == bi or polys[j].is_empty: continue
        if polys[j].intersects(seg) and not is_duplicate(bi, j): return False
    return True


# ---- the facades of a footprint: every wall with a road in front of it, memoised per
# (footprint, simplification, whether service roads count). Each entry: (sidewalk depth,
# centreline distance, edge index, edge start, unit direction, length, outward normal, road)
_facades = {}
def facades(bi, tol, allow_service):
    key = (bi, tol, allow_service)
    if key in _facades: return _facades[key]
    ring = wall_ring(bi, tol); n = len(ring)
    sign = 1.0 if area2(ring) > 0 else -1.0
    out = []
    for i in range(n):
        x0, z0 = ring[i]; x1, z1 = ring[(i + 1) % n]
        dx, dz = x1 - x0, z1 - z0
        L = math.hypot(dx, dz)
        if L < MIN_EDGE: continue
        nx, nz = dz / L * sign, -dx / L * sign
        mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
        pt = Point(mx, mz)
        best = None
        for ri in rTree.query(sbox(mx - NEAR_ROAD, mz - NEAR_ROAD, mx + NEAR_ROAD, mz + NEAR_ROAD)):
            ri = int(ri)
            if roadGroup[ri] == 1 and not allow_service: continue
            line = roadLines[ri]
            dist = line.distance(pt)
            if dist > NEAR_ROAD: continue
            depth = max(0.0, dist - roadHalf[ri])
            if best is not None and depth >= best[0]: continue
            q = line.interpolate(line.project(pt))
            if dist > 0.5 and ((q.x - mx) * nx + (q.y - mz) * nz) / dist < FACING_COS: continue
            if not clear_line(bi, mx, mz, nx, nz, q.x, q.y): continue
            best = (depth, dist, ri)
        if best is not None:
            out.append((best[0], best[1], i, (x0, z0), (dx / L, dz / L), L, (nx, nz), best[2]))
    _facades[key] = out
    return out


def seg_dist(px, pz, x0, z0, ux, uz, L):
    t = max(0.0, min(L, (px - x0) * ux + (pz - z0) * uz))
    return math.hypot(px - (x0 + ux * t), pz - (z0 + uz * t))


SAT = []
_rec = None
def clip(v):
    r = int(round(v))
    if r > 32767 or r < -32767:
        SAT.append((_rec, v))
        return max(-32767, min(32767, r))
    return r


def colour(name, kind, x, z):
    key = name.strip() if name and name.strip() else f'{kind}@{round(x)},{round(z)}'
    return int(hashlib.sha1(key.encode('utf-8')).hexdigest()[:2], 16) & 15


LADDER = [(tol, svc) for svc in (False, True) for tol in SIMPLIFY]   # streets at every tolerance before any service road


def place(x, z, bi, tol, svc, level):
    """The storefront for business (x, z) on footprint bi at one ladder step, or None:
    (sx, sz, width, edge length, nx, nz, edge key, depth, dist, tied)."""
    cands = facades(bi, tol, svc)
    if not cands: return None
    top = min(c[0] for c in cands)
    tied = [c for c in cands if c[0] <= top + TIE]
    order = sorted(tied, key=lambda c: seg_dist(x, z, c[3][0], c[3][1], c[4][0], c[4][1], c[5])) + \
            sorted((c for c in cands if c[0] > top + TIE), key=lambda c: c[0])
    for depth, dist, ei, (x0, z0), (ux, uz), L, (nx, nz), ri in order:
        w = max(4.0, min(L - 1.0, 12.0))
        t = (x - x0) * ux + (z - z0) * uz
        lo, hi = min(w / 2, L / 2), max(L - w / 2, L / 2)
        t = max(lo, min(hi, t))
        sx, sz = x0 + ux * t, z0 + uz * t
        line = roadLines[ri]; sp = Point(sx, sz)
        q = line.interpolate(line.project(sp))
        if not clear_line(bi, sx, sz, nx, nz, q.x, q.y): continue
        return sx, sz, w, L, nx, nz, (bi, level, ei), depth, dist, len(tied) > 1
    return None


shops = json.load(open(IN))
edgeCount = Counter()
body, rows = [], []
n_nobuilding = n_noedge = n_cap = n_service = n_tie = n_coarse = n_moved = 0
byTier = Counter()
for s in shops:
    x, z, kind, name = s['x'], s['z'], int(s['kind']), s.get('name') or ''
    pt = Point(x, z)
    near = []
    for i in bTree.query(sbox(x - NEAR_BUILDING, z - NEAR_BUILDING, x + NEAR_BUILDING, z + NEAR_BUILDING)):
        if polys[i].is_empty: continue
        d = polys[i].distance(pt)
        if d < NEAR_BUILDING: near.append((d, int(i)))
    if not near: n_nobuilding += 1; continue
    near.sort()
    hit = None
    for rank, (bd, bi) in enumerate(near):
        for level, (tol, svc) in enumerate(LADDER):
            hit = place(x, z, bi, tol, svc, level)
            if hit: break
        if hit: break
    if hit is None: n_noedge += 1; continue
    sx, sz, w, L, nx, nz, ekey, depth, dist, tied = hit
    if svc: n_service += 1
    if tol != SIMPLIFY[0]: n_coarse += 1
    if rank: n_moved += 1
    if tied: n_tie += 1
    cap = max(1, int(L // CAP_PITCH))
    if edgeCount[ekey] >= cap: n_cap += 1; continue
    edgeCount[ekey] += 1
    ang = math.atan2(nz, nx)
    fh = 3.6 if heights[bi] < 8 else 4.2
    flags = (1 if kind in AWNING else 0) | 2 | (0 if kind in HALF_GLASS else 4)
    col = colour(name, kind, x, z)
    _rec = ('storefront', name, kind, round(sx), round(sz))
    body += [clip(sx / S), clip(sz / S), clip(ang * 1000), clip(w * 10), kind, col, clip(fh * 10), flags]
    rows.append({'x': round(sx, 2), 'z': round(sz, 2), 'angle': round(ang, 4), 'width': round(w, 1), 'kind': kind,
                 'colour': col, 'floorH': fh, 'flags': flags, 'name': name, 'tier': tiers[bi],
                 'roadDist': round(dist, 1), 'depth': round(depth, 1), 'simplify': tol})
    byTier[tiers[bi]] += 1

if SAT:
    for rec, v in SAT[:12]: print('  SATURATED', rec, round(v, 1))
    sys.exit(f'ERROR: {len(SAT)} int16 saturations; {OUT_B64} not written')
n = len(rows)
blob = struct.pack('<4i', MAGIC, n, 0, 0) + struct.pack('<%dh' % len(body), *body)
open(OUT_B64, 'w').write(base64.b64encode(blob).decode('ascii'))
json.dump(rows, open(OUT_JSON, 'w'), separators=(',', ':'), ensure_ascii=False)
kinds = Counter(r['kind'] for r in rows)
print(f'businesses: {len(shops)} fetched, {n} assigned ({n_service} on a service road, {n_coarse} on a wall read at the '
      f'{SIMPLIFY[1]} m simplification, {n_moved} on a footprint other than the nearest, {n_tie} settled by the business '
      f'point between tied walls), {n_nobuilding} dropped for no building within {NEAR_BUILDING:.0f} m, '
      f'{n_noedge} for no facing edge, {n_cap} by the per-edge cap', flush=True)
print('by tier: ' + ', '.join(f'{k}:{byTier[k]}' for k in ('core', 'wide', 'south')) +
      '; by kind: ' + ', '.join(f'{k}:{kinds[k]}' for k in sorted(kinds)), flush=True)
print(f'{OUT_B64}: {len(blob):,} bytes binary, {os.path.getsize(OUT_B64):,} base64 ({n} storefronts); '
      f'{OUT_JSON}: {os.path.getsize(OUT_JSON):,} bytes', flush=True)
