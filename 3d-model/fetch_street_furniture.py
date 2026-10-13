#!/usr/bin/env python3
"""Fetch the street furniture OpenStreetMap maps across Philadelphia (the realism pass; the finding: "No street furniture:
signals, stop signs, bus-stop signs and hydrants are missing"): the signalised junctions (highway=traffic_signals),
the stop signs (highway=stop), the signalised crossings, the fire hydrants (emergency=fire_hydrant) and, in Center City
mostly, the benches and the litter bins. Nodes only, in a few tiles over the city's box, each tile checkpointed under
lidar_cache/furniture_tiles/ by overpass.py, merged into lidar_cache/street_furniture_raw.json for
bake_street_furniture.py. overpass-api.de is pinned first (the other mirrors hang on a node query this size)."""
import json, os
os.environ.setdefault('OVERPASS_MIRRORS', 'https://overpass-api.de/api/interpreter,https://overpass.private.coffee/api/interpreter')
from overpass import fetch_tiles, grid_tiles

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join('lidar_cache', 'furniture_tiles')   # relative, run from here (main() changes to it): provenance.jsonl records it
OUT = os.path.join(HERE, 'lidar_cache', 'street_furniture_raw.json')
# the city's box (fetch_city.py's boxes together, the wide box inside them), in 3 x 3 tiles
S, N, W, E = 39.860, 40.140, -75.285, -74.955


def query(bbox):
    return f'''[out:json][timeout:180];
(
  node["highway"="traffic_signals"]({bbox});
  node["highway"="stop"]({bbox});
  node["highway"="crossing"]["crossing"="traffic_signals"]({bbox});
  node["emergency"="fire_hydrant"]({bbox});
  node["amenity"="bench"]({bbox});
  node["amenity"="waste_basket"]({bbox});
);
out body qt;'''


def main():
    os.chdir(HERE)
    tiles = grid_tiles('furniture', S, N, W, E, 3, 3)
    elements = fetch_tiles(tiles, query, CACHE, rounds=3, pause=3)
    json.dump({'elements': elements}, open(OUT + '.tmp', 'w'))
    os.replace(OUT + '.tmp', OUT)
    kinds = {}
    for e in elements:
        t = e.get('tags') or {}
        k = t.get('highway') or t.get('emergency') or t.get('amenity') or '?'
        kinds[k] = kinds.get(k, 0) + 1
    print(OUT, len(elements), 'nodes', kinds)


if __name__ == '__main__':
    main()
