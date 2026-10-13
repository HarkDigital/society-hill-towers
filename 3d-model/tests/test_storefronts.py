"""Round 189 (Mike: "Do the storefront boxes on Broad Street too"): the storefronts' data.

storefronts.b64 is never re-packed by accident (its sha256 is pinned; bake_storefronts.py refuses to write a blob that
differs unless --rebake), and what the generated shopfronts need beyond the record rides in storefront_info.json in its
order: the count and the blob it was baked against, a record of 8 int16 each, no two kept spans on one wall line
overlapping, the names clean (no em or en dash or middot, the house rule for anything on screen; at most 40 characters),
the trades the art's thirteen, the hours well formed. fetch_shops.py runs its fetch only as a script, so the bake imports
it without fetching."""
import ast
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
        cls.st = cls.info.get('stride', 8)

    def test_it_rides_on_the_blob(self):
        self.assertEqual(self.info['n'], self.n)
        self.assertEqual(self.info['v'], 2)
        self.assertEqual(self.st, 9)   # the review's ninth field: the panel's turn to its wall
        self.assertEqual(len(self.rec), self.n * self.st)
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
            fam, hx = self.rec[i * self.st + 5], self.rec[i * self.st + 6]
            self.assertTrue(0 <= fam < 13)
            self.assertTrue(-1 <= hx < len(H))
        self.assertGreater(sum(1 for i in range(self.n) if self.rec[i * self.st + 6] >= 0), 900)

    def test_no_two_kept_spans_on_a_wall_overlap(self):
        spans = []
        for i in range(self.n):
            o, q = i * 8, i * self.st
            x, z, ang = self.body[o] * 0.2, self.body[o + 1] * 0.2, self.body[o + 2] / 1000
            shift, w = self.rec[q] / 10, self.rec[q + 1] / 10
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
        self.assertLess(st['noWall'] + st['mall'], 160)
        for i in range(self.n):
            q = i * self.st
            w = self.rec[q + 1]
            if w:
                self.assertLessEqual(abs(self.rec[q]), 330)        # never more than 30 m along its wall, and 3 m more on it
            self.assertTrue(w == 0 or 34 <= w <= 120, w)            # 3.4 to 12 m, or hidden
            self.assertLessEqual(self.rec[q + 3], self.rec[q + 2])
            self.assertLessEqual(abs(self.rec[q + 8]), 1500)       # turned at most 8.5 degrees

    def test_the_wall_is_measured_never_saturated(self):
        # the review: out and in were held to 1.2 m, so five panels on tower hosts whose base the page draws 1.4 to 2.8 m
        # behind the record's line stood 1.3 to 1.5 m in front of their wall (Insomnia Cookies on Broad Street a white
        # board off the granite). A face is found within SPAN_REACH of the line and the cm reach it whole, never pinned at
        # a bound: no laid record sits at the old clamp or at the reach, and those five carry their wall's own line
        reach = int(round(_bake_const('SPAN_REACH') * 100))
        names = self.info['names']
        for i in range(self.n):
            q = i * self.st
            if not self.rec[q + 1]:
                continue
            o, n_ = self.rec[q + 2], self.rec[q + 3]
            self.assertTrue(-reach < n_ <= o < reach, (i, names[i], o, n_))
            self.assertFalse(o == n_ == -120 or o == n_ == 120, (i, names[i], o, n_))
        want = {'Insomnia Cookies': -250, 'Girasole': -250, "Talula's Daily": -140, "Talula's Garden": -135}
        seen = {}
        for i in range(self.n):
            q = i * self.st
            if self.rec[q + 1] and names[i] in want:
                seen.setdefault(names[i], []).append(self.rec[q + 2])
        for nm, lim in want.items():
            self.assertTrue(any(o <= lim for o in seen.get(nm, [])), (nm, seen.get(nm)))
        src = (ROOT / 'bake_storefronts.py').read_text()
        self.assertNotIn('max(-120, min(120,', src)

    def test_every_span_stands_on_its_wall(self):
        # the review: a span bridging a jog stood out as a box up to 2 m deep, and one past its wall's end stood in the air:
        # no kept span's face stands more than SPAN_FLUSH (30 cm) proud of the wall anywhere along it
        for i in range(self.n):
            q = i * self.st
            if self.rec[q + 1]:
                self.assertLessEqual(self.rec[q + 2] - self.rec[q + 3], 31, i)



def _bake_const(name):
    """One module constant of bake_storefronts.py (a literal), without running the bake."""
    for n in ast.parse((ROOT / 'bake_storefronts.py').read_text()).body:
        if isinstance(n, ast.Assign) and any(getattr(t, 'id', None) == name for t in n.targets):
            return ast.literal_eval(n.value)
    raise KeyError(name)


def _bake_fn(name, *consts):
    """One function of bake_storefronts.py (a script: importing it runs the bake), with the module constants it reads."""
    tree = ast.parse((ROOT / 'bake_storefronts.py').read_text())
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == name)
            or (isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in consts for t in n.targets))]
    ns = {'re': __import__('re')}
    exec(compile(ast.Module(body=keep, type_ignores=[]), 'bake_storefronts.py', 'exec'), ns)
    return ns[name]


class Hours(unittest.TestCase):
    """The review: parse_hours on real OSM strings, and the panel's hours as its vertex shader reads them."""
    @classmethod
    def setUpClass(cls):
        cls.parse = staticmethod(_bake_fn('parse_hours', 'DAYS'))

    def test_osm_strings(self):
        P = self.parse
        self.assertEqual(P('24/7'), [0, 1440, 0, 1440, 0, 1440])
        self.assertEqual(P('Mo-Su 00:00-24:00'), [0, 1440, 0, 1440, 0, 1440])
        self.assertEqual(P('Mo-Fr 09:00-17:00; Sa 10:00-14:00; Su off'), [540, 1020, 600, 840, -1, -1])
        # a range that wraps the week, and a close past midnight running on past 1440
        self.assertEqual(P('Su-Th 11:00-22:00; Fr-Sa 11:00-02:00'), [660, 1320, 660, 1560, 660, 1320])
        self.assertEqual(P('Mo-Sa 07:00-15:00; PH off'), [420, 900, 420, 900, -1, -1])
        # a day's two spans are its first opening to its last close; a comma between days
        self.assertEqual(P('Mo-Fr 08:00-12:00,13:00-17:00'), [480, 1020, -1, -1, -1, -1])
        self.assertEqual(P('Mo,We,Fr 10:00-18:00; Sa,Su 12:00-16:00'), [600, 1080, 720, 960, 720, 960])
        self.assertEqual(P('Tu-Su 17:00-24:00'), [1020, 1440, 1020, 1440, 1020, 1440])
        for s in ('Jan-Mar Mo-Fr 09:00-17:00', 'sunrise-sunset', 'Mo-Fr 09:00-17:00 "by appointment"', 'Mo[1] 10:00-12:00', ''):
            self.assertIsNone(P(s), s)

    def test_the_shader_reads_them(self):
        import shutil, subprocess
        if not shutil.which('node'):
            self.skipTest('node is not installed')
        src = (ROOT / 'app.js').read_text()
        arr = src[src.index('  const SF_VERT = [') + len('  const SF_VERT = '):src.index("].join('\\n');", src.index('  const SF_VERT = ['))] + ']'
        late = src[src.index('  const SF_LATE = '):src.index('\n', src.index('  const SF_LATE = '))]
        js = late + """
const L = %s;
const g = L.join('\\n');
const a = g.indexOf('float m = uSfClock.x'), b = g.indexOf('  vSfP = vec4(');
const body = g.slice(a, b).replace(/float /g, 'let ');
const step = (e, x) => (x < e ? 0 : 1), floor = Math.floor, max = Math.max, mod = (x, y) => x - y * Math.floor(x / y);
const f = new Function('uSfClock', 'aSfHours', 'aSfInfo', 'step', 'floor', 'max', 'mod', body + '; return [open, sgn];');
const pk = (o, c) => (o < 0 ? -1 : o * 2048 + c);
const H = { x: pk(1020, 1560), y: pk(1020, 1620), z: pk(720, 1320), w: 0 };   // weekdays 17:00 to 02:00, Saturday to 03:00, Sunday 12:00 to 22:00
const at = (dw, m) => f({ x: m, y: dw }, H, { x: 4 }, step, floor, max, mod);
console.log(JSON.stringify([at(3, 1200), at(3, 900), at(4, 60), at(4, 150), at(6, 90), at(0, 150), at(0, 200), at(1, 60), at(0, 800), at(1, 1400)]));
""" % arr
        out = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        got = [o for o, sg in __import__('json').loads(out.stdout)]
        # Wed 20:00 open; Wed 15:00 shut; Thu 01:00 Wednesday's night still on; Thu 02:30 shut; Sat 01:30 Friday's night;
        # Sun 02:30 Saturday's night (to 03:00); Sun 03:20 shut; Mon 01:00 shut (Sunday closed at 22:00); Sun 13:20 open;
        # Mon 23:20 open
        self.assertEqual(got, [1, 0, 1, 0, 1, 1, 0, 0, 1, 1])


if __name__ == '__main__':
    unittest.main()
