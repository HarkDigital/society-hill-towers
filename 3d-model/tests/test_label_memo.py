"""Round 276 (Stage 5, Mike: "Yes, go ahead"): the street lettering's fit kept on the device. The page's wiring: the build's
own id from build.py, the key (build, device kind, tier, Graphics choice), the query allow-list, the read before 'Laying out
the ground', the sampled street index, the check that refits every LMEMO_SAMPLE-th name to the bit, the write on a launch
that fitted, the beacon fields and the privacy policy's sentence. The run itself (miss and write, hit at 13 ms with the same
PERF.streetLabels.hash, a tampered record caught and dropped, a fresh fit after it) is a four-load headless check in one
browser profile on both paths (devlog Round 276)."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
BUILD = (ROOT / 'build.py').read_text()


class LabelMemo(unittest.TestCase):
    def test_build_id(self):
        self.assertIn('const("BUILD_ID", json.dumps(_bid.hexdigest()[:16]))', BUILD)
        self.assertIn('for _blob in (three, app, rebuilds, *(js for _, js in DATA_PARTS)):', BUILD)
        # it goes in after every data part it hashes and before the parts are written out
        self.assertLess(BUILD.index('const("BUILD_ID"'), BUILD.index('data_total = sum('))

    def test_key_and_allow_list(self):
        self.assertIn("[BUILD_ID, isTouch ? 't' : 'd', TIER, GFX.pick || ''].join('|')", SRC)
        self.assertIn("/^(dev|dpr|gfx|cold|coldms|probe|probe4)(=|$)/", SRC)
        self.assertIn("!/[?&]memo=0\\b/.test(location.search)", SRC)

    def test_read_before_the_ground(self):
        b = SRC[SRC.index('  async function build() {'):]
        self.assertLess(b.index('await lmemoRead();'), b.index('for (const s of buildSteps)'))
        self.assertIn('initStreetSurfaces(LMEMO.hit ? LMEMO_SAMPLE : 1);', SRC)
        self.assertIn("if ((i/5) % sample) continue;", SRC)
        self.assertEqual(int(re.search(r'const LMEMO_SAMPLE = (\d+)', SRC).group(1)), 50)

    def test_check_and_write(self):
        self.assertIn('same = H.pos[o] === v[k][0] && H.pos[o + 1] === v[k][2] && H.pos[o + 2] === v[k][1];', SRC)
        self.assertIn("if (LMEMO.bad) { LMEMO.lm = 3; lmemoDrop(); }", SRC)
        self.assertIn("lmemoWrite({ k: LMEMO.key, n: NP, pos: P, uv: U, idx: I, first, stats: keep });", SRC)
        self.assertIn("lf: L.fit, lm: M.lm, lq: M.lq }", SRC)

    def test_privacy_policy_names_it(self):
        self.assertIn("a copy of the street names' layout the app worked out the last time it started", (ROOT / 'privacy.html').read_text())


if __name__ == '__main__':
    unittest.main()
