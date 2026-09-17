#!/usr/bin/env python3
"""lidar_cache/markers_raw/{phmc.json, percent_for_art.geojson} -> markers.json : the
historical markers and the public art in the local frame for the app (Round 77).
  {"m": [[x, z, type, year, name, location, text], ...],      # PHMC: type 0 Roadside, 1 City, 2 Plaque
   "a": [[x, z, mat, title, artist, date, medium, where, img], ...]}   # Percent for Art
Whole metres, arrays not objects (the keys would repeat 587 times). PHMC rows keep every
marker with a coordinate inside the far-ring box; the year is the dedication date's; two
markers on one coordinate (seven pairs in the state's file) are nudged 2 m apart along x.
A point that lies inside one of the page's building footprints (scene.json's core polys and
the packed outer districts and far ring, decoded by tests/_common.py) is stepped 2.5 m out
past the nearest wall, since a post inside a building mass is a post nobody sees: geocodes
land on the building's address, and the Clothespin's buffer centroid lies inside Centre
Square's podium.
Percent for Art keeps the works whose status is Active (the Inaccessible interior works and
the ones In Progress are dropped); the 40 m buffer polygon's centroid is the spot; mat is a
scan of the medium (0 bronze, 1 steel or aluminum, 2 stone or concrete, 3 anything else); the
image link is kept only on the city's own S3 bucket and never inlined; the streetview links
and the neighborhood are dropped. Every string loses its dashes and middots (the HUD rule)
and its doubled whitespace, and none may contain '</script' (build.py refuses the page).
Frame: philly_frame.py (the scene's own projection).
Run with plain python3; bake() is pure so tests/test_markers_bake.py can feed it fixtures."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'markers_raw')
OUT = os.path.join(HERE, 'markers.json')
from philly_frame import to_xz   # the one scene frame

CITY = (-12000, 16500, -21700, 9700)   # pack_city.py's box: x0, x1, z0, z1
TYPES = {'roadside': 0, 'city': 1, 'plaque': 2}
IMG_HOST = 'https://dpd-art-is-essential-docs.s3.amazonaws.com/'
DASHES = re.compile('[‒–—―·•]')


def clean(s):
    """Trim, collapse whitespace, and turn dashes and middots into commas (the HUD rule)."""
    if not s:
        return ''
    s = DASHES.sub(', ', str(s))
    s = re.sub(r'\s+,', ',', s)
    s = re.sub(r',(\s*,)+', ',', s)
    s = re.sub(r'\s+', ' ', s).strip(' ,')
    if '</script' in s.lower():
        raise ValueError('a string carries </script: ' + s[:80])
    return s


def ring_centroid(ring):
    a = cx = cz = 0.0
    n = len(ring)
    for i in range(n):
        (x0, z0), (x1, z1) = ring[i], ring[(i + 1) % n]
        w = x0 * z1 - x1 * z0
        a += w
        cx += (x0 + x1) * w
        cz += (z0 + z1) * w
    if abs(a) < 1e-9:
        return sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n
    return cx / (3 * a), cz / (3 * a)


def art_material(medium):
    m = (medium or '').lower()
    if 'bronze' in m or 'brass' in m or 'copper' in m:
        return 0
    if 'steel' in m or 'aluminum' in m or 'aluminium' in m or 'iron' in m or 'metal' in m:
        return 1
    if 'granite' in m or 'stone' in m or 'marble' in m or 'concrete' in m or 'limestone' in m or 'brick' in m:
        return 2
    return 3


def bake_markers(rows):
    out = []
    for r in rows or []:
        try:
            lat, lon = float(r.get('latitude')), float(r.get('longitude'))
        except (TypeError, ValueError):
            continue
        x, z = to_xz(lat, lon)
        if not (CITY[0] <= x <= CITY[1] and CITY[2] <= z <= CITY[3]):
            continue
        t = TYPES.get(str(r.get('markertype') or '').strip().lower(), 1)
        yr = str(r.get('dedicateddate') or '')[:4]
        year = int(yr) if yr.isdigit() else None
        name = re.sub(r'\s*-\s*PLAQUE\s*$', '', clean(r.get('name')), flags=re.I)   # the state suffixes its wall plaques
        out.append([int(round(x)), int(round(z)), t, year, name, clean(r.get('location')), clean(r.get('markertext'))])
    out.sort(key=lambda m: (m[4].lower(), m[0], m[1]))
    seen = {}
    for m in out:   # two markers on one spot stand 2 m apart
        k = (m[0], m[1])
        n = seen.get(k, 0)
        seen[k] = n + 1
        if n:
            m[0] += 2 * n
    return out


def bake_art(features):
    out = []
    for f in features or []:
        p = f.get('properties') or {}
        g = f.get('geometry') or {}
        if str(p.get('status') or '').strip().lower() != 'active':
            continue
        polys = g.get('coordinates') if g.get('type') == 'MultiPolygon' else [g.get('coordinates')] if g.get('type') == 'Polygon' else []
        rings = [[to_xz(lat, lon) for lon, lat in poly[0]] for poly in polys if poly and poly[0]]
        if not rings:
            continue
        ring = max(rings, key=len)
        x, z = ring_centroid(ring)
        if not (CITY[0] <= x <= CITY[1] and CITY[2] <= z <= CITY[3]):
            continue
        img = str(p.get('image') or '').strip()
        if not img.startswith(IMG_HOST):
            img = ''
        out.append([int(round(x)), int(round(z)), art_material(p.get('medium')), clean(p.get('title')), clean(p.get('artist')),
                    clean(p.get('date_')), clean(p.get('medium')), clean(p.get('location_name') or p.get('address')), img])
    out.sort(key=lambda a: (a[3].lower(), a[0], a[1]))
    return out


class FootGrid:
    """The model's building footprints in a 64 m cell grid, so a point can be tested against
    the few rings around it and stepped out past the nearest wall when it lies inside one
    (a geocode lands on the building's address, the Clothespin's buffer centroid inside
    Centre Square's podium, and a post inside a building mass is a post nobody sees)."""

    CELL = 64.0

    def __init__(self, rings):
        self.rings = []
        self.cells = {}
        for ring in rings:
            if len(ring) < 3:
                continue
            i = len(self.rings)
            self.rings.append(ring)
            xs = [p[0] for p in ring]
            zs = [p[1] for p in ring]
            for gx in range(int(min(xs) // self.CELL), int(max(xs) // self.CELL) + 1):
                for gz in range(int(min(zs) // self.CELL), int(max(zs) // self.CELL) + 1):
                    self.cells.setdefault((gx, gz), []).append(i)

    @staticmethod
    def inside(x, z, ring):
        hit = False
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, zi = ring[i]
            xj, zj = ring[j]
            if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi:
                hit = not hit
            j = i
        return hit

    def containing(self, x, z):
        for i in self.cells.get((int(x // self.CELL), int(z // self.CELL)), ()):
            if self.inside(x, z, self.rings[i]):
                return self.rings[i]
        return None

    def step_out(self, x, z, out=2.5):
        """(x, z, moved): the point, or its spot `out` metres past the nearest wall of the
        footprint it lies in (three tries, for a point that lands in the next building)."""
        moved = False
        for _ in range(3):
            ring = self.containing(x, z)
            if ring is None:
                return x, z, moved
            best = None
            n = len(ring)
            for i in range(n):
                (ax, az), (bx, bz) = ring[i], ring[(i + 1) % n]
                dx, dz = bx - ax, bz - az
                L2 = dx * dx + dz * dz or 1e-9
                t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
                fx, fz = ax + dx * t, az + dz * t
                d = ((x - fx) ** 2 + (z - fz) ** 2) ** 0.5
                if best is None or d < best[0]:
                    L = L2 ** 0.5
                    best = (d, fx, fz, -dz / L, dx / L)
            _d, fx, fz, nx, nz = best
            if self.inside(fx + nx * 0.3, fz + nz * 0.3, ring):   # the normal points in: flip it
                nx, nz = -nx, -nz
            x, z, moved = fx + nx * out, fz + nz * out, True
        return x, z, moved


def load_footprints():
    """Every building outline the page draws in the core, the outer districts and the far
    ring: scene.json's polys plus the packed tiers decoded by the test suite's walker."""
    rings = []
    try:
        for b in json.load(open(os.path.join(HERE, 'scene.json'))).get('buildings', []):
            poly = b.get('poly') or []
            if len(poly) >= 3:
                rings.append([(p[0], p[1]) for p in poly])
    except (OSError, ValueError):
        pass
    try:
        import sys
        sys.path.insert(0, os.path.join(HERE, 'tests'))
        import _common as C
        for name in ('wide.b64', 'city.b64'):
            if os.path.exists(os.path.join(HERE, name)):
                for _n, _h, _mh, _t, pts in C.walk_scene(name)['buildings']:
                    if len(pts) >= 3:
                        rings.append(pts)
    except Exception as e:   # the bake still runs without the tiers, it just cannot step out of them
        print('packed tiers not read:', e, flush=True)
    return rings


def step_out_all(rows, grid, xi=0, zi=1):
    moved = 0
    for r in rows:
        x, z, m = grid.step_out(r[xi], r[zi])
        if m:
            r[xi], r[zi], moved = int(round(x)), int(round(z)), moved + 1
    return moved


def bake(phmc_rows, art_features, footprints=None):
    out = {'m': bake_markers(phmc_rows), 'a': bake_art(art_features)}
    if footprints:
        grid = FootGrid(footprints)
        out['moved'] = [step_out_all(out['m'], grid), step_out_all(out['a'], grid)]
    return out


def main():
    rows = json.load(open(os.path.join(RAW, 'phmc.json')))
    feats = json.load(open(os.path.join(RAW, 'percent_for_art.geojson')))['features']
    rings = load_footprints()
    out = bake(rows, feats, rings)
    moved = out.pop('moved', [0, 0])
    print(f'{len(rings)} footprints; {moved[0]} markers and {moved[1]} artworks stepped out of a building', flush=True)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), ensure_ascii=False)
    types = [sum(1 for m in out['m'] if m[2] == t) for t in range(3)]
    mats = [sum(1 for a in out['a'] if a[2] == k) for k in range(4)]
    flagged = [r.get('name') for r in rows if str(r.get('status')).lower() == 'true']
    print(f"{len(out['m'])} markers of {len(rows)} (Roadside {types[0]}, City {types[1]}, Plaque {types[2]}), "
          f"{len(out['a'])} artworks of {len(feats)} (bronze {mats[0]}, steel {mats[1]}, stone {mats[2]}, other {mats[3]}, "
          f"{sum(1 for a in out['a'] if a[8])} with an image link), markers.json {os.path.getsize(OUT) / 1e3:.1f} KB", flush=True)
    print(f"{len(flagged)} markers carry status True (undocumented, kept): {', '.join(flagged[:12])}", flush=True)


if __name__ == '__main__':
    main()
