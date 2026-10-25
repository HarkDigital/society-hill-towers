"""The realism pass, the ground and the vegetation (Oct 12, Mike: "please do anything necessary to make this look more photo
realistic and less cartoony. This should apply to all surfaces/water/anything you can improve to look more real").

- the tree cards: the atlas keeps its colour premultiplied (the 1 to 2 px black outline round every crown from the air
  was the canvas's clear texels uploaded as black and mipped into the edges), each tree is its own (mirror, size, width,
  tint from its seed), the card is lit as a dome, a tree turns over a stretch of the change and dissolves between its two
  pictures, autumn comes in mid-October through a turning picture, and snow lies on the boughs;
- a computer at the full tier draws the cells at the bake's 448 and 224 on a canvas as tall as its rows, a phone keeps 128
  and 64;
- the lawn's photographed colour, the parks' macro from the air, the yards on built-up ground (LAND_MASK), the woods'
  canopy and the wood field, the rivers' banks (riprap, wet silt, the tide's stain), the canopy map's shade and leaf fall;
- the tufts packed near the eye in the lawn's own colour, flattened by snow; the snow cover in drifts, not squares.
?real=0 keeps the old ground, line for line."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def fn(src, name):
    a = src.index('  function ' + name + '(')
    return src[a:src.index('\n  }\n', a) + 4]


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_the_atlas_is_premultiplied_and_divided_back(self):
        s = self.s
        self.assertIn('tex.premultiplyAlpha = true;', fn(s, 'treeArtAtlas'))
        self.assertIn("tx.rgb = min(tx.rgb / max(tx.a, 0.004), vec3(1.0));", s)

    def test_each_tree_is_its_own(self):
        s = self.s
        a = s.index('  const TREE_ART_VERT = ')
        v = s[a:s.index('  }`;', a)]
        self.assertIn('mix(position.x + 0.5, 0.5 - position.x, step(0.5, v1))', v)   # mirrored by its seed
        self.assertIn('* (0.92 + 0.16 * v2)', v)                                     # its size
        self.assertIn("- ${REAL ? '0.035 * S * (1.0 - lean)'", v)                       # the root plate under the grass
        self.assertIn('float turn = smoothstep(seedT * 0.7, seedT * 0.7 + 0.3, L1.x);', v)   # inside the change, always
        self.assertIn('nrmOut = normalize(rt * q.x * 0.75 + up * q.y * 0.75 + nC * 0.65 + vec3(0.0, 0.25, 0.0));', v)
        self.assertIn("seedT = abs(aLS.y);", v)                                # a wood field tree's seed is negative
        # the look behind REAL (the review: ?real=0 showed the realism pass's trees): size, width, sink, mirror, the dome
        self.assertIn("float S = mix(H / hf, D / df, tw)${REAL ? ' * (0.92 + 0.16 * v2)' : ''};", v)
        self.assertIn("${REAL ? '0.035 * S * (1.0 - lean)' : '0.03 * (1.0 - lean)'}", v)
        self.assertIn("vec2 cs = ${REAL ? 'vec2(mix(position.x + 0.5, 0.5 - position.x, step(0.5, v1)), yy)' : 'vec2(position.x + 0.5, yy)'};", v)
        self.assertIn(": 'nrmOut = normalize(mix(vec3(fh.x * 0.45, 1.0, fh.y * 0.45), vec3(0.0, 1.0, 0.0), tw));'}", v)
        p = fn(s, 'treeArtPatch')
        self.assertIn("(depth ? '' : '  diffuseColor.rgb *= pow(tx.rgb, vec3(2.2));\\n' + (REAL ?", p)
        self.assertIn("tx.rgb = min(tx.rgb / max(tx.a, 0.004), vec3(1.0));", p)   # the premultiply fix holds either way

    def test_the_turning_picture_is_scattered(self):
        s = self.s
        a = s.index('  const TREE_PICK = REAL ? [')
        k = s[a:s.index(";\n", s.index("vec4 tPick(sampler2D s, vec4 uv, float k) { if (k <= 0.001)", a)) + 2]
        self.assertIn('smoothstep(tNa - 0.15, tNa + 0.15, k * 1.3 - 0.15)', k)          # the change comes in leaf clumps
        self.assertIn('if (mod(tTp, 2.0) > 0.5) a = tGreen(a); if (tTp > 1.5) b = tGreen(b);', k)
        self.assertIn("TREEART.uLk.value[li].w = (st[0] === 'turning' ? 1 : 0) + (st[1] === 'turning' ? 2 : 0);", s)

    def test_the_atlas_goes_up_by_the_cell(self):
        s = self.s
        a = fn(s, 'treeArtAtlas')
        self.assertIn('tex.onUpdate = () => { if (at.live) return; at.live = true; at.cv.width = at.cv.height = 1; at.ctx = null; };', a)
        f = fn(s, 'atlasFlush')
        self.assertIn('renderer.copyTextureToTexture(_atPos.set(x, at.AH - y - at.N), c.tex, at.tex);', f)
        self.assertIn('at.tex.generateMipmaps = mips && i === at.pend.length - 1;', f)   # the mips once a flush
        self.assertIn('if (!at.live) at.tex.needsUpdate = true;', f)                      # never the freed canvas again
        a = s.index('  async function treeArtSeason(force) {')
        self.assertNotIn('tex.needsUpdate = true', s[a:s.index('\n  }\n', a)])

    def test_the_wood_field(self):
        s = self.s
        w = fn(s, 'woodAt')
        self.assertIn("M.gb[(j * M.w + i) * 2] === 0) return null;", w)   # its own texel: water or a railway
        st = fn(s, 'woodStep')
        self.assertIn('const g = m[0] + 0.3 * (woodNoise(x, z) - 0.5);', st)
        self.assertEqual(st.count('needsUpdate = true'), 2)                # the matrices and aLS, once, at the sow's end
        end = st[st.index('if (W.row > 2 * n || W.k >= W.N) {'):]
        self.assertIn('im.instanceMatrix.needsUpdate = true; W.ls.needsUpdate = true;', end)
        self.assertIn("!/[?&]woods=0\\b/.test(location.search)", s)

    def test_a_phone_carries_less(self):
        s = self.s
        self.assertIn("if (isTouch) shader.fragmentShader = '#define VEG_NO_RIPRAP\\n' + shader.fragmentShader;", fn(s, 'vegSurfPatch'))
        self.assertIn("names.delete(name);", fn(s, 'vegSamplers'))
        self.assertIn("new THREE.InstancedBufferAttribute(CANOPYMAP.data, 4).onUpload(dropUploadedArray)", s)
        self.assertIn("CANOPYMAP.data = null;", fn(s, 'canopyMapUpdate'))
        v = fn(s, 'loadVegArt')
        self.assertIn("VEG_ART.parkmacro && !TIER2", v)
        self.assertIn("VEG_ART.alley && !TIER2", v)

    def test_snow_on_the_trees_and_the_ground(self):
        s = self.s
        self.assertIn("uSnowAcc: wxSurfU.uSnowAcc, uTexelS: { value: 1.5 / S.AH }", s)
        # the drifts under REAL; ?real=0 keeps Round 185's 1.1 m hash (the review: every look change behind the flag)
        self.assertIn("REAL ? 'float wxN = smoothstep(0.25, 0.75, 0.55 * cshn(wxWP.xz * 0.08)", s)
        self.assertIn(": 'float wxN = fract(sin(dot(floor(wxWP.xz * 0.9), vec2(127.1, 311.7))) * 43758.5453);',", s)
        self.assertIn("(REAL ? ' diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.80, 0.83, 0.87), uSnowAcc * smoothstep(-0.2, 0.9, vCY) * 0.85);' : '')", s)
        self.assertIn("transformed.y *= 1.0 - smoothstep(0.15, 0.45, uSnowAcc);", s)  # the tufts lie down

    def test_the_tufts(self):
        s = self.s
        self.assertIn('GRASS_R = REAL ? (isTouch ? 30 : 45) : (isTouch ? 140 : 160);', s)
        self.assertIn("normal_fragment_begin.replace('normal = normal * faceDirection;', '')", fn(s, 'grassInit'))

    def test_the_old_ground_stays_under_real_off(self):
        g = fn(self.s, 'vegGrassGLSL')
        self.assertIn('if (!REAL) return pre.concat([', g)
        self.assertIn("MEADOW_GAIN.toFixed(2)", g)
        self.assertIn('if (!REAL) return;', fn(self.s, 'vegSurfPatch'))
        self.assertIn("if (!REAL) return '';", fn(self.s, 'vegAfterGLSL'))

    def test_the_wiring(self):
        s = self.s
        self.assertIn('...vegGrassGLSL(forced, paved),', s)   # the integration's paved flag (sixteen texture units)
        self.assertIn('vegSurfPatch(shader, forced, paved);', fn(s, 'surfTexPatch'))
        self.assertIn('vegUpdate(now);', s)
        self.assertIn("step('Planting the woods', woodInit);", s)
        self.assertIn("const WOOD = { on: REAL && !isTouch && TIER === 0 && TREE_ART_ON && ", s)   # never on a phone
        self.assertIn("const VEG_LAND = REAL && !TIER2 && typeof LAND_MASK !== 'undefined'", s)
        # the canopy map's quads seen from above wind clockwise: drawn both sides or none draws
        self.assertIn('depthTest: false, depthWrite: false, side: THREE.DoubleSide,', fn(s, 'canopyMapUpdate'))
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("LAND_MASK", text_of("land_mask.json", "null"))', b)
        self.assertIn('"land_mask.json"', b)

    def test_the_tide_band_is_one_snippet(self):
        s = self.s
        self.assertEqual(s.count('float tideK(float tH)'), 1)
        self.assertIn('function tidePatch(shader, worldExpr) {', s)
        self.assertIn("im.material.onBeforeCompile = (sh) => tidePatch(sh, 'cameraPosition - vViewPosition * mat3(viewMatrix)');", s)   # the piers' piles

    def test_every_extra_picture_can_go(self):
        # the texture budget: the ground's patch ends by counting, and each extra picture's declaration and every read of it
        # sit inside its own #ifndef, or a define would leave a read of an undeclared sampler and the program would not link
        s = self.s
        body = fn(s, 'surfTexPatch')
        self.assertTrue(body.rstrip().endswith("vegBudget(shader, forced ? 'ground' : paved ? 'paved' : 'surface');   // last: within the GPU's texture units, whatever the passes added\n  }"))
        for define, name in (('VEG_NO_RIPRAP', 'uRiprap'), ('VEG_NO_MACRO', 'uMacro'), ('VEG_NO_ALLEY', 'uAlley'), ('VEG_NO_CANOPY', 'uCanopy')):
            self.assertIn("['" + define + "', '" + name + "']", s)
            uses = [i for i in range(len(s)) if s.startswith('texture2D(' + name + ',', i) or s.startswith('uniform sampler2D ' + name + ';', i)]
            self.assertGreater(len(uses), 1, name)
            for i in uses:
                opened, closed = s.rfind('#ifndef ' + define, 0, i), s.rfind('#endif', 0, i)
                self.assertGreater(opened, closed, name + ' read outside its #ifndef')
                self.assertLess(i - opened, 1200, name)
                self.assertNotIn('sampler2D ' + name + ',', s)      # never in a list a define cannot split
                self.assertNotIn(', ' + name + ';', s)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Seasons(unittest.TestCase):
    def test_the_turn(self):
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const TREE_CAL = {')
        cal = s[a:s.index('\n  };\n', a) + 5]
        js = cal + fn(s, 'treeSeasonOf') + r'''
const doy = (m, d) => Math.round((Date.UTC(2026, m - 1, d) - Date.UTC(2026, 0, 1)) / 864e5);
const at = (look, m, d, t) => treeSeasonOf(look, doy(m, d), t);
console.log(JSON.stringify({ oct12Plane: at('plane', 10, 12, true), oct20Maple: at('redmaple', 10, 20, true),
  nov1Maple: at('redmaple', 11, 1, true), nov20Oak: at('redoak', 11, 20, true), dec1Plane: at('plane', 12, 1, true), nov25Plane: at('plane', 11, 25, true),
  dec31Oak: at('redoak', 12, 31, true), oct30NoTurn: at('broadleaf', 10, 30, false) }));
'''
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o['oct12Plane'][:2], ['summer', 'summer'])        # mid-October: the planes are still green
        self.assertEqual(o['oct20Maple'][:2], ['summer', 'turning'])       # the red maples first, a fifth coloured
        self.assertEqual(o['nov1Maple'][:2], ['turning', 'autumn'])
        self.assertEqual(o['nov20Oak'][:2], ['turning', 'autumn'])   # the oaks last
        self.assertEqual(o['nov25Plane'][:2], ['autumn', 'autumn'])        # the planes hold their leaves into late November
        self.assertEqual(o['dec1Plane'][:2], ['autumn', 'winter'])
        self.assertEqual(o['dec31Oak'][:2], ['winter', 'winter'])   # the oaks hold theirs into December
        self.assertEqual(o['oct30NoTurn'][:2], ['summer', 'autumn'])       # a look without a turning picture goes straight

    def test_the_budget(self):
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const VEG_DROP = ')
        decl = s[a:s.index('\n', s.index('  const VEG_BUDGET = ', a)) + 1]
        b = s.index('  const VEG_THREE_MAPS = ')
        decl += s[b:s.index('];', b) + 3]
        js = ('const REAL = true; let location = { search: "" }; const renderer = { capabilities: { maxTextures: 16 } };\n' +
              decl.replace('const VEG_TEX', 'let VEG_TEX') + fn(s, 'vegSamplers') + fn(s, 'vegBudget') + r'''
const own = 'uniform sampler2D uGrass; uniform sampler2D uGrass2;\nuniform sampler2D uAsph, uConc, uBrick; uniform vec3 uStM;\nuniform sampler2D uLand;\n' +
  '#ifndef VEG_NO_MACRO\nuniform sampler2D uMacro;\n#endif\n#ifndef VEG_NO_CANOPY\nuniform sampler2D uCanopy;\n#endif\n#ifndef VEG_NO_RIPRAP\nuniform sampler2D uRiprap;\n#endif\n' +
  'uniform sampler2D uCanMap; uniform vec4 uCanBox;\nuniform sampler2D uLampMap, uLampNear; uniform vec4 uLampBox;\n';
const three = '#ifdef USE_SHEENCOLORMAP\n\tuniform sampler2D sheenColorMap;\n#endif\n#ifdef USE_SPECULARCOLORMAP\n\tuniform sampler2D specularColorMap;\n#endif\n';
const par = (extra, shadows) => ({ fragmentShader: three + extra + own, envMap: true, shadowMapEnabled: true, numDirLightShadows: shadows, numSpotLightShadows: 0, numPointLightShadows: 0 });
const out = {};
let p = par('', 1); vegBudget(p, 'mine'); out.mine = [vegSamplers(p).n, p.fragmentShader.indexOf('#define') < 0];
p = par('uniform sampler2D uWxLampMap; uniform vec4 uWxLampBox;\nuniform sampler2D uLotTex;\n', 2); vegBudget(p, 'lot');
out.lot = [vegSamplers(p).n, (p.fragmentShader.match(/#define VEG_NO_\w+/g) || [])];
p = par('uniform sampler2D uA[4];\n', 2); vegBudget(p, 'many');
out.many = [vegSamplers(p).n, (p.fragmentShader.match(/#define VEG_NO_\w+/g) || [])];
VEG_TEX = 11; p = par('', 1); vegBudget(p, 'pinned');
out.pinned = (p.fragmentShader.match(/#define VEG_NO_\w+/g) || []);
out.seen = VEG_BUDGET.seen;
console.log(JSON.stringify(out));
''')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o['mine'], [14, True])                   # ten of its own, the lamps' two, envMap, one shadow: 14, kept whole
        self.assertEqual(o['lot'][0], 16)                          # 17 (the weather's lamp read, a lot's stripes, a second shadow), counted again after the drop
        self.assertEqual(o['lot'][1], ['#define VEG_NO_RIPRAP'])   # one over: the riprap goes, the rest stays
        self.assertEqual(o['many'][1], ['#define VEG_NO_CANOPY', '#define VEG_NO_MACRO', '#define VEG_NO_RIPRAP'])   # an array counts each
        self.assertEqual(o['pinned'], ['#define VEG_NO_CANOPY', '#define VEG_NO_MACRO', '#define VEG_NO_RIPRAP'])
        self.assertEqual(o['seen']['lot 17']['drop'], ['uRiprap'])
        self.assertNotIn('sheenColorMap', o['seen']['lot 17']['own'])

    def test_a_computer_draws_the_bake_size(self):
        s = (ROOT / 'app.js').read_text()
        d = json.loads((ROOT / 'tree_art.json').read_text())
        js = ('const THREE = { CanvasTexture: function (c) { this.image = c; } };\n'
              'const renderer = { capabilities: { isWebGL2: true, getMaxAnisotropy: () => 8 } };\n'
              'const document = { createElement: () => ({ getContext: () => ({}) }) };\n'
              'const TREE_ART = ' + json.dumps({k: d[k] for k in ('looks', 'side', 'top')}) + ';\n'
              'const out = [];\n'
              'for (const [isTouch, TIER] of [[false, 0], [false, 1], [true, 0]]) {\n' + fn(s, 'treeArtAtlas') +
              '  for (const v of ["side", "top"]) { const a = treeArtAtlas(v); out.push([isTouch, TIER, v, a.N, a.A, a.AH, a.C, a.tex.premultiplyAlpha]); }\n}\n'
              'console.log(JSON.stringify(out));')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = {(t, k, v): (N, A, AH, C, pm) for t, k, v, N, A, AH, C, pm in json.loads(r.stdout)}
        cells = 2 * len(d['looks'])
        self.assertEqual(got[(False, 0, 'side')][:2], (448, 448 * 8))
        self.assertGreaterEqual(got[(False, 0, 'side')][2], -(-cells // 8) * 448)
        self.assertEqual(got[(False, 1, 'side')][:3], (256, 2048, 2048))   # a lighter tier keeps Round 184's canvas
        self.assertEqual(got[(True, 0, 'side')][:3], (128, 1024, 1024))    # a phone keeps its 128 cells
        self.assertEqual(got[(True, 0, 'top')][:3], (64, 512, 512))
        self.assertTrue(all(v[4] for v in got.values()))


class Data(unittest.TestCase):
    def test_the_trees_turn_and_mute(self):
        d = json.loads((ROOT / 'tree_art.json').read_text())
        self.assertEqual((d['side'], d['top']), (448, 224))
        turning = [lk for lk in d['looks'] if 'turning' in d['images'][lk]['side']]
        self.assertEqual(len(turning), 25)                                  # every look that colours but the evergreens
        for lk in ('pine', 'spruce', 'holly'):
            self.assertNotIn(lk, turning)
        b = (ROOT / 'bake_tree_art.py').read_text()
        self.assertIn("MUTE = {'autumn': (0.82, 0.95), 'spring': (0.82, 0.95)}", b)

    def test_the_ground_set(self):
        d = json.loads((ROOT / 'ground_art.json').read_text())['veg']
        self.assertEqual(set(d), {'parkmacro', 'canopy_summer', 'canopy_autumn', 'canopy_winter', 'riprap', 'alley', 'snow'})   # the realism round two: the lying snow
        from PIL import Image
        for k, rec in d.items():
            self.assertEqual(set(rec), {'img', 'imgHalf', 'm', 'mean'})
            self.assertEqual(Image.open(ROOT / rec['img']).size, (1024, 1024), k)
            self.assertEqual(Image.open(ROOT / rec['imgHalf']).size, (512, 512), k)
            self.assertTrue(all(0 < v < 1 for v in rec['mean']), k)
        self.assertEqual(d['parkmacro']['m'], 240.0)
        self.assertEqual(d['canopy_summer']['m'], 70.0)
        # a forest from the air is dark and green, its winter grey-brown
        s, w = d['canopy_summer']['mean'], d['canopy_winter']['mean']
        self.assertGreater(s[1], s[0]); self.assertGreater(w[0], w[1])

    def test_the_land_mask(self):
        m = json.loads((ROOT / 'land_mask.json').read_text())
        self.assertEqual(m['box'], [-12000.0, -21700.0, 28500.0, 31400.0])   # pack_city.py CITY
        from PIL import Image
        import numpy as np
        im = Image.open(ROOT / m['img'])
        self.assertEqual(im.mode, 'RGB')                                     # no alpha: a browser may premultiply by it
        self.assertEqual(im.size, (m['w'], m['h']))
        self.assertEqual(Image.open(ROOT / m['imgHalf']).size, (m['w'] // 2, m['h'] // 2))
        a = np.asarray(im, np.float32) / 255
        px = lambda x, z: a[int((z - m['box'][1]) / m['px']), int((x - m['box'][0]) / m['px'])]
        self.assertGreater(px(-1300, -300)[0], 0.5)      # Center City is built up
        self.assertLess(px(-1300, -300)[1], 0.1)         # and no woods
        self.assertGreater(px(-5600, -11600)[1], 0.5)    # the Wissahickon gorge is woods
        self.assertGreater(px(-5450, 1500)[2], 0.9)      # the Schuylkill at Bartram's is a river's bank
        self.assertLess(px(-1300, -300)[2], 0.1)

    def test_no_woods_on_water_or_a_railway(self):
        # the review: about 10 km2 of water and the Amtrak corridor took woods (East Park Reservoir, the Wissahickon's
        # channel, Darby Creek, FDR Park's lakes). Every texel a water ring or an open track touches is exactly 0, and the
        # wood field plants nothing on a zero texel
        import sys
        import numpy as np
        from PIL import Image, ImageDraw
        sys.path.insert(0, str(ROOT))
        import bake_landmask as B
        m = json.loads((ROOT / 'land_mask.json').read_text())
        G = np.asarray(Image.open(ROOT / m['img']).convert('RGB'))[:, :, 1]
        x0, z0, px = m['box'][0], m['box'][1], m['px']
        rings = [r for name, unit in B.BLOBS for k, r in B.read_blob(name, unit)[2] if k == 1]
        rings += [list(zip(f[0::2], f[1::2])) for f in json.loads((ROOT / 'nw_water.json').read_text())['polys']]
        S, X0, X1, Z0, Z1 = 5.0, -12000, 1500, -21700, 9700
        c = Image.new('L', (int((X1 - X0) / S), int((Z1 - Z0) / S)), 0)
        d = ImageDraw.Draw(c)
        for r in rings:
            if len(r) >= 3:
                d.polygon([((x - X0) / S, (z - Z0) / S) for x, z in r], fill=255)
        jj, ii = np.nonzero(np.asarray(c) > 127)
        xs, zs = X0 + (ii + 0.5) * S, Z0 + (jj + 0.5) * S
        g = G[((zs - z0) / px).astype(int), ((xs - x0) / px).astype(int)]
        self.assertGreater(len(g), 500000)                     # 12 km2 and more of water west of the Delaware's bank
        self.assertEqual(int((g > 0).sum()), 0)
        for x, z in ((-4234, -4477), (-3000, 4500)):          # East Park Reservoir's ring, FDR Park's lakes
            self.assertEqual(int(G[int((z - z0) / px), int((x - x0) / px)]), 0)
        rail = json.loads((ROOT / 'rail_amtrak.json').read_text())
        bad = 0
        for l in rail['lines']:
            if l.get('t'):
                continue
            p = np.array(l['p'], float)[:, :2]
            for a, b in zip(p[:-1], p[1:]):
                n = max(1, int(np.hypot(*(b - a)) / 8.5))
                for t in np.arange(n) / n:
                    q = a + (b - a) * t
                    i, j = int((q[0] - x0) / px), int((q[1] - z0) / px)
                    if 0 <= i < G.shape[1] and 0 <= j < G.shape[0]:   # the corridor runs past the mask's box
                        bad += int(G[j, i] > 0)
        self.assertEqual(bad, 0)


if __name__ == '__main__':
    unittest.main()
