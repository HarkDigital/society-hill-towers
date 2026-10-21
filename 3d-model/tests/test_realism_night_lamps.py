"""The realism round, night-lamps (night#0, night#5, streets#10, weather#10; Mike: "make this look more photo realistic
and less cartoony").

At 5.9 m a texel the light map could not hold a pool, so poles 30 to 40 m apart merged into one even wash and a street at
night read like an overcast day. A near map (LAMPNEAR) is drawn from the same splats with a pool's own shape round a point
ahead of the eye, each lamp scaled to put on the ground what its far splat puts there; the surfaces read it within a
gliding circle, under an irradiance shoulder, and a wall reads the ground in front of itself up to about the height of the
heads. The luminaires stand where the meshes put them (the glow at the head, the arm over the street), the survey's pole
families are drawn (the lanterns, the wood poles; pole_families.json beside poles.b64, which stays as committed), with
lit lenses and a lens-sized glare. The wet air's halos, bloom and grade (weather#10) are realism/weather's alone
(wxHaloMesh, wxGrade): this branch writes none of the composite's uniforms and grows no halo. ?real=0 keeps Round 146's
wash and the shaft-top glow.

Checked here: the families' bake and its alignment with poles.b64, the near kernel's energy against the far splat's (the
shader's own formula, the shader's own constants), the arm's yaw convention against three's own rotation, the near map's
orientation, the glare's shape and its fog, the 8-bit map's rounding, and the wiring (REAL gates, the far map's shared
gain, phones, the old path kept whole)."""
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class Families(unittest.TestCase):
    def test_the_bake_maps_the_survey_types(self):
        import bake_pole_families as P
        for t in ('FLP', 'C13', 'PTF', 'PTC', 'CCP'):
            self.assertEqual(P.family(t), 1, t)        # the post-top lanterns
        for t in ('WP', 'AEL'):
            self.assertEqual(P.family(t), 2, t)        # the wood and alley poles
        for t in ('SLA', 'SLF', 'D30', 'SNP', 'MAP', 'C20'):
            self.assertEqual(P.family(t), 0, t)        # the metal standards with a cobra head or a davit
        self.assertEqual(P.family('OTH'), 3)
        self.assertEqual(P.family('nonsense'), 3)

    def test_the_sidecar_lines_up_with_poles_b64(self):
        import base64
        import struct
        fam = json.loads((ROOT / 'pole_families.json').read_text())
        raw = base64.b64decode((ROOT / 'poles.b64').read_text().strip())
        n = struct.unpack('<2i', raw[:8])[1]
        self.assertEqual(fam['n'], n, 'pole_families.json was baked against another poles.b64: rerun bake_pole_families.py')
        self.assertEqual(fam['bits'], 2)
        packed = base64.b64decode(fam['b64'])
        self.assertEqual(len(packed), (n + 3) // 4)
        codes = [(packed[i >> 2] >> ((i & 3) * 2)) & 3 for i in range(n)]
        self.assertEqual([codes.count(k) for k in range(4)], fam['counts'])
        self.assertGreater(fam['counts'][1], 10000)     # the lanterns of Old City, Society Hill and the Avenue of the Arts
        self.assertGreater(fam['counts'][2], 100000)    # the wood poles of the rowhouse streets
        self.assertGreater(fam['counts'][0], 40000)     # the cobra heads and davits
        # Head House Square's Franklin lanterns (FLP, 15 ft) are lanterns; the n02 rowhouse street's are wood poles
        body = struct.unpack('<%dh' % (3 * n), raw[16:16 + 6 * n])
        def near(cx, cz, r):
            return [codes[i] for i in range(n) if (body[3 * i] * 0.7 - cx) ** 2 + (body[3 * i + 1] * 0.7 - cz) ** 2 < r * r]
        hh = near(-42, 332, 30)
        self.assertGreater(hh.count(1), 0.7 * len(hh), hh)
        def at(cx, cz):   # the packed pole nearest a surveyed one
            i = min(range(n), key=lambda k: (body[3 * k] * 0.7 - cx) ** 2 + (body[3 * k + 1] * 0.7 - cz) ** 2)
            return codes[i]
        self.assertEqual(at(-1802.3, 1975.7), 2)   # a WP on the n02 rowhouse street
        self.assertEqual(at(-1778.2, 2003.9), 2)   # an AEL alley light beside it
        self.assertEqual(at(-1680.9, 383.0), 1)    # a PTF post top on the Avenue of the Arts

    def test_the_page_reads_them(self):
        s = (ROOT / 'app.js').read_text()
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("POLE_FAMILIES", text_of("pole_families.json", "null"))', b)
        self.assertIn("if (FAM && typeof POLE_FAMILIES !== 'undefined' && POLE_FAMILIES && POLE_FAMILIES.n === head[1]) {", s)
        self.assertIn('fam = famOf ? (famOf[i >> 2] >> ((i & 3) * 2)) & 3 : 0;', s)
        self.assertIn('headAt(i, REAL && fam !== 3 ? fam : 0);', s)   # other is drawn as a cobra head, and ?real=0 draws every pole as one


class NearKernel(unittest.TestCase):
    """The near splat puts the far splat's light on the ground: its integral over the disc equals 0.7307 in the splat's
    units, for every mounting height the page uses."""

    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        cls.sh = float(re.search(r'const LAMP_SH = ([\d.]+);', cls.s).group(1))
        cls.cut4 = float(re.search(r'const LAMP_CUT = ([\d.]+);', cls.s).group(1)) ** 4

    def far(self, d):
        return 0.8 * math.exp(-d * d * 1.9) * (1 - d * d)

    def near(self, d, q, vN):
        d2 = d * d
        rh = q * q * d2
        return vN * ((1 + rh) ** -1.5 * math.exp(-rh * rh / self.cut4) * (1 - d2 * d2) + self.sh * math.exp(-2.2 * d2) * (1 - d2))

    def vN(self, q):   # the vertex shader's 32 rings, exactly
        I = 0.0
        for k in range(32):
            u = (k + 0.5) / 32
            rh = q * q * u
            I += (1 + rh) ** -1.5 * math.exp(-rh * rh / self.cut4) * (1 - u * u) + self.sh * math.exp(-2.2 * u) * (1 - u)
        return 0.7307 / (I * math.pi / 32)

    def disc(self, f, n=4000):
        return sum(f((i + 0.5) / n) * 2 * math.pi * ((i + 0.5) / n) / n for i in range(n))

    def test_the_far_constant(self):
        self.assertAlmostEqual(self.disc(self.far), 0.7307, places=3)

    def test_each_lamp_keeps_its_light(self):
        # q = the splat's radius over the luminaire's height: a 25 ft cobra (26 m over 7.45 m), a 15 ft lantern (15.6 over
        # 4.6), a lot mast (56 over 14.7), a pier lamp (20 over 6.9), a short alley light (14 over 3.6)
        for q in (3.49, 3.39, 3.8, 2.9, 3.9, 5.6):
            vN = self.vN(q)
            got = self.disc(lambda d: self.near(d, q, vN))
            self.assertLess(abs(got / 0.7307 - 1), 0.03, 'q %.2f: %.4f' % (q, got))

    def test_a_pool_and_a_gap(self):
        # poles 30 m apart along one side of a street, 26 m splats from 7.45 m heads: the near map's light under a head is
        # several times the light midway, where the far map's was flat (Round 144's plateau, night#0's evidence)
        q, R = 26 / 7.45, 26.0
        vN = self.vN(q)
        def line(f, x):
            return sum(f(abs(x - p) / R) for p in (-60, -30, 0, 30, 60) if abs(x - p) < R)
        n_peak, n_gap = line(lambda d: self.near(d, q, vN), 0), line(lambda d: self.near(d, q, vN), 15)
        f_peak, f_gap = line(self.far, 0), line(self.far, 15)
        # the cut-off (a full cut-off head: nothing much past 1.8 heads' heights) takes the street between two pools down to
        # well under a fifth of the light under a head, where the plain cosine-cubed core left about a third
        self.assertGreater(n_peak / n_gap, 6.0)
        self.assertLess(f_peak / f_gap, 1.6)
        s = self.s
        self.assertIn("vN = 0.7307 / (I * 3.14159265 / 32.0); } }", s)
        self.assertIn("float u = (float(k) + 0.5) / 32.0, rh = vQ * vQ * u; I += pow(1.0 + rh, -1.5) * exp(-rh * rh / uCut4) * (1.0 - u * u) + uSh * exp(-2.2 * u) * (1.0 - u); }", s)
        self.assertIn("float d2 = d * d, rh = vQ * vQ * d2; float f = vN * (pow(1.0 + rh, -1.5) * exp(-rh * rh / uCut4) * (1.0 - d2 * d2) + uSh * exp(-2.2 * d2) * (1.0 - d2));", s)
        self.assertIn("uSh: { value: LAMP_SH }, uCut4: { value: LAMP_CUT ** 4 } }", s)

    def test_the_pool_is_mostly_under_the_head(self):
        # a 25 ft cobra (26 m splat, 7.45 m head): most of its light lands within two heads' heights of the pole, and very
        # little past 2.5 (where the plain core still put a fifth of it)
        q, R = 26 / 7.45, 26.0
        vN = self.vN(q)
        tot = self.disc(lambda d: self.near(d, q, vN))
        inner = self.disc(lambda d: self.near(d, q, vN) if d * R < 2 * 7.45 else 0.0)
        outer = self.disc(lambda d: self.near(d, q, vN) if d * R > 2.5 * 7.45 else 0.0)
        self.assertGreater(inner / tot, 0.6)
        self.assertLess(outer / tot, 0.2)

    def test_only_the_lamps_in_the_near_map_integrate(self):
        # the 32 rings run per lamp in the vertex shader; a lamp whose centre lies outside the near map is clipped whole, so
        # it skips them (a twentieth of the city's lamps fall inside the 640 m map)
        self.assertIn("if (uNear > 0.5 && max(abs(gl_Position.x), abs(gl_Position.y)) <= gl_Position.w) {", self.s)
        # and the far splat is Round 144's, untouched
        self.assertIn('float f = 0.8 * exp(-d * d * 1.9) * (1.0 - d * d); gl_FragColor = vec4(vCol * f * uStore, 1.0); }', self.s)


class Geometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def node(self, script):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        script = 'const THREE = require(' + json.dumps(str(ROOT / 'three.min.js')) + ');\n' + script
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_arm_reaches_the_street(self):
        # poleArmRot's yaw, atan2(-dz, dx), turns the mesh's +x (the arm) toward (dx, dz) under three's own rotation
        out = self.node(r'''
const up = new THREE.Vector3(0, 1, 0), q = new THREE.Quaternion(), worst = [];
for (const [dx, dz] of [[1, 0], [0, 1], [-1, 0], [0, -1], [3, -4], [-5, 2]]) {
  q.setFromAxisAngle(up, Math.atan2(-dz, dx));
  const v = new THREE.Vector3(1, 0, 0).applyQuaternion(q), L = Math.hypot(dx, dz);
  worst.push(Math.hypot(v.x - dx / L, v.z - dz / L));
}
console.log(JSON.stringify(worst));''')
        for e in out:
            self.assertLess(e, 1e-6)
        self.assertIn('return Math.atan2(-dz, dx);', self.s)
        self.assertIn('const s = SRG.n ? septaSnapRoad(x, z, 26) : null;', self.s)
        # and the glow, the glare and the splat stand at the head the mesh draws: cos(rot) along x, -sin(rot) along z
        self.assertIn('pos[i * 3] = X[i] + Math.cos(r) * POLE_HEAD.arm; pos[i * 3 + 1] = GY[i] + POLE_HEAD.y * HM[i] / 9; pos[i * 3 + 2] = Z[i] - Math.sin(r) * POLE_HEAD.arm;', self.s)
        self.assertIn('gp[q * 3] = poleInv.X[i] + Math.cos(rot) * arm;', self.s)
        self.assertIn('gp[q * 3 + 2] = poleInv.Z[i] - Math.sin(rot) * arm;', self.s)
        self.assertIn('lp[m * 3] = pos[i * 3]; lp[m * 3 + 1] = pos[i * 3 + 1] - GY[i]; lp[m * 3 + 2] = pos[i * 3 + 2];', self.s)

    def test_the_near_map_reads_where_it_was_drawn(self):
        out = self.node(r'''
const S = 640, cx = -1640, cz = 1920;
const cam = new THREE.OrthographicCamera(-S / 2, S / 2, S / 2, -S / 2, 1, 4000);
cam.up.set(0, 0, -1); cam.position.set(cx, 2000, cz); cam.lookAt(cx, 0, cz); cam.updateMatrixWorld();
const out = [];
for (const [x, z] of [[cx, cz], [cx + 250, cz], [cx, cz + 250], [cx - 300, cz - 100], [cx + 310, cz - 310]]) {
  const p = new THREE.Vector3(x, 0, z).project(cam);
  const box = [cx - S / 2, cz - S / 2, 1 / S];
  const sh = [(x - box[0]) * box[2], 1 - (z - box[1]) * box[2]];
  out.push(Math.max(Math.abs((p.x + 1) / 2 - sh[0]), Math.abs((p.y + 1) / 2 - sh[1])));
}
console.log(JSON.stringify(out));''')
        for e in out:
            self.assertLess(e, 1e-6)
        upd = cut(self.s, '  function lampNearUpdate() {', '  function lampLightPatch(')
        self.assertIn("N.cam.up.set(0, 0, -1);", upd)
        self.assertIn("N.cam.position.set(cx, 2000, cz); N.cam.lookAt(cx, 0, cz);", upd)
        self.assertIn("U.uLampNearBox.value.set(cx - S / 2, cz - S / 2, 1 / S, LAMP_GAIN / N.store);", upd)
        self.assertIn("vec4 lnm = texture2D(uLampNear, vec2((lsp.x - uLampNearBox.x) * uLampNearBox.z, 1.0 - (lsp.y - uLampNearBox.y) * uLampNearBox.z));", self.s)


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def node(self, script):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        script = 'const THREE = require(' + json.dumps(str(ROOT / 'three.min.js')) + ');\n' + script
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_real_gates_the_new_look_and_keeps_the_old(self):
        s = self.s
        self.assertIn('const LAMPNEAR = { on: REAL,', s)
        self.assertIn('if (REAL) { lampLightPatchReal(shader, worldExpr, mode); return; }', s)
        # ?real=0 keeps Round 146's wash, word for word
        old = cut(s, '  function lampLightPatch(', '  function lampLightPatchReal(')
        self.assertIn("0.75 * mix(0.3, 1.0, 1.0 - smoothstep(0.35, 0.7, abs(vWNorm.y))) * (1.0 - smoothstep(3.0, 16.0, lwp.y - vBase))", old)
        self.assertIn('totalEmissiveRadiance += min(la, vec3(0.5)) + lo / (1.0 + lo * 2.0);', old)
        # the near meshes, the lenses and the glare only in the realistic look; since Round 205 a phone's too (every tier since Round 218)
        self.assertIn('if (REAL) polesRealBuild(maxPtOf());', cut(s, '    if (POLE_MESH_CAP > 0) {', '    poleInv = keepInv'))
        self.assertIn('const POLE_MESH_CAP = isTouch ? 500 : 1600;', s)
        # ?real=0 keeps the shaft-top glow, the far splats where they were and the hashed arms: headAt does nothing there,
        # and the inventory carries no families or colours
        self.assertIn('if (!ROT || !REAL) return;', s)
        self.assertIn('const FAM = keepInv && REAL ? new Uint8Array(nAll) : null, PC = keepInv && REAL ? new Uint8Array(nAll * 3) : null;', s)

    def test_the_far_map_gain_is_the_shared_contract(self):
        # uLampBox.w is LAMP_GAIN over the store and nothing else: realism/weather's wet-street glints and canyons and its
        # lamp-lit rain and snow read it as the lamps' gain. The realistic patch takes LAMP_REAL_K through uLampReal.y, and
        # the landmark rebuilds through a box of their own
        s = self.s
        far = cut(s, '  function lampMapUpdate() {', '  const _lmDir')
        self.assertIn('lampMapU.uLampBox.value.set(cx - S / 2, cz - S / 2, 1 / S, LAMP_GAIN / LAMPMAP.store);', far)
        self.assertEqual(far.count('uLampBox.value'), 1)
        near = cut(s, '  function lampNearUpdate() {', '  function lampLightPatch(')
        self.assertNotIn('lampK', far + near)
        self.assertIn('lnm.rgb * uLampNearBox.w, nw) * (uLampReal.y * uLampOn * lf);', s)
        self.assertIn('U.uLampReal.value.set(N.rt ? hk : 0, LAMP_REAL_K, 0, 0);', near)
        self.assertIn('const lampK = () => (REAL ? LAMP_REAL_K : 1);', s)
        self.assertIn('const LAMP_RB_U = { uLampMap: lampMapU.uLampMap, uLampBox: { value: new THREE.Vector4(0, 0, 1 / 12000, 0) }, uLampOn: lampMapU.uLampOn, uLampFade: lampMapU.uLampFade };', s)
        self.assertIn('    api.lampU = LAMP_RB_U;', cut(s, "  step('Rebuilding the landmarks'", '    for (const d of REBUILDS) {'))
        fx = cut(s, '  function lampNightFx(', '  // ---------------------------------------------------------------- skyline lights')
        self.assertIn('LAMP_RB_U.uLampBox.value.copy(lampMapU.uLampBox.value);\n    LAMP_RB_U.uLampBox.value.w *= lampK();', fx)
        # nothing else writes the far map's own box
        writes = re.findall(r'(?<!LAMP_RB_U\.)uLampBox\.value\.(?:set\(|w\s*[*+/-]?=|copy\(|multiplyScalar\()', s)
        self.assertEqual(len(writes), 1, writes)
        # and the rebuilds read only what their box carries
        for f in ('esp.js', 'rtm.js'):
            rb = (ROOT / 'rebuilds' / f).read_text()
            self.assertIn('uLampBox', rb)
            self.assertNotIn('uLampReal', rb)

    def test_the_wall_reads_the_ground_in_front_and_spares_the_glass(self):
        real = cut(self.s, '  function lampLightPatchReal(', '  function surfTexPatch(')
        self.assertIn("vec2 lsp = lwp.xz' + (wall ? ' + vWNorm.xz * 2.5' : '') + ';'", real)
        self.assertIn("fs.indexOf('float shtGlass') !== -1 ? 'shtGlass' : fs.indexOf('vec4 frMask;') !== -1 ? 'frMask.r' : fs.indexOf('vec4 tsMask;') !== -1 ? 'tsMask.r' : '0.0'", real)
        self.assertIn('(1.0 - 0.9 * clamp(', real)
        self.assertIn("float lHl = mix(8.0, 16.0 * lnm.a / max(lnl, 1e-5), nw * step(1e-5, lnl));", real)
        # the glass masks those shaders declare, where the patch looks for them
        self.assertIn("'float shtGlass = 0.0;',", self.s)
        self.assertIn('varying float vBase; varying vec4 vFrR, vFrT; varying vec3 vFrSun; vec4 frMask;', self.s)   # the fronts' own declaration (the realism pass's fronts)

    def test_the_near_map_is_mipmapped_and_cleared_to_no_height(self):
        upd = cut(self.s, '  function lampNearUpdate() {', '  function lampLightPatch(')
        self.assertIn('generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter', upd)
        # half float wherever the device draws into it, a phone too (8 bits rounded each channel apart: coloured blotches on
        # a pale pavement), and the 8-bit map where the half-float target will not complete
        self.assertIn("N.half = caps.isWebGL2 && (ext.has('EXT_color_buffer_float') || ext.has('EXT_color_buffer_half_float'));", upd)
        self.assertIn("if (!done) { N.rt.dispose(); N.half = false; N.rt = mk(false); }", upd)
        self.assertIn("N.store = N.half ? 1 : 0.12;", upd)
        self.assertLess(upd.index('if (!done)'), upd.index('N.store = N.half ? 1 : 0.12;'))
        self.assertIn("mu.uDither.value = N.half ? 0 : 1 / 255;", upd)
        self.assertIn("r.setClearColor(0x000000, 0);", upd)
        # the splats' uniforms go back to the far map's after the near pass
        self.assertIn('mu.uNear.value = 0; mu.uPxPerM.value = LAMPMAP.size / LAMPMAP.span; mu.uStore.value = LAMPMAP.store; mu.uDither.value = 0;', upd)
        # and it is drawn first, never skipped by the far map's own early return
        far = cut(self.s, '  function lampMapUpdate() {', '  const _lmDir')
        self.assertLess(far.index('if (LAMPNEAR.on) lampNearUpdate();'), far.index('if (LAMPMAP.rt && cx === LAMPMAP.cx && cz === LAMPMAP.cz) return;'))

    def test_wet_air(self):
        # the lights in wet air are the weather's alone (wxHaloMesh, wxGrade): the night pass's own halo, its grown glare and
        # its grade doubled every halo and, reading the grade's base once, kept a rainy load's lowered grade for the session
        fx = cut(self.s, '  function lampNightFx(', '  // ---------------------------------------------------------------- skyline lights')
        for k in ('lampHaloU', 'gradeU', 'uBloom', 'WXFX'):
            self.assertNotIn(k, fx)
        self.assertNotIn('uLampHalo', self.s)
        self.assertIn("'#include <color_fragment>\\n\\tdiffuseColor.a *= smoothstep(0.5, 0.08, length(gl_PointCoord - vec2(0.5)));'", self.s)

    def test_the_wet_air_is_weathers(self):
        # weather#10 has one owner, realism/weather (wxGrade, wxHaloMesh): this branch writes none of the composite's
        # uniforms (two hooks each taking the other's output as its base ran the grade away within frames), grows no halo
        # on the glow, and keeps the glare a lens's in every weather
        s = self.s
        fx = cut(s, '  function lampNightFx(', '  // ---------------------------------------------------------------- skyline lights')
        for w in ('gradeU', 'uBloom', 'uSat', 'uCon', 'WXFX', 'F.fog', 'F.rain'):
            self.assertNotIn(w, fx)
        for w in ('lampHaloU', 'uLampHalo', 'LAMP_GRADE0', 'uGlare.z', 'uGlare.w'):
            self.assertNotIn(w, s)
        # the glow is Round 54's sprite again
        self.assertIn("'#include <color_fragment>\\n\\tdiffuseColor.a *= smoothstep(0.5, 0.08, length(gl_PointCoord - vec2(0.5)));');", s)
        self.assertIn('glareU: { value: new THREE.Vector2(500, 0.8) }', s)

    def test_the_glare_has_no_rim(self):
        # the glare's shape rides the alpha and falls to nothing inside the sprite: no cut at a rim, under a hundredth of a
        # percent of its peak at the circle, falling all the way out to it
        s = self.s
        self.assertIn("vec2 gq = gl_PointCoord - vec2(0.5); float gr2 = dot(gq, gq) * 4.0, gt = max(1.0 - gr2, 0.0);", s)
        self.assertIn("diffuseColor.a *= (0.42 * exp(-gr2 * 12.0) + 0.05 * exp(-gr2 * 3.5) * gt * gt) * vGa;", s)
        self.assertNotIn('smoothstep(0.8, 1.0, gr)', s)

        def f(r):
            r2 = r * r
            return 0.42 * math.exp(-r2 * 12) + 0.05 * math.exp(-r2 * 3.5) * max(1 - r2, 0) ** 2
        self.assertLess(f(1.0) / f(0.0), 1e-4)
        self.assertLess(f(1.41) / f(0.0), 1e-8)   # the sprite's corners
        prev = f(0.0)
        for i in range(1, 101):
            v = f(i / 100)
            self.assertLess(v, prev)
            prev = v

    def test_the_fog_dims_the_glare_and_adds_no_grey(self):
        # the fog chunk's mix put the fog's colour across the whole sprite (a grey ball with a rim round every near lamp on a
        # fog night); the glare takes the fog as extinction instead, on three's own chunk and on an aerial-perspective chunk
        # that mixes toward its own colour (realism/sky-atmos's), and drops fog on a chunk it cannot read
        line = next(l for l in self.s.splitlines() if 'const fogMul = THREE.ShaderChunk.fog_fragment.replace(' in l)
        rx = re.search(r'\.replace\((/.*/), ', line).group(1)
        out = self.node('const rx = ' + rx + ''';
const sky = ['#ifdef USE_FOG', '\\tvec3 fogMix = fogColor;', '\\tif ( fogAP.w > 0.5 ) { fogFactor = 1.0; }',
  '\\tgl_FragColor.rgb = mix( gl_FragColor.rgb, fogMix, fogFactor );', '#endif'].join('\\n');
console.log(JSON.stringify([THREE.ShaderChunk.fog_fragment, sky].map((c) => {
  const m = c.replace(rx, 'gl_FragColor.rgb *= 1.0 - fogFactor;');
  return [m.includes('gl_FragColor.rgb *= 1.0 - fogFactor;'), /mix\\(/.test(m)];
})));''')
        self.assertEqual(out, [[True, False], [True, False]])
        self.assertIn(".replace('#include <fog_fragment>', fogMul.indexOf('*= 1.0 - fogFactor;') !== -1 ? fogMul : '');", self.s)

    def test_the_8bit_rounding_keeps_the_mean(self):
        # the 8-bit fallback rounds each splat up or down by its own remainder: the expected value is the splat's own, the
        # dark gap's tiny values included, and never below zero
        self.assertIn("if (uDither > 0.0) o = floor(o * 255.0 + fract(sin(dot(gl_FragCoord.xy + vec2(vH * 7.13, vQ * 3.71), vec2(12.9898, 78.233))) * 43758.5453)) / 255.0;", self.s)
        n = 4096
        for v in (0.0, 0.0004, 0.0021, 0.013, 0.2, 0.71):
            vals = [math.floor(v * 255 + (k + 0.5) / n) for k in range(n)]
            self.assertGreaterEqual(min(vals), 0)
            self.assertLess(abs(sum(vals) / 255 / n - v), 1e-4, v)

    def test_a_phone_holds_its_near_map(self):
        s = self.s
        # 256 px over 400 m on a phone: 0.7 MB in half float with its mips
        self.assertIn('size: isTouch ? 256 : 1024, span: isTouch ? 400 : 640,', s)
        self.assertIn('const LAMP_NEAR_EVERY = isTouch ? 250 : 0;', s)
        upd = cut(s, '  function lampNearUpdate() {', '  function lampLightPatch(')
        hold = 'if (N.rt && LAMP_NEAR_EVERY && now - N.at < LAMP_NEAR_EVERY && Math.max(Math.abs(cx - N.cx), Math.abs(cz - N.cz)) <= 2 * step) {'
        self.assertIn(hold, upd)
        # the circle stays within a step of the held map's centre (radius S/2 - step: it never reads past the edge)
        self.assertIn('U.uLampNearFade.value.x = clamp(ax, N.cx - step, N.cx + step); U.uLampNearFade.value.y = clamp(az, N.cz - step, N.cz + step);', upd)
        self.assertLess(upd.index('if (N.rt && cx === N.cx && cz === N.cz) return;'), upd.index(hold))
        self.assertLess(upd.index(hold), upd.index('if (!N.rt) {'))
        self.assertIn('N.cx = cx; N.cz = cz; N.renders++; N.at = now;', upd)

    def test_no_dash_in_user_strings(self):
        block = cut(self.s, '  const LAMPNEAR = {', '  const LOT_CENTER')
        for line in block.splitlines():
            for q in re.findall(r"'([^']*)'", line):
                self.assertNotIn('—', q)
                self.assertNotIn('·', q)


if __name__ == '__main__':
    unittest.main()
