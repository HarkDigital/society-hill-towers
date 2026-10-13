"""The realism pass, the streets (Oct 12; Mike: "please do anything necessary to make this look more photo realistic and less
cartoony. This should apply to all surfaces"). Under REAL (?real=0 keeps every street as it was):

- the asphalt re-keyed neutral-warm at about 0.45 of its old linear value, each street a little older or newer;
- a realistic lane shader (lanePatchReal): road-aligned wear, the lane photographs, utility cuts, manholes, the gutter and
  the kerb, worn amber and white paint, and at the junctions (streetJunctions, carried on aLane.w by laneW) crossings, stop
  bars and no lane lines through the box; a residential street under 9 m unmarked (laneClsOf, no repack);
- the outer districts' sidewalks (bake_sidewalks.py, sidewalks.b64), filled to the facades, staged in typed arrays, laid
  only within the half mile on a phone (and dropped behind it) and not built in a LITE city;
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

    def test_the_stop_bar_spans_the_inbound_half(self):
        # u = offset . (-dz, dx) in ribbon and the road loops: for a street running north (d = (0, -1)) a point to the east
        # (+x) has u = +1, the right of travel, the side a car drives on. A junction ahead along +s (E falling, lnAhead < 0)
        # is approached on u > 0, so the bar must cover u >= 0 there (the review: it covered the outbound half)
        s = (ROOT / 'app.js').read_text()
        self.assertIn("lanes.push((x-ax)*-dz+(z-az)*dx,sv,hw,lw(sv));", fn(s, 'ribbon'))
        self.assertIn("lane(i,(x-a[0])*-dz+(z-a[1])*dx,", fn(s, 'roadStrip'))
        dx, dz = 0.0, -1.0                      # northbound
        u_east = 1.0 * -dz + 0.0 * dx
        self.assertGreater(u_east, 0)
        f = fn(s, 'lanePatchReal')
        self.assertIn("'    float lnInb = lnTwo > 0.5 ? step(0.0, lnU * sign(-lnAhead)) : 1.0;',", f)
        lnAhead = -1.0                          # the junction lies ahead
        sign = lambda v: (v > 0) - (v < 0)
        step = lambda e, x: 1.0 if x >= e else 0.0
        self.assertEqual(step(0.0, u_east * sign(-lnAhead)), 1.0)     # the bar on the approaching (east) half
        self.assertEqual(step(0.0, -u_east * sign(-lnAhead)), 0.0)    # none on the outbound (west) half

    def test_no_pow_of_a_negative_base(self):
        # pow(x, 2.0) with x < 0 is undefined in GLSL ES: some Mali and Adreno drivers return NaN (the review)
        self.assertNotIn('exp(-pow(', fn((ROOT / 'app.js').read_text(), 'lanePatchReal'))


class Airfields(unittest.TestCase):
    """PHL's runways (45 m) and taxiways (16 m) ride pack_city's class 5: no crossings, stop bars, kerbs or manholes."""

    def test_no_junctions_on_a_runway(self):
        if not shutil.which('node'):
            self.skipTest('node unavailable')
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const isAirfield = ')
        src = s[a:s.index('\n', s.index('  const STREET_JOINS = ', a)) + 1]
        code = src + '\n'.join(fn(s, n) for n in ('streetJunctions',)) + r'''
const recs = [
  { pts: [[-300, 0], [300, 0]], w: 45, t: 5 },     // 0: a runway
  { pts: [[0, -100], [0, 100]], w: 16, t: 5 },     // 1: a taxiway across it
  { pts: [[100, -100], [100, 100]], w: 7, t: 5 },  // 2: a street drawn across the runway's line
  { pts: [[-50, 60], [200, 60]], w: 7, t: 5 },     // 3: a street crossing the taxiway and street 2
];
const JX = streetJunctions(recs, STREET_JOINS, STREET_JOINS, null);
console.log(JSON.stringify(JX));
'''
        r = subprocess.run(['node', '-e', code], capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(r.stderr)
        jx = json.loads(r.stdout)
        self.assertEqual(jx[0], [])                 # the runway takes none
        self.assertEqual(jx[1], [])                 # nor the taxiway
        self.assertEqual(jx[2], [160, 3.5])         # street 2 is crossed by street 3 only (not by the runway)
        self.assertEqual(jx[3], [150, 3.5])         # street 3 by street 2 only (not by the taxiway)

    def test_the_shader_keeps_a_street_off_them(self):
        f = fn((ROOT / 'app.js').read_text(), 'lanePatchReal')
        self.assertIn("lnAir = step(3.5, lnCls);", f)
        self.assertIn("'  float lnStreet = 1.0 - lnDiv - lnMill - lnAir, lnKerb = lnStreet * step(2.6, lnHw);',", f)
        self.assertIn("lpk = step(0.94, lph) * lnFar * lnLaneK;", f)   # no utility cuts


class Lots(unittest.TestCase):
    """lotFrame's phases are taken on the angle the shader rebuilds from its byte, and anchored on the lot's own outline."""

    def test_the_rows_start_at_the_edge(self):
        if not shutil.which('node'):
            self.skipTest('node unavailable')
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const LOT_STALL_W = ')
        code = 'const fl = { nx: Math.cos(0.17), nz: Math.sin(0.17) }; function hash01(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }\n' + \
            s[a:s.index('\n', a) + 1] + fn(s, 'lotFrame') + r'''
const out = [];
for (const [cx, cz, ang, L, W] of [[3100, 4200, 0.4, 120, 60], [-2600, -3900, 1.234, 80, 45], [4800, -100, 2.9, 200, 90]]) {
  const u = [Math.cos(ang), Math.sin(ang)], v = [-u[1], u[0]];
  const poly = [[-L / 2, -W / 2], [L / 2, -W / 2], [L / 2, W / 2], [-L / 2, W / 2]].map(([a, b]) => [cx + a * u[0] + b * v[0], cz + a * u[1] + b * v[1]]);
  const f = lotFrame(poly, 7);
  // the shader's own reading: the angle from its byte, the phases as bytes over 255
  const la = Math.floor(f[0] / 255 * 255 + 0.5) / 255 * Math.PI, U = [Math.cos(la), Math.sin(la)], V = [-U[1], U[0]];
  let wu = Infinity, wv = Infinity;
  for (const p of poly) {
    const lu = p[0] * U[0] + p[1] * U[1] - f[1] / 255 * LOT_STALL_W, lv = p[0] * V[0] + p[1] * V[1] - f[2] / 255 * LOT_MODULE;
    const mu = ((lu % LOT_STALL_W) + LOT_STALL_W) % LOT_STALL_W, mv = ((lv % LOT_MODULE) + LOT_MODULE) % LOT_MODULE;
    wu = Math.min(wu, Math.min(mu, LOT_STALL_W - mu)); wv = Math.min(wv, Math.min(mv, LOT_MODULE - mv));
  }
  out.push([wu, wv]);
}
console.log(JSON.stringify(out));
'''
        r = subprocess.run(['node', '-e', code], capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(r.stderr)
        for wu, wv in json.loads(r.stdout):
            self.assertLess(wu, 0.02)   # a stall tick within 2 cm of the lot's end
            self.assertLess(wv, 0.05)   # a row's back line within 5 cm of its edge


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
        self.assertIn('if (!SW.cells || !isTouch) return;', u)
        self.assertIn('else if (!c.empty && d < NEAR_R) { c.d = d; SW.queue.push(c); }', u)   # laid only within the half mile
        self.assertIn('if (c.mesh) { if (d > NEAR_R + SIDEWALK_KEEP) swDrop(c); }', u)            # and dropped behind it
        self.assertIn('c.mesh.geometry.dispose();', fn(s, 'swDrop'))
        self.assertIn('updateStreets(now);', cut(s, '  function frame(now, once) {', '\n  setHint();'))
        st = cut(s, "  step('Paving the sidewalks'", '  function updateStreets(')
        self.assertIn('if (!isTouch) {', st)   # a computer lays them all at load; a phone the circle about the eye
        self.assertIn('k === 0 || dist(near[k]) < NEAR_R', st)
        self.assertIn("const SIDEWALK_CELL = isTouch ? 200 : (TILE_OFF ? 1e5 : 1200)", s)
        # staged in typed arrays (the review: 3.6 M boxed entries), never a boxed push per vertex
        g = fn(s, 'swGeometry')
        self.assertIn('pos = new Float32Array(cap * 3), col = new Uint8Array(cap * 4)', g)
        self.assertIn('const idx = new IdxBuf(4096);', g)
        self.assertNotIn('pos.push(', g)
        self.assertNotIn('col.push(', g)
        self.assertNotIn('noSow(', cut(s, "  // ---- the outer districts' sidewalks", '  function updateStreets('))   # sidewalkAt, not noSow's arrays
        self.assertIn('if (sidewalkAt(x, z)) return false;', fn(s, 'bareGroundAt'))
        # four-byte streams only (Round 158): the sidewalks' normals and colours (the fade byte in the colour's fourth), the lots' aLot
        self.assertIn("g.setAttribute('normal', new THREE.BufferAttribute(nor, 4, true));", g)
        self.assertIn("const cb = new THREE.InterleavedBuffer(col.subarray(0, nv * 4), 4);", g)
        self.assertIn("g.setAttribute('color', new THREE.InterleavedBufferAttribute(cb, 3, 0, true));", g)
        self.assertIn("g.setAttribute('aSwH', new THREE.InterleavedBufferAttribute(cb, 1, 3, true));", g)
        self.assertIn("if (length(vViewPosition) > uSwFar - ", fn(s, 'swFadePatch'))
        lots = fn(s, 'mergeLots')
        self.assertIn("new THREE.BufferAttribute(lot, 4, true)", lots)
        self.assertIn("new THREE.InterleavedBufferAttribute(new THREE.InterleavedBuffer(col, 4), 3, 0, true)", lots)
        self.assertIn("if (!isTouch) one('steel'", fn(s, 'loadStreetArt'))   # the El's steel and the ties are a computer's

    def test_no_hook_written_inline_in_a_build_step(self):
        # a material hook lives as long as its material, and one written inline in a build step keeps that step's whole scope
        # (Round 158): the decks' hook held every part of 'Raising the overpasses', geometries and arrays, until the review round
        s = self.s
        for a, b in (("  step('Raising the overpasses'", "\n  step('"), ("  step('Painting the El'", "\n  step('")):
            st = cut(s, a, b)
            self.assertNotIn('onBeforeCompile =', st, a)
            self.assertNotIn('customProgramCacheKey =', st, a)
        self.assertIn('if (REAL) deckConcrete(ovpMat);', s)
        self.assertIn('el.material = elSteelMat();', s)
        self.assertIn('groupCity.add(new THREE.Mesh(g, lotSheetMat()));', s)
        self.assertNotIn("m.customProgramCacheKey = () => 'lot sheets';", cut(s, "  step('Raising the outer districts'", "\n  step('"))

    def test_the_flats_stay_out_of_the_pins_capture(self):
        s = self.s
        self.assertIn("m.userData.occFlat = true;", fn(s, 'swAdd'))
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
        src = s[s.index('  const isAirfield = '):s.index('\n', s.index('  const isAirfield = ')) + 1] + s[a:s.index('\n', s.index('  const laneClsOf = ', a)) + 1]
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
        self.assertEqual(self.lane_cls(True), [1, 1, 0, 0, 0, 2, 2, 0, 4, 2, 2])   # the runway: an airfield's class 4
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

    def test_the_ring_test_on_the_int16_form(self):
        if not shutil.which('node'):
            self.skipTest('node unavailable')
        s = (ROOT / 'app.js').read_text()
        code = fn(s, 'swRingHas') + r'''
// an L-shaped ring at (100, 200) in 0.2 m units: (0,0) (50,0) (50,10) (10,10) (10,40) (0,40), as n, kind, x0, z0, deltas
const SW = { v: Int16Array.from([6, 5, 100, 200, 50, 0, 0, 10, -40, 0, 0, 30, -10, 0]) };
const at = (x, z) => swRingHas(0, x * 5, z * 5);
console.log(JSON.stringify([at(21, 41), at(29, 41), at(21, 47), at(19, 41), at(31, 47), at(25, 43)]));
'''
        r = subprocess.run(['node', '-e', code], capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(r.stderr)
        self.assertEqual(json.loads(r.stdout), [True, True, True, False, False, False])

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
