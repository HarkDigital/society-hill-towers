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
fit, never moved more than 30 m), then each span measured on the walls the page DRAWS (the core's scene.json rings and
wide.b64's records decoded, so this reads wide.b64 too): kept where the wall is there, in view and flush, turned to the
wall's own lean, narrowed or slid within its room, hidden under 3.4 m of such wall or inside a shop=mall (the review: see
'the span on the wall the page draws' below; --debug i,j prints the profiles); the drawn wall's outermost and innermost
point over the span, the host's storey height (its OPA storeys) and its height. 9 int16 a record (v 2, 'stride'): shift
along the tangent (-nz, nx) in dm, the laid width in dm (0 hidden), out and in in cm, the host's storey height in dm (0
unknown), the family, the hours' index (-1 unknown), the span's end bits (bit 0 its left end at its edge's end, bit 1 its
right) plus the host's height in dm shifted left by 2, and the panel's turn to its wall (the lean, a slope in
ten-thousandths). The tags come from fetch_shops.businesses over the same cached tiles, checked row for row against
shops_raw.json."""
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
# the third review (Hajimaru Ramen, Hibachi 2 Go, Oriental Chinese Restaurant all showed one white-tablecloth dining
# room): the counters' cuisines, a name that says it is a takeout, OSM's takeaway=only, and a Chinese restaurant outside
# Center City (the neighbourhoods' corner takeouts; Chinatown's and Center City's are dining rooms) take the takeout's
# counter and stools
COUNTER_CUISINE = {'noodle', 'ramen', 'noodles', 'poke', 'dumpling', 'dumplings'}
TAKEOUT_NAME = re.compile(r"(?:\b(?:2|to)\s?go\b|\btake\s?-?\s?out\b|\bexpress\b|\bcarry\s?-?\s?out\b)", re.I)
CENTER_CITY = (-3400, 400, -1450, 470)   # x0, x1, z0, z1: the Schuylkill to the Delaware, Vine (and Callowhill) to South
LAYOUT_COS = math.cos(0.05)   # records on one wall line: normals within 0.05 rad,
LAYOUT_OFF = 0.6              # their lines within 0.6 m,
LAYOUT_OVER = -0.05           # and their spans meeting or overlapping (or their edges: see the grouping)
LAYOUT_GAP = 0.2              # what stands between two laid side by side (the record's decimetres round within it)
LAYOUT_MIN = 4.0              # a shrunk one keeps at least this
LAYOUT_MAX_SHIFT = 30.0


def family(kind, t, x=0.0, z=0.0, name=''):
    if kind == 1:
        cu = {c.strip() for c in (t.get('cuisine') or '').replace(',', ';').split(';') if c.strip()}
        cc = CENTER_CITY[0] <= x <= CENTER_CITY[1] and CENTER_CITY[2] <= z <= CENTER_CITY[3]
        take = (t.get('amenity') == 'fast_food' or (cu & TAKEOUT_CUISINE) or (cu & COUNTER_CUISINE) or t.get('takeaway') == 'only'
                or bool(TAKEOUT_NAME.search(name or '')) or ('chinese' in cu and not cc))
        return 2 if take else 1
    if kind == 6:
        return 8 if (t.get('shop') or '').split(';')[0].strip() in BAKERY_SHOP else 7
    return {0: 0, 2: 3, 3: 4, 4: 5, 5: 6, 7: 9, 8: 10, 9: 11, 10: 12}[kind]


FORMAT = re.compile('[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]')


def clean_name(t, name):
    s = (t.get('short_name') or name or '').strip()
    s = unicodedata.normalize('NFC', s)
    s = FORMAT.sub('', s)
    s = s.replace('\u2014', ' - ').replace('\u2013', '-').replace('\u00b7', ' ').replace('\u2022', ' ')
    s = re.sub('\\s+', ' ', CORP.sub('', s.strip())).strip()
    if len(s) > NAME_MAX:
        s = CORP.sub('', cut_name(s)).strip()
    return s


CORP = re.compile('(,\\s*Inc\\.?|\\s+Inc\\.|\\s+LLC\\.?)$', re.I)


NAME_MAX = 40
# what a name may be cut at, best first (the third review: cut at 40 characters and stripped of ' ,-&' only, the sidecar
# carried 'Greater Philadelphia Health Action Inc.:' and "Francoluigi's Italian Restaurant & High"): its head before a
# separator ('Blue Bird Distilling - Center City Tasting Room'), before an '&' or 'and' joining two names, after a word that
# ends a business's name ('Philadelphia Brewing Company Peacock Room Bar & Garden'), before a connector ('Weitzman National
# Museum of American Jewish History Museum Store'), else at the last word that fits; and then never a connector or a
# separator left dangling at its end
NAME_SEP = re.compile(r'\s+(?:-{1,2}|\||/)\s+|:\s+|\s+@\s+|\s+at\s+')
NAME_JOIN = re.compile(r'\s+(?:&|and|\+)\s+', re.I)
NAME_END = {'company', 'co.', 'restaurant', 'cafe', 'café', 'bar', 'shop', 'store', 'market', 'center', 'centre', 'museum',
            'pharmacy', 'clinic', 'bakery', 'pizza', 'pizzeria', 'grill', 'kitchen', 'studio', 'salon', 'spa', 'library',
            'gallery', 'hall', 'house', 'brewery', 'distilling', 'theatre', 'theater', 'college', 'emporium', 'parlor',
            'deli', 'diner', 'tavern', 'pub', 'lounge', 'barbershop', 'boutique', 'supply', 'hardware'}
NAME_TAIL = re.compile(r'(?:\s+(?:&|\+|and|n|of|the|at|on|for|by|with|in|de|la|y)|\s*[,;:/&+|@\-])\s*$', re.I)


def trim_tail(s):
    while True:
        t = NAME_TAIL.sub('', s).rstrip()
        if t == s or not t:
            return s
        s = t


def cut_name(s):
    for m in NAME_SEP.finditer(s):
        head = trim_tail(s[:m.start()])
        if 6 <= len(head) <= NAME_MAX:
            return head
    for m in NAME_JOIN.finditer(s):
        head = trim_tail(s[:m.start()])
        if 12 <= len(head) <= NAME_MAX:
            return head
    words = s.split(' ')
    heads = [' '.join(words[:k]) for k in range(1, len(words)) if len(' '.join(words[:k])) <= NAME_MAX]
    for h in reversed(heads):
        if len(h) >= 12 and h.split(' ')[-1].lower() in NAME_END:
            return trim_tail(h)
    for k in range(len(heads), 0, -1):
        nxt = words[k].lower() if k < len(words) else ''
        if nxt in ('of', 'for', 'at', 'in', 'on', 'and', '&', 'with', 'by') and len(heads[k - 1]) >= 16:
            return trim_tail(heads[k - 1])
    return trim_tail(heads[-1]) if heads else s[:NAME_MAX].rstrip()


DAYS = ('Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su')


def parse_hours(oh):
    """An OSM opening_hours string as [weekday open, close, Saturday open, close, Sunday open, close, weekdays shut] in
    minutes after midnight (a close past midnight runs on past 1440; -1, -1 closed), or None when the string is beyond this
    reader (public holidays, months, weeks, comments are ignored or refuse). A day's two spans are its first opening to its
    last close. The weekday's span is the one most of Monday to Friday keep (Wednesday's on a tie), and the seventh value
    has a bit for each weekday the shop is shut, Monday the first (the third review: 'Tu-Su 17:00-24:00' opened on
    Mondays); a day OSM does not name is shut. The limit that stays: the page keeps one weekday span, so a weekday open on
    another span than the rest keeps theirs ('Mo-We 11:00-21:00; Th-Fr 11:00-23:00' closes at 21:00 all week)."""
    if not oh:
        return None
    oh = oh.strip()
    if oh in ('24/7', 'Mo-Su 00:00-24:00', '00:00-24:00'):
        return [0, 1440, 0, 1440, 0, 1440, 0]
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
    wk = day[:5]
    cnt = {}
    for v in wk:
        if v is not None and v != 'off':
            cnt[v] = cnt.get(v, 0) + 1
    if cnt:
        best = max(cnt.values())
        span = wk[2] if cnt.get(wk[2]) == best else next(v for v in wk if cnt.get(v) == best)
        out, shut = [span[0], span[1]], sum(1 << d for d in range(5) if wk[d] is None or wk[d] == 'off')
    else:
        out, shut = [-1, -1], 0
    for d in (5, 6):
        v = day[d]
        if v is None or v == 'off':
            out += [-1, -1]
        else:
            out += [v[0], v[1]]
    return out + [shut]


import fetch_shops
ELEMENTS = fetch_shops.load_elements()
biz, _ = fetch_shops.businesses(ELEMENTS)
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
    fams.append(family(r['kind'], t, r['x'], r['z'], nm))
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

# ---- the span on the wall the page draws (the review): the layout above works on the simplified edges, and the drawn
# wall is the unsimplified ring, with its corners, its jogs, its bends and its neighbours. A span sampled every SPAN_STEP
# along its wall (each sample's line along the normal: where the host's own ring crosses it, the outermost crossing the
# face seen from the street) keeps only the samples where the wall is there (no crossing: past a corner the panel stood
# in the air over a lawn), in view (no footprint, a neighbour's or the host's own bay, inside the 45 degree cone SPAN_PROBE
# deep in front of it: a neighbour's wall standing 40 cm proud cut a name mid-word from up the street) and flush (the
# span's face at most SPAN_FLUSH proud of the wall anywhere along it, once the wall's own lean against the record's
# angle is taken out and handed to the page as a turn, SPAN_SLOPE at most: a panel bridging a deeper jog stood out as a
# box up to 2 m deep). The best window of such samples, within the record's own room (its laid span and SPAN_SLIDE
# either side, never past the midpoint of the free wall to a neighbour laid beside it), takes the span at its laid width
# when it can, else narrowed to the window; under SPAN_MIN it is hidden. And a business inside a mall (shop=mall: Liberty
# Place, the Fashion District) is no storefront on the street wall: hidden
SPAN_STEP = 0.1
SPAN_FLUSH = 0.3
SPAN_PROBE = 3.0
SPAN_MIN = 3.4        # the S cell (4.5 m) at three quarters
SPAN_SLIDE = 3.0
SPAN_REACH = 3.0      # how far either side of the record's line a crossing counts as its wall
SPAN_SLOPE = 0.15     # the most the panel is turned to its wall (8.5 degrees)
import numpy as np


def ring_cross(ring, cx, cz, tx, tz, nx, nz, ss):
    """For each sample position s along the tangent from (cx, cz), the sorted offsets along n at which `ring` crosses the
    line through (cx, cz) + t s parallel to n."""
    out = [[] for _ in ss]
    m = len(ring)
    for k in range(m):
        x0, z0 = ring[k]; x1, z1 = ring[(k + 1) % m]
        t0 = (x0 - cx) * tx + (z0 - cz) * tz; t1 = (x1 - cx) * tx + (z1 - cz) * tz
        if abs(t1 - t0) < 1e-9:
            continue
        u0 = (x0 - cx) * nx + (z0 - cz) * nz; u1 = (x1 - cx) * nx + (z1 - cz) * nz
        lo, hi = min(t0, t1), max(t0, t1)
        j0 = max(0, int(np.searchsorted(ss, lo)))
        for j in range(j0, len(ss)):
            sv = ss[j]
            if sv >= hi:
                break
            out[j].append(u0 + (sv - t0) / (t1 - t0) * (u1 - u0))
    for q in out:
        q.sort()
    return out


# the rings the page draws, which the profile reads (the review's 'Pub On Passyunk Eas': the host as the extract has it lay
# 3 cm proud of the extract's line and the panel 6 cm proud of that, while the page draws the wall on wide.b64's 0.2 m grid
# 10 cm out at one end, so the wall stood through the panel's end): the core's own as scene.json has them, and wide.b64's
# records (the outer districts and the south set after pack_wide.py's simplification, its grid and its coplanar insets),
# the building parts among them only where they stand on the ground
def drawn_rings():
    out = [rings[i] for i in range(len(rings)) if tiers[i] == 'core']
    raw = base64.b64decode(open('wide.b64').read())
    nb = struct.unpack('<4i', raw[:16])[1]
    h = struct.unpack('<%dh' % ((len(raw) - 16) // 2), raw[16:])
    o = 0
    for _ in range(nb):
        L, minH = h[o], h[o + 2] / 5
        pts = [(h[o + 6 + 2 * k] / 5, h[o + 7 + 2 * k] / 5) for k in range(L)]
        o += 6 + 2 * L
        if minH < 3 and len(pts) >= 3:
            out.append(pts)
    return out


DRAWN = drawn_rings()
DPOLY = []
for ring in DRAWN:
    try:
        pg = Polygon(ring)
        DPOLY.append(pg if pg.is_valid else pg.buffer(0))
    except Exception:
        DPOLY.append(Polygon())
DTREE = STRtree(DPOLY)
_drawnOf = {}


def drawn_host(bi):
    """The drawn rings that are host bi's walls: those mostly inside its footprint (a tower's ground-floor parts, where
    pack_wide.py drew the parts for the outline) or sharing most of it; an empty list when none is."""
    if bi in _drawnOf:
        return _drawnOf[bi]
    out = []
    pg = polys[bi]
    if not pg.is_empty:
        for j in DTREE.query(pg):
            j = int(j)
            q = DPOLY[j]
            if q.is_empty or q.area <= 0:
                continue
            try:
                inter = pg.intersection(q).area
                if inter >= 0.6 * q.area or inter / max(1e-6, pg.union(q).area) > 0.3:
                    out.append(j)
            except Exception:
                continue
    _drawnOf[bi] = out
    return out


def wall_profile(bi, cx, cz, tx, tz, nx, nz, ss):
    """Per sample: the face's offset along n (None where the host's wall is not there) and whether it is out of view."""
    ss = np.asarray(ss)
    dh = drawn_host(bi)
    hostX = [ring_cross(DRAWN[j] if j is not None else rings[bi], cx, cz, tx, tz, nx, nz, ss) for j in (dh or [None])]
    face = []
    for k in range(len(ss)):
        hs = [u for cr in hostX for u in cr[k] if -SPAN_REACH <= u <= SPAN_REACH]
        face.append(max(hs) if hs else None)
    # every footprint's inside along each sample line, as (line, lo, hi): the host's own (its body under the face is
    # below any sample's cone; a bay or a wing proud of it is not) and the neighbours'
    x0 = cx + tx * ss[0]; z0 = cz + tz * ss[0]; x1 = cx + tx * ss[-1]; z1 = cz + tz * ss[-1]
    pad = SPAN_PROBE + SPAN_REACH
    qb = sbox(min(x0, x1) - pad, min(z0, z1) - pad, max(x0, x1) + pad, max(z0, z1) + pad)
    occ = []
    hp = polys[bi]
    hs = set(dh)
    for j in [-1 - q for q in range(len(hostX))] + [int(q) for q in DTREE.query(qb) if int(q) not in hs]:
        if j >= 0:
            q = DPOLY[j]
            if q.is_empty:
                continue
            try:   # the same ground drawn twice is no neighbour
                if q.intersection(hp).area > 0.5 * min(q.area, hp.area):
                    continue
            except Exception:
                pass
        cr = hostX[-1 - j] if j < 0 else ring_cross(DRAWN[j], cx, cz, tx, tz, nx, nz, ss)
        for m, us in enumerate(cr):
            for q in range(0, len(us) - 1, 2):
                occ.append((ss[m], us[q], us[q + 1]))
    hid = [False] * len(ss)
    if occ:
        O = np.asarray(occ)
        for k in range(len(ss)):
            if face[k] is None:
                continue
            d = np.abs(O[:, 0] - ss[k])
            lo = face[k] + np.maximum(0.05, d)
            hi = face[k] + SPAN_PROBE
            hid[k] = bool(np.any((d <= SPAN_PROBE) & (O[:, 2] > lo) & (O[:, 1] < hi)))
    return face, hid


def best_window(ss, face, hid, c0, w):
    """The span's centre and width on the samples: the window of wall that is there, in view and flush that takes the
    most of the laid width, nearest the laid centre, the outer of two equals; or None."""
    K = len(ss)
    ok = [face[k] is not None and not hid[k] for k in range(K)]
    best = None
    i = 0
    from collections import deque
    while i < K:
        if not ok[i]:
            i += 1
            continue
        j0 = i
        while i < K and ok[i]:
            i += 1
        # every maximal flush window within the run (two pointers over a max and a min deque)
        mx, mn = deque(), deque()
        lo = j0
        for j in range(j0, i):
            while mx and face[mx[-1]] <= face[j]: mx.pop()
            mx.append(j)
            while mn and face[mn[-1]] >= face[j]: mn.pop()
            mn.append(j)
            while face[mx[0]] - face[mn[0]] > SPAN_FLUSH:
                lo += 1
                if mx[0] < lo: mx.popleft()
                if mn[0] < lo: mn.popleft()
            a_, b_ = ss[lo] - SPAN_STEP / 2, ss[j] + SPAN_STEP / 2
            L = b_ - a_
            wa = min(w, L)
            c = min(max(c0, a_ + wa / 2), b_ - wa / 2)
            lvl = sum(face[q] for q in range(lo, j + 1)) / (j + 1 - lo)
            key = (round(wa, 2) - 0.5 * abs(c - c0), lvl)
            if best is None or key > best[0]:
                best = (key, c, wa)
    return None if best is None else (best[1], best[2])


def lean(ss, face, a, b):
    """The wall's lean against the record's line over [a, b]: a least-squares slope of its face, with its jogs (a step
    of more than 3 cm a sample) taken out, held within SPAN_SLOPE; 0 when too little of it is there."""
    xs, ys = [], []
    for k in range(len(ss) - 1):
        if a <= ss[k] <= b and face[k] is not None and face[k + 1] is not None and abs(face[k + 1] - face[k]) < 0.03:
            xs.append(ss[k]); ys.append(face[k + 1] - face[k])
    if len(xs) < 10:
        return 0.0
    return max(-SPAN_SLOPE, min(SPAN_SLOPE, float(np.median(ys)) / SPAN_STEP))


malls = []
_mc = {el['id']: fetch_shops.to_xz(el['lat'], el['lon']) for el in ELEMENTS if el.get('type') == 'node' and 'lat' in el}
for el in ELEMENTS:
    t = el.get('tags') or {}
    if el.get('type') == 'way' and t.get('shop') == 'mall':
        ring = [_mc[q] for q in el.get('nodes', []) if q in _mc]
        if len(ring) >= 4:
            try:
                pg = Polygon(ring)
                malls.append(pg if pg.is_valid else pg.buffer(0))
            except Exception:
                pass
# each kept record's room along its wall: SPAN_SLIDE either side of its laid span, and never past the midpoint of the free
# wall to the next one laid on its line
room = {}
for i, e in enumerate(extra):
    c0 = e['c'] + e['shift']
    room[i] = [c0 - e['w'] / 2 - SPAN_SLIDE, c0 + e['w'] / 2 + SPAN_SLIDE]
for g in groups.values():
    live = [i for i in g if extra[i]['keep']]
    if len(live) < 2:
        continue
    T = extra[live[0]]['t']
    pos = sorted(live, key=lambda i: rows[i]['x'] * T[0] + rows[i]['z'] * T[1] + extra[i]['shift'] * (T[0] * extra[i]['t'][0] + T[1] * extra[i]['t'][1]))
    for a_, b_ in zip(pos, pos[1:]):
        ea, eb = extra[a_], extra[b_]
        ca = rows[a_]['x'] * T[0] + rows[a_]['z'] * T[1] + ea['shift'] * (T[0] * ea['t'][0] + T[1] * ea['t'][1])
        cb = rows[b_]['x'] * T[0] + rows[b_]['z'] * T[1] + eb['shift'] * (T[0] * eb['t'][0] + T[1] * eb['t'][1])
        mid = ((ca + ea['w'] / 2) + (cb - eb['w'] / 2)) / 2
        # in each record's own tangent (the group's within 0.05 rad of it)
        sa = T[0] * ea['t'][0] + T[1] * ea['t'][1]; sb = T[0] * eb['t'][0] + T[1] * eb['t'][1]
        ma = ea['c'] + ea['shift'] + (mid - ca) * sa; mb = eb['c'] + eb['shift'] + (mid - cb) * sb
        if sa > 0: room[a_][1] = min(room[a_][1], ma - LAYOUT_GAP / 2)
        else: room[a_][0] = max(room[a_][0], ma + LAYOUT_GAP / 2)
        if sb > 0: room[b_][0] = max(room[b_][0], mb + LAYOUT_GAP / 2)
        else: room[b_][1] = min(room[b_][1], mb - LAYOUT_GAP / 2)

DEBUG = [int(q) for q in (sys.argv[sys.argv.index('--debug') + 1].split(',') if '--debug' in sys.argv else [])]
n_mall = n_narrow = n_slid = n_gone = n_hidpart = n_turned = 0
for i, (r, e) in enumerate(zip(rows, extra)):
    if not e['keep']:
        continue
    if any(m.contains(Point(e['px'], e['pz'])) for m in malls):
        e['keep'] = False; n_mall += 1; continue
    nx, nz = e['n']; tx, tz = e['t']
    c0 = e['c'] + e['shift']                       # the laid centre along the tangent (from the origin)
    a_, b_ = room[i]
    K = max(2, int(round((b_ - a_) / SPAN_STEP)))
    ss = [a_ + (k + 0.5) * (b_ - a_) / K - c0 for k in range(K)]   # relative to the laid centre
    cx, cz = r['x'] + tx * e['shift'], r['z'] + tz * e['shift']
    face, hid = wall_profile(e['bi'], cx, cz, tx, tz, nx, nz, ss)
    slope = lean(ss, face, -e['w'] / 2, e['w'] / 2)
    win = None
    for it in range(2):   # the lean over the laid span, then over the window it finds
        flat = [None if f is None else f - slope * sv for f, sv in zip(face, ss)]
        win = best_window(ss, flat, hid, 0.0, e['w'])
        if win is None or it:
            break
        s2 = lean(ss, face, win[0] - win[1] / 2, win[0] + win[1] / 2)
        if abs(s2 - slope) < 0.005:
            break
        slope = s2
    if i in DEBUG:
        print('record', i, names[i] if i < len(names) else '', 'laid w', round(e['w'], 2), 'room', [round(a_ - c0, 2), round(b_ - c0, 2)], 'slope', round(slope, 3))
        print('  face', ' '.join('--' if f is None else ('%+.2f%s' % (f, '*' if h else '')) for f, h in zip(flat, hid)))
        print('  window', win)
    if win is None or win[1] < SPAN_MIN - 1e-6:
        e['keep'] = False; n_gone += 1; continue
    dc, wa = win
    if any(hid[k] for k in range(len(ss)) if abs(ss[k]) < e['w'] / 2):
        n_hidpart += 1
    if wa < e['w'] - 0.05:
        n_narrow += 1
    if abs(dc) > 0.05:
        n_slid += 1
    if abs(slope) > 0.005:
        n_turned += 1
    e['shift'] += dc; e['w'] = wa; e['slope'] = slope
    # the face over the span at its centre's line: the flattened profile's highest and lowest, carried back to the centre
    sp = [f for f, sv in zip(flat, ss) if f is not None and abs(sv - dc) <= wa / 2]
    e['span'] = [max(sp) + slope * dc, min(sp) + slope * dc]

# the drawn wall over each span, the host's storeys and height
out_cm, in_cm = [], []
rec = []
for i, (r, e) in enumerate(zip(rows, extra)):
    nx, nz = e['n']; tx, tz = e['t']
    w = e['w'] if e['keep'] else 0.0
    cx, cz = r['x'] + tx * e['shift'], r['z'] + tz * e['shift']
    sp = e.get('span') if w > 0 else None
    hi, lo = (sp[0], sp[1]) if sp else (None, None)
    # never saturated (the review: a clamp at 1.2 m laid five panels on tower hosts 1.3 to 1.5 m in front of their wall,
    # Insomnia Cookies on Broad Street among them; the faces are found within SPAN_REACH, and the int16 guard below holds)
    o = 0 if hi is None else int(round(hi * 100))
    n_ = 0 if lo is None else int(round(lo * 100))
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
    rec += [int(round(e['shift'] * 10)), int(math.floor(w * 10 + 1e-6)), o, n_, fp, fams[i], e['hours'], ends | (hdm << 2),
            int(round(e.get('slope', 0.0) * 10000)) if w > 0 else 0]
REC_STRIDE = 9
for v in rec:
    if v > 32767 or v < -32768:
        sys.exit(f'ERROR: {OUT_INFO}: a value {v} does not fit an int16; nothing written')
info = {'v': 2, 'stride': REC_STRIDE, 'n': n, 'b64sha': hashlib.sha256(b64.encode('ascii')).hexdigest(), 'families': list(FAMILIES), 'names': names,
        'rec': base64.b64encode(struct.pack('<%dh' % len(rec), *rec)).decode('ascii'), 'hours': hours,
        'stats': {'groups': n_groups, 'moved': n_moved, 'shrunk': n_shrunk, 'dropped': n_dropped, 'named': n_named,
                  'mall': n_mall, 'narrowed': n_narrow, 'slid': n_slid, 'noWall': n_gone, 'hiddenPart': n_hidpart, 'turned': n_turned,
                  'hoursParsed': n_hours, 'hoursStrings': n_hours_str, 'families': dict(Counter(FAMILIES[f] for f in fams))}}
json.dump(info, open(OUT_INFO, 'w'), separators=(',', ':'), ensure_ascii=False)
pc = lambda a, q: sorted(a)[min(len(a) - 1, int(q * len(a)))] if a else 0
print(f'{OUT_INFO}: {os.path.getsize(OUT_INFO):,} bytes; layout: {n_groups} groups, {n_moved} moved, {n_shrunk} shrunk, '
      f'{n_dropped} dropped; on the drawn wall: {n_narrow} narrowed, {n_slid} slid, {n_hidpart} partly hidden by a '
      f'neighbour before, {n_turned} turned to their wall, {n_gone} hidden (no {SPAN_MIN} m of wall), {n_mall} in a mall; '
      f'{n_named} named; hours parsed for {n_hours} of {n_hours_str} strings; wall out cm p50/p95 '
      f'{pc(out_cm, 0.5)}/{pc(out_cm, 0.95)}, in p5/p50 {pc(in_cm, 0.05)}/{pc(in_cm, 0.5)}', flush=True)
print('families: ' + ', '.join(f'{k}:{v}' for k, v in sorted(info['stats']['families'].items())), flush=True)
