#!/usr/bin/env python3
"""Bake the Ticketmaster Discovery API's Philadelphia music listings to a static
concerts.json (+ .gz twin) for philly3d.com.

Why: the Discovery API wants a key on every call and allows 5,000 calls a day, so
the key stays on the VPS and one baker asks Ticketmaster once every 15 minutes for
every viewer; nginx serves the trimmed file next to the page (gzip_static). The page
shows a placard over each venue from 9 am Philadelphia time on the day of the show
until the show ends, comparing the two instants below with real time.

Output contract (the page's concertsPoll parses exactly this -- keep it):

    {"t": <unix seconds of this bake, float>,
     "day": "YYYY-MM-DD",                  Philadelphia's date at the bake
     "events": [ {"id": str, "name": str, "artist": str, "genre": str, "url": str,
                  "image": str (a ticketm.net image url, or ""),
                  "venue": {"id": str, "name": str, "lat": float, "lon": float},
                  "date": "YYYY-MM-DD", "time": "HH:MM" or "", "tba": bool,
                  "start": <unix seconds> or null,
                  "from": <unix seconds: 09:00 America/New_York on the show day>,
                  "until": <unix seconds: start + 4 h, or the next local midnight after a TBA time>,
                  "status": "onsale" | "offsale" | "rescheduled"}, ... ] }

Events are the Music segment only, with a venue position, a known date, and a
status other than cancelled or postponed, from local midnight today through --days
(default 3) days, sorted by start, one record per event id. Names pass through
untouched except that dashes and middots become ", " (the HUD's own rule).

The page treats "t" older than 3 hours as "baker down" and drops every placard, so
on a bad upstream answer this script KEEPS the previous file -- "t" goes stale on
its own -- and never writes garbage. Nothing older than the window is ever kept:
the file is rewritten whole every bake.

Usage:
    concerts_bake.py                    one bake (systemd timer mode); exit 1 on failure, 2 without a key
    concerts_bake.py --loop             bake every --interval seconds (default 900) forever
    concerts_bake.py --out PATH         default /var/www/philly3d/concerts.json
    concerts_bake.py --env-file PATH    default /etc/philly3d/concerts.env (TICKETMASTER_KEY=...)
The key is read from the TICKETMASTER_KEY environment variable (systemd's
EnvironmentFile) or the env file; it is never logged and never written anywhere.
Stdlib only (zoneinfo needs Python 3.9+ and the system tzdata)."""
import argparse
import datetime as dt
import gzip
import http.client
import json
import logging
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

API = 'https://app.ticketmaster.com/discovery/v2/events.json'
DEFAULT_OUT = '/var/www/philly3d/concerts.json'
DEFAULT_ENV = '/etc/philly3d/concerts.env'
TZ = ZoneInfo('America/New_York')
CITY_HALL = (39.9526, -75.1652)
TIMEOUT = 18.0
MAX_BYTES = 6 * 1024 * 1024
PAGE_SIZE = 200
MAX_PAGES = 4                      # size * page < 1000 is the API's deep-paging cap
USER_AGENT = 'philly3d-concerts-bake/1 (+https://philly3d.com)'
SHOW_FROM = (9, 0)                 # the placard rises at 9 am local on the show day
SHOW_LEN = 4 * 3600                # and stands four hours past the start
STATUS_DROP = ('canceled', 'cancelled', 'postponed')
DASHES = re.compile(r'\s*[–—·•]\s*')

log = logging.getLogger('concerts-bake')


# ---------------------------------------------------------------- the key
def load_key(env_file):
    """TICKETMASTER_KEY from the environment, else from a KEY=value file; '' when absent."""
    k = os.environ.get('TICKETMASTER_KEY', '').strip()
    if k:
        return k
    try:
        with open(env_file, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('TICKETMASTER_KEY=') and not line.startswith('#'):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ''


# ---------------------------------------------------------------- the fetch
def window(now, days):
    """Local midnight today to local midnight days later, as the API's UTC strings."""
    day0 = dt.datetime.fromtimestamp(now, TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    day1 = day0 + dt.timedelta(days=days)
    fmt = lambda d: d.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return fmt(day0), fmt(day1), day0.strftime('%Y-%m-%d')


def fetch_page(key, page, start, end, lat, lon, radius_km):
    """One page of the Music search around (lat, lon); raises on any failure.
    The URL carries the key, so only the path is ever logged."""
    q = {'apikey': key, 'classificationName': 'Music', 'latlong': '%.4f,%.4f' % (lat, lon),
         'radius': str(int(radius_km)), 'unit': 'km', 'startDateTime': start, 'endDateTime': end,
         'sort': 'date,asc', 'size': str(PAGE_SIZE), 'page': str(page), 'locale': 'en-us', 'countryCode': 'US'}
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(q), headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise RuntimeError('events.json page %d: http %s' % (page, e.code)) from None
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        raise RuntimeError('events.json page %d: %s' % (page, getattr(e, 'reason', e.__class__.__name__))) from None
    if len(raw) > MAX_BYTES:
        raise RuntimeError('events.json page %d: answer over %d bytes' % (page, MAX_BYTES))
    d = json.loads(raw.decode('utf-8'))
    if not isinstance(d, dict) or 'page' not in d:
        raise RuntimeError('events.json page %d: not a Discovery answer' % page)
    return d


def fetch_all(key, start, end, lat, lon, radius_km):
    pages, page = [], 0
    while page < MAX_PAGES:
        d = fetch_page(key, page, start, end, lat, lon, radius_km)
        pages.append(d)
        pg = d.get('page') or {}
        total = int(pg.get('totalPages') or 1)
        page += 1
        if page >= total or page * PAGE_SIZE >= 1000:
            break
    return pages


# ---------------------------------------------------------------- the projection
def clean(s):
    return DASHES.sub(', ', str(s or '')).strip()


def local_ts(date_str, hh, mm):
    y, m, d = (int(p) for p in date_str.split('-'))
    return int(dt.datetime(y, m, d, hh, mm, tzinfo=TZ).timestamp())


def pick_image(images):
    """The smallest 16:9 image at least 300 px wide from a ticketm.net host; else ''."""
    best = None
    for im in images or []:
        url = str(im.get('url') or '')
        if im.get('fallback') or not re.match(r'^https://[a-z0-9.-]*ticketm\.net/', url, re.I):
            continue
        w = int(im.get('width') or 0)
        if im.get('ratio') != '16_9' or w < 300:
            continue
        if best is None or w < best[0]:
            best = (w, url)
    return best[1] if best else ''


def project(pages, now):
    """The output contract from the raw pages (see the module docstring)."""
    out, seen = [], set()
    for d in pages:
        for ev in ((d.get('_embedded') or {}).get('events') or []):
            try:
                rec = project_event(ev)
            except (TypeError, ValueError, KeyError, AttributeError):
                rec = None
            if rec and rec['id'] not in seen:
                seen.add(rec['id'])
                out.append(rec)
    out.sort(key=lambda r: (r['date'], r['start'] or 0, r['name']))
    day = dt.datetime.fromtimestamp(now, TZ).strftime('%Y-%m-%d')
    return {'t': float(now), 'day': day, 'events': out}


def project_event(ev):
    """One event record, or None when it is not a placard: no venue position, no date,
    cancelled or postponed, or not the Music segment."""
    dates = ev.get('dates') or {}
    start = dates.get('start') or {}
    status = str(((dates.get('status') or {}).get('code')) or 'onsale').lower()
    if status in STATUS_DROP or start.get('dateTBD') or start.get('dateTBA'):
        return None
    if not any(str(((c.get('segment') or {}).get('name')) or '').lower() == 'music' for c in (ev.get('classifications') or [])):
        return None
    venues = (ev.get('_embedded') or {}).get('venues') or []
    if not venues:
        return None
    v = venues[0]
    loc = v.get('location') or {}
    lat, lon = float(loc.get('latitude')), float(loc.get('longitude'))
    date = str(start.get('localDate') or '')
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        return None
    tba = bool(start.get('timeTBA') or start.get('noSpecificTime')) or not start.get('localTime')
    hhmm = '' if tba else str(start['localTime'])[:5]
    if hhmm and not re.match(r'^\d{2}:\d{2}$', hhmm):
        tba, hhmm = True, ''
    # the TBA flag wins over a dateTime the record may still carry: a time to be announced has no start
    if not tba and start.get('dateTime'):
        st = int(dt.datetime.fromisoformat(str(start['dateTime']).replace('Z', '+00:00')).timestamp())
    elif not tba and hhmm:
        st = local_ts(date, int(hhmm[:2]), int(hhmm[3:]))
    else:
        st = None
    show_from = local_ts(date, SHOW_FROM[0], SHOW_FROM[1])
    y, m, d = (int(p) for p in date.split('-'))
    next_midnight = int((dt.datetime(y, m, d, tzinfo=TZ) + dt.timedelta(days=1)).timestamp())   # wall-clock arithmetic: right across a DST change
    until = st + SHOW_LEN if st else next_midnight   # a TBA time stands to the next local midnight
    if st and st < show_from:   # a late set listed under its calendar date (a 12:30 am start): the placard opens the evening before
        show_from = st - 12 * 3600
    if until <= show_from:      # a last-resort guard: the page needs an open window
        until = show_from + 3600
    attractions = (ev.get('_embedded') or {}).get('attractions') or []
    genre = ''
    for c in ev.get('classifications') or []:
        g = (c.get('genre') or {}).get('name')
        if g and str(g).lower() != 'undefined':
            genre = clean(g)
            break
    url = str(ev.get('url') or '')
    if not re.match(r'^https://[a-z0-9.-]*ticketmaster\.com/', url, re.I):
        url = ''
    return {'id': str(ev.get('id') or ''), 'name': clean(ev.get('name')),
            'artist': clean(attractions[0].get('name')) if attractions else '', 'genre': genre, 'url': url,
            'image': pick_image(ev.get('images')),
            'venue': {'id': str(v.get('id') or ''), 'name': clean(v.get('name')), 'lat': lat, 'lon': lon},
            'date': date, 'time': hhmm, 'tba': tba, 'start': st, 'from': show_from, 'until': until, 'status': status}


# ---------------------------------------------------------------- the writer (septa_bake's: temp file, fsync, 0644, replace; the .gz twin first)
def write_atomic(path, data):
    d = os.path.dirname(os.path.abspath(path)) or '.'
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.', suffix='.tmp', dir=d)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def publish(path, obj):
    raw = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    write_atomic(path + '.gz', gzip.compress(raw, compresslevel=6, mtime=0))
    write_atomic(path, raw)
    return len(raw)


# ---------------------------------------------------------------- one bake
def bake_once(key, out, days, lat, lon, radius_km):
    now = time.time()
    start, end, _ = window(now, days)
    try:
        pages = fetch_all(key, start, end, lat, lon, radius_km)
        obj = project(pages, now)
    except (RuntimeError, ValueError, TypeError) as e:
        log.warning('kept the previous file: %s', e)
        return False
    try:
        n = publish(out, obj)
    except OSError as e:
        log.warning('could not write %s: %s', out, e.__class__.__name__)
        return False
    log.info('wrote %s: %d events through %s, %d bytes', out, len(obj['events']), end[:10], n)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--env-file', default=DEFAULT_ENV)
    ap.add_argument('--loop', action='store_true')
    ap.add_argument('--interval', type=float, default=900.0)
    ap.add_argument('--days', type=int, default=3)
    ap.add_argument('--lat', type=float, default=CITY_HALL[0])
    ap.add_argument('--lon', type=float, default=CITY_HALL[1])
    ap.add_argument('--radius', type=float, default=12.0, help='km about --lat/--lon (the city and the Camden waterfront)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
    key = load_key(a.env_file)
    if not key:
        log.error('no TICKETMASTER_KEY in the environment or %s', a.env_file)
        return 2
    if not a.loop:
        return 0 if bake_once(key, a.out, a.days, a.lat, a.lon, a.radius) else 1
    while True:
        t0 = time.time()
        try:
            bake_once(key, a.out, a.days, a.lat, a.lon, a.radius)
        except Exception:   # the loop outlives any surprise; the traceback shows code, never the key
            log.exception('bake failed unexpectedly; continuing')
        time.sleep(max(1.0, a.interval - (time.time() - t0)))


if __name__ == '__main__':
    sys.exit(main())
