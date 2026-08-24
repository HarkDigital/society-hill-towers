#!/usr/bin/env python3
"""Convert Overpass OSM JSON to compact scene.json for Three.js city model."""
import json, math, re, sys, os

SCRATCH = os.environ.get("SHT_DIR", os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(SCRATCH, os.environ.get("SHT_RAW", "osm_raw.json"))
OUT = os.path.join(SCRATCH, os.environ.get("SHT_OUT", "scene.json"))

TOWER_IDS = [194835183, 194835184, 194835182]  # north, west, south (any order ok)

with open(RAW) as f:
    data = json.load(f)

nodes = {}
ways = {}
rels = []
for el in data["elements"]:
    t = el["type"]
    if t == "node":
        nodes[el["id"]] = (el["lat"], el["lon"], el.get("tags"))
    elif t == "way":
        ways[el["id"]] = el
    elif t == "relation":
        rels.append(el)

notes = []

# ---------- origin: centroid of the three tower footprints ----------
def ring_latlon(way):
    ids = way["nodes"]
    if ids[0] == ids[-1]:
        ids = ids[:-1]
    return [(nodes[i][0], nodes[i][1]) for i in ids]

def poly_centroid_xy(pts):
    """Area-weighted centroid of polygon given as [(x,y)...]. Falls back to mean."""
    a = 0.0; cx = 0.0; cy = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        cr = x1 * y2 - x2 * y1
        a += cr
        cx += (x1 + x2) * cr
        cy += (y1 + y2) * cr
    if abs(a) < 1e-9:
        return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))

# rough reference for centroid computation
tower_rings_ll = {tid: ring_latlon(ways[tid]) for tid in TOWER_IDS}
all_ll = [p for r in tower_rings_ll.values() for p in r]
lat_r = sum(p[0] for p in all_ll) / len(all_ll)
lon_r = sum(p[1] for p in all_ll) / len(all_ll)
cosr = math.cos(math.radians(lat_r))

cent_ll = []
for tid in TOWER_IDS:
    pts = [((lon - lon_r) * 111320 * cosr, (lat - lat_r) * 110574) for lat, lon in tower_rings_ll[tid]]
    cx, cy = poly_centroid_xy(pts)
    cent_ll.append((lat_r + cy / 110574, lon_r + cx / (111320 * cosr)))
lat0 = sum(c[0] for c in cent_ll) / 3
lon0 = sum(c[1] for c in cent_ll) / 3
COS0 = math.cos(math.radians(lat0))

def to_xz(lat, lon):
    x = (lon - lon0) * 111320 * COS0
    north = (lat - lat0) * 110574
    return (round(x, 2), round(-north, 2))

def way_pts(way, close=False):
    ids = way["nodes"]
    if not close and len(ids) > 1 and ids[0] == ids[-1]:
        ids = ids[:-1]
    pts = []
    for i in ids:
        if i not in nodes:
            return None
        lat, lon, _ = nodes[i]
        pts.append(list(to_xz(lat, lon)))
    return pts

def dedupe(pts):
    out = []
    for p in pts:
        if not out or p != out[-1]:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out

def shoelace(pts):
    """Signed area in (x,z) plane, standard math convention: positive = CCW."""
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, z1 = pts[i]
        x2, z2 = pts[(i + 1) % n]
        a += x1 * z2 - x2 * z1
    return a * 0.5

def ensure_ccw(pts):
    return pts if shoelace(pts) > 0 else pts[::-1]

def ensure_cw(pts):
    return pts if shoelace(pts) < 0 else pts[::-1]

# ---------- height parsing ----------
FT = 0.3048
def parse_len(s):
    if s is None:
        return None
    s = str(s).strip().lower().replace(",", ".")
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*'\s*(?:(\d+(?:\.\d+)?)\s*\")?$", s)
    if m:
        v = float(m.group(1)) + (float(m.group(2)) / 12 if m.group(2) else 0)
        return v * FT
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(ft|feet|foot)\.?$", s)
    if m:
        return float(m.group(1)) * FT
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(m|meter|meters|metre|metres)?\.?$", s)
    if m:
        return float(m.group(1))
    return None

TYPE_H = {
    "church": 14, "cathedral": 14, "chapel": 14,
    "synagogue": 12,
    "garage": 10, "garages": 10, "parking": 10,
    "retail": 6, "commercial": 6,
    "school": 12,
    "hotel": 15,
    "apartments": 15,
    "house": 10.5, "residential": 10.5, "terrace": 10.5, "rowhouse": 10.5,
}

def building_height(tags, area):
    h = parse_len(tags.get("height"))
    if h is not None and h > 0:
        return h
    lv = tags.get("building:levels")
    if lv is not None:
        try:
            return float(str(lv).strip()) * 3.3 + 1.5
        except ValueError:
            pass
    b = tags.get("building", "yes")
    if b in TYPE_H:
        return TYPE_H[b]
    return 11 if area < 300 else 13

def building_type(tags):
    if tags.get("amenity") == "place_of_worship":
        return "worship"
    b = tags.get("building", "yes")
    return "generic" if b in ("yes", "", None) else b

# ---------- minimal-area oriented rectangle ----------
def min_area_rect(pts):
    best = None
    step = math.radians(0.25)
    n_steps = int(round(math.radians(180) / step))
    for k in range(n_steps):
        th = k * step
        c, s = math.cos(th), math.sin(th)
        us = [p[0] * c + p[1] * s for p in pts]
        vs = [-p[0] * s + p[1] * c for p in pts]
        umin, umax = min(us), max(us)
        vmin, vmax = min(vs), max(vs)
        area = (umax - umin) * (vmax - vmin)
        if best is None or area < best[0]:
            best = (area, th, umin, umax, vmin, vmax)
    _, th, umin, umax, vmin, vmax = best
    c, s = math.cos(th), math.sin(th)
    du, dv = umax - umin, vmax - vmin
    corners_uv = [(umin, vmin), (umax, vmin), (umax, vmax), (umin, vmax)]
    corners = [[round(u * c - v * s, 2), round(u * s + v * c, 2)] for u, v in corners_uv]
    if du >= dv:
        width, depth, ang = du, dv, th
    else:
        width, depth, ang = dv, du, th + math.pi / 2
    ang = ang % math.pi
    return corners, ang, width, depth

# ---------- towers ----------
towers = []
for tid in TOWER_IDS:
    w = ways[tid]
    tags = w.get("tags", {})
    pts = dedupe(way_pts(w))
    cx, cz = poly_centroid_xy(pts)
    corners, ang, width, depth = min_area_rect(pts)
    towers.append({
        "name": tags.get("name", f"way/{tid}"),
        "centroid": [round(cx, 2), round(cz, 2)],
        "corners": corners,
        "angleRad": round(ang, 4),
        "width_m": round(width, 2),
        "depth_m": round(depth, 2),
        "h": building_height(tags, abs(shoelace(pts))),
    })

# ---------- buildings ----------
buildings = []
skipped = {"degenerate_building": 0, "bad_relation": 0, "open_pier": 0,
           "missing_nodes": 0, "degenerate_area": 0}
tower_set = set(TOWER_IDS)

def add_building(outer, holes, tags):
    outer = dedupe(outer)
    if len(outer) < 3:
        skipped["degenerate_building"] += 1
        return
    area = abs(shoelace(outer))
    if area < 1:
        skipped["degenerate_building"] += 1
        return
    outer = ensure_ccw(outer)
    entry = {"poly": outer}
    good_holes = []
    for hpts in holes:
        hpts = dedupe(hpts)
        if len(hpts) >= 3 and abs(shoelace(hpts)) >= 1:
            good_holes.append(ensure_cw(hpts))
    if good_holes:
        entry["holes"] = good_holes
    entry["h"] = round(building_height(tags, area), 2)
    mh = parse_len(tags.get("min_height"))
    if mh:
        entry["minH"] = round(mh, 2)
    name = tags.get("name")
    if name:
        entry["name"] = name
    entry["t"] = building_type(tags)
    buildings.append(entry)

# building ways
for wid, w in ways.items():
    tags = w.get("tags") or {}
    if "building" not in tags or wid in tower_set:
        continue
    pts = way_pts(w)
    if pts is None:
        skipped["missing_nodes"] += 1
        continue
    add_building(pts, [], tags)

# ring assembly for relations
def assemble_rings(members_ways):
    """members_ways: list of node-id lists. Returns list of closed rings (node id lists) or None."""
    segs = [list(m) for m in members_ways if len(m) >= 2]
    rings = []
    while segs:
        ring = segs.pop(0)
        while ring[0] != ring[-1]:
            found = False
            for i, s in enumerate(segs):
                if s[0] == ring[-1]:
                    ring += s[1:]; segs.pop(i); found = True; break
                if s[-1] == ring[-1]:
                    ring += s[::-1][1:]; segs.pop(i); found = True; break
                if s[-1] == ring[0]:
                    ring = s[:-1] + ring; segs.pop(i); found = True; break
                if s[0] == ring[0]:
                    ring = s[::-1][:-1] + ring; segs.pop(i); found = True; break
            if not found:
                return None
        rings.append(ring[:-1])
    return rings

def ids_to_pts(ids):
    pts = []
    for i in ids:
        if i not in nodes:
            return None
        lat, lon, _ = nodes[i]
        pts.append(list(to_xz(lat, lon)))
    return pts

def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside

rel_area_entries = []
for rel in rels:
    tags = rel.get("tags") or {}
    is_bldg = "building" in tags
    is_park = tags.get("leisure") in ("park", "garden", "playground", "pitch")
    if not (is_bldg or is_park):
        continue
    outers_m, inners_m = [], []
    ok = True
    for m in rel.get("members", []):
        if m["type"] != "way":
            continue
        w = ways.get(m["ref"])
        if w is None:
            ok = False
            break
        (outers_m if m.get("role") != "inner" else inners_m).append(w["nodes"])
    if not ok:
        skipped["bad_relation"] += 1
        notes.append(f"relation {rel['id']}: member way missing, skipped")
        continue
    outer_rings = assemble_rings(outers_m)
    inner_rings = assemble_rings(inners_m) if inners_m else []
    if outer_rings is None or inner_rings is None or not outer_rings:
        skipped["bad_relation"] += 1
        notes.append(f"relation {rel['id']}: ring assembly failed, skipped")
        continue
    outer_pts = [ids_to_pts(r) for r in outer_rings]
    inner_pts = [ids_to_pts(r) for r in inner_rings]
    if any(p is None for p in outer_pts) or any(p is None for p in inner_pts):
        skipped["bad_relation"] += 1
        notes.append(f"relation {rel['id']}: missing nodes, skipped")
        continue
    if is_bldg:
        for op in outer_pts:
            od = dedupe(op)
            if len(od) < 3:
                continue
            holes = [ip for ip in inner_pts
                     if len(dedupe(ip)) >= 3 and point_in_poly(dedupe(ip)[0], od)]
            add_building(op, holes, tags)
    else:
        for op in outer_pts:
            od = dedupe(op)
            if len(od) >= 3 and abs(shoelace(od)) >= 1:
                rel_area_entries.append({"kind": "park", "poly": ensure_ccw(od)})
            else:
                skipped["degenerate_area"] += 1

# ---------- roads ----------
ROAD_W = {
    "motorway": 16, "trunk": 16,
    "motorway_link": 8, "trunk_link": 8,
    "primary": 13, "secondary": 11, "tertiary": 9,
    "primary_link": 8, "secondary_link": 7, "tertiary_link": 7,
    "residential": 7, "unclassified": 7,
    "living_street": 6, "service": 4, "pedestrian": 5,
    "footway": 2.5, "path": 2.5, "steps": 2.5, "cycleway": 2.5,
}
roads = []
columbus_x = []
for wid, w in ways.items():
    tags = w.get("tags") or {}
    hw = tags.get("highway")
    if not hw or hw in ("proposed", "construction", "corridor"):
        continue
    pts = way_pts(w, close=True)
    if pts is None or len(pts) < 2:
        skipped["missing_nodes"] += 1
        continue
    entry = {"pts": pts, "w": ROAD_W.get(hw, 5), "t": hw}
    name = tags.get("name")
    if name:
        entry["name"] = name
        nl = name.lower()
        if "columbus" in nl or "delaware ave" in nl:
            columbus_x.extend(p[0] for p in pts)
    roads.append(entry)

# ---------- areas ----------
areas = []
for wid, w in ways.items():
    tags = w.get("tags") or {}
    kind = None
    if tags.get("leisure") in ("park", "garden", "playground", "pitch"):
        kind = "park"
    elif tags.get("man_made") == "pier":
        closed = w["nodes"][0] == w["nodes"][-1]
        if not closed:
            skipped["open_pier"] += 1
            continue
        kind = "pier"
    elif tags.get("natural") == "water":
        kind = "water"
    if kind is None:
        continue
    pts = way_pts(w)
    if pts is None:
        skipped["missing_nodes"] += 1
        continue
    pts = dedupe(pts)
    if len(pts) < 3 or abs(shoelace(pts)) < 1:
        skipped["degenerate_area"] += 1
        continue
    areas.append({"kind": kind, "poly": ensure_ccw(pts)})
areas.extend(rel_area_entries)

# ---------- trees ----------
trees = []
for nid, (lat, lon, tags) in nodes.items():
    if tags and tags.get("natural") == "tree":
        x, z = to_xz(lat, lon)
        trees.append([x, z])

# ---------- write scene ----------
scene = {
    "origin": {"lat": lat0, "lon": lon0},
    "towers": towers,
    "buildings": buildings,
    "roads": roads,
    "areas": areas,
    "trees": trees,
}
with open(OUT, "w") as f:
    json.dump(scene, f, separators=(",", ":"))

# ---------- report ----------
xs, zs = [], []
def take(pts):
    for x, z in pts:
        xs.append(x); zs.append(z)
for t in towers:
    take(t["corners"])
for b in buildings:
    take(b["poly"])
    for h in b.get("holes", []):
        take(h)
for r in roads:
    take(r["pts"])
for a in areas:
    take(a["poly"])
take(trees)
bounds = {"minX": round(min(xs), 2), "maxX": round(max(xs), 2),
          "minZ": round(min(zs), 2), "maxZ": round(max(zs), 2)}

tall = []
for t in towers:
    tall.append({"name": t["name"], "h": round(t["h"], 1),
                 "centroid": [round(t["centroid"][0]), round(t["centroid"][1])]})
for b in buildings:
    if "name" in b and b["h"] > 25:
        cx, cz = poly_centroid_xy(b["poly"])
        tall.append({"name": b["name"], "h": round(b["h"], 1),
                     "centroid": [round(cx), round(cz)]})
tall = [t for t in tall if t["h"] > 25]
tall.sort(key=lambda e: -e["h"])
tall = tall[:25]

# validation
with open(OUT) as f:
    check = json.load(f)
assert len(check["towers"]) == 3, "expected 3 towers"
assert len(check["buildings"]) > 2000, f"only {len(check['buildings'])} buildings"

report = {
    "counts": {"buildings": len(buildings), "roads": len(roads),
               "areas": len(areas), "trees": len(trees)},
    "area_kinds": {k: sum(1 for a in areas if a["kind"] == k) for k in ("park", "pier", "water")},
    "bounds": bounds,
    "towers": towers,
    "columbusXRange": [round(min(columbus_x), 2), round(max(columbus_x), 2)] if columbus_x else None,
    "tallNamed": tall,
    "origin": {"lat": lat0, "lon": lon0},
    "sceneBytes": os.path.getsize(OUT),
    "skipped": skipped,
    "notes": notes,
}
with open(os.path.join(SCRATCH, os.environ.get("SHT_REPORT", "report.json")), "w") as f:
    json.dump(report, f, indent=1)
print(json.dumps(report, indent=1))
