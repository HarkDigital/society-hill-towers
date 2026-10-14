"""Round 192's review, the glass towers' day colour (must-fix 2: "too dark, too grey, and the blue is lost"): each
researched tower's glass, measured by glass_calibrate.py over the glass mask at the standard noon poses, lies within its
stated CIE76 delta E of its reference swatch (Comcast a light silver blue, the CTC a pale neutral, the Liberty Places a mid
blue, Cira a bright silver, The Laurel a greige), and the measure was taken on the glass the page draws now: its shaders'
and systems' fingerprint matches, so a change to the glass that is not re-measured (python3 glass_calibrate.py after a
build) fails here.

Round 192's second review: Comcast a hundred metres off its south face at noon keeps its swatch and its frames do not stand
out of its glass (the 90th over the 10th percentile of the face's luminance under CONTRAST's bound: the first cut's white
joints measured 3.3), and One Liberty's crown (REGION) reads as the tower's blue glass, not a white lattice."""
import importlib.util
import json
from pathlib import Path
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

    def test_every_tower_within_its_swatch(self):
        sw = self.C['swatches']
        self.assertEqual(set(sw), set(self.G.SWATCHES), 'the swatches are glass_calibrate.py\'s')
        for name, (hexc, poses, tol) in self.G.SWATCHES.items():
            self.assertLessEqual(tol, 15, name)
            got = self.C['measured'].get(name, {})
            for pose in poses:
                self.assertIn(pose, got, '%s was not measured at %s' % (name, pose))
                m = got[pose]
                self.assertGreaterEqual(m['px'], 100, (name, pose))   # a hundred pixels of the tower's own glass at least (Comcast stands mostly behind 1818 Market from the south-west)
                de = self.G.delta_e(m['mean'], self.G.hex_rgb(hexc))
                self.assertAlmostEqual(de, m['dE'], delta=0.11)
                self.assertLessEqual(de, tol, '%s at %s: %s against %s, delta E %.1f' % (name, pose, m['mean'], hexc, de))

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
            self.assertGreater(m[pose]['mean'][2] - m[pose]['mean'][0], 20, pose)   # blue, not the white lattice over tan

    def test_delta_e_is_cie76(self):
        self.assertAlmostEqual(self.G.delta_e([255, 255, 255], [255, 255, 255]), 0.0, places=6)
        self.assertAlmostEqual(self.G.delta_e([0, 0, 0], [255, 255, 255]), 100.0, delta=0.05)
        L = self.G.lab([128, 128, 128])
        self.assertAlmostEqual(L[0], 53.59, delta=0.05)


if __name__ == '__main__':
    unittest.main()
