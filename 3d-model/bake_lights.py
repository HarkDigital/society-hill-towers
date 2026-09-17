#!/usr/bin/env python3
"""lidar_cache/lights_raw/boma.json -> lights.json : BOMA Philadelphia's Building Illumination
Calendar parsed to dated colour rows for the skyline lights (Round 81). The page lights the
skyline crowns and the Ben Franklin Bridge in the night's colour: a Philadelphia game day's
team colour first (the page's own call from the scores), else the calendar's row for the date.
  {"t": <unix seconds of this bake, float>,
   "rows": [{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD",   # Philadelphia calendar days, inclusive
             "c": ["blue", "yellow"],                    # the colours, in the title's order
             "n": "Alopecia Areata Awareness Month"}, ...]}   # the cause, cleaned
The colour lives only in the title. parse_colors() takes every colour word of the lexicon
COLORS in order of first appearance (word-boundary, case-insensitive, entities unescaped,
duplicates removed), folding the aliases in ALIASES first so 'light blue' is lightblue and not
blue, 'dark pink' magenta, 'BOMA blue' blue, 'rainbow' the six; a title with no colour word
falls back to a keyword of the cause or the team (FALLBACK, first match wins: Go Birds is
green, the Phillies red, the Flyers orange, the 76ers blue, the Union blue and gold, Pride the
rainbow, the causes that recur on the calendar without naming their colour take the colour
their other, dated requests name), and a title neither knows is dropped and reported.
clean_name() drops the lighting instruction (the ' - LIGHT UP BLUE!' clause, a trailing
'(BLUE/YELLOW)', a leading 'Light up for'), every Squarespace '(Copy)', title-cases a name
that is all capitals, and turns every dash and middot into a comma (the HUD rule: never an em
dash or middot in a user-facing string). Dates are the local calendar days of the two instants
(America/New_York; an end at exactly midnight belongs to the day before). Rows are deduped on
(from, to, colours), rows that ended more than a year before the bake are dropped, and no
string may carry '</script' (build.py refuses the page).
Run with plain python3 for the pipeline (reads the cached raw file, writes lights.json, no .gz
twin, the repo never gains one); `bake_lights.py --fetch --out /var/www/philly3d/lights.json`
is the VPS mode (fetches in-process through fetch_lights.fetch_all, publishes with the
concerts writer: the .gz twin first, atomic, 0644, and keeps the previous file on a bad
answer). bake() and bake_rows() are pure so tests/test_lights_bake.py can feed them fixtures."""
import argparse
import datetime as dt
import gzip
import html
import json
import os
import re
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'lights_raw', 'boma.json')
OUT = os.path.join(HERE, 'lights.json')
TZ = ZoneInfo('America/New_York')
KEEP_DAYS = 365          # rows that ended longer ago than this are dropped

# ---------------------------------------------------------------- the lexicon
# name -> a representative hex, for the report and as a hint; the page carries its own palette
COLORS = {
    'white': 'ffffff', 'green': '00a651', 'red': 'e4002b', 'orange': 'f47a20', 'blue': '0057b8',
    'teal': '008c95', 'purple': '7b2cbf', 'pink': 'f28cb1', 'yellow': 'ffd200', 'gold': 'd4a017',
    'cyan': '00c2ff', 'magenta': 'e5007d', 'crimson': 'a6192e', 'gray': '9a9a9a', 'maroon': '6a0f2b',
    'burgundy': '7a1f3d', 'silver': 'c0c0c0', 'lavender': 'b57edc', 'navy': '1f2a5c', 'lightblue': '7fb7e6',
}
RAINBOW = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
ALIASES = {
    'grey': 'gray', 'light blue': 'lightblue', 'sky blue': 'lightblue', 'baby blue': 'lightblue',
    'dark pink': 'magenta', 'hot pink': 'magenta', 'aqua': 'cyan', 'turquoise': 'teal', 'lime': 'green',
    'amber': 'gold', 'boma blue': 'blue', 'violet': 'purple', 'orangeup': 'orange',   # '#OrangeUp for Kidney Cancer'
    'rainbow': RAINBOW,
}
# a team or a cause named without its colour, first match wins (the brief's list, then the
# causes that recur on this calendar without a colour word, in the colour their dated requests name)
FALLBACK = [
    (r'birds|eagles', ['green']),
    (r'phillies|phils|red october|paint the town red', ['red']),
    (r'flyers', ['orange']),
    (r'76ers|sixers', ['blue']),
    (r'\bunion\b', ['blue', 'gold']),
    (r'breast cancer|tatas', ['pink']),
    (r'\bpride\b', RAINBOW),
    (r'st\.?\s*patrick|greening', ['green']),
    (r'autism', ['blue']),
    (r'alzheimer', ['purple']),
    (r'childhood cancer|pediatric cancer', ['gold']),
    (r'ovarian', ['teal']),
    (r'pancreatic', ['purple']),
    (r'leukemia', ['orange']),
    (r'kidney|copd|prader', ['orange']),
    (r'sickle cell|hemophilia', ['red']),
    (r'lupus|epilepsy|vitiligo|naloxone|antibiotic', ['purple']),
    (r'holocaust|sarcoma', ['yellow']),
    (r'down syndrome|sudc', ['blue', 'yellow']),
    (r'donate life', ['blue', 'green']),
    (r'parkin?son|diabetes|angelman|rheumatic', ['blue']),
    (r'neuralgia|fragile x|pcos', ['teal']),
    (r'mitochondrial|mental health', ['green']),
    (r'diaphragmatic', ['blue', 'pink', 'yellow']),
    (r'drexel', ['blue', 'gold']),
    (r'transgender', ['lightblue', 'pink', 'white']),
    (r'philippine', ['blue', 'red', 'yellow']),
    (r'appendix cancer', ['gold']),
]
FALLBACK = [(re.compile(p, re.I), c) for p, c in FALLBACK]


def _alt(words):
    """A regex alternation, longest first so 'light blue' wins over 'blue'; spaces match any whitespace."""
    return '|'.join(r'\s+'.join(re.escape(w) for w in word.split()) for word in sorted(words, key=len, reverse=True))


CWORD = _alt(list(COLORS) + list(ALIASES))
COLOR_RE = re.compile(r'\b(?:%s)\b' % CWORD, re.I)
FILLER = r'\band/or\b|&/or|\b(?:and|or|for|the|in)\b|[&/,+!.:;\'"]'   # the separators and the small words between colours
TOKENS = r'(?:\s*(?:\b(?:%s)\b|%s))' % (CWORD, FILLER)       # one colour word or one filler token, whole words only
LIGHT_UP = r'(?:light(?:ing)?\s*(?:it\s*)?up|lights?\s+up|lit\s+up)'
LEAD = re.compile(r'^\s*["\'“”‘’(#]*\s*(?:%s|go\s+(?:%s))\b' % (LIGHT_UP, CWORD), re.I)   # a segment that opens with the instruction
LEAD_TAIL = re.compile(r'^%s*\s*' % TOKENS, re.I)                # the colours and filler after it
TRAIL = re.compile(r'[\s,:;.!-]*\b%s\b%s*\s*$' % (LIGHT_UP, TOKENS), re.I)   # '... Light up GREEN!' at the end
DASH_TAIL = re.compile(r'\s*[-‒–—―:]%s+\s*$' % TOKENS, re.I)    # 'Month -ORANGE' without the split's space
PAREN_TAIL = re.compile(r'\s*\(%s+\s*\)\s*$' % TOKENS, re.I)     # 'Day (BLUE/YELLOW)'
ONLY_COLORS = re.compile(r'^%s*\s*$' % TOKENS, re.I)             # nothing but colours, separators and filler
SPLIT = re.compile(r'\s*\|\s*|\s*[-‒–—―]\s+|\s+[-‒–—―]\s*')      # ' - ', ' | ', ' – ', 'Championship- '
COPY = re.compile(r'\(\s*copy\s*\)', re.I)
DASHES = re.compile('[‒–—―·•]')


def _canon(word):
    """A matched colour word -> its lexicon name(s), a list."""
    w = re.sub(r'\s+', ' ', word.lower())
    c = ALIASES.get(w, w)
    return list(c) if isinstance(c, list) else [c]


def parse_colors(title):
    """Every colour word of the title in order of first appearance; the fallback lexicon when it
    names none; [] when neither knows the title (the row is dropped)."""
    s = html.unescape(str(title or ''))
    out = []
    for m in COLOR_RE.finditer(s):
        for c in _canon(m.group(0)):
            if c not in out:
                out.append(c)
    if out:
        return out
    for rx, cols in FALLBACK:
        if rx.search(s):
            return list(cols)
    return []


def _title(s):
    """Title-case an all-capitals name; a letter after a digit stays lower (76ERS -> 76ers, 175TH -> 175th)."""
    s = re.sub(r"[A-Za-z][A-Za-z'’]*", lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(), s)
    return re.sub(r'(\d)([A-Z])', lambda m: m.group(1) + m.group(2).lower(), s)


def _tidy(s):
    """The HUD pass: dashes and middots to commas, 'Day!  Next' to 'Day, Next', whitespace
    collapsed, stray punctuation off the ends, capitals title-cased."""
    s = DASHES.sub(', ', s)
    s = re.sub(r'!+\s+', ', ', s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s+,', ',', s)
    s = re.sub(r',(\s*,)+', ',', s)
    s = s.strip(' !.,:;-|')
    if s and not any(ch.islower() for ch in s):
        s = _title(s)
    return s


def _segment(seg):
    """One separator-bounded piece of a title without its lighting instruction; '' when it was
    nothing else."""
    seg = seg.strip()
    m = LEAD.match(seg)
    if m:                                   # 'Light up BLUE for Xavier!' -> 'Xavier!'; 'LIGHT UP BLUE!' -> ''
        seg = LEAD_TAIL.sub('', seg[m.end():])
    else:                                   # 'GO BIRDS Light up GREEN!' -> 'GO BIRDS'
        seg = TRAIL.sub('', seg)
    seg = DASH_TAIL.sub('', seg)
    seg = PAREN_TAIL.sub('', seg)
    if ONLY_COLORS.match(seg):
        return ''
    return _tidy(seg)


def clean_name(title):
    """The cause's name: entities unescaped, every '(Copy)' gone, the lighting clause and the colour
    list gone, dashes to commas, capitals title-cased; the tidied title itself when nothing else is left."""
    raw = COPY.sub(' ', html.unescape(str(title or '')))
    parts = []
    for seg in SPLIT.split(raw):
        s = _segment(seg)
        if s and s.lower() not in [p.lower() for p in parts]:
            parts.append(s)
    # a piece that is only part of a longer piece says nothing new ('Rare' beside 'Rare Disease Day')
    parts = [p for p in parts if not any(p is not q and p.lower() in q.lower() for q in parts)]
    name = ', '.join(parts) or _tidy(raw)
    if '</script' in name.lower():
        raise ValueError('a name carries </script: ' + name[:80])
    return name


def local_dates(start_ms, end_ms):
    """The Philadelphia calendar day of each instant as 'YYYY-MM-DD'. An end in the first minutes
    after midnight belongs to the day before; an end before the start is the start."""
    a = dt.datetime.fromtimestamp(int(start_ms) / 1000, TZ)
    b = dt.datetime.fromtimestamp(int(end_ms) / 1000, TZ)
    if b.hour == 0 and b.minute < 5:
        b -= dt.timedelta(days=1)
    f, t = a.strftime('%Y-%m-%d'), b.strftime('%Y-%m-%d')
    return f, (t if t >= f else f)


def bake_rows(items, now_ts):
    """(rows, dropped): the rows of the contract from the raw items, and the titles no lexicon knew."""
    rows, dropped, seen = [], [], set()
    today = dt.datetime.fromtimestamp(float(now_ts), TZ).date()
    cutoff = (today - dt.timedelta(days=KEEP_DAYS)).isoformat()
    ordered = sorted((it for it in items or [] if isinstance(it, dict)),
                     key=lambda it: (it.get('startDate') or 0, it.get('endDate') or 0, str(it.get('id') or '')))
    for it in ordered:
        title = str(it.get('title') or '')
        try:
            s, e = int(it['startDate']), int(it['endDate'])
        except (KeyError, TypeError, ValueError):
            continue
        if s <= 0 or e <= 0:
            continue
        cols = parse_colors(title)
        if not cols:
            dropped.append(title.strip())
            continue
        f, t = local_dates(s, e)
        if t < cutoff:
            continue
        key = (f, t, tuple(cols))
        if key in seen:
            continue
        seen.add(key)
        rows.append({'from': f, 'to': t, 'c': cols, 'n': clean_name(title)})
    rows.sort(key=lambda r: (r['from'], r['to'], r['n']))
    return rows, dropped


def bake(items, now_ts):
    """The output contract (see the module docstring)."""
    rows, _ = bake_rows(items, now_ts)
    return {'t': float(now_ts), 'rows': rows}


# ---------------------------------------------------------------- the writer (concerts_bake's: temp file, fsync, 0644, replace; the .gz twin first)
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
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--fetch', action='store_true',
                    help='fetch the calendar in-process (fetch_lights.fetch_all) instead of reading lidar_cache/lights_raw/boma.json: the VPS mode')
    ap.add_argument('--out', default=None,
                    help='where to write (default lights.json beside this script); given explicitly, the file is published with its .gz twin')
    ap.add_argument('-v', '--verbose', action='store_true', help='print every row')
    a = ap.parse_args(argv)
    out = a.out or OUT
    vps = a.fetch or a.out is not None
    now = time.time()
    if a.fetch:
        try:
            import fetch_lights
            items = fetch_lights.fetch_all()
        except Exception as e:   # a dead feed, a bad answer: the previous file stands, its t goes stale on its own
            print(f'kept the previous file: the fetch failed: {e.__class__.__name__}: {e}', flush=True)
            return 1
    else:
        with open(RAW, encoding='utf-8') as f:
            items = json.load(f)
    rows, dropped = bake_rows(items, now)
    if not rows:
        print(f'kept the previous file: no rows parsed from {len(items)} items', flush=True)
        return 1
    obj = {'t': float(now), 'rows': rows}
    if vps:
        n = publish(out, obj)
    else:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(obj, f, separators=(',', ':'), ensure_ascii=False)
        n = os.path.getsize(out)
    print(f'{len(rows)} rows from {len(items)} items ({len(dropped)} without a colour dropped, '
          f'{len(items) - len(rows) - len(dropped)} older than a year or duplicates), '
          f'{rows[0]["from"]} to {rows[-1]["to"]}, {os.path.basename(out)} {n / 1e3:.1f} KB', flush=True)
    for t in dropped:
        print('  dropped, no colour:', repr(t))
    if a.verbose:
        for r in rows:
            print(f"  {r['from']}..{r['to']} {'/'.join(r['c']):24s} {r['n']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
