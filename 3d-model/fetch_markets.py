#!/usr/bin/env python3
"""Download the City's Farmers' Market Locations (Farmers_Markets on the City ArcGIS,
via OpenDataPhilly: 34 points with per-weekday hours, the season, the payments each
market takes and its website) and write lidar_cache/markets_raw/farmers_markets.geojson,
the service's own GeoJSON, untouched. One page (the layer is far under the 2,000-row cap).
Run with plain python3; bake_markets.py projects, parses and writes markets.json."""
import json, os, time, urllib.request, urllib.parse
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'markets_raw')
os.makedirs(RAW, exist_ok=True)
BASE = ('https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
        'Farmers_Markets/FeatureServer/0/query')
OUT = os.path.join(RAW, 'farmers_markets.geojson')
QUERY = {'where': '1=1', 'outFields': '*', 'outSR': '4326', 'orderByFields': 'objectid', 'f': 'geojson'}


def main():
    q = urllib.parse.urlencode(QUERY)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(BASE + '?' + q, timeout=120) as r:
                d = json.load(r)
            if 'features' not in d:
                raise RuntimeError('no features key: ' + str(d)[:200])
            break
        except Exception as e:
            if attempt == 5:
                raise
            print('retry after', e, flush=True)
            time.sleep(3 + 4 * attempt)
    with open(OUT + '.tmp', 'w') as f:
        json.dump(d, f)
    os.replace(OUT + '.tmp', OUT)
    n = len(d['features'])
    if provenance:
        provenance.record('fetch_markets.arcgis', BASE, q, n)
    print(f'wrote {n} markets -> lidar_cache/markets_raw/farmers_markets.geojson', flush=True)


if __name__ == '__main__':
    main()
