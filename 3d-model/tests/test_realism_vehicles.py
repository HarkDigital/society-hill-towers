"""The realism pass's vehicles (Oct 12, Mike: "please do anything necessary to make this look more photo realistic and less
cartoony"): the generated cars and liveries, their projected shadows, the parked cars, the lamps and the street furniture.

- vehicle_art.json: the six car kinds in CAR_MODELS's order with 40-station profiles and two wheels each, the six transit
  kinds, every rect inside its atlas, the masks lossless (a lossy mask bled the lamp channel into red outlines by night);
- the lofted cars are their kinds' real sizes on a computer and a phone, inside a triangle budget, every uv inside the atlas;
- the parked cars line both kerbs of a one-way street and a two-way secondary at the kerb (hw - 1.12 m), leave a two-way
  residential street's lanes alone, keep off the junction and inside the half-mile rule, all of them on the first lay (the
  far kerb's cars in the next cell once came only with the second), their lamps dark by night, clear of the hydrants;
- a signalised junction gets a pole on each corner and a head toward each street, the streets in two groups; a stop sign
  stands at its driver's right facing them; a hydrant in the carriageway is pushed to the kerb, and the hydrants the map
  lacks stand at the kerb's back;
- the wiring: everything behind REAL with its own escape (?vart=0, ?parked=0, ?furniture=0, ?carpools=0), the shadows
  projected (a stencil, never depth) and the ground vehicles out of the shadow map's movers, both manifests inlined.

The review before the merge (Oct 13): the headlights' pools from a call that runs under the realistic lamps and only on the
paved surfaces (a green has no sixteenth texture unit to spare); the vehicles' lamp share from their own patch, never a text
replace on another patch's output; nothing that moves casts into a depth pass no mover redraws; the parked rows clear of
every moving lane; the sun's shade reading the shadow map where it lands, both shades fading with the fog, none flattened
off a deck or under a train; the moving traffic's far copies, and no empty mesh drawn."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / 'app.js').read_text()


def cut(a, b):
    i = SRC.index(a)
    return SRC[i:SRC.index(b, i)]


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((ROOT / 'vehicle_art.json').read_text())

    def test_cars(self):
        kinds = self.m['cars']['kinds']
        self.assertEqual([k['id'] for k in kinds], ['compact', 'sedan', 'wagon', 'suv', 'pickup', 'van'])
        for k in kinds:
            self.assertEqual(len(k['prof']), self.m['stations'])
            self.assertTrue(all(len(r) == 5 for r in k['prof']))
            self.assertEqual(len(k['wheels']), 2, k['id'])
            (x0, r0), (x1, r1) = k['wheels']
            self.assertTrue(0.1 < x0 < 0.35 and 0.65 < x1 < 0.9, k['id'])
            self.assertTrue(0.6 < k['paintRef'] < 0.95, k['id'])
            for v in ('side', 'top', 'front', 'rear'):
                r = k[v]
                self.assertTrue(0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1, (k['id'], v))

    def test_transit(self):
        kinds = {k['id']: k for k in self.m['transit']['kinds']}
        self.assertEqual(set(kinds), {'bus', 'trolley', 'acs64', 'acela', 'amfleet', 'patco'})
        for k in kinds.values():
            for v in ('side', 'roof'):
                r = k[v]
                self.assertTrue(0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1, (k['id'], v))

    def test_masks_lossless_and_halves(self):
        bake = (ROOT / 'bake_vehicle_art.py').read_text()
        self.assertIn("name + '-mask', 'WEBP', lossless=True", bake)
        for s in ('cars', 'transit'):
            for f in ('atlas', 'atlasHalf', 'mask', 'maskHalf'):
                self.assertTrue((ROOT / self.m[s][f]).exists(), (s, f))
        for f in ('side', 'sideHalf', 'end', 'endHalf'):
            self.assertTrue((ROOT / self.m['containers'][f]).exists(), f)


@unittest.skipUnless(shutil.which('node'), 'Node unavailable')
class Runtime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = subprocess.run(['node', str(ROOT / 'tests/vehicles_checks.js')], capture_output=True, text=True, timeout=120)
        if run.returncode:
            raise AssertionError(run.stderr or run.stdout)
        cls.r = json.loads(run.stdout)

    def test_cars_are_their_real_size(self):
        for key, budget in (('cars', 760), ('carsTouch', 420)):
            for c in self.r[key]:
                self.assertTrue(c['finite'] and c['uvOk'], c['name'])
                self.assertAlmostEqual(c['len'], c['l'], delta=0.02)
                self.assertAlmostEqual(c['wid'], c['w'], delta=0.04)
                self.assertAlmostEqual(c['top'], c['h'], delta=0.02)
                self.assertAlmostEqual(c['bottom'], 0, delta=0.01)
                self.assertLessEqual(c['tris'], budget, c['name'])
                self.assertLessEqual(c['farTris'], 200, c['name'])
                self.assertEqual(c['parts'], [0, 1, 2], c['name'])   # body, tyre treads, underside

    def test_parked_cars(self):
        p = self.r['parked']
        self.assertGreater(p['oneway'], 40)            # 200 m of one-way street, both kerbs
        self.assertGreater(p['secondary'], 30)         # the two-way secondary, both kerbs
        self.assertEqual(p['twoWayRes'], 0)            # the two-way residential street's lanes fill its 7 m
        self.assertEqual(p['onewayOffsets'], [2.38])   # at the kerb: 3.5 - 1.12
        self.assertEqual(p['secondaryOffsets'], [4.38])
        self.assertTrue(p['secondaryFacing'])          # a two-way street's cars face their own side's way
        self.assertGreater(p['nearestToJunction'], 12)  # trimmed off the junction
        self.assertLessEqual(p['farthest'], min(p['r'], 804.67))
        self.assertEqual(p['lods'], [0, 1])            # the near ring whole, the rest their far copies
        self.assertGreater(p['hydrants'], 3)            # the hydrants the map lacks, about one every 95 m
        self.assertGreater(p['nearestToHydrant'], 4.5)  # and every car keeps its 15 feet

    def test_parked_rows_clear_the_moving_lanes(self):
        c = self.r['clearance']
        self.assertEqual(c['nBad'], 0, c['bad'])          # every class, both kinds of street, 2 to 9 m: the widest van's width clear
        self.assertGreater(c['parkedCases'], 400)
        self.assertGreater(c['oneSide'], 0)               # a narrow one-lane one-way street parks one kerb
        self.assertEqual(c['tertiaryHw45'], 2)            # a two-way tertiary at its drawn 4.5 m still parks both
        self.assertEqual(c['offw4'], 1.3)
        t = self.r['tertiary']
        self.assertGreater(t['n'], 60)
        self.assertEqual(t['offsets'], [3.38])            # 4.5 - 1.12
        self.assertEqual(t['sides'], [-1, 1])
        self.assertGreaterEqual(t['offsets'][0] - t['lane'], 2.05)
        n = self.r['narrowOneWay']
        self.assertGreater(n['n'], 25)
        self.assertEqual(len(n['z']), 1)                  # one kerb
        self.assertAlmostEqual(abs(n['z'][0]), 1.68)      # 2.8 - 1.12
        self.assertAlmostEqual(abs(n['laneZ']), 1.07)     # the moving car keeps to the other half
        self.assertLess(n['z'][0] * n['laneZ'], 0)
        self.assertGreaterEqual(abs(n['z'][0] - n['laneZ']), 2.05)
        self.assertLessEqual(abs(n['laneZ']) + 1.025, n['hw'])   # and stays on the street

    def test_vehicle_lamp_share_lands(self):
        L = self.r['lampShare']
        self.assertEqual((L['car'], L['bus'], L['train']), ('0.35', '0.35', '0.35'))
        self.assertTrue(L['uniforms'])
        self.assertEqual(L['once'], 1)

    def test_headlight_pools_only_on_paved_surfaces(self):
        m = self.r['carMap']
        self.assertTrue(m['on'])
        self.assertEqual((m['road'], m['lot'], m['deck'], m['lawn']), (1, 1, 1, 0))

    def test_shades(self):
        sh = self.r['shades']
        self.assertEqual((sh['sunType'], sh['blobType']), ('ShadowMaterial', 'MeshBasicMaterial'))
        self.assertTrue(sh['sunFog'] and sh['blobFog'])
        for k in ('maskRead', 'maskWhere', 'shadowAtShade', 'logDepth', 'logOrder', 'fog', 'fogAfter', 'deck'):
            self.assertTrue(sh[k], k)
        self.assertFalse(sh['blobDeck'])
        self.assertEqual(sh['outerOff'], 0)   # outside the core the mask waits for the outer streets to receive

    def test_traffic_far_copies_and_shade_reach(self):
        L = self.r['lod']
        self.assertEqual((L['nearN'], L['farN']), (1, 2))   # 40 m whole; 400 m and 1,200 m the far copy
        self.assertEqual(L['farXs'], [400, 1200])           # the one past the shades' reach written last
        self.assertEqual((L['nearShadeN'], L['farShadeN']), (1, 1))
        self.assertEqual(L['farShades'], [{'n': 1, 'vis': True}, {'n': 1, 'vis': True}])
        self.assertEqual(L['emptyShades'], [{'n': 0, 'vis': False}, {'n': 0, 'vis': False}])
        self.assertEqual(L['visible'], {'near': True, 'far': True, 'empty': False})
        self.assertEqual((L['nearTris'], L['farTris']), (684, 180))
        self.assertEqual((L['kind3Near'], L['kind3Far']), (0, 1))

    def test_furniture_geometry_is_plain_triangles(self):
        g = self.r['furnGeom']
        self.assertEqual(g['indexed'], [])
        self.assertEqual(g['tris']['stop'], 28)   # the post's box (12), the sign's two octagons (8 each): every part's index expanded
        self.assertEqual(g['tris']['bus'], 16)    # the post's box and the plate's two faces
        for k, m in g['longest'].items():
            self.assertLessEqual(m, 4.9, k)       # no triangle longer than its tallest part

    def test_furniture(self):
        f = self.r['furniture']
        self.assertEqual(sorted(f['poles']), [[-7.1, -7.1], [-7.1, 7.1], [7.1, -7.1], [7.1, 7.1]])   # a corner each, past the kerb
        self.assertEqual(f['heads'], 8)
        self.assertTrue(f['headsOutward'])             # each faces the cars coming up its street
        self.assertEqual(f['groups'], [0, 1])
        self.assertEqual(f['stop'], [{'x': 7.2, 'z': 80, 'fx': 0, 'fz': 1}])   # the driver's right, facing them
        # a wide street crossing a narrow one, the signal mapped up an approach: the poles at the corners of the streets as
        # drawn (1.6 m behind each kerb: 8 + 1.6 off the wide one, 5.5 + 1.6 off the narrow one), round where they meet
        self.assertEqual(self.r['furnitureWide']['poles'], [[-7.1, -9.6], [-7.1, 9.6], [7.1, -9.6], [7.1, 9.6]])
        self.assertIn({'x': 100, 'z': 6.2}, f['hyd'])   # the mapped one out of the carriageway
        self.assertEqual(f['hydKerb'], [6.05, 6.2])     # the made ones at the kerb's back (hw + 0.55)


class Wiring(unittest.TestCase):
    def test_behind_real_with_escapes(self):
        self.assertIn("const VART = REAL && typeof VEHICLE_ART !== 'undefined' && VEHICLE_ART && VEHICLE_ART.cars && !/[?&]vart=0\\b/.test(location.search)", SRC)
        self.assertIn("on: REAL && !TIER2 && !/[?&]parked=0\\b/.test(location.search)", SRC)
        self.assertIn("/[?&]furniture=0\\b/", SRC)
        self.assertIn("/[?&]carpools=0\\b/", SRC)
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("VEHICLE_ART", text_of("vehicle_art.json", "null"))', b)
        self.assertIn('const("STREET_FURN", text_of("street_furniture.json", "null"))', b)
        self.assertIn('"vehicle_art.json"', b)

    def test_shadows_projected(self):
        s = cut('  function vehShadowMaterial(fade, blob, deck) {', '  const VEH_SHADOWS = [];')
        self.assertIn('depthWrite: false', s)
        self.assertIn('m.stencilFunc = THREE.NotEqualStencilFunc', s)
        self.assertIn('vFragDepth = 1.0 + gl_Position.w * 0.9993', s)   # the log depth's polygon offset
        self.assertIn('const movers = !REAL && (', SRC)            # no ground vehicle redraws the depth pass
        self.assertIn('body.castShadow=!isTouch&&!REAL', SRC)
        # the trains keep the contact shade alone (a flattened shadow hung off the bridges)
        self.assertIn('vehShadowsFor(m, null, vehBlobGeom(AMTRAK_LEN[kind], 3.1), false);', SRC)
        self.assertIn('vehShadowsFor(patcoCar, null, vehBlobGeom(PATCO_LEN, PATCO_W), false);', SRC)
        # the shades' counts and visibility are set once every vehicle's count is, never by an empty draw
        u = cut('  function updateTraffic(now,dt) {', '  function trafficStep(now,dt) {')
        self.assertLess(u.index('trafficStep(now,dt);'), u.index('vehShadowSync();'))
        self.assertNotIn('onBeforeRender', cut('  function vehShadowsFor(', '  function vehShadowUpdate() {'))

    def test_nothing_moving_casts_into_an_unrefreshed_depth_pass(self):
        # REAL takes every ground vehicle out of the movers, so the depth pass is redrawn only on a box move, a caster
        # set's change or the sun's step: a ship's stacks or the ferry casting into it froze astern of them (review)
        self.assertIn('shipStacks.castShadow = false;', SRC)
        self.assertIn('FERRY.mesh.castShadow = !isTouch && !REAL;', SRC)
        self.assertIn('m.castShadow = !isTouch && !REAL;', cut('  function amtrakInit() {', '  function patcoInit() {'))
        self.assertIn('patcoCar.castShadow = !isTouch && !REAL;', SRC)
        # the roof kit, relaid ahead of a moving eye, asks for its own redraw
        self.assertIn('if (REAL && !shadowFrozen && (ROOFKIT.cam.x !== ROOFKIT.shX || ROOFKIT.cam.z !== ROOFKIT.shZ))', SRC)

    def test_headlight_pools_hook(self):
        # called at the end of the surface patch, after the lamps' (which return first under the realistic lamps), and
        # never from inside lampLightPatch
        f = cut('  function surfTexPatch(shader, opt) {', '\n  }\n')
        self.assertIn("carMapPatch(shader, 'cameraPosition - vViewPosition * mat3(viewMatrix)');", f)
        self.assertLess(f.index('lampLightPatch(shader,'), f.index('carMapPatch(shader,'))
        self.assertNotIn('carMapPatch', cut('  function lampLightPatch(shader, worldExpr, mode) {', '  function surfTexPatch(shader, opt) {'))
        self.assertNotIn("'float lk = 0.35 *'", SRC)   # the old text replace is gone

    def test_parked_lamps_dark(self):
        # a parked car's tail lamps stay out by night: its brake is written as -1 and the lamp term is gated on it
        self.assertIn('step(0.0, vCarX.y) * (1.3 * uNight + 1.6 * vCarX.y)', cut('  function carArtMaterial(kind) {', '  // ---- the vehicles\' shadows'))
        self.assertIn('p.ext.array[i * 2 + 1] = -1;', cut('  function parkedLay(now) {', '  function updateParked('))

    def test_paint_fills_the_masks_gaps(self):
        # a light texel between the mask's paint, glass and lamps is the white car's body and takes the paint (a dark car
        # drew pale outlines round its windows and arches, brightest under a streetlamp); a dark one keeps its own
        c = cut('  function carArtMaterial(kind) {', '  // ---- the vehicles\' shadows')
        self.assertIn("float vGap = clamp(1.0 - vmk.r - vmk.g - vmk.b, 0.0, 1.0) * smoothstep(0.2, 0.45,", c)
        self.assertIn('vPaintM = min(1.0, vmk.r + vGap) * vBody', c)

    def test_ship_houses_behind_real(self):
        b = cut('    const bridge = (cx, w, h, y, d) => {', '    const funnel = ')
        self.assertLess(b.index('if (!REAL) return;'), b.index('const rows = '))

    def test_aircraft_have_instance_colour(self):
        # r149 picks a shared material's program by instancing, never by instance colour: every user of the vehicles' body
        # material carries an instanceColor, or it draws with a program that reads the missing one as black
        b = cut('  function flightsInit() {', '  function flightPoll() {')
        self.assertIn('for (const m of [flightMesh, heliMesh, heliRotor]) { for (let k = 0; k < FLIGHT_CAP; k++) m.setColorAt(k, _sc.setRGB(1, 1, 1));', b)
        for a, z in (('  function shipsInit() {', '  const shipDecoder'), ('  function ferryInit() {', '  function ferryCard('), ('    indegoSolid = new THREE.InstancedMesh(', '    indegoSolid.castShadow')):
            self.assertIn('setColorAt(', cut(a, z))

    def test_textures_uploaded_once(self):
        # the vehicles' two atlases and their masks (vartSet), the ships' container textures and the street signs' canvas,
        # each uploaded once and its source let go (test_memory_cuts counts every use)
        self.assertEqual(cut('  function vartSet(name) {', '  // the section').count('freeTexOnUpload(t);'), 2)
        self.assertIn('return freeTexOnUpload(t);', cut('  function furnSignTexture() {', '  function furnGeoms() {'))

    def test_near_rule(self):
        self.assertIn('R = Math.min(PARKED.r, NEAR_R)', cut('  function parkedLay(now) {', '  function updateParked('))
        self.assertIn('R = Math.min(FURN.r, NEAR_R)', cut('  function furnLay() {', '  function updateFurniture('))

    def test_no_dashes_in_strings(self):
        for a, b in (('  // ---- the vehicles\' own faces', '  function trafficCreateFleet() {'), ('  // ---- parked cars', '  function trafficPrepareGraph(runs) {')):
            block = cut(a, b)
            for line in block.splitlines():
                code = line.split('//')[0]
                self.assertNotIn('—', code)
                self.assertNotIn('·', code)


if __name__ == '__main__':
    unittest.main()
