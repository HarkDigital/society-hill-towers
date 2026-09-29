"""Round 169: the citywide landmark labels stand on their buildings.

Mike: "Fix the location of the Met on north broad. The map location when searching is wrong. The met is at the south west
corner of broad and poplar." The label (which is also the search result) stood 211 m south of the Met, and the Divine Lorraine's
350 m north of the hotel, beside the Met; the Mann Center, Freedom Mortgage Pavilion, Chestnut Hill College, Frankford Arsenal,
Christ Church and Valley Green Inn were 80 m to 2.2 km off too. Every label is now checked against the city basemap's own point
for the same name (landmarks.json, OSM outline centroids in the scene frame); campuses, parks and districts are areas and get a
wider allowance. The concert placards pin the Met by name (VENUE_NAMED), because Ticketmaster's point is across Broad Street."""
import json
import math
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAT0, LON0 = 39.94547, -75.14475
MX, MZ = 111320 * math.cos(math.radians(LAT0)), 110574

# an area's label stands somewhere inside it, not on one building of it
AREAS = {'University of Pennsylvania', 'Drexel University', "Saint Joseph's University", "Bartram's Garden", 'Navy Yard',
         'Italian Market', 'Temple University', 'Laurel Hill Cemetery', 'La Salle University', 'Einstein Medical Center',
         'Northeast Philadelphia Airport'}


def scene(lat, lon):
    return (lon - LON0) * MX, -(lat - LAT0) * MZ


class LandmarkLabels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        blk = cls.src[cls.src.index('    for (const [nm, la, lo, lh] of ['):]
        blk = blk[:blk.index('    ]) {')]
        cls.rows = [(m[1], float(m[2]), float(m[3])) for m in re.findall(r"\[(['\"])(.+?)\1, ([\d.]+), (-[\d.]+), \d+\]", blk)]
        cls.lm = json.loads((ROOT / 'landmarks.json').read_text())

    def test_every_label_stands_on_its_place(self):
        self.assertGreaterEqual(len(self.rows), 40)
        norm = lambda t: re.sub(r'^the ', '', t.lower())
        names, L = self.lm['names'], self.lm['l']
        checked = 0
        for nm, la, lo in self.rows:
            x, z = scene(la, lo)
            ds = [math.hypot(L[i * 4 + 1] - x, L[i * 4 + 2] - z) for i, n in enumerate(names) if norm(n) == norm(nm)]
            if not ds:
                continue
            checked += 1
            self.assertLess(min(ds), 400 if nm in AREAS else 90, nm)
        self.assertGreaterEqual(checked, 25)

    def test_the_met_at_broad_and_poplar(self):
        # OSM way 335078446 "The Met" (Metropolitan Opera House), the four corners of its outline
        corners = [(39.9694945, -75.1606558), (39.9702346, -75.1605041), (39.9701672, -75.1599395), (39.9694269, -75.1600884)]
        cx, cz = scene(sum(c[0] for c in corners) / 4, sum(c[1] for c in corners) / 4)
        la, lo = next((a, b) for n, a, b in self.rows if n == 'The Met Philadelphia')
        x, z = scene(la, lo)
        self.assertLess(math.hypot(x - cx, z - cz), 10)
        # south-west of the corner: west of the outline's east (Broad Street) edge, south of its north (Poplar) edge
        self.assertLess(lo, -75.15994)
        self.assertLess(la, 39.97023)
        # the Divine Lorraine is its own building two blocks south, at Fairmount, where the rebuild stands
        la, lo = next((a, b) for n, a, b in self.rows if n == 'Divine Lorraine Hotel')
        x, z = scene(la, lo)
        self.assertLess(math.hypot(x - -1308.5, z - -2352.5), 15)

    def test_a_met_concert_lands_on_the_met(self):
        m = re.search(r"\[/(\\bthe met\\b\|metropolitan opera)/i, (-?[\d.]+), (-?[\d.]+)\]", self.src)
        self.assertIsNotNone(m)
        rx = re.compile(m.group(1).replace('\\\\', '\\'), re.I)
        for venue in ('The Met Philadelphia', 'The Met', 'Metropolitan Opera House'):
            self.assertTrue(rx.search(venue), venue)
        for venue in ('Metropolitan Bakery', 'The Metropolitan', 'Met-Ed Arena'):
            self.assertFalse(rx.search(venue), venue)
        self.assertLess(math.hypot(float(m.group(2)) - -1326.8, float(m.group(3)) - -2693.7), 1)


if __name__ == '__main__':
    unittest.main()
