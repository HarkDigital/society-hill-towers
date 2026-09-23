"""Round 140: the street lamps light the ground and the lower storeys (Mike: "The lamp posts are not putting out
enough light at night", the stadium lots' "larger light circles" should be "more diffused", and "a lot of
flickering" over the Navy Yard, which was Round 130's pool discs losing the depth test to the lots under them).

Every pole and lot mast is splatted into a light map drawn by an orthographic camera looking straight down; the
surfaces sample it by world position. These checks run the page's own camera setup under Node with the vendored
three.min.js and prove the render target's texel for a world point is the one the surface shader reads, then
check the wiring: the pool discs are gone, surfTexPatch and the facade hook both carry the patch, and the map is
drawn only while the lamps are on."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LampLight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_map_orientation_matches_the_shader(self):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        script = r'''
const THREE = require(THREE_PATH);
const S = 12000, cx = -1500, cz = 3000;
const cam = new THREE.OrthographicCamera(-S / 2, S / 2, S / 2, -S / 2, 1, 4000);
cam.up.set(0, 0, -1); cam.position.set(cx, 2000, cz); cam.lookAt(cx, 0, cz); cam.updateMatrixWorld();
const out = [];
for (const [x, z] of [[cx, cz], [cx + 2500, cz], [cx, cz + 2500], [cx - 4000, cz - 1000], [cx + 5900, cz - 5900]]) {
  const p = new THREE.Vector3(x, 0, z).project(cam);
  const rt = [(p.x + 1) / 2, (p.y + 1) / 2];                          // the render target's uv (v = 0 at the bottom row)
  const sh = [(x - (cx - S / 2)) / S, 1 - (z - (cz - S / 2)) / S];    // the surface shader's luv
  out.push(Math.max(Math.abs(rt[0] - sh[0]), Math.abs(rt[1] - sh[1])));
}
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js')))
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        for err in json.loads(r.stdout):
            self.assertLess(err, 1e-6)
        # and the page sets its camera exactly so, and the shader reads exactly that formula
        self.assertIn('LAMPMAP.cam.up.set(0, 0, -1);', self.src)
        self.assertIn('LAMPMAP.cam.position.set(cx, 2000, cz); LAMPMAP.cam.lookAt(cx, 0, cz);', self.src)
        self.assertIn("vec2 luv = vec2((lwp.x - uLampBox.x) * uLampBox.z, 1.0 - (lwp.z - uLampBox.y) * uLampBox.z);", self.src)
        self.assertIn('lampMapU.uLampBox.value.set(cx - S / 2, cz - S / 2, 1 / S, LAMP_GAIN / LAMPMAP.store);', self.src)

    def test_wiring(self):
        s = self.src
        self.assertNotIn('lotPools', s)                         # Round 130's discs, which fought the lots for depth
        self.assertIn("lampLightPatch(shader, 'cameraPosition - vViewPosition * mat3(viewMatrix)');   // Round 140", s)
        self.assertIn("lampLightPatch(shader, 'vWPos', 'wall');", s)
        self.assertIn("lampLightPatch(sh, 'cameraPosition - vViewPosition * mat3(viewMatrix)', 'blade');", s)   # the grass tufts
        self.assertIn('lampMapU.uLampOn.value = show ? night : 0;\n    if (show) lampMapUpdate();', s)
        # the lamps only light walls on their first storeys, never roofs; the ground path only faces turned up
        self.assertIn("(1.0 - smoothstep(0.35, 0.7, abs(vWNorm.y))) * (1.0 - smoothstep(2.5, 11.0, lwp.y - vBase))", s)
        self.assertIn("smoothstep(0.35, 0.7, inverseTransformDirection(normal, viewMatrix).y)", s)
        # review: the edge fades on a circle round the unsnapped look-ahead point, inside the snapped map
        self.assertIn('lampMapU.uLampFade.value.set(ax, az, S / 2 - step, S * 0.15);', s)
        upd = s[s.index('  function lampMapUpdate() {'):s.index('  const _lmDir')]
        self.assertLess(upd.index('lampMapU.uLampFade.value.set('), upd.index('if (LAMPMAP.rt && cx === LAMPMAP.cx && cz === LAMPMAP.cz) return;'))   # every frame, not only on a re-render
        # review: bounded, a bright albedo taken at most at 0.35 and anything over 0.5 rolled off under the bloom threshold
        self.assertIn('vec3 la = min(diffuseColor.rgb, vec3(0.35))', s)
        self.assertIn('totalEmissiveRadiance += min(la, vec3(0.5)) + lo / (1.0 + lo * 2.0);', s)
        # the splat's soft pool: brightest under the lamp, nothing past its radius; since Round 144 flatter, lower and 1.4 times wider
        self.assertIn('float f = 0.8 * exp(-d * d * 1.9) * (1.0 - d * d);', s)
        self.assertIn('lr[m] = mast ? 56 : clamp(HM[i] * 3.4, 14, 42);', s)
        # Round 144: no pole stands in a deck; the elevated decks carry their own standards, arms over the lanes
        self.assertIn("if (deckOver(x, z, gy)) { pos[i * 3 + 1] = -1000; underDeck++; continue; }", s)
        self.assertIn("if (y - gy < 4.5 || wwbNear(x, z, 40) || bfbNear(x, z, 40)) continue;", s)
        self.assertIn("Math.atan2(nz * sg, -nx * sg)", s)
        self.assertIn("Number.isNaN(poleInv.ROT[i]) ? hash01(i * 1.7 + 0.3) * Math.PI * 2 : poleInv.ROT[i]", s)
        # the paved kinds that overlap each other never share a lift (Round 144's rail yard flicker)
        self.assertIn('const PAVED_UP = { 1: 0.055, 2: 0.025, 3: 0.04, 4: 0.04 };', s)


if __name__ == '__main__':
    unittest.main()
