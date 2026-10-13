"""The realism pass, the ground and the vegetation (Oct 12, Mike: "please do anything necessary to make this look more photo
realistic and less cartoony. This should apply to all surfaces/water/anything you can improve to look more real").

- the tree cards: the atlas keeps its colour premultiplied (the 1 to 2 px black outline round every crown from the air
  was the canvas's clear texels uploaded as black and mipped into the edges), each tree is its own (mirror, size, width,
  tint from its seed), the card is lit as a dome, a tree turns over a stretch of the change and dissolves between its two
  pictures, autumn comes in mid-October through a turning picture, and snow lies on the boughs;
- a computer at the full tier draws the cells at the bake's 448 and 224 on a canvas as tall as its rows, a phone keeps 128
  and 64;
- the lawn's photographed colour, the parks' macro from the air, the yards on built-up ground (LAND_MASK), the woods'
  canopy and the wood field, the rivers' banks (riprap, wet silt, the tide's stain), the canopy map's shade and leaf fall;
- the tufts packed near the eye in the lawn's own colour, flattened by snow; the snow cover in drifts, not squares.
?real=0 keeps the old ground, line for line."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def fn(src, name):
    a = src.index('  function ' + name + '(')
    return src[a:src.index('\n  }\n', a) + 4]


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_the_atlas_is_premultiplied_and_divided_back(self):
        s = self.s
        self.assertIn('tex.premultiplyAlpha = true;', fn(s, 'treeArtAtlas'))
        self.assertIn("tx.rgb = min(tx.rgb / max(tx.a, 0.004), vec3(1.0));", s)

    def test_each_tree_is_its_own(self):
        s = self.s
        a = s.index('  const TREE_ART_VERT = ')
        v = s[a:s.index('  }`;', a)]
        self.assertIn('mix(position.x + 0.5, 0.5 - position.x, step(0.5, v1))', v)   # mirrored by its seed
        self.assertIn('* (0.92 + 0.16 * v2)', v)                                     # its size
        self.assertIn('- 0.035 * S * (1.0 - lean)', v)                               # the root plate under the grass
        self.assertIn('float turn = smoothstep(seedT * 0.7, seedT * 0.7 + 0.3, L1.x);', v)   # inside the change, always
        self.assertIn('nrmOut = normalize(rt * q.x * 0.75 + up * q.y * 0.75 + nC * 0.65 + vec3(0.0, 0.25, 0.0));', v)
        self.assertIn("seedT = abs(aLS.y);", v)                                # a wood field tree's seed is negative

    def test_snow_on_the_trees_and_the_ground(self):
        s = self.s
        self.assertIn("uSnowAcc: wxSurfU.uSnowAcc, uTexelS: { value: 1.5 / S.AH }", s)
        self.assertNotIn("floor(wxWP.xz * 0.9)", s)                                  # the 1.1 m checkerboard
        self.assertIn("transformed.y *= 1.0 - smoothstep(0.15, 0.45, uSnowAcc);", s)  # the tufts lie down

    def test_the_tufts(self):
        s = self.s
        self.assertIn('GRASS_R = REAL ? (isTouch ? 30 : 45) : (isTouch ? 140 : 160);', s)
        self.assertIn("normal_fragment_begin.replace('normal = normal * faceDirection;', '')", fn(s, 'grassInit'))

    def test_the_old_ground_stays_under_real_off(self):
        g = fn(self.s, 'vegGrassGLSL')
        self.assertIn('if (!REAL) return pre.concat([', g)
        self.assertIn("MEADOW_GAIN.toFixed(2)", g)
        self.assertIn('if (!REAL) return;', fn(self.s, 'vegSurfPatch'))
        self.assertIn("if (!REAL) return '';", fn(self.s, 'vegAfterGLSL'))

    def test_the_wiring(self):
        s = self.s
        self.assertIn('...vegGrassGLSL(forced),', s)
        self.assertIn('vegSurfPatch(shader, forced);', fn(s, 'surfTexPatch'))
        self.assertIn('vegUpdate(now);', s)
        self.assertIn("step('Planting the woods', woodInit);", s)
        self.assertIn("const WOOD = { on: REAL && !isTouch && TIER === 0 && TREE_ART_ON,", s)   # never on a phone
        self.assertIn("const VEG_LAND = REAL && !TIER2 && typeof LAND_MASK !== 'undefined'", s)
        # the canopy map's quads seen from above wind clockwise: drawn both sides or none draws
        self.assertIn('depthTest: false, depthWrite: false, side: THREE.DoubleSide,', fn(s, 'canopyMapUpdate'))
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("LAND_MASK", text_of("land_mask.json", "null"))', b)
        self.assertIn('"land_mask.json"', b)

    def test_the_tide_band_is_one_snippet(self):
        s = self.s
        self.assertEqual(s.count('float tideK(float tH)'), 1)
        self.assertIn('function tidePatch(shader, worldExpr) {', s)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Seasons(unittest.TestCase):
    def test_the_turn(self):
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const TREE_CAL = {')
        cal = s[a:s.index('\n  };\n', a) + 5]
        js = cal + fn(s, 'treeSeasonOf') + r'''
const doy = (m, d) => Math.round((Date.UTC(2026, m - 1, d) - Date.UTC(2026, 0, 1)) / 864e5);
const at = (look, m, d, t) => treeSeasonOf(look, doy(m, d), t);
console.log(JSON.stringify({ oct12Plane: at('plane', 10, 12, true), oct20Maple: at('redmaple', 10, 20, true),
  nov1Maple: at('redmaple', 11, 1, true), nov20Oak: at('redoak', 11, 20, true), dec1Plane: at('plane', 12, 1, true), nov25Plane: at('plane', 11, 25, true),
  dec31Oak: at('redoak', 12, 31, true), oct30NoTurn: at('broadleaf', 10, 30, false) }));
'''
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o['oct12Plane'][:2], ['summer', 'summer'])        # mid-October: the planes are still green
        self.assertEqual(o['oct20Maple'][:2], ['summer', 'turning'])       # the red maples first, a fifth coloured
        self.assertEqual(o['nov1Maple'][:2], ['turning', 'autumn'])
        self.assertEqual(o['nov20Oak'][:2], ['turning', 'autumn'])   # the oaks last
        self.assertEqual(o['nov25Plane'][:2], ['autumn', 'autumn'])        # the planes hold their leaves into late November
        self.assertEqual(o['dec1Plane'][:2], ['autumn', 'winter'])
        self.assertEqual(o['dec31Oak'][:2], ['winter', 'winter'])   # the oaks hold theirs into December
        self.assertEqual(o['oct30NoTurn'][:2], ['summer', 'autumn'])       # a look without a turning picture goes straight

    def test_a_computer_draws_the_bake_size(self):
        s = (ROOT / 'app.js').read_text()
        d = json.loads((ROOT / 'tree_art.json').read_text())
        js = ('const THREE = { CanvasTexture: function (c) { this.image = c; } };\n'
              'const renderer = { capabilities: { isWebGL2: true, getMaxAnisotropy: () => 8 } };\n'
              'const document = { createElement: () => ({ getContext: () => ({}) }) };\n'
              'const TREE_ART = ' + json.dumps({k: d[k] for k in ('looks', 'side', 'top')}) + ';\n'
              'const out = [];\n'
              'for (const [isTouch, TIER] of [[false, 0], [false, 1], [true, 0]]) {\n' + fn(s, 'treeArtAtlas') +
              '  for (const v of ["side", "top"]) { const a = treeArtAtlas(v); out.push([isTouch, TIER, v, a.N, a.A, a.AH, a.C, a.tex.premultiplyAlpha]); }\n}\n'
              'console.log(JSON.stringify(out));')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = {(t, k, v): (N, A, AH, C, pm) for t, k, v, N, A, AH, C, pm in json.loads(r.stdout)}
        cells = 2 * len(d['looks'])
        self.assertEqual(got[(False, 0, 'side')][:2], (448, 448 * 8))
        self.assertGreaterEqual(got[(False, 0, 'side')][2], -(-cells // 8) * 448)
        self.assertEqual(got[(False, 1, 'side')][:3], (256, 2048, 2048))   # a lighter tier keeps Round 184's canvas
        self.assertEqual(got[(True, 0, 'side')][:3], (128, 1024, 1024))    # a phone keeps its 128 cells
        self.assertEqual(got[(True, 0, 'top')][:3], (64, 512, 512))
        self.assertTrue(all(v[4] for v in got.values()))


class Data(unittest.TestCase):
    def test_the_trees_turn_and_mute(self):
        d = json.loads((ROOT / 'tree_art.json').read_text())
        self.assertEqual((d['side'], d['top']), (448, 224))
        turning = [lk for lk in d['looks'] if 'turning' in d['images'][lk]['side']]
        self.assertEqual(len(turning), 25)                                  # every look that colours but the evergreens
        for lk in ('pine', 'spruce', 'holly'):
            self.assertNotIn(lk, turning)
        b = (ROOT / 'bake_tree_art.py').read_text()
        self.assertIn("MUTE = {'autumn': (0.82, 0.95), 'spring': (0.82, 0.95)}", b)

    def test_the_ground_set(self):
        d = json.loads((ROOT / 'ground_art.json').read_text())['veg']
        self.assertEqual(set(d), {'parkmacro', 'canopy_summer', 'canopy_autumn', 'canopy_winter', 'riprap', 'alley'})
        from PIL import Image
        for k, rec in d.items():
            self.assertEqual(set(rec), {'img', 'imgHalf', 'm', 'mean'})
            self.assertEqual(Image.open(ROOT / rec['img']).size, (1024, 1024), k)
            self.assertEqual(Image.open(ROOT / rec['imgHalf']).size, (512, 512), k)
            self.assertTrue(all(0 < v < 1 for v in rec['mean']), k)
        self.assertEqual(d['parkmacro']['m'], 240.0)
        self.assertEqual(d['canopy_summer']['m'], 70.0)
        # a forest from the air is dark and green, its winter grey-brown
        s, w = d['canopy_summer']['mean'], d['canopy_winter']['mean']
        self.assertGreater(s[1], s[0]); self.assertGreater(w[0], w[1])

    def test_the_land_mask(self):
        m = json.loads((ROOT / 'land_mask.json').read_text())
        self.assertEqual(m['box'], [-12000.0, -21700.0, 28500.0, 31400.0])   # pack_city.py CITY
        from PIL import Image
        import numpy as np
        im = Image.open(ROOT / m['img'])
        self.assertEqual(im.mode, 'RGB')                                     # no alpha: a browser may premultiply by it
        self.assertEqual(im.size, (m['w'], m['h']))
        self.assertEqual(Image.open(ROOT / m['imgHalf']).size, (m['w'] // 2, m['h'] // 2))
        a = np.asarray(im, np.float32) / 255
        px = lambda x, z: a[int((z - m['box'][1]) / m['px']), int((x - m['box'][0]) / m['px'])]
        self.assertGreater(px(-1300, -300)[0], 0.5)      # Center City is built up
        self.assertLess(px(-1300, -300)[1], 0.1)         # and no woods
        self.assertGreater(px(-5600, -11600)[1], 0.5)    # the Wissahickon gorge is woods
        self.assertGreater(px(-5450, 1500)[2], 0.9)      # the Schuylkill at Bartram's is a river's bank
        self.assertLess(px(-1300, -300)[2], 0.1)


if __name__ == '__main__':
    unittest.main()
