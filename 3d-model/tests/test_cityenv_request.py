"""Round 229: a request that lands between the city probe's two cubes is kept.

The glass mirrors the city through CITYENV (Round 192): a computer bakes two cubes, Center City's on the frame refreshEnv
asks and University City's on the frame after, so no frame carries both. The first bake ends with nothing asked; the
second ended the same way, and so cleared a request that refreshEnv had raised on its own frame, just ahead of it. Center
City's cube then kept the light of the frame before, and the scale between bakes is capped at 1, so a cube baked at night
stayed a night city under a day sky until something asked again (the sun's next three degrees, the next weather, the
skyline theme settling).

MEASURED (Nov 10, headless Chrome on the Mac's GPU, the entry orbit by day, loaded after dark): with one frame drawn at
night and the day clock set before the second, the towers of Center City mirror a night city: 6.34% of the pixels over
24 levels from the same pose with no frame drawn first. That is every capture after dark from the round that lights
Enter by the first frame (its fallback timer draws that frame before a tool can set a clock), and the page before that
round does the same once a frame is forced first (6.3426% against 6.3421%). With the clock pinned from the first frame,
or with two frames drawn before the clock is set, the difference is 0.002%.

What must hold, run under Node on the tick cut from app.js, against a bake that keeps the real bake's last two lines:
- a request raised between the two cubes is still asked after the second: both cubes end under the new light;
- the second cube is still baked on the frame after the first, and no cube twice within CITYENV_GAP;
- with no such request nothing more is baked (the kept flag is the request's, never the bake's own);
- a phone's single cube is untouched;
- the tick as it was written before fails the first of these (the control: this file would have caught it)."""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


def cut(a, b, text=SRC):
    i = text.index(a)
    return text[i:text.index(b, i + len(a))]


TICK = cut('  function cityEnvTick() {', '\n  }\n') + '\n  }\n'
BAKE = cut('  function cityEnvBake(only) {', '\n  }\n')
# the bake's own bookkeeping, as written: what it leaves asked and which cube is next
TAIL = ['    if (only !== 1) CITYENV.lumAt = cityEnvLum();',
        '    CITYENV.u.uCityEnvK.value = 1;',
        '    CITYENV.renders++; CITYENV.msLast = performance.now() - t0; CITYENV.ms += CITYENV.msLast; CITYENV.at = performance.now();',
        '    CITYENV.pending = false; CITYENV.next = only === 0 && CITYENV.centres.length > 1 ? 1 : -1;']
OLD_LINE = '    if (CITYENV.next === 1) { CITYENV.next = -1; cityEnvBake(1); }'
NEW_LINE = '    if (CITYENV.next === 1) { const asked = CITYENV.pending; CITYENV.next = -1; cityEnvBake(1); CITYENV.pending = asked; }'

HARNESS = r'''
let NOW = 5000, LIGHT = 'night';
const LUM = { night: 0.0151, day: 0.4197 };
const performance = { now: () => NOW };
const cityEnvLum = () => LUM[LIGHT];
const CITYENV_GAP = __GAP__;
const CITYENV = { built: true, pending: true, next: -1, at: 0, lumAt: 0, renders: 0, ms: 0, msLast: 0, centres: __CENTRES__, u: { uCityEnvK: { value: 1 } } };
const held = [null, null], log = [];
function cityEnvBake(only) {
  const t0 = performance.now();
  CITYENV.centres.forEach((c, k) => { if (only != null && k !== only) return; held[k] = LIGHT; log.push([k, LIGHT, NOW]); });
__TAIL__
}
__TICK__
// a frame: applyLighting (refreshEnv asks when the light is new), then the tick, as frame() has them
let lit = null;
const frame = (ms) => { NOW += ms; if (lit !== LIGHT) { lit = LIGHT; CITYENV.pending = true; } cityEnvTick(); };
const state = () => ({ held: held.slice(), pending: CITYENV.pending, next: CITYENV.next, renders: CITYENV.renders, k: CITYENV.u.uCityEnvK.value, log: log.slice() });
__RUN__
'''


def run(script, tick=TICK, centres=2):
    js = (HARNESS.replace('__GAP__', re.search(r'const CITYENV_GAP = (\d+);', SRC).group(1)).replace('__CENTRES__', json.dumps([{}] * centres))
          .replace('__TAIL__', '\n'.join(TAIL)).replace('__TICK__', tick).replace('__RUN__', script))
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


# the first frame at night (the fallback that lights Enter, or any frame before a clock is set), the day clock, then frames
NIGHT_THEN_DAY = r'''
frame(16);                                   // the first frame: Center City's cube, at night
const a = state();
LIGHT = 'day';                               // the clock is set between the frames
frame(16);                                   // refreshEnv asks, then the second cube's turn
const b = state();
for (let i = 0; i < 40; i++) frame(16);      // 640 ms on: past the gap
console.log(JSON.stringify({ a, b, c: state() }));
'''


class TheRequestBetweenTheCubes(unittest.TestCase):
    def test_the_text(self):
        for ln in TAIL:
            self.assertIn(ln, BAKE, 'the harness keeps the bake\'s own bookkeeping: follow it if it changes')
        self.assertIn(NEW_LINE, TICK)
        self.assertNotIn(OLD_LINE, SRC)
        self.assertEqual(TICK.count('cityEnvBake(1)'), 1)
        self.assertIn('else if (CITYENV.pending && performance.now() - CITYENV.at >= CITYENV_GAP) cityEnvBake(0);', TICK)
        # the bake is the glass calibration's fingerprint and stays as it was: the request is kept by the tick
        self.assertNotIn('asked', BAKE)
        # refreshEnv only asks, and the frame runs the tick right behind the lighting that calls it
        self.assertIn('if (cityEnvReady) CITYENV.pending = true;', cut('  function refreshEnv() {', '\n  }\n'))
        self.assertIn('    applyLighting();\n    if (CITYENV.built) cityEnvTick();', cut('  function frame(now, once) {', '\n  }\n'))

    def test_a_request_between_the_cubes_is_kept(self):
        r = run(NIGHT_THEN_DAY)
        self.assertEqual(r['a']['held'], ['night', None])
        self.assertEqual((r['a']['pending'], r['a']['next']), (False, 1))
        # the second cube on its own frame, under the new light, and the request still standing
        self.assertEqual(r['b']['held'], ['night', 'day'])
        self.assertEqual((r['b']['pending'], r['b']['next'], r['b']['renders']), (True, -1, 2))
        # after the gap both cubes hold the day, and nothing is left asked
        self.assertEqual(r['c']['held'], ['day', 'day'])
        self.assertEqual((r['c']['pending'], r['c']['next'], r['c']['renders']), (False, -1, 4))
        self.assertEqual([k for k, _, _ in r['c']['log']], [0, 1, 0, 1])
        self.assertEqual(r['c']['k'], 1)

    def test_never_two_bakes_of_a_cube_within_the_gap(self):
        r = run(NIGHT_THEN_DAY)
        log = r['c']['log']
        gap = int(re.search(r'const CITYENV_GAP = (\d+);', SRC).group(1))
        self.assertGreaterEqual(log[2][2] - log[1][2], gap, 'the kept request waits the gap out from the second cube')
        self.assertEqual(log[1][2] - log[0][2], 16, 'the second cube is the frame after the first')
        self.assertEqual(log[3][2] - log[2][2], 16)

    def test_between_bakes_the_scale_follows_the_sky(self):
        # day first, night asked between the cubes: until the kept request bakes, the old day cube is scaled down to the night
        r = run(r'''
LIGHT = 'day'; frame(16); LIGHT = 'night'; frame(16); frame(16);
const mid = state();
for (let i = 0; i < 40; i++) frame(16);
console.log(JSON.stringify({ mid, end: state() }));
''')
        self.assertEqual(r['mid']['held'], ['day', 'night'])
        self.assertTrue(r['mid']['pending'])
        self.assertAlmostEqual(r['mid']['k'], 0.0151 / 0.4197, places=6)
        self.assertEqual(r['end']['held'], ['night', 'night'])
        self.assertEqual(r['end']['k'], 1)

    def test_no_request_no_more_bakes(self):
        r = run(r'''
for (let i = 0; i < 80; i++) frame(16);
console.log(JSON.stringify(state()));
''')
        self.assertEqual((r['renders'], r['pending'], r['next']), (2, False, -1))
        self.assertEqual(r['held'], ['night', 'night'])

    def test_a_request_after_both_cubes_is_as_before(self):
        r = run(r'''
frame(16); frame(16);
LIGHT = 'day';
for (let i = 0; i < 40; i++) frame(16);
console.log(JSON.stringify(state()));
''')
        self.assertEqual((r['renders'], r['pending'], r['next']), (4, False, -1))
        self.assertEqual(r['held'], ['day', 'day'])

    def test_a_phone_has_one_cube(self):
        r = run(NIGHT_THEN_DAY, centres=1)
        self.assertEqual(r['a']['next'], -1)
        self.assertEqual(r['c']['held'], ['day', None])
        self.assertEqual((r['c']['renders'], r['c']['pending']), (2, False))

    def test_the_tick_as_it_was_loses_it(self):
        """The control: the line before this round, in the same harness, leaves Center City at night under a day sky."""
        self.assertIn(NEW_LINE, TICK)
        r = run(NIGHT_THEN_DAY, tick=TICK.replace(NEW_LINE, OLD_LINE))
        self.assertEqual(r['c']['held'], ['night', 'day'])
        self.assertEqual((r['c']['renders'], r['c']['pending']), (2, False))
        self.assertEqual(r['c']['k'], 1, 'and the scale between bakes cannot lift a night cube: it is capped at 1')


if __name__ == '__main__':
    unittest.main()
