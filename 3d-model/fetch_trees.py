#!/usr/bin/env python3
"""Download the PPR Tree Inventory 2025 (OpenDataPhilly / City ArcGIS) for the
wide-tier envelope via the ArcGIS REST API and write
lidar_cache/phl_trees_raw.json: {"trees": [[lon, lat, dbh_in, name], ...]}.
Only the wide tier is fetched (~50k trees) — the far ring has no trees in the
model and stays that way. Resumable: per-page files in lidar_cache/tree_pages/.
Run with plain python3; pack_trees.py projects, filters, and packs the result."""
import json, os, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
PAGES = os.path.join(CACHE, 'tree_pages')
os.makedirs(PAGES, exist_ok=True)
BASE = ('https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
        'ppr_tree_inventory_2025/FeatureServer/0/query')
PAGE = 2000
# wide box (pack_wide.py WIDE) in lon/lat plus a ~30 m margin
ENV = '-75.1885,39.8873,-75.1174,39.9862'
GEO = {'geometry': ENV, 'geometryType': 'esriGeometryEnvelope', 'inSR': '4326',
       'spatialRel': 'esriSpatialRelIntersects'}

def total_count():
    q = urllib.parse.urlencode({'where': '1=1', **GEO, 'returnCountOnly': 'true', 'f': 'json'})
    with urllib.request.urlopen(BASE + '?' + q, timeout=60) as r:
        return json.load(r)['count']

def fetch_page(off):
    path = os.path.join(PAGES, f'p{off}.json')
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return path
    q = urllib.parse.urlencode({
        'where': '1=1', **GEO, 'outFields': 'tree_name,tree_dbh',
        'outSR': '4326', 'orderByFields': 'objectid',
        'resultOffset': off, 'resultRecordCount': PAGE, 'f': 'geojson'})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(BASE + '?' + q, timeout=120) as r:
                d = json.load(r)
            if 'features' not in d:
                raise RuntimeError(f'no features key: {str(d)[:200]}')
            with open(path + '.tmp', 'w') as f:
                json.dump(d, f)
            os.replace(path + '.tmp', path)
            return path
        except Exception:
            time.sleep(3 + 4 * attempt)
    raise RuntimeError(f'page {off} failed after retries')

def main():
    n = total_count()
    offsets = list(range(0, n, PAGE))
    print(f'{n} trees in the wide envelope, {len(offsets)} pages', flush=True)
    for i, off in enumerate(offsets):
        fetch_page(off)
        if (i + 1) % 5 == 0 or i + 1 == len(offsets):
            print(f'{i + 1}/{len(offsets)} pages', flush=True)
    trees = []
    for off in offsets:
        d = json.load(open(os.path.join(PAGES, f'p{off}.json')))
        for f in d['features']:
            g = f.get('geometry')
            if not g or g.get('type') != 'Point':
                continue
            lon, lat = g['coordinates'][:2]
            p = f.get('properties') or {}
            trees.append([round(lon, 6), round(lat, 6),
                          p.get('tree_dbh') or 0, (p.get('tree_name') or '').strip()])
    with open(os.path.join(CACHE, 'phl_trees_raw.json'), 'w') as f:
        json.dump({'trees': trees}, f, separators=(',', ':'))
    print(f'wrote {len(trees)} trees -> lidar_cache/phl_trees_raw.json', flush=True)

if __name__ == '__main__':
    main()
