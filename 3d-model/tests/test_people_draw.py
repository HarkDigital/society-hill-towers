"""Round 227: the walkers drawn (app.js, '// ---- people on the sidewalks: the drawing'), behind ?people=1.

The section is cut from app.js and run under Node on the vendored three.min.js itself (its geometry, material and
InstancedMesh classes need no GL), with the page's own lamp and cloud patches cut in beside it, so what is held is the
page's text and not a copy of it:
  - without the flag nothing is made: no mesh, no material, no texture, no buffer, and the frame's one hook is behind
    PEOPLE_ON; under the flag nothing is made before Ready, and the frame after Ready makes the meshes with ONE
    collapsed instance (the programs' warm-up) and calls peopleInit beside it;
  - the static rules: every instance stream is 4-byte floats (WebKit pads a 1- or 3-byte stream), every mesh carries
    reflK 0, casts nothing and has no depth material, no program of the section writes gl_FragDepth, and the art is
    asked for through artImage(artSrc(...)) alone, the sharp copy by a computer under ?people=sharp and nobody else;
  - the view: the front inside 45 degrees of walking at the eye, the back inside 45 of walking away, the side between,
    mirrored when the walker's way is toward the viewer's left, and both cells with a share between them across the
    hand-over; the step: stride, pass, stride, pass, the second stride mirrored only for a figure PEOPLE_SYM names;
    the sun's view for the shadow, from the side always the passing pose; the figure index taken modulo the figures;
  - the patches land: every anchor the card's and the shadow's patches replace is in r149's shaders, under the
    realistic look and under ?real=0, the lamps' share is the card's own uniform in its own text, the shared patch
    functions are called and never rewritten, and each program stays far under sixteen samplers."""
import json
import os
import pathlib
import re
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANNER, END = '  // ---- people on the sidewalks: the drawing (Round 227', '  // ---- people on the sidewalks: the drawing ends'

HARNESS = r'''
const fs = require('fs'), path = require('path');
const ROOT = process.env.PP_ROOT;
const REALTHREE = require(path.join(ROOT, 'three.min.js'));
const src = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8');
const cut = (a, b) => { const i = src.indexOf(a); if (i < 0) throw new Error('app.js lacks ' + a); const j = src.indexOf(b, i + a.length); if (j < 0) throw new Error('app.js lacks ' + b); return src.slice(i, j); };
const draw = cut('  // ---- people on the sidewalks: the drawing (Round 227', '  // ---- people on the sidewalks: the drawing ends');
const lamp = cut('  function lampLightPatch(shader, worldExpr, mode) {', '  // ---- the realism pass: the ground') + cut('  function lampLightPatchReal(shader, worldExpr, mode) {', '  function surfTexPatch(shader, opt) {');
const cloud = cut('  function cloudShadowPatch(shader, worldExpr) {', '  function wxSurfacePatch(shader) {');
const ART = JSON.parse(fs.readFileSync(path.join(ROOT, 'people_art.json'), 'utf8'));
function make(OPT) {
  const made = [], asked = [], added = [], log = { init: 0, fills: 0 };
  const THREE = new Proxy(REALTHREE, { get(t, k) { const v = t[k]; return typeof v === 'function' && /^[A-Z]/.test(String(k)) ? new Proxy(v, { construct(T, a) { made.push(k); return new T(...a); } }) : v; } });
  const body = `
const PEOPLE_ON = !!OPT.on, isTouch = !!OPT.touch, REAL = OPT.real !== false, location = { search: OPT.search || '' };
const PEOPLE = { cap: isTouch ? 150 : 600, stride: 8, ready: false }, PEOPLE_ART = OPT.art === undefined ? ART : OPT.art, PERF = { ready: undefined };
const performance = { now: () => 0 }, clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const renderer = { info: { programs: [] }, domElement: { height: 900 }, capabilities: { isWebGL2: true } };
const camera = { position: { x: 0, y: 1.7, z: 0 } }, sunDir = { x: 1, y: 0.5, z: 0 };
const sunWUniform = { value: sunDir }, ZREV = { on: !!OPT.zrev }, VEH_SHADE_FOG = '\\nfloat shFog = 0.0;\\n#ifdef USE_FOG\\nshFog = fogFactor;\\n#endif\\n';
const vehShadowU = { uSunW: sunWUniform, uShadowA: { value: 0.6 }, uBlobA: { value: 0.5 }, uShadeOut: { value: 0 }, uCoreBox: { value: new REALTHREE.Vector4() } };
const vehBlobGeom = (l, w) => { const g = new REALTHREE.BufferGeometry(); g.userData.blob = [l, w]; return g; };
const vehShadowMaterial = (fade, blob, deck) => { const m = new REALTHREE.MeshBasicMaterial(); m.userData.veh = [fade, blob, deck]; return m; };
const groupCity = { add: (m) => added.push(m) };
let moonNoRecv = OPT.moonOff ? [] : null, trafficReady = true; const trafficRuns = [1];
const peopleInit = () => { log.init++; PEOPLE.ready = true; };
let ROWS = [];
const peopleFill = (out) => { log.fills++; for (let i = 0; i < ROWS.length; i++) out.set(ROWS[i], i * 8); return ROWS.length; };
const inCore = (x, z) => !!OPT.core, sidewalkAt = (x, z) => x > 1000;
const artSrc = (full, half) => { asked.push([full, half]); return isTouch && half ? half : full; };
const artImage = (s) => ({ then: (f) => { PENDING.push(() => f(OPT.noArt ? null : { width: OPT.imW || ART.atlas.w, height: OPT.imH || ART.atlas.h, src: s })); } });
const PENDING = [], anisoOf = (n) => n, freeTexOnUpload = (t) => t;
const lampMapU = { uLampMap: { value: null }, uLampBox: { value: null }, uLampOn: { value: 0 }, uLampFade: { value: null }, uLampNear: { value: null }, uLampNearBox: { value: null }, uLampNearFade: { value: null }, uLampReal: { value: null } };
const LAMP_SHOULDER = 0.5, LAMP_WX_DECL = 'uniform sampler2D uLampMap; uniform vec4 uLampBox;';
const cloudShU = { uCloudOff: {}, uCloudCov: {}, uCloudSh: {}, uCloudSlant: {} };
${lamp}
${cloud}
${draw}
return { PPL, PEOPLE, PERF, camera, sunDir, made, asked, added, log, PENDING, peopleStep, peopleCells, peopleCardPatch, peopleShadeMaterial, peopleDrawDbg, peopleTune, PEOPLE_SHARP, PEOPLE_SYM,
  rows: (r) => { ROWS = r; }, moon: () => moonNoRecv, has: { step: typeof peopleStep } };`;
  return new Function('OPT', 'ART', 'THREE', 'REALTHREE', 'made', 'asked', 'added', 'log', body)(OPT, ART, THREE, REALTHREE, made, asked, added, log);
}
// the page's frames after Ready: the make frame, the second warm frame, then the frames that fill
function warm(A) { A.PERF.ready = 1; A.peopleStep(0); A.peopleStep(16); }
function land(A) { while (A.PENDING.length) A.PENDING.shift()(); }
const cell = (fig, view, frame) => { const A = ART.atlas, V = ['front', 'back', 'side'].map((v) => ART.views.indexOf(v)), r = ART.figures[fig].cells[V[view]][frame]; return [r[0] / A.w, 1 - (r[1] + r[3]) / A.h, r[2] / A.w, r[3] / A.h]; };
const near = (a, b) => a.length === b.length && a.every((v, i) => Math.abs(v - b[i]) < 1e-5);
'''

OFF = r'''
const o = {};
{ const A = make({ on: false }); o.off = { made: A.made.slice(), added: A.added.length, state: A.PPL.made, tex: A.PPL.uTex.value, sharp: A.PEOPLE_SHARP }; }
{ const A = make({ on: true, search: '?people=1' }); A.peopleStep(0); A.peopleStep(16); o.early = { made: A.made.filter((k) => k !== 'Vector4'), added: A.added.length, init: A.log.init, fills: A.log.fills }; }
{ const A = make({ on: true, art: null }); A.PERF.ready = 1; A.peopleStep(0); o.noArt = { made: A.PPL.made, added: A.added.length }; }
{ const A = make({ on: true, search: '?people=1' }); A.PERF.ready = 1; A.peopleStep(0);
  const P = A.PPL, m = A.added;
  o.make = { n: m.length, names: m.map((q) => q.name), counts: m.map((q) => q.count), fade0: P.fade[0], init: A.log.init, fills: A.log.fills, asked: A.asked.length, cap: P.card.instanceMatrix.count,
    sameIM: m.every((q) => q.instanceMatrix === P.card.instanceMatrix), identity: Array.from(P.card.instanceMatrix.array.slice(16, 32)).join(),
    refl: m.map((q) => q.userData.reflK), cast: m.map((q) => q.castShadow), culled: m.map((q) => q.frustumCulled), depthMat: m.map((q) => !!q.customDepthMaterial), recv: m.map((q) => q.receiveShadow), order: m.map((q) => q.renderOrder),
    keys: m.map((q) => q.material.userData.veh ? q.material.userData.veh.join() : q.material.customProgramCacheKey()), blob: P.blob.geometry.userData.blob,
    mats: m.map((q) => [q.material.type, q.material.transparent, q.material.depthWrite, q.material.alphaTest, q.material.side === REALTHREE.FrontSide]), stencil: [P.shade.material.stencilWrite, P.shade.material.stencilRef, P.shade.material.stencilFunc === REALTHREE.NotEqualStencilFunc],
    streams: [] };
  for (const q of m) for (const k in q.geometry.attributes) { const a = q.geometry.attributes[k], arr = a.data ? a.data.array : a.array; o.make.streams.push([q.name, k, arr.constructor.name, a.itemSize, a.data ? a.data.stride : a.itemSize, !!(a.normalized)]); }
  o.make.streams.push(['People', 'instanceMatrix', P.card.instanceMatrix.array.constructor.name, 16, 16, false]);
  A.peopleStep(16); A.peopleStep(32); o.make.fills = A.log.fills; o.make.init2 = A.log.init; }
{ const A = make({ on: true, moonOff: true }); A.PERF.ready = 1; A.peopleStep(0); o.moon = { recv: A.added.map((q) => q.receiveShadow), listed: A.moon().map((q) => q.name) }; }
{ const A = make({ on: true, touch: true, search: '?people=sharp' }); A.PERF.ready = 1; A.peopleStep(0); o.touch = { recv: A.added.map((q) => q.receiveShadow), sharp: A.PEOPLE_SHARP, cap: A.PPL.card.instanceMatrix.count }; }
{ const A = make({ on: true, real: false }); A.PERF.ready = 1; A.peopleStep(0); o.plain = { names: A.added.map((q) => q.name) }; }
console.log(JSON.stringify(o));
'''

VIEW = r'''
const o = {};
const A = make({ on: true, search: '?people=1' }); warm(A);
const P = A.PPL, row = (x, z, hx, hz, fig, ph, fade, y) => [x, y || 0, z, hx, hz, fig, ph, fade === undefined ? 1 : fade];
const R = (deg) => [Math.sin(deg * Math.PI / 180), Math.cos(deg * Math.PI / 180)];   // a heading deg off the line to the eye, toward the viewer's right for a positive angle
// the eye at the origin; every walker 10 m north of it, so the line to the eye is +z and the viewer's right is +x
const H = [0, 30, 38.9, 45, 51.1, 60, 90, 120, 128.9, 135, 141.1, 150, 180, -90, -45, -120];
A.rows(H.map((d) => row(0, -10, R(d)[0], R(d)[1], 1, 0.3)));
A.peopleStep(32);
o.beforeArt = { count: P.card.count, vis: P.card.visible, asked: A.asked.slice(), loading: P.loading };
A.peopleStep(48); o.askedOnce = A.asked.length;
land(A); A.peopleStep(64);
o.atlas = P.atlas; o.count = [P.card.count, P.shade.count, P.blob.count]; o.vis = [P.card.visible, P.shade.visible, P.blob.visible]; o.cellPx = P.uPK.value.z;
const iv = P.iv, rd = (i, s) => Array.from(iv.slice(i * 16 + 4 + s * 4, i * 16 + 8 + s * 4)), mir = (c) => [c[0] + c[2], c[1], -c[2], c[3]];
const which = (r, fig) => { for (let v = 0; v < 3; v++) for (let f = 0; f < ART.frames; f++) { const c = cell(fig, v, f); if (near(r, c)) return 'FBS'[v] + f; if (near(r, mir(c))) return 'FBS'[v] + f + 'm'; } return '?'; };
o.views = H.map((d, i) => [d, which(rd(i, 0), 1), which(rd(i, 1), 1), +iv[i * 16 + 2].toFixed(3)]);
o.size = [iv[0], iv[1], ART.figures[1].tall];
// the step: figure 0 (p01, carries a tote: never mirrored) and figure 1 (p02), walking at the eye and away, by phase
const PH = [0.05, 0.17, 0.3, 0.42, 0.55, 0.67, 0.8, 0.92];   // one eighth of a cycle each: every frame of both steps
A.rows([].concat(...[0, 1, 2, 4].map((fig) => PH.map((ph) => row(0, -10, 0, 1, fig, ph))), PH.map((ph) => row(0, -10, 0, -1, 1, ph)), PH.map((ph) => row(0, -10, 1, 0, 1, ph))));
A.peopleStep(80);
o.step = [0, 1, 2, 4].map((fig, a) => PH.map((ph, b) => which(rd(a * 8 + b, 0), fig % 3)));
o.stepBack = PH.map((ph, b) => which(rd(32 + b, 0), 1)); o.stepSide = PH.map((ph, b) => which(rd(40 + b, 0), 1));
o.bob = PH.map((ph, b) => +iv[b * 16 + 3].toFixed(4));
// the sun stands east (sunDir.x 1): its view of a walker by the walker's heading, for the shadow
A.rows([[1, 0], [-1, 0], [0, 1], [0, -1]].map((h) => row(0, -10, h[0], h[1], 1, 0.05)).concat([[0, 1], [0, -1]].map((h) => row(0, -10, h[0], h[1], 1, 0.55))));
A.peopleStep(96);
o.sun = [0, 1, 2, 3, 4, 5].map((i) => which(rd(i, 2), 1));
// the place: the fill's ground and the lift (a sidewalk east of x 1000 in this harness), the fade, the count's streams
A.rows([row(5, -10, 1, 0, 0, 0.1, 0.5, 3), row(2000, -10, 1, 0, 0, 0.1, 1, 3), row(1000.2, -10, 1, 0, 0, 0.1, 1, 3)]);
A.peopleStep(112);
const me = P.card.instanceMatrix.array;
o.place = [[me[12], +me[13].toFixed(4), me[14]], +me[16 + 13].toFixed(4), +me[32 + 13].toFixed(4)]; o.up = [P.up0, P.up1]; o.fade = [P.fade[0], P.fade[1]];
o.ranges = [P.card.instanceMatrix.updateRange.count, P.ivb.updateRange.count, P.card.geometry.attributes.aCarFade.updateRange.count];
A.rows([]); A.peopleStep(128); o.empty = [P.card.count, P.card.visible, P.shade.visible, P.blob.visible];
// the hand-over's width and the cross-dissolve of the poses are the review's knobs
A.peopleTune({ hand: 2, xfade: 0.5 }); A.rows([row(0, -10, R(41)[0], R(41)[1], 1, 0.3), row(0, -10, 0, 1, 1, 0.22)]); A.peopleStep(144);
o.tuned = [which(rd(0, 1), 1), +iv[2].toFixed(3), which(rd(1, 0), 1), which(rd(1, 1), 1), iv[16 + 2] > 0 && iv[16 + 2] < 1];
// the art: asked once whatever the frames; a computer under ?people=sharp, a phone, and an answer that never comes
const S = make({ on: true, search: '?dev=1&people=sharp' }); warm(S); S.rows([row(0, -10, 0, 1, 0, 0.1)]); S.peopleStep(32); land(S);
const T = make({ on: true, touch: true, search: '?people=sharp' }); warm(T); T.rows([row(0, -10, 0, 1, 0, 0.1)]); T.peopleStep(32);
const N = make({ on: true, noArt: true }); warm(N); N.rows([row(0, -10, 0, 1, 0, 0.1)]); N.peopleStep(32); land(N); N.peopleStep(48); N.peopleStep(20000); N.peopleStep(40000);
o.art = { plain: A.asked, sharp: S.asked, sharpOn: S.PEOPLE_SHARP, touch: T.asked, touchSharp: T.PEOPLE_SHARP, lost: { asked: N.asked.length, failed: N.PPL.failed, count: N.PPL.card.count, atlas: N.PPL.atlas } };
o.dbg = Object.keys(A.peopleDrawDbg()).join();
console.log(JSON.stringify(o));
'''

PATCH = r'''
const o = {};
const count = (s, w) => s.split(w).length - 1;
for (const real of [true, false]) for (const zrev of [true, false]) {
  const A = make({ on: true, real, zrev }), L = REALTHREE.ShaderLib, tag = (real ? 'real' : 'plain') + (zrev ? '-zrev' : '-log');
  const c = { uniforms: {}, vertexShader: L.standard.vertexShader, fragmentShader: L.standard.fragmentShader }; A.peopleCardPatch(c);
  const m = A.peopleShadeMaterial(), s = { uniforms: {}, vertexShader: L.shadow.vertexShader, fragmentShader: L.shadow.fragmentShader }; m.onBeforeCompile(s);
  const samp = (t) => (t.match(/uniform\s+sampler\w+\s+[^;]+;/g) || []).reduce((n, d) => n + d.split(',').length, 0);
  o[tag] = {
    card: { v: ['attribute float aCarFade; attribute vec4 aPB; attribute vec4 aRA; attribute vec4 aRB;', 'vec3 pLP, pNrm; pCard(pLP, pNrm);\n#include <beginnormal_vertex>', '#include <defaultnormal_vertex>\ntransformedNormal = normalMatrix * pNrm;', '#include <begin_vertex>\ntransformed = pLP;', '#include <project_vertex>\nif (aCarFade <= 0.0) gl_Position = vec4(0.0, 0.0, -2.0, 1.0);'].map((w) => count(c.vertexShader, w)),
      f: ['uniform sampler2D tPeople; uniform vec4 uPL;', '#include <map_fragment>\n{ if (pK.y <= pBay(gl_FragCoord.xy)) discard;', 'float lk = uPL.x', 'float lk = 0.12', 'uniform float uLampOn;', 'float cloudShade('].map((w) => count(c.fragmentShader, w)),
      samplers: samp(c.fragmentShader) + samp(c.vertexShader) - samp(L.standard.fragmentShader) - samp(L.standard.vertexShader), uniforms: Object.keys(c.uniforms).sort().join(), depth: count(c.vertexShader + c.fragmentShader, 'gl_FragDepth') },
    shade: { v: ['#include <common>\nattribute float aCarFade; attribute vec4 aPB; attribute vec4 aRS;', 'vec4 mvPosition = viewMatrix * wpS;', '#include <logdepthbuf_vertex>\n#if defined(USE_LOGDEPTHBUF) && defined(USE_LOGDEPTHBUF_EXT)', 'gl_Position.z /= 0.9993;', 'worldPosition = wpS;', '#include <project_vertex>', 'pSF = aCarFade; vShXZ = wpS.xz;\nif (aCarFade <= 0.0) gl_Position = vec4(0.0, 0.0, -2.0, 1.0);'].map((w) => count(s.vertexShader, w)),
      f: ['uniform sampler2D tPeople;', 'if (pSF <= pBay(gl_FragCoord.xy)) discard;', 'if (pHull < 0.5) discard;', 'getShadowMask() ) );', 'gl_FragColor = vec4(0.0, 0.0, 0.0, uShadowA * bk * (1.0 - shFog));', '#include <logdepthbuf_fragment>'].map((w) => count(s.fragmentShader, w)),
      samplers: samp(s.fragmentShader) + samp(s.vertexShader) - samp(L.shadow.fragmentShader) - samp(L.shadow.vertexShader), uniforms: Object.keys(s.uniforms).sort().join(), depth: count(s.vertexShader + s.fragmentShader, 'gl_FragDepth'), key: m.customProgramCacheKey() } };
}
console.log(JSON.stringify(o));
'''


def have():
    return bool(shutil.which('node')) and all((ROOT / f).exists() for f in ('three.min.js', 'people_art.json'))


def node(script):
    r = subprocess.run(['node', '-e', HARNESS + script], capture_output=True, text=True, timeout=300, env=dict(os.environ, PP_ROOT=str(ROOT)))
    if r.returncode:
        raise AssertionError(r.stderr[-4000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def code_of(text):
    """The text without its whole-line comments and trailing comments (a '//' inside a string is left alone by the rule
    that a trailing comment starts at three spaces and two slashes, which is how this file writes them)."""
    out = []
    for ln in text.split('\n'):
        if ln.lstrip().startswith('//'):
            continue
        out.append(re.sub(r'\s{3}// .*$', '', ln))
    return '\n'.join(out)


def section():
    s = (ROOT / 'app.js').read_text(encoding='utf-8')
    return s, s[s.index(BANNER):s.index(END)]


class Text(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src, cls.sec = section()
        cls.code = code_of(cls.sec)

    def test_the_section_stands_once_after_the_traffic_step_and_out_of_the_core(self):
        s = self.src
        self.assertEqual((s.count(BANNER), s.count(END)), (1, 1))
        self.assertLess(s.index('  // ---- people on the sidewalks: the section ends'), s.index(BANNER))
        self.assertLess(s.index('  function trafficStep(now,dt) {'), s.index(BANNER))
        self.assertEqual(s[s.index(END):].split('\n', 3)[2], '  // ---------------------------------------------------------------- streetlights')
        # the core's own text still draws nothing (tests/test_people.py holds it); the flag reads 1 or sharp
        self.assertIn("  const PEOPLE_ON = /[?&]people=(?:1|sharp)\\b/.test(location.search) && !TIER2;", s)
        self.assertIn("  const PEOPLE_SHARP = PEOPLE_ON && !isTouch && /[?&]people=sharp\\b/.test(location.search);", self.sec)

    def test_nothing_runs_without_the_flag(self):
        s = self.src
        # one hook in the frame, after the traffic's, behind the flag; the make and the step have no other caller
        self.assertIn("    updateTraffic(now, dt);\n    if (PEOPLE_ON) peopleStep(now);", s)
        self.assertEqual(len(re.findall(r'\bpeopleStep\(', s)), 2)
        self.assertEqual(len(re.findall(r'\bpeopleDrawMake\(', s)), 2)
        self.assertEqual(len(re.findall(r'\bpeopleAtlasLoad\(', s)), 2)
        self.assertEqual(len(re.findall(r'\bpeopleShadeMaterial\(', s)), 2)
        self.assertEqual(len(re.findall(r'\bpeopleCardPatch\b', s)), 2)
        # the probe adds its drawing part only under the flag, and by typeof (the core also runs alone under Node)
        self.assertIn("    if (PEOPLE_ON && typeof peopleDrawDbg === 'function') o.draw = peopleDrawDbg();", s)
        # nothing of the drawing is made where the section is read: every THREE class it names is inside a function,
        # but for the three small vectors its uniforms hold
        top, inside = [], False
        for ln in self.code.split('\n'):
            if ln.startswith('  function '):
                inside = not ln.rstrip().endswith('}')
            elif inside:
                inside = ln != '  }'
            else:
                top.append(ln)
        top = '\n'.join(top)
        self.assertEqual(re.findall(r'new THREE\.(\w+)', top), ['Vector4', 'Vector4', 'Vector4'])
        self.assertNotRegex(top, r'\b(artImage|groupCity|renderer|peopleDrawMake|scene)\b')

    def test_the_two_programs_are_the_sections_own(self):
        s = self.src
        for key in ("'people-card'", "'people-shade'"):
            self.assertEqual(s.count("customProgramCacheKey = () => " + key), 1, key)
        self.assertEqual(len(re.findall(r"customProgramCacheKey = \(\) => 'people", s)), 2)
        # the shared patches are called, never rewritten: the section assigns to no shader chunk and defines none of them
        self.assertNotIn('ShaderChunk', self.code)
        for fn in ('lampLightPatch', 'lampLightPatchReal', 'cloudShadowPatch', 'treeArtPatch', 'vehShadowMaterial', 'carFadePatch', 'vehBlobGeom'):
            self.assertNotIn('function ' + fn, self.sec, fn)
            self.assertEqual(s.count('  function ' + fn + '('), 1, fn)
        self.assertIn("lampLightPatch(sh, wp, 'crown');", self.code)
        self.assertIn('cloudShadowPatch(sh, wp);', self.code)
        self.assertIn('vehShadowMaterial(true, true, false)', self.code)   # the contact shade is the traffic's own program
        # no program of the section writes the fragment's depth (tests/test_zbuf.py counts the page's)
        self.assertNotIn('gl_FragDepth', self.sec)

    def test_the_static_rules(self):
        c = self.code
        # 4-byte words only: the instance streams are Float32Arrays; the one byte array is the 1 by 1 texture's
        self.assertEqual(re.findall(r'new (\w+Array)\(', c), ['Float32Array', 'Float32Array', 'Float32Array', 'Float32Array', 'Uint8Array'])
        self.assertIn('new THREE.DataTexture(new Uint8Array(4), 1, 1)', c)
        for word in ('Int8Array', 'Uint16Array', 'Int16Array', 'Uint8ClampedArray', 'Uint32Array', ', true)'):
            self.assertNotIn(word, c.replace('vehShadowMaterial(true, true, false)', ''), word)
        self.assertIn('m.userData.reflK = 0;', c)
        self.assertNotRegex(c, r'castShadow\s*=\s*(true|!0|1)\b')
        self.assertNotIn('customDepthMaterial', c)
        self.assertNotIn('MeshDepthMaterial', c)
        # no tap, no pin: nothing of the picking or the pins is named
        for word in ('pinMesh', 'pinTexture', 'bldgPick', 'pickOccluded', 'addEventListener', 'vehinfo'):
            self.assertNotIn(word, c, word)
        # the art: one request, the full or the sharp picture with the record's half beside it
        self.assertEqual(len(re.findall(r'\bartImage\(', c)), 2)
        self.assertIn('    (PEOPLE_SHARP ? artImage(artSrc(A.imgSharp, A.imgHalf)) : artImage(artSrc(A.img, A.imgHalf))).then((im) => {', c)
        self.assertIn('t.premultiplyAlpha = true;', c)

    def test_no_dashes_or_middots(self):
        self.assertNotIn('—', self.sec)
        self.assertNotIn('·', self.sec)

    def test_the_skill_says_how_to_hold_them_still(self):
        skill = (ROOT.parent / '.claude' / 'skills' / 'philly3d-capture' / 'SKILL.md').read_text(encoding='utf-8')
        for word in ('?people=1', '__dbg.people(false)', '__dbg.peopleAt(t)'):
            self.assertTrue(word in skill, word)


@unittest.skipUnless(have(), 'needs node, three.min.js and people_art.json')
class Made(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = node(OFF)

    def test_nothing_without_the_flag(self):
        t = self.o['off']
        self.assertEqual(sorted(t['made']), ['Vector4', 'Vector4', 'Vector4'])
        self.assertEqual((t['added'], t['state'], t['tex'], t['sharp']), (0, False, None, False))

    def test_nothing_before_ready_and_nothing_without_the_art(self):
        self.assertEqual(self.o['early'], {'made': [], 'added': 0, 'init': 0, 'fills': 0})
        self.assertEqual(self.o['noArt'], {'made': False, 'added': 0})

    def test_the_frame_after_ready_makes_three_meshes_and_one_collapsed_instance(self):
        m = self.o['make']
        self.assertEqual(m['names'], ['People', 'People shadows', 'People contact'])
        self.assertEqual(m['counts'], [1, 1, 1])
        self.assertEqual(m['fade0'], 0)                      # nobody: the vertex shader clips it, the draw links the programs
        self.assertEqual((m['init'], m['init2'], m['asked']), (1, 1, 0))   # peopleInit beside the warm-up, once; no picture yet
        self.assertEqual(m['fills'], 1)                      # the fill runs only once the warm frames are drawn
        self.assertEqual(m['cap'], 600)
        self.assertTrue(m['sameIM'])
        self.assertEqual(m['identity'], '1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1')
        self.assertEqual(m['keys'], ['people-card', 'people-shade', 'true,true,false'])
        self.assertEqual(m['order'], [0, 2, 1])
        self.assertEqual(m['mats'][0], ['MeshStandardMaterial', False, True, 0.5, True])
        self.assertEqual(m['mats'][1][:3], ['ShadowMaterial', True, False])
        self.assertEqual(m['stencil'], [True, 1, True])

    def test_the_rules_on_every_mesh(self):
        m = self.o['make']
        self.assertEqual(m['refl'], [0, 0, 0])
        self.assertEqual(m['cast'], [False, False, False])
        self.assertEqual(m['culled'], [False, False, False])
        self.assertEqual(m['depthMat'], [False, False, False])
        self.assertEqual(m['recv'], [True, True, False])     # a computer: the card and its shadow read the sun's map
        # every stream the section adds is 32-bit floats on a stride that is a multiple of four bytes, none normalised
        mine = [s for s in m['streams'] if s[1] not in ('position', 'normal')]
        self.assertEqual(sorted(set(s[1] for s in mine)), ['aCarFade', 'aPB', 'aRA', 'aRB', 'aRS', 'instanceMatrix'])
        for name, key, kind, size, stride, norm in m['streams']:
            self.assertEqual(kind, 'Float32Array', (name, key))
            self.assertFalse(norm, (name, key))
        self.assertEqual(sorted(set((s[1], s[3], s[4]) for s in mine)), [('aCarFade', 1, 1), ('aPB', 4, 16), ('aRA', 4, 16), ('aRB', 4, 16), ('aRS', 4, 16), ('instanceMatrix', 16, 16)])

    def test_the_receive_roles(self):
        # made while the receivers are off (after dusk on a phone, under a closed deck): none receives, and those that
        # would join the list they come back from
        self.assertEqual(self.o['moon'], {'recv': [False, False, False], 'listed': ['People', 'People shadows']})
        # a phone: the card does not read the map; never the sharp picture, and its own cap
        self.assertEqual(self.o['touch'], {'recv': [False, True, False], 'sharp': False, 'cap': 150})
        # ?real=0: the card alone (the shades are the realistic look's, as the vehicles' are)
        self.assertEqual(self.o['plain'], {'names': ['People']})


@unittest.skipUnless(have(), 'needs node, three.min.js and people_art.json')
class View(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = node(VIEW)
        cls.art = json.loads((ROOT / 'people_art.json').read_text())

    def test_nobody_is_drawn_before_the_picture_and_it_is_asked_for_once(self):
        o, A = self.o, self.art['atlas']
        self.assertEqual(o['beforeArt'], {'count': 0, 'vis': False, 'asked': [[A['img'], A['imgHalf']]], 'loading': True})
        self.assertEqual(o['askedOnce'], 1)
        self.assertEqual(o['count'], [16, 16, 16])
        self.assertEqual(o['vis'], [True, True, True])
        self.assertEqual(o['atlas'], {'w': A['w'], 'h': A['h'], 'bytes': round(A['w'] * A['h'] * 4 * 4 / 3), 'sharp': False, 'half': False})
        self.assertEqual(o['cellPx'], 256)
        self.assertEqual(o['empty'], [0, False, False, False])

    def test_the_view_by_the_heading_against_the_eye(self):
        got = {d: (a, b, k) for d, a, b, k in self.o['views']}
        # phase 0.3 is the passing pose (frame 2 of four); F front, B back, S side, m mirrored
        for d in (0, 30, 38.9):
            self.assertEqual(got[d], ('F2', 'F2', 0), d)
        for d in (51.1, 60, 90, 120, 128.9):
            self.assertEqual(got[d], ('S2', 'S2', 0), d)       # toward the viewer's right: the picture as drawn
        for d in (141.1, 150, 180):
            self.assertEqual(got[d], ('B2', 'B2', 0), d)
        self.assertEqual(got[-90], ('S2m', 'S2m', 0))          # toward the viewer's left: mirrored
        self.assertEqual(got[-120], ('S2m', 'S2m', 0))
        # on a line both pictures ride the instance, half and half
        self.assertEqual(got[45], ('F2', 'S2', 0.5))
        self.assertEqual(got[135], ('S2', 'B2', 0.5))
        self.assertEqual(got[-45], ('F2', 'S2m', 0.5))
        # the card's size is the figure's cell: its height the manifest's tall, its width by the cell's shape
        w, h, tall = self.o['size']
        self.assertAlmostEqual(h, tall, places=5)
        self.assertAlmostEqual(w, tall * 128 / 256, places=5)

    def test_the_step(self):
        s = self.o['step']
        # Round 237: a step is four frames (contact, down, passing, up), eight a cycle
        self.assertEqual(s[0], ['F0', 'F1', 'F2', 'F3', 'F0', 'F1', 'F2', 'F3'])           # p01 carries a tote on one shoulder: never mirrored
        self.assertEqual(s[1], ['F0', 'F1', 'F2', 'F3', 'F0m', 'F1m', 'F2m', 'F3m'])   # p02: the second step is the other leg's
        self.assertEqual(s[2], s[1])                           # p03
        self.assertEqual(s[3], s[1])                           # figure 4 of the fill's twelve is figure 1 of the three here
        self.assertEqual(self.o['stepBack'], ['B0', 'B1', 'B2', 'B3', 'B0m', 'B1m', 'B2m', 'B3m'])
        self.assertEqual(self.o['stepSide'], ['S0', 'S1', 'S2', 'S3'] * 2)   # a side is mirrored by its way alone

    def test_the_bob_is_lowest_at_the_down_and_highest_at_the_up(self):
        # the shader stretches the card by 0.5 - 0.5 cos(4 pi (w - 0.125)) of the bob, w the phase it is handed: lowest at
        # w 0.125, highest at 0.375. With four frames the page hands the phase a sixteenth early
        import math
        lift = [0.5 - 0.5 * math.cos(4 * math.pi * (w - 0.125)) for w in self.o['bob']]
        self.assertLess(max(lift[1], lift[5]), 0.1)            # the down (0.17, 0.67)
        self.assertGreater(min(lift[3], lift[7]), 0.9)         # the up (0.42, 0.92)

    def test_the_suns_view_for_the_shadow(self):
        # the sun stands east: a walker heading east shows it the front, west the back; north and south a side, and
        # from the side always the passing pose (a stride's feet would stand apart from the card's own)
        self.assertEqual(self.o['sun'], ['F0', 'B0', 'S2m', 'S2', 'S2m', 'S2'])

    def test_the_place_the_lift_and_the_fade(self):
        o = self.o
        up0, up1 = o['up']
        self.assertEqual(o['place'][0], [5, round(3 + up0, 4), -10])          # bare ground
        self.assertAlmostEqual(o['place'][1], 3 + up1, places=4)              # on a sidewalk
        self.assertAlmostEqual(o['place'][2], 3 + up0 + (up1 - up0) * 2 / 3, places=4)   # a ring's edge, a third at a time
        self.assertEqual(o['fade'], [0.5, 1])
        self.assertEqual(o['ranges'], [48, 48, 3])             # only the walkers drawn go up

    def test_the_knobs(self):
        b, k, a1, b1, mid = self.o['tuned']
        self.assertEqual(b, 'F2')                              # 41 degrees is outside a 2 degree hand-over
        self.assertEqual(k, 0)
        self.assertEqual((a1, b1, mid), ('F1', 'F2', True))    # the tail of the down dissolving into the passing pose

    def test_the_art(self):
        A, a = self.art['atlas'], self.o['art']
        self.assertEqual(a['plain'], [[A['img'], A['imgHalf']]])
        self.assertEqual((a['sharp'], a['sharpOn']), ([[A['imgSharp'], A['imgHalf']]], True))
        self.assertEqual((a['touch'], a['touchSharp']), ([[A['img'], A['imgHalf']]], False))   # artSrc hands a phone the half
        # a picture that never comes: nobody drawn, asked again only after the wait
        self.assertEqual(a['lost'], {'asked': 2, 'failed': 1, 'count': 0, 'atlas': None})
        for k in ('made', 'drawn', 'atlas', 'programs', 'warm', 'shades'):
            self.assertIn(k, self.o['dbg'].split(','))


@unittest.skipUnless(have(), 'needs node and three.min.js')
class Patch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = node(PATCH)

    def test_every_anchor_is_found_in_r149s_shaders(self):
        for tag, t in self.o.items():
            self.assertEqual(t['card']['v'], [1, 1, 1, 1, 1], tag)
            # the lamps' patch ran, and its crown share is the card's own uniform in this program's text alone
            self.assertEqual(t['card']['f'], [1, 1, 1, 0, 1, 1], tag)
            zrev = tag.endswith('zrev')
            self.assertEqual(t['shade']['v'], [1, 1, 1, 1 if zrev else 0, 1, 0, 1], tag)
            self.assertEqual(t['shade']['f'], [1, 1, 1, 0, 1, 1], tag)
            self.assertEqual(t['shade']['key'], 'people-shade', tag)
            self.assertEqual((t['card']['depth'], t['shade']['depth']), (0, 0), tag)

    def test_the_samplers(self):
        # what the patches add to r149's own text: the atlas, and the lamps' one map (two under the realistic look). r149 adds the
        # lights' shadow maps (two here: the sun's and the far map's) and the scene's environment at compile time, so a
        # card reads six units at most and its shadow three: far under the sixteen a program has
        self.assertEqual(self.o['real-zrev']['card']['samplers'], 3)
        self.assertEqual(self.o['plain-zrev']['card']['samplers'], 2)
        for tag, t in self.o.items():
            self.assertEqual(t['shade']['samplers'], 1, tag)
            self.assertLessEqual(t['card']['samplers'] + 3, 8, tag)
        self.assertEqual(self.o['real-log']['card']['uniforms'], 'tPeople,uCloudCov,uCloudOff,uCloudSh,uCloudSlant,uLampBox,uLampFade,uLampMap,uLampNear,uLampNearBox,uLampNearFade,uLampOn,uLampReal,uPK,uPL')
        self.assertEqual(self.o['real-log']['shade']['uniforms'], 'tPeople,uCoreBox,uPS,uShadeOut,uShadowA,uSunW')


if __name__ == '__main__':
    unittest.main()
