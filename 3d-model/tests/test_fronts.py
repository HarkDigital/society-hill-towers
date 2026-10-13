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
        self.assertEqual(set(d['sets']), {'federal', 'southrow', 'shop', 'victorian', 'porch', 'airlite', 'newbuild', 'stonetwin', 'siding',
                                          'univcity', 'chestnut', 'manayunk', 'loft', 'mixeduse', 'rittenhouse',   # Round 184: six more
                                          'shop1'})   # the realism pass: the one-storey shops
        self.assertLessEqual(len(d['sets']), 16)   # the set rides in a note's low four bits
        self.assertNotIn('runs', d)   # the page finds every house's street wall itself since Round 181
        for name, s in d['sets'].items():
            # Round 184: files under art/fronts/, a phone's half of each beside it
            for k, ext in (('img', 'webp'), ('imgHalf', 'webp'), ('mask', 'png'), ('maskHalf', 'png')):
                self.assertRegex(s[k], r'^art/fronts/%s(-mask)?(-half)?\.[0-9a-f]{10}\.%s$' % (name, ext))
                self.assertTrue((ROOT / s[k]).exists(), s[k])
            # the realism pass: a wide set's cells are wide, a near-square set's near square, each set within Round 184's
            # 4.7 MP (the review: 768 by 576 cells made the one-storey shops 7.1 MP)
            self.assertEqual(s['cell'], [512, 384] if s['aspect'] > 1 else [480, 600] if s['aspect'] >= 0.7 else [384, 768])
            self.assertEqual(len(s['cells']), 16, name)   # sixteen a set since Round 184
            self.assertLessEqual(len(s['cells']), s['cols'] * s['rows'])
            self.assertEqual(s['porch'], int(name in ('porch', 'univcity')), name)
            self.assertTrue(4 <= s['w'] <= 12, (name, s['w']))
            for c in s['cells']:
                self.assertRegex(c['cornice'], r'^#[0-9a-f]{6}$')
                self.assertGreater(c['wins'], 0, (name, c['id']))


class TowerTiles(unittest.TestCase):
    def test_tiles(self):
        d = json.loads((ROOT / 'fronts.json').read_text())
        self.assertEqual(set(d['tiles']), {'glass', 'glassdark', 'precast', 'deco', 'brick', 'resi', 'silver', 'blackgrid', 'officebrick', 'glassresi',
                                           'goldglass', 'greenglass', 'ribbon', 'brutalist', 'limestone', 'marble', 'terracotta', 'blueband',
                                           'unitized', 'hotel', 'granite', 'fins', 'darkbrick', 'metalpanel', 'greygrid',
                                           # Round 185: the mid-rise walls
                                           'aptbrick', 'gardenapt', 'loftbrick', 'warehouse', 'institution', 'modernapt', 'commercial',
                                           'paintedbrick', 'officemid', 'stucco'})   # 25 since Round 184, 35 since Round 185
        for k, t in d['tiles'].items():
            for f in ('img', 'imgHalf', 'mask'):
                self.assertRegex(t[f], r'^art/tiles/%s(-mask)?(-half)?\.[0-9a-f]{10}\.(webp|png)$' % k)
                self.assertTrue((ROOT / t[f]).exists(), t[f])
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
        # the realism pass (buildings 5): each hands its house's own wall colour too
        self.assertIn("frontNote(b.poly, ty || 0, (ty || 0) + wallTop, i, b.fa, tCode, area, true, style, color);", s)
        self.assertIn("frontNote(poly, base, rplan ? base + h - rplan.rise : base + hTop, i, fa, t, Math.abs(signedArea(poly)), false, style, c);", s)
        self.assertIn("if (wideSeam && !isTouch && !mh) frontNote(poly, base, rplan ? base + h - rplan.rise : base + h, i + 0.37, fa, t, Math.abs(signedArea(poly)), false, style, c);", s)
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
        # Round 184: the bake's half files (artSrc), and halved here only when a record has none
        self.assertIn('artImage(artSrc(full, half))', f)
        self.assertIn('load(S.img, S.imgHalf, map), load(S.mask, S.maskHalf, mask)', f)
        self.assertIn("if (isTouch && !half) { const cv = document.createElement('canvas'); cv.width = im.width >> 1; cv.height = im.height >> 1;", f)

    def test_only_the_glass_glows(self):
        # the realism pass (buildings 6): the whole opening the bake found glows, its bright bars dark, never the day
        # paint's dark texels (the luminance gate flipped pane by pane: white panes salted with black)
        a = self.s.index('  function frontSetRes(s) {')
        f = self.s[a:self.s.index('\n  }\n', a)]
        real = f[f.index('      if (REAL) {\n'):f.index('      } else {\n')]   # ?real=0 keeps Round 184's gate after it
        self.assertNotIn('float glass = 1.0 - smoothstep(0.05, 0.2, dot(diffuseColor.rgb', real)
        self.assertIn('float glass = 1.0 - smoothstep(0.05, 0.2, dot(diffuseColor.rgb', f)
        self.assertIn("totalEmissiveRadiance += frMask.r * (1.0 - 0.85 * frBar) * hl * uNight * lit; }", real)
        self.assertIn("vec3 lit = roomLight(vec2(0.5, vp), vec2(floor(frMask.g * 255.0 + 0.5), floor(vSeed * 997.0)), vSeed, 0.0) * (0.55 + 0.45 * st);", real)   # the facade's own rooms
        self.assertIn("frBar = smoothstep(0.05, 0.16, dot(sampledDiffuseColor.rgb - frBlur", f)   # a bar is brighter than the opening round it
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
        a = s.index('  const FR_AREAS = {')
        areas = s[a:s.index('\n  // the set a house', a)]
        js = ("const FR_SETS = ['federal', 'southrow', 'shop', 'victorian', 'porch', 'airlite', 'newbuild', 'stonetwin', 'siding',"
              " 'univcity', 'chestnut', 'manayunk', 'loft', 'mixeduse', 'rittenhouse', 'shop1'];\n"
              "const FR_SET_IX = (name) => FR_SETS.indexOf(name), FR_STRIDE = 10, REAL = true;\n" + areas + '\n' + fn(s, 'frontSetOf') + fn(s, 'frontSide') + fn(s, 'frontHonest')
              + fn(s, 'frontFitWord') + fn(s, 'frontFitOf') + fn(s, 'orientedBox') + body)
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
  // Round 184: the six more, by record and by place (Rittenhouse Square, 40th and Spruce, Germantown Avenue at Highland,
  // Manayunk's Green Lane, 3rd and Race, 13th and Walnut, and a new factory)
  rit: n(frontSetOf([0, 0, 2, 4], 1, 14, 120, false, 9, -2300, -200)), uc: n(frontSetOf([0, 0, 3, 3], 1, 11, 160, false, 10, -4900, -500)),
  ucLow: n(frontSetOf([0, 0, 3, 2], 1, 8, 160, false, 10, -4900, -500)), ch: n(frontSetOf([0, 2, 2, 3], 1, 9, 400, false, 0, -5500, -14400)),
  chBig: n(frontSetOf([0, 0, 3, 3], 1, 10, 800, false, 0, -5500, -14400)), mk: n(frontSetOf([0, 0, 3, 2], 1, 7.5, 70, false, 9, -6800, -9000)),
  loftOC: n(frontSetOf([3, 0, 2, 5], 3, 18, 900, false, 6, -100, -900)), shopOC: n(frontSetOf([3, 0, 2, 2], 3, 9, 200, false, 5, -100, -900)),
  mixCC: n(frontSetOf([3, 0, 3, 4], 3, 13, 300, false, 5, -1200, -600)), shopCC: n(frontSetOf([3, 0, 3, 2], 3, 9, 300, false, 5, -1200, -600)),
  newFactory: n(frontSetOf([5, 0, 6, 3], 4, 12, 600, false, 12)), ritLow: n(frontSetOf([0, 0, 2, 2], 1, 8, 90, false, 9, -2300, -200)),
  // the realism pass: a one-storey shop takes its own set, and a tall postwar house is no airlite
  shopLow: n(frontSetOf([3, 0, 3, 2], 3, 5.5, 120, false, 5)), postwarTall: n(frontSetOf([0, 0, 4, 2], 1, 12, 85, false, 8)),
}));
''')
        self.assertEqual(o, {'core': 'federal', 'shop': 'shop', 'frame': 'siding', 'stone': 'stonetwin', 'newer': 'newbuild',
                             'postwar': 'airlite', 'porch': 'porch', 'tall': 'victorian', 'low': 'southrow', 'tower': None,
                             'factory': 'loft', 'flats': None,
                             'rit': 'rittenhouse', 'uc': 'univcity', 'ucLow': 'porch', 'ch': 'chestnut', 'chBig': 'chestnut',
                             'mk': 'manayunk', 'loftOC': 'loft', 'shopOC': 'shop', 'mixCC': 'mixeduse', 'shopCC': 'shop',
                             'newFactory': None, 'ritLow': 'southrow', 'shopLow': 'shop1', 'postwarTall': 'victorian'})

    def test_the_street_side(self):
        # a rowhouse 5 m wide and 14 m deep, its long axis along z, a street along x 9 m north of its front wall and
        # another along z 7 m east of its side wall: the front faces the north street, though the side street is nearer
        o = self.run_js(r'''
const FRONTS = { buf: new Float32Array([0, 0, 0, 1, 7, 2.5, 0, 9, 0.5, 1 + 16 * 15]) };   // cx, cz, u (0, 1): the box's +u side faces south; every side honest (Round 187)
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

    def test_a_front_takes_only_an_honest_side(self):
        # Round 187 (Mike: fronts "obviously off kilter"): a side of the fitted box is honest only where the outline's own
        # wall runs along it. A rectangle: all four; a trapezoid whose street wall leans 10 degrees: not that side; a house
        # with a 1.2 m recess across most of its front: not that side either
        o = self.run_js(r'''
const sides = (poly) => { const ob = orientedBox(poly); return frontHonest(poly, ob); };
const rect = [[0, 0], [5, 0], [5, 14], [0, 14]];
const t = Math.tan(10 * Math.PI / 180);
const trap = [[0, 0], [5, 5 * t], [5, 14], [0, 14]];
const jog = [[0, 0], [1, 0], [1, 1.2], [4, 1.2], [4, 0], [5, 0], [5, 14], [0, 14]];
// and the street side follows it: the rectangle's +u... the trapezoid's leaning end is never chosen
console.log(JSON.stringify({ rect: sides(rect), trapBits: sides(trap), jogBits: sides(jog) }));
''')
        self.assertEqual(o['rect'], 15)
        self.assertEqual(bin(o['trapBits']).count('1'), 3)   # the leaning end is out, the other three stand
        self.assertEqual(bin(o['jogBits']).count('1'), 3)    # the recessed front is out


if __name__ == '__main__':
    unittest.main()
