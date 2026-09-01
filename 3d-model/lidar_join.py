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

print('loading city footprints...', flush=True)
fpd = json.load(open('lidar_cache/phl_footprints_local.json'))['fps']
fp_geoms, fp_h = [], []
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
    fp_geoms.append(pg)
    fp_h.append(min(CLAMP_HI, h))
print(f'{len(fp_geoms)} usable footprints ({n_guard} dropped by contamination guard)', flush=True)
tree = STRtree(fp_geoms)

def measure(poly_pts, holes_pts=None):
    """poly in local meters -> (h, coverage) or (None, cov)."""
    try:
        pg = Polygon(poly_pts, holes_pts or None)
        if not pg.is_valid:
            pg = pg.buffer(0)
        if pg.is_empty or pg.area < 2:
            return None, 0.0
    except Exception:
        return None, 0.0
    idxs = tree.query(pg)
    if len(idxs) == 0:
        return None, 0.0
    inters = []
    for i in idxs:
        try:
            ia = pg.intersection(fp_geoms[i]).area
        except Exception:
            continue
        if ia > 0.5:
            inters.append((ia, fp_h[i]))
    if not inters:
        return None, 0.0
    tot = sum(ia for ia, _ in inters)
    cov = tot / pg.area
    if cov < COVER_MIN:
        return None, cov
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
    return max(CLAMP_LO, min(CLAMP_HI, wmean)), cov

report = {'footprints': len(fp_geoms), 'contamination_guard': n_guard, 'sets': {}}
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
        h, cov = measure(poly, b.get('holes'))
        if h is None:
            st['unmeasured'] += 1
            b['h'] = old
            continue
        # talls (>30 = explicitly tagged in practice) follow OSM's max-height tag
        # semantics: LiDAR may raise them (stale/low tags) but never lower them —
        # mixed tower+podium ways would otherwise read 30% short, and the two
        # known wrong-HIGH tags are hand-overridden in the app anyway
        if old > 30 and h < old:
            st['protected'] += 1
            b['h'] = old
            continue
        st['measured'] += 1
        b['h'] = round(h, 1)
        if abs(h - old) > 0.05:
            cx = sum(p[0] for p in poly) / len(poly)
            cz = sum(p[1] for p in poly) / len(poly)
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
    h, cov = measure(poly, b.get('holes'))
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
    h, cov = measure(pts)
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
