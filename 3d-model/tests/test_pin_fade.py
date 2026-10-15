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
  screen; a still eye keeps the old cadence; a pin waiting for an image asks for one
Round 202 (Mike: "they should show regardless unless the user is very close, 0.1 miles. At close range buildings should hide
them"): a tip past PIN_OCC_NEAR is shown at once whatever the images say, and an image is drawn only while a tip in view
stands within PIN_OCC_PREP; so the phone's near images between complete ones (for a far tip) are never drawn now
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
let frameNo = 0, moving = true, LAT = 1, covers = true, dirty = false, step2 = 1;   // dirty: the eye has moved since the last image, by step2 (squared)
const isTouch = TOUCH, PIN_NEAR = 900, PIN_JUMP = 300, PIN_COVER = 1.25, PIN_OCC_NEAR = 160.93, PIN_OCC_PREP = 300;
let truth = () => 1, zone = () => true;
const mkCh = () => ({ slots: [], gate: -1, cpu: { ok: false, frame: -1e9 }, last: -1e9 });
const PIN_OCC = { ok: false, every: isTouch ? 10 : 5, moveEvery: isTouch ? 2 : 1, fullEvery: isTouch ? 10 : 1, far: 30000, want: -99, close: -99, hid: 0, wait: -1e9, waitFar: false, waitTip: -1e9, waitTipFar: false,
  lastFrame: -1e9, fresh: false, reach: 0, reachTip: 0, near: mkCh(), full: mkCh(), cause: { first: 0, old: 0, jump: 0, cadence: 0, cover: 0, wait: 0, reach: 0, full: 0, near: 0 },
  lastPos: { copy() { dirty = false; } }, lastQuat: { copy() {} }, pvPos: { copy() {} }, pvQuat: { copy() {} } };
const PIN_ASYNC = { eye: {} };
const camera = { position: { x: 0, y: 0, z: 0, distanceToSquared: (o) => (o === PIN_OCC.lastPos ? (moving || dirty ? step2 : 0) : moving ? 1 : 0) }, quaternion: { dot: () => 1 }, updateMatrixWorld() {}, projectionMatrix: {}, matrixWorldInverse: {} };
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
const step = (dt = 1 / 60) => { frameNo++; if (moving) dirty = true; poll(); pinOccUpdate(dt); };
const run = (n, dt = 1 / 60) => { const out = []; for (let i = 0; i < n; i++) { step(dt); out.push(vis()); } return out; };
BODY
'''.replace('TOUCH', 'true' if touch else 'false').replace('BLOCK', self.block).replace('BODY', body)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_hidden_until_an_image_drawn_after_its_arrival_says_clear(self):
        # the pin is out of view, then comes into view at frame 21: the image the CPU holds then is older, so the pin waits for one
        # drawn after its arrival, shows on the frame that image lands, and rises over PIN_FADE. Round 202: a second pin, in view
        # and within PIN_OCC_PREP throughout, keeps an image standing (with nothing near in view none is drawn)
        out = self.run_js('''
m.count = 2; m.instanceMatrix.array[16 + 12] = 50;
zone = (x) => x === 50 || frameNo > 20; moving = false;
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
moving = false; run(2); const r0 = renders.length;   // the stop's own image (review) comes first
truth = (x, f) => (x > 5 ? 0 : 1);
m.instanceMatrix.array[12] = 10; const hide = run(3);
m.instanceMatrix.array[12] = 0; const back = run(60);
console.log(JSON.stringify({ hide, at: back.findIndex((v) => v > 0), images: renders.length - r0 }));''')
        self.assertEqual(out['hide'], [0, 0, 0])
        self.assertEqual(out['images'], 0)
        self.assertGreaterEqual(out['at'], 26)                       # 0.45 s at 60 fps
        self.assertLessEqual(out['at'], 29)

    def test_a_new_pin_in_a_slot_arrives(self):
        # the slot now holds a pin 100 m away (the set reshuffled), and a pin new to slot 1: both wait for an image drawn after them
        out = self.run_js('''
moving = false; run(30);
m.instanceMatrix.array[12] = 100; m.count = 2; m.instanceMatrix.array[16 + 12] = 150;
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
run(1); renders.length = 0; moving = false; run(100); const still = renders.length;   // 41 frames: the last one drew an image
covers = false; moving = true; renders.length = 0; run(6); const cov = renders.map(([f]) => f);
console.log(JSON.stringify({ gaps: mv.slice(1).map((f, i) => f - mv[i]), still, cov }));''')
        self.assertTrue(out['gaps'] and all(g == 2 for g in out['gaps']), out['gaps'])   # every 2nd drawn frame on a phone while moving
        self.assertEqual(out['still'], 0)                             # a still eye that has not changed draws none
        cov = out['cov']
        self.assertEqual([b - a for a, b in zip(cov, cov[1:])], [1] * (len(cov) - 1))   # the newest no longer holds the screen: every frame

    def test_an_image_the_frame_the_eye_stops(self):
        # review: a phone draws an image every 2nd frame while the eye moves, so the eye stops on a frame that drew none as often
        # as not, and the gate then read the image of a step before until the still cadence came round (10 frames): a pin fading
        # in showed through a building's edge for up to 0.3 s. Now the first still frame draws the pose the eye rests at, once
        out = self.run_js('''
const stop = (n) => { moving = true; run(n); const last = renders.length && renders[renders.length - 1][0] === frameNo; renders.length = 0; moving = false; run(30); return { last, still: renders.map(([f]) => f - frameNo + 30) }; };
const a = stop(40), b = stop(41);
step2 = 0.16 * 0.16; const c = stop(40), e = stop(41);   // a slow flight's last step, 16 cm: under the old 30 cm, it stood through the hold
console.log(JSON.stringify({ a, b, c, e }));''')
        runs = [out['a'], out['b']]
        self.assertEqual([out['c'], out['e']], runs)
        self.assertEqual(sorted(r['last'] for r in runs), [False, True])   # one stop on a frame with an image, one without
        for r in runs:
            if r['last']:
                self.assertEqual(r['still'], [])                          # the image already holds the pose it rests at
            else:
                self.assertEqual(r['still'], [1])                         # the first still frame, and only that one

    def test_a_pin_that_changes_slots_keeps_its_state(self):
        # review: the half-mile reconcile writes the slots afresh in a new order, and a vehicle or a flight that goes shifts every
        # later one down a slot: a pin that only changed slots keeps its own state (no blink out and fade back), whatever order;
        # a pin that was nowhere near still arrives
        out = self.run_js('''
moving = true; m.count = 3; const e = m.instanceMatrix.array;
e[12] = 0; e[16 + 12] = 50; e[32 + 12] = 100;   // all within the near line (Round 202)
run(40); const before = [vis(0), vis(1), vis(2)];
e[12] = 100; e[16 + 12] = 0; e[32 + 12] = 50; step(); const shuffled = [vis(0), vis(1), vis(2)];
for (let i = 0; i < 3; i++) e[i * 16 + 12] += 12; step(); const moved = [vis(0), vis(1), vis(2)];   // moving pins, not new
e[12] = e[16 + 12]; e[16 + 12] = e[32 + 12] + 12; m.count = 2; step(); const shifted = [vis(0), vis(1)];   // the first went: a shift down
m.count = 3; e[32 + 12] = 150; step(); const arrived = vis(2);
console.log(JSON.stringify({ before, shuffled, moved, shifted, arrived }));''')
        self.assertEqual(out['before'], [1, 1, 1])
        self.assertEqual(out['shuffled'], [1, 1, 1])
        self.assertEqual(out['moved'], [1, 1, 1])
        self.assertEqual(out['shifted'], [1, 1])
        self.assertEqual(out['arrived'], 0)

    def test_cadence_on_a_computer(self):
        out = self.run_js('''
moving = true; run(30); const f = renders.filter(([q]) => q > 5);
console.log(JSON.stringify({ gaps: f.slice(1).map((q, i) => q[0] - f[i][0]), kinds: [...new Set(f.map((q) => q[1]))] }));''', touch=False)
        self.assertTrue(all(g == 1 for g in out['gaps']))
        self.assertEqual(out['kinds'], ['full'])

    def test_a_far_pin_shows_at_once_whatever_the_images_say(self):
        # Round 202: a tip past the near line (161 m) is shown the frame it comes into view, at full, though every image says
        # covered, and no image is drawn for it (nothing in view stands within PIN_OCC_PREP); a layer's far pins the same
        out = self.run_js('''
truth = () => 0;
zone = () => frameNo > 5;
m.count = 3; const e = m.instanceMatrix.array; e[12] = 400; e[16 + 12] = 5000; e[32 + 12] = 170;
const a = []; for (let i = 0; i < 40; i++) { step(); a.push([vis(0), vis(1), vis(2)]); }
const near = renders.length;   // the tip at 170 m stands within PIN_OCC_PREP: the images come for it
m.count = 2; renders.length = 0; run(20);
console.log(JSON.stringify({ before: a[4], first: a[5], all: a.slice(5).every((q) => q.every((v) => v === 1)), near, renders: renders.length, reach: PIN_OCC.reach }));''')
        self.assertEqual(out['before'], [0, 0, 0])          # out of view
        self.assertEqual(out['first'], [1, 1, 1])           # in view: at once, no wait for an image, no fade
        self.assertTrue(out['all'])
        self.assertGreater(out['near'], 0)
        self.assertEqual(out['renders'], 0)                 # 400 m and 5 km alone: no image
        self.assertEqual(out['reach'], 0)

    def test_crossing_the_near_line(self):
        # Round 202: a pin behind a building (every image says covered) walks in from 400 m, 10 m a frame: it shows past the
        # near line, the images start once it stands within PIN_OCC_PREP so they already hold it when it crosses, and it is
        # hidden the frame it crosses; walking back out it eases in over PIN_FADE past the line, and the images stop
        out = self.run_js('''
truth = () => 0;
const e = m.instanceMatrix.array, rows = [];
for (let x = 400; x >= 100; x -= 10) { e[12] = x; const r0 = renders.length; step(); rows.push([x, vis(), renders.length - r0]); }
for (let x = 110; x <= 400; x += 10) { e[12] = x; const r0 = renders.length; step(); rows.push([x, vis(), renders.length - r0]); }
renders.length = 0; run(10);
console.log(JSON.stringify({ rows, after: renders.length }));''')
        rows = out['rows']
        inward = rows[:31]
        self.assertTrue(all(v == 1 for x, v, _ in inward if x > 160.93))
        self.assertTrue(all(v == 0 for x, v, _ in inward if x <= 160))       # hidden at the first frame inside
        first_img = next(x for x, _, r in inward if r)
        self.assertLessEqual(first_img, 300)
        self.assertGreater(first_img, 200)                                     # drawn ahead of the line
        self.assertEqual([r for x, _, r in inward if x > 300], [0] * len([1 for x, _, r in inward if x > 300]))
        outward = rows[31:]
        past = [v for x, v, _ in outward if x > 160.93]
        self.assertEqual(past, sorted(past))
        self.assertTrue(any(0 < v < 1 for v in past))                          # an ease, not a snap
        self.assertEqual(past[-1], 1)
        self.assertEqual(out['after'], 0)                                      # nothing within the prep line: no images

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
        # the pick still refuses a pin that is more than half gone, and one the gate hides (review)
        self.assertIn('if (v.getX(hit.instanceId) < 0.5 || !pinGateShows(...pinTipOf(hit.object, hit.instanceId))) continue;', SRC)
        # and the things a tap finds without a gate ask the same images whether a building covers them (review)
        self.assertIn('      if (pinGateCovers(tx, ty, tz)) return true;   // Round 169 (review)', SRC)
        # Round 202: past the images' reach the building tap's one-pixel render answers, once a tap
        self.assertIn('q = bldgPointAt(cx, cy, PIN_OCC.far * 0.99);', SRC)
        self.assertIn('return tapT < L - 3;', SRC)
        # Round 202: the near line in the gate, the judge and the placards; the placards' roof-grid line of sight is gone
        self.assertIn('const PIN_OCC_NEAR = 160.93;', SRC)
        self.assertIn('const PIN_OCC_PREP = 300;', SRC)
        self.assertIn('if (dot(ve, ve) > uPinOccReach.w * uPinOccReach.w) return 1.0;', SRC)
        self.assertIn('G.reach.value.set(aNew ? a.reach : 0, b ? b.reach : 0, aNew ? 1 : 0, PIN_OCC_NEAR);', SRC)
        blocked = SRC[SRC.index('  function pinBlocked('):SRC.index('  const PIN_FADE = ')]
        self.assertIn('if (d < PIN_OCC_PREP) PIN_OCC.want = frameNo;', blocked)
        self.assertNotIn('losClear', blocked)
        # and the search destination's name has no line of sight either
        self.assertNotIn('!losClear(searchMark', SRC)
        # the still eye's image the frame it stops (review), never after `every` frames
        self.assertIn('if (moving ? since >= PIN_OCC.moveEvery : off) { C.cadence++; due = 1; }', SRC)
        # and by the moving test's own centimetre: a slow flight's last step (16 cm) under the old 30 cm stood through a hold
        self.assertIn('const off = changed || camera.position.distanceToSquared(PIN_OCC.lastPos) > 1e-4 || 1 - Math.abs(camera.quaternion.dot(PIN_OCC.lastQuat)) > 1e-9;', SRC)
        # Round 143's wide image through its own camera, now with a reach
        self.assertIn('w: Math.round((isTouch ? 160 : 256) * 1.5), wide: 1.5,', SRC)
        self.assertIn("e[10] = -(f + n) / (f - n); e[14] = -2 * f * n / (f - n);", SRC)


if __name__ == '__main__':
    unittest.main()
