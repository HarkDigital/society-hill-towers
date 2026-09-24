"""The RiverLink ferry is M/V Freedom on its own AIS (Round 151 built the model on a timetable; Round 152, Mike: "this boat
is the riverlink so get rid of the riverlink schedule and label M/V Freedom as the Riverlink").

The Freedom broadcasts AIS as MMSI 368417620. The ships layer eases its fix but no longer draws it as a generic hull; the
ferry model and pin stand at the fix, and its card names it the RiverLink Ferry, M/V Freedom, with no timetable anywhere."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Ferry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        a = cls.s.index('  // ---- the RiverLink ferry, M/V Freedom, on its own AIS')
        cls.block = cls.s[a:cls.s.index('  function trainCard(p)', a)]

    def test_ais_drives_it(self):
        s, b = self.s, self.block
        self.assertIn('const FERRY_MMSI = 368417620;', b)
        self.assertIn('const v = SHIPS.on ? shipMap.get(FERRY_MMSI) : null;', b)
        self.assertIn('if (!v || v.dx === undefined) { ferryHide(); return; }', b)
        # the ships layer eases its fix but no longer draws it a second time
        self.assertIn('if (v.mmsi === FERRY_MMSI) continue;   // the RiverLink ferry draws as its own model (Round 152)', s)
        # both ingest paths note whether the heading is the ship's own compass
        self.assertEqual(s.count('v.th = '), 2)

    def test_no_timetable(self):
        for gone in ('FERRY_SEASON', 'FERRY_BASE', 'ferryDay', 'ferryState', 'ferryNowSec', 'riverlinkferry.com', 'Next Departure', 'No Sailings'):
            self.assertNotIn(gone, self.s, gone)
        self.assertNotIn('Timetable', self.block)   # PATCO's cards keep theirs; the ferry has none

    def test_card(self):
        b = self.block
        self.assertIn('<span class="vroute" style="background:\' + FERRY_BLUE + \';color:#fdfbf6">RiverLink Ferry</span>', b)
        self.assertIn('<span class="vdest">M/V Freedom</span>', b)
        self.assertIn("'Live Position (AIS), Fix '", b)
        self.assertIn('shipLink(v);', b)
        self.assertNotRegex(b, '[—·]')   # no em dashes or middots in what the card says

    def test_wiring(self):
        s = self.s
        self.assertIn('    updateFerry(now);   // Round 151\n', s)
        self.assertIn('function trainCard(p) { if (p.ferry) ferryCard(p);', s)
        self.assertIn('if (pickedTrain && !pickedTrain.patco && !pickedTrain.ferry) {', s)
        self.assertIn('if (yAct) targets.push(FERRY.mesh, FERRY.pin);', s)


if __name__ == '__main__':
    unittest.main()
