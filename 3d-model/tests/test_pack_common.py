"""pack_common.py (Round 71): the building packers' shared guards against walls that share
a plane. dedupe_stacked keeps the taller of two records on one footprint; nudge_coplanar
insets the smaller of two records whose walls lie on one plane facing the same way, by the
inset the packer passes, and leaves party walls (opposite normals) alone."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pack_common import dedupe_stacked, inset_ring, nudge_coplanar   # noqa: E402


def square(x0, z0, w, ccw=True):
    r = [(x0, z0), (x0 + w, z0), (x0 + w, z0 + w), (x0, z0 + w)]
    return r if ccw else r[::-1]


def item(ring, h, mh=0.0):
    n = len(ring)
    a2 = sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1] for i in range(n))
    cx = sum(p[0] for p in ring) / n
    cz = sum(p[1] for p in ring) / n
    return (cx, cz, abs(a2) / 2, float(h), float(mh), ['t', [tuple(p) for p in ring]])


class DedupeStacked(unittest.TestCase):
    def test_keeps_the_taller_of_two_records_on_one_footprint(self):
        items = [item(square(0, 0, 20), 30), item(square(0.5, 0.5, 20), 60)]
        kept, dropped = dedupe_stacked(items)
        self.assertEqual(dropped, 1)
        self.assertEqual([it[3] for it in kept], [60.0])

    def test_leaves_neighbours_alone(self):
        items = [item(square(0, 0, 20), 30), item(square(25, 0, 20), 30)]
        kept, dropped = dedupe_stacked(items)
        self.assertEqual(dropped, 0)
        self.assertEqual(len(kept), 2)


class NudgeCoplanar(unittest.TestCase):
    def test_insets_the_smaller_record_sharing_a_plane(self):
        big = item(square(0, 0, 40), 12)                 # a block strip
        small = item(square(0, 0, 10), 60)               # a tower flush with its street face
        n = nudge_coplanar([big, small], 1.05)
        self.assertEqual(n, 1)
        ring = small[5][1]
        # every vertex moved 1.05 m inward: the ring is now the 1.05-inset square
        xs = sorted(p[0] for p in ring)
        self.assertAlmostEqual(xs[0], 1.05, places=6)
        self.assertAlmostEqual(xs[-1], 10 - 1.05, places=6)
        self.assertEqual(big[5][1], square(0, 0, 40))    # the larger record is untouched

    def test_party_walls_face_opposite_ways_and_stay(self):
        a = item(square(0, 0, 10), 12)
        b = item(square(10, 0, 10), 12)                  # shares x = 10 with a, normals opposed
        n = nudge_coplanar([a, b], 1.05)
        self.assertEqual(n, 0)

    def test_the_inset_is_the_packers_own(self):
        big = item(square(0, 0, 40), 12)
        small = item(square(0, 0, 10), 60)
        nudge_coplanar([big, small], 0.4)
        self.assertAlmostEqual(min(p[0] for p in small[5][1]), 0.4, places=6)


class InsetRing(unittest.TestCase):
    def test_square_shrinks_by_d_each_side(self):
        r = inset_ring(square(0, 0, 10), 1.0)
        self.assertAlmostEqual(min(p[0] for p in r), 1.0, places=6)
        self.assertAlmostEqual(max(p[1] for p in r), 9.0, places=6)
        r2 = inset_ring(square(0, 0, 10, ccw=False), 1.0)   # winding does not matter
        self.assertAlmostEqual(min(p[0] for p in r2), 1.0, places=6)


if __name__ == '__main__':
    unittest.main()
