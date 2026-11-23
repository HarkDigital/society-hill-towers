"""Round 267 (Mike: "The train station is missing from 2nd and market. I would like all underground Market Frankford
line, Broad Street Line, Patco stations to be included"): subway.json from bake_subway.py and the page's wiring. Every
underground station of the three lines is in it with an entrance, the timetables decode to rising minutes, the entrances
point at real stations, and the page builds the wells, pins and card from it behind ?subway=0."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / 'subway.json').read_text())
SRC = (ROOT / 'app.js').read_text()

L_STATIONS = {'2nd Street', '5th Street', '8th & Market (L/B)', '11th Street', '13th Street', '15th Street', '30th Street', '34th Street'}
B_STATIONS = {'NRG', 'Oregon', 'Snyder', 'Tasker-Morris', 'Ellsworth-Federal', 'Lombard-South', 'Walnut-Locust', 'City Hall',
              'Race-Vine', 'Spring Garden', 'Fairmount', 'Girard', 'Cecil B. Moore', 'Susquehanna-Dauphin', 'North Philadelphia',
              'Allegheny', 'Erie', 'Hunting Park', 'Wyoming', 'Logan', 'Olney Transportation Center', 'Chinatown'}
P_STATIONS = {'15th-16th & Locust', '12th-13th & Locust', '9th-10th & Locust', '8th & Market (PATCO)', 'Franklin Square', 'City Hall, Camden'}


class Data(unittest.TestCase):
    def test_every_underground_station(self):
        names = {s['n'] for s in D['st']}
        self.assertEqual(names, L_STATIONS | B_STATIONS | P_STATIONS)
        by = {s['n']: s for s in D['st']}
        for n in L_STATIONS:
            self.assertIn('L', by[n]['ln'], n)
        for n in B_STATIONS:
            self.assertIn('B', by[n]['ln'], n)
        for n in P_STATIONS:
            self.assertEqual(by[n]['ln'], ['P'], n)
        # none of the El's elevated stations, nor Fern Rock at grade
        for n in names:
            self.assertNotRegex(n, r'^(40th|46th|52nd|56th|60th|63rd|69th|Berks|York|Huntingdon|Somerset|Tioga|Church|Fern Rock)')

    def test_every_station_has_an_entrance(self):
        have = {e[2] for e in D['en']}
        self.assertEqual(have, set(range(len(D['st']))))
        second = [i for i, s in enumerate(D['st']) if s['n'] == '2nd Street'][0]
        self.assertGreaterEqual(sum(1 for e in D['en'] if e[2] == second), 2)   # Mike's corner
        for x, z, si, both in D['en']:
            s = D['st'][si]
            self.assertLess(((x - s['x']) ** 2 + (z - s['z']) ** 2) ** 0.5, 260)
            self.assertIn(both, (0, 1))

    def test_the_timetables(self):
        two = [s for s in D['st'] if s['n'] == '2nd Street'][0]
        heads = {(r, h) for r, h, _ in two['d']}
        self.assertEqual(heads, {('L1', 'Frankford'), ('L1', '69th Street')})
        for s in D['st']:
            for route, head, byday in s['d']:
                for k in ('wk', 'sa', 'su'):
                    t, prev = 0, -1
                    for i, v in enumerate(byday[k]):
                        t += v
                        self.assertGreaterEqual(t, prev, (s['n'], route, head, k))
                        prev = t
                    if byday[k]:
                        self.assertLess(t, 30 * 60, (s['n'], route, head, k))   # GTFS's 24:00 and later kept, nothing past 30:00
                self.assertTrue(byday['wk'], (s['n'], route, head))
        # a terminal's arrivals are not departures: the express ends at Walnut-Locust, so none leaves it southbound
        wl = [s for s in D['st'] if s['n'] == 'Walnut-Locust'][0]
        self.assertNotIn(('B2', 'Walnut-Locust'), {(r, h) for r, h, _ in wl['d']})

    def test_user_facing_text(self):
        for s in D['st']:
            for word in [s['n']] + [h for _, h, _ in s['d']]:
                self.assertNotIn('—', word)
                self.assertNotIn('·', word)


class Page(unittest.TestCase):
    def test_built_behind_its_hatch(self):
        self.assertIn("const SUBWAY_ON = !/[?&]subway=0\\b/.test(location.search) && typeof SUBWAY !== 'undefined'", SRC)
        self.assertIn("step('Opening the subway stations', () => {", SRC)
        self.assertIn('const("SUBWAY", text_of("subway.json", "null"))', (ROOT / 'build.py').read_text())

    def test_pins_card_and_search(self):
        self.assertIn("subwayPins = SUB_LI.map((L) => pinMesh(pinTexture(SUB_LINES[L].c, '#fdfbf6', glyphLetter(L)), 40, 'subwayPin'));", SRC)
        self.assertIn("if (st.rec.kind === 'subway') { subwayCard(st); return; }", SRC)
        self.assertIn("'Scheduled times from SEPTA\\'s timetable, not live'", SRC)
        self.assertIn("subway: 'Subway Station',", SRC)
        self.assertIn("if ((e.kind === 'rail' || e.kind === 'subway') && e.ref) openStopCard(e.ref);", SRC)
        # the stations' pins follow the Rail Stations layer: the stops' near list asks STOPS.stations for any kind but a bus
        self.assertIn("(rec.kind === 'bus' ? STOPS.on : STOPS.stations) && nearCam(rec.x, rec.gy, rec.z)", SRC)

    def test_the_entrances_never_cull_by_one_geometry(self):
        self.assertIn('body.frustumCulled = false;', SRC)
        self.assertIn('S.frustumCulled = false;', SRC)


if __name__ == '__main__':
    unittest.main()
