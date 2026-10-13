#!/usr/bin/env python3
"""Bake the outer districts' sidewalks (Oct 12, the realism pass; Mike: "please do anything necessary to make this look
more photo realistic and less cartoony"). Outside the core every rowhouse stood on a strip of lawn: the core's 'Paving
the streets' step lays its own walks, and nothing paved the 3 to 5 m between an outer street's kerb and its facades.

The input is wide.b64 itself (the streets and footprints exactly as the page draws them, the south merge and the insets
included) with overpasses.json (a street a baked deck owns is not at grade), the water (wide.b64's own water areas,
schuylkill.json and delaware.json) and places.json's historic districts for the brick. Per 400 m tile, with a margin:

  CW  the carriageways: every drawn street (primary to residential) buffered by its half width, round ends
  S   the base band: the same streets buffered by half width plus d (primary 4.0, secondary 3.5, tertiary 3.2,
      residential 2.8 m), the sidewalk a city street carries
  S2  the facade fill: a morphological closing of S with the footprints (buffer 2.6 out and back), kept within 6.5 m
      of a kerb, which paves any strip under 5.2 m between the band and a facade (a rowhouse block) and leaves a real
      front lawn (a Northeast Philadelphia setback) alone
  SW  = (S | S2) - CW - footprints - water - the core's box (it paves its own), cut to the tile, simplified (--simplify,
      0.25 m by default) and snapped to the 0.2 m grid, parts under 2 m2 dropped

Each part's holes are split away (no_holes: a cut through each hole), so every ring is simple, and written as a ring. The
rings are cut only at the 400 m tile edges: 72 m across at the median, 150 m at the 90th percentile, none over 400 m (the
page densifies each ring's edges to 12 m and splits any long earcut triangle that would dip under the drawn ground).
Brick (kind 6) inside Old City, Society Hill, Rittenhouse-Fitler and Spring Garden (places.json) and hand-drawn Queen
Village and Washington Square West boxes; concrete (kind 5) elsewhere.

sidewalks.b64: Int32 header [magic 0x53485757 'SHWW', nRings, version 1, 0], then int16 per ring: n, kind, x0, z0 in
0.2 m units of the model frame, then n - 1 deltas (dx, dz) in the same units. The page keeps the rings in this form and
lays them on the drawn ground ('Paving the sidewalks', swGeometry): a computer all of them at load in 1,200 m squares, a
phone the 200 m squares within half a mile of the eye as it moves."""
import argparse, base64, json, math, os, struct, sys, time
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, MultiPolygon, box, GeometryCollection
from shapely.ops import unary_union, split
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'sidewalks.b64')
MAGIC = 0x53485757
UNIT = 0.2
WIDE = (-3700, 2300, -4480, 6400)
CORE = (-640, 770, -520, 850)          # app.js CORE_EXT: the core paves its own walks out to its runs' 40 m reach
CORE_PAD = 42
TILE = 400
D_BY_T = {2: 4.0, 3: 3.5, 4: 3.2, 5: 2.8}   # pack_wide RT: 2 primary, 3 secondary, 4 tertiary, 5 residential
FILL_R, FILL_REACH = 2.6, 6.5
BRICK_HD = ('Old City', 'Society Hill', 'Rittenhouse-Fitler Residential', 'Spring Garden')
BRICK_BOXES = [(-661, 106, 218, 1213),      # Queen Village: Front to 6th, Lombard to Washington
               (-1609, -747, -324, 439)]    # Washington Square West: 7th to Broad, Walnut to South
QS = 4                                       # quarter-circle segments on the round ends


def decode_wide(path):
    raw = base64.b64decode(open(path).read().strip())
    magic, nb, nr, na = struct.unpack_from('<4i', raw, 0)
    body = np.frombuffer(raw, dtype='<i2', offset=16)
    hs = 6 if magic in (0x5348545A, 0x5348545B, 0x5348545C, 0x5348545D) else 4
    i, blds, roads, areas = 0, [], [], []
    for _ in range(nb):
        n = int(body[i]); p0 = i + hs
        pts = body[p0:p0 + 2 * n].reshape(-1, 2).astype(np.float64) * 0.2
        blds.append(pts); i = p0 + 2 * n
    for _ in range(nr):
        n = int(body[i]); w = body[i + 1] / 10.0; t = int(body[i + 2]); p0 = i + 3
        pts = body[p0:p0 + 2 * n].reshape(-1, 2).astype(np.float64) * 0.2
        roads.append((w, t, pts)); i = p0 + 2 * n
    for _ in range(na):
        n = int(body[i]); kind = int(body[i + 1]); p0 = i + 2
        pts = body[p0:p0 + 2 * n].reshape(-1, 2).astype(np.float64) * 0.2
        areas.append((kind, pts)); i = p0 + 2 * n
    assert i == len(body), 'wide.b64: %d int16 left' % (len(body) - i)
    return blds, roads, areas


def deck_segments():
    """The baked decks' centrelines (app.js ovpSegs: the elevated and sunken chains), for ovpOwned."""
    o = json.load(open(os.path.join(HERE, 'overpasses.json')))
    segs = []
    for c in o.get('el', []) + o.get('sk', []):
        p = c['p']
        for a, b in zip(p, p[1:]):
            segs.append((a[0], a[1], b[0], b[1]))
    return np.array(segs, np.float64)


def owned_mask(pts, decks, tree):
    """app.js ovpOwned per segment: both ends within 2.6 m of a deck segment aligned within 0.8."""
    out = []
    for a, b in zip(pts, pts[1:]):
        d = b - a
        L = math.hypot(*d) or 1.0
        ux, uz = d / L

        def hit(p):
            for k in tree.query(shapely.points(p[0], p[1]).buffer(2.7)):
                sx, sz, ex, ez = decks[k]
                dx, dz = ex - sx, ez - sz
                sl = math.hypot(dx, dz) or 1.0
                if abs((dx * ux + dz * uz) / sl) < 0.8:
                    continue
                t = min(1.0, max(0.0, ((p[0] - sx) * dx + (p[1] - sz) * dz) / (sl * sl)))
                if (sx + dx * t - p[0]) ** 2 + (sz + dz * t - p[1]) ** 2 < 2.6 * 2.6:
                    return True
            return False
        out.append(hit(a) and hit(b))
    return out


def ring_of(flat):
    return [(flat[k], flat[k + 1]) for k in range(0, len(flat) - 1, 2)]


def water_geoms(areas):
    polys = []
    for kind, pts in areas:
        if kind == 1 and len(pts) >= 3:
            g = Polygon(pts).buffer(0)
            if not g.is_empty:
                polys.append(g)
    for name in ('schuylkill.json', 'delaware.json'):
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        for wp in json.load(open(p)).get('polys', []):
            g = Polygon(wp['ring'], [h for h in wp.get('holes', []) if len(h) >= 3]).buffer(0)
            g = g.intersection(box(WIDE[0] - 300, WIDE[2] - 300, WIDE[1] + 300, WIDE[3] + 300))
            if not g.is_empty:
                polys.append(g)
    return polys


def brick_zone():
    zs = [box(x0, z0, x1, z1) for x0, x1, z0, z1 in BRICK_BOXES]
    places = json.load(open(os.path.join(HERE, 'places.json')))
    for h in places.get('hd', []):
        if h['n'] in BRICK_HD:
            for r in h['rings']:
                g = Polygon(ring_of(r)).buffer(0)
                if not g.is_empty:
                    zs.append(g)
    return unary_union(zs)


def polys_of(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, (MultiPolygon, GeometryCollection)):
        out = []
        for p in g.geoms:
            out += polys_of(p)
        return out
    return []


def no_holes(p, depth=0):
    """Simple pieces of a gridded polygon: split by a line through each hole's centroid (on the 0.2 m grid, across the
    hole's shorter extent), each piece snapped back to the grid, so every ring the page earcuts is simple."""
    if not p.interiors:
        return [p]
    if depth > 12:
        return []
    h = Polygon(p.interiors[0])
    cx, cz = round(h.centroid.x / UNIT) * UNIT, round(h.centroid.y / UNIT) * UNIT
    x0, z0, x1, z1 = p.bounds
    hx0, hz0, hx1, hz1 = h.bounds
    cut = LineString([(cx, z0 - 1), (cx, z1 + 1)]) if hx1 - hx0 < hz1 - hz0 else LineString([(x0 - 1, cz), (x1 + 1, cz)])
    out = []
    for q in split(p, cut).geoms:
        for r in polys_of(shapely.set_precision(q, UNIT)):
            out += no_holes(r, depth + 1)
    return out


def ring_out(p):
    """The ring in 0.2 m units, CCW in (x, z), or None for a sliver."""
    if p.area < 2.0 or not p.is_valid:
        return None
    p = orient(p, 1.0)
    c = np.round(np.asarray(p.exterior.coords)[:-1] / UNIT).astype(np.int64)
    return c if len(c) >= 3 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tiles', default='', help='x0,z0,x1,z1: bake only the tiles inside (a quick look)')
    ap.add_argument('--simplify', type=float, default=0.25)
    ap.add_argument('--out', default=OUT, help='where to write (a quick look writes only when given one)')
    a = ap.parse_args()
    t0 = time.time()
    blds, roads, areas = decode_wide(os.path.join(HERE, 'wide.b64'))
    decks = deck_segments()
    deck_tree = STRtree([LineString([(s[0], s[1]), (s[2], s[3])]) for s in decks]) if len(decks) else None
    # the drawn streets, cut into the runs no deck owns
    runs = []   # (w, t, LineString)
    owned = 0
    for w, t, pts in roads:
        if t not in D_BY_T or len(pts) < 2:
            continue
        mask = owned_mask(pts, decks, deck_tree) if deck_tree is not None else [False] * (len(pts) - 1)
        cur = [pts[0]]
        for k, own in enumerate(mask):
            if own:
                owned += 1
                if len(cur) > 1:
                    runs.append((w, t, LineString(cur)))
                cur = [pts[k + 1]]
            else:
                cur.append(pts[k + 1])
        if len(cur) > 1:
            runs.append((w, t, LineString(cur)))
    print('streets: %d runs from %d ways (%d deck-owned segments), %.1f s' % (len(runs), len(roads), owned, time.time() - t0))
    run_tree = STRtree([r[2] for r in runs])
    bpolys = []
    for pts in blds:
        if len(pts) >= 3:
            g = Polygon(pts)
            if not g.is_valid:
                g = g.buffer(0)
            if not g.is_empty:
                bpolys.append(g)
    b_tree = STRtree(bpolys)
    water = water_geoms(areas)
    w_tree = STRtree(water) if water else None
    brick = brick_zone()
    core = box(CORE[0] - CORE_PAD, CORE[2] - CORE_PAD, CORE[1] + CORE_PAD, CORE[3] + CORE_PAD)
    print('inputs: %d footprints, %d water polygons, %.1f s' % (len(bpolys), len(water), time.time() - t0))
    lim = [float(v) for v in a.tiles.split(',')] if a.tiles else None
    rings, area, kinds = [], 0.0, {5: 0, 6: 0}
    M = FILL_REACH + 8
    for tx in range(WIDE[0], WIDE[1], TILE):
        for tz in range(WIDE[2], WIDE[3], TILE):
            if lim and (tx + TILE < lim[0] or tx > lim[2] or tz + TILE < lim[1] or tz > lim[3]):
                continue
            T = box(tx, tz, tx + TILE, tz + TILE)
            if T.within(core):
                continue
            TM = T.buffer(M, join_style=2)
            idx = run_tree.query(TM)
            if not len(idx):
                continue
            S, CW, NEAR = [], [], []
            for k in idx:
                w, t, ln = runs[k]
                hw = w / 2
                S.append(ln.buffer(hw + D_BY_T[t], quad_segs=QS))
                CW.append(ln.buffer(hw, quad_segs=QS))
                NEAR.append(ln.buffer(hw + FILL_REACH, quad_segs=QS))
            S = unary_union(S).intersection(TM)
            CW = unary_union(CW)
            NEAR = unary_union(NEAR)
            bi = b_tree.query(TM)
            B = unary_union([bpolys[k] for k in bi]) if len(bi) else Polygon()
            fill = S.union(B).buffer(FILL_R, quad_segs=QS, join_style=2).buffer(-FILL_R, quad_segs=QS, join_style=2).intersection(NEAR)
            SW = S.union(fill).difference(CW)
            if not B.is_empty:
                SW = SW.difference(B)
            if w_tree is not None:
                wi = w_tree.query(TM)
                if len(wi):
                    SW = SW.difference(unary_union([water[k] for k in wi]))
            SW = SW.difference(core).intersection(T)
            if SW.is_empty:
                continue
            SW = shapely.set_precision(SW.simplify(a.simplify), UNIT)   # gridded and still valid: every ring survives its 0.2 m units
            for p in polys_of(SW):
                for q in no_holes(p):
                    c = ring_out(q)
                    if c is None:
                        continue
                    kind = 6 if brick.contains(q.representative_point()) else 5
                    rings.append((kind, c))
                    area += q.area
                    kinds[kind] += 1
        print('  tiles to x %d: %d rings, %.2f km2, %.0f s' % (tx + TILE, len(rings), area / 1e6, time.time() - t0), flush=True)
    body = []
    for kind, c in rings:
        body += [len(c), kind, int(c[0][0]), int(c[0][1])]
        d = np.diff(c, axis=0)
        body += d.reshape(-1).tolist()
    arr = np.array(body, dtype=np.int64)
    assert arr.max() <= 32767 and arr.min() >= -32767, 'int16 overflow'
    raw = struct.pack('<4i', MAGIC, len(rings), 1, 0) + arr.astype('<i2').tobytes()
    if lim and a.out == OUT:
        print('a quick look (--tiles): not written; %d rings, %d vertices, %.2f km2, %d KB raw' % (len(rings), sum(len(c) for _, c in rings), area / 1e6, len(raw) // 1024))
        return
    with open(a.out + '.tmp', 'w') as f:
        f.write(base64.b64encode(raw).decode('ascii'))
    os.replace(a.out + '.tmp', a.out)
    print('wrote %s: %d rings (%d concrete, %d brick), %d vertices, %.2f km2, %d KB base64, %.0f s'
          % (a.out, len(rings), kinds[5], kinds[6], sum(len(c) for _, c in rings), area / 1e6, os.path.getsize(a.out) // 1024, time.time() - t0))


if __name__ == '__main__':
    main()
