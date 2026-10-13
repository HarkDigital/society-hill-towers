"""Round 189 (Mike: "Do the storefront boxes on Broad Street too"): the storefronts' data.

storefronts.b64 is never re-packed by accident (its sha256 is pinned; bake_storefronts.py refuses to write a blob that
differs unless --rebake), and what the generated shopfronts need beyond the record rides in storefront_info.json in its
order: the count and the blob it was baked against, a record of 8 int16 each, no two kept spans on one wall line
overlapping, the names clean (no em or en dash or middot, the house rule for anything on screen; at most 40 characters),
the trades the art's thirteen, the hours well formed. fetch_shops.py runs its fetch only as a script, so the bake imports
it without fetching."""
import base64
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
B64_SHA = '1c7e5d45f2411b597ab5360a9b65cf7364489d479170808f38035785afee6aba'


class Blob(unittest.TestCase):
    def test_the_blob_is_the_one_the_page_has_always_had(self):
        self.assertEqual(hashlib.sha256((ROOT / 'storefronts.b64').read_bytes()).hexdigest(), B64_SHA)

    def test_the_bake_guards_it(self):
        s = (ROOT / 'bake_storefronts.py').read_text()
        self.assertIn("if os.path.exists(OUT_B64) and '--rebake' not in sys.argv:", s)
        self.assertIn('nothing written (pass --rebake to replace it)', s)
        # the guard runs before anything is written
        self.assertLess(s.index("if os.path.exists(OUT_B64) and '--rebake' not in sys.argv:"), s.index("open(OUT_B64, 'w').write(b64)"))

    def test_fetch_shops_imports_without_fetching(self):
        s = (ROOT / 'fetch_shops.py').read_text()
        self.assertIn("if __name__ == '__main__':", s)
        self.assertIn('def businesses(elements):', s)
        tail = s[s.index("if __name__ == '__main__':"):]
        self.assertEqual(tail.count('\n'), 2)   # the guard and its one call
        top = [ln for ln in s.splitlines() if ln and not ln.startswith((' ', '#', 'def ', 'import', 'from', '"', "'", ')', ']', '}'))]
        self.assertFalse([ln for ln in top if 'fetch_tiles(' in ln or 'json.dump(' in ln])


class Sidecar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = json.loads((ROOT / 'storefront_info.json').read_text())
        raw = base64.b64decode((ROOT / 'storefronts.b64').read_text())
        cls.n = struct.unpack('<4i', raw[:16])[1]
        cls.body = struct.unpack('<%dh' % ((len(raw) - 16) // 2), raw[16:])
        r = base64.b64decode(cls.info['rec'])
        cls.rec = struct.unpack('<%dh' % (len(r) // 2), r)

    def test_it_rides_on_the_blob(self):
        self.assertEqual(self.info['n'], self.n)
        self.assertEqual(len(self.rec), self.n * 8)
        self.assertEqual(len(self.info['names']), self.n)
        self.assertEqual(self.info['b64sha'], hashlib.sha256((ROOT / 'storefronts.b64').read_text().encode('ascii')).hexdigest())

    def test_the_names(self):
        names = self.info['names']
        self.assertGreaterEqual(sum(1 for s in names if s), 2200)
        for s in names:
            self.assertLessEqual(len(s), 40, s)
            for c in ('—', '–', '·', '​', '﻿'):
                self.assertNotIn(c, s)
            self.assertEqual(s, s.strip())

    def test_the_trades_and_the_hours(self):
        import fetch_storefront_art as F
        self.assertEqual(self.info['families'], [f[0] for f in F.FAMILIES])
        H = self.info['hours']
        for h in H:
            self.assertEqual(len(h), 6)
            for k in range(0, 6, 2):
                o, c = h[k], h[k + 1]
                if o < 0:
                    self.assertEqual(c, -1)
                else:
                    self.assertTrue(0 <= o < c <= 2047, h)
        for i in range(self.n):
            fam, hx = self.rec[i * 8 + 5], self.rec[i * 8 + 6]
            self.assertTrue(0 <= fam < 13)
            self.assertTrue(-1 <= hx < len(H))
        self.assertGreater(sum(1 for i in range(self.n) if self.rec[i * 8 + 6] >= 0), 900)

    def test_no_two_kept_spans_on_a_wall_overlap(self):
        spans = []
        for i in range(self.n):
            o = i * 8
            x, z, ang = self.body[o] * 0.2, self.body[o + 1] * 0.2, self.body[o + 2] / 1000
            shift, w = self.rec[o] / 10, self.rec[o + 1] / 10
            if w <= 0:
                continue
            nx, nz = math.cos(ang), math.sin(ang)
            tx, tz = -nz, nx
            cx, cz = x + tx * shift, z + tz * shift
            spans.append((cx, cz, nx, nz, w, i))
        cells = {}
        for k, s in enumerate(spans):
            cells.setdefault((int(s[0] // 40), int(s[1] // 40)), []).append(k)
        bad = []
        for k, (cx, cz, nx, nz, w, i) in enumerate(spans):
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in cells.get((int(cx // 40) + dx, int(cz // 40) + dz), ()):
                        if j <= k:
                            continue
                        c2 = spans[j]
                        if nx * c2[2] + nz * c2[3] < math.cos(0.05):
                            continue
                        if abs((c2[0] - cx) * nx + (c2[1] - cz) * nz) > 0.6:
                            continue
                        t1, t2 = cx * -nz + cz * nx, c2[0] * -nz + c2[1] * nx
                        over = min(t1 + w / 2, t2 + c2[4] / 2) - max(t1 - w / 2, t2 - c2[4] / 2)
                        if over > 0.1:
                            bad.append((i, c2[5], round(over, 2)))
        self.assertEqual(bad, [])

    def test_the_layout_moved_little(self):
        st = self.info['stats']
        self.assertLess(st['dropped'], 20)
        for i in range(self.n):
            self.assertLessEqual(abs(self.rec[i * 8]), 300)        # never more than 30 m along its wall
            w = self.rec[i * 8 + 1]
            self.assertTrue(w == 0 or 40 <= w <= 120, w)            # 4 to 12 m, or hidden
            self.assertTrue(-120 <= self.rec[i * 8 + 3] <= self.rec[i * 8 + 2] <= 120)


if __name__ == '__main__':
    unittest.main()
