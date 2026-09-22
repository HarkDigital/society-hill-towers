#!/usr/bin/env python3
"""Download the city's libraries and recreation centers into lidar_cache/civic_raw/ (Round 134):
  libraries.json   the Free Library's 54 branches (library_locations on the City ArcGIS): building,
                   address, zip_code, phone_number, library_url. No hours: the Free Library publishes
                   none as data, so the page links each branch's own page for them.
  ppr_sites.json   Parks and Recreation's program sites (PPR_Program_Sites): the recreation centers
                   (program_type PPR_REC) and the older adult centers, with the building and gym flags.
                   The pools are left out (Mike declined them in the Sep 16 survey).
Both are one request each and cached until deleted. Run with plain python3."""
import json, os, time, urllib.parse, urllib.request
try:
    import provenance
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'civic_raw')
os.makedirs(RAW, exist_ok=True)
BASE = 'https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
SRC = [
    ('library_locations', {'where': '1=1'}, 'libraries.json', 40),
    ('PPR_Program_Sites', {'where': "program_type IN ('PPR_REC','OLDER_ADULT_CENTER')"}, 'ppr_sites.json', 100),
]


def get(layer, where, name, floor):
    q = dict(where, outFields='*', outSR='4326', returnGeometry='true', f='json', resultRecordCount='2000')
    url = BASE + layer + '/FeatureServer/0/query?' + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={'User-Agent': 'philly3d-fetch/1 (+https://philly3d.com)'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            n = len(d.get('features') or [])
            if n < floor:
                raise RuntimeError(f'{layer}: {n} features, under {floor}: ' + str(d)[:200])
            break
        except Exception as e:
            if attempt == 5:
                raise
            print('retry after', e, flush=True)
            time.sleep(3 + 4 * attempt)
    path = os.path.join(RAW, name)
    with open(path + '.tmp', 'w') as f:
        json.dump(d, f)
    os.replace(path + '.tmp', path)
    if provenance:
        provenance.record('fetch_civic.' + name.split('.')[0], url, '', n)
    print(f'wrote {n} features -> {os.path.relpath(path, HERE)}', flush=True)


def main():
    for layer, where, name, floor in SRC:
        get(layer, where, name, floor)


if __name__ == '__main__':
    main()
