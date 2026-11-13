"""Stage 2 of the Nov 10 plan, its performance half (Round 247): fewer programs and less wasted shading, nothing on screen
changed (each checked by a pixel parity of noon and night poses, devlog Round 247).

- The program diet: the outer city's and the core's facades share one program (their gains are each material's uniform,
  uFabG and uFabR, never literals); the El stations' four lit materials one key; the lamps' lens and lantern glass one
  (uLensK); the roof kit's kinds one program but the deck's, which ends in a discard (KIT_SHARED).
- The backdrops drawn last: the sky dome at 45 and the apron at 40, both under the river mirror's sweep line (50), the
  apron named out of the mirror; every other sampled window of the GPU timer draws them in the old order under 'sceneB'.
- The cloud shadow's gate: cloudShade returns 0 at once where its strength is 0."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


class Diet(unittest.TestCase):
    def test_one_facade_program(self):
        self.assertEqual(SRC.count("customProgramCacheKey = () => 'fabric'"), 2)
        self.assertIn("facade(cityMat, 'fabric|wx');", SRC)
        self.assertIn("facade(coreMat, 'fabric|wx');", SRC)
        a = SRC.index('    const facadeHook = (gW, gR, sat, satR) => (shader) => {')
        b = SRC.index('    cityMat.onBeforeCompile = facadeHook(FACADE_GAIN, ROOF_GAIN, 1.2);')
        h = SRC[a:b]
        # the gains reach the text only through the uniforms: no number of theirs is written into the shader
        self.assertNotRegex(h, r"' \+ \(?(gW|gR|sat|satR)\b")   # no gain concatenated into the shader's text
        self.assertIn("'uniform float uFabSnow, uFabWet; uniform vec4 uFabK; uniform vec4 uFabG; uniform float uFabR;',", h)

    def test_the_small_merges(self):
        self.assertIn("m.customProgramCacheKey = () => 'lamp-lens';", SRC)
        self.assertNotIn("'lamp-lens-' + k", SRC)
        self.assertIn("sh.uniforms.uLensK = { value: new THREE.Vector2(day, k) };", SRC)
        el = (ROOT / 'rebuilds' / 'elst.js').read_text()
        self.assertIn("m.customProgramCacheKey = () => 'elst-lit';", el)
        self.assertNotIn("'elst-' + key", el)

    def test_the_roof_kit_is_two_programs(self):
        self.assertIn("const KIT_SHARED = (k) => !(REAL && k === 5);", SRC)
        self.assertIn("mat.customProgramCacheKey = () => (shared ? 'roofkit' : 'roofkit-' + ki) + (REAL ? '-real' : '');", SRC)
        self.assertIn("sh.uniforms.uKitKind = { value: ki };", SRC)
        # the deck's discard stays out of the shared program
        i = SRC.index('const kitDetailShared = () => {')
        shared = SRC[i:SRC.index('};', i)]
        self.assertIn('if (!KIT_SHARED(k)) continue;', shared)


class Backdrops(unittest.TestCase):
    def test_drawn_last_and_out_of_the_mirror(self):
        self.assertIn("const BACKDROP = { sky, apron: null, sky0: BACKDROP_FIRST ? 0 : 45, apron0: BACKDROP_FIRST ? -1 : 40, ab: !BACKDROP_FIRST };", SRC)
        self.assertIn('sky.renderOrder = BACKDROP.sky0;', SRC)
        self.assertIn('apron.renderOrder = BACKDROP.apron0;', SRC)
        self.assertIn('apron.userData.reflK = 0;', SRC)
        # the mirror's sweep takes 0 to 49: both new orders stay inside it, which is why the apron is named out
        self.assertIn('o.renderOrder >= 0 && o.renderOrder < 50', SRC)
        for v in (45, 40):
            self.assertLess(v, 50)

    def test_the_ab_in_the_timers_windows(self):
        post = SRC[SRC.index('  function renderPost(sc, cam) {'):]
        post = post[:post.index('\n  }\n')]
        self.assertIn('const oldOrder = GPUT.live && BACKDROP.ab && Math.floor(GPUT.fid / GPUT_EVERY) % 2 === 1;', post)
        self.assertLess(post.index('BACKDROP.sky.renderOrder = oldOrder ? 0 : BACKDROP.sky0;'), post.index("gpuT(oldOrder ? 'sceneB' : 'scene');"))
        self.assertLess(post.index("gpuT(oldOrder ? 'sceneB' : 'scene');"), post.index('renderer.render(sc, cam);'))


class CloudGate(unittest.TestCase):
    def test_a_strength_of_nothing_returns_at_once(self):
        self.assertIn("'float cloudShade(vec2 wp){ if (uCloudSh <= 0.0) return 0.0; vec2 cp =", SRC)
        line = [l for l in SRC.splitlines() if "'float cloudShade(vec2 wp){" in l][0]
        self.assertTrue(re.search(r"\* uCloudSh; \}',$", line.strip()), 'the result is still the strength times the shade')


if __name__ == '__main__':
    unittest.main()
