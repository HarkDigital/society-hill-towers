#!/usr/bin/env python3
"""Bake the libraries and recreation centers into civic.json for the page (Round 134).

Inputs (fetch_civic.py): lidar_cache/civic_raw/libraries.json and ppr_sites.json.
Output: {"lib": [[x, z, name, address, zip, phone, url]], "rec": [[x, z, name, kind, gym]]}, x and z whole
metres in the scene frame; kind 0 a recreation center, 1 an older adult center; gym 1 when PPR flags one.
A point inside one of the page's building footprints is stepped 2.5 m out past the nearest wall (bake_markers'
FootGrid), so its pin stands in the open and is not hidden by its own building. Strings cleaned as the
markers' are. Run with plain python3."""
import json, os, sys
from philly_frame import to_xz
from bake_markers import FootGrid, load_footprints, clean

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'civic_raw')
OUT = os.path.join(HERE, 'civic.json')


def pt(f):
    g = f.get('geometry') or {}
    if 'x' in g and 'y' in g:
        return to_xz(g['y'], g['x'])
    return None


def bake(libs, sites, footprints=None):
    lib, rec = [], []
    for f in libs:
        a = f.get('attributes') or {}
        p = pt(f)
        if not p or not a.get('building'):
            continue
        url = str(a.get('library_url') or '')
        if not url.startswith('https://'):
            url = ''
        lib.append([round(p[0]), round(p[1]), clean(a['building']), clean(a.get('address') or ''), clean(str(a.get('zip_code') or '')[:5]), clean(a.get('phone_number') or ''), url])
    for f in sites:
        a = f.get('attributes') or {}
        p = pt(f)
        if not p or not a.get('park_name'):
            continue
        kind = 1 if a.get('program_type') == 'OLDER_ADULT_CENTER' else 0
        rec.append([round(p[0]), round(p[1]), clean(a['park_name']), kind, 1 if str(a.get('gym') or '').upper() == 'Y' else 0])
    moved = [0, 0]
    if footprints:
        grid = FootGrid(footprints)
        for k, rows in enumerate((lib, rec)):
            for r in rows:
                x, z, m = grid.step_out(r[0], r[1])
                if m:
                    r[0], r[1] = round(x), round(z); moved[k] += 1
    return {'lib': sorted(lib, key=lambda r: r[2]), 'rec': sorted(rec, key=lambda r: r[2])}, moved


def main():
    libs = json.load(open(os.path.join(RAW, 'libraries.json')))['features']
    sites = json.load(open(os.path.join(RAW, 'ppr_sites.json')))['features']
    out, moved = bake(libs, sites, load_footprints())
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
    os.replace(OUT + '.tmp', OUT)
    print(f"wrote {len(out['lib'])} libraries ({moved[0]} stepped out), {len(out['rec'])} centers ({moved[1]} stepped out) -> civic.json ({os.path.getsize(OUT):,} bytes)")


if __name__ == '__main__':
    sys.exit(main())
