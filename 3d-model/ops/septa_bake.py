#!/usr/bin/env python3
"""Bake SEPTA TransitViewAll to a static septa.json (+ .gz twin) for philly3d.com.

Why: TransitViewAll is ~370 KB a pull and the page polled it every 15 s PER
VIEWER over JSONP. One baker on the VPS pulls it once every 10 s and writes a
trimmed copy next to the page; nginx serves that as a static file through
gzip_static, so N viewers cost SEPTA one request per 10 s and each viewer
downloads ~30 KB of gzip instead of 370 KB of script.

Output contract (the page's septaGotTV parses exactly this -- keep it):

    {"t": <unix seconds of this bake, float>,
     "routes": [ { "<routeId>": [ {"VehicleID", "lat", "lng", "heading",
                                     "timestamp", "destination", "late",
                                     "next_stop_name"}, ... ],
                   ... } ] }

"routes" stays an array whose first element is the per-route object, exactly
as upstream returns it. Every route and every vehicle is kept (the page does
its own rail / placeholder / stale-fix filtering); only the fields the page
never reads are dropped, and kept values pass through untouched (lat/lng are
strings upstream, heading/late/timestamp numbers, next_stop_name may be null).

The page treats "t" older than 90 s as "baker down" and falls back to JSONP,
so on a bad upstream answer this script KEEPS the previous file -- "t" goes
stale on its own -- and never writes garbage or crashes the loop.

Usage:
    septa_bake.py                     one bake (systemd timer mode); exit 1 on failure
    septa_bake.py --loop              bake every --interval seconds (default 10) forever
    septa_bake.py --out PATH          default /var/www/philly3d/septa.json
Stdlib only. Python 3.9+.
"""
import argparse
import gzip
import json
import logging
import os
import signal
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

# app.js SEPTA_HOSTS, www3 first as the primary here; the other is the fallback
HOSTS = ['https://www3.septa.org/api', 'https://api.septa.org/api']
PATH = '/TransitViewAll/index.php'
# the fields septaGotTV / septaUpsert read from each vehicle record
FIELDS = ('VehicleID', 'lat', 'lng', 'heading', 'timestamp',
          'destination', 'late', 'next_stop_name')
DEFAULT_OUT = '/var/www/philly3d/septa.json'
TIMEOUT = 18.0                       # the page's own JSONP timeout
MAX_BYTES = 8 * 1024 * 1024          # TransitViewAll is ~370 KB; anything near this is not it
USER_AGENT = 'philly3d-septa-bake/1 (+https://philly3d.com)'

log = logging.getLogger('septa-bake')


def fetch(host):
    """GET TransitViewAll from one host; returns the decoded JSON or raises."""
    req = urllib.request.Request(host + PATH, headers={
        'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        if r.status != 200:
            raise RuntimeError('HTTP %s' % r.status)
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise RuntimeError('response larger than %d bytes' % MAX_BYTES)
    return json.loads(data.decode('utf-8'))


def project(d):
    """Trim an upstream TransitViewAll answer to the fields the page reads.

    Returns (routes_object, vehicle_count). Raises ValueError when the answer
    is not the shape the page could parse (so the caller keeps the old file).
    """
    routes = d.get('routes') if isinstance(d, dict) else None
    if isinstance(routes, list):
        routes = routes[0] if routes else None
    if not isinstance(routes, dict):
        raise ValueError('no routes object in upstream answer')
    out = {}
    n = 0
    for rid, lst in routes.items():
        if not isinstance(lst, list):
            continue                 # the page skips non-array routes too
        kept = []
        for b in lst:
            if not isinstance(b, dict):
                continue
            kept.append({k: b.get(k) for k in FIELDS})
            n += 1
        out[str(rid)] = kept
    if not out:
        raise ValueError('upstream answer lists no routes at all')
    return out, n


def write_atomic(path, data, mode=0o644):
    """Write bytes to a temp file beside path, fsync, chmod, rename over path."""
    d = os.path.dirname(os.path.abspath(path)) or '.'
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.', suffix='.tmp', dir=d)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def publish(path, obj):
    """Write obj as path.gz (gzip_static twin) then path. Returns (raw, gz) sizes."""
    raw = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    gz = gzip.compress(raw, compresslevel=6, mtime=0)
    # twin first: gzip_static hands the .gz to every modern browser, and a .gz
    # that is never older than its .json means nobody is served yesterday's
    # compressed copy of today's file
    write_atomic(path + '.gz', gz)
    write_atomic(path, raw)
    return len(raw), len(gz)


def bake_once(out, state):
    """Fetch (primary, then fallback host), project, publish. True on success.

    state['host'] remembers the last host that answered so the loop sticks
    with it, the way the page's septaHost does.
    """
    order = HOSTS[state['host']:] + HOSTS[:state['host']]
    last_err = None
    for host in order:
        try:
            d = fetch(host)
            routes, n = project(d)
            obj = {'t': round(time.time(), 1), 'routes': [routes]}
            raw, gz = publish(out, obj)
            state['host'] = HOSTS.index(host)
            log.info('baked %d vehicles on %d routes from %s -> %s (%d B, %d B gz)',
                     n, len(routes), host, out, raw, gz)
            return True
        except (OSError, urllib.error.URLError, ValueError, RuntimeError) as e:
            last_err = e
            log.warning('%s: %s', host, e)
        except Exception as e:                  # never let one bad answer end the loop
            last_err = e
            log.exception('%s: unexpected error', host)
    log.error('every host failed (%s); keeping the previous %s', last_err, out)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=DEFAULT_OUT, help='output path (default %(default)s)')
    ap.add_argument('--loop', action='store_true', help='keep baking every --interval seconds')
    ap.add_argument('--interval', type=float, default=10.0, help='seconds between bakes in --loop mode')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format='%(asctime)s %(name)s %(levelname)s %(message)s',
                        stream=sys.stderr)
    state = {'host': 0}
    if not a.loop:
        return 0 if bake_once(a.out, state) else 1

    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    log.info('loop: every %.0f s -> %s', a.interval, a.out)
    while not stop.is_set():
        t0 = time.monotonic()
        try:
            bake_once(a.out, state)
        except Exception:                        # belt and braces: the loop outlives anything
            log.exception('bake failed unexpectedly; continuing')
        remaining = a.interval - (time.monotonic() - t0)
        if remaining > 0:
            stop.wait(remaining)
    log.info('stopped')
    return 0


if __name__ == '__main__':
    sys.exit(main())
