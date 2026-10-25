"""The realism pass two, the sky (Round 223): R5's cirrus from the high cloud Open-Meteo reports (WX.high, read nowhere
before), drawn on the dome and copied into the sky probe, with no light touched (Round 88). The warmer low haze built with it
(R10's D3 part) was dropped at Mike's call after the side by side ("Ship the cheap round with the haze change dropped"): the
air, apColor and its twin apColorC are as they were, so the glass's calibration stands.

Run under Node: applyWx and the weather's targets cut from app.js (the cirrus preset, the high cloud kept out of the deck, a
preset without the layers clearing it, the pin). The rest is text: the flag, the probe's copy, the air untouched."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text(encoding='utf-8')


def cut(src, start, end):
    i = src.index(start)
    return src[i:src.index(end, i)]


def run_node(tc, script):
    if not shutil.which('node'):
        tc.skipTest('Node.js unavailable')
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
    tc.assertEqual(r.returncode, 0, r.stderr)
    return json.loads(r.stdout)


class TestSkyFlags(unittest.TestCase):
    def test_flags(self):
        self.assertIn(r"const CIRRUS = REAL && !/[?&]cirrus=0\b/.test(location.search);", SRC)
        self.assertNotIn('HAZE2', SRC)   # the haze was dropped (Round 223)
        self.assertIn("(CIRRUS ? [", SRC)   # the dome's cirrus block is built only under the flag (?real=0 too)

    def test_probe_and_twin(self):
        env = cut(SRC, '  function refreshEnv() {', '  refreshEnv();')
        self.assertIn('envSky.material.uniforms.uCirrus.value.copy(skyMat.uniforms.uCirrus.value);', env)
        # the air the glass is calibrated under: apColorC and apColor's sun term exactly as before the round
        city = cut(SRC, '  const CITYENV_GLSL_F = `', '  // the proxy\'s geometry')
        self.assertIn('vec3 apColorC(vec3 dir) {', city)
        self.assertIn('return mix(c, fogAPSunC, (0.24 * exp(-190.0 * q) + 0.07 * exp(-18.0 * q) + 0.10 * m8 * m4 + 0.10 * m8 + 0.05 * m2) * 1.7857);', city)
        self.assertIn(r"'\t\tc = mix( c, fogAPSunC, ( 0.24 * exp( - 190.0 * q ) + 0.07 * exp( - 18.0 * q ) + 0.10 * m8 * m4 + 0.10 * m8 + 0.05 * m2 ) * 1.7857 );',", SRC)
        for gone in ('fogAPWarm', 'uHazeW', 'apWarmK', 'AP_LOBES', 'haze2'):
            self.assertNotIn(gone, SRC)

    def test_no_light_change(self):
        # Round 88: the light follows the deck only (sunDeckK is the deck's share); the high cloud reaches the dome alone
        self.assertIn('const sunDeckK = REAL ? 1 - 0.80 * smooth(0.55, 1.0, WX.cover) - 0.16 * smooth(0.75, 1.0, WX.cover) : deckK;', SRC)
        light = cut(SRC, '  function applyLighting() {', '  // --- time panel')
        for line in light.splitlines():
            if 'intensity' in line:
                self.assertNotIn('irrus', line)
        n, off = 0, 0
        for line in SRC.splitlines(keepends=True):   # recorded in applyWx, read by the targets and the probe only (code, not comments)
            if 'WX.high' in line.split('//')[0]:
                at = off + line.index('WX.high')
                ctx = SRC[SRC.rfind('function ', 0, at):at]
                self.assertTrue(ctx.startswith(('function applyWx', 'function wxSetTargets', 'function cirrusProbe')), ctx[:60])
                n += 1
            off += len(line)
        self.assertGreaterEqual(n, 4)


HARNESS = r"""
const out = {};
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
// applyWx and the weather's targets, cut from app.js, over stubs
const WX = { cover: 0.22, high: undefined, nwsCover: 0, nwsT: 0, windX: 0, windZ: 0 };
const waterU = { uWAmp: { value: 0 }, uWDir: { value: { set() {} } } };
const wxWind = { set() {} };
const mkWx = new Function('WX', 'clamp', 'waterU', 'wxWind', 'refreshTimeUI', 'LTN', 'AQI',
  'let lastEnvEl = 0;\n' + __APPLY__ + '\n' + __PRESETS__ + '\n' + __TARGETS__ + '\nreturn { applyWx, WX_PRESETS, WXFX, wxSetTargets };');
const S = mkWx(WX, clamp, waterU, wxWind, () => {}, { live: false }, { ok: false });
S.applyWx({ current: S.WX_PRESETS.cirrus });
out.cirrus = { high: WX.high, cover: WX.cover, t: S.WXFX.tCirrus, k: S.WXFX.cirrus };
S.applyWx({ current: { cloud_cover: 60, cloud_cover_low: 4, cloud_cover_mid: 0, cloud_cover_high: 62, weather_code: 2 } });
out.evening = { high: WX.high, cover: WX.cover, t: S.WXFX.tCirrus };
S.WXFX.cirrusPin = 0.25; S.wxSetTargets();
out.pinned = S.WXFX.tCirrus;
S.WXFX.cirrusPin = null;
S.applyWx({ current: S.WX_PRESETS.clear });
out.clear = { high: WX.high, t: S.WXFX.tCirrus };
console.log(JSON.stringify(out));
"""


class TestSkyNode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apply_ = cut(SRC, '  function applyWx(js) {', '  const wxCanFetch')
        presets = cut(SRC, '  const WX_PRESETS = {', "  const wxForced")
        targets = cut(SRC, '  const WXFX = {', '  // ---- weather on surfaces')
        script = (HARNESS.replace('__APPLY__', json.dumps(apply_)).replace('__PRESETS__', json.dumps(presets)).replace('__TARGETS__', json.dumps(targets))
)
        cls.script = script

    def test_run(self):
        o = run_node(self, self.script)
        # ?wx=cirrus: a clear deck under 60 per cent high cloud, landing at once on the first report
        self.assertAlmostEqual(o['cirrus']['high'], 0.6)
        self.assertEqual(o['cirrus']['cover'], 0)
        self.assertAlmostEqual(o['cirrus']['k'], 0.6)
        # Round 88's evening: 62 high, 4 low, the deck 0.04, the cirrus 0.62
        self.assertAlmostEqual(o['evening']['high'], 0.62)
        self.assertAlmostEqual(o['evening']['cover'], 0.04)
        self.assertAlmostEqual(o['evening']['t'], 0.62)
        self.assertAlmostEqual(o['pinned'], 0.25)
        self.assertEqual(o['clear']['high'], 0)
        self.assertEqual(o['clear']['t'], 0)


if __name__ == '__main__':
    unittest.main()
