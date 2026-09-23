"""Round 137: five windows of the South Tower's south face light in the skyline's colours of the night.

Mike boxed them on a screenshot: the 14th row of glass down from the parapet (floor index 16 of 30) and the
6th to 10th bays from the west. The page finds the face by its outward normal, the rooms by the glass
shader's room coordinates (the face's seed, the floor, the bays), and deals the night's colours across the
five in order. These checks run the page's own helpers under Node and read the wiring from app.js."""
import json
from pathlib import Path
import math
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ShtWindows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'app.js').read_text()
        cls.towers = json.loads((ROOT / 'scene.json').read_text())['towers']

    def helpers(self):
        s = self.source
        return s[s.index('  function shtWinDeal('):s.index('  const groundMats')]

    def spec(self):
        m = re.search(r"const SHT_THEMED = \{ tower: /([^/]+)/, floor: (\d+), from: (\d+), to: (\d+) \};", self.source)
        self.assertIsNotNone(m, 'SHT_THEMED is declared in its one-line form')
        return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))

    def test_the_boxed_windows(self):
        name, floor, lo, hi = self.spec()
        self.assertEqual((floor, lo, hi), (16, 5, 9))   # the 14th row down of 30, bays 5 to 9 from the west: five windows
        hits = [t['name'] for t in self.towers if re.search(name, t['name'])]
        self.assertEqual(hits, ['Society Hill Towers South Building'])

    def test_deal_and_south_face(self):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        south = next(t for t in self.towers if 'South' in t['name'])
        script = self.helpers() + r'''
const out = {};
out.one = shtWinDeal(['green']);
out.two = shtWinDeal(['red', 'white']);
out.three = shtWinDeal(['green', 'white', 'red']);
out.four = shtWinDeal(['a', 'b', 'c', 'd']);
const W = WIDTH, Dp = DEPTH;
const sides = [{ len: W, off: Dp / 2, axis: 'x' }, { len: W, off: -Dp / 2, axis: 'x' }, { len: Dp, off: W / 2, axis: 'z' }, { len: Dp, off: -W / 2, axis: 'z' }];
out.south = sides.indexOf(shtSouthSide(sides, ANG));
out.turned = [0, 1.2, 2.4, 3.6, 4.8].map((a) => sides.indexOf(shtSouthSide(sides, a)));
console.log(JSON.stringify(out));
'''.replace('WIDTH', str(south['width_m'])).replace('DEPTH', str(south['depth_m'])).replace('ANG', str(-south['angleRad']))
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out['one'], ['green'] * 5)
        self.assertEqual(out['two'], ['red', 'white', 'red', 'white', 'red'])
        self.assertEqual(out['three'], ['green', 'white', 'red', 'green', 'white'])
        self.assertEqual(out['four'], ['a', 'b', 'c', 'd', 'a'])
        self.assertEqual(out['south'], 0)   # the wide face at +depth/2: its normal is about 9 degrees off due south
        # the pick follows the outward normal as the tower turns (the page's rotation: z' = -x sin(a) + z cos(a))
        for a, got in zip([0, 1.2, 2.4, 3.6, 4.8], out['turned']):
            k = [math.cos(a), -math.cos(a), -math.sin(a), math.sin(a)]
            self.assertEqual(got, k.index(max(k)), a)

    def test_wiring(self):
        s = self.source
        # the tower glass compiles the themed rooms in, with the bloom mask only where the post pipeline runs
        self.assertIn("THEMED_ROOMS: ''", s)
        self.assertIn("...(POST.on ? { THEMED_BLOOM: '' } : {})", s)
        self.assertIn('towerGlassMat.onBeforeCompile = (sh) => { apartmentWindowHook(sh); Object.assign(sh.uniforms, shtWinU); };', s)
        # the variation panes keep the plain hook, and nothing hangs in front of the five
        self.assertIn('towerVarMat.onBeforeCompile = apartmentWindowHook;', s)
        self.assertIn('if (s === themedSide && fi === SHT_THEMED.floor && bi >= SHT_THEMED.from && bi <= SHT_THEMED.to) continue;', s)
        self.assertIn('if (s === themedSide) shtWinU.uLitWin.value.set(roomSeed, SHT_THEMED.floor, SHT_THEMED.from, SHT_THEMED.to);', s)
        # the shader: the rooms by seed, floor and bays, the skyline's emission, and the declarations behind the define
        hook = s[s.index('  function apartmentWindowHook('):s.index('  function towerRoomCoordinates(')]
        self.assertIn('#ifdef THEMED_ROOMS', hook)
        self.assertIn('step(abs(vInterior.z-uLitWin.x),.005)*step(abs(rid.y-uLitWin.y),.5)*step(uLitWin.z-.5,rid.x)*step(rid.x,uLitWin.w+.5)', hook)
        self.assertIn('totalEmissiveRadiance=te*uThemeNight*2.4*mix(1.0,.42,tsat)', hook)
        self.assertIn('uniform vec4 uLitWin; uniform float uThemeNight; uniform vec3 uWin0, uWin1, uWin2, uWin3, uWin4; float themedRoom=0.0;', hook)
        self.assertIn('gl_FragColor.a+=uThemeNight*.7*themedRoom;', hook)
        # the theme deals the night's colours to the five, eases them with the crowns and lands them on load
        self.assertIn("shtWinDeal(th.colors).forEach((c, j) => THEME.wtgt[j].setHex(", s)
        self.assertIn('for (let i = 0; i < 5; i++) { const c = THEME.wcur[i], t = THEME.wtgt[i];', s)
        self.assertIn('for (let i = 0; i < 5; i++) THEME.wcur[i].copy(THEME.wtgt[i]);', s)
        self.assertIn("shtWinU['uWin' + i].value.copy(_thHouseLin).lerp(themeLift(_thTmp.copy(THEME.wcur[i]), _thWinLin), THEME.on)", s)
        self.assertIn('if (!themeMat && !themeSheet && !bfbNodes && !towerGlassMat) return;', s)
        # the day's own late data (the scoreboard, the served calendar) lands at once: the settled flag is read BEFORE
        # lightsRetarget clears it (Round 136's guard read it after, so the landing never fired and a game day eased from white)
        upd = s[s.index('  function updateLightsTheme('):s.index('    const e = THEME.seeded ?')]
        self.assertLess(upd.index('const wasSettled = THEME.settled;'), upd.index('lightsRetarget();'))
        self.assertIn('if (sameDay && wasSettled) THEME.seeded = false;', upd)
        self.assertNotIn('sameDay && THEME.settled', upd)
        rt = s[s.index('  function lightsRetarget('):s.index('  function updateLightsTheme(')]
        self.assertIn('THEME.settled = false;', rt)   # the reason the read must come first

    def test_seed_is_unique(self):
        # the shader matches the face by its room seed within 0.005: no other face of the three towers, nor a lobby, comes near it
        seeds = []
        for ti, t in enumerate(self.towers):
            W, Dp = t['width_m'], t['depth_m']
            for off, axis in ((Dp / 2, 'x'), (-Dp / 2, 'x'), (W / 2, 'z'), (-W / 2, 'z')):
                seeds.append((t['name'], off, axis, ti * .71 + off * .13 + (0 if axis == 'x' else 3.7)))
            seeds.append((t['name'], 0, 'lobby', ti * .71))
        south = next(q for q in seeds if 'South' in q[0] and q[2] == 'x' and q[1] > 0)
        others = [q for q in seeds if q is not south]
        self.assertGreater(min(abs(q[3] - south[3]) for q in others), 0.1)


if __name__ == '__main__':
    unittest.main()
