#!/usr/bin/env python3
"""lidar_cache/landmarks_raw/{poly,points}.geojson -> landmarks.json : the City basemap's
named places in the local frame for the search index (Round 78).
  {"names": ["Julia R. Masterman School", ...],      # one string per entry, in entry order
   "l": [nameIdx, x, z, cls, ...]}                     # whole metres; cls indexes LM_KIND in app.js
Rows: archived rows, PUBLIC_ = N rows and Neighborhood rows (the neighborhoods are in
places.json) are dropped, as are the utility yards, industrial sites, communication towers,
plain retail, housing and parking lots; the rest is classed by SUBTYPE (CLS below). TYPE is a
small integer in the city's file and LABEL a Y/N flag, so only SUBTYPE carries the class.
Sites: 3,796 polygons have no NAME and belong to a PARENT_NAME (the many parcels of a park or
a recreation center), so the site key is NAME, else PARENT_NAME; a parent's position is the
area-weighted mean of its members' centroids (a university lands mid-campus), and a row with
its own NAME and a different PARENT_NAME emits itself and feeds its parent. A name that
recurs across the city ("US Post Office") stays one site while the members lie within 400 m
of it and starts another beyond that; entries are sorted largest site first, so the app's
dedupe on name keeps the biggest. Names lose their dashes and middots (the HUD rule).
Frame: philly_frame.py (the scene's own projection); clipped to the far-ring box.
Run with plain python3; bake() is pure so tests/test_landmarks_bake.py can feed it fixtures."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'landmarks_raw')
OUT = os.path.join(HERE, 'landmarks.json')
from philly_frame import to_xz   # the one scene frame

CITY = (-12000, 16500, -21700, 9700)   # pack_city.py's box: x0, x1, z0, z1
SPLIT_M = 400.0                         # members of one name farther apart than this are separate sites
KINDS = ['school', 'college', 'worship', 'hospital', 'park', 'rec', 'cemetery', 'museum', 'site', 'venue',
         'civic', 'station', 'bridge', 'building', 'nature']   # = LM_KIND in app.js
CLS = {}
for _cls, _subs in [
    (0, ['Elementary School', 'Middle School', 'High School', 'Other Education', 'Day Care / Pre-Kindergarten']),
    (1, ['College / University']),
    (2, ['Place of Worship', 'Religious']),
    (3, ['Hospital / Emergency Medical Center', 'Medical Office', 'Other Health / Medical', 'Veterinary Hospital / Clinic']),
    (4, ['Park', 'Playground', 'Open Space / Natural Area', 'Community Garden', 'Arboretum / Botanical Garden', 'Golf Course',
         'Pool / Sprayground', 'Trailhead']),
    (5, ['Community / Recreation Center', 'Athletic Facility']),
    (6, ['Cemetery']),
    (7, ['Museum', 'Library', 'Zoo']),
    (8, ['Historic Site', 'Fountain / Monument / Statue', 'Mural']),
    (9, ['Indoor Entertainment Venue', 'Outdoor Entertainment Venue', 'Sports Arena / Stadium', 'Convention Center', 'Casino',
         'Other Public Attraction / Point of Interest']),
    (10, ['Fire / EMS', 'Law Enforcement', 'Other Emergency Services', 'Municipal Government', 'State Government', 'US Government',
          'Other Government / Military', 'DOD / Military', 'Post Office', 'Correctional Facility']),
    (11, ['Railroad Station', 'Subway Station', 'Bus Station', 'Airport Terminal', 'Airport / Airfield', 'Pier / Dock / Port',
          'Helipad / Heliport / Helispot']),
    (12, ['Bridge', 'Tunnel']),
    (13, ['Named Building', 'Shopping Mall / Complex', 'Office Park', 'Hotel / Motel', 'Dormitory', 'Planned Community']),
    (14, ['Lake / Pond / Reservoir', 'Island', 'Cape', 'Dam / Dike / Levee', 'Wetland / Swamp', 'Other Hydrography', 'Other Land', 'Cave']),
]:
    for _s in _subs:
        CLS[_s.lower()] = _cls
DASHES = re.compile('[‒–—―·•]')


def clean(s):
    if not s:
        return ''
    s = DASHES.sub(', ', str(s))
    s = re.sub(r'\s+,', ',', s)
    s = re.sub(r',(\s*,)+', ',', s)
    return re.sub(r'\s+', ' ', s).strip(' ,')


def ring_area_centroid(pts):
    a = cx = cz = 0.0
    for i in range(len(pts)):
        u, v = pts[i], pts[(i + 1) % len(pts)]
        w = u[0] * v[1] - v[0] * u[1]
        a += w
        cx += (u[0] + v[0]) * w
        cz += (u[1] + v[1]) * w
    a *= 0.5
    if abs(a) < 1e-6:
        xs = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        return 0.0, sum(xs) / len(xs), sum(zs) / len(zs)
    return abs(a), cx / (6 * a), cz / (6 * a)


def geom_spot(g):
    """(area m2, x, z) of a feature: the largest ring's centroid, or the point."""
    if not g:
        return None
    t = g.get('type')
    if t == 'Point':
        lon, lat = g['coordinates'][:2]
        x, z = to_xz(lat, lon)
        return 0.0, x, z
    polys = g['coordinates'] if t == 'MultiPolygon' else [g['coordinates']] if t == 'Polygon' else []
    best = None
    for poly in polys:
        if not poly or len(poly[0]) < 3:
            continue
        ring = [to_xz(lat, lon) for lon, lat in poly[0]]
        a, cx, cz = ring_area_centroid(ring)
        if best is None or a > best[0]:
            best = (a, cx, cz)
    return best


class Site:
    __slots__ = ('name', 'cls', 'wsum', 'wx', 'wz', 'n', 'mx', 'mz')

    def __init__(self, name, cls):
        self.name, self.cls = name, cls
        self.wsum = self.wx = self.wz = 0.0
        self.n = 0
        self.mx = self.mz = 0.0

    def add(self, a, x, z):
        w = max(a, 1.0)
        self.wsum += w
        self.wx += w * x
        self.wz += w * z
        self.n += 1
        self.mx += x
        self.mz += z

    @property
    def spot(self):
        return self.wx / self.wsum, self.wz / self.wsum


def bake(features):
    sites, by_name = [], {}

    def site_for(name, cls, x, z):
        key = name.lower()
        for s in by_name.get(key, ()):
            sx, sz = s.spot
            if (sx - x) ** 2 + (sz - z) ** 2 <= SPLIT_M ** 2:
                return s
        s = Site(name, cls)
        sites.append(s)
        by_name.setdefault(key, []).append(s)
        return s

    for f in features or []:
        p = f.get('properties') or {}
        if p.get('ARCHIVE_DATE') or str(p.get('PUBLIC_') or '').strip().upper() == 'N':
            continue
        sub = str(p.get('SUBTYPE') or '').strip().lower()
        cls = CLS.get(sub)
        if cls is None:
            continue
        spot = geom_spot(f.get('geometry'))
        if spot is None:
            continue
        a, x, z = spot
        if not (CITY[0] <= x <= CITY[1] and CITY[2] <= z <= CITY[3]):
            continue
        name, parent = clean(p.get('NAME')), clean(p.get('PARENT_NAME'))
        if name:
            site_for(name, cls, x, z).add(a, x, z)
        if parent and parent.lower() != name.lower():
            pcls = CLS.get(str(p.get('PARENT_SUBTYPE') or '').strip().lower(), cls)
            site_for(parent, pcls, x, z).add(a, x, z)
    sites.sort(key=lambda s: (-s.wsum, s.name.lower()))
    names, flat = [], []
    for s in sites:
        x, z = s.spot
        names.append(s.name)
        flat += [len(names) - 1, int(round(x)), int(round(z)), s.cls]
    return {'names': names, 'l': flat}


def main():
    feats = []
    for key in ('poly', 'points'):
        feats.extend(json.load(open(os.path.join(RAW, key + '.geojson')))['features'])
    out = bake(feats)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), ensure_ascii=False)
    counts = [0] * len(KINDS)
    for i in range(3, len(out['l']), 4):
        counts[out['l'][i]] += 1
    print(f"{len(out['names'])} places from {len(feats)} rows, landmarks.json {os.path.getsize(OUT) / 1e3:.1f} KB", flush=True)
    print('  ' + ', '.join(f'{k} {n}' for k, n in zip(KINDS, counts)), flush=True)


if __name__ == '__main__':
    main()
