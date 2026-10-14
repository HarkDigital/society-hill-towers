"""Round 190 (Mike: "I want City hall ... to be totally revamped"): City Hall rebuilt to the measured building under the
realistic look (buildCityHallReal), its facades generated photographs (fetch_cityhall_art.py, bake_cityhall_art.py,
cityhall_art.json, art/cityhall/), Round 81's block kept byte for byte for ?real=0.

These checks hold the measured table (NOAA 2022 QL1 LiDAR, OSM relation 4720912, Turner's 1909 booklet), the one themed
slot taken at Round 81's place in the build order, the realistic-look gate, the old block and its flood patch untouched,
the manifest's cells, the level's constants, and then run chModel under Node with the vendored three.min.js: both levels'
triangles within their budgets, every index and normal sound, and the tops within half a metre of the table.

The review's fixes (fix1) are held here too: every wall of the tower faces away from its axis (the clock stage's octagonal
head faced in and the sky showed under the dome), a ray from round the building (the street, a flight round the tower,
the skyline) never first meets the back of a face (the open undersides of the upper balcony, the lantern's gallery and
the crowns, the slots at every mansard's foot and every stage's head), the cut-outs in their own program, the weather
patched in rather than taken for a flat, the bronzes metallic, the dials' sphere on the dials, the café skipped and
rebuilt, tier 2's art."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text(encoding='utf-8')


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class Table(unittest.TestCase):
    def test_the_frame_and_the_tower_axis(self):
        t = cut(SRC, '  const CITY_HALL = {', '  const CH_HOUSE')
        self.assertIn('B0: [-1608.65, -764.51],', t)
        self.assertIn("tower: { c: [0, -37.2],", t)
        # the tower's axis in the scene stays where the viewpoint, the orbit and the skyglow point at it
        fl = (0.986, 0.167, -0.167, 0.986)
        x, z = -1608.65 + fl[2] * -37.2, -764.51 + fl[3] * -37.2
        self.assertAlmostEqual(x, -1602.44, delta=0.05)
        self.assertAlmostEqual(z, -801.19, delta=0.05)

    def test_the_measured_heights(self):
        t = cut(SRC, '  const CITY_HALL = {', '  const CH_HOUSE')
        self.assertIn('st: { water: 1.5, base: 5.57, princ: 15.78, main: 26.63 },', t)
        self.assertIn("roofs: { curtainDeck: 36.0, curb: 32.8, flankDeck: 39.4, centreBody: 49.0, crown: [57.0, 59.6, 61.8, 73.5], cornerCurb: 45.4, cornerCap: 48.8, cornerPole: 58.4 },", t)
        self.assertIn('centreTop: 39.28, cornerTop: 38.13,', t)
        self.assertIn('clock: [102.8, 123.4, 10, 117, 2.5],', t)
        self.assertIn('dome: [[123.4, 8.6], [127, 8.5], [130, 8.2], [133, 7.6], [136, 6.8], [139, 5.8], [142, 4.6]],', t)
        self.assertIn('penn: [155.6, 167.0] },', t)
        # the faces: N V -62.9 to -76.7, S 63.1 to 72.1, E/W |U| 63.2 to 72.0 (the LiDAR's cornice lines)
        self.assertIn('N: { curtain: -62.9, flank: -68.9, corner: -67.0, centre: -75.0, bay: -76.7 },', t)
        self.assertIn('S: { curtain: 63.1, flank: 65.5, corner: 67.8, centre: 70.1, bay: 72.1 },', t)
        self.assertIn('E: { curtain: 63.2, flank: 65.6, corner: 67.6, centre: 70.4, bay: 72.0 },', t)

    def test_the_osm_ring(self):
        t = cut(SRC, '    ring: [[', '  };\n')
        ring = json.loads(t[t.index('['):t.rindex(']') + 1])
        self.assertEqual(len(ring), 71)
        xs, zs = [p[0] for p in ring], [p[1] for p in ring]
        self.assertTrue(-1681 < min(xs) and max(xs) < -1533 and -843 < min(zs) and max(zs) < -689)


class Wiring(unittest.TestCase):
    def test_one_slot_taken_where_round_81_took_it(self):
        blk = cut(SRC, '      cityHall: {', '      // --- Philadelphia Museum of Art')
        self.assertEqual(blk.count('themeSlotN'), 1)
        slot = blk.index('        const chSlot = themeSlotN++ % 4;')
        gate = blk.index('        if (CH_ON) {')
        self.assertLess(slot, gate)
        self.assertIn('buildCityHallReal({ chSlot, themeParts });', blk[gate:gate + 400])
        self.assertIn('break cityHall;', blk[gate:gate + 400])
        # the themed parts merge after it in the same step, and before the rebuilds
        self.assertLess(SRC.index('      cityHall: {'), SRC.index("    if (themeParts.length) {   // the night's themed lights"))
        self.assertLess(SRC.index("    if (themeParts.length) {   // the night's themed lights"), SRC.index("  step('Rebuilding the landmarks'"))

    def test_the_realistic_look_gate(self):
        self.assertIn("const CH_ON = REAL && typeof CITYHALL_ART !== 'undefined' && !!CITYHALL_ART && !!CITYHALL_ART.cells;", SRC)
        # fix1: City Hall's outline was dropped at pack and its tower's parts go with BRIDGE_SKIP, so the loop's old skip of
        # the outline never fired; the café on Dilworth Park is skipped there instead (as DEMOLISHED is: wideColK counted)
        self.assertNotIn('rbDist(cx, cz, CITY_HALL.ring) <= 2', SRC)
        self.assertIn('[-1603, -802, 24]', SRC)
        self.assertIn("if (CH_ON && !CH_CAFE.poly && Math.hypot(cx - CH_CAFE[0], cz - CH_CAFE[1]) < 14) { if (h <= 45 && t <= 6) wideColK++; CH_CAFE.poly = poly; CH_CAFE.h = h; CH_CAFE.c = [cx, cz]; continue; }", SRC)
        # the loop has a CH of its own (the chunk size), so it never names City Hall's state
        loop = cut(SRC, "  step('Raising the outer districts'", '      if (ovpStraddle(poly, cx, cz)) continue;')
        self.assertIn('const CH = 700;', loop)
        self.assertNotIn('CH.cafe', loop)
        build = cut(SRC, '  function buildCityHallReal(ctx) {', '  // the atlas and its mask')
        self.assertIn('chCafe(far.b, CH.cafe, Y0);', build)
        self.assertIn('chCafe(near.b, CH.cafe, Y0);', build)

    def test_the_old_block_stands_for_real_0(self):
        blk = cut(SRC, '      cityHall: {', '      // --- Philadelphia Museum of Art')
        for line in ('        const hallMat=cityMat.clone(),hallFacade=cityMat.onBeforeCompile;', '        if (VDEPTH_WANT) vdepthTwin(hallMat);',
                     "        hallMat.customProgramCacheKey=()=> 'city-hall-soft-flood';",
                     '        appendBuilding(hallChunk(bx, bz), sqPoly(bx, bz, 148, 143), base - 1, base + 27, c, 1, base, [sqPoly(bx, bz, 64, 59)]);'):
            self.assertIn(line, blk)
        # Round 109's flood patch, which ?real=0 and tests/city_hall_gpu.html run, is the pre-round one to the byte
        flood = cut(SRC, '  function cityHallFloodPatch(sh,uniforms) {', '  const BOATHOUSE_PLANS')
        self.assertEqual(hashlib.sha256(flood.encode()).hexdigest()[:16], 'fdf4e57d694b39d2')
        self.assertIn('vec3 hc=mix(vec3(.38,.32,.23),uHallColor,uHallOn);', flood)
        self.assertIn("float tower=hallBeam((hp-vec2(0.0,-55.0))/vec2(19.0,20.0));", flood)

    def test_the_frame_steps_it_and_dev_probes_it(self):
        fr = cut(SRC, '  function frame(now, once) {', '\n  setHint();')
        self.assertEqual(fr.count('cityHallStep();'), 1)
        self.assertIn(' cityHall: cityHallProbe,', SRC)

    def test_the_level_constants(self):
        self.assertIn('const CH_NEAR_R = isTouch ? 420 : 650, CH_HYST = 40, CH_ART_R = 1000;', SRC)
        step = cut(SRC, '  function cityHallStep() {', '  // ?dev: __dbg.cityHall()')
        self.assertIn("else if (lod === 'near' && d > CH_NEAR_R + CH_HYST) lod = 'far';", step)
        # fix1: tier 2 (the far level alone) takes the half art once the eye is within CH_NEAR_R
        self.assertIn('if ((isTouch || TIER2) && d < (TIER2 ? CH_NEAR_R : CH_ART_R)) chLoadArt();', step)
        self.assertIn("if (CH.art !== 'none') return;", cut(SRC, '  function chLoadArt() {', '  const _chE'))
        self.assertIn('if (!isTouch && !TIER2) chLoadArt();', SRC)
        self.assertIn("if (CH.cut) CH.cut.visible = lod === 'near' && !CH.off;", step)

    def test_phone_streams_and_samplers(self):
        g = cut(SRC, '  function chGeometry(b, Y0) {', '  // the untextured materials')
        # the colour as four normalized bytes (never three), the kind and seed as two floats: no 1- or 3-byte stream
        self.assertIn("g.setAttribute('aCol', new THREE.BufferAttribute(new Uint8Array(b.C), 4, true));", g)
        self.assertIn("g.setAttribute('aK', new THREE.BufferAttribute(new Float32Array(b.K), 2));", g)
        m = cut(SRC, '  function chMaterial(chSlot, Y0, cut) {', '  // the cut-out parts\' shadow')
        # its own samplers: the atlas, the mask, the pitched roofs' slate and the flat roofs' tar for the decks (fix1; the
        # lamps' maps, the shadows and the weather's come with the shared patches)
        self.assertEqual(sorted(set(__import__('re').findall(r'uniform sampler2D ([^;]+);', m))), ['uMask, uPitchArt, uRoofArt'])
        self.assertNotIn('userData.vdepth', cut(SRC, '  // ---- City Hall rebuilt (Round 190', "  step('Restoring the landmarks'"))

    def test_the_cut_outs_have_their_own_program(self):
        m = cut(SRC, '  function chMaterial(chSlot, Y0, cut) {', '  // the cut-out parts\' shadow')
        # the discard rides only the cut program, and only on the balustrade's own cell (fix1: on every cell the mask's
        # filtered void and dial edges holed the walls round the portals, and the whole building lost its early depth test)
        self.assertEqual(m.count('discard'), 1)
        self.assertIn("...(cut ? ['if (abs(vChK.x - ' + balusIx.toFixed(1) + ') < 0.5 && frMask.b > 0.16 && frMask.b < 0.33 && frMask.r < 0.5) discard;'] : []),", m)
        self.assertIn("if (cut) mat.defines = { CH_CUT: 1 };", m)
        build = cut(SRC, '  function buildCityHallReal(ctx) {', '  // the atlas and its mask')
        self.assertIn("const { keep, take } = chSplit(near.b, Object.keys(A.cells).sort().indexOf('balus'));", build)
        self.assertIn("CH.cut = mk(take, CH.matCut, 'city-hall-cut'); CH.cut.customDepthMaterial = chCutDepth();", build)
        dm = cut(SRC, '  function chCutDepth() {', '  // the dials: a canvas a dial')
        self.assertIn('depthPacking: THREE.RGBADepthPacking', dm)
        self.assertIn('discard', dm)

    def test_the_weather_is_patched_in_not_flagged(self):
        m = cut(SRC, '  function chMaterial(chSlot, Y0, cut) {', '  // the cut-out parts\' shadow')
        # fix1: as userData.wxSurf the building was taken for a flat on the ground and kept out of the river's mirror
        self.assertNotIn('userData.wxSurf', m)
        self.assertIn('      wxSurfacePatch(sh);   // first', m)
        self.assertIn("+ '|wx';", m)
        self.assertIn('mat.userData.wxSurf = true;', cut(SRC, '  function chFloor(Y0) {', '  // Dilworth Park'))

    def test_the_bronzes_are_metal(self):
        b = cut(SRC, '  function chBronze(themeParts, chSlot, Y0) {', '  // the courtyard')
        self.assertIn('style: 3, gain: -1 });', b)
        self.assertIn("if (vTheme.z < 0.0) { metalnessFactor = 0.62; roughnessFactor = 0.42; }", SRC)
        self.assertIn('totalEmissiveRadiance += te * uNight * 2.4 * abs(vTheme.z) * mix(1.0, 0.42, tsat); }', SRC)

    def test_the_dials_sphere_holds_the_dials(self):
        build = cut(SRC, '  function buildCityHallReal(ctx) {', '  // the atlas and its mask')
        a = build.index('chHands(clock.minutes);')
        self.assertLess(a, build.index('CH.dial.geometry.computeBoundingSphere();'))

    def test_no_em_dashes_in_its_strings(self):
        blk = cut(SRC, '  // ---- City Hall rebuilt (Round 190', "  step('Restoring the landmarks'")
        for ch in ('—', '·'):
            for line in blk.splitlines():
                if ch in line:
                    code = line.split('//')[0]
                    self.assertNotIn(ch, code, line)


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((ROOT / 'cityhall_art.json').read_text())

    def test_the_cells(self):
        cells = self.m['cells']
        want = {'aedicule', 'apse', 'ashlar', 'balus', 'belvedere', 'centre', 'clock', 'corner', 'court', 'curtain', 'dome', 'dormer_c',
                'dormer_w', 'flank', 'oculus', 'tower_low', 'tower_mid', 'turret'}
        self.assertEqual(set(cells), want)
        rects = list(cells.values())
        for r in rects:
            self.assertTrue(0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1, r)
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                self.assertFalse(a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6, (a, b))
        self.assertEqual(set(self.m['m']), want)
        self.assertEqual(set(self.m['mean']), want)

    def test_what_the_page_builds_to_the_pictures(self):
        meta = self.m['meta']
        a0, a1, spring, crown = meta['centre']['arch']
        self.assertAlmostEqual(a1 - a0, 5.0, delta=0.6)      # the 18 ft archway
        self.assertAlmostEqual(crown, 9.14, delta=0.8)        # 30 ft
        self.assertLess(spring, crown)
        cu, cy, ru, rv = meta['clock']['dial']
        self.assertAlmostEqual(cu, 10.0, delta=0.5)           # centred on the 20 m face
        self.assertAlmostEqual(102.8 + cy, 110.0, delta=0.6)  # 361 ft
        self.assertAlmostEqual(max(ru, rv) * 2, 7.92, delta=0.6)   # 26 ft
        self.assertEqual(len(meta['centre']['cols']), 12)
        self.assertEqual(len(meta['corner']['cols']), 8)
        self.assertEqual(len(meta['flank']['cols']), 2)

    def test_the_files_and_the_phone_copies(self):
        for k in ('img', 'imgHalf', 'mask', 'maskHalf'):
            self.assertTrue(self.m[k].startswith('art/cityhall/'), k)
            self.assertTrue((ROOT / self.m[k]).exists(), k)
        self.assertEqual(self.m['size'], [2048, 2048])


# the geometry checks, in the building frame (U, y, V): a small BVH over the triangles; every ray's first hit (two faces
# within 2 mm of each other count as one: a two-sided board is two single-sided quads) and whether it is a back face
GEOM = r'''
function bvh(P, I) {
  const n = I.length / 3, cx = new Float32Array(n * 3), bb = new Float32Array(n * 6);
  for (let t = 0; t < n; t++) {
    let x0 = 1e9, y0 = 1e9, z0 = 1e9, x1 = -1e9, y1 = -1e9, z1 = -1e9;
    for (let k = 0; k < 3; k++) { const o = I[t * 3 + k] * 3; x0 = Math.min(x0, P[o]); x1 = Math.max(x1, P[o]); y0 = Math.min(y0, P[o + 1]); y1 = Math.max(y1, P[o + 1]); z0 = Math.min(z0, P[o + 2]); z1 = Math.max(z1, P[o + 2]); }
    bb.set([x0, y0, z0, x1, y1, z1], t * 6); cx.set([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], t * 3);
  }
  const ids = Array.from({ length: n }, (_, i) => i);
  const build = (a, b) => {
    const nd = { box: [1e9, 1e9, 1e9, -1e9, -1e9, -1e9] };
    for (let i = a; i < b; i++) { const t = ids[i]; for (let k = 0; k < 3; k++) { nd.box[k] = Math.min(nd.box[k], bb[t * 6 + k]); nd.box[k + 3] = Math.max(nd.box[k + 3], bb[t * 6 + k + 3]); } }
    if (b - a <= 8) { nd.leaf = ids.slice(a, b); return nd; }
    const ext = [0, 1, 2].map((k) => nd.box[k + 3] - nd.box[k]), ax = ext.indexOf(Math.max(...ext));
    const sub = ids.slice(a, b).sort((p, q) => cx[p * 3 + ax] - cx[q * 3 + ax]);
    for (let i = a; i < b; i++) ids[i] = sub[i - a];
    const m = (a + b) >> 1; nd.l = build(a, m); nd.r = build(m, b); return nd;
  };
  const root = build(0, n);
  const hitBox = (bx, o, d, tmax) => { let t0 = 0, t1 = tmax; for (let k = 0; k < 3; k++) { const inv = 1 / (d[k] || 1e-12); let ta = (bx[k] - o[k]) * inv, tb = (bx[k + 3] - o[k]) * inv; if (ta > tb) { const s = ta; ta = tb; tb = s; } t0 = Math.max(t0, ta); t1 = Math.min(t1, tb); if (t0 > t1) return false; } return true; };
  return (o, d, tmax) => {
    const hits = [], st = [root];
    while (st.length) {
      const nd = st.pop(); if (!hitBox(nd.box, o, d, tmax)) continue;
      if (!nd.leaf) { st.push(nd.l, nd.r); continue; }
      for (const t of nd.leaf) {
        const a = I[t * 3] * 3, b = I[t * 3 + 1] * 3, c = I[t * 3 + 2] * 3;
        const e1 = [P[b] - P[a], P[b + 1] - P[a + 1], P[b + 2] - P[a + 2]], e2 = [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]];
        const pv = [d[1] * e2[2] - d[2] * e2[1], d[2] * e2[0] - d[0] * e2[2], d[0] * e2[1] - d[1] * e2[0]], det = e1[0] * pv[0] + e1[1] * pv[1] + e1[2] * pv[2];
        if (Math.abs(det) < 1e-12) continue;
        const tv = [o[0] - P[a], o[1] - P[a + 1], o[2] - P[a + 2]], u = (tv[0] * pv[0] + tv[1] * pv[1] + tv[2] * pv[2]) / det; if (u < -1e-7 || u > 1 + 1e-7) continue;
        const qv = [tv[1] * e1[2] - tv[2] * e1[1], tv[2] * e1[0] - tv[0] * e1[2], tv[0] * e1[1] - tv[1] * e1[0]], v = (d[0] * qv[0] + d[1] * qv[1] + d[2] * qv[2]) / det; if (v < -1e-7 || u + v > 1 + 1e-7) continue;
        const tt = (e2[0] * qv[0] + e2[1] * qv[1] + e2[2] * qv[2]) / det; if (tt <= 1e-4 || tt > tmax) continue;
        const nx = e1[1] * e2[2] - e1[2] * e2[1], ny = e1[2] * e2[0] - e1[0] * e2[2], nz = e1[0] * e2[1] - e1[1] * e2[0];
        hits.push([tt, Math.sign(nx * d[0] + ny * d[1] + nz * d[2]), P[a + 1]]);
      }
    }
    return hits.sort((p, q) => p[0] - q[0]);
  };
}
function seeThrough(b, N) {
  const P = b.P, I = b.I, cast = bvh(P, I), n = I.length / 3;
  let s = 7; const R = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const cum = new Float64Array(n); let tot = 0;
  for (let t = 0; t < n; t++) { const a = I[t * 3] * 3, c = I[t * 3 + 1] * 3, e = I[t * 3 + 2] * 3; const u = [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]], v = [P[e] - P[a], P[e + 1] - P[a + 1], P[e + 2] - P[a + 2]]; tot += Math.hypot(u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]) / 2; cum[t] = tot; }
  const pick = () => { const x = R() * tot; let lo = 0, hi = n - 1; while (lo < hi) { const m = (lo + hi) >> 1; if (cum[m] < x) lo = m + 1; else hi = m; } return lo; };
  const eyes = [];
  for (let k = 0; k < 16; k++) { const a = k / 16 * Math.PI * 2; eyes.push([Math.cos(a) * 115, 1.7, Math.sin(a) * 118 - 3], [Math.cos(a) * 200, 30, Math.sin(a) * 200]); }
  for (let k = 0; k < 12; k++) { const a = (k + 0.5) / 12 * Math.PI * 2; for (const [r, y] of [[40, 118], [30, 146], [45, 95], [60, 64], [24, 160]]) eyes.push([Math.cos(a) * r, y, Math.sin(a) * r - 37.2]); }
  for (let k = 0; k < 8; k++) { const a = k / 8 * Math.PI * 2; eyes.push([Math.cos(a) * 150, 220, Math.sin(a) * 150]); }
  const out = { rays: 0, back: 0, backTower: 0 };
  for (const e of eyes) for (let i = 0; i < N; i++) {
    const t = pick(), a = I[t * 3] * 3, c = I[t * 3 + 1] * 3, f = I[t * 3 + 2] * 3; let r1 = R(), r2 = R(); if (r1 + r2 > 1) { r1 = 1 - r1; r2 = 1 - r2; }
    const p = [0, 1, 2].map((k) => P[a + k] + (P[c + k] - P[a + k]) * r1 + (P[f + k] - P[a + k]) * r2);
    const d = [p[0] - e[0], p[1] - e[1], p[2] - e[2]], L = Math.hypot(d[0], d[1], d[2]); d[0] /= L; d[1] /= L; d[2] /= L;
    out.rays++;
    const h = cast(e, d, L + 0.01); if (!h.length) continue;
    let front = false, back = null; for (const x of h) { if (x[0] > h[0][0] + 0.002) break; if (x[1] < 0) front = true; else back = x; }
    if (front || !back) continue;
    out.back++;
    if (e[1] + d[1] * back[0] > 60) out.backTower++;
  }
  return out;
}
function towerFacing(b) {
  const P = b.P, I = b.I, cu = 0, cv = -37.2; let n = 0, bad = 0;
  for (let t = 0; t < I.length; t += 3) {
    if (b.K[I[t] * 2] === b.balusK) continue;   // the balustrades are boards seen from both sides
    const A = I[t] * 3, B2 = I[t + 1] * 3, C = I[t + 2] * 3;
    const ux = P[B2] - P[A], uy = P[B2 + 1] - P[A + 1], uz = P[B2 + 2] - P[A + 2], vx = P[C] - P[A], vy = P[C + 1] - P[A + 1], vz = P[C + 2] - P[A + 2];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx, l = Math.hypot(nx, ny, nz);
    if (l < 1.0 || Math.abs(ny) / l > 0.3) continue;
    let w = 0; for (const [p, q] of [[A, B2], [B2, C], [C, A]]) w = Math.max(w, Math.hypot(P[p] - P[q], P[p + 2] - P[q + 2])); if (w < 1.5) continue;   // a column's or a pier's narrow faces
    const mx = (P[A] + P[B2] + P[C]) / 3, my = (P[A + 1] + P[B2 + 1] + P[C + 1]) / 3, mz = (P[A + 2] + P[B2 + 2] + P[C + 2]) / 3;
    if (my < 49.5 || Math.hypot(mx - cu, mz - cv) > 15) continue;   // the tower over every roof
    n++;
    if ((mx - cu) * nx + (mz - cv) * nz < 0) bad++;
  }
  return { n, bad };
}
'''


class Model(unittest.TestCase):
    def run_model(self, touch):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        mod = cut(SRC, '  // ---- City Hall rebuilt (Round 190', "  // the night's flood on the rebuilt block")
        script = r'''
const THREE = require(THREE_PATH);
const REAL = true, isTouch = TOUCH;
const CITYHALL_ART = MANIFEST;
const fl = { px: 140, pz: 0, dx: -0.167, dz: 0.986, nx: 0.986, nz: 0.167 };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
MOD
GEOM
const out = {};
for (const far of [false, true]) {
  const { b, tops } = chModel(CITYHALL_ART, far);
  const ids = Object.keys(CITYHALL_ART.cells).sort();
  b.balusK = ids.indexOf('balus');
  const see = seeThrough(b, 120), tower = towerFacing(b);
  // the undersides: down-facing faces under the upper balcony, the lantern's gallery and the crowns' cornice boxes
  const soff = { bal2: 0, gallery: 0, box: 0 };
  for (let t = 0; t < b.I.length; t += 3) {
    const A = b.I[t] * 3, B2 = b.I[t + 1] * 3, Cc = b.I[t + 2] * 3, P = b.P;
    const ux = P[B2] - P[A], uy = P[B2 + 1] - P[A + 1], uz = P[B2 + 2] - P[A + 2], vx = P[Cc] - P[A], vy = P[Cc + 1] - P[A + 1], vz = P[Cc + 2] - P[A + 2];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx, l = Math.hypot(nx, ny, nz) || 1;
    if (ny / l > -0.9) continue;
    const my = (P[A + 1] + P[B2 + 1] + P[Cc + 1]) / 3;
    if (Math.abs(my - 87.5) < 0.05) soff.bal2++; else if (Math.abs(my - 149.5) < 0.05) soff.gallery++; else if (Math.abs(my - 53.6) < 0.05) soff.box++;
  }
  let bad = 0, nanP = 0, nanN = 0, short = 0;
  for (const i of b.I) if (!(i >= 0 && i < b.nv)) bad++;
  for (const v of b.P) if (!Number.isFinite(v)) nanP++;
  for (let i = 0; i < b.nv; i++) { const l = Math.hypot(b.N[i * 3], b.N[i * 3 + 1], b.N[i * 3 + 2]); if (!Number.isFinite(l)) nanN++; else if (l < 0.5) short++; }
  let ymax = -1e9, ymin = 1e9; for (let i = 1; i < b.P.length; i += 3) { ymax = Math.max(ymax, b.P[i]); ymin = Math.min(ymin, b.P[i]); }
  const g = chGeometry(b, 2.45);
  out[far ? 'far' : 'near'] = { tris: b.I.length / 3, verts: b.nv, bad, nanP, nanN, short, ymax, ymin, tops, see, tower, soff,
    balus: b.K.filter((k, i) => i % 2 === 0 && k === b.balusK).length,
    attrs: Object.fromEntries(Object.entries(g.attributes).map(([k, a]) => [k, [a.array.constructor.name, a.itemSize, a.array.BYTES_PER_ELEMENT * a.itemSize]])) };
}
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('TOUCH', 'true' if touch else 'false') \
            .replace('MANIFEST', (ROOT / 'cityhall_art.json').read_text()).replace('MOD', mod).replace('GEOM', GEOM)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def check(self, out, near_budget):
        for lod, budget in (('near', near_budget), ('far', 6000)):
            o = out[lod]
            self.assertLessEqual(o['tris'], budget, lod)
            self.assertEqual((o['bad'], o['nanP'], o['nanN'], o['short']), (0, 0, 0, 0), lod)
            self.assertGreaterEqual(o['ymin'], -0.01, lod)
            for k, (typ, size, bytes_) in o['attrs'].items():
                self.assertEqual(bytes_ % 4, 0, (lod, k, typ, size))   # no 1- or 3-byte stream (Round 158)
        t = out['near']['tops']
        for k, v in (('centreCrown', 61.8), ('cornerCap', 48.8), ('flankDeck', 39.4), ('centreBody', 49.0), ('crownDeck', 57.0),
                     ('masonry', 102.8), ('clockStage', 123.4), ('dome', 142.0), ('cupola', 155.6), ('turret', 48.5), ('apse', 24.5)):
            self.assertAlmostEqual(t[k], v, delta=0.5, msg=k)
        # the highest point the model itself builds is the north crown's flagpole (73.5) under the cupola's head, where Penn's
        # feet stand (he rides the themed parts to 167.0)
        self.assertAlmostEqual(out['near']['ymax'], 155.6, delta=0.1)
        for lod in ('near', 'far'):
            o = out[lod]
            # fix1: every wall of the tower over the roofs faces away from its axis (the octagonal head faced in)
            self.assertGreater(o['tower']['n'], 100, lod)
            self.assertEqual(o['tower']['bad'], 0, lod)
            # and from round the building no ray first meets the back of a face: none over 60 m (the tower's stages, the
            # dome's foot, the balconies, the gallery), hardly any at all (a valley's sliver between two roofs)
            self.assertGreaterEqual(o['see']['rays'], 12000, lod)
            self.assertEqual(o['see']['backTower'], 0, (lod, o['see']))
            self.assertLess(o['see']['back'] / o['see']['rays'], 0.001, (lod, o['see']))
        # the undersides the review found open: the upper balcony's, the lantern gallery's and the crowns' cornice boxes'
        n = out['near']['soff']
        self.assertGreaterEqual(n['bal2'], 8)
        self.assertGreaterEqual(n['gallery'], 8)
        self.assertGreaterEqual(n['box'], 16)
        # the balustrades and the cresting ride their own (cut-out) mesh in the near level; the far level has none
        self.assertGreater(out['near']['balus'], 100)
        self.assertEqual(out['far']['balus'], 0)

    def test_a_computer(self):
        out = self.run_model(False)
        self.check(out, 60000)
        self.assertGreater(out['near']['tris'], 5 * out['far']['tris'] / 2)

    def test_a_phone(self):
        self.check(self.run_model(True), 30000)


if __name__ == '__main__':
    unittest.main()
