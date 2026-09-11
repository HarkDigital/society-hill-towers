"""The packed rings' vertex buffer (VBuf in app.js) run for real under JavaScriptCore with the
vendored Three.js: the facade attributes (aStyle, aBase, aFloorH and the Round 54 glass tint
aTint) must survive buffer growth and reach the uploaded geometry, and the outer glass upload
must ask for them (geometry(true)): the Sep 8 rework found the curtain-wall upload calling
geometry(false), which silently dropped every researched curtain-wall variant. Skips when
osascript is unavailable (non-macOS hosts)."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_vbuf
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

JXA = r'''ObjC.import("Foundation");
function readFile(p) { return $.NSString.stringWithContentsOfFileEncodingError($.NSString.alloc.initWithUTF8String(p), 4, null).js; }
(0, eval)(readFile(%(three)s));
var freed = 0;
function freeOnUpload(g) { freed++; }
var VBuf = (function () { %(snippet)s
  return VBuf; })();
var b = new VBuf(8);
for (var i = 0; i < 40; i++) b.push(i, i * 2, i * 3, 0, 1, 0, 0.5, 0.4, 0.3, 21, 12.5, 3.1, 0.62);
var g = b.geometry(true);
var out = { n: g.attributes.position.count, freed: freed, idxOk: !!g.index, bs: g.boundingSphere ? g.boundingSphere.radius > 0 : false,
  style: Array.from(g.attributes.aStyle.array).every(function (v) { return v === 21; }),
  base: Array.from(g.attributes.aBase.array).every(function (v) { return Math.abs(v - 12.5) < 1e-6; }),
  floor: Array.from(g.attributes.aFloorH.array).every(function (v) { return v === 31; }),
  tint: Array.from(g.attributes.aTint.array).every(function (v) { return v === 158; }),
  tintNorm: g.attributes.aTint.normalized === true,
  tintLen: g.attributes.aTint.array.length,
  released: b.pos === null && b.tin === null };
var b2 = new VBuf(8);
for (var j = 0; j < 3; j++) b2.push(j, 0, 0, 0, 1, 0, 1, 1, 1, 3, 0, 0);
var g2 = b2.geometry(false);
out.plainHasStyle = !!g2.attributes.aStyle; out.plainHasTint = !!g2.attributes.aTint; out.plainN = g2.attributes.position.count;
JSON.stringify(out);'''


def vbuf_snippet(src):
    """The IdxBuf and VBuf classes, cut from app.js by their banners."""
    a = src.index('\n  class IdxBuf {')
    b = src.index('\n  const groupCity = new THREE.Group();')
    return src[a:b]


class VBufRuntime(unittest.TestCase):
    def setUp(self):
        C.require(self, 'app.js')
        C.require(self, 'three.min.js')
        self.src = C.path('app.js').read_text(encoding='utf-8')

    def test_glass_upload_keeps_facade_attributes(self):
        """The curtain-wall chunks upload with geometry(true): aStyle, aBase and aTint reach the outer glass shader."""
        m = re.search(r"for \(const ch of glassChunks\.values\(\)\) \{\s*const g = ch\.geometry\((\w+)\);", self.src)
        self.assertIsNotNone(m, 'the glass chunk upload loop is gone from app.js')
        self.assertEqual('true', m.group(1), 'the glass chunks must upload with geometry(true), or the curtain-wall variants are lost')
        for attr in ('attribute float aStyle;', 'attribute float aBase;'):
            self.assertIn(attr, self.src[self.src.index('outerGlassMat = new THREE.MeshStandardMaterial'):][:6000], 'the outer glass shader no longer declares ' + attr)

    def test_vbuf_attributes_survive_growth(self):
        """40 pushes through an 8-slot buffer (three doublings) keep style, base, floor height and tint on every vertex."""
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        script = JXA % {'three': json.dumps(str(C.path('three.min.js'))), 'snippet': vbuf_snippet(self.src)}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=180)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:600])
        out = json.loads(r.stdout.strip())
        self.assertEqual(40, out['n'])
        self.assertTrue(out['style'], 'aStyle lost through growth')
        self.assertTrue(out['base'], 'aBase lost through growth')
        self.assertTrue(out['floor'], 'aFloorH lost through growth')
        self.assertTrue(out['tint'], 'aTint lost through growth (0.62 -> byte 158)')
        self.assertTrue(out['tintNorm'], 'aTint must be a normalized byte attribute')
        self.assertEqual(40, out['tintLen'])
        self.assertTrue(out['idxOk'] and out['bs'])
        self.assertEqual(1, out['freed'], 'geometry() must hand the buffers to freeOnUpload once')
        self.assertTrue(out['released'], 'geometry() must release the staging arrays, the tint included')
        self.assertEqual(3, out['plainN'])
        self.assertFalse(out['plainHasStyle'] or out['plainHasTint'], 'geometry(false) must stay attribute-free (streets, water, trim)')


if __name__ == '__main__':
    unittest.main()
