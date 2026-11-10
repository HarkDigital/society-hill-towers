"""Round 226 (Stage 1 of the Nov 10 plan): Enter lights only when a tap can be answered.

The button used to light as build() ended, with the first frame still to draw. That frame uploads the last of the
geometry and compiles whatever the flushes never drew, and while it runs the page answers nothing: on a cold device it
froze for 8.5 to 9.1 s (Apple) and 29 s (a Windows PC) under a button that already read Explore the City. Now the Ready
line, the button and the bar's last step are set at the end of the first drawn frame (enterLight, called by frame), and
a page that gets no animation frame (a hidden tab, the Browser pane, the capture skill's render.mjs, which holds
requestAnimationFrame and waits for this button) draws that frame itself from a timer ENTER_WAIT ms after the build and
then lights the button (enterArm).

What must hold:
- build() no longer touches the button, its text, the Ready line or the bar's 100; the ready beacon stays in build();
- the first frame's end lights it, after the render, once;
- with no animation frame the timer draws one frame through the once path and lights it, within about a second and a
  half; with a frame already drawn the timer does nothing; a frame that throws, or a lost context, still lights it;
- the words are the old words (the veil's wording is the owner's);
- the recovery gate's own use of the button is untouched.

The block is cut from app.js and run under Node."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


def cut(a, b, text=SRC):
    i = text.index(a)
    return text[i:text.index(b, i + len(a))]


ENTER = cut('  const ENTER = { lit: false, fail: 0 };', '\n  // Round 220 (the measurement round): the first frames')
SET_MSG = cut('  function setLoadingMessage(message) {', '\n  }\n') + '\n  }\n'


def node(script):
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


HARNESS = r'''
const PERF = { t0: 1000 }, timers = [], errs = [];
const performance = { now: () => 43210.4 };
const setTimeout = (fn, ms) => { timers.push({ fn, ms }); return timers.length; };
console.error = (...a) => errs.push(a.map(String).join(' '));
const loadmsg = { textContent: 'Opening the Libraries and Rec Centers', classes: [], classList: { add: (c) => loadmsg.classes.push(c) } };
const btnEnter = { disabled: true, textContent: 'Preparing' };
const bar = { value: 99.2 };
const document = { getElementById: (id) => (id === 'loadProgress' ? bar : null) };
SET_MSG
let frames = [], frameThrows = false, glDead = false;
function frame(now, once) { frames.push([typeof now === 'number', once === true]); if (glDead) return; if (frameThrows) throw new Error('boom'); if (!ENTER.lit) enterLight(); }
ENTER
const state = () => ({ lit: ENTER.lit, disabled: btnEnter.disabled, text: btnEnter.textContent, line: loadmsg.textContent, done: loadmsg.classes.join(','), bar: bar.value, frames: frames.length, by: PERF.enterBy || '' });
const out = {};
'''


def harness(body):
    h = HARNESS.replace('SET_MSG', SET_MSG)
    i = h.rindex('\nENTER\n')
    return node(h[:i] + '\n' + ENTER + '\n' + h[i + len('\nENTER\n'):] + body + '\nconsole.log(JSON.stringify(out));')


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Lighting(unittest.TestCase):
    def test_an_animation_frame_lights_it_and_the_timer_then_does_nothing(self):
        r = harness(r'''
out.before = state();
enterArm();                       // the block after build(): beside requestAnimationFrame(frame)
out.armed = { timers: timers.length, ms: timers[0].ms, id: PERF.enterTimer, lit: ENTER.lit };
frame(16.7);                      // the first animation frame runs first (the timer waits behind its task)
out.afterFrame = state();
timers[0].fn();                   // the timer, late
out.afterTimer = state(); out.litAt = PERF.lit;
''')
        self.assertEqual(r['before'], {'lit': False, 'disabled': True, 'text': 'Preparing', 'line': 'Opening the Libraries and Rec Centers', 'done': '', 'bar': 99.2, 'frames': 0, 'by': ''})
        self.assertEqual(r['armed'], {'timers': 1, 'ms': 1500, 'id': 1, 'lit': False})
        lit = {'lit': True, 'disabled': False, 'text': 'Explore the City', 'line': 'Ready', 'done': 'done', 'bar': 100, 'frames': 1, 'by': ''}
        self.assertEqual(r['afterFrame'], lit)
        self.assertEqual(r['afterTimer'], lit, 'the timer finds the button lit: no second frame, nothing set twice')
        self.assertEqual(r['litAt'], 42210)   # on PERF.ready's clock (ms since PERF.t0)

    def test_no_animation_frame_the_timer_draws_one_and_lights_it(self):
        r = harness(r'''
enterArm();
out.waiting = state();            // a hidden tab, the pane, render.mjs: nothing has drawn
timers[0].fn();
out.after = state(); out.frameArgs = frames[0];
''')
        self.assertFalse(r['waiting']['lit'])
        self.assertTrue(r['waiting']['disabled'])
        self.assertEqual(r['after'], {'lit': True, 'disabled': False, 'text': 'Explore the City', 'line': 'Ready', 'done': 'done', 'bar': 100, 'frames': 1, 'by': 'timer'})
        self.assertEqual(r['frameArgs'], [True, True], 'the once path: a time, and no new animation frame asked for')

    def test_a_frame_that_throws_or_a_lost_context_still_lights_it(self):
        r = harness(r'''
frameThrows = true; enterArm(); timers[0].fn(); out.thrown = state(); out.errs = errs.length;
''')
        self.assertEqual((r['thrown']['lit'], r['thrown']['disabled'], r['thrown']['text'], r['thrown']['frames'], r['errs']), (True, False, 'Explore the City', 1, 1))
        r = harness(r'''
glDead = true; enterArm(); timers[0].fn(); out.dead = state();
''')
        self.assertEqual((r['dead']['lit'], r['dead']['disabled'], r['dead']['frames']), (True, False, 1))

    def test_the_failed_steps_line_and_only_once(self):
        r = harness(r'''
ENTER.fail = 2; enterLight(); out.a = state();
btnEnter.textContent = 'x'; loadmsg.textContent = 'y'; enterLight(); out.b = [btnEnter.textContent, loadmsg.textContent];
''')
        self.assertEqual(r['a']['line'], 'Ready (Some Detail Could Not Be Built)')   # setLoadingMessage's title case, as before
        self.assertEqual(r['b'], ['x', 'y'])

    def test_the_wait_is_about_a_second_and_a_half(self):
        self.assertIn('  const ENTER_WAIT = 1500;\n', ENTER)
        self.assertIn('    }, ENTER_WAIT);\n', ENTER)


class Wiring(unittest.TestCase):
    def test_build_no_longer_lights_the_button(self):
        b = cut('  async function build() {', '\n  }\n')
        for gone in ('btnEnter', 'Explore the City', "'Ready'", "loadmsg.classList.add('done')", "getElementById('loadProgress').value = 100"):
            self.assertNotIn(gone, b, gone)
        self.assertIn("    beacon('ready', { ms: PERF.ready, fail: failures, sf: SF.state });", b)   # the ready beacon stays at the build's end
        self.assertIn('    ENTER.fail = failures;', b)
        self.assertLess(b.index("beacon('ready'"), b.index('ENTER.fail = failures;'))

    def test_the_words_are_the_old_words(self):
        f = cut('  function enterLight() {', '\n  }\n')
        for line in ("    setLoadingMessage(ENTER.fail ? 'Ready (some detail could not be built)' : 'Ready');", "    loadmsg.classList.add('done');",
                     '    btnEnter.disabled = false;', "    btnEnter.textContent = 'Explore the City';", "    document.getElementById('loadProgress').value = 100;"):
            self.assertIn(line, f)
        self.assertEqual(SRC.count("'Explore the City'"), 1)
        for s in ("'Ready (some detail could not be built)'", "'Explore the City'"):
            self.assertNotRegex(s, '[—·]')

    def test_the_first_frames_end_lights_it(self):
        f = cut('  function frame(now, once) {', '\n  setHint();')
        self.assertEqual(f.count('enterLight()'), 1)
        self.assertLess(f.index('if (POST.on) renderPost(scene, camera); else renderer.render(scene, camera);'), f.index('if (!ENTER.lit) enterLight();'))
        self.assertLess(f.index('PERF.frame1Ms = Math.round(performance.now() - tFrame);'), f.index('if (!ENTER.lit) enterLight();'))
        self.assertTrue(f.rstrip().endswith('}'))
        self.assertEqual(f.rstrip().splitlines()[-2].split('   //')[0], '    if (!ENTER.lit) enterLight();', 'the last thing the frame does')

    def test_the_fallback_is_armed_beside_the_first_animation_frame(self):
        tail = SRC[SRC.index('  build().then(() => {'):]
        self.assertEqual(SRC.count('enterArm();'), 1)
        self.assertIn('    requestAnimationFrame(frame);\n    enterArm();', tail)
        arm = cut('  function enterArm() {', '\n  }\n')
        self.assertIn('      if (ENTER.lit) return;', arm)
        self.assertIn('      try { frame(performance.now(), true); } catch (e) {', arm)
        self.assertLess(arm.index('frame(performance.now(), true)'), arm.index('      enterLight();'))
        # nothing here renders by itself: the frame does (tests/test_cull.py: nothing renders between build's end and the first frame)
        self.assertNotIn('renderer.render(', ENTER)

    def test_the_recovery_gate_keeps_its_own_use_of_the_button(self):
        g = cut('  function bootGate() {', '\n  async function build() {')
        self.assertIn("    btnEnter.textContent = 'Load the City';\n    btnEnter.disabled = false;", g)
        self.assertIn('        btnEnter.disabled = true;', g)
        click = cut("  btnEnter.addEventListener('click', () => {\n    btnEnter.blur();", '\n  });\n')
        self.assertIn('    if (gateGo) { gateGo(); return; }', click)

    def test_the_bail_beacon_still_reads_the_builds_own_ready(self):
        # hidden before Ready is judged by PERF.ready (set in build()), never by the button, which now lights a frame later
        self.assertIn("if (document.hidden && !PERF.ready && lm) beacon('bail', { step: lm.textContent.slice(0, 40) });", SRC)


if __name__ == '__main__':
    unittest.main()
