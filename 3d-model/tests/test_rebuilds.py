"""Round 161: the seven landmark rebuilds (rebuilds/*.js, inlined by build.py ahead of app.js).

Each rebuild file calls RB.add({ id, name, center, skip, views, build(api) }). These checks run every build() under Node
against the real three r149 with a stub api (the app's handles as plain objects), and read the packed wide tier and the
page's own wiring: every def is well formed and builds; every stream is a 4-byte multiple (Round 158: WebKit's ANGLE
Metal backend keeps a padded copy of any other); positions are finite and stand on their own site; the triangle budget
holds; each skip names exactly the generic footprints it replaces; and app.js consults the skip, owns the ground (trees,
packed poles, storefronts) and moves the rail pin."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_rebuilds
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

ROOT = Path(__file__).resolve().parents[1]
RB_DIR = ROOT / 'rebuilds'
IDS = ['dl', 'esp', 'gc', 'rtm', 'shot', 't30', 'ww']
# the generic packed records each skip removes (the Sep 25 study's final run, inscene.log.json)
SKIPPED = {'t30': 2, 'ww': 10, 'esp': 11, 'dl': 1, 'gc': 1, 'rtm': 4, 'shot': 0}
BUDGET = {'shot': 12000}                # a big building stays under 40k triangles, a small one under 12k
REACH = {'ww': 450}                     # metres from the centre; the Water Works carries the Fairmount Dam's crest across the river


def centroid(pts):                      # app.js polyCentroid: the area-weighted centroid the wide loop tests
    x = y = a = 0.0
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        c = p[0] * q[1] - q[0] * p[1]
        a += c; x += (p[0] + q[0]) * c; y += (p[1] + q[1]) * c
    a *= 0.5
    return (pts[0][0], pts[0][1]) if abs(a) < 1e-6 else (x / (6 * a), y / (6 * a))


def inside(x, z, poly):
    c = False
    for i in range(len(poly)):
        (xi, zi), (xj, zj) = poly[i], poly[i - 1]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            c = not c
    return c


SCRIPT = r'''
const fs = require('fs'), vm = require('vm');
const THREE = require(THREE_PATH);
global.THREE = THREE;
const ctx2d = new Proxy({}, { get: (t, k) => (k in t ? t[k] : (k === 'measureText' ? () => ({ width: 10 }) : () => {})), set: (t, k, v) => { t[k] = v; return true; } });
global.document = { createElement: () => ({ width: 0, height: 0, style: {}, getContext: () => ctx2d }) };
global.location = { search: '' };
global.RB = { defs: [], kit: null, add(def) { global.RB.defs.push(def); } };
for (const f of FILES) vm.runInThisContext(fs.readFileSync(f, 'utf8'), { filename: f });
const out = [];
for (const d of RB.defs) {
  const calls = { occupy: 0, pinAt: 0 };
  const api = { THREE, K: RB.kit(THREE), where: 'app', ground: () => 0, night: { value: 0 }, lamp: { value: 0 },
    lampU: { uLampMap: { value: null }, uLampBox: { value: new THREE.Vector4() }, uLampOn: { value: 0 }, uLampFade: { value: new THREE.Vector4() } },
    dayF: () => 1, lawn: null, occupy: () => { calls.occupy++; }, pinAt: () => { calls.pinAt++; }, log: () => {} };
  const r = { id: d.id, name: d.name, center: d.center, skip: d.skip, views: d.views, calls, tris: 0, meshes: 0, mats: new Set(), bad: [], finite: true, box: null };
  try {
    const obj = d.build(api);
    const bb = new THREE.Box3();
    obj.traverse((o) => {
      if (!o.isMesh) return;
      r.meshes++; r.mats.add(o.material.uuid);
      const g = o.geometry;
      r.tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
      for (const k in g.attributes) {
        const a = g.attributes[k], arr = a.isInterleavedBufferAttribute ? a.data.array : a.array, stride = a.isInterleavedBufferAttribute ? a.data.stride : a.itemSize;
        if ((arr.BYTES_PER_ELEMENT * stride) % 4) r.bad.push(k + ':' + arr.constructor.name + 'x' + stride);
      }
      const p = g.attributes.position.array;
      for (let i = 0; i < p.length; i++) if (!Number.isFinite(p[i])) { r.finite = false; break; }
      g.computeBoundingBox(); bb.union(g.boundingBox);
    });
    r.box = [bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z];
  } catch (e) { r.error = String(e && e.stack || e); }
  r.mats = r.mats.size; r.tris = Math.round(r.tris);
  out.push(r);
}
console.log(JSON.stringify(out));
'''


class RebuildsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        files = [str(RB_DIR / '_kit.js')] + [str(RB_DIR / (i + '.js')) for i in IDS]
        script = SCRIPT.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('FILES', json.dumps(files))
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if run.returncode:
            raise AssertionError(run.stderr[-3000:])
        cls.defs = {d['id']: d for d in json.loads(run.stdout)}
        cls.app = (ROOT / 'app.js').read_text()

    def test_every_file_is_one_def_named_for_it(self):
        self.assertEqual(sorted(p.stem for p in RB_DIR.glob('*.js') if p.name != '_kit.js'), IDS)
        self.assertEqual(sorted(self.defs), IDS)
        for i, d in self.defs.items():
            self.assertTrue(d['name'], i)
            self.assertEqual(len(d['center']), 2, i)
            self.assertTrue(d['views'], i)
            for ring in d['skip'] or []:
                self.assertGreaterEqual(len(ring), 3, i)

    def test_each_builds_finite_on_its_own_site_under_budget(self):
        for i, d in self.defs.items():
            self.assertNotIn('error', d, d.get('error'))
            self.assertTrue(d['finite'], i)
            self.assertGreater(d['tris'], 1000, i)
            self.assertLessEqual(d['tris'], BUDGET.get(i, 40000), i)
            self.assertLessEqual(d['mats'], 12, i)
            x0, y0, z0, x1, y1, z1 = d['box']
            cx, cz = d['center']
            self.assertLess(max(abs(x0 - cx), abs(x1 - cx), abs(z0 - cz), abs(z1 - cz)), REACH.get(i, 260), (i, d['box']))
            self.assertGreater(y0, -30, i); self.assertLess(y1, 120, i)

    def test_every_stream_is_a_four_byte_multiple(self):
        for i, d in self.defs.items():
            self.assertEqual(d['bad'], [], i)          # Round 158: never a 3-byte or 1-byte stream

    def test_the_app_handles_are_used(self):
        self.assertEqual(self.defs['t30']['calls']['pinAt'], 1)    # the Rail Stations pin onto the attic
        self.assertGreaterEqual(self.defs['ww']['calls']['occupy'], 5)
        self.assertEqual(self.defs['shot']['calls']['occupy'], 1)    # the tower's own ground (a tree grew through it)
        # the builder lets its parts go once merged: a def's hooks close over build()'s scope (the review's memory find)
        self.assertIn('parts.clear(); B.extra = null;', (RB_DIR / '_kit.js').read_text())
        self.assertIn('bag.length = 0; mas.length = 0;', (RB_DIR / 'rtm.js').read_text())
        for p in RB_DIR.glob('*.js'):
            src = p.read_text()
            self.assertNotRegex(src, r'window\.__dbg|__dbg\.|window\.__KIT|__proto\(', p.name)

    def test_each_skip_removes_exactly_its_generic_footprints(self):
        scene = C.walk_scene('wide.b64')
        cents = [centroid(b[4]) for b in scene['buildings']]
        for i, d in self.defs.items():
            n = sum(1 for (x, z) in cents if any(inside(x, z, r) for r in (d['skip'] or [])))
            self.assertEqual(n, SKIPPED[i], i)

    def test_the_app_is_wired(self):
        a = self.app
        self.assertIn("const REBUILDS = typeof RB !== 'undefined'", a)
        self.assertRegex(a, r"const rbId = REBUILD_SKIP\.length \? rebuildSkipAt\(cx, cz\) : null;\n\s+if \(rbId \|\| DEMOLISHED\.some")
        self.assertIn("rebuildAt(x, z, 2)) return;", a)                      # trees
        self.assertIn("rebuildCrownAt(x, z, cr * st[3] * 1.21", a)
        self.assertIn("if(inCapSite(x,z) || rebuildAt(x, z, 1))", a)          # packed poles
        self.assertIn("for (const o of REBUILD_OCC) own.push(", a)           # storefronts
        self.assertIn("for (const p of REBUILD_PINS) if (x >= p.bb[0]", a)   # the rail pin
        self.assertIn("for (const s of REBUILD_SKIP) own.push(", a)          # storefronts: the whole site
        self.assertIn("o.frustumCulled = false; pendingUpload.push(o);", a)  # uploaded (and freed on a phone) behind the veil
        self.assertIn("PERF.failed.push(['Rebuilding the landmarks: ' + d.id", a)
        self.assertRegex(a, r"if \(rbId\) \{\n\s+REBUILD_OCC\.push\(\{ id: rbId, ring: poly, bb: rbBox\(poly\) \}\);\n\s+if \(h >= 6\) roofNote\(")
        steps = re.findall(r"step\('([^']+)'", a)
        k = steps.index('Rebuilding the landmarks')
        self.assertEqual(steps[k - 1], 'Raising the outer districts')
        for later in ('Dressing the storefronts', 'Planting the street trees', 'Lighting the streetlamps', 'Posting the transit stops'):
            self.assertGreater(steps.index(later), k, later)

    def test_the_page_carries_them(self):
        page = C.path('society-hill-towers.html').read_text()
        self.assertIn('const RB = { defs: [], kit: null', page)
        for i in IDS:
            self.assertIn('// ---- rebuilds/' + i + '.js', page)
        self.assertLess(page.index('const RB = { defs'), page.index("const REBUILDS = typeof RB !== 'undefined'"))


if __name__ == '__main__':
    unittest.main()
