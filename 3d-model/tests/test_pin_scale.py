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
    def test_the_half_mile_size_all_the_way_in(self):
        # Round 190's coda: a pin's minimum size on the screen is its size at half a mile (NEAR_R 804.67 m), on a computer
        # and a phone alike; the first cut's 0.6 close in was "way too small"
        f = cut(self.s, '  function pinScaleAt(d, cap) {', '\n')
        js = '%s\nconst r = [];\nfor (const d of [0.5, 1, 5, 15, 30, 60, 120, 300, 804.67, 1500, 1890, 3000]) r.push([d, pinScaleAt(d, 14), pinScaleAt(d, 190)]);\nconsole.log(JSON.stringify(r));' % f
        run = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = json.loads(run.stdout)
        half = {cap: dict((d, s) for d, *ss in rows for cap2, s in zip((14, 190), ss) if cap2 == cap)[804.67] / 804.67 for cap in (14, 190)}
        for d, s14, s190 in rows:
            for cap, s in ((14, s14), (190, s190)):
                if d <= cap * 135:
                    self.assertGreaterEqual(s / max(d, 1e-9) + 1e-12, half[cap] * (1 if d >= 1 else 0))   # never smaller on the screen than at half a mile
                    if d >= 1:
                        self.assertAlmostEqual(s / d, half[cap], places=9)                                  # and exactly that size
        self.assertAlmostEqual(dict((d, s) for d, s, _ in rows)[3000], 14)    # the cap still lets the far ones go
        self.assertNotIn('PIN_NEAR_K', self.s)


if __name__ == '__main__':
    unittest.main()
