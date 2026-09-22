"""Round 132: tap a building. The property queries only ever carry two finite numbers, and a
non-finite point asks nothing."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildingCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = (ROOT / 'app.js').read_text()
        cls.src = src
        fn = src[src.index('  function bldgSql('):src.index('  const bldgTitle')]
        title = src[src.index('  const bldgTitle'):src.index('  function bldgQuery(')]
        script = fn + title + r'''
const out = {};
out.parcel = bldgSql('parcel', -75.144606, 39.94456);
out.permits = bldgSql('permits', -75.1446061234, 39.944560987);
out.nan = bldgSql('parcel', NaN, 39.9);
out.inf = bldgSql('district', -75.1, Infinity);
out.injected = bldgSql('parcel', "-75.1); DROP TABLE x; --", 39.9);
out.unknown = bldgSql('owners', -75.1, 39.9);
out.title = bldgTitle('127-29 SPRUCE ST');
console.log(JSON.stringify(out));
'''
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=20)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.r = json.loads(run.stdout)

    def test_point_is_two_fixed_numbers(self):
        self.assertIn('ST_Point(-75.144606,39.944560)', self.r['parcel'])
        self.assertIn('ST_Point(-75.144606,39.944561)', self.r['permits'])

    def test_bad_points_ask_nothing(self):
        for k in ('nan', 'inf', 'injected', 'unknown'):
            self.assertIsNone(self.r[k], k)

    def test_no_owner_or_value_fields(self):
        q = self.r['parcel'].lower()
        for f in ('owner', 'market_value', 'sale_price'):
            self.assertNotIn(f, q)

    def test_title(self):
        self.assertEqual('127-29 Spruce St', self.r['title'])


if __name__ == '__main__':
    unittest.main()
