"""Round 251: the buses keep a lane clear of the parked cars, nearest their fix; and no grass grows through paving.

Mike, Nov 13, with a screenshot of a Route 57 bus half inside a parked car on S 4th Street between Chestnut and Walnut: "is
it possible to not have the busses clip parked cars? Can the bus always stay in the lane closest to it's real world
position?" Round 207 stood a bus CAR_OFFW of its class right of the drawn street's centreline, the two-way streets' lane, on
every street: S 4th Street there is one lane one way between two parked rows (7 m drawn), so the bus stood 1.6 m off the
middle with its flank 1.2 m into the right-hand row. Now a bus near the eye takes the traffic run's own lanes (busLaneOf):

  * a one-way street's lanes as the traffic lays them, the one nearest the fix, kept until another is BUS_LANE_HYST nearer;
  * a two-way street's lane on the bus's own side, whatever side of the centreline the fix lies;
  * clear of a kerb that parks by the widest parked car's inner flank and BUS_LANE_AIR, of a bare kerb by 0.1 m, and on a
    street with room for neither, the middle of what is left;
  * busRunSnap keeps a bus at a junction on the street along its heading, and off a motorway unless the drawn street is one;
  * the last check (busLaneDodge): where the bus, a little longer and ahead of itself, would still come within
    BUS_LANE_AIR of a parked car as drawn, it takes the nearest place across the street, inside its kerbs, that clears.

Two parking rules go with it, both measured by the buses' survey (__dbg.busParkSurvey): a car inside the roadway of a
street that meets its run at under 30 degrees parks no more (parkedInSlant, ?parkslant=0: Round 240's rules took only the
streets at 30 degrees or more), and a street with a SEPTA stop parks no car a bus in its lane would touch going round a
bend (parkedBusClear, swept only near a bend or on a squeezed street). The survey over six districts found the old rule in
a parked car along 9 to 56 km of each district's bus streets and the new at 0 to 3 places of about 100,000.

The functions run under Node, cut from app.js, over modelled streets. The wiring is read from the source: on by default,
?buslane=old keeps Round 207's rule, the run index is typed (a Map of arrays was 64,000 of them) and built behind the veil.

The second half, from the same screenshot ("Also in that shot, grass is coming through the sidewalk. Can we clean that up
everywhere?"): every tuft sample asks grassPaved (a drawn street of any tier to its edge, a walk or path, an outer sidewalk
ring); the walks are indexed where each tier lays them (walkNote, walkSeg), and walkAt is exact on a merged centreline.
"""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


def cut(a, b):
    i = SRC.index(a)
    return SRC[i:SRC.index(b, i)]


def line(a):
    i = SRC.index(a)
    return SRC[i:SRC.index('\n', i)] + '\n'


HARNESS = r"""
const REAL = true, location = { search: '' };
%(clamp)s
%(models)s
%(offw)s
const PARK2 = true, PARK_KERB = %(kerb)s;
%(kerbin)s
%(count)s
%(offset)s
const parkedShift = (r) => r.sh || 0, parkedRunOK = () => true, parkedSides = (r) => r.sides, parkHalfW = (r) => r.hw;
const PARKED = { on: true }, trafficRuns = [];
%(kind)s
%(lanes)s
%(boxgap)s
const van = CAR_MODELS[5].w, half = 1.3, out = { cases: {} };
const inner = (r) => r.hw - PARK_KERB - van;   // the widest parked car's inner flank
// every fix across the street, both ways along it: the worst clearance to a parked row (or a bare kerb) and the lanes taken
function sweep(name, r, hwD) {
  let worstPark = Infinity, worstKerb = Infinity, sq = false;
  const lanes = { '1': new Set(), '-1': new Set() };
  for (const bdir of [1, -1]) for (let lat = -6; lat <= 6; lat += 0.125) {
    const ln = busLaneOf(r, bdir, lat, null, half, hwD);
    sq = sq || busLaneOf.squeezed;
    lanes[bdir].add(+ln.toFixed(3));
    for (const s of [1, -1]) {   // the bus's right (s 1) is the run's side bdir
      const flank = s * ln + half, side = s * bdir;
      if (r.sides.indexOf(side) >= 0) worstPark = Math.min(worstPark, inner(r) - flank);
      else worstKerb = Math.min(worstKerb, Math.min(r.hw, hwD || r.hw) - flank);
    }
  }
  out.cases[name] = { worstPark: worstPark === Infinity ? null : +worstPark.toFixed(4), worstKerb: worstKerb === Infinity ? null : +worstKerb.toFixed(4),
    squeezed: sq, lanes: { '1': [...lanes['1']].sort((a, b) => a - b), '-1': [...lanes['-1']].sort((a, b) => a - b) } };
}
sweep('s4th', { oneway: true, cls: 5, hw: 3.5, sides: [1, -1] }, 3.5);
sweep('tertiaryTwoWay', { oneway: false, cls: 4, hw: 4.5, sides: [1, -1] }, 4.5);
sweep('secondaryOneWay', { oneway: true, cls: 3, hw: 5.5, sides: [1, -1] }, 5.5);
sweep('oneKerb', { oneway: true, cls: 5, hw: 3.0, sides: [1], sh: -1.07 }, 3.0);
sweep('tooNarrow', { oneway: true, cls: 5, hw: 3.0, sides: [1, -1] }, 3.0);
sweep('bare', { oneway: false, cls: 5, hw: 3.5, sides: [] }, 3.5);
sweep('bareNarrowed', { oneway: false, cls: 5, hw: 3.5, sides: [] }, 2.6);
// the lane nearest the fix, and the hold against the scatter between fixes
const two = { oneway: true, cls: 3, hw: 5.5, sides: [1, -1] };
out.pick = [2, 0.1, -0.1, -1.2].map((lat) => busLaneOf(two, 1, lat, null, half, 5.5));
out.hold = [[-0.3, 1.6], [-0.45, 1.6], [-0.55, 1.6], [0.3, -1.6], [1.0, -1.6]].map(([lat, keep]) => busLaneOf(two, 1, lat, keep, half, 5.5));
out.against = busLaneOf(two, -1, 2, null, half, 5.5);
// Round 207's rule on S 4th Street, for the record: CAR_OFFW[5] right of the middle, short of the kerb
out.oldS4th = Math.min(CAR_OFFW[5], Math.max(0, 3.5 - half - 0.1)) + half - (3.5 - PARK_KERB - CAR_MODELS[1].w);
// the run snap: a junction of an east-west run and a north-south one, a motorway beside them
const run = (pts, cls) => ({ xs: Float32Array.from(pts.map((p) => p[0])), zs: Float32Array.from(pts.map((p) => p[1])), cls });
trafficRuns.push(run([[-100, 0], [100, 0]], 3), run([[0, -100], [0, 100]], 4), run([[-100, 30], [100, 30]], 0));
busRunCells();
const snap = (x, z, hx, hz, mot) => { const b = busRunSnap(x, z, 20, hx, hz, mot); return b ? b.ri : -1; };
out.snap = { southbound: snap(2, 1, 0, 1), eastbound: snap(2, 1, 1, 0), nearMotorway: snap(50, 18, 1, 0), onMotorway: snap(50, 18, 1, 0, true), far: snap(50, 60, 1, 0) };
out.index = { typed: BUSRUN.off instanceof Int32Array && BUSRUN.ids instanceof Int32Array, refs: BUSRUN.ids.length };
// the dodge: a car parked in the middle of a 7 m street's lane, 10 m ahead (a car of a street at a slant), and a bus
// heading east along z = 0 in the middle; then a car at the kerb that leaves the lane clear
const sp = SEPTA_KIND.bus, G = new Map(), lim = 3.5 - 0.1 - sp.w / 2;
parkedHitAdd(G, 10, 0.4, 0, 1);
const d1 = busLaneDodge(G, 0, 0, 1, 0, 0, sp, lim);
out.dodge = { lane: d1, moved: busLaneDodge.moved, gap: +busParkedGap(G, BUS_DODGE_AHEAD, d1, 1, 0, sp.l / 2 + BUS_DODGE_LONG, sp.w / 2).toFixed(3) };
const G2 = new Map(); parkedHitAdd(G2, 10, -2.4, 0, 5);   // a van at the left kerb (z -2.4: the bus's right is +z heading east)
out.kerbCar = { lane: busLaneDodge(G2, 0, 0, 1, 0, 0, sp, lim), moved: busLaneDodge.moved };
const G3 = new Map(); for (const z of [-2.4, 2.4]) parkedHitAdd(G3, 4, z, 0, 5); parkedHitAdd(G3, 12, 0, 0, 3);   // a car in the middle between two rows
out.blocked = { lane: busLaneDodge(G3, 0, 0, 1, 0, 0, sp, lim), moved: busLaneDodge.moved };
console.log(JSON.stringify(out));
"""

GRASS = r"""
%(clamp)s
%(walks)s
// a sidewalk densified to 1.5 m as the core lays it, along a 60 m straight and round a right-angle corner
const pts = [];
for (let s = 0; s <= 60; s += 1.5) pts.push([s, 0]);
for (let s = 1.5; s <= 30; s += 1.5) pts.push([60, s]);
walkNote(pts, 1.5);
walkSeg(100, 100, 130, 100, 0.9);   // a footway of the outer tiers
const at = (x, z, pad) => walkAt(x, z, pad);
console.log(JSON.stringify({ n: WALK.n, inside: [at(30, 1.4, 0), at(30, -1.4, 0), at(60.5, 20, 0), at(115, 100.8, 0)],
  pad: [at(30, 1.55, GRASS_KERB), at(30, 1.59, GRASS_KERB), at(115, 100.95, GRASS_KERB)], outside: [at(30, 1.6, 0), at(30, 1.65, GRASS_KERB), at(70, 15, GRASS_KERB), at(115, 101.05, GRASS_KERB)], kerb: GRASS_KERB }));
"""


def run_node(text):
    run = subprocess.run(['node', '-e', text], capture_output=True, text=True, timeout=60)
    if run.returncode:
        raise AssertionError(run.stderr or run.stdout)
    return json.loads(run.stdout)


class BusLanes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        kerb = re.search(r'const PARK_KERB = ([0-9.]+)', SRC).group(1)
        cls.r = run_node(HARNESS % {
            'clamp': line('  function clamp(v, a, b)'),
            'models': cut('  const CAR_K = REAL ?', '  const CAR_OFFW = '),
            'offw': line('  const CAR_OFFW = '),
            'kerb': kerb,
            'kerbin': line('  const parkKerbIn = '),
            'count': line('  function carLaneCount(r)'),
            'offset': line('  function carOffset(r, lane)'),
            'lanes': cut('  const BUS_RUN_CELL = ', '  // the snap and the lane for a bus near the eye'),
            'kind': cut('  const SEPTA_KIND = {', '  const SEPTA_TINT = '),
            'boxgap': cut('  // the gap between two boxes on the ground', '  function trafficAdvance('),
        })
        cls.air = float(re.search(r'BUS_LANE_AIR = ([0-9.]+)', SRC).group(1))

    def test_s4th_street_keeps_the_middle_clear_of_both_rows(self):
        c = self.r['cases']['s4th']
        self.assertEqual(c['lanes'], {'1': [0], '-1': [0]})   # its one lane, whatever the fix
        self.assertGreaterEqual(c['worstPark'], self.air - 1e-6)
        self.assertFalse(c['squeezed'])
        self.assertGreater(self.r['oldS4th'], 1.0)   # Round 207's rule ran 1.2 m into the row

    def test_every_modelled_street_clears_its_parked_rows_and_kerbs(self):
        for name, c in self.r['cases'].items():
            if c['worstPark'] is not None and not c['squeezed']:
                self.assertGreaterEqual(c['worstPark'], self.air - 1e-6, name)
            if c['worstKerb'] is not None and not c['squeezed']:
                self.assertGreaterEqual(c['worstKerb'], 0.1 - 1e-6, name)

    def test_two_way_street_keeps_its_own_side(self):
        c = self.r['cases']['tertiaryTwoWay']
        for d in ('1', '-1'):
            self.assertEqual(len(c['lanes'][d]), 1)
            self.assertGreater(c['lanes'][d][0], 0.8)   # right of its heading even with the fix over the centreline
        self.assertEqual(self.r['cases']['bare']['lanes']['1'], [1.6])
        self.assertEqual(self.r['cases']['bareNarrowed']['lanes']['1'], [1.2])   # the drawn kerb where it stands

    def test_nearest_lane_with_a_hold(self):
        self.assertEqual(self.r['pick'], [1.6, 1.6, -1.6, -1.6])
        self.assertEqual(self.r['hold'], [1.6, 1.6, -1.6, -1.6, 1.6])   # held to half the hold past the middle
        self.assertEqual(self.r['against'], 1.6)   # against the run, its lanes in its own frame

    def test_one_kerb_street_rides_the_traffic_lane(self):
        c = self.r['cases']['oneKerb']
        self.assertEqual(c['lanes']['1'], [-1.07])
        self.assertEqual(c['lanes']['-1'], [1.07])

    def test_no_room_takes_the_middle(self):
        c = self.r['cases']['tooNarrow']
        self.assertTrue(c['squeezed'])
        self.assertEqual(c['lanes'], {'1': [0], '-1': [0]})

    def test_run_snap_keeps_the_street_along_the_heading(self):
        s = self.r['snap']
        self.assertEqual(s['southbound'], 1)
        self.assertEqual(s['eastbound'], 0)
        self.assertEqual(s['nearMotorway'], 0)   # the street 18 m off, not the motorway 12 m off
        self.assertEqual(s['onMotorway'], 2)
        self.assertEqual(s['far'], -1)
        self.assertTrue(self.r['index']['typed'])

    def test_dodge_clears_a_car_in_the_lane(self):
        d = self.r['dodge']
        self.assertTrue(d['moved'])
        self.assertGreaterEqual(d['gap'], self.air - 1e-6)
        self.assertLessEqual(abs(d['lane']), 3.5 - 0.1 - 1.3 + 1e-9)   # inside its kerbs
        self.assertEqual(self.r['kerbCar'], {'lane': 0, 'moved': False})   # a kerb row the lane clears: no move
        self.assertFalse(self.r['blocked']['moved'] and abs(self.r['blocked']['lane']) > 2.1)

    def test_wiring(self):
        self.assertIn("const BUS_LANES = BUS_YIELD && !/[?&]buslane=old\\b/.test(location.search);", SRC)
        self.assertIn('if (BUS_LANES && trafficReady && (v.x - camera.position.x) ** 2 + (v.z - camera.position.z) ** 2 < (NEAR_R + BUS_LANE_PAD) ** 2) busLaneSnap(v, sn);', SRC)
        self.assertIn('    trafficReady = true;\n    if (BUS_LANES) busRunCells();', SRC)
        self.assertIn('wx = v.snx + Math.sin(v.yaw) * ln; wz = v.snz + Math.cos(v.yaw) * ln;', SRC)   # Round 207's rule kept for ?buslane=old and far buses
        body = cut('  function busRunCells() {', '  const _brs = ')
        self.assertNotIn('new Map', body)
        self.assertIn('if (window.__dbg && !window.__dbg.busLanes) busLaneProbes();', SRC)
        self.assertIn('if (G.size) lane = busLaneDodge(G, b.px, b.pz, b.ux * bdir, b.uz * bdir, lane, sp,', SRC)
        lay = cut('  function parkedLay(now) {', '  function updateParked(now) {')
        self.assertIn('PARKED_HIT.clear();', lay)
        self.assertIn('parkedHitAdd(PARKED_HIT, x, z, yaw, kind);', lay)   # every car the lay draws, and only those

    def test_parking_rules(self):
        expand = cut('  function parkedExpand(ri) {', '  // Round 240 (Mike, Nov 11, over Center City')
        self.assertIn('if (PARKED.slant && parkedInSlant(r, sl, _pkS.x, _pkS.z, _pkS.yaw))', expand)
        self.assertIn('if (busSt && !parkedBusClear(r, sl, _pkS.x, _pkS.z, _pkS.yaw, kind, side * u))', expand)
        self.assertIn("PARKED.slant = PARK2 && !/[?&]parkslant=0\\b/.test(location.search);", SRC)
        self.assertIn('PARKED.busSweep = PARK2 && !/[?&](buslane=old|busyield=0)\\b/.test(location.search);', SRC)   # BUS_LANES, as the traffic section reads it
        # the slant candidates come from the junction scan's own walk of the pieces near a run (no second scan)
        jx = cut('  function parkedJunctions(r) {', '  // a car len long at arc s of run r')
        self.assertIn('if (Math.abs(den) < PARK_JX_SIN) { shallow = true; continue; }', jx)
        self.assertIn('r.pkS = Float32Array.from(slant);', jx)


class GrassOffPaving(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = run_node(GRASS % {
            'clamp': line('  function clamp(v, a, b)'),
            'walks': cut('  const GRASS_KERB = ', '  function grassPaved('),
        })

    def test_walks_merge_and_hit_exactly(self):
        self.assertLessEqual(self.r['n'], 4)   # 61 densified points become the two legs and the footway
        self.assertEqual(self.r['inside'], [True, True, True, True])
        self.assertEqual(self.r['pad'], [True, True, True])
        self.assertEqual(self.r['outside'], [False, False, False, False])
        self.assertEqual(self.r['kerb'], 0.1)   # 0.35 left a bare band along every path

    def test_every_sample_asks_for_paving(self):
        self.assertIn("const GRASS_PAVE = !/[?&]grasswalk=0\\b/.test(location.search);", SRC)
        self.assertIn('if (GRASS_PAVE ? grassPaved(x, z) : septaSnapRoad(x, z, 4)) continue;', SRC)
        self.assertIn('function grassPaved(x, z) { return !!streetInside(x, z, GRASS_KERB) || walkAt(x, z, GRASS_KERB) || sidewalkAt(x, z); }', SRC)

    def test_each_tier_indexes_its_walks(self):
        roads = cut('    // ---- sidewalks and crossings, now that every carriageway is known', '    for (const run of splitRuns(pts, cls.map((c) => c === \'x\')))')
        self.assertIn('walkNote(run, (j.w || 3.0) / 2)', roads)   # the core's generated sidewalks
        self.assertIn('walkNote(run, j.w / 2)', roads)            # its mapped footways
        self.assertIn('if (foot) walkNote(run, r.w / 2);', SRC)   # its pedestrian streets
        self.assertEqual(SRC.count('else if (t === 6) for (let j = 0; j + 1 < pts.length; j++) walkSeg('), 2)   # the outer districts' and the far ring's footways


if __name__ == '__main__':
    unittest.main()
