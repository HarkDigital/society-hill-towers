#!/usr/bin/env python3
"""Shared Overpass fetch for the tiled OSM extracts (fetch_city / fetch_wide /
fetch_south): mirror rotation with backoff, and per-tile checkpoints so a rerun
only touches the tiles that failed. Lifted verbatim from fetch_city.py's loop,
which was the only fetch that could survive a mirror outage without starting over.

  tiles = grid_tiles('wide', S, N, W, E, rows, cols)   # [(tile id, 'S,W,N,E'), ...]
  elements = fetch_tiles(tiles, query_fn, 'wide_tiles')  # id-deduplicated, tile order

fetch_tiles() writes <cache_dir>/<tile id>.json per tile (atomically, so a killed
run never leaves a truncated checkpoint that a rerun would skip), retries missing
tiles for `rounds` passes, and EXITS NON-ZERO if any tile is still missing - a
partial extract silently packed as a full one is how the bare patches happened.
Delete a tile file to force its refetch. Plain python3."""
import json, os, sys, time, urllib.request, urllib.parse

MIRRORS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
           'https://overpass.private.coffee/api/interpreter']
USER_AGENT = 'sht-3d-model/1.0'


def fetch(query, mirrors=MIRRORS, attempts=10, timeout=190):
    """POST one Overpass QL query, rotating mirrors with a growing backoff
    (12 s, 26 s, ... capped at 120 s). Raises the last error after `attempts`."""
    data = urllib.parse.urlencode({'data': query}).encode()
    last = None
    for attempt in range(attempts):
        url = mirrors[attempt % len(mirrors)]
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(min(120, 12 + 14 * attempt))
    raise last


def grid_tiles(name, S, N, W, E, rows, cols):
    """Split the lat/lon box into rows x cols tiles: [(f'{name}-{i}-{j}', 'S,W,N,E'), ...]
    (same ids and 5-decimal bbox strings fetch_city.py always used, so its
    city_tiles/ checkpoints stay valid)."""
    tiles = []
    for i in range(rows):
        for j in range(cols):
            s = S + (N - S) * i / rows; n = S + (N - S) * (i + 1) / rows
            w = W + (E - W) * j / cols; e = W + (E - W) * (j + 1) / cols
            tiles.append((f'{name}-{i}-{j}', f'{s:.5f},{w:.5f},{n:.5f},{e:.5f}'))
    return tiles


def _tile_path(cache_dir, tid):
    return os.path.join(cache_dir, f'{tid}.json')


def fetch_tiles(tiles, query_fn, cache_dir, rounds=3, pause=5):
    """Fetch every (tile id, bbox) whose checkpoint is absent, `rounds` passes over
    the stragglers, `pause` seconds between tiles (mirror etiquette). Returns the
    merged element list, deduplicated by (type, id) in tile order. Any tile still
    missing after the last round is fatal (sys.exit(1)) - nothing is written."""
    os.makedirs(cache_dir, exist_ok=True)
    for rnd in range(rounds):
        missing = [(tid, bbox) for tid, bbox in tiles if not os.path.exists(_tile_path(cache_dir, tid))]
        if not missing:
            break
        print(f'round {rnd}: {len(missing)} tiles to fetch', flush=True)
        for tid, bbox in missing:
            t0 = time.time()
            try:
                d = fetch(query_fn(bbox))
            except Exception as e:
                print(f'{tid} FAILED this round: {e}', flush=True)
                continue
            path = _tile_path(cache_dir, tid)
            with open(path + '.tmp', 'w') as f:
                json.dump(d, f)
            os.replace(path + '.tmp', path)
            print(f'{tid} {bbox}: {len(d.get("elements", []))} elements ({time.time()-t0:.0f}s)', flush=True)
            time.sleep(pause)
    missing = [tid for tid, _ in tiles if not os.path.exists(_tile_path(cache_dir, tid))]
    if missing:
        print(f'ERROR: {len(missing)} of {len(tiles)} tiles still missing after {rounds} rounds: '
              f'{missing[:8]}{" ..." if len(missing) > 8 else ""} - rerun to retry just those '
              f'(checkpoints in {cache_dir}/)', file=sys.stderr, flush=True)
        sys.exit(1)
    return merge_tiles(tiles, cache_dir)


def merge_tiles(tiles, cache_dir):
    """Concatenate the cached tiles in order, keeping the first copy of each (type, id)."""
    elements, seen = [], set()
    for tid, _ in tiles:
        with open(_tile_path(cache_dir, tid)) as f:
            for el in json.load(f).get('elements', []):
                k = (el['type'], el['id'])
                if k in seen:
                    continue
                seen.add(k); elements.append(el)
    return elements
