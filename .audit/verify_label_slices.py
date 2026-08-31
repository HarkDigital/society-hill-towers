#!/usr/bin/env python3
"""Independent re-derivation of the 'label-slices' audit.

Formats read directly from the pack scripts:
  street_labels.json  (bake_street_labels.py): {"names":[...], "l": flat
      [nameIdx, x, z, bearingDeg, cls] * N}, cls 0=major 1=minor 2=core,
      TH = [7.0, 5.6, 4.4]
  overpasses.json (task spec / bake_street_labels.py reader): {"el":[{c,w,
      p:[[x,z,yTop],...], e}], ...}

Audit's stated criterion: label span = center +- halfLen*(cos b, sin b),
halfLen = len(name)*0.31*TH[cls]; sliced if exact 2D seg-seg distance to an
el deck segment < w/2 + 1 AND |cos angle between directions| < 0.72.
Brute force with bbox prefilter -- no shared code with the audit script.
"""
import json, math, pathlib

ROOT = pathlib.Path("/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model")
TH = [7.0, 5.6, 4.4]

sl = json.loads((ROOT / "street_labels.json").read_text())
names = sl["names"]
flat = sl["l"]
assert len(flat) % 5 == 0
labels = [flat[i:i+5] for i in range(0, len(flat), 5)]

ov = json.loads((ROOT / "overpasses.json").read_text())
segs = []  # (ax, az, bx, bz, hw, c, chain_idx)
for ci, ch in enumerate(ov.get("el", [])):
    hw = ch["w"] / 2.0
    p = ch["p"]
    for a, b in zip(p, p[1:]):
        segs.append((a[0], a[1], b[0], b[1], hw, ch["c"], ci))
print(f"el chains={len(ov.get('el', []))} el segments={len(segs)} labels={len(labels)}")

def seg_seg_dist(p1, p2, p3, p4):
    """Exact min distance between 2D segments p1-p2 and p3-p4."""
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    # intersection test
    d1, d2 = cross(p3, p4, p1), cross(p3, p4, p2)
    d3, d4 = cross(p1, p2, p3), cross(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    def pt_seg(p, a, b):
        dx, dz = b[0]-a[0], b[1]-a[1]
        L2 = dx*dx + dz*dz
        if L2 < 1e-12:
            return math.hypot(p[0]-a[0], p[1]-a[1])
        t = max(0.0, min(1.0, ((p[0]-a[0])*dx + (p[1]-a[1])*dz) / L2))
        return math.hypot(a[0]+dx*t-p[0], a[1]+dz*t-p[1])
    return min(pt_seg(p1, p3, p4), pt_seg(p2, p3, p4),
               pt_seg(p3, p1, p2), pt_seg(p4, p1, p2))

def sliced_by(x, z, bdeg, half_len, extra=1.0, cos_thr=0.72):
    """Return list of (dist, hw, c, chain) for el segs slicing this span."""
    b = math.radians(bdeg)
    ux, uz = math.cos(b), math.sin(b)
    e1 = (x - ux*half_len, z - uz*half_len)
    e2 = (x + ux*half_len, z + uz*half_len)
    lo_x, hi_x = min(e1[0], e2[0]), max(e1[0], e2[0])
    lo_z, hi_z = min(e1[1], e2[1]), max(e1[1], e2[1])
    hits = []
    for ax, az, bx, bz, hw, c, ci in segs:
        r = hw + extra
        if min(ax, bx) > hi_x + r or max(ax, bx) < lo_x - r:
            continue
        if min(az, bz) > hi_z + r or max(az, bz) < lo_z - r:
            continue
        dx, dz = bx - ax, bz - az
        L = math.hypot(dx, dz)
        if L < 0.05:
            continue
        if abs((dx*ux + dz*uz) / L) >= cos_thr:
            continue
        d = seg_seg_dist(e1, e2, (ax, az), (bx, bz))
        if d < r:
            hits.append((round(d, 2), hw, c, ci))
    return hits

offenders = []
for ni, x, z, bdeg, cls in labels:
    name = names[ni]
    hl = len(name) * 0.31 * TH[cls]
    hits = sliced_by(x, z, bdeg, hl)
    if hits:
        offenders.append((name, x, z, bdeg, cls, hits))

print(f"\nAUDIT CRITERION (halfLen=0.31*TH, w/2+1, |cos|<0.72): sliced = {len(offenders)}")
for name, x, z, b, cls, hits in offenders[:40]:
    print(f"  {name} @({x},{z}) b={b} cls={cls} hits={hits}")

# sensitivity: the bake's own span factor 0.34 and clearance +1.2
off34 = 0
for ni, x, z, bdeg, cls in labels:
    hl = len(names[ni]) * 0.34 * TH[cls]
    if sliced_by(x, z, bdeg, hl, extra=1.2):
        off34 += 1
print(f"BAKE CRITERION  (halfLen=0.34*TH, w/2+1.2): sliced = {off34}")

# the three named offenders from the audit report
print("\nNamed offenders check (does a label exist there, and is it sliced?):")
for tx, tz, tname in [(-293, 2781, "Jackson Street"), (-243, 2514, "McKean Street"),
                      (-262, 3211, "East Porter Street"), (378, -1658, "Spring Garden Street")]:
    best = min(labels, key=lambda L: (L[1]-tx)**2 + (L[2]-tz)**2)
    ni, x, z, b, cls = best
    d = math.hypot(x-tx, z-tz)
    nm = names[ni]
    hl = len(nm) * 0.31 * TH[cls]
    hits = sliced_by(x, z, b, hl)
    print(f"  target ({tx},{tz}) '{tname}': nearest label '{nm}' @({x},{z}) "
          f"dist={d:.1f} m cls={cls} sliced={bool(hits)} hits={hits}")
    # also: any label with that exact name within 60 m?
    same = [L for L in labels if names[L[0]] == tname and math.hypot(L[1]-tx, L[2]-tz) < 60]
    print(f"    labels named '{tname}' within 60 m: {[(L[1], L[2]) for L in same]}")
