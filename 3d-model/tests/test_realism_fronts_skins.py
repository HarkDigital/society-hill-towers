"""The realism pass on the house fronts and the tower and mid-rise walls (Oct 12, Mike: "please do anything necessary to
make this look more photo realistic and less cartoony").

The fronts lie on their walls' own lines (FRONTS.fit), keep their images' proportions with whole storeys repeated or
dropped to fill a wall (the bake's 'rows', the shader's remap), match their houses' colours, wear a moulded crown in place
of the cornice slab and no foam stoops, light their windows over the whole opening, take the sun in their reveals and
the weather, and the storefront boxes give way under a generated shop front; the tower and mid-rise walls start and end
on bay lines, meet the roof on a spandrel, vary pane by pane, light whole windows after dark and stand on a generated
street floor. Each is checked here on its data, its source or its own functions run under node."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def fn(src, name):
    a = src.index('  function ' + name + '(')
    return src[a:src.index('\n  }\n', a) + 4]


class Data(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'fronts.json').read_text())

    def test_the_sets_carry_their_proportions_and_storeys(self):
        import fetch_fronts as F
        for name, s in self.d['sets'].items():
            self.assertIn('aspect', s, name)
            self.assertEqual(s.get('maskA'), 1, name)   # the mask's alpha is each window's height inside it
            if name in F.SIZES:   # made again at its houses' proportions (once all sixteen are made)
                w, h = (int(v) for v in F.SIZES[name][0].split('x'))
                if abs(s['aspect'] - 0.6) > 0.02 or name == 'shop1':
                    self.assertAlmostEqual(s['aspect'], w / h, places=3, msg=name)
            rows = [c['rows'] for c in s['cells'] if c.get('rows')]
            if s['aspect'] < 1:
                self.assertGreaterEqual(len(rows), 8, name)   # most cells know their storeys
            for r in rows:
                self.assertTrue(0.06 < r[0] < r[1] <= 0.99 and r[2] >= 1, (name, r))
            for c in s['cells']:
                self.assertRegex(c.get('wall', ''), r'^#[0-9a-f]{6}$', (name, c['id']))

    def test_the_one_storey_shops(self):
        s = self.d['sets'].get('shop1')
        self.assertIsNotNone(s, 'the one-storey shops are baked')
        self.assertGreater(s['aspect'], 1.2)
        self.assertGreater(s['awn'], 0)

    def test_the_tiles_masks_are_folded(self):
        t = self.d['tiles']
        folded = [k for k, v in t.items() if v.get('folded')]
        self.assertGreaterEqual(len(folded), 25, folded)   # one clean window a bay and floor on most
        for k in folded:
            self.assertTrue(0 <= t[k]['spandV'] <= 1, k)

    def test_the_street_floors(self):
        b = self.d.get('bases') or {}
        self.assertGreaterEqual(len(b), 12, sorted(b))
        for k, v in b.items():
            for f in ('img', 'imgHalf', 'mask'):
                self.assertRegex(v[f], r'^art/tiles/base-%s(-mask)?(-half)?\.[0-9a-f]{10}\.(webp|png)$' % k)
                self.assertTrue((ROOT / v[f]).exists(), v[f])
            self.assertTrue(5 <= v['w'] <= 9 and v['h'] == 4.5, (k, v['w']))
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const SKIN_BASE = {')
        names = set()
        import re
        for lst in re.findall(r"\[([^\]]*)\]", s[a:s.index('};', a)]):
            names |= set(re.findall(r"'([a-z0-9]+)'", lst))
        self.assertLessEqual(names, set(b) | {'none'}, names - set(b))   # every street floor the page deals is baked


class Bake(unittest.TestCase):
    def test_storeys_from_the_rows_of_windows(self):
        import bake_fronts as B
        # a three-storey front: a ground floor with a door and a window, two upper rows of three sashes, each sash cut at
        # its meeting rail by the finder (two boxes, one window)
        wins = []
        for y0, y1 in ((0.10, 0.30), (0.40, 0.60)):   # upper rows, from the top
            for x0 in (0.1, 0.4, 0.7):
                wins += [(x0, y0, x0 + 0.18, (y0 + y1) / 2 - 0.005), (x0, (y0 + y1) / 2 + 0.005, x0 + 0.18, y1)]
        wins.append((0.5, 0.72, 0.8, 0.92))
        door = (0.12, 0.68, 0.3, 0.97)
        r = B.storeys(wins, door)
        self.assertEqual(r[2], 2)
        self.assertAlmostEqual(r[0], (1 - 0.68 + 1 - 0.6) / 2, places=3)   # halfway from the door's head to the sills over it
        self.assertAlmostEqual(r[1], r[0] + 2 * 0.3, places=3)              # two storeys as tall as their sills are apart
        self.assertIsNone(B.storeys([(0.1, 0.1, 0.3, 0.3)], None))

    def test_a_window_is_filled_to_its_box(self):
        # the realism pass's review of the lit towers: a window whose paint is dark only along its head and its jambs (a
        # light curtain filling the rest) is lit whole, not as a curtain-shaped cut-out; a curtain wall's glass is left
        import bake_fronts as B
        u = np.zeros((40, 30), bool)
        u[6:9, 5:25] = True        # the dark head over the curtain
        u[6:34, 5:7] = True        # and the jambs either side
        u[6:34, 23:25] = True
        f = B.fill_openings(u)
        self.assertTrue(f[6:34, 5:25].all())
        self.assertFalse(f[:5].any() or f[36:].any() or f[:, :4].any() or f[:, 26:].any())
        g = np.ones((40, 30), bool); g[18:21] = False   # glass but a spandrel band
        self.assertEqual(int(B.fill_openings(g).sum()), int(g.sum()))

    def test_the_fold_makes_one_clean_window_a_bay(self):
        import bake_fronts as B
        H = W = 128
        g = np.zeros((H, W), bool)
        for fy in range(4):
            for bx in range(8):
                g[fy * 32 + 6:fy * 32 + 24, bx * 16 + 3:bx * 16 + 13] = True
        rng = np.random.default_rng(3)
        noisy = g ^ (rng.random((H, W)) < 0.08)   # salt and pepper
        glass, vp, spand, pier = B.fold_mask(noisy, 8, 4)
        self.assertGreater((glass == g).mean(), 0.97)
        self.assertLess(vp[23, 5], 0.1)          # the sill
        self.assertGreater(vp[6, 5], 0.9)        # the head
        self.assertTrue(spand > 0.7 or spand < 0.2, spand)   # the band over and under the windows
        self.assertTrue(pier < 3 / 16 or pier > 13 / 16, pier)   # the pier between two windows, never a pane


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Fit(unittest.TestCase):
    def run_js(self, body):
        s = (ROOT / 'app.js').read_text()
        js = fn(s, 'frontHonest') + fn(s, 'frontFitWord') + fn(s, 'frontFitOf') + fn(s, 'orientedBox') + fn(s, 'frontRemaps') + body
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_a_front_lies_on_its_wall(self):
        # critic gap 0 (what was left of Mike's "off kilter"): a rectangle's sides are its walls; a wall turned 2 degrees
        # off its box's side is fitted at its own angle; a wall 25 cm inside its box (the box held out by a 40 cm stub) is
        # fitted 25 cm in; a side whose wall stops short at a corner is laid over the wall alone
        o = self.run_js(r'''
const fitOf = (poly) => { const ob = orientedBox(poly), fit = new Uint32Array(4), mask = frontHonest(poly, ob, fit);
  return { mask, ob: [ob.ux, ob.uz, ob.w, ob.d], fits: Array.from(fit).map(frontFitOf) }; };
const rect = [[0, 0], [5, 0], [5, 14], [0, 14]];
const t = Math.tan(2 * Math.PI / 180);
const trap = [[0, 0], [5, 5 * t], [5, 14], [0, 14]];
const stub = [[0, 0.25], [2.3, 0.25], [2.3, 0], [2.7, 0], [2.7, 0.25], [5, 0.25], [5, 14], [0, 14]];
const cut = [[0.6, 0], [5, 0], [5, 14], [0, 14], [0, 0.6]];
console.log(JSON.stringify({ rect: fitOf(rect), trap: fitOf(trap), stub: fitOf(stub), cut: fitOf(cut) }));
''')
        for f in o['rect']['fits']:
            self.assertIsNotNone(f)
            self.assertAlmostEqual(f[0], 0, places=2)
            self.assertAlmostEqual(f[1], 0, places=3)
            self.assertLessEqual(f[2], 0.005); self.assertGreaterEqual(f[3], 0.995)
        # the trapezoid: the leaning end's line follows the wall at 2 degrees (one of its fits carries the slope)
        slopes = sorted(abs(f[1]) for f in o['trap']['fits'] if f)
        self.assertAlmostEqual(slopes[-1], 2 * 3.14159 / 180, delta=0.003)
        # the stub: some side's wall stands about 25 cm inside the box's side, and its front goes there
        offs = sorted(f[0] for f in o['stub']['fits'] if f)
        self.assertLess(offs[0], -0.2)
        self.assertGreater(offs[0], -0.3)
        # the cut corner: the short sides are covered 0.6 m short of the corner, out of 5 m and 14 m
        spans = sorted(f[3] - f[2] for f in o['cut']['fits'] if f)
        self.assertLess(spans[0], 0.97)

    def test_a_curved_wall_is_one_wall(self):
        # the cladding's walls (buildings 7): a square's four sides are four walls; a quarter circle in sixteen facets
        # (which meets the side before it on its tangent and the one after it at a corner) is one wall with that side, so
        # its bays run round it and are never squeezed into a facet
        o = self.run_js(fn((ROOT / 'app.js').read_text(), 'skinWalls') + r'''
const sq = skinWalls([[0, 0], [10, 0], [10, 10], [0, 10]]);
const arc = [[0, 0], [20, 0]];
for (let k = 1; k <= 16; k++) { const a = k / 16 * Math.PI / 2; arc.push([20 + 10 * Math.sin(a), 10 - 10 * Math.cos(a)]); }
arc.push([0, 10]);
const w = skinWalls(arc);
console.log(JSON.stringify({ sq: sq.len, runs: Array.from(w.run), lens: w.len.map((v) => +v.toFixed(2)) }));
''')
        self.assertEqual(o['sq'], [10, 10, 10, 10])
        arcRuns = set(o['runs'][1:17])   # the sixteen facets
        self.assertEqual(len(arcRuns), 1, o)
        self.assertEqual(o['runs'][0], o['runs'][1], o)   # the side it continues on its tangent
        self.assertEqual(len(o['lens']), 3, o)   # that wall, the top and the west side
        self.assertIn(35.7, o['lens'], o)

    def test_the_storeys_remap_only_where_a_storey_fits(self):
        o = self.run_js(r'''
const cm = { rows: [0.3, 0.9, 2] };
console.log(JSON.stringify([frontRemaps(cm, 9, 11), frontRemaps(cm, 9, 4.5), frontRemaps({ rows: null }, 9, 11), frontRemaps(cm, 0, 11)]));
''')
        # 9 m of image on an 11 m wall: 2.7 m ground floor, 0.9 m band, 7.4 m of storeys; on 4.5 m the storeys have 0.9 m,
        # under four tenths of one (2.7 m), so the front stretches as it did
        self.assertEqual(o, [True, False, False, False])


class PageWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_the_fronts_lie_on_the_fit(self):
        f = fn(self.s, 'frontsLay')
        self.assertIn('const ft = frontFitOf(FRONTS.fit[k * 4 + s]);', f)
        self.assertIn("Rs.aFr.array[n * 4 + 3] = hi;", f)   # the image's height at its width, for the storey remap
        self.assertIn('if (!REAL && cm.door && !porch', f)   # no foam stoops in the realistic look
        self.assertIn("put(G.crown, gc.crown, px + nx * 0.04, y1 - 0.22", f)

    def test_the_fronts_take_the_weather_and_the_sun(self):
        f = fn(self.s, 'frontSetRes')
        self.assertIn('wxSurfacePatch(sh);', f)
        # one program for every set (a set's own program compiled in flight the first time its houses came near)
        self.assertIn("mat.customProgramCacheKey = () => 'house-fronts|wx';", f)
        self.assertNotIn("' + cols + '", f)
        self.assertIn('textureGrad(map, frUv, frGx, frGy)', f)
        self.assertIn('reflectedLight.directDiffuse *= 1.0 - 0.65 * vFrSun.z * frMask.r * (1.0 - frRv);', f)

    def test_the_storefronts_give_way(self):
        s = self.s
        a = s.index("step('Dressing the storefronts'")
        f = s[a:s.index("step('Raising the overpasses'", a)]
        self.assertIn("if (ign <= 1.0 - smoothstep(uFrR * 0.8, uFrR, fd)) discard;", f)   # the fronts' own dither, turned over
        self.assertIn("new Set(['shop', 'mixeduse', 'loft', 'shop1'].map(FR_SET_IX)", f)
        self.assertIn('if (baseCells.size && onBase(x - nx * 1.2, z - nz * 1.2)) { baseN++; continue; }', f)
        self.assertNotIn('aFrontNear', f)   # the flag rides in the colour's sign: no stream of its own (a phone's memory)
        self.assertIn('vFrontNear = 1.0 - step(-1e-5, color.r); vColor = abs(vColor);', f)

    def test_the_skins(self):
        s = self.s
        a = s.index("step('Cladding the towers'")
        f = s[a:s.index('\n  });\n', a)]
        # a whole number of bays a wall, a wall a run of the outline's edges
        self.assertIn('const L = W.len[W.run[i]], kq = Math.max(1, Math.round(L / bayW)) / T.nb / L; uA = u0 + W.at[i] * kq; uB = uA + len * kq;', f)
        self.assertIn('wxSurfacePatch(sh);', f)
        self.assertIn('if (SKIN_BASES) await skinBasesLay(tex, aniso, baseGot);', f)
        # the rooms behind the glass: the facade's own, cut at the tile's pier and spandrel
        self.assertIn("roomLight(vec2(fract(tsG.x), mix(fract(tsG.y), tsVp, uSkinF.x)), floor(tsG), vSeed * 3.1, uSkinF.y); }", f)
        # every kind shares one program in the realistic look (a program a kind cost the build 8 s of compiling), the
        # old look keeps its own
        self.assertIn("mat.customProgramCacheKey = () => REAL ? 'tower-skin|real' : 'tower-skin-' + kind;", f)
        self.assertIn("mat.customProgramCacheKey = () => 'skin-base|wx';", s)
        self.assertIn("const par = REAL && !isTouch && !c.mid && !c.spec && c.y1 - (c.g0 != null ? c.g0 : c.y0) >= 58 ? 1.1 : 0;", f)

    def test_the_old_look_stays_behind_the_flag(self):
        s = self.s
        self.assertIn("cor: REAL ? null : mk(box, plain('front-cornice'), caps.cor, 'fronts-cornices', true),", s)
        self.assertIn("const SKIN_BASES = REAL && typeof FRONTS_DATA !== 'undefined'", s)


if __name__ == '__main__':
    unittest.main()
