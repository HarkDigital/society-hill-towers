"""Round 131: weather alerts. The heat and cold word lists that stand in for Code Red and Code Blue,
and the alert clock in Philadelphia time."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Alerts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = (ROOT / 'app.js').read_text()
        cls.src = src
        block = src[src.index('  const ALERT_HEAT'):src.index('  function alertKind(')]
        script = block + r'''
const out = {};
out.heat = ['Heat Advisory', 'Excessive Heat Warning', 'Extreme Heat Watch'].map((e) => ALERT_HEAT.test(e));
out.cold = ['Cold Weather Advisory', 'Extreme Cold Warning', 'Wind Chill Advisory', 'Freeze Warning'].map((e) => ALERT_COLD.test(e));
out.neither = ['Flood Watch', 'Severe Thunderstorm Warning', 'Air Quality Alert'].map((e) => ALERT_HEAT.test(e) || ALERT_COLD.test(e));
// 2026-07-15 20:00 EDT is 00:00Z on the 16th; the label must read Philadelphia's hour, not UTC's
const ms = Date.UTC(2026, 6, 16, 0, 0);
out.clock = alertClock(ms);
console.log(JSON.stringify(out));
'''
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=20)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.r = json.loads(run.stdout)

    def test_heat_and_cold_products(self):
        self.assertEqual([True, True, True], self.r['heat'])
        self.assertEqual([True, True, True, True], self.r['cold'])
        self.assertEqual([False, False, False], self.r['neither'])

    def test_clock_is_philadelphia_time(self):
        self.assertTrue(self.r['clock'].endswith('8 PM'), self.r['clock'])

    def test_alerts_ride_the_existing_nws_call(self):
        self.assertIn("alertsSet(al.features.map((f) => f.properties || {}))", self.src)
        self.assertEqual(1, self.src.count('/alerts/active?'), 'one alerts poll, not two')


if __name__ == '__main__':
    unittest.main()
