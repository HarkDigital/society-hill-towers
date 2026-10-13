"""The realism pass's water (Oct 12, Mike: "please do anything necessary to make this look more photo realistic and less
cartoony. This should apply to all surfaces/water/anything").

- the old water is REAL-gated: ?real=0 runs Round 54's shader untouched, REAL runs liquifyReal;
- the water's sky probe is its own envMap from the same generator, re-baked at the end of refreshEnv, never a sampler on
  scene.environment (another probe may resize it and change the CUBEUV defines);
- the planar mirror is a desktop post-pipeline pass of its own: drawn before the scene pass, its counts apart from POST's,
  the shadow map's flags restored, and nothing it draws is a pin, a flat, the water or pinDepthClear (and so the AO copy);
- the mirrored eye is right: every water point the eye sees lands inside the mirror's image, a point over the water is
  kept and one under it is clipped by the oblique near plane;
- the wave slopes are a zero-mean, unit-rms field, longer along the wind, whose third channel holds the squared slope;
- a pier is found by the water round it, a riverside park is not;
- the glint is clamped on a phone, and the new geometry streams are 4-byte aligned floats."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut_function(src, name):
    i = src.index('  function %s(' % name)
    j = src.index('{', i)
    depth = 0
    for k in range(j, len(src)):
        c = src[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
    raise ValueError(name)


def run_node(js):
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=120, cwd=str(ROOT))
    if out.returncode != 0:
        raise AssertionError(out.stderr[-2000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_old_water_kept_behind_real(self):
        s = self.s
        self.assertIn("if (REAL) { liquifyReal(mat, scale, amp, speed, opt || {}); return; }", s)
        self.assertIn("mat.customProgramCacheKey = () => 'water|' + [scale, amp, speed, isTouch].join('|');", s)
        self.assertIn("if (REAL) COLORS.water = WATER_BODY.del;", s)
        self.assertIn("    water: 0x102b2e,", s)   # the old palette entry itself stands for ?real=0

    def test_sky_probe_is_the_waters_own(self):
        s = self.s
        env = cut_function(s, 'refreshEnv')
        self.assertTrue(env.rstrip('}').rstrip().endswith("waterEnvBake();   // realism, water: the water's own sky-only probe from the same generator (living water)"))
        bake = cut_function(s, 'waterEnvBake')
        self.assertIn('pmremGen.fromScene(envScene, 0)', bake)
        self.assertIn('m.envMap = rt.texture', bake)
        self.assertNotIn('scene.environment', bake)
        real = cut_function(s, 'liquifyReal')
        self.assertIn('mat.envMap = waterEnvBake.rt.texture', real)
        self.assertIn('textureCubeUV(envMap, wr, wRough)', real)
        self.assertNotIn('scene.environment', real)

    def test_mirror_is_its_own_pass(self):
        s = self.s
        post = cut_function(s, 'renderPost')
        r, scene_pass, counts = post.index('reflRender(sc, cam);'), post.index('renderer.render(sc, cam);'), post.index('POST.calls = renderer.info.render.calls')
        self.assertLess(r, scene_pass)
        self.assertLess(scene_pass, counts)
        refl = cut_function(s, 'reflRender')
        self.assertIn('REFL.calls = r.info.render.calls; REFL.tris = r.info.render.triangles;', refl)
        self.assertIn('r.shadowMap.autoUpdate = false; r.shadowMap.needsUpdate = false;', refl)
        self.assertIn('r.shadowMap.autoUpdate = prevUp; r.shadowMap.needsUpdate = prevNeed;', refl)
        self.assertIn('C.layers.set(REFL.layer);', refl)
        # the texture matrix is taken before the oblique plane rewrites the projection's z row
        self.assertLess(refl.index('waterU.uReflMat.value.set('), refl.index('e[2] = _rfV.x;'))
        self.assertIn("const REFL = { on: REAL && POST.on && !/[?&]refl=0\\b/.test(location.search)", s)

    def test_mirror_draws_no_pin_flat_or_water(self):
        sweep = cut_function(self.s, 'reflSweep')
        for k in ('o.userData.occFlat', 'o.userData.pinSceneDepth', 'o.renderOrder < 50', 'm.userData.water', 'm.userData.wxSurf', 'o !== sky', 'o !== cloudDeck', 'o !== grassMesh'):
            self.assertIn(k, sweep)
        # pinDepthClear (whose hook copies the AO's depth) is at renderOrder 99: never on the mirror's layer
        self.assertIn('pinDepthClear.renderOrder = 99;', self.s)

    def test_phone_glint_clamped_and_planar_desktop_only(self):
        real = cut_function(self.s, 'liquifyReal')
        self.assertIn("#define W_GLINT_MAX ' + (phone ? '3.0' : '40.0')", real)
        self.assertIn("refl = !!opt.refl && REFL.on", real)
        self.assertIn('vec3(W_GLINT_MAX)', real)

    def test_new_streams_are_aligned_floats(self):
        jets = cut_function(self.s, 'jetGeometry')
        self.assertIn("new THREE.BufferAttribute(new Float32Array(aj), 4)", jets)
        self.assertNotIn('Uint8Array', jets)
        for name in ('ringWall', 'soffit', 'raisedFlush', 'pierDeck', 'waterRing'):
            self.assertNotIn('Uint8Array', cut_function(self.s, name), name)

    def test_shared_hooks_are_single_lines(self):
        s = self.s
        self.assertEqual(s.count('waterFrame();   // realism, water'), 1)
        self.assertEqual(s.count('reflRender(sc, cam);   // realism, water'), 1)
        self.assertEqual(s.count('waterEnvBake();   // realism, water'), 1)

    def test_art(self):
        man = json.loads((ROOT / 'water_art.json').read_text())
        for k in ('pierdeck', 'pierdeckHalf', 'foam', 'foamHalf'):
            self.assertTrue((ROOT / man[k]).exists(), k)
            self.assertRegex(man[k], r'^art/water/[a-z-]+\.[0-9a-f]{10}\.webp$')
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("WATER_ART", text_of("water_art.json", "null"))', b)
        self.assertIn('"water_art.json"', b)
        self.assertIn('artImage(artSrc(WATER_ART_M.pierdeck, WATER_ART_M.pierdeckHalf))', self.s)

    def test_dam_takes_the_waters_clock(self):
        ww = (ROOT / 'rebuilds' / 'ww.js').read_text()
        self.assertIn('const TIME = api.time || { value: 0 };', ww)
        self.assertIn('const FOAM = api.foam || null;', ww)
        self.assertIn('if (app && FOAM) {', ww)   # ?real=0 and the design harness keep the one foam quad
        self.assertIn("time: waterU.uTime, foam: REAL ?", self.s)


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Node(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_wave_slopes(self):
        fn = cut_function(self.s, 'makeWaveSlopes')
        js = """
const isTouch = false;
const renderer = { capabilities: { getMaxAnisotropy: () => 16 } };
const THREE = { DataTexture: function (d, w, h) { this.image = { data: d, width: w, height: h }; }, RGBAFormat: 1023, RepeatWrapping: 1000, LinearMipmapLinearFilter: 1008, LinearFilter: 1006 };
""" + fn + """
const t0 = Date.now();
const a = makeWaveSlopes(256, 32, 0x51ed270b), b = makeWaveSlopes(256, 32, 0x51ed270b);
const ms = Date.now() - t0, d = a.image.data, n = d.length / 4;
let mr = 0, mg = 0, mb = 0, vr = 0, vg = 0, same = true;
for (let i = 0; i < n; i++) { mr += d[i * 4]; mg += d[i * 4 + 1]; mb += d[i * 4 + 2]; }
mr /= n; mg /= n; mb /= n;
for (let i = 0; i < n; i++) { vr += (d[i * 4] - mr) ** 2; vg += (d[i * 4 + 1] - mg) ** 2; }
for (let i = 0; i < d.length; i++) if (d[i] !== b.image.data[i]) { same = false; break; }
console.log(JSON.stringify({ ms, mr, mg, mb, vr: vr / n, vg: vg / n, same, mips: a.generateMipmaps, wrap: a.wrapS, aniso: a.anisotropy }));
"""
        r = run_node(js)
        self.assertTrue(r['same'])
        self.assertLess(abs(r['mr'] - 127.5), 2.0)
        self.assertLess(abs(r['mg'] - 127.5), 2.0)
        self.assertLess(abs(r['mb'] - 255 / 16), 1.5)                    # E|u|^2 / 16 with a unit rms
        self.assertGreater(r['vr'], r['vg'] * 1.3)                       # longer crests across the wind: more slope along it
        self.assertAlmostEqual((r['vr'] + r['vg']) / (255 / 4) ** 2, 1.0, delta=0.08)
        self.assertTrue(r['mips'])
        self.assertEqual(r['wrap'], 1000)
        self.assertEqual(r['aniso'], 16)
        self.assertLess(r['ms'], 3000)

    def test_pier_test(self):
        js = """
const REAL = true;
const TERRAIN = { water: -7.34 };
let delawareAt = (x, z) => x > 0;   // the river east of x = 0
const schRaster = null;
const siteY = (x) => x > 0 ? -7.34 : 0;   // the river's bed at its level, the bank 7 m over it
""" + cut_function(self.s, 'pointInPoly') + '\n' + cut_function(self.s, 'polyCentroid') + '\n' + re.search(r'  const waterAtXZ = .*\n', self.s).group(0) + cut_function(self.s, 'pierWet') + """
const pier = [[-5, 0], [60, 0], [60, 15], [-5, 15]];
const park = [[-100, 0], [-1, 0], [-1, 80], [-100, 80]];
// a pier between slips: the river's outline runs along the pierhead line at x = 100, the slips are low ground
const slipPier = [[0, 0], [90, 0], [90, 15], [0, 15]];
const r1 = { pier: pierWet(pier), pierDel: pierWet(pier, true), park: pierWet(park), parkDel: pierWet(park, true) };
delawareAt = (x, z) => x > 100;
r1.slip = pierWet(slipPier); r1.slipDel = pierWet(slipPier, true);
console.log(JSON.stringify(r1));
"""
        r = run_node(js)
        self.assertEqual(r, {'pier': True, 'pierDel': True, 'park': False, 'parkDel': False, 'slip': True, 'slipDel': False})

    def test_mirrored_eye(self):
        refl = cut_function(self.s, 'reflRender')
        body = refl[refl.index('    const C = REFL.cam;'):refl.index('    C.projectionMatrixInverse.copy(C.projectionMatrix).invert();')]
        js = """
const THREE = require('./three.min.js');
const W0 = -7.34, REFL_FAR = 3500;
const REFL = { cam: new THREE.PerspectiveCamera() };
const waterU = { uReflMat: { value: new THREE.Matrix4() } };
const _rfA = new THREE.Vector3(), _rfN = new THREE.Vector3(0, 1, 0), _rfP = new THREE.Plane(), _rfV = new THREE.Vector4(), _rfQ = new THREE.Vector4();
const cam = new THREE.PerspectiveCamera(60, 1.6, 1, 26000);
cam.position.set(100, W0 + 12, -40); cam.lookAt(900, W0 - 30, -300); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
""" + body + """
let inside = 0, tried = 0, kept = 0, clipped = 0;
const v = new THREE.Vector3(), P = new THREE.Vector4();
for (let j = 0; j < 12; j++) for (let i = 0; i < 16; i++) {
  v.set((i + 0.5) / 8 - 1, (j + 0.5) / 6 - 1, 0.5).unproject(cam).sub(cam.position).normalize();
  if (v.y > -0.01) continue;
  const t = (W0 - cam.position.y) / v.y, x = cam.position.x + v.x * t, z = cam.position.z + v.z * t;
  if (t > 3000) continue;
  tried++;
  P.set(x, W0, z, 1).applyMatrix4(waterU.uReflMat.value);
  const u = P.x / P.w, w = P.y / P.w;
  if (P.w > 0 && u > -0.001 && u < 1.001 && w > -0.001 && w < 1.001) inside++;
  // the oblique plane: 2 m over the water at that point is kept, 2 m under it (between the mirrored eye and the water) is cut
  const up = new THREE.Vector4(x, W0 + 2, z, 1).applyMatrix4(REFL.cam.matrixWorldInverse).applyMatrix4(REFL.cam.projectionMatrix);
  const dn = new THREE.Vector4(x, W0 - 2, z, 1).applyMatrix4(REFL.cam.matrixWorldInverse).applyMatrix4(REFL.cam.projectionMatrix);
  if (up.z >= -up.w) kept++;
  if (dn.z < -dn.w) clipped++;
}
console.log(JSON.stringify({ tried, inside, kept, clipped, far: REFL.cam.far }));
"""
        r = run_node(js)
        self.assertGreater(r['tried'], 40)
        self.assertEqual(r['inside'], r['tried'])
        self.assertEqual(r['kept'], r['tried'])
        self.assertEqual(r['clipped'], r['tried'])
        self.assertEqual(r['far'], 3500)


if __name__ == '__main__':
    unittest.main()
