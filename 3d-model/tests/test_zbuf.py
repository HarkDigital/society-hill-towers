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
- nothing else in the page writes gl_FragDepth but the river mirror's point sprites, whose twins write the depth of their
  own pixel on the sprite's plane (the review's must-fix: under the oblique row a sprite's one depth let the far shore's
  lamps through the walls in front of them), and every gl_Position.z the page sets is one this file knows;
- the guard is per target and survives other renders; the extension must be seen to clip; a crumb or an Android phone keeps
  log depth (?zbuf=rev overrides both); a float depth target that fails at full size leaves the crumb, and the frame's own
  reloads once;
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
        self.assertIn("else if (mode === 'rev' && !zrevClipWorks(g2, ZPROBE)) { mode = 'log';", s)
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
        self.assertIn('ZREV.status = zrevFloatDepth(postRT);', s)
        self.assertIn('REFL.zst = zrevFloatDepth(REFL.rt);', s)
        refl = s[s.index('      REFL.rt = new THREE.WebGLRenderTarget('):]
        refl = refl[:refl.index('\n', refl.index('\n') + 1)]
        self.assertIn('stencilBuffer: true', refl)        # the vehicle shadows' stencil in the mirror too
        self.assertNotIn('depthTexture', refl)
        # the mirror's anisotropy is set before zrevFloatDepth makes its framebuffers (three sets a target texture's parameters
        # only then: the other way round its streaks lost the anisotropic filter and blurred, found in the parity renders)
        self.assertLess(s.index('REFL.rt.texture.anisotropy = renderer.capabilities.getMaxAnisotropy();'), s.index('REFL.zst = zrevFloatDepth(REFL.rt);'))
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
        self.assertEqual(len(writes), 3, writes)
        self.assertTrue(all('logDepthBufFC' in w or 'hitClip' in w or 'uMirZ' in w for w in writes), writes)
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
        self.assertIn("ZPROBE.mode + (ZPROBE.forced ? 'q' : '') + (ZPROBE.crumb ? 'c' : '') + (ZPROBE.android ? 'a' : '') + '.' + ZPROBE.e + ZPROBE.f + ZPROBE.k + ZPROBE.real + '.' + blit + (bad ? '0' : '')", z)
        # the trailing 0 covers every float depth target, the mirror's and the occlusion copy's too, and a failed blit
        self.assertIn('[ZREV.status, ZREV.aoStatus, mirror].some(', z)
        self.assertIn('!!ZREV.fail', z)
        self.assertIn("ZREV.blit === 'failed' ? 'x'", z)
        # the second review: 'p' is the real context's post pipeline whatever ZREV.sub says (the throwaway context's answer)
        self.assertIn(": ZREV.on && POST.on ? 'p' : '-';", z)
        self.assertNotIn('!ZREV.sub && POST.on', z)

    def test_a_failed_float_depth_target_falls_back(self):
        s = self.s
        f = cut_function(s, 'zrevFail')
        self.assertIn("localStorage.setItem(ZBUF_KEY, JSON.stringify({ t: Date.now(), why: ZREV.fail }))", f)
        self.assertIn("beacon('zbuf', { zf: what, zs: code });", f)
        self.assertIn("sessionStorage.getItem('philly3d.zbufre')", f)
        # every float depth target is checked where it is made, at full size
        self.assertIn("if (ZREV.status && ZREV.status !== 36053) zrevFail('post', ZREV.status, true);", s)
        self.assertIn("if (ZREV.status !== gl.FRAMEBUFFER_COMPLETE) { zrevFail('sub', ZREV.status, true); return; }", s)
        self.assertIn("zrevFail('refl', REFL.zst, false); REFL.on = false;", s)
        self.assertIn("zrevFail('ao', ZREV.aoStatus, false); AO.on = false;", s)
        p = cut_function(s, 'zrevPresent')
        self.assertIn("if (err !== gl.NO_ERROR && ZREV.rfb) {", p)
        self.assertIn("zrevFail('blit', err, true);", p)
        # the second review: the phone's new target is presented once at once, during the build's first render, so a canvas
        # that takes neither blit reloads in seconds, not after the whole build
        fb = s[s.index('    ZREV.fbInit = function zrevFB() {'):]
        fb = fb[:fb.index('\n    };\n')]
        self.assertIn("if (first && !ZREV.blit) {\n        zrevPresent(true);", fb)
        self.assertLess(fb.index("zrevFail('sub', ZREV.status, true); return; }"), fb.index('zrevPresent(true)'))
        self.assertLess(fb.index('ZREV.w = w; ZREV.h = h;'), fb.index('zrevPresent(true)'))
        self.assertIn('if (test) ZREV.tested = performance.now(); else ZREV.presents++;', p)
        self.assertIn('return zrevPresent(test);', p)
        self.assertIn("if (ZREV.sub && this.getRenderTarget() === null && ZREV.fbInit) { ZREV.fbInit(); this.setRenderTarget(null); }", s)

    def test_a_lost_context_is_no_failure(self):
        # the second review's must-fix: on a lost context every check answers with a failure (36061, CONTEXT_LOST_WEBGL); a
        # frame that resizes between the loss and the handler wrote the fortnight's crumb and set off a zbuf reload. Every
        # check returns before it records a status, and zrevFail does nothing there
        s = self.s
        self.assertIn('function zrevLost() { try { return renderer.getContext().isContextLost(); } catch (e) { return false; } }', s)
        self.assertTrue(cut_function(s, 'zrevFail').split('\n')[1].strip().startswith('if (zrevLost()) return;'))
        self.assertTrue(cut_function(s, 'zrevFloatDepth').split('\n')[1].strip().startswith('if (zrevLost()) return 0;'))
        self.assertTrue(cut_function(s, 'zrevAoDepth').split('\n')[1].strip().startswith('if (zrevLost()) return;'))
        p = cut_function(s, 'zrevPresent')
        self.assertLess(p.index('if (zrevLost()) return;'), p.index('gl.getError()'))
        self.assertIn('if (err !== gl.NO_ERROR && zrevLost()) return;', p)
        self.assertLess(p.index('if (err !== gl.NO_ERROR && zrevLost()) return;'), p.index("ZREV.blit = 'failed'"))
        fb = s[s.index('    ZREV.fbInit = function zrevFB() {'):]
        fb = fb[:fb.index('\n    };\n')]
        self.assertLess(fb.index('if (zrevLost()) return;'), fb.index('ZREV.status = gl.checkFramebufferStatus'))
        self.assertIn("if (ZREV.on && !zrevLost()) {   // Round 192: the samples' depth DEPTH32F_STENCIL8", s)
        self.assertIn("if (ZREV.on && !zrevLost()) {   // (the second review: nothing recorded on a lost context)\n        REFL.zst = zrevFloatDepth(REFL.rt);", s)

    def test_the_mirror_sprites_twins(self):
        s = self.s
        self.assertIn("if (ZREV.on && !MIRZ.off) mirzSwap(C);", s)
        refl = cut_function(s, 'reflRender')
        self.assertLess(refl.index('mirzSwap(C)'), refl.index('r.render(sc, C);'))
        self.assertLess(refl.index('r.render(sc, C);'), refl.index('mirzBack();'))
        self.assertIn('finally {\n      mirzBack();', refl)
        sw = cut_function(s, 'mirzSwap')
        self.assertIn('MIRZ.u.value.set(2 * row[0] / (e[0] * REFL.w), 2 * row[1] / (e[5] * REFL.h), REFL.w, REFL.h); MIRZ.far.value = C.far;', sw)
        self.assertIn('if (!o.isPoints ||', sw)
        t = cut_function(s, 'mirzTwin')
        self.assertIn("customProgramCacheKey = () => m.customProgramCacheKey() + '|mirz'", t)
        self.assertIn('uniforms: Object.assign({}, m.uniforms, { uMirZ: MIRZ.u, uMirF: MIRZ.far })', t)
        # the second review: the twins are built behind the veil, on the second frame, through the mirror's own lights and
        # settings into a scratch target, and everything forced for that draw is put back
        self.assertIn("if (!MIRZ.warmed && frameNo >= 2) mirzWarm();", cut_function(s, 'waterFrame'))
        w = cut_function(s, 'mirzWarm')
        self.assertIn('MIRZ.warmed = true;\n    if (!ZREV.on || MIRZ.off || !REFL.on || zrevLost()) return;', w)
        self.assertIn('reflSweep();', w)
        self.assertIn('if (o.isLight && o.layers.isEnabled(L) && !o.layers.isEnabled(W)) { o.layers.enable(W);', w)
        self.assertIn('C.layers.set(W);', w)
        self.assertIn('r.shadowMap.autoUpdate = false; r.shadowMap.needsUpdate = false; scene.background = null;', w)
        self.assertIn('zrevFloatDepth(rt);', w)
        self.assertIn('for (let i = undo.length - 1; i >= 0; i--) undo[i]();', w)
        self.assertIn('C.layers.mask = prevMask;', w)
        self.assertIn('rt.dispose();', w)
        self.assertIn('mirzSync(t, m);', w)
        self.assertIn('mirzSync(t, m);', sw)
        self.assertEqual(len(re.findall(r'layers\.(?:set|enable)\(30\)|MIRZ_WARM_LAYER = 30', s)), 1)   # the warm's layer is its own


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

    def test_mirror_sprite_depth(self):
        # the twins' depth (MIRZ): the centre's depth plus the slope times the pixel offset is the oblique row's depth of the
        # point on the sprite's plane under that pixel (the window's y up, the crop in the projection's scale and offset), and
        # against it a point on the same pixel's ray nearer than the plane is nearer (it hides the sprite) and one past it is
        # farther; the bare centre depth (the spike's sprite) let points in front of it lose
        s = self.s
        refl = cut_function(s, 'reflRender')
        body = refl[refl.index('    const C = REFL.cam;'):refl.index('    C.projectionMatrixInverse.copy(C.projectionMatrix).invert();')]
        sw = cut_function(s, 'mirzSwap')
        slope = re.search(r'MIRZ\.u\.value\.set\(([^;]+)\);', sw).group(1)
        js = """
const THREE = require('./three.min.js');
const W0 = -7.34, REFL_FAR = 3500, ZREV = { on: true };
const REFL = { cam: new THREE.PerspectiveCamera(), box: [-0.55, 0.7, -0.6, 0.35], w: 640, h: 400 };
const MIRZ = { u: { value: new THREE.Vector4() } };
const waterU = { uReflMat: { value: new THREE.Matrix4() } };
const _rfA = new THREE.Vector3(), _rfN = new THREE.Vector3(0, 1, 0), _rfP = new THREE.Plane(), _rfV = new THREE.Vector4(), _rfQ = new THREE.Vector4();
const cam = new THREE.PerspectiveCamera(60, 1.6, 0.75, 26000);
cam.position.set(100, W0 + 5, -40); cam.lookAt(900, W0 + 2, -300); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
""" + body + """
const row = C.userData.zrevRow;
{ const e = C.projectionMatrix.elements; MIRZ.u.value.set(""" + slope + """); }
const S = MIRZ.u.value, Wd = REFL.w, Hd = REFL.h;
const depthOf = (v) => (row[0] * v.x + row[1] * v.y + row[2] * v.z + row[3]) / (-v.z);
const ndcOf = (v) => [(e[0] * v.x + e[8] * v.z + e[12]) / (-v.z), (e[5] * v.y + e[9] * v.z + e[13]) / (-v.z)];
const heightOf = (v) => v.clone().applyMatrix4(C.matrixWorld).y - W0;
let n = 0, worst = 0, nearer = 0, farther = 0, tried = 0, bare = 0, btried = 0;
let seed = 7; const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
for (let k = 0; k < 400; k++) {
  const d = 60 + rnd() * 2500, nx = rnd() * 1.6 - 0.8, ny = rnd() * 1.6 - 0.8;
  const c = new THREE.Vector3(d * (nx + e[8]) / e[0], d * (ny + e[9]) / e[5], -d);   // a sprite centre at that NDC and depth
  if (heightOf(c) < 3) continue;
  const dc = depthOf(c), [cx, cy] = ndcOf(c), wx = (cx * 0.5 + 0.5) * Wd, wy = (cy * 0.5 + 0.5) * Hd;
  for (const [dx, dy] of [[0, 0], [9, 0], [-9, 4], [3, 12], [0, -12], [11, -7]]) {
    const fx = cx + 2 * dx / Wd, fy = cy + 2 * dy / Hd;   // the fragment's NDC
    const p = new THREE.Vector3(d * (fx + e[8]) / e[0], d * (fy + e[9]) / e[5], -d);   // its point on the sprite's plane
    const twin = dc + S.x * dx + S.y * dy, exact = depthOf(p);
    worst = Math.max(worst, Math.abs(twin - exact)); n++;
    if (heightOf(p) < 0.5) continue;
    for (const f of [0.6, 0.9, 0.98]) { const q = p.clone().multiplyScalar(f); if (heightOf(q) < 0.1) continue; tried++; if (depthOf(q) > twin) nearer++; if (depthOf(q) > dc) bare++; }
    for (const f of [1.02, 1.3]) { const q = p.clone().multiplyScalar(f); btried++; if (depthOf(q) < twin) farther++; }
  }
}
console.log(JSON.stringify({ n, worst, tried, nearer, farther, btried, bare, slope: [S.x, S.y] }));
"""
        r = run_node(js)
        self.assertGreater(r['n'], 1000)
        self.assertLess(r['worst'], 1e-6)
        self.assertGreater(r['tried'], 500)
        self.assertEqual(r['nearer'], r['tried'])        # whatever stands in front on the pixel's ray hides the sprite there
        self.assertGreater(r['btried'], 500)
        self.assertEqual(r['farther'], r['btried'])      # and what stands past the sprite's plane does not
        self.assertLess(r['bare'], r['tried'])           # the centre's bare depth: some in front lost to it (the must-fix)

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

    def test_mode(self):
        # the depth-mode block under Node with fake contexts: the default, the flags, the clip test, the crumb, an Android phone
        s = self.s
        i = s.index('  const ZPROBE = {')
        j = s.index("    if (ZPROBE.why) console.warn('zbuf: log depth (' + ZPROBE.why + ')');", i)
        block = s[i:j] + "  } catch (e) { threw = String(e && e.message || e); }\n"
        js = """
function fakeGL(c) {
  const g = { FRAMEBUFFER: 1, RENDERBUFFER: 2, RGBA8: 3, RGBA16F: 4, DEPTH32F_STENCIL8: 5, COLOR_ATTACHMENT0: 6, DEPTH_STENCIL_ATTACHMENT: 7, FRAMEBUFFER_COMPLETE: 36053,
    NO_ERROR: 0, MAX_SAMPLES: 8, VERTEX_SHADER: 9, FRAGMENT_SHADER: 10, LINK_STATUS: 11, ARRAY_BUFFER: 12, STATIC_DRAW: 13, FLOAT: 14, DEPTH_TEST: 15,
    COLOR_BUFFER_BIT: 16, POINTS: 17, RGBA: 18, UNSIGNED_BYTE: 19, depth: 3, z: 0, lit: false,
    getExtension(n) {
      if (n === 'EXT_clip_control') return c.ext ? { LOWER_LEFT_EXT: 1, ZERO_TO_ONE_EXT: 2, NEGATIVE_ONE_TO_ONE_EXT: 3, clipControlEXT: (o, d) => { g.depth = c.clip === 'stuck' ? 3 : d; } } : null;
      if (n === 'EXT_color_buffer_float') return {};
      if (n === 'WEBGL_lose_context') return { loseContext() {} };
      return null; },
    getParameter: () => 4, getError: () => 0, createFramebuffer: () => ({}), createRenderbuffer: () => ({}), createBuffer: () => ({}), createProgram: () => ({}),
    createShader: () => ({}), shaderSource() {}, compileShader() {}, attachShader() {}, bindAttribLocation() {}, linkProgram() {}, getProgramParameter: () => true,
    bindFramebuffer() {}, bindRenderbuffer() {}, bindBuffer() {}, bufferData() {}, enableVertexAttribArray() {}, vertexAttribPointer() {},
    renderbufferStorageMultisample() {}, renderbufferStorage() {}, framebufferRenderbuffer() {}, checkFramebufferStatus: () => (c.fb === false ? 36054 : 36053),
    viewport() {}, disable() {}, useProgram() {}, getUniformLocation: () => ({}), clearColor() {}, clear() { g.lit = false; }, uniform1f(l, z) { g.z = z; },
    drawArrays() { g.lit = g.depth === 2 ? g.z >= 0 && g.z <= 1 : g.z >= -1 && g.z <= 1; }, readPixels(x, y, w, h, f, t, px) { px[0] = g.lit ? 255 : 0; },
    deleteFramebuffer() {}, deleteRenderbuffer() {}, deleteBuffer() {}, deleteProgram() {}, deleteShader() {} };
  return g;
}
function load(o) {
  const LS = o.ls || new Map(), made = [];
  const location = { search: o.search || '' }, navigator = { userAgent: o.ua || 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)' };
  const isTouch = !!o.touch, window = {}, veil = { style: {} }, console = { warn() {} };
  const localStorage = { getItem: (k) => (LS.has(k) ? LS.get(k) : null), setItem: (k, v) => LS.set(k, String(v)), removeItem: (k) => LS.delete(k) };
  const document = { createElement: () => ({ getContext: () => (o.g2 === null ? null : fakeGL(o.g2 || o.gl)) }), getElementById: () => ({ style: {} }) };
  let canvas = { cloneNode() { return { replaceWith() {} }; }, replaceWith() {} };
  const THREE = { WebGLRenderer: function (opts) { made.push(opts); this.getContext = () => fakeGL(o.real || o.gl); this.capabilities = { isWebGL2: true }; this.dispose = () => {}; this.forceContextLoss = () => {}; } };
  let renderer, threw = null;
  BLOCK
  return { mode: ZPROBE.mode, why: ZPROBE.why, e: ZPROBE.e, f: ZPROBE.f, k: ZPROBE.k, crumb: ZPROBE.crumb, android: ZPROBE.android, forced: ZPROBE.forced, sub: !!window.__zrevSub, logDepth: !!window.__useLogDepth, renderers: made.length, threw, kept: LS.has('philly3d.zbuf') };
}
const good = { ext: 1, fb: true, clip: 'good' }, iphone = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X)', pixel = 'Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 Chrome/141.0 Mobile Safari/537.36';
const out = {};
out.desk = load({ gl: good });
out.phone = load({ gl: good, touch: true, ua: iphone });
out.forcedLog = load({ gl: good, search: '?zbuf=log' });
out.noExt = load({ gl: { ext: 0 } });
out.noFb = load({ gl: { ext: 1, fb: false } });
out.stuck = load({ gl: { ext: 1, fb: true, clip: 'stuck' } });   // lists the extension, still clips by -1..1
out.noGl2 = load({ gl: good, g2: null, touch: true, ua: iphone });
const fresh = () => new Map([['philly3d.zbuf', JSON.stringify({ t: Date.now() - 86400000, why: 'post 36054' })]]);
out.crumb = load({ gl: good, ls: fresh() });
out.crumbRev = load({ gl: good, ls: fresh(), search: '?zbuf=rev' });
out.stale = load({ gl: good, ls: new Map([['philly3d.zbuf', JSON.stringify({ t: Date.now() - 15 * 86400000, why: 'post 36054' })]]) });
out.android = load({ gl: good, touch: true, ua: pixel });
out.androidRev = load({ gl: good, touch: true, ua: pixel, search: '?zbuf=rev' });
out.androidTablet = load({ gl: good, touch: false, ua: pixel });
out.realRefuses = load({ g2: good, real: { ext: 1, fb: false }, touch: true, ua: iphone });
console.log(JSON.stringify(out));
""".replace('BLOCK', block)
        r = run_node(js)
        self.assertEqual((r['desk']['mode'], r['desk']['e'], r['desk']['f'], r['desk']['k'], r['desk']['sub']), ('rev', 1, 1, 1, False))
        self.assertEqual((r['phone']['mode'], r['phone']['sub'], r['phone']['android']), ('rev', True, False))
        self.assertEqual((r['forcedLog']['mode'], r['forcedLog']['forced'], r['forcedLog']['logDepth']), ('log', True, True))
        self.assertEqual((r['noExt']['mode'], r['noExt']['e']), ('log', 0))
        self.assertEqual((r['noFb']['mode'], r['noFb']['f']), ('log', 0))
        self.assertEqual((r['stuck']['mode'], r['stuck']['k']), ('log', 0))          # the clip test refuses a driver that does not clip
        self.assertIn('does not clip', r['stuck']['why'])
        self.assertEqual(r['noGl2']['mode'], 'log')
        self.assertEqual((r['crumb']['mode'], r['crumb']['crumb'], r['crumb']['k']), ('log', True, 1))   # the probe still ran
        self.assertIn('post 36054', r['crumb']['why'])
        self.assertEqual(r['crumbRev']['mode'], 'rev')                                  # ?zbuf=rev overrides the crumb
        self.assertEqual((r['stale']['mode'], r['stale']['kept']), ('rev', False))     # a fortnight on, the crumb goes
        self.assertEqual((r['android']['mode'], r['android']['android'], r['android']['e'], r['android']['f'], r['android']['k']), ('log', True, 1, 1, 1))
        self.assertEqual(r['androidRev']['mode'], 'rev')
        self.assertEqual(r['androidTablet']['mode'], 'rev')                             # no touch: the post pipeline's path, not the hold's
        self.assertEqual((r['realRefuses']['mode'], r['realRefuses']['renderers']), ('log', 2))
        for k, v in r.items():
            self.assertIsNone(v['threw'], k)

    def test_fail(self):
        # zrevFail: the first failure leaves the crumb and a beacon; the frame's own reloads once a tab, a pass's does not
        f = cut_function(self.s, 'zrevFail')
        lost = cut_function(self.s, 'zrevLost') + '\n'
        js = """
const ZBUF_KEY = 'philly3d.zbuf';
function run(seq, sessHas, lost) {
  const LS = new Map(), SS = new Map(sessHas ? [['philly3d.zbufre', '1']] : []), beacons = [];
  let reloads = 0;
  const ZREV = {}, localStorage = { setItem: (k, v) => LS.set(k, v) }, sessionStorage = { getItem: (k) => (SS.has(k) ? SS.get(k) : null), setItem: (k, v) => SS.set(k, v) };
  const location = { reload: () => reloads++ }, setTimeout = (fn) => fn(), console = { warn() {} }, beacon = (st, q) => beacons.push([st, q]);
  const renderer = { getContext: () => ({ isContextLost: () => !!lost }) };
  """ + lost + f + """
  for (const [w, c, fatal] of seq) zrevFail(w, c, fatal);
  return { crumb: LS.has(ZBUF_KEY) ? JSON.parse(LS.get(ZBUF_KEY)).why : null, beacons, reloads, fail: ZREV.fail || null, sess: SS.has('philly3d.zbufre') };
}
console.log(JSON.stringify({ post: run([['post', 36054, true]]), again: run([['post', 36054, true]], true), refl: run([['refl', 36054, false]]),
  twice: run([['ao', 36061, false], ['blit', 1282, true]]),
  lost: run([['post', 36061, true], ['sub', 36061, true], ['ao', 36061, false], ['refl', 36061, false], ['blit', 37442, true]], false, true) }));
"""
        r = run_node(js)
        # the second review's must-fix: on a lost context no crumb, no beacon, no reload and no sessionStorage mark (the
        # webglcontextlost handler's recovery is the only one)
        self.assertEqual((r['lost']['crumb'], r['lost']['beacons'], r['lost']['reloads'], r['lost']['fail'], r['lost']['sess']), (None, [], 0, None, False))
        self.assertEqual((r['post']['crumb'], r['post']['reloads'], r['post']['beacons']), ('post 36054', 1, [['zbuf', {'zf': 'post', 'zs': 36054}]]))
        self.assertEqual((r['again']['crumb'], r['again']['reloads']), ('post 36054', 0))   # a second failure in the tab: no loop
        self.assertEqual((r['refl']['crumb'], r['refl']['reloads']), ('refl 36054', 0))
        self.assertEqual((r['twice']['fail'], r['twice']['reloads'], len(r['twice']['beacons'])), ('ao 36061', 1, 1))   # the first answer is the crumb's, a lost frame still reloads

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
cleared = []; target = T; R.clear(); R.render({}, new THREE.OrthographicCamera()); R.render({}, cam); out.guard5 = cleared.slice();   // an orthographic render between: still guarded (the review)
cleared = []; target = T; R.clear(); target = U; R.autoClear = true; R.render({}, cam); R.autoClear = false; target = T; R.render({}, cam); out.guard7 = cleared.slice();   // a reversed render of another target between
cleared = []; target = T; R.render({}, cam); out.guard8 = cleared.slice();   // T's depth is a reversed render's now: no guard
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
        self.assertEqual(len(r['guard5']), 2)                             # the page's clear, then the guard's after the orthographic render
        self.assertEqual(r['guard5'][1], {'value': 0, 'mask': True, 'target': 'T', 'active': True})
        self.assertEqual([c['target'] for c in r['guard7']], ['T', 'T'])   # T's clear, then the guard's on T (the stand-in's render does not clear U for itself)
        self.assertEqual(r['guard7'][1]['value'], 0)
        self.assertEqual(r['guard8'], [])
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
