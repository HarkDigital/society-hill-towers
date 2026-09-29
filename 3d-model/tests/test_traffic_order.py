"""Round 168: trafficLeaders walks only the runs that hold cars and orders each by insertion.

The old block called Array.prototype.sort on every one of the 46,131 runs every frame, nearly all of them empty. The new
one walks trafficBusy (a run joins when a car is pushed on, in carSpawn and carTransfer, and leaves when the walk finds
it empty), gives a lone car no leader, and puts two or more in order by insertion over the order the last frame left.
Both sorts are stable and the runs independent, so the order and every leader must be exactly the old ones: the block is
cut from app.js and run under Node beside the old code over many frames of moving, overtaking, arriving, leaving and
transferring cars, with ties in distance, lane and direction, and the orders and leaders compared frame by frame."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

OLD = r'''
function oldLeaders(runs, lead) {
  for (const r of runs) {
    r.sort((a,b)=>a.dir-b.dir||a.lane-b.lane||a.s-b.s);
    for (let i=0;i<r.length;i++) {
      const c=r[i],l=r[i+(c.dir>0?1:-1)];
      lead.set(c, l&&l.dir===c.dir&&l.lane===c.lane?l:null);
    }
  }
}
'''


class TrafficOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = (ROOT / 'app.js').read_text()
        cls.src = src
        cls.block = src[src.index('  const trafficBusy = [];'):src.index('  function trafficAdvance(now,dt) {')]

    def run_js(self, body):
        script = 'const trafficRuns = [];\n' + self.block + OLD + body
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_block_sorts_nothing_whole(self):
        self.assertNotIn('.sort(', self.block)
        self.assertIn('if(n<2){cars[0].leader=null;continue;}', self.block)
        self.assertIn('if(!n){r.busy=false;continue;}', self.block)

    def test_every_car_that_joins_a_run_puts_the_run_on_the_walk(self):
        import re
        pushes = re.findall(r'(\w+)\.cars\.push\(car\);(\w+)\((\w+)\);', self.src)
        self.assertEqual(sorted(pushes), [('next', 'trafficHold', 'next'), ('r', 'trafficHold', 'r')])   # carTransfer and carSpawn
        self.assertEqual(len(re.findall(r'\.cars\.push\(', self.src[self.src.index("  step('Setting the traffic flowing'"):self.src.index('  function trafficAdvance(now,dt) {')])), 2)
        self.assertIn('want: 0, cars: [], busy: false });', self.src)

    def test_identical_order_and_leaders_over_many_frames(self):
        out = self.run_js(r'''
let seed = 12345;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
let nextId = 0;
const mk = () => { const stuck = rnd() < 0.3; return { id: nextId++, stuck, dir: rnd() < 0.5 ? 1 : -1, lane: stuck ? 0 : Math.floor(rnd() * 3), s: stuck ? Math.floor(rnd() * 3) * 10 : rnd() * 300, leader: 'stale' }; };   // a stuck car waits at a light: equal keys
const put = (r, c) => { r.cars.push(c); trafficHold(r); };   // carSpawn's and carTransfer's own two steps
for (let i = 0; i < 400; i++) { const r = { cars: [], busy: false }; trafficRuns.push(r); const n = i % 7 === 0 ? Math.floor(rnd() * 14) : i % 3 === 0 ? 1 : 0; for (let k = 0; k < n; k++) put(r, mk()); }
let frames = 0, compared = 0, multi = 0, lone = 0, ties = 0, walked = 0, mismatch = [];
for (let f = 0; f < 600; f++) {
  // the frame's traffic: most cars creep forward, a few overtake or jump, some arrive (pushed on the end) or leave (spliced)
  for (const r of trafficRuns) {
    for (const c of r.cars) { if (c.stuck) { if (rnd() < 0.01) c.stuck = false; continue; } const u = rnd(); c.s += u < 0.9 ? c.dir * rnd() * 0.5 : u < 0.97 ? c.dir * rnd() * 25 : (rnd() - 0.5) * 200; if (rnd() < 0.01) c.lane = Math.floor(rnd() * 3); if (rnd() < 0.02) c.s = Math.round(c.s / 10) * 10; }
    if (rnd() < 0.01) put(r, mk());
    if (r.cars.length && rnd() < 0.03) r.cars.splice(Math.floor(rnd() * r.cars.length), 1);
    if (r.cars.length && rnd() < 0.02) { const c = r.cars.splice(Math.floor(rnd() * r.cars.length), 1)[0]; put(trafficRuns[Math.floor(rnd() * trafficRuns.length)], c); }   // a transfer
  }
  walked += trafficBusy.length;
  const copies = trafficRuns.map((r) => r.cars.slice()), lead = new Map();
  oldLeaders(copies, lead);
  trafficLeaders();
  frames++;
  trafficRuns.forEach((r, i) => {
    const a = r.cars.map((c) => c.id).join(','), b = copies[i].map((c) => c.id).join(',');
    if (a !== b) mismatch.push(['order', f, i, a, b]);
    for (const c of r.cars) { compared++; if (c.leader !== lead.get(c)) mismatch.push(['leader', f, i, c.id]); }
    if (r.cars.length > 1) multi++; else if (r.cars.length === 1) lone++;
    for (let k = 1; k < r.cars.length; k++) { const p = r.cars[k - 1], c = r.cars[k]; if (p.dir === c.dir && p.lane === c.lane && p.s === c.s) ties++; }
  });
}
const stale = trafficRuns.filter((r) => r.cars.length && !r.busy).length;
console.log(JSON.stringify({ frames, compared, multi, lone, ties, walked: walked / frames, runs: trafficRuns.length, stale, mismatch: mismatch.slice(0, 5), n: mismatch.length }));''')
        self.assertEqual(out['n'], 0, out['mismatch'])
        self.assertGreater(out['compared'], 100000)
        self.assertGreater(out['multi'], 10000)          # runs of two or more were ordered
        self.assertGreater(out['lone'], 10000)           # and lone cars had their leader cleared
        self.assertGreater(out['ties'], 100)             # equal keys kept their order, as the stable sort keeps it
        self.assertEqual(out['stale'], 0)                # no run holds a car off the walk
        self.assertLess(out['walked'], out['runs'] * 0.7)   # and the walk passes the empty runs by

    def test_a_lone_car_loses_a_stale_leader_and_an_empty_run_is_left_alone(self):
        out = self.run_js(r'''
const a = { dir: 1, lane: 0, s: 5, leader: {} }, b = { dir: 1, lane: 0, s: 9, leader: null };
trafficRuns.push({ cars: [a], busy: false }, { cars: [], busy: false }, { cars: [b, { dir: 1, lane: 0, s: 1, leader: null }], busy: false });
for (const r of trafficRuns) trafficHold(r);
trafficLeaders();
console.log(JSON.stringify({ lone: a.leader, empty: trafficRuns[1].cars.length, off: trafficRuns[1].busy, walk: trafficBusy.length, order: trafficRuns[2].cars.map((c) => c.s), lead: trafficRuns[2].cars[0].leader === b }));''')
        self.assertIsNone(out['lone'])
        self.assertEqual(out['empty'], 0)
        self.assertFalse(out['off'])                     # the empty run left the walk
        self.assertEqual(out['walk'], 2)
        self.assertEqual(out['order'], [1, 9])
        self.assertTrue(out['lead'])


if __name__ == '__main__':
    unittest.main()
