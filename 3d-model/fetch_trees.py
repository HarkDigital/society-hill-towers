#!/usr/bin/env python3
"""Download the PPR Tree Inventory 2025 (OpenDataPhilly / City ArcGIS) and write
lidar_cache/phl_trees_raw.json: {"trees": [[lon, lat, dbh_in, name], ...]}.
Round 87 fetches the whole city (151,726 trees) instead of the wide tier's
envelope (50,073): the far ring had no trees at all, so West Philadelphia, the
Northeast and everything past x = -3700 stood bare. Resumable: per-page files in
lidar_cache/tree_pages/<env tag>/, keyed by envelope so a widened box never
reads the old box's pages back. Run with plain python3; pack_trees.py projects,
filters, and packs the result."""
import hashlib, json, os, time, urllib.request, urllib.parse
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
PAGES = os.path.join(CACHE, 'tree_pages')
BASE = ('https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
        'ppr_tree_inventory_2025/FeatureServer/0/query')
PAGE = 2000
# the whole city in lon/lat, a little past the city line so the far ring's edge
# is planted too (Round 87; the wide box alone was '-75.1885,39.8873,-75.1174,39.9862')
ENV = '-75.2900,39.8600,-74.9400,40.1500'
GEO = {'geometry': ENV, 'geometryType': 'esriGeometryEnvelope', 'inSR': '4326',
       'spatialRel': 'esriSpatialRelIntersects'}
# the page cache is keyed by envelope: p{off}.json for one box says nothing about
# another, and reading it back silently truncates the fetch to the old extent
PAGES = os.path.join(PAGES, hashlib.sha1(ENV.encode()).hexdigest()[:10])
os.makedirs(PAGES, exist_ok=True)

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
    print(f'{n} trees in {ENV}, {len(offsets)} pages', flush=True)
    for i, off in enumerate(offsets):
        fetch_page(off)
        if (i + 1) % 5 == 0 or i + 1 == len(offsets):
            print(f'{i + 1}/{len(offsets)} pages', flush=True)
    if provenance: provenance.record('fetch_trees.arcgis', BASE, f'where=1=1&geometry={ENV}&outFields=tree_name,tree_dbh&f=geojson', n, pages=len(offsets))
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
