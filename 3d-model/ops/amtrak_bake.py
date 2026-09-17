#!/usr/bin/env python3
"""Bake the Amtrak trains near Philadelphia to a static amtrak.json (+ .gz twin) for
philly3d.com (Round 80).

Why: the Amtraker API (a community mirror of Amtrak's own train tracker, no key, CORS open,
ODC-By 1.0: the page credits it) answers with every train in the country, 1.3 MB a pull and
about a minute between Amtrak's position updates; one baker here pulls it every 30 seconds
for every viewer and writes the handful of trains within the model's reach, a few kilobytes,
that nginx serves next to the page (gzip_static). The page rides the trains along the baked
Northeast Corridor and Keystone tracks between fixes.

Output contract (the page's amtrakGot parses exactly this -- keep it):

    {"t": <unix seconds of this bake, float>,
     "src": <unix seconds of the newest fix kept, or 0>,
     "trains": [ {"id": "192-16", "num": "192", "route": "Northeast Regional",
                  "lat": 39.93, "lon": -75.22, "hdg": "NE", "mph": 95.6, "state": "Active",
                  "fix": <unix seconds of the position>,
                  "orig": "WAS", "dest": "Boston South", "destCode": "BOS",
                  "next": {"code": "PHL", "name": "Philadelphia 30th Street", "sch": <unix s>, "est": <unix s>, "late": 7} | null,
                  "timely": "7 Minutes Late"}, ... ] }

Kept: trains whose state is Active with a finite position inside --box (the model's city
plus about 11 km, so an approaching train is known before it crosses the limit). "next" is
the first station in list order that has not departed and is not a bus connection; "late"
is the estimate against the schedule in minutes. Every string loses its dashes and middots
(the HUD's own rule). The page treats "t" older than 150 seconds as a stopped baker and
pulls Amtraker itself; on a bad upstream answer this script KEEPS the previous file.

Usage:
    amtrak_bake.py --loop [--interval 30]   bake forever (the systemd service)
    amtrak_bake.py                          one bake; exit 1 on failure
    amtrak_bake.py --out PATH               default /var/www/philly3d/amtrak.json
Stdlib only."""
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
import urllib.request

API = 'https://api-v3.amtraker.com/v3/trains'
DEFAULT_OUT = '/var/www/philly3d/amtrak.json'
TIMEOUT = 20.0
MAX_BYTES = 16 * 1024 * 1024
USER_AGENT = 'philly3d-amtrak-bake/1 (+https://philly3d.com)'   # Amtraker refuses a call without one
BOX = (39.75, 40.25, -75.45, -74.80)                            # lat0, lat1, lon0, lon1
DASHES = re.compile(r'\s*[‒–—―·•]\s*')

log = logging.getLogger('amtrak-bake')


def clean(s):
    return re.sub(r'\s+', ' ', DASHES.sub(', ', str(s or ''))).strip(' ,')


def ts(s):
    """An ISO instant with its offset ('2026-09-16T20:58:41-04:00') to unix seconds, or None."""
    if not s:
        return None
    try:
        return int(dt.datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp())
    except (TypeError, ValueError):
        return None


def fetch(url=API):
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json', 'Accept-Encoding': 'gzip'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES + 1)
            enc = (r.headers.get('Content-Encoding') or '').lower()
    except urllib.error.HTTPError as e:
        raise RuntimeError('trains: http %s' % e.code) from None
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        raise RuntimeError('trains: %s' % getattr(e, 'reason', e.__class__.__name__)) from None
    if len(raw) > MAX_BYTES:
        raise RuntimeError('trains: answer over %d bytes' % MAX_BYTES)
    if enc == 'gzip' or raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    d = json.loads(raw.decode('utf-8'))
    if not isinstance(d, dict):
        raise RuntimeError('trains: not an object')
    return d


def project_train(t, box=BOX):
    """One train record for the contract, or None when it is not on the model's reach."""
    if str(t.get('trainState') or '').lower() != 'active':
        return None
    try:
        lat, lon = float(t.get('lat')), float(t.get('lon'))
    except (TypeError, ValueError):
        return None
    if not (box[0] <= lat <= box[1] and box[2] <= lon <= box[3]):
        return None
    nxt = None
    for s in t.get('stations') or []:
        if not isinstance(s, dict) or s.get('bus'):
            continue
        if str(s.get('status') or '').lower() == 'departed':
            continue
        sch = ts(s.get('schArr')) or ts(s.get('schDep'))
        est = ts(s.get('arr')) or ts(s.get('dep'))
        nxt = {'code': clean(s.get('code')), 'name': clean(s.get('name')), 'sch': sch, 'est': est,
               'late': int(round((est - sch) / 60.0)) if sch and est else None}
        break
    try:
        mph = round(float(t.get('velocity') or 0), 1)
    except (TypeError, ValueError):
        mph = 0.0
    return {'id': clean(t.get('trainID')) or clean(t.get('trainNum')), 'num': clean(t.get('trainNum')),
            'route': clean(t.get('routeName')), 'lat': round(lat, 5), 'lon': round(lon, 5),
            'hdg': clean(t.get('heading')).upper()[:3], 'mph': mph, 'state': 'Active',
            'fix': ts(t.get('lastValTS')) or ts(t.get('updatedAt')) or 0,
            'orig': clean(t.get('origCode')), 'dest': clean(t.get('destName')), 'destCode': clean(t.get('destCode')),
            'next': nxt, 'timely': clean(t.get('trainTimely'))}


def project(d, now, box=BOX):
    out = []
    for group in d.values():
        for t in group if isinstance(group, list) else []:
            if not isinstance(t, dict):
                continue
            rec = project_train(t, box)
            if rec:
                out.append(rec)
    out.sort(key=lambda r: (r['num'].zfill(6), r['id']))
    src = max([r['fix'] for r in out] + [0])
    return {'t': float(now), 'src': src, 'trains': out}


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


def bake_once(out, box):
    now = time.time()
    try:
        obj = project(fetch(), now, box)
    except (RuntimeError, ValueError, TypeError) as e:
        log.warning('kept the previous file: %s', e)
        return False
    try:
        n = publish(out, obj)
    except OSError as e:
        log.warning('could not write %s: %s', out, e.__class__.__name__)
        return False
    log.info('wrote %s: %d trains, %d bytes', out, len(obj['trains']), n)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--loop', action='store_true')
    ap.add_argument('--interval', type=float, default=30.0)
    ap.add_argument('--box', default=','.join(str(v) for v in BOX), help='lat0,lat1,lon0,lon1')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
    box = tuple(float(v) for v in a.box.split(','))
    if not a.loop:
        return 0 if bake_once(a.out, box) else 1
    while True:
        t0 = time.time()
        try:
            bake_once(a.out, box)
        except Exception:
            log.exception('bake failed unexpectedly; continuing')
        time.sleep(max(1.0, a.interval - (time.time() - t0)))


if __name__ == '__main__':
    sys.exit(main())
