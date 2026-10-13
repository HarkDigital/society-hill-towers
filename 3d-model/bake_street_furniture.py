#!/usr/bin/env python3
"""Bake the street furniture (fetch_street_furniture.py) into street_furniture.json, which build.py inlines as STREET_FURN:
each kind's points in the scene frame at 0.5 m, inside the city line (CITY_LIMIT's real line, buffered 300 m so a
border junction keeps its signals). The page stands them near the eye ('Furnishing the streets'): a signal pole on each
corner of a signalised junction with its heads toward the approaches, a stop sign at each stop line, the hydrants, the
benches and the litter bins where they are mapped. OpenStreetMap, ODbL (the About panel's OpenStreetMap credit covers it).

  sig    highway=traffic_signals (a junction; a signalised crossing's node joins it when it stands within 25 m of none)
  stop   highway=stop
  hyd    emergency=fire_hydrant
  bench  amenity=bench
  bin    amenity=waste_basket"""
import json, math, os, sys
from philly_frame import to_xz

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'street_furniture_raw.json')
OUT = os.path.join(HERE, 'street_furniture.json')


def inside(poly, x, z):
    c = False
    for i in range(len(poly)):
        x1, z1 = poly[i]; x2, z2 = poly[i - 1]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            c = not c
    return c


def main():
    if not os.path.exists(RAW):
        sys.exit('no %s (run fetch_street_furniture.py)' % RAW)
    els = json.load(open(RAW))['elements']
    lim = json.load(open(os.path.join(HERE, 'city_limit.json')))
    rings = lim.get('city')
    if rings and isinstance(rings[0][0], (int, float)):
        rings = [rings]
    def keep(x, z):
        return not rings or any(inside(r, x, z) for r in rings)
    out = {'sig': [], 'stop': [], 'hyd': [], 'bench': [], 'bin': []}
    xing = []
    seen = set()
    for e in els:
        if e.get('type') != 'node' or e['id'] in seen:
            continue
        seen.add(e['id'])
        t = e.get('tags') or {}
        x, z = to_xz(e['lat'], e['lon'])
        if not keep(x, z):
            continue
        k = None
        if t.get('highway') == 'traffic_signals':
            k = 'sig'
        elif t.get('highway') == 'crossing':
            xing.append((x, z)); continue
        elif t.get('highway') == 'stop':
            k = 'stop'
        elif t.get('emergency') == 'fire_hydrant':
            k = 'hyd'
        elif t.get('amenity') == 'bench':
            k = 'bench'
        elif t.get('amenity') == 'waste_basket':
            k = 'bin'
        if k:
            out[k].append((x, z))
    # a signalised crossing with no junction signal near it is a mid-block signal of its own
    sig = out['sig']
    grid = {}
    for (x, z) in sig:
        grid.setdefault((int(x // 25), int(z // 25)), []).append((x, z))
    def near_sig(x, z):
        gx, gz = int(x // 25), int(z // 25)
        return any(math.hypot(px - x, pz - z) < 25 for dx in (-1, 0, 1) for dz in (-1, 0, 1) for (px, pz) in grid.get((gx + dx, gz + dz), []))
    extra = [(x, z) for (x, z) in xing if not near_sig(x, z)]
    sig += extra
    # one node per junction: OSM often maps a signal on every approach of a wide street or a dual carriageway (Broad
    # Street's are 15 to 20 m apart); merge within 22 m, under the shortest block
    merged = []
    for (x, z) in sorted(sig):
        for m in merged:
            if math.hypot(m[0] / m[2] - x, m[1] / m[2] - z) < 22:
                m[0] += x; m[1] += z; m[2] += 1
                break
        else:
            merged.append([x, z, 1])
    out['sig'] = [(m[0] / m[2], m[1] / m[2]) for m in merged]
    res = {'src': 'OpenStreetMap contributors (ODbL), nodes fetched by fetch_street_furniture.py; scene frame, 0.5 m units'}
    for k, pts in out.items():
        res[k] = [v for (x, z) in pts for v in (int(round(x * 2)), int(round(z * 2)))]
    with open(OUT + '.tmp', 'w') as f:
        json.dump(res, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.1f KB' % (os.path.getsize(OUT) / 1e3), {k: len(v) for k, v in out.items()}, 'mid-block crossings', len(extra))


if __name__ == '__main__':
    main()
