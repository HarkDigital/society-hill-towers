"""Round 189 (Mike: "Do the storefront boxes on Broad Street too"): the page's generated shopfronts.

- the realistic look on WebGL 2 with the art (SF_ART_ON) builds the panels; ?real=0, ?sfart=0, WebGL 1 or art that does
  not arrive in 10 s build the old boxes exactly as before, inline in the step (their strings stand where they stood);
- the hooks are written at the top level, never in the step (a hook written in a build step keeps its whole scope);
- every stream the panels and their awnings upload is Float32 at a stride of 4, 8, 12 or 16 (a phone: Round 158);
- the names' atlas is red only, never freed on upload (its slots are written after it), and the step's slots stream stays;
- the sidecar is used only when its count is the blob's;
- the painted shop floors (style 5) take the same atlas in the facade hook behind SF_PARTA (REAL and WebGL 2) and uSfOn;
- build.py inlines the sidecar and the manifest and holds the manifest to the art guards.

The review (Round 189's second pass): the old boxes' step is byte for byte what it was before the round, less the new
path (a sha pins it); the art is on at every phone tier (Round 219); one awning program; the decoded images let go; the names' canvas read
often and their mips rebuilt on the last copy that runs; the panels into the scene only when everything has been made;
the parallax held inside its cell; every test made at the laid span; the painted shop floors never painted once the art
is up.

The second review: every test made 1.2 m inside the wall's measured line (five tower panels stood in the air); the wall's
material kept off the painted shop floors' shopfronts (a phone beaded every pane with mortar) and their units only from
3.4 m; the awnings' own depth material; the art decoded into ImageBitmaps on a computer and uploaded a task at a time; and
Build, which runs sfBuild itself under Node over the real records."""
import hashlib
from pathlib import Path
import re
import unittest

# the 'Dressing the storefronts' step as it stood before Round 189 (08350a5), which the step less its new path must still be
# (Round 198: its base cells take the own facades' bases too, baseOwn, so a box never doubles a building's own shopfronts
# under ?sfart=0 either; 300fc5a7 before it)
LEGACY_SHA = 'f10d4354a57284491ddff008e134fb8eed4b1d61759b07123763c15def783a1d'

ROOT = Path(__file__).resolve().parents[1]


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        cls.block = cut(cls.s, "  // ---- the storefronts' shopfronts (Round 189", "  step('Dressing the storefronts'")
        cls.step = cut(cls.s, "  step('Dressing the storefronts'", "  step('Raising the overpasses'")

    def test_the_gates(self):
        self.assertIn("const SF_ART_ON = REAL && !!renderer.capabilities.isWebGL2 && typeof STOREFRONT_ART !== 'undefined' && !!STOREFRONT_ART && !!STOREFRONT_ART.cells && !/[?&]sfart=0\\b/.test(location.search);", self.block)
        self.assertIn("const SF_SIGNS = SF_ART_ON && !/[?&]signs=0\\b/.test(location.search);", self.block)
        self.assertIn("const SF_PARTA = REAL && !!renderer.capabilities.isWebGL2 && typeof STOREFRONT_ART !== 'undefined'", self.s)

    def test_the_old_boxes_stay_as_they_were(self):
        st = self.step
        new = st.index('if (SF_ART_ON) {')
        old = st.index('    let nearN = 0, baseN = 0;\n    for (let i = 0; i < n; i++) {')
        self.assertLess(new, old)
        legacy = st[old:]
        for line in ("parts.push({ geom: mk(w - 0.2, glassH + 0.5, 0.10, 0.12, gy + 0.25 + (glassH + 0.5) / 2, 0), color: cFrame, style: 3, near });",
                     "if (flags & 1) parts.push({ geom: mk(w - 0.5, 0.12, 1.1, 0.62, gy + fh + 0.05, -0.32), color: AWNING[col], style: 3, near });",
                     "'#include <emissivemap_fragment>\\ntotalEmissiveRadiance += vLit * uNight * 2.2;'",
                     'STOREFRONT_N = made; STOREFRONT_NEAR = nearN; STOREFRONT_BASE = baseN;'):
            self.assertIn(line, legacy)
        # the new path returns only when it built; art late or failed falls through to the boxes
        newp = st[new:old]
        self.assertIn("const got = await Promise.race([sfArtLoad(), new Promise((r) => { late = setTimeout(() => r(null), SF_ART_WAIT); })]);\n      clearTimeout(late);\n      sfArtP = null;", newp)
        # the two uploads a task each (the review: one 342 ms task), the build's own yield (a timer sleeps in a hidden tab)
        self.assertIn("try { renderer.initTexture(map); } catch (e) { }\n        await yieldNow();\n        try { renderer.initTexture(mask); } catch (e) { }\n        await yieldNow();", newp)
        # a computer decodes the art into ImageBitmaps (flipped as decoded, closed once uploaded), but not an old desktop
        # Safari or Firefox, which ignore the flip (the third review); a phone keeps its <img>
        b = self.block
        gate = cut(b, '  const SF_BITMAP = (() => {', '  })();')
        self.assertIn("if (isTouch || typeof createImageBitmap !== 'function'", gate)
        self.assertIn("return !!m && +m[1] >= 17;", gate)
        self.assertIn("return !!m && +m[1] >= 98;", gate)
        self.assertIn("if (SF_BITMAP) {", b)
        self.assertIn("createImageBitmap(im, { imageOrientation: 'flipY', premultiplyAlpha: 'none' })", b)
        # the third review (MUST): a phone fetches only the art's bytes at the top of the build and decodes its <img> at the
        # step, so no decoded image is held through the far ring's uploads
        self.assertIn("if (SF_ART_ON) { if (isTouch) sfArtPrefetch(); else sfArtLoad(); }", cut(self.s, '  async function build() {', '    let failures = 0;'))
        pre = cut(b, '  function sfArtPrefetch() {', '  function sfArtLoad() {')
        self.assertIn('fetch(src).then((r) => (r.ok ? r.blob() : null))', pre)
        self.assertNotIn('decode', pre)
        self.assertNotIn('artImage', pre)
        self.assertIn("tex.flipY = false;", cut(self.s, '  function sfBitmapTex(', '  function sfTextures('))
        self.assertIn("return [sfBitmapTex(map), sfBitmapTex(mask)];", b)
        self.assertIn("if (built) { SF.state = 'built'; STOREFRONT_N = SF.n; STOREFRONT_NEAR = SF.near; STOREFRONT_BASE = SF.base; return; }", newp)
        self.assertNotIn('onBeforeCompile', newp)
        self.assertNotIn('aFrontNear', self.block)

    def test_the_old_step_is_byte_for_byte_as_it_was(self):
        st = cut(self.s, "  step('Dressing the storefronts', async () => {", "  // the realism pass: a photographed face (STREET_ART)")
        a, b = st.index('    // Round 189: the generated shopfronts (sfBuild)'), st.index('    let nearN = 0, baseN = 0;\n')
        old = (st[:a] + st[b:]).replace("step('Dressing the storefronts', async () => {", "step('Dressing the storefronts', () => {", 1)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), LEGACY_SHA)

    def test_the_review(self):
        b = self.block
        # one awning program for the flat and the scalloped, the lobes cut by the metre
        self.assertIn("m.customProgramCacheKey = () => 'storefront-awnings|wx';", b)
        self.assertIn('nS = max(2.0, floor(vAwnLen / 0.33 + 0.5))', b)
        self.assertEqual(b.count('new THREE.InstancedMesh('), 2)
        # the names: a canvas read often, the released slots dropped before the batch, the setup on its own
        self.assertIn("c.getContext('2d', { willReadFrequently: true })", b)
        self.assertIn('const todo = S.queue.splice(0, max).filter((s) => S.owner[s] >= 0);', b)
        self.assertIn('try { sfNamesInit(); } catch (e) {', b)
        build = cut(self.s, '  function sfBuild(', '  // ---- the names (Round 189)')
        self.assertLess(build.index('am = new THREE.InstancedMesh('), build.index('groupCity.add(mesh);'))
        self.assertLess(build.index('groupCity.add(mesh);'), build.index('try { sfNamesInit(); }'))
        # every test at the laid span and the wall's own line (Build below runs them): the custom models and the street
        # floors at its middle, the fronts at its ends
        self.assertIn('if (ownsIt(wx - nx * 1.2, wz - nz * 1.2)) continue;', build)
        self.assertIn('for (const s of [-e, 0, e]) sfFrontsAt(frCells, wx - nz * s, wz + nx * s, nx, nz, frSet);', build)
        # the parallax held in its cell, the returns' pier by depth
        self.assertIn("vec2 uv2 = clamp(sfUv + du, vSfCell.xy + ' + SF_TX + ', vSfCell.xy + vSfCell.zw - ' + SF_TX + ');", b)
        self.assertIn("-position.z * length(instanceMatrix[2].xyz)", b)
        self.assertNotIn('mix(0.012, 0.988', b)

    def test_the_hooks_live_at_the_top(self):
        for name in ('sfPanelHook', 'sfAwningHook', 'sfPanelMat', 'sfAwningMat', 'sfBuild', 'sfNamesInit', 'sfStep'):
            self.assertIn('  function ' + name + '(', self.block)
            self.assertNotIn('function ' + name + '(', self.step)
        self.assertIn("m.customProgramCacheKey = () => rich ? 'storefront-panels|wx' : 'storefront-panels|wx|lite';", self.block)
        # the panel's dissolve is the fronts' own dither line on the instance's near flag
        self.assertIn('if (ign <= 1.0 - smoothstep(uFrR * 0.8, uFrR, fd)) discard; }', self.block)
        self.assertIn("lampLightPatch(sh, 'vSfW', 'wall');\n    wxSurfacePatch(sh);", self.block)
        # every read is textureGrad, from gradients taken in uniform flow at the top of main
        self.assertIn("'sfDx = dFdx(vSfP.xy); sfDy = dFdy(vSfP.xy);',", self.block)
        self.assertNotIn('texture2D(uSf', self.block)

    def test_every_stream_is_four_byte_aligned(self):
        b = self.block
        self.assertFalse(re.search(r'new (Uint8|Int8|Uint16|Int16)Array\([^)]*\)\s*,\s*\d', b))
        for m in re.finditer(r'new THREE\.(Float32BufferAttribute|InstancedBufferAttribute|BufferAttribute)\(([^;]*)', b):
            args = m.group(2)
            if m.group(1) != 'Float32BufferAttribute':
                self.assertIn('Float32Array', args, args)
            if args.startswith('new Float32Array(N * k), k)'):
                continue   # the helper below, called with 4 and 1
            k = re.search(r',\s*(\d)\)', args)
            self.assertTrue(k and int(k.group(1)) in (1, 2, 3, 4), args)
        self.assertIn('const at = (k) => new THREE.InstancedBufferAttribute(new Float32Array(N * k), k);', b)
        self.assertIn('const aCell = at(4), aBand = at(4), aDim = at(4), aInfo = at(4), aHours = at(4), aSlot = at(1);', b)
        self.assertNotIn('setColorAt', cut(self.s, '  function sfPanelGeometry(', '  function sfAwningHook('))

    def test_the_names(self):
        b = self.block
        init = cut(self.s, '  function sfNamesInit(', '  function sfNamesRedraw(')
        self.assertIn('tex.format = THREE.RedFormat;', init)
        self.assertNotIn('freeTexOnUpload', init)
        self.assertIn('renderer.initTexture(tex)', init)
        self.assertIn('renderer.copyTextureToTexture(_sfPos.set(col * S.SW, (S.rows - 1 - row) * S.SH), S.cell.tex, S.tex);', b)
        build = cut(self.s, '  function sfBuild(', '  function sfNamesInit(')
        self.assertNotIn('freeOnUpload(geo)', build)   # aSfSlot is rewritten by the names
        self.assertIn('for (const a of [aCell, aBand, aDim, aInfo, aHours]) { a.onUpload(dropUploadedArray); }', build)
        self.assertIn("aSlot.setUsage(THREE.DynamicDrawUsage);", build)
        self.assertIn('sfStep(now);   // Round 189', self.s)

    def test_the_sidecar_is_checked(self):
        f = cut(self.s, '  function sfInfo(', '  // the review: a panel and a generated house front on one wall')
        self.assertIn('if (!I || I.n !== n || !I.rec) return null;', f)
        self.assertIn('return rec.length === n * st ?', f)

    def test_the_painted_shop_floors(self):
        s = self.s
        self.assertIn("if (SF_PARTA) Object.assign(shader.uniforms, sfPartU);", s)
        # once the art is up no painted shop floor is painted: the panes and the awning band go from every style-5 wall,
        # one too short or too low for a shopfront keeping masonry and the style's sashes (the review)
        self.assertIn("'      if (st == 5 && uSfOn > 0.5) {',\n            '        isShop = 0.0;',", s)
        self.assertIn("'        if (local && wallTop >= 2.9 && vWallL >= ' + SF_PARTA_MIN.toFixed(2) + ' && det > 0.001) {',", s)
        # the wall's material kept off the whole shopfront (the review: a phone drew the brick's mortar round every pane)
        self.assertIn("glass = mix(glass, sfM.r, sfUse); trimM = mix(trimM, 1.0, sfUse);", s)
        self.assertNotIn('1.0 - sfM.r', s)
        self.assertIn("SF_PARTA ? '      awnOn *= 1.0 - step(0.5, uSfOn);' : '',", s)
        # no two units side by side share a cell (a stride of 1, 3, 5 or 7 of the class's eight)
        self.assertIn("mod(floor(hw * 8.0) + sfUi * (1.0 + 2.0 * floor(fract(hw * 7.13) * 4.0)), 8.0)", s)
        # the paint stands where the art does not: the painted shop and awning strings are as they were
        self.assertIn("'      float shop = rectM(m, vec2(0.0, 1.7), vec2(1.5, 2.5), aa) * isShop;',", s)
        self.assertIn("'      float awnOn = step(3.72, wallTop) * float(st == 5) * inWall * det * step(fv, 4.0);',", s)
        self.assertIn("if (SF_PARTA) { sfPartU.uSfArt.value = map; sfPartU.uSfMaskA.value = mask; sfPartU.uSfOn.value = 1; SF.partA = true; }", self.step)
        # a cell's corner packed as x + w y by the atlas's own width on both sides (the third review: 4096 written in)
        self.assertIn("U.uSfGen.value[k].set(px + A.w * py,", s)
        self.assertIn("float gyq = floor(G.x / ' + SF_AW + ' + 0.0001); vec2 g0 = vec2(G.x - gyq * ' + SF_AW + ', gyq)", s)
        self.assertIn('STOREFRONT_ART.w * STOREFRONT_ART.h <= 16777216', s)
        self.assertNotIn('4096 * py', s)
        # the slot's index rounded like every other word decoded from a varying
        self.assertIn('float s = floor(vSfBand.w + 0.5), cl = mod(s, uSfSlots.x)', s)
        # the stripes filtered over the pixel on both awnings (the fronts' under the realistic look only)
        self.assertEqual(s.count('awnStripe(awT, awW)'), 2)
        self.assertIn("'float awnStripeW(float t) { return length(vec2(dFdx(t), dFdy(t))); }", s)

    def test_the_build(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("STOREFRONT_INFO", text_of("storefront_info.json", "null"))', b)
        self.assertIn('const("STOREFRONT_ART", text_of("storefront_art.json", "null"))', b)
        self.assertRegex(b, r'for name in \([^)]*"storefront_art\.json"[^)]*\):')

    def test_no_dash_in_what_shows(self):
        b = self.block
        for c in ('—', '·'):
            self.assertNotIn(c, b)


# the page's storefront block under Node with the vendored three.min.js and the real art manifest, sidecar and records:
# the rest of the page is stubbed (the ground flat, every sidewalk there, the house fronts a buffer the test lays)
_STUBS = r"""
const THREE = require(__THREE__);
const fs = require('fs');
const location = { search: '' };
const atob = (b) => Buffer.from(b, 'base64').toString('binary');
const STOREFRONT_ART = JSON.parse(fs.readFileSync(__ART__, 'utf8')), STOREFRONT_INFO = JSON.parse(fs.readFileSync(__INFO__, 'utf8'));
const REAL = true, TIER2 = false, FRONTS_ON = true, isTouch = false;
const renderer = { capabilities: { isWebGL2: true, getMaxAnisotropy: () => 8 } };
const camera = new THREE.PerspectiveCamera();
const nightUniform = { value: 0 }, sunWUniform = { value: new THREE.Vector3() }, frR = { value: 380 }, frShopOn = { value: 1 };
const FR_STRIDE = 10, FR_SETS = ['row', 'shop', 'mixeduse', 'shop1', 'loft'], FR_SET_IX = (n) => FR_SETS.indexOf(n), FR_SHOPPY = new Set([1, 2, 3, 4]);
const FR_AREAS = { cc: null }, frIn = () => false;
let FRONTS = { n: 0, buf: new Float32Array(0), side: null, r: 380 };
const frontSide = () => 0;
const groundMeshY = () => 0, siteY = () => 0, sidewalkAt = () => true, SIDEWALK_UP = 0.15;
const groupCity = new THREE.Group();
function dropUploadedArray() { this.array = null; }
const freeOnUpload = (g) => g, freeTexOnUpload = (t) => t;
const frontStored = (h) => new THREE.Color(h);
function frontAwning(A) { A.pos.push(0, 0, 0, 1, 0, 0, 0, 1, 0); A.nor.push(0, 0, 1, 0, 0, 1, 0, 0, 1); A.along.push(0, 1, 0); }
const glassOpticsPatch = () => {}, lampLightPatch = () => {}, wxSurfacePatch = () => {};
const artImage = () => Promise.resolve(null), artSrc = (a) => a;
const SF_PARTA = true, SF_PARTA_MIN = 3.4;
const unb64 = (b) => { const u = Buffer.from(b, 'base64'); return new Uint8Array(u.buffer.slice(u.byteOffset, u.byteOffset + u.length)); };
let STOREFRONT_N = 0, STOREFRONT_NEAR = 0, STOREFRONT_BASE = 0;
const BL_ON = false;   // the realism round two's blade signs (their own section, not the block's): off here
__HASH01__
__BLOCK__
const raw = Buffer.from(fs.readFileSync(__B64__, 'utf8').trim(), 'base64');
const ab = raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.length);
const n = new Int32Array(ab, 0, 4)[1], body = new Int16Array(ab, 16);
const I = sfInfo(n);
"""


class Build(unittest.TestCase):
    """The review: sfBuild run, not read. Every test a record meets is made at its wall's measured line; the panel's face
    stands there; no two panels within 15 m facing the same way wear one cell; a house front under a panel becomes its
    shop set only once the build has succeeded; a cut name keeps no connector at its end; the painted shop floors' units
    never repeat side by side and stop where the panels do."""

    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def run_js(self, tail):
        import json, os, shutil, subprocess, tempfile
        if not shutil.which('node'):
            self.skipTest('node is not installed')
        s = self.s
        js = (_STUBS.replace('__THREE__', json.dumps(str(ROOT / 'three.min.js')))
              .replace('__ART__', json.dumps(str(ROOT / 'storefront_art.json'))).replace('__INFO__', json.dumps(str(ROOT / 'storefront_info.json')))
              .replace('__B64__', json.dumps(str(ROOT / 'storefronts.b64')))
              .replace('__HASH01__', cut(s, '  function hash01(n)', '\n'))
              .replace('__BLOCK__', cut(s, "  // ---- the storefronts' shopfronts (Round 189", "  step('Dressing the storefronts'"))) + tail
        fd, fn = tempfile.mkstemp(suffix='.cjs')
        try:
            os.write(fd, js.encode()); os.close(fd)
            out = subprocess.run(['node', fn], capture_output=True, text=True, timeout=120)
        finally:
            os.unlink(fn)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout.strip().splitlines()[-1])

    def test_every_test_at_the_wall_and_the_face_on_it(self):
        r = self.run_js(r"""
// the records sfBuild reaches its tests with, in its order, and where each test should be made: 1.2 m inside the wall's
// measured line (the record's line moved out by the sidecar's out), on the panel's turned normal
const want = [];
for (let i = 0; i < n; i++) {
  const o = i * 8, q = i * I.st, r = I.rec;
  if (body[o + 3] / 10 < 2.5 || body[o + 6] / 10 < 2.5 || r[q + 1] <= 0) continue;
  const ang = body[o + 2] / 1000, x = body[o] * 0.2, z = body[o + 1] * 0.2, shift = r[q] / 10, out = r[q + 2] / 100, lean = r[q + 8] / 10000;
  let nx = Math.cos(ang), nz = Math.sin(ang);
  const cx = x - nz * shift, cz = z + nx * shift, n0 = [nx, nz];
  if (lean) { const k = 1 / Math.sqrt(1 + lean * lean), tx = -nz, tz = nx; nx = (nx - tx * lean) * k; nz = (nz - tz * lean) * k; }
  want.push({ i, cx, cz, n0, nx, nz, out, w: r[q + 1] / 10, name: I.names[i] });
}
const asked = [], based = [];
// a street floor drawn 2.64 m behind Insomnia Cookies' record line (where the bake measures its tower's base): the point a
// metre and a fifth inside the wall finds it, the old point inside the record's line did not
const ins = want.find((w) => w.name === 'Insomnia Cookies' && w.out < -2);
const onBase = (x, z) => { based.push([x, z]); const dx = x - ins.cx, dz = z - ins.cz; return Math.hypot(dx, dz) < 8 && dx * ins.n0[0] + dz * ins.n0[1] < -2.64; };
sfBuild(body, n, (x, z) => { asked.push([x, z]); return false; }, onBase, true);
let bad = 0, worst = 0;
want.forEach((w, k) => {
  const p = asked[k], wx = w.cx + w.n0[0] * w.out, wz = w.cz + w.n0[1] * w.out;
  const d = Math.hypot(p[0] - (wx - w.nx * 1.2), p[1] - (wz - w.nz * 1.2));
  worst = Math.max(worst, d); if (d > 1e-3) bad++;
});
// the faces: the front's middle on the wall's line plus 6 cm, on the panel's own normal, at the laid middle
const M = SF.mesh.instanceMatrix.array, L = SF.list, laid = want.filter((w) => w !== ins);
let faceBad = 0, faceWorst = 0;
laid.forEach((w, k) => {
  const o = k * 16, fx = M[o + 12] + 0.5 * M[o], fz = M[o + 14] + 0.5 * M[o + 2];
  const ex = w.cx + w.nx * (w.out + 0.06), ez = w.cz + w.nz * (w.out + 0.06);
  const d = Math.hypot(fx - ex, fz - ez); faceWorst = Math.max(faceWorst, d); if (d > 1e-3) faceBad++;
  if (Math.abs(Math.hypot(M[o], M[o + 2]) - w.w) > 1e-3) faceBad++;
});
console.log(JSON.stringify({ want: want.length, asked: asked.length, based: based.length, bad, worst, made: SF.n, base: SF.base, faceBad, faceWorst, insOut: ins.out }));
""")
        self.assertEqual(r['asked'], r['want'])
        self.assertEqual(r['based'], r['want'])
        self.assertEqual(r['bad'], 0, r)
        self.assertLessEqual(r['insOut'], -2.5)
        self.assertEqual(r['base'], 1)                    # Insomnia Cookies, on its tower's street floor
        self.assertEqual(r['made'], r['want'] - 1)
        self.assertEqual(r['faceBad'], 0, r)

    def test_no_neighbour_wears_the_same_cell(self):
        # the third review: within 30 m, whichever way they face (Ho Sai Gai and Jade Harbor across 10th Street, corners);
        # a pair is allowed only where the later panel found every cell it may wear already worn (SF.repeats)
        r = self.run_js(r"""
sfBuild(body, n, () => false, () => false, false);
const L = SF.list, C = SF.cellOf; let pairs = 0, near = 0, R = SF_NEIGH_R;
for (let a = 0; a < SF.n; a++) for (let b = a + 1; b < SF.n; b++) {
  const pa = a * 9, pb = b * 9, d2 = (L[pa] - L[pb]) ** 2 + (L[pa + 2] - L[pb + 2]) ** 2;
  if (C[a] === C[b] && d2 < R * R) { pairs++; if (d2 < 225) near++; }
}
console.log(JSON.stringify({ n: SF.n, pairs, near, repeats: SF.repeats, R }));
""")
        self.assertGreater(r['n'], 1300)
        self.assertEqual(r['R'], 30)
        self.assertLessEqual(r['pairs'], r['repeats'], r)
        self.assertLessEqual(r['repeats'], 10, r)

    def test_a_front_is_switched_only_when_the_build_stands(self):
        r = self.run_js(r"""
// a row house's front laid on the first panel's wall (its street side the panel's normal), its set 'row'
let k0 = -1, w0 = null;
for (let i = 0; i < n && k0 < 0; i++) { const q = i * I.st; if (I.rec[q + 1] > 0 && body[i * 8 + 3] >= 25 && body[i * 8 + 6] >= 25) k0 = i; }
{ const o = k0 * 8, q = k0 * I.st, ang = body[o + 2] / 1000, nx = Math.cos(ang), nz = Math.sin(ang), sh = I.rec[q] / 10, out = I.rec[q + 2] / 100;
  const cx = body[o] * 0.2 - nz * sh + nx * (out - 2), cz = body[o + 1] * 0.2 + nx * sh + nz * (out - 2);
  FRONTS = { n: 1, buf: new Float32Array([cx, cz, nx, nz, 2.5, 7, 0, 9, 0, 0]), side: null, r: 380 }; }
const real = THREE.InstancedMesh;
THREE.InstancedMesh = function () { throw new Error('test'); };
let threw = false;
try { sfBuild(body, n, () => false, () => false, false); } catch (e) { threw = true; }
const after = FRONTS.buf[9];
THREE.InstancedMesh = real;
sfBuild(body, n, () => false, () => false, false);
console.log(JSON.stringify({ threw, after, set: FRONTS.buf[9], switched: SF.switched, near: SF.list[6] }));
""")
        self.assertTrue(r['threw'])
        self.assertEqual(r['after'], 0)        # nothing switched by a build that did not stand
        self.assertEqual(r['set'], 1)          # 'shop': 9 m, under the mixed-use 13.5 m
        self.assertEqual(r['switched'], 1)
        self.assertEqual(r['near'], 1)         # and the panel gives way near the eye to the front's own shopfront

    def test_a_panel_on_a_painted_shop_floor_takes_its_units(self):
        # the third review: a panel on a style-5 wall cut the facade shader's own shopfronts through a door and their fascia
        # showed over its top. A 25 m wall along a laid record's line, from 9.5 m before its middle: the shader's units are
        # three of 8.33 m (sfHostNote's grid, the facade hook's own rule); the panel goes to the joints and over the fascia
        r = self.run_js(r"""
var STOREFRONTS_B64 = raw.toString('base64');
let k0 = -1;
for (let i = 0; i < n && k0 < 0; i++) { const p = sfPlace(body, I, i); if (p && !p.hidden && p.w >= 4 && p.w <= 7) k0 = i; }
const p0 = sfPlace(body, I, k0), tx = -p0.nz, tz = p0.nx, s0 = -9.5;
const a = [p0.wx + tx * s0, p0.wz + tz * s0], q = [p0.wx + tx * (s0 + 25), p0.wz + tz * (s0 + 25)];
sfHostNote(a, q, 25, p0.nx, p0.nz, 5, 1.0, 0.0, 13.0, 0);
const ht = SF_HOST.at.get(k0);
const g = [Object.assign(sfPlace(body, I, k0), { host: ht.h })];
sfSnapRun(g);
const U = ht.h.unit, lo = g[0].s - g[0].w / 2, hi = g[0].s + g[0].w / 2;
const top = sfPartTop(12.0, 0, 5);
sfBuild(body, n, () => false, () => false, false);
console.log(JSON.stringify({ k0, U, nu: ht.h.nu, lo: lo / U, hi: hi / U, w0: p0.w, w: g[0].w, onLine: Math.hypot(g[0].wx - (a[0] + tx * g[0].s), g[0].wz - (a[1] + tz * g[0].s)),
  top, hostTop: ht.h.top, partTop: g[0].partTop, moved: SF_HOST.moved, raised: SF_HOST.raised, walls: SF_HOST.walls }));
""")
        self.assertEqual(r['nu'], 3)
        self.assertAlmostEqual(r['U'], 25 / 3, 3)
        self.assertAlmostEqual(r['lo'], round(r['lo']), 4)        # both ends on the units' joints
        self.assertAlmostEqual(r['hi'], round(r['hi']), 4)
        self.assertGreaterEqual(round(r['hi']) - round(r['lo']), 1)
        self.assertLess(r['onLine'], 1e-3)                          # seated on the wall's own line
        self.assertAlmostEqual(r['top'], 3.75 / ((3 * 3.05 + 2.94) / (12.0 - 0.9 - 0.04)), 4)   # the shader's sfHh / facadeScale
        self.assertAlmostEqual(r['hostTop'], 1.0 + r['top'], 4)
        self.assertGreaterEqual(r['moved'], 2)                      # the run above, and sfBuild's own
        self.assertGreaterEqual(r['raised'], 1)                     # its top over the fascia (4.43 m over a sidewalk at 0.15)

    def test_every_instance_inside_its_sphere(self):
        # the third review: the water mirror's reach read the unit panel's sphere at the scene's origin
        r = self.run_js(r"""
sfBuild(body, n, () => false, () => false, false);
const out = [];
for (const m of [SF.mesh, SF.awn[0]]) {
  const S = m.geometry.boundingSphere, M = m.instanceMatrix.array, v = new THREE.Vector3(), mt = new THREE.Matrix4();
  let bad = 0;
  for (let k = 0; k < m.count; k++) { mt.fromArray(M, k * 16); for (const c of [[0, 0, 0], [1, 1, -1], [1, 0, 0], [0, 1, 0]]) { v.set(...c).applyMatrix4(mt); if (v.distanceTo(S.center) > S.radius + 1e-3) bad++; } }
  out.push({ n: m.count, bad, r: Math.round(S.radius) });
}
console.log(JSON.stringify(out));
""")
        for m in r:
            self.assertGreater(m['n'], 600)
            self.assertEqual(m['bad'], 0, m)
            self.assertGreater(m['r'], 1000)

    def test_a_cut_name_keeps_no_connector(self):
        r = self.run_js(r"""
console.log(JSON.stringify(['IDK Smash Burgerz &', 'Hand & Stone Massage and', 'Taqueria de', 'Salt, Pepper,', 'Pub On Passyunk'].map(sfTrimTail)));
""")
        self.assertEqual(r, ['IDK Smash Burgerz', 'Hand & Stone Massage', 'Taqueria', 'Salt, Pepper', 'Pub On Passyunk'])

    def test_the_painted_floors_units(self):
        import re
        s = self.s
        m = re.search(r"'          int ci = int\(bc\) \* 8 \+ (int\(mod\(.*?, 8\.0\)\));',", s)
        self.assertTrue(m)
        expr = m.group(1)
        r = self.run_js(r"""
const floor = Math.floor, fract = (x) => x - Math.floor(x), mod = (x, y) => x - y * Math.floor(x / y), int = (x) => Math.trunc(x);
const ci = (hw, sfUi) => """ + expr + r""";
let same = 0, short = 0;
for (let h = 0; h < 2000; h++) { const hw = h / 2000; const seen = new Set();
  for (let u = 0; u < 24; u++) { if (u && ci(hw, u) === ci(hw, u - 1)) same++; if (u < 8) seen.add(ci(hw, u)); }
  if (seen.size < 8) short++; }
console.log(JSON.stringify({ same, short }));
""")
        self.assertEqual(r, {'same': 0, 'short': 0})   # side by side never one cell, and eight units wear all eight
        # they stop where the panels do: the page's shortest wall is the bake's SPAN_MIN
        import ast
        span_min = next(ast.literal_eval(n.value) for n in ast.parse((ROOT / 'bake_storefronts.py').read_text()).body
                        if isinstance(n, ast.Assign) and any(getattr(t, 'id', None) == 'SPAN_MIN' for t in n.targets))
        self.assertIn('  const SF_PARTA_MIN = %s;' % span_min, s)


if __name__ == '__main__':
    unittest.main()
