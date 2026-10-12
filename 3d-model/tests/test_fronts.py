"""The house fronts (Round 175's prototype on three blocks; Round 181 citywide, Mike: "much of the app is still showing the
old style where buildings have no doors and all look alike").

fronts.json (bake_fronts.py) holds per set an atlas, a mask atlas in the same layout and the cells; the page notes every
house its property record gives a set, finds its street wall near the eye and dresses it. The window finder is checked on
the stand-in fronts, whose windows are known; the page's wiring by its source; the set choice and the street side run
under node from the page's own functions."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FrontsData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'fronts.json').read_text())

    def test_sets(self):
        d = self.d
        self.assertFalse(d['placeholder'], 'stand-in fronts never ship')
        self.assertEqual(set(d['sets']), {'federal', 'southrow', 'shop', 'victorian', 'porch', 'airlite', 'newbuild', 'stonetwin', 'siding'})
        self.assertNotIn('runs', d)   # the page finds every house's street wall itself since Round 181
        for name, s in d['sets'].items():
            self.assertTrue(s['img'].startswith('data:image/webp;base64,'), name)
            self.assertTrue(s['mask'].startswith('data:image/png;base64,'), name)
            self.assertEqual(s['cell'], [512, 1024])
            self.assertGreaterEqual(len(s['cells']), 8)
            self.assertLessEqual(len(s['cells']), s['cols'] * s['rows'])
            self.assertTrue(4 <= s['w'] <= 8, (name, s['w']))
            for c in s['cells']:
                self.assertRegex(c['cornice'], r'^#[0-9a-f]{6}$')
                self.assertGreater(c['wins'], 0, (name, c['id']))


class TowerTiles(unittest.TestCase):
    def test_tiles(self):
        d = json.loads((ROOT / 'fronts.json').read_text())
        self.assertEqual(set(d['tiles']), {'glass', 'glassdark', 'precast', 'deco', 'brick', 'resi', 'silver', 'blackgrid', 'officebrick', 'glassresi'})
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
        self.assertIn('function frontAwning(A, wx0, wz0, ux, uz, nx, nz, s0, s1, yA, D, drop, V, scallop)', s)
        self.assertIn('if (kinds && cm.gf && !porch && hash01(seed * 5.3 + j * 1.7) < (S.awn || 0))', s)
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

    def test_every_tier_notes_its_houses(self):
        s = self.s
        self.assertIn("frontNote(b.poly, ty || 0, (ty || 0) + wallTop, i, b.fa, tCode, area, true, style);", s)
        self.assertIn("frontNote(poly, base, rplan ? base + h - rplan.rise : base + hTop, i, fa, t, Math.abs(signedArea(poly)), false, style);", s)
        self.assertIn("if (wideSeam && !isTouch && !mh) frontNote(poly, base, rplan ? base + h - rplan.rise : base + h, i + 0.37, fa, t, Math.abs(signedArea(poly)), false, style);", s)
        self.assertIn("const FRONTS_ON = typeof FRONTS_DATA !== 'undefined' && !!FRONTS_DATA && !!FRONTS_DATA.sets && !TIER2;", s)

    def test_laid_near_the_eye_after_every_street_is_indexed(self):
        s = self.s
        self.assertLess(s.index("step('Fitting out the rooftops'"), s.index("step('Fitting the house fronts'"))
        self.assertIn('    updateFronts(now);   // Round 181\n', s)
        self.assertIn("if (ign > 1.0 - smoothstep(uFrR * 0.8, uFrR, fd)) discard;", s)   # they dissolve into the facade

    def test_a_phone_takes_half_size_atlases(self):
        s = self.s
        a = s.index('  function frontSetRes(s) {')
        f = s[a:s.index('\n  }\n', a)]
        self.assertIn('if (isTouch) { const cv = document.createElement(\'canvas\'); cv.width = im.width >> 1; cv.height = im.height >> 1;', f)

    def test_only_the_glass_glows(self):
        self.assertRegex(self.s, re.escape("float glass = 1.0 - smoothstep(0.05, 0.2, dot(diffuseColor.rgb"))
        self.assertIn("lampLightPatch(sh, 'vWPos', 'wall');", self.s)

    def test_towers_are_clad(self):
        s = self.s
        self.assertIn("if (h >= 35 && t !== 8 && t !== 9) towerSkinNote(poly, mh > 0 ? base + mh : base, base + hTop, style, spec, i, c, mh > 0, t);", s)
        self.assertIn("if (wideSeam && !mh && h >= 35 && t !== 8 && t !== 9) towerSkinNote(", s)
        self.assertIn("if (!TSKIN_ON || y1 - y0 < 30 || (style >= 24 && style <= 29)) return;", s)   # the researched curtain walls keep theirs
        self.assertLess(s.index("step('Fitting the house fronts'"), s.index("step('Cladding the towers'"))   # after the far ring
        self.assertIn('float sw = 3.0 + floor(fh * 4.0)', s)   # windows light by suites, not by bays

    def test_build_inlines_it(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("FRONTS_DATA", text_of("fronts.json", "null"))', b)


def fn(src, name):
    a = src.index('  function ' + name + '(')
    return src[a:src.index('\n  }\n', a) + 4]


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class SetsAndSides(unittest.TestCase):
    def run_js(self, body):
        s = (ROOT / 'app.js').read_text()
        js = ("const FR_SETS = ['federal', 'southrow', 'shop', 'victorian', 'porch', 'airlite', 'newbuild', 'stonetwin', 'siding'];\n"
              "const FR_SET_IX = (name) => FR_SETS.indexOf(name), FR_STRIDE = 10;\n" + fn(s, 'frontSetOf') + fn(s, 'frontSide') + body)
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_record_picks_the_set(self):
        o = self.run_js(r'''
const n = (i) => i < 0 ? null : FR_SETS[i];
console.log(JSON.stringify({
  core: n(frontSetOf([0, 0, 1, 3], 1, 11, 90, true, 0)), shop: n(frontSetOf([3, 0, 3, 3], 3, 10, 120, false, 5)),
  frame: n(frontSetOf([0, 1, 3, 2], 1, 8, 80, false, 11)), stone: n(frontSetOf([0, 2, 3, 2], 1, 9, 140, false, 0)),
  newer: n(frontSetOf([0, 0, 7, 3], 1, 10, 90, false, 13)), postwar: n(frontSetOf([0, 0, 4, 2], 1, 7, 85, false, 8)),
  porch: n(frontSetOf([0, 0, 3, 2], 1, 8, 160, false, 10)), tall: n(frontSetOf([0, 0, 3, 3], 1, 11, 90, false, 9)),
  low: n(frontSetOf([0, 0, 3, 2], 1, 7.5, 70, false, 9)), tower: n(frontSetOf([0, 0, 6, 20], 2, 60, 900, false, 18)),
  factory: n(frontSetOf([5, 0, 2, 3], 4, 12, 600, false, 12)), flats: n(frontSetOf([0, 0, 3, 4], 2, 14, 600, false, 18)),
}));
''')
        self.assertEqual(o, {'core': 'federal', 'shop': 'shop', 'frame': 'siding', 'stone': 'stonetwin', 'newer': 'newbuild',
                             'postwar': 'airlite', 'porch': 'porch', 'tall': 'victorian', 'low': 'southrow', 'tower': None,
                             'factory': None, 'flats': None})

    def test_the_street_side(self):
        # a rowhouse 5 m wide and 14 m deep, its long axis along z, a street along x 9 m north of its front wall and
        # another along z 7 m east of its side wall: the front faces the north street, though the side street is nearer
        o = self.run_js(r'''
const FRONTS = { buf: new Float32Array([0, 0, 0, 1, 7, 2.5, 0, 9, 0.5, 1]) };   // cx, cz, u (0, 1): the box's +u side faces south
let roads = [];
function septaSnapRoad(x, z, maxD) {
  let best = null, bd = maxD;
  for (const [ax, az, bx, bz] of roads) { const dx = bx - ax, dz = bz - az, L2 = dx * dx + dz * dz; let t = ((x - ax) * dx + (z - az) * dz) / L2; t = Math.max(0, Math.min(1, t));
    const px = ax + dx * t, pz = az + dz * t, d = Math.hypot(px - x, pz - z); if (d < bd) { bd = d; const L = Math.sqrt(L2); best = [px, pz, dx / L, dz / L]; } }
  return best;
}
roads = [[-60, -16, 60, -16], [9.5, -60, 9.5, 60]];
const a = frontSide(0);
roads = [[-60, -16, 60, -16]];
const b = frontSide(0);
roads = [];
const c = frontSide(0);
console.log(JSON.stringify([a, b, c]));
''')
        self.assertEqual(o, [1, 1, -1])   # 1: the -u side (north); -1 with no street at all


if __name__ == '__main__':
    unittest.main()
