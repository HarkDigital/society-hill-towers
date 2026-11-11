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
  ce:  one [end0, end1] per corridor run (Round 226): 0 = the page's old end face, 1 = a portal
       (por) closes it, 2 = the cut runs out onto the ground there, nothing across it
  por: the tunnel mouths the cut runs into (Round 226): [[x, z, roadY, dx, dz, halfW], ...],
       (dx, dz) pointing into the tunnel
A sunken run may also carry ap: 1 (Round 226: an approach, the plain road past a tunnel's mouth
held at the mouth's height until the ground has come down to it; the page opens the ground over
its whole length) and rp: 1 (a ramp leaving such an approach); a covered run may carry g: 1 (a
short underpass that touches down at both ends: the page draws its road through at grade).

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
# Round 226 (Mike, over the Vine Street Expressway at Logan Circle: "this view has the road running right into the
# grass. Fix that."). Three things in this file put it there, and the four numbers below undo them:
#   - OSM now maps the expressway under the 18th and 19th Street bridges, and under the cap between them, as tunnels
#     of 20 to 36 m with 38 m of open road between each pair. Every piece fell under the 40 m a run needs to be
#     written, so from 18th Street to the tunnel's mouth neither carriageway was in the file at all and the page drew
#     both flat on the lawn, 190 m of them, ending where the real tunnel begins. A covered stretch under SHORT_COVER
#     with open road at both its ends is a bridge's shadow, not a tunnel: it is open cut, and the street's own deck
#     (el) spans it.
#   - The westbound carriageway from 15th to 18th Street is two ways without a layer tag, 480 m, past the 360 m a
#     sunken chain would bridge, so it was never sunk and the cut was fitted to the eastbound one alone, its north
#     wall down the middle of the westbound lanes. SUNK_FILL carries the chain through.
#   - A tunnel that met a plain road at its end came up to the ground INSIDE itself (the west mouth, by 21st Street,
#     stood at street level), though the DEM shows the real road staying down for another 200 m. Where the ground
#     ahead falls to the road's own depth the mouth holds that depth (approach_plan) and the road past it is an
#     approach: level until the ground has come down to it.
# And a tunnel is covered only where there is ground to cover it: the DEM still shows open cut over the first 35 m
# of the tagged tunnel at its east end (a cap newer than the survey), so the mouth is drawn back, by MOUTH_TRIM at
# most, to where COVER_MIN of ground stands over the roadway.
SUNK_FILL = 520
SHORT_COVER = 45
COVER_MIN = 5.0
MOUTH_TRIM = 70
APPROACH_MAX = 320
UNDERPASS_MAX = 100

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
# Round 85: the river's real outline (schuylkill.json, OSM natural=water) decides "over water" for the Schuylkill;
# the hand polyline above runs up to a kilometre west of the river through Center City, so the crossings between
# Spring Garden and South Street solved 7 m over the water instead of the rule's 13 and 20
_SCH = None
def _sch_polys():
    global _SCH
    if _SCH is None:
        _SCH = []
        fp = os.path.join(HERE, "schuylkill.json")
        if os.path.exists(fp):
            for pg in json.load(open(fp)).get("polys", []):
                rings = [pg["ring"]] + list(pg.get("holes", []))
                xs = [q[0] for q in pg["ring"]]; zs = [q[1] for q in pg["ring"]]
                _SCH.append((min(xs), max(xs), min(zs), max(zs), rings))
    return _SCH
def _in_ring(x, z, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        ax, az = ring[i]; bx, bz = ring[(i + 1) % n]
        if (az > z) != (bz > z):
            t = (z - az) / (bz - az)
            if x < ax + (bx - ax) * t:
                inside = not inside
    return inside
def sch_bank(x, z, r=40.0):
    """Within r of the Schuylkill outline's edge (Round 85: the touch-down floor is the bank's, not the made land's)."""
    r2 = r * r
    for x0, x1, z0, z1, rings in _sch_polys():
        if x < x0 - r or x > x1 + r or z < z0 - r or z > z1 + r:
            continue
        for ring in rings:
            n = len(ring)
            for i in range(n):
                ax, az = ring[i]; bx, bz = ring[(i + 1) % n]
                dx, dz = bx - ax, bz - az
                L2 = dx * dx + dz * dz or 1e-9
                t = ((x - ax) * dx + (z - az) * dz) / L2
                t = 0.0 if t < 0 else 1.0 if t > 1 else t
                ex, ez = ax + dx * t - x, az + dz * t - z
                if ex * ex + ez * ez < r2:
                    return True
    return False
def in_schuylkill(x, z):
    for x0, x1, z0, z1, rings in _sch_polys():
        if x < x0 or x > x1 or z < z0 or z > z1:
            continue
        hit = False
        for r in rings:
            if _in_ring(x, z, r):
                hit = not hit
        if hit:
            return True
    return False
def over_water(x, z):
    return in_schuylkill(x, z) or (dem_y(x, z) < WATER + 0.6 and (east_of_del(x, z) or near_schuylkill(x, z)))

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

# The southern core is an approach to the viaduct, not a continuation of the
# Penn's Landing trench. OSM splits its embankments from the short bridge spans;
# keep the connected I-95 mainline through those untagged gaps and the core seam.
def i95_south_approach(tags, pts):
    return (tags.get("highway") == "motorway" and tags.get("ref") == "I 95"
            and tags.get("tunnel") in (None, "no")
            and all(-160 < x < 225 and 220 < z < 1400 for x, z in pts))

def i95_approach_y(z, grade_y):
    # Rise out of the existing tunnel/cut over a full city block sequence, then
    # keep the normal viaduct clearance. Heights are model estimates, not survey.
    t = max(0.0, min(1.0, (z - 230.0) / 490.0))
    t = t * t * (3.0 - 2.0 * t)
    trench_surface = 1.5 - DATUM + 0.55 + 0.24
    return trench_surface * (1.0 - t) + (grade_y + 6.8) * t

# Round 216 (Mike, over I-95 at Market Street: the street climbed out of the trench as a narrow deck at Front Street's
# height, dropped 6 m at the trench's east wall and never met the street on the river side). OSM maps Market Street east
# of Front Street as a layer-1 bridge over I-95 and Columbus Boulevard, carried round to the riverfront by Penn's Landing
# Road (layer 1 too). Both lie inside the core, which this bake leaves to the page's own trench, so they were clipped and
# the core drew them flat. They are kept whole now (core "market"): the page solves the profile against its own trench,
# lanes and streets (marketDeckSolve in app.js) and trims the ends where the deck has come down to the street, so the
# bake carries the geometry, every node, and a deck wide enough for the generated sidewalks (7 m roadway, 3 m walks)
def penns_landing_bridge(tags, pts):
    return (tags.get("highway") == "unclassified" and tags.get("bridge") not in (None, "no")
            and tags.get("name") in ("Market Street", "Penn's Landing Road")
            and all(100 < x < 420 and -520 < z < -250 for x, z in pts))
MARKET_DECK_W = 13

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
    approach = i95_south_approach(t, [nodes[n] for n in nds])
    if approach:
        br = True; ly = max(1, ly)
    W[wid] = {"nds": nds, "pts": [nodes[n] for n in nds], "cls": CLS[hw], "hw": hw,
              "w": ROAD_W.get(hw, 7), "mo": hw in MOTOR, "layer": ly, "tunnel": tu,
              "elev": (br or ly > 0) and not tu, "sunk": tu or ly < 0,
              "skipname": any(s in name for s in SKIP_NAMES), "i95core": approach, "core_ramp": False,
              "market": penns_landing_bridge(t, [nodes[n] for n in nds])}
def way_len(w):
    return sum(math.hypot(w["pts"][i + 1][0] - w["pts"][i][0], w["pts"][i + 1][1] - w["pts"][i][1])
               for i in range(len(w["pts"]) - 1))

ends = {}
for wid, w in W.items():
    for n in (w["nds"][0], w["nds"][-1]):
        ends.setdefault(n, []).append(wid)
# Access ramps must join the same profile as the mainline. Follow only connected
# motorway links in the southern core; adjacent Front Street/Columbus stay down.
approach_nodes = {n for w in W.values() if w["i95core"] for n in w["nds"]}
changed = True
while changed:
    changed = False
    for w in W.values():
        if (w["hw"] != "motorway_link" or w["tunnel"] or w["core_ramp"]
                or not all(50 < x < 240 and 220 < z < 830 for x, z in w["pts"])
                or not approach_nodes.intersection(w["nds"])):
            continue
        w["core_ramp"] = True; w["elev"] = True; w["layer"] = max(1, w["layer"])
        approach_nodes.update(w["nds"]); changed = True
core_ramp_nodes = {n for w in W.values() if w["core_ramp"] for n in (w["nds"][0], w["nds"][-1])}

def other_end(w, n):
    return w["nds"][-1] if w["nds"][0] == n else w["nds"][0]

# ---------------------------------------------------------------- chaining
used = set()
def turn_ok(arr, n, oid):
    """Through node n from the way arr onto oid without a turn sharper than pick_next allows (Round 212)."""
    hx, hz = dir_from(W[arr], n)
    cx, cz = dir_from(W[oid], n)
    return -(hx * cx + hz * cz) > 0.64

def fill_path(node, want, lim, mo, arr=None):
    """BFS through plain ways to another `want` way; returns the path (plain ways +
    the reached way) or None. Every step goes on through its node no sharper than pick_next's turn (Round 212: a
    divided mainline's gap used to be bridged onto the other carriageway, a U-turn the profile drew as a hairpin)."""
    q = deque([(node, [], 0.0, arr)])
    seen = {node}
    while q:
        n, path, dist, pw = q.popleft()
        for oid in ends.get(n, ()):
            if oid in used or oid not in W or W[oid]["skipname"]:
                continue
            if pw is not None and not turn_ok(pw, n, oid):
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
            q.append((far, path + [oid], dist + L, oid))
    return None

def dir_from(w, n):
    """Unit direction leaving node n along way w."""
    p = w["pts"]
    a, b = (p[0], p[1]) if w["nds"][0] == n else (p[-1], p[-2])
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1e-9
    return dx / L, dz / L

def pick_next(node, endw, cand):
    """Continuation through a junction: same highway type first, then smallest turn. A lone candidate takes the
    same turn test (Round 212: at Fairmount Avenue a ramp splits into two parallel bridges, both leaving one node,
    and the lone-candidate shortcut chained the second branch onto the first nose to nose, a hairpin whose
    junction the profile then held 8 m up while the traffic ran on down to the street)."""
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
                step = fill_path(node, want, lim, endw["mo"], c[-1] if side else c[0])
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
    sunk_chains.append(grow(wid, "sunk", SUNK_FILL))
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
    if w["i95core"] or w["market"]:
        continue
    if w["core_ramp"]:
        grade_bridge.add(wid); continue
    cr = crossings_under(wid)
    if cr:
        if all(W[c]["sunk"] or any(in_core_trench(p[0], p[1]) for p in W[c]["pts"]) for c in cr):
            grade_bridge.add(wid)
    elif any(in_core_trench(p[0], p[1]) for p in w["pts"]):
        grade_bridge.add(wid)
print(f"{len(grade_bridge)} elevated ways stay at grade (spans over sunken cuts)")

# ---------------------------------------------------------------- approaches (Round 226)
def walk_plain(nid, arr, kinds, lim):
    """The plain road on from node nid, reached by way arr: [(way, its node ids outward), ...], the same kind of
    highway, never a tagged bridge or tunnel or a way a chain already holds, no sharper than pick_next's turn."""
    out, node, prev, dist = [], nid, arr, 0.0
    while dist < lim:
        cand = [oid for oid in ends.get(node, ()) if oid != prev and oid in W and oid not in used
                and W[oid]["hw"] in kinds and not W[oid]["sunk"] and not W[oid]["elev"] and not W[oid]["skipname"]
                and all(oid != o for o, _ in out) and W[oid]["nds"][0] != W[oid]["nds"][-1]
                and turn_ok(prev, node, oid)]
        if not cand:
            break
        hx, hz = dir_from(W[prev], node)
        nxt = min(cand, key=lambda o: hx * dir_from(W[o], node)[0] + hz * dir_from(W[o], node)[1])
        seq = list(W[nxt]["nds"])
        if seq[0] != node:
            seq.reverse()
        out.append((nxt, seq))
        dist += way_len(W[nxt]); prev = nxt; node = seq[-1]
    return out

def track_points(steps):
    """[x, z, way, node id or None] along the ways at solve_chain's own 20 m, with the distance to each."""
    P = []
    for wid, seq in steps:
        for i in range(len(seq) - 1):
            a, b = nodes[seq[i]], nodes[seq[i + 1]]
            if not P or P[-1][3] != seq[i]:
                P.append([a[0], a[1], wid, seq[i]])
            k = int(math.hypot(b[0] - a[0], b[1] - a[1]) // 20)
            for j in range(1, k + 1):
                t = j / (k + 1)
                P.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, wid, None])
            P.append([b[0], b[1], wid, seq[i + 1]])
    s = [0.0]
    for i in range(1, len(P)):
        s.append(s[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    return P, s

APPROACH = {}      # a tunnel's mouth node -> its approach's plan, or None
def approach_plan(nid, arr, y_tgt):
    """A tunnel ends at node nid on a plain motorway. Where the ground along that road falls, within APPROACH_MAX,
    to at least 2.5 m under the ground at the mouth, the road ahead is still down in its cut (the DEM's own record
    of it): the mouth holds the depth of that low ground, never deeper than the tunnel's own target, and only when
    that leaves COVER_MIN of ground over the mouth. Otherwise None, and the end touches down as it always did."""
    if nid in APPROACH:
        return APPROACH[nid]
    plan = None
    steps = walk_plain(nid, arr, ("motorway",), APPROACH_MAX)
    if steps:
        P, s = track_points(steps)
        g = [grade(q[0], q[1]) for q in P]
        low = min(g[i] for i in range(len(P)) if s[i] <= APPROACH_MAX)
        hold = max(y_tgt, low + 0.3)
        if low + 0.3 < g[0] - 2.5 and g[0] - hold >= COVER_MIN:
            plan = {"hold": hold, "P": P, "s": s, "g": g}
    APPROACH[nid] = plan
    return plan

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
            if w["i95core"]:
                y = i95_approach_y(p[1], g[i])
            tgt.append(y)
    tgt = [tgt[0]] + [(tgt[i - 1] + tgt[i] + tgt[i + 1]) / 3 for i in range(1, n - 1)] + [tgt[-1]]
    cls0 = min(W[c]["cls"] for c in cids)
    slope = 0.042 if cls0 <= 1 else (0.09 if cls0 == 6 else 0.055)
    chain_set = set(cids)
    def end_constraint(idx):
        nid = P[idx][3]
        w = W[P[idx][2]]
        if (w["i95core"] or w["core_ramp"]) and P[idx][1] < 250:
            return i95_approach_y(230, g[idx])
        if nid in node_y:
            return node_y[nid]
        touch = ends.get(nid, ()) if nid is not None else ()
        if any(oid in W and W[oid]["skipname"] for oid in touch):
            return tgt[idx]                              # meets a custom bridge: hold
        if sunk and w["tunnel"] and nid is not None:
            ap = approach_plan(nid, P[idx][2], tgt[idx])
            if ap:
                return ap["hold"]                        # Round 226: the road past the mouth stays down: hold its depth
        if any(oid in W and oid not in chain_set for oid in touch):
            x, z = P[idx][0], P[idx][1]
            y0 = grade(x, z) + 0.3     # meets plain roads: touch down
            return max(y0, WATER + 1.4) if (in_schuylkill(x, z) or sch_bank(x, z)) else y0     # never awash on the Schuylkill's bank; the made land keeps its datum (Round 85)
        return tgt[idx]                                  # dead end at the data edge: hold
    def end_kind(idx):
        """0 = ramps to grade, 1 = pinned to a junction or held high."""
        nid = P[idx][3]
        if nid in node_y:
            return 1
        touch = ends.get(nid, ()) if nid is not None else ()
        if any(oid in W and W[oid]["skipname"] for oid in touch):
            return 1
        if sunk and nid is not None and APPROACH.get(nid):
            return 1                                     # Round 226: an approach carries the roadway on
        if any(oid in W and oid not in set(cids) for oid in touch):
            return 0
        return 1
    y = list(tgt)
    y[0] = end_constraint(0)
    y[-1] = end_constraint(n - 1)
    ek = (end_kind(0), end_kind(n - 1))                  # after the constraints: an approach is planned there (Round 226)
    yl = y[-1]
    for i in range(1, n):
        d = (s[i] - s[i - 1]) * slope
        y[i] = min(max(tgt[i], y[i - 1] - d), y[i - 1] + d)
    y[-1] = yl
    for i in range(n - 2, 0, -1):
        d = (s[i + 1] - s[i]) * slope
        y[i] = min(max(y[i], y[i + 1] - d), y[i + 1] + d)
    # The detailed core carves a real trench below the bare-earth DEM. Its
    # emerging motorway/ramp can be below that DEM without being below the mesh.
    def road_floor(i, lift):
        w = W[P[i][2]]
        return min(g[i] + lift, i95_approach_y(P[i][1], g[i])) if w["i95core"] or w["core_ramp"] else g[i] + lift
    # Round 85: an elevated deck never sits under the DEM it is meant to clear (the slope limit could not climb the
    # concourse's rise at 30th Street, so Schuylkill Avenue's ramp ran 1.7 to 4.2 m under the drawn ground)
    if not sunk:
        for i in range(1, n - 1):
            y[i] = max(y[i], road_floor(i, 0.45))
    # soften profile kinks (ends stay pinned); junction heights register AFTER
    # smoothing so ramps meet the smoothed mainline exactly
    for _ in range(2):
        y = [y[0]] + [(y[i - 1] + y[i] + y[i + 1]) / 3 for i in range(1, n - 1)] + [y[-1]]
    if not sunk:
        for i in range(1, n - 1):
            y[i] = max(y[i], road_floor(i, 0.3))
    for i, p in enumerate(P):
        if p[3] is not None and p[3] not in node_y:
            node_y[p[3]] = y[i]
    return P, s, g, y, ek

def simplify_profile(P, y, tol2d=0.9, toly=0.22, keep_nodes=()):
    keep = {0, len(P) - 1}
    keep.update(i for i, p in enumerate(P) if p[3] in keep_nodes)
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
    # Keep the merging node itself, not just a nearby simplified chord at a
    # slightly different height. The ramp shares this exact xyz with its deck.
    anchors = sorted(keep)
    for a, b in zip(anchors, anchors[1:]):
        dp(a, b)
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

def emit_runs(P, y, ek, prof, keep_core=False):
    """Split at the core box, carrying end kinds: an interior cut keeps kind 1
    (the roadway continues; the deck must not taper there)."""
    runs = [prof] if keep_core else clip_core(prof)
    out = []
    for run in runs:
        f0 = ek[0] if run[0] == prof[0] else 1
        f1 = ek[1] if run[-1] == prof[-1] else 1
        out.append((run, f0, f1))
    return out

out_el, out_sk = [], []
sunk_solved = []       # (P, s, g, y, ek, cov, mainline, at_mouth): cov[i] = the stretch on from point i is a tunnel
approach_tracks = []   # (P, s, g, y, owner): the mainline approaches (Round 226), owner = the chain's place in sunk_solved
mouths = []            # (x, z, roadY, dx, dz): where an open stretch runs into a covered one, (dx, dz) into the tunnel

def cover_flags(P, s, y):
    """Which stretches of a solved sunken chain are tunnel (Round 226; the tags alone, before). A tagged stretch under
    SHORT_COVER with open road at both its ends is a bridge's shadow and counts as open cut. Then each mouth that
    faces an open stretch is drawn back into the tunnel, MOUTH_TRIM at most, while the DEM across the roadway there
    stands under COVER_MIN over it: no ground, no tunnel."""
    n = len(P)
    cov = [bool(W[P[i][2]]["tunnel"]) for i in range(n)]
    cov[-1] = cov[-2]
    def stretches():
        out, i = [], 0
        while i < n - 1:
            if cov[i]:
                j = i
                while j < n - 1 and cov[j]:
                    j += 1
                out.append((i, j))        # covered from point i to point j
                i = j
            else:
                i += 1
        return out
    for i, j in stretches():
        if i > 0 and j < n - 1 and s[j] - s[i] < SHORT_COVER:
            for k in range(i, j):
                cov[k] = False
    def covered(i):
        i0, i1 = max(0, i - 1), min(n - 1, i + 1)
        dx, dz = P[i1][0] - P[i0][0], P[i1][1] - P[i0][1]
        L = math.hypot(dx, dz) or 1e-9
        nx, nz = -dz / L, dx / L
        return min(grade(P[i][0] + nx * o, P[i][1] + nz * o) for o in (-8, 0, 8)) >= y[i] + COVER_MIN
    for i, j in stretches():
        if s[j] - s[i] < SHORT_COVER:     # a stub at the chain's end (10th Street's, 39 m): left as it was
            continue
        if i > 0:                         # open road before it: the mouth at point i
            k = i
            while k < j - 1 and s[k] - s[i] < MOUTH_TRIM and not covered(k):
                cov[k] = False; k += 1
            i = k
        if j < n - 1:                     # open road after it: the mouth at point j
            k = j
            while k > i + 1 and s[j] - s[k] < MOUTH_TRIM and not covered(k):
                cov[k - 1] = False; k -= 1
    cov[-1] = cov[-2]
    return cov

for cids in sunk_chains:
    r = solve_chain(cids, True)
    if not r:
        continue
    P, s, g, y, ek = r
    M = 35
    if all(CORE[0] - M <= p[0] <= CORE[1] + M and CORE[2] - M <= p[1] <= CORE[3] + M for p in P):
        continue                       # the core I-95 trench is already built
    cov = cover_flags(P, s, y)
    at_mouth = set()               # the points a written tunnel's mouth stands at (Round 226)
    sunk_solved.append((P, s, g, y, ek, cov, all(W[c]["hw"] == "motorway" for c in cids), at_mouth))
    # split at cover transitions FIRST: covered (tunnel) stretches must not dig
    # holes or grow walls in the app (the I-76 tunnel under 30th St stays buried)
    segs, cur, cov0 = [], [0], cov[0]
    for i in range(1, len(P)):
        cv = cov[i]
        if cv != cov0:
            cur.append(i)
            segs.append((cur, cov0))
            cur = [i]
            cov0 = cv
        else:
            cur.append(i)
    segs.append((cur, cov0))
    for idxs, cv in segs:
        if len(idxs) < 2:
            continue
        Pseg = [P[i] for i in idxs]
        yseg = [y[i] for i in idxs]
        prof = simplify_profile(Pseg, yseg)
        eks = (ek[0] if idxs[0] == 0 else 1, ek[1] if idxs[-1] == len(P) - 1 else 1)
        wrote = False
        for run, f0, f1 in emit_runs(Pseg, yseg, eks, prof):
            if run_len(run) > 40:
                rec = {"c": 0, "w": 12, "p": run, "e": [f0, f1], "cov": 1 if cv else 0}
                # Round 226: a tunnel under UNDERPASS_MAX that touches down at both its ends is an underpass the model
                # cannot dig (the profile gets 2 m down at most): the page took its road away for the tunnel's length
                # and left both ends on the lawn (the I-76 ramps under Broad Street by the arena). g: 1 hands the road
                # back to the page, which draws it through at grade
                if cv and f0 == 0 and f1 == 0 and run_len(run) < UNDERPASS_MAX:
                    rec["g"] = 1
                out_sk.append(rec)
                wrote = not rec.get("g")
        if cv and wrote:               # Round 226: its mouths, where open road or an approach meets it
            for i, step, far in ((idxs[0], 1, 0), (idxs[-1], -1, len(P) - 1)):
                if i == far and not APPROACH.get(P[i][3]):
                    continue
                dx, dz = P[i + step][0] - P[i][0], P[i + step][1] - P[i][1]
                L = math.hypot(dx, dz) or 1e-9
                mouths.append((P[i][0], P[i][1], y[i], dx / L, dz / L))
                at_mouth.add(i)

# Round 226: the approaches. Past a held mouth the plain road keeps the mouth's height until the ground has come down
# to it and is written as an open sunken run from the mouth to that point, ap: 1 (the page opens the ground over all
# of it, however shallow its far end). A ramp that leaves an approach while it is still under the ground climbs out
# at the motorway's 4.2% and runs one point on at grade, so the cut's wall breaks where it crosses (rp: 1).
for owner, (P0, s0, g0, y0, ek0, cov0, main0, am0) in enumerate(list(sunk_solved)):
    for end in (0, len(P0) - 1):
        plan = APPROACH.get(P0[end][3])
        if not plan:
            continue
        P, s, g = plan["P"], plan["s"], plan["g"]
        hold = y0[end]
        ya = []
        for i in range(len(P)):
            ya.append(min(g[i] + 0.3, hold))
            if i and g[i] + 0.3 <= hold + 0.05:
                break
        n = len(ya)
        if n < 2 or s[n - 1] < 40:
            continue
        Pa = P[:n]
        for i, q in enumerate(Pa):
            if q[3] is not None and q[3] not in node_y:
                node_y[q[3]] = ya[i]
        out_sk.append({"c": 0, "w": 12, "p": simplify_profile(Pa, ya), "e": [1, 0], "cov": 0, "ap": 1})
        approach_tracks.append((Pa, s[:n], g[:n], ya, owner))
        held = {w for w, _ in walk_plain(P0[end][3], P0[end][2], ("motorway",), APPROACH_MAX)}
        for i, q in enumerate(Pa[:-1]):
            if q[3] is None or g[i] - ya[i] < 1.3:
                continue
            for oid in ends.get(q[3], ()):
                o = W.get(oid)
                if (not o or oid in used or oid in held or o["hw"] != "motorway_link" or o["sunk"] or o["elev"]
                        or o["nds"][0] == o["nds"][-1]):
                    continue
                seq = list(o["nds"])
                if seq[0] != q[3]:
                    seq.reverse()
                Pr, sr = track_points([(oid, seq)] + walk_plain(seq[-1], oid, ("motorway_link",), 200))
                yr = []
                for k in range(len(Pr)):
                    gk = grade(Pr[k][0], Pr[k][1]) + 0.3
                    up = ya[i] + 0.042 * sr[k]
                    yr.append(min(gk, up))
                    if k and gk <= up:
                        if k + 1 < len(Pr):
                            yr.append(grade(Pr[k + 1][0], Pr[k + 1][1]) + 0.3)
                        break
                if len(yr) > 1 and sr[len(yr) - 1] >= 24:
                    out_sk.append({"c": 0, "w": 8, "p": simplify_profile(Pr[:len(yr)], yr), "e": [1, 0], "cov": 0,
                                   "ap": 1, "rp": 1})

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
    market = any(W[c]["market"] for c in cids)
    keep_core = market or any(W[c]["i95core"] or W[c]["core_ramp"] for c in cids)
    keep_nodes = {p[3] for p in P if p[3] is not None} if market else core_ramp_nodes if keep_core else ()
    prof = simplify_profile(P, y, keep_nodes=keep_nodes)
    cmin = min(W[c]["cls"] for c in cids)
    wmax = MARKET_DECK_W if market else max(W[c]["w"] for c in cids)
    for run, f0, f1 in emit_runs(P, y, ek, prof, keep_core):
        if run_len(run) < 24:
            continue
        record = {"c": cmin, "w": wmax, "p": run, "e": [f0, f1]}
        if keep_core:
            record["core"] = "market" if market else "i95" if any(W[c]["i95core"] for c in cids) else "i95-ramp"
        out_el.append(record)

# ---------------------------------------------------------------- Vine corridor
def corridor_runs():
    """One clean corridor from the TWO mainline carriageways (ramps excluded):
    even 12 m stations, clamped and smoothed width, smoothed floor.
    Round 226: the lead is still the longest sunken chain, but its partner is whichever other mainline carriageway
    lies beside it at each station (the second-longest chain alone left the cut fitted to one carriageway west of
    15th Street), a station is an OPEN point by cover_flags, and each mainline approach gets a run of its own for
    as long as both carriageways are still down. Returns the runs and, for each, its two ends' kinds (ce)."""
    if not sunk_solved:
        return [], []
    order = sorted(range(len(sunk_solved)), key=lambda k: -sunk_solved[k][1][-1])
    if len(order) < 2:
        return [], []
    lead = order[0]
    def partners(skip_owner):
        out = []
        for k, r in enumerate(sunk_solved):
            if k != skip_owner and r[6]:
                out.append((r[0], r[3]))
        for (Pa, sa, ga, ya, owner) in approach_tracks:
            if owner != skip_owner:
                out.append((Pa, ya))
        return out
    def nearest(tracks, x, z):
        """(distance, height) of the nearest partner point, or None past the end of its track."""
        best, hit = 1e18, None
        for P2, y2 in tracks:
            for j in range(len(P2)):
                d2 = (P2[j][0] - x) ** 2 + (P2[j][1] - z) ** 2
                if d2 < best:
                    best, hit = d2, (P2, y2, j)
        if hit is None or best >= 60 * 60:
            return None
        P2, y2, j = hit
        if j in (0, len(P2) - 1) and len(P2) > 1:
            k = 1 if j == 0 else len(P2) - 2
            dx, dz = P2[j][0] - P2[k][0], P2[j][1] - P2[k][1]
            L = math.hypot(dx, dz) or 1e-9
            if ((x - P2[j][0]) * dx + (z - P2[j][1]) * dz) / L > 12:
                return None
        return math.sqrt(best), y2[j], P2[j]
    def stations(P, y, g, is_open, tracks, need_partner):
        runs, cur = [], []
        for i in range(len(P)):
            depth = g[i] - y[i]
            st = None
            if is_open(i) and depth > 0.5:
                x, z = P[i][0], P[i][1]
                near = nearest(tracks, x, z)
                if near:
                    d, y2, q = near
                    cx, cz = (x + q[0]) / 2, (z + q[1]) / 2
                    hw = max(14.0, min(24.0, d / 2 + 12.5))
                    fy = min(y[i], y2) - 0.45
                elif not need_partner:
                    cx, cz, hw, fy = x, z, 14.0, y[i] - 0.45
                else:
                    cx = None
                if cx is not None:
                    st = [cx, cz, fy, hw]
            if st:
                cur.append(st)
            else:
                if len(cur) > 2:
                    runs.append(cur)
                cur = []
        if len(cur) > 2:
            runs.append(cur)
        return runs
    P, s, g, y, ek, cov, main, at_mouth = sunk_solved[lead]
    raw = [(run, False) for run in stations(P, y, g, lambda i: (not cov[i] and (i == 0 or not cov[i - 1])) or i in at_mouth, partners(lead), False)]
    for (Pa, sa, ga, ya, owner) in approach_tracks:
        if owner == lead:
            raw += [(run, True) for run in stations(Pa, ya, ga, lambda i: True, partners(owner), True)]
    out, kinds = [], []
    for run, is_ap in raw:
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
        kinds.append([0, 2 if is_ap else 0])
    return out, kinds
out_cor, out_ce = corridor_runs()

# Round 226: the portals. Each corridor end that a mouth stands at (the two carriageways' mouths lie within a few
# metres of each other along the road) is closed by one portal across the cut's whole width there; a mouth no
# corridor reaches gets a portal of its own roadway's width.
out_por = []
taken = set()
for ri, run in enumerate(out_cor):
    for e in (0, 1):
        st = run[0] if e == 0 else run[-1]
        near = [k for k, m in enumerate(mouths) if math.hypot(m[0] - st[0], m[1] - st[1]) < 36]
        if not near:
            continue
        taken.update(near)
        dx = sum(mouths[k][3] for k in near); dz = sum(mouths[k][4] for k in near)
        L = math.hypot(dx, dz) or 1e-9
        out_por.append([st[0], st[1], round(min(mouths[k][2] for k in near), 2), round(dx / L, 4), round(dz / L, 4), st[3]])
        out_ce[ri][e] = 1
for k, m in enumerate(mouths):
    if k not in taken:
        out_por.append([round(m[0], 1), round(m[1], 1), round(m[2], 2), round(m[3], 4), round(m[4], 4), 8.0])

# ---------------------------------------------------------------- report + write
tot_el = sum(run_len(c["p"]) for c in out_el)
tot_sk = sum(run_len(c["p"]) for c in out_sk)
tot_cor = sum(run_len(r) for r in out_cor)
with open(os.path.join(HERE, "overpasses.json"), "w") as f:
    json.dump({"el": out_el, "sk": out_sk, "cor": out_cor, "ce": out_ce, "por": out_por}, f, separators=(",", ":"))
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
print("Vine cut corridor runs x-extents:", [(round(r[0][0]), round(r[-1][0])) for r in out_cor], "ends", out_ce)
print("portals:", out_por)
print("approaches:", [(c["p"][0], c["p"][-1], "ramp" if c.get("rp") else "main") for c in out_sk if c.get("ap")])
print("underpasses drawn through at grade:", [(c["p"][0][:2], c["p"][-1][:2]) for c in out_sk if c.get("g")])
# Round 226, the sanity that would have caught it: a covered run whose mouth lies well under the ground has a portal
for c in out_sk:
    if not c["cov"] or c.get("g"):
        continue
    for q in (c["p"][0], c["p"][-1]):
        deep = grade(q[0], q[1]) - q[2]
        def off(o):
            best = 1e9
            for a, b in zip(o["p"], o["p"][1:]):
                dx, dz = b[0] - a[0], b[1] - a[1]
                t = max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dz) / (dx * dx + dz * dz or 1e-9)))
                best = min(best, math.hypot(a[0] + dx * t - q[0], a[1] + dz * t - q[1]))
            return best
        joins = any(o is not c and off(o) < 3 for o in out_sk)   # another run's roadway carries it on underground
        if deep > 3 and not joins and not any(math.hypot(q[0] - m[0], q[1] - m[1]) < 40 for m in out_por):
            print("  NOTE covered run end %.0f, %.0f lies %.1f m under the DEM with no portal" % (q[0], q[1], deep))
