"""Round 255 (Stage 4's probe, the Nov 10 plan's 3.4): two questions a phone answers on its beacons before Stage 4 builds
on them. ix (ready): does an IndexedDB record survive a relaunch. ax (perf): does an ASTC texture upload and sample right,
in linear and sRGB, 4x4 and 6x6. Touch only, ?probe4=0 refuses, nothing drawn changes, the record holds a time and nothing
else, and the privacy policy says so."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT.parent / '.claude' / 'skills' / 'philly3d-capture' / 'scripts' / 'beacons.py'


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class Probe4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_touch_only_and_refusable(self):
        self.assertIn("const PROBE4_ON = isTouch && !/[?&]probe4=0\\b/.test(location.search);", self.src)
        body = cut(self.src, '  function ixProbe() {', '\n  }\n')
        self.assertIn('if (!PROBE4_ON) return;', body)
        self.assertIn('if (PROBE4_ON) ixWrite();', self.src)
        start = cut(self.src, '  function astcProbeStart() {', '\n  }\n')
        self.assertIn('if (!PROBE4_ON) return;', start)
        # once a device: a kept answer is reported and the probe is not run again
        self.assertIn("if (kept) { PROBE4.ax = kept + '.1'; return; }", start)
        # only while still, never before 45 s, never after 170 s, never hidden
        self.assertIn('now - PACE.lastInput < PACE_IDLE_AFTER || now - PACE.moved < PACE_IDLE_AFTER || document.hidden', start)
        self.assertIn('now - t0 > 170000', start)
        self.assertIn('now - t0 < 45000', start)

    def test_the_record_is_a_time_and_nothing_else(self):
        body = cut(self.src, '  function ixWrite() {', '\n  }\n')
        self.assertIn("put({ t: now }, 'probe')", body)
        self.assertEqual(len(re.findall(r'\.put\(', body)), 1)

    def test_astc_probe_leaves_three_consistent(self):
        body = cut(self.src, '  function astcProbe() {', '\n  }\n')
        self.assertIn('renderer.resetState();', body)
        self.assertLess(body.index('gl.deleteTexture(tx)'), body.index('renderer.resetState()'))
        # the four formats: linear and sRGB, 4x4 and 6x6, and the reds a right decode reads
        self.assertIn('[[0x93b0, 4, 128], [0x93d0, 4, 55], [0x93b4, 6, 128], [0x93d4, 6, 55]]', body)
        # a void-extent block: 0x1FC in the low nine bits, the reserved bits set, no extent, then R 0.5, G 0, B 1, A 1
        self.assertIn('[0xfc, 0xfd, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x80, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff]', body)
        self.assertNotIn('KHR_parallel_shader_compile', body)

    def test_fields_ride_the_beacons_and_the_reader_names_them(self):
        facts = cut(self.src, '  function measFacts(st) {', '\n  }\n')
        self.assertIn('ix: f(() => PROBE4.ix)', facts)
        self.assertIn("{ const ax = f(() => PROBE4.ax); if (ax) o.ax = ax; }", facts)
        # outside the Round 229 measurement block, which never asks for an extension
        blk = cut(self.src, '  // ---- Round 229, measurement round two (Stage 1', '  // ---- reversed-Z depth (Round 192')
        self.assertNotIn('function astcProbe', blk)
        b = SKILL.read_text()
        ready2 = re.search(r'^READY2 = \(([^)]*)\)', b, re.M).group(1)
        run2 = re.search(r'^RUN2 = \(([^)]*)\)', b, re.M).group(1)
        self.assertIn("'ix'", ready2)
        self.assertIn("'ax'", run2)

    def test_privacy_says_so(self):
        t = (ROOT / 'privacy.html').read_text()
        self.assertIn('one small test record holding only the time it was saved', t)


if __name__ == '__main__':
    unittest.main()
