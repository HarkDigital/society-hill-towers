"""Round 139: 207 E Wildey St is demolished and dug out (Mike, with two photos).

The house is wide.b64 record 74399. The page skips the footprint holding a DEMOLISHED point at run time (a repack
would renumber every later record, and the palette, facade and roof draws are seeded by the record number), cuts
each GROUND_PITS ring out of the drawn ground and builds a closed pit under it. These checks read the packed tier and
the page's own lists: the point names exactly one house, the ring is convex, holds that house and no other, sits
clear of the drawn street, and its party-wall spans lie on the neighbours' walls; and the wiring is in place."""
import json
import math
from pathlib import Path
import re
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_ground_pits
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

ROOT = Path(__file__).resolve().parents[1]


def inside(x, z, poly):
    c = False
    for i in range(len(poly)):
        (xi, zi), (xj, zj) = poly[i], poly[i - 1]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            c = not c
    return c


def centroid(poly):
    a = cx = cz = 0.0
    for i in range(len(poly)):
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % len(poly)]
        k = x0 * z1 - x1 * z0
        a += k; cx += (x0 + x1) * k; cz += (z0 + z1) * k
    return cx / (3 * a), cz / (3 * a)


def seg_dist(p, a, b):
    ax, az = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * az) / (ax * ax + az * az)))
    return math.hypot(p[0] - a[0] - ax * t, p[1] - a[1] - az * t)


class GroundPits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        m = re.search(r'const DEMOLISHED = (\[\[.*?\]\]);', cls.src)
        cls.demolished = json.loads(m.group(1))
        m = re.search(r"const GROUND_PITS = \[\{ name: '([^']+)', ring: (\[\[.*?\]\]),\s*left: (\[[^\]]+\]), right: (\[[^\]]+\]) \}\];", cls.src, re.S)
        cls.name, cls.ring, cls.left, cls.right = m.group(1), json.loads(m.group(2)), json.loads(m.group(3)), json.loads(m.group(4))
        scene = C.walk_scene('wide.b64')
        cls.buildings = [(i, b[1], b[4]) for i, b in enumerate(scene['buildings'])]
        cls.roads = scene['roads']

    def test_the_point_names_one_house(self):
        (px, pz), = self.demolished
        hits = [(i, h) for i, h, poly in self.buildings if inside(px, pz, poly)]
        self.assertEqual(len(hits), 1, hits)
        i, h = hits[0]
        self.assertEqual(i, 74399)
        self.assertAlmostEqual(h, 7.0, places=1)

    def test_ring_is_convex_and_holds_only_that_house(self):
        r = self.ring
        crosses = [(r[(k + 1) % 4][0] - r[k][0]) * (r[(k + 2) % 4][1] - r[(k + 1) % 4][1]) - (r[(k + 1) % 4][1] - r[k][1]) * (r[(k + 2) % 4][0] - r[(k + 1) % 4][0]) for k in range(4)]
        self.assertTrue(all(c > 0 for c in crosses) or all(c < 0 for c in crosses), crosses)   # elPortalClipGround cuts convex rings
        held = [i for i, h, poly in self.buildings if inside(*centroid(poly), r)]
        self.assertEqual(held, [74399])
        # every other house near it stays outside the ring but for a sliver on a shared wall (the rings are rounded to 1 cm)
        for i, h, poly in self.buildings:
            if i == 74399 or abs(poly[0][0] - r[0][0]) > 60 or abs(poly[0][1] - r[0][1]) > 60:
                continue
            for q in poly:
                if inside(q[0], q[1], r):
                    self.assertLess(min(seg_dist(q, r[k], r[(k + 1) % 4]) for k in range(4)), 0.08, (i, q))

    def test_ring_clear_of_the_street(self):
        # the drawn carriageway is w/2 either side of the centreline; the pit must not eat into it
        for n, w, t, pts in self.roads:
            if abs(pts[0][0] - self.ring[0][0]) > 400 or abs(pts[0][1] - self.ring[0][1]) > 400:
                continue
            for q in self.ring:
                d = min(seg_dist(q, pts[k], pts[k + 1]) for k in range(len(pts) - 1))
                self.assertGreater(d, w / 2 + 0.3, (q, w))

    def test_party_wall_spans_sit_on_the_neighbours(self):
        F1, F2, R2, R1 = self.ring
        for (a, b), span, want in (((F1, R1), self.left, 74408), ((F2, R2), self.right, 74404)):
            p0 = (a[0] + (b[0] - a[0]) * span[0], a[1] + (b[1] - a[1]) * span[0])
            p1 = (a[0] + (b[0] - a[0]) * span[1], a[1] + (b[1] - a[1]) * span[1])
            poly = next(poly for i, h, poly in self.buildings if i == want)
            for p in (p0, p1):   # each span end is a corner of the neighbour, to 10 cm
                self.assertLess(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in poly), 0.1, (want, p))

    def test_wiring(self):
        s = self.src
        loop = s[s.index('      const [cx, cz] = polyCentroid(poly);\n      if (DEMOLISHED'):]
        self.assertLess(loop.index('if (DEMOLISHED'), loop.index('if (h >= 45) tallGlow.push'))   # before any consumer
        self.assertIn('if (h <= 45 && t <= 6) wideColK++;', s)   # the far ring's colour reservoir keeps its count
        self.assertIn('.concat(GROUND_PITS.map(p=>({poly:p.ring,bounds:streetBounds(p.ring)}))', s)
        self.assertIn("step('Digging on East Wildey Street', buildGroundPits);", s)
        self.assertLess(s.index("step('Digging on East Wildey Street'"), s.index("step('Sowing the grass'"))   # noSow before the sow
        self.assertIn('noSow(P.ring.map(', s)
        # the floor faces up and every wall strip faces into the pit (review: the weather wrap and the shadow bias read the raw normal)
        self.assertIn('if (up) idx.push(a, b, c, b, d, c); else idx.push(a, c, b, b, c, d);', s)
        self.assertIn('if (nn.count && nn.getX(0) * inward.x + nn.getZ(0) * inward.z < 0)', s)
        self.assertNotIn('—', 'Digging on East Wildey Street')


if __name__ == '__main__':
    unittest.main()
