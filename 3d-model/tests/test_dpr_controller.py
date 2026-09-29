"""Round 166: the resolution controller lowers the ratio only where lowering it buys time.

Mike, from the TestFlight app: "The graphics are looking pretty pixelated. Are we able to spruce those up while maintaining
performance?" Every phone beacon since Sep 25 had ended at the floor (0.72) with frames of 17 to 75 ms at 8 to 10.7 M
triangles: held back by geometry, so every step down cost sharpness and bought nothing. dprJudge makes each step an A-B-A
trial. The DPR literal, the controller and frame()'s hook are cut from app.js and run under Node, frame by frame, against
modelled devices: a frame's ms as a function of the ratio r, the time t and the ms since the last change c, optionally
paced by the display (q: 16.67 at 60 Hz, 33.33 in Low Power Mode) with jitter."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
const isTouch = @@TOUCH@@;
const document = { hidden: false };
const renderer = { getPixelRatio: () => (isTouch ? 1.25 : 1.75) };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
@@LITERAL@@
function applyDPR(r) { DPR.cur = r; }
@@BLOCK@@
function hook(rawMs, now) { const once = false;
@@HOOK@@
}
let seed = @@SEED@@; const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
DPR.live = true;
if (@@START@@) dprGo(@@START@@);
const T = @@SECONDS@@ * 1000, Q = @@Q@@, J = @@JITTER@@, GAPS = @@GAPS@@;
let now = 0, below = 0, total = 0, changes = 0, prev = DPR.cur, lastCh = 0, gi = 0, scale = 1;
const trace = [];
while (now < T) {
  if (gi < GAPS.length && now >= GAPS[gi][0]) { const g = GAPS[gi++]; now += g[1]; scale = g[2]; hook(g[1], now); continue; }
  const r = DPR.cur, t = now, c = now - lastCh;
  const work = Math.max(4, (@@MODEL@@) * scale);
  let ms = Q ? Math.ceil(work / Q - 1e-9) * Q : work;
  ms *= 1 + J * (rnd() * 2 - 1);
  now += ms; total += ms; if (DPR.cur < DPR.cap - 1e-6) below += ms;
  hook(ms, now);
  if (DPR.cur !== prev) { changes++; prev = DPR.cur; lastCh = now; trace.push([Math.round(now), +DPR.cur.toFixed(3)]); }
}
const late = trace.filter((e) => e[0] > 60000).length;
console.log(JSON.stringify({ end: +DPR.cur.toFixed(3), levels: DPR.levels.map((x) => +x.toFixed(3)), below: below / total, changes,
  lateRate: late / Math.max(1e-9, (T - 60000) / 60000), trials: DPR.tri, trace, beacon: dprBeacon() }));
'''


class DprController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = (ROOT / 'app.js').read_text()
        cls.src = src
        i = src.index('  const DPR = { cap: renderer.getPixelRatio()')
        cls.literal = src[i:src.index('\n', i)]
        cls.block = src[src.index('  const DPR_SLOW = '):src.index('  renderer.setSize(window.innerWidth, window.innerHeight);')]
        h = src.index('    if (!once && !DPR.pinned && DPR.live && paceJudge) {')   # Round 168: a paced phone judges only its active frames
        cls.hook = 'const paceJudge = true;\n' + src[h:src.index('    if (introSpin && !interacted)', h)]

    def sim(self, model, seconds=600, touch=True, start=0, q=0, jitter=0.0, gaps=(), seed=7):
        script = HARNESS
        for k, v in {'@@TOUCH@@': 'true' if touch else 'false', '@@LITERAL@@': self.literal, '@@BLOCK@@': self.block, '@@HOOK@@': self.hook,
                     '@@SEED@@': str(seed), '@@START@@': str(start), '@@SECONDS@@': str(seconds), '@@MODEL@@': model,
                     '@@Q@@': str(q), '@@JITTER@@': str(jitter), '@@GAPS@@': json.dumps([list(g) for g in gaps])}.items():
            script = script.replace(k, v)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        return json.loads(r.stdout)

    def test_the_ladder(self):
        self.assertEqual(self.sim('10', seconds=1)['levels'], [1.25, 1.0, 0.8, 0.72])
        self.assertEqual(self.sim('10', seconds=1, touch=False)['levels'], [1.75, 1.488, 1.264, 1.075, 0.9])

    def test_held_back_by_geometry_it_stays_sharp(self):
        # Mike's iPhone: ~29 ms whatever the ratio. The old controller sank to 0.72 and stayed
        for kw in ({}, {'q': 16.667, 'jitter': 0.03}, {'jitter': 0.25}):
            o = self.sim('29', **kw)
            self.assertEqual(o['end'], 1.25, kw)
            self.assertLess(o['below'], 0.03, kw)              # under 3% of ten minutes below the cap
            self.assertEqual(o['trials'][0], 0, kw)             # no step down is ever kept
            self.assertLessEqual(o['trials'][1], 7, kw)         # the holds double: a handful of trials in 10 minutes
            self.assertLessEqual(o['lateRate'], 1.0, kw)        # after the first minute, at most one change a minute

    def test_held_back_by_pixels_it_steps_down(self):
        # the fill is the cost: 42 ms at 1.25, 30 at 1.0, 22.1 at 0.8, 19.4 at 0.72
        o = self.sim('8 + 22 * r * r')
        self.assertLessEqual(o['end'], 0.8)
        self.assertGreater(o['below'], 0.9)
        # paced at 60 Hz the same device draws 50 ms at 1.25 and 33.3 at every rung below: it stops at 1.0, where the gain stops
        o = self.sim('8 + 22 * r * r', q=16.667, jitter=0.03)
        self.assertEqual(o['end'], 1.0)
        self.assertGreater(o['below'], 0.9)

    def test_a_fast_or_comfortable_device_never_moves(self):
        for m, kw in (('6 + 4 * r * r', {}), ('6 + 4 * r * r', {'q': 16.667}), ('14 + 4 * r * r', {}), ('12', {'q': 16.667, 'jitter': 0.03})):
            self.assertEqual(self.sim(m, **kw)['changes'], 0, (m, kw))

    def test_partly_fill_bound_settles_where_the_gain_stops(self):
        # 32.5 ms at 1.25, 28 at 1.0 (14% faster: kept), 25.1 at 0.8 (10%: not worth it)
        o = self.sim('20 + 8 * r * r')
        self.assertEqual(o['end'], 1.0)
        self.assertEqual(o['trials'][2], 0)                    # no step back up is kept: 1.25 costs more than 8%
        self.assertLessEqual(o['changes'], 30)
        self.assertLessEqual(o['lateRate'], 2.5)

    def test_it_climbs_back_from_a_wrong_low(self):
        # started at the floor on a geometry-bound phone: back at the cap within a minute, and it stays
        for kw in ({}, {'q': 16.667, 'jitter': 0.03}):
            o = self.sim('29', seconds=180, start=3, **kw)
            back = next(t for t, r in o['trace'] if r == 1.25)
            self.assertLess(back, 60000, kw)
            self.assertEqual(o['end'], 1.25, kw)
            self.assertLessEqual(sum(1 for t, r in o['trace'] if t > back and r < 1.0), 1, kw)   # at most the one floor probe

    def test_headroom_on_a_60_hz_display_climbs_back(self):
        # a pixel-bound heavy half minute, then a light view: a 60 Hz display never shows a frame under 16.7 ms, so headroom
        # is judged against the display's own interval (the old 13 ms rule left this phone at 0.72 for good)
        o = self.sim('t < 30000 ? 8 + 24 * r * r : 8', seconds=120, q=16.667, jitter=0.03)
        self.assertLess(min(r for t, r in o['trace']), 1.25)   # it did step down in the heavy part
        self.assertEqual(o['end'], 1.25)
        self.assertLess(next(t for t, r in o['trace'] if r == 1.25 and t > 30000), 80000)

    def test_a_gain_only_at_the_floor_is_found(self):
        # paced at 60 Hz, one rung down buys nothing (33.3 ms either way) and the floor halves the frame: the first refusal
        # from the cap tries the floor, keeps it, and the up trials then climb back to the highest rung that holds 60 fps
        o = self.sim('4 + 13 * r * r', q=16.667, jitter=0.03)      # 33.3 ms at 1.25 and 1.0, 16.7 at 0.8 and 0.72
        self.assertEqual(o['end'], 0.8)
        self.assertLessEqual(o['lateRate'], 1.0)
        o = self.sim('3 + 9 * r * r', q=16.667, jitter=0.03, touch=False)   # a desktop: 33.3 down to 1.264, 16.7 below
        self.assertEqual(o['end'], 1.075)

    def test_a_refused_step_waits_for_a_changed_load(self):
        # a geometry-bound phone: after the first refusal (and the floor probe) nothing is retried at the same load until
        # DPR_HOLD_MAX, so there are no trial dips every few minutes
        o = self.sim('29', seconds=300, q=16.667, jitter=0.03)
        self.assertLessEqual(o['trials'][1], 2)
        self.assertLessEqual(o['changes'], 4)

    def test_a_short_spike_is_not_the_device(self):
        self.assertEqual(self.sim('(t % 3000) < 450 ? 40 : 18')['changes'], 0)

    def test_a_drifting_view_does_not_sink_a_geometry_bound_phone(self):
        # the view's cost swings 30% on an 8 s turn: A-B-A keeps the swing from reading as the ratio's doing
        for sd in (7, 11, 23):
            o = self.sim('29 * (1 + 0.3 * Math.sin(t / 1300))', q=16.667, jitter=0.03, seed=sd)
            self.assertLess(o['below'], 0.12, sd)
            self.assertLessEqual(o['lateRate'], 1.0, sd)

    def test_no_hunting_near_the_budget(self):
        # a pixel-bound phone whose view swings 35% over ~45 s at 60 Hz, so the best rung really does change with the view: it
        # may follow the load, but trials are spaced (DPR_GAP) and a reversal holds longer each time, so it does not flip every
        # few seconds (the first design made 5.9 changes a minute here, the reviewers' old-design runs 5.6 to 8.4)
        for sd in (3, 7, 11):
            o = self.sim('(8 + 22 * r * r) * (1 + 0.35 * Math.sin(t / 7000))', q=16.667, jitter=0.05, seed=sd)
            self.assertLessEqual(o['lateRate'], 3.0, (sd, o['lateRate'], o['trials']))
            self.assertGreater(o['below'], 0.8, sd)              # and it does shed resolution: this device needs it

    def test_the_app_in_the_background_mid_trial(self):
        # a trial under way when the app goes to the background for a minute, and the phone comes back cooler: the trial is
        # abandoned, not judged across the gap, and the geometry-bound phone stays at the cap
        o = self.sim('29', gaps=[(1600, 60000, 0.55)], q=16.667, jitter=0.03)
        self.assertEqual(o['end'], 1.25)
        self.assertLess(o['below'], 0.05)

    def test_low_power_mode_stays_sharp(self):
        # iOS's Low Power Mode paces the page at 30 Hz: no rung can buy anything, so it keeps the cap
        o = self.sim('14', q=33.333, jitter=0.02)
        self.assertEqual(o['end'], 1.25)
        self.assertLess(o['below'], 0.05)

    def test_a_load_that_turns_pixel_bound_is_answered(self):
        # geometry-bound for 400 s (the holds have grown), then the fill becomes the cost (night, weather, heat): the
        # hold earned under the lighter load gives way, and it steps down within seconds, not minutes
        o = self.sim('t < 400000 ? 29 : 8 + 30 * r * r', seconds=480)
        first = next(t for t, r in o['trace'] if t > 400000 and r < 1.25)
        self.assertLess(first - 400000, 15000)
        self.assertLessEqual(o['end'], 0.8)

    def test_the_beacon_says_what_happened(self):
        # a geometry-bound phone that makes 60 fps in lighter views (frames of 16.7 and 33.3 ms)
        o = self.sim('(t % 4000) < 1500 ? 14 : 29', seconds=60, q=16.667, jitter=0.03)
        b = o['beacon']
        self.assertEqual(set(b), {'dpt', 'dpm', 'dpl', 'dpv', 'dpf'})
        self.assertRegex(b['dpt'], r'^\d+\.\d+\.\d+\.\d+$')
        self.assertRegex(b['dpf'], r'^125:\d+\.100:\d+\.80:\d+\.72:\d+$')
        self.assertEqual(b['dpl'], '0.72')                    # the lowest ratio tried: the one floor probe, undone
        self.assertGreater(float(b['dpm']), 1.2)              # the time-weighted ratio: nearly all of it at the cap
        self.assertAlmostEqual(float(b['dpv']), 16.7, delta=1.0)   # it found the display's 60 Hz

    def test_wiring(self):
        s = self.src
        self.assertIn('if (!once && !DPR.pinned && DPR.live && paceJudge) {', s)
        self.assertIn('if (rawMs >= 250 || document.hidden) dprGap(now);', s)
        self.assertEqual(s.count('dprJudge(sum / n, DPR.tmp[o + 1], now);'), 1)
        self.assertNotIn('DPR.fast', s)
        self.assertIn('const DPR_CAP = isTouch ? 1.25 : 1.75;', s)          # the cap, and so the load's peak, unchanged
        self.assertIn('min: isTouch ? 0.72 : 0.9', s)
        enter = s[s.index("  btnEnter.addEventListener('click', () => {"):]
        enter = enter[:enter.index('\n  });\n')]
        self.assertLess(enter.index('if (gateGo) { gateGo(); return; }'), enter.index('DPR.live = true;'))
        self.assertIn("beacon('perf', {", enter)
        self.assertIn("beacon('settled', {", enter)                        # 'settled', not 'perf3': st=perf& stays one sample a session
        self.assertEqual(enter.count('...dprBeacon()'), 3)                     # perf, settled and (Round 168) late


if __name__ == '__main__':
    unittest.main()
