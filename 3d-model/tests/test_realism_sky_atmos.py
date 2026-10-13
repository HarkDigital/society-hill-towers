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
        # one varying: three's vFogDepth is the view position's -z (the merge review: two floats more a fogged program, not three)
        self.assertIn('vFogV = mvPosition.xyz;', out['vert'])
        self.assertNotIn('vFogDepth', out['vert'])
        self.assertIn('varying vec3 vFogV;', out['pv'])
        self.assertNotIn('varying float vFogDepth', out['pv'] + out['pars'])
        self.assertIn('#define vFogDepth ( - vFogV.z )', out['pars'])
        # the cull line's wall closes the air's remainder, on the true distance, linear fog only
        self.assertIn('fogFactor = max( fogFactor, smoothstep( fogNear, fogFar, apD ) );', out['frag'])
        self.assertLess(out['frag'].index('#ifndef FOG_EXP2'), out['frag'].index('smoothstep( fogNear, fogFar, apD )'))
        self.assertIn('if ( fogFactor > 0.004 ) {', out['frag'])
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
        self.assertIn('scene.fog.far = far; scene.fog.near = far * 0.75;', f)    # cullFogged still reads a distance
        # the night keeps Round 51's reach, and with it the night's cull line (a phone's night frame was tuned to it)
        self.assertIn('farN = fogBase.far * F.haze * (1 - 0.6 * night);', f)
        self.assertIn('V = Math.min(V, 1.15 * farN);', f)
        self.assertNotIn('1.25 * farN', f)

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
        self.assertIn('const sunDeckK = REAL ? 1 - 0.80 * smooth(0.55, 1.0, WX.cover) - 0.16 * smooth(0.75, 1.0, WX.cover) : deckK;', self.src)
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
        self.assertIn('hemi.groundColor.multiplyScalar(1 - 0.3 * dayF * (1 - sunDeckK * (1 - 0.9 * WXFX.fog) * (1 - 0.55 * WXFX.gloom)));', s)

    def test_the_cloud_volumes(self):
        s = self.src
        # a computer on WebGL2 only, one switch off; a phone and WebGL1 keep the first phase's march
        self.assertIn("const CLOUD3D = { on: REAL && !isTouch && !!renderer.capabilities.isWebGL2 && (CLOUD3D_Q ? CLOUD3D_Q[1] === '1' : !CLOUD3D_WEAK && GFX.pick !== 'smoother'),", s)
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


class MergeReview(unittest.TestCase):
    """The sky's merge with the key light under weather (realism/post-shadows) and the review that followed: the sun's key
    taken by the deck, the fog and the rain once each, the camera lifting for the sun the city actually lost, a phone's fog
    left in display colour (r149 mixes it after the tone map), the cull line back at Round 51's and 52's reach with the
    ground fog in it, the phone's clouds off the per-pixel jitter, the volumes' weak cells and far fragments translucent,
    the volumes gated by the GPU and falling back if their program fails, and their shadows projected from their own height."""

    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')

    def node(self, script):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_key_and_the_exposure_take_the_weather_once(self):
        s = self.src
        a = s.index('  const KEYWX = {')
        kw = s[a:s.index('\n  }\n', a) + 4]
        self.assertNotIn('scene.fog.color', kw)          # a phone's fog is display colour: no inverse
        deck = re.search(r'const sunDeckK = REAL \? (.+?) : deckK;', s).group(1)
        self.assertNotIn('fog', deck)                     # the fog's share is keyWeather's alone
        self.assertIn('WXFX.fog', kw)
        script = (
            "const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };\n"
            "const REAL = true, POST = { on: false }, WX = { cover: 0 }, WXFX = { fog: 0, rain: 0, gloom: 0 };\n"
            "const sun = { intensity: 0 }, hemi = { intensity: 0 }, gradeU = { uAOK: { value: 1 } };\n"
            "const scene = { fog: { color: { multiplyScalar() { throw new Error('the fog colour was touched'); } } } };\n"
            "function moonShadowsOff() {}\n" + kw + "\n"
            "const at = (cover, fog, rain) => { WX.cover = cover; WXFX.fog = fog; WXFX.rain = rain;\n"
            "  const sunDeckK = " + deck + ";\n"
            "  sun.intensity = 1.85 * sunDeckK; hemi.intensity = 0.54;\n"
            "  const ec = keyWeather(1, sunDeckK);\n"
            "  return { sun: +(sun.intensity / 1.85).toFixed(4), ec: +ec.toFixed(3) }; };\n"
            "console.log(JSON.stringify({ clear: at(0.22, 0, 0), mid: at(0.7, 0, 0), over: at(0.92, 0, 0), fog: at(0.7, 1, 0), rain: at(0.95, 0, 1) }));")
        out = self.node(script)
        self.assertEqual(out['clear'], {'sun': 1, 'ec': 1})
        # a 0.7 cover keeps 0.79 of the sun (the shadows mask the rest under each cloud), and the camera keeps the clear day's
        # exposure: the review measured 1.17 here, a lift for a 0.50 sun the city never lost
        self.assertAlmostEqual(out['mid']['sun'], 0.793, places=2)
        self.assertEqual(out['mid']['ec'], 1)
        # one fog term: 0.79 of the sun times keyWeather's 0.1, not 0.3 of that again
        self.assertAlmostEqual(out['fog']['sun'], 0.0793, places=3)
        self.assertTrue(1.4 < out['fog']['ec'] <= 1.5, out['fog'])   # a fog's city photographs bright and soft
        self.assertTrue(1.3 < out['over']['ec'] <= 1.5, out['over'])
        self.assertLess(out['rain']['sun'], 0.02)

    def test_threes_fog_mixes_after_the_tone_map(self):
        # why a phone's fog colour takes no inverse of the exposure: in r149 every built-in shader mixes the fog after the
        # tone map and the encoding, in display colour, and the dome writes display colour too
        t = (ROOT / 'three.min.js').read_text(encoding='utf-8')
        n = 0
        for m in re.finditer(r'#include <fog_fragment>', t):
            before = t[max(0, m.start() - 140):m.start()]
            if '#include <output_fragment>' not in before:
                continue
            n += 1
            self.assertLess(before.index('#include <tonemapping_fragment>'), before.index('#include <encodings_fragment>'))
        self.assertGreaterEqual(n, 6)                    # basic, lambert, phong, standard and physical, toon, points, sprite

    def test_the_sky_reads_the_fog_colour_the_city_mixes(self):
        f = body(self.src, '  function applyLighting() {')
        kw = f.index('keyWeather(dayF, sunDeckK)')
        rs = f.index('realSky(el, dayF, night, twi, ch, cz)')
        pu = f.index('pUndoColor(scene.fog.color, postU.uExposure.value)')
        self.assertLess(kw, rs)
        self.assertLess(rs, pu)
        r = body(self.src, '  function realSky(')
        self.assertIn('const fogD = scene.fog.color;', r)
        self.assertIn('U.uSkyFogC.value.copy(fogD);', r)

    def test_the_cull_line(self):
        r = body(self.src, '  function realSky(')
        lm = re.search(r'const lm = (.+?);\n', r).group(1)
        far = re.search(r'let far = (.+?);\n', r).group(1)
        top = int(re.search(r'const AP_TOP = (\d+);', self.src).group(1))
        script = (
            "const AP_TOP = %d, lm = %s;\n"
            "const run = (V, ye, fog, night) => { const b = 3.912 / V, H = 1200, bl = fog * 3.912 / 320, farN = 40000 * (1 - 0.6 * night);\n"
            "  const he = Math.max(ye, 0), hl = Math.max(ye - 8, 0); return Math.round(%s); };\n"
            "const fogV = 1 / (1 / 45000 + 1 / 8000);\n"
            "console.log(JSON.stringify({ day: run(45000, 140, 0, 0), dayHigh: run(45000, 1500, 0, 0), night: run(18400, 140, 0, 1), fogStreet: run(fogV, 3.2, 1, 0),\n"
            "  fogHigh: run(fogV, 400, 1, 0), fogNight: run(Math.min(fogV, 18400), 3.2, 1, 1) }));") % (top, lm, far)
        out = self.node(script)
        self.assertEqual(out['day'], 40000)               # Round 52's clear day
        self.assertEqual(out['dayHigh'], 40000)
        self.assertEqual(out['night'], 16000)             # Round 51's night: a phone's night frame (the review found 20 km)
        self.assertTrue(1500 < out['fogStreet'] < 3000, out['fogStreet'])   # the ground fog counts (it was 9.2 km)
        self.assertGreater(out['fogHigh'], 6000)          # over the layer the towers stand out of it
        self.assertLess(out['fogNight'], 3000)

    def test_the_phone_marches_from_the_midpoints(self):
        s = self.src
        self.assertIn("${isTouch ? '' : 'cJit = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);'}", s)
        self.assertIn("float edge = ${isTouch ? '0.11' : '0.08'} + min(0.12, footprint * 1.5);", s)

    def test_the_volumes_lose_their_specks(self):
        s = self.src
        self.assertIn('float d = cRemap(s * pr, 1.0 - 0.75 * wc, 1.0) * smoothstep(0.0, 0.4, wc);', s)
        self.assertIn("${v3 ? ' * (1.0 - 0.5 * smoothstep(4000.0, 15000.0, t))' : ''}", s)
        self.assertIn('float footprint = max(t * cone, ds * 0.55) * ${f(layer.scale)};', s)

    def test_the_volumes_gate_and_fall_back(self):
        s = self.src
        rx = re.search(r'const CLOUD3D_WEAK = (/.+/i)\.test\(CLOUD3D_GPU\);', s).group(1)
        names = ['ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'Intel(R) HD Graphics 630',
                 'ANGLE (Intel Inc., Intel(R) Iris(TM) Plus Graphics 655, OpenGL 4.1)', 'Google SwiftShader', 'Mali-G78',
                 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)',
                 'ANGLE (Apple, ANGLE Metal Renderer: Apple M1 Pro, Unspecified Version)',
                 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'AMD Radeon Pro 5500M OpenGL Engine',
                 'AMD Radeon(TM) Graphics', 'AMD Radeon HD 7700 Series', '']
        out = self.node('const rx = %s; console.log(JSON.stringify(%s.map((n) => rx.test(n))));' % (rx, json.dumps(names)))
        self.assertEqual(out, [True] * 5 + [False] * 7)
        self.assertIn("if (REAL && !isTouch && !CLOUD3D.on) CLOUD3D.why = ", s)
        # a program that fails to compile or link gives the deck the first phase's march, read once at its first draw
        f = body(s, '  function cloudsPhase1(why) {')
        self.assertIn('cloudMat.fragmentShader = cloudFrag(); cloudMat.needsUpdate = true;', f)
        self.assertIn('for (const rt of CLOUD3D.rts) rt.dispose();', f)
        self.assertIn('    fragmentShader: cloudFrag(),', s)
        self.assertIn('  function cloudFrag() {', s)
        self.assertIn('gl.getProgramParameter(pr.program, gl.LINK_STATUS)', s)
        self.assertIn("if (!ok) cloudsPhase1('compile');", s)
        self.assertIn('CLOUD3D.rts = [shape, detail];', s)

    def test_the_shadows_lie_under_the_volumes(self):
        s = self.src
        self.assertIn('const CLOUD3D_ALT = 1250;', s)
        self.assertIn('multiplyScalar((CLOUD3D.on ? CLOUD3D_ALT : CLOUD_ALT) / Math.max(sunDir.y, 0.25));', s)

    def test_the_sky_takes_back_only_the_grades_own_saturation(self):
        s = self.src
        self.assertIn('U.uSatK.value = POST.on ? 1 / Math.max(0.5, SKY_SAT0) : 1;', s)
        self.assertLess(s.index('const gradeU = { uSat: { value: REAL ? 0.84 : 1 }'), s.index('  const SKY_SAT0 = gradeU.uSat.value;'))
        self.assertNotIn('gradeU.uSat.value)', body(s, '  function realSky('))


if __name__ == '__main__':
    unittest.main()
