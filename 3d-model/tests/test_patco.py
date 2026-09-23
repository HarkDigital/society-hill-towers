"""Round 141: scheduled PATCO trains over the Ben Franklin Bridge (Mike: "add the scheduled PATCO trains on the bridge").

PATCO publishes no live positions, so bake_patco.py bakes its timetable and its OSM track into patco.json and the page
runs each bridge-crossing trip between its two scheduled minutes, drawn only between the portals. These checks read
patco.json (the two chains, the stops and portals in order, the trips, a service every day) and run the page's own
run profile, calendar and consist rule under Node. Nothing here depends on today's date (the deploy gate refuses on
any failing test)."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PatcoData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'patco.json').read_text())

    def test_chains(self):
        ch = self.d['chains']
        self.assertEqual([c['d'] for c in ch], [0, 1])                  # index = direction_id
        self.assertEqual({c['trk'] for c in ch}, {'north', 'south'})
        self.assertEqual(ch[0]['trk'], 'north')                          # right-hand running: westbound on the north track
        for c in ch:
            s = c['s']
            self.assertLess(s['11'], s['10'])                            # 8th and Market, Franklin Square, City Hall, Broadway, Philadelphia to Camden
            self.assertLess(s['10'], c['vis'][0])                        # the portals lie between Franklin Square and City Hall
            self.assertLess(c['vis'][0], c['vis'][1])
            self.assertLess(c['vis'][1], s['9'])
            self.assertLess(s['9'], s['8'])
            self.assertGreater(c['vis'][1] - c['vis'][0], 2000)          # the open run, portal to portal, about 2.3 km
            self.assertLess(c['vis'][1] - c['vis'][0], 2600)
            self.assertEqual(len(c['f']), len(c['p']) - 1)

    def test_trips_and_calendar(self):
        d = self.d
        self.assertEqual(len(d['trips']), len(d['svc']))
        for si, per in enumerate(d['trips']):
            for dr in (0, 1):
                for r in per[dr]:
                    tP, tC = r[0], r[1]
                    if dr == 1:
                        self.assertLess(tP, tC)                          # eastbound leaves Philadelphia first
                    else:
                        self.assertLess(tC, tP)
                    self.assertLess(abs(tP - tC), 20 * 60)
        self.assertTrue(all(m > 0 for m in d['days']))                    # every date of the feed runs something
        self.assertEqual(len(d['week']), 7)
        self.assertTrue(all(m > 0 for m in d['week']))
        if d['feed']['v'] == '19':   # the swap-day repair on feed 19's Bike MS day, Sep 26 2026
            import datetime
            k = (datetime.date(2026, 9, 26) - datetime.date.fromisoformat(d['feed']['from'])).days
            self.assertEqual(d['days'][k], 1 << d['svc'].index('Bike MS'))


class PatcoPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_run_calendar_and_consists(self):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        s = self.src
        cut = lambda a, b: s[s.index(a):s.index(b, s.index(a))]
        code = (cut('  function patcoServices(', '  function patcoRecon(') + cut('  function patcoRun(', '  function patcoCard('))
        head = 'const PATCO_RAMP = 0.15; const PATCO_DATA = ' + json.dumps({'feed': {'from': '2026-09-21'}, 'days': [4, 4, 8], 'week': [1, 1, 1, 1, 1, 2, 2]}) + ';\n'
        script = head + code + r'''
const run = []; for (let i = 0; i <= 100; i++) run.push(patcoRun(i / 100));
let mono = true; for (let i = 1; i < run.length; i++) mono = mono && run[i] >= run[i - 1];
const out = { r0: run[0], r1: run[100], mid: +run[50].toFixed(4), mono,
  inFeed: patcoServices(2026, 9, 23), before: patcoServices(2026, 9, 20), after: patcoServices(2027, 1, 2),
  peakWB: patcoCars('194 Weekday', 0, 8 * 3600), peakEB: patcoCars('194 Weekday', 1, 17 * 3600), midday: patcoCars('194 Weekday', 0, 12 * 3600),
  night: patcoCars('194 Weekday', 1, 23 * 3600), sat: patcoCars('194 Saturday', 0, 8 * 3600) };
console.log(JSON.stringify(out));
'''
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual((o['r0'], o['r1'], o['mid'], o['mono']), (0, 1, 0.5, True))
        self.assertEqual(o['inFeed'], {'mask': 8, 'typical': False})       # 2026-09-23 is the third day of the feed
        self.assertEqual(o['before'], {'mask': 2, 'typical': True})        # a Sunday before it: the weekly pattern
        self.assertEqual(o['after'], {'mask': 2, 'typical': True})         # a Saturday after it
        self.assertEqual((o['peakWB'], o['peakEB'], o['midday'], o['night'], o['sat']), (6, 6, 4, 2, 4))

    def test_wiring(self):
        s = self.src
        self.assertIn("step('Laying the PATCO tracks',", s)
        self.assertLess(s.index("step('Laying the PATCO tracks',"), s.index("step('Rolling out the SEPTA fleet',"))
        self.assertIn('    updatePatco(now, dt);\n', s)
        self.assertIn('trainCard(bestA);', s)
        self.assertIn('if (pickedTrain && !pickedTrain.patco) {', s)
        upd = s[s.index('  function updatePatco('):s.index('  function updatePatco(') + 5000]
        self.assertIn('if (!insideLimit(cx, cz) || !nearCam(cx, cy, cz)) continue;', upd)   # the half-mile rule (Round 82), like Amtrak's
        self.assertIn('if (sc < tr.sFaceP - PATCO_COVER || sc > tr.sFaceC + PATCO_LEN / 2 + 0.3) continue;', upd)   # nothing drawn underground (Round 20)
        # review fixes: the live clock is the HUD's own minute, a pinned hour loops, tomorrow's owls are looked at,
        # the cars sit on their trucks, the ties are never culled, the piers clear a road's width and the decks
        self.assertIn('if (clock.live) { PATCO_S.pinKey = \'\'; return clock.minutes * 60 + (Date.now() / 1000) % 60; }', s)
        self.assertIn('return clock.minutes * 60 + PATCO_S.drift % 3600;', s)
        self.assertIn('next.getUTCDate(), -86400]]', s)
        self.assertIn('patcoAt(tr, sc + dir * (PATCO_LEN / 2 - 3), _pcF);', upd)
        self.assertIn('tm.frustumCulled = false;', s)
        self.assertIn('septaSnapRoad(x, z, 9.6) || onDeck(x, z)', s)
        self.assertIn('if (hw < 4 && patcoCutAt(mx, mz)) continue;', s)
        self.assertIn('.concat(patcoCuts().filter(c=>streetOverlap(bounds,c.bounds)));', s)
        self.assertIn('const deckY = bfbDeckY;', s)
        # the train card never says live, and no em dash or middot in anything the card shows
        card = s[s.index('  function patcoCard('):s.index('  function trainCard(')]
        self.assertIn('Not Live', card)
        self.assertNotRegex(card, '[—·]')
        # the five pick branches that used to leave a train card's record set now clear it
        self.assertIn('pickedArt = null; pickedTrain = null; pickedClosure = rec; closureCard(rec);', s)
        self.assertIn('pickedMarket = null; pickedTrain = null; pickedMarker = isM ? r : null;', s)
        self.assertIn('pickedArt = null; pickedTrain = null; pickedClosure = bestC;', s)
        self.assertIn('pickedMarket = null; pickedTrain = null; pickedMarker = bestKm ? bestK : null;', s)
        self.assertIn('pickedShip = null; pickedTrain = null; pickedTree = bestT; treeCard(bestT);', s)
        tpl = (ROOT / 'template.html').read_text()
        self.assertIn('<span class="ltext">Trains</span>', tpl)
        self.assertIn('id="btnAmtrak"', tpl)


if __name__ == '__main__':
    unittest.main()
