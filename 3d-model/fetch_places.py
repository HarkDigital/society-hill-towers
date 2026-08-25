#!/usr/bin/env python3
"""Download the two small 'places' sources into lidar_cache/places_raw/:
  historic_districts.geojson — Philadelphia Register historic districts
      (phl.carto.com SQL API, 17 polygons)
  neighborhoods.geojson — Philadelphia neighborhoods (OpenDataPhilly storage,
      159 MultiPolygons, MAPNAME + Shape_Area, CC-BY 4.0)
Both are cached; delete the files to re-fetch. bake_places.py turns them into
places.json for the app."""
import os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'places_raw')
os.makedirs(RAW, exist_ok=True)

HD_URL = ('https://phl.carto.com/api/v2/sql?q='
          + urllib.parse.quote('SELECT name, the_geom FROM historicdistricts_local')
          + '&format=geojson')
NB_URL = ('https://raw.githubusercontent.com/opendataphilly/odp-data-storage/'
          'master/philadelphia-neighborhoods/philadelphia-neighborhoods.geojson')

def get(url, path, tries=6):
    if os.path.exists(path) and os.path.getsize(path) > 500:
        print(f'cached {os.path.basename(path)}', flush=True)
        return
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'SHT-3d-model-bake/1.0'})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            if len(data) < 500:
                raise RuntimeError('suspiciously small response')
            with open(path + '.tmp', 'wb') as f:
                f.write(data)
            os.replace(path + '.tmp', path)
            print(f'fetched {os.path.basename(path)} ({len(data) / 1e3:.0f} KB)', flush=True)
            return
        except Exception as e:
            print(f'  retry {attempt + 1}/{tries}: {e}', flush=True)
            time.sleep(3 + 3 * attempt)
    raise SystemExit(f'FATAL: cannot fetch {url}')

if __name__ == '__main__':
    get(HD_URL, os.path.join(RAW, 'historic_districts.geojson'))
    get(NB_URL, os.path.join(RAW, 'neighborhoods.geojson'))
