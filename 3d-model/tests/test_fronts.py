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
        self.assertEqual(set(d['sets']), {'federal', 'southrow'})
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

    def test_build_inlines_it(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("FRONTS_DATA", text_of("fronts.json", "null"))', b)


if __name__ == '__main__':
    unittest.main()
