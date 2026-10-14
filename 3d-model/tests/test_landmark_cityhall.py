"""Round 190 (Mike: "I want City hall ... to be totally revamped"): City Hall rebuilt to the measured building under the
realistic look (buildCityHallReal), its facades generated photographs (fetch_cityhall_art.py, bake_cityhall_art.py,
cityhall_art.json, art/cityhall/), Round 81's block kept byte for byte for ?real=0.

These checks hold the measured table (NOAA 2022 QL1 LiDAR, OSM relation 4720912, Turner's 1909 booklet), the one themed
slot taken at Round 81's place in the build order, the realistic-look gate, the old block and its flood patch untouched,
the manifest's cells, the level's constants, and then run chModel under Node with the vendored three.min.js: both levels'
triangles within their budgets, every index and normal sound, and the tops within half a metre of the table."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text(encoding='utf-8')


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class Table(unittest.TestCase):
    def test_the_frame_and_the_tower_axis(self):
        t = cut(SRC, '  const CITY_HALL = {', '  const CH_HOUSE')
        self.assertIn('B0: [-1608.65, -764.51],', t)
        self.assertIn("tower: { c: [0, -37.2],", t)
        # the tower's axis in the scene stays where the viewpoint, the orbit and the skyglow point at it
        fl = (0.986, 0.167, -0.167, 0.986)
        x, z = -1608.65 + fl[2] * -37.2, -764.51 + fl[3] * -37.2
        self.assertAlmostEqual(x, -1602.44, delta=0.05)
        self.assertAlmostEqual(z, -801.19, delta=0.05)

    def test_the_measured_heights(self):
        t = cut(SRC, '  const CITY_HALL = {', '  const CH_HOUSE')
        self.assertIn('st: { water: 1.5, base: 5.57, princ: 15.78, main: 26.63 },', t)
        self.assertIn("roofs: { curtainDeck: 36.0, curb: 32.8, flankDeck: 39.4, centreBody: 49.0, crown: [57.0, 59.6, 61.8, 73.5], cornerCurb: 45.4, cornerCap: 48.8, cornerPole: 58.4 },", t)
        self.assertIn('centreTop: 39.28, cornerTop: 38.13,', t)
        self.assertIn('clock: [102.8, 123.4, 10, 117, 2.5],', t)
        self.assertIn('dome: [[123.4, 8.6], [127, 8.5], [130, 8.2], [133, 7.6], [136, 6.8], [139, 5.8], [142, 4.6]],', t)
        self.assertIn('penn: [155.6, 167.0] },', t)
        # the faces: N V -62.9 to -76.7, S 63.1 to 72.1, E/W |U| 63.2 to 72.0 (the LiDAR's cornice lines)
        self.assertIn('N: { curtain: -62.9, flank: -68.9, corner: -67.0, centre: -75.0, bay: -76.7 },', t)
        self.assertIn('S: { curtain: 63.1, flank: 65.5, corner: 67.8, centre: 70.1, bay: 72.1 },', t)
        self.assertIn('E: { curtain: 63.2, flank: 65.6, corner: 67.6, centre: 70.4, bay: 72.0 },', t)

    def test_the_osm_ring(self):
        t = cut(SRC, '    ring: [[', '  };\n')
        ring = json.loads(t[t.index('['):t.rindex(']') + 1])
        self.assertEqual(len(ring), 71)
        xs, zs = [p[0] for p in ring], [p[1] for p in ring]
        self.assertTrue(-1681 < min(xs) and max(xs) < -1533 and -843 < min(zs) and max(zs) < -689)


class Wiring(unittest.TestCase):
    def test_one_slot_taken_where_round_81_took_it(self):
        blk = cut(SRC, '      cityHall: {', '      // --- Philadelphia Museum of Art')
        self.assertEqual(blk.count('themeSlotN'), 1)
        slot = blk.index('        const chSlot = themeSlotN++ % 4;')
        gate = blk.index('        if (CH_ON) {')
        self.assertLess(slot, gate)
        self.assertIn('buildCityHallReal({ chSlot, themeParts });', blk[gate:gate + 400])
        self.assertIn('break cityHall;', blk[gate:gate + 400])
        # the themed parts merge after it in the same step, and before the rebuilds
        self.assertLess(SRC.index('      cityHall: {'), SRC.index("    if (themeParts.length) {   // the night's themed lights"))
        self.assertLess(SRC.index("    if (themeParts.length) {   // the night's themed lights"), SRC.index("  step('Rebuilding the landmarks'"))

    def test_the_realistic_look_gate(self):
        self.assertIn("const CH_ON = REAL && typeof CITYHALL_ART !== 'undefined' && !!CITYHALL_ART && !!CITYHALL_ART.cells;", SRC)
        # the outer districts' loop leaves the outline's ground to the model only under it
        self.assertIn('if (CH_ON && cx > -1690 && cx < -1520 && cz > -850 && cz < -680 && rbDist(cx, cz, CITY_HALL.ring) <= 2)', SRC)

    def test_the_old_block_stands_for_real_0(self):
        blk = cut(SRC, '      cityHall: {', '      // --- Philadelphia Museum of Art')
        for line in ('        const hallMat=cityMat.clone(),hallFacade=cityMat.onBeforeCompile;', '        if (VDEPTH_WANT) vdepthTwin(hallMat);',
                     "        hallMat.customProgramCacheKey=()=> 'city-hall-soft-flood';",
                     '        appendBuilding(hallChunk(bx, bz), sqPoly(bx, bz, 148, 143), base - 1, base + 27, c, 1, base, [sqPoly(bx, bz, 64, 59)]);'):
            self.assertIn(line, blk)
        # Round 109's flood patch, which ?real=0 and tests/city_hall_gpu.html run, is the pre-round one to the byte
        flood = cut(SRC, '  function cityHallFloodPatch(sh,uniforms) {', '  const BOATHOUSE_PLANS')
        self.assertEqual(hashlib.sha256(flood.encode()).hexdigest()[:16], 'fdf4e57d694b39d2')
        self.assertIn('vec3 hc=mix(vec3(.38,.32,.23),uHallColor,uHallOn);', flood)
        self.assertIn("float tower=hallBeam((hp-vec2(0.0,-55.0))/vec2(19.0,20.0));", flood)

    def test_the_frame_steps_it_and_dev_probes_it(self):
        fr = cut(SRC, '  function frame(now, once) {', '\n  setHint();')
        self.assertEqual(fr.count('cityHallStep();'), 1)
        self.assertIn(' cityHall: cityHallProbe,', SRC)

    def test_the_level_constants(self):
        self.assertIn('const CH_NEAR_R = isTouch ? 420 : 650, CH_HYST = 40, CH_ART_R = 1000;', SRC)
        step = cut(SRC, '  function cityHallStep() {', '  // ?dev: __dbg.cityHall()')
        self.assertIn("else if (lod === 'near' && d > CH_NEAR_R + CH_HYST) lod = 'far';", step)
        self.assertIn('if (isTouch && d < CH_ART_R) chLoadArt();', step)
        self.assertIn("if (CH.art !== 'none' || TIER2) return;", cut(SRC, '  function chLoadArt() {', '  const _chE'))

    def test_phone_streams_and_samplers(self):
        g = cut(SRC, '  function chGeometry(b, Y0) {', '  // the untextured materials')
        # the colour as four normalized bytes (never three), the kind and seed as two floats: no 1- or 3-byte stream
        self.assertIn("g.setAttribute('aCol', new THREE.BufferAttribute(new Uint8Array(b.C), 4, true));", g)
        self.assertIn("g.setAttribute('aK', new THREE.BufferAttribute(new Float32Array(b.K), 2));", g)
        m = cut(SRC, '  function chMaterial(chSlot, Y0) {', '  // the dials: a canvas a dial')
        # its own samplers: the atlas, the mask and the pitched roofs' slate (the lamps' maps, the shadows and the weather's
        # come with the shared patches)
        self.assertEqual(sorted(set(__import__('re').findall(r'uniform sampler2D ([^;]+);', m))), ['uMask, uPitchArt'])
        self.assertNotIn('userData.vdepth', cut(SRC, '  // ---- City Hall rebuilt (Round 190', "  step('Restoring the landmarks'"))

    def test_no_em_dashes_in_its_strings(self):
        blk = cut(SRC, '  // ---- City Hall rebuilt (Round 190', "  step('Restoring the landmarks'")
        for ch in ('—', '·'):
            for line in blk.splitlines():
                if ch in line:
                    code = line.split('//')[0]
                    self.assertNotIn(ch, code, line)


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((ROOT / 'cityhall_art.json').read_text())

    def test_the_cells(self):
        cells = self.m['cells']
        want = {'aedicule', 'apse', 'ashlar', 'balus', 'belvedere', 'centre', 'clock', 'corner', 'court', 'curtain', 'dome', 'dormer_c',
                'dormer_w', 'flank', 'oculus', 'tower_low', 'tower_mid', 'turret'}
        self.assertEqual(set(cells), want)
        rects = list(cells.values())
        for r in rects:
            self.assertTrue(0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1, r)
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                self.assertFalse(a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6, (a, b))
        self.assertEqual(set(self.m['m']), want)
        self.assertEqual(set(self.m['mean']), want)

    def test_what_the_page_builds_to_the_pictures(self):
        meta = self.m['meta']
        a0, a1, spring, crown = meta['centre']['arch']
        self.assertAlmostEqual(a1 - a0, 5.0, delta=0.6)      # the 18 ft archway
        self.assertAlmostEqual(crown, 9.14, delta=0.8)        # 30 ft
        self.assertLess(spring, crown)
        cu, cy, ru, rv = meta['clock']['dial']
        self.assertAlmostEqual(cu, 10.0, delta=0.5)           # centred on the 20 m face
        self.assertAlmostEqual(102.8 + cy, 110.0, delta=0.6)  # 361 ft
        self.assertAlmostEqual(max(ru, rv) * 2, 7.92, delta=0.6)   # 26 ft
        self.assertEqual(len(meta['centre']['cols']), 12)
        self.assertEqual(len(meta['corner']['cols']), 8)
        self.assertEqual(len(meta['flank']['cols']), 2)

    def test_the_files_and_the_phone_copies(self):
        for k in ('img', 'imgHalf', 'mask', 'maskHalf'):
            self.assertTrue(self.m[k].startswith('art/cityhall/'), k)
            self.assertTrue((ROOT / self.m[k]).exists(), k)
        self.assertEqual(self.m['size'], [2048, 2048])


class Model(unittest.TestCase):
    def run_model(self, touch):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        mod = cut(SRC, '  // ---- City Hall rebuilt (Round 190', "  // the night's flood on the rebuilt block")
        script = r'''
const THREE = require(THREE_PATH);
const REAL = true, isTouch = TOUCH;
const CITYHALL_ART = MANIFEST;
const fl = { px: 140, pz: 0, dx: -0.167, dz: 0.986, nx: 0.986, nz: 0.167 };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
MOD
const out = {};
for (const far of [false, true]) {
  const { b, tops } = chModel(CITYHALL_ART, far);
  let bad = 0, nanP = 0, nanN = 0, short = 0;
  for (const i of b.I) if (!(i >= 0 && i < b.nv)) bad++;
  for (const v of b.P) if (!Number.isFinite(v)) nanP++;
  for (let i = 0; i < b.nv; i++) { const l = Math.hypot(b.N[i * 3], b.N[i * 3 + 1], b.N[i * 3 + 2]); if (!Number.isFinite(l)) nanN++; else if (l < 0.5) short++; }
  let ymax = -1e9, ymin = 1e9; for (let i = 1; i < b.P.length; i += 3) { ymax = Math.max(ymax, b.P[i]); ymin = Math.min(ymin, b.P[i]); }
  const g = chGeometry(b, 2.45);
  out[far ? 'far' : 'near'] = { tris: b.I.length / 3, verts: b.nv, bad, nanP, nanN, short, ymax, ymin, tops,
    attrs: Object.fromEntries(Object.entries(g.attributes).map(([k, a]) => [k, [a.array.constructor.name, a.itemSize, a.array.BYTES_PER_ELEMENT * a.itemSize]])) };
}
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('TOUCH', 'true' if touch else 'false') \
            .replace('MANIFEST', (ROOT / 'cityhall_art.json').read_text()).replace('MOD', mod)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def check(self, out, near_budget):
        for lod, budget in (('near', near_budget), ('far', 6000)):
            o = out[lod]
            self.assertLessEqual(o['tris'], budget, lod)
            self.assertEqual((o['bad'], o['nanP'], o['nanN'], o['short']), (0, 0, 0, 0), lod)
            self.assertGreaterEqual(o['ymin'], -0.01, lod)
            for k, (typ, size, bytes_) in o['attrs'].items():
                self.assertEqual(bytes_ % 4, 0, (lod, k, typ, size))   # no 1- or 3-byte stream (Round 158)
        t = out['near']['tops']
        for k, v in (('centreCrown', 61.8), ('cornerCap', 48.8), ('flankDeck', 39.4), ('centreBody', 49.0), ('crownDeck', 57.0),
                     ('masonry', 102.8), ('clockStage', 123.4), ('dome', 142.0), ('cupola', 155.6), ('turret', 48.5), ('apse', 24.5)):
            self.assertAlmostEqual(t[k], v, delta=0.5, msg=k)
        # the highest point the model itself builds is the cupola's head, where Penn's feet stand (he rides the themed parts to 167.0)
        self.assertAlmostEqual(out['near']['ymax'], 155.6, delta=0.1)

    def test_a_computer(self):
        out = self.run_model(False)
        self.check(out, 60000)
        self.assertGreater(out['near']['tris'], 5 * out['far']['tris'] / 2)

    def test_a_phone(self):
        self.check(self.run_model(True), 30000)


if __name__ == '__main__':
    unittest.main()
