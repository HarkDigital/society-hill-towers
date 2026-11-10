"""Round 226: Camden at its measured heights, and the guard for any repack that is meant to move heights only.

The City's footprint heights stop at the city line, so every building east of the Delaware stood at process_osm's
default for its kind (614 of the 1,195 between x 1,250 and 2,400 at exactly 10.5 m). lidar_join.py now gives a building
the City join leaves unmeasured, standing outside the city line, the citywide roof pass's own height for its OSM way
(lidar_city_roofs.json), and writes every such row to lidar_east_heights.json. pack_wide.py --against <the blob it
replaces> then refuses a pack that differs in anything but height words, and writes wide_repack.json.

The page seeds every wide record's wall colour, style, roof lottery and reservoir draw from its RECORD NUMBER, and
wide_walls.b64 rides the same order, so these checks hold the committed wide.b64 to exactly this:
  - it is Round 225's blob (PREDECESSOR, a sha256 of the decoded bytes) with the height words wide_repack.json lists
    put back: same record count, same order, same rings, types, roof words, roads and areas, byte for byte;
  - every changed record stands east of the river (outside city_limit.json's city line), none west of it;
  - every changed height is a row of lidar_east_heights.json, and every row is the roof pass's own number;
  - a record lifted over the 45 m line is named in app.js's WIDE_COLK_KEEP, so the far ring's colour reservoir
    counts as it did;
  - Camden City Hall's whole footprint is not a 113 m slab.
A LATER heights-only repack packs with --against a copy of the then-committed wide.b64, commits the wide_repack.json
that writes, and moves PREDECESSOR to that file's "against" in the same commit; a repack that is NOT heights-only
re-deals the tier's look and has to say so, and retire the first check, on purpose."""
import base64
import hashlib
import json
import os
import re
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from pack_common import PITCH_BITS, repack_diff, walk_packed   # noqa: E402

try:
    from . import _common as C          # python3 -m unittest tests.test_wide_repack
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

# sha256 of the DECODED bytes of the wide.b64 the committed one was packed against: Round 225's, commit e4b6a2f
# (the base64 text's own sha256 there is 791197d7d6690f684fa8bb06ee377f86b49ab44fabe1db0b155b9daa1aa60dc4)
PREDECESSOR = '6098ce3c8c339ae6eebaf6b25b27878cb35f2800921260d273c4467aa2d42144'
EAST_X = 1000.0            # lidar_join.py's belt
WIDE_X1 = 2300.0           # pack_wide.py's WIDE box, east edge


def blob(nb_recs, roads=(4, 80, 5, 0, 0, 10, 0, 10, 10, 0, 10), areas=(3, 0, 0, 0, 5, 0, 5, 5)):
    """A packed tier from [(h word, minH word, type, attr, roof, [(x, z) words])] plus one road and one area."""
    body = []
    for h, mh, t, attr, roof, pts in nb_recs:
        body += [len(pts), h, mh, t, attr, roof] + [v for p in pts for v in p]
    body += list(roads) + list(areas)
    return struct.pack('<4i', 0x5348545D, len(nb_recs), 1, 1) + struct.pack('<%dh' % len(body), *body)


SQ = [(0, 0), (50, 0), (50, 50), (0, 50)]
SQ2 = [(100, 0), (150, 0), (150, 50), (100, 50)]
ATTR = 3 | (2 << 3) | (5 << 6) | (9 << 10)      # u, mat, era, a storey pitch


def point_in_ring(x, z, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, zi = ring[i]
        xj, zj = ring[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            inside = not inside
        j = i
    return inside


class RepackDiff(unittest.TestCase):
    """pack_common.repack_diff on synthetic blobs: heights pass, everything else is named."""

    def base(self):
        return [(60, 0, 1, ATTR, 27, SQ), (65, 0, 0, -1, -1, SQ2), (300, 50, 3, -1, -1, SQ)]

    def test_identical_blobs_have_no_changes_and_no_problems(self):
        b = blob(self.base())
        self.assertEqual(repack_diff(b, b), ([], []))

    def test_a_height_word_is_a_change_and_nothing_else(self):
        new = self.base()
        new[1] = (271,) + new[1][1:]
        changes, problems = repack_diff(blob(self.base()), blob(new))
        self.assertEqual(problems, [])
        self.assertEqual(changes, [[1, 25.0, 5.0, 65, 271, -1, -1]])       # the ring's vertex mean at 0.2 m a word

    def test_the_storey_pitch_may_move_with_its_height(self):
        new = self.base()
        new[0] = (75, 0, 1, (ATTR & ~PITCH_BITS) | (14 << 10), 27, SQ)
        changes, problems = repack_diff(blob(self.base()), blob(new))
        self.assertEqual(problems, [])
        self.assertEqual([c[:1] + c[3:] for c in changes], [[0, 60, 75, ATTR, (ATTR & ~PITCH_BITS) | (14 << 10)]])

    def test_a_pitch_that_moves_alone_is_a_problem(self):
        new = self.base()
        new[0] = (60, 0, 1, (ATTR & ~PITCH_BITS) | (14 << 10), 27, SQ)
        changes, problems = repack_diff(blob(self.base()), blob(new))
        self.assertEqual(changes, [])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('storey pitch moved', problems[0])

    def test_every_other_word_is_a_problem(self):
        cases = {
            'the attribute word differs outside the storey pitch': (0, (60, 0, 1, ATTR ^ 1, 27, SQ)),
            'attribute word differs': (1, (65, 0, 0, ATTR, -1, SQ2)),                 # none -> some
            'type differs': (1, (65, 0, 4, -1, -1, SQ2)),
            'roof word differs': (0, (60, 0, 1, ATTR, 28, SQ)),
            'minimum height differs': (2, (300, 55, 3, -1, -1, SQ)),
            'the ring differs': (1, (65, 0, 0, -1, -1, [(100, 0), (150, 0), (150, 51), (100, 50)])),
        }
        for want, (i, rec) in cases.items():
            new = self.base()
            new[i] = rec
            changes, problems = repack_diff(blob(self.base()), blob(new))
            self.assertTrue(any(want in p for p in problems), (want, problems))

    def test_a_dropped_added_or_swapped_record_is_a_problem(self):
        old = self.base()
        for new in (old[:2], old + [(40, 0, 1, -1, -1, SQ2)], [old[1], old[0], old[2]]):
            changes, problems = repack_diff(blob(old), blob(new))
            self.assertTrue(problems, new)
        # a reorder is caught at its first misplaced ring, and the walk stops there
        changes, problems = repack_diff(blob(old), blob([old[1], old[0], old[2]]))
        self.assertTrue(any('ring differs' in p for p in problems), problems)

    def test_a_road_or_an_area_is_a_problem(self):
        old = blob(self.base())
        for kw in ({'roads': (4, 90, 5, 0, 0, 10, 0, 10, 10, 0, 10)}, {'areas': (3, 1, 0, 0, 5, 0, 5, 5)}):
            changes, problems = repack_diff(old, blob(self.base(), **kw))
            self.assertEqual(changes, [])
            self.assertTrue(any('roads and areas' in p for p in problems), problems)

    def test_a_blob_that_does_not_walk_is_a_problem(self):
        changes, problems = repack_diff(blob(self.base()), blob(self.base())[:40])
        self.assertTrue(problems)


class CamdenHeights(unittest.TestCase):
    """The committed wide.b64 against Round 225's, the join's table and the roof pass."""

    @classmethod
    def setUpClass(cls):
        need = ('wide.b64', 'wide_repack.json', 'lidar_east_heights.json', 'lidar_city_roofs.json', 'city_limit.json',
                'scene_wide.json', 'scene_south.json', 'app.js', 'lidar_join.py', 'pack_wide.py')
        missing = [n for n in need if not C.path(n).exists()]
        if missing:
            raise unittest.SkipTest('input absent: ' + ', '.join(missing))
        cls.buf = base64.b64decode(C.path('wide.b64').read_text())
        cls.hdr, cls.body, cls.offs = walk_packed(cls.buf)
        cls.rep = json.loads(C.path('wide_repack.json').read_text())
        cls.changes = cls.rep['changes']
        cls.rows = json.loads(C.path('lidar_east_heights.json').read_text())['rows']
        cls.roofs = json.loads(C.path('lidar_city_roofs.json').read_text())
        cls.line = json.loads(C.path('city_limit.json').read_text())['city']
        cls.app = C.path('app.js').read_text()
        cls.join = C.path('lidar_join.py').read_text()

    def ring(self, i):
        a = self.offs[i]
        n = self.body[a]
        return [(self.body[a + 6 + 2 * k] * 0.2, self.body[a + 7 + 2 * k] * 0.2) for k in range(n)]

    def east(self, x, z):
        return x > EAST_X and not point_in_ring(x, z, self.line)

    # ---- the blob is its predecessor with height words changed, and nothing else
    def test_the_repack_file_describes_the_committed_blob(self):
        self.assertEqual(hashlib.sha256(self.buf).hexdigest(), self.rep['packed'],
                         'wide.b64 is not the pack wide_repack.json describes: repack with --against (see this file\'s docstring)')
        self.assertEqual(self.rep['against'], PREDECESSOR)

    def test_putting_the_listed_height_words_back_gives_the_predecessor_byte_for_byte(self):
        body = list(self.body)
        seen = set()
        for rec, cx, cz, h0, h1, a0, a1 in self.changes:
            self.assertNotIn(rec, seen)
            seen.add(rec)
            a = self.offs[rec]
            self.assertEqual((body[a + 1], body[a + 4]), (h1, a1), rec)
            self.assertNotEqual(h0, h1, rec)
            body[a + 1], body[a + 4] = h0, a0
        old = self.buf[:16] + struct.pack('<%dh' % len(body), *body)
        self.assertEqual(len(old), len(self.buf))
        self.assertEqual(hashlib.sha256(old).hexdigest(), PREDECESSOR,
                         'wide.b64 differs from Round 225\'s in more than the listed height words: a record count, the '
                         'order, a ring, a type, a roof word, a road or an area moved')
        # and the walker agrees with the bytes: the same test the packer ran
        changes, problems = repack_diff(old, self.buf)
        self.assertEqual(problems, [])
        self.assertEqual(changes, self.changes)

    def test_only_height_words_moved(self):
        # New Jersey has no OPA facade word, so not even the storey pitch moved in this repack
        for rec, cx, cz, h0, h1, a0, a1 in self.changes:
            self.assertEqual(a0, a1, rec)
            self.assertEqual((a0 ^ a1) & ~PITCH_BITS, 0, rec)
        self.assertEqual(self.hdr[1:], (112752, 6651, 1163))       # Round 225's counts
        self.assertEqual(len(self.changes), 553)

    def test_the_wall_colours_still_ride_the_same_records(self):
        raw = base64.b64decode(C.path('wide_walls.b64').read_text())
        self.assertEqual(struct.unpack_from('<4i', raw, 0)[1], self.hdr[1])

    # ---- where
    def test_every_changed_record_stands_east_of_the_river(self):
        for rec, cx, cz, h0, h1, a0, a1 in self.changes:
            ring = self.ring(rec)
            mx = sum(p[0] for p in ring) / len(ring)
            mz = sum(p[1] for p in ring) / len(ring)
            self.assertAlmostEqual(mx, cx, delta=0.06)
            self.assertAlmostEqual(mz, cz, delta=0.06)
            self.assertTrue(self.east(mx, mz), 'record %d at (%.0f, %.0f) is not east of the Delaware' % (rec, mx, mz))
            self.assertGreater(min(p[0] for p in ring), EAST_X, rec)
            self.assertFalse(any(point_in_ring(p[0], p[1], self.line) for p in ring), rec)

    def test_no_record_west_of_the_river_changed(self):
        changed = {c[0] for c in self.changes}
        west = 0
        for i in range(self.hdr[1]):
            ring = self.ring(i)
            mx = sum(p[0] for p in ring) / len(ring)
            mz = sum(p[1] for p in ring) / len(ring)
            if not self.east(mx, mz):
                west += 1
                self.assertNotIn(i, changed, 'record %d at (%.0f, %.0f), west of the river, changed' % (i, mx, mz))
        self.assertGreater(west, 110000)       # the tier is Philadelphia's: the east bank is about 1,200 records

    # ---- what: the join's table, and the roof pass behind it
    def pair_rows(self):
        """Each changed record with its row of the join's table: the row whose two heights pack to the record's two
        words and whose point (the scene polygon's vertex mean, rounded to a metre) lies in the record's box, the
        nearest first. Returns (pairs, records without a row, rows inside the tier whose word moved without a record)."""
        def word(h):
            return int(round(max(2.5, min(6500, h)) * 5))      # pack_wide.py: clip(h * 5) on h = max(2.5, min(6500, b['h']))
        free = {}
        for r in self.rows:
            if word(r[4]) != word(r[5]):
                free.setdefault((word(r[4]), word(r[5])), []).append(r)
        pairs, orphans = [], []
        for c in self.changes:
            ring = self.ring(c[0])
            x0, x1 = min(p[0] for p in ring) - 2, max(p[0] for p in ring) + 2
            z0, z1 = min(p[1] for p in ring) - 2, max(p[1] for p in ring) + 2
            cands = [r for r in free.get((c[3], c[4]), []) if x0 <= r[6] <= x1 and z0 <= r[7] <= z1]
            if not cands:
                orphans.append(c)
                continue
            best = min(cands, key=lambda r: (r[6] - c[1]) ** 2 + (r[7] - c[2]) ** 2)
            free[(c[3], c[4])].remove(best)        # one row, one record
            pairs.append((c, best))
        left = [r for rs in free.values() for r in rs if r[6] < WIDE_X1 - 15]
        return pairs, orphans, left

    def test_every_changed_height_is_a_row_of_the_joins_table(self):
        pairs, orphans, left = self.pair_rows()
        self.assertEqual(orphans, [], 'changed records that are no row of lidar_east_heights.json')
        self.assertEqual(len(pairs), len(self.changes))

    def test_every_row_inside_the_tier_reached_the_blob(self):
        # the other way round: a row inside the wide box whose height word moved is a changed record, but for the
        # packer's own drops: a south-scene building the wide scene already holds (pack_wide's seenB; the same way has
        # a 'wide' row), and an outline that holds 3D parts, which is not packed (the Triad1828 Centre, 60.9 m to
        # 86.9, and the Waterfront Garage: their building:part records carry their own heights)
        pairs, orphans, left = self.pair_rows()
        wide_ways = {r[2] for r in self.rows if r[0] == 'wide'}
        left = [r for r in left if not (r[0] == 'south' and r[2] in wide_ways)]
        self.assertEqual(sorted(r[8] for r in left), ['Triad1828 Centre', 'Waterfront Garage'], left)

    def test_every_row_is_the_roof_pass_s_own_number(self):
        scenes = {'wide': json.loads(C.path('scene_wide.json').read_text())['buildings'],
                  'south': json.loads(C.path('scene_south.json').read_text())['buildings']}
        self.assertEqual(len(self.rows), 584)
        for tag, bi, way, form, old, new, cx, cz, name in self.rows:
            m = self.roofs[str(way)]
            self.assertEqual(m[0], form, way)
            self.assertIn(form, (0, 1, 2))
            self.assertAlmostEqual(new, max(2.5, min(550.0, round(m[2], 1))), places=6, msg=str(way))
            b = scenes[tag][bi]
            self.assertEqual(b['h'], new, (tag, bi))
            poly = b['poly']
            mx = sum(p[0] for p in poly) / len(poly)
            mz = sum(p[1] for p in poly) / len(poly)
            self.assertEqual((round(mx), round(mz)), (cx, cz), (tag, bi))
            self.assertTrue(self.east(mx, mz), (tag, bi, mx, mz))
            self.assertFalse(old > 30 and new < old, 'a tall was lowered: %r' % ((tag, bi, name, old, new),))

    def test_the_join_keeps_its_rules(self):
        s = self.join
        self.assertIn('if east_of_river(cx, cz, CITY_LINE):', s)
        self.assertIn('return cx > EAST_X and not line.contains(Point(cx, cz))', s)
        self.assertIn('if ia >= ROOF_COVER * pg.area and ia >= ROOF_COVER * wpg.area and (best is None or ia > best[0]):', s)
        self.assertIn('if old > 30 and hr < old:', s)            # the talls' ratchet, as for the City's footprints
        self.assertRegex(s, r"EAST_X = 1000\.0\b")
        self.assertRegex(s, r"ROOF_COVER = 0\.5\b")
        # the roof pass is read only where the City join has nothing: inside the h is None branch
        branch = s[s.index('        if h is None:'):s.index('        # Round 160: the snapshot is not pristine everywhere')]
        self.assertIn('roof_pass_height(pg, east_tree, east_list)', branch)
        self.assertEqual(s.count('roof_pass_height('), 2)        # its definition and that one call
        # Camden Tower: tagged 37.2 m, the pass reads 28.4, the ratchet holds it
        ct = [b for b in json.loads(C.path('scene_wide.json').read_text())['buildings'] if b.get('name') == 'Camden Tower']
        self.assertEqual([b['h'] for b in ct], [37.2])

    def test_the_packer_refuses_anything_but_heights(self):
        s = C.path('pack_wide.py').read_text()
        guard = s[s.index('if ARGS.against:'):s.index("open('wide.b64', 'w').write(b64)")]
        self.assertIn('repack_diff(_old, buf)', guard)
        self.assertIn('sys.exit(1)', guard)
        self.assertIn("base64.b64decode(open('wide_walls.b64').read()) != wb", guard)
        self.assertLess(guard.index('sys.exit(1)'), guard.index("open('wide_repack.json', 'w')"))
        self.assertEqual(s.count("open('wide.b64', 'w')"), 1)    # and nothing is written before the guard

    # ---- what the page does with them
    def test_the_measured_skyline_is_in_the_blob(self):
        want = {   # (x, z) of the packed record's centre, the default it stood at, its measured roof
            'One Port Center': (1288, 134, 13.0, 54.2),
            'Riverview Towers': (1545, 357, 15.0, 40.7),
            '330 Cooper': (1886, -162, 21.3, 39.2),
            'the county jail': (1821, 219, 13.0, 30.9),
            'the Hall of Justice': (1907, 264, 13.0, 28.5),
            'the Board of Education building': (1563, -307, 29.8, 44.0),
            'the American Water building': (1192, -372, 18.0, 28.9),
        }
        for name, (x, z, old, new) in want.items():
            hit = [c for c in self.changes if abs(c[1] - x) < 12 and abs(c[2] - z) < 12 and c[3] == round(old * 5) and c[4] == round(new * 5)]
            self.assertEqual(len(hit), 1, (name, hit))

    def test_a_record_lifted_over_45_m_keeps_its_place_in_the_reservoirs_count(self):
        m = re.search(r'const WIDE_COLK_KEEP = (\[\[.*?\]\]);', self.app)
        self.assertIsNotNone(m)
        keep = json.loads(m.group(1))
        crossers = [c for c in self.changes if c[3] <= 225 < c[4] and self.body[self.offs[c[0]] + 3] <= 6]
        self.assertEqual(len(crossers), 1, crossers)             # One Port Center, 13 m to 54.2
        for c in crossers:
            ring = self.ring(c[0])
            self.assertEqual(sum(1 for q in keep if point_in_ring(q[0], q[1], ring)), 1, c)
        for q in keep:   # and every point named is one record over the line of a kind the reservoir counts, well inside it
            hits = []
            for i in range(self.hdr[1]):
                a = self.offs[i]
                if self.body[a + 1] > 225 and self.body[a + 3] <= 6 and abs(self.body[a + 6] * 0.2 - q[0]) < 400:
                    ring = self.ring(i)
                    if point_in_ring(q[0], q[1], ring):
                        hits.append(i)
            self.assertEqual(len(hits), 1, (q, hits))
            ring = self.ring(hits[0])
            mx = sum(p[0] for p in ring) / len(ring)
            mz = sum(p[1] for p in ring) / len(ring)
            self.assertLess(max(abs(q[0] - mx), abs(q[1] - mz)), 60)      # the loop's own box test before pointInPoly
        self.assertIn("else if (t <= 6 && WIDE_COLK_KEEP.some((q) => Math.abs(q[0] - cx) < 60 && Math.abs(q[1] - cz) < 60 && pointInPoly(q[0], q[1], poly))) wideColK++;", self.app)
        # it hangs on the sampler's own line, so a record is counted once: sampled at 45 m or under, or kept over it
        i = self.app.index("else if (t <= 6 && WIDE_COLK_KEEP.some(")
        prev = self.app[:i].rstrip().rsplit('\n', 1)[-1]
        self.assertIn("if (h <= 45 && t <= 6) { wideColSample(c, i); colStat('wide', c);", prev)
        self.assertIn("Object.defineProperty(COL_STAT, 'wideColK', { enumerable: true, get: () => wideColK });", self.app)

    def test_camden_city_hall_is_not_a_slab(self):
        # 371 ft of tower on a base of a few storeys, and beyond the 2022 flight's tiles (x 2,114 against 2,010): its
        # 4,174 m2 footprint must never stand at the tower's height. It keeps its default until it is modelled as a
        # base and a tower.
        hits = []
        for i in range(self.hdr[1]):
            a = self.offs[i]
            if abs(self.body[a + 6] * 0.2 - 2114) < 120:
                ring = self.ring(i)
                if point_in_ring(2114, 72, ring):
                    hits.append(self.body[a + 1] / 5)
        self.assertEqual(len(hits), 1, hits)
        self.assertLess(hits[0], 40.0)


if __name__ == '__main__':
    unittest.main()
