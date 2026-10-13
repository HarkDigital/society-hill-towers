"""The realism pass, weather (Mike: "please do anything necessary to make this look more photo realistic and less
cartoony ... all surfaces/water/anything"). A wet street is a dielectric film with puddles, rings and, at night, the
lamps drawn out toward the eye; the rain is soft streak quads with a far curtain; snow is specks at their true size
with motion blur; lights in wet air carry halos and the grade follows the weather. ?real=0 keeps every old look.

These pin the switches, the phone path (no 1- or 3-byte streams, fewer drops, no rings, the light map's two taps in
place of the computer's sixteen lamps), the wiring order the shaders depend on, and run two pieces under Node: the
glint lobe (it must streak toward the eye, which is the whole point of stretching it) and the grade's relative
weather term (it must ride on whatever base the grade's owners set)."""
import json
from pathlib import Path
import math
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class WetStreets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_the_old_varnish_is_kept_for_real_0(self):
        s = self.s
        f = cut(s, '  function wxSurfacePatch(shader) {', '\n  }\n')
        self.assertIn("REAL ? WX_WET_GLSL.color : 'diffuseColor.rgb *= 1.0 - 0.45 * wxWetW;'", f)
        self.assertIn("REAL ? '' : 'metalnessFactor = mix(metalnessFactor, 0.32, wxWetW * (0.4 + 0.6 * wxDark));'", f)   # dielectric under REAL
        self.assertIn('if (REAL) wxWetPatch(shader);', f)
        # a street is as wet by night as by day (it was cut to 45 per cent after dark)
        self.assertIn('wxSurfU.uWet.value = REAL ? F.wet : F.wet * (0.45 + 0.55 * F.dayF);', s)

    def test_the_snow_lines_are_untouched(self):
        # the ground and trees' engineers own the snow cover in this patch: the weather pass adds lines, never rewrites them
        f = cut(self.s, '  function wxSurfacePatch(shader) {', '\n  }\n')
        for line in ("'float wxSnowW = uSnowAcc * max(wxUpW, 0.14) * (0.78 + 0.22 * wxN);',",
                     "'diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.88, 0.90, 0.93), wxSnowW);',",
                     "'roughnessFactor = mix(roughnessFactor, 0.92, wxSnowW);',"):
            self.assertIn(line, f)

    def test_puddles_fade_with_footprint_and_snow(self):
        c = cut(self.s, '  const WX_WET_GLSL = {', '\n  };\n')
        self.assertIn("(1.0 - wxSnowW)", c)
        self.assertIn("(1.0 - smoothstep(0.35, 1.2, wxFw))", c)   # a roof seen from the air never speckles
        self.assertIn("'/*wxLane*/',", c)
        self.assertIn('vLane.z - 1.25', c)                        # the gutters: the road's last metre each side

    def test_the_lamp_pool_guard_still_sees_its_own_declaration(self):
        # lampLightPatch returns early once a lamp patch has run (its declarations end 'uniform float uLampOn;'), and the
        # weather wraps the flats before surfTexPatch runs: the weather's own declarations name the lamp map only through
        # LAMP_WX_DECL, which the lamp patch then leaves out of its own
        f = cut(self.s, '  function wxWetPatch(shader) {', '\n  }\n')
        self.assertNotIn('uniform sampler2D uLampMap', cut(self.s, '  const WX_WET_GLSL = {', '\n  };\n'))
        # the lamps on the wet street read the lamp patch's own sampler (a second name for the same texture spent a unit of
        # sixteen): the wet patch declares it, and the lamp patch, keyed on its own uLampOn, declares only the rest
        self.assertIn("if (shader.fragmentShader.indexOf('uniform sampler2D uLampMap') === -1) decl += '\\n' + LAMP_WX_DECL;", f)
        self.assertNotIn('uWxLampMap', self.s)
        self.assertIn("if (shader.fragmentShader.indexOf('uniform float uLampOn;') !== -1) return;", self.s)
        self.assertIn("(fs.indexOf(LAMP_WX_DECL) !== -1 ? 'uniform sampler2D uLampNear;", self.s)

    def test_the_gutters_land_after_every_hook(self):
        s = self.s
        self.assertIn('m.onBeforeCompile = (sh, r) => { wxSurfacePatch(sh); prev(sh, r); wxSurfaceLate(sh); };', s)
        f = cut(s, '  function wxSurfaceLate(shader) {', '\n  }\n')
        self.assertIn("indexOf('varying vec4 vLane;')", f)
        self.assertIn("replace('/*wxLane*/', WX_WET_GLSL.lane)", f)

    def test_the_phone_path(self):
        s = self.s
        self.assertIn('const WX_GLINT_N = isTouch ? 0 : 16;', s)
        f = cut(s, '  function wxWetPatch(shader) {', '\n  }\n')
        self.assertIn('if (!isTouch) decl += ', f)                   # the rings: a computer only
        self.assertIn("(isTouch ? '' : [", f)
        self.assertIn('const RAIN_N = REAL && isTouch ? 8000 : 16000;', s)
        self.assertIn('const SNOW_N = REAL && !isTouch ? 30000 : 11000;', s)
        self.assertIn('const WX_SHELLS = REAL ? (isTouch ? [[30, 160], [80, 260]] : [[28, 150], [75, 260], [190, 480]]) : [];', s)
        self.assertIn("uMaxPx: { value: isTouch ? 24 : 44 }", s)

    def test_no_narrow_vertex_streams(self):
        # WebKit's Metal backend pads a copy of every stream whose stride is not a multiple of 4 (Round 158)
        rain = cut(self.s, '  if (REAL) {\n    const g = new THREE.InstancedBufferGeometry();', '    rainMesh = new THREE.Mesh(g, m);')
        self.assertIn('const seed = new Float32Array(RAIN_N * 3);', rain)
        self.assertIn("g.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seed, 3));", rain)
        self.assertIn('new Float32Array([-1, 0, 0, 1, 0, 0, -1, 1, 0, 1, 1, 0]), 3)', rain)
        for k in ('Uint8Array', 'Int8Array', 'Uint16Array'):
            self.assertNotIn(k, rain)
        snow = cut(self.s, '  if (REAL) {\n    const seed = new Float32Array(SNOW_N * 3), ph = new Float32Array(SNOW_N);', '    snowMesh = new THREE.Points(g, m);')
        self.assertNotIn('Uint8Array', snow)

    def test_the_halo_leaves_the_bloom_mask_alone(self):
        f = cut(self.s, '  function wxHaloMesh() {', '\n  }\n')
        self.assertIn('blendSrcAlpha: THREE.ZeroFactor, blendDstAlpha: THREE.OneFactor', f)
        self.assertIn('new THREE.Points(poleGlow.geometry, m)', f)     # the lamps' own buffers, nothing copied

    def test_the_glints_know_each_lamps_colour(self):
        # beside the computer's own inventory (keepInv): a phone keeps neither (test_memory_cuts' FreedArrays)
        lamps = cut(self.s, "  step('Lighting the streetlamps'", "  step('Fitting out the rooftops'")
        self.assertIn('if (keepInv && REAL) wxLampCol(pcol);', lamps)
        f = cut(self.s, '  function wxGlintStep(now, dt) {', '\n  }\n')
        self.assertIn('pinOccAnswer(inv.X[i], inv.GY[i] + inv.HM[i], inv.Z[i]) === 0', f)   # a building in front: no glint
        self.assertIn('wxSurfU.uWet.value > 0.02', f)

    def test_rain_quads_draw_either_winding(self):
        # the quad's frame (across, along) turns with the streak, so half the streaks were back faces and culled
        self.assertIn('uniforms: rainU, side: THREE.DoubleSide', self.s)


class GlintLobe(unittest.TestCase):
    """The lamps' streaks: the shader's anisotropic GGX, evaluated over the wet ground for an eye 3 m up and a 9 m lamp
    40 m ahead. The bright footprint must run along the line of sight, several times longer than it is wide."""

    def lobe(self, x, z, a=0.14):
        eye, lamp = (0.0, 3.0, 0.0), (0.0, 9.0, 40.0)
        V = [eye[0] - x, eye[1], eye[2] - z]
        lv = math.sqrt(sum(c * c for c in V)); V = [c / lv for c in V]
        L = [lamp[0] - x, lamp[1], lamp[2] - z]
        d2 = sum(c * c for c in L); ll = math.sqrt(d2); L = [c / ll for c in L]
        H = [L[i] + V[i] for i in range(3)]; hl = math.sqrt(sum(c * c for c in H)); H = [c / hl for c in H]
        t = (V[0], V[2]); tl = math.hypot(*t) or 1e-9; t = (t[0] / tl, t[1] / tl)
        ax, ay = a * 1.9, a * 0.7
        hz, hx, hy = H[1], H[0] * t[0] + H[2] * t[1], H[0] * -t[1] + H[2] * t[0]
        k = hx * hx / (ax * ax) + hy * hy / (ay * ay) + hz * hz
        F = 0.02 + 0.98 * (1 - max(0.0, min(1.0, sum(L[i] * H[i] for i in range(3))))) ** 5
        return F / (math.pi * ax * ay * k * k * 4 * max(V[1], 0.03) * d2)

    def test_the_streak_runs_toward_the_eye(self):
        zs = [z * 0.25 for z in range(4, 160)]
        along = [self.lobe(0.0, z) for z in zs]
        peak = max(along); zp = zs[along.index(peak)]
        self.assertGreater(zp, 4); self.assertLess(zp, 30)      # the mirror point lies between the eye and the lamp
        long = [z for z, v in zip(zs, along) if v > peak * 0.5]
        xs = [x * 0.05 for x in range(-100, 101)]
        wide = [x for x in xs if self.lobe(x, zp) > peak * 0.5]
        self.assertGreater((max(long) - min(long)) / (max(wide) - min(wide)), 3.0)

    def test_a_puddle_is_a_sharper_mirror(self):
        film = max(self.lobe(0.0, z * 0.25) for z in range(4, 160))
        pud = max(self.lobe(0.0, z * 0.25, a=0.035) for z in range(4, 160))
        self.assertGreater(pud, film * 4)


class Grade(unittest.TestCase):
    def test_the_weather_rides_on_the_owners_base(self):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        s = (ROOT / 'app.js').read_text()
        src = cut(s, '  const WXG = {', '\n  // the lamps\' inventory colour')
        script = '''
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const WX = { cover: 0.5 };
const postComp = { uniforms: { uBloom: { value: 0.45 } } };
const gradeU = { uSat: { value: 0.84 }, uCon: { value: 1.05 } };
''' + src + '''
const out = [];
const rain = { rain: 1, snow: 0, fog: 0 }, dry = { rain: 0, snow: 0, fog: 0 };
wxGrade(rain, 1); out.push([postComp.uniforms.uBloom.value, gradeU.uSat.value, gradeU.uCon.value]);
wxGrade(rain, 1); out.push([postComp.uniforms.uBloom.value, gradeU.uSat.value, gradeU.uCon.value]);   // no compounding
gradeU.uSat.value = 0.9;                                                                             // the owner retunes it
wxGrade(dry, 0); out.push([postComp.uniforms.uBloom.value, gradeU.uSat.value, gradeU.uCon.value]);
console.log(JSON.stringify(out));
'''
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b, c = json.loads(r.stdout)
        self.assertAlmostEqual(a[0], 0.8)                 # 0.45 + 0.35 by a rainy night
        self.assertAlmostEqual(a[1], 0.84 * 0.8)
        self.assertAlmostEqual(a[2], 1.05 - 0.08)
        self.assertEqual(a, b)
        self.assertAlmostEqual(c[0], 0.45)                # dry again: the base, never the weather's value
        self.assertAlmostEqual(c[1], 0.9)                 # and the owner's new base kept
        self.assertAlmostEqual(c[2], 1.05)


if __name__ == '__main__':
    unittest.main()
