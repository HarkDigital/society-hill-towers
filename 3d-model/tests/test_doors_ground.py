"""Every house has a door, and the ground is the generated lawn (Oct 12, Mike: "much of the app is still showing the old
style where buildings have no doors and all look alike", then "If you could also update the grass/ground textures").

Round 180: the facade shader drew a door every third bay on two styles only, and a rowhouse wall is two or three bays
wide, so most houses had none. A wall of up to three bays now takes its door in an end bay, chosen per wall, and every
row style takes one. Round 183: GROUND_ART's lawn and verge, made to tile, take the painted meadow's place, toned to its
mean."""
from pathlib import Path
import base64
import io
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Doors(unittest.TestCase):
    def test_every_house_wall_takes_a_door(self):
        s = (ROOT / 'app.js').read_text()
        self.assertIn("'      float doorCol = nbD <= 3.0 ? 1.0 - step(0.5, abs(cell.x - doorBay)) : step(2.5, mod(cell.x, 3.0));',", s)
        self.assertIn("float(st == 0 || st == 8 || st == 9 || st == 10 || st == 11) * inWall * det * detU;',", s)
        self.assertNotIn("float(st == 0 || st == 8) * brickish * inWall * det * detU;", s)


class Ground(unittest.TestCase):
    def test_the_textures(self):
        d = json.loads((ROOT / 'ground_art.json').read_text())
        # Round 184: the streets' three beside the lawn and verge, each a file under art/ground/ with a phone's half
        kinds = ('lawn', 'meadow', 'asphalt', 'concrete', 'bricks', 'yard')   # Round 185: the yards
        self.assertEqual(set(d), set(kinds) | {k + 'Half' for k in kinds} | {'m', 'roofs', 'roofsHalf', 'roofKinds', 'roofMean', 'roofPad', 'veg'})
        d.pop('veg')   # the realism pass's own set (tests/test_realism_ground_veg.py)
        self.assertEqual(d.pop('m'), {'asphalt': 6.0, 'concrete': 1.5, 'bricks': 1.625, 'yard': 10.0, 'roof': 8.0})   # a tile's metres
        # Round 185: the flat roofs' 2 by 2 atlas, its kinds in the shader's order and their linear means (tar darkest, white lightest)
        self.assertEqual(d.pop('roofKinds'), ['tar', 'silver', 'white', 'gravel'])
        means = d.pop('roofMean'); lum = [0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2] for m in means]
        self.assertLess(lum[0], 0.15); self.assertGreater(lum[2], lum[1]); self.assertEqual(d.pop('roofPad'), 0.03125)
        from PIL import Image as _I
        self.assertEqual(_I.open(ROOT / d.pop('roofs')).size, (2048, 2048)); self.assertEqual(_I.open(ROOT / d.pop('roofsHalf')).size, (1024, 1024))
        from PIL import Image
        import numpy as np
        for k, path in d.items():
            self.assertTrue(re.fullmatch(r'art/ground/[a-z]+(-half)?\.[0-9a-f]{10}\.webp', path), path)
            a = np.asarray(Image.open(ROOT / path).convert('RGB'), np.float32)
            self.assertEqual(a.shape[:2], (512, 512) if k.endswith('Half') else (1024, 1024))
            # it tiles: the step across each edge is no larger than the image's own pixel to pixel steps
            inner = np.abs(np.diff(a, axis=1)).mean()
            self.assertLess(np.abs(a[:, 0] - a[:, -1]).mean(), inner * 1.6, k)
            self.assertLess(np.abs(a[0] - a[-1]).mean(), np.abs(np.diff(a, axis=0)).mean() * 1.6, k)

    def test_wiring(self):
        s = (ROOT / 'app.js').read_text()
        self.assertIn('loadGroundArt();   // Round 183', s)
        self.assertIn("'if (uGrassArt > 0.5) { vec3 gB = mix(texture2D(uGrass2, gUv1).rgb, texture2D(uGrass2, gUv2).rgb, 0.5) * uGrassTone2;',", s)
        self.assertIn("/[?&]ground=painted\\b/.test(location.search)", s)
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("GROUND_ART", text_of("ground_art.json", "null"))', b)


if __name__ == '__main__':
    unittest.main()
