#!/usr/bin/env python3
"""Tier-1 facade pass, stage 1: join OPA parcel attributes (era, material, use,
stories) onto every model building.

OPA rows (lidar_cache/opa_rows.csv, 583k) are collapsed to SITES by rounded
lat/lng (condo units share a point: stories=max, year=min, use/mat=modal), then
each site is assigned to the model footprint that contains it (or the nearest
within 12 m). Buildings aggregate their sites modally.

Codes (packed later as use(3)|mat(3)|era(4)|stories(6)):
  use: 0 rowhouse/twin  1 detached res  2 apartments/condo  3 store+dwelling/mixed
       4 commercial/office/hotel  5 industrial/garage  6 civic/institutional  7 unknown
  mat: 0 masonry/brick  1 frame  2 stone  3 mixed/other  4 unknown
  era: 0 <1800  1 <1860  2 <1900  3 <1935  4 <1965  5 <1990  6 <2010  7 >=2010  8 unknown

Outputs: lidar_cache/opa_core.json {scene idx: [u,m,e,s]},
         lidar_cache/opa_wide.json, lidar_cache/opa_south.json (scene idx),
         lidar_cache/opa_city.json {way id: [u,m,e,s]}, stats into lidar_report.json.
Run with the shapely venv python."""
import csv, json, math, os, sys
from collections import Counter, defaultdict
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
LON0, LAT0, KX, KZ = -75.144748, 39.945474, 85350.0, 110574.0

# ---------------- OPA rows -> sites ----------------
def era_of(year, desc_new):
    if year:
        for i, cut in enumerate((1800, 1860, 1900, 1935, 1965, 1990, 2010)):
            if year < cut:
                return i
        return 7
    d = desc_new or ''
    if 'OLD STYLE' in d: return 2
    if 'POST WAR' in d: return 4
    if 'MODERN' in d or 'CONTEMPORARY' in d: return 6
    return 8

def use_of(cat, desc):
    c, d = cat or '', desc or ''
    if c.startswith('VACANT'): return None
    if 'MIXED USE' in c: return 3
    if c in ('SINGLE FAMILY', 'MULTI FAMILY'):
        if 'APT' in d or 'CONDO' in d: return 2
        if 'DET' in d and 'ROW' not in d: return 1
        return 0
    if 'APARTMENT' in c or 'CONDO' in c: return 2
    if 'INDUSTRIAL' in c or 'GARAGE' in c: return 5
    if c in ('COMMERCIAL', 'OFFICES', 'HOTELS AND APARTMENTS', 'RETAIL'):
        if 'DWELL' in d: return 3
        return 4
    if 'STORE' in c: return 4
    return 6

def mat_of(desc, cat):
    d = desc or ''
    has_m = 'MASONRY' in d or 'MAS' in d
    has_f = 'FRAME' in d
    if has_m and has_f: return 3
    if has_m: return 0
    if has_f: return 1
    if 'STONE' in d: return 2
    if 'METAL' in d or 'STEEL' in d: return 3
    if (cat or '').startswith('INDUSTRIAL'): return 3
    return 4

sites = {}
n_rows = n_skip = 0
for r in csv.DictReader(open('lidar_cache/opa_rows.csv')):
    n_rows += 1
    try:
        lat = float(r['lat']); lng = float(r['lng'])
    except (TypeError, ValueError):
        n_skip += 1
        continue
    u = use_of(r['category_code_description'], r['building_code_description'])
    if u is None:
        n_skip += 1
        continue
    try:
        st = int(float(r['number_stories'] or 0))
    except ValueError:
        st = 0
    if not (1 <= st <= 60):
        st = 0
    try:
        yr = int(float(r['year_built'] or 0))
    except ValueError:
        yr = 0
    if not (1600 <= yr <= 2026):
        yr = 0
    key = (round(lat, 5), round(lng, 5))
    s = sites.get(key)
    if s is None:
        sites[key] = s = {'st': 0, 'yr': 9999, 'u': Counter(), 'm': Counter(), 'dn': Counter()}
    s['st'] = max(s['st'], st)
    if yr:
        s['yr'] = min(s['yr'], yr)
    s['u'][u] += 1
    s['m'][mat_of(r['building_code_description'], r['category_code_description'])] += 1
    if r['building_code_description_new']:
        s['dn'][r['building_code_description_new']] += 1
print(f'{n_rows} rows -> {len(sites)} sites ({n_skip} skipped: vacant/no-point)', flush=True)

site_pts, site_attr = [], []
for (lat, lng), s in sites.items():
    x = (lng - LON0) * KX
    z = (LAT0 - lat) * KZ
    u = s['u'].most_common(1)[0][0]
    m = s['m'].most_common(1)[0][0]
    dn = s['dn'].most_common(1)[0][0] if s['dn'] else ''
    e = era_of(s['yr'] if s['yr'] != 9999 else 0, dn)
    site_pts.append((x, z))
    site_attr.append((u, m, e, s['st']))

# ---------------- model footprints ----------------
def poly_of(pts):
    try:
        pg = Polygon(pts)
        if not pg.is_valid:
            pg = pg.buffer(0)
        return None if pg.is_empty else pg
    except Exception:
        return None

targets = []   # (setname, key, shapely poly)
core = json.load(open('scene.json'))
for i, b in enumerate(core['buildings']):
    if b.get('poly') and len(b['poly']) >= 3 and b.get('t') != 'ship':
        pg = poly_of(b['poly'])
        if pg: targets.append(('core', i, pg))
for name, path in (('wide', 'scene_wide.json'), ('south', 'scene_south.json')):
    d = json.load(open(path))
    for i, b in enumerate(d['buildings']):
        if b.get('poly') and len(b['poly']) >= 3 and b.get('t') not in ('ship', 'stadium', 'arena'):
            pg = poly_of(b['poly'])
            if pg: targets.append((name, i, pg))
print('loading osm_city_raw.json...', flush=True)
raw = json.load(open('osm_city_raw.json'))
nodes = {}
for el in raw['elements']:
    if el.get('type') == 'node':
        nodes[el['id']] = ((el['lon'] + 75.144748) * KX, (39.945474 - el['lat']) * KZ)
for el in raw['elements']:
    if el.get('type') != 'way' or 'building' not in (el.get('tags') or {}):
        continue
    pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        continue
    pg = poly_of(pts)
    if pg: targets.append(('city', el['id'], pg))
print(f'{len(targets)} target footprints', flush=True)

tree = STRtree([t[2] for t in targets])
hits = defaultdict(list)     # target index -> site attrs
n_in = n_near = n_miss = 0
for (x, z), attr in zip(site_pts, site_attr):
    p = Point(x, z)
    idxs = tree.query(p)
    # a site informs EVERY footprint containing it — the core scene, the wide
    # scene and the raw dump all carry their own copy of the same building
    containers = [i for i in idxs if targets[i][2].contains(p)]
    if containers:
        n_in += 1
        for i in containers:
            hits[i].append(attr)
        continue
    i = tree.nearest(p)
    if i is not None and targets[i][2].distance(p) <= 12.0:
        n_near += 1
        hits[i].append(attr)
    else:
        n_miss += 1
print(f'sites: {n_in} inside, {n_near} near, {n_miss} unmatched', flush=True)

out = {'core': {}, 'wide': {}, 'south': {}, 'city': {}}
for ti, attrs in hits.items():
    setname, key, _ = targets[ti]
    u = Counter(a[0] for a in attrs).most_common(1)[0][0]
    m = Counter(a[1] for a in attrs).most_common(1)[0][0]
    es = [a[2] for a in attrs if a[2] != 8]
    e = Counter(es).most_common(1)[0][0] if es else 8
    sts = [a[3] for a in attrs if a[3]]
    st = max(Counter(sts).most_common(1)[0][0], 0) if sts else 0
    out[setname][str(key)] = [u, m, e, min(st, 60)]
for name in out:
    json.dump(out[name], open(f'lidar_cache/opa_{name}.json', 'w'), separators=(',', ':'))
    print(f'opa_{name}.json: {len(out[name])} buildings', flush=True)
rep = json.load(open('lidar_report.json')) if os.path.exists('lidar_report.json') else {}
rep['opa'] = {'rows': n_rows, 'sites': len(sites), 'inside': n_in, 'near': n_near,
              'unmatched_sites': n_miss,
              'matched_buildings': {k: len(v) for k, v in out.items()}}
json.dump(rep, open('lidar_report.json', 'w'), indent=1)
print('done', flush=True)
