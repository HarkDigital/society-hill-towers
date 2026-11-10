"""Round 226 (Stage 1 of the Nov 10 plan): ?veilcity=1, a computer's veil showing the city rising. Off by default.

Under the desktop post pipeline a flush behind the veil draws into the float target and never presents, so a computer
shows an empty veil for the whole build. With the flag each flush ends with one composite of its own picture onto the
canvas: the frames' own composite material on the frames' own quad, with no bloom and no occlusion (nothing has drawn
their targets yet). Where the canvas is drawn through reversed depth's own framebuffer and no post pipeline (an iPhone)
a flush is not presented either, and the flag presents it with the frames' own blit.

What must hold:
- off by default, and off for any value but 1: the loading screen changes only when the flag asks;
- it adds no program a session would not compile anyway and changes no shader: it makes no material and holds no GLSL,
  it draws the frames' postComp;
- the bloom's strength is never written (wxGrade is its one writer, tests/test_realism_weather.py): the bloom's targets
  have not been drawn, and three reads an undrawn target as black; the occlusion is off for the draw;
- one draw a flush, after the flush's own render and before its meshes go back to culling.

veilCityShow is cut from app.js and run under Node with a recording renderer."""
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


VEIL = cut('  const VEIL_CITY = /[?&]veilcity=1\\b/.test(location.search);', '\n\n  const scene = new THREE.Scene();')


def node(script):
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


HARNESS = r'''
const location = { search: SEARCH };
const PERF = {}, calls = [];
const POST = { on: POST_ON }, ZREV = { sub: ZSUB };
const postRT = { texture: 'scene-tex' }, postA = { texture: 'bloom-tex' };
const postScene = 'postScene', postCam = 'postCam';
const postComp = { uniforms: { tScene: { value: null }, tBloom: { value: null }, uBloom: { value: 0.45 }, uAO: { value: 1 }, tAO: { value: 'ao-tex' }BLOOMW } };
const postQuad = { material: 'the last pass' };
let target = 'postRT';
const renderer = { setRenderTarget: (t) => { target = t; }, render: (s, c) => { calls.push({ target, scene: s, cam: c, mat: postQuad.material === postComp ? 'postComp' : String(postQuad.material),
  bloom: postComp.uniforms.uBloom.value, ao: postComp.uniforms.uAO.value, tScene: postComp.uniforms.tScene.value, tBloom: postComp.uniforms.tBloom.value, tBloomW: postComp.uniforms.tBloomW ? postComp.uniforms.tBloomW.value : undefined }); } };
let presents = 0; function zrevPresent() { presents++; }
VEIL
const out = { flag: VEIL_CITY };
'''


def run(body, search='?veilcity=1', post=True, sub=False, bloomw=True):
    h = HARNESS.replace('SEARCH', json.dumps(search)).replace('POST_ON', 'true' if post else 'false').replace('ZSUB', 'true' if sub else 'false')
    h = h.replace('BLOOMW', ", tBloomW: { value: null }, uBloomW: { value: 1 }" if bloomw else '').replace('\nVEIL\n', '\n' + VEIL + '\n')
    return node(h + body + '\nconsole.log(JSON.stringify(out));')


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Show(unittest.TestCase):
    def test_off_by_default(self):
        for q in ('', '?dev=1', '?veilcity=0', '?veilcity=10', '?veilcity', '?xveilcity=1'):
            self.assertFalse(run('', search=q)['flag'], q)
        for q in ('?veilcity=1', '?dev=1&veilcity=1', '?veilcity=1&dpr=1'):
            self.assertTrue(run('', search=q)['flag'], q)
        self.assertIn('    if (VEIL_CITY) veilCityShow();', SRC)
        self.assertEqual(SRC.count('veilCityShow()'), 2)      # its definition and the flush's one call, behind the flag

    def test_one_composite_of_the_flushs_own_picture(self):
        r = run('veilCityShow(); out.calls = calls; out.after = { bloom: postComp.uniforms.uBloom.value, target, presents, perf: [PERF.veilCity.on, PERF.veilCity.n] };')
        self.assertEqual(len(r['calls']), 1)
        c = r['calls'][0]
        self.assertEqual((c['target'], c['scene'], c['cam'], c['mat']), (None, 'postScene', 'postCam', 'postComp'))   # onto the canvas, the frames' quad and material
        self.assertEqual((c['tScene'], c['tBloom'], c['tBloomW']), ('scene-tex', 'bloom-tex', 'bloom-tex'))
        self.assertEqual((c['bloom'], c['ao']), (0.45, 0))     # the occlusion off; the bloom's strength untouched (its undrawn targets read as black)
        self.assertEqual(r['after'], {'bloom': 0.45, 'target': None, 'presents': 0, 'perf': [True, 1]})

    def test_without_the_wide_bloom(self):
        r = run('veilCityShow(); out.calls = calls;', bloomw=False)
        self.assertEqual(len(r['calls']), 1)
        self.assertIsNone(r['calls'][0].get('tBloomW'))

    def test_a_canvas_drawn_through_reversed_depths_own_framebuffer_is_presented(self):
        r = run('veilCityShow(); veilCityShow(); out.calls = calls.length; out.presents = presents; out.n = PERF.veilCity.n;', post=False, sub=True)
        self.assertEqual((r['calls'], r['presents'], r['n']), (0, 2, 2))
        # and a canvas the flush drew straight onto (log depth, no post pipeline) needs nothing
        r = run('veilCityShow(); out.calls = calls.length; out.presents = presents;', post=False, sub=False)
        self.assertEqual((r['calls'], r['presents']), (0, 0))


class Wiring(unittest.TestCase):
    def test_after_the_flushs_render_and_before_its_meshes_cull_again(self):
        flush = cut('  const flushUploads = (all) => {', '\n  };')
        self.assertEqual(flush.count('veilCityShow()'), 1)
        a = flush.index('renderer.render(scene, camera); renderer.setRenderTarget(null); } else renderer.render(scene, camera);')
        self.assertLess(a, flush.index('if (VEIL_CITY) veilCityShow();'))
        self.assertLess(flush.index('if (VEIL_CITY) veilCityShow();'), flush.index('for (const m of pendingUpload) m.frustumCulled = true;'))

    def test_no_new_program_and_no_shader_text(self):
        f = cut('  function veilCityShow() {', '\n  }\n')
        for word in ('new THREE.', 'ShaderMaterial', 'onBeforeCompile', 'gl_', '#include', 'fragmentShader', 'vertexShader', 'needsUpdate', 'defines'):
            self.assertNotIn(word, f, word)
        self.assertIn('postQuad.material = postComp;', f)
        self.assertNotIn('uBloom', f)                           # one writer of the grade (wxGrade)
        self.assertIn('renderer.setRenderTarget(null); renderer.render(postScene, postCam);', f)
        # the composite it draws is the one the frames draw: postInit makes postComp once, and nothing here touches its text
        self.assertEqual(SRC.count('postComp = new THREE.ShaderMaterial('), 1)

    def test_the_frames_composite_is_untouched(self):
        post = cut('  function renderPost(sc, cam) {', '\n  }\n')
        self.assertNotIn('VEIL_CITY', post)
        self.assertIn('postComp.uniforms.uAO.value = 0;', post)   # the frame sets its own occlusion and scene every time, whatever the flush left
        self.assertIn('postQuad.material = postComp; postComp.uniforms.tScene.value = postRT.texture; postComp.uniforms.tBloom.value = postA.texture;', post)


if __name__ == '__main__':
    unittest.main()
