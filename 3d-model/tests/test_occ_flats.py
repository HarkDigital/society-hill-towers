"""Round 168 (the phones' GPU): the pins' depth image passes over the flats laid on the drawn ground.

occRender drew the whole city for the pins every 10th frame while the eye moved. A sheet on the drawn ground (a street,
a lot or yard, a far park or apron) or a flat water sheet hides nothing the ground under it does not, so the pins'
capture (and only it: the building tap's one-pixel render draws everything) skips what carries userData.occFlat. What
stands up off the ground is never skipped: a street segment that roadRaised finds raised (a deck, a quay-wall skirt, a
piece at its own grade, a flat fan, a strip off the mesh more than OCC_FLAT_TOL over it) has its triangles copied into a
capture-only mesh (occRaisedMesh) with the street mesh's own Float32 positions, so the image holds them where it did;
the overpass decks, the far ground, the core's streets (they bridge the I-95 trench), piers and the outer districts'
areas are never flagged. The promise is that no pin's answer changes: the sweep in the round's notes found none in
thousands of pins; here roadRaised and occRaisedMesh run under Node and the wiring is checked at every site."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class OccFlats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')

    def node(self, script):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_road_raised(self):
        block = cut(self.src, '  const OCC_FLAT_TOL = ', '\n  // Keep only road triangles beneath')
        out = self.node('''
const DRAPE_FB = { n: 0 }, ROAD_STATS = { flatFans: 0 };
let ground = 10;
const groundMeshY = (x, z) => (x > 1000 ? null : ground);
''' + block + r'''
// one segment's triangles at heights ys over the ground (10), at x
const seg = (ys, x = 0) => { const rc = { pos: [], idx: [] }; ys.forEach((y, i) => { rc.pos.push(x + i, y, 0); rc.idx.push(i); }); return rc; };
const flat = seg([10.2, 10.7, 10.74]), high = seg([10.2, 10.9, 10.3]), below = seg([9, 8, 10.5]), off = seg([10.1, 10.1, 10.1], 5000);
const r = {
  onMeshFlat: roadRaised(flat, 0, true, 0, false, 0, 0),
  onMeshHigh: roadRaised(high, 0, true, 0, false, 0, 0),            // on the mesh a strip sits its lift over it by construction
  offMeshFlat: roadRaised(flat, 0, false, 0, false, 0, 0),
  offMeshHigh: roadRaised(high, 0, false, 0, false, 0, 0),
  offMeshBelow: roadRaised(below, 0, false, 0, false, 0, 0),
  offMeshNoGround: roadRaised(off, 0, false, 0, false, 0, 0),
  deck: roadRaised(flat, 0, false, 13, false, 0, 0),
  skirt: roadRaised(flat, 0, true, 0, true, 0, 0),
  fallback: roadRaised(flat, 0, true, 0, false, -1, 0),
  flatFan: roadRaised(flat, 0, true, 0, false, 0, -1),
  tol: OCC_FLAT_TOL,
};
console.log(JSON.stringify(r));''')
        self.assertFalse(out['onMeshFlat'])
        self.assertFalse(out['onMeshHigh'])
        self.assertFalse(out['offMeshFlat'])
        self.assertTrue(out['offMeshHigh'])
        self.assertFalse(out['offMeshBelow'])
        self.assertTrue(out['offMeshNoGround'])
        for k in ('deck', 'skirt', 'fallback', 'flatFan'):
            self.assertTrue(out[k], k)
        self.assertGreaterEqual(out['tol'], 0.24 + 6 * 0.055 + 0.1)   # every street on the ground: LAYER.road, a motorway's class lift, the jitter

    def test_the_raised_mesh_holds_exactly_the_raised_triangles(self):
        block = cut(self.src, '  const OCC_ONLY = [];', '\n  // Wide roads and parks extend')
        out = self.node('''
const THREE = require('./three.min.js');
const PERF = {}, groupCity = new THREE.Group();
function freeOnUpload(g) { if (!g.boundingSphere) g.computeBoundingSphere(); }
''' + block + r'''
let seed = 3; const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const rc = { pos: [], idx: [], raised: [] };
for (let v = 0; v < 3000; v++) rc.pos.push(rnd() * 20000 - 9000.123456789, rnd() * 60 - 7.3333333, rnd() * 20000 - 12000.987654321);
for (let t = 0; t < 4000; t++) rc.idx.push(Math.floor(rnd() * 3000), Math.floor(rnd() * 3000), Math.floor(rnd() * 3000));
const want = [];
for (const [a, b] of [[30, 90], [300, 303], [6000, 7500], [11997, 12000]]) { rc.raised.push(a, b); for (let k = a; k < b; k++) want.push(rc.idx[k]); }
const m = occRaisedMesh(rc), g = m.geometry, P = g.attributes.position.array, I = g.index.array, F = new Float32Array(rc.pos);
let bad = 0; for (let k = 0; k < want.length; k++) for (let c = 0; c < 3; c++) if (P[I[k] * 3 + c] !== F[want[k] * 3 + c]) bad++;
const none = occRaisedMesh({ pos: rc.pos, idx: rc.idx, raised: [] });
console.log(JSON.stringify({ n: I.length, want: want.length, bad, u16: I instanceof Uint16Array, pf32: P instanceof Float32Array, verts: P.length / 3, visible: m.visible, only: m.userData.occOnly, listed: OCC_ONLY.length, inCity: m.parent === groupCity, attrs: Object.keys(g.attributes), none, perf: PERF.occRaised }));''')
        self.assertEqual(out['n'], out['want'])
        self.assertEqual(out['bad'], 0)             # each raised triangle, vertex for vertex, as the street mesh's Float32 rounds it
        self.assertTrue(out['u16'])
        self.assertTrue(out['pf32'])
        self.assertLessEqual(out['verts'], out['want'])   # shared vertices kept shared
        self.assertFalse(out['visible'])            # drawn only inside the pins' capture
        self.assertTrue(out['only'])
        self.assertEqual(out['listed'], 1)
        self.assertTrue(out['inCity'])
        self.assertEqual(out['attrs'], ['position'])   # a 12-byte stream and an index: no 1- or 3-byte stream (Round 158)
        self.assertIsNone(out['none'])
        self.assertEqual(out['perf'], out['want'] // 3)

    def test_only_the_pins_capture_skips_the_flats(self):
        s = self.src
        occ = cut(s, '  function occRender(rt, W, H, buf, noInstanced, cam = camera, read = null, noFlats = false) {', '\n  const occUnpack')
        self.assertIn('(noFlats && o.userData.occFlat)', occ)
        self.assertIn('if (noFlats) for (const m of OCC_ONLY) m.visible = true;', occ)
        self.assertIn('finally { if (noFlats) for (const m of OCC_ONLY) m.visible = false; }', occ)
        # Round 169: one call draws every image of the pins (the near and the complete kinds, read at once or later), over the flats
        # from high enough (nf = occFlatsOff()) and without the instanced meshes (Round 168: only buildings hide pins)
        self.assertIn('const s = ch.slots[k], c = pinOccCam(reach), nf = occFlatsOff();', s)
        self.assertIn('occRender(s.rt, W, H, ch.cpu.buf, true, c, now ? null : pinOccNoRead, nf);', s)
        self.assertIn('occRender(BPICK.rt, 1, 1, BPICK.buf, true);', s)   # the building tap draws everything, as it did
        self.assertEqual(s.count('occRender('), 3)

    def test_only_from_an_eye_well_over_the_ground(self):
        block = cut(self.src, '  const OCC_FLAT_EYE = ', '\n  // the city')
        out = self.node('''
const TERRAIN = { water: -7.34 }, camera = { position: { x: 0, y: 0, z: 0 } };
let mesh = 10;
const groundMeshY = (x, z) => (x > 1000 ? null : mesh), siteY = (x, z, mode) => 30;
''' + block + r'''
const at = (x, y, z) => { camera.position.x = x; camera.position.y = y; camera.position.z = z; return occFlatsOff(); };
const r = { floor: at(0, 12.5, 0), six: at(0, 16, 0), under: at(0, 29.9, 0), at20: at(0, 30, 0), high: at(0, 160, 0),
  offMesh: at(5000, 45, 0), offMeshHigh: at(5000, 55, 0) };
mesh = -40;   // a carved river bed: the water's sheet is the ground that counts
r.overWater = at(0, 5, 0); r.overWaterHigh = at(0, 12.7, 0);
r.eye = OCC_FLAT_EYE;
console.log(JSON.stringify(r));''')
        self.assertFalse(out['floor'])          # the fly floor, 2.5 m up: the flats drawn, as they always were
        self.assertFalse(out['six'])
        self.assertFalse(out['under'])
        self.assertTrue(out['at20'])
        self.assertTrue(out['high'])
        self.assertFalse(out['offMesh'])        # past the registered ground, siteY's
        self.assertTrue(out['offMeshHigh'])
        self.assertFalse(out['overWater'])      # over the river, height over the water, never the carved bed
        self.assertTrue(out['overWaterHigh'])
        self.assertEqual(out['eye'], 20)

    def test_what_is_flagged_and_what_never_is(self):
        s = self.src
        for want in ("occFlatTiles(addTiles(new THREE.Mesh(g, roadMat({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide })), 'wide roads'));",
                     "occFlatTiles(addTiles(new THREE.Mesh(g, roadMat({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide })), 'ring roads'));",
                     "occFlatTiles(addTiles(new THREE.Mesh(g, surfMat({ vertexColors: true, roughness: 0.95 })), 'ring areas'));",
                     "occFlatTiles(addTiles(m, 'lots'));",
                     "groupCity.add(occFlatTiles([new THREE.Mesh(mergeColored(slipParts), waterMat)])[0]);",
                     "water.userData.occFlat = true;"):
            self.assertIn(want, s)
        self.assertEqual(s.count('groupCity.add(occFlatTiles([new THREE.Mesh(g, riverMat)])[0]);'), 2)   # the far ring's and the outer districts' ponds
        self.assertEqual(s.count('occRaisedMesh(rc);'), 2)                                              # both street loops, before their index goes
        for never in ("addTiles(m, 'far ground');", "for (const t of addTiles(mesh, 'decks')) rayTargets.push(t);"):
            self.assertIn(never, s)
        self.assertEqual(s.count('occFlatTiles('), 8)   # the definition and the seven sites above
        streets = cut(s, "  step('Paving the streets', () => {", "\n  step('Planting parks and piers'")
        self.assertNotIn('occFlat', streets)            # the core's streets bridge the I-95 trench
        parks = cut(s, "  step('Planting parks and piers', () => {", '\n  // ------------------------------------------------ the city fabric')
        self.assertNotIn('occFlat', parks)
        self.assertIn("groupCity.add(new THREE.Mesh(g, surfMat({ vertexColors: true, roughness: 0.95 })));", s)   # the outer districts' areas (piers 1.2 m up) stay drawn
        self.assertEqual(s.count('if (roadRaised(rc, r0, onMesh, deck, skirt, fb0, ff0)) rc.raised.push(r0, rc.idx.length);'), 2)   # both loops note it
        self.assertEqual(s.count('skirt = true;'), 2)


if __name__ == '__main__':
    unittest.main()
