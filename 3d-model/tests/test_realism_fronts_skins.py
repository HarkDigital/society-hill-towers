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
            self.assertEqual(s.get('maskV'), 1, name)   # the mask's blue is each window's height inside it
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

    def test_the_masks_are_opaque_and_survive_a_premultiplied_decode(self):
        # the review: an image with alpha under 255 reaches WebGL through a premultiplied decode on WebKit (Safari, iOS,
        # the app), and every window's number in green moved by one across its rows, so a lit window drew in bands. The
        # masks are opaque RGB now; a premultiply and unmultiply round trip (as WebKit does it) leaves every byte alone
        from PIL import Image
        for name, s in self.d['sets'].items():
            for f in ('mask', 'maskHalf'):
                im = Image.open(ROOT / s[f])
                self.assertEqual(im.mode, 'RGB', (name, f))
                a = np.asarray(im.convert('RGBA')).astype(np.int64)
                al = a[..., 3:4]
                pm = np.round(a[..., :3] * al / 255.0)
                back = np.where(al > 0, np.round(pm * 255.0 / np.maximum(al, 1)), 0)
                self.assertTrue((back == a[..., :3]).all(), (name, f))

    def test_the_masks_blue(self):
        # a house window's blue is its height inside it, 0 at the sill to 64 at the head; a shop's display 128 to 192; the
        # door 255 with no glass; the head is up (the alpha it replaced ran the other way: the rooms' ceilings at the sill)
        from PIL import Image
        for name, s in self.d['sets'].items():
            a = np.asarray(Image.open(ROOT / s['mask'])).astype(int)
            r, b = a[..., 0], a[..., 2]
            self.assertFalse(((r > 127) & (b > 64) & (b < 128)).any(), name)
            self.assertFalse(((b > 192) & (b < 255)).any(), name)
            self.assertFalse(((r > 127) & (b == 255)).any(), name)   # the door is never glass
            ys, xs = np.nonzero((r > 127) & (b <= 64))
            if not len(ys):
                continue
            x = xs[len(xs) // 2]
            col = np.nonzero((r[:, x] > 127) & (b[:, x] <= 64))[0]
            run = col[: np.argmax(np.diff(col) > 1) + 1] if (np.diff(col) > 1).any() else col
            self.assertGreater(b[run[0], x], b[run[-1], x], name)   # the top row of a window is its head

    def test_a_display_lights_its_glass_alone(self):
        # the review: the display box covered most of each shop's ground floor and the dark green and black cast-iron
        # fronts glowed bone white after dark, frames, pilasters, panels and doors with the glass. The bake now marks the
        # glass alone inside the box, and the fronts with none (lacquered panels, a grille) stay dark
        from PIL import Image
        import bake_fronts as B
        lit = box = 0
        for name in ('shop', 'mixeduse', 'shop1'):
            s = self.d['sets'][name]
            a = np.asarray(Image.open(ROOT / s['mask'])).astype(int)
            inbox = (a[..., 2] >= 128) & (a[..., 2] <= 192)
            box += int(inbox.sum()); lit += int((inbox & (a[..., 0] > 127)).sum())
            mW, mH = s['cell'][0] // 2, s['cell'][1] // 2
            for k, c in enumerate(s['cells']):
                if c['id'] in B.DISPLAY_DARK.get(name, ()):
                    cell = a[(k // 4) * mH:(k // 4 + 1) * mH, (k % 4) * mW:(k % 4 + 1) * mW]
                    self.assertFalse(((cell[..., 2] >= 128) & (cell[..., 2] <= 192) & (cell[..., 0] > 127)).any(), (name, c['id']))
        self.assertGreater(box, 0)
        self.assertLess(lit / box, 0.8)    # the frames, the bulkheads and the doors in the box are not lit
        self.assertGreater(lit / box, 0.3)

    def test_every_set_inside_the_atlas_budget(self):
        # Round 184's budget, 4 by 4 cells of 384 by 768 (4.7 MP): the review found the one-storey shops at 7.1 MP
        for name, s in self.d['sets'].items():
            px = s['cols'] * s['cell'][0] * s['rows'] * s['cell'][1]
            self.assertLessEqual(px, 1536 * 3072, name)

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

    def test_display_glass_leaves_the_frames(self):
        # a dark green cast-iron front: near-black panes inside a frame, a mullion and a bulkhead the green of the paint;
        # only the panes are glass, and a shelf of bright goods inside a pane is the pane's
        import bake_fronts as B
        a = np.zeros((80, 120, 3)) + np.array([0.10, 0.17, 0.12])
        a[8:60, 8:56] = 0.035; a[8:60, 64:112] = 0.035
        a[40:46, 20:40] = 0.6   # goods on a shelf
        g = B.display_glass(a)
        self.assertTrue(g[10:58, 10:54].all())
        self.assertTrue(g[10:58, 66:110].all())
        self.assertFalse(g[:, 58:62].any())     # the mullion
        self.assertFalse(g[64:].any())          # the bulkhead
        self.assertFalse(g[:4].any() or g[:, :4].any())
        # a front that is all one dark grille: one piece, but a lattice, under a third of its box
        h = np.zeros((60, 90, 3)) + 0.2
        h[:, ::6] = 0.03; h[::6, :] = 0.03
        self.assertLess(B.display_glass(h).mean(), 0.2)

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


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Late(unittest.TestCase):
    def test_the_towers_empty_with_the_clock(self):
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const SKIN_LATE = ')
        js = s[a:s.index(';\n', a) + 2] + fn(s, 'skinLateAt') + r'''
console.log(JSON.stringify([0, 180, 360, 1020, 1110, 1140, 1260, 1320, 1439].map((m) => skinLateAt(m).map((v) => +v.toFixed(3)))));
'''
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = dict(zip([0, 180, 360, 1020, 1110, 1140, 1260, 1320, 1439], json.loads(r.stdout)))
        self.assertEqual(o[1020][0], 1.0)            # five o'clock: every suite roomLight lights
        self.assertLess(o[1260][0], 0.5)             # nine at night: under half of them
        self.assertGreaterEqual(o[1140][1], 0.8)     # the homes nearly full at seven
        self.assertLessEqual(max(o[180]), 0.25)      # three in the morning: the city mostly dark
        for m in o:
            self.assertTrue(0.2 <= o[m][0] <= 1 and 0.2 <= o[m][1] <= 1, (m, o[m]))
        self.assertAlmostEqual(o[1439][0], o[0][0], delta=0.01)   # no jump at midnight


class Fetch(unittest.TestCase):
    def test_only_names_one_thing(self):
        # the review: --only shop1 made the shop street floor again, not the one-storey shop set
        import fetch_fronts as F
        self.assertEqual([j[:2] for j in F.pick_jobs({'base/shop1'})], [('base', 'shop1')])
        self.assertEqual(len(F.pick_jobs(set(), 'shop1')), 16)
        with self.assertRaises(SystemExit):
            F.pick_jobs({'shop1'})


class PageWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_the_fronts_lie_on_the_fit(self):
        f = fn(self.s, 'frontsLay')
        self.assertIn('const ft = REAL ? frontFitOf(FRONTS.fit[k * 4 + s]) : null;', f)   # ?real=0 keeps Round 187's box side
        self.assertIn("Rs.aFr.array[n * 4 + 3] = hi;", f)   # the image's height at its width, for the storey remap
        self.assertIn('if (!REAL && cm.door && !porch', f)   # no foam stoops in the realistic look
        self.assertIn("put(G.crown, gc.crown, px + nx * 0.04, y1 - 0.22", f)

    def test_the_fronts_take_the_weather_and_the_sun(self):
        f = fn(self.s, 'frontSetRes')
        self.assertIn('if (REAL) wxSurfacePatch(sh);', f)
        # one program for every set (a set's own program compiled in flight the first time its houses came near)
        self.assertIn("mat.customProgramCacheKey = () => REAL ? (rich ? 'house-fronts|wx' : 'house-fronts|wx|lite') : 'house-fronts';", f)
        self.assertIn('const rich = REAL && !isTouch;', f)   # the reveal and the jambs: a computer's
        # the window's number read whole, the height from the blue, the varyings four to a row
        self.assertIn('vec2(floor(frMask.g * 255.0 + 0.5), floor(vSeed * 997.0))', f)
        self.assertIn('float frB = frMask.b * 255.0, shopG = step(96.0, frB) * (1.0 - step(224.0, frB))', f)
        self.assertNotIn('frMask.a', f)
        self.assertNotIn('vFrRows', f)
        self.assertIn('varying vec4 vFrR, vFrT; varying vec3 vFrSun;', f)
        self.assertNotIn("' + cols + '", f)
        self.assertIn('textureGrad(map, frUv, frGx, frGy)', f)
        self.assertIn('reflectedLight.directDiffuse *= 1.0 - 0.65 * vFrSun.z * frMask.r * (1.0 - frRv);', f)

    def test_the_storefronts_give_way(self):
        s = self.s
        a = s.index("step('Dressing the storefronts'")
        f = s[a:s.index("step('Raising the overpasses'", a)]
        self.assertIn("if (ign <= 1.0 - smoothstep(uFrR * 0.8, uFrR, fd)) discard;", f)   # the fronts' own dither, turned over
        self.assertIn("if (!FR_SHOPPY.has((FRONTS.buf[o + 9] | 0) & 15)) continue;", f)
        self.assertIn('if (FRONTS_ON && REAL) for (let k = 0; k < FRONTS.n; k++) {', f)   # ?real=0 keeps its storefronts
        # only on the side the front is laid on (a corner shop's side street keeps its storefronts), and only once the
        # shop set's atlas is in (uFrShop)
        self.assertIn('if (s2 === -2) s2 = FRONTS.side[k] = frontSide(k);', f)
        self.assertIn('if (vFrontNear * uFrShop > 0.5) {', f)
        self.assertIn('frShopOn.value = shopWait ? 0 : 1;', fn(s, 'frontsLay'))
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
        self.assertIn("mat.customProgramCacheKey = () => REAL ? 'tower-skin|real' + (SKIN_GLASS ? '|glass' : '') : 'tower-skin-' + kind;", f)   # Round 191: the city probe's windows
        self.assertIn("mat.customProgramCacheKey = () => 'skin-base|wx';", s)
        # the parapet starts where roofClutter's lip stops (h < 60 over the ground): never both
        self.assertIn("const par = REAL && !isTouch && !c.mid && !c.spec && c.y1 - (c.g0 != null ? c.g0 : c.y0) >= 60 ? 1.1 : 0;", f)
        self.assertIn('h < 60) roofClutter(', s)
        # the lit share follows the model's hour, and a far window is dimmer
        self.assertIn('mix(uSkinLate.y, uSkinLate.x, uSkinF.y)', f)
        self.assertIn('mix(0.9, 0.5, tsFar)', f)
        self.assertIn("'#include <emissivemap_fragment>\\nif (uNight > 0.001) { vec2 tsG", f)   # no rooms by day
        self.assertIn('skinLateU.value.set(L[0], L[1]);', fn(s, 'updateFronts'))

    def test_the_old_look_stays_behind_the_flag(self):
        s = self.s
        self.assertIn("cor: REAL ? null : mk(box, plain('front-cornice'), caps.cor, 'fronts-cornices', true),", s)
        self.assertIn("const SKIN_BASES = REAL && typeof FRONTS_DATA !== 'undefined'", s)


if __name__ == '__main__':
    unittest.main()
