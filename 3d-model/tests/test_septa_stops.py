"""Round 133: the transit stops. The baked file's shape and bounds, and the layer link's
seventeen-bit form with every older form still decoding."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def pip(x, z, poly):
    ins = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]; xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            ins = not ins
        j = i
    return ins


class StopsBake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'septa_stops.json').read_text())
        cls.bound = json.loads((ROOT / 'city_limit.json').read_text())['bound']

    def test_shape(self):
        b, r = self.d['bus'], self.d['rail']
        self.assertGreater(len(b['id']), 6000)
        self.assertGreater(len(r['id']), 40)
        for k in ('id', 'x', 'z', 'n', 'r'):
            self.assertEqual(len(b['id']), len(b[k]), k)
        for k in ('id', 'x', 'z', 'n'):
            self.assertEqual(len(r['id']), len(r[k]), k)

    def test_inside_the_flight_limit(self):
        for part in ('bus', 'rail'):
            p = self.d[part]
            for i in range(0, len(p['id']), 37):
                self.assertTrue(pip(p['x'][i] / 2, p['z'][i] / 2, self.bound), (part, p['id'][i]))

    def test_names_clean(self):
        for n in self.d['bus']['n']:
            self.assertTrue(n.strip())
            self.assertNotRegex(n, r'-\s*(FS|NS|MBFS|MBNS)$')
            self.assertNotIn('</script', n.lower())
        self.assertTrue(all(self.d['bus']['r']), 'every stop has a route')

    def test_station_names_are_the_boards(self):
        raw = ROOT / 'lidar_cache' / 'septa_raw' / 'station_id_name.csv'
        if not raw.exists():
            self.skipTest('station list not fetched')
        names = {r[1].strip() for r in csv.reader(raw.open()) if r and r[0].strip().isdigit()}
        for n in self.d['rail']['n']:
            self.assertIn(n, names)
        for want in ('30th Street Station', 'Suburban Station', 'Market East'):
            self.assertIn(want, self.d['rail']['n'])
        self.assertIn('Jefferson Station', self.d['rail']['d'])
        self.assertEqual(len(self.d['rail']['n']), len(self.d['rail']['d']))


class LayerLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = (ROOT / 'app.js').read_text()
        keys = src[src.index('  const LAYER_KEYS'):src.index('  const CIVIC = { on: false };')]
        mask = src[src.index('  function layersFromMask('):]
        mask = mask[:mask.index('\n') + 1]
        script = keys + mask + r'''
const out = {};
const all = {}; LAYER_KEYS.forEach((k, i) => { all[k] = i % 2 === 0; });
let m = LAYER_MASK_V5; LAYER_KEYS.forEach((k, i) => { if (all[k]) m |= 1 << i; });
out.v5 = JSON.stringify(layersFromMask(m)) === JSON.stringify(all);
out.v4 = Object.keys(layersFromMask(LAYER_MASK_V4 | 1 | 8192)).length;
out.v4art = layersFromMask(LAYER_MASK_V4 | 8192).art;
out.v4stops = 'stops' in layersFromMask(LAYER_MASK_V4 | 8192);
out.v3 = Object.keys(layersFromMask(LAYER_MASK_V3 | 1)).length;
out.max = m <= 262143;
out.n = LAYER_KEYS.length;
console.log(JSON.stringify(out));
'''
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=20)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.r = json.loads(run.stdout)

    def test_round_trip_and_old_links(self):
        self.assertTrue(self.r['v5'])
        self.assertEqual(17, self.r['n'])
        self.assertEqual(14, self.r['v4'])
        self.assertTrue(self.r['v4art'])
        self.assertFalse(self.r['v4stops'], "a fourteen-bit link's marker is not the stops layer")
        self.assertEqual(12, self.r['v3'])
        self.assertTrue(self.r['max'], 'parseHash keeps 262143')


if __name__ == '__main__':
    unittest.main()
