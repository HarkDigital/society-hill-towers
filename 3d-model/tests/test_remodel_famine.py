"""Round 197 (Mike: "The irish famine memorial needs to look more realistic. lookup photos of it. There is a boat. Also put an
irish flag on a flagpole to the northeast of it."). Glenna Goodacre's memorial rebuilt from the photographs at Mike's place
(84, 104) and heading: a granite plinth on a dark paved circle, the planked ship with its gunwale, stem, wales, porthole and
ribs, the gangway, the famine's rock with its cross and gravestones, and thirty-one people and four children as smooth
sculpted forms in a patinated bronze. The Irish tricolour flies on the wind from a 9.5 m aluminium pole to the north-east.
The forms are cut from app.js and built under Node: the figure count, the budget near and far, the streams, the rock kept on
the plinth, the pole clear of the plinth, the paths, the buildings and the trees. ?real=0 keeps Round 129's memorial."""
import json
import math
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent
A = (ROOT / 'app.js').read_text()


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


MOD = cut(A, '  // ---- The Irish Famine Memorial (Round 197', "  step('Restoring the landmarks', () => {")
FORMS = cut(A, '  // ---- The Irish Famine Memorial (Round 197', "  // the memorial's material:")

SCRIPT = r'''
const THREE = require(THREE_PATH);
__HASH__
__CHS__
__FORMS__
const tri = (g) => (g.index ? g.index.count : g.attributes.position.count) / 3;
const F = FAMINE, L0 = Math.hypot(F.sp1[0] - F.sp0[0], F.sp1[1] - F.sp0[1]), ux = (F.sp1[0] - F.sp0[0]) / L0, uz = (F.sp1[1] - F.sp0[1]) / L0;
const pu = (F.pole[0] - F.c[0]) * ux + (F.pole[1] - F.c[1]) * uz, pv = -(F.pole[0] - F.c[0]) * uz + (F.pole[1] - F.c[1]) * ux;
const ground = (u, v) => 0.04 * Math.sin(u * 0.4) - 0.02 * v;
const out = { pu, pv, ux, uz, figsList: FAM_FIGS.length, kids: FAM_KIDS };
for (const [k, lo, far] of [['near', false, false], ['phone', true, false], ['far', false, true]]) {
  const t0 = Date.now(), r = famineForms(lo, far, ground), pole = famPoleForms(pu, pv, 0.1, lo, far), g = famMerge(r.parts.concat(pole));
  const P = g.attributes.position.array, N = g.attributes.normal.array, K = g.attributes.aFm.array;
  let bad = 0, fin = true, outside = 0, topPole = -1e9;
  for (let i = 0; i < P.length / 3; i++) {
    if (!(Math.abs(Math.hypot(N[i * 3], N[i * 3 + 1], N[i * 3 + 2]) - 1) < 0.02)) bad++;
    for (let q = 0; q < 3; q++) if (!isFinite(P[i * 3 + q])) fin = false;
    const kind = K[i * 4], u = P[i * 3], v = P[i * 3 + 2];
    // every bronze stands on the plinth: inside its outline, a centimetre's grace
    if ((kind < 1.5 || kind > 7.5) && Math.hypot(u - pu, v - pv) > 2) { const [eu, ev] = famOutline(Math.atan2(v, u)); if (Math.hypot(u, v) > Math.hypot(eu, ev) + 0.01) outside++; }
    if (Math.hypot(u - pu, v - pv) < 0.2) topPole = Math.max(topPole, P[i * 3 + 1]);
  }
  const attrs = {}; for (const n in g.attributes) { const a = g.attributes[n]; attrs[n] = [a.array.constructor.name, a.itemSize]; }
  out[k] = { tris: tri(g), figs: r.figs, bad, fin, outside, topPole: topPole - 0.1, attrs, index: g.index.array.constructor.name, ms: Date.now() - t0 };
}
const fg = famFlagGeom(false), fp = fg.attributes.position.array, fa = fg.attributes.aFlag.array;
let x0 = 1e9, x1 = -1e9; for (let i = 0; i < fp.length; i += 3) { x0 = Math.min(x0, fp[i]); x1 = Math.max(x1, fp[i]); }
let s0 = 1e9, s1 = -1e9; for (let i = 0; i < fa.length; i += 2) { s0 = Math.min(s0, fa[i]); s1 = Math.max(s1, fa[i]); }
out.flag = { tris: tri(fg), phone: tri(famFlagGeom(true)), x0, x1, s0, s1, sphere: fg.boundingSphere.radius };
out.plinth = []; for (let k = 0; k < 32; k++) out.plinth.push(famOutline(k / 32 * Math.PI * 2));
console.log(JSON.stringify(out));
'''


class Forms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        script = (SCRIPT.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js')))
                  .replace('__HASH__', cut(A, '  function hash01(n)', '\n'))
                  .replace('__CHS__', cut(A, '  const CHS = {', '  // the figures, each a list'))
                  .replace('__FORMS__', FORMS))
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise AssertionError(r.stderr[-3000:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_figures(self):
        # thirty-one people and four children (a child on a hip, in a lap, on a father's shoulders), near and far
        o = self.o
        self.assertEqual(o['figsList'], 31)
        self.assertEqual(o['kids'], 4)
        for k in ('near', 'phone', 'far'):
            self.assertEqual(o[k]['figs'], 35, k)

    def test_the_budget(self):
        # the memorial, its pole and the flag within 25,000 triangles near, a phone's under 21,000, the far level under 2,000;
        # one indexed draw each (the far level past FAMINE.nearR), built in well under a second
        o = self.o
        self.assertLessEqual(o['near']['tris'] + o['flag']['tris'], 25000)
        self.assertGreater(o['near']['tris'], 18000)
        self.assertLessEqual(o['phone']['tris'] + o['flag']['phone'], 21000)
        self.assertLessEqual(o['far']['tris'], 2000)
        for k in ('near', 'phone', 'far'):
            self.assertLess(o[k]['ms'], 1500, k)
        self.assertIn("nearR: 250, hyst: 30", A)

    def test_the_streams(self):
        # four-byte streams only (Round 158): float positions, normals and the kind word; every normal unit, every point finite
        for k in ('near', 'phone', 'far'):
            m = self.o[k]
            self.assertEqual(m['attrs'], {'position': ['Float32Array', 3], 'normal': ['Float32Array', 3], 'aFm': ['Float32Array', 4]}, k)
            self.assertEqual(m['index'], 'Uint16Array', k)
            self.assertEqual(m['bad'], 0, k)
            self.assertTrue(m['fin'], k)

    def test_the_bronze_stands_on_the_plinth(self):
        # the rock's noise once pushed a lump through the plinth's skirt at the famine end: every bronze vertex inside the outline
        for k in ('near', 'phone', 'far'):
            self.assertEqual(self.o[k]['outside'], 0, k)

    def test_the_pole(self):
        # about 9.5 m of pole over its drum, the ball over that: 9.5 to 10.2 m above the ground
        for k in ('near', 'phone'):
            self.assertTrue(9.5 <= self.o[k]['topPole'] <= 10.2, self.o[k]['topPole'])
        # clear of the plinth and of the paved circle (11.5 by 8.2 m in the memorial's frame)
        pu, pv = self.o['pu'], self.o['pv']
        self.assertGreater((pu / 11.5) ** 2 + (pv / 8.2) ** 2, 1.2)
        d = min(math.hypot(pu - u, pv - v) for u, v in self.o['plinth'])
        self.assertGreater(d, 3.0)

    def test_the_flag(self):
        # 2 m by 1 m (2:1), the hoist at the pole (s = 0) and the fly out to 2 m; its bounds cover it turned any way
        f = self.o['flag']
        self.assertAlmostEqual(f['x0'], 0.0, places=3)
        self.assertAlmostEqual(f['x1'], 2.0, places=3)
        self.assertEqual((f['s0'], f['s1']), (0, 1))
        self.assertGreaterEqual(f['sphere'], 2.4)


class Place(unittest.TestCase):
    """The pole to the north-east (north is -z, east +x), on the lawn, clear of the paths, the buildings and the trees."""

    @classmethod
    def setUpClass(cls):
        cls.scene = json.loads((ROOT / 'scene.json').read_text())
        F = cut(A, '  const FAMINE = {', '\n  // kinds')
        num = lambda key: [float(x) for x in F.split(key + ': [')[1].split(']')[0].split(',')]
        cls.c, cls.pole = num('c'), num('pole')

    def test_north_east(self):
        dx, dz = self.pole[0] - self.c[0], self.pole[1] - self.c[1]
        self.assertGreater(dx, 0)
        self.assertLess(dz, 0)
        bearing = math.degrees(math.atan2(dx, -dz))   # from north, clockwise
        self.assertTrue(20 <= bearing <= 70, bearing)
        self.assertEqual(self.c, [84.0, 104.0])   # Mike's place for the memorial

    @staticmethod
    def seg(p, a, b):
        dx, dz = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dz * dz
        t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
        return math.hypot(a[0] + dx * t - p[0], a[1] + dz * t - p[1])

    def test_clear_of_the_paths_and_streets(self):
        # every mapped way's edge at least 3 m off the pole's drum (the drum 0.75 m)
        for r in self.scene['roads']:
            pts = r['pts']
            d = min(self.seg(self.pole, pts[i], pts[i + 1]) for i in range(len(pts) - 1)) if len(pts) > 1 else 1e9
            self.assertGreater(d - r['w'] / 2 - 0.75, 3.0, (r.get('name'), r['t']))

    def test_clear_of_the_buildings_and_trees(self):
        for b in self.scene['buildings']:
            poly = b['poly']
            d = min(self.seg(self.pole, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))
            self.assertGreater(d, 4.0)
        for t in self.scene['trees']:
            self.assertGreater(math.hypot(t[0] - self.pole[0], t[1] - self.pole[1]), 4.0)

    def test_kept_free(self):
        # the trees kept 2.4 m off the pole (a crown out of the flag), the tufts off the paved circle and the drum (the park's
        # sow too, through REBUILD_PAVED), the walker round the plinth and the drum
        b = cut(A, '  function famineBuild(', '  function famineStep(')
        self.assertIn('registerPoly(plinth); registerPoly(circ(2.4, 12));', b)
        self.assertIn('noSow(apron); noSow(circ(0.8, 12));', b)
        self.assertIn('REBUILD_PAVED.push({ ring: apron, bb: rbBox(apron) }, { ring: circ(0.8, 12), bb: rbBox(circ(0.8, 12)) });', b)
        self.assertIn('addColSeg(p0[0], p0[1], p1[0], p1[1]);', b)
        # laid before the trees are planted and the grass sown
        self.assertLess(A.index("step('Restoring the landmarks'"), A.index("step('Planting the street trees'"))
        self.assertLess(A.index("step('Restoring the landmarks'"), A.index("step('Sowing the grass'"))


class Shader(unittest.TestCase):
    def test_the_flag_colours_and_order(self):
        # the tricolour: green at the hoist, white, orange (#169B62, #FFFFFF, #FF883E), by the cloth's run from the pole
        self.assertIn('flag: [0x169b62, 0xffffff, 0xff883e]', MOD)
        self.assertIn('uFlagC0: { value: famFlagC(FAMINE.flag[0]) }, uFlagC1: { value: famFlagC(FAMINE.flag[1]) }, uFlagC2: { value: famFlagC(FAMINE.flag[2]) }', MOD)
        self.assertIn("'float fS = vFlag.x * 3.0, fW = max(fwidth(fS), 1e-4) * 0.75;',", MOD)
        self.assertIn("'vec3 fC = mix(uFlagC0, uFlagC1, smoothstep(1.0 - fW, 1.0 + fW, fS));',", MOD)
        self.assertIn("'fC = mix(fC, uFlagC2, smoothstep(2.0 - fW, 2.0 + fW, fS));',", MOD)
        # a cloth both sides: one double-sided surface, so its back has the green at the pole too
        flag = cut(MOD, '  function famFlagMat() {', '  const FAM = {')
        self.assertIn('side: THREE.DoubleSide', flag)

    def test_the_wind(self):
        # the cloth's wave on the water's clock (still under reduced motion), turned to the weather's heading at a bounded rate
        s = cut(MOD, '  function famineStep() {', '  // ?dev: __dbg.famine()')
        self.assertIn('t = waterU.uTime.value', s)
        self.assertIn('Math.atan2(wz, wx) - FAM.ang', s)
        self.assertIn('Math.max(-0.6 * dt, Math.min(0.6 * dt, da))', s)
        self.assertIn('famineStep();   // Round 197', A)
        self.assertIn('famine: famineProbe, ', A)

    def test_depth_and_programs(self):
        # no fragment depth (Round 192's reversed-Z: the standard chunks write it), its own program keys, the flag no caster
        self.assertNotIn('gl_FragDepth', MOD)
        self.assertIn("m.customProgramCacheKey = () => 'famine-memorial-r197';", MOD)
        self.assertIn("m.customProgramCacheKey = () => 'famine-flag-r197';", MOD)
        b = cut(MOD, '  function famineBuild(', '  function famineStep(')
        self.assertNotIn('flag.castShadow', b)
        self.assertIn('FAM.flag.receiveShadow = true;', b)
        # the night's floods of Round 184 kept, on the lamps' photocell
        self.assertIn("'  float mFace = clamp(dot(mWN.xz, mR) * 0.9 + 0.06 - 0.3 * mWN.y, 0.0, 1.0); mFace *= mFace;',", MOD)
        self.assertIn('Object.assign(sh.uniforms, famU, { uLamp: lampUniform });', MOD)

    def test_the_old_one_under_real_0(self):
        # ?real=0 builds Round 129's memorial as it was (and no flag)
        i = A.index('    if (REAL) {\n      const [cx, cz] = FAMINE.c,')
        blk = A[i:A.index('    // Glory Beer Bar & Kitchen', i)]
        self.assertIn('famineBuild(cx, cz, ux, uz, ryAlign(ux, uz), siteY(cx, cz, \'ground\'));', blk)
        old = blk[blk.index('} else {'):]
        self.assertIn("const BRONZE = '#050403', BRONZE_L = '#080605', GRANITE = '#0b0c0d', GRANITE_T = '#111213', PAVE = '#3b3a37';", old)
        self.assertIn("memMat.customProgramCacheKey = () => 'famine-memorial';", old)
        self.assertNotIn('flag', old.lower().replace('flags', ''))


if __name__ == '__main__':
    unittest.main()
