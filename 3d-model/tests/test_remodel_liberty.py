"""Round 195: One and Two Liberty Place remodelled under the realistic look (LIB_SPECS, 'Raising the outer districts').

- The massing keeps to the references: One Liberty's notched shaft to OSM's 185 m, its central bays' gables to 220.5 (OSM
  220), its crown's squares to 229, 240 and 248 (the LiDAR's 251.5 is the pyramid's foot) and the needle to 288; Two
  Liberty's bays to 240.9 and its finial to 258.5; every tier inside the one below, every bay proud of its shaft face.
  The review's fixes: One's top tier runs on as a glazed pyramid into a flared steel foot of 2 to 3.5 m under the mast
  (OSM's 250 m part 9.4 m square), Two's flanks set back in two stages (182 and 207 m, the photographs), its finial slender.
- The builder is run under Node with the page's own code (cut from app.js) against recording stand-ins for the chunks: 48
  lit gable edges (Round 84's 32 and 16: every sloping edge of every gable end, Mike's photo), the eaves unlit, the spire and
  the finial white every night (mix 0) with One's red beacon on top at 288 m, every wall quad wound to face its own normal,
  every slope facing up, the near level's base quads facing out, the theme slots taken in Round 84's order. The review's
  colours: the spire's steel dark and on themeMat's metal path (a negative gain), the edges' tubes a mid silver metal whose
  light after dark is Round 84's, the slopes the crown's glass at its full lightness and more (never the first pass's 0.42),
  their hue halfway to grey, the pyramid glass, nothing near white by day.
- ?real=0 keeps Round 84's towers: the old blocks stand under `if (!REAL)`, unchanged.
- The near level: the art's manifest names a picture and a phone half for the base and the glazing, the halves half the
  size (the base 1024 by 512 on a computer, the review's budget); the glazing is ribs along the eave with faint mullions,
  never a square grid; the page loads them through artImage(artSrc(...)) and lets a phone's go at upload, each picture
  within its own mesh's reach, each mesh shown only once its picture has landed; the placeholder is premultiplied; no new
  program writes gl_FragDepth; every stream the near level uploads is a 4-byte float stream (the phones' padded copies,
  Round 158); libStep runs once a frame and the recovery tier builds neither near mesh.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
THREE = json.dumps(str(ROOT / 'three.min.js'))


def cut(start, end, src=SRC):
    a = src.index(start)
    return src[a:src.index(end, a)]


SPECS = cut('  const LIB_SPECS = [', '  // the near level (LIB.base')
BUILD = cut('      if (REAL) {\n        const DIRS = [[1, 0]', '      // --- One Liberty Place (17th & Market)')
PYR4 = cut('      const pyr4 = (cx, cz, w, y0, y1, rT) => {', '      const neon = ')
BOX = cut('  function box(w, h, d, x, y, z, ry) {', '\n  }\n') + '\n  }\n'
AREA = cut('  function signedArea(pts) {', '\n  }\n') + '\n  }\n'


def node(script):
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class Massing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        cls.S = node(SPECS + '\nconsole.log(JSON.stringify(LIB_SPECS));')

    def test_heights_keep_to_the_references(self):
        one, two = self.S
        self.assertEqual((one['name'], two['name']), ('One Liberty Place', 'Two Liberty Place'))
        self.assertEqual(one['shaft']['top'], 185)                     # OSM's building parts
        self.assertAlmostEqual(one['arms']['apex'], 220, delta=1.5)    # OSM 220, the skyline photographs 220.6
        self.assertEqual([t['apex'] for t in one['tiers']], [229, 240, 248])
        self.assertEqual(one['spire']['needle'], 288)                  # 945 ft
        self.assertAlmostEqual(one['spire']['pyr'][0], 245, delta=4)   # the pyramid's foot inside the top tier
        self.assertLess(one['spire']['pyr'][1], 260)
        self.assertLessEqual(one['spire']['pyr'][2], 2 * one['tiers'][-1]['hw'])   # inside the top tier (OSM's 250 m part 9.4 m)
        f = one['spire']['foot']                                       # the flared steel foot: 2 to 3.5 m, over the glass's top
        self.assertTrue(2.0 <= f[1] - f[0] <= 3.5, f)
        self.assertLessEqual(f[0], one['spire']['pyr'][1])
        self.assertGreater(f[2], one['spire']['pyr'][3])
        self.assertAlmostEqual(f[3] * 0.7071, one['spire']['mast'][2], delta=0.05)   # its top the mast's foot
        self.assertEqual(two['spire']['finial'][1], 258.5)             # 848 ft
        self.assertLessEqual(two['spire']['finial'][2], 1.2)           # slender (the first pass's 3.4 m read as a white arrowhead)
        up = two['shaft']['upper']                                     # the flanks' setbacks: 182 and 207 m
        self.assertEqual((two['shaft']['top'], up['top']), (182, 207))
        self.assertTrue(up['u'][0] > two['shaft']['u'][0] and up['u'][1] < two['shaft']['u'][1] and up['v'][1] < two['shaft']['v'][1])
        self.assertAlmostEqual(two['arms']['apex'], 240.9, delta=8)    # OSM 233, the photographs 240.9
        self.assertEqual(two['tiers'][0]['apex'], 253.5)

    def test_every_tier_nests_and_every_bay_stands_proud(self):
        for T in self.S:
            S, A = T['shaft'], T['arms']
            faces = [S['u'][1], S['v'][1], -S['u'][0], -S['v'][0]]
            for k in range(4):
                self.assertGreater(A['ends'][k], faces[k], (T['name'], k))           # proud of its shaft face
                self.assertLess(A['ends'][k] - faces[k], 6, (T['name'], k))
            self.assertLess(A['a'], T['tiers'][0]['hw'])
            U = S.get('upper')
            if U:   # a setback stage: inside the shaft, over it, under the bays' eaves, round the first tier
                uf = [U['u'][1], U['v'][1], -U['u'][0], -U['v'][0]]
                for k in range(4):
                    self.assertLessEqual(uf[k], faces[k], (T['name'], k))
                    self.assertGreaterEqual(uf[k], T['tiers'][0]['hw'], (T['name'], k))
                self.assertGreater(U['top'], S['top'])
                faces = uf
            prev_hw, prev_eave = min(faces), (U or S)['top']
            for t in T['tiers']:
                self.assertLess(t['hw'], prev_hw, T['name'])
                self.assertGreater(t['eave'], prev_eave - 1, T['name'])
                self.assertGreater(t['apex'], t['eave'])
                pitch = (t['apex'] - t['eave']) / t['hw']
                self.assertTrue(0.95 < pitch < 1.4, (T['name'], pitch))                # about 45 to 55 degrees, the photographs'
                prev_hw, prev_eave = t['hw'], t['eave']
            bay = (A['apex'] - A['eave']) / A['a']
            self.assertTrue(0.95 < bay < 1.45, (T['name'], bay))
            self.assertGreater(A['eave'], (S.get('upper') or S)['top'])
            # a bay's ridge meets the first tier's wall under that wall's own gable
            t0 = T['tiers'][0]
            self.assertLess(A['apex'], t0['apex'])
            self.assertLess(A['eave'], t0['apex'] - (t0['apex'] - t0['eave']) / t0['hw'] * A['a'])

    def test_the_lobbies_face_the_streets(self):
        one, two = self.S
        self.assertEqual(sorted(one['lobby']), [2, 3])   # Market (north) and 17th (west)
        self.assertEqual(sorted(two['lobby']), [0, 1])   # Chestnut (south) and 16th (east)


class Builder(unittest.TestCase):
    """The block that builds both towers, run under Node with recording stand-ins for the chunks and lists it fills."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        art = (ROOT / 'liberty_art.json').read_text()
        script = r'''
const THREE = require(@@THREE@@);
const V3 = THREE.Vector3;
const REAL = true, GLASS_ON = true;
const LIBERTY_ART = @@ART@@;
@@SPECS@@
const LIB = { on: true, base: null, frames: null, feet: [], crowns: [], tris: { base: 0, frames: 0, shared: 0 }, parts: { walls: 0, roofs: 0, trims: 0, neon: 0, lit: 0 } };
const lum = (c) => 0.2126 * c.r ** 2.2 + 0.7152 * c.g ** 2.2 + 0.0722 * c.b ** 2.2;
const sat = (c) => { const mx = Math.max(c.r, c.g, c.b), mn = Math.min(c.r, c.g, c.b); return mx > 0 ? (mx - mn) / mx : 0; };
const libU = { uLibBase: { value: 0 } };
const fl = { nx: 0.98547, nz: 0.16983, dx: -0.16983, dz: 0.98547 };
const ryG = Math.atan2(-fl.nz, fl.nx);
const siteY = () => 5;
@@BOX@@
@@AREA@@
@@PYR4@@
const cWhite = new THREE.Color(0xa7b7c2), cSilver = new THREE.Color(0xc1cbd2);
const themeParts = [], lmGlass = [], lmTrim = [];
let themeSlotN = 1;
const glassTowerBody = (spec, out) => { out.set(0x5d7f9e).multiplyScalar(0.66); return true; };
const glassSysOfSpec = () => 2, glassFh = (sys) => -(sys + 1) / 10, glassTintKey = () => 0.5;
const chunk = () => ({ v: [], idx: [] });
const gchs = new Map(), chs = new Map();
const getGlassChunk = (x, z) => { const k = Math.floor(x / 700) + ':' + Math.floor(z / 700); if (!gchs.has(k)) gchs.set(k, chunk()); return gchs.get(k); };
const getChunk = (x, z) => { const k = Math.floor(x / 700) + ':' + Math.floor(z / 700); if (!chs.has(k)) chs.set(k, chunk()); return chs.get(k); };
const pushV = (ch, x, y, z, nx, ny, nz, r, g, b, st, base, fh, tint, u, len, h) => { ch.v.push([x, y, z, nx, nz, st, fh, u, len, h]); return ch.v.length - 1; };
const appended = [];
const appendBuilding = (ch, poly, y0, y1, color, st, base, holes, fh) => appended.push({ glass: [...gchs.values()].includes(ch), poly, y0, y1, st, fh });
const libMaterials = () => {}, freeOnUpload = () => {}, vdepthNoteOverlay = () => {};
const addChunkMesh = (g) => ({ geometry: g });
@@BUILD@@
// the walls: every triangle faces the way its vertices' normal does, every wall carries the shader's whole-wall u (0 or L)
let wallTris = 0, wallBad = 0, uBad = 0, sysOf = {};
for (const ch of gchs.values()) {
  for (let t = 0; t < ch.idx.length; t += 3) {
    const [a, b, c] = [ch.v[ch.idx[t]], ch.v[ch.idx[t + 1]], ch.v[ch.idx[t + 2]]];
    const e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    const n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    if (Math.hypot(...n) < 1e-6) continue;
    wallTris++;
    if (n[0] * a[3] + n[2] * a[4] <= 0) wallBad++;
  }
  for (const v of ch.v) { if (!(Math.abs(v[7]) < 1e-6 || Math.abs(v[7] - v[8]) < 1e-6)) uBad++; sysOf[v[6]] = (sysOf[v[6]] || 0) + 1; }
}
// the slopes face up
let slopeTris = 0, slopeDown = 0;
for (const p of lmGlass) {
  const P = p.geom.attributes.position.array;
  for (let i = 0; i < P.length; i += 9) {
    const e1 = [P[i + 3] - P[i], P[i + 4] - P[i + 1], P[i + 5] - P[i + 2]], e2 = [P[i + 6] - P[i], P[i + 7] - P[i + 1], P[i + 8] - P[i + 2]];
    slopeTris++; if (e1[2] * e2[0] - e1[0] * e2[2] <= 0) slopeDown++;
  }
}
// the near level's base quads face out (their front side toward their normal), the frames sit over the slopes
const bg = LIB.base.geometry, bp = bg.attributes.position.array, bn = bg.attributes.normal.array, bi = bg.index.array;
let baseBad = 0;
for (let t = 0; t < bi.length; t += 3) {
  const a = bi[t] * 3, b = bi[t + 1] * 3, c = bi[t + 2] * 3;
  const e1 = [bp[b] - bp[a], bp[b + 1] - bp[a + 1], bp[b + 2] - bp[a + 2]], e2 = [bp[c] - bp[a], bp[c + 1] - bp[a + 1], bp[c + 2] - bp[a + 2]];
  const n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
  if (n[0] * bn[a] + n[2] * bn[a + 2] <= 0) baseBad++;
}
const top = (g) => { g.computeBoundingBox(); return g.boundingBox.max.y; };
const lit = themeParts.filter((p) => p.mix === 1), white = themeParts.filter((p) => p.mix === 0);
const red = white.filter((p) => p.color.r > 0.9 && p.color.g < 0.3);
const streams = [bg, LIB.frames.geometry].flatMap((g) => Object.values(g.attributes).map((a) => a.array.constructor.name + a.itemSize));
// the review's day colours: the spire's steel and the tubes on the metal path (a negative gain), nothing lit pale by day
const crownBody = new THREE.Color(0x5d7f9e).multiplyScalar(0.66);
const steel = white.filter((p) => !red.includes(p)), tubes = lit;
const slopeCols = lmGlass.map((p) => p.color);
const glassTop = Math.max(...lmGlass.map((p) => top(p.geom)));
console.log(JSON.stringify({
  slots: [...new Set(themeParts.map((p) => p.slot))], neon: lit.length, neonGain: [...new Set(lit.map((p) => p.gain))],
  whiteTop: Math.max(...white.filter((p) => !red.includes(p)).map((p) => top(p.geom))), redTop: red.map((p) => top(p.geom)), redN: red.length,
  wallTris, wallBad, uBad, sysOf, slopeTris, slopeDown, baseTris: bi.length / 3, baseBad,
  frameTris: LIB.frames.geometry.attributes.position.count / 3, streams,
  appended: appended.map((a) => ({ glass: a.glass, n: a.poly.length, y0: a.y0, y1: a.y1, st: a.st, fh: a.fh })),
  trims: lmTrim.length, crowns: LIB.crowns, feet: LIB.feet.length, tris: LIB.tris, parts: LIB.parts,
  steelGains: [...new Set(steel.map((p) => p.gain))], tubeGains: [...new Set(tubes.map((p) => p.gain))],
  steelLumMax: Math.max(...steel.map((p) => lum(p.color))), tubeLum: Math.max(...tubes.map((p) => lum(p.color))),
  tubeNight: [...new Set(tubes.map((p) => p.lit.getHexString()))], steelNight: [...new Set(steel.map((p) => p.lit.getHexString()))],
  trimLumMax: Math.max(...lmTrim.map((p) => lum(p.color))),
  slopeLum: slopeCols.map(lum), slopeSat: slopeCols.map(sat), crownLum: lum(crownBody), crownSat: sat(crownBody), glassTop,
}));
'''
        for k, v in (('@@THREE@@', THREE), ('@@ART@@', art), ('@@SPECS@@', SPECS), ('@@BOX@@', BOX), ('@@AREA@@', AREA), ('@@PYR4@@', PYR4), ('@@BUILD@@', BUILD)):
            script = script.replace(k, v)
        cls.R = node(script)

    def test_every_gable_edge_lit_and_nothing_else(self):
        R = self.R
        self.assertEqual(R['neon'], 48)          # One: four bays and three tiers, four faces, two slopes; Two: bays and one tier
        self.assertEqual(R['neonGain'], [-1.5])  # Round 85's LED gain, on the metal path by day
        self.assertEqual(R['slots'], [1, 2])     # One then Two, in Round 84's order
        self.assertAlmostEqual(R['redTop'][0], 5 + 288 + 0.2 + 0.55, delta=0.05)   # the beacon on the needle
        self.assertEqual(R['redN'], 1)
        self.assertAlmostEqual(R['whiteTop'], 5 + 288, delta=0.05)   # the needle, white every night

    def test_walls_slopes_and_base_face_out(self):
        R = self.R
        self.assertGreater(R['wallTris'], 150)
        self.assertEqual(R['wallBad'], 0)
        self.assertEqual(R['uBad'], 0)          # the glass shader reads a wall's u as 0 or its length (VBuf's aFacade)
        self.assertEqual(R['slopeTris'], 64 + 8)   # the cross gables' and One's glazed pyramid
        self.assertEqual(R['slopeDown'], 0)
        self.assertGreater(R['baseTris'], 30)
        self.assertEqual(R['baseBad'], 0)
        self.assertEqual(R['frameTris'], R['slopeTris'])

    def test_the_systems_each_face_wears(self):
        R = self.R
        fh = lambda sys: -(sys + 1) / 10   # glassFh: the system rides the floor byte as -(sys + 1)
        sys = {round(float(k), 3) for k in R['sysOf']}
        self.assertIn(round(fh(12), 3), sys)    # the bays' caps
        self.assertIn(round(fh(2), 3), sys)     # Liberty's own above the shaft
        glass = [a for a in R['appended'] if a['glass']]
        self.assertEqual(len(glass), 3)              # One's shaft, Two's and Two's setback stage
        for a in glass:
            self.assertAlmostEqual(a['fh'], fh(7))   # the flanks' ribbons
        self.assertEqual([a['y0'] for a in glass], [5 + 12, 5 + 12, 5 + 182])   # over the granite base: no lobby band in the curtain wall
        self.assertEqual([a['y1'] for a in glass], [5 + 185, 5 + 182, 5 + 207])
        self.assertEqual(glass[2]['n'], 4 * 3)       # the stage's plan, one step a corner
        bases = [a for a in R['appended'] if not a['glass']]
        self.assertEqual([a['y1'] for a in bases], [17, 17])
        self.assertEqual(bases[0]['n'], 4)         # One's base the full square (OSM's 9.7 m part)
        self.assertEqual(bases[1]['n'], 4 * 5)     # Two's on the notched plan (two steps a corner)
        self.assertEqual(glass[0]['n'], 4 * 7)     # One's shaft: three steps a corner

    def test_the_day_colours(self):
        R = self.R
        self.assertEqual(R['steelGains'], [-1])      # the spire, the pyramid's hips, the foot, Two's finial: metal
        self.assertEqual(R['tubeGains'], [-1.5])
        self.assertLess(R['steelLumMax'], 0.2)       # LIB_EDGE at most (the first pass's 0x7d868e matte read 229 in the sun)
        self.assertLess(R['tubeLum'], 0.2)
        self.assertLess(R['trimLumMax'], 0.25)       # the eave, ridge and valley caps a mid silver (0xa7b7c2 was 0.47)
        self.assertEqual(R['tubeNight'], ['535b61'])  # Round 84's light: LIB_SILVER at half
        for c in R['steelNight']:
            self.assertGreater(int(c[:2], 16), 0x5a)   # white every night
        for L, S in zip(R['slopeLum'], R['slopeSat']):
            self.assertGreaterEqual(L, R['crownLum'])          # never darker than the crown's glass (the first pass: 0.42 of it)
            self.assertLess(S, R['crownSat'] * 0.7)            # its hue halfway to grey (the photographs' pale silver blue)
        self.assertAlmostEqual(R['glassTop'], 5 + 254, delta=0.5)   # the pyramid is the crown's glass up to the foot

    def test_the_near_level_streams_are_four_byte_floats(self):
        for s in self.R['streams']:
            self.assertTrue(s.startswith('Float32Array'), s)
        self.assertEqual(self.R['feet'], 2)
        self.assertEqual(len(self.R['crowns']), 2)


class Wiring(unittest.TestCase):
    def test_real0_keeps_round_84(self):
        self.assertIn("      // --- One Liberty Place (17th & Market): sheer blue shaft, four gabled tiers, needle spire\n      if (!REAL) {", SRC)
        self.assertIn("      // --- Two Liberty Place (16th & Chestnut): squatter, two big gable tiers, white finial\n      if (!REAL) {", SRC)
        self.assertIn('crown(cx, cz, base, [[48.5, 212, 226], [36, 223, 237], [26, 233, 244], [17, 242, 251]], gcCrown, cWhite, olSlot, lFh);', SRC)
        self.assertIn('crown(cx, cz, base, [[34, 207, 228], [22, 224, 253]], gcCrown, cWhite, tlSlot, tFh);', SRC)
        self.assertLess(SRC.index('        const DIRS = [[1, 0], [0, 1], [-1, 0], [0, -1]];'), SRC.index('      // --- One Liberty Place (17th & Market)'))

    def test_near_level(self):
        lib = cut('  const LIB_SPECS = [', '  // the rooms\' light by the ambient light')
        self.assertNotIn('gl_FragDepth', lib)
        self.assertNotIn('gl_FragDepth', BUILD)
        self.assertIn('artImage(artSrc(A.img, A.imgHalf))', lib)
        self.assertEqual(lib.count('freeTexOnUpload(t);'), 2)
        self.assertIn('const LIB = { on: REAL && !TIER2 &&', lib)                     # the recovery tier: no near meshes, no art
        self.assertIn('LIB.base.visible = LIB.near && LIB.ready.base;', lib)          # shown once its picture has landed
        self.assertIn('LIB.frames.visible = LIB.framesOn && LIB.ready.glazing;', lib)
        self.assertIn("if (!LIB.asked.base && dF < LIB_DECODE_BASE_R) libLoadArt('base');", lib)
        self.assertIn("if (!LIB.asked.glazing && dC < LIB_FRAME_R) libLoadArt('glazing');", lib)   # its own reach
        self.assertIn('LIB.glzTex = libTexOf(libPremul(A.glazing.caps, A.glazing.cover));', lib)
        self.assertIn("lampLightPatch(sh, 'vWPos', 'wall');", lib)
        self.assertIn('    libStep();   // Round 195', SRC)
        self.assertNotRegex(BUILD, r'Uint8BufferAttribute|Int8BufferAttribute|Uint16BufferAttribute')
        self.assertIn('vdepthNoteOverlay(fg)', BUILD)

    def test_the_art(self):
        A = json.loads((ROOT / 'liberty_art.json').read_text())
        from PIL import Image
        for k in ('base', 'glazing'):
            full, half = ROOT / A[k]['img'], ROOT / A[k]['imgHalf']
            self.assertTrue(full.exists() and half.exists(), k)
            with Image.open(full) as a, Image.open(half) as b:
                (wf, hf), (wh, hh) = a.size, b.size
            self.assertEqual((wh * 2, hh * 2), (wf, hf), k)
            with Image.open(full) as im:
                self.assertEqual(im.mode, 'RGBA', k)
        self.assertEqual(A['base']['m'], [12.0, 12.0])
        self.assertEqual(set(A['base']['cells']), {'lobby', 'wall'})
        self.assertTrue(0.3 < A['base']['means']['lobby']['glass'] < 0.6)
        self.assertTrue(0.02 < A['glazing']['cover'] < 0.08)
        with Image.open(ROOT / A['base']['img']) as im:
            self.assertEqual(im.size, (1024, 512))     # the review's budget: 2.8 MB with its mips on a computer, not 11.2
        # the glazing: ribs along the eave (rows of the tile), the mullions across them faint, never a square grid
        import numpy as np
        with Image.open(ROOT / A['glazing']['img']) as im:
            a = np.asarray(im.convert('RGBA')).astype(float)[..., 3] / 255
        rows, cols = a.mean(1), a.mean(0)
        self.assertGreater(rows.max(), 0.9)
        self.assertLess(cols.max(), 0.35)
        on = rows > 0.5
        self.assertEqual(int((on & ~np.roll(on, 1)).sum()), 2)   # two ribs a 3 m tile: 1.5 m courses
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("LIBERTY_ART", text_of("liberty_art.json", "null"))', b)
        self.assertIn('"glass_art.json", "liberty_art.json"):', b)


if __name__ == '__main__':
    unittest.main()
