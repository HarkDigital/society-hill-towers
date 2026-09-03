"""towers.json (bake_towers.py): the Center City tower specs the app joins to the
packed buildings by position. Every record carries the keys the app reads, sits
inside the wide box, is tower-height, and names a facade archetype and crown type
from the sets the app knows. Skips when the bake has not run."""
import math
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_towers
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

FILE = 'towers.json'
KEYS = ('name', 'x', 'z', 'h', 'r', 'hex', 'glass', 'facade', 'crown', 'lit', 'podium', 'matched')
FACADES = {'glass', 'glass_bands', 'glass_dark', 'concrete_grid', 'stone_piers', 'deco', 'precast_bands', 'brick'}
CROWNS = {'flat', 'notch', 'pyramid', 'stepped', 'custom', 'spire', 'lattice', 'ziggurat', 'lantern',
          'sloped', 'mansard', 'dome'}
MIN_RECORDS = 40
H_RANGE = (45.0, 400.0)


def is_hex(s):
    return isinstance(s, str) and len(s) == 7 and s[0] == '#' and all(c in '0123456789abcdefABCDEF' for c in s[1:])


class Towers(unittest.TestCase):
    def setUp(self):
        C.require(self, FILE)
        data = C.load_json(FILE)
        self.assertIn('src', data)
        self.assertIsInstance(data.get('towers'), list)
        self.towers = data['towers']

    def test_enough_records(self):
        self.assertGreaterEqual(len(self.towers), MIN_RECORDS)

    def test_record_shape(self):
        x0, x1, z0, z1 = C.WIDE_BOX
        seen = set()
        for t in self.towers:
            with self.subTest(name=t.get('name')):
                for k in KEYS:
                    self.assertIn(k, t)
                self.assertIsInstance(t['name'], str)
                self.assertTrue(t['name'].strip())
                self.assertNotIn(t['name'], seen, 'duplicate record name')
                seen.add(t['name'])
                self.assertTrue(x0 <= t['x'] <= x1 and z0 <= t['z'] <= z1, 'outside the wide box: %r' % ((t['x'], t['z']),))
                self.assertTrue(H_RANGE[0] <= t['h'] <= H_RANGE[1], 'h %r out of range' % t['h'])
                self.assertGreater(t['r'], 0)
                self.assertTrue(t['hex'] is None or is_hex(t['hex']), 'bad hex %r' % t['hex'])
                self.assertIsInstance(t['glass'], bool)
                self.assertIn(t['facade'], FACADES)
                crown = t['crown']
                self.assertIsInstance(crown, dict)
                self.assertIn(crown.get('type'), CROWNS)
                if 'h' in crown:
                    self.assertGreater(crown['h'], 0)
                    self.assertLess(crown['h'], t['h'])
                if crown['type'] == 'ziggurat':
                    self.assertGreaterEqual(crown.get('steps', 0), 2)
                self.assertTrue(t['lit'] is None or is_hex(t['lit']), 'bad lit %r' % t['lit'])
                self.assertIsInstance(t['podium'], int)
                self.assertTrue(0 <= t['podium'] < t['h'])
                self.assertIsInstance(t['matched'], bool)

    def test_records_do_not_pile_up(self):
        """two records inside one join radius would fight over a footprint"""
        pts = [(t['name'], t['x'], t['z'], t['r']) for t in self.towers]
        for i, (n1, x1, z1, r1) in enumerate(pts):
            for n2, x2, z2, r2 in pts[i + 1:]:
                d = math.hypot(x1 - x2, z1 - z2)
                self.assertGreater(d, 0.5 * min(r1, r2), '%s and %s are %.0f m apart' % (n1, n2, d))

    def test_mostly_matched(self):
        matched = sum(1 for t in self.towers if t['matched'])
        self.assertGreaterEqual(matched, 0.8 * len(self.towers), 'too many records missed their footprint')


if __name__ == '__main__':
    unittest.main()
