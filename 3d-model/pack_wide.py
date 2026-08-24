#!/usr/bin/env python3
"""scene_wide.json -> wide.b64 : compact int16 binary (0.2 m units) for the outer districts.
Layout: Int32[4] header (magic, nBuildings, nRoads, nAreas), then Int16 body:
  building: n, h*5, minH*5, type, x1,z1,...   road: n, w*10, type, pts...   area: n, kind, pts...
Buildings inside the detailed core bbox are dropped (the core scene covers them)."""
import json, math, struct, base64
CORE = (-640, 770, -520, 850)        # x0, x1, z0, z1 of the detailed core extract
WIDE = (-3700, 2300, -4480, 6400)    # wide bbox in local meters (south to the stadiums + Walt Whitman Bridge)
BT = {'generic': 0, 'house': 1, 'residential': 1, 'terrace': 1, 'apartments': 2, 'detached': 1, 'semidetached_house': 1,
      'commercial': 3, 'retail': 3, 'office': 3, 'hotel': 3, 'industrial': 4, 'warehouse': 4, 'garage': 4, 'parking': 4,
      'church': 5, 'worship': 5, 'school': 6, 'civic': 6, 'hospital': 6, 'university': 6, 'roof': 7, 'ship': 7, 'stadium': 8, 'arena': 9}
RT = {'motorway': 0, 'motorway_link': 0, 'trunk': 1, 'trunk_link': 1, 'primary': 2, 'secondary': 3, 'tertiary': 4,
      'residential': 5, 'living_street': 5, 'unclassified': 5, 'pedestrian': 6}
AK = {'park': 0, 'water': 1, 'pier': 2}
d = json.load(open('scene_wide.json'))
try:
    _south = json.load(open('scene_south.json'))
    seenB = set(tuple(map(tuple, b['poly'][:3])) for b in d['buildings'])
    for b in _south['buildings']:
        if tuple(map(tuple, b['poly'][:3])) in seenB: continue
        if (b.get('name') or '') == 'Xfinity Mobile Arena': b['t'] = 'arena'
        d['buildings'].append(b)
    d['roads'] += _south['roads']; d['areas'] += _south['areas']
    print('merged south scene')
except FileNotFoundError: pass
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
def clip(v): return max(-32767, min(32767, int(round(v))))
def touchesCore(poly, m=2):
    return any(CORE[0] - m <= q[0] <= CORE[1] + m and CORE[2] - m <= q[1] <= CORE[3] + m for q in poly)
def pip(x, z, poly):
    inside = False; j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]; xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi: inside = not inside
        j = i
    return inside
# building:part centroids indexed on a 50 m grid: outlines that contain a part are dropped
partCells = {}
try:
    for pt in json.load(open('parts_wide.json')):
        if len(pt['poly']) >= 3:
            cx, cz = cent(pt['poly']); partCells.setdefault((int(cx // 50), int(cz // 50)), []).append((cx, cz))
except FileNotFoundError: pass
def containsPart(poly):
    xs = [q[0] for q in poly]; zs = [q[1] for q in poly]
    for gx in range(int(min(xs) // 50), int(max(xs) // 50) + 1):
        for gz in range(int(min(zs) // 50), int(max(zs) // 50) + 1):
            for (cx, cz) in partCells.get((gx, gz), []):
                if pip(cx, cz, poly): return True
    return False
body = []
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
    sp = simplify(poly, 0.35)
    if len(sp) > 48: sp = sp[::max(1, len(sp) // 48)]
    h = max(2.5, min(6500, b['h']))
    body += [len(sp), clip(h * 5), 0, BT.get(b.get('t') or 'generic', 0)]
    for q in sp: body += [clip(q[0] * 5), clip(q[1] * 5)]
    nb += 1
# 3D-mapped building parts (skyscraper shafts, crowns, podiums) from building:part ways;
# parts of research-flagged glass towers get type 10 (reflective glass material)
import os, math as _m
glassSpots = []
try:
    for res in json.load(open('wide_landmarks_research.json')):
        for bb in res.get('buildings', []):
            if bb.get('glass') and bb.get('lat') and bb.get('lon'):
                glassSpots.append(((bb['lon'] + 75.144748) * 85350, (39.945474 - bb['lat']) * -110574 * -1))
except FileNotFoundError: pass
glassSpots = [(gx, (39.945474 - lat) * 110574) if False else (gx, gz) for (gx, gz) in glassSpots]
def isGlass(cx, cz):
    return any(_m.hypot(cx - gx, cz - gz) < 75 for gx, gz in glassSpots)
if os.path.exists('parts_wide.json'):
    for pt in json.load(open('parts_wide.json')):
        poly = pt['poly']
        if len(poly) < 3 or area(poly) < 8: continue
        cx, cz = cent(poly)
        if CORE[0] <= cx <= CORE[1] and CORE[2] <= cz <= CORE[3]: continue
        sp = simplify(poly, 0.3)
        if len(sp) > 48: sp = sp[::max(1, len(sp) // 48)]
        body += [len(sp), clip(min(6500, pt['h']) * 5), clip(pt['minH'] * 5), 10 if isGlass(cx, cz) else 3]
        for q in sp: body += [clip(q[0] * 5), clip(q[1] * 5)]
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
        body += [len(pts), clip(r['w'] * 10), RT[r['t']]]
        for q in pts: body += [clip(q[0] * 5), clip(q[1] * 5)]
        nr += 1
for a in d['areas']:
    if a['kind'] not in AK or len(a['poly']) < 3: continue
    cx, cz = cent(a['poly'])
    if touchesCore(a['poly']): continue
    if not (WIDE[0] - 500 <= cx <= WIDE[1] + 500 and WIDE[2] - 500 <= cz <= WIDE[3] + 500): continue
    sp = simplify(a['poly'], 0.8)
    if len(sp) > 120: sp = sp[::max(1, len(sp) // 120)]
    body += [len(sp), AK[a['kind']]]
    for q in sp: body += [clip(q[0] * 5), clip(q[1] * 5)]
    na += 1
buf = struct.pack('<4i', 0x53485458, nb, nr, na) + struct.pack('<%dh' % len(body), *body)
b64 = base64.b64encode(buf).decode('ascii')
open('wide.b64', 'w').write(b64)
print(f'buildings {nb} roads {nr} areas {na} -> {len(buf)/1e6:.2f} MB binary, {len(b64)/1e6:.2f} MB base64; dropped {dropped_dup} core-duplicates, {dropped_outline} outlines with 3D parts')
