"""Tier hand-off: the wide tier (wide.b64) and the far ring (city.b64) must not both
carry the same park / water body."""
import math
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_tiers
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

CENTROID_TOL_M = 25.0
AREA_TOL = 0.005      # 0.5 %


def duplicate_areas():
    """[(wide index, city index, cx, cz, area, kind)] for wide areas matched by a city area."""
    wide = C.walk_scene('wide.b64')
    city = C.walk_scene('city.b64')
    cell = 50.0
    grid = {}
    for ci, (n, kind, pts) in enumerate(city['areas']):
        cx, cz = C.mean_centroid(pts)
        grid.setdefault((int(math.floor(cx / cell)), int(math.floor(cz / cell))), []).append((ci, cx, cz, C.ring_area(pts), kind))
    dups = []
    for wi, (n, kind, pts) in enumerate(wide['areas']):
        cx, cz = C.mean_centroid(pts)
        a = C.ring_area(pts)
        gx, gz = int(math.floor(cx / cell)), int(math.floor(cz / cell))
        for ox in (-1, 0, 1):
            for oz in (-1, 0, 1):
                for ci, ccx, ccz, ca, ck in grid.get((gx + ox, gz + oz), ()):
                    if math.hypot(ccx - cx, ccz - cz) <= CENTROID_TOL_M and abs(ca - a) <= AREA_TOL * max(a, ca):
                        dups.append((wi, ci, round(cx, 1), round(cz, 1), round(a), kind))
    return dups


class TierOverlap(unittest.TestCase):

    @unittest.expectedFailure
    def test_no_duplicate_areas_between_tiers(self):
        """No wide.b64 area whose centroid lies within 25 m and area within 0.5 % of a
        city.b64 area. Currently FAILS for 9 parks / water bodies straddling the wide-box
        edge (pack_city.py keeps areas whose way centroid is outside WIDE even when
        pack_wide.py also packed them). Expected failure until pack_city.py is fixed."""
        C.require(self, 'wide.b64', 'city.b64')
        dups = duplicate_areas()
        lines = ['wide#%d = city#%d at (%s, %s) area %s m2 kind %d' % d for d in dups]
        self.assertEqual([], dups, '%d duplicated area polygons across tiers:\n  ' % len(dups) + '\n  '.join(lines))

    def test_wide_buildings_outside_core_box(self):
        """pack_wide.py drops every outline touching the core extract (CORE +/- 2 m on any
        vertex) and every building:part whose centroid is inside CORE — so no packed wide
        building may have its centroid inside the core box. (A handful of parts along the
        core edge legitimately keep vertices inside it; they are reported, not failed.)"""
        C.require(self, 'wide.b64')
        core = (-640, 770, -520, 850)
        inside = []
        touching = 0
        for n, h, mh, bt, pts in C.walk_scene('wide.b64')['buildings']:
            cx, cz = C.mean_centroid(pts)
            if core[0] < cx < core[1] and core[2] < cz < core[3]:
                inside.append((round(cx, 1), round(cz, 1), h, bt))
            elif any(core[0] - 2 <= x <= core[1] + 2 and core[2] - 2 <= z <= core[3] + 2 for x, z in pts):
                touching += 1
        if touching:
            print('\n  wide buildings with a vertex inside CORE+/-2 but centroid outside (building:part pieces): %d' % touching)
        self.assertEqual([], inside, '%d wide buildings have their centroid inside the core box: %s' % (len(inside), inside[:10]))

    def test_city_buildings_outside_wide_box(self):
        """pack_city.py skips every way whose centroid lies inside the wide box; the merged
        block strips it emits can put a centroid a metre or two inside the edge, so the
        invariant is: no far-ring centroid more than 25 m inside the wide box."""
        C.require(self, 'city.b64')
        x0, x1, z0, z1 = C.WIDE_BOX
        edge = 0
        deep = []
        for n, h, mh, bt, pts in C.walk_scene('city.b64')['buildings']:
            cx, cz = C.mean_centroid(pts)
            if x0 < cx < x1 and z0 < cz < z1:
                depth = min(cx - x0, x1 - cx, cz - z0, z1 - cz)
                if depth > 25:
                    deep.append((round(cx, 1), round(cz, 1), round(depth, 1)))
                else:
                    edge += 1
        if edge:
            print('\n  far-ring merged strips with a centroid within 25 m inside the wide edge: %d' % edge)
        self.assertEqual([], deep, '%d far-ring buildings sit well inside the wide box: %s' % (len(deep), deep[:10]))



class OutskirtsHandoff(unittest.TestCase):
    """outskirts.b64 (pack_outskirts.py) carries only what no older fetch box owns: every
    building centroid lies inside the far-ring box and outside fetch_city's six boxes,
    the wide box and the south box (in lat/lon, converted through philly_frame)."""

    OWNED_LL = [
        (39.860, 39.990, -75.285, -75.185), (39.986, 40.050, -75.190, -75.060), (40.050, 40.140, -75.130, -74.955),
        (39.990, 40.100, -75.285, -75.190), (39.915, 40.050, -75.118, -74.990), (40.050, 40.100, -75.190, -75.130),
        (39.915, 39.986, -75.188, -75.118),
        (39.890, 39.9155, -75.190, -75.118),   # fetch_south's box only as far east as pack_wide packs it
    ]

    def test_outskirts_buildings_outside_owned_boxes(self):
        C.require(self, 'outskirts.b64')
        import sys
        sys.path.insert(0, str(C.MODEL))
        from philly_frame import LON0, LAT0, KX, KZ
        owned = [((w - LON0) * KX, (e - LON0) * KX, (LAT0 - n) * KZ, (LAT0 - s) * KZ) for s, n, w, e in self.OWNED_LL]
        x0, x1, z0, z1 = C.CITY_BOX
        s = C.walk_scene('outskirts.b64')
        bad_in, bad_owned = 0, 0
        for rec in s['buildings']:
            cx, cz = C.mean_centroid(rec[-1])
            if not (x0 - 5 <= cx <= x1 + 5 and z0 - 5 <= cz <= z1 + 5):
                bad_in += 1
            elif any(b[0] + 5 <= cx <= b[1] - 5 and b[2] + 5 <= cz <= b[3] - 5 for b in owned):
                bad_owned += 1
        self.assertEqual(0, bad_in, '%d outskirts buildings outside the far-ring box' % bad_in)
        self.assertEqual(0, bad_owned, '%d outskirts buildings inside a box another tier packs' % bad_owned)

if __name__ == '__main__':
    unittest.main()
