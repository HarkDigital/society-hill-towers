"""Round 225 (Stage 1 of the Nov 10 plan): the app carries only the art a phone can ask for.

Inside the app the page always takes the phone path (IN_APP forces isTouch), and artSrc answers a record's half copy
wherever it has one, so a full-size file with a half copy is never requested there. app/scripts/copy-web.mjs used to copy
the whole art folder into the bundle; it now copies the list app/scripts/art-touch.mjs makes from the page being copied,
365 files and 33,411,772 bytes lighter on Nov 10 (417 files, 10,173,156 bytes, of 782 and 43,584,928).

A phone path that asked for a file the bundle does not hold would fall silently to the procedural look (artImage answers
null after its retry), so these checks are the guard and they fail closed:

- the list IS artSrc's rule: the page's own artSrc line, cut from app.js and run under Node with isTouch true over every
  record of every manifest build.py inlines, answers exactly the files the list carries (plus the full-size files of the
  kinds KEEP_FULL names, none today);
- the built page names exactly the files the manifests name, so the list read from the page misses nothing;
- every art request in app.js goes through artSrc with a record's own half beside it, or is one of the few direct loads
  listed here, each of a file that has no half copy; a new call site of any other shape fails until it is looked at;
- and every MENTION of artImage and artSrc is one of those calls (the review of Round 225: a bare reference handed to
  .map, an alias, a call behind a string holding ' //' all passed a test that looked only for 'artImage('), every fetch
  is of a known feed, and the other ways a page can ask for a picture (an <img>, a loader, a .src) are counted;
- copy-web.mjs itself, run over the real page and art into a scratch folder, leaves exactly that list on disk, byte for
  byte, refuses a page that names a missing file, art the page's scan did not find, or a www that reaches into the source
  folder, each before it writes anything, and brings a stale folder to the list by name."""
from collections import Counter
import filecmp
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT.parent / 'app' / 'scripts'
PAGE = ROOT / 'society-hill-towers.html'
NODE = shutil.which('node')
ARTSRC = '  const artSrc = (full, half) => (isTouch && half ? half : full);\n'


def manifests():
    """build.py's art file list, read by membership: every manifest whose art the page can ask for."""
    b = (ROOT / 'build.py').read_text()
    names = re.findall(r'"([a-z0-9_]+\.json)"', b[b.index('ART_FILES = []'):b.index('const("NW_WATER"')])
    return sorted(set(names))


def is_art(v):
    return isinstance(v, str) and v.startswith('art/')


def records(o, out):
    """Every art path a manifest names, as artSrc is handed it: the path, and the same record's <key>Half beside it (or None).
    Round 227: a record's sharp copy, <key>Sharp, is handed with the record's own <key>Half (people_art.json's imgSharp
    with its imgHalf), so a phone takes the half in its place."""
    if isinstance(o, dict):
        for k, v in o.items():
            if is_art(v):
                h = o.get((k[:-5] if k.endswith('Sharp') else k) + 'Half')
                out.append((v, h if is_art(h) else None))
            else:
                records(v, out)
    elif isinstance(o, list):
        for v in o:
            if is_art(v):
                out.append((v, None))
            else:
                records(v, out)
    return out


def pairs():
    out = []
    for m in manifests():
        records(json.loads((ROOT / m).read_text()), out)
    return out


def kind(p):
    return p.split('/')[1]


_ran = {}


def rule():
    """The page's artSrc line and the app's list, run once under Node over the shipped manifests and the built page."""
    if 'r' in _ran:
        return _ran['r']
    src = (ROOT / 'app.js').read_text()
    assert src.count(ARTSRC) == 1, 'artSrc is one line of app.js, the one this test runs'
    js = r'''
const fs = require('node:fs'), { pathToFileURL } = require('node:url');
const IN = JSON.parse(fs.readFileSync(0, 'utf8'));
(async () => {
  const M = await import(pathToFileURL(IN.module).href);
  const pick = (isTouch) => new Function('isTouch', IN.artSrc + '  return artSrc;')(isTouch);
  const touch = pick(true), computer = pick(false);
  const named = [...new Set(IN.pairs.map((p) => p[0]))].sort();
  const now = M.artTouch(named);
  console.log(JSON.stringify({
    touch: IN.pairs.map((p) => touch(p[0], p[1] || undefined)), computer: IN.pairs.map((p) => computer(p[0], p[1] || undefined)),
    carry: now.carry, leave: now.leave, keepFull: [...M.KEEP_FULL].sort(),
    fronts: M.artTouch(named, new Set(['fronts'])), none: M.artTouch(named, new Set()),
    page: M.artNamed(fs.readFileSync(IN.page, 'utf8')),
  }));
})().catch((e) => { console.error(e); process.exit(1); });
'''
    r = subprocess.run([NODE, '-e', js], input=json.dumps({'module': str(SCRIPTS / 'art-touch.mjs'), 'artSrc': ARTSRC, 'pairs': pairs(), 'page': str(PAGE)}),
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    _ran['r'] = json.loads(r.stdout)
    return _ran['r']


@unittest.skipUnless(NODE, 'node is not installed')
class TheListIsArtSrc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = pairs()
        cls.named = {f for f, _ in cls.pairs}
        cls.r = rule()

    def test_the_manifests_are_all_read(self):
        self.assertGreaterEqual(len(manifests()), 24)
        self.assertGreater(len(self.named), 400)
        self.assertGreater(sum(1 for _, h in self.pairs if h), 300)

    def test_the_app_carries_exactly_what_artSrc_answers_on_a_phone(self):
        r = self.r
        carry, leave, answers = set(r['carry']), set(r['leave']), set(r['touch'])
        self.assertEqual(carry | leave, self.named)
        self.assertEqual(carry & leave, set())
        self.assertEqual(len(r['carry']) + len(r['leave']), len(self.named), 'no file twice')
        self.assertEqual(answers - carry, set(), 'a phone can ask for a file the app does not carry: it would draw the procedural look in silence')
        kept_full = {f for f, h in self.pairs if h and kind(f) in r['keepFull']}
        self.assertEqual(carry, answers | kept_full, 'the app carries a file no phone path asks for')

    def test_what_is_left_out_is_a_full_size_file_whose_half_is_carried(self):
        r = self.r
        carry, leave = set(r['carry']), set(r['leave'])
        halves = {}
        for f, h in self.pairs:
            halves.setdefault(f, set()).add(h)
        self.assertGreater(len(leave), 300)
        for f in leave:
            self.assertNotIn(None, halves[f], f + ' is named somewhere without a half copy beside it')
            self.assertLessEqual(halves[f], carry, f)
            self.assertNotIn('-half.', f.split('/')[-1])
        # and the saving is the larger part of the folder, as measured (76.7% of its bytes on Nov 10)
        size = lambda ps: sum((ROOT / p).stat().st_size for p in ps)
        self.assertGreater(size(leave), 2 * size(carry))

    def test_the_line_run_is_the_pages_own(self):
        r = self.r
        # a computer takes every record's own file, a phone its half where there is one: the cut is the real selector
        self.assertEqual(r['computer'], [f for f, _ in self.pairs])
        self.assertEqual(r['touch'], [h or f for f, h in self.pairs])
        s = (ROOT / 'app.js').read_text()
        self.assertIn("  const isTouch = window.matchMedia('(pointer: coarse)').matches || IN_APP;\n", s, 'the app always takes the phone path')
        self.assertEqual(len(re.findall(r'\bisTouch\s*=[^=]', s)), 1, 'isTouch is set once')
        self.assertEqual(len(re.findall(r'\bartSrc\s*=[^=>]', s)), 1, 'artSrc is defined once')

    def test_the_table_is_keyed_by_art_kind(self):
        r = self.r
        kinds = {kind(p) for p in self.named}
        self.assertEqual({p.name for p in (ROOT / 'art').iterdir() if p.is_dir()}, kinds)
        # empty today. A kind that keeps its full size must also be asked for by the page (its artSrc call), and this pin
        # moves in the same commit: until then its full-size files would ride in the bundle unread
        self.assertEqual(r['keepFull'], [])
        self.assertLessEqual(set(r['keepFull']), kinds)
        self.assertEqual(r['none'], {'carry': r['carry'], 'leave': r['leave']})
        fronts = {f for f, h in self.pairs if h and kind(f) == 'fronts'}
        self.assertGreater(len(fronts), 16)
        self.assertEqual(set(r['fronts']['carry']), set(r['carry']) | fronts, 'a kept kind brings back its full-size files and nothing else')
        self.assertEqual(set(r['fronts']['leave']), set(r['leave']) - fronts)

    def test_the_built_page_names_what_the_manifests_name(self):
        # copy-web.mjs reads its list from the page it copies; a manifest inlined any other way would be missed there
        self.assertEqual(set(self.r['page']), self.named)
        self.assertEqual(self.r['page'], sorted(self.named))


def strip_comments(s):
    """Line comments out (a '//' after white space or at a line's start, so a URL inside a string stays). It knows nothing
    of strings, so a string holding ' //' loses the rest of its line: test_every_mention_is_a_call holds it to account."""
    return re.sub(r'(^|[ \t])//[^\n]*', r'\1', s, flags=re.M)


def mentions(src, name):
    """How often a name stands in src as a whole word, called or not."""
    return len(re.findall(r'(?<![\w$])' + re.escape(name) + r'(?![\w$])', src))


def calls(src, name):
    """Every call name(...) in src: its argument text, brackets and quotes balanced."""
    out = []
    for m in re.finditer(r'(?<![\w.$])' + re.escape(name) + r'\(', src):
        j, depth, q = m.end(), 1, None
        while depth:
            c = src[j]
            if q:
                if c == '\\':
                    j += 1
                elif c == q:
                    q = None
            elif c in '\'"`':
                q = c
            elif c in '([{':
                depth += 1
            elif c in ')]}':
                depth -= 1
            j += 1
        out.append(src[m.end():j - 1])
    return out


def args(text):
    out, depth, q, a, i = [], 0, None, 0, 0
    while i < len(text):
        c = text[i]
        if q:
            if c == '\\':
                i += 1
            elif c == q:
                q = None
        elif c in '\'"`':
            q = c
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ',' and not depth:
            out.append(text[a:i].strip())
            a = i + 1
        i += 1
    out.append(text[a:].strip())
    return out


def own_half(a, b):
    """artSrc(a, b) hands a record's field and the same record's <field>Half: A.img, A.imgHalf or A[k], A[k + 'Half'];
    or (Round 227) a record's sharp copy and that record's half: A.imgSharp, A.imgHalf."""
    return b == a + 'Half' or (a.endswith(']') and b == a[:-1] + " + 'Half']") or (a.endswith('Sharp') and b == a[:-5] + 'Half')


def region(src, start, end='\n  }\n'):
    i = src.index(start)
    return src[i:src.index(end, i)]


class EveryRequestGoesThroughArtSrc(unittest.TestCase):
    """Pure text, so it runs wherever the suite does."""
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / 'app.js').read_text()
        cls.s = strip_comments(cls.raw)
        cls.rebuilds_raw = ''.join(p.read_text() for p in sorted((ROOT / 'rebuilds').glob('*.js')))
        cls.rebuilds = strip_comments(cls.rebuilds_raw)

    def test_artImage_is_asked_through_artSrc(self):
        got = calls(self.s, 'artImage')
        through = [a for a in got if a.startswith('artSrc(')]
        for a in through:
            inner = calls(a, 'artSrc')
            self.assertEqual(['artSrc(' + inner[0] + ')'], [a], a)
        self.assertGreaterEqual(len(through), 40)   # 44 on Nov 10
        # the rest, each accounted for below: the definition's own parameter; a prefetched blob's URL, then the same artSrc
        # answer again if the blob did not decode (gloryLoad, sfArtLoad); and three direct loads of files with no half copy
        direct = Counter(a for a in got if not a.startswith('artSrc('))
        self.assertEqual(direct, Counter({'src': 3, 'url || src': 2, 'T.mask': 2, 'GLASS_DATA.rooms.rooms': 1}),
                         'an art request that does not go through artSrc: if its record has a half copy the app no longer carries the full file')
        self.assertEqual(calls(self.rebuilds, 'artImage') + calls(self.rebuilds, 'artSrc'), [], 'the rebuilds load art through the page')

    def test_every_mention_is_a_call(self):
        # The tests beside this one read CALLS, the text 'artImage(' and 'artSrc('. The review of Round 225 walked round
        # them four ways on a scratch app.js, each asking the app for a full-size file it no longer carries: a bare
        # reference ([NJ_ART.img].map(artImage)), an alias ((artImage)(x), artImage.apply), a method (api.artImage(x) in a
        # rebuild), and a call behind a string holding ' //', which strip_comments cut away. So: every mention is a call.
        s, raw = self.s, self.raw
        self.assertEqual(mentions(s, 'artImage'), len(calls(s, 'artImage')),
                         'artImage is named somewhere it is not called (its definition reads as one call): a reference or an alias is a way to a picture this test cannot follow')
        self.assertEqual(s.count(ARTSRC), 1)
        self.assertEqual(mentions(s, 'artSrc'), len(calls(s, 'artSrc')) + 1, 'artSrc is named somewhere other than its one definition and its calls')
        for name in ('artImage', 'artSrc'):
            self.assertEqual(len(re.findall(r'[\w$]*' + name + r'[\w$]*', s)), mentions(s, name), 'a name built on ' + name)
            self.assertEqual(s.count(name + '('), len(calls(s, name)), name + ' called behind a dot')
        # nothing of either name was cut away with a comment that was not one. A line that is a comment whole is left out;
        # on every other line the cut must take no mention with it, apart from the one trailing comment that names artSrc
        cut = [ln.strip() for ln in raw.split('\n') if not ln.lstrip().startswith('//')
               and any(mentions(ln, n) != mentions(strip_comments(ln), n) for n in ('artImage', 'artSrc'))]
        self.assertEqual(cut, ['if (!waterArtLoad.started) waterArtLoad();   // the generated deck and white water (artSrc is ready by the first frame)'],
                         "artImage or artSrc after ' //' on a line of code: if that is code behind a string and not a comment, this test did not read it")
        self.assertNotIn('/*', ''.join(ln for ln in raw.split('\n') if 'artImage' in ln or 'artSrc' in ln), 'a block comment on a line this test reads')
        # and the rebuilds do not name them at all, comments included (they load art through the page: api.artImage would
        # be a method call the call reader does not see)
        for name in ('artImage', 'artSrc'):
            self.assertNotIn(name, self.rebuilds_raw)

    def test_the_blob_paths_carry_an_artSrc_answer(self):
        s = self.s
        self.assertEqual(s.count('  function artImage(src) {\n'), 1)
        retry = 'return artImage(url || src).then((im) => (im || !url ? im : artImage(src))).then((im) => {'
        glory = region(s, '  function gloryLoad(tex, full, half, then, pre) {')
        self.assertIn('    const src = artSrc(full, half);\n', glory)
        self.assertEqual(glory.count(retry), 1)
        shop = region(s, '  function sfArtLoad() {')
        self.assertIn('    const one = (p, src) => Promise.resolve(p).then((blob) => {\n', shop)
        self.assertEqual(shop.count(retry), 1)
        ones = [args(a) for a in calls(shop, 'one')]
        self.assertEqual(len(ones), 2)
        for a in ones:
            self.assertTrue(a[1].startswith('artSrc('), a)
        self.assertEqual(s.count(retry), 2)

    def test_artSrc_is_handed_a_record_and_its_own_half(self):
        s = self.s
        got = [args(a) for a in calls(s, 'artSrc')]
        self.assertGreaterEqual(len(got), 50)   # 53 on Nov 10: the 44, the prefetches' eight and gloryLoad's own
        passed = Counter()
        for a in got:
            self.assertEqual(len(a), 2, a)
            if not own_half(a[0], a[1]):
                passed[tuple(a)] += 1
        # the four that hand on their caller's pair, each caller checked below
        stadium = '[A.wallsHalf, A.seatsHalf, A.grassHalf, A.clayHalf, A.boardHalf][i]'
        self.assertEqual(passed, Counter({('full', 'half'): 2, ('f', 'h'): 1, ('full', stadium): 1}),
                         'artSrc handed something other than a record and its own half: the app carries a file by that pairing')
        # gloryLoad(tex, full, half, ...)
        glory = [args(a) for a in calls(s, 'gloryLoad') if args(a)[:3] != ['tex', 'full', 'half']]
        self.assertEqual(len(glory), 4)
        for a in glory:
            self.assertTrue(own_half(a[1], a[2]), a)
        # a front set's two pictures
        fronts = region(s, '    const load = (full, half, tex) => artImage(artSrc(full, half)).then((im) => {')
        loads = [args(a) for a in calls(fronts, 'load')]
        self.assertEqual([a[:2] for a in loads], [['S.img', 'S.imgHalf'], ['S.mask', 'S.maskHalf']])
        # the container ships' two
        ships = region(s, '    const load = (f, h, cb) => artImage(artSrc(f, h)).then((im) => {')
        loads = [args(a) for a in calls(ships, 'load')]
        self.assertEqual([a[:2] for a in loads], [['C.side', 'C.sideHalf'], ['C.end', 'C.endHalf']])
        # the stadiums' five, the halves in the fulls' order
        self.assertIn('Promise.all([A.walls, A.seats, A.grass, A.clay, A.board].map((full, i) => artImage(artSrc(full, ' + stadium + ')))).then((ims) => {', s)
        self.assertEqual([x.strip() + 'Half' for x in 'A.walls, A.seats, A.grass, A.clay, A.board'.split(',')], [x.strip() for x in stadium[1:-4].split(',')])

    def test_the_direct_loads_name_files_with_no_half(self):
        s = self.s
        # the tower tiles' and the skin bases' masks, and the glass towers' rooms (a computer's: a phone never draws them)
        self.assertIn('const T = FRONTS_DATA.tiles[kind]; return [kind, Promise.all([artImage(artSrc(T.img, T.imgHalf)), artImage(T.mask)])];', s)
        self.assertIn('const T = SKIN_BASES[b]; return [b, Promise.all([artImage(artSrc(T.img, T.imgHalf)), artImage(T.mask)])];', s)
        self.assertIn("  const SKIN_BASES = REAL && typeof FRONTS_DATA !== 'undefined' && FRONTS_DATA && FRONTS_DATA.bases ? FRONTS_DATA.bases : null;\n", s)
        self.assertIn('    artImage(GLASS_DATA.rooms.rooms).then((rooms) => {\n', s)
        named = {f for f, _ in pairs()}
        stems = {p.rsplit('/', 1)[0] + '/' + p.rsplit('/', 1)[1].split('.')[0] for p in named}
        twin = lambda p: p.rsplit('/', 1)[0] + '/' + p.rsplit('/', 1)[1].split('.')[0] + '-half' in stems
        F = json.loads((ROOT / 'fronts.json').read_text())
        masks = [T for group in ('tiles', 'bases') for T in F[group].values()]
        self.assertGreater(len(masks), 40)
        for T in masks:
            self.assertNotIn('maskHalf', T)
            self.assertFalse(twin(T['mask']), T['mask'])
        G = json.loads((ROOT / 'glass_art.json').read_text())
        self.assertNotIn('roomsHalf', G['rooms'])
        self.assertFalse(twin(G['rooms']['rooms']), G['rooms']['rooms'])

    def test_no_other_way_to_an_art_file(self):
        s = self.s
        # the two prefetches take their bytes with fetch, both of an artSrc answer
        self.assertEqual(s.count('fetch(src)'), 2)
        self.assertIn("  const gloryBytes = (src) => (!src || typeof fetch !== 'function' ? Promise.resolve(null) : fetch(src).then((r) => (r.ok ? r.blob() : null)).catch(() => null));\n", s)
        for a in calls(s, 'gloryBytes'):
            self.assertTrue(a.startswith('artSrc('), a)
        pre = region(s, '  function sfArtPrefetch() {')
        self.assertIn("    const get = (src) => (!src || typeof fetch !== 'function' ? Promise.resolve(null) : fetch(src).then((r) => (r.ok ? r.blob() : null)).catch(() => null));\n", pre)
        gets = calls(pre, 'get')
        self.assertEqual(len(gets), 2)
        for a in gets:
            self.assertTrue(a.startswith('artSrc('), a)
        # fetch is called, never handed on (the two typeof tests apart), and every call is of a known feed or of `src`,
        # the two prefetches above. A new feed is added here; a fetch of a record's picture never is: it goes through
        # artSrc, or the app is asked for a file it does not carry
        got = Counter(args(a)[0] for a in calls(s, 'fetch'))
        self.assertEqual(sum(got.values()), len(re.findall(r'\bfetch\(', s)), 'a fetch behind a dot')
        self.assertEqual(s.count("typeof fetch !== 'function'"), 2)
        self.assertEqual(mentions(s, 'fetch') - sum(got.values()), 2, 'fetch is named somewhere it is not called')
        feeds = Counter({
            'src': 2, 'url': 2, 'u': 1,   # the art prefetches; the beacon and the Amtrak pull; the weather stations
            'SEPTA_BAKED': 1, 'SEPTA_V2 + path': 1, 'CARTO_SQL + encodeURIComponent(q)': 1, 'SCORE_URL(k)': 1,
            "SCORE_URL(t.k) + '?dates=' + key.replace(/-/g, '')": 1, 'CONCERTS_URL': 1, 'INDEGO_URL': 1, 'FLIGHT_HOSTS[FLIGHTS.host]': 1,
            'AIS_RELAY': 1, 'LIGHTS_URL': 1, 'CLOSURES_URL': 1, 'LIGHTNING_URL': 1, 'ALERT_SITES_URL': 1, 'AQI_URL': 1,
        })
        web = Counter({a: n for a, n in got.items() if a.startswith("'https://")})
        self.assertEqual(sorted(a.split('?')[0] for a in web), ["'https://api.open-meteo.com/v1/forecast", "'https://nominatim.openstreetmap.org/search"])
        self.assertEqual(got - web, feeds, 'a fetch this test does not know: an art file is fetched as an artSrc answer, a new feed is added to this list')
        self.assertIn("    fetch(url, { cache: 'no-store', signal: ctl ? ctl.signal : undefined })\n", region(s, '  function amtrakFetch(url, ms, ok, miss) {'))
        self.assertIn('    const get = (u) => fetch(u, opts).then((r) => (r && r.ok ? r.json() : null)).catch(() => null);\n', region(s, '  function fetchNws() {'))
        self.assertIn("try { fetch(url, { method: 'POST', keepalive: true, referrerPolicy: 'no-referrer'", s)
        # the other ways a page asks for a picture, counted: none of them reaches an art file today, and one that does
        # tomorrow fails here until it is looked at
        for pat in (r'Loader\b', r'''createElement\(\s*['"`](?:img|image|picture|video|source|link|iframe|object|embed|svg)\b''',
                    r'''setAttribute\(\s*['"`](?:src|href)''', r'srcset', r'\burl\(', r'XMLHttpRequest', r'importScripts', r'new Worker\b', r'\.loadAsync\b'):
            self.assertIsNone(re.search(pat, s), pat + ': a way to an image file that is not artImage(artSrc(...))')
            self.assertIsNone(re.search(pat, self.rebuilds), pat + ' in a rebuild')
        for pat in (r'\bfetch\b', r'new Image\b', r'createImageBitmap', r'\.src\s*=(?!=)', r'<img'):
            self.assertIsNone(re.search(pat, self.rebuilds), pat + ' in a rebuild')
        # createImageBitmap is handed a picture artImage answered, never a path or bytes of its own (Round 189's SF_BITMAP)
        self.assertEqual(mentions(s, 'createImageBitmap'), 2)
        self.assertIn("    if (isTouch || typeof createImageBitmap !== 'function' || typeof navigator === 'undefined') return false;\n", s)
        shop = region(s, '  function sfArtLoad() {')
        self.assertIn("      const dec = (im) => (!im ? im : createImageBitmap(im, { imageOrientation: 'flipY', premultiplyAlpha: 'none' }).then((b) => b, () => im));\n", shop)
        self.assertIn('      sfArtP = Promise.all([artImage(artSrc(A.img, A.imgHalf)).then(dec), artImage(artSrc(A.mask, A.maskHalf)).then(dec)]);\n', shop)
        self.assertEqual(mentions(shop, 'dec'), 3, 'the decoder is handed something other than those two answers')
        # every .src that is set: the analytics script, artImage's own image, the two JSONP scripts, the street names'
        # atlas from inlined bytes, and the skyline theme's source word (not an element)
        self.assertEqual(Counter(re.findall(r'([\w$.\]]+)\.src\s*=(?!=)', s)), Counter({'script': 2, 'ga': 1, 'im': 1, 'img': 1, 'THEME': 1}))
        # the two <img> the cards write are ESPN's and Ticketmaster's own pictures, never an art file
        self.assertEqual(s.count('<img'), 2)
        for field in ('g.logo', 'first.image'):
            self.assertEqual(s.count('\'<img class="logo" alt="" src="\' + septaEsc(' + field + ') + \'" onerror="this.remove()">\''), 1, field)
        # two images are made in the page: artImage's, and the street names' atlas from the bytes the page inlines
        self.assertEqual(s.count('new Image()'), 2, 'a new image loader: an art file must come through artImage(artSrc(...))')
        self.assertEqual(s.count('im.src = src;'), 1)
        self.assertIn("img.src = 'data:image/png;base64,' + ST_SDF.png;", s)
        # and no art path is written into the page's own source, only into the manifests it inlines
        for f in ('app.js', 'template.html', 'style.css'):
            self.assertIsNone(re.search(r'''["'`]art/''', (ROOT / f).read_text()), f)
        self.assertIsNone(re.search(r'''["'`]art/''', self.rebuilds))


def copy_web(src=None, www=None):
    env = dict(os.environ)
    env.pop('SHT_APP_SRC', None)
    if src:
        env['SHT_APP_SRC'] = str(src)
    env['SHT_APP_WWW'] = str(www)
    return subprocess.run([NODE, str(SCRIPTS / 'copy-web.mjs')], capture_output=True, text=True, timeout=300, env=env)


def held(www):
    return {str(f.relative_to(www)) for f in (www / 'art').rglob('*') if f.is_file()} if (www / 'art').exists() else set()


@unittest.skipUnless(NODE, 'node is not installed')
class CopyWeb(unittest.TestCase):
    def test_the_real_page_and_art(self):
        r0 = rule()
        carry = set(r0['carry'])
        with tempfile.TemporaryDirectory() as d:
            www = Path(d) / 'www'
            r = copy_web(www=www)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn('copy-web', r.stderr, 'the art folder holds nothing the page does not name')
            self.assertTrue(filecmp.cmp(PAGE, www / 'index.html', shallow=False))
            self.assertEqual(held(www), carry)
            self.assertEqual({p.name for p in www.iterdir()}, {'index.html', 'art'})
            for p in carry:
                self.assertTrue(filecmp.cmp(ROOT / p, www / p, shallow=False), p)
            # both totals, in the files' own counts and megabytes
            size = lambda ps: '%.1f' % (sum((ROOT / p).stat().st_size for p in ps) / 1e6)
            n, left, named = len(carry), r0['leave'], r0['carry'] + r0['leave']
            self.assertIn('www/art <- 3d-model/art: the %d files a phone can ask for, %s MB (%d copied, 0 already there, 0 removed)' % (n, size(carry), n), r.stdout)
            self.assertIn('left out: %d full-size files with a half copy, %s MB, of the %d files, %s MB, the page names' % (len(left), size(left), len(named), size(named)), r.stdout)
            # a second sync writes no art (the names are content hashes), which is what spares Dropbox the rewrite
            some = sorted(carry)[::40]
            for p in some:
                os.utime(www / p, (1e9, 1e9))
            r = copy_web(www=www)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('(0 copied, %d already there, 0 removed)' % n, r.stdout)
            for p in some:
                self.assertEqual((www / p).stat().st_mtime, 1e9, p)
            # a folder from before (a full-size file, a stray, an emptied kind), a short file and a file of the right name
            # and size but the wrong bytes (the review: the first cut kept that one for good) are brought to the list
            first, second = sorted(carry)[:2]
            (www / first).write_bytes(b'cut short')
            wrong = bytes(b ^ 0xff for b in (ROOT / second).read_bytes())
            (www / second).write_bytes(wrong)
            self.assertEqual((www / second).stat().st_size, (ROOT / second).stat().st_size)
            shutil.copyfile(ROOT / left[0], www / left[0])
            (www / 'art' / 'gone').mkdir()
            (www / 'art' / 'gone' / 'old.0123456789.webp').write_bytes(b'x')
            (www / 'art' / '.DS_Store').write_bytes(b'x')
            r = copy_web(www=www)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('(2 copied, %d already there, 3 removed)' % (n - 2), r.stdout)
            self.assertEqual(held(www), carry)
            self.assertFalse((www / 'art' / 'gone').exists())
            for p in carry:
                self.assertTrue(filecmp.cmp(ROOT / p, www / p, shallow=False), p)

    def page(self, d, body, files):
        src = Path(d) / 'src'
        (src / 'art' / 'k').mkdir(parents=True, exist_ok=True)
        (src / 'society-hill-towers.html').write_text('<script>const X = ' + body + ';</script>')
        for f in files:
            (src / f).write_bytes(b'picture ' + f.encode())
        return src

    def test_a_missing_file_is_refused_before_anything_is_written(self):
        body = '{"img": "art/k/a.0123456789.webp", "imgHalf": "art/k/a-half.1123456789.webp", "mask": "art/k/b.2123456789.png"}'
        with tempfile.TemporaryDirectory() as d:
            src, www = self.page(d, body, ['art/k/a.0123456789.webp', 'art/k/a-half.1123456789.webp']), Path(d) / 'www'
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 1)
            self.assertIn('FATAL (copy-web): 1 art file(s) the page names are missing or empty', r.stderr)
            self.assertIn('art/k/b.2123456789.png', r.stderr)
            self.assertFalse(www.exists(), 'nothing is written on a refusal')
            # an empty file is no picture either
            (src / 'art/k/b.2123456789.png').write_bytes(b'')
            self.assertEqual(copy_web(src, www).returncode, 1)
            # a full-size file the app would leave out is still the page's: a page older than its art is refused whole
            (src / 'art/k/b.2123456789.png').write_bytes(b'mask')
            (src / 'art/k/a.0123456789.webp').unlink()
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 1)
            self.assertIn('art/k/a.0123456789.webp', r.stderr)
            self.assertFalse(www.exists())

    def test_the_half_is_carried_and_the_rest_of_a_record(self):
        body = '{"img": "art/k/a.0123456789.webp", "imgHalf": "art/k/a-half.1123456789.webp", "mask": "art/k/a-mask.2123456789.png", "list": ["art/k/c.3123456789.webp"]}'
        files = ['art/k/a.0123456789.webp', 'art/k/a-half.1123456789.webp', 'art/k/a-mask.2123456789.png', 'art/k/c.3123456789.webp']
        with tempfile.TemporaryDirectory() as d:
            src, www = self.page(d, body, files), Path(d) / 'www'
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn('copy-web', r.stderr)
            self.assertEqual(held(www), set(files) - {'art/k/a.0123456789.webp'})
            self.assertIn('left out: 1 full-size files with a half copy', r.stdout)
            # the Finder's dotfiles in the source are not art: ignored, and not carried
            (src / 'art/.DS_Store').write_bytes(b'x')
            (src / 'art/k/.DS_Store').write_bytes(b'x')
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn('copy-web', r.stderr)
            self.assertEqual(held(www), set(files) - {'art/k/a.0123456789.webp'})

    def test_art_the_page_does_not_name_stops_the_sync(self):
        # The page and its folder agree exactly or nothing ships (the review of Round 225: this was a note and exit 0, and
        # testflight.sh run alone runs no tests). Art newer than the page is one reading; the other is a name the scan
        # cannot see, and then the app would be short of a file its page asks for
        body = '{"img": "art/k/a.0123456789.webp", "imgHalf": "art/k/a-half.1123456789.webp"}'
        files = ['art/k/a.0123456789.webp', 'art/k/a-half.1123456789.webp']
        with tempfile.TemporaryDirectory() as d:
            src, www = self.page(d, body, files), Path(d) / 'www'
            (src / 'art/k/new.4123456789.webp').write_bytes(b'newer than the page')
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 1)
            self.assertIn('FATAL (copy-web): 1 file(s) under art/ are not named by this page, first art/k/new.4123456789.webp', r.stderr)
            self.assertFalse(www.exists(), 'nothing is written on a refusal')
            (src / 'art/k/new.4123456789.webp').unlink()
            self.assertEqual(copy_web(src, www).returncode, 0)
            before = {f: (www / f).read_bytes() for f in held(www)}
            # a page that asks for three files and writes two of the names where the scan does not look: one in single
            # quotes, one inside an escaped JSON.parse string (a plausible load-time change). The reviewer's case, which
            # left the app's folder holding 1 of the 3 with exit 0
            body = ('{"img": "art/k/a.0123456789.webp", "imgHalf": "art/k/a-half.1123456789.webp", "mask": \'art/k/b.2123456789.png\', '
                    '"more": JSON.parse("{\\"img\\": \\"art/k/c.3123456789.webp\\"}")}')
            src = self.page(d, body, files + ['art/k/b.2123456789.png', 'art/k/c.3123456789.webp'])
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 1)
            self.assertIn('FATAL (copy-web): 2 file(s) under art/ are not named by this page, first art/k/b.2123456789.png', r.stderr)
            self.assertIn('artNamed in art-touch.mjs cannot see how', r.stderr)
            self.assertEqual({f: (www / f).read_bytes() for f in held(www)}, before, 'the folder from the last good sync stands')

    def test_a_www_that_reaches_the_source_is_refused(self):
        # The sync REMOVES what the list does not hold. The review ran it with SHT_APP_WWW set to the source folder, and
        # with www/art a link to the source's art: both exited 0 having deleted the source's own full-size file (and the
        # first wrote an index.html into the source, which in 3d-model is the committed Pages redirect)
        body = '{"img": "art/k/a.0123456789.webp", "imgHalf": "art/k/a-half.1123456789.webp", "mask": "art/k/b.2123456789.png"}'
        files = ['art/k/a.0123456789.webp', 'art/k/a-half.1123456789.webp', 'art/k/b.2123456789.png']
        snap = lambda root: {str(f.relative_to(root)): f.read_bytes() for f in sorted(root.rglob('*')) if f.is_file()}

        def refused(src, www, was):
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn('FATAL (copy-web): the app folder ', r.stderr)
            self.assertIn('is, or reaches into, the source folder ', r.stderr)
            self.assertEqual(snap(src), was, 'the source is as it was')

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            src = self.page(d, body, files)
            was = snap(src)
            self.assertEqual(set(was), set(files) | {'society-hill-towers.html'})
            refused(src, src, was)                               # www IS the source
            self.assertFalse((src / 'index.html').exists())
            (d / 'link').symlink_to(src, target_is_directory=True)
            refused(src, d / 'link', was)                        # www is a link to it
            if (d / 'SRC').exists():                             # and, where the disk folds case (a Mac's does), by another spelling
                refused(src, d / 'SRC', was)
            www = d / 'www'
            www.mkdir()
            (www / 'art').symlink_to(src / 'art', target_is_directory=True)
            refused(src, www, was)                               # www/art is a link to the source's art
            self.assertFalse((www / 'index.html').exists())
            (www / 'art').unlink()
            (www / 'art').symlink_to(src / 'art' / 'k', target_is_directory=True)
            refused(src, www, was)                               # or to a folder inside it
            (www / 'art').unlink()
            refused(src, src / 'art', was)                       # www is the source's art folder
            # the other way round: a source that lies inside the app's art folder would be swept away by the removal
            inner = www / 'art' / 'inner'
            shutil.copytree(src, inner)
            was_inner = snap(inner)
            refused(inner, www, was_inner)
            shutil.rmtree(www / 'art')
            # and a www beside the source, or inside it but clear of its art, is an ordinary sync
            self.assertEqual(copy_web(src, www).returncode, 0)
            self.assertEqual(held(www), set(files) - {'art/k/a.0123456789.webp'})
            r = copy_web(src, src / 'www')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(held(src / 'www'), set(files) - {'art/k/a.0123456789.webp'})
            self.assertEqual({k: v for k, v in snap(src).items() if not k.startswith('www/')}, was)

    def test_a_page_that_cannot_be_trusted_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            www = Path(d) / 'www'
            src = self.page(d, '{"img": "none"}', [])
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 1)
            self.assertIn('the page names no art at all', r.stderr)
            src = self.page(d, '{"img": "art/../../outside.0123456789.webp"}', [])
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 1)
            self.assertIn('not plain paths under art/', r.stderr)
            (src / 'society-hill-towers.html').unlink()
            r = copy_web(src, www)
            self.assertEqual(r.returncode, 1)
            self.assertIn('no built page', r.stderr)
            self.assertFalse(www.exists())

    def test_the_script_is_wired(self):
        c = (SCRIPTS / 'copy-web.mjs').read_text()
        self.assertIn("import { artNamed, artTouch } from './art-touch.mjs';", c)
        self.assertIn('const { carry, leave } = artTouch(named);', c)
        self.assertNotIn('cpSync', c, 'the whole folder is never copied again')
        # every check comes before the first write: the www that reaches the source, the missing file, the unnamed art
        body = c[c.index('const here = '):]
        first_write = min(body.index(w) for w in ('mkdirSync(', 'writeFileSync(', 'copyFileSync(', 'rmSync(', 'rmdirSync('))
        self.assertEqual(body.index('mkdirSync(www, { recursive: true });\nwriteFileSync(out, page);\n'), first_write)
        for check in ("fatal('the app folder '", 'if (missing.length) fatal(', 'if (unnamed.length) fatal(', "if (!named.length) fatal(", 'if (odd.length) fatal('):
            self.assertEqual(body.count(check), 1, check)
            self.assertLess(body.index(check), first_write, check)
        self.assertNotIn("console.error('note", c, 'art the page does not name is a refusal, not a note')
        # the page is read once and those bytes are what the app gets (a build.py finishing mid-sync cannot split them)
        self.assertEqual(c.count('readFileSync(src'), 1)
        self.assertIn('try { page = readFileSync(src); }', c)
        self.assertIn("const named = artNamed(page.toString('utf8'));", c)
        self.assertNotIn('copyFileSync(src', c)
        # a file already in the app is kept only with its source's bytes
        self.assertIn('if (st && st.isFile() && st.size === size.get(p) && readFileSync(to).equals(readFileSync(join(from, p)))) continue;', c)
        t = (SCRIPTS / 'art-touch.mjs').read_text()
        self.assertIn('export const KEEP_FULL = new Set([]);', t)
        pk = json.loads((SCRIPTS.parent / 'package.json').read_text())
        self.assertEqual(pk['scripts']['sync'], 'node scripts/copy-web.mjs && npx cap sync')
        for text in (c, t):
            for ch in ('—', '–', '·'):
                self.assertNotIn(ch, text)


if __name__ == '__main__':
    unittest.main()
