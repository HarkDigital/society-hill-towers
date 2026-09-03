"""The built single-file page (build.py -> society-hill-towers.html): the embedded
blobs decode to exactly the committed .b64 data, no template placeholder survives,
and the page stays under the size budget. Skips when the page has not been built."""
import base64
import json
import re
import struct
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_build
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

PAGE = 'society-hill-towers.html'
PAGE_LIMIT_MB = 75
EMBEDDED = {'WIDE_B64': 'wide.b64', 'WIDE_WALLS_B64': 'wide_walls.b64', 'CITY_B64': 'city.b64', 'OUTSKIRTS_B64': 'outskirts.b64', 'STOREFRONTS_B64': 'storefronts.b64', 'TREES_B64': 'trees.b64',
            'TRAFFIC_B64': 'traffic.b64', 'POLES_B64': 'poles.b64'}
# blobs whose body is bytes, not int16 (never byte-plane shuffled): file -> accepted magics
BYTE_BLOBS = {'wide_walls.b64': (0x53485457,)}


def unplanar(raw):
    """Undo build.py's byte-plane shuffle: header, then every low byte, then every high byte."""
    n = (len(raw) - 16) // 2
    lo = raw[16:16 + n]
    hi = raw[16 + n:16 + 2 * n]
    out = bytearray(2 * n)
    out[0::2] = lo
    out[1::2] = hi
    return raw[:16] + bytes(out)


def planar_flags(page):
    """Parse `const B64_PLANAR = {...};` -> {VARNAME: value}. Values are True (the named
    `let X_B64` string is planar) or a base64 string (the planar blob itself). Empty when
    the page carries no such declaration (plain interleaved blobs)."""
    m = re.search(r'const B64_PLANAR\s*=\s*(\{.*?\})\s*;', page, re.S)
    if not m:
        return {}
    lit = m.group(1)
    try:
        d = json.loads(lit)
    except ValueError:
        d = {}
        for k, v in re.findall(r'["\']?([A-Za-z0-9_]+)["\']?\s*:\s*(true|false|"[^"]*"|\'[^\']*\'|\d+)', lit):
            d[k] = True if v == 'true' else (False if v == 'false' else v.strip('"\''))
    out = {}
    for k, v in d.items():
        key = k.upper()
        if not key.endswith('_B64'):
            key += '_B64'
        out[key] = v
    return out


class BuiltPage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        p = C.path(PAGE)
        cls.page = p.read_text(encoding='utf-8') if p.exists() else None

    def need_page(self):
        if self.page is None:
            self.skipTest('%s not built (cd 3d-model && python3 build.py)' % PAGE)

    def test_embedded_blobs_match_committed(self):
        """Each `let X_B64 = "..."` (un-shuffled when B64_PLANAR flags it) equals the committed .b64."""
        self.need_page()
        flags = planar_flags(self.page)
        for var, fname in EMBEDDED.items():
            with self.subTest(blob=fname):
                if not C.path(fname).exists():
                    self.skipTest('%s not committed' % fname)
                want = base64.b64decode(C.path(fname).read_text(encoding='ascii').strip())
                flag = flags.get(var)
                if isinstance(flag, str) and len(flag) > 32:
                    raw = base64.b64decode(flag)
                    planar = True
                else:
                    m = re.search(r'\blet %s = "([A-Za-z0-9+/=]*)";' % var, self.page)
                    self.assertIsNotNone(m, 'page has no `let %s = "..."` declaration' % var)
                    raw = base64.b64decode(m.group(1))
                    planar = bool(flag)
                self.assertEqual(len(want), len(raw), '%s: embedded %d bytes vs committed %d' % (fname, len(raw), len(want)))
                got = unplanar(raw) if planar else raw
                if got != want and not planar and unplanar(raw) == want:
                    self.fail('%s: the embedded blob is byte-plane shuffled but B64_PLANAR does not flag %s' % (fname, var))
                self.assertEqual(want, got, '%s: embedded blob differs from the committed file (planar=%s)' % (fname, planar))
                magic = struct.unpack('<i', got[:4])[0]
                self.assertIn(magic, BYTE_BLOBS.get(fname) or C.BLOBS[fname][0], '%s: decoded header magic is wrong' % fname)

    def test_no_leftover_placeholders(self):
        self.need_page()
        names = set(re.findall(r'\{\{[A-Z_0-9]+\}\}', C.path('template.html').read_text(encoding='utf-8'))) \
            if C.path('template.html').exists() else set()
        left = sorted(set(re.findall(r'\{\{[A-Z_0-9]+\}\}', self.page)))
        self.assertEqual([], left, 'unreplaced template placeholders in the built page: %s (template declares %s)' % (left, sorted(names)))

    def test_page_size_under_budget(self):
        self.need_page()
        size = C.path(PAGE).stat().st_size
        print('\n  %s = %.2f MB' % (PAGE, size / 1e6))
        self.assertLess(size, PAGE_LIMIT_MB * 1024 * 1024, '%s is %.2f MB (limit %d MB)' % (PAGE, size / 1e6, PAGE_LIMIT_MB))

    def test_data_constants_present(self):
        """build.py inlines every data constant app.js reads; each must be declared exactly once."""
        self.need_page()
        for const in ('SCENE_DATA', 'META', 'DEM', 'DEM_WIDE', 'DEM_SOUTH', 'WWB_PTS', 'WIDE_NAMES', 'DEM_CITY',
                      'FACADE_PAL', 'ST_LABELS', 'TREE_NAMES', 'PLACES', 'OVERPASSES', 'DEM_NW', 'NW_PARKS', 'NW_WATER'):
            with self.subTest(const=const):
                n = len(re.findall(r'\bconst %s = ' % const, self.page))
                self.assertEqual(1, n, 'const %s declared %d times' % (const, n))
        for var in list(EMBEDDED) + ['ST_SDF']:
            with self.subTest(var=var):
                self.assertEqual(1, len(re.findall(r'\blet %s = ' % var, self.page)), 'let %s missing or duplicated' % var)
        self.assertNotRegex(self.page, r'<script[^>]*>\s*</script>', 'an empty <script> block made it into the page')


if __name__ == '__main__':
    unittest.main()
