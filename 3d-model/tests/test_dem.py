"""Elevation grids: structure, and the seams between the nested grids the app samples
in priority order (dem.json 25 m core -> dem_wide 50 m -> dem_south -> dem_nw -> dem_city 150 m)."""
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_dem
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

GRIDS = ('dem.json', 'dem_wide.json', 'dem_south.json', 'dem_nw.json', 'dem_city.json')


def border_points(g, step):
    x0, x1, z0, z1 = C.grid_extent(g)
    pts = []
    x = x0
    while x <= x1:
        pts.append((x, z0))
        pts.append((x, z1))
        x += step
    z = z0
    while z <= z1:
        pts.append((x0, z))
        pts.append((x1, z))
        z += step
    return pts


def seam_diffs(inner, outer, step=5.0):
    diffs = []
    for x, z in border_points(inner, step):
        a = C.bilinear(inner, x, z)
        b = C.bilinear(outer, x, z)
        if a is None or b is None:
            continue
        diffs.append((abs(a - b), x, z))
    diffs.sort()
    return diffs


class DemGrids(unittest.TestCase):

    def test_grid_structure(self):
        for name in GRIDS:
            with self.subTest(grid=name):
                C.require(self, name)
                g = C.load_json(name)
                for k in ('x0', 'z0', 'cell', 'nx', 'nz', 'rows'):
                    self.assertIn(k, g)
                self.assertGreater(g['cell'], 0)
                self.assertEqual(g['nz'], len(g['rows']), '%s: nz != len(rows)' % name)
                self.assertTrue(all(len(r) == g['nx'] for r in g['rows']), '%s: a row is not nx wide' % name)
                nulls = sum(1 for r in g['rows'] for v in r if v is None)
                vals = [v for r in g['rows'] for v in r if v is not None]
                self.assertTrue(vals, '%s: no elevation samples at all' % name)
                self.assertLess(nulls / (g['nx'] * g['nz']), 0.02, '%s: %d null cells' % (name, nulls))
                # NED reads the dredged Delaware channel down to about -32 m; Chestnut Hill tops out near 135 m
                self.assertTrue(-50 <= min(vals) and max(vals) <= 250,
                                '%s: elevations %.1f..%.1f outside -50..250 m ASL' % (name, min(vals), max(vals)))

    def test_core_wide_seam(self):
        """Bilinear difference along the border of dem.json (25 m core) against dem_wide.json
        (50 m): p90 must stay under 0.5 m; the max is reported (2.38 m at the south edge)."""
        C.require(self, 'dem.json', 'dem_wide.json')
        diffs = seam_diffs(C.load_json('dem.json'), C.load_json('dem_wide.json'))
        self.assertGreater(len(diffs), 100, 'the core border barely overlaps the wide grid')
        vals = [d[0] for d in diffs]
        p90 = C.percentile(vals, 0.90)
        mx = diffs[-1]
        print('\n  dem seam core/wide: n=%d p50=%.3f p90=%.3f p95=%.3f max=%.2f m at (%g, %g)'
              % (len(vals), C.percentile(vals, 0.5), p90, C.percentile(vals, 0.95), mx[0], mx[1], mx[2]))
        self.assertLess(p90, 0.5, 'core/wide DEM seam p90 = %.3f m (max %.2f m at (%g, %g))' % (p90, mx[0], mx[1], mx[2]))

    def test_nw_patch_feathers_to_city(self):
        """fetch_dem_nw.py blends the patch to dem_city's bilinear value over its outer
        250 m, so on the patch border the two grids must agree (2-dp rounding aside)."""
        C.require(self, 'dem_nw.json', 'dem_city.json')
        diffs = seam_diffs(C.load_json('dem_nw.json'), C.load_json('dem_city.json'), step=50.0)
        self.assertGreater(len(diffs), 100)
        mx = diffs[-1]
        self.assertLess(mx[0], 0.02, 'dem_nw border departs from dem_city by %.3f m at (%g, %g)' % mx)

    def test_wide_city_seam(self):
        """The 50 m wide grid against the 150 m city grid along the wide border: a coarse
        pair (p90 2.4 m, max 8.8 m at the SW corner today), so only a loose p90 bound (4 m)
        guards against a refetched grid landing on the wrong datum; the max is reported."""
        C.require(self, 'dem_wide.json', 'dem_city.json')
        diffs = seam_diffs(C.load_json('dem_wide.json'), C.load_json('dem_city.json'), step=10.0)
        self.assertGreater(len(diffs), 100)
        vals = [d[0] for d in diffs]
        p90 = C.percentile(vals, 0.9)
        print('\n  dem seam wide/city: n=%d p50=%.2f p90=%.2f max=%.2f m at (%g, %g)'
              % (len(vals), C.percentile(vals, 0.5), p90, diffs[-1][0], diffs[-1][1], diffs[-1][2]))
        self.assertLess(p90, 4.0, 'wide/city DEM seam p90 = %.2f m' % p90)


if __name__ == '__main__':
    unittest.main()
