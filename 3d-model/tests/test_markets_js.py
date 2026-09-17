"""The market clock predicate (Round 76) run for real under JavaScriptCore: marketOpenAt and
marketInSeason are cut from app.js and fed a Headhouse-shaped record (Sunday 10 to 2, year
round), a June-to-November record and a wrap-around season. Skips when osascript is
unavailable (non-macOS hosts)."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_markets_js
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

JXA = r'''%(snippet)s
var head = { yr: true, o: null, c: null, h: { '0': [600, 840, 'note'] } };
var summer = { yr: false, o: [6, 1], c: [11, 30], h: { '4': [960, 1140] } };
var winter = { yr: false, o: [11, 15], c: [3, 31], h: { '6': [540, 780] } };
var nine = { yr: true, o: null, c: null, h: { '6': [540, 840] } };
var out = {
  headSun11: marketOpenAt(head, 2026, 9, 20, 660),
  headSun14: marketOpenAt(head, 2026, 9, 20, 840),
  headSun959: marketOpenAt(head, 2026, 9, 20, 599),
  headMon: marketOpenAt(head, 2026, 9, 21, 660),
  summerJulyThu: marketOpenAt(summer, 2026, 7, 16, 1000),
  summerJulyWed: marketOpenAt(summer, 2026, 7, 15, 1000),
  summerDecThu: marketOpenAt(summer, 2026, 12, 3, 1000),
  summerJune1: marketOpenAt(summer, 2026, 6, 4, 1000),
  winterJanSat: marketOpenAt(winter, 2026, 1, 10, 600),
  winterJulSat: marketOpenAt(winter, 2026, 7, 11, 600),
  winterNov14: marketInSeason(winter, 11, 14),
  winterNov15: marketInSeason(winter, 11, 15),
  nineSat: marketOpenAt(nine, 2026, 9, 19, 540)
};
JSON.stringify(out);'''


def snippet(src):
    a = src.index('\n  function marketOpenAt(')
    b = src.index('\n  const marketOpen = ')
    return src[a:b]


class MarketClock(unittest.TestCase):
    def setUp(self):
        C.require(self, 'app.js')
        self.src = C.path('app.js').read_text(encoding='utf-8')

    def test_predicate(self):
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        script = JXA % {'snippet': snippet(self.src)}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=120)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:600])
        out = json.loads(r.stdout.strip())
        self.assertTrue(out['headSun11'], 'Headhouse is open on a Sunday at 11')
        self.assertFalse(out['headSun14'], 'the end is exclusive: closed at 2')
        self.assertFalse(out['headSun959'], 'not yet open at 9:59')
        self.assertFalse(out['headMon'], 'closed on a Monday')
        self.assertTrue(out['summerJulyThu'])
        self.assertFalse(out['summerJulyWed'], 'a Thursday market is closed on a Wednesday')
        self.assertFalse(out['summerDecThu'], 'closed for the season in December')
        self.assertTrue(out['summerJune1'], 'the season includes its opening week')
        self.assertTrue(out['winterJanSat'], 'a November-to-March season wraps across New Year')
        self.assertFalse(out['winterJulSat'])
        self.assertFalse(out['winterNov14'])
        self.assertTrue(out['winterNov15'])
        self.assertTrue(out['nineSat'], "a '9:00' start opens at 540")

    def test_wiring(self):
        self.assertIn("step('Pitching the market tents'", self.src)
        self.assertIn('updateMarkets(now);', self.src, 'the frame loop must re-evaluate the markets (with the frame time since Round 82: the tents re-deal as the camera moves)')
        self.assertIn("market: 'Farmers Market'", self.src, 'the search index label for a market')


if __name__ == '__main__':
    unittest.main()
