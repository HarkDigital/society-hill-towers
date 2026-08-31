#!/usr/bin/env python3
"""Audit: far-ring (city.b64) buildings intersecting elevated motorway decks.

Decodes city.b64 (magic 0x5348545B; int16 body; coord unit 0.7 m;
building record: n, h*5, minH*5, type, attr, roof, then n (x,z) pairs).
Test (same as wide audit): building with h >= 4 whose centroid lies within
(chainWidth/2 - 1) m of an elevated chain with class c <= 1, OR >= 60% of
whose vertices lie within that band.
"""
import json, struct, base64, math, os, sys

MODEL = "/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model"
S = 0.7

blob = base64.b64decode(open(os.path.join(MODEL, "city.b64")).read())
magic, nb, nr, na = struct.unpack_from("<4i", blob, 0)
assert magic == 0x5348545B, hex(magic)
body = struct.unpack_from("<%dh" % ((len(blob) - 16) // 2), blob, 16)

buildings = []  # (cx, cz, h, verts, btype)
i = 0
for _ in range(nb):
    n, h5, mh5, bt, aw, rw = body[i:i + 6]
    i += 6
    verts = [(body[i + 2 * k] * S, body[i + 2 * k + 1] * S) for k in range(n)]
    i += 2 * n
    cx = sum(v[0] for v in verts) / n
    cz = sum(v[1] for v in verts) / n
    buildings.append((cx, cz, h5 / 5.0, verts, bt))
for _ in range(nr):
    n = body[i]
    i += 3 + 2 * n
for _ in range(na):
    n = body[i]
    i += 2 + 2 * n
assert i == len(body), (i, len(body))

ov = json.load(open(os.path.join(MODEL, "overpasses.json")))
chains = [ch for ch in ov["el"] if ch["c"] <= 1]

# segment grid: (ci, si, ax, az, bx, bz, halfw) indexed into 50 m cells
CELL = 50.0
grid = {}
segs = []
maxhw = 0.0
for ci, ch in enumerate(chains):
    hw = ch["w"] / 2.0 - 1.0
    maxhw = max(maxhw, hw)
    p = ch["p"]
    for si in range(len(p) - 1):
        ax, az = p[si][0], p[si][1]
        bx, bz = p[si + 1][0], p[si + 1][1]
        idx = len(segs)
        segs.append((ci, si, ax, az, bx, bz, hw))
        x0, x1 = sorted((ax, bx)); z0, z1 = sorted((az, bz))
        for gx in range(int((x0 - hw) // CELL), int((x1 + hw) // CELL) + 1):
            for gz in range(int((z0 - hw) // CELL), int((z1 + hw) // CELL) + 1):
                grid.setdefault((gx, gz), []).append(idx)

def seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    qx, qz = ax + t * dx, az + t * dz
    return math.hypot(px - qx, pz - qz), t

def near(px, pz):
    """Return (dist, segrec, t) for nearest indexed segment within its halfw, else None."""
    gx, gz = int(px // CELL), int(pz // CELL)
    best = None
    for ox in (-1, 0, 1):
        for oz in (-1, 0, 1):
            for idx in grid.get((gx + ox, gz + oz), ()):
                s = segs[idx]
                d, t = seg_dist(px, pz, s[2], s[3], s[4], s[5])
                if d <= s[6] and (best is None or d < best[0]):
                    best = (d, s, t)
    return best

tested = 0
offenders = []
for cx, cz, h, verts, bt in buildings:
    if h < 4:
        continue
    tested += 1
    hit = near(cx, cz)
    frac = None
    if hit is None:
        inside = sum(1 for vx, vz in verts if near(vx, vz) is not None)
        frac = inside / len(verts)
        if frac >= 0.6:
            hit = near(*max(verts, key=lambda v: 0 if near(*v) is None else 1))
            # representative: first vertex that is inside
            for v in verts:
                hh = near(*v)
                if hh is not None:
                    hit = hh
                    break
        else:
            continue
    d, s, t = hit
    ci, si = s[0], s[1]
    ch = chains[ci]
    ya, yb = ch["p"][si][2], ch["p"][si + 1][2]
    ytop = ya + t * (yb - ya)
    ybot = ytop - 1.7
    mode = "centroid" if frac is None else f"{frac*100:.0f}% verts"
    offenders.append({
        "x": round(cx, 1), "z": round(cz, 1),
        "detail": (f"h={h:.1f}m bldg ({mode} in band, d={d:.1f}m of c{ch['c']} "
                   f"chain #{ci} w={ch['w']}m; deck top y={ytop:.1f}, bottom y={ybot:.1f})"),
        "_d": d,
    })

offenders.sort(key=lambda o: o["_d"])
for o in offenders:
    del o["_d"]

result = {
    "counts": {
        "buildings": nb, "roads": nr, "areas": na,
        "elevated_chains_total": len(ov["el"]),
        "elevated_chains_c_le_1": len(chains),
        "segments_indexed": len(segs),
        "buildings_tested_h_ge_4": tested,
        "offenders": len(offenders),
    },
    "offenders": offenders[:40],
}
json.dump(result, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "city_motorway_result.json"), "w"), indent=1)
print(json.dumps(result["counts"], indent=1))
for o in result["offenders"]:
    print(o["x"], o["z"], o["detail"])
