"""schuylkill.json's water rings must be SIMPLE polygons.

The page triangulates them with earcut, and earcut on a self-intersecting ring leaves whole
pockets untriangulated: the water sheet comes out with holes in it and the carved channel shows
through them as strips of land lying in the river. That shipped from Round 85 to Round 89 (Mike:
"we still have those 3 thin strips of land appearing in this view in the river"). The cause was
the 0.1 m coordinate rounding at emit closing a handful of zero-width spikes in the ring; the
bake despikes now, and this is the guard that keeps the shipped file honest.

No shapely here: the test suite stays on the standard library, so the crossing test is a plain
segment sweep over a 60 m grid.
"""
import math
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_schuylkill
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests


def _seg_cross(a, b, c, d):
    """do segments ab and cd properly cross (sharing an endpoint does not count)"""
    def o(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)
    if a in (c, d) or b in (c, d):
        return False
    o1, o2, o3, o4 = o(a, b, c), o(a, b, d), o(c, d, a), o(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    # collinear overlap counts too: two edges lying on each other is not a simple ring
    if o1 == o2 == o3 == o4 == 0:
        def on(p, q, r):
            return (min(p[0], q[0]) - 1e-9 <= r[0] <= max(p[0], q[0]) + 1e-9
                    and min(p[1], q[1]) - 1e-9 <= r[1] <= max(p[1], q[1]) + 1e-9)
        return on(a, b, c) or on(a, b, d) or on(c, d, a) or on(c, d, b)
    return False


def _crossings(ring, cell=60.0):
    n = len(ring)
    segs = [(tuple(ring[i]), tuple(ring[(i + 1) % n])) for i in range(n)]
    grid = {}
    for i, (a, b) in enumerate(segs):
        x0, x1 = sorted((a[0], b[0]))
        z0, z1 = sorted((a[1], b[1]))
        for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
            for gz in range(int(math.floor(z0 / cell)), int(math.floor(z1 / cell)) + 1):
                grid.setdefault((gx, gz), []).append(i)
    bad = []
    seen = set()
    for ids in grid.values():
        for ii in range(len(ids)):
            for jj in range(ii + 1, len(ids)):
                i, j = ids[ii], ids[jj]
                if j == (i + 1) % n or i == (j + 1) % n:
                    continue
                key = (i, j) if i < j else (j, i)
                if key in seen:
                    continue
                seen.add(key)
                if _seg_cross(segs[i][0], segs[i][1], segs[j][0], segs[j][1]):
                    bad.append((i, j, segs[i][0]))
    return bad


class Schuylkill(unittest.TestCase):
    def test_water_rings_are_simple(self):
        """no ring or island hole in schuylkill.json crosses itself (earcut needs that)"""
        C.require(self, 'schuylkill.json')
        d = C.load_json('schuylkill.json')
        polys = d.get('polys') or []
        self.assertTrue(polys, 'schuylkill.json carries no water polygons')
        for pi, w in enumerate(polys):
            rings = [('ring', w['ring'])] + [('hole %d' % k, h) for k, h in enumerate(w.get('holes') or [])]
            for name, r in rings:
                self.assertGreaterEqual(len(r), 3, 'poly %d %s has %d points' % (pi, name, len(r)))
                self.assertNotEqual(tuple(r[0]), tuple(r[-1]), 'poly %d %s repeats its first point' % (pi, name))
                bad = _crossings(r)
                self.assertEqual([], bad[:4], 'poly %d %s self-intersects at %d place(s), first near %s'
                                 % (pi, name, len(bad), bad[0][2] if bad else None))

    def test_no_needle_spikes(self):
        """a vertex whose neighbours nearly touch is a spike any rounding turns into a crossing"""
        C.require(self, 'schuylkill.json')
        d = C.load_json('schuylkill.json')
        for pi, w in enumerate(d.get('polys') or []):
            for name, r in [('ring', w['ring'])] + [('hole %d' % k, h) for k, h in enumerate(w.get('holes') or [])]:
                n = len(r)
                worst, at = 1e9, None
                for i in range(n):
                    a, b = r[(i - 1) % n], r[(i + 1) % n]
                    dd = math.hypot(a[0] - b[0], a[1] - b[1])
                    if dd < worst:
                        worst, at = dd, r[i]
                self.assertGreater(worst, 0.2, 'poly %d %s has a needle %.3f m wide near %s'
                                   % (pi, name, worst, at))
