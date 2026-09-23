"""Round 151: the RiverLink ferry on its timetable (Mike: no live position, so a schedule).

ferryDay is cut from app.js and run under Node: the 2026 season (full service May 23 to Sep 7, Tuesday to Sunday and the
two holiday Mondays; weekends only Sep 8 to Oct 27), the weekend extras, a Freedom Mortgage Pavilion shuttle, and the rule
that a run is only taken from where the one boat is."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Ferry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const FERRY = {')
        block = s[a:s.index('  const _fyA = [0, 0];', a)]
        cls.script = 'let CONCERTS = { events: [] };\n' + block + r'''
const n = (y, m, d) => ferryDay(y, m, d);
const out = {
  tueJul: n(2026, 7, 7).length, monJul: n(2026, 7, 6).length, labor: n(2026, 9, 7).length, memorial: n(2026, 5, 25).length,
  satJul: n(2026, 7, 11).length, wedSep: n(2026, 9, 23).length, satSep: n(2026, 9, 26).length, satNov: n(2026, 10, 31).length,
  alternate: n(2026, 9, 26).every((r, i, a) => i === 0 || r[1] !== a[i - 1][1]) && n(2026, 9, 26)[0][1] === 'cam',
  first: n(2026, 7, 7)[0], last: n(2026, 7, 7).slice(-1)[0],
};
CONCERTS.events = [{ date: '2026-09-23', time: '19:30', venue: { name: 'Freedom Mortgage Pavilion' } }];
const show = n(2026, 9, 23);
out.show = show.length; out.showAll = show.every((r) => r[2]); out.showFirst = show[0];
console.log(JSON.stringify(out));'''

    def test_timetable(self):
        r = subprocess.run(['node', '-e', self.script], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o['tueJul'], 14)       # Camden 10:30 to 4:30, Philadelphia 11:00 to 5:00
        self.assertEqual(o['monJul'], 0)        # closed Mondays
        self.assertEqual(o['labor'], 14)        # but not Labor Day or Memorial Day
        self.assertEqual(o['memorial'], 14)
        self.assertEqual(o['satJul'], 20)       # the weekend adds three each way
        self.assertEqual(o['wedSep'], 0)        # after Labor Day, weekends only
        self.assertEqual(o['satSep'], 20)
        self.assertEqual(o['satNov'], 0)        # the season is over
        self.assertTrue(o['alternate'])         # one boat, starting from Camden
        self.assertEqual(o['first'], [630 * 60, 'cam', False])
        self.assertEqual(o['last'], [1020 * 60, 'phl', False])
        self.assertGreater(o['show'], 10)       # a pavilion show on an otherwise dark day runs the shuttle
        self.assertTrue(o['showAll'])
        # the boat lies at Camden, so the shuttle starts from there a quarter hour after the first Philadelphia slot
        self.assertEqual(o['showFirst'], [(19 * 60 + 30 - 105) * 60, 'cam', True])

    def test_wiring(self):
        s = (ROOT / 'app.js').read_text()
        self.assertIn('    updateFerry(now);   // Round 151\n', s)
        self.assertIn("function trainCard(p) { if (p.ferry) ferryCard(p);", s)
        self.assertIn('if (pickedTrain && !pickedTrain.patco && !pickedTrain.ferry) {', s)
        self.assertIn("'<div class=\"vmeta\">Timetable Position, Not Live</div>'", s)


if __name__ == '__main__':
    unittest.main()
