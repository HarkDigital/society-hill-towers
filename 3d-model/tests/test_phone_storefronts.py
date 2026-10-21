"""Round 219: every phone draws the generated storefronts, whatever its tier.

Mike, from the app, after Round 218 put the lamp posts back on every phone tier: "I am still not seeing the store fronts on
mobile. We need to load those similarly." Round 189's shopfronts (STOREFRONT_ART: the photographic panels, the names on
their boards and the painted shop floors of the facade shader's style 5) were off at tier 2 (SF_ART_ON, SF_SIGNS and
SF_PARTA each carried !TIER2), and a phone reaches tier 2 by dying: his app was there from 20:07 on Oct 20, so it dressed
the old navy boxes. Now nothing in the storefronts' switches, art loading or step reads a tier, the Graphics choice or the
pace; the step waits SF_ART_WAIT (30 s, 10 before) for the art rather than fall back to the boxes; and the ready beacon
carries what the step did (`sf`).
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


def flag(name):
    return re.search(r'const ' + name + r' = ([^;]+);', APP).group(1)


class PhoneStorefronts(unittest.TestCase):
    def test_the_storefronts_carry_no_tier_gate(self):
        blocks = {
            'the switches': cut('  const SF_ART_ON = ', '  const SF = {'),
            'the painted shop floors': cut('  const SF_PARTA = ', '  const SF_AW = '),
            'the art loading': cut('  function sfArtPrefetch(', '  function sfBitmapTex('),
            'the step': cut("  step('Dressing the storefronts'", '    let nearN = 0, baseN = 0;'),
        }
        for name, b in blocks.items():
            self.assertEqual(GATES.findall(b), [], name)
        self.assertIn('if (SF_ART_ON) { if (isTouch) sfArtPrefetch(); else sfArtLoad(); }', APP)

    def test_the_step_waits_for_the_art(self):
        self.assertIn('const SF_ART_WAIT = 30000;', APP)
        self.assertIn('late = setTimeout(() => r(null), SF_ART_WAIT); })]);', cut("  step('Dressing the storefronts'", '    let nearN = 0, baseN = 0;'))
        self.assertIn("beacon('ready', { ms: PERF.ready, fail: failures, sf: SF.state });", APP)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_on_for_every_tier_and_pick(self):
        art, signs, parta = flag('SF_ART_ON'), flag('SF_SIGNS'), flag('SF_PARTA')
        js = ('const location = { search: "" }, STOREFRONT_ART = { cells: [1], gen: [1], w: 4096, h: 2048 }, renderer = { capabilities: { isWebGL2: true } };\n'
              'const out = []; for (const isTouch of [true, false]) for (const TIER of [0, 1, 2]) for (const pick of ["auto", "smoother", "sharper"]) {\n'
              '  const LITE = TIER >= 1, TIER2 = TIER >= 2, REAL = true, GFX = { pick };\n'
              '  const SF_ART_ON = (' + art + '); const SF_SIGNS = (' + signs + '); const SF_PARTA = (' + parta + ');\n'
              '  out.push([isTouch, TIER, pick, SF_ART_ON, SF_SIGNS, SF_PARTA]); }\n'
              'console.log(JSON.stringify(out));')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        for touch, tier, pick, a, s, p in json.loads(r.stdout):
            self.assertTrue(a and s and p, (touch, tier, pick, a, s, p))

    def test_the_escape_hatches_stand(self):
        self.assertIn('!/[?&]sfart=0\\b/.test(location.search)', flag('SF_ART_ON'))
        self.assertIn('!/[?&]signs=0\\b/.test(location.search)', flag('SF_SIGNS'))
        self.assertIn('REAL &&', flag('SF_ART_ON'))


if __name__ == '__main__':
    unittest.main()
