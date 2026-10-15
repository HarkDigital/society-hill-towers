"""Round 198 (Mike: "The buildings around city hall look too generic. Make them look more like real life."): the
buildings round City Hall in their own facades (fetch_tower_art.py, bake_tower_art.py -> tower_art.json, art/towers/).

- every building in scope (towers.json's non-glass towers within about 450 m of City Hall's centre, but City Hall, One
  and Two Liberty Place and both Comcast towers, which other rounds remodel) has its own entry by its towers.json name,
  with its own cells (base where it has one, the typical storeys, the top), in the atlas and inside it;
- the manifest's files are there under their hashes, with a phone's half copies; build.py inlines the manifest and
  checks its files;
- every in-scope building owns at least one record of wide.b64 (by its spec, with the research's REAL fixes, or by a
  point of its own), no record is owned twice, and nothing of the excluded buildings is owned;
- the excluded buildings' towers.json records carry no fix, and every fix says why;
- the page: the own facades only under the realistic look on WebGL 2 (?real=0 and ?townart=0 keep the lottery), the
  fixes only under REAL, one program for every building, Float32 streams of 1 and 4 (no 1- or 3-byte stream), no
  gl_FragDepth, the bases standing in for the storefronts."""
import base64
import json
import math
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parent.parent
CH = (-1603.0, -802.0)
SCOPE_R = 450.0
EXCLUDED = ('One Liberty Place', 'Two Liberty Place', 'Comcast Center', 'Comcast Technology Center')
GLASS_FACADES = ('glass', 'glass_bands', 'glass_dark')


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


def load_towers(real):
    T = json.loads((ROOT / 'towers.json').read_text())['towers']
    if real:
        for sp in T:
            if 'real' in sp:
                sp.update(sp["real"])
    return T


def wide_records():
    raw = base64.b64decode((ROOT / 'wide.b64').read_text())
    nb = struct.unpack('<4i', raw[:16])[1]
    h = struct.unpack('<%dh' % ((len(raw) - 16) // 2), raw[16:])
    out, o = [], 0
    for i in range(nb):
        n = h[o]
        pts = [(h[o + 6 + 2 * k] / 5, h[o + 7 + 2 * k] / 5) for k in range(n)]
        out.append((i, h[o + 1] / 5, h[o + 2] / 5, h[o + 3], pts))
        o += 6 + 2 * n
    return out


def centroid(p):
    a = cx = cz = 0.0
    for k in range(len(p)):
        x0, z0 = p[k]
        x1, z1 = p[(k + 1) % len(p)]
        c = x0 * z1 - x1 * z0
        a += c; cx += (x0 + x1) * c; cz += (z0 + z1) * c
    if abs(a) < 1e-9:
        return p[0]
    return cx / (3 * a), cz / (3 * a)


def inside(x, y, pts):
    ins, j = False, len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


class Scope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.art = json.loads((ROOT / 'tower_art.json').read_text())
        cls.towers = load_towers(real=True)   # the research's fixes: Eight Penn is glass, Two Penn is not
        cls.scope = [t for t in cls.towers if math.hypot(t['x'] - CH[0], t['z'] - CH[1]) < SCOPE_R
                     and t['facade'] not in GLASS_FACADES and not t['glass'] and t['name'] not in EXCLUDED]

    def test_every_building_in_scope_has_its_own_facade(self):
        names = {a['name'] for a in self.art['towers'].values()}
        self.assertGreaterEqual(len(self.scope), 24)
        for t in self.scope:
            self.assertIn(t['name'], names, t['name'])

    def test_every_entry_is_a_tower_by_name_and_none_excluded(self):
        known = {t['name'] for t in self.towers}
        for bid, a in self.art['towers'].items():
            self.assertIn(a['name'], known, bid)
            self.assertNotIn(a['name'], EXCLUDED)
            self.assertNotRegex(a['name'].lower(), r'city hall|liberty place|comcast')

    def test_cells_are_their_own_and_inside_the_atlas(self):
        A = self.art
        seen = set()
        for bid, a in A['towers'].items():
            self.assertTrue(a['strips'], bid)
            self.assertGreater(a['bay'], 1.0)
            for s in a['strips']:
                whole = bool(s['shaft'].get('whole'))   # a low building's whole wall (the Masonic Temple, the churches)
                if not whole:
                    self.assertTrue(2.4 <= a['floor'] <= 7.0, bid)
                self.assertIn('shaft', s, bid)
                for z in ('top', 'shaft', 'base'):
                    if z not in s:
                        continue
                    c = s[z]
                    x, y, w, h = c['r']
                    self.assertTrue(x >= A['pad'] and y >= A['pad'] and x + w + A['pad'] <= A['w'] and y + h + A['pad'] <= A['h'], (bid, z))
                    self.assertNotIn(tuple(c['r']), seen, (bid, z))
                    seen.add(tuple(c['r']))
                    self.assertGreater(c['nb'], 0)
                    self.assertGreater(c['nf'], 0)
                    self.assertTrue(c['m'][0] > 0 and c['m'][1] > 0)
                    self.assertEqual(len(c['mean']), 3)
                if not whole:
                    self.assertAlmostEqual(s['shaft']['m'][1] / s['shaft']['nf'], a['floor'], 2, bid)
                    self.assertIn('base', s, bid)
                    self.assertIn('top', s, bid)
                self.assertAlmostEqual(s['shaft']['m'][0] / s['shaft']['nb'], s.get('bay', a['bay']), 2, bid)

    def test_files_and_phone_copies(self):
        A = self.art
        for k in ('img', 'imgHalf', 'mask', 'maskHalf'):
            self.assertRegex(A[k], r'^art/towers/atlas(-half|-mask|-mask-half)?\.[0-9a-f]{10}\.(webp|png)$')
            self.assertTrue((ROOT / A[k]).exists(), A[k])
        self.assertLessEqual(A['w'], 4096)
        self.assertLessEqual(A['h'], 4096)
        self.assertEqual(A['pad'], 16)

    def test_build_inlines_and_checks_it(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("TOWER_ART", text_of("tower_art.json", "null"))', b)
        self.assertIn('"tower_art.json"):', b)


class Ownership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.art = json.loads((ROOT / 'tower_art.json').read_text())['towers']
        cls.towers = load_towers(real=True)
        cls.recs = wide_records()

    def tower_at(self, x, z, h):
        best, bd = None, 1e9
        for sp in self.towers:
            d = math.hypot(sp['x'] - x, sp['z'] - z)
            rad = (sp.get('r') or 35) + (20 if h > 300 and sp['h'] > 300 else 0)
            if d < rad and d < bd:
                bd, best = d, sp
        return best

    def test_each_building_owns_records_and_none_twice(self):
        byname = {a['name']: k for k, a in self.art.items()}
        owned = {}
        excluded_specs = {t['name'] for t in self.towers if t['name'] in EXCLUDED}
        for (i, h, mh, t, p) in self.recs:
            cx, cz = centroid(p)
            if math.hypot(cx - CH[0], cz - CH[1]) > 700 or h < 6:
                continue
            sp = self.tower_at(cx, cz, h) if h > 45 else None
            by = []
            if sp and sp['name'] in byname:
                by.append(byname[sp['name']])
            for k, a in self.art.items():
                if any(inside(q[0], q[1], p) for q in a.get('pts', [])):
                    by.append(k)
            if not by:
                continue
            self.assertFalse(sp and sp['name'] in excluded_specs, 'record %d is %s' % (i, sp and sp['name']))
            self.assertEqual(len(set(by)), 1, 'record %d owned by %s' % (i, by))
            owned.setdefault(by[0], []).append(i)
        for k in self.art:
            self.assertTrue(owned.get(k), '%s owns no record' % k)


class Fixes(unittest.TestCase):
    def test_fixes_say_why_and_spare_the_excluded(self):
        T = json.loads((ROOT / 'towers.json').read_text())['towers']
        n = 0
        for t in T:
            if t['name'] in EXCLUDED:
                self.assertNotIn('real', t, t['name'])
            if 'real' in t:
                n += 1
                self.assertTrue(t.get('why', '').strip(), t['name'])
                for k in t['real']:
                    self.assertIn(k, ('x', 'z', 'r', 'h', 'hex', 'facade', 'crown', 'glass', 'podium'), (t['name'], k))
        self.assertGreater(n, 0)
        bt = (ROOT / 'bake_towers.py').read_text()
        self.assertIn('REAL_FIX = [', bt)


class Page(unittest.TestCase):
    def assertIn(self, a, b, msg=None):   # the source is 2 MB: a failure names the text, never prints the file
        self.assertTrue(a in b, msg or 'missing: %r' % a[:160])

    def assertNotIn(self, a, b, msg=None):
        self.assertTrue(a not in b, msg or 'present: %r' % a[:160])

    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_gated_on_the_realistic_look(self):
        s = self.src
        self.assertIn("const TOWN_ON = REAL && TSKIN_ON && !!TOWN_ART && !!renderer.capabilities.isWebGL2 && !/[?&]townart=0\\b/.test(location.search);", s)
        self.assertIn("if (REAL && typeof TOWERS !== 'undefined' && TOWERS && TOWERS.towers) for (const sp of TOWERS.towers) if (sp.real) Object.assign(sp, sp.real);", s)
        self.assertLess(s.index('for (const sp of TOWERS.towers) if (sp.real)'), s.index('  const TOWER_SPECS ='))   # before the specs are gridded
        self.assertIn('if (!TOWN_ON) return null;', cut(s, '  function townOf(', '  function townNote('))
        # the wide loop: a building lays no lottery skin, no house front, no mid-rise wall, and is never a glass part
        self.assertIn("const own = TOWN_ON && h >= 6 && t !== 8 && t !== 9 && !isGlassStyle(style) ? townOf(spec, poly, cx, cz) : null, ownStrip = own ? TOWN.hit : null;", s)
        self.assertIn('if (own) { /* Round 198: its own facade (townNote, with its walls below), no skin */ }', s)
        self.assertIn('if (t === 10 && !own) {', s)
        self.assertIn('else if (!mh && !spec) frontNote(', s)
        self.assertIn('if (MID_SKIN && !own && !mh && !spec', s)

    def test_one_program_float_streams_no_frag_depth(self):
        lay = cut(self.src, '  async function townLay(aniso, got) {', '  function townProbe() {')
        self.assertEqual(lay.count('customProgramCacheKey'), 1)
        self.assertIn("mat.customProgramCacheKey = () => 'tower-own|real' + (SKIN_GLASS ? '|glass' : '');", lay)
        for name, size in (('aTnCell', 4), ('aTnGrid', 4), ('aTnOff', 1), ('aSeed', 1), ('uv', 2), ('color', 3), ('normal', 3), ('position', 3)):
            self.assertIn("geo.setAttribute('%s', new THREE.Float32BufferAttribute(" % name, lay)
        self.assertNotIn('Uint8BufferAttribute', lay)
        self.assertNotIn('Int8BufferAttribute', lay)
        self.assertNotIn('gl_FragDepth', lay)
        self.assertNotIn('texture2D(', lay.split('mat.onBeforeCompile')[1].split('wxSurfacePatch(sh)')[0])   # every read is textureGrad
        self.assertIn('if (isTouch) freeTexOnUpload(t);', lay)

    def test_the_bases_stand_in_for_the_storefronts(self):
        s = self.src
        self.assertIn('const baseOwn = TOWN_ON ? TOWN.cands.filter((c) => c.g0 != null) : [];', s)
        self.assertIn('if (!c.art && !skinBaseOf(c)) continue;', s)

    def test_the_cladding_step_lays_them(self):
        step = cut(self.src, "  step('Cladding the towers'", "  step('Mirroring the city'")
        self.assertIn('artImage(artSrc(TOWN_ART.img, TOWN_ART.imgHalf)), artImage(artSrc(TOWN_ART.mask, TOWN_ART.maskHalf))', step)
        self.assertIn('if (townGot) await townLay(aniso, townGot);', step)
        self.assertIn('towerArt: townProbe', self.src)


if __name__ == '__main__':
    unittest.main()
