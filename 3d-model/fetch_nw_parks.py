#!/usr/bin/env python3
"""Official parkland boundaries for the NW hills patch: PPR_Properties
(OpenDataPhilly) intersecting the dem_nw box -> nw_parks.json
{"polys": [[x1,z1,x2,z2,...], ...]} in local meters.

Why: the central Wissahickon gorge has NO park polygon in the OSM extract
(it's a nature_reserve relation the city fetch never downloaded), so the far
ring renders it bare. The 50 m patch ground tints woodland green from these
official boundaries instead. Run with plain python3.
Frame: philly_frame.py (the scene's own projection). This script used to hardcode
KX=85350, which put its output up to ~1.1 m east of the scene at the far ring;
the committed nw_parks.json keeps that offset until the next rerun."""
import json, math, os, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
from philly_frame import LON0, LAT0, KX, KZ   # the one scene frame
# dem_nw box in lon/lat with a small margin
ENV = '-75.2700,39.8035,-75.1730,40.0900'
P = (-10600, -2600, -15600, -6600)
BASE = ('https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
        'PPR_Properties/FeatureServer/0/query')

def env_for_patch():
    # patch corners back to lon/lat (z south-positive)
    lon0 = LON0 + P[0] / KX; lon1 = LON0 + P[1] / KX
    lat0 = LAT0 - P[3] / KZ; lat1 = LAT0 - P[2] / KZ
    return f'{lon0 - 0.003:.4f},{lat0 - 0.003:.4f},{lon1 + 0.003:.4f},{lat1 + 0.003:.4f}'

def simplify(ring, min_d=20.0, cap=600):
    out = [ring[0]]
    for q in ring[1:]:
        dx = q[0] - out[-1][0]; dz = q[1] - out[-1][1]
        if dx * dx + dz * dz >= min_d * min_d:
            out.append(q)
    if len(out) > cap:
        out = out[::max(1, len(out) // cap)]
    return out

def ring_area(r):
    a = 0
    for i in range(len(r)):
        x1, z1 = r[i]; x2, z2 = r[(i + 1) % len(r)]
        a += x1 * z2 - x2 * z1
    return abs(a) / 2

def main():
    q = urllib.parse.urlencode({
        'where': '1=1', 'geometry': env_for_patch(), 'geometryType': 'esriGeometryEnvelope',
        'inSR': '4326', 'spatialRel': 'esriSpatialRelIntersects',
        'outFields': 'official_name,acreage', 'outSR': '4326', 'f': 'geojson'})
    with urllib.request.urlopen(BASE + '?' + q, timeout=120) as r:
        d = json.load(r)
    polys = []
    names = []
    for f in d.get('features', []):
        g = f.get('geometry') or {}
        rings = []
        if g.get('type') == 'Polygon':
            rings = [g['coordinates'][0]]           # outer ring only; holes are noise at 50 m
        elif g.get('type') == 'MultiPolygon':
            rings = [pp[0] for pp in g['coordinates']]
        for ring in rings:
            loc = [((lon - LON0) * KX, (LAT0 - lat) * KZ) for lon, lat, *_ in ring]
            loc = simplify(loc)
            if len(loc) < 3 or ring_area(loc) < 25000:
                continue
            # keep only rings that touch the patch at all
            xs = [p[0] for p in loc]; zs = [p[1] for p in loc]
            if max(xs) < P[0] or min(xs) > P[1] or max(zs) < P[2] or min(zs) > P[3]:
                continue
            flat = []
            for x, z in loc:
                flat.append(round(x, 1)); flat.append(round(z, 1))
            polys.append(flat)
            names.append((f.get('properties') or {}).get('official_name'))
    out = os.path.join(HERE, 'nw_parks.json')
    json.dump({'polys': polys}, open(out, 'w'), separators=(',', ':'))
    kb = os.path.getsize(out) / 1e3
    print(f'{len(polys)} rings kept ({kb:.0f} KB):')
    for nm in sorted(set(n for n in names if n))[:20]:
        print(' ', nm)

if __name__ == '__main__':
    main()
