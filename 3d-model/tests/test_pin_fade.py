"""Round 169: no pin through a building (Mike, from the phone: "I am still seeing pins through buildings when I first turn
to look at them. They quickly disappear but I want to avoid this at all costs").

Round 138 had a pin change its mind only when two captures agreed (or PIN_HOLD passed), hold PIN_DWELL and fade over
PIN_FADE both ways, and Round 143 kept a shown pin while anything in a 5 by 5 neighbourhood lay behind its tip; a tip
outside the image read as visible. So a pin turning into view behind a building showed for up to a second. Now:
- unknown is hidden: no image, the tip outside it or past its reach, or an image drawn before the pin came into view
- a covered answer hides at once (no fade out, no hold, no dwell); showing keeps the guard (one image after an unknown,
  two images or PIN_HOLD and PIN_DWELL since the last covered answer after a covered one) and fades in over PIN_FADE
- the 5 by 5 stay-visible test is gone (it showed pins whose own 3 by 3 neighbourhood was covered)
- the cadence: while the eye moves an image every moveEvery drawn frames and at once when the newest no longer holds the
  screen; a still eye keeps the old cadence; a pin waiting for an image asks for one; a phone with a far tip in view
  draws near images between complete ones every fullEvery frames
The block (the state, the step, the judge, the cadence and pinOccUpdate) is cut from app.js and run under Node against
scripted images; the answers themselves (pinOccAnswer and the gate) are test_pin_gate.py's."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


def cut(start, end):
    a = SRC.index(start)
    return SRC[a:SRC.index(end, a)]


class PinPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        cls.block = cut('  const PIN_FADE = ', '  function frame(now, once) {')

    def run_js(self, body, touch=True):
        # images: pinOccCapture records a render at frameNo; its read lands LAT frames later (poll), when the CPU's image becomes it.
        # truth(x, f): the answer an image drawn at frame f gives for the pin at x (1 clear, 0 covered, -1 outside). zone(x): in view
        script = r'''
let frameNo = 0, moving = true, LAT = 1, covers = true;
const isTouch = TOUCH, PIN_NEAR = 900, PIN_JUMP = 300, PIN_COVER = 1.25;
let truth = () => 1, zone = () => true;
const mkCh = () => ({ slots: [], gate: -1, cpu: { ok: false, frame: -1e9 }, last: -1e9 });
const PIN_OCC = { ok: false, every: isTouch ? 10 : 5, moveEvery: isTouch ? 2 : 1, fullEvery: isTouch ? 10 : 1, far: 30000, want: -99, hid: 0, wait: -1e9, waitFar: false, waitTip: -1e9, waitTipFar: false,
  lastFrame: -1e9, fresh: false, reach: 0, reachTip: 0, near: mkCh(), full: mkCh(), cause: { first: 0, old: 0, jump: 0, cadence: 0, cover: 0, wait: 0, reach: 0, full: 0, near: 0 },
  lastPos: { copy() {} }, lastQuat: { copy() {} }, pvPos: { copy() {} }, pvQuat: { copy() {} } };
const PIN_ASYNC = { eye: {} };
const camera = { position: { x: 0, y: 0, z: 0, distanceToSquared: () => (moving ? 1 : 0) }, quaternion: { dot: () => 1 }, updateMatrixWorld() {}, projectionMatrix: {}, matrixWorldInverse: {} };
const _pzm = { multiplyMatrices() {} };
const renders = [], landed = [];
let inflight = [];
function pinOccCapture(kind = 'full') {
  const ch = PIN_OCC[kind];
  ch.slots = [{ frame: frameNo, reach: kind === 'near' ? 945 : 30000 }]; ch.gate = 0; ch.last = frameNo;
  renders.push([frameNo, kind]);
  if (!PIN_OCC.ok) { PIN_OCC.ok = true; ch.cpu.ok = true; ch.cpu.frame = frameNo; return 'now'; }
  inflight.push({ f: frameNo, kind });
  return 'later';
}
function pinOccRead() {}
function poll() { PIN_OCC.fresh = false; const due = inflight.filter((q) => frameNo - q.f >= LAT); inflight = inflight.filter((q) => frameNo - q.f < LAT); for (const q of due) { const c = PIN_OCC[q.kind].cpu; c.ok = true; c.frame = Math.max(c.frame, q.f); PIN_OCC.fresh = true; landed.push(q.f); } }
const pinOccCovers = () => covers, pinOccNewest = () => PIN_OCC.full.slots[0];
const cpuFrame = () => Math.max(PIN_OCC.full.cpu.frame, PIN_OCC.near.cpu.ok ? PIN_OCC.near.cpu.frame : -1e9);
function pinOccAnswer(x, y, z, arr = -1e9) { if (!PIN_OCC.full.cpu.ok) return -1; const f = cpuFrame(); if (f < arr) return -1; return truth(x, f); }
function pinZone(x) { return zone(x); }
function mesh(xs) {
  const cap = 8, mat = new Float32Array(cap * 16), vis = new Float32Array(cap).fill(1);
  xs.forEach((x, i) => { mat[i * 16 + 12] = x; });
  return { visible: true, count: xs.length, userData: {}, instanceMatrix: { count: cap, array: mat }, geometry: { attributes: { aPinVis: { array: vis, needsUpdate: false } } } };
}
const PIN_MESHES = [];
BLOCK
const m = mesh([0]); PIN_MESHES.push(m);
const vis = (i = 0) => +m.geometry.attributes.aPinVis.array[i].toFixed(3);
const step = (dt = 1 / 60) => { frameNo++; poll(); pinOccUpdate(dt); };
const run = (n, dt = 1 / 60) => { const out = []; for (let i = 0; i < n; i++) { step(dt); out.push(vis()); } return out; };
BODY
'''.replace('TOUCH', 'true' if touch else 'false').replace('BLOCK', self.block).replace('BODY', body)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_hidden_until_an_image_drawn_after_its_arrival_says_clear(self):
        # the pin is out of view, then comes into view at frame 21: the image the CPU holds then is older, so the pin waits for one
        # drawn after its arrival, shows on the frame that image lands, and rises over PIN_FADE
        out = self.run_js('''
zone = () => frameNo > 20; moving = false;
run(20);
const s = run(40);
console.log(JSON.stringify({ s, renders, landed }));''')
        s = out['s']
        self.assertEqual(s[0], 0)                                    # arrived: hidden, whatever the old image says
        first = next(i for i, v in enumerate(s) if v > 0)
        arrival = 21
        drawn = [f for f, k in out['renders'] if f >= arrival][0]     # the image the waiting pin asked for
        self.assertLessEqual(drawn, arrival + 2)
        self.assertEqual(first + 21, drawn + 1)                      # shown the frame that image lands (LAT 1)
        rise = s[first:first + 14]
        self.assertEqual(rise, sorted(rise))
        self.assertGreaterEqual(sum(1 for v in rise if 0 < v < 1), 10)   # an ease over 0.2 s, not a snap
        self.assertEqual(s[-1], 1)

    def test_a_covered_answer_hides_at_once(self):
        # shown; then the image drawn at frame 30 says covered: the pin is gone the frame that image lands, with no fade and no hold
        out = self.run_js('''
run(30);
truth = (x, f) => (f >= 30 ? 0 : 1);
const s = run(10);
console.log(JSON.stringify({ s, landed }));''')
        s = out['s']
        self.assertEqual(s[0], 1)
        k = s.index(0)
        self.assertTrue(all(v == 1 for v in s[:k]))
        self.assertTrue(all(v == 0 for v in s[k:]))                  # 1 to 0 in one frame
        self.assertLessEqual(k, 2)

    def test_showing_after_covered_needs_two_images_and_the_dwell(self):
        # covered by the image of frame 30, clear again from the image of frame 32: it waits for two clear images and PIN_DWELL
        out = self.run_js('''
run(30);
truth = (x, f) => (f >= 30 && f < 32 ? 0 : 1);
const s = run(60);
console.log(JSON.stringify({ s }));''')
        s = out['s']
        hid = s.index(0)
        up = next(i for i in range(hid, len(s)) if s[i] > 0)
        self.assertGreaterEqual(up - hid, 18)                        # PIN_DWELL: 0.3 s at 60 fps, from the covered answer
        self.assertEqual(s[-1], 1)

    def test_one_image_brings_back_a_pin_that_was_only_unknown(self):
        out = self.run_js('''
run(30);
truth = (x, f) => (f >= 30 && f < 34 ? -1 : 1);   // two images that do not hold the tip (outside them), then one that says clear
const s = run(30);
console.log(JSON.stringify({ s, landed }));''')
        s = out['s']
        hid = s.index(0)
        up = next(i for i in range(hid, len(s)) if s[i] > 0)
        self.assertLessEqual(up - hid, 6)                            # no dwell: the first clear image
        self.assertGreater(up - hid, 0)

    def test_no_blink_at_a_building_edge(self):
        # a tip on an edge: the images alternate covered and clear. The pin hides at the first covered answer and stays hidden
        out = self.run_js('''
run(30);
truth = (x, f) => ((f >> 1) % 2 ? 0 : 1);
const s = run(120);
let ups = 0; for (let i = 1; i < s.length; i++) if (s[i] > s[i - 1] && s[i - 1] === 0) ups++;
console.log(JSON.stringify({ ups, max: Math.max(...s.slice(10)) }));''')
        self.assertEqual(out['ups'], 0)
        self.assertEqual(out['max'], 0)

    def test_still_eye_moving_pin(self):
        # no image comes while the eye is still (the 120-frame one aside): a pin moving out from behind a building shows after
        # PIN_HOLD (and the dwell), one moving behind a building hides at once, on the answer the old image gives its new place
        out = self.run_js('''
run(30);
moving = false; const r0 = renders.length;
truth = (x, f) => (x > 5 ? 0 : 1);
m.instanceMatrix.array[12] = 10; const hide = run(3);
m.instanceMatrix.array[12] = 0; const back = run(60);
console.log(JSON.stringify({ hide, at: back.findIndex((v) => v > 0), images: renders.length - r0 }));''')
        self.assertEqual(out['hide'], [0, 0, 0])
        self.assertEqual(out['images'], 0)
        self.assertGreaterEqual(out['at'], 26)                       # 0.45 s at 60 fps
        self.assertLessEqual(out['at'], 29)

    def test_a_new_pin_in_a_slot_arrives(self):
        # the slot now holds a pin 500 m away (the set reshuffled), and a pin new to slot 1: both wait for an image drawn after them
        out = self.run_js('''
moving = false; run(30);
m.instanceMatrix.array[12] = 500; m.count = 2; m.instanceMatrix.array[16 + 12] = 900;
const a = []; for (let i = 0; i < 12; i++) { step(); a.push([vis(0), vis(1)]); }
console.log(JSON.stringify({ first: a[0], later: a[a.length - 1] }));''')
        self.assertEqual(out['first'], [0, 0])
        self.assertGreater(out['later'][0], 0)
        self.assertGreater(out['later'][1], 0)

    def test_a_layer_off_and_on_arrives_anew(self):
        out = self.run_js('''
moving = false; run(30);
m.visible = false; run(5); const off = vis();
m.visible = true; step(); const back = vis(); run(10); const later = vis();
console.log(JSON.stringify({ off, back, later }));''')
        self.assertEqual(out['off'], 0)
        self.assertEqual(out['back'], 0)
        self.assertGreater(out['later'], 0)

    def test_out_of_view_is_hidden(self):
        out = self.run_js('''
run(30); zone = () => false; const s = run(3);
console.log(JSON.stringify({ s }));''')
        self.assertEqual(out['s'], [0, 0, 0])

    def test_cadence_moving_and_still(self):
        out = self.run_js('''
moving = true; run(40); const mv = renders.filter(([f]) => f > 10).map(([f]) => f);
renders.length = 0; moving = false; run(100); const still = renders.length;
covers = false; moving = true; renders.length = 0; run(6); const cov = renders.map(([f]) => f);
console.log(JSON.stringify({ gaps: mv.slice(1).map((f, i) => f - mv[i]), still, cov }));''')
        self.assertTrue(out['gaps'] and all(g == 2 for g in out['gaps']), out['gaps'])   # every 2nd drawn frame on a phone while moving
        self.assertEqual(out['still'], 0)                             # a still eye that has not changed draws none
        cov = out['cov']
        self.assertEqual([b - a for a, b in zip(cov, cov[1:])], [1] * (len(cov) - 1))   # the newest no longer holds the screen: every frame

    def test_cadence_on_a_computer(self):
        out = self.run_js('''
moving = true; run(30); const f = renders.filter(([q]) => q > 5);
console.log(JSON.stringify({ gaps: f.slice(1).map((q, i) => q[0] - f[i][0]), kinds: [...new Set(f.map((q) => q[1]))] }));''', touch=False)
        self.assertTrue(all(g == 1 for g in out['gaps']))
        self.assertEqual(out['kinds'], ['full'])

    def test_near_images_between_complete_ones_on_a_phone(self):
        # a far tip (a flight, a placard) in view while the eye moves: a complete image every fullEvery frames, near ones between
        out = self.run_js('''
m.count = 2; m.instanceMatrix.array[16 + 12] = 5000; m.instanceMatrix.array[16 + 14] = 0;
camera.position.x = 0;
run(80);
const f = renders.filter(([q]) => q > 20);
console.log(JSON.stringify({ kinds: f.map((q) => q[1][0]).join(''), reach: PIN_OCC.reach }));''')
        k = out['kinds']
        self.assertIn('n', k)
        self.assertIn('f', k)
        full = [i for i, c in enumerate(k) if c == 'f']
        self.assertTrue(all(4 <= b - a <= 6 for a, b in zip(full, full[1:])), k)   # every 10 drawn frames: every 5th image
        self.assertGreater(out['reach'], 900)

    def test_constants_and_wiring(self):
        self.assertIn('const PIN_FADE = 0.2, PIN_HOLD = 0.45, PIN_DWELL = 0.3;', SRC)
        self.assertIn('const PIN_OCC_MOVE_EVERY = isTouch ? 2 : 1;', SRC)
        self.assertIn('const PIN_OCC_FULL_EVERY = isTouch ? 10 : 1;', SRC)
        self.assertIn('const PIN_OCC_READ_EVERY = isTouch ? 4 : 2;', SRC)   # the reads' synchronous landing, at most this often
        self.assertIn('if (A.sync || frameNo - A.at < PIN_OCC_READ_EVERY) return;', SRC)
        self.assertIn('    pinOccUpdate(dt);\n', SRC)
        # the 5 by 5 stay-visible test is gone: one 3 by 3 rule, as the gate's
        self.assertNotIn('st.tgt[i] ? 2 : 1', SRC)
        self.assertNotIn('pinOccVisible(x, y, z, rad', SRC)
        # the pick still refuses a pin that is more than half gone
        self.assertIn('if (v.getX(hit.instanceId) < 0.5) continue;', SRC)
        # Round 143's wide image through its own camera, now with a reach
        self.assertIn('w: Math.round((isTouch ? 160 : 256) * 1.5), wide: 1.5,', SRC)
        self.assertIn("e[10] = -(f + n) / (f - n); e[14] = -2 * f * n / (f - n);", SRC)


if __name__ == '__main__':
    unittest.main()
