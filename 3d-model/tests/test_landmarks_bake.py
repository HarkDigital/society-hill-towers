"""bake_landmarks.py (Round 78): the City basemap's named places for the search index. A
parent with unnamed parcels collapses to one site at the area-weighted centroid; a parcel
with its own name emits itself and feeds its parent; archived, non-public, neighborhood and
parking rows are dropped; a recurring name far apart is two sites; the dash rule; the flat
layout; City Hall's outline lands at City Hall in the frame."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from bake_landmarks import bake, KINDS, CLS   # noqa: E402


def square(lon, lat, d=0.0004):
    return [[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]


def poly(name, sub, lon, lat, d=0.0004, **props):
    p = {'NAME': name, 'TYPE': 10, 'SUBTYPE': sub, 'PUBLIC_': 'Y', 'ARCHIVE_DATE': None, 'PARENT_NAME': None, 'PARENT_SUBTYPE': None}
    p.update(props)
    return {'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [square(lon, lat, d)]}, 'properties': p}


def point(name, sub, lon, lat, **props):
    p = {'NAME': name, 'TYPE': 10, 'SUBTYPE': sub, 'PUBLIC_': 'Y', 'ARCHIVE_DATE': None, 'PARENT_NAME': None}
    p.update(props)
    return {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]}, 'properties': p}


def entries(out):
    L = out['l']
    return {out['names'][L[i]]: (L[i + 1], L[i + 2], L[i + 3]) for i in range(0, len(L), 4)}


class Landmarks(unittest.TestCase):
    def test_parent_collapses_and_child_emits(self):
        out = bake([
            poly(None, 'Park', -75.20, 39.95, 0.0006, PARENT_NAME='Clark Park', PARENT_SUBTYPE='Park'),
            poly(None, 'Park', -75.202, 39.95, 0.0002, PARENT_NAME='Clark Park', PARENT_SUBTYPE='Park'),
            poly(None, 'Playground', -75.201, 39.951, 0.0002, PARENT_NAME='Clark Park', PARENT_SUBTYPE='Park'),
            poly('Clark Park Dog Bowl', 'Park', -75.203, 39.949, 0.0002, PARENT_NAME='Clark Park', PARENT_SUBTYPE='Park'),
        ])
        e = entries(out)
        self.assertEqual({'Clark Park', 'Clark Park Dog Bowl'}, set(e), 'one site for the parent, the named parcel on its own')
        self.assertEqual(4, e['Clark Park'][2], 'the park class')
        px, pz, _ = e['Clark Park']
        bx, bz, _ = e['Clark Park Dog Bowl']
        self.assertTrue(abs(px - -4737) < 40 and abs(pz - -505) < 40, 'the weighted centroid sits near the big parcel: %r' % ((px, pz),))
        self.assertNotEqual((px, pz), (bx, bz))
        self.assertEqual(len(out['l']), 4 * len(out['names']))

    def test_drops_and_classes(self):
        out = bake([
            poly('Old Thing', 'Park', -75.15, 39.95, ARCHIVE_DATE='2020-01-01'),
            poly('Pumping Station', 'Water Supply / Treatment', -75.15, 39.95, TYPE=3),
            poly('Private Lot', 'Park', -75.15, 39.95, PUBLIC_='N'),
            point('Fishtown', 'Neighborhood', -75.13, 39.97, TYPE=9),
            point('Garage', 'Parking Lot / Garage', -75.15, 39.95, TYPE=12),
            poly('Masterman School', 'High School', -75.16, 39.96, TYPE=1),
            poly('Christ Church', 'Place of Worship', -75.14, 39.95),
            poly('Pennsylvania Hospital', 'Hospital / Emergency Medical Center', -75.155, 39.945, TYPE=5),
            poly('Laurel Hill', 'Cemetery', -75.19, 40.0),
            point('Ben Franklin Bridge', 'Bridge', -75.13, 39.955, TYPE=12),
            poly('Far Away', 'Park', -74.0, 40.5),
        ])
        e = entries(out)
        self.assertEqual({'Masterman School', 'Christ Church', 'Pennsylvania Hospital', 'Laurel Hill', 'Ben Franklin Bridge'}, set(e))
        self.assertEqual(KINDS.index('school'), e['Masterman School'][2])
        self.assertEqual(KINDS.index('worship'), e['Christ Church'][2])
        self.assertEqual(KINDS.index('hospital'), e['Pennsylvania Hospital'][2])
        self.assertEqual(KINDS.index('cemetery'), e['Laurel Hill'][2])
        self.assertEqual(KINDS.index('bridge'), e['Ben Franklin Bridge'][2])
        self.assertEqual(len(KINDS), 1 + max(CLS.values()))

    def test_recurring_name_and_dashes(self):
        out = bake([
            poly('US Post Office — Main', 'Post Office', -75.15, 39.95, 0.0006, TYPE=4),
            poly('US Post Office — Main', 'Post Office', -75.15, 39.9502, 0.0002, TYPE=4),
            poly('US Post Office — Main', 'Post Office', -75.25, 40.02, 0.0004, TYPE=4),
        ])
        self.assertEqual(['US Post Office, Main', 'US Post Office, Main'], out['names'], 'two sites 10 km apart, the dash a comma, the bigger first')
        L = out['l']
        self.assertTrue(abs(L[1] - -448) < 30, 'the bigger cluster leads')

    def test_city_hall_in_the_frame(self):
        e = entries(bake([poly('City Hall', 'Municipal Government', -75.16353, 39.95272, TYPE=4)]))
        x, z, _ = e['City Hall']
        self.assertTrue(abs(x - -1603) < 5 and abs(z - -802) < 5, 'City Hall is at (-1603, -802): %r' % ((x, z),))


if __name__ == '__main__':
    unittest.main()
