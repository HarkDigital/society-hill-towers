#!/usr/bin/env python3
"""INDEPENDENT verification of the buildings-far audit.
Own decoder for city.b64 (format read from pack_city.py source, not the audit script):
  header <4i: magic 0x5348545B, nb, nr, na
  int16 LE body; building = [n, h*5, minH*5, type, attr, roof] + n*(x,z) at 0.7 m/unit
  road = [n, w*10, rt] + pairs; area = [n, kind] + pairs
Rule replicated from the audit's claim: offender iff h>=4 AND
  (centroid within (w/2 - 1) m of a c<=1 chain polyline, OR >=60% of vertices in band).
Full recompute over all buildings with a segment grid; exact distances out to band+20 m.
"""
import json, struct, base64, math, sys
from array import array

BASE = "/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model"
S = 0.7

blob = base64.b64decode(open(BASE + "/city.b64").read())
magic, nb, nr, na = struct.unpack_from("<4i", blob, 0)
assert magic == 0x5348545B, hex(magic)
body = array("h")
body.frombytes(blob[16:])
if sys.byteorder == "big":
    body.byteswap()

k = 0
buildings = []  # (h, [(x,z) meters...])
hmin = 1e9
for _ in range(nb):
    n = body[k]; h = body[k + 1] / 5.0; mh = body[k + 2] / 5.0
    bt, aw, rw = body[k + 3], body[k + 4], body[k + 5]
    k += 6
    # pack_city's decimation ext[::max(1,len//32)] leaves up to 63 verts (stride 1 for 33..63)
    assert 3 <= n <= 63, n
    pts = [(body[k + 2 * i] * S, body[k + 2 * i + 1] * S) for i in range(n)]
    k += 2 * n
    hmin = min(hmin, h)
    buildings.append((h, pts))
for _ in range(nr):
    n = body[k]; k += 3 + 2 * n
    assert n >= 2
nr_end = k
for _ in range(na):
    n = body[k]; k += 2 + 2 * n
    assert n >= 3
assert k == len(body), (k, len(body))  # whole body consumed => layout is right

ov = json.load(open(BASE + "/overpasses.json"))
chains = [ch for ch in ov["el"] if ch["c"] <= 1]
segs = []  # (ax, az, bx, bz, halfband)
for ch in chains:
    hb = ch["w"] / 2.0 - 1.0
    p = ch["p"]
    for a, b in zip(p, p[1:]):
        segs.append((a[0], a[1], b[0], b[1], hb))

CELL = 64.0
REACH = 20.0  # exact distances out to band+REACH
grid = {}
for si, (ax, az, bx, bz, hb) in enumerate(segs):
    r = hb + REACH
    x0, x1 = min(ax, bx) - r, max(ax, bx) + r
    z0, z1 = min(az, bz) - r, max(az, bz) + r
    for gx in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
        for gz in range(int(math.floor(z0 / CELL)), int(math.floor(z1 / CELL)) + 1):
            grid.setdefault((gx, gz), []).append(si)

def near_segs(x, z):
    return grid.get((int(math.floor(x / CELL)), int(math.floor(z / CELL))), ())

def pseg(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    ex, ez = ax + t * dx - px, az + t * dz - pz
    return math.hypot(ex, ez)

offenders = []
tested = 0
best = []  # (margin, dist, hb, cx, cz, h) smallest centroid margins
for h, pts in buildings:
    if h < 4:
        continue
    tested += 1
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    cand = near_segs(cx, cz)
    if not cand:
        continue
    # centroid test: min margin over segments
    m_margin, m_dist, m_hb = 1e9, None, None
    for si in cand:
        ax, az, bx, bz, hb = segs[si]
        d = pseg(cx, cz, ax, az, bx, bz)
        if d - hb < m_margin:
            m_margin, m_dist, m_hb = d - hb, d, hb
    # vertex test: fraction of vertices inside SOME chain band
    inb = 0
    for px, pz in pts:
        ok = False
        for si in near_segs(px, pz):
            ax, az, bx, bz, hb = segs[si]
            if pseg(px, pz, ax, az, bx, bz) <= hb:
                ok = True
                break
        if ok:
            inb += 1
    vfrac = inb / len(pts)
    if m_margin <= 0 or vfrac >= 0.6:
        offenders.append(dict(x=round(cx, 1), z=round(cz, 1), h=h,
                              cmargin=round(m_margin, 2), vfrac=round(vfrac, 2)))
    best.append((m_margin, m_dist, m_hb, round(cx, 1), round(cz, 1), h))

best.sort(key=lambda t: t[0])
print(json.dumps(dict(
    counts=dict(buildings=nb, roads=nr, areas=na,
                chains_total=len(ov["el"]), chains_c_le_1=len(chains),
                segments=len(segs), tested_h_ge_4=tested, min_building_h=hmin),
    offenders=offenders[:10], n_offenders=len(offenders),
    nearest5=[dict(margin=round(m, 2), dist=round(d, 2), band=b, x=x, z=z, h=h)
              for m, d, b, x, z, h in best[:5]],
    within10_of_band=sum(1 for m, *_ in best if m <= 10.0),
), indent=1))
