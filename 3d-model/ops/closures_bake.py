#!/usr/bin/env python3
"""Bake the Streets Department's live street closures and paving status to a static
closures.json (+ .gz twin) for philly3d.com (Round 79).

Why: the city's StreetSmartPHL and LaneClosure_Master layers on ArcGIS Online are open
(CORS *, no key) but three GeoJSON pages of about a megabyte each per viewer per half hour
is the wrong shape, and the trimming below belongs on the server. One baker asks the city
every 30 minutes for every viewer and nginx serves the trimmed file next to the page
(gzip_static). The page posts barrels and cones on the closed blocks, lays fresh asphalt on
the season's paved blocks, and drops everything when the file is three hours stale.

Output contract (the page's closuresProject parses exactly this -- keep it):

    {"t": <unix seconds of this bake, float>,
     "day": "YYYY-MM-DD",                  Philadelphia's date at the bake
     "closures": [ {"id": "<seg_id>",      one record per city street segment in force
                    "o": 3 | 2 | 1,        the most restrictive occupancy of its permits: full, partial, footway
                    "addr": "2500 Block of N 22nd St",
                    "g": [[lon, lat], ...],  the city centreline segment, 5 decimals
                    "permits": [ {"n": "2026-11263", "type": "Utility Work Excavation",
                                  "why": "Trench and Install Water Main", "from": <unix s>, "until": <unix s>,
                                  "url": "https://stsweb.phila.gov/..." | ""}, ... ] }, ... ],
     "paving": [ {"id": "<objectid>", "k": "paved" | "milled", "week": bool,
                  "addr": "2200 Block of S 63rd St", "g": [[lon, lat], ...]}, ... ] }

Rules: a permit counts when it is in force now or starts within seven days and has not
expired; its end is capped at 180 days out (the city leaves some open to 2103). Permits for
parking relaxation, dumpsters, containers, loading zones and valet stands do not vote on the
occupancy (they are most of the partials), and a segment with only those is dropped; the
others vote and the strictest wins, with every permit of the segment listed newest first,
four at most. Purposes are title-cased with the city's acronyms kept, newlines and dashes
become commas, and a permit link is kept only on stsweb.phila.gov. Addresses come from
LaneClosure_Master (the same permits with a "2500 block of N 22ND ST" address). Paving:
the paving season's status layer gives "paved" for a block whose paving is complete
(striping pending, or by PennDOT) and "milled" for one milled and waiting; this week's
milling and paving lists add their rows with week=true, deduped against the season by
midpoint. The page treats "t" older than 3 hours as "baker down"; on a bad upstream answer
this script KEEPS the previous file and never writes garbage.

Usage:
    closures_bake.py                    one bake (systemd timer mode); exit 1 on failure
    closures_bake.py --loop             bake every --interval seconds (default 1800) forever
    closures_bake.py --out PATH         default /var/www/philly3d/closures.json
Stdlib only (zoneinfo needs Python 3.9+ and the system tzdata). No key."""
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

SERVICES = 'https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/'
CLOSURES = SERVICES + 'StreetSmartPHL/FeatureServer/1/query'      # the closure segments with PermitURL
ADDRESSES = SERVICES + 'LaneClosure_Master/FeatureServer/0/query'  # the same permits with an address
PAVING = SERVICES + 'StreetSmartPHL/FeatureServer/2/query'         # streets status for the paving season
MILL_WEEK = SERVICES + 'StreetSmartPHL/FeatureServer/3/query'      # this week's milling list
PAVE_WEEK = SERVICES + 'StreetSmartPHL/FeatureServer/4/query'      # this week's paving list
DEFAULT_OUT = '/var/www/philly3d/closures.json'
TZ = ZoneInfo('America/New_York')
TIMEOUT = 45.0
MAX_BYTES = 12 * 1024 * 1024
PAGE = 2000
MAX_PAGES = 8
USER_AGENT = 'philly3d-closures-bake/1 (+https://philly3d.com)'
HORIZON = 7 * 86400            # a permit starting later than this is not posted yet
CAP = 180 * 86400              # an open-ended permit is shown through this
NO_VOTE = re.compile(r'RELAXATION OF PARKING|DUMPSTER|CONTAINER|NO PARKING|LOADING ZONE|VALET', re.I)
NO_VOTE_TYPES = {'temporary no parking', 'temporary loading zone', 'temporary passenger loading zone'}
PAVED = {'paving complete / line striping pending', 'paving complete by penndot'}
MILLED = {'milling complete / street adjustments pending'}
ACRONYMS = {'PGW', 'PWD', 'PECO', 'SEPTA', 'PPA', 'PIDC', 'EUN', 'HVAC', 'ADA', 'NBC', 'AT&T', 'PENNDOT', 'DOT', 'ROW', 'PA', 'US', 'LLC', 'INC', 'II', 'III', 'IV'}
DASHES = re.compile(r'\s*[‒–—―·•]\s*')
URL_OK = re.compile(r'^https://stsweb\.phila\.gov/', re.I)

log = logging.getLogger('closures-bake')


# ---------------------------------------------------------------- the fetch
def fetch_json(url, params):
    req = urllib.request.Request(url + '?' + urllib.parse.urlencode(params), headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise RuntimeError('%s: http %s' % (url.split('/services/')[-1], e.code)) from None
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        raise RuntimeError('%s: %s' % (url.split('/services/')[-1], getattr(e, 'reason', e.__class__.__name__))) from None
    if len(raw) > MAX_BYTES:
        raise RuntimeError('%s: answer over %d bytes' % (url, MAX_BYTES))
    d = json.loads(raw.decode('utf-8'))
    if not isinstance(d, dict) or 'features' not in d:
        raise RuntimeError('%s: not a feature answer (%s)' % (url.split('/services/')[-1], str(d)[:120]))
    return d


def fetch_all(url, where, fields, geometry=True):
    """Every feature of a query, GeoJSON, paged by resultOffset until a short page."""
    feats, off = [], 0
    for _ in range(MAX_PAGES):
        d = fetch_json(url, {'where': where, 'outFields': fields, 'outSR': '4326', 'geometryPrecision': '5',
                             'returnGeometry': 'true' if geometry else 'false', 'orderByFields': 'OBJECTID',
                             'resultOffset': str(off), 'resultRecordCount': str(PAGE), 'f': 'geojson'})
        page = d.get('features') or []
        feats.extend(page)
        if len(page) < PAGE:
            break
        off += PAGE
    return feats


# ---------------------------------------------------------------- the projection
def clean(s):
    s = DASHES.sub(', ', str(s or ''))
    s = re.sub(r'\s*[\r\n]+\s*', ', ', s)
    s = re.sub(r'\s+', ' ', s).strip(' ,')
    return re.sub(r',(\s*,)+', ',', s)


def title(s):
    """Title case for the city's ALL CAPS purposes, the acronyms kept."""
    out = []
    for w in clean(s).split(' '):
        core = w.strip('(),.;:')
        if core.upper() in ACRONYMS or re.match(r'^[A-Z]-\d+$', core):
            out.append(w.upper())
        elif re.match(r'^\d+(ST|ND|RD|TH)$', core, re.I):
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:].lower())
    s = ' '.join(out)
    return re.sub(r'\b(Of|And|The|At|To|For|On|In)\b', lambda m: m.group(1).lower(), s)


def addr_case(s):
    """'2500 block of N 22ND ST' -> '2500 Block of N 22nd St', the direction letters kept."""
    s = title(s)
    return re.sub(r'\b([NSEW])\b', lambda m: m.group(1).upper(), s)


def occupancy(s):
    s = str(s or '').lower()
    if 'full' in s:
        return 3
    if 'sidewalk' in s or 'footway' in s:
        return 1
    if 'partial' in s:
        return 2
    return 2


def line_of(geom):
    """The segment's coordinates, the longest part of a multi-line, 5 decimals."""
    if not geom:
        return None
    t, c = geom.get('type'), geom.get('coordinates')
    if t == 'LineString':
        parts = [c]
    elif t == 'MultiLineString':
        parts = c or []
    else:
        return None
    parts = [p for p in parts if p and len(p) >= 2]
    if not parts:
        return None
    best = max(parts, key=len)
    out = [[round(float(p[0]), 5), round(float(p[1]), 5)] for p in best if len(p) >= 2]
    return out if len(out) >= 2 else None


def ms(v):
    try:
        return float(v) / 1000.0
    except (TypeError, ValueError):
        return None


def project_closures(feats, addr_by_permit, now):
    segs = {}
    for f in feats:
        p = f.get('properties') or {}
        eff, exp = ms(p.get('EffectiveDate')), ms(p.get('ExpirationDate'))
        if exp is None or exp < now:
            continue
        if eff is None:
            eff = now
        if eff > now + HORIZON:
            continue
        seg = str(p.get('SEG_ID') or '').strip()
        line = line_of(f.get('geometry'))
        if not seg or not line:
            continue
        purpose_raw = str(p.get('Purpose') or '')
        ptype = str(p.get('PermitType') or '').strip()
        vote = 0 if (NO_VOTE.search(purpose_raw) or ptype.lower() in NO_VOTE_TYPES) else occupancy(p.get('OccupancyType'))
        url = str(p.get('PermitURL') or '').strip()
        if not URL_OK.match(url):
            url = ''
        n = str(p.get('PermitNumber') or '').strip()
        rec = segs.get(seg)
        if rec is None:
            rec = segs[seg] = {'id': seg, 'o': 0, 'addr': '', 'g': line, 'permits': []}
        rec['o'] = max(rec['o'], vote)
        if not rec['addr'] and addr_by_permit.get(n):
            rec['addr'] = addr_case(addr_by_permit[n])
        rec['permits'].append({'n': n, 'type': title(ptype), 'why': title(purpose_raw),
                               'from': int(eff), 'until': int(min(exp, now + CAP)), 'url': url})
    out = []
    for rec in segs.values():
        if rec['o'] < 1:
            continue   # parking relaxations and dumpsters alone close nothing
        rec['permits'].sort(key=lambda q: -q['from'])
        rec['permits'] = rec['permits'][:4]
        out.append(rec)
    out.sort(key=lambda r: r['id'])
    return out


def midpoint(line):
    a, b = line[0], line[-1]
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


def project_paving(season_feats, mill_feats, pave_feats):
    out, mids = [], []
    for f in season_feats:
        p = f.get('properties') or {}
        st = str(p.get('STATUS') or '').strip().lower()
        k = 'paved' if st in PAVED else 'milled' if st in MILLED else None
        line = line_of(f.get('geometry'))
        if not k or not line:
            continue
        addr = p.get('BLOCK') or ' '.join(str(p.get(x) or '') for x in ('ON_STREET', 'FROM_STREET', 'TO_STREET'))
        out.append({'id': 's' + str(p.get('ObjectID') or p.get('OBJECTID') or len(out)), 'k': k, 'week': False, 'addr': addr_case(addr), 'g': line})
        mids.append(midpoint(line))
    for feats, k in ((mill_feats, 'milled'), (pave_feats, 'paved')):
        for f in feats:
            p = f.get('properties') or {}
            line = line_of(f.get('geometry'))
            if not line:
                continue
            mx, my = midpoint(line)
            if any(abs(mx - qx) * 85344 < 15 and abs(my - qy) * 110574 < 15 for qx, qy in mids):
                continue
            addr = p.get('Block') or ' '.join(str(p.get(x) or '') for x in ('OnStreet', 'FromStreet', 'ToStreetNa'))
            out.append({'id': 'w' + str(p.get('OBJECTID') or len(out)), 'k': k, 'week': True, 'addr': addr_case(addr), 'g': line})
            mids.append((mx, my))
    return out


def project(closure_feats, addr_rows, season_feats, mill_feats, pave_feats, now):
    """The output contract from the raw answers (see the module docstring)."""
    addr_by_permit = {}
    for f in addr_rows:
        p = f.get('properties') or {}
        n, a = str(p.get('permitnumber') or '').strip(), str(p.get('address') or '').strip()
        if n and a and n not in addr_by_permit:
            addr_by_permit[n] = a
    day = dt.datetime.fromtimestamp(now, TZ).strftime('%Y-%m-%d')
    return {'t': float(now), 'day': day,
            'closures': project_closures(closure_feats, addr_by_permit, now),
            'paving': project_paving(season_feats, mill_feats, pave_feats)}


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
def bake_once(out):
    now = time.time()
    try:
        closures = fetch_all(CLOSURES, 'ExpirationDate>=CURRENT_TIMESTAMP',
                             'PermitType,OccupancyType,PermitNumber,EffectiveDate,ExpirationDate,Purpose,Status,SEG_ID,PermitURL')
        addrs = fetch_all(ADDRESSES, 'expirationdate>=CURRENT_TIMESTAMP', 'permitnumber,address', geometry=False)
        season = fetch_all(PAVING, '1=1', 'STATUS,ON_STREET,FROM_STREET,TO_STREET,BLOCK')
        mill = fetch_all(MILL_WEEK, '1=1', 'OnStreet,FromStreet,ToStreetNa,Block,WeekOf')
        pave = fetch_all(PAVE_WEEK, '1=1', 'OnStreet,FromStreet,ToStreetNa,Block,WeekOf')
        obj = project(closures, addrs, season, mill, pave, now)
    except (RuntimeError, ValueError, TypeError) as e:
        log.warning('kept the previous file: %s', e)
        return False
    try:
        n = publish(out, obj)
    except OSError as e:
        log.warning('could not write %s: %s', out, e.__class__.__name__)
        return False
    full = sum(1 for r in obj['closures'] if r['o'] >= 3)
    log.info('wrote %s: %d closures (%d full) from %d permits, %d paving strips, %d bytes', out, len(obj['closures']), full, len(closures), len(obj['paving']), n)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--loop', action='store_true')
    ap.add_argument('--interval', type=float, default=1800.0)
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
    if not a.loop:
        return 0 if bake_once(a.out) else 1
    while True:
        t0 = time.time()
        try:
            bake_once(a.out)
        except Exception:
            log.exception('bake failed unexpectedly; continuing')
        time.sleep(max(1.0, a.interval - (time.time() - t0)))


if __name__ == '__main__':
    sys.exit(main())
