"""The realism round, night-lamps (night#0, night#5, streets#10, weather#10; Mike: "make this look more photo realistic
and less cartoony").

At 5.9 m a texel the light map could not hold a pool, so poles 30 to 40 m apart merged into one even wash and a street at
night read like an overcast day. A near map (LAMPNEAR) is drawn from the same splats with a pool's own shape round a point
ahead of the eye, each lamp scaled to put on the ground what its far splat puts there; the surfaces read it within a
gliding circle, under an irradiance shoulder, and a wall reads the ground in front of itself up to about the height of the
heads. The luminaires stand where the meshes put them (the glow at the head, the arm over the street), the survey's pole
families are drawn (the lanterns, the wood poles; pole_families.json beside poles.b64, which stays as committed), with lit lenses and glare, and wet air puts a halo on every lamp and
takes some saturation and contrast out of the grade. ?real=0 keeps Round 146's wash.

Checked here: the families' bake and its alignment with poles.b64, the near kernel's energy against the far splat's (the shader's own formula, the
shader's own constants), the arm's yaw convention against three's own rotation, the near map's orientation, and the wiring
(REAL gates, phones, the old path kept whole)."""
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

    def far(self, d):
        return 0.8 * math.exp(-d * d * 1.9) * (1 - d * d)

    def near(self, d, q, vN):
        d2 = d * d
        return vN * ((1 + q * q * d2) ** -1.5 * (1 - d2 * d2) + self.sh * math.exp(-2.2 * d2) * (1 - d2))

    def vN(self, q):   # the vertex shader's 32 rings, exactly
        I = 0.0
        for k in range(32):
            u = (k + 0.5) / 32
            I += (1 + q * q * u) ** -1.5 * (1 - u * u) + self.sh * math.exp(-2.2 * u) * (1 - u)
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
        self.assertGreater(n_peak / n_gap, 3.5)
        self.assertLess(f_peak / f_gap, 1.6)
        s = self.s
        self.assertIn("vN = 0.7307 / (I * 3.14159265 / 32.0); }", s)
        self.assertIn("I += pow(1.0 + vQ * vQ * u, -1.5) * (1.0 - u * u) + ' + LAMP_SH.toFixed(3) + ' * exp(-2.2 * u) * (1.0 - u); }", s)
        self.assertIn("float f = vN * (pow(1.0 + vQ * vQ * d2, -1.5) * (1.0 - d2 * d2) + ' + LAMP_SH.toFixed(3) + ' * exp(-2.2 * d2) * (1.0 - d2));", s)
        # and the far splat is Round 144's, untouched
        self.assertIn('float f = 0.8 * exp(-d * d * 1.9) * (1.0 - d * d); gl_FragColor = vec4(vCol * f * uStore, 1.0); }', s)


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

    def test_real_gates_the_new_look_and_keeps_the_old(self):
        s = self.s
        self.assertIn('const LAMPNEAR = { on: REAL && !LITE,', s)
        self.assertIn('if (REAL) { lampLightPatchReal(shader, worldExpr, mode); return; }', s)
        # ?real=0 keeps Round 146's wash, word for word
        old = cut(s, '  function lampLightPatch(', '  function lampLightPatchReal(')
        self.assertIn("0.75 * mix(0.3, 1.0, 1.0 - smoothstep(0.35, 0.7, abs(vWNorm.y))) * (1.0 - smoothstep(3.0, 16.0, lwp.y - vBase))", old)
        self.assertIn('totalEmissiveRadiance += min(la, vec3(0.5)) + lo / (1.0 + lo * 2.0);', old)
        # the near meshes, the lenses and the glare only on a computer and only in the realistic look
        self.assertIn('if (REAL) polesRealBuild(maxPtOf());', cut(s, '    if (POLE_MESH_CAP > 0) {', '    poleInv = keepInv'))
        self.assertIn('const POLE_MESH_CAP = isTouch ? 0 : 1600;', s)
        # the landmark rebuilds read the far map with LAMP_GAIN alone, so the realistic strength rides its own uniform
        self.assertIn('lampMapU.uLampBox.value.set(cx - S / 2, cz - S / 2, 1 / S, LAMP_GAIN / LAMPMAP.store);', s)
        self.assertIn('(uLampReal.y * uLampOn * lf)', s)

    def test_the_wall_reads_the_ground_in_front_and_spares_the_glass(self):
        real = cut(self.s, '  function lampLightPatchReal(', '  function surfTexPatch(')
        self.assertIn("vec2 lsp = lwp.xz' + (wall ? ' + vWNorm.xz * 2.5' : '') + ';'", real)
        self.assertIn("fs.indexOf('float shtGlass') !== -1 ? 'shtGlass' : fs.indexOf('vec4 frMask;') !== -1 ? 'frMask.r' : fs.indexOf('vec4 tsMask;') !== -1 ? 'tsMask.r' : '0.0'", real)
        self.assertIn('(1.0 - 0.9 * clamp(', real)
        self.assertIn("float lHl = mix(8.0, 16.0 * lnm.a / max(lnl, 1e-5), nw * step(1e-5, lnl));", real)
        # the glass masks those shaders declare, where the patch looks for them
        self.assertIn("'float shtGlass = 0.0;',", self.s)
        self.assertIn('varying float vBase; vec4 frMask;', self.s)

    def test_the_near_map_is_mipmapped_and_cleared_to_no_height(self):
        upd = cut(self.s, '  function lampNearUpdate() {', '  function lampLightPatch(')
        self.assertIn('generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter', upd)
        self.assertIn("N.half = !isTouch && caps.isWebGL2", upd)
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
        self.assertIn('u.y = 1.6; u.w = 1;', fx)
        self.assertNotIn('uLampHalo', self.s)
        self.assertIn("'#include <color_fragment>\\n\\tdiffuseColor.a *= smoothstep(0.5, 0.08, length(gl_PointCoord - vec2(0.5)));'", self.s)

    def test_no_dash_in_user_strings(self):
        block = cut(self.s, '  const LAMPNEAR = {', '  const LOT_CENTER')
        for line in block.splitlines():
            for q in re.findall(r"'([^']*)'", line):
                self.assertNotIn('—', q)
                self.assertNotIn('·', q)


if __name__ == '__main__':
    unittest.main()
