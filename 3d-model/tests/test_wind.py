"""The realism round two: one wind for everything that moves in it (D14), snow that lies (D8), the worn ground (D12).

- One wind: the trees' cards and crowns, the tufts, the flag, the water's chop and the precipitation read one profile (WIND,
  windU, WIND_GLSL), the live speed and heading eased and their gusts a noise running downwind. The JavaScript twin of the
  shaders' gust field (windAt) runs here under Node: a calm is calm, a gust front travels downwind at the wind's own speed, the
  field is periodic in its clock, and the GLSL carries the same constants. The crowns' and the cards' frustum spheres still
  hold every vertex as the windy shaders move it (CROWN_SLACK, the cards' 1.4). ?wind1=0 keeps Round 179's fixed sway.
- Snow that lies: the ground's snow picture is baked (bake_ground_art.py's VEG), named in ground_art.json, read only through
  the alley's sampler on the bare ground's program inside its #ifndef (no new sampler), laid by the weather's late pass; the
  plowed streets' ruts and kerb piles on the lane shader; the parked cars' caps a colour term. ?snow2=0 keeps Round 188's.
- The worn ground: the lawn's 47 m read weighted by the footprint, packed earth under the crowns (never over snow), the kerb's
  dust on the road's outer metre. ?wear=0 keeps the look before it.
"""
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


def cut(start, end, src=SRC):
    a = src.index(start)
    return src[a:src.index(end, a)]


class Flags(unittest.TestCase):
    def test_every_part_has_its_flag_and_is_real_gated(self):
        self.assertIn("const WIND = { on: REAL && !/[?&]wind1=0\\b/.test(location.search),", SRC)
        self.assertIn("const SNOW2_ON = REAL && !/[?&]snow2=0\\b/.test(location.search);", SRC)
        self.assertIn("const WEAR_ON = REAL && !/[?&]wear=0\\b/.test(location.search);", SRC)

    def test_the_old_sway_is_kept_behind_the_flag(self):
        vert = cut('  const TREE_ART_VERT = ', '  const TREE_VARY = ')
        self.assertIn("'float sw = (sin(uTime * 1.1 + ph) * 0.6 + sin(uTime * 2.3 + ph * 3.1) * 0.25) * 0.012 * yy * yy * S * (1.0 - tw);'", vert)
        self.assertIn('${WIND.on ? `', vert)
        tufts = cut('  function grassInit() {', '    grassMesh = new THREE.InstancedMesh(')
        self.assertIn("float sw = sin(uTime * 1.7 + ph) * 0.55 + sin(uTime * 3.1 + ph * 2.7) * 0.3;", tufts)
        self.assertIn('if (WIND.on) {', tufts)


class OneWind(unittest.TestCase):
    def test_everything_reads_the_profile(self):
        # the cards and their depth material (one patch), the crowns, the tufts, the flag, the water, the rain, the snow, the shells
        patch = cut('  function treeArtPatch(sh, depth) {', "    if (lit) sh.vertexShader = sh.vertexShader.replace('#include <defaultnormal_vertex>'")
        self.assertIn('if (WIND.on) Object.assign(sh.uniforms, windU);', patch)
        self.assertIn("(WIND.on ? WIND_GLSL + '\\n' : '')", patch)
        self.assertIn("dmat.onBeforeCompile = (sh) => treeArtPatch(sh, true);", SRC)   # the shadow sways with its tree
        sway = cut('    const canopySway = (sh) => {', '    // Round 146')
        self.assertIn('Object.assign(sh.uniforms, windU);', sway)
        fam = cut('  function famineStep() {', '  // ?dev: __dbg.famine()')
        self.assertIn('windAt(FAM.pole[0], FAM.pole[1])', fam)
        self.assertIn('Math.atan2(wz, wx) - FAM.ang', fam)
        self.assertIn('rainVel.set((WIND.on ? WIND.vx : WX.windX) * 0.75,', SRC)
        self.assertIn('snowVel.set((WIND.on ? WIND.vx : WX.windX) * sk,', SRC)
        self.assertIn('shellU.uWind.value.set((WIND.on ? WIND.vx : WX.windX) * 0.75 / fall,', SRC)
        step = cut('  function windStep(dt) {', '  // ?dev: __dbg.wind(spd)')
        self.assertIn('waterU.uWAmp.value = clamp(0.5 + W.eye * 0.14, 0.5, 1.8);', step)
        self.assertIn('if (!reducedMotion) {', step)   # nothing moves under reduced motion
        self.assertIn('windStep(dt);   // the realism round two', SRC)
        self.assertIn('wind_gusts_10m&hourly=snowfall&forecast_hours=12', SRC)

    def test_glsl_and_javascript_share_the_gust_field(self):
        g = cut('  const WIND_GLSL = [', '].join')
        js = cut('  const windFr = ', '  const windAmpAt = ')
        for k in ('0.1031', '33.33', '60.0', '0.65', '0.35', 'q * 3.0', '17.0', '1.6', '0.4'):
            self.assertIn(k, g)
        for k in ('0.1031', '33.33', '/ 60', '0.65', '0.35', 'q * 3', '+ 17', '1.6', '0.4'):
            self.assertIn(k, js)

    def test_the_crowns_stay_inside_their_slack(self):
        slack = float(re.search(r'const CROWN_GROW = [\d.]+, CROWN_SLACK = ([\d.]+);', SRC).group(1))
        sway = cut('      if (WIND.on) {   // the realism round two: the crowns', '      } else')
        m = re.search(r'wK = clamp\(windAmp\(wE\) / 0\.012, ([\d.]+), ([\d.]+)\)', sway)
        self.assertIsNotNone(m)
        kmax = float(m.group(2))
        self.assertIn('transformed += (wL * (sw * 0.04 + windLean(wE) * 0.05) + vec3(-wL.z, 0.0, wL.x) * sw * 0.02) * wK * up;', sway)
        self.assertIn('transformed.y += sin(uWindP.w + ph * 5.0 + position.x * 2.0) * 0.02 * up;', sway)
        self.assertIn('float sw = sin(uWindP.x + ph) * 0.6 + sin(uWindP.y + ph * 3.1) * 0.25;', sway)
        lean = float(re.search(r'WIND_LEAN = ([\d.]+);', SRC).group(1))
        side = kmax * math.hypot(0.85 * 0.04 + lean * 0.05, 0.85 * 0.02)
        self.assertLessEqual(math.hypot(side, 0.02), slack)       # wL is a unit vector in the crown's frame, up at most 1

    def test_the_cards_stay_inside_their_sphere(self):
        amp = [float(v) for v in re.search(r'const WIND_AMP = \[([\d.]+), ([\d.]+), ([\d.]+)\]', SRC).groups()]
        lean = float(re.search(r'WIND_LEAN = ([\d.]+);', SRC).group(1))
        self.assertIn('cardG.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0.9, 0), 1.4);', SRC)
        art = json.loads((ROOT / 'tree_art.json').read_text())
        hf = min(r['hf'] for lk in art['images'].values() for r in lk['side'].values())
        S = 1.08 / hf                                              # the card's size over the tree's height (REAL's 1.08 at most)
        corner = math.hypot(0.5 * S * 1.1 + amp[2] * (0.85 + lean) * S, S - 0.9)
        self.assertLess(corner, 1.4)

    @unittest.skipUnless(shutil.which('node'), 'node is not installed')
    def test_the_gust_field_under_node(self):
        js = cut('  const windFr = ', '  const windAmpAt = ')
        script = 'const WIND = { clk: 3.7, dx: 0.8, dz: 0.6, spd: 6, gust: 0.45 };\n' + js + r'''
const out = {};
// a calm is calm
WIND.spd = 0; out.calm = Math.max(...[0, 50, 900, -3000].map((x) => windAt(x, x * 0.3)));
// the field: never negative, its mean near the reported speed, its gusts to (1 + 0.96 gust) of it
WIND.spd = 6; let lo = 1e9, hi = -1e9, sum = 0, n = 0;
for (let i = 0; i < 4000; i++) { const e = windAt(-8000 + i * 4.1, 300 - i * 1.7); lo = Math.min(lo, e); hi = Math.max(hi, e); sum += e; n++; }
out.lo = lo; out.hi = hi; out.mean = sum / n;
// a gust front travels downwind at the wind's own speed: the clock's advance of dt * spd / 60 meets the point dt * spd downwind
let worst = 0;
for (let k = 0; k < 50; k++) { const x = k * 37.3 - 900, z = 400 - k * 11.1, dt = 0.5 + k * 0.07; const a = windAt(x, z); WIND.clk += dt * WIND.spd / 60; const b = windAt(x + WIND.dx * dt * WIND.spd, z + WIND.dz * dt * WIND.spd); WIND.clk -= dt * WIND.spd / 60; worst = Math.max(worst, Math.abs(a - b)); }
out.travel = worst;
// periodic in its clock (it wraps at 256 without a jump)
const c0 = WIND.clk; const a0 = windAt(120, -40); WIND.clk = c0 + 256; out.period = Math.abs(windAt(120, -40) - a0); WIND.clk = c0;
console.log(JSON.stringify(out));
'''
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o['calm'], 0)
        self.assertGreaterEqual(o['lo'], 6 * (1 - 0.64 * 0.45) - 1e-9)
        self.assertLessEqual(o['hi'], 6 * (1 + 0.96 * 0.45) + 1e-9)
        self.assertTrue(5.5 < o['mean'] < 7.5, o)
        self.assertLess(o['travel'], 1e-6)
        self.assertLess(o['period'], 1e-6)


class SnowThatLies(unittest.TestCase):
    def test_the_picture_is_baked_and_named(self):
        bake = (ROOT / 'bake_ground_art.py').read_text()
        self.assertIn("'alley': 10.0, 'snow': 6.5}", bake)
        man = json.loads((ROOT / 'ground_art.json').read_text())
        snow = man['veg']['snow']
        for k in ('img', 'imgHalf'):
            self.assertTrue((ROOT / snow[k]).exists(), snow[k])
        self.assertEqual(snow['m'], 6.5)
        self.assertIn('"ground_art.json"', (ROOT / 'build.py').read_text())   # build.py's art list checks every file it names

    def test_no_new_sampler_and_the_alley_guard(self):
        ground = cut('  function vegGrassGLSL(forced, paved) {', '  function vegAfterGLSL(paved) {')
        i = ground.index('if (uAlleySnow > 0.5) vegSnowT = ')
        self.assertGreater(ground.rfind("'#ifndef VEG_NO_ALLEY'", 0, i), ground.rfind("'#endif'", 0, i))
        self.assertIn("' && uAlleySnow < 0.5'", ground)    # the alley's own line steps aside while the slot holds the snow
        self.assertNotIn('uniform sampler2D uSnow', cut('  function vegSurfPatch(', '  const VEG_DROP = '))
        self.assertIn("forced && SNOW2_ON ? 'uniform float uAlleySnow; uniform vec3 uAlleySnowM;' : '',", SRC)
        # the swap: the same sampler, another texture; the alley's late arrival does not take the slot back
        step = cut('  function snow2Step(F) {', '  const snow2Probe = ')
        self.assertIn('vegU.uAlley.value = S.tex; snow2U.uAlleySnow.value = 1;', step)
        self.assertIn('if (im.decode) im.decode().then(done, done);', step)   # decoded ahead, not in the frame that draws it
        self.assertIn('WX.snowSoon', step)                                    # fetched on the forecast
        self.assertIn('if (SNOW2.live) SNOW2.alley = t; else vegU.uAlley.value = t;', SRC)
        self.assertIn('!TIER2', cut('  const SNOW2 = {', '\n'))

    def test_the_weather_lays_it_and_keeps_its_lines(self):
        f = cut('  function wxSurfacePatch(shader) {', '\n  }\n')
        self.assertIn("REAL && SNOW2_ON ? '/*wxSnowLane*/' : '',", f)
        self.assertIn("REAL && SNOW2_ON ? '/*wxSnowLate*/' : '',", f)
        late = cut('  function wxSurfaceLate(shader) {', '\n  }\n')
        self.assertIn("fs.replace('/*wxSnowLate*/', 'diffuseColor.rgb *= mix(vec3(1.0), vegSnowT, wxSnowW);')", late)
        self.assertIn('wxSnowW *= 1.0 - 0.72 * lnSnowRut;', late)
        lane = cut('  function lanePatchReal(shader, fresh) {', '  // streets follow the terrain')
        self.assertIn('lnSnowRut = mix(exp(-lsR * lsR), 0.32, lsF) * lnLaneK;', lane)
        self.assertIn('if (SNOW2_ON) shader.uniforms.uLnSnow = wxSurfU.uSnowAcc;', lane)

    def test_the_cars_caps_are_colour_only(self):
        car = cut('  function carArtMaterial(kind) {', "    mat.customProgramCacheKey = () => 'car-art-v1';")
        self.assertIn('(vCarX.y < -0.5 ? 1.0 : 0.25 * (1.0 - vGlassM))', car)   # a parked car's brake is -1: the whole cap
        self.assertNotIn('castShadow', car)
        self.assertNotIn('gl_FragDepth', cut('  const WIND = {', '  function windProbe('))

    def test_the_roof_edges(self):
        self.assertIn("if (vWallL > 0.5 && abs(n.y) < 0.35) fabSnowW = max(fabSnowW, uFabSnow * (1.0 - smoothstep(0.1 - lpA, 0.1 + lpA, vWallH - v))", SRC)
        self.assertIn("'    float lpA = max(fwidth(v), 0.01) * 0.5;'", SRC)   # the derivative outside the wall's branch


class Wear(unittest.TestCase):
    def test_the_terms(self):
        self.assertIn("(WEAR_ON ? '0.20 + 0.18 * smoothstep(0.06, 0.4, sfw)' : '0.20')", SRC)
        can = cut('  function canopyPatch(shader, worldExpr, green) {', '  // the trees step hands it')
        self.assertIn("shader.fragmentShader.indexOf('float wxSnowW') !== -1 ? ' * (1.0 - wxSnowW)' : ''", can)
        self.assertIn('green && WEAR_ON ?', can)
        lane = cut('  function lanePatchReal(shader, fresh) {', '  // streets follow the terrain')
        self.assertIn('WEAR_ON ? ', lane)
        self.assertIn('* lnKerb * (1.0 - lnMouth) * (1.0 - smoothstep(1.0, 3.0, lnW))', lane)


if __name__ == '__main__':
    unittest.main()
