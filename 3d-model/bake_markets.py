#!/usr/bin/env python3
"""lidar_cache/markets_raw/farmers_markets.geojson -> markets.json : the City's farmers'
markets in the local frame with their hours parsed for the app's clock (Round 76).
  [{"n": name, "x": m, "z": m, "op": operator, "addr": address, "web": url or "",
    "pay": ["SNAP", "Credit", ...], "yr": true|false,
    "o": [month, day] | null, "c": [month, day] | null,        # the season, when not year round
    "h": {"0": [start, end, note?], ...}}, ...]                  # JS weekday (0 Sunday) -> minutes
Hours come as 'HH:MM' strings per weekday (one '9:00' without its zero, one end of '01:00'
that is plainly 13:00: an end at or before its start gains twelve hours); a day whose start
or end does not parse is dropped. The season is a month name plus a day (day 1 opening and
the month's last day closing when the day is missing), 'Yes' in season_year_round for the
markets that never close, and two seasonal rows carry no months at all (open all year by
weekday: the card says what the city says). Payments are the 'Yes' flags; cash is implied.
Websites are normalised to https://host/path. Names, operators, addresses and the hour
notes lose their dashes and middots (the HUD rule) and their doubled whitespace.
Frame: philly_frame.py (the scene's own projection); clipped to the far-ring box.
Run with plain python3; bake() is pure so tests/test_markets_bake.py can feed it fixtures."""
import calendar
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'markets_raw', 'farmers_markets.geojson')
OUT = os.path.join(HERE, 'markets.json')
from philly_frame import to_xz   # the one scene frame

CITY = (-12000, 16500, -21700, 9700)   # pack_city.py's box: x0, x1, z0, z1
DAYS = ['sun', 'mon', 'tues', 'wed', 'thurs', 'fri', 'sat']   # index = JS getDay()
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
PAYMENTS = [('payment_snap', 'SNAP'), ('payment_credit', 'Credit'), ('payment_fmnp', 'FMNP'),
            ('payment_philly_food_bucks', 'Philly Food Bucks')]
DASHES = re.compile('[‒–—―·•]')


def clean(s):
    """Trim, collapse whitespace, and turn dashes and middots into commas (the HUD rule)."""
    if not s:
        return ''
    s = DASHES.sub(', ', str(s))
    s = re.sub(r'\s+,', ',', s)          # 'Market , Shambles' -> 'Market, Shambles'
    s = re.sub(r',(\s*,)+', ',', s)
    return re.sub(r'\s+', ' ', s).strip(' ,')


def parse_hhmm(s):
    """'9:00' -> 540, '14:30' -> 870; None when the string is not a clock time."""
    m = re.match(r'^\s*(\d{1,2}):(\d{2})\s*$', str(s or ''))
    if not m:
        return None
    h, mm = int(m.group(1)), int(m.group(2))
    if h > 23 or mm > 59:
        return None
    return h * 60 + mm


def hours_of(p):
    """The per-weekday [start, end, note?] table, JS weekday keys as strings."""
    h = {}
    for i, d in enumerate(DAYS):
        s, e = parse_hhmm(p.get(f'hours_{d}_start')), parse_hhmm(p.get(f'hours_{d}_end'))
        if s is None or e is None:
            continue
        if e <= s:
            e += 720          # '01:00' after a '09:00' start is one in the afternoon
        if e <= s:
            continue
        note = clean(p.get(f'hours_{d}_exceptions'))
        h[str(i)] = [s, e] + ([note] if note else [])
    return h


def season_of(p):
    """(year_round, [open month, day] | None, [close month, day] | None)."""
    yr = str(p.get('season_year_round') or '').strip().lower() == 'yes'
    om = MONTHS.get(str(p.get('season_opening_month') or '').strip().lower())
    cm = MONTHS.get(str(p.get('season_closing_month') or '').strip().lower())
    if yr or not om or not cm:
        return yr, None, None
    od = int(p.get('season_opening_day') or 0) or 1
    cd = int(p.get('season_closing_day') or 0) or calendar.monthrange(2026, cm)[1]
    return False, [om, max(1, min(31, od))], [cm, max(1, min(31, cd))]


def website_of(s):
    s = str(s or '').strip()
    if not s or s.lower() in ('n/a', 'na', 'none'):
        return ''
    if not re.match(r'^https?://', s, re.I):
        s = 'https://' + s
    m = re.match(r'^(https?://)([^/\s]+)(/\S*)?$', s, re.I)
    if not m:
        return ''
    return 'https://' + m.group(2).lower() + (m.group(3) or '')


def bake(features):
    out = []
    for f in features or []:
        g = f.get('geometry') or {}
        p = f.get('properties') or {}
        if g.get('type') != 'Point' or not p.get('name'):
            continue
        lon, lat = g['coordinates'][:2]
        x, z = to_xz(lat, lon)
        if not (CITY[0] <= x <= CITY[1] and CITY[2] <= z <= CITY[3]):
            continue
        yr, o, c = season_of(p)
        out.append({
            'n': clean(p.get('name')), 'x': int(round(x)), 'z': int(round(z)),
            'op': clean(p.get('operator')), 'addr': clean(p.get('address')),
            'web': website_of(p.get('contact_website')),
            'pay': [label for key, label in PAYMENTS if str(p.get(key) or '').strip().lower() == 'yes'],
            'yr': yr, 'o': o, 'c': c, 'h': hours_of(p),
        })
    out.sort(key=lambda m: (m['n'].lower(), m['x'], m['z']))
    return out


def main():
    feats = json.load(open(RAW))['features']
    out = bake(feats)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), ensure_ascii=False)
    n_h = sum(1 for m in out if m['h'])
    n_yr = sum(1 for m in out if m['yr'])
    print(f'{len(out)} markets ({n_h} with hours, {n_yr} year round, {len(feats) - len(out)} dropped), '
          f'markets.json {os.path.getsize(OUT) / 1e3:.1f} KB', flush=True)
    for m in out:
        days = ','.join(DAYS[int(k)] for k in sorted(m['h']))
        print(f"  {m['n']} ({m['x']}, {m['z']}) {days or 'no hours'} {'year round' if m['yr'] else (m['o'], m['c'])}")


if __name__ == '__main__':
    main()
