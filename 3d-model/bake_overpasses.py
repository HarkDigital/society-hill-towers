#!/usr/bin/env python3
"""Bake elevated roads (bridges/viaducts/ramps) and sunken expressways from the raw
OSM dumps into overpasses.json for the app.

The packed road formats carry no bridge/tunnel/layer tags, so this reads the raw
Overpass dumps (osm_wide_raw.json, osm_south_raw.json, city_tiles/*.json), chains
tagged ways into corridors, solves a slope-limited height profile per chain against
the DEM, and emits overpasses.json:
  el:  elevated chains  [{c: clsCode, w: width_m, p: [[x, z, yTop], ...]}, ...]
  sk:  sunken chains    (same shape; y = roadway surface, below grade)
  cor: open-cut corridor runs for sunken motorways (the Vine Street cut):
       [[[x, z, floorY, halfW], ...], ...]

Height model (model frame, y = 0 at the towers' site):
  grade    = DEM, clamped at the water plane like the app's siteY
  elevated = grade + 6.8 (layer 1) / 12.5 (layer 2) / 17.5 (layer 3+), except
             grade + 0.45 where everything crossing beneath is itself sunken
             (streets over the Vine cut / core I-95 trench stay flat); over
             rivers the deck clears water + 20 (motorway) / + 13 (streets)
  sunken   = grade - 8 (open cut) / - 8.5 (covered)
  ramps    = slope-limited ends (4.2% motorway / 5.5% street / 9% footbridge)
             down to grade where a chain meets plain roads, pinned to the
             junction height where it meets an already-solved chain.
Plain gaps between tagged sections (embankments between overpasses on I-95, the
uncovered blocks of the Vine cut) are absorbed up to ~350 m for motorway-family
chains. Custom-built bridges (Ben Franklin, Walt Whitman) are skipped by name;
chains whose ends meet them hold their height instead of ramping down.
"""
import json, math, os, glob
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
LAT0, LON0 = 39.945473644755005, -75.14474803850973
COS0 = math.cos(math.radians(LAT0))
def to_xz(lat, lon):
    return ((lon - LON0) * 111320 * COS0, -(lat - LAT0) * 110574)

ROAD_W = {"motorway": 16, "trunk": 16, "motorway_link": 8, "trunk_link": 8,
          "primary": 13, "primary_link": 8, "secondary": 11, "secondary_link": 7,
          "tertiary": 9, "tertiary_link": 7, "residential": 7, "unclassified": 7,
          "living_street": 6, "pedestrian": 5, "footway": 3, "path": 3, "cycleway": 3}
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
raw_ways = {}
need = set()
for fp in files:
    if not os.path.exists(fp):
        continue
    try:
        d = json.load(open(fp))
    except Exception as e:
        print(f"skip {fp}: {e}"); continue
    for el in d.get("elements", []):
        if el["type"] != "way" or el["id"] in raw_ways:
            continue
        t = el.get("tags") or {}
        hw = t.get("highway")
        if not hw or hw not in CLS or t.get("area") == "yes":
            continue
        if CLS[hw] == 6 and not t.get("bridge"):
            continue          # footways only matter as pedestrian overpasses
        if len(el["nodes"]) > 1 and el["nodes"][0] == el["nodes"][-1]:
            continue          # closed rings (mapped plazas etc.)
        raw_ways[el["id"]] = {"nds": el["nodes"], "tags": t}
        need.update(el["nodes"])
    del d
nodes = {}
for fp in files:
    if not os.path.exists(fp):
        continue
    try:
        d = json.load(open(fp))
    except Exception:
        continue
    for el in d.get("elements", []):
        if el["type"] == "node" and el["id"] in need and el["id"] not in nodes:
            nodes[el["id"]] = to_xz(el["lat"], el["lon"])
    del d
print(f"{len(raw_ways)} highway ways, {len(nodes)}/{len(need)} nodes resolved")

# ---------------------------------------------------------------- DEM (mirrors demAbs)
def load_dem(name):
    p = os.path.join(HERE, name)
    return json.load(open(p)) if os.path.exists(p) else None
DEM_ALL = [(load_dem("dem.json"), 8.34), (load_dem("dem_wide.json"), 3.2),
           (load_dem("dem_south.json"), 3.2), (load_dem("dem_nw.json"), 4.0),
           (load_dem("dem_city.json"), 4.0)]
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
    for G, fb in DEM_ALL:
        if G:
            vv = sample_dem(G, x, z, fb)
            if vv is not None:
                return vv
    G = DEM_ALL[1][0]
    if G:
        cx = max(G["x0"], min(G["x0"] + G["cell"] * (G["nx"] - 1), x))
        cz = max(G["z0"], min(G["z0"] + G["cell"] * (G["nz"] - 1), z))
        s = sample_dem(G, cx, cz, 0)
        if s is not None:
            return s
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
def grade(x, z):
    y = dem_y(x, z)
    if y >= WATER + 0.6:
        return y
    return BULK if east_of_del(x, z) else WATER + 0.45
def over_water(x, z):
    return dem_y(x, z) < WATER + 0.6 and (east_of_del(x, z) or near_schuylkill(x, z))

# Front St line fit (locates the existing core I-95 trench corridor)
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
        return int(float(str(t.get("layer", "0")).strip()))
    except ValueError:
        return 0
W = {}
for wid, w in raw_ways.items():
    t = w["tags"]
    nds = [n for n in w["nds"] if n in nodes]
    if len(nds) < 2:
        continue
    hw = t["highway"]
    br = t.get("bridge") not in (None, "no")
    tu = t.get("tunnel") not in (None, "no")
    ly = parse_layer(t)
    if br and ly <= 0: ly = 1
    if tu and ly >= 0: ly = -1
    name = t.get("name") or ""
    W[wid] = {"nds": nds, "pts": [nodes[n] for n in nds], "cls": CLS[hw], "hw": hw,
              "w": ROAD_W.get(hw, 7), "mo": hw in MOTOR, "layer": ly, "tunnel": tu,
              "elev": (br or ly > 0) and not tu, "sunk": tu or ly < 0,
              "skipname": any(s in name for s in SKIP_NAMES)}
def way_len(w):
    return sum(math.hypot(w["pts"][i + 1][0] - w["pts"][i][0], w["pts"][i + 1][1] - w["pts"][i][1])
               for i in range(len(w["pts"]) - 1))

ends = {}
for wid, w in W.items():
    for n in (w["nds"][0], w["nds"][-1]):
        ends.setdefault(n, []).append(wid)
def other_end(w, n):
    return w["nds"][-1] if w["nds"][0] == n else w["nds"][0]

# ---------------------------------------------------------------- chaining
used = set()
def fill_path(node, want, lim, mo):
    """BFS through plain ways to another `want` way; returns the path (plain ways +
    the reached way) or None."""
    q = deque([(node, [], 0.0)])
    seen = {node}
    while q:
        n, path, dist = q.popleft()
        for oid in ends.get(n, ()):
            if oid in used or oid not in W or W[oid]["skipname"]:
                continue
            o = W[oid]
            if o[want] and path:
                return path + [oid]
            if o["elev"] or o["sunk"]:
                continue
            if mo and not o["mo"]:
                continue
            if not mo and o["cls"] == 6:
                continue
            L = way_len(o)
            if dist + L > lim or len(path) >= 3:
                continue
            far = other_end(o, n)
            if far in seen:
                continue
            seen.add(far)
            q.append((far, path + [oid], dist + L))
    return None

def dir_from(w, n):
    """Unit direction leaving node n along way w."""
    p = w["pts"]
    a, b = (p[0], p[1]) if w["nds"][0] == n else (p[-1], p[-2])
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1e-9
    return dx / L, dz / L

def pick_next(node, endw, cand):
    """Continuation through a junction: same highway type first, then smallest turn."""
    if len(cand) == 1:
        return cand[0]
    same = [o for o in cand if W[o]["hw"] == endw["hw"]]
    pool = same if same else cand
    hx, hz = dir_from(endw, node)          # direction back along the arriving way
    best, bo = -2.0, None
    for oid in pool:
        cx, cz = dir_from(W[oid], node)
        d = -(hx * cx + hz * cz)           # 1 = straight through
        if d > best:
            best, bo = d, oid
    return bo if best > 0.64 else None     # give up on turns sharper than ~50 deg

def grow(seed, want, fill_lim):
    c = [seed]; used.add(seed)
    head, tail = W[seed]["nds"][0], W[seed]["nds"][-1]
    for side in (1, 0):
        node = tail if side else head
        while True:
            endw = W[c[-1] if side else c[0]]
            cand = [oid for oid in ends.get(node, ()) if oid not in used and oid in W
                    and W[oid][want] and not W[oid]["skipname"]]
            step = None
            if cand:
                nxt = pick_next(node, endw, cand)
                if nxt is not None:
                    step = [nxt]
            if step is None:
                lim = fill_lim if endw["mo"] else 45
                step = fill_path(node, want, lim, endw["mo"])
            if not step:
                break
            for oid in step:
                used.add(oid)
                if side:
                    c.append(oid)
                else:
                    c.insert(0, oid)
                node = other_end(W[oid], node)
            if side:
                tail = node
            else:
                head = node
    return c

def assemble(cids):
    """Ordered node ids + per-vertex source way for a chain; None if broken."""
    nids = list(W[cids[0]]["nds"])
    if len(cids) > 1:
        nxt = W[cids[1]]
        sh = {nxt["nds"][0], nxt["nds"][-1]}
        if nids[-1] not in sh and nids[0] in sh:
            nids.reverse()
    src = [cids[0]] * len(nids)
    for wid in cids[1:]:
        seq = list(W[wid]["nds"])
        if seq[0] != nids[-1]:
            if seq[-1] == nids[-1]:
                seq.reverse()
            else:
                return None
        nids += seq[1:]
        src += [wid] * (len(seq) - 1)
    return nids, src

sunk_chains, elev_chains = [], []
for wid in sorted(W, key=lambda i: -way_len(W[i])):
    w = W[wid]
    if wid in used or not w["sunk"] or not w["mo"] or w["skipname"]:
        continue
    sunk_chains.append(grow(wid, "sunk", 360))
for wid in sorted(W, key=lambda i: -way_len(W[i])):
    w = W[wid]
    if wid in used or not w["elev"] or w["skipname"]:
        continue
    elev_chains.append(grow(wid, "elev", 340))
print(f"{len(sunk_chains)} sunken chains, {len(elev_chains)} elevated chains")

# ------------------------------------------------- grade bridges over sunken cuts
seg_grid = {}
SEG_CELL = 40
for wid, w in W.items():
    for i in range(len(w["pts"]) - 1):
        a, b = w["pts"][i], w["pts"][i + 1]
        x0, x1 = sorted((a[0], b[0])); z0, z1 = sorted((a[1], b[1]))
        for gx in range(int(x0 // SEG_CELL), int(x1 // SEG_CELL) + 1):
            for gz in range(int(z0 // SEG_CELL), int(z1 // SEG_CELL) + 1):
                seg_grid.setdefault((gx, gz), []).append((wid, a[0], a[1], b[0], b[1]))

def crossings_under(wid):
    w = W[wid]
    out = set()
    for i in range(len(w["pts"]) - 1):
        a, b = w["pts"][i], w["pts"][i + 1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz)
        if L < 0.05:
            continue
        ux, uz = dx / L, dz / L
        k = 0.0
        while k <= L:
            x, z = a[0] + ux * k, a[1] + uz * k
            for (oid, ax, az, bx, bz) in seg_grid.get((int(x // SEG_CELL), int(z // SEG_CELL)), ()):
                if oid == wid or oid not in W:
                    continue
                o = W[oid]
                if o["layer"] >= w["layer"]:
                    continue
                sdx, sdz = bx - ax, bz - az
                L2 = sdx * sdx + sdz * sdz or 1e-9
                t = max(0.0, min(1.0, ((x - ax) * sdx + (z - az) * sdz) / L2))
                ex, ez = ax + sdx * t - x, az + sdz * t - z
                if ex * ex + ez * ez > ((w["w"] + o["w"]) / 2 + 1) ** 2:
                    continue
                sl = math.hypot(sdx, sdz)
                if sl > 0.05 and abs(ux * sdx / sl + uz * sdz / sl) > 0.906:
                    continue
                out.add(oid)
            k += 8.0
    return out

grade_bridge = set()
for wid, w in W.items():
    if not w["elev"] or w["skipname"]:
        continue
    cr = crossings_under(wid)
    if cr:
        if all(W[c]["sunk"] or any(in_core_trench(p[0], p[1]) for p in W[c]["pts"]) for c in cr):
            grade_bridge.add(wid)
    elif any(in_core_trench(p[0], p[1]) for p in w["pts"]):
        grade_bridge.add(wid)
print(f"{len(grade_bridge)} elevated ways stay at grade (spans over sunken cuts)")

# ---------------------------------------------------------------- profiles
LIFT = {1: 6.8, 2: 12.5, 3: 17.5, 4: 17.5}
node_y = {}
def solve_chain(cids, sunk):
    asm = assemble(cids)
    if not asm:
        return None
    nids, src = asm
    P = []      # [x, z, srcWid, nodeId|None]
    for i in range(len(nids) - 1):
        a, b = nodes[nids[i]], nodes[nids[i + 1]]
        P.append([a[0], a[1], src[i + 1], nids[i]])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = int(L // 20)
        for j in range(1, k + 1):
            t = j / (k + 1)
            P.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, src[i + 1], None])
    P.append([nodes[nids[-1]][0], nodes[nids[-1]][1], src[-1], nids[-1]])
    n = len(P)
    s = [0.0]
    for i in range(1, n):
        s.append(s[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    if s[-1] < (40 if sunk else 26):
        return None
    g = [grade(p[0], p[1]) for p in P]
    if sunk:
        # the NED grid dips into the expressway cut itself (the same trap the core
        # I-95 trench hit), so read the street grade at the rim beside the cut
        for i in range(n):
            i0, i1 = max(0, i - 1), min(n - 1, i + 1)
            dx, dz = P[i1][0] - P[i0][0], P[i1][1] - P[i0][1]
            L = math.hypot(dx, dz) or 1e-9
            nxr, nzr = -dz / L, dx / L
            rim = max(grade(P[i][0] + nxr * o * sgn, P[i][1] + nzr * o * sgn)
                      for o in (30, 44) for sgn in (1, -1))
            g[i] = max(g[i], rim)
    tgt = []
    for i, p in enumerate(P):
        w = W[p[2]]
        if sunk:
            tgt.append(max(g[i] - (8.5 if w["tunnel"] else 8.0), WATER + 1.4))
        else:
            lift = 0.45 if p[2] in grade_bridge else LIFT.get(max(1, w["layer"]), 6.8)
            y = g[i] + lift
            if over_water(p[0], p[1]):
                y = max(y, WATER + (20 if w["cls"] == 0 else 13))
            tgt.append(y)
    tgt = [tgt[0]] + [(tgt[i - 1] + tgt[i] + tgt[i + 1]) / 3 for i in range(1, n - 1)] + [tgt[-1]]
    cls0 = min(W[c]["cls"] for c in cids)
    slope = 0.042 if cls0 <= 1 else (0.09 if cls0 == 6 else 0.055)
    chain_set = set(cids)
    def end_constraint(idx):
        nid = P[idx][3]
        if nid in node_y:
            return node_y[nid]
        touch = ends.get(nid, ()) if nid is not None else ()
        if any(oid in W and W[oid]["skipname"] for oid in touch):
            return tgt[idx]                              # meets a custom bridge: hold
        if any(oid in W and oid not in chain_set for oid in touch):
            return grade(P[idx][0], P[idx][1]) + 0.3     # meets plain roads: touch down
        return tgt[idx]                                  # dead end at the data edge: hold
    def end_kind(idx):
        """0 = ramps to grade, 1 = pinned to a junction or held high."""
        nid = P[idx][3]
        if nid in node_y:
            return 1
        touch = ends.get(nid, ()) if nid is not None else ()
        if any(oid in W and W[oid]["skipname"] for oid in touch):
            return 1
        if any(oid in W and oid not in set(cids) for oid in touch):
            return 0
        return 1
    ek = (end_kind(0), end_kind(n - 1))
    y = list(tgt)
    y[0] = end_constraint(0)
    y[-1] = end_constraint(n - 1)
    yl = y[-1]
    for i in range(1, n):
        d = (s[i] - s[i - 1]) * slope
        y[i] = min(max(tgt[i], y[i - 1] - d), y[i - 1] + d)
    y[-1] = yl
    for i in range(n - 2, 0, -1):
        d = (s[i + 1] - s[i]) * slope
        y[i] = min(max(y[i], y[i + 1] - d), y[i + 1] + d)
    # soften profile kinks (ends stay pinned); junction heights register AFTER
    # smoothing so ramps meet the smoothed mainline exactly
    for _ in range(2):
        y = [y[0]] + [(y[i - 1] + y[i] + y[i + 1]) / 3 for i in range(1, n - 1)] + [y[-1]]
    for i, p in enumerate(P):
        if p[3] is not None and p[3] not in node_y:
            node_y[p[3]] = y[i]
    return P, s, g, y, ek

def simplify_profile(P, y, tol2d=0.9, toly=0.22):
    keep = {0, len(P) - 1}
    def dp(i0, i1):
        if i1 - i0 < 2:
            return
        ax, az, ay = P[i0][0], P[i0][1], y[i0]
        bx, bz, by = P[i1][0], P[i1][1], y[i1]
        dx, dz = bx - ax, bz - az
        L = math.hypot(dx, dz) or 1e-9
        best, bi = -1.0, -1
        for i in range(i0 + 1, i1):
            d2 = abs((P[i][0] - ax) * dz - (P[i][1] - az) * dx) / L
            t = max(0.0, min(1.0, ((P[i][0] - ax) * dx + (P[i][1] - az) * dz) / (L * L)))
            dy = abs(y[i] - (ay + (by - ay) * t))
            m = max(d2 / tol2d, dy / toly)
            if m > best:
                best, bi = m, i
        if best > 1:
            keep.add(bi); dp(i0, bi); dp(bi, i1)
    dp(0, len(P) - 1)
    ks = sorted(keep)
    return [[round(P[i][0], 1), round(P[i][1], 1), round(y[i], 2)] for i in ks]

def clip_core(prof):
    M = 35
    inb = lambda p: CORE[0] - M <= p[0] <= CORE[1] + M and CORE[2] - M <= p[1] <= CORE[3] + M
    runs, cur = [], []
    for i, p in enumerate(prof):
        keep = not inb(p) or (i > 0 and not inb(prof[i - 1])) or (i + 1 < len(prof) and not inb(prof[i + 1]))
        if keep:
            cur.append(p)
        else:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
    if len(cur) > 1:
        runs.append(cur)
    return runs

def run_len(run):
    return sum(math.hypot(run[i + 1][0] - run[i][0], run[i + 1][1] - run[i][1]) for i in range(len(run) - 1))

def emit_runs(P, y, ek, prof):
    """Split at the core box, carrying end kinds: an interior cut keeps kind 1
    (the roadway continues; the deck must not taper there)."""
    runs = clip_core(prof)
    out = []
    for run in runs:
        f0 = ek[0] if run[0] == prof[0] else 1
        f1 = ek[1] if run[-1] == prof[-1] else 1
        out.append((run, f0, f1))
    return out

out_el, out_sk = [], []
sunk_solved = []
for cids in sunk_chains:
    r = solve_chain(cids, True)
    if not r:
        continue
    P, s, g, y, ek = r
    M = 35
    if all(CORE[0] - M <= p[0] <= CORE[1] + M and CORE[2] - M <= p[1] <= CORE[3] + M for p in P):
        continue                       # the core I-95 trench is already built
    sunk_solved.append(r)
    # split at cover transitions FIRST: covered (tunnel) stretches must not dig
    # holes or grow walls in the app (the I-76 tunnel under 30th St stays buried)
    segs, cur, cov0 = [], [0], W[P[0][2]]["tunnel"]
    for i in range(1, len(P)):
        cv = W[P[i][2]]["tunnel"]
        if cv != cov0:
            cur.append(i)
            segs.append((cur, cov0))
            cur = [i]
            cov0 = cv
        else:
            cur.append(i)
    segs.append((cur, cov0))
    for idxs, cov in segs:
        if len(idxs) < 2:
            continue
        Pseg = [P[i] for i in idxs]
        yseg = [y[i] for i in idxs]
        prof = simplify_profile(Pseg, yseg)
        eks = (ek[0] if idxs[0] == 0 else 1, ek[1] if idxs[-1] == len(P) - 1 else 1)
        for run, f0, f1 in emit_runs(Pseg, yseg, eks, prof):
            if run_len(run) > 40:
                out_sk.append({"c": 0, "w": 12, "p": run, "e": [f0, f1], "cov": 1 if cov else 0})

# longest/motorway chains first so ramps pin to solved mainlines
elev_chains.sort(key=lambda cids: (0 if any(W[c]["mo"] for c in cids) else 1,
                                   -sum(way_len(W[c]) for c in cids)))
for cids in elev_chains:
    r = solve_chain(cids, False)
    if not r:
        continue
    P, s, g, y, ek = r
    if max(y[i] - g[i] for i in range(len(P))) < 0.35:
        continue
    prof = simplify_profile(P, y)
    cmin = min(W[c]["cls"] for c in cids)
    wmax = max(W[c]["w"] for c in cids)
    for run, f0, f1 in emit_runs(P, y, ek, prof):
        if run_len(run) < 24:
            continue
        out_el.append({"c": cmin, "w": wmax, "p": run, "e": [f0, f1]})

# ---------------------------------------------------------------- Vine corridor
def corridor_runs():
    """One clean corridor from the TWO mainline carriageways (ramps excluded):
    even 12 m stations, clamped and smoothed width, smoothed floor."""
    if not sunk_solved:
        return []
    chains = sorted(sunk_solved, key=lambda r: -r[1][-1])
    if len(chains) < 2:
        return []
    lead, partner = chains[0], chains[1]
    P, s, g, y, ek = lead
    P2, s2, g2, y2, ek2 = partner
    runs, cur = [], []
    for i in range(len(P)):
        w = W[P[i][2]]
        depth = g[i] - y[i]
        if (not w["tunnel"]) and depth > 0.5:
            x, z = P[i][0], P[i][1]
            best, bj = 1e18, -1
            for j in range(len(P2)):
                d2 = (P2[j][0] - x) ** 2 + (P2[j][1] - z) ** 2
                if d2 < best:
                    best, bj = d2, j
            if best < 60 * 60:
                cx, cz = (x + P2[bj][0]) / 2, (z + P2[bj][1]) / 2
                hw = math.sqrt(best) / 2 + 12.5
                fy = min(y[i], y2[bj]) - 0.45
            else:
                cx, cz, hw = x, z, 14.0
                fy = y[i] - 0.45
            cur.append([cx, cz, fy, max(14.0, min(24.0, hw))])
        else:
            if len(cur) > 2:
                runs.append(cur)
            cur = []
    if len(cur) > 2:
        runs.append(cur)
    out = []
    for run in runs:
        # resample to even 12 m stations along the centerline
        seg = [0.0]
        for i in range(1, len(run)):
            seg.append(seg[-1] + math.hypot(run[i][0] - run[i - 1][0], run[i][1] - run[i - 1][1]))
        if seg[-1] < 60:
            continue
        nst = max(2, int(seg[-1] // 12))
        ev = []
        for k in range(nst + 1):
            t = seg[-1] * k / nst
            j = 0
            while j + 1 < len(seg) and seg[j + 1] < t:
                j += 1
            f = (t - seg[j]) / max(1e-6, seg[j + 1] - seg[j])
            ev.append([run[j][m] + (run[j + 1][m] - run[j][m]) * f for m in range(4)])
        # smooth centerline + floor (3-tap x2) and width (5-tap): the raw pairing
        # wobbles where the carriageways weave, which serrated the walls
        for _ in range(2):
            ev = [ev[0]] + [[(ev[i - 1][m] + ev[i][m] + ev[i + 1][m]) / 3 for m in range(3)] + [ev[i][3]]
                            for i in range(1, len(ev) - 1)] + [ev[-1]]
        hws = [p[3] for p in ev]
        sm = []
        for i in range(len(hws)):
            lo, hi = max(0, i - 2), min(len(hws), i + 3)
            sm.append(sum(hws[lo:hi]) / (hi - lo))
        for i, p in enumerate(ev):
            p[3] = sm[i]
        out.append([[round(p[0], 1), round(p[1], 1), round(p[2], 2), round(p[3], 1)] for p in ev])
    return out
out_cor = corridor_runs()

# ---------------------------------------------------------------- report + write
tot_el = sum(run_len(c["p"]) for c in out_el)
tot_sk = sum(run_len(c["p"]) for c in out_sk)
tot_cor = sum(run_len(r) for r in out_cor)
with open(os.path.join(HERE, "overpasses.json"), "w") as f:
    json.dump({"el": out_el, "sk": out_sk, "cor": out_cor}, f, separators=(",", ":"))
size = os.path.getsize(os.path.join(HERE, "overpasses.json"))
print(f"elevated: {len(out_el)} chains, {tot_el/1000:.1f} km | sunken: {len(out_sk)} runs, "
      f"{tot_sk/1000:.1f} km | corridor: {len(out_cor)} runs, {tot_cor/1000:.1f} km | {size/1024:.0f} KB")

# sanity: the two corridors Mike named
def near_any(pts_list, x, z, r):
    for c in pts_list:
        for p in c["p"]:
            if math.hypot(p[0] - x, p[1] - z) < r:
                return True
    return False
print("I-95 viaduct at Front & Reed:", near_any(out_el, -60, 1380, 200))
print("Vine cut corridor runs x-extents:", [(round(r[0][0]), round(r[-1][0])) for r in out_cor])
