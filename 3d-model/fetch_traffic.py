#!/usr/bin/env python3
"""PennDOT traffic volumes (RMSTRAFFIC) for the wide extent, cached raw.
One envelope query against the open-data ArcGIS layer, paginated until
exceededTransferLimit clears. Writes lidar_cache/traffic_raw/rmstraffic.geojson;
skips the fetch entirely when the merged file already exists."""
import json, math, pathlib, time, urllib.request, urllib.parse

HERE = pathlib.Path(__file__).parent
CACHE = HERE / 'lidar_cache' / 'traffic_raw'
OUT = CACHE / 'rmstraffic.geojson'
SVC = 'https://gis.penndot.gov/arcgis/rest/services/opendata/roadwaytraffic/MapServer/0/query'

# wide local extent + 200 m pad, converted with the scene origin (process_osm.py math)
LAT0, LON0 = 39.945473644755005, -75.14474803850973
MX = 111320 * math.cos(math.radians(LAT0))
MZ = 110574
X0, X1, Z0, Z1 = -3900, 2500, -4680, 6600
W, E = LON0 + X0 / MX, LON0 + X1 / MX
N, S = LAT0 - Z0 / MZ, LAT0 - Z1 / MZ

def fetch(url):
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'SHT-3d-model-bake/1.0'})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(5 + 5 * attempt)
    raise last

def main():
    if OUT.exists():
        d = json.load(open(OUT))
        print(f'cached: {OUT} ({len(d["features"])} segments) — delete to refetch')
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    feats, offset, page = [], 0, 0
    while True:
        params = urllib.parse.urlencode({
            'where': '1=1',
            'geometry': json.dumps({'xmin': W, 'ymin': S, 'xmax': E, 'ymax': N}),
            'geometryType': 'esriGeometryEnvelope',
            'inSR': 4326, 'outSR': 4326,
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': 'CUR_AADT,ST_RT_NO,SEG_LNGTH_FEET,K_FACTOR,D_FACTOR,DIR_IND',
            'returnGeometry': 'true',
            'f': 'geojson',
            'resultOffset': offset,
            'resultRecordCount': 1000,
        })
        d = fetch(SVC + '?' + params)
        got = d.get('features', [])
        feats += got
        (CACHE / f'rmstraffic_p{page}.geojson').write_text(json.dumps(d))
        print(f'page {page}: +{len(got)} segments (total {len(feats)})', flush=True)
        more = d.get('exceededTransferLimit') or (d.get('properties') or {}).get('exceededTransferLimit')
        if not more or not got:
            break
        offset += len(got)
        page += 1
        time.sleep(1)
    OUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}))
    print(f'wrote {OUT} ({len(feats)} segments)')

if __name__ == '__main__':
    main()
