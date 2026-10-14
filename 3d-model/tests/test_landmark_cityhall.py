"""Round 191 (Mike: "I want City hall ... to be totally revamped"): City Hall rebuilt to the measured building under the
realistic look (buildCityHallReal), its facades generated photographs (fetch_cityhall_art.py, bake_cityhall_art.py,
cityhall_art.json, art/cityhall/), Round 81's block kept byte for byte for ?real=0.

These checks hold the measured table (NOAA 2022 QL1 LiDAR, OSM relation 4720912, Turner's 1909 booklet), the one themed
slot taken at Round 81's place in the build order, the realistic-look gate, the old block and its flood patch untouched,
the manifest's cells, the level's constants, and then run chModel under Node with the vendored three.min.js: both levels'
triangles within their budgets, every index and normal sound, and the tops within half a metre of the table.

The review's fixes (fix1) are held here too: every wall of the tower faces away from its axis (the clock stage's octagonal
head faced in and the sky showed under the dome), a ray from round the building (the street, a flight round the tower,
the skyline) never first meets the back of a face (the open undersides of the upper balcony, the lantern's gallery and
the crowns, the slots at every mansard's foot and every stage's head), the cut-outs in their own program, the weather
patched in rather than taken for a flat, the bronzes metallic, the dials' sphere on the dials, the café skipped and
rebuilt, tier 2's art.

The second review's fixes (fix2): the ground under and round the building is the LiDAR's and the building stands on its
measured datum (CH_GRADE: the DEM had a 2.7 m pit in the courtyard and the basement was under the sidewalks), the faces
carried under the datum to meet it, the courtyard floor flat at its level, the passages level with their own end walls and
small arches, one program again (the cut-outs' split bought nothing under the log depth buffer), the near level from 400 m,
a failed build falling back to Round 81's block, the lantern's true profile, the figure groups and eagles modelled once and
laid four times, the courtyard's own cells, the compass on its own canvas, Dilworth Park's headhouses in glass, and the
viewpoint on Broad Street's axis.

The third review's fixes (fix3): the dials read clockwise from outside (they were mirrored), the water table in the base
course's granite under each front's lowest sill, no sun inside a passage, the bronzes and the apron's statues modelled as
forms within their budgets, Penn's new form, the glass pavilions' light glass and their night, the park's café in glass,
the crowns' pediments, the lantern's piers, the floor painted on a phone's first near frame, a failed build taking back its
ground, and the viewpoint over Broad Street's canyon."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text(encoding='utf-8')


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class Table(unittest.TestCase):
    def test_the_frame_and_the_tower_axis(self):
        t = cut(SRC, '  const CITY_HALL = {', '  const CH_HOUSE')
        self.assertIn('B0: [-1608.65, -764.51],', t)
        self.assertIn("tower: { c: [0, -37.2],", t)
        # the tower's axis in the scene stays where the viewpoint, the orbit and the skyglow point at it
        fl = (0.986, 0.167, -0.167, 0.986)
        x, z = -1608.65 + fl[2] * -37.2, -764.51 + fl[3] * -37.2
        self.assertAlmostEqual(x, -1602.44, delta=0.05)
        self.assertAlmostEqual(z, -801.19, delta=0.05)

    def test_the_measured_heights(self):
        t = cut(SRC, '  const CITY_HALL = {', '  const CH_HOUSE')
        self.assertIn('st: { water: 1.5, base: 5.57, princ: 15.78, main: 26.63 },', t)
        self.assertIn("roofs: { curtainDeck: 36.0, curb: 32.8, flankDeck: 39.4, centreBody: 49.0, crown: [57.0, 59.6, 61.8, 73.5], cornerCurb: 45.4, cornerCap: 48.8, cornerPole: 58.4 },", t)
        self.assertIn('centreTop: 39.28, cornerTop: 38.13,', t)
        self.assertIn('clock: [102.8, 123.4, 10, 117, 2.5],', t)
        self.assertIn('dome: [[123.4, 8.6], [127, 8.5], [130, 8.2], [133, 7.6], [136, 6.8], [139, 5.8], [142, 4.6]],', t)
        self.assertIn('penn: [155.6, 167.0] },', t)
        # the faces: N V -62.9 to -76.7, S 63.1 to 72.1, E/W |U| 63.2 to 72.0 (the LiDAR's cornice lines)
        self.assertIn('N: { curtain: -62.9, flank: -68.9, corner: -67.0, centre: -75.0, bay: -76.7 },', t)
        self.assertIn('S: { curtain: 63.1, flank: 65.5, corner: 67.8, centre: 70.1, bay: 72.1 },', t)
        self.assertIn('E: { curtain: 63.2, flank: 65.6, corner: 67.6, centre: 70.4, bay: 72.0 },', t)

    def test_the_osm_ring(self):
        t = cut(SRC, '    ring: [[', '  };\n')
        ring = json.loads(t[t.index('['):t.rindex(']') + 1])
        self.assertEqual(len(ring), 71)
        xs, zs = [p[0] for p in ring], [p[1] for p in ring]
        self.assertTrue(-1681 < min(xs) and max(xs) < -1533 and -843 < min(zs) and max(zs) < -689)


class Wiring(unittest.TestCase):
    def test_one_slot_taken_where_round_81_took_it(self):
        blk = cut(SRC, '      cityHall: {', '      // --- Philadelphia Museum of Art')
        self.assertEqual(blk.count('themeSlotN'), 1)
        slot = blk.index('        const chSlot = themeSlotN++ % 4;')
        gate = blk.index('        if (CH_ON && chBuildSafe({ chSlot, themeParts })) break cityHall;')
        self.assertLess(slot, gate)
        # fix2: the block names no City Hall state (the loop's own CH is the chunk size); a failed build takes back its
        # meshes, its themed parts and its ground claims and falls through to Round 81's block
        self.assertNotIn('CH.', blk[:blk.index('        const floodlit')])
        safe = cut(SRC, '  function chBuildSafe(ctx) {', '  // the atlas and its mask')
        for line in ('try { buildCityHallReal(ctx); return true; } catch (e) {', "for (const k of ['near', 'far', 'dial', 'floor']) {",
                     'themeParts.length = nTheme; REBUILD_OCC.length = nOcc; CH.built = false; CH.hands = null;', 'return false;'):
            self.assertIn(line, safe)
        # the themed parts merge after it in the same step, and before the rebuilds
        self.assertLess(SRC.index('      cityHall: {'), SRC.index("    if (themeParts.length) {   // the night's themed lights"))
        self.assertLess(SRC.index("    if (themeParts.length) {   // the night's themed lights"), SRC.index("  step('Rebuilding the landmarks'"))

    def test_the_realistic_look_gate(self):
        self.assertIn("const CH_ON = REAL && typeof CITYHALL_ART !== 'undefined' && !!CITYHALL_ART && !!CITYHALL_ART.cells;", SRC)
        # fix1: City Hall's outline was dropped at pack and its tower's parts go with BRIDGE_SKIP, so the loop's old skip of
        # the outline never fired; the café on Dilworth Park is skipped there instead (as DEMOLISHED is: wideColK counted)
        self.assertNotIn('rbDist(cx, cz, CITY_HALL.ring) <= 2', SRC)
        self.assertIn('[-1603, -802, 24]', SRC)
        self.assertIn("if (CH_ON && !CH_CAFE.poly && Math.hypot(cx - CH_CAFE[0], cz - CH_CAFE[1]) < 14) { if (h <= 45 && t <= 6) wideColK++; CH_CAFE.poly = poly; CH_CAFE.h = h; CH_CAFE.c = [cx, cz]; continue; }", SRC)
        # fix2: Dilworth Park's two glass headhouses the same way (two windowless beige boxes across the west front)
        self.assertIn("if (CH_ON && h <= 15 && CH_HEADHOUSE.pts.some((q) => Math.abs(cx - q[0]) < 30 && Math.abs(cz - q[1]) < 30 && rbDist(q[0], q[1], poly) < 1.5)) {", SRC)
        self.assertIn('CH_HEADHOUSE.recs.push({ poly, h, c: [cx, cz] }); continue;', SRC)
        # the loop has a CH of its own (the chunk size), so it never names City Hall's state
        loop = cut(SRC, "  step('Raising the outer districts'", '      if (ovpStraddle(poly, cx, cz)) continue;')
        self.assertIn('const CH = 700;', loop)
        self.assertNotIn('CH.cafe', loop)
        build = cut(SRC, '  function buildCityHallReal(ctx) {', '  // the atlas and its mask')
        self.assertIn('const glassHouses = (b, lo) => { chCafe(b, CH.cafe, Y0, 0, lo); for (const r of CH.heads) chCafe(b, r, Y0, clamp(r.h - 0.35, 3.2, 5.5), lo); };', build)
        self.assertIn('chFloorFar(far.b, Y0); glassHouses(far.b, true);', build)
        self.assertIn('glassHouses(near.b);', build)

    def test_the_old_block_stands_for_real_0(self):
        blk = cut(SRC, '      cityHall: {', '      // --- Philadelphia Museum of Art')
        for line in ('        const hallMat=cityMat.clone(),hallFacade=cityMat.onBeforeCompile;', '        if (VDEPTH_WANT) vdepthTwin(hallMat);',
                     "        hallMat.customProgramCacheKey=()=> 'city-hall-soft-flood';",
                     '        appendBuilding(hallChunk(bx, bz), sqPoly(bx, bz, 148, 143), base - 1, base + 27, c, 1, base, [sqPoly(bx, bz, 64, 59)]);'):
            self.assertIn(line, blk)
        # Round 109's flood patch, which ?real=0 and tests/city_hall_gpu.html run, is the pre-round one to the byte
        flood = cut(SRC, '  function cityHallFloodPatch(sh,uniforms) {', '  const BOATHOUSE_PLANS')
        self.assertEqual(hashlib.sha256(flood.encode()).hexdigest()[:16], 'fdf4e57d694b39d2')
        self.assertIn('vec3 hc=mix(vec3(.38,.32,.23),uHallColor,uHallOn);', flood)
        self.assertIn("float tower=hallBeam((hp-vec2(0.0,-55.0))/vec2(19.0,20.0));", flood)

    def test_the_frame_steps_it_and_dev_probes_it(self):
        fr = cut(SRC, '  function frame(now, once) {', '\n  setHint();')
        self.assertEqual(fr.count('cityHallStep();'), 1)
        self.assertIn(' cityHall: cityHallProbe,', SRC)

    def test_the_level_constants(self):
        # fix2: a computer switches at 400 m as a phone does at 420 (at 650 the building is 40 px wide)
        self.assertIn('const CH_NEAR_R = isTouch ? 420 : 400, CH_HYST = 40, CH_ART_R = 1000;', SRC)
        step = cut(SRC, '  function cityHallStep() {', '  // ?dev: __dbg.cityHall()')
        self.assertIn("else if (lod === 'near' && d > CH_NEAR_R + CH_HYST) lod = 'far';", step)
        # fix1: tier 2 (the far level alone) takes the half art once the eye is within CH_NEAR_R
        self.assertIn('if ((isTouch || TIER2) && d < (TIER2 ? CH_NEAR_R : CH_ART_R)) chLoadArt();', step)
        self.assertIn("if (CH.art !== 'none') return;", cut(SRC, '  function chLoadArt() {', '  const _chE'))
        self.assertIn('if (!isTouch && !TIER2) chLoadArt();', SRC)
        self.assertNotIn('CH.cut', SRC)

    def test_phone_streams_and_samplers(self):
        g = cut(SRC, '  function chGeometry(b, Y0) {', '  // the untextured materials')
        # the colour as four normalized bytes (never three), the kind and seed as two floats: no 1- or 3-byte stream
        self.assertIn("g.setAttribute('aCol', new THREE.BufferAttribute(new Uint8Array(b.C), 4, true));", g)
        self.assertIn("g.setAttribute('aK', new THREE.BufferAttribute(new Float32Array(b.K), 2));", g)
        m = cut(SRC, '  function chMaterial(chSlot, Y0) {', '  // the cut-out parts\' shadow')
        # its own samplers: the atlas, the mask, the pitched roofs' slate and the flat roofs' tar for the decks (fix1; the
        # lamps' maps, the shadows and the weather's come with the shared patches)
        self.assertEqual(sorted(set(__import__('re').findall(r'uniform sampler2D ([^;]+);', m))), ['uMask, uPitchArt, uRoofArt'])
        self.assertNotIn('userData.vdepth', cut(SRC, '  // ---- City Hall rebuilt (Round 191', "  step('Restoring the landmarks'"))

    def test_one_program_cuts_the_balustrades(self):
        m = cut(SRC, '  function chMaterial(chSlot, Y0) {', '  // the cut-out parts\' shadow')
        # fix2 (the review): the cut-outs' own program bought nothing under the log depth buffer (every program writes
        # gl_FragDepth), so the discard is back in the one program, still only on the balustrade's own cell (fix1: on every
        # cell the mask's filtered void and dial edges holed the walls round the portals)
        self.assertEqual(m.count('discard'), 1)
        self.assertIn("'if (abs(vChK.x - ' + balusIx.toFixed(1) + ') < 0.5 && frMask.b > 0.16 && frMask.b < 0.33 && frMask.r < 0.5) discard;',", m)
        self.assertIn("mat.customProgramCacheKey = () => 'city-hall-real' + (gl2 ? '2' : '1') + '|wx';", m)
        build = cut(SRC, '  function buildCityHallReal(ctx) {', '  // the build, and a failed one undone')
        self.assertIn('CH.near = mk(near.b); CH.tris.near = near.b.I.length / 3; CH.near.customDepthMaterial = chCutDepth();', build)
        self.assertNotIn('chSplit', SRC)
        self.assertNotIn('city-hall-cut\'', SRC)
        dm = cut(SRC, '  function chCutDepth() {', '  // the dials: a canvas a dial')
        self.assertIn('depthPacking: THREE.RGBADepthPacking', dm)
        self.assertIn('discard', dm)

    def test_the_weather_is_patched_in_not_flagged(self):
        m = cut(SRC, '  function chMaterial(chSlot, Y0) {', '  // the cut-out parts\' shadow')
        # fix1: as userData.wxSurf the building was taken for a flat on the ground and kept out of the river's mirror
        self.assertNotIn('userData.wxSurf', m)
        self.assertIn('      wxSurfacePatch(sh);   // first', m)
        self.assertIn("+ '|wx';", m)
        self.assertIn('mat.userData.wxSurf = true;', cut(SRC, '  function chFloor(Y0) {', '  // Dilworth Park'))

    def test_the_bronzes_are_metal(self):
        b = cut(SRC, '  function chBronze(themeParts, chSlot, Y0) {', '  // the courtyard')
        self.assertIn('style: 3, gain: -1 });', b)
        self.assertIn("if (vTheme.z < 0.0) { metalnessFactor = 0.82; roughnessFactor = 0.4; }", SRC)   # fix2: a metal's sheen on a lighter bronze
        self.assertIn('const cBronze = new THREE.Color(0x221c15), cBronzeD = new THREE.Color(0x19140f), tone = [cBronze, cBronzeD];', b)
        self.assertIn('totalEmissiveRadiance += te * uNight * 2.4 * abs(vTheme.z) * mix(1.0, 0.42, tsat); }', SRC)

    def test_the_dials_sphere_holds_the_dials(self):
        build = cut(SRC, '  function buildCityHallReal(ctx) {', '  // the atlas and its mask')
        a = build.index('chHands(clock.minutes);')
        self.assertLess(a, build.index('CH.dial.geometry.computeBoundingSphere();'))

    def test_the_ground_is_the_lidars_and_the_datum_the_measurements(self):
        # fix2: NED had the courtyard 2.7 m under Penn Square's sidewalks and the fronts 0.4 to 0.7 m low; the LiDAR has the
        # courtyard 0.3 to 0.8 m OVER them. Under the realistic look the DEM round the building is the plane fitted to the
        # LiDAR's ground within 4 m of the walls, eased back to NED by 40 m, and the building stands on the measurements' datum
        self.assertIn("const CH_GRADE = REAL ? { cx: -1608.65, cz: -764.51, box: [-72.0, 72.0, -76.7, 72.1], d0: 10, d1: 40, g: [13.473, -0.00083, 0.00318], datum: 13.57 } : null;", SRC)
        dem = cut(SRC, '  function demAbs(x, z) {', '  function demAbs0(x, z) {')
        self.assertIn('if (CH_GRADE) return chGrade(x, z, demAbs0(x, z));', dem)
        self.assertLess(SRC.index('const CH_GRADE = REAL'), SRC.index('  const DATUM = demAbs(towersCenter.x, towersCenter.z);'))
        build = cut(SRC, '  function buildCityHallReal(ctx) {', '  // the build, and a failed one undone')
        self.assertIn('const Y0 = CH_GRADE.datum - DATUM;', build)
        # the plane at the walls against the datum: the north front 0.34 m under it, the south level with it, as the LiDAR
        g = (13.473, -0.00083, 0.00318)
        at = lambda U, V: g[0] + g[1] * U + g[2] * V - 13.57
        self.assertAlmostEqual(at(0, -77.5), -0.34, delta=0.05)
        self.assertAlmostEqual(at(0, 72.5), 0.13, delta=0.05)
        for U, V in ((72.5, 0), (-72.5, 0), (68, -68), (-68, 68)):
            self.assertLess(abs(at(U, V)), 0.4, (U, V))
        self.assertIn('court0: 0.34,', SRC)

    def test_the_floors(self):
        d = cut(SRC, '  function chDrapes(Y0) {', '  // the far level\'s floor')
        # the courtyard laid flat at its own level (the drape followed the DEM's pit), the west front paved over Dilworth's lawn
        self.assertIn('const y = Y0 + C.court0 + 0.02, tr = THREE.ShapeUtils.triangulateShape(', d)
        self.assertIn('[-84, -72, -77.5, 72.5]]', d)
        self.assertIn('CH.noTuft = [court, ...bands].map((r) => [r, rbBox(r)]);', d)
        self.assertIn("if (pg && CH.noTuft && CH.noTuft.some(([r, bb]) => x >= bb[0] && x <= bb[1] && z >= bb[2] && z <= bb[3] && pointInPoly(x, z, r))) continue;", SRC)
        # the compass on its own canvas, at 40 px a metre or more on both devices
        cc = cut(SRC, '  function chCompassCanvas() {', '  const CH_FLOOR_BOX')
        self.assertIn('const S = isTouch ? 512 : 1024', cc)   # fix3: 768 on a phone held 3.1 MB for an 18 m disc
        self.assertIn('const CH_COMPASS = { c: [0, 3.3], R: 8.75, span: 18 };', SRC)
        self.assertGreaterEqual(512 / 18, 28)
        # fix3: a phone paints the floor's canvases on its first near frame and draws the floor only once they are painted
        fl = cut(SRC, '  function chFloor(Y0) {', '  // Dilworth Park')
        self.assertIn('if (!isTouch) CH.floorPaint();', fl)
        # new textures, never the pixels' (WebGL 2 fixes a texture's storage at its first upload)
        self.assertIn('mat.map = t2; FU.uCompass.value = c2; tex.dispose(); ctex.dispose();', fl)
        step = cut(SRC, '  function cityHallStep() {', '  // ?dev: __dbg.cityHall()')
        self.assertIn("if (CH.floor) CH.floor.visible = lod === 'near' && !CH.off && !CH.floorPaint;", step)
        self.assertIn("if (CH.floorPaint && lod === 'near' && !CH.off) CH.floorPaint();", step)
        # and the floor's grain, wear and softer joints, the compass worn into the same slabs
        for line in ("float grain = mix(1.0, 0.86 + 0.28 * chFn(fp * 22.0), sfade)", "cc = mix(cc, vec3(cl), 0.18 + 0.12 * chFn(fp * 0.9)) * kj * grain"):
            self.assertIn(line, fl)
        self.assertNotIn("'#2b5d8f'", SRC)   # the old saturated blue

    def test_the_passages_at_night_and_their_ends(self):
        f = cut(SRC, '  function cityHallFloodPatchReal(sh, uniforms) {', '  // the material both levels share')
        self.assertIn('* smoothstep(0.9, 1.0, vChCol.a);', f)   # no flood inside a passage
        m = cut(SRC, '  function chMaterial(chSlot, Y0) {', '  // the cut-out parts\' shadow')
        self.assertIn('totalEmissiveRadiance += chPass * diffuseColor.rgb * vec3(1.0, 0.78, 0.52)', m)
        self.assertNotIn('step(4.5, chKind) * step(chKind, 5.5) * vec3(1.0, 0.81, 0.58)', m)   # the vaults' flat glow
        p = cut(SRC, '  function chPortal(b, H, cp, Fm, s0, s1, arch, far) {', '  // the tower: the base in the courtyard')
        self.assertIn('const fc = C.court0, fy = (d) => fm + (fc - fm) * clamp(d / rv, 0, 1), yb = Math.min(fm, fc) - 0.6;', p)
        self.assertIn('const back = [-ax, 0, -az], opening = shut ? null : chBayArch(), door = chApseDoor();', p)

    def test_the_viewpoint_on_broad_street(self):
        # fix2: 130 m east of Broad's axis the view up it was a wall of towers
        # fix3: 80 m up and 430 m out the canyon's walls filled four fifths of the view; 300 m up and 330 m out it looks over them
        self.assertIn("['cityhall', 'City Hall', [-1663.8, -439.1, 300], [-1602.4, -801.2, 40]],", SRC)
        loc = cut(SRC, '  function locateCityHall(text) {', '  function locateFix(')
        self.assertIn("const vp = viewpoints.find((v) => v.name === 'City Hall');", loc)

    def test_no_em_dashes_in_its_strings(self):
        blk = cut(SRC, '  // ---- City Hall rebuilt (Round 191', "  step('Restoring the landmarks'")
        for ch in ('—', '·'):
            for line in blk.splitlines():
                if ch in line:
                    code = line.split('//')[0]
                    self.assertNotIn(ch, code, line)


class Fix3(unittest.TestCase):
    def test_the_dials_read_clockwise_from_outside(self):
        # the review: every dial's right was the viewer's left, so it read IIX at its head and III at nine and its hands ran
        # backward. Facing a face, the viewer's right is -n x up = (nv, -nu): on the south face III falls to the east
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        mod = cut(SRC, '  // ---- City Hall rebuilt (Round 191', "  // the night's flood on the rebuilt block")
        faces = cut(SRC, '  function chDialFaces(h, off) {', '  // the four dials and their hands')
        hands = cut(SRC, '  function chHands(minutes) {', '  // the bronzes on the night')
        script = r'''
const THREE = require(THREE_PATH); const REAL = true, isTouch = false; const CITYHALL_ART = { cells: {}, meta: {}, mean: {}, m: {} };
const fl = { px: 0, pz: 0, dx: 0, dz: 1, nx: 1, nz: 0 };   // the frame's axes the scene's: U is x, V is z
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
__MOD__
__FACES__
__HANDS__
const F = chDialFaces(10, 0), out = [];
CH.hands = { g: { attributes: { position: { array: new Float32Array(8 * 4 * 3), needsUpdate: false } } }, hb: 0, dials: F, r: 3.6, yc: 110, Y0: 0 };
chHands(15 * 60);   // three in the afternoon: the hour hand to III, the minute hand to XII
const p = CH.hands.g.attributes.position.array, B = CITY_HALL.B0;
F.forEach((D, k) => {
  const tip = (j) => { const q = (k * 2 + j) * 4 * 3 + 2 * 3; return [p[q] - B[0] - D.c0[0], p[q + 1] - 110, p[q + 2] - B[1] - D.c0[1]]; };
  const h = tip(0), m = tip(1), cr = [-D.nv, 0, D.nu];   // (the viewer's right by the cross product: -n x up, with n's v as z)
  out.push({ n: [D.nu, D.nv], r: [D.ru, D.rv], right: [D.nv, -D.nu], hourAlongRight: h[0] * D.ru + h[2] * D.rv, hourUp: h[1], minuteUp: m[1] });
});
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('__MOD__', mod).replace('__FACES__', faces).replace('__HANDS__', hands)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(len(out), 4)
        for d in out:
            self.assertEqual(d['r'], d['right'], d)                 # the dial's 3 o'clock is the viewer's right
            self.assertGreater(d['hourAlongRight'], 1.5, d)          # at 15:00 the hour hand points to it
            self.assertLess(abs(d['hourUp']), 0.3, d)
            self.assertGreater(d['minuteUp'], 2.5, d)               # and the minute hand straight up
        south = [d for d in out if d['n'] == [0, 1]][0]
        self.assertEqual(south['r'], [1, 0])                         # on the south face III is to the east

    def test_the_water_table_and_the_feet_are_granite(self):
        m = cut(SRC, '  function chModel(A, far, gnd) {', '  // the apron\'s statues and the courtyard\'s furniture')
        self.assertIn("if (prof === PROF.water) { const t = waterTop(F.cell); prof = [[0, -1.2], [0.25, -1.2], [0.25, t - 0.2], [0.05, t], [0, t]]; y = t; vf = vG; }", m)
        self.assertIn("const waterTop = (cell) => { const sl = typeof cell === 'string' && A.meta[cell] && A.meta[cell].sill; return sl ? clamp(sl - 0.12, 0.5, 1.5) : 1.5; };", m)
        self.assertIn('const ix = [[a, -1.2], [c, -1.2], [c, 0], [a, 0]].map(([s2, y]) => vG(F, at(F, s2, y, 0), n));', m)
        self.assertNotIn('F.v0 + 0.002 * (F.v1 - F.v0)', m)   # the picture's foot row stretched down the plinth

    def test_no_sun_in_a_passage_and_the_soffits_lit(self):
        m = cut(SRC, '  function chMaterial(chSlot, Y0) {', "  // the cut-out parts' shadow")
        self.assertIn('{ float chSun = mix(1.0, smoothstep(0.42, 0.7, vChCol.a), chPass); reflectedLight.directDiffuse *= chSun; reflectedLight.directSpecular *= chSun; }', m)
        f = cut(SRC, '  function cityHallFloodPatchReal(sh, uniforms) {', '  // the material both levels share')
        self.assertIn('* (1.0 - max(vWNorm.y, 0.0)) * (1.0 - frMask.r) * (1.0 - chGl) * smoothstep(0.9, 1.0, vChCol.a);', f)
        self.assertNotIn('(1.0 - abs(vWNorm.y))', f)

    def test_the_glass(self):
        m = cut(SRC, '  function chMaterial(chSlot, Y0) {', "  // the cut-out parts' shadow")
        # by day the daylit room and plaza through clear glass (Fresnel's share), at night the pavilions lit within, the bars
        # thin dark steel (they were a cream grid the lamps lit into a wireframe)
        self.assertIn('reflectedLight.indirectDiffuse += chGl * (1.0 - chBar) * (1.0 - chFr)', m)
        self.assertIn('totalEmissiveRadiance += chGl * (1.0 - chBar) * mix(vec3(0.05, 0.045, 0.04), vec3(0.1, 0.075, 0.045)', m)
        self.assertIn('reflectedLight.indirectSpecular *= 1.0 + mix(1.8, 3.5, step(13.5, chKind)) * chGl * (1.0 - chBar);', m)
        self.assertIn("'  chAlb = mix(chAlb, vec3(0.105, 0.11, 0.115), chBar); }',", m)
        self.assertNotIn('vec3(0.62, 0.63, 0.62), chBar', m)
        cafe = cut(SRC, '  function chCafe(b, cafe, Y0, gh, far) {', '  // the build (in')
        self.assertIn('vk(CHK.pglass, v, nn,', cafe)
        self.assertNotIn('CHK.marble', cafe)

    def test_dilworth_parks_cafe(self):
        # OSM's way 333931838 (building=retail, the Dilworth Park Café's node in it) at the plaza's north-west corner: taken
        # with the headhouses and built in glass, its ring in REBUILD_OCC so no storefront hangs on it
        self.assertIn('const CH_HEADHOUSE = { pts: [[-1713.6, -793.5], [-1716.0, -777.6], [-1682.7, -860.3]], recs: [] };', SRC)
        build = cut(SRC, '  function buildCityHallReal(ctx) {', '  // the build, and a failed one undone')
        self.assertIn("for (const r of CH.heads) REBUILD_OCC.push({ id: 'cityhall', ring: r.poly, bb: rbBox(r.poly), pad: 0.5, top: Y0 + r.h });", build)

    def test_a_failed_build_gives_back_its_ground(self):
        safe = cut(SRC, '  function chBuildSafe(ctx) {', '  // the atlas and its mask')
        self.assertIn('NO_SOW_RINGS.length = nSow; NO_SOW_RING_BB.length = nSow; CH.noTuft = null; CH.drapes = null; CH.floorPaint = null;', safe)
        blk = cut(SRC, '      cityHall: {', '      // --- Philadelphia Museum of Art')
        self.assertIn('...CH_HEADHOUSE.recs]) { const gy = siteY(r.c[0], r.c[1], \'ground\');', blk)

    def test_the_crowns_and_the_lantern(self):
        m = cut(SRC, '  function chModel(A, far, gnd) {', '  // the apron\'s statues and the courtyard\'s furniture')
        self.assertIn("const box = rectFaces(RB, yT, yC, () => ['crown', 0, 1, 0, hBox / crH]);", m)
        self.assertNotIn("['ashlar', 0, L2 / 4, 0, (C.roofs.crown[0] - yT) / 4]", m)
        t = cut(SRC, '  function chTower(b, H) {', '  // a balustrade along face F')
        self.assertIn('cyl(cu, cv, g0, g1, far ? gr : gr - 0.3, far ? gr : gr - 0.3, segs, CHK.glass, 1, null, null, false);', t)
        self.assertIn('const nPi = 12, pw = 0.26;', t)
        self.assertIn('const pu = cu + du * CH_PED.d, pv = cv + dv * CH_PED.d', t)
        self.assertIn('const CH_PED = { d: 7.78, h: 1.5, r: 1.1 };', SRC)

    def test_the_bake_keeps_a_windows_number_on_its_bars(self):
        bake = (ROOT / 'bake_cityhall_art.py').read_text()
        # fix3 (the review: the basement's sashes a dotted line at night): a bar is not glass, but keeps its window's number
        self.assertIn('mreg[bars, 0] = 0', bake)
        self.assertNotIn('mreg[bars] = 0', bake)
        self.assertIn("if cid in ('rustic', 'tower_low'):", bake)


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((ROOT / 'cityhall_art.json').read_text())

    def test_the_cells(self):
        cells = self.m['cells']
        want = {'aedicule', 'apse', 'ashlar', 'balus', 'belvedere', 'centre', 'clock', 'corner', 'court', 'court_bay', 'court_main', 'curtain',
                'dome', 'dormer_c', 'dormer_w', 'flank', 'oculus', 'rustic', 'tower_low', 'tower_mid', 'turret',   # fix2: the courtyard's own two, the tower's courses
                'crown', 'granite', 'vest'}   # fix3: the crowns' cornice box, the base course's granite, the passages' walls
        self.assertEqual(set(cells), want)
        rects = list(cells.values())
        for r in rects:
            self.assertTrue(0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1, r)
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                self.assertFalse(a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6, (a, b))
        self.assertEqual(set(self.m['m']), want)
        self.assertEqual(set(self.m['mean']), want)

    def test_what_the_page_builds_to_the_pictures(self):
        meta = self.m['meta']
        a0, a1, spring, crown = meta['centre']['arch']
        self.assertAlmostEqual(a1 - a0, 5.0, delta=0.6)      # the 18 ft archway
        self.assertAlmostEqual(crown, 9.14, delta=0.8)        # 30 ft
        self.assertLess(spring, crown)
        cu, cy, ru, rv = meta['clock']['dial']
        self.assertAlmostEqual(cu, 10.0, delta=0.5)           # centred on the 20 m face
        self.assertAlmostEqual(102.8 + cy, 110.0, delta=0.6)  # 361 ft
        self.assertAlmostEqual(max(ru, rv) * 2, 7.92, delta=0.6)   # 26 ft
        self.assertEqual(len(meta['centre']['cols']), 12)
        self.assertEqual(len(meta['corner']['cols']), 8)
        self.assertEqual(len(meta['flank']['cols']), 2)
        # fix2: the bay's small arch at each passage's courtyard end, centred on its 14 m and under the basement's head, and
        # the apse's door, centred on its 19.8 m, which the page cuts where the pictures paint them
        b0, b1, bs, bc = meta['court_bay']['arch']
        self.assertAlmostEqual((b0 + b1) / 2, 7.0, delta=0.4)
        self.assertTrue(2.5 < b1 - b0 < 4.5 and bs < bc < 5.57, (b0, b1, bs, bc))
        d0, d1, ds, dc = meta['apse']['arch']
        self.assertAlmostEqual((d0 + d1) / 2, 9.9, delta=0.3)
        self.assertTrue(1.5 < d1 - d0 < 3.3 and 3.5 < dc < 6.0, (d0, d1, dc))
        # the belvedere's arch is glazed now: no void left in it (the review: a black hole twice the photographs' width)
        self.assertNotIn('belvedere', meta)
        # fix3: the crown box's pediment, measured on its picture (centred, two fifths of the face, 1.56 m over the cornice at 3.4)
        p0, p1, pb, pa = meta['crown']['ped']
        self.assertAlmostEqual((p0 + p1) / 2, 4.3, delta=0.2)
        self.assertTrue(2.6 < p1 - p0 < 4.2 and abs(pb - 3.4) < 0.1 and 1.2 < pa - pb < 2.0, meta['crown'])
        # and every outer front's lowest sill, the water table's head under it: the flanks' basement arches come down to 0.74
        # m, the corner pavilions' to 0.94, the wings' to 1.65
        for c, lo, hi in (('flank', 0.6, 0.9), ('corner', 0.8, 1.1), ('curtain', 1.5, 1.8), ('centre', 3.0, 3.6)):
            self.assertTrue(lo < meta[c]['sill'] < hi, (c, meta[c]))

    def test_the_files_and_the_phone_copies(self):
        for k in ('img', 'imgHalf', 'mask', 'maskHalf'):
            self.assertTrue(self.m[k].startswith('art/cityhall/'), k)
            self.assertTrue((ROOT / self.m[k]).exists(), k)
        self.assertEqual(self.m['size'], [2048, 2048])


# the geometry checks, in the building frame (U, y, V): a small BVH over the triangles; every ray's first hit (two faces
# within 2 mm of each other count as one: a two-sided board is two single-sided quads) and whether it is a back face
GEOM = r'''
function bvh(P, I) {
  const n = I.length / 3, cx = new Float32Array(n * 3), bb = new Float32Array(n * 6);
  for (let t = 0; t < n; t++) {
    let x0 = 1e9, y0 = 1e9, z0 = 1e9, x1 = -1e9, y1 = -1e9, z1 = -1e9;
    for (let k = 0; k < 3; k++) { const o = I[t * 3 + k] * 3; x0 = Math.min(x0, P[o]); x1 = Math.max(x1, P[o]); y0 = Math.min(y0, P[o + 1]); y1 = Math.max(y1, P[o + 1]); z0 = Math.min(z0, P[o + 2]); z1 = Math.max(z1, P[o + 2]); }
    bb.set([x0, y0, z0, x1, y1, z1], t * 6); cx.set([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], t * 3);
  }
  const ids = Array.from({ length: n }, (_, i) => i);
  const build = (a, b) => {
    const nd = { box: [1e9, 1e9, 1e9, -1e9, -1e9, -1e9] };
    for (let i = a; i < b; i++) { const t = ids[i]; for (let k = 0; k < 3; k++) { nd.box[k] = Math.min(nd.box[k], bb[t * 6 + k]); nd.box[k + 3] = Math.max(nd.box[k + 3], bb[t * 6 + k + 3]); } }
    if (b - a <= 8) { nd.leaf = ids.slice(a, b); return nd; }
    const ext = [0, 1, 2].map((k) => nd.box[k + 3] - nd.box[k]), ax = ext.indexOf(Math.max(...ext));
    const sub = ids.slice(a, b).sort((p, q) => cx[p * 3 + ax] - cx[q * 3 + ax]);
    for (let i = a; i < b; i++) ids[i] = sub[i - a];
    const m = (a + b) >> 1; nd.l = build(a, m); nd.r = build(m, b); return nd;
  };
  const root = build(0, n);
  const hitBox = (bx, o, d, tmax) => { let t0 = 0, t1 = tmax; for (let k = 0; k < 3; k++) { const inv = 1 / (d[k] || 1e-12); let ta = (bx[k] - o[k]) * inv, tb = (bx[k + 3] - o[k]) * inv; if (ta > tb) { const s = ta; ta = tb; tb = s; } t0 = Math.max(t0, ta); t1 = Math.min(t1, tb); if (t0 > t1) return false; } return true; };
  return (o, d, tmax) => {
    const hits = [], st = [root];
    while (st.length) {
      const nd = st.pop(); if (!hitBox(nd.box, o, d, tmax)) continue;
      if (!nd.leaf) { st.push(nd.l, nd.r); continue; }
      for (const t of nd.leaf) {
        const a = I[t * 3] * 3, b = I[t * 3 + 1] * 3, c = I[t * 3 + 2] * 3;
        const e1 = [P[b] - P[a], P[b + 1] - P[a + 1], P[b + 2] - P[a + 2]], e2 = [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]];
        const pv = [d[1] * e2[2] - d[2] * e2[1], d[2] * e2[0] - d[0] * e2[2], d[0] * e2[1] - d[1] * e2[0]], det = e1[0] * pv[0] + e1[1] * pv[1] + e1[2] * pv[2];
        if (Math.abs(det) < 1e-12) continue;
        const tv = [o[0] - P[a], o[1] - P[a + 1], o[2] - P[a + 2]], u = (tv[0] * pv[0] + tv[1] * pv[1] + tv[2] * pv[2]) / det; if (u < -1e-7 || u > 1 + 1e-7) continue;
        const qv = [tv[1] * e1[2] - tv[2] * e1[1], tv[2] * e1[0] - tv[0] * e1[2], tv[0] * e1[1] - tv[1] * e1[0]], v = (d[0] * qv[0] + d[1] * qv[1] + d[2] * qv[2]) / det; if (v < -1e-7 || u + v > 1 + 1e-7) continue;
        const tt = (e2[0] * qv[0] + e2[1] * qv[1] + e2[2] * qv[2]) / det; if (tt <= 1e-4 || tt > tmax) continue;
        const nx = e1[1] * e2[2] - e1[2] * e2[1], ny = e1[2] * e2[0] - e1[0] * e2[2], nz = e1[0] * e2[1] - e1[1] * e2[0];
        hits.push([tt, Math.sign(nx * d[0] + ny * d[1] + nz * d[2]), P[a + 1]]);
      }
    }
    return hits.sort((p, q) => p[0] - q[0]);
  };
}
function seeThrough(b, N) {
  const P = b.P, I = b.I, cast = bvh(P, I), n = I.length / 3;
  let s = 7; const R = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const cum = new Float64Array(n); let tot = 0;
  for (let t = 0; t < n; t++) { const a = I[t * 3] * 3, c = I[t * 3 + 1] * 3, e = I[t * 3 + 2] * 3; const u = [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]], v = [P[e] - P[a], P[e + 1] - P[a + 1], P[e + 2] - P[a + 2]]; tot += Math.hypot(u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]) / 2; cum[t] = tot; }
  const pick = () => { const x = R() * tot; let lo = 0, hi = n - 1; while (lo < hi) { const m = (lo + hi) >> 1; if (cum[m] < x) lo = m + 1; else hi = m; } return lo; };
  const eyes = [];
  for (let k = 0; k < 16; k++) { const a = k / 16 * Math.PI * 2; eyes.push([Math.cos(a) * 115, 1.7, Math.sin(a) * 118 - 3], [Math.cos(a) * 200, 30, Math.sin(a) * 200]); }
  for (let k = 0; k < 12; k++) { const a = (k + 0.5) / 12 * Math.PI * 2; for (const [r, y] of [[40, 118], [30, 146], [45, 95], [60, 64], [24, 160]]) eyes.push([Math.cos(a) * r, y, Math.sin(a) * r - 37.2]); }
  for (let k = 0; k < 8; k++) { const a = k / 8 * Math.PI * 2; eyes.push([Math.cos(a) * 150, 220, Math.sin(a) * 150]); }
  const out = { rays: 0, back: 0, backTower: 0 };
  for (const e of eyes) for (let i = 0; i < N; i++) {
    const t = pick(), a = I[t * 3] * 3, c = I[t * 3 + 1] * 3, f = I[t * 3 + 2] * 3; let r1 = R(), r2 = R(); if (r1 + r2 > 1) { r1 = 1 - r1; r2 = 1 - r2; }
    const p = [0, 1, 2].map((k) => P[a + k] + (P[c + k] - P[a + k]) * r1 + (P[f + k] - P[a + k]) * r2);
    const d = [p[0] - e[0], p[1] - e[1], p[2] - e[2]], L = Math.hypot(d[0], d[1], d[2]); d[0] /= L; d[1] /= L; d[2] /= L;
    out.rays++;
    const h = cast(e, d, L + 0.01); if (!h.length) continue;
    let front = false, back = null; for (const x of h) { if (x[0] > h[0][0] + 0.002) break; if (x[1] < 0) front = true; else back = x; }
    if (front || !back) continue;
    out.back++;
    if (e[1] + d[1] * back[0] > 60) out.backTower++;
  }
  return out;
}
function towerFacing(b) {
  const P = b.P, I = b.I, cu = 0, cv = -37.2; let n = 0, bad = 0;
  for (let t = 0; t < I.length; t += 3) {
    if (b.K[I[t] * 2] === b.balusK) continue;   // the balustrades are boards seen from both sides
    const A = I[t] * 3, B2 = I[t + 1] * 3, C = I[t + 2] * 3;
    const ux = P[B2] - P[A], uy = P[B2 + 1] - P[A + 1], uz = P[B2 + 2] - P[A + 2], vx = P[C] - P[A], vy = P[C + 1] - P[A + 1], vz = P[C + 2] - P[A + 2];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx, l = Math.hypot(nx, ny, nz);
    if (l < 1.0 || Math.abs(ny) / l > 0.3) continue;
    let w = 0; for (const [p, q] of [[A, B2], [B2, C], [C, A]]) w = Math.max(w, Math.hypot(P[p] - P[q], P[p + 2] - P[q + 2])); if (w < 1.5) continue;   // a column's or a pier's narrow faces
    const mx = (P[A] + P[B2] + P[C]) / 3, my = (P[A + 1] + P[B2 + 1] + P[C + 1]) / 3, mz = (P[A + 2] + P[B2 + 2] + P[C + 2]) / 3;
    if (my < 49.5 || Math.hypot(mx - cu, mz - cv) > 15) continue;   // the tower over every roof
    n++;
    if ((mx - cu) * nx + (mz - cv) * nz < 0) bad++;
  }
  return { n, bad };
}
'''


class Model(unittest.TestCase):
    def run_model(self, touch):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        mod = cut(SRC, '  // ---- City Hall rebuilt (Round 191', "  // the night's flood on the rebuilt block")
        script = r'''
const THREE = require(THREE_PATH);
const REAL = true, isTouch = TOUCH;
const CITYHALL_ART = MANIFEST;
const fl = { px: 140, pz: 0, dx: -0.167, dz: 0.986, nx: 0.986, nz: 0.167 };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
MOD
GEOM
const out = {};
for (const far of [false, true]) {
  const { b, tops } = chModel(CITYHALL_ART, far);
  const ids = Object.keys(CITYHALL_ART.cells).sort();
  b.balusK = ids.indexOf('balus');
  const see = seeThrough(b, 120), tower = towerFacing(b);
  // the undersides: down-facing faces under the upper balcony, the lantern's gallery and the crowns' cornice boxes
  const soff = { bal2: 0, gallery: 0, box: 0 };
  for (let t = 0; t < b.I.length; t += 3) {
    const A = b.I[t] * 3, B2 = b.I[t + 1] * 3, Cc = b.I[t + 2] * 3, P = b.P;
    const ux = P[B2] - P[A], uy = P[B2 + 1] - P[A + 1], uz = P[B2 + 2] - P[A + 2], vx = P[Cc] - P[A], vy = P[Cc + 1] - P[A + 1], vz = P[Cc + 2] - P[A + 2];
    const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx, l = Math.hypot(nx, ny, nz) || 1;
    if (ny / l > -0.9) continue;
    const my = (P[A + 1] + P[B2 + 1] + P[Cc + 1]) / 3;
    if (Math.abs(my - 87.5) < 0.05) soff.bal2++; else if (Math.abs(my - 149.5) < 0.05) soff.gallery++; else if (Math.abs(my - 53.6) < 0.05) soff.box++;
  }
  let bad = 0, nanP = 0, nanN = 0, short = 0;
  for (const i of b.I) if (!(i >= 0 && i < b.nv)) bad++;
  for (const v of b.P) if (!Number.isFinite(v)) nanP++;
  for (let i = 0; i < b.nv; i++) { const l = Math.hypot(b.N[i * 3], b.N[i * 3 + 1], b.N[i * 3 + 2]); if (!Number.isFinite(l)) nanN++; else if (l < 0.5) short++; }
  let ymax = -1e9, ymin = 1e9; for (let i = 1; i < b.P.length; i += 3) { ymax = Math.max(ymax, b.P[i]); ymin = Math.min(ymin, b.P[i]); }
  // fix2: the lantern's glazed gallery, the passages' floors (the ground at 0 here) and the courtyard's tiling cell
  const kindAt = (i) => b.K[i * 2];
  let glass = 0, paveLo = 1e9, paveHi = -1e9, cmU = 0;
  for (let i = 0; i < b.nv; i++) {
    const U = b.P[i * 3], y = b.P[i * 3 + 1], V = b.P[i * 3 + 2];
    if (kindAt(i) === -13 && y > 146.5 && y < 149.6 && Math.abs(Math.hypot(U, V + 37.2) - (far ? 4.85 : 4.55)) < 0.1) glass++;   // (fix3: set back 0.3 m behind its piers)
    if (kindAt(i) === -7 && Math.abs(U) < 75 && Math.abs(V) < 80) { paveLo = Math.min(paveLo, y); paveHi = Math.max(paveHi, y); }
    if (kindAt(i) === ids.indexOf('court_main')) cmU = Math.max(cmU, b.T[i * 2]);
  }
  // fix3: the granite's highest point on the north flanks' fronts (the water table, under their 0.74 m sills), the far level's
  // portal recesses (the vault's kind), the near level's red granite columns and lamps
  let wtFlank = -1e9, farVault = 0, rgran = 0, lamps = 0, bronze = 0;
  for (let i = 0; i < b.nv; i++) {
    const U = b.P[i * 3], y = b.P[i * 3 + 1], V = b.P[i * 3 + 2], k = kindAt(i);
    if (k === ids.indexOf('granite') && Math.abs(U) > 13.8 && Math.abs(U) < 30.5 && V < -68.8 && V > -69.3 && y > -0.5) wtFlank = Math.max(wtFlank, y);
    if (k === -5) farVault++;
    if (k === -16) rgran++; if (k === -18) lamps++; if (k === -15) bronze++;
  }
  const g = chGeometry(b, 2.45);
  out[far ? 'far' : 'near'] = { tris: b.I.length / 3, verts: b.nv, bad, nanP, nanN, short, ymax, ymin, tops, see, tower, soff, glass, paveLo, paveHi, cmU, wtFlank, farVault, rgran, lamps, bronze,
    balus: b.K.filter((k, i) => i % 2 === 0 && k === b.balusK).length,
    attrs: Object.fromEntries(Object.entries(g.attributes).map(([k, a]) => [k, [a.array.constructor.name, a.itemSize, a.array.BYTES_PER_ELEMENT * a.itemSize]])) };
}
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('TOUCH', 'true' if touch else 'false') \
            .replace('MANIFEST', (ROOT / 'cityhall_art.json').read_text()).replace('MOD', mod).replace('GEOM', GEOM)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def check(self, out, near_budget):
        for lod, budget in (('near', near_budget), ('far', 6000)):
            o = out[lod]
            self.assertLessEqual(o['tris'], budget, lod)
            self.assertEqual((o['bad'], o['nanP'], o['nanN'], o['short']), (0, 0, 0, 0), lod)
            self.assertGreaterEqual(o['ymin'], -1.21, lod)   # fix2: the faces' feet carried 1.2 m under the datum
            for k, (typ, size, bytes_) in o['attrs'].items():
                self.assertEqual(bytes_ % 4, 0, (lod, k, typ, size))   # no 1- or 3-byte stream (Round 158)
        t = out['near']['tops']
        for k, v in (('centreCrown', 61.8), ('cornerCap', 48.8), ('flankDeck', 39.4), ('centreBody', 49.0), ('crownDeck', 57.0),
                     ('masonry', 102.8), ('clockStage', 123.4), ('dome', 142.0), ('cupola', 155.6), ('turret', 48.5), ('apse', 24.5)):
            self.assertAlmostEqual(t[k], v, delta=0.5, msg=k)
        # the highest point the model itself builds is the north crown's flagpole (73.5) under the cupola's head, where Penn's
        # feet stand (he rides the themed parts to 167.0)
        self.assertAlmostEqual(out['near']['ymax'], 155.6, delta=0.1)
        for lod in ('near', 'far'):
            o = out[lod]
            # fix1: every wall of the tower over the roofs faces away from its axis (the octagonal head faced in)
            self.assertGreater(o['tower']['n'], 100, lod)
            self.assertEqual(o['tower']['bad'], 0, lod)
            # and from round the building no ray first meets the back of a face: none over 60 m (the tower's stages, the
            # dome's foot, the balconies, the gallery), hardly any at all (a valley's sliver between two roofs)
            self.assertGreaterEqual(o['see']['rays'], 12000, lod)
            self.assertEqual(o['see']['backTower'], 0, (lod, o['see']))
            self.assertLess(o['see']['back'] / o['see']['rays'], 0.001, (lod, o['see']))
        # the undersides the review found open: the upper balcony's, the lantern gallery's and the crowns' cornice boxes'
        n = out['near']['soff']
        self.assertGreaterEqual(n['bal2'], 8)
        self.assertGreaterEqual(n['gallery'], 8)
        self.assertGreaterEqual(n['box'], 16)
        # the balustrades and the cresting (cut out by the one program, fix2) in the near level; the far level has none
        self.assertGreater(out['near']['balus'], 100)
        self.assertEqual(out['far']['balus'], 0)
        n = out['near']
        # fix2: the lantern's glazed gallery is there in both levels; the passages' floors run from the ground at the mouth
        # (0 here) to the courtyard's floor at 0.34, never the old ramp down into the DEM's pit; the courtyard's cell tiles
        # along its 62 m faces (clamped, it drew one stretched column of pixels)
        self.assertGreater(n['glass'], 20)
        self.assertGreater(out['far']['glass'], 10)
        self.assertGreaterEqual(n['paveLo'], -0.01)
        self.assertLessEqual(n['paveHi'], 0.35)
        self.assertGreater(n['cmU'], 2.0)
        # fix3: the water table in granite under the north flanks' 0.74 m sills (it ran to 1.5 m across their arched windows);
        # the far level's four portals a recess of the passage's tone (they were the picture's black arches); the passages'
        # red granite columns and their lanterns and the apron's bronzes in the near level
        self.assertTrue(0.5 < n['wtFlank'] < 0.66, n['wtFlank'])
        self.assertGreaterEqual(out['far']['farVault'], 4 * 7)
        self.assertGreater(n['rgran'], 100)
        self.assertGreater(n['lamps'], 40)
        self.assertGreater(n['bronze'], 2000)

    def test_a_computer(self):
        out = self.run_model(False)
        self.check(out, 60000)
        self.assertGreater(out['near']['tris'], 5 * out['far']['tris'] / 2)

    def test_a_phone(self):
        self.check(self.run_model(True), 30000)


class Bronzes(unittest.TestCase):
    def test_the_forms(self):
        # the eagles 3.7 m across their raised wings (12 ft), on the stone; Penn 10.98 m to his hat's crown before he is taken to
        # the statue's 11.4; a group within its pedestal; no form with a broken normal
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        mod = cut(SRC, '  // ---- City Hall rebuilt (Round 191', "  // the night's flood on the rebuilt block")
        script = r'''
const THREE = require(THREE_PATH); const REAL = true, isTouch = false; const CITYHALL_ART = { cells: {}, meta: {}, mean: {}, m: {} };
const fl = { px: 140, pz: 0, dx: -0.167, dz: 0.986, nx: 0.986, nz: 0.167 };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
__MOD__
const box = (L) => { const b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9]; let bad = 0; for (const [g] of L) { const p = g.attributes.position.array, n = g.attributes.normal.array; for (let i = 0; i < p.length; i += 3) { for (let k = 0; k < 3; k++) { b[k] = Math.min(b[k], p[i + k]); b[k + 3] = Math.max(b[k + 3], p[i + k]); } if (!(Math.abs(Math.hypot(n[i], n[i + 1], n[i + 2]) - 1) < 0.01)) bad++; } } return { b, bad }; };
console.log(JSON.stringify({ eagle: box(chEagleForm(false)), penn: box(chPennForm(false)), group: box(chGroupForm(false)) }));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('__MOD__', mod)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        o = json.loads(r.stdout.strip().splitlines()[-1])
        e = o['eagle']['b']
        self.assertAlmostEqual(e[5] - e[2], 3.7, delta=0.15)   # the span
        self.assertGreater(e[4], 2.3)                           # the wings raised over the head
        self.assertGreater(e[1], -0.05)                         # nothing under the stone
        self.assertAlmostEqual(o['penn']['b'][4], 10.98, delta=0.02)
        g = o['group']['b']
        self.assertLess(max(abs(g[0]), abs(g[3]), abs(g[2]), abs(g[5])), 1.35)
        for k in ('eagle', 'penn', 'group'):
            self.assertEqual(o[k]['bad'], 0, k)

    def test_the_groups_and_eagles(self):
        # fix2: one group of draped figures (about 800 triangles) and one eagle with fanned, notched wings (about 110) modelled
        # once and laid four times each at the dome's foot, in the themed mesh's own draw; the boxes and balls they were
        # made a few hundred
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        mod = cut(SRC, '  // ---- City Hall rebuilt (Round 191', "  // the night's flood on the rebuilt block")
        bronze = cut(SRC, '  function chBronze(themeParts, chSlot, Y0) {', '  // the courtyard')
        script = r'''
const THREE = require(THREE_PATH); const V3 = THREE.Vector3;
const REAL = true, isTouch = false; const CITYHALL_ART = { cells: {}, meta: {}, mean: {}, m: {} };
const fl = { px: 140, pz: 0, dx: -0.167, dz: 0.986, nx: 0.986, nz: 0.167 };
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
__MOD__
__BRONZE__
const parts = [];
chBronze(parts, 0, 0);
let low = 0, all = 0, mirror = 0;
for (const p of parts) {
  const g = p.geom.index ? p.geom.toNonIndexed() : p.geom, P = g.attributes.position.array, t = P.length / 9;
  all += t;
  let y = 0; for (let i = 1; i < P.length; i += 3) y += P[i]; y /= P.length / 3;
  if (y < 150) low += t;
  if (p.gain !== -1) mirror++;
}
console.log(JSON.stringify({ parts: parts.length, all, low, mirror }));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('__MOD__', mod).replace('__BRONZE__', bronze)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o['mirror'], 0)   # every part bronze (the themed mesh's metal)
        # fix3 (the review: pawns with ball heads, bat-winged balls, a peg doll): each group of figures 2 to 3k triangles, each
        # eagle about 700, Penn 3 to 5k, all on the themed mesh's one draw
        self.assertTrue(4 * (2000 + 500) <= o['low'] <= 4 * (3000 + 900), o)
        self.assertTrue(3000 <= o['all'] - o['low'] <= 5000, o)


if __name__ == '__main__':
    unittest.main()
