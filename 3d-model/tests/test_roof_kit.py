"""Round 150: the roofs at night and their hardware (Mike: the tops of the buildings look too dark; the roofs look too plain).

The facade hook gives every face turned up a share of its own colour after dark (ROOF_NIGHT). Every flat roof of the
packed tiers is noted in ROOF_KIT by roofClutter, on phones too (the note comes before the touch return), and
'Fitting out the rooftops' lays condensers, rooftop units, hatches, vent stacks and dishes near the eye as five
instanced meshes, refilled as the eye moves. These checks pin the wiring and the ordering that matter.

Oct 12 (Mike: rooftop units floating in the air over East Passyunk Avenue): a note was the roof's oriented box, and the
lay scatters units across up to 1.6 times its half length, so on a roof that is not its own box (a wedge on a diagonal
avenue, a rowhouse with a rear ell, a courtyard) some stood beyond the roof at roof height. Each note now carries an 8 by
6 occupancy mask of the box (roofKitMask), every unit and dish in the lay is gated on it (roofKitOn), and roofClutter's
baked boxes are tested against the footprint itself. The mask functions run under node, from the page's own source."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RoofKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_roof_glow(self):
        s = self.s
        self.assertRegex(s, r'const ROOF_NIGHT = 0\.\d+;')
        self.assertIn("'\\ntotalEmissiveRadiance += diffuseColor.rgb * uNight * ' + ROOF_NIGHT.toFixed(3) + ' * smoothstep(0.35, 0.75, vWNorm.y);'", s)

    def test_every_flat_roof_is_noted_before_the_touch_return(self):
        s = self.s
        body = s[s.index('  function roofClutter('):s.index('  // ---- pitched roofs for the packed tiers')]
        self.assertLess(body.index('roofKitNote(ob, ax, base + h, area, seed, poly, holes);'), body.index('if (isTouch || h < 5) return;'))

    def test_the_step_and_the_refill(self):
        s = self.s
        self.assertIn("step('Fitting out the rooftops', () => {", s)
        self.assertLess(s.index("step('Fitting out the rooftops'"), s.index("step('Lighting the skyline'"))
        self.assertIn('    updateRoofKit(now);   // Round 150\n', s)
        # a scale must default, or four of the five kinds get NaN matrices and vanish (the first build did)
        self.assertIn('const put = (kind, x, y, z, rot, s = 1) => {', s)
        kinds = s[s.index('    const kinds = [\n'):s.index('    ];\n', s.index('    const kinds = [\n'))]
        self.assertEqual(len(re.findall(r'\{ cap: isTouch \?', kinds)), 5)
        # the realism pass: the roof decks and the solar arrays come after the five, under REAL, so put()'s kinds 0 to 4 hold
        more = s[s.index('    const kinds = [\n'):s.index('    for (const [ki, kd] of kinds.entries()) {')]
        self.assertEqual(more.count('kinds.push({ cap: isTouch ?'), 2)
        self.assertIn('    if (REAL) {\n      kinds[0].parts.push(', more)


def fn(src, name):
    a = src.index('  function ' + name + '(')
    return src[a:src.index('\n  }\n', a) + 4]


class OnTheRoof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_every_unit_is_gated(self):
        s = self.s
        a = s.index('  function roofKitLay() {')
        lay = s[a:s.index('\n  }\n', a)]
        # units go through item(), which asks the mask; the two dishes placed with put() ask it themselves
        self.assertIn('const item = (kind, u, v, r) => { if (!full && !roofKitOn(mlo, mhi, u, v, hl, hs)) { ROOFKIT.off++; return; }', lay)
        self.assertEqual(lay.count('put(4, x, y, z, -0.35, 1)'), 2)
        self.assertEqual(lay.count('if (full || roofKitOn(mlo, mhi, du, dv, hl, hs))'), 2)
        self.assertIn('const o = a[q] * ROOF_KIT_STRIDE', lay)

    def test_notes_carry_the_footprint(self):
        s = self.s
        self.assertIn('roofKitNote(ob, ax, base + h, area, seed, poly, holes);', s)
        self.assertIn("Math.floor(B[i * ROOF_KIT_STRIDE] / ROOFKIT.cell)", s)
        self.assertNotIn('B[i * 8]', s)
        # the baked boxes are tested against the footprint too
        self.assertIn('add = (pg, y0, y1, hex, st2, hs2) => { if (hs2 || onRoof(pg)) add0(pg, y0, y1, hex, st2, hs2); };', s)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Mask(unittest.TestCase):
    def run_js(self, body):
        s = (ROOT / 'app.js').read_text()
        js = 'const RK_NU = 8, RK_NV = 6;\n' + fn(s, 'pointInPoly') + fn(s, 'roofKitMask') + fn(s, 'roofKitOn') + body
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_masks(self):
        out = self.run_js(r'''
const ob = { cx: 0, cz: 0 }, ax = { ax: 1, az: 0, hl: 20, hs: 10 };
const rect = [[-20, -10], [20, -10], [20, 10], [-20, 10]];
// an L: the box's +u, -v quarter is empty (the yard beside a rear ell); the lay's perpendicular is (-uz, ux) = (0, 1)
const ell = [[-20, -10], [0, -10], [0, 0], [20, 0], [20, 10], [-20, 10]];
const court = [[[-6, -4], [6, -4], [6, 4], [-6, 4]]];
const f32 = (m) => Array.from(new Float32Array(m));
const R = f32(roofKitMask(ob, ax, rect, null)), L = f32(roofKitMask(ob, ax, ell, null)), C = f32(roofKitMask(ob, ax, rect, court));
const on = (m, u, v) => roofKitOn(m[0], m[1], u, v, 20, 10);
console.log(JSON.stringify({
  rectFull: R[0] === 0xffffff && R[1] === 0xffffff,
  ellRoof: on(L, -10, -5) && on(L, 10, 5) && on(L, -10, 5),
  ellYard: on(L, 10, -5) || on(L, 15, -8) || on(L, 5, -2),
  courtRoof: on(C, -15, 0) && on(C, 15, 0),
  courtHole: on(C, 0, 0),
  outside: on(R, 25, 0) || on(R, 0, 12),
}));
''')
        self.assertTrue(out['rectFull'], 'a rectangle is all roof')
        self.assertTrue(out['ellRoof'], 'the L keeps its roof')
        self.assertFalse(out['ellYard'], 'no unit over the yard beside the ell')
        self.assertTrue(out['courtRoof'])
        self.assertFalse(out['courtHole'], 'no unit over a courtyard')
        self.assertFalse(out['outside'])


if __name__ == '__main__':
    unittest.main()
