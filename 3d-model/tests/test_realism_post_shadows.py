"""The realism pass, post and shadows (Oct 12, Mike: "please do anything necessary to make this look more photo realistic and
less cartoony"). The outer districts, the far ring and every flat outside the core cast and receive (shadowRoles); a far
shadow map past the near box on a computer (FARSH: a black second light, lights_fragment_begin rewritten once); the key
light under weather and the exposure with it (keyWeather); the receivers off under a closed deck as well as a phone's moon
(moonShadowsOff's reasons); the occlusion's creases; the wide bloom (BLOOMW); the grade on a phone (CustomToneMapping); the
GPU pass timings; __dbg.pickAt."""
from pathlib import Path
import json
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


class Switches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_flags(self):
        s = self.s
        self.assertIn("FARSH.can = POST.on && REAL && !LITE && !/[?&]shadowwide=0\\b/.test(location.search) && gfxPick() !== 'smoother';", s)
        self.assertIn("const BLOOMW = { on: REAL && !/[?&]bloomwide=0\\b/.test(location.search),", s)
        # timers only with ?dev, never a production frame
        self.assertIn("GPUT.ext = POST.on && /[?&]dev\\b/.test(location.search) ? renderer.getContext().getExtension('EXT_disjoint_timer_query_webgl2') : null;", s)

    def test_roles_once_the_city_stands(self):
        s = self.s
        self.assertIn('if (!SHROLE.done) shadowRoles();', s)
        f = section(s, '  function shadowRoles() {', '\n  }\n')
        self.assertIn('if (!REAL) return;', f)
        self.assertIn("if (desk && (m === cityMat || m === outerGlassMat)) { if (!o.castShadow) { o.castShadow = true; SHROLE.cast++; } recv(o); }", f)
        self.assertIn('if (!m.userData.wxSurf || o.isInstancedMesh) return;', f)
        self.assertIn("phoneFlats = isTouch && gfxPick() === 'sharper'", f)   # a phone pays new filter taps only by choice
        # never a recompile: flags only, never a light's castShadow
        self.assertNotIn('sun.castShadow =', f)
        # a mesh flagged while the receivers are off joins their list
        self.assertIn('if (moonNoRecv) moonNoRecv.push(o); else o.receiveShadow = true;', f)

    def test_tree_cards_cast(self):
        # r149 never uploads viewMatrix to a MeshDepthMaterial: the cards' depth pass read a zero matrix and drew nothing
        # (tests/shadows_gpu.html draws a card into a sun's map on a GPU)
        self.assertIn("(depth ? '#define viewMatrix modelViewMatrix\\n' : '')", self.s)
        f = section(self.s, '  function treeArtPatch(sh, depth) {', '\n  }\n')
        self.assertIn('#define viewMatrix modelViewMatrix', f)

    def test_tree_cards_look_out_of_their_crown(self):
        s = self.s
        self.assertIn('    if (lit) cardShadowReach(sh);', s)
        f = section(s, '  function cardShadowReach(sh) {', '\n  }\n')
        self.assertIn('worldPosition.xyz += uSunW * length(instanceMatrix[2].xyz) * 0.6;', f)

    def test_the_far_map_never_holds_instanced_meshes(self):
        f = section(self.s, '  function farShadowPre(cam) {', '\n  }\n')
        self.assertIn('if (o.castShadow && o.isInstancedMesh) { o.castShadow = false; FARSH.hid.push(o); }', f)
        self.assertIn('if (renderer.shadowMap.needsUpdate) return false;', f)   # never in a frame that draws the near map
        self.assertIn('sun.shadow.autoUpdate = false;', f)
        g = section(self.s, '  function farShadowPost() {', '\n  }\n')
        self.assertIn('sun.shadow.autoUpdate = true;', g)
        self.assertIn('for (const o of FARSH.hid) o.castShadow = true;', g)

    def test_the_occlusion_creases(self):
        s = self.s
        self.assertIn("uK: { value: 2.0 } }", s)
        self.assertIn("'  float ao = max(0.5, 1.0 - sum * uK * 5.0 / (R2 * R2 * R2 * 12.0));'", s)
        self.assertIn('* (1.0 - smoothstep(0.6 * R, 1.2 * R, v.z));', s)

    def test_exposure_line(self):
        # (the sky's merge: keyWeather is handed the share of the key the sun was actually given, sunDeckK under REAL)
        self.assertIn('renderer.toneMappingExposure = (0.94 + 0.11 * dayF) * keyWeather(dayF, sunDeckK);', self.s)


@unittest.skipUnless(shutil.which('node'), 'node unavailable')
class Chunks(unittest.TestCase):
    """The far map's rewrite of r149's light loop, run on the vendored three: the sun's shadow through p3dSunShadow, the
    black light's lighting gone, a later light still lit, and every #if closed."""

    @classmethod
    def setUpClass(cls):
        s = (ROOT / 'app.js').read_text()
        body = section(s, '    const C = THREE.ShaderChunk, lf = C.lights_fragment_begin;', '      const L = new THREE.DirectionalLight(0x000000, 0);')
        script = '''const THREE = require(%s); const FARSH = { fail: '' };
const orig = THREE.ShaderChunk.lights_fragment_begin;
{ %s } }
const C = THREE.ShaderChunk;
// three's own program steps: the light counts, then the loops unrolled
const unroll = (src) => src.replace(/#pragma unroll_loop_start\\s+for\\s*\\(\\s*int\\s+i\\s*=\\s*(\\d+)\\s*;\\s*i\\s*<\\s*(\\d+)\\s*;\\s*i\\s*\\+\\+\\s*\\)\\s*{([\\s\\S]+?)}\\s+#pragma unroll_loop_end/g,
  (m, a, b, snip) => { let o = ''; for (let i = +a; i < +b; i++) o += snip.replace(/\\[\\s*i\\s*\\]/g, '[ ' + i + ' ]').replace(/UNROLLED_LOOP_INDEX/g, i); return o; });
const nums = (src, n) => src.replace(/NUM_DIR_LIGHTS/g, n).replace(/NUM_DIR_LIGHT_SHADOWS/g, n).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g, 0).replace(/NUM_SPOT_LIGHT_MAPS/g, 0).replace(/NUM_SPOT_LIGHT_SHADOWS/g, 0).replace(/NUM_SPOT_LIGHT_COORDS/g, 0).replace(/NUM_SPOT_LIGHTS/g, 0).replace(/NUM_RECT_AREA_LIGHTS/g, 0).replace(/NUM_POINT_LIGHT_SHADOWS/g, 0).replace(/NUM_POINT_LIGHTS/g, 0).replace(/NUM_HEMI_LIGHTS/g, 1);
const bal = (src) => { let d = 0; for (const l of src.split('\\n')) { const t = l.trim(); if (/^#if/.test(t)) d++; if (/^#endif/.test(t)) d--; if (d < 0) return false; } return d === 0; };
const two = unroll(nums(C.lights_fragment_begin, 2)), three = unroll(nums(C.lights_fragment_begin, 3)), one = unroll(nums(C.lights_fragment_begin, 1));
console.log(JSON.stringify({ fail: FARSH.fail, changed: orig !== C.lights_fragment_begin,
  sunCall: (two.match(/p3dSunShadow\\(\\)/g) || []).length, light1: two.indexOf('directionalLights[ 1 ]') >= 0, light2: three.indexOf('directionalLights[ 2 ]') >= 0,
  light2shadow: three.indexOf('directionalShadowMap[ 2 ]') >= 0, oneLight: one.indexOf('getShadow( directionalShadowMap[ 0 ]') >= 0,
  balanced: bal(C.lights_fragment_begin) && bal(C.shadowmap_pars_fragment), pars: C.shadowmap_pars_fragment.indexOf('float p3dSunShadow()') >= 0,
  farOnly: C.shadowmap_pars_fragment.indexOf('fS.shadowRadius > 0.5') >= 0,
  pointsKept: C.lights_fragment_begin.slice(0, orig.indexOf('#if ( NUM_DIR_LIGHTS > 0 )')) === orig.slice(0, orig.indexOf('#if ( NUM_DIR_LIGHTS > 0 )')) && C.lights_fragment_begin.endsWith(orig.slice(orig.indexOf('#if ( NUM_RECT_AREA_LIGHTS > 0 )'))) }));
''' % (json.dumps(str(ROOT / 'three.min.js')), body)
        cls.r = node(script)

    def test_rewritten(self):
        r = self.r
        self.assertEqual(r['fail'], '')
        self.assertTrue(r['changed'])
        self.assertTrue(r['pars'])
        self.assertTrue(r['balanced'])

    def test_the_sun_reads_both_maps_and_the_black_light_is_skipped(self):
        r = self.r
        self.assertGreaterEqual(r['sunCall'], 1)
        self.assertFalse(r['light1'])        # light 1 (the far map's) is never lit
        self.assertTrue(r['light2'])         # a third light would still be
        self.assertTrue(r['light2shadow'])
        self.assertTrue(r['oneLight'])       # one light (a phone): the stock lookup
        self.assertTrue(r['farOnly'])        # radius is the far map's switch
        self.assertTrue(r['pointsKept'])


class GpuPageCuts(unittest.TestCase):
    def test_the_markers_shadows_gpu_cuts_by(self):
        s = (ROOT / 'app.js').read_text()
        page = (ROOT / 'tests' / 'shadows_gpu.html').read_text()
        for a, b in (("  const TREE_ART_VERT = ", "  function treeChipColor("), ("    const C = THREE.ShaderChunk, lf = C.lights_fragment_begin;", "      const L = new THREE.DirectionalLight(0x000000, 0);")):
            self.assertIn(a, page)
            self.assertIn(b, page)
            self.assertLess(s.index(a), s.index(b, s.index(a)))


@unittest.skipUnless(shutil.which('node'), 'node unavailable')
class Weather(unittest.TestCase):
    """keyWeather and moonShadowsOff's reasons, run under node against stubs."""

    @classmethod
    def setUpClass(cls):
        s = (ROOT / 'app.js').read_text()
        kw = section(s, '  const KEYWX = {', '\n  }\n') + '\n  }\n'
        ms = section(s, '  let moonNoRecv = null;', '\n  }\n') + '\n  }\n'   # moonNoRecv, shadowOffWhy and moonShadowsOff
        cls.script = '''const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const REAL = true, POST = { on: true };
const sun = { intensity: 0 }, hemi = { intensity: 0 }, gradeU = { uAOK: { value: 1 } }, scene = { fog: { color: { multiplyScalar() {} } }, traverse(f) { for (const o of objs) f(o); } };
const renderer = { shadowMap: { needsUpdate: false } };
let shadowsIdle = false;
const objs = [{ receiveShadow: true }, { receiveShadow: true }, { receiveShadow: false }];
const WX = { cover: 0 }, WXFX = { fog: 0, rain: 0, gloom: 0 };
%s
%s
const at = (cover, fog, rain, dayF) => { WX.cover = cover; WXFX.fog = fog; WXFX.rain = rain;
  const deckK = 1 - 0.72 * cover - 0.16 * smooth(0.75, 1.0, cover);
  sun.intensity = 1.85 * deckK; hemi.intensity = 0.54 * (1 - 0.18 * cover);
  const ec = keyWeather(dayF, deckK);
  return { ec: +ec.toFixed(3), k: +KEYWX.k.toFixed(3), sun: +sun.intensity.toFixed(3), hemi: +hemi.intensity.toFixed(3), off: KEYWX.off, recv: objs.map((o) => o.receiveShadow), idle: shadowsIdle, aok: +gradeU.uAOK.value.toFixed(2) }; };
const out = { clear: at(0.08, 0, 0, 1), fair: at(0.3, 0, 0, 1), overcast: at(0.92, 0, 0, 1), fog: at(0.7, 1, 0, 1) };
moonShadowsOff(true);   // a phone's dusk on top of the fog's deck
out.both = { why: [...shadowOffWhy], idle: shadowsIdle };
out.clearAgain = at(0.08, 0, 0, 1);   // the deck opens: the moon still holds them off
moonShadowsOff(false);
out.allBack = { recv: objs.map((o) => o.receiveShadow), idle: shadowsIdle, redraw: renderer.shadowMap.needsUpdate };
console.log(JSON.stringify(out));''' % (ms, kw)
        cls.r = node(cls.script)

    def test_clear_air_is_untouched(self):
        c = self.r['clear']
        self.assertEqual(c['k'], 1)
        self.assertEqual(c['ec'], 1)          # the approved clear-day exposure
        self.assertFalse(c['off'])
        self.assertEqual(self.r['fair']['ec'], 1)   # a fair day's cumulus too

    def test_overcast_soft_and_bright(self):
        o = self.r['overcast']
        self.assertLess(o['k'], 0.6)
        self.assertGreater(o['ec'], 1.3)
        self.assertLessEqual(o['ec'], 1.5)
        self.assertGreater(o['aok'], 1.1)

    def test_fog_turns_the_receivers_off(self):
        f = self.r['fog']
        self.assertTrue(f['off'])
        self.assertEqual(f['recv'], [False, False, False])
        self.assertTrue(f['idle'])

    def test_reasons_stack(self):
        self.assertEqual(sorted(self.r['both']['why']), ['deck', 'moon'])
        self.assertTrue(self.r['clearAgain']['idle'])     # the moon's reason remains
        self.assertEqual(self.r['allBack']['recv'], [True, True, False])
        self.assertFalse(self.r['allBack']['idle'])
        self.assertTrue(self.r['allBack']['redraw'])


@unittest.skipUnless(shutil.which('node'), 'node unavailable')
class PhoneGrade(unittest.TestCase):
    def test_the_stub_is_there_to_replace(self):
        # r149's CustomToneMapping stub, which the phone's grade replaces (a three upgrade must keep a hook for it)
        r = node('const T = require(%s); console.log(JSON.stringify(T.ShaderChunk.tonemapping_pars_fragment.indexOf("vec3 CustomToneMapping( vec3 color ) { return color; }") >= 0));' % json.dumps(str(ROOT / 'three.min.js')))
        self.assertTrue(r)

    def test_wiring(self):
        s = (ROOT / 'app.js').read_text()
        f = section(s, '  if (!POST.on && REAL) {', '\n  }\n')
        self.assertIn('renderer.toneMapping = THREE.CustomToneMapping;', f)
        self.assertIn("'  vec3 c = ACESFilmicToneMapping( color );',", f)
        self.assertIn("'  c = mix( vec3( L ), c, 0.84 );',", f)


if __name__ == '__main__':
    unittest.main()
