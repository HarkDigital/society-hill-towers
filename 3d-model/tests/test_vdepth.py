"""Round 168 (plan item 1a): vertex-only log depth for the far facades, on a phone only.

The log depth buffer writes gl_FragDepth from every fragment, which costs the early depth test (and, on Apple's tile
GPUs, hidden-surface removal). A facade mesh far enough from the eye draws with a twin of its material compiled with
USE_LOGDEPTHBUF_EXT undefined, so three writes the same log depth from the vertex stage. Checked here:

- only the facade materials (cityMat and its clones, the curtain wall) are flagged; the flats and everything else never are
- the twin: made at once after its original (three sorts opaque draws by material id), both shaders open with the
  #undef, the original's hook runs at compile time (the weather chained on after the build included), every uniform
  object is the original's own, the program key is the original's plus '|vdepth', no depth offset, userData is not
  deep-copied, a dispose of the original disposes the twin, and the properties the frames write are copied across
- the line: a mesh goes far only past max(near, k x its longest triangle edge) + band and comes back inside that line
  (the vertex path's interpolation error grows with a triangle's depth span: the pier warehouses showed the ground
  through their walls at the 300 m floor alone), never holds the twin inside it at a decision, and a jump is decided at once
- the overlays: a facade mesh with a skyline light, a landmark trim or accent on or beside one of its 100 m cells keeps
  fragment depth (a coplanar overlay lost the samples where the wall leans toward the eye: a lit crown went muddy)
- the first frame after the build draws every other facade mesh with its twin, unculled (behind the veil, so the programs
  compile there), and the culling comes back in the second
- touch only by default, ?vdepth=0 off, ?vdepth=<m> on any device, off without log depth or fragment depth
- the call sits in frame() after the camera moves and before the main render, and vdepthInit after the weather re-hook
- three r149 still guards the fragment write on USE_LOGDEPTHBUF_EXT and has the vertex path this relies on
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
THREE_JS = (ROOT / 'three.min.js').read_text()
THREE = json.dumps(str(ROOT / 'three.min.js'))


def cut(start, end):
    a = SRC.index(start)
    return SRC[a:SRC.index(end, a)]


BLOCK = cut('  const VDEPTH_Q = ', '  const cityMat = new THREE') + cut('  function vdepthSync() {', '  let last = performance.now();')


def node(script):
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


def harness(search='', touch=True, logdepth=True, gl2=True, body=''):
    """The VDEPTH block under Node with three, a scene of facade and flat meshes, and `body` run against it."""
    return r'''
const THREE = require(THREE_PATH);
(() => {   // a function scope: under node -e a top-level const window would shadow three's own lookups
const V3 = THREE.Vector3;
const location = { search: __SEARCH__ };
const window = { __useLogDepth: __LOGDEPTH__ };
const isTouch = __TOUCH__;
const renderer = { capabilities: { isWebGL2: __GL2__ }, extensions: { has: () => false } };
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(58, 2, 1, 26000);
let frameNo = 0;
// the shared uniforms a facade hook hands its shader, and a hook that sets them (as facadeHook does)
const sunW = { value: new V3(0, 1, 0) }, night = { value: 0 };
const facadeMat = new THREE.MeshStandardMaterial({ vertexColors: true });
facadeMat.userData.vdepth = true;
facadeMat.onBeforeCompile = (sh) => { sh.uniforms.uSunW = sunW; sh.uniforms.uNight = night; sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\n// facade'); facadeMat.userData.shader = sh; };
facadeMat.customProgramCacheKey = () => 'fabric';
const glassMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.38 });
glassMat.userData.vdepth = true;
glassMat.onBeforeCompile = (sh) => { sh.uniforms.uNight = night; };
const flatMat = new THREE.MeshStandardMaterial({ polygonOffset: true });
const box = (w, h, d, x, y, z, mat) => { const g = new THREE.BoxGeometry(w, h, d); g.translate(x, y, z); g.computeBoundingSphere(); const m = new THREE.Mesh(g, mat); scene.add(m); return m; };
// a chunk of 100 m blocks every 1 km along x, the glass tower among them, the flats under them
const chunks = [];
for (let i = 0; i < 8; i++) chunks.push(box(100, 40, 100, i * 1000, 20, 0, facadeMat));
const tower = box(40, 200, 40, 3000, 100, 400, glassMat);
const flat = box(9000, 1, 9000, 3500, -0.5, 0, flatMat);
const inst = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), facadeMat, 4); scene.add(inst);
chunks[3].frustumCulled = false;   // one staged mesh, drawn unculled for its upload
BLOCK
const out = {};
BODY
console.log(JSON.stringify(out));
})();
'''.replace('THREE_PATH', THREE).replace('__SEARCH__', json.dumps(search)).replace('__LOGDEPTH__', json.dumps(logdepth)) \
        .replace('__TOUCH__', json.dumps(touch)).replace('__GL2__', json.dumps(gl2)).replace('BLOCK', BLOCK).replace('BODY', body)


class Wiring(unittest.TestCase):
    def test_only_the_facades_are_flagged(self):
        self.assertEqual(len(re.findall(r'userData\.vdepth = true', SRC)), 2)
        self.assertIn('  cityMat.userData.vdepth = true;', SRC)
        self.assertIn('        outerGlassMat.userData.vdepth = true;', SRC)
        # coreMat and City Hall's material are clones of cityMat taken after the flag, so they carry it
        self.assertLess(SRC.index('  cityMat.userData.vdepth = true;'), SRC.index('    coreMat = cityMat.clone();'))
        self.assertLess(SRC.index('  cityMat.userData.vdepth = true;'), SRC.index('const hallMat=cityMat.clone()'))
        self.assertEqual(len(re.findall(r'cityMat\.clone\(\)', SRC)), 2)

    def test_the_frame_decides_after_the_camera_and_before_the_render(self):
        fr = cut('  function frame(now, once) {', '\n  setHint();')
        self.assertEqual(fr.count('vdepthUpdate();'), 1)
        at = fr.index('vdepthUpdate();')
        self.assertGreater(at, fr.index('else applyFly(dt);'))
        self.assertLess(at, fr.index('if (POST.on) renderPost(scene, camera); else renderer.render(scene, camera);'))
        self.assertLess(at, fr.index('pinOccUpdate(dt);'))

    def test_each_twin_is_made_beside_its_original(self):
        # three sorts opaque draws by material id: a twin made at once after its original sorts beside it
        for made, twin in (("  cityMat.userData.vdepth = true;", "  if (VDEPTH_WANT) vdepthTwin(cityMat);"),
                           ("    coreMat = cityMat.clone();", "    if (VDEPTH_WANT) vdepthTwin(coreMat);"),
                           ("        const hallMat=cityMat.clone(),hallFacade=cityMat.onBeforeCompile;", "        if (VDEPTH_WANT) vdepthTwin(hallMat);"),
                           ("        outerGlassMat.userData.vdepth = true;", "        if (VDEPTH_WANT) vdepthTwin(outerGlassMat);")):
            at = SRC.index(made)
            nxt = SRC.index('\n', SRC.index('\n', at) + 1)
            self.assertEqual(SRC[SRC.index('\n', at) + 1:nxt].split('   //')[0], twin, made)
        # nothing between cityMat's construction and its twin makes a material
        self.assertLess(SRC.index('  const cityMat = new THREE.MeshStandardMaterial('), SRC.index('  if (VDEPTH_WANT) vdepthTwin(cityMat);'))
        self.assertLess(SRC.index('  const VDEPTH = {'), SRC.index('  const cityMat = new THREE.MeshStandardMaterial('))

    def test_init_after_the_weather_rehook_and_before_the_first_frame(self):
        tail = SRC[SRC.index('  build().then(() => {'):]
        self.assertEqual(tail.count('    vdepthInit();'), 1)
        self.assertGreater(tail.index('    vdepthInit();'), tail.index("coreMat.customProgramCacheKey = () => 'fabric-core|wx';"))
        self.assertLess(tail.index('    vdepthInit();'), tail.index('requestAnimationFrame(frame);'))
        self.assertIn('if (window.__dbg) window.__dbg.vdepth = vdepthDbg;', tail)

    def test_three_r149_log_depth_paths(self):
        # the fragment write is guarded on USE_LOGDEPTHBUF_EXT, and without it the vertex stage writes the log depth
        self.assertIn('logdepthbuf_fragment:"#if defined( USE_LOGDEPTHBUF ) && defined( USE_LOGDEPTHBUF_EXT )\\n\\tgl_FragDepthEXT', THREE_JS)
        self.assertIn('\\t#else\\n\\t\\tif ( isPerspectiveMatrix( projectionMatrix ) ) {\\n\\t\\t\\tgl_Position.z = log2( max( EPSILON, gl_Position.w + 1.0 ) ) * logDepthBufFC - 1.0;', THREE_JS)
        # the prefix defines it ahead of the body the hook edits, so the body's #undef wins
        self.assertIn('i.logarithmicDepthBuffer&&i.rendererExtensionFragDepth?"#define USE_LOGDEPTHBUF_EXT":""', THREE_JS)
        self.assertIn("const VDEPTH_UNDEF = '#undef USE_LOGDEPTHBUF_EXT\\n';", SRC)


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Twin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = node(harness(body=r'''
vdepthInit();
const rec = VDEPTH.recs.find((q) => q.mesh === chunks[0]), t = rec.twin;
out.on = VDEPTH.on; out.meshes = VDEPTH.recs.length; out.twins = VDEPTH.twins.size;
out.flatIn = VDEPTH.recs.some((q) => q.mesh === flat); out.instIn = VDEPTH.recs.some((q) => q.mesh === inst);
out.sameTwin = VDEPTH.recs.filter((q) => q.mat === facadeMat).every((q) => q.twin === t && q.twin === VDEPTH.twins.get(facadeMat));
// a compiled facade keeps its shader in userData (a circular object here): the twin is still made, userData untouched
const sh0 = { uniforms: {}, vertexShader: '#include <common>\nvoid main(){}', fragmentShader: 'void main(){}' };
facadeMat.onBeforeCompile(sh0); sh0.self = sh0;
VDEPTH.twins.clear(); VDEPTH.recs.length = 0;
let threw = null; try { vdepthCollect(); } catch (e) { threw = String(e); }
out.threw = threw; out.udKept = facadeMat.userData.shader === sh0 && facadeMat.userData.vdepth === true;
const tw = VDEPTH.twins.get(facadeMat);
out.twinUd = Object.keys(tw.userData);
// the compile: the original's hook, then the #undef at the head of both shaders; the uniforms are the same objects
const sh = { uniforms: {}, vertexShader: '#include <common>\nvoid main(){}', fragmentShader: 'void main(){}' };
tw.onBeforeCompile(sh, null);
out.vHead = sh.vertexShader.split('\n')[0]; out.fHead = sh.fragmentShader.split('\n')[0];
out.hooked = sh.vertexShader.includes('// facade');
out.sharedU = sh.uniforms.uSunW === sunW && sh.uniforms.uNight === night;
out.key = tw.customProgramCacheKey(); out.origKey = facadeMat.customProgramCacheKey();
out.offset = [tw.polygonOffset, tw.polygonOffsetFactor, tw.polygonOffsetUnits];
out.copied = [tw.vertexColors, tw.roughness === facadeMat.roughness, tw.side === facadeMat.side, tw.depthWrite, tw.transparent];
// the weather's chain, assigned after the build: the twin follows the hook and the key
const prev = facadeMat.onBeforeCompile;
facadeMat.onBeforeCompile = (s2, r2) => { prev(s2, r2); s2.fragmentShader = s2.fragmentShader + '\n// wx'; };
facadeMat.customProgramCacheKey = () => 'fabric|wx';
const sh2 = { uniforms: {}, vertexShader: '#include <common>', fragmentShader: 'void main(){}' };
tw.onBeforeCompile(sh2, null);
out.wx = sh2.fragmentShader.endsWith('// wx') && sh2.fragmentShader.startsWith('#undef USE_LOGDEPTHBUF_EXT\n');
out.wxKey = tw.customProgramCacheKey();
// a glass twin keyed on its hook's own source (no hand key), like the curtain wall
const gt = VDEPTH.twins.get(glassMat);
out.glassKey = gt.customProgramCacheKey() === glassMat.onBeforeCompile.toString() + '|vdepth';
// the frames' writes reach the twin; a needsUpdate on the original rebuilds the twin too; a dispose disposes it
glassMat.emissiveIntensity = 0.55; glassMat.color.setRGB(0.2, 0.3, 0.4);
const v0 = gt.version; glassMat.needsUpdate = true;
VDEPTH.on = true; vdepthUpdate(); vdepthUpdate();
out.synced = [gt.emissiveIntensity, gt.color.equals(glassMat.color), gt.version > v0];
const fresh = new THREE.MeshStandardMaterial(); const ft = vdepthTwin(fresh); out.nextId = ft.id === fresh.id + 1 && vdepthTwin(fresh) === ft;
let disposed = 0; tw.addEventListener('dispose', () => disposed++);
facadeMat.dispose(); out.disposed = disposed;
'''))

    def test_collects_only_facade_meshes(self):
        r = self.r
        self.assertTrue(r['on'])
        self.assertEqual(r['meshes'], 9)       # eight chunks and the tower
        self.assertEqual(r['twins'], 2)        # one twin a material
        self.assertFalse(r['flatIn'])
        self.assertFalse(r['instIn'])
        self.assertTrue(r['sameTwin'])

    def test_userdata_is_not_copied(self):
        self.assertIsNone(self.r['threw'])
        self.assertTrue(self.r['udKept'])
        self.assertEqual(self.r['twinUd'], ['ver'])

    def test_the_twin_compiles_the_original_with_vertex_depth(self):
        r = self.r
        self.assertEqual(r['vHead'], '#undef USE_LOGDEPTHBUF_EXT')
        self.assertEqual(r['fHead'], '#undef USE_LOGDEPTHBUF_EXT')
        self.assertTrue(r['hooked'])
        self.assertTrue(r['sharedU'])
        self.assertEqual(r['key'], r['origKey'] + '|vdepth')
        self.assertTrue(r['wx'])
        self.assertEqual(r['wxKey'], 'fabric|wx|vdepth')
        self.assertTrue(r['glassKey'])
        self.assertEqual(r['copied'], [True, True, True, True, False])

    def test_no_offset(self):
        # a slope offset on the far walls brought a coplanar overlay back but widened the lit streets at night: none now
        self.assertEqual(self.r['offset'], [False, 0, 0])
        self.assertNotIn('polygonOffset', BLOCK)

    def test_sync_and_dispose(self):
        self.assertEqual(self.r['synced'], [0.55, True, True])
        self.assertTrue(self.r['nextId'])    # made at once, the twin takes the next id (and is made once)
        self.assertEqual(self.r['disposed'], 1)


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Swap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = node(harness(body=r'''
vdepthInit();
const R = VDEPTH.recs, twinOf = (m) => R.find((q) => q.mesh === m);
out.spans = R.map((q) => Math.round(q.span * 10) / 10);
VDEPTH.k = 1;   // the floor's own tests first: k times a block's 141 m span stays under near
// the first frame after the build: every facade on its twin, unculled
camera.position.set(0, 50, 0);
frameNo = 1; vdepthUpdate();
out.warm1 = { allTwin: R.every((q) => q.mesh.material === q.twin), allUnculled: R.every((q) => q.mesh.frustumCulled === false), warm: VDEPTH.warm };
// the second: the culling back as it was, the near ones back on their originals
frameNo = 2; vdepthUpdate();
out.warm2 = { culled: R.filter((q) => q.mesh !== chunks[3]).every((q) => q.mesh.frustumCulled === true), staged: chunks[3].frustumCulled,
  nearOrig: chunks[0].material === facadeMat, farTwin: chunks[5].material === twinOf(chunks[5]).twin, warm: VDEPTH.warm };
// the hysteresis on chunk 1 (a 100 m box at x 1000, its sphere 73.5 m round the centre): the eye walks along x at the
// box's middle height, so the distance to the sphere is 1000 - x - r
const seq = [], r1 = chunks[1].geometry.boundingSphere.radius;
for (const x of [560, 600, 630, 610, 590, 580, 620, 635, 500]) {
  camera.position.set(x, 20, 0);
  frameNo = 5;   // a decision frame
  vdepthUpdate();
  seq.push([x, 1000 - x - r1, chunks[1].material === twinOf(chunks[1]).twin ? 1 : 0]);
}
out.seq = seq;
// a jump: off the decision cadence, a move over 20 m is decided at once; under it waits for the cadence
camera.position.set(950, 20, 0); frameNo = 6; vdepthUpdate();
out.jump = chunks[1].material === facadeMat;
camera.position.set(600, 20, 0); frameNo = 7; vdepthUpdate(); const d1 = VDEPTH.decided;
camera.position.set(610, 20, 0); frameNo = 8; vdepthUpdate();
out.small = [VDEPTH.decided === d1, chunks[1].material === facadeMat];
// the span's line: at k 8 a block (its longest edge 141.4 m) stays on fragment depth to 8 x 141.4 = 1131 m, whatever near
VDEPTH.k = 8;
const seqK = [];
for (const x of [-200, -260, -230, -210, -200, -240, -300]) {
  camera.position.set(x, 20, 0);
  frameNo = 9;
  vdepthUpdate();
  seqK.push([x, 1000 - x - r1, chunks[1].material === twinOf(chunks[1]).twin ? 1 : 0]);
}
out.seqK = seqK;
// random flights: at every decision no mesh holds its twin inside its line, near or k times its span
let seed = 5; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
let bad = 0, far = 0, n = 0;
for (let k = 0; k < 6000; k++) {
  if (k === 3000) VDEPTH.k = 1;   // and with the floor governing
  if (rnd() < 0.1) camera.position.set(-2500 + rnd() * 12000, 2 + rnd() * 900, -2000 + rnd() * 4000);
  else camera.position.add(new V3(rnd() * 60 - 30, rnd() * 10 - 5, rnd() * 60 - 30));
  frameNo = k; vdepthUpdate();
  if (VDEPTH.eye.equals(camera.position)) for (const q of R) {
    n++;
    const d = Math.max(0, Math.hypot(q.x - camera.position.x, q.y - camera.position.y, q.z - camera.position.z) - q.r);
    if (q.mesh.material === q.twin) { far++; if (d < Math.max(VDEPTH.near, VDEPTH.k * q.span)) bad++; }
  }
}
out.flights = { bad, far, n };
// the hatch: off puts every original back; a distance turns it on again
vdepthDbg(0); out.off = { on: VDEPTH.on, allOrig: R.every((q) => q.mesh.material === q.mat) };
camera.position.set(0, 50, 0); frameNo = 1;
const st = vdepthDbg(500, 2); vdepthUpdate();
out.back = { on: st.on, near: st.near, k: st.k, far5: chunks[5].material === twinOf(chunks[5]).twin, near0: chunks[0].material === facadeMat, dbg: Object.keys(vdepthDbg()).sort() };
'''))

    def test_first_frame_compiles_every_twin(self):
        self.assertEqual(self.r['warm1'], {'allTwin': True, 'allUnculled': True, 'warm': 2})

    def test_second_frame_puts_the_culling_back(self):
        w = self.r['warm2']
        self.assertTrue(w['culled'])
        self.assertFalse(w['staged'])       # a mesh staged unculled stays so (its frame's own release culls it)
        self.assertTrue(w['nearOrig'])
        self.assertTrue(w['farTwin'])
        self.assertEqual(w['warm'], 0)

    def test_hysteresis(self):
        near, band = 300, 40
        state = 0   # the eye came from x 0 at 50 m, where the chunk was near
        for x, d, twin in self.r['seq']:
            state = (1 if d >= near else 0) if state else (1 if d > near + band else 0)
            self.assertEqual(twin, state, (x, d))
        # both ways across the line, and a stay on each side of it inside the band
        self.assertEqual([s[2] for s in self.r['seq']], [1, 1, 0, 0, 0, 1, 1, 0, 1])

    def test_the_span_line(self):
        self.assertEqual(self.r['spans'][:8], [141.4] * 8)   # a 100 m box: its faces' diagonals
        self.assertEqual(self.r['spans'][8], 204.0)          # the 40 by 200 m tower's side
        line, band = 8 * 141.42, 40
        state = 0   # the eye came from x 610, where the chunk was near
        for x, d, twin in self.r['seqK']:
            state = (1 if d >= line else 0) if state else (1 if d > line + band else 0)
            self.assertEqual(twin, state, (x, d))
        self.assertEqual([s[2] for s in self.r['seqK']], [0, 1, 1, 1, 0, 0, 1])

    def test_a_jump_is_decided_at_once(self):
        self.assertTrue(self.r['jump'])
        self.assertEqual(self.r['small'], [True, True])   # 10 m off the cadence waits (the twin never came back)

    def test_never_the_twin_inside_its_line(self):
        f = self.r['flights']
        self.assertEqual(f['bad'], 0, f)
        self.assertGreater(f['far'], 1000)

    def test_the_hatch(self):
        self.assertEqual(self.r['off'], {'on': False, 'allOrig': True})
        b = self.r['back']
        self.assertTrue(b['on']); self.assertEqual((b['near'], b['k']), (500, 2)); self.assertTrue(b['far5']); self.assertTrue(b['near0'])
        self.assertEqual(b['dbg'], ['band', 'decided', 'far', 'hostCells', 'hosts', 'k', 'meshes', 'near', 'on', 'span', 'swaps', 'twins', 'warm'])


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Span(unittest.TestCase):
    def test_longest_edge(self):
        r = node(harness(body=r'''
const box2 = new THREE.BoxGeometry(100, 40, 30);
const flatG = box2.toNonIndexed();
const freed = new THREE.BoxGeometry(10, 10, 10); freed.index.array = null;
const inter = new THREE.BufferGeometry();
inter.setAttribute('position', new THREE.InterleavedBufferAttribute(new THREE.InterleavedBuffer(new Float32Array(12), 4), 3, 0));
const tri = new THREE.BufferGeometry(); tri.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 300, 0, 0, 0, 0, 400], 3)); tri.setIndex([0, 1, 2]);
out.box = vdepthMeasure(box2).span; out.flat = vdepthMeasure(flatG).span; out.freed = vdepthMeasure(freed).span; out.inter = vdepthMeasure(inter).span; out.tri = vdepthMeasure(tri).span;
const cb = vdepthMeasure(box2).cells; out.cells = [cb.gx0, cb.gz0, cb.nx, cb.nz, [...cb.top].join(',')]; out.freedCells = vdepthMeasure(freed).cells;
// a scaled mesh's span is in world metres
chunks[0].scale.set(2, 2, 2); chunks[0].updateMatrixWorld(); VDEPTH.recs.length = 0; vdepthCollect();
out.scaled = VDEPTH.recs.find((q) => q.mesh === chunks[0]).span;
// a span the build took is used as it stands (the arrays are freed by then)
chunks[1].geometry.userData.vd = { span: 12, cells: { gx0: 9, gz0: -1, nx: 2, nz: 2, top: new Float32Array(4).fill(-Infinity) } }; VDEPTH.recs.length = 0; vdepthCollect();
out.readOnce = chunks[1].geometry.userData.vd;
out.taken = VDEPTH.recs.find((q) => q.mesh === chunks[1]).span;
'''))
        self.assertAlmostEqual(r['box'], (100 ** 2 + 40 ** 2) ** 0.5, 3)
        self.assertAlmostEqual(r['flat'], r['box'], 6)
        self.assertEqual(r['freed'], None)     # Infinity serialises as null: never far
        self.assertEqual(r['inter'], None)
        self.assertAlmostEqual(r['tri'], 500, 6)
        self.assertAlmostEqual(r['scaled'], 2 * (2 * 100 ** 2) ** 0.5, 3)
        self.assertEqual(r['taken'], 12)
        # a 100 by 40 by 30 m box round the origin: its sphere's grid runs from cell -1 to 0 each way, its triangles start
        # in all four, and each reaches the box's top
        self.assertEqual(r['cells'], [-1, -1, 2, 2, '20,20,20,20'])
        self.assertIsNone(r['freedCells'])
        self.assertIsNone(r['readOnce'])   # the cells are dropped once read

    def test_the_build_takes_the_span_before_the_upload(self):
        add = cut('  const addChunkMesh = (g, mat) => {', '  const flushUploads = ')
        self.assertIn('if (VDEPTH_WANT && mat.userData.vdepth) g.userData.vd = vdepthMeasure(g);', add)
        self.assertLess(add.index('g.userData.vd = vdepthMeasure(g)'), add.index('pendingUpload.push(m);'))
        self.assertIn('const VDEPTH_WANT = !!window.__useLogDepth && (VDEPTH_Q ? VDEPTH.near > 0 : isTouch);', SRC)


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Hosts(unittest.TestCase):
    def test_the_meshes_under_an_overlay_keep_fragment_depth(self):
        r = node(harness(body=r'''
// a lit panel on the roof of the block at x 2000 (its top at 40 m), merged as the skyline lights are, and a crown 200 m up
// over the block at x 3000, which is 40 m tall: that one sits on nothing of it
const panel = new THREE.BoxGeometry(20, 1, 20); panel.translate(2010, 40.4, 10);
const crown = new THREE.BoxGeometry(10, 4, 10); crown.translate(3010, 202, 10);
vdepthNoteOverlay(panel); vdepthNoteOverlay(crown);
out.cells = [...VDEPTH.hosts].map(([k, y]) => k + '@' + y.toFixed(1)).sort();
vdepthInit();
out.rows = VDEPTH.recs.map((q) => [Math.round(q.x), q.host ? 1 : 0]);
// the first frame warms only what can draw a twin; from 5 km everything else goes far, the host never does
camera.position.set(2000, 20, 5000); frameNo = 1; vdepthUpdate();
out.warmHost = chunks[2].material === facadeMat && chunks[2].frustumCulled === true;
frameNo = 2; vdepthUpdate(); frameNo = 5; vdepthUpdate();
out.far = VDEPTH.recs.map((q) => [Math.round(q.x), q.mesh.material === q.twin ? 1 : 0]);
// the neighbour rule: an overlay one cell off still counts, two cells off does not
const c = { gx0: 10, gz0: 10, nx: 3, nz: 3, top: new Float32Array([-Infinity, -Infinity, -Infinity, -Infinity, 30, -Infinity, -Infinity, -Infinity, -Infinity]) };
VDEPTH.hosts.clear(); VDEPTH.hosts.set('12,12', 31); out.beside = vdepthHosts(c);
VDEPTH.hosts.clear(); VDEPTH.hosts.set('13,11', 31); out.twoOff = vdepthHosts(c);
VDEPTH.hosts.clear(); VDEPTH.hosts.set('11,11', 32.5); out.above = vdepthHosts(c);   // over what the cell reaches, less 2 m
out.none = vdepthHosts(null);
// a mesh that does not sit at the origin cannot be read against the world cells: it keeps fragment depth
for (const q of VDEPTH.recs) q.mesh.material = q.mat;   // collected once, before any swap, as the page does
chunks[6].position.set(5, 0, 0); chunks[6].updateMatrixWorld(); VDEPTH.recs.length = 0; vdepthCollect();
out.moved = VDEPTH.recs.find((q) => q.mesh === chunks[6]).host;
out.dbg = vdepthDbg().hosts;
'''))
        self.assertEqual(r['cells'], ['20,0@39.9', '30,0@200.0'])   # one 100 m cell each, with the lowest vertex
        hosts = {x: h for x, h in r['rows']}
        self.assertEqual(hosts[2000], 1)          # the block under it
        self.assertEqual(hosts[1000], 0)          # its neighbours 1 km off do not
        self.assertEqual(hosts[3000], 0)          # 40 m tall under a crown at 200 m: not its building
        self.assertTrue(r['warmHost'])
        far = {x: f for x, f in r['far']}
        self.assertEqual(far[2000], 0)
        self.assertEqual(far[1000], 1)
        self.assertEqual(far[7000], 1)
        self.assertTrue(r['beside'])
        self.assertFalse(r['twoOff'])
        self.assertFalse(r['above'])
        self.assertTrue(r['none'])
        self.assertTrue(r['moved'])
        self.assertEqual(r['dbg'], 1)             # the moved one (the cells were read once and dropped)

    def test_every_overlay_is_noted_as_it_is_merged(self):
        for site in ('      const g = mergeColored(glowParts); freeOnUpload(g);\n      vdepthNoteOverlay(g);',
                     '      const g = mergeColored(lmTrim); freeOnUpload(g);\n      vdepthNoteOverlay(g);',
                     '      const g = mergeColored(themeParts); freeOnUpload(g);\n      vdepthNoteOverlay(g);',
                     '      const g=mergeColored(crownPanels);freeOnUpload(g);\n      vdepthNoteOverlay(g);',
                     '      const g = themeWashGeometry(themeSheets);\n      vdepthNoteOverlay(g);'):
            self.assertIn(site, SRC)
        self.assertEqual(SRC.count('vdepthNoteOverlay(g);'), 5)
        self.assertIn('const far = !q.host && vdepthFar(', SRC)


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class WhoGetsIt(unittest.TestCase):
    def run_case(self, **kw):
        return node(harness(body='vdepthInit(); out.on = VDEPTH.on; out.near = VDEPTH.near; out.meshes = VDEPTH.recs.length; out.warm = VDEPTH.warm;', **kw))

    def test_a_phone(self):
        self.assertEqual(self.run_case(), {'on': True, 'near': 300, 'meshes': 9, 'warm': 1})

    def test_a_desktop_is_unchanged(self):
        self.assertEqual(self.run_case(touch=False), {'on': False, 'near': 300, 'meshes': 0, 'warm': 0})

    def test_the_url_hatch(self):
        self.assertEqual(self.run_case(search='?dev=1&vdepth=0')['on'], False)
        r = self.run_case(search='?vdepth=450&dev=1', touch=False)
        self.assertEqual((r['on'], r['near'], r['meshes']), (True, 450, 9))

    def test_needs_log_depth_and_fragment_depth(self):
        self.assertFalse(self.run_case(logdepth=False)['on'])     # ?logdepth=0: nothing to move to the vertex stage
        self.assertFalse(self.run_case(gl2=False)['on'])          # WebGL 1 without EXT_frag_depth draws it there already


if __name__ == '__main__':
    unittest.main()
