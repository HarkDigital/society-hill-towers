"""Round 274 (Stage 4, Mike: "Yes, both"): the buildings' shadows on a phone, swept on the CPU from the flight's walls (HIT)
and drawn into the canopy map's blue channel. Under Node with the page's own HIT writer and sweep: random towers noted with
hitNote, the window filled and swept in slices as the frame loop does, then every cell's ceiling checked against a brute
march along the true sun ray; and the page's wiring (touch only, the hatch, the flats' and the facade's reads, the map
redrawn on a finished sweep)."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()

SIM = r'''
let seed = 7;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const towers = [];
for (let n = 0; n < 500; n++) {
  const x = (rnd() - 0.5) * 3000, z = (rnd() - 0.5) * 3000, w = 8 + rnd() * 40, d = 8 + rnd() * 40, h = 5 + Math.pow(rnd(), 3) * 250;
  hitNote([[x, z], [x + w, z], [x + w, z + d], [x, z + d]], h); towers.push([x, z, w, d, h]);
}
const res = [];
for (const [sx, sy, sz] of [[0.62, 0.42, 0.27], [-0.3, 0.55, 0.78], [0.05, 0.3, -0.95], [-0.7, 0.25, -0.66]]) {
  const L = Math.hypot(sx, sy, sz); sunDir.set(sx / L, sy / L, sz / L);
  BSH.H = new Uint8Array(BSH_N * BSH_N); BSH.out = new Uint8Array(BSH_N * BSH_N); BSH.prev = new Float32Array(BSH_N); BSH.cur = new Float32Array(BSH_N);
  bshStart(0, 0);
  const J = BSH.job; let slices = 0;
  while (!bshFill(J, performance.now())) slices++;
  while (!bshSweep(J, performance.now())) slices++;
  // the brute march: from each sampled cell's centre toward the sun in 2 m steps, the highest roof's ceiling over it, read
  // from HIT itself (hitTop); a cell's own roof is not its own shadow
  const hl = Math.hypot(sunDir.x, sunDir.z), ux = sunDir.x / hl, uz = sunDir.z / hl, tan = sunDir.y / hl;
  const brute = (ci, cj) => {   // the highest ceiling over the cell's centre, toward the sun in 2 m steps; its own roof left out
    const x = (ci + 0.5) * HIT_CELL, z = (cj + 0.5) * HIT_CELL;
    let best = -1e9;
    for (let t = 2; t < 1200; t += 2) {
      const pi = Math.floor((x + ux * t) / HIT_CELL), pj = Math.floor((z + uz * t) / HIT_CELL);
      if (pi === ci && pj === cj) continue;
      if (pi < J.i0 || pj < J.j0 || pi >= J.i0 + BSH_N || pj >= J.j0 + BSH_N) break;
      const h = hitTop(pi, pj);
      if (h > -1e8) best = Math.max(best, h - t * tan);
    }
    return best;
  };
  let n = 0, exact = 0, near = 0, over = 0;
  for (let s = 0; s < 3000; s++) {
    const i = BSH_N / 2 + Math.floor((rnd() - 0.5) * 800), j = BSH_N / 2 + Math.floor((rnd() - 0.5) * 800), q = BSH.out[j * BSH_N + i];
    const ci = J.i0 + i, cj = J.j0 + j, ceil = q ? q * HIT_DY + HIT_Y0 : -1e9, b0 = brute(ci, cj);
    if (b0 <= 0 && ceil <= 0) continue;   // open sun both ways: no information
    n++;
    if ((b0 > 0) === (ceil > 0) && Math.abs(ceil - b0) < 4) { exact++; near++; continue; }
    // a 4 m cell's ray against the true one: the value must lie within what the true ray gives over the cell's neighbours
    let lo = Infinity, hi = -Infinity;
    for (let a = -1; a <= 1; a++) for (let c = -1; c <= 1; c++) { const v = Math.max(0, brute(ci + a, cj + c)); lo = Math.min(lo, v); hi = Math.max(hi, v); }
    const v = Math.max(0, ceil);
    if (v >= lo - 4 && v <= hi + 4) near++;
    if (v > hi + 4) over++;
  }
  res.push({ n, exact, near, over, slices });
}
// one tower alone: nothing upstream of it is shaded, and its shadow's length is its height over the sun's tangent
HIT.dense.clear(); HIT.packed.clear(); HIT.key = -1; HIT.arr = null;
hitNote([[0, 0], [20, 0], [20, 20], [0, 20]], 100);
sunDir.set(0.8, 0.36, 0).normalize ? 0 : 0;
{ const L = Math.hypot(0.8, 0.36); sunDir.set(0.8 / L, 0.36 / L, 0); }
BSH.H.fill(0); bshStart(0, 0); { const J = BSH.job; while (!bshFill(J, performance.now())); while (!bshSweep(J, performance.now())); }
const J = BSH.job, row = Math.floor((10 - J.j0 * HIT_CELL) / HIT_CELL);
let upShaded = 0, len = 0;
for (let i = 0; i < BSH_N; i++) {
  const x = (J.i0 + i + 0.5) * HIT_CELL, q = BSH.out[row * BSH_N + i];
  if (x > 20 && q) upShaded++;
  if (x < 0 && q && (q * HIT_DY + HIT_Y0) > 0) len = Math.max(len, -x);
}
console.log(JSON.stringify({ res, upShaded, len, want: 100 / (0.36 / 0.8) }));
'''


class Sweep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        s = SRC
        hit = s[s.index('  const HIT_ON = '):s.index('  function hitSquare(')]
        bsh = s[s.index('  const BSH_ON = '):s.index('  function bshUpdate() {')]
        pre = '''
class V3 { constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; } set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  clone() { return new V3(this.x, this.y, this.z); } copy(v) { return this.set(v.x, v.y, v.z); } dot(v) { return this.x * v.x + this.y * v.y + this.z * v.z; } }
class V4 { constructor() { this.x = this.y = this.z = this.w = 0; } set(a, b, c, d) { this.x = a; this.y = b; this.z = c; this.w = d; return this; } toArray() { return [this.x, this.y, this.z, this.w]; } }
const THREE = { Vector3: V3, Vector4: V4 };
const location = { search: '' }, isTouch = true, REAL = true, sunDir = new V3(0, 1, 0);
const polyCentroid = (p) => { let x = 0, z = 0; for (const q of p) { x += q[0]; z += q[1]; } return [x / p.length, z / p.length]; };
'''
        r = subprocess.run(['node', '-e', pre + hit + bsh + SIM], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-3000:])
        cls.o = json.loads(r.stdout)

    def test_matches_a_brute_march(self):
        for r in self.o['res']:
            self.assertGreater(r['n'], 400, r)
            self.assertGreater(r['exact'] / r['n'], 0.9, r)    # the Bresenham ray against the true ray, 4 m cells
            self.assertGreater(r['near'] / r['n'], 0.995, r)   # and the rest within one cell of it
            self.assertLess(r['over'] / r['n'], 0.005, r)
            self.assertGreater(r['slices'], 0, r)              # the frame loop's slices were exercised

    def test_one_tower(self):
        self.assertEqual(self.o['upShaded'], 0)
        self.assertLess(abs(self.o['len'] - self.o['want']), 8, self.o)


class Wiring(unittest.TestCase):
    def test_phone_only_with_a_hatch(self):
        self.assertIn("const BSH_ON = isTouch && REAL && HIT_ON && !/[?&]bshadow=0\\b/.test(location.search);", SRC)
        self.assertIn("BSH_ON ? [   // Round 274", SRC)   # a computer's canopy text is untouched
        self.assertIn("if (!BSH_ON || shader.fragmentShader.indexOf('uniform vec4 uBshBox') !== -1) return;", SRC)

    def test_the_reads_and_the_map(self):
        self.assertIn("bshFacadePatch(shader);   // Round 274", SRC)
        self.assertIn("    bshUpdate();\n    canopyMapUpdate();\n", SRC)
        self.assertIn("&& !BSH.dirty) return;\n    BSH.dirty = false;", SRC)
        self.assertIn("k * BSH_SHADE : 0);   // Round 274", SRC)
        self.assertIn("gl_FragColor = vec4(0.0, 0.0, texture2D(uT, vQ).r, 0.0);", SRC)   # blue only, under the trees' MAX blend


if __name__ == '__main__':
    unittest.main()
