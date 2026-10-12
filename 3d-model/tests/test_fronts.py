"""The house fronts of the facade prototype (Oct 12, Mike: "prototype both blocks with AI-generated fronts").

fronts.json (bake_fronts.py) holds per set an atlas, a mask atlas in the same layout and the cells, and the runs; the
page dresses each house a run passes with a front. The window finder is checked on the stand-in fronts, whose windows
are known; the page's wiring by its source."""
from pathlib import Path
import json
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FrontsData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'fronts.json').read_text())

    def test_sets_and_runs(self):
        d = self.d
        self.assertFalse(d['placeholder'], 'stand-in fronts never ship')
        self.assertEqual(set(d['sets']), {'federal', 'southrow', 'shop'})
        for name, s in d['sets'].items():
            self.assertTrue(s['img'].startswith('data:image/webp;base64,'), name)
            self.assertTrue(s['mask'].startswith('data:image/png;base64,'), name)
            self.assertEqual(s['cell'], [512, 1024])
            self.assertGreaterEqual(len(s['cells']), 8)
            self.assertLessEqual(len(s['cells']), s['cols'] * s['rows'])
            for c in s['cells']:
                self.assertRegex(c['cornice'], r'^#[0-9a-f]{6}$')
                self.assertGreater(c['wins'], 0, c['id'])
        sets = {r['set'] for r in d['runs']}
        self.assertEqual(sets, set(d['sets']))
        for r in d['runs']:
            self.assertGreater(((r['b'][0] - r['a'][0]) ** 2 + (r['b'][1] - r['a'][1]) ** 2) ** 0.5, 50)


class TowerTiles(unittest.TestCase):
    def test_tiles(self):
        d = json.loads((ROOT / 'fronts.json').read_text())
        self.assertEqual(set(d['tiles']), {'glass', 'glassdark', 'precast', 'deco', 'brick', 'resi'})
        for k, t in d['tiles'].items():
            self.assertTrue(t['img'].startswith('data:image/webp;base64,'), k)
            self.assertTrue(8 <= t['w'] <= 24 and 8 <= t['h'] <= 24, (k, t['w'], t['h']))   # a few floors by a few bays
            self.assertGreaterEqual(t['nb'], 3, k)
            self.assertGreaterEqual(t['nf'], 2, k)


class Awnings(unittest.TestCase):
    def test_no_painted_awnings_in_the_prompts(self):
        import fetch_fronts as F
        self.assertIn('no awnings and no canopies', F.FRAME)
        for f in F.FRONTS:
            self.assertNotRegex(f[3], r'awning|canopy', f[1])

    def test_awnings_are_built(self):
        s = (ROOT / 'app.js').read_text()
        self.assertIn('function frontAwning(A, wx0, wz0, ux, uz, nx, nz, s0, s1, yA, D, drop, V, scallop, colA, colB, stripeK)', s)
        self.assertIn("if (kinds && cm.gf && hash01(c.seed * 5.3 + j * 1.7) < (S.awn || 0))", s)
        d = json.loads((ROOT / 'fronts.json').read_text())
        self.assertEqual(d['sets']['federal']['awn'], 0)          # Society Hill's Federal rows wear none
        self.assertGreater(d['sets']['shop']['awn'], 0)
        self.assertTrue(any(c['gf'] for c in d['sets']['shop']['cells']))


class WindowFinder(unittest.TestCase):
    def test_finds_the_stand_ins_windows(self):
        import bake_fronts as B
        for set_, floors, bays in (('federal', 3, 3), ('southrow', 2, 2)):
            for k in range(4):
                wins, door = B.find_openings(B.placeholder(set_, k))
                self.assertIsNotNone(door, (set_, k))
                # every sash but the door's bay on the ground floor; a cross muntin may split one into panes
                self.assertGreaterEqual(len(wins), floors * bays - 1, (set_, k))
                for x0, y0, x1, y1 in wins:
                    self.assertTrue(0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1)


class PageWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_both_tiers_hand_their_houses_over(self):
        s = self.s
        self.assertIn("frontNote(b.poly, ty || 0, (ty || 0) + wallTop, i, 'core');", s)
        self.assertIn("frontNote(poly, base, rplan ? base + h - rplan.rise : base + hTop, i, 'wide');", s)
        self.assertIn('const FRONTS_ON = typeof FRONTS_DATA !== \'undefined\' && !!FRONTS_DATA && !!FRONTS_DATA.runs && !TIER2;', s)

    def test_a_wide_deep_building_keeps_its_own_facade(self):
        self.assertIn('if (k >= 2 && depth > 18) return null;', self.s)

    def test_a_phone_takes_half_size_atlases(self):
        s = self.s
        self.assertIn('if (!isTouch) return new THREE.Texture(src);', s)
        self.assertIn('cv.width = src.width >> 1; cv.height = src.height >> 1;', s)
        self.assertIn('return freeTexOnUpload(new THREE.CanvasTexture(cv));', s)

    def test_only_the_glass_glows(self):
        self.assertRegex(self.s, re.escape("float glass = 1.0 - smoothstep(0.05, 0.2, dot(diffuseColor.rgb"))
        self.assertIn("lampLightPatch(sh, 'vWPos', 'wall');", self.s)

    def test_towers_are_clad(self):
        s = self.s
        self.assertIn("if (h >= 35 && t !== 8 && t !== 9) towerSkinNote(poly, mh > 0 ? base + mh : base, base + hTop, style, spec, i, c, mh > 0, t);", s)
        self.assertIn("if (!TSKIN_ON || y1 - y0 < 30 || (style >= 24 && style <= 29)) return;", s)   # the researched curtain walls keep theirs
        self.assertIn("step('Cladding the towers'", s)
        self.assertIn('float sw = 3.0 + floor(fh * 4.0)', s)   # windows light by suites, not by bays

    def test_build_inlines_it(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("FRONTS_DATA", text_of("fronts.json", "null"))', b)


if __name__ == '__main__':
    unittest.main()
