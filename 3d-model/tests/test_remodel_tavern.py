"""Round 199 (Mike, with a screenshot from across Spruce Street: "Man Full of Trouble needs to look like the other newer
textures"): A Man Full of Trouble, 127 Spruce, is built again in a mesh of its own on its own material and dressed from
its generated atlas (fetch_tavern_art.py, bake_tavern_art.py, tavern_art.json, art/tavern/).

- the manifest: the atlas and its phone half under their hashes, four swatches and six openings inside the atlas without
  overlapping, the glazed ones' grids the house's (a four-light transom, nine over nine, six over six), and the atlas's
  own panes dark and bars light exactly where the grid the page draws says (the bake repaints them on it);
- the page: the gate (the realistic look, not the recovery tier, ?tavern=0 the A/B), the Round 127 model kept whole for
  ?real=0, one 4-byte aTv stream, its own program key, no depth written, a raycast target, the phone's art after Enter;
- the geometry, run for real under JavaScriptCore with the vendored Three.js on the house's own footprint: inside the
  budget, every triangle wound to its normal, nothing past the footprint but the pent, the cornice, the roof and the
  stoops' things, and no two faces that look the same way sharing a plane where they overlap (they would flicker).
Skips the runtime part when osascript is unavailable (non-macOS hosts)."""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest

try:
    from . import _common as C
except ImportError:
    import _common as C


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i + len(a))]


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not C.path('tavern_art.json').exists():
            raise unittest.SkipTest('input absent: tavern_art.json')
        cls.man = json.loads(C.path('tavern_art.json').read_text())

    def test_files_and_halves(self):
        for k in ('img', 'imgHalf'):
            p = self.man[k]
            m = re.fullmatch(r'art/tavern/(atlas|atlas-half)\.([0-9a-f]{10})\.webp', p)
            self.assertTrue(m, p)
            self.assertEqual(hashlib.sha256(C.path(p).read_bytes()).hexdigest()[:10], m.group(2))
        from PIL import Image
        self.assertEqual(Image.open(C.path(self.man['img'])).size, (self.man['w'], self.man['h']))
        self.assertEqual(Image.open(C.path(self.man['imgHalf'])).size, (self.man['w'] // 2, self.man['h'] // 2))

    def test_rects(self):
        rects = []
        for k in ('brick', 'shingle', 'paint', 'marble'):
            s = self.man['sw'][k]
            self.assertTrue(all(v > 0 for v in s['m']), k)
            self.assertEqual(len(s['mean']), 3)
            rects.append((k, s['rect']))
        for k in ('door', 'sash', 'dsash', 'winshut', 'shutL', 'shutR'):
            rects.append((k, self.man['el'][k]['rect']))
        for k, (u, v, w, h) in rects:
            self.assertTrue(0 <= u and 0 <= v and u + w <= 1.0001 and v + h <= 1.0001, k)
        for i, (ka, a) in enumerate(rects):
            for kb, b in rects[i + 1:]:
                ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
                oy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
                self.assertFalse(ox > 1e-6 and oy > 1e-6, '%s overlaps %s' % (ka, kb))

    def test_grids_are_the_houses(self):
        el = self.man['el']
        self.assertEqual(el['door']['grid'], [[4, 1]])            # the four-light transom (refs)
        self.assertEqual(el['sash']['grid'], [[3, 3], [3, 3]])    # nine over nine upstairs (refs; the model drew nine over six)
        self.assertEqual(el['dsash']['grid'], [[3, 2], [3, 2]])   # six over six in the dormers
        for k in ('door', 'sash', 'dsash'):
            for r in el[k]['glass']:
                self.assertTrue(0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1, k)
        a, b = el['sash']['glass']
        self.assertLess(abs((a[3] - a[1]) - (b[3] - b[1])), 0.01, 'the two sashes are equal (equalise)')

    def test_atlas_panes_match_the_grid(self):
        """The page draws the glass from the grid; the picture's bars must be where the grid's are."""
        from PIL import Image
        im = Image.open(C.path(self.man['img'])).convert('L')
        W, H = im.size
        for k in ('door', 'sash', 'dsash'):
            e = self.man['el'][k]
            R = e['rect']
            bu, bv = e['bar']
            for (u0, v0, u1, v1), (c, r) in zip(e['glass'], e['grid']):
                pw, ph = (u1 - u0 - (c - 1) * bu) / c, (v1 - v0 - (r - 1) * bv) / r
                def px(qu, qv):
                    x = (R[0] + qu * R[2]) * W
                    y = (1 - (R[1] + qv * R[3])) * H
                    return im.getpixel((int(x), int(y)))
                for i in range(c):
                    for j in range(r):
                        self.assertLess(px(u0 + i * (pw + bu) + pw / 2, v0 + j * (ph + bv) + ph / 2), 70, '%s pane %d,%d' % (k, i, j))
                for i in range(c - 1):   # a bar between two columns, in the middle of a pane's height
                    self.assertGreater(px(u0 + (i + 1) * pw + i * bu + bu / 2, v0 + ph / 2), 110, '%s bar %d' % (k, i))


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = C.path('app.js').read_text(encoding='utf-8')
        cls.sec = cut(cls.src, '  // ---- A Man Full of Trouble textured (Round 199', '  // ------------------------------------------------ museum ships')

    def test_gate_and_the_old_model(self):
        s = self.src
        self.assertIn("const TAVERN_ON = REAL && !TIER2 && typeof TAVERN_ART !== 'undefined'", s)
        self.assertIn("!/[?&]tavern=0\\b/.test(location.search)", self.sec)
        blk = cut(s, "      const b = get('Man Full of Troubles Tavern');", '    // The Irish Famine Memorial')
        self.assertIn('if (b && TAVERN_ON) tavernMake(b);', blk)
        self.assertIn('else if (b) {', blk)
        # the Round 127 model stands whole behind it for ?real=0 and the recovery tier
        for line in ("const BRICK = '#8f4430', BRICK_D = '#2a120c', CREAM = '#e9e2c8', SHUT = '#ddd5b4', SHINGLE = '#120c08', GLASS = '#232830', STONE = '#6e6a62';",
                     'aw(buildingGeom(b.poly, b.holes, EAVE, -1.5), BRICK, 3);', 'for (const x of [-4.0, -1.97, 1.15, 4.04]) win(x * K, 3.95, 0.9, 1.75);'):
            self.assertIn(line, blk)
        b = C.path('build.py').read_text()
        self.assertIn('const("TAVERN_ART", text_of("tavern_art.json", "null"))', b)
        self.assertIn('"tavern_art.json"):', b)

    def test_the_material_and_the_mesh(self):
        s = self.sec
        self.assertNotIn('gl_FragDepth', s)   # reversed-Z float depth (Round 192): no program of ours writes depth
        self.assertIn("g.setAttribute('aTv', new THREE.BufferAttribute(new Uint8Array(tvs), 4, true));", s)
        self.assertNotRegex(s, r"BufferAttribute\(new (Uint8|Int8)Array\([^)]*\), [13]\b")   # never a 1- or 3-byte stream
        self.assertIn("mat.customProgramCacheKey = () => 'tavern' + (gl2 ? '' : '|gl1');", s)
        self.assertIn('freeShadingOnUpload(geo);', s)
        self.assertIn('groupCity.add(m); rayTargets.push(m);', s)
        self.assertIn('artImage(artSrc(A.img, A.imgHalf))', s)
        self.assertIn("else { const wait = () => (PERF.enterT ? go() : setTimeout(wait, 400)); wait(); }", s)   # a phone decodes after Enter
        for p in ('glassOpticsPatch(sh,', 'occBind(sh);', "lampLightPatch(sh, 'tvWP', 'wall');", 'wxSurfacePatch(sh);', 'roomLight(tvRuv', 'roomDay(tvRuv'):
            self.assertIn(p, s)


JXA = r'''ObjC.import("Foundation");
function readFile(p) { return $.NSString.stringWithContentsOfFileEncodingError($.NSString.alloc.initWithUTF8String(p), 4, null).js; }
(0, eval)(readFile(%(three)s));
var TAVERN_ART = JSON.parse(readFile(%(man)s));
var SCENE = JSON.parse(readFile(%(scene)s));
var out = (function () {
  %(helpers)s
  function siteY() { return 0; }
  var tavernU = { uTvY0: { value: 0 }, uTvE: { value: new THREE.Vector2() }, uTvEv: { value: new THREE.Vector2() } };
  %(consts)s
  %(build)s
  var b = null;
  for (var i = 0; i < SCENE.buildings.length; i++) if (SCENE.buildings[i].name === 'Man Full of Troubles Tavern') b = SCENE.buildings[i];
  var g = tavernBuild(b), P = g.attributes.position.array, N = g.attributes.normal.array, T = g.attributes.aTv, U = g.attributes.uv.array;
  var n = P.length / 9, bad = 0, degen = 0, nrm = 0, nan = 0, far = 0, low = 0, high = 0;
  var ob = orientedBox(b.poly), a = obbAxis(ob);
  for (var k = 0; k < U.length; k++) if (!isFinite(U[k])) nan++;
  var tris = [];
  for (var t = 0; t < n; t++) {
    var o = t * 9, A = [P[o], P[o + 1], P[o + 2]], B = [P[o + 3], P[o + 4], P[o + 5]], Cc = [P[o + 6], P[o + 7], P[o + 8]];
    var e1 = [B[0] - A[0], B[1] - A[1], B[2] - A[2]], e2 = [Cc[0] - A[0], Cc[1] - A[1], Cc[2] - A[2]];
    var cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    var L = Math.sqrt(cr[0] * cr[0] + cr[1] * cr[1] + cr[2] * cr[2]);
    var nn = [N[o], N[o + 1], N[o + 2]], nl = Math.sqrt(nn[0] * nn[0] + nn[1] * nn[1] + nn[2] * nn[2]);
    if (Math.abs(nl - 1) > 1e-4) nrm++;
    if (L < 1e-7) { degen++; continue; }
    if ((cr[0] * nn[0] + cr[1] * nn[1] + cr[2] * nn[2]) / L < 0.999) bad++;
    [A, B, Cc].forEach(function (p) {
      var dx = p[0] - ob.cx, dz = p[2] - ob.cz, u = dx * a.ax + dz * a.az, v = dx * a.px + dz * a.pz;
      if (Math.abs(u) > a.hl + 0.5 || Math.abs(v) > a.hs + 1.0) far++;
      if (p[1] < -1.6) low++; if (p[1] > 12.5) high++;
    });
    tris.push({ p: [A, B, Cc], n: [cr[0] / L, cr[1] / L, cr[2] / L] });
  }
  // two faces turned the same way in one plane, overlapping (not merely touching): the separating axes of two triangles
  // in that plane
  function proj(p, ax) { return p[0] * ax[0] + p[1] * ax[1] + p[2] * ax[2]; }
  function crossv(x, y) { return [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]]; }
  var cop = 0, copEx = [];
  for (var i2 = 0; i2 < tris.length; i2++) for (var j2 = i2 + 1; j2 < tris.length; j2++) {
    var s1 = tris[i2], s2 = tris[j2];
    if (s1.n[0] * s2.n[0] + s1.n[1] * s2.n[1] + s1.n[2] * s2.n[2] < 0.9999) continue;
    if (Math.abs(proj(s1.p[0], s1.n) - proj(s2.p[0], s1.n)) > 1e-3) continue;
    var sep = false;
    [s1, s2].forEach(function (s) { for (var e = 0; e < 3 && !sep; e++) {
      var p0 = s.p[e], p1 = s.p[(e + 1) %% 3], ax = crossv([p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]], s1.n);
      var mn1 = Infinity, mx1 = -Infinity, mn2 = Infinity, mx2 = -Infinity;
      s1.p.forEach(function (q) { var d = proj(q, ax); mn1 = Math.min(mn1, d); mx1 = Math.max(mx1, d); });
      s2.p.forEach(function (q) { var d = proj(q, ax); mn2 = Math.min(mn2, d); mx2 = Math.max(mx2, d); });
      var al = Math.sqrt(proj(ax, ax)) || 1;
      if (Math.min(mx1, mx2) - Math.max(mn1, mn2) < 1e-4 * al) sep = true;
    } });
    if (!sep) { cop++; if (copEx.length < 4) copEx.push([s1.p[0], s2.p[0]]); }
  }
  return { tris: n, bad: bad, degen: degen, nrm: nrm, nan: nan, far: far, low: low, high: high, cop: cop, copEx: copEx,
    tvItems: T.itemSize, tvBytes: T.array.BYTES_PER_ELEMENT, tvNorm: T.normalized, tvLen: T.array.length, verts: g.attributes.position.count,
    modes: Array.from(new Set(Array.from(T.array).filter(function (_, q) { return q %% 4 === 0; }))).sort() };
})();
JSON.stringify(out);'''


class Geometry(unittest.TestCase):
    def test_built_for_real(self):
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        C.require(self, 'three.min.js', 'scene.json', 'tavern_art.json')
        src = C.path('app.js').read_text(encoding='utf-8')
        helpers = '\n'.join(cut(src, '  function %s(' % f, '\n  }\n') + '\n  }' for f in ('polyCentroid', 'orientedBox', 'obbAxis'))
        consts = cut(src, '  const TV_SW = ', '\n')
        build = cut(src, '  function tavernBuild(b) {', '  // the house built and its atlas asked for')
        script = JXA % {'three': json.dumps(str(C.path('three.min.js'))), 'man': json.dumps(str(C.path('tavern_art.json'))),
                        'scene': json.dumps(str(C.path('scene.json'))), 'helpers': helpers, 'consts': consts, 'build': build}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=300)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:800])
        out = json.loads(r.stdout.strip())
        self.assertGreater(out['tris'], 500)
        self.assertLess(out['tris'], 15000, 'the budget: under about 15,000 triangles')
        self.assertEqual(0, out['bad'], 'a triangle wound against its normal (back-face culled from outside)')
        self.assertEqual(0, out['degen'])
        self.assertEqual(0, out['nrm'])
        self.assertEqual(0, out['nan'])
        self.assertEqual(0, out['far'], 'a vertex past the footprint by more than the eaves, the pent and the hatches reach')
        self.assertEqual(0, out['low'] + out['high'])
        self.assertEqual(0, out['cop'], 'two faces turned the same way share a plane where they overlap: %s' % out['copEx'])
        self.assertEqual((4, 1, True, out['verts'] * 4), (out['tvItems'], out['tvBytes'], out['tvNorm'], out['tvLen']))
        self.assertEqual([0, 1, 2], out['modes'])


if __name__ == '__main__':
    unittest.main()
