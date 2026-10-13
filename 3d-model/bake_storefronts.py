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
Guards: an int16 saturation is fatal (storefronts.b64 is not written). Needs shapely.

Round 189 (Mike: "Do the storefront boxes on Broad Street too"): the page dresses each storefront in a generated
photographic shopfront (bake_storefront_art.py), and what that needs beyond the record rides in a sidecar in the records'
order, storefront_info.json, never in storefronts.b64 (whose bytes stay as they are: the bake re-encodes the blob and
refuses to write anything when it differs from the file on disk, unless --rebake). The sidecar carries each shop's name
(OSM's short name or name, cleaned: no format marks, no em or en dash or middot, at most 40 characters at a word), its trade
family (FAMILIES, the art's trades: the kind and the OSM tags that split it, a takeout from a sit-down restaurant, a bakery
from a grocery), its opening hours where OSM has a string this parses (the weekday's, Saturday's and Sunday's span), and
its place on the wall: records on one wall line are laid side by side (LAYOUT_*: slid apart in the order of their own points
within the union of their own edges, shrunk to no less than 4 m, the last in fetch order dropped when they still do not
fit, never moved more than 30 m), and the drawn wall's outermost and innermost point over the span (the unsimplified ring,
so the panel's ends close onto the wall the page draws), the host's storey height (its OPA storeys) and its height. 8 int16
a record: shift along the tangent (-nz, nx) in dm, the laid width in dm (0 hidden), out and in in cm, the host's storey
height in dm (0 unknown), the family, the hours' index (-1 unknown), and the span's end bits (bit 0 its left end at its
edge's end, bit 1 its right) plus the host's height in dm shifted left by 2. The tags come from fetch_shops.businesses over
the same cached tiles, checked row for row against shops_raw.json."""
import base64, hashlib, json, math, os, re, struct, sys, unicodedata
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
rings, heights, tiers, buildings_fa = [], [], [], []   # Round 189: each host's OPA word (its storeys) for the sidecar
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
        rings.append(poly); heights.append(float(b.get('h') or 0)); tiers.append(tier); buildings_fa.append(b.get('fa'))
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
        return sx, sz, w, L, nx, nz, (bi, level, ei), depth, dist, len(tied) > 1, (x0, z0, ux, uz, L)
    return None


shops = json.load(open(IN))
edgeCount = Counter()
body, rows = [], []
n_nobuilding = n_noedge = n_cap = n_service = n_tie = n_coarse = n_moved = 0
byTier = Counter()
extra = []   # Round 189: per record, the business's index in shops, its host, the edge it hangs on and its own point
for si, s in enumerate(shops):
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
    sx, sz, w, L, nx, nz, ekey, depth, dist, tied, edge = hit
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
    extra.append({'shop': si, 'bi': bi, 'edge': edge, 'px': x, 'pz': z})

if SAT:
    for rec, v in SAT[:12]: print('  SATURATED', rec, round(v, 1))
    sys.exit(f'ERROR: {len(SAT)} int16 saturations; {OUT_B64} not written')
n = len(rows)
blob = struct.pack('<4i', MAGIC, n, 0, 0) + struct.pack('<%dh' % len(body), *body)
b64 = base64.b64encode(blob).decode('ascii')
# Round 189: storefronts.b64 is never re-packed by accident (the house fronts' and the page's records are keyed on its order,
# and the sidecar below rides on it): a bake that would change it writes nothing unless --rebake
if os.path.exists(OUT_B64) and '--rebake' not in sys.argv:
    old = base64.b64decode(open(OUT_B64).read())
    if old != blob:
        on = struct.unpack('<4i', old[:16])[1] if len(old) >= 16 else -1
        oh = struct.unpack('<%dh' % ((len(old) - 16) // 2), old[16:]) if len(old) > 16 else ()
        for i in range(max(n, on)):
            a8, b8 = tuple(oh[i * 8:i * 8 + 8]), tuple(body[i * 8:i * 8 + 8])
            if a8 != b8:
                print(f'record {i}: on disk {a8}, this bake {b8}')
                break
        sys.exit(f'ERROR: this bake would change {OUT_B64} ({on} records on disk, {n} now); nothing written (pass --rebake to replace it)')
open(OUT_B64, 'w').write(b64)
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

# ---------------------------------------------------------------- the sidecar (Round 189)
OUT_INFO = 'storefront_info.json'
# the art's trades (fetch_storefront_art.py FAMILIES, in its order)
FAMILIES = ('retail', 'restaurant', 'takeout', 'cafe', 'bar', 'bank', 'pharmacy', 'grocery', 'bakery', 'boutique', 'salon',
            'venue', 'trade')
TAKEOUT_CUISINE = {'pizza', 'burger', 'chicken', 'sandwich', 'donut', 'bagel', 'kebab', 'cheesesteak', 'fried_chicken',
                   'hot_dog', 'wings', 'chicken_wings', 'fish_and_chips', 'juice', 'bubble_tea', 'falafel'}
BAKERY_SHOP = {'bakery', 'pastry', 'confectionery', 'chocolate', 'cheese', 'tea', 'wine', 'coffee'}
LAYOUT_COS = math.cos(0.05)   # records on one wall line: normals within 0.05 rad,
LAYOUT_OFF = 0.6              # their lines within 0.6 m,
LAYOUT_OVER = -0.05           # and their spans meeting or overlapping (or their edges: see the grouping)
LAYOUT_GAP = 0.2              # what stands between two laid side by side (the record's decimetres round within it)
LAYOUT_MIN = 4.0              # a shrunk one keeps at least this
LAYOUT_MAX_SHIFT = 30.0


def family(kind, t):
    if kind == 1:
        cu = {c.strip() for c in (t.get('cuisine') or '').replace(',', ';').split(';') if c.strip()}
        return 2 if t.get('amenity') == 'fast_food' or (cu & TAKEOUT_CUISINE) else 1
    if kind == 6:
        return 8 if (t.get('shop') or '').split(';')[0].strip() in BAKERY_SHOP else 7
    return {0: 0, 2: 3, 3: 4, 4: 5, 5: 6, 7: 9, 8: 10, 9: 11, 10: 12}[kind]


FORMAT = re.compile('[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]')


def clean_name(t, name):
    s = (t.get('short_name') or name or '').strip()
    s = unicodedata.normalize('NFC', s)
    s = FORMAT.sub('', s)
    s = s.replace('\u2014', ' - ').replace('\u2013', '-').replace('\u00b7', ' ').replace('\u2022', ' ')
    s = re.sub('(,\\s*Inc\\.?|\\s+Inc\\.|\\s+LLC\\.?)$', '', s.strip(), flags=re.I)
    s = re.sub('\\s+', ' ', s).strip()
    if len(s) > 40:
        cut = s[:41].rsplit(' ', 1)[0] if ' ' in s[:41] else s[:40]
        s = cut.rstrip(' ,-&')
    return s


DAYS = ('Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su')


def parse_hours(oh):
    """An OSM opening_hours string as [weekday open, close, Saturday open, close, Sunday open, close] in minutes after
    midnight (a close past midnight runs on past 1440; -1, -1 closed), the weekday taken as Wednesday's; or None when the
    string is beyond this reader (public holidays, months, weeks, comments are ignored or refuse)."""
    if not oh:
        return None
    oh = oh.strip()
    if oh in ('24/7', 'Mo-Su 00:00-24:00', '00:00-24:00'):
        return [0, 1440, 0, 1440, 0, 1440]
    day = [None] * 7   # (open, close) or 'off'
    for rule in re.split('[;|]', oh):
        rule = rule.strip()
        if not rule:
            continue
        if re.search('[A-Z][a-z]{2} ?\\d|week|"|\\[|easter|sunrise|sunset|dawn|dusk|\\+', rule):
            return None
        m = re.match('^((?:(?:Mo|Tu|We|Th|Fr|Sa|Su|PH|SH)(?:-(?:Mo|Tu|We|Th|Fr|Sa|Su))?,?\\s*)*)(.*)$', rule)
        dpart, tpart = m.group(1).strip().rstrip(','), m.group(2).strip()
        ds = set()
        if not dpart:
            ds = set(range(7))
        else:
            for tok in dpart.replace(' ', '').split(','):
                if tok in ('PH', 'SH', ''):
                    continue
                if '-' in tok:
                    a, b = tok.split('-')
                    i, j = DAYS.index(a), DAYS.index(b)
                    k = i
                    while True:
                        ds.add(k)
                        if k == j:
                            break
                        k = (k + 1) % 7
                else:
                    ds.add(DAYS.index(tok))
            if not ds:
                continue
        if tpart in ('off', 'closed'):
            for d in ds:
                day[d] = 'off'
            continue
        spans = []
        for rng in tpart.split(','):
            rng = rng.strip()
            mm = re.match('^(\\d{1,2}):(\\d{2})\\s*-\\s*(\\d{1,2}):(\\d{2})\\+?$', rng)
            if not mm:
                return None
            o = int(mm.group(1)) * 60 + int(mm.group(2)); c = int(mm.group(3)) * 60 + int(mm.group(4))
            if c <= o:
                c += 1440
            spans.append((o, min(c, 2047)))
        if not spans:
            return None
        o, c = min(q[0] for q in spans), max(q[1] for q in spans)
        for d in ds:
            day[d] = (o, c)
    if all(d is None for d in day):
        return None
    out = []
    for d in (2, 5, 6):
        v = day[d]
        if v is None or v == 'off':
            out += [-1, -1]
        else:
            out += [v[0], v[1]]
    return out


def ray_hits(pg, px, pz, nx, nz, reach=3.0):
    """The offsets along n at which the ray from (p + n reach) to (p - n reach) meets the ring (pg's exterior)."""
    seg = LineString([(px + nx * reach, pz + nz * reach), (px - nx * reach, pz - nz * reach)])
    try:
        hit = pg.exterior.intersection(seg)
    except Exception:
        return []
    pts = []
    for g in getattr(hit, 'geoms', [hit]):
        if g.is_empty:
            continue
        for q in (g.coords if g.geom_type in ('Point', 'LineString') else []):
            pts.append((q[0] - px) * nx + (q[1] - pz) * nz)
    return pts


import fetch_shops
biz, _ = fetch_shops.businesses(fetch_shops.load_elements())
if len(biz) != len(shops) or any(abs(b['x'] - s['x']) > 1e-6 or abs(b['z'] - s['z']) > 1e-6 or b['kind'] != s['kind'] or b['name'] != (s.get('name') or '')
                                 for b, s in zip(biz, shops)):
    sys.exit(f'ERROR: the cached tiles give {len(biz)} businesses that do not match {IN} row for row; {OUT_INFO} not written')

names, hours, hourIx, fams = [], [], {}, []
n_named = n_hours = n_hours_str = 0
for r, e in zip(rows, extra):
    t = biz[e['shop']]['tags']
    nm = clean_name(t, r['name'])
    names.append(nm)
    n_named += bool(nm)
    fams.append(family(r['kind'], t))
    hrs = parse_hours(t.get('opening_hours'))
    n_hours_str += bool(t.get('opening_hours'))
    if hrs is None:
        e['hours'] = -1
    else:
        key = tuple(hrs)
        if key not in hourIx:
            hourIx[key] = len(hours); hours.append(hrs)
        e['hours'] = hourIx[key]
        n_hours += 1

# the layout: records on one wall line laid side by side
# (every position as the page decodes it: the record's 0.2 m units, so what is laid apart here stays apart there)
for r in rows:
    r['x'], r['z'] = round(r['x'] / S) * S, round(r['z'] / S) * S
for i, (r, e) in enumerate(zip(rows, extra)):
    nx, nz = math.cos(r['angle']), math.sin(r['angle'])
    e['n'] = (nx, nz); e['t'] = (-nz, nx)
    e['c'] = r['x'] * e['t'][0] + r['z'] * e['t'][1]       # the centre along the tangent
    e['d'] = r['x'] * nx + r['z'] * nz                      # the line's offset along the normal
    e['w'] = r['width']
    x0, z0, ux, uz, L = e['edge']
    a = x0 * e['t'][0] + z0 * e['t'][1]; b = (x0 + ux * L) * e['t'][0] + (z0 + uz * L) * e['t'][1]
    e['lim'] = (min(a, b), max(a, b))
    e['p'] = e['px'] * e['t'][0] + e['pz'] * e['t'][1]       # the business's own point along the tangent
    e['shift'] = 0.0; e['keep'] = True
cells = {}
for i, e in enumerate(extra):
    cells.setdefault((int(rows[i]['x'] // 40), int(rows[i]['z'] // 40)), []).append(i)
parent = list(range(len(rows)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
for i, e in enumerate(extra):
    gx, gz = int(rows[i]['x'] // 40), int(rows[i]['z'] // 40)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            for j in cells.get((gx + dx, gz + dz), ()):
                if j <= i:
                    continue
                f = extra[j]
                if e['n'][0] * f['n'][0] + e['n'][1] * f['n'][1] < LAYOUT_COS:
                    continue
                dj = rows[j]['x'] * e['n'][0] + rows[j]['z'] * e['n'][1]
                if abs(dj - e['d']) > LAYOUT_OFF:
                    continue
                cj = rows[j]['x'] * e['t'][0] + rows[j]['z'] * e['t'][1]
                over = min(e['c'] + e['w'] / 2, cj + f['w'] / 2) - max(e['c'] - e['w'] / 2, cj - f['w'] / 2)
                # and two on one stretch of wall (their edges overlap along it): sliding one apart from a third must not
                # push it into the second (the review: a pair laid apart ran into the shop beside them)
                a0, a1 = e['lim']; fx0, fz0, fux, fuz, fL = f['edge']
                b0 = fx0 * e['t'][0] + fz0 * e['t'][1]; b1 = (fx0 + fux * fL) * e['t'][0] + (fz0 + fuz * fL) * e['t'][1]
                if over > LAYOUT_OVER or min(a1, max(b0, b1)) - max(a0, min(b0, b1)) > 0.0:
                    parent[find(i)] = find(j)
groups = {}
for i in range(len(rows)):
    groups.setdefault(find(i), []).append(i)
n_groups = n_moved = n_shrunk = n_dropped = 0
for g in groups.values():
    if len(g) < 2:
        continue
    n_groups += 1
    e0 = extra[g[0]]
    T = e0['t']
    ctr = {i: rows[i]['x'] * T[0] + rows[i]['z'] * T[1] for i in g}
    pt = {i: extra[i]['px'] * T[0] + extra[i]['pz'] * T[1] for i in g}
    lims = []
    for i in g:
        x0, z0, ux, uz, L = extra[i]['edge']
        a = x0 * T[0] + z0 * T[1]; b = (x0 + ux * L) * T[0] + (z0 + uz * L) * T[1]
        lims.append((min(a, b), max(a, b)))
    A, B = min(q[0] for q in lims), max(q[1] for q in lims)
    live = sorted(g, key=lambda i: (pt[i], i))
    width = {i: rows[i]['width'] for i in g}
    while True:
        need = sum(width[i] for i in live) + LAYOUT_GAP * (len(live) - 1)
        if need <= B - A + 1e-6:
            break
        k = (B - A - LAYOUT_GAP * (len(live) - 1)) / sum(rows[i]['width'] for i in live)
        for i in live:
            width[i] = max(LAYOUT_MIN, rows[i]['width'] * k)
        if sum(width[i] for i in live) + LAYOUT_GAP * (len(live) - 1) <= B - A + 1e-6:
            break
        last = max(live, key=lambda i: extra[i]['shop'])   # the last in fetch order goes
        live.remove(last); extra[last]['keep'] = False; n_dropped += 1
        for i in live:
            width[i] = rows[i]['width']
        if len(live) < 2:
            break
    # minimal moves: forward then backward, each inside [A, B]
    pos = {}
    end = A
    for i in live:
        c = max(ctr[i], end + width[i] / 2, A + width[i] / 2)
        pos[i] = c; end = c + width[i] / 2 + LAYOUT_GAP
    start = B
    for i in reversed(live):
        c = min(pos[i], start - width[i] / 2)
        pos[i] = c; start = c - width[i] / 2 - LAYOUT_GAP
    for i in live:
        sh = pos[i] - ctr[i]
        if abs(sh) > LAYOUT_MAX_SHIFT:
            extra[i]['keep'] = False; n_dropped += 1; continue
        if abs(sh) > 0.05:
            n_moved += 1
        if width[i] < rows[i]['width'] - 0.05:
            n_shrunk += 1
        # the shift in the record's own tangent (the group's within 0.05 rad of it)
        extra[i]['shift'] = sh * (T[0] * extra[i]['t'][0] + T[1] * extra[i]['t'][1])
        extra[i]['w'] = width[i]

# the drawn wall over each span, the host's storeys and height
out_cm, in_cm = [], []
rec = []
for i, (r, e) in enumerate(zip(rows, extra)):
    nx, nz = e['n']; tx, tz = e['t']
    w = e['w'] if e['keep'] else 0.0
    cx, cz = r['x'] + tx * e['shift'], r['z'] + tz * e['shift']
    pg = polys[e['bi']]
    hi, lo = None, None
    if w > 0 and not pg.is_empty and pg.geom_type == 'Polygon':
        k = max(2, int(w / 0.25))
        for j in range(k + 1):
            s_ = -w / 2 + w * j / k
            hits = ray_hits(pg, cx + tx * s_, cz + tz * s_, nx, nz)
            if not hits:
                continue
            f = max(hits)   # the wall's face seen from the street
            hi = f if hi is None else max(hi, f); lo = f if lo is None else min(lo, f)
    o = 0 if hi is None else max(-120, min(120, int(round(hi * 100))))
    n_ = 0 if lo is None else max(-120, min(120, int(round(lo * 100))))
    if w > 0:
        out_cm.append(o); in_cm.append(n_)
    b = buildings_fa[e['bi']]
    h = heights[e['bi']]
    fp = 0
    if b and b[3] and h:
        rr = h / b[3]
        if 2.2 <= rr <= 5.2:
            fq = min(25, max(1, int(round((min(rr, 4.6) - 2.2) / 0.1)) + 1))
            fp = int(round((2.2 + (fq - 1) * 0.1) * 10))
    x0, z0, ux, uz, L = e['edge']
    a = x0 * tx + z0 * tz; bb = (x0 + ux * L) * tx + (z0 + uz * L) * tz
    c0 = cx * tx + cz * tz
    ends = (1 if abs((c0 - w / 2) - min(a, bb)) < 0.3 else 0) | (2 if abs(max(a, bb) - (c0 + w / 2)) < 0.3 else 0)
    hdm = max(0, min(8000, int(round(h * 10))))
    rec += [int(round(e['shift'] * 10)), int(math.floor(w * 10 + 1e-6)), o, n_, fp, fams[i], e['hours'], ends | (hdm << 2)]
for v in rec:
    if v > 32767 or v < -32768:
        sys.exit(f'ERROR: {OUT_INFO}: a value {v} does not fit an int16; nothing written')
info = {'v': 1, 'n': n, 'b64sha': hashlib.sha256(b64.encode('ascii')).hexdigest(), 'families': list(FAMILIES), 'names': names,
        'rec': base64.b64encode(struct.pack('<%dh' % len(rec), *rec)).decode('ascii'), 'hours': hours,
        'stats': {'groups': n_groups, 'moved': n_moved, 'shrunk': n_shrunk, 'dropped': n_dropped, 'named': n_named,
                  'hoursParsed': n_hours, 'hoursStrings': n_hours_str, 'families': dict(Counter(FAMILIES[f] for f in fams))}}
json.dump(info, open(OUT_INFO, 'w'), separators=(',', ':'), ensure_ascii=False)
pc = lambda a, q: sorted(a)[min(len(a) - 1, int(q * len(a)))] if a else 0
print(f'{OUT_INFO}: {os.path.getsize(OUT_INFO):,} bytes; layout: {n_groups} groups, {n_moved} moved, {n_shrunk} shrunk, '
      f'{n_dropped} dropped; {n_named} named; hours parsed for {n_hours} of {n_hours_str} strings; wall out cm p50/p95 '
      f'{pc(out_cm, 0.5)}/{pc(out_cm, 0.95)}, in p5/p50 {pc(in_cm, 0.05)}/{pc(in_cm, 0.5)}', flush=True)
print('families: ' + ', '.join(f'{k}:{v}' for k, v in sorted(info['stats']['families'].items())), flush=True)
