"""Round 158: the invisible memory cuts (Mike's iPhone is killed for memory during the late build steps and the first
frames after ready, since WebGL buffers and textures are charged to the page's own WebContent process).

None of these changes what is drawn. Each one lets go of something the page held after its last use, or never builds
what a phone never reads:

- the 43 inline data scripts go at the top of the page's own script, not after the nineteenth late step;
- the street names' SDF atlas is read through one canvas a band high (not a 4096 by 2244 copy), uploaded in its step,
  and a phone drops its 9.2 MB array at the upload;
- the pier and I-95 lamps ask one small numeric grid (the poles near their rings and segments) instead of two string
  grids of all 200,805 poles, with exactly the old answers;
- static canvases and DataTextures free their source at upload on a phone (freeTexOnUpload), the pin badges keeping a
  one-bit alpha for the tap test; the six venue screens share three textures; the unused leaf sprite is not painted;
- the street text, the Northeast Corridor, the lamp glow and the light map's splats free their arrays at upload;
- a phone builds no pole inventory (it has no pole meshes to reconcile);
- the ground registry's normals go when the last conformDrape is done;
- the El's sleepers are gathered without a 28,344-argument spread and its ties' matrices go at upload;
- every material the post-build weather pass re-hooks is disposed, so r149 releases the program it had compiled.

The lamp grid, the SDF band loop, the texture helper and the pin tap test are cut from app.js and run under Node."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


def node(script):
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class LampGrid(unittest.TestCase):
    """The pier and I-95 lamps' 'is a lamp within 10 m' against the old string grids of every pole."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        for name in ('poles.b64', 'i95.json'):
            if not (ROOT / name).exists():
                raise unittest.SkipTest('input absent: ' + name)
        src = (ROOT / 'app.js').read_text()
        block = cut(src, '  function lampNearGrid(', "  step('Lighting the streetlamps'")
        script = r'''
const fs = require('fs');
const raw = Buffer.from(fs.readFileSync(__POLES__, 'utf8'), 'base64'), ab = new ArrayBuffer(raw.length);
new Uint8Array(ab).set(raw);
const head = new Int32Array(ab, 0, 4), v = new Int16Array(ab, 16), N = head[1];
const chains = JSON.parse(fs.readFileSync(__I95__, 'utf8')).chains;
BLOCK
// the old grids, as Round 148 built them: every pole (and, for I-95, every deck and pier lamp) in 20 m string cells
const oldGrid = (extra) => {
  const near = new Map(), key = (x, z) => Math.floor(x / 20) + ':' + Math.floor(z / 20);
  const add = (x, z) => { const k = key(x, z); let a = near.get(k); if (!a) near.set(k, a = []); a.push(x, z); };
  for (let i = 0; i < N; i++) add(v[i * 3] * 0.7, v[i * 3 + 1] * 0.7);
  for (let j = 0; j < extra.length; j += 5) add(extra[j], extra[j + 1]);
  return (x, z) => { const gx = Math.floor(x / 20), gz = Math.floor(z / 20); for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) { const c = near.get((gx + a) + ':' + (gz + b)); if (c) for (let j = 0; j < c.length; j += 2) if ((c[j] - x) ** 2 + (c[j + 1] - z) ** 2 < 100) return true; } return false; };
};
let seed = 12345;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
// rings: rotated rectangles and a few L shapes of 12 to 400 m, each placed near a real pole (so its edges pass poles)
const rings = [];
for (let r = 0; r < 700; r++) {
  const i = Math.floor(rnd() * N), px = v[i * 3] * 0.7 + (rnd() - 0.5) * 60, pz = v[i * 3 + 1] * 0.7 + (rnd() - 0.5) * 60;
  const w = 12 + rnd() * (r % 50 ? 200 : 400), h = 8 + rnd() * 90, a = rnd() * Math.PI, c = Math.cos(a), s = Math.sin(a);
  const loc = r % 7 ? [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]] : [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, 0], [0, 0], [0, h / 2], [-w / 2, h / 2]];
  rings.push({ poly: loc.map(([u, q]) => [px + u * c - q * s, pz + u * s + q * c]) });
}
const grid = lampNearGrid(v, N, rings, chains);
const oldPier = oldGrid([]);
// the pier questions: every edge at a 2 m pitch (the step uses 28 m from any phase), 0.8 m either side of the edge
let pierQ = 0, pierBad = 0, pierYes = 0;
for (const R of rings) {
  const P = R.poly;
  for (let e = 0; e < P.length; e++) {
    const a = P[e], b = P[(e + 1) % P.length], dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz), nx = dz / L, nz = -dx / L;
    for (let t = 0; t < L; t += 2) for (const side of [-0.8, 0.8]) {
      const x = a[0] + dx * t / L + nx * side, z = a[1] + dz * t / L + nz * side, got = grid.near(x, z), want = oldPier(x, z);
      pierQ++; if (want) pierYes++; if (got !== want) pierBad++;
    }
  }
}
// the deck and pier lamps the I-95 block also avoids: points strewn beside the chains and in the rings
const deck = [];
for (const C of chains) for (let e = 0; e + 1 < C.length; e += 3) { const a = C[e]; deck.push(a[0] + (rnd() - 0.5) * 30, a[1] + (rnd() - 0.5) * 30, 0, 0, 12); }
for (const R of rings.slice(0, 200)) deck.push(R.poly[0][0], R.poly[0][1], 0, 0, 7);
for (let j = 0; j < deck.length; j += 5) grid.add(deck[j], deck[j + 1]);
const oldI95 = oldGrid(deck);
// the I-95 questions: every segment at a 3 m pitch (the step uses 50 m from any phase), 7.5 m either side
let i95Q = 0, i95Bad = 0, i95Yes = 0;
for (const C of chains) for (let e = 0; e + 1 < C.length; e++) {
  const a = C[e], b = C[e + 1], dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz);
  if (L < 1e-6) continue;
  const rx = -dz / L, rz = dx / L;
  for (let t = 0; t < L; t += 3) for (const side of [-7.5, 7.5]) {
    const x = a[0] + dx * t / L + rx * side, z = a[1] + dz * t / L + rz * side, got = grid.near(x, z), want = oldI95(x, z);
    i95Q++; if (want) i95Yes++; if (got !== want) i95Bad++;
  }
}
// the old grid itself against brute force, on a sample
let bruteBad = 0;
for (let q = 0; q < 300; q++) {
  const i = Math.floor(rnd() * N), x = v[i * 3] * 0.7 + (rnd() - 0.5) * 30, z = v[i * 3 + 1] * 0.7 + (rnd() - 0.5) * 30;
  let any = false; for (let k = 0; k < N && !any; k++) any = (v[k * 3] * 0.7 - x) ** 2 + (v[k * 3 + 1] * 0.7 - z) ** 2 < 100;
  if (any !== oldPier(x, z)) bruteBad++;
}
const i95Only = lampNearGrid(v, N, [], chains);
console.log(JSON.stringify({ N, pierQ, pierBad, pierYes, i95Q, i95Bad, i95Yes, bruteBad, held: grid.poles, i95Held: i95Only.poles }));
'''.replace('BLOCK', block).replace('__POLES__', json.dumps(str(ROOT / 'poles.b64'))).replace('__I95__', json.dumps(str(ROOT / 'i95.json')))
        cls.r = node(script)

    def test_pier_answers_are_the_old_ones(self):
        r = self.r
        self.assertGreater(r['pierQ'], 50000)
        self.assertGreater(r['pierYes'], 1000)                   # a real share of the questions find a pole
        self.assertLess(r['pierYes'], r['pierQ'] - 1000)         # and a real share do not
        self.assertEqual(r['pierBad'], 0)

    def test_i95_answers_are_the_old_ones(self):
        r = self.r
        self.assertGreater(r['i95Q'], 30000)
        self.assertGreater(r['i95Yes'], 1000)
        self.assertLess(r['i95Yes'], r['i95Q'] - 1000)
        self.assertEqual(r['i95Bad'], 0)

    def test_the_reference_is_brute_force(self):
        self.assertEqual(self.r['bruteBad'], 0)

    def test_the_grid_holds_a_small_share_of_the_poles(self):
        r = self.r
        self.assertGreater(r['N'], 150000)
        self.assertLess(r['i95Held'], r['N'] * 0.2)           # I-95's corridor alone, as the step sees it apart from the piers
        self.assertLess(r['held'], r['N'] * 0.6)              # with 700 synthetic rings strewn across the city on top

    def test_the_step_uses_it_for_both_blocks(self):
        src = (ROOT / 'app.js').read_text()
        s = cut(src, "  step('Lighting the streetlamps'", "  step('Fitting out the rooftops'")
        self.assertEqual(s.count('lampNearGrid('), 1)
        self.assertNotIn("+ ':' + Math.floor(z / 20)", s)      # no string-keyed 20 m grid left
        self.assertIn('const poleNear = lampNear.near;', s)
        self.assertIn('const taken = lampNear.near;', s)
        # the deck lamps join the grid after the pier block and before the I-95 loop, never the I-95 loop's own lamps
        self.assertLess(s.index('const poleNear = lampNear.near;'), s.index('lampNear.add(DECK_LAMPS[j]'))
        self.assertLess(s.index('lampNear.add(DECK_LAMPS[j]'), s.index('for (const C of I95_CHAINS)'))


class SdfBands(unittest.TestCase):
    """The street atlas read a band at a time through one band-high canvas gives the old lum byte for byte."""

    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.step = cut(cls.src, "  step('Lettering the streets'", "  step('Naming the neighborhoods'")

    def test_no_full_size_canvas(self):
        s = self.step[:self.step.index('} else {')]                # the SDF branch (the canvas fallback draws its own atlas)
        self.assertNotIn('cv.height = AH', s)
        self.assertNotIn('g.drawImage(img, 0, 0)', s)
        self.assertIn('cv.height = Math.min(BAND, AH)', s)
        self.assertIn('g.drawImage(img, 0, y, AW, rows, 0, 0, AW, rows)', s)
        self.assertIn('g.getImageData(0, 0, AW, rows)', s)
        self.assertIn("img.removeAttribute('src')", s)
        # the array goes at the upload, and the upload is now
        self.assertLess(s.index('freeTexOnUpload(tex)'), s.index('renderer.initTexture(tex)'))

    def test_band_loop_matches_the_old_read(self):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        block = cut(self.step, '      const BAND = 256;', '      img.onload = img.onerror = null;')
        script = r'''
// a canvas that does what the loop needs exactly: 1:1 drawImage with source-over, clearRect, getImageData, and a
// bitmap cleared whenever its size is set, as a real canvas is
class Canvas {
  constructor() { this.w = 0; this.h = 0; this.px = new Uint8ClampedArray(0); }
  get width() { return this.w; } set width(v) { this.w = v; this.px = new Uint8ClampedArray(this.w * this.h * 4); }
  get height() { return this.h; } set height(v) { this.h = v; this.px = new Uint8ClampedArray(this.w * this.h * 4); }
  getContext() {
    const c = this;
    return {
      clearRect(x, y, w, h) { for (let j = y; j < Math.min(c.h, y + h); j++) for (let i = x; i < Math.min(c.w, x + w); i++) c.px.fill(0, (j * c.w + i) * 4, (j * c.w + i) * 4 + 4); },
      drawImage(img, ...a) {
        const [sx, sy, sw, sh, dx, dy, dw, dh] = a.length === 2 ? [0, 0, img.width, img.height, a[0], a[1], img.width, img.height] : a;
        if (sw !== dw || sh !== dh) throw new Error('not 1:1');
        for (let j = 0; j < sh; j++) for (let i = 0; i < sw; i++) {
          const X = sx + i, Y = sy + j, x = dx + i, y = dy + j;
          if (X < 0 || Y < 0 || X >= img.width || Y >= img.height || x < 0 || y < 0 || x >= c.w || y >= c.h) continue;
          const s = (Y * img.width + X) * 4, d = (y * c.w + x) * 4, sa = img.px[s + 3], da = c.px[d + 3];
          if (sa === 255 || da === 0) { for (let k = 0; k < 4; k++) c.px[d + k] = img.px[s + k]; }
          else if (sa > 0) { for (let k = 0; k < 3; k++) c.px[d + k] = (img.px[s + k] * sa + c.px[d + k] * (255 - sa)) / 255; c.px[d + 3] = sa + da * (255 - sa) / 255; }
        }
      },
      getImageData(x, y, w, h) { const out = new Uint8ClampedArray(w * h * 4); for (let j = 0; j < h; j++) out.set(c.px.subarray(((y + j) * c.w + x) * 4, ((y + j) * c.w + x + w) * 4), j * w * 4); return { data: out }; },
    };
  }
}
const document = { createElement: () => new Canvas() };
let seed = 7;
const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const out = [];
for (const [AW, AH] of [[64, 2244], [48, 256], [40, 100], [32, 513]]) {
  const img = { width: AW, height: AH, px: new Uint8ClampedArray(AW * AH * 4) };
  for (let i = 0; i < img.px.length; i++) img.px[i] = rnd() < 0.2 ? (i % 4 === 3 ? 0 : 255) : Math.floor(rnd() * 256);   // alpha from 0 to 255, so a missing clear would show
  // the old read: the whole atlas in one canvas, bands of rows read out of it
  const old = new Uint8Array(AW * AH);
  { const cv = document.createElement('canvas'); cv.width = AW; cv.height = AH; const g = cv.getContext('2d'); g.drawImage(img, 0, 0);
    for (let y = 0; y < AH; y += 256) { const rows = Math.min(256, AH - y); const px = g.getImageData(0, y, AW, rows).data; for (let i = 0, o = y * AW; i < rows * AW; i++) old[o + i] = px[i * 4]; } }
  const lum = (() => {
BLOCK
    return lum;
  })();
  let diff = 0; for (let i = 0; i < old.length; i++) if (old[i] !== lum[i]) diff++;
  out.push({ AW, AH, diff, n: lum.length, nonzero: lum.some((q) => q > 0) });
}
console.log(JSON.stringify(out));
'''.replace('BLOCK', block)
        for case in node(script):
            self.assertEqual(case['n'], case['AW'] * case['AH'])
            self.assertTrue(case['nonzero'])
            self.assertEqual(case['diff'], 0, case)


class TextureSources(unittest.TestCase):
    """freeTexOnUpload: a phone's static texture lets its source go at upload; the pin tap test survives it."""

    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def run_helper(self, touch):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        helper = cut(self.src, '  function freeTexOnUpload(', '  const PIER_RINGS')
        pins = cut(self.src, '  function pinHitOpaque(', '  function pickPinHit(')
        script = r'''
const THREE = require(THREE_PATH), isTouch = TOUCH, clamp = (v, a, b) => Math.max(a, Math.min(b, v));
HELPER
PINS
const W = 256, H = 320, px = new Uint8ClampedArray(W * H * 4);
let seed = 3; const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
for (let i = 0; i < W * H; i++) px[i * 4 + 3] = rnd() < 0.5 ? 0 : Math.floor(rnd() * 256);
const canvas = { width: W, height: H, getContext: () => ({ getImageData: (x, y, w, h) => { const d = new Uint8ClampedArray(w * h * 4); for (let j = 0; j < h; j++) d.set(px.subarray(((y + j) * W + x) * 4, ((y + j) * W + x + w) * 4), j * w * 4); return { data: d }; } }) };
const tex = new THREE.CanvasTexture(canvas);
const hit = (u, v) => ({ object: { material: { map: tex }, geometry: { attributes: {} } }, uv: new THREE.Vector2(u, v), instanceId: 0 });
const uvs = []; for (let i = 0; i < 4000; i++) uvs.push([rnd(), rnd()]);
const before = uvs.map(([u, v]) => pinHitOpaque(hit(u, v)));
freeTexOnUpload(tex, true);
const hook = typeof tex.onUpdate === 'function';
if (hook) tex.onUpdate(tex);                                   // what r149 does right after the upload
const after = uvs.map(([u, v]) => pinHitOpaque(hit(u, v)));
const data = new THREE.DataTexture(new Uint8Array(16), 2, 2); freeTexOnUpload(data);
const dataHook = typeof data.onUpdate === 'function'; if (dataHook) data.onUpdate(data);
console.log(JSON.stringify({ hook, dataHook, w: canvas.width, h: canvas.height, data: data.image.data === null, same: before.every((b, i) => b === after[i]),
  opaque: before.filter(Boolean).length, mask: !!tex.userData.hitMask, onUpdateLeft: tex.onUpdate }));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('TOUCH', 'true' if touch else 'false').replace('HELPER', helper).replace('PINS', pins)
        return node(script)

    def test_a_phone_frees_the_source_at_upload(self):
        r = self.run_helper(True)
        self.assertTrue(r['hook'] and r['dataHook'])
        self.assertEqual((r['w'], r['h']), (0, 0))
        self.assertTrue(r['data'])
        self.assertTrue(r['mask'])
        self.assertIsNone(r['onUpdateLeft'])                   # the hook runs once

    def test_the_pin_tap_test_is_unchanged(self):
        r = self.run_helper(True)
        self.assertTrue(r['same'])
        self.assertGreater(r['opaque'], 1000)
        self.assertLess(r['opaque'], 3000)

    def test_the_desktop_keeps_its_sources(self):
        r = self.run_helper(False)
        self.assertFalse(r['hook'] or r['dataHook'])
        self.assertEqual((r['w'], r['h']), (256, 320))
        self.assertFalse(r['data'])
        self.assertFalse(r['mask'])
        self.assertTrue(r['same'])

    def test_r149_calls_onupdate_after_the_upload(self):
        three = (ROOT / 'three.min.js').read_text()
        # uploadTexture ends: the image upload, the mips (F(..)&&k(..)), the version, then texture.onUpdate(texture)
        self.assertRegex(three, r'texImage2D\(3553,0,\w+,\w+,\w+,\w+\);F\(\w+,\w+\)&&k\(\w+\),\w+\.__version=\w+\.version,\w+\.onUpdate&&\w+\.onUpdate\(\w+\)')

    def test_the_static_textures_use_it_and_nothing_live_does(self):
        s = self.src
        self.assertIn('return freeTexOnUpload(tex);   // Round 158: drawn once, never redrawn', cut(s, '    const venueTexture = ', '    const venueMapped = '))
        self.assertIn('freeTexOnUpload(', cut(s, '  function pitCmuTexture(', '  function buildGroundPits('))
        self.assertIn('freeTexOnUpload(', cut(s, '  function wildeyTex(', '  function buildWildeyRow('))
        self.assertIn('freeTexOnUpload(new THREE.CanvasTexture(cv))', cut(s, "  step('Naming the neighborhoods'", '  // ---------------------------------------------------------------- address search'))
        self.assertIn('freeTexOnUpload(tex, true)', cut(s, '  function pinMesh(', '  const PIN_RISE'))
        # a texture flagged again after its first upload would upload an empty source: the live ones never take it
        for live in ('indegoTex', 'LAMPMAP.rt', 'lampMapU', 'uGrass', 'tuftTex'):
            for line in s.splitlines():
                if 'freeTexOnUpload(' in line and 'function freeTexOnUpload' not in line:
                    self.assertNotIn(live, line)
        self.assertEqual(len(re.findall(r'\bfreeTexOnUpload\(', s)), 7)   # the definition and its six uses

    def test_venue_screens_share_textures(self):
        s = cut(self.src, '    const venueScreenTex = new Map();', '    const buildStadium = ')
        self.assertIn("const tkey = title + '|' + sub + '|' + accent;", s)
        self.assertIn('venueScreenTex.get(tkey) || venueScreenTex.set(tkey, venueTexture(', s)

    def test_the_leaf_sprite_waits_for_the_cards(self):
        s = self.src
        self.assertEqual(s.count('paintLeafTex('), 2)          # the definition and the one call, inside CARDS ? ... : null
        self.assertIn('const leafMat = CARDS ? new THREE.MeshStandardMaterial({ map: leafTex = paintLeafTex(', s)
        self.assertNotIn('paintLeafTex', cut(s, "  step('Painting the meadow'", "  step('Planting the street trees'"))


class FreedArrays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_late_meshes_free_their_arrays(self):
        s = self.src
        self.assertIn('freeOnUpload(geo);', cut(s, "  step('Lettering the streets'", "  step('Naming the neighborhoods'"))
        nec = cut(s, "  step('Laying the Northeast Corridor'", "  step('Laying the PATCO tracks'")
        self.assertIn('freeOnUpload(mesh.geometry);', nec)
        self.assertIn('freeOnUpload(smesh.geometry);', nec)
        lamps = cut(s, "  step('Lighting the streetlamps'", "  step('Fitting out the rooftops'")
        self.assertIn('freeOnUpload(pg);', lamps)
        self.assertIn('freeOnUpload(g);', lamps)
        # nothing reads them back: the street text, the glow and the splats are only shown, hidden or rendered
        for name in ('stMesh.geometry', 'poleGlow.geometry', 'LAMPMAP.scene.children'):
            self.assertNotIn(name, s)

    def test_a_phone_builds_no_pole_inventory(self):
        lamps = cut(self.src, "  step('Lighting the streetlamps'", "  step('Fitting out the rooftops'")
        self.assertIn('const keepInv = POLE_MESH_CAP > 0;', lamps)
        self.assertIn('const cells = keepInv ? new Map() : null;', lamps)
        self.assertIn('poleInv = keepInv ? { X, Z, GY, HM, ROT, cells, n: nAll } : null;', lamps)
        # the only reader is poleReconcile, which runs only for the desktop's pole meshes
        uses = [m.start() for m in re.finditer(r'poleInv\.', self.src)]
        body = cut(self.src, '  function poleReconcile(', '  function syncLightsBtn(')
        start = self.src.index('  function poleReconcile(')
        self.assertTrue(uses and all(start <= u < start + len(body) for u in uses))
        self.assertIn('if (poleMesh) {', cut(self.src, '  function updateLights(', '  let bfbNodes'))

    def test_the_ground_normals_go_with_the_last_drape(self):
        s = self.src
        paving = cut(s, "  step('Paving the lots and yards'", "  function paveLotsAndYards(")
        self.assertIn('finally { for (const G of groundGrids) G.nrm = null; if (coreRoadGround) coreRoadGround.nrm = null; }', paving)
        end = s.index("  step('Dressing the storefronts'")
        calls = [m.start() for m in re.finditer(r'conformDrape\(', s) if not s[m.start() - 9:m.start()] == 'function ']
        self.assertTrue(calls and max(calls) < end, 'a conformDrape call after the paving step would read nulled normals')
        # the normals' readers: groundPlaneN, called from conformDrape and from groundMeshN, which nothing calls
        self.assertEqual(len(re.findall(r'\bgroundMeshN\(', s)), 1)
        self.assertEqual(len(re.findall(r'\bgroundPlaneN\(', s)), 3)
        code = [ln.strip() for ln in s.splitlines() if '.nrm' in ln and not ln.strip().startswith('//')]
        self.assertEqual(len(code), 3)                                 # the two readers and the frees, nothing else
        self.assertEqual(sum('N = G.nrm;' in ln for ln in code), 2)
        self.assertTrue(any(ln.startswith('try { paveLotsAndYards(); } finally {') for ln in code))
        self.assertNotIn('G.nrm = null', cut(s, '  async function build() {', '  btnEnter.addEventListener('))

    def test_the_data_scripts_go_first(self):
        s = self.src
        top = s[:s.index('// ---------------------------------------------------------------- config')]
        self.assertIn("for (const el of document.querySelectorAll('script[data-blob]')) el.remove();", top)
        self.assertEqual(s.count('script[data-blob]'), 1)
        tpl = (ROOT / 'template.html').read_text()
        self.assertLess(tpl.index('{{DATA}}'), tpl.index('{{APP}}'))

    def test_the_el(self):
        el = cut(self.src, "  step('Raising the Frankford El'", "  // ---- Amtrak's tracks")
        self.assertNotIn('push(...', el)
        self.assertIn('ties.instanceMatrix.onUpload(dropUploadedArray);', el)
        self.assertEqual(el.count('ties.setMatrixAt('), 1)
        self.assertEqual(self.src.count("'El Cross Ties'"), 1)


    def test_no_upload_callback_closes_over_a_step(self):
        # a callback written inline in a build step keeps that step's whole scope alive with it: Round 158 measured an inline
        # one on the El's ties holding every box and ribbon of the El step (6 MB of objects, 7 MB of arrays) at ready
        s = self.src
        self.assertIn('\n  function dropUploadedArray() { this.array = null; }\n', s)   # at the IIFE's top level
        a = s.index('  function freeOnUpload(')
        b = s.index('  function unb64(', a)                      # freeOnUpload's own callbacks are made in its own small scope
        for m in re.finditer(r'\.onUpload\(', s):
            if a <= m.start() < b:
                continue
            self.assertTrue(s.startswith('.onUpload(dropUploadedArray)', m.start()), s[m.start() - 80:m.start() + 60])


class ProgramRelease(unittest.TestCase):
    def test_rehooked_materials_are_disposed(self):
        src = (ROOT / 'app.js').read_text()
        s = cut(src, '  build().then(() => {', "    if (/[?&]dev\\b/.test(location.search)) {")
        self.assertLess(s.index("cityMat.customProgramCacheKey = () => 'fabric|wx';"), s.index('cityMat.dispose();'))
        self.assertLess(s.index("coreMat.customProgramCacheKey = () => 'fabric-core|wx';"), s.index('coreMat.dispose();'))
        self.assertEqual(s.count('m.dispose();'), 2)             # the wrapped wxSurf flats and the hookless standard materials
        self.assertLess(s.index("m.customProgramCacheKey = () => 'wx|' + prev.toString();"), s.index('m.dispose();'))
        self.assertLess(s.index('m.onBeforeCompile = wxSurfacePatch;'), s.rindex('m.dispose();'))

    def test_r149_dispose_releases_programs_only(self):
        three = (ROOT / 'three.min.js').read_text()
        # the renderer's material 'dispose' handler: drop the listener, release every program in the material's own map
        # (and a ShaderMaterial's shader cache), forget its properties; no texture or geometry is touched
        m = re.search(r'function ([\w$]+)\(t\)\{const e=t\.target;e\.removeEventListener\("dispose",\1\),function\(t\)\{\(function\(t\)\{const e=([\w$]+)\.get\(t\)\.programs;void 0!==e&&\(e\.forEach\(\(function\(t\)\{([\w$]+)\.releaseProgram\(t\)\}\)\),t\.isShaderMaterial&&\3\.releaseShaderCache\(t\)\)\}\)\(t\),\2\.remove\(t\)\}\(e\)\}', three)
        self.assertIsNotNone(m)
        # and getProgram starts a fresh programs map (and listens again) when a disposed material next renders
        self.assertRegex(three, r'void 0===\w+&&\(\w+\.addEventListener\("dispose",' + re.escape(m.group(1)) + r'\),\w+=new Map,\w+\.programs=\w+\)')
        # a program is deleted only when no material holds it any more
        self.assertIn('releaseProgram:function(t){if(0==--t.usedTimes)', three)


if __name__ == '__main__':
    unittest.main()
