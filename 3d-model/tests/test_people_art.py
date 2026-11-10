"""Round 227 (Mike: "people on the sidewalks, walking"): the first figure art, three test pedestrians as card sprites.

fetch_people_art.py makes one character sheet a figure (six pictures of one person: front, back and side, each at the
contact and the passing moment of a step) and bake_people_art.py packs every figure into one atlas with a phone's half
and a computer's sharp copy. The walkers' drawing reads the manifest under ?people=1 (tests/test_people_draw.py); these checks hold the shape it
is told it will find:

- people_art.json's shape, key for key, and one figure a record of the fetch's FIGURES, in its order;
- every cell an inner rect of 128 by 256 inside the atlas with its 8 px gutter, no two cells' gutters overlapping, every
  edge on the 16 px grid (so the half and the mips stay on whole pixels);
- the three files present, named by their content's hash, the half exactly half and the sharp exactly twice the full;
- in each of the three pictures: nothing in the gutters, the figure's feet on its rect's bottom edge, its vertical axis
  on the rect's centre line, the two frames of a view at one height, and the colour just beyond the edge the figure's
  own (the page premultiplies and mips it, handoff's gotcha 16);
- build.py inlines the manifest as PEOPLE_ART and guards its files with the rest of the art;
- the app carries the half and neither the full nor the sharp picture: a phone can never ask for the sharp one."""
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
COPIES = (('img', 1.0), ('imgHalf', 0.5), ('imgSharp', 2.0))


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
        self.assertEqual(set(m), {'v', 'frames', 'views', 'atlas', 'figures'})
        self.assertEqual((m['v'], m['frames'], m['views']), (1, 2, ['front', 'back', 'side']))
        self.assertEqual(set(m['atlas']), {'img', 'imgHalf', 'imgSharp', 'w', 'h'})
        self.assertGreaterEqual(len(m['figures']), 3)
        for f in m['figures']:
            self.assertEqual(set(f), {'id', 'tall', 'season', 'cells'}, f.get('id'))
            self.assertRegex(f['id'], r'^p\d\d$')
            self.assertIn(f['season'], ('cold', 'warm'))
            self.assertEqual(len(f['cells']), len(m['views']))
            for view in f['cells']:
                self.assertEqual(len(view), m['frames'])
                for rect in view:
                    self.assertEqual(len(rect), 4)
                    self.assertTrue(all(isinstance(v, int) for v in rect), rect)

    def test_the_figures_are_the_fetchs(self):
        figs = fetch_people_art.FIGURES
        self.assertEqual([f['id'] for f in self.m['figures']], [f[0] for f in figs])
        self.assertEqual(len({f[0] for f in figs}), len(figs))
        for f, (fid, who, tall, season) in zip(self.m['figures'], figs):
            self.assertEqual(f['season'], season)
            # the cell stands the person's height over the share of it the figure fills: a stride is wider than half a height
            self.assertGreaterEqual(f['tall'], tall)
            self.assertLess(f['tall'], tall / 0.75, fid)
            self.assertTrue(1.45 <= tall <= 2.0, fid)
        # the sheet's order is the manifest's: view by view, the contact frame then the passing
        self.assertEqual(fetch_people_art.POSES, [(v, f) for v in self.m['views'] for f in range(self.m['frames'])])

    def test_every_rect_sits_inside_the_atlas_with_its_gutter(self):
        W, H = self.m['atlas']['w'], self.m['atlas']['h']
        self.assertEqual((W % 16, H % 16), (0, 0))
        rects = [r for f in self.m['figures'] for view in f['cells'] for r in view]
        self.assertEqual(len(rects), 6 * len(self.m['figures']))
        for x, y, w, h in rects:
            self.assertEqual((w, h), (CELL_W, CELL_H))
            self.assertGreaterEqual(min(x, y), GUTTER)
            self.assertLessEqual(x + w + GUTTER, W)
            self.assertLessEqual(y + h + GUTTER, H)
            # the padded cell is on the 16 px grid, so the half's cells and four levels of mips fall on whole pixels
            self.assertEqual(((x - GUTTER) % 16, (y - GUTTER) % 16), (0, 0))
        pad = [(x - GUTTER, y - GUTTER, x + w + GUTTER, y + h + GUTTER) for x, y, w, h in rects]
        for i, a in enumerate(pad):
            for b in pad[i + 1:]:
                self.assertTrue(a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], 'two cells share a gutter: %s %s' % (a, b))

    def test_the_files_are_there_under_their_hashes_at_their_sizes(self):
        at = self.m['atlas']
        for key, s in COPIES:
            p = at[key]
            name = {'img': 'people', 'imgHalf': 'people-half', 'imgSharp': 'people-sharp'}[key]
            m = re.fullmatch(r'art/people/%s\.([0-9a-f]{10})\.webp' % name, p)
            self.assertTrue(m, p)
            self.assertEqual(hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:10], m.group(1), p)
            self.assertEqual(webp_size(ROOT / p), (int(at['w'] * s), int(at['h'] * s)), key)
        self.assertEqual(at['w'] % 2 + at['h'] % 2, 0, 'the half is exactly half')
        self.assertEqual({f.name for f in (ROOT / 'art' / 'people').iterdir()}, {Path(at[k]).name for k, _ in COPIES})


class Pictures(unittest.TestCase):
    """The three pictures, read as they ship."""
    @classmethod
    def setUpClass(cls):
        from PIL import Image
        cls.m = json.loads(MAN.read_text())
        cls.im = {k: Image.open(ROOT / cls.m['atlas'][k]).convert('RGBA') for k, _ in COPIES}
        for im in cls.im.values():
            im.load()

    def cells(self, s):
        for f in self.m['figures']:
            for v, view in enumerate(f['cells']):
                for fr, (x, y, w, h) in enumerate(view):
                    yield f['id'], v, fr, (int(x * s), int(y * s), int((x + w) * s), int((y + h) * s))

    def test_nothing_lies_in_the_gutters(self):
        from PIL import Image
        for key, s in COPIES:
            a = self.im[key].getchannel('A')
            for _, _, _, box in self.cells(s):
                a.paste(0, box)
            self.assertIsNone(a.getbbox(), key + ': alpha outside the cells')

    def test_feet_on_the_bottom_edge_and_the_axis_on_the_centre_line(self):
        from PIL import Image
        for key, s in COPIES:
            tall = {}
            for fid, v, fr, box in self.cells(s):
                a = self.im[key].crop(box).getchannel('A')
                w, h = a.size
                solid = a.point(lambda t: 255 if t > 127 else 0).getbbox()
                self.assertIsNotNone(solid, (key, fid, v, fr))
                self.assertGreaterEqual(solid[3], h - 1, '%s %s view %d frame %d: the feet are off the bottom edge' % (key, fid, v, fr))
                if key == 'imgSharp':   # drawn with a pixel to spare each side: a stride that touched its rect's edge was cut by it
                    self.assertGreater(solid[0], 0, 'the figure touches its rect\'s left edge')
                    self.assertLess(solid[2], w, 'the figure touches its rect\'s right edge')
                self.assertGreater(solid[3] - solid[1], 0.75 * h, 'the figure fills too little of its cell')
                col = list(a.resize((w, 1), Image.BOX).getdata())
                axis = sum((i + 0.5) * c for i, c in enumerate(col)) / sum(col)
                self.assertLess(abs(axis - w / 2), 0.02 * w + 0.5, '%s %s view %d frame %d: the axis is %.1f px off the centre line' % (key, fid, v, fr, axis - w / 2))
                tall[(fid, v, fr)] = solid[3] - solid[1]
            for (fid, v, fr), t in tall.items():   # one scale a figure: the six poses within 4% and a pixel of one another
                top = max(u for (g, _, _), u in tall.items() if g == fid)
                self.assertGreaterEqual(t, 0.96 * top - 1, (key, fid, v, fr))

    def test_the_colour_beyond_the_edge_is_the_figures_own(self):
        # the page uploads the picture premultiplied and mips it, and a lossy WebP smears chroma across an edge: the clear
        # pixels round a figure must hold its colour, never black or white (handoff's gotcha 16; the tree cards' path)
        from PIL import ImageChops, ImageFilter, ImageStat
        for key, _ in COPIES:
            im = self.im[key]
            a = im.getchannel('A')
            solid = a.point(lambda t: 255 if t > 200 else 0)
            clear = a.point(lambda t: 255 if t == 0 else 0)
            ring = ImageChops.multiply(clear, a.point(lambda t: 255 if t > 0 else 0).filter(ImageFilter.MaxFilter(5)))   # clear, within 2 px of the figure
            rim = ImageChops.multiply(solid, clear.filter(ImageFilter.MaxFilter(9)))                                     # solid, within 4 px of the clear
            self.assertGreater(ImageStat.Stat(ring).sum[0], 255 * 500, key)
            lum = im.convert('L')
            out, inn = ImageStat.Stat(lum, ring).mean[0], ImageStat.Stat(lum, rim).mean[0]
            self.assertLess(abs(out - inn), 14, '%s: the clear pixels round the figures average %.0f against %.0f just inside' % (key, out, inn))


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
        self.assertEqual(s.count("art_files.write("), 3)
        self.assertIn("art_files.prune('people')", s)
        self.assertIn('exact=True', s)   # the colour under the clear pixels is kept by the encoder
        self.assertNotIn('data:image/', MAN.read_text())

    def test_the_key_goes_into_the_header_and_nowhere_else(self):
        s = (ROOT / 'fetch_people_art.py').read_text()
        self.assertIn("os.environ.get('OPENAI_API_KEY')", s)
        self.assertIn("os.path.expanduser('~/.config/philly3d/openai.env')", s)
        uses = ("def make(key, fid, prompt, force):", "'Authorization': 'Bearer ' + key", "key = api_key()", "make(key, j[0], j[1], a.force)")
        for line in s[s.index('def api_key'):].split('\n'):
            if re.search(r'\bkey\b', line):
                self.assertTrue(any(u in line for u in uses), 'a new use of the key: ' + line.strip())
                self.assertNotRegex(line, r'print\(|json\.dump\(|\.write\(|open\(')

    @unittest.skipUnless(NODE, 'node is not installed')
    def test_the_app_carries_the_half_and_never_the_sharp(self):
        at = json.loads(MAN.read_text())['atlas']
        js = ("import('" + (ROOT.parent / 'app' / 'scripts' / 'art-touch.mjs').as_uri() + "').then((M) => { const n = JSON.parse(process.argv[1]); "
              "console.log(JSON.stringify({ now: M.artTouch(n), kept: M.artTouch(n, new Set(['people'])) })); })")
        named = sorted([at['img'], at['imgHalf'], at['imgSharp'], 'art/fronts/row-a.0123456789.webp', 'art/glass/rooms.0123456789.webp'])
        r = subprocess.run([NODE, '-e', js, json.dumps(named)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        others = ['art/fronts/row-a.0123456789.webp', 'art/glass/rooms.0123456789.webp']
        self.assertEqual(sorted(got['now']['carry']), sorted(others + [at['imgHalf']]))
        self.assertEqual(sorted(got['now']['leave']), sorted([at['img'], at['imgSharp']]))
        # a kind that keeps its full-size files (KEEP_FULL) brings back the full picture and never the sharp one
        self.assertEqual(sorted(got['kept']['carry']), sorted(others + [at['img'], at['imgHalf']]))
        self.assertEqual(got['kept']['leave'], [at['imgSharp']])

if __name__ == '__main__':
    unittest.main()
