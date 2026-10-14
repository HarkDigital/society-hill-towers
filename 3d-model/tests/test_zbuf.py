"""Round 192 (from perf spike 1): reversed-Z float depth through EXT_clip_control in place of r149's log depth buffer.

Mike asked for a way to hold about 60 fps. r149's log depth writes gl_FragDepth from every fragment, which costs the GPU its
early depth test and Apple's hidden-surface removal; reversed Z keeps the depth in the vertex stage (measured 1.3 to 1.9 times
faster from the air and 2.3 to 4.3 at street level, in Chrome and in WebKit, with the same picture).

- the default is reversed Z wherever a throwaway WebGL 2 context reports EXT_clip_control AND a complete 4x DEPTH32F_STENCIL8
  framebuffer, and the real context passes the same check (else a fresh canvas and log depth); ?zbuf=log forces log depth,
  ?logdepth=0 is still plain depth;
- every perspective camera draws with its own reversed z row only inside renderer.render (camera.projectionMatrix is three's
  everywhere else), the depth clears to 0, LESS becomes GREATER and the shadow pass keeps the standard convention;
- a renderer.clear() outside a render clears to 1, the NEAR plane in reversed Z: a render that does not clear its own depth
  clears it to 0 first when its target was last cleared that way (the guard), and r149's PMREM always does;
- the reversed projection maps the near plane to depth 1 and the far plane to 0, and the AO's linearisation inverts it;
- the mirror's reversed oblique row keeps a point over the water and clips one under it, depth 1 on the water, and keeps a
  row (still clipping) when the river is not in its view;
- the cloud deck's twin writes no depth and draws in both depth modes, leaving the aircraft's rectangles to the
  depth-writing program; the rectangles cover every plane and fit in sixteen;
- nothing else in the page writes gl_FragDepth, and every gl_Position.z the page sets is one this file knows;
- every beacon carries zc."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


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


NODE = shutil.which('node')


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_reversed_is_the_default_where_it_can_be(self):
        s = self.s
        self.assertIn("let mode = qsZ && qsZ[1] === 'log' ? 'log' : qsDepth ? (qsDepth[1] === '1' ? 'log' : 'std') : 'rev';", s)
        self.assertIn("qsZ = /[?&]zbuf=(rev|log)\\b/.exec(location.search)", s)
        # one throwaway context answers both the post pipeline's question and the depth's
        self.assertIn("if (mode === 'rev' && !zrevCheck(g2, postCapable, ZPROBE)) { mode = 'log';", s)
        # the real context passes the same check, or a fresh canvas builds on log depth
        i = s.index("    if (mode === 'rev') {\n      const real = { e: '-', f: '-', why: '' };")
        body = s[i:s.index('    ZPROBE.mode = mode;', i)]
        self.assertIn('zrevCheck(renderer.getContext(), postCapable, real)', body)
        self.assertIn('const fresh = canvas.cloneNode(false); canvas.replaceWith(fresh); canvas = fresh;', body)
        self.assertIn("mode = 'log';\n        renderer = make(mode);", body)
        self.assertIn("  let canvas = document.getElementById('gl');", s)
        # the renderer options per mode: the phone's reversed canvas has no depth, no stencil, no antialias (ZREV's own target)
        self.assertIn("return new THREE.WebGLRenderer(window.__zrevSub ? { canvas, antialias: false, depth: false, stencil: false, powerPreference: 'high-performance', logarithmicDepthBuffer: false }", s)
        self.assertIn(": { canvas, antialias: !postCapable, powerPreference: 'high-performance', logarithmicDepthBuffer: window.__useLogDepth });", s)
        self.assertIn("window.__useLogDepth = m === 'log';", s)
        self.assertIn('ZREV.on = !!ZREV.ext;', s)
        self.assertIn('if (ZREV.on) {\n    const gl = renderer.getContext(), st = renderer.state, _zv2 = new THREE.Vector2();\n    ZREV.sub = !!window.__zrevSub;\n    zrevInstall(renderer);', s)
        # the log-depth-only paths stay with log depth: the far facades' vertex depth
        self.assertIn('const VDEPTH_WANT = !!window.__useLogDepth && ', s)
        self.assertIn("window.__useLogDepth || ZREV.on ? 0.75 : 1.0, 26000);", s)

    def test_float_depth_everywhere_reversed_draws(self):
        s = self.s
        self.assertIn('if (ZREV.on) ZREV.status = zrevFloatDepth(postRT);', s)
        self.assertIn('if (ZREV.on) REFL.zst = zrevFloatDepth(REFL.rt);', s)
        refl = s[s.index('      REFL.rt = new THREE.WebGLRenderTarget('):]
        refl = refl[:refl.index('\n', refl.index('\n') + 1)]
        self.assertIn('stencilBuffer: true', refl)        # the vehicle shadows' stencil in the mirror too
        self.assertNotIn('depthTexture', refl)
        # the mirror's anisotropy is set before zrevFloatDepth makes its framebuffers (three sets a target texture's parameters
        # only then: the other way round its streaks lost the anisotropic filter and blurred, found in the parity renders)
        self.assertLess(s.index('REFL.rt.texture.anisotropy = renderer.capabilities.getMaxAnisotropy();'), s.index('if (ZREV.on) REFL.zst = zrevFloatDepth(REFL.rt);'))
        f = cut_function(s, 'zrevFloatDepth')
        self.assertIn('const fmt = rt.stencilBuffer ? gl.DEPTH32F_STENCIL8 : gl.DEPTH_COMPONENT32F;', f)
        self.assertIn('if (ms) p.__ignoreDepthValues = true;', f)
        for k in ("THREE.WebGLRenderTarget(1, 1, { type: THREE.FloatType, depthBuffer: true, stencilBuffer: !ZREV.on, depthTexture: zrevDT(1, 1) })",
                  "BPICK.rt = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: true, stencilBuffer: false, depthTexture: zrevDT(1, 1) })",
                  "new THREE.WebGLRenderTarget(W, H, { depthBuffer: true, stencilBuffer: false, depthTexture: zrevDT(W, H),"):
            self.assertIn(k, s)
        # the phone's own target
        self.assertIn('gl.renderbufferStorageMultisample(gl.RENDERBUFFER, ZREV.samples, gl.DEPTH32F_STENCIL8, w, h);', s)
        # the two-step blit stays: the direct one works only on an alpha:true canvas
        p = cut_function(s, 'zrevPresent')
        self.assertIn("ZREV.blit = ZREV.rfb ? 'two-step' : 'direct';", p)
        self.assertIn('gl.invalidateFramebuffer(gl.READ_FRAMEBUFFER, [gl.DEPTH_STENCIL_ATTACHMENT]);', p)

    def test_cloud_programs(self):
        s = self.s
        frag = cut_function(s, 'cloudFrag')
        i = frag.index('#if defined(CLOUD_NOZ)')
        self.assertLess(i, frag.index('gl_FragDepthEXT ='))
        self.assertIn("gl_FragDepthEXT = hitClip.z / hitClip.w${ZREV.on ? '' : ' * 0.5 + 0.5'};", frag)
        # the twin leaves the rectangles, the depth-writing program keeps only them: the same test, so they tile the screen
        self.assertIn('#if defined(CLOUD_RECT_IN)\n        if (!cloudInRect()) discard;\n        #elif defined(CLOUD_RECT_N)\n        if (cloudInRect()) discard;\n        #endif', frag)
        self.assertIn('gl_FragCoord.x >= r.x && gl_FragCoord.x < r.z && gl_FragCoord.y >= r.y && gl_FragCoord.y < r.w', frag)
        # both depth modes draw the twin (only the A/B and plain depth keep the old deck)
        self.assertIn("old: /[?&]cloudz=old\\b/.test(location.search) || ZPROBE.mode === 'std'", s)
        self.assertIn("const cloudMatNoZ = CLOUDZ.old ? null : cloudTwin({ CLOUD_NOZ: '' }, false);", s)
        self.assertIn("const cloudMatRect = CLOUDZ.old ? null : cloudTwin({ CLOUD_RECT_IN: '' }, true);", s)
        self.assertIn('cloudDeckStep();   // Round 192', s)
        self.assertNotIn('if (ZREV.on) zrevCloud();', s)
        step = cut_function(s, 'cloudDeckStep')
        self.assertIn('const below = camera.position.y < minBase - 25;', step)
        self.assertIn('cloudRects(minBase)', step)
        # the sky dome and the deck's clamp sit on the far plane in either convention
        self.assertIn("(ZREV.on ? 'gl_Position.z = 0.0; }' : 'gl_Position.z = gl_Position.w; }')", s)
        self.assertIn("${ZREV.on ? 'gl_Position.z = max(gl_Position.z, 0.0);' : 'gl_Position.z = min(gl_Position.z, gl_Position.w * 0.99999);'}", s)
        # the three programs compile behind the veil, never in flight
        self.assertIn('warm: 3', s)
        self.assertIn('cloudDeckZ.material = CLOUDZ.warm === 2 ? cloudMatNoZ : cloudMatRect;', s)
        # the rectangles' program never reaches the mirror or the pins' depth image
        self.assertIn('cloudDeckZ.frustumCulled = false; cloudDeckZ.renderOrder = -5;', s)
        self.assertIn('cloudDeck.add(cloudDeckZ);', s)

    def test_no_other_depth_writes(self):
        # the page's gl_FragDepth writes: the cloud deck's alone (r149's own chunk aside), and every gl_Position.z it sets
        srcs = [(ROOT / 'app.js').read_text()] + [p.read_text() for p in sorted((ROOT / 'rebuilds').glob('*.js'))]
        writes = []
        for t in srcs:
            for m in re.finditer(r'gl_FragDepth(?:EXT)?\s*=', t):
                writes.append(t[max(0, t.rfind('\n', 0, m.start())):t.find('\n', m.end())].strip())
        self.assertEqual(len(writes), 2, writes)
        self.assertTrue(all('logDepthBufFC' in w or 'hitClip' in w for w in writes), writes)
        allowed = ('gl_Position.z = 0.0;', 'gl_Position.z = gl_Position.w;', 'gl_Position.z = max(gl_Position.z, 0.0);',
                   'gl_Position.z = min(gl_Position.z, gl_Position.w * 0.99999);', 'gl_Position.z = log2(max(EPSILON, pinA.w + 1.0)) * logDepthBufFC - 1.0;',
                   'gl_Position.z *= gl_Position.w;', 'gl_Position.z = pinA.z / pinA.w * gl_Position.w;', 'gl_Position.z = stdZ;',
                   'gl_Position.z /= 0.9995;', 'gl_Position.z /= 0.9993;')
        seen = []
        for t in srcs:
            for m in re.finditer(r'gl_Position\.z\s*(?:[-+*/]?=)[^;]*;', t):
                seen.append(m.group(0))
        for z in seen:
            self.assertIn(z, allowed)

    def test_the_wakes_and_shadows_keep_their_hair(self):
        s = self.s
        self.assertIn("(ZREV.on ? '\\ngl_Position.z /= 0.9995;' : '')", s)
        self.assertIn("(ZREV.on ? '\\ngl_Position.z /= 0.9993;' : '')", s)

    def test_every_beacon_carries_zc(self):
        s = self.s
        b = cut_function(s, 'beacon')
        self.assertIn("zc: safe(() => zcField(), '')", b)
        z = cut_function(s, 'zcField')
        self.assertIn("ZPROBE.mode + (ZPROBE.forced ? 'q' : '') + '.' + ZPROBE.e + ZPROBE.f + ZPROBE.real + '.' + blit", z)


@unittest.skipUnless(NODE, 'Node.js unavailable')
class Numbers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_reversed_depth_and_ao_decode(self):
        # the AO's linW for uLog 2, lifted from the shader string, inverts the reversed row the render writes
        s = self.s
        m = re.search(r"'float linW\(float d\)\{ return uLog > 1\.5 \? ([^:]+) :", s)
        self.assertIsNotNone(m)
        expr = m.group(1).replace('uNear', 'n').replace('uFar', 'f')
        js = """
const THREE = require('./three.min.js');
const cam = new THREE.PerspectiveCamera(58, 1.6, 0.75, 26000), e = cam.projectionMatrix.elements, n = cam.near, f = cam.far;
e[10] = n / (f - n); e[14] = f * n / (f - n);
const linW = (d) => """ + expr + """;
let worst = 0, mono = true, prev = 2;
const out = {};
for (const w of [0.75, 1, 5, 50, 500, 2000, 10000, 25999]) {
  const c = new THREE.Vector4(0, 0, -w, 1).applyMatrix4(cam.projectionMatrix), d = c.z / c.w;
  if (!(d < prev)) mono = false; prev = d;
  worst = Math.max(worst, Math.abs(linW(d) - w) / w);
  out[w] = d;
}
console.log(JSON.stringify({ near: out[0.75], far: out[25999], mono, worst }));
"""
        r = run_node(js)
        self.assertAlmostEqual(r['near'], 1.0, places=5)
        self.assertLess(r['far'], 1e-6)
        self.assertTrue(r['mono'])
        self.assertLess(r['worst'], 1e-4)

    def mirror(self, look):
        refl = cut_function(self.s, 'reflRender')
        body = refl[refl.index('    const C = REFL.cam;'):refl.index('    C.projectionMatrixInverse.copy(C.projectionMatrix).invert();')]
        js = """
const THREE = require('./three.min.js');
const W0 = -7.34, REFL_FAR = 3500, ZREV = { on: true };
const REFL = { cam: new THREE.PerspectiveCamera() };
const waterU = { uReflMat: { value: new THREE.Matrix4() } };
const _rfA = new THREE.Vector3(), _rfN = new THREE.Vector3(0, 1, 0), _rfP = new THREE.Plane(), _rfV = new THREE.Vector4(), _rfQ = new THREE.Vector4();
const cam = new THREE.PerspectiveCamera(60, 1.6, 0.75, 26000);
cam.position.set(100, W0 + 12, -40); cam.lookAt(""" + look + """); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
""" + body + """
const row = REFL.cam.userData.zrevRow, P = REFL.cam.projectionMatrix.clone(), pe = P.elements;
pe[2] = row[0]; pe[6] = row[1]; pe[10] = row[2]; pe[14] = row[3];
let tried = 0, kept = 0, clipped = 0, onWater = 0, mono = 0, under = 0, underClipped = 0;
const v = new THREE.Vector3();
const clip = (x, y, z) => new THREE.Vector4(x, y, z, 1).applyMatrix4(REFL.cam.matrixWorldInverse).applyMatrix4(P);
for (let j = 0; j < 12; j++) for (let i = 0; i < 16; i++) {
  v.set((i + 0.5) / 8 - 1, (j + 0.5) / 6 - 1, 0.5).unproject(cam).sub(cam.position).normalize();
  // the mirrored world under the water, along the mirror's own rays: every such point must clip, whatever the view
  const m = new THREE.Vector3(v.x, -v.y, v.z), me = REFL.cam.position;
  for (const t of [5, 50, 500]) { const q = me.clone().addScaledVector(m, t); if (q.y < W0 - 0.5) { under++; const c = clip(q.x, q.y, q.z); if (c.z > c.w || c.w <= 0) underClipped++; } }
  if (v.y > -0.01) continue;
  const t = (W0 - cam.position.y) / v.y, x = cam.position.x + v.x * t, z = cam.position.z + v.z * t;
  if (t > 3000) continue;
  tried++;
  const up = clip(x, W0 + 2, z), dn = clip(x, W0 - 2, z), on = clip(x, W0 + 0.02, z), hi = clip(x, W0 + 40, z);
  if (up.z >= 0 && up.z <= up.w) kept++;   // ZERO_TO_ONE: 0 <= z <= w
  if (dn.z > dn.w) clipped++;
  if (Math.abs(on.z / on.w - 1) < 1e-4) onWater++;
  if (hi.z / hi.w < up.z / up.w) mono++;   // farther from the mirrored eye along the reflected ray: nearer 0
}
console.log(JSON.stringify({ row: !!row, tried, kept, clipped, onWater, mono, under, underClipped }));
"""
        return run_node(js)

    def test_mirrored_eye_reversed(self):
        r = self.mirror('900, W0 - 30, -300')
        self.assertGreater(r['tried'], 40)
        self.assertEqual(r['kept'], r['tried'])
        self.assertEqual(r['clipped'], r['tried'])
        self.assertEqual(r['onWater'], r['tried'])
        self.assertEqual(r['mono'], r['tried'])

    def test_mirror_keeps_its_row_with_no_river_in_view(self):
        # the eye looking up and away: no frustum corner climbs from the water, and the spike's null row lost the clip plane
        r = self.mirror('300, W0 + 400, -300')
        self.assertTrue(r['row'])
        self.assertEqual(r['tried'], 0)
        self.assertGreater(r['under'], 20)
        self.assertEqual(r['underClipped'], r['under'])

    def test_probe(self):
        # zrevCheck against a fake context: the extension, the framebuffer's status over each colour format, a GL error, a throw
        f = cut_function(self.s, 'zrevCheck')
        js = """
""" + f + """
function fake(o) {
  const g = { FRAMEBUFFER: 1, RENDERBUFFER: 2, RGBA8: 3, RGBA16F: 4, DEPTH32F_STENCIL8: 5, COLOR_ATTACHMENT0: 6, DEPTH_STENCIL_ATTACHMENT: 7,
    FRAMEBUFFER_COMPLETE: 36053, NO_ERROR: 0, MAX_SAMPLES: 8, fb: 'x', rb: 'x', fmt: 0, errs: (o.errs || []).slice(), made: 0, gone: 0, samples: [],
    getExtension: (n) => (n === 'EXT_clip_control' && o.ext ? {} : null),
    getParameter: () => 4, createFramebuffer() { this.made++; return {}; }, createRenderbuffer() { this.made++; return {}; },
    deleteFramebuffer() { this.gone++; }, deleteRenderbuffer() { this.gone++; },
    bindFramebuffer(t, f) { this.fb = f; }, bindRenderbuffer(t, r) { this.rb = r; },
    renderbufferStorageMultisample(t, n, fmt) { if (o.throws) throw new Error('lost'); this.samples.push(n); if (fmt !== 5) this.fmt = fmt; },
    framebufferRenderbuffer() {}, checkFramebufferStatus() { return (o.bad || []).includes(this.fmt) ? 36054 : 36053; },
    getError() { return this.errs.length ? this.errs.shift() : 0; } };
  return g;
}
const out = {};
for (const [k, o, post] of [['none', {}, false], ['ok', { ext: 1 }, false], ['okPost', { ext: 1 }, true], ['f16', { ext: 1, bad: [4] }, true],
  ['f16phone', { ext: 1, bad: [4] }, false], ['rgba8', { ext: 1, bad: [3] }, false], ['err', { ext: 1, errs: [0, 1282] }, false], ['stale', { ext: 1, errs: [1282] }, false], ['throws', { ext: 1, throws: 1 }, false]]) {
  const g = fake(o), a = { e: '-', f: '-', why: '' };
  out[k] = { ok: zrevCheck(g, post, a), e: a.e, f: a.f, why: a.why, unbound: g.fb === null && g.rb === null, freed: g.made === g.gone, samples: g.samples };
}
out.nogl = zrevCheck(null, false, {});
console.log(JSON.stringify(out));
"""
        r = run_node(js)
        self.assertEqual((r['none']['ok'], r['none']['e']), (False, 0))
        self.assertEqual((r['ok']['ok'], r['ok']['e'], r['ok']['f']), (True, 1, 1))
        self.assertTrue(r['ok']['unbound'] and r['ok']['freed'])
        self.assertEqual(r['ok']['samples'], [4, 4])
        self.assertTrue(r['okPost']['ok'])
        self.assertEqual(r['okPost']['samples'], [4, 4, 4, 4])     # RGBA8 and RGBA16F, each with the float depth
        self.assertEqual((r['f16']['ok'], r['f16']['f']), (False, 0))
        self.assertTrue(r['f16phone']['ok'])                      # a phone never draws RGBA16F
        self.assertFalse(r['rgba8']['ok'])
        self.assertFalse(r['err']['ok'])                          # an error the check made
        self.assertTrue(r['stale']['ok'])                         # an error left from before it is not a refusal
        self.assertFalse(r['throws']['ok'])
        self.assertTrue(r['throws']['why'].startswith('check: '))
        self.assertFalse(r['nogl'])

    def test_install(self):
        # zrevInstall on a stand-in renderer over the real three: the projection only inside render, the clear value, the depth
        # function, the shadow pass, the frustum's far plane, the sorts, and the clear-to-near guard
        f = cut_function(self.s, 'zrevInstall')
        js = """
const THREE = require('./three.min.js');
""" + f + """
const log = [];
const ZREV = { on: true, active: false, clip: null, frus: false, renders: 0, noClear: 0, guard: 0, cleared: null, pmrem: false,
  ext: { LOWER_LEFT_EXT: 1, ZERO_TO_ONE_EXT: 2, NEGATIVE_ONE_TO_ONE_EXT: 3, clipControlEXT(o, d) { log.push(['clip', d]); } } };
const D = { clear: 1, func: 0, mask: true, setFunc(f) { this.func = f; }, setClear(v) { this.clear = v; }, setMask(m) { this.mask = m; } };
let target = null, inside = null, cleared = [];
const R = {
  state: { buffers: { depth: D } }, autoClear: true, autoClearDepth: true, opaque: null, transparent: null,
  setOpaqueSort(f) { this.opaque = f; }, setTransparentSort(f) { this.transparent = f; },
  getRenderTarget() { return target; },
  clear(c = true, d = true, s = true) { if (d) cleared.push({ value: D.clear, mask: D.mask, target: target && target.name, active: ZREV.active }); },
  clearDepth() { this.clear(false, true, false); },
  render(sc, cam) {
    // what three does inside: its frustum from the camera's matrices, a material's depth function, the shadow pass
    const m = new THREE.Matrix4().multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse), fr = new THREE.Frustum().setFromProjectionMatrix(m);
    D.setFunc(3); const lequal = D.func; D.setFunc(2); const less = D.func;
    const e = cam.projectionMatrix.elements, p = (w) => { const c = new THREE.Vector4(0, 0, -w, 1).applyMatrix4(cam.projectionMatrix); return c.z / c.w; };
    inside = { row: [e[2], e[6], e[10], e[14]], near: cam.isPerspectiveCamera ? p(cam.near) : null, far: cam.isPerspectiveCamera ? p(cam.far * 0.999) : null, clear: D.clear, lequal, less,
      in09: fr.containsPoint(new THREE.Vector3(0, 0, -cam.far * 0.9)), out11: fr.containsPoint(new THREE.Vector3(0, 0, -cam.far * 1.1)),
      outNear: fr.containsPoint(new THREE.Vector3(0, 0, -cam.near * 0.5)) };
    this.shadowMap.render([], sc, cam);
    inside.after = { clear: D.clear, active: ZREV.active };
  },
  shadowMap: { render() { log.push(['shadow', ZREV.active, D.clear]); } },
};
zrevInstall(R);
const out = {};
const cam = new THREE.PerspectiveCamera(58, 1.6, 0.75, 26000); cam.updateMatrixWorld();
const row0 = Array.from(cam.projectionMatrix.elements);
R.render({}, cam);
out.inside = inside; out.restored = Array.from(cam.projectionMatrix.elements).every((v, i) => v === row0[i]); out.clearAfter = D.clear; out.active = ZREV.active;
out.shadow = log.filter((l) => l[0] === 'shadow');
// the guard: a clear outside, then a render that keeps its depth
const T = { name: 'T' }, U = { name: 'U' };
cleared = []; target = T; R.clear(); R.autoClear = false; R.render({}, cam); out.guard1 = cleared.slice(); out.g1 = ZREV.guard;
cleared = []; R.render({}, cam); out.guard2 = cleared.slice();   // nothing cleared since: its depth is its own
cleared = []; R.autoClear = true; R.clear(); R.render({}, cam); out.guard3 = cleared.slice();   // a render that clears for itself
cleared = []; R.autoClear = false; R.clear(); target = U; R.render({}, cam); out.guard4 = cleared.slice();   // another target's clear
cleared = []; target = T; R.clear(); R.render({}, new THREE.OrthographicCamera()); R.render({}, cam); out.guard5 = cleared.slice();   // an orthographic render took it
cleared = []; ZREV.pmrem = true; R.render({}, cam); ZREV.pmrem = false; out.guard6 = cleared.slice();   // r149's PMREM never clears
R.autoClear = true;
// the sorts: near first (opaque) and far first (transparent) while reversed, three's own otherwise
const a = { groupOrder: 0, renderOrder: 0, material: { id: 1 }, z: 0.9, id: 1 }, b = { groupOrder: 0, renderOrder: 0, material: { id: 1 }, z: 0.1, id: 2 };   // a is nearer when reversed
ZREV.active = true; out.opaqueRev = R.opaque(a, b) < 0; out.transRev = R.transparent(a, b) > 0; ZREV.active = false;
out.opaqueStd = R.opaque(b, a) < 0;
// outside a render three's frustum is three's own
const m = new THREE.Matrix4().multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse);
out.outsideFar = new THREE.Frustum().setFromProjectionMatrix(m).containsPoint(new THREE.Vector3(0, 0, -cam.far * 0.9));
console.log(JSON.stringify(out));
"""
        r = run_node(js)
        i = r['inside']
        self.assertAlmostEqual(i['near'], 1.0, places=5)
        self.assertLess(i['far'], 1e-3)
        self.assertGreaterEqual(i['far'], 0)
        self.assertEqual(i['clear'], 0)
        self.assertEqual((i['lequal'], i['less']), (5, 6))              # GEQUAL and GREATER
        self.assertTrue(i['in09'])
        self.assertFalse(i['out11'])
        self.assertFalse(i['outNear'])
        self.assertEqual(i['after'], {'clear': 0, 'active': True})       # back to reversed after the shadow pass
        self.assertEqual(r['shadow'][0][1:], [False, 1])                 # the shadow pass: standard depth, cleared to 1
        self.assertTrue(r['restored'])
        self.assertEqual((r['clearAfter'], r['active']), (1, False))
        # the guard
        self.assertEqual(len(r['guard1']), 2)
        self.assertEqual(r['guard1'][0], {'value': 1, 'mask': True, 'target': 'T', 'active': False})   # the page's own clear
        self.assertEqual(r['guard1'][1], {'value': 0, 'mask': True, 'target': 'T', 'active': True})    # the guard's, to the far plane
        self.assertEqual(r['g1'], 1)
        self.assertEqual(r['guard2'], [])
        self.assertEqual(len(r['guard3']), 1)
        self.assertEqual(len(r['guard4']), 1)
        self.assertEqual(len(r['guard5']), 1)
        self.assertEqual(r['guard6'], [{'value': 0, 'mask': True, 'target': 'T', 'active': True}])
        self.assertTrue(r['opaqueRev'] and r['transRev'] and r['opaqueStd'])
        self.assertTrue(r['outsideFar'])

    def test_cloud_rects(self):
        # every aircraft over the base on the screen gets a rectangle holding its whole silhouette; one under the base, behind the
        # eye or off the screen gets none; more than sixteen are merged and still cover every plane
        s = self.s
        js = """
const THREE = require('./three.min.js');
const CLOUD_RECT_N = 16;
const CLOUDZ = { cand: [], merged: 0, rects: Array.from({ length: 16 }, () => new THREE.Vector4()), box: new THREE.Vector4() };
const _crV = new THREE.Vector3(), _crS = new THREE.Vector2();
const W = 1600, H = 900;
const renderer = { getDrawingBufferSize: (v) => v.set(W, H) };
const camera = new THREE.PerspectiveCamera(58, W / H, 0.75, 26000);
camera.position.set(0, 120, 0); camera.lookAt(0, 400, -3000); camera.updateMatrixWorld(); camera.updateProjectionMatrix();
let flightReady = true; const FLIGHTS = { on: true };
const mk = (n) => ({ visible: true, count: 0, instanceMatrix: { array: new Float32Array(n * 16) } });
const flightMesh = mk(80), heliMesh = mk(8);
const put = (m, x, y, z, len, yaw) => { const M = new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, yaw, 0.1)), new THREE.Vector3(len, len, len)); M.toArray(m.instanceMatrix.array, m.count * 16); m.count++; };
""" + cut_function(s, 'cloudRects') + "\n" + cut_function(s, 'cloudRectsFit') + """
// a silhouette's points: the unit airliner's extremes (nose, tail, wingtips, fin) under the instance's matrix
const pts = []; for (const p of [[0.5, 0, 0], [-0.5, 0.2, 0], [-0.12, 0, 0.52], [-0.12, 0, -0.52], [-0.45, 0.25, 0], [0.1, -0.08, 0.2]]) pts.push(new THREE.Vector3(...p));
function covered(m, rects) {
  let bad = 0, n = 0;
  const a = m.instanceMatrix.array;
  for (let i = 0; i < m.count; i++) {
    const M = new THREE.Matrix4().fromArray(a, i * 16), len = Math.hypot(a[i * 16], a[i * 16 + 1], a[i * 16 + 2]);
    if (a[i * 16 + 13] + 0.75 * len + 1 < 780) continue;   // under the base: the twin's depth test answers for it
    for (const p of pts) {
      const q = p.clone().applyMatrix4(M), v = q.clone().applyMatrix4(camera.matrixWorldInverse);
      if (-v.z < camera.near) continue;
      const c = q.clone().project(camera), x = (c.x * 0.5 + 0.5) * W, y = (c.y * 0.5 + 0.5) * H;
      if (x < 0 || y < 0 || x >= W || y >= H) continue;
      n++;
      if (!rects.some((r) => x >= r.x && x < r.z && y >= r.y && y < r.w)) bad++;
    }
  }
  return { n, bad };
}
const out = {};
put(flightMesh, 200, 900, -2500, 60, 0.3);        // over the base, in view
put(flightMesh, -300, 500, -2000, 40, 1.0);       // under the base: in front of every cloud
put(flightMesh, 0, 1200, 3000, 60, 0);            // behind the eye
put(flightMesh, 9000, 900, -1000, 60, 0);         // off the screen to the right
put(flightMesh, -150, 830, -1500, 70, 2.0);       // nearer, over the base
const n1 = cloudRects(780);
out.one = { n: n1, cov: covered(flightMesh, CLOUDZ.rects.slice(0, n1)), box: CLOUDZ.box.toArray() };
// forty planes over the base across the sky: merged to sixteen, every one still covered
flightMesh.count = 0;
let seed = 3; const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
for (let i = 0; i < 40; i++) put(flightMesh, (rnd() - 0.5) * 6000, 900 + rnd() * 3000, -1500 - rnd() * 9000, 30 + rnd() * 40, rnd() * 6);
const n2 = cloudRects(780);
out.many = { n: n2, merged: CLOUDZ.merged, cov: covered(flightMesh, CLOUDZ.rects.slice(0, n2)) };
// the box is the scissor: every rectangle inside it
const B = CLOUDZ.box; out.boxHolds = CLOUDZ.rects.slice(0, n2).every((r) => r.x >= B.x && r.y >= B.y && r.z <= B.x + B.z && r.w <= B.y + B.w);
// the layer off: none
FLIGHTS.on = false; out.off = cloudRects(780); FLIGHTS.on = true;
// a plane the near plane cuts takes the screen
flightMesh.count = 0; put(flightMesh, 0, 900, -1, 70, 0); camera.position.set(0, 890, 30); camera.lookAt(0, 890, -1000); camera.updateMatrixWorld();
const n3 = cloudRects(780); out.near = { n: n3, r: CLOUDZ.rects[0].toArray() };
console.log(JSON.stringify(out));
"""
        r = run_node(js)
        self.assertEqual(r['one']['n'], 2)
        self.assertGreater(r['one']['cov']['n'], 6)
        self.assertEqual(r['one']['cov']['bad'], 0)
        self.assertEqual(r['many']['n'], 16)
        self.assertGreater(r['many']['merged'], 0)
        self.assertGreater(r['many']['cov']['n'], 100)
        self.assertEqual(r['many']['cov']['bad'], 0)
        self.assertTrue(r['boxHolds'])
        self.assertEqual(r['off'], 0)
        self.assertEqual(r['near'], {'n': 1, 'r': [0, 0, 1600, 900]})


if __name__ == '__main__':
    unittest.main()
