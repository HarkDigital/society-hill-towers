"""Stage 2 of the Nov 10 plan, the first view by day (Round 247): three looks for Mike's first side by side of the train,
on by default since his pick (Nov 13: "The shader updates look great, wrap that into the next deploy").

- ?roofpick=held by default, photo or 0 (AERIAL-1): a flat cap whose colour is the orthophoto's sample carries a mark in its floor byte
  (1, or 2 after the far ring's lift) and takes its kind by that sample; unsampled caps are dealt at the photographs'
  shares; held scales each tier's kinds back to today's mean. Shader text either way, uRoofPick.x the switch.
- ?farforms=0 refuses (REALDATA-4 step A): pack_city.py packs a merged strip's measured form in codes 5 to 7, read as 4, 1 and 2
  and as 0 (the lottery) under ?farforms=0; city.b64 changed in roof words only.
- ?orbitsh=0 refuses (AERIAL-2 step 1): the far map's switch at 360 m, so the entry orbit is in the near map."""
import math
from pathlib import Path
import unittest

from _common import decode_b64

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
PACK = (ROOT / 'pack_city.py').read_text()


def roof_inv(t):
    return min(1.0, (max(t, 4) / 31.5) ** 2.364 / 255)


class RoofPick(unittest.TestCase):
    def test_on_by_default_since_mikes_pick(self):
        self.assertIn("const ROOF_PICK = (/[?&]roofpick=(photo|held|0)\\b/.exec(location.search) || [])[1] || 'held';", SRC)
        self.assertIn("const ROOF_PICK_ON = REAL && ROOF_PICK !== '0';", SRC)
        self.assertIn("uRoofPick: { value: new THREE.Vector4(ROOF_PICK_ON ? 1 : 0, 0.0754, 0.211, 0.367) },", SRC)
        self.assertIn("const ROOF_HOLD = ROOF_PICK === 'held' ? [0.739, 0.925] : [1, 1];", SRC)

    def test_thresholds_are_the_palettes_bins(self):
        for v, t in zip((0.0754, 0.211, 0.367), (110, 170, 215)):
            self.assertLess(abs(v - roof_inv(t)), 1e-3)

    def test_the_three_writers_mark_a_sample(self):
        self.assertIn('const ROOF_SAMPLED = 0.1, ROOF_SAMPLED_LIFT = 0.2;', SRC)
        self.assertIn('style: 3, flh: ROOF_SAMPLED });', SRC)   # the core's overlay cap
        self.assertIn("fh, capC, mh === 0, capC ? ROOF_SAMPLED : 0);", SRC)   # the outer districts
        self.assertIn("fh, capC, mh === 0, capC ? (h <= 45 && t <= 6 ? ROOF_SAMPLED_LIFT : ROOF_SAMPLED) : 0);", SRC)   # the far ring
        # the lift the far mark stands for is farCapLight's, the one the shader takes back off
        self.assertIn('FAR_CAP_LIGHT = 1.23;', SRC)
        self.assertIn('(vFloorH > 1.5 && vFloorH < 2.5 ? 0.813 : 1.0)', SRC)
        self.assertAlmostEqual(1 / 1.23, 0.813, places=3)

    def test_the_brightness_is_read_before_the_mottle(self):
        i = SRC.index("'    float rL0 = dot(diffuseColor.rgb, vec3(0.2126, 0.7152, 0.0722)) / uFabG.y")
        j = SRC.index("'    diffuseColor.rgb *= 1.0 + rdet * 0.22 * (rn - 0.5);',")
        k = SRC.index("'      if (uRoofPick.x > 0.5) {',")
        self.assertLess(i, j)
        self.assertLess(j, k)
        # a floor height is 22 decimetres or more, so only the two marks pass the pick's gate
        self.assertIn("if (vFloorH > 0.5 && vFloorH < 2.5) {", SRC)

    def test_unsampled_shares_are_the_photographs(self):
        line = [l for l in SRC.splitlines() if "else rk = rsd < 0.15 ? 0.0 : (rsd < 0.41 ? 3.0 : (rsd < 0.79 ? 1.0 : 2.0));" in l]
        self.assertEqual(len(line), 1)
        # the old lottery stays, so the default draws what it did
        self.assertIn("'      float rk = rsd < 0.36 ? 1.0 : (rsd < 0.66 ? 0.0 : (rsd < 0.86 ? 2.0 : 3.0));',", SRC)


class FarForms(unittest.TestCase):
    def test_the_page_reads_them_unless_refused(self):
        self.assertIn("const FAR_FORMS = !/[?&]farforms=0\\b/.test(location.search);", SRC)
        self.assertIn('const FAR_FORM_OF = [0, 0, 0, 0, 0, 4, 1, 2];', SRC)
        a = SRC.index('      if (rb[1] >= 5) rb[1] = FAR_FORMS ? FAR_FORM_OF[rb[1]] : 0;')
        # remapped before anything reads the form, colStats' keys included
        self.assertLess(a, SRC.index("colStat(tk + 'Form' + rb[1]);"))
        self.assertLess(a, SRC.index("const rplan = mh > 0 ? null : roofPlan(poly, Math.abs(signedArea(poly)), h, t, rb[1], rb[2]"))

    def test_the_packer_uses_codes_no_building_has(self):
        self.assertIn('STRIP_SHARE, STRIP_RIDGE = 0.6, math.radians(20)', PACK)
        self.assertIn("rf_ = mine[0][3] if len(mine) == 1 else (strip_form(g, mine) if STRIP_FORMS else (0, 0.0))", PACK)
        self.assertIn('TAGFORM = {0: 4, 1: 1, 2: 2, 3: 3}', PACK)   # a single building's forms stay 1 to 4

    def test_city_blob_carries_strip_forms(self):
        hdr, b = decode_b64('city.b64')
        i, forms = 0, {}
        for _ in range(hdr[1]):
            n = b[i]
            rw = b[i + 5] & 0xFFFF
            if rw != 0xFFFF:
                f = (rw >> 9) & 7
                forms[f] = forms.get(f, 0) + 1
            i += 6 + 2 * n
        self.assertGreater(forms.get(5, 0), 1000)
        self.assertGreater(forms.get(6, 0) + forms.get(7, 0), 0)


class OrbitShadows(unittest.TestCase):
    def test_the_switch_at_360_unless_refused(self):
        self.assertIn('wideH: 250,', SRC)
        self.assertIn("if (!/[?&]orbitsh=0\\b/.test(location.search)) FARSH.wideH = 360;", SRC)
        # the orbit flies at 318.5 m: the flag's switch, less its 30 m hysteresis, stays over it
        self.assertGreater(360 - 30, 700 * math.cos(1.22) + 78 - 1)


if __name__ == '__main__':
    unittest.main()
