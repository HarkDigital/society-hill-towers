"""Round 225: the roof-kit masks by an exact scanline, and no roof notes where no rooftop hardware is laid.

roofKitMask asks pointInPoly 240 times a roof (48 cells, five samples each) for every flat roof of the three packed
tiers: the largest per-record cost of the ring loops (rk on the beacons, 0.53 to 0.88 s on Mike's iPhone and 3.4 to
4.4 s on the Windows desktops). roofKitScan reads the same 240 samples from 18 rows in the roof box's own frame and
refuses to answer within 1e-7 m of the footprint's edge, where roofKitFast asks roofKitMask instead, as it does for a
roof with holes. The rule for a change like this is that it is exact, proven over the shipped data and never argued:

  * every record of wide.b64, city.b64 and outskirts.b64 that the page's own gates would note goes through both
    functions, cut from app.js, under Node and under JavaScriptCore (the phone's engine: the two hand orientedBox's
    Math.hypot back an ulp apart, so each must prove its own equality), and no mask may differ;
  * the core's buildings in scene.json go through them too, as the core loop hands them to roofClutter: these are the
    only footprints that are not on a packer's grid (floats to the centimetre), the only ones with real holes (three
    courtyards, which must fall back) and one the page cuts in two before the loop (the Liberty Bell Center, lbellSplit);
  * the fallback is needed, and the check can see a wrong mask: with the margin at 0 some masks do differ;
  * the page's own ?dev self-check (RK_SCAN.check) counts exactly what the direct comparison counts.

The second half: tier 2 lays no rooftop hardware, and 'Fitting out the rooftops' threw every note away there. One
flag, ROOF_KIT_ON, is read by that step and by roofClutter, and it is declared outside the span the Node tests cut
(insetRing to roofClutter), which has no tiers in scope.

Neither engine on the machine is a failure, not a skip, while the blobs are there: a deploy must not go out unguarded."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BLOBS = (('wide.b64', 0.2), ('city.b64', 0.7), ('outskirts.b64', 1.0))   # each tier's file and its loop's own S
SCENE = 'scene.json'   # the core: its buildings reach roofClutter from the core loop, holes and all


def cut(src, a, b):
    i = src.index(a)
    return src[i:src.index(b, i)]


def page_functions(src):
    """The page's own code the masks run on: nothing here is rewritten for the test."""
    return '\n'.join([
        cut(src, '  function signedArea(', '  function pointInPoly('),
        cut(src, '  function pointInPoly(', '  function polyCentroid('),
        cut(src, '  function orientedBox(', '  // hip roof over an OBB'),
        cut(src, '  function obbAxis(', '  function obbEnd('),
        cut(src, '  function insetRing(', '  function roofClutter('),
    ])


def core_split(src):
    """lbellSplit as the page runs it before the core loop, with the helpers it reads."""
    return '\n'.join([
        cut(src, '  function signedArea(', '  function pointInPoly('),
        cut(src, '  function orientedBox(', '  // hip roof over an OBB'),
        cut(src, '  function obbAxis(', '  function obbEnd('),
        cut(src, '  const LBELL_ON = ', '  // the inscription, the founders'),
    ])


# One program for both engines. `readText` and `emit` are the only things that differ between them.
PROGRAM = r'''
function b64bytes(s) {
  var T = new Int8Array(128).fill(-1), A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  for (var i = 0; i < 64; i++) T[A.charCodeAt(i)] = i;
  var n = s.length;
  while (n && T[s.charCodeAt(n - 1) & 127] < 0) n--;   // padding and a trailing newline
  var out = new Uint8Array(Math.floor(n * 3 / 4)), o = 0, i = 0;
  for (; i + 3 < n; i += 4) {
    var w = (T[s.charCodeAt(i)] << 18) | (T[s.charCodeAt(i + 1)] << 12) | (T[s.charCodeAt(i + 2)] << 6) | T[s.charCodeAt(i + 3)];
    out[o++] = w >> 16; out[o++] = (w >> 8) & 255; out[o++] = w & 255;
  }
  if (n - i === 2) { out[o++] = ((T[s.charCodeAt(i)] << 18) | (T[s.charCodeAt(i + 1)] << 12)) >> 16; }
  else if (n - i === 3) { var w2 = (T[s.charCodeAt(i)] << 18) | (T[s.charCodeAt(i + 1)] << 12) | (T[s.charCodeAt(i + 2)] << 6); out[o++] = w2 >> 16; out[o++] = (w2 >> 8) & 255; }
  return out;
}
var clock = (typeof performance !== 'undefined' && performance.now) ? function () { return performance.now(); } : function () { return Date.now(); };
// the page's code, twice: as it ships, and with the scan's margin at 0 (no fallback but for holes)
var SHIP = (function () { %(page)s
  return { signedArea: signedArea, orientedBox: orientedBox, obbAxis: obbAxis, roofKitMask: roofKitMask, roofKitScan: roofKitScan, roofKitFast: roofKitFast, RK_SCAN: RK_SCAN, RK_EPS: RK_EPS, roofKitOn: roofKitOn }; })();
var BARE = (function () { %(bare)s
  return { roofKitFast: roofKitFast, RK_SCAN: RK_SCAN, RK_EPS: RK_EPS }; })();
var out = { eps: SHIP.RK_EPS, bareEps: BARE.RK_EPS, tiers: {}, masks: 0, differ: 0, bareDiffer: 0, fallbacks: 0, holed: 0, msOld: 0, msNew: 0, firstDiff: null };
var BATCH = 4096, obs = new Array(BATCH), axs = new Array(BATCH), polys = new Array(BATCH), hls = new Array(BATCH).fill(null), res = new Float64Array(BATCH * 2);
function flush(m, T) {
  var i, r;
  var t0 = clock();
  for (i = 0; i < m; i++) { r = SHIP.roofKitFast(obs[i], axs[i], polys[i], hls[i]); res[i * 2] = r[0]; res[i * 2 + 1] = r[1]; }
  var t1 = clock();
  for (i = 0; i < m; i++) {
    r = SHIP.roofKitMask(obs[i], axs[i], polys[i], hls[i]);
    if (r[0] !== res[i * 2] || r[1] !== res[i * 2 + 1]) { T.differ++; if (!out.firstDiff) out.firstDiff = { poly: polys[i], holes: hls[i], ob: obs[i], ax: axs[i], old: r, scan: [res[i * 2], res[i * 2 + 1]] }; }
    res[i * 2] = r[0]; res[i * 2 + 1] = r[1];
  }
  var t2 = clock();
  for (i = 0; i < m; i++) { r = BARE.roofKitFast(obs[i], axs[i], polys[i], hls[i]); if (r[0] !== res[i * 2] || r[1] !== res[i * 2 + 1]) T.bareDiffer++; }
  T.msNew += t1 - t0; T.msOld += t2 - t1;
}
var FILES = %(files)s, SCENE_NAME = %(sceneName)s, SCENE_PATH = %(scenePath)s;
for (var f = 0; f < FILES.length; f++) {
  var bin = b64bytes(readText(FILES[f][1])), S = FILES[f][2];
  var hdr = new Int32Array(bin.buffer, 0, 4), body = new Int16Array(bin.buffer, 16, (bin.length - 16) >> 1);
  var hasAttr = hdr[0] !== 0x53485458 && hdr[0] !== 0x53485459, nb = hdr[1], k = 0, m = 0;
  var T = out.tiers[FILES[f][0]] = { records: nb, masks: 0, differ: 0, bareDiffer: 0, fallbacks: 0, msOld: 0, msNew: 0 };
  var fb0 = SHIP.RK_SCAN.fallbacks;
  for (var i = 0; i < nb; i++) {
    // the ring loops' own decode (app.js: the outer districts' loop and raiseRing)
    var n = body[k++], h = body[k++] / 5, mh = body[k++] / 5; k++;
    if (hasAttr) k += 2;
    var poly = new Array(n);
    for (var j = 0; j < n; j++) { poly[j] = [body[k++] * S, body[k++] * S]; }
    // the gates between a record and its mask: the loops' (!mh && h < 60), roofClutter's (h >= 3, hs >= 2.2) and
    // roofKitNoteRaw's (the area). The roof plan is ignored (a pitched roof takes no note), so this is every mask
    // the page can ask for and some it does not
    if (mh || h >= 60 || h < 3) continue;
    var ob = SHIP.orientedBox(poly);
    if (!ob) continue;
    var ax = SHIP.obbAxis(ob);
    if (ax.hs < 2.2) continue;
    var area = Math.abs(SHIP.signedArea(poly));
    if (area < 25 || area > 40000) continue;
    obs[m] = ob; axs[m] = ax; polys[m] = poly; m++;
    if (m === BATCH) { flush(m, T); T.masks += m; m = 0; }
  }
  flush(m, T); T.masks += m;
  T.fallbacks = SHIP.RK_SCAN.fallbacks - fb0;
  T.msOld = Math.round(T.msOld); T.msNew = Math.round(T.msNew);
  out.masks += T.masks; out.differ += T.differ; out.bareDiffer += T.bareDiffer; out.fallbacks += T.fallbacks; out.msOld += T.msOld; out.msNew += T.msNew;
}
// the core (scene.json), as the core loop hands each building to roofClutter: b.poly as stored (floats, on no packer's
// grid) with b.holes && b.holes.length ? b.holes : null. Only roofClutter's and the note's own gates stand between a
// record and its mask here (hs >= 2.2, the area): the loop's (a ship, a custom model, a pitched or tall roof) are
// ignored, so this is every mask the core can ask for and some it does not. Then the one footprint the page changes
// before the loop: lbellSplit cuts the Liberty Bell Center, and the loop passes what is left
(function () {
  var CORE = (function () { var REAL = true, location = { search: '' }; %(split)s
    return { lbellSplit: lbellSplit, LBELL: LBELL }; })();
  var blds = JSON.parse(readText(SCENE_PATH)).buildings;   // read as bytes: the names are not used
  var T = out.tiers[SCENE_NAME] = { records: blds.length, masks: 0, differ: 0, bareDiffer: 0, fallbacks: 0, holed: 0, msOld: 0, msNew: 0, split: false };
  var fb0 = SHIP.RK_SCAN.fallbacks, m = 0;
  var take = function (b) {
    if (!b.poly || b.poly.length < 3) return;
    var ob = SHIP.orientedBox(b.poly);
    if (!ob) return;
    var ax = SHIP.obbAxis(ob);
    if (ax.hs < 2.2) return;
    var area = Math.abs(SHIP.signedArea(b.poly));
    if (area < 25 || area > 40000) return;
    var holes = b.holes && b.holes.length ? b.holes : null;
    if (holes && holes.some(function (hr) { return hr && hr.length > 2; })) T.holed++;
    obs[m] = ob; axs[m] = ax; polys[m] = b.poly; hls[m] = holes; m++;
    if (m === BATCH) { flush(m, T); T.masks += m; m = 0; }
  };
  for (var i = 0; i < blds.length; i++) take(blds[i]);
  CORE.lbellSplit(blds);
  if (CORE.LBELL.b && !CORE.LBELL.err) { T.split = true; take(CORE.LBELL.b); }
  flush(m, T); T.masks += m; hls.fill(null);
  T.fallbacks = SHIP.RK_SCAN.fallbacks - fb0;
  T.msOld = Math.round(T.msOld); T.msNew = Math.round(T.msNew);
  out.masks += T.masks; out.differ += T.differ; out.bareDiffer += T.bareDiffer; out.fallbacks += T.fallbacks; out.holed += T.holed; out.msOld += T.msOld; out.msNew += T.msNew;
})();
out.counted = SHIP.RK_SCAN.masks; out.bareFallbacks = BARE.RK_SCAN.fallbacks;
// the page's ?dev self-check, on the margin-free copy that is known to be wrong somewhere: it must count what the direct
// comparison counted, over the towns again (and 0 on the shipped copy)
(function () {
  var bin = b64bytes(readText(FILES[2][1])), S = FILES[2][2], hdr = new Int32Array(bin.buffer, 0, 4), body = new Int16Array(bin.buffer, 16, (bin.length - 16) >> 1);
  var hasAttr = hdr[0] !== 0x53485458 && hdr[0] !== 0x53485459, nb = hdr[1], k = 0;
  BARE.RK_SCAN.check = true; SHIP.RK_SCAN.check = true;
  var b0 = BARE.RK_SCAN.masks, s0 = SHIP.RK_SCAN.masks, sf0 = SHIP.RK_SCAN.fallbacks;
  for (var i = 0; i < nb; i++) {
    var n = body[k++], h = body[k++] / 5, mh = body[k++] / 5; k++;
    if (hasAttr) k += 2;
    var poly = new Array(n);
    for (var j = 0; j < n; j++) { poly[j] = [body[k++] * S, body[k++] * S]; }
    if (mh || h >= 60 || h < 3) continue;
    var ob = SHIP.orientedBox(poly);
    if (!ob) continue;
    var ax = SHIP.obbAxis(ob);
    if (ax.hs < 2.2) continue;
    var area = Math.abs(SHIP.signedArea(poly));
    if (area < 25 || area > 40000) continue;
    BARE.roofKitFast(ob, ax, poly, null); SHIP.roofKitFast(ob, ax, poly, null);
  }
  out.selfCheck = { bare: { masks: BARE.RK_SCAN.masks - b0, checked: BARE.RK_SCAN.checked, differ: BARE.RK_SCAN.differ },
    ship: { masks: SHIP.RK_SCAN.masks - s0, fallbacks: SHIP.RK_SCAN.fallbacks - sf0, checked: SHIP.RK_SCAN.checked, differ: SHIP.RK_SCAN.differ } };
  BARE.RK_SCAN.check = false; SHIP.RK_SCAN.check = false;
})();
// shapes with a known answer, and the cases the scan must hand back: holes, a vertex on a sample row, a sample on an edge
(function () {
  var ob = { cx: 0, cz: 0 }, ax = { ax: 1, az: 0, hl: 20, hs: 10 };
  var rect = [[-20, -10], [20, -10], [20, 10], [-20, 10]];
  var ell = [[-20, -10], [0, -10], [0, 0], [20, 0], [20, 10], [-20, 10]];
  var court = [[[-6, -4], [6, -4], [6, 4], [-6, 4]]];
  var same = function (a, b) { return a[0] === b[0] && a[1] === b[1]; };
  var f0 = SHIP.RK_SCAN.fallbacks;
  var R = SHIP.roofKitFast(ob, ax, rect, null), fRect = SHIP.RK_SCAN.fallbacks - f0;
  var L = SHIP.roofKitFast(ob, ax, ell, null);   // its inner corner's edges lie on a cell line, never on a sample row
  var f1 = SHIP.RK_SCAN.fallbacks;
  var C = SHIP.roofKitFast(ob, ax, rect, court), fCourt = SHIP.RK_SCAN.fallbacks - f1;
  var f2 = SHIP.RK_SCAN.fallbacks;
  var D = SHIP.roofKitFast(ob, ax, rect, [null, [[0, 0], [1, 1]]]), fDud = SHIP.RK_SCAN.fallbacks - f2;   // no real hole: scanned
  // a notch whose floor lies exactly on the first cell row's centre line (v = -hs + hs / 6): a vertex on a sample row
  var vrow = -10 + 10 / 6, notch = [[-20, -10], [-5, -10], [-5, vrow], [5, vrow], [5, -10], [20, -10], [20, 10], [-20, 10]];
  // a wall exactly on a sample column: u = -hl + 0.5 * (2 hl / 8) - 0.5 hl / 8, the first cell's low corner sample
  var ucol = -20 + 0.5 * (2 * 20 / 8) - 0.5 * 20 / 8, wall = [[ucol, -10], [20, -10], [20, 10], [ucol, 10]];
  var rot = function (p, t, dx, dz) { return p.map(function (q) { return [q[0] * Math.cos(t) - q[1] * Math.sin(t) + dx, q[0] * Math.sin(t) + q[1] * Math.cos(t) + dz]; }); };
  var turned = rot(ell, 0.1736, -5210.4, 3120.8), tob = SHIP.orientedBox(turned), tax = SHIP.obbAxis(tob);
  out.shapes = {
    rectFull: R[0] === 0xffffff && R[1] === 0xffffff, rectScanned: fRect === 0,
    ell: same(L, SHIP.roofKitMask(ob, ax, ell, null)), ellYard: SHIP.roofKitOn(L[0], L[1], 10, -5, 20, 10), ellRoof: SHIP.roofKitOn(L[0], L[1], -10, -5, 20, 10),
    court: same(C, SHIP.roofKitMask(ob, ax, rect, court)), courtFellBack: fCourt === 1, courtHole: SHIP.roofKitOn(C[0], C[1], 0, 0, 20, 10),
    dudHoleScanned: fDud === 0 && D[0] === 0xffffff && D[1] === 0xffffff,
    notchRefused: SHIP.roofKitScan(ob, ax, notch) === null, notch: same(SHIP.roofKitFast(ob, ax, notch, null), SHIP.roofKitMask(ob, ax, notch, null)),
    wallRefused: SHIP.roofKitScan(ob, ax, wall) === null, wall: same(SHIP.roofKitFast(ob, ax, wall, null), SHIP.roofKitMask(ob, ax, wall, null)),
    turned: same(SHIP.roofKitFast(tob, tax, turned, null), SHIP.roofKitMask(tob, tax, turned, null)),
    // more corners than the scratch arrays start with (64): they grow, and the answer holds
    many: (function () { var p = []; for (var i = 0; i < 300; i++) { var a = i / 300 * Math.PI * 2, r = 18 + (i %% 2) * 1.5; p.push([Math.cos(a) * r * 1.1, Math.sin(a) * r * 0.5]); } var o = SHIP.orientedBox(p), x = SHIP.obbAxis(o); return same(SHIP.roofKitFast(o, x, p, null), SHIP.roofKitMask(o, x, p, null)); })(),
  };
})();
emit(JSON.stringify(out));
'''

NODE_HEAD = "const readText = (p) => require('fs').readFileSync(p, 'latin1'); const emit = (s) => console.log(s);\n"
JSC_HEAD = 'var readText = readFile, emit = print;\n'   # the jsc shell's own globals

# JavaScriptCore here is the framework's own shell, not the suite's usual osascript: osascript runs the engine with its
# JIT off (twelve times slower on a plain loop, and this comparison took 315 s there against 29 s under Node), and the
# shell is the engine as a phone's web view runs it. macOS ships it inside the framework; it is on no PATH
JSC_SHELL = '/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc'


def jsc_shell():
    return shutil.which('jsc') or (JSC_SHELL if Path(JSC_SHELL).exists() else None)


def program(src):
    page = page_functions(src)
    # the same code with the margin at 0: the scan answers everywhere, right or wrong
    assert page.count('  const RK_EPS = 1e-7;\n') == 1
    bare = page.replace('  const RK_EPS = 1e-7;\n', '  const RK_EPS = 0;\n')
    files = [[name, str(ROOT / name), unit] for name, unit in BLOBS]
    return PROGRAM % {'page': page, 'bare': bare, 'files': json.dumps(files), 'split': core_split(src),
                      'sceneName': json.dumps(SCENE), 'scenePath': json.dumps(str(ROOT / SCENE))}


HAVE = {'node': bool(shutil.which('node')), 'jsc': bool(jsc_shell())}
_RUNS = {}


def run(engine):
    """Each engine runs the whole program once for the module, the two side by side (about 10 s on an idle machine)."""
    if not _RUNS:
        src, going = (ROOT / 'app.js').read_text(), []
        for eng in ('node', 'jsc'):
            if not HAVE[eng]:
                continue
            with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
                f.write((NODE_HEAD if eng == 'node' else JSC_HEAD) + program(src))
            cmd = ['node', f.name] if eng == 'node' else [jsc_shell(), f.name]
            going.append((eng, f.name, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)))
        for eng, name, proc in going:
            try:
                stdout, stderr = proc.communicate(timeout=900)
            except subprocess.TimeoutExpired:
                proc.kill(); stdout, stderr = proc.communicate(); stderr += '\ntimed out'
            Path(name).unlink(missing_ok=True)
            _RUNS[eng] = (proc.returncode, stdout, stderr)
    code, stdout, stderr = _RUNS[engine]
    if code != 0:
        raise AssertionError(engine + ' failed: ' + (stderr or stdout)[-1200:])
    return json.loads(stdout.strip().splitlines()[-1])


BLOBS_HERE = all((ROOT / name).exists() for name, _ in BLOBS) and (ROOT / SCENE).exists()


class EveryRecord(unittest.TestCase):
    """Both mask functions over every record of the three packed tiers and the core, on each engine this machine has."""

    def check(self, engine):
        out = run(engine)
        self.assertEqual(out['eps'], 1e-7)
        self.assertEqual(out['bareEps'], 0)
        # every tier is there in full: the counts the audit measured were 91,031, 176,978 and 49,493 (a repack moves them)
        for name, floor in (('wide.b64', 80000), ('city.b64', 150000), ('outskirts.b64', 40000)):
            t = out['tiers'][name]
            self.assertGreater(t['masks'], floor, name)
            self.assertEqual(t['differ'], 0, '%s: %d of %d masks differ under %s, the first %s' % (name, t['differ'], t['masks'], engine, json.dumps(out['firstDiff'])[:900]))
        # the core: scene.json's buildings with their holes, and the Liberty Bell Center's footprint as lbellSplit leaves it
        # (2,609 masks of 2,834 buildings when this was written, three of them courtyards, 0 differing and those three
        # the only fallbacks under Node and under JavaScriptCore)
        core = out['tiers'][SCENE]
        self.assertGreater(core['records'], 2000)
        self.assertGreater(core['masks'], 2000, 'the core is there in full')
        self.assertEqual(core['differ'], 0, '%s: %d of %d masks differ under %s, the first %s' % (SCENE, core['differ'], core['masks'], engine, json.dumps(out['firstDiff'])[:900]))
        self.assertTrue(core['split'], 'lbellSplit cut the Liberty Bell Center and what it left went through too')
        self.assertGreater(core['holed'], 0, 'the real courtyards are in the core, and they went through')
        self.assertGreaterEqual(core['fallbacks'], core['holed'], 'a roof with a hole is roofKitMask\'s')
        self.assertEqual(out['holed'], core['holed'], 'no packed tier carries a hole')
        self.assertGreater(out['masks'], 300000)
        self.assertEqual(out['differ'], 0)
        self.assertEqual(out['counted'], out['masks'], 'RK_SCAN counts every mask asked for')
        # the fallback is a few roofs in a hundred, and it is needed: with no margin the scan gets some wrong, which also
        # shows this comparison can see a wrong mask
        self.assertGreater(out['fallbacks'], 0)
        self.assertLess(out['fallbacks'], 0.06 * out['masks'], 'the scan answers nearly every roof itself')
        self.assertEqual(out['bareFallbacks'], out['holed'], 'with no margin only a hole falls back')
        self.assertGreater(out['bareDiffer'], 0, 'with the margin at 0 some masks differ: the fallback earns its place')
        # and it is the cheaper way round. Measured at a fifth to a third of the old time, but this is the deploy's gate
        # and a clock on a busy machine is not: a separate run under load average 39 once read 2.1 times, so the floor
        # is only that it is no dearer. How much it saves is the beacons' to say (rk)
        self.assertLess(out['msNew'], out['msOld'], {k: out[k] for k in ('msOld', 'msNew')})
        return out

    @unittest.skipUnless(HAVE['node'], 'node is not installed (JavaScriptCore runs the same program)')
    def test_node(self):
        self.check('node')

    @unittest.skipUnless(HAVE['jsc'], 'the jsc shell is not here (Node runs the same program)')
    def test_javascriptcore(self):
        self.check('jsc')

    def test_an_engine_ran_it(self):
        # no engine is a failure while the data is here: this is the gate on the masks, and a skip would let a deploy by
        if BLOBS_HERE:
            self.assertTrue(HAVE['node'] or HAVE['jsc'], 'neither node nor the jsc shell: the roof masks were not checked against roofKitMask')

    def check_self(self, engine):
        sc = run(engine)['selfCheck']
        tier = run(engine)['tiers']['outskirts.b64']
        # the margin-free copy: every roof scanned, every one checked, and the page's own count is the direct count
        self.assertEqual(sc['bare']['checked'], sc['bare']['masks'])
        self.assertEqual(sc['bare']['masks'], tier['masks'])
        self.assertEqual(sc['bare']['differ'], tier['bareDiffer'])
        # the shipped copy: checked wherever it did not fall back, and nothing differs
        self.assertEqual(sc['ship']['checked'], sc['ship']['masks'] - sc['ship']['fallbacks'])
        self.assertEqual(sc['ship']['fallbacks'], tier['fallbacks'])
        self.assertEqual(sc['ship']['differ'], 0)

    @unittest.skipUnless(HAVE['node'], 'node is not installed')
    def test_the_dev_self_check_counts_what_differs_node(self):
        self.check_self('node')

    @unittest.skipUnless(HAVE['jsc'], 'the jsc shell is not here')
    def test_the_dev_self_check_counts_what_differs_javascriptcore(self):
        self.check_self('jsc')

    def check_shapes(self, engine):
        sh = run(engine)['shapes']
        self.assertTrue(sh['rectFull'], 'a rectangle is all roof'); self.assertTrue(sh['rectScanned'], 'and the scan answers it')
        self.assertTrue(sh['ell']); self.assertTrue(sh['ellRoof']); self.assertFalse(sh['ellYard'], 'no unit over the yard beside the ell')
        self.assertTrue(sh['court']); self.assertTrue(sh['courtFellBack'], 'a roof with a hole goes to roofKitMask'); self.assertFalse(sh['courtHole'])
        self.assertTrue(sh['dudHoleScanned'], 'a hole roofKitMask would ignore (null, or two points) is no reason to fall back')
        self.assertTrue(sh['notchRefused'], 'a vertex on a sample row: the scan does not answer'); self.assertTrue(sh['notch'])
        self.assertTrue(sh['wallRefused'], 'a sample on an edge: the scan does not answer'); self.assertTrue(sh['wall'])
        self.assertTrue(sh['turned']); self.assertTrue(sh['many'])

    @unittest.skipUnless(HAVE['node'], 'node is not installed')
    def test_shapes_node(self):
        self.check_shapes('node')

    @unittest.skipUnless(HAVE['jsc'], 'the jsc shell is not here')
    def test_shapes_javascriptcore(self):
        self.check_shapes('jsc')


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_the_note_takes_the_scan_and_the_old_function_stays_whole(self):
        s = self.s
        raw = cut(s, '  function roofKitNoteRaw(', "  // a point in the lay's frame")
        self.assertIn('const [lo, hi] = poly ? roofKitFast(ob, ax, poly, holes) : [0xffffff, 0xffffff];', raw)
        self.assertNotIn('roofKitMask(', raw)
        # roofKitMask is the fallback and the reference: its text is what it was (tests/test_roof_kit.py runs it alone)
        mask = cut(s, '  function roofKitMask(ob, ax, poly, holes) {', '\n  }\n')
        self.assertIn('const cu = -hl + (a + 0.5) * (2 * hl / RK_NU), cv = -hs + (b + 0.5) * (2 * hs / RK_NV);', mask)
        self.assertIn('const du = 0.5 * hl / RK_NU, dv = 0.5 * hs / RK_NV;', mask)
        self.assertIn('if (on(cu, cv) && on(cu - du, cv - dv) && on(cu + du, cv - dv) && on(cu + du, cv + dv) && on(cu - du, cv + dv)) {', mask)
        self.assertEqual(mask.count('pointInPoly('), 2)
        # the scan samples at the page's own expressions, so the samples are the same numbers
        scan = cut(s, '  function roofKitScan(ob, ax, poly) {', '  function roofKitFast(')
        self.assertIn('const du = 0.5 * hl / RK_NU, dv = 0.5 * hs / RK_NV;', scan)
        self.assertIn('const cv = -hs + (b + 0.5) * (2 * hs / RK_NV);', scan)
        self.assertIn('const cu = -hl + (a + 0.5) * (2 * hl / RK_NU);', scan)
        self.assertIn('const v = r === 0 ? cv : r === 1 ? cv - dv : cv + dv;', scan)
        self.assertIn('if (r === 0) q = roofKitRowAt(cu, m);\n          else { q = roofKitRowAt(cu - du, m); if (q === 1) q = roofKitRowAt(cu + du, m); }', scan)
        self.assertIn('  const RK_EPS = 1e-7;\n', s)
        self.assertNotIn('pointInPoly', scan)
        # the fallbacks: holes, and anything the scan refuses
        fast = cut(s, '  function roofKitFast(ob, ax, poly, holes) {', '  function roofKitNote(')
        self.assertIn('if (!(holes && holes.some((hr) => hr && hr.length > 2))) m = roofKitScan(ob, ax, poly);', fast)
        self.assertIn('if (!m) { RK_SCAN.fallbacks++; return roofKitMask(ob, ax, poly, holes); }', fast)

    def test_the_dev_self_check(self):
        s = self.s
        fast = cut(s, '  function roofKitFast(ob, ax, poly, holes) {', '  function roofKitNote(')
        self.assertIn('if (RK_SCAN.check) { const r = roofKitMask(ob, ax, poly, holes); RK_SCAN.checked++; if (r[0] !== m[0] || r[1] !== m[1]) RK_SCAN.differ++; }', fast)
        self.assertIn('  const RK_SCAN = { masks: 0, fallbacks: 0, checked: 0, differ: 0, check: false };\n', s)
        # switched on by ?dev where PERF is, never inside the span that runs under Node with no PERF and no location
        # ?rkcheck=0 turns it off under ?dev: the check runs the old mask on every scanned roof, so a ?dev load's rk is dearer
        # than before the scan and a timing run (the capture skill's default query is dev=1) must be able to leave it out
        reg = '  PERF.roofKitMask = RK_SCAN; RK_SCAN.check = /[?&]dev\\b/.test(location.search) && !/[?&]rkcheck=0\\b/.test(location.search);'
        self.assertIn(reg, s)
        self.assertLess(s.index('  PERF.roofKitNote = RK_STAT;'), s.index(reg))
        self.assertLess(s.index(reg), s.index('  const STEP_EXTRA = {'))
        span = re.sub(r'//.*', '', cut(s, '  function insetRing(', '  function roofClutter('))
        for word in ('PERF', 'location', 'TIER', 'isTouch', 'ROOF_KIT_ON', 'performance.now() - t0'):
            self.assertNotIn(word, span, word)
        # the probe carries it: __dbg.roofKit().mask and __dbg.PERF.roofKitMask; and a difference is a console error, which
        # the capture skill's render.mjs prints
        self.assertIn('hist: Array.from(ROOF_KIT.hist), mask: RK_SCAN };', s)
        self.assertIn("    if (RK_SCAN.differ) console.error('roof kit: ' + RK_SCAN.differ + ' of ' + RK_SCAN.checked + ' scanned masks differ from roofKitMask');", s)

    @unittest.skipUnless(HAVE['node'], 'node is not installed')
    def test_the_check_is_on_under_dev_and_off_at_rkcheck_0(self):
        # the page's own expression, against the queries a load can carry
        expr = cut(self.s, 'RK_SCAN.check = /[?&]dev', ';   // Round 225')[len('RK_SCAN.check = '):]
        qs = ['', '?dev=1', '?dev=1&dpr=1', '?dpr=1&dev', '?dev=1&rkcheck=0', '?rkcheck=0&dev=1', '?rkcheck=0', '?dev=1&rkcheck=1', '?device=1']
        js = 'const f = (q) => { const location = { search: q }; return %s; };\nconsole.log(JSON.stringify(%s.map(f)));' % (expr, json.dumps(qs))
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertEqual(json.loads(r.stdout), [False, True, True, True, False, False, False, True, False])

    def test_no_timer_in_the_masks(self):
        # Round 220's rule: the per-record functions time nothing
        code = cut(self.s, '  function roofKitMask(ob, ax, poly, holes) {', '  function roofKitNote(')
        self.assertNotIn('performance.now', code)
        self.assertNotIn('Date.now', code)

    def test_one_flag_for_the_step_and_the_note(self):
        s = self.s
        self.assertEqual(s.count('const ROOF_KIT_ON = '), 1)
        self.assertIn('  const ROOF_KIT_ON = !TIER2;\n', s)
        # declared with the tiers, before the span the Node tests cut and outside it
        self.assertLess(s.index('const LITE = TIER >= 1, TIER2 = TIER >= 2;'), s.index('  const ROOF_KIT_ON = !TIER2;'))
        self.assertLess(s.index('  const ROOF_KIT_ON = !TIER2;'), s.index('  function insetRing('))
        # the step drops the notes on the flag, and nowhere on the tier by name
        step = cut(s, "  step('Fitting out the rooftops',", '    const B = ROOF_KIT.buf')
        self.assertIn('if (!ROOF_KIT_ON) { ROOF_KIT.buf = null; ROOF_KIT.n = 0; return; }', step)
        self.assertNotIn('TIER', re.sub(r'//.*', '', step))
        body = cut(s, '  function roofClutter(', '  // ---- pitched roofs for the packed tiers')
        self.assertNotIn('TIER', re.sub(r'//.*', '', body))
        # roofClutter: no note where none is read; with the flag on, the head is what it was
        head = body[:body.index('    // the baked boxes below stand only where')]
        self.assertIn('    if (h < 3) return;\n    if (!ROOF_KIT_ON && isTouch) return;', head)
        self.assertIn('\n    const ob = orientedBox(poly), ax = obbAxis(ob);\n    if (ax.hs < 2.2) return;\n    if (ROOF_KIT_ON) roofKitNote(ob, ax, base + h, area, seed, poly, holes, ', head)
        self.assertEqual(body.count('roofKitNote('), 1)
        # the note still comes before the touch return (a phone at tiers 0 and 1 takes every note), and a computer
        # forced to tier 2 still bakes its boxes: only a phone returns at the head
        self.assertLess(body.index('roofKitNote(ob, ax, base + h, area, seed, poly, holes, '), body.index('if (isTouch || h < 5) return;'))
        self.assertLess(body.index('if (!ROOF_KIT_ON && isTouch) return;'), body.index('orientedBox(poly)'))
        # the only readers of the notes are that step and the lay it sets up
        self.assertEqual(len(re.findall(r'\bROOF_KIT\.buf\b', s[s.index("  step('Fitting out the rooftops',"):])), 3)


CLUTTER = r'''
const calls = { box: 0 };
function hash01(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
const ST_COPING = 3, REAL = true;
%(page)s
const orientedBox0 = orientedBox;
orientedBox = function (poly) { calls.box++; return orientedBox0(poly); };
%(clutter)s
const wall = { clone() { return this; }, multiplyScalar() { return this; }, getHex() { return 0x808080; } };
// an office roof, 40 by 24 m and 20 m up (a parapet lip, rooftop boxes and a stair bulkhead on a computer), and a rowhouse
const office = [[100, 200], [140, 200], [140, 224], [100, 224]], house = [[0, 0], [5, 0], [5, 14], [0, 14]];
const added = [];
const add = (pg, y0, y1, hex, st, holes) => added.push([pg, y0, y1, hex, st, holes ? holes.length : 0]);
roofClutter(add, office, 3, 20, 960, 3, [1, 0, 2, 0], 7, wall, false);
roofClutter(add, house, 3, 9, 70, 1, [0, 0, 0, 0], 11, wall, false);
roofClutter(add, house, 3, 2, 70, 1, [0, 0, 0, 0], 12, wall, false);   // under 3 m: nothing, as ever
console.log(JSON.stringify({ notes: ROOF_KIT.n, calls: RK_STAT.calls, masks: RK_SCAN.masks, boxes: calls.box, added,
  note0: Array.from(ROOF_KIT.buf.subarray(0, ROOF_KIT.n ? ROOF_KIT_STRIDE : 0)), rows: ROOF_KIT.n > 1 ? [ROOF_KIT.buf[10], ROOF_KIT.buf[ROOF_KIT_STRIDE + 10]] : [] }));
'''


@unittest.skipUnless(HAVE['node'], 'node is not installed')
class TheFlagInRoofClutter(unittest.TestCase):
    """roofClutter itself, from the page, with the flag and the device each way."""

    @classmethod
    def setUpClass(cls):
        src = (ROOT / 'app.js').read_text()
        page = page_functions(src).replace('  function orientedBox(poly) {', '  let orientedBox = function (poly) {', 1)
        cls.body = CLUTTER % {'page': page, 'clutter': cut(src, '  function roofClutter(', '  // ---- pitched roofs for the packed tiers')}

    def run_js(self, on, touch):
        js = 'const ROOF_KIT_ON = %s, isTouch = %s;\n' % ('true' if on else 'false', 'true' if touch else 'false') + self.body
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1200:])
        return json.loads(r.stdout)

    def test_each_way(self):
        on_pc, on_phone = self.run_js(True, False), self.run_js(True, True)
        off_pc, off_phone = self.run_js(False, False), self.run_js(False, True)
        # the flag on: both roofs noted on either device (the note comes before the touch return), boxes on a computer only
        for o in (on_pc, on_phone):
            self.assertEqual(o['notes'], 2); self.assertEqual(o['calls'], 2); self.assertEqual(o['masks'], 2); self.assertEqual(o['boxes'], 2)
            self.assertEqual(o['rows'], [0, 1], 'the office is no row of houses, the house is')
            self.assertEqual(o['note0'][:3], [120, 212, 23]); self.assertEqual(o['note0'][5:7], [20, 12])
            self.assertEqual(o['note0'][8:10], [0xffffff, 0xffffff], 'a rectangle is all roof')
        self.assertEqual(on_pc['note0'], on_phone['note0'])
        self.assertEqual(on_phone['added'], [])
        self.assertGreaterEqual(len(on_pc['added']), 3, 'the lip, a rooftop box and the bulkhead at least')
        # the flag off on a computer (?lite=2): no note, no mask, and the baked boxes exactly as they were
        self.assertEqual(off_pc['notes'], 0); self.assertEqual(off_pc['calls'], 0); self.assertEqual(off_pc['masks'], 0)
        self.assertEqual(off_pc['boxes'], 2)
        self.assertEqual(off_pc['added'], on_pc['added'])
        # the flag off on a phone (tier 2): nothing at all, not the oriented box either
        self.assertEqual(off_phone, {'notes': 0, 'calls': 0, 'masks': 0, 'boxes': 0, 'added': [], 'note0': [], 'rows': []})


if __name__ == '__main__':
    unittest.main()
