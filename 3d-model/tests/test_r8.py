"""The realism round two, R8 and C4 (a). R8: a phone's river mirrors the city through the city's probe a phone already
bakes (CITYENV, one centre at 128, the water's own probe's size), bound on the river's program as a second probe, tiers 0
and 1 only, ?rivercity=0 off. C4 (a): the near shadow map's two biases follow its texel (aimSun's box), the depth bias
scaled by the receiver's slope to the sun (p3dBiasK in r149's light loop, the near map's lookup only), ?shadowbias=0 keeps
the fixed pair. The light-loop patch and the bias numbers run under node on the vendored three."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


def section(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


def node(script):
    run = subprocess.run(['node'], input=script, capture_output=True, text=True, timeout=60)
    if run.returncode:
        raise AssertionError(run.stderr)
    return json.loads(run.stdout)


class RiverCity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_flag_and_tiers(self):
        s = self.s
        # a phone under the realism pass, never tier 2 (it bakes no city probe and keeps the sky), ?rivercity=0 off
        self.assertIn("const RCITY = { want: REAL && isTouch && !TIER2 && !/[?&]rivercity=0\\b/.test(location.search), on: false, dbg: false, r: 700 };", s)
        self.assertIn('RCITY.on = RCITY.want && CITYENV.on;', s)
        self.assertNotIn('rcr=', s)   # no experiment's switch left behind

    def test_the_river_binds_the_city_probe(self):
        s = self.s
        lq = section(s, '  function liquifyReal(mat, scale, amp, speed, opt) {', '  function reflSweep() {')
        # rivers only (no basin or pool), never beside the planar mirror (a computer's)
        self.assertIn("const city = () => kind === 'river' && !refl && RCITY.on;", lq)
        self.assertIn("if (wc) { sh.uniforms.uWCity = waterU.uWCity; sh.uniforms.uWCityOn = waterU.uWCityOn; sh.uniforms.uCityEnvC = CITYENV.u.uCityEnvC; sh.uniforms.uCityEnvK = CITYENV.u.uCityEnvK; }", lq)
        self.assertIn("+ (city() ? '|city' : '');", lq)
        self.assertIn('#if defined( W_CITY ) && defined( USE_ENVMAP ) && defined( ENVMAP_TYPE_CUBE_UV )', lq)
        self.assertEqual(lq.count('textureCubeUV(uWCity,'), 1)   # the sphere's far side along the ray
        self.assertEqual(lq.count('textureCubeUV(envMap,'), 2)   # the water's own sky: the ray's, and taken away again at the carried ray
        # what the city adds over the water's own sky, so the reflected sky is unchanged wherever the probe shows sky
        self.assertIn('wEnv = max(wEnv + kC * (cCity - kS * cSky - (1.0 - kS) * wEnv), vec3(0.0));', lq)
        self.assertIn("'#define W_CITY\\n#define W_CITY_R ' + RCITY.r.toFixed(1)", lq)
        # the one-centre limit: the city's share fades from 3.5 to 6 km from the centre
        self.assertIn('(1.0 - smoothstep(3500.0, 6000.0, length(cp.xz)))', lq)
        # re-pointed every frame after the bake (a bake disposes the target it replaces), read once a real bake has landed
        wf = section(s, '  function waterFrame() {', '  function waterShadowSweep() {')
        self.assertIn('if (RCITY.on) { const rt = CITYENV.rts[0]; waterU.uWCity.value = rt ? rt.texture : null; waterU.uWCityOn.value = rt && CITYENV.renders > 0 ? 1 : 0; }', wf)
        self.assertLess(s.index('    if (CITYENV.built) cityEnvTick();'), s.index('    waterFrame();   // realism, water'))

    def test_one_probe_size(self):
        # a phone's city probe and its water probe come from one generator at 128, so one set of cube defines reads both
        s = self.s
        self.assertIn('return isTouch ? waterPmrem() : pmremGen;', s)
        self.assertIn("S.gen._setSize = function () { this._lodMax = 7; this._cubeSize = 128; };", s)


class ShadowBias(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_flag(self):
        s = self.s
        self.assertIn("const SHBIAS = { on: REAL && !/[?&]shadowbias=0\\b/.test(location.search), d: 1.0, n: 1.5, fail: '', dbg: false };", s)
        # the fixed pair stays the boot values (and ?shadowbias=0's, ?real=0's); the box's own text is untouched
        self.assertIn('  sun.shadow.bias = -0.0004;\n  sun.shadow.normalBias = 1.4;', s)
        self.assertNotIn('SHBIAS', section(s, '  const shadowAim = {', '  aimSun(-1450, -700, 800);'))
        self.assertIn('if (SHBIAS.on) { const aim0 = aimSun; aimSun = function (cx, cz, extent) { aim0(cx, cz, extent); shBiasSet(); }; shBiasSet(); }', s)
        # the far map's own pair is untouched
        self.assertIn('L.shadow.bias = -1.6 / (c.far - c.near);', s)
        self.assertIn('L.shadow.normalBias = Math.max(2.5, 1.4 * texel);', s)

    @unittest.skipUnless(shutil.which('node'), 'node unavailable')
    def test_the_pair_by_the_texel(self):
        body = section(self.s, '  function shBiasSet() {', '  if (SHBIAS.on) { const aim0')
        script = '''const SHBIAS = { on: true, d: 1.0, n: 1.5, fail: '', dbg: true }; const window = {};
const sun = { shadow: { bias: 0, normalBias: 0, camera: { near: 100, far: 2600, right: 300 } } };
let SHADOW_RES = 4096;
%s
const at = (res, ext) => { SHADOW_RES = res; sun.shadow.camera.right = ext; shBiasSet(); return [+(-sun.shadow.bias * 2500).toFixed(3), +sun.shadow.normalBias.toFixed(3)]; };
console.log(JSON.stringify({ desk300: at(4096, 300), desk900: at(4096, 900), phone300: at(2048, 300), phone600: at(2048, 600), lite900: at(1024, 900) }));''' % body
        r = node(script)
        self.assertEqual(r['desk300'], [0.146, 0.22])    # a computer's street box: a fifth of a metre where 1 m and 1.4 m stood
        self.assertEqual(r['desk900'], [0.439, 0.659])
        self.assertEqual(r['phone300'], [0.293, 0.439])
        self.assertEqual(r['phone600'], [0.586, 0.879])
        self.assertEqual(r['lite900'], [1.758, 2.637])   # LITE's coarsest map keeps more than the old fixed pair

    @unittest.skipUnless(shutil.which('node'), 'node unavailable')
    def test_the_light_loop(self):
        s = self.s
        far = section(s, '    const C = THREE.ShaderChunk, lf = C.lights_fragment_begin;', '      const L = new THREE.DirectionalLight(0x000000, 0);')
        mine = section(s, '  if (SHBIAS.on) {\n    const C = THREE.ShaderChunk', '  const _farV = new V3();')
        script = '''const THREE = require(%s); const SHBIAS = { on: true, fail: '' }; const FARSH = { fail: '' };
const stock = { lf: THREE.ShaderChunk.lights_fragment_begin, sp: THREE.ShaderChunk.shadowmap_pars_fragment };
const unroll = (src) => src.replace(/#pragma unroll_loop_start\\s+for\\s*\\(\\s*int\\s+i\\s*=\\s*(\\d+)\\s*;\\s*i\\s*<\\s*(\\d+)\\s*;\\s*i\\s*\\+\\+\\s*\\)\\s*{([\\s\\S]+?)}\\s+#pragma unroll_loop_end/g,
  (m, a, b, snip) => { let o = ''; for (let i = +a; i < +b; i++) o += snip.replace(/\\[\\s*i\\s*\\]/g, '[ ' + i + ' ]').replace(/UNROLLED_LOOP_INDEX/g, i); return o; });
const nums = (src, n) => src.replace(/NUM_DIR_LIGHTS/g, n).replace(/NUM_DIR_LIGHT_SHADOWS/g, n).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g, 0).replace(/NUM_SPOT_LIGHT_MAPS/g, 0).replace(/NUM_SPOT_LIGHT_SHADOWS/g, 0).replace(/NUM_SPOT_LIGHT_COORDS/g, 0).replace(/NUM_SPOT_LIGHTS/g, 0).replace(/NUM_RECT_AREA_LIGHTS/g, 0).replace(/NUM_POINT_LIGHT_SHADOWS/g, 0).replace(/NUM_POINT_LIGHTS/g, 0).replace(/NUM_HEMI_LIGHTS/g, 1);
const bal = (src) => { let d = 0; for (const l of src.split('\\n')) { const t = l.trim(); if (/^#if/.test(t)) d++; if (/^#endif/.test(t)) d--; if (d < 0) return false; } return d === 0; };
const out = {};
// a phone (no far map): the stock loop
{ %s }
{ const C = THREE.ShaderChunk, one = unroll(nums(C.lights_fragment_begin, 1));
  out.phone = { fail: SHBIAS.fail, decl: C.shadowmap_pars_fragment.indexOf('float p3dBiasK = 1.0;') >= 0, k: one.indexOf('p3dBiasK = 0.5 + 0.5 * min( sqrt( 1.0 - p3dC * p3dC ) / p3dC, 6.0 );') >= 0,
    sun: one.indexOf('getShadow( directionalShadowMap[ 0 ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowBias * ( 0 == 0 ? p3dBiasK : 1.0 ),') >= 0,
    kFirst: one.indexOf('p3dBiasK = 0.5') < one.indexOf('getShadow( directionalShadowMap[ 0 ]'), balanced: bal(C.lights_fragment_begin) && bal(C.shadowmap_pars_fragment) }; }
// a computer on the post pipeline: the far map's rewrite first, then this
THREE.ShaderChunk.lights_fragment_begin = stock.lf; THREE.ShaderChunk.shadowmap_pars_fragment = stock.sp;
{ %s } }
{ %s }
{ const C = THREE.ShaderChunk, two = unroll(nums(C.lights_fragment_begin, 2)), three = unroll(nums(C.lights_fragment_begin, 3)), sp = C.shadowmap_pars_fragment;
  out.desk = { fail: SHBIAS.fail + FARSH.fail, near: sp.indexOf('getShadow( directionalShadowMap[ 0 ], nS.shadowMapSize, nS.shadowBias * p3dBiasK,') >= 0,
    far: sp.indexOf('getShadow( directionalShadowMap[ 1 ], fS.shadowMapSize, fS.shadowBias, 1.0,') >= 0,
    one: C.lights_fragment_begin.indexOf('getShadow( directionalShadowMap[ 0 ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowBias * p3dBiasK,') >= 0,
    light2: three.indexOf('getShadow( directionalShadowMap[ 2 ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowBias * ( 2 == 0 ? p3dBiasK : 1.0 ),') >= 0,
    sunCall: (two.match(/p3dSunShadow\\(\\)/g) || []).length, balanced: bal(C.lights_fragment_begin) && bal(sp) }; }
console.log(JSON.stringify(out));''' % (json.dumps(str(ROOT / 'three.min.js')), mine, far, mine)
        r = node(script)
        p, d = r['phone'], r['desk']
        self.assertEqual(p['fail'], '')
        self.assertTrue(p['decl'] and p['k'] and p['sun'] and p['kFirst'] and p['balanced'], p)
        self.assertEqual(d['fail'], '')
        self.assertTrue(d['near'], d)        # the near map's lookup takes the slope
        self.assertTrue(d['far'], d)         # the far map's keeps its own
        self.assertTrue(d['one'], d)         # one light (a computer before the far map's first draw keeps two: the rewrite's one-light path too)
        self.assertTrue(d['light2'], d)      # a later light's shadow, if one ever came, keeps its own bias
        self.assertGreaterEqual(d['sunCall'], 1)
        self.assertTrue(d['balanced'])


if __name__ == '__main__':
    unittest.main()
