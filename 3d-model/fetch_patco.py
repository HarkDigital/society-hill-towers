#!/usr/bin/env python3
"""Download PATCO's public timetable and its track into lidar_cache/patco_raw/ (Round 141):
  PATCO_GTFS.zip    PATCO's static GTFS (the permalink www.ridepatco.org/developers links, hosted by National RTAP):
                    the timetable bake_patco.py reads. PATCO publishes no live positions (no GTFS-realtime, no
                    train tracker), so the page runs its trains from this timetable and says so.
  osm_patco.json    the OpenStreetMap ways PATCO operates between 8th and Market and past Broadway, Overpass
                    `out geom` (ODbL): the track's course, with its tunnel and bridge tags.
One request each, rewritten on every run. Run with plain python3."""
import json, os, time, urllib.request
import overpass
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'patco_raw')
GTFS_URL = 'https://rapid.nationalrtap.org/GTFSFileManagement/UserUploadFiles/13562/PATCO_GTFS.zip'
BOX = (39.930, -75.175, 39.960, -75.100)   # S, W, N, E: 8th and Market to past Broadway, the bridge between
QUERY = '[out:json][timeout:120];way["railway"="subway"]["operator"~"PATCO",i](%s,%s,%s,%s);out geom;' % BOX


def atomic(path, data):
    with open(path + '.tmp', 'wb') as f:
        f.write(data)
    os.replace(path + '.tmp', path)


def get_gtfs():
    req = urllib.request.Request(GTFS_URL, headers={'User-Agent': 'philly3d-fetch/1 (+https://philly3d.com)'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) < 30_000:
                raise RuntimeError(f'PATCO_GTFS.zip: {len(data)} bytes, under the 30,000 floor')
            break
        except Exception as e:
            if attempt == 5:
                raise
            print('retry after', e, flush=True)
            time.sleep(3 + 4 * attempt)
    atomic(os.path.join(RAW, 'PATCO_GTFS.zip'), data)
    if provenance:
        provenance.record('fetch_patco.gtfs', GTFS_URL, '', len(data))
    print(f'wrote {len(data):,} bytes -> lidar_cache/patco_raw/PATCO_GTFS.zip', flush=True)


def get_osm():
    d = overpass.fetch(QUERY)
    ways = [e for e in d.get('elements', []) if e.get('type') == 'way' and e.get('geometry')]
    if len(ways) < 40:
        raise SystemExit(f'FATAL: only {len(ways)} PATCO ways in the box (expected about 100)')
    atomic(os.path.join(RAW, 'osm_patco.json'), json.dumps(d).encode())
    if provenance:
        provenance.record('fetch_patco.osm', overpass.LAST['mirror'], QUERY, len(ways))
    print(f'wrote {len(ways)} ways -> lidar_cache/patco_raw/osm_patco.json', flush=True)


def main():
    os.makedirs(RAW, exist_ok=True)
    get_gtfs()
    get_osm()


if __name__ == '__main__':
    main()
