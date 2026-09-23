#!/usr/bin/env python3
"""PATCO's static GTFS + its OSM track -> patco.json (Round 141): what the page needs to run SCHEDULED
(not live) PATCO trains over the Ben Franklin Bridge.

PATCO publishes no live positions (no GTFS-realtime, no train tracker), so the page runs its trains from the
timetable and labels them scheduled. They are drawn only where the line is above ground: the Philadelphia portal
near 5th and Race, the approach, the span, the Camden approach and the Camden portal. The tunnels (under Race and
8th Streets, under Camden to City Hall and Broadway) ride along as geometry so a train's clock runs through them,
but a hidden segment is never drawn (the Round 20 rule: nothing underground).

Inputs (fetch_patco.py): lidar_cache/patco_raw/PATCO_GTFS.zip and lidar_cache/patco_raw/osm_patco.json.
Output (one line):
  {"src", "feed": {"v", "from", "to", "tz"}, "baked",
   "chains": [{"d": direction_id, "h": headsign, "trk": "south"|"north",
               "p": [[x, z], ...],             # 0.1 m, ordered PHILADELPHIA -> CAMDEN on both chains
               "f": [flags per segment],       # 1 tunnel, 2 bridge, 4 OSM covered, 8 the passage through an anchorage
               "s": {stop_id: metres along}, "vis": [s0, s1]}],   # vis: portal to portal
   "svc": [service_id, ...],
   "trips": [[[tPhl, tCam(, code)], ...] per direction_id 0, 1] per service,
            # seconds after the service day's midnight, may exceed 86400; tPhl at the Philadelphia-side stop,
            # tCam at the Camden-side one; code bit 1: the Philadelphia stop is 8th and Market (Franklin Square
            # skipped), bit 2: the Camden stop is Broadway (City Hall skipped)
   "days": [service bitmask per date from feed.from to feed.to],
   "week": [bitmask Mon..Sun], the plain weekly pattern for a date past the feed}
The calendar: calendar.txt, then calendar_dates, then a swap-day repair (a service ADDED on a date that shares over
a quarter of its trips with a base service running that date replaces it: feed 19's Bike MS day, Sep 26 2026, whose
removal names 194 Sunday instead of 194 Saturday, so a literal reading runs both). Plain python3 (stdlib)."""
import csv
import datetime
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict

import zipfile
from philly_frame import to_xz

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'patco_raw')
GTFS_ZIP = os.path.join(RAW, 'PATCO_GTFS.zip')
OSM = os.path.join(RAW, 'osm_patco.json')
OUT = os.path.join(HERE, 'patco.json')

TOL = 1.5                  # Douglas-Peucker tolerance, as bake_rail.py
MARGIN = 150.0             # chain kept this far past 8th and Market and past Broadway (a 6-car consist is 124 m)
ANCHOR_PASSAGE = 100.0     # a covered bridge way shorter than this is the passage through an anchorage
PHL_STOPS = ('10', '11')   # Franklin Square, then 8th and Market: the Philadelphia-side bracket, in preference order
CAM_STOPS = ('9', '8')     # City Hall, then Broadway: the Camden-side bracket
END_W, END_E = '11', '8'   # the chain runs 8th and Market -> Broadway (plus MARGIN)
BFB_A, BFB_B = (400.0, -940.0), (1360.0, -722.0)   # app.js:2998, the modelled bridge's anchorages
DUP_SHARE = 0.25           # two services active on one date sharing more than this share of trips: a swap day


# ------------------------------------------------------------------ geometry
def simplify(pts, tol):
    """Douglas-Peucker on an open polyline (bake_rail.py's, verbatim)."""
    if len(pts) <= 2:
        return pts
    a, b = pts[0], pts[-1]
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = (dx * dx + dz * dz) ** 0.5 or 1e-9
    best, bi = -1.0, -1
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = abs((p[0] - a[0]) * dz - (p[1] - a[1]) * dx) / L
        if d > best:
            best, bi = d, i
    if best > tol:
        return simplify(pts[:bi + 1], tol)[:-1] + simplify(pts[bi:], tol)
    return [a, b]


def nkey(g):
    return (round(g['lat'], 7), round(g['lon'], 7))


def way_flags(w):
    t = w.get('tags') or {}
    L = sum(math.dist(to_xz(a['lat'], a['lon']), to_xz(b['lat'], b['lon'])) for a, b in zip(w['geometry'], w['geometry'][1:]))
    tunnel = t.get('tunnel') not in (None, 'no')
    covered = t.get('covered') not in (None, 'no')
    try:
        lay = int(t.get('layer') or 0)
    except ValueError:
        lay = 0
    bridge = (t.get('bridge') not in (None, 'no') or lay >= 1) and not tunnel
    passage = covered and bridge and L < ANCHOR_PASSAGE
    return (1 if tunnel else 0) | (2 if bridge else 0) | (4 if covered else 0) | (8 if passage else 0)


def build_chains(elements):
    """The two main tracks as ordered chains (west end first), stitched by shared end nodes.
    Returns [{'ways': [(way, forward_bool)], 'dir': +1 if travel runs west->east else -1}]."""
    main = [w for w in elements if w.get('type') == 'way' and w.get('geometry')
            and not (w.get('tags') or {}).get('service') and (w.get('tags') or {}).get('railway') == 'subway']
    at = defaultdict(list)
    for w in main:
        at[nkey(w['geometry'][0])].append(w)
        at[nkey(w['geometry'][-1])].append(w)
    bad = {k: len(v) for k, v in at.items() if len(v) > 2}
    if bad:
        sys.exit(f'FATAL: {len(bad)} junction nodes of degree > 2 on the main tracks after dropping service ways')
    ends = [k for k, v in at.items() if len(v) == 1]
    if len(ends) != 4:
        sys.exit(f'FATAL: expected 4 track ends (two chains), found {len(ends)}')
    used, chains = set(), []
    for start in sorted(ends, key=lambda k: to_xz(*k)[0]):     # west ends first
        if at[start][0]['id'] in used:
            continue
        seq, node = [], start
        while True:
            nxt = [w for w in at[node] if w['id'] not in used]
            if not nxt:
                break
            w = nxt[0]
            used.add(w['id'])
            fwd = nkey(w['geometry'][0]) == node
            seq.append((w, fwd))
            node = nkey(w['geometry'][-1] if fwd else w['geometry'][0])
        if to_xz(*node)[0] < to_xz(*start)[0]:
            sys.exit('FATAL: a chain ran east to west')
        vote = 0
        for w, fwd in seq:
            pd = (w.get('tags') or {}).get('railway:preferred_direction')
            if pd == 'forward':
                vote += 1 if fwd else -1
            elif pd == 'backward':
                vote += -1 if fwd else 1
        chains.append({'ways': seq, 'dir': 1 if vote > 0 else -1, 'vote': vote})
    if len(chains) != 2 or {c['dir'] for c in chains} != {1, -1}:
        sys.exit('FATAL: expected one eastbound and one westbound chain')
    return chains


def chain_points(seq):
    """Per-way simplified points in chain order, and per-segment flags (flag boundaries kept exact)."""
    pts, flags = [], []
    for w, fwd in seq:
        g = w['geometry'] if fwd else w['geometry'][::-1]
        p = simplify([to_xz(q['lat'], q['lon']) for q in g], TOL)
        f = way_flags(w)
        if pts:
            p = p[1:]                      # the shared end node
        else:
            pts.append(p[0]); p = p[1:]
        for q in p:
            pts.append(q); flags.append(f)
    return pts, flags


def cumulative(pts):
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + math.dist(a, b))
    return s


def project(pts, s, x, z):
    """(along, lateral signed: + to the right of travel along the stored order, i) of the nearest point."""
    best = (1e18, 0, 0, 0)
    for i in range(len(pts) - 1):
        (ax, az), (bx, bz) = pts[i], pts[i + 1]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
        ex, ez = ax + dx * t - x, az + dz * t - z
        d2 = ex * ex + ez * ez
        if d2 < best[0]:
            L = math.sqrt(L2)
            side = ((x - ax) * dz - (z - az) * dx) / L    # x east, z south: + is right of the direction of travel
            best = (d2, s[i] + t * L, side, i)
    return best[1], best[2], best[3]


def point_at(pts, s, d):
    for i in range(len(pts) - 1):
        if s[i + 1] >= d:
            t = (d - s[i]) / ((s[i + 1] - s[i]) or 1e-9)
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
    return pts[-1]


def cut(pts, flags, s, d0, d1):
    """The sub-chain between along-distances d0 < d1 (interpolated ends), flags kept per segment."""
    out, fo = [point_at(pts, s, d0)], []
    for i in range(len(pts) - 1):
        if s[i] > d0 and s[i] < d1:
            out.append(pts[i]); fo.append(flags[i - 1])
    out.append(point_at(pts, s, d1))
    # the last segment's flag: the segment containing d1
    j = max(i for i in range(len(pts) - 1) if s[i] < d1)
    fo.append(flags[j])
    return out, fo


# ------------------------------------------------------------------ GTFS
_ZIP = {}


def rows(name):
    if 'z' not in _ZIP:
        _ZIP['z'] = zipfile.ZipFile(GTFS_ZIP)
    import io
    with _ZIP['z'].open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig', newline='')))


def has(name):
    if 'z' not in _ZIP:
        _ZIP['z'] = zipfile.ZipFile(GTFS_ZIP)
    return name in _ZIP['z'].namelist()


def secs(t):
    h, m, x = (int(v) for v in t.strip().split(':'))
    return h * 3600 + m * 60 + x          # >= 24:00:00 stays past 86400 (the next morning of this service day)


def ymd(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:]))


def resolve_calendar(trip_sig):
    """Dates -> active service ids, calendar.txt then calendar_dates.txt, then the swap-day repair."""
    cal = rows('calendar.txt')
    cdates = rows('calendar_dates.txt') if has('calendar_dates.txt') else []
    info = rows('feed_info.txt')[0] if has('feed_info.txt') else {}
    d0 = ymd(info.get('feed_start_date') or min(c['start_date'] for c in cal))
    d1 = ymd(info.get('feed_end_date') or max(c['end_date'] for c in cal))
    wd = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    base, adds, rems = {}, defaultdict(set), defaultdict(set)
    for r in cdates:
        (adds if r['exception_type'].strip() == '1' else rems)[ymd(r['date'])].add(r['service_id'])
    days, notes = {}, []
    d = d0
    while d <= d1:
        on = {c['service_id'] for c in cal if ymd(c['start_date']) <= d <= ymd(c['end_date']) and c[wd[d.weekday()]] == '1'}
        base[d] = set(on)
        for sv in rems[d]:
            if sv not in on:
                notes.append(f'{d} {d.strftime("%a")}: calendar_dates removes {sv!r}, which calendar.txt does not run that day (a no-op removal)')
        on = (on - rems[d]) | adds[d]
        # the repair: a service ADDED for the date that duplicates a base service running that day
        # replaces it (feed 19, Sep 26 2026: Bike MS is the Saturday timetable plus early trains, and
        # the removal names 194 Sunday instead of 194 Saturday, so a literal reading runs both)
        for a in adds[d]:
            for b in sorted(on & base[d]):
                if a == b:
                    continue
                share = len(trip_sig[a] & trip_sig[b]) / max(1, min(len(trip_sig[a]), len(trip_sig[b])))
                if share > DUP_SHARE:
                    on.discard(b)
                    notes.append(f'{d} {d.strftime("%a")}: added {a!r} shares {share:.0%} of its trips with {b!r}; {b!r} dropped (swap day)')
        days[d] = on
        d += datetime.timedelta(days=1)
    return d0, d1, days, notes


def reduce_trips(trips, stop_times):
    """Each trip that crosses the bridge -> (service, direction, tPhl, tCam, code)."""
    by_trip = defaultdict(list)
    for r in stop_times:
        by_trip[r['trip_id']].append(r)
    names = {t['trip_id'] for t in trips}
    out, skipped, sig = [], Counter(), defaultdict(set)
    for t in trips:
        st = sorted(by_trip[t['trip_id']], key=lambda r: int(r['stop_sequence']))
        tm = [secs(r['departure_time'] or r['arrival_time']) for r in st]
        # a clock that runs backwards inside one trip wrapped past midnight: carry the day
        for i in range(1, len(tm)):
            if tm[i] < tm[i - 1] - 6 * 3600:
                tm[i:] = [v + 86400 for v in tm[i:]]
        # the split-trip artefact ("... Next Day_Tnn" carrying 00:xx times on the same service date as
        # its "... Current Day_Tnn" half): the Next Day half runs after midnight, so +24 h
        if 'Next Day' in t['trip_id'] and t['trip_id'].replace('Next Day', 'Current Day') in names and tm and tm[0] < 6 * 3600:
            tm = [v + 86400 for v in tm]
        seq = [r['stop_id'] for r in st]
        sig[t['service_id']].add((t['direction_id'], tuple(zip(seq, tm))))
        ph = next((s for s in PHL_STOPS if s in seq), None)
        ca = next((s for s in CAM_STOPS if s in seq), None)
        if ph is None or ca is None:
            skipped[t['trip_id'].rsplit('_', 1)[0]] += 1
            continue
        tp, tc = tm[seq.index(ph)], tm[seq.index(ca)]
        d = int(t['direction_id'])
        if (d == 1) != (tp < tc):
            sys.exit(f'FATAL: {t["trip_id"]} runs the wrong way for direction {d}')
        code = (1 if ph == '11' else 0) | (2 if ca == '8' else 0)
        out.append((t['service_id'], d, tp, tc, code, t['trip_id']))
    return out, skipped, sig


# ------------------------------------------------------------------ main
def main():
    osm = json.load(open(OSM))
    chains = build_chains(osm['elements'])
    stops = {r['stop_id']: r for r in rows('stops.txt')}
    sxz = {k: to_xz(float(v['stop_lat']), float(v['stop_lon'])) for k, v in stops.items()}
    out_chains, report = [], []
    for c in chains:
        pts, flags = chain_points(c['ways'])
        s = cumulative(pts)
        a0 = project(pts, s, *sxz[END_W])[0] - MARGIN
        a1 = project(pts, s, *sxz[END_E])[0] + MARGIN
        full_len = s[-1]
        pts, flags = cut(pts, flags, s, max(0.0, a0), min(s[-1], a1))
        s = cumulative(pts)
        st = {}
        for k in ('11', '10', '9', '8'):
            along, side, _ = project(pts, s, *sxz[k])
            st[k] = (along, side)
        # the drawn run, portal to portal: the longest stretch with no tunnel bit (the anchorage
        # passages inside it are hidden separately, by bit 8)
        runs, cur = [], None
        for i, f in enumerate(flags):
            if not f & 1:
                cur = [s[i], s[i + 1]] if cur is None else [cur[0], s[i + 1]]
            elif cur is not None:
                runs.append(cur); cur = None
        if cur is not None:
            runs.append(cur)
        vis = max(runs, key=lambda r: r[1] - r[0])
        if len([r for r in runs if r[1] - r[0] > 50]) != 1:
            sys.exit(f'FATAL: expected one open-air run between the portals, found {runs}')
        marks = []   # every flag change: (along, from, to)
        for i in range(1, len(flags)):
            if flags[i] != flags[i - 1]:
                marks.append((s[i], flags[i - 1], flags[i], pts[i]))
        d = 1 if c['dir'] > 0 else 0      # eastbound (west->east travel) is direction_id 1, to Lindenwold
        # lateral position against the modelled bridge's centreline, sampled on the span
        ux, uz = BFB_B[0] - BFB_A[0], BFB_B[1] - BFB_A[1]
        Lb = math.hypot(ux, uz); ux /= Lb; uz /= Lb
        lat = []
        for i, p in enumerate(pts):
            u = (p[0] - BFB_A[0]) * ux + (p[1] - BFB_A[1]) * uz
            if 0 <= u <= Lb:
                lat.append((p[0] - BFB_A[0]) * (-uz) + (p[1] - BFB_A[1]) * ux)   # + is to the right of A->B (south)
        aA = project(pts, s, *BFB_A)[0]
        aB = project(pts, s, *BFB_B)[0]
        report.append({'d': d, 'full': full_len, 'len': s[-1], 'n': len(pts), 'st': st, 'vis': vis, 'marks': marks,
                       'vote': c['vote'], 'ways': len(c['ways']), 'lat': (min(lat), max(lat)) if lat else None, 'aA': aA, 'aB': aB,
                       'first': pts[0], 'last': pts[-1]})
        side = 'south' if (sum(lat) / len(lat) > 0) else 'north'
        out_chains.append({'d': d, 'h': 'Lindenwold' if d == 1 else 'Philadelphia', 'trk': side,
                           'p': [[round(x, 1), round(z, 1)] for x, z in pts], 'f': flags,
                           's': {k: round(v[0], 1) for k, v in st.items()}, 'vis': [round(vis[0], 1), round(vis[1], 1)]})
    out_chains.sort(key=lambda c: c['d'])            # index = direction_id

    trips = rows('trips.txt')
    reduced, skipped, sig = reduce_trips(trips, rows('stop_times.txt'))
    d0, d1, days, notes = resolve_calendar(sig)
    svc = sorted({t['service_id'] for t in trips})
    idx = {v: i for i, v in enumerate(svc)}
    per = [[[], []] for _ in svc]
    for sv, d, tp, tc, code, _ in sorted(reduced, key=lambda r: (r[0], r[1], min(r[2], r[3]))):
        per[idx[sv]][d].append([tp, tc, code] if code else [tp, tc])
    mask = []
    dd = d0
    while dd <= d1:
        mask.append(sum(1 << idx[v] for v in days[dd]))
        dd += datetime.timedelta(days=1)
    cal = rows('calendar.txt')
    wd = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    # the weekly pattern for a date past the feed: the services calendar.txt runs on that weekday
    # across the whole feed (a one-day special like Bike MS, start == end, never counts)
    week = [sum(1 << idx[c['service_id']] for c in cal if c[w] == '1' and ymd(c['end_date']) > ymd(c['start_date'])) for w in wd]
    info = rows('feed_info.txt')[0]
    out = {'src': 'PATCO GTFS (Port Authority Transit Corporation, www.ridepatco.org/developers) for the timetable; '
                  'OpenStreetMap railway=subway ways operated by PATCO (ODbL) for the track, model frame (philly_frame.py)',
           'feed': {'v': info.get('feed_version', ''), 'from': d0.isoformat(), 'to': d1.isoformat(), 'tz': 'America/New_York'},
           'baked': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'chains': out_chains, 'svc': svc, 'trips': per, 'days': mask, 'week': week}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    if d1 < datetime.date.today():
        print(f'WARNING: the PATCO feed ended {d1}; the page falls back to its weekly pattern. Rerun fetch_patco.py when PATCO posts a new feed.')

    # ---------------------------------------------------------------- report
    print(f'{OUT}: {os.path.getsize(OUT):,} bytes')
    for r in sorted(report, key=lambda r: r['d']):
        print(f"\nchain d={r['d']} ({'eastbound, to Lindenwold' if r['d'] else 'westbound, to Philadelphia'}): {r['ways']} ways, preferred_direction vote {r['vote']:+d}, "
              f"whole track {r['full']:.1f} m, kept {r['len']:.1f} m in {r['n']} points, first {tuple(round(v,1) for v in r['first'])} last {tuple(round(v,1) for v in r['last'])}")
        for k in ('11', '10', '9', '8'):
            a, sd = r['st'][k]
            print(f"   {stops[k]['stop_name']:18s} s={a:7.1f}  (stop point {abs(sd):5.1f} m {'right' if sd > 0 else 'left'} of the track, stored order)")
        for a, f0, f1, p in r['marks']:
            print(f"   flag {f0}->{f1} at s={a:7.1f}  ({p[0]:7.1f}, {p[1]:7.1f})")
        print(f"   drawn run (portal to portal): s={r['vis'][0]:.1f} .. {r['vis'][1]:.1f} = {r['vis'][1]-r['vis'][0]:.1f} m")
        print(f"   BFB_A projects at s={r['aA']:.1f}, BFB_B at s={r['aB']:.1f}; lateral from the A-B line on the span {r['lat'][0]:+.1f} .. {r['lat'][1]:+.1f} m (+ south)")
    print('\ncalendar notes:')
    for n in notes:
        print('  ' + n)
    print('\ntrips skipped (never cross the bridge):', dict(skipped))
    print('trips per service (westbound d0 / eastbound d1):')
    for i, v in enumerate(svc):
        print(f'  {v:13s} {len(per[i][0]):3d} / {len(per[i][1]):3d}   codes {dict(Counter(r[2] if len(r) > 2 else 0 for d in (0, 1) for r in per[i][d]))}')
    dates = Counter(tuple(sorted(days[k])) for k in days)
    print('dates resolved:', {', '.join(k): v for k, v in dates.items()})
    # the sanity check: headways where the drawn run crosses the river (the span's midpoint on each
    # chain), each trip timed linearly in distance between its two bracketing stops
    print('headways over the span (minutes; by hour of the service day):')
    for i, v in enumerate(svc):
        for d in (0, 1):
            c = out_chains[d]
            ptsd = c['p']
            sd = cumulative(ptsd)
            mid = project(ptsd, sd, (BFB_A[0] + BFB_B[0]) / 2, (BFB_A[1] + BFB_B[1]) / 2)[0]
            tm = []
            for r in per[i][d]:
                code = r[2] if len(r) > 2 else 0
                sp, sc = c['s']['11' if code & 1 else '10'], c['s']['8' if code & 2 else '9']
                tm.append(r[0] + (r[1] - r[0]) * (mid - sp) / (sc - sp))
            tm.sort()
            hw = [(b - a) / 60 for a, b in zip(tm, tm[1:])]
            byh = defaultdict(set)
            for a, h in zip(tm, hw):
                byh[int(a // 3600)].add(round(h))
            print(f'  {v:13s} d{d} {len(tm):3d} crossings {int(tm[0]) // 3600:02d}:{int(tm[0]) % 3600 // 60:02d}..{int(tm[-1]) // 3600:02d}:{int(tm[-1]) % 3600 // 60:02d}, '
                  f'min {min(hw):.1f} median {sorted(hw)[len(hw) // 2]:.1f} max {max(hw):.1f}; ' + ' '.join(f'{h:02d}h:' + '/'.join(str(x) for x in sorted(byh[h])) for h in sorted(byh)))
    return out, report


if __name__ == '__main__':
    main()
