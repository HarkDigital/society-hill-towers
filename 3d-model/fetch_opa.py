#!/usr/bin/env python3
"""Download the OPA properties table (583k rows) from phl.carto.com into
lidar_cache/opa_rows.csv — the attribute source for the Tier-1 facade pass.
Paginated by cartodb_id, resumable. Plain python3."""
import os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
os.makedirs(CACHE, exist_ok=True)
OUT = os.path.join(CACHE, 'opa_rows.csv')
PAGES_DIR = os.path.join(CACHE, 'opa_pages')
os.makedirs(PAGES_DIR, exist_ok=True)

COLS = ('parcel_number, location, unit, building_code_description, '
        'building_code_description_new, category_code_description, '
        'number_stories, year_built, year_built_estimate, general_construction, '
        'quality_grade, ST_X(the_geom) AS lng, ST_Y(the_geom) AS lat, cartodb_id')
STEP = 40000
MAXID = 700000   # cartodb_id upper bound (count is 583k; ids can be sparse)

def fetch(lo, hi):
    path = os.path.join(PAGES_DIR, f'{lo}.csv')
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return path
    q = (f'SELECT {COLS} FROM opa_properties_public '
         f'WHERE cartodb_id > {lo} AND cartodb_id <= {hi} ORDER BY cartodb_id')
    url = 'https://phl.carto.com/api/v2/sql?' + urllib.parse.urlencode(
        {'q': q, 'format': 'csv'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                data = r.read()
            if not data.startswith(b'parcel_number'):
                raise RuntimeError('unexpected: ' + data[:120].decode('utf-8', 'replace'))
            with open(path + '.tmp', 'wb') as f:
                f.write(data)
            os.replace(path + '.tmp', path)
            return path
        except Exception as e:
            print(f'page {lo}: retry {attempt} ({e})', flush=True)
            time.sleep(5 + 5 * attempt)
    raise RuntimeError(f'page {lo} failed')

total = 0
parts = []
for lo in range(0, MAXID, STEP):
    p = fetch(lo, lo + STEP)
    n = sum(1 for _ in open(p, 'rb')) - 1
    total += max(0, n)
    parts.append(p)
    print(f'{lo}-{lo+STEP}: {n} rows (total {total})', flush=True)
with open(OUT, 'w') as out:
    first = True
    for p in parts:
        with open(p) as f:
            hdr = f.readline()
            if first:
                out.write(hdr)
                first = False
            for line in f:
                out.write(line)
print(f'wrote {OUT}: {total} rows', flush=True)
