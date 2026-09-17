"""The air-quality block (Round 75) run for real under JavaScriptCore: the EPA index tables,
the six category names, the clear-air multiplier and smoke tint from PM2.5, and the reading
cleaner (nulls, the -999 sentinel, stale hours, the two-site rule). The block is cut from
app.js between its banners (AQI_PM25 to aqiFromRows) so a drift in the page is caught here.
Skips when osascript is unavailable (non-macOS hosts)."""
import json
import shutil
import subprocess
import tempfile
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_aqi
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

JXA = r'''function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
var smooth = function (a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
%(snippet)s
var now = 1789581600000 + 40 * 60000;   // forty minutes after the 18:00Z sample hour
var rows = [
  { site_name: 'LABP', pm25_ug_m3: 7.73, ozone_ppb: 56, sample_timestamp: 1789581600000 },
  { site_name: 'NEA', pm25_ug_m3: null, ozone_ppb: 52, sample_timestamp: 1789581600000 },
  { site_name: 'MON', pm25_ug_m3: 6.85, ozone_ppb: null, sample_timestamp: 1789581600000 },
  { site_name: 'NEW', pm25_ug_m3: -999, ozone_ppb: -999, sample_timestamp: 1789581600000 },
  { site_name: 'OLD', pm25_ug_m3: 80, ozone_ppb: 120, sample_timestamp: 1789581600000 - 13 * 3600000 },
  null
];
var one = [{ pm25_ug_m3: 12, ozone_ppb: null, sample_timestamp: 1789581600000 }];
var out = {
  pm: [aqiPiece(0, AQI_PM25), aqiPiece(9.0, AQI_PM25), aqiPiece(9.1, AQI_PM25), aqiPiece(35.4, AQI_PM25), aqiPiece(55.4, AQI_PM25), aqiPiece(125.4, AQI_PM25), aqiPiece(225.4, AQI_PM25), aqiPiece(400, AQI_PM25), aqiPiece(null, AQI_PM25), aqiPiece(-3, AQI_PM25)],
  o3: [aqiPiece(54, AQI_O3), aqiPiece(70, AQI_O3), aqiPiece(105, AQI_O3)],
  cats: [aqiCat(0), aqiCat(50), aqiCat(51), aqiCat(100), aqiCat(101), aqiCat(150), aqiCat(151), aqiCat(200), aqiCat(201), aqiCat(300), aqiCat(301), aqiCat(null)],
  k: [5, 22, 35, 55, 80, 125, 225, 400].map(function (p) { return hazeFor(p).k; }),
  tint: [5, 30, 75, 120, 300].map(function (p) { return hazeFor(p).tint; }),
  none: hazeFor(null),
  clean: aqiFromRows(rows, now),
  single: aqiFromRows(one, now),
  empty: aqiFromRows([], now),
  stale: aqiFromRows(rows, now + 13 * 3600000)
};
JSON.stringify(out);'''


def aqi_snippet(src):
    """The pure air-quality functions, cut from app.js by their first and last lines."""
    a = src.index('\n  const AQI_PM25 = ')
    b = src.index('\n  const AQI_PRESETS = ')
    return src[a:b]


class AqiRuntime(unittest.TestCase):
    def setUp(self):
        C.require(self, 'app.js')
        self.src = C.path('app.js').read_text(encoding='utf-8')

    def test_block_is_wired(self):
        """The fog distances scale by WXFX.haze and the time panel prints the air quality line."""
        self.assertIn('scene.fog.far = fogBase.far * WXFX.haze', self.src, 'the far fog distance no longer follows the haze')
        self.assertIn("'   Air quality: '", self.src, 'the time panel lost its air quality line')
        self.assertNotIn('—', aqi_snippet(self.src), 'no em dash in the air-quality strings')

    def test_index_and_cleaning(self):
        """Breakpoints, categories, the haze curve and the reading cleaner, run under JavaScriptCore."""
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        script = JXA % {'snippet': aqi_snippet(self.src)}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(script)
        r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=120)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:600])
        out = json.loads(r.stdout.strip())
        self.assertEqual([0, 50, 51, 100, 150, 200, 300, 500, None, None], out['pm'], 'PM2.5 breakpoints (EPA 2024)')
        self.assertEqual([50, 100, 200], out['o3'], 'ozone 8-hour breakpoints')
        self.assertEqual(['Good', 'Good', 'Moderate', 'Moderate', 'Unhealthy for Sensitive Groups', 'Unhealthy for Sensitive Groups',
                          'Unhealthy', 'Unhealthy', 'Very Unhealthy', 'Very Unhealthy', 'Hazardous', ''], out['cats'])
        k = out['k']
        self.assertEqual(1, k[0], 'clean air keeps the full clear-air distance')
        self.assertEqual(1, k[1], '22 ug/m3 is the 40 km the clear day already has')
        for a, b in zip(k, k[1:]):
            self.assertLessEqual(b, a, 'the clear-air multiplier must fall with PM2.5')
        self.assertAlmostEqual(0.4, k[3], places=2)
        self.assertLessEqual(k[-1], 0.1)
        self.assertGreaterEqual(k[-1], 0.08)
        self.assertEqual(0, out['tint'][0])
        self.assertEqual(0, out['tint'][1], 'no smoke tint through the first half of Moderate')
        self.assertEqual(1, out['tint'][3], 'an Unhealthy day is fully tinted')
        self.assertEqual({'k': 1, 'tint': 0}, out['none'])
        c = out['clean']
        self.assertEqual(2, c['sites'], 'two PM2.5 sites count: the null, the -999 and the 13-hour-old row do not')
        self.assertAlmostEqual(7.3, c['pm25'], places=1)
        self.assertEqual(56, c['o3'], 'the ozone is the freshest sites\' maximum')
        self.assertEqual(1789581600000, c['t'])
        self.assertIsNone(out['single'], 'one PM2.5 site and no ozone is not a reading')
        self.assertIsNone(out['empty'])
        self.assertIsNone(out['stale'], 'readings over twelve hours old say nothing about now')


if __name__ == '__main__':
    unittest.main()
