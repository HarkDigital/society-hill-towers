#!/usr/bin/env python3
"""Audit: parapet tangles where elevated decks overlap or meet, plus
pier-through-deck risks. Reads overpasses.json (el chains), emits JSON report.

Model frame: x = east, z = south, meters.
"""
import json, math, sys, collections

BASE = "/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model"
data = json.load(open(BASE + "/overpasses.json"))
chains = data["el"]

def depth(c):
    if c <= 1: return 1.7
    if c == 6: return 0.5
    return 1.15

# ---------- build segment list ----------
# seg: (chain_idx, seg_idx, ax,az,ay, bx,bz,by, dirx,dirz, length, station0)
segs = []
chain_stations = []  # per chain: cumulative arclength at each point
for ci, ch in enumerate(chains):
    p = ch["p"]
    st = [0.0]
    for i in range(len(p) - 1):
        ax, az, ay = p[i][0], p[i][1], p[i][2]
        bx, bz, by = p[i+1][0], p[i+1][1], p[i+1][2]
        dx, dz = bx - ax, bz - az
        L = math.hypot(dx, dz)
        st.append(st[-1] + L)
        if L < 1e-6:
            continue
        segs.append((ci, i, ax, az, ay, bx, bz, by, dx / L, dz / L, L, st[-2]))
    chain_stations.append(st)

maxhw = max(ch["w"] for ch in chains) / 2.0
REACH = 2 * maxhw + 1.0

# ---------- spatial grid over segments ----------
CELL = 100.0
grid = collections.defaultdict(list)
def cells_for_bbox(x0, z0, x1, z1):
    for gx in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
        for gz in range(int(math.floor(z0 / CELL)), int(math.floor(z1 / CELL)) + 1):
            yield (gx, gz)
for si, s in enumerate(segs):
    x0, x1 = min(s[2], s[5]), max(s[2], s[5])
    z0, z1 = min(s[3], s[6]), max(s[3], s[6])
    for cell in cells_for_bbox(x0 - REACH, z0 - REACH, x1 + REACH, z1 + REACH):
        grid[cell].append(si)

def seg_seg_closest(a, b):
    """2D closest approach of two segments; returns (dist, s, t) params in [0,1]."""
    p1x, p1z = a[2], a[3]; d1x, d1z = a[5] - a[2], a[6] - a[3]
    p2x, p2z = b[2], b[3]; d2x, d2z = b[5] - b[2], b[6] - b[3]
    rx, rz = p1x - p2x, p1z - p2z
    A = d1x * d1x + d1z * d1z
    E = d2x * d2x + d2z * d2z
    F = d2x * rx + d2z * rz
    C = d1x * rx + d1z * rz
    B = d1x * d2x + d1z * d2z
    den = A * E - B * B
    s = 0.0 if den < 1e-12 else max(0.0, min(1.0, (B * F - C * E) / den))
    t = (B * s + F) / E if E > 1e-12 else 0.0
    if t < 0.0:
        t = 0.0; s = max(0.0, min(1.0, -C / A)) if A > 1e-12 else 0.0
    elif t > 1.0:
        t = 1.0; s = max(0.0, min(1.0, (B - C) / A)) if A > 1e-12 else 0.0
    qx = p1x + d1x * s - (p2x + d2x * t)
    qz = p1z + d1z * s - (p2z + d2z * t)
    return math.hypot(qx, qz), s, t

# shared endpoints between chains (chains that connect end-to-end)
def endpoints(ch):
    return [tuple(ch["p"][0][:2]), tuple(ch["p"][-1][:2])]
shared = set()  # frozenset({ci,cj}) that share an endpoint within 0.25 m
epindex = collections.defaultdict(list)
for ci, ch in enumerate(chains):
    for ep in endpoints(ch):
        epindex[(round(ep[0] / 0.5), round(ep[1] / 0.5))].append(ci)
for key, lst in epindex.items():
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if lst[i] != lst[j]:
                shared.add(frozenset((lst[i], lst[j])))

# ---------- find deck-overlap events ----------
events = []  # (mx, mz, my, ci, cj, dy, cosang, stA, stB, sharednode)
pairs_checked = set()
for cell, lst in grid.items():
    for ii in range(len(lst)):
        for jj in range(ii + 1, len(lst)):
            si, sj = lst[ii], lst[jj]
            if si > sj: si, sj = sj, si
            key = (si, sj)
            if key in pairs_checked:
                continue
            pairs_checked.add(key)
            a, b = segs[si], segs[sj]
            if a[0] == b[0]:
                continue
            hwa, hwb = chains[a[0]]["w"] / 2.0, chains[b[0]]["w"] / 2.0
            lim = hwa + hwb
            # quick bbox reject
            if min(a[2], a[5]) - lim > max(b[2], b[5]) or min(b[2], b[5]) - lim > max(a[2], a[5]):
                continue
            if min(a[3], a[6]) - lim > max(b[3], b[6]) or min(b[3], b[6]) - lim > max(a[3], a[6]):
                continue
            d, s, t = seg_seg_closest(a, b)
            if d >= lim:
                continue
            ya = a[4] + (a[7] - a[4]) * s
            yb = b[4] + (b[7] - b[4]) * t
            dy = ya - yb
            if abs(dy) >= 2.5:
                continue
            mx = (a[2] + (a[5] - a[2]) * s + b[2] + (b[5] - b[2]) * t) / 2.0
            mz = (a[3] + (a[6] - a[3]) * s + b[3] + (b[6] - b[3]) * t) / 2.0
            cosang = abs(a[8] * b[8] + a[9] * b[9])
            stA = a[11] + a[10] * s
            stB = b[11] + b[10] * t
            sh = frozenset((a[0], b[0])) in shared
            events.append((mx, mz, (ya + yb) / 2.0, a[0], b[0], dy, cosang, stA, stB, sh))

# ---------- cluster events (merge within 40 m) ----------
MERGE = 40.0
parent = list(range(len(events)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
def union(i, j):
    ri, rj = find(i), find(j)
    if ri != rj: parent[rj] = ri
egrid = collections.defaultdict(list)
for ei, ev in enumerate(events):
    egrid[(int(ev[0] // MERGE), int(ev[1] // MERGE))].append(ei)
for (gx, gz), lst in egrid.items():
    for dgx in (0, 1):
        for dgz in (-1, 0, 1):
            if dgx == 0 and dgz < 0: continue
            other = egrid.get((gx + dgx, gz + dgz))
            if not other: continue
            for ei in lst:
                for ej in other:
                    if ei >= ej and dgx == 0 and dgz == 0: continue
                    a, b = events[ei], events[ej]
                    if (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= MERGE * MERGE:
                        union(ei, ej)

clusters = collections.defaultdict(list)
for ei in range(len(events)):
    clusters[find(ei)].append(ei)

# ---------- classify regions ----------
regions = []
for root, eids in clusters.items():
    evs = [events[e] for e in eids]
    cx = sum(e[0] for e in evs) / len(evs)
    cz = sum(e[1] for e in evs) / len(evs)
    cy = sum(e[2] for e in evs) / len(evs)
    inv_chains = set()
    for e in evs:
        inv_chains.add(e[3]); inv_chains.add(e[4])
    # per chain-pair stats
    pairstats = {}
    for e in evs:
        key = (min(e[3], e[4]), max(e[3], e[4]))
        st = pairstats.setdefault(key, {"cos": [], "stA": [], "stB": [], "dy": [], "shared": e[9]})
        st["cos"].append(e[6])
        (st["stA"] if key[0] == min(e[3], e[4]) else st["stB"])  # noop clarity
        if e[3] == key[0]:
            st["stA"].append(e[7]); st["stB"].append(e[8])
        else:
            st["stA"].append(e[8]); st["stB"].append(e[7])
        st["dy"].append(abs(e[5]))
    # junction-mouth check: endpoint with kind 1 of an involved chain inside region
    junction_hits = []
    for ci in inv_chains:
        ch = chains[ci]
        for end_i, pt in ((0, ch["p"][0]), (1, ch["p"][-1])):
            if ch.get("e", [0, 0])[end_i] != 1:
                continue
            if any((pt[0] - e[0]) ** 2 + (pt[1] - e[1]) ** 2 <= MERGE * MERGE for e in evs):
                junction_hits.append((ci, end_i))
    # twins check
    twin_pairs = []
    for key, st in pairstats.items():
        meancos = sum(st["cos"]) / len(st["cos"])
        ovl = max(max(st["stA"]) - min(st["stA"]), max(st["stB"]) - min(st["stB"]))
        if meancos > 0.9 and ovl > 60.0:
            twin_pairs.append((key, meancos, ovl))
    all_shared = all(st["shared"] for st in pairstats.values())
    if junction_hits:
        cls = "junction_mouth"
    elif twin_pairs:
        cls = "twins"
    else:
        cls = "braid"
    maxovl = 0.0
    for key, st in pairstats.items():
        maxovl = max(maxovl, max(st["stA"]) - min(st["stA"]), max(st["stB"]) - min(st["stB"]))
    mindy = min(min(st["dy"]) for st in pairstats.values())
    regions.append({
        "cls": cls, "x": cx, "z": cz, "y": cy,
        "chains": sorted(inv_chains), "npairs": len(pairstats),
        "nevents": len(evs), "junctions": junction_hits,
        "twins": twin_pairs, "overlap_len": maxovl, "min_dy": mindy,
        "all_shared_node": all_shared,
    })

# ---------- pier-through-deck risks ----------
STEP = 24.0
pier_flags = []  # (x, z, ci_upper, cj_lower, soffit, y_lower)
for ci, ch in enumerate(chains):
    p = ch["p"]
    st = chain_stations[ci]
    total = st[-1]
    dep = depth(ch["c"])
    s_target = 0.0
    seg_i = 0
    while s_target <= total + 1e-9:
        while seg_i < len(st) - 2 and st[seg_i + 1] < s_target:
            seg_i += 1
        L = st[seg_i + 1] - st[seg_i]
        f = 0.0 if L < 1e-9 else (s_target - st[seg_i]) / L
        f = max(0.0, min(1.0, f))
        px = p[seg_i][0] + (p[seg_i + 1][0] - p[seg_i][0]) * f
        pz = p[seg_i][1] + (p[seg_i + 1][1] - p[seg_i][1]) * f
        py = p[seg_i][2] + (p[seg_i + 1][2] - p[seg_i][2]) * f
        soffit = py - dep
        lower = soffit - 30.0
        # query grid for nearby other-chain segments
        best = {}
        gx0, gz0 = int(math.floor(px / CELL)), int(math.floor(pz / CELL))
        cand = grid.get((gx0, gz0), ())
        for si in cand:
            s = segs[si]
            if s[0] == ci:
                continue
            hw = chains[s[0]]["w"] / 2.0
            # point-to-segment
            dx, dz = s[5] - s[2], s[6] - s[3]
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - s[2]) * dx + (pz - s[3]) * dz) / L2))
            qx, qz = s[2] + dx * t, s[3] + dz * t
            d = math.hypot(px - qx, pz - qz)
            if d >= hw:
                continue
            yq = s[4] + (s[7] - s[4]) * t
            if lower < yq < soffit - 1.0:
                if s[0] not in best or d < best[s[0]][0]:
                    best[s[0]] = (d, yq)
        for cj, (d, yq) in best.items():
            pier_flags.append((px, pz, ci, cj, soffit, yq))
        s_target += STEP

# cluster pier flags (40 m merge) for reporting
pparent = list(range(len(pier_flags)))
def pfind(i):
    while pparent[i] != i:
        pparent[i] = pparent[pparent[i]]
        i = pparent[i]
    return i
pgrid = collections.defaultdict(list)
for pi, pf in enumerate(pier_flags):
    pgrid[(int(pf[0] // MERGE), int(pf[1] // MERGE))].append(pi)
for (gx, gz), lst in pgrid.items():
    for dgx in (0, 1):
        for dgz in (-1, 0, 1):
            if dgx == 0 and dgz < 0: continue
            other = pgrid.get((gx + dgx, gz + dgz))
            if not other: continue
            for pi in lst:
                for pj in other:
                    if pi >= pj and dgx == 0 and dgz == 0: continue
                    a, b = pier_flags[pi], pier_flags[pj]
                    if (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= MERGE * MERGE:
                        ra, rb = pfind(pi), pfind(pj)
                        if ra != rb: pparent[rb] = ra
pclusters = collections.defaultdict(list)
for pi in range(len(pier_flags)):
    pclusters[pfind(pi)].append(pi)
pier_regions = []
for root, pids in pclusters.items():
    pts = [pier_flags[i] for i in pids]
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    uppers = sorted(set(p[2] for p in pts))
    lowers = sorted(set(p[3] for p in pts))
    clear = min(p[4] - p[5] for p in pts)
    pier_regions.append({"x": cx, "z": cz, "n": len(pts),
                         "uppers": uppers, "lowers": lowers, "min_clear": clear})

out = {
    "n_chains": len(chains), "n_segments": len(segs),
    "n_overlap_events": len(events),
    "regions": regions, "pier_stations": len(pier_flags),
    "pier_regions": pier_regions,
}
json.dump(out, open(BASE + "/../.audit/parapet_tangle_report.json", "w"), indent=1)

cnt = collections.Counter(r["cls"] for r in regions)
print("regions:", len(regions), dict(cnt))
print("pier stations:", len(pier_flags), "pier regions:", len(pier_regions))
