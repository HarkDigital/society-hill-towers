"""The realism pass, the facade shader's workstream (Mike: "please do anything necessary to make this look more photo
realistic and less cartoony. This should apply to all surfaces"):

- the walls' and the pitched roofs' materials are generated photographs (fetch_wall_art.py, bake_wall_art.py): brick red,
  dark and painted, render, limestone, Formstone, marble, granite and concrete in a 3 by 3 atlas, shingle, slate, metal
  and three-tab in a 2 by 2, and a fresh snow; every coursed one is cut on its own courses so it repeats with no seam,
  and a wall takes only the texture's grain over its kind's mean (its calibrated colour stays the mean)
- a flat roof keeps its dealt kind at every distance (the far roof is the near one's mean), the kinds' albedos spread
- the weather's snow and wet land after the gains and the roof art (the snow came out charcoal on every roof)
- the joinery and stone (frames, lintels, sills, doors, steps, awnings, cornices) stay out of the wall's material
- rain runs, splash and blotches on the walls, a stain under each sill
- a room behind the glass by day and by night (interior mapping), the rooms' lamps by the clock, the city's reflection
  darkening the glass below the horizon a pane sees
- copings and gable ends carry words of their own on style 3; square detached houses take hips in the pitched districts
- the rooftop hardware's grilles and fan guards, roof decks and solar arrays; the landmark rebuilds' stone and brick
"""
import json
import math
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / 'app.js').read_text()


def fn(name):
    a = SRC.index('  function ' + name + '(')
    return SRC[a:SRC.index('\n  }\n', a) + 4]


class WallArt(unittest.TestCase):
    def test_the_manifest(self):
        m = json.loads((ROOT / 'wall_art.json').read_text())
        self.assertEqual(m['wallsKinds'], ['brick_red', 'brick_dark', 'brick_painted', 'stucco', 'ashlar', 'formstone', 'marble', 'granite', 'concrete'])
        self.assertEqual(m['pitchedKinds'], ['shingle', 'slate', 'metal', 'tab'])
        self.assertEqual((len(m['wallsMean']), len(m['wallsM'])), (9, 9))
        self.assertEqual((len(m['pitchedMean']), len(m['pitchedM'])), (4, 4))
        self.assertEqual((m['wallsGrid'], m['pitchedGrid']), (3, 2))
        # a brick tile is a whole number of 7.5 cm courses, a metre or two across; every tile a sensible size
        self.assertAlmostEqual(m['wallsM'][0][1] / 0.075, round(m['wallsM'][0][1] / 0.075), places=6)
        for mx, my in m['wallsM'] + m['pitchedM']:
            self.assertTrue(0.8 < mx < 8 and 0.8 < my < 8, (mx, my))
        for k in ('walls', 'wallsHalf', 'pitched', 'pitchedHalf', 'snow', 'snowHalf'):
            self.assertTrue(m[k].startswith('art/walls/'), k)
            self.assertTrue((ROOT / m[k]).exists(), m[k])
        # the page inlines it and build.py checks its files
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("WALL_ART", text_of("wall_art.json", "null"))', b)
        self.assertIn('"wall_art.json"', b[b.index('for name in ("tree_art.json"'):].split('\n', 1)[0])   # in build.py's file check

    def test_the_fetch_never_prints_the_key(self):
        f = (ROOT / 'fetch_wall_art.py').read_text()
        self.assertIn("os.path.expanduser('~/.config/philly3d/openai.env')", f)
        self.assertNotRegex(f, r'print\([^)]*key')
        self.assertIn("RAW = os.path.join(HERE, 'lidar_cache', 'wall_art_raw')", f)

    def test_the_page_loads_it_on_demand(self):
        f = fn('loadWallArt')
        self.assertIn('artImage(artSrc(W.walls, W.wallsHalf))', f)
        self.assertIn('artImage(artSrc(W.pitched, W.pitchedHalf))', f)
        self.assertIn('!isTouch', f)   # the walls' atlas is a computer's
        self.assertIn("step('Dressing the walls', loadWallArt);", SRC)
        self.assertIn('const WALL_ART_ON = REAL && ', SRC)
        # the snow only the first time it lies, from the frame hook applyLighting calls
        self.assertIn('wxSurfU.uSnowAcc.value > 0.02', fn('facadeFrame'))
        self.assertEqual(SRC.count('    facadeFrame();'), 1)

    def test_the_wall_takes_only_the_grain(self):
        self.assertIn("'  vec3 r = T / max(mean, vec3(1.0e-3));',", SRC)
        self.assertIn("'  return mix(col, col * clamp(mix(vec3(lr), r, chroma), 0.0, 3.0), k);',", SRC)
        # faded out before the mips reach a neighbouring cell
        self.assertIn("'  k *= 1.0 - smoothstep(20.0, 60.0, fp);',", SRC)
        # the joinery stays out of it, under REAL
        self.assertIn("'      float wallM = (1.0 - glass) * (1.0 - ' + (REAL ? 'trimM' : '0.0') + ');',", SRC)


class Bake(unittest.TestCase):
    """bake_wall_art's course cut on a drawn running bond: the tile repeats with no seam in the pattern."""

    def test_a_drawn_bond_cuts_clean(self):
        try:
            import numpy as np
            sys.path.insert(0, str(ROOT))
            import bake_wall_art as B
        except Exception as e:   # the pipeline's own deps (numpy, PIL) are not the page's
            self.skipTest(str(e))
        rng = np.random.default_rng(3)
        H = W = 1024
        a = np.zeros((H, W, 3), np.float32)
        course = 40
        for c in range(H // course + 1):
            y0 = c * course
            x = -rng.integers(0, 150)
            while x < W:
                L = int(rng.integers(120, 170))
                tone = rng.uniform(120, 200)
                a[max(0, y0):min(H, y0 + course), max(0, x):min(W, x + L)] = (tone, tone * 0.45, tone * 0.35)
                a[max(0, y0):min(H, y0 + course), max(0, x + L - 5):min(W, x + L)] = 200   # the head joint
                x += L
            a[max(0, y0):min(H, y0 + 5)] = 200   # the bed joint
        t, mx, my, rep = B.course_tile(a, 0.075, 'drawn')
        self.assertIn('courses cut on their joints', rep)
        n = round(my / 0.075)
        self.assertEqual(n % 2, 0)
        self.assertAlmostEqual(t.shape[0] / n, course, delta=1.0)
        # the wrap runs through a bed joint, neither doubled nor lost: its rows at the two ends add up to one joint's five
        L = (t @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean(axis=1)
        self.assertEqual(int((L[:12] > 150).sum() + (L[-12:] > 150).sum()), 5)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Clock(unittest.TestCase):
    def run_js(self, body):
        a = SRC.index('  const occU = ')
        block = SRC[a:SRC.index('  const WINDOW_INTERIOR_GLSL = `', a)]
        js = 'const THREE = require(%s);\nconst REAL = true; const clock = { y: 2026, m: 10, d: 12, minutes: 0 };\n' % json.dumps(str(ROOT / 'three.min.js')) + block + body
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_rooms_by_the_clock(self):
        out = self.run_js(r'''
const at = (y, m, d, min) => { clock.y = y; clock.m = m; clock.d = d; clock.minutes = min; occUpdate(); return occU.uOcc.value.toArray(); };
console.log(JSON.stringify({ eve: at(2026, 10, 12, 1260), late: at(2026, 10, 12, 180), six: at(2026, 10, 12, 1080), sat: at(2026, 10, 17, 1080), clean: at(2026, 10, 12, 1320) }));
''')
        self.assertAlmostEqual(out['eve'][0], 0.55, places=2)       # 21:00, the homes' evening
        self.assertLess(out['late'][0], 0.12)                       # 03:00
        self.assertLess(out['late'][1], 0.15)
        self.assertGreater(out['six'][1], 0.5)                      # offices at six
        self.assertAlmostEqual(out['sat'][1], out['six'][1] * 0.6, places=5)   # a Saturday's offices
        self.assertEqual(out['clean'][2], 1)                        # the cleaners' floors at 22:00
        self.assertEqual(out['late'][2], 0)

    def test_the_old_shares_without_the_clock(self):
        # a host that binds no clock keeps the old 0.48 of the homes and 0.54 of the suites
        self.assertIn('const vec4 uOcc = vec4(0.48, 0.54, 0.0, 0.0);', SRC)
        self.assertIn('float on=mix(step(1.0-uOcc.x,r),max(step(1.0-uOcc.y,zone)*floorOn,uOcc.z*step(floorHash,.08)),office);', SRC)
        # every room host binds it: the fabric, the apartments, the Ryland, the curtain wall
        self.assertEqual(SRC.count('occBind(shader);') + SRC.count('occBind(sh);'), 4)
        # the towers' skins and their far glow follow the offices
        self.assertIn("step(' + (REAL ? '1.0 - 0.34 * uOcc.y / 0.54' : '0.66') + ', h)", SRC)
        self.assertIn('towerMat.opacity = night * (REAL ? Math.min(1, occU.uOcc.value.y / 0.55) : 1);', SRC)


class Shader(unittest.TestCase):
    def test_the_weather_comes_after_the_gains(self):
        a = SRC.index("        .replace('#include <color_fragment>', [\n          '#include <color_fragment>',\n          '{',")
        block = SRC[a:SRC.index('].join', a)]
        # the block starts again from the vertex colour (the weather's own colour lands ahead of it)
        self.assertLess(block.index("'  diffuseColor = vec4(diffuse, opacity);',"), block.index("'#include <color_fragment>',", block.index('diffuse, opacity')))
        # and lays the snow and the wet at its end, after the roofs' art; walls take neither
        snow = block.index("'    fabSnowW = uFabSnow * fUp * (0.80 + 0.20 * fN);',")
        self.assertGreater(snow, block.index("'      diffuseColor.rgb = mix(rFar, rCol, 1.0 - smoothstep(0.25, 1.4, rfw)) * (0.86 + 0.28 * fract(rsd * 7.13));',"))
        self.assertIn("'    float fUp = smoothstep(0.55, 0.85, n.y);',", block)
        self.assertIn('shader.uniforms.uFabSnow = wxSurfU.uSnowAcc; shader.uniforms.uFabWet = wxSurfU.uWet;', SRC)
        # the bright kinds and the snow never glow past a dark roof's colour at night
        self.assertIn("min(diffuseColor.rgb, vec3(0.06)) * uNight * ' + ROOF_NIGHT.toFixed(3)", SRC)

    def test_the_roof_kinds_hold_at_any_distance(self):
        self.assertIn("'      vec3 rFar = mix(diffuseColor.rgb, rMean * ' + (gR * 0.9).toFixed(3) + ' * rKk, uRoofOwn);',", SRC)
        self.assertIn('uRoofKindK: { value: REAL ? new THREE.Vector4(0.8, 1.35, 1.9, 1.05) : new THREE.Vector4(1, 1, 1, 1) },', SRC)

    def test_the_pitched_roofs_and_the_copings(self):
        self.assertIn("'  if (st == 3 && !coping && n.y > 0.35 && n.y < 0.985 && uPitchOn > 0.5) {',", SRC)
        self.assertIn("'  bool coping = st == 3 && variantF > 2.5;',", SRC)
        self.assertIn('const ST_COPING = REAL ? 3 + 96 : 3, ST_GABLE = REAL ? 3 + 64 : 3;', SRC)
        self.assertIn('add(poly, top - 0.05, top + 0.45, darkHex, ST_COPING, [insetRing(poly, 0.35)]);   // the parapet lip', SRC)
        self.assertIn('pushGeom(ch, g.ends, wallC.r, wallC.g, wallC.b, ST_GABLE, base);', SRC)
        self.assertIn('const capSt = st >= 96 && (st & 31) === 3 ? st : 3;', SRC)
        # both words fit the chunks' signed style byte
        self.assertLess(3 + 96, 128)

    def test_the_glass_sees_the_city_below_its_horizon(self):
        f = fn('glassOpticsPatch')
        self.assertIn("if (REAL) shader.fragmentShader = shader.fragmentShader.replace('#include <lights_fragment_maps>'", f)
        self.assertIn('radiance = mix(radiance, radiance * mix(vec3(0.30, 0.29, 0.28), vec3(1.0)', f)
        # scene.environment is never replaced (a probe of another size would recompile every lit program)
        self.assertNotIn('scene.environment =', SRC[SRC.index('  const wallArtU = {'):SRC.index("  step('Dressing the walls'")])

    def test_the_room_behind_the_glass(self):
        self.assertIn('vec4 roomBox(vec2 uv, vec3 d, vec4 A) {', SRC)
        self.assertIn('const FAB_DAYROOM = REAL && !isTouch;', SRC)
        # the pane's u runs either way along a wall: its sign is read from the derivatives
        self.assertIn("'    float uSg = (dFdx(uW) * dot(dFdx(vWPos.xz), perpW) + dFdy(uW) * dot(dFdy(vWPos.xz), perpW)) >= 0.0 ? 1.0 : -1.0;',", SRC)
        self.assertIn('totalEmissiveRadiance += fabRoomDay * (1.0 - uNight);', SRC)
        # a host that sets no ray draws the flat pane it always did
        self.assertIn('vec3 roomRay = vec3(0.0, 0.0, 1.0); float roomPar = 0.0;', SRC)
        self.assertIn('if(roomPar>.5&&detail>.001){', SRC)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Roofs(unittest.TestCase):
    def plan(self, real, lot, poly, area=None, h=9.0):
        names = ['signedArea', 'orientedBox', 'simplifyRing', 'roofQuad', 'roofPlan']
        pieces = []
        for n in names:
            try:
                pieces.append(fn(n))
            except ValueError:
                pass
        a = SRC.index('  const PITCHED_AREAS = ')
        pieces.insert(0, SRC[a:SRC.index('\n', a) + 1])
        js = ('const REAL = %s; const clamp = (v, a, b) => Math.max(a, Math.min(b, v)); const hash01 = () => 0.01;\n' % ('true' if real else 'false')
              + '\n'.join(pieces)
              + '\nconst poly = %s; const p = roofPlan(poly, %s, %s, 1, 0, 0, 1.5, %s); console.log(JSON.stringify(p ? { form: p.form } : null));'
              % (json.dumps(poly), area if area is not None else 'Math.abs(signedArea(poly))', h, lot))
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_a_square_stone_house_takes_a_hip(self):
        sq = [[-6000, -14000], [-5989, -14000], [-5989, -13989.5], [-6000, -13989.5]]   # 11 x 10.5 m in Chestnut Hill
        self.assertEqual(self.plan(True, 0.75, sq), {'form': 2})
        self.assertIsNone(self.plan(False, 0.8, sq))          # ?real=0: the old gable lottery, which a square plan fails
        self.assertIsNone(self.plan(True, 0.2, sq))           # a brick row's kind never takes the hip

    def test_a_long_house_keeps_its_gable(self):
        lng = [[-6000, -14000], [-5984, -14000], [-5984, -13992], [-6000, -13992]]   # 16 x 8 m
        self.assertEqual(self.plan(True, 0.75, lng), {'form': 1})

    def test_the_bigger_houses_only_in_the_pitched_districts(self):
        big = [[-6000, -14000], [-5981, -14000], [-5981, -13984], [-6000, -13984]]   # 19 x 16 m, 304 m2
        self.assertEqual(self.plan(True, 0.75, big), {'form': 2})
        away = [[p[0] + 7000, p[1] + 16000] for p in big]    # the same house in South Philadelphia
        self.assertIsNone(self.plan(True, 0.75, away))


class RoofKitAndLandmarks(unittest.TestCase):
    def test_the_decks(self):
        lay = fn('roofKitLay')
        self.assertEqual(lay.count('deckOk()'), 4)                 # every deck and array wholly on the roof
        self.assertIn('const cnt = M.map(() => 0), caps = M.map((m) => m.instanceMatrix.count);', lay)
        self.assertIn("mat.customProgramCacheKey = () => 'roofkit-' + ki + (REAL ? '-real' : '');", SRC)

    def test_the_landmarks(self):
        f = fn('landmarkDetail')
        self.assertIn("if (own) { m.customProgramCacheKey = () => ownKey + '|rbdetail'; return; }", f)
        self.assertIn('m.userData.wxSurf = true;', f)
        self.assertIn('landmarkDetail(mm);', SRC[SRC.index("  step('Rebuilding the landmarks'"):])


if __name__ == '__main__':
    unittest.main()
