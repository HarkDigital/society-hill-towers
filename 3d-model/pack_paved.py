#!/usr/bin/env python3
"""osm_paved_raw.json + osm_landuse_raw.json -> paved.b64 : the paved ground, for the app's
'Paving the lots and yards' step. Since Round 52 every unbuilt surface is the meadow, so the
port terminals, the rail yards, the refineries, the big-box lots and every surface parking
lot in the city were green. This packs them as flat rings the app lays on the drawn ground
under the parks and the streets.

Kinds: 1 surface parking lot (asphalt); 2 industrial / port / commercial / retail yard
(asphalt and concrete mixed: landuse industrial, commercial, retail, port, depot, garages,
brownfield, construction, quarry, landfill, and man_made=works); 3 rail yard (ballast,
landuse=railway); 4 airport apron (concrete, aeroway=apron). Residential land use stays
meadow, that is the game's look.

Layout (little-endian int16, base64 in the file): [0] magic 0x5056 'PV', [1] version 1,
[2] nPolys low 16 bits, [3] nPolys >> 16; then per polygon n, kind, x0, z0 ... xn-1, zn-1 in
whole metres, closed implicitly, CCW in (x, z) like pack_wide's rings (gotcha 10: the app
never orients earcut by the ring, but the wall-less flats key nothing off winding either;
CCW is simply the house convention). Every ring has n >= 3, lies inside the far-ring box
and, per kind, is part of one unary_union: two rings of one kind never sit coplanar, and a
lot inside a yard is a different kind that draws above it. Holes are dropped (the parks
and buildings inside draw above the sheet anyway). Rings centred in the hand-tuned core
box are dropped: the core has its own ground. Sorted by kind then centroid so a rerun on
the same extract writes the same bytes. Frame: philly_frame.py. Needs shapely."""
import base64, json, os, struct
from collections import Counter
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
from philly_frame import to_xz   # the one scene frame

CITY = (-12000, 16500, -21700, 9700)   # pack_city.py CITY (x0, x1, z0, z1): the terrain's extent
CORE = (-640, 770, -520, 850)          # app.js CORE_EXT, hand-tuned, keeps its own ground
MAGIC, VERSION = 0x5056, 1
SIMPLIFY = 1.0                         # metres; a lot's corner survives, a wavy port edge does not
MIN_AREA = {1: 200.0, 2: 400.0, 3: 400.0, 4: 400.0}   # m2; raise kind 1 first if the blob outgrows ~600 KB
YARD_LANDUSE = ('industrial', 'commercial', 'retail', 'port', 'depot', 'garages',
                'brownfield', 'construction', 'quarry', 'landfill')
NOT_SURFACE = ('multi-storey', 'underground', 'rooftop', 'carports', 'garage_boxes')
KIND_NAME = {1: 'lots', 2: 'yards', 3: 'rail', 4: 'aprons'}


def kind_of(t, from_landuse):
    """The kind a way's tags earn, or None. The landuse extract contributes only its three
    paved uses (residential is meadow); the paved extract carries the rest. A lot wins over
    the yard it may also be tagged as (it draws above), a garage is a building, not a lot."""
    if from_landuse:
        return 2 if t.get('landuse') in ('industrial', 'commercial', 'retail') else None
    if t.get('amenity') == 'parking':
        if t.get('parking') in NOT_SURFACE or t.get('building'):
            return None
        return 1
    if t.get('aeroway') == 'apron':
        return 4
    if t.get('landuse') == 'railway':
        return 3
    if t.get('landuse') in YARD_LANDUSE or t.get('man_made') == 'works':
        return 2
    return None


def polygons_of(path, from_landuse, stats):
    """Closed ways of one raw extract as {kind: [shapely Polygon in the scene frame]}."""
    d = json.load(open(os.path.join(HERE, path)))
    els = d['elements']
    nodes = {el['id']: (el['lat'], el['lon']) for el in els if el['type'] == 'node'}
    out = {k: [] for k in KIND_NAME}
    for el in els:
        if el['type'] != 'way':
            continue
        kind = kind_of(el.get('tags') or {}, from_landuse)
        if kind is None:
            continue
        ids = el.get('nodes') or []
        if len(ids) < 4 or ids[0] != ids[-1]:
            stats['open'] += 1
            continue
        pts = [to_xz(*nodes[i]) for i in ids[:-1] if i in nodes]
        if len(pts) < 3:
            stats['open'] += 1
            continue
        try:
            pg = Polygon(pts).buffer(0)   # self-touching OSM rings come back valid
        except Exception:
            stats['bad'] += 1
            continue
        if pg.is_empty:
            stats['bad'] += 1
            continue
        stats['tagged', kind] += 1
        out[kind].append(pg)
    return out


def rings(kind, polys, stats):
    """One kind's polygons -> [(cx, cz, [(x, z), ...])]: clipped, core dropped, unioned,
    holes dropped, simplified, floored, CCW, whole metres."""
    cityBox = box(CITY[0], CITY[2], CITY[1], CITY[3])
    kept = []
    for pg in polys:
        c = pg.centroid
        if CORE[0] <= c.x <= CORE[1] and CORE[2] <= c.y <= CORE[3]:
            stats['core'] += 1
            continue
        g = pg.intersection(cityBox)
        if g.is_empty:
            stats['outside'] += 1
            continue
        kept.append(g)
    if not kept:
        return []
    merged = unary_union(kept)
    geoms = list(merged.geoms) if hasattr(merged, 'geoms') else [merged]
    out = []
    for g in geoms:
        if g.geom_type != 'Polygon':
            continue
        shell = Polygon(g.exterior).simplify(SIMPLIFY)   # holes dropped: what is inside draws above
        if shell.is_empty or shell.area < MIN_AREA[kind]:
            stats['small', kind] += 1
            continue
        shell = orient(shell, 1.0)                      # CCW in (x, z): positive shoelace
        pts = [(int(round(x)), int(round(z))) for x, z in list(shell.exterior.coords)[:-1]]
        dedup = [p for i, p in enumerate(pts) if p != pts[i - 1]]   # rounding can fuse neighbours
        if len(dedup) < 3:
            stats['small', kind] += 1
            continue
        a2 = sum(dedup[i][0] * dedup[(i + 1) % len(dedup)][1] - dedup[(i + 1) % len(dedup)][0] * dedup[i][1]
                 for i in range(len(dedup)))
        if a2 <= 0:                                     # a sliver that rounding folded over
            stats['small', kind] += 1
            continue
        for x, z in dedup:
            assert CITY[0] - 1 <= x <= CITY[1] + 1 and CITY[2] - 1 <= z <= CITY[3] + 1, (x, z)
        dedup = [(min(CITY[1], max(CITY[0], x)), min(CITY[3], max(CITY[2], z))) for x, z in dedup]
        c = shell.centroid
        out.append((int(round(c.x)), int(round(c.y)), dedup))
    out.sort(key=lambda r: (r[0], r[1]))
    return out


def main():
    stats = Counter()
    byKind = {k: [] for k in KIND_NAME}
    for path, from_landuse in (('osm_paved_raw.json', False), ('osm_landuse_raw.json', True)):
        for k, pgs in polygons_of(path, from_landuse, stats).items():
            byKind[k].extend(pgs)
    body = [MAGIC, VERSION, 0, 0]
    nPolys = nVerts = 0
    counts = {}
    for kind in sorted(KIND_NAME):
        rs = rings(kind, byKind[kind], stats)
        counts[kind] = len(rs)
        for _, _, pts in rs:
            body.append(len(pts)); body.append(kind)
            for x, z in pts:
                body.append(x); body.append(z)
            nPolys += 1; nVerts += len(pts)
    body[2] = nPolys & 0xFFFF; body[3] = nPolys >> 16
    assert all(-32768 <= v <= 32767 for v in body)
    raw = struct.pack('<%dh' % len(body), *body)
    b64 = base64.b64encode(raw).decode('ascii')
    open(os.path.join(HERE, 'paved.b64'), 'w').write(b64)
    print('tagged ways: ' + ', '.join(f'{KIND_NAME[k]} {stats["tagged", k]}' for k in sorted(KIND_NAME))
          + f'; open {stats["open"]}, bad {stats["bad"]}, centred in the core {stats["core"]}, outside the box {stats["outside"]}')
    print('dropped under the area floor: ' + ', '.join(f'{KIND_NAME[k]} {stats["small", k]}' for k in sorted(KIND_NAME)))
    print('rings per kind: ' + ', '.join(f'{KIND_NAME[k]} ({k}) {counts[k]}' for k in sorted(KIND_NAME))
          + f'; {nPolys} rings, {nVerts} vertices')
    print(f'paved.b64 {len(raw)/1e3:.1f} KB raw, {len(b64)/1e3:.1f} KB base64', flush=True)


if __name__ == '__main__':
    main()
