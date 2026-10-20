"""Round 213 (Mike, with a photograph of Girard Station: "Can we add the stations for the elevated train tracks in Fishtown?
There should be coverings that are lit from underneath and the structure holding up the tracks should be light blue."):
Girard and Berks (rebuilds/elst.js) on the El's own profile (api.elAt), the Frankford leg's steel light blue.

- the stations stand where OSM's cross streets meet the El's centreline, on its straight runs;
- the skip ring is OSM's Berks footprint exactly (the 16 m box that stood round the tracks), and its record's centroid is
  inside it, so the wide loop drops it;
- the app hands the rebuilds elAt, which reads the El's smoothed profile, and paints only the Frankford leg (?elblue=0);
- the roofs' strips take the lamps' photocell and the windows the night."""
import json
import re
import unittest

try:
    from . import _common as C
except ImportError:
    import _common as C


class Stations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rb = C.path('rebuilds/elst.js').read_text(encoding='utf-8')
        cls.src = C.path('app.js').read_text(encoding='utf-8')

    def test_on_the_el_at_the_cross_streets(self):
        at = {k: (float(x), float(z)) for k, x, z in re.findall(r"key: '(\w+)', name: '[^']+', at: \[([-\d.]+), ([-\d.]+)\]", self.rb)}
        self.assertEqual({'girard', 'berks'}, set(at))
        el = json.loads(re.search(r'const EL_TRACK = (\[\[.*?\]\]);', self.src).group(1))[0]
        pts = list(zip(el[0::2], el[1::2]))
        for k, (x, z) in at.items():
            d = min(abs((b[0] - a[0]) * (a[1] - z) - (a[0] - x) * (b[1] - a[1])) / ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
                    for a, b in zip(pts, pts[1:]) if min(a[1], b[1]) - 1 <= z <= max(a[1], b[1]) + 1)
            self.assertLess(d, 1.0, k)

    def test_the_berks_box_is_skipped(self):
        ring = json.loads(re.search(r'const BERKS_FOOT = (\[\[.*?\]\]);', self.rb).group(1))
        if not C.path('scene_wide.json').exists():
            self.skipTest('input absent: scene_wide.json')
        d = json.loads(C.path('scene_wide.json').read_text())
        bl = d['buildings'] if isinstance(d, dict) else d
        b = [q for q in bl if q.get('name') == 'Berks SEPTA MFL Station']
        self.assertEqual(1, len(b))
        self.assertEqual([[round(x, 2), round(z, 2)] for x, z in b[0]['poly']], ring)
        self.assertIn('skip: [BERKS_FOOT],', self.rb)

    def test_the_app_wiring(self):
        s = self.src
        self.assertIn('  function elAt(x, z) {', s)
        self.assertIn('      elAt,   // Round 213', s)
        self.assertIn("const fk = EL_BLUE && corridor++ === 0;", s)   # the Frankford leg only
        self.assertIn("blue('#6aa6b8', 0.88)", s)
        self.assertIn("/[?&]elblue=0\\b/.test(location.search)", s)
        self.assertIn("lit('#fff4de', 2.6, 'lamp', 'strip')", self.rb)
        self.assertIn("lit('#f3d9a8', 0.9, 'night', 'pane')", self.rb)
        self.assertIn('const TB = Math.max(HB - 2.3, g0 + 5.0);', self.rb)   # 5 m over the cross street at least


if __name__ == '__main__':
    unittest.main()
