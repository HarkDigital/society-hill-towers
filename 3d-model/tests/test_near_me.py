"""Round 135: the near me card. Its distances read in feet under a tenth of a mile, in miles above,
and the location fix opens it."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NearMe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        cls.src = (ROOT / 'app.js').read_text()
        fn = cls.src[cls.src.index('  function nearDist('):]
        fn = fn[:fn.index('\n') + 1]
        run = subprocess.run(['node', '-e', fn + 'console.log(JSON.stringify([nearDist(10), nearDist(107), nearDist(160), nearDist(170), nearDist(1609.34 * 1.26)]));'], capture_output=True, text=True, timeout=20)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.r = json.loads(run.stdout)

    def test_distances(self):
        self.assertEqual(['50 ft', '350 ft', '500 ft', '0.1 mi', '1.3 mi'], self.r)

    def test_the_fix_opens_it(self):
        self.assertIn("placeSearchMark(x, gy, z, 'You are here');\n    nearMeOpen(x, z);", self.src)

    def test_no_em_dash_in_its_strings(self):
        block = self.src[self.src.index('  function nearCardRender('):self.src.index('  function nearGo(')]
        self.assertNotIn('—', block)


if __name__ == '__main__':
    unittest.main()
