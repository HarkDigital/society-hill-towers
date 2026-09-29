"""Round 168 (the phones' GPU): the streetlamps' glow points take their log depth from the vertex.

The 205,323 glow points cost about 2 ms of an M2's night frame at ratio 1.25. With the log depth buffer every material
writes gl_FragDepth, so every fragment of every point was shaded before the depth test, the lamps behind the buildings
too. A point sprite's varyings are one value over the sprite, so the fragment path's depth, log2(1 + w) * FC / 2 from the
vertex's own w, is the same number the vertex path hands the rasterizer; the glow's material now takes that path (three's
own non-EXT branch of logdepthbuf_vertex, with USE_LOGDEPTHBUF_EXT undefined in both of its shaders) and keeps the
standard depth where it clips a point nearer than the near plane or past the far one. Measured 0.5 to 1.1 ms a night
frame. Checked here: the hook's output against three's own points shaders, the preprocessed branches (no gl_FragDepth
left, the vertex branch live), and the two depths equal to float rounding over the camera's whole range. (Round 168
first cut the points into frustum-culled tiles: 0.02 ms saved for 52 to 113 more draw calls, not kept.)"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GlowDepth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')
        a = cls.src.index('    poleMat.onBeforeCompile = (shader) => {')
        cls.hook = cls.src[a:cls.src.index('    postRaw(poleMat);', a)]

    def node(self, body):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        script = "const THREE = require('./three.min.js');\nconst poleMat = {};\n" + self.hook + r'''
// a small preprocessor: #define, #undef, #ifdef, #ifndef, #if defined(A) && defined(B), #else, #endif, and #include of
// three's chunks; returns the live lines
function live(src, defs) {
  const D = new Set(defs), out = [], stack = [];
  const lines = src.replace(/#include <(\w+)>/g, (m, n) => THREE.ShaderChunk[n]).split('\n');
  const on = () => stack.every((s) => s.take);
  for (const raw of lines) {
    const l = raw.trim();
    let m;
    if ((m = l.match(/^#ifdef (\w+)/))) { stack.push({ take: D.has(m[1]), done: D.has(m[1]) }); continue; }
    if ((m = l.match(/^#ifndef (\w+)/))) { stack.push({ take: !D.has(m[1]), done: !D.has(m[1]) }); continue; }
    if ((m = l.match(/^#if (.*)$/))) { const v = eval(m[1].replace(/defined\s*\(\s*(\w+)\s*\)/g, (q, n) => D.has(n)).replace(/\b[A-Z_]{3,}\b/g, '0')); stack.push({ take: !!v, done: !!v }); continue; }
    if (/^#elif/.test(l)) { const s = stack[stack.length - 1]; s.take = false; continue; }
    if (/^#else/.test(l)) { const s = stack[stack.length - 1]; s.take = !s.done; s.done = true; continue; }
    if (/^#endif/.test(l)) { stack.pop(); continue; }
    if (!on()) continue;
    if ((m = l.match(/^#define (\w+)/))) { D.add(m[1]); continue; }
    if ((m = l.match(/^#undef (\w+)/))) { D.delete(m[1]); continue; }
    out.push(l);
  }
  return out.join('\n');
}
''' + body
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_hook_on_threes_points_shaders(self):
        out = self.node(r'''
const L = THREE.ShaderLib.points, sh = { vertexShader: L.vertexShader, fragmentShader: L.fragmentShader, uniforms: {} };
poleMat.onBeforeCompile(sh);
const defs = ['USE_LOGDEPTHBUF', 'USE_LOGDEPTHBUF_EXT', 'USE_COLOR'];   // what r149 defines on WebGL 2 with logarithmicDepthBuffer
const v = live(sh.vertexShader, defs), f = live(sh.fragmentShader, defs);
const v0 = live(L.vertexShader, defs), f0 = live(L.fragmentShader, defs);
console.log(JSON.stringify({
  vFirst: sh.vertexShader.split('\n')[0], fFirst: sh.fragmentShader.split('\n')[0],
  incl: (L.vertexShader.match(/#include <logdepthbuf_vertex>/g) || []).length,
  size: sh.vertexShader.includes('gl_PointSize = size * clamp(1400.0 / max(1.0, -mvPosition.z), 1.6, 7.5);'),
  alpha: sh.fragmentShader.includes('diffuseColor.a *= smoothstep(0.5, 0.08, length(gl_PointCoord - vec2(0.5)));'),
  vLog: /gl_Position\.z = log2\( max\( EPSILON, gl_Position\.w \+ 1\.0 \) \) \* logDepthBufFC - 1\.0;/.test(v),
  vUniform: /uniform float logDepthBufFC;/.test(v),
  vClip: /float stdZ = gl_Position\.z;[\s\S]*gl_Position\.z \*= gl_Position\.w;[\s\S]*if \(stdZ < -gl_Position\.w \|\| stdZ > gl_Position\.w\) gl_Position\.z = stdZ;/.test(v),
  vFrag: /vFragDepth/.test(v), fDepth: /gl_FragDepth/.test(f),
  f0Depth: /gl_FragDepth/.test(f0), v0Frag: /vFragDepth = 1\.0 \+ gl_Position\.w;/.test(v0),
}));''')
        self.assertEqual(out['vFirst'], '#undef USE_LOGDEPTHBUF_EXT')
        self.assertEqual(out['fFirst'], '#undef USE_LOGDEPTHBUF_EXT')
        self.assertEqual(out['incl'], 1)
        self.assertTrue(out['size'])                 # the glow's own two patches stand
        self.assertTrue(out['alpha'])
        self.assertTrue(out['vLog'])                 # three's vertex branch is the live one
        self.assertTrue(out['vUniform'])
        self.assertTrue(out['vClip'])                # and the standard depth still clips past the near and far planes
        self.assertFalse(out['vFrag'])
        self.assertFalse(out['fDepth'])              # no fragment writes its depth
        self.assertTrue(out['f0Depth'])              # (as three's own points shader did)
        self.assertTrue(out['v0Frag'])

    def test_the_two_depths_agree_over_the_camera_range(self):
        out = self.node(r'''
const f = Math.fround, near = 0.75, far = 26000, FC = f(2 / (Math.log(far + 1) / Math.LN2));   // the camera's own (camera.near, camera.far)
let worst = 0, n = 0;
for (let i = 0; i <= 20000; i++) {
  const w = f(near * Math.pow(far / near, i / 20000));   // the near plane to the far one, log-spaced
  const frag = f(f(Math.log2(f(1 + w))) * FC * 0.5);                                  // logdepthbuf_fragment
  const z = f(f(f(Math.log2(Math.max(1e-6, f(w + 1)))) * FC - 1) * w);                // logdepthbuf_vertex, the non-EXT branch
  const vert = f(f(f(z / w) * 0.5) + 0.5);                                            // the divide and the depth range
  worst = Math.max(worst, Math.abs(vert - frag)); n++;
}
console.log(JSON.stringify({ worst, n }));''')
        self.assertLess(out['worst'], 1.2e-7)   # a float's last place or two: under a millimetre of depth at a kilometre
        self.assertEqual(out['n'], 20001)

    def test_only_the_glow_material(self):
        # the glow's two shaders; the far facades' twins (Round 168, VDEPTH_UNDEF) are the only other user, one named constant
        self.assertEqual(self.src.count("'#undef USE_LOGDEPTHBUF_EXT\\n'"), 3)
        self.assertEqual(self.src.count("const VDEPTH_UNDEF = '#undef USE_LOGDEPTHBUF_EXT\\n';"), 1)
        step = self.src[self.src.index("  step('Lighting the streetlamps', () => {"):self.src.index("  // ---- the rooftops' hardware")]
        self.assertIn('poleGlow = new THREE.Points(pg, poleMat);', step)
        self.assertIn('poleGlow.frustumCulled = false;', step)
        self.assertIsNone(re.search(r'lampTile', self.src))


if __name__ == '__main__':
    unittest.main()
