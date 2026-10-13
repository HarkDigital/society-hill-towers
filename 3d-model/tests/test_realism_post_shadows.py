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
        self.assertIn('if (!SHROLE.done || frameNo % 900 === 0) shadowRoles();', s)   # and again now and then, for late meshes
        f = section(s, '  function shadowRoles() {', '\n  }\n')
        self.assertIn('if (!REAL) return;', f)
        self.assertIn("if (desk && (m === cityMat || m === outerGlassMat)) { if (!o.castShadow && !SHROLE.held && SHROLE.list.indexOf(o) < 0) { o.castShadow = true; SHROLE.cast++; SHROLE.list.push(o); } recv(o); }", f)
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

    def test_the_movers_redraw_less_often_high_up(self):
        s = self.s
        self.assertIn('const moverShadowEvery = () => (REAL && camera.position.y > 250 ? 8 : 4);', s)
        self.assertIn('frameNo % (isTouch ? 12 : moverShadowEvery()) === 0', s)   # a phone's 12 unchanged

    def test_exposure_line(self):
        self.assertIn('renderer.toneMappingExposure = (0.94 + 0.11 * dayF) * keyWeather(dayF, deckK);', self.s)


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
        ms = section(s, '  let moonNoRecv = null;', '  function applyLighting() {')
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
class Roles(unittest.TestCase):
    """shadowRoles run under node against a stub scene: the roles once, again for a mesh that arrives later (the closures'
    paving strips come with the first poll), never twice for one mesh, the casters held off by __dbg.shadowRoles(false)
    staying off through a later pass, a flat made at night joining the list the receivers come back from, and a phone
    gaining no casters."""

    @classmethod
    def setUpClass(cls):
        s = (ROOT / 'app.js').read_text()
        body = section(s, '  const SHROLE = {', '\n  }\n') + '\n  }\n'
        cls.script = '''const REAL = true; const gfxPick = () => 'auto';
const window = { __dbg: {} };
const renderer = { shadowMap: { needsUpdate: false } };
const FARSH = { light: null, on: false, can: false, fail: '', ext: 0, cx: 0, cz: 0, drawn: 0 };
const lastAim = {}; let moonNoRecv = null; const shadowOffWhy = new Set();
const shadowAudit = () => 0, pickAt = () => 0, gpuStats = () => 0, KEYWX = {};
const std = (ud) => ({ isMeshStandardMaterial: true, userData: ud || {} });
const cityMat = std(), outerGlassMat = std(), flatMat = std({ wxSurf: true }), otherMat = std();
const mk = (mat, ud) => ({ isMesh: true, material: mat, castShadow: false, receiveShadow: false, userData: ud || {}, geometry: { boundingSphere: { center: { x: 0, z: 0 } } } });
const run = (touch) => {
  const isTouch = touch;
  const a = mk(cityMat), b = mk(outerGlassMat), f = mk(flatMat), o = mk(otherMat), card = mk(otherMat, { treeCard: true }), inst = Object.assign(mk(flatMat), { isInstancedMesh: true });
  const pin = (ud) => { const x = mk(flatMat, ud); Object.defineProperty(x, 'receiveShadow', { get() { return false; }, set() {}, configurable: true }); return x; };
  const apron = pin({ noShadow: true }), pinned = pin();   // Girard College's apron (rebuilds/gc.js), and a pin that is not a rebuild's
  const outerMeshes = [a, b], objs = [a, b, f, o, card, inst, apron, pinned];
  const scene = { traverse(fn) { for (const x of objs) fn(x); } };
  %s
  const flags = (xs) => xs.map((x) => [x.castShadow, x.receiveShadow]);
  const out = {};
  shadowRoles(); out.first = { roles: window.__dbg.shadowRoles(), flags: flags(objs) };
  shadowRoles(); out.again = window.__dbg.shadowRoles();
  const late = mk(flatMat); objs.push(late);
  shadowRoles(); out.late = { roles: window.__dbg.shadowRoles(), flag: [late.castShadow, late.receiveShadow] };
  window.__dbg.shadowRoles(false); shadowRoles(); out.held = { flags: flags([a, b]), redraw: renderer.shadowMap.needsUpdate };
  window.__dbg.shadowRoles(true); out.back = flags([a, b]);
  moonNoRecv = []; const night = mk(flatMat); objs.push(night); shadowRoles();
  out.night = { recv: night.receiveShadow, listed: moonNoRecv.indexOf(night) >= 0 };
  moonNoRecv = null;
  return out;
};
console.log(JSON.stringify({ desk: run(false), phone: run(true) }));''' % body
        cls.r = node(cls.script)

    def test_a_computer(self):
        d = self.r['desk']
        # the outer buildings cast and receive, the flat and the card receive, the plain mesh and the instanced flat are left
        self.assertEqual(d['first']['flags'], [[True, True], [True, True], [False, True], [False, False], [False, True], [False, False], [False, True], [False, False]])
        # the apron's getter pin gives way (the ground around it receives now); a pin that is no rebuild's stays, uncounted
        self.assertEqual(d['first']['roles']['recv'], 5)
        self.assertEqual(d['first']['roles']['cast'], 2)
        self.assertEqual(d['again']['cast'], 2)       # idempotent
        self.assertEqual(d['again']['recv'], d['first']['roles']['recv'])
        self.assertEqual(d['late']['flag'], [False, True])   # a later flat takes its role on the next pass
        self.assertEqual(d['late']['roles']['runs'], 3)

    def test_held_casters_stay_off(self):
        d = self.r['desk']
        self.assertEqual(d['held']['flags'], [[False, True], [False, True]])
        self.assertTrue(d['held']['redraw'])
        self.assertEqual(d['back'], [[True, True], [True, True]])

    def test_a_flat_made_at_night(self):
        n = self.r['desk']['night']
        self.assertFalse(n['recv'])
        self.assertTrue(n['listed'])

    def test_a_phone_gains_no_casters(self):
        p = self.r['phone']
        self.assertEqual(p['first']['roles']['cast'], 0)
        self.assertTrue(all(not c for c, r in p['first']['flags']))
        self.assertEqual(p['first']['flags'][2], [False, False])   # Auto: no new receivers either


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
