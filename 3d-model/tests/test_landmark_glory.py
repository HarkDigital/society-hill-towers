"""Round 190: Glory Beer Bar & Kitchen, 126 Chestnut Street (rebuilds/glory.js, bake_glory_art.py, the app's api.glory).

- the lot: the OPA address point for 126 lies in it, and exactly one core footprint's area-weighted centroid does, scene
  building 2541 (the old builder stood on 120, two lots east);
- the realistic look holds 2541 back under a key that is not 'glory' (the old builder would run on it), and ?real=0 and
  ?glory=0 keep the old entry exactly;
- under Node the def builds a near level, a far level and the signs inside their budgets, every stream finite and a
  multiple of four bytes (Round 158), aGl four normalized bytes, the index 16-bit;
- the manifest's files are there with their phone halves, the masks opaque RGB PNGs, the rooms each with a back wall;
- the app's wiring: the def skipped unless GLORY_ON, the lamps in the light map at their own 7 m, the search's bar kind, the
  card's lines, the frame step, and no em dash or middot in anything a person reads."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

try:
    from . import _common as C
except ImportError:
    import _common as C

ROOT = Path(__file__).resolve().parents[1]
LOT = [[97.23, -265.88], [91.29, -266.94], [98.51, -307.95], [106.97, -306.47], [106.74, -305.21], [102.6, -281.43], [100.02, -281.87]]
OPA_126 = (101.01, -284.81)


def inside(x, z, poly):
    c = False
    for i in range(len(poly)):
        (xi, zi), (xj, zj) = poly[i], poly[i - 1]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            c = not c
    return c


def centroid(pts):
    x = y = a = 0.0
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        c = p[0] * q[1] - q[0] * p[1]
        a += c; x += (p[0] + q[0]) * c; y += (p[1] + q[1]) * c
    a *= 0.5
    return (pts[0][0], pts[0][1]) if abs(a) < 1e-6 else (x / (6 * a), y / (6 * a))


SCRIPT = r'''
const fs = require('fs'), vm = require('vm');
const THREE = require(THREE_PATH);
global.THREE = THREE;
const ctx2d = new Proxy({}, { get: (t, k) => (k in t ? t[k] : (k === 'measureText' ? () => ({ width: 10 }) : () => {})), set: (t, k, v) => { t[k] = v; return true; } });
global.document = { createElement: () => ({ width: 0, height: 0, style: {}, getContext: () => ctx2d }) };
global.location = { search: '' };
global.RB = { defs: [], kit: null, add(def) { global.RB.defs.push(def); } };
for (const f of FILES) vm.runInThisContext(fs.readFileSync(f, 'utf8'), { filename: f });
const art = JSON.parse(fs.readFileSync(ART, 'utf8'));
const out = {};
for (const withArt of [false, true]) {
  const calls = { lod: 0, lamps: 0, ref: null, occupy: 0, frame: null };
  const mat = new THREE.MeshStandardMaterial();
  const api = { THREE, K: RB.kit(THREE), where: 'app', ground: () => 0.25, occupy: () => { calls.occupy++; }, pinAt: () => {}, log: () => {} };
  if (withArt) api.glory = { art, facade: (f) => { calls.frame = f; return mat; }, signs: () => mat, lod: () => { calls.lod++; }, lamps: (l) => { calls.lamps = l.length; }, ref: (r) => { calls.ref = r; } };
  const t0 = Date.now();
  const obj = RB.defs.find((d) => d.id === 'glory').build(api);
  const r = { ms: Date.now() - t0, calls, meshes: {} };
  obj.traverse((o) => {
    if (!o.isMesh) return;
    const g = o.geometry, m = { tris: (g.index ? g.index.count : g.attributes.position.count) / 3, bad: [], finite: true, attrs: {}, index: g.index ? g.index.array.constructor.name : null };
    for (const k in g.attributes) {
      const a = g.attributes[k];
      m.attrs[k] = [a.array.constructor.name, a.itemSize, !!a.normalized];
      if ((a.array.BYTES_PER_ELEMENT * a.itemSize) % 4) m.bad.push(k);
    }
    const p = g.attributes.position.array;
    for (let i = 0; i < p.length; i++) if (!Number.isFinite(p[i])) { m.finite = false; break; }
    g.computeBoundingBox();
    m.box = [g.boundingBox.min.x, g.boundingBox.min.y, g.boundingBox.min.z, g.boundingBox.max.x, g.boundingBox.max.y, g.boundingBox.max.z];
    r.meshes[o.name] = m;
  });
  out[withArt ? 'art' : 'stub'] = r;
}
console.log(JSON.stringify(out));
'''


class Lot(unittest.TestCase):
    def test_the_lot_is_126(self):
        self.assertTrue(inside(*OPA_126, LOT))
        scene = C.load_json('scene.json')
        hits = [i for i, b in enumerate(scene['buildings']) if b.get('poly') and len(b['poly']) >= 3 and inside(*centroid(b['poly']), LOT)]
        self.assertEqual(hits, [2541])
        cx, cz = centroid(scene['buildings'][2541]['poly'])
        self.assertAlmostEqual(cx, 99.03, delta=0.05)
        self.assertAlmostEqual(cz, -288.41, delta=0.05)
        # the def carries the same lot
        src = (ROOT / 'rebuilds' / 'glory.js').read_text()
        self.assertIn('const LOT = ' + json.dumps(LOT) + ';', src)


class Gating(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / 'app.js').read_text()

    def test_the_realistic_key_is_not_the_old_one(self):
        a = self.app
        self.assertIn("const GLORY_ON = REAL && !/[?&]glory=0\\b/.test(location.search);", a)
        # the old entry, exactly as it was, only off the realistic look (or under ?glory=0)
        self.assertIn("...(GLORY_ON ? [] : [{ x: 115.1, z: -283.8, r: 5, minArea: 100, spec: { mode: 'custom', key: 'glory' } }]),", a)
        self.assertIn("{ x: 99.03, z: -288.41, r: 3, minArea: 250, spec: { mode: 'custom', key: 'glory126' } },", a)
        self.assertNotIn("getKey('glory126')", a)
        self.assertIn("const bG = getKey('glory');", a)

    def test_the_rebuild_step_hands_it_over(self):
        a = self.app
        self.assertIn('api.glory = gloryApi();', a)
        self.assertIn('if (d.real && !GLORY_ON) continue;', a)
        self.assertIn('gloryStep(now);   // Round 190', a)
        steps = re.findall(r"step\('([^']+)'", a)
        self.assertLess(steps.index('Rebuilding the landmarks'), steps.index('Lighting the streetlamps'))   # the lanterns are known before the light map

    def test_the_lanterns_join_the_light_map(self):
        a = self.app
        self.assertIn('const nGl = GLORY.lamps.length;', a)
        s = a[a.index('for (const q of GLORY.lamps) {'):]
        s = s[:s.index('\n      }')]
        self.assertIn('lr[m] = 7;', s)
        self.assertIn('lc[m * 3] = 0.22;', s)

    def test_the_search_and_the_card(self):
        a = self.app
        self.assertIn("bar: 2, building: 4", a)
        self.assertIn("bar: 'Bar'", a)
        self.assertIn("if (GLORY.ref) add(GLORY.ref.name, GLORY.ref.door[0], GLORY.ref.door[1], 'bar', GLORY.ref);", a)
        self.assertIn("if (e.kind === 'bar' && e.ref) { gloryGoTo(e.ref);", a)
        self.assertIn("bldgOpen(p[0], p[1] + 1, p[2], x, z, gloryAt(x, z, 1) ? GLORY.ref : null);", a)
        self.assertIn("if (st.biz) { gloryCard(st); return; }", a)
        self.assertIn("const GLORY_OPENS = [720, 960, 960, 960, 720, 720, 720], GLORY_SHUT = 120;", a)
        card = a[a.index('  function gloryCardHead() {'):a.index('  function gloryAt(x, z, pad) {')]
        for line in ('Craft beer bar and kitchen on two floors', '126 Chestnut St, Old City', 'Built 1853 as a store for James A. Brown'):
            self.assertIn(line, card)
        body = a[a.index('  function gloryCard(st) {'):a.index('  function bldgPick(cx, cy) {')]
        self.assertIn('https://www.gloryphilly.com/', body)
        self.assertIn('septaEsc(st.biz.name)', body)

    def test_no_em_dash_or_middot_where_people_read(self):
        a = self.app
        for start, end in (('  function gloryCanvas() {', '  // an image into a placeholder texture'), ('  function gloryCardHead() {', '  function gloryAt(x, z, pad) {'),
                           ('  function gloryCard(st) {', '  function bldgPick(cx, cy) {')):
            s = a[a.index(start):a.index(end)]
            strings = re.findall(r"'([^'\\]*)'", s)
            for t in strings:
                self.assertNotIn('—', t, t)
                self.assertNotIn('·', t, t)
        g = (ROOT / 'rebuilds' / 'glory.js').read_text()
        self.assertIn("name: 'Glory Beer Bar & Kitchen'", g)
        self.assertNotIn('·', g)

    def test_the_old_look_is_untouched(self):
        a = self.app
        # the narrowed Chestnut, the neighbours' recolours and the lanterns are the realistic look's alone
        self.assertIn("if (GLORY_ON && r.name === 'Chestnut Street'", a)
        self.assertIn("...(GLORY_ON ? [\n        { x: 99.03", a)


class Def(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        files = [str(ROOT / 'rebuilds' / '_kit.js'), str(ROOT / 'rebuilds' / 'glory.js')]
        script = SCRIPT.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('FILES', json.dumps(files)).replace('ART', json.dumps(str(ROOT / 'glory_art.json')))
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if run.returncode:
            raise AssertionError(run.stderr[-3000:])
        cls.r = json.loads(run.stdout)

    def test_budgets_with_and_without_the_app(self):
        for k in ('stub', 'art'):
            m = self.r[k]['meshes']
            self.assertEqual(sorted(m), ['glory-far', 'glory-near', 'glory-signs'], k)
            self.assertLessEqual(m['glory-near']['tris'], 6000, k)
            self.assertGreater(m['glory-near']['tris'], 2500, k)
            self.assertLessEqual(m['glory-far']['tris'], 150, k)
            self.assertLessEqual(m['glory-signs']['tris'], 60, k)
            self.assertLess(self.r[k]['ms'], 300, k)

    def test_streams(self):
        for k in ('stub', 'art'):
            for name, m in self.r[k]['meshes'].items():
                self.assertEqual(m['bad'], [], (k, name))
                self.assertTrue(m['finite'], (k, name))
                self.assertEqual(m['index'], 'Uint16Array', (k, name))
                self.assertEqual(m['attrs']['position'][:2], ['Float32Array', 3])
            for name in ('glory-near', 'glory-far'):
                self.assertEqual(self.r[k]['meshes'][name]['attrs']['aGl'], ['Uint8Array', 4, True])
            self.assertNotIn('aGl', self.r[k]['meshes']['glory-signs']['attrs'])

    def test_it_stands_on_its_lot(self):
        for k in ('stub', 'art'):
            x0, y0, z0, x1, y1, z1 = self.r[k]['meshes']['glory-near']['box']
            self.assertGreater(x0, 89); self.assertLess(x1, 109)
            self.assertGreater(z0, -311); self.assertLess(z1, -264)   # the stoop and the old sign box reach about 2.6 m out
            self.assertLess(y1, 24); self.assertGreater(y0, -2)

    def test_the_app_handles(self):
        c = self.r['art']['calls']
        self.assertEqual(c['lod'], 1)
        self.assertEqual(c['lamps'], 2)
        self.assertEqual(c['occupy'], 1)
        self.assertEqual(c['ref']['name'], 'Glory Beer Bar & Kitchen')
        d, n = c['ref']['door'], c['ref']['n']
        self.assertFalse(inside(d[0], d[1], LOT))                              # the door's point is on the stoop, a metre out
        self.assertTrue(inside(d[0] - n[0] * 1.2, d[1] - n[1] * 1.2, LOT))      # and a metre and a fifth back is the bar
        f = c['frame']
        self.assertAlmostEqual(f['ux'], 0.98504, places=3)
        self.assertAlmostEqual(f['vz'], 0.98504, places=3)
        self.assertEqual(len(f['lanterns']), 2)
        self.assertEqual(self.r['stub']['calls']['occupy'], 1)


class Art(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = C.load_json('glory_art.json')

    def test_files_and_halves(self):
        m = self.m
        for k in ('img', 'imgHalf', 'mask', 'maskHalf'):
            self.assertTrue((ROOT / m[k]).exists(), m[k])
            self.assertTrue((ROOT / m['interior'][k]).exists(), m['interior'][k])
        self.assertIn('-half.', m['imgHalf']); self.assertIn('-half.', m['maskHalf'])

    def test_masks_are_opaque_rgb(self):
        try:
            from PIL import Image
        except ImportError:
            raise unittest.SkipTest('PIL unavailable')
        for p in (self.m['mask'], self.m['maskHalf'], self.m['interior']['mask'], self.m['interior']['maskHalf']):
            with Image.open(ROOT / p) as im:
                self.assertEqual(im.format, 'PNG', p)
                self.assertEqual(im.mode, 'RGB', p)
        with Image.open(ROOT / self.m['img']) as im:
            self.assertEqual(im.size, (self.m['w'], self.m['h']))

    def test_measures_and_rooms(self):
        L, U = self.m['lower'], self.m['upper']
        self.assertEqual(len(L['bays']), 4); self.assertEqual(len(L['arcade']), 4); self.assertEqual(len(L['cols']), 6)
        self.assertEqual(len(U['win']), 12)
        self.assertLess(L['doorTop'], L['sill2']); self.assertLess(L['sill2'], L['spring']); self.assertLess(L['spring'], L['crown'])
        self.assertLessEqual(L['crown'], L['cornice'][0])
        self.assertEqual(self.m['gen']['warnings'], [])
        P = self.m['interior']['plates']
        self.assertEqual(sorted(P), ['ground-closed', 'ground-open', 'upperroom-closed', 'upperroom-open'])
        for k, p in P.items():
            x0, y0, x1, y1 = p['back']
            self.assertTrue(0 < x0 < x1 < 1 and 0 < y0 < y1 < 1, k)
        self.assertEqual(len(self.m['swatches']), 7)


if __name__ == '__main__':
    unittest.main()
