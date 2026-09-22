"""Round 134: the libraries and rec centers. The baked file's shape, its bounds and links, and that
no pin point is left inside a drawn footprint of the core."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


class Civic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'civic.json').read_text())

    def test_shape(self):
        self.assertGreaterEqual(len(self.d['lib']), 50)
        self.assertGreaterEqual(len(self.d['rec']), 140)
        for r in self.d['lib']:
            self.assertEqual(7, len(r))
            self.assertTrue(r[2].strip())
            self.assertTrue(r[6] == '' or r[6].startswith('https://'), r[6])
        for r in self.d['rec']:
            self.assertEqual(5, len(r))
            self.assertIn(r[3], (0, 1))
            self.assertIn(r[4], (0, 1))

    def test_in_the_city(self):
        for part in ('lib', 'rec'):
            for r in self.d[part]:
                self.assertTrue(-20000 < r[0] < 16000 and -26000 < r[1] < 16000, (part, r[2]))

    def test_no_pin_inside_a_core_footprint(self):
        from bake_markers import FootGrid
        scene = json.loads((ROOT / 'scene.json').read_text())
        grid = FootGrid([[(p[0], p[1]) for p in b['poly']] for b in scene['buildings'] if len(b.get('poly') or []) >= 3])
        for part in ('lib', 'rec'):
            for r in self.d[part]:
                self.assertIsNone(grid.containing(r[0], r[1]), (part, r[2]))


if __name__ == '__main__':
    unittest.main()
