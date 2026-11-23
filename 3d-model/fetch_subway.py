#!/usr/bin/env python3
"""Round 267 (Mike: "The train station is missing from 2nd and market. I would like all underground Market Frankford
line, Broad Street Line, Patco stations to be included"): the subway stations and their street entrances from
OpenStreetMap, one Overpass request cached in lidar_cache/subway_raw/osm_subway.json until deleted:
  railway=subway_entrance and railway=train_station_entrance nodes, and the station=subway / subway=yes stations,
  inside the city and its 2 km flight buffer (ODbL).
bake_subway.py reads it with SEPTA's and PATCO's GTFS (fetch_septa_stops.py, fetch_patco.py). Run with plain python3."""
import json
import os

import overpass
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'subway_raw')
OUT = os.path.join(RAW, 'osm_subway.json')
BOX = '39.86,-75.29,40.14,-74.95'
QUERY = ('[out:json][timeout:120];('
         f'node["railway"="subway_entrance"]({BOX});'
         f'node["railway"="train_station_entrance"]({BOX});'
         f'nwr["railway"="station"]["station"="subway"]({BOX});'
         f'nwr["public_transport"="station"]["subway"="yes"]({BOX});'
         ');out center tags;')


def main():
    if os.path.exists(OUT):
        print('cached:', OUT)
        return
    os.makedirs(RAW, exist_ok=True)
    d = overpass.fetch(QUERY)
    els = d.get('elements', [])
    if sum(1 for e in els if e.get('tags', {}).get('railway') == 'subway_entrance') < 100:
        raise SystemExit('fetch_subway: under 100 subway entrances came back; nothing written')
    with open(OUT + '.tmp', 'w') as f:
        json.dump(d, f)
    os.replace(OUT + '.tmp', OUT)
    if provenance:
        provenance.record('fetch_subway.osm', overpass.LAST['mirror'], QUERY, len(els))
    print('wrote', OUT, len(els), 'elements')


if __name__ == '__main__':
    main()
