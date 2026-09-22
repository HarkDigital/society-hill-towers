#!/usr/bin/env python3
"""Download SEPTA's public GTFS release and its Arrivals station list into lidar_cache/septa_raw/ (Round 133):
  gtfs_public.zip        github.com/septadev/GTFS releases/latest (about 22 MB): holds google_bus.zip and
                         google_rail.zip, each a GTFS feed; the stops are what bake_septa_stops.py reads.
  station_id_name.csv    the station names the Arrivals API accepts (www3.septa.org/api/Arrivals), so a
                         rail stop can be matched to the exact name a departure board asks for.
Both are one request each and cached until deleted. Run with plain python3."""
import os, time, urllib.request
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'septa_raw')
os.makedirs(RAW, exist_ok=True)
SRC = [
    ('https://github.com/septadev/GTFS/releases/latest/download/gtfs_public.zip', 'gtfs_public.zip', 5_000_000),
    ('https://www3.septa.org/api/Arrivals/station_id_name.csv', 'station_id_name.csv', 2_000),
]


def get(url, name, floor):
    path = os.path.join(RAW, name)
    req = urllib.request.Request(url, headers={'User-Agent': 'philly3d-fetch/1 (+https://philly3d.com)'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            if len(data) < floor:
                raise RuntimeError(f'{name}: {len(data)} bytes, under the {floor} floor')
            break
        except Exception as e:
            if attempt == 5:
                raise
            print('retry after', e, flush=True)
            time.sleep(3 + 4 * attempt)
    with open(path + '.tmp', 'wb') as f:
        f.write(data)
    os.replace(path + '.tmp', path)
    if provenance:
        provenance.record('fetch_septa_stops.' + name.split('.')[0], url, '', len(data))
    print(f'wrote {len(data):,} bytes -> {os.path.relpath(path, HERE)}', flush=True)


def main():
    for url, name, floor in SRC:
        get(url, name, floor)


if __name__ == '__main__':
    main()
