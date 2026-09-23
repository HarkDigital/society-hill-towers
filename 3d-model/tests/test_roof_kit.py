"""Round 150: the roofs at night and their hardware (Mike: the tops of the buildings look too dark; the roofs look too plain).

The facade hook gives every face turned up a share of its own colour after dark (ROOF_NIGHT). Every flat roof of the
packed tiers is noted in ROOF_KIT by roofClutter, on phones too (the note comes before the touch return), and
'Fitting out the rooftops' lays condensers, rooftop units, hatches, vent stacks and dishes near the eye as five
instanced meshes, refilled as the eye moves. These checks pin the wiring and the ordering that matter."""
from pathlib import Path
import re
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
        self.assertLess(body.index('roofKitNote(ob, ax, base + h, area, seed);'), body.index('if (isTouch || h < 5) return;'))

    def test_the_step_and_the_refill(self):
        s = self.s
        self.assertIn("step('Fitting out the rooftops', () => {", s)
        self.assertLess(s.index("step('Fitting out the rooftops'"), s.index("step('Lighting the skyline'"))
        self.assertIn('    updateRoofKit(now);   // Round 150\n', s)
        # a scale must default, or four of the five kinds get NaN matrices and vanish (the first build did)
        self.assertIn('const put = (kind, x, y, z, rot, s = 1) => {', s)
        kinds = s[s.index('    const kinds = [\n'):s.index('    for (const kd of kinds) {')]
        self.assertEqual(len(re.findall(r'\{ cap: isTouch \?', kinds)), 5)


if __name__ == '__main__':
    unittest.main()
