"""Round 225: the Art Museum is solid to the flight (the Nov 10 audit: "the Art Museum can be flown through").

Round 214's rule is that whatever raises a building notes its footprint and top for the flight (hitNote). The museum's
block (Round 5) noted nothing, and its OSM footprint leaves the outer districts' loop at BRIDGE_SKIP before the loop's own
note, so the eye passed through the city's postcard. Each mass is now noted where it is built (`mass`), each tile roof as
strips stepping up to its ridge (`hitGable`), and nothing that is drawn changes.

The museum's block and the flight's walls are cut from app.js and run under Node with the page's own three.js against the
shipped dem_wide.json (the block reads the hill through siteY), with a recording stand-in for the chunk:
- every draw call is the one Round 5 made (the plans in the museum's own frame, the heights over the terrace, the styles and
  colours), 21 boxes and 39 trim parts, with and without ?collide=0;
- over every 4 m cell round the hill, the column is the drawn mass: none where nothing taller than the terrace stands (the
  court, the pedestal, the steps: the hill's ground), and where a wall or a roof stands, a column no more than HIT_CLR under
  the drawn top at the cell's centre and less than one HIT_DY over it;
- the eye stops at the portico and at a wing's wall, flies on over the roofs, comes down onto the tiles and never into them,
  and is lifted out of the centre block; ?collide=0 flies through as before and notes nothing.
"""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


def cut(start, end):
    a = SRC.index(start)
    return SRC[a:SRC.index(end, a)]


MUSEUM = cut('      // --- Philadelphia Museum of Art', '      // --- Battleship New Jersey')

SCRIPT = r'''
const fs = require('fs');
const THREE = require(@@THREE@@), V3 = THREE.Vector3;
const location = { search: @@SEARCH@@ };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function polyCentroid(p) { let x = 0, z = 0; for (const q of p) { x += q[0]; z += q[1]; } return [x / p.length, z / p.length]; }
const REBUILD_OCC = [];
@@HIT@@
@@DEM@@
const DEMW = JSON.parse(fs.readFileSync(@@DEMW@@)), DEM0 = JSON.parse(fs.readFileSync(@@DEM0@@));
const DATUM = sampleDem(DEM0, 0, 0, 8.34);
const siteY = (x, z) => sampleDem(DEMW, x, z, 3.2) - DATUM;   // siteY outside the core: the wide DEM over the datum
const draws = [], lmTrim = []; let rockySite = null;
const FLOODS = false, FLOOD_N = {}, sheetOf = () => {};   // Round 251: the floodlights, off
const c = new THREE.Color(), getChunk = () => ({});
const appendBuilding = (ch, poly, y0, y1, color, st, base, ...rest) => draws.push({ poly: poly.map((q) => q.slice()), y0, y1, st, base, col: color.getHex(), rest: rest.length });
@@MUSEUM@@
// ---- the museum's own frame, as its block sets it, and its exact inverse
const O = [-3112, -2242], fu = [0.717, 0.697], pv = [-0.697, 0.717], det = fu[0] * pv[1] - pv[0] * fu[1];
const pt = (u, v) => [O[0] + fu[0] * u + pv[0] * v, O[1] + fu[1] * u + pv[1] * v];
const uv = (x, z) => { const dx = x - O[0], dz = z - O[1]; return [(dx * pv[1] - dz * pv[0]) / det, (dz * fu[0] - dx * fu[1]) / det]; };
const T = draws[0].y1;   // the terrace's deck
const r3 = (v) => Math.round(v * 1000) / 1000;
// ---- what is drawn over a point: the boxes that rise more than the eye's clearance over the deck (the deck, the paving and
// the steps are ground), and the roofs' own triangles, read from the geometry the block pushed
const walls = draws.filter((d) => d.y1 - T > 3).map((d) => { const q = d.poly.map((p) => uv(p[0], p[1])); return { u0: Math.min(...q.map((p) => p[0])), u1: Math.max(...q.map((p) => p[0])), v0: Math.min(...q.map((p) => p[1])), v1: Math.max(...q.map((p) => p[1])), top: d.y1 }; });
const tris = [];
for (const t of lmTrim) {
  if (t.geom.type !== 'BufferGeometry') continue;   // the prisms; the columns, the pedestal and Rocky are three's own shapes
  const p = t.geom.attributes.position.array;
  for (let i = 0; i < p.length; i += 9) { const a = [p[i], p[i + 1], p[i + 2]], b = [p[i + 3], p[i + 4], p[i + 5]], d = [p[i + 6], p[i + 7], p[i + 8]], den = (b[2] - d[2]) * (a[0] - d[0]) + (d[0] - b[0]) * (a[2] - d[2]); if (Math.abs(den) > 1e-6) tris.push([a, b, d, den]); }   // a gable end stands upright: no plan
}
const drawn = (x, z) => {
  let top = -Infinity; const [u, v] = uv(x, z);
  for (const w of walls) if (u > w.u0 && u < w.u1 && v > w.v0 && v < w.v1 && w.top > top) top = w.top;
  for (const [a, b, d, den] of tris) { const l0 = ((b[2] - d[2]) * (x - d[0]) + (d[0] - b[0]) * (z - d[2])) / den, l1 = ((d[2] - a[2]) * (x - d[0]) + (a[0] - d[0]) * (z - d[2])) / den, l2 = 1 - l0 - l1; if (l0 >= 0 && l1 >= 0 && l2 >= 0) { const y = l0 * a[1] + l1 * b[1] + l2 * d[1]; if (y > top) top = y; } }
  return top;
};
const colAt = (x, z) => hitTop(Math.floor(x / HIT_CELL), Math.floor(z / HIT_CELL));
// ---- every cell round the hill against what is drawn at its centre
const bad = { ghost: 0, hole: 0, low: 0, high: 0 }; let cells = 0, solid = 0, worstLow = 0, worstHigh = -Infinity;
for (let j = Math.floor((O[1] - 220) / HIT_CELL); j <= Math.floor((O[1] + 220) / HIT_CELL); j++) for (let i = Math.floor((O[0] - 220) / HIT_CELL); i <= Math.floor((O[0] + 220) / HIT_CELL); i++) {
  const x = (i + 0.5) * HIT_CELL, z = (j + 0.5) * HIT_CELL, d = drawn(x, z), col = hitTop(i, j); cells++;
  if (d === -Infinity) { if (col !== -Infinity) bad.ghost++; continue; }
  solid++;
  if (col === -Infinity) { bad.hole++; continue; }
  if (col < d - HIT_CLR - 1e-6) bad.low++; if (col >= d + HIT_DY) bad.high++;
  worstLow = Math.max(worstLow, d - col); worstHigh = Math.max(worstHigh, col - d);
}
// ---- the deck where nothing stands on it (the court between the wings, the slots beside the centre block): how far the
// hill lies under it (the eye's floor is the ground + 2.5 m)
let courtMin = Infinity, courtMax = -Infinity, deckMax = -Infinity, deckN = 0;
for (let u = -69; u <= 54; u += 2) for (let v = -94; v <= 94; v += 2) {
  const p = pt(u, v); if (drawn(p[0], p[1]) > -Infinity) continue;
  const g = T - siteY(p[0], p[1]); deckMax = Math.max(deckMax, g); deckN++;
  if (u > 15) { courtMin = Math.min(courtMin, g); courtMax = Math.max(courtMax, g); }
}
// and the steps' flights over the hill under them
let stepMax = -Infinity;
for (const d of draws.slice(13)) { const q = d.poly.map((p) => uv(p[0], p[1])), u0 = Math.min(...q.map((p) => p[0])), u1 = Math.max(...q.map((p) => p[0])); for (let u = u0 + 0.1; u < u1; u += 1) for (let v = -34; v <= 34; v += 2) { const p = pt(u, v); stepMax = Math.max(stepMax, d.y1 - siteY(p[0], p[1])); } }
// ---- flights: t seconds at a constant wish, 60 frames a second, as applyFly's lerp holds it
function fly(p, v, t) { const pos = new V3(...p), vel = new V3(...v); for (let f = 0; f < t * 60; f++) { vel.set(v[0], v[1], v[2]); hitFly(pos, vel, 1 / 60); } return { u: r3(uv(pos.x, pos.z)[0]), v: r3(uv(pos.x, pos.z)[1]), y: r3(pos.y - T), tile: r3(drawn(pos.x, pos.z) - T) }; }
const from = (u, v, y) => { const p = pt(u, v); return [p[0], T + y, p[1]]; };
const out = {
  search: location.search, T: r3(T), cells, solid, bad, worstLow: r3(worstLow), worstHigh: r3(worstHigh), hitCells: HIT.cells, notes: HIT.notes,
  draws: draws.map((d) => ({ q: d.poly.map((p) => uv(p[0], p[1]).map(r3)), y0: r3(d.y0 - T), y1: r3(d.y1 - T), st: d.st, base: r3(d.base - T), col: d.col, rest: d.rest })),
  trim: lmTrim.map((t) => t.geom.type), rocky: rockySite && uv(rockySite.x, rockySite.z).map(r3).concat(r3(rockySite.y - T)),
  centre: r3(colAt(...pt(-12.5, 0)) - T), rear: r3(colAt(...pt(-55, 60)) - T), wing: r3(colAt(...pt(9, 71.5)) - T), eaveN: r3(colAt(...pt(9, 93)) - T),
  skip: r3(colAt(-3093, -2226) - T), skipUV: uv(-3094, -2226).map(r3),   // the cell of BRIDGE_SKIP's own point: the portico's podium
  open: [pt(40, 20), pt(38, 0), pt(80, 0), pt(100, 20), pt(-10, 44), pt(30, -44), pt(70, 0), pt(-90, 0), pt(0, 110)].map((p) => colAt(p[0], p[1]) === -Infinity),
  court: [r3(courtMin), r3(courtMax)], deck: [deckN, r3(deckMax)], stepMax: r3(stepMax),
  portico: fly(from(140, 0, 14), [-60 * fu[0], 0, -60 * fu[1]], 4),          // up the Parkway's axis at the columns
  wingN: fly(from(9, -160, 12), [60 * pv[0], 0, 60 * pv[1]], 4),             // across the hill into the north wing's wall
  rearW: fly(from(-130, 30, 10), [60 * fu[0], 0, 60 * fu[1]], 4),            // from behind into the rear range
  over: fly(from(140, 0, 60), [-60 * fu[0], 0, -60 * fu[1]], 5),             // over the roofs: on its way
  ridge: fly(from(-12.5, 0, 80), [0, -30, 0], 4),                            // straight down onto the central ridge
  slope: fly(from(-12.5, 30, 80), [0, -30, 0], 4),                           // and onto its slope, 30 m off the ridge
  rearRoof: fly(from(-55, 6, 80), [0, -30, 0], 4),
  inside: fly(from(-12.5, 10, 5), [0, 0, 0], 0.1),                           // a link into the centre block: lifted out
  courtIn: fly(from(140, 0, 2.6), [-40 * fu[0], 0, -40 * fu[1]], 2.4),       // up the steps and across the court at 2.6 m over the deck: nothing in the way
  lands: HIT.lands, lifts: HIT.lifts, stops: HIT.stops, pushes: HIT.pushes,
};
console.log(JSON.stringify(out));
'''

# Round 5's boxes before the steps, in the museum's frame (u toward the steps, v across; metres over the terrace's deck):
# [u0, u1, v0, v1, foot, top, style, colour]
BOXES = [
    (-70, 55, -95, 95, -9, 0, 3, 0x6f6455),        # the terrace plinth
    (-15, 55, -45, 45, 0, 0.12, 3, 0x7d7264),      # the forecourt's paving
    (-40, 15, -40, 40, -1, 25, 1, 0x8a744c),       # the centre block
    (-70, -40, -95, 95, -1, 19, 1, 0x8a744c),      # the rear range
    (-40, 58, 48, 95, -1, 19, 1, 0x8a744c),        # the wings
    (-40, 58, -95, -48, -1, 19, 1, 0x8a744c),
    (15, 29, -17, 17, 0, 3.5, 3, 0x6f6455),        # the portico's podium, two steps
    (15, 25, -16, 16, 3.5, 7, 3, 0x6f6455),
    (12, 24, -17, 17, 19.5, 21.5, 3, 0x8a744c),    # its entablature
    (54, 64, -90.5, -52.5, 0, 6.5, 3, 0x6f6455),   # the wing ends' podiums and entablatures
    (56, 61, -89.5, -53.5, 17.5, 19, 3, 0x8a744c),
    (54, 64, 52.5, 90.5, 0, 6.5, 3, 0x6f6455),
    (56, 61, 53.5, 89.5, 17.5, 19, 3, 0x8a744c),
]


class MuseumWalls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        cls.on = cls.run_js('')
        cls.off = cls.run_js('?collide=0')

    @staticmethod
    def run_js(search):
        script = SCRIPT
        for k, v in (('@@THREE@@', json.dumps(str(ROOT / 'three.min.js'))), ('@@SEARCH@@', json.dumps(search)),
                     ('@@HIT@@', cut('  const HIT_ON = ', '  // the outer districts\' wall colours, sampled')),
                     ('@@DEM@@', cut('  function sampleDem(', '  function demAbs(')),
                     ('@@DEMW@@', json.dumps(str(ROOT / 'dem_wide.json'))), ('@@DEM0@@', json.dumps(str(ROOT / 'dem.json'))),
                     ('@@MUSEUM@@', MUSEUM)):
            script = script.replace(k, v)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if r.returncode:
            raise AssertionError(r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_nothing_drawn_changes(self):
        o = self.on
        self.assertEqual(len(o['draws']), 21)
        for d, (u0, u1, v0, v1, y0, y1, st, col) in zip(o['draws'], BOXES):
            us, vs = sorted(p[0] for p in d['q']), sorted(p[1] for p in d['q'])
            self.assertEqual((us[0], us[-1], vs[0], vs[-1]), (u0, u1, v0, v1), d)
            self.assertEqual((d['y0'], d['y1'], d['st'], d['col'], d['rest']), (y0, y1, st, col, 0), d)
            self.assertEqual(d['base'], -9 if y1 == 0 else 0, d)   # the plinth's skirt, else the deck
        steps = o['draws'][13:]
        self.assertEqual(len(steps), 8)
        for i, d in enumerate(steps):                       # the eight flights: 6.3 m runs, 7 m slabs, never rising downhill
            us, vs = sorted(p[0] for p in d['q']), sorted(p[1] for p in d['q'])
            self.assertEqual((us[0], us[-1], vs[0], vs[-1]), (round(55 + 6.3 * i, 3), round(55 + 6.3 * (i + 1) + 0.4, 3), -34, 34))
            self.assertAlmostEqual(d['y1'] - d['y0'], 7, places=3)
            self.assertEqual((d['st'], d['col'], d['base']), (3, 0x6f6455, d['y0']))
            self.assertLess(d['y1'], 0.6)
            if i:
                self.assertLessEqual(d['y1'], steps[i - 1]['y1'] - 0.2 + 1e-6)
        # the trim: six prisms (four roofs, the pediment's shell and tympanum), 20 columns, the pedestal, Rocky's twelve parts
        self.assertEqual(len(o['trim']), 39)
        self.assertEqual(o['trim'].count('BufferGeometry'), 6)
        self.assertEqual(o['rocky'], [38, 0, 0.9])           # Round 113: on the upper landing's pedestal
        # and the notes change none of it: ?collide=0 draws the same calls
        self.assertEqual(self.off['draws'], o['draws'])
        self.assertEqual(self.off['trim'], o['trim'])

    def test_columns_are_the_drawn_masses(self):
        o = self.on
        self.assertGreater(o['solid'], 1200)                 # about 21,000 sq m of walls and roofs in 16 sq m cells
        self.assertEqual(o['bad'], {'ghost': 0, 'hole': 0, 'low': 0, 'high': 0}, o)
        self.assertLessEqual(o['worstLow'], 2.5)             # HIT_CLR: an eye set down on a column is never inside what is drawn
        self.assertLess(o['worstHigh'], 1.6)                 # HIT_DY: a column rounds up, by less than a step
        self.assertEqual(o['hitCells'], o['solid'])          # and no column anywhere else
        # the ridge of the centre block (34 m over the deck: its top strip is the tiles at 31.75), the rear range's (25: 23),
        # a wing's (26: 23.67) and a wing's eave (19)
        self.assertTrue(31.75 <= o['centre'] < 31.75 + 1.6, o['centre'])
        self.assertTrue(21 <= o['rear'] < 25 + 1.6, o['rear'])
        self.assertTrue(26 - 7 / 3 <= o['wing'] < 26 - 7 / 3 + 1.6, o['wing'])
        self.assertTrue(19 <= o['eaveN'] < 19 + 1.6 + 7 / 3, o['eaveN'])
        # BRIDGE_SKIP's own point (-3094, -2225) is not the centre block: it lies on the portico's podium, 24 m toward the steps
        self.assertTrue(24 < o['skipUV'][0] < 25 and abs(o['skipUV'][1]) < 2, o['skipUV'])
        # (its podium's upper step, 7 m), and the tallest thing drawn over its cell's centre is the tympanum, whose prism runs
        # 0.3 m past the pediment's shell (to u 24.3) and is 24.3 m over the deck at its upper strip
        self.assertTrue(24.3 <= o['skip'] < 24.3 + 1.6, o['skip'])

    def test_the_hill_is_ground(self):
        o = self.on
        # the court, Rocky's pedestal, the steps, the slots between the centre block and the wings, the hill round the museum
        self.assertEqual(o['open'], [True] * 9)
        # the eye's floor is the ground + 2.5 m, and wherever the deck is open the hill lies under it by less than that
        # (0.4 to 0.9 m across the court, 2.2 m at most in the slots), so the floor already keeps the eye over the deck
        self.assertGreater(o['court'][0], 0.3)
        self.assertLess(o['court'][1], 1.0)
        self.assertGreater(o['deck'][0], 800)                # about 3,500 sq m of open deck, sampled every 2 m
        self.assertLess(o['deck'][1], 2.5)
        self.assertLess(o['stepMax'], 1.6)                   # and no flight of the steps stands more than 1.5 m over the hill
        f = o['courtIn']                                     # so the eye comes up the steps and crosses the court unhindered
        self.assertAlmostEqual(f['u'], 140 - 40 * 2.4, delta=0.05)
        self.assertAlmostEqual(f['v'], 0, delta=0.05)

    def test_the_eye_stops_at_the_walls(self):
        o = self.on
        p = o['portico']                                     # at the entablature's line (u 24), HIT_R off its cells
        self.assertTrue(24 + 3 - 2.9 <= p['u'] <= 24 + 3 + 2.9, p)
        self.assertAlmostEqual(p['y'], 14, places=3)
        w = o['wingN']                                       # the north wing's wall at v -95
        self.assertTrue(-95 - 3 - 2.9 <= w['v'] <= -95 - 3 + 2.9, w)
        r = o['rearW']                                       # the rear range's at u -70
        self.assertTrue(-70 - 3 - 2.9 <= r['u'] <= -70 - 3 + 2.9, r)
        self.assertLess(o['over']['u'], -100)                # 60 m over the deck: across the whole museum
        self.assertAlmostEqual(o['over']['y'], 60, places=3)
        self.assertGreater(o['stops'] + o['pushes'], 0)

    def test_the_eye_lands_on_the_tiles(self):
        o = self.on
        for k in ('ridge', 'slope', 'rearRoof'):
            f = o[k]
            self.assertGreaterEqual(f['y'], f['tile'], (k, f))               # never inside the roof
            self.assertLess(f['y'], f['tile'] + 2.5 + 2.5 + 1.6, (k, f))     # a strip's step, the clearance and the rounding
        self.assertAlmostEqual(o['ridge']['tile'], 34, delta=0.01)
        self.assertAlmostEqual(o['slope']['tile'], 34 - 9 * 30 / 40, delta=0.01)
        self.assertGreater(o['lands'], 0)
        f = o['inside']                                      # a link that lands inside the centre block is lifted onto its roof
        self.assertGreaterEqual(f['y'], f['tile'])
        self.assertGreater(o['lifts'], 0)

    def test_escape_hatch(self):
        o = self.off
        self.assertEqual((o['hitCells'], o['notes']), (0, 0))
        self.assertLess(o['portico']['u'], -90)              # straight through, as before Round 214
        self.assertAlmostEqual(o['rearW']['u'], -130 + 60 * 4, delta=0.05)
        self.assertAlmostEqual(o['ridge']['y'], 80 - 30 * 4, delta=0.01)

    def test_each_mass_is_noted_where_it_is_built(self):
        # one helper draws a box and notes the same quad, so the two cannot drift; the roofs note their own prisms
        self.assertIn('const mass = (u0, u1, v0, v1, y0, y1, st) => { const q = quad(u0, u1, v0, v1); appendBuilding(chk, q, y0, y1, c, st, T); hitNote(q, y1); };', MUSEUM)
        self.assertIn('hitGable(alongU ? (l, x) => pt(cu + l, cv + x) : (l, x) => pt(cu - x, cv + l), -hl, hl, hw, eave, apex);', MUSEUM)
        self.assertEqual(MUSEUM.count('mass('), 9)           # nine calls for eleven boxes: the wing ends' run twice
        self.assertEqual(MUSEUM.count('appendBuilding('), 4)   # the plinth, the paving, the flights and mass's own
        self.assertEqual(self.on['notes'], 11 + 4 + 3 + 3 + 3 + 3 + 2)   # eleven boxes and the six prisms' strips (9, 6, 7, 7, 6 and 4.6 m of rise)
        # its footprint still leaves the outer districts' loop before the loop's note: the block's notes are the only ones
        self.assertIn('[-3094, -2225, 130]];', SRC)
        loop = cut('      if (BRIDGE_SKIP.some(q => Math.hypot(cx - q[0], cz - q[1]) < q[2])) continue;', '      hitNote(poly, base + h);   // the flight\'s walls (Round 214)')
        self.assertNotIn('hitNote(', loop)


if __name__ == '__main__':
    unittest.main()
