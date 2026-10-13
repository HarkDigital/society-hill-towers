"""The realism pass, the streets (Oct 12; Mike: "please do anything necessary to make this look more photo realistic and less
cartoony. This should apply to all surfaces"). Under REAL (?real=0 keeps every street as it was):

- the asphalt re-keyed neutral-warm at about 0.45 of its old linear value, each street a little older or newer;
- a realistic lane shader (lanePatchReal): road-aligned wear, the lane photographs, utility cuts, manholes, the gutter and
  the kerb, worn amber and white paint, and at the junctions (streetJunctions, carried on aLane.w by laneW) crossings, stop
  bars and no lane lines through the box; a residential street under 9 m unmarked (laneClsOf, no repack);
- the outer districts' sidewalks (bake_sidewalks.py, sidewalks.b64), filled to the facades, culled to the half mile on a
  phone and not built in a LITE city;
- the lots' stalls and oil, the paving season's overlays on the road material at the street's own width with square ends
  (wideStreetAt), the decks' photographed concrete, the El's
  steel, the cobra heads and historic posts, the main line's ties (STREET_ART, bake_street_art.py)."""
import base64
import json
import shutil
import struct
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


def fn(s, name):
    a = s.index('  function ' + name + '(')
    return s[a:s.index('\n  }\n', a) + 4]


class Junctions(unittest.TestCase):
    """streetJunctions finds crossings and T's but not a street's own bend or continuation; laneW's E is linear between the
    vertices splitAtS inserts at junctionCuts, so the attribute interpolates exactly."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('node unavailable')
        s = (ROOT / 'app.js').read_text()
        code = '\n'.join(fn(s, n) for n in ('laneW', 'junctionCuts', 'splitAtS', 'streetJunctions')) + r'''
const J = (t) => t >= 2 && t <= 5;
const recs = [
  { pts: [[-100, 0], [100, 0]], w: 10, t: 3 },          // 0: a through street
  { pts: [[0, -80], [0, 80]], w: 8, t: 5 },             // 1: crosses 0 at the origin (no shared node: both pass through)
  { pts: [[50, 0], [50, 60]], w: 7, t: 5 },             // 2: a T, ending on 0 at x = 50
  { pts: [[-60, 40], [-30, 40]], w: 7, t: 5 },          // 3 and 4: one street split into two ways with a 45 degree bend
  { pts: [[-30, 40], [-10, 60]], w: 7, t: 5 },
  { pts: [[100, 0], [150, 0]], w: 10, t: 3 },           // 5: 0's continuation, end to end and aligned
  { pts: [[-100, 30], [100, 30]], w: 30, t: 0 },        // 6: a motorway: neither takes nor makes a crossing
];
const JX = streetJunctions(recs, J, J, null);
const out = { jx: JX.map((l) => l.map((v) => Math.round(v * 100) / 100)) };
// E along street 0, split at its cuts: linear between consecutive vertices
const jl = JX[0], pts = splitAtS(recs[0].pts, junctionCuts(jl));
let s = 0, worst = 0;
const sv = [0];
for (let i = 1; i < pts.length; i++) { s += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); sv.push(s); }
for (let i = 0; i + 1 < pts.length; i++) {
  const wa = laneW(0, jl, sv[i]), wb = laneW(0, jl, sv[i + 1]);
  for (let k = 1; k < 10; k++) { const t = k / 10, sm = sv[i] + (sv[i + 1] - sv[i]) * t; worst = Math.max(worst, Math.abs(laneW(0, jl, sm) - (wa + (wb - wa) * t))); }
}
out.worst = worst; out.verts = pts.length;
out.plain = laneW(2, [], 10);
out.atJ = laneW(0, jl, 100);     // street 0's s at x = 0: inside the crossing street's box, E = -hwX
out.far = laneW(1, jl, 300);
console.log(JSON.stringify(out));
'''
        r = subprocess.run(['node', '-e', code], capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(r.stderr)
        cls.d = json.loads(r.stdout)

    def test_crossings_and_ts(self):
        jx = self.d['jx']
        self.assertEqual(jx[0], [100, 4, 150, 3.5])    # street 0 at x = 0 (crossed by 1, hw 4) and x = 50 (the T, hw 3.5)
        self.assertEqual(jx[1], [80, 5])                # street 1 at the origin, crossing street 0's hw 5
        self.assertEqual(jx[2], [0, 5])                 # the T's own end
        self.assertEqual(jx[3], [])                     # a bend between two ways of one street is no junction
        self.assertEqual(jx[4], [])
        self.assertEqual(jx[5], [])                     # nor is a continuation
        self.assertEqual(jx[6], [])                     # the motorway takes none

    def test_the_encoding(self):
        d = self.d
        self.assertLess(d['worst'], 1e-6)               # E is linear between the inserted vertices
        self.assertEqual(d['verts'], 5)                 # two ends, two junctions, one switch point between them
        self.assertEqual(d['plain'], 2)                 # no junction: the class alone, as before
        self.assertEqual(d['atJ'], 1000 - 4)            # 1000 (cls + 1) + E, E = -hwX at the junction
        self.assertEqual(d['far'], 2000 + 150 - 3.5)    # cls 1, 150 m past the T at s 150, less its hw

    def test_the_shader_decodes_it(self):
        s = (ROOT / 'app.js').read_text()
        f = fn(s, 'lanePatchReal')
        for want in ("'float lnWv = abs(vLane.w), lnNoX = step(vLane.w, -500.0);',", "'float lnK = floor((lnWv + 500.0) / 1000.0);',",
                     "'float lnE = mix(999.0, lnWv - 1000.0 * lnK, lnJ);',"):
            self.assertIn(want, f)


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_real_gates_every_change(self):
        s = self.s
        self.assertIn('if (REAL) { lanePatchReal(shader, fresh); return; }', fn(s, 'lanePatch'))
        self.assertIn('if (REAL) { for (let k = 0; k < 6; k++) ROAD_COLORS[k] = STREET_REAL_COLS[k];', s)
        self.assertIn("if (!REAL || LITE || typeof SIDEWALKS_B64 === 'undefined' || !SIDEWALKS_B64) return;", s)
        self.assertIn("if (!REAL || typeof STREET_ART === 'undefined' || !STREET_ART", fn(s, 'loadStreetArt'))
        self.assertIn("if (!REAL || isTouch) return;", cut(s, "  step('Painting the El'", "  step('Laying the Northeast Corridor'"))
        self.assertIn('const TIES = REAL && !isTouch,', s)
        self.assertIn('const poleGeo = REAL ? mergePlain([', s)
        self.assertIn("const JX = REAL ? streetJunctions(wideRoadRecs, STREET_JOINS, STREET_JOINS,", s)
        self.assertIn('const JX = REAL && rc.lane ? streetJunctions(roadRecs,', s)   # the far ring: a computer's, which carries aLane

    def test_a_phone_keeps_its_budget(self):
        s = self.s
        u = fn(s, 'updateStreets')
        self.assertIn('if (!sidewalkTiles || !isTouch || now < streetsNearAt) return;', u)
        self.assertIn('< NEAR_R;', u)
        self.assertIn('if (!bs || !t.frustumCulled) continue;', u)   # never hidden before its first draw uploaded it and freed its arrays
        self.assertIn('updateStreets(now);', cut(s, '  function frame(now, once) {', '\n  setHint();'))
        # four-byte streams only (Round 158): the sidewalks' normals and colours, the lots' aLot
        sw = cut(s, "  step('Paving the sidewalks'", '  function streetTiles(')
        self.assertIn("g.setAttribute('normal', new THREE.BufferAttribute(nor, 4, true));", sw)
        self.assertIn("g.setAttribute('color', rgbStride4(col));", sw)
        lots = fn(s, 'mergeLots')
        self.assertIn("new THREE.BufferAttribute(lot, 4, true)", lots)
        self.assertIn("new THREE.InterleavedBufferAttribute(new THREE.InterleavedBuffer(col, 4), 3, 0, true)", lots)
        self.assertIn("if (!isTouch) one('steel'", fn(s, 'loadStreetArt'))   # the El's steel and the ties are a computer's

    def test_the_flats_stay_out_of_the_pins_capture(self):
        s = self.s
        self.assertIn("for (const t of sidewalkTiles) t.userData.occFlat = true;", s)
        self.assertIn("for (const t of streetTiles(m, 9600)) t.userData.occFlat = true;", s)

    def test_build_ships_them(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('let_blob("SIDEWALKS_B64", "sidewalks.b64")', b)
        self.assertIn('const("STREET_ART", text_of("street_art.json", "null"))', b)
        self.assertIn('ART_FILES += art_paths(json.loads((ROOT / "street_art.json").read_text()))', b)


class Markings(unittest.TestCase):
    """The residential width rule (the audit's double yellow on every street, decided without a repack) and the paving
    season's strips on the street's own width, with square ends."""

    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def lane_cls(self, real):
        if not shutil.which('node'):
            self.skipTest('node unavailable')
        s = self.s
        a = s.index('  const RES_UNMARKED_W = ')
        src = s[a:s.index('\n', s.index('  const laneClsOf = ', a)) + 1]
        code = 'const REAL = %s;\n' % ('true' if real else 'false') + src + r'''
const cases = [[0, 30], [1, 12], [2, 13], [3, 11], [4, 9], [5, 7], [5, 6], [5, 9.5], [5, 45], [6, 7], [3, 5]];
console.log(JSON.stringify(cases.map(([t, w]) => laneClsOf(t, w))));
'''
        r = subprocess.run(['node', '-e', code], capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(r.stderr)
        return json.loads(r.stdout)

    def test_the_width_rule(self):
        #                  mway trunk prim sec tert res7 res6 res9.5 runway serv narrow
        self.assertEqual(self.lane_cls(True), [1, 1, 0, 0, 0, 2, 2, 0, 2, 2, 2])
        self.assertEqual(self.lane_cls(False), [1, 1, 0, 0, 0, 0, 0, 0, 2, 2, 2])   # ?real=0: every 7 m street keeps its double yellow

    def test_every_tier_uses_it(self):
        s = self.s
        self.assertEqual(s.count('const cls = laneClsOf(t, w);'), 2)   # the outer districts and the far ring
        self.assertNotIn('(t === 5 && w > 10)) ? 2 : 0', s)
        self.assertIn("(REAL && /^(residential|unclassified)$/.test(r.t) && r.w < RES_UNMARKED_W) ? 2 : 0)", s)   # the core
        self.assertIn('wideRoadAdd(pts[j][0], pts[j][1], pts[j + 1][0], pts[j + 1][1], w / 2, laneClsOf(t, w));', s)

    def test_the_paving_strips(self):
        s = self.s
        p = cut(s, '    const strips = { paved: [], milled: [] };', '    if (pavedMesh) {')
        self.assertIn('const cw = roadHalfW(ln.mx, ln.mz, 6), ws = cw === null ? wideStreetAt(ln.mx, ln.mz, 12) : null;', p)
        self.assertIn("REAL ? { cls: p.k === 'milled' ? 3 : pcls, square: true } : null", p)
        self.assertIn('return maxD && !hit ? null : clamp(best, 2.5, 14);', fn(s, 'roadHalfW'))   # without maxD, as it always was
        self.assertIn('|| (lane && lane.square)) continue;', fn(s, 'ribbon'))
        self.assertIn('return best < 0 || !wideRoadInfo[best / 2] ? null : [wideRoadInfo[best / 2], wideRoadInfo[best / 2 + 1]];', fn(s, 'wideStreetAt'))
        self.assertIn("REAL ? roadMat({ color: 0x070706, roughness: 1.0, envMapIntensity: 0.3 }, true)", s)


class Sidewalks(unittest.TestCase):
    """sidewalks.b64 (bake_sidewalks.py): the contract 'Paving the sidewalks' decodes."""

    def test_the_blob(self):
        p = ROOT / 'sidewalks.b64'
        if not p.exists():
            self.skipTest('sidewalks.b64 absent')
        raw = base64.b64decode(p.read_text().strip())
        magic, n, version, zero = struct.unpack_from('<4i', raw, 0)
        self.assertEqual((magic, version, zero), (0x53485757, 1, 0))
        body = struct.unpack_from('<%dh' % ((len(raw) - 16) // 2), raw, 16)
        i, kinds, area, core, bad = 0, {5: 0, 6: 0}, 0.0, 0, 0
        for _ in range(n):
            k, kind, x, z = body[i:i + 4]
            i += 4
            pts = [(x, z)]
            for _ in range(k - 1):
                x += body[i]; z += body[i + 1]; i += 2
                pts.append((x, z))
            kinds[kind] += 1
            a = sum(pts[j][0] * pts[(j + 1) % k][1] - pts[(j + 1) % k][0] * pts[j][1] for j in range(k)) / 2 * 0.04
            if a <= 0:
                bad += 1   # every ring CCW in (x, z)
            area += a
            cx, cz = sum(q[0] for q in pts) / k * 0.2, sum(q[1] for q in pts) / k * 0.2
            if -640 + 50 < cx < 770 - 50 and -520 + 50 < cz < 850 - 50:
                core += 1   # the core lays its own walks
        self.assertEqual(i, len(body), 'every int16 consumed')
        self.assertEqual(bad, 0)
        self.assertEqual(core, 0)
        self.assertGreater(kinds[5], 5000)
        self.assertGreater(kinds[6], 300)                 # the historic districts' brick
        self.assertTrue(3.0e6 < area < 7.0e6, area)       # about 5 km2 of the outer districts


class StreetArt(unittest.TestCase):
    def test_the_manifest(self):
        p = ROOT / 'street_art.json'
        if not p.exists():
            self.skipTest('street_art.json absent')
        d = json.loads(p.read_text())
        for k in ('lanewear', 'ballast', 'concrete', 'steel', 'lot'):
            self.assertTrue((ROOT / d[k]).exists(), d[k])
            self.assertTrue((ROOT / d[k + 'Half']).exists(), d[k + 'Half'])
            self.assertTrue(0 < d[k + 'Mean'] < 1, k)
        r = d['ballastRails']
        self.assertTrue(0.2 < r[0] < 0.5 < r[1] < 0.8, r)   # one rail either side of the middle
        self.assertAlmostEqual(d['ballastM'] / 0.6, round(d['ballastM'] / 0.6), places=6)   # a whole number of tie pitches
        self.assertTrue(10 < d['lanewearM'] < 20)


if __name__ == '__main__':
    unittest.main()
