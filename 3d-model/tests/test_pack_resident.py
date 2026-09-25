"""The phones' memory (Sep 24): the resident geometry that still went to the GPU fat is packed before its first upload.

Measured at ready on the phone path, 48 static geometries carried Float32 normals and colours (5.3 M vertices) and the
overpass decks 1.1 M more. packResident walks groupCity ahead of every render behind the veil (flushUploads) and once
as build() ends, and packs what it may: a normal to four normalized bytes (packNormals; four, not three, because ANGLE's
Metal backend converts any vertex stride that is not a multiple of 4 into a padded copy it keeps beside the original),
a colour in [0, 1] to normalized shorts in an 8 B interleaved stride (never bytes: the stored-dark palette sits near
0.007 linear), and a Uint32 index to Uint16 when every index is under 65,535 (WebGL 2's primitive restart).

These checks cut packNormals and the packing block out of app.js and run them under Node with the vendored three.min.js
on synthetic geometries: the types and layouts, the colour error (at most 1/65535), the normal direction error (under
1 degree), what must be left alone, and the freeOnUpload hooks moving with the packed attributes. Then the wiring."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class PackResident(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')

    def run_js(self, body):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        pack_normals = cut(self.src, '  function packNormals(g) {', '\n  const _rwSeen')
        block = cut(self.src, '  function freeOnUpload(g) {', '\n  // base64 -> bytes for the packed blobs.')
        script = r'''
const THREE = require(THREE_PATH);
const PERF = { t0: 0 };
let themeSheet = null;
PACK_NORMALS
BLOCK
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function geom(n, opt) {
  opt = opt || {};
  const r = rng(opt.seed || 7), pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), cs = opt.colorSize || 3, col = new Float32Array(n * cs);
  for (let i = 0; i < n; i++) {
    pos[i * 3] = r() * 1000; pos[i * 3 + 1] = r() * 50; pos[i * 3 + 2] = r() * 1000;
    let x = r() * 2 - 1, y = r() * 2 - 1, z = r() * 2 - 1; const L = Math.hypot(x, y, z) || 1;
    nor[i * 3] = x / L; nor[i * 3 + 1] = y / L; nor[i * 3 + 2] = z / L;
    for (let k = 0; k < cs; k++) col[i * cs + k] = i % 3 === 0 ? r() : [0, 1, 0.007, 0.0071, 0.063][(i + k) % 5];   // the ends, the stored-dark palette and a spread
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, cs));
  return { g, nor, col, cs };
}
function colErr(g, col, cs) {   // through three's own denormalizing getters, the values the GPU reads
  const a = g.attributes.color; let e = 0;
  for (let i = 0; i < a.count; i++) for (let k = 0; k < cs; k++) { const v = [a.getX(i), a.getY(i), a.getZ(i), cs === 4 ? a.getW(i) : 0][k]; e = Math.max(e, Math.abs(v - col[i * cs + k])); }
  return e;
}
function nrmErrDeg(g, nor) {
  const a = g.attributes.normal; let e = 0;
  for (let i = 0; i < a.count; i++) {
    const x = a.getX(i), y = a.getY(i), z = a.getZ(i), L = Math.hypot(x, y, z);
    const d = (x * nor[i * 3] + y * nor[i * 3 + 1] + z * nor[i * 3 + 2]) / L;
    e = Math.max(e, Math.acos(Math.min(1, d)) * 180 / Math.PI);
  }
  return e;
}
const own = (o) => Object.prototype.hasOwnProperty.call(o, 'onUploadCallback');
const group = new THREE.Group();
BODY
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('PACK_NORMALS', pack_normals).replace('BLOCK', block).replace('BODY', body)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        return json.loads(r.stdout)

    def test_normals_and_colours_pack(self):
        out = self.run_js(r'''
const A = geom(5000), W = geom(3000, { colorSize: 4, seed: 11 });
group.add(new THREE.Mesh(A.g), new THREE.Mesh(W.g));
packResident(group);
const n = A.g.attributes.normal, c = A.g.attributes.color, wc = W.g.attributes.color;
let wZero = true; for (let i = 3; i < n.array.length; i += 4) if (n.array[i] !== 0) wZero = false;
console.log(JSON.stringify({
  nType: n.array.constructor.name, nSize: n.itemSize, nNorm: n.normalized, nBytes: n.array.byteLength / n.count, wZero,
  cInter: !!c.isInterleavedBufferAttribute, cType: c.array.constructor.name, cStride: c.data.stride, cSize: c.itemSize, cNorm: c.normalized, cBytes: c.array.byteLength / c.count,
  wType: wc.array.constructor.name, wSize: wc.itemSize, wNorm: wc.normalized, wInter: !!wc.isInterleavedBufferAttribute,
  cErr: colErr(A.g, A.col, 3), wErr: colErr(W.g, W.col, 4), nErr: nrmErrDeg(A.g, A.nor), wnErr: nrmErrDeg(W.g, W.nor),
  count: A.g.attributes.color.count, stats: PERF.pack }));''')
        self.assertEqual(out['nType'], 'Int8Array')
        self.assertEqual(out['nSize'], 4)                  # four bytes a vertex: a 4-aligned stride Metal draws as it stands
        self.assertTrue(out['nNorm'])
        self.assertEqual(out['nBytes'], 4)
        self.assertTrue(out['wZero'])
        self.assertTrue(out['cInter'])                     # a colour of three keeps itemSize 3 (no vertexAlphas) in an 8 B stride
        self.assertEqual(out['cType'], 'Uint16Array')      # shorts, never bytes
        self.assertEqual(out['cStride'], 4)
        self.assertEqual(out['cSize'], 3)
        self.assertTrue(out['cNorm'])
        self.assertEqual(out['cBytes'], 8)
        self.assertEqual(out['count'], 5000)
        self.assertEqual(out['wType'], 'Uint16Array')      # the water's shore alpha rides along as a plain four-item attribute
        self.assertEqual(out['wSize'], 4)
        self.assertTrue(out['wNorm'])
        self.assertFalse(out['wInter'])
        self.assertLessEqual(out['cErr'], 1 / 65535)
        self.assertLessEqual(out['wErr'], 1 / 65535)
        self.assertLess(out['nErr'], 1.0)
        self.assertLess(out['wnErr'], 1.0)
        st = out['stats']
        self.assertEqual((st['geoms'], st['normals'], st['colors'], st['passes']), (2, 2, 2, 1))
        # 8000 vertices: 12 B of normal and 12 (16 for the water) of colour each, to 4 and 8
        self.assertEqual(st['fromB'], 5000 * 24 + 3000 * 28)
        self.assertEqual(st['toB'], 8000 * 12)

    def test_indices(self):
        out = self.run_js(r'''
function indexed(nv, maxIx) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(nv * 3), 3));
  const ix = new Uint32Array(3000); for (let i = 0; i < ix.length; i++) ix[i] = i % 7 === 0 ? maxIx : i % nv;
  g.setIndex(new THREE.BufferAttribute(ix, 1));
  return g;
}
const a = indexed(65535, 65534), b = indexed(65536, 65535), c = indexed(70000, 69999), d = indexed(100, 99);
for (const g of [a, b, c, d]) group.add(new THREE.Mesh(g));
packResident(group);
const t = (g) => g.index.array.constructor.name;
let same = true; for (let i = 0; i < 3000; i++) if (a.index.array[i] !== (i % 7 === 0 ? 65534 : i % 65535)) same = false;
console.log(JSON.stringify({ a: t(a), b: t(b), c: t(c), d: t(d), same, n: a.index.count }));''')
        self.assertEqual(out['a'], 'Uint16Array')           # 65,535 vertices, every index at most 65,534
        self.assertEqual(out['b'], 'Uint32Array')           # 0xFFFF is WebGL 2's primitive restart: stays wide
        self.assertEqual(out['c'], 'Uint32Array')
        self.assertEqual(out['d'], 'Uint16Array')
        self.assertTrue(out['same'])
        self.assertEqual(out['n'], 3000)

    def test_left_alone(self):
        out = self.run_js(r'''
const R = geom(200, { seed: 3 }); R.g.attributes.color.array[5] = 1.3;          // a tint ratio over 1: the colour stays, the normals pack
const D = geom(200, { seed: 4 }); D.g.attributes.normal.array[4] = 5;           // a normal attribute carrying data
const Y = geom(200, { seed: 5 }); Y.g.attributes.color.setUsage(THREE.DynamicDrawUsage);
const T = geom(200, { seed: 6 }); themeSheet = new THREE.Mesh(T.g);            // the skyline's wash: colours rewritten every eased frame
const I = geom(200, { seed: 8 }), P = geom(200, { seed: 9 }), L = geom(200, { seed: 10 });
const F = geom(200, { seed: 12 }); for (const k in F.g.attributes) F.g.attributes[k].array = null;   // uploaded and freed already
const S = geom(200, { seed: 13 });                                              // first seen through an instanced mesh: never packed later
group.add(new THREE.Mesh(R.g), new THREE.Mesh(D.g), new THREE.Mesh(Y.g), themeSheet, new THREE.InstancedMesh(I.g, null, 4), new THREE.Points(P.g), new THREE.LineSegments(L.g), new THREE.Mesh(F.g), new THREE.InstancedMesh(S.g, null, 2));
packResident(group);
group.add(new THREE.Mesh(S.g));
const Z = geom(200, { seed: 14 }); const zm = new THREE.Mesh(Z.g); group.add(zm);
packResident(group);
const before = Z.g.attributes.normal;
Z.g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(600), 3));   // after a pass: never repacked (it may be on the GPU)
packResident(group);
const k = (g) => [g.attributes.normal.array ? g.attributes.normal.array.constructor.name : null, g.attributes.color.array ? g.attributes.color.array.constructor.name : null];
console.log(JSON.stringify({ R: k(R.g), D: k(D.g), Y: k(Y.g), T: k(T.g), I: k(I.g), P: k(P.g), L: k(L.g), F: k(F.g), S: k(S.g), Z: k(Z.g), zFirst: before.array.constructor.name, passes: PERF.pack.passes }));''')
        self.assertEqual(out['R'], ['Int8Array', 'Float32Array'])
        self.assertEqual(out['D'], ['Float32Array', 'Uint16Array'])
        self.assertEqual(out['Y'], ['Int8Array', 'Float32Array'])
        for key in ('T', 'I', 'P', 'L', 'S'):
            self.assertEqual(out[key], ['Float32Array', 'Float32Array'], key)
        self.assertEqual(out['F'], [None, None])
        self.assertEqual(out['zFirst'], 'Int8Array')
        self.assertEqual(out['Z'], ['Float32Array', 'Uint16Array'])
        self.assertEqual(out['passes'], 3)

    def test_upload_hooks_follow_the_packed_arrays(self):
        out = self.run_js(r'''
const F = geom(300, { seed: 21 }); F.g.setIndex(new THREE.BufferAttribute(new Uint32Array([0, 1, 2, 2, 1, 3]), 1)); freeOnUpload(F.g);
const K = geom(300, { seed: 22 });                                              // no freeOnUpload: its packed arrays stay
const O = geom(300, { seed: 23 }); O.g.setAttribute('aLane', new THREE.BufferAttribute(new Float32Array(1200), 4)); freeShadingOnUpload(O.g);
group.add(new THREE.Mesh(F.g), new THREE.Mesh(K.g), new THREE.Mesh(O.g));
packResident(group);
// what three's WebGLAttributes.createBuffer does at the upload: the attribute's (or the interleaved buffer's) callback
const up = (a) => (a.isInterleavedBufferAttribute ? a.data : a).onUploadCallback();
for (const g of [F.g, K.g, O.g]) { for (const k in g.attributes) up(g.attributes[k]); if (g.index) g.index.onUploadCallback(); }
const gone = (g) => Object.fromEntries(Object.keys(g.attributes).map((k) => [k, g.attributes[k].array === null]).concat(g.index ? [['index', g.index.array === null]] : []));
console.log(JSON.stringify({ F: gone(F.g), K: gone(K.g), O: gone(O.g), fIx: F.g.index.count, kOwn: own(K.g.attributes.normal) || own(K.g.attributes.color.data), bs: !!O.g.boundingSphere }));''')
        self.assertEqual(out['F'], {'position': True, 'normal': True, 'color': True, 'index': True})
        self.assertEqual(out['fIx'], 6)
        self.assertEqual(out['K'], {'position': False, 'normal': False, 'color': False})
        self.assertFalse(out['kOwn'])
        # the overpass decks stay a raycast target: positions kept, the shading arrays go
        self.assertEqual(out['O'], {'position': False, 'normal': True, 'color': True, 'aLane': True})
        self.assertTrue(out['bs'])

    def test_pack_normals_clamps(self):
        out = self.run_js(r'''
const g = new THREE.BufferGeometry();
g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(6), 3));
g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array([1.0009, -1.0009, 0, 0, 0.7071068, -0.7071068]), 3));
packNormals(g);
console.log(JSON.stringify(Array.from(g.attributes.normal.array)));''')
        self.assertEqual(out, [127, -127, 0, 0, 0, 90, -90, 0])   # never wrapped to -128 (a flipped normal)

    def test_wiring(self):
        s = self.src
        flush = cut(s, '  const flushUploads = (all) => {', '\n  };')
        self.assertLess(flush.index('packResident(groupCity);'), flush.index('renderer.render(scene, camera)'))
        b = cut(s, '  async function build() {', '\n  }\n')
        self.assertLess(b.index('for (const s of buildSteps)'), b.index('packResident(groupCity);'))
        self.assertLess(b.index('packResident(groupCity);'), b.index("bootMark('ready')"))
        self.assertIn('const mesh = new THREE.Mesh(mergeColored(parts), ovpMat);\n      freeShadingOnUpload(mesh.geometry);', s)
        self.assertIn('rayTargets.push(mesh);', cut(s, 'const mesh = new THREE.Mesh(mergeColored(parts), ovpMat);', 'if (collarParts.length)'))
        self.assertIsNotNone(re.search(r"o === themeSheet", cut(s, '  function packResident(root) {', '\n  }\n')))
        # packNormals' callers (the two ring road loops) still hand the packed geometry to freeOnUpload
        self.assertEqual(s.count('packNormals(g);\n'), 2)


if __name__ == '__main__':
    unittest.main()
