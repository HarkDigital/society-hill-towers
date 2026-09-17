"""rail_amtrak.json (Round 80), the track the live Amtrak trains ride: every line at least
two finite points inside the far-ring box, the flags booleans, 30 to 600 track kilometres
(every track of the corridor is its own line), and the nearest line within 120 m of 30th
Street Station, North Philadelphia and Overbrook; and app.js still carries the snap grid and
the upsert that read it. Skips when the bake's output is absent."""
import math
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_rail
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

STATIONS = {'30th Street Station': (-3171, -1122), 'North Philadelphia': (-875, -5753), 'Overbrook': (-8960, -4850)}


class Rail(unittest.TestCase):
    def setUp(self):
        C.require(self, 'rail_amtrak.json')
        self.d = C.load_json('rail_amtrak.json')

    def test_schema_and_reach(self):
        lines = self.d['lines']
        self.assertGreater(len(lines), 20)
        km = 0.0
        x0, x1, z0, z1 = C.CITY_BOX
        for l in lines:
            p = l['p']
            self.assertGreaterEqual(len(p), 2)
            self.assertIn(l['t'], (0, 1))
            self.assertIn(l['b'], (0, 1))
            for x, z in p:
                self.assertTrue(math.isfinite(x) and math.isfinite(z))
                self.assertTrue(x0 <= x <= x1 and z0 <= z <= z1, 'a point outside the far-ring box: %r' % ((x, z),))
            for i in range(1, len(p)):
                km += math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) / 1000
        self.assertTrue(30 <= km <= 600, 'track km: %.1f' % km)
        for name, (sx, sz) in STATIONS.items():
            best = min(C.seg_dist(sx, sz, p[i - 1][0], p[i - 1][1], p[i][0], p[i][1]) for l in lines for p in [l['p']] for i in range(1, len(p)))
            self.assertLess(best, 120, '%s is %.0f m from the nearest track' % (name, best))

    def test_app_reads_it(self):
        C.require(self, 'app.js')
        src = C.path('app.js').read_text(encoding='utf-8')
        for needle in ('RAIL_AMTRAK', 'function railSnap(', 'function railWalk(', 'function amtrakUpsert(', "step('Laying the Northeast Corridor'"):
            self.assertIn(needle, src, needle + ' is gone from app.js')


if __name__ == '__main__':
    unittest.main()
