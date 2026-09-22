"""The layers panel's bits (Round 83): fourteen keys in the mask's order, the markers and the art
on their own bits with the fourteen-bit link marker, the hash keeping fifteen bits, a row and a
key per layer, and the reset map naming every key. A text check on app.js and template.html."""
import re
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_layers
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

KEYS = ['septa', 'indego', 'flights', 'ships', 'traffic', 'lights', 'streets', 'labels', 'places', 'concerts', 'amtrak', 'closures', 'markers', 'art', 'stops', 'stations', 'civic']   # Round 133 appended three
ROWS = {'btnTransit': 'V', 'btnIndego': 'B', 'btnFlights': 'X', 'btnShips': 'H', 'btnAmtrak': 'K', 'btnConcerts': 'M', 'btnTraffic': 'R',
        'btnClosures': 'U', 'btnMarkers': 'J', 'btnArt': 'O', 'btnLights': 'G', 'btnStreets': 'N', 'btnLabels': 'L', 'btnPlaces': 'P',
        'btnStops': 'C', 'btnStations': 'Y'}


class Layers(unittest.TestCase):
    def setUp(self):
        C.require(self, 'app.js', 'template.html')
        self.src = C.path('app.js').read_text(encoding='utf-8')
        self.tpl = C.path('template.html').read_text(encoding='utf-8')

    def test_mask(self):
        m = re.search(r"const LAYER_KEYS = \[([^\]]+)\];", self.src)
        self.assertIsNotNone(m)
        keys = [k.strip().strip("'") for k in m.group(1).split(',')]
        self.assertEqual(KEYS, keys, 'the mask order is the link format: append, never reorder')
        self.assertIn('const LAYER_MASK_V2 = 1024, LAYER_MASK_V3 = 4096, LAYER_MASK_V4 = 16384, LAYER_MASK_V5 = 131072;', self.src)
        self.assertIn('let m = LAYER_MASK_V5;', self.src, 'a new link carries the seventeen-bit marker alone')
        self.assertIn('(m & LAYER_MASK_V5) ? LAYER_KEYS.length : (m & LAYER_MASK_V4) ? 14 : (m & LAYER_MASK_V3) ? 12 : (m & LAYER_MASK_V2) ? 10 : 9', self.src, 'older links keep their width, newest marker first')
        self.assertIn('out.l = v[0] & 262143;', self.src, 'the hash keeps eighteen bits')
        for k in KEYS:
            self.assertIn("'%s' in f" % k, self.src, 'setLayerFlags does not read ' + k)
            self.assertIn('%s: ' % k, self.src)
        self.assertIn('markers: toggleMarkers, art: toggleArt, stops: toggleStops, stations: toggleStations, civic: toggleCivic', self.src, 'Reset Layers must know every key')

    def test_rows_and_keys(self):
        for btn, key in ROWS.items():
            self.assertRegex(self.tpl, r'id="%s"[^\n]*<kbd>%s</kbd>' % (btn, key), '%s row with its %s key' % (btn, key))
        for key, fn in (('j', 'toggleMarkers'), ('o', 'toggleArt'), ('u', 'toggleClosures'), ('k', 'toggleAmtrak'), ('c', 'toggleStops'), ('y', 'toggleStations')):
            self.assertIn("else if (k === '%s') %s();" % (key, fn), self.src)
        self.assertIn("if ((e.isM ? HMARK.on : PUBART.on) && nearCam(", self.src, 'the reconcile reads the two flags')
        self.assertIn("getElementById('markersCount')", self.src)
        self.assertIn("getElementById('artCount')", self.src)


if __name__ == '__main__':
    unittest.main()
