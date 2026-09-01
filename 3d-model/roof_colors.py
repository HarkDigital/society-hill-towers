#!/usr/bin/env python3
"""Tier-1 facade pass, stage 2: sample every model building's roof color from the
City of Philadelphia 2024 3-inch orthophoto tile cache (public ArcGIS Online
service), at zoom 17 (~0.92 m/px here).

Per building: median RGB of tile pixels inside the footprint eroded 0.8 m
(median rides over overhanging branches; the flight is leaf-off). All medians
are k-means clustered to a 30-color palette; buildings store a palette index.

Outputs: lidar_cache/roof_palette.json  [[r,g,b] x30]
         lidar_cache/roof_core.json / roof_wide.json / roof_south.json {idx: pal}
         lidar_cache/roof_city.json {way id: pal}
Tiles cached in lidar_cache/tiles/. Run with the venv python (shapely, PIL, numpy).
Frame: philly_frame.py (the scene's own projection). This script used to hardcode
KX=85350, which sampled the ortho up to ~1.1 m (about one pixel) east of each far-
ring footprint; the cached roof_*.json keep that until the next rerun."""
import io, json, math, os, sys, time, urllib.request
from collections import OrderedDict
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
TILE_DIR = 'lidar_cache/tiles'
os.makedirs(TILE_DIR, exist_ok=True)
from philly_frame import LON0, LAT0, KX, KZ   # the one scene frame
Z = 17
WORLD = 256 * (1 << Z)
URL = ('https://tiles.arcgis.com/tiles/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
       'CityImagery_2024_3in/MapServer/tile/%d/%d/%d')

def to_px(x, z):
    lon = LON0 + x / KX
    lat = LAT0 - z / KZ
    px = (lon + 180.0) / 360.0 * WORLD
    la = math.radians(lat)
    py = (1.0 - math.log(math.tan(la) + 1.0 / math.cos(la)) / math.pi) / 2.0 * WORLD
    return px, py

_cache = OrderedDict()
_stats = {'net': 0, 'disk': 0, 'miss': 0}

def tile(tx, ty):
    key = (tx, ty)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    path = os.path.join(TILE_DIR, f'{tx}_{ty}.jpg')
    data = None
    if os.path.exists(path) and os.path.getsize(path) > 0:
        data = open(path, 'rb').read()
        _stats['disk'] += 1
    else:
        for attempt in range(4):
            try:
                with urllib.request.urlopen(URL % (Z, ty, tx), timeout=60) as r:
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code in (404, 422):    # outside the cache = outside the city
                    data = b''
                    break
                time.sleep(2 + 2 * attempt)
            except Exception:
                time.sleep(2 + 2 * attempt)
        if data is None:
            data = b''
        with open(path, 'wb') as f:
            f.write(data)
        _stats['net'] += 1
    if not data:
        arr = None
        _stats['miss'] += 1
    else:
        try:
            arr = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))
        except Exception:
            arr = None
    _cache[key] = arr
    if len(_cache) > 1400:
        _cache.popitem(last=False)
    return arr

def sample(poly_pts):
    """median RGB inside the footprint (local-meter ring), or None."""
    try:
        pg = Polygon(poly_pts)
        if not pg.is_valid:
            pg = pg.buffer(0)
        er = pg.buffer(-0.8)
        if er.is_empty:
            er = pg
        if er.geom_type == 'MultiPolygon':
            er = max(er.geoms, key=lambda g: g.area)
        ring = list(er.exterior.coords)
    except Exception:
        return None
    px = [to_px(x, z) for x, z in ring]
    xs = [p[0] for p in px]; ys = [p[1] for p in px]
    x0, x1 = int(min(xs)), int(max(xs)) + 1
    y0, y1 = int(min(ys)), int(max(ys)) + 1
    if x1 - x0 < 2 or y1 - y0 < 2 or x1 - x0 > 3000 or y1 - y0 > 3000:
        return None
    tx0, tx1 = x0 // 256, (x1 - 1) // 256
    ty0, ty1 = y0 // 256, (y1 - 1) // 256
    w, h = x1 - x0, y1 - y0
    mos = np.zeros((h, w, 3), np.uint8)
    have = np.zeros((h, w), bool)
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            arr = tile(tx, ty)
            if arr is None:
                continue
            gx0, gy0 = tx * 256, ty * 256
            sx0 = max(x0, gx0); sx1 = min(x1, gx0 + 256)
            sy0 = max(y0, gy0); sy1 = min(y1, gy0 + 256)
            if sx1 <= sx0 or sy1 <= sy0:
                continue
            mos[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = arr[sy0 - gy0:sy1 - gy0, sx0 - gx0:sx1 - gx0]
            have[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = True
    m = Image.new('1', (w, h), 0)
    ImageDraw.Draw(m).polygon([(p[0] - x0, p[1] - y0) for p in px], fill=1)
    mask = np.asarray(m, bool) & have
    if mask.sum() < 8:
        return None
    sel = mos[mask]
    return [int(v) for v in np.median(sel, axis=0)]

# ---------------- targets ----------------
jobs = []   # (set, key, poly, centroid tile for locality sort)
def add(setname, key, pts):
    if len(pts) < 3:
        return
    cx = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    px, py = to_px(cx, cz)
    jobs.append((setname, key, pts, (int(py // 256), int(px // 256))))

core = json.load(open('scene.json'))
for i, b in enumerate(core['buildings']):
    if b.get('poly') and b.get('t') != 'ship':
        add('core', i, b['poly'])
for name, path in (('wide', 'scene_wide.json'), ('south', 'scene_south.json')):
    d = json.load(open(path))
    for i, b in enumerate(d['buildings']):
        if b.get('poly') and b.get('t') not in ('ship', 'stadium', 'arena'):
            add(name, i, b['poly'])
print('loading osm_city_raw.json...', flush=True)
raw = json.load(open('osm_city_raw.json'))
nodes = {}
for el in raw['elements']:
    if el.get('type') == 'node':
        nodes[el['id']] = ((el['lon'] - LON0) * KX, (LAT0 - el['lat']) * KZ)
for el in raw['elements']:
    if el.get('type') != 'way' or 'building' not in (el.get('tags') or {}):
        continue
    pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    add('city', el['id'], pts)
del raw, nodes
jobs.sort(key=lambda j: j[3])
print(f'{len(jobs)} footprints to sample', flush=True)

results = {'core': {}, 'wide': {}, 'south': {}, 'city': {}}
colors = []
t0 = time.time()
for n, (setname, key, pts, _) in enumerate(jobs):
    c = sample(pts)
    if c is not None:
        results[setname][str(key)] = len(colors)
        colors.append(c)
    if n % 20000 == 0:
        print(f'{n}/{len(jobs)} sampled ({time.time()-t0:.0f}s, tiles net {_stats["net"]} disk {_stats["disk"]} miss {_stats["miss"]})', flush=True)
print(f'sampled {len(colors)}/{len(jobs)} ({time.time()-t0:.0f}s)', flush=True)

# ---------------- 30-color palette (k-means) ----------------
X = np.array(colors, np.float32)
sub = X[np.random.default_rng(7).choice(len(X), min(60000, len(X)), replace=False)]
k = 30
cent = sub[np.random.default_rng(3).choice(len(sub), k, replace=False)]
for it in range(14):
    d2 = ((sub[:, None, :] - cent[None, :, :]) ** 2).sum(2)
    lab = d2.argmin(1)
    for j in range(k):
        m = lab == j
        if m.any():
            cent[j] = sub[m].mean(0)
d2 = ((X[:, None, :] - cent[None, :, :]) ** 2).sum(2)
lab_all = d2.argmin(1)
pal = [[int(round(v)) for v in c] for c in cent]
for setname in results:
    results[setname] = {kk: int(lab_all[v]) for kk, v in results[setname].items()}
json.dump(pal, open('lidar_cache/roof_palette.json', 'w'))
for setname, r in results.items():
    json.dump(r, open(f'lidar_cache/roof_{setname}.json', 'w'), separators=(',', ':'))
    print(f'roof_{setname}.json: {len(r)}', flush=True)
counts = np.bincount(lab_all, minlength=k)
print('palette:', [(pal[i], int(counts[i])) for i in np.argsort(-counts)[:10]], flush=True)
print('done', flush=True)
