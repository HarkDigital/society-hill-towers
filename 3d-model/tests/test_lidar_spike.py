"""Round 160: the Reading Terminal's 125 m slab, and every confirmed LiDAR spike like it.

The City footprint over the Reading Terminal headhouse reads max_hgt 125.07 m over approx_hgt 44.5 m, a ratio of 2.81
that the 3x contamination guard let through, and the pre-LiDAR snapshot had inherited the same 125.1 from an earlier
in-place join, so the tall protection defended it: the headhouse outline and its two-storey link to the train shed
(OSM way 335512395, building:levels 2) stood 125 m tall. lidar_join.py now CONFIRMS a spike against the point cloud (a
flat LiDAR roof covering half the footprint, far under the max, with approx_hgt agreeing with that roof), a confirmed
spike contributes approx_hgt, places of worship keep the max (their spike is the steeple), and the protection no longer
defends a snapshot tall that is exactly the spike. These checks read the packed tier, the join's report and its source."""
import json
import re
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_lidar_spike
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests


def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


class LidarSpikeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = C.path('lidar_join.py').read_text()
        cls.report = json.loads(C.path('lidar_report.json').read_text())
        cls.scene = C.walk_scene('wide.b64')

    def test_the_link_is_no_longer_125_m(self):
        # the link's packed record (centroid about (-1235, -760), 82 by 13 m); the rtm rebuild draws the real one
        hits = [b for b in self.scene['buildings'] if abs(centroid(b[4])[0] + 1235) < 6 and abs(centroid(b[4])[1] + 760) < 6]
        self.assertEqual(len(hits), 1, [(centroid(b[4]), b[1]) for b in hits])
        self.assertLess(hits[0][1], 60.0)

    def test_nothing_on_the_headhouse_block_stands_at_the_spike(self):
        # the headhouse's own footprint (x -1281 to -1195, z -760 to -715) and the link behind it; Jefferson Tower just
        # east of it (x -1190 on) really stands 125 to 143 m, so it is left out
        for b in self.scene['buildings']:
            cx, cz = centroid(b[4])
            if -1285 < cx < -1195 and -775 < cz < -710:
                self.assertFalse(120 < b[1] < 130, (round(cx), round(cz), b[1]))

    def test_the_report_names_the_released_spikes(self):
        self.assertGreater(self.report.get('confirmed_spikes', 0), 0)
        rel = self.report.get('spike_released', [])
        link = [r for r in rel if abs(r[2] + 1248) < 3 and abs(r[3] + 762) < 3]
        self.assertEqual(len(link), 1, rel)
        self.assertAlmostEqual(link[0][4], 125.1, places=1)
        self.assertLess(link[0][5], 60.0)
        for tag, name, cx, cz, old, new in rel:
            self.assertGreater(old, 30.0)          # only a defended tall is ever released
            self.assertLess(new, old)

    def test_places_of_worship_keep_their_max(self):
        # a steeple is indistinguishable from a spike, so every measure of a worship record reads max_hgt
        self.assertIn("WORSHIP_T = 'worship'", self.src)
        self.assertRegex(self.src, r"measure\(poly, b\.get\('holes'\), use_max=worship\)")
        self.assertRegex(self.src, r"use_max=b\.get\('t'\) == WORSHIP_T")
        self.assertRegex(self.src, r"use_max=t\.get\('amenity'\) == 'place_of_worship'")
        scene = json.loads(C.path('scene_wide.json').read_text())['buildings']
        names = {b.get('name') for b in scene if b.get('t') == 'worship'}
        for r in self.report.get('spike_released', []):
            self.assertNotIn(r[1], names - {None}, r)

    def test_a_spike_needs_both_witnesses(self):
        body = re.search(r'def spike_check\(.*?\n(?=\n\S)', self.src, re.S).group(0)
        for need in ('SPIKE_RATIO * a', 'SPIKE_ROOF_K * p90 + SPIKE_ROOF_M', 'abs(a - p90) <= SPIKE_AGREE * p90', 'SPIKE_COVER * pg.area'):
            self.assertIn(need, body)


if __name__ == '__main__':
    unittest.main()
