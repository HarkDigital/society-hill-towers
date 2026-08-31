#!/usr/bin/env python3
"""Adversarial re-derivation of 3 reported parapet-tangle offenders.

Own implementation, own geometry code. Reads overpasses.json directly.
Model frame: x east, z south, meters. p entries: [x, z, yDeckTop].
Deck structural depth below yDeckTop: 1.7 (c<=1), 0.5 (c==6), else 1.15.
Pier-risk rule under test: at 24 m stations along a chain, flag stations where
another chain's deck TOP lies in [soffit-30, soffit-1] and the station sits
laterally over that other deck (lateral dist to its centerline < its halfwidth).
"""
import json, math

BASE = "/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model/overpasses.json"
d = json.load(open(BASE))
el = d["el"]

def depth(c):
    return 1.7 if c <= 1 else (0.5 if c == 6 else 1.15)

def seg_closest(px, pz, ax, az, bx, bz):
    """closest point on segment ab to p; returns (dist2d, t, y-interp needs t)"""
    dx, dz = bx - ax, bz - az
    L2 = dx*dx + dz*dz
    if L2 == 0:
        t = 0.0
    else:
        t = max(0.0, min(1.0, ((px-ax)*dx + (pz-az)*dz) / L2))
    cx, cz = ax + t*dx, az + t*dz
    return math.hypot(px-cx, pz-cz), t

def closest_on_chain(px, pz, pts):
    """min lateral distance from (px,pz) to polyline, with interpolated deck-top y there"""
    best = (1e18, None)
    for i in range(len(pts)-1):
        a, b = pts[i], pts[i+1]
        dist, t = seg_closest(px, pz, a[0], a[1], b[0], b[1])
        if dist < best[0]:
            y = a[2] + t*(b[2]-a[2])
            best = (dist, y)
    return best

def stations(pts, step=24.0):
    """points every `step` m along the polyline, with interpolated deck-top y"""
    out = []
    acc = 0.0
    for i in range(len(pts)-1):
        a, b = pts[i], pts[i+1]
        seglen = math.hypot(b[0]-a[0], b[1]-a[1])
        if seglen == 0:
            continue
        while acc <= seglen:
            t = acc/seglen
            out.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]), a[2]+t*(b[2]-a[2])))
            acc += step
        acc -= seglen
    return out

def pier_conflicts(iA, iB, region=None, radius=400.0):
    """stations on chain A where chain B's deck top is in [soffitA-30, soffitA-1]
       and station lies over B's deck footprint. region=(x,z) filters near a spot."""
    A, B = el[iA], el[iB]
    dA = depth(A["c"]); hwB = B["w"]/2.0
    hits = []
    for (sx, sz, sy) in stations(A["p"]):
        if region and math.hypot(sx-region[0], sz-region[1]) > radius:
            continue
        lat, yB = closest_on_chain(sx, sz, B["p"])
        if lat >= hwB:
            continue
        soffit = sy - dA
        if soffit - 30.0 <= yB <= soffit - 1.0:
            hits.append((sx, sz, soffit - yB))
    return hits

print("=== chain metadata ===")
for i in (0, 1, 7, 8, 13, 54, 193):
    ch = el[i]
    xs = [p[0] for p in ch["p"]]; zs = [p[1] for p in ch["p"]]
    print(f"ch{i}: c={ch['c']} w={ch['w']} pts={len(ch['p'])} e={ch['e']} "
          f"x[{min(xs):.0f},{max(xs):.0f}] z[{min(zs):.0f},{max(zs):.0f}]")

print("\n=== OFFENDER 1: ch1 over ch0 near (-4282.4, 5658), claim: 30 stations, min clr 1.6 m ===")
h = pier_conflicts(1, 0, region=(-4282.4, 5658.0))
print(f"stations flagged in 400 m radius: {len(h)}, min clearance {min((c for *_ ,c in h), default=None)}")
if h:
    cs = sorted(c for *_, c in h)
    print(f"clearances: min {cs[0]:.2f} max {cs[-1]:.2f}")

print("\n=== OFFENDER 2: ch1 over ch0 near (-4869.2, 6207.1), claim: 19 stations, min clr 1.6 m ===")
h = pier_conflicts(1, 0, region=(-4869.2, 6207.1))
print(f"stations flagged in 400 m radius: {len(h)}")
if h:
    cs = sorted(c for *_, c in h)
    print(f"clearances: min {cs[0]:.2f} max {cs[-1]:.2f}")

# whole-run ch1-over-ch0 total for context
h_all = pier_conflicts(1, 0)
print(f"\nch1-over-ch0 flagged stations along entire chain: {len(h_all)}")
if h_all:
    xs = [x for x, _, _ in h_all]; zs = [z for _, z, _ in h_all]
    print(f"extent x[{min(xs):.0f},{max(xs):.0f}] z[{min(zs):.0f},{max(zs):.0f}], "
          f"min clr {min(c for *_, c in h_all):.2f}")

print("\n=== OFFENDER 3: ch54/ch193 over ch13/ch193 near (-3184.4, -821.3), claim: 12 stations, min clr 3.5 m ===")
tot = 0; minc = 1e9
for a, b in ((54, 13), (54, 193), (193, 13)):
    h = pier_conflicts(a, b, region=(-3184.4, -821.3))
    if h:
        mc = min(c for *_, c in h)
        minc = min(minc, mc)
        print(f"  ch{a} over ch{b}: {len(h)} stations, min clr {mc:.2f}")
        tot += len(h)
    else:
        print(f"  ch{a} over ch{b}: 0 stations")
print(f"total stations in region: {tot}, min clearance {minc if minc < 1e9 else 'n/a'}")

print("\n=== TWIN CHECK: ch7/ch8 near-parallel coincident run (claimed twin, overlap > 60 m) ===")
A, B = el[7], el[8]
hwA, hwB = A["w"]/2.0, B["w"]/2.0
twin_len = 0.0
n_over = 0
for (sx, sz, sy) in stations(A["p"], 12.0):
    lat, yB = closest_on_chain(sx, sz, B["p"])
    if lat < hwA + hwB and abs(sy - yB) < 2.5:
        twin_len += 12.0
        n_over += 1
print(f"ch7 stations overlapping ch8 deck (lat < hwA+hwB, |dy|<2.5): {n_over}, "
      f"approx coincident length {twin_len:.0f} m")
