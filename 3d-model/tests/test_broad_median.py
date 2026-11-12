"""South Broad Street's median (Round 238, Mike, Nov 11: "Draw the median on South Broad so the cars come back").

Round 236 took the parked rows off the inner kerbs of every divided street, South Broad's with them, though the city has
long let about two hundred cars park down the middle of Broad from Washington Avenue to Oregon Avenue. OSM draws the stretch
as two one-way carriageways 8.7 to 13 m apart, each painted 13 m wide as a two-way street. The page now finds the two by
their place (broadMedianFit), counts each one's lanes from the median's edge (broadMedLane, broadMedU), lays the median and
its double yellows again as a strip of their own from crossing to crossing (broadMedianDraw), and parks a row down its
middle (broadMedSlots, laid by parkedLay). tests/broad_median_checks.js runs the page's own functions over scene_wide.json:

- the fit takes South Broad's carriageways and nothing else, both sides, 8.7 to 13 m apart, and every one of the 21 named
  streets over the median's line (Washington to Oregon) breaks the row and both halves of the strip;
- each carriageway's paint: its centre line 2.9 to 3.9 m off the median's edge, its kerb at the half width the shader reads
  (so no kerb is painted inside it), three lanes everywhere, the inner moving lane clear of the double yellow;
- the strip: each half its carriageway's paint continued (u from -m/2 at the middle to BROAD_MED.edge past the edge, the
  same half width, no junction), the median 2.9 to 5.2 m wide;
- the row: about three hundred slots inside the blocks, on the middle, both ways about, at the blocks' own fills; a parked
  van and the inner lane's car pass clear at the narrowest;
- the wiring: on under REAL, off with ?broadmed=0 and with ?parkmid=1; the wide loop's call sites and parkedLay's loop.
"""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / 'app.js').read_text()


class Runtime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = subprocess.run(['node', str(ROOT / 'tests/broad_median_checks.js')], capture_output=True, text=True, timeout=120)
        if run.returncode:
            raise AssertionError(run.stderr or run.stdout)
        cls.r = json.loads(run.stdout)

    def test_fit_finds_the_two_carriageways(self):
        f = self.r['fit']
        self.assertEqual(self.r['names'], ['South Broad Street'])
        self.assertGreaterEqual(f['recs'], 40)
        self.assertGreaterEqual(min(self.r['sides'].values()), 18)
        self.assertGreater(f['sepMin'], 8.5)
        self.assertLess(f['sepMax'], 13.5)
        self.assertEqual(f['ownNoses'], 2 * f['crossings'])   # every crossing's nose from each carriageway's own junction

    def test_every_crossing_street_breaks_the_median(self):
        names = {c[0] for c in self.r['crossings']}
        for n in ('Washington Avenue', 'Ellsworth Street', 'Federal Street', 'Wharton Street', 'Reed Street', 'Dickinson Street',
                  'Tasker Street', 'Morris Street', 'Moore Street', 'Mifflin Street', 'McKean Street', 'Passyunk Avenue',
                  'Snyder Avenue', 'Jackson Street', 'Wolf Street', 'Ritner Street', 'Porter Street', 'Shunk Street', 'Oregon Avenue'):
            self.assertIn(n, names)
        for c in self.r['crossings']:
            self.assertTrue(all(c[2:]), c)   # in a gap of the row and of both halves of the strip
        self.assertEqual(len(self.r['blocks']), 19)
        self.assertTrue(1900 < self.r['fit']['m'] < 2200, self.r['fit']['m'])
        self.assertEqual(self.r['half'], {'1': 19, '-1': 19})

    def test_carriageway_lanes_count_from_the_median(self):
        p = self.r['paint']
        self.assertGreater(p['pts'], 100)
        self.assertGreater(p['eMin'], 2.85)
        self.assertLess(p['eMax'], 3.95)
        self.assertLess(p['kerbErr'], 0.08)   # the kerb's u is the half width: no kerb painted inside the carriageway
        self.assertEqual(p['lanes'], [3])     # two moving lanes and the parking lane, everywhere
        self.assertGreater(p['innerFlank'], 0.25)   # a 2 m car in the inner lane clear of the double yellow (0.22 out)

    def test_strip_continues_each_carriageways_paint(self):
        s = self.r['strip']
        self.assertGreater(s['tris'], 500)
        self.assertEqual(s['cols'], s['verts'])
        self.assertAlmostEqual(s['uMinPlusHalf'], 0, places=3)   # the middle is u = -m/2 from either half
        self.assertAlmostEqual(s['uMax'], 0.35, places=3)        # out to BROAD_MED.edge past the edge, over the double yellow
        self.assertEqual(s['outer'], [0.35, 0.35])
        self.assertEqual(s['midErr'], 0)
        self.assertTrue(9.3 <= s['hw'][0] and s['hw'][1] <= 10.5, s['hw'])   # the carriageways' own half width (6.5 + e)
        self.assertGreaterEqual(s['sMin'], 0)
        self.assertEqual(s['clsMax'], 0)   # no junction: the double yellow runs nose to nose
        self.assertTrue(2.85 < self.r['m'][0] and self.r['m'][1] < 5.3, self.r['m'])

    def test_row_down_the_middle(self):
        w = self.r['row']
        self.assertTrue(250 <= w['slots'] <= 340, w['slots'])
        self.assertTrue(w['inBlock'])
        self.assertLessEqual(w['latMax'], 0.151)
        self.assertAlmostEqual(w['y'], 0.24 + 0.38, places=6)   # on the strip's top
        self.assertTrue(0.7 <= w['fillMin'] and w['fillMax'] <= 0.95, w)
        self.assertGreater(min(w['yaws']), 100)   # both ways about
        self.assertGreater(self.r['clear'], 0.45)   # a 2.1 m van 0.15 m off the middle and a 2 m car in the inner lane

    def test_flags(self):
        self.assertFalse(self.r['on?broadmed=0'])
        self.assertFalse(self.r['on?parkmid=1'])
        self.assertTrue(self.r['on?real=1'])


class Wiring(unittest.TestCase):
    def test_call_sites(self):
        self.assertIn('const BM = BROAD_MED_ON ? broadMedianFit(wideRoadRecs, JX) : null;', SRC)
        self.assertIn('if (BM && BM.side.has(ri)) laneJ = broadMedLane(BM, BM.side.get(ri), laneJ, rc);', SRC)
        self.assertIn('if (BM) broadMedianDraw(BM, rc, rcLane, wideRoadRecs);', SRC)
        self.assertIn('for (let i = 0; i < BROAD_SLOTS.length; i += 6) {', SRC)
        self.assertIn("const BROAD_MED_ON = REAL && !/[?&]broadmed=0\\b/.test(location.search) && !/[?&]parkmid=1\\b/.test(location.search);", SRC)

    def test_strip_above_every_carriageway(self):
        # a primary carriageway stands LAYER.road + 0.22 + up to 0.1 (the wide loop's jr); the strip 0.06 over the highest
        self.assertIn('up: 0.38', SRC)
        self.assertIn('LAYER.road + (6 - Math.min(t, 6)) * 0.055 + hash01(i * 3.7 + 1.1) * 0.1', SRC)


if __name__ == '__main__':
    unittest.main()
