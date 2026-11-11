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
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
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

    def test_a_pier_covers_each_end_of_the_headwall(self):
        """The corridor's last stretch is not square to the way into its tunnel (the bake gives the mouth its own
        direction), so the cut's wall ends short of the headwall's face on one side: by the mouth's half width times
        the sine of the angle between them, 0.33 m at the west mouth. A pier 0.5 m out from the face covers the end."""
        self.assertIn('for (const sg of [-1, 1]) { const pc = at(-0.2, sg * (hw + 0.33)); boxAt(pc[0], pc[1], dx, dz, 0.6, 0.7, floor - 0.6, top, tint(cWall, 1)); }', self.portal)
        ov = json.loads((ROOT / 'overpasses.json').read_text())
        worst = 0.0
        for m in ov['por']:
            ends = [(run[0], run[1]) for run in ov['cor']] + [(run[-1], run[-2]) for run in ov['cor']]
            e, b = min(ends, key=lambda q: math.hypot(q[0][0] - m[0], q[0][1] - m[1]))
            self.assertLess(math.hypot(e[0] - m[0], e[1] - m[1]), 1.0, 'a mouth stands on its corridor end')
            dx, dz = b[0] - e[0], b[1] - e[1]
            L = math.hypot(dx, dz)
            short = m[5] * abs(m[3] * dz / L - m[4] * dx / L)       # how far the wall's end stands off the mouth's own line
            worst = max(worst, short)
            self.assertLess(short, 0.45, 'the pier (0.5 m out from the face) covers the end of the wall at %s' % m[:2])
        self.assertGreater(worst, 0.2, 'the west mouth is the one that showed it')

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


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class LawnUnder(unittest.TestCase):
    """The slivers (Round 226's last open item: from the lowest eye the flight allows, the world's underside showed
    beside the far ends of the two approach cuts). The cause, measured on the page with a plan view from overhead and a
    pick through each magenta pixel of the walk: the lawn put back over opened ground cells has no ground mesh under
    it, and trimTerrainPatch takes a road's triangle out of it and leaves nothing in its place. So (1) wherever the
    lawn stood over what cut it, the step had no riser (a street laid flat across the old cut's valley 0.5 m under the
    lawn beside it; an approach wall's top, a chord between stations 13 m apart, 0.3 m under a lawn that is a 5 m
    lattice), and (2) under a street's sheet where the lawn was cut away there was no floor (a motorway's sheet lies
    0.6 m over its ground), seen in from under the sheet's far edge. From straight overhead there was no hole at all.

    lawnUnder gives the lawn a floor under what cut it and a riser at every step. This runs the page's own text (the
    trim and lawnUnder, cut from app.js) under Node on a lawn over one opened cell, a bank with a hump in it, with a
    street laid flat across it and a cut through it, and looks from every side: an eye at least 2.5 m over the ground
    looks at a point under the lawn, and the ray must hit the lawn, a road, the floor or a riser before it comes under
    the ground at the cell's rim. With the trim alone thousands of rays in 30,000 get through; with lawnUnder none of
    120,000 does."""

    @classmethod
    def setUpClass(cls):
        src = (ROOT / 'app.js').read_text()

        def fn(name):
            i = src.index('\n  function ' + name + '(') + 1
            return src[i:src.index('\n  }\n', i) + 5]

        def line(a):
            i = src.index(a)
            return src[i:src.index('\n', i) + 1]

        cls.src = src
        cls.fn = fn('lawnUnder')
        a = src.index("step('Raising the overpasses'")
        cls.step = src[a:src.index('  // ------------------------------------------------ trees', a)]
        js = (line('  const TERRAIN_PATCH_CELL = 50, TERRAIN_PATCH_CLEARANCE') + 'let terrainRoadGrid = null;\n'
              + line('  const TRS = { w: new Float32Array(9 * 65536), n: 0 };') + line('  const TERRAIN_PATCH_STATS = ')
              + line('  const LAWN_DROP = ') + line('  function lerp(a, b, t) {')
              + ''.join(fn(n) for n in ('signedArea', 'tidyRing', 'triangleGrade', 'streetBounds', 'streetIntersection', 'trsAdd',
                                        'trsPoly', 'trsOverlap', 'terrainPatchCells', 'outsideConvex', 'trimTerrainPatch', 'zoneSpans', 'lawnUnder'))
              + LAWN_HARNESS)
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
            f.write(js)
        try:
            r = subprocess.run(['node', f.name], capture_output=True, text=True, timeout=600)
        finally:
            os.unlink(f.name)
        if r.returncode:
            raise AssertionError(r.stderr[-3000:])
        cls.res = json.loads(r.stdout)

    def test_the_trim_alone_is_open(self):
        """The harness sees the defect: without the floor and the risers, rays get under the lawn in every scene."""
        for name in ('street', 'cut', 'both'):
            self.assertGreater(self.res[name]['without'], 100, name)

    def test_no_ray_reaches_the_underside(self):
        for name in ('street', 'cut', 'both'):
            r = self.res[name]
            self.assertEqual(0, r['with'], '%s: %d rays under the lawn, the first %s' % (name, r['with'], r['where'][:2]))
            self.assertGreater(r['st']['floor'], 10, name)
            self.assertGreater(r['st']['riser'], 50, name)
            self.assertGreater(r['st']['rim'], 0, name + ': the street and the cut both leave the cell under its rim')

    def test_the_floor_lies_under_what_cut_it(self):
        """Never grass through the asphalt: every corner and middle of every floor triangle is at least the trim's own
        clearance under every road over it."""
        for name in ('street', 'cut', 'both'):
            r = self.res[name]
            self.assertGreater(r['floorTris'], 10, name)
            self.assertEqual(0, r['over'], name)
            self.assertGreaterEqual(r['low'], 0.08 - 1e-4, name)

    def test_nothing_under_a_tunnels_roof(self):
        """A riser hung from the lawn over the tunnel to the cut's floor would stand across the mouth: over a roof the
        floor and the risers stop on it."""
        r = self.res['roof']
        self.assertGreater(r['plain'], 20, 'the scene does go below the roof line without one')
        self.assertEqual(0, r['roofed'])
        self.assertGreater(r['inside'], 100)
        self.assertEqual(0, r['out'], "nothing in a headwall's own footprint")

    def test_a_deep_cut_keeps_its_own_walls(self):
        """The corridor and an approach near its mouth lie metres under the lawn and have walls with parapets. A floor
        laid under them would hang under a bridge's deck, and a riser beside them in the cut's own air."""
        r = self.res['deep']
        self.assertEqual(0, r['alone'], 'a lawn only a deep cut touches gets nothing')
        self.assertGreater(r['both'], 50, "the street beside it still gets its floor")
        self.assertEqual(0, r['floorInCut'], "and that floor stops at the cut's line")
        self.assertIn('if (step > LAWN_STEP) { deep.push(sPoly); continue; }', self.fn)
        self.assertIn('for (const sPoly of t.deep) rem = rem.flatMap((part) => outsideConvex(part, sPoly));', self.fn)

    def test_the_page_lays_it_under_the_one_lawn(self):
        s = self.src
        step = self.step
        lay = step[step.index('const lawnLay = () => {'):step.index('const portalStat = []')]
        self.assertIn('const un = lawnUnder(g2.attributes.position.array, rimE, zones);', lay, "the lawn's own triangles, as the trim will read them")
        self.assertEqual(1, lay.count('noTrim: true'), 'the lawn itself still goes through the trim: its kept pieces are the ones drawn before')
        self.assertIn('for(const p of collarParts)if(!p.noTrim)p.geom=trimTerrainPatch(p.geom);', step, 'the trim drops a triangle with no area in plan, which is every riser')
        self.assertIn('groundMeshY(X + cw * (0.5 + di), Z + ch * (0.5 + dj)) !== null', lay, 'a rim riser only toward drawn ground: an opened cell with no lawn is the cut, and a riser stood across it')
        self.assertIn('tunnelBox.push([mx, mz, dx, dz, hw, vo, u1, roof - 0.1]);', step)
        self.assertIn('zones.push([rect(-0.8, 0.05, b[4] + 0.7), Infinity], [rect(0.05, b[6] + 0.5, b[5]), b[7]]);', lay, 'the headwall keeps the under-lawn out, the box keeps it over its roof')
        self.assertIn('PERF.lawnUnder = un.st;', lay)

    def test_no_new_material_and_no_shader_text(self):
        for word in ('onBeforeCompile', 'ShaderMaterial', 'THREE.', 'Material(', 'gl_Frag', 'uniform ', 'polygonOffset'):
            self.assertNotIn(word, self.fn, word)
        step = self.step
        self.assertEqual(1, step.count('const collarMat = groundSurfMat('), "on the collars' own mesh")
        self.assertEqual(1, step.count('new THREE.Mesh(mergeColored(collarParts), collarMat)'))

    def test_the_kept_pieces_are_the_trims(self):
        """lawnUnder walks the trim's own steps in the trim's own order to find the pieces it puts risers under."""
        trim = self.src[self.src.index('  function trimTerrainPatch(g) {'):self.src.index('  const LAWN_DROP = ')]
        for text in ('if(overlap.length<3 || Math.abs(signedArea(overlap))<1e-7)continue;', 'if(overlap.every(q=>height(...q)<sHeight(...q)-TERRAIN_PATCH_CLEARANCE))continue;',
                     'pieces=pieces.flatMap(piece=>outsideConvex(piece,sPoly));', 'if(!pieces.length)break;', 'piece=tidyRing(piece);if(!piece)continue;'):
            self.assertIn(text, trim)
            self.assertIn(text.replace(' ', ''), self.fn.replace(' ', '').replace('(q)=>', 'q=>').replace('(piece)=>', 'piece=>'), text)


LAWN_HARNESS = r"""
// ---- the harness (tests/test_vine_portals.py): a lawn over one opened cell, roads through it, rays from above
const THREE = { BufferGeometry: class { constructor() { this.attributes = {}; this.index = null; } setAttribute(n, a) { this.attributes[n] = a; } computeVertexNormals() {} dispose() {} },
  Float32BufferAttribute: class { constructor(arr, n) { this.array = new Float32Array(arr); this.count = this.array.length / n; } getX(i) { return this.array[i * 3]; } getY(i) { return this.array[i * 3 + 1]; } getZ(i) { return this.array[i * 3 + 2]; } } };
const PERF = {};
function remember(tris) {   // rememberTerrainRoad without the core's cap test: [x, y, z] triangles
  for (const t of tris) {
    const poly = t.map((p) => [p[0], p[2], p[1]].map(Math.fround)), bounds = streetBounds(poly);
    const id = trsAdd(poly);
    terrainPatchCells(bounds, (key) => { if (!terrainRoadGrid.has(key)) terrainRoadGrid.set(key, []); terrainRoadGrid.get(key).push(id); });
  }
}
function scene(cfg) {
  terrainRoadGrid = new Map(); TRS.n = 0;
  const N = 5, C = 25, X = 100, Z = 200, roads = [];
  // the ground: a bank falling to the south (the old cut's valley side), with a hump in it
  const gy = (x, z) => 3 - 0.22 * (z - Z) + 0.6 * Math.sin((x - X) / 6) * Math.cos((z - Z) / 7);
  const quad = (a, b, c, d) => { roads.push([a, b, c], [a, c, d]); };
  // a street laid flat across the bank (its sheet at its centreline's height and a lift): over the lawn on the low side, under it on the high side
  if (cfg.street) { const zc = Z + 9, hw = 4, y = gy(X + 12, zc) + 0.6; quad([X - 20, y, zc - hw - 1.5], [X + 45, y, zc - hw + 1.5], [X + 45, y, zc + hw + 1.5], [X - 20, y, zc + hw - 1.5]); }
  // an approach's shoulder, level, well under the lawn at one end and over it at the other
  if (cfg.cut) { const zc = Z + 19, y0 = gy(X, zc) - 0.9; quad([X - 20, y0, zc - 3], [X + 45, y0 + 0.2, zc - 2], [X + 45, y0 + 0.2, zc + 4], [X - 20, y0, zc + 3]); }
  // the expressway's own cut, 5 m under the lawn: its walls close it, and nothing is laid under it or hung beside it
  let deepBox = null;
  if (cfg.deep) { const zc = Z + 14, y0 = gy(X, zc) - 5; quad([X - 20, y0, zc - 4], [X + 45, y0, zc - 4], [X + 45, y0, zc + 4], [X - 20, y0, zc + 4]); deepBox = [zc - 4, zc + 4]; }
  remember(roads);
  const tris = [], rimE = [];
  const P = (a, b) => { const x = X + C * a / N, z = Z + C * b / N; return [x, gy(x, z), z]; };
  for (let a = 0; a < N; a++) for (let b = 0; b < N; b++) {
    const p00 = P(a, b), p10 = P(a + 1, b), p11 = P(a + 1, b + 1), p01 = P(a, b + 1);
    tris.push(...p00, ...p01, ...p11, ...p00, ...p11, ...p10);
    rimE.push((a === 0 ? 1 : 0) | (b + 1 === N ? 2 : 0), (a + 1 === N ? 2 : 0) | (b === 0 ? 4 : 0));
  }
  const pos = new Float32Array(tris);
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const kept = Array.from(trimTerrainPatch(g).attributes.position.array);
  const un = lawnUnder(pos, rimE, cfg.zone !== undefined ? [[[[X + 8, Z - 1], [X + 18, Z - 1], [X + 18, Z + C + 1], [X + 8, Z + C + 1]], cfg.zone]] : undefined);   // a strip across the cell: a tunnel's box under the lawn
  return { X, Z, C, gy, roads, kept, un, lawn: tris, deepBox };
}
function triList(arr) { const o = []; for (let k = 0; k + 8 < arr.length; k += 9) o.push([[arr[k], arr[k + 1], arr[k + 2]], [arr[k + 3], arr[k + 4], arr[k + 5]], [arr[k + 6], arr[k + 7], arr[k + 8]]]); return o; }
function hit(o, d, t) {   // Moller-Trumbore, both faces, a hair generous at the edges: the distance along the ray, or Infinity
  const [a, b, c] = t, e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
  const px = d[1] * e2[2] - d[2] * e2[1], py = d[2] * e2[0] - d[0] * e2[2], pz = d[0] * e2[1] - d[1] * e2[0], det = e1[0] * px + e1[1] * py + e1[2] * pz;
  if (Math.abs(det) < 1e-12) return Infinity;
  const tx = o[0] - a[0], ty = o[1] - a[1], tz = o[2] - a[2], u = (tx * px + ty * py + tz * pz) / det;
  if (u < -1e-6 || u > 1 + 1e-6) return Infinity;
  const qx = ty * e1[2] - tz * e1[1], qy = tz * e1[0] - tx * e1[2], qz = tx * e1[1] - ty * e1[0], v = (d[0] * qx + d[1] * qy + d[2] * qz) / det;
  if (v < -1e-6 || u + v > 1 + 2e-6) return Infinity;
  const s = (e2[0] * qx + e2[1] * qy + e2[2] * qz) / det;
  return s > 1e-9 ? s : Infinity;
}
function planY(t, x, z) {   // a triangle's height over a plan point, or null outside it
  const [a, b, c] = t, d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2]);
  if (Math.abs(d) < 1e-12) return null;
  const u = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d, v = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d, w = 1 - u - v;
  return u >= -1e-7 && v >= -1e-7 && w >= -1e-7 ? u * a[1] + v * b[1] + w * c[1] : null;
}
function rays(sc, withUnder, n, seed) {
  // an eye at least 2.5 m over the ground anywhere round the cell looks at a point in it. The ray leaks if it comes to
  // the cell's underside: below the ground at the cell's rim on its way out, or 30 m under the cell, having hit nothing
  let a = seed >>> 0; const rnd = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const occ = triList(sc.kept).concat(sc.roads, withUnder ? triList(sc.un.pos) : []);
  const { X, Z, C, gy } = sc; let leaks = 0; const where = [];
  // the ground at the cell's rim as the lawn has it: the lattice's points, straight between them
  const rimY = (x, z) => { const u = Math.min(4.999999, Math.max(0, (x - X) / 5)), v = Math.min(4.999999, Math.max(0, (z - Z) / 5)), i = Math.floor(u), j = Math.floor(v);
    const onX = Math.min(Math.abs(x - X), Math.abs(x - X - C)) < Math.min(Math.abs(z - Z), Math.abs(z - Z - C)), xs = x - X < C / 2 ? X : X + C, zs = z - Z < C / 2 ? Z : Z + C;
    return onX ? gy(xs, Z + j * 5) + (gy(xs, Z + j * 5 + 5) - gy(xs, Z + j * 5)) * (v - j) : gy(X + i * 5, zs) + (gy(X + i * 5 + 5, zs) - gy(X + i * 5, zs)) * (u - i); };
  for (let i = 0; i < n; i++) {
    const ex = X - 15 + rnd() * (C + 30), ez = Z - 15 + rnd() * (C + 30), ey = gy(ex, ez) + 2.5 + rnd() * rnd() * 12;
    const tx = X + rnd() * C, tz = Z + rnd() * C, ty = gy(tx, tz) - 0.3 - rnd() * 2.5;   // a point under the lawn: through it if nothing is in the way
    let d = [tx - ex, ty - ey, tz - ez]; const L = Math.hypot(...d); d = d.map((v) => v / L);
    if (d[1] > -0.02) continue;
    let best = Infinity; for (const t of occ) { const s = hit([ex, ey, ez], d, t); if (s < best) best = s; }
    // where the ray leaves the cell's column (or goes 30 m under it)
    let sOut = (-30 + gy(tx, tz) - ey) / d[1], sIn = 0;
    for (const [o, dd, lo, hi] of [[ex, d[0], X, X + C], [ez, d[2], Z, Z + C]]) {
      if (Math.abs(dd) < 1e-12) { if (o < lo || o > hi) sOut = -1; continue; }
      const s0 = (lo - o) / dd, s1 = (hi - o) / dd; sIn = Math.max(sIn, Math.min(s0, s1)); sOut = Math.min(sOut, Math.max(s0, s1));
    }
    if (sOut <= sIn) continue;
    // it enters the column over the ground (the eye is over the ground and the ground outside the cell is whole)
    const pin = [ex + d[0] * sIn, ey + d[1] * sIn, ez + d[2] * sIn]; if (pin[1] < rimY(pin[0], pin[2]) - 1e-6) continue;
    if (best <= sOut + 1e-6) continue;   // (a riser at the rim stands on the column's own side)
    const po = [ex + d[0] * sOut, ey + d[1] * sOut, ez + d[2] * sOut];
    // (over a road where it leaves the cell, or at its very edge, it is in that road's own cut, which goes on past the cell)
    if (po[1] < rimY(po[0], po[2]) - 1e-4 && !sc.roads.some((t) => [[0, 0], [0.15, 0], [-0.15, 0], [0, 0.15], [0, -0.15]].some((o) => { const y = planY(t, po[0] + o[0], po[2] + o[1]); return y !== null && y <= po[1] + 1e-6; }))) { leaks++; if (where.length < 8) where.push([ex, ey, ez, tx, ty, tz].map((v) => +v.toFixed(2))); }
  }
  return { leaks, where };
}

const res = {};
for (const [name, cfg] of [['street', { street: 1 }], ['cut', { cut: 1 }], ['both', { street: 1, cut: 1 }]]) {
  const sc = scene(cfg), a = rays(sc, false, 30000, 11), b = rays(sc, true, 120000, 23);
  // the floor under what cut it: every level triangle of the under-lawn, at its corners and its middle, against every road over the point
  let over = 0, floorTris = 0, low = Infinity;
  for (const t of triList(sc.un.pos)) {
    const ar = (t[1][0] - t[0][0]) * (t[2][2] - t[0][2]) - (t[1][2] - t[0][2]) * (t[2][0] - t[0][0]);
    if (Math.abs(ar) < 1e-5) continue;
    floorTris++;
    const pts = t.concat([[(t[0][0] + t[1][0] + t[2][0]) / 3, (t[0][1] + t[1][1] + t[2][1]) / 3, (t[0][2] + t[1][2] + t[2][2]) / 3]]);
    for (const q of pts) for (const r of sc.roads) { const y = planY(r, q[0], q[2]); if (y !== null) { if (q[1] > y - 0.08 + 1e-4) over++; low = Math.min(low, y - q[1]); } }
  }
  res[name] = { st: sc.un.st, kept: sc.kept.length / 9, tris: sc.un.pos.length / 9, without: a.leaks, with: b.leaks, where: b.where, over, floorTris, low };
}
{ // a roof under the lawn (lower than the lawn everywhere in this cell): nothing of the under-lawn goes below it over the roof,
  // and nothing at all is laid where the zone's height is Infinity
  const R = -3.3, plain = scene({ street: 1, cut: 1 }), roofed = scene({ street: 1, cut: 1, zone: R }), out = scene({ street: 1, cut: 1, zone: Infinity });
  const count = (sc, test) => { let n = 0; const p = sc.un.pos; for (let k = 0; k < p.length; k += 3) if (p[k] > sc.X + 8.05 && p[k] < sc.X + 17.95 && test(p[k + 1])) n++; return n; };   // (a sill's outer corner follows its riser's cut, so it may stand LAWN_INSET over a zone's line)
  res.roof = { plain: count(plain, (y) => y < R - 1e-6), roofed: count(roofed, (y) => y < R - 1e-6), inside: count(plain, () => true), out: count(out, () => true), tris: roofed.un.pos.length / 9 };
}
{ // a deep cut alone leaves the lawn as the trim left it; with a street beside it the street's floor stops at the cut's line
  const alone = scene({ deep: 1 }), both = scene({ deep: 1, street: 1 });
  const inCut = (sc) => { let n = 0; const p = sc.un.pos; for (let k = 0; k < p.length; k += 9) { const zs = [p[k + 2], p[k + 5], p[k + 8]], xs = [p[k], p[k + 3], p[k + 6]]; const flat = Math.abs((xs[1] - xs[0]) * (zs[2] - zs[0]) - (zs[1] - zs[0]) * (xs[2] - xs[0])) > 1e-5; if (flat && (zs[0] + zs[1] + zs[2]) / 3 > sc.deepBox[0] + 0.05 && (zs[0] + zs[1] + zs[2]) / 3 < sc.deepBox[1] - 0.05) n++; } return n; };
  res.deep = { alone: alone.un.pos.length / 9, both: both.un.pos.length / 9, floorInCut: inCut(both), st: both.un.st };
}
console.log(JSON.stringify(res));
"""


if __name__ == '__main__':
    unittest.main()
