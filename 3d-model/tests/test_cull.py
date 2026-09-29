"""Round 167: the phones draw fewer triangles with nothing on screen changed.

- The tree meshes cull: r149's InstancedMesh never did (its constructor turns frustumCulled off), so all 68 of them,
  2.27 M triangles on a phone, drew in every view. fitInstSphere gives each mesh a sphere round every instance as its
  shader draws it (a crown lumped up to CROWN_GROW and swayed CROWN_SLACK), run here under Node against random poses.
- The El's and PATCO's ties are runs of about TIE_RUN metres (tieRuns), each culled by its own sphere and by nothing
  else, where they were two meshes drawn from everywhere. (A hide past 700 m went in with them and came out on review:
  the ties still reached a pixel and a half there, and an El overview differed by 751 pixels. Culling alone changes no
  pixel, which the Node run below checks against random eyes: a run with any corner of any tie in view is never culled.)
- Every mesh newly culled draws unculled once behind the veil (pendingUpload, released after the first frame), so it
  uploads there as before (handoff gotcha 12).
- The pins' depth image is read back through a pixel pack buffer behind a fence on WebGL 2 (PIN_ASYNC), installed with
  its own matrices only once the fence has passed; run here under Node against a scripted WebGL 2 context. A turn that
  finds a read in flight tries again the next frame, so late fences cost no whole cadence.
"""
import json
import re
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
THREE = json.dumps(str(ROOT / 'three.min.js'))


def cut(start, end):
    a = SRC.index(start)
    return SRC[a:SRC.index(end, a)]


# the tree step's shapes, cut from the source so the test fits the real ones (Round 167 review: the vase is concatGeo's
# cylinder AND its scaled icosahedron cap); run under both values of isTouch, as the step builds them
SHAPES = (cut('    const trunkCoreG = new THREE.CylinderGeometry(', '    const canWideG = ')
          + cut('    const canWideG = ', '\n') + '\n'
          + cut('    const coneG = new THREE.ConeGeometry(', '    const CHN = 3;'))


def node(script):
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class FitInstSphere(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        script = r'''
const THREE = require(THREE_PATH);
FIT
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const out = [];
// the tree shapes exactly as the step builds them (cut from app.js, both crown details), and the ties' boxes
const SH = {};
for (const isTouch of [false, true]) {
SHAPES
  Object.assign(SH, isTouch ? { crownWideTouch: canWideG } : { trunkCore: trunkCoreG, trunkWide: trunkWideG, crownCore: canCoreG, crownWide: canWideG,
    cone: coneG, vase: vaseG, pyramid: pyrG, crownOuter: canOuterG, trunkOuter: trunkOuterG });
}
const shapes = Object.fromEntries(Object.entries(SH).map(([k, g]) => [k, () => g.clone()]));
shapes.tie = () => new THREE.BoxGeometry(0.24, 0.14, 2.7);
shapes.patcoTie = () => new THREE.BoxGeometry(0.24, 0.14, 2.6);
for (const [name, make] of Object.entries(shapes)) {
  for (const [grow, slack] of [[1, 0], [1.21, 0.1]]) {
    const g = make(), n = 300, m = new THREE.InstancedMesh(g, new THREE.MeshBasicMaterial(), n);
    const mt = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();
    for (let i = 0; i < n; i++) {
      q.setFromEuler(new THREE.Euler(name === 'tie' ? (rnd() - 0.5) * 0.2 : 0, rnd() * 6.3, name === 'tie' ? (rnd() - 0.5) * 0.2 : 0, 'YXZ'));
      p.set(-3000 + rnd() * 6000, -8 + rnd() * 140, -4000 + rnd() * 9000);
      s.set(0.5 + rnd() * 9, 0.5 + rnd() * 14, 0.5 + rnd() * 9);
      m.setMatrixAt(i, mt.compose(p, q, s));
    }
    const bb = fitInstSphere(m, grow, slack, 0);
    const sp = m.geometry.boundingSphere, pos = g.attributes.position, v = new THREE.Vector3(), e = new THREE.Matrix4();
    // every vertex as a shader may move it: scaled by up to `grow` about the shape's origin, then pushed `slack` any way
    let worst = -Infinity, outBox = 0;
    for (let i = 0; i < n; i++) {
      m.getMatrixAt(i, e);
      const ms = e.getMaxScaleOnAxis();
      for (let k = 0; k < pos.count; k++) {
        for (const f of [0.79, 1, grow]) {
          v.fromBufferAttribute(pos, k).multiplyScalar(f).applyMatrix4(e);
          const d = v.distanceTo(sp.center) + slack * ms - sp.radius;
          worst = Math.max(worst, d);
          if (v.x < bb[0] - 1e-6 || v.x > bb[1] + 1e-6 || v.y < bb[2] - 1e-6 || v.y > bb[3] + 1e-6 || v.z < bb[4] - 1e-6 || v.z > bb[5] + 1e-6) outBox++;
        }
      }
    }
    // and the sphere is not wildly loose: within the box's half diagonal plus the largest instance sphere
    const half = Math.hypot(bb[1] - bb[0], bb[3] - bb[2], bb[5] - bb[4]) / 2;
    out.push({ name, grow, worst, outBox, loose: sp.radius <= half + 1e-6, radius: sp.radius });
  }
}
// the empty mesh: no sphere to hit
const e0 = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial(), 0);
fitInstSphere(e0, 1, 0, 0);
const es = e0.geometry.boundingSphere;
out.push({ finite: [es.center.x, es.center.y, es.center.z, es.radius].every(Number.isFinite) });
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', THREE).replace('FIT', cut('  function fitInstSphere(', '  // ring meshes upload in batches')).replace('SHAPES', SHAPES)
        cls.rows = node(script)

    def test_every_vertex_as_drawn_is_inside(self):
        names = {r['name'] for r in self.rows[:-1]}
        self.assertTrue({'vase', 'pyramid', 'cone', 'crownCore', 'crownWide', 'crownWideTouch', 'crownOuter', 'trunkCore', 'trunkWide', 'trunkOuter', 'tie'} <= names, names)
        for r in self.rows[:-1]:
            self.assertLessEqual(r['worst'], 1e-6, r)       # no vertex, lumped and swayed, outside the sphere
            self.assertEqual(r['outBox'], 0, r)             # nor outside the box fitInstSphere returns
            self.assertTrue(r['loose'], r)

    def test_an_empty_mesh_gets_a_finite_sphere(self):
        self.assertTrue(self.rows[-1]['finite'])   # a NaN centre would pass every frustum test


class Trees(unittest.TestCase):
    def test_crown_bounds_match_the_shader(self):
        # the lumps: transformed *= 0.79 + 0.42 * vh, vh in [0, 1); CROWN_GROW must be their top
        self.assertIn('transformed *= 0.79 + 0.42 * vh;', SRC)
        grow = float(re.search(r'const CROWN_GROW = ([\d.]+), CROWN_SLACK = ([\d.]+);', SRC).group(1))
        slack = float(re.search(r'const CROWN_GROW = ([\d.]+), CROWN_SLACK = ([\d.]+);', SRC).group(2))
        self.assertAlmostEqual(grow, 0.79 + 0.42)
        # the sway: sw = sin * 0.6 + sin * 0.25, x by 0.07, z by 0.035, y by 0.02, all times up (at most 1)
        sway = SRC[SRC.index('const canopySway = (sh) => {'):SRC.index('cloudShadowPatch(sh,', SRC.index('const canopySway = (sh) => {'))]
        self.assertIn('float sw = sin(uTime * 1.1 + ph) * 0.6 + sin(uTime * 2.3 + ph * 3.1) * 0.25;', sway)
        self.assertIn('transformed.x += sw * 0.07 * up; transformed.z += sw * 0.035 * up; transformed.y += sin(uTime * 3.1 + ph * 5.0 + position.x * 2.0) * 0.02 * up;', sway)
        self.assertGreaterEqual(slack, ((0.85 * 0.07) ** 2 + (0.85 * 0.035) ** 2 + 0.02 ** 2) ** 0.5)

    def test_every_tree_mesh_is_fitted_and_uploads_behind_the_veil(self):
        step = cut("  step('Planting the street trees',", '  function plantProceduralTrees() {')
        self.assertNotIn('g2.boundingSphere = new THREE.Sphere', step)   # the hand-set chunk spheres are gone
        self.assertIn('treeMeshes.push(im);', step)
        self.assertEqual(step.count('new THREE.InstancedMesh('), 1)       # every tree mesh is made by instMesh
        fit = step[step.index('for (const im of treeMeshes) {'):]
        self.assertIn('fitInstSphere(im, crown ? CROWN_GROW : 1, crown ? CROWN_SLACK : 0, 2);', fit)
        self.assertIn('im.frustumCulled = false; pendingUpload.push(im);', fit)
        # fitted after every mesh is posed: the loop is the step's last work
        self.assertGreater(step.index('for (const im of treeMeshes) {'), step.rindex('setMatrixAt('))
        self.assertGreater(step.index('for (const im of treeMeshes) {'), step.rindex('instMesh('))


class TiesAndUploads(unittest.TestCase):
    def test_tie_runs(self):
        runs = cut('  function tieRuns(', '  // One cached alignment/profile')
        self.assertIn('const TIE_RUN = 500, TIE_RUNS = [];', SRC)
        self.assertIn('fitInstSphere(run, 1, 0, 1);', runs)
        self.assertIn('TIE_RUNS.push(run);', runs)
        self.assertIn('freeOnUpload(run.geometry);', runs)
        self.assertIn('run.instanceMatrix.onUpload(dropUploadedArray);', runs)
        self.assertIn('run.frustumCulled = false; pendingUpload.push(run);', runs)
        # the sphere is taken before anything can drop the matrices
        self.assertLess(runs.index('fitInstSphere(run'), runs.index('run.instanceMatrix.onUpload('))
        self.assertIn("tieRuns(sleepers, new THREE.BoxGeometry(EL_RAIL.tieWidth, 0.14, EL_RAIL.tieLength),", SRC)
        self.assertIn("const tm = tieRuns(ties, new THREE.BoxGeometry(0.24, 0.14, 2.6),", SRC)

    def test_no_run_is_hidden_by_distance(self):
        # Round 167 review: the hide past TIE_NEAR (tieRunsNear) changed pixels along the El and PATCO (751 px of an El
        # overview by day), so it is gone; a run is culled by the frustum alone, and nothing else touches its visibility
        for gone in ('tieRunsNear', 'TIE_NEAR', 'TIE_PX_M', 'addedDrawCalls'):
            self.assertNotIn(gone, SRC)
        runs = cut('  function tieRuns(', '  // One cached alignment/profile')
        self.assertNotIn('.visible', runs)
        # TIE_RUNS is declared, filled in tieRuns, and read only by __dbg.cull
        dbg = SRC[SRC.index('cull: () => {'):SRC.index('lampGain: (k) =>', SRC.index('cull: () => {'))]
        self.assertNotIn('.visible =', dbg)
        rest = SRC.replace(dbg, '').replace(runs, '')
        self.assertEqual(len(re.findall(r'\bTIE_RUNS\.', rest)), 0)
        self.assertEqual(runs.count('TIE_RUNS.push(run);'), 1)

    def test_culling_never_drops_a_tie_in_view(self):
        if not shutil.which('node'):
            self.skipTest('Node.js unavailable')
        script = r"""
const THREE = require(THREE_PATH);
(() => {
const freeOnUpload = () => {}, dropUploadedArray = function () { this.array = null; }, pendingUpload = [];
__FIT__
__RUNS__
// two tracks 4 km long, 3.7 m apart, ties every 0.72 m, climbing and curving, then a second corridor far away
const ties = [];
for (let s = 0; s < 4000; s += 0.72) for (const o of [-1.85, 1.85]) { const a = s / 3000; ties.push([s + Math.sin(a) * o, 10 + s * 0.004 + Math.sin(s / 300) * 6, o * Math.cos(a) + 400 * Math.sin(a * a), -a, Math.atan(0.004)]); }
for (let s = 0; s < 800; s += 0.72) ties.push([9000 + s, 12, 5000, 0, 0]);
const g = tieRuns(ties, new THREE.BoxGeometry(0.24, 0.14, 2.7), new THREE.MeshBasicMaterial(), 'Test Ties');
const out = { runs: g.children.length, counts: g.children.reduce((a, m) => a + m.count, 0), n: ties.length, pending: pendingUpload.length,
  unculled: g.children.every((m) => m.frustumCulled === false && m.visible), listed: TIE_RUNS.length };
out.firstX = g.children.map((m) => { const e = new THREE.Matrix4(); m.getMatrixAt(0, e); return Math.round(e.elements[12]); });
// the property that makes the culling invisible: from random eyes, every run with any corner of any tie inside the view
// frustum passes three's own test (Frustum.intersectsObject, what the renderer asks of a culled mesh)
let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const cam = new THREE.PerspectiveCamera(58, 740 / 360, 1, 26000), f = new THREE.Frustum(), M = new THREE.Matrix4(), e = new THREE.Matrix4(), v = new THREE.Vector3();
let eyes = 0, missed = 0, culled = 0, seen = 0;
for (let k = 0; k < 400; k++) {
  const near = rnd() < 0.5;
  cam.position.set(near ? -200 + rnd() * 4400 : -3000 + rnd() * 15000, 2 + rnd() * (near ? 60 : 900), near ? -300 + rnd() * 900 : -3000 + rnd() * 11000);
  cam.aspect = 0.5 + rnd() * 2; cam.fov = 30 + rnd() * 50; cam.updateProjectionMatrix();
  const yaw = rnd() * 6.3, p = -1.2 + rnd() * 1.3, cp = Math.cos(p);
  cam.lookAt(cam.position.x + Math.sin(yaw) * cp, cam.position.y + Math.sin(p), cam.position.z - Math.cos(yaw) * cp); cam.updateMatrixWorld();
  f.setFromProjectionMatrix(M.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse));
  eyes++;
  for (const m of g.children) {
    m.frustumCulled = true;
    const passes = f.intersectsObject(m);
    if (!passes) culled++;
    let inView = false;
    for (let i = 0; i < m.count && !inView; i++) {
      m.getMatrixAt(i, e);
      for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) if (!inView && f.containsPoint(v.set(sx * 0.12, sy * 0.07, sz * 1.35).applyMatrix4(e))) inView = true;
    }
    if (inView) seen++;
    if (inView && !passes) missed++;
  }
}
Object.assign(out, { eyes, missed, culled, seen });
console.log(JSON.stringify(out));
})();
""".replace('THREE_PATH', THREE).replace('__FIT__', cut('  function fitInstSphere(', '  // ring meshes upload in batches')).replace('__RUNS__', cut('  const TIE_RUN = 500,', '  // One cached alignment/profile'))
        out = node(script)
        self.assertEqual(out['counts'], out['n'])
        self.assertEqual(out['pending'], out['runs'])
        self.assertEqual(out['listed'], out['runs'])
        self.assertTrue(out['unculled'])                 # every run draws unculled until the first frame releases it
        # runs of about 500 m along the line, and the far corridor on its own (a jump of over 10 m starts a new run)
        starts = out['firstX']
        line = [x for x in starts if x < 5000]
        self.assertEqual(line[0], 0)
        self.assertTrue(7 <= len(line) <= 9, starts)
        self.assertTrue(all(480 <= b - a <= 510 for a, b in zip(line, line[1:])), starts)
        self.assertEqual([x for x in starts if x >= 5000], [9000, 9500])
        # culling did cut (runs out of view), and never a run with a tie in view
        self.assertGreater(out['culled'], out['eyes'])
        self.assertGreater(out['seen'], out['eyes'] // 4)
        self.assertEqual(out['missed'], 0)

    def test_the_first_frame_releases_what_is_pending(self):
        fr = cut('  function frame(now, once) {', '\n  setHint();')
        # the pins' read lands first thing, and the release comes after the render
        self.assertLess(fr.index('pinOccPoll();'), fr.index('applyLighting();'))   # first thing: before the frame queues GL work
        self.assertLess(fr.index('pinOccPoll();'), fr.index('pinOccUpdate(dt);'))
        render = fr.index('if (POST.on) renderPost(scene, camera); else renderer.render(scene, camera);')
        rel = fr.index('for (const m of pendingUpload) m.frustumCulled = true;')
        self.assertGreater(rel, render)
        self.assertIn('pendingUpload.length = 0;', fr[rel:])
        # nothing renders the scene between the build's end and the first frame, so the first frame is the upload frame
        b = cut('  async function build() {', '  btnEnter.addEventListener(')
        self.assertNotIn('renderer.render(', b)


class PinAsync(unittest.TestCase):
    """The async block under Node, with a scripted WebGL 2 context and occRender reduced to its read."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')

    def run_js(self, body, webgl2=True):
        script = r'''
const THREE = require(THREE_PATH);
(async () => {
const window = { innerWidth: 800, innerHeight: 400 };
const PIN_OCC = { w: 240, h: 0, rt: null, buf: null, ok: false, n: 0, view: new THREE.Matrix4(), proj: new THREE.Matrix4(), cam: new THREE.PerspectiveCamera() };
const G = { PIXEL_PACK_BUFFER: 0x88EB, STREAM_READ: 0x88E1, SYNC_GPU_COMMANDS_COMPLETE: 0x9117, SYNC_STATUS: 0x9114, SIGNALED: 0x9119, UNSIGNALED: 0x9118, NO_ERROR: 0,
  bound: null, lost: false, err: 0, signal: false, fences: 0, deleted: 0, log: [], data: null,
  createBuffer() { return { id: 'pbo' }; }, deleteBuffer() {}, bindBuffer(t, b) { this.bound = b; this.log.push(b ? 'bind' : 'unbind'); },
  bufferData(t, n) { this.size = n; }, getError() { const e = this.err; this.err = 0; return e; },
  fenceSync() { if (this.lost) return null; this.fences++; return { f: this.fences }; }, flush() { this.log.push('flush'); },
  getSyncParameter(s) { return this.signal ? this.SIGNALED : this.UNSIGNALED; }, deleteSync() { this.deleted++; }, isContextLost() { return this.lost; },
  getBufferSubData(t, off, dst) { if (!this.bound) throw new Error('nothing bound'); dst.fill(this.data); this.log.push('sub'); } };
const renderer = { capabilities: { isWebGL2: WEBGL2 }, getContext: () => G, reads: [],
  readRenderTargetPixels(rt, x, y, w, h, dst) { this.reads.push({ into: typeof dst === 'number' ? 'pbo' : 'array', packBound: !!G.bound }); if (typeof dst !== 'number') dst.fill(5); } };
THREE.WebGLRenderTarget.prototype.dispose = function () {};
let camera = new THREE.PerspectiveCamera(); camera.position.set(1, 2, 3); camera.updateMatrixWorld();
let camN = 0;
function pinOccMat() {}
function pinOccCam() { camN++; const c = PIN_OCC.cam; c.position.set(camN, 0, 0); c.updateMatrixWorld(); c.matrixWorldInverse.copy(c.matrixWorld).invert(); c.projectionMatrix.makeScale(camN, 1, 1); return c; }
function pinOccCaptureRest() { const c = pinOccCam(); PIN_OCC.buf.fill(9); PIN_OCC.view.copy(c.matrixWorldInverse); PIN_OCC.proj.copy(c.projectionMatrix); PIN_OCC.ok = true; PIN_OCC.n++; }
function occRender(rt, W, H, buf, noInstanced, cam, read) { return read ? read() : false; }
BLOCK
const viewX = () => -PIN_OCC.view.elements[12];   // the capture camera's x, which pinOccCam counts up
BODY
pinOccTick.port1.close();
})().catch((e) => { console.error(e); process.exit(1); });
'''.replace('THREE_PATH', THREE).replace('WEBGL2', 'true' if webgl2 else 'false').replace('BLOCK', cut('  const PIN_JUMP = ', '  function pinOccMat() {')).replace('BODY', body)
        return node(script)

    def test_the_read_lands_with_its_own_matrices(self):
        out = self.run_js('''
const r = {};
r.first = pinOccCapture();                                   // the first image: synchronous, installed now
r.firstView = viewX();
G.data = 42; G.signal = false;
r.second = pinOccCapture();                                  // then a read into the pack buffer
r.read = renderer.reads[renderer.reads.length - 1];
r.unboundAfter = G.bound === null;
r.flushed = G.log.includes('flush');
r.busy = pinOccCapture();                                    // one in flight: nothing drawn
pinOccPoll(); r.beforeFence = { fresh: PIN_OCC.fresh, view: viewX(), buf: PIN_OCC.buf[0] };
G.signal = true; pinOccPoll();
r.landed = { fresh: PIN_OCC.fresh, view: viewX(), buf: PIN_OCC.buf[0], n: PIN_OCC.n, unbound: G.bound === null, deleted: G.deleted };
pinOccPoll(); r.nextFrame = PIN_OCC.fresh;
r.third = pinOccCapture();
console.log(JSON.stringify(r));''')
        self.assertEqual(out['first'], 'now')
        self.assertEqual(out['firstView'], 1)
        self.assertEqual(out['second'], 'later')
        self.assertEqual(out['read'], {'into': 'pbo', 'packBound': True})
        self.assertTrue(out['unboundAfter'])
        self.assertTrue(out['flushed'])
        self.assertEqual(out['busy'], 'busy')
        # before the fence passes nothing changes: the old image with the old matrices
        self.assertEqual(out['beforeFence'], {'fresh': False, 'view': 1, 'buf': 9})
        # once it has: the new pixels and the matrices of the capture that drew them (the second camera), together
        self.assertEqual(out['landed'], {'fresh': True, 'view': 2, 'buf': 42, 'n': 2, 'unbound': True, 'deleted': 1})
        self.assertFalse(out['nextFrame'])
        self.assertEqual(out['third'], 'later')

    def test_a_new_size_reads_synchronously(self):
        out = self.run_js('''
pinOccCapture(); G.signal = false; pinOccCapture();
window.innerHeight = 300;                                    // resized with a read in flight
const got = pinOccCapture();
console.log(JSON.stringify({ got, h: PIN_OCC.h, dropped: PIN_ASYNC.dropped, inFlight: !!PIN_ASYNC.sync, view: viewX() }));''')
        self.assertEqual(out, {'got': 'now', 'h': 90, 'dropped': 1, 'inFlight': False, 'view': 3})

    def test_a_jump_reads_synchronously(self):
        # a shared link or a located fix moves the eye hundreds of metres at once: the read in flight (of the old place)
        # is dropped and the capture at the next turn is read at once, as before Round 167; a flight's steps are not jumps
        out = self.run_js('''
pinOccCapture(); G.signal = false;
camera.position.x += 250; const step = pinOccCapture();       // 250 m since the last capture: still a flight
camera.position.x += 301; const jumped = pinOccCapture();     // a read in flight, and the eye 301 m away
console.log(JSON.stringify({ step, jumped, dropped: PIN_ASYNC.dropped, inFlight: !!PIN_ASYNC.sync, view: viewX() }));''')
        self.assertEqual(out, {'step': 'later', 'jumped': 'now', 'dropped': 1, 'inFlight': False, 'view': 3})

    def test_webgl1_reads_synchronously(self):
        out = self.run_js('''
const a = pinOccCapture(), b = pinOccCapture();
console.log(JSON.stringify({ a, b, pbo: renderer.reads.some((x) => x.into === 'pbo'), fences: G.fences }));''', webgl2=False)
        self.assertEqual(out, {'a': 'now', 'b': 'now', 'pbo': False, 'fences': 0})

    def test_a_refused_read_goes_synchronous_for_good(self):
        out = self.run_js('''
pinOccCapture();
G.err = 0x502;                                               // the driver refuses the pack read (checked once)
const oldGetError = G.getError; let calls = 0; G.getError = function () { calls++; return calls === 2 ? 0x502 : 0; };
const got = pinOccCapture();
const last = renderer.reads[renderer.reads.length - 1];
const later = pinOccCapture();
console.log(JSON.stringify({ got, off: PIN_ASYNC.off, last, later, unbound: G.bound === null, view: viewX() }));''')
        self.assertEqual(out['got'], 'now')                       # read synchronously in its place, matrices installed at once
        self.assertTrue(out['off'])
        self.assertEqual(out['last'], {'into': 'array', 'packBound': False})
        self.assertEqual(out['later'], 'now')
        self.assertTrue(out['unbound'])
        self.assertEqual(out['view'], 3)

    def test_a_fence_that_never_passes_is_given_up_only_across_tasks(self):
        out = self.run_js('''
pinOccCapture(); G.signal = false; pinOccCapture();
for (let i = 0; i < 500; i++) pinOccPoll();                  // one task: the fence cannot pass yet, nothing is given up
const within = { off: PIN_ASYNC.off, inFlight: !!PIN_ASYNC.sync };
await new Promise((r) => setTimeout(r, 30));
for (let i = 0; i < 121; i++) pinOccPoll();                  // frames in later tasks: 120 of them and it goes synchronous
console.log(JSON.stringify({ within, off: PIN_ASYNC.off, inFlight: !!PIN_ASYNC.sync, next: pinOccCapture() }));''')
        self.assertEqual(out, {'within': {'off': False, 'inFlight': True}, 'off': True, 'inFlight': False, 'next': 'now'})

    def test_a_lost_context(self):
        out = self.run_js('''
pinOccCapture(); G.signal = false; pinOccCapture();
G.lost = true; pinOccPoll();
console.log(JSON.stringify({ off: PIN_ASYNC.off, inFlight: !!PIN_ASYNC.sync, fresh: PIN_OCC.fresh, view: viewX() }));''')
        self.assertEqual(out, {'off': True, 'inFlight': False, 'fresh': False, 'view': 1})

    def test_wiring(self):
        # the building tap keeps its synchronous read; only the pins' capture passes a read
        self.assertIn('try { occRender(BPICK.rt, 1, 1, BPICK.buf, true); }', SRC)
        self.assertEqual(SRC.count('pinOccIssue)'), 1)
        occ = cut('  function occRender(', '  const occUnpack =')
        self.assertIn('if (read) out = read(); else r.readRenderTargetPixels(rt, 0, 0, W, H, buf);', occ)
        # the pack buffer is unbound in a finally, straight after the read is issued
        issue = cut('  function pinOccIssue() {', '  const pinOccTick =')
        self.assertIn('finally { gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null); }', issue)
        self.assertIn('gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0)', issue)
        # __dbg can force either path (a probe's loop of frameOnce is one task, where no fence can pass)
        self.assertIn('pinAsync: (on) =>', SRC)
        # the cadence and the fade are Round 138's and 143's
        self.assertIn('every: isTouch ? 10 : 5,', SRC)
        # a jump is past the fastest flight between two captures: 500 m/s boosted 3.2 times over 5 frames at 60 fps (desktop),
        # 500 m/s over 10 frames at 20 fps (a phone); both under PIN_JUMP
        self.assertIn('const PIN_JUMP = 300;', SRC)
        self.assertIn('clamp(fly.speed * Math.exp(-e.deltaY * 0.0012), 10, 500)', SRC)
        self.assertIn("const boost = walk.keys['shift'] ? 3.2 : 1;", SRC)
        self.assertLess(500 * 3.2 * 5 / 60, 300)
        self.assertLess(500 * 10 / 20, 300)
        self.assertIn('const PIN_FADE = 0.2, PIN_HOLD = 0.45, PIN_DWELL = 0.3;', SRC)


class PinAsyncFade(unittest.TestCase):
    """pinOccUpdate with reads that land a frame after their capture: two landed images still decide, a busy turn waits."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')

    def test_landed_images_count_as_captures(self):
        block = cut('  const PIN_FADE = ', '  function frame(now, once) {')
        script = r'''
let frameNo = 0, answer = 1, inFlight = 0, captures = 0, busy = 0;
const PIN_OCC = { ok: false, every: 5, want: -99, hid: 0, lastFrame: -1e9, fresh: false, lastPos: { copy() {} }, lastQuat: { copy() {} } };
const camera = { position: { distanceToSquared: () => 1 }, quaternion: { dot: () => 1 } };
let seen = 1;   // the answer the installed image gives
function pinOccCapture() { if (!PIN_OCC.ok) { PIN_OCC.ok = true; seen = answer; return 'now'; } if (inFlight) { busy++; return 'busy'; } inFlight = { a: answer }; captures++; return 'later'; }
function poll() { PIN_OCC.fresh = false; if (inFlight) { seen = inFlight.a; inFlight = 0; PIN_OCC.fresh = true; } }   // lands the frame after
function pinOccVisible() { return seen === 1; }
const cap = 8, mat = new Float32Array(cap * 16), vis = new Float32Array(cap).fill(1);
const m = { visible: true, count: 1, userData: {}, instanceMatrix: { count: cap, array: mat }, geometry: { attributes: { aPinVis: { array: vis, needsUpdate: false } } } };
const PIN_MESHES = [m];
BLOCK
const run = (n, a) => { const o = []; for (let i = 0; i < n; i++) { answer = a; frameNo++; poll(); pinOccUpdate(1 / 60); o.push(+vis[0].toFixed(3)); } return o; };
run(20, 1);
const s = run(40, 0);
console.log(JSON.stringify({ s, captures, busy }));
'''.replace('BLOCK', block)
        out = node(script)
        s = out['s']
        self.assertEqual(s[0], 1)
        self.assertEqual(s[-1], 0)                                   # two landed images agree: hidden
        first = next(i for i, v in enumerate(s) if v < 1)
        # the capture at frame 25 lands at 26, the one at 30 lands at 31: the ease starts on the second landing
        self.assertEqual(first, 31 - 21)
        self.assertEqual(out['busy'], 0)                             # every read landed before the next turn

    def test_a_busy_turn_tries_again_the_next_frame(self):
        # Round 167 review: a turn that found a read in flight waited a whole cadence, so when fences ran later than the
        # cadence the images came half as often. Now it tries again each frame: an image is issued the frame the last one
        # lands, never two in flight, and a fence faster than the cadence keeps the cadence exactly
        block = cut('  const PIN_FADE = ', '  function frame(now, once) {')
        script = r'''
let frameNo = 0, inFlight = null, issued = [], landed = 0, busy = 0, most = 0;
const PIN_OCC = { ok: true, every: 10, want: -99, hid: 0, lastFrame: -1e9, fresh: false, lastPos: { copy() {} }, lastQuat: { copy() {} } };
const camera = { position: { distanceToSquared: () => 1 }, quaternion: { dot: () => 1 } };   // a flight: moved at every turn
let LAT = 1;
function pinOccCapture() { if (inFlight) { busy++; return 'busy'; } inFlight = { at: frameNo }; issued.push(frameNo); return 'later'; }
function poll() { PIN_OCC.fresh = false; if (inFlight && frameNo - inFlight.at >= LAT) { inFlight = null; landed++; PIN_OCC.fresh = true; } }
function pinOccVisible() { return true; }
const cap = 8, mat = new Float32Array(cap * 16), vis = new Float32Array(cap).fill(1);
const m = { visible: true, count: 1, userData: {}, instanceMatrix: { count: cap, array: mat }, geometry: { attributes: { aPinVis: { array: vis, needsUpdate: false } } } };
const PIN_MESHES = [m];
BLOCK
const run = (lat, n) => { LAT = lat; issued = []; landed = 0; busy = 0; inFlight = null; PIN_OCC.retry = false; for (let i = 0; i < n; i++) { frameNo++; poll(); pinOccUpdate(1 / 60); } return { issued: issued.slice(), landed, busy }; };
frameNo = 0;
const fast = run(2, 100);      // lands two frames after it went: the cadence of ten holds
const slow = run(14, 140);     // later than the cadence: issued as each one lands
console.log(JSON.stringify({ fast, slow }));
'''.replace('BLOCK', block)
        out = node(script)
        fast, slow = out['fast'], out['slow']
        self.assertEqual(fast['busy'], 0)
        self.assertTrue(all(b - a == 10 for a, b in zip(fast['issued'], fast['issued'][1:])), fast['issued'])
        gaps = [b - a for a, b in zip(slow['issued'], slow['issued'][1:])]
        self.assertTrue(gaps and all(g == 14 for g in gaps), slow['issued'])   # the frame each one lands, not the next multiple of ten (20)
        self.assertGreaterEqual(len(slow['issued']), 9)
        self.assertGreater(slow['busy'], 0)


if __name__ == '__main__':
    unittest.main()
