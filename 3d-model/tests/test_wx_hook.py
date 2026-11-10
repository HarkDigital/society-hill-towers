"""Round 226 (Stage 1 of the Nov 10 plan): the weather's hooks are laid before the first compile, so no program compiles
twice.

Until this round the block after build() wrapped the facade (cityMat, coreMat), every flat that carries userData.wxSurf
and every plain MeshStandardMaterial with the weather's patch, and disposed each one: every one of them had already
compiled without the weather in a flush behind the veil (flushUploads draws the whole scene), so the first frame after
Ready compiled all of them a second time with the button lit. wxHookAll lays the same wrappers under the same keys, is
idempotent, and runs before every flush's render and once more as build() ends.

What must hold:
- the wrappers and the keys are the block's own, to the character (a program's source is what its hooks make of it, and
  Stage 1 changes no shader);
- a second call changes nothing, and a material that arrives between two calls is hooked by the next;
- a hooked material is remembered outside userData, which clone copies (a clone must be hooked, not passed by);
- the facade's own hook stays readable under the weather's (wxOwnHook: City Hall's clone of the facade is made after the
  first flush, and a hook read straight off cityMat would bring the weather's lines in twice);
- nothing is disposed, and the block after build() no longer hooks anything;
- a hook laid over the weather's after a material's first flush is counted on the last call.

The proof that no program's source changed is not here but in the round's captures: the hashes of every shader of every
program linked, old page against new, on the computer and the phone path (devlog, Round 226). This file runs the function
itself under Node with stub materials."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()


def cut(a, b, text=SRC):
    i = text.index(a)
    return text[i:text.index(b, i + len(a))]


HOOK = cut('  const WX_OWN = new WeakMap();', '\n  // decorrelated per-particle gate')


def node(script):
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


HARNESS = r'''
// r149's Material as far as the hooks go: onBeforeCompile and customProgramCacheKey on the prototype, clone copying
// userData through JSON and dropping both
class Mat {
  constructor(o) { this.isMeshStandardMaterial = true; this.userData = {}; this.flatShading = false; this.type = 'MeshStandardMaterial'; this.name = ''; Object.assign(this, o || {}); }
  clone() { const m = new Mat(); m.isMeshStandardMaterial = this.isMeshStandardMaterial; m.flatShading = this.flatShading; m.userData = JSON.parse(JSON.stringify(this.userData)); return m; }
  dispose() { disposed++; }
}
Mat.prototype.onBeforeCompile = function () {};
Mat.prototype.customProgramCacheKey = function () { return this.onBeforeCompile.toString(); };
let disposed = 0;
const location = { search: SEARCH };
const PERF = {}, warned = [];
const console2 = console; const consoleWarn = console.warn; console.warn = (s) => warned.push(String(s));
const objects = [];
const scene = { traverse: (f) => { for (const o of objects) f(o); } };
const renderer = { info: { programs: [] } };
const wxSurfacePatch = (sh) => { sh.log.push('wx'); };
const wxSurfaceLate = (sh) => { sh.log.push('late'); };
const facadeCity = (sh) => { sh.log.push('facade'); }, facadeCore = (sh) => { sh.log.push('facade-core'); };
const cityMat = new Mat(); cityMat.onBeforeCompile = facadeCity; cityMat.customProgramCacheKey = () => 'fabric';
let coreMat = cityMat.clone(); coreMat.onBeforeCompile = facadeCore; coreMat.customProgramCacheKey = () => 'fabric-core';
HOOK
const compile = (m) => { const sh = { log: [] }; m.onBeforeCompile(sh, null); return sh.log.join(','); };
const own = (m) => Object.prototype.hasOwnProperty.call(m, 'onBeforeCompile');
const out = {};
'''


def run(body, search=''):
    return node(HARNESS.replace('SEARCH', json.dumps(search)).replace('HOOK', HOOK) + body + '\nconsole.log(JSON.stringify(out));')


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Hooks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = run(r'''
const surf = new Mat(); surf.userData.wxSurf = true; const surfOwn = (sh) => { sh.log.push('surf'); }; surf.onBeforeCompile = surfOwn;
const ground = new Mat(); ground.userData.wxSurf = true; const groundOwn = (sh) => { sh.log.push('ground'); }; ground.onBeforeCompile = groundOwn; ground.customProgramCacheKey = () => 'ground';
const plain = new Mat(), flat = new Mat({ flatShading: true });
const water = new Mat(); const waterOwn = (sh) => { sh.log.push('water'); }; water.onBeforeCompile = waterOwn; water.customProgramCacheKey = () => 'water';
const basic = new Mat({ isMeshStandardMaterial: false });
objects.push({ material: cityMat }, { material: coreMat }, { material: [surf, plain] }, { material: ground }, { material: flat }, { material: water }, { material: basic }, { material: plain }, {});
wxHookAll();
out.first = { city: compile(cityMat), core: compile(coreMat), surf: compile(surf), ground: compile(ground), plain: compile(plain), flat: compile(flat), water: compile(water), basic: compile(basic) };
out.keys = { city: cityMat.customProgramCacheKey(), core: coreMat.customProgramCacheKey(), surf: surf.customProgramCacheKey() === 'wx|' + surfOwn.toString(), ground: ground.customProgramCacheKey() === 'wx|' + groundOwn.toString(),
  plain: plain.customProgramCacheKey() === wxSurfacePatch.toString(), water: water.customProgramCacheKey() };
out.plainIsThePatch = plain.onBeforeCompile === wxSurfacePatch;
out.untouched = [water.onBeforeCompile === waterOwn, !own(flat), !own(basic)];
out.mats1 = PERF.wxHook.mats;
// a second call, and a third: nothing moves
const fns = [cityMat, coreMat, surf, ground, plain].map((m) => m.onBeforeCompile);
wxHookAll(); wxHookAll();
out.same = [cityMat, coreMat, surf, ground, plain].every((m, i) => m.onBeforeCompile === fns[i]);
out.second = { city: compile(cityMat), surf: compile(surf), plain: compile(plain) };
out.mats2 = PERF.wxHook.mats; out.calls = PERF.wxHook.n;
// what arrives between two flushes is hooked by the next: a new flat, a new plain material, and a CLONE of a hooked
// flat, which carries the flat's userData and none of its hooks
const late = new Mat(); late.userData.wxSurf = true; const lateOwn = (sh) => { sh.log.push('late-own'); }; late.onBeforeCompile = lateOwn;
const plain2 = new Mat();
const cl = surf.clone();
out.cloneBefore = [cl.userData.wxSurf === true, own(cl)];
objects.push({ material: late }, { material: plain2 }, { material: cl });
wxHookAll();
out.third = { late: compile(late), plain2: compile(plain2), clone: compile(cl) };
out.cloneHooked = own(cl);
out.mats3 = PERF.wxHook.mats;
// nothing is remembered in userData
out.userData = [Object.keys(surf.userData), Object.keys(plain.userData), Object.keys(cityMat.userData)];
// the facade's own hook, under the weather's
out.ownHook = [wxOwnHook(cityMat) === facadeCity, wxOwnHook(coreMat) === facadeCore, wxOwnHook(water) === waterOwn, wxOwnHook(surf) === surfOwn, wxOwnHook(plain) === wxSurfacePatch];
// City Hall's clone, made after the first flush, on the facade's own hook: the weather's lines once, never twice
const hall = cityMat.clone(), hallFacade = wxOwnHook(cityMat);
hall.onBeforeCompile = (sh, r) => { hallFacade(sh, r); sh.log.push('flood'); }; hall.customProgramCacheKey = () => 'city-hall-soft-flood';
objects.push({ material: hall });
wxHookAll();
out.hall = [compile(hall), hall.customProgramCacheKey()];
out.disposed = disposed;
// the last call counts a hook laid over the weather's after the material's first flush
out.over0 = PERF.wxHook.over;
const chained = plain2.onBeforeCompile; plain2.onBeforeCompile = (sh, r) => { chained(sh, r); sh.log.push('late hook'); };
wxHookAll(true);
out.over = PERF.wxHook.over; out.warned = warned.length;
''')

    def test_the_wrappers_and_the_keys_are_the_old_blocks(self):
        r = self.r
        self.assertEqual(r['first'], {'city': 'facade,wx', 'core': 'facade-core,wx', 'surf': 'wx,surf,late', 'ground': 'wx,ground,late', 'plain': 'wx', 'flat': '', 'water': 'water', 'basic': ''})
        self.assertEqual(r['keys'], {'city': 'fabric|wx', 'core': 'fabric-core|wx', 'surf': True, 'ground': True, 'plain': True, 'water': 'water'})
        self.assertTrue(r['plainIsThePatch'])            # the bare function, so every plain material shares r149's default key
        self.assertEqual(r['untouched'], [True, True, True])   # a hook of its own, flat shading, not a standard material
        self.assertEqual(r['mats1'], 5)
        # the text itself, once each in the page: the facade's wrapper, the flats' wrapper and key, the bare patch
        f = HOOK
        self.assertIn('m.onBeforeCompile = (sh, r) => { prev(sh, r); wxSurfacePatch(sh); };', f)
        self.assertIn("facade(cityMat, 'fabric|wx');\n    facade(coreMat, 'fabric-core|wx');", f)
        self.assertIn('m.onBeforeCompile = (sh, r) => { wxSurfacePatch(sh); prev(sh, r); wxSurfaceLate(sh); };', f)
        self.assertIn("m.customProgramCacheKey = () => 'wx|' + prev.toString();", f)
        self.assertIn("if (Object.prototype.hasOwnProperty.call(m, 'onBeforeCompile')) continue;\n        if (m.flatShading) continue;\n        m.onBeforeCompile = wxSurfacePatch;", f)
        for line in ("facade(cityMat, 'fabric|wx');", "facade(coreMat, 'fabric-core|wx');", "m.customProgramCacheKey = () => 'wx|' + prev.toString();", 'm.onBeforeCompile = wxSurfacePatch;'):
            self.assertEqual(SRC.count(line), 1, line)

    def test_idempotent(self):
        r = self.r
        self.assertTrue(r['same'])
        self.assertEqual(r['second'], {'city': 'facade,wx', 'surf': 'wx,surf,late', 'plain': 'wx'})
        self.assertEqual((r['mats2'], r['calls']), (5, 3))

    def test_what_arrives_later_is_hooked_and_a_clone_is_not_taken_for_hooked(self):
        r = self.r
        self.assertEqual(r['cloneBefore'], [True, False])   # the flag came with userData, the hook did not
        self.assertEqual(r['third'], {'late': 'wx,late-own,late', 'plain2': 'wx', 'clone': 'wx,late'})
        self.assertTrue(r['cloneHooked'])
        self.assertEqual(r['mats3'], 8)
        self.assertEqual(r['userData'], [['wxSurf'], [], []])
        self.assertIn('const WX_OWN = new WeakMap();', HOOK)
        self.assertNotIn('userData.wxHooked', SRC)

    def test_the_facades_own_hook_stays_readable(self):
        r = self.r
        self.assertEqual(r['ownHook'], [True, True, True, True, True])
        self.assertEqual(r['hall'], ['facade,flood', 'city-hall-soft-flood'])
        self.assertEqual(SRC.count('hallFacade=wxOwnHook(cityMat);'), 1)
        self.assertNotIn('hallFacade=cityMat.onBeforeCompile', SRC)

    def test_nothing_is_disposed(self):
        self.assertEqual(self.r['disposed'], 0)
        self.assertNotIn('dispose', HOOK.split('  function wxHookAll(last) {')[1])

    def test_a_hook_laid_over_the_weathers_is_counted_on_the_last_call(self):
        r = self.r
        self.assertEqual((r['over0'], r['over']), (0, 1))
        self.assertEqual(r['warned'], 0)                 # the warning is ?dev's
        d = run(r'''
const p = new Mat(); objects.push({ material: p }); wxHookAll();
const c = p.onBeforeCompile; p.onBeforeCompile = (sh, r) => { c(sh, r); };
wxHookAll(true); out.over = PERF.wxHook.over; out.warned = warned.length;
// ?dev: a program a flush linked that the first frame no longer has is listed
renderer.info.programs = [{ id: 1, name: 'MeshStandardMaterial', cacheKey: 'a,b,fabric' }, { id: 2, name: 'ShaderMaterial', cacheKey: 'sky' }];
progNote();
renderer.info.programs = [{ id: 2, name: 'ShaderMaterial', cacheKey: 'sky' }, { id: 3, name: 'MeshStandardMaterial', cacheKey: 'a,b,fabric|wx' }];
progLost(); out.prog = PERF.prog; out.warned2 = warned.length;
''', search='?dev=1')
        self.assertEqual((d['over'], d['warned']), (1, 1))
        self.assertEqual(d['prog'], {'f1': 2, 'lost': ['MeshStandardMaterial a,b,fabric']})
        self.assertEqual(d['warned2'], 2)
        # without ?dev nothing is kept and nothing is listed: only the count after the first frame
        q = run(r'''
renderer.info.programs = [{ id: 1, name: 'a', cacheKey: 'k' }]; progNote(); renderer.info.programs = []; progLost(); out.prog = PERF.prog;
''')
        self.assertEqual(q['prog'], {'f1': 0, 'lost': []})


class Wiring(unittest.TestCase):
    def test_before_every_flushs_render(self):
        flush = cut('  const flushUploads = (all) => {', '\n  };')
        self.assertEqual(flush.count('wxHookAll();'), 1)
        self.assertLess(flush.index('< 12)) return;'), flush.index('wxHookAll();'), 'only a flush that renders pays for the walk')
        self.assertLess(flush.index('wxHookAll();'), flush.index('renderer.render(scene, camera)'))
        self.assertLess(flush.index('renderer.render(scene, camera)'), flush.index('progNote();'))

    def test_once_more_as_the_build_ends(self):
        b = cut('  async function build() {', '\n  }\n')
        self.assertEqual(b.count('wxHookAll('), 1)
        self.assertLess(b.index('for (const s of buildSteps)'), b.index('wxHookAll(true);'))
        self.assertLess(b.index('wxHookAll(true);'), b.index("bootMark('ready')"))
        # and nothing renders the scene between that call and the first frame (tests/test_cull.py holds the same line)
        self.assertNotIn('renderer.render(', cut('  async function build() {', '  btnEnter.addEventListener('))

    def test_the_block_after_the_build_hooks_nothing_and_disposes_nothing(self):
        tail = SRC[SRC.index('  build().then(() => {'):]
        head = tail[:tail.index("    if (/[?&]dev\\b/.test(location.search)) {")]
        for gone in ('onBeforeCompile', 'customProgramCacheKey', '.dispose()', 'scene.traverse'):
            self.assertNotIn(gone, head, gone)
        self.assertNotIn('wxHookAll(', tail)              # build() made the last call: the block comes after it
        self.assertNotIn('cityMat.dispose()', SRC)
        self.assertNotIn('coreMat.dispose()', SRC)

    def test_the_first_frame_reads_the_programs(self):
        f = cut('  function frame(now, once) {', '\n  setHint();')
        self.assertIn('if (PERF.prog.f1 < 0) progLost();', f)
        self.assertLess(f.index('if (POST.on) renderPost(scene, camera); else renderer.render(scene, camera);'), f.index('if (PERF.prog.f1 < 0) progLost();'))

    def test_no_glsl_in_the_hooking(self):
        # the function lays hooks; it holds no shader text of its own (Stage 1's rule: no shader text changes)
        for word in ('gl_', 'uniform ', 'varying ', '#include', 'vec3', '.replace('):
            self.assertNotIn(word, HOOK.split('  function wxHookAll(last) {')[1].replace(".replace(/\\s+/g, ' ')", ''), word)


if __name__ == '__main__':
    unittest.main()
