"""Round 220 (the measurement round): the build sub-timers. Nothing drawn changes; each step that the performance plan
wants measured first (p08, p10, p11, p12, p13, p14, p15, p18) carries integer-millisecond phase marks on PERF, read by
__dbg.perf() and spread into the step's beacon through PERF.stepExtra(msg):

  PERF.wide          'Raising the outer districts': dec, loop, yld, junc, flush
  PERF.far           'Raising the rest of Philadelphia': dec, loop, yld, n, rdec, adec, ground, grounds[], flush, roads, areas
                     (the ring's own marks ride raiseRing's and uploadRing's R.ms and are copied in)
  PERF.fit           'Fitting streets to the terrain': ms, pave, fit, sch (schEdges' calls during the step)
  PERF.streetLabels.ms   'Lettering the streets': decode, bands, tex, fit
  PERF.traffic       'Setting the traffic flowing': sample, loop, link, fleet, ways
  TSKIN.msParts      'Cladding the towers': wait, lay, other, flush (TSKIN.ms stays the total, a number)
  PERF.roofKitNote   calls, sampled, ms (one call in sixteen timed, scaled)
  PERF.sch, PERF.triNear   call counters only: schEdges (2.8 M calls a load) and streetTriNear (2.9 M) are never timed
  PERF.clockUs       the clock's quantum in microseconds, read once in the far step

The rule the counters keep: no performance.now() pair inside a function called more than 50,000 times a load, and none
per record in the ring loops (only round their every-4096th flush)."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
NOW = 'performance.now()'


def cut(a, b, start=0):
    i = SRC.index(a, start)
    j = SRC.index(b, i + len(a))
    return SRC[i:j]


def after(a, b):
    """the text between the anchors, the start anchor itself left out (it may carry the mark being counted)"""
    i = SRC.index(a) + len(a)
    return SRC[i:SRC.index(b, i)]


def node(js):
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class OuterStep(unittest.TestCase):
    def setUp(self):
        self.step = cut("  step('Raising the outer districts'", "\n  step('")

    def test_the_marks(self):
        s = self.step
        self.assertIn("const tWD = performance.now();", s)
        self.assertIn("const WMS = PERF.wide = { dec: Math.round(performance.now() - tWD), loop: 0, yld: 0, junc: 0, flush: 0 };", s)
        self.assertLess(s.index('const tWD = performance.now();'), s.index("const bin = unb64(WIDE_B64, 'WIDE');"))
        self.assertIn("const tWL = performance.now();   // Round 220: the record loop\n    for (let i = 0; i < nb; i++) {", s)
        self.assertIn("    }\n    WMS.loop = Math.round(performance.now() - tWL); WMS.yld = Math.round(WMS.yld);   // Round 220\n    if (TOWN_ON) townMass(", s)
        self.assertIn("WMS.junc = Math.round(performance.now() - tJ);", s)
        self.assertLess(s.index("P.wideMs = Math.round(performance.now() - tJ); }"), s.index("WMS.junc = Math.round(performance.now() - tJ);"))
        self.assertIn("const tWF = performance.now();   // Round 220: the flush, the glass chunks' and the fabric's\n    for (const ch of glassChunks.values()) {", s)
        self.assertIn("    flushUploads(true);\n    await yieldNow();\n    WMS.flush = Math.round(performance.now() - tWF);   // Round 220\n    wideSurfaceTasks.push(() => {", s)

    def test_the_record_loop_is_timed_only_round_its_flushes(self):
        loop = after("const tWL = performance.now();   // Round 220: the record loop\n", "WMS.loop = Math.round(performance.now() - tWL);")
        flushes = loop.count("const ty = performance.now(); flushUploads(); await yieldNow(); WMS.yld += performance.now() - ty; }")
        self.assertEqual(flushes, 3)
        self.assertEqual(loop.count(NOW), 2 * flushes)   # the pair round each every-4096th flush, nothing per record
        self.assertEqual(loop.count('(i & 4095) === 4095'), flushes)


class RingSteps(unittest.TestCase):
    def test_raise_ring_returns_its_marks(self):
        ring = cut('  async function raiseRing(bin, S, label, wideSeam, keepAt, buildingsOnly) {', '  // the far ring\'s parks (kind 0)')
        self.assertIn("const RMS = { loop: 0, yld: 0, n: 0, rdec: 0, adec: 0 }, tRL = performance.now();\n    for (let i = 0; i < nb; i++) {", ring)
        self.assertIn("      RMS.n++;   // Round 220: a record raised\n      if (rplan) raisePitched(getChunk(cx, cz), poly, base, h, rplan, c, style, fh, capC,", ring)
        self.assertIn("    }\n    RMS.loop = Math.round(performance.now() - tRL); RMS.yld = Math.round(RMS.yld); const tRD = performance.now();   // Round 220\n", ring)
        self.assertIn("RMS.rdec = Math.round(performance.now() - tRD);   // Round 220: the roads decoded (paved at upload, see paveRoads)\n    const paveRoads = async () => {", ring)
        self.assertIn("const tRA = performance.now();   // Round 220: the areas' decode\n    const areaPolys = [], waterAreaParts = [];", ring)
        self.assertIn("    RMS.adec = Math.round(performance.now() - tRA);\n    return { chunks, rc, paveRoads, areaPolys, waterAreaParts, nwParks, nwWaters, label, ms: RMS };", ring)
        # the record loop: a pair round each every-4096th flush and nothing per record
        loop = after("tRL = performance.now();\n    for (let i = 0; i < nb; i++) {", "RMS.loop = Math.round(performance.now() - tRL);")
        flushes = loop.count("const ty = performance.now(); flushUploads(); await yieldNow(); RMS.yld += performance.now() - ty; }")
        self.assertEqual(flushes, 2)
        self.assertEqual(loop.count(NOW), 2 * flushes)
        # the roads' and the areas' decode loops carry no timer of their own
        self.assertEqual(after("const tRD = performance.now();   // Round 220", "RMS.rdec = Math.round(").count(NOW), 0)
        self.assertEqual(after("const tRA = performance.now();   // Round 220: the areas' decode", "RMS.adec = Math.round(").count(NOW), 0)

    def test_upload_ring_adds_flush_roads_areas(self):
        up = cut('  async function uploadRing(R) {', "\n  step('Raising the rest of Philadelphia'")
        self.assertIn("const M = R.ms || (R.ms = {}), tUF = performance.now();", up)
        self.assertIn("    flushUploads(true);\n    await yieldNow();\n    M.flush = Math.round(performance.now() - tUF); const tUR = performance.now();\n    if (R.paveRoads) await R.paveRoads();", up)
        self.assertIn("    }\n    M.roads = Math.round(performance.now() - tUR);\n    const areaParts = ringAreaParts(R);", up)
        # the water line stays the function's last (tests/test_tiles.py pins it): the far step takes the remainder as areas
        self.assertIn("groupCity.add(occFlatTiles([new THREE.Mesh(g, riverMat)])[0]); }   // Round 168: flat for the pins' capture\n  }\n  step('Raising the rest of Philadelphia'", SRC)

    def test_the_far_step(self):
        s = cut("  step('Raising the rest of Philadelphia'", "\n  // Round 158 (the phones' memory): the ground registry's normals")
        self.assertIn("PERF.clockUs = Math.round(q * 1000); }", s)
        self.assertIn("    const tFD = performance.now();\n    const bin = unb64(CITY_B64, 'CITY');\n    CITY_B64 = null;   // 7 MB of base64 freed\n"
                      "    const FMS = PERF.far = { dec: Math.round(performance.now() - tFD), loop: 0, yld: 0, n: 0, rdec: 0, adec: 0, ground: 0, grounds: [], flush: 0, roads: 0, areas: 0 };", s)
        self.assertIn("    if (!R) return;\n    Object.assign(FMS, R.ms);   // Round 220: the loop's marks, before the strips", s)
        self.assertIn("const tFG = performance.now();   // Round 220: the strips timed one by one (PERF.far.grounds) and together (PERF.far.ground)", s)
        self.assertIn("]) { const tS = performance.now(); mkFarGround(x0, x1, z0, z1, FAR_CELL, nwHole, true, false); FMS.grounds.push(Math.round(performance.now() - tS)); }", s)
        self.assertIn("if (nwHole) { const tS = performance.now(); mkFarGround(nwHole.x0, nwHole.x1, nwHole.z0, nwHole.z1, 50, null, true, true); FMS.grounds.push(Math.round(performance.now() - tS)); }\n"
                      "    FMS.ground = Math.round(performance.now() - tFG);", s)
        self.assertIn("    const tUp = performance.now();\n    await uploadRing(R);\n    Object.assign(FMS, R.ms); FMS.areas = Math.max(0, Math.round(performance.now() - tUp) - FMS.flush - FMS.roads);", s)
        # the strip builder itself is untouched (test_tiles cuts it by the same anchors)
        self.assertNotIn(NOW, cut('    const mkFarGround = (x0, x1, z0, z1, cell, hole, tint, sink) => {', '\n    };'))


class FitStep(unittest.TestCase):
    def test_the_marks(self):
        s = cut("  step('Fitting streets to the terrain'", "\n  // Round 158 (the phones' memory)")
        self.assertIn("const tFit = performance.now(), sch0 = SCH_STAT.calls;", s)
        self.assertIn("    for(const pave of wideSurfaceTasks){pave();await yieldNow();}\n    wideSurfaceTasks.length=0;\n    const tPatch = performance.now();\n    for(const fit of terrainOverlayTasks)fit();\n    terrainOverlayTasks.length=0;\n"
                      "    PERF.fit = { ms: Math.round(performance.now() - tFit), pave: Math.round(tPatch - tFit), fit: Math.round(performance.now() - tPatch), sch: SCH_STAT.calls - sch0 };", s)


class LetteringStep(unittest.TestCase):
    def test_the_marks(self):
        s = cut("  step('Lettering the streets'", "  step('Naming the neighborhoods'")
        self.assertIn("const LMS = { decode: 0, bands: 0, tex: 0, fit: 0 };", s)
        self.assertIn("      const tDec = performance.now();\n      await new Promise((res) => { img.onload = res; img.onerror = res; img.src = 'data:image/png;base64,' + ST_SDF.png; });\n      LMS.decode = Math.round(performance.now() - tDec);", s)
        self.assertIn("      const BAND = 256;\n      const tBand = performance.now();", s)
        self.assertIn("LMS.bands = Math.round(performance.now() - tBand); const tTex = performance.now();\n      tex = new THREE.DataTexture(", s)
        self.assertIn("      renderer.initTexture(tex);\n      LMS.tex = Math.round(performance.now() - tTex);\n    } else {\n      const tTex = performance.now();", s)
        self.assertIn("      tex.anisotropy = anisoOf(16);\n      LMS.tex = Math.round(performance.now() - tTex);\n    }\n    const L2 = ST_LABELS.l;\n    const tFit = performance.now();", s)
        self.assertIn("LMS.fit = Math.round(performance.now() - tFit); stats.ms = LMS;   // Round 220\n    PERF.streetLabels=stats;", s)
        # the label loop carries no timer of its own (10,000 placements)
        self.assertEqual(after("const tFit = performance.now();   // Round 220: the label loop", "LMS.fit = Math.round(").count(NOW), 0)
        # Round 158's order stands: the texture's bytes go with its upload, which happens in the step
        self.assertLess(s.index('freeTexOnUpload(tex)'), s.index('renderer.initTexture(tex)'))


class TrafficStep(unittest.TestCase):
    def test_the_marks(self):
        s = cut("  step('Setting the traffic flowing'", "\n  });")
        self.assertIn("let tSample = 0; const tWays = performance.now();\n    for (let wI = 0; wI < hdr[1]; wI++) {", s)
        self.assertIn("      const runs = [];\n      const tS = performance.now();   // Round 220\n      for (let j = 0; j < pts.length; j++) {", s)
        self.assertIn("      if (cur && cur.xs.length > 1) runs.push(cur);\n      tSample += performance.now() - tS;   // Round 220\n      for (const r of runs) {", s)
        self.assertIn("    const tLink = performance.now();   // Round 220: the way loop is done; the linker, then the fleet\n    trafficPrepareGraph(trafficRuns);\n    const tFleet = performance.now();\n    trafficCreateFleet();\n"
                      "    PERF.traffic = { sample: Math.round(tSample), loop: Math.round(tLink - tWays), link: Math.round(tFleet - tLink), fleet: Math.round(performance.now() - tFleet), ways: hdr[1] };", s)
        # one pair a way (29,749 ways, under the 50,000 line), none per vertex
        self.assertEqual(cut("for (let wI = 0; wI < hdr[1]; wI++) {", "const tLink = performance.now();").count(NOW), 2)
        # test_traffic_link.py runs the decode body under Node without PERF: PERF is first named after the linker's line
        body = cut("    const bin = unb64(TRAFFIC_B64, 'TRAFFIC');", '    trafficPrepareGraph(trafficRuns);')
        code = '\n'.join(l for l in body.split('\n') if not l.strip().startswith('//'))   # the comment may say so
        self.assertNotIn('PERF', code)


class CladdingStep(unittest.TestCase):
    def test_the_marks_and_tskin_ms_stays_a_number(self):
        s = cut("  step('Cladding the towers'", "\n  });")
        self.assertIn("const CMS = TSKIN.msParts = { wait: 0, lay: 0, other: 0, flush: 0 };", s)
        self.assertIn("      const tKinds = performance.now();   // Round 220\n      for (const [kind, list] of byKind) {\n        const T = FRONTS_DATA.tiles[kind];\n        const tWait = performance.now();\n        const [im, mk] = await got.get(kind);\n        CMS.wait += performance.now() - tWait;", s)
        self.assertIn("CMS.wait = Math.round(CMS.wait); CMS.lay = Math.max(0, Math.round(performance.now() - tKinds) - CMS.wait); const tOther = performance.now();", s)
        self.assertIn("CMS.other = Math.round(performance.now() - tOther); const tFlush = performance.now();\n      flushUploads(true);\n      CMS.flush = Math.round(performance.now() - tFlush);\n    } catch (err) {", s)
        # the total keeps its line and its type: __dbg.fronts().towers.ms passes the number through
        self.assertIn('    TSKIN.ms = Math.round(performance.now() - t0);\n  });', s + '\n  });')
        self.assertIn('const TSKIN = { cands: [], meshes: [], laid: {}, bases: {}, ms: 0, error: null };', SRC)
        self.assertIn('ms: TSKIN.ms, msParts: TSKIN.msParts || null, error: TSKIN.error,', SRC)   # the fronts probe carries the parts too (the lead's wiring)
        self.assertEqual(SRC.count('TSKIN.ms = '), 1)


class Counters(unittest.TestCase):
    def test_roof_kit_note_counts_and_samples(self):
        self.assertIn('  const RK_STAT = { calls: 0, sampled: 0, acc: 0, ms: 0 };\n  function roofKitMask(', SRC)
        # registered at load beside STEP_EXTRA, not in the insetRing..roofClutter span tests/test_roof_light_bands.py runs without PERF
        self.assertIn('  PERF.roofKitNote = RK_STAT;', SRC)
        self.assertLess(SRC.index('  PERF.roofKitNote = RK_STAT;'), SRC.index('  const STEP_EXTRA = {'))
        self.assertNotIn('PERF', re.sub(r'//.*', '', cut('  function insetRing(', '  function roofClutter(')))   # the comments may say so
        wrap = cut('  function roofKitNote(ob, ax, top, area, seed, poly, holes, row = 0) {', '  function roofKitNoteRaw(')
        self.assertIn('if ((RK_STAT.calls++ & 15) !== 0) { roofKitNoteRaw(ob, ax, top, area, seed, poly, holes, row); return; }', wrap)
        self.assertIn('RK_STAT.acc += (performance.now() - tk) * 16; RK_STAT.ms = Math.round(RK_STAT.acc); RK_STAT.sampled++;', wrap)
        raw = cut('  function roofKitNoteRaw(ob, ax, top, area, seed, poly, holes, row = 0) {', "  // a point in the lay's frame")
        self.assertNotIn(NOW, raw)
        self.assertNotIn(NOW, cut('  function roofKitMask(ob, ax, poly, holes) {', '  function roofKitNote('))
        # the one call site is roofClutter's, unchanged
        self.assertIn('roofKitNote(ob, ax, base + h, area, seed, poly, holes, ', SRC)

    def test_sch_edges_and_street_tri_near_are_counted_never_timed(self):
        sch = cut('    schEdges = (x, z) => {', '  // the ground height under and beside the river')
        self.assertIn('      SCH_STAT.calls++;   // Round 220: counted, never timed\n      let best = 6400, side = 0;', sch)
        self.assertNotIn(NOW, sch)
        self.assertIn('  const SCH_STAT = { calls: 0 };\n  PERF.sch = SCH_STAT;\n  if (SCH_POLYS) {', SRC)
        tri = cut('  function streetTriNear(ax,az,bx,bz,cx,cz) {', '  function rememberStreetTriangle(')
        self.assertIn('    TRI_NEAR.calls++;   // Round 220: counted, never timed\n    const x0=Math.min(ax,bx,cx)-0.01,', tri)
        self.assertNotIn(NOW, tri)
        self.assertNotIn(NOW, cut('  function groundMeshLandY(x, z) {', '  // ---- conformDrape (Round 52)'))
        # the counter lives beside ROAD_STATS, inside the helpers span the Node harnesses cut (groundGrids to offsetPolyline)
        self.assertIn("  PERF.roads = ROAD_STATS;   // __dbg.roads()\n  const TRI_NEAR = { calls: 0 };", SRC)
        self.assertLess(SRC.index('  const groundGrids = [];'), SRC.index('const TRI_NEAR = { calls: 0 };'))
        self.assertLess(SRC.index('const TRI_NEAR = { calls: 0 };'), SRC.index('  function offsetPolyline('))


class StepExtraTable(unittest.TestCase):
    def test_the_table(self):
        s = cut('  const STEP_EXTRA = {', "  step('Fitting streets to the terrain'")
        for msg, fields in {
            'Raising the outer districts': 'wd: W.dec, wl: W.loop, wy: W.yld, wf: W.flush',
            'Raising the rest of Philadelphia': 'fd: F.dec, fl: F.loop, fy: F.yld, fn: F.n, fg: F.ground, ff: F.flush, fr: F.roads, fa: F.areas, rk: K.ms, rkn: K.calls, cq: PERF.clockUs',
            'Fitting streets to the terrain': 'sm: F.ms, sp: F.pave, sf: F.fit, sc: F.sch, wj: W.junc',
            'Lettering the streets': 'ld: L.decode, lb: L.bands, lt: L.tex, lf: L.fit',
            'Setting the traffic flowing': 'ts: T.sample, tw: T.loop, tl: T.link, tf: T.fleet',
            'Cladding the towers': 'cw: C.wait, cl: C.lay, co: C.other, cf: C.flush',
        }.items():
            self.assertIn("'%s': () =>" % msg, s)
            self.assertIn(fields, s)
        self.assertIn('PERF.stepExtra = (msg) => {', s)
        self.assertLess(SRC.index('PERF.stepExtra = (msg) => {'), SRC.index('  async function build() {'))


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class UnderNode(unittest.TestCase):
    def test_step_extra_rounds_and_drops_the_unmeasured(self):
        table = cut('  const STEP_EXTRA = {', "  step('Fitting streets to the terrain'")
        out = node('''
const PERF = { wide: { dec: 12.4, loop: 3000.6, yld: 7, junc: 0, flush: 90 }, far: { dec: 240, loop: 7400, yld: 300, n: 123456, rdec: 50, adec: 20, ground: 1100, grounds: [300, 280, 260, 250, 10], flush: 400, roads: 900, areas: 150 },
  roofKitNote: { calls: 400000, sampled: 25000, acc: 512.3, ms: 512 }, clockUs: 1000, fit: { ms: 800, pave: 500, fit: 300, sch: 123 },
  streetLabels: { placements: 9000, ms: { decode: 90, bands: 40, tex: 30, fit: 600 } }, traffic: { sample: 700, loop: 1000, link: 200, fleet: 100, ways: 29749 } };
const TSKIN = { ms: 1234, msParts: { wait: 400, lay: 700, other: 100, flush: 34 } };
''' + table + '''
const out = {};
for (const m of ['Raising the outer districts', 'Raising the rest of Philadelphia', 'Fitting streets to the terrain', 'Lettering the streets', 'Setting the traffic flowing', 'Cladding the towers', 'Planting the street trees']) out[m] = PERF.stepExtra(m);
delete PERF.far; delete PERF.traffic; TSKIN.msParts = undefined; PERF.wide.junc = null;
out.missing = [PERF.stepExtra('Raising the rest of Philadelphia'), PERF.stepExtra('Setting the traffic flowing'), PERF.stepExtra('Cladding the towers'), PERF.stepExtra('Raising the outer districts')];
console.log(JSON.stringify(out));''')
        self.assertEqual(out['Raising the outer districts'], {'wd': 12, 'wl': 3001, 'wy': 7, 'wf': 90})
        self.assertEqual(out['Raising the rest of Philadelphia'], {'fd': 240, 'fl': 7400, 'fy': 300, 'fn': 123456, 'fg': 1100, 'ff': 400, 'fr': 900, 'fa': 150, 'rk': 512, 'rkn': 400000, 'cq': 1000})
        self.assertEqual(out['Fitting streets to the terrain'], {'sm': 800, 'sp': 500, 'sf': 300, 'sc': 123, 'wj': 0})
        self.assertEqual(out['Lettering the streets'], {'ld': 90, 'lb': 40, 'lt': 30, 'lf': 600})
        self.assertEqual(out['Setting the traffic flowing'], {'ts': 700, 'tw': 1000, 'tl': 200, 'tf': 100})
        self.assertEqual(out['Cladding the towers'], {'cw': 400, 'cl': 700, 'co': 100, 'cf': 34})
        self.assertEqual(out['Planting the street trees'], {})
        # a step that returned early measured nothing: its beacon carries only what exists (rk and rkn stay, cq stays)
        self.assertEqual(out['missing'][0], {'rk': 512, 'rkn': 400000, 'cq': 1000})
        self.assertEqual(out['missing'][1], {})
        self.assertEqual(out['missing'][2], {})
        self.assertEqual(out['missing'][3], {'wd': 12, 'wl': 3001, 'wy': 7, 'wf': 90})
        # every field is an integer, the query string's kind
        for m, o in out.items():
            for v in (o.values() if isinstance(o, dict) else []):
                self.assertIsInstance(v, int, (m, o))

    def test_roof_kit_note_samples_one_call_in_sixteen(self):
        stat = cut('  const RK_STAT = { calls: 0, sampled: 0, acc: 0, ms: 0 };', '  function roofKitMask(')
        wrap = cut('  function roofKitNote(ob, ax, top, area, seed, poly, holes, row = 0) {', '  function roofKitNoteRaw(')
        out = node('const seen = [];\n' + stat + wrap + '''
function roofKitNoteRaw(ob, ax, top, area, seed, poly, holes, row) { seen.push([top, row]); let s = 0; for (let i = 0; i < 20000; i++) s += Math.sqrt(i); return s; }
for (let i = 0; i < 48; i++) roofKitNote({}, {}, i, 100, 1, null, null, i & 1);
console.log(JSON.stringify({ calls: RK_STAT.calls, sampled: RK_STAT.sampled, ms: RK_STAT.ms, acc: RK_STAT.acc, seen: seen.length, first: seen[0], last: seen[47] }));''')
        self.assertEqual(out['calls'], 48)
        self.assertEqual(out['sampled'], 3)        # calls 0, 16 and 32
        self.assertEqual(out['seen'], 48)          # every call does its work, timed or not
        self.assertEqual(out['first'], [0, 0]); self.assertEqual(out['last'], [47, 1])
        self.assertIsInstance(out['ms'], int); self.assertGreaterEqual(out['ms'], 0)
        self.assertGreaterEqual(out['acc'], 0)

    def test_sch_edges_counts_its_calls(self):
        block = cut('  const SCH_POLYS = (typeof SCHUYLKILL_DATA', '  // the ground height under and beside the river')
        out = node('''const PERF = {}, clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const SCHUYLKILL_DATA = { polys: [{ ring: [[0, 0], [100, 0], [100, 100], [0, 100]], holes: [] }] };
''' + block + '''
const a = schEdges(50, -10), b = schEdges(50, 50), c = schEdges(50, 50);
console.log(JSON.stringify({ calls: PERF.sch.calls, a: [Math.round(a[0]), a[1]], b: [Math.round(b[0]), b[1]], same: PERF.sch === SCH_STAT }));''')
        self.assertEqual(out['calls'], 3)
        self.assertEqual(out['a'], [10, 1])    # 10 m outside the south edge
        self.assertEqual(out['b'], [50, -1])   # the centre, 50 m inside
        self.assertTrue(out['same'])

    def test_street_tri_near_counts_its_calls(self):
        decl = cut('  const TRI_NEAR = { calls: 0 };', '  // At a tier/cut boundary')
        fn = cut('  function streetTriNear(ax,az,bx,bz,cx,cz) {', '  function rememberStreetTriangle(')
        out = node('const PERF = {}; const TERRAIN_PATCH_CELL = 100; let terrainRoadGrid = null, streetSurfaceIndex = null;\n' + decl + fn + '''
const none = streetTriNear(0, 0, 10, 0, 0, 10);
terrainRoadGrid = new Set(['0:0']);
const hit = streetTriNear(0, 0, 10, 0, 0, 10), miss = streetTriNear(500, 500, 510, 500, 500, 510);
console.log(JSON.stringify({ calls: PERF.triNear.calls, none, hit, miss }));''')
        self.assertEqual(out['calls'], 3)
        self.assertFalse(out['none']); self.assertTrue(out['hit']); self.assertFalse(out['miss'])


class NoNewTimerInTheHotPaths(unittest.TestCase):
    """Round 220's rule, as text: the functions the ring loops call per record, and the loops themselves, time nothing."""

    def test_the_hot_functions(self):
        for a, b in (('  function colStat(', '\n  function '), ('    const getChunk = (x, z) => {', '    };'), ('  function pointInPoly(', '\n  function '),
                     ('  function roofClutter(', '  // ---- pitched roofs for the packed tiers')):
            if a in SRC:
                self.assertNotIn(NOW, cut(a, b), a)


if __name__ == '__main__':
    unittest.main()
