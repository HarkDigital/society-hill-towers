"""Round 229, measurement round two (Stage 1 of the Nov 10 plan): the timers and beacon fields that decide the later stages.

Fields and timers only: nothing drawn changes and no shader text is touched. The block is cut from app.js and run under
Node against a scripted WebGL context whose calls advance a scripted clock, so every figure is checked to the millisecond:

- the link timers: a program's two compiles, its link and its first status query are timed apart, then its introspection
  and the texture calls; the wraps are INSTANCE wraps, call straight through, count their own faults and come off whole
  (the prototype's method shows through again); the cold verdict is the median's, over ten programs, so one slow first
  query after a batch of uploads does not make a load cold; only a cold load drains, once before each program's first
  shaderSource; a warm load's wraps come off at Ready and a cold load's after the one frame behind the unlit button;
- a program's tag is its material type and custom key, never the type alone, in letters, digits and dashes;
- the fences behind the flushes: never read in the task that made them, two bounds for one seen unsignalled; laid only
  on a computer in Chromium, the call timed, and never again in a load once one call has waited (the review: WebKit's
  fenceSync blocks until the GPU process has caught up, 0.3 to 2.7 s a load);
- the frame's counters: stalls only after Enter and never across time hidden, the gap after a pin landing paired with
  the frame before, the eye's height bands;
- the crumb every second after Ready: the same 'ready' step, inside the next load's pc cut, stopped by the clock before
  the running crumb takes over and for good when the page is left, and never written from a tab that is not in front;
- the geometry's bytes by family: noted before an upload frees the array, a shared buffer once;
- measFacts by checkpoint, its characters (a query escapes none of them), no URL, and the longest beacon's length;
- the wiring: where each call sits, a computer's lost context beaconed, the capture skill's beacons.py reading it all.
"""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import re
import sys
import tempfile
import unittest
import urllib.parse

try:
    from .test_recovery import run_node, cut          # python3 -m unittest tests.test_measure_two
except ImportError:
    from test_recovery import run_node, cut           # python3 -m unittest discover -s tests

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
BLOCK = cut(SRC, '  // ---- Round 229, measurement round two (Stage 1 of the Nov 10 plan', '  // ---- reversed-Z depth (Round 192, from perf spike 1)')
BEACONS_PY = ROOT.parent / '.claude' / 'skills' / 'philly3d-capture' / 'scripts' / 'beacons.py'
BAD = ('—', '–', '·')   # no em dash, en dash or middot

# the block's world: a clock the fake context's calls advance, the page's state it reads, and the timers it sets
PRELUDE = r'''
let NOW = 1000;
const performance = { now: () => NOW };
const location = { search: SEARCH };
const PERF = { ready: 0 };
const HID = { n: 0, ms: 0, at: -1, bail: -1 };
const YLD = { n: 0, ms: 0, max: 0, afN: 0, afMs: 0, af: false };
const GPUMEM = { on: true, buf: 911 * 1048576, tex: 844 * 1048576, rb: 89 * 1048576 };
const winL = {}, docL = {};
const isTouch = __TOUCH__;
const window = { addEventListener: (t, f) => { (winL[t] = winL[t] || []).push(f); }, chrome: __CHROME__ };
let FOCUS = true, MW = 0;
const document = { hidden: false, visibilityState: 'visible', hasFocus: () => FOCUS, addEventListener: (t, f) => { (docL[t] = docL[t] || []).push(f); } };
class GL {
  constructor() { this.SYNC_GPU_COMMANDS_COMPLETE = 0x9117; this.SYNC_STATUS = 0x9114; this.SIGNALED = 0x9119; this.log = []; this.cost = {}; this.sig = new Set(); this.err = 0; this.fences = 0; this.deleted = 0; this.reads = 0;
    this.drawingBufferWidth = 2240; this.drawingBufferHeight = 1260; this.ext = ['WEBGL_compressed_texture_astc', 'EXT_texture_compression_bptc', 'WEBGL_compressed_texture_s3tc', 'KHR_parallel_shader_compile', 'OES_texture_float_linear']; this.asked = 0; }
  _c(name) { this.log.push(name); NOW += this.cost[name] || 0; }
  shaderSource() { this._c('shaderSource'); }
  compileShader() { this._c('compileShader'); }
  attachShader() { this._c('attachShader'); }
  linkProgram() { this._c('linkProgram'); }
  getProgramInfoLog() { this._c('getProgramInfoLog'); return 'the log'; }
  getProgramParameter(p, k) { this._c('getProgramParameter'); return k === 35714 ? true : 3; }
  getActiveUniform() { this._c('getActiveUniform'); return { name: 'u' }; }
  getUniformLocation() { this._c('getUniformLocation'); return {}; }
  getActiveAttrib() { this._c('getActiveAttrib'); return { name: 'a' }; }
  getAttribLocation() { this._c('getAttribLocation'); return 0; }
  texImage2D() { this._c('texImage2D'); return 'ti'; }
  texSubImage2D() { this._c('texSubImage2D'); }
  generateMipmap() { this._c('generateMipmap'); }
  getError() { this._c('getError'); const e = this.err; this.err = 0; return e; }
  fenceSync() { this._c('fenceSync'); return { id: ++this.fences }; }
  flush() { this._c('flush'); }
  getSyncParameter(s) { this.reads++; return this.sig.has(s) ? this.SIGNALED : 0x9118; }
  deleteSync() { this.deleted++; }
  getSupportedExtensions() { return this.ext; }
  getExtension() { this.asked++; return null; }
}
const gl = new GL();
const renderer = { getContext: () => gl, info: { programs: [] }, capabilities: { maxTextureSize: 16384, maxSamples: 4 } };
const sceneObjs = [];
const scene = { traverse: (f) => { for (const o of sceneObjs) f(o); }, updateMatrixWorld: () => { MW++; NOW += 0.25; } };
const outerMeshes = [], LANE_MATS = [];
let frameNo = 0;
const ENTER = { lit: false }, DPR = { live: false }, PIN_OCC = { landN: 0, landMs: 0 };
const camera = { position: { x: 0, y: 100, z: 0 } }, groundMeshY = () => 0, siteY = () => 0, TERRAIN = { water: -7.34 };
const crumbs = [], bootMark = (step, ctx) => crumbs.push([step, ctx]);
const timers = [], setInterval = (f) => { timers.push(f); return timers.length; }, clearInterval = (id) => { timers[id - 1] = null; };
// a program the way r149 makes one: two shaders compiled, attached vertex first, linked, the log read, the status, then the
// uniforms and the attributes (c the ms of each compile, l the link's, q the first status query's, i each later call's)
function program(c, l, q, i, noLog) {
  const v = { v: 1 }, f = { f: 1 }, p = { p: 1 };
  gl.cost = { compileShader: c, linkProgram: l, getProgramInfoLog: noLog ? 0 : q, getProgramParameter: noLog ? q : i, getActiveUniform: i, getUniformLocation: i, getActiveAttrib: i, getAttribLocation: i, getError: gl.cost.getError || 0 };
  gl.shaderSource(v, 'x'.repeat(300)); gl.compileShader(v); gl.shaderSource(f, 'y'.repeat(700)); gl.compileShader(f);
  gl.attachShader(p, v); gl.attachShader(p, f); gl.linkProgram(p);
  if (!noLog) gl.getProgramInfoLog(p);
  gl.getProgramParameter(p, 35714);
  gl.cost.getProgramParameter = i;
  gl.getProgramParameter(p, 35718);
  for (let k = 0; k < 3; k++) { gl.getActiveUniform(p, k); gl.getUniformLocation(p, 'u'); }
  gl.getProgramParameter(p, 35721); gl.getActiveAttrib(p, 0); gl.getAttribLocation(p, 'a');
  return p;
}
const R = (v) => Math.round(v * 100) / 100;
'''


def node(test, body, search='', touch=False, chrome=True):
    """The block under Node: a computer in Chromium unless told otherwise (touch: a phone; chrome=False: an engine with no
    window.chrome, WebKit or Firefox)."""
    pre = PRELUDE.replace('SEARCH', json.dumps(search)).replace('__TOUCH__', 'true' if touch else 'false').replace('__CHROME__', '{ runtime: {} }' if chrome else 'undefined')
    return run_node(test, pre + BLOCK + body)


def r149_key(custom, defines=(), raw=False):
    """A cache key the way r149 joins one: the shader id, the defines, the precision and the 24 values after it, the two
    masks and the encoding, then the custom key."""
    a = ['standard'] + list(defines)
    if not raw:
        a += ['highp', 3001, 0, '', 0, True, False, False, 0, 0, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 4, 0, 0, 3201, 12345, 67890, 3001]
    a.append(custom)
    return ','.join('true' if x is True else 'false' if x is False else str(x) for x in a)


class LinkTimers(unittest.TestCase):
    def test_a_warm_load_is_timed_apart_and_never_drained(self):
        o = node(self, r'''
const own0 = Object.prototype.hasOwnProperty.call(gl, 'linkProgram'), names = LINK.names.slice();
const ps = [];
for (let k = 0; k < 12; k++) ps.push(program(1.5, 0.5, 4, 0.25));
const snap = { n: LINK.n, c: R(LINK.c), l: R(LINK.l), q: R(LINK.q), i: R(LINK.i), d: LINK.d, dn: LINK.dn, cold: LINK.cold, med: R(LINK.med), err: LINK.err, recs: LINK.recs.length };
const r0 = LINK.recs[0];
const rec0 = { c: R(r0.c), l: R(r0.l), q: R(r0.q), i: R(r0.i), vl: r0.vl, fl: r0.fl, si: r0.si, late: r0.late };
const ret = [gl.getProgramInfoLog(ps[0]), gl.getProgramParameter(ps[0], 35714), gl.texImage2D()];
gl.cost = { texImage2D: 6, texSubImage2D: 2, generateMipmap: 1 };
gl.texImage2D(); gl.texSubImage2D(); gl.generateMipmap();
const tex = [LINK.tn, R(LINK.tms)];
LINK.off();
console.log(JSON.stringify({ own0, names, snap, rec0, ret, tex, errors: gl.log.filter((n) => n === 'getError').length, on: LINK.on, left: LINK.names.length,
  own1: Object.keys(gl).filter((k) => typeof gl[k] === 'function'), proto: gl.linkProgram === GL.prototype.linkProgram && gl.texImage2D === GL.prototype.texImage2D }));
''')
        self.assertTrue(o['own0'], 'an instance wrap, laid on the real context')
        self.assertEqual(sorted(o['names']), sorted(['shaderSource', 'compileShader', 'attachShader', 'linkProgram', 'getProgramInfoLog', 'getProgramParameter', 'getActiveUniform',
                                                      'getUniformLocation', 'getActiveAttrib', 'getAttribLocation', 'texImage2D', 'texSubImage2D', 'generateMipmap']),
                         'the 3D pair is skipped where the context has none; no draw call is ever wrapped')
        s = o['snap']
        self.assertEqual((s['n'], s['recs']), (12, 12))
        self.assertEqual((s['c'], s['l'], s['q']), (36.0, 6.0, 48.0), 'two compiles of 1.5, a link of 0.5 and a first query of 4, by 12')
        # after the first query: LINK_STATUS, ACTIVE_UNIFORMS, three uniform pairs, ACTIVE_ATTRIBUTES and the attribute pair: 11 calls of 0.25
        self.assertEqual(s['i'], 33.0)
        self.assertEqual((s['cold'], s['med']), (0, 7.5), 'ten programs in, a median of 7.5 ms: warm')
        self.assertEqual((s['d'], s['dn'], o['errors']), (0, 0, 0), 'a warm load makes no getError call')
        self.assertEqual(o['rec0'], {'c': 3.0, 'l': 0.5, 'q': 4.0, 'i': 2.75, 'vl': 300, 'fl': 700, 'si': -1, 'late': False})
        self.assertEqual(o['ret'], ['the log', True, 'ti'], 'a wrap hands back what the context returned')
        self.assertEqual(o['tex'], [4, 9.0])
        self.assertEqual(s['err'], 0)
        # off: every wrap gone, the prototype's own methods showing through
        self.assertEqual((o['on'], o['left'], o['own1'], o['proto']), (False, 0, [], True))

    def test_the_cold_verdict_is_the_medians_and_only_cold_drains(self):
        o = node(self, r'''
const out = {};
// one slow first query (the uploads queued ahead of it), then quick ones: not a cold load
program(0, 0, 900, 0);
for (let k = 0; k < 11; k++) program(1, 1, 5, 0);
out.outlier = { cold: LINK.cold, med: R(LINK.med), dn: LINK.dn };
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['outlier'], {'cold': 0, 'med': 8, 'dn': 0}, 'two compiles of 1, a link of 1 and a query of 5')
        o = node(self, r'''
const out = { early: [] };
gl.cost = { getError: 3 };
for (let k = 0; k < 9; k++) { program(10, 20, 90, 0); out.early.push(LINK.cold); }
program(10, 20, 90, 0);
out.at10 = { cold: LINK.cold, med: LINK.med, dn: LINK.dn };
gl.err = 1281;
program(10, 20, 90, 0); program(10, 20, 90, 0);
out.after = { cold: LINK.cold, dn: LINK.dn, d: LINK.d, de: LINK.de, q: LINK.q, n: LINK.n };
// the drain goes before the program's first shaderSource, once a program: never after its own compiles (its shader
// translation would be waited for in the drain) and never between the link and its first query
const i = gl.log.lastIndexOf('getError');
out.order = gl.log.slice(i, i + 9);
out.perProgram = gl.log.slice(gl.log.indexOf('getError')).filter((n) => n === 'getError' || n === 'linkProgram').join();
// a shader made and never linked does not cost the next program its drain, nor earn it two
gl.shaderSource({ lone: 1 }, 'z'); gl.compileShader({ lone: 1 });
const dn0 = LINK.dn; program(10, 20, 90, 0);
out.afterLone = LINK.dn - dn0;
// a quick program later does not make a cold load warm
for (let k = 0; k < 30; k++) program(0, 0, 1, 0);
out.latched = LINK.cold;
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['early'], [-1] * 9, 'under ten programs there is no verdict')
        self.assertEqual(o['at10'], {'cold': 1, 'med': 130, 'dn': 0})
        self.assertEqual(o['after'], {'cold': 1, 'dn': 2, 'd': 6, 'de': 1, 'q': 12 * 90, 'n': 12}, 'the drain is timed apart, and an error it swallowed is counted')
        self.assertEqual(o['order'], ['getError', 'shaderSource', 'compileShader', 'shaderSource', 'compileShader', 'attachShader', 'attachShader', 'linkProgram', 'getProgramInfoLog'],
                         'the review: drained before the link, a cold program\'s own translation was waited for in the drain and its ms under-read a warm load\'s')
        self.assertEqual(o['perProgram'], 'getError,linkProgram,getError,linkProgram', 'one drain a program')
        self.assertEqual(o['afterLone'], 0, 'the lone shader took the drain; the program after it is drained by its own next first source')
        self.assertEqual(o['latched'], 1)
        # the line can be moved for a proof
        o = node(self, 'for (let k = 0; k < 10; k++) program(1, 1, 5, 0);\nconsole.log(JSON.stringify({ cold: LINK.cold, ms: COLD_MS, min: COLD_MIN }));', search='?dev=1&coldms=6')
        self.assertEqual(o, {'cold': 1, 'ms': 6, 'min': 10})
        self.assertIn("const COLD_MS = +(/[?&]coldms=(\\d+)/.exec(location.search) || [0, 60])[1], COLD_MIN = 10;", BLOCK)
        # the review: the line was 40, and a warm M2 Max under other work read a median of 37.6 to 45 ms in Chrome, cold with
        # nothing to compile. 45 is warm now; the fastest cold load the beacons hold (88 ms a program, about 70 at the median) is cold
        o = node(self, r'''
const out = {};
for (let k = 0; k < 12; k++) program(1, 1, 42, 0);   // two compiles of 1, a link of 1, a query of 42
out.busy = [LINK.cold, LINK.med, LINK.dn];
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['busy'], [0, 45, 0])
        o = node(self, 'for (let k = 0; k < 12; k++) program(1, 1, 67, 0);\nconsole.log(JSON.stringify([LINK.cold, LINK.med, COLD_MS]));')
        self.assertEqual(o, [1, 70, 60])

    def test_where_the_wraps_come_off(self):
        """The review: a warm load's wraps come off at Ready, so nothing is installed on any path a warm load runs after its
        build; a cold load's stay through the one frame drawn behind the unlit button, so the enter beacon says what that
        frame linked on the loads the plan is about."""
        body = r'''
const own = () => Object.keys(gl).filter((k) => typeof gl[k] === 'function').length;
const out = { before: [LINK.on, own()] };
for (let k = 0; k < 12; k++) program(1, 1, Q, 0);
const progs = () => LINK.recs.map((r, k) => ({ program: r.p, name: 'MeshStandardMaterial', cacheKey: 'k' + k }));
renderer.info.programs = progs();
PERF.ready = 29000; NOW = 30000; measReady();
out.ready = [LINK.cold, LINK.on, own(), LINK.names.length, MEAS.ready.wr, gl.linkProgram === GL.prototype.linkProgram];
// the first frame links three more
for (let k = 0; k < 3; k++) program(1, 1, Q, 0);
renderer.info.programs = out.before[0] && LINK.on ? progs() : renderer.info.programs.concat([{}, {}, {}]);
out.frame = [LINK.recs.length, LINK.n];
measLit();
out.lit = [LINK.on, own(), MEAS.lit.prg, MEAS.lit.link.n];
PERF.lit = 31000;
out.enter = measFacts('enter');
console.log(JSON.stringify(out));
'''
        w = node(self, body.replace('Q', '5'))
        self.assertEqual(w['before'], [True, 13], 'thirteen of the fifteen names exist on this scripted context')
        self.assertEqual(w['ready'], [0, False, 0, 0, False, True], 'a warm load: every wrap off at Ready, the prototype\'s method showing through')
        self.assertEqual(w['frame'], [12, 12], 'and its first frame is not timed')
        self.assertEqual(w['lit'], [False, 0, 15, 12])
        self.assertEqual(w['enter'], {'cold': 0, 'f1p': 3, 'lit': 2000, 'eb': 0}, 'the count of programs still rides; no timer that was not running is reported as nought')
        c = node(self, body.replace('Q', '90'))
        self.assertEqual(c['ready'], [1, True, 13, 13, True, False], 'a cold load keeps them for the one frame behind the unlit button')
        self.assertEqual(c['frame'], [15, 15])
        self.assertEqual(c['lit'], [False, 0, 15, 15], 'and they come off as that frame ends')
        self.assertEqual(c['enter']['f1k'], '3.6.3.270.0.0')
        self.assertEqual(c['enter']['f1p'], 3)
        r = cut(BLOCK, '  function measReady() {', '\n  }\n')
        self.assertIn("      if (LINK.cold !== 1) LINK.off();", r)
        self.assertLess(r.index('link: linkSnap()'), r.index('if (LINK.cold !== 1) LINK.off();'), 'the sums are read before the wraps go')
        self.assertLess(r.index('if (LINK.cold !== 1) LINK.off();'), r.index('MEAS.ready.wr = LINK.on;'))

    def test_the_first_status_query_is_whichever_comes_first(self):
        # with checkShaderErrors off (a later round), three's first blocking call is getProgramParameter
        o = node(self, r'''
const p = program(2, 3, 50, 1, true), r = LINK.recs[0];
console.log(JSON.stringify({ c: r.c, l: r.l, q: r.q, i: r.i, n: LINK.n }));
''')
        self.assertEqual(o, {'c': 4, 'l': 3, 'q': 50, 'i': 10, 'n': 1})

    def test_a_wrap_that_faults_still_calls_through(self):
        o = node(self, r'''
const before = gl.log.length;
gl.shaderSource(null, 'x');   // a WeakMap refuses the key: the bookkeeping throws, the call does not
gl.compileShader(undefined);
const ret = gl.getProgramInfoLog({ never: 'attached' });   // a program the timers never saw
console.log(JSON.stringify({ err: LINK.err, calls: gl.log.slice(before), ret, n: LINK.n }));
''')
        self.assertEqual(o, {'err': 1, 'calls': ['shaderSource', 'compileShader', 'getProgramInfoLog'], 'ret': 'the log', 'n': 0})

    def test_the_wraps_text(self):
        f = cut(BLOCK, '  function linkInstall(gl) {', '\n  }\n', inclusive=True)
        # the call itself sits outside every try, and no draw call is named
        self.assertIn("        if (pre) { try { pre(this); } catch (e) { L.err++; } }\n        const t0 = performance.now(), out = o.apply(this, arguments);\n        try { fn(performance.now() - t0, arguments); } catch (e) { L.err++; }\n        return out;", f)
        for bad in ('drawElements', 'drawArrays', 'useProgram', 'uniform1', 'bindBuffer', 'bufferData'):
            self.assertNotIn(bad, f)
        self.assertIn("L.off = () => { for (const n of L.names) delete gl[n]; L.names.length = 0; L.on = false; };", f)
        self.assertNotIn('getExtension', BLOCK.replace('getExtension would ENABLE', ''), 'asking for the parallel-compile extension would change what is measured')
        # laid once, on the real context, before anything compiles: the block sits between the renderer and its first use
        self.assertEqual(SRC.count('linkInstall(renderer.getContext())'), 1)
        self.assertLess(SRC.index('    renderer = make(mode);'), SRC.index('linkInstall(renderer.getContext())'))
        self.assertLess(SRC.index('linkInstall(renderer.getContext())'), SRC.index('function zrevInstall(R) {'))
        self.assertLess(SRC.index('linkInstall(renderer.getContext())'), SRC.index('const scene = new THREE.Scene();'))


class Tags(unittest.TestCase):
    def test_the_key_and_the_tag(self):
        hook = "(sh, r) => { lanePatch(sh, fresh); prev(sh, r); }"
        keys = {
            'fabric': r149_key('fabric|wx'),
            'defines': r149_key('glass-sys|10111', defines=('STANDARD', '', 'USE_UV', '')),
            'plain': r149_key('onBeforeCompile(){}'),
            'hooked': r149_key(hook),
            'long': r149_key('lane|' + hook + hook),
            'raw': r149_key('onBeforeCompile(){}', defines=('X', 1), raw=True),
            'venue': r149_key('venue-texture-0.35'),
        }
        o = node(self, 'const K = ' + json.dumps(keys) + r''';
const out = {};
for (const k in K) out[k] = [progKey(K[k]), progTag(k === 'raw' ? 'RawShaderMaterial' : k === 'plain' ? 'MeshLambertMaterial' : 'MeshStandardMaterial', progKey(K[k]), 40126)];
out.type = [progTag('MeshDepthMaterial', 'fabric', 1), progTag('MeshToonMaterial', '', 9), progTag('ShaderMaterial', '', 14332), progTag(undefined, '', 0)];
out.same = progHash('abc') === progHash('abc') && progHash('abc') !== progHash('abd');
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['fabric'], ['fabric|wx', 'Std-fabric-wx'])
        self.assertEqual(o['defines'], ['glass-sys|10111', 'Std-glass-sys-10111'], 'the defines before the precision do not move the key')
        self.assertEqual(o['plain'], ['', 'Lam-f40126'], 'no key of its own: the type and the fragment source length')
        self.assertEqual(o['hooked'][0], hook, 'a hook with commas in its source is taken whole')
        self.assertRegex(o['hooked'][1], r'^Std-h[0-9a-z]+$')
        self.assertRegex(o['long'][1], r'^Std-lane-h[0-9a-z]+$', 'a long key: its first safe characters and a hash of the whole')
        self.assertEqual(o['raw'], ['', 'Raw-f40126'])
        self.assertEqual(o['venue'], ['venue-texture-0.35', 'Std-venue-texture-0-35'])
        self.assertEqual(o['type'], ['Dep-fabric', 'Toon-f9', 'Sha-f14332', 'x-f0'])
        self.assertTrue(o['same'])
        for k, v in o.items():
            if k in ('type', 'same'):
                continue
            self.assertRegex(v[1], r'^[A-Za-z0-9-]{1,30}$', 'letters, digits and dashes: a tag holds no dot and no underscore')
            self.assertNotEqual(v[1], 'MeshStandardMaterial')

    def test_the_slowest_five_and_the_listing(self):
        o = node(self, r'''
const ps = [];
const ms = [5, 80, 20, 300, 7, 150, 60, 9];
for (const q of ms) ps.push(program(0, 0, q, 0));
const K = (c) => ['standard', 'highp', 3001, 0, '', 0, true, false, false, 0, 0, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 4, 0, 0, 3201, 1, 2, 3001, c].join();
// three keeps a program's GL object as .program; one has been released since
renderer.info.programs = ps.map((p, k) => ({ program: p, name: 'MeshStandardMaterial', cacheKey: K('key' + k) })).filter((p, k) => k !== 5);
const top = linkTop(0, LINK.recs.length), late = linkTop(6, LINK.recs.length), list = PERF.programs();
console.log(JSON.stringify({ top, late, list: list.slice(0, 3).map((p) => [p.tag, p.ms, p.q, p.gone, p.key, p.fs]), n: list.length }));
''')
        self.assertEqual(o['top'], 'Std-key3.300_gone-f700.150_Std-key1.80_Std-key6.60_Std-key2.20')
        self.assertEqual(o['late'], 'Std-key6.60_Std-key7.9', 'a range: what the first frame linked')
        self.assertEqual(o['list'], [['Std-key3', 300, 300, False, 'key3', 700], ['gone-f700', 150, 150, True, '', 700], ['Std-key1', 80, 80, False, 'key1', 700]])
        self.assertEqual(o['n'], 8)


class BuildWaits(unittest.TestCase):
    def test_a_step_s_waits(self):
        o = node(self, r'''
const w = stepYield(7);
const step = MEAS.step;
YLD.n = 1; YLD.ms = 116.4;                 // the step's own yield
stepWaited(w);
YLD.n = 4; YLD.ms = 116.4 + 60.3;          // three more inside the step
stepDone(w);
const v = stepYield(9); YLD.n = 5; YLD.ms += 2; stepWaited(v); stepDone(v);   // a step with none inside
console.log(JSON.stringify({ step, gw: Array.from(MEAS.gw, (x) => x || 0), gi: MEAS.gi, now: MEAS.step }));
''')
        self.assertEqual(o, {'step': 7, 'gw': [0, 0, 0, 0, 0, 0, 0, 116, 0, 2], 'gi': ['7.3.60'], 'now': 9})

    def test_the_fences(self):
        o = node(self, r'''
const out = {};
MEAS.step = 10; renderer.info.programs = new Array(63);
NOW = 5000; flushNote(4000, 3);
out.flush = { list: MEAS.flushes.slice(), af: YLD.af, calls: gl.log.slice(-2), q: MEAS.fq.length, n: MEAS.fence.n };
const f0 = MEAS.fq[0].s;
// Ready in the same task: a fence no later task has polled is never read and counts for nothing
const m0 = { ...MEAS.fence }; const reads0 = gl.reads;
// (not called here: see the last case)  a later task finds it unsignalled, a later one still, then passed
NOW = 5001; fencePoll(false);
NOW = 5400; fencePoll(false);
out.pending = { q: MEAS.fq.length, reads: gl.reads - reads0, late: MEAS.fence.late };
gl.sig.add(f0); NOW = 6200; fencePoll(false);
out.late = { ...MEAS.fence, q: MEAS.fq.length, deleted: gl.deleted };
// one that has passed by its first poll is not late
MEAS.step = 11; NOW = 7000; flushNote(6900, 63); gl.sig.add(MEAS.fq[0].s); NOW = 7003; fencePoll(false);
out.quick = { ...MEAS.fence, q: MEAS.fq.length };
// at Ready: one seen unsignalled is pending (its lower bound counted), one never polled is neither
MEAS.step = 12; NOW = 8000; flushNote(7990, 63); NOW = 8050; fencePoll(false);
MEAS.step = 39; NOW = 9000; flushNote(8990, 63);
const r1 = gl.reads; NOW = 9100; fencePoll(true);
out.ready = { ...MEAS.fence, q: MEAS.fq.length, reads: gl.reads - r1, deleted: gl.deleted };
// at most eight in flight
for (let k = 0; k < 12; k++) flushNote(NOW, 63);
out.cap = [MEAS.fq.length, MEAS.fence.n, MEAS.flushes.length];
// a context that throws costs nothing but the count
gl.getSyncParameter = () => { throw new Error('lost'); }; fencePoll(false);
out.lost = [MEAS.fq.length, MEAS.err];
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['flush'], {'list': [[10, 1000, 60]], 'af': True, 'calls': ['fenceSync', 'flush'], 'q': 1, 'n': 1})
        self.assertEqual(o['pending'], {'q': 1, 'reads': 2, 'late': 0})
        self.assertEqual(o['late'], {'n': 1, 'late': 1, 'lo': 400, 'hi': 1200, 'max': 400, 'at': 10, 'pend': 0, 'cms': 0, 'st': 0, 'q': 0, 'deleted': 1},
                         'last seen unsignalled 400 ms after the flush, first seen passed at 1,200')
        self.assertEqual((o['quick']['n'], o['quick']['late'], o['quick']['lo'], o['quick']['q']), (2, 1, 400, 0))
        self.assertEqual(o['ready'], {'n': 4, 'late': 1, 'lo': 400 + 1100, 'hi': 1200, 'max': 1100, 'at': 12, 'pend': 1, 'cms': 0, 'st': 0, 'q': 0, 'reads': 1, 'deleted': 4},
                         'Ready reads only the fence a later task had polled, and lets both go')
        self.assertEqual(o['cap'], [8, 12, 16])
        self.assertEqual(o['lost'], [0, 0], 'a read that throws drops the fence quietly')

    def test_no_fence_where_the_call_waits(self):
        """The review's must-fix. MEASURED in a WKWebView on this build: fenceSync waits there until the GPU process has
        worked through what the flush queued, 264 to 865 ms a load on a computer's path and 527 and 2,680 ms on the
        phone's, on warm loads, in no field. A fence is laid only on a computer in Chromium; the call is timed; and the
        first call that waits is the load's last."""
        none = r'''
gl.cost = { fenceSync: 772, flush: 1 };
MEAS.step = 12; renderer.info.programs = new Array(63);
const t0 = NOW;
for (let k = 0; k < 3; k++) { NOW += 1000; flushNote(NOW - 900, 60); }
fencePoll(false); NOW += 5; fencePoll(true);
console.log(JSON.stringify({ calls: gl.log.filter((n) => n === 'fenceSync' || n === 'flush').length, reads: gl.reads, fence: MEAS.fence, q: MEAS.fq.length, flushes: MEAS.flushes, af: YLD.af, waited: NOW - t0 - 3005, ok: FENCE_OK, err: MEAS.err }));
'''
        want = {'calls': 0, 'reads': 0, 'fence': {'n': 0, 'late': 0, 'lo': 0, 'hi': 0, 'max': 0, 'at': -1, 'pend': 0, 'cms': 0, 'st': 2}, 'q': 0,
                'flushes': [[12, 900, 3], [12, 900, 3], [12, 900, 3]], 'af': True, 'waited': 0, 'ok': False, 'err': 0}
        self.assertEqual(node(self, none, touch=True), want, 'a phone: no fenceSync, no flush, no poll, and the flush is still noted')
        self.assertEqual(node(self, none, chrome=False), want, 'a computer in WebKit or Firefox: the same')
        self.assertEqual(node(self, none, touch=True, chrome=False), want)
        o = node(self, r'''
const out = {};
MEAS.step = 10; renderer.info.programs = new Array(63);
// quick calls keep the instrument: each pair's ms is summed
gl.cost = { fenceSync: 0.5, flush: 0.25 };
NOW = 5000; flushNote(4000, 3); NOW = 6000; flushNote(5900, 63);
out.quick = { ...MEAS.fence, q: MEAS.fq.length, ok: FENCE_OK };
// one call that waits: it is timed, its fence is kept and still polled, and no other is laid in this load
gl.cost = { fenceSync: 73, flush: 0 };
NOW = 7000; flushNote(6900, 63);
out.slow = { ...MEAS.fence, q: MEAS.fq.length };
const calls = gl.log.filter((n) => n === 'fenceSync').length;
gl.cost = { fenceSync: 1608 }; const t = NOW;
for (let k = 0; k < 4; k++) flushNote(NOW - 10, 63);
out.after = { ...MEAS.fence, q: MEAS.fq.length, more: gl.log.filter((n) => n === 'fenceSync').length - calls, waited: NOW - t, flushes: MEAS.flushes.length };
for (const f of MEAS.fq) gl.sig.add(f.s);
NOW += 3; fencePoll(false);
out.polled = [MEAS.fq.length, gl.deleted];
console.log(JSON.stringify(out));
''')
        self.assertEqual((o['quick']['n'], o['quick']['cms'], o['quick']['st'], o['quick']['q'], o['quick']['ok']), (2, 1.5, 0, 2, True))
        self.assertEqual((o['slow']['n'], o['slow']['cms'], o['slow']['st'], o['slow']['q']), (3, 74.5, 1, 3), 'the slow call is counted and timed: on such an engine that number is the backlog')
        self.assertEqual((o['after']['n'], o['after']['cms'], o['after']['st'], o['after']['more'], o['after']['waited'], o['after']['flushes']), (3, 74.5, 1, 0, 0, 7))
        self.assertEqual(o['polled'], [0, 3], 'the fences already laid are still read and let go')
        # a WebGL 1 context has no fenceSync
        o = node(self, 'gl.fenceSync = undefined; flushNote(NOW - 5, 0); flushNote(NOW - 5, 0);\nconsole.log(JSON.stringify([MEAS.fence.st, MEAS.fence.n, MEAS.err, MEAS.flushes.length]));')
        self.assertEqual(o, [3, 0, 0, 2])
        # the text: the gate reads the device and the engine's own global, never the agent string, and the line is a few ms
        self.assertIn("  const FENCE_OK = !isTouch && typeof window.chrome === 'object' && !!window.chrome, FENCE_SLOW_MS = 4;", BLOCK)
        f = cut(BLOCK, '  function flushNote(tf, fp) {', '\n  }\n')
        self.assertLess(f.index('YLD.af = true;'), f.index('if (F.st !== 0) return;'), 'the flush is noted whether or not a fence follows')
        self.assertLess(f.index('if (F.st !== 0) return;'), f.index('gl.fenceSync('))
        self.assertEqual(BLOCK.count('fenceSync('), 1)
        self.assertIn('if (d >= FENCE_SLOW_MS) F.st = 1;', f)

    def test_yield_now_times_itself(self):
        line = cut(SRC, '  const YLD = PERF.yld = {', '\n', inclusive=True) + cut(SRC, '  const yieldNow = () => new Promise(r => {', '\n', inclusive=True)
        self.assertEqual(SRC.count('const yieldNow = '), 1)
        o = run_node(self, r'''
let NOW = 0; const performance = { now: () => NOW }, PERF = {}; let polls = 0; const fencePoll = (last) => { polls += last === false ? 1 : 100; };
const chans = []; class MessageChannel { constructor() { this.port1 = {}; this.port2 = { postMessage: () => chans.push(this) }; } }
LINE
(async () => {
  const fire = (ms) => { NOW += ms; chans.shift().port1.onmessage(); };
  let p = yieldNow(); fire(3); await p;
  YLD.af = true; p = yieldNow(); const cleared = YLD.af; fire(225); await p;
  p = yieldNow(); fire(1); await p;
  console.log(JSON.stringify({ YLD, polls, cleared }));
})();
'''.replace('LINE', line))
        self.assertEqual(o, {'YLD': {'n': 3, 'ms': 229, 'max': 225, 'afN': 1, 'afMs': 225, 'af': False}, 'polls': 3, 'cleared': False})


class Frames(unittest.TestCase):
    def test_stalls_gaps_and_the_eye(self):
        o = node(self, r'''
const out = {};
const F = (ms, once) => { frameNo++; measFrame(ms, once); };
renderer.info.programs = new Array(165);
// behind the veil: the first frame's gap is the whole build's and is not the worst; nothing counts before Enter
MEAS.ready = { link: linkSnap(), prg: 141 };
F(29000); F(700); F(40);
out.veil = { last: MEAS.lastMs, worst: MEAS.worstMs, stall: MEAS.stall.n, off: LINK.on };
DPR.live = true;   // Enter
F(16);
out.offAtEnter = [LINK.on, !!MEAS.lit, Object.keys(gl).filter((k) => typeof gl[k] === 'function').length];
F(300);                                         // a stall with no new program
F(16); renderer.info.programs = new Array(170); // five programs compile in this frame's draw...
F(1300);                                        // ...and the gap to the next frame is the stall they made
F(260, true);                                   // a probe's frameOnce is not a frame of the loop
out.stall = { ...MEAS.stall };
// hidden: the gap spent away is no stall, nor is the first frame back
document.hidden = true; for (const f of docL.visibilitychange) f();
document.hidden = false; F(45000); F(16);
out.away = MEAS.stall.n;
// a landing is made at a frame's start; its cost is in the gap to the NEXT frame
MEAS.fg = [0, 0, 0, 0];
F(16); PIN_OCC.landN = 1; F(16); F(40); F(16); PIN_OCC.landN = 2; F(18); F(60); F(600);
out.fg = MEAS.fg.slice();
// the eye's height every 8th frame, over the ground or the water
MEAS.eh = [0, 0, 0, 0];
const at = (y) => { camera.position.y = y; while (frameNo % 8 !== 7) F(16); F(16); };
at(5); at(100); at(100); at(500); at(900);
out.eh = MEAS.eh;
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['veil'], {'last': 40, 'worst': 700, 'stall': 0, 'off': True})
        self.assertEqual(o['offAtEnter'], [False, True, 0], 'whatever happened to the first frame, the first frame after Enter finds no wrap')
        self.assertEqual(o['stall'], {'n': 2, 'ms': 1600, 'pn': 1, 'pms': 1300, 'max': 1300, 'prg': 170})
        self.assertEqual(o['away'], 2)
        self.assertEqual(o['fg'], [100, 2, 16 * 3 + 18, 4], 'the 40 and the 60 follow the two landing frames; 600 ms is a stall, not a gap')
        self.assertEqual(o['eh'], [1, 2, 1, 1])

    def test_the_javascript_split_and_the_capture(self):
        o = node(self, r'''
measJs(100, 100.5, 103, 111, 118, 119); measJs(200, 200.5, 201, 202, 203, 209);
capNote(false, 3.5, { triangles: 2400000, calls: 150 }); capNote(true, 1.5, { triangles: 600000, calls: 50 }); capNote(false, 4, null);
console.log(JSON.stringify({ js: MEAS.js, n: MEAS.jsN, cap: MEAS.cap }));
''')
        self.assertEqual(o, {'js': [1, 3, 9, 8, 7], 'n': 2, 'cap': {'n': 3, 'ms': 9, 'tris': 3000000, 'calls': 200, 'near': 1}})


class Crumb(unittest.TestCase):
    def test_every_second_until_the_running_crumb(self):
        o = node(self, r'''
const out = {};
PERF.ready = 29000; frameNo = 1;
for (let k = 0; k < 12; k++) program(1, 1, 5, 0);
NOW = 30000; measReady();
out.ready = { prg: MEAS.ready.prg, n: MEAS.ready.link.n, hd: MEAS.ready.hd, hn: MEAS.ready.hn, med: MEAS.ready.med, top: MEAS.ready.top, on: MEAS.on, timers: timers.length, mw: MW };
const tick = timers[0];
NOW = 31000; tick();
PERF.enterT = 33500; ENTER.lit = true; frameNo = 130; MEAS.lastMs = 46.4; MEAS.worstMs = 1467.2; renderer.info.programs = new Array(193);
NOW = 36000; tick();
NOW = 49400; tick();
out.crumbs = crumbs.slice();
NOW = 49500; tick();   // by the clock: the running crumb is due at 20 s and must never be overwritten
out.stopped = [crumbs.length, timers[0] === null];
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['ready'], {'prg': 0, 'n': 12, 'hd': 0, 'hn': 0, 'med': 8, 'top': '', 'on': '0.250', 'timers': 1, 'mw': 11},
                         'the matrix pass is the mean of ten after a first (the review: one pass is under the clock\'s step), in microseconds')
        self.assertEqual(o['crumbs'], [['ready', 'q1,e-1,f1,m0,w0,gb1844,b911,x844,r89,p0,l0'], ['ready', 'q6,e3,f130,m46,w1467,gb1844,b911,x844,r89,p193,l1'],
                                       ['ready', 'q19,e16,f130,m46,w1467,gb1844,b911,x844,r89,p193,l1']], 'q is the clock\'s seconds since Ready, not a count of ticks (a hidden tab ticks late)')
        self.assertEqual(o['stopped'], [3, True])
        for step, ctx in o['crumbs']:
            self.assertEqual(step, 'ready', "the same step: the next load's verdict is what it was")
            self.assertEqual(re.sub(r'[^\w.,:-]', '', ctx), ctx, "pc's own cleaning leaves it whole")
        # the worst the crumb can be still fits the next load's pc (80 characters)
        self.assertLessEqual(len('q19,e19,f99999,m99999,w599999,gb9999,b9999,x9999,r9999,p999,l1'), 80)

    def test_left_or_hidden(self):
        o = node(self, r'''
PERF.ready = 1; NOW = 2000; measReady();
NOW = 3000; timers[0]();
for (const f of winL.pagehide) f();   // the page is left: pagehide clears the crumb for good (bootClear), and nothing writes it back
NOW = 4000; if (timers[0]) timers[0]();
console.log(JSON.stringify({ n: crumbs.length, cleared: timers[0] === null }));
''')
        self.assertEqual(o, {'n': 1, 'cleared': True})
        # the review: only the tab in front writes, the running crumb's own rule. A second tab finishing its build in the
        # background wrote 'ready' every second for 19.5 s over the front tab's 'running'
        o = node(self, r'''
PERF.ready = 1; NOW = 2000; measReady();
const tick = timers[0], n = [];
NOW = 3000; tick(); n.push(crumbs.length);
document.visibilityState = 'hidden'; NOW = 4000; tick(); NOW = 5000; tick(); n.push(crumbs.length);
document.visibilityState = 'visible'; FOCUS = false; NOW = 6000; tick(); n.push(crumbs.length);   // visible beside the window in front
FOCUS = true; NOW = 7000; tick(); n.push(crumbs.length);
console.log(JSON.stringify({ n, alive: timers[0] !== null, last: crumbs[crumbs.length - 1][1].split(',')[0] }));
''')
        self.assertEqual(o, {'n': [1, 1, 1, 2], 'alive': True, 'last': 'q5'}, 'not written while hidden or unfocused; written again in front, by the clock')
        # the ready snapshot closes an open hide
        o = node(self, r'''
HID.n = 2; HID.ms = 4000; HID.at = 9000; HID.bail = 3100; PERF.ready = 1; NOW = 12500; measReady();
console.log(JSON.stringify([MEAS.ready.hd, MEAS.ready.hn]));
''')
        self.assertEqual(o, [7500, 2])

    def test_the_wiring(self):
        b = cut(SRC, '  async function build() {', '\n  }\n')
        self.assertIn("    bootMark('ready');\n    measReady();", b)
        self.assertLess(b.index('measReady();'), b.index("beacon('ready', { ms: PERF.ready, fail: failures, sf: SF.state });"), 'the ready beacon reads the snapshot')
        self.assertLess(b.index('measReady();'), b.index('}, 20000);'))
        # the running crumb's own timer is as it was
        self.assertIn('bootRun(); setInterval(bootRun, 5000);', b)
        r = cut(BLOCK, '  function measReady() {', '\n  }\n')
        self.assertIn("if (MEAS.left || performance.now() - t >= 19500) { clearInterval(id); return; }", r)
        self.assertIn("try { bootMark('ready', readyCtx()); } catch (e) { MEAS.err++; }", r)
        gate = "if (document.visibilityState !== 'visible' || !document.hasFocus()) return;"
        self.assertIn(gate, r)
        self.assertLess(r.index('clearInterval(id); return; }'), r.index(gate), 'the stop by the clock comes first: a hidden tab still stops at 19.5 s')
        self.assertLess(r.index(gate), r.index("bootMark('ready', readyCtx())"))
        self.assertIn("const bootRun = () => { if (document.visibilityState === 'visible' && document.hasFocus()) bootMark('running', bootCtx()); };", b, 'the rule it follows')
        self.assertIn("window.addEventListener('pagehide', () => { MEAS.left = true; });", BLOCK)
        # the hides before Ready, counted from the first line that can
        h = cut(SRC, '  const HID = PERF.hid = {', '\n  });\n', inclusive=True)
        self.assertIn("const HID = PERF.hid = { n: document.hidden ? 1 : 0, ms: 0, at: document.hidden ? performance.now() : -1, bail: -1 };", h)
        self.assertIn('if (PERF.ready) return;', h)
        o = run_node(self, r'''
let NOW = 100; const performance = { now: () => NOW }, PERF = { ready: 0 }; const L = []; const document = { hidden: false, addEventListener: (t, f) => L.push(f) };
HIDE
const go = (hidden, t) => { document.hidden = hidden; NOW = t; for (const f of L) f(); };
go(true, 3000); go(true, 3500); go(false, 5000); go(true, 8000); go(false, 9000); PERF.ready = 9500; go(true, 9600); go(false, 9900);
console.log(JSON.stringify(HID));
'''.replace('HIDE', h))
        self.assertEqual(o, {'n': 2, 'ms': 3000, 'at': -1, 'bail': 3000}, 'two hides, their time, the first one the bail; nothing after Ready')


class Families(unittest.TestCase):
    def test_bytes_by_family(self):
        o = node(self, r'''
const A = (n) => ({ array: new Uint8Array(n) });
const lane = { userData: { wxSurf: true } }, park = { userData: { wxSurf: true } }, wall = { userData: {} };
LANE_MATS.push(lane);
const shared = A(1000), ib = { array: new Uint8Array(640) };
const chunk = { geometry: { attributes: { position: A(1200), normal: { isInterleavedBufferAttribute: true, data: ib }, color: { isInterleavedBufferAttribute: true, data: ib } }, index: A(300) }, material: wall };
outerMeshes.push(chunk);
const road = { geometry: { attributes: { position: A(500) }, index: null }, material: [lane] };
const flat = { geometry: { attributes: { position: A(700) } }, material: park };
const trees = { isInstancedMesh: true, geometry: { attributes: { position: shared } }, material: wall, instanceMatrix: A(6400), instanceColor: null };
const posts = { isInstancedMesh: true, geometry: { attributes: { position: shared } }, material: wall, instanceMatrix: A(640), instanceColor: A(30) };
const other = { geometry: { attributes: { position: A(90) }, index: A(10) }, material: wall };
const group = { children: [] }, lost = { geometry: { attributes: { position: { array: null } } }, material: wall };
sceneObjs.push(group, chunk, road, flat, trees, posts, other);
const out = { noted: famWalk(false), sum: famWalk(true) };
// the upload frees the arrays: what was noted stands
for (const o of sceneObjs) if (o.geometry) { for (const k in o.geometry.attributes) { const a = o.geometry.attributes[k]; (a.data || a).array = null; } if (o.geometry.index) o.geometry.index.array = null; }
trees.instanceMatrix.array = null;
sceneObjs.push(lost);   // made and uploaded between two walks: never sized
out.freed = famWalk(true);
MEAS.fam = new WeakMap();
out.forgot = famWalk(true).slice(0, 6);
out.field = (MEAS.fam = new WeakMap(), sceneObjs.length = 0, sceneObjs.push({ geometry: { attributes: { position: A(481502620 / 4) } }, material: wall }), outerMeshes[0] = sceneObjs[0], famField());
out.probe = Object.keys(PERF.families());
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['noted'], [0, 0, 0, 0, 0, 0], 'a noting walk sums nothing')
        self.assertEqual(o['sum'], [1200 + 640 + 300, 500, 700, 1000 + 6400 + 640 + 30, 100, 0], 'chunks, roads, flats, instanced, the rest; a shared buffer once')
        self.assertEqual(o['freed'], [2140, 500, 700, 8070, 100, 1])
        self.assertEqual(o['forgot'][5], 10, 'with nothing noted, each of the ten freed buffers is one never sized (the instance streams still here are sized)')
        self.assertEqual(o['field'], '115.0.0.0.0.0')
        self.assertEqual(o['probe'], ['chunks', 'roads', 'flats', 'instanced', 'rest', 'unknown', 'walkMs'])

    def test_noted_before_every_upload(self):
        f = cut(SRC, '  const flushUploads = (all) => {', '\n  };')
        self.assertIn('    try { famWalk(false); } catch (e) { /* a count, never the flush */ }', f)
        self.assertLess(f.index('packResident(groupCity);'), f.index('famWalk(false);'), 'after the pack: the bytes are the packed ones')
        self.assertLess(f.index('famWalk(false);'), f.index('renderer.render(scene, camera)'), 'before the render that uploads and frees')
        self.assertLess(f.index('const fp = renderer.info.programs.length;'), f.index('renderer.render(scene, camera)'))
        self.assertTrue(f.rstrip().endswith('flushNote(tf, fp);   // Round 229: this flush\'s step, ms and programs for the ready beacon\'s fll, and the fence behind it'))
        self.assertIn('      famWalk(false);\n', cut(BLOCK, '  function measReady() {', '\n  }\n'), 'and at Ready, for what the first frame uploads')


FACTS = r'''
const out = {};
out.none = [measFacts('boot'), measFacts('step:x'), measFacts('ready'), measFacts('err')];
out.bail0 = measFacts('bail');
for (let k = 0; k < 12; k++) program(10, 20, 90, 0.5);
const K = (c) => ['standard', 'highp', 3001, 0, '', 0, true, false, false, 0, 0, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 4, 0, 0, 3201, 1, 2, 3001, c].join();
renderer.info.programs = LINK.recs.map((r, k) => ({ program: r.p, name: 'MeshStandardMaterial', cacheKey: K(k === 3 ? 'fabric|wx' : 'k' + k) }));
LINK.recs[3].q = 400; LINK.q += 310;
out.bail = measFacts('bail');
gl.cost = { texImage2D: 5 }; gl.texImage2D(); gl.texImage2D();
MEAS.gw = [4, 6, 116]; MEAS.gw[5] = 9; MEAS.gi = ['2.29.15', '5.3.9'];
MEAS.flushes = [[2, 1000, 30], [2, 757, 30], [5, 1301, 36]];
Object.assign(YLD, { n: 155, ms: 695.3, max: 224.6, afN: 14, afMs: 11.9 });
Object.assign(MEAS.fence, { n: 14, late: 3, lo: 410.2, hi: 1894.4, max: 371.9, at: 5, pend: 1, cms: 2.4, st: 0 });
HID.n = 1; HID.ms = 4200; HID.bail = 3100; MEAS.artNull = 2;
sceneObjs.push({ geometry: { attributes: { position: { array: new Uint8Array(3 * 1048576) } } }, material: { userData: {} } });
PERF.ready = 29209; NOW = 30000; measReady();
out.ready = measFacts('ready');
out.asked = gl.asked;
// the first frame links three more, then the button lights
gl.cost = {}; for (let k = 0; k < 3; k++) program(1, 1, 60 + k, 0);
renderer.info.programs = renderer.info.programs.concat(LINK.recs.slice(12).map((r, k) => ({ program: r.p, name: 'ShaderMaterial', cacheKey: K('wx-halo' + k) })));
gl.cost = { texSubImage2D: 4 }; gl.texSubImage2D();
PERF.lit = 31226; PERF.enterBy = 'timer';
out.enter = measFacts('enter');
out.off = [LINK.on, Object.keys(gl).filter((k) => typeof gl[k] === 'function').length];
Object.assign(MEAS.stall, { n: 3, ms: 2100.4, pn: 2, pms: 1800, max: 1300 });
PIN_OCC.landN = 40; PIN_OCC.landMs = 172.6;
Object.assign(MEAS.cap, { n: 6, ms: 21, tris: 14778000, calls: 888, near: 2 });
MEAS.eh = [1, 71, 7, 1]; MEAS.js = [4, 320, 1680, 360, 40]; MEAS.jsN = 400; MEAS.fg = [232, 4, 6400, 394]; MEAS.traf = 39.84;
out.perf = measFacts('perf'); out.late = Object.keys(measFacts('late')).join(); out.settled = Object.keys(measFacts('settled')).join();
console.log(JSON.stringify(out));
'''


class Facts(unittest.TestCase):
    _o = None

    @property
    def o(self):
        if Facts._o is None:
            Facts._o = node(self, FACTS)
        return Facts._o

    def test_by_checkpoint(self):
        o = self.o
        self.assertEqual(o['none'], [{}, {}, {}, {}], 'nothing for the other checkpoints, and nothing for ready before Ready')
        self.assertEqual(o['bail0'], {'cold': ''}, 'a bail before ten programs: the verdict is not in')
        self.assertEqual(o['bail'], {'cold': 1})
        r = o['ready']
        self.assertEqual(r['cold'], 1)
        self.assertEqual(r['lk'], '12.240.240.1390.66.0.130', 'programs, then ms: compile, link, first query, introspection, drain; the median program')
        self.assertEqual(r['l5'].split('_')[0], 'Std-fabric-wx.440')
        self.assertEqual(len(r['l5'].split('_')), 5)
        self.assertEqual(r['tu'], '2.10')
        self.assertEqual(r['fll'], '2.2.1757.60_5.1.1301.36', 'per step: flush renders, their ms, the programs they added')
        self.assertEqual(r['gw'], '4.6.116.0.0.9')
        self.assertEqual(r['gi'], '2.29.15_5.3.9')
        self.assertEqual(r['gy'], '155.695.225.14.12')
        self.assertEqual(r['gf'], '14.3.410.1894.372.5.1.2.0', 'and the ms the fence calls took, and the state')
        self.assertEqual((r['hd'], r['hn'], r['bl']), (4200, 1, 3100))
        self.assertEqual(r['cap'], 'absk.16384.4')
        self.assertEqual(o['asked'], 0, 'the extensions are read from the list, never asked for')
        self.assertEqual(r['db'], '2240x1260')
        self.assertEqual(r['gbf'], '0.0.0.0.3.0')
        self.assertEqual(r['on'], '1.250')
        self.assertEqual((r['an'], r['wn']), (2, 0))
        e = o['enter']
        self.assertEqual(e, {'cold': 1, 'f1p': 3, 'f1k': '3.6.3.183.0.0', 'f1t': '1.4', 'f15': 'Sha-wx-halo2.65_Sha-wx-halo1.64_Sha-wx-halo0.63', 'lit': 2017, 'eb': 1})
        self.assertEqual(o['off'], [False, 0], 'composing the enter beacon takes the wraps off if the frame never did')
        p = o['perf']
        self.assertEqual(p, {'stl': '3.2100.2.1800.1300', 'prg': 15, 'db': '2240x1260', 'gbf': '0.0.0.0.3.0', 'pl': '40.173', 'pt': '6.2463.148.35.2', 'eh': '1.89.9.1',
                             'js': '0.8.42.9.1.400', 'fgl': '580.4.162.394', 'trm': 39.8, 'an': 2})
        self.assertEqual(o['late'], o['settled'])
        self.assertEqual(o['late'], ','.join(p.keys()))

    def test_nothing_a_query_escapes_and_no_url(self):
        # a colon or a comma costs three bytes in a query: the lists are dots and underscores
        for st in ('ready', 'enter', 'perf', 'bail'):
            for k, v in self.o[st].items():
                s = str(v)
                self.assertRegex(s, r'^[A-Za-z0-9._-]*$', '%s.%s = %r' % (st, k, v))
                self.assertEqual(urllib.parse.quote(s, safe='*-._'), s)
                self.assertNotIn('http', s.lower())
                self.assertNotIn('www', s.lower())
        # nothing personal is read: no GPU name, no address, no agent string
        for bad in ('UNMASKED', 'WEBGL_debug_renderer_info', 'userAgent', 'location.href', 'location.host', 'document.referrer', 'navigator.'):
            self.assertNotIn(bad, BLOCK)
        for bad in BAD:
            self.assertNotIn(bad, BLOCK)

    def test_the_longest_beacon_fits_the_request_line(self):
        """The ready beacon whole, composed by the page's own beacon(), readyFacts, gpuMemField and measFacts, at the worst
        this build could send: 48 steps that all flushed and all yielded inside, five 30-character tags, an 80-character
        crumb, every number at its widest. MEASURED on a headless load it is 1,050 bytes on a computer (1,157 when cold,
        with its five programs) and 1,049 on the phone path; nginx logs a request line of 8 KB."""
        both = cut(SRC, '  function beaconQuery(st, extra) {', '\n  }\n', inclusive=True)
        ready = cut(SRC, '  function readyFacts(safe) {', '\n  }\n', inclusive=True)
        i = SRC.index('  function gpuMemField() {')
        gmf = SRC[i:SRC.index('\n  }\n', i) + 5]
        o = node(self, r'''
const sent = [];
const BEACON = 'https://philly3d.com/b', beaconSeen = new Set(); let beaconErrs = 0;
window.devicePixelRatio = 3; window.matchMedia = () => ({ matches: true });
const navigator = { hardwareConcurrency: 16, deviceMemory: 8, standalone: true };
document.lastModified = '11/10/2026 20:00:00';
const NAV = { type: 'navigate', transferSize: 14200000, encodedBodySize: 13050000, decodedBodySize: 30440000, requestStart: 12.5, responseEnd: 16850.2, domInteractive: 17700.7, workerStart: 1, fetchStart: 15, responseStart: 16012 };
performance.getEntriesByType = (t) => (t === 'navigation' ? [NAV] : t === 'paint' ? [{ name: 'first-contentful-paint', startTime: 1234.6 }] : []);
const fetch = (url) => { sent.push(url); return { catch() {} }; };
BOTH
READY
GMF
const TIER = 2, LITE_WHY = 'cgtsxrupa';
const bootPrev = { step: 'Lettering the landmarks and the rest', ctx: 'q19,e19,f99999,m99999,w599999,gb9999,b9999,x9999,r9999,p999,l1' + 'x'.repeat(40) };
const zcField = () => 'rqca.1111.p0', pendingUpload = new Array(20), TSKIN = { ms: 12345 }, SF = { waitMs: 12345, preBlob: 1 };
Object.assign(GPUMEM, { peak: 2300 * 1048576, peakAt: 'Opening the Libr +199s', zrev: 136 * 1048576, att: () => 172 * 1048576 });
DPR.cur = 1.25;
const K = (c) => ['standard', 'highp', 3001, 0, '', 0, true, false, false, 0, 0, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 4, 0, 0, 3201, 1, 2, 3001, c].join();
gl.cost = { getError: 99 };
for (let k = 0; k < 190; k++) program(4000, 9000, 30000, 100);
renderer.info.programs = LINK.recs.map((r, k) => ({ program: r.p, name: 'MeshStandardMaterial', cacheKey: K('venue-texture-rich-n-' + (100 + k)) }));   // 24 characters: the longest key that rides whole
PERF.steps = []; PERF.flush = { n: 99, ms: 99999.6, p0: 140, p1: 190 }; PERF.staged = () => ({ n: 20, bytes: 44040192, mb: 142.5 });
for (let i = 0; i < 48; i++) { PERF.steps.push(['step ' + i, 99000 + i]); MEAS.gw[i] = 21000 + i; MEAS.gi.push(i + '.999.' + (21000 + i)); MEAS.flushes.push([i, 57000 + i, 190]); }
Object.assign(YLD, { n: 9999, ms: 999999, max: 99999, afN: 999, afMs: 99999 });
Object.assign(MEAS.fence, { n: 999, late: 999, lo: 999999, hi: 999999, max: 99999, at: 47, pend: 8, cms: 99999, st: 3 });
HID.n = 99; HID.ms = 999999; HID.bail = 999999; MEAS.artNull = 999; LINK.err = 999;
const COLD = { n: 999999 }; MEAS.pp = '5.1.' + new Array(12).fill(99999).join('.'); MEAS.ppk = 'Std-venue-texture-rich-n-12345';   // part two: a salted cold load that ran the link probe, every number at its widest
gl.ext = ['WEBGL_compressed_texture_astc', 'EXT_texture_compression_bptc', 'WEBGL_compressed_texture_s3tc', 'EXT_texture_compression_rgtc', 'WEBGL_compressed_texture_etc', 'WEBGL_compressed_texture_etc1', 'WEBKIT_WEBGL_compressed_texture_pvrtc', 'KHR_parallel_shader_compile', 'EXT_disjoint_timer_query_webgl2'];
for (let k = 0; k < 6; k++) sceneObjs.push({ isInstancedMesh: k === 3, geometry: { attributes: { position: { array: { byteLength: 9999 * 1048576 } } } }, material: { userData: { wxSurf: k === 2 } } });
outerMeshes.push(sceneObjs[0]); LANE_MATS.push(sceneObjs[1].material);
PERF.ready = 599999; NOW = 600000; measReady();
beacon('ready', { ms: 599999, fail: 48, sf: 'built' });
const q = Object.fromEntries(new URLSearchParams(sent[0].split('?')[1]));
console.log(JSON.stringify({ bytes: sent[0].length, q, keys: Object.keys(q).length }));
'''.replace('BOTH', both).replace('READY', ready).replace('GMF', gmf), touch=True)
        q = o['q']
        self.assertEqual(q['cold'], '1')
        self.assertEqual(q['gf'], '999.999.999999.999999.99999.47.8.99999.3')
        self.assertEqual(len(q['sp'].split(',')), 48)
        self.assertEqual(len(q['gw'].split('.')), 48)
        self.assertEqual(len(q['gi'].split('_')), 48)
        self.assertEqual(len(q['fll'].split('_')), 48)
        self.assertEqual(len(q['l5'].split('_')), 5)
        for e in q['l5'].split('_'):
            self.assertRegex(e, r'^Std-venue-texture-rich-n-\d{3}\.47000$')
        self.assertEqual(q['cap'], 'absre1pkt.16384.4')
        self.assertEqual(q['gbf'], '9999.9999.9999.9999.19998.0')
        self.assertEqual(q['gbs'], '911.844.89.172')
        self.assertEqual(len(q['pc']), 80)
        self.assertEqual((q['cs'], len(q['pp'].split('.')), q['ppk']), ('999999', 14, 'Std-venue-texture-rich-n-12345'), "part two: the salt's field and the link probe's two")
        for k in ('ws', 'fs', 'rs', 'lk', 'tu', 'gy', 'gf', 'hd', 'hn', 'bl', 'db', 'on', 'an', 'wn', 'sp', 'prg', 'fl', 'flms', 'flp', 'pu', 'pub', 'gb', 'gbp', 'gbw', 'gbm'):
            self.assertIn(k, q)
        # part two: the bound was 3,072 before the link probe's two fields and the salt's (pp, ppk, cs: 3,135 with every number
        # of theirs at its widest too, on a load that is salted, cold and probed at once)
        self.assertLess(o['bytes'], 3200, 'the longest beacon at its worst, well under nginx\'s 8 KB request line: %d' % o['bytes'])
        print('\n    the ready beacon at its worst: %d bytes, %d fields' % (o['bytes'], o['keys']))

    def test_a_fact_that_throws_costs_only_itself(self):
        o = node(self, r'''
PERF.ready = 1; NOW = 2000; measReady();
renderer.getContext = () => { throw new Error('lost'); };
MEAS.caps = null;
const r = measFacts('ready'), p = measFacts('perf');
console.log(JSON.stringify({ cap: r.cap, db: r.db, gbf: r.gbf, lk: r.lk, pdb: p.db, stl: p.stl }));
''')
        self.assertEqual(o, {'cap': '', 'db': '', 'gbf': '0.0.0.0.0.0', 'lk': '0.0.0.0.0.0.0', 'pdb': '', 'stl': '0.0.0.0.0'})


class Wiring(unittest.TestCase):
    def test_the_beacon_spreads_the_facts(self):
        both = cut(SRC, '  function beaconQuery(st, extra) {', '\n  }\n', inclusive=True)
        a = "    if (st === 'ready') Object.assign(q, safe(() => readyFacts(safe), {}));"
        b = "    Object.assign(q, safe(() => measFacts(st), {}));"
        self.assertIn(b, both)
        self.assertLess(both.index(a), both.index(b))
        self.assertLess(both.index(b), both.index('if (extra) for (const k in extra)'), "a call's own fields still win")
        self.assertIn("ws: nv('workerStart'), fs: nv('fetchStart'), rs: nv('responseStart'),", both)

    def test_the_build_loop(self):
        b = cut(SRC, '  async function build() {', '\n  }\n')
        self.assertIn("      bootMark(s.msg);\n      const yw = stepYield(builtSteps - 1);", b)
        self.assertIn("      await yieldNow();\n      stepWaited(yw);\n      const t0 = performance.now();", b, "the step's ms still starts after its yield")
        self.assertIn("      PERF.steps.push([s.msg, Math.round(performance.now() - t0)]);\n      stepDone(yw);", b)

    def test_the_frame(self):
        f = cut(SRC, '  function frame(now, once) {', '\n  }\n')
        self.assertIn("    pinOccPoll();", f)
        i = f.index('    const tj1 = performance.now();')
        self.assertLess(f.index('    pinOccPoll();'), i)
        self.assertIn('    const tj1 = performance.now();   // Round 229: the marks that split the JavaScript before the draw (measJs)\n    measFrame(rawMs, once);', f)
        order = ['const tj1 = ', 'applyLighting();', 'const tj2 = performance.now();\n    updateTransit(now, dt);', 'updateTraffic(now, dt);', 'const tj3 = performance.now();',
                 'updateHash(now);\n    const tj4 = performance.now();\n    pinOccUpdate(dt);\n    const tPre = performance.now();', 'measJs(tFrame, tj1, tj2, tj3, tj4, tPre);', 'if (LINK.on || !MEAS.lit) measLit();', 'if (!ENTER.lit) enterLight();']
        at = [f.index(x) for x in order]
        self.assertEqual(at, sorted(at))
        # the third part ends with the traffic and, on the line after it, the walkers (Round 227, behind ?people=1): they
        # read the traffic's runs and its view, so their fill is timed with it and not with the steps after
        body = [ln.split('   //')[0] for ln in f.splitlines()]
        k = body.index('    updateTraffic(now, dt);')
        self.assertEqual(body[k + 1:k + 3], ['    if (PEOPLE_ON) peopleStep(now);', '    const tj3 = performance.now();'])
        self.assertEqual(f.count('measLit()'), 1)
        # a cold load's wraps come off before the button can light, on the line before it (a warm load's went at Ready, and
        # the frame's snapshot is taken either way)
        lines = [ln.split('   //')[0] for ln in f.rstrip().splitlines()]
        self.assertEqual(lines[-2:], ['    if (LINK.on || !MEAS.lit) measLit();', '    if (!ENTER.lit) enterLight();'])
        m = cut(BLOCK, '  function measLit() {', '\n  }\n')
        self.assertLess(m.index('LINK.off();'), m.index('if (MEAS.lit) return;'))

    def test_the_small_counters(self):
        self.assertIn("else { MEAS.artNull++; res(null); } }; im.src = src; };", cut(SRC, '  function artImage(src) {', '\n  }\n'))
        self.assertIn("if (!src) { res(null); return; }", cut(SRC, '  function artImage(src) {', '\n  }\n'), 'no source asked is not a load that failed')
        self.assertIn("const tr0=performance.now();trafficReconcile(now);const trMs=performance.now()-tr0;if(trMs>MEAS.traf)MEAS.traf=trMs;", SRC)
        self.assertEqual(SRC.count('trafficReconcile(now);'), 1)
        occ = cut(SRC, '  function occRender(rt, W, H, buf, noInstanced, cam = camera, read = null, noFlats = false) {', '\n  const occUnpack')
        self.assertIn("const r = renderer, hid = [], stood = [], tOcc = performance.now();", occ)
        cap = "    if (pinLab) capNote(pinLab === 'pinsnear', performance.now() - tOcc, r.info && r.info.render);"
        self.assertIn(cap, occ)
        self.assertLess(occ.index('r.render(scene, cam);'), occ.index(cap))
        self.assertLess(occ.index(cap), occ.index('if (read) out = read(); else r.readRenderTargetPixels'), "before the read: a synchronous read is pos's, not the capture's")

    def test_a_computer_s_lost_context_is_beaconed(self):
        h = cut(SRC, "  canvas.addEventListener('webglcontextlost', (e) => {", '\n  });\n')
        line = "    if (!isTouch) beacon('ctxlost', { f: document.visibilityState === 'visible' && performance.now() - shownAt > 5000 ? 1 : 0, ms: Math.round(performance.now()), d: 1, ar: PERF.ready ? 1 : 0, ae: PERF.enterT ? 1 : 0 });"
        self.assertIn(line, h)
        self.assertEqual(h.count("beacon('ctxlost'"), 3, "the phone's two, and the computer's")
        self.assertLess(h.index(line), h.index("el.style.display = 'flex';"))
        self.assertIn("Reload the page to continue exploring.", h, 'what the visitor is told is as it was')
        # run: a computer's loss makes no reload and one beacon
        ctx = cut(SRC, "  canvas.addEventListener('webglcontextlost', (e) => {", '\n  });\n', inclusive=True)
        o = run_node(self, r'''
const out = {};
for (const [touch, ready, enterT] of [[false, 29000, 33000], [false, 0, 0]]) {
  let lost = null; const beacons = [], el = { style: {}, firstElementChild: {} };
  const canvas = { addEventListener: (t, f) => { lost = f; } }, document = { visibilityState: 'visible', getElementById: () => el, addEventListener() {} };
  const performance = { now: () => 60000 }, PERF = { ready, enterT }, isTouch = touch, window = { removeEventListener() {} }, location = { reload: () => beacons.push('RELOAD') };
  const beacon = (st, x) => beacons.push([st, x]); let glDead = false, shownAt = 0, bootHeld = false; const bootClear = () => {}, bootMark = () => {}, sessionStorage = { getItem: () => null, setItem() {} };
  CTX
  lost({ preventDefault() {} });
  out[ready ? 'running' : 'building'] = { beacons, dead: glDead, shown: el.style.display, text: el.firstElementChild.innerHTML };
}
console.log(JSON.stringify(out));
'''.replace('CTX', ctx))
        self.assertEqual(o['running']['beacons'], [['ctxlost', {'f': 1, 'ms': 60000, 'd': 1, 'ar': 1, 'ae': 1}]])
        self.assertEqual(o['building']['beacons'], [['ctxlost', {'f': 1, 'ms': 60000, 'd': 1, 'ar': 0, 'ae': 0}]])
        self.assertEqual((o['running']['dead'], o['running']['shown']), (True, 'flex'))
        self.assertIn('Reload the page', o['running']['text'])


class BeaconsPy(unittest.TestCase):
    """The capture skill's log reader learns every new field (--all)."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('beacons_py', BEACONS_PY)
        cls.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.m)

    def test_decode(self):
        d = self.m.decode
        self.assertEqual(d('lk', '144.0.1.3706.52.496.23'), {'programs': 144, 'compile_ms': 0, 'link_ms': 1, 'query_ms': 3706, 'intro_ms': 52, 'drain_ms': 496, 'median_ms': 23})
        self.assertEqual(d('fll', '10.5.2757.60_39.1.2534.40'), [{'step': 10, 'flushes': 5, 'ms': 2757, 'programs': 60}, {'step': 39, 'flushes': 1, 'ms': 2534, 'programs': 40}])
        self.assertEqual(d('l5', 'Std-fabric-wx.112_Sha-f14332.13'), [('Std-fabric-wx', 112), ('Sha-f14332', 13)])
        self.assertEqual(d('gw', '4.6.116.1.225'), {'steps': 5, 'ms': 352, 'longest': [(4, 225), (2, 116), (1, 6), (0, 4), (3, 1)]})
        self.assertEqual(d('cap', 'absk.16384.4'), {'formats': ['ASTC', 'BPTC', 'S3TC', 'parallel-compile'], 'max_texture': 16384, 'max_samples': 4})
        self.assertEqual(d('cap', '0.4096.4')['formats'], [])
        self.assertEqual(d('gbs', '911.844.89.120'), {'buffers_mb': 911, 'textures_mb': 844, 'renderbuffers_mb': 89, 'attached_mb': 120})
        self.assertEqual(d('db', '2240x1260'), '2240x1260')
        self.assertEqual(d('gi', ''), '')
        # the fences: the review's two numbers, and a line from before them still reads
        self.assertEqual(d('gf', '14.14.16.1780.4.11.0.2.0'), {'fences': 14, 'late': 14, 'lo_ms': 16, 'hi_ms': 1780, 'longest_lo_ms': 4, 'step': 11, 'pending': 0, 'call_ms': 2, 'state': 'laid'})
        self.assertEqual(d('gf', '1.0.0.0.0.-1.0.73.1')['state'], 'stopped-at-a-slow-call')
        self.assertEqual(d('gf', '0.0.0.0.0.-1.0.0.2')['state'], 'never-laid-here')
        self.assertEqual(d('gf', '0.0.0.0.0.-1.0.0.3')['state'], 'no-fenceSync')
        self.assertEqual(d('gf', '14.3.410.1894.372.5.1'), {'fences': 14, 'late': 3, 'lo_ms': 410, 'hi_ms': 1894, 'longest_lo_ms': 372, 'step': 5, 'pending': 1})
        # the cold line cut again from the median program
        c = self.m.cold_of
        self.assertEqual([c({'cold': '1', 'lk': '144.0.1.4280.45.0.45'}), c({'cold': '0'}), c({}), c({'cold': ''})], ['cold', 'warm', '', ''], "the page's own flag")
        self.assertEqual(c({'cold': '1', 'lk': '144.0.1.4280.45.0.45'}, 60), 'warm', "a load the first cut's 40 ms called cold")
        self.assertEqual(c({'cold': '0', 'lk': '144.0.1.4280.45.0.74'}, 60), 'cold')
        self.assertEqual(c({'cold': '', 'lk': '4.0.0.9.0.0.2'}, 60), '', 'under ten programs there is no verdict to cut again')
        self.assertEqual(c({'cold': '1'}, 60), '')
        # every field measFacts sends is one the reader prints under --all
        facts = cut(BLOCK, '  function measFacts(st) {', '\n  }\n')
        sent = set(re.findall(r"[{,] (\w+): ", facts)) | set(re.findall(r"\bo\.(\w+) = ", facts))
        sent -= {'cold'} - set(self.m.READY2)
        known = set(self.m.READY2) | set(self.m.ENTER2) | set(self.m.RUN2)
        self.assertEqual(sent - known, set(), 'a field the page sends and beacons.py does not print')
        for k in ('lk', 'f1k', 'tu', 'f1t', 'gy', 'gf', 'gbs', 'gbf', 'on', 'stl', 'pl', 'pt', 'eh', 'js', 'fgl'):
            self.assertIn(k, self.m.FIELDS)

    def test_a_log(self):
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        def line(ip, **q):
            return '%s - - [10/Nov/2026:16:00:00 +0000] "POST /b?%s HTTP/2.0" 404 0 "-" "%s"\n' % (ip, urllib.parse.urlencode(q), ua)
        log = ''.join([
            # a cold computer: hidden once, its bail, then Ready, Enter and a perf line
            line('1.1.1.1', st='boot', t=900, tch=0, tier=0, cores=12, ms=400, pc='q6,e2,f41,m48,w900,gb871,b520,x260,r91,p165,l1', pv='ready'),
            line('1.1.1.1', st='bail', t=5000, tch=0, tier=0, step='Raising the Outer Districts', cold=''),
            line('1.1.1.1', st='step:Raising the outer districts', t=20000, tch=0, tier=0, ms=15000),
            line('1.1.1.1', st='ready', t=60000, tch=0, tier=0, ms=59000, cold=1, lk='144.0.1.48000.52.496.330', l5='Std-fabric-wx.812_Sha-f14332.640', fll='10.5.27570.60', gw='4.6.116', gf='14.3.410.1894.372.5.1',
                 hd=12000, hn=1, bl=5000, cap='bs.16384.8', db='1920x1080', gbs='911.844.89.120', gbf='459.177.92.28.153.0'),
            line('1.1.1.1', st='enter', t=70000, tch=0, tier=0, ms=70000, cold=1, f1p=24, f1k='27.0.0.9000.3.82', lit=9100, eb=0),
            line('1.1.1.1', st='perf', t=130000, tch=0, tier=0, p50=50, stl='3.2100.2.1800.1300', js='4.8.172.99.60.440', eh='0.87.13.0', trm='39.8', gbs='924.1153.99.144'),
            # a warm one
            line('2.2.2.2', st='step:Raising the outer districts', t=9000, tch=0, tier=0, ms=6000),
            line('2.2.2.2', st='ready', t=26000, tch=0, tier=0, ms=25500, cold=0, lk='144.0.0.3231.51.0.9'),
            # a bail that no Ready followed, and a computer that lost its context
            line('3.3.3.3', st='bail', t=7000, tch=0, tier=0, step='Fitting Streets', cold=0),
            line('4.4.4.4', st='ctxlost', t=400000, tch=0, tier=0, f=1, d=1, ar=1, ae=1, gb=2176, gbs='924.1153.99.144'),
        ])
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write(log)
        argv = sys.argv
        buf = io.StringIO()
        try:
            sys.argv = ['beacons.py', f.name, '--all']
            with redirect_stdout(buf):
                self.m.main()
        finally:
            sys.argv = argv
            Path(f.name).unlink()
        out = buf.getvalue()
        self.assertIn("bail at t=5000 step='Raising the Outer Districts' cold=: ready came later, at t=60000 (hidden 12000 ms in 1)", out)
        self.assertIn("bail at t=7000 step='Fitting Streets' cold=0: no ready followed", out)
        self.assertIn('ctxlost at t=400000 front=1 computer=1 after_ready=1 after_enter=1 gb=2176 gbs=924.1153.99.144', out)
        self.assertIn("'lk': {'programs': 144, 'compile_ms': 0, 'link_ms': 1, 'query_ms': 48000, 'intro_ms': 52, 'drain_ms': 496, 'median_ms': 330}", out)
        self.assertIn("'l5': [('Std-fabric-wx', 812), ('Sha-f14332', 640)]", out)
        self.assertIn("'cap': {'formats': ['BPTC', 'S3TC'], 'max_texture': 16384, 'max_samples': 8}", out)
        self.assertIn("last session's crumb (pc): q6,e2,f41,m48,w900,gb871,b520,x260,r91,p165,l1 at step ready", out)
        self.assertIn("enter, round two: {'cold': '1', 'f1p': '24', 'f1k': {'programs': 27, 'compile_ms': 0, 'link_ms': 0, 'query_ms': 9000, 'intro_ms': 3, 'drain_ms': 82}, 'lit': '9100', 'eb': '0'}", out)
        self.assertIn("'stl': {'stalls': 3, 'ms': 2100, 'with_programs': 2, 'with_programs_ms': 1800, 'longest_ms': 1300}", out)
        # cold and warm loads are reduced apart
        self.assertIn("('desk', 'Win', '0', 'cold') n= 1", out)
        self.assertIn("('desk', 'Win', '0', 'warm') n= 1", out)
        self.assertIn(' cold: t0=1000 ', out)
        # --coldms cuts the line again from the median program: at 400 the 330 ms load is warm too
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write(log)
        buf = io.StringIO()
        try:
            sys.argv = ['beacons.py', f.name, '--coldms=400']
            with redirect_stdout(buf):
                self.m.main()
        finally:
            sys.argv = argv
            Path(f.name).unlink()
        self.assertIn("('desk', 'Win', '0', 'warm') n= 2", buf.getvalue())
        self.assertNotIn("'cold')", buf.getvalue())


if __name__ == '__main__':
    unittest.main()
