#!/usr/bin/env python3
"""Download BOMA Philadelphia's Building Illumination Calendar (a Squarespace events
collection at bomaphila.com read with `?format=json`: the nights the city's building owners
are asked to light their crowns for a cause, one item per request with its title and its
start and end instants in epoch milliseconds) and write lidar_cache/lights_raw/boma.json:
a JSON list of the items trimmed to id, title, startDate, endDate, addedOn, updatedOn and
fullUrl, deduped by id, sorted by start. The collection pages by `offset` (30 items a page,
each page carrying an `upcoming` and a `past` list, `pagination.nextPage` false on the last:
seven pages in Sep 2026, 212 items from Dec 2022 to Nov 2026). No key, and no CORS header,
which is why this is a bake and not a fetch from the page. A polite pause between pages,
six tries with backoff like fetch_markets.py, a User-Agent that names the project.
Run with plain python3; bake_lights.py parses the titles to colours and writes lights.json
(and imports fetch_all for its --fetch mode on the VPS)."""
import datetime as dt
import json
import os
import time
import urllib.request
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'lights_raw')
OUT = os.path.join(RAW, 'boma.json')
BASE = 'https://www.bomaphila.com/building-illumination-calendar'
USER_AGENT = 'philly3d-lights-bake/1 (+https://philly3d.com)'
TIMEOUT = 30
PAUSE = 0.3          # seconds between pages
MAX_PAGES = 40       # 1,200 items; the collection holds a few hundred
KEEP = ('id', 'title', 'startDate', 'endDate', 'addedOn', 'updatedOn', 'fullUrl')


def page_url(offset=None):
    return BASE + '?format=json' + ('' if offset is None else '&offset=%d' % int(offset))


def get_json(url):
    """One page as parsed JSON; six tries with backoff, raises after the last."""
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                d = json.load(r)
            if not isinstance(d, dict) or 'collection' not in d:
                raise RuntimeError('not a Squarespace collection answer: ' + str(d)[:200])
            return d
        except Exception as e:
            if attempt == 5:
                raise
            print('retry after', e, flush=True)
            time.sleep(3 + 4 * attempt)


def trim(item):
    """The kept keys of one item, or None when it has no id or no dates."""
    if not isinstance(item, dict) or not item.get('id'):
        return None
    try:
        s, e = int(item['startDate']), int(item['endDate'])
    except (KeyError, TypeError, ValueError):
        return None
    out = {k: item.get(k) for k in KEEP}
    out['id'] = str(item['id'])
    out['title'] = str(item.get('title') or '')
    out['startDate'], out['endDate'] = s, e
    return out


def fetch_all(get=None):
    """Every item of the collection, trimmed, deduped by id, sorted by start. `get(url)` returns
    one page's parsed JSON; the default pulls it over https (tests inject their own)."""
    polite = get is None
    get = get or get_json
    out, seen = [], set()
    url = page_url()
    for _ in range(MAX_PAGES):
        d = get(url)
        for item in (d.get('upcoming') or []) + (d.get('past') or []) + (d.get('items') or []):
            t = trim(item)
            if t and t['id'] not in seen:
                seen.add(t['id'])
                out.append(t)
        pg = d.get('pagination') or {}
        if not pg.get('nextPage') or pg.get('nextPageOffset') is None:
            break
        url = page_url(pg['nextPageOffset'])
        if polite:
            time.sleep(PAUSE)
    out.sort(key=lambda it: (it['startDate'], it['id']))
    return out


def main():
    items = fetch_all()
    if not items:
        raise SystemExit('the calendar came back empty; the cache is unchanged')
    os.makedirs(RAW, exist_ok=True)
    with open(OUT + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=0)
    os.replace(OUT + '.tmp', OUT)
    if provenance:
        provenance.record('fetch_lights.squarespace', BASE, 'format=json (every offset page)', len(items))
    tz = dt.timezone(dt.timedelta(hours=-5))   # a rough Eastern day for the report only; bake_lights.py does the real calendar
    day = lambda ms: dt.datetime.fromtimestamp(ms / 1000, tz).strftime('%Y-%m-%d')
    print(f'wrote {len(items)} items, {day(items[0]["startDate"])} to {day(items[-1]["startDate"])} '
          f'-> lidar_cache/lights_raw/boma.json', flush=True)


if __name__ == '__main__':
    main()
