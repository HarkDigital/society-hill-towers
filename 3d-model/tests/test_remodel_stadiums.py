"""Round 195: the sports complex remodelled (Mike: "Remodel ... The stadiums/arena").

The section ('// ---- the sports complex remodelled') is run under Node with the vendored three.js and the real manifest, the
venues built from the arena's OSM outline, and what it makes is checked against the round's budget and rules:

- three venues, each a near level (the shell and the seats) and a far one, the fields drawn at both: at most three meshes
  near and two far a venue, the triangles under the stated budget (near 12,000 / 6,000 / 3,000 for the ballpark, the Linc
  and the arena; far 2,000 each), every position finite;
- every vertex stream a multiple of 4 bytes (Round 158: aCol and aLit four normalized bytes, never three), the index in 16
  bits;
- the ballpark's field fills its outline (the triangles' area is the ring's: a missing patch showed the ground through it);
- the Linc's field frame: the rules' 120 by 53 1/3 yards are the shader's numbers, and the numbers read from their own
  sideline (its right is -u);
- the arena's eyebrow, its struts and its drum's wash carry the slot the wide loop dealt it (Round 84's skyline lights);
- the integration: ?real=0 and ?venues=0 keep Round 92's builders (buildStadium, buildArenaOld), the arena's slot is dealt
  where the loop meets its record whichever builds it, a failed remodel puts Round 92's back, the frame steps the levels,
  no new program writes gl_FragDepth, and no program samples more than four of its own textures;
- the art: eight wall strips in VEN_STRIP's order, the half copies, the seat tile lossless (it is data, not a picture).

The review's round (Round 195's fixes) adds:
- the warning track: the outfield fence and the foul ground's wall reach the field's shader (nothing filled the fence's
  uniform at first, and the track shrank to a disc at home plate), their arrays sized as the shader loops them;
- the walls stand on their feet (the first cut read each strip from its top: every wall stood on its cornice), the panes
  are the atlas's alpha (the bake's mask, never under 128 for the wall), and the lit share, rows and bays come per strip;
- the lines box-filtered (a ten centimetre line never covers more of a pixel than its width), the numbers faded out;
- no floodlight on the faces seen from outside where the stands end (the ballpark's two ends, the Linc's steps), each end
  its own polygons in brick, concrete and steel;
- the Linc's office block in its own strip, the ballpark's gates in theirs, open bays between the pavilions;
- the arena's roof one smooth dome: no position on it carries two normals (the flat cap was an oculus from the air).
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
A = SRC.index('  // ---- the sports complex remodelled (Round 195')
B = SRC.index('  // ---- the landmark rebuilds (Round 161')
SECTION = SRC[A:B]
# the arena's outline (OSM way 25312366, the scene frame), as the wide loop hands it over
ARENA = [[-2233.2, 4862.1], [-2246.5, 4907.4], [-2255.3, 4905.7], [-2257.9, 4917.9], [-2253.7, 4960.6], [-2268.6, 4962.2], [-2269.9, 4965.6],
         [-2282.0, 4963.4], [-2286.2, 4987.9], [-2315.5, 4981.8], [-2338.7, 4977.5], [-2370.7, 4974.2], [-2368.3, 4961.4], [-2363.8, 4961.5],
         [-2362.5, 4956.7], [-2391.3, 4951.0], [-2388.7, 4938.3], [-2401.9, 4935.6], [-2396.3, 4881.2], [-2390.8, 4842.2], [-2384.3, 4835.6],
         [-2374.6, 4839.0], [-2372.5, 4846.4], [-2369.7, 4828.3], [-2349.6, 4830.8], [-2340.7, 4832.8], [-2325.9, 4826.4], [-2311.0, 4825.0],
         [-2296.4, 4827.1], [-2269.9, 4831.9], [-2271.5, 4836.9], [-2255.9, 4839.7], [-2254.6, 4830.2], [-2228.2, 4834.8]]

HARNESS = r'''
const THREE = require(THREE_PATH), V3 = THREE.Vector3;
const STADIUM_ART = MANIFEST;
const REAL = true, isTouch = false, TIER2 = false, location = { search: '' };
const nightUniform = { value: 0 }, PERF = { failed: [] };
const architecturalBloom = (m) => m, anisoOf = (n) => n, freeTexOnUpload = (t) => t, artImage = () => Promise.resolve(null), artSrc = (a) => a;
const ctx2d = new Proxy({}, { get: (_, k) => k === 'createLinearGradient' ? () => ({ addColorStop() {} }) : () => {}, set: () => true });
const document = { createElement: () => ({ getContext: () => ctx2d, width: 0, height: 0 }) };
const groundMeshY = (x, z) => 3 + 0.002 * (x + 1900) + 0.001 * (z - 4600), siteY = () => 3;
const groupCity = { kids: [], add(m) { this.kids.push(m); }, remove() {} };
const pendingUpload = [], freeOnUpload = () => {}, NO_SOW_RINGS = [], NO_SOW_RING_BB = [], REBUILD_OCC = [];
const rbBox = (ring) => { let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9; for (const q of ring) { x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); z0 = Math.min(z0, q[1]); z1 = Math.max(z1, q[1]); } return [x0, x1, z0, z1]; };
const camera = { position: new V3(-1900, 400, 3900) };
SECTION
const themeParts = [], themeSheets = [], flood = [];
const ok = venuesBuildSafe({ stadia: [{ def: { baseball: true } }, { def: { baseball: false } }], arena: { poly: ARENA, base: 3, slot: 3 },
  themeParts, themeSheets, flood, sheetOf: (geom, slot, w, grad) => themeSheets.push({ geom, slot, w, grad }) });
const meshes = groupCity.kids.map((m) => {
  const g = m.geometry, at = {};
  for (const k in g.attributes) { const a = g.attributes[k]; at[k] = { bytes: a.array.BYTES_PER_ELEMENT * a.itemSize, size: a.itemSize, norm: !!a.normalized, type: a.array.constructor.name }; }
  let finite = true; for (const v of g.attributes.position.array) if (!Number.isFinite(v)) { finite = false; break; }
  return { name: m.name, tris: g.index.count / 3, index: g.index.array.constructor.name, at, finite, cast: m.castShadow, stand: !!m.userData.occStandIn };
});
// the ballpark's field: the triangles' area against its ring's
const fieldM = groupCity.kids.find((m) => m.name === 'venue-cbp-field'), fg = fieldM.geometry, P = fg.attributes.position.array, I = fg.index.array;
let triA = 0;
for (let i = 0; i < I.length; i += 3) { const a = I[i] * 3, b = I[i + 1] * 3, c = I[i + 2] * 3; triA += Math.abs((P[b] - P[a]) * (P[c + 2] - P[a + 2]) - (P[c] - P[a]) * (P[b + 2] - P[a + 2])) / 2; }
const ctl = CBP.control.flatMap((q, j, a) => j + 1 < a.length ? [q, [(q[0] + a[j + 1][0]) / 2, (q[1] + a[j + 1][1]) / 2]] : [q]);
const ring = ctl.concat([[72, 76]], CBP.fence.slice().reverse(), [[72, -76]]);
let ringA = 0; for (let i = 0; i < ring.length; i++) { const p = ring[i], q = ring[(i + 1) % ring.length]; ringA += p[0] * q[1] - q[0] * p[1]; }
// the arena's roof: every position over the eyebrow's lip with the normals it carries
const arenaM = groupCity.kids.find((m) => m.name === 'venue-arena-shell'), ag = arenaM.geometry, AP = ag.attributes.position.array, AN = ag.attributes.normal.array;
const y0a = VEN.list.find((V) => V.id === 'arena').y0, byPos = new Map();
for (let i = 0; i < AP.length / 3; i++) {
  if (AP[i * 3 + 1] - y0a < 35.8) continue;
  const k = AP.slice(i * 3, i * 3 + 3).map((x) => x.toFixed(2)).join(','), nk = AN.slice(i * 3, i * 3 + 3).map((x) => x.toFixed(3)).join(',');
  if (!byPos.has(k)) byPos.set(k, new Set()); byPos.get(k).add(nk);
}
const roofSplit = [...byPos.values()].filter((v) => v.size > 1).length;
// the shell's strips by venue: how many vertices wear each (aCol.a 3, a wall of the atlas; aLit.a its strip), and the
// floodlight (aLit.rgb) on the matte faces
const stripsOf = (nm) => { const g = groupCity.kids.find((m) => m.name === nm).geometry, C = g.attributes.aCol.array, L = g.attributes.aLit.array, o = {}; for (let i = 0; i < C.length / 4; i++) if (C[i * 4 + 3] === 3) o[L[i * 4 + 3]] = (o[L[i * 4 + 3]] || 0) + 1; return o; };
console.log(JSON.stringify({ ok, err: VEN.err, probe: venuesProbe(), meshes, flood: flood.length / 3, roofSplit, roofPositions: byPos.size,
  fence: venU.uVenFence.value.map((q) => [q.x, q.y]), foul: venU.uVenFoul.value.map((q) => [q.x, q.y]), cbpFence: CBP.fence, cbpFoul: cbpFoul(),
  cbpStrips: stripsOf('venue-cbp-shell'), lincStrips: stripsOf('venue-linc-shell'), arenaStrips: stripsOf('venue-arena-shell'), winGlsl: VEN_WIN_GLSL, rings: REBUILD_OCC.length, sow: NO_SOW_RINGS.length,
  theme: themeParts.map((p) => p.slot), sheets: themeSheets.map((s) => [s.slot, s.grad]), fieldArea: triA, ringArea: Math.abs(ringA) / 2,
  strips: VEN_STRIP, classes: [0, 6, 12, 23, 24, 30, 41, 42, 48, 59, 60, 66, 71].map((j) => lincClass(j)) }));
'''


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        code = (HARNESS.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js')))
                .replace('MANIFEST', (ROOT / 'stadium_art.json').read_text())
                .replace('ARENA', json.dumps(ARENA)).replace('SECTION', SECTION))
        r = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=60)
        if r.returncode:
            raise AssertionError(r.stderr[-3000:])
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])
        cls.by = {m['name']: m for m in cls.out['meshes']}

    def test_it_builds_three_venues(self):
        self.assertTrue(self.out['ok'], self.out['err'])
        self.assertEqual([v['id'] for v in self.out['probe']['venues']], ['cbp', 'linc', 'arena'])
        for m in self.out['meshes']:
            self.assertTrue(m['finite'], m['name'])

    def test_the_budget(self):
        near = {'cbp': 12000, 'linc': 6000, 'arena': 3000}
        for v in self.out['probe']['venues']:
            t = v['tris']
            self.assertLess(t.get('shell', 0) + t.get('seats', 0) + t.get('field', 0), near[v['id']], v)
            self.assertLess(t['far'] + t.get('field', 0), 2000, v)
            self.assertLessEqual(v['draws']['near'], 3)
            self.assertLessEqual(v['draws']['far'], 2)

    def test_streams_are_four_byte_aligned(self):
        for m in self.out['meshes']:
            self.assertEqual(m['index'], 'Uint16Array', m['name'])
            for k, a in m['at'].items():
                self.assertEqual(a['bytes'] % 4, 0, (m['name'], k, a))
            self.assertEqual((m['at']['aCol']['type'], m['at']['aCol']['size'], m['at']['aCol']['norm']), ('Uint8Array', 4, True))
            self.assertEqual((m['at']['aLit']['type'], m['at']['aLit']['size'], m['at']['aLit']['norm']), ('Uint8Array', 4, True))

    def test_levels_and_shadows(self):
        for vid in ('cbp', 'linc', 'arena'):
            self.assertTrue(self.by['venue-%s-shell' % vid]['stand'], 'the near level gives the pins\' capture the far one')
            self.assertTrue(self.by['venue-%s-shell' % vid]['cast'])
            self.assertTrue(self.by['venue-%s-far' % vid]['cast'])
        self.assertFalse(self.by['venue-cbp-field']['cast'])

    def test_the_ballpark_field_fills_its_outline(self):
        self.assertAlmostEqual(self.out['fieldArea'], self.out['ringArea'], delta=1.0)
        self.assertGreater(self.out['ringArea'], 12000)

    def test_the_arena_keeps_its_slot(self):
        self.assertGreater(len(self.out['theme']), 100)          # the eyebrow (64) and the struts
        self.assertEqual(set(self.out['theme']), {3})
        self.assertEqual(self.out['sheets'], [[3, 1]])            # the drum's uplight wash

    def test_floods_and_ground(self):
        self.assertGreaterEqual(self.out['flood'], 40)            # the towers' heads, the board's tower, the Linc's edges
        self.assertEqual(self.out['rings'], 3)
        self.assertEqual(self.out['sow'], 3)

    def test_the_warning_track_reaches_the_shader(self):
        # the fence's uniform and the foul ground's are filled from the ballpark's own outlines (the first cut left the fence's
        # at the origin and the track was a 4.6 m disc at home plate)
        self.assertEqual(self.out['fence'], self.out['cbpFence'])
        self.assertEqual(len(self.out['foul']), 17)
        self.assertEqual(self.out['foul'], self.out['cbpFoul'])
        self.assertTrue(all(abs(x) + abs(y) > 50 for x, y in self.out['fence']))
        # the arrays as the shader declares and loops them
        self.assertIn('uniform vec2 uVenFence[8]; uniform vec2 uVenFoul[17];', SECTION)
        self.assertIn("for (int i = 0; i < 7; i++) wt = min(wt, venSeg(p, uVenFence[i], uVenFence[i + 1]));", SECTION)
        self.assertIn("for (int i = 0; i < 16; i++) wt = min(wt, venSeg(p, uVenFoul[i], uVenFoul[i + 1]));", SECTION)

    def test_the_arena_roof_is_one_smooth_dome(self):
        self.assertGreater(self.out['roofPositions'], 300)
        self.assertEqual(self.out['roofSplit'], 0)
        self.assertNotIn('K.cap(drum(lipS * 0.4)', SECTION)

    def test_each_venue_wears_its_strips(self):
        st = {int(k): v for k, v in self.out['cbpStrips'].items()}
        self.assertEqual(set(st), {0, 7})                          # the brick and the gates' atriums
        lt = {int(k): v for k, v in self.out['lincStrips'].items()}
        self.assertEqual(set(lt), {1, 2, 6})                       # the glazed sides, the braced ends, the office block
        self.assertGreater(lt[6], 40)
        self.assertEqual({int(k) for k in self.out['arenaStrips']}, {3, 4, 5})
        # one entry a strip in the panes' expression, eight strips
        self.assertEqual(self.out['winGlsl'].count('vec4('), 9)

    def test_linc_classes(self):
        self.assertEqual(self.out['classes'], ['E', 'C', 'S', 'S', 'C', 'E', 'E', 'C', 'S', 'S', 'C', 'E', 'E'])


class Integration(unittest.TestCase):
    def test_the_old_venues_stay_for_real0_and_venues0(self):
        self.assertIn("const VENUES_ON = REAL && !/[?&]venues=0\\b/.test(location.search);", SECTION)
        self.assertIn('if (!(VENUES_ON && venuesBuildSafe({ stadia, arena: venArenaRec, themeParts, themeSheets, sheetOf, flood }))) {\n      for (const sd of stadia) buildStadium(sd);\n      if (venArenaRec) buildArenaOld(', SRC)
        self.assertIn('    const buildArenaOld = (poly, base, chk, aslot) => {', SRC)

    def test_the_arena_slot_is_dealt_in_the_loop(self):
        i = SRC.index('      if (t === 9) {   // the Xfinity Mobile Arena')
        block = SRC[i:i + 500]
        self.assertLess(block.index('const aslot = themeSlotN++ % 4;'), block.index('if (VENUES_ON) venArenaRec'))
        self.assertIn('else buildArenaOld(poly, base, chk, aslot);', block)

    def test_the_frame_and_the_probe(self):
        self.assertIn('    venuesStep();   // Round 195', SRC)
        self.assertIn('venues: venuesProbe, ', SRC)

    def test_walls_stand_on_their_feet(self):
        # sv 0 is a wall's foot: the strip's last row (the first cut read it from the top)
        self.assertIn("'  float v = (st + uVenStrip.y + (1.0 - sv) * (1.0 - 2.0 * uVenStrip.y)) / uVenStrip.x;',", SECTION)
        self.assertIn("float gl = uVenArt * smoothstep(0.6, 0.95, t4.a);", SECTION)
        self.assertIn('VEN_ART.strips.length', SECTION)

    def test_lines_are_box_filtered(self):
        self.assertIn('min(1.0, w / max(2.0 * fw, 1e-4))', SECTION)
        self.assertIn('float venLineP(float d, float w, float fw) { return mix(venLine(d, w, fw), w, smoothstep(0.15, 0.45, fw)); }', SECTION)
        self.assertIn('num * (1.0 - smoothstep(0.12, 0.35, fw))', SECTION)

    def test_no_floodlight_on_the_stands_ends(self):
        ends = SECTION[SECTION.index('    const ends = (K, plain) => {'):SECTION.index('    ends(near, false); ends(far, true);')]
        self.assertNotIn('VL.soffit', ends)
        self.assertNotIn('near.quad(pts[0], pts[k], pts[k + 1], pts[k + 1]', SECTION)
        steps = SECTION[SECTION.index("    // where the classes meet:"):SECTION.index('    // the goal posts on the end lines')]
        self.assertNotIn('VL.soffit', steps)
        self.assertNotIn('near.quad(P[0], P[k], P[k + 1], P[k + 1], m)', steps)

    def test_the_board_is_a_photograph(self):
        body = SECTION[SECTION.index('  function venScreenTex(boardIm) {'):SECTION.index('  // the yard numbers')]
        self.assertIn('c.drawImage(boardIm', body)
        self.assertNotIn('#b06c42', body)                         # the cartoon's tan diamond
        self.assertIn("'  vb = t * 0.12; vEm = t * mix(0.9, 0.62, uVenNight); vRough = 0.25;',", SECTION)

    def test_no_new_program_writes_depth(self):
        self.assertNotIn('gl_FragDepth', SECTION)

    def test_texture_units(self):
        for fn in ('venShellPatch', 'venSeatPatch', 'venFieldPatch'):
            body = SECTION[SECTION.index('  function %s(sh) {' % fn):]
            body = body[:body.index('\n  }\n')]
            decl = re.findall(r'uniform sampler2D ([^;]+);', body)
            n = sum(len(d.split(',')) for d in decl)
            self.assertLessEqual(n, 4, fn)

    def test_no_dashes_in_names(self):
        for s in re.findall(r"name: '([^']+)'", SECTION):
            self.assertNotIn('\u2014', s); self.assertNotIn('\u00b7', s)


class Art(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((ROOT / 'stadium_art.json').read_text())

    def test_strips_in_order(self):
        ids = [s['id'] for s in self.m['strips']]
        self.assertEqual(ids, ['cbp-brick', 'linc-glass', 'linc-screen', 'arena-fins', 'arena-podium', 'arena-drum', 'linc-office', 'cbp-atrium'])
        order = re.search(r'const VEN_STRIP = \{([^}]+)\}', SECTION).group(1)
        self.assertEqual([int(x) for x in re.findall(r': (\d)', order)], list(range(8)))
        for s in self.m['strips']:
            self.assertGreater(s['aspect'], 1.5)
            self.assertIn(s['rows'], (1, 2, 3))
            self.assertTrue(0 <= s['lit'] <= 1)
            self.assertEqual(s['glass'] > 0, s['lit'] > 0, s['id'])   # a strip lit after dark has panes to light

    def test_the_atlas_carries_its_glass(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('PIL unavailable')
        im = Image.open(ROOT / self.m['walls'])
        self.assertEqual(im.mode, 'RGBA')
        lo, hi = im.getchannel('A').getextrema()
        self.assertGreaterEqual(lo, 120)                            # never under 128 (a premultiplying decoder keeps the colour)
        self.assertEqual(hi, 255)
        self.assertEqual(im.size, (1024, 256 * len(self.m['strips'])))

    def test_files_and_half_copies(self):
        for k in ('walls', 'seats', 'grass', 'clay', 'board'):
            self.assertTrue((ROOT / self.m[k]).exists(), k)
            self.assertTrue((ROOT / self.m[k + 'Half']).exists(), k)
            self.assertRegex(self.m[k + 'Half'], r'^art/stadiums/%s-half\.[0-9a-f]{10}\.webp$' % k)

    def test_the_seat_tile_is_lossless(self):
        for k in ('seats', 'seatsHalf'):
            b = (ROOT / self.m[k]).read_bytes()
            self.assertEqual(b[12:16], b'VP8L', k)               # WebP lossless: the mask in green stays the mask

    def test_build_inlines_it(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("STADIUM_ART", text_of("stadium_art.json", "null"))', b)
        self.assertIn('"stadium_art.json"):', b)


if __name__ == '__main__':
    unittest.main()
