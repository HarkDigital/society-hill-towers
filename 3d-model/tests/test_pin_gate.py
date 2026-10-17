"""Round 169: what an image says of a pin's tip, on the CPU and in the gate.

- The CPU's answer (pinOccAnswer): 1 clear, 0 covered, -1 unknown (no image, the tip outside it, behind its eye or past its
  reach, or the image drawn before the pin came into view), by the 3 by 3 rule with the need vz - (2.5 + 0.02 vz), clamped
  under the sky's value so a tip past the packing range is judged by what stands in front of it. Two images: a near one
  for the tips within its reach while it is the newer, and for a tip past it the near one for what stands within its
  reach and the complete one, read along the same ray (all four pixels round it), for the rest.
- The placards' answer (pinOccTipAnswer): once the eye has moved or turned since the image was drawn, the samples an image
  drawn now would take, carried back, clear along the whole slide a building nearer the eye could have made.
- The gate (PIN_GATE_GLSL): the same rule in every instanced pin's vertex shader, reading the latest images; checked here by
  its text (tests/pin_gate_gpu.html runs it on a GPU against the CPU's answers).
Cut from app.js and run under Node against synthetic images."""
import json
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


HARNESS = r'''
const THREE = require(THREE_PATH);
let frameNo = 100;
const W = 240, H = 120, FAR = 30000;
const PIN_OCC = { w: W, h: H, far: FAR, wide: 1.5, near: { cpu: { ok: false, frame: -1e9 } }, full: { cpu: { ok: false, frame: -1e9 } } };
const _pov = new THREE.Vector3();
const camera = new THREE.PerspectiveCamera(60, 2, 0.75, 26000);
camera.updateMatrixWorld();
// an image drawn from the camera as it stands, reaching `reach`, of a scene given as depth(ndcX, ndcY) (metres along the view axis)
function image(depth, reach = FAR, frame = frameNo) {
  camera.updateMatrixWorld();
  const c = camera, proj = c.projectionMatrix.clone();
  proj.elements[0] /= 1.5; proj.elements[5] /= 1.5;
  const n = c.near, f = Math.min(c.far, reach); proj.elements[10] = -(f + n) / (f - n); proj.elements[14] = -2 * f * n / (f - n);
  const buf = new Uint8Array(W * H * 4);
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const d = Math.min(depth(((i + 0.5) / W * 2 - 1) * 1.5, ((j + 0.5) / H * 2 - 1) * 1.5), FAR * 0.99995);
    let x = d / FAR * 256; const o = (j * W + i) * 4;   // occUnpack's own base-256 digits
    buf[o + 3] = Math.floor(x); x = (x - buf[o + 3]) * 256; buf[o + 2] = Math.floor(x); x = (x - buf[o + 2]) * 256; buf[o + 1] = Math.floor(x); x = (x - buf[o + 1]) * 256; buf[o] = Math.min(255, Math.round(x));
  }
  return { buf, view: c.matrixWorldInverse.clone(), viewInv: c.matrixWorld.clone(), proj, frame, reach: f, eye: c.position.clone(), quat: c.quaternion.clone(), ok: true };
}
// a point at screen NDC (x, y) of the eye as it stands, `dist` metres along the view axis
const at = (x, y, dist) => new THREE.Vector3(x, y, 0.5).unproject(camera).sub(camera.position).normalize().multiplyScalar(dist / new THREE.Vector3(x, y, 0.5).unproject(camera).sub(camera.position).normalize().dot(new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion))).add(camera.position);
BLOCK
'''


class PinAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        cls.block = cut('  const occUnpack = ', '  // the zone a pin is judged in')

    def run_js(self, body):
        script = HARNESS.replace('THREE_PATH', THREE).replace('BLOCK', self.block) + body
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_one_image(self):
        # a wall 100 m off over the left half of the image, the sky elsewhere
        out = self.run_js(r'''
const wall = (x) => (x < 0 ? 100 : 1e9);
const r = {};
r.none = pinOccAnswer(...at(0.5, 0, 300).toArray());                     // no image yet: unknown
PIN_OCC.full.cpu = image(wall);
const p = (x, d) => pinOccAnswer(...at(x, 0, d).toArray());
r.behind = p(-0.5, 300); r.clear = p(0.5, 300); r.front = p(-0.5, 60);   // behind the wall, beside it, in front of it
r.edge = p(-2 / 240 * 1.5 * 0.5, 300);                                    // a pixel inside the wall's edge: its 3 by 3 finds the sky
r.deep = p(-4 / 240 * 1.5 * 2, 300);                                      // four pixels in: covered
r.outside = pinOccAnswer(...at(1.6, 0, 300).toArray());                   // outside the 1.5-times-wide image
r.behindEye = pinOccAnswer(0, 0, 50);                                     // behind the eye
r.old = pinOccAnswer(...at(0.5, 0, 300).toArray(), frameNo + 1);          // the image drawn before the pin arrived
r.fresh = pinOccAnswer(...at(0.5, 0, 300).toArray(), frameNo);
r.visible = pinOccVisible(...at(1.6, 0, 300).toArray());                  // unknown is hidden
// a reach: the image drawn to 1,000 m knows nothing of a tip at 1,200
PIN_OCC.full.cpu = image(wall, 1000);
r.pastReach = p(0.5, 1200); r.inReach = p(0.5, 900);
// far off: a tip 25 km off in the sky is clear, one behind a hill 20 km off is covered, one past the camera's own far plane unknown
PIN_OCC.full.cpu = image((x) => (x < 0 ? 20000 : 1e9));
r.farSky = p(0.5, 25000); r.farHill = p(-0.5, 25000); r.pastFar = p(0.5, 27000);
console.log(JSON.stringify(r));''')
        self.assertEqual(out, {'none': -1, 'behind': 0, 'clear': 1, 'front': 1, 'edge': 1, 'deep': 0, 'outside': -1, 'behindEye': -1,
                               'old': -1, 'fresh': 1, 'visible': False, 'pastReach': -1, 'inReach': 1, 'farSky': 1, 'farHill': 0, 'pastFar': -1})

    def test_two_images(self):
        # the complete image F, older, sees a far tower at 3 km on the left; the near image N, newer, reaches 945 m and sees a
        # near wall at 200 m over the lower left quarter. A near tip reads N alone; a far tip reads both
        out = self.run_js(r'''
const r = {};
PIN_OCC.full.cpu = image((x, y) => (x < 0 ? 3000 : 1e9), FAR, 90);
PIN_OCC.near.cpu = image((x, y) => (x < 0 && y < 0 ? 200 : 1e9), 945, 99);
const p = (x, y, d) => pinOccAnswer(...at(x, y, d).toArray());
r.nearBehindWall = p(-0.5, -0.5, 500); r.nearClear = p(-0.5, 0.5, 500);          // N alone: F's far tower does not cover a tip at 500 m
r.farBehindWall = p(-0.5, -0.5, 5000); r.farBehindTower = p(-0.5, 0.5, 5000); r.farClear = p(0.5, 0.5, 5000);
r.farPastF = pinOccAnswer(...at(0.5, 0.5, 5000).toArray()); PIN_OCC.full.cpu.reach = 4000; r.farPastFReach = p(0.5, 0.5, 5000);
PIN_OCC.full.cpu.reach = FAR;
// once F is the newer, it answers alone
PIN_OCC.full.cpu.frame = 100; r.fNewer = p(-0.5, -0.5, 500);
console.log(JSON.stringify(r));''')
        self.assertEqual(out, {'nearBehindWall': 0, 'nearClear': 1, 'farBehindWall': 0, 'farBehindTower': 0, 'farClear': 1,
                               'farPastF': 1, 'farPastFReach': -1, 'fNewer': 1})

    def test_placards_answer_under_motion(self):
        # a placard's tip 2 km off, one image pixel over a roof edge 150 m off (the plain rule finds the sky just over the edge):
        # from the eye that drew the image it is clear; once the eye has moved sideways toward the building the edge slides over
        # it and it is called covered; a turn alone keeps it clear; a tip well clear of the edge stays clear through the move
        out = self.run_js(r'''
const edgeY = 0.0;   // screen NDC: below it a building 150 m off
PIN_OCC.full.cpu = image((x, y) => (y < edgeY ? 150 : 1e9));
const tip = at(0.2, edgeY - 1.2 / 120 * 1.5, 2000);   // a pixel and a bit inside the edge: the plain 3 by 3 finds the sky over it
const high = at(0.2, 0.3, 2000);
const r = { plain: pinOccAnswer(...tip.toArray()), still: pinOccTipAnswer(...tip.toArray()) };
camera.rotation.y += 0.01; camera.updateMatrixWorld(); r.turned = pinOccTipAnswer(...tip.toArray()); camera.rotation.y -= 0.01;
camera.position.y -= 3; camera.updateMatrixWorld(); r.movedDown = pinOccTipAnswer(...tip.toArray()); r.highMoved = pinOccTipAnswer(...high.toArray());
console.log(JSON.stringify(r));''')
        self.assertEqual(out['plain'], 1)
        self.assertEqual(out['still'], 1)
        self.assertEqual(out['movedDown'], 0)                       # the eye went 3 m down: the roof edge rose over the tip
        self.assertEqual(out['highMoved'], 1)

    def test_a_tap_asks_the_gates_images(self):
        # review: while the eye moves the gate reads images newer than the CPU's, so a pin at half its fade or more could be hidden
        # by the gate and still take a tap. The tap reads the gate's own images (each once) and asks them what the gate asks
        tap = cut('  const PIN_TAP = ', '  // the building-anchored pins')
        out = self.run_js(r'''
const pinOccImg = () => ({ buf: null, view: new THREE.Matrix4(), viewInv: new THREE.Matrix4(), proj: new THREE.Matrix4(), frame: -1e9, reach: 0, ok: false });
let reads = 0;
const renderer = { capabilities: { vertexTextures: true }, readRenderTargetPixels(rt, x, y, w, h, buf) { reads++; buf.set(rt.buf); } };
const slot = (I) => ({ rt: { buf: I.buf }, view: I.view, viewInv: I.viewInv, proj: I.proj, reach: I.reach, frame: I.frame, eye: I.eye, quat: I.quat });
PIN_OCC.near.slots = []; PIN_OCC.near.gate = -1; PIN_OCC.full.slots = []; PIN_OCC.full.gate = -1; PIN_OCC.moveEvery = 2;
const pinOccNewest = () => { const a = PIN_OCC.near.slots[PIN_OCC.near.gate], b = PIN_OCC.full.slots[PIN_OCC.full.gate]; return a && (!b || a.frame > b.frame) ? a : b; };
''' + tap + r'''
const r = {};
const tip = at(-0.5, 0, 300).toArray(), far = at(-0.5, -0.5, 5000).toArray(), farClear = at(0.5, 0.5, 5000).toArray();
r.none = pinGateShows(...tip);                                            // no image: the gate hides every pin
PIN_OCC.full.cpu = image(() => 1e9, FAR, 90);                             // the CPU's image, older: clear
PIN_OCC.full.slots = [slot(image((x) => (x < 0 ? 100 : 1e9), FAR, 99))]; PIN_OCC.full.gate = 0;   // the gate's, newer: a wall
r.cpu = pinOccAnswer(...tip); r.gate = pinGateShows(...tip); r.clear = pinGateShows(...at(0.5, 0, 300).toArray());
r.reads = reads;                                                          // the gate's image read once for both questions
PIN_OCC.near.slots = [slot(image((x, y) => (x < 0 && y < 0 ? 200 : 1e9), 945, 100))]; PIN_OCC.near.gate = 0;   // a newer near image
r.nearTip = pinGateShows(...at(-0.5, 0.5, 500).toArray());                // within its reach: the near image alone (clear there)
r.farBehind = pinGateShows(...far); r.farClear = pinGateShows(...farClear);   // past it: both, as the gate reads them
r.reads2 = reads;
renderer.capabilities.vertexTextures = false; r.noGate = pinGateShows(...tip);   // no gate on this GPU: the CPU's state alone
// the things a tap finds without a gate (a post, a bus, a tree: pickOccluded) ask whether a building covers them, only while the
// newest image is the eye's own (drawn this frame or the one before, or the eye has not moved since)
PIN_OCC.near.slots = []; PIN_OCC.near.gate = -1;
r.covers = pinGateCovers(...tip); r.coversClear = pinGateCovers(...at(0.5, 0, 300).toArray()); r.coversOutside = pinGateCovers(...at(1.6, 0, 300).toArray());
frameNo = 200; r.coversStill = pinGateCovers(...tip);                     // an old image, the eye where it was drawn
camera.position.x += 1; camera.updateMatrixWorld(); r.coversMoved = pinGateCovers(...tip);   // an old image from elsewhere: it says nothing
console.log(JSON.stringify(r));''')
        self.assertEqual(out, {'none': False, 'cpu': 1, 'gate': False, 'clear': True, 'reads': 1, 'nearTip': True, 'farBehind': False,
                               'farClear': True, 'reads2': 2, 'noGate': True, 'covers': True, 'coversClear': False, 'coversOutside': False,
                               'coversStill': True, 'coversMoved': False})

    def test_the_gate_text(self):
        g = cut('  const PIN_GATE_GLSL = `', '`;\n')
        # the need and the sky's clamp, the packing, the 3 by 3 neighbourhood, NEAREST reads at pixel centres
        self.assertIn('float pinOccNeed(float vz) { return min(vz - (2.5 + 0.02 * vz), uPinOccInfo.z * 0.9998); }', g)
        self.assertIn('vec4(1.0 / 16777216.0, 1.0 / 65536.0, 1.0 / 256.0, 1.0)) * (255.0 / 256.0) * uPinOccInfo.z', g)
        self.assertIn('texture2D(t, (q + 0.5) / uPinOccInfo.xy)', g)
        self.assertEqual(g.count('for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {'), 2)
        # collapsed with no image, outside it, behind its eye or past its reach
        self.assertIn('if (uPinOccReach.y < 0.5) return 0.0;', g)
        self.assertIn('if (vz <= 1.0 || vz > reach) return 0.0;', g)
        self.assertIn('if (pinOccOut(p)) return 0.0;', g)
        # the tip is the instance's origin, through the pin's own model matrix; the two-image branch reads B round the carried ray
        self.assertIn('vec4 w = modelMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);', g)
        self.assertIn('if (vza <= uPinOccReach.x) return pinOccOne(uPinOccA, uPinOccViewA, uPinOccProjA, uPinOccReach.x, w);', g)
        self.assertIn('float needA = uPinOccReach.x * 0.999, needB = pinOccNeed(vzb);', g)
        self.assertIn('uniform highp sampler2D uPinOccA, uPinOccB;', g)
        # aPinVis multiplies in, and the vertex hook shares one set of uniforms among every pin
        self.assertIn("transformed *= aPinVis * pinOccGate();", SRC)
        self.assertIn('u.uPinOccA = G.texA; u.uPinOccB = G.texB; u.uPinOccViewA = G.viewA; u.uPinOccViewAInv = G.viewAInv; u.uPinOccProjA = G.projA;', SRC)
        self.assertIn("mat.customProgramCacheKey = () => 'pinAnchor:gate:'", SRC)
        # the CPU's answer uses the same constants
        cpu = cut('  const occUnpack = ', '  // the zone a pin is judged in')
        self.assertIn('Math.min(vz - (2.5 + vz * 0.02), PIN_OCC.far * 0.9998)', cpu)
        self.assertIn('const needA = N.reach * 0.999, needB = occNeed(vzb)', cpu)
        # the gate reads the new images the frame they are drawn
        self.assertIn('    pinGateSync();\n', cut('  function pinOccCapture(kind', '  function pinGateSync() {'))


if __name__ == '__main__':
    unittest.main()
