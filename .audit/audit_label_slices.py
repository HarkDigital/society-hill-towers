#!/usr/bin/env python3
"""Audit: street-name labels sliced by crossing elevated (el) deck chains.

A label span = segment from (x,z) - halfLen*dir to (x,z) + halfLen*dir,
dir = (cos b, sin b) with b = bearingDeg (atan2(dz,dx) convention, per
bake_street_labels.py). halfLen = len(name) * 0.31 * TH, TH by label cls.

Flag when the span passes within (chainW/2 + 1) of an el chain segment whose
axis crosses the label: |cos(angle between directions)| < 0.72.
Then test shifts of +-20/40/60 m along the bearing for a clear placement.
"""
import json, math, pathlib
from collections import defaultdict

ROOT = pathlib.Path("/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model")
TH = [7.0, 5.6, 4.4]
COS_CROSS = 0.72
CELL = 250.0

labels_d = json.loads((ROOT / "street_labels.json").read_text())
names = labels_d["names"]
flat = labels_d["l"]
NLAB = len(flat) // 5

over = json.loads((ROOT / "overpasses.json").read_text())
el = over["el"]

# ---- collect chain segments: (ax, az, bx, bz, ux, uz, thresh, cls) ----
segs = []
for ch in el:
    w = ch["w"]
    thresh = w / 2.0 + 1.0
    cls = ch["c"]
    p = ch["p"]
    for a, b in zip(p, p[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz)
        if L < 0.01:
            continue
        segs.append((a[0], a[1], b[0], b[1], dx / L, dz / L, thresh, cls))

# ---- spatial grid over chain segments (expanded by thresh) ----
grid = defaultdict(list)
for i, (ax, az, bx, bz, ux, uz, th, cls) in enumerate(segs):
    x0, x1 = min(ax, bx) - th, max(ax, bx) + th
    z0, z1 = min(az, bz) - th, max(az, bz) + th
    for cx in range(int(x0 // CELL), int(x1 // CELL) + 1):
        for cz in range(int(z0 // CELL), int(z1 // CELL) + 1):
            grid[(cx, cz)].append(i)

def seg_seg_dist(p1x, p1z, p2x, p2z, q1x, q1z, q2x, q2z):
    """2D min distance between segments p1-p2 and q1-q2."""
    d1x, d1z = p2x - p1x, p2z - p1z
    d2x, d2z = q2x - q1x, q2z - q1z
    # intersection test via orientation signs
    def cross(ox, oz, axx, azz, bxx, bzz):
        return (axx - ox) * (bzz - oz) - (azz - oz) * (bxx - ox)
    o1 = cross(p1x, p1z, p2x, p2z, q1x, q1z)
    o2 = cross(p1x, p1z, p2x, p2z, q2x, q2z)
    o3 = cross(q1x, q1z, q2x, q2z, p1x, p1z)
    o4 = cross(q1x, q1z, q2x, q2z, p2x, p2z)
    if ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0)):
        return 0.0
    def pt_seg(px, pz, ax, az, bx, bz):
        vx, vz = bx - ax, bz - az
        L2 = vx * vx + vz * vz
        if L2 < 1e-12:
            return math.hypot(px - ax, pz - az)
        t = ((px - ax) * vx + (pz - az) * vz) / L2
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
        return math.hypot(px - (ax + vx * t), pz - (az + vz * t))
    return min(pt_seg(p1x, p1z, q1x, q1z, q2x, q2z),
               pt_seg(p2x, p2z, q1x, q1z, q2x, q2z),
               pt_seg(q1x, q1z, p1x, p1z, p2x, p2z),
               pt_seg(q2x, q2z, p1x, p1z, p2x, p2z))

def crossing_hits(cx, cz, ux, uz, half):
    """Chain segments that slice a span centered at (cx,cz), dir (ux,uz)."""
    p1x, p1z = cx - ux * half, cz - uz * half
    p2x, p2z = cx + ux * half, cz + uz * half
    x0, x1 = min(p1x, p2x), max(p1x, p2x)
    z0, z1 = min(p1z, p2z), max(p1z, p2z)
    cand = set()
    for gx in range(int(x0 // CELL), int(x1 // CELL) + 1):
        for gz in range(int(z0 // CELL), int(z1 // CELL) + 1):
            cand.update(grid.get((gx, gz), ()))
    hits = []
    for i in cand:
        ax, az, bx, bz, sux, suz, th, cls = segs[i]
        if abs(ux * sux + uz * suz) >= COS_CROSS:
            continue  # aligned: label rides the deck, fine
        if seg_seg_dist(p1x, p1z, p2x, p2z, ax, az, bx, bz) < th:
            hits.append(cls)
    return hits

offenders = []          # (name, x, z, chain classes hit, fixable, cls)
per_class_hit = defaultdict(int)   # by chain class
per_label_cls = defaultdict(int)   # by label cls
fixable = 0
SHIFTS = (20, -20, 40, -40, 60, -60)

for li in range(NLAB):
    ni, x, z, b, cls = flat[li * 5:li * 5 + 5]
    name = names[ni]
    half = len(name) * 0.31 * TH[cls]
    ang = math.radians(b)
    ux, uz = math.cos(ang), math.sin(ang)
    hits = crossing_hits(x, z, ux, uz, half)
    if not hits:
        continue
    per_label_cls[cls] += 1
    for c in set(hits):
        per_class_hit[c] += 1
    fix = False
    for s in SHIFTS:
        if not crossing_hits(x + ux * s, z + uz * s, ux, uz, half):
            fix = True
            break
    if fix:
        fixable += 1
    offenders.append((name, x, z, sorted(set(hits)), fix, cls))

CLASS_NAMES = {0: "motorway", 1: "trunk/primary", 2: "secondary", 3: "tertiary",
               4: "minor", 5: "rail/other", 6: "footbridge"}

print(json.dumps({
    "total_labels": NLAB,
    "el_chains": len(el),
    "el_segments": len(segs),
    "sliced": len(offenders),
    "fixable_by_shift": fixable,
    "unfixable": len(offenders) - fixable,
    "sliced_by_label_cls": dict(sorted(per_label_cls.items())),
    "sliced_by_chain_cls": dict(sorted(per_class_hit.items())),
    "offenders": [
        {"name": n, "x": x, "z": z, "chain_cls": cc, "fixable": fx, "label_cls": lc}
        for n, x, z, cc, fx, lc in offenders[:60]
    ],
}, indent=1))
