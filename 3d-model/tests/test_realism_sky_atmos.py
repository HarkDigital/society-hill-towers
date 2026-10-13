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
as a direct-light mask, the lightning ribbon's streams and the switches back to the old look."""
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
        self.assertIn('gl_FragColor.rgb = mix( gl_FragColor.rgb, fogMix, fogFactor );', out['frag'])
        self.assertIn('vFogDepth = - mvPosition.z;', out['vert'])
        self.assertIn('vFogV = mvPosition.xyz;', out['vert'])
        self.assertIn('varying vec3 vFogV;', out['pv'])
        for f in ('float apLayer( vec4 L, float dy, float d )', 'float apOD( vec3 v, float d )', 'vec3 apColor( vec3 v, float d )'):
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


if __name__ == '__main__':
    unittest.main()
