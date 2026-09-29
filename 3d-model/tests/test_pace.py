"""Round 168: a phone draws at a steady pace and spends the saved time on sharpness.

Mike (iPhone 18 Pro Max, Low Power Mode off): "blurry, pixelated, and had framerate drops". The page drew the whole city at
every display refresh, touched or not, and the phone heated until iOS throttled it (29 ms frames at noon, 68 to 79 ms at night,
paced at 30 Hz). A paced phone now draws at most PACE.fps times a second while anything moves and PACE_IDLE_FPS once still; the
resolution trials judge against the pace (dprPace) and climb a ladder that now runs above the load's 1.25 (GFX_PERF, per
Graphics choice), so the time saved becomes sharpness. The wiring is checked statically; the ladder and a paced climb run under
Node through test_dpr_controller's harness."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

try:
    from test_dpr_controller import HARNESS
except ImportError:   # run as tests.test_pace from 3d-model/
    from tests.test_dpr_controller import HARNESS

ROOT = Path(__file__).resolve().parents[1]


class Pace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_the_choices(self):
        s = self.src
        self.assertIn("touch: { smoother: { fps: 60, top: 1.0, min: 0.72, start: 1.0, far: 9000 }, auto: { fps: 30, top: 1.6, min: 0.72, start: 1.25, far: 0 }, sharper: { fps: 30, top: 2.0, min: 1.0, start: 1.6, far: 0 } },", s)
        self.assertIn('const PACE_IDLE_FPS = 12, PACE_IDLE_AFTER = 2500;', s)
        self.assertIn('const DPR_CAP = isTouch ? 1.25 : 1.75;', s)            # the load's ratio, and so its peak, unchanged
        # the choice changes the pace and the ladder live, through the Graphics strip's hooks
        self.assertIn("if (typeof GFX !== 'undefined' && GFX && GFX.hooks) GFX.hooks.push(() => { paceApply(); dprMode(); });", s)
        self.assertIn('else renderer.setPixelRatio(DPR.cur);   // before Enter', s)

    def test_the_frame_skips_before_it_counts(self):
        f = self.src[self.src.index('  function frame(now, once) {'):]
        f = f[:f.index('\n  }\n')]
        i_skip = f.index('if (now - PACE.lastDraw < 1000 / (paceActive ? PACE.fps : PACE_IDLE_FPS) - 4) return;')
        self.assertLess(f.index('if (!once) requestAnimationFrame(frame);'), i_skip)     # the loop keeps running
        self.assertLess(i_skip, f.index('last = now;'))                                  # a drawn frame's rawMs spans the skipped refreshes
        self.assertLess(i_skip, f.index('frameNo++;'))
        self.assertIn('if (!once && PACE.on && DPR.live) {', f)                          # paced only in the city, never behind the veil
        self.assertIn('const dt = Math.min(rawMs / 1000, PACE.on ? 0.1 : 0.05);', f)
        self.assertIn('const paceJudge = !PACE.on || (paceActive && PACE.prevActive);', f)
        self.assertIn('if (!once && !DPR.pinned && DPR.live && paceJudge) {', f)
        self.assertIn('PACE.moved = now;', f)
        i_render = f.index('if (POST.on) renderPost(scene, camera); else renderer.render(scene, camera);')
        self.assertLess(f.index('const tPre = performance.now();'), i_render)

    def test_the_beacons_carry_the_pace(self):
        s = self.src
        enter = s[s.index("  btnEnter.addEventListener('click', () => {"):]
        enter = enter[:enter.index('\n  });\n')]
        self.assertIn('DPR.live = true; dprMode();', enter)
        self.assertEqual(enter.count('...paceBeacon()'), 3)
        self.assertIn("beacon('late', {", enter)
        self.assertIn('}, 600000);', enter)
        pb = s[s.index('  function paceBeacon() {'):]
        pb = pb[:pb.index('\n  }\n')]
        for k in ('gx:', 'pf:', 'jp:', 'jr:', 'fg:', 'fg95:', 'sk:', 'idl:'):
            self.assertIn(k, pb)

    def test_smoother_pulls_the_haze_in(self):
        self.assertIn("{ const gf = gfxPerf().far; if (gf) { scene.fog.far = Math.min(scene.fog.far, gf); scene.fog.near = Math.min(scene.fog.near, gf * 0.3); } }", self.src)

    def sim(self, prelude, model, q=33.333, seconds=300, seed=5, jitter=0.03):
        src = self.src
        i = src.index('  const DPR = { cap: renderer.getPixelRatio()')
        literal = src[i:src.index('\n', i)]
        block = src[src.index('  const DPR_SLOW = '):src.index('  renderer.setSize(window.innerWidth, window.innerHeight);')]
        h = src.index('    if (!once && !DPR.pinned && DPR.live && paceJudge) {')
        hook = src[h:src.index('    if (introSpin && !interacted)', h)]
        hook = 'const paceJudge = true;\n' + hook
        script = HARNESS.replace('DPR.live = true;', 'DPR.live = true;\n' + prelude)
        for k, v in {'@@TOUCH@@': 'true', '@@LITERAL@@': literal, '@@BLOCK@@': block, '@@HOOK@@': hook, '@@SEED@@': str(seed), '@@START@@': '0',
                     '@@SECONDS@@': str(seconds), '@@MODEL@@': model, '@@Q@@': str(q), '@@JITTER@@': str(jitter), '@@GAPS@@': '[]'}.items():
            script = script.replace(k, v)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return json.loads(r.stdout)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_the_ladder_passes_through_the_start(self):
        o = self.sim('DPR.top = 1.6; dprInit();', '20', seconds=1)
        self.assertEqual(o['levels'], [1.6, 1.25, 1.0, 0.8, 0.72])                   # Auto on a 3x phone: one rung above the load's 1.25
        o = self.sim('DPR.cur = 1.6; DPR.top = 2.0; DPR.min = 1.0; dprInit();', '20', seconds=1)
        self.assertEqual(o['levels'], [2.0, 1.6, 1.28, 1.0])                         # Sharper after Enter

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_a_paced_phone_climbs_while_it_holds_the_pace(self):
        # paced at 30 (frames land on 33.3 ms when the work fits): 24 ms of work at 1.25 and 30 at 1.6 both hold the pace, so the
        # trials climb to 1.6 and stay; the old fixed 22 ms budget would have read every paced frame as slow and sunk it
        o = self.sim('DPR.top = 1.6; dprInit(); DPR.live = true; dprPace(30);', '12 + 7 * r * r')
        self.assertEqual(o['end'], 1.6)
        self.assertLessEqual(o['lateRate'], 1.0)
        # 1.6 costs 37 ms, a missed pace: it tries, is undone, and stays at 1.25
        o = self.sim('DPR.top = 1.6; dprInit(); DPR.live = true; dprPace(30);', '16 + 8 * r * r')
        self.assertEqual(o['end'], 1.25)
        self.assertGreaterEqual(o['trials'][3], 1)
        # a night that misses the pace at 1.25 (41 ms) and holds it at 1.0 (29 ms): it steps down
        o = self.sim('DPR.top = 1.6; dprInit(); DPR.live = true; dprPace(30);', '9 + 20 * r * r')
        self.assertLessEqual(o['end'], 1.0)


class MikesTwoCalls(unittest.TestCase):
    """Round 168, Mike's answers: "Turn them off" (moon shadows after dusk) and "Only buildings hide pins"."""
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_moon_shadows_off_on_a_phone(self):
        self.assertIn("if (isTouch) { const cast = el > -3; if (sun.castShadow !== cast) { sun.castShadow = cast; if (cast) renderer.shadowMap.needsUpdate = true; } }", self.src)
        # the same line where the key light becomes the moon's: el > -3 is the sun's branch of applyLighting
        self.assertIn("    if (el > -3) {\n      sunDir.copy(sp.dir);", self.src)

    def test_only_buildings_hide_pins(self):
        s = self.src
        self.assertEqual(s.count('occRender(PIN_OCC.rt, PIN_OCC.w, PIN_OCC.h, PIN_OCC.buf, true, c,'), 2)   # both the async and the synchronous read
        self.assertNotIn('occRender(PIN_OCC.rt, PIN_OCC.w, PIN_OCC.h, PIN_OCC.buf, false', s)


if __name__ == '__main__':
    unittest.main()
