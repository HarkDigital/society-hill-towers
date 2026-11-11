#!/usr/bin/env python3
"""LiDAR true-massing pass, stage 1: join City of Philadelphia 2022-LiDAR building
heights (lidar_cache/phl_footprints_local.json, from fetch_footprints.py) onto every
model building by polygon overlap in the local frame.

Outputs:
  - scene_wide.json, scene_south.json : b['h'] patched (geometry untouched). The
    heights are read from an IMMUTABLE snapshot, lidar_cache/scene_wide.pre_lidar.json
    and lidar_cache/scene_south.pre_lidar.json, created from the current scene file
    on the first run if absent and never rewritten - so the ratchet below compares
    against the ORIGINAL OSM value, not against this script's own previous output
    (the in-place rewrite used to make every rerun read its own patched heights,
    which turned "never lower a tall" into "never lower anything a run ever raised").
    The current scene file is what gets patched, building by building index, so
    attributes other passes wrote in place (patch_scenes_facade's fa/rp) survive.
    Buildings left unmeasured/protected are reset to the snapshot's h, so the
    output is a pure function of (snapshot, footprints). A snapshot is only as
    pristine as the file it was taken from: after regenerating a scene with
    process_osm.py (or if the count/order no longer lines up, which is fatal),
    delete the snapshot and rerun.
  - lidar_city_heights.json           : {osm way id: h_m} for pack_city.py
  - lidar_cache/core_join.json        : per-core-building measured h (consumed +
                                        refined by lidar_core.py, which also does
                                        roof forms from the raw point cloud)
  - lidar_report.json                 : stats, known-truth table, top deltas

Rules:
  - overlap coverage >= 25% of the target polygon, else unmeasured (keeps old h)
  - h = intersection-area-weighted mean of footprint heights; if pieces >= 1.5x
    that mean cover >= 45% of the target, use just those (tower-on-podium ways)
  - contamination guard: a city footprint with max_hgt > 3x approx_hgt (approx >=
    3 m, max >= 8 m) is ignored (crane/tree-contaminated outliers)
  - confirmed spikes (Round 160): a footprint under the 3x guard whose max_hgt the
    point cloud contradicts contributes approx_hgt instead (see spike_check), and the
    tall protection below no longer defends a snapshot height that is that spike
  - tag protection (scenes): if existing h > 30 and measured < 0.6*h, keep h
    (spires and buildings finished after the 2022 flight); pack_city applies
    max(tag, measured) since it still sees real OSM tags
  - skip: t in (ship, stadium, arena), entries with minH (3D parts), custom towers
  - clamp 2.5..550 m
  - east of the Delaware (Round 231): the City's footprints stop at the city line, so a scene
    building the join above leaves unmeasured, standing outside the city line (city_limit.json)
    and east of EAST_X, takes the citywide roof pass's own height where that pass measured
    its OSM way (lidar_city_roofs.json: P90 above ground for a flat roof, the ridge for a
    pitched one); see roof_pass_height. The talls' ratchet applies to it as to every other
    measure. Nothing west of the river takes a height from this source, and every row it
    gives is written to lidar_east_heights.json. A way in ROOF_HELD gives none (a bridge's
    anchorage, where the "roof" is the deck; two port structures nobody has checked) and
    is listed there under "held"
Frame: philly_frame.py (the scene's own projection). This script used to hardcode
KX=85350, which put the city footprints up to ~1.1 m east of the far-ring ways
they were overlapped with (a few % of coverage on narrow rowhouses); the committed
lidar_city_heights.json and the patched scenes keep that until the next rerun.
Run with the shapely venv python."""
import json, math, os, sys
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
from philly_frame import LON0, LAT0, KX, KZ   # the one scene frame
COVER_MIN = 0.25
CLAMP_LO, CLAMP_HI = 2.5, 550.0
SKIP_T = {'ship', 'stadium', 'arena'}

SPIKE_RATIO = 2.0          # a spike's max stands at least this many times the footprint's approx_hgt
SPIKE_ROOF_K, SPIKE_ROOF_M = 1.5, 10.0   # ... and over 1.5 x the flat LiDAR roof + 10 m
SPIKE_AGREE = 0.25         # ... while approx_hgt agrees with that roof within 25 %
SPIKE_COVER = 0.5          # the flat-roofed way covers at least half the footprint
WORSHIP_T = 'worship'

# Round 231: Camden at its measured heights. The City's footprint heights end at the city line, so every building east
# of the Delaware stood at process_osm's default for its kind: of the 1,195 buildings of scene_wide.json between
# x 1,250 and 2,400 and z -1,400 and 3,600, 614 at exactly 10.5 m, 180 at 13 and 163 at 11, one flat shelf of boxes
# behind the Battleship New Jersey. The 2022 flight's tiles reach about 750 m into New Jersey (scene x 2,010 on the
# core's row) and the citywide roof pass (fetch_lidar_roofs.py) measured the OSM ways under them, forms and heights
# both; the packers read lidar_city_roofs.json for the forms only and this script for the spike check only.
# How the two sources compare, on the 7,353 wide-scene buildings west of the river that both measure: the pass reads a
# median 1.5 m under the City's footprint (the City gives max_hgt, the pass a P90 or a P95 of the roof's own cells),
# within 3 m on 71%, and over it by more than 5 m on 20 of them (0.27%). It under-reads, it does not spike.
EAST_X = 1000.0            # a belt under the city line test: nothing west of this reads the roof pass, whatever the
                           # line file says (Camden's bank lies between x 1,000 and 1,250: the battleship's berth is at
                           # 996, the American Water building at 1,192; 38 of the wide scene's New Jersey buildings
                           # stand west of 1,250, the water's edge the river walk looks straight at)
ROOF_COVER = 0.5           # the building and its way cover at least half of each other: one building, one way
# Round 231, the review: what the pass measured is not always a roof, and a reading nothing can vouch for is not a
# height. A way named in ROOF_HELD (roof_ways adds the bridge supports to it) gives no height: its building keeps the
# default it had, its blob word does not move, and lidar_east_heights.json lists it under "held" with what the pass
# read and why.
# - A bridge's anchorage is not a building. OSM maps the Delaware bridges' New Jersey anchorages as building ways
#   tagged bridge:support (way 1044593722 the Walt Whitman's, 55 by 33 m at scene (1853, 4573); way 334628517 the Ben
#   Franklin's Camden pier; way 754832343 under the Ben Franklin's east tower, which the talls' ratchet was already
#   holding), and the flight's flat "roof" over each is the roadway on top of it (38.8, 38.1 and 40.8 m). The
#   page draws its own bridges: its BRIDGE_SKIP drops the Ben Franklin's anchorage and both bridges' towers but not
#   the Walt Whitman's anchorage, which at 13 m sat hidden under the deck and at 38.8 stood across the roadway as a
#   glass office block with the traffic driving into its wall.
# - Two unnamed port structures the pass reads over 30 m, the line where the page's wide loop stops dressing a record
#   as fabric and dresses it as an office tower (towerStyle). Flat within a metre, so real roofs, but OSM gives no
#   name, no levels, no trade and no land use under either, and their type words (commercial, plain) cannot say
#   "industrial": in the review's captures the 84 by 31 m shed at the foot of Kaighn Avenue drew as a blue curtain
#   wall at the water's edge and the 916 sq m block at (1686, 3193) as a white slab. Held until someone has looked at
#   the orthophoto; a third (way 576393381, 33.2 m, at (1794, 3585)) is tagged office=company and keeps its reading.
ROOF_HELD = {
    265973742: 'unnamed port structure (building=commercial) read at 35.8 m; unchecked, and over 30 m it would be dressed as an office tower',
    1186523447: 'unnamed port structure (a Microsoft footprint, no tags) read at 31.9 m; unchecked, and over 30 m it would be dressed as an office tower',
}
BRIDGE_SUPPORT = 'a bridge support (OSM bridge:support): the reading is the deck over it, and the page draws its own bridges'

def roof_ways():
    """{way id: (scene-frame Polygon, top AGL m, form)} for the OSM building ways the citywide LiDAR roof pass
    (lidar_city_roofs.json, fetch_lidar_roofs.py) measured: every flat one (form 0: P90 - P10 under 1 m over its
    cells, or a level roof with bulkheads; top = P90) and, east of EAST_X only, the pitched ones (form 1 gable, 2 hip;
    top = the ridge, P95), which nothing west of the river reads. Polygons from whichever OSM raws are on disk (the
    pass's own rings are UTM). A way OSM tags bridge:support is noted in ROOF_HELD on the way through (it stays in
    the result: the spike check's witnesses are as they were)."""
    roofs = json.load(open('lidar_city_roofs.json')) if os.path.exists('lidar_city_roofs.json') else {}
    meas = {int(k): (v[2], v[0]) for k, v in roofs.items() if v[0] in (0, 1, 2)}
    out = {}
    for f in ('osm_wide_raw.json', 'osm_south_raw.json', 'osm_city_raw.json'):
        if not os.path.exists(f):
            continue
        els = json.load(open(f))['elements']
        nodes = {e['id']: (e['lon'], e['lat']) for e in els if e.get('type') == 'node'}
        for e in els:
            if e.get('type') != 'way' or e['id'] not in meas or e['id'] in out:
                continue
            g = e.get('geometry')
            pts = ([((q['lon'] - LON0) * KX, (LAT0 - q['lat']) * KZ) for q in g] if g else
                   [((nodes[n][0] - LON0) * KX, (LAT0 - nodes[n][1]) * KZ) for n in e.get('nodes', []) if n in nodes])
            if len(pts) < 4:
                continue
            top, form = meas[e['id']]
            if 'bridge:support' in e.get('tags', {}):
                ROOF_HELD.setdefault(e['id'], BRIDGE_SUPPORT)
            if form != 0 and max(q[0] for q in pts) <= EAST_X:
                continue
            try:
                pg = Polygon(pts).buffer(0)
            except Exception:
                continue
            if pg.area > 20:
                out[e['id']] = (pg, top, form)
        del els, nodes
    return out

def flat_roof_ways(ways=None):
    """{way id: (scene-frame Polygon, P90 AGL m)}: the flat-roofed ways of roof_ways(), the spike check's witnesses."""
    ways = roof_ways() if ways is None else ways
    return {wid: (pg, top) for wid, (pg, top, form) in ways.items() if form == 0}

def city_line():
    """Philadelphia's own line in the scene frame (city_limit.json's `city`, fetch_boundary.py). It runs down the
    middle of the Delaware, so 'outside it and east of EAST_X' is New Jersey. Fatal without the file: a silent skip
    would put every building east of the river back at its default."""
    if not os.path.exists('city_limit.json'):
        sys.exit('ERROR: city_limit.json missing - the roof pass heights east of the Delaware need the city line '
                 '(fetch_boundary.py)')
    pg = Polygon(json.load(open('city_limit.json'))['city'])
    return pg if pg.is_valid else pg.buffer(0)

def east_of_river(cx, cz, line):
    """True for a point on the New Jersey side: east of EAST_X and outside the city line (north of about z -2,400
    the river bends east and the same x is Fishtown and Kensington, which the City's footprints measure)."""
    return cx > EAST_X and not line.contains(Point(cx, cz))

def roof_pass_height(pg, east_tree, east_list):
    """(top AGL m, way id, form) from the roof pass for a scene building's polygon, or None. The scene's buildings ARE
    the OSM ways, so the rule is identity rather than a blend: the way that overlaps the building most, with the
    overlap at least ROOF_COVER of BOTH (a kiosk inside a big way's outline, or a big building over a small way, is
    not that way's measurement and keeps its default). A building whose way is in ROOF_HELD gets None and is noted
    in east_held: the next best way is never taken in a held one's place."""
    best = None
    for j in east_tree.query(pg):
        wid, wpg, top, form = east_list[j]
        try:
            ia = pg.intersection(wpg).area
        except Exception:
            continue
        if ia >= ROOF_COVER * pg.area and ia >= ROOF_COVER * wpg.area and (best is None or ia > best[0]):
            best = (ia, top, wid, form)
    if best is None:
        return None
    if best[2] in ROOF_HELD:
        c = pg.centroid
        east_held.append([best[2], best[3], round(float(best[1]), 1), round(c.x), round(c.y), ROOF_HELD[best[2]]])
        return None
    return max(CLAMP_LO, min(CLAMP_HI, float(best[1]))), best[2], best[3]

def spike_check(pg, h, a, flat_tree, flat_list):
    """True when this footprint's max_hgt is a CONFIRMED spike (Round 160). The Reading Terminal headhouse's City
    footprint reads max 125.07 m over approx 44.5 m, a ratio of 2.81 under the 3x guard, so the headhouse outline and
    its two-storey link to the train shed stood 125 m tall. Two independent measures must agree against the max: an
    OSM way covering at least half the footprint has a FLAT LiDAR roof (P90 - P10 under 1 m, so anything taller covers
    under a tenth of it: a crane, a mast, a bad return, never a building's mass) and the max stands over 1.5 x that
    roof + 10 m; and the City's own approx_hgt agrees with that roof within 25 % while the max is at least twice it.
    A steeple is indistinguishable from a spike in these numbers, which is why the caller exempts places of worship."""
    if not (a and a >= 3.0 and h >= 20.0 and h >= SPIKE_RATIO * a):
        return False
    for j in flat_tree.query(pg):
        wpg, p90 = flat_list[j]
        if (h > SPIKE_ROOF_K * p90 + SPIKE_ROOF_M and abs(a - p90) <= SPIKE_AGREE * p90
                and pg.intersection(wpg).area >= SPIKE_COVER * pg.area):
            return True
    return False

print('loading flat LiDAR roofs...', flush=True)
_ways = roof_ways()
_flat = list(flat_roof_ways(_ways).values())
flat_tree = STRtree([w[0] for w in _flat])
print(f'{len(_flat)} flat-roofed ways', flush=True)
CITY_LINE = city_line()
# the roof pass's ways on the New Jersey side, flat and pitched: the only ones roof_pass_height reads
east_list = []
for _wid, (_pg, _top, _form) in _ways.items():
    _c = _pg.centroid
    if east_of_river(_c.x, _c.y, CITY_LINE):
        east_list.append((_wid, _pg, _top, _form))
east_tree = STRtree([w[1] for w in east_list])
print(f'{len(east_list)} roof-pass ways east of the Delaware', flush=True)
del _ways

print('loading city footprints...', flush=True)
fpd = json.load(open('lidar_cache/phl_footprints_local.json'))['fps']
fp_geoms, fp_h, fp_hmax = [], [], []   # fp_h: a confirmed spike's approx_hgt; fp_hmax: max_hgt as the City gives it
spiked = set()             # indices into fp_geoms
n_guard = 0
for h, a, rings in fpd:
    if h is None or h <= 0:
        continue
    # contamination guard (cranes, overhanging trees, bad returns)
    if a is not None and a >= 3.0 and h >= 8.0 and h > 3.0 * a:
        n_guard += 1
        continue
    shell = list(zip(rings[0][0::2], rings[0][1::2]))
    holes = [list(zip(r[0::2], r[1::2])) for r in rings[1:] if len(r) >= 8]
    try:
        pg = Polygon(shell, holes)
        if not pg.is_valid:
            pg = pg.buffer(0)
        if pg.is_empty or pg.area < 4:
            continue
    except Exception:
        continue
    if spike_check(pg, h, a, flat_tree, _flat):
        spiked.add(len(fp_geoms))
    fp_geoms.append(pg)
    fp_hmax.append(min(CLAMP_HI, h))
    fp_h.append(min(CLAMP_HI, a if len(fp_geoms) - 1 in spiked else h))
print(f'{len(fp_geoms)} usable footprints ({n_guard} dropped by contamination guard, {len(spiked)} confirmed spikes)', flush=True)
del _flat, flat_tree
tree = STRtree(fp_geoms)

def measure(poly_pts, holes_pts=None, use_max=False):
    """poly in local meters -> (h, coverage, touched) or (None, cov, touched). use_max reads max_hgt even where a
    footprint's max is a confirmed spike (places of worship: their spike is the steeple); touched says whether any
    confirmed spike overlapped the polygon."""
    H = fp_hmax if use_max else fp_h
    try:
        pg = Polygon(poly_pts, holes_pts or None)
        if not pg.is_valid:
            pg = pg.buffer(0)
        if pg.is_empty or pg.area < 2:
            return None, 0.0, False
    except Exception:
        return None, 0.0, False
    idxs = tree.query(pg)
    if len(idxs) == 0:
        return None, 0.0, False
    inters, touched = [], False
    for i in idxs:
        try:
            ia = pg.intersection(fp_geoms[i]).area
        except Exception:
            continue
        if ia > 0.5:
            inters.append((ia, H[i]))
            touched = touched or i in spiked
    if not inters:
        return None, 0.0, touched
    tot = sum(ia for ia, _ in inters)
    cov = tot / pg.area
    if cov < COVER_MIN:
        return None, cov, touched
    wmean = sum(ia * h for ia, h in inters) / tot
    # dominant tall mass: when the tallest pieces carry most of the footprint, the
    # box stands at their height (a tower sharing its OSM way with a podium must
    # not read 30% short — the 1.5x refinement alone can't fire when the tower
    # itself drags the mean up). wmax only from pieces with real coverage.
    big = [h for ia, h in inters if ia >= 8]
    if big:
        wmax = max(big)
        dom = [(ia, h) for ia, h in inters if h >= 0.72 * wmax]
        dom_cov = sum(ia for ia, _ in dom) / pg.area
        if dom_cov >= 0.5 and wmax > wmean * 1.12:
            wmean = sum(ia * h for ia, h in dom) / sum(ia for ia, _ in dom)
        else:
            tall = [(ia, h) for ia, h in inters if h >= 1.5 * wmean]
            tall_cov = sum(ia for ia, _ in tall) / pg.area
            if tall and tall_cov >= 0.45:
                wmean = sum(ia * h for ia, h in tall) / sum(ia for ia, _ in tall)
    return max(CLAMP_LO, min(CLAMP_HI, wmean)), cov, touched

report = {'footprints': len(fp_geoms), 'contamination_guard': n_guard, 'confirmed_spikes': len(spiked), 'sets': {}}
spike_log = []   # (set, name, cx, cz, what the join gave before Round 160, what it gives now)
deltas = []  # (|dh|, set, name, cx, cz, old, new)
east_rows = []   # Round 231: [set, building index, way id, form, old h, new h, cx, cz, name], every height the roof pass gave
east_held = []   # Round 231, the review: [way id, form, what the pass read, cx, cz, why] for every ROOF_HELD way a building matched

def snapshot_path(path):
    """lidar_cache/<scene>.pre_lidar.json: the scene's heights as they were before any LiDAR pass."""
    return os.path.join('lidar_cache', os.path.basename(path)[:-5] + '.pre_lidar.json')

def patch_scene(path, tag):
    d = json.load(open(path))
    snap_path = snapshot_path(path)
    if os.path.exists(snap_path):
        snap = json.load(open(snap_path))
    else:
        # first run: freeze the current file as the pre-LiDAR baseline (only pristine if
        # this really is process_osm output - see the docstring); never rewritten after
        os.makedirs('lidar_cache', exist_ok=True)
        with open(snap_path, 'w') as f:
            json.dump(d, f, separators=(',', ':'))
        print(f'{snap_path}: pre-LiDAR snapshot created from {path}', flush=True)
        snap = d
    sb, cb = snap['buildings'], d['buildings']
    if len(sb) != len(cb) or any(a.get('poly', [])[:2] != b.get('poly', [])[:2] for a, b in zip(sb, cb)):
        sys.exit(f'ERROR: {snap_path} no longer lines up with {path} (building count or order differs): '
                 f'the scene was regenerated since the snapshot - delete the snapshot and rerun')
    st = {'total': 0, 'measured': 0, 'protected': 0, 'unmeasured': 0, 'skipped': 0}
    for bi, (b, b0) in enumerate(zip(cb, sb)):
        poly = b.get('poly')
        if not poly or len(poly) < 3 or b.get('t') in SKIP_T or b.get('minH'):
            st['skipped'] += 1
            continue
        st['total'] += 1
        old = b0['h']          # the ORIGINAL OSM value from the snapshot, never our own previous output
        worship = b.get('t') == WORSHIP_T
        h, cov, touched = measure(poly, b.get('holes'), use_max=worship)
        if h is None:
            # Round 231: east of the Delaware the roof pass's own measurement, where it has one for this building's way
            cx = sum(p[0] for p in poly) / len(poly)
            cz = sum(p[1] for p in poly) / len(poly)
            rp = None
            if east_of_river(cx, cz, CITY_LINE):
                try:
                    pg = Polygon(poly, b.get('holes') or None)
                    if not pg.is_valid:
                        pg = pg.buffer(0)
                    rp = None if pg.is_empty or pg.area < 2 else roof_pass_height(pg, east_tree, east_list)
                except Exception:
                    rp = None
            if rp is None:
                st['unmeasured'] += 1
                b['h'] = old
                continue
            hr, wid, form = rp
            # the same ratchet as below: a tall (over 30 m, tagged in practice) is raised by a measurement, never
            # lowered (Camden Tower is tagged 37.2 m and the pass reads 28.4)
            if old > 30 and hr < old:
                st['roof_pass_protected'] = st.get('roof_pass_protected', 0) + 1
                b['h'] = old
                continue
            st['roof_pass'] = st.get('roof_pass', 0) + 1
            b['h'] = round(hr, 1)
            east_rows.append([tag, bi, wid, form, old, b['h'], round(cx), round(cz), b.get('name')])
            if abs(hr - old) > 0.05:
                deltas.append((round(abs(hr - old), 1), tag, b.get('name'), round(cx), round(cz), old, round(hr, 1)))
            continue
        # Round 160: the snapshot is not pristine everywhere (it was frozen from a scene an earlier join had already
        # patched in place: the Reading Terminal link reads 125.1 there, though OSM tags it two storeys), so the
        # protection below must not defend a tall that is exactly what a confirmed spike gives this very join
        inherited = False
        if touched and not worship and old > 30:
            h_max = measure(poly, b.get('holes'), use_max=True)[0]
            inherited = h_max is not None and abs(old - h_max) < 1.0 and h < h_max - 0.05
        # talls (>30 = explicitly tagged in practice) follow OSM's max-height tag
        # semantics: LiDAR may raise them (stale/low tags) but never lower them —
        # mixed tower+podium ways would otherwise read 30% short, and the two
        # known wrong-HIGH tags are hand-overridden in the app anyway
        if old > 30 and h < old and not inherited:
            st['protected'] += 1
            b['h'] = old
            continue
        st['measured'] += 1
        cx = sum(p[0] for p in poly) / len(poly)
        cz = sum(p[1] for p in poly) / len(poly)
        if inherited:
            st['spike_released'] = st.get('spike_released', 0) + 1
            spike_log.append((tag, b.get('name'), round(cx), round(cz), old, round(h, 1)))
        b['h'] = round(h, 1)
        if abs(h - old) > 0.05:
            deltas.append((round(abs(h - old), 1), tag, b.get('name'), round(cx), round(cz), old, round(h, 1)))
    json.dump(d, open(path, 'w'), separators=(',', ':'))
    report['sets'][tag] = st
    print(tag, st, flush=True)

# --- wide + south scenes (patched in place; pack_wide.py reads them) ---
patch_scene('scene_wide.json', 'wide')
patch_scene('scene_south.json', 'south')
# Round 231: the roof pass's heights east of the river, row by row (tests/test_wide_repack.py holds wide.b64 to them)
with open('lidar_east_heights.json', 'w') as f:
    f.write('{"rule":"outside the city line and east of x %g, unmeasured by the City footprints, the roof pass way covering '
            'at least %g of the building and the building of it; a way listed under held gives no height and its building keeps its default",'
            '"cols":["set","building","way","form","old","new","cx","cz","name"],"held_cols":["way","form","read","cx","cz","why"],"held":[\n'
            % (EAST_X, ROOF_COVER) + ',\n'.join(json.dumps(r, separators=(',', ':')) for r in sorted(east_held)) + '\n],"rows":[\n'
            + ',\n'.join(json.dumps(r, separators=(',', ':')) for r in east_rows) + '\n]}\n')
print(f'lidar_east_heights.json: {len(east_rows)} heights from the roof pass east of the Delaware, {len(east_held)} held back', flush=True)
report['east_roof_pass'] = {'ways': len(east_list), 'heights': len(east_rows), 'held': len(east_held),
                            'changed': sum(1 for r in east_rows if abs(r[5] - r[4]) > 0.05),
                            'over_20m': sum(1 for r in east_rows if r[5] > 20)}

# --- core: measure only, lidar_core.py patches scene.json with LAZ refinement ---
core = json.load(open('scene.json'))
core_out = {}
st = {'total': 0, 'measured': 0, 'unmeasured': 0, 'skipped': 0}
for i, b in enumerate(core['buildings']):
    poly = b.get('poly')
    if not poly or len(poly) < 3 or b.get('t') in SKIP_T or b.get('minH'):
        st['skipped'] += 1
        continue
    st['total'] += 1
    h, cov, _ = measure(poly, b.get('holes'), use_max=b.get('t') == WORSHIP_T)
    if h is None:
        st['unmeasured'] += 1
        continue
    st['measured'] += 1
    core_out[str(i)] = round(h, 2)
json.dump(core_out, open('lidar_cache/core_join.json', 'w'))
report['sets']['core_join'] = st
print('core_join', st, flush=True)

# --- far ring: way id -> h from the raw dump (pack_city.py looks these up) ---
if '--skip-city' in sys.argv:
    print('skipping city LUT (--skip-city; lidar_city_heights.json kept as-is)', flush=True)
    deltas.sort(key=lambda e: -e[0])
    report['top_deltas'] = deltas[:50]
    report['spike_released'] = spike_log
    rep_old = json.load(open('lidar_report.json')) if os.path.exists('lidar_report.json') else {}
    if 'sets' in rep_old and 'city_lut' in rep_old.get('sets', {}):
        report['sets']['city_lut'] = rep_old['sets']['city_lut']
    d = json.load(open('scene_wide.json'))
    truths = {}
    for b in d['buildings']:
        if b.get('name') in ('One Liberty Place', 'Two Liberty Place', 'Comcast Center',
                             'Comcast Technology Center', 'City Hall', 'Hopkinson House',
                             'Society Hill Towers', 'The Ryland', 'Dockside'):
            truths.setdefault(b['name'], []).append(b['h'])
    report['known_truths_wide'] = truths
    json.dump(report, open('lidar_report.json', 'w'), indent=1)
    print('lidar_report.json written', flush=True)
    sys.exit(0)
print('loading osm_city_raw.json (377 MB)...', flush=True)
raw = json.load(open('osm_city_raw.json'))
els = raw['elements']
nodes = {}
for el in els:
    if el.get('type') == 'node':
        nodes[el['id']] = ((el['lon'] - LON0) * KX, (LAT0 - el['lat']) * KZ)
lut = {}
st = {'total': 0, 'measured': 0, 'unmeasured': 0}
for el in els:
    if el.get('type') != 'way':
        continue
    t = el.get('tags') or {}
    if 'building' not in t:
        continue
    pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        continue
    st['total'] += 1
    h, cov, _ = measure(pts, use_max=t.get('amenity') == 'place_of_worship')
    if h is None:
        st['unmeasured'] += 1
        continue
    st['measured'] += 1
    lut[el['id']] = round(h, 1)
json.dump(lut, open('lidar_city_heights.json', 'w'), separators=(',', ':'))
report['sets']['city_lut'] = st
print('city_lut', st, flush=True)

deltas.sort(key=lambda e: -e[0])
report['top_deltas'] = deltas[:50]
report['spike_released'] = spike_log
# known-truth spot checks out of the patched scenes
truths = {}
for path, tag in (('scene_wide.json', 'wide'),):
    d = json.load(open(path))
    for b in d['buildings']:
        if b.get('name') in ('One Liberty Place', 'Two Liberty Place', 'Comcast Center',
                             'Comcast Technology Center', 'City Hall', 'Hopkinson House',
                             'Society Hill Towers', 'The Ryland', 'Dockside'):
            truths.setdefault(b['name'], []).append(b['h'])
report['known_truths_wide'] = truths
json.dump(report, open('lidar_report.json', 'w'), indent=1)
print('lidar_report.json written', flush=True)
