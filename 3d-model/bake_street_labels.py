#!/usr/bin/env python3
"""Bake street-name label placements into street_labels.json.

The wide/far packed road formats carry no names, so labels are computed here
from the source scenes (scene.json core + scene_wide.json + scene_south.json)
and shipped as a small const via build.py. Each label: [nameIdx, x, z,
bearingDeg, cls] with cls 0 = major (motorway/trunk/primary/secondary),
1 = minor, 2 = core-detail streets (lower lift, denser spacing); cls + 3 is the
same street lettered at 0.75 of its height, cls + 6 at 0.6 and cls + 9 at 0.45
(Round 241: a name too long for every block within reach; app.js
STREET_TEXT_HEIGHT holds all twelve).

Round 241 (Mike: "the street names are now intersecting in the intersection. i
dont want that to happen in any intersection"): no label's text may pass within
a crossing street's half width plus its zebra (JX_ZEBRA) of that street's
centre line. A station slides along its street up to 96 m to the nearest block
its text fits in, then tries the smaller sizes, else it is dropped. Spans are
measured from street_sdf.json's own glyph widths when it is present, and the
names keep the order the previous street_labels.json gave them, so the atlas
stays aligned with them (rebake the atlas only when a name is new).

Rerun after refetching any scene json:  python3 bake_street_labels.py
"""
import json, math, pathlib

ROOT = pathlib.Path(__file__).parent
CORE = {"x0": -640, "x1": 770, "z0": -520, "z1": 850}   # CORE_EXT in app.js
MARGIN = 40

MAJOR = {"motorway", "trunk", "primary", "secondary"}
MINOR = {"tertiary", "residential", "unclassified", "living_street"}
SKIP = {"footway", "path", "steps", "cycleway", "service",
        "motorway_link", "trunk_link", "primary_link", "secondary_link"}

def in_core(x, z, m=MARGIN):
    return CORE["x0"] - m < x < CORE["x1"] + m and CORE["z0"] - m < z < CORE["z1"] + m

# Camden/NJ placements read as misplaced Philadelphia streets from across the
# river (both cities have a Market Street), so labels stop at the Delaware bank
DEL_BANK = [[13500, -21700], [10500, -18500], [7300, -14500], [4300, -10500], [2500, -7200],
            [1500, -4480], [900, -2600], [450, -1500], [404, -520], [345, 850], [700, 2200],
            [1300, 3600], [1500, 4400], [1000, 4900], [900, 5600], [1200, 6400], [3400, 7600], [5200, 9700]]
# (south of the stadiums this hugs the Philadelphia shore tighter than the app's
# terrain polyline: Gloucester City NJ sits west of the terrain line and its
# Market Street was leaking into the label set)
def east_of_delaware(x, z):
    for i in range(len(DEL_BANK) - 1):
        a, b = DEL_BANK[i], DEL_BANK[i + 1]
        if a[1] <= z <= b[1]:
            t = (z - a[1]) / max(1e-6, b[1] - a[1])
            return x > a[0] + (b[0] - a[0]) * t
    return x > (DEL_BANK[0][0] if z < DEL_BANK[0][1] else DEL_BANK[-1][0])

def place(pts, interval, min_len):
    """Yield (x, z, bearing_deg) along a polyline at ~interval spacing."""
    segs, total = [], 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L > 0.01:
            segs.append((a, b, L))
            total += L
    if total < min_len:
        return
    s = min(interval * 0.5, total / 2)
    while s < total:
        acc = 0.0
        for a, b, L in segs:
            if acc + L >= s:
                t = (s - acc) / L
                x = a[0] + (b[0] - a[0]) * t
                z = a[1] + (b[1] - a[1]) * t
                dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                # readable from a north-up view: text runs west->east / south->north
                if dx < -0.05 or (abs(dx) <= 0.05 and dz > 0):
                    dx, dz = -dx, -dz
                yield x, z, math.degrees(math.atan2(dz, dx)) % 360
                break
            acc += L
        s += interval

# ---- elevated decks and cut walls slice any label text they cross: keep
# ---- stations clear of them (overpasses.json is baked by bake_overpasses.py)
TH = [7.0, 5.6, 4.4]                     # text height by class (matches app.js)
ovp_segs = []                            # (ax, az, bx, bz, halfW)
ovp_path = ROOT / "overpasses.json"
if ovp_path.exists():
    _ov = json.loads(ovp_path.read_text())
    for c in _ov.get("el", []):
        hw = c["w"] / 2
        for a, b in zip(c["p"], c["p"][1:]):
            ovp_segs.append((a[0], a[1], b[0], b[1], hw))
    for run in _ov.get("cor", []):       # the cut's coping walls slice text too
        for a, b in zip(run, run[1:]):
            ovp_segs.append((a[0], a[1], b[0], b[1], (a[3] + b[3]) / 2))
ovp_grid = {}
for si, (ax, az, bx, bz, hw) in enumerate(ovp_segs):
    for gx in range(int(min(ax, bx) - 40) // 80, int(max(ax, bx) + 40) // 80 + 1):
        for gz in range(int(min(az, bz) - 40) // 80, int(max(az, bz) + 40) // 80 + 1):
            ovp_grid.setdefault((gx, gz), []).append(si)

def span_sliced(x, z, bdeg, half_len):
    """Does a label span centered at (x,z) cross under a deck or over a wall?"""
    b = math.radians(bdeg)
    ux, uz = math.cos(b), math.sin(b)
    steps = max(2, int(half_len // 4))
    for k in range(-steps, steps + 1):
        px, pz = x + ux * half_len * k / steps, z + uz * half_len * k / steps
        for si in ovp_grid.get((int(px) // 80, int(pz) // 80), ()):
            ax, az, bx, bz, hw = ovp_segs[si]
            dx, dz = bx - ax, bz - az
            L = math.hypot(dx, dz)
            if L < 0.05:
                continue
            if abs((dx * ux + dz * uz) / L) > 0.72:
                continue                 # aligned: the label rides this deck
            t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (L * L)))
            ex, ez = ax + dx * t - px, az + dz * t - pz
            if ex * ex + ez * ez < (hw + 1.2) ** 2:
                return True
    return False

def near_way(way_pts, x, z, tol=5.0):
    for a, b in zip(way_pts, way_pts[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / L2))
        ex, ez = a[0] + dx * t - x, a[1] + dz * t - z
        if ex * ex + ez * ez < tol * tol:
            return True
    return False

# ---- Round 241: the streets a label's text must keep out of (the drawn ones:
# ---- the wide and south sets carry no service way, the core draws its own)
DRIVE = {"trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "living_street"}
JX_ZEBRA = 4.0            # past a crossing street's kerb line: its zebra ends 3.8 m out (app.js lane paint)
JX_ROUND = 1.0            # and a metre more, which the whole-metre position and whole-degree bearing written out can take back
JX_COS = 0.866            # a street within 30 degrees of the label's bearing runs along it, not across it
JX_OFFS = [0] + [s * k for k in range(8, 104, 8) for s in (1, -1)]
JX_SIZES = (1.0, 0.75, 0.6, 0.45)
jx_segs = []              # (ax, az, bx, bz, half width)
for _fn, _core in (("scene.json", True), ("scene_wide.json", False), ("scene_south.json", False)):
    _p = ROOT / _fn
    if not _p.exists():
        continue
    for _r in json.loads(_p.read_text()).get("roads", []):
        if not (_r.get("t") in DRIVE or (_core and _r.get("t") == "service")):
            continue
        for a, b in zip(_r["pts"], _r["pts"][1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 0.3:
                jx_segs.append((a[0], a[1], b[0], b[1], _r.get("w", 7) / 2))
jx_grid = {}
for si, (ax, az, bx, bz, hw) in enumerate(jx_segs):
    for gx in range(int(min(ax, bx)) // 60 - 1, int(max(ax, bx)) // 60 + 2):
        for gz in range(int(min(az, bz)) // 60 - 1, int(max(az, bz)) // 60 + 2):
            jx_grid.setdefault((gx, gz), []).append(si)

def seg_dist(p1x, p1z, p2x, p2z, ax, az, bx, bz):
    """The least distance between two segments (0 where they cross)."""
    def pd(px, pz, qx, qz, rx, rz):
        dx, dz = rx - qx, rz - qz
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((px - qx) * dx + (pz - qz) * dz) / L2))
        return math.hypot(qx + dx * t - px, qz + dz * t - pz)
    def side(ox, oz, px, pz, qx, qz):
        return (qx - ox) * (pz - oz) - (qz - oz) * (px - ox)
    if (side(p1x, p1z, p2x, p2z, ax, az) > 0) != (side(p1x, p1z, p2x, p2z, bx, bz) > 0) and \
       (side(ax, az, bx, bz, p1x, p1z) > 0) != (side(ax, az, bx, bz, p2x, p2z) > 0):
        return 0.0
    return min(pd(p1x, p1z, ax, az, bx, bz), pd(p2x, p2z, ax, az, bx, bz),
               pd(ax, az, p1x, p1z, p2x, p2z), pd(bx, bz, p1x, p1z, p2x, p2z))

def span_in_junction(x, z, bdeg, half_len):
    """Does a label span centred at (x, z) come within a crossing street's half
    width plus JX_ZEBRA of its centre line (its junction box or a zebra)?"""
    b = math.radians(bdeg)
    ux, uz = math.cos(b), math.sin(b)
    p1x, p1z, p2x, p2z = x - ux * half_len, z - uz * half_len, x + ux * half_len, z + uz * half_len
    seen = set()
    for gx in range(int(min(p1x, p2x)) // 60, int(max(p1x, p2x)) // 60 + 1):
        for gz in range(int(min(p1z, p2z)) // 60, int(max(p1z, p2z)) // 60 + 1):
            for si in jx_grid.get((gx, gz), ()):
                if si in seen:
                    continue
                seen.add(si)
                ax, az, bx, bz, hw = jx_segs[si]
                L = math.hypot(bx - ax, bz - az)
                if abs(((bx - ax) * ux + (bz - az) * uz) / L) > JX_COS:
                    continue             # along the label: its own street, or one beside it
                if seg_dist(p1x, p1z, p2x, p2z, ax, az, bx, bz) < hw + JX_ZEBRA + JX_ROUND:
                    return True
    return False

# the glyph widths the page letters with (street_sdf.json, in the names' order), else an estimate
_sdf_path = ROOT / "street_sdf.json"
_sdf = json.loads(_sdf_path.read_text()) if _sdf_path.exists() else None

def half_length(name, cls):
    est = len(name) * 0.34 * TH[cls]
    i = name_idx.get(name)
    if _sdf and i is not None and i < len(_sdf["rects"]) and _sdf["rects"][i]:
        return TH[cls] * _sdf["rects"][i][2] / _sdf["fs"] / 2, est
    return est, est

def clear_station(x, z, bdeg, name, cls, way_pts):
    """Slide a station along its bearing to the nearest place its text clears every
    deck and every junction (the slid point must still lie on the street: the bearing
    drifts on curves), at the full size, then 0.75 and 0.6 of it. (x, z, size) or None."""
    full, est = half_length(name, cls)
    b = math.radians(bdeg)
    ux, uz = math.cos(b), math.sin(b)
    for size, k in enumerate(JX_SIZES):
        for off in JX_OFFS:
            nx, nz = x + ux * off, z + uz * off
            if off and not near_way(way_pts, nx, nz):
                continue
            if span_sliced(nx, nz, bdeg, max(full, est) * k):
                continue
            if span_in_junction(nx, nz, bdeg, full * k):
                continue
            return nx, nz, size
    return None

names, name_idx = [], {}
# Round 241: the names in the order the shipped file gives them (the atlas, street_sdf.json, is aligned with it)
_prev = ROOT / "street_labels.json"
if _prev.exists():
    for _nm in json.loads(_prev.read_text()).get("names", []):
        name_idx[_nm] = len(names)
        names.append(_nm)
placed = {}   # name -> list of (x, z) for the 90 m same-name dedupe
out = []
stats = {"stations": 0, "sizes": [0, 0, 0, 0], "dropped": 0}

def add(name, x, z, b, cls):
    key = name
    for px, pz in placed.get(key, ()):
        if math.hypot(px - x, pz - z) < 90:
            return
    placed.setdefault(key, []).append((x, z))
    if name not in name_idx:
        name_idx[name] = len(names)
        names.append(name)
    out.append([name_idx[name], round(x), round(z), round(b) % 360, cls])

# --- core: dense, includes charming named alleys/pedestrian ways ---
core = json.loads((ROOT / "scene.json").read_text())
for r in core.get("roads", []):
    nm, t = r.get("name"), r.get("t", "")
    if not nm or t in ("footway", "steps", "cycleway", "path"):
        continue
    # ramps carry DESTINATION names in OSM (the I-95 links down the trench are
    # all named Market Street) — never letter a link with its target's name
    if "link" in t:
        continue
    for x, z, b in place(r["pts"], 220, 40):
        if east_of_delaware(x, z):
            continue
        stats["stations"] += 1
        cs = clear_station(x, z, b, nm, 2, r["pts"])
        if cs is None:
            stats["dropped"] += 1
            continue
        stats["sizes"][cs[2]] += 1
        add(nm, cs[0], cs[1], b, 2 + 3 * cs[2])

# --- wide + south: drivable named streets, outside the core box ---
for fn in ("scene_wide.json", "scene_south.json"):
    p = ROOT / fn
    if not p.exists():
        continue
    d = json.loads(p.read_text())
    for r in d.get("roads", []):
        nm, t = r.get("name"), r.get("t", "")
        if not nm or t in SKIP:
            continue
        if t in MAJOR:
            cls, interval, min_len = 0, (600 if t == "motorway" else 350), (200 if t == "motorway" else 70)
        elif t in MINOR:
            cls, interval, min_len = 1, 300, 70
        else:
            continue
        for x, z, b in place(r["pts"], interval, min_len):
            if in_core(x, z) or east_of_delaware(x, z):
                continue
            stats["stations"] += 1
            cs = clear_station(x, z, b, nm, cls, r["pts"])
            if cs is None:
                stats["dropped"] += 1
                continue
            stats["sizes"][cs[2]] += 1
            add(nm, cs[0], cs[1], b, cls + 3 * cs[2])

data = {"names": names, "l": [v for lbl in out for v in lbl]}
(ROOT / "street_labels.json").write_text(json.dumps(data, separators=(",", ":")))
print(f"street_labels.json: {len(out)} labels, {len(names)} unique names, "
      f"{(ROOT / 'street_labels.json').stat().st_size / 1024:.0f} KB; "
      f"{stats['stations']} stations: {stats['sizes'][0]} full size, {stats['sizes'][1]} at 0.75, "
      f"{stats['sizes'][2]} at 0.6, {stats['sizes'][3]} at 0.45, {stats['dropped']} with no block their name fits")
