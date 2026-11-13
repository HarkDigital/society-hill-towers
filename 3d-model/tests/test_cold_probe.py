"""Round 229, measurement round two, part two (Stage 1 of the Nov 10 plan): cold runs on demand and the link probe.

Two tools that answer one question, the one Stage 3 (linking ahead) is decided on: are programs issued together and then
awaited faster than the same programs linked one at a time? Nothing drawn changes and no GLSL string in app.js is touched.

- ?cold=<n> salts every fragment shader where three hands its source to the context: the page's main is renamed and a new
  main runs one branch that is never taken and that no compiler can remove, so the browser's and the system's shader caches
  miss. Without the flag no wrap is installed and no source differs; the flag is read once, kept nowhere, never rides a
  copied link, and a salted load says so on every beacon (cs).
- The link probe runs as build() ends on a cold load alone (the link timers' own verdict, and the median as it stands at the
  call), once a device and build, or once a week where the page cannot tell its build (the app: the review): copies
  of one of the page's own programs, each salted, one linked and waited on, then three issued together and waited on, then
  one more, each followed by a first draw with its mesh's vertex layout into a small target of the frame's kind. It leaves
  nothing behind (every object deleted, every binding put back, no GL error), is in none of the link timers' counts, and
  reports serial ms, batched ms and where the wait landed on the ready beacon (pp, ppk).
- tests/prelink_gpu.html runs the same trial by hand on the built page's own context, and beacons.py reads the fields.

The blocks are cut from app.js and run under Node against a scripted WebGL context whose calls advance a scripted clock.
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
    from .test_recovery import run_node, cut          # python3 -m unittest tests.test_cold_probe
    from . import test_measure_two as M2
except ImportError:
    from test_recovery import run_node, cut           # python3 -m unittest discover -s tests
    import test_measure_two as M2

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
COLD = cut(SRC, '  // ---- Round 229 (Stage 1 of the Nov 10 plan, measurement round two, part two): cold runs on demand', '\n  let renderer;\n')
PROBE = cut(SRC, '  // ---- Round 229, measurement round two, part two: THE LINK PROBE', '  // ---- reversed-Z depth (Round 192, from perf spike 1)')
PAGE = (ROOT / 'tests' / 'prelink_gpu.html').read_text()
BEACONS_PY = ROOT.parent / '.claude' / 'skills' / 'philly3d-capture' / 'scripts' / 'beacons.py'
BAD = ('—', '–', '·')   # no em dash, en dash or middot

# three's own fragment prefix on WebGL 2 (r149), then a hook's body
THREE_FS = '''#version 300 es
#define varying in
layout(location = 0) out highp vec4 pc_fragColor;
#define gl_FragColor pc_fragColor
precision highp float;
uniform sampler2D map;
void shade(out vec4 c) { c = vec4(1.0); }
void main() {
  vec4 c; shade(c);
  gl_FragColor = c;
}
'''


def cold_node(test, body, search=''):
    """The ?cold block alone: two context classes whose prototypes it may wrap, and the address it reads."""
    pre = r'''
const PERF = {}, location = { search: SEARCH };
const calls = [];
class Ctx { createShader(type) { return { type }; } shaderSource(shader, src) { calls.push([this.tag, shader.type, src]); shader.src = src; return 'ss'; } }
class Ctx1 extends Object { createShader(type) { return { type }; } shaderSource(shader, src) { shader.src = src; } }
const ORIG = { cs: Ctx.prototype.createShader, ss: Ctx.prototype.shaderSource };
const window = { WebGLRenderingContext: Ctx1, WebGL2RenderingContext: Ctx };
'''.replace('SEARCH', json.dumps(search))
    return run_node(test, pre + COLD + body)


class Salt(unittest.TestCase):
    def test_the_salt_is_a_branch_never_taken_on_the_shader_s_own_output(self):
        o = cold_node(self, r'''
const T = FS;
const a = coldSalt(T, 7), b = coldSalt(T, 123456);
const raw3 = '#version 300 es\nprecision mediump float;\nin vec2 vUv;\nout mediump vec4 fragOut;\nvoid main(void) { fragOut = vec4(vUv, 0.0, 1.0); }\n';
const es1 = 'precision mediump float;\nvoid  main ( ) { gl_FragColor = vec4(1.0); }\n';
const mrt1 = 'precision mediump float;\nvoid main() { gl_FragData[0] = vec4(1.0); }\n';
const flt = '#version 300 es\nprecision highp float;\nout float d;\nvoid main() { d = 1.0; }\n';
console.log(JSON.stringify({ a, b, raw3: coldSalt(raw3, 5), es1: coldSalt(es1, 5), mrt1: coldSalt(mrt1, 5), flt: coldSalt(flt, 5),
  noMain: coldSalt('precision highp float;\nfloat f() { return 1.0; }\n', 5), intOut: coldSalt('#version 300 es\nout ivec4 o;\nvoid main() { o = ivec4(1); }\n', 5),
  twice: coldSalt(a, 123456) === b, again: coldSalt(coldSalt(T, 7), 7) === a, cond: [coldCond(1), coldCond(999), coldCond(1000), coldCond(999999)] }));
'''.replace('FS', json.dumps(THREE_FS)))
        a = o['a']
        tail = '\nvoid main() { p3dColdMain(); if (gl_FragCoord.x < -7.5 && gl_FragCoord.y < -0.5) pc_fragColor = vec4(0.0); }\n'
        self.assertTrue(a.endswith(tail), a[-200:])
        self.assertEqual(a[:-len(tail)], THREE_FS.replace('void main()', 'void p3dColdMain()'), "the page's own text, its main renamed and nothing else")
        self.assertEqual(a.count('void main('), 1)
        self.assertNotIn('discard', a[len(THREE_FS):], 'no discard: it would cost the early depth test on every salted program')
        self.assertNotIn('gl_FragDepth', a)
        self.assertTrue(o['b'].endswith('if (gl_FragCoord.x < -456.5 && gl_FragCoord.y < -123.5) pc_fragColor = vec4(0.0); }\n'))
        # the sink is the shader's own first float output, whatever it is called
        self.assertIn('void p3dColdMain() { fragOut = vec4(vUv, 0.0, 1.0); }', o['raw3'])
        self.assertTrue(o['raw3'].endswith(') fragOut = vec4(0.0); }\n'))
        self.assertTrue(o['es1'].endswith(') gl_FragColor = vec4(0.0); }\n'))
        self.assertIn('void p3dColdMain() { gl_FragColor = vec4(1.0); }', o['es1'])
        self.assertTrue(o['mrt1'].endswith(') gl_FragData[0] = vec4(0.0); }\n'), 'a shader may write only one of gl_FragColor and gl_FragData')
        self.assertTrue(o['flt'].endswith(') d = float(0.0); }\n'))
        self.assertIsNone(o['noMain'])
        self.assertIsNone(o['intOut'], 'no float output to write: the caller falls back to a comment and counts it')
        self.assertTrue(o['twice'], 'a salted source only has its constants moved (the link probe salts copies of a ?cold page\'s programs)')
        self.assertTrue(o['again'])
        self.assertEqual(o['cond'], ['gl_FragCoord.x < -1.5 && gl_FragCoord.y < -0.5', 'gl_FragCoord.x < -999.5 && gl_FragCoord.y < -0.5',
                                     'gl_FragCoord.x < -0.5 && gl_FragCoord.y < -1.5', 'gl_FragCoord.x < -999.5 && gl_FragCoord.y < -999.5'])

    def test_every_n_is_its_own_program(self):
        o = cold_node(self, r'''
const seen = new Set(); let bad = 0;
for (let n = 1; n <= 999999; n++) { const c = coldCond(n); if (seen.has(c)) bad++; seen.add(c); }
const m = /x < -(\d+)\.5 && gl_FragCoord\.y < -(\d+)\.5$/;
let over = 0; for (const c of seen) { const k = m.exec(c); if (!k || +k[1] > 999 || +k[2] > 999) over++; }
console.log(JSON.stringify({ n: seen.size, bad, over }));
''')
        self.assertEqual(o, {'n': 999999, 'bad': 0, 'over': 0}, 'a million distinct pairs, each constant exact in a 16-bit float (under 1024, a half apart)')

    def test_without_the_flag_nothing_is_installed(self):
        for search in ('', '?dev=1&dpr=1', '?cold=0', '?coldms=0', '?dev=1&coldms=80', '?uncold=5', '?cold=', '?cold=x7'):
            o = cold_node(self, r'''
const g = new Ctx(); g.tag = 'a';
const f = g.createShader(0x8B30); g.shaderSource(f, FS);
console.log(JSON.stringify({ n: COLD.n, same: Ctx.prototype.createShader === ORIG.cs && Ctx.prototype.shaderSource === ORIG.ss && Ctx1.prototype.shaderSource.toString().indexOf('coldSalt') < 0,
  src: f.src === FS, salt: PERF.salt === COLD, salted: COLD.salted }));
'''.replace('FS', json.dumps(THREE_FS)), search)
            self.assertEqual(o, {'n': 0, 'same': True, 'src': True, 'salt': True, 'salted': 0}, search)

    def test_with_it_every_fragment_shader_is_salted_and_no_vertex_shader(self):
        o = cold_node(self, r'''
const g = new Ctx(); g.tag = 'a';
const v = g.createShader(0x8B31), f = g.createShader(0x8B30), f2 = g.createShader(0x8B30), f3 = g.createShader(0x8B30), f4 = g.createShader(0x8B30);
const VS = '#version 300 es\nin vec3 position;\nvoid main() { gl_Position = vec4(position, 1.0); }\n';
const ret = g.shaderSource(v, VS); g.shaderSource(f, FS);
const pre = coldSalt(FS, 4242); g.shaderSource(f2, pre);           // salted already (the link probe's copy): as it is
g.shaderSource(f3, '#version 300 es\nout ivec4 o;\nvoid main() { o = ivec4(1); }\n');   // cannot be salted: a comment, and counted
g.shaderSource(f4, FS);
const g1 = new Ctx1(), f5 = g1.createShader(0x8B30); g1.shaderSource(f5, FS);   // the other context class too (WebGL 1)
console.log(JSON.stringify({ n: COLD.n, ret, v: v.src === VS, f: f.src === coldSalt(FS, COLD.n), f2: f2.src === pre, f3: f3.src, f4: f4.src === f.src, f5: f5.src === f.src,
  salted: COLD.salted, missed: COLD.missed, self: calls.every((c) => c[0] === 'a') }));
'''.replace('FS', json.dumps(THREE_FS)), '?dev=1&cold=31')
        self.assertEqual(o['n'], 31)
        self.assertEqual(o['ret'], 'ss', "the call's own return")
        self.assertTrue(o['v'], 'a vertex shader is the page\'s own text')
        self.assertTrue(o['f'] and o['f4'] and o['f5'])
        self.assertTrue(o['f2'], 'a source that already carries a salt passes as it is')
        self.assertEqual(o['f3'], '#version 300 es\nout ivec4 o;\nvoid main() { o = ivec4(1); }\n\n// cold 31\n')
        self.assertEqual((o['salted'], o['missed']), (3, 1))
        self.assertTrue(o['self'])

    def test_the_flag_s_number(self):
        for search, n in (('?cold=1', 1), ('?dev=1&cold=999999', 999999), ('?cold=1000000', 1), ('?cold=1000007&dev=1', 8), ('?cold=7.5', 0), ('?cold=31#x', 31)):
            self.assertEqual(cold_node(self, 'console.log(JSON.stringify(COLD.n));', search), n, search)

    def test_it_cannot_ship_salted(self):
        # read once, from the address, and kept nowhere
        self.assertEqual(SRC.count('[?&]cold=('), 1, 'the flag is read in one place')
        code = '\n'.join(l for l in COLD.split('\n') if not l.lstrip().startswith('//'))
        for bad in ('localStorage', 'sessionStorage', 'keepSet', 'document.cookie', 'history.', 'viewState'):
            self.assertNotIn(bad, code)
        self.assertIn('if (COLD.n) {\n    const frag = new WeakSet();', COLD, 'the wraps are laid only under the flag')
        self.assertLess(SRC.index('const COLD = PERF.salt = '), SRC.index('\n  let renderer;\n'), 'before the first context exists (the reversed-Z probe\'s throwaway one)')
        # a copied link never carries it (the site's Copy Link carries the rest of the query)
        q = cut(SRC, '  const shareQuery = () => {', '\n  };\n')
        # the review: nor ?coldms, which would have the other device read cold, probe, and beacon both as a visitor's
        self.assertIn(".replace(/[?&](?:cold|coldms|probe)=[^&#]*/g, '').replace(/[?&]gfx=[^&#]*/g, '').replace(/^&/, '?')", q)
        strip = lambda x: re.sub(r'^&', '?', re.sub(r'[?&]gfx=[^&#]*', '', re.sub(r'[?&](?:cold|coldms|probe)=[^&#]*', '', x)))
        self.assertEqual([strip(x) for x in ('?cold=7', '?cold=7&dev=1', '?dev=1&cold=7&probe=1', '?wx=snow&probe=0&gfx=auto&dev=1', '?coldms=0', '?dev=1&coldms=80&wx=fog', '?dev=1', '?uncold=5&scold=1')],
                         ['', '?dev=1', '?dev=1', '?wx=snow&dev=1', '', '?dev=1&wx=fog', '?dev=1', '?uncold=5&scold=1'])
        for fn in ('  function writePrefs() {', '  function viewState('):
            self.assertNotIn('COLD', cut(SRC, fn, '\n  }\n'))

    def test_a_salted_load_says_so_on_every_beacon(self):
        both = cut(SRC, '  function beaconQuery(st, extra) {', '\n  }\n', inclusive=True)
        line = "    { const cs = safe(() => COLD.n, 0); if (cs) q.cs = cs; }"
        self.assertIn(line, both)
        self.assertLess(both.index("Object.assign(q, safe(() => measFacts(st), {}));"), both.index(line))
        self.assertLess(both.index(line), both.index('if (extra) for (const k in extra)'))
        script = r'''
const sent = [];
const BEACON = '/b', beaconSeen = new Set(); let beaconErrs = 0;
const window = { devicePixelRatio: 1, matchMedia: () => ({ matches: false }) }, navigator = {}, document = { lastModified: 'x' }, location = { search: '' };
const performance = { now: () => 5, getEntriesByType: () => [] };
const fetch = (url) => { sent.push(url); return { catch() {} }; };
BOTH
beacon('boot');                       // before COLD's own line has run: the TDZ, and nothing is added
DECL
beacon('ready'); beacon('perf');
console.log(JSON.stringify(sent.map((u) => new URLSearchParams(u.split('?')[1]).get('cs'))));
'''.replace('BOTH', both)
        self.assertEqual(run_node(self, script.replace('DECL', 'const COLD = { n: 31 };')), [None, '31', '31'])
        self.assertEqual(run_node(self, script.replace('DECL', 'const COLD = { n: 0 };')), [None, None, None], 'nothing on any other load')


# ---- the link probe: the measurement block's world (tests/test_measure_two.py's prelude) with a WebGL 2 context that keeps
# its objects, its bindings and a clock. ENGINE says how it links: 'parallel' (each link done L ms after it was issued, the
# status query waits: Chromium), 'stream' (links run one after another and ANY synchronous call waits for them all: what
# WebKit's GPU process does) or 'block' (the link call itself waits). A program's first draw queues D ms, any other 1.
WORLD = r'''
const E = { VERTEX_SHADER: 0x8B31, FRAGMENT_SHADER: 0x8B30, CURRENT_PROGRAM: 0x8B8D, VERTEX_ARRAY_BINDING: 0x85B5, ARRAY_BUFFER_BINDING: 0x8894, DRAW_FRAMEBUFFER_BINDING: 0x8CA6, READ_FRAMEBUFFER_BINDING: 0x8CAA,
  RENDERBUFFER_BINDING: 0x8CA7, VIEWPORT: 0x0BA2, MAX_SAMPLES: 0x8D57, FRAMEBUFFER: 0x8D40, DRAW_FRAMEBUFFER: 0x8CA9, READ_FRAMEBUFFER: 0x8CA8, RENDERBUFFER: 0x8D41, RGBA8: 0x8058, RGBA16F: 0x881A,
  DEPTH32F_STENCIL8: 0x8CAD, DEPTH24_STENCIL8: 0x88F0, COLOR_ATTACHMENT0: 0x8CE0, DEPTH_STENCIL_ATTACHMENT: 0x821A, FRAMEBUFFER_COMPLETE: 0x8CD5, ARRAY_BUFFER: 0x8892, STATIC_DRAW: 0x88E4, TRIANGLES: 4 };
let ENGINE = 'parallel', L_MS = 300, D_MS = 100;
const UNIFORMS = [{ name: 'map', type: 0x8B5E, size: 1 }, { name: 'uGain', type: 0x1406, size: 1 }, { name: 'shadowMap[0]', type: 0x8B62, size: 2 }, { name: 'envMap', type: 0x8B60, size: 1 }, { name: 'tVol', type: 0x8B5F, size: 1 }];
const ATTRIBS = ['position', 'normal', 'color', 'aFacade', 'aId', 'instanceColor'];
class GL2 {
  constructor() {
    Object.assign(this, E);
    this.log = []; this.live = new Set(); this.ids = 0; this.busy = 0; this.queue = 0; this.errq = []; this.asked = 0; this.linkOk = true; this.fbStatus = E.FRAMEBUFFER_COMPLETE;
    this.ext = ['EXT_color_buffer_float', 'KHR_parallel_shader_compile'];
    this.b = { prog: { was: 'three\'s program' }, vao: { was: 'three\'s vao' }, ab: null, dfb: { was: 'postRT' }, rfb: null, rb: { was: 'rb' }, vp: [0, 0, 1280, 720] };
    this.uni = []; this.ptr = []; this.rbs = []; this.bufs = []; this.srcs = []; this.draws = [];
  }
  _n(kind) { const o = { kind, id: ++this.ids }; this.live.add(o); return o; }
  _sync() { if (ENGINE === 'stream') NOW = Math.max(NOW, this.busy); NOW += this.queue; this.queue = 0; }   // a synchronous call: the stream's links, then what is queued
  getSupportedExtensions() { return this.ext; }
  getExtension(n) { this.asked++; return this.ext.indexOf(n) >= 0 ? {} : null; }
  getShaderSource(s) { return s.src; }
  getParameter(e) { return e === E.CURRENT_PROGRAM ? this.b.prog : e === E.VERTEX_ARRAY_BINDING ? this.b.vao : e === E.ARRAY_BUFFER_BINDING ? this.b.ab : e === E.DRAW_FRAMEBUFFER_BINDING ? this.b.dfb : e === E.READ_FRAMEBUFFER_BINDING ? this.b.rfb : e === E.RENDERBUFFER_BINDING ? this.b.rb : e === E.VIEWPORT ? this.b.vp.slice() : e === E.MAX_SAMPLES ? 8 : null; }
  getError() { this.log.push('getError'); this._sync(); return this.errq.shift() || 0; }
  createShader(t) { const s = this._n('shader'); s.type = t; return s; }
  createProgram() { return this._n('program'); }
  shaderSource(s, src) { this.log.push('shaderSource'); s.src = src; this.srcs.push([s.type, src]); }
  compileShader() { this.log.push('compileShader'); }
  attachShader(p, s) { this.log.push('attachShader'); (p.sh = p.sh || []).push(s); }
  linkProgram(p) { this.log.push('linkProgram'); if (ENGINE === 'block') NOW += L_MS; else if (ENGINE === 'stream') this.busy = Math.max(this.busy, NOW) + L_MS; else p.done = NOW + L_MS; }
  getProgramParameter(p, e) {
    this.log.push('getProgramParameter:' + e.toString(16));
    if (e === 0x91B1) return this.extOn ? ENGINE !== 'parallel' || NOW >= p.done : null;   // COMPLETION_STATUS_KHR: never waits, and null until the extension is on
    this._sync();
    if (e === 0x8B82) { if (ENGINE === 'parallel') NOW = Math.max(NOW, p.done); return this.linkOk; }
    return e === 0x8B86 ? UNIFORMS.length : e === 0x8B89 ? ATTRIBS.length : null;
  }
  getProgramInfoLog(p) { this.log.push('getProgramInfoLog'); this._sync(); if (ENGINE === 'parallel') NOW = Math.max(NOW, p.done); return ''; }
  getActiveUniform(p, i) { this.log.push('getActiveUniform'); return UNIFORMS[i]; }
  getUniformLocation(p, n) { this.log.push('getUniformLocation'); return { n }; }
  getActiveAttrib(p, i) { this.log.push('getActiveAttrib'); return { name: ATTRIBS[i] }; }
  getAttribLocation(p, n) { this.log.push('getAttribLocation'); return ATTRIBS.indexOf(n); }
  useProgram(p) { this.b.prog = p; }
  uniform1i(loc, v) { this.uni.push([this.b.prog.id || 0, loc.n, v]); }
  uniform1iv(loc, v) { this.uni.push([this.b.prog.id || 0, loc.n, Array.from(v)]); }
  createVertexArray() { return this._n('vao'); }
  bindVertexArray(v) { this.b.vao = v; }
  createBuffer() { return this._n('buffer'); }
  bindBuffer(t, b) { this.b.ab = b; }
  bufferData(t, n, u) { this.bufs.push(n); }
  enableVertexAttribArray() {}
  vertexAttribPointer(loc, size, type, norm, stride, off) { this.ptr.push(['f', ATTRIBS[loc], size, type, norm, stride, off]); }
  vertexAttribIPointer(loc, size, type, stride, off) { this.ptr.push(['i', ATTRIBS[loc], size, type, stride, off]); }
  createFramebuffer() { return this._n('fb'); }
  createRenderbuffer() { return this._n('rb'); }
  bindFramebuffer(t, f) { if (t !== E.READ_FRAMEBUFFER) this.b.dfb = f; if (t !== E.DRAW_FRAMEBUFFER) this.b.rfb = f; }
  bindRenderbuffer(t, r) { this.b.rb = r; }
  renderbufferStorageMultisample(t, n, fmt, w, h) { this.rbs.push([n, fmt, w, h]); }
  framebufferRenderbuffer() {}
  checkFramebufferStatus() { return this.fbStatus; }
  viewport(x, y, w, h) { this.b.vp = [x, y, w, h]; }
  drawArrays(mode, first, count) { this.log.push('drawArrays'); const p = this.b.prog; this.draws.push([p.id, mode, first, count, this.b.dfb.kind, this.b.vp.join()]); this.queue += p.drawn ? 1 : D_MS; p.drawn = true; }
  deleteVertexArray(o) { this.live.delete(o); } deleteBuffer(o) { this.live.delete(o); } deleteProgram(o) { this.live.delete(o); } deleteShader(o) { this.live.delete(o); }
  deleteFramebuffer(o) { this.live.delete(o); } deleteRenderbuffer(o) { this.live.delete(o); }
}
const g2 = new GL2(), BOUND0 = JSON.stringify(g2.b);
renderer.getContext = () => g2;
renderer.capabilities.isWebGL2 = true;
renderer.properties = { get: (m) => m.props || (m.props = {}) };
LINK.off(); linkInstall(g2);   // the link timers' instance wraps on this context, as on the page's
const POST = { on: true }, ZREV = { on: true };
let glDead = false, IN_APP = false;
let WALL = Date.parse('11/12/2026 09:30:00'); Date.now = () => WALL;   // the wall clock, moved by hand (the document's date below is two days before it: a date the page can believe)
const store = new Map(), localStorage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => { store.set(k, String(v)); } };
document.lastModified = '11/10/2026 20:00:00';
const K = (c) => ['standard', 'highp', 3001, 0, '', 0, true, false, false, 0, 0, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 4, 0, 0, 3201, 1, 2, 3001, c].join();
const FS = THREE_FS, VS = '#version 300 es\nin vec3 position;\nvoid main() { gl_Position = vec4(position, 1.0); }\n';
// a material's program the way r149 and the page's own timers leave one: linked THROUGH the instance (so LINK holds its
// record, with ms the first status query's), its wrapper in renderer.info.programs and in the material's own map, and a
// mesh in the scene that wears it. Its geometry: plain floats, a normalized byte normal, an interleaved normalized short
// colour (a stride of four shorts), the facade's two non-normalized shorts, an integer id, and nothing for instanceColor
function wear(key, ms, geo) {
  const v = g2.createShader(E.VERTEX_SHADER), f = g2.createShader(E.FRAGMENT_SHADER), p = g2.createProgram();
  g2.shaderSource(v, VS + '// ' + key + '\n'); g2.compileShader(v); g2.shaderSource(f, FS + '// ' + key + '\n'); g2.compileShader(f);
  g2.attachShader(p, v); g2.attachShader(p, f);
  const keep = [ENGINE, L_MS]; ENGINE = 'parallel'; L_MS = ms;
  g2.linkProgram(p); g2.getProgramInfoLog(p); g2.getProgramParameter(p, 0x8B82);
  ENGINE = keep[0]; L_MS = keep[1];
  const w = { program: p, vertexShader: v, fragmentShader: f, name: 'MeshStandardMaterial', cacheKey: K(key) }, mat = { props: { programs: new Map([[K(key), w]]) } };
  renderer.info.programs.push(w);
  const il = { array: new Uint16Array(12), stride: 4 };
  const mesh = { isMesh: true, material: mat, geometry: geo || { attributes: {
    position: { array: new Float32Array(9), itemSize: 3, normalized: false },
    normal: { array: new Int8Array(12), itemSize: 4, normalized: true },
    color: { isInterleavedBufferAttribute: true, data: il, itemSize: 3, offset: 0, normalized: true },
    aFacade: { array: new Int16Array(6), itemSize: 2, normalized: false },
    aId: { array: new Int32Array(3), itemSize: 1, normalized: false } } } };
  sceneObjs.push(mesh);
  return { w, mat, mesh, p };
}
const R1 = (v) => Math.round(v * 10) / 10;
const state = () => ({ live: g2.live.size, bound: JSON.stringify(g2.b) === BOUND0, n: LINK.n, recs: LINK.recs.length, info: renderer.info.programs.length, asked: g2.asked });
'''.replace('THREE_FS', json.dumps(THREE_FS))


def probe_node(test, body, search='', touch=False):
    """The measurement block (the probe is inside it) with the ?cold block and the probe's world laid after it."""
    return M2.node(test, COLD + WORLD + body, search=search, touch=touch)


class Layout(unittest.TestCase):
    def test_a_mesh_s_layout_is_the_gl_calls_three_makes(self):
        o = probe_node(self, r'''
const a = wear('fabric', 80);
const lay = lpLayout(a.mesh.geometry);
const show = (L) => L && Object.fromEntries(Object.keys(L).map((k) => [k, [L[k].type, L[k].size, L[k].norm, L[k].int, L[k].stride, L[k].off, L[k].bytes]]));
// an upload frees the arrays: famWalk noted each buffer's element type while it stood
famWalk(false);
const A = a.mesh.geometry.attributes;
for (const k in A) (A[k].data || A[k]).array = null;
const freed = lpLayout(a.mesh.geometry);
const never = lpLayout({ attributes: { position: { array: null, itemSize: 3 } } });                 // made and uploaded between two walks: unknown
const inst = lpLayout({ attributes: { position: { array: new Float32Array(9), itemSize: 3 }, aOff: { array: new Float32Array(9), itemSize: 3, isInstancedBufferAttribute: true } } });
const wide = lpLayout({ attributes: { m: { array: new Float32Array(48), itemSize: 16 } } });
const gpu = lpLayout({ attributes: { aK: { array: new Int16Array(6), itemSize: 2, gpuType: 1013 } } });
console.log(JSON.stringify({ lay: show(lay), same: JSON.stringify(show(freed)) === JSON.stringify(show(lay)), shared: lay.color.buf === A.color.data, never, inst, wide, gpu: show(gpu) }));
''')
        self.assertEqual(o['lay'], {
            'position': [5126, 3, False, False, 0, 0, 36],      # FLOAT, as three binds a plain attribute: stride and offset 0
            'normal': [5120, 4, True, False, 0, 0, 12],         # BYTE, normalized
            'color': [5123, 3, True, False, 8, 0, 24],          # UNSIGNED_SHORT in a buffer of four a vertex
            'aFacade': [5122, 2, False, False, 0, 0, 12],       # SHORT, not normalized: the layout Direct3D converts
            'aId': [5124, 1, False, True, 0, 0, 12],            # INT: vertexAttribIPointer
        })
        self.assertTrue(o['same'], 'a freed buffer keeps the type famWalk noted')
        self.assertTrue(o['shared'])
        self.assertEqual([o['never'], o['inst'], o['wide']], [None, None, None], 'an unknown type, an instanced stream or a matrix: no layout, so no candidate')
        self.assertEqual(o['gpu']['aK'][3], True, "r149's rule: an IntType attribute is an integer pointer")
        self.assertIn("MEAS.fmt.set(a, a.array.constructor);", cut(M2.BLOCK, '  function famWalk(sum) {', '\n  }\n'))


TRIAL = r'''
wear('cheap', 20); const a = wear('tower-own|real|glass', 389); wear('fabric|wx', 1400); wear('fabric-core|wx', 1469);
const inst = wear('trees', 395); inst.mesh.isInstancedMesh = true;                           // an instanced mesh is no candidate
const lost = wear('lost', 399, { attributes: { position: { array: null, itemSize: 3 } } });   // nor one whose layout is unknown
LINK.cold = 1;
const before = state(), log0 = g2.log.length;
NOW = 50000;
linkProbeAtReady();
const T = PERF.lp.last, log = g2.log.slice(log0);
const fsrc = g2.srcs.slice(-10).filter((s) => s[0] === E.FRAGMENT_SHADER).map((s) => s[1]);
console.log(JSON.stringify({ pp: MEAS.pp, ppk: MEAS.ppk, st: T.st, src: T.src, groups: T.groups.map((G) => [G.n, R1(G.i), R1(G.s), R1(G.w), R1(G.d), R1(G.r)]), ms: R1(T.ms), before, after: state(), log,
  uni: g2.uni.filter((u) => u[0] === g2.uni[0][0]), ptr: g2.ptr.slice(0, 5), nptr: g2.ptr.length, rbs: g2.rbs, bufs: g2.bufs, draws: g2.draws.length, draw0: g2.draws[0].slice(1),
  salts: new Set(fsrc.map((s) => /if \(([^)]*)\)/.exec(s.slice(s.lastIndexOf('p3dColdMain')))[1])).size, own: fsrc.every((s) => s.indexOf('// tower-own|real|glass') > 0 && s.indexOf('void p3dColdMain()') > 0),
  vs: g2.srcs.slice(-10).filter((s) => s[0] === E.VERTEX_SHADER).every((s) => s[1] === a.w.vertexShader.src), crumbs: crumbs.map((c) => c[0]), marker: store.get('philly3d.pp'),
  facts: measFacts('ready') }));
'''


class Trial(unittest.TestCase):
    def run_engine(self, engine, search=''):
        return probe_node(self, 'ENGINE = %s;\n' % json.dumps(engine) + TRIAL, search=search)

    def test_one_then_three_then_one_each_drawn_on_an_engine_that_links_side_by_side(self):
        o = self.run_engine('parallel')
        # the program copied: the slowest the build timed at no more than 400 ms, never the 1.4 s facade
        self.assertEqual(o['ppk'], 'Std-tower-own-real-glass')
        self.assertEqual(o['src'][0]['ref'], 389)
        # one, three, one: [programs, issue, the one call, wait, first draws, second draws]
        self.assertEqual(o['groups'], [[1, 0, 0, 300, 100, 1], [3, 0, 0, 300, 300, 3], [1, 0, 0, 300, 100, 1]], 'three links side by side wait once; every first draw is paid one at a time')
        self.assertEqual(o['pp'], '1.1.300.100.0.0.300.300.300.100.5.389.0.1405')
        self.assertEqual(o['st'], 1)
        # the order of the calls: a single issued and waited for, then three issued before any is waited for
        seq = [c for c in o['log'] if c in ('linkProgram', 'getProgramParameter:8b82', 'drawArrays')]
        self.assertEqual(seq, ['linkProgram', 'getProgramParameter:8b82', 'drawArrays', 'drawArrays',
                               'linkProgram', 'linkProgram', 'linkProgram', 'getProgramParameter:8b82', 'getProgramParameter:8b82', 'getProgramParameter:8b82'] + ['drawArrays'] * 6 +
                         ['linkProgram', 'getProgramParameter:8b82', 'drawArrays', 'drawArrays'])
        i = o['log'].index('linkProgram')
        self.assertEqual(o['log'][i + 1], 'getError', 'the one trivial synchronous call comes right behind the links')
        j = [k for k, c in enumerate(o['log']) if c == 'drawArrays']
        self.assertTrue(all(o['log'][k + 1] == 'getError' for k in j), 'every draw is waited for')
        self.assertNotIn('getProgramInfoLog', o['log'])
        # five copies, each its own salt, each the page's own program text; the vertex source is the page's to the byte
        self.assertEqual(o['salts'], 5)
        self.assertTrue(o['own'] and o['vs'])
        # drawn with the mesh's layout, every sampler type on a unit of its own, into the frame's kind of target
        self.assertEqual(o['ptr'], [['f', 'position', 3, 5126, False, 0, 0], ['f', 'normal', 4, 5120, True, 0, 0], ['f', 'color', 3, 5123, True, 8, 0], ['f', 'aFacade', 2, 5122, False, 0, 0], ['i', 'aId', 1, 5124, 0, 0]])
        self.assertEqual(o['nptr'], 25, 'five attributes a copy; instanceColor, which the mesh does not carry, stays a constant')
        self.assertEqual([u[1:] for u in o['uni']], [['map', 0], ['shadowMap[0]', [3, 3]], ['envMap', 2], ['tVol', 1]], 'a float uniform is left alone')
        self.assertEqual(o['rbs'], [[4, 0x881A, 4, 4], [4, 0x8CAD, 4, 4]], 'four samples, RGBA16F and DEPTH32F_STENCIL8: the post pipeline\'s frame under reversed Z')
        self.assertEqual(o['bufs'], [36, 12, 24, 12, 12], 'three zeroed vertices a buffer, made once and shared by the five copies')
        self.assertEqual((o['draws'], o['draw0']), (10, [4, 0, 3, 'fb', '0,0,4,4']))
        # nothing left, nothing counted
        b, a = o['before'], o['after']
        self.assertEqual(a['live'], b['live'], 'every program, shader, vertex array, buffer, framebuffer and renderbuffer is deleted')
        self.assertTrue(a['bound'], 'every binding and the viewport are back as they were read')
        self.assertEqual((a['n'], a['recs'], a['info']), (b['n'], b['recs'], b['info']), 'the link timers and three never see the probe\'s programs')
        self.assertEqual(a['asked'], 0, 'the extension is read from the list, never asked for')
        # the crumb, the marker and the beacon's two fields
        self.assertEqual(o['crumbs'][-1], 'link probe')
        self.assertEqual(o['marker'], '11/10/2026 20:00:00')
        self.assertNotIn('pp', o['facts'], 'nothing for ready before Ready')

    def test_an_engine_whose_stream_stalls_behind_a_link(self):
        o = self.run_engine('stream')
        self.assertEqual(o['groups'], [[1, 0, 300, 0, 100, 1], [3, 0, 900, 0, 300, 3], [1, 0, 300, 0, 100, 1]], 'the wait lands in the one synchronous call, and three cost three')
        self.assertEqual(o['pp'], '1.1.300.100.0.900.0.300.300.100.5.389.0.2005')

    def test_an_engine_whose_link_call_blocks(self):
        o = self.run_engine('block')
        self.assertEqual(o['groups'], [[1, 300, 0, 0, 100, 1], [3, 900, 0, 0, 300, 3], [1, 300, 0, 0, 100, 1]])
        self.assertEqual(o['pp'], '1.1.300.100.900.0.0.300.300.100.5.389.0.2005')

    def test_the_field_on_the_ready_beacon(self):
        o = probe_node(self, r'''
wear('tower-own|real|glass', 389); LINK.cold = 1; NOW = 50000; linkProbeAtReady();
PERF.ready = 51405; measReady();
const r = measFacts('ready'), keys = Object.keys(r);
console.log(JSON.stringify({ pp: r.pp, ppk: r.ppk, after: keys[keys.indexOf('pp') - 1], enter: 'pp' in measFacts('enter'), perf: 'pp' in measFacts('perf') }));
''')
        self.assertEqual(o['pp'], '1.1.300.100.0.0.300.300.300.100.5.389.0.1405')
        self.assertEqual(o['ppk'], 'Std-tower-own-real-glass')
        self.assertEqual((o['enter'], o['perf']), (False, False), 'the ready beacon alone')
        for v in (o['pp'], o['ppk']):
            self.assertRegex(v, r'^[A-Za-z0-9._-]*$')
            self.assertEqual(urllib.parse.quote(v, safe='*-._'), v)
        f = cut(M2.BLOCK, '  function measFacts(st) {', '\n  }\n')
        self.assertIn("      if (MEAS.pp) { o.pp = MEAS.pp; if (MEAS.ppk) o.ppk = MEAS.ppk; }", f)


class When(unittest.TestCase):
    def test_only_a_cold_load_and_once_a_device_and_build(self):
        o = probe_node(self, r'''
wear('tower-own|real|glass', 389);
const out = {}, calls = () => g2.log.length, go = () => { const n = calls(); MEAS.pp = ''; linkProbeAtReady(); return [MEAS.pp !== '', calls() - n > 0]; };
LINK.cold = 0; out.warm = go();                      // every load of a device that has seen this build
LINK.cold = -1; out.unknown = go();                  // under ten programs timed: no verdict, no probe
out.marker0 = store.has('philly3d.pp');
LINK.cold = 1; out.cold = go();
out.marker = store.get('philly3d.pp');
out.again = go();                                    // the same device and build: a slow machine does not pay it every load
document.lastModified = '11/11/2026 09:00:00'; out.newBuild = go();
store.clear(); document.hidden = true; out.hidden = go(); out.hiddenMarker = store.has('philly3d.pp'); document.hidden = false;
glDead = true; out.dead = go(); glDead = false;
renderer.capabilities.isWebGL2 = false; out.gl1 = go(); renderer.capabilities.isWebGL2 = true;
out.markerEnd = store.has('philly3d.pp');
const ls = localStorage.getItem; localStorage.getItem = () => { throw new Error('private mode'); }; out.private = go(); localStorage.getItem = ls;
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['warm'], [False, False], 'a warm load makes no GL call at all')
        self.assertEqual(o['unknown'], [False, False])
        self.assertFalse(o['marker0'])
        self.assertEqual(o['cold'], [True, True])
        self.assertEqual(o['marker'], '11/10/2026 20:00:00')
        self.assertEqual(o['again'], [False, False])
        self.assertEqual(o['newBuild'], [True, True])
        self.assertEqual((o['hidden'], o['hiddenMarker']), ([False, False], False), 'a page built hidden is not timed, and keeps its turn')
        self.assertEqual([o['dead'], o['gl1'], o['markerEnd']], [[False, False], [False, False], False])
        self.assertEqual(o['private'], [True, True], 'where nothing can be kept the probe still runs')

    def test_a_load_that_began_slow_and_turned_out_warm_does_not_probe(self):
        # the review: LINK.cold latches the first time the running median of ten or more programs passes the line and is
        # never taken back, so the median as it stands at the call (the ready beacon's own number) must be over it too
        o = probe_node(self, r'''
wear('slow-a', 300); wear('slow-b', 320);
for (let k = 0; k < 12; k++) wear('quick-' + k, 20);
const out = { med: linkMedian() }, n = g2.log.length;
LINK.cold = 1; linkProbeAtReady();
out.warm = [MEAS.pp, g2.log.length - n, store.has('philly3d.pp')];
for (let k = 0; k < 14; k++) wear('heavy-' + k, 180);
out.med2 = linkMedian(); LINK.cold = 1; linkProbeAtReady();
out.cold = [MEAS.pp.split('.')[0], store.has('philly3d.pp')];
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['med'], 20)
        self.assertEqual(o['warm'], ['', 0, False], 'no GL call, and the device keeps its turn for a load that is cold')
        self.assertEqual((o['med2'], o['cold']), (180, ['1', True]))
        self.assertIn("        if (LINK.cold !== 1 || !(linkMedian() > COLD_MS)) return;", PROBE)

    def test_a_page_that_cannot_tell_its_build_probes_once_a_week(self):
        # the review: Capacitor's asset handler sends no Last-Modified, so in the app document.lastModified is the moment it
        # is read and a marker that held it never matched: every launch that read cold probed again. Each launch below has
        # its own date, as the app's does
        o = probe_node(self, r'''
wear('tower-own|real|glass', 389);
const out = {};
const go = () => { const n = g2.log.length; MEAS.pp = ''; LINK.cold = 1; linkProbeAtReady(); return MEAS.pp !== '' && g2.log.length > n; };
const two = (v) => String(v).padStart(2, '0');
const stamp = (t) => { const d = new Date(t); return two(d.getMonth() + 1) + '/' + two(d.getDate()) + '/' + d.getFullYear() + ' ' + two(d.getHours()) + ':' + two(d.getMinutes()) + ':' + two(d.getSeconds()); };
const launch = (ms) => { WALL += ms; document.lastModified = stamp(WALL); return go(); };   // the clock moves on, and the document's date is the read's own second
const DAY = 864e5;
IN_APP = true; WALL += 417;
out.first = launch(0); out.marker = store.get('philly3d.pp') === '@' + WALL;
out.relaunch = [launch(40000), launch(3600e3), launch(DAY), launch(5 * DAY)];   // a build that died early and was opened again; the next days' launches
out.early = lpBuild();
out.week = launch(DAY);                                                        // seven days and an hour on: once more
out.marker2 = store.get('philly3d.pp') === '@' + WALL;
out.after = launch(60000);
// the app does not believe a date it is given, either (a web view that did send one would send the bundle's, not the build's)
store.clear(); document.lastModified = '11/10/2026 20:00:00';
out.dated = [go(), go(), store.get('philly3d.pp')[0]];
// not the app, but a host that sends no Last-Modified: the same rule, told by a date that reads as the clock's
IN_APP = false; store.clear();
out.host = [launch(1000), launch(90000), launch(8 * DAY), launch(1000)];
// a marker that is not a time, a clock set back a month, and a build marker left by a dated page: each probes and writes the time
store.set('philly3d.pp', '@soon'); out.broken = launch(1000);
WALL -= 30 * DAY; out.back = launch(0);
store.set('philly3d.pp', '11/10/2026 20:00:00'); out.other = [launch(1000), store.get('philly3d.pp')[0]];
// and a page with a date still goes by its build, whatever the clock says
document.lastModified = '11/10/2026 20:00:00'; store.clear();
out.site = [lpBuild(), go(), go(), (WALL += 30 * DAY, go()), store.get('philly3d.pp')];
console.log(JSON.stringify(out));
''')
        self.assertTrue(o['first'] and o['marker'], "the first cold launch probes, and the marker is the time, not a date")
        self.assertEqual(o['relaunch'], [False, False, False, False], 'no relaunch within the week probes again, though every one has a new document date')
        self.assertEqual(o['early'], '')
        self.assertTrue(o['week'] and o['marker2'])
        self.assertFalse(o['after'])
        self.assertEqual(o['dated'], [True, False, '@'])
        self.assertEqual(o['host'], [True, False, True, False])
        self.assertEqual([o['broken'], o['back'], o['other']], [True, True, [True, '@']])
        self.assertEqual(o['site'], ['11/10/2026 20:00:00', True, False, False, '11/10/2026 20:00:00'], 'once a build where the page can tell it, for as long as the build stands')
        self.assertIn("  const LP_AGAIN_MS = 7 * 864e5, LP_NOW_MS = 5000;", PROBE)
        self.assertIn("    return IN_APP || !(Math.abs(Date.now() - Date.parse(b)) > LP_NOW_MS) ? '' : b;", PROBE)
        self.assertIn("if (b ? m === b : !!m && m[0] === '@' && Math.abs(now - +m.slice(1)) < LP_AGAIN_MS) return;", PROBE)

    def test_the_flags(self):
        never = probe_node(self, r'''
wear('tower-own|real|glass', 389); LINK.cold = 1; const n = g2.log.length; linkProbeAtReady();
console.log(JSON.stringify([MEAS.pp, g2.log.length - n, store.size]));
''', search='?dev=1&probe=0')
        self.assertEqual(never, ['', 0, 0], '?probe=0: never')
        forced = probe_node(self, r'''
wear('tower-own|real|glass', 389); LINK.cold = 0; store.set('philly3d.pp', document.lastModified); linkProbeAtReady();
console.log(JSON.stringify([MEAS.pp.split('.')[0], store.size, PERF.lp.last.groups.length]));
''', search='?probe=1')
        self.assertEqual(forced, ['1', 1, 3], '?probe=1: on a warm load too, whatever the marker says')
        salted = probe_node(self, r'''
wear('tower-own|real|glass', 389); LINK.cold = 1; store.set('philly3d.pp', document.lastModified); linkProbeAtReady(); const first = MEAS.pp.split('.')[0];
store.clear(); linkProbeAtReady();
console.log(JSON.stringify([first, MEAS.pp.split('.')[0], store.size, COLD.n]));
''', search='?cold=31')
        self.assertEqual(salted, ['1', '1', 0, 31], 'a load salted by ?cold ignores the marker and leaves none: a dev\'s cold runs probe every time')
        self.assertIn("const LP_FLAG = (/[?&]probe=([01])\\b/.exec(location.search) || [0, ''])[1];", PROBE)

    def test_a_program_the_build_timed_within_the_budget(self):
        o = probe_node(self, r'''
const out = {};
const pick = () => { LINK.cold = 1; store.clear(); linkProbeAtReady(); return [MEAS.ppk, PERF.lp.last.src[0] && Math.round(PERF.lp.last.src[0].ref)]; };
wear('slow-a', 900); wear('slow-b', 650); out.over = pick();              // every one over 400 ms: the quickest of them
wear('mid', 240); out.one = pick();
wear('top', 400); wear('low', 30); out.best = pick();                     // the slowest at no more than 400
console.log(JSON.stringify(out));
''')
        self.assertEqual(o, {'over': ['Std-slow-b', 650], 'one': ['Std-mid', 240], 'best': ['Std-top', 400]})
        self.assertIn("const LP_KEY = 'philly3d.pp', LP_EACH_MS = 400, LP_ONE_MS = 800, LP_STOP_MS = 2500;", PROBE)
        self.assertIn("const R = lpTrial({ each: LP_EACH_MS, one: LP_ONE_MS, stop: LP_STOP_MS });", PROBE)

    def test_it_stops_for_time_and_says_what_went_wrong(self):
        o = probe_node(self, r'''
const out = {};
const go = (f) => { LINK.cold = 1; store.clear(); MEAS.pp = ''; const b = state(); f && f(); NOW = 50000; linkProbeAtReady(); const a = state(); return [MEAS.pp, PERF.lp.last.groups.length, a.live === b.live && a.bound, a.n === b.n]; };
wear('tower-own|real|glass', 389);
L_MS = 1200; out.slow1 = go();            // the first single took 1.3 s, linked and drawn: over 800 ms, the three are never issued
L_MS = 700; out.edge = go();              // 800 ms exactly: the three are issued, and on this engine (side by side) the last single too
ENGINE = 'stream'; out.slow3 = go();      // the same single on an engine that links one at a time: 3.2 s by the end of the three, no last single
ENGINE = 'parallel'; L_MS = 300;
out.nolink = go(() => { g2.linkOk = false; }); g2.linkOk = true;
out.glerr = go(() => { g2.errq = [0, 0, 0x502]; });
out.notarget = go(() => { g2.fbStatus = 0x8CD6; }); g2.fbStatus = E.FRAMEBUFFER_COMPLETE;
const err0 = MEAS.err; const dr = GL2.prototype.drawArrays; GL2.prototype.drawArrays = () => { throw new Error('lost'); };
out.threw = go(); out.counted = MEAS.err - err0; GL2.prototype.drawArrays = dr;
sceneObjs.length = 0; out.none = go();
console.log(JSON.stringify(out));
''')
        self.assertEqual(o['slow1'][:2], ['2.1.1200.100.0.0.0.0.0.0.1.389.0.1301', 1])
        self.assertEqual(o['edge'][:2], ['1.1.700.100.0.0.700.300.700.100.5.389.0.2605', 3])
        self.assertEqual(o['slow3'][:2], ['2.1.700.100.0.2100.0.300.0.0.4.389.0.3204', 2])
        self.assertEqual(o['nolink'][0], '4', 'a salted copy that does not link is the salt\'s fault on that engine: no numbers')
        self.assertEqual(o['glerr'][0].split('.')[0], '5')
        self.assertEqual(o['notarget'][0], '3')
        self.assertEqual((o['threw'][0], o['counted']), ('6', 1))
        self.assertEqual(o['none'][0], '3', 'no program with a timed link and a known layout')
        for k in ('slow3', 'slow1', 'edge', 'nolink', 'glerr', 'notarget', 'threw'):
            self.assertTrue(o[k][2], k + ': whatever happens, nothing is left and every binding is back')
            self.assertTrue(o[k][3], k)


class Scratch(unittest.TestCase):
    def test_the_dev_trial_by_family(self):
        o = probe_node(self, r'''
const fab = wear('fabric', 90), gnd = wear('surf', 40), cld = wear('cloud', 12), gls = wear('glass-sys|01111', 45);
const cityMat = fab.mat, groundMats = [gnd.mat], cloudDeck = { material: cld.mat };
const out = {}, live0 = state().live;
ENGINE = 'parallel';
const s = PERF.linkProbe({ groups: [1, 1, 1, 1, 1, 1, 1, 1] }), b = PERF.linkProbe({ groups: [8] });
out.names = s.src.map((x) => x.name + ':' + x.tag);
out.serial = [s.st, s.groups.length, R1(s.groups.reduce((a, G) => a + G.i + G.s + G.w, 0))];
out.batched = [b.st, b.groups.length, R1(b.groups[0].i + b.groups[0].s + b.groups[0].w), R1(b.groups[0].d)];
out.cycle = g2.srcs.slice(-16).filter((x) => x[0] === E.FRAGMENT_SHADER).map((x) => /\/\/ ([\w|-]+)\n/.exec(x[1])[1]);
out.asked0 = g2.asked;
const some = PERF.linkProbe({ pick: ['glass-sys', 'nothing-by-this-name', 'facade'], groups: [2] });
out.some = some.src.map((x) => x.name);
out.none = PERF.linkProbe({ pick: ['nothing-by-this-name'] }).st;
const e = PERF.linkProbe({ groups: [4], ext: true });
out.ext = [e.ext, g2.asked];
out.clean = state().live === live0 && state().bound && LINK.recs.length === 4;
(async () => {
  const np = await PERF.linkProbe({ groups: [2], poll: true });   // polled where the extension is not on: the status reads null and nothing waits on it
  out.nopoll = [np.st, np.groups[0].turns, R1(np.groups[0].w)];
  g2.extOn = true;                                               // the scratch page's getExtension
  const p = PERF.linkProbe({ groups: [3], ext: true, poll: true });
  out.promise = typeof p.then === 'function';
  let over = false; const tick = () => { NOW += 60; if (!over) setTimeout(tick, 0); };   // the clock moves a task at a time, as the page's would
  tick();
  const r = await p; over = true;
  out.poll = [r.st, r.groups[0].turns > 0, state().live === live0 && state().bound];
  console.log(JSON.stringify(out));
})();
''')
        self.assertEqual(o['names'], ['facade:Std-fabric', 'ground:Std-surf', 'clouds:Std-cloud', 'glass-sys:Std-glass-sys-01111'])
        self.assertEqual(o['serial'], [1, 8, 2400], 'eight one at a time: eight waits')
        self.assertEqual(o['batched'], [1, 1, 300, 800], 'eight issued, then awaited: one wait where links run side by side, and eight first draws')
        self.assertEqual(o['cycle'], ['fabric', 'surf', 'cloud', 'glass-sys|01111'] * 2, 'the copies cycle through the families')
        self.assertEqual(o['asked0'], 0)
        self.assertEqual(o['some'], ['glass-sys', 'facade'], 'a family that is not there is left out')
        self.assertEqual(o['none'], 3)
        self.assertEqual(o['ext'], [1, 0], '{ ext: true } is the caller\'s word that it turned the extension on: the page itself never asks')
        self.assertTrue(o['clean'])
        self.assertTrue(o['promise'])
        self.assertEqual(o['nopoll'], [1, 0, 300])
        self.assertEqual(o['poll'], [1, True, True], 'polled: the page runs on while the links complete, and nothing is left')

    def test_the_scratch_page(self):
        self.assertIn("'?dev=1&probe=0'", PAGE, "the page's own probe stays out of the way")
        self.assertIn("(q.get('page') || '../society-hill-towers.html')", PAGE)
        self.assertIn('P.linkProbe(Object.assign({ pick, groups: new Array(N).fill(1) }, o))', PAGE)
        self.assertIn('P.linkProbe(Object.assign({ pick, groups: [N] }, o))', PAGE)
        self.assertIn("'facade,ground,clouds,glass-sys'", PAGE)
        self.assertIn("ratio < 0.5 ? 'UNDER HALF' : 'NOT UNDER HALF'", PAGE)
        # the review: the verdict is for issue-then-wait, and the polled wait's own ratio stands beside it
        self.assertIn("' for links issued and then waited for, as a page may behind the veil' + (pe ? '; polled to completion with the extension on, as a page that must not block would wait: ' + (pe.link / ser).toFixed(2) + ' of serial'", PAGE)
        self.assertIn("polled: pe ? pe.link / ser : null", PAGE)
        self.assertIn('D.PERF.lit', PAGE, 'the runs wait for the lit button: the build, its flushes and its first frame are over')
        self.assertIn("pick: ['facade', 'ground', 'clouds', 'glass-sys']", PROBE)
        for bad in BAD:
            self.assertNotIn(bad, PAGE)
            self.assertNotIn(bad, PROBE)
            self.assertNotIn(bad, COLD)


class Wiring(unittest.TestCase):
    def test_the_build_runs_it_before_ready_is_stamped(self):
        b = cut(SRC, '  async function build() {', '\n  }\n')
        self.assertIn("    wxHookAll(true);", b)
        self.assertLess(b.index('wxHookAll(true);'), b.index('linkProbeAtReady();'), 'after the last hook: every program the build will make is made')
        self.assertLess(b.index('linkProbeAtReady();'), b.index('PERF.ready = Math.round(performance.now() - PERF.t0);'), 'its cost is inside Ready, and the field says how much')
        self.assertLess(b.index('linkProbeAtReady();'), b.index("bootMark('ready');"), "its own crumb is overwritten at once")
        self.assertEqual(SRC.count('linkProbeAtReady();'), 1)

    def test_no_shader_text_and_nothing_personal(self):
        # the probe and the salt hold no GLSL of their own beyond the salt's one line, and read nothing about the person
        for blk in (COLD, PROBE):
            for bad in ('UNMASKED', 'WEBGL_debug_renderer_info', 'userAgent', 'location.href', 'location.host', 'document.referrer', 'navigator.'):
                self.assertNotIn(bad, blk)
        code = '\n'.join(l for l in PROBE.split('\n') if not l.lstrip().startswith('//'))
        self.assertNotIn('gl_Frag', code, 'the probe writes no shader text: it copies the page\'s and salts it through coldSalt')
        self.assertNotIn('getExtension(', code, 'the page never asks for the parallel-compile extension: asking changes how the engine links')
        self.assertIn("frame.contentWindow.__dbg.renderer.getContext().getExtension('KHR_parallel_shader_compile')", PAGE, 'the scratch page asks, on the page\'s context, for its second table')
        self.assertNotIn('ext:', cut(PROBE, '  function linkProbeAtReady() {', '\n  }\n'))
        # the calls the link timers wrap go through the prototype, so the probe's programs are never the page's
        for name in ('shaderSource', 'compileShader', 'attachShader', 'linkProgram', 'getProgramParameter', 'getActiveUniform', 'getUniformLocation', 'getActiveAttrib', 'getAttribLocation'):
            self.assertNotRegex(code, r'\bgl\.' + name + r'\(', name)
            self.assertIn("X('" + name + "'", code)
        wrapped = set(re.findall(r"wrap\('(\w+)'", M2.BLOCK)) | set(re.findall(r"'(\w+)'", cut(M2.BLOCK, "    for (const n of ['getActiveUniform'", '\n') + cut(M2.BLOCK, "    for (const n of ['texImage2D'", '\n')))
        self.assertGreaterEqual(len(wrapped), 15)
        used = set(re.findall(r'\bgl\.([a-z]\w+)\(', code))
        self.assertEqual(used & wrapped, set(), 'a wrapped call made on the instance would count the probe in lk')


class BeaconsPy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('beacons_py', BEACONS_PY)
        cls.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.m)

    def test_decode(self):
        d = self.m.decode
        # MEASURED, headless Chrome on the Mac under ?cold: three links side by side
        p = d('pp', '1.1.292.136.4.0.437.378.319.135.8.389.79.1717')
        self.assertEqual({k: p[k] for k in ('state', 'khr_offered', 'serial_ms', 'serial_draw_ms', 'batch_issue_ms', 'batch_call_ms', 'batch_wait_ms', 'batch_draw_ms', 'serial2_ms', 'serial2_draw_ms', 'redraw_ms', 'build_ms', 'frag_kchars', 'probe_ms')},
                         {'state': 'whole', 'khr_offered': 1, 'serial_ms': 292, 'serial_draw_ms': 136, 'batch_issue_ms': 4, 'batch_call_ms': 0, 'batch_wait_ms': 437, 'batch_draw_ms': 378, 'serial2_ms': 319, 'serial2_draw_ms': 135,
                          'redraw_ms': 8, 'build_ms': 389, 'frag_kchars': 79, 'probe_ms': 1717})
        self.assertEqual((p['batched_over_serial'], p['where_it_waits'], p['first_draw_share']), (0.48, 'wait', 0.31))
        self.assertNotIn('under_half', p, 'the review: no load is given a verdict (the field sits on the line where the scratch page is clearly under it)')
        # MEASURED, a WKWebView under ?cold: the stream stalls behind the links and three cost three
        w = d('pp', '1.1.246.165.0.765.0.523.255.160.1.301.82.2126')
        self.assertEqual((w['batched_over_serial'], w['where_it_waits'], w['first_draw_share']), (1.02, 'call', 0.39))
        # stopped before the second single: the first is the baseline; stopped after the first: no ratio
        s = d('pp', '2.1.644.228.4.0.1226.511.0.0.7.331.82.2631')
        self.assertEqual((s['state'], s['batched_over_serial']), ('stopped-early', 0.64))
        self.assertNotIn('batched_over_serial', d('pp', '2.1.1200.100.0.0.0.0.0.0.1.389.0.1301'))
        self.assertEqual([d('pp', x)['state'] for x in ('3', '4', '6')], ['nothing-to-probe-with', 'a-copy-did-not-link', 'threw'])
        self.assertEqual(d('pp', ''), '')
        for k in ('pp', 'ppk', 'cs'):
            self.assertIn(k, self.m.READY2)
        self.assertEqual(len(self.m.FIELDS['pp']), 14)

    def test_the_engine_a_ratio_belongs_to(self):
        e = lambda ua, tch='0': self.m.engine({'ua': ua, 'ev': [('ready', 0, {'tch': tch})]})
        self.assertEqual(e('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'), 'Chromium Win')
        self.assertEqual(e('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'), 'Chromium Win')
        self.assertEqual(e('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/142.0.0.0 Safari/537.36'), 'Chromium Mac')
        self.assertEqual(e('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15'), 'WebKit Mac')
        self.assertEqual(e('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15', '1'), 'WebKit iOS', 'an iPad that says it is a Mac')
        self.assertEqual(e('Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Philly3DApp', '1'), 'WebKit iOS')
        self.assertEqual(e('Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/142.0.0.0 Mobile/15E148 Safari/604.1', '1'), 'WebKit iOS', 'Chrome on an iPhone is WebKit')
        self.assertEqual(e('Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0'), 'Gecko Win')
        self.assertEqual(e('Mozilla/5.0 (Linux; Android 16; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36', '1'), 'Chromium Android')

    def test_a_log(self):
        WIN = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15'
        def line(ip, ua=WIN, **q):
            return '%s - - [10/Nov/2026:16:00:00 +0000] "POST /b?%s HTTP/2.0" 404 0 "-" "%s"\n' % (ip, urllib.parse.urlencode(q), ua)
        step = dict(st='step:Raising the outer districts', t=20000, tch=0, tier=0, ms=15000)
        log = ''.join([
            # a visitor's cold load that ran the probe: 59,000 ms to Ready, 1,717 of them the probe's
            line('1.1.1.1', **step),
            line('1.1.1.1', st='ready', t=60000, tch=0, tier=0, ms=59000, cold=1, lk='144.0.1.48000.52.496.330', pp='1.1.292.136.4.0.437.378.319.135.8.389.79.1717', ppk='Std-tower-own-real-glass'),
            # the same machine class, a cold load with no probe (the device had probed this build): the same 57,283 ms without it
            line('4.4.4.4', **step),
            line('4.4.4.4', st='ready', t=58283, tch=0, tier=0, ms=57283, cold=1, lk='144.0.1.48000.52.496.330'),
            # two more visitors' probes on the engine, either side of the line (the numbers MEASURED in Chrome on this Mac, 0.73 and 0.39, worn here by a Windows visitor)
            line('5.5.5.5', **step),
            line('5.5.5.5', st='ready', t=60000, tch=0, tier=0, ms=59000, cold=1, lk='144.0.1.48000.52.496.330', pp='1.1.247.68.5.0.539.172.252.61.9.400.64.1360', ppk='Std-tower-own-real-glass'),
            line('6.6.6.6', **step),
            line('6.6.6.6', st='ready', t=60000, tch=0, tier=0, ms=59000, cold=1, lk='144.0.1.48000.52.496.330', pp='1.1.284.50.1.1.417.162.433.53.9.395.63.1416', ppk='Std-tower-own-real-glass'),
            # a probe stopped after its first single (a first draw as dear as the link): no ratio, and still out of gaps
            line('7.7.7.7', **step),
            line('7.7.7.7', st='ready', t=60000, tch=0, tier=0, ms=59000, cold=1, lk='144.0.1.48000.52.496.330', pp='2.1.450.420.0.0.0.0.0.0.2.390.80.900', ppk='Std-tower-own-real-glass'),
            # a probe that hit a GL error on the way (state 5): it carries a ratio, which no median counts
            line('8.8.8.8', **step),
            line('8.8.8.8', st='ready', t=60000, tch=0, tier=0, ms=59000, cold=1, lk='144.0.1.48000.52.496.330', pp='5.1.300.100.4.0.200.150.310.90.9.395.63.1200', ppk='Std-tower-own-real-glass'),
            # a dev's cold run on demand in Safari: salted
            line('2.2.2.2', MAC, **dict(step, cs=31)),
            line('2.2.2.2', MAC, st='ready', t=70000, tch=0, tier=0, ms=69000, cold=1, cs=31, lk='183.0.1.25280.518.9377.71', pp='1.1.246.165.0.765.0.523.255.160.1.301.82.2126', ppk='Std-wx-h1qfwvhc'),
            # a warm load: no probe
            line('3.3.3.3', **dict(step, t=9000, ms=6000)),
            line('3.3.3.3', st='ready', t=26000, tch=0, tier=0, ms=25500, cold=0, lk='144.0.0.3231.51.0.9'),
        ])
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write(log)
        argv, buf = sys.argv, io.StringIO()
        try:
            sys.argv = ['beacons.py', f.name, '--all']
            with redirect_stdout(buf):
                self.m.main()
        finally:
            sys.argv = argv
            Path(f.name).unlink()
        out = buf.getvalue()
        self.assertIn("('desk', 'Win', '0', 'cold') n= 6", out)
        self.assertIn("('desk', 'Mac', '0', 'salted cold') n= 1", out, "a salted load is never one of the visitors' cold loads")
        self.assertIn("('desk', 'Win', '0', 'warm') n= 1", out)
        self.assertIn("'cs': '31'", out)
        self.assertIn("'ppk': 'Std-tower-own-real-glass'", out)
        self.assertIn("'batched_over_serial': 0.48, 'where_it_waits': 'wait', 'first_draw_share': 0.31", out)
        # the review: the probe's own ms come out of gaps and Ready, so a probed load reads as the unprobed one beside it
        self.assertIn('cold: t0=1000 boot=4000 build=15000 gaps=38283 ready=57283 enter_gap=None probe=1717\n', out)
        self.assertIn('cold: t0=1000 boot=4000 build=15000 gaps=38283 ready=57283 enter_gap=None\n', out)
        self.assertIn('gaps=39100 ready=58100 enter_gap=None probe=900\n', out)
        self.assertIn('salted cold: t0=1000 boot=4000 build=15000 gaps=47874 ready=66874 enter_gap=None probe=2126\n', out)
        self.assertIn('warm: t0=500 boot=2500 build=6000 gaps=17000 ready=25500 enter_gap=None\n', out)
        self.assertIn("('desk', 'Win', '0', 'cold') n= 6 [1000.0, 4000.0, 15000.0, 38612.0, 57612.0, None]", out, 'the medians too: of 57,283 twice, 57,584, 57,640, 57,800 and 58,100, never of 59,000')
        self.assertEqual(self.m.probe_ms({'pp': '6'}), 0)
        self.assertEqual(self.m.probe_ms({}), 0)
        # a load a line, with no verdict; then the engine's median, its count and its range
        self.assertIn('LINK PROBES', out)
        self.assertIn('desk Win cold [Chromium Win]: Std-tower-own-real-glass batched/serial=0.48 serial=292,319 batch=4+0+437 waits_in=wait first_draw_share=0.31 khr=1 probe_ms=1717 state=whole', out)
        self.assertIn('desk Mac salted cold [WebKit Mac]: Std-wx-h1qfwvhc batched/serial=1.02 serial=246,255 batch=0+765+0 waits_in=call first_draw_share=0.39 khr=1 probe_ms=2126 state=whole', out)
        self.assertIn('desk Win cold [Chromium Win]: Std-tower-own-real-glass state=stopped-early serial=450 first_draw=420 probe_ms=900', out)
        self.assertEqual(out.count('batched/serial='), 5)
        for word in ('UNDER HALF', 'under half', 'under_half'):
            self.assertNotIn(word, out)
        self.assertIn('ENGINE MEDIANS of batched/serial (one, three, one: a three-program batch cannot read under 0.33;', out)
        # Round 244: the median is of whole probes, and the line says what it left out (a stopped probe has no ratio; a GL
        # error's ratio is not trusted), with the stopped ones' first single and its draw
        self.assertIn('Chromium Win: median 0.48 of n=3 (0 salted), 0.39 to 0.73, first draw share 0.21, waits in wait 3; '
                      'not counted 2: gl-error 1, stopped-early 1, their first single median 375 ms and its first draw 260 ms', out)
        self.assertIn('WebKit Mac: median 1.02 of n=1 (1 salted), 1.02 to 1.02, first draw share 0.39, waits in call 1', out)


if __name__ == '__main__':
    unittest.main()
