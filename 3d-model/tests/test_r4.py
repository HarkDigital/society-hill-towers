"""The realism round two, R4: sixteen flat-roof surfaces in place of four. Each of Round 185's four kinds (tar, silver,
white, gravel) keeps its quadrant of the 2048 atlas and holds four photographed variants in its own 2 by 2 (variant 0 the
Round 185 picture, then a patched, a ponded and a seamed or drained one), every variant baked to its kind's own linear
mean, so a far roof (its kind's mean) is exactly what it was and the manifest's four means are Round 185's. A variant is
padded with its own wrapped edge, 64 px of its 512 on the quadrant's outside and 16 px toward its kind's other variants;
the shader holds a roof's footprint inside the 64 px pad and takes the texel to the mean as it is held. ?roofs16=0 deals
only variant 0."""
from pathlib import Path
import json
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Round 185's four means, which the far roofs (and the approved far aerial) are made of
MEANS_185 = [[0.08628, 0.08384, 0.08522], [0.45091, 0.46143, 0.4841], [0.71181, 0.69569, 0.66379], [0.32169, 0.31404, 0.28398]]


def to_lin(a):
    import numpy as np
    a = np.clip(a, 0, 255) / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def cell_box(k, v, ext, inn, size):
    """The inner box of kind k's variant v in image pixels (x0, y0, x1, y1, row 0 at the top), from the shader's own uv
    arithmetic: rUV = Q(k) * 0.5 + 0.5 * (ext + V(v) * (c + 2 inn) + t * c) for t in [0, 1], with uv's y up."""
    c = 0.5 - ext - inn
    qx, qy = (k % 2) * 0.5, (1 - k // 2) * 0.5
    vx, vy = v % 2, 1 - v // 2
    u0, v0 = qx + 0.5 * (ext + vx * (c + 2 * inn)), qy + 0.5 * (ext + vy * (c + 2 * inn))
    u1, v1 = u0 + 0.5 * c, v0 + 0.5 * c
    return round(u0 * size), round((1 - v1) * size), round(u1 * size), round((1 - v0) * size)


class Roofs16(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        cls.d = json.loads((ROOT / 'ground_art.json').read_text())

    def test_the_flag(self):
        self.assertIn("const ROOFS16 = REAL && !/[?&]roofs16=0\\b/.test(location.search);", self.s)
        self.assertIn("""ROOFS16 ? "      float rv = min(floor(fract(sin(vBase * 127.1 + vTint * 311.7) * 43758.5453) * 4.0), 3.0);" : "      float rv = 0.0;",""", self.s)

    def test_the_readers(self):
        s = self.s
        # the facade's roof branch: the kind's quadrant, then the variant's cell in it, the footprint held in the outside pad
        self.assertIn("'      vec2 rUV = vec2(mod(rk, 2.0), 1.0 - floor(rk / 2.0)) * 0.5 + 0.5 * (uRoofPad.x + vec2(mod(rv, 2.0), 1.0 - floor(rv / 2.0)) * (rC + 2.0 * uRoofPad.y) + fract(rG) * rC);',", s)
        self.assertIn("'      float rGl = max(length(rGx), length(rGy)) / (0.5 * uRoofPad.x), rHold = 1.0 / max(rGl, 1.0);',", s)
        self.assertIn("'      rT = mix(rT, rMean, smoothstep(1.0, 2.0, rGl));',", s)
        # the four kind means suffice (WebGL 1 indexes a uniform array only by a constant): still four, still the ternary chain
        self.assertIn("'      vec3 rMean = rk < 0.5 ? uRoofMean[0] : (rk < 1.5 ? uRoofMean[1] : (rk < 2.5 ? uRoofMean[2] : uRoofMean[3]));',", s)
        self.assertNotIn('uRoofMean[16]', s)
        self.assertIn('uniform vec2 uRoofPad; uniform vec3 uRoofMean[4];', s)
        # City Hall's decks: the tar's first variant, the top left cell of the tar's quadrant
        self.assertIn("'  float rC = 0.5 - uRoofPad.x - uRoofPad.y, rSc = 0.5 * rC; vec2 rUV = vec2(0.0, 0.5) + 0.5 * (uRoofPad.x + vec2(0.0, rC + 2.0 * uRoofPad.y) + fract(rG) * rC);',", s)
        self.assertIn('uniform vec2 uChLate, uRoofPad;', s)
        self.assertNotIn('uRoofPad;', s.replace('uniform vec2 uChLate, uRoofPad;', '').replace('uniform vec2 uRoofPad;', ''))   # no float declaration left
        self.assertIn("uRoofPad: { value: new THREE.Vector2(0.0625, 0.015625) }", s)
        self.assertIn("if (Array.isArray(GROUND_ART.roofPad)) roofArtU.uRoofPad.value.set(GROUND_ART.roofPad[0], GROUND_ART.roofPad[1]);", s)

    def test_the_manifest(self):
        d = self.d
        self.assertEqual(d['roofKinds'], ['tar', 'silver', 'white', 'gravel'])   # tar at the top left, where City Hall reads it
        self.assertEqual(d['roofMean'], MEANS_185)
        self.assertEqual(d['roofPad'], [64 / 1024, 16 / 1024])
        b = (ROOT / 'bake_ground_art.py').read_text()
        self.assertIn('ROOF_VARS, ROOF_EXT, ROOF_INT = 4, 64, 16', b)
        # Round 185's picture keeps the plain half roll (its look unchanged), the variants roll where the band is quiet
        self.assertIn('quiet=v > 0), means[k])', b)
        f = (ROOT / 'fetch_ground_art.py').read_text()
        for k in ('tar', 'silver', 'white', 'gravel'):
            for v in (1, 2, 3):
                self.assertIn("('roof_%s_%d', " % (k, v), f)

    def test_the_atlas(self):
        """Every cell where the shader reads it: its own mean at its kind's, the box's edge the cell's own wrapped edge."""
        import numpy as np
        from PIL import Image
        ext, inn = self.d['roofPad']
        for key, size in (('roofs', 2048), ('roofsHalf', 1024)):
            a = np.asarray(Image.open(ROOT / self.d[key]).convert('RGB'), np.float32)
            self.assertEqual(a.shape[:2], (size, size))
            L = to_lin(a)
            for k in range(4):
                m = np.asarray(MEANS_185[k])
                dev0 = None
                for v in range(4):
                    x0, y0, x1, y1 = cell_box(k, v, ext, inn, size)
                    self.assertEqual(x1 - x0, 432 * size // 2048)
                    dev = np.abs(L[y0:y1, x0:x1].reshape(-1, 3).mean(0) / m - 1)
                    # every variant holds its kind's mean as Round 185's own picture does (the 8 bits, the WebP and, at the
                    # half, a resize in sRGB that takes a few per cent off the gravel's stones): the far roof is the mean
                    if v == 0:
                        dev0 = dev
                        self.assertTrue(np.all(dev < (0.025 if size == 2048 else 0.06)), (key, k, dev.tolist()))
                    else:
                        self.assertTrue(np.all(dev < dev0 + (0.02 if size == 2048 else 0.045)), (key, k, v, dev.tolist(), dev0.tolist()))
                    if size == 2048:
                        # the 16 px just outside the box's left edge repeat the box's own last 16 columns (the wrap)
                        w = 16
                        out_l, in_r = a[y0:y1, x0 - w:x0], a[y0:y1, x1 - w:x1]
                        self.assertLess(np.abs(out_l - in_r).mean(), 4.0, (k, v))
                        out_t, in_b = a[y0 - w:y0, x0:x1], a[y1 - w:y1, x0:x1]
                        self.assertLess(np.abs(out_t - in_b).mean(), 4.0, (k, v))
            # the quadrant's outside pad is 64 px wide (the hold's reach)
            x0, y0, x1, y1 = cell_box(0, 0, ext, inn, size)
            self.assertEqual((x0, y0), (64 * size // 2048, 64 * size // 2048))

    def test_the_hold_under_node(self):
        """The hold, cut out as arithmetic and run: the 8 m kinds keep their texture to rfw 1.19 m a pixel (the fade has all
        but taken it by then), the gravel's 2.8 m tile goes to its mean between 0.41 and 0.83 m."""
        js = r"""
const pad = 0.0625, c = 0.5 - pad - 0.015625, sc = 0.5 * c;
const gl = (rfw, tile) => (rfw / tile) * sc / (0.5 * pad);   // the footprint in uv over the outside pad in uv
const ss = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const out = {};
for (const [name, tile] of [['eight', 8], ['gravel', 8 * 0.35]]) {
  let one = 0, two = 0;
  for (let r = 0.01; r < 4; r += 0.01) { const g = gl(r, tile); if (!one && g >= 1) one = r; if (!two && g >= 2) two = r; }
  out[name] = [+one.toFixed(2), +two.toFixed(2), +(1 - ss(0.25, 1.4, one)).toFixed(3)];
}
console.log(JSON.stringify(out));
"""
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertAlmostEqual(o['eight'][0], 1.19, delta=0.02)
        self.assertLess(o['eight'][2], 0.1)   # the fade's own weight where the hold begins on the 8 m kinds
        self.assertAlmostEqual(o['gravel'][0], 0.42, delta=0.02)
        self.assertAlmostEqual(o['gravel'][1], 0.83, delta=0.02)

    def test_the_art_files(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('ground_art.json', b)
        for key in ('roofs', 'roofsHalf'):
            self.assertTrue(re.fullmatch(r'art/ground/roofs(-half)?\.[0-9a-f]{10}\.webp', self.d[key]), self.d[key])
            self.assertTrue((ROOT / self.d[key]).exists())


if __name__ == '__main__':
    unittest.main()
