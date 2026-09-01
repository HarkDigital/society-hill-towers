#!/usr/bin/env python3
"""Append-only provenance log for the fetch_*.py scripts.

record(source, url, query, elements) appends one JSON line to
3d-model/provenance.jsonl right after a download succeeds:

  {"ts": "2026-09-01T18:04:11Z", "source": "fetch_wide.overpass",
   "url": "https://overpass-api.de/api/interpreter",
   "query_sha1": "…40 hex…", "query_head": "[out:json][timeout:170]; ( way[...",
   "elements": 109420, ...extra}

`query` may be the literal request text (Overpass QL, SQL, an ArcGIS parameter
string) or any JSON-serialisable object; its sha1 identifies exactly what was asked
without storing multi-KB query bodies. `elements` is a count, or anything with a
len() (the count is stored), or None. Extra keyword arguments ride along as-is
(tile ids, byte sizes).

record() never raises: a failed provenance write must not abort an hours-long
fetch. It returns the row written, or None."""
import datetime
import hashlib
import json
import pathlib

LOG = pathlib.Path(__file__).resolve().parent / 'provenance.jsonl'
HEAD_CHARS = 160


def _query_text(query):
    if query is None:
        return ''
    if isinstance(query, (bytes, bytearray)):
        return bytes(query).decode('utf-8', 'replace')
    if isinstance(query, str):
        return query
    return json.dumps(query, sort_keys=True, separators=(',', ':'), default=str)


def record(source, url, query, elements, **extra):
    """Append one provenance line; see the module docstring. Never raises."""
    try:
        q = _query_text(query)
        if isinstance(elements, bool) or elements is None:
            n = None
        elif isinstance(elements, int):
            n = elements
        elif hasattr(elements, '__len__'):
            n = len(elements)
        else:
            n = None
        row = {
            'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source': str(source),
            'url': str(url) if url is not None else None,
            'query_sha1': hashlib.sha1(q.encode('utf-8')).hexdigest(),
            'query_head': ' '.join(q.split())[:HEAD_CHARS],
            'elements': n,
        }
        for k, v in extra.items():
            row.setdefault(k, v)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row, sort_keys=True, default=str) + '\n')
        return row
    except Exception:
        return None


if __name__ == '__main__':
    import sys
    rows = LOG.read_text(encoding='utf-8').splitlines() if LOG.exists() else []
    print('%s: %d rows' % (LOG, len(rows)))
    for line in rows[-int(sys.argv[1]) if len(sys.argv) > 1 else -20:]:
        print(' ', line)
