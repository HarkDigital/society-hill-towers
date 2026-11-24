"""Round 270 (Stage 4, Mike: "Start the walls"): the pulled walls. A wall of the outer districts, the far ring and the towns
is one 48-byte record in a float texture, drawn by a shared index with no vertex stream, where it was four 32-byte vertices
and six indices. Under Node with the page's own VBuf and WallRecs: every wall pushed both ways decodes, by the vertex
shader's own arithmetic (WALL_PULL_GLSL, emulated in float32), to the very bytes the four vertices held (position, normal,
colour, style, floor, tint, base, length and height) and to the same two triangles with the same winding. And the page's
wiring: the hatch, the override materials, the facade attributes the pull replaces."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()

SIM = r'''
const f32 = Math.fround;
let seed = 11;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const vb = new VBuf(64), wr = new WallRecs();
const walls = [];
for (let i = 0; i < 4000; i++) {
  const ax = (rnd() - 0.5) * 30000, az = (rnd() - 0.5) * 30000, ang = rnd() * Math.PI * 2, len = 0.05 + Math.pow(rnd(), 2) * 120;
  const qx = ax + Math.cos(ang) * len, qz = az + Math.sin(ang) * len, base = (rnd() - 0.3) * 60, y0 = base - rnd() * 2, y1 = base + 3 + Math.pow(rnd(), 3) * 300;
  const dx = qx - ax, dz = qz - az, L = Math.hypot(dx, dz), sg = rnd() < 0.5 ? 1 : -1, nx = (dz / L) * sg, nz = (-dx / L) * sg;
  const r = rnd(), g = rnd(), b = rnd(), ra = rnd() < 0.7 ? 0.78 : 1, st = Math.floor(rnd() * 128) - (rnd() < 0.1 ? 0 : 0), fh = rnd() < 0.3 ? 0 : 2.6 + rnd() * 3, tint = rnd() < 0.5 ? 0 : rnd();
  const stw = rnd() < 0.2 ? st | 96 : st;
  const r0 = r * ra, g0 = g * ra, b0 = b * ra;
  // the VBuf's four corners and two triangles, as appendBuilding pushed them
  const i0 = vb.push(ax, y0, az, nx, 0, nz, r0, g0, b0, stw, base, fh, tint, 0, L, y1 - base);
  const i1 = vb.push(qx, y0, qz, nx, 0, nz, r0, g0, b0, stw, base, fh, tint, L, L, y1 - base);
  const i2 = vb.push(qx, y1, qz, nx, 0, nz, r, g, b, stw, base, fh, tint, L, L, y1 - base);
  const i3 = vb.push(ax, y1, az, nx, 0, nz, r, g, b, stw, base, fh, tint, 0, L, y1 - base);
  const fwd = ((-dz) * nx + dx * nz) >= 0;
  if (fwd) vb.idx.push(i0, i1, i2, i0, i2, i3); else vb.idx.push(i0, i2, i1, i0, i3, i2);
  wr.add(ax, az, qx, qz, y0, y1, nx, nz, r0, g0, b0, r, g, b, stw, base, fh, tint, L, y1 - base, !fwd);
}
// the vertex shader's decode, in float32 (every divisor a power of two: the integers come back exact)
const F = wr.f;
const corner = (w, k) => {
  const o = w * 12, t0 = [F[o], F[o + 1], F[o + 2], F[o + 3]], t1 = [F[o + 4], F[o + 5], F[o + 6], F[o + 7]], t2 = [F[o + 8], F[o + 9], F[o + 10], F[o + 11]];
  const fl = t2[2] >= 8388608 ? 1 : 0, lz = f32(t2[2] - fl * 8388608);
  if (fl && (k & 1) === 1) k = 4 - k;
  const u = k === 1 || k === 2, v = k >= 2;
  const nxb = Math.floor(lz / 32768), nzb = Math.floor(t2[3] / 32768), Ld = lz - nxb * 32768, Hd = t2[3] - nzb * 32768;
  const c = v ? t1[3] : t2[0], s = t2[1], rgb = (q) => [q % 256, Math.floor(q / 256) % 256, Math.floor(q / 65536)];
  return { k, pos: [u ? t0[2] : t0[0], v ? t1[1] : t1[0], u ? t0[3] : t0[1]], nor: [nxb, nzb], col: rgb(c), sft: rgb(s), base: t1[2], fac: [u ? Ld : -Ld, Hd] };
};
let bad = 0, first = null, tris = 0, flips = 0;
const s8 = (b) => b & 255;
for (let w = 0; w < walls.length || w < 4000; w++) {
  for (let k = 0; k < 4; k++) {
    const c = corner(w, k), pv = w * 4 + c.k;   // the physical corner this index slot draws
    const want = { pos: [vb.pos[pv * 3], vb.pos[pv * 3 + 1], vb.pos[pv * 3 + 2]], nor: [s8(vb.nor[pv * 4]), s8(vb.nor[pv * 4 + 2])], ny: vb.nor[pv * 4 + 1],
      col: [vb.col[pv * 4], vb.col[pv * 4 + 1], vb.col[pv * 4 + 2]], sft: [vb.sft[pv * 4], vb.sft[pv * 4 + 1], vb.sft[pv * 4 + 2]], w4: vb.sft[pv * 4 + 3], base: vb.bas[pv], fac: [vb.fac[pv * 2], vb.fac[pv * 2 + 1]] };
    const ok = JSON.stringify([c.pos, c.nor, c.col, c.sft, c.base, c.fac]) === JSON.stringify([want.pos, want.nor, want.col, want.sft, want.base, want.fac]) && want.ny === 0 && want.w4 === 255;
    if (!ok) { bad++; if (!first) first = { w, k, got: c, want }; }
  }
  // the two triangles: the shared index's [0,1,2, 0,2,3] through the pull's corners, against the VBuf's own six
  const shared = [0, 1, 2, 0, 2, 3].map((k) => w * 4 + corner(w, k).k), own = Array.from(vb.idx.a.subarray(w * 6, w * 6 + 6));
  const same = (a, b) => [0, 1, 2].some((r) => a[0] === b[r] && a[1] === b[(r + 1) % 3] && a[2] === b[(r + 2) % 3]);
  const A = [shared.slice(0, 3), shared.slice(3)], B = [own.slice(0, 3), own.slice(3)];
  if ((same(A[0], B[0]) && same(A[1], B[1])) || (same(A[0], B[1]) && same(A[1], B[0]))) tris++; else if (!first) first = { w, shared, own };
  if (F[w * 12 + 10] >= 8388608) flips++;
}
console.log(JSON.stringify({ n: wr.n, bad, tris, flips, first }));
'''


class WallPull(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        s = SRC
        vbuf = s[s.index('  class IdxBuf {'):s.index('  function rgbStride4(triples) {')] + s[s.index('  const _sftI8 = new Int8Array(1)'):s.index('  // ---- the pulled walls (Round 270')]
        recs = s[s.index('  const WALL_PER = 16383'):s.index('  const WALL_PULL_GLSL = [')]
        recs += s[s.index('  class WallRecs {'):s.index('\n  const groupCity = new THREE.Group();')]
        script = 'const THREE = { BufferGeometry: class {}, BufferAttribute: class {}, InterleavedBuffer: class {}, InterleavedBufferAttribute: class {} };\n' + vbuf + recs + SIM
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise AssertionError(r.stderr)
        cls.o = json.loads(r.stdout)

    def test_every_corner_decodes_to_the_vertex_it_was(self):
        self.assertEqual(self.o['n'], 4000)
        self.assertEqual(self.o['bad'], 0, self.o['first'])

    def test_same_triangles_same_winding(self):
        self.assertEqual(self.o['tris'], 4000, self.o['first'])
        self.assertGreater(self.o['flips'], 1000)   # both windings were exercised
        self.assertLess(self.o['flips'], 3000)


class Wiring(unittest.TestCase):
    def test_no_corner_is_the_restart_index(self):
        # WebGL 2 always restarts a strip at 0xFFFF in a Uint16 index: the shared index's highest corner stays under it
        per = int(re.search(r'const WALL_PER = (\d+)', SRC).group(1))
        self.assertLess(per * 4 - 1, 65535)

    def test_the_hatch(self):
        self.assertIn("const WALLS_Q = /[?&]walls=(quads|pull)\\b/.exec(location.search);", SRC)
        self.assertIn("want: WALLS_Q ? WALLS_Q[1] === 'pull' : isTouch", SRC)   # phone first, ?walls=quads today's walls
        self.assertIn('WALLS.on = WALLS.want && !!renderer.capabilities.isWebGL2', SRC)

    def test_the_facade_attributes_it_replaces_are_there(self):
        # wallPullText strips these declarations and puts the pull's globals in their place: if the facade's text moves, it throws
        self.assertIn("'attribute vec4 aSFT;',", SRC)
        self.assertIn("attribute float aWallU; attribute float aWallL; attribute float aWallH; attribute float aBase; attribute vec2 aFacade;\\nvarying vec3 vWPos;", SRC)
        self.assertIn("#define aWallU 0.0", SRC)   # a chunk never carries the core's float wall attributes: 0, never the context's stray value
        self.assertIn("WALLS.mat.customProgramCacheKey = () => cityMat.customProgramCacheKey() + '|pull';", SRC)

    def test_both_loops_pull_and_seal(self):
        self.assertEqual(SRC.count("if (ch.wr) { ch.wr.add(a[0], a[1], q[0], q[1], y0, y1, nx, nz, r0, g0, b0, r, g, b, st, base, fh, tint, L, y1 - base, ((-dz) * nx + dx * nz) < 0); continue; }"), 2)
        self.assertIn('for (const w of wallRecs.values()) w.seal();', SRC)
        self.assertIn('if (chunks.wallRecs) for (const w of chunks.wallRecs.values()) w.seal();', SRC)

    def test_the_depth_images_see_the_walls(self):
        # the pins' capture and the building tap share one override, and pickAt has its own: both pull a wall's corners
        self.assertIn("uniforms: wallPullOvU({ uFar: { value: PIN_OCC.far } })", SRC)
        self.assertIn("uniforms: wallPullOvU({ uId: { value: 0 } })", SRC)
        self.assertIn('r.state.bindTexture(gl.TEXTURE_2D, T, gl.TEXTURE0 + P.wpUnit);', SRC)   # the lit draw binds its texture alone
        self.assertIn('ov.value = 1; mat.uniformsNeedUpdate = true;', SRC)
        self.assertIn("if (!isTouch) mesh.customDepthMaterial = wallDepthMat(tex);", SRC)

    def test_the_beacon_says_so(self):
        self.assertIn("if (typeof WALLS !== 'undefined' && WALLS.on) o.wp = ", SRC)
        bp = (ROOT.parent / '.claude' / 'skills' / 'philly3d-capture' / 'scripts' / 'beacons.py').read_text()
        self.assertRegex(bp, r"RUN2 = \([^)]*'wp'")


if __name__ == '__main__':
    unittest.main()
