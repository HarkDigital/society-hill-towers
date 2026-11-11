"""Round 229: Camden at its measured heights, and the guard for any repack that is meant to move heights only.

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
  - Camden City Hall's whole footprint is not a 113 m slab;
  - (the review) no bridge structure took a "roof": the pass's flat reading over an anchorage is the deck, and the Walt
    Whitman's New Jersey anchorage at 38.8 m stood across the roadway as an office block. A way OSM tags
    bridge:support, and the two unchecked port structures of lidar_join.py's ROOF_HELD, give no height;
  - (the review) the storefronts hung on the hosts that moved carry the new host heights in storefront_info.json
    (bake_storefronts.py --host-heights), so no panel stands over a wall the measurement lowered.
A LATER heights-only repack packs with --against a copy of the then-committed wide.b64, commits the wide_repack.json
that writes, and moves PREDECESSOR to that file's "against" in the same commit; a repack that is NOT heights-only
re-deals the tier's look and has to say so, and retire the first check, on purpose."""
import base64
import hashlib
import json
import os
import ast
import math
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
        self.assertEqual(len(self.changes), 549)        # 553 before the review: less two bridge anchorages and two port structures

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
        self.assertEqual(len(self.rows), 580)
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

    # ---- the review: what the pass measured is not always a roof
    def record_at(self, x, z):
        hits = []
        for i in range(self.hdr[1]):
            a = self.offs[i]
            if abs(self.body[a + 6] * 0.2 - x) < 400 and point_in_ring(x, z, self.ring(i)):
                hits.append(i)
        self.assertEqual(len(hits), 1, (x, z, hits))
        return hits[0]

    def test_a_held_way_gives_no_height(self):
        s = self.join
        self.assertIn("            if 'bridge:support' in e.get('tags', {}):\n                ROOF_HELD.setdefault(e['id'], BRIDGE_SUPPORT)", s)
        self.assertIn('    if best[2] in ROOF_HELD:', s)
        fn = s[s.index('def roof_pass_height('):s.index('def spike_check(')]
        self.assertLess(fn.index('if best[2] in ROOF_HELD:'), fn.index('return max(CLAMP_LO'))    # held before any height is returned
        doc = json.loads(C.path('lidar_east_heights.json').read_text())
        held = {r[0]: r for r in doc['held']}
        # the Walt Whitman's New Jersey anchorage, the Ben Franklin's Camden anchorage and its east tower's pier (OSM
        # bridge:support), and the two unnamed port structures nobody has checked
        self.assertEqual(sorted(held), [265973742, 334628517, 754832343, 1044593722, 1186523447])
        self.assertEqual(sum(1 for r in held.values() if 'bridge support' in r[5]), 3)
        self.assertFalse({r[2] for r in self.rows} & set(held))
        changed = {c[0] for c in self.changes}
        # each stands in the blob at the word Round 225 gave it: 13 m under the Walt Whitman's deck, not 38.8 across it
        for x, z, word in ((1853, 4573, 65), (1368, -717, 65), (1261, 1730, 30), (1686, 3193, 65)):
            i = self.record_at(x, z)
            self.assertNotIn(i, changed, (x, z))
            self.assertEqual(self.body[self.offs[i] + 1], word, (x, z))

    def test_no_changed_record_stands_in_a_delaware_bridge(self):
        # The page draws the Ben Franklin and the Walt Whitman itself and leaves the wide loop at BRIDGE_SKIP for the
        # footprints it knows: the first four entries are the two bridges' towers. A changed record whose footprint
        # comes within DECK of a bridge's axis (the line through its towers, on to REACH past the east one: the
        # anchorages are 226 and 241 m out, the approach spans beyond them) must be one the page skips, by the loop's
        # own test with a margin for the centroid.
        DECK, REACH = 25.0, 600.0
        m = re.search(r'const BRIDGE_SKIP = (\[\[.*?\]\]);', self.app, re.S)
        self.assertIsNotNone(m)
        skip = json.loads(re.sub(r'//[^\n]*', '', m.group(1)))
        towers = skip[:4]
        self.assertEqual([q[2] for q in towers], [60, 60, 60, 60])
        self.assertEqual([towers[0][:2], towers[2][:2]], [[620.8, -889.9], [1037.2, 4391.6]])     # the Ben Franklin's west tower, the Walt Whitman's

        def seg_dist(px, pz, ax, az, bx, bz):
            dx, dz = bx - ax, bz - az
            t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz)))
            return math.hypot(px - ax - t * dx, pz - az - t * dz)

        def crosses(a, b, c, d):
            o = lambda p, q, r: (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
            return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0

        near = []
        for a, b in ((towers[0], towers[1]), (towers[2], towers[3])):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            ux, uz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            e = (b[0] + ux * REACH, b[1] + uz * REACH)
            for c in self.changes:
                ring = self.ring(c[0])
                d = min(min(seg_dist(p[0], p[1], a[0], a[1], e[0], e[1]) for p in ring),
                        min(seg_dist(q[0], q[1], ring[k - 1][0], ring[k - 1][1], ring[k][0], ring[k][1]) for q in (a[:2], e) for k in range(len(ring))))
                if d < DECK or any(crosses(a[:2], e, ring[k - 1], ring[k]) for k in range(len(ring))):
                    near.append(c)
        for c in near:
            self.assertTrue(any(math.hypot(c[1] - q[0], c[2] - q[1]) < q[2] - 5 for q in skip),
                            'record %d at (%.0f, %.0f) took a height of %.1f m in a bridge the page draws, and BRIDGE_SKIP does '
                            'not drop it' % (c[0], c[1], c[2], c[4] / 5))
        # and the check sees what the review saw: the Walt Whitman's anchorage is in the corridor and outside every circle
        i = self.record_at(1853, 4573)
        ring = self.ring(i)
        a, b = towers[2], towers[3]
        self.assertLess(min(seg_dist(p[0], p[1], a[0], a[1], b[0] + (b[0] - a[0]), b[1] + (b[1] - a[1])) for p in ring), DECK)
        self.assertFalse(any(math.hypot(1853.4 - q[0], 4572.6 - q[1]) < q[2] for q in skip))

    def test_the_records_lifted_into_the_tower_styles_are_the_ones_looked_at(self):
        # over 30 m the wide loop leaves fabricStyle for towerStyle, whose only industrial dress needs the type word a
        # heights-only repack cannot change: a port shed lifted over the line draws as an office block. These six
        # crossed it and were looked at in captures; a seventh has to be looked at too before it is added here.
        self.assertIn('      else if (h > 30) style = towerStyle(fa, t, i);', self.app)
        # (each record's centre and its two words as the blob holds them, 0.2 m a word)
        up = sorted((round(c[1]), round(c[2]), c[3] / 5, c[4] / 5) for c in self.changes if c[3] <= 150 < c[4])
        self.assertEqual(up, [
            (1288, 134, 13.0, 54.2),       # One Port Center
            (1550, 360, 15.0, 40.8),       # Riverview Towers
            (1563, -307, 29.8, 44.0),      # the Board of Education building
            (1794, 3585, 13.0, 33.2),      # way 576393381, office=company
            (1819, 218, 13.0, 30.8),       # the county jail
            (1886, -162, 21.2, 39.2),      # 330 Cooper
        ])
        self.assertEqual([c for c in self.changes if c[4] <= 150 < c[3]], [])

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


def bake_fn(name, *consts):
    """One function of bake_storefronts.py (a script: importing it runs the bake) with the module constants it reads."""
    tree = ast.parse(C.path('bake_storefronts.py').read_text())
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == name)
            or (isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in consts for t in n.targets))]
    ns = {'math': math}
    exec(compile(ast.Module(body=keep, type_ignores=[]), 'bake_storefronts.py', 'exec'), ns)
    return ns[name]


class StorefrontHosts(unittest.TestCase):
    """The review: the page clamps a shopfront panel, its awning and its blade sign to the host height baked into
    storefront_info.json, which held the defaults the repack replaced. bake_storefronts.py --host-heights gave the 52
    records on the moved hosts their new host heights and touched nothing else."""

    # sha256 of the base64 text of Round 225's sidecar records (storefront_info.json's "rec" at e4b6a2f)
    REC_225 = '5418489e882b0741c443e3cb51948e4c9c147d805b7eab0a0b2598f4cffb126a'

    @classmethod
    def setUpClass(cls):
        need = ('storefronts.b64', 'storefront_info.json', 'lidar_east_heights.json', 'scene_wide.json', 'scene_south.json',
                'bake_storefronts.py', 'app.js')
        missing = [n for n in need if not C.path(n).exists()]
        if missing:
            raise unittest.SkipTest('input absent: ' + ', '.join(missing))
        cls.info = json.loads(C.path('storefront_info.json').read_text())
        raw = base64.b64decode(C.path('storefronts.b64').read_text())
        cls.body = struct.unpack('<%dh' % ((len(raw) - 16) // 2), raw[16:])
        r = base64.b64decode(cls.info['rec'])
        cls.rec = struct.unpack('<%dh' % (len(r) // 2), r)
        cls.st = cls.info['stride']
        cls.rows = json.loads(C.path('lidar_east_heights.json').read_text())['rows']
        cls.scenes = {'wide': json.loads(C.path('scene_wide.json').read_text())['buildings'],
                      'south': json.loads(C.path('scene_south.json').read_text())['buildings']}
        cls.fn = staticmethod(bake_fn('host_heights', 'S'))
        # the same walk with every row's two heights swapped puts the old host heights back
        cls.back, cls.undone, cls.back_problems = cls.fn(cls.body, cls.rec, cls.st, [r[:4] + [r[5], r[4]] + r[6:] for r in cls.rows], cls.scenes)

    def test_the_sidecar_is_round_225s_with_the_moved_hosts_heights_and_nothing_else(self):
        self.assertEqual(self.back_problems, [])
        self.assertEqual(len(self.undone), 52)
        old = base64.b64encode(struct.pack('<%dh' % len(self.back), *self.back)).decode('ascii')
        self.assertEqual(hashlib.sha256(old.encode('ascii')).hexdigest(), self.REC_225,
                         'storefront_info.json differs from Round 225\'s in more than the host heights of the records on moved hosts')
        # forward from Round 225's records gives the committed ones, and a second run changes nothing
        fwd, changed, problems = self.fn(self.body, self.back, self.st, self.rows, self.scenes)
        self.assertEqual(problems, [])
        self.assertEqual(tuple(fwd), self.rec)
        self.assertEqual(sorted(c[0] for c in changed), sorted(c[0] for c in self.undone))
        self.assertEqual(self.fn(self.body, self.rec, self.st, self.rows, self.scenes)[1:], ([], []))
        # only field 7 moved, and its two end bits stayed
        diff = [i for i in range(len(self.rec)) if self.rec[i] != self.back[i]]
        self.assertEqual({i % self.st for i in diff}, {7})
        self.assertTrue(all((self.rec[i] & 3) == (self.back[i] & 3) for i in diff))
        # every one of them is a storefront east of the river
        for c in changed:
            self.assertGreater(self.body[c[0] * 8] * 0.2, EAST_X, c)

    def test_no_panel_stands_over_its_measured_host(self):
        app = C.path('app.js').read_text()
        self.assertEqual(app.count('if (r.hostH > 0) H = Math.min(H, r.hostH - 0.15);'), 2)     # the panel and the blade sign's
        self.assertEqual(app.count('let H = Math.min(r.fh, Math.max(3.4, (r.fp || 3.05) + 0.7));'), 2)
        self.assertIn('hostH = (r[q + 7] >> 2) / 10;', app)

        def panel(i, rec):     # the page's own height for record i's panel
            fh, fp, host = self.body[i * 8 + 6] / 10, rec[i * self.st + 4] / 10, (rec[i * self.st + 7] >> 2) / 10
            H = min(fh, max(3.4, (fp or 3.05) + 0.7))
            if host > 0:
                H = min(H, host - 0.15)
            return max(2.6, H)
        over_before = []
        for i, old, new, tag, bi in self.undone:      # (undone: old and new swapped)
            h = self.scenes[tag][bi]['h']
            self.assertEqual(self.rec[i * self.st + 7] >> 2, int(round(h * 10)), i)
            self.assertEqual(old, int(round(h * 10)), i)
            # the wall is drawn at the blob's 0.2 m word, at most 0.1 m under the scene's height
            self.assertLessEqual(panel(i, self.rec), max(2.6, h - 0.1) + 1e-9, (i, self.info['names'][i], h))
            if panel(i, self.back) > h:
                over_before.append((i, self.info['names'][i], panel(i, self.back), panel(i, self.rec), h))
        # the two the review named: 3.6 m of panel on a 3.2 m wall, 3.75 on 3.3
        self.assertEqual([(i, n) for i, n, a, b, h in over_before], [(1078, "Buster's Liquor"), (1099, "Friend's Cafe")])
        self.assertEqual([round(b, 2) for i, n, a, b, h in over_before], [3.05, 3.15])

    def test_a_record_that_is_not_its_hosts_is_refused(self):
        # a record behind whose wall a moved building stands, but carrying some other host's height: a problem, no change
        i, old, new, tag, bi = self.undone[0]
        rec = list(self.back)
        rec[i * self.st + 7] = (rec[i * self.st + 7] & 3) | ((new + 7) << 2)     # (undone's `new` is the old height)
        out, changed, problems = self.fn(self.body, rec, self.st, self.rows, self.scenes)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('record %d ' % i, problems[0])
        self.assertNotIn(i, [c[0] for c in changed])
        self.assertEqual(out[i * self.st + 7], rec[i * self.st + 7])

    def test_the_flag_bakes_nothing_and_writes_nothing_on_a_problem(self):
        s = C.path('bake_storefronts.py').read_text()
        a, b = s.index("if '--host-heights' in sys.argv:"), s.index('# ---- footprints: the drawn set')
        self.assertLess(a, b)                              # before the bake reads a footprint
        block = s[a:b]
        self.assertTrue(block.rstrip().endswith('sys.exit(0)'))
        self.assertNotIn('OUT_B64, \'w\'', block)
        self.assertNotIn("open(OUT_B64, 'w')", block)
        self.assertLess(block.index('if _problems:'), block.index("open('storefront_info.json', 'w'"))
        self.assertIn("sys.exit(f'ERROR: --host-heights: {len(_problems)} record(s) do not line up", block)


if __name__ == '__main__':
    unittest.main()
