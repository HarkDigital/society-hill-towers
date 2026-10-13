"""The realism pass, the sky and the air (Mike: "make this look more photo realistic and less cartoony. This should apply
to all surfaces/water/anything you can improve to look more real").

Under REAL the air is a medium: three's fog chunks are replaced once, before any program compiles, with an exponential
height fog on the true distance from the eye (a 1,200 m haze over the river's datum and a 55 m ground fog), coloured as
the dome's horizon is in that azimuth with the sun's glow toward it, and its visibility comes from the weather and the air
quality (45 km in clean air, about 6 in rain, 1.5 in snow, 320 m in a fog). The uniforms are shared by every material (r149
clones uniforms per material; these vectors return themselves), and a material without them reads zeros, which is
THREE.Fog exactly (?real=0, ?ap=0). Checked here: the chunks go in before anything that compiles or clones the fog's
uniforms, the custom shaders still pair the fog's vertex and fragment chunks, the shared uniforms survive r149's clone, the
preprocessed chunks keep three's linear branch, the visibility the weather gives, the probe's boot call, the cloud shadow
as a direct-light mask, the lightning ribbon's streams and the switches back to the old look.

The second try adds the cloud volumes (a computer on WebGL2: Perlin-Worley shape and Worley detail drawn once at boot
into 3D render targets, the cells carved on the same 2D field as the ground's shadows, three light taps up the sun's
ray), the stars a city's sky lets through (the two dozen brightest at their real places, checked here against Polaris
and Vega), the city's glow scattered along the low air as light added over the veil, the dome's far band lit from below
by night, and the probe rebaked as the weather eases in."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def body(src, head):
    a = src.index(head)
    return src[a:src.index('\n  }\n', a) + 4]


class SkyAtmos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')
        a = cls.src.index('  const AP = { on: REAL')
        b = cls.src.index("for (const n of Object.keys(apU)) u[n] = apU[n]; }\n  }\n", a)
        cls.block = cls.src[a:b + len("for (const n of Object.keys(apU)) u[n] = apU[n]; }\n  }\n")]

    def node(self, script):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_chunks_go_in_before_anything_compiles(self):
        s = self.src
        at = s.index('C.fog_fragment = [')
        self.assertLess(s.index('const scene = new THREE.Scene();'), at)
        self.assertLess(at, s.index('  const skyMat = new THREE.ShaderMaterial({'))
        self.assertLess(at, s.index('  refreshEnv();\n'))             # the probe's PMREM is the first program built
        self.assertLess(at, s.index('THREE.UniformsUtils.clone(THREE.UniformsLib.fog)'))   # the deck clones the fog's uniforms
        for m in re.finditer(r'renderer\.(render|compile)\(', s[:at]):
            # only inside functions (renderPost and its passes), never at boot
            self.assertIn('function renderPost', s[:m.start()])

    def test_custom_shaders_pair_the_fog_chunks(self):
        # the fragment chunk now reads a varying the vertex chunk writes: a shader with one and not the other fails to link
        text = self.src + ''.join(p.read_text(encoding='utf-8') for p in sorted((ROOT / 'rebuilds').glob('*.js')))
        frag = len(re.findall(r'<fog_pars_fragment>', text))
        self.assertEqual(frag, len(re.findall(r'<fog_pars_vertex>', text)))
        self.assertEqual(frag, len(re.findall(r'<fog_vertex>', text)))

    def test_the_shared_uniforms_survive_threes_clone(self):
        out = self.node("const THREE = require('./three.min.js'); const REAL = true; const location = { search: '' };\n" + self.block + r'''
const lib = Object.keys(THREE.ShaderLib).filter((k) => THREE.ShaderLib[k].uniforms.fogColor);
const shared = lib.every((k) => { const u = THREE.UniformsUtils.clone(THREE.ShaderLib[k].uniforms); return Object.keys(apU).every((n) => u[n] && u[n].value === apU[n].value); });
const custom = THREE.UniformsUtils.clone(THREE.UniformsLib.fog);
const merged = THREE.UniformsUtils.merge([THREE.UniformsLib.common, THREE.UniformsLib.fog]);
console.log(JSON.stringify({ lib: lib.length, shared, custom: custom.fogAP.value === apU.fogAP.value && custom.fogAPSunC.value === apU.fogAPSunC.value,
  merged: merged.fogAPAnti.value === apU.fogAPAnti.value, on: AP.on, off: apU.fogAP.value.w }));
''')
        self.assertGreaterEqual(out['lib'], 9)     # basic, lambert, phong, standard, physical, toon, points, sprite, ...
        self.assertTrue(out['shared'])
        self.assertTrue(out['custom'])
        self.assertTrue(out['merged'])
        self.assertTrue(out['on'])
        self.assertEqual(out['off'], 0)            # off until applyLighting's first frame: THREE.Fog behind the veil

    def test_the_chunks_keep_threes_linear_fog(self):
        out = self.node("const THREE = require('./three.min.js'); const REAL = true; const location = { search: '' };\n" + self.block + r'''
const C = THREE.ShaderChunk, bal = (t) => { let a = 0, b = 0; for (const ch of t) { if (ch === '(') a++; if (ch === ')') a--; if (ch === '{') b++; if (ch === '}') b--; if (a < 0 || b < 0) return false; } return a === 0 && b === 0; };
console.log(JSON.stringify({ frag: C.fog_fragment, pars: C.fog_pars_fragment, vert: C.fog_vertex, pv: C.fog_pars_vertex,
  balanced: [C.fog_fragment, C.fog_pars_fragment, C.fog_vertex].every(bal) }));
''')
        self.assertTrue(out['balanced'])
        self.assertIn('float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );', out['frag'])   # three's own, the fallback
        self.assertIn('if ( fogAP.w > 0.5 ) {', out['frag'])
        # the city's glow by night is light scattered along the low air, added over the veil (fogAdd is zero by day and
        # with AP off, so three's own mix stands)
        self.assertIn('gl_FragColor.rgb = mix( gl_FragColor.rgb, fogMix, fogFactor ) + fogAdd;', out['frag'])
        self.assertIn('vec3 fogMix = fogColor, fogAdd = vec3( 0.0 );', out['frag'])
        self.assertIn('vFogDepth = - mvPosition.z;', out['vert'])
        self.assertIn('vFogV = mvPosition.xyz;', out['vert'])
        self.assertIn('varying vec3 vFogV;', out['pv'])
        for f in ('float apLayer( vec4 L, float dy, float d )', 'float apOD( vec3 v, float d )', 'vec3 apColor( vec3 v, float d )',
                  'vec3 apGlow( vec3 v, float d )'):
            self.assertIn(f, out['pars'])
        # the sun's lobe is normalised to one at the sun: its five weights over 0.56
        self.assertIn('* 1.7857 );', out['pars'])
        self.assertAlmostEqual(0.24 + 0.07 + 0.10 + 0.10 + 0.05, 1 / 1.7857, places=4)

    def test_the_visibility_the_weather_gives(self):
        f = body(self.src, '  function realSky(')
        ext = re.search(r'const ext = ([^;]+);', f).group(1)
        out = self.node('''const ext = (F, Vc) => %s;
const Vc = 45000;
const wx = { clear: {}, rain: { rain: 0.6, gloom: 0.3 }, downpour: { rain: 1, gloom: 0.5 }, snow: { snow: 0.65 }, blizzard: { snow: 1 },
  storm: { rain: 1, gloom: 1 }, fog: { fog: 1 } };
const o = {};
for (const k in wx) o[k] = 1 / ext(Object.assign({ rain: 0, snow: 0, gloom: 0, hail: 0, fog: 0 }, wx[k]), Vc);
console.log(JSON.stringify(o));''' % ext.replace('\n', ' '))
        self.assertAlmostEqual(out['clear'], 45000, delta=1)          # nothing but the clean air
        self.assertTrue(4000 < out['rain'] < 7000, out['rain'])
        self.assertTrue(1500 < out['downpour'] < 2500, out['downpour'])
        self.assertTrue(1000 < out['snow'] < 2000, out['snow'])
        self.assertLess(out['blizzard'], 700)
        self.assertLess(out['storm'], out['downpour'])
        self.assertTrue(5000 < out['fog'] < 8000, out['fog'])          # the haze over a ground fog; the layer is its own
        self.assertIn('const bl = F.fog * 3.912 / 320;', f)          # 320 m on the street in a fog
        self.assertIn('apU.fogAPLow.value.set(bl, 1 / 55, 8, 0);', f)
        self.assertIn('scene.fog.far = Math.min(far, 80000);', f)    # cullFogged still reads a distance
        # the night keeps Round 51's reach, and with it the night's cull line (a phone's night frame was tuned to it)
        self.assertIn('farN = fogBase.far * F.haze * (1 - 0.6 * night);', f)
        self.assertIn('V = Math.min(V, 1.15 * farN);', f)
        self.assertIn('1.25 * farN);', f)

    def test_the_probe_boots_without_the_lamps(self):
        # refreshEnv runs at boot, long before lampUniform is declared: reading it there is a TDZ ReferenceError
        f = body(self.src, '  function refreshEnv() {')
        self.assertNotIn('lampUniform', f)
        self.assertIn('lk = envLamp', f)
        self.assertIn('envLamp = lampUniform.value;', body(self.src, '  function realSky('))
        self.assertLess(self.src.index('  let envLamp = 0;'), self.src.index('  refreshEnv();\n'))

    def test_cloud_shadows_take_the_sun_not_the_albedo(self):
        f = body(self.src, '  function cloudShadowPatch(shader, worldExpr) {')
        self.assertIn("if (REAL) shader.fragmentShader = shader.fragmentShader.replace('#include <lights_fragment_end>'", f)
        self.assertIn('reflectedLight.directDiffuse *= csK; reflectedLight.directSpecular *= csK;', f)
        self.assertIn("diffuseColor.rgb *= 1.0 - 0.45 * cloudShade(", f)    # the old stain, ?real=0
        self.assertIn('const sunDeckK = REAL ? (1 - 0.80 * smooth(0.55, 1.0, WX.cover)', self.src)
        self.assertIn('sun.intensity = 0.05 * (1 - 0.6 * WX.cover) + 0.13 * mp.k * deckK;', self.src)   # the moon keeps Round 88's

    def test_the_lightning_ribbon(self):
        s = self.src
        self.assertIn('const BOLT_RIB = REAL, BOLT_W = 70;', s)
        # every stream a multiple of 4 bytes (Round 158): float positions, directions and sides
        self.assertIn('new Float32Array(BOLT_MAX * 12)', s)
        self.assertIn("boltGeo.setAttribute('aSide', new THREE.BufferAttribute(side, 2));", s)
        self.assertIn('const side = new Float32Array(BOLT_MAX * 8), idx = new Uint16Array(BOLT_MAX * 6);', s)
        self.assertIn('boltGeo.setDrawRange(0, BOLT_RIB ? n * 6 : n * 2);', s)
        self.assertIn('const flashG = WXFX.flash * (REAL ? 0.3 : 1);', s)

    def test_the_old_look_is_one_switch_away(self):
        s = self.src
        self.assertIn("const AP = { on: REAL && !/[?&]ap=0\\b/.test(location.search), clear: 45000, V: 45000 };", s)
        self.assertIn('if (REAL) realSky(el, dayF, night, twi, ch, cz);', s)
        self.assertIn('steps: isTouch ? 32 : REAL ? 80 : 64,', s)
        self.assertIn('new THREE.Color(REAL ? 0x070d19 : 0x060e1b)', s)
        self.assertIn("float t = span.x + (float(i) + ${REAL ? 'cJit' : '0.5'}) * ds;", s)
        # the clear day's sun and hemisphere stand (Round 54): the bounce changes only away from a clear sky
        self.assertIn('sun.intensity = 1.85 * smooth(-3, 15, el) * sunDeckK * (1 - 0.55 * WXFX.gloom);', s)
        self.assertIn('hemi.groundColor.multiplyScalar(1 - 0.3 * dayF * (1 - sunDeckK * (1 - 0.55 * WXFX.gloom)));', s)

    def test_the_cloud_volumes(self):
        s = self.src
        # a computer on WebGL2 only, one switch off; a phone and WebGL1 keep the first phase's march
        self.assertIn("const CLOUD3D = { on: REAL && !isTouch && !!renderer.capabilities.isWebGL2 && !/[?&]clouds3d=0\\b/.test(location.search),", s)
        f = body(s, '  function cloudVolumesBake() {')
        self.assertIn('const shape = mk(128), detail = mk(64)', f)
        self.assertIn('new THREE.WebGL3DRenderTarget(n, n, n)', f)
        self.assertIn('t.wrapS = t.wrapT = t.wrapR = THREE.RepeatWrapping;', f)
        self.assertIn('renderer.setRenderTarget(rt, z); renderer.render(sc, cam);', f)
        self.assertIn('renderer.setRenderTarget(prevRT); renderer.autoClear = prevAuto;', f)   # in a finally
        # a failed bake falls back before the deck's shader is written, and the deck reads the flag
        self.assertIn('if (CLOUD3D.on) { try { cloudVolumesBake(); } catch (e) { CLOUD3D.on = false;', s)
        self.assertLess(s.index('if (CLOUD3D.on) { try { cloudVolumesBake(); }'), s.index('  const cloudMat = new THREE.ShaderMaterial({'))
        self.assertIn("${CLOUD3D.on ? 'precision highp sampler3D;", s)          # GLSL ES 3.00 has no default for it
        self.assertIn('...(CLOUD3D.on ? { tCloudShape: { value: CLOUD3D.shape }, tCloudDetail: { value: CLOUD3D.detail } } : {}),', s)
        # the volumes' cells sit on the same 2D field and threshold as the ground's shadows
        self.assertIn('float cloudWc(float f, float cov) { float thr = 0.60 - cov * 0.40;', s)
        self.assertIn('float thr = 0.60 - clamp(uCloudCov, 0.0, 1.0) * 0.40;', s)
        # the Perlin-Worley spread to the full range (its 5th to 95th percentiles), or the cells extrude their footprint
        self.assertIn('0.70, 0.95), 0.55, far);', s)
        self.assertIn('0.7 * smoothstep(60.0, 260.0, footprint / scale)', s)     # and eased to its mean past a pixel's reach
        # the march's light: three taps up the sun's ray, Beer's law with the multiple-scattering octave
        self.assertIn('float tSun = max(exp(-odS), 0.30 * exp(-odS * 0.2));', s)
        self.assertEqual(s.count('cloudTap(p + uSun * '), 3)

    def test_the_generator_and_deck_templates_balance(self):
        # the GLSL lives in JS template literals: a dropped brace or bracket would fail only at the GPU
        s = self.src
        a = s.index('      fragmentShader: `\n        uniform float uZ, uN, uKind;')
        gen = s[a:s.index('      `,\n    });', a)]
        b = s.index("      // ---- the volumes' density (the second phase)")
        deck = s[b:s.index("` : ''}\n      ${CLOUD_LAYERS.map(cloudLayerShader).join('\\n')}", b)]   # the GLSL, without the template's own close
        for t in (gen, deck):
            for o, c in ('()', '{}', '[]'):
                self.assertEqual(t.count(o), t.count(c), (o, t[:80]))

    def test_the_stars_stand_where_they_are(self):
        s = self.src
        a = s.index('  const STARS = [')
        table = s[a:s.index('  ];\n', a) + 5]
        f = body(s, '  function starsAt(ms) {')
        js = ('const DEG = Math.PI / 180, SITE = { lat: 39.9455, lon: -75.1447 };\n'
              'const skyMat = { uniforms: { uStar: { value: Array.from({ length: 24 }, () => ({ set(x, y, z, w) { this.x = x; this.y = y; this.z = z; this.w = w; } })) } } };\n'
              + table + '\nlet starsMs = NaN;\n' + f +
              '\nconst alt = (v) => Math.asin(v.y) / DEG, az = (v) => (Math.atan2(v.x, -v.z) / DEG + 360) % 360;\n'
              'starsAt(Date.UTC(2026, 9, 13, 2, 30));\n'   # 22:30 EDT on October 12
              'const u = skyMat.uniforms.uStar.value;\n'
              'console.log(JSON.stringify({ n: STARS.length, polaris: [alt(u[23]), az(u[23])], vega: [alt(u[2]), az(u[2])], sirius: u[0].w, polarisW: u[23].w }));')
        out = self.node(js)
        self.assertEqual(out['n'], 24)                                    # the dome's uStar[24]
        self.assertIn('uniform vec4 uStar[24];', s)
        self.assertAlmostEqual(out['polaris'][0], 39.95, delta=1.0)       # Polaris stands at the latitude, due north
        self.assertTrue(out['polaris'][1] < 3 or out['polaris'][1] > 357, out['polaris'])
        self.assertAlmostEqual(out['vega'][0], 41.1, delta=1.5)           # in the west after dark in October
        self.assertAlmostEqual(out['vega'][1], 290.7, delta=2.0)
        self.assertEqual(out['sirius'], 0)                                # under the horizon then: no light
        self.assertGreater(out['polarisW'], 0.1)

    def test_the_nights_glow_and_the_probe_follow_the_weather(self):
        s = self.src
        # the glow in the low air is light, added over the deck's veil as over the city's
        self.assertIn('col = mix(col, fogMix, fogFactor) + fogAdd;', s)
        # the dome's far cloud band is lit from below by night like the deck
        self.assertIn("(REAL ? '    cc += uGlow * (1.7 - 0.5 * lit);\\n' : '')", s)
        # the probe rebakes as the weather eases in and the night closes, not only with the sun
        f = body(s, '  function applyLighting() {')
        self.assertIn('if (REAL && Math.abs(envKey - lastEnvKey) > 0.15) lastEnvEl = 999;', f)
        self.assertIn('lastEnvKey = envKey;', f)


if __name__ == '__main__':
    unittest.main()
