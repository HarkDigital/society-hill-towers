#!/usr/bin/env python3
"""LiDAR true-massing pass, stage 2 (core): process the 2022 QL1 point cloud over the
detailed core, derive per-building measured heights + roof forms, and patch scene.json.

Input:  lidar_cache/laz/*.copc.laz (NOAA 9848 tiles, EPSG:6347 UTM18N, NAVD88 m,
        leaf-off Apr 2022), lidar_cache/core_join.json (city-footprint fallback),
        scene.json.
Output: scene.json patched in place —
          b.h    : measured height (ridge for pitched, P90 parapet for flat)
          b.roof : [form, eave, ridge, ridgeRad]  form 1=gable 2=hip; [0] = measured
                   flat (suppresses the app's gable lottery). ridgeRad = angle of the
                   ridge line in the x-z plane (atan2(dz,dx), z south).
        lidar_report.json gains a 'core' section.

Method: 0.5 m grids of first-return min/max (class 2/7/9/18 excluded); a cell with
max-min > 4 m is canopy-contaminated (leaf-off branches) and dropped; roof surface =
per-cell MIN (tree-robust). Ground = 1 m mean of class 2/8. AGL percentiles per
eroded footprint; form via axial aspect statistics (R2 gable / R4 hip) on the
gradient of the roof grid. Alignment verified against the three towers by grid
cross-correlation before sampling. Run with the shapely venv python.
Frame: philly_frame.py (the scene's own projection). This script used to hardcode
KX=85350, a 6.9e-5 scale error (negligible over the 1.5 km core, up to ~1.1 m at
the far ring); the committed scene.json roof data keeps it until the next rerun."""
import json, math, os, sys, glob
import numpy as np
import laspy
import shapely
from shapely.geometry import Polygon
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
X0, X1, Z0, Z1 = -720.0, 800.0, -620.0, 950.0
C = 0.5                      # roof grid cell
GC = 1.0                     # ground grid cell
NX, NZ = int((X1 - X0) / C), int((Z1 - Z0) / C)
GNX, GNZ = int((X1 - X0) / GC), int((Z1 - Z0) / GC)
from philly_frame import LON0, LAT0, KX, KZ   # the one scene frame
UTM_BOX = (486880, 488470, 4420730, 4422370)   # padded core in EPSG:6347

GRIDS = 'lidar_cache/core_grids.npz'

def build_grids():
    fmin = np.full((NZ, NX), np.inf, np.float32)
    fmax = np.full((NZ, NX), -np.inf, np.float32)
    gsum = np.zeros((GNZ, GNX), np.float64)
    gcnt = np.zeros((GNZ, GNX), np.int32)
    tr = Transformer.from_crs('EPSG:6347', 'EPSG:4326', always_xy=True)
    for path in sorted(glob.glob('lidar_cache/laz/*.copc.laz')):
        f = laspy.open(path)
        n = 0
        for pts in f.chunk_iterator(4_000_000):
            n += len(pts.x)
            u = np.asarray(pts.x); v = np.asarray(pts.y); z = np.asarray(pts.z)
            m = (u >= UTM_BOX[0]) & (u <= UTM_BOX[1]) & (v >= UTM_BOX[2]) & (v <= UTM_BOX[3])
            m &= (z > -5) & (z < 250)
            if not m.any():
                continue
            u, v, z = u[m], v[m], z[m]
            cls = np.asarray(pts.classification)[m]
            rn = np.asarray(pts.return_number)[m]
            lon, lat = tr.transform(u, v)
            x = (lon - LON0) * KX
            zz = (LAT0 - lat) * KZ
            inb = (x >= X0) & (x < X1) & (zz >= Z0) & (zz < Z1)
            x, zz, z, cls, rn = x[inb], zz[inb], z[inb], cls[inb], rn[inb]
            # ground: class 2 (+8 model key points)
            gm = (cls == 2) | (cls == 8)
            if gm.any():
                gi = ((zz[gm] - Z0) / GC).astype(np.int32) * GNX + ((x[gm] - X0) / GC).astype(np.int32)
                np.add.at(gsum.ravel(), gi, z[gm])
                np.add.at(gcnt.ravel(), gi, 1)
            # roof surface: first returns, not ground/noise/water
            fm = (rn == 1) & ~gm & (cls != 7) & (cls != 9) & (cls != 18)
            if fm.any():
                fi = ((zz[fm] - Z0) / C).astype(np.int32) * NX + ((x[fm] - X0) / C).astype(np.int32)
                np.minimum.at(fmin.ravel(), fi, z[fm].astype(np.float32))
                np.maximum.at(fmax.ravel(), fi, z[fm].astype(np.float32))
        print(os.path.basename(path), f'{n} pts', flush=True)
    np.savez_compressed(GRIDS, fmin=fmin, fmax=fmax, gsum=gsum, gcnt=gcnt)

if not os.path.exists(GRIDS):
    build_grids()
d = np.load(GRIDS)
fmin, fmax, gsum, gcnt = d['fmin'], d['fmax'], d['gsum'], d['gcnt']
gmean = np.where(gcnt > 0, gsum / np.maximum(gcnt, 1), np.nan)
# canopy filter: bare-branch cells have a large first-return spread
roof = np.where((fmax - fmin) <= 4.0, fmin, np.nan)
roof[np.isinf(fmin)] = np.nan
print('roof cells: %.1f%% of grid' % (100 * np.mean(~np.isnan(roof))), flush=True)
if '--grids-only' in sys.argv:
    sys.exit(0)

scene = json.load(open('scene.json'))

def cell_centers(ix0, ix1, iz0, iz1):
    xs = X0 + (np.arange(ix0, ix1) + 0.5) * C
    zs = Z0 + (np.arange(iz0, iz1) + 0.5) * C
    return np.meshgrid(xs, zs)

def poly_cells(pg):
    """indices (iz, ix) of roof-grid cells whose centers fall inside pg."""
    minx, minz, maxx, maxz = pg.bounds
    ix0 = max(0, int((minx - X0) / C)); ix1 = min(NX, int((maxx - X0) / C) + 1)
    iz0 = max(0, int((minz - Z0) / C)); iz1 = min(NZ, int((maxz - Z0) / C) + 1)
    if ix1 <= ix0 or iz1 <= iz0:
        return None
    X, Z = cell_centers(ix0, ix1, iz0, iz1)
    inside = shapely.contains_xy(pg, X.ravel(), Z.ravel()).reshape(X.shape)
    iz, ix = np.nonzero(inside)
    return iz + iz0, ix + ix0

# ---- alignment check against the three towers (94 m cliffs, unmissable) ----
def tower_score(dx, dz):
    s = 0.0
    for t in scene['towers']:
        pg = Polygon(t['corners']).buffer(-1.5)
        cells = poly_cells(shapely.affinity.translate(pg, dx, dz))
        if cells is None:
            continue
        vals = roof[cells]
        vals = vals[~np.isnan(vals)]
        if len(vals):
            s += np.mean(vals > 60)
    return s
import shapely.affinity
best = (0.0, 0.0); best_s = tower_score(0, 0)
for dx in np.arange(-2, 2.01, 0.5):
    for dz in np.arange(-2, 2.01, 0.5):
        s = tower_score(dx, dz)
        if s > best_s + 1e-6:
            best_s, best = s, (dx, dz)
print(f'alignment: base score {tower_score(0,0):.3f}, best {best_s:.3f} at shift {best}', flush=True)
SHIFT = best if (abs(best[0]) + abs(best[1])) >= 0.5 and best_s > tower_score(0, 0) + 0.05 else (0.0, 0.0)
print('applied shift:', SHIFT, flush=True)

core_join = json.load(open('lidar_cache/core_join.json')) if os.path.exists('lidar_cache/core_join.json') else {}

def ground_level(pg):
    minx, minz, maxx, maxz = pg.bounds
    for pad in (10, 25, 60):
        gx0 = max(0, int((minx - pad - X0) / GC)); gx1 = min(GNX, int((maxx + pad - X0) / GC) + 1)
        gz0 = max(0, int((minz - pad - Z0) / GC)); gz1 = min(GNZ, int((maxz + pad - Z0) / GC) + 1)
        sub = gmean[gz0:gz1, gx0:gx1]
        vals = sub[~np.isnan(sub)]
        if len(vals) >= 8:
            return float(np.median(vals))
    return None

stats = {'total': 0, 'flat': 0, 'gable': 0, 'hip': 0, 'join_fallback': 0,
         'unmeasured': 0, 'skipped': 0, 'protected': 0}
examples = {}
deltas = []
for i, b in enumerate(scene['buildings']):
    poly = b.get('poly')
    if not poly or len(poly) < 3 or b.get('t') == 'ship' or b.get('minH'):
        stats['skipped'] += 1
        continue
    stats['total'] += 1
    old = b['h']
    try:
        pg = Polygon(poly)
        if not pg.is_valid:
            pg = pg.buffer(0)
        er = pg.buffer(-0.5)
        if er.is_empty:
            er = pg
        if er.geom_type == 'MultiPolygon':
            er = max(er.geoms, key=lambda g: g.area)
        er = shapely.affinity.translate(er, SHIFT[0], SHIFT[1])
        cells = poly_cells(er)
    except Exception:
        cells = None
    meas = None
    if cells is not None and len(cells[0]) >= 30:
        g0 = ground_level(pg)
        if g0 is not None:
            agl = roof[cells] - g0
            ok = ~np.isnan(agl)
            agl = agl[ok]
            agl = agl[agl > 1.6]      # wall-edge / yard cells
            if len(agl) >= 30:
                meas = agl, cells, ok
    if meas is None:
        cj = core_join.get(str(i))
        if cj is not None:
            stats['join_fallback'] += 1
            if not (old > 30 and cj < old):    # talls: raise-only (tag semantics)
                b['h'] = round(cj, 1)
                if abs(b['h'] - old) > 0.05:
                    deltas.append((round(abs(b['h'] - old), 1), b.get('name'), old, b['h'], 'join'))
        else:
            stats['unmeasured'] += 1
        continue
    agl, cells, okmask = meas
    p08, p50, p90, p95, p97 = np.percentile(agl, [8, 50, 90, 95, 97])
    relief = p95 - p08
    form = 0
    ridge_rad = 0.0
    eave = ridge = None
    if relief >= 1.15:
        # gradient of the roof grid over the building's cell set
        iz, ix = cells
        sub = np.full((iz.max() - iz.min() + 3, ix.max() - ix.min() + 3), np.nan, np.float32)
        sub[iz - iz.min() + 1, ix - ix.min() + 1] = roof[cells]
        gx = (sub[1:-1, 2:] - sub[1:-1, :-2]) / (2 * C)
        gz = (sub[2:, 1:-1] - sub[:-2, 1:-1]) / (2 * C)
        valid = ~np.isnan(gx) & ~np.isnan(gz)
        slope = np.hypot(gx, gz)
        rm = valid & (slope > 0.22) & (slope < 2.2)
        nroof = rm.sum()
        if nroof >= 20 and nroof >= 0.22 * valid.sum():
            th = np.arctan2(gz[rm], gx[rm])
            w = np.minimum(slope[rm], 1.2)
            v2 = np.abs(np.sum(w * np.exp(2j * th))) / np.sum(w)
            v4 = np.abs(np.sum(w * np.exp(4j * th))) / np.sum(w)
            mu2 = np.angle(np.sum(w * np.exp(2j * th))) / 2
            if v2 >= 0.5:
                form = 1
                ridge_rad = float((mu2 + math.pi / 2) % math.pi)
            elif v4 >= 0.5:
                form = 2
                mu4 = np.angle(np.sum(w * np.exp(4j * th))) / 4
                # pick the 90-deg-ambiguous axis closer to the footprint's long axis
                mrr = pg.minimum_rotated_rectangle
                cs = list(mrr.exterior.coords)
                e1 = math.hypot(cs[1][0] - cs[0][0], cs[1][1] - cs[0][1])
                e2 = math.hypot(cs[2][0] - cs[1][0], cs[2][1] - cs[1][1])
                la = math.atan2(cs[1][1] - cs[0][1], cs[1][0] - cs[0][0]) if e1 >= e2 \
                    else math.atan2(cs[2][1] - cs[1][1], cs[2][0] - cs[1][0])
                cand = [float((mu4 + k * math.pi / 2) % math.pi) for k in range(2)]
                ridge_rad = min(cand, key=lambda a: min(abs(a - la % math.pi), math.pi - abs(a - la % math.pi)))
            if form:
                eave, ridge = float(p08), float(p97)
                rise = ridge - eave
                if rise < 0.8 or rise > 8:
                    form = 0
    # talls (>30 = tagged) keep OSM's max-height semantics: measurement may raise,
    # never lower (mixed tower+podium footprints under-read in any percentile)
    if form:
        if old > 30 and ridge < old:
            stats['protected'] += 1
            b.pop('roof', None)
        else:
            stats['gable' if form == 1 else 'hip'] += 1
            b['h'] = round(ridge, 1)
            b['roof'] = [form, round(eave, 1), round(ridge, 1), round(ridge_rad, 3)]
    else:
        h = float(p90)
        if old > 30 and h < old:
            stats['protected'] += 1
            b.pop('roof', None)
        else:
            stats['flat'] += 1
            b['h'] = round(h, 1)
            b['roof'] = [0]
    if abs(b['h'] - old) > 0.05:
        deltas.append((round(abs(b['h'] - old), 1), b.get('name'), old, b['h'],
                       ['flat', 'gable', 'hip'][form]))
    if b.get('name') in ('Powel House', 'Head House', 'Man Full of Troubles Tavern',
                         'Athenaeum of Philadelphia', 'A Man Full of Trouble Tavern',
                         'Society Hill Synagogue', 'Old Pine Street Church'):
        examples[b['name']] = {'form': ['flat', 'gable', 'hip'][form], 'h': b['h'],
                               'eave': eave and round(eave, 1), 'ridge': ridge and round(ridge, 1)}

with open('scene.json.tmp', 'w') as _f:
    json.dump(scene, _f, separators=(',', ':'))
os.replace('scene.json.tmp', 'scene.json')
deltas.sort(key=lambda e: -e[0])
rep = json.load(open('lidar_report.json')) if os.path.exists('lidar_report.json') else {}
rep['core'] = {'stats': stats, 'shift': [float(SHIFT[0]), float(SHIFT[1])],
               'examples': examples, 'top_deltas': deltas[:40]}
json.dump(rep, open('lidar_report.json', 'w'), indent=1)
print(json.dumps(rep['core'], indent=1)[:3000], flush=True)
print('scene.json patched', flush=True)
