"""bake_markers.py (Round 77): the PHMC historical markers and the Percent for Art works for
the app. Marker types by name (Plaque is 2), the year from the dedication date, the dash rule
on texts, the ' - PLAQUE' suffix stripped, two markers on one spot nudged 2 m apart, the box
clip; artworks kept only when Active, the buffer polygon's centroid, the material scan, the
image link only on the city's bucket, and the column counts the app decodes."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from bake_markers import bake, art_material, FootGrid   # noqa: E402


def marker(name, lat=39.9455, lon=-75.1447, **kw):
    r = {'name': name, 'county': 'Philadelphia', 'dedicateddate': '1993-04-17T00:00:00.000', 'markertype': 'City',
         'location': 'S 3rd St, Philadelphia', 'markertext': 'Text of the marker.', 'status': 'False',
         'latitude': str(lat), 'longitude': str(lon)}
    r.update(kw)
    return r


def art(title, cx=-75.15, cy=39.95, status='Active', **kw):
    d = 0.0004
    ring = [[cx - d, cy - d], [cx + d, cy - d], [cx + d, cy + d], [cx - d, cy + d], [cx - d, cy - d]]
    p = {'title': title, 'artist': 'Someone', 'date_': '2008', 'medium': 'Bronze', 'location_name': 'A plaza',
         'address': '1 Market St', 'status': status, 'image': 'No image available', 'google_streetview_link': 'N/A'}
    p.update(kw)
    return {'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [ring]}, 'properties': p}


class Markers(unittest.TestCase):
    def test_markers(self):
        out = bake([
            marker('Common Sense', markertype='Roadside', markertext='Published here — January 1776.'),
            marker('Hannah Penn - PLAQUE', markertype='Plaque'),
            marker('Twin A', lat=39.95, lon=-75.16),
            marker('Twin B', lat=39.95, lon=-75.16),
            marker('Far away', lat=40.5, lon=-74.0),
            marker('No coordinate', latitude=None, longitude=None),
            marker('No year', dedicateddate=None),
        ], [])['m']
        by = {m[4]: m for m in out}
        self.assertEqual(['Common Sense', 'Hannah Penn', 'No year', 'Twin A', 'Twin B'], sorted(by), 'the box clip and the missing coordinate')
        self.assertEqual(0, by['Common Sense'][2], 'Roadside is type 0')
        self.assertEqual(2, by['Hannah Penn'][2], 'Plaque is type 2, and the suffix is gone')
        self.assertEqual('Published here, January 1776.', by['Common Sense'][6], 'the em dash becomes a comma')
        self.assertEqual(1993, by['Common Sense'][3])
        self.assertIsNone(by['No year'][3])
        self.assertEqual(by['Twin A'][0] + 2, by['Twin B'][0], 'two markers on one spot stand 2 m apart')
        self.assertEqual(by['Twin A'][1], by['Twin B'][1])
        for m in out:
            self.assertEqual(7, len(m))
            self.assertTrue(abs(m[0]) < 20000 and abs(m[1]) < 25000)

    def test_art(self):
        out = bake([], [
            art('A Part/Apart', medium='3 steel relief panels', image='https://dpd-art-is-essential-docs.s3.amazonaws.com/203.pdf'),
            art('Inside', status='Inaccessible'),
            art('Coming', status='In Progress'),
            art('Elsewhere image', image='https://example.com/x.pdf', medium='Granite'),
            art('Plain', medium='Mixed media · light'),
        ])['a']
        by = {a[3]: a for a in out}
        self.assertEqual(['A Part/Apart', 'Elsewhere image', 'Plain'], sorted(by), 'only Active works ship')
        self.assertEqual('https://dpd-art-is-essential-docs.s3.amazonaws.com/203.pdf', by['A Part/Apart'][8])
        self.assertEqual('', by['Elsewhere image'][8], 'an image off the city bucket is dropped')
        self.assertEqual(1, by['A Part/Apart'][2], 'steel')
        self.assertEqual(2, by['Elsewhere image'][2], 'granite is stone')
        self.assertEqual(3, by['Plain'][2])
        self.assertEqual('Mixed media, light', by['Plain'][6], 'the middot becomes a comma')
        self.assertEqual('A plaza', by['Plain'][7])
        a = by['Plain']
        self.assertTrue(abs(a[0] - -448) < 3 and abs(a[1] - -500) < 3, 'the buffer centroid in the frame: %r' % ((a[0], a[1]),))
        for row in out:
            self.assertEqual(9, len(row))

    def test_material_scan(self):
        self.assertEqual(0, art_material('Cast bronze'))
        self.assertEqual(1, art_material('Painted aluminum'))
        self.assertEqual(2, art_material('Concrete and limestone'))
        self.assertEqual(3, art_material('Glass mosaic'))
        self.assertEqual(3, art_material(None))

    def test_step_out_of_a_footprint(self):
        square = [(0, 0), (40, 0), (40, 40), (0, 40)]
        grid = FootGrid([square, [(100, 100), (120, 100), (120, 120), (100, 120)]])
        x, z, moved = grid.step_out(5, 20)
        self.assertTrue(moved)
        self.assertFalse(FootGrid.inside(x, z, square), 'the point stands outside the wall')
        self.assertAlmostEqual(-2.5, x, places=6, msg='past the nearest (west) wall by 2.5 m')
        self.assertAlmostEqual(20, z, places=6)
        self.assertEqual((70, 70, False), grid.step_out(70, 70), 'a point outside every footprint stays')
        m = bake([marker('Inside', lat=39.9455, lon=-75.1447)], [], footprints=[[(-30, -30), (30, -30), (30, 30), (-30, 30)]])
        self.assertEqual([1, 0], m['moved'])
        self.assertFalse(FootGrid.inside(m['m'][0][0], m['m'][0][1], [(-30, -30), (30, -30), (30, 30), (-30, 30)]))

    def test_no_script_tag(self):
        with self.assertRaises(ValueError):
            bake([marker('Bad', markertext='x </script> y')], [])


if __name__ == '__main__':
    unittest.main()
