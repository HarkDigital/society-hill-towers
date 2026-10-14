"""Round 192, the glass towers (Mike: "Can we also update the glass textures of the skyscrapers that are glass?").

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
  under a pixel, the blocks keep the share) and the finished light blended, never its colour and amount apart.

Round 192's review: the frames are a texture array (a tile a system, REPEAT, mips: each axis filtered by its own footprint,
no isotropic cut to a flat mean), the procedural frame box filtered per axis (gBand, checked against brute force), the city
probe baked right behind the sky's with no gap or stillness rule and never before the clock's lighting, scaled by the sky
between bakes, read as it is outside its sphere, blurred where its hit is near, with no sun sprite; the frames' fill the sky
probe's; the folded roughness capped; the rooms' light by the ambient light; the skins' probe a computer's, for their windows
only within its sphere; the probe off on the recovery tier and its arrays freed; the rooms' pictures on the first dusk."""
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
        # the review: the residential towers wear a residential wall (homes lit room by room), never the unitized office's
        rooms = {x['id']: x['rooms'] for x in self.S['systems']}
        for name in ('The Laurel Rittenhouse Square (1911 Walnut)', '1919 Market'):
            self.assertEqual('home', rooms[named[name]['sys']], name)

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
        for c in cells:
            self.assertTrue(c['size'][0] <= 512 and c['size'][1] <= 512)
            self.assertTrue(0 <= c['sill'] < c['head'] <= 1, c)
            self.assertTrue(0.3 <= c['coverage'] + c['secondary'] <= 1.0, c)
            self.assertLess(c['disagree'], 0.16)
            self.assertEqual(3, len(c['frameMean']))
            self.assertNotIn('rect', c, 'the frames are a texture array now, no shelf atlas')

    def test_the_frames_strip(self):
        """Sixteen square tiles in a strip, a system a tile, each exactly periodic (its left column continues its right, its
        foot its head), so REPEAT and the mips filter it like the wall it is; a phone's half strip beside it."""
        from PIL import Image
        import numpy as np
        T = self.A['tile']
        self.assertEqual(256, T)
        for k, t in (('frames', T), ('framesHalf', T // 2)):
            p = ROOT / self.A[k]
            self.assertTrue(p.exists() and p.suffix == '.png', k)
            im = Image.open(p)
            self.assertEqual('RGB', im.mode, 'opaque RGB, never RGBA (WebKit premultiplies)')
            self.assertEqual((t, 16 * t), im.size)
        # the tiles are resampled periodically: a periodic module comes out periodic, its seam no different from its middle,
        # and the module's foot is the tile's first row (the page uploads the strip with flipY off)
        import importlib.util, sys
        spec = importlib.util.spec_from_file_location('bake_glass_art', ROOT / 'bake_glass_art.py')
        sys.path.insert(0, str(ROOT))
        B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
        h, w = 90, 130
        yy, xx = np.mgrid[0:h, 0:w]
        M = (127.5 + 100 * np.sin(2 * np.pi * (xx + 0.5) / w) * np.cos(2 * np.pi * (yy + 0.5) / h))
        M = np.repeat(M[..., None], 3, axis=2).clip(0, 255).astype(np.uint8)
        M[:3] = 255   # the module's head marked: it lands in the tile's last rows
        tl = B.tile(M, 64).astype(float)
        self.assertEqual((64, 64, 3), tl.shape)
        self.assertGreater(tl[-1].mean(), 200)
        body = tl[8:-8]
        seam = np.abs(body[:, 0] - body[:, -1]).mean()
        inside = np.abs(np.diff(body, axis=1)).mean(axis=(0, 2)).max()
        self.assertLessEqual(seam, inside * 1.05 + 1.5)
        self.assertNotIn('mask', self.A)
        self.assertNotIn('size', self.A)

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
        self.assertNotIn('roomsHalf', R, 'a phone never draws the rooms: no half copy shipped')
        self.assertNotIn('alb', self.A, "one fetch: the frame's detail rides the frames' blue")


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
        self.assertIn("const GLASS_ART_ON = GLASS_ON && !TIER2 && !!GLASS_DATA.frames &&", s)
        self.assertIn("const GLASS_ROOMS = GLASS_ART_ON && !GLASS_LITE &&", s)
        self.assertIn("on: GLASS_ON && !TIER2 && !/[?&]cityenv=0\\b/.test(location.search)", s)   # the review: off on the recovery tier
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
        a = s.index('  function cityEnvBake(only) {'); b = s.index('  function cityEnvTick() {')
        self.assertNotIn('scene.environment', s[a:b], 'the city probe must never become scene.environment (every program would change)')
        self.assertIn("if (!isTouch) return pmremGen;", s[s.index('  function cityEnvGen() {'):])
        self.assertIn("CITYENV.gen._setSize = function () { this._lodMax = 7; this._cubeSize = 128; };", s)
        # the proxy's streams: Float32 x 3 and Uint8 x 4, both 4-aligned, freed once uploaded
        self.assertIn("g.setAttribute('aP', new THREE.BufferAttribute(new Uint8Array(T.col.concat(S.col)), 4, true));", s)
        self.assertIn('for (const a of Object.values(g.attributes)) a.onUpload(dropUploadedArray);', s)
        # no sun sprite in the city's probe (the glint is the key light's)
        self.assertIn('const lend = [envSky], parents', s[a:b])

    def test_the_probe_follows_the_clock(self):
        """The review: a phone held a daylit probe into a night link and through a time-lapse (a 10 s gap, a still-only
        rule, and the build's own bake before the clock's lighting). The bake now runs on the frame refreshEnv asks, right
        after applyLighting, on every device; the build only builds; between bakes the probe follows the sky's light."""
        s = self.src
        tick = s[s.index('  function cityEnvTick() {'):s.index('  // the curtain wall\'s fragment work.')]
        self.assertNotIn('10000', tick); self.assertNotIn('active', tick); self.assertNotIn('isTouch', tick)
        self.assertIn('else if (CITYENV.pending) cityEnvBake(0);', tick)
        self.assertIn('CITYENV.u.uCityEnvK.value = Math.min(1, cityEnvLum() / CITYENV.lumAt);', tick)
        self.assertIn('    applyLighting();\n    if (CITYENV.built) cityEnvTick();', s)
        step = s[s.index("  step('Mirroring the city', () => {"):s.index("  function glassArtTex(im, srgb, aniso) {")]
        self.assertIn('cityEnvBuild();', step)
        self.assertNotIn('cityEnvBake(', step)
        self.assertIn("Object.assign(CITYENV, { scene: scene2, group, mesh, mat, tris: CITYENV.geoms.reduce((a, g) => a + g.attributes.position.count / 3, 0), built: true, pending: true });", s)
        self.assertIn('if (cityEnvReady) CITYENV.pending = true;', s)
        env = re.search(r'const GLASS_ENV_PARS = `(.*?)`;', s, re.S).group(1)
        self.assertIn('* uCityEnvK;', env)
        # City Hall in the proxy where the rebuilt block stands (Round 191's frame)
        self.assertIn('const chC = CH_ON ? [CITY_HALL.B0[0] + fl.dx * -2.3, CITY_HALL.B0[1] + fl.dz * -2.3] : [-1603, -802];', s)

    def test_parallax_and_near_hits(self):
        """A fragment outside the probe's sphere reads its ray as it is (the review's CPU port: a sky ray 37 degrees up
        fetched the ground); a hit within about 80 m, or a low wall's level ray, reads the probe blurred toward its mean."""
        env = re.search(r'const GLASS_ENV_PARS = `(.*?)`;', self.src, re.S).group(1)
        self.assertIn('if (c > 0.0) return r;', env)
        self.assertIn('gNear = 1.0 - smoothstep(25.0, 80.0, t);', env)
        self.assertIn('vec4 envMapColor = glassEnv( reflectVec, mix(roughness, 0.8, gNear) );', env)
        # port the sphere branch: inside, the corrected direction points at the ray's exit on the sphere
        def par(pw, r, C, R):
            p = [pw[i] - C[i] for i in range(3)]
            c = sum(v * v for v in p) - R * R
            if c > 0:
                return r
            b = sum(p[i] * r[i] for i in range(3))
            t = -b + math.sqrt(max(b * b - c, 0.0))
            q = [p[i] + r[i] * t for i in range(3)]
            n = math.sqrt(sum(v * v for v in q))
            return [v / n for v in q]
        up = [0.0, math.sin(math.radians(37)), math.cos(math.radians(37))]
        out = par([0, 150, -1800], up, [0, 110, 0], 1500)
        self.assertEqual(up, out)
        q = par([0, 150, 200], up, [0, 110, 0], 1500)
        self.assertGreater(q[1], 0.3)

    def test_the_frames_are_filtered_per_axis(self):
        """Must-fix 1: no isotropic footprint and no cut to the mean past three pixels a pane; each axis its own footprint, the
        frames' texture array with REPEAT and its mips, the procedural frame's band and mullions box filtered exactly."""
        main = re.search(r'const GLASS_SYS_MAIN = `(.*?)`;', self.src, re.S).group(1)
        self.assertNotIn('pp >= 3.0', main)
        self.assertNotIn('gmax', main)
        self.assertNotIn('max(fx, fy)', main)
        self.assertIn('float fx = max(length(vec2(dFdx(uB), dFdy(uB))), 1.0e-5), fy = max(length(vec2(dFdx(yF), dFdy(yF))), 1.0e-5);', main)
        self.assertIn('vec3 msk = texture(uGlassArr, vec3(uB / A.z, yF / A.w, sy)).rgb;', main)
        self.assertIn('float visV = gBand(yF, fy, vs, vh), glU = gBand(uB, fx, B.y, 1.0 - B.y);', main)
        glaze = self.src[self.src.index("  step('Glazing the towers'"):self.src.index('  // the street floors (critic gap 4)')]
        for frag in ('new THREE.DataArrayTexture(im, T, T, 16)', 't.wrapS = t.wrapT = THREE.RepeatWrapping;', 't.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true;',
                     't.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy() || 1);', 'artImage(artSrc(A.frames, A.framesHalf))'):
            self.assertIn(frag, glaze)
        # gBand is the exact box filter of a periodic band (against brute force)
        def band(x, w, a, b):
            x0, x1, L = x - w / 2, x + w / 2, b - a
            F = lambda t: math.floor(t) * L + min(max(t - math.floor(t), a), b)
            return min(max((F(x1) - F(x0)) / w, 0), 1)
        def brute(x, w, a, b, k=20000):
            return sum(1 for j in range(k) if a <= ((x - w / 2 + w * (j + 0.5) / k) % 1.0) <= b) / k
        for (x, w, a, b) in ((0.3, 0.2, 0.0, 0.8), (7.91, 3.3, 0.1, 0.75), (2.5, 0.01, 0.4, 0.6), (-4.2, 12.7, 0.02, 0.97)):
            self.assertAlmostEqual(band(x, w, a, b), brute(x, w, a, b), places=2)
        self.assertAlmostEqual(band(0.37, 40.0, 0.2, 0.7), 0.5, places=3)   # many periods: the band's share
        self.assertIn('return clamp(((floor(x1) * L + clamp(fract(x1), a, b)) - (floor(x0) * L + clamp(fract(x0), a, b))) / w, 0.0, 1.0);',
                      re.search(r'const GLASS_SYS_PARS = `(.*?)`;', self.src, re.S).group(1))

    def test_glints_and_panes(self):
        """Must-fix 7: the folded roughness is capped (a glint stays a glint) and each pane keeps its own tilt and tint to
        about two pixels a pane, on a phone too."""
        main = re.search(r'const GLASS_SYS_MAIN = `(.*?)`;', self.src, re.S).group(1)
        self.assertIn('gGlassR = min(sqrt(sqrt(a0 * a0 + aL * aL)), 0.095) + 0.012 * pq.z * jf;', main)
        self.assertIn('float jf = smoothstep(1.2, 3.0, pp), fade = smoothstep(3.0, 20.0, pp);', main)
        self.assertIn('(pq.xy - 0.5) * mix(0.022, 0.008, fade) * jf', main)

    def test_the_rooms_follow_the_ambient_light(self):
        """Must-fix 4: the rooms' light by the ambient light, ahead of the night term through the dusk (glassRoomLevel), the
        pictures loaded on the first dusk, a computer's only."""
        s = self.src
        self.assertIn('return Math.max(night, 1 - smooth(-3, 5, elAmb));', s)
        self.assertIn('glassU.uGlassL.value.x = glassRoomLevel(elAmb, night);', s)
        self.assertIn('if (GLASS_ROOMS && !GLASS.rooms.asked && glassU.uGlassL.value.x > 0.001) glassRoomsLoad();', s)
        hook = s[s.index('  function glassSysHook(sh) {'):s.index('  function glassSamplers(mat) {')]
        self.assertIn('totalEmissiveRadiance = (gRoomN * uGlassL.x + gRoomD * (1.0 - uGlassL.x)) * gVLT * (1.0 - Fr) * gVis;', hook)
        # at 18:25 on Oct 14 (the sun about 0.3 degrees up) the night term is near 0 and the rooms' level is not
        sm = lambda a, b, x: (lambda t: t * t * (3 - 2 * t))(min(max((x - a) / (b - a), 0), 1))
        night = 1 - sm(-9, 1, 0.3)
        self.assertLess(night, 0.05)
        self.assertGreater(max(night, 1 - sm(-3, 5, 0.3)), 0.5)

    def test_frames_take_the_sky_fill(self):
        """The review's grey ribbons at night: the frames' diffuse fill is the sky probe's (its dome over its street), never
        the city probe's lit windows and lamps; the skins keep the sky probe for their walls."""
        env = re.search(r'const GLASS_ENV_PARS = `(.*?)`;', self.src, re.S).group(1)
        self.assertIn('return PI * mix(uGlassIrrG, uGlassIrrS, 0.5 + 0.5 * worldNormal.y) * envMapIntensity;', env)
        s = self.src
        self.assertIn('const SKIN_GLASS = CITYENV.on && REAL && !isTouch;', s)
        skin = s[s.index('  const SKIN_ENV_PARS = `'):s.index('  // the towers\' cladding runs after the far ring')]
        self.assertIn('vec4 envMapColor = textureCubeUV( envMap, worldNormal, 1.0 );', skin)
        self.assertIn('rad = mix(rad, textureCubeUV( uCityEnvA, rv, mix(roughness, 0.8, gNear) ).rgb * uCityEnvK, tsMask.r * skInR);', skin)
        self.assertNotIn('CITYENV.mats.push(mat);   // Round 192: the city probe for its windows', s)
        self.assertIn("SKIN_GLASS ? '  diffuseColor.rgb *= mix(1.0, 0.6, win * (1.0 - tsBar) * skInR);' : '',", s)

    def test_samplers_within_budget(self):
        s = self.src
        pars = re.search(r'const GLASS_SYS_PARS = `(.*?)`;', s, re.S).group(1)
        env = re.search(r'const GLASS_ENV_PARS = `(.*?)`;', s, re.S).group(1)
        own = re.findall(r'uniform (?:mediump )?sampler2D(?:Array)? ([\w, ]+);', pars + env)
        names = [n.strip() for grp in own for n in grp.split(',')]
        self.assertEqual(['uGlassArr', 'uRooms', 'uCityEnvB'], names)
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
        self.assertIn('gRoomN = mix(farC * litFar, nearC * lit, nearK) * uGlassK.x;', main)   # two finished lights, blended
        self.assertNotIn('mix(nearC', main)

    def test_art_loads_free_on_a_phone(self):
        s = self.src
        a = s.index('  function glassArtTex(im, srgb, aniso) {'); b = s.index('  function glassRoomsLoad() {')
        self.assertIn('return freeTexOnUpload(t);', s[a:b])
        self.assertIn('artImage(artSrc(A.frames, A.framesHalf))', s)
        self.assertIn('glassU.uGlassArr.value = freeTexOnUpload(t);', s)
        self.assertIn("const GLASS_ART = ", (ROOT / 'build.py').read_text().replace('const("GLASS_ART", text_of("glass_art.json", "null"))', 'const GLASS_ART = '))


if __name__ == '__main__':
    unittest.main()
