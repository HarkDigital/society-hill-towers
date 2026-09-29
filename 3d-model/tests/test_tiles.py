"""Round 167 (the phones' triangles): the city-wide merged meshes go into the scene as frustum-culled tiles.

A merged world-space mesh that spans the city has one bounding sphere as wide as the city, so frustum culling never drops
it. tileGeometry cuts the far ring's streets (and the towns'), its ground strips and parks, the outer districts' streets,
the overpass decks and the lots and yards into grid tiles by triangle centroid (TILE_CELL), each with its own bounding
sphere, and addTiles stages the tiles like the chunks (drawn unculled once behind the veil so they upload and free their
arrays, gotcha 12).

The promise is NO VISIBLE CHANGE, so these checks cut tileGeometry, tileMesh and addTiles out of app.js and run them
under Node with the vendored three.min.js on synthetic geometries: every source triangle lands in exactly one tile with
every attribute value of its three vertices bit for bit and in its source order; every attribute keeps its array type,
item size, normalization, usage and (interleaved) stride and offsets, so no 3-byte or 1-byte stream appears (Round 158);
the upload hooks ride along; an index is Uint16 exactly where packResident would make it; groups, draw ranges and the
refusals behave; the mesh's flags, hooks and matrices are copied. Then the wiring at every call site."""
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


class Tiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')

    def run_js(self, body):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        pack_normals = cut(self.src, '  function packNormals(g) {', '\n  const _rwSeen')
        free = cut(self.src, '  function freeOnUpload(g) {', '\n  // ---- resident packing')
        tiles = cut(self.src, '  // ---- tiles (Round 167', '\n  // base64 -> bytes for the packed blobs.')
        add = cut(self.src, '  // Round 167: a city-wide merged mesh goes into the scene', '\n  // Wide roads and parks extend')
        script = r'''
const THREE = require(THREE_PATH);
const PERF = {};
const location = { search: LOC };
const pendingUpload = [];
const groupCity = new THREE.Group();
PACK_NORMALS
FREE
TILES
ADD
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
// every triangle as the full value tuple of its three vertices, read through three's own getters
function vals(g, v) {
  const out = [];
  for (const k of Object.keys(g.attributes).sort()) {
    const a = g.attributes[k];
    out.push(k + ':' + [a.getX(v), a.itemSize > 1 ? a.getY(v) : '', a.itemSize > 2 ? a.getZ(v) : '', a.itemSize > 3 ? a.getW(v) : ''].join(','));
  }
  return out.join('|');
}
function tris(g) {
  const ix = g.index, n = ix ? ix.count : g.attributes.position.count, out = [];
  const s0 = g.drawRange.start, s1 = Math.min(n, g.drawRange.start + g.drawRange.count);
  for (let o = s0; o + 2 < s1; o += 3) { const t = []; for (let j = 0; j < 3; j++) t.push(vals(g, ix ? ix.getX(o + j) : o + j)); out.push(t.join(' / ')); }
  return out;
}
function cellOf(g, o, cell) {
  const ix = g.index, p = g.attributes.position;
  let cx = 0, cz = 0; for (let j = 0; j < 3; j++) { const v = ix ? ix.getX(o + j) : o + j; cx += p.getX(v); cz += p.getZ(v); }
  return Math.floor(cx / 3 / cell) + ':' + Math.floor(cz / 3 / cell);
}
// the source triangles grouped by the cell their centroid falls in, in source order
function expected(g, cell) {
  const ix = g.index, n = ix ? ix.count : g.attributes.position.count, by = new Map(), all = tris(g);
  const s0 = g.drawRange.start;
  for (let t = 0; t < all.length; t++) { const k = cellOf(g, s0 + t * 3, cell); if (!by.has(k)) by.set(k, []); by.get(k).push(all[t]); }
  return by;
}
function same(by, tiles, cell) {
  if (by.size !== tiles.length) return 'tile count ' + tiles.length + ' against ' + by.size + ' cells';
  const seen = new Set();
  for (const tg of tiles) {
    const k = cellOf(tg, 0, cell);
    if (seen.has(k)) return 'two tiles for ' + k;
    seen.add(k);
    const a = tris(tg), b = by.get(k);
    if (!b) return 'a tile in no cell ' + k;
    if (a.length !== b.length) return k + ': ' + a.length + ' triangles against ' + b.length;
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return k + ': triangle ' + i + ' differs';
  }
  return 'ok';
}
function sphereCovers(tg) {
  const p = tg.attributes.position, bs = tg.boundingSphere, v = new THREE.Vector3();
  if (!bs) return false;
  for (let i = 0; i < p.count; i++) if (v.fromBufferAttribute(p, i).distanceTo(bs.center) > bs.radius + 1e-3) return false;
  return true;
}
function grid(nx, nz, x0, z0, cell, withColor) {   // the far strips' own layout: (nx + 1) x (nz + 1) vertices, a, d, b, b, d, e
  const pos = [], col = [], idx = [], r = rng(5);
  for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) { pos.push(x0 + i * cell, r() * 30, z0 + j * cell); col.push(r(), r(), r() * 1.4); }
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) { const a = j * (nx + 1) + i, b = a + 1, d = a + nx + 1, e = d + 1; idx.push(a, d, b, b, d, e); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  if (withColor) g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(col), 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}
const own = (o) => Object.prototype.hasOwnProperty.call(o, 'onUploadCallback');
const up = (a) => (a.isInterleavedBufferAttribute ? a.data : a).onUploadCallback();
BODY
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('LOC', json.dumps(getattr(self, 'loc', ''))) \
            .replace('PACK_NORMALS', pack_normals).replace('FREE', free).replace('TILES', tiles).replace('ADD', add).replace('BODY', body)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        return json.loads(r.stdout)

    def test_indexed_grid_splits_exactly(self):
        """A far strip's layout (indexed, Float32 normals, a tint colour over 1) cut at 2,400 m: every triangle in the tile
        of its centroid, bit for bit and in order; a seam vertex copied into both tiles; Uint16 indices; the source consumed;
        spheres that cover their tiles; the freeOnUpload hooks on every tile's arrays."""
        out = self.run_js(r'''
const g = grid(150, 90, -3725, -2240, 50, true);
freeOnUpload(g);
const by = expected(g, 2400), nv = g.attributes.position.count, nt = g.index.count / 3;
const ts = tileGeometry(g, 2400);
let vOut = 0, u16 = true, types = new Set(), hooks = true, covers = true, freed = true;
for (const tg of ts) {
  vOut += tg.attributes.position.count;
  if (!(tg.index.array instanceof Uint16Array)) u16 = false;
  for (const k in tg.attributes) { const a = tg.attributes[k]; types.add(k + ':' + a.array.constructor.name + ':' + a.itemSize + ':' + a.normalized); if (!own(a)) hooks = false; }
  if (!own(tg.index)) hooks = false;
  if (!sphereCovers(tg)) covers = false;
}
const check = same(by, ts, 2400);
for (const tg of ts) { for (const k in tg.attributes) up(tg.attributes[k]); tg.index.onUploadCallback(); for (const k in tg.attributes) if (tg.attributes[k].array !== null) freed = false; if (!tg.boundingSphere) freed = false; }
console.log(JSON.stringify({ check, tiles: ts.length, cells: by.size, nv, vOut, nt, u16, types: [...types].sort(), hooks, covers, freed, left: Object.keys(g.attributes).length, index: g.index }));''')
        self.assertEqual(out['check'], 'ok')
        self.assertEqual(out['tiles'], out['cells'])
        self.assertGreater(out['tiles'], 4)
        self.assertGreater(out['vOut'], out['nv'])               # the seams are copied into both tiles
        self.assertLess(out['vOut'], out['nv'] * 1.1)
        self.assertTrue(out['u16'])
        self.assertEqual(out['types'], ['color:Float32Array:3:false', 'normal:Float32Array:3:false', 'position:Float32Array:3:false'])
        self.assertTrue(out['hooks'])
        self.assertTrue(out['covers'])
        self.assertTrue(out['freed'])
        self.assertEqual(out['left'], 0)                         # the source is consumed
        self.assertIsNone(out['index'])

    def test_streams_keep_their_layout(self):
        """The far streets' streams: Float32 positions, Int8 normals four to a vertex (packNormals), a byte colour on a
        4-byte stride read as three (rgbStride4), Float32 lane paint, and an interleaved buffer two attributes share.
        Every stream keeps its type, item size, normalization, usage, stride and offset, so every vertex stream stays
        4-byte aligned (Round 158); the shared buffer stays shared; the hooks ride on the buffers."""
        out = self.run_js(r'''
const n = 9000, r = rng(9), pos = new Float32Array(n * 3), rgb = [], lane = new Float32Array(n * 4), pair = new Float32Array(n * 4);
for (let i = 0; i < n; i++) { pos[i * 3] = r() * 20000 - 10000; pos[i * 3 + 1] = r() * 20; pos[i * 3 + 2] = r() * 20000 - 10000; rgb.push(Math.floor(r() * 256), Math.floor(r() * 256), Math.floor(r() * 256)); for (let k = 0; k < 4; k++) { lane[i * 4 + k] = r() * 100; pair[i * 4 + k] = r(); } }
for (let t = 0; t < n; t += 3) for (let j = 1; j < 3; j++) { pos[(t + j) * 3] = pos[t * 3] + r() * 30; pos[(t + j) * 3 + 2] = pos[t * 3 + 2] + r() * 30; }
const g = new THREE.BufferGeometry();
g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(n * 3).map(() => r() * 2 - 1), 3)); packNormals(g);
const u = new Uint8Array(n * 4); for (let i = 0; i < n; i++) { u[i * 4] = rgb[i * 3]; u[i * 4 + 1] = rgb[i * 3 + 1]; u[i * 4 + 2] = rgb[i * 3 + 2]; }
g.setAttribute('color', new THREE.InterleavedBufferAttribute(new THREE.InterleavedBuffer(u, 4), 3, 0, true));
g.setAttribute('aLane', new THREE.BufferAttribute(lane, 4));
const ib = new THREE.InterleavedBuffer(pair, 4); ib.setUsage(THREE.DynamicDrawUsage);
g.setAttribute('aA', new THREE.InterleavedBufferAttribute(ib, 2, 0));
g.setAttribute('aB', new THREE.InterleavedBufferAttribute(ib, 2, 2));
freeShadingOnUpload(g);   // the overpass decks: a raycast target keeps its positions
const by = expected(g, 4800);
const ts = tileGeometry(g, 4800);
const lay = new Set(); let shared = true, aligned = true, posKept = true, others = true, usage = true;
for (const tg of ts) {
  for (const k in tg.attributes) {
    const a = tg.attributes[k], d = a.isInterleavedBufferAttribute ? a.data : null, bpe = a.array.BYTES_PER_ELEMENT;
    lay.add(k + ':' + a.array.constructor.name + ':' + a.itemSize + ':' + a.normalized + ':' + (d ? 'stride' + d.stride + '@' + a.offset : 'plain'));
    if ((d ? d.stride * bpe : a.itemSize * bpe) % 4 || (d && (a.offset * bpe) % 4)) aligned = false;
  }
  if (tg.attributes.aA.data !== tg.attributes.aB.data) shared = false;
  if (tg.attributes.aA.data.usage !== THREE.DynamicDrawUsage) usage = false;
  if (own(tg.attributes.position)) posKept = false;
  if (!own(tg.attributes.normal) || !own(tg.attributes.color.data) || !own(tg.attributes.aLane) || !own(tg.attributes.aA.data)) others = false;
}
console.log(JSON.stringify({ check: same(by, ts, 4800), tiles: ts.length, nonIndexed: ts.every((tg) => tg.index === null), lay: [...lay].sort(), shared, aligned, posKept, others, usage, vOut: ts.reduce((s, tg) => s + tg.attributes.position.count, 0) }));''')
        self.assertEqual(out['check'], 'ok')
        self.assertGreater(out['tiles'], 10)
        self.assertTrue(out['nonIndexed'])
        self.assertEqual(out['vOut'], 9000)                     # a non-indexed mesh copies nothing twice
        self.assertEqual(out['lay'], ['aA:Float32Array:2:false:stride4@0', 'aB:Float32Array:2:false:stride4@2', 'aLane:Float32Array:4:false:plain',
                                      'color:Uint8Array:3:true:stride4@0', 'normal:Int8Array:4:true:plain', 'position:Float32Array:3:false:plain'])
        self.assertTrue(out['shared'])
        self.assertTrue(out['aligned'])
        self.assertTrue(out['usage'])
        self.assertTrue(out['posKept'])                          # freeShadingOnUpload: the positions stay for the raycast
        self.assertTrue(out['others'])

    def test_index_width_follows_pack_index(self):
        """Uint16 exactly where packResident's packIndex would make it: a tile of 65,535 vertices (every index at most
        65,534) is Uint16, one of 65,536 stays Uint32 (0xFFFF is WebGL 2's primitive restart)."""
        out = self.run_js(r'''
function strip(nv) {   // one cell, every vertex used, indexed
  const pos = new Float32Array(nv * 3); for (let i = 0; i < nv; i++) { pos[i * 3] = (i % 1000) * 0.5; pos[i * 3 + 2] = Math.floor(i / 1000) * 0.5; }
  const ix = new Uint32Array((nv - 2) * 3); for (let i = 0; i < nv - 2; i++) { ix[i * 3] = i; ix[i * 3 + 1] = i + 1; ix[i * 3 + 2] = i + 2; }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setIndex(new THREE.BufferAttribute(ix, 1)); return g;
}
const a = tileGeometry(strip(65535), 4800), b = tileGeometry(strip(65536), 4800);
console.log(JSON.stringify({ a: [a.length, a[0].index.array.constructor.name, a[0].attributes.position.count], b: [b.length, b[0].index.array.constructor.name, b[0].attributes.position.count] }));''')
        self.assertEqual(out['a'], [1, 'Uint16Array', 65535])
        self.assertEqual(out['b'], [1, 'Uint32Array', 65536])

    def test_groups_draw_range_and_refusals(self):
        """Groups survive as runs of each tile's triangles (a triangle outside every group is dropped: r149 never draws
        one), the draw range is honoured, and what cannot be cut comes back null with the geometry untouched: overlapping
        groups, morph targets, instancing, an attribute already freed, a cell of 0."""
        out = self.run_js(r'''
const G = () => grid(40, 10, -2400, 0, 120, false);
const g1 = G(); const nt = g1.index.count / 3;
g1.addGroup(0, 90, 0); g1.addGroup(90, 90, 1); g1.addGroup(270, g1.index.count - 270, 2);   // triangles 60..89 in no group
const src = tris(g1), keep = src.filter((t, i) => i < 60 || i >= 90);
const t1 = tileGeometry(g1, 2400);
let got = 0, groupsOk = true;
for (const tg of t1) {
  got += tg.index.count / 3;
  let end = 0; for (const gr of tg.groups) { if (gr.start !== end || gr.count % 3) groupsOk = false; end = gr.start + gr.count; }
  if (end !== tg.index.count) groupsOk = false;
}
const mats = t1.map((tg) => tg.groups.map((gr) => gr.materialIndex).join(''));
const g2 = G(); g2.setDrawRange(30, 150); const want2 = tris(g2).length; const t2 = tileGeometry(g2, 2400);
const refuse = [];
const g3 = G(); g3.addGroup(0, 60, 0); g3.addGroup(30, 60, 1); refuse.push([tileGeometry(g3, 2400), Object.keys(g3.attributes).length, !!g3.index]);
const g4 = G(); g4.morphAttributes.position = [g4.attributes.position.clone()]; refuse.push([tileGeometry(g4, 2400), Object.keys(g4.attributes).length, !!g4.index]);
const g5 = G(); g5.attributes.normal.array = null; refuse.push([tileGeometry(g5, 2400), Object.keys(g5.attributes).length, !!g5.index]);
const g6 = new THREE.InstancedBufferGeometry().copy(G()); refuse.push([tileGeometry(g6, 2400), Object.keys(g6.attributes).length, !!g6.index]);
const g7 = G(); refuse.push([tileGeometry(g7, 0), Object.keys(g7.attributes).length, !!g7.index]);
console.log(JSON.stringify({ nt, got, want: keep.length, groupsOk, mats, drawRange: t2.reduce((s, tg) => s + tg.index.count / 3, 0), want2, refuse }));''')
        self.assertEqual(out['got'], out['want'])
        self.assertEqual(out['want'], out['nt'] - 30)
        self.assertTrue(out['groupsOk'])
        self.assertTrue(all(set(m) <= {'0', '1', '2'} for m in out['mats']))
        self.assertEqual(out['drawRange'], out['want2'])
        self.assertEqual(out['want2'], 50)
        for r in out['refuse']:
            self.assertEqual(r, [None, 2, True])

    def test_tile_mesh_and_add_tiles(self):
        """tileMesh copies what the renderer and the rest of the page read: the shared material, render order, layers,
        shadow flags, visibility, culling flag, user data (noPack), render hooks, matrices. addTiles stages every tile
        unculled in pendingUpload (flushUploads or the first frame culls it again) and adds a mesh it cannot cut whole."""
        out = self.run_js(r'''
const mat = new THREE.MeshBasicMaterial({ transparent: true });
const m = new THREE.Mesh(grid(100, 20, -4000, -600, 80, true), mat);
m.renderOrder = 5; m.layers.set(3); m.castShadow = true; m.receiveShadow = true; m.userData.noPack = true; m.matrixAutoUpdate = false; m.name = 'lettering';
const hook = () => 1; m.onBeforeRender = hook;
const parent = new THREE.Object3D();
const ts = addTiles(m, 'wide roads', parent);
const flags = ts.map((t) => [t.material === mat, t.renderOrder, t.layers.mask, t.castShadow, t.receiveShadow, t.visible, t.frustumCulled, t.userData.noPack === true, t.userData !== m.userData, t.matrixAutoUpdate, t.onBeforeRender === hook, t.name, t.parent === parent, t.position.lengthSq()].join(','));
const staged = pendingUpload.length === ts.length && ts.every((t) => pendingUpload.includes(t));
const whole = new THREE.Mesh(new THREE.BufferGeometry(), mat);   // nothing to cut: added as it was
const w = addTiles(whole, 'lots');
console.log(JSON.stringify({ n: ts.length, flags: [...new Set(flags)], staged, stats: PERF.tiles, whole: [w.length, w[0] === whole, whole.parent === groupCity, pendingUpload.length] }));''')
        self.assertGreater(out['n'], 3)
        self.assertEqual(out['flags'], ['true,5,8,true,true,true,false,true,true,false,true,lettering,true,0'])
        self.assertTrue(out['staged'])
        st = out['stats']['wide roads']
        self.assertEqual((st['meshes'], st['tiles']), (1, out['n']))
        self.assertEqual(st['vIn'], 101 * 21)
        self.assertGreaterEqual(st['vOut'], st['vIn'])
        self.assertEqual(out['whole'][:3], [1, True, True])
        self.assertEqual(out['whole'][3], out['n'])             # the whole mesh is not staged: it culls as it always did

    def test_nan_triangles_share_one_tile(self):
        """A triangle whose centroid is NaN (a degenerate read) lands in one tile of its own, which has a NaN sphere and so
        is never culled: drawn exactly as the whole mesh was."""
        out = self.run_js(r'''
const g = grid(30, 5, 0, 0, 100, false); const p = g.attributes.position.array; p[0] = NaN;
const ts = tileGeometry(g, 2400), nan = ts.filter((tg) => !(tg.boundingSphere.radius >= 0));
const f = new THREE.Frustum(new THREE.Plane(new THREE.Vector3(1, 0, 0), -1e9));
console.log(JSON.stringify({ tiles: ts.length, nan: nan.length, tris: ts.reduce((s, tg) => s + tg.index.count / 3, 0), drawn: nan.every((tg) => f.intersectsSphere(tg.boundingSphere)) }));''')
        self.assertEqual(out['nan'], 1)
        self.assertEqual(out['tris'], 30 * 5 * 2)
        self.assertTrue(out['drawn'])

    def test_wiring(self):
        """The city-wide flats go in through addTiles at their measured cells; the decks' tiles are the raycast targets;
        the far water, the outer districts' parks and the street lettering stay whole (no cell paid for its calls); the
        first frame culls what the steps staged after the last flush; no strip is tiled before it registered its ground."""
        s = self.src
        cells = re.search(r"const TILE_CELL = (\{[^}]*\});", s).group(1)
        self.assertEqual(json.loads(cells.replace("'", '"')), {'ring roads': 4800, 'far ground': 7200, 'decks': 4800, 'lots': 9600, 'ring areas': 19200, 'wide roads': 1800})
        for label in ('ring roads', 'ring areas', 'far ground', 'wide roads', 'lots', 'decks'):
            self.assertEqual(len(re.findall(r"addTiles\([^;]*, '%s'\)" % label, s)), 1, label)
        self.assertEqual(s.count('addTiles('), 7)                 # six call sites and the definition
        self.assertIn("for (const t of addTiles(mesh, 'decks')) rayTargets.push(t);", s)
        self.assertNotIn('rayTargets.push(mesh);\n    }\n    if (collarParts.length)', s)
        # kept whole, as before
        self.assertIn('stMesh = new THREE.Mesh(geo, stMat);\n    stMesh.renderOrder = 5;', s)
        self.assertIn('freeOnUpload(g); groupCity.add(occFlatTiles([new THREE.Mesh(g, riverMat)])[0]); }   // Round 168: flat for the pins\' capture\n  }\n  step(\'Raising the rest of Philadelphia\'', s)
        frame = cut(s, '  function frame(now, once) {', '\n  setHint();')
        tail = frame[frame.index('if (POST.on) renderPost(scene, camera); else renderer.render(scene, camera);'):]
        self.assertIn('if (pendingUpload.length) { for (const m of pendingUpload) m.frustumCulled = true; pendingUpload.length = 0; }', tail)
        # the far strips register their ground before they are cut (the registry reads its own arrays)
        mk = cut(s, '    const mkFarGround = (x0, x1, z0, z1, cell, hole, tint, sink) => {', '\n    };')
        self.assertLess(mk.index('registerGround(g, '), mk.index("addTiles(m, 'far ground')"))
        # the ring roads never go in whole
        ring = cut(s, '  async function uploadRing(R) {', "\n  step('Raising the rest of Philadelphia'")
        self.assertNotIn('groupCity.add(new THREE.Mesh(g, roadMat(', ring)

    def test_escape_hatch(self):
        """?tiles=0 draws every merged mesh whole (the A/B hatch)."""
        self.loc = '?dev=1&tiles=0'
        try:
            out = self.run_js(r'''
const m = new THREE.Mesh(grid(100, 20, -4000, -600, 80, false), new THREE.MeshBasicMaterial());
const a = addTiles(m, 'wide roads'), b = addTiles(new THREE.Mesh(grid(200, 10, -8000, 0, 80, false)), 'ring roads');
console.log(JSON.stringify({ off: TILE_OFF, a: [a.length, a[0] === m], b: b.length, staged: pendingUpload.length }));''')
        finally:
            del self.loc
        self.assertTrue(out['off'])
        self.assertEqual(out['a'], [1, True])
        self.assertEqual(out['b'], 1)
        self.assertEqual(out['staged'], 0)


class TileFlushCount(unittest.TestCase):
    def test_a_tiled_mesh_counts_once_toward_the_flush(self):
        # review (Round 167): the far ring's 48 tiles, staged after uploadRing's own flush, set off a whole-scene render in
        # the towns loop; a run of one mesh's tiles now counts once toward the dozen
        src = (Path(__file__).resolve().parents[1] / 'app.js').read_text()
        self.assertIn("t.userData.tileSet = mesh; pendingUpload.push(t);", src)
        self.assertIn("a[i - 1].userData.tileSet === m.userData.tileSet ? 0 : 1), 0) < 12)) return;", src)


if __name__ == '__main__':
    unittest.main()
