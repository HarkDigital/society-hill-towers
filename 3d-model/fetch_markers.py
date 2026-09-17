#!/usr/bin/env python3
"""Download the two public-art inputs of Round 77 into lidar_cache/markers_raw/:
  phmc.json                  the Pennsylvania Historical and Museum Commission's historical
                             markers in Philadelphia County (data.pa.gov, Socrata dataset
                             xt8f-pzzz, public domain): id, name, dedicateddate, markertype
                             (Roadside, City, Plaque), location, markertext, status, latitude,
                             longitude. 348 rows on 2026-09-16.
  percent_for_art.geojson    the City's Percent for Art works (Percent_for_Art_Public on the
                             City ArcGIS via OpenDataPhilly): p4a_id, image, status, artist,
                             title, date_, location_name, address, location_note, medium,
                             neighborhood, with a 40 m buffer polygon around each. 239 rows.
Both are one request. Run with plain python3; bake_markers.py projects and writes markers.json."""
import json, os, time, urllib.parse, urllib.request
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'markers_raw')
os.makedirs(RAW, exist_ok=True)
PHMC = 'https://data.pa.gov/resource/xt8f-pzzz.json'
PHMC_Q = {'$where': "upper(county) like 'PHILADELPHIA%'", '$limit': '2000'}
ART = ('https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
       'Percent_for_Art_Public/FeatureServer/0/query')
ART_Q = {'where': '1=1', 'outFields': '*', 'returnGeometry': 'true', 'outSR': '4326', 'orderByFields': 'objectid', 'f': 'geojson'}


def get(url, query, path, key):
    q = urllib.parse.urlencode(query)
    req = urllib.request.Request(url + '?' + q, headers={'User-Agent': 'philly3d-fetch/1 (+https://philly3d.com)'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            n = len(d) if isinstance(d, list) else len(d.get(key) or [])
            if not n:
                raise RuntimeError('empty answer: ' + str(d)[:200])
            break
        except Exception as e:
            if attempt == 5:
                raise
            print('retry after', e, flush=True)
            time.sleep(3 + 4 * attempt)
    with open(path + '.tmp', 'w') as f:
        json.dump(d, f)
    os.replace(path + '.tmp', path)
    if provenance:
        provenance.record('fetch_markers.' + os.path.basename(path).split('.')[0], url, q, n)
    print(f'wrote {n} rows -> {os.path.relpath(path, HERE)}', flush=True)


def main():
    get(PHMC, PHMC_Q, os.path.join(RAW, 'phmc.json'), None)
    get(ART, ART_Q, os.path.join(RAW, 'percent_for_art.geojson'), 'features')


if __name__ == '__main__':
    main()
