#!/usr/bin/env python3
"""LiDAR roof forms for the WHOLE city, streamed tile by tile through COPC's octree.

lidar_core.py measures roof forms over the 1.5 km core from full-resolution tiles on
disk (100+ pts/m2, 100-360 MB each). This is the same measurement for all 752 tiles of
the 2022 QL1 flight (NOAA Digital Coast dataset 9848, EPSG:6347 UTM 18N, NAVD88 m)
without downloading the 100 GB: each tile is a COPC LAZ on the public NOAA bucket
(https://noaa-nos-coastal-lidar-pds.s3.amazonaws.com/<key>), so HTTP range requests
pull only the coarse octree levels. Levels 0..2 of a standard 942 m tile (root spacing
6.41 m, finest level 1.6 m) are ~1.5-2.8 M points in 13-26 MB and take about a second;
level 3 (0.8 m) would triple the bytes and level 1 alone (3.2 m) cannot resolve a
4.5 m rowhouse, so 1.6 m it is (TARGET_SPACING). Octree nodes that hold no building
(river, parks, the airport) are not fetched at all.

Inputs:  lidar_cache/noaa_9848_index.json (tile keys, UTM bounds, sizes),
         osm_city_raw.json + osm_wide_raw.json + osm_south_raw.json (building ways),
         cached once as lidar_cache/roof_footprints.npz (UTM rings, 30..5000 m2).
Outputs: lidar_cache/roof_tiles/<tile>.json per tile (resumable: done tiles are skipped)
           {"tile", "stats", "b": {way id: [form, eave, ridge, ridgeRad, ncells]}}
         lidar_city_roofs.json (merged, forms 0/1/2 only, the packers' LUT)
           {"<way id>": [form, eave_m, ridge_m, ridgeRad]}
           form 0 flat (eave == ridge == P90 AGL, ridgeRad 0), 1 gable, 2 hip;
           ridgeRad = angle of the ridge line in the scene's x-z plane (atan2(dz,dx),
           x east, z south, philly_frame.py), same convention as lidar_core.py.

Method per tile (lidar_core's, adapted to the coarse grid): first returns not in
class 2/7/8/9/18 into a 1.5 m grid of per-cell MIN (tree-robust); a cell whose
first-return spread exceeds 4 m is leaf-off canopy and dropped; ground = 3 m mean of
class 2/8, per building the median within 10/25/60 m pads. AGL percentiles over the
cells whose centres fall in the footprint eroded by 1 m (>= 8 cells, else form -1
unresolved); flat when P90 - P10 < 1.0 m; else the gradient of the roof grid (central
differences inside the un-eroded footprint, one-sided at its edge so a 3-cell-wide
rowhouse still has a cross-slope) gives axial aspect statistics: R2 >= 0.5 gable
(two opposite aspects), else R4 >= 0.5 hip (four), ridge angle = dominant gradient
direction + 90 degrees, rotated into the model frame; eave = P10, ridge = P95, and a
rise outside 0.8..8 m falls back to flat. A building straddling tiles is measured in
each and the merge keeps the record with the most cells.

Usage:
  python3 fetch_lidar_roofs.py                 # all tiles (north of the core first), then merge
  python3 fetch_lidar_roofs.py --tiles 690,455 # just these tile numbers
  python3 fetch_lidar_roofs.py --limit 40      # stop after 40 new tiles
  python3 fetch_lidar_roofs.py --merge         # merge the per-tile files only
  python3 fetch_lidar_roofs.py --prep          # (re)build the footprint cache only
Needs the user-site laspy[lazrs], requests, pyproj and the system shapely (2.x)."""
import argparse, gc, json, math, os, sys, time, warnings
import numpy as np
warnings.filterwarnings('ignore')
import laspy
from laspy.copc import load_octree_for_query
import shapely
from shapely.geometry import Polygon
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
from philly_frame import to_xz   # the one scene frame

BASE = 'https://noaa-nos-coastal-lidar-pds.s3.amazonaws.com/'
INDEX = 'lidar_cache/noaa_9848_index.json'
FP_CACHE = 'lidar_cache/roof_footprints.npz'
TILE_DIR = 'lidar_cache/roof_tiles'
OUT = 'lidar_city_roofs.json'
RAW = ['osm_city_raw.json', 'osm_wide_raw.json', 'osm_south_raw.json']

C = 1.5                  # roof grid cell (m)
GC = 3.0                 # ground grid cell (m)
TARGET_SPACING = 1.8     # finest octree level fetched has spacing <= this (1.6 m on standard tiles)
AREA_MIN, AREA_MAX = 30.0, 5000.0
ERODE = 1.0
MIN_CELLS = 8
FLAT_SPREAD = 1.0        # P90 - P10 below this is flat
AGL_MIN = 1.6            # wall-edge / yard cells
CANOPY_SPREAD = 4.0      # first-return max - min above this is bare branches
CORE_NORTH = 4422370.0   # north edge of lidar_core's UTM box
HTTP_THREADS = 8
MERGE_FIRST, MERGE_EVERY = 40, 100

FWD = Transformer.from_crs('EPSG:4326', 'EPSG:6347', always_xy=True)
INV = Transformer.from_crs('EPSG:6347', 'EPSG:4326', always_xy=True)


def log(*a):
    print(*a, flush=True)


# ---- footprints -------------------------------------------------------------------
def build_footprints():
    """Building ways of the three OSM raw dumps -> UTM rings in one npz."""
    ids, lons, lats, offs = [], [], [], [0]
    seen = set()
    for path in RAW:
        if not os.path.exists(path):
            log(f'  {path}: missing, skipped')
            continue
        t0 = time.time()
        d = json.load(open(path))
        els = d['elements']
        nodes = {}
        for e in els:
            if e['type'] == 'node':
                nodes[e['id']] = (e['lon'], e['lat'])
        n_way = n_keep = 0
        for e in els:
            if e['type'] != 'way':
                continue
            n_way += 1
            t = e.get('tags')
            if not t or 'building' not in t or t['building'] == 'no':
                continue
            nd = e['nodes']
            if len(nd) < 4 or nd[0] != nd[-1] or e['id'] in seen:
                continue
            try:
                ll = [nodes[i] for i in nd]
            except KeyError:
                continue
            seen.add(e['id'])
            ids.append(e['id'])
            lons.extend(p[0] for p in ll)
            lats.extend(p[1] for p in ll)
            offs.append(len(lons))
            n_keep += 1
        log(f'  {path}: {n_way} ways, {n_keep} new building rings, {time.time() - t0:.0f}s')
        del d, els, nodes
        gc.collect()
    ids = np.asarray(ids, np.int64)
    offs = np.asarray(offs, np.int64)
    E, N = FWD.transform(np.asarray(lons, np.float64), np.asarray(lats, np.float64))
    del lons, lats
    # shoelace area + bbox per ring, vectorised over the flat arrays
    E = np.asarray(E, np.float64); N = np.asarray(N, np.float64)
    nb = len(ids)
    area = np.zeros(nb); bbox = np.zeros((nb, 4))
    for j in range(nb):
        a, b = offs[j], offs[j + 1]
        x, y = E[a:b], N[a:b]
        area[j] = 0.5 * abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))
        bbox[j] = (x.min(), x.max(), y.min(), y.max())
    keep = (area >= AREA_MIN) & (area <= AREA_MAX)
    # compact the kept rings
    kidx = np.nonzero(keep)[0]
    lens = offs[1:] - offs[:-1]
    new_offs = np.concatenate([[0], np.cumsum(lens[kidx])])
    sel = np.concatenate([np.arange(offs[j], offs[j + 1]) for j in kidx]) if len(kidx) else np.zeros(0, np.int64)
    np.savez_compressed(FP_CACHE, ids=ids[kidx], offs=new_offs, E=E[sel], N=N[sel],
                        area=area[kidx], bbox=bbox[kidx])
    log(f'footprints: {nb} building rings, {len(kidx)} within {AREA_MIN:.0f}..{AREA_MAX:.0f} m2 -> {FP_CACHE}')


def load_footprints():
    if not os.path.exists(FP_CACHE):
        log('building the footprint cache (loads the 450 MB city dump once)...')
        build_footprints()
    d = np.load(FP_CACHE)
    fp = {k: d[k] for k in ('ids', 'offs', 'E', 'N', 'area', 'bbox')}
    log(f'footprints: {len(fp["ids"])} buildings from {FP_CACHE}')
    return fp


# ---- tiles ------------------------------------------------------------------------
def tile_name(key):
    return os.path.basename(key).replace('.copc.laz', '')


def tile_order(index, only=None):
    """North of the core first (northernmost first: the far Northeast, Chestnut Hill,
    Mount Airy, Roxborough), then the rest, also north to south."""
    items = list(index['bounds'].items())
    if only:
        items = [(k, b) for k, b in items if tile_name(k).rsplit('_', 1)[-1] in only]
    north = [(k, b) for k, b in items if b[2] >= CORE_NORTH]
    rest = [(k, b) for k, b in items if b[2] < CORE_NORTH]
    north.sort(key=lambda kb: -kb[1][2])
    rest.sort(key=lambda kb: -kb[1][2])
    return north + rest


def choose_levels(spacing):
    L = 1
    while spacing / 2 ** (L - 1) > TARGET_SPACING:
        L += 1
    return L


def frame_rotation(e0, n0):
    """Angle (rad) of the UTM east axis in the model frame's (x east, z south) plane."""
    lon0, lat0 = INV.transform(e0, n0)
    lon1, lat1 = INV.transform(e0 + 100.0, n0)
    x0, z0 = to_xz(lat0, lon0)
    x1, z1 = to_xz(lat1, lon1)
    return math.atan2(z1 - z0, x1 - x0)


def grad_axis(sub, axis):
    """Gradient along an axis of a NaN-padded grid: central where both neighbours are
    valid, else one-sided, so edge cells of a narrow building still get a slope."""
    p = np.pad(sub, 1, constant_values=np.nan)
    if axis == 1:
        left, right = p[1:-1, :-2], p[1:-1, 2:]
    else:
        left, right = p[:-2, 1:-1], p[2:, 1:-1]
    g = (right - left) / (2 * C)
    gf = (right - sub) / C
    gb = (sub - left) / C
    return np.where(np.isnan(g), np.where(~np.isnan(gf), gf, gb), g)


def long_axis(pg):
    """Angle of the footprint's long axis in the (east, south) plane."""
    cs = list(pg.minimum_rotated_rectangle.exterior.coords)
    if len(cs) < 3:
        return 0.0
    e1 = math.hypot(cs[1][0] - cs[0][0], cs[1][1] - cs[0][1])
    e2 = math.hypot(cs[2][0] - cs[1][0], cs[2][1] - cs[1][1])
    if e1 >= e2:
        return math.atan2(-(cs[1][1] - cs[0][1]), cs[1][0] - cs[0][0])
    return math.atan2(-(cs[2][1] - cs[1][1]), cs[2][0] - cs[1][0])


def measure(pg, roof, gmean, minx, maxy, NX, NZ, GNX, GNZ, rot):
    """One building -> [form, eave, ridge, ridgeRad(model), ncells]. form -1 = unresolved."""
    er = pg.buffer(-ERODE)
    if er.is_empty:
        return [-1, 0, 0, 0, 0]
    if er.geom_type == 'MultiPolygon':
        er = max(er.geoms, key=lambda g: g.area)
    bx0, by0, bx1, by1 = pg.bounds
    ix0 = max(0, int((bx0 - minx) / C)); ix1 = min(NX, int((bx1 - minx) / C) + 1)
    iz0 = max(0, int((maxy - by1) / C)); iz1 = min(NZ, int((maxy - by0) / C) + 1)
    if ix1 <= ix0 or iz1 <= iz0:
        return [-1, 0, 0, 0, 0]
    xs = minx + (np.arange(ix0, ix1) + 0.5) * C
    ys = maxy - (np.arange(iz0, iz1) + 0.5) * C
    X, Y = np.meshgrid(xs, ys)
    inA = shapely.contains_xy(pg, X.ravel(), Y.ravel()).reshape(X.shape)
    inE = shapely.contains_xy(er, X.ravel(), Y.ravel()).reshape(X.shape)
    sub = np.where(inA, roof[iz0:iz1, ix0:ix1], np.nan)
    # ground: median of the 3 m ground grid within widening pads
    g0 = None
    for pad in (10, 25, 60):
        cx0 = max(0, int((bx0 - pad - minx) / GC)); cx1 = min(GNX, int((bx1 + pad - minx) / GC) + 1)
        cz0 = max(0, int((maxy - by1 - pad) / GC)); cz1 = min(GNZ, int((maxy - by0 + pad) / GC) + 1)
        gs = gmean[cz0:cz1, cx0:cx1]
        gv = gs[~np.isnan(gs)]
        if len(gv) >= 8:
            g0 = float(np.median(gv))
            break
    if g0 is None:
        return [-1, 0, 0, 0, 0]
    agl = sub - g0
    okE = inE & ~np.isnan(agl) & (agl > AGL_MIN)
    n = int(okE.sum())
    if n < MIN_CELLS:
        return [-1, 0, 0, 0, n]
    vals = agl[okE]
    p10, p90, p95 = np.percentile(vals, [10, 90, 95])
    if p90 - p10 < FLAT_SPREAD:
        h = round(float(p90), 1)
        return [0, h, h, 0.0, n]
    # pitched? gradient over the building's own cells, evaluated at the eroded ones
    gx = grad_axis(sub, 1)          # d/d east
    gz = grad_axis(sub, 0)          # d/d south (row 0 is the tile's north edge)
    valid = okE & ~np.isnan(gx) & ~np.isnan(gz)
    slope = np.hypot(gx, gz)
    rm = valid & (slope > 0.22) & (slope < 2.2)
    nroof = int(rm.sum())
    form, ridge_rad = 0, 0.0
    if nroof >= 6 and nroof >= 0.22 * valid.sum():
        th = np.arctan2(gz[rm], gx[rm])
        w = np.minimum(slope[rm], 1.2)
        s2 = np.sum(w * np.exp(2j * th)); s4 = np.sum(w * np.exp(4j * th))
        v2 = abs(s2) / np.sum(w); v4 = abs(s4) / np.sum(w)
        if v2 >= 0.5:
            form = 1
            ridge_rad = (np.angle(s2) / 2 + math.pi / 2) % math.pi
        elif v4 >= 0.5:
            form = 2
            mu4 = np.angle(s4) / 4
            la = long_axis(pg) % math.pi
            cand = [(mu4 + k * math.pi / 2) % math.pi for k in range(2)]
            ridge_rad = min(cand, key=lambda a: min(abs(a - la), math.pi - abs(a - la)))
    if form:
        rise = float(p95 - p10)
        if 0.8 <= rise <= 8.0:
            return [form, round(float(p10), 1), round(float(p95), 1),
                    round(float((ridge_rad + rot) % math.pi), 3), n]
    h = round(float(p90), 1)
    return [0, h, h, 0.0, n]


def process_tile(key, bounds, fp, sel):
    """Stream one tile's coarse octree levels, grid it, measure every building in sel."""
    name = tile_name(key)
    minx, maxx, miny, maxy = bounds[:4]
    t0 = time.time()
    rd = laspy.CopcReader.open(BASE + key, http_num_threads=HTTP_THREADS)
    L = choose_levels(rd.copc_info.spacing)
    nodes = load_octree_for_query(rd.source, rd.copc_info, rd.root_page, None, range(0, L))
    # only nodes that hold a building (plus the ground pads around it)
    bb = fp['bbox'][sel]
    pad = 60.0
    keep = []
    for nd in nodes:
        mn, mx = nd.bounds.mins, nd.bounds.maxs
        hit = (bb[:, 0] <= mx[0] + pad) & (bb[:, 1] >= mn[0] - pad) & \
              (bb[:, 2] <= mx[1] + pad) & (bb[:, 3] >= mn[1] - pad)
        if hit.any():
            keep.append(nd)
    mb = sum(nd.byte_size for nd in keep) / 1e6
    pts = rd._fetch_and_decompress_points_of_nodes(keep)
    npts = len(pts)
    x = np.asarray(pts.x); y = np.asarray(pts.y); z = np.asarray(pts.z)
    cls = np.asarray(pts.classification); rn = np.asarray(pts.return_number)
    del pts
    try:
        rd.source.close()
    except Exception:
        pass
    t_dl = time.time() - t0
    m = (x >= minx) & (x < maxx) & (y > miny) & (y <= maxy) & (z > -5) & (z < 250)
    x, y, z, cls, rn = x[m], y[m], z[m], cls[m], rn[m]
    NX = int(math.ceil((maxx - minx) / C)); NZ = int(math.ceil((maxy - miny) / C))
    GNX = int(math.ceil((maxx - minx) / GC)); GNZ = int(math.ceil((maxy - miny) / GC))
    gm = (cls == 2) | (cls == 8)
    gsum = np.zeros(GNZ * GNX, np.float64); gcnt = np.zeros(GNZ * GNX, np.int32)
    if gm.any():
        gi = np.minimum(GNZ - 1, ((maxy - y[gm]) / GC).astype(np.int32)) * GNX + \
             np.minimum(GNX - 1, ((x[gm] - minx) / GC).astype(np.int32))
        np.add.at(gsum, gi, z[gm]); np.add.at(gcnt, gi, 1)
    gmean = np.where(gcnt > 0, gsum / np.maximum(gcnt, 1), np.nan).reshape(GNZ, GNX)
    fm = (rn == 1) & ~gm & (cls != 7) & (cls != 9) & (cls != 18)
    fmin = np.full(NZ * NX, np.inf, np.float32); fmax = np.full(NZ * NX, -np.inf, np.float32)
    if fm.any():
        fi = np.minimum(NZ - 1, ((maxy - y[fm]) / C).astype(np.int32)) * NX + \
             np.minimum(NX - 1, ((x[fm] - minx) / C).astype(np.int32))
        zf = z[fm].astype(np.float32)
        np.minimum.at(fmin, fi, zf); np.maximum.at(fmax, fi, zf)
    roof = np.where((fmax - fmin) <= CANOPY_SPREAD, fmin, np.nan).reshape(NZ, NX)
    roof[np.isinf(fmin).reshape(NZ, NX)] = np.nan
    del x, y, z, cls, rn, gm, fm, gsum, gcnt, fmin, fmax
    rot = frame_rotation((minx + maxx) / 2, (miny + maxy) / 2)
    out = {}
    st = {'buildings': int(len(sel)), 'resolved': 0, 'gable': 0, 'hip': 0, 'flat': 0, 'unresolved': 0}
    E, N, offs = fp['E'], fp['N'], fp['offs']
    for j in sel:
        wid = int(fp['ids'][j])
        a, b = offs[j], offs[j + 1]
        try:
            pg = Polygon(np.column_stack([E[a:b], N[a:b]]))
            if not pg.is_valid:
                pg = pg.buffer(0)
                if pg.geom_type == 'MultiPolygon':
                    pg = max(pg.geoms, key=lambda g: g.area)
            if pg.is_empty or pg.geom_type != 'Polygon':
                raise ValueError('bad ring')
            r = measure(pg, roof, gmean, minx, maxy, NX, NZ, GNX, GNZ, rot)
        except Exception:
            r = [-1, 0, 0, 0, 0]
        out[str(wid)] = r
        if r[0] < 0:
            st['unresolved'] += 1
        else:
            st['resolved'] += 1
            st[('flat', 'gable', 'hip')[r[0]]] += 1
    dt = time.time() - t0
    st.update({'points': int(npts), 'mb': round(mb, 1), 'levels': L,
               'spacing': round(rd.copc_info.spacing / 2 ** (L - 1), 2),
               'nodes': len(keep), 'download_s': round(t_dl, 1), 'secs': round(dt, 1)})
    tmp = f'{TILE_DIR}/{name}.json.tmp'
    with open(tmp, 'w') as f:
        json.dump({'tile': name, 'key': key, 'bounds': bounds[:4], 'stats': st, 'b': out}, f, separators=(',', ':'))
    os.replace(tmp, f'{TILE_DIR}/{name}.json')
    del roof, gmean
    gc.collect()
    log(f'{name} pts {npts} {mb:.1f} MB bld {st["resolved"]}/{st["buildings"]} '
        f'gable {st["gable"]} hip {st["hip"]} flat {st["flat"]} {dt:.1f}s')
    return st


def write_empty_tile(key, bounds):
    name = tile_name(key)
    st = {'buildings': 0, 'resolved': 0, 'gable': 0, 'hip': 0, 'flat': 0, 'unresolved': 0,
          'points': 0, 'mb': 0.0, 'secs': 0.0}
    with open(f'{TILE_DIR}/{name}.json', 'w') as f:
        json.dump({'tile': name, 'key': key, 'bounds': bounds[:4], 'stats': st, 'b': {}}, f)
    log(f'{name} no buildings, skipped')


# ---- merge ------------------------------------------------------------------------
def merge():
    best = {}
    files = sorted(f for f in os.listdir(TILE_DIR) if f.endswith('.json')) if os.path.isdir(TILE_DIR) else []
    for fn in files:
        d = json.load(open(f'{TILE_DIR}/{fn}'))
        for wid, r in d['b'].items():
            if r[0] not in (0, 1, 2):
                continue
            cur = best.get(wid)
            if cur is None or r[4] > cur[4]:
                best[wid] = r
    out = {wid: [r[0], r[1], r[2], r[3]] for wid, r in best.items()}
    tmp = OUT + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(tmp, OUT)
    forms = [0, 0, 0]
    for r in out.values():
        forms[r[0]] += 1
    log(f'merged {len(files)} tiles -> {OUT}: {len(out)} buildings, '
        f'flat {forms[0]} gable {forms[1]} hip {forms[2]}')
    return len(out)


# ---- main -------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description='city-wide LiDAR roof forms streamed from COPC tiles')
    ap.add_argument('--merge', action='store_true', help='merge the per-tile files and exit')
    ap.add_argument('--prep', action='store_true', help='(re)build the footprint cache and exit')
    ap.add_argument('--tiles', help='comma-separated tile numbers to process (e.g. 690,455)')
    ap.add_argument('--limit', type=int, default=0, help='stop after this many new tiles')
    ap.add_argument('--force', action='store_true', help='redo tiles that already have a file')
    args = ap.parse_args()
    os.makedirs(TILE_DIR, exist_ok=True)
    if args.merge:
        merge()
        return
    if args.prep:
        build_footprints()
        return
    index = json.load(open(INDEX))
    fp = load_footprints()
    bb = fp['bbox']
    only = set(args.tiles.split(',')) if args.tiles else None
    order = tile_order(index, only)
    done = {f[:-5] for f in os.listdir(TILE_DIR) if f.endswith('.json')}
    todo = [(k, b) for k, b in order if args.force or tile_name(k) not in done]
    log(f'{len(order)} tiles, {len(order) - len(todo)} already done, {len(todo)} to go')
    n_new = 0
    merged_at = -1
    t_start = time.time()
    tot = {'points': 0, 'mb': 0.0, 'resolved': 0, 'gable': 0, 'hip': 0, 'flat': 0}
    for k, b in todo:
        minx, maxx, miny, maxy = b[:4]
        sel = np.nonzero((bb[:, 0] <= maxx) & (bb[:, 1] >= minx) & (bb[:, 2] <= maxy) & (bb[:, 3] >= miny))[0]
        if len(sel) == 0:
            write_empty_tile(k, b)
        else:
            st = None
            for attempt in range(3):
                try:
                    st = process_tile(k, b, fp, sel)
                    break
                except Exception as ex:
                    log(f'{tile_name(k)} attempt {attempt + 1} failed: {ex!r}')
                    time.sleep(5 * (attempt + 1))
            if st is None:
                log(f'{tile_name(k)} GIVING UP for now (rerun to retry)')
                continue
            for kk in tot:
                tot[kk] += st.get(kk, 0)
        n_new += 1
        n_done = len(done) + n_new
        if (n_done >= MERGE_FIRST and merged_at < 0) or (merged_at >= 0 and n_done - merged_at >= MERGE_EVERY):
            merge()
            merged_at = n_done
        if args.limit and n_new >= args.limit:
            break
    el = time.time() - t_start
    log(f'run: {n_new} tiles in {el / 60:.1f} min, {tot["points"]} points, {tot["mb"]:.0f} MB streamed, '
        f'{tot["resolved"]} buildings resolved (gable {tot["gable"]} hip {tot["hip"]} flat {tot["flat"]})')
    if n_new:
        merge()


if __name__ == '__main__':
    main()
