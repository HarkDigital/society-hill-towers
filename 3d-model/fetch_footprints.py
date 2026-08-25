#!/usr/bin/env python3
"""Download the City of Philadelphia building footprints (LI_BUILDING_FOOTPRINTS,
546k polygons with 2022-LiDAR-derived MAX_HGT in feet) via the ArcGIS REST API,
convert to the model's local frame, and write lidar_cache/phl_footprints_local.json:
  {"fps": [[h_m, approx_m, [x1,z1,x2,z2,...ring...], [hole...]...], ...]}
Heights: h_m = max_hgt * 0.3048 (LiDAR max height above grade, 2022 QL1 flight).
Resumable: per-page files in lidar_cache/fp_pages/. Run with plain python3."""
import json, os, sys, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
PAGES = os.path.join(CACHE, 'fp_pages')
os.makedirs(PAGES, exist_ok=True)
BASE = ('https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
        'LI_BUILDING_FOOTPRINTS/FeatureServer/0/query')
PAGE = 2000
FT = 0.3048
LON0, LAT0, KX, KZ = -75.144748, 39.945474, 85350.0, 110574.0

def total_count():
    q = urllib.parse.urlencode({'where': '1=1', 'returnCountOnly': 'true', 'f': 'json'})
    with urllib.request.urlopen(BASE + '?' + q, timeout=60) as r:
        return json.load(r)['count']

def fetch_page(off):
    path = os.path.join(PAGES, f'p{off}.json')
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return path
    q = urllib.parse.urlencode({
        'where': '1=1', 'outFields': 'max_hgt,approx_hgt',
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
        except Exception as e:
            time.sleep(3 + 4 * attempt)
    raise RuntimeError(f'page {off} failed after retries')

def main():
    n = total_count()
    offsets = list(range(0, n, PAGE))
    print(f'{n} footprints, {len(offsets)} pages', flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for _ in ex.map(fetch_page, offsets):
            done += 1
            if done % 20 == 0:
                print(f'{done}/{len(offsets)} pages', flush=True)
    # merge into the local frame
    fps = []
    n_h = 0
    for off in offsets:
        d = json.load(open(os.path.join(PAGES, f'p{off}.json')))
        for f in d['features']:
            g = f.get('geometry')
            if not g or g['type'] not in ('Polygon', 'MultiPolygon'):
                continue
            p = f['properties']
            mh = p.get('max_hgt')
            ah = p.get('approx_hgt')
            h = round(mh * FT, 2) if mh is not None else None
            a = round(ah * FT, 2) if ah is not None else None
            polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
            for rings in polys:
                out = []
                for ring in rings:
                    flat = []
                    for lon, lat in ring:
                        flat.append(round((lon - LON0) * KX, 2))
                        flat.append(round((LAT0 - lat) * KZ, 2))
                    out.append(flat)
                if out and len(out[0]) >= 8:
                    fps.append([h, a, out])
                    if h is not None:
                        n_h += 1
    with open(os.path.join(CACHE, 'phl_footprints_local.json'), 'w') as f:
        json.dump({'fps': fps}, f, separators=(',', ':'))
    print(f'wrote {len(fps)} footprint polys ({n_h} with max_hgt) '
          f'-> lidar_cache/phl_footprints_local.json', flush=True)

if __name__ == '__main__':
    main()
