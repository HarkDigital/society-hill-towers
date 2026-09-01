#!/usr/bin/env python3
"""Full-fidelity water polygons for the NW hills patch -> nw_water.json
{"polys": [[x1,z1,...], ...]} in local meters, clipped to the dem_nw box.

Why: pack_city caps area rings at 90 vertices, which turns the 8 km sinuous
Wissahickon into a self-intersecting zigzag — harmless rendered flat, confetti
when draped on the 50 m terrain. The app drapes THESE rings inside the patch
instead and leaves the packed water exactly as it was. Run with plain python3."""
import json, math, os, time, urllib.parse, urllib.request
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
LON0, LAT0, KX, KZ = -75.144748, 39.945474, 85350.0, 110574.0
P = (-10600, -2600, -15600, -6600)
MIRRORS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
           'https://overpass.private.coffee/api/interpreter']

def bbox_latlon():
    lat_s = LAT0 - P[3] / KZ; lat_n = LAT0 - P[2] / KZ
    lon_w = LON0 + P[0] / KX; lon_e = LON0 + P[1] / KX
    return f'{lat_s:.5f},{lon_w:.5f},{lat_n:.5f},{lon_e:.5f}'

def fetch(q):
    data = urllib.parse.urlencode({'data': q}).encode()
    last = None
    for attempt in range(6):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'sht-3d-model/1.0'})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(8 + 8 * attempt)
    raise last

def clip_rect(ring, x0, x1, z0, z1):
    """Sutherland–Hodgman against the patch rectangle."""
    def clip_edge(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out
    r = ring
    for inside, inter in [
        (lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= z0, lambda a, b: (a[0] + (b[0] - a[0]) * (z0 - a[1]) / (b[1] - a[1]), z0)),
        (lambda p: p[1] <= z1, lambda a, b: (a[0] + (b[0] - a[0]) * (z1 - a[1]) / (b[1] - a[1]), z1)),
    ]:
        r = clip_edge(r, inside, inter)
        if len(r) < 3:
            return []
    return r

def simplify(ring, min_d=6.0, cap=900):
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
    q = f'''[out:json][timeout:170];
(
  way["natural"="water"]({bbox_latlon()});
  relation["natural"="water"]({bbox_latlon()});
);
(._;>;);
out body qt;'''
    d = fetch(q)
    if provenance: provenance.record('fetch_nw_water.overpass', MIRRORS[0], q, len(d.get('elements', [])))
    els = d.get('elements', [])
    nodes = {el['id']: ((el['lon'] - LON0) * KX, (LAT0 - el['lat']) * KZ)
             for el in els if el.get('type') == 'node'}
    ways = {el['id']: el for el in els if el.get('type') == 'way'}
    rings = []
    used = set()
    # relation outers: stitch member ways end-to-end into closed rings
    for el in els:
        if el.get('type') != 'relation':
            continue
        segs = []
        for m in el.get('members', []):
            if m.get('type') == 'way' and m.get('role') in ('outer', ''):
                w = ways.get(m['ref'])
                if w:
                    used.add(m['ref'])
                    pts = [nodes[n] for n in w.get('nodes', []) if n in nodes]
                    if len(pts) >= 2:
                        segs.append(pts)
        while segs:
            ring = segs.pop()
            grew = True
            while grew and ring[0] != ring[-1]:
                grew = False
                for i, s in enumerate(segs):
                    if s[0] == ring[-1]: ring += s[1:]; segs.pop(i); grew = True; break
                    if s[-1] == ring[-1]: ring += s[-2::-1]; segs.pop(i); grew = True; break
            if len(ring) >= 4 and ring[0] == ring[-1]:
                rings.append(ring[:-1])
    # plain closed ways
    for wid, w in ways.items():
        if wid in used:
            continue
        pts = [nodes[n] for n in w.get('nodes', []) if n in nodes]
        if len(pts) >= 4 and pts[0] == pts[-1]:
            rings.append(pts[:-1])
    # clip to the patch, simplify ONCE, then tile big rings into ~480 m pieces:
    # drapedPoly grows its sampling with area (sqrt(A/420)), so a 1.8 km2 river
    # would sample at ~65 m and drop bend triangles — small pieces stay dense.
    # Tiling after the single simplify keeps shared tile edges identical, so
    # the pieces butt without seams.
    TILE = 480.0
    polys = []
    for ring in rings:
        c = clip_rect(ring, *[P[0], P[1], P[2], P[3]])
        if len(c) < 3:
            continue
        c = simplify(c)
        if len(c) < 3 or ring_area(c) < 1500:
            continue
        xs = [p[0] for p in c]; zs = [p[1] for p in c]
        gx0 = math.floor(min(xs) / TILE); gx1 = math.floor(max(xs) / TILE)
        gz0 = math.floor(min(zs) / TILE); gz1 = math.floor(max(zs) / TILE)
        for gx in range(gx0, gx1 + 1):
            for gz in range(gz0, gz1 + 1):
                piece = clip_rect(c, gx * TILE, (gx + 1) * TILE, gz * TILE, (gz + 1) * TILE)
                if len(piece) < 3 or ring_area(piece) < 1200:
                    continue
                flat = []
                for x, z in piece:
                    flat.append(round(x, 1)); flat.append(round(z, 1))
                polys.append(flat)
    out = os.path.join(HERE, 'nw_water.json')
    json.dump({'polys': polys}, open(out, 'w'), separators=(',', ':'))
    kb = os.path.getsize(out) / 1e3
    print(f'{len(rings)} raw rings -> {len(polys)} clipped polys ({kb:.0f} KB)')

if __name__ == '__main__':
    main()
