#!/usr/bin/env python3
"""Amtrak's tracks through the city -> rail_amtrak.json (Round 80): the polyline the live
trains snap to and ride, and the corridor the page draws as ballast and rails.

The packed tiers keep no railway (fetch_wide.py pulls the ways, nothing downstream uses
them), and the only track in the page is the Frankford El. This bake asks Overpass for the
railway=rail ways Amtrak operates over the far-ring box (the Northeast Corridor from the
airport reach to Torresdale, the Keystone Corridor west past Overbrook, by operator tag or
by the corridor's names), drops yard, siding, spur and crossover ways (a service tag) and
industrial or military usage, keeps each way's tunnel/covered and bridge flags, projects
into the model frame (philly_frame.py), clips to the far-ring box, simplifies to 1.5 m
(Douglas-Peucker, stdlib) and rounds to 0.1 m:

  {"src", "fetched", "box": [x0, x1, z0, z1],
   "lines": [{"n": name, "t": 0|1 (tunnel or covered), "b": 0|1 (bridge), "p": [[x, z], ...]}, ...]}

Every track of a multi-track corridor is its own line (OSM maps each), so the page's snap
grid finds the nearest and the corridor draws as the four tracks it is. Prints the track
kilometres and the nearest line's distance to three stations as the sanity check. Cached in
lidar_cache/rail_amtrak_raw.json; --force refetches. Data (c) OpenStreetMap contributors,
ODbL (see ../DATA-LICENSE.md). Plain python3."""
import json
import os
import sys
import time

from philly_frame import to_xz
try:
    import provenance
except Exception:
    provenance = None
import overpass

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
CACHE = os.path.join('lidar_cache', 'rail_amtrak_raw.json')
OUT = 'rail_amtrak.json'
BOX = (39.855, -75.30, 40.145, -74.94)                 # SEPTA_BOX in app.js: the modelled city
CITY = (-12000.0, 16500.0, -21700.0, 9700.0)           # the far-ring box: x0, x1, z0, z1
QUERY = ('[out:json][timeout:180];('
         'way["railway"="rail"]["operator"~"Amtrak",i](%s);'
         'way["railway"="rail"]["name"~"Northeast Corridor|Keystone Corridor|Harrisburg Line",i](%s);'
         ');out geom;' % (','.join(str(v) for v in BOX), ','.join(str(v) for v in BOX)))
STATIONS = {'30th Street Station': (-3171, -1122), 'North Philadelphia': (-875, -5753), 'Overbrook': (-8960, -4850)}
TOL = 1.5


def simplify(pts, tol):
    """Douglas-Peucker on an open polyline."""
    if len(pts) <= 2:
        return pts
    a, b = pts[0], pts[-1]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = (dx * dx + dz * dz) ** 0.5 or 1e-9
    best, bi = -1.0, -1
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = abs((p[0] - a[0]) * dz - (p[1] - a[1]) * dx) / L
        if d > best:
            best, bi = d, i
    if best > tol:
        return simplify(pts[:bi + 1], tol)[:-1] + simplify(pts[bi:], tol)
    return [a, b]


def inside(p):
    return CITY[0] <= p[0] <= CITY[1] and CITY[2] <= p[1] <= CITY[3]


def clip_runs(pts):
    """The runs of consecutive points inside the box (a way that leaves and returns is two)."""
    runs, cur = [], []
    for p in pts:
        if inside(p):
            cur.append(p)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) >= 2]


def seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz or 1e-9
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return ((px - ax - dx * t) ** 2 + (pz - az - dz * t) ** 2) ** 0.5


def bake(elements):
    lines, dropped = [], 0
    for w in elements:
        if w.get('type') != 'way' or not w.get('geometry'):
            continue
        tags = w.get('tags') or {}
        if tags.get('service') or tags.get('usage') in ('industrial', 'military', 'tourism') or tags.get('railway') != 'rail':
            dropped += 1
            continue
        op = (tags.get('operator') or '').lower()
        if op and 'amtrak' not in op:   # Round 85: the name clause also matched Norfolk Southern's Harrisburg Line up the Schuylkill's east bank (36 freight ways Amtrak never rides)
            dropped += 1
            continue
        t = 1 if (tags.get('tunnel') not in (None, 'no') or tags.get('covered') not in (None, 'no')) else 0
        layer = tags.get('layer')
        try:
            lay = int(layer) if layer is not None else 0
        except ValueError:
            lay = 0
        b = 1 if (tags.get('bridge') not in (None, 'no') or lay >= 1) and not t else 0
        pts = [to_xz(g['lat'], g['lon']) for g in w['geometry']]
        for run in clip_runs(pts):
            simp = simplify(run, TOL)
            lines.append({'n': tags.get('name') or '', 't': t, 'b': b, 'p': [[round(x, 1), round(z, 1)] for x, z in simp]})
    lines.sort(key=lambda l: (l['n'], l['p'][0][0], l['p'][0][1]))
    return lines, dropped


def stats(lines):
    km = 0.0
    for l in lines:
        p = l['p']
        for i in range(1, len(p)):
            km += ((p[i][0] - p[i - 1][0]) ** 2 + (p[i][1] - p[i - 1][1]) ** 2) ** 0.5
    near = {}
    for name, (sx, sz) in STATIONS.items():
        best = float('inf')
        for l in lines:
            p = l['p']
            for i in range(1, len(p)):
                best = min(best, seg_dist(sx, sz, p[i - 1][0], p[i - 1][1], p[i][0], p[i][1]))
        near[name] = best
    return km / 1000.0, near


def main():
    if os.path.exists(CACHE) and '--force' not in sys.argv:
        data = json.load(open(CACHE))
    else:
        data = overpass.fetch(QUERY)
        os.makedirs('lidar_cache', exist_ok=True)
        json.dump(data, open(CACHE, 'w'))
        if provenance:
            provenance.record('bake_rail.overpass', 'overpass railway=rail operated by Amtrak, and the NEC and Keystone ways by name', {'query': QUERY}, len(data.get('elements', [])))
    lines, dropped = bake(data.get('elements', []))
    out = {'src': 'OpenStreetMap railway=rail ways operated by Amtrak, and the Northeast Corridor and Keystone Corridor ways by name, via Overpass (ODbL), model frame (philly_frame.py)',
           'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'box': list(CITY), 'lines': lines}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    km, near = stats(lines)
    n_t = sum(1 for l in lines if l['t'])
    n_b = sum(1 for l in lines if l['b'])
    n_p = sum(len(l['p']) for l in lines)
    print(f'{OUT}: {len(lines)} lines ({n_p} pts, {n_t} in tunnel, {n_b} on bridges, {dropped} service or industrial ways dropped), '
          f'{km:.1f} track km, {os.path.getsize(OUT):,} bytes', flush=True)
    for name, d in near.items():
        print(f'  nearest line to {name}: {d:.0f} m', flush=True)
    names = sorted({l['n'] for l in lines if l['n']})
    print('  names: ' + ', '.join(names[:12]) + ('...' if len(names) > 12 else ''), flush=True)


if __name__ == '__main__':
    main()
