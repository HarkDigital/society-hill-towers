#!/usr/bin/env python3
"""Download the Streets Department street-lighting poles (Street_Poles on the
City ArcGIS, via OpenDataPhilly — 203k points citywide) and write
lidar_cache/phl_poles_raw.json: {"poles": [[lon, lat, height_ft, nlumin, bulb, type], ...]}.
Resumable: per-page files in lidar_cache/pole_pages/. Run with plain python3;
pack_poles.py projects, filters, and packs the result."""
import json, os, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
PAGES = os.path.join(CACHE, 'pole_pages')
os.makedirs(PAGES, exist_ok=True)
BASE = ('https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
        'Street_Poles/FeatureServer/0/query')
PAGE = 2000

def total_count():
    q = urllib.parse.urlencode({'where': '1=1', 'returnCountOnly': 'true', 'f': 'json'})
    with urllib.request.urlopen(BASE + '?' + q, timeout=60) as r:
        return json.load(r)['count']

def fetch_page(off):
    path = os.path.join(PAGES, f'p{off}.json')
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return path
    q = urllib.parse.urlencode({
        'where': '1=1', 'outFields': 'height,nlumin,bulb_type,type',
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
    print(f'{n} street poles, {len(offsets)} pages', flush=True)
    for i, off in enumerate(offsets):
        fetch_page(off)
        if (i + 1) % 10 == 0 or i + 1 == len(offsets):
            print(f'{i + 1}/{len(offsets)} pages', flush=True)
    poles = []
    for off in offsets:
        d = json.load(open(os.path.join(PAGES, f'p{off}.json')))
        for f in d['features']:
            g = f.get('geometry')
            if not g or g.get('type') != 'Point':
                continue
            lon, lat = g['coordinates'][:2]
            p = f.get('properties') or {}
            poles.append([round(lon, 6), round(lat, 6),
                          p.get('height') or 0, p.get('nlumin') or 1,
                          (p.get('bulb_type') or '').strip(), (p.get('type') or '').strip()])
    with open(os.path.join(CACHE, 'phl_poles_raw.json'), 'w') as f:
        json.dump({'poles': poles}, f, separators=(',', ':'))
    print(f'wrote {len(poles)} poles -> lidar_cache/phl_poles_raw.json', flush=True)

if __name__ == '__main__':
    main()
