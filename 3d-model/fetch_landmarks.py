#!/usr/bin/env python3
"""Download the City basemap's Landmarks (Landmark_Poly, 9,202 named polygons, and
Landmark_Points, 1,147 points, on the City ArcGIS via OpenDataPhilly: schools, places of
worship, hospitals, parks, recreation centers, cemeteries, universities, government
buildings, monuments and more, each with NAME, TYPE, SUBTYPE, ADDRESS, PARENT_NAME) and write
lidar_cache/landmarks_raw/poly.geojson and points.geojson. Resumable: per-page files in
lidar_cache/landmark_pages/. Run with plain python3; bake_landmarks.py projects, groups and
classes the result into landmarks.json for the search index (Round 78)."""
import json, os, time, urllib.parse, urllib.request
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
PAGES = os.path.join(CACHE, 'landmark_pages')
RAW = os.path.join(CACHE, 'landmarks_raw')
os.makedirs(PAGES, exist_ok=True)
os.makedirs(RAW, exist_ok=True)
SERVICES = 'https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
LAYERS = {
    'poly': (SERVICES + 'Landmark_Poly/FeatureServer/0/query', 'NAME,TYPE,SUBTYPE,ADDRESS,ACREAGE,PARENT_NAME,PARENT_SUBTYPE,PUBLIC_,ARCHIVE_DATE'),
    'points': (SERVICES + 'Landmark_Points/FeatureServer/0/query', 'NAME,TYPE,SUBTYPE,ADDRESS,PARENT_NAME,PARENT_SUBTYPE,PUBLIC_,ARCHIVE_DATE'),
}
PAGE = 2000


def total_count(base):
    q = urllib.parse.urlencode({'where': '1=1', 'returnCountOnly': 'true', 'f': 'json'})
    with urllib.request.urlopen(base + '?' + q, timeout=60) as r:
        return json.load(r)['count']


def fetch_page(key, base, fields, off):
    path = os.path.join(PAGES, f'{key}_p{off}.json')
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return path
    q = urllib.parse.urlencode({
        'where': '1=1', 'outFields': fields, 'outSR': '4326', 'orderByFields': 'OBJECTID',
        'geometryPrecision': '6', 'resultOffset': off, 'resultRecordCount': PAGE, 'f': 'geojson'})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(base + '?' + q, timeout=180) as r:
                d = json.load(r)
            if 'features' not in d:
                raise RuntimeError(f'no features key: {str(d)[:200]}')
            with open(path + '.tmp', 'w') as f:
                json.dump(d, f)
            os.replace(path + '.tmp', path)
            return path
        except Exception:
            time.sleep(3 + 4 * attempt)
    raise RuntimeError(f'{key} page {off} failed after retries')


def main():
    for key, (base, fields) in LAYERS.items():
        n = total_count(base)
        offsets = list(range(0, n, PAGE))
        print(f'{key}: {n} rows, {len(offsets)} pages', flush=True)
        feats = []
        for off in offsets:
            feats.extend(json.load(open(fetch_page(key, base, fields, off)))['features'])
        out = os.path.join(RAW, key + '.geojson')
        with open(out + '.tmp', 'w') as f:
            json.dump({'type': 'FeatureCollection', 'features': feats}, f)
        os.replace(out + '.tmp', out)
        if provenance:
            provenance.record('fetch_landmarks.' + key, base, f'where=1=1&outFields={fields}&outSR=4326&f=geojson', len(feats), pages=len(offsets))
        print(f'wrote {len(feats)} features -> lidar_cache/landmarks_raw/{key}.geojson', flush=True)


if __name__ == '__main__':
    main()
