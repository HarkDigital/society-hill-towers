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
- the packed tiers' pitched roofs overhang their walls along their own plane, boxed in on a computer (a fascia and a
  soffit under every eave); the pitched districts' detached Ls take a main hip and a cross wing that dies into it;
  the rows' party walls carry copings from the air
- the review's round: the walls' art is a computer's whole (no phone program carries it, no phone rebuild is re-hooked),
  its gradients are taken where the control flow is uniform, the snow and the weathering run only where they can show,
  ?real=0 keeps the weather's old colour, the copings stand on houses' roofs only and take the snow, the eaves are boxed
  in the outer districts only, the towers' skins are left to their own workstream
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
        self.assertIn('"wall_art.json"):', b)

    def test_the_fetch_never_prints_the_key(self):
        f = (ROOT / 'fetch_wall_art.py').read_text()
        self.assertIn("os.path.expanduser('~/.config/philly3d/openai.env')", f)
        self.assertNotRegex(f, r'print\([^)]*key')
        self.assertIn("RAW = os.path.join(HERE, 'lidar_cache', 'wall_art_raw')", f)

    def test_the_page_loads_it_on_demand(self):
        f = fn('loadWallArt')
        self.assertIn('artImage(artSrc(W.walls, W.wallsHalf))', f)
        self.assertIn('artImage(artSrc(W.pitched, W.pitchedHalf))', f)
        self.assertIn('if (WALL_ART_DEV) {', f)   # the walls' atlas is a computer's
        self.assertIn("const WALL_ART_DEV = REAL && !isTouch && typeof WALL_ART !== 'undefined' && !!WALL_ART && !!WALL_ART.walls && ", SRC)
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
        # the towers' far glow follows the offices; their skins are the fronts-skins workstream's material, which takes
        # the clock by its own occBind (this branch leaves it as it was)
        self.assertIn('towerMat.opacity = night * (REAL ? Math.min(1, occU.uOcc.value.y / 0.55) : 1);', SRC)
        a = SRC.index("  step('Cladding the towers'")
        self.assertNotIn('uOcc', SRC[a:SRC.index("mat.customProgramCacheKey = () => 'tower-skin-' + kind;", a)])
        # the weekday is worked out only when the model's date moves, not every frame
        u = fn('occUpdate')
        self.assertIn('if (clock.y !== occDay.y || clock.m !== occDay.m || clock.d !== occDay.d) {', u)
        self.assertEqual(u.count('new Date('), 1)


class Shader(unittest.TestCase):
    def test_the_weather_comes_after_the_gains(self):
        a = SRC.index("        .replace('#include <color_fragment>', [\n          '#include <color_fragment>',\n          '{',")
        block = SRC[a:SRC.index('].join', a)]
        # the block starts again from the vertex colour (the weather's own colour lands ahead of it), under REAL only:
        # ?real=0 keeps the weather's colour under the gains, as it was
        self.assertIn("...(REAL ? ['  diffuseColor = vec4(diffuse, opacity);', '#include <color_fragment>'] : []),", block)
        # and lays the snow and the wet at its end, after the roofs' art; walls take neither; on a dry day none of it runs
        snow = block.index("'    fabSnowW = uFabSnow * fUp * (0.80 + 0.20 * fN);',")
        gate = block.index("'  if (uFabSnow + uFabWet > 0.001) {',")
        self.assertLess(gate, snow)
        self.assertEqual(block[block.rindex('...(REAL ? [', 0, gate):gate].count('\n'), 1)
        self.assertGreater(snow, block.index("'      diffuseColor.rgb = mix(rFar, rCol, 1.0 - smoothstep(0.25, 1.4, rfw)) * (0.86 + 0.28 * fract(rsd * 7.13));',"))
        self.assertIn("'    float fUp = smoothstep(0.55, 0.85, n.y);',", block)
        self.assertIn('shader.uniforms.uFabSnow = wxSurfU.uSnowAcc; shader.uniforms.uFabWet = wxSurfU.uWet;', SRC)
        # the bright kinds and the snow never glow past a dark roof's colour at night
        self.assertIn("min(diffuseColor.rgb, vec3(0.06)) * uNight * ' + ROOF_NIGHT.toFixed(3)", SRC)
        # the snow's screen gradient is taken under the uniform gate, not under the per-pixel fabSnowW
        self.assertLess(block.index("'    float sfp = max(fwidth(sg.x), fwidth(sg.y)) * 1024.0;',"), block.index("'    if (fabSnowW > 0.001) {',"))

    def test_the_weathering_runs_only_where_it_shows(self):
        a = SRC.index("        .replace('#include <color_fragment>', [\n          '#include <color_fragment>',\n          '{',")
        block = SRC[a:SRC.index('].join', a)]
        gk = block.index("'      float gk = det * (1.0 - glass) * (tower ? 0.4 : 1.0) * uFabK.z;',")
        self.assertLess(gk, block.index("'      if (gk > 0.001) {',"))
        self.assertLess(block.index("'      if (gk > 0.001) {',"), block.index("float stk = shtVN(vec2(sx, v * 0.11))"))
        self.assertIn('if (det > 0.001) { float drip = rectM(', block)

    def test_the_walls_art_is_a_computers_whole(self):
        a = SRC.index("        .replace('#include <color_fragment>', [\n          '#include <color_fragment>',\n          '{',")
        block = SRC[a:SRC.index('].join', a)]
        common = SRC[SRC.index("        .replace('#include <common>', [\n          '#include <common>',\n          WINDOW_INTERIOR_GLSL,"):a]
        # the atlas lookup every device's pitched roofs use; the walls' kind and detail a computer's only
        self.assertIn('...FAB_ATLAS_FN,', common)
        self.assertIn("...(WALL_ART_DEV ? [...FAB_WALL_FN,\n          'float fabWallKind(", common)
        self.assertIn("...(WALL_ART_DEV ? [\n            '      float wk = uWallOn > 0.5 ? fabWallKind(", block)
        self.assertIn("] : ['      if (detT > 0.001 && wallM > 0.01) {']),", block)
        self.assertIn("...(WALL_ART_DEV ? [\n            '  else if (abs(n.y) < 0.35 && st == 3 && variantF > 1.5", block)
        # the tile coordinate's gradients ahead of the branch the glass's edge splits; none taken inside fabWallArt
        self.assertLess(block.index('wTx = dFdx(wT), wTy = dFdy(wT);'), block.index("'      if (wk > -0.5 && wallM > 0.01) {',"))
        fa = SRC[SRC.index("'vec3 fabWallArt("):SRC.index("  // the rooms behind the glass by day")]
        self.assertNotIn('dFdx', fa)
        self.assertNotIn('dFdy', fa)
        # the landmarks: no phone re-hook, no flat-shaded material, the three planes' gradients before their branches
        f = fn('landmarkDetail')
        self.assertIn('if (!WALL_ART_DEV || !m || rbDone.has(m)) return;', f)
        self.assertIn('|| m.flatShading) return;', f)
        self.assertLess(f.index('tYx = dFdx(tY)'), f.index('if (an.x > 0.01)'))
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



@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Eaves(unittest.TestCase):
    """buildings#12 and #11: the overhang keeps the roof's plane on the wall's top; an L takes a main hip and a cross wing."""

    def run_js(self, body):
        names = ['signedArea', 'pointInPoly', 'orientedBox', 'simplifyRing', 'roofQuad', 'roofL', 'roofPlan', 'hipGeom', 'quadGable', 'wingGeom']
        a = SRC.index('  const PITCHED_AREAS = ')
        js = ('const THREE = require(%s); const REAL = true; const clamp = (v, a, b) => Math.max(a, Math.min(b, v)); const hash01 = () => 0.01;\n'
              % json.dumps(str(ROOT / 'three.min.js')) + SRC[a:SRC.index('\n', a) + 1] + '\n'.join(fn(n) for n in names) + body)
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_gable_overhangs_along_its_own_plane(self):
        out = self.run_js(r"""
const q = [[0, 0], [12, 0], [12, 8], [0, 8]];
const flat = quadGable(q, 6, 9, null), g = quadGable(q, 6, 9, null, 0.3);
const ys = (geo) => Array.from(geo.slopes.attributes.position.array).filter((v, i) => i % 3 === 1);
const xz = (geo) => Array.from(geo.slopes.attributes.position.array).filter((v, i) => i % 3 !== 1);
console.log(JSON.stringify({ minFlat: Math.min(...ys(flat)), min: Math.min(...ys(g)), maxZ: Math.max(...xz(g)), minZ: Math.min(...xz(g)), out: g.eaveOut.map((e) => [e.nx, e.nz, e.s]), flatOut: flat.eaveOut.length }));
""")
        self.assertEqual(out['minFlat'], 6)
        self.assertEqual(out['flatOut'], 0)                     # no overhang asked, none made (the core's gables)
        self.assertAlmostEqual(out['min'], 6 - 0.3 * 3 / 4, places=5)   # 0.3 m out, down the slope's own 3 in 4
        self.assertAlmostEqual(out['minZ'], -0.3, places=5)
        self.assertAlmostEqual(out['maxZ'], 12, places=5)       # the eaves move out; the gable ends stay on their walls
        self.assertEqual(sorted(tuple(o[:2]) for o in out['out']), [(0, -1), (0, 1)])

    def test_an_unboxed_hip_sits_flush(self):
        # with no soffit under it an overhang is a slit of sky from the street, so an unboxed hip has none: its eave
        # corners on the footprint's own corners at the wall's top (0 is an overhang of nothing, not the old default)
        out = self.run_js(r"""
const ob = orientedBox([[0, 0], [12, 0], [12, 10], [0, 10]]);
const pts = (g) => { const a = g.attributes.position.array, o = []; for (let i = 0; i < a.length; i += 3) o.push([a[i], a[i + 1], a[i + 2]]); return o; };
const lo = (g) => pts(g).filter((p) => p[1] < 6.5);
const flat = lo(hipGeom(ob, 6, 9, 0)), old = lo(hipGeom(ob, 6, 9));
console.log(JSON.stringify({ x: [Math.min(...flat.map((p) => p[0])), Math.max(...flat.map((p) => p[0]))], z: [Math.min(...flat.map((p) => p[2])), Math.max(...flat.map((p) => p[2]))],
  y: [...new Set(flat.map((p) => p[1]))], oldX: [Math.min(...old.map((p) => p[0])), Math.max(...old.map((p) => p[0]))] }));
""")
        self.assertEqual([round(v, 4) for v in out['x']], [0, 12])
        self.assertEqual([round(v, 4) for v in out['z']], [0, 10])
        self.assertEqual(out['y'], [6])
        self.assertEqual([round(v, 4) for v in out['oldX']], [-0.3, 12.3])   # no overhang named: the old 0.3

    def test_an_l_takes_a_main_hip_and_a_cross_wing(self):
        out = self.run_js(r"""
const rot = (pts, a, cx, cz) => pts.map(([x, z]) => [cx + x * Math.cos(a) - z * Math.sin(a), cz + x * Math.sin(a) + z * Math.cos(a)]);
const L0 = [[0, 0], [14, 0], [14, 8], [6, 8], [6, 13], [0, 13]], res = [];
for (const a of [0, 0.4, 1.3, 2.7]) for (const rev of [false, true]) {
  let p = rot(L0, a, -6000, -14000); if (rev) p = p.slice().reverse();
  const plan = roofPlan(p, Math.abs(signedArea(p)), 9, 1, 0, 0, 1.5, 0.75);
  if (!plan || plan.form !== 5) { res.push(null); continue; }
  const A = plan.L.A, B = plan.L.B, g = wingGeom(B, 5.6, 7.5, 0.3), n = g.attributes.normal.array;
  let up = true; for (let i = 1; i < n.length; i += 3) if (n[i] < 0.5) up = false;
  // the wing's outer wall on the footprint's edge: a step in is inside it, a step out is not
  res.push({ A: [Math.min(A.w, A.d), Math.max(A.w, A.d)].map((v) => +v.toFixed(2)), hs: +B.hs.toFixed(2), Lb: +B.Lb.toFixed(2), e: +B.e.toFixed(2), up,
    inside: pointInPoly(B.ox + B.dx * 0.5, B.oz + B.dz * 0.5, p), outside: !pointInPoly(B.ox - B.dx * 0.5, B.oz - B.dz * 0.5, p),
    flush: pointInPoly(B.ox + B.dx * (B.Lb + 0.5) + B.dz * B.flush * (B.hs - 0.3), B.oz + B.dz * (B.Lb + 0.5) - B.dx * B.flush * (B.hs - 0.3), p) });
}
// a rectangle is roofQuad's; an L away from the pitched districts, or a row's kind, stays flat
const away = rot(L0, 0, 1000, 1000), U = [[0, 0], [14, 0], [14, 9], [10, 9], [10, 4], [4, 4], [4, 9], [0, 9]].map(([x, z]) => [x - 6000, z - 14000]);
console.log(JSON.stringify({ res, away: roofPlan(away, Math.abs(signedArea(away)), 9, 1, 0, 0, 1.5, 0.75),
  row: roofPlan(rot(L0, 0, -6000, -14000), 142, 9, 1, 0, 0, 1.5, 0.2), U: roofL(U, Math.abs(signedArea(U))) }));
""")
        for r in out['res']:
            self.assertIsNotNone(r)
            self.assertEqual(r['A'], [8, 14])                   # the main wing the full length
            self.assertEqual((r['hs'], r['Lb'], r['e']), (3, 5, 4))   # the cross wing 6 wide, 5 out, run on to the main ridge
            self.assertTrue(r['up'] and r['inside'] and r['outside'] and r['flush'], r)
        self.assertIsNone(out['away'])
        self.assertIsNone(out['row'])
        self.assertIsNone(out['U'])

    def test_the_boards_are_a_computers(self):
        self.assertIn('const EAVE_OVH = 0.3, EAVE_FASCIA = 0.2, EAVE_BOX = REAL && !isTouch;', SRC)
        self.assertIn('const EAVE_TIER = { x0: -3700, x1: 2300, z0: -4480, z1: 6400 };', SRC)
        f = fn('raisePitched')
        # the outer districts' only (the far ring's and the towns' were most of 26 MB under a pixel); there and on a phone
        # every roof keeps its eave on the wall with no overhang (no soffit, so no slit of sky from the street); with a box
        # a hip's plane meets the wall's top 0.3 m out; ?real=0 keeps the old hip, its overhang at the wall's height
        self.assertIn('const box = EAVE_BOX && poly[0][0] > EAVE_TIER.x0 && poly[0][0] < EAVE_TIER.x1 && poly[0][1] > EAVE_TIER.z0 && poly[0][1] < EAVE_TIER.z1;', f)
        self.assertIn('quadGable(plan.quad, eaveY, ridgeY, null, box ? EAVE_OVH : 0)', f)
        self.assertIn('hipGeom(ob, eaveY - (box ? EAVE_OVH * s : 0), ridgeY, box || !REAL ? 0.3 : 0)', f)
        self.assertIn('const A = plan.L.A, B = plan.L.B, o = box ? EAVE_OVH : 0,', f)
        self.assertEqual(f.count('if (box)'), 3)
        self.assertNotIn('if (EAVE_BOX)', f)
        # the cross wing stands 3 cm under the main one, where a face of each is one plane
        self.assertIn('wingGeom(B, yE - 0.03, eB + s * B.hs, o)', f)
        # every board quad is two triangles on four vertices, the chunks' own stride
        self.assertIn('ch.idx.push(i0, i0 + 1, i0 + 2, i0, i0 + 2, i0 + 3);', fn('eaveBox'))


class Copings(unittest.TestCase):
    def test_the_party_walls(self):
        lay = fn('roofKitLay')
        self.assertIn('const COPE = M.length > 7 ? 7 : -1;', lay)
        # a coping is a metre long and stretched along its own x only
        self.assertIn("e[o] = c * len; e[o + 1] = 0; e[o + 2] = -sn * len;", lay)
        self.assertIn("e[o + 8] = sn; e[o + 9] = 0; e[o + 10] = c;", lay)
        # wholly on the roof, a row's depth, a rowhouse's width
        self.assertIn('roofKitOn(mlo, mhi, u + t * len, v, hl, hs)', lay)
        self.assertIn('if (hs <= 7.5) for (let k = 0; k <= n; k++) cope(', lay)
        self.assertIn('if (hs <= 3.8 && hl >= 1.3 * hs) for (const sg of [-1, 1]) cope(0, sg * (hs - 0.12), true, 2 * hl);', lay)
        # the deck's early continue comes after the copings, so a house with a deck keeps its party walls
        self.assertLess(lay.index('cope(0, sg * (hs - 0.12)'), lay.index('            if (hd < (deckArea(x0, z0) ? 0.125 : 0.04) && deckOk()) {\n              const [x, z] = at(du, 0);'))

    def test_on_houses_roofs_only(self):
        # the note carries a row flag (a row or a corner store, by the OPA word or the type, no more than 14 m up), and the
        # lay lays a coping only on a flagged roof: an apartment slab, a garage or a school one house deep takes none
        self.assertIn('const ROOF_KIT_STRIDE = 11, RK_NU = 8, RK_NV = 6;', SRC)
        self.assertIn('ROOF_KIT.buf.set([ob.cx, ob.cz, top, ax.ax, ax.az, ax.hl, ax.hs, seed, lo, hi, row], ROOF_KIT.n * S);', SRC)
        self.assertIn('roofKitNote(ob, ax, base + h, area, seed, poly, holes, REAL && h <= 14 && (fa ? fa[0] === 0 || fa[0] === 3 : t <= 1) ? 1 : 0);', fn('roofClutter'))
        lay = fn('roofKitLay')
        self.assertIn('row = B[o + 10] > 0.5;', lay)
        self.assertIn('if (COPE < 0 || !row) return;', lay)

    def test_the_kit_takes_the_snow(self):
        # the kit's own hook keeps the weather's re-hook off it: its own snow on what faces up, and a snowy face glows no
        # more than a snowy roof after dark (a dry one as before)
        self.assertIn('if (REAL) sh.uniforms.uKitSnow = wxSurfU.uSnowAcc;', SRC)
        self.assertIn("kitGlow = mix(diffuseColor.rgb, vec3(0.06), ks) * (1.0 + 0.6 * ks); diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.84, 0.86, 0.90), ks);", SRC)
        self.assertIn("(REAL ? 'kitGlow' : 'diffuseColor.rgb')", SRC)


class Merge(unittest.TestCase):
    def test_the_debug_hook(self):
        # the facade's probe line is the first commit's, which the other branches carry beside their own lines; the pitched
        # counts join it from a line of their own after the first frame is asked for
        self.assertIn("if (window.__dbg) window.__dbg.facade = () => ({ wall: wallArtU, occ: occU.uOcc.value.toArray(), snowAsked: snowArtAsked, dayRoom: FAB_DAYROOM });", SRC)
        self.assertIn('window.__dbg.facade = () => Object.assign(f0(), { pitched: PITCH_N }); }', SRC)


if __name__ == '__main__':
    unittest.main()
