"""The packed rings' vertex buffer (VBuf in app.js) run for real under JavaScriptCore with the
vendored Three.js: the facade attributes (style, floor height and the Round 54 glass tint in aSFT
since Round 158, and aBase) must survive buffer growth and reach the uploaded geometry, and the outer
glass upload must ask for them (geometry(true)): the Sep 8 rework found the curtain-wall upload calling
geometry(false), which silently dropped every researched curtain-wall variant. Round 158: every stream
sits on a 4-byte stride and offset (WebKit's ANGLE Metal backend keeps a padded copy of anything else),
and the shader's byte decode returns exactly what the old Int8 and Uint8 arrays held. Skips when
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
var VB = (function () { %(snippet)s
  return { VBuf: VBuf, rgbStride4: rgbStride4 }; })();
var VBuf = VB.VBuf, rgbStride4 = VB.rgbStride4;
var b = new VBuf(8);
for (var i = 0; i < 40; i++) b.push(i, i * 2, i * 3, 0, 1, 0, 0.5, 0.4, 0.3, 21, 12.5, 3.1, 0.62);
var g = b.geometry(true);
var sft = g.attributes.aSFT;
function col(k) { var a = []; for (var i = 0; i < sft.count; i++) a.push(sft.array[i * 4 + k]); return a; }
function i8(u) { return u > 127 ? u - 256 : u; }
var nrm = g.attributes.normal, clr = g.attributes.color;
var out = { n: g.attributes.position.count, freed: freed, idxOk: !!g.index, bs: g.boundingSphere ? g.boundingSphere.radius > 0 : false,
  style: col(0).every(function (v) { return i8(v) === 21; }),
  base: Array.from(g.attributes.aBase.array).every(function (v) { return Math.abs(v - 12.5) < 1e-6; }),
  floor: col(1).every(function (v) { return i8(v) === 31; }),
  tint: col(2).every(function (v) { return v === 158; }),
  flag: col(3).every(function (v) { return v === 255; }),
  sftNorm: sft.normalized === true, sftItems: sft.itemSize, sftBytes: sft.array.BYTES_PER_ELEMENT,
  nrmInter: !!nrm.isInterleavedBufferAttribute, nrmStride: nrm.data ? nrm.data.stride * nrm.data.array.BYTES_PER_ELEMENT : 0, nrmItems: nrm.itemSize, nrmNorm: nrm.normalized,
  nrmY: nrm.getY(3), clrStride: clr.data ? clr.data.stride * clr.data.array.BYTES_PER_ELEMENT : 0, clrItems: clr.itemSize, clrR: clr.data ? clr.data.array[4] : -1,
  aligned: Object.keys(g.attributes).every(function (k) { var a = g.attributes[k]; var bpe = (a.isInterleavedBufferAttribute ? a.data.array : a.array).BYTES_PER_ELEMENT; var stride = a.isInterleavedBufferAttribute ? a.data.stride * bpe : a.itemSize * bpe; var off = a.isInterleavedBufferAttribute ? a.offset * bpe : 0; return stride %% 4 === 0 && off %% 4 === 0; }),
  released: b.pos === null && b.sft === null };
// the wrap the old Int8 arrays did: a style of 130 and a 13.0 m floor (130) read back as -126, as they always did
var bw = new VBuf(4); bw.push(0, 0, 0, 0, 1, 0, 1, 1, 1, 130, 0, 13.0, 0); bw.push(0, 0, 0, 0, 1, 0, 1, 1, 1, -3, 0, 0, 0);
var gw = bw.geometry(true), aw = gw.attributes.aSFT.array;
out.wrap = [i8(aw[0]), i8(aw[1]), i8(aw[4])];
var b2 = new VBuf(8);
for (var j = 0; j < 3; j++) b2.push(j, 0, 0, 0, 1, 0, 1, 1, 1, 3, 0, 0);
var g2 = b2.geometry(false);
out.plainHasSft = !!g2.attributes.aSFT; out.plainN = g2.attributes.position.count;
// the shader's decode, in float32: floor(v * 255 + 0.5) of the normalized byte, read signed, for every byte
var f = Math.fround, ok = true;
for (var u = 0; u < 256; u++) { var v = f(u / 255); var bb = Math.floor(f(f(v * 255) + 0.5)); var sg = bb > 127.5 ? bb - 256 : bb; if (sg !== i8(u)) ok = false; }
out.decode = ok;
var rs = rgbStride4([10, 20, 30, 250, 251, 252]);
out.rgb = [rs.itemSize, rs.normalized, rs.data.stride, Array.from(rs.data.array)];
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
        """The curtain-wall chunks upload with geometry(true): style, base and tint reach the outer glass shader."""
        m = re.search(r"for \(const ch of glassChunks\.values\(\)\) \{\s*const g = ch\.geometry\((\w+)\);", self.src)
        self.assertIsNotNone(m, 'the glass chunk upload loop is gone from app.js')
        self.assertEqual('true', m.group(1), 'the glass chunks must upload with geometry(true), or the curtain-wall variants are lost')
        glass = self.src[self.src.index('outerGlassMat = new THREE.MeshStandardMaterial'):][:6000]
        for attr in ('${SFT_GLSL}', 'attribute float aBase;'):
            self.assertIn(attr, glass, 'the outer glass shader no longer declares ' + attr)
        self.assertIn("'#include <common>\\n' + SFT_GLSL + '\\nattribute float aWallU;", self.src, 'the facade shader must read aSFT')
        for mac in ("'#define aStyle (aSFT.w > 0.5 ? sftByte(aSFT.x) : aSFT.x)'", "'#define aFloorH (aSFT.w > 0.5 ? sftByte(aSFT.y) : aSFT.y)'", "'#define aTint aSFT.z'"):
            self.assertIn(mac, self.src)
        self.assertNotIn("'aStyle'", self.src, 'no geometry may carry the old 1-byte aStyle stream')
        self.assertNotIn("'aTint'", self.src, 'no geometry may carry the old 1-byte aTint stream')
        # mergeColored's full path writes the same attribute as raw floats with a 0 flag, so its tints keep full precision
        self.assertIn("out.setAttribute('aSFT', new THREE.BufferAttribute(sft, 4));", self.src)
        self.assertIn('sft[q] = styleV; sft[q + 1] = flhV; sft[q + 2] = tv;', self.src)

    def test_vbuf_attributes_survive_growth(self):
        """40 pushes through an 8-slot buffer (three doublings) keep style, base, floor height and tint on every vertex,
        on 4-aligned streams, and the shader's decode returns the old bytes exactly."""
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        script = JXA % {'three': json.dumps(str(C.path('three.min.js'))), 'snippet': vbuf_snippet(self.src)}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=180)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:600])
        out = json.loads(r.stdout.strip())
        self.assertEqual(40, out['n'])
        self.assertTrue(out['style'], 'the style byte lost through growth')
        self.assertTrue(out['base'], 'aBase lost through growth')
        self.assertTrue(out['floor'], 'the floor byte lost through growth')
        self.assertTrue(out['tint'], 'the tint byte lost through growth (0.62 -> byte 158)')
        self.assertTrue(out['flag'], 'the chunks must flag their aSFT as bytes (255 in the fourth slot)')
        self.assertTrue(out['sftNorm'] and out['sftItems'] == 4 and out['sftBytes'] == 1)
        self.assertTrue(out['nrmInter'] and out['nrmStride'] == 4 and out['nrmItems'] == 3 and out['nrmNorm'])
        self.assertEqual(127, out['nrmY'] * 127 if abs(out['nrmY']) <= 1 else out['nrmY'])
        self.assertEqual(4, out['clrStride']); self.assertEqual(3, out['clrItems'])
        self.assertEqual(127, out['clrR'], 'vertex 1 red: 0.5 * 255 truncated, as the Uint8 array stored it')
        self.assertTrue(out['aligned'], 'every stream must sit on a 4-byte stride and offset')
        self.assertEqual([-126, -126, -3], out['wrap'], 'the style and floor bytes must wrap exactly as the Int8 arrays did')
        self.assertTrue(out['decode'], 'the shader decode must return every byte exactly')
        self.assertEqual([3, True, 4, [10, 20, 30, 0, 250, 251, 252, 0]], out['rgb'])
        self.assertTrue(out['idxOk'] and out['bs'])
        self.assertEqual(1, out['freed'], 'geometry() must hand the buffers to freeOnUpload once')
        self.assertTrue(out['released'], 'geometry() must release the staging arrays')
        self.assertEqual(3, out['plainN'])
        self.assertFalse(out['plainHasSft'], 'geometry(false) must stay attribute-free (streets, water, trim)')

if __name__ == '__main__':
    unittest.main()
