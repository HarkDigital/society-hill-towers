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
        # Round 220: the timer is on in every desktop post-pipeline session that grants the extension, sampled (tests/test_gput.py); ?gput=0 the escape
        self.assertIn("GPUT.ext = POST.on && !isTouch && !/[?&]gput=0\\b/.test(location.search) ? renderer.getContext().getExtension('EXT_disjoint_timer_query_webgl2') : null;", s)

    def test_roles_once_the_city_stands(self):
        s = self.s
        self.assertIn('if (!SHROLE.done || frameNo % 900 === 0) shadowRoles();', s)   # and again now and then, for late meshes
        f = section(s, '  function shadowRoles() {', '\n  }\n')
        self.assertIn('if (!REAL) return;', f)
        self.assertIn("if (desk && (m === cityMat || m === outerGlassMat)) { if (!o.castShadow && !SHROLE.held && SHROLE.list.indexOf(o) < 0) { o.castShadow = !FARSH.wide; SHROLE.cast++; SHROLE.list.push(o); } recv(o); }", f)
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
        # not in a frame that draws the near map, unless it has waited two (FarTurn runs it)
        self.assertIn('if (renderer.shadowMap.needsUpdate) { if (++FARSH.waited < 3) return false; FARSH.owe = true; }', f)
        self.assertIn('sun.shadow.autoUpdate = false;', f)
        g = section(self.s, '  function farShadowPost() {', '\n  }\n')
        self.assertIn('sun.shadow.autoUpdate = true;', g)
        self.assertIn('for (const o of FARSH.hid) o.castShadow = true;', g)

    def test_the_occlusion_creases(self):
        s = self.s
        self.assertIn("uK: { value: 2.0 } }", s)
        self.assertIn("'  float ao = max(0.5, 1.0 - sum * uK * 5.0 / (R2 * R2 * R2 * 12.0));'", s)
        self.assertIn('* (1.0 - smoothstep(0.6 * R, 1.2 * R, v.z));', s)

    def test_high_up_the_outer_districts_are_the_far_maps(self):
        # the review: a near-map redraw high up with the outer districts in it was 7 ms, a periodic spike at every 8th frame
        # and every frame of a time-lapse; above 250 m they leave the near map to the far one, and the movers keep every 4th
        s = self.s
        self.assertNotIn('moverShadowEvery', s)
        self.assertIn('frameNo % (isTouch ? 12 : 4) === 0', s)
        self.assertIn('farWide(!onFoot && camera.position.y > (FARSH.wide ? FARSH.wideH - 30 : FARSH.wideH));', s)
        self.assertIn('wideH: 250,', s)
        self.assertIn("const farRes = (pick) => (pick === 'sharper' ? 4096 : 2048);", s)   # 24 MB under Auto, 96 under Sharper
        self.assertIn('L.shadow.normalBias = Math.max(2.5, 1.4 * texel);', s)
        # a moved box waits a second since the last draw (a pilot looking round high up drew it every few frames)
        self.assertIn('(Math.hypot(cx - FARSH.cx, cz - FARSH.cz) > ext * 0.25 && performance.now() - FARSH.lastT > 1000)', s)
        # the passes' CPU time and draw calls under ?dev, beside their GPU time
        self.assertIn("gpuRecord(lab + 'Cpu', performance.now() - t0); gpuRecord(lab + 'Calls', renderer.info.render.calls - c0);", s)
        self.assertIn('FARSH.res = farRes(gfxPick());', s)
        self.assertIn('farSize(farRes(pick));', s)   # a Graphics change resizes it
        self.assertIn('const texel = ext * 2 / L.shadow.mapSize.x;', s)

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
  wide: C.shadowmap_pars_fragment.indexOf('s = fS.shadowRadius > 1.5 ? min( mix( 1.0, s, inN ), f ) : mix( f, s, inN );') >= 0,
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
        self.assertTrue(r['wide'])           # and 2 has it shade the near box too, the darker of the two
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
        sw = section(s, '  function shadowsIdleSweep() {', '\n  }\n') + '\n  }\n'
        kw = section(s, '  const KEYWX = {', '\n  }\n') + '\n  }\n'
        ms = section(s, '  let moonNoRecv = null;', '\n  }\n') + '\n  }\n'   # moonNoRecv, shadowOffWhy and moonShadowsOff
        cls.script = '''const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const REAL = true, POST = { on: false };   // a phone: keyWeather must leave its fog alone
let fogTouched = 0;
const sun = { intensity: 0 }, hemi = { intensity: 0 }, gradeU = { uAOK: { value: 1 } }, scene = { fog: { color: { multiplyScalar() { fogTouched++; }, copy() { fogTouched++; }, set() { fogTouched++; } } }, traverse(f) { for (const o of objs) f(o); } };
const renderer = { shadowMap: { needsUpdate: false } };
let shadowsIdle = false;
const sunDir = { y: 0.68 };   // the sun 43 degrees up, a mid-October noon
const shadowAim = { cx: 5 }, lastAim = { cx: 1, cz: 2, extent: 300 }, aims = [];
const aimSun = (cx, cz, e) => { aims.push([cx, cz, e, shadowAim.cx]); if (!shadowsIdle) renderer.shadowMap.needsUpdate = true; };
const objs = [{ receiveShadow: true }, { receiveShadow: true }, { receiveShadow: false }];
const WX = { cover: 0 }, WXFX = { fog: 0, rain: 0, gloom: 0 };
%s
%s
%s
const at = (cover, fog, rain, dayF) => { WX.cover = cover; WXFX.fog = fog; WXFX.rain = rain;
  const deckK = 1 - 0.72 * cover - 0.16 * smooth(0.75, 1.0, cover);
  sun.intensity = 1.85 * deckK; hemi.intensity = 0.54 * (1 - 0.18 * cover);
  const S0 = sun.intensity * sunDir.y, H0 = hemi.intensity;
  const ec = keyWeather(dayF, deckK);
  const fill = 1 + (KEYWX.fill - 1) * dayF * KEYWX.k, H1 = hemi.intensity / fill, S1 = sun.intensity * sunDir.y;
  return { ec: +ec.toFixed(3), k: +KEYWX.k.toFixed(3), sun: +sun.intensity.toFixed(3), hemi: +hemi.intensity.toFixed(3), off: KEYWX.off, recv: objs.map((o) => o.receiveShadow), idle: shadowsIdle, aok: +gradeU.uAOK.value.toFixed(2),
    comp: +KEYWX.comp.toFixed(4), fill: +fill.toFixed(3), sunlit: +((S1 + H1 * fill) * KEYWX.comp / (S1 + H1)).toFixed(4), shade: +(fill * KEYWX.comp).toFixed(3) }; };
const out = { clear: at(0.08, 0, 0, 1), fair: at(0.3, 0, 0, 1), overcast: at(0.92, 0, 0, 1), fog: at(0.7, 1, 0, 1) };
moonShadowsOff(true);   // a phone's dusk on top of the fog's deck
out.both = { why: [...shadowOffWhy], idle: shadowsIdle };
out.clearAgain = at(0.08, 0, 0, 1);   // the deck opens: the moon still holds them off
const late = { receiveShadow: true }; objs.push(late);   // a mesh made after dusk that turns its own receiving on
out.swept = { n: shadowsIdleSweep(), recv: late.receiveShadow };
renderer.shadowMap.needsUpdate = false;
moonShadowsOff(false);
out.allBack = { recv: objs.map((o) => o.receiveShadow), idle: shadowsIdle, redraw: renderer.shadowMap.needsUpdate, aims, fogTouched };
console.log(JSON.stringify(out));''' % (ms, sw, kw)
        cls.r = node(cls.script)

    def test_clear_air_keeps_its_key(self):
        c = self.r['clear']
        self.assertEqual(c['k'], 1)
        self.assertFalse(c['off'])
        # the approved clear-day exposure, but for what gives back the sky's added fill
        self.assertAlmostEqual(c['ec'], c['comp'], places=3)
        self.assertAlmostEqual(self.r['fair']['ec'], self.r['fair']['comp'], places=3)   # a fair day's cumulus too

    def test_the_clear_skys_fill(self):
        # the review: the shade read blue-black; the sky's share rises and the sunlit street keeps its level exactly
        c = self.r['clear']
        self.assertAlmostEqual(c['fill'], 1.8)
        self.assertAlmostEqual(c['sunlit'], 1.0, places=3)
        self.assertGreater(c['shade'], 1.25)          # the shade a quarter brighter or more
        o = self.r['overcast']
        self.assertLess(o['fill'], 1.4)                # a closing deck takes the clear sky's fill with the key
        self.assertAlmostEqual(o['sunlit'], 1.0, places=3)
        self.assertLess(self.r['fog']['fill'], 1.1)

    def test_overcast_soft_and_bright(self):
        o = self.r['overcast']
        self.assertLess(o['k'], 0.6)
        # the camera's exposure for the grey day, before the give-back for the sky's fill
        self.assertGreater(o['ec'] / o['comp'], 1.3)
        self.assertLessEqual(o['ec'] / o['comp'], 1.5 + 1e-3)
        self.assertGreater(o['aok'], 1.1)

    def test_fog_turns_the_receivers_off(self):
        f = self.r['fog']
        self.assertTrue(f['off'])
        self.assertEqual(f['recv'], [False, False, False])
        self.assertTrue(f['idle'])

    def test_reasons_stack(self):
        self.assertEqual(sorted(self.r['both']['why']), ['deck', 'moon'])
        self.assertTrue(self.r['clearAgain']['idle'])     # the moon's reason remains
        self.assertEqual(self.r['allBack']['recv'], [True, True, False, True])
        self.assertFalse(self.r['allBack']['idle'])
        self.assertTrue(self.r['allBack']['redraw'])
        # the return aims the map at the light as it stands: shadowAim forgotten, aimSun called with the last box, once
        self.assertEqual(len(self.r['allBack']['aims']), 1)
        self.assertEqual(self.r['allBack']['aims'][0][:3], [1, 2, 300])
        self.assertIsNone(self.r['allBack']['aims'][0][3])   # NaN

    def test_the_idle_sweep(self):
        self.assertEqual(self.r['swept']['n'], 1)
        self.assertFalse(self.r['swept']['recv'])

    def test_a_phones_fog_is_left_alone(self):
        # the review: r149 mixes a phone's fog in after the tone mapping, so dividing it by the exposure darkened the haze
        self.assertEqual(self.r['allBack']['fogTouched'], 0)
        self.assertNotIn('scene.fog.color.multiplyScalar(1 / ec)', (ROOT / 'app.js').read_text())


@unittest.skipUnless(shutil.which('node'), 'node unavailable')
class KeyLight(unittest.TestCase):
    """aimSun under node (the review: an idle return before the light's direction held a phone's moonlight at the boot
    direction all night): the light follows sunDir every call, idle or not; idle draws no map and leaves shadowAim stale."""

    @classmethod
    def setUpClass(cls):
        s = (ROOT / 'app.js').read_text()
        body = section(s, '  const shadowAim = {', '  aimSun(-1450, -700, 800);')
        script = '''const THREE = require(%s); const V3 = THREE.Vector3;
const sunDir = new V3(-0.62, 0.5, 0.27).normalize(), SHADOW_RES = 2048, lastAim = {};
const sun = new THREE.DirectionalLight(0xffffff, 1); sun.shadow.camera.updateProjectionMatrix = () => { proj++; };
const renderer = { shadowMap: { needsUpdate: false } }; let proj = 0;
%s
const dir = () => { const d = sun.position.clone().sub(sun.target.position).normalize(); return [d.x, d.y, d.z].map((v) => +v.toFixed(4)); };
const want = () => [sunDir.x, sunDir.y, sunDir.z].map((v) => +v.toFixed(4));
const out = {};
aimSun(-1450, -700, 800); out.boot = { dir: dir(), want: want(), redraw: renderer.shadowMap.needsUpdate, proj };
renderer.shadowMap.needsUpdate = false; proj = 0;
shadowsIdle = true;                                   // a phone after dusk: the key light becomes the moon's
sunDir.set(-0.914, 0.35, 0.204).normalize();
aimSun(lastAim.cx, lastAim.cz, lastAim.extent);
out.idle = { dir: dir(), want: want(), redraw: renderer.shadowMap.needsUpdate, proj, stale: shadowAim.sun.distanceTo(sunDir) > 0.1 };
sunDir.set(0.2, 0.6, -0.5).normalize(); aimSun(-1000, -500, 600);   // the moon moves on, the eye too
out.idle2 = { dir: dir(), want: want(), redraw: renderer.shadowMap.needsUpdate };
shadowsIdle = false; aimSun(lastAim.cx, lastAim.cz, lastAim.extent);   // the receivers back: the map is drawn for the light as it stands
out.back = { dir: dir(), want: want(), redraw: renderer.shadowMap.needsUpdate, proj, fresh: shadowAim.sun.distanceTo(sunDir) < 1e-9 };
console.log(JSON.stringify(out));''' % (json.dumps(str(ROOT / 'three.min.js')), body)
        cls.r = node(script)

    def test_the_light_follows_while_idle(self):
        r = self.r
        self.assertEqual(r['boot']['dir'], r['boot']['want'])
        self.assertTrue(r['boot']['redraw'])
        self.assertEqual(r['idle']['dir'], r['idle']['want'])
        self.assertEqual(r['idle2']['dir'], r['idle2']['want'])

    def test_idle_draws_no_map(self):
        r = self.r
        self.assertFalse(r['idle']['redraw'])
        self.assertEqual(r['idle']['proj'], 0)
        self.assertTrue(r['idle']['stale'])
        self.assertFalse(r['idle2']['redraw'])

    def test_the_return_redraws(self):
        r = self.r
        self.assertEqual(r['back']['dir'], r['back']['want'])
        self.assertTrue(r['back']['redraw'])
        self.assertEqual(r['back']['proj'], 1)
        self.assertTrue(r['back']['fresh'])


@unittest.skipUnless(shutil.which('node'), 'node unavailable')
class FarTurn(unittest.TestCase):
    """farShadowPre, farShadowPost, farSize and farWide under node, three's shadow pass modelled (the near map drawn when
    the global flag is up and the sun's own autoUpdate is on, the far one when its needsUpdate is): a time-lapse that
    redraws the near map every frame still gives the far map its turns (the review: none for the whole lapse), never both
    in one frame and the near map never two frames late; high up the outer casters are out of the near map and in the far
    one; a new size makes the map not live until it is drawn again."""

    @classmethod
    def setUpClass(cls):
        s = (ROOT / 'app.js').read_text()
        lit = section(s, '  const FARSH = {', '\n') + '\n'
        res = section(s, '  const farRes = ', '\n') + '\n'
        fns = ''.join(section(s, a, '\n  }\n') + '\n  }\n' for a in ('  function farShadowPre(cam) {', '  function farShadowPost() {', '  function farSize(n) {', '  function farWide(high) {'))
        script = '''const THREE = require(%s); const V3 = THREE.Vector3;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const sunDir = new V3(-0.62, 0.5, 0.27).normalize(), _farV = new V3();
const renderer = { shadowMap: { needsUpdate: false } };
const sun = { shadow: { autoUpdate: true } };
let shadowsIdle = false, frameNo = 0;
const a = { castShadow: true }, b = { castShadow: true }, tree = { castShadow: true, isInstancedMesh: true };
const SHROLE = { held: false, list: [a, b] };
const scene = { traverse(f) { for (const o of [a, b, tree]) f(o); } };
%s%s
FARSH.light = new THREE.DirectionalLight(0, 0); FARSH.on = true; FARSH.res = 3072; FARSH.light.shadow.mapSize.set(3072, 3072); FARSH.light.shadow.autoUpdate = false;
%s
const cam = new THREE.PerspectiveCamera(50, 1.6, 1, 1e5); cam.position.set(-900, 600, 2600); cam.lookAt(-1600, 0, -300); cam.updateMatrixWorld();
const log = [];
const frame = (sunStep, high) => {
  frameNo++;
  if (sunStep) { sunDir.applyAxisAngle(new V3(0, 1, 0), sunStep); renderer.shadowMap.needsUpdate = true; }   // aimSun: the sun moved, the near map is due
  farWide(high);
  const far = farShadowPre(cam);
  const L = FARSH.light, rec = { near: false, far: false, farCasters: null };
  if (renderer.shadowMap.needsUpdate) {
    if (sun.shadow.autoUpdate) rec.near = true;
    if (L.shadow.needsUpdate) { rec.far = true; rec.farCasters = [a.castShadow, b.castShadow, tree.castShadow]; L.shadow.needsUpdate = false; }
    rec.nearCasters = rec.near ? [a.castShadow, b.castShadow, tree.castShadow] : null;
  }
  renderer.shadowMap.needsUpdate = false;
  if (far) farShadowPost();
  log.push(rec);
  return rec;
};
const out = {};
frame(0, false); frame(0, false);                      // the first far map
out.live = FARSH.light.shadow.radius;
log.length = 0;
for (let i = 0; i < 64; i++) frame(0.5 * Math.PI / 180, false);   // a time-lapse: half a degree of sun a frame
let gap = 0, maxGap = 0; for (const r of log) { gap = r.near ? 0 : gap + 1; maxGap = Math.max(maxGap, gap); }
out.lapse = { near: log.filter((r) => r.near).length, far: log.filter((r) => r.far).length, both: log.filter((r) => r.near && r.far).length, maxGap };
log.length = 0;
frame(0, true); out.wideOn = { wide: FARSH.wide, radius: FARSH.light.shadow.radius, near: log[0].near, nearCasters: log[0].nearCasters };
for (let i = 0; i < 24 && !log.some((r) => r.far); i++) frame(0.5 * Math.PI / 180, true);
const fr = log.find((r) => r.far);
out.wideFar = { casters: fr && fr.farCasters, after: [a.castShadow, b.castShadow, tree.castShadow], radius: FARSH.light.shadow.radius };
SHROLE.held = true; frame(0, true); out.held = { wide: FARSH.wide, casters: [a.castShadow, b.castShadow] };
SHROLE.held = false; for (const o of SHROLE.list) o.castShadow = !FARSH.wide;   // __dbg.shadowRoles(true)
frame(0, false); out.low = { wide: FARSH.wide, casters: [a.castShadow, b.castShadow], radius: FARSH.light.shadow.radius };
{ const d0 = FARSH.drawn; for (let i = 0; i < 6; i++) { cam.position.x += 900; cam.updateMatrixWorld(); frame(0, false); } out.moving = FARSH.drawn - d0; }   // 5.4 km in six frames, well inside a second
farSize(4096); out.resized = { res: FARSH.light.shadow.mapSize.x, radius: FARSH.light.shadow.radius };
frame(0, false); out.redrawn = { radius: FARSH.light.shadow.radius, far: log[log.length - 1].far };
console.log(JSON.stringify(out));''' % (json.dumps(str(ROOT / 'three.min.js')), lit, res, fns)
        cls.r = node(script)

    def test_a_time_lapse_gives_the_far_map_its_turns(self):
        r = self.r
        self.assertEqual(r['live'], 1)
        l = r['lapse']
        self.assertGreaterEqual(l['far'], 5)        # one in about ten frames
        self.assertGreaterEqual(l['near'], 54)
        self.assertEqual(l['both'], 0)
        self.assertLessEqual(l['maxGap'], 1)        # the near map a frame late at most

    def test_high_up(self):
        r = self.r
        self.assertTrue(r['wideOn']['wide'])
        self.assertEqual(r['wideOn']['radius'], 2)
        self.assertTrue(r['wideOn']['near'])        # the switch redraws the near map ...
        self.assertEqual(r['wideOn']['nearCasters'], [False, False, True])   # ... without the outer districts
        self.assertEqual(r['wideFar']['casters'], [True, True, False])       # the far map: every building, no instanced mesh
        self.assertEqual(r['wideFar']['after'], [False, False, True])
        self.assertEqual(r['wideFar']['radius'], 2)
        self.assertEqual(r['held']['casters'], [False, False])               # __dbg.shadowRoles(false) holds them off anywhere
        self.assertFalse(r['held']['wide'])
        self.assertEqual(r['low'], {'wide': False, 'casters': [True, True], 'radius': 1})

    def test_a_moving_box_waits_a_second(self):
        self.assertLessEqual(self.r['moving'], 1)

    def test_a_new_size(self):
        r = self.r
        self.assertEqual(r['resized'], {'res': 4096, 'radius': 0})
        self.assertTrue(r['redrawn']['far'])
        self.assertEqual(r['redrawn']['radius'], 1)


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
