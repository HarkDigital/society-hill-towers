"""Round 190 (Mike, with a screenshot of a historical marker's pin filling half the view from the sidewalk: "Pins need to
scale down in size as you get closer to them"). Every pin took distance / 135 held at 2.2 at least, so from 300 m in a pin
stood at its full 10 by 12.6 m and grew on the screen as the eye came on. pinScaleAt keeps the far size on the screen to
300 m and eases down from there to a fraction of it close in; every pin goes through it."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class PinScale(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_every_pin_takes_the_rule(self):
        s = self.s
        self.assertNotIn('/ 135, 2.2', s)
        self.assertEqual(len(re.findall(r'pinScaleAt\(camera\.position\.distanceTo\(_\w+\), (?:14|190)\)', s)), 11)

    @unittest.skipUnless(shutil.which('node'), 'node unavailable')
    def test_the_screen_size_falls_as_the_eye_comes_on(self):
        f = cut(self.s, '  const PIN_NEAR_K = ', '  function pinSweep(now) {')
        out = {}
        for touch in (False, True):
            js = 'const isTouch = %s;\n%s\nconst r = [];\nfor (const d of [5, 15, 30, 60, 120, 200, 299, 300, 301, 600, 1800, 3000]) r.push([d, pinScaleAt(d, 14), pinScaleAt(d, 14) / d]);\nconsole.log(JSON.stringify(r));' % ('true' if touch else 'false', f)
            run = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            out[touch] = json.loads(run.stdout)
        for touch, rows in out.items():
            ang = {d: a for d, s, a in rows}
            far = 1 / 135
            self.assertAlmostEqual(ang[600] / far, 1, places=6)                      # far: the old constant size on the screen
            self.assertAlmostEqual(ang[300] / far, 1, places=6)                      # the knee meets it with no jump
            k = 0.75 if touch else 0.6
            self.assertAlmostEqual(ang[15] / far, k, places=6)                       # close in: a fraction of it
            self.assertAlmostEqual(ang[30] / far, k, places=6)
            seq = [ang[d] for d in (30, 60, 120, 200, 299, 300)]
            self.assertEqual(seq, sorted(seq))                                       # never larger closer in
            self.assertAlmostEqual(dict((d, s) for d, s, a in rows)[3000], 14)      # the cap stands
            # the old rule at 20 m: 2.2 / 20 against 1 / 135 is about fifteen times the far size; now under one
            self.assertLess(ang[15] / far, 1)


if __name__ == '__main__':
    unittest.main()
