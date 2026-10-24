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
- the glint is clamped on a phone, and the new geometry streams are 4-byte aligned floats;
- every river sheet shades alike (no shore term: it drew a seam along the pierhead line where the core's quad meets
  the outer sheets), and the one calmer reach is the Schuylkill's pool above the Fairmount Dam;
- a pier's deck is weathered concrete in the legacy linear palette, not the white slab it drew at 0x5c5a54;
- (the review, Oct 13) a ring is levelled only when it is compact and its own ground is level: a creek ribbon on a slope,
  a pond on a hillside and the NW patch's rings keep the river path, the coping is a fountain's or the outer districts',
  and a bank wall stops at the ground beside it;
- the mirror is cropped to the water's box on the screen, and every water point in the box still lands in its image;
- a park far from the Delaware's outline costs one delawareAt, a phone's water probe is a 128 cube, the wakes allocate
  nothing a frame."""
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


BBOX = """
const bboxOf = (poly) => {
  let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
  for (const q of poly) { if (q[0] < x0) x0 = q[0]; if (q[0] > x1) x1 = q[0]; if (q[1] < z0) z0 = q[1]; if (q[1] > z1) z1 = q[1]; }
  return [x0, x1, z0, z1];
};
"""


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
        self.assertIn('waterPmrem().fromScene(envScene, 0)', bake)
        self.assertIn('m.envMap = rt.texture', bake)
        self.assertNotIn('scene.environment', bake)
        # only the sun's disc and the placeholder boxes are hidden: a cloud or an atmosphere added to the probe scene stays
        self.assertIn("(o === envSun || (o.geometry && o.geometry.type === 'BoxGeometry'))", bake)
        self.assertNotIn('o !== envSky', bake)
        gen = cut_function(s, 'waterPmrem')
        self.assertIn('if (!isTouch) return pmremGen;', gen)   # a computer shares the glass's generator and size
        self.assertIn('this._lodMax = 7; this._cubeSize = 128;', gen)   # a phone's is a 128 cube (Round 158's memory)
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
        for name in ('ringWall', 'soffit', 'raisedFlush', 'pierDeck', 'waterRing', 'bankWall'):
            self.assertNotIn('Uint8Array', cut_function(self.s, name), name)

    def test_wakes_allocate_nothing(self):
        w = cut_function(self.s, 'waterWakes')
        self.assertNotIn('push({', w)
        self.assertIn('wakeTake(', w)

    def test_phone_river_skips_the_shadow(self):
        self.assertIn('if (!isTouch && (frameNo % 300) === 2) waterShadowSweep();', cut_function(self.s, 'waterFrame'))

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
const DEL_POLYS = null;   // no outline: every probe is tested
const siteY = (x) => x > 0 ? -7.34 : 0;   // the river's bed at its level, the bank 7 m over it
""" + BBOX + cut_function(self.s, 'pointInPoly') + '\n' + cut_function(self.s, 'polyCentroid') + '\n' + re.search(r'  const waterAtXZ = .*\n', self.s).group(0) + 'let delCells = null;\n' + cut_function(self.s, 'delOutlineNear') + cut_function(self.s, 'pierWet') + """
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

    def test_pier_prefilter(self):
        # a park whose padded box holds no cell of the outline costs one delawareAt; one by the outline is tested in full
        js = """
const REAL = true;
const TERRAIN = { water: -7.34 };
const ring = [[0, -5000], [3000, -5000], [3000, 5000], [0, 5000]];   // the river: x 0 to 3,000
const DEL_POLYS = [{ ring, holes: [] }];
let calls = 0;
const delawareAt = (x, z) => { calls++; return pointInPoly(x, z, ring); };
const schRaster = null;
const siteY = (x) => x > 0 && x < 3000 ? -7.34 : 0;
""" + BBOX + cut_function(self.s, 'pointInPoly') + '\n' + cut_function(self.s, 'polyCentroid') + '\n' + 'let delCells = null;\n' + cut_function(self.s, 'delOutlineNear') + cut_function(self.s, 'pierWet') + """
const far = [[-2000, 0], [-1800, 0], [-1800, 150], [-2000, 150]];
const r = {};
calls = 0; r.far = pierWet(far, true); r.farCalls = calls;
const pierPark = [[-40, 0], [120, 0], [120, 60], [-40, 60]];   // 120 m out into the river from the bank at x = 0
calls = 0; r.pier = pierWet(pierPark, true); r.pierCalls = calls;
console.log(JSON.stringify(r));
"""
        r = run_node(js)
        self.assertFalse(r['far'])
        self.assertEqual(r['farCalls'], 1)
        self.assertTrue(r['pier'])
        self.assertGreater(r['pierCalls'], 8)

    def test_ring_gate(self):
        # the review, Oct 13: a creek ribbon on a slope was levelled into a walled channel; it and a pond on a hillside keep
        # the river path, and only a fountain or the outer districts' small rings take the coping
        gate = cut_function(self.s, 'waterRingGate')
        consts = re.search(r'  const WR_COMPACT = .*\n', self.s).group(0)
        jets = self.s[self.s.index('  const FOUNTAIN_JETS = ['):self.s.index('  ];', self.s.index('  const FOUNTAIN_JETS = [')) + 5]
        js = """
const TERRAIN = { water: -7.34 };
const schRaster = null;
const delawareAt = () => false;
const P = { x0: -10600, x1: -2600, z0: -15600, z1: -6600 };
const hitsP = (bb) => P && bb[0] < P.x1 && bb[1] > P.x0 && bb[2] < P.z1 && bb[3] > P.z0;
let siteY = (x, z) => 20;   // a level plateau 27 m over the water
const bankGround = (x, z) => siteY(x, z, 'ground');   // the realism round two (R1): off the Schuylkill's bank a ring reads siteY
""" + BBOX + cut_function(self.s, 'pointInPoly') + '\n' + cut_function(self.s, 'polyCentroid') + '\n' + cut_function(self.s, 'signedArea') + '\n' + jets + consts + gate + """
const ribbon = [];   // a creek 12 m wide winding 1.5 km east, its ground falling 30 m along it
for (let i = 0; i <= 60; i++) ribbon.push([5000 + i * 25, 3000 + Math.sin(i / 6) * 80]);
for (let i = 60; i >= 0; i--) ribbon.push([5000 + i * 25, 3012 + Math.sin(i / 6) * 80]);
const sq = (cx, cz, h) => [[cx - h, cz - h], [cx + h, cz - h], [cx + h, cz + h], [cx - h, cz + h]];
const r = {};
const flat = siteY;
r.ribbonFlat = waterRingGate(ribbon, false); r.ribbonFlatWhy = waterRingGate.why;
siteY = (x, z) => 50 - (x - 5000) * 0.02;   // the ribbon's ground falling 30 m
r.ribbon = waterRingGate(ribbon, false); r.ribbonWhy = waterRingGate.why;
r.ribbonWide = waterRingGate(ribbon, true); r.ribbonWideWhy = waterRingGate.why;
r.hillPond = waterRingGate(sq(5000, 3000, 40), false); r.hillPondWhy = waterRingGate.why;   // 80 m across on a 2 per cent slope: 1.6 m
r.hillLake = waterRingGate(sq(5000, 3000, 200), false); r.hillLakeWhy = waterRingGate.why;   // 400 m across: 8 m
siteY = (x, z) => 50 - (x - 5000) * 0.025;   // 200 m across, 5 m: within a lake's relief, but its low shore 4.4 m under the level
r.tank = waterRingGate(sq(5000, 3000, 100), false); r.tankWhy = waterRingGate.why;
siteY = (x, z) => 50 - (x - 5000) * 0.008;   // 1.6 m: a lake, its wall about 1.4 m at the low shore
r.gentle = waterRingGate(sq(5000, 3000, 100), false);
siteY = flat;
r.pond = waterRingGate(sq(5000, 3000, 30), false);
r.wideBasin = waterRingGate(sq(-1000, 2000, 10), true);
r.swann = waterRingGate([[-2190, -1379], [-2205, -1364], [-2220, -1379], [-2205, -1394]], true);
r.dilworth = waterRingGate(sq(-1690, -808, 12), true);
r.lake = waterRingGate(sq(5000, 3000, 150), false);
r.nw = waterRingGate(sq(-5000, -9000, 100), false); r.nwWhy = waterRingGate.why;
r.low = (siteY = () => -7, waterRingGate(sq(5000, 3000, 30), false)); r.lowWhy = waterRingGate.why;
const brief = (g) => g && { coping: g.coping, basin: g.basin, J: !!g.J, flush: !!(g.J && g.J.flush), y: +g.y.toFixed(2) };
for (const k of Object.keys(r)) if (r[k] && typeof r[k] === 'object') r[k] = brief(r[k]);
console.log(JSON.stringify(r));
"""
        r = run_node(js)
        for k in ('ribbonFlat', 'ribbon', 'ribbonWide'):
            self.assertIsNone(r[k], k)
        self.assertEqual(r['ribbonFlatWhy'], 'ribbon')   # a ribbon never levels, even on flat ground
        self.assertEqual(r['ribbonWhy'], 'ribbon')
        self.assertEqual(r['ribbonWideWhy'], 'ribbon')
        self.assertIsNone(r['hillPond'])
        self.assertEqual(r['hillPondWhy'], 'slope')
        self.assertIsNone(r['hillLake'])
        self.assertEqual(r['hillLakeWhy'], 'slope')
        self.assertIsNone(r['tank'])
        self.assertEqual(r['tankWhy'], 'wall')   # a level standing 4.4 m over its low shore is a tank
        self.assertFalse(r['gentle']['coping'])
        self.assertLess(r['gentle']['y'], 50 + 0.8 + 0.35 + 0.01)
        self.assertIsNone(r['nw'])
        self.assertEqual(r['nwWhy'], 'nw')
        self.assertIsNone(r['low'])
        self.assertEqual(r['lowWhy'], 'low')
        self.assertEqual(r['pond'], {'coping': False, 'basin': True, 'J': False, 'flush': False, 'y': 20.35})   # a far-ring pond: no coping
        self.assertTrue(r['wideBasin']['coping'])
        self.assertTrue(r['swann']['J'] and r['swann']['coping'])
        self.assertTrue(r['dilworth']['J'] and r['dilworth']['flush'])
        self.assertEqual(r['lake'], {'coping': False, 'basin': False, 'J': False, 'flush': False, 'y': 20.35})

    def test_bank_wall_stops_at_the_ground(self):
        js = """
const THREE = require('./three.min.js');
const siteY = (x, z) => 30 - x * 0.02;   // falling 4 m across the ring's 200 m
const bankGround = (x, z) => siteY(x, z, 'ground');   // R1: off the Schuylkill's bank, siteY
""" + cut_function(self.s, 'signedArea') + '\n' + cut_function(self.s, 'bankWall') + """
const ring = [[0, 0], [200, 0], [200, 200], [0, 200]], top = 28.5;
const r = { cw: null, ccw: null };
for (const [k, R] of [['ccw', ring], ['cw', ring.slice().reverse()]]) {
  const g = bankWall(R, top), p = g.attributes.position.array, n = g.attributes.normal.array;
  let under = 0, deep = 0, over = 0, out = 0, faces = 0, minX = 1e9;
  for (let i = 0; i < p.length; i += 3) {
    const x = p[i], y = p[i + 1], z = p[i + 2], gy = siteY(x, z);
    if (y > top + 1e-6) over++;
    if (y < top - 1e-6) { if (y < Math.min(top, gy) - 0.5 - 1e-6) deep++; if (y > gy) under++; }
    minX = Math.min(minX, x);
  }
  for (let i = 0; i < p.length; i += 9) {   // every face's winding agrees with its outward normal, and the normal points out
    const ax = p[i + 3] - p[i], ay = p[i + 4] - p[i + 1], az = p[i + 5] - p[i + 2], bx = p[i + 6] - p[i], by = p[i + 7] - p[i + 1], bz = p[i + 8] - p[i + 2];
    const cx = ay * bz - az * by, cz = ax * by - ay * bx, mx = (p[i] + p[i + 3] + p[i + 6]) / 3 - 100, mz = (p[i + 2] + p[i + 5] + p[i + 8]) / 3 - 100;
    if (cx * n[i] + cz * n[i + 2] > 0 && n[i] * mx + n[i + 2] * mz > 0) out++;
    faces++;
  }
  r[k] = { over, deep, under, out, faces, minX };
}
console.log(JSON.stringify(r));
"""
        r = run_node(js)
        for k in ('ccw', 'cw'):
            w = r[k]
            self.assertEqual(w['over'], 0, k)
            self.assertEqual(w['deep'], 0, k)   # never deeper than half a metre under the ground beside it
            self.assertEqual(w['under'], 0, k)   # its foot is in the ground, not hanging over it
            self.assertEqual(w['out'], w['faces'], k)
            self.assertGreater(w['faces'], 20, k)
            # the west side (ground 30, over the top) has no wall; the east side (26 m) has one
            self.assertGreater(w['minX'], 20, k)

    def test_mirrored_eye(self):
        refl = cut_function(self.s, 'reflRender')
        body = refl[refl.index('    const C = REFL.cam;'):refl.index('    C.projectionMatrixInverse.copy(C.projectionMatrix).invert();')]
        js = """
const THREE = require('./three.min.js');
const W0 = -7.34, REFL_FAR = 3500, ZREV = { on: false };   // ZREV: Round 192's reversed Z, off here
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

    def test_mirror_water_raster(self):
        # the crop's water: every cell whose middle is in the Delaware's outline is marked (the scan line fill and the
        # edges' cells), and the raster is cheap to build
        fn = cut_function(self.s, 'reflWaterBuild')
        js = """
const DEL_POLYS = JSON.parse(require('fs').readFileSync('delaware.json', 'utf8')).polys, REFL_CELL = 100;
const RING_W = { x0: -12000, x1: 16500, z0: -21700, z1: 9700 };
const schRaster = (x, z) => x > -3000 && x < -2900 && z > -2000 && z < 0;   // a strip of the Schuylkill
""" + cut_function(self.s, 'pointInPoly') + '\n' + fn + """
const t = Date.now(), W = reflWaterBuild(), ms = Date.now() - t;
let wet = 0, miss = 0;
for (let j = 0; j < W.nz; j += 2) for (let i = 0; i < W.nx; i += 2) {
  const x = W.x0 + (i + 0.5) * 100, z = W.z0 + (j + 0.5) * 100;
  if (DEL_POLYS.some((pg) => pointInPoly(x, z, pg.ring) && !(pg.holes || []).some((h) => pointInPoly(x, z, h)))) { wet++; if (!W.m[j * W.nx + i]) miss++; }
}
const at = (x, z) => W.m[Math.floor((z - W.z0) / 100) * W.nx + Math.floor((x - W.x0) / 100)];
console.log(JSON.stringify({ ms, wet, miss, sch: at(-2950, -1000), grown: at(-2750, -1000), dry: at(-6000, -1000), cityHall: at(-1603, -802) }));
"""
        r = run_node(js)
        self.assertGreater(r['wet'], 500)
        self.assertEqual(r['miss'], 0)
        self.assertEqual(r['sch'], 1)
        self.assertEqual(r['grown'], 1)   # grown 200 m for the slips and the shore
        self.assertEqual(r['dry'], 0)
        self.assertEqual(r['cityHall'], 0)
        self.assertLess(r['ms'], 1500)

    def test_mirror_reach_is_enforced(self):
        # the oblique near plane leaves the projection no far plane: the reach is reflReach's, around the pass alone
        refl = cut_function(self.s, 'reflRender')
        self.assertIn('reflReach(C.position, REFL.far || REFL_FAR)', refl)
        self.assertLess(refl.index('reflReach(C.position'), refl.index('r.render(sc, C);'))
        self.assertIn('for (const o of REFL.cut) o.layers.enable(REFL.layer);', refl[refl.index('} finally {'):])
        reach = cut_function(self.s, 'reflReach')
        self.assertIn('_rrS.center.distanceTo(eye) - _rrS.radius > reach', reach)
        self.assertIn('list.push(o)', cut_function(self.s, 'reflSweep'))

    def test_mirror_crop(self):
        # the crop (the review: the mirror drew 80 to 85 per cent of the scene pass): the water's box on the eye's screen,
        # mirrored in x (the mirrored eye's right is the eye's left), fills the image, and every water point still lands in it
        refl = cut_function(self.s, 'reflRender')
        body = refl[refl.index('    const C = REFL.cam;'):refl.index('    C.projectionMatrixInverse.copy(C.projectionMatrix).invert();')]
        head = """
const THREE = require('./three.min.js');
const W0 = -7.34, REFL_FAR = 3500, ZREV = { on: false };   // ZREV: Round 192's reversed Z, off here
const REFL = { cam: new THREE.PerspectiveCamera(), box: null };
const waterU = { uReflMat: { value: new THREE.Matrix4() } };
const _rfA = new THREE.Vector3(), _rfN = new THREE.Vector3(0, 1, 0), _rfP = new THREE.Plane(), _rfV = new THREE.Vector4(), _rfQ = new THREE.Vector4();
const cam = new THREE.PerspectiveCamera(60, 1.6, 1, 26000);
cam.position.set(-2000, W0 + 300, -300); cam.lookAt(800, W0, -900); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
// the river: a band from x 400 to 1,300 (the eye 2.4 km west of it, 300 m up: a strip across the screen)
const pts = [], v = new THREE.Vector3();
for (let x = 400; x <= 1300; x += 25) for (let z = -3000; z <= 2000; z += 25) {
  if (Math.hypot(x - cam.position.x, z - cam.position.z) > REFL_FAR) continue;
  v.set(x, W0, z).project(cam);
  if (v.z < 1 && Math.abs(v.x) <= 1 && Math.abs(v.y) <= 1) pts.push([x, z, v.x, v.y]);
}
let x0 = 9, x1 = -9, y0 = 9, y1 = -9;
for (const q of pts) { x0 = Math.min(x0, q[2]); x1 = Math.max(x1, q[2]); y0 = Math.min(y0, q[3]); y1 = Math.max(y1, q[3]); }
function run() {
"""
        tail = """
}
const P = new THREE.Vector4();
const uvs = () => pts.map((q) => { P.set(q[0], W0, q[1], 1).applyMatrix4(waterU.uReflMat.value); return [P.x / P.w, P.y / P.w]; });
const span = (a) => { let u0 = 9, u1 = -9, v0 = 9, v1 = -9; for (const [u, w] of a) { u0 = Math.min(u0, u); u1 = Math.max(u1, u); v0 = Math.min(v0, w); v1 = Math.max(v1, w); } return [u0, u1, v0, v1]; };
run(); const full = span(uvs());
REFL.box = [-x1 - 0.02, -x0 + 0.02, y0 - 0.02, y1 + 0.02]; run(); const crop = span(uvs()); const cxy = [REFL.cx, REFL.cy];
REFL.box = [x0 - 0.02, x1 + 0.02, y0 - 0.02, y1 + 0.02]; run(); const wrong = span(uvs());
console.log(JSON.stringify({ n: pts.length, box: [x0, x1, y0, y1], full, crop, cxy, wrong }));
"""
        r = run_node(head + body + tail)
        self.assertGreater(r['n'], 200)
        self.assertLess(r['box'][3] - r['box'][2], 0.8)   # the river is a strip across the screen
        u0, u1, v0, v1 = r['crop']
        self.assertGreaterEqual(u0, 0.0)
        self.assertLessEqual(u1, 1.0)
        self.assertGreaterEqual(v0, 0.0)
        self.assertLessEqual(v1, 1.0)
        bh, bw = r['box'][3] - r['box'][2], r['box'][1] - r['box'][0]
        self.assertAlmostEqual(v1 - v0, bh / (bh + 0.04), delta=0.01)   # the strip fills the image's height but its margins
        self.assertAlmostEqual(u1 - u0, bw / (bw + 0.04), delta=0.01)
        self.assertGreater(r['cxy'][1], 2.0)
        fv0, fv1 = r['full'][2:]
        self.assertLess(fv1 - fv0, 0.5)
        # unmirrored, the same box misses the water (the sign is load-bearing)
        wu0, wu1 = r['wrong'][:2]
        self.assertTrue(wu0 < -0.05 or wu1 > 1.05, r['wrong'])



def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


class Surface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        cls.real = cut_function(cls.s, 'liquifyReal')

    def test_every_sheet_shades_alike(self):
        # the core's Delaware quad has no shore alpha and the outer sheets do: any term on it is a seam
        self.assertNotIn('wsh', self.real)
        self.assertNotIn('USE_COLOR_ALPHA', self.real)
        old = cut_function(self.s, 'liquify')
        self.assertIn('float wsh = vColor.a;', old)   # ?real=0 keeps Round 54's shallows

    def test_the_pool_above_the_dam(self):
        m = re.search(r'float wPool = (.*);\n', self.real)
        self.assertIsNotNone(m)
        expr = m.group(1).replace('vWq.x', 'x').replace('vWq.z', 'z')
        pool = lambda x, z: eval(expr, {'smoothstep': smoothstep, 'x': x, 'z': z})
        for x, z in [(-3520, -2626), (-3796, -2682), (-3600, -2420), (-4224, -4437), (-6500, -6800)]:   # Boathouse Row, the pool, East Park
            self.assertGreater(pool(x, z), 0.99, (x, z))
        for x, z in [(-3300, -2200), (-3500, -2250), (-3000, -500), (-3500, 3000), (600, -800), (6000, -9000), (-2500, 6500)]:   # the tailwater, the tidal Schuylkill, the Delaware
            self.assertLess(pool(x, z), 0.01, (x, z))
        self.assertIn('* (1.0 - 0.7 * wPool);', self.real)
        self.assertIn('uCoxMunk * 0.45 * (1.0 - 0.7 * wPool)', self.real)

    def test_pier_albedos(self):
        m = re.search(r'const PIER_DECK = 0x([0-9a-f]{6}), PIER_FASCIA = 0x([0-9a-f]{6}), PILE_COL = 0x([0-9a-f]{6})', self.s)
        self.assertIsNotNone(m)
        deck, fascia, pile = [[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in m.groups()]
        self.assertLessEqual(max(deck), 0x30)   # 0x5c5a54 drew 220 of 255 in the sun
        self.assertGreaterEqual(min(deck), 0x18)
        self.assertLess(max(fascia), min(deck))
        self.assertLess(max(pile), min(deck))

    def test_delaware_body_is_not_khaki(self):
        m = re.search(r'const WATER_BODY = \{ del: 0x([0-9a-f]{6})', self.s)
        r, g, b = [int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)]
        self.assertGreaterEqual(b, r)
        self.assertGreater(g, r)


if __name__ == '__main__':
    unittest.main()
