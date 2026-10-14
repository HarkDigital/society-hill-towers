"""Round 192's review, the glass towers' day colour (must-fix 2: "too dark, too grey, and the blue is lost"): each
researched tower's glass, measured by glass_calibrate.py over its own glass at the standard noon poses, lies within its
stated CIE76 delta E of its reference swatch, and the measure was taken on the glass the page draws now: its shaders' and
systems' fingerprint matches, so a change to the glass that is not re-measured (python3 glass_calibrate.py after a build)
fails here.

Round 192's second review: Comcast a hundred metres off its south face at noon keeps its swatch and its frames do not stand
out of its glass (the 90th over the 10th percentile of the face's luminance under CONTRAST's bound), and One Liberty's crown
(REGION) reads as the tower's blue glass, not a white lattice.

Round 192's third review: every researched glass tower with a reference colour (27), at the poses where it stands in the
open (JUDGE: 400 pixels of its own glass, two fifths of its height, the eye no more than 20 m over its top), measured by its
own code (no neighbour's glass), its b* within HUE_B of the swatch's as well (delta E alone let a blue tower pass as grey):
over its judged poses each tower's median within both bounds, the towers still open (OPEN) held at their recorded gaps; no
judged measure another colour entirely; Comcast and the CTC within both bounds at mid-level and on a shaded face at every
pose the review named."""
import importlib.util
import json
from pathlib import Path
import statistics
import unittest

ROOT = Path(__file__).resolve().parents[1]


def calibrator():
    spec = importlib.util.spec_from_file_location('glass_calibrate', ROOT / 'glass_calibrate.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Calibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = calibrator()
        cls.C = json.loads((ROOT / 'tests' / 'glass_calibration.json').read_text())

    def test_measured_on_the_glass_drawn_now(self):
        self.assertEqual(self.G.fingerprint(), self.C['fingerprint'], 'the glass changed since it was calibrated: python3 build.py && python3 glass_calibrate.py')

    def test_every_researched_glass_tower_with_a_colour(self):
        self.assertEqual(set(self.C['swatches']), set(self.G.SWATCHES), 'the swatches are glass_calibrate.py\'s')
        self.assertGreaterEqual(len(self.G.SW), 27)
        sysd = json.loads((ROOT / 'glass_systems.json').read_text())['towers']
        towers = {t['name']: t for t in json.loads((ROOT / 'towers.json').read_text())['towers']}
        for name, hexc in self.G.SW.items():
            self.assertIn(name, towers, name)
            self.assertIn(name, sysd, name)
        for name, v in sysd.items():
            if v.get('body') and name not in ('3025 JFK Boulevard',) and name in towers and towers[name].get('h', 0) >= 100:
                self.assertIn(name, self.G.SW, 'a researched glass tower with a colour and no swatch: ' + name)

    def test_the_judged_poses(self):
        J = json.loads((ROOT / 'tests' / 'glass_calibration_poses.json').read_text())
        towers = {t['name']: t for t in json.loads((ROOT / 'towers.json').read_text())['towers']}
        for name, (hexc, poses, tol) in self.G.SWATCHES.items():
            self.assertLessEqual(tol, 15, name)
            got = self.C['measured'].get(name, {})
            if name in self.G.REGION:
                continue
            self.assertEqual(poses, J.get(name, poses), name)
            if not poses:
                self.assertIn(name, self.G.OPEN, '%s is judged at no pose' % name)
                continue
            for pose in poses:
                self.assertIn(pose, got, '%s was not measured at %s' % (name, pose))
                m = got[pose]
                self.assertGreaterEqual(m['px'], self.G.JUDGE[0] * 0.75, (name, pose))
                self.assertLessEqual(self.G.POSES[pose]['pos'][1], towers[name]['h'] + self.G.JUDGE[2], (name, pose))   # never from over its top

    def test_every_tower_keeps_its_colour(self):
        hb = self.G.HUE_B
        self.assertLessEqual(hb, 6.0)
        for name, (hexc, poses, tol) in self.G.SWATCHES.items():
            got = self.C['measured'].get(name, {})
            if not got:
                continue
            for pose, m in got.items():
                de = self.G.delta_e(m['mean'], self.G.hex_rgb(hexc))
                self.assertAlmostEqual(de, m['dE'], delta=0.11)
                self.assertAlmostEqual(self.G.lab(m['mean'])[2] - self.G.lab(self.G.hex_rgb(hexc))[2], m['db'], delta=0.11)
                if name not in self.G.OPEN:
                    self.assertLessEqual(de, 35, '%s at %s is another colour: %s against %s' % (name, pose, m['mean'], hexc))
            mde = statistics.median(m['dE'] for m in got.values())
            mdb = statistics.median(m['db'] for m in got.values())
            if name in self.G.OPEN:
                o = self.G.OPEN[name]
                self.assertLessEqual(mde, o[0] + 0.5, '%s: median delta E %.1f past its recorded open gap %.1f' % (name, mde, o[0]))
                self.assertLessEqual(abs(mdb), abs(o[1]) + 0.5, '%s: median b* gap %.1f past its recorded %.1f' % (name, mdb, o[1]))
                continue
            self.assertLessEqual(mde, tol, '%s: median delta E %.1f over its poses %s' % (name, mde, list(got)))
            self.assertLessEqual(abs(mdb), hb, '%s: median b* gap %.1f over its poses %s' % (name, mdb, list(got)))

    def test_the_open_towers_are_few_and_said(self):
        self.assertLessEqual(len(self.G.OPEN), 8)
        for name, (mde, mdb, why) in self.G.OPEN.items():
            self.assertIn(name, self.G.SW)
            self.assertGreater(len(why), 40, name)
        self.assertEqual(self.C['open'], {k: list(v) for k, v in self.G.OPEN.items()})

    def test_comcast_and_the_ctc_at_mid_level_and_in_shade(self):
        for name, poses in self.G.NAMED.items():
            self.assertNotIn(name, self.G.OPEN)
            for pose in poses:
                self.assertIn(pose, self.G.SWATCHES[name][1], '%s is no longer judged at %s' % (name, pose))
                m = self.C['measured'][name][pose]
                self.assertLessEqual(m['dE'], 15, (name, pose, m['mean']))
                self.assertLessEqual(abs(m['db']), self.G.HUE_B, (name, pose, m['mean']))
        self.assertIn('ctc-mid', self.G.NAMED['Comcast Technology Center'])
        self.assertIn('market-north', self.G.NAMED['Comcast Technology Center'])
        self.assertIn('comcast-north-150', self.G.NAMED['Comcast Center'])

    def test_the_liberty_places_read_blue_and_comcast_is_not_dark(self):
        # the review's two named failures: One Liberty a neutral grey (B - R 14) and Comcast a dark slab (69, 79, 86)
        M = self.C['measured']
        for pose, m in M['One Liberty Place'].items():
            self.assertGreater(m['mean'][2] - m['mean'][0], 20, pose)
        for pose, m in M['Comcast Center'].items():
            self.assertGreater(sum(m['mean']) / 3, 105, pose)

    def test_the_frames_do_not_stand_out_of_the_glass(self):
        self.assertTrue(self.G.CONTRAST, 'a pose bounds the frames against the glass')
        self.assertEqual(self.C['contrast'], [{'tower': k[0], 'pose': k[1], 'max': v} for k, v in self.G.CONTRAST.items()])
        for (name, pose), mx in self.G.CONTRAST.items():
            self.assertLessEqual(mx, 2.0, (name, pose))
            self.assertIn(pose, self.G.SWATCHES[name][1], (name, pose))
            m = self.C['measured'][name][pose]
            self.assertLessEqual(m['contrast'], mx, '%s at %s: p90 %.1f over p10 %.1f' % (name, pose, m['p90'], m['p10']))

    def test_the_liberty_crown_is_measured_as_part_of_its_tower(self):
        name = 'One Liberty Place (crown)'
        self.assertIn(name, self.G.SWATCHES)
        tower, y0, y1 = self.G.REGION[name]
        self.assertEqual(tower, 'One Liberty Place')
        self.assertLess(y0, 212 + 15)   # the lowest tier's eaves, over the tower's ground
        self.assertGreater(y1, 251)     # the top tier's ridge
        m = self.C['measured'][name]
        for pose in self.G.SWATCHES[name][1]:
            self.assertGreaterEqual(m[pose]['px'], 100, pose)
            self.assertGreater(m[pose]['mean'][2] - m[pose]['mean'][0], 20, pose)   # blue, not the white lattice over tan
            self.assertLessEqual(m[pose]['dE'], 15, pose)

    def test_delta_e_is_cie76(self):
        self.assertAlmostEqual(self.G.delta_e([255, 255, 255], [255, 255, 255]), 0.0, places=6)
        self.assertAlmostEqual(self.G.delta_e([0, 0, 0], [255, 255, 255]), 100.0, delta=0.05)
        L = self.G.lab([128, 128, 128])
        self.assertAlmostEqual(L[0], 53.59, delta=0.05)

    def test_a_tower_code_survives_the_tone_curve(self):
        # the code a tower's glass is drawn in (views 7 and 8) is its body's bytes hashed: two of the review's neighbours
        # (PNC beside Two Liberty) differ
        T = {t['name']: t for t in json.loads((ROOT / 'towers.json').read_text())['towers']}
        a = self.G.tower_code('PNC Bank Building (1600 Market)', T['PNC Bank Building (1600 Market)'])
        b = self.G.tower_code('Two Liberty Place', T['Two Liberty Place'])
        self.assertNotEqual(a, b)
        for c in (a, b):
            self.assertTrue(0 <= c[0] < 8 and 0 <= c[1] < 8)
        import numpy as np
        I = np.array([[[200, 20, 30], [10, 10, 10], [190, 200, 210]]], float)
        self.assertEqual(self.G.code_of(I).tolist(), [[1, 0, 7]])


if __name__ == '__main__':
    unittest.main()
