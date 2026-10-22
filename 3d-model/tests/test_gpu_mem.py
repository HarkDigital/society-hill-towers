"""Round 220, the measurement round (p25): GPU-byte accounting in the page itself.

Every memory figure the project had was headless Chrome's (the capture skill's gpuhook.js): no real device had ever
reported its bytes, and the phone tiers' cuts were sized without one. The page now carries the hook's wraps itself, on a
phone and behind ?gpumem=1 on a computer, installed on both context prototypes before the first context is made:

- bufferData sizes the buffer bound to the target it names (the pins' pixel pack buffer is not the array buffer), in the
  size, buffer, view and WebGL 2 offset-and-count forms; deleteBuffer takes it back;
- texImage2D sizes each face and level of the bound texture by its format and type pair, in the long and the six-argument
  forms; texStorage2D sizes the immutable allocation by its internal format, six faces for a cube map and a third more for
  mips; generateMipmap adds a third over the level-0 bytes once; deleteTexture takes the whole texture back;
- renderbufferStorage and renderbufferStorageMultisample size a renderbuffer by its format and every sample;
  deleteRenderbuffer takes it back;
- the peak and the loading message under it are kept; the sizes live in WeakMaps only;
- the install sits before the reversed-Z probe's throwaway context, the first getContext in the file;
- bootCtx's crumb carries gb, gpuMemField gives the beacon fields and PERF.gpuMem the probe, and the phone's reversed-Z
  target records its own bytes for gbm."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')


def cut_function(src, name):
    i = src.index('  function %s(' % name)
    j = src.index('{', i)
    depth = 0
    for k in range(j, len(src)):
        c = src[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
    raise ValueError(name)


def run_node(js):
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=120, cwd=str(ROOT))
    if out.returncode != 0:
        raise AssertionError(out.stderr[-3000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


# a WebGL 2 context with the methods the hook wraps and the binding reads it makes, nothing else; every call is logged and
# returns a marker, so the test can see the wrap forwards the call and hands back what the context returned
FAKE = r'''
const BIND = { 0x8892: 0x8894, 0x8893: 0x8895, 0x88EB: 0x88ED, 0x88EC: 0x88EF, 0x8A11: 0x8A28, 0x8F36: 0x8F36, 0x8F37: 0x8F37 };
class FakeGL2 {
  constructor() { this.bound = {}; this.t2 = null; this.tc = null; this.rb = null; this.calls = []; }
  getParameter(p) { return p === 0x8069 ? this.t2 : p === 0x8514 ? this.tc : p === 0x8CA7 ? this.rb : (this.bound[p] || null); }
  bindBuffer(target, b) { this.bound[BIND[target]] = b; }
  bufferData() { this.calls.push(['bufferData', arguments.length]); return 'bd'; }
  deleteBuffer() { this.calls.push(['deleteBuffer']); }
  texImage2D() { this.calls.push(['texImage2D', arguments.length]); return 'ti'; }
  texStorage2D() { this.calls.push(['texStorage2D']); }
  generateMipmap() { this.calls.push(['generateMipmap']); }
  deleteTexture() { this.calls.push(['deleteTexture']); }
  renderbufferStorage() { this.calls.push(['renderbufferStorage']); }
  renderbufferStorageMultisample() { this.calls.push(['renderbufferStorageMultisample']); return 'rm'; }
  deleteRenderbuffer() { this.calls.push(['deleteRenderbuffer']); }
}
class FakeGL1 {
  constructor() { this.bound = {}; this.t2 = null; this.tc = null; this.rb = null; this.calls = []; }
  getParameter(p) { return p === 0x8069 ? this.t2 : p === 0x8514 ? this.tc : p === 0x8CA7 ? this.rb : (this.bound[p] || null); }
  bindBuffer(target, b) { this.bound[BIND[target]] = b; }
  bufferData() { this.calls.push(['bufferData']); }
  deleteBuffer() { this.calls.push(['deleteBuffer']); }
  texImage2D() { this.calls.push(['texImage2D']); }
  generateMipmap() { this.calls.push(['generateMipmap']); }
  deleteTexture() { this.calls.push(['deleteTexture']); }
  renderbufferStorage() { this.calls.push(['renderbufferStorage']); }
  deleteRenderbuffer() { this.calls.push(['deleteRenderbuffer']); }
}
'''

# the replay: every op is followed by a reading, and the where() the hook is handed names the op in flight
REPLAY = r'''
const G = { on: true, buf: 0, tex: 0, rb: 0, peak: 0, peakAt: '', zrev: 0 };
let op = 0;
gpuMemInstall(G, [null, FakeGL1, FakeGL2], () => 'op' + op);
const gl = new FakeGL2(), steps = [], rets = {};
const step = (label) => { steps.push([label, G.buf, G.tex, G.rb, G.peak, G.peakAt]); };
const run = (label, f) => { op++; const r = f(); if (r !== undefined) rets[label] = r; step(label); };
const ARRAY = 0x8892, ELEMENT = 0x8893, PACK = 0x88EB, T2 = 0x0DE1, CUBE = 0x8513, RB = 0x8CA7, RENDERBUFFER = 0x8D41;
const RGBA = 0x1908, RGB = 0x1907, UBYTE = 0x1401, HALF = 0x140B, RGBA8 = 0x8058, RGBA16F = 0x881A, D32FS8 = 0x8CAD, D24S8 = 0x88F0, DSTENCIL = 0x84F9, F32_24_8 = 0x8DAD;
const b1 = {}, b2 = {}, b3 = {}, t1 = {}, t2 = {}, t3 = {}, t4 = {}, t5 = {}, tc1 = {}, tc2 = {}, r1 = {}, r2 = {}, r3 = {}, r4 = {}, r5 = {};
run('b1', () => { gl.bindBuffer(ARRAY, b1); return gl.bufferData(ARRAY, new Float32Array(1000), 0x88E4); });
run('b2', () => { gl.bindBuffer(ELEMENT, b2); gl.bufferData(ELEMENT, new Uint16Array(300), 0x88E4); });
run('b3 pack', () => { gl.bindBuffer(PACK, b3); gl.bufferData(PACK, 1024, 0x88E1); });
run('b1 again', () => { gl.bufferData(ARRAY, new Float32Array(500), 0x88E4); });
run('b1 offset', () => { gl.bufferData(ARRAY, new Float32Array(100), 0x88E4, 10, 0); });
run('b1 offset count', () => { gl.bufferData(ARRAY, new Float32Array(100), 0x88E4, 10, 20); });
run('b1 arraybuffer', () => { gl.bufferData(ARRAY, new ArrayBuffer(256), 0x88E4); });
run('delete b3', () => { gl.deleteBuffer(b3); gl.deleteBuffer({}); gl.deleteBuffer(null); });
run('t1 l0', () => { gl.t2 = t1; return gl.texImage2D(T2, 0, RGBA, 256, 128, 0, RGBA, UBYTE, null); });
run('t1 l1', () => { gl.texImage2D(T2, 1, RGBA, 128, 64, 0, RGBA, UBYTE, null); });
run('t1 mips', () => { gl.generateMipmap(T2); });
run('t1 mips again', () => { gl.generateMipmap(T2); });
run('t1 l0 source', () => { gl.texImage2D(T2, 0, RGB, RGB, UBYTE, { width: 64, height: 64 }); });
run('t2 half', () => { gl.t2 = t2; gl.texImage2D(T2, 0, RGBA16F, 16, 16, 0, RGBA, HALF, null); });
run('t3 depth', () => { gl.t2 = t3; gl.texImage2D(T2, 0, D32FS8, 8, 8, 0, DSTENCIL, F32_24_8, null); });
run('t4 storage', () => { gl.t2 = t4; gl.texStorage2D(T2, 1, RGBA8, 512, 512); });
run('t5 storage mips', () => { gl.t2 = t5; gl.texStorage2D(T2, 10, RGBA8, 512, 512); });
run('tc1 cube storage', () => { gl.tc = tc1; gl.texStorage2D(CUBE, 1, RGBA16F, 64, 64); });
run('tc2 faces', () => { gl.tc = tc2; for (let f = 0; f < 6; f++) gl.texImage2D(0x8515 + f, 0, RGBA, 32, 32, 0, RGBA, UBYTE, null); });
run('tc2 mips', () => { gl.generateMipmap(CUBE); });
run('unbound', () => { gl.t2 = null; gl.tc = null; gl.texImage2D(T2, 0, RGBA, 1000, 1000, 0, RGBA, UBYTE, null); });
run('delete t1 t5', () => { gl.deleteTexture(t1); gl.deleteTexture(t5); gl.deleteTexture({}); });
run('r1 ms', () => { gl.rb = r1; return gl.renderbufferStorageMultisample(RENDERBUFFER, 4, RGBA8, 1170, 2532); });
run('r2 ms depth', () => { gl.rb = r2; gl.renderbufferStorageMultisample(RENDERBUFFER, 4, D32FS8, 1170, 2532); });
run('r3', () => { gl.rb = r3; gl.renderbufferStorage(RENDERBUFFER, D24S8, 100, 100); });
run('r4 unknown', () => { gl.rb = r4; gl.renderbufferStorage(RENDERBUFFER, 0x9999, 10, 10); });
run('r1 resized', () => { gl.rb = r1; gl.renderbufferStorageMultisample(RENDERBUFFER, 4, RGBA8, 100, 100); });
run('delete r3', () => { gl.deleteRenderbuffer(r3); gl.deleteRenderbuffer({}); });
run('r5 zero samples', () => { gl.rb = r5; gl.renderbufferStorageMultisample(RENDERBUFFER, 0, RGBA8, 10, 10); });
const g1 = new FakeGL1(), b4 = {};
g1.bindBuffer(ARRAY, b4); g1.bufferData(ARRAY, new Uint8Array(7), 0x88E4);
console.log(JSON.stringify({ steps, rets, calls: gl.calls, g1buf: G.buf, g1calls: g1.calls, gl1storage: typeof FakeGL1.prototype.texStorage2D, gl1ms: typeof FakeGL1.prototype.renderbufferStorageMultisample }));
'''

MB = 1048576
# the bytes each op leaves, to the byte
EXPECT = [
    ('b1', 4000, 0, 0),
    ('b2', 4600, 0, 0),
    ('b3 pack', 5624, 0, 0),
    ('b1 again', 2000 + 600 + 1024, 0, 0),
    ('b1 offset', 360 + 600 + 1024, 0, 0),
    ('b1 offset count', 80 + 600 + 1024, 0, 0),
    ('b1 arraybuffer', 256 + 600 + 1024, 0, 0),
    ('delete b3', 856, 0, 0),
    ('t1 l0', 856, 131072, 0),
    ('t1 l1', 856, 131072 + 32768, 0),
    ('t1 mips', 856, 131072 + 32768 + 43254, 0),
    ('t1 mips again', 856, 207094, 0),
    ('t1 l0 source', 856, 207094 - 131072 + 12288, 0),
    ('t2 half', 856, 88310 + 2048, 0),
    ('t3 depth', 856, 90358 + 512, 0),
    ('t4 storage', 856, 90870 + 512 * 512 * 4, 0),
    ('t5 storage mips', 856, 1139446 + 1394606, 0),
    ('tc1 cube storage', 856, 2534052 + 64 * 64 * 8 * 6, 0),
    ('tc2 faces', 856, 2730660 + 6 * 32 * 32 * 4, 0),
    ('tc2 mips', 856, 2755236 + 8110, 0),
    ('unbound', 856, 2763346, 0),
    ('delete t1 t5', 856, 2763346 - 88310 - 1394606, 0),
    ('r1 ms', 856, 1280430, 1170 * 2532 * 4 * 4),
    ('r2 ms depth', 856, 1280430, 47399040 + 1170 * 2532 * 8 * 4),
    ('r3', 856, 1280430, 142197120 + 100 * 100 * 4),
    ('r4 unknown', 856, 1280430, 142237120 + 10 * 10 * 4),
    ('r1 resized', 856, 1280430, 142237520 - 47399040 + 100 * 100 * 4 * 4),
    ('delete r3', 856, 1280430, 94998480 - 40000),
    ('r5 zero samples', 856, 1280430, 94958480 + 400),
]


class Hook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    @unittest.skipUnless(NODE, 'node not on PATH')
    def test_bytes_to_the_byte(self):
        f = cut_function(self.s, 'gpuMemInstall')
        out = run_node(FAKE + f + REPLAY)
        steps = out['steps']
        self.assertEqual([st[0] for st in steps], [e[0] for e in EXPECT])
        for st, e in zip(steps, EXPECT):
            self.assertEqual(tuple(st[1:4]), e[1:], st[0])
        # the peak is the largest total the replay reached, and peakAt names the op it stood under
        totals = [e[1] + e[2] + e[3] for e in EXPECT]
        top = max(totals)
        k = totals.index(top)
        self.assertEqual(steps[-1][4], top)
        self.assertEqual(steps[-1][5], 'op%d' % (k + 1))
        self.assertEqual(EXPECT[k][0], 'r4 unknown')
        # the peak never falls: every reading after the top keeps it
        for st in steps[k:]:
            self.assertEqual(st[4], top)
        # every call reached the context and handed back what it returned
        self.assertEqual(out['rets'], {'b1': 'bd', 't1 l0': 'ti', 'r1 ms': 'rm'})
        names = [c[0] for c in out['calls']]
        self.assertEqual(names.count('bufferData'), 7)
        self.assertEqual(names.count('deleteBuffer'), 3)
        self.assertEqual(names.count('texImage2D'), 1 + 1 + 1 + 1 + 1 + 6 + 1)
        self.assertEqual(names.count('texStorage2D'), 3)
        self.assertEqual(names.count('generateMipmap'), 3)
        self.assertEqual(names.count('deleteTexture'), 3)
        self.assertEqual(names.count('renderbufferStorage'), 2)
        self.assertEqual(names.count('renderbufferStorageMultisample'), 4)
        self.assertEqual(names.count('deleteRenderbuffer'), 2)
        self.assertEqual([c[1] for c in out['calls'] if c[0] == 'bufferData'], [3, 3, 3, 3, 5, 5, 3])
        # a WebGL 1 prototype is wrapped too, without the methods it does not have, and shares the sums
        self.assertEqual(out['g1buf'], 856 + 7)
        self.assertEqual(out['g1calls'], [['bufferData']])
        self.assertEqual(out['gl1storage'], 'undefined')
        self.assertEqual(out['gl1ms'], 'undefined')

    def test_hook_holds_sizes_in_weakmaps_and_times_nothing(self):
        f = cut_function(self.s, 'gpuMemInstall')
        self.assertIn('const bsz = new WeakMap(), tsz = new WeakMap(), rsz = new WeakMap();', f)
        self.assertNotIn('new Map(', f)
        self.assertNotIn('performance.now()', f)
        # the lesson the headless hook learnt in Round 167: the pins' pixel pack buffer is not the array buffer
        self.assertIn('t === 0x88EB ? 0x88ED', f)
        # the renderbuffer and immutable formats are sized by their bytes, the depth of the phone's target 8 a sample
        self.assertIn('0x8CAD: 8', f)
        self.assertIn('0x8058: 4', f)
        self.assertIn('0x881A: 8', f)
        self.assertIn("(target === 0x8513 ? 6 : 1) * (levels > 1 ? 1.33 : 1)", f)
        self.assertIn('Math.max(1, samples | 0)', f)
        for m in ('bufferData', 'deleteBuffer', 'texImage2D', 'texStorage2D', 'generateMipmap', 'deleteTexture', 'renderbufferStorage', 'renderbufferStorageMultisample', 'deleteRenderbuffer', 'texStorage3D', 'texImage3D'):
            self.assertIn('P.%s = function' % m, f)


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_installed_before_the_first_context(self):
        s = self.s
        self.assertIn("const GPUMEM = { on: isTouch || /[?&]gpumem=1\\b/.test(location.search), buf: 0, tex: 0, rb: 0, peak: 0, peakAt: '', zrev: 0 };", s)
        install = 'if (GPUMEM.on) gpuMemInstall(GPUMEM, [window.WebGLRenderingContext, window.WebGL2RenderingContext], gpuMemWhere);'
        self.assertIn(install, s)
        i = s.index(install)
        self.assertLess(s.index('const isTouch = '), s.index('const GPUMEM = '))
        self.assertLess(s.index('const GPUMEM = '), i)
        self.assertLess(i, s.index('.getContext('))   # the reversed-Z probe's throwaway context is the first in the file
        self.assertLess(i, s.index('new THREE.WebGLRenderer('))
        self.assertLess(i, s.index('  let renderer;'))

    def test_crumb_beacon_and_probe(self):
        s = self.s
        b = cut_function(s, 'bootCtx')
        self.assertIn("(GPUMEM.on ? ',gb' + Math.round((GPUMEM.buf + GPUMEM.tex + GPUMEM.rb) / 1048576) : '')", b)
        f = cut_function(s, 'gpuMemField')
        self.assertIn('if (!GPUMEM.on) return {};', f)
        self.assertIn("gb: Math.round((GPUMEM.buf + GPUMEM.tex + GPUMEM.rb) / 1048576), gbp: Math.round(GPUMEM.peak / 1048576), gbw: GPUMEM.peakAt, gbm: GPUMEM.zrev ? Math.round(GPUMEM.zrev / 1048576) : ''", f)
        self.assertIn("PERF.gpuMem = () => {", s)
        self.assertIn("return { on: GPUMEM.on, buf: MB(GPUMEM.buf), tex: MB(GPUMEM.tex), rb: MB(GPUMEM.rb), total: MB(GPUMEM.buf + GPUMEM.tex + GPUMEM.rb), peak: MB(GPUMEM.peak), peakAt: GPUMEM.peakAt, zrev: MB(GPUMEM.zrev) };", s)
        self.assertNotIn('__dbg.gpu = ', s)
        # the phone's reversed-Z target records its own bytes once both renderbuffers are made
        fb = s[s.index('ZREV.fbInit = function zrevFB() {'):]
        fb = fb[:fb.index('ZREV.status = gl.checkFramebufferStatus')]
        self.assertIn('gl.renderbufferStorageMultisample(gl.RENDERBUFFER, ZREV.samples, gl.DEPTH32F_STENCIL8, w, h);\n      GPUMEM.zrev = w * h * ZREV.samples * 12;', fb)
        # where the peak stood: the loading message, guarded, and after Ready the seconds since
        w = cut_function(s, 'gpuMemWhere')
        self.assertIn("loadmsg ? String(loadmsg.textContent || '').slice(0, 24) : ''", w)
        self.assertIn("PERF.ready ? s.slice(0, 16) + ' +'", w)

    @unittest.skipUnless(NODE, 'node not on PATH')
    def test_beacon_fields_under_node(self):
        f = cut_function(self.s, 'gpuMemField')
        js = f + r'''
const early = gpuMemField();   // before GPUMEM's line has run: the TDZ, and the error beacon can fire then
const GPUMEM = { on: true, buf: 3 * 1048576, tex: 5 * 1048576, rb: 7 * 1048576, peak: 20 * 1048576, peakAt: 'Raising the far ring', zrev: 0 };
const a = gpuMemField();
GPUMEM.zrev = 1170 * 2532 * 4 * 12;
const b = gpuMemField();
GPUMEM.on = false;
const c = gpuMemField();
console.log(JSON.stringify({ early, a, b, c }));
'''
        out = run_node(js)
        self.assertEqual(out['early'], {})
        self.assertEqual(out['a'], {'gb': 15, 'gbp': 20, 'gbw': 'Raising the far ring', 'gbm': ''})
        self.assertEqual(out['b'], {'gb': 15, 'gbp': 20, 'gbw': 'Raising the far ring', 'gbm': 136})
        self.assertEqual(out['c'], {})


if __name__ == '__main__':
    unittest.main()
