"""The skyline lights' resolver (Round 81) run for real under JavaScriptCore: lightsThemeAt (a
team's game day first, Eagles before Phillies before Flyers before Sixers, then the calendar's
most specific request, then the house white), lightsGameDays (an ESPN scoreboard answer to the
Philadelphia days a Philadelphia team plays, preseason never), lightsCalOf (the baked rows
checked), lightsPinTheme (the ?lights= pin) and lightsLabel. The block is cut from app.js
between its first and last lines, with the clock's DST helpers cut the same way, so a drift in
the page is caught here. Skips when osascript is unavailable (non-macOS hosts)."""
import json
import shutil
import subprocess
import tempfile
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_lights_js
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

JXA = r'''%(tz)s
%(snippet)s
var cal = lightsCalOf({ t: 1789000000, rows: [
  { from: '2026-09-16', to: '2026-09-18', c: ['blue'], n: 'Pulmonary Fibrosis Awareness Month' },
  { from: '2026-09-17', to: '2026-09-17', c: ['teal', 'cyan'], n: 'Trigeminal Neuralgia Awareness Day' },
  { from: '2026-09-17', to: '2026-09-17', c: ['purple'], n: 'Later request' },
  { from: '2026-10-01', to: '2026-10-31', c: ['pink'], n: 'Breast Cancer Awareness Month' },
  { from: '2026-10-05', to: '2026-10-05', c: ['green', 'white', 'red'], n: 'Italian National Day' },
  { from: '2026-11-01', to: '2026-11-02', c: ['plaid'], n: 'No such colour' },
  { from: 'bad', to: '2026-11-02', c: ['blue'], n: 'Bad date' },
  { from: '2026-11-05', to: '2026-11-04', c: ['blue'], n: 'Ends before it starts' },
  { from: '2026-11-10', to: '2026-11-10', c: ['blue'], n: 'A <b>tag</b> in the name' },
  null
] });
var games = { nfl: {}, mlb: {}, nhl: {}, nba: {} };
var sb = function (date, abbr, type) { return { events: [{ date: date, season: { type: type || 2 }, competitions: [{ competitors: [{ team: { abbreviation: abbr } }, { team: { abbreviation: 'NYM' } }] }] }] }; };
var n1 = lightsGameDays(sb('2026-09-17T23:05Z', 'PHI'), games.mlb);          // 7:05 pm Philadelphia, the 17th
var n2 = lightsGameDays(sb('2026-09-18T00:15Z', 'PHI'), games.nfl);          // 8:15 pm Philadelphia on the 17th (Thursday night)
var n3 = lightsGameDays(sb('2026-09-22T23:00Z', 'PHI', 1), games.nhl);       // preseason: never
var n4 = lightsGameDays(sb('2026-10-05T23:00Z', 'BOS'), games.nba);          // someone else's game
var n5 = lightsGameDays(sb('2026-11-01T03:30Z', 'PHI'), games.nba);          // 11:30 pm Philadelphia on Oct 31 (EDT)
var n6 = lightsGameDays(sb('2026-11-02T04:30Z', 'PHI'), games.nhl);          // 11:30 pm Philadelphia on Nov 1 (EST)
var n7 = lightsGameDays(sb('2026-10-05T23:00Z', 'PHI'), games.nhl);          // the Flyers on the Italian night
var n8 = lightsGameDays(sb('2026-10-05T20:00Z', 'PHI'), games.mlb);          // and the Phillies the same day
var out = {
  counts: [n1, n2, n3, n4, n5, n6, n7, n8],
  mlbDays: Object.keys(games.mlb), nflDays: Object.keys(games.nfl), nbaDays: Object.keys(games.nba), nhlDays: Object.keys(games.nhl),
  calRows: cal.rows.length, calT: cal.t, calNames: cal.rows.map(function (r) { return r.n; }),
  sep17: lightsThemeAt(2026, 9, 17, games, cal),
  sep17noGames: lightsThemeAt(2026, 9, 17, { nfl: {}, mlb: {}, nhl: {}, nba: {} }, cal),
  sep16: lightsThemeAt(2026, 9, 16, null, cal),
  oct5: lightsThemeAt(2026, 10, 5, games, cal),
  oct5noGames: lightsThemeAt(2026, 10, 5, {}, cal),
  oct20: lightsThemeAt(2026, 10, 20, games, cal),
  oct31: lightsThemeAt(2026, 10, 31, games, cal),
  nov1: lightsThemeAt(2026, 11, 1, games, cal),
  nov10: lightsThemeAt(2026, 11, 10, games, cal),
  dec1: lightsThemeAt(2026, 12, 1, games, cal),
  noCal: lightsThemeAt(2026, 9, 17, null, null),
  pins: [lightsPinTheme('eagles'), lightsPinTheme('Phils'), lightsPinTheme('sixers'), lightsPinTheme('off'), lightsPinTheme('ff00aa'), lightsPinTheme('purple,gold'), lightsPinTheme('plaid'), lightsPinTheme(null), lightsPinTheme('')],
  labels: [lightsLabel({ colors: ['green'], name: 'Go Birds' }), lightsLabel({ colors: ['pink', 'blue'], name: 'National Pregnancy and Infant Loss Awareness Month' }), lightsLabel({ colors: ['white'], name: '' })],
  gap: [lightsDayGap('2026-09-16', '2026-09-18'), lightsDayGap('2026-12-31', '2027-01-01'), lightsDayGap('2026-03-07', '2026-03-09')],
  key: lightsDateKey(2026, 9, 7),
  badCal: [lightsCalOf(null), lightsCalOf({}), lightsCalOf({ rows: 'x' })]
};
JSON.stringify(out);'''


def snippet(src):
    """The pure resolver, cut from app.js by its first and last lines."""
    a = src.index('\n  const LIGHT_COLORS = ')
    b = src.index('\n  const THEME = {')
    return src[a:b]


def tz_snippet(src):
    """The clock's DST helpers the resolver leans on (nthSunday, tzOffsetMin), cut the same way."""
    a = src.index('\n  function nthSunday(')
    b = src.index('\n  function clockUtcMs(')
    return src[a:b]


class LightsRuntime(unittest.TestCase):
    def setUp(self):
        C.require(self, 'app.js')
        self.src = C.path('app.js').read_text(encoding='utf-8')

    def test_block_is_wired(self):
        """The frame drives the theme, the time panel prints its line, the strings carry no em dash."""
        self.assertIn('updateLightsTheme(now, dt);', self.src, 'the frame no longer updates the skyline lights')
        self.assertIn("'   Lights: '", self.src, 'the time panel lost its lights line')
        self.assertIn("typeof LIGHTS_CAL !== 'undefined'", self.src, 'the built-in calendar is not read')
        self.assertIn('lightsFetchDate(dk, now)', self.src, "the day's games are not fetched")
        self.assertIn("case 'band':", self.src, 'the PECO band crown is missing from the crown builder')
        self.assertNotIn('—', snippet(self.src), 'no em dash in the lights strings')
        for k in ('themeParts', 'themeSheets', 'bfbLampPts', 'bfbNodes'):
            self.assertIn(k, self.src, k + ' is missing')

    def test_resolver(self):
        """Game days first in team order, then the calendar's most specific request, then white; run under JavaScriptCore."""
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        script = JXA % {'snippet': snippet(self.src), 'tz': tz_snippet(self.src)}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=120)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:600])
        out = json.loads(r.stdout.strip())
        self.assertEqual([1, 1, 0, 0, 1, 1, 1, 1], out['counts'], 'a PHI game counts once, preseason and other teams never')
        self.assertEqual(['2026-09-17', '2026-10-05'], out['mlbDays'])
        self.assertEqual(['2026-09-17'], out['nflDays'], 'a Thursday night game at 00:15Z is the Philadelphia evening before')
        self.assertEqual(['2026-10-31'], out['nbaDays'], '03:30Z on Nov 1 is 11:30 pm on Oct 31 under EDT')
        self.assertEqual(['2026-11-01', '2026-10-05'], out['nhlDays'], '04:30Z on Nov 2 is 11:30 pm on Nov 1 under EST')
        self.assertEqual(6, out['calRows'], 'the unknown colour, the bad date and the reversed range are dropped')
        self.assertEqual(1789000000, out['calT'])
        self.assertIn('A btag/b in the name', out['calNames'], 'angle brackets never reach the panel')
        self.assertEqual({'colors': ['green'], 'stripes': ['green', 'white'], 'name': 'Go Birds', 'src': 'nfl'}, out['sep17'], 'the Eagles beat the Phillies and the calendar; the striped parts take the pair (Round 85)')
        self.assertEqual({'colors': ['teal', 'cyan'], 'name': 'Trigeminal Neuralgia Awareness Day', 'src': 'boma'}, out['sep17noGames'],
                         'the one-day request beats the three-day one; the earlier of two one-day requests loses to the later start only when spans tie and starts differ')
        self.assertEqual({'colors': ['blue'], 'name': 'Pulmonary Fibrosis Awareness Month', 'src': 'boma'}, out['sep16'])
        self.assertEqual('mlb', out['oct5']['src'], 'the Phillies come before the Flyers')
        self.assertEqual({'colors': ['green', 'white', 'red'], 'name': 'Italian National Day', 'src': 'boma'}, out['oct5noGames'], 'a one-day request beats the month')
        self.assertEqual({'colors': ['pink'], 'name': 'Breast Cancer Awareness Month', 'src': 'boma'}, out['oct20'])
        self.assertEqual('nba', out['oct31']['src'])
        self.assertEqual('nhl', out['nov1']['src'])
        self.assertEqual('boma', out['nov10']['src'])
        self.assertEqual({'colors': ['white'], 'name': '', 'src': 'house'}, out['dec1'], 'nothing that night: the house white')
        self.assertEqual('house', out['noCal']['src'], 'no data at all is the house white, not an error')
        p = out['pins']
        self.assertEqual({'colors': ['green'], 'stripes': ['green', 'white'], 'name': 'Go Birds', 'src': 'pin'}, p[0])
        self.assertEqual(['blue', 'red', 'white'], p[2]['stripes'], 'the Sixers stripe three')
        self.assertNotIn('stripes', p[4], 'a hex pin deals its own colour to the stripes')
        self.assertNotIn('stripes', p[5], 'so does a colour list')
        self.assertEqual('red', p[1]['colors'][0], 'the pin is case-insensitive')
        self.assertEqual('blue', p[2]['colors'][0])
        self.assertEqual('house', p[3]['src'], '?lights=off is the house white')
        self.assertEqual(['#ff00aa'], p[4]['colors'], 'a hex pin')
        self.assertEqual(['purple', 'gold'], p[5]['colors'], 'a colour list')
        self.assertIsNone(p[6], 'an unknown word pins nothing')
        self.assertIsNone(p[7])
        self.assertIsNone(p[8])
        self.assertEqual(['green, Go Birds', 'pink and blue, National Pregnancy and Infant Loss Awareness Month', 'white'], out['labels'])
        self.assertEqual([2, 1, 2], out['gap'])
        self.assertEqual('2026-09-07', out['key'])
        self.assertEqual([None, None, None], out['badCal'])


if __name__ == '__main__':
    unittest.main()
