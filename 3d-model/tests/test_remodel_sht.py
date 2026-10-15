"""Round 195: the Society Hill Towers remodelled (app.js 'the three towers remodelled', fetch_sht_art.py, bake_sht_art.py).

The review's round: the band over the top heads a floor and the penthouse 1.1 floors over the coping, the far
level carrying the colonnade's pilotis and the cooling tower (no change at the switch), the motor court's service ways
laying no asphalt over the court, the means built from the material's own lights and the screen's own curve, the night's
rooms on one mean (the flat pane, roomPar never set), the concrete's light after dark.

- the tower as built: 94.2 m, thirty floors of 2.76 m over the colonnade and the transfer girder, 18 bays by 12 on the
  six-foot module, its faces 33.68 by 22.70 m (inside the three OSM footprints' spread), one tower placed three times;
- under Node the builder makes a near and a far level inside their budgets: every quad wound to its own normal, every
  stream a Float32 multiple of four bytes (Round 158), a 16-bit index, each shell face running u from 0 to its length;
- Round 137's five windows exactly as they were: the same seed from the same OSM record (2.8968, the South tower's south
  face), floor 16, bays 5 to 9 inside that face's grid, the tower glass's hook run unchanged and its varyings made the
  ray-cast's per-pixel values, the themed rooms carrying no blind by day;
- the facade hook's anchors all land on three r149's own chunks and on the hook's own output (shtHook run under Node on
  ShaderLib.standard), no gl_FragDepth anywhere in it, one program for both levels;
- the wiring: ?sht=0 and ?real=0 build Round 194's towers, the frame's level step, the pins' stand-in, the art's manifest
  (a computer's 1024 and a phone's 512) and freeTexOnUpload, and no em dash or middot in anything a person reads."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(src, start, end):
    i = src.index(start)
    return src[i:src.index(end, i)]


SCRIPT = r'''
const THREE = require(THREE_PATH);
global.THREE = THREE;
const REAL = true, isTouch = false, POST = { on: true }, location = { search: '' };
const LAYER = { park: 0.06, plaza: 0.1, deck: 0.14, sidewalk: 0.16, road: 0.24, footway: 0.32, basin: 0.36, pool: 0.38 };
const nightUniform = { value: 0 }, sunWUniform = { value: new THREE.Vector3(0, 1, 0) };
const postU = { uExposure: { value: 1.06 } }, gradeU = { uCon: { value: 1.05 } };
const renderer = { capabilities: { isWebGL2: true } };
let lampCalls = 0;
function lampLightPatch(sh, w, mode) { lampCalls++; sh.fragmentShader = sh.fragmentShader.replace('void main() {', 'uniform float uLampOn;\nvoid main() {'); }
BLOCKS
const towers = TOWERS;
const out = { near: [], far: [], dims: { fh: SHT_D.fh, L: SHT_D.L, gridBot: SHT_D.gridBot, H: SHT_D.H } };
const nearL = [], farL = [];
towers.forEach((t, ti) => {
  const W0 = t.width_m, Dp0 = t.depth_m, ang = -(t.angleRad || 0);
  const sides = [{ len: W0, off: Dp0 / 2, axis: 'x' }, { len: W0, off: -Dp0 / 2, axis: 'x' }, { len: Dp0, off: W0 / 2, axis: 'z' }, { len: Dp0, off: -W0 / 2, axis: 'z' }];
  const seeds = sides.map((s) => ti * .71 + s.off * .13 + (s.axis === 'x' ? 0 : 3.7));
  const m = new THREE.Matrix4().makeRotationY(ang).setPosition(t.centroid[0], 1.0, t.centroid[1]);
  const nm = (t.name || '').match(/(North|West|South)/), kit = SHT_KIT[nm ? nm[1] : 'West'];
  const n = shtTowerParts(true, kit), f = shtTowerParts(false, kit);
  out.near.push({ name: t.name, quads: n.nv / 4, south: sides.indexOf(shtSouthSide(sides, ang)), seeds });
  out.far.push({ quads: f.nv / 4 });
  nearL.push({ B: n, m, seeds, lobby: ti * .71 }); farL.push({ B: f, m, seeds, lobby: ti * .71 });
});
const fm = new THREE.Matrix4().makeTranslation(0, 1.0, 0), fB = shtFountain();
nearL.push({ B: fB, m: fm, seeds: [0, 0, 0, 0], lobby: 0 }); farL.push({ B: fB, m: fm, seeds: [0, 0, 0, 0], lobby: 0 });
const check = (g) => {
  const r = { tris: g.index.count / 3, verts: g.attributes.position.count, index: g.index.array.constructor.name, attrs: {}, wound: 0, badWound: 0, finite: true };
  for (const k in g.attributes) { const a = g.attributes[k]; r.attrs[k] = [a.array.constructor.name, a.itemSize, (a.array.BYTES_PER_ELEMENT * a.itemSize) % 4 === 0]; }
  const p = g.attributes.position.array, n = g.attributes.normal.array, ix = g.index.array;
  for (let i = 0; i < p.length; i++) if (!Number.isFinite(p[i])) { r.finite = false; break; }
  for (let t = 0; t < ix.length; t += 3) {
    const a = ix[t] * 3, b = ix[t + 1] * 3, c = ix[t + 2] * 3;
    const e1 = [p[b] - p[a], p[b + 1] - p[a + 1], p[b + 2] - p[a + 2]], e2 = [p[c] - p[a], p[c + 1] - p[a + 1], p[c + 2] - p[a + 2]];
    const cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    const L = Math.hypot(cr[0], cr[1], cr[2]); if (L < 1e-9) continue;
    const d = (cr[0] * n[a] + cr[1] * n[a + 1] + cr[2] * n[a + 2]) / L;
    r.wound++; if (d < 0.99) r.badWound++;
  }
  // the shell faces: kind 0, u from 0 to the face's length, y from the colonnade's soffit to the roof
  const it = g.attributes.aInterior.array, k = g.attributes.aShtK.array, faces = {};
  for (let v = 0; v < k.length; v++) {
    if (k[v] !== 0) continue;
    const L = it[v * 4 + 3], key = it[v * 4 + 2].toFixed(4) + ':' + L.toFixed(2);
    const f = faces[key] || (faces[key] = { seed: +it[v * 4 + 2].toFixed(4), L: +L.toFixed(2), u0: 1e9, u1: -1e9, y0: 1e9, y1: -1e9 });
    f.u0 = Math.min(f.u0, it[v * 4]); f.u1 = Math.max(f.u1, it[v * 4]); f.y0 = Math.min(f.y0, it[v * 4 + 1]); f.y1 = Math.max(f.y1, it[v * 4 + 1]);
  }
  r.faces = Object.values(faces);
  r.kinds = [...new Set(Array.from(k))].sort();
  return r;
};
out.nearG = check(shtMerge(nearL));
out.farG = check(shtMerge(farL));
// the hook on three's own standard program: every anchor lands, the hook's varyings made per-pixel values
const sh = { vertexShader: THREE.ShaderLib.standard.vertexShader, fragmentShader: THREE.ShaderLib.standard.fragmentShader, uniforms: {} };
shtHook(sh);
out.hook = { ok: SHT.hookOk, miss: SHT.hookMiss, lampCalls, fs: sh.fragmentShader, vs: sh.vertexShader, uniforms: Object.keys(sh.uniforms).sort() };
console.log(JSON.stringify(out));
'''


class Remodel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.towers = json.loads((ROOT / 'scene.json').read_text())['towers']
        cls.out = None
        if shutil.which('node'):
            s = cls.src
            blocks = '\n'.join([
                cut(s, '  const SHT_THEMED = ', '  const groundMats'),
                cut(s, '  const occU = ', '  function towerRoomCoordinates('),
                cut(s, '  const SHT_ON = ', '  // the concrete\'s photograph'),
                cut(s, '  function shtBuf() {', '  function shtBuild() {'),
                cut(s, '  const SHT_FOUNTAIN = ', '  function shtPlaza('),
                cut(s, '  function shtFountain() {', '  // the lawns\' berms'),
            ])
            script = SCRIPT.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('TOWERS', json.dumps(cls.towers)).replace('BLOCKS', blocks)
            r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
            assert r.returncode == 0, r.stderr[-3000:]
            cls.out = json.loads(r.stdout)

    def need(self):
        if self.out is None:
            raise unittest.SkipTest('Node.js unavailable')
        return self.out

    def test_the_tower_as_built(self):
        o = self.need()
        d = o['dims']
        self.assertAlmostEqual(d['H'], 94.2)
        self.assertAlmostEqual(d['fh'], 2.793, places=3)   # thirty floors, close on nine feet (the review's round's band over the top heads)
        self.assertAlmostEqual(d['L'][0], 33.68, places=2)
        self.assertAlmostEqual(d['L'][1], 22.70, places=2)
        # the one tower against the three OSM footprints (mapping noise of about a metre either way)
        for t in self.towers:
            self.assertLess(abs(t['width_m'] - d['L'][0]), 1.6, t['name'])
            self.assertLess(abs(t['depth_m'] - d['L'][1]), 1.3, t['name'])
        # 18 and 12 bays on the six-foot module, Round 4's count
        for L, bays in zip(d['L'], (18, 12)):
            self.assertEqual(int((L - 2 * 0.55 + 0.36) / 1.83 + 0.5), bays)

    def test_levels_and_streams(self):
        o = self.need()
        for lvl, cap in (('nearG', 2000), ('farG', 2000)):
            g = o[lvl]
            self.assertLessEqual(g['tris'], cap, lvl)
            self.assertTrue(g['finite'], lvl)
            self.assertEqual(g['index'], 'Uint16Array', lvl)
            self.assertEqual(g['badWound'], 0, lvl)   # every quad wound to its own normal (front faces out)
            self.assertGreater(g['wound'], 100, lvl)
            self.assertEqual(sorted(g['attrs']), ['aInterior', 'aShtK', 'normal', 'position'])
            for k, (typ, size, aligned) in g['attrs'].items():
                self.assertEqual(typ, 'Float32Array', k)
                self.assertTrue(aligned, k)   # Round 158: no 1- or 3-byte stream
            # twelve shell faces, u from 0 to each face's length, y from the soffit to the roof
            self.assertEqual(len(g['faces']), 12, lvl)
            for f in g['faces']:
                self.assertAlmostEqual(f['u0'], 0, places=3); self.assertAlmostEqual(f['u1'], f['L'], places=2)
                self.assertAlmostEqual(f['y0'], 6.4, places=3); self.assertAlmostEqual(f['y1'], 94.2, places=3)
        self.assertEqual(o['nearG']['kinds'], [0, 1, 2, 3, 4, 5, 6, 7])
        # the review's round: the far level carries the pilotis' outer faces and the cooling tower and its fans, so nothing at the
        # base or on the roof changes at the switch (the review's pop at 520 m and 320 m), and stays under the near's cost
        self.assertEqual(o['farG']['kinds'], [0, 1, 2, 3, 4, 5, 6, 7])
        self.assertLess(o['farG']['tris'], o['nearG']['tris'])
        self.assertGreater(o['farG']['tris'] - 3 * 140, 500)   # the old far level (420 for the three) plus the colonnade's faces

    def test_the_five_windows(self):
        o = self.need()
        m = re.search(r"const SHT_THEMED = \{ tower: /([^/]+)/, floor: (\d+), from: (\d+), to: (\d+) \};", self.src)
        self.assertEqual((m.group(2), m.group(3), m.group(4)), ('16', '5', '9'))
        south = next(t for t in o['near'] if 'South' in t['name'])
        self.assertEqual(south['south'], 0)   # the wide face at +depth/2, as Round 137 found it
        seed = south['seeds'][0]
        self.assertAlmostEqual(seed, 2.8968, places=4)   # Round 137's seed (lightsState().windows.at[0] on main)
        faces = [f for f in o['nearG']['faces'] if abs(f['seed'] - seed) < 0.005]
        self.assertEqual(len(faces), 1)
        self.assertAlmostEqual(faces[0]['L'], 33.68, places=2)   # the wide face: 18 bays, so bays 5 to 9 lie on it
        # no other face of the three, nor a lobby, near the seed
        others = [s for t in o['near'] for s in t['seeds'] if abs(s - seed) > 1e-9] + [ti * .71 for ti in range(3)]
        self.assertGreater(min(abs(s - seed) for s in others), 0.1)
        b = self.src
        self.assertIn("shtWinU.uLitWin.value.set(seeds[fi], SHT_THEMED.floor, SHT_THEMED.from, SHT_THEMED.to);", b)
        self.assertIn('apartmentWindowHook(sh);                 // the rooms, the themed five', b)
        self.assertIn("mat.defines = { THEMED_ROOMS: '', ...(POST.on ? { THEMED_BLOOM: '', SHT_POST: '' } : {}) };", b)
        self.assertIn('towerGlassMat = mat;', b)   # the night's emission and updateLightsTheme's reach
        # by day the five carry no blind or curtain (Round 137: plain glass), on the hook's own test
        self.assertIn('plain = 1.0 - step(abs(rI.z - uLitWin.x), .005) * step(abs(rid.y - uLitWin.y), .5) * step(uLitWin.z - .5, rid.x) * step(rid.x, uLitWin.w + .5);', b)
        self.assertIn('float blindOn = step(.58, r2) * plain, curtOn = step(.65, r3) * plain', b)

    def test_the_hook_on_three(self):
        o = self.need()
        h = o['hook']
        self.assertTrue(h['ok'], h['miss'])
        self.assertEqual(h['lampCalls'], 1)
        fs, vs = h['fs'], h['vs']
        self.assertNotIn('gl_FragDepth', fs)   # Round 192: no new program writes it
        self.assertIn('varying vec4 vInteriorV; varying vec3 vInteriorNormalV; vec4 vInterior = vec4(0.0); vec3 vInteriorNormal = vec3(0.0, 1.0, 0.0);', fs)
        self.assertIn('vInteriorV=aInterior; vInteriorNormalV=normal;', vs)
        self.assertNotIn('varying vec4 vInterior;', fs)
        self.assertIn('opticalGlass=clamp(shtGlass,0.0,1.0);', fs)
        self.assertNotIn('material.diffuseColor*=1.0-opticalGlass*0.600;', fs)
        self.assertIn('themedRoom=1.0; totalEmissiveRadiance*=shtThemeK;', fs)
        self.assertIn('#define RE_Direct RE_Direct_Sht', fs)
        self.assertIn('radiance *= shtSpecOcc;', fs)
        # the themed rooms' emission is the hook's own formula, unchanged (Round 137)
        self.assertIn('totalEmissiveRadiance=te*uThemeNight*2.4*mix(1.0,.42,tsat)', fs)
        self.assertEqual(fs.count('#ifdef THEMED_ROOMS'), 3)   # the hook's declarations, its block, and the blinds' test
        # the ray-cast runs before the hook's emissive block and its day room after it
        self.assertLess(fs.index('float K = floor(vShtK + 0.5);'), fs.index('vec3 interior=roomLight(fract(vInterior.xy)'))
        self.assertLess(fs.index('vec3 interior=roomLight(fract(vInterior.xy)'), fs.index('totalEmissiveRadiance += shtDay;'))
        for u in ('uShtG', 'uShtV', 'uShtC', 'uShtL', 'uShtTex', 'uLitWin', 'uWin0', 'uThemeNight', 'uOcc'):
            self.assertIn(u, h['uniforms'])

    def test_wiring(self):
        s = self.src
        self.assertIn("const SHT_ON = REAL && !/[?&]sht=0\\b/.test(location.search);", s)
        step = cut(s, "  step('Casting the concrete grid', () => {", '  // ------------------------------------------------ the outer districts')
        self.assertTrue(step.split('\n')[1].strip().startswith('if (SHT_ON && shtBuildSafe()) { shtLandscape(); return; }'))
        self.assertIn('towerGlassMat.onBeforeCompile = (sh) => { apartmentWindowHook(sh); Object.assign(sh.uniforms, shtWinU); };', step)   # Round 194's, kept
        self.assertIn('    shtStep();   // Round 195', s)
        self.assertIn('sht: shtProbe, ', s)
        b = cut(s, '  function shtBuild() {', '  // the build, or Round 194')
        self.assertIn('SHT.near.userData.occStandIn = SHT.far;', b)
        self.assertIn('rayTargets.push(SHT.near);', b)
        self.assertIn('addColSeg(', b); self.assertIn('registerPoly(cor);', b)
        self.assertIn('tex.image = im; tex.needsUpdate = true; freeTexOnUpload(tex);', cut(s, '  function shtLoadArt() {', '  function shtBuf() {'))
        self.assertIn("const SHT_NEAR_R = isTouch ? 320 : 520, SHT_HYST = 40;", s)

    def test_art(self):
        from PIL import Image
        a = json.loads((ROOT / 'sht_art.json').read_text())['concrete']
        with Image.open(ROOT / a['img']) as im:
            self.assertEqual(im.size, (1024, 1024)); self.assertEqual(im.mode, 'RGB')
        with Image.open(ROOT / a['imgHalf']) as im:
            self.assertEqual(im.size, (512, 512))
        self.assertEqual(len(a['mean']), 3)
        self.assertGreater(a['tileM'], 1)
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("SHT_ART", text_of("sht_art.json", "null"))', b)
        self.assertIn('"sht_art.json"):', b)

    def test_proportions_at_the_top(self):
        # the review's round: the band over the top heads is a floor (row profiles: lccn.jpg 1.0, korean.jpg 0.97, pa1.jpg 0.77
        # of a floor; it was 3.6 m, 1.3 floors) and the penthouse stands 1.1 floors over the coping (pa1.jpg; it was 1.6 m)
        m = re.search(r"parapetH: ([0-9.]+),", cut(self.src, '  const SHT_D = ', '  const SHT_NEAR_R'))
        pent = re.search(r"pent: \[([0-9.]+), ([0-9.]+), ([0-9.]+)\]", self.src)
        parapet, fh = float(m.group(1)), (94.2 - float(m.group(1)) - 6.4 - 2.15 + 0.55) / 30
        band = parapet + 0.55 / 2
        self.assertTrue(0.9 <= band / fh <= 1.0, band / fh)
        self.assertTrue(1.0 <= float(pent.group(3)) / fh <= 1.2)

    def test_the_motor_court_is_paving(self):
        # OSM's service ways round the fountain and the drive in from Locust Street lay no asphalt over the court, the car
        # park east of it keeps its own; every registration stays (the kerbs, the trees' clearance), traffic drives no
        # service way
        s = self.src
        ring = json.loads(re.search(r"const SHT_COURT = (\[\[.*?\]\]);", s).group(1))
        def inside(x, z):
            c = False
            for i in range(len(ring)):
                (x1, z1), (x2, z2) = ring[i], ring[i - 1]
                if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
                    c = not c
            return c
        roads = json.loads((ROOT / 'scene.json').read_text())['roads']
        loop = [r for r in roads if r.get('t') == 'service' and all(abs(p[0] - 2) < 13 and abs(p[1]) < 13 for p in r['pts'])]
        self.assertEqual(len(loop), 1)   # the loop round the fountain
        drive = [r for r in roads if r.get('t') == 'service' and [round(v, 1) for v in r['pts'][0]] == [-4.7, 42.7]]
        self.assertEqual(len(drive), 1)   # the drive in from Locust Street
        mids = lambda r: [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(r['pts'], r['pts'][1:])]
        for r in loop + drive:
            self.assertTrue(all(inside(x, z) for x, z in mids(r)))
        lot = [(x, z) for r in roads if r.get('t') == 'service' for x, z in mids(r) if 14 < x < 34 and -11 < z < 19]
        self.assertTrue(lot)
        self.assertFalse(any(inside(x, z) for x, z in lot))   # the car park's aisles keep their asphalt
        paving = cut(s, "  step('Paving the streets', () => {", "    // ---- sidewalks and crossings")
        self.assertIn("const paint = SHT_ON && r.t === 'service' ? shtCourtRuns(run) : [run];", paving)
        self.assertIn('addRoadSeg(run[i][0], run[i][1], run[i + 1][0], run[i + 1][1], r.w / 2);', paving)   # registered whole
        self.assertIn('const court = SHT_COURT;', s)
        self.assertNotIn("'service'", (ROOT / 'bake_traffic.py').read_text().split('RT = ')[1].split('}')[0])

    def test_the_means_and_the_night(self):
        o = self.need()
        fs = o['hook']['fs']
        # the means take each part's light from the material's own lights, defined after three's light pars
        self.assertLess(fs.index('#include <lights_physical_pars_fragment>'), fs.index('vec3 shtFill(vec3 nW)'))
        self.assertIn('getHemisphereLightIrradiance(hemisphereLights[i], nV)', fs)
        self.assertIn('irr += getIBLIrradiance(nV);', fs)
        # and the cell's mean on the screen's own curve, its inverse the composite's
        self.assertIn('float shtDisp(float L)', fs); self.assertIn('float shtUndisp(float D)', fs)
        self.assertIn('kD = clamp(shtUndisp(Dm) / max(Llin, 1.0e-6), 0.5, 2.0);', fs)
        # the night's rooms on the flat pane in both views, at one mean (roomLight's room box is never asked for)
        self.assertNotIn('roomPar = 1.0', fs)
        self.assertIn('shtRoomK = mix(mix(1.0, 1.36, detE), kRm * uShtK.y * kD, wA);', fs)
        self.assertIn('totalEmissiveRadiance *= emK * shtRoomK * uShtDbg.x;', fs)
        self.assertIn('shtThemeK = emK;', fs)   # the five themed rooms never take the rooms' mean
        # the concrete's light after dark by the lamps' photocell, on the concrete alone
        self.assertIn('shtDay += shtConA * uShtF.w * uShtDbg.y * uShtN.rgb', fs)
        self.assertIn('shtU.uShtF.value.w = lampUniform.value;', self.src)
        for u in ('uShtGl', 'uShtGT', 'uShtF', 'uShtN', 'uShtM', 'uShtK', 'uShtExp', 'uShtCon'):
            self.assertIn(u, o['hook']['uniforms'])
        # no sampler of its own beyond the concrete's (sixteen units a program)
        self.assertEqual(len(re.findall(r'uniform sampler2D uSht', fs)), 1)

    def test_no_dashes_in_what_a_person_reads(self):
        block = cut(self.src, '  // ------------------------------------------------ the three towers remodelled (Round 195)', "  step('Casting the concrete grid'")
        for q in re.findall(r"'([^'\n]*)'", block):
            self.assertNotIn('—', q); self.assertNotIn('·', q)


if __name__ == '__main__':
    unittest.main()
