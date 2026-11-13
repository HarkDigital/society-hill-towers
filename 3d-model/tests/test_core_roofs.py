"""Society Hill's roofs match the city round it (Oct 12, Mike over Old City: "a distinct cutoff where there is no roof
hardware on buildings in society hill", and "those buildings all appear to stand out from the rest color wise").

The core (the 2,800 buildings of 'Raising 2,800 buildings', CORE_EXT) never called roofClutter, so its flat roofs had no
ROOF_KIT note and the instanced hardware stopped at its edge; and its own roof gain (0.34 against the tiers' 0.17) drew
the same sampled ROOF_PAL entries pale and grey. The core now notes and dresses its flat roofs like the tiers and renders
its roofs at the tiers' gain and saturation; its walls keep their own gain (they matched)."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CoreRoofs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        a = cls.s.index("  step('Raising 2,800 buildings', () => {")
        cls.core = cls.s[a:cls.s.index('\n  });\n', a)]

    def test_core_flat_roofs_take_the_hardware(self):
        c = self.core
        self.assertIn('let flatTop = 0;', c)
        self.assertIn('if (!b.minH && hFlat < 60) flatTop = hFlat;', c)
        # laid in world space after the lift, so its ROOF_KIT note carries the roof's real height
        lift = c.index('parts[k].geom.translate(0, ty, 0)')
        call = c.index('roofClutter(', lift)
        self.assertLess(lift, call)
        self.assertIn('}, b.poly, ty || 0, flatTop, area, tCode, b.fa, i, color.clone().multiplyScalar(1 / kG), false, b.holes && b.holes.length ? b.holes : null);', c)   # Round 178: and its courtyards
        self.assertIn('const kG = FACADE_GAIN / CORE_FACADE_GAIN;', c)

    def test_core_roofs_render_like_the_tiers(self):
        s = self.s
        self.assertIn('const CORE_FACADE_GAIN = 0.52, CORE_ROOF_GAIN = ROOF_GAIN, CORE_ROOF_SAT = 1.2;', s)
        self.assertIn('cityMat.onBeforeCompile = facadeHook(FACADE_GAIN, ROOF_GAIN, 1.2);', s)
        self.assertIn('coreMat.onBeforeCompile = facadeHook(CORE_FACADE_GAIN, CORE_ROOF_GAIN, 1.0, CORE_ROOF_SAT);', s)
        # the roof-only saturation is the core's alone. Since Round 251 (Stage 2's program diet) the gains are each material's
        # uniform uFabG and the line is in both, the tiers' at 1.0 (mix(L, c, 1.0) is c): one program for both
        self.assertIn("'  diffuseColor.rgb = mix(diffuseColor.rgb, mix(vec3(dot(diffuseColor.rgb, vec3(0.2126, 0.7152, 0.0722))), diffuseColor.rgb, uFabG.w), step(0.7, n.y));',", s)
        self.assertIn('shader.uniforms.uFabG = { value: new THREE.Vector4(gW, gR, sat, satR || 1.0) };', s)
        self.assertEqual(s.count("customProgramCacheKey = () => 'fabric'"), 2)
        self.assertNotIn("=> 'fabric-core'", s)


if __name__ == '__main__':
    unittest.main()
