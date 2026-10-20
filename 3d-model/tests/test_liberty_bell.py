"""Round 211 (Mike, with a screenshot of the Liberty Bell Center's south end: "Can we have the liberty bell show through the
window like in real life"): the Liberty Bell Center's footprint is split before the core loop (lbellSplit), its north part
left to the generic extrusion and its south end built as the bell's chamber (lbellBuild): a shell on the same facade, a glass
wall in a dark frame, a lit room and the bell on its yoke.

- the split, run for real under JavaScriptCore on scene.json: the cut crosses the footprint exactly twice, the chamber is
  the south end (a five-sided ring 7 to 12 m deep), the two parts cover the footprint's area;
- the page: the gate (the realistic look, ?bell=0 the A/B), the split before the core loop, the fallback that closes the
  extrusion over the chamber if the build fails, the shell through the step's own aw with the generic's facade style, the
  glass not writing depth, the canvas freed after upload on a phone, the probe.
Skips the runtime part when osascript is unavailable."""
import json
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


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = C.path('app.js').read_text(encoding='utf-8')
        cls.sec = cut(cls.src, '  // ---- the Liberty Bell in its chamber (Round 211', '  // ---- Independence Hall remodelled (Round 210')

    def test_gate_split_and_fallback(self):
        s, sec = self.src, self.sec
        self.assertIn("const LBELL_ON = REAL && !/[?&]bell=0\\b/.test(location.search);", sec)
        loop = cut(s, '    lbellSplit(D.buildings);', '    for (let i = 0; i < D.buildings.length; i++) {')
        self.assertIn('const parts = [];', loop)   # before the core loop reads a footprint
        blk = cut(s, '      if (LBELL.ring) {', '      if (obIH && IH_ON) indhallMake(obIH);')
        self.assertIn('lbellBuild(aw, ad, mark, liftAt);', blk)
        self.assertIn('aw(buildingGeom(LBELL.ring, null, LBELL.b.h || 10.7, -1.5)', blk)   # a failed build closes the hole
        self.assertIn('const st = fabricStyle(b.fa, h, tCode,', sec)
        self.assertIn("transparent: true, opacity: 0.16, depthWrite: false", sec)
        self.assertIn('return isTouch ? freeTexOnUpload(t) : t;', sec)
        self.assertNotIn('gl_FragDepth', sec)
        self.assertIn('lbell: () => ({ on: LBELL.on, built: LBELL.built,', s)
        self.assertIn('registerPoly(R);', sec)   # no tree grows in the chamber


JXA = r'''ObjC.import("Foundation");
function readFile(p) { return $.NSString.stringWithContentsOfFileEncodingError($.NSString.alloc.initWithUTF8String(p), 4, null).js; }
(0, eval)(readFile(%(three)s));
var SCENE = JSON.parse(readFile(%(scene)s));
var out = (function () {
  %(helpers)s
  var REAL = true, location = { search: '' };
  %(split)s
  var b = SCENE.buildings.filter(function (x) { return x.name === 'Liberty Bell Center'; })[0], full = Math.abs(signedArea(b.poly));
  lbellSplit(SCENE.buildings);
  var sMin = Infinity, sMax = -Infinity;
  LBELL.ring.forEach(function (p) { var v = p[0] * LBELL.ax + p[1] * LBELL.az; sMin = Math.min(sMin, v); sMax = Math.max(sMax, v); });
  return { err: LBELL.err, ring: LBELL.ring.length, body: b.poly.length, az: LBELL.az, depth: sMax - sMin,
    area: Math.abs(signedArea(LBELL.ring)) + Math.abs(signedArea(b.poly)), full: full };
})();
JSON.stringify(out);'''


class Split(unittest.TestCase):
    def test_split_for_real(self):
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        C.require(self, 'three.min.js', 'scene.json')
        src = C.path('app.js').read_text(encoding='utf-8')
        helpers = '\n'.join(cut(src, '  function %s(' % f, '\n  }\n') + '\n  }' for f in ('polyCentroid', 'orientedBox', 'obbAxis', 'signedArea'))
        split = cut(src, '  const LBELL_ON = ', '  // the inscription, the founders')
        script = JXA % {'three': json.dumps(str(C.path('three.min.js'))), 'scene': json.dumps(str(C.path('scene.json'))), 'helpers': helpers, 'split': split}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=120)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:800])
        out = json.loads(r.stdout.strip())
        self.assertIsNone(out['err'])
        self.assertEqual(5, out['ring'])
        self.assertGreater(out['body'], 20)
        self.assertGreater(out['az'], 0.9)   # the axis points south, so the chamber is the Chestnut Street end
        self.assertTrue(7 < out['depth'] < 12.5, out['depth'])
        self.assertAlmostEqual(out['full'], out['area'], delta=0.5)


if __name__ == '__main__':
    unittest.main()
