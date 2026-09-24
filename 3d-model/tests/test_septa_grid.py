"""Round 153: the SEPTA road-snap grid as typed arrays (the phones' memory) answers exactly as the Map of arrays did.

The Map kept a copy of every segment in every 36 m cell of its bounding box, about 717,000 entries and 65 to 75 MB of heap
on a phone. The page now appends the segments to one Float64Array and freezes a dense cell index on the first read. This
runs the page's septaRoadAdd / septaRoadFreeze / septaSnapRoad under Node against the old Map implementation (kept here
as the reference) over random road networks, including a write after a freeze, and requires identical answers."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

OLD = r'''
const oldGrid = new Map();
function oldAdd(ax, az, bx, bz) {
  const x0 = Math.floor(Math.min(ax, bx) / 36), x1 = Math.floor(Math.max(ax, bx) / 36);
  const z0 = Math.floor(Math.min(az, bz) / 36), z1 = Math.floor(Math.max(az, bz) / 36);
  for (let gx = x0; gx <= x1; gx++) for (let gz = z0; gz <= z1; gz++) { const key = gx + ':' + gz; let a = oldGrid.get(key); if (!a) { a = []; oldGrid.set(key, a); } a.push(ax, az, bx, bz); }
}
function oldSnap(x, z, maxD) {
  const gx = Math.floor(x / 36), gz = Math.floor(z / 36);
  let bd = maxD * maxD, bx2 = 0, bz2 = 0, bdx = 1, bdz = 0, found = false;
  for (let cx2 = gx - 1; cx2 <= gx + 1; cx2++) for (let cz2 = gz - 1; cz2 <= gz + 1; cz2++) {
    const a = oldGrid.get(cx2 + ':' + cz2); if (!a) continue;
    for (let i = 0; i < a.length; i += 4) {
      const ax = a[i], az = a[i + 1], dx = a[i + 2] - ax, dz = a[i + 3] - az, L2 = dx * dx + dz * dz || 1e-9;
      let tt = ((x - ax) * dx + (z - az) * dz) / L2; tt = tt < 0 ? 0 : tt > 1 ? 1 : tt;
      const ex = ax + dx * tt - x, ez = az + dz * tt - z, d2 = ex * ex + ez * ez;
      if (d2 < bd) { bd = d2; bx2 = ax + dx * tt; bz2 = az + dz * tt; bdx = dx; bdz = dz; found = true; }
    }
  }
  if (!found) return null;
  const L3 = Math.hypot(bdx, bdz) || 1; return [bx2, bz2, bdx / L3, bdz / L3];
}
'''


class SeptaGrid(unittest.TestCase):
    def test_identical_answers(self):
        if not shutil.which('node'):
            self.skipTest('Node.js unavailable')
        s = (ROOT / 'app.js').read_text()
        block = s[s.index('  const SEPTA_RG_CELL = 36;'):s.index('  function septaMerge(parts) {')]
        script = OLD + block + r'''
let seed = 7; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
const add = (ax, az, bx, bz) => { oldAdd(ax, az, bx, bz); septaRoadAdd(ax, az, bx, bz); };
for (let k = 0; k < 4000; k++) {   // a street grid with long diagonals and short stubs, some far from the origin
  const x = (rnd() - 0.5) * 9000, z = (rnd() - 0.5) * 9000, L = rnd() < 0.1 ? 400 * rnd() : 60 * rnd(), a = rnd() * 6.283;
  add(x, z, x + Math.cos(a) * L, z + Math.sin(a) * L);
}
let bad = 0, hits = 0;
const check = (n) => { for (let q = 0; q < n; q++) { const x = (rnd() - 0.5) * 9400, z = (rnd() - 0.5) * 9400, d = 5 + rnd() * 40, A = oldSnap(x, z, d), B = septaSnapRoad(x, z, d); if (A) hits++; if (JSON.stringify(A) !== JSON.stringify(B)) bad++; } };
check(6000);
add(12000, 12000, 12050, 12040);   // a write after the freeze, outside the old extent: the next read refreezes
check(1000);
const far = JSON.stringify(septaSnapRoad(12020, 12020, 30)) === JSON.stringify(oldSnap(12020, 12020, 30));
console.log(JSON.stringify({ bad, hits, far, freezes: SRG.freezes, segs: SRG.n }));'''
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o['bad'], 0, o)
        self.assertGreater(o['hits'], 1000, o)   # the queries actually find roads
        self.assertTrue(o['far'], o)
        self.assertEqual(o['freezes'], 2, o)     # one freeze, then one more after the late write
        self.assertEqual(o['segs'], 4001)


if __name__ == '__main__':
    unittest.main()
