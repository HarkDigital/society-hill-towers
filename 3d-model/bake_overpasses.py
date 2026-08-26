#!/usr/bin/env python3
"""Bake elevated roads (bridges/viaducts/ramps) and sunken expressways from the raw
OSM dumps into overpasses.json for the app.

The packed road formats carry no bridge/tunnel/layer tags, so this reads the raw
Overpass dumps (osm_wide_raw.json, osm_south_raw.json, city_tiles/*.json), chains
tagged ways into corridors, solves a slope-limited height profile per chain against
the DEM, and emits:
  el:  elevated chains  [{c: clsCode, w: width_m, p: [[x, z, yTop], ...]}, ...]
  sk:  sunken chains    (same shape; y = roadway surface, below grade)
  cor: open-cut corridor runs for sunken motorways (the Vine Street cut):
       [[[x, z, floorY, halfW], ...], ...]

Height model (model frame, y = 0 at the towers' site):
  grade      = DEM (clamped at the water plane like the app's siteY)
  elevated   = grade + 6.8 (layer 1) / 12.5 (layer 2) / 17.5 (layer 3+),
               but only grade + 0.45 where everything crossing beneath is itself
               sunken (streets crossing the Vine cut / core I-95 trench stay flat);
               over rivers the deck clears water + 20 (motorway) / +13 (streets)
  sunken     = grade - 8
  ramps      = ends slope-limited (4.2% motorway / 5% street / 9% footbridge) down
               to grade where a chain meets plain roads, and pinned to the junction
               height where it meets an already-solved chain (ramp continuity).
Custom-built bridges (Ben Franklin, Walt Whitman) are skipped by name; chains whose
ends meet them hold their height instead of ramping down.
"""
import json, math, os, glob, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAT0, LON0 = 39.945473644755005, -75.14474803850973
COS0 = math.cos(math.radians(LAT0))
def to_xz(lat, lon):
    return ((lon - LON0) * 111320 * COS0, -(lat - LAT0) * 110574)

ROAD_W = {"motorway": 16, "trunk": 16, "motorway_link": 8, "trunk_link": 8,
          "primary": 13, "secondary": 11, "tertiary": 9,
          "primary_link": 8, "secondary_link": 7, "tertiary_link": 7,
          "residential": 7, "unclassified": 7, "living_street": 6, "pedestrian": 5,
          "footway": 3, "path": 3, "cycleway": 3}
CLS = {"motorway": 0, "motorway_link": 0, "trunk": 1, "trunk_link": 1,
       "primary": 2, "primary_link": 2, "secondary": 3, "secondary_link": 3,
       "tertiary": 4, "tertiary_link": 4, "residential": 5, "living_street": 5,
       "unclassified": 5, "pedestrian": 6, "footway": 6, "path": 6, "cycleway": 6}
MOTOR = {"motorway", "motorway_link", "trunk", "trunk_link"}
CORE = (-640, 770, -520, 850)
SKIP_NAMES = ("Benjamin Franklin Bridge", "Walt Whitman Bridge")

# ---------------------------------------------------------------- load raw dumps
files = [os.path.join(HERE, "osm_wide_raw.json"), os.path.join(HERE, "osm_south_raw.json")]
files += sorted(glob.glob(os.path.join(HERE, "city_tiles", "*.json")))
ways = {}          # id -> {nds, tags}
need_nodes = set()
for fp in files:
    if not os.path.exists(fp):
        continue
    try:
        d = json.load(open(fp))
    except Exception as e:
        print(f"skip {fp}: {e}"); continue
    for el in d.get("elements", []):
        if el["type"] != "way" or el["id"] in ways:
            continue
        t = el.get("tags") or {}
        hw = t.get("highway")
        if not hw or hw not in CLS:
            continue
        if t.get("area") == "yes":
            continue
        # footways only matter when they are bridges (pedestrian overpasses)
        if CLS[hw] == 6 and not t.get("bridge"):
            continue
        ways[el["id"]] = {"nds": el["nodes"], "tags": t}
        need_nodes.update(el["nodes"])
nodes = {}
for fp in files:
    if not os.path.exists(fp):
        continue
    try:
        d = json.load(open(fp))
    except Exception:
        continue
    for el in d.get("elements", []):
        if el["type"] == "node" and el["id"] in need_nodes and el["id"] not in nodes:
            nodes[el["id"]] = to_xz(el["lat"], el["lon"])
print(f"{len(ways)} highway ways, {len(nodes)}/{len(need_nodes)} nodes resolved")

# ---------------------------------------------------------------- DEM (mirror of demAbs)
def load_dem(name):
    p = os.path.join(HERE, name)
    return json.load(open(p)) if os.path.exists(p) else None
DEMS_ALL = [(load_dem("dem.json"), 8.34), (load_dem("dem_wide.json"), 3.2),
            (load_dem("dem_south.json"), 3.2), (load_dem("dem_city.json"), 4.0)]
def sample_dem(G, x, z, fb):
    fx = (x - G["x0"]) / G["cell"]; fz = (z - G["z0"]) / G["cell"]
    if fx < 0 or fz < 0 or fx > G["nx"] - 1 or fz > G["nz"] - 1:
        return None
    i = max(0, min(G["nx"] - 2, int(fx))); j = max(0, min(G["nz"] - 2, int(fz)))
    tx = max(0.0, min(1.0, fx - i)); tz = max(0.0, min(1.0, fz - j))
    r0, r1 = G["rows"][j], G["rows"][j + 1]
    v = lambda a: fb if a is None else a
    a = v(r0[i]) * (1 - tx) + v(r0[i + 1]) * tx
    b = v(r1[i]) * (1 - tx) + v(r1[i + 1]) * tx
    return a * (1 - tz) + b * tz
def dem_abs(x, z):
    for G, fb in DEMS_ALL:
        if G:
            vv = sample_dem(G, x, z, fb)
            if vv is not None:
                return vv
    G = DEMS_ALL[1][0]
    if G:
        cx = max(G["x0"], min(G["x0"] + G["cell"] * (G["nx"] - 1), x))
        cz = max(G["z0"], min(G["z0"] + G["cell"] * (G["nz"] - 1), z))
        return sample_dem(G, cx, cz, 0) or 8.34
    return 8.34

scene = json.load(open(os.path.join(HERE, "scene.json")))
tc = [sum(t["centroid"][i] for t in scene["towers"]) / 3 for i in (0, 1)]
DATUM = dem_abs(tc[0], tc[1])
WATER = 0.5 - DATUM
BULK = 2.8 - DATUM
def dem_y(x, z): return dem_abs(x, z) - DATUM

DEL_BANK = [[13500, -21700], [10500, -18500], [7300, -14500], [4300, -10500], [2500, -7200],
            [1500, -4480], [900, -2600], [450, -1500], [404, -520], [345, 850], [700, 2200],
            [1300, 3600], [2000, 4800], [2600, 6400], [3400, 7600], [5200, 9700]]
SCHUYLKILL = [[-8500, -11500], [-7700, -9400], [-6900, -7700], [-5600, -5300], [-4700, -3300],
              [-4100, -1600], [-4300, -400], [-4500, 1100], [-4200, 2600], [-3900, 4200],
              [-3700, 5600], [-3860, 7240]]
def x_del(z):
    for i in range(len(DEL_BANK) - 1):
        a, b = DEL_BANK[i], DEL_BANK[i + 1]
        if a[1] <= z <= b[1]:
            t = (z - a[1]) / max(1e-6, b[1] - a[1])
            return a[0] + (b[0] - a[0]) * t
    return DEL_BANK[0][0] if z < DEL_BANK[0][1] else DEL_BANK[-1][0]
def east_of_del(x, z): return x > x_del(z)
def near_schuylkill(x, z, r=260):
    b = 1e18
    for i in range(len(SCHUYLKILL) - 1):
        A, B = SCHUYLKILL[i], SCHUYLKILL[i + 1]
        dx, dz = B[0] - A[0], B[1] - A[1]
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((x - A[0]) * dx + (z - A[1]) * dz) / L2))
        ex, ez = A[0] + dx * t - x, A[1] + dz * t - z
        b = min(b, ex * ex + ez * ez)
    return b < r * r
def river_corridor(x, z): return east_of_del(x, z) or near_schuylkill(x, z)
def grade(x, z):
    y = dem_y(x, z)
    if y >= WATER + 0.6:
        return y
    return BULK if east_of_del(x, z) else WATER + 0.45
def over_water(x, z):
    return dem_y(x, z) < WATER + 0.6 and river_corridor(x, z)

# Front St line fit (for the existing core I-95 trench corridor)
fl = {"px": 140, "pz": 0, "dx": -0.167, "dz": 0.986, "nx": 0.986, "nz": 0.167}
fpts = [q for r in scene["roads"] if r.get("name") and "front street" in r["name"].lower() for q in r["pts"]]
if len(fpts) > 3:
    mx = sum(q[0] for q in fpts) / len(fpts); mz = sum(q[1] for q in fpts) / len(fpts)
    sxx = sxz = szz = 0.0
    for q in fpts:
        ax, az = q[0] - mx, q[1] - mz
        sxx += ax * ax; sxz += ax * az; szz += az * az
    ang = 0.5 * math.atan2(2 * sxz, sxx - szz)
    dx, dz = math.cos(ang), math.sin(ang)
    if dz < 0: dx, dz = -dx, -dz
    nx, nz = -dz, dx
    if nx < 0: nx, nz = -nx, -nz
    fl = {"px": mx, "pz": mz, "dx": dx, "dz": dz, "nx": nx, "nz": nz}
def in_core_trench(x, z):
    o = (x - fl["px"]) * fl["nx"] + (z - fl["pz"]) * fl["nz"]
    return 5 < o < 78 and -1250 < z < 1850

# ---------------------------------------------------------------- classify ways
def parse_layer(t):
    try:
        return int(str(t.get("layer", "0")).strip())
    except ValueError:
        return 0
W = {}
for wid, w in ways.items():
    t = w["tags"]
    pts = [nodes[n] for n in w["nds"] if n in nodes]
    if len(pts) < 2:
        continue
    hw = t["highway"]
    br = t.get("bridge") not in (None, "no")
    tu = t.get("tunnel") not in (None, "no")
    ly = parse_layer(t)
    if br and ly <= 0: ly = 1
    if tu and ly >= 0: ly = -1
    name = (t.get("name") or "")
    W[wid] = {"pts": pts, "nds": [n for n in w["nds"] if n in nodes], "cls": CLS[hw],
              "w": ROAD_W.get(hw, 7), "mo": hw in MOTOR, "layer": ly,
              "elev": (br or ly > 0) and not tu, "sunk": tu or ly < 0, "tunnel": tu,
              "skipname": any(s in name for s in SKIP_NAMES)}

# endpoint connectivity over all rendered ways
ends = {}
for wid, w in W.items():
    for e, n in ((0, w["nds"][0]), (1, w["nds"][-1])):
        ends.setdefault(n, []).append((wid, e))

# segment hash for crossing detection
seg_grid = {}
SEG_CELL = 40
def seg_add(wid, a, b):
    x0, x1 = sorted((a[0], b[0])); z0, z1 = sorted((a[1], b[1]))
    for gx in range(int(x0 // SEG_CELL), int(x1 // SEG_CELL) + 1):
        for gz in range(int(z0 // SEG_CELL), int(z1 // SEG_CELL) + 1):
            seg_grid.setdefault((gx, gz), []).append((wid, a[0], a[1], b[0], b[1]))
for wid, w in W.items():
    for i in range(len(w["pts"]) - 1):
        seg_add(wid, w["pts"][i], w["pts"][i + 1])

def crossings_under(w):
    """Way ids of lower-layer ways crossing beneath an elevated way."""
    out = set()
    my = w["layer"]
    step = 8.0
    for i in range(len(w["pts"]) - 1):
        a, b = w["pts"][i], w["pts"][i + 1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz)
        if L < 0.05: continue
        ux, uz = dx / L, dz / L
        k = 0.0
        while k <= L:
            x, z = a[0] + ux * k, a[1] + uz * k
            cell = seg_grid.get((int(x // SEG_CELL), int(z // SEG_CELL)), ())
            for (oid, ax, az, bx, bz) in cell:
                if oid == wid_current or oid not in W: continue
                o = W[oid]
                if o["layer"] >= my: continue
                sdx, sdz = bx - ax, bz - az
                L2 = sdx * sdx + sdz * sdz or 1e-9
                t = max(0.0, min(1.0, ((x - ax) * sdx + (z - az) * sdz) / L2))
                ex, ez = ax + sdx * t - x, az + sdz * t - z
                if ex * ex + ez * ez > ((w["w"] + o["w"]) / 2 + 1) ** 2: continue
                sl = math.hypot(sdx, sdz)
                if sl > 0.05 and abs(ux * sdx / sl + uz * sdz / sl) > 0.906: continue  # parallel
                out.add(oid)
            k += step
    return out

# ---------------------------------------------------------------- chaining
used = set()
def chain_from(seed, want, fill_len):
    """Grow a chain of `want`-flagged ways from seed, absorbing short plain gaps."""
    c = [seed]; used.add(seed)
    for direction in (1, 0):
        while True:
            wid = c[-1] if direction else c[0]
            w = W[wid]
            # orientation bookkeeping happens at assembly; here track by endpoint node
            node = None
            # find the free end node of the current chain end
            if direction:
                prev = W[c[-2]] if len(c) > 1 else None
                n0, n1 = w["nds"][0], w["nds"][-1]
                node = n1 if (prev is None or n0 in (prev["nds"][0], prev["nds"][-1])) else n0
                if prev is None and len(c) == 1:
                    node = n1
            else:
                nxt = W[c[1]] if len(c) > 1 else None
                n0, n1 = w["nds"][0], w["nds"][-1]
                node = n0 if (nxt is None or n1 in (nxt["nds"][0], nxt["nds"][-1])) else n1
            cand = [oid for (oid, e) in ends.get(node, []) if oid != wid and oid not in used
                    and oid in W and W[oid][want] and not W[oid]["skipname"]]
            if len(cand) == 1:
                c.append(cand[0]) if direction else c.insert(0, cand[0])
                used.add(cand[0]); continue
            if len(cand) > 1:
                same = [o for o in cand if W[o]["cls"] == w["cls"]]
                if len(same) == 1:
                    c.append(same[0]) if direction else c.insert(0, same[0])
                    used.add(same[0]); continue
                break
            # gap fill through plain ways (embankments between viaduct sections)
            lim = fill_len if w["mo"] else 45
            path = fill_path(node, want, lim, w["mo"])
            if path:
                for p in (path if direction else reversed(path)):
                    used.add(p)
                    c.append(p) if direction else c.insert(0, p)
                continue
            break
    return c

def fill_path(node, want, lim, mo):
    """BFS through un-flagged plain ways to reach another `want` way. Returns the
    plain path + the reached way, or None."""
    from collections import deque
    q = deque([(node, [], 0.0)])
    seen = {node}
    while q:
        n, path, dist = q.popleft()
        for (oid, e) in ends.get(n, ()):
            if oid in used or oid not in W or W[oid]["skipname"]: continue
            o = W[oid]
            if o[want] and path:
                return path + [oid]
            if o["elev"] or o["sunk"]: continue
            if mo and not o["mo"]: continue
            if not mo and o["cls"] > 5: continue
            L = sum(math.hypot(o["pts"][i + 1][0] - o["pts"][i][0], o["pts"][i + 1][1] - o["pts"][i][1])
                    for i in range(len(o["pts"]) - 1))
            if dist + L > lim or len(path) >= 3: continue
            far = o["nds"][-1] if o["nds"][0] == n else o["nds"][0]
            if far in seen: continue
            seen.add(far)
            q.append((far, path + [oid], dist + L))
    return None

def assemble(cids):
    """Order way point lists head-to-tail into one polyline + per-vertex way id."""
    pts = list(W[cids[0]]["pts"]); src = [cids[0]] * len(pts)
    for wid in cids[1:]:
        p = list(W[wid]["pts"])
        if math.hypot(pts[-1][0] - p[0][0], pts[-1][1] - p[0][1]) > math.hypot(pts[-1][0] - p[-1][0], pts[-1][1] - p[-1][1]):
            p.reverse()
        pts += p[1:]; src += [wid] * (len(p) - 1)
    # for the first way, check orientation against the second
    return pts, src

def order_chain(cids):
    if len(cids) < 2:
        return cids
    return cids

sunk_chains, elev_chains = [], []
# sunk first (motorway family only), so elevated ends can pin to them
for wid in sorted(W, key=lambda i: -len(W[i]["pts"])):
    w = W[wid]
    if wid in used or not w["sunk"] or not w["mo"] or w["skipname"]:
        continue
    cids = chain_from(wid, "sunk", 360)
    sunk_chains.append(cids)
for wid in sorted(W, key=lambda i: (W[i]["cls"], -sum(1 for _ in W[i]["pts"]))):
    w = W[wid]
    if wid in used or not w["elev"] or w["skipname"]:
        continue
    cids = chain_from(wid, "elev", 330)
    elev_chains.append(cids)
print(f"{len(sunk_chains)} sunken chains, {len(elev_chains)} elevated chains")

# lift-0 detection: elevated ways whose under-crossings are all sunken
wid_current = None
grade_bridge = set()
for wid, w in W.items():
    if not w["elev"] or w["skipname"]: continue
    wid_current = wid
    cr = crossings_under(w)
    if not cr:
        # no mapped crossing: check the core I-95 trench corridor directly
        if any(in_core_trench(p[0], p[1]) for p in w["pts"]):
            grade_bridge.add(wid)
        continue
    if all(W[c]["sunk"] or any(in_core_trench(p[0], p[1]) for p in W[c]["pts"][:2]) for c in cr):
        grade_bridge.add(wid)
wid_current = None
print(f"{len(grade_bridge)} elevated ways stay at grade (over sunken cuts)")

# ---------------------------------------------------------------- profiles
LIFT_BY_LAYER = {1: 6.8, 2: 12.5, 3: 17.5, 4: 17.5}
node_y = {}      # solved junction heights
def solve_chain(cids, sunk):
    pts, src = assemble(cids)
    # densify to <= 20 m, tracking source way + node ids at original vertices
    P = []          # [x, z, srcWid, nodeId|None]
    _, _ = pts, src
    orig_nodes = []
    ni = 0
    # rebuild the node list along the assembled line
    node_seq = list(W[cids[0]]["nds"])
    for wid in cids[1:]:
        seq = list(W[wid]["nds"])
        if seq[0] != node_seq[-1] and seq[-1] == node_seq[-1]:
            seq.reverse()
        elif seq[0] != node_seq[-1]:
            # assembly reversed the first way; recompute defensively
            if seq[-1] != node_seq[0] and seq[0] == node_seq[0]:
                node_seq.reverse()
            elif seq[-1] == node_seq[0]:
                node_seq.reverse(); seq.reverse()
        node_seq += seq[1:]
    if len(node_seq) != len(pts):
        node_seq = [None] * len(pts)   # fallback: no junction pinning mid-chain
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        P.append([a[0], a[1], src[i], node_seq[i]])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = int(L // 20)
        for j in range(1, k + 1):
            t = j / (k + 1)
            P.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, src[i], None])
    P.append([pts[-1][0], pts[-1][1], src[-1], node_seq[-1]])
    n = len(P)
    if n < 2:
        return None
    s = [0.0]
    for i in range(1, n):
        s.append(s[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    if s[-1] < 26 and not sunk:
        return None
    g = [grade(p[0], p[1]) for p in P]
    tgt = []
    for i, p in enumerate(P):
        w = W[p[2]]
        if sunk:
            tgt.append(g[i] - (8.5 if w["tunnel"] else 8.0))
        else:
            lift = 0.45 if p[2] in grade_bridge else LIFT_BY_LAYER.get(max(1, w["layer"]), 6.8)
            y = g[i] + lift
            if over_water(p[0], p[1]):
                y = max(y, WATER + (20 if w["cls"] == 0 else 13))
            tgt.append(y)
    # smooth targets (DEM noise)
    tgt = [tgt[0]] + [(tgt[i - 1] + tgt[i] + tgt[i + 1]) / 3 for i in range(1, n - 1)] + [tgt[-1]]
    cls0 = W[P[0][2]]["cls"]
    slope = 0.042 if cls0 <= 1 else (0.09 if cls0 == 6 else 0.055)
    # end constraints
    def end_constraint(idx):
        nid = P[idx][3]
        if nid is not None and nid in node_y:
            return node_y[nid]
        touch = ends.get(nid, ()) if nid is not None else ()
        if any(oid in W and W[oid]["skipname"] for (oid, e) in touch):
            return tgt[idx]                      # meets a custom bridge: stay high
        wset = set(cids)
        others = [oid for (oid, e) in touch if oid in W and oid not in wset]
        if others:
            return grade(P[idx][0], P[idx][1]) + 0.3   # meets plain roads: touch down
        return tgt[idx]                          # dead end (data edge): hold
    y = list(tgt)
    y[0] = end_constraint(0)
    y[-1] = end_constraint(n - 1)
    for i in range(1, n):
        d = (s[i] - s[i - 1]) * slope
        lo, hi = y[i - 1] - d, y[i - 1] + d
        yy = tgt[i] if i < n - 1 else y[i]
        y[i] = min(max(yy, lo), hi)
    for i in range(n - 2, -1, -1):
        d = (s[i + 1] - s[i]) * slope
        lo, hi = y[i + 1] - d, y[i + 1] + d
        y[i] = min(max(y[i], lo), hi)
    for i, p in enumerate(P):
        if p[3] is not None and p[3] not in node_y:
            node_y[p[3]] = y[i]
    return P, s, g, y

def simplify_profile(P, y, tol2d=0.9, toly=0.22):
    keep = [0, len(P) - 1]
    def dp(i0, i1):
        if i1 - i0 < 2: return
        ax, az, ay = P[i0][0], P[i0][1], y[i0]
        bx, bz, by = P[i1][0], P[i1][1], y[i1]
        dx, dz = bx - ax, bz - az
        L = math.hypot(dx, dz) or 1e-9
        best, bi = -1, -1
        for i in range(i0 + 1, i1):
            d2 = abs((P[i][0] - ax) * dz - (P[i][1] - az) * dx) / L
            t = ((P[i][0] - ax) * dx + (P[i][1] - az) * dz) / (L * L)
            dy = abs(y[i] - (ay + (by - ay) * max(0, min(1, t))))
            m = max(d2 / tol2d, dy / toly)
            if m > best: best, bi = m, i
        if best > 1:
            keep.append(bi); dp(i0, bi); dp(bi, i1)
    dp(0, len(P) - 1)
    keep = sorted(set(keep))
    return [[round(P[i][0], 1), round(P[i][1], 1), round(y[i], 2)] for i in keep]

def clip_core(prof):
    """Split a profile into runs outside the core box (the core paves its own)."""
    M = 35
    inb = lambda p: CORE[0] - M <= p[0] <= CORE[1] + M and CORE[2] - M <= p[1] <= CORE[3] + M
    runs, cur = [], []
    for i, p in enumerate(prof):
        keep = not inb(p) or (i > 0 and not inb(prof[i - 1])) or (i + 1 < len(prof) and not inb(prof[i + 1]))
        if keep: cur.append(p)
        else:
            if len(cur) > 1: runs.append(cur)
            cur = []
    if len(cur) > 1: runs.append(cur)
    return runs

out_el, out_sk, out_cor = [], [], []
sunk_solved = []
for cids in sunk_chains:
    r = solve_chain(cids, True)
    if not r: continue
    P, s, g, y = r
    if all(CORE[0] - 35 <= p[0] <= CORE[1] + 35 and CORE[2] - 35 <= p[1] <= CORE[3] + 35 for p in P):
        continue   # the core I-95 trench is built by the app already
    sunk_solved.append((P, s, g, y))
    prof = simplify_profile(P, y)
    for run in clip_core(prof):
        out_sk.append({"c": CLS_min(cids), "w": W[cids[0]]["w"], "p": run})

def CLS_min(cids):
    return min(W[c]["cls"] for c in cids)

# (function used before definition; simple re-run)
out_sk = []
for (P, s, g, y) in sunk_solved:
    prof = simplify_profile(P, y)
    cmin = 0
    for run in clip_core(prof):
        out_sk.append({"c": cmin, "w": 12, "p": run})

for cids in elev_chains:
    r = solve_chain(cids, False)
    if not r: continue
    P, s, g, y = r
    # drop chains that never rise meaningfully above grade (grade bridges keep 0.45)
    if max(y[i] - g[i] for i in range(len(P))) < 0.35:
        continue
    prof = simplify_profile(P, y)
    cmin = min(W[c]["cls"] for c in cids)
    wmax = max(W[c]["w"] for c in cids)
    for run in clip_core(prof):
        if sum(math.hypot(run[i + 1][0] - run[i][0], run[i + 1][1] - run[i][1]) for i in range(len(run) - 1)) < 22:
            continue
        out_el.append({"c": cmin, "w": wmax, "p": run})

# ---------------------------------------------------------------- Vine corridor
# open-cut runs: sunken samples that are (a) not tunnel-covered, (b) well below
# grade; paired across carriageways for a single wall-to-wall corridor
def corridor_runs():
    if not sunk_solved:
        return []
    # largest chain leads
    chains = sorted(sunk_solved, key=lambda r: -r[1][-1])
    lead = chains[0]
    others = chains[1:]
    runs, cur = [], []
    P, s, g, y = lead
    for i in range(len(P)):
        w = W[P[i][2]]
        depth = g[i] - y[i]
        opencut = (not w["tunnel"]) and depth > 1.7
        if opencut:
            x, z = P[i][0], P[i][1]
            fy = y[i] - 0.45
            best, bx, bz, by2 = 1e18, None, None, None
            for (P2, s2, g2, y2) in others:
                for j in range(0, len(P2), 2):
                    d2 = (P2[j][0] - x) ** 2 + (P2[j][1] - z) ** 2
                    if d2 < best:
                        best, bx, bz, by2 = d2, P2[j][0], P2[j][1], y2[j] - 0.45
            if best < 55 * 55:
                cx, cz = (x + bx) / 2, (z + bz) / 2
                hw = math.sqrt(best) / 2 + 13.5
                fy = min(fy, by2)
            else:
                cx, cz, hw = x, z, 13.0
            cur.append([round(cx, 1), round(cz, 1), round(fy, 2), round(hw, 1)])
        else:
            if len(cur) > 2: runs.append(cur)
            cur = []
    if len(cur) > 2: runs.append(cur)
    # thin out: keep every ~15 m and endpoints
    slim = []
    for run in runs:
        keep = [run[0]]
        for p in run[1:-1]:
            if math.hypot(p[0] - keep[-1][0], p[1] - keep[-1][1]) > 14:
                keep.append(p)
        keep.append(run[-1])
        if sum(math.hypot(keep[i + 1][0] - keep[i][0], keep[i + 1][1] - keep[i][1]) for i in range(len(keep) - 1)) > 60:
            slim.append(keep)
    return slim
out_cor = corridor_runs()

# ---------------------------------------------------------------- report + write
tot_el = sum(sum(math.hypot(c["p"][i + 1][0] - c["p"][i][0], c["p"][i + 1][1] - c["p"][i][1])
                 for i in range(len(c["p"]) - 1)) for c in out_el)
tot_sk = sum(sum(math.hypot(c["p"][i + 1][0] - c["p"][i][0], c["p"][i + 1][1] - c["p"][i][1])
                 for i in range(len(c["p"]) - 1)) for c in out_sk)
tot_cor = sum(sum(math.hypot(r[i + 1][0] - r[i][0], r[i + 1][1] - r[i][1])
                  for i in range(len(r) - 1)) for r in out_cor)
out = {"el": out_el, "sk": out_sk, "cor": out_cor}
with open(os.path.join(HERE, "overpasses.json"), "w") as f:
    json.dump(out, f, separators=(",", ":"))
size = os.path.getsize(os.path.join(HERE, "overpasses.json"))
print(f"elevated: {len(out_el)} chains, {tot_el/1000:.1f} km | sunken: {len(out_sk)} runs, "
      f"{tot_sk/1000:.1f} km | corridor: {len(out_cor)} runs, {tot_cor/1000:.1f} km | {size/1024:.0f} KB")
