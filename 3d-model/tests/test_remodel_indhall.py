"""Round 210 (Mike: "Can we have independence hall remodeled with the chat GPT api?"): Independence Hall is built again in a
mesh of its own on A Man Full of Trouble's material (tvMat) and dressed from its generated atlas (fetch_indhall_art.py,
bake_indhall_art.py, indhall_art.json, art/indhall/).

- the manifest: the atlas and its phone half under their hashes, four swatches and eleven openings inside the atlas without
  overlapping, the three glazed sashes' grids (twelve over twelve on the main block, nine over nine in the wings), and the
  atlas's own panes dark and bars light exactly where the grid the page draws says;
- the page: the gate (the realistic look, not the recovery tier, ?indhall=0 the A/B), the old massing kept whole for
  ?real=0, the shared material's program key, uniforms sized to the hall, the 32-texel gutter, one 4-byte aTv stream,
  no depth written, a raycast target, the phone's art after Enter, the probe;
- the geometry, run for real under JavaScriptCore with the vendored Three.js on the complex's own footprint: inside the
  budget, the vane at the steeple's 168 ft 7 in, every triangle wound to its normal, nothing past the footprint but the
  cornice, the wings' eaves and the Chestnut Street steps, and no two faces that look the same way sharing a plane where
  they overlap (they would flicker).
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


SW = ('brick', 'shingle', 'paint', 'stone')
EL = ('sashG', 'sashU', 'sashW', 'door', 'tdoor', 'palladian', 'arch', 'clock', 'oculus', 'wdoor', 'cellar')


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not C.path('indhall_art.json').exists():
            raise unittest.SkipTest('input absent: indhall_art.json')
        cls.man = json.loads(C.path('indhall_art.json').read_text())

    def test_files_and_halves(self):
        for k in ('img', 'imgHalf'):
            p = self.man[k]
            m = re.fullmatch(r'art/indhall/(atlas|atlas-half)\.([0-9a-f]{10})\.webp', p)
            self.assertTrue(m, p)
            self.assertEqual(hashlib.sha256(C.path(p).read_bytes()).hexdigest()[:10], m.group(2))
        from PIL import Image
        self.assertEqual(Image.open(C.path(self.man['img'])).size, (self.man['w'], self.man['h']))
        self.assertEqual(Image.open(C.path(self.man['imgHalf'])).size, (self.man['w'] // 2, self.man['h'] // 2))

    def test_rects_and_gutters(self):
        W, H = self.man['w'], self.man['h']
        rects = []
        for k in SW:
            s = self.man['sw'][k]
            self.assertTrue(all(v > 0 for v in s['m']), k)
            self.assertEqual(len(s['mean']), 3)
            rects.append((k, s['rect']))
        for k in EL:
            e = self.man['el'][k]
            self.assertEqual(len(e['size']), 2)
            rects.append((k, e['rect']))
        for k, (u, v, w, h) in rects:
            self.assertTrue(0 <= u and 0 <= v and u + w <= 1.0001 and v + h <= 1.0001, k)
        # 30 texels clear between any two (the page reads up to 28 into a gutter: ihU.uTvGut)
        g = 30
        for i, (ka, a) in enumerate(rects):
            for kb, b in rects[i + 1:]:
                ox = min(a[0] + a[2], b[0] + b[2]) * W - max(a[0], b[0]) * W
                oy = min(a[1] + a[3], b[1] + b[3]) * H - max(a[1], b[1]) * H
                self.assertFalse(ox > -2 * g and oy > -2 * g, '%s within %d texels of %s' % (ka, 2 * g, kb))

    def test_grids_are_the_halls(self):
        el = self.man['el']
        self.assertEqual(el['sashG']['grid'], [[3, 4], [3, 4]])   # twelve over twelve, the main block's ground floor
        self.assertEqual(el['sashU']['grid'], [[3, 4], [3, 4]])   # and its upper floor
        self.assertEqual(el['sashW']['grid'], [[3, 3], [3, 3]])   # nine over nine in the wings
        for k in ('sashG', 'sashU', 'sashW'):
            a, b = el[k]['glass']
            for r in (a, b):
                self.assertTrue(0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1, k)
            self.assertLess(abs((a[3] - a[1]) - (b[3] - b[1])), 0.01, '%s: the two sashes are equal (equalise)' % k)
        for k in EL[3:]:
            self.assertNotIn('glass', el[k], k)   # only the first three are glazed in the shader

    def test_atlas_panes_match_the_grid(self):
        """The page draws the glass from the grid; the picture's panes must be where the grid's are."""
        from PIL import Image
        im = Image.open(C.path(self.man['img'])).convert('L')
        W, H = im.size
        for k in ('sashG', 'sashU', 'sashW'):
            e = self.man['el'][k]
            R = e['rect']
            bu, bv = e['bar']
            for (u0, v0, u1, v1), (c, r) in zip(e['glass'], e['grid']):
                pw, ph = (u1 - u0 - (c - 1) * bu) / c, (v1 - v0 - (r - 1) * bv) / r
                def px(qu, qv):
                    return im.getpixel((int((R[0] + qu * R[2]) * W), int((1 - (R[1] + qv * R[3])) * H)))
                for i in range(c):
                    for j in range(r):
                        self.assertLess(px(u0 + i * (pw + bu) + pw / 2, v0 + j * (ph + bv) + ph / 2), 70, '%s pane %d,%d' % (k, i, j))
                for i in range(c - 1):
                    self.assertGreater(px(u0 + (i + 1) * pw + i * bu + bu / 2, v0 + ph / 2), 110, '%s bar %d' % (k, i))


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = C.path('app.js').read_text(encoding='utf-8')
        cls.sec = cut(cls.src, '  // ---- Independence Hall remodelled (Round 210', '  // ---- the USS New Jersey remodelled (Round 195')

    def test_gate_and_the_old_model(self):
        s = self.src
        self.assertIn("const IH_ON = REAL && !TIER2 && typeof INDHALL_ART !== 'undefined'", self.sec)
        self.assertIn("!/[?&]indhall=0\\b/.test(location.search)", self.sec)
        blk = cut(s, "      const b = get('Independence Hall');", "    for (const nm of ['Congress Hall', 'Old City Hall'])")
        self.assertIn('if (obIH && IH_ON) indhallMake(obIH);', blk)
        self.assertIn('else if (obIH) {', blk)
        for line in ('const BW = 16.45, BD = 13.4;', 'liftB(m0, b);'):   # the old massing stands whole behind it
            self.assertIn(line, blk)
        b = C.path('build.py').read_text()
        self.assertIn('const("INDHALL_ART", text_of("indhall_art.json", "null"))', b)
        self.assertIn('"indhall_art.json"', b[b.index('for name in ("tree_art.json"'):b.index('    if (ROOT / name).exists():')])

    def test_the_material_and_the_mesh(self):
        s, sec = self.src, self.sec
        self.assertNotIn('gl_FragDepth', sec)
        self.assertIn("mat = tvMat(gl2, U, IH_SW.length, IH_EL.length, 'indhall');", sec)
        self.assertIn("mat.customProgramCacheKey = () => key + (gl2 ? '' : '|gl1');", s)   # its own program, never the tavern's
        self.assertIn("uTvGut: { value: new THREE.Vector2(24, 28) }", sec)
        self.assertIn("uTvGut: { value: new THREE.Vector2(24, 6) }", s)   # the tavern's own gutter unchanged
        self.assertIn("'float tvGm = (tvIsEl ? uTvGut.y : uTvGut.x) / uTvAtW,", s)
        self.assertIn("g.setAttribute('aTv', new THREE.BufferAttribute(new Uint8Array(tvs), 4, true));", sec)
        self.assertNotRegex(sec, r"BufferAttribute\(new (Uint8|Int8)Array\([^)]*\), [13]\b")
        self.assertIn('freeShadingOnUpload(geo);', sec)
        self.assertIn('groupCity.add(m); rayTargets.push(m);', sec)
        self.assertIn('artImage(artSrc(A.img, A.imgHalf))', sec)
        self.assertIn("else { const wait = () => (PERF.enterT ? go() : setTimeout(wait, 400)); wait(); }", sec)
        self.assertIn('indhall: () => ({ on: IH_ON,', s)
        bk = cut(C.path('bake_indhall_art.py').read_text(), 'GUTTER = ', '\n')
        self.assertEqual('GUTTER = 32', bk.split('#')[0].strip())
        # the uniform arrays are sized to the hall's swatches and elements
        u = cut(sec, '  const ihU = {', '\n  };')
        for k in ('uTvSw', 'uTvSwM', 'uTvSwC'):
            self.assertIn('%s: { value: IH_SW.map(' % k, u)
        for k in ('uTvEl', 'uTvElC'):
            self.assertIn('%s: { value: IH_EL.map(' % k, u)
        self.assertEqual(list(EL), json.loads(cut(sec, '  const IH_EL = ', ';').split('=', 1)[1].replace("'", '"')))
        self.assertEqual(list(SW), json.loads(cut(sec, '  const IH_SW = ', ';').split('=', 1)[1].replace("'", '"')))


JXA = r'''ObjC.import("Foundation");
function readFile(p) { return $.NSString.stringWithContentsOfFileEncodingError($.NSString.alloc.initWithUTF8String(p), 4, null).js; }
(0, eval)(readFile(%(three)s));
var INDHALL_ART = JSON.parse(readFile(%(man)s));
var SCENE = JSON.parse(readFile(%(scene)s));
var out = (function () {
  %(helpers)s
  function siteY() { return 0; }
  var IH = { parts: {} }, ihU = { uTvY0: { value: 0 }, uTvE: { value: new THREE.Vector2() } };
  %(consts)s
  %(build)s
  var b = null;
  for (var i = 0; i < SCENE.buildings.length; i++) if (SCENE.buildings[i].name === 'Independence Hall') b = SCENE.buildings[i];
  var ob = orientedBox(b.poly), a = obbAxis(ob);
  var g = indhallBuild(ob), P = g.attributes.position.array, N = g.attributes.normal.array, T = g.attributes.aTv, U = g.attributes.uv.array;
  var n = P.length / 9, bad = 0, degen = 0, nrm = 0, nan = 0, farU = 0, farV = 0, low = 0, top = -1e9;
  for (var k = 0; k < U.length; k++) if (!isFinite(U[k])) nan++;
  var buckets = {};
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
      var dx = p[0] - ob.cx, dz = p[2] - ob.cz, u = dx * a.ax + dz * a.az, v = (dx * a.px + dz * a.pz) * (a.pz > 0 ? 1 : -1);
      if (Math.abs(u) > a.hl + 0.6) farU++;
      if (v < -a.hs - 1.25 || v > a.hs + 0.1) farV++;
      if (p[1] < -1.6) low++; top = Math.max(top, p[1]);
    });
    var tn = [cr[0] / L, cr[1] / L, cr[2] / L], d = A[0] * tn[0] + A[1] * tn[1] + A[2] * tn[2];
    var key = Math.round(tn[0] * 200) + ',' + Math.round(tn[1] * 200) + ',' + Math.round(tn[2] * 200) + '|' + Math.round(d * 100);
    (buckets[key] = buckets[key] || []).push({ p: [A, B, Cc], n: tn });
  }
  // two faces turned the same way in one plane, overlapping (not merely touching): the separating axes of two triangles
  // in that plane, within each plane's bucket
  function proj(p, ax) { return p[0] * ax[0] + p[1] * ax[1] + p[2] * ax[2]; }
  function crossv(x, y) { return [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]]; }
  var cop = 0, copEx = [];
  Object.keys(buckets).forEach(function (bk) {
    var Ls = buckets[bk];
    for (var i2 = 0; i2 < Ls.length; i2++) for (var j2 = i2 + 1; j2 < Ls.length; j2++) {
      var s1 = Ls[i2], s2 = Ls[j2];
      if (s1.n[0] * s2.n[0] + s1.n[1] * s2.n[1] + s1.n[2] * s2.n[2] < 0.9999) continue;
      if (Math.abs(proj(s1.p[0], s1.n) - proj(s2.p[0], s1.n)) > 1e-3) continue;
      var sep = false;
      [s1, s2].forEach(function (s) { for (var e = 0; e < 3 && !sep; e++) {
        var p0 = s.p[e], p1 = s.p[(e + 1) %% 3], ax = crossv([p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]], s1.n);
        var mn1 = Infinity, mx1 = -Infinity, mn2 = Infinity, mx2 = -Infinity;
        s1.p.forEach(function (q) { var dd = proj(q, ax); mn1 = Math.min(mn1, dd); mx1 = Math.max(mx1, dd); });
        s2.p.forEach(function (q) { var dd = proj(q, ax); mn2 = Math.min(mn2, dd); mx2 = Math.max(mx2, dd); });
        var al = Math.sqrt(proj(ax, ax)) || 1;
        if (Math.min(mx1, mx2) - Math.max(mn1, mn2) < 1e-4 * al) sep = true;
      } });
      if (!sep) { cop++; if (copEx.length < 4) copEx.push([s1.p[0], s2.p[0]]); }
    }
  });
  return { tris: n, bad: bad, degen: degen, nrm: nrm, nan: nan, farU: farU, farV: farV, low: low, top: top, cop: cop, copEx: copEx,
    parts: Object.keys(IH.parts), tvItems: T.itemSize, tvBytes: T.array.BYTES_PER_ELEMENT, tvNorm: T.normalized, tvLen: T.array.length, verts: g.attributes.position.count,
    modes: Array.from(new Set(Array.from(T.array).filter(function (_, q) { return q %% 4 === 0; }))).sort() };
})();
JSON.stringify(out);'''


class Geometry(unittest.TestCase):
    def test_built_for_real(self):
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        C.require(self, 'three.min.js', 'scene.json', 'indhall_art.json')
        src = C.path('app.js').read_text(encoding='utf-8')
        helpers = '\n'.join(cut(src, '  function %s(' % f, '\n  }\n') + '\n  }' for f in ('polyCentroid', 'orientedBox', 'obbAxis'))
        consts = cut(src, '  const IH_SW = ', '\n') + '\n' + cut(src, '  const IH_EL = ', '\n')
        build = cut(src, '  function tvKit(', '  // the hall built and its atlas asked for')
        script = JXA % {'three': json.dumps(str(C.path('three.min.js'))), 'man': json.dumps(str(C.path('indhall_art.json'))),
                        'scene': json.dumps(str(C.path('scene.json'))), 'helpers': helpers, 'consts': consts, 'build': build}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=300)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:800])
        out = json.loads(r.stdout.strip())
        self.assertGreater(out['tris'], 5000)
        self.assertLess(out['tris'], 25000, 'the budget: under 25,000 triangles')
        self.assertEqual(0, out['bad'], 'a triangle wound against its normal (back-face culled from outside)')
        self.assertEqual(0, out['degen'])
        self.assertEqual(0, out['nrm'])
        self.assertEqual(0, out['nan'])
        self.assertEqual(0, out['farU'], 'a vertex past the complex\'s ends by more than the wings\' eaves')
        self.assertEqual(0, out['farV'], 'a vertex past the complex\'s north side by more than the steps, or past its south side')
        self.assertEqual(0, out['low'])
        self.assertAlmostEqual(51.39, out['top'], delta=0.1, msg='the vane: 168 ft 7 1/4 in (NPS)')
        self.assertEqual(0, out['cop'], 'two faces turned the same way share a plane where they overlap: %s' % out['copEx'])
        self.assertEqual(['mainWalls', 'quoins', 'cornice', 'roof', 'chimneys', 'tower', 'steeple', 'arcades', 'wings'], out['parts'])
        self.assertEqual((4, 1, True, out['verts'] * 4), (out['tvItems'], out['tvBytes'], out['tvNorm'], out['tvLen']))
        self.assertEqual([0, 1, 2], out['modes'])


if __name__ == '__main__':
    unittest.main()
