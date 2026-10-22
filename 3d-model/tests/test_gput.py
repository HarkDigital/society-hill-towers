"""Round 220, the measurement round: the GPU pass timer on in every desktop session, sampled, every pass labelled, the frame id
stamped at the top of frame(), the pins' synchronous reads counted, and gputBeacon's fields for the perf beacons.

The timer block (cut from app.js) runs under Node against a fake WebGL 2 context whose queries land two polls after they are
ended: the sampled schedule over 900 frames (exactly 90, 30 in every 300), a pass drawn before the scene landing in its own
frame's total, the window's last frame committed without waiting for the next window, no GL call while nothing is in flight,
Enter re-basing the means and the counters, the beacon's text, and the escapes (?gput=0, a phone, a disjoint clock)."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(src, start, end, inclusive=False):
    i = src.index(start)
    j = src.index(end, i)
    return src[i:j + (len(end) if inclusive else 0)]


BLOCK_START = '  const GPUT_ON = 30, GPUT_EVERY = 300;'
BLOCK_END = "  // the CPU's side of each shadow pass too"
HARNESS = r"""
const BLOCK = BLOCK_JSON;
const mk = new Function('POST', 'isTouch', 'location', 'renderer', 'DPR', 'PERF', 'PIN_OCC', 'REFL', 'CARMAP', 'LAMPMAP', 'LAMPNEAR',
  BLOCK + '\nreturn { GPUT, GPUT_ON, GPUT_EVERY, gpuSampled, gpuT, gpuNow, gpuRecord, gpuCommit, gpuFrame, gpuPoll, gpuStats, gputEnter, gputBeacon };');
// a fake WebGL 2 context: one timer open at a time, a query's result available two polls after it was ended, its time the
// ms the test set before the query began; the polls (GPU_DISJOINT_EXT reads) are counted
let tick = 0, nextMs = 1;
const EXT = { TIME_ELAPSED_EXT: 1, GPU_DISJOINT_EXT: 2 };
const gl = { QUERY_RESULT_AVAILABLE: 3, QUERY_RESULT: 4, made: 0, deleted: 0, open: null, disjoint: false, polls: 0,
  getExtension: (n) => (n === 'EXT_disjoint_timer_query_webgl2' ? EXT : null),
  createQuery: () => { gl.made++; return { ms: 0, ended: -1 }; },
  beginQuery: (t, q) => { if (t !== 1) throw new Error('target ' + t); if (gl.open) throw new Error('two timers at once'); gl.open = q; q.ms = nextMs; q.ended = -1; },
  endQuery: (t) => { if (!gl.open) throw new Error('no timer open'); gl.open.ended = tick; gl.open = null; },
  deleteQuery: () => { gl.deleted++; },
  getParameter: (p) => { if (p === 2) { gl.polls++; return gl.disjoint; } return null; },
  getQueryParameter: (q, p) => (p === 3 ? q.ended >= 0 && tick - q.ended >= 2 : q.ms * 1e6) };
const renderer = { getContext: () => gl };
const counters = () => ({ PIN_OCC: { renders: 0, rendersNear: 0 }, REFL: { n: 0, ms: 0 }, CARMAP: { renders: 0 }, LAMPMAP: { renders: 0 }, LAMPNEAR: { renders: 0 } });
const load = (o) => { const C = counters(), DPR = { live: false }, PERF = {};
  const S = mk({ on: o.post !== false }, !!o.touch, { search: o.search || '' }, renderer, DPR, PERF, C.PIN_OCC, C.REFL, C.CARMAP, C.LAMPMAP, C.LAMPNEAR);
  S.C = C; S.DPR = DPR; S.PERF = PERF; return S; };
// a frame as frame() and renderPost run it: the stamp at the top, a pass before the scene (the pins' capture), the poll at the
// start of renderPost, then the scene's query, ended as renderPost ends
const frame = (S, pre, sc) => { tick++; S.gpuFrame(); nextMs = pre; S.gpuT('pins'); S.gpuT(null); S.gpuPoll(); nextMs = sc; S.gpuT('scene'); S.gpuT(null); };
const out = {};
BODY
console.log(JSON.stringify(out));
"""


def run_node(tc, script):
    if not shutil.which('node'):
        tc.skipTest('Node.js unavailable')
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
    tc.assertEqual(r.returncode, 0, r.stderr)
    return json.loads(r.stdout)


class Gput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        cls.block = cut(cls.s, BLOCK_START, BLOCK_END)

    def node(self, body):
        return run_node(self, HARNESS.replace('BLOCK_JSON', json.dumps(self.block), 1).replace('BODY', body, 1))

    # ---- the text
    def test_on_by_default_on_a_desktop_sampled_with_the_escape(self):
        s = self.s
        self.assertIn("GPUT.ext = POST.on && !isTouch && !/[?&]gput=0\\b/.test(location.search) ? renderer.getContext().getExtension('EXT_disjoint_timer_query_webgl2') : null;", s)
        self.assertIn('const GPUT_ON = 30, GPUT_EVERY = 300;', s)
        self.assertIn('const gpuSampled = (fid, dev) => !!dev || fid % GPUT_EVERY < GPUT_ON;', s)
        self.assertIn("dev: /[?&]dev\\b/.test(location.search), live: false,", s)
        self.assertIn('GPUT.live = gpuSampled(GPUT.fid, GPUT.dev);', s)
        self.assertIn("if (!label || !GPUT.live) return;", s)
        self.assertIn('if (!GPUT.on || !GPUT.pend.length) return;', s)   # bounded: nothing in flight, no GL call
        self.assertIn('if (!GPUT.pend.length && GPUT.accF >= 0 && GPUT.accF !== GPUT.fid) { gpuCommit(); GPUT.accF = -1; }', s)
        for bad in ('—', '–', '·'):
            self.assertNotIn(bad, self.block)

    def test_every_pass_is_labelled(self):
        s = self.s
        post = cut(s, '  function renderPost(sc, cam) {', '\n  }\n')
        for lab in ('scene', 'ao', 'bloom', 'comp'):
            self.assertIn("gpuT('" + lab + "')", post)
        self.assertIn("    postSize();\n    gpuPoll();", post)
        self.assertIn("const prev = gpuNow(), lab = FARSH.pending ? 'shadowFar' : 'shadow', c0 = renderer.info.render.calls, t0 = performance.now();\n      if (FARSH.pending) GPUT.sfd++; else GPUT.sdn++;", s)
        refl = cut(s, '  function reflRender(sc, cam) {', '\n  }\n')
        self.assertIn("const gprev = gpuNow(); gpuT('mirror');", refl)
        self.assertIn("r.render(sc, C);\n      gpuT(gprev);", refl)
        car = cut(s, '  function carMapUpdate() {', '\n  }\n')
        self.assertIn("const gprev = gpuNow(); gpuT('carmap');", car)
        self.assertIn('r.render(CARMAP.scene, CARMAP.cam); r.autoClear = prevAuto;\n    gpuT(gprev);', car)
        far = cut(s, '  function lampMapUpdate() {', '\n  }\n')
        self.assertIn("const gprev = gpuNow(); gpuT('lampfar');", far)
        self.assertIn('r.render(LAMPMAP.scene, LAMPMAP.cam); r.autoClear = prevAuto;\n    gpuT(gprev);', far)
        near = cut(s, '  function lampNearUpdate() {', '\n  }\n')
        self.assertIn("const gprev = gpuNow(); gpuT('lampnear');", near)
        self.assertIn('r.render(LAMPMAP.scene, N.cam); r.autoClear = prevAuto;\n    gpuT(gprev);', near)
        env = cut(s, '  function cityEnvBake(only) {', '\n  }\n')
        # the probe's bake is wrapped from outside: its own text is the glass calibration's fingerprint (glass_calibrate.py) and the
        # tick's call is pinned by tests/test_glass_towers.py
        self.assertNotIn('gpuT(', env)
        self.assertIn("{ const bake0 = cityEnvBake; cityEnvBake = function (only) { const gprev = gpuNow(); gpuT('cityenv'); try { bake0(only); } finally { gpuT(gprev); } }; }", s)
        self.assertIn('else if (CITYENV.pending && performance.now() - CITYENV.at >= CITYENV_GAP) cityEnvBake(0);', cut(s, '  function cityEnvTick() {', '\n  }\n'))
        # the pins' capture is timed inside occRender, by its buffer: the pins' block runs under Node without the timer (tests/test_cull.py)
        self.assertNotIn('gpuT(', cut(s, '  const PIN_OCC_MOVE_EVERY = ', '  function pinOccMat() {'))
        occ = cut(s, '  function occRender(rt, W, H, buf, noInstanced, cam = camera, read = null, noFlats = false) {', '\n  }\n')
        self.assertIn("const pinLab = buf === PIN_OCC.full.cpu.buf ? 'pins' : buf === PIN_OCC.near.cpu.buf ? 'pinsnear' : null, gprev = pinLab ? gpuNow() : null;", occ)
        self.assertIn('if (pinLab) gpuT(pinLab);\n    try { r.render(scene, cam); } finally { if (noFlats) for (const m of OCC_ONLY) m.visible = false; }\n    if (pinLab) gpuT(gprev);', occ)

    def test_the_frame_id_is_stamped_at_the_top_of_frame(self):
        s = self.s
        f = cut(s, '  function frame(now, once) {', '\n  setHint();')
        self.assertIn('    frameNo++;\n    gpuFrame();', f)
        self.assertEqual(s.count('GPUT.fid++'), 1)
        self.assertIn('  function gpuFrame() {\n    if (!GPUT.on) return;\n    GPUT.fid++;', s)
        self.assertNotIn('GPUT.fid++', cut(s, '  function gpuPoll() {', '\n  }\n'))
        self.assertIn('if (!GPUT.entered && DPR.live) gputEnter();', s)
        # the first frame frame() draws, once, for the enter beacon (another piece carries it)
        self.assertIn('if (PERF.frame1Ms === undefined) PERF.frame1Ms = Math.round(performance.now() - tFrame);', f)
        self.assertEqual(f.count('PERF.frame1Ms'), 2)

    def test_the_pins_synchronous_reads_are_counted(self):
        s = self.s
        self.assertIn('syncN: 0, syncMs: 0, landN: 0, landMs: 0,', cut(s, '  const PIN_OCC = {', '\n  const pinDepthClear'))
        occ = cut(s, '  function occRender(rt, W, H, buf, noInstanced, cam = camera, read = null, noFlats = false) {', '\n  }\n')
        # test_cull.py pins the read's line whole: the timing sits round it, the pins' buffers alone counted
        self.assertIn('const t0 = performance.now();\n    if (read) out = read(); else r.readRenderTargetPixels(rt, 0, 0, W, H, buf);\n    if (pinLab && !read) { PIN_OCC.syncN++; PIN_OCC.syncMs += performance.now() - t0; }', occ)
        issue = cut(s, '  function pinOccIssue(s, dst) {', '\n  }\n')
        self.assertIn('PIN_OCC.syncN++; PIN_OCC.syncMs += performance.now() - t0;\n      return false;', issue)
        poll = cut(s, '  function pinOccPoll() {', '\n  }\n')
        self.assertIn('try { gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, 0, ch.cpu.buf); } finally { gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null); }\n      const tl = performance.now() - t0;\n      PIN_OCC.syncN++; PIN_OCC.syncMs += tl; PIN_OCC.landN++; PIN_OCC.landMs += tl;', poll)

    def test_the_beacon_fields(self):
        s = self.s
        b = cut(s, '  function gputBeacon() {', '\n  }\n')
        self.assertIn('if (!GPUT.on) return {};', b)
        self.assertIn("gt.push(k + ':' + (m.sum / m.cnt).toFixed(1));", b)
        self.assertIn("return { gt: gt.join(','), gtn: GPUT.ms.total ? GPUT.ms.total.cnt : 0, pr: PIN_OCC.renders - B.pr, prn: PIN_OCC.rendersNear - B.prn, rf: REFL.n - B.rf, rfm: Math.round(REFL.ms),", b)
        self.assertIn('cm: CARMAP.renders - B.cm, sdn: GPUT.sdn - B.sdn, sfd: GPUT.sfd - B.sfd, ln: LAMPNEAR.renders - B.ln, lf: LAMPMAP.renders - B.lf };', b)
        self.assertIn('PERF.gput = gputBeacon; PERF.gputState = GPUT;', s)
        self.assertIn('const GPUT_CPU_LAB = /Cpu$|Calls$/;', s)

    # ---- the block under Node
    def test_the_schedule_samples_90_of_900_frames(self):
        o = self.node(r"""
const S = load({});
out.on = S.GPUT.on; out.dev = S.GPUT.dev;
let n = 0; const runs = []; let run = 0; const per = [0, 0, 0];
for (let f = 1; f <= 900; f++) { const s = S.gpuSampled(f, false); if (s) { n++; run++; per[Math.floor((f - 1) / 300)]++; } else if (run) { runs.push(run); run = 0; } }
if (run) runs.push(run);
out.n = n; out.per = per; out.longest = Math.max(...runs); out.devAll = [1, 2, 31, 299, 300].every((f) => S.gpuSampled(f, true));
""")
        self.assertTrue(o['on'])
        self.assertFalse(o['dev'])
        self.assertEqual(o['n'], 90)
        self.assertEqual(o['per'], [30, 30, 30])
        self.assertEqual(o['longest'], 30)
        self.assertTrue(o['devAll'])

    def test_a_pass_before_the_scene_lands_in_its_own_frame(self):
        o = self.node(r"""
const S = load({}), G = S.GPUT;
for (let f = 1; f <= 40; f++) frame(S, 3, 10);   // frames 1 to 29 sampled, then the window closes and the last queries land
const T = G.ms.total;
out.frames = T.cnt; out.pins = G.ms.pins.cnt; out.scene = G.ms.scene.cnt; out.ring = T.ring.slice(); out.sampled = G.sampled;
out.open = gl.open; out.pend = G.pend.length; out.made = gl.made; out.freed = G.free.length;
const p0 = gl.polls;
for (let f = 41; f <= 299; f++) frame(S, 3, 10);
out.idlePolls = gl.polls - p0; out.madeIdle = gl.made - out.made;
""")
        self.assertEqual(o['sampled'], 29)
        self.assertEqual(o['frames'], 29)   # the window's last frame committed without waiting for the next window
        self.assertEqual(o['pins'], 29)
        self.assertEqual(o['scene'], 29)
        self.assertTrue(all(v == 13 for v in o['ring']), o['ring'])   # pins 3 + scene 10 in every frame: never the frame before's
        self.assertIsNone(o['open'])
        self.assertEqual(o['pend'], 0)
        self.assertEqual(o['freed'], o['made'])   # every query read serves again
        self.assertEqual(o['idlePolls'], 0)   # nothing in flight: no GL call for 259 frames
        self.assertEqual(o['madeIdle'], 0)

    def test_enter_rebases_the_means_and_the_counters(self):
        o = self.node(r"""
const S = load({}), G = S.GPUT, C = S.C;
for (let f = 1; f <= 299; f++) frame(S, 3, 10);
C.PIN_OCC.renders = 5; C.PIN_OCC.rendersNear = 1; C.REFL.n = 4; C.REFL.ms = 2.6; C.CARMAP.renders = 7; C.LAMPNEAR.renders = 2; C.LAMPMAP.renders = 1; G.sdn = 4; G.sfd = 2;
out.before = S.gputBeacon();
S.DPR.live = true;   // Enter
for (let f = 300; f <= 340; f++) frame(S, 1, 5);   // the next window, sampled at 300 to 329
C.PIN_OCC.renders = 9; C.PIN_OCC.rendersNear = 2; C.REFL.n = 10; C.CARMAP.renders = 8; C.LAMPNEAR.renders = 5; C.LAMPMAP.renders = 3; G.sdn = 9; G.sfd = 3;
out.after = S.gputBeacon(); out.entered = G.entered; out.base = Object.assign({}, G.base);
out.viaPerf = S.PERF.gput === S.gputBeacon && S.PERF.gputState === G;
out.stats = S.gpuStats().total.n;
""")
        self.assertEqual(o['before']['gtn'], 29)
        self.assertEqual(o['before']['gt'], 'pins:3.0,scene:10.0,total:13.0')
        self.assertEqual(o['before']['pr'], 5)
        self.assertTrue(o['entered'])
        self.assertEqual(o['base'], {'pr': 5, 'prn': 1, 'rf': 4, 'cm': 7, 'sdn': 4, 'sfd': 2, 'ln': 2, 'lf': 1})
        a = o['after']
        self.assertEqual(a['gtn'], 30)
        self.assertEqual(a['gt'], 'pins:1.0,scene:5.0,total:6.0')   # the means since Enter alone
        self.assertEqual({k: a[k] for k in ('pr', 'prn', 'rf', 'rfm', 'cm', 'sdn', 'sfd', 'ln', 'lf')}, {'pr': 4, 'prn': 1, 'rf': 6, 'rfm': 3, 'cm': 1, 'sdn': 5, 'sfd': 1, 'ln': 3, 'lf': 2})
        self.assertTrue(o['viaPerf'])
        self.assertEqual(o['stats'], 59)   # __dbg.gpu() keeps every frame

    def test_the_escapes(self):
        o = self.node(r"""
const off = load({ search: '?gput=0' }), phone = load({ touch: true }), noPost = load({ post: false }), dev = load({ search: '?dev=1' });
out.off = off.GPUT.on; out.phone = phone.GPUT.on; out.noPost = noPost.GPUT.on; out.offBeacon = off.gputBeacon();
off.gpuFrame(); out.offFid = off.GPUT.fid;
out.dev = dev.GPUT.dev;
for (let f = 1; f <= 50; f++) frame(dev, 2, 4);
out.devSampled = dev.GPUT.sampled;
// a disjoint clock: what was in flight is dropped, nothing of it recorded
const S = load({});
frame(S, 3, 10); frame(S, 3, 10);
tick += 2;   // a result is there to consume: the disjoint flag is read only then (the review: each read is a round trip)
gl.disjoint = true; S.gpuPoll(); gl.disjoint = false;
out.dropped = S.GPUT.pend.length; out.acc = Object.keys(S.GPUT.acc).length;
""")
        self.assertFalse(o['off'])
        self.assertFalse(o['phone'])
        self.assertFalse(o['noPost'])
        self.assertEqual(o['offBeacon'], {})
        self.assertEqual(o['offFid'], 0)
        self.assertTrue(o['dev'])
        self.assertEqual(o['devSampled'], 50)   # continuous under ?dev
        self.assertEqual(o['dropped'], 0)
        self.assertEqual(o['acc'], 0)


if __name__ == '__main__':
    unittest.main()
