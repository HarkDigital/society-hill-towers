"""Round 157: a phone's far windows (Mike: "On mobile, the lights on buildings are not visible until you get very
close"). A lit window is drawn only while a floor spans a pixel or two, and under that both facade shaders fell back
to a flat glow a quarter to a fifth of the rooms' own mean; a phone has about a third of a desktop's pixels, so its
towers went grey at 0.6 to 1.9 km. On touch the fallback is a pyramid of room blocks at the rooms' own mean, weighted
by the desktop's resolve at FAR_K times the pixels. These checks hold the wiring (touch only, both shaders, the
desktop's strings untouched) and run the block hash itself to prove the blocks keep the rooms' mean."""
import math
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def fract(x):
    return x - math.floor(x)


def room_hash(p):   # WINDOW_INTERIOR_GLSL's roomHash, in doubles
    q = [fract(p[0] * .1031), fract(p[1] * .1031), fract(p[0] * .1031)]
    d = q[0] * (q[1] + 33.33) + q[1] * (q[2] + 33.33) + q[2] * (q[0] + 33.33)
    q = [v + d for v in q]
    return fract((q[0] + q[1]) * q[2])


class FarLit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        m = re.search(r'const FAR_LIT_GLSL = `(.*?)`;', cls.src, re.S)
        assert m, 'FAR_LIT_GLSL not found'
        cls.glsl = m.group(1)

    def test_touch_only(self):
        self.assertIn('const FAR_LIT = isTouch;', self.src)
        k = float(re.search(r'const FAR_K = ([\d.]+);', self.src).group(1))
        self.assertTrue(2.0 <= k <= 3.0, k)

    def test_both_shaders_carry_it_and_the_desktop_keeps_its_fallback(self):
        self.assertIn("FAR_LIT ? FAR_LIT_GLSL : ''", self.src)                 # the facade hook
        self.assertIn("${FAR_LIT ? FAR_LIT_GLSL : ''}", self.src)              # the curtain-wall glass
        # the desktop's own strings are the else branches, unchanged
        self.assertIn(": '      shtLit = 0.05 * windowArea;'", self.src)
        self.assertIn(": '    shtLit = mix(0.035*windowArea,max(0.0,glass-roomFrame*.98),resolved);'", self.src)
        self.assertIn(": '    shtLamp = mix(vec3(0.82,0.67,0.47),interior,resolved);'", self.src)
        self.assertIn(": 'mix(.055,1.0,resolved)'", self.src)

    def test_weight_is_the_desktops_resolve(self):
        # the facade: the desktop's det at uDetFar 1 on fwidth / FAR_K, and its pixels-a-floor gate times FAR_K
        self.assertIn("'      float fwD = fwidth(v) / ' + FAR_K.toFixed(2) + ';'", self.src)
        self.assertIn("smoothstep(0.8, 2.4, ' + FAR_K.toFixed(2) + ' / max(fwidth(uW) / 2.0, fwidth(fv) / facadeFp))", self.src)
        # the glass: its det and column gate with FAR_K times the pixels
        self.assertIn('fp*${FAR_K.toFixed(2)}/aaV-1.3', self.src)
        self.assertIn('muP*2.0*${FAR_K.toFixed(2)}/aaU', self.src)

    def test_blocks_keep_the_rooms_mean(self):
        m = re.search(r'step\(\.(\d+), roomHash\(key\)\) \* \(\.(\d+) \+ ([\d.]+) \* roomHash\(key \+ ([\d.]+)\)\)', self.glsl)
        self.assertIsNotNone(m)
        cut, base, span, off = float('.' + m.group(1)), float('.' + m.group(2)), float(m.group(3)), float(m.group(4))
        # roomLight lights a room at odds of about 0.48 with a mean brightness factor of 1: the blocks' expectation
        self.assertAlmostEqual((1 - cut) * (base + span / 2), 0.48, delta=0.01)
        # and the hash delivers it over real keys, at level 0 and at a coarse level
        for L in ((0.0, 0.0), (3.0, 2.0)):
            tot, n = 0.0, 0
            for i in range(-60, 60):
                for j in range(0, 60):
                    seed = 0.37 + (i % 7) * 0.113
                    kx = math.floor(i / 2 ** L[0]) + seed * 113.7 + L[0] * 17.0 + L[1] * 5.1
                    ky = math.floor(j / 2 ** L[1]) + seed * 39.1 - L[1] * 5.3 + L[0] * 2.9
                    h = room_hash((kx, ky))
                    tot += (h >= cut) * (base + span * room_hash((kx + off, ky + off)))
                    n += 1
            self.assertAlmostEqual(tot / n, 0.48, delta=0.06, msg=str(L))

    def test_blocks_are_at_least_two_pixels(self):
        self.assertIn('max(log2(max(2.0 * fpx, vec2(1.0e-6))), 0.0)', self.glsl)


if __name__ == '__main__':
    unittest.main()
