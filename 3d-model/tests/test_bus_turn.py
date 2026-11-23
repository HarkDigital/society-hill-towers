"""Round 266 (Mike: SEPTA buses "appear to turn and then get course corrected to going straight midway through the turn").

A bus is drawn sliding from its last fix toward the new one, facing whichever street septaSnapRoad finds. With the nearest
street alone, a bus driving straight through a junction a few metres off its own centreline was handed the cross street
there, swung toward it and swung back. Run under Node with the page's own road grid and the updateTransit heading rule
(the snap every 120 ms, the yaw eased at 2.6 rad/s): straight through a junction the new rule never leaves the street's
heading, and round a real corner it turns once, without a reversal."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

SIM = r'''
const wrapPi = (a) => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
// a four-way junction at the origin: one street along x, one along z, cut in 40 m segments as the packed streets are
for (let k = -6; k < 6; k++) { septaRoadAdd(k * 40, 0, (k + 1) * 40, 0, 6, 4); septaRoadAdd(0, k * 40, 0, (k + 1) * 40, 6, 4); }
// a bus's fix slides from (x0, z0) to (x1, z1) over T seconds; the heading follows updateTransit's rule
function drive(x0, z0, x1, z1, old, yaw0) {
  const T = 15, dt = 1 / 30, cap = 2.6 * dt, tdl = Math.hypot(x1 - x0, z1 - z0), thx = (x1 - x0) / tdl, thz = (z1 - z0) / tdl;
  const yawT = Math.atan2(-thz, thx);
  let yaw = yaw0 === undefined ? yawT : yaw0, snT = -1, sdx = null, sdz = null, rev = 0, lastD = 0, maxOff = 0;
  const yaws = [];
  for (let t = 0; t <= T; t += dt) {
    const k = t / T, x = x0 + (x1 - x0) * k, z = z0 + (z1 - z0) * k;
    if (snT < 0 || t - snT > 0.12) {
      snT = t;
      const sn = old ? septaSnapRoad(x, z, 20) : septaSnapRoad(x, z, 20, thx, thz);
      sdx = sn ? sn[2] : null; sdz = sn ? sn[3] : null;
    }
    let goal = yawT;
    if (sdx != null) { const ry = Math.atan2(-sdz, sdx); goal = Math.abs(wrapPi(ry - yawT)) <= Math.PI / 2 ? ry : ry + Math.PI; }
    const d = wrapPi(goal - yaw), step = Math.abs(d) <= cap ? d : Math.sign(d) * cap;
    if (step && lastD && Math.sign(step) !== Math.sign(lastD)) rev++;
    if (step) lastD = step;
    yaw += step;
    yaws.push(yaw);
  }
  return { yaws, rev, end: wrapPi(yaw) };
}
const deg = (a) => +(Math.abs(wrapPi(a)) * 180 / Math.PI).toFixed(1);
const o = {};
// straight through, 1 to 6 m to the right of the centreline (a lane off it, or GPS scatter), both ways along each street
for (const old of [true, false]) {
  let worst = 0, rev = 0;
  for (const off of [1, 2.5, 4, 6]) for (const [x0, z0, x1, z1] of [[-150, off, 150, off], [150, -off, -150, -off], [off, -150, off, 150], [-off, 150, -off, -150]]) {
    const r = drive(x0, z0, x1, z1, old), want = Math.atan2(-(z1 - z0), x1 - x0);
    for (const y of r.yaws) worst = Math.max(worst, deg(y - want));
    rev += r.rev;
  }
  o[old ? 'straightOld' : 'straightNew'] = { worst, rev };
}
// a real turn: the last fix on the x street, the next round the corner on the z street, the bus facing along x as it came
for (const old of [true, false]) {
  const r = drive(-60, 3, -3, 60, old, 0);
  o[old ? 'turnOld' : 'turnNew'] = { rev: r.rev, endOff: deg(r.end - Math.atan2(-1, 0)) };
}
// every caller that passes no heading is answered as before: the nearest street
const a = septaSnapRoad(1, 3, 20), b = septaSnapRoad(1, 3, 20, 1, 0);
o.plain = [Math.abs(a[2]), Math.abs(a[3])]; o.toll = [Math.abs(b[2]), Math.abs(b[3])];
console.log(JSON.stringify(o));
'''


class BusTurn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        s = (ROOT / 'app.js').read_text()
        cls.src = s
        block = s[s.index('  const SEPTA_RG_CELL = 36;'):s.index('  function septaMerge(parts) {')]
        const = s[s.index('  const SEPTA_SNAP_TURN = '):]
        const = const[:const.index(';') + 1]
        script = 'const location = { search: "" };\n' + const + '\n' + block + SIM
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise AssertionError(r.stderr)
        cls.o = json.loads(r.stdout)

    def test_the_old_rule_swung_toward_the_cross_street(self):
        # the fault as Mike saw it: past 40 degrees toward the cross street and back
        self.assertGreater(self.o['straightOld']['worst'], 40, self.o)
        self.assertGreater(self.o['straightOld']['rev'], 0, self.o)

    def test_straight_through_stays_on_its_street(self):
        self.assertLess(self.o['straightNew']['worst'], 1, self.o)
        self.assertEqual(self.o['straightNew']['rev'], 0, self.o)

    def test_a_real_turn_turns_once(self):
        self.assertEqual(self.o['turnNew']['rev'], 0, self.o)
        self.assertLess(self.o['turnNew']['endOff'], 1, self.o)

    def test_no_heading_means_the_nearest_street(self):
        self.assertEqual([round(v, 6) for v in self.o['plain']], [0, 1])   # (1, 3) is nearer the z street
        self.assertEqual([round(v, 6) for v in self.o['toll']], [1, 0])   # travelling along x it keeps the x street

    def test_the_page_passes_the_travel_and_keeps_a_hatch(self):
        s = self.src
        self.assertIn('const sn = BUS_TURN_OLD ? septaSnapRoad(v.x, v.z, 20) : septaSnapRoad(v.x, v.z, 20, v.thx, v.thz);', s)
        self.assertIn('v.thx = tdl > 6 ? tdx / tdl : Math.cos(v.yawT); v.thz = tdl > 6 ? tdz / tdl : -Math.sin(v.yawT);', s)
        self.assertIn("BUS_TURN_OLD = /[?&]busturn=old\\b/.test(location.search);", s)


if __name__ == '__main__':
    unittest.main()
