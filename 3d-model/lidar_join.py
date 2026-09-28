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
Frame: philly_frame.py (the scene's own projection). This script used to hardcode
KX=85350, which put the city footprints up to ~1.1 m east of the far-ring ways
they were overlapped with (a few % of coverage on narrow rowhouses); the committed
lidar_city_heights.json and the patched scenes keep that until the next rerun.
Run with the shapely venv python."""
import json, math, os, sys
from shapely.geometry import Polygon
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

def flat_roof_ways():
    """{way id: (scene-frame Polygon, P90 AGL m)} for every OSM building way the citywide LiDAR roof pass
    (lidar_city_roofs.json, fetch_lidar_roofs.py) measured flat: P90 - P10 under 1 m over its cells, or a level
    roof with bulkheads. Polygons from whichever OSM raws are on disk (the pass's own rings are UTM)."""
    roofs = json.load(open('lidar_city_roofs.json')) if os.path.exists('lidar_city_roofs.json') else {}
    flat = {int(k): v[2] for k, v in roofs.items() if v[0] == 0}
    out = {}
    for f in ('osm_wide_raw.json', 'osm_south_raw.json', 'osm_city_raw.json'):
        if not os.path.exists(f):
            continue
        els = json.load(open(f))['elements']
        nodes = {e['id']: (e['lon'], e['lat']) for e in els if e.get('type') == 'node'}
        for e in els:
            if e.get('type') != 'way' or e['id'] not in flat or e['id'] in out:
                continue
            g = e.get('geometry')
            pts = ([((q['lon'] - LON0) * KX, (LAT0 - q['lat']) * KZ) for q in g] if g else
                   [((nodes[n][0] - LON0) * KX, (LAT0 - nodes[n][1]) * KZ) for n in e.get('nodes', []) if n in nodes])
            if len(pts) < 4:
                continue
            try:
                pg = Polygon(pts).buffer(0)
            except Exception:
                continue
            if pg.area > 20:
                out[e['id']] = (pg, flat[e['id']])
        del els, nodes
    return out

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
_flat = list(flat_roof_ways().values())
flat_tree = STRtree([w[0] for w in _flat])
print(f'{len(_flat)} flat-roofed ways', flush=True)

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
    for b, b0 in zip(cb, sb):
        poly = b.get('poly')
        if not poly or len(poly) < 3 or b.get('t') in SKIP_T or b.get('minH'):
            st['skipped'] += 1
            continue
        st['total'] += 1
        old = b0['h']          # the ORIGINAL OSM value from the snapshot, never our own previous output
        worship = b.get('t') == WORSHIP_T
        h, cov, touched = measure(poly, b.get('holes'), use_max=worship)
        if h is None:
            st['unmeasured'] += 1
            b['h'] = old
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
