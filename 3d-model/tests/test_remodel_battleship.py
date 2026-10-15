"""Round 195 (Mike: "Remodel ... Battleship NJ"): the USS New Jersey rebuilt as BB-62 lies at Camden, under the realistic
look (njBuild), her plating, bulkheads, steel decks and teak a generated atlas (fetch_nj_art.py, bake_nj_art.py,
nj_art.json, art/nj/), the Round 30 ship kept as it was for ?real=0 and ?nj=0 and as a failed build's fallback.

These checks hold the measured tables (HAER HI-62's general plans of her sister Missouri: the sheer, the half-breadths,
the stem's rake), the gate and the old ship's place in the build order, the remodel's place after the piers are decked,
the frame's hook and the dev probe, the manifest and its inlining, the phone-safe streams, and then run njModel under
Node with the vendored three.min.js: both levels' triangles within their budgets, every index and normal sound, her
length, beam, deck heights and masthead, the hull's normals outboard, the 62 reading left to right from outboard on both
bows, the railings and the deck lamps.

The review's fixes (Round 195, the same round): the 01 and 02 cut into recessed bays under the deck over them, the
conning tower, a few hundred lockers and boxes, the lattice foremast and mainmast as truss quads in the railings' draw
with the SPS-49 a curved strip, the funnels' platforms, searchlights, steam pipes and whistle, the floods by the height
over the deck that carries them, the deck lamps sized by the drawing buffer and staged for culling, the guns raised with
their tampions' stars, her lines to the pier, no anchor in the hawse, her own card on a tap, the bulkhead art mirrored by
its place, and the old lens kind gone."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text(encoding='utf-8')
MOD0, MOD1 = '  // ---- the USS New Jersey remodelled (Round 195', '  // ------------------------------------------------ museum ships'


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


MOD = cut(SRC, MOD0, MOD1)


class Gate(unittest.TestCase):
    def test_the_realistic_look_and_its_flag(self):
        self.assertIn("const NJ_ON = REAL && !/[?&]nj=0\\b/.test(location.search);", MOD)
        self.assertIn("NJ_ON && typeof NJ_ART !== 'undefined' && !!NJ_ART && !!NJ_ART.img", MOD)

    def test_the_old_ship_stands_for_real_0_where_it_stood(self):
        wide = cut(SRC, '    const lmTrim = [];', "    setLoadingMessage('Raising the outer districts, uploading');")
        self.assertIn('let njOld = null;', wide)
        old = cut(wide, '      njOld = () => {', '      if (njPoly && !NJ_ON) njOld();')
        # the Round 30 ship, unchanged: the hull extruded into the chunk, the turrets and funnels in lmTrim
        for s in ('appendBuilding(chkN, njPoly, W0 - 1.5, W0 + 8.7, c, 3, W0);', "turretAt(62, D0, 1);", "turretAt(-58, D0, -1);",
                  "shipBox(-4, 0, D0 + 2.2, 84, 4.4, 17, gray);"):
            self.assertIn(s, old)

    def test_the_remodel_waits_for_the_piers(self):
        wide = cut(SRC, '    const lmTrim = [];', "    setLoadingMessage('Raising the outer districts, uploading');")
        areas = wide.index('// parks, water, piers')
        build = wide.index('if (njPoly && NJ_ON && !njBuildSafe(njPoly) && njOld) njOld();')
        self.assertGreater(build, areas)   # PIER_RINGS holds the T-head by then (njFindPier)
        self.assertIn('PIER_RINGS.push({ poly, y: yD, lift: 0 });', SRC)

    def test_the_frame_steps_it_and_dev_probes_it(self):
        self.assertIn('njStep();   // Round 195', SRC)
        self.assertIn('nj: njProbe,', SRC)
        self.assertIn("NJ.near.userData.occStandIn = NJ.far;", MOD)   # the pins' depth image takes the far level

    def test_the_build_inlines_the_manifest(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("NJ_ART", text_of("nj_art.json", "null"))', b)
        self.assertIn('"nj_art.json"', b[b.index('for name in ("tree_art.json"'):b.index('    if (ROOT / name).exists():')])   # in build.py's art file list

    def test_the_manifest(self):
        m = json.loads((ROOT / 'nj_art.json').read_text())
        self.assertEqual(m['cells'], ['hull', 'bulkhead', 'deck', 'teak'])
        self.assertEqual(m['grid'], [2, 2])
        self.assertEqual(len(m['mean']), 4)
        self.assertEqual(len(m['m']), 4)
        for p in (m['img'], m['imgHalf']):
            self.assertRegex(p, r'^art/nj/atlas(-half)?\.[0-9a-f]{10}\.webp$')
            self.assertTrue((ROOT / p).exists(), p)
        # the teak cut on its own seams: a whole number of 15 cm planks up
        self.assertAlmostEqual(m['m'][3][1] / 0.15, round(m['m'][3][1] / 0.15), places=3)
        self.assertEqual(m['m'][1][1], 2.7)   # the bulkhead one deck level, deck to overhead


class Streams(unittest.TestCase):
    def test_four_byte_streams_and_no_frag_depth(self):
        self.assertIn("g.setAttribute('aCol', new THREE.BufferAttribute(new Uint8Array(b.C), 4, true));", MOD)
        self.assertNotIn('gl_FragDepth', MOD)
        self.assertNotRegex(MOD, r'Uint8Array\([^)]*\),\s*[13]\b')

    def test_the_weather_and_the_lamps_patched_in(self):
        mat = cut(MOD, '  function njMaterial(f) {', '  // the atlas, a computer')
        self.assertLess(mat.index('wxSurfacePatch(sh);'), mat.index("Object.assign(sh.uniforms, U);"))
        self.assertIn("lampLightPatch(sh, 'vWPos', 'wall');", mat)
        self.assertIn("textureGrad(map, njA", mat)
        self.assertIn('freeTexOnUpload(NJ.map);', MOD)

    def test_no_em_dashes_or_middots_in_its_strings(self):
        for line in MOD.split('\n'):
            code = line.split('//')[0]
            for ch in ('—', '·'):
                self.assertNotIn(ch, code, line)


class Model(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        pip = cut(SRC, '  function pointInPoly(x, y, pts) {', '  function polyCentroid(pts) {')
        script = r'''
const THREE = require(THREE_PATH); const REAL = true, isTouch = false, TIER2 = false;
const location = { search: '' }; const NJ_ART = null; const PIER_RINGS = [];
const TERRAIN = { water: -7.84 }; const lampUniform = { value: 0 }, nightUniform = { value: 0 };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
__PIP__
__MOD__
NJ.pier = { s0: 70, s1: 192, edge: 20.4, y: -5.09, gang: [97, 166], dolphins: [217, 45] };
const out = {};
for (const lo of [false, true]) {
  NJ.clutter = 0; NJ.lines = 0;
  const { b, mesh } = njModel(lo);
  let bad = 0, nanP = 0, x0 = 1e9, x1 = -1e9, y1 = -1e9, zMax = 0, hullOut = 0, hullIn = 0;
  for (const i of b.I) if (i < 0 || i >= b.nv) bad++;
  for (let v = 0; v < b.nv; v++) {
    const x = b.P[v * 3], y = b.P[v * 3 + 1], z = b.P[v * 3 + 2], nl = Math.hypot(b.N[v * 3], b.N[v * 3 + 1], b.N[v * 3 + 2]);
    if (!isFinite(x + y + z) || Math.abs(nl - 1) > 1e-3) nanP++;
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
    if (b.K[v * 2] === NJK.hull && Math.abs(b.K[v * 2 + 1] - 0.37) < 1e-6) { zMax = Math.max(zMax, Math.abs(z)); if (Math.abs(z) > 2 && y > 0.5) { if (b.N[v * 3 + 2] * z > 0) hullOut++; else hullIn++; } }
  }
  const kinds = {}; for (let v = 0; v < b.nv; v++) kinds[b.K[v * 2]] = (kinds[b.K[v * 2]] || 0) + 1;
  const mk = {}; for (const e of mesh) mk[e.t] = (mk[e.t] || 0) + 1;
  // the bays' walls: the near level's darker bulkhead faces; the soffits: faces looking down in the soffit's shade
  let bayV = 0, soffitV = 0; for (let v = 0; v < b.nv; v++) { const c = [b.C[v * 4], b.C[v * 4 + 1], b.C[v * 4 + 2]]; if (b.K[v * 2] === NJK.bulk && c[0] === NJC.bay[0] && c[1] === NJC.bay[1]) bayV++; if (b.N[v * 3 + 1] < -0.99 && c[0] === NJC.soffit[0]) soffitV++; }
  // the funnels' seeds (their heights) and the bulkheads' seeds (the heights their floods stand at)
  const fSeeds = new Set(), bSeeds = new Set(); for (let v = 0; v < b.nv; v++) { if (b.K[v * 2] === NJK.funnel) fSeeds.add(+b.K[v * 2 + 1].toFixed(2)); if (b.K[v * 2] === NJK.bulk) bSeeds.add(+b.K[v * 2 + 1].toFixed(2)); }
  out[lo ? 'far' : 'near'] = { tris: b.I.length / 3, bad, nanP, len: x1 - x0, top: y1, zMax, hullOut, hullIn, mesh: mesh.length, mk, kinds, bayV, soffitV, clutter: NJ.clutter, lines: NJ.lines, fSeeds: [...fSeeds], bSeeds: [...bSeeds].sort((a, c) => a - c) };
}
// the sheer and the sections
out.deck = [0, 70, 132, 196.3, 250, 270.54].map((s) => +njDeck(s).toFixed(2));
out.sec = [10, 100, 200, 250, 266].map((s) => { const q = njSec(s, 8); return [+q[0][0].toFixed(3), +q[0][1].toFixed(3), +njDeck(s).toFixed(3), +njBeam(s).toFixed(3)]; });
// the hull number: where u = 0 (the 62's left) and u = 0.5 lie along her, each side
const m = njMarks({ cx: 0, cz: 0, hx: 1, hz: 0, sx: 0, sz: 1, W0: 0 });
const ends = [];
for (let i = 0; i < 2; i++) { const base = i * 20; ends.push({ zSide: Math.sign(m.P[base * 3 + 2]), xLeft: m.P[base * 3], xRight: m.P[(base + 12) * 3], uLeft: m.T[base * 2], uRight: m.T[(base + 12) * 2] }); }   // a side: the 62's seven columns of two, then the hawse's three
out.marks = ends;
const r = njRails({}); out.rails = r.I.length / 3;
{ const { mesh } = njModel(false), r2 = njRails({}, mesh); out.railsAll = r2.I.length / 3; out.railsUv = []; for (let i = 0; i < r2.nv; i++) out.railsUv.push(r2.T[i * 2 + 1]); out.railsUv = [Math.min(...out.railsUv), Math.max(...out.railsUv)]; }
out.notched = njNotched(NJ_HOUSE[1], 1).pl.length - NJ_HOUSE[1].length; out.notched2 = njNotched(NJ_HOUSE[2], 2).pl.length - NJ_HOUSE[2].length;
out.floodTower = njFloodBase(8, [njX(138.0), 3.4], [njX(147.0), 3.4]); out.floodOwn = njFloodBase(2, [njX(100), 7.8], [njX(110), 7.8]);
out.house = NJ_HOUSE.length;
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('__PIP__', pip).replace('__MOD__', MOD)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-3000:])
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    def test_budgets(self):
        self.assertLess(self.out['near']['tris'], 22000)   # 16k at the build, 19.6k after the review's bays, clutter, masts and funnels
        self.assertLess(self.out['far']['tris'], 4000)     # 3.4k
        self.assertGreater(self.out['near']['tris'], 3 * self.out['far']['tris'])

    def test_sound_geometry(self):
        for k in ('near', 'far'):
            self.assertEqual(self.out[k]['bad'], 0, k)
            self.assertEqual(self.out[k]['nanP'], 0, k)

    def test_her_measures(self):
        n = self.out['near']
        self.assertLess(abs(n['len'] - 270.54), 25)   # the hull 270.54 m; the anchor cables run 20 m ahead of the stem
        self.assertLess(abs(n['zMax'] - 16.47), 0.05)   # the beam 32.94 m
        self.assertGreater(n['top'], 49.5)             # the foremast's head about 50.7 m over the river
        self.assertLess(n['top'], 52.0)
        d = self.out['deck']
        self.assertAlmostEqual(d[2], 6.65, places=2)    # the main deck amidships, a metre lighter than the design
        self.assertGreater(d[5], 11.5)                  # the bow's sheer
        self.assertLess(d[3], d[4])
        for top_y, top_z, D, B in self.out['sec']:
            self.assertAlmostEqual(top_y, D, places=3)  # every section starts at the deck edge
            self.assertAlmostEqual(top_z, B, places=3)

    def test_the_hull_faces_outboard(self):
        n = self.out['near']
        self.assertGreater(n['hullOut'], 20 * max(1, n['hullIn']))

    def test_the_62_reads_from_outboard(self):
        # starboard (z > 0): its left (u = 0) aft of its right; port: its left forward of its right
        for e in self.out['marks']:
            self.assertEqual(e['uLeft'], 0)
            if e['zSide'] > 0:
                self.assertLess(e['xLeft'], e['xRight'])
            else:
                self.assertGreater(e['xLeft'], e['xRight'])

    def test_the_railings_the_lattices_and_the_radars_mesh(self):
        self.assertGreater(self.out['rails'], 300)
        mk = self.out['near']['mk']
        self.assertEqual(mk.get('sps'), 1)     # the SPS-49's reflector, a curved strip drawn with the railings
        self.assertEqual(mk.get('truss'), 16)  # two lattices, four faces, two rows a face
        self.assertGreaterEqual(mk.get('rail', 0), 12)   # the masts' platforms and the whistle's
        self.assertEqual(self.out['far']['mesh'], 0)
        # the lattices, the reflector and the platforms' rails: under a hundred more triangles in the same draw
        self.assertLess(self.out['railsAll'] - self.out['rails'], 100)
        lo, hi = self.out['railsUv']
        self.assertGreaterEqual(lo, 0.02)
        self.assertLessEqual(hi, 0.99)

    def test_the_deck_lamps(self):
        self.assertIn("for (const sd of [1, -1]) for (let s = 2; s < 268.5; s += 2.4)", MOD)
        self.assertIn('NJ.lights.visible = night > 0.01', MOD)

    def test_the_superstructures_bays_and_overhangs(self):
        n = self.out['near']
        self.assertEqual(self.out['notched'], 4 * 6)    # six bays a side in the 01's straight runs, four points each
        self.assertEqual(self.out['notched2'], 4 * 6)
        self.assertEqual(n['bayV'], 12 * 2 * 3 * 4)   # every bay's back and end walls in the darker shade, both sides
        self.assertGreater(n['soffitV'], 12 * 2 * 4)    # the deck over each bay seen from under it
        self.assertGreaterEqual(n['clutter'], 250)      # a few hundred lockers and boxes (274)
        self.assertEqual(self.out['far']['clutter'], 0)   # the far level builds none
        self.assertIn('function njConning(b, lo)', MOD)

    def test_the_floods_stand_on_decks(self):
        # the fire-control tower's walls run up from the 06's deck (the stack's), never a band a level; a bulkhead with
        # a deck at its foot is lit from that deck
        self.assertAlmostEqual(self.out['floodTower'], 6 * 2.55, places=3)
        self.assertAlmostEqual(self.out['floodOwn'], 2 * 2.55, places=3)
        self.assertEqual(sorted(self.out['near']['fSeeds']), [8.2, 9.8])   # the funnels' heights, for the soot
        mat = cut(MOD, '  function njMaterial(f) {', '  // the atlas, a computer')
        self.assertNotIn('fract(max(fh, 0.0)', mat)   # the old sawtooth: a stripe every 2.55 m on every face
        self.assertIn('smoothstep(-0.5, -0.2, nW.y)', mat)   # a face that looks down takes no flood
        self.assertIn('uNjPier', mat)

    def test_the_lamps_are_sized_by_the_buffer_and_culled(self):
        lights = cut(MOD, '  function njLights(f) {', '  // the pier along her starboard side')
        self.assertIn('uNjBuf', lights)
        self.assertNotIn('renderer.getPixelRatio()', lights)
        self.assertIn('pendingUpload.push(p)', lights)
        self.assertIn('njLampU.uNjBuf.value = renderer.getDrawingBufferSize(_njBuf).y;', MOD)

    def test_the_guns_the_tampions_and_the_hawse(self):
        self.assertIn('njTurret(b, 196.3, 1, njDeck(196.3) + 0.75, 10, lo);', MOD)
        self.assertIn('njTurret(b, 174.2, 1, NJ_Y0 + 3.6, 17, lo);', MOD)
        self.assertIn('capK: lo ? NJK.black : NJK.tamp', MOD)
        self.assertIn('njStar(', MOD)
        self.assertGreaterEqual(self.out['near']['kinds'].get(str(13), 0), 9 * 15)   # nine tampions' discs
        gear = cut(MOD, '  function njDeckGear(b) {', '  // the railings: a quad a run')
        self.assertNotIn('the anchor in its hawse', gear)
        self.assertNotIn('lens', MOD.split('const NJK')[1].split('\n')[0])
        self.assertNotIn('NJK.lens', MOD)

    def test_her_lines_to_the_pier(self):
        self.assertGreaterEqual(self.out['near']['lines'], 4)
        self.assertLessEqual(self.out['near']['lines'], 6)

    def test_a_tap_opens_her_own_card(self):
        pick = cut(SRC, '  function bldgPick(cx, cy) {', '  // a building\'s card at (ax, ay, az)')
        self.assertIn('if (njAt(p[0], p[1], p[2])) { njCard(p[0], p[1] + 1, p[2]); return true; }', pick)
        self.assertLess(pick.index('njAt('), pick.index("if (p[1] < g + 2 && !glo) return false;"))
        card = cut(SRC, '  function njCard(ax, ay, az) {', '  function updateBldgPick() {')
        self.assertIn('USS New Jersey (BB-62)', card)
        for ch in ('\u2014', '\u00b7'):
            self.assertNotIn(ch, card)


if __name__ == '__main__':
    unittest.main()
