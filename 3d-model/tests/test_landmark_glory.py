"""Round 191: Glory Beer Bar & Kitchen, 126 Chestnut Street (rebuilds/glory.js, bake_glory_art.py, the app's api.glory).

- the lot: the OPA address point for 126 lies in it, and exactly one core footprint's area-weighted centroid does, scene
  building 2541 (the old builder stood on 120, two lots east);
- the realistic look holds 2541 back under a key that is not 'glory' (the old builder would run on it), and ?real=0 and
  ?glory=0 keep the old entry exactly;
- under Node the def builds a near level (the signs among its faces since the review) and a far level inside their
  budgets, every stream finite and a multiple of four bytes (Round 158), aGl four normalized bytes, the index 16-bit;
- the manifest's files are there with their phone halves, the masks opaque RGB PNGs, the rooms each with a back wall;
- the app's wiring: the def skipped unless GLORY_ON, the lamps in the light map at their own 7 m, the search's bar kind, the
  card's lines, the frame step, and no em dash or middot in anything a person reads;
- Round 191's review: the second storey's low arch (the chosen frame's key-measured rise at most 0.5 m), a jointless granite
  swatch at its real coursing, the bar's glass and the rooms told apart by position (not by the mask's mipped codes), the
  signs on the near mesh, the trade fitted inside the sign's border, a phone's art decoded only near Glory after Enter;
- its second review: the muntins kept at 0 in the mask two texels wide (pane_bars, bar_texels), a tap on the sign from the
  sidewalk naming Glory (the apron over the walk in front of its own frontage, never 128's), the cast lace cut in the shader
  (and in its shadow), the capitals' boxes on the painted ones, the lamps' wash a metal's share, the stone's grain and
  weather, and the art decoded near Glory on a computer too;
- its third review: the stone's grain smooth value noise (no hashed cells), the lower elevation's lites regular rectangles
  of whole texels with straight bars (regular_lites) read texel by texel where magnified, every plain swatch periodic, the
  open bar's light out through its glass, the bar's door leaf standing open (mode 6) with its doorway, the east return
  painted, a tap under 2 m naming Glory, the search's mark over the parapet and its address in the index, the recovery
  tier's art at the near level's reach and without the rooms, one upload a frame, and the block's walk paved."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

try:
    from . import _common as C
except ImportError:
    import _common as C

ROOT = Path(__file__).resolve().parents[1]
LOT = [[97.23, -265.88], [91.29, -266.94], [98.51, -307.95], [106.97, -306.47], [106.74, -305.21], [102.6, -281.43], [100.02, -281.87]]
OPA_126 = (101.01, -284.81)


def inside(x, z, poly):
    c = False
    for i in range(len(poly)):
        (xi, zi), (xj, zj) = poly[i], poly[i - 1]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi:
            c = not c
    return c


def centroid(pts):
    x = y = a = 0.0
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        c = p[0] * q[1] - q[0] * p[1]
        a += c; x += (p[0] + q[0]) * c; y += (p[1] + q[1]) * c
    a *= 0.5
    return (pts[0][0], pts[0][1]) if abs(a) < 1e-6 else (x / (6 * a), y / (6 * a))


SCRIPT = r'''
const fs = require('fs'), vm = require('vm');
const THREE = require(THREE_PATH);
global.THREE = THREE;
const ctx2d = new Proxy({}, { get: (t, k) => (k in t ? t[k] : (k === 'measureText' ? () => ({ width: 10 }) : () => {})), set: (t, k, v) => { t[k] = v; return true; } });
global.document = { createElement: () => ({ width: 0, height: 0, style: {}, getContext: () => ctx2d }) };
global.location = { search: '' };
global.RB = { defs: [], kit: null, add(def) { global.RB.defs.push(def); } };
for (const f of FILES) vm.runInThisContext(fs.readFileSync(f, 'utf8'), { filename: f });
const art = JSON.parse(fs.readFileSync(ART, 'utf8'));
const out = {};
for (const withArt of [false, true]) {
  const calls = { lod: 0, lamps: 0, ref: null, occupy: 0, frame: null };
  const mat = new THREE.MeshStandardMaterial();
  const api = { THREE, K: RB.kit(THREE), where: 'app', ground: () => 0.25, occupy: () => { calls.occupy++; }, pinAt: () => {}, log: () => {} };
  if (withArt) api.glory = { art, facade: (f) => { calls.frame = f; return mat; }, lod: (n, f, c) => { calls.lod++; calls.lodArgs = [!!n, !!f, Array.isArray(c)]; }, lamps: (l) => { calls.lamps = l.length; }, ref: (r) => { calls.ref = r; }, paved: (ring) => { calls.paved = ring; } };
  const t0 = Date.now();
  const obj = RB.defs.find((d) => d.id === 'glory').build(api);
  const r = { ms: Date.now() - t0, calls, meshes: {} };
  obj.traverse((o) => {
    if (!o.isMesh) return;
    const g = o.geometry, m = { tris: (g.index ? g.index.count : g.attributes.position.count) / 3, bad: [], finite: true, attrs: {}, index: g.index ? g.index.array.constructor.name : null };
    for (const k in g.attributes) {
      const a = g.attributes[k];
      m.attrs[k] = [a.array.constructor.name, a.itemSize, !!a.normalized];
      if ((a.array.BYTES_PER_ELEMENT * a.itemSize) % 4) m.bad.push(k);
    }
    const p = g.attributes.position.array;
    for (let i = 0; i < p.length; i++) if (!Number.isFinite(p[i])) { m.finite = false; break; }
    m.modes = {};
    const gl = g.attributes.aGl.array;
    for (let i = 0; i < gl.length; i += 4) { const k = gl[i] + ':' + gl[i + 1]; m.modes[k] = (m.modes[k] || 0) + 1; }
    g.computeBoundingBox();
    m.box = [g.boundingBox.min.x, g.boundingBox.min.y, g.boundingBox.min.z, g.boundingBox.max.x, g.boundingBox.max.y, g.boundingBox.max.z];
    r.meshes[o.name] = m;
  });
  out[withArt ? 'art' : 'stub'] = r;
}
console.log(JSON.stringify(out));
'''


class Lot(unittest.TestCase):
    def test_the_lot_is_126(self):
        self.assertTrue(inside(*OPA_126, LOT))
        scene = C.load_json('scene.json')
        hits = [i for i, b in enumerate(scene['buildings']) if b.get('poly') and len(b['poly']) >= 3 and inside(*centroid(b['poly']), LOT)]
        self.assertEqual(hits, [2541])
        cx, cz = centroid(scene['buildings'][2541]['poly'])
        self.assertAlmostEqual(cx, 99.03, delta=0.05)
        self.assertAlmostEqual(cz, -288.41, delta=0.05)
        # the def carries the same lot
        src = (ROOT / 'rebuilds' / 'glory.js').read_text()
        self.assertIn('const LOT = ' + json.dumps(LOT) + ';', src)


class Gating(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / 'app.js').read_text()

    def test_the_realistic_key_is_not_the_old_one(self):
        a = self.app
        self.assertIn("const GLORY_ON = REAL && !/[?&]glory=0\\b/.test(location.search);", a)
        # the old entry, exactly as it was, only off the realistic look (or under ?glory=0)
        self.assertIn("...(GLORY_ON ? [] : [{ x: 115.1, z: -283.8, r: 5, minArea: 100, spec: { mode: 'custom', key: 'glory' } }]),", a)
        self.assertIn("{ x: 99.03, z: -288.41, r: 3, minArea: 250, spec: { mode: 'custom', key: 'glory126' } },", a)
        self.assertNotIn("getKey('glory126')", a)
        self.assertIn("const bG = getKey('glory');", a)

    def test_the_rebuild_step_hands_it_over(self):
        a = self.app
        self.assertIn('api.glory = gloryApi();', a)
        self.assertIn('if (d.real && !REAL) continue;', a)
        # ?glory=0 by Glory's own id, never by real (Round 191's review: a City Hall def marked real would have gone with it)
        self.assertIn("if (d.id === 'glory' && !GLORY_ON) continue;", a)
        self.assertNotIn('d.real && !GLORY_ON', a)
        self.assertIn('gloryStep(now);   // Round 191', a)
        steps = re.findall(r"step\('([^']+)'", a)
        self.assertLess(steps.index('Rebuilding the landmarks'), steps.index('Lighting the streetlamps'))   # the lanterns are known before the light map

    def test_the_lanterns_join_the_light_map(self):
        a = self.app
        self.assertIn('const nGl = GLORY.lamps.length;', a)
        s = a[a.index('for (const q of GLORY.lamps) {'):]
        s = s[:s.index('\n      }')]
        self.assertIn('lr[m] = 7;', s)
        self.assertIn('lc[m * 3] = 0.22;', s)

    def test_the_search_and_the_card(self):
        a = self.app
        self.assertIn("bar: 2, building: 4", a)
        self.assertIn("bar: 'Bar'", a)
        self.assertIn("if (GLORY.ref) add(GLORY.ref.name, GLORY.ref.door[0], GLORY.ref.door[1], 'bar', GLORY.ref);", a)
        self.assertIn("if (e.kind === 'bar' && e.ref) { gloryGoTo(e.ref);", a)
        # its third review: the search's mark over the parapet (at the door it covered the board and the entrance in the very
        # view the search lands on), and the address in the index under the bar's own name
        go = a[a.index('  function gloryGoTo(r) {'):a.index('  function searchLocalSubmit(qy) {')]
        self.assertIn('placeSearchMark(r.c[0], r.y0 + 20, r.c[2], r.name);', go)
        self.assertNotIn('placeSearchMark(r.door[0]', go)
        self.assertIn("if (GLORY.ref) ix.push({ name: GLORY.ref.name, lc: '126 chestnut street',", a)
        # no pad (Round 191's review: a metre's pad round a point already 1.5 m into the building hit gave a tap on 128's party
        # wall Glory's card), and the card asks for the parcel at the business's own point inside its lot
        # its second review: the lot tested 0.3 m past the hit (the parcel's point 1.5 m along an oblique ray from the sidewalk
        # gave a tap on 128's front Glory's card), and the hit itself on the walk in front of its own frontage (the blade sign,
        # the lanterns, the old sign box, tapped from the sidewalk, opened the generic card)
        self.assertIn("const gx = p[0] + dir.x * 0.3, gz = p[2] + dir.z * 0.3;", a)
        # its third review: asked before the ground test, so a tap under 2 m (the door at eye height, a railing, a chair, the
        # stoop's deck) names it, anything over the walk's own level
        pick = a[a.index('  function bldgPick(cx, cy) {'):a.index('  function bldgOpen(')]
        glo = "const glo = !!GLORY.ref && p[1] > GLORY.ref.y0 + 0.1 && (gloryAt(gx, gz, 0) || gloryApron(p[0], p[2]));"
        self.assertIn(glo, pick)
        self.assertLess(pick.index(glo), pick.index("if (p[1] < g + 2 && !glo) return false;"))
        self.assertIn("bldgOpen(p[0], p[1] + 1, p[2], x, z, glo ? GLORY.ref : null);", pick)
        self.assertIn("return !!(r && r.apron && pointInPoly(x, z, r.apron));", a)
        self.assertIn("if (biz && biz.parcel) { x = biz.parcel[0]; z = biz.parcel[1]; }", a)
        self.assertIn("if (st.biz) { gloryCard(st); return; }", a)
        self.assertIn("const GLORY_OPENS = [720, 960, 960, 960, 720, 720, 720], GLORY_SHUT = 120;", a)
        card = a[a.index('  function gloryCardHead() {'):a.index('  function gloryAt(x, z, pad) {')]
        for line in ('Craft beer bar and kitchen on two floors', '126 Chestnut St, Old City', 'Built 1853 as a store for James A. Brown'):
            self.assertIn(line, card)
        body = a[a.index('  function gloryCard(st) {'):a.index('  function bldgPick(cx, cy) {')]
        self.assertIn('https://www.gloryphilly.com/', body)
        self.assertIn('septaEsc(st.biz.name)', body)

    def test_no_em_dash_or_middot_where_people_read(self):
        a = self.app
        for start, end in (('  function gloryCanvas() {', '  // an image into a placeholder texture'), ('  function gloryCardHead() {', '  function gloryAt(x, z, pad) {'),
                           ('  function gloryCard(st) {', '  function bldgPick(cx, cy) {')):
            s = a[a.index(start):a.index(end)]
            strings = re.findall(r"'([^'\\]*)'", s)
            for t in strings:
                self.assertNotIn('—', t, t)
                self.assertNotIn('·', t, t)
        g = (ROOT / 'rebuilds' / 'glory.js').read_text()
        self.assertIn("name: 'Glory Beer Bar & Kitchen'", g)
        self.assertNotIn('·', g)

    def test_the_reviews_shader_fixes(self):
        a = self.app
        mat = a[a.index('  function gloryFacadeMat(fr) {'):a.index('  function gloryHoursStep() {')]
        # the bar's glass, the flats' and the two rooms by the face's place in the frame: a mip averages the mask's codes with
        # the frames' zeros (the bar went black from about 100 m, and the panes flipped between rooms across the street)
        self.assertIn("'glBar = frMask.r * glLow * (1.0 - step(0.5, glMode));'", mat)
        self.assertIn("'  float up = step(4.6, glPf.y);'", mat)
        self.assertNotIn('step(196.0, glB)', mat)
        self.assertNotIn('step(208.0, glB)', mat)
        # the numbers (a window's, the height inside it) at the mask's full size; a GL_ macro name is reserved
        self.assertIn("#define GLMASK0(p) textureGrad(uGlMask, p, vec2(0.0), vec2(0.0))", mat)
        self.assertNotIn('GL_MASK0', a)
        # the signs: faces of the near mesh (mode 4), no material of their own
        self.assertIn("'else if (glMode > 3.5) { glTex = texture2D(uGlSign, vUv, -0.6); glRgh = 0.6; }',", mat)
        self.assertNotIn('function glorySignsMat', a)
        self.assertNotIn('GLORY.signs', a)
        # the cafe's chairs a metal, the lanterns' bulb seen through their glass, a recess's shade
        self.assertIn('metalnessFactor = max(metalnessFactor, glMet);', mat)
        self.assertIn("'glTex.rgb *= 1.0 - vGl.w / 255.0;',", mat)
        self.assertIn('glBl = min(glBl, length(glQ - glRd * dot(glQ, glRd)));', mat)
        # the trade measured and fitted inside the border before it is drawn
        cv = a[a.index('  function gloryCanvas() {'):a.index('  // an image into a placeholder texture')]
        self.assertIn('if (wsub > 0.82 * 512) { fs = Math.floor(fs * 0.82 * 512 / wsub); wsub = subW(fs); }', cv)
        self.assertIn('const gap = 3, total =', cv)
        # the narrowed one-way block of Chestnut carries no centre line
        self.assertIn('cls: /^(motorway|trunk)(_link)?$|^primary_link$/.test(r.t) ? 1 : (r.glWalk ||', a)

    def test_the_second_reviews_shader_fixes(self):
        a = self.app
        mat = a[a.index('  function gloryFacadeMat(fr) {'):a.index('  function gloryHoursStep() {')]
        # the glass's cover sharpened only where the mask is magnified (a far pane still averages its glass and bars)
        self.assertIn("frMask.r = mix(clamp((frMask.r - 0.5) / max(glRw * 1.5, 1e-3) + 0.5, 0.0, 1.0), frMask.r, smoothstep(0.15, 0.4, glRw));", mat)
        # the lace: cut by its signed distance and dithered by its share in the facade, cut at its line in the shadow pass
        self.assertIn("'else if (glMode > 4.5) {',", mat)
        self.assertIn("discard;", mat)
        self.assertIn("if (vGlMK.x > 4.5 && glLace(vGlUv, floor(vGlMK.y + 0.5)) > 0.0) discard;", mat)
        self.assertIn('const GLORY_LACE_GLSL = [', a)
        # the street lamps' wash takes a face's share of its colour: a metal's (1 - metalness), the old sign box a little
        self.assertIn("'vec3 glDcKeep = diffuseColor.rgb; diffuseColor.rgb *= glLampK;', '#include <emissivemap_fragment>', 'diffuseColor.rgb = glDcKeep;',", mat)
        self.assertIn('glLampK = 1.0 - glMet;', mat)
        self.assertIn('glRgh = 0.8; glLampK = 0.12;', mat)
        # the stone's grain on its own plane, faded before a pixel spans its cells, and its weather by its place on the front
        # (its third review: smooth value noise in turned octaves, never hashed square cells stepped to specks)
        self.assertNotIn('glH(floor(glPl / 0.003))', mat)
        self.assertNotIn('floor(glPl /', mat)
        self.assertIn("'    float glGr = (glVN(mat2(0.83, 0.56, -0.56, 0.83) * glPl / 0.004) - 0.5) * 0.035 * (1.0 - smoothstep(0.002, 0.004, glPx));',", mat)
        self.assertIn('float glH2(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031);', mat)
        self.assertIn("'  vec2 glFw = fwidth(glPl); float glPx = max(glFw.x, glFw.y);',", mat)   # a derivative in uniform flow
        self.assertIn('if (fr.drips && fr.drips.length === 3) gloryU.uGlDrip.value.set(fr.drips[0], fr.drips[1], fr.drips[2], 1);', mat)
        self.assertIn('if (fr.signbox && fr.signbox.length === 4) gloryU.uGlBox.value.fromArray(fr.signbox);', mat)
        # the bar's glow from afar after dark
        self.assertIn("smoothstep(uGlFar.x, uGlFar.y, distance(cameraPosition, vGlP)) * uGlFar.z", mat)
        # one more swatch, the old sign box's rust cap: the shader's array is the bake's list
        import bake_glory_art as B
        self.assertIn('const GLORY_SW = %d;' % len(B.SWATCHES), a)
        g = (ROOT / 'rebuilds' / 'glory.js').read_text()
        self.assertIn('const SW = { ' + ', '.join('%s: %d' % (k, i) for i, k in enumerate(B.SWATCHES)) + ' };', g)

    def test_the_third_reviews_fixes(self):
        a = self.app
        mat = a[a.index('  function gloryFacadeMat(fr) {'):a.index('  function gloryHoursStep() {')]
        # the mask's glass read texel by texel where it is magnified (its edges eased over a pixel), the uv's derivatives
        # taken in uniform flow before any branch
        self.assertIn("vec2 glUvW = fwidth(vUv), glUdx = dFdx(vUv), glUdy = dFdy(vUv);", mat)
        self.assertIn("frMask = textureGrad(uGlMask, (glMi + glMf + 0.5) / glMs, glUdx, glUdy);", mat)
        self.assertLess(mat.index('glUdx = dFdx(vUv)'), mat.index("'if (glMode < 0.5 || glMode > 5.5) { glTex = texture2D(map, vUv);',"))
        # the open bar's light out through its glass after dark, each opening by its own room's hours
        self.assertIn("'float glSpill(vec3 P, vec3 N, vec4 o, float dg) {',", mat)
        self.assertIn("glSp += glSpill(glPf, glNf, vec4(glB4.xy, uGlBayY.xy), 0.25) * uGlOpen.x + glSpill(glPf, glNf, vec4(glB4.zw, uGlBayY.zw), 0.2) * uGlOpen.y; }", mat)
        self.assertIn("'if (uNight > 0.001 && glPf.z < 0.3 && glPf.z > -3.2 && glPf.y < 9.4) {',", mat)
        # the bar's door leaf (mode 6) folds with the door in the drawn pass and the shadow pass, and its doorway opens
        self.assertIn("(abs(vGl.x - 6.0) < 0.5 && uGlDoor < 0.5)) transformed = vec3(0.0);", mat)
        self.assertIn("(abs(aGl.x * 255.0 - 6.0) < 0.5 && uGlDoor < 0.5)) transformed = vec3(0.0);", mat)
        self.assertIn("if (glMode < 0.5 && uGlDoor > 0.5 && glPf.z > 0.2) glHo =", mat)
        self.assertIn("roughnessFactor = mix(roughnessFactor, 1.0, glHo);", mat)
        hrs = a[a.index('  function gloryHoursStep() {'):a.index('  function gloryStep(now) {')]
        self.assertIn('const door = GLORY.open && WXFX.rain < 0.15 && WXFX.snow < 0.15 && WXFX.hail < 0.15 && (WX.temp == null || WX.temp > 50);', hrs)
        # the east return black-painted over the storefront, the board lit after dark and its canvas read sharper, the
        # lanterns' filament amber, the chairs a dull galvanized metal
        self.assertIn("glPf.x > uGlFw - 0.12 && dot(vWNorm.xz, uGlF.zw) > 0.5 && glPf.z < 1.6 && glPf.y > 4.1", mat)
        self.assertIn("if (glMode > 3.5 && glMode < 4.5 && glPf.y > 3.9 && glPf.z > -0.4) reflectedLight.directDiffuse +=", mat)
        self.assertIn("vec3(1.0, 0.5, 0.17) * (0.05 + 2.4 * exp(", mat)
        self.assertNotIn('glMet = glCh ? 0.7', mat)
        self.assertIn('glMet = glCh ? 0.25 : 0.0;', mat)
        # the room upstairs' ceiling drawn (its plate's top rows drew big diagonals), and no rooms: a plain warm glow
        self.assertIn("'  if (up > 0.5 && glCeil > 0.5) {", mat)
        self.assertIn("'} else if (glBar > 0.01) totalEmissiveRadiance += glBar * uNight *", mat)
        # the stoop's band: heavy fleurons, strokes of about 2 cm, a heavy ring at each post
        lace = a[a.index('  const GLORY_LACE_GLSL = ['):a.index('  const GLORY_DITHER')]
        self.assertIn("'  float d = y > 0.072 ? abs(length(vec2(ax + 0.052, y - 0.075)) - 0.1) - 0.0095 : 1.0;',", lace)
        self.assertIn("'  if (pd < 0.095) d = abs(length(vec2(pd, y - 0.1)) - 0.068) - 0.012;',", lace)
        self.assertNotIn('abs(q) - 0.0065', lace)   # the old band's 1.3 cm lines
        # the recovery tier: the art at the near level's reach, no rooms; one image up a frame
        self.assertIn('const GLORY_DECODE_R = TIER2 ? 200 : 600;', a)
        self.assertIn('const I = A.interior && A.interior.plates && !TIER2 ? A.interior : null;', mat)
        # the block's walk: paved to under the set-back fronts, and no tuft sown on a rebuild's paving
        self.assertIn('const wide = r.glWalk ? 5.0 : 3.0, off = r.w / 2 + 0.05 + wide / 2;', a)
        grass = a[a.index('  function grassStep() {'):a.index('  function grassStep() {') + 3000]
        self.assertIn('if (REBUILD_PAVED.length && rebuildPavedAt(x, z)) continue;', grass)
        self.assertIn('paved: (ring) => { REBUILD_PAVED.push({ ring, bb: rbBox(ring) }); },', a)

    def test_the_old_look_is_untouched(self):
        a = self.app
        # the narrowed Chestnut, the neighbours' recolours and the lanterns are the realistic look's alone
        self.assertIn("if (GLORY_ON && r.name === 'Chestnut Street'", a)
        self.assertIn("...(GLORY_ON ? [\n        { x: 99.03", a)


class Def(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        files = [str(ROOT / 'rebuilds' / '_kit.js'), str(ROOT / 'rebuilds' / 'glory.js')]
        script = SCRIPT.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('FILES', json.dumps(files)).replace('ART', json.dumps(str(ROOT / 'glory_art.json')))
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if run.returncode:
            raise AssertionError(run.stderr[-3000:])
        cls.r = json.loads(run.stdout)

    def test_budgets_with_and_without_the_app(self):
        for k in ('stub', 'art'):
            m = self.r[k]['meshes']
            self.assertEqual(sorted(m), ['glory-far', 'glory-near'], k)   # one draw near, one far: the signs are near faces
            self.assertLessEqual(m['glory-near']['tris'] + m['glory-far']['tris'], 6000, k)
            self.assertGreater(m['glory-near']['tris'], 2500, k)
            self.assertLessEqual(m['glory-far']['tris'], 150, k)
            self.assertLess(self.r[k]['ms'], 300, k)

    def test_streams(self):
        for k in ('stub', 'art'):
            for name, m in self.r[k]['meshes'].items():
                self.assertEqual(m['bad'], [], (k, name))
                self.assertTrue(m['finite'], (k, name))
                self.assertEqual(m['index'], 'Uint16Array', (k, name))
                self.assertEqual(m['attrs']['position'][:2], ['Float32Array', 3])
            for name in ('glory-near', 'glory-far'):
                self.assertEqual(self.r[k]['meshes'][name]['attrs']['aGl'], ['Uint8Array', 4, True])

    def test_it_stands_on_its_lot(self):
        for k in ('stub', 'art'):
            x0, y0, z0, x1, y1, z1 = self.r[k]['meshes']['glory-near']['box']
            self.assertGreater(x0, 89); self.assertLess(x1, 109)
            self.assertGreater(z0, -311); self.assertLess(z1, -264)   # the stoop and the old sign box reach about 2.6 m out
            self.assertLess(y1, 24); self.assertGreater(y0, -2)

    def test_the_app_handles(self):
        c = self.r['art']['calls']
        self.assertEqual(c['lod'], 1)
        self.assertEqual(c['lodArgs'], [True, True, True])
        self.assertEqual(c['ref']['parcel'], list(OPA_126))
        self.assertTrue(inside(*c['ref']['parcel'], LOT))
        self.assertEqual(c['lamps'], 2)
        self.assertEqual(c['occupy'], 1)
        self.assertEqual(c['ref']['name'], 'Glory Beer Bar & Kitchen')
        d, n = c['ref']['door'], c['ref']['n']
        self.assertFalse(inside(d[0], d[1], LOT))                              # the door's point is on the stoop, a metre out
        self.assertTrue(inside(d[0] - n[0] * 1.2, d[1] - n[1] * 1.2, LOT))      # and a metre and a fifth back is the bar
        f = c['frame']
        self.assertAlmostEqual(f['ux'], 0.98504, places=3)
        self.assertAlmostEqual(f['vz'], 0.98504, places=3)
        self.assertEqual(len(f['lanterns']), 2)
        self.assertEqual(self.r['stub']['calls']['occupy'], 1)
        # the apron: the walk in front of the lot's own frontage, 2.4 m out. The blade sign (u 4.29, v -1.2) is on it, 128's
        # front (u -0.5, v 0.5) is neither on it nor on the lot
        ap = c['ref']['apron']
        self.assertEqual(len(ap), 4)
        P = lambda u, v: (LOT[2][0] + u * f['ux'] + v * f['vx'], LOT[2][1] + u * f['uz'] + v * f['vz'])
        self.assertTrue(inside(*P(4.29, -1.2), ap))
        self.assertTrue(inside(*P(2.4, -0.39), ap))      # a lantern
        self.assertTrue(inside(*P(8.1, -0.9), ap))       # the old sign box
        self.assertFalse(inside(*P(-0.5, 0.5), ap))
        self.assertFalse(inside(*P(-0.5, 0.5), LOT))
        self.assertFalse(inside(*P(-0.5, -1.2), ap))     # the walk in front of 128
        self.assertFalse(inside(*P(9.1, -1.2), ap))      # and of 124
        self.assertEqual(f['drips'], sorted(f['drips']))
        self.assertEqual(len(f['signbox']), 4)

    def test_the_lace_and_the_cap(self):
        m = self.r['art']['meshes']
        near, far = m['glory-near']['modes'], m['glory-far']['modes']
        # the cast lace: the stoop's band (kind 0) and the balconet's scrolls (1) near, the whole railing (2) far; the rings
        # are gone (their six pieces were plain hexagons), and the band costs a strip a run
        self.assertGreater(near.get('5:0', 0), 0)
        self.assertGreater(near.get('5:1', 0), 0)
        self.assertGreater(far.get('5:2', 0), 0)
        self.assertLessEqual(near.get('5:0', 0), 64)
        self.assertEqual(far.get('5:2', 0), 32)   # four runs, two faces of two triangles
        self.assertGreater(near.get('1:7', 0), 0)  # the old sign box's rust cap


    def test_the_open_leaf_and_the_frame(self):
        m = self.r['art']['meshes']
        near, far = m['glory-near']['modes'], m['glory-far']['modes']
        # the bar's door leaf standing open: two faces of four corners, near only
        self.assertEqual(near.get('6:0', 0), 8)
        self.assertFalse(any(k.startswith('6:') for k in far))
        f = self.r['art']['calls']['frame']
        self.assertEqual(len(f['bays']), 4); self.assertEqual(len(f['arcade']), 4); self.assertEqual(len(f['bayY']), 4)
        u0, u1, y0, y1 = f['leaf']
        b = f['bays'][1]                                   # the entrance, the second bay from the west
        self.assertTrue(b[0] < u0 < u1 < b[1], (b, f['leaf']))
        self.assertAlmostEqual(y0, f['bayY'][0], places=3)
        self.assertTrue(y0 + 2.5 < y1 < f['bayY'][1], f['leaf'])
        # the block's walk handed over as paving: it holds the apron and the strip before 124's set-back front
        ring = self.r['art']['calls']['paved']
        self.assertEqual(len(ring), 4)
        P = lambda u, v: (LOT[2][0] + u * f['ux'] + v * f['vx'], LOT[2][1] + u * f['uz'] + v * f['vz'])
        self.assertTrue(inside(*P(4.3, -2.0), ring))
        self.assertTrue(inside(*P(12.0, 0.6), ring))
        self.assertFalse(inside(*P(4.3, -5.0), ring))     # the roadway stays the street's


class Art(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = C.load_json('glory_art.json')

    def test_files_and_halves(self):
        m = self.m
        for k in ('img', 'imgHalf', 'mask', 'maskHalf'):
            self.assertTrue((ROOT / m[k]).exists(), m[k])
            self.assertTrue((ROOT / m['interior'][k]).exists(), m['interior'][k])
        self.assertIn('-half.', m['imgHalf']); self.assertIn('-half.', m['maskHalf'])

    def test_masks_are_opaque_rgb(self):
        try:
            from PIL import Image
        except ImportError:
            raise unittest.SkipTest('PIL unavailable')
        for p in (self.m['mask'], self.m['maskHalf'], self.m['interior']['mask'], self.m['interior']['maskHalf']):
            with Image.open(ROOT / p) as im:
                self.assertEqual(im.format, 'PNG', p)
                self.assertEqual(im.mode, 'RGB', p)
        with Image.open(ROOT / self.m['img']) as im:
            self.assertEqual(im.size, (self.m['w'], self.m['h']))

    def test_measures_and_rooms(self):
        L, U = self.m['lower'], self.m['upper']
        self.assertEqual(len(L['bays']), 4); self.assertEqual(len(L['arcade']), 4); self.assertEqual(len(L['cols']), 6)
        self.assertEqual(len(U['win']), 12)
        self.assertLess(L['doorTop'], L['sill2']); self.assertLess(L['sill2'], L['spring']); self.assertLess(L['spring'], L['crown'])
        self.assertLessEqual(L['crown'], L['cornice'][0])
        self.assertEqual(self.m['gen']['warnings'], [])
        P = self.m['interior']['plates']
        self.assertEqual(sorted(P), ['ground-closed', 'ground-open', 'upperroom-closed', 'upperroom-open'])
        for k, p in P.items():
            x0, y0, x1, y1 = p['back']
            self.assertTrue(0 < x0 < x1 < 1 and 0 < y0 < y1 < 1, k)
        self.assertEqual(len(self.m['swatches']), 8)
        # Round 191's review: the second storey's arches are the real low ones (lower-b's lancets rose 0.58 m), and the
        # granite swatch tiles at its own coursing, not the 0.45 m ladder
        self.assertEqual(self.m['gen']['chosen']['lower'], 'lower-e')
        self.assertLessEqual(L['crown'] - L['spring'], 0.5)
        self.assertGreaterEqual(self.m['swatches']['granite']['m'], 0.6)

    def test_the_capitals(self):
        # the painted capitals, measured by hand on the chosen frame: the cap boxes stand on them (Round 191's second review)
        cap = self.m['lower']['capital']
        self.assertLess(cap['y'][0], self.m['lower']['doorTop'])
        self.assertLess(self.m['lower']['doorTop'], cap['y'][1])
        self.assertLess(cap['y'][1] - cap['y'][0], 0.25)
        for e in cap['ends']:
            self.assertTrue(0.05 <= e <= 0.3, e)

    def test_the_muntins_stay_in_the_mask(self):
        # Round 191's second review: the glass grown into the muntins from both sides left each one a texel at a third or
        # two thirds of the glass, so the French doors and the casements drew as single sheets. Every bar between two panes
        # of one opening is 0 two texels wide: down a door leaf (the review's column x 180, rows 350 to 480) and down a
        # casement (x 75, rows 90 to 240) every bar between two panes is a run of zeros at least two texels long
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            raise unittest.SkipTest('PIL or numpy unavailable')
        with Image.open(ROOT / self.m['mask']) as im:
            r = np.asarray(im.convert('RGB'))[..., 0]
        for x, y0, y1, least in ((180, 350, 480, 5), (75, 90, 240, 6)):
            col = r[y0:y1, x]
            runs, i = [], 0
            while i < len(col):
                if col[i] == 0 and i > 0 and col[i - 1] >= 128:
                    j = i
                    while j < len(col) and col[j] == 0:
                        j += 1
                    if j < len(col) and col[j] >= 85:
                        runs.append(j - i)
                    i = j
                else:
                    i += 1
            self.assertGreaterEqual(len(runs), least, (x, runs))
            self.assertTrue(all(n >= 2 for n in runs), (x, runs))

    def test_the_bar_helpers(self):
        # a synthetic key at the bake's scale (three pixels a mask texel): two by two panes 45 px a side with a 5 or 6 px
        # muntin between them at every phase on the grid (the chosen frame's are 5 to 6), and a 40 px mullion to a second
        # window: the muntins are bars, the mullion is not, and at the mask's size every bar is two texels
        try:
            import numpy as np
        except ImportError:
            raise unittest.SkipTest('numpy unavailable')
        import bake_glory_art as B
        for gap in (5, 6):
            for x0 in (15, 16, 17):
                k = np.zeros((180, 300), bool)
                xa = x0 + 45 + gap
                for xs in (x0, xa, xa + 45 + 40):
                    for ys in (21, 21 + 45 + gap):
                        k[ys:ys + 45, xs:xs + 45] = True
                bars = B.pane_bars(k)
                self.assertTrue(bars[40, x0 + 45 + gap // 2] and bars[21 + 45 + gap // 2, x0 + 20], (gap, x0))   # both muntins
                self.assertFalse(bars[40, xa + 45 + 20], (gap, x0))                                            # the mullion
                t = B.bar_texels(bars, (60, 100))
                self.assertEqual(int(t[13, (x0 + 40) // 3:(xa + 5) // 3 + 1].sum()), 2, (gap, x0))              # across the vertical
                self.assertEqual(int(t[(21 + 40) // 3:(21 + 45 + gap + 5) // 3 + 1, (x0 + 20) // 3].sum()), 2, (gap, x0))   # down the horizontal

    def test_the_lower_lites_are_rectangles(self):
        # Round 191's third review: the lower elevation's glass is regular_lites', every lite a rectangle of whole texels
        # and every bar straight, nothing between glass and frame (the image's own bars wobbled a texel, and the filtered
        # mask rounded every lite)
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            raise unittest.SkipTest('PIL or numpy unavailable')
        from bake_fronts import blobs
        with Image.open(ROOT / self.m['mask']) as im:
            r = np.asarray(im.convert('RGB'))[..., 0]
        lo = r[4:4 + 545, 4:4 + 504]                       # the lower elevation at the mask's half size, in its gutter
        self.assertEqual(sorted(np.unique(lo).tolist()), [0, 255])
        lites = [b for b in blobs(lo == 255) if b[4] > 4]
        self.assertEqual(len(lites), 232)                  # 8 leaves of 12, 8 transoms, 8 casements of 16
        for y0, x0, y1, x1, n in lites:
            self.assertEqual(n, (y1 - y0 + 1) * (x1 - x0 + 1), (y0, x0, y1, x1))

    def test_the_door_leaves(self):
        L = self.m['lower']
        lv = L['leaves']
        self.assertEqual(len(lv['bays']), 4)
        for (a, mid, b), (u0, u1) in zip(lv['bays'], L['bays']):
            self.assertTrue(u0 < a < mid < b < u1, (a, mid, b, u0, u1))
        self.assertTrue(L['doorFoot'] + 2.5 < lv['top'] < L['doorTop'], lv['top'])

    def test_the_plain_swatches_tile(self):
        # Round 191's third review: noise_swatch's coarse field was resized without wrapping, so every concrete and roof
        # tile ended at a hard edge (a seam down the stoop and through every step). Without the grain, a tile's wrap is
        # no harder than any step inside it
        try:
            import numpy as np
        except ImportError:
            raise unittest.SkipTest('numpy unavailable')
        import bake_glory_art as B
        for seed in (1, 5, 7):
            t = np.asarray(B.noise_swatch((128, 128, 128), 0.5, seed, fine=0), np.float32)[..., 0]
            self.assertLessEqual(np.abs(t[:, 0] - t[:, -1]).max(), np.abs(np.diff(t, axis=1)).max() + 1)
            self.assertLessEqual(np.abs(t[0] - t[-1]).max(), np.abs(np.diff(t, axis=0)).max() + 1)

    def test_the_old_sign_box_is_pale(self):
        # the Bright MLS view's pale worn white-grey enamel (Round 191's third review: the grey-sage read darker and greener)
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            raise unittest.SkipTest('PIL or numpy unavailable')
        with Image.open(ROOT / self.m['img']) as im:
            a = np.asarray(im.convert('RGB'), np.float32)
        H, W = a.shape[:2]
        u0, v0, du, dv = self.m['swatches']['rustblue']['rect']
        sw = a[round((1 - v0 - dv) * H):round((1 - v0) * H), round(u0 * W):round((u0 + du) * W)].reshape(-1, 3).mean(0)
        self.assertGreater(sw.mean(), 150)
        self.assertLess(abs(sw[1] - sw[0]), 10)            # grey, not sage

    def test_the_granite_swatch_has_no_joint(self):
        try:
            from PIL import Image, ImageFilter
            import numpy as np
        except ImportError:
            raise unittest.SkipTest('PIL or numpy unavailable')
        with Image.open(ROOT / self.m['img']) as im:
            a = im.convert('L')
            W, H = a.size
            u0, v0, du, dv = self.m['swatches']['granite']['rect']
            box = (round(u0 * W), round((1 - v0 - dv) * H), round((u0 + du) * W), round((1 - v0) * H))
            sw = np.asarray(a.crop(box), np.float32) / 255
        # a joint is a line: a row (or column) whose mean departs from the swatch's by a joint's contrast (the old swatch's
        # joint and shadow: 0.10 and more)
        self.assertLess(float(np.abs(sw.mean(1) - sw.mean()).max()), 0.05)
        self.assertLess(float(np.abs(sw.mean(0) - sw.mean()).max()), 0.05)


if __name__ == '__main__':
    unittest.main()
