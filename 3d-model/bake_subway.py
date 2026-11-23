#!/usr/bin/env python3
"""Round 267 (Mike: "The train station is missing from 2nd and market. I would like all underground Market Frankford
line, Broad Street Line, Patco stations to be included"): subway.json, the underground stations of the L (the Market-
Frankford Line's Market Street subway), the B (the Broad Street Line and the Broad-Ridge Spur) and PATCO, their street
entrances and their timetables, inlined by build.py as SUBWAY.

Inputs: lidar_cache/subway_raw/osm_subway.json (fetch_subway.py: OSM's stations and subway entrances, ODbL),
lidar_cache/septa_raw/gtfs_public.zip (fetch_septa_stops.py: SEPTA's GTFS, google_bus.zip carries L1, B1, B2, B3) and
lidar_cache/patco_raw/PATCO_GTFS.zip (fetch_patco.py).

Which stations are underground: every B station but Fern Rock (at grade); the L stations on Market Street from 2nd to
34th (the El rises west of 34th and north of 2nd); PATCO's five on Locust and Market Streets and Franklin Square, and
Camden's City Hall under Broadway. An entrance belongs to the nearest underground station within ENT_R (an entrance of an
elevated station or the trolley tunnel finds none and is dropped); one within 12 m of Dilworth Park's two glass headhouses
is left out, since the page already builds them.

Timetables: each station's departures for a weekday, a Saturday and a Sunday of the feeds' current calendars, by route and
headsign, minutes after midnight (GTFS times past 24:00 kept past 1440), delta-coded.

Output: {v, src, baked, days: {wk, sa, su: the dates}, st: [{n, net, ln, x, z, d: [[route, headsign, {wk, sa, su}]]}],
en: [[x, z, station, both kerbs]]}, coordinates in the scene frame to 0.1 m."""
import csv
import datetime
import io
import json
import math
import os
import sys
import zipfile

import philly_frame

HERE = os.path.dirname(os.path.abspath(__file__))
OSM = os.path.join(HERE, 'lidar_cache', 'subway_raw', 'osm_subway.json')
SEPTA = os.path.join(HERE, 'lidar_cache', 'septa_raw', 'gtfs_public.zip')
PATCO = os.path.join(HERE, 'lidar_cache', 'patco_raw', 'PATCO_GTFS.zip')
OUT = os.path.join(HERE, 'subway.json')
ENT_R = 260.0
MERGE_R = 80.0
GTFS_R = 220.0
HEADHOUSES = [(-1713.6, -793.5), (-1716.0, -777.6), (-1682.7, -860.3)]   # app.js CH_HEADHOUSE: Dilworth Park's glass headhouses
PATCO_UNDER = {'15th-16th & Locust', '12th-13th & Locust', '9th-10th & Locust', '8th & Market', 'Franklin Square', 'City Hall'}
SEPTA_ROUTES = {'L1': 'L', 'B1': 'B', 'B2': 'B', 'B3': 'B'}
HEAD_SHORT = {   # the headsigns as a rider reads them on the platform
    'Frankford Transit Center': 'Frankford', '69th St Transit Center': '69th Street', 'Fern Rock Transit Center': 'Fern Rock',
    'NRG Station': 'NRG', 'Olney Transit Center': 'Olney', '8th-Market': '8th and Market',
}


def xz(lat, lon):
    return philly_frame.to_scene(lat, lon) if hasattr(philly_frame, 'to_scene') else (
        (lon - philly_frame.LON0) * 111320 * math.cos(math.radians(philly_frame.LAT0)), -(lat - philly_frame.LAT0) * 110574)


def gtfs(path, inner=None):
    z = zipfile.ZipFile(path)
    if inner:
        z = zipfile.ZipFile(io.BytesIO(z.read(inner)))
    return lambda n: list(csv.DictReader(io.TextIOWrapper(z.open(n), 'utf-8-sig')))


def ref_days(rd):
    """A weekday, a Saturday and a Sunday on which the feed's regular services all run: the first of each kind from
    today (or the calendar's start) that no calendar_dates exception touches."""
    cal = rd('calendar.txt')
    try:
        ex = {r['date'] for r in rd('calendar_dates.txt')}
    except KeyError:
        ex = set()
    start = max(datetime.date.today(), min(datetime.datetime.strptime(c['start_date'], '%Y%m%d').date() for c in cal))
    want, out = {'wk': (0, 1, 2, 3, 4), 'sa': (5,), 'su': (6,)}, {}
    for k, wds in want.items():
        d = start
        for _ in range(60):
            if d.weekday() in wds and d.strftime('%Y%m%d') not in ex and d.weekday() != 4:   # never a Friday: some lines run late
                break
            d += datetime.timedelta(days=1)
        out[k] = d
    return out


def services_on(rd, day):
    ds = day.strftime('%Y%m%d')
    wd = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')[day.weekday()]
    on = {c['service_id'] for c in rd('calendar.txt') if c[wd] == '1' and c['start_date'] <= ds <= c['end_date']}
    try:
        for r in rd('calendar_dates.txt'):
            if r['date'] == ds:
                (on.add if r['exception_type'] == '1' else on.discard)(r['service_id'])
    except KeyError:
        pass
    return on


def minutes(t):
    h, m, s = (int(v) for v in t.split(':'))
    return h * 60 + m + (1 if s >= 30 else 0)


def timetable(rd, routes_ok, label):
    """{stop_id: {(route, headsign): {day: [minutes]}}} for the routes routes_ok answers True for, and the reference days"""
    days = ref_days(rd)
    routes = {r['route_id']: r for r in rd('routes.txt') if routes_ok(r)}
    trips = {t['trip_id']: t for t in rd('trips.txt') if t['route_id'] in routes}
    svc = {k: services_on(rd, d) for k, d in days.items()}
    last = {}
    for r in rd('stop_times.txt'):
        if r['trip_id'] in trips:
            last[r['trip_id']] = max(last.get(r['trip_id'], -1), int(r['stop_sequence']))
    out = {}
    for r in rd('stop_times.txt'):
        t = trips.get(r['trip_id'])
        if not t or not r['departure_time'] or int(r['stop_sequence']) == last[r['trip_id']]:   # a trip's last stop is an arrival
            continue
        for k, on in svc.items():
            if t['service_id'] in on:
                key = (label(routes[t['route_id']]), HEAD_SHORT.get(t['trip_headsign'], t['trip_headsign']))
                out.setdefault(r['stop_id'], {}).setdefault(key, {}).setdefault(k, []).append(minutes(r['departure_time']))
    return out, days


def main():
    for p in (OSM, SEPTA, PATCO):
        if not os.path.exists(p):
            sys.exit('bake_subway: missing %s (run fetch_subway.py, fetch_septa_stops.py, fetch_patco.py)' % p)
    els = json.load(open(OSM))['elements']
    srd = gtfs(SEPTA, 'google_bus.zip')
    prd = gtfs(PATCO)
    s_tt, s_days = timetable(srd, lambda r: r['route_id'] in SEPTA_ROUTES, lambda r: r['route_short_name'])
    p_tt, p_days = timetable(prd, lambda r: True, lambda r: 'PATCO')
    s_stops = {s['stop_id']: s for s in srd('stops.txt') if s['stop_id'] in s_tt}
    p_stops = {s['stop_id']: s for s in prd('stops.txt') if s['stop_id'] in p_tt}

    # the OSM stations, the SEPTA ones within MERGE_R of each other one station (OSM maps 8th Street and 8th & Market
    # 25 m apart); each GTFS stop then belongs to its nearest station of its network within GTFS_R, so a station on
    # Market Street never takes the Broad Street Line's stops a block away
    raw = []
    for e in els:
        t = e.get('tags', {})
        if t.get('railway') in ('subway_entrance', 'train_station_entrance') or not t.get('name'):
            continue
        lat, lon = (e['lat'], e['lon']) if 'lat' in e else (e['center']['lat'], e['center']['lon'])
        x, z = xz(lat, lon)
        patco = 'PATCO' in (t.get('network', '') + t.get('operator', ''))
        dup = [r for r in raw if r[3] == patco and math.hypot(r[1] - x, r[2] - z) < MERGE_R]
        if dup:
            if '&' in t['name'] and '&' not in dup[0][0]:
                dup[0][0] = t['name']   # the name riders use ('8th & Market', not OSM's second node '8th Street')
            continue
        raw.append([t['name'], x, z, patco, e])
    own = {}
    for stops, patco in ((s_stops, False), (p_stops, True)):
        for sid, s in stops.items():
            sx, sz = xz(float(s['stop_lat']), float(s['stop_lon']))
            best, bi = GTFS_R, -1
            for i, r in enumerate(raw):
                if r[3] == patco and math.hypot(r[1] - sx, r[2] - sz) < best:
                    best, bi = math.hypot(r[1] - sx, r[2] - sz), i
            if bi >= 0:
                own.setdefault(bi, []).append(sid)

    stations = []
    for ri, (name, x, z, patco, e) in enumerate(raw):
        t = e['tags']
        sids = own.get(ri, [])
        market = x > -4500 and -1300 < z < 0 and x < 300   # the L's Market Street subway, 34th to 2nd
        if patco:
            if name not in PATCO_UNDER or (name == 'City Hall' and x < 1000):
                continue
            tt, lines = p_tt, ['P']
            if name == 'City Hall':
                name = 'City Hall, Camden'
        else:
            routes = {k[0] for sid in sids for k in s_tt[sid]}
            lines = sorted({SEPTA_ROUTES[r] for r in routes}, key='LB'.index)
            if not lines and market:
                lines = ['L']   # 11th Street: in OSM, its entrances on the street, no L1 trip stopping in SEPTA's current timetable
            under = ('B' in lines and 'Fern Rock' not in name) or ('L' in lines and market)
            if not under:
                continue
            tt = s_tt
        dirs = {}
        for sid in sids:
            for key, byday in tt[sid].items():
                if not patco and SEPTA_ROUTES.get(key[0]) not in lines:
                    continue
                d = dirs.setdefault(key, {})
                for k, v in byday.items():
                    d.setdefault(k, set()).update(v)
        D = []
        for (route, head), byday in sorted(dirs.items()):
            row = {}
            for k in ('wk', 'sa', 'su'):
                v = sorted(byday.get(k, ()))
                row[k] = [v[0]] + [b - a for a, b in zip(v, v[1:])] if v else []
            D.append([route, head, row])
        stations.append({'n': name, 'net': 'PATCO' if patco else 'SEPTA', 'ln': lines, 'x': round(x, 1), 'z': round(z, 1), 'd': D})
    # the station records' names, as a rider knows them
    seen = {}
    for s in stations:
        seen.setdefault(s['n'], []).append(s)
    for n, ss in seen.items():
        if len(ss) > 1:
            for s in ss:
                s['n'] = n + (' (' + '/'.join(s['ln']) + ')' if s['net'] == 'SEPTA' else ' (PATCO)')
    # entrances: to the nearest underground station within ENT_R; merged within 3 m; none on Dilworth's headhouses
    ents, dropped = [], {'far': 0, 'headhouse': 0, 'dup': 0}
    for e in els:
        t = e.get('tags', {})
        if t.get('railway') not in ('subway_entrance', 'train_station_entrance'):
            continue
        x, z = xz(e['lat'], e['lon'])
        best, bi = ENT_R, -1
        for i, s in enumerate(stations):
            d = math.hypot(s['x'] - x, s['z'] - z)
            if d < best:
                best, bi = d, i
        if bi < 0:
            dropped['far'] += 1
            continue
        if any(math.hypot(x - hx, z - hz) < 12 for hx, hz in HEADHOUSES):
            dropped['headhouse'] += 1
            continue
        if any(math.hypot(x - a[0], z - a[1]) < 3 for a in ents):
            dropped['dup'] += 1
            continue
        ents.append([round(x, 1), round(z, 1), bi, 0])
    # a station OSM maps no entrance for (Olney, Hunting Park, Erie, Oregon on Broad Street) is given one on each sidewalk
    # of the street over it, at the station's own point: the page puts a [x, z, station, 1] entrance on both kerbs
    have = {e[2] for e in ents}
    for i, s in enumerate(stations):
        if i not in have:
            ents.append([s['x'], s['z'], i, 1])
    stations_used = {e[2] for e in ents}
    out = {'v': 1, 'src': 'OpenStreetMap (ODbL) stations and subway entrances; SEPTA GTFS (L1, B1, B2, B3) and PATCO GTFS timetables',
           'baked': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
           'days': {'septa': {k: d.isoformat() for k, d in s_days.items()}, 'patco': {k: d.isoformat() for k, d in p_days.items()}},
           'st': stations, 'en': ents}
    txt = json.dumps(out, separators=(',', ':'))
    open(OUT, 'w').write(txt)
    for i, s in enumerate(stations):
        print('%-32s %-6s %-5s %7.1f %7.1f  entrances %2d  dirs %s' % (s['n'], s['net'], ''.join(s['ln']), s['x'], s['z'], sum(1 for e in ents if e[2] == i),
              ', '.join('%s %s %d' % (r, h, len(d['wk'])) for r, h, d in s['d'])))
    print('subway.json: %d stations (%d with an entrance), %d entrances, dropped %s, %d bytes' % (len(stations), len(stations_used), len(ents), dropped, len(txt)))


if __name__ == '__main__':
    main()
