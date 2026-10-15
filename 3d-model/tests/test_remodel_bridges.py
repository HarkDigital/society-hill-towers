"""Round 195 (Mike: "Remodel ... the bridges"): the four Delaware crossings rebuilt under the realistic look. The Ben
Franklin and the Walt Whitman are bridgesBuild's at Round 66's place in 'Raising the outer districts' (the themed parts and
the wash sheets are that step's); the Betsy Ross and the Tacony-Palmyra, which the city drew as overpass decks at a third
of their height, keep their overpass chains as the roadway, raised to the bridges' profiles before 'Raising the overpasses'
densifies them, the overpasses' piers standing down under the spans (brOvpSkip). ?real=0 and ?bridges=0 build Round 66's
and Round 12's bridges exactly as they were.

These checks hold the gates and the hooks, the art's manifest, the program (no gl_FragDepth, every stream a multiple of
four bytes), and then run brBuildBfb and brBuildWwb under Node with the vendored three.min.js: each level's triangles in
its budget, every index and normal sound, nothing the Ben Franklin builds inside the envelope a PATCO car runs through
between the anchorages (the bed at deckY + 1, the car 3.1 m wide at 17.75 m either side and 4.42 m tall over the bed),
the walkway's underside where Round 141 put it, the anchorages on OSM's footprints, west of Columbus Boulevard, and the
traffic decks (BRIDGE_DECKS) at Round 66's and Round 12's heights.

The review's fixes: the lattice canvas read with its first row at v 0 (three's flipY had swapped the lacing and the
girder's panel), the Ben Franklin's roadway carried on west and east of its anchorages to where OSM's carriageways reach
grade (the approaches, registered for the traffic past the anchorages only, clear of PATCO's viaducts), the Walt Whitman's
deck centred between its two carriageways, seven painted lanes and a zipper on both decks with the traffic fitted to them,
the Tacony-Palmyra's bascule as deck trusses between towered granite piers, the bridges' own lamp standards alone on the
raised chains with their arms over the lanes, and the overpasses' piers standing down only under those chains."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text(encoding='utf-8')
MOD_START = "  // ---------------------------------------------------------------- the Delaware's bridges, remodelled (Round 195)"
MOD_END = "  // ---------------------------------------------------------------- overpasses"


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class Gates(unittest.TestCase):
    def test_the_gate_and_the_old_bridges(self):
        self.assertIn("const BR_ON = REAL && !/[?&]bridges=0\\b/.test(location.search);", SRC)
        # Round 66's Ben Franklin and Round 12's Walt Whitman stand for ?real=0 and ?bridges=0, untouched within
        self.assertIn("    if (!BR_ON) {   // Round 195: the remodel (bridgesBuild) unless ?real=0 or ?bridges=0\n      const A = BFB_A, B = BFB_B;", SRC)
        self.assertIn("    if (!BR_ON && typeof WWB_PTS !== 'undefined' && WWB_PTS && WWB_PTS.length > 3) {\n      const line = densify(WWB_PTS, 20);", SRC)
        old = cut(SRC, "    if (!BR_ON) {   // Round 195", "    // Walt Whitman Bridge (1957)")
        self.assertIn("const STEEL = '#2452a6', CABLE = '#214a96', FLOOR = '#1c3f7c', ASPHALT = '#262422', WALK = '#6e6656';", old)
        self.assertIn("seg(box(len + 0.5, 0.35, 3.0, 0, 5.8, s * 18.0, 0), WALK);", old)

    def test_the_hooks(self):
        self.assertIn("    if (BR_ON) bridgesBuild({ themeParts, sheetOf });   // Round 195: the four Delaware bridges remodelled\n    if (themeParts.length) {", SRC)
        self.assertIn("    bridgesStep();   // Round 195: the bridges' levels, their art on the approach", SRC)
        self.assertIn("bridges: bridgesProbe, ", SRC)
        self.assertIn("if (bfbNear(p[0], p[2], 25) || wwbNear(p[0], p[2], 25) || brOwns(p[0], p[2])) return false;", SRC)
        piers = cut(SRC, "      // piers wherever there is clearance and no street crossing beneath", "    // ---------------- the Vine Street cut")
        self.assertIn("if (c.br && brOvpSkip(x, z)) continue;", piers)   # only under the bridges' own raised chains (review)
        # the chains are raised in 'Raising the outer districts', before 'Raising the overpasses' densifies and indexes them
        self.assertLess(SRC.index("step('Raising the outer districts'"), SRC.index("step('Raising the overpasses'"))

    def test_the_program(self):
        m = cut(SRC, MOD_START, MOD_END)
        self.assertNotIn('gl_FragDepth', m)
        self.assertIn("g.setAttribute('aBrC', new THREE.BufferAttribute(new Uint8Array(b.C), 4, true));", m)   # four bytes
        self.assertIn("g.setAttribute('aBrUv', new THREE.BufferAttribute(new Float32Array(b.T), 2));", m)
        self.assertIn("m.customProgramCacheKey = () => (lat ? 'bridges-lat' : 'bridges');", m)
        self.assertIn("'#ifdef BR_LAT_ON',", m)   # the discard only in the lattice's own program
        self.assertEqual(m.count('sampler2D'), 1)  # three samplers in one declaration: the detail, the elevations, the lattice
        self.assertIn('uniform sampler2D tBrDet, tBrElev, tBrLat;', m)
        self.assertIn("m.extensions = { derivatives: true };", m)   # the lanes' and the lattice's fwidth on WebGL 1
        self.assertIn("t.flipY = false;", m)                        # the canvas's lacing at v 0 to 0.5, the girder's panel above
        self.assertIn("lampLightPatch(sh, 'vBrW', 'ground');", m)   # the decks take their lamps' pools

    def test_the_review_hooks(self):
        # the cross streets keep their own height under a deck (Columbus Boulevard climbed onto the Ben Franklin)
        self.assertIn("function bridgeDeckLift(x, z, ux, uz) {", SRC)
        self.assertIn("const bY = bridgeDeckLift(x, z, ux, uz);   // the custom spans", SRC)
        # the traffic onto the Ben Franklin's painted lanes, the approaches' at-grade twins gone from both road loops
        self.assertIn("pts = brLaneFit(densify(pts, 20));", SRC)
        self.assertEqual(SRC.count("bfbUnder(mx, mz, dx, dz)) continue;"), 2)
        # the overpasses' 12 m standards leave the raised chains to the bridges' own, and none stands through an approach
        self.assertIn("if (OVP.el[chain] && OVP.el[chain].br) continue;", SRC)
        self.assertIn("if (bridgesOccAt(x, z)) continue;", SRC)
        m = cut(SRC, MOD_START, MOD_END)
        # the arms over the lanes (the first cut turned them out over the river)
        self.assertIn("at.push([x - dz * hw * s, y, z + dx * hw * s, Math.atan2(-dz, dx) + (s > 0 ? Math.PI / 2 : -Math.PI / 2)]);", m)
        # the Tacony-Palmyra's bascule: deck trusses under the floor, no truss over it
        self.assertIn("const bTop = (a) => yd(a) - 0.6, bBot", m)
        self.assertNotIn("bTop = (a) => yd(a) + 7.5", m)
        # the Betsy Ross: solid members and inclined end posts
        self.assertIn("C.steel, null, { chord: 1.1, chordH: 1.2, web: 0.8, webH: 0.9, endPosts: true }", m)
        # the Whitman's deck between its carriageways
        self.assertIn("const WWB_N0 = -7.6;", m)
        self.assertIn("const P = (sv, n, y) => { const q = at(sv), nn = n + WWB_N0;", m)


class Art(unittest.TestCase):
    def test_the_manifest(self):
        A = json.loads((ROOT / 'bridge_art.json').read_text())
        for k in ('detail', 'detailHalf', 'elev', 'elevHalf'):
            self.assertTrue((ROOT / A[k]).exists(), A[k])
            self.assertTrue(A[k].startswith('art/bridges/'), A[k])
        self.assertEqual(A['detailTile'], [3.0, 4.8, 4.0])
        for r in A['rects'].values():
            self.assertTrue(0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1, r)
        self.assertEqual(A['pylonM'], [8.0, 16.0])
        # the review: the 1024 square atlas was 37% blank; 1024 by 512, the pylon and a strip of two bays side by side
        self.assertAlmostEqual(A['friezeM'][0] / A['friezeM'][1], 1.5, delta=0.02)
        self.assertEqual(A['friezeM'][1], 3.4)
        self.assertLess(A['rects']['pylon'][2], A['rects']['frieze'][0])
        self.assertGreater(A['rects']['frieze'][2] - A['rects']['frieze'][0], 0.7)
        with open(ROOT / A['elev'], 'rb') as f:   # the WebP's VP8 or VP8L header: the canvas 1024 by 512
            head = f.read(64)
        self.assertEqual(head[:4], b'RIFF')
        self.assertIn(head[12:16], (b'VP8 ', b'VP8L', b'VP8X'))
        self.assertLess(sum(A['bytes'].values()), 1_000_000)
        build = (ROOT / 'build.py').read_text()
        self.assertIn('const("BRIDGE_ART", text_of("bridge_art.json", "null"))', build)
        self.assertIn('"glass_art.json", "bridge_art.json"):', build)


HARNESS = r'''
const THREE = require(THREE_PATH);
const REAL = true, isTouch = false, location = { search: '' };
const BRIDGE_ART = __ART__, WWB_PTS = __WWB__;
const TERRAIN = { water: -7.34, bed: -9.84 };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function signedArea(pts) { let a = 0; for (let i = 0, n = pts.length; i < n; i++) { const p = pts[i], q = pts[(i + 1) % n]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; }
function siteY(x, z) { return x > 1200 ? -6.0 : -6.35; }
function groundMeshY() { return null; }
function delawareAt() { return false; }
function box(w, h, d, x, y, z, ry) { const g = new THREE.BoxGeometry(w, h, d); if (ry) g.rotateY(ry); g.translate(x, y, z); return g; }
function mergeColored(parts) { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 0, 1, 0], 3)); return g; }
const REMEMBERED = [];
function rememberStreetGeometry(g) { REMEMBERED.push(g.attributes.position.count / 3); }
function postRaw() {} function architecturalBloom() {} function freeOnUpload() {} function anisoOf(n) { return n; } function freeTexOnUpload(t) { return t; }
function artImage() { return Promise.resolve(null); } const artSrc = (a) => a;
const ctx2d = new Proxy({}, { get: (t, k) => (k in t ? t[k] : () => {}), set: (t, k, v) => { t[k] = v; return true; } });
const document = { createElement: () => ({ getContext: () => ctx2d, width: 0, height: 0, style: {} }) };
const renderer = { getPixelRatio: () => 1, capabilities: {} };
const groupCity = { add() {} }, pendingUpload = { push() {} }, PERF = { failed: [] }, camera = { position: new THREE.Vector3() };
const labels = [], labelsRoot = { appendChild() {} }, V3 = THREE.Vector3;
const BRIDGE_DECKS = [], bfbLampPts = [];
let bfbLampMesh = null, bfbNodes = null, bfbNodesMat = null, WWB_LAMP_N = 0;
const OVP = { el: [] }; function ovpIndex() {}
const REBUILD_OCC = [];
const rbBox = (ring) => { let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; for (const q of ring) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); z0 = Math.min(z0, q[1]); z1 = Math.max(z1, q[1]); } return [x0, x1, z0, z1]; };
function pointInPoly(x, z, poly) { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const a = poly[i], b = poly[j]; if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
__DENSIFY__
__BFB__
__MOD__
const themeParts = [], sheets = [];
brBuildBfb({ themeParts, sheetOf: (g) => sheets.push(g) });
brBuildWwb();
const A = BFB_A, L = Math.hypot(BFB_B[0] - A[0], BFB_B[1] - A[1]), ux = (BFB_B[0] - A[0]) / L, uz = (BFB_B[1] - A[1]) / L;
function scan(geoms, test) {
  let bad = 0, nanN = 0, tris = 0, normBad = 0, idxBad = 0, first = null;
  for (const g of geoms) {
    const p = g.attributes.position.array, nr = g.attributes.normal.array, I = g.index ? g.index.array : null, nv = p.length / 3;
    for (let i = 0; i < p.length; i++) if (!Number.isFinite(p[i])) nanN++;
    for (let i = 0; i < nv; i++) { const l = Math.hypot(nr[i * 3], nr[i * 3 + 1], nr[i * 3 + 2]); if (Math.abs(l - 1) > 1e-3) normBad++; }
    const nt = I ? I.length / 3 : nv / 3;
    tris += nt;
    for (let t = 0; t < nt; t++) {
      const ix = I ? [I[t * 3], I[t * 3 + 1], I[t * 3 + 2]] : [t * 3, t * 3 + 1, t * 3 + 2];
      if (ix.some((i) => i < 0 || i >= nv)) { idxBad++; continue; }
      if (!test) continue;
      const v = ix.map((i) => [p[i * 3], p[i * 3 + 1], p[i * 3 + 2]]);
      const pts = v.concat([[(v[0][0] + v[1][0] + v[2][0]) / 3, (v[0][1] + v[1][1] + v[2][1]) / 3, (v[0][2] + v[1][2] + v[2][2]) / 3]],
        [[0, 1], [1, 2], [2, 0]].map(([a, b]) => [(v[a][0] + v[b][0]) / 2, (v[a][1] + v[b][1]) / 2, (v[a][2] + v[b][2]) / 2]));
      if (pts.some(test)) { bad++; if (!first) first = v; }
    }
  }
  return { tris, nanN, normBad, idxBad, bad, first };
}
// a PATCO car's envelope between the anchorages' river faces: 16.25 to 19.25 m either side, from 0.45 m over the bed (the
// ties and rails) to 4.37 m over it (the car's roof, 4.42, less a few centimetres)
const ANCH = [-7, L - 22];
const patco = (q) => { const a = (q[0] - A[0]) * ux + (q[2] - A[1]) * uz, n = Math.abs((q[0] - A[0]) * -uz + (q[2] - A[1]) * ux); if (a < ANCH[0] || a > ANCH[1] || n < 16.25 || n > 19.25) return false; const bed = bfbDeckY(clamp(a / L, 0, 1)) + 1.0; return q[1] > bed + 0.45 && q[1] < bed + 4.37; };
const out = {};
for (const r of BR.list) {
  const nearG = r.chunks.flatMap((c) => c.near.map((m) => m.geometry)), farG = [r.far.geometry];
  const isB = r.name === 'Ben Franklin';
  out[r.name] = { chunks: r.chunks.length, tris: r.tris, near: scan(nearG, isB ? patco : null), far: scan(farG, isB ? patco : null), box: r.box };
}
out.theme = scan(themeParts.map((q) => q.geom), patco);
out.themeSlots = [...new Set(themeParts.map((q) => q.slot))].sort();
out.nodeSlots = bfbNodes ? [...new Set(Array.from(bfbNodes.userData.slot))].sort() : null;
out.decks = BRIDGE_DECKS.map((d) => ({ L: d.cum[d.cum.length - 1], halfW: d.halfW, y0: d.yAt(0), yMid: d.yAt(d.cum[d.cum.length - 1] / 2), yEnd: d.yAt(d.cum[d.cum.length - 1]) }));
out.deckMid = bfbDeckY(0.5); out.deck0 = bfbDeckY(0);
out.lamps = bfbLampPts.length / 3; out.wwbLamps = WWB_LAMP_N; out.sheets = sheets.length; out.remembered = REMEMBERED;
// the approaches: every vertex of the Ben Franklin's past its anchorages within 13.6 m of the roadway's centre line, and
// PATCO's viaducts (their tracks eased as patcoTracks eases them, 2.2 m either side) clear of it by 0.9 m
{
  const nGeoms = BR.list[0].chunks.flatMap((c) => c.near.map((m) => m.geometry)).concat([BR.list[0].far.geometry]);
  let wide = 0, n = 0, first = null;
  for (const g of nGeoms) { const p = g.attributes.position.array; for (let i = 0; i < p.length; i += 3) { const a = (p[i] - A[0]) * ux + (p[i + 2] - A[1]) * uz, nn = (p[i] - A[0]) * -uz + (p[i + 2] - A[1]) * ux; if (a < -56 || a > L + 27) { n++; if (Math.abs(nn - bfbCentreN(a)) > 13.6) { wide++; if (!first) first = [a, nn]; } } } }
  const sm = (e0, e1, v) => { const q = clamp((v - e0) / (e1 - e0), 0, 1); return q * q * (3 - 2 * q); };
  let gap = 1e9;
  for (let a = -553; a <= -30.5; a += 2) { const w = sm(-150.5, -30.5, a), pN = -10.6 * (1 - w) - 17.75 * w, pS = 22.6 * (1 - w) + 17.75 * w, c = bfbCentreN(a); gap = Math.min(gap, (c - 13.5) - (pN + 2.2), (pS - 2.2) - (c + 13.5)); }
  for (let a = L + 30.5; a <= L + 470; a += 2) { const v = sm(L + 30.5, L + 180.5, a), pN = -17.75 + 4.25 * v, pS = 17.75 + 2.75 * v, c = bfbCentreN(a); gap = Math.min(gap, (c - 13.5) - (pN + 2.2), (pS - 2.2) - (c + 13.5)); }
  out.approach = { verts: n, wide, first, patcoGap: gap };
}
out.owns = BR.owns;
console.log(JSON.stringify(out));
'''


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        script = HARNESS.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))) \
            .replace('__ART__', (ROOT / 'bridge_art.json').read_text()).replace('__WWB__', (ROOT / 'wwb.json').read_text()) \
            .replace('__DENSIFY__', cut(SRC, '  function densify(pts, step) {', '  // Bowyer-Watson Delaunay')) \
            .replace('__BFB__', cut(SRC, '  const BFB_A = [400, -940], BFB_B = [1360, -722];', '  function bfbNear(x, z, r) {')) \
            .replace('__MOD__', cut(SRC, MOD_START, MOD_END))
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-3000:])
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    def test_sound_geometry(self):
        for name in ('Ben Franklin', 'Walt Whitman'):
            for lv in ('near', 'far'):
                s = self.out[name][lv]
                self.assertEqual((s['nanN'], s['normBad'], s['idxBad']), (0, 0, 0), (name, lv))
        self.assertEqual((self.out['theme']['nanN'], self.out['theme']['idxBad']), (0, 0))

    def test_the_budgets(self):
        # triangles a level (the near level is solid plus lattice): the Ben Franklin within 45k near and 15k far, the
        # Whitman (3.6 km of deck truss and viaduct) within 60k and 20k; the near level chunked along the bridge
        b, w = self.out['Ben Franklin'], self.out['Walt Whitman']
        self.assertLess(b['tris']['near'] + b['tris']['lat'], 45000, b['tris'])
        self.assertLess(b['tris']['far'], 15000, b['tris'])
        self.assertLess(w['tris']['near'] + w['tris']['lat'], 60000, w['tris'])
        self.assertLess(w['tris']['far'], 20000, w['tris'])
        self.assertGreaterEqual(b['chunks'], 3)
        self.assertGreaterEqual(w['chunks'], 10)
        self.assertLess(self.out['theme']['tris'], 25000)   # the cables, their bands and the suspenders on the themed mesh

    def test_patco_runs_clear(self):
        # nothing in the PATCO car's envelope between the anchorages: not the trusses, the brackets, the legs, the hoods
        for lv in ('near', 'far'):
            s = self.out['Ben Franklin'][lv]
            self.assertEqual(s['bad'], 0, (lv, s['first']))
        self.assertEqual(self.out['theme']['bad'], 0, self.out['theme']['first'])
        m = cut(SRC, MOD_START, MOD_END)
        # the walkway's underside where Round 141 put it (patcoCheck reads deckY + 5.625)
        self.assertIn("[s * 16.5, 5.625, s * 19.5, 5.625, C.steelLo, 0, -1]", m)
        self.assertIn("const inr = s > 0 ? [13.2, 16.0] : [-16.0, -13.2];", m)

    def test_the_slots_are_the_themes(self):
        self.assertEqual(self.out['themeSlots'], [0, 1, 2, 3])
        self.assertEqual(self.out['nodeSlots'], [0, 1, 2, 3])

    def test_traffic_rides_the_old_decks(self):
        d = self.out['decks']
        self.assertEqual(len(d), 4)   # the Ben Franklin, its two approaches (stations past the anchorages only), the Whitman
        self.assertAlmostEqual(d[0]['y0'], self.out['deck0'] + 1.3, places=6)          # Round 66: deckY + 1.3
        self.assertAlmostEqual(d[0]['yMid'], self.out['deckMid'] + 1.3, places=6)
        self.assertEqual(d[0]['halfW'], 20)
        self.assertEqual(d[3]['halfW'], 16)                                            # Round 12's Whitman
        # the approaches meet the span's deck at its own height (the asphalt's top, Round 66's 1.3 over the floor's centre)
        self.assertAlmostEqual(d[1]['yEnd'], self.out['deck0'] + 1.3, places=2)        # the west one ends at the anchorage
        self.assertAlmostEqual(d[2]['y0'], self.out['deck0'] + 1.3, places=2)          # the east one starts at Camden's
        self.assertEqual((d[1]['halfW'], d[2]['halfW']), (15, 15))
        self.assertGreater(len(self.out['remembered']), 0)

    def test_the_approaches_clear_patco(self):
        ap = self.out['approach']
        self.assertGreater(ap['verts'], 1000)
        self.assertEqual(ap['wide'], 0, ap['first'])
        self.assertGreater(ap['patcoGap'], 0.85)   # 0.9 m at the west end, between the viaducts' edges and the parapets

    def test_the_lamps_and_the_night(self):
        # Round 81's walkway lamps (two a panel outside the anchorages' runs, 144), the four over the saddles, the approaches'
        # standards (every 36 m a side off the anchorages' tops, 52), Round 88's 196
        self.assertEqual(self.out['wwbLamps'], 196)
        self.assertEqual(self.out["lamps"], 144 + 4 + 52 + 196)
        self.assertEqual(self.out['sheets'], 6)   # each tower's pier and its two legs washed

    def test_the_anchorages_stand_where_osm_has_them(self):
        # OSM's ways 334628511 and 334628517 (bridge:support=pier): a -54 to -7 and L - 22 to L + 25; Columbus Boulevard's
        # carriageways cross the axis at a 17.1 and 37.8, river side of the Philadelphia anchorage
        m = cut(SRC, MOD_START, MOD_END)
        self.assertIn("const ANCH = [[-54, -7], [L - 22, L + 25]];", m)
        self.assertLess(-7, 17.1)
        box = self.out['Ben Franklin']['box']
        self.assertLess(box[0], 350)


if __name__ == '__main__':
    unittest.main()
