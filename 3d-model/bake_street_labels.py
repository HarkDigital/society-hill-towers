#!/usr/bin/env python3
"""Bake street-name label placements into street_labels.json.

The wide/far packed road formats carry no names, so labels are computed here
from the source scenes (scene.json core + scene_wide.json + scene_south.json)
and shipped as a small const via build.py. Each label: [nameIdx, x, z,
bearingDeg, cls] with cls 0 = major (motorway/trunk/primary/secondary),
1 = minor, 2 = core-detail streets (lower lift, denser spacing).

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

names, name_idx = [], {}
placed = {}   # name -> list of (x, z) for the 90 m same-name dedupe
out = []

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
    for x, z, b in place(r["pts"], 220, 40):
        add(nm, x, z, b, 2)

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
            if in_core(x, z):
                continue
            add(nm, x, z, b, cls)

data = {"names": names, "l": [v for lbl in out for v in lbl]}
(ROOT / "street_labels.json").write_text(json.dumps(data, separators=(",", ":")))
print(f"street_labels.json: {len(out)} labels, {len(names)} unique names, "
      f"{(ROOT / 'street_labels.json').stat().st_size / 1024:.0f} KB")
