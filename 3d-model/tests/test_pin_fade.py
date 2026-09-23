"""Round 138: the pins no longer flash as the eye moves (Mike: "the pins flashing and disappearing while I move around").

A pin's visibility comes from a small depth image recaptured every few frames, and a tip beside a building's edge
could land on either side of it from one capture to the next. pinOccUpdate now changes a pin's state only when two
captures agree (or the answer has held PIN_HOLD seconds, for a pin moving while the eye is still), holds a new state
PIN_DWELL seconds, and eases aPinVis over PIN_FADE seconds instead of snapping. A pin new to its slot takes its answer
at once. The block is cut from app.js and run under Node against scripted capture results."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PinFade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = (ROOT / 'app.js').read_text()
        cls.block = src[src.index('  const PIN_FADE = '):src.index('  function frame(now, once) {')]

    def run_js(self, body):
        script = r'''
let frameNo = 0, moving = true, answer = 1;
const PIN_OCC = { ok: false, every: 5, want: -99, hid: 0, lastFrame: -1e9, lastPos: { copy() {} }, lastQuat: { copy() {} } };
const camera = { position: { distanceToSquared: () => (moving ? 1 : 0) }, quaternion: { dot: () => 1 } };
let captures = 0;
function pinOccCapture() { PIN_OCC.ok = true; captures++; }
function pinOccVisible(x, y, z, rad = 1) { return answer === 'edge' ? rad >= 2 : answer === 1; }   // 'edge': only the wide neighbourhood finds the gap
function mesh(xs) {
  const cap = 8, mat = new Float32Array(cap * 16), vis = new Float32Array(cap).fill(1);
  xs.forEach((x, i) => { mat[i * 16 + 12] = x; });
  return { visible: true, count: xs.length, userData: {}, instanceMatrix: { count: cap, array: mat }, geometry: { attributes: { aPinVis: { array: vis, needsUpdate: false } } } };
}
const PIN_MESHES = [];
BLOCK
const m = mesh([0]); PIN_MESHES.push(m);
const vis = () => +m.geometry.attributes.aPinVis.array[0].toFixed(3);
const run = (n, a, dt = 1 / 60) => { const out = []; for (let i = 0; i < n; i++) { if (a !== undefined) answer = typeof a === 'function' ? a(i) : a; frameNo++; pinOccUpdate(dt); out.push(vis()); } return out; };
BODY
'''.replace('BLOCK', self.block).replace('BODY', body)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_one_capture_blip_is_ignored(self):
        # visible, then ONE capture (frames 5..9) says hidden, then visible again: the pin never moves
        out = self.run_js('''
run(20, 1);
const s = run(20, (i) => (i < 5 ? 0 : 1));
console.log(JSON.stringify({ min: Math.min(...s) }));''')
        self.assertEqual(out['min'], 1)

    def test_two_captures_hide_and_it_eases(self):
        out = self.run_js('''
run(20, 1);
const s = run(40, 0);
console.log(JSON.stringify({ s }));''')
        s = out['s']
        self.assertEqual(s[0], 1)                                   # the first disagreeing capture changes nothing
        self.assertEqual(s[-1], 0)                                  # two agreeing captures hide it
        mids = [v for v in s if 0 < v < 1]
        self.assertGreaterEqual(len(mids), 8)                       # 0.2 s at 60 fps: an ease, not a snap
        self.assertEqual(s, sorted(s, reverse=True))                # and a monotone one

    def test_dwell_holds_a_fresh_state(self):
        # hidden by two captures, then visible at once for two captures: it stays hidden until PIN_DWELL has passed
        out = self.run_js('''
run(20, 1);
const hide = run(10, 0);                                    // frames that hide it (the second capture lands in here)
const back = run(40, 1);
const firstUp = back.findIndex((v, i) => i > 0 && v > back[i - 1]);
console.log(JSON.stringify({ hideEnd: hide[hide.length - 1], firstUp }));''')
        self.assertLess(out['hideEnd'], 1)
        # the pin started hiding at the second capture (frame 10 of the hide run); it may rise again only 0.3 s (18 frames) later
        self.assertGreaterEqual(out['firstUp'], 18 - 10 - 1)

    def test_still_eye_moving_pin_times_out(self):
        # no capture comes while the eye is still (the 120-frame fallback aside), so a moving pin's answer is taken after PIN_HOLD
        out = self.run_js('''
run(20, 1);
moving = false; const c0 = captures;
const s = run(40, 0);
console.log(JSON.stringify({ at: s.findIndex((v) => v < 1), caps: captures - c0 }));''')
        self.assertEqual(out['caps'], 0)
        self.assertGreaterEqual(out['at'], 26)                     # 0.45 s at 60 fps
        self.assertLessEqual(out['at'], 29)

    def test_new_pin_in_a_slot_takes_its_answer_at_once(self):
        out = self.run_js('''
run(20, 1);
m.instanceMatrix.array[12] = 500;                          // the slot now holds a pin 500 m away (the set reshuffled)
answer = 0; frameNo++; pinOccUpdate(1 / 60); const moved = vis();
m.count = 2; m.instanceMatrix.array[16 + 12] = 900;        // a pin new to slot 1
frameNo++; pinOccUpdate(1 / 60); const fresh = +m.geometry.attributes.aPinVis.array[1].toFixed(3);
console.log(JSON.stringify({ moved, fresh }));''')
        self.assertEqual(out, {'moved': 0, 'fresh': 0})

    def test_an_edge_pin_keeps_its_state(self):
        # Round 143: a tip on a building's edge (visible only to the 5 by 5 ask) neither hides a shown pin nor shows a hidden one
        out = self.run_js('''
run(30, 1); const shown = run(120, 'edge');
const m2 = mesh([500]); PIN_MESHES.length = 0; PIN_MESHES.push(m2);
const v2 = () => +m2.geometry.attributes.aPinVis.array[0].toFixed(3);
const hid = []; for (let i = 0; i < 120; i++) { answer = 'edge'; frameNo++; pinOccUpdate(1 / 60); hid.push(v2()); }
console.log(JSON.stringify({ shownMin: Math.min(...shown), hiddenMax: Math.max(...hid) }));''')
        self.assertEqual(out, {'shownMin': 1, 'hiddenMax': 0})

    def test_wide_image(self):
        src = (ROOT / 'app.js').read_text()
        # Round 143: the depth image covers 1.5 times the screen each way through its own camera, with the real near and far
        self.assertIn('w: Math.round((isTouch ? 160 : 256) * 1.5), wide: 1.5,', src)
        self.assertIn('c.near = camera.near; c.far = camera.far;', src)
        self.assertIn('c.projectionMatrix.elements[0] /= PIN_OCC.wide; c.projectionMatrix.elements[5] /= PIN_OCC.wide;', src)
        self.assertIn('occRender(PIN_OCC.rt, PIN_OCC.w, PIN_OCC.h, PIN_OCC.buf, false, c);', src)
        self.assertIn('PIN_OCC.view.copy(c.matrixWorldInverse); PIN_OCC.proj.copy(c.projectionMatrix);', src)

    def test_wiring(self):
        src = (ROOT / 'app.js').read_text()
        self.assertIn('    pinOccUpdate(dt);\n', src)
        self.assertIn('const PIN_FADE = 0.2, PIN_HOLD = 0.45, PIN_DWELL = 0.3;', src)
        # the pick still refuses a pin that is more than half gone
        self.assertIn('if (v.getX(hit.instanceId) < 0.5) continue;', src)


if __name__ == '__main__':
    unittest.main()
