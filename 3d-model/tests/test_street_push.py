"""Round 205: a pole or a trunk on a drawn street goes back to its kerb (streetPush), run on the page's own code."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i + len(a))]


class StreetPush(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')

    def test_the_index_carries_every_tiers_half_width(self):
        s = self.src
        self.assertIn('septaRoadAdd(run[i][0], run[i][1], run[i + 1][0], run[i + 1][1], r.w / 2, mot ? 0 :', s)   # the core (and its class, Round 207)
        self.assertEqual(s.count('septaRoadAdd(pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1], w / 2, t);'), 2)   # wide, far ring
        self.assertEqual(s.count('septaRoadAdd('), 4)   # the three passes and the definition
        self.assertIn('SRG.hw = SRG.hw.slice(0, n);', s)

    def test_the_trees_and_poles_take_it(self):
        s = self.src
        trees = cut(s, "  step('Planting the street trees'", "  step('Sowing the grass'")
        self.assertIn('const p = streetPush(x, z, 1.0, 4);', trees)
        self.assertIn("} else if (!STREET_PUSH && septaSnapRoad(x, z, 2.4)) continue;", trees)
        lamps = cut(s, "  step('Lighting the streetlamps'", "  step('Fitting out the rooftops'")
        self.assertIn('const p = streetPush(x, z, 0.5, Infinity);', lamps)
        self.assertIn("const STREET_PUSH = !/[?&]streetpush=0\\b/.test(location.search);", s)

    def run_node(self, body):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        fns = cut(self.src, '  function streetInside(', '\n  function septaRoadFreeze(')
        script = r'''
const clamp = (v, a, b) => Math.max(a, Math.min(b, v)), SEPTA_RG_CELL = 36;
const SEGS = [];   // [ax, az, bx, bz, hw]
const SRG = { seg: null, hw: null, ids: null };
function setRoads(list) { SEGS.length = 0; SEGS.push(...list); SRG.seg = Float64Array.from(list.flatMap((q) => q.slice(0, 4))); SRG.hw = Uint8Array.from(list.map((q) => Math.round(q[4] * 10))); SRG.ids = Uint32Array.from(list.map((q, i) => i)); }
function septaRoadCell() { return [0, SEGS.length]; }   // every segment in every cell: the search, not the grid, is under test
''' + fns + '\n' + body
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_a_point_on_the_asphalt_goes_to_its_own_kerb(self):
        out = self.run_node(r'''
setRoads([[-100, 0, 100, 0, 5]]);   // an east-west street, 10 m wide
const r = (p) => p && p !== false ? p.map((v) => +v.toFixed(2)) : p;
console.log(JSON.stringify({
  clear: streetPush(0, 6.5, 1.0, 4),        // already 1.5 m past the edge
  north: r(streetPush(10, -4, 1.0, 4)),     // 1 m inside, north side: to z = -6.02
  south: r(streetPush(10, 3, 0.5, 4)),      // the pole's clearance
  deep: streetPush(10, 0.5, 1.0, 4),        // 4.5 m in: no street tree
  centre: r(streetPush(10, 0, 0.5, Infinity)),
  end: r(streetPush(103, 0, 0.5, Infinity)),   // past the street's end: out along the radius
}));''')
        self.assertIsNone(out['clear'])
        self.assertEqual(out['north'], [10, -6.02])
        self.assertEqual(out['south'], [10, 5.52])
        self.assertIs(out['deep'], False)
        self.assertEqual(abs(out['centre'][1]), 5.52)
        self.assertEqual(out['end'], [105.52, 0])

    def test_a_corner_clears_both_streets_or_gives_up(self):
        out = self.run_node(r'''
setRoads([[-100, 0, 100, 0, 5], [0, -100, 0, 100, 5]]);   // a crossing
const p = streetPush(7, 4, 1.0, 4), inside = p ? !!streetInside(p[0], p[1], 1.0) : null;
const median = (setRoads([[-100, 0, 100, 0, 5], [-100, 12, 100, 12, 5]]), streetPush(0, 6, 0.5, Infinity));   // a 2 m median: room to stand
const between = (setRoads([[-100, 0, 100, 0, 5], [-100, 10.6, 100, 10.6, 5]]), streetPush(0, 5.3, 0.5, Infinity));   // 0.6 m: none
console.log(JSON.stringify({ p, inside, median, between }));''')
        self.assertTrue(out['p'])
        self.assertFalse(out['inside'])
        self.assertIsNone(out['median'])
        self.assertIs(out['between'], False)   # no kerb to stand at: the caller keeps the survey's point


if __name__ == '__main__':
    unittest.main()
