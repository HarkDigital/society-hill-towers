#!/usr/bin/env python3
"""I-95's carriageways -> i95.json (Round 148): the lamp line along the interstate, in the city and past it.

Mike: "can you light up 95 south even outside of the city?" The packed road tiers carry a class and a width but no
names, so the page cannot find I-95 in them. This reads the far ring's raw OSM dump (fetch_city.py's
osm_city_raw.json, which reaches from the far south-west past the airport to Bucks County), keeps the motorway ways
whose ref names I 95 (not the links), stitches them into chains by their shared end nodes and simplifies each to 2 m.

Output (one line): {"src", "chains": [[[x, z], ...], ...]} in the scene frame, 0.1 m, each chain in the direction
of travel (OSM draws a oneway motorway along its traffic), so the right-hand side is the outer shoulder.
Plain python3, stdlib only."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAT0, LON0 = 39.94547, -75.14475
KX, KZ = 111320 * math.cos(math.radians(LAT0)), 110574


def xz(lat, lon):
    return ((lon - LON0) * KX, -(lat - LAT0) * KZ)


def rdp(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz) or 1e-9
    i, dmax = 0, -1.0
    for k in range(1, len(pts) - 1):
        d = abs((pts[k][0] - a[0]) * dz - (pts[k][1] - a[1]) * dx) / L
        if d > dmax:
            i, dmax = k, d
    if dmax <= tol:
        return [a, b]
    return rdp(pts[:i + 1], tol)[:-1] + rdp(pts[i:], tol)


def main():
    d = json.loads((HERE / 'osm_city_raw.json').read_text())
    els = d['elements'] if isinstance(d, dict) else d
    nodes = {e['id']: (e['lat'], e['lon']) for e in els if e['type'] == 'node' and 'lat' in e}
    ways = []
    for e in els:
        t = e.get('tags') or {}
        if e['type'] != 'way' or t.get('highway') != 'motorway':
            continue
        if 'I 95' not in [r.strip() for r in t.get('ref', '').split(';')]:
            continue
        ids = [n for n in e.get('nodes', []) if n in nodes]
        if len(ids) >= 2:
            ways.append(ids)
    # stitch: a way whose first node is another's last continues it (one successor and one predecessor each)
    starts = {}
    for i, w in enumerate(ways):
        starts.setdefault(w[0], []).append(i)
    ends = {}
    for i, w in enumerate(ways):
        ends.setdefault(w[-1], []).append(i)
    used, chains = set(), []
    for i, w in enumerate(ways):
        if i in used:
            continue
        # walk back to the head of this run
        h = i
        seen = {h}
        while len(ends.get(ways[h][0], [])) == 1 and ends[ways[h][0]][0] not in seen and ends[ways[h][0]][0] not in used:
            h = ends[ways[h][0]][0]; seen.add(h)
        run, j = list(ways[h]), h
        used.add(h)
        while len(starts.get(ways[j][-1], [])) == 1 and starts[ways[j][-1]][0] not in used:
            j = starts[ways[j][-1]][0]; used.add(j); run += ways[j][1:]
        pts = rdp([xz(*nodes[n]) for n in run], 2.0)
        chains.append([[round(x, 1), round(z, 1)] for x, z in pts])
    km = sum(math.hypot(c[k + 1][0] - c[k][0], c[k + 1][1] - c[k][1]) for c in chains for k in range(len(c) - 1)) / 1000
    xs = [p[0] for c in chains for p in c]; zs = [p[1] for c in chains for p in c]
    out = {'src': 'OpenStreetMap (ODbL) via osm_city_raw.json: highway=motorway, ref I 95', 'chains': chains}
    (HERE / 'i95.json').write_text(json.dumps(out, separators=(',', ':')))
    print('i95.json: %d ways in %d chains, %.1f km, x %d..%d, z %d..%d' % (len(ways), len(chains), km, min(xs), max(xs), min(zs), max(zs)))


if __name__ == '__main__':
    main()
