"""Stage 2 of the Nov 10 plan, the night and winter (Round 247): four looks for Mike's second side by side of the train,
each a uniform or a data switch. His picks (Nov 13): the fronts' clock, the floods and the lying snow on by default
(?frontclock=0, ?floods=0, ?snowlies=0 refuse); the lit floors kept off (?litfloors=1 shows them).

- ?litfloors=1 (AERIAL-7 part 2): an office's rooms light by the floor (a floor on or off, one run of rooms along each zone
  of 8 to 16), at the suites' own lit share. roomLight's uLitFl; the fronts, skins and town strips bind it too.
- ?frontclock=1 (ART-5 b): the house fronts' rooms by the clock's home share instead of 0.48 at every hour.
- ?snowlies=1 (REALDATA-3): the snow lies while the feed's snow_depth says so; the crowns, cards, sky and fog keep the
  falling term. ?wx=snowday is the day after a storm.
- ?floods=1 (ART-3): the Art Museum's wash sheets in their own colour (slot -1), Independence Hall's and Founder's Hall's
  flood in their own materials (tvMat's uTvFlood, the rebuilds' family part gc-flood)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
GC = (ROOT / 'rebuilds' / 'gc.js').read_text()


class LitFloors(unittest.TestCase):
    def test_off_by_default_and_bound_everywhere_the_rooms_are(self):
        self.assertIn('const LIT_FLOORS = /[?&]litfloors=1\\b/.test(location.search);', SRC)
        self.assertIn('uLitFl: { value: LIT_FLOORS ? 1 : 0 }', SRC)
        self.assertIn('uniform vec4 uOcc; uniform float uLitFl;', SRC)
        self.assertIn('const vec4 uOcc = vec4(0.48, 0.54, 0.0, 0.0); const float uLitFl = 0.0;', SRC)
        # the fronts, the skins and the town strips bind it at the old fixed shares
        self.assertEqual(SRC.count('occFixBind(sh);'), 2)
        self.assertIn('if (REAL) occFixBind(sh, frOccU);', SRC)
        self.assertIn('const occFixU = { uOcc: { value: new THREE.Vector4(0.48, 0.54, 0, 0) } };', SRC)

    def test_the_share_is_held(self):
        # a floor on at 1.29 times the clock's office share, a run of 0.55 to 1 of its zone (0.775 on average), every
        # eighth room dark: 1.29 x 0.775 x 0.88 = 0.88, the suites' own share (their floors on at 0.88)
        self.assertIn('float fOn=min(uOcc.y*1.29,1.0);', SRC)
        self.assertIn('float rl=max(1.0,floor(mix(.55,1.0,roomHash(vec2(id.y+7.1,seed*1.9)))*zl+.5));', SRC)
        self.assertAlmostEqual(1.29 * 0.775 * 0.88, 0.88, delta=0.005)


class FrontClock(unittest.TestCase):
    def test_on_by_default_since_mikes_pick(self):
        self.assertIn('const FRONT_CLOCK = !/[?&]frontclock=0\\b/.test(location.search);', SRC)
        self.assertIn('const frOccU = { value: FRONT_CLOCK ? occU.uOcc.value : occFixU.uOcc.value };', SRC)


class SnowLies(unittest.TestCase):
    def test_the_depth_is_asked_ahead_of_the_pinned_tail(self):
        self.assertIn('snowfall,snow_depth,weather_code,', SRC)
        self.assertIn('wind_gusts_10m&hourly=snowfall&forecast_hours=12', SRC)
        self.assertIn('WX.snowDepth = cur.snow_depth == null ? null : cur.snow_depth;', SRC)
        self.assertIn("snowday: { cloud_cover: 6, weather_code: 0, wind_speed_10m: 8, temperature_2m: 25, snow_depth: 0.15 },", SRC)

    def test_on_by_default_and_the_falling_term_is_the_old_one_without_it(self):
        self.assertIn('const SNOW_LIES = !/[?&]snowlies=0\\b/.test(location.search);', SRC)
        self.assertIn('if (SNOW_LIES && WX.snowDepth != null) F.tSnowGround = Math.max(F.tSnowGround, 0.85 * smoothstep01((WX.snowDepth - 0.01) / 0.05));', SRC)
        self.assertIn('    else F.snowFall = F.snowGround;', SRC)   # under ?snowlies=0
        # what only falling snow whitens
        self.assertIn('const snowSky = Math.max(WXFX.snow * 0.55, WXFX.snowFall * 0.3);', SRC)
        self.assertIn('WXFX.snow * 0.4, WXFX.snowFall * 0.3));', SRC)
        self.assertIn('sh.uniforms.uSnowAcc = wxSurfU.uSnowFall;', SRC)
        self.assertIn('uSnowAcc: wxSurfU.uSnowFall, uTexelS', SRC)
        # the roofs, the ground, the lanes and the cars keep the lying term
        self.assertIn('shader.uniforms.uFabSnow = wxSurfU.uSnowAcc;', SRC)
        self.assertIn('sh.uniforms.uCarSnow = wxSurfU.uSnowAcc;', SRC)


class Floods(unittest.TestCase):
    def test_on_by_default_since_mikes_pick(self):
        self.assertIn('const FLOODS = !/[?&]floods=0\\b/.test(location.search), FLOOD_N = {};', SRC)
        self.assertIn('uTvFlood: { value: new THREE.Vector2(FLOODS ? 0.9 : 0, 45) },', SRC)
        self.assertIn('floods: FLOODS,', SRC)
        self.assertIn("uGcFl: { value: api.floods ? 1 : 0 }", GC)

    def test_the_museum_sheets_take_no_slot(self):
        a = SRC.index('        if (FLOODS) {\n          const FLOOD = new THREE.Color(1.0, 0.8, 0.58);')
        block = SRC[a:SRC.index('        }', a)]
        self.assertIn(', -1, 0.45, true, FLOOD);', block)
        self.assertNotIn('themeSlotN', block)   # no later building's colour moves on a many-colour night
        self.assertIn('if (sl[i] < 0) {', SRC)   # a slot of -1 keeps its own colour every night

    def test_founders_hall_is_a_family_part_on_its_own_copies(self):
        self.assertIn("const flood = (m) => K.fam(m.clone(), { id: 'gc-flood',", GC)
        self.assertIn('M.col = flood(M.col); M.wall = flood(M.wall);', GC)



class DoorLamps(unittest.TestCase):
    """?doorlamps=1 (STREET-6): pools in the near lamp map only, on the splats' own material, no point of light."""
    def test_off_by_default_and_near_only(self):
        self.assertIn('const DOOR_LAMPS = REAL && /[?&]doorlamps=1\\b/.test(location.search);', SRC)
        self.assertIn('r.autoClear = false; if (LAMPDYN.scene && LAMPDYN.n) r.render(LAMPDYN.scene, N.cam);', SRC)
        far = SRC[SRC.index('  function lampMapUpdate() {'):SRC.index('  const _lmDir = new THREE.Vector3()')]
        self.assertNotIn('LAMPDYN', far)   # the far map never draws them
        self.assertIn('D.pts = new THREE.Points(g, LAMPMAP.mat);', SRC)   # no program of its own
        self.assertNotIn('LAMPMAP.scene.children', SRC)

    def test_the_shops_open_by_the_panels_rule(self):
        # the CPU's rule is the panels' shader rule (SF_VERT): today's span, last night's running on, the shut weekdays
        self.assertIn("if (yest >= 0) { const op = Math.floor(yest / 2048), cl = yest - op * 2048; if (cl > 1440 && m <= cl - 1440.5) return true; }", SRC)
        self.assertIn("'  if (yest >= 0.0) { float o = floor(yest / 2048.0), c = yest - o * 2048.0; if (c > 1440.0) open = max(open, step(m, c - 1440.5)); }',", SRC)
        self.assertIn('if (sfHrs) sfHrs.set(', SRC)

    def test_doors_only_where_the_picture_has_one(self):
        self.assertIn('if (LAMPDYN.on && cm.door && hash01(seed * 6.13 + j * 1.31) < 0.6 && dl.n < 2048) {', SRC)


class SkinWeather(unittest.TestCase):
    """?skinwx=1 (ART-5 c): the tile skins' wall share weathers, every term about zero mean, faded by the footprint."""
    def test_off_by_default_and_mean_held(self):
        self.assertIn("const SKIN_WX_U = { value: /[?&]skinwx=1\\b/.test(location.search) ? 1 : 0 };", SRC)
        self.assertIn('sh.uniforms.uSkinWx = SKIN_WX_U;', SRC)
        line = [l for l in SRC.splitlines() if 'diffuseColor.rgb *= 1.0 + twK * (' in l][0]
        self.assertIn('(twB - 0.5)', line)       # value noise, mean 0.5
        self.assertIn('(twS - 0.3875)', line)    # 0.5 x (0.55 + 0.45 x 0.5)
        self.assertIn('twK = uSkinWx * (1.0 - win)', SRC)   # never the glass
        self.assertAlmostEqual(0.5 * (0.55 + 0.45 * 0.5), 0.3875)


if __name__ == '__main__':
    unittest.main()
