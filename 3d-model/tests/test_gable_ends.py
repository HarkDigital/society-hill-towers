"""Every gable end faces out of its house (Oct 12, Mike over Spruce Street: "The roofs look broken. they are missing a
piece on the side so you cant see into them").

quadGable's end triangles were wound with the horizontal normal read the wrong way round, (Bz - Az, -(Bx - Ax)) where
(B - A) x (R - A) gives (-(Bz - Az), Bx - Ax), so every gable end in the city (the core's, the outer districts' and the
far ring's pitched rows through raisePitched, the researched gables) faced into its house and was culled. The test runs
the page's own quadGable under node on quads given in all four rotations and both windings."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def fn_source(src, name):
    a = src.index('  function ' + name + '(')
    return src[a:src.index('\n  }\n', a) + 4]


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class GableEnds(unittest.TestCase):
    def test_every_end_faces_out(self):
        src = (ROOT / 'app.js').read_text()
        js = fn_source(src, 'quadGable') + r'''
const THREE = { BufferGeometry: class { setAttribute(k, v) { this[k] = v; } computeVertexNormals() {} },
                BufferAttribute: class { constructor(a) { this.array = a; } } };
const out = [];
const base = [[0, 0], [10, 0], [10, 6], [0, 6]];
for (const rev of [false, true]) for (let rot = 0; rot < 4; rot++) {
  let q = base.slice(rot).concat(base.slice(0, rot)); if (rev) q = q.slice().reverse();
  for (const rad of [null, 0, Math.PI / 2]) {
    const g = quadGable(q, 3, 6, rad), p = g.ends.position.array;
    const cx = 5, cz = 3;
    for (let i = 0; i < p.length; i += 9) {
      const A = p.slice(i, i + 3), B = p.slice(i + 3, i + 6), R = p.slice(i + 6, i + 9);
      const u = [B[0] - A[0], B[1] - A[1], B[2] - A[2]], v = [R[0] - A[0], R[1] - A[1], R[2] - A[2]];
      const n = [u[1] * v[2] - u[2] * v[1], u[0] * v[1] - u[1] * v[0]];
      const m = [(A[0] + B[0]) / 2 - cx, (A[2] + B[2]) / 2 - cz];
      const nx = u[1] * v[2] - u[2] * v[1], nz = u[0] * v[1] - u[1] * v[0];
      out.push(Math.sign(nx * m[0] + nz * m[1]));
    }
  }
}
console.log(JSON.stringify(out));
'''
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        signs = json.loads(r.stdout)
        self.assertEqual(len(signs), 2 * 4 * 3 * 2)
        self.assertEqual(set(signs), {1}, 'a gable end faces into its house')


if __name__ == '__main__':
    unittest.main()
