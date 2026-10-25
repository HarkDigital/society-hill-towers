"""Round 224: the cobra head's light at the cobra head.

Mike, with a South Street night capture: "the lights do not align with the lamppost where they should". The realism pass
(Round 188, night#5) drew the cobra's luminaire as a flattened sphere 2.3 m out along the arm with its underside at 8.93 m
on the 9 m reference pole, while POLE_HEAD, which places the lit lens, the glow, the glare and the lamp's pool on the street,
kept the old box head's 1.5 m and 8.81 m: every cobra's light stood 0.8 m short of its head, half way along the arm. Now both
read one set of numbers (COBRA_HEAD), and this test holds the lens inside the luminaire's footprint and just under it.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.js').read_text()


class LampHead(unittest.TestCase):
    def test_one_set_of_numbers(self):
        self.assertIn('const POLE_HEAD = { arm: COBRA_HEAD.x, y: COBRA_HEAD.y - COBRA_HEAD.ry, lantern: 4.1 };', APP)
        self.assertIn('new THREE.SphereGeometry(1, 12, 6).scale(COBRA_HEAD.rx, COBRA_HEAD.ry, COBRA_HEAD.rz).translate(COBRA_HEAD.x, COBRA_HEAD.y, 0),', APP)
        self.assertNotIn('translate(2.3, 9.05, 0)', APP)
        # every placement of the light reads POLE_HEAD: the glow (headAt), the glare (poleReconcile), the lens, the wood head
        self.assertIn('pos[i * 3] = X[i] + Math.cos(r) * POLE_HEAD.arm; pos[i * 3 + 1] = GY[i] + POLE_HEAD.y * HM[i] / 9;', APP)
        self.assertIn("translate(POLE_HEAD.arm, POLE_HEAD.y - 0.005, 0), lensMat(4.0, 0.3), 'lamp-lenses');", APP)
        self.assertIn('[new THREE.BoxGeometry(0.56, 0.14, 0.25).translate(POLE_HEAD.arm, hY, 0), STEEL],', APP)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_the_lens_sits_under_the_head(self):
        cobra = re.search(r'const COBRA_HEAD = (\{[^}]*\});', APP).group(1)
        head = re.search(r'const POLE_HEAD = (\{[^}]*\});', APP).group(1)
        js = ('const COBRA_HEAD = ' + cobra + '; const POLE_HEAD = ' + head + ';\n'
              'const lx = POLE_HEAD.arm, ly = POLE_HEAD.y - 0.005, C = COBRA_HEAD;\n'
              'const inX = Math.abs(lx - C.x) <= C.rx * 0.5, under = ly <= C.y - C.ry && ly >= C.y - C.ry - 0.02;\n'
              'console.log(JSON.stringify({ lx, ly, inX, under, gap: +(C.y - C.ry - ly).toFixed(4) }));')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertTrue(o['inX'], o)     # the lens is under the luminaire, not half way along the arm
        self.assertTrue(o['under'], o)   # and just under its underside (5 mm), not inside it or a hand's width below


if __name__ == '__main__':
    unittest.main()
