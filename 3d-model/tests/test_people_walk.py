"""Round 227: people_walk.b64 (bake_people_walk.py) and its mapping onto the page's runs.

The blob holds, per way of traffic.b64 and per interval along it, how far the nearest wall stands from the centreline
on either side. It is keyed by way and by distance along the way, because the page's runs cannot be reproduced by a
bake (the built terrain cuts them), so the page tags every run, under ?people=1, with its way's index and its start's
distance along the way. The proof that the tag and the lookup are right, for every run and both sides:
  - the page's own decoder and linker, cut from app.js, run under Node on the real traffic.b64, over a flat ground and
    over a rough one whose dead water, dead site and decks drop vertices and refuse links as the real terrain does;
  - each run's two ends must lie on this file's Python polyline of the tagged way, at the tagged distance and at the
    tagged distance plus the run's length (5 cm);
  - the page's peopleClearCode must return, for each run side, exactly what bake_people_walk.lookup() returns from the
    Python decode of the same blob.
The ways' count and the total of their lengths must agree between the two languages too."""
import base64
import bisect
import math
import re
import struct
import sys
import unittest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import _people_node as pn   # noqa: E402

ROOT = pn.ROOT
sys.path.insert(0, str(ROOT))
import bake_people_walk as bake   # noqa: E402  (numpy is only imported inside the functions that measure)

SCRIPT = r'''
const out = {};
for (const rough of [false, true]) {
  const A = make({ rough }); A.boot(); A.peopleInit();
  const P = A.PEOPLE, runs = A.runs, rows = [];
  for (let i = 0; i < runs.length; i++) { const r = runs[i], m = r.xs.length - 1; rows.push([r.wi, P.arc0[i], r.len, r.xs[0], r.zs[0], r.xs[m], r.zs[m], A.peopleClearCode(i, 0), A.peopleClearCode(i, 1), r.cls]); }
  out[rough ? 'rough' : 'flat'] = { ready: P.ready, ways: P.ways, recWays: P.rec.way.length - 1, recs: P.rec.code.length, unit: P.rec.unit, base: P.rec.base, rows };
}
console.log(JSON.stringify(out));
'''


def at(pts, arc, s):
    j = min(len(arc) - 2, max(0, bisect.bisect_right(arc, s) - 1))
    seg = arc[j + 1] - arc[j]
    t = (s - arc[j]) / seg if seg > 0 else 0.0
    return pts[j][0] + (pts[j + 1][0] - pts[j][0]) * t, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * t


class Blob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / 'people_walk.b64').exists():
            raise unittest.SkipTest('people_walk.b64 absent')
        cls.raw = base64.b64decode((ROOT / 'people_walk.b64').read_text())
        cls.recs = bake.decode(cls.raw)
        cls.ways = bake.load_ways()

    def test_header_and_size(self):
        magic, nw, nrec, params = struct.unpack('<4i', self.raw[:16])
        self.assertEqual(magic, bake.MAGIC)
        self.assertEqual(nw, len(self.ways))                      # one entry a way of traffic.b64, in its order
        self.assertEqual(nrec, sum(len(r) for r in self.recs))
        self.assertEqual(params & 255, bake.LEN_UNIT_DM)
        self.assertEqual(params >> 16 & 255, bake.CODE_BASE_DM)
        self.assertLess(len(self.raw), 100_000)                   # the round's budget: inlined on every visit
        self.assertGreater(len(self.raw), 60_000)

    def test_records_follow_the_ways(self):
        dense_len = []
        for (cls_, _, pts), rec in zip(self.ways, self.recs):
            L = bake.arcs(bake.densify(pts))[-1] if len(pts) > 1 else 0.0
            dense_len.append(L)
            if cls_ < 2 or L <= 0:
                self.assertEqual(rec, [])                         # nobody walks a motorway or a trunk road
                continue
            self.assertTrue(rec)
            self.assertEqual(rec[0][0], 0.0)
            self.assertIsNone(rec[-1][1])                         # the last interval runs to the way's end
            for (s0, e0, r, l), nxt in zip(rec, rec[1:]):
                self.assertEqual(e0, nxt[0])
                self.assertGreater(e0, s0)
                self.assertLess(e0, L + 1.01)                     # a boundary is rounded to 2 m: within a metre of the way
            for _, _, r, l in rec:
                self.assertTrue(0 <= r <= 63 and 0 <= l <= 63)
        self.assertGreater(sum(1 for r in self.recs if r), 25000)

    def test_the_codes(self):
        self.assertEqual(bake.code_of(float('inf')), bake.CODE_NONE)
        self.assertEqual(bake.code_of(25.0), bake.CODE_FAR)
        self.assertEqual(bake.code_of(10.0), bake.CODE_FAR)
        self.assertEqual(bake.code_of(9.99), 61)
        self.assertEqual(bake.code_of(6.0), 22)
        self.assertEqual(bake.code_of(3.8), 0)
        self.assertEqual(bake.code_of(1.0), 0)                    # 3.8 m or less: no room beside any drawn street
        self.assertEqual(bake.code_metres(22), 6.0)
        self.assertEqual(bake.code_metres(bake.CODE_FAR), 10.0)
        self.assertEqual(bake.code_metres(bake.CODE_NONE), math.inf)
        for q in (3.81, 4.449, 5.5, 7.77, 9.94):                  # the floor: never more room than was measured
            self.assertLessEqual(bake.code_metres(bake.code_of(q)), q + 1e-9)
            self.assertGreater(bake.code_metres(bake.code_of(q)), q - 0.1 - 1e-9)

    def test_the_bake_and_the_page_share_their_numbers(self):
        src = (ROOT / 'app.js').read_text(encoding='utf-8')
        m = re.search(r'const PARK_HW = \[([^\]]+)\];', src)
        self.assertEqual([float(v) for v in m.group(1).split(',')], [float(v) for v in bake.PARK_HW])
        sec = src[src.index('  // ---- people on the sidewalks (Round 227'):src.index('  // ---- people on the sidewalks: the section ends')]
        self.assertIn('hdr[0] !== 0x%x' % bake.MAGIC, sec)
        self.assertIn('t = Math.min(3, (s1 - s0) / 2)', sec)       # LOOK_TRIM
        self.assertEqual(bake.LOOK_TRIM, 3.0)
        self.assertIn("c === 63 ? Infinity : c === 62 ? 10 : P.rec.base + c / 10", sec)
        self.assertEqual((bake.CODE_NONE, bake.CODE_FAR, bake.CODE_FAR_M), (63, 62, 10.0))
        # the densify the arcs are measured on is the page's own, line for line
        self.assertIn("const k = Math.max(1, Math.ceil(L / step));\n      for (let j = 1; j <= k; j++) out.push([a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k]);", src)

    def test_merge_keeps_the_lesser_and_only_merges_the_roomy_or_the_equal(self):
        roomy5 = int(round((bake.PARK_HW[5] + bake.ROOMY_M) * 10)) - bake.CODE_BASE_DM
        self.assertEqual(bake.merge([[10, 20, 20], [10, 20, 20]], 5), [[20, 20, 20]])
        self.assertEqual(bake.merge([[10, 20, 21], [10, 20, 20]], 5), [[10, 20, 21], [10, 20, 20]])
        self.assertEqual(bake.merge([[10, roomy5, 63], [10, roomy5 + 9, 62]], 5), [[20, roomy5, 62]])
        self.assertEqual(bake.merge([[10, roomy5 - 1, 63], [10, roomy5 + 9, 62]], 5), [[10, roomy5 - 1, 63], [10, roomy5 + 9, 62]])
        # a primary is drawn 6.5 m to the kerb: only the open codes are roomy beside it
        self.assertEqual(bake.merge([[10, 61, 63], [10, 60, 63]], 2), [[10, 61, 63], [10, 60, 63]])
        self.assertEqual(bake.merge([[10, 62, 63], [10, 63, 62]], 2), [[20, 62, 62]])

    def test_a_wall_on_the_right_is_the_right(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('numpy absent')
        # a way heading east; a wall 6 m to its south. In the scene frame z is south, and the page's side +1 (carSample's
        # positive offset, the normal (-tz, tx)) is the right of the way's own direction: south of an eastbound way
        grid = bake.WallGrid(np.array([[-50.0, 6.0, 150.0, 6.0], [-50.0, -9.5, 20.0, -9.5]]))
        pts = bake.densify([(0.0, 0.0), (100.0, 0.0)])
        s, x, z, tx, tz = bake.way_samples(pts, bake.arcs(pts))
        right, left = bake.cast(grid, x, z, tx, tz)
        self.assertTrue(np.allclose(right, 6.0))
        self.assertTrue(np.allclose(left[s < 19], 9.5))
        self.assertTrue(np.isinf(left[s > 21]).all())
        self.assertEqual(bake.interval_value(s, right, 0.0, 100.0), 22)
        self.assertEqual(bake.interval_value(s, left, 30.0, 100.0), bake.CODE_NONE)


class Mapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pn.have():
            raise unittest.SkipTest('Node.js, traffic.b64 or people_walk.b64 unavailable')
        cls.o = pn.node(SCRIPT)
        cls.recs = bake.decode(base64.b64decode((ROOT / 'people_walk.b64').read_text()))
        cls.ways = bake.load_ways()
        cls.dense = [bake.densify(p) if len(p) > 1 else list(p) for _, _, p in cls.ways]
        cls.arc = [bake.arcs(p) for p in cls.dense]

    def test_every_run_maps_onto_its_way_and_reads_the_bakes_own_codes(self):
        counts = {}
        for name in ('flat', 'rough'):
            o = self.o[name]
            self.assertTrue(o['ready'], name)
            self.assertEqual(o['ways'], len(self.ways))            # the step's own count of ways, handed to the section
            self.assertEqual(o['recWays'], len(self.ways))
            self.assertEqual(o['recs'], sum(len(r) for r in self.recs))
            self.assertEqual((o['unit'], o['base']), (bake.LEN_UNIT_DM / 10, bake.CODE_BASE_DM / 10))
            rows = o['rows']
            counts[name] = len(rows)
            worst = 0.0
            bad = 0
            covered = [0.0] * len(self.ways)
            for wi, s0, ln, ax, az, bx, bz, cr, cl, cls_ in rows:
                self.assertEqual(self.ways[wi][0], cls_)
                L = self.arc[wi][-1]
                self.assertGreaterEqual(s0, -1e-6)
                self.assertLessEqual(s0 + ln, L + 0.02)
                px, pz = at(self.dense[wi], self.arc[wi], s0)
                qx, qz = at(self.dense[wi], self.arc[wi], s0 + ln)
                worst = max(worst, math.hypot(px - ax, pz - az), math.hypot(qx - bx, qz - bz))
                covered[wi] += ln
                if cr != bake.lookup(self.recs[wi], s0, s0 + ln, 1) or cl != bake.lookup(self.recs[wi], s0, s0 + ln, -1):
                    bad += 1
            self.assertLess(worst, 0.05, name)                     # every run's two ends on its own way, at the tagged distances
            self.assertEqual(bad, 0, name)                         # and every run side reads what the bake's reader reads
            # no way is covered twice: the runs of a way never overlap along it
            for wi, c in enumerate(covered):
                self.assertLessEqual(c, self.arc[wi][-1] + 0.05, (name, wi))
            if name == 'flat':
                # on a flat ground nothing is dropped but a way under 2 m: the runs cover the network
                total = sum(a[-1] for a in self.arc)
                self.assertGreater(sum(covered), total - 100)
                self.assertGreater(total, 5_500_000)
        # the two grounds cut the same ways into different runs (that is why the blob is not keyed by run)
        self.assertEqual(counts['flat'], 46145)
        self.assertNotEqual(counts['flat'], counts['rough'])

    def test_the_codes_on_the_runs_are_not_all_one(self):
        rows = self.o['flat']['rows']
        walk = [r for r in rows if r[9] >= 2]
        none = sum(1 for r in walk for c in (r[7], r[8]) if c == bake.CODE_NONE)
        tight = sum(1 for r in walk for c in (r[7], r[8]) if c < 30)
        self.assertGreater(none, 0.15 * 2 * len(walk))
        self.assertGreater(tight, 0.05 * 2 * len(walk))
        for r in rows:
            if r[9] < 2:
                self.assertEqual((r[7], r[8]), (bake.CODE_NONE, bake.CODE_NONE))   # a way with no records reads as open (and is never walked)


if __name__ == '__main__':
    unittest.main()
