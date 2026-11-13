"""Stage 2 of the Nov 10 plan, its performance half (Round 251): fewer programs and less wasted shading, nothing on screen
changed (each checked by a pixel parity of noon and night poses, devlog Round 251).

- The program diet: the outer city's and the core's facades share one program (their gains are each material's uniform,
  uFabG and uFabR, never literals); the El stations' four lit materials one key; the lamps' lens and lantern glass one
  (uLensK); the roof kit's kinds one program but the deck's, which ends in a discard (KIT_SHARED).
- The backdrops drawn last: the sky dome at 45 and the apron at 40, both under the river mirror's sweep line (50), the
  apron named out of the mirror; every other sampled window of the GPU timer draws them in the old order under 'sceneB'.
- The cloud shadow's gate: cloudShade returns 0 at once where its strength is 0.
- The rebuilds' family (K.fam in rebuilds/_kit.js): every rebuild material with a hook of its own is a part of one program
  text, its code behind a gate on uRbFx; one key for the family, the same text for every member, each part's code once."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


class Diet(unittest.TestCase):
    def test_one_facade_program(self):
        self.assertEqual(SRC.count("customProgramCacheKey = () => 'fabric'"), 2)
        self.assertIn("facade(cityMat, 'fabric|wx');", SRC)
        self.assertIn("facade(coreMat, 'fabric|wx');", SRC)
        a = SRC.index('    const facadeHook = (gW, gR, sat, satR) => (shader) => {')
        b = SRC.index('    cityMat.onBeforeCompile = facadeHook(FACADE_GAIN, ROOF_GAIN, 1.2);')
        h = SRC[a:b]
        # the gains reach the text only through the uniforms: no number of theirs is written into the shader
        self.assertNotRegex(h, r"' \+ \(?(gW|gR|sat|satR)\b")   # no gain concatenated into the shader's text
        self.assertIn("'uniform float uFabSnow, uFabWet; uniform vec4 uFabK; uniform vec4 uFabG; uniform float uFabR;',", h)

    def test_the_small_merges(self):
        self.assertIn("m.customProgramCacheKey = () => 'lamp-lens';", SRC)
        self.assertNotIn("'lamp-lens-' + k", SRC)
        self.assertIn("sh.uniforms.uLensK = { value: new THREE.Vector2(day, k) };", SRC)
        el = (ROOT / 'rebuilds' / 'elst.js').read_text()
        self.assertIn("return K.fam(m, { id: 'elst-lit',", el)
        self.assertNotIn("'elst-' + key", el)

    def test_the_roof_kit_is_two_programs(self):
        self.assertIn("const KIT_SHARED = (k) => !(REAL && k === 5);", SRC)
        self.assertIn("mat.customProgramCacheKey = () => (shared ? 'roofkit' : 'roofkit-' + ki) + (REAL ? '-real' : '');", SRC)
        self.assertIn("sh.uniforms.uKitKind = { value: ki };", SRC)
        # the deck's discard stays out of the shared program
        i = SRC.index('const kitDetailShared = () => {')
        shared = SRC[i:SRC.index('};', i)]
        self.assertIn('if (!KIT_SHARED(k)) continue;', shared)


FAM_SCRIPT = r'''
const fs = require('fs'), vm = require('vm');
const THREE = require(THREE_PATH);
global.THREE = THREE;
const ctx2d = new Proxy({}, { get: (t, k) => (k in t ? t[k] : (k === 'measureText' ? () => ({ width: 10 }) : () => {})), set: (t, k, v) => { t[k] = v; return true; } });
global.document = { createElement: () => ({ width: 0, height: 0, style: {}, getContext: () => ctx2d }) };
global.location = { search: '' };
global.RB = { defs: [], kit: null, add(def) { global.RB.defs.push(def); } };
for (const f of FILES) vm.runInThisContext(fs.readFileSync(f, 'utf8'), { filename: f });
const K = RB.kit(THREE), mats = new Set();
for (const d of RB.defs) {
  const api = { THREE, K, where: 'app', ground: () => 0, night: { value: 0 }, lamp: { value: 0 }, time: { value: 0 },
    foam: { tex: { value: null }, on: { value: 0 }, m: { value: 8 } },
    lampU: { uLampMap: { value: null }, uLampBox: { value: new THREE.Vector4() }, uLampOn: { value: 0 }, uLampFade: { value: new THREE.Vector4() } },
    dayF: () => 1, lawn: null, occupy: () => {}, pinAt: () => {}, log: () => {}, elAt: () => null };
  try { d.build(api).traverse((o) => { if (o.isMesh) for (const m of [].concat(o.material)) if (m.userData.rbFam) mats.add(m); }); } catch (e) { console.error(d.id, e); }
}
const L = THREE.ShaderLib.standard, out = { info: K.famInfo(), mats: [] };
for (const m of mats) {
  const sh = { uniforms: THREE.UniformsUtils.clone(L.uniforms), vertexShader: L.vertexShader, fragmentShader: L.fragmentShader };
  m.onBeforeCompile(sh, null);
  out.mats.push({ part: m.userData.rbFam, key: m.customProgramCacheKey(), vs: sh.vertexShader, fs: sh.fragmentShader, uni: Object.keys(sh.uniforms), fx: sh.uniforms.uRbFx.value });
}
console.log(JSON.stringify(out));
'''


class Family(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        rb = ROOT / 'rebuilds'
        files = [str(rb / '_kit.js')] + sorted(str(p) for p in rb.glob('*.js') if p.name != '_kit.js')
        script = FAM_SCRIPT.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('FILES', json.dumps(files))
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        if run.returncode:
            raise AssertionError(run.stderr[-3000:])
        cls.out = json.loads(run.stdout)

    def test_the_parts(self):
        info = self.out['info']
        self.assertEqual(sorted(info['parts']), sorted(['dl-lampwash', 'elst-lit', 'esp-night-ground', 'esp-night-wall', 'esp-night-wall-flood', 'gc-flood',
            'rtm-glass', 'rtm-mas', 'rtm-metal', 'rtm-sky', 't30-base', 't30-glass', 't30-lime', 't30-roof', 't30-shed', 't30-trim',
            'ww-apron', 'ww-foam', 'ww-glass', 'ww-wash']))
        self.assertEqual(info['ver'], len(info['parts']))
        self.assertGreater(len(self.out['mats']), len(info['parts']))   # several materials share a part

    def test_one_key_and_one_text(self):
        mats = self.out['mats']
        self.assertEqual({m['key'] for m in mats}, {'rbfam-' + str(self.out['info']['ver'])})
        # the promise the key makes: every member compiles exactly one text, whatever its part
        self.assertEqual(len({m['vs'] for m in mats}), 1)
        self.assertEqual(len({m['fs'] for m in mats}), 1)
        vs, fs = mats[0]['vs'], mats[0]['fs']
        self.assertEqual(vs.count('varying vec3 vRbW;'), 1)
        self.assertEqual(fs.count('varying vec3 vRbW;'), 1)
        for n in range(1, self.out['info']['ver'] + 1):
            self.assertEqual(fs.count('if (abs(uRbFx - %d.0) < 0.5) {' % n), len(re.findall(r'abs\(uRbFx - %d\.0\)' % n, fs)))
        for fn in ('float t30h(', 'vec2 t30loc(', 'vec3 t30flood(', 'float fh(', 'float foamAt('):
            self.assertEqual(fs.count(fn), 1, fn)
        for old in ('vWP', 'vWN', 'vDat', 'vEspW', 'vEspN', 'vWwPos', 'vWwN', 'vWwF', 'vFoamUv', 'vPane', 'vWY'):
            self.assertNotRegex(fs, r'\b%s\b' % old)

    def test_every_member_has_every_uniform_and_its_own_gate(self):
        mats = self.out['mats']
        uni = set(mats[0]['uni'])
        for m in mats:
            self.assertEqual(set(m['uni']), uni)   # a declared sampler is never left on another material's unit
        by = {}
        for m in mats:
            by.setdefault(m['part'], set()).add(m['fx'])
        self.assertTrue(all(len(v) == 1 for v in by.values()))
        self.assertEqual(len({next(iter(v)) for v in by.values()}), len(by))

    def test_the_detail_pass_reads_the_familys_varyings(self):
        self.assertIn("const fam = !!(own && m.userData.rbFam);", SRC)
        self.assertIn("if (!fam) sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\\nvarying vec3 vRbW; varying vec3 vRbN;')", SRC)
        self.assertIn("m.customProgramCacheKey = () => ownKey.call(m) + '|rbdetail';", SRC)


class Backdrops(unittest.TestCase):
    def test_drawn_last_and_out_of_the_mirror(self):
        self.assertIn("const BACKDROP = { sky, apron: null, sky0: BACKDROP_FIRST ? 0 : 45, apron0: BACKDROP_FIRST ? -1 : 40, ab: !BACKDROP_FIRST };", SRC)
        self.assertIn('sky.renderOrder = BACKDROP.sky0;', SRC)
        self.assertIn('apron.renderOrder = BACKDROP.apron0;', SRC)
        self.assertIn('apron.userData.reflK = 0;', SRC)
        # the mirror's sweep takes 0 to 49: both new orders stay inside it, which is why the apron is named out
        self.assertIn('o.renderOrder >= 0 && o.renderOrder < 50', SRC)
        for v in (45, 40):
            self.assertLess(v, 50)

    def test_the_ab_in_the_timers_windows(self):
        post = SRC[SRC.index('  function renderPost(sc, cam) {'):]
        post = post[:post.index('\n  }\n')]
        self.assertIn('const oldOrder = GPUT.live && BACKDROP.ab && Math.floor(GPUT.fid / GPUT_EVERY) % 2 === 1;', post)
        self.assertLess(post.index('BACKDROP.sky.renderOrder = oldOrder ? 0 : BACKDROP.sky0;'), post.index("gpuT(oldOrder ? 'sceneB' : 'scene');"))
        self.assertLess(post.index("gpuT(oldOrder ? 'sceneB' : 'scene');"), post.index('renderer.render(sc, cam);'))


class CloudGate(unittest.TestCase):
    def test_a_strength_of_nothing_returns_at_once(self):
        self.assertIn("'float cloudShade(vec2 wp){ if (uCloudSh <= 0.0) return 0.0; vec2 cp =", SRC)
        line = [l for l in SRC.splitlines() if "'float cloudShade(vec2 wp){" in l][0]
        self.assertTrue(re.search(r"\* uCloudSh; \}',$", line.strip()), 'the result is still the strength times the shade')


if __name__ == '__main__':
    unittest.main()
