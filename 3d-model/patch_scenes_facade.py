#!/usr/bin/env python3
"""Tier-1 facade pass, stage 3: write the joined OPA attributes and sampled roof
palette indices into the scene files, and publish the roof palette for build.py.

  scene.json / scene_wide.json / scene_south.json buildings gain:
    b['fa'] = [use, mat, era, stories]   (opa_join.py codes)
    b['rp'] = roof palette index 0..29   (roof_colors.py)
  facade_palette.json (committed, embedded by build.py as FACADE_PAL):
    {"roof": [[r,g,b] x30]}  raw sampled sRGB — the app divides for the legacy
                             color pipeline (calibrate ROOF_DIV by swatch).

pack_wide.py / pack_city.py read fa/rp (and their LUT equivalents) into the b64
records. Plain python3; idempotent."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

pal = json.load(open('lidar_cache/roof_palette.json'))
json.dump({'roof': pal}, open('facade_palette.json', 'w'))
print('facade_palette.json written (30 colors)')

stats = {}
for scene, tag in (('scene.json', 'core'), ('scene_wide.json', 'wide'), ('scene_south.json', 'south')):
    opa = json.load(open(f'lidar_cache/opa_{tag}.json'))
    roof = json.load(open(f'lidar_cache/roof_{tag}.json'))
    d = json.load(open(scene))
    n_fa = n_rp = 0
    for i, b in enumerate(d['buildings']):
        k = str(i)
        b.pop('fa', None); b.pop('rp', None)
        if k in opa:
            b['fa'] = opa[k]
            n_fa += 1
        if k in roof:
            b['rp'] = roof[k]
            n_rp += 1
    with open(scene + '.tmp', 'w') as f:
        json.dump(d, f, separators=(',', ':'))
    os.replace(scene + '.tmp', scene)
    stats[tag] = {'buildings': len(d['buildings']), 'opa': n_fa, 'roof': n_rp}
    print(f'{scene}: {n_fa} fa, {n_rp} rp of {len(d["buildings"])}')
city_opa = json.load(open('lidar_cache/opa_city.json'))
city_roof = json.load(open('lidar_cache/roof_city.json'))
stats['city_ways'] = {'opa': len(city_opa), 'roof': len(city_roof)}
rep = json.load(open('lidar_report.json')) if os.path.exists('lidar_report.json') else {}
rep['tier1'] = {'coverage': stats, 'roof_palette': pal}
json.dump(rep, open('lidar_report.json', 'w'), indent=1)
print('lidar_report.json updated')
print('done')
