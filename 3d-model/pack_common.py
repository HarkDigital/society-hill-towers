#!/usr/bin/env python3
"""Shared guards for the building packers (Round 71): the stacked-record dedupe and the
coplanar-wall inset that pack_wide.py has carried since Round 5x, now used by pack_city.py
and pack_outskirts.py too, so no tier draws two walls on one plane facing the same way
(Mike, Sep 16: a tower at East Falls still flickered; the far ring had no guard at all).

Records are tuples (cx, cz, area, h, minH, fields) with fields[1] the ring, a list of
(x, z); nudge_coplanar insets rings in place. Stdlib only."""
import math

# Stacked building:part ways on one footprint (OSM models several towers as a pile of
# coincident prisms of different heights: the Comcast Technology Center has nine) draw
# coplanar walls that z-fight from every angle. Among records whose centroids sit within
# 2.5 m, whose areas agree within 20 % and whose height ranges overlap, only the tallest
# is packed; the shorter ones were hidden inside it anyway.
def dedupe_stacked(items):
    """items: [(cx, cz, area, h, minH, rec)]; returns the kept recs in input order."""
    grid = {}
    for idx, it in enumerate(items):
        grid.setdefault((int(it[0] // 20), int(it[1] // 20)), []).append(idx)
    drop = set()
    for idx, it in enumerate(items):
        if idx in drop: continue
        kx, kz = int(it[0] // 20), int(it[1] // 20)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for j in grid.get((kx + dx, kz + dz), ()):
                    if j == idx or j in drop: continue
                    q = items[j]
                    if math.hypot(q[0] - it[0], q[1] - it[1]) < 2.5 and min(it[2], q[2]) > 0.8 * max(it[2], q[2]) \
                            and min(it[3], q[3]) - max(it[4], q[4]) > 1.0:
                        drop.add(j if q[3] <= it[3] else idx)
    return [it for idx, it in enumerate(items) if idx not in drop], len(drop)

# Two records whose walls lie on one plane facing the same way (a building:part sharing
# its street face with the outline it sits in, a wing part flush with the tower's face,
# two neighbouring outlines drawn over each other) z-fight over the whole overlap, which
# on a tower is a speckled two-thirds of the facade. The smaller record of every such
# pair is inset 0.4 m (a chain gets 0.4 m more per link), so its wall sits just inside
# the larger one's: hidden where they overlap, imperceptibly recessed where it rises above.
def inset_ring(ring, d):
    n = len(ring)
    a2 = sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1] for i in range(n))
    sgn = 1.0 if a2 > 0 else -1.0
    out = []
    for i in range(n):
        p0, p1, p2 = ring[i - 1], ring[i], ring[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1]); e2 = (p2[0] - p1[0], p2[1] - p1[1])
        L1 = math.hypot(*e1) or 1e-9; L2 = math.hypot(*e2) or 1e-9
        u1 = (e1[0] / L1, e1[1] / L1); u2 = (e2[0] / L2, e2[1] / L2)
        n1 = (-u1[1] * sgn, u1[0] * sgn); n2 = (-u2[1] * sgn, u2[0] * sgn)      # inward normals
        dot = n1[0] * n2[0] + n1[1] * n2[1]
        if 1 + dot > 0.3:
            k = d / (1 + dot); out.append((p1[0] + (n1[0] + n2[0]) * k, p1[1] + (n1[1] + n2[1]) * k))
        else:
            out.append((p1[0] + n1[0] * d, p1[1] + n1[1] * d))
    return out

def nudge_coplanar(items, d=0.4):
    """items: [(cx, cz, area, h, minH, fields)] with fields[1] the ring; insets rings in place.
    d is the inset per link: it must exceed the packer's coordinate grid or the int16 rounding
    cancels it (0.4 on pack_wide's 0.2 m grid; pack_city and pack_outskirts pass 1.5 times theirs)."""
    grid = {}; segs = []
    for idx, it in enumerate(items):
        ring = it[5][1]; n = len(ring)
        a2 = sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1] for i in range(n))
        ccw = a2 > 0
        for j in range(n):
            a, b = ring[j], ring[(j + 1) % n]
            dx, dz = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dz)
            if L < 0.5: continue
            ux, uz = dx / L, dz / L
            nx, nz = (uz, -ux) if ccw else (-uz, ux)
            sid = len(segs); segs.append((idx, a, b, ux, uz, nx, nz, L))
            for cx in range(int(min(a[0], b[0]) // 15), int(max(a[0], b[0]) // 15) + 1):
                for cz in range(int(min(a[1], b[1]) // 15), int(max(a[1], b[1]) // 15) + 1):
                    grid.setdefault((cx, cz), []).append(sid)
    pairs = set()
    for ids in grid.values():
        for x in range(len(ids)):
            s1 = segs[ids[x]]
            for y in range(x + 1, len(ids)):
                s2 = segs[ids[y]]
                if s1[0] == s2[0]: continue
                if abs(s1[3] * s2[4] - s1[4] * s2[3]) > 0.02 or s1[5] * s2[5] + s1[6] * s2[6] < 0.98: continue
                if abs((s2[1][0] - s1[1][0]) * s1[5] + (s2[1][1] - s1[1][1]) * s1[6]) > 0.12: continue
                t2a = (s2[1][0] - s1[1][0]) * s1[3] + (s2[1][1] - s1[1][1]) * s1[4]
                t2b = (s2[2][0] - s1[1][0]) * s1[3] + (s2[2][1] - s1[1][1]) * s1[4]
                if min(s1[7], max(t2a, t2b)) - max(0.0, min(t2a, t2b)) < 1.0: continue
                A, B = items[s1[0]], items[s2[0]]
                if min(A[3], B[3]) - max(A[4], B[4]) < 1.0: continue
                pairs.add((s1[0], s2[0]) if A[2] >= B[2] else (s2[0], s1[0]))
    insets = {}
    for big, small in sorted(pairs, key=lambda p: -items[p[0]][2]):
        insets[small] = max(insets.get(small, 0.0), insets.get(big, 0.0) + d)   # over one grid quantum: an inset the int16 grid could round away is no inset
    for idx, d in insets.items():
        items[idx][5][1] = inset_ring(items[idx][5][1], d)
    return len(insets)
