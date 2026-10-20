"""Round 214: the flight's walls (Mike: "Can we add building collision detection so people cannot just fly through
buildings?").

Every building loop notes its footprint and roof into a sparse grid of HIT_CELL m columns (hitNote), and applyFly moves the
eye through hitFly: out of every column it was not already over, onto a roof it comes down on, in steps no longer than
HIT_R so a fast eye cannot step through a row. The block is cut from app.js and run under Node."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


def cut(start, end):
    a = SRC.index(start)
    return SRC[a:SRC.index(end, a)]


class FlightWalls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        cls.block = cut('  const HIT_ON = ', '  // the outer districts\' wall colours, sampled')

    def run_js(self, body, search=''):
        script = r'''
const location = { search: SEARCH };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function polyCentroid(p) { let x = 0, z = 0; for (const q of p) { x += q[0]; z += q[1]; } return [x / p.length, z / p.length]; }
class V3 { constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
  copy(o) { this.x = o.x; this.y = o.y; this.z = o.z; return this; }
  addScaledVector(v, s) { this.x += v.x * s; this.y += v.y * s; this.z += v.z * s; return this; } }
const REBUILD_OCC = [];
BLOCK
const box = (x0, z0, x1, z1) => [[x0, z0], [x1, z0], [x1, z1], [x0, z1]];
// fly for t seconds at a constant velocity, 60 frames a second; vel is the wish, as applyFly's lerp holds it
function fly(p, v, t, fps = 60) { const pos = new V3(...p), vel = new V3(...v); for (let f = 0; f < t * fps; f++) { vel.x = v[0]; vel.y = v[1]; vel.z = v[2]; hitFly(pos, vel, 1 / fps); } return [pos.x, pos.y, pos.z]; }
const out = {};
BODY
console.log(JSON.stringify(out));
'''.replace('SEARCH', json.dumps(search)).replace('BLOCK', self.block).replace('BODY', body)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_raster(self):
        o = self.run_js('''
hitNote(box(0, 0, 40, 20), 30);              // a 40 by 20 m block, 30 m tall
hitNote(box(1.2, 30.2, 3.0, 31.8), 12);      // a kiosk smaller than a cell: its centroid's cell
hitNote(box(10, 0, 20, 20), 18);             // a lower part inside the block keeps the taller roof
out.cells = HIT.cells; out.tiles = HIT.dense.size + HIT.packed.size;
out.inside = hitTop(5, 2); out.edge = hitTop(9, 4); out.outside = hitTop(10, 2); out.kiosk = hitTop(0, 7);
out.neg = (hitNote(box(-30, -30, -10, -10), 9), hitTop(-5, -5));
''')
        self.assertEqual(o['cells'], 50 + 1)   # the third adds no cell
        self.assertGreaterEqual(o['inside'], 30)
        self.assertLess(o['inside'], 30 + 1.6)       # rounded up, by less than a step
        self.assertGreaterEqual(o['edge'], 30)
        self.assertIsNone(o['outside'])              # -Infinity is null in JSON
        self.assertGreaterEqual(o['kiosk'], 12)
        self.assertGreaterEqual(o['neg'], 9)

    def test_packed_tiles(self):
        # more tiles than HIT_DENSE: the oldest are packed, a later note reopens one, and every cell reads the same packed
        o = self.run_js('''
const T = HIT_TILE * HIT_CELL, recs = [];
for (let t = 0; t < 300; t++) {   // a tile apiece: a block, a lower one beside it, a kiosk; heights that run and step
  const x = (t % 20) * T, z = Math.floor(t / 20) * T;
  recs.push([box(x + 8, z + 8, x + 100, z + 40), 12 + (t % 7) * 3], [box(x + 100, z + 8, x + 140, z + 40), 9], [box(x + 200, z + 200, x + 202, z + 202), 30 + t % 50]);
}
for (const [p, h] of recs) hitNote(p, h);
out.packs = HIT.packs; out.dense = HIT.dense.size; out.packed = HIT.packed.size;
hitNote(box(8, 100, 60, 120), 44);   // into the first tile, packed long ago
out.unpacks = HIT.unpacks;
const want = new Map(); let bad = 0, n = 0;
const ref = (x, z) => { let best = -Infinity; for (const [p, h] of recs.concat([[box(8, 100, 60, 120), 44]])) { const q = Math.ceil((h - HIT_Y0) / HIT_DY) * HIT_DY + HIT_Y0; if (p[0][0] <= x && x <= p[1][0] && p[0][1] <= z && z <= p[2][1]) best = Math.max(best, q); } return best; };
for (let t of [0, 1, 57, 150, 299]) { const x0 = (t % 20) * T, z0 = Math.floor(t / 20) * T;
  for (let j = 0; j < HIT_TILE; j++) for (let i = 0; i < HIT_TILE; i++) { const x = x0 + (i + 0.5) * HIT_CELL, z = z0 + (j + 0.5) * HIT_CELL, a = hitTop(Math.floor(x / HIT_CELL), Math.floor(z / HIT_CELL)), r = (x0 + 200 < x && x < x0 + 204 && z0 + 200 < z && z < z0 + 204) ? a : ref(x, z); n++; if (a !== r) bad++; } }
out.bad = bad; out.n = n;
out.kb = HIT.bytes / 1024; out.denseKb = HIT.dense.size * 4;
''')
        self.assertGreater(o['packs'], 0)
        self.assertLessEqual(o['dense'], 256)
        self.assertEqual(o['unpacks'], 1)
        self.assertEqual(o['bad'], 0, o)
        self.assertEqual(o['n'], 5 * 64 * 64)

    def test_wall_stops_the_eye(self):
        o = self.run_js('''
hitNote(box(0, 0, 40, 20), 30);
out.head = fly([20, 10, -60], [0, 0, 90], 2);             // straight at the north wall, under its roof
out.fast = fly([20, 10, -60], [0, 0, 900], 0.5, 30);      // ten times as fast, 30 frames a second: no tunnelling
out.over = fly([20, 40, -60], [0, 0, 90], 2);             // over the roof: on its way
''')
        self.assertAlmostEqual(o['head'][2], -3.0, delta=0.05)    # HIT_R off the wall
        self.assertAlmostEqual(o['fast'][2], -3.0, delta=0.05)
        self.assertGreater(o['over'][2], 100)
        self.assertAlmostEqual(o['over'][1], 40)

    def test_slides_along_a_wall(self):
        o = self.run_js('''
hitNote(box(0, 0, 400, 20), 30);
const v = [60, 0, 30];                                    // into the wall at a slant: the eye keeps its run along it
out.p = fly([20, 10, -10], v, 2);
''')
        self.assertAlmostEqual(o['p'][2], -3.0, delta=0.05)
        self.assertGreater(o['p'][0], 20 + 100)

    def test_lands_on_a_roof(self):
        o = self.run_js('''
hitNote(box(0, 0, 40, 20), 30);
out.p = fly([20, 60, 10], [0, -40, 0], 3);                // straight down onto the roof
out.lands = HIT.lands;
''')
        self.assertGreaterEqual(o['p'][1], 30 + 2.5)
        self.assertLess(o['p'][1], 30 + 2.5 + 1.6)
        self.assertGreater(o['lands'], 0)

    def test_starting_inside_lifts_onto_the_roof(self):
        o = self.run_js('''
hitNote(box(0, 0, 40, 20), 30);
out.p = fly([20, 10, 10], [0, 0, 0], 0.1);
out.lifts = HIT.lifts;
''')
        self.assertGreaterEqual(o['p'][1], 32.5)
        self.assertGreater(o['lifts'], 0)

    def test_narrow_gap_stops(self):
        o = self.run_js('''
hitNote(box(0, 0, 40, 20), 30); hitNote(box(0, 23, 40, 60), 30);   // a 3 m gap, narrower than the eye
out.p = fly([-30, 10, 21.5], [60, 0, 0], 2);
''')
        self.assertLess(o['p'][0], 0)
        self.assertAlmostEqual(o['p'][1], 10)

    def test_rebuild_rings_are_swept(self):
        o = self.run_js('''
REBUILD_OCC.push({ ring: box(0, 0, 20, 20), top: 25 }, { ring: box(100, 0, 120, 20) });   // the second has no top: ground only
out.p = fly([10, 10, -40], [0, 0, 60], 2);
out.cells = HIT.cells; out.occ = HIT.occN;
''')
        self.assertAlmostEqual(o['p'][2], -3.0, delta=0.05)
        self.assertEqual(o['cells'], 25)
        self.assertEqual(o['occ'], 2)

    def test_escape_hatch(self):
        o = self.run_js('''
hitNote(box(0, 0, 40, 20), 30);
out.p = fly([20, 10, -60], [0, 0, 90], 2);
out.cells = HIT.cells;
''', search='?collide=0')
        self.assertEqual(o['cells'], 0)
        self.assertGreater(o['p'][2], 100)

    def test_every_loop_notes(self):
        # the three building loops (the core, the outer districts, the far ring and the towns) and the landmarks that build
        # their own: every roofNote of a building's footprint has its hitNote beside it
        self.assertIn('hitFly(fly.pos, fly.vel, dt)', SRC)
        self.assertNotIn('fly.pos.addScaledVector(fly.vel, dt)', SRC)
        self.assertGreaterEqual(len(re.findall(r'hitNote\(poly, base \+ h\)', SRC)), 3)
        self.assertIn("hitNote(b.poly, siteY(rx, rz, 'ground') + b.h)", SRC)


if __name__ == '__main__':
    unittest.main()
