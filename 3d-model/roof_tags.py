#!/usr/bin/env python3
"""OpenStreetMap roof:shape tags -> lidar_cache/roof_shapes.json, the roof-form source the
packers fall back to where the LiDAR pass (fetch_lidar_roofs.py -> lidar_city_roofs.json)
has not resolved a building. Scans osm_city_raw.json, osm_wide_raw.json and
osm_south_raw.json:
  byId:  {way id: form}            form 0 flat, 1 gable (gabled, gambrel, saltbox
                                   variants), 2 hip (hipped, half-hipped, pyramidal,
                                   mansard), 3 skillion
  ways:  [[cx, cz, way id], ...]   centroid (model frame) of EVERY building way in the
                                   wide and south dumps, so pack_wide.py can attach way
                                   ids (and with them both roof sources) to scene_wide /
                                   scene_south buildings, which carry no ids
Plain python3; the far-ring dump is 450 MB and takes a minute to load."""
import json
from philly_frame import LON0, LAT0, KX, KZ

FORM = {'flat': 0, 'gabled': 1, 'gambrel': 1, 'saltbox': 1, 'double_saltbox': 1, 'quadruple_saltbox': 1, 'round': 1,
        'hipped': 2, 'half-hipped': 2, 'pyramidal': 2, 'mansard': 2, 'skillion': 3}
byId, ways = {}, []
for name, keep_centroids in (('osm_wide_raw.json', True), ('osm_south_raw.json', True), ('osm_city_raw.json', False)):
    try:
        raw = json.load(open(name))
    except FileNotFoundError:
        print('missing', name, flush=True); continue
    nodes = {el['id']: ((el['lon'] - LON0) * KX, (LAT0 - el['lat']) * KZ) for el in raw['elements'] if el.get('type') == 'node'}
    n_tag = 0
    for el in raw['elements']:
        t = el.get('tags') or {}
        if el.get('type') != 'way' or 'building' not in t: continue
        rs = t.get('roof:shape')
        if rs in FORM:
            byId[str(el['id'])] = FORM[rs]; n_tag += 1
        if keep_centroids:
            pts = [nodes[n] for n in el.get('nodes', []) if n in nodes]
            if len(pts) >= 3:
                ways.append([round(sum(p[0] for p in pts) / len(pts), 1), round(sum(p[1] for p in pts) / len(pts), 1), el['id']])
    print(f'{name}: {n_tag} roof:shape tags', flush=True)
    del raw, nodes
json.dump({'byId': byId, 'ways': ways}, open('lidar_cache/roof_shapes.json', 'w'), separators=(',', ':'))
from collections import Counter
print('roof_shapes.json:', len(byId), 'tagged ways', Counter(byId.values()), ';', len(ways), 'wide/south way centroids', flush=True)
