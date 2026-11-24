"""Round 272 (Stage 4's merged flats, Mike: "Yes, start it"): the lots, yards, parks, plazas, water sheets and overpass decks
go to the GPU welded, one copy of each shared vertex drawn through an index, where they were triangle soups.

The promise is NO VISIBLE CHANGE, so these checks cut weldGeometry (and the packing it leans on) out of app.js and run them
under Node with the vendored three.min.js: every triangle, read through the index, carries every attribute value of the
soup's three vertices bit for bit, in the soup's order and winding; a float is compared as its bits (-0 and 0 stay apart);
every attribute keeps its array type, item size, normalization, usage, and an interleaved buffer its stride and offsets;
the decks' nrmBytes weld leaves the normals packResident draws byte for byte as the soup's would have packed; the soup is
kept where an index would not pay, and nothing indexed, grouped or instanced is touched. Then the wiring at each site."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text(encoding='utf-8')


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


SIM = r'''
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
const tri = (g, t) => { const ix = g.index; const vs = [0, 1, 2].map((j) => ix ? ix.getX(t * 3 + j) : t * 3 + j); return vs.map((v) => Object.keys(g.attributes).sort().map((k) => { const a = g.attributes[k], o = []; for (let c = 0; c < a.itemSize; c++) { const x = [a.getX, a.getY, a.getZ, a.getW][c].call(a, v); o.push(Object.is(x, -0) ? '-0' : String(x)); } return k + ':' + o.join(','); }).join('|')).join(' / '); };
const ntri = (g) => (g.index ? g.index.count : g.attributes.position.count) / 3;
// a conformed sheet: a grid of cells, each two triangles, six fresh vertices a cell, with a colour per part
function sheet(r, nx, nz, col, negZero) {
  const pos = [], nor = [], c = [];
  const y = (i, j) => Math.fround(Math.sin(i * 0.7) + Math.cos(j * 0.3) + r() * 0);
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const P = (a, b) => { pos.push(a * 10, y(a, b), b * 10); nor.push(negZero && a === 0 ? -0 : 0, 1, 0); c.push(col[0], col[1], col[2]); };
    P(i, j); P(i, j + 1); P(i + 1, j); P(i + 1, j); P(i, j + 1); P(i + 1, j + 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(nor), 3));
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(c), 3));
  return g;
}
const out = {};
{ // a plain sheet of two colours
  const r = rng(3), a = sheet(r, 40, 30, [0.2, 0.5, 0.1], true), b = sheet(r, 20, 10, [0.3, 0.3, 0.3]);
  const n = a.attributes.position.count + b.attributes.position.count, cat = (k, s) => { const A = new Float32Array(n * s); A.set(a.attributes[k].array, 0); A.set(b.attributes[k].array, a.attributes[k].array.length); return A; };
  const soup = new THREE.BufferGeometry();
  for (const [k, s] of [['position', 3], ['normal', 3], ['color', 3]]) soup.setAttribute(k, new THREE.BufferAttribute(cat(k, s), s));
  soup.attributes.color.setUsage(THREE.StaticDrawUsage);
  const ref = []; for (let t = 0; t < ntri(soup); t++) ref.push(tri(soup, t));
  const before = n, g = weldGeometry(soup, 'sheet');
  let same = 0; for (let t = 0; t < ntri(g); t++) if (tri(g, t) === ref[t]) same++;
  out.sheet = { tris: ref.length, after: ntri(g), same, vFrom: before, vTo: g.attributes.position.count, index: g.index && g.index.array.constructor.name,
    types: Object.keys(g.attributes).map((k) => [k, g.attributes[k].array.constructor.name, g.attributes[k].itemSize, g.attributes[k].normalized]) };
}
{ // mergeLots' form: byte normals in four, an interleaved colour of three in a stride of four, a byte aLot
  const s = sheet(rng(5), 25, 25, [0, 0, 0]), n = s.attributes.position.count;
  const nor = new Int8Array(n * 4), col = new Uint8Array(n * 4), lot = new Uint8Array(n * 4);
  for (let i = 0; i < n; i++) { nor[i * 4 + 1] = 127; col[i * 4] = 40; col[i * 4 + 1] = 41; col[i * 4 + 2] = 42; col[i * 4 + 3] = (i * 7) % 3 === 0 ? 9 : 0; lot[i * 4] = 17; }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', s.attributes.position);
  g.setAttribute('normal', new THREE.BufferAttribute(nor, 4, true));
  g.setAttribute('color', new THREE.InterleavedBufferAttribute(new THREE.InterleavedBuffer(col, 4), 3, 0, true));
  g.setAttribute('aLot', new THREE.BufferAttribute(lot, 4, true));
  const ref = []; for (let t = 0; t < ntri(g); t++) ref.push(tri(g, t));
  weldGeometry(g, 'lots');
  let same = 0; for (let t = 0; t < ntri(g); t++) if (tri(g, t) === ref[t]) same++;
  const c = g.attributes.color;
  out.lots = { tris: ref.length, same, vTo: g.attributes.position.count, vFrom: n, inter: !!c.isInterleavedBufferAttribute, stride: c.data.stride, off: c.offset, colArr: c.data.array.constructor.name, nor: [g.attributes.normal.itemSize, g.attributes.normal.array.constructor.name] };
}
{ // the decks: face normals an ulp apart on one plane weld by their packed bytes, and pack to what the soup packed to
  const r = rng(9), pos = [];
  for (let q = 0; q < 300; q++) { const x = r() * 500, z = r() * 500, y = r() * 20, w = 3 + r() * 9, h = 2 + r() * 5, ang = r() * 6.28, ux = Math.cos(ang) * w, uz = Math.sin(ang) * w;
    const A = [x, y, z], B = [x + ux, y + r() * 0.3, z + uz], C = [x + ux, y + h, z + uz], D = [x, y + h, z];
    pos.push(...A, ...B, ...C, ...A, ...C, ...D); }
  const soup = new THREE.BufferGeometry();
  soup.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  soup.computeVertexNormals();
  const n = soup.attributes.position.count, col = new Float32Array(n * 3).fill(0.4); soup.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const exact = weldGeometry(soup.clone(), 'decks0');
  const pk = soup.clone(); packNormals(pk);
  const ref = []; for (let t = 0; t < ntri(pk); t++) ref.push(tri(pk, t));
  const g = weldGeometry(soup, 'decks', 0.8, true); packNormals(g);
  let same = 0; for (let t = 0; t < ntri(g); t++) if (tri(g, t) === ref[t]) same++;
  out.decks = { tris: ref.length, same, vFrom: n, vTo: g.attributes.position.count, exactKept: !exact.index };
}
{ // refusals: an indexed geometry, groups, and a soup with nothing to share
  const ix = sheet(rng(1), 4, 4, [1, 1, 1]); ix.setIndex([0, 1, 2]);
  const gr = sheet(rng(1), 4, 4, [1, 1, 1]); gr.addGroup(0, 6, 0);
  const r = rng(2), lone = new THREE.BufferGeometry(), lp = new Float32Array(900); for (let i = 0; i < lp.length; i++) lp[i] = r();
  lone.setAttribute('position', new THREE.BufferAttribute(lp, 3));
  out.refuse = { indexed: weldGeometry(ix, 'x').index.count, grouped: !!weldGeometry(gr, 'x').index, lone: !!weldGeometry(lone, 'x').index };
}
{ // a big soup's index is Uint32 (over 65,535 vertices after the weld), a small one's Uint16
  const big = sheet(rng(4), 330, 220, [0.1, 0.2, 0.3]);
  for (let i = 0; i < big.attributes.position.count; i++) big.attributes.color.array[i * 3] = (i % 5) / 7;   // every vertex its own colour
  weldGeometry(big, 'big', 2);
  out.big = { index: big.index.array.constructor.name, n: big.attributes.position.count };
}
out.weld = { geoms: WELD.geoms, kept: WELD.kept, labels: Object.keys(WELD.by).sort() };
console.log(JSON.stringify(out));
'''


class Weld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        weld = cut(SRC, '  // ---- the welded flats (Round 272', '\n  function box(w, h, d, x, y, z, ry) {')
        pack_normals = cut(SRC, '  function packNormals(g) {', '\n  const _rwSeen')
        in_range = cut(SRC, '  function packInRange(arr, lo, hi) {', '\n  function packColors(g) {')
        script = 'const THREE = require(' + json.dumps(str(ROOT / 'three.min.js')) + ');\nconst PERF = {};\n' + pack_normals + '\n' + in_range + '\n' + weld + SIM
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-3000:])
        cls.o = json.loads(r.stdout)

    def test_a_sheet_draws_every_triangle_as_it_was(self):
        s = self.o['sheet']
        self.assertEqual((s['after'], s['same']), (s['tris'], s['tris']))
        self.assertLess(s['vTo'], s['vFrom'] / 4)   # a grid node is six soup vertices
        self.assertEqual(s['index'], 'Uint16Array')
        self.assertEqual(s['types'], [['position', 'Float32Array', 3, False], ['normal', 'Float32Array', 3, False], ['color', 'Float32Array', 3, False]])

    def test_minus_zero_stays_apart(self):
        # the sheet's first column carries a -0 normal x: a float compares as its bits, so those vertices are not merged with
        # their +0 neighbours, and the triangles still read back exactly (the check above reads -0 as '-0')
        self.assertEqual(self.o['sheet']['same'], self.o['sheet']['tris'])

    def test_the_lots_form_keeps_its_four_byte_streams(self):
        s = self.o['lots']
        self.assertEqual(s['same'], s['tris'])
        self.assertLess(s['vTo'], s['vFrom'])
        self.assertEqual((s['inter'], s['stride'], s['off'], s['colArr']), (True, 4, 0, 'Uint8Array'))   # never a 3-byte stream (Round 158)
        self.assertEqual(s['nor'], [4, 'Int8Array'])

    def test_the_decks_weld_by_their_packed_normals(self):
        d = self.o['decks']
        self.assertTrue(d['exactKept'], 'to the bit, computeVertexNormals leaves no two deck vertices alike')
        self.assertEqual(d['same'], d['tris'], 'packed, every triangle draws what the packed soup drew')
        self.assertLess(d['vTo'], d['vFrom'] * 0.8)

    def test_refusals(self):
        r = self.o['refuse']
        self.assertEqual(r['indexed'], 3)
        self.assertFalse(r['grouped'])
        self.assertFalse(r['lone'], 'a soup with nothing to share stays a soup')

    def test_index_width(self):
        self.assertEqual(self.o['big']['index'], 'Uint32Array')
        self.assertGreater(self.o['big']['n'], 65535)

    def test_the_counter(self):
        w = self.o['weld']
        self.assertGreaterEqual(w['geoms'], 4)
        self.assertIn('sheet', w['labels'])


class Wiring(unittest.TestCase):
    def test_each_flat_is_welded(self):
        for line in (
            "const g = weldGeometry(mergeColored(areaParts), 'wide areas'); freeOnUpload(g);",
            "const g0 = weldGeometry(mergeColored(lotSheetParts), 'lot sheets'), g = GROUND_CUTS.length ? elPortalClipGround(g0) : g0; freeOnUpload(g);",
            "const g = weldGeometry(mergeColored(areaParts), 'ring areas'); freeOnUpload(g);",
            "const g = weldGeometry(mergeColored(parts), 'yards');",
            "weldGeometry(out, 'lots');",
            "const mesh = new THREE.Mesh(weldGeometry(mergeColored(parts), 'decks', 0.8, true), ovpMat);",
        ):
            self.assertEqual(SRC.count(line), 1, line)
        self.assertEqual(SRC.count("const g = weldGeometry(mergeWater(waterAreaParts), 'water'); freeOnUpload(g);"), 2)

    def test_mergecolored_itself_stays_a_soup(self):
        # opt in per caller: chFloorFar and a few others walk a merged mesh as consecutive triples
        mc = cut(SRC, '  function mergeColored(parts, ao, facade) {', '\n  // ---- the welded flats')
        self.assertNotIn('weldGeometry', mc)
        self.assertIn("if (typeof PERF !== 'undefined') PERF.weld = WELD;", SRC)


if __name__ == '__main__':
    unittest.main()
