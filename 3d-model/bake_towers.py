#!/usr/bin/env python3
"""wide_landmarks_research.json + wide_names.json -> towers.json : one record per
Center City tower, joined to the packed buildings by position, carrying the facade
archetype, crown geometry, night accent and podium the app dresses it with.

  {"src": "...", "towers": [{"name", "x", "z", "h", "r", "hex", "glass", "facade",
                             "crown": {"type", "h"?, "steps"?}, "lit", "podium",
                             "matched", "sh"}, ...]}

Research buildings (155 across the three research areas) are kept when they are
real, built, inside the box and at least MIN_H tall; bridge towers, the proposed
Wharton Piers tower, the OUTSIDE BBOX entries, the Broad/Callowhill "edge" cluster,
the Convention Center halls and City Hall (custom model in the app) are skipped. Each is joined to a footprint
of scene_wide.json (then parts_wide.json, a tower's shaft is often a part):
  1. by name, within 300 m: the research name's distinctive tokens (IDF-weighted over
     every scene, part, research and wide name; number and street clashes veto) must
     cover the candidate's; the best candidate by name, then height, then distance.
     A name match whose scene height is under 0.65 x the research roof is only kept
     when no strong position match exists (OSM's "Six Penn Center" sits on an
     18-storey block north of Market; the 32-storey 1700 Market it describes is
     unnamed). A far name stage (800 m, strict) rescues research points that are
     simply wrong (CHOP Roberts is 560 m off).
  2. by position, within 200 m: candidates at least half the research height, scored
     d/250 + 3 |ln(scene h / research roof)|, best under 1.0. The research grid is a
     fixed-longitude street table, so its points drift ~0.17 m per metre from City Hall
     as the real grid rotates ~9.5 deg: south of Walnut and west of 20th they land
     80-260 m off, which is why a plain "tallest within 60 m" rule mis-joins there.
  3. else the research point itself, flagged matched: false.
The record's x, z are the matched centroid; h is the research height, sh the scene's.

Facade and crown come from a keyword pass over massing/notes plus the colour and
glass flags, then the OVERRIDES table (the owner's knowledge of the buildings) wins
by name. wide_names.json entries not already covered (same footprint within 20 m,
or a name match within 40 m of a matched record / 120 m of an unmatched one) are
added with facade by the scene's era word and a flat crown, then overridden too.

Frame: philly_frame.py. Stdlib only. TOWERS_VERBOSE=1 lists every record."""
import collections
import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
from philly_frame import to_xz   # the one scene frame

MIN_H = 45.0           # a "tower" for the app's purposes (tests/test_towers.py checks 45..400)
R_DEFAULT = 35         # join radius the app uses around x, z
STOREY_M = 4.4         # podium storeys -> metres when the massing gives only a count
NAME_R, FAR_R, POS_R = 300, 800, 200

FACADES = ('glass', 'glass_bands', 'glass_dark', 'concrete_grid', 'stone_piers', 'deco',
           'precast_bands', 'brick')
CROWNS = ('flat', 'notch', 'pyramid', 'stepped', 'custom', 'spire', 'lattice', 'ziggurat',
          'lantern', 'sloped', 'mansard', 'dome')
CROWN_H = {'notch': 8, 'pyramid': 20, 'spire': 15, 'lattice': 30, 'ziggurat': 25, 'lantern': 10,
           'sloped': 13, 'mansard': 10, 'dome': 15, 'stepped': 20}

# name tokens that carry no identity (building words shared by many)
STOP = {'building', 'tower', 'towers', 'center', 'centre', 'square', 'house', 'street', 'place',
        'hotel', 'apartments', 'apartment', 'philadelphia', 'residences', 'residence',
        'condominiums', 'condominium', 'downtown', 'plaza', 'church', 'the', 'and', 'at', 'of',
        'by', 'west', 'east', 'north', 'south', 'penn', 'former', 'ex', 'jr', 'blvd', 'boulevard',
        'for', 'inn', 'new', 'old', 'ave', 'sts', 'apt', 'ltd', 'llc', 'inc', 'del', 'van', 'der', 'von',
        'saint', 'st', 'mt', 'our', 'lady'}
NUMWORDS = {'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
            'eleven', 'twelve'}
ROMAN = {'i', 'ii', 'iii', 'iv'}
STREETS = {'market', 'chestnut', 'walnut', 'locust', 'spruce', 'pine', 'arch', 'race', 'vine',
           'broad', 'jfk', 'sansom', 'cherry', 'callowhill'}


# ---------------------------------------------------------------- the owner's override table
# (regex on the lower-cased name, first match wins; a dict of the fields it pins)
def C(t, h=None, **kw):
    d = {'type': t}
    if h is not None:
        d['h'] = h
    d.update(kw)
    return d


OVERRIDES = [
    (r'comcast technology', dict(facade='glass', crown=C('lantern', 18), lit='#ffe9c4')),
    (r'comcast center', dict(facade='glass', crown=C('notch', 8), lit='#cfe0ff')),
    (r'(one|two) liberty place', dict(facade='glass_bands', crown=C('custom'), lit='#dbe6ff')),
    (r'bny mellon', dict(facade='stone_piers', crown=C('lattice', 30), lit='#dfe8ff')),
    (r'three logan', dict(facade='deco', hex='#B36349', crown=C('ziggurat', 25, steps=3), lit='#ffd9a8')),
    (r'fmc tower', dict(facade='glass', crown=C('notch', 20))),
    (r'dibona', dict(facade='glass', crown=C('notch', 6))),
    (r'\belement\b', dict(facade='concrete_grid', crown=C('flat'))),          # The W and Element
    (r'\blaurel\b', dict(facade='glass', crown=C('flat'), podium=22)),
    (r'(one|two) commerce square', dict(facade='stone_piers', crown=C('notch', 6))),
    (r'arthaus', dict(facade='glass_bands', crown=C('flat'), podium=20)),
    (r'1818 market', dict(facade='glass_dark', crown=C('flat'))),
    (r'st\.? james', dict(facade='precast_bands', crown=C('flat'))),
    (r'psfs|loews', dict(facade='stone_piers', crown=C('spire', 14), lit='#ff5a5a')),
    (r'pnc bank', dict(facade='glass_bands', crown=C('flat'))),
    (r'peco building', dict(facade='concrete_grid', crown=C('flat'), lit='#ffb060')),
    (r'five penn center|six penn center|centre square|1500 locust|jefferson tower|academy house|'
     r'kennedy house|hopkinson house|penn center house|william penn house|rittenhouse plaza|'
     r'\bsterling\b|2400 chestnut|municipal services', dict(facade='concrete_grid', crown=C('flat'))),
    (r'murano', dict(facade='glass_bands', crown=C('flat'))),
    (r'one south broad', dict(facade='deco', crown=C('lantern', 8), lit='#ffe2b0')),
    (r'^cira centre', dict(facade='glass', crown=C('sloped', 25), lit='#9fd0ff')),
    (r'two logan', dict(facade='stone_piers', crown=C('pyramid', 22), lit='#c9f0d8')),
    (r'one logan', dict(facade='stone_piers', crown=C('flat'))),
    (r'^evo\b', dict(facade='glass_dark', crown=C('flat'))),
    (r'eleven penn', dict(facade='glass_bands', crown=C('flat'))),
    (r'2000 market|1650 arch', dict(facade='glass_dark', crown=C('flat'))),
    (r'the drake', dict(facade='deco', crown=C('mansard', 10))),
    (r'wells fargo|lewis tower|girard trust|bellevue|widener|north american|land title',
     dict(facade='deco', crown=C('flat'))),
    (r'1706 rittenhouse|^10 rittenhouse|residences at the ritz|1919 market|the alexander|the harper|'
     r'riverwalk|^icon\b', dict(facade='glass', crown=C('flat'))),
    (r'symphony house|ellington|barclay|carlyle|adelphia house|chancellor', dict(facade='warm', crown=C('flat'))),
    (r'waterfront square', dict(facade='precast_bands', crown=C('flat'))),   # the three sisters share one skin
]
SKIP_NAMES = (r'bridge', r'callowhill edge', r'city hall', r'convention center')   # the last: big-box halls, not a tower
SKIP_NOTES = ('not built', 'outside bbox', 'demolished')


# ----------------------------------------------------------------------------- names
def strip_parens(s):
    return re.sub(r'\([^)]*\)', ' ', s)


def norm(s):
    s = s.lower().replace('&', ' and ').replace("'", '')
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


def tokens(name):
    out = set()
    for t in norm(name).split():
        if t.isdigit() or t in NUMWORDS or t in ROMAN or (len(t) >= 3 and t not in STOP):
            out.add(t)
    return out


def is_num(t):
    return t.isdigit() or t in NUMWORDS


class Names:
    """IDF weights over every building name we know, and the name-alike score."""

    def __init__(self, names):
        df = collections.Counter()
        for n in names:
            for t in tokens(n):
                df[t] += 1
        self.df = df

    def w(self, t):
        if t in ROMAN:
            return 0.05
        n = self.df.get(t, 1)
        return 1.0 if n <= 2 else 0.5 if n <= 5 else 0.2 if n <= 10 else 0.1

    def score(self, research, cand):
        """0..1 how surely two building names are the same building: the research
        name's distinctive tokens (IDF-weighted) covered by the candidate's, less half
        the candidate's uncovered weight; a whole-leading-words match counts as 1.
        Zero on a number clash (One vs Two Commerce Square, 1818 vs 2000 Market) or a
        street clash (1500 Locust vs 1500 Walnut). Tried with and without the
        parenthesised addresses on both sides."""
        best = 0.0
        for a in (research, strip_parens(research)):
            for b in (cand, strip_parens(cand)):
                ta, tb = tokens(a), tokens(b)
                if not ta or not tb:
                    continue
                na, nb = {t for t in ta if is_num(t)}, {t for t in tb if is_num(t)}
                if na and nb and not (na & nb):
                    continue
                ra, rb = {t for t in ta if t in ROMAN}, {t for t in tb if t in ROMAN}
                if ra and rb and not (ra & rb):
                    continue
                sa, sb = ta & STREETS, tb & STREETS
                if sa and sb and not (sa & sb):
                    continue
                pa, pb = norm(a), norm(b)
                short, long_ = (pa, pb) if len(pa) <= len(pb) else (pb, pa)
                if len(short) >= 8 and (short == long_ or long_.startswith(short + ' ')):
                    return 1.0
                shared = sum(self.w(t) for t in ta & tb)
                if shared < 0.5:
                    continue
                # an address number the candidate lacks (OSM rarely names "210 W Rittenhouse") weighs a third
                cov = shared / sum(self.w(t) * (0.3 if t.isdigit() and t not in tb else 1.0) for t in ta)
                extra = sum(self.w(t) for t in tb - ta) / sum(self.w(t) for t in tb)
                best = max(best, cov - 0.5 * extra)
        return best


# ---------------------------------------------------------------------------- scene
def centroid(poly):
    n = float(len(poly))
    return sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n


class Grid:
    """100 m cells over footprint centroids for the radius queries."""
    CELL = 100.0

    def __init__(self, items):
        self.cells = collections.defaultdict(list)
        for it in items:
            self.cells[(int(math.floor(it['x'] / self.CELL)), int(math.floor(it['z'] / self.CELL)))].append(it)

    def near(self, x, z, r):
        c = self.CELL
        out = []
        for gx in range(int(math.floor((x - r) / c)), int(math.floor((x + r) / c)) + 1):
            for gz in range(int(math.floor((z - r) / c)), int(math.floor((z + r) / c)) + 1):
                for it in self.cells.get((gx, gz), ()):
                    d = math.hypot(it['x'] - x, it['z'] - z)
                    if d <= r:
                        out.append((d, it))
        return out


def load_footprints():
    scene = json.load(open(os.path.join(HERE, 'scene_wide.json'), encoding='utf-8'))
    bl = []
    for b in scene['buildings']:
        x, z = centroid(b['poly'])
        bl.append({'x': x, 'z': z, 'h': float(b['h']), 'name': b.get('name') or '', 'fa': b.get('fa'), 'kind': 'building'})
    parts = json.load(open(os.path.join(HERE, 'parts_wide.json'), encoding='utf-8'))
    pl = []
    for p in parts:
        x, z = centroid(p['poly'])
        pl.append({'x': x, 'z': z, 'h': float(p['h']), 'name': p.get('name') or '', 'fa': None, 'kind': 'part'})
    return bl, pl


def height_mismatch(sh, roof):
    return abs(math.log(sh / roof))


def match_footprint(name, x0, z0, hm, roof, names, bgrid, pgrid):
    """-> (footprint dict or None, how). roof is the research's occupied-roof height
    (the crown-less height the scene's h should agree with). See the module docstring."""
    def by_name(r, min_score):
        best = None
        for d, it in bgrid.near(x0, z0, r) + pgrid.near(x0, z0, r):
            if not it['name'] or it['h'] < 0.5 * hm:
                continue
            s = names.score(name, it['name'])
            if s < min_score:
                continue
            rank = s - 0.3 * height_mismatch(it['h'], roof) - d / 1000.0
            if best is None or rank > best[0]:
                best = (rank, d, it)
        return best

    def by_pos(r, cutoff):
        best = None
        for grid, tag in ((bgrid, 'pos'), (pgrid, 'pos part')):
            for d, it in grid.near(x0, z0, r):
                if it['h'] < 0.5 * hm:
                    continue
                s = d / 250.0 + 3.0 * height_mismatch(it['h'], roof)
                if s <= cutoff and (best is None or (s, d) < (best[0], best[3])):
                    best = (s, it, tag, d)
            if best:
                return best
        return None

    nm = by_name(NAME_R, 0.5)
    if nm and nm[2]['h'] >= 0.65 * roof:
        return nm[2], 'name'
    ps = by_pos(POS_R, 1.0)
    if nm:                      # a name on a footprint much lower than the research roof: only if nothing better sits nearby
        if ps and ps[0] <= 0.6 and height_mismatch(ps[1]['h'], roof) <= 0.18:
            return ps[1], ps[2] + ' (over a low name match)'
        return nm[2], 'name (low)'
    if ps:
        return ps[1], ps[2]
    far = by_name(FAR_R, 0.5)
    if far and 0.65 * roof <= far[2]['h'] <= 1.5 * roof + 15:
        return far[2], 'name far'
    return None, 'none'


# ------------------------------------------------------------------- classification
def is_warm(hex_):
    if not hex_:
        return None
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return r > b + 20 and r >= g


def parse_year(text):
    ys = [int(y) for y in re.findall(r'\b(1[89]\d\d|20[0-3]\d)\b', text)]
    return max(ys) if ys else None


DECO_WORDS = r'art[- ]deco|terra ?cotta|limestone|marble|brownstone|stucco|beaux[- ]arts|renaissance|gothic|romanesque|revival|victorian'


def classify_facade(text, hex_, glass, year):
    t = text
    old = year is not None and year < 1940
    if glass:
        if re.search(r'dark[- ](bronze|glass|gray glass|grey glass|gray/|grey/)|bronze/gray glass', t):
            return 'glass_dark'
        if re.search(r'\bbands?\b|spandrel|\bfins\b', t):
            return 'glass_bands'
        return 'glass'
    if re.search(DECO_WORDS, t) or (old and re.search(r'granite|stone|setback', t)):
        return 'deco'
    if re.search(r'\bbrick\b', t):
        return 'brick'
    if re.search(r'concrete (grid|frame)|precast concrete (grid|frame)|exposed concrete|gridded', t):
        return 'concrete_grid'
    if re.search(r'granite|\bpiers\b', t):
        return 'stone_piers'
    if 'precast' in t:
        return 'precast_bands' if (year or 0) >= 1990 else 'concrete_grid'
    if re.search(r'curtain wall|reflective', t):
        return 'glass_bands' if re.search(r'\bbands?\b|spandrel|\bfins\b', t) else 'glass'
    if re.search(r'\bspire|church|cathedral', t):
        return 'deco'
    return 'brick' if is_warm(hex_) else 'concrete_grid'


def roof_height(text, h):
    """the occupied roof / top floor height the massing gives below the total, else None"""
    for m in re.finditer(r'(?:main roof|top floor|flat roof at|roof(?: edge)?|apex)\s*~?(\d{2,3}(?:\.\d)?)\s*m', text):
        v = float(m.group(1))
        if 8 <= h - v <= 0.65 * h:
            return v
    return None


def classify_crown(text, h):
    t = re.sub(r'\bno spire\b', '', text)
    for pat, typ in ((r'lattice', 'lattice'), (r'ziggurat', 'ziggurat'), (r'stepped gable', 'stepped'),
                     (r'pyramid', 'pyramid'), (r'\bdome|barrel[- ]vault', 'dome'), (r'lantern', 'lantern'),
                     (r'\bspire|conical|belfry|campanile|steeple', 'spire'), (r'mansard', 'mansard'),
                     (r'slop(ed|es|ing) (crown|roof|parapet)|roof edge slopes', 'sloped'),
                     (r'notched|step(s|ped)? back|setbacks? (at|near) (the )?top|shallow setbacks|stepped at', 'notch')):
        if re.search(pat, t):
            c = {'type': typ}
            if typ == 'ziggurat':
                c['steps'] = 3
            rf = roof_height(t, h)
            c['h'] = int(round(h - rf)) if rf else CROWN_H[typ]
            return c
    if re.search(r'setbacks', t) and not re.search(r'flat roof|flat top', t):
        rf = roof_height(t, h)
        return {'type': 'notch', 'h': int(round(h - rf)) if rf else CROWN_H['notch']}
    return {'type': 'flat'}


def parse_podium(text):
    t = text
    m = re.search(r'(?:podium|base)\s*\(~?(\d+)\s*m\)', t) or re.search(r'base to ~?(\d+)\s*m', t)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)(?:-\d+)?[- ](?:storey|story|floor)s?\s+(?:[a-z/-]+\s+){0,3}?(?:podium|base)\b', t) \
        or re.search(r'podium\s*~?(\d+)\s+floors', t)
    if m:
        return int(round(int(m.group(1)) * STOREY_M))
    return 0


def facade_by_era(fa):
    era = fa[2] if fa and len(fa) > 2 else 8
    if era <= 3:
        return 'deco'
    if era in (6, 7):
        return 'glass'
    return 'concrete_grid'


def apply_overrides(rec, fa=None):
    n = rec['name'].lower()
    for pat, spec in OVERRIDES:
        if re.search(pat, n):
            for k, v in spec.items():
                if k == 'facade' and v == 'warm':
                    w = is_warm(rec['hex'])
                    if w is None:
                        era = fa[2] if fa and len(fa) > 2 else 8
                        w = era <= 3
                    v = 'brick' if w else 'precast_bands'
                rec[k] = dict(v) if isinstance(v, dict) else v
            return pat
    return None


# ------------------------------------------------------------------------------ main
def skip_reason(b):
    n = b.get('name', '').lower()
    if b.get('lat') is None or b.get('lon') is None:
        return 'no coordinates'
    for pat in SKIP_NAMES:
        if re.search(pat, n):
            return pat
    blob = ((b.get('notes') or '') + ' ' + (b.get('massing') or '')).lower()
    for w in SKIP_NOTES:
        if w in blob:
            return w
    if 'proposed' in n:
        return 'proposed'
    if (b.get('height_m') or 0) < MIN_H:
        return 'under %d m' % MIN_H
    return None


def main():
    research = json.load(open(os.path.join(HERE, 'wide_landmarks_research.json'), encoding='utf-8'))
    wide_names = json.load(open(os.path.join(HERE, 'wide_names.json'), encoding='utf-8'))
    buildings, parts = load_footprints()
    bgrid, pgrid = Grid(buildings), Grid(parts)
    names = Names([it['name'] for it in buildings + parts if it['name']]
                  + [b['name'] for a in research for b in a['buildings']] + [e['n'] for e in wide_names])

    records, via_of = [], {}
    skipped = collections.Counter()
    for area in research:
        for b in area['buildings']:
            why = skip_reason(b)
            if why:
                skipped[why] += 1
                continue
            name = b['name']
            if name.startswith('Lewis Tower'):          # one research entry for two towers; Academy House comes from wide_names
                name = 'Lewis Tower (Aria)'
            x0, z0 = to_xz(b['lat'], b['lon'])
            hm = float(b['height_m'])
            text = ((b.get('massing') or '') + ' ' + (b.get('notes') or '')).lower()
            roof = roof_height(text, hm) or hm
            fp, via = match_footprint(name, x0, z0, hm, roof, names, bgrid, pgrid)
            hex_ = (b.get('facade_color_hex') or None)
            if hex_:
                hex_ = hex_.upper()
            glass = bool(b.get('glass'))
            year = parse_year(text)
            rec = {
                'name': name,
                'x': round(fp['x'] if fp else x0, 1), 'z': round(fp['z'] if fp else z0, 1),
                'h': hm, 'r': R_DEFAULT,
                'hex': hex_, 'glass': glass,
                'facade': classify_facade(text, hex_, glass, year),
                'crown': classify_crown(text, hm),
                'lit': None,
                'podium': parse_podium(text),
                'matched': fp is not None,
                'sh': round(fp['h'], 1) if fp else None,
            }
            apply_overrides(rec, fp['fa'] if fp else None)
            records.append(rec)
            via_of[name] = via + (' <- ' + fp['name'] if fp and fp['name'] else '')

    # wide_names entries the research did not cover
    added = []
    for e in wide_names:
        cov = None
        for r in records:
            d = math.hypot(r['x'] - e['x'], r['z'] - e['z'])
            if d <= 20 or (d <= (40 if r['matched'] else 120) and names.score(e['n'], r['name']) >= 0.5):
                cov = r
                break
        if cov:
            continue
        fp = min(bgrid.near(e['x'], e['z'], 10), default=None, key=lambda di: di[0])
        fa = fp[1]['fa'] if fp else None
        rec = {
            'name': e['n'], 'x': float(e['x']), 'z': float(e['z']), 'h': float(e['h']), 'r': R_DEFAULT,
            'hex': None, 'glass': False, 'facade': facade_by_era(fa), 'crown': {'type': 'flat'},
            'lit': None, 'podium': 0, 'matched': fp is not None, 'sh': round(fp[1]['h'], 1) if fp else None,
        }
        apply_overrides(rec, fa)
        records.append(rec)
        added.append(rec['name'])
        via_of[rec['name']] = 'wide_names'

    for r in records:
        assert r['facade'] in FACADES, (r['name'], r['facade'])
        assert r['crown']['type'] in CROWNS, (r['name'], r['crown'])

    out = {
        'src': 'bake_towers.py: wide_landmarks_research.json (%d buildings) + wide_names.json (%d) joined to '
               'scene_wide.json / parts_wide.json footprints; facade + crown by keyword then the override table'
               % (sum(len(a['buildings']) for a in research), len(wide_names)),
        'towers': records,
    }
    path = os.path.join(HERE, 'towers.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    # ---- report
    matched = [r for r in records if r['matched']]
    unmatched = [r for r in records if not r['matched']]
    print('towers.json: %d records (%d from research, %d added from wide_names), %s bytes'
          % (len(records), len(records) - len(added), len(added), format(os.path.getsize(path), ',')))
    print('matched %d, unmatched %d' % (len(matched), len(unmatched)))
    print('skipped research entries: ' + ', '.join('%s %d' % kv for kv in skipped.most_common()))
    print('facade: ' + ', '.join('%s %d' % kv for kv in collections.Counter(r['facade'] for r in records).most_common()))
    print('crown:  ' + ', '.join('%s %d' % kv for kv in collections.Counter(r['crown']['type'] for r in records).most_common()))
    print('lit %d, podium %d' % (sum(1 for r in records if r['lit']), sum(1 for r in records if r['podium'])))
    vias = collections.Counter(v.split(' <- ')[0] for v in via_of.values())
    print('join: ' + ', '.join('%s %d' % kv for kv in vias.most_common()))
    if unmatched:
        print('unmatched: ' + '; '.join('%s (%.0f m)' % (r['name'], r['h']) for r in unmatched))
    if os.environ.get('TOWERS_VERBOSE'):
        for r in records:
            print('  %-58s %6.0f %6.0f h %5.1f sh %-6s %-13s %-9s lit %-8s pod %2d  %s'
                  % (r['name'][:58], r['x'], r['z'], r['h'], r['sh'], r['facade'], r['crown']['type'], r['lit'], r['podium'], via_of.get(r['name'], '')))


if __name__ == '__main__':
    main()
