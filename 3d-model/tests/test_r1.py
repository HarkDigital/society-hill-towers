"""The realism round two, R1: the Schuylkill's banks (Round 55 coda 2's complaint again: "the Schuylkill River Trail is
under water, trees and lampposts in the river").

riverCarve takes the bank within 60 m of the outline down 5 to 8 m, the Delaware's one water quad at the river's level lay
under the whole city and showed through every metre of it the carve took below that level (1,350 samples of 100 m2 in the
wide box, 91 per cent of the first 5 m), and everything standing there read siteY, the DEM over the slope. The fix, none of
which moves the drawn river bed (Round 89's invariant): a baked hole in the quad over the corridor (schuylkill.json
quad_hole, its patches quad_keep), the land's floor on the outer districts' strips at water + 0.05, every free-standing
thing in the band on the drawn ground (bankPlace) and none in the river off a deck, and the bake's ribbon cut back to the
Fairmount pool's own bank at the Water Works. ?banks=0 brings back the old placement, the old floor and the whole quad.

The page's probe is __dbg.bankCheck(step); here a Python twin of the outer districts' ground (the verifier's bank model,
app.js's sampleDem, siteY, schEdges, schRaster, riverCarve and the 25 m strips) measures the wide box, and Node runs the
page's own Schuylkill block against the twin so neither can drift from the other. Stdlib only, as test_schuylkill.py.
"""
import json
import math
import re
import shutil
import subprocess
import unittest

try:
    from . import _common as C
    from .test_schuylkill import _crossings
except ImportError:
    import _common as C
    from test_schuylkill import _crossings

APP = (C.MODEL / 'app.js').read_text()
RING_W = (-12000.0, 16500.0, -21700.0, 9700.0)   # app.js RING_W: x0, x1, z0, z1
DEL_X, Z_MAX, QUAD_R = -2400.0, 7500.0, 60.0      # bake_schuylkill.py
POOL_REACH = (-3900.0, -2800.0, -3250.0, -2300.0)


def cut(start, end):
    a = APP.index(start)
    return APP[a:APP.index(end, a)]


def pip(x, z, ring):
    ins = False
    n = len(ring)
    for k in range(n):
        a, b = ring[k], ring[(k + 1) % n]
        if (a[1] > z) != (b[1] > z) and x < a[0] + (z - a[1]) / (b[1] - a[1]) * (b[0] - a[0]):
            ins = not ins
    return ins


def seg_dist(px, pz, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dz * dz or 1e-12
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (pz - a[1]) * dz) / L2))
    return math.hypot(a[0] + dx * t - px, a[1] + dz * t - pz)


class Twin:
    """the outer districts' drawn ground near the Schuylkill, as app.js builds it ('Laying out the ground'), built once"""
    _inst = None

    @classmethod
    def get(cls):
        if cls._inst is None:
            cls._inst = Twin()
        return cls._inst

    def __init__(self):
        J = C.load_json
        self.dems = [(J('dem.json'), 8.34), (J('dem_wide.json'), 3.2), (J('dem_south.json'), 3.2), (J('dem_nw.json'), 4.0), (J('dem_city.json'), 4.0)]
        self.S = J('schuylkill.json')
        self.D = J('delaware.json')
        self.DATUM = self.dem_abs(0, 0)
        self.WATER = 0.5 - self.DATUM
        self.BED = -2.0 - self.DATUM
        rings = []
        for pg in self.S['polys']:
            rings.append(pg['ring'])
            rings += pg.get('holes', [])
        RC, EC = 10, 40
        xs = [q[0] for pg in self.S['polys'] for q in pg['ring']]
        zs = [q[1] for pg in self.S['polys'] for q in pg['ring']]
        self.gx0, self.gz0 = math.floor(min(xs) / RC) - 1, math.floor(min(zs) / RC) - 1
        self.nx, self.nz = math.ceil(max(xs) / RC) - self.gx0 + 2, math.ceil(max(zs) / RC) - self.gz0 + 2
        self.mask = bytearray(self.nx * self.nz)
        for j in range(self.nz):   # the page's even-odd scanline raster, holes included
            zc = (self.gz0 + j + 0.5) * RC
            cr = []
            for r in rings:
                for k in range(len(r)):
                    a, b = r[k], r[(k + 1) % len(r)]
                    if (a[1] <= zc) != (b[1] <= zc):
                        cr.append(a[0] + (zc - a[1]) / (b[1] - a[1]) * (b[0] - a[0]))
            cr.sort()
            for m in range(0, len(cr) - 1, 2):
                i0 = max(0, math.ceil(cr[m] / RC - 0.5) - self.gx0)
                i1 = min(self.nx - 1, math.floor(cr[m + 1] / RC - 0.5) - self.gx0)
                for ii in range(i0, i1 + 1):
                    self.mask[j * self.nx + ii] = 1
        self.egrid, self.segs = {}, []
        for r in rings:
            n = len(r)
            ar = sum(r[k][0] * r[(k + 1) % n][1] - r[(k + 1) % n][0] * r[k][1] for k in range(n))
            sg = 1 if ar > 0 else -1
            for k in range(n):
                a, b = r[k], r[(k + 1) % n]
                dx, dz = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dz)
                if L < 0.05:
                    continue
                sid = len(self.segs)
                self.segs.append((a[0], a[1], dx / L, dz / L, L, dz / L * sg, -dx / L * sg))
                for gx in range(math.floor(min(a[0], b[0]) / EC), math.floor(max(a[0], b[0]) / EC) + 1):
                    for gz in range(math.floor(min(a[1], b[1]) / EC), math.floor(max(a[1], b[1]) / EC) + 1):
                        self.egrid.setdefault((gx, gz), []).append(sid)
        self.hole = self.S.get('quad_hole') or []
        self.keep = self.S.get('quad_keep') or []
        self.cache = {}

    def sample(self, G, x, z, fb):
        fx, fz = (x - G['x0']) / G['cell'], (z - G['z0']) / G['cell']
        if fx < 0 or fz < 0 or fx > G['nx'] - 1 or fz > G['nz'] - 1:
            return None
        i, j = min(max(math.floor(fx), 0), G['nx'] - 2), min(max(math.floor(fz), 0), G['nz'] - 2)
        tx, tz = min(max(fx - i, 0), 1), min(max(fz - j, 0), 1)
        r0, r1 = G['rows'][j], G['rows'][j + 1]
        v = lambda a: fb if a is None else a
        a = v(r0[i]) * (1 - tx) + v(r0[i + 1]) * tx
        b = v(r1[i]) * (1 - tx) + v(r1[i + 1]) * tx
        return a * (1 - tz) + b * tz

    def dem_abs(self, x, z):
        for G, fb in self.dems:
            v = self.sample(G, x, z, fb)
            if v is not None:
                return v
        return 8.34

    def raster(self, x, z):
        ii, jj = math.floor(x / 10) - self.gx0, math.floor(z / 10) - self.gz0
        return 0 <= ii < self.nx and 0 <= jj < self.nz and self.mask[jj * self.nx + ii] == 1

    def edges(self, x, z):
        best, side = 6400.0, 0
        gx, gz = math.floor(x / 40), math.floor(z / 40)
        for a in range(-2, 3):
            for b in range(-2, 3):
                for sid in self.egrid.get((gx + a, gz + b), ()):
                    s = self.segs[sid]
                    t = min(max((x - s[0]) * s[2] + (z - s[1]) * s[3], 0), s[4])
                    px, pz = x - (s[0] + s[2] * t), z - (s[1] + s[3] * t)
                    d2 = px * px + pz * pz
                    if d2 < best:
                        best, side = d2, (1 if px * s[5] + pz * s[6] >= 0 else -1)
        return math.sqrt(best), side

    def inside(self, x, z):
        d, side = self.edges(x, z)
        return (side < 0) if d < 8 else self.raster(x, z)

    def carve(self, x, z, yy, banks):
        d, side = self.edges(x, z)
        if ((side < 0) if d < 8 else self.raster(x, z)):
            return min(yy, self.BED - 0.6)
        if d < 60:
            t = min(max(d / 60, 0), 1)
            y = min(yy, self.WATER - 0.5 + (yy - self.WATER + 0.5) * t * t * (3 - 2 * t))
            return min(yy, max(self.WATER + 0.05, y)) if banks else y
        return yy

    def node(self, x, z, banks):
        k = (round(x, 3), round(z, 3), banks)
        if k not in self.cache:
            y = self.dem_abs(x, z) - self.DATUM
            yy = (self.WATER + 0.45 if y < self.WATER + 0.6 else y) - 0.05
            self.cache[k] = self.carve(x, z, yy, banks)
        return self.cache[k]

    STRIPS = ((-3700, 2300, -4480, -520), (-3700, 2300, 850, 6400), (-3700, -640, -520, 850))   # the wide box's strips that meet the river (CORE_EXT)

    def mesh(self, x, z, banks):
        for sx0, sx1, sz0, sz1 in self.STRIPS:
            if sx0 <= x <= sx1 and sz0 <= z <= sz1:
                gnx, gnz = max(1, round((sx1 - sx0) / 25)), max(1, round((sz1 - sz0) / 25))
                fu, fv = (x - sx0) * gnx / (sx1 - sx0), (z - sz0) * gnz / (sz1 - sz0)
                i, j = min(max(math.floor(fu), 0), gnx - 1), min(max(math.floor(fv), 0), gnz - 1)
                u, v = fu - i, fv - j
                X = lambda ii: sx0 + (sx1 - sx0) * ii / gnx
                Z = lambda jj: sz0 + (sz1 - sz0) * jj / gnz
                ya, yb = self.node(X(i), Z(j), banks), self.node(X(i + 1), Z(j), banks)
                yc, yd = self.node(X(i), Z(j + 1), banks), self.node(X(i + 1), Z(j + 1), banks)
                if u + v <= 1:
                    return ya + (yb - ya) * u + (yc - ya) * v
                return yd + (yc - yd) * (1 - u) + (yb - yd) * (1 - v)
        return None

    def quad(self, x, z, banks):
        return not (banks and self.hole and pip(x, z, self.hole) and not any(pip(x, z, r) for r in self.keep))

    def near_delaware(self, x, z, r):
        for pg in self.D['polys']:
            if pip(x, z, pg['ring']) and not any(pip(x, z, h) for h in pg.get('holes') or []):
                return True
            ring = pg['ring']
            if any(seg_dist(x, z, ring[k], ring[(k + 1) % len(ring)]) < r for k in range(len(ring))):
                return True
        return False

    def survey(self, banks, step=10):
        """the wide box's Schuylkill reach on a step grid: bank samples (outside within 60 m) drawn as water where the quad
        lies, and inside samples within 0.3 m of the sheet"""
        out = {'band': 0, 'drowned': 0, 'kept': 0, 'tidal': 0, 'near': 0, 'over': 0, 'highest': -99.0}
        for xi in range(-3700, -2400, step):
            for zi in range(-4480, 6400, step):
                x, z = xi + step / 2, zi + step / 2
                if -640 <= x <= 770 and -520 <= z <= 850:
                    continue
                d, _ = self.edges(x, z)
                if d >= 60:
                    continue
                m = self.mesh(x, z, banks)
                if m is None:
                    continue
                if self.inside(x, z):
                    out['highest'] = max(out['highest'], m - self.WATER - 0.5)
                    out['near'] += m > self.WATER + 0.5 - 0.3
                    out['over'] += m > self.WATER + 0.5
                    continue
                out['band'] += 1
                if m < self.WATER and self.quad(x, z, banks):
                    if banks and any(pip(x, z, r) for r in self.keep):
                        out['kept'] += 1
                    elif banks and self.near_delaware(x, z, QUAD_R):   # the Navy Yard's slips: the Delaware's own bank, which the hole leaves
                        out['tidal'] += 1
                    else:
                        out['drowned'] += 1
        return out


class TheFlag(unittest.TestCase):
    def test_banks_flag_and_every_part_behind_it(self):
        self.assertIn("const BANKS = !/[?&]banks=0\\b/.test(location.search);", APP)
        self.assertIn('function bankBand(x, z) { return BANKS ? schBand(x, z) : 0; }', APP)
        self.assertIn('const SCH_QUAD_HOLE = BANKS && SCH_POLYS && SCHUYLKILL_DATA.quad_hole', APP)
        self.assertIn('return BANKS && floor ? Math.min(yy, Math.max(TERRAIN.water + 0.05, y)) : y;', APP)

    def test_the_quad_takes_the_hole_and_keeps_its_patches(self):
        lay = cut("  step('Laying out the ground'", "  step('Shaping the waterfront'")
        self.assertIn('if (SCH_QUAD_HOLE) sheetHoles.push(SCH_QUAD_HOLE);', lay)
        self.assertIn('.concat(SCH_QUAD_KEEP.map((r) => shapeFromPoly(r, null)))', lay)
        # the floor on the outer districts' 25 m strips only; the far strips' 50 m cells keep Round 89's
        self.assertIn('yy = riverCarve(x, z, yy, true);', lay)
        far = cut('    const mkFarGround = (', '    // patch hole snapped')
        self.assertIn('yy = riverCarve(x, z, yy);', far)

    def test_siteY_is_untouched(self):
        body = cut('  function siteY(x, z, mode) {', '  function walkY(')
        self.assertEqual([], re.findall(r'\bbank[A-Z]\w*|\bBANKS\b|groundMeshY|schBand', body))

    def test_every_free_standing_thing_reads_bankPlace(self):
        trees = cut("  step('Planting the street trees'", "  step('Sowing the grass'")
        self.assertIn('const q = bankPlace(x, z, false); if (!q) { BANK_STAT.trees++; return; }', trees)
        self.assertIn('cy = gy + boleH(dbh) * 0.75', trees)   # the crown test stands on the same ground
        self.assertIn('GY[n] = gy;', trees)
        self.assertIn('const wq = bankPlace(x, z, false);', cut('  function woodStep() {', '\n  }\n'))
        poles = cut("  step('Lighting the streetlamps'", "  step('Fitting out the rooftops'")
        self.assertIn('const q = bankPlace(x, z, false);', poles)
        self.assertIn('if (deckOver(x, z, gy))', poles)
        self.assertIn('const q = bankPlace(px, pz);', cut("  step('Raising the historical markers'", "  step('Posting the transit stops'"))
        stops = cut("  step('Posting the transit stops'", "  step('Opening the libraries")
        self.assertIn('const sq = bankPlace(x, z);', stops)
        self.assertIn('const rq = bankPlace(x, z);', stops)
        self.assertIn('const dq = bankPlace(x, z);', APP)
        self.assertIn('|| st.river) continue;   // R1', APP)
        gate = cut('  function waterRingGate(poly, wide) {', '  // true when it built the ring itself')
        self.assertNotIn("siteY(", gate)
        self.assertEqual(gate.count('bankGround'), 5)
        self.assertIn('if (window.__dbg) Object.assign(window.__dbg, { bankCheck });', APP)

    def test_the_cars_ride_their_roads(self):
        # R1 leaves the traffic, the parked cars and the buses on their roads (the verifier: they ride bankFloor's road)
        traffic = cut("  step('Setting the traffic flowing'", "  step('Lighting the streetlamps'")
        self.assertNotIn('bankPlace', traffic)
        self.assertNotIn('bankBand', traffic)


class TheBake(unittest.TestCase):
    def setUp(self):
        C.require(self, 'schuylkill.json', 'delaware.json')
        self.S = C.load_json('schuylkill.json')
        self.D = C.load_json('delaware.json')

    def test_hole_is_one_simple_ring_in_the_quad(self):
        h = self.S.get('quad_hole')
        self.assertTrue(h and len(h) > 100, 'schuylkill.json carries no quad_hole')
        self.assertEqual([], _crossings(h)[:4])
        self.assertTrue(all(RING_W[0] < q[0] < RING_W[1] and RING_W[2] < q[1] < RING_W[3] for q in h))
        self.assertTrue(all(q[0] < DEL_X and q[1] <= Z_MAX - QUAD_R + 1 for q in h))

    def test_hole_keeps_clear_of_the_delaware(self):
        h = self.S['quad_hole']
        for pg in self.D['polys']:
            ring = pg['ring']
            near = [r for r in ring if r[0] < DEL_X + 200 and r[1] > -14000]
            self.assertFalse(any(pip(q[0], q[1], h) for q in near), 'a Delaware vertex lies in the hole')
            worst = min(min(seg_dist(q[0], q[1], ring[k], ring[(k + 1) % len(ring)]) for k in range(len(ring)) if min(ring[k][0], ring[(k + 1) % len(ring)][0]) < DEL_X + 200) for q in h)
            self.assertGreater(worst, QUAD_R - 10, 'the hole comes within %.1f m of the Delaware' % worst)

    def test_hole_covers_the_bank(self):
        """every bank point 2 to 40 m out from the outline, the Delaware's 60 m and the bake's cuts aside, lies in the hole"""
        T = Twin.get()
        h = self.S['quad_hole']
        miss = []
        for pg in self.S['polys']:
            r = pg['ring']
            n = len(r)
            ar = sum(r[k][0] * r[(k + 1) % n][1] - r[(k + 1) % n][0] * r[k][1] for k in range(n))
            sg = 1 if ar > 0 else -1
            for k in range(0, n, 2):
                a, b = r[k], r[(k + 1) % n]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 1:
                    continue
                mx, mz, nx, nz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (b[1] - a[1]) / L * sg, -(b[0] - a[0]) / L * sg
                for d in (2, 10, 25, 40):
                    x, z = mx + nx * d, mz + nz * d
                    if x > DEL_X - QUAD_R or z > Z_MAX - 2 * QUAD_R or T.inside(x, z) or pip(x, z, h):
                        continue
                    if T.near_delaware(x, z, QUAD_R + 5):
                        continue
                    miss.append((round(x), round(z), d))
        self.assertEqual([], miss[:10], '%d bank points outside the hole' % len(miss))

    def test_patches_are_simple_and_inside_the_hole(self):
        h = self.S['quad_hole']
        keep = self.S.get('quad_keep') or []
        holes = [hh for pg in self.S['polys'] for hh in pg.get('holes') or []]
        self.assertTrue(keep)
        for r in keep:
            self.assertEqual([], _crossings(r)[:4])
            self.assertTrue(all(pip(q[0], q[1], h) for q in r))
        for hh in holes:   # every island and pier of the outline sits under a patch
            cx, cz = sum(q[0] for q in hh) / len(hh), sum(q[1] for q in hh) / len(hh)
            if pip(cx, cz, h):
                self.assertTrue(any(pip(cx, cz, r) for r in keep), 'island at %d, %d has no patch' % (cx, cz))
        for i, a in enumerate(keep):
            for b in keep[i + 1:]:
                self.assertFalse(any(pip(q[0], q[1], b) for q in a) or any(pip(q[0], q[1], a) for q in b), 'two patches overlap')

    def test_the_water_works_bank_is_land(self):
        """the pool behind the Fairmount Dam bounds the ribbon there: of the 97 PPR trees the ribbon put in the river on the
        lawn between Lloyd Hall and the Water Works, none is inside the outline now (one stands on the wooded island)"""
        T = Twin.get()
        hdr, body = C.decode_b64('trees.b64')
        tq = hdr[3] / 1000 if hdr[3] > 0 else 0.2
        x0, z0, x1, z1 = POOL_REACH
        inside = [(body[i * 4] * tq, body[i * 4 + 1] * tq) for i in range(hdr[1])
                  if x0 < body[i * 4] * tq < x1 and z0 < body[i * 4 + 1] * tq < z1]
        inside = [q for q in inside if T.inside(*q)]
        self.assertLessEqual(len(inside), 1, inside[:5])


class TheTwin(unittest.TestCase):
    """the wide box's Schuylkill reach, the verifier's measure, before and after"""

    @classmethod
    def setUpClass(cls):
        cls.T = Twin.get()
        cls.old = cls.T.survey(False)
        cls.new = cls.T.survey(True)

    def test_the_old_bank_floods_so_the_twin_is_live(self):
        self.assertGreater(self.old['drowned'], 1000, self.old)

    def test_no_bank_is_drawn_as_water(self):
        self.assertEqual(0, self.new['drowned'], self.new)

    def test_the_river_bed_stays_clear_of_the_sheet(self):
        # Round 89's invariant over the whole outline, not only the centreline: the floor cannot lift the bed's edge
        self.assertEqual(0, self.new['near'], self.new)
        self.assertLess(self.new['highest'], -0.3, self.new)


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class ThePagesOwnCarve(unittest.TestCase):
    """app.js's Schuylkill block (the raster, the edges, schBand, riverCarve) run under Node against the twin"""

    def run_block(self, search, pts):
        block = cut('  const SCH_POLYS = (typeof SCHUYLKILL_DATA', '  function schuylkillCut(x, z) {')
        flag = re.search(r'  const BANKS = [^\n]+\n', APP).group(0)
        T = Twin.get()
        js = ('const SCHUYLKILL_DATA = ' + json.dumps(T.S) + ';\n'
              'const location = { search: ' + json.dumps(search) + ' };\n' + flag +
              'const PERF = {}; const TERRAIN = { water: ' + repr(T.WATER) + ', bed: ' + repr(T.BED) + ' };\n'
              'const clamp = (v, a, b) => (v < a ? a : v > b ? b : v); const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };\n'
              'function schuylkillCut() { return 0; }\n' + block +
              '\nconst P = ' + json.dumps(pts) + ';\n'
              'console.log(JSON.stringify({ banks: BANKS, hole: !!SCH_QUAD_HOLE, keep: SCH_QUAD_KEEP.length, '
              'carve: P.map((p) => [riverCarve(p[0], p[1], p[2], true), riverCarve(p[0], p[1], p[2])]), band: P.map((p) => schBand(p[0], p[1])) }));')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return json.loads(r.stdout)

    def test_the_page_and_the_twin_agree(self):
        T = Twin.get()
        pts = []
        for x in range(-3650, -2450, 37):
            for z in range(-4400, 6300, 113):
                d, _ = T.edges(x, z)
                if d < 80:
                    pts.append([x, z, (T.dem_abs(x, z) - T.DATUM)])
        self.assertGreater(len(pts), 150)
        out = self.run_block('', pts)
        self.assertTrue(out['banks'] and out['hole'] and out['keep'] > 0)
        bad = []
        for p, (yf, y0), b in zip(pts, out['carve'], out['band']):
            if abs(yf - T.carve(p[0], p[1], p[2], True)) > 1e-6 or abs(y0 - T.carve(p[0], p[1], p[2], False)) > 1e-6:
                bad.append(('carve', p))
            want = 2 if T.inside(p[0], p[1]) else (1 if T.edges(p[0], p[1])[0] < 80 else 0)
            if b != want:
                bad.append(('band', p, b, want))
        self.assertEqual([], bad[:5])
        # the floor is the only change, never over the builder's own height and never under water + 0.05 outside
        for p, (yf, y0) in zip(pts, out['carve']):
            self.assertLessEqual(yf, p[2] + 1e-9)
            if not T.inside(p[0], p[1]) and p[2] >= T.WATER + 0.05:
                self.assertGreaterEqual(yf, T.WATER + 0.05 - 1e-9)

    def test_banks_off_is_the_old_page(self):
        T = Twin.get()
        pts = [[-2960.0, -1080.0, 2.0], [-3330.0, -2450.0, 7.5], [-3100.0, -400.0, 1.0]]
        out = self.run_block('?dev=1&banks=0', pts)
        self.assertFalse(out['banks'])
        self.assertFalse(out['hole'])
        self.assertEqual(0, out['keep'])
        for p, (yf, y0) in zip(pts, out['carve']):
            self.assertAlmostEqual(yf, y0, places=9)
            self.assertAlmostEqual(y0, T.carve(p[0], p[1], p[2], False), places=6)


if __name__ == '__main__':
    unittest.main()
