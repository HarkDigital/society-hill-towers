"""Round 226 (Mike, over the Vine Street Expressway at Logan Circle: "this view has the road running right into the
grass. Fix that."). The expressway's cut used to stop at 18th Street: bake_overpasses.py dropped both carriageways
from there to the tunnel under the Parkway (OSM's short tunnel pieces under the 18th and 19th Street bridges cut the
stretch into runs under the 40 m a run needs), the page drew them flat on the lawn, and they ended where the tunnel
begins. The tunnel's west mouth came up to street level inside the tunnel and had nothing built at it either.

What this file pins:
  - the cut reaches the tunnel: two open carriageways and the corridor from 18th Street to the east mouth, through
    the point Mike was looking at;
  - every tunnel mouth that open road runs into has a portal record, and the corridor's end there is closed by it;
  - the west mouth holds its depth and an approach carries each carriageway on to where the ground has come down;
  - the stretch east of 15th Street lies where it lay;
  - cover_flags, the bake's rule for what is a tunnel, on synthetic chains;
  - the page builds the portals, opens the ground over an approach, keeps the traffic and the buses on the sunken run
    and out of sight in the tunnel, carries the traffic's network through the tunnels its data leaves out, and does
    it without a new material or a line of shader text;
  - the survey's other find: a short underpass that touches down at both its ends (the I-76 ramps under Broad Street
    by the arena) no longer takes its road away and leaves both ends on the lawn.
"""
import ast
import json
import math
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIKE = (-2238.0, -1492.0)          # the ragged end of the road on the lawn in his view


def dist_to_run(p, run):
    best = 1e18
    for a, b in zip(run, run[1:]):
        dx, dz = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / (dx * dx + dz * dz or 1e-9)))
        best = min(best, math.hypot(a[0] + dx * t - p[0], a[1] + dz * t - p[1]))
    return best


class VineData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ov = json.loads((ROOT / 'overpasses.json').read_text())
        cls.sk = cls.ov['sk']
        cls.open = [c for c in cls.sk if not c['cov'] and not c.get('ap')]
        cls.cov = [c for c in cls.sk if c['cov']]
        cls.ap = [c for c in cls.sk if c.get('ap')]

    def test_shape(self):
        ov = self.ov
        self.assertEqual(len(ov['cor']), len(ov['ce']), 'one pair of end kinds per corridor run')
        for pair in ov['ce']:
            self.assertEqual(2, len(pair))
            self.assertTrue(all(k in (0, 1, 2) for k in pair))
        self.assertGreaterEqual(len(ov['por']), 2)
        for m in ov['por']:
            self.assertEqual(6, len(m))
            self.assertAlmostEqual(1.0, math.hypot(m[3], m[4]), places=2, msg='a portal points into its tunnel with a unit vector')
            self.assertGreater(m[5], 4)
        for c in self.ap:
            self.assertEqual(0, c['cov'])
            self.assertEqual([1, 0], c['e'], 'an approach is pinned at its mouth and comes out onto the ground')

    def test_the_cut_reaches_the_tunnel(self):
        """Two open carriageways and the corridor, unbroken, from 18th Street to the east mouth."""
        for x in range(-2285, -2045, 10):
            z = MIKE[1] + (x - MIKE[0]) * (31.0 / 193.0)       # the expressway's line there
            near = [c for c in self.open if dist_to_run((x, z), c['p']) < 12]
            self.assertEqual(2, len(near), 'two open sunken carriageways at x = %d, found %d' % (x, len(near)))
            self.assertTrue(any(dist_to_run((x, z), [q[:2] for q in run]) < 6 for run in self.ov['cor']), 'the corridor at x = %d' % x)
        for c in self.open:
            if dist_to_run(MIKE, c['p']) < 12:
                ys = [q[2] for q in c['p'] if -2300 < q[0] < -2040]
                self.assertTrue(ys and max(ys) < -5.5, 'the roadway stays down in its cut to the mouth: %s' % ys)

    def test_every_mouth_has_a_portal(self):
        """A covered run's end that an open run or an approach ends at is a mouth, and has a portal within 40 m."""
        ends = [(q, c) for c in self.open + self.ap for q in (c['p'][0], c['p'][-1])]
        mouths = 0
        for c in self.cov:
            for q in (c['p'][0], c['p'][-1]):
                if not any(math.hypot(q[0] - e[0], q[1] - e[1]) < 1.5 and abs(q[2] - e[2]) < 0.1 for e, _ in ends):
                    continue
                mouths += 1
                self.assertTrue(any(math.hypot(q[0] - m[0], q[1] - m[1]) < 40 for m in self.ov['por']),
                                'the mouth at %.0f, %.0f has no portal' % (q[0], q[1]))
        self.assertGreaterEqual(mouths, 4, 'the Parkway tunnel has four mouths, two carriageways at each end')

    def test_portals_close_the_corridor(self):
        ov = self.ov
        closed = 0
        for run, kinds in zip(ov['cor'], ov['ce']):
            for st, k in ((run[0], kinds[0]), (run[-1], kinds[1])):
                at = [m for m in ov['por'] if math.hypot(m[0] - st[0], m[1] - st[1]) < 1.0]
                if k == 1:
                    closed += 1
                    self.assertEqual(1, len(at), 'a portal stands at the corridor end %s' % st[:2])
                    m = at[0]
                    self.assertAlmostEqual(st[3], m[5], places=1, msg='the headwall spans the cut wall to wall')
                    self.assertAlmostEqual(st[2] + 0.45, m[2], delta=0.25, msg='the mouth at the roadway')
                else:
                    self.assertEqual([], at)
        self.assertEqual(2, closed, 'the cut runs into the tunnel at both its mouths')
        # the two portals face each other across the tunnel
        a, b = [m for m in ov['por'] if m[5] > 10][:2]
        self.assertLess(a[3] * b[3] + a[4] * b[4], -0.95)
        self.assertGreater(math.hypot(a[0] - b[0], a[1] - b[1]), 100)

    def test_the_west_mouth_holds_its_depth(self):
        """The tunnel no longer climbs to the street inside itself: both its runs stay down end to end, and an
        approach takes each on, level or falling, to where it meets the ground."""
        tunnel = [c for c in self.cov if any(dist_to_run(c['p'][0], [m[:2], m[:2]]) < 40 for m in self.ov['por'])]
        self.assertEqual(2, len(tunnel))
        for c in tunnel:
            self.assertLess(max(q[2] for q in c['p']), -5.5, 'a tunnel run comes up inside the tunnel')
        main = [c for c in self.ap if not c.get('rp')]
        self.assertEqual(2, len(main))
        for c in main:
            self.assertTrue(any(math.hypot(c['p'][0][0] - t['p'][k][0], c['p'][0][1] - t['p'][k][1]) < 1 and abs(c['p'][0][2] - t['p'][k][2]) < 0.05
                                for t in tunnel for k in (0, -1)), 'an approach starts at a mouth, at its height')
            ys = [q[2] for q in c['p']]
            self.assertTrue(all(b <= a + 0.06 for a, b in zip(ys, ys[1:])), 'an approach never climbs: %s' % ys)
            self.assertLess(c['p'][-1][0], c['p'][0][0] - 100, 'and runs west, to the ground the DEM shows it meeting')
        for c in self.ap:
            if c.get('rp'):
                self.assertTrue(any(dist_to_run(c['p'][0], m['p']) < 1 for m in main), 'a ramp leaves an approach')

    def test_east_of_15th_street_as_it_was(self):
        """The corridor still ends by 10th Street where it did, and the 39 m stub there is still left alone."""
        xs = sorted(st[0] for run in self.ov['cor'] for st in (run[0], run[-1]))
        self.assertAlmostEqual(-964.3, xs[-1], delta=0.6)
        self.assertEqual(0, self.ov['ce'][[i for i, r in enumerate(self.ov['cor']) if max(r[0][0], r[-1][0]) > -1000][0]][
            0 if self.ov['cor'][0][0][0] > -1000 else 1], 'the 10th Street end keeps its old face')
        self.assertTrue(any(abs(c['p'][-1][0] + 947.5) < 0.6 or abs(c['p'][0][0] + 947.5) < 0.6 for c in self.open))
        untouched = [c for c in self.sk if c['cov'] and not any(math.hypot(c['p'][0][0] - m[0], c['p'][0][1] - m[1]) < 40 for m in self.ov['por'])]
        self.assertEqual(8, len(untouched), 'the eight covered runs elsewhere in the city')
        self.assertFalse(any(math.hypot(m[0] - q[0], m[1] - q[1]) < 200 for c in untouched for q in c['p'] for m in self.ov['por']))

    def test_underpasses_at_grade(self):
        """A covered run under 100 m that touches down at both ends cannot be dug (its profile is the ground's):
        flagged g, so the page draws the packed road through instead of leaving a gap with both ends on the lawn.
        The long tunnels under 30th Street Station are not such a run, and keep their Round 85 treatment."""
        g = [c for c in self.sk if c.get('g')]
        self.assertEqual(4, len(g))
        for c in g:
            self.assertEqual(1, c['cov'])
            self.assertEqual([0, 0], c['e'])
            self.assertLess(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(c['p'], c['p'][1:])), 100)
        for c in self.cov:
            if not c.get('g') and c['e'] == [0, 0]:
                self.assertGreater(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(c['p'], c['p'][1:])), 600)


class CoverFlags(unittest.TestCase):
    """bake_overpasses.cover_flags on synthetic chains: points every 10 m along x, the roadway 6 m down."""
    @classmethod
    def setUpClass(cls):
        tree = ast.parse((ROOT / 'bake_overpasses.py').read_text())
        fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'cover_flags']
        consts = [n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') in ('SHORT_COVER', 'COVER_MIN', 'MOUTH_TRIM')]
        cls.ns = {'math': math}
        exec(compile(ast.Module(body=consts + fn, type_ignores=[]), 'bake_overpasses.py', 'exec'), cls.ns)

    def flags(self, tunnel, ground=lambda x: 0.0):
        n = len(tunnel)
        P = [[10.0 * i, 0.0, i, None] for i in range(n)]
        self.ns['W'] = {i: {'tunnel': bool(t)} for i, t in enumerate(tunnel)}
        self.ns['grade'] = lambda x, z: ground(x)
        return self.ns['cover_flags'](P, [10.0 * i for i in range(n)], [-6.0] * n)

    def test_a_bridge_shadow_is_open_cut(self):
        cov = self.flags([0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0])          # 20 m and 30 m of tunnel between open road
        self.assertFalse(any(cov), cov)

    def test_a_tunnel_stays_a_tunnel(self):
        t = [0] * 4 + [1] * 12 + [0] * 4
        self.assertEqual([bool(v) for v in t[:-1]], self.flags(t)[:-1])

    def test_no_ground_no_tunnel(self):
        """The DEM stands under COVER_MIN over the first 30 m of the tagged tunnel: the mouth is drawn back to
        where there is ground, and never by more than MOUTH_TRIM."""
        t = [0] * 4 + [1] * 14 + [0] * 4
        cov = self.flags(t, lambda x: -4.0 if x < 70 else 0.0)                # points at 40, 50, 60 lack cover
        self.assertEqual([False] * 7 + [True] * 11, cov[:18])
        cov = self.flags(t, lambda x: -4.0)                                   # no ground anywhere: 70 m at each mouth, no more
        self.assertEqual(4 + 7, cov.index(True))
        self.assertTrue(any(cov))

    def test_a_stub_at_the_chain_end_is_left_alone(self):
        t = [1, 1, 1, 0, 0, 0, 0, 0]                                        # 30 m of tunnel at the chain's end (10th Street's)
        self.assertEqual([True, True, True, False], self.flags(t, lambda x: -6.0)[:4])


class VinePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        a = cls.s.index("step('Raising the overpasses'")
        cls.step = cls.s[a:cls.s.index('  // ------------------------------------------------ trees', a)]
        a = cls.step.index('Round 226: the tunnel mouths')
        cls.portal = cls.step[a:cls.step.index('// ------- sunken carriageways and ramps', a)]

    def test_the_page_builds_the_mouths(self):
        self.assertIn('for (const m of OVP.por)', self.portal)
        for part in ('the headwall over the mouth', 'the pier between the carriageways', 'the soffit', 'the back', 'groundSheet(at,'):
            self.assertIn(part, self.portal)
        self.assertIn("if (ce[e2 ? 1 : 0] !== 0) continue;", self.step, 'the old end face stands down where a portal or the ground ends the cut')
        self.assertIn('PERF.portals = portalStat', self.step)

    def test_no_new_material_and_no_shader_text(self):
        """Mike's plan (Round 225): a release that edits shared shader text makes every device compile again. The
        mouths are parts of the overpasses' own mesh and the cut's own collars."""
        for word in ('onBeforeCompile', 'ShaderMaterial', 'new THREE.Mesh', 'Material(', 'gl_Frag', 'uniform '):
            self.assertNotIn(word, self.portal, word)
        self.assertEqual(1, self.step.count('const ovpMat = roadMat('))
        self.assertEqual(1, self.step.count('const collarMat = groundSurfMat('))

    def test_the_ground_is_open_over_an_approach(self):
        m = re.search(r'function cutHole\(x, z\) \{\s*return ([^;]+);', self.s)
        self.assertIn('apCutNear(x, z, 1)', m.group(1))
        self.assertIn('vineCut(x, z, 0.5) !== null || apCutNear(x, z, 0)', self.s, 'no pole stands in the cut')
        self.assertIn('vineCut(x, z, 2) !== null || apCutNear(x, z, 2)', self.s, 'nor a tree')

    def test_the_traffic_rides_the_sunken_run(self):
        a = self.s.index('        const oy = ovpDeckY(x, z, ux, uz);\n        // The aligned road')
        body = self.s[a:self.s.index('if (dead) {', a)]
        self.assertIn('const su = ovpSunkY(x, z, ux, uz);', body)
        self.assertLess(body.index('ovpSunkY'), body.index('sunkCutNear'), 'its own run first, the old depth test after')
        self.assertIn('if (cls === -2 && !OVP.sk[ovpSegs[s + 8] - 1000].pt) continue;', self.s, 'a tunnel without mouths keeps its traffic on the ground')
        self.assertIn('under?0:1', self.s.replace(' ', ''), 'a car in the tunnel is not drawn')
        self.assertIn('trafficBridge(trafficRuns);   // Round 226', self.s, "the network is carried through the tunnels bake_traffic.py leaves out")
        self.assertLess(self.s.index('trafficBridge(trafficRuns);'), self.s.index('    trafficPrepareGraph(trafficRuns);'), 'before the linker, which joins the new runs like any other')

    def test_a_bus_rides_the_cut(self):
        a = self.s.index('const oy = ovpDeckY(v.dx, v.dz, v.sdx, v.sdz);')
        body = self.s[a:a + 900]
        self.assertIn('const su = ovpSunkY(v.dx, v.dz, v.sdx, v.sdz, 7);', body)
        self.assertIn('if (v.tun) return;', body, 'and is not drawn in the tunnel')

    def test_an_underpass_at_grade_owns_nothing(self):
        self.assertIn('OVP.sk.forEach((c, ci) => { if (c.g) return;', self.s, 'ovpIndex leaves the packed road to draw through it')
        self.assertIn('if (c.g) continue;   // Round 226', self.step)

    def test_the_corridor_ends_square_for_an_approach(self):
        """vineCut rounds a run's end by its half width; an approach's own cut starts on the end's own line."""
        self.assertIn('if (square && (t < 0 || t > 1)) continue;', self.s)
        self.assertIn('if (ce[e2 ? 1 : 0] !== 2) continue;', self.step, 'and the corridor wall steps in to the approach wall there')


if __name__ == '__main__':
    unittest.main()
