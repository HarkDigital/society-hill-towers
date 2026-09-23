#!/usr/bin/env python3
"""Bake SEPTA's stops into septa_stops.json for the page (Round 133).

Inputs (fetch_septa_stops.py): lidar_cache/septa_raw/gtfs_public.zip and station_id_name.csv.
  bus   every bus and trolley stop (route types 3 and 0; the subway, which Mike took off the map as
        underground, stays out) inside the flight limit (city_limit.json's bound): its GTFS stop id,
        which is the id the BusSchedules API takes, its scene position to 0.5 m, its name without the
        near-side / far-side suffix, and the routes that serve it.
  rail  every Regional Rail station inside the flight limit, named as the Arrivals API names it
        (station_id_name.csv, matched on the GTFS stop id: GTFS says "Gray 30th St Station", the API
        "30th Street Station").
Output: {"src", "bus": {"id", "x", "z", "n", "r"}, "rail": {"id", "x", "z", "n", "d"}}, x and z in 0.5 m units; a station's
n is the board's key, d the name a rider knows (the API still says "Market East" for Jefferson Station).
Run with plain python3."""
import csv, io, json, os, re, sys, zipfile
from philly_frame import to_xz
from bake_markers import FootGrid, load_footprints

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'septa_raw')
OUT = os.path.join(HERE, 'septa_stops.json')


def pip(x, z, poly):
    ins = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]; xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            ins = not ins
        j = i
    return ins


def rows(zz, name):
    return list(csv.DictReader(io.TextIOWrapper(zz.open(name), 'utf-8-sig')))


def clean(n):
    n = re.sub(r'\s*-\s*(FS|NS|MBFS|MBNS|MB|FSL|NSL|MBL)\s*$', '', n.strip(), flags=re.I)   # far side, near side, mid block
    return re.sub(r'\s+', ' ', n)


def main():
    bound = json.load(open(os.path.join(HERE, 'city_limit.json')))['bound']
    outer = zipfile.ZipFile(os.path.join(RAW, 'gtfs_public.zip'))
    bus = zipfile.ZipFile(io.BytesIO(outer.read('google_bus.zip')))
    rail = zipfile.ZipFile(io.BytesIO(outer.read('google_rail.zip')))
    rtype = {r['route_id']: (r['route_type'], r['route_short_name'] or r['route_id']) for r in rows(bus, 'routes.txt')}
    served = {}
    for r in rows(bus, 'route_stops.txt'):
        t, short = rtype.get(r['route_id'], ('3', r['route_id']))
        if t in ('0', '3'):
            served.setdefault(r['stop_id'], set()).add(short)
    def rkey(s):
        m = re.match(r'([A-Za-z]*)(\d*)', s)
        return (m.group(1), int(m.group(2)) if m.group(2) else 0, s)
    B = {'id': [], 'x': [], 'z': [], 'n': [], 'r': []}
    for s in rows(bus, 'stops.txt'):
        if s['stop_id'] not in served or s.get('location_type') not in ('', '0', None):
            continue
        x, z = to_xz(float(s['stop_lat']), float(s['stop_lon']))
        if not pip(x, z, bound):
            continue
        B['id'].append(int(s['stop_id'])); B['x'].append(round(x * 2)); B['z'].append(round(z * 2))
        B['n'].append(clean(s['stop_name'])); B['r'].append(','.join(sorted(served[s['stop_id']], key=rkey)))
    names = {}
    for r in csv.reader(open(os.path.join(RAW, 'station_id_name.csv'))):
        if r and r[0].strip().isdigit():
            names[r[0].strip()] = r[1].strip()
    # the API's names are the boards' keys; riders know some stations by other names today
    DISPLAY = {'Market East': 'Jefferson Station', 'Temple U': 'Temple University', 'Fern Rock TC': 'Fern Rock Transportation Center',
               'Holmesburg Jct': 'Holmesburg Junction', 'Wayne Jct': 'Wayne Junction', 'Mt Airy': 'Mount Airy', 'St. Martins': "St. Martin's",
               'North Broad St': 'North Broad', '49th St': '49th Street', 'Eastwick Station': 'Eastwick'}
    R = {'id': [], 'x': [], 'z': [], 'n': [], 'd': []}
    for s in rows(rail, 'stops.txt'):
        nm = names.get(s['stop_id'])
        if not nm:
            continue
        x, z = to_xz(float(s['stop_lat']), float(s['stop_lon']))
        if not pip(x, z, bound):
            continue
        R['id'].append(int(s['stop_id'])); R['x'].append(round(x * 2)); R['z'].append(round(z * 2)); R['n'].append(nm); R['d'].append(DISPLAY.get(nm, nm))
    # a stop or station point inside one of the page's footprints is stepped 2.5 m out past the wall, so its pin
    # stands in the open instead of hiding behind its own building (review, Sep 22; the markers' FootGrid)
    grid = FootGrid(load_footprints())
    moved = 0
    for P in (B, R):
        for i in range(len(P['id'])):
            x, z, m = grid.step_out(P['x'][i] / 2, P['z'][i] / 2)
            if m:
                P['x'][i], P['z'][i] = round(x * 2), round(z * 2); moved += 1
    print(f'{moved} stop and station points stepped out of a footprint')
    out = {'src': 'SEPTA GTFS (github.com/septadev/GTFS) and the Arrivals station list; scene frame, 0.5 m units',
           'bus': B, 'rail': R}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print(f"wrote {len(B['id'])} bus stops, {len(R['id'])} rail stations -> septa_stops.json ({os.path.getsize(OUT):,} bytes)")


if __name__ == '__main__':
    sys.exit(main())
