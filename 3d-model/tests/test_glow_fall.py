"""Round 253 (Mike, from the phone at night: "The lights all bunch up on mobile to just look white"): a phone's far lamp
glow fades past the point size's floor, so the far city's thousands of additive dots no longer sum to a clipped band.
Measured on the phone path at night: 8.5 to 16% of the horizon band's pixels at 255 before, 0.2 to 1.1% at the power 1.2,
under 1% with the glow hidden altogether; a computer (ACES after the glow) is untouched."""
from pathlib import Path
import unittest

SRC = (Path(__file__).resolve().parents[1] / 'app.js').read_text()


class GlowFall(unittest.TestCase):
    def test_a_phone_only_with_its_power(self):
        self.assertIn("const GLOW_FALL = (() => { const m = /[?&]glowfall=([0-9.]+)/.exec(location.search); return m ? +m[1] : 1.2; })();", SRC)
        self.assertIn('const GLOW_FALL_U = { value: new THREE.Vector2(isTouch ? GLOW_FALL : 0, 0) };', SRC)

    def test_the_fade_starts_at_the_floor(self):
        # the dot's own size over the floor (1.6), capped at 1: a lamp nearer than about 875 m keeps its whole light
        self.assertIn("vGlowK = uGlowFall.x > 0.0 ? pow(min(1400.0 / max(1.0, -mvPosition.z) / 1.6, 1.0), uGlowFall.x) : 1.0;", SRC)
        self.assertIn("diffuseColor.a *= vGlowK;", SRC)
        # the size law itself as it was (tests/test_glow_depth.py holds it too)
        self.assertIn("gl_PointSize = size * clamp(1400.0 / max(1.0, -mvPosition.z), 1.6, 7.5);", SRC)
        # at 5 km a lamp keeps (280 / 1.6) ** 1.2 of its light, about a fifth: the carpet thins, it does not go
        k = ((1400 / 5000) / 1.6) ** 1.2
        self.assertTrue(0.1 < k < 0.2, k)


if __name__ == '__main__':
    unittest.main()
