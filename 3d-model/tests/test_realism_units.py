"""The integration of the realism pass (Oct 13): a WebGL program has sixteen texture units on a computer and on an iPhone,
and the ground's program stood at exactly sixteen once every workstream had added its maps, so the roads, the lots and the
decks (one sampler more each) failed to link and drew nothing. A paved surface takes no grass and no vegetation maps, and
the wet streets read the lamp map under the lamp patch's own name."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class Units(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_a_paved_surface_carries_no_grass_or_vegetation_maps(self):
        f = cut(self.s, '  function surfTexPatch(shader, opt) {', '\n  }\n')
        self.assertIn("const paved = REAL && !forced && /varying vec4 vLane;|uniform sampler2D (uLotTex|uConcWall|uElSteel)\\b/.test(shader.fragmentShader);", f)
        self.assertIn("paved ? 'uniform float uGrassK;", f)
        self.assertIn("(forced ? '1.0;' : paved ? '0.0;'", f)
        self.assertIn('...vegGrassGLSL(forced, paved),', f)
        self.assertIn('vegAfterGLSL(paved),', f)
        self.assertIn('vegSurfPatch(shader, forced, paved);', f)
        g = cut(self.s, '  function vegGrassGLSL(forced, paved) {', '\n  }\n')
        self.assertNotIn('texture2D', g.split('\n')[1])   # the paved return comes first and samples nothing
        v = cut(self.s, '  function vegSurfPatch(shader, forced, paved) {', '\n  }\n')
        self.assertIn("(paved ? '' : 'uniform sampler2D uMacro, uLand, uCanopy, uRiprap; ')", v)

    def test_the_road_lot_and_deck_patches_run_before_the_surface_patch(self):
        s = self.s
        self.assertIn('m.onBeforeCompile = (sh, r) => { lanePatch(sh, fresh); prev(sh, r); };', s)
        self.assertIn('m.onBeforeCompile = (sh, r) => { lotPatch(sh); surfTexPatch(sh, r); };', s)
        self.assertIn("ovpMat.onBeforeCompile = (sh, r) => { deckWallPatch(sh, 'concrete'); prevO(sh, r); };", s)

    def test_one_lamp_sampler(self):
        self.assertNotIn('uWxLampMap', self.s)


if __name__ == '__main__':
    unittest.main()
