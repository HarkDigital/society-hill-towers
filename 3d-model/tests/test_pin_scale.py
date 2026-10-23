"""Round 190 (Mike, with a screenshot of a historical marker's pin filling half the view from the sidewalk: "Pins need to
scale down in size as you get closer to them"). Every pin took distance / 135 held at 2.2 at least, so from 300 m in a pin
stood at its full 10 by 12.6 m and grew on the screen as the eye came on. pinScaleAt keeps the far size on the screen to
300 m and eases down from there to a fraction of it close in; every pin goes through it.

Round 221 (Mike: "The pins need to be 2x as large on mobile. They get too small when near them now"): a phone (isTouch) draws
every pin at PIN_TOUCH_K, twice the computer's size, at every distance, with the caps' knees where they were."""
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
        self.assertEqual(len(re.findall(r'pinScaleAt\(camera\.position\.distanceTo\(_\w+\), (?:14|190)\)', s)), 9)
        # Round 202: the ships' anchors and the ferry measure their distance first (their pins show within a mile)
        self.assertIn('const aps = pinScaleAt(sd, 190) * pinRise(v, now);', s)
        self.assertIn('const aps = pinScaleAt(fd, 190) * pinRise(p, now);', s)

    def scale_rows(self, touch):
        # the constant and the rule as the page declares them, run under node for a computer (isTouch false) or a phone
        k = cut(self.s, '  const PIN_TOUCH_K = ', '\n')
        f = cut(self.s, '  function pinScaleAt(d, cap) {', '\n')
        js = 'const isTouch = %s;\n%s\n%s\nconst r = [];\nfor (const d of [0.5, 1, 5, 15, 30, 60, 120, 300, 804.67, 1500, 1890, 3000, 25650, 40000]) r.push([d, pinScaleAt(d, 14), pinScaleAt(d, 190)]);\nconsole.log(JSON.stringify(r));' % ('true' if touch else 'false', k, f)
        run = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    @unittest.skipUnless(shutil.which('node'), 'node unavailable')
    def test_the_half_mile_size_all_the_way_in(self):
        # Round 190's coda: a pin's minimum size on the screen is its size at half a mile (NEAR_R 804.67 m), on a computer
        # and a phone alike; the first cut's 0.6 close in was "way too small"
        for touch in (False, True):
            with self.subTest(touch=touch):
                self.half_mile_rule(self.scale_rows(touch), 2 if touch else 1)

    def half_mile_rule(self, rows, k):
        half = {cap: dict((d, s) for d, *ss in rows for cap2, s in zip((14, 190), ss) if cap2 == cap)[804.67] / 804.67 for cap in (14, 190)}
        for d, s14, s190 in rows:
            for cap, s in ((14, s14), (190, s190)):
                if d <= cap * 135:
                    self.assertGreaterEqual(s / max(d, 1e-9) + 1e-12, half[cap] * (1 if d >= 1 else 0))   # never smaller on the screen than at half a mile
                    if d >= 1:
                        self.assertAlmostEqual(s / d, half[cap], places=9)                                  # and exactly that size
        self.assertAlmostEqual(dict((d, s) for d, s, _ in rows)[3000], 14 * k)    # the cap still lets the far ones go
        self.assertAlmostEqual(dict((d, s) for d, _, s in rows)[40000], 190 * k)
        self.assertNotIn('PIN_NEAR_K', self.s)

    @unittest.skipUnless(shutil.which('node'), 'node unavailable')
    def test_a_phone_draws_every_pin_twice_the_size(self):
        # Round 221: the phone's pin is exactly twice the computer's at every distance, under both caps, the knees unmoved
        # (a factor inside the min would move the 14 cap's knee from 1,890 m to 3,780 m and leave the far pins one size)
        self.assertIn('const PIN_TOUCH_K = isTouch ? 2 : 1;', self.s)
        self.assertIn('function pinScaleAt(d, cap) { return PIN_TOUCH_K * Math.min(Math.max(d, 1) / 135, cap); }', self.s)
        desk, phone = self.scale_rows(False), self.scale_rows(True)
        for (d, a14, a190), (d2, b14, b190) in zip(desk, phone):
            self.assertEqual(d, d2)
            self.assertAlmostEqual(b14, 2 * a14, places=9)
            self.assertAlmostEqual(b190, 2 * a190, places=9)
        # the factor is applied once, in pinScaleAt: no caller scales a pin by the device again
        for line in self.s.splitlines():
            if 'pinScaleAt(' in line and 'function pinScaleAt' not in line:
                self.assertNotIn('isTouch', line)
                self.assertNotIn('PIN_TOUCH_K', line)

    def test_the_bigger_pin_keeps_its_tip(self):
        # Round 221: a doubled pin still stands on its anchor and is still judged at it. Every badge is a plane lifted
        # wholly above its instance's origin (scaling grows it upward from the tip), and the anchor depth (Round 126), the
        # gate (Round 169) and the pick's tip (pinTipOf) all read the instance's origin, never a corner of the badge
        s = self.s
        badges = re.findall(r'new THREE\.PlaneGeometry\(([\d.]+), ([\d.]+)\)\.translate\(0, ([\d.]+), 0\)', s)
        self.assertEqual(len(badges), 6)   # pinMesh, the SEPTA, Indego, aircraft, ship anchor and Amtrak badges
        for w, h, ty in badges:
            self.assertGreaterEqual(float(ty) - float(h) / 2, 0, (w, h, ty))
        self.assertIn('vec4 pinA = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);', s)
        self.assertIn('vec4 w = modelMatrix * instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);', s)
        self.assertIn('return _ptv.setFromMatrixPosition(_ptm).applyMatrix4(mesh.matrixWorld).toArray();', s)


if __name__ == '__main__':
    unittest.main()
