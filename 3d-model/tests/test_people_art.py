"""Round 227 (Mike: "people on the sidewalks, walking"), Round 242 (Mike: "make it smoother still and have many more
different looking people. They should also be dressed specific to the season"): the figure art.

fetch_people_art.py makes three strips a figure (eight pictures of one person, the eight moments of one step, seen from
the side, from the front and from behind; the front and the back edits of the side) and bake_people_art.py packs each
WARDROBE's figures (cold, cool, warm) into one atlas with a phone's half beside it. The walkers' drawing reads the
manifest under ?people=1 (tests/test_people_draw.py); these checks hold the shape it is told it will find:

- people_art.json's shape, key for key, and one figure a record of the fetch's FIGURES, wardrobe by wardrobe in its order;
- every figure mirror-safe (nothing carried on one side: the page mirrors the second step), ten or more a wardrobe;
- every cell an inner rect of 128 by 256 inside its atlas with its 8 px gutter, no two cells' gutters overlapping, every
  edge on the 16 px grid (so the half and the mips stay on whole pixels);
- the two files a wardrobe present, named by their content's hash, the half exactly half the full;
- in each picture: nothing in the gutters, the figure's feet on its rect's bottom edge, its body (head and trunk) on the
  rect's centre line, a view's eight pictures at one scale, and the colour just beyond the edge the figure's own (the
  page premultiplies and mips it, handoff's gotcha 16);
- build.py inlines the manifest as PEOPLE_ART and guards its files with the rest of the art;
- the app carries the halves and never the full pictures."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import fetch_people_art  # noqa: E402  (standard library only: its FIGURES and POSES are the bake's config)

MAN = ROOT / 'people_art.json'
PAGE = ROOT / 'society-hill-towers.html'
NODE = shutil.which('node')
CELL_W, CELL_H, GUTTER = 128, 256, 8
COPIES = (('img', 1.0), ('imgHalf', 0.5))
WARDS = ('cold', 'cool', 'warm')


def webp_size(path):
    """A WebP's canvas size from its header (an extended file, VP8X, which every picture with alpha is)."""
    b = path.read_bytes()[:30]
    assert b[:4] == b'RIFF' and b[8:16] == b'WEBPVP8X', path
    w = struct.unpack('<I', b[24:27] + b'\0')[0] + 1
    h = struct.unpack('<I', b[27:30] + b'\0')[0] + 1
    return w, h


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(MAN.read_text())

    def test_the_shape(self):
        m = self.m
        self.assertEqual(set(m), {'v', 'frames', 'views', 'temps', 'wardrobes'})
        self.assertEqual((m['v'], m['frames'], m['views'], m['temps']), (2, 8, ['front', 'back', 'side'], [50, 70]))
        self.assertEqual(tuple(m['wardrobes']), WARDS)
        for ward, w in m['wardrobes'].items():
            self.assertEqual(set(w), {'atlas', 'figures'})
            self.assertEqual(set(w['atlas']), {'img', 'imgHalf', 'w', 'h'})
            self.assertGreaterEqual(len(w['figures']), 10, ward)
            for f in w['figures']:
                self.assertEqual(set(f), {'id', 'tall', 'cells'}, f.get('id'))
                self.assertRegex(f['id'], r'^[cmw]\d\d$')
                self.assertEqual(f['id'][0], ward[0] if ward != 'cool' else 'm')
                self.assertEqual(len(f['cells']), len(m['views']))
                for view in f['cells']:
                    self.assertEqual(len(view), m['frames'])
                    for rect in view:
                        self.assertEqual(len(rect), 4)
                        self.assertTrue(all(isinstance(v, int) for v in rect), rect)

    def test_the_figures_are_the_fetchs(self):
        F = fetch_people_art
        figs = F.FIGURES
        self.assertEqual(len({f[0] for f in figs}), len(figs))
        for ward in WARDS:
            got = self.m['wardrobes'][ward]['figures']
            mine = [f for f in figs if f[3] == ward]
            self.assertEqual([f['id'] for f in got], [f[0] for f in mine])
            for f, (fid, who, tall, _, carry) in zip(got, mine):
                # the cell stands the person's height over the share of it the figure fills: a stride is wider than half a
                # height, and a backpack in profile wider again (w02 fills 0.746)
                self.assertGreaterEqual(f['tall'], tall)
                self.assertLess(f['tall'], tall / 0.72, fid)
                self.assertTrue(1.45 <= tall <= 2.0, fid)
                # mirror-safe: hands empty or a backpack on both shoulders, and nothing in the words that hangs on one side
                self.assertIn(carry, F.CARRY, fid)
                self.assertNotRegex(who, r'\b(tote|shoulder bag|crossbody|handbag|purse|umbrella|cup|phone)\b', fid)
        self.assertEqual(set(F.WARDROBES), set(WARDS))
        self.assertEqual((F.VIEWS, F.FRAMES), (['side', 'front', 'back'], self.m['frames']))

    def test_every_rect_sits_inside_the_atlas_with_its_gutter(self):
        for ward, w in self.m['wardrobes'].items():
            W, H = w['atlas']['w'], w['atlas']['h']
            self.assertEqual((W % 16, H % 16), (0, 0))
            self.assertLessEqual(max(W, H), 4096, ward)   # the full picture fits every WebGL 2 device's texture size
            rects = [r for f in w['figures'] for view in f['cells'] for r in view]
            self.assertEqual(len(rects), 3 * self.m['frames'] * len(w['figures']))
            for x, y, cw, ch in rects:
                self.assertEqual((cw, ch), (CELL_W, CELL_H))
                self.assertGreaterEqual(min(x, y), GUTTER)
                self.assertLessEqual(x + cw + GUTTER, W)
                self.assertLessEqual(y + ch + GUTTER, H)
                # the padded cell is on the 16 px grid, so the half's cells and four levels of mips fall on whole pixels
                self.assertEqual(((x - GUTTER) % 16, (y - GUTTER) % 16), (0, 0))
            pad = sorted((x - GUTTER, y - GUTTER, x + cw + GUTTER, y + ch + GUTTER) for x, y, cw, ch in rects)
            for i, a in enumerate(pad):
                for b in pad[i + 1:]:
                    self.assertTrue(a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], 'two cells share a gutter: %s %s' % (a, b))

    def test_the_files_are_there_under_their_hashes_at_their_sizes(self):
        names = set()
        for ward, w in self.m['wardrobes'].items():
            at = w['atlas']
            for key, s in COPIES:
                p = at[key]
                name = 'people-' + ward + ('-half' if key == 'imgHalf' else '')
                m = re.fullmatch(r'art/people/%s\.([0-9a-f]{10})\.webp' % name, p)
                self.assertTrue(m, p)
                self.assertEqual(hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:10], m.group(1), p)
                self.assertEqual(webp_size(ROOT / p), (int(at['w'] * s), int(at['h'] * s)), key)
                names.add(Path(p).name)
            self.assertEqual(at['w'] % 2 + at['h'] % 2, 0, 'the half is exactly half')
        self.assertEqual({f.name for f in (ROOT / 'art' / 'people').iterdir()}, names)


class Pictures(unittest.TestCase):
    """The pictures, read as they ship."""
    @classmethod
    def setUpClass(cls):
        from PIL import Image
        cls.m = json.loads(MAN.read_text())
        cls.im = {(w, k): Image.open(ROOT / cls.m['wardrobes'][w]['atlas'][k]).convert('RGBA') for w in WARDS for k, _ in COPIES}
        for im in cls.im.values():
            im.load()

    def cells(self, ward, s):
        for f in self.m['wardrobes'][ward]['figures']:
            for v, view in enumerate(f['cells']):
                for fr, (x, y, w, h) in enumerate(view):
                    yield f['id'], v, fr, (int(x * s), int(y * s), int((x + w) * s), int((y + h) * s))

    def test_nothing_lies_in_the_gutters(self):
        for ward in WARDS:
            for key, s in COPIES:
                a = self.im[(ward, key)].getchannel('A')
                for _, _, _, box in self.cells(ward, s):
                    a.paste(0, box)
                self.assertIsNone(a.getbbox(), '%s %s: alpha outside the cells' % (ward, key))

    def test_feet_on_the_bottom_edge_and_the_body_on_the_centre_line(self):
        for ward in WARDS:
            for key, s in COPIES:
                tall = {}
                for fid, v, fr, box in self.cells(ward, s):
                    a = self.im[(ward, key)].crop(box).getchannel('A')
                    w, h = a.size
                    solid = a.point(lambda t: 255 if t > 127 else 0).getbbox()
                    self.assertIsNotNone(solid, (key, fid, v, fr))
                    self.assertGreaterEqual(solid[3], h - 1, '%s %s view %d frame %d: the feet are off the bottom edge' % (key, fid, v, fr))
                    self.assertGreater(solid[3] - solid[1], 0.7 * h, 'the figure fills too little of its cell')
                    # the body: the head and the trunk's band (the bake's BODY, 0.06 to 0.42 of the figure from its top)
                    fh = solid[3] - solid[1]
                    band = a.crop((0, solid[1] + int(0.06 * fh), w, solid[1] + int(0.42 * fh))).point(lambda t: 1 if t > 127 else 0)
                    col = [sum(band.crop((i, 0, i + 1, band.height)).getdata()) for i in range(w)]
                    axis = sum((i + 0.5) * c for i, c in enumerate(col)) / sum(col)
                    self.assertLess(abs(axis - w / 2), 0.03 * w + 1, '%s %s %s view %d frame %d: the body is %.1f px off the centre line' % (ward, key, fid, v, fr, axis - w / 2))
                    tall[(fid, v, fr)] = fh
                for (fid, v, fr), t in tall.items():   # one scale a view: its eight pictures within 8% and a pixel of its tallest
                    top = max(u for (g, vv, _), u in tall.items() if g == fid and vv == v)
                    self.assertGreaterEqual(t, 0.92 * top - 1, (ward, key, fid, v, fr))

    def test_the_colour_beyond_the_edge_is_the_figures_own(self):
        # the page uploads the picture premultiplied and mips it, and a lossy WebP smears chroma across an edge: the clear
        # pixels round a figure must hold its colour, never black or white (handoff's gotcha 16; the tree cards' path)
        from PIL import ImageChops, ImageFilter, ImageStat
        for (ward, key), im in self.im.items():
            a = im.getchannel('A')
            solid = a.point(lambda t: 255 if t > 200 else 0)
            clear = a.point(lambda t: 255 if t == 0 else 0)
            ring = ImageChops.multiply(clear, a.point(lambda t: 255 if t > 0 else 0).filter(ImageFilter.MaxFilter(5)))   # clear, within 2 px of the figure
            rim = ImageChops.multiply(solid, clear.filter(ImageFilter.MaxFilter(9)))                                     # solid, within 4 px of the clear
            self.assertGreater(ImageStat.Stat(ring).sum[0], 255 * 500, (ward, key))
            lum = im.convert('L')
            out, inn = ImageStat.Stat(lum, ring).mean[0], ImageStat.Stat(lum, rim).mean[0]
            self.assertLess(abs(out - inn), 14, '%s %s: the clear pixels round the figures average %.0f against %.0f just inside' % (ward, key, out, inn))

    def test_no_chroma_green_on_the_edge(self):
        # a strip that came back on its green screen is keyed by the bake: no green fringe survives round a figure
        for (ward, key), im in self.im.items():
            px = [p for p in im.getdata() if 40 < p[3] < 250]
            green = sum(1 for r, g, b, _ in px if g > max(r, b) + 60)
            self.assertLess(green / max(1, len(px)), 0.01, (ward, key))


class Wiring(unittest.TestCase):
    def test_build_inlines_it_and_guards_its_files(self):
        b = (ROOT / 'build.py').read_text()
        self.assertEqual(b.count('const("PEOPLE_ART", text_of("people_art.json", "null"))'), 1)
        art = b[b.index('ART_FILES = []'):b.index('const("NW_WATER"')]
        self.assertIn('"people_art.json"', art)   # by membership, never by position

    @unittest.skipUnless(PAGE.exists(), 'no built page')
    def test_the_built_page_carries_the_manifest(self):
        page = PAGE.read_text()
        self.assertEqual(page.count('const PEOPLE_ART = ' + MAN.read_text().strip() + ';\n'), 1,
                         'the page was built before people_art.json was baked: run build.py')

    def test_the_bake_writes_through_art_files_and_never_inlines(self):
        s = (ROOT / 'bake_people_art.py').read_text()
        self.assertEqual(s.count("art_files.write("), 2)
        self.assertIn("art_files.prune('people')", s)
        self.assertIn('exact=True', s)   # the colour under the clear pixels is kept by the encoder
        self.assertNotIn('data:image/', MAN.read_text())

    def test_the_key_goes_into_the_header_and_nowhere_else(self):
        s = (ROOT / 'fetch_people_art.py').read_text()
        self.assertIn("os.environ.get('OPENAI_API_KEY')", s)
        self.assertIn("os.path.expanduser('~/.config/philly3d/openai.env')", s)
        uses = ("def make(key, fid, view, prompt, force):", "'Authorization': 'Bearer ' + key", "key = api_key()", "make(key, j[0], j[1], j[2], a.force)")
        for line in s[s.index('def api_key'):].split('\n'):
            if re.search(r'\bkey\b', line):
                self.assertTrue(any(u in line for u in uses), 'a new use of the key: ' + line.strip())
                self.assertNotRegex(line, r'print\(|json\.dump\(|\.write\(|open\(')

    @unittest.skipUnless(NODE, 'node is not installed')
    def test_the_app_carries_the_halves_and_never_the_full(self):
        w = json.loads(MAN.read_text())['wardrobes']
        js = ("import('" + (ROOT.parent / 'app' / 'scripts' / 'art-touch.mjs').as_uri() + "').then((M) => { const n = JSON.parse(process.argv[1]); "
              "console.log(JSON.stringify({ now: M.artTouch(n) })); })")
        full = sorted(w[k]['atlas']['img'] for k in WARDS)
        half = sorted(w[k]['atlas']['imgHalf'] for k in WARDS)
        others = ['art/fronts/row-a.0123456789.webp', 'art/glass/rooms.0123456789.webp']
        r = subprocess.run([NODE, '-e', js, json.dumps(sorted(full + half + others))], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)['now']
        self.assertEqual(sorted(got['carry']), sorted(others + half))
        self.assertEqual(sorted(got['leave']), full)

if __name__ == '__main__':
    unittest.main()
