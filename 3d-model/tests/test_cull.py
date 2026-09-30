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
  its own matrices only once the fence has passed; run here under Node against a scripted WebGL 2 context. Since Round 169
  drawing an image (the gate reads it at once) is apart from reading it back: an image is drawn whatever is in flight,
  never into the target a read is in flight from, and the newest unread one is read as soon as the last read lands.
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
    """The pins' images under Node (Round 167's read into a pack buffer behind a fence, Round 169's drawing apart from reading):
    a scripted WebGL 2 context, occRender reduced to its read."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')

    def run_js(self, body, webgl2=True, touch=True):
        script = r'''
const THREE = require(THREE_PATH);
(async () => {
const window = { innerWidth: 800, innerHeight: 400 }, isTouch = TOUCH, scene = { add() {} };
let frameNo = 1;
const G = { PIXEL_PACK_BUFFER: 0x88EB, STREAM_READ: 0x88E1, SYNC_GPU_COMMANDS_COMPLETE: 0x9117, SYNC_STATUS: 0x9114, SIGNALED: 0x9119, UNSIGNALED: 0x9118, NO_ERROR: 0,
  bound: null, lost: false, err: 0, signal: false, fences: 0, deleted: 0, log: [], data: null,
  createBuffer() { return { id: 'pbo' }; }, deleteBuffer() {}, bindBuffer(t, b) { this.bound = b; this.log.push(b ? 'bind' : 'unbind'); },
  bufferData(t, n) { this.size = n; }, getError() { const e = this.err; this.err = 0; return e; },
  fenceSync() { if (this.lost) return null; this.fences++; return { f: this.fences }; }, flush() { this.log.push('flush'); },
  getSyncParameter(s) { return this.signal ? this.SIGNALED : this.UNSIGNALED; }, deleteSync() { this.deleted++; }, isContextLost() { return this.lost; },
  getBufferSubData(t, off, dst) { if (!this.bound) throw new Error('nothing bound'); dst.fill(this.data); this.log.push('sub'); } };
const renderer = { capabilities: { isWebGL2: WEBGL2 }, getContext: () => G, reads: [],
  readRenderTargetPixels(rt, x, y, w, h, dst) { this.reads.push({ into: typeof dst === 'number' ? 'pbo' : 'array', packBound: !!G.bound, rt: rt.id }); if (typeof dst !== 'number') dst.fill(rt.id); } };
let rtN = 0;
THREE.WebGLRenderTarget = function (w, h, o) { this.id = ++rtN; this.w = w; this.h = h; this.o = o; this.texture = { rt: this.id }; this.dispose = () => {}; };
const camera = new THREE.PerspectiveCamera(); camera.position.set(1, 2, 3); camera.updateMatrixWorld();
const PIN_GATE = { texA: { value: null }, texB: { value: null }, viewA: { value: new THREE.Matrix4() }, viewAInv: { value: new THREE.Matrix4() }, projA: { value: new THREE.Matrix4() },
  viewB: { value: new THREE.Matrix4() }, projB: { value: new THREE.Matrix4() }, info: { value: new THREE.Vector4() }, reach: { value: new THREE.Vector4() }, frame: -1e9 };
let camN = 0, reachAsked = [];
function pinOccMat() {}
function pinOccCam(reach) { camN++; reachAsked.push(reach); const c = new THREE.PerspectiveCamera(); c.position.set(camN, 0, 0); c.updateMatrixWorld(); c.far = Math.min(reach, 26000); c.projectionMatrix.makeScale(camN, 1, 1); return c; }
function occFlatsOff() { return true; }   // Round 168: the capture's flats gate (test_occ_flats.py)
const drawn = [];
function occRender(rt, W, H, buf, noInstanced, cam, read) { drawn.push(rt.id); if (read) return read(); renderer.readRenderTargetPixels(rt, 0, 0, W, H, buf); return false; }
BLOCK
const viewX = (I) => -I.view.elements[12];   // the capture camera's x, which pinOccCam counts up
const F = PIN_OCC.full.cpu, N = PIN_OCC.near.cpu;
BODY
pinOccTick.port1.close();
})().catch((e) => { console.error(e); process.exit(1); });
'''.replace('THREE_PATH', THREE).replace('WEBGL2', 'true' if webgl2 else 'false').replace('TOUCH', 'true' if touch else 'false').replace('BLOCK', cut('  const PIN_OCC_MOVE_EVERY = ', '  function pinOccMat() {')).replace('BODY', body)
        return node(script)

    def test_the_read_lands_with_its_own_matrices(self):
        out = self.run_js('''
const r = {};
r.first = pinOccCapture();                                   // the first image: synchronous, installed now
r.firstView = viewX(F);
frameNo++; G.data = 42; G.signal = false;
r.second = pinOccCapture();                                  // drawn for the gate at once; read later
r.gateB = PIN_GATE.texB.value.rt; r.secondRt = drawn[drawn.length - 1];
pinOccRead();                                                // the newest image into the pack buffer
r.read = renderer.reads[renderer.reads.length - 1];
r.unboundAfter = G.bound === null;
r.flushed = G.log.includes('flush');
frameNo++; r.third = pinOccCapture();                        // a read in flight: the image is still drawn, never into its target
r.thirdRt = drawn[drawn.length - 1]; r.gateB3 = PIN_GATE.texB.value.rt;
pinOccRead(); r.issued = PIN_ASYNC.issued;                   // one read in flight at a time
pinOccPoll(); r.beforeFence = { fresh: PIN_OCC.fresh, view: viewX(F), buf: F.buf[0] };
G.signal = true; pinOccPoll();
r.landed = { fresh: PIN_OCC.fresh, view: viewX(F), buf: F.buf[0], n: PIN_OCC.n, unbound: G.bound === null, deleted: G.deleted, frame: F.frame };
pinOccPoll(); r.nextFrame = PIN_OCC.fresh;
pinOccRead(); r.tooSoon = PIN_ASYNC.issued;                           // a frame after the last read went: not yet (PIN_OCC_READ_EVERY)
frameNo += 3; pinOccRead(); r.next = renderer.reads[renderer.reads.length - 1].rt; r.issued2 = PIN_ASYNC.issued;   // four frames on: the newest image goes next
console.log(JSON.stringify(r));''')
        self.assertEqual(out['first'], 'now')
        self.assertEqual(out['firstView'], 1)
        self.assertEqual(out['second'], 'later')
        self.assertEqual(out['gateB'], out['secondRt'])               # the gate reads the new image the frame it is drawn
        self.assertEqual(out['read'], {'into': 'pbo', 'packBound': True, 'rt': out['secondRt']})
        self.assertTrue(out['unboundAfter'])
        self.assertTrue(out['flushed'])
        self.assertEqual(out['third'], 'later')
        self.assertNotEqual(out['thirdRt'], out['secondRt'])          # a render never disturbs the read in flight
        self.assertEqual(out['gateB3'], out['thirdRt'])
        self.assertEqual(out['issued'], 1)
        # before the fence passes nothing changes: the old image with the old matrices
        self.assertEqual(out['beforeFence'], {'fresh': False, 'view': 1, 'buf': 1})   # the first image's pixels (its target's id, as the stub reads)
        # once it has: the new pixels and the matrices of the capture that drew them (the second camera), together
        self.assertEqual(out['landed'], {'fresh': True, 'view': 2, 'buf': 42, 'n': 2, 'unbound': True, 'deleted': 1, 'frame': 2})
        self.assertFalse(out['nextFrame'])
        self.assertEqual(out['tooSoon'], 1)
        self.assertEqual(out['next'], out['thirdRt'])
        self.assertEqual(out['issued2'], 2)

    def test_a_new_size_reads_synchronously(self):
        out = self.run_js('''
pinOccCapture(); frameNo++; G.signal = false; pinOccCapture(); pinOccRead();
window.innerHeight = 300;                                    // resized with a read in flight
const got = pinOccCapture('near');                           // a new size draws the complete kind, read at once
console.log(JSON.stringify({ got, h: PIN_OCC.h, dropped: PIN_ASYNC.dropped, inFlight: !!PIN_ASYNC.sync, view: viewX(F), nearOk: N.ok, near: PIN_OCC.rendersNear }));''')
        self.assertEqual(out, {'got': 'now', 'h': 90, 'dropped': 1, 'inFlight': False, 'view': 3, 'nearOk': False, 'near': 0})

    def test_a_jump_reads_synchronously(self):
        # a shared link or a located fix moves the eye hundreds of metres at once: the read in flight (of the old place)
        # is dropped and the next image is read at once, as before Round 167; a flight's steps are not jumps
        out = self.run_js('''
pinOccCapture(); G.signal = false;
camera.position.x += 250; frameNo++; const step = pinOccCapture(); pinOccRead();   // 250 m since the last image: still a flight
camera.position.x += 301; frameNo++; const jumped = pinOccCapture();              // a read in flight, and the eye 301 m away
console.log(JSON.stringify({ step, jumped, dropped: PIN_ASYNC.dropped, inFlight: !!PIN_ASYNC.sync, view: viewX(F) }));''')
        self.assertEqual(out, {'step': 'later', 'jumped': 'now', 'dropped': 1, 'inFlight': False, 'view': 3})

    def test_webgl1_reads_synchronously_at_the_old_cadence(self):
        # without a pack buffer every image still reaches the gate, but the stalling read comes only at the old cadence (or for a
        # pin that waits), as before Round 169
        out = self.run_js('''
const got = [];
for (let i = 0; i < 12; i++) { frameNo++; got.push(pinOccCapture()); pinOccRead(); }
PIN_OCC.wait = frameNo + 1; frameNo++; got.push(pinOccCapture());   // a pin waiting, a frame after the last read: not yet
frameNo += 3; got.push(pinOccCapture());                              // four frames on: read at once
console.log(JSON.stringify({ got, pbo: renderer.reads.some((x) => x.into === 'pbo'), fences: G.fences, drawn: drawn.length }));''', webgl2=False)
        self.assertEqual(out['got'][0], 'now')
        self.assertEqual(out['got'][1:10], ['later'] * 9)
        self.assertEqual(out['got'][10], 'now')                   # ten frames on: the old cadence
        self.assertEqual(out['got'][-2:], ['later', 'now'])       # a pin waiting: read at once, but never more than every 4th frame
        self.assertFalse(out['pbo'])
        self.assertEqual(out['fences'], 0)
        self.assertEqual(out['drawn'], 14)

    def test_a_refused_read_goes_synchronous_for_good(self):
        out = self.run_js('''
pinOccCapture();
let calls = 0; G.getError = function () { calls++; return calls === 2 ? 0x502 : 0; };   // the driver refuses the pack read (checked once)
frameNo++; const got = pinOccCapture(); pinOccRead();
const last = renderer.reads[renderer.reads.length - 1];
const fresh = PIN_OCC.fresh, view = viewX(F);
frameNo++; const later = pinOccCapture();
console.log(JSON.stringify({ got, off: PIN_ASYNC.off, last: { into: last.into, packBound: last.packBound }, fresh, view, unbound: G.bound === null, later }));''')
        self.assertEqual(out['got'], 'later')
        self.assertTrue(out['off'])
        self.assertEqual(out['last'], {'into': 'array', 'packBound': False})   # read synchronously in its place, installed at once
        self.assertTrue(out['fresh'])
        self.assertEqual(out['view'], 2)
        self.assertTrue(out['unbound'])
        self.assertEqual(out['later'], 'later')                    # from now on the old cadence's synchronous read

    def test_a_fence_that_never_passes_is_given_up_only_across_tasks(self):
        out = self.run_js('''
pinOccCapture(); frameNo++; G.signal = false; pinOccCapture(); pinOccRead();
for (let i = 0; i < 500; i++) pinOccPoll();                  // one task: the fence cannot pass yet, nothing is given up
const within = { off: PIN_ASYNC.off, inFlight: !!PIN_ASYNC.sync };
await new Promise((r) => setTimeout(r, 30));
for (let i = 0; i < 121; i++) pinOccPoll();                  // frames in later tasks: 120 of them and it goes synchronous
frameNo += 20;
console.log(JSON.stringify({ within, off: PIN_ASYNC.off, inFlight: !!PIN_ASYNC.sync, next: pinOccCapture() }));''')
        self.assertEqual(out, {'within': {'off': False, 'inFlight': True}, 'off': True, 'inFlight': False, 'next': 'now'})

    def test_a_lost_context(self):
        out = self.run_js('''
pinOccCapture(); frameNo++; G.signal = false; pinOccCapture(); pinOccRead();
G.lost = true; pinOccPoll();
console.log(JSON.stringify({ off: PIN_ASYNC.off, inFlight: !!PIN_ASYNC.sync, fresh: PIN_OCC.fresh, view: viewX(F) }));''')
        self.assertEqual(out, {'off': True, 'inFlight': False, 'fresh': False, 'view': 1})

    def test_two_kinds(self):
        # a phone's near image: its own targets, its own reach (5% past PIN_NEAR), read after the complete one; the gate reads it
        # with the complete one while it is the newer, and the complete one alone once that is
        out = self.run_js('''
PIN_OCC.reach = 4000;
pinOccCapture(); frameNo++;
const first = pinOccCapture('near');                          // the first near image is read at once
const g1 = { a: PIN_GATE.reach.value.x, b: PIN_GATE.reach.value.y, aNewer: PIN_GATE.reach.value.z, texA: PIN_GATE.texA.value.rt };
frameNo++; pinOccCapture('near'); frameNo++; pinOccCapture('full');
const g2 = { aNewer: PIN_GATE.reach.value.z };
G.signal = false; pinOccRead(); const readFull = renderer.reads[renderer.reads.length - 1].rt, fullRts = PIN_OCC.full.slots.map((s) => s.rt.id);
console.log(JSON.stringify({ first, reaches: reachAsked, g1, g2, readFull: fullRts.includes(readFull), nearOk: N.ok, rendersNear: PIN_OCC.rendersNear, nearRts: PIN_OCC.near.slots.map((s) => s.rt.id), fullRts }));''')
        self.assertEqual(out['first'], 'now')
        self.assertEqual(out['reaches'][0], 30000)                # the first image reaches the packing range
        self.assertAlmostEqual(out['reaches'][1], 900 * 1.05)     # a near image: 5% past PIN_NEAR
        self.assertAlmostEqual(out['reaches'][3], 4000 * 1.1 + 50)   # a complete one: the farthest tip, 10% and 50 m on
        self.assertEqual(out['g1'], {'a': 945, 'b': 26000, 'aNewer': 1, 'texA': out['nearRts'][0]})
        self.assertEqual(out['g2'], {'aNewer': 0})
        self.assertTrue(out['readFull'])
        self.assertEqual(out['rendersNear'], 2)
        self.assertTrue(set(out['nearRts']).isdisjoint(out['fullRts']))

    def test_nearest_filtering_and_the_wiring(self):
        slot = cut('  function pinOccSlot(W, H) {', '  const pinOccNoRead')
        self.assertIn('minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false', slot)
        # the building tap keeps its synchronous read; the pins' one capture call reads at once or leaves it to pinOccRead
        self.assertIn('try { occRender(BPICK.rt, 1, 1, BPICK.buf, true); }', SRC)
        self.assertIn('occRender(s.rt, W, H, ch.cpu.buf, true, c, now ? null : pinOccNoRead, nf);', SRC)
        occ = cut('  function occRender(', '  const occUnpack =')
        self.assertIn('if (read) out = read(); else r.readRenderTargetPixels(rt, 0, 0, W, H, buf);', occ)
        # the pack buffer is unbound in a finally, straight after the read is issued
        issue = cut('  function pinOccIssue(s, dst) {', '  const pinOccTick =')
        self.assertIn('finally { gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null); }', issue)
        self.assertIn('gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0)', issue)
        # never into the target a read is in flight from
        self.assertIn('const k = A.sync && A.chan === ch ? 1 - A.slot : ch.gate === 0 ? 1 : 0;', SRC)
        # __dbg can force either path (a probe's loop of frameOnce is one task, where no fence can pass)
        self.assertIn('pinAsync: (on) =>', SRC)
        self.assertIn('every: isTouch ? 10 : 5, moveEvery: PIN_OCC_MOVE_EVERY, fullEvery: PIN_OCC_FULL_EVERY,', SRC)
        # a jump is past the fastest flight between two images: 500 m/s boosted 3.2 times over a frame at 60 fps (a computer draws an
        # image every frame while moving), 500 m/s over 10 frames at 20 fps (a phone's complete image); both under PIN_JUMP
        self.assertIn('const PIN_JUMP = 300;', SRC)
        self.assertIn('clamp(fly.speed * Math.exp(-e.deltaY * 0.0012), 10, 500)', SRC)
        self.assertIn("const boost = walk.keys['shift'] ? 3.2 : 1;", SRC)
        self.assertLess(500 * 3.2 * 5 / 60, 300)
        self.assertLess(500 * 10 / 20, 300)
        # the frame: the read lands first thing, the images are drawn in pinOccUpdate before the render
        fr = cut('  function frame(now, once) {', '\n  setHint();')
        self.assertLess(fr.index('pinOccPoll();'), fr.index('pinOccUpdate(dt);'))
        self.assertLess(fr.index('pinOccUpdate(dt);'), fr.index('if (POST.on) renderPost(scene, camera); else renderer.render(scene, camera);'))


if __name__ == '__main__':
    unittest.main()
