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
  projected (a stencil, never depth) and the ground vehicles out of the shadow map's movers, both manifests inlined."""
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
        s = cut('  function vehShadowMaterial(fade, blob) {', '  const VEH_SHADOWS = [];')
        self.assertIn('depthWrite: false', s)
        self.assertIn('m.stencilFunc = THREE.NotEqualStencilFunc', s)
        self.assertIn('vFragDepth = 1.0 + gl_Position.w * 0.9993', s)   # the log depth's polygon offset
        self.assertIn('const movers = !REAL && (', SRC)            # no ground vehicle redraws the depth pass
        self.assertIn('body.castShadow=!isTouch&&!REAL', SRC)

    def test_parked_lamps_dark(self):
        # a parked car's tail lamps stay out by night: its brake is written as -1 and the lamp term is gated on it
        self.assertIn('step(0.0, vCarX.y) * (1.3 * uNight + 1.6 * vCarX.y)', cut('  function carArtMaterial(kind) {', '  // ---- the vehicles\' shadows'))
        self.assertIn('p.ext.array[i * 2 + 1] = -1;', cut('  function parkedLay(now) {', '  function updateParked('))

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
