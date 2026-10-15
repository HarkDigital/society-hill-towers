"""Round 195 (Mike: "Remodel ... The Moshulu"): the 1904 four-masted barque at Penn's Landing, rebuilt from her OSM outline
in her own frame (moshuluBuild), drawn as the photographs show her now: the navy hull over the red bottom with the
restaurant's windows, buff masts and yards braced a little, standing rigging and ratlines as ribbons that hold 0.6 px and
fade by their coverage, the tented decks, the Deck Bar, the boats, the gangways and the festoons of bulbs from the
bowsprit over every truck to the taffrail after dark. Her berth opens east through the hand-drawn bulkhead (every
photograph shows open water on her river side), and the riverfront promenade strip is broken there.

These checks cut the Moshulu's section out of app.js and build her under Node with the vendored three.min.js from the
real footprint in scene.json: her frame (bow north), no NaN anywhere, every vertex stream a float stream (no 1- or 3-byte
stream, Round 158), the hull's sides wound outward and her decks wound upward (a deck wound the other way is culled and
the water shows through it), her lines' heights, the ribbons and bulbs, the levels by distance and the phone's path. Then
the wiring: ?real=0 and ?moshulu=0 keep the old model and the old berth, the art's manifest and its build guard, the
fetch script's key handling, and no program of hers writes gl_FragDepth."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


HARNESS = r'''
const THREE = require(@@THREE@@);
const V3 = THREE.Vector3;
const location = { search: '' };
const REAL = true, isTouch = @@TOUCH@@, MAT_DITHER = true;
const TERRAIN = { water: -7.84, bulkhead: -5.54 };
const nightUniform = { value: 1 }, lampUniform = { value: 1 };
const PERF = { failed: [], enterT: 0 };
const WXFX = { dayF: 1 };
const window = {};
const camera = new THREE.PerspectiveCamera(58, 1.6, 0.75, 26000);
const renderer = { getPixelRatio: () => 1, domElement: { height: 800 } };
const groupCity = new THREE.Group();
const pendingUpload = [];
let freed = 0;
const freeOnUpload = (g) => { freed++; };
const freeTexOnUpload = (t) => t;
const postRaw = (m) => m, architecturalBloom = (m) => m, anisoOf = (n) => n;
const artImage = () => Promise.resolve(null), artSrc = (a, b) => a;
const MOSHULU_ART = @@MANIFEST@@;
const canvasLog = [];
const document = { createElement: () => { const cv = { width: 0, height: 0, getContext: () => new Proxy({}, { get: (o, k) => k === 'createLinearGradient' ? () => ({ addColorStop() {} }) : (k in o ? o[k] : (...a) => { if (k === 'fillText') canvasLog.push(a[0]); }), set: (o, k, v) => { o[k] = v; return true; } }) }; return cv; } };
const MOSHULU_ON = true;
const MOSHULU_SLIP = @@SLIP@@;
@@HELPERS@@
@@SECTION@@
const b = @@SHIP@@;
const ob = orientedBox(b.poly);
const ok = moshuluBuild(b, ob);
const S = MOSHULU, f = S.frame, out = { ok, frame: { ax: f.ax, az: f.az, Ld: f.Ld }, tris: S.tris, bulbN: S.bulbN, ribbons: S.ribbons, pending: pendingUpload.length, freed, canvasLog };
// every stream a float stream, no NaN
out.streams = []; out.nan = 0;
groupCity.traverse((o) => { if (!o.geometry) return; for (const k in o.geometry.attributes) { const a = o.geometry.attributes[k]; out.streams.push([o.name || o.parent.name, k, a.array.constructor.name, a.itemSize]); for (const v of a.array) if (!Number.isFinite(v)) out.nan++; } });
// the hull: its sides wound outward, its decks wound upward; its heights over the water
const near = groupCity.getObjectByName('moshulu-near'), hull = near.children[0].geometry;
const P = hull.attributes.position.array, K = hull.attributes.aMo.array;
let deckUp = 0, deckDown = 0, sideOut = 0, sideIn = 0, maxY = -1e9, minY = 1e9, maxT = 0;
const cx = f.O[0], cz = f.O[1];
for (let t = 0; t < P.length / 9; t++) {
  const A = new V3(P[t * 9], P[t * 9 + 1], P[t * 9 + 2]), B = new V3(P[t * 9 + 3], P[t * 9 + 4], P[t * 9 + 5]), C = new V3(P[t * 9 + 6], P[t * 9 + 7], P[t * 9 + 8]);
  const n = new V3().subVectors(B, A).cross(new V3().subVectors(C, A)); if (n.lengthSq() < 1e-10) continue; n.normalize();
  const kind = Math.round(K[t * 6]);
  const m = A.clone().add(B).add(C).multiplyScalar(1 / 3), tt = (m.x - cx) * f.px + (m.z - cz) * f.pz;
  if (kind === 1) { if (n.y > 0.9) deckUp++; else if (n.y < -0.9) deckDown++; }
  if (kind === 0 && Math.abs(n.y) < 0.5 && Math.abs(tt) > 1) { if ((n.x * f.px + n.z * f.pz) * tt > 0) sideOut++; else sideIn++; }
  for (const q of [A, B, C]) { maxY = Math.max(maxY, q.y); minY = Math.min(minY, q.y); maxT = Math.max(maxT, Math.abs((q.x - cx) * f.px + (q.z - cz) * f.pz)); }
}
out.hull = { deckUp, deckDown, sideOut, sideIn, railTop: maxY - TERRAIN.water, bottom: minY - TERRAIN.water, maxHalf: maxT };
// the trucks and the festoons
const bulbs = groupCity.getObjectByName('moshulu-bulbs').geometry.attributes.position.array;
let bTop = -1e9, bLow = 1e9; for (let i = 1; i < bulbs.length; i += 3) { bTop = Math.max(bTop, bulbs[i]); bLow = Math.min(bLow, bulbs[i]); }
out.bulbs = { top: bTop - TERRAIN.water, low: bLow - TERRAIN.water };
const rig = groupCity.getObjectByName('moshulu-rigging').geometry.attributes.aMoSR.array;
let rMax = 0, rMin = 1e9; for (const v of rig) { rMax = Math.max(rMax, Math.abs(v)); rMin = Math.min(rMin, Math.abs(v)); }
out.rig = { rMax, rMin };
// the levels by distance
const lv = (d) => { camera.position.copy(S.c).add(new V3(d, 0, 0)); moshuluStep(); return { near: S.near.visible, far: S.far.visible, spars: S.spars.visible, rig: S.rig.visible, bulbs: S.bulbs.visible }; };
out.lod = { at100: lv(100), at900: lv(900), at2000: lv(2000), back200: lv(200) };
lampUniform.value = 0; out.dayBulbs = lv(100).bulbs;
console.log(JSON.stringify(out));
'''


class Moshulu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')
        cls.sec = cut(cls.src, '  // ---- the Moshulu (Round 195', "  step('Mooring the ships'")

    def build(self, touch=False):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        scene = json.loads((ROOT / 'scene.json').read_text())
        ship = next(b for b in scene['buildings'] if b.get('t') == 'ship' and b.get('name') == 'Moshulu')
        x0 = min(p[0] for p in ship['poly']); x1 = max(p[0] for p in ship['poly'])
        z0 = min(p[1] for p in ship['poly']); z1 = max(p[1] for p in ship['poly'])
        helpers = '\n'.join([
            cut(self.src, '  function hash01(n) {', '\n  function clamp('),
            cut(self.src, '  function clamp(v, a, b) {', '\n'),
            cut(self.src, '  function orientedBox(poly) {', '\n  // hip roof over an OBB'),
            cut(self.src, '  function obbAxis(ob) {', '\n  function obbEnd('),
        ])
        subs = {'THREE': json.dumps(str(ROOT / 'three.min.js')), 'TOUCH': 'true' if touch else 'false',
                'MANIFEST': (ROOT / 'moshulu_art.json').read_text(), 'SLIP': json.dumps([x0 - 7, 347.5, z0 - 7, z1 + 7, True]),
                'HELPERS': helpers, 'SECTION': self.sec, 'SHIP': json.dumps(ship)}
        js = re.sub(r'@@([A-Z]+)@@', lambda m: subs[m.group(1)], HARNESS)
        with tempfile.TemporaryDirectory() as d:   # a file, not node -e (Node 24 strips types from -e input)
            f = Path(d) / 'moshulu.cjs'
            f.write_text(js)
            r = subprocess.run(['node', str(f)], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, '\n'.join(l[:400] for l in r.stderr.splitlines()[-12:]))
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_she_builds_from_her_outline(self):
        o = self.build()
        self.assertTrue(o['ok'])
        self.assertAlmostEqual(o['frame']['ax'], 0, delta=0.05)      # her keel runs north and south
        self.assertAlmostEqual(o['frame']['az'], -1, delta=0.01)     # her bow points north, toward the Olympia
        self.assertAlmostEqual(o['frame']['Ld'], 113, delta=1.5)
        self.assertEqual(o['nan'], 0)
        t = o['tris']
        self.assertGreater(t['hull'], 5000); self.assertLess(t['hull'], 9000)
        self.assertGreater(t['paint'], 3000); self.assertLess(t['paint'], 8000)
        self.assertLess(t['far'], 1200); self.assertLess(t['spars'], 200)
        self.assertLess(t['hull'] + t['paint'] + t['names'] + t['rig'], 20000)   # the near level's stated budget
        self.assertEqual(o['pending'], 7)   # hull, paint, names, far, rigging, spars, bulbs: drawn once behind the veil

    def test_every_stream_is_a_float_stream(self):
        for name, attr, kind, size in self.build()['streams']:
            self.assertEqual(kind, 'Float32Array', (name, attr))
            self.assertIn(size, (1, 2, 3), (name, attr))

    def test_her_hull_faces_out_and_her_decks_face_up(self):
        h = self.build()['hull']
        self.assertGreater(h['deckUp'], 300)
        self.assertEqual(h['deckDown'], 0)   # (Round 195's first renders: the decks wound down, culled, the water through them)
        self.assertGreater(h['sideOut'], 2000)
        self.assertLess(h['sideIn'], h['sideOut'] * 0.01)
        self.assertGreater(h['railTop'], 9.5); self.assertLess(h['railTop'], 10.3)   # the forecastle's rail
        self.assertAlmostEqual(h['bottom'], -1.6, delta=0.05)                          # under the water, never above it
        self.assertLess(h['maxHalf'], 7.3)                                              # inside her 14.3 m beam

    def test_her_rigging_and_festoons(self):
        o = self.build()
        self.assertGreater(o['ribbons'], 1200)
        self.assertGreater(o['rig']['rMin'], 0.005); self.assertLess(o['rig']['rMax'], 0.08)
        self.assertGreater(o['bulbN'], 180)
        self.assertGreater(o['bulbs']['top'], 58); self.assertLess(o['bulbs']['top'], 64)   # over the main truck
        self.assertGreater(o['bulbs']['low'], 8)                                            # down to the taffrail

    def test_her_levels_by_distance(self):
        o = self.build()['lod']
        self.assertEqual(o['at100'], {'near': True, 'far': False, 'spars': False, 'rig': True, 'bulbs': True})
        self.assertEqual(o['at900'], {'near': False, 'far': True, 'spars': True, 'rig': False, 'bulbs': True})
        self.assertEqual(o['at2000']['far'], True)
        self.assertEqual(o['back200']['near'], True)
        self.assertFalse(self.build()['dayBulbs'])

    def test_a_phone_frees_her_arrays_and_halves_her_boards(self):
        o = self.build(touch=True)
        self.assertEqual(o['freed'], 7)
        self.assertIn('WELCOME ABOARD', o['canvasLog'])

    def test_her_strings_carry_no_dash(self):
        for s in self.build()['canvasLog']:
            self.assertNotIn('—', s); self.assertNotIn('·', s)

    def test_no_program_of_hers_writes_frag_depth(self):
        self.assertNotIn('gl_FragDepth', self.sec)
        self.assertIn("side: THREE.DoubleSide });   // (a ribbon turned to the eye winds either way)", self.sec)


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text(encoding='utf-8')

    def test_real0_and_moshulu0_keep_the_old_ship_and_berth(self):
        s = self.src
        self.assertIn("const MOSHULU_ON = REAL && !/[?&]moshulu=0\\b/.test(location.search);", s)
        ships = cut(s, "  step('Mooring the ships'", '  // ------------------------------------------------ the three towers')
        self.assertIn('if (MOSHULU_ON) {', ships)
        self.assertIn('try { if (moshuluBuild(b, ob)) continue; }', ships)
        # the old model stays in place behind it, verbatim
        self.assertIn("add(extrudePoly(b.poly, null, W + 8.5, W - 0.3), '#202224');", ships)
        self.assertIn("for (const yh of [18, 30, 40]) add(box(22, 0.3, 0.3, mx, W + 8.5 + yh, mz, ry + Math.PI / 2), '#3e3b37');", ships)
        # the berth opens only for her, and the bulkhead and the promenade are unchanged without an open slip
        self.assertIn("if (MOSHULU_ON && /moshulu/i.test(b.name || '')) {", s)
        self.assertIn("if (!slipsOpen.length) { vstrip(ax, az, bx, bz, TERRAIN.bed, TERRAIN.bulkhead, '#6f6a62'); return; }", s)
        self.assertIn('const cutZ = (z) => slips.some((sl) => sl[4] &&', s)

    def test_her_step_runs_every_frame(self):
        frame = cut(self.src, '  function frame(now, once) {', '\n  }\n')
        self.assertIn('moshuluStep();', frame)

    def test_her_art(self):
        man = json.loads((ROOT / 'moshulu_art.json').read_text())
        for k in ('hull', 'deck'):
            self.assertTrue((ROOT / man[k]).exists()); self.assertTrue((ROOT / man[k + 'Half']).exists())
            self.assertRegex(man[k], r'^art/moshulu/' + k + r'\.[0-9a-f]{10}\.webp$')
            self.assertEqual(len(man['m'][k]), 2); self.assertEqual(len(man['mean'][k]), 3)
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("MOSHULU_ART", text_of("moshulu_art.json", "null"))', b)
        self.assertIn('"moshulu_art.json"):', b)
        self.assertIn('Promise.all([artImage(artSrc(A.hull, A.hullHalf)), artImage(artSrc(A.deck, A.deckHalf))])', self.src)

    def test_the_fetch_script_keeps_the_key_private(self):
        f = (ROOT / 'fetch_moshulu_art.py').read_text()
        self.assertIn("os.environ.get('OPENAI_API_KEY')", f)
        self.assertIn("~/.config/philly3d/openai.env", f)
        self.assertNotIn('codex', f)
        self.assertNotIn('print(key', f)
        self.assertIn("'gpt-image-2'", f); self.assertIn("'high'", f)
        self.assertIn('no text', f)
        self.assertIn("os.path.join(HERE, 'lidar_cache', 'moshulu_art_raw')", f)


if __name__ == '__main__':
    unittest.main()
