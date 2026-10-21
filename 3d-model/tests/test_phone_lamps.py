"""Round 218: every phone draws every lamp post, whatever its tier.

Mike, from the iOS app at night: "I again am not seeing lamp posts on mobile at night. Is that due to some light load? I
dont want that to happen if so." Round 205 had given a phone its 500 nearest poles within 300 m, but not at tier 2
(POLE_MESH_CAP 0), and tier 2 is where a phone goes after it dies: the load beacons showed his app at a sticky tier 1 since a
build death on Oct 16 and at tier 2 after a context loss in the build at 20:07 on Oct 20, and from then on every lamp was the
glow alone again. The lite tiers had no near pool map either (LAMPNEAR, 0.7 MB on a phone), so their pools were the far map's
7.8 m wash. Now the lamps are no tier's, Graphics choice's or pace's to drop: the cap, the radius, the inventory, the near
glow and the near map read only the device and the realistic look, and the step and the reconcile carry no tier gate.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.js').read_text()
GATES = re.compile(r'\b(TIER2?|LITE|LITE_R|tierAuto|GFX|PACE|GFX_PERF)\b')


def cut(start, end):
    a = APP.index(start)
    return APP[a:APP.index(end, a)]


class PhoneLamps(unittest.TestCase):
    def test_the_lamps_carry_no_tier_gate(self):
        blocks = {
            'constants': cut('  const LIGHTS = { on: true, ready: false };', '  let towerGlow = null'),
            'light maps': cut('  const LAMPMAP = {', '  const LAMP_NEAR_EVERY'),
            'the step': cut("  step('Lighting the streetlamps'", "  step('Fitting out the rooftops'"),
            'the reconcile and the near meshes': cut('  function poleReconcile(', '  function syncLightsBtn('),
            'the night switch': cut('  function updateLights(', '  const _v2lamp'),
            'the near map': cut('  function lampNearUpdate(', '\n  }\n'),
        }
        for name, b in blocks.items():
            self.assertEqual(GATES.findall(b), [], name)

    def test_every_phone_meshes_its_poles(self):
        self.assertIn('const POLE_MESH_CAP = isTouch ? 500 : 1600;', APP)
        self.assertIn('const POLE_MESH_R = isTouch ? 300 : 1000;', APP)
        self.assertIn('const LAMPNEAR = { on: REAL,', APP)
        step = cut("  step('Lighting the streetlamps'", "  step('Fitting out the rooftops'")
        self.assertIn('const keepInv = POLE_MESH_CAP > 0;', step)
        self.assertIn('if (POLE_MESH_CAP > 0) {', step)
        self.assertIn('const NEAR_GLOW = POLE_MESH_CAP > 0 && REAL && !POLE_AIM_BUILD;', step)
        self.assertIn('if (LAMPNEAR.on) lampNearUpdate();', APP)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_the_cap_is_positive_on_every_tier_and_pick(self):
        # the page's own lines, run for every device, tier and Graphics choice the boot block can produce
        cap = re.search(r'const POLE_MESH_CAP = ([^;]+);', APP).group(1)
        near = re.search(r'const LAMPNEAR = \{ on: ([^,]+),', APP).group(1)
        js = ('const out = []; for (const isTouch of [true, false]) for (const TIER of [0, 1, 2]) for (const pick of ["auto", "smoother", "sharper"]) '
              '{ const LITE = TIER >= 1, TIER2 = TIER >= 2, REAL = true, GFX = { pick }; out.push([isTouch, TIER, pick, (' + cap + '), (' + near + ')]); } '
              'console.log(JSON.stringify(out));')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        for touch, tier, pick, c, n in json.loads(r.stdout):
            self.assertEqual(c, 500 if touch else 1600, (touch, tier, pick))
            self.assertTrue(n, (touch, tier, pick))

    def test_a_probe_reports_them(self):
        self.assertIn('poles: () => ({ tier: TIER, cap: POLE_MESH_CAP, r: POLE_MESH_R, meshed: poleMesh ? poleMesh.count : 0,', APP)


if __name__ == '__main__':
    unittest.main()
