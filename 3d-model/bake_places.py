#!/usr/bin/env python3
"""lidar_cache/places_raw/*.geojson -> places.json : historic-district outlines
plus neighborhood name labels, baked into the local frame for the app.
  {"hd": [{"n": name, "lbl": [x, z] | null, "rings": [[x1,z1,...], ...]}, ...],
   "nb": {"names": [...], "l": [nameIdx, x, z, cls, ...]}}
Districts: Philadelphia Register outlines, Douglas-Peucker 3 m, outer rings only.
The 'Historic Street Paving Thematic District' (9,672 scattered curb segments,
not an outline) is excluded by name. A district's LABEL is dropped when a kept
neighborhood label lands inside it (Society Hill the district ≡ Society Hill
the neighborhood); its ribbon always stays.
Neighborhoods: MAPNAME at the largest ring's centroid; size class by Shape_Area
(sq ft); labels within 250 m of a bigger neighborhood's label are thinned.
Frame: philly_frame.py (the scene's own projection). This script used to hardcode
KX=85350, which put its output up to ~1.1 m east of the scene at the far ring;
the committed places.json keeps that offset until the next rerun."""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'places_raw')
from philly_frame import LON0, LAT0, KX, KZ   # the one scene frame
EXCLUDE = 'Historic Street Paving Thematic District'
SQFT_3KM2, SQFT_1KM2 = 3.2292e7, 1.0764e7

def proj(lon, lat):
    return (lon - LON0) * KX, (LAT0 - lat) * KZ

def simplify(pts, tol):
    # Douglas-Peucker on a closed ring (pack_wide.py's version, kept in sync)
    if len(pts) <= 4:
        return pts
    def dp(seg):
        if len(seg) < 3:
            return seg
        a, b = seg[0], seg[-1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz) or 1e-9
        best, bi = -1, -1
        for i in range(1, len(seg) - 1):
            p = seg[i]
            dist = abs((p[0] - a[0]) * dz - (p[1] - a[1]) * dx) / L
            if dist > best:
                best, bi = dist, i
        if best > tol:
            return dp(seg[:bi + 1])[:-1] + dp(seg[bi:])
        return [a, b]
    far = max(range(1, len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    out = dp(pts[:far + 1])[:-1] + dp(pts[far:] + [pts[0]])[:-1]
    return out if len(out) >= 3 else pts

def ring_area_centroid(pts):
    a = cx = cz = 0.0
    for i in range(len(pts)):
        u, v = pts[i], pts[(i + 1) % len(pts)]
        w = u[0] * v[1] - v[0] * u[1]
        a += w
        cx += (u[0] + v[0]) * w
        cz += (u[1] + v[1]) * w
    a *= 0.5
    if abs(a) < 1e-6:
        xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
        return 0.0, sum(xs) / len(xs), sum(zs) / len(zs)
    return abs(a), cx / (6 * a), cz / (6 * a)

def pip(x, z, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, zi = pts[i]; xj, zj = pts[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside

def outer_rings(geom):
    """Projected outer ring(s) of a (Multi)Polygon, without the closing repeat."""
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    rings = []
    for p in polys:
        ring = [proj(lon, lat) for lon, lat in p[0]]
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]
        if len(ring) >= 3:
            rings.append(ring)
    return rings

def main():
    hd_raw = json.load(open(os.path.join(RAW, 'historic_districts.geojson')))
    nb_raw = json.load(open(os.path.join(RAW, 'neighborhoods.geojson')))

    # ---- neighborhoods first (their labels drive the district-label dedupe)
    cands = []
    for f in nb_raw['features']:
        name = (f['properties'].get('MAPNAME') or f['properties'].get('NAME') or '').strip()
        if not name:
            continue
        area_sqft = f['properties'].get('Shape_Area') or 0
        best = None
        for ring in outer_rings(f['geometry']):
            a, cx, cz = ring_area_centroid(ring)
            if best is None or a > best[0]:
                best = (a, cx, cz, ring)
        if not best:
            continue
        a, cx, cz, ring = best
        if not pip(cx, cz, ring):                      # concave shapes: centroid outside
            cx = sum(p[0] for p in ring) / len(ring)
            cz = sum(p[1] for p in ring) / len(ring)
        cls = 0 if area_sqft >= SQFT_3KM2 else 1 if area_sqft >= SQFT_1KM2 else 2
        cands.append((area_sqft, name, cx, cz, cls))
    cands.sort(key=lambda c: -c[0])
    nb_kept, dropped = [], []
    for area_sqft, name, cx, cz, cls in cands:
        if any((cx - k[1]) ** 2 + (cz - k[2]) ** 2 < 250 ** 2 for k in nb_kept):
            dropped.append(name)
            continue
        nb_kept.append((name, cx, cz, cls))
    names = [k[0] for k in nb_kept]
    flat = []
    for i, (_n, cx, cz, cls) in enumerate(nb_kept):
        flat += [i, round(cx, 1), round(cz, 1), cls]

    # ---- historic districts
    hd_out = []
    for f in hd_raw['features']:
        name = (f['properties'].get('name') or '').strip()
        if not name or name == EXCLUDE:
            continue
        rings = [simplify(r, 3.0) for r in outer_rings(f['geometry'])]
        rings = [r for r in rings if len(r) >= 3]
        if not rings:
            continue
        biggest = max(rings, key=lambda r: ring_area_centroid(r)[0])
        _a, cx, cz = ring_area_centroid(biggest)
        lbl = None if any(pip(nx, nz, biggest) for _n2, nx, nz, _c in nb_kept) else [round(cx, 1), round(cz, 1)]
        hd_out.append({'n': name, 'lbl': lbl,
                       'rings': [[round(v, 1) for pt in r for v in pt] for r in rings]})

    out = {'hd': hd_out, 'nb': {'names': names, 'l': flat}}
    path = os.path.join(HERE, 'places.json')
    json.dump(out, open(path, 'w'), separators=(',', ':'))
    n_lbl = sum(1 for d in hd_out if d['lbl'])
    n_pts = sum(len(r) // 2 for d in hd_out for r in d['rings'])
    print(f'{len(hd_out)} districts ({n_lbl} labeled, {n_pts} outline pts), '
          f'{len(nb_kept)} neighborhood labels (thinned {len(dropped)}: {", ".join(dropped[:6])}{"..." if len(dropped) > 6 else ""})')
    print(f'places.json {os.path.getsize(path) / 1e3:.1f} KB', flush=True)

if __name__ == '__main__':
    main()
