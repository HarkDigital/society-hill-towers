"""Round 191, the glass towers (Mike: "Can we also update the glass textures of the skyscrapers that are glass?").

- glass_systems.json: the sixteen curtain-wall systems in range (F0 0.05 to 0.40, transmittance 0.08 to 0.85, bay 0.6 to
  3 m, floor 2.8 to 5 m), every towers.json glass tower named in 'towers' with a real system, every glass cladding kind
  mapped, FMC's floor on its LED rings' pitch (4.0) and Comcast's on its crown's (4.15);
- glass_art.json: the bake is current (its systems are glass_systems.json's), a cell for every system inside the atlas,
  eight rooms with their back walls and vanishing points;
- the system index rides the aSFT floor byte as -(sys + 1): VBuf (run under JavaScriptCore) keeps it through growth and
  geometry(true), and the shader decodes it;
- the wiring: GLASS_ON gates every new path (?real=0 and ?glass=0 build the old outer-glass hook untouched), one draw per
  glass wall (no skin over a routed or researched glass wall), the probe bound as the glass's own envMap, never
  scene.environment, the samplers inside the budget, the far rooms' arithmetic (the run cover is the run's true share
  under a pixel, the blocks keep the share) and the finished light blended, never its colour and amount apart."""
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLASS_FACADES = ('glass', 'glass_bands', 'glass_dark')


def fract(x):
    return x - math.floor(x)


def towers():
    d = json.loads((ROOT / 'towers.json').read_text())
    return d['towers'] if isinstance(d, dict) else d


def is_glass_tower(t):
    return t.get('facade') in GLASS_FACADES or (t.get('facade') == 'concrete_grid' and t.get('glass'))


class Systems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = json.loads((ROOT / 'glass_systems.json').read_text())

    def test_sixteen_systems_in_range(self):
        sy = self.S['systems']
        self.assertEqual(list(range(16)), [s['id'] for s in sy])
        for s in sy:
            self.assertTrue(0.05 <= s['F0'] <= 0.40, s['name'])
            self.assertTrue(0.08 <= s['VLT'] <= 0.85, s['name'])
            self.assertTrue(0.6 <= s['bay'] <= 3.0, s['name'])
            self.assertTrue(2.8 <= s['floor'] <= 5.0, s['name'])
            self.assertTrue(isinstance(s['nbM'], int) and 1 <= s['nbM'] <= 4 and isinstance(s['nfM'], int) and 1 <= s['nfM'] <= 3, s['name'])
            self.assertTrue(0 <= s['coatSat'] <= 1 and 0 <= s['pillow'] <= 0.01 and 0 <= s['roller'] <= 0.003, s['name'])
            self.assertIn(s['spandrel']['kind'], (0, 1, 2, 3))
            self.assertIn(s['rooms'], self.S['rooms'])
            self.assertTrue(0 <= s['frame']['metal'] <= 1 and 0 < s['frame']['rough'] <= 1 and isinstance(s['frame']['tint'], bool))
            self.assertTrue(re.fullmatch(r'#[0-9A-F]{6}', s['body']), s['name'])
            self.assertTrue(s['sources'], s['name'] + ' names no source')
            if s['upper']:
                self.assertTrue(0.05 <= s['upper']['F0'] <= 0.40 and 0.08 <= s['upper']['VLT'] <= 0.85 and s['upper']['datum'] > 50)
                self.assertIn(s['upper']['rooms'], self.S['rooms'])

    def test_every_glass_tower_is_named(self):
        named = self.S['towers']
        glass = [t['name'] for t in towers() if is_glass_tower(t)]
        self.assertGreater(len(glass), 30)
        missing = [n for n in glass if n not in named]
        self.assertEqual([], missing, 'towers.json glass towers with no system in glass_systems.json')
        for name, e in named.items():
            self.assertTrue(0 <= e['sys'] < 16, name)
            if 'body' in e:
                self.assertTrue(re.fullmatch(r'#[0-9A-F]{6}', e['body']), name)
        # the research's two reassignments (Mike's call to keep): 1818 Market is white concrete ribbons, The Laurel warm grey
        self.assertEqual(7, named['1818 Market Street']['sys'])
        self.assertEqual('#8E8A82', named['The Laurel Rittenhouse Square (1911 Walnut)']['body'])

    def test_every_glass_kind_is_mapped(self):
        src = (ROOT / 'app.js').read_text()
        alt = re.search(r"const TOWER_TILE_ALT = \{ glass: \[([^\]]*)\], glassdark: \[([^\]]*)\]", src)
        kinds = set(re.findall(r"'(\w+)'", alt.group(1) + alt.group(2))) | {'glassresi', 'blueband'}
        self.assertEqual(kinds, set(self.S['glassKinds']))
        for k in self.S['glassKinds']:
            g = self.S['generic'][k]
            for v in (g if isinstance(g, list) else [g]):
                self.assertTrue(0 <= v < 16, k)
        self.assertEqual(self.S['styleDefault'], {'20': 14, '21': 12, '22': 6, '23': 14, '24': 1, '25': 0, '26': 2, '27': 4, '28': 3, '29': 5, '30': 14, '3': 14})

    def test_the_floors_meet_the_led_lines(self):
        src = (ROOT / 'app.js').read_text()
        fmc = next(s for s in self.S['systems'] if s['name'] == 'fmc')
        comcast = next(s for s in self.S['systems'] if s['name'] == 'comcast')
        self.assertIn('const lw = lit.clone().multiplyScalar(0.6), fp = 4.0;', src)   # FMC's rings, k2 x 4.0 from the base
        self.assertIn('const fp = th.style === 25 ? 4.15 : 4.0, lw = lit.clone().multiplyScalar(0.6);', src)   # the Comcast crown's LED floors
        self.assertEqual(4.0, fmc['floor'])
        self.assertEqual(4.15, comcast['floor'])
        self.assertEqual(4.42, next(s for s in self.S['systems'] if s['name'] == 'ctc')['floor'])


class Art(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = json.loads((ROOT / 'glass_systems.json').read_text())
        cls.A = json.loads((ROOT / 'glass_art.json').read_text())

    def test_the_bake_is_current(self):
        for k in ('systems', 'towers', 'generic', 'glassKinds', 'styleDefault'):
            self.assertEqual(self.S[k], self.A[k], k + ' differs from glass_systems.json: re-run bake_glass_art.py')

    def test_a_cell_for_every_system(self):
        cells = self.A['cells']
        self.assertEqual(list(range(16)), [c['sys'] for c in cells])
        W, H = self.A['size']
        self.assertEqual([2048, 1024], [W, H])
        for c in cells:
            u0, v0, du, dv = c['rect']
            self.assertTrue(0 <= u0 and u0 + du <= 1 and 0 <= v0 and v0 + dv <= 1, c)
            self.assertTrue(c['size'][0] <= 512 and c['size'][1] <= 512)
            self.assertTrue(0 <= c['sill'] < c['head'] <= 1, c)
            self.assertTrue(0.3 <= c['coverage'] + c['secondary'] <= 1.0, c)
            self.assertLess(c['disagree'], 0.16)
            self.assertEqual(3, len(c['frameMean']))
        # no two cells overlap, gutters included
        boxes = [(round(c['rect'][0] * W) - 8, round((1 - c['rect'][1] - c['rect'][3]) * H) - 8, round(c['rect'][2] * W) + 16, round(c['rect'][3] * H) + 16) for c in cells]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                self.assertFalse(a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3], (a, b))

    def test_rooms(self):
        R = self.A['rooms']
        self.assertEqual([1536, 1152], R['roomSize'])
        cells = R['roomCells']
        self.assertEqual(8, len(cells))
        self.assertEqual(['office'] * 4 + ['home'] * 2 + ['hotel', 'mech'], [c['kind'] for c in cells])
        for c in cells:
            self.assertTrue(all(0.1 < b < 0.8 for b in c['b']), c['id'])
            self.assertTrue(all(0.3 < v < 0.7 for v in c['vp']), c['id'])
            self.assertTrue(all(0 < m < 1 for m in c['meanLit']), c['id'])
        for k in ('mask', 'maskHalf'):
            self.assertTrue((ROOT / self.A[k]).exists(), k)
        self.assertNotIn('alb', self.A, "one atlas: the frame's detail rides the mask's blue (one fetch a fragment)")
        self.assertTrue(self.A['mask'].endswith('.png') and self.A['maskHalf'].endswith('.png'), 'the masks are opaque PNGs')


JXA = r'''ObjC.import("Foundation");
function readFile(p) { return $.NSString.stringWithContentsOfFileEncodingError($.NSString.alloc.initWithUTF8String(p), 4, null).js; }
(0, eval)(readFile(%(three)s));
function freeOnUpload(g) {}
var VB = (function () { %(snippet)s
  return { VBuf: VBuf }; })();
var b = new VB.VBuf(4), out = [];
for (var s = 0; s < 16; s++) for (var i = 0; i < 3; i++) b.push(s, i, 0, 1, 0, 0, 0.5, 0.5, 0.5, 30, 2.0, -(s + 1) / 10, 0.4, 0, 10, 50);
var g = b.geometry(true), a = g.attributes.aSFT.array;
function i8(u) { return u > 127 ? u - 256 : u; }
var f = Math.fround;
for (var k = 0; k < 48; k++) {
  var v = f(a[k * 4 + 1] / 255), bb = Math.floor(f(f(v * 255) + 0.5)), fl = bb > 127.5 ? bb - 256 : bb;
  out.push(fl < -0.5 ? -fl - 1 : -1);
}
JSON.stringify({ sys: out, style: i8(a[0]), n: g.attributes.position.count, facade: !!g.attributes.aFacade });'''


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_the_system_rides_the_floor_byte(self):
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        a = self.src.index('\n  class IdxBuf {'); b = self.src.index('\n  const groupCity = new THREE.Group();')
        script = JXA % {'three': json.dumps(str(ROOT / 'three.min.js')), 'snippet': self.src[a:b]}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=180)
        self.assertEqual(0, r.returncode, (r.stderr or r.stdout)[:600])
        out = json.loads(r.stdout.strip())
        self.assertEqual([s for s in range(16) for _ in range(3)], out['sys'], 'the shader decode must return every system through growth')
        self.assertEqual(30, out['style']); self.assertEqual(48, out['n']); self.assertTrue(out['facade'])
        self.assertIn('const glassFh = (sys) => -(sys + 1) / 10;', self.src)
        self.assertIn('{ float fl = aFloorH; vGSy = fl < -0.5 ? -fl - 1.0 : -1.0; }', self.src)
        self.assertIn("const isGlassStyle = (style) => style >= 20 && style < 32;", self.src)   # style 30, the generic curtain wall, is inside it

    def test_gates(self):
        s = self.src
        self.assertIn("if (!REAL || !GLASS_DATA || !renderer.capabilities.isWebGL2 || /[?&]glass=0\\b/.test(location.search)) return false;", s)
        self.assertIn('return gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS) >= 512;', s)
        self.assertIn("const GLASS_ART_ON = GLASS_ON && !TIER2 &&", s)
        self.assertIn("const GLASS_ROOMS = GLASS_ART_ON && !GLASS_LITE &&", s)
        self.assertIn("on: GLASS_ON && !/[?&]cityenv=0\\b/.test(location.search)", s)
        # the old hook is whole and only replaced under GLASS_ON
        a = s.index('        outerGlassMat.onBeforeCompile = (sh) => {')
        b = s.index('        if (GLASS_ON) glassSysMat(outerGlassMat);', a)
        old = s[a:b]
        self.assertIn("glassOpticsPatch(sh,{mask:'gGlazing',normal:'vGNm',uv:'gPaneUV',id:'gPaneID',seed:'vGT*7.1',coating:.14,roughness:.075,depth:.86});", old)
        self.assertEqual('3fec7d8ddb', hashlib.sha256(old.encode()).hexdigest()[:10], 'the pre-Round-191 outer glass hook must stay byte for byte (?real=0, ?glass=0)')
        # every new routing branch asks GLASS_ON
        self.assertIn('const gSys = GLASS_ON && isGlassStyle(style) ? glassSysOfSpec(spec, style) : -1;', s)
        self.assertIn('if (GLASS_ON && !spec && base + hTop - ys0 >= 30) gRoute = glassGenericSys(skinKindOf(style, null, i, t), i);', s)
        self.assertIn("if (GLASS_ON && TSKIN_ON && !rplan) { const mk = midSkinKindOf(style, i + 0.11, t, fa); if (mk === 'glass' || mk === 'unitized') gMid = glassGenericSys(mk, i); }", s)

    def test_one_draw_per_glass_wall(self):
        s = self.src
        # a researched glass wall lays no skin; a routed generic wall lays none; its roof stays on the fabric chunk
        self.assertIn('if (gSys >= 0) { if (TSKIN_ON && base + hTop - ys0 >= 30 && !(style >= 24 && style <= 29)) GLASS.skinsSkipped++; }', s)
        self.assertIn('if (gRoute < 0) towerSkinNote(poly, mh > 0 ? base + mh : base, base + hTop, style, spec, i, c, mh > 0, t);', s)
        self.assertIn('appendBuilding(getGlassChunk(cx, cz), poly, mh > 0 ? base + mh : base - 1.0, base + hTop, glassBody(gs, i, _glBody), 30, base, null, glassFh(gs), capCol, false, chk);', s)
        self.assertIn('const cch = capCh || ch;', s)
        self.assertIn('function skinKindOf(style, spec, seed, t) {', s)
        self.assertIn('const kind = skinKindOf(style, spec, seed, t);', s)

    def test_the_probe_is_the_glass_own(self):
        s = self.src
        self.assertIn('if (only !== 1) for (const m of CITYENV.mats) m.envMap = CITYENV.rts[0].texture;', s)
        a = s.index('  function cityEnvBake(only) {'); b = s.index('  function cityEnvTick(now, active) {')
        self.assertNotIn('scene.environment', s[a:b], 'the city probe must never become scene.environment (every program would change)')
        self.assertIn("if (!isTouch) return pmremGen;", s[s.index('  function cityEnvGen() {'):])
        self.assertIn("CITYENV.gen._setSize = function () { this._lodMax = 7; this._cubeSize = 128; };", s)
        # the proxy's streams: Float32 x 3 and Uint8 x 4, both 4-aligned
        self.assertIn("g.setAttribute('aP', new THREE.BufferAttribute(new Uint8Array(T.col.concat(S.col)), 4, true));", s)
        self.assertIn("now - CITYENV.at < (isTouch ? 10000 : 1500)", s)
        self.assertIn('if (isTouch && active) return;', s)

    def test_samplers_within_budget(self):
        s = self.src
        pars = re.search(r'const GLASS_SYS_PARS = `(.*?)`;', s, re.S).group(1)
        env = re.search(r'const GLASS_ENV_PARS = `(.*?)`;', s, re.S).group(1)
        own = re.findall(r'uniform sampler2D ([\w, ]+);', pars + env)
        names = [n.strip() for grp in own for n in grp.split(',')]
        self.assertEqual(['uGlassMsk', 'uRooms', 'uCityEnvB'], names)
        # with envMap and the two shadow maps: 6 on a computer of 16, 4 on a phone (no rooms, no second probe)
        self.assertLessEqual(len(names) + 1 + 2, 6)

    def test_far_rooms_arithmetic(self):
        """gRunCover is the lit run's true share of the rooms under a pixel; the far blocks keep the share."""
        def cover(a, b, L, n):
            ia = math.floor(a / n) * L + min(a - math.floor(a / n) * n, L)
            ib = math.floor(b / n) * L + min(b - math.floor(b / n) * n, L)
            return min(max((ib - ia) / max(b - a, 1e-4), 0), 1)
        def brute(a, b, L, n, k=4000):
            return sum(1 for j in range(k) if ((a + (b - a) * (j + 0.5) / k) % n) < L) / k
        for (a, b, L, n) in ((0.3, 4.7, 3, 10), (-7.2, 15.1, 6, 9), (12.0, 12.5, 2, 5), (3.1, 41.0, 7, 12)):
            self.assertAlmostEqual(cover(a, b, L, n), brute(a, b, L, n), places=2)
        glsl = re.search(r'const GLASS_SYS_PARS = `(.*?)`;', self.src, re.S).group(1)
        self.assertIn('float ia = floor(a / n) * L + min(a - floor(a / n) * n, L);', glsl)
        # the blocks: lit at the share by their own hash, so a wall of them keeps the share
        def gh(x, y):
            q = [fract(x * .1031), fract(y * .1031), fract(x * .1031)]
            d = q[0] * (q[1] + 33.33) + q[1] * (q[2] + 33.33) + q[2] * (q[0] + 33.33)
            q = [v + d for v in q]
            return fract((q[0] + q[1]) * q[2])
        for share in (0.2, 0.55):
            for L in (1, 2, 3):
                lit = [1 if gh(i + L * 17.0 + 0.37, j + L * 5.3 + 0.37) > 1 - share else 0 for i in range(60) for j in range(60)]
                self.assertAlmostEqual(share, sum(lit) / len(lit), delta=0.04)

    def test_the_finished_light_is_blended(self):
        """Round 159's rule on the glass: the room's light is its colour times the lit share as one finished light (a dark
        room gives nothing), never a lit colour and a lit amount blended apart."""
        main = re.search(r'const GLASS_SYS_MAIN = `(.*?)`;', self.src, re.S).group(1)
        self.assertIn('gRoomN = nightC * lit * uGlassK.x;', main)
        self.assertNotIn('mix(nightC', main)
        hook = self.src[self.src.index('  function glassSysHook(sh) {'):self.src.index('  function glassSysMat(mat) {')]
        self.assertIn('totalEmissiveRadiance = (gRoomN * uNight + gRoomD * (1.0 - uNight)) * gVLT * (1.0 - Fr) * gVis;', hook)

    def test_art_loads_free_on_a_phone(self):
        s = self.src
        a = s.index('  function glassArtTex(im, srgb, aniso) {'); b = s.index("  step('Glazing the towers'")
        self.assertIn('return freeTexOnUpload(t);', s[a:b])
        self.assertIn('artImage(artSrc(A.mask, A.maskHalf))', s)
        self.assertIn("const GLASS_ART = ", (ROOT / 'build.py').read_text().replace('const("GLASS_ART", text_of("glass_art.json", "null"))', 'const GLASS_ART = '))


if __name__ == '__main__':
    unittest.main()
