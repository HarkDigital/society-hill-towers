#!/usr/bin/env python3
"""Audit: buildings in wide.b64 intersecting elevated motorway/trunk deck swaths,
sunken OPEN runs, and corridor runs from overpasses.json."""
import base64, json, math, struct, os

MODEL = '/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model'

# ---------- decode wide.b64 ----------
raw = base64.b64decode(open(os.path.join(MODEL, 'wide.b64')).read())
magic, nb, nr, na = struct.unpack_from('<4i', raw, 0)
assert magic in (0x5348545A, 0x53485458), hex(magic)
has_attr = (magic == 0x5348545A)
body = struct.unpack_from('<%dh' % ((len(raw) - 16) // 2), raw, 16)
i = 0
buildings = []
for _ in range(nb):
    n = body[i]; h = body[i + 1] / 5.0; minh = body[i + 2] / 5.0
    btype = body[i + 3]
    if has_attr:
        i += 6
    else:
        i += 4
    pts = [(body[i + 2 * k] / 5.0, body[i + 2 * k + 1] / 5.0) for k in range(n)]
    i += 2 * n
    buildings.append((h, minh, btype, pts))
# sanity: walk roads and areas to be sure the stream is aligned
for _ in range(nr):
    n = body[i]; i += 3 + 2 * n
for _ in range(na):
    n = body[i]; i += 2 + 2 * n
assert i == len(body), (i, len(body))

# ---------- centroid (area-weighted) ----------
def centroid(p):
    a = 0.0; cx = 0.0; cz = 0.0
    for j in range(len(p)):
        x0, z0 = p[j]; x1, z1 = p[(j + 1) % len(p)]
        cr = x0 * z1 - x1 * z0
        a += cr; cx += (x0 + x1) * cr; cz += (z0 + z1) * cr
    if abs(a) < 1e-9:
        return sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p)
    a *= 0.5
    return cx / (6 * a), cz / (6 * a)

# ---------- swath segments with spatial grid ----------
ov = json.load(open(os.path.join(MODEL, 'overpasses.json')))
CELL = 64.0
grid = {}
segs = []  # (x0,z0,x1,z1,halfw,kind,label)

def add_seg(x0, z0, x1, z1, halfw, kind):
    idx = len(segs)
    segs.append((x0, z0, x1, z1, halfw, kind))
    pad = halfw + 1.0
    gx0 = int(math.floor((min(x0, x1) - pad) / CELL)); gx1 = int(math.floor((max(x0, x1) + pad) / CELL))
    gz0 = int(math.floor((min(z0, z1) - pad) / CELL)); gz1 = int(math.floor((max(z0, z1) + pad) / CELL))
    for gx in range(gx0, gx1 + 1):
        for gz in range(gz0, gz1 + 1):
            grid.setdefault((gx, gz), []).append(idx)

n_el_chains = 0
for ch in ov['el']:
    if ch.get('c', 99) > 1:
        continue
    n_el_chains += 1
    hw = ch['w'] / 2.0 - 1.0
    p = ch['p']
    for j in range(len(p) - 1):
        add_seg(p[j][0], p[j][1], p[j + 1][0], p[j + 1][1], hw, 'elevated')

n_sk_open = 0
for ch in ov.get('sk', []):
    if ch.get('cov') == 1:
        continue
    n_sk_open += 1
    hw = ch['w'] / 2.0 - 1.0
    p = ch['p']
    for j in range(len(p) - 1):
        add_seg(p[j][0], p[j][1], p[j + 1][0], p[j + 1][1], hw, 'sunken-open')

n_cor = 0
for run in ov.get('cor', []):
    n_cor += 1
    for j in range(len(run) - 1):
        hw = max(run[j][3], run[j + 1][3])  # halfW straight from the data
        add_seg(run[j][0], run[j][1], run[j + 1][0], run[j + 1][1], hw, 'corridor')

def hit_kinds(x, z):
    """set of kinds whose swath contains point (x,z)"""
    out = set()
    key = (int(math.floor(x / CELL)), int(math.floor(z / CELL)))
    for idx in grid.get(key, ()):  # pad in add_seg guarantees cell coverage
        x0, z0, x1, z1, hw, kind = segs[idx]
        if kind in out:
            continue
        dx = x1 - x0; dz = z1 - z0
        L2 = dx * dx + dz * dz
        if L2 < 1e-12:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((x - x0) * dx + (z - z0) * dz) / L2))
        px = x0 + t * dx; pz = z0 + t * dz
        if (x - px) ** 2 + (z - pz) ** 2 <= hw * hw:
            out.add(kind)
    return out

def seg_seg_dist(ax, az, bx, bz, cx, cz, dx, dz):
    def pt_seg(px, pz, x0, z0, x1, z1):
        ux, uz = x1 - x0, z1 - z0
        L2 = ux * ux + uz * uz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - x0) * ux + (pz - z0) * uz) / L2))
        return math.hypot(px - (x0 + t * ux), pz - (z0 + t * uz))
    def cr(ox, oz, px, pz, qx, qz): return (px - ox) * (qz - oz) - (pz - oz) * (qx - ox)
    d1 = cr(cx, cz, dx, dz, ax, az); d2 = cr(cx, cz, dx, dz, bx, bz)
    d3 = cr(ax, az, bx, bz, cx, cz); d4 = cr(ax, az, bx, bz, dx, dz)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(pt_seg(ax, az, cx, cz, dx, dz), pt_seg(bx, bz, cx, cz, dx, dz),
               pt_seg(cx, cz, ax, az, bx, bz), pt_seg(dx, dz, ax, az, bx, bz))

def overlap_kinds(pts):
    """kinds whose swath the footprint OUTLINE overlaps (any edge comes within halfw)"""
    cand = set()
    for (vx, vz) in pts:
        key = (int(math.floor(vx / CELL)), int(math.floor(vz / CELL)))
        cand.update(grid.get(key, ()))
    out = set()
    for idx in cand:
        x0, z0, x1, z1, hw, kind = segs[idx]
        if kind in out:
            continue
        for k in range(len(pts)):
            a = pts[k]; b = pts[(k + 1) % len(pts)]
            if seg_seg_dist(a[0], a[1], b[0], b[1], x0, z0, x1, z1) <= hw:
                out.add(kind)
                break
    return out

# ---------- audit ----------
offenders = []
counts = {'elevated': 0, 'sunken-open': 0, 'corridor': 0}
for h, minh, btype, pts in buildings:
    cx, cz = centroid(pts)
    cent_hits = hit_kinds(cx, cz) if h >= 4 else set()
    # vertex test (independent of the h>=4 gate per the spec: "even if the centroid is not")
    vhits = {'elevated': 0, 'sunken-open': 0, 'corridor': 0}
    for (vx, vz) in pts:
        for k in hit_kinds(vx, vz):
            vhits[k] += 1
    nvert = len(pts)
    vert_kinds = {k for k, c in vhits.items() if c >= 0.6 * nvert}
    ov_kinds = overlap_kinds(pts) if h >= 4 else set()
    kinds = cent_hits | vert_kinds | ov_kinds
    if not kinds:
        continue
    for k in kinds:
        counts[k] += 1
    how = []
    for k in sorted(kinds):
        tags = []
        if k in cent_hits:
            tags.append('centroid')
        if k in vert_kinds:
            tags.append('%d/%d verts' % (vhits[k], nvert))
        if k in ov_kinds and k not in cent_hits and k not in vert_kinds:
            tags.append('footprint straddles swath')
        how.append('%s (%s)' % (k, '+'.join(tags)))
    offenders.append({
        'x': round(cx, 1), 'z': round(cz, 1),
        'detail': 'h=%.1fm type=%d %s' % (h, btype, '; '.join(how)),
        '_h': h,
    })

# known-offender confirmation: literal hinted window, plus x-sign-tolerant window
known_literal = [o for o in offenders if 200 <= o['x'] <= 500 and 850 <= o['z'] <= 1400]
known_wide = [o for o in offenders if -500 <= o['x'] <= 500 and 850 <= o['z'] <= 1400]

offenders.sort(key=lambda o: -o['_h'])
for o in offenders:
    del o['_h']

result = {
    'total_buildings': nb,
    'roads': nr, 'areas': na,
    'el_chains_c_le_1': n_el_chains, 'sk_open_runs': n_sk_open, 'cor_runs': n_cor,
    'offender_total': len(offenders),
    'counts': counts,
    'known_region_hits_literal': known_literal,
    'known_region_hits_x_sign_tolerant': known_wide,
    'offenders': offenders[:40],
}
print(json.dumps(result, indent=1))
