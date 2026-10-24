#!/usr/bin/env python3
"""The Schuylkill's real course -> schuylkill.json, for the river carve and the water sheet
through Fairmount Park.

OSM maps the river as waterway=river ways (145 fragments across the city, side channels
around the islands included) and its surface as riverbank multipolygons that neither
packed tier carries north of the Fairmount dam, so the model's channel through the park
followed a hand-drawn polyline that wandered up to 500 m off the water. This bake asks
Overpass for the named waterway ways over the city (cached in lidar_cache/), projects them
into the model frame (philly_frame.py) and writes:

  lines  every fragment as [[x, z], ...] simplified to 3 m: the app's schuylkillCut() carves
         the terrain within 60..95 m of the nearest one
  polys  the river's outline: the natural=water river multipolygons OSM keeps around those
         ways (a second cached Overpass query), polygonised, the faces the waterway threads
         kept, united with the fragments buffered HALF_W where they run outside the faces (so a
         gap in the outline still carries water without widening a bounded reach), clipped to the modelled reach (Z_MIN..Z_MAX), as [{"ring", "holes"}]
         in the model frame. The app carves the terrain to the outline (inside to the bed, a
         40 m ramp outside) and draws it flat at the river level, so the shoreline is the
         outline itself and not the 25 m ground grid surfacing through the sheet
  quad_hole  one simple ring (the realism round two): the outline buffered QUAD_R, the carve's
         reach, kept clear of the tidal Delaware (delaware.json's outline buffered QUAD_R, the
         river east of DEL_X, and the bake's own z cut), whole metres. The page cuts it out of
         the Delaware's one water quad, which lay under the whole city and showed through every
         bank the carve takes below it as a band of water up to 25 m wide (0.135 km2 in the wide
         box alone, 91 per cent of the first 5 m), so the carved slope shows as the bank it is
  quad_keep  the patches of that quad the page keeps inside the hole: the outline's islands and the
         bridge piers OSM cuts out of the river, grown QUAD_KEEP, where the water there was the quad's and
         stays so (a pier's hole is smaller than a ground cell, its ground the bed's)

Data (c) OpenStreetMap contributors, ODbL (see ../DATA-LICENSE.md). Needs shapely."""
import json, math, os, sys, time
from shapely.geometry import LineString, LinearRing, Polygon, MultiPolygon, box
from shapely.ops import unary_union, polygonize
from shapely.validation import explain_validity
from philly_frame import to_xz
try:
    import provenance
except Exception:
    provenance = None
import overpass

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
CACHE = os.path.join('lidar_cache', 'schuylkill_ways.json')
CACHE_OUTLINE = os.path.join('lidar_cache', 'schuylkill_outline_raw.json')
QUERY = '[out:json][timeout:90];way["waterway"="river"]["name"~"Schuylkill",i](39.85,-75.30,40.09,-75.12);out geom;'
HALF_W = 60.0            # metres each side of the centreline where the outline has a gap
# the realism round two (R1): OSM keeps the slack-water pool behind the Fairmount Dam as water=reservoir, which the
# face filter below leaves out, so from the dam to Boathouse Row the ribbon WAS the outline, and its 60 m about the
# canoe channel along the east bank ran over the land between Lloyd Hall and the Water Works: 97 PPR trees and 30 poles
# stood in the river there (Round 55 coda 2's complaint again). In POOL_REACH the ribbon is cut back to the pool's own
# outer ring (its wooded island stays water, as it was) after a closing that fills the gaps between the dam's fragments'
# ribbons; nowhere else changes
POOL_REACH = (-3900.0, -2800.0, -3250.0, -2300.0)   # x0, z0, x1, z1: the dam, the Water Works and Boathouse Row
POOL_CLOSE = 40.0        # metres: the closing that fills the ribbons' gaps in POOL_REACH
QUAD_KEEP = 6.0          # the patches the quad keeps over the outline's own islands and piers, this much past them (quad_keep_rings)
QUAD_R = 60.0            # the hole in the Delaware's quad: the carve's reach outside the outline (app.js riverCarve)
DEL_X = -2400.0          # east of this the Schuylkill's polygon is the tidal Delaware's (the Navy Yard and up past it)
DELAWARE = 'delaware.json'
Z_MIN, Z_MAX = -13000.0, 7500.0   # the modelled reach of the river
QUERY_OUTLINE = ('[out:json][timeout:180];way["waterway"="river"]["name"~"Schuylkill",i](39.85,-75.30,40.09,-75.12)->.w;'
                 '(rel(around.w:60)["natural"="water"];way(around.w:60)["natural"="water"];way(around.w:60)["waterway"="riverbank"];);out geom;')
OUT = 'schuylkill.json'


def despike(coords, eps=0.25):
    """Drop needle tips from a ring.

    Uniting the OSM riverbank faces with the buffered centreline leaves a handful of zero-width
    spikes: the boundary runs out and straight back, so vertex i sits between two neighbours only
    millimetres apart. The geometry is valid at full precision, but ROUNDING it for the json moves
    each vertex up to half a quantum and the two sides of the spike cross, which makes the ring
    self-intersecting. The shipped file carried exactly that (measured: edge pairs 4 to 6 mm apart
    near (-8247, -9788) and (-8150, -9840), invalid at any quantum coarser than 1 mm), and earcut
    on an invalid ring leaves pockets untriangulated: the water sheet had holes in it and the
    carved channel showed through them as strips of land lying in the river (Round 89, Mike).
    Six vertices go and the ring survives 0.1 m rounding, the area moving 0.02 km2.
    """
    pts = [tuple(p) for p in coords]
    if pts and pts[0] == pts[-1]:
        pts = pts[:-1]
    changed = True
    while changed and len(pts) > 4:
        n = len(pts)
        drop = [math.hypot(pts[(i - 1) % n][0] - pts[(i + 1) % n][0],
                           pts[(i - 1) % n][1] - pts[(i + 1) % n][1]) < eps for i in range(n)]
        changed = any(drop)
        if changed:
            pts = [p for i, p in enumerate(pts) if not drop[i]]
    return pts


def emit_ring(coords, nd=1):
    """despike, round to nd decimals, drop repeats: the ring as it goes in the json."""
    r = [[round(x, nd), round(z, nd)] for x, z in despike(coords)]
    out = [r[0]] + [p for i, p in enumerate(r[1:], 1) if p != r[i - 1]]
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def quad_hole_ring(polys):
    """the hole the page cuts in the Delaware's water quad: every shipped polygon (islands filled) buffered QUAD_R, less
    the tidal Delaware and its own margin, the reach east of DEL_X and QUAD_R short of the z cut; the largest piece, whole
    metres, refused unless simple"""
    outline = unary_union([Polygon(p['ring']) for p in polys])
    hole = outline.buffer(QUAD_R, resolution=4)
    dl = json.load(open(DELAWARE))
    dpoly = unary_union([Polygon(p['ring'], p.get('holes') or []).buffer(0) for p in dl.get('polys') or []])
    hole = hole.difference(dpoly.buffer(QUAD_R, resolution=4))
    hole = hole.difference(box(DEL_X, -1e6, 1e6, 1e6)).difference(box(-1e6, Z_MAX - QUAD_R, 1e6, 1e6))
    pieces = list(hole.geoms) if isinstance(hole, MultiPolygon) else [hole]
    best = max(pieces, key=lambda g: g.area)
    ring = [[int(round(x)), int(round(z))] for x, z in Polygon(best.exterior).simplify(8.0).exterior.coords][:-1]   # 8 m: the edge stays 51 to 68 m out, the drowned band is the first 25
    ring = [ring[0]] + [q for i, q in enumerate(ring[1:], 1) if q != ring[i - 1]]
    if len(ring) < 3 or not LinearRing(ring + [ring[0]]).is_simple or not Polygon(ring).is_valid:
        raise SystemExit('bake_schuylkill: the quad hole is not a simple ring (%d pts)' % len(ring))
    return ring


def quad_keep_rings(polys, hole):
    """the quad's patches inside its hole: the outline's island holes (Peters Island, Manayunk's islands, the bridge piers
    OSM cuts out of the river) grown QUAD_KEEP and merged where they meet, where the quad keeps the water it always showed
    (a pier's hole is smaller than a ground cell and its ground is the bed's: without the quad it was a pit in the river)"""
    hp = Polygon(hole)
    grown = unary_union([Polygon(h).buffer(QUAD_KEEP, resolution=2) for p in polys for h in (p.get('holes') or [])]).intersection(hp)
    out = []
    for g in (list(grown.geoms) if hasattr(grown, 'geoms') else [grown]):
        if g.is_empty or g.geom_type != 'Polygon' or g.area < 1:
            continue
        r = [[int(round(x)), int(round(z))] for x, z in Polygon(g.exterior).simplify(1.0).exterior.coords][:-1]
        r = [r[0]] + [q for i, q in enumerate(r[1:], 1) if q != r[i - 1]]
        if len(r) < 3 or not LinearRing(r + [r[0]]).is_simple or not Polygon(r).within(hp):
            raise SystemExit('bake_schuylkill: a quad patch is not a simple ring inside the hole (%d pts)' % len(r))
        out.append(r)
    if len(out) > 1 and any(Polygon(a).intersects(Polygon(b)) for i, a in enumerate(out) for b in out[i + 1:]):
        raise SystemExit('bake_schuylkill: two quad patches overlap')
    return out


def main():
    if os.path.exists(CACHE) and '--force' not in sys.argv:
        data = json.load(open(CACHE))
    else:
        data = overpass.fetch(QUERY)
        os.makedirs('lidar_cache', exist_ok=True)
        json.dump(data, open(CACHE, 'w'))
        if provenance:
            provenance.record('bake_schuylkill.overpass', 'overpass waterway=river Schuylkill', {'query': QUERY}, len(data.get('elements', [])))
    ways = [w for w in data.get('elements', []) if w.get('type') == 'way' and w.get('geometry')]
    lines = []
    for w in ways:
        pts = [to_xz(g['lat'], g['lon']) for g in w['geometry']]
        if len(pts) < 2:
            continue
        ls = LineString(pts).simplify(3.0)
        lines.append([[round(x, 1), round(z, 1)] for x, z in ls.coords])
    # the outline: OSM's natural=water river multipolygons around the waterway, polygonised
    if os.path.exists(CACHE_OUTLINE) and '--force' not in sys.argv:
        raw = json.load(open(CACHE_OUTLINE))
    else:
        raw = overpass.fetch(QUERY_OUTLINE)
        json.dump(raw, open(CACHE_OUTLINE, 'w'))
        if provenance:
            provenance.record('bake_schuylkill.overpass', 'overpass natural=water around the Schuylkill', {'query': QUERY_OUTLINE}, len(raw.get('elements', [])))
    edges = []
    for e in raw.get('elements', []):
        if e.get('type') == 'way' and e.get('geometry') and (e.get('tags') or {}).get('water') not in ('rapids', 'fish_pass', 'stream'):
            edges.append(LineString([to_xz(g['lat'], g['lon']) for g in e['geometry']]))
        elif e.get('type') == 'relation' and (e.get('tags') or {}).get('water') in ('river', 'canal', None):
            for m in e.get('members', []):
                if m.get('type') == 'way' and m.get('geometry') and m.get('role') in ('outer', 'inner', ''):
                    edges.append(LineString([to_xz(g['lat'], g['lon']) for g in m['geometry']]))
    thread = unary_union([LineString(l) for l in lines if len(l) >= 2]).buffer(25.0)
    faces = [f for f in polygonize(unary_union(edges)) if f.area > 2000 and f.intersects(thread)]
    # the ribbon fills GAPS in the outline only: buffered everywhere it widened every reach the
    # outline already bounds (the river is 100 m between the walls at Center City, the ribbon
    # 120 m, and the Schuylkill Banks trail stood in the water with its trees and lamps), so the
    # centreline is cut to the parts outside the faces before it is buffered
    outline = unary_union(faces)
    thread_lines = unary_union([LineString(l) for l in lines if len(l) >= 2]).difference(outline)
    ribbon = thread_lines.buffer(HALF_W, cap_style=2, join_style=2)
    # the pool behind the Fairmount Dam bounds the ribbon in POOL_REACH (see POOL_REACH): its outer rings only
    reach = box(POOL_REACH[0], POOL_REACH[1], POOL_REACH[2], POOL_REACH[3])
    pool = []
    for e in raw.get('elements', []):
        if e.get('type') == 'relation' and (e.get('tags') or {}).get('water') == 'reservoir':
            outer = [LineString([to_xz(g['lat'], g['lon']) for g in m['geometry']]) for m in e.get('members', [])
                     if m.get('type') == 'way' and m.get('geometry') and m.get('role') == 'outer']
            pool += [f for f in polygonize(unary_union(outer)) if f.intersects(reach)] if outer else []
    if pool:   # closed first (out POOL_CLOSE and back), so the gaps between the dam's fragments' ribbons, a 1,300 m2 triangle of
        # land off the island's tip and a wedge at the dam's west end, are water there; then never past the pool's bank
        closed = ribbon.buffer(POOL_CLOSE, join_style=2).buffer(-POOL_CLOSE, join_style=2)
        ribbon = ribbon.difference(reach).union(closed.intersection(reach).intersection(unary_union(pool)))
    water = unary_union(faces + [ribbon]).intersection(box(-16000, Z_MIN, 4000, Z_MAX)).simplify(1.5)
    geoms = list(water.geoms) if isinstance(water, MultiPolygon) else [water]
    polys = []
    for g in sorted(geoms, key=lambda g: -g.area):
        if g.area < 5000:
            continue
        ring = emit_ring(g.exterior.coords)
        holes = [emit_ring(h.coords) for h in g.interiors if Polygon(h).area > 300]
        # never ship a ring earcut cannot triangulate: an invalid ring leaves whole pockets
        # untriangulated and the carved channel shows through the water sheet (Round 89)
        for name, r in [('ring', ring)] + [('hole', h) for h in holes]:
            if len(r) < 3 or not LinearRing(r + [r[0]]).is_simple:
                raise SystemExit('bake_schuylkill: emitted %s is not a simple ring (%d pts)' % (name, len(r)))
        if not Polygon(ring, holes).is_valid:
            raise SystemExit('bake_schuylkill: emitted polygon invalid: %s'
                             % explain_validity(Polygon(ring, holes))[:120])
        polys.append({'ring': ring, 'holes': holes})
    quad_hole = quad_hole_ring(polys)
    quad_keep = quad_keep_rings(polys, quad_hole)
    out = {'src': 'OpenStreetMap waterway=river ways named Schuylkill and the natural=water polygons around them, via Overpass (ODbL), model frame (philly_frame.py)',
           'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'half_w': HALF_W, 'z_range': [Z_MIN, Z_MAX],
           'lines': lines, 'polys': polys, 'quad_hole': quad_hole, 'quad_keep': quad_keep}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    zs = [p[1] for l in lines for p in l]
    print(f'{OUT}: {len(lines)} fragments ({sum(len(l) for l in lines)} pts, z {min(zs):.0f}..{max(zs):.0f}), '
          f'{len(faces)} outline faces, {len(polys)} water polygons ({sum(len(p["ring"]) for p in polys)} ring pts, '
          f'{sum(len(p["holes"]) for p in polys)} island holes) over {water.area / 1e4:.1f} ha, the quad\'s hole {len(quad_hole)} pts '
          f'over {Polygon(quad_hole).area / 1e4:.1f} ha with {len(quad_keep)} patches, {os.path.getsize(OUT):,} bytes', flush=True)


if __name__ == '__main__':
    main()
