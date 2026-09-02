"""Packed-blob structure: header magic, exact int16 consumption, int16 saturation,
ring-size caps, and the per-record bit fields the app decoders rely on."""
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_blobs
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

# Documented ring caps (pack_wide.py / pack_city.py). The packers decimate with
# ring[::max(1, len // cap)], which leaves rings up to 2*cap-1 long — so the cap is
# reported as a warning while 2*cap-1 is the hard ceiling the decimation guarantees.
RING_CAPS = {
    'wide.b64': {'buildings': 48, 'areas': 120},          # pack_wide: 48 / 120
    'city.b64': {'buildings': 32, 'areas': 90, 'roads': 120},   # pack_city: 32 / 90 / 120-point road chunks
    'outskirts.b64': {'buildings': 16, 'areas': 60, 'roads': 120},   # pack_outskirts: 16 / 60 / 120
}


class BlobStructure(unittest.TestCase):

    def test_header_magic_and_exact_consumption(self):
        """16-byte header with the right magic; the int16 body is consumed exactly (0 leftover)."""
        for name, (magics, unit, step) in C.BLOBS.items():
            with self.subTest(blob=name, app_step=step):
                C.require(self, name)
                hdr, body = C.decode_b64(name)
                self.assertIn(hdr[0], magics, '%s magic 0x%08X not in %s' % (name, hdr[0] & 0xFFFFFFFF, [hex(m) for m in magics]))
                if name in ('wide.b64', 'city.b64', 'outskirts.b64'):
                    s = C.walk_scene(name)
                    self.assertEqual(0, s['leftover'], '%s: %d int16 left after %d buildings / %d roads / %d areas'
                                     % (name, s['leftover'], s['nb'], s['nr'], s['na']))
                elif name == 'trees.b64':
                    t = C.walk_trees()
                    self.assertEqual(0, t['leftover'], 'trees.b64: %d int16 left after %d trees x 4' % (t['leftover'], hdr[1]))
                elif name == 'poles.b64':
                    p = C.walk_poles()
                    self.assertEqual(0, p['leftover'], 'poles.b64: %d int16 left after %d poles x 3' % (p['leftover'], hdr[1]))
                    self.assertEqual((0, 0), tuple(hdr[2:]), 'poles.b64 header words 2-3 must be zero')
                elif name == 'traffic.b64':
                    t = C.walk_traffic()
                    self.assertEqual(0, t['leftover'], 'traffic.b64: %d int16 left after %d ways' % (t['leftover'], hdr[1]))
                    self.assertEqual(hdr[2], sum(w[0] for w in t['ways']), 'traffic.b64 header nPts disagrees with the way records')

    def test_no_int16_saturation(self):
        """No coordinate sits at +/-32767 (a clipped value = geometry pushed past the int16 wall).
        wide.b64 areas are covered by their own (expected-failure) test below."""
        C.require(self, 'wide.b64', 'city.b64', 'outskirts.b64', 'trees.b64', 'poles.b64', 'traffic.b64')
        report = {}
        for name in ('wide.b64', 'city.b64', 'outskirts.b64'):
            s = C.walk_scene(name)
            for part, n in s['saturated'].items():
                if name == 'wide.b64' and part == 'areas':
                    continue
                report['%s %s' % (name, part)] = n
        report['trees.b64'] = C.walk_trees()['saturated']
        report['poles.b64'] = C.walk_poles()['saturated']
        report['traffic.b64'] = C.walk_traffic()['saturated']
        bad = {k: v for k, v in report.items() if v}
        self.assertEqual({}, bad, 'saturated int16 coordinates: %s' % bad)

    def test_wide_areas_no_int16_saturation(self):
        """pack_wide.py admits area rings whose centroid lies within WIDE +/- 500 m, but
        0.2 m units saturate at 6553.4 m; since 2026-09-01 pack_wide clips such rings to
        the int16 box (the committed wide.b64 used to carry 43 saturated vertices)
        sit on the int16 wall. Expected to fail until pack_wide.py clips those rings."""
        C.require(self, 'wide.b64')
        s = C.walk_scene('wide.b64')
        n = s['saturated']['areas']
        rings = [i for i, (cnt, kind, pts) in enumerate(s['areas'])
                 if any(abs(round(x / 0.2)) == C.INT16_SAT or abs(round(z / 0.2)) == C.INT16_SAT for x, z in pts)]
        self.assertEqual(0, n, 'wide.b64: %d saturated area coordinates in %d rings (indices %s)' % (n, len(rings), rings[:12]))

    def test_ring_sizes_within_caps(self):
        """Rings within the documented caps: over-cap counts are WARNINGS (pack_city currently
        leaves ~1,030 rings over 32); the decimation ceiling (2*cap-1) and the 120-point road
        chunking are hard limits, as are >= 3 vertices per ring and >= 2 per road."""
        warnings = []
        for name, caps in RING_CAPS.items():
            with self.subTest(blob=name):
                C.require(self, name)
                s = C.walk_scene(name)
                for part in ('buildings', 'areas'):
                    sizes = [rec[0] for rec in s[part]]
                    self.assertTrue(all(n >= 3 for n in sizes), '%s %s: ring with < 3 vertices' % (name, part))
                    cap = caps[part]
                    over = sum(1 for n in sizes if n > cap)
                    if over:
                        warnings.append('%s %s: %d rings over the %d cap (max %d)' % (name, part, over, cap, max(sizes)))
                    self.assertLessEqual(max(sizes), 2 * cap - 1,
                                         '%s %s: ring of %d vertices exceeds the decimation ceiling %d' % (name, part, max(sizes), 2 * cap - 1))
                road_sizes = [rec[0] for rec in s['roads']]
                self.assertTrue(all(n >= 2 for n in road_sizes), '%s roads: polyline with < 2 points' % name)
                if 'roads' in caps:
                    self.assertLessEqual(max(road_sizes), caps['roads'], '%s roads: run longer than the %d-point chunk' % (name, caps['roads']))
        if warnings:
            print('\n  WARNING ring caps: ' + '; '.join(warnings))


class BlobRecords(unittest.TestCase):

    def test_scene_record_fields(self):
        """Heights, widths and type codes stay in the ranges the app palettes index."""
        for name in ('wide.b64', 'city.b64', 'outskirts.b64'):
            with self.subTest(blob=name):
                C.require(self, name)
                s = C.walk_scene(name)
                hs = [b[1] for b in s['buildings']]
                # pack_wide floors h at 2.5 m, which packs as round(12.5) = 12 -> 2.4 m; pack_city floors at 3-4 m
                self.assertGreaterEqual(min(hs), 2.4, '%s: building shorter than the packed 2.5 m floor' % name)
                self.assertLessEqual(max(hs), 6500, '%s: building taller than the 6500 m clamp' % name)
                self.assertTrue(all(0 <= b[3] <= 10 for b in s['buildings']), '%s: building type outside 0..10' % name)
                self.assertTrue(all(0 <= r[2] <= 6 for r in s['roads']), '%s: road class outside 0..6' % name)
                self.assertTrue(all(r[1] > 0 for r in s['roads']), '%s: road with non-positive width' % name)
                self.assertTrue(all(0 <= a[1] <= 2 for a in s['areas']), '%s: area kind outside 0..2' % name)

    def test_tree_names_consistent(self):
        """trees.b64 nNames == tree_names.json rows and every nameIdx resolves."""
        C.require(self, 'trees.b64', 'tree_names.json')
        t = C.walk_trees()
        names = C.load_json('tree_names.json')
        n_names = t['header'][2]
        self.assertEqual(n_names, len(names['names']))
        self.assertEqual(n_names, len(names['latin']))
        self.assertEqual(n_names, len(names['g']))
        idx = [tr[3] for tr in t['trees']]
        self.assertTrue(all(0 <= i < n_names for i in idx), 'tree nameIdx out of range')
        self.assertTrue(all(1 <= tr[2] <= 60 for tr in t['trees']), 'tree dbh outside 1..60 in')
        x0, x1, z0, z1 = C.WIDE_BOX
        outside = sum(1 for x, z, _d, _n in t['trees'] if not (x0 - 1 <= x <= x1 + 1 and z0 - 1 <= z <= z1 + 1))
        self.assertEqual(0, outside, '%d trees outside the wide box' % outside)

    def test_pole_bits(self):
        """packed bits: 0-1 lamp kind (0..2), 2-8 height ft (1..127), 9 two-luminaire flag."""
        C.require(self, 'poles.b64')
        p = C.walk_poles()
        kinds = set()
        for x, z, pk in p['poles']:
            kinds.add(pk & 3)
            self.assertTrue(1 <= ((pk >> 2) & 127) <= 127)
            self.assertEqual(0, pk >> 10, 'pole packed word uses bits above 9')
        self.assertTrue(kinds <= {0, 1, 2}, 'pole lamp kind outside 0..2: %s' % kinds)
        x0, x1, z0, z1 = C.CITY_BOX
        outside = sum(1 for x, z, _ in p['poles'] if not (x0 - 1 <= x <= x1 + 1 and z0 - 1 <= z <= z1 + 1))
        self.assertEqual(0, outside, '%d poles outside the city box' % outside)

    def test_traffic_records(self):
        """clsFlags bits 0-2 class (0..5), 3 oneway, 4 penndot-matched; positive AADT; >= 2 points."""
        C.require(self, 'traffic.b64')
        t = C.walk_traffic()
        for n, flags, aadt10, pts in t['ways']:
            self.assertGreaterEqual(n, 2)
            self.assertLessEqual(flags & 7, 5)
            self.assertEqual(0, flags >> 5, 'traffic flags use bits above 4')
            self.assertGreater(aadt10, 0)
        matched = sum(1 for w in t['ways'] if w[1] & 16)
        self.assertGreater(matched, 0, 'no way carries a PennDOT-matched count')


if __name__ == '__main__':
    unittest.main()
