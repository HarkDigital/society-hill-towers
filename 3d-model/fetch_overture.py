#!/usr/bin/env python3
"""Pull what Overture Maps' buildings theme knows about Philadelphia's buildings
beyond the OSM tags the scene was built from (roof shape/colour, facade colour/
material, height, floors) and export it for the roof and facade passes.

Source: the public Overture bucket s3://overturemaps-us-west-2/release/<release>/
theme=buildings/type=building/*.parquet (512 zstd parquet files, ~260 GB; read
anonymously with DuckDB's httpfs + spatial extensions). The release is the newest
one listed under the bucket's release/ prefix unless --release pins it. The scan
filters on the per-row-group bbox struct (bbox.xmin/xmax/ymin/ymax) for the box
lon -75.30..-74.94, lat 39.85..40.15, so only the row groups touching Philadelphia
are fetched: one pass, minutes not hours, and the raw result is cached as
  lidar_cache/overture_raw_<release>.parquet   (id, sources, the attribute
      columns, class, subtype, centroid lon/lat; rerun with --force to refetch)
so the summary and the export below rerun from the local file in seconds.

Outputs (both under lidar_cache/):
  overture_phl.json      {"release": "...", "n": <buildings in the box>,
                          "byWay": {"<osm way id>": {"rs": roof_shape, "rc": roof_color,
                                    "fc": facade_color, "fm": facade_material,
                                    "h": height_m, "nf": num_floors}},   (nulls kept)
                          "noWay": [[lon, lat, rs, rc, fc, fm, h, nf], ...]}
      Only buildings with at least one of rs/rc/fc/fm set are written; byWay keys
      are the OSM way ids recovered from sources[].record_id ('w123456@7' entries
      of dataset 'OpenStreetMap'); noWay holds the rest (Microsoft/Esri/Google
      ML footprints and OSM multipolygon relations) by centroid.
  overture_phl_summary.json   the coverage counts printed at the end of a run.

Needs: python3 -m pip install --user duckdb (1.4+; the httpfs and spatial
extensions are installed on first use into ~/.duckdb). Stdlib otherwise.
Usage: python3 fetch_overture.py [--release 2026-08-19.0] [--force]"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
os.makedirs(CACHE, exist_ok=True)
OUT = os.path.join(CACHE, 'overture_phl.json')
SUMMARY = os.path.join(CACHE, 'overture_phl_summary.json')

BUCKET_HTTP = 'https://overturemaps-us-west-2.s3.amazonaws.com'
BUCKET_S3 = 's3://overturemaps-us-west-2'
DEFAULT_RELEASE = '2026-08-19.0'     # used only if the bucket listing fails
W, S, E, N = -75.30, 39.85, -74.94, 40.15   # lon/lat box: the far ring plus a margin

ATTRS = ('roof_shape', 'roof_color', 'facade_color', 'facade_material')   # what gets exported
STAT_COLS = ATTRS + ('roof_material', 'height', 'num_floors')


def latest_release():
    """Newest 'release/YYYY-MM-DD.N/' prefix in the public bucket (anonymous listing)."""
    url = BUCKET_HTTP + '/?list-type=2&prefix=release/&delimiter=/'
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            xml = r.read().decode('utf-8', 'replace')
    except Exception as e:
        print(f'release listing failed ({e}); using {DEFAULT_RELEASE}', flush=True)
        return DEFAULT_RELEASE
    ids = re.findall(r'<Prefix>release/(\d{4}-\d{2}-\d{2}\.\d+)/</Prefix>', xml)
    if not ids:
        print(f'no releases in listing; using {DEFAULT_RELEASE}', flush=True)
        return DEFAULT_RELEASE
    return max(ids, key=lambda s: (s[:10], int(s[11:])))


def connect():
    import duckdb
    con = duckdb.connect()
    con.execute('INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;')
    con.execute("SET s3_region='us-west-2'; SET s3_access_key_id=''; SET s3_secret_access_key='';")
    con.execute('SET http_retries=6; SET http_retry_wait_ms=2000; SET http_timeout=120000;')
    return con


def fetch_raw(con, release, raw, force):
    """One pass over the release's buildings parquet, bbox-pruned, cached locally."""
    if os.path.exists(raw) and os.path.getsize(raw) > 1000 and not force:
        print(f'raw cache present: {raw} ({os.path.getsize(raw)/1e6:.1f} MB)', flush=True)
        return
    src = f'{BUCKET_S3}/release/{release}/theme=buildings/type=building/*.parquet'
    sql = f"""
COPY (
  SELECT id, sources, height, num_floors, roof_shape, roof_material, roof_color,
         facade_color, facade_material, class, subtype,
         ST_X(ST_Centroid(geometry)) AS lon, ST_Y(ST_Centroid(geometry)) AS lat
  FROM read_parquet('{src}', hive_partitioning=1)
  WHERE bbox.xmin <= {E} AND bbox.xmax >= {W} AND bbox.ymin <= {N} AND bbox.ymax >= {S}
) TO '{raw}.tmp' (FORMAT PARQUET, COMPRESSION ZSTD)"""
    print(f'scanning {src}\n  box lon {W}..{E} lat {S}..{N} (this is the slow step)', flush=True)
    t0 = time.time()
    con.execute(sql)
    os.replace(raw + '.tmp', raw)
    n = con.execute(f"SELECT count(*) FROM read_parquet('{raw}')").fetchone()[0]
    print(f'  {n} buildings in {time.time()-t0:.0f} s -> {raw} ({os.path.getsize(raw)/1e6:.1f} MB)', flush=True)
    if provenance:
        provenance.record('fetch_overture.s3', src, sql, n, release=release,
                          bytes=os.path.getsize(raw))


# sources[] entries of dataset 'OpenStreetMap' carry record_id like 'w123456@7'
# (way), 'r123@2' (multipolygon relation) or 'n123@1'; the export keys by way id.
OSM_IDS = ("list_transform(list_filter(sources, lambda s: s.dataset = 'OpenStreetMap' "
           "AND s.record_id IS NOT NULL), lambda s: s.record_id)")
ROWS_SQL = f"""
SELECT id,
       list_filter({OSM_IDS}, lambda r: r LIKE 'w%')[1] AS way,
       list_filter({OSM_IDS}, lambda r: r LIKE 'r%')[1] AS rel,
       sources[1].dataset AS dataset,
       roof_shape, roof_color, facade_color, facade_material, roof_material,
       height, num_floors, class, subtype, lon, lat
FROM read_parquet('{{raw}}')"""


def way_id(rid):
    m = re.match(r'w(\d+)', rid or '')
    return m.group(1) if m else None


def summarize(con, raw, release):
    """Coverage counts for the box; printed and returned as a dict."""
    view = ROWS_SQL.format(raw=raw)
    con.execute(f'CREATE OR REPLACE TEMP VIEW b AS {view}')
    n = con.execute('SELECT count(*) FROM b').fetchone()[0]
    summ = {'release': release, 'box': [W, S, E, N], 'n': n, 'nonnull': {}}
    print(f'\nOverture {release}, buildings touching the box: {n}')
    for c in STAT_COLS:
        k = con.execute(f'SELECT count({c}) FROM b').fetchone()[0]
        summ['nonnull'][c] = k
        print(f'  {c:16s} {k:8d}  {100.0*k/max(n,1):5.1f}%')
    for c in ('roof_shape', 'roof_material', 'facade_material', 'roof_color', 'facade_color', 'dataset', 'class', 'subtype'):
        rows = con.execute(f'SELECT {c}, count(*) AS k FROM b WHERE {c} IS NOT NULL '
                           f'GROUP BY 1 ORDER BY k DESC LIMIT 25').fetchall()
        summ[c] = [[v, k] for v, k in rows]
        print(f'  {c} values:', ', '.join(f'{v} {k}' for v, k in rows))
    ways = con.execute('SELECT count(way) FROM b').fetchone()[0]
    rels = con.execute('SELECT count(rel) FROM b WHERE way IS NULL').fetchone()[0]
    any_attr = ' OR '.join(f'{c} IS NOT NULL' for c in ATTRS)
    att = con.execute(f'SELECT count(*), count(way) FROM b WHERE {any_attr}').fetchone()
    ht = con.execute('SELECT dataset, count(height), count(*) FROM b GROUP BY 1 ORDER BY 3 DESC').fetchall()
    summ.update({'osm_way': ways, 'osm_relation_only': rels,
                 'with_attr': att[0], 'with_attr_way': att[1],
                 'height_by_dataset': [[d, h, k] for d, h, k in ht]})
    print(f'  OSM way id in sources: {ways} ({100.0*ways/max(n,1):.1f}%), '
          f'OSM relation only: {rels}')
    print(f'  rows with any of {"/".join(ATTRS)}: {att[0]}, of which keyed by way: {att[1]}')
    print('  height non-null by primary dataset:',
          ', '.join(f'{d} {h}/{k}' for d, h, k in ht))
    return summ


def export(con, raw, release, n):
    """Write overture_phl.json: byWay keyed on the OSM way id, noWay by centroid."""
    any_attr = ' OR '.join(f'{c} IS NOT NULL' for c in ATTRS)
    cur = con.execute(f'SELECT way, roof_shape, roof_color, facade_color, facade_material, '
                      f'height, num_floors, lon, lat FROM b WHERE {any_attr}')
    by_way, no_way, dup = {}, [], 0
    while True:
        rows = cur.fetchmany(20000)
        if not rows:
            break
        for way, rs, rc, fc, fm, h, nf, lon, lat in rows:
            h = round(h, 1) if h is not None else None
            wid = way_id(way)
            if wid is None:
                no_way.append([round(lon, 6), round(lat, 6), rs, rc, fc, fm, h, nf])
                continue
            rec = {'rs': rs, 'rc': rc, 'fc': fc, 'fm': fm, 'h': h, 'nf': nf}
            old = by_way.get(wid)
            if old:      # the same way twice (split footprints): keep every non-null
                dup += 1
                for k, v in rec.items():
                    if old[k] is None and v is not None:
                        old[k] = v
            else:
                by_way[wid] = rec
    out = {'release': release, 'n': n, 'byWay': by_way, 'noWay': no_way}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print(f'\nwrote {OUT}: byWay {len(by_way)}, noWay {len(no_way)}, '
          f'{dup} duplicate way ids merged, {os.path.getsize(OUT)/1e6:.2f} MB', flush=True)
    return len(by_way), len(no_way)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--release', help='Overture release id (default: newest in the bucket)')
    ap.add_argument('--force', action='store_true', help='refetch even if the raw cache exists')
    a = ap.parse_args()
    release = a.release or latest_release()
    print(f'Overture release {release}', flush=True)
    raw = os.path.join(CACHE, f'overture_raw_{release}.parquet')
    try:
        con = connect()
    except Exception as e:
        sys.exit(f'DuckDB setup failed: {e}\n(python3 -m pip install --user duckdb)')
    fetch_raw(con, release, raw, a.force)
    summ = summarize(con, raw, release)
    summ['byWay'], summ['noWay'] = export(con, raw, release, summ['n'])
    summ['out_bytes'] = os.path.getsize(OUT)
    with open(SUMMARY, 'w') as f:
        json.dump(summ, f, indent=1)
    print(f'summary -> {SUMMARY}')


if __name__ == '__main__':
    main()
