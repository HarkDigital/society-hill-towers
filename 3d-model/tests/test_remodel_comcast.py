"""Round 195 (Mike: "Remodel Liberty One, Liberty 2, The stadiums/arena, both Comcast towers, ..."): the two Comcast towers
remodelled under the realistic look (CMR). The Comcast Center's end wings lean in as they rise (the faceted obelisk) and its
east wing, 39 m from its spec's point, is its glass again (it was drawn as an unresearched tower in a precast skin), its crown
is an open cage of low-iron glass in a bold frame from the lintel (the wings' tops) to the top round a grey enclosure, its
winter garden on the clear system; the CTC's bars stop at 190 (north) and 142 m (south), its spine is a glazed column up the
middle on the tower's own glass between silver and dark grey cladding, its lantern pale sea-green glass on the column, lit at
night as the blade was (crownPanels, slots 100 up) behind the old blade's dark bars every 1.6 m, its Z braces on the bars'
east and west ends (not the broad faces), a fascia every three floors, the top floors glazed to the roof, the louvred podium
and its silver columns (the blue of the 2017 photographs was protective film), the lobby and its canopy. The remodel's trim
has a near and a far level (cmrStep), its cladding one art strip (COMCAST_ART) whose numbers the vertex shader picks (WebGL 1
indexes a uniform array in a fragment shader only by a constant), and ?real=0 and ?comcast=0 build Round 194's towers."""
import re
import base64
import json
from pathlib import Path
import shutil
import struct
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_gated_by_the_realistic_look_and_its_own_flag(self):
        s = self.s
        self.assertIn("const CMR_ON = REAL && !/[?&]comcast=0\\b/.test(location.search);", s)
        self.assertIn('const CMRW = CMR_ON ? {', s)
        # every change to the old paths is behind it: the bars' heights, the broad-face braces, the CTC's old trim, the
        # wings, the spine, the crown's deck and its roof panel, the blade
        self.assertIn('if (style === 24 && h > 135 && h < 150 && t === 10 && !(CMR_ON && spec && cz > spec.z)) {\n        h = CMR_ON ? CTC_DIMS.nBar : 213.5;', s)
        self.assertIn('if (style === 24 && hTop > 130 && Math.abs(signedArea(poly)) > 650 && !CMR_ON) {', s)
        self.assertIn('if (spec && style!==25 && !(CMR_ON && style === 24)) crownTrim.push(...landmarkFacadeDetails(spec, poly, base, hTop, mh));', s)
        self.assertIn('const wing = CMR_ON && h < spec.h - 5 ? cmrWingOf(poly, cp) : null;', s)
        self.assertIn('} else if (CMR_ON && style === 24 && h > 300 && Math.abs(signedArea(poly)) < 200) CMRW.ctcSpine = { poly, base };', s)
        self.assertIn('for(const part of cp.pieces)if(!(CMR_ON&&part===cp.crown))appendBuilding(glass,part.poly,th.base+part.y0,th.base+part.y1,', s)
        self.assertIn('const ri = CMR_ON ? CC_DIMS.inset : 0;', s)
        self.assertIn('(CMR_ON?encTop:th.base+cp.top)+.12', s)
        self.assertIn('if(!(CMR_ON&&piece===cp.crown))for(let y=piece.y0;', s)
        self.assertIn('if (CMR_ON && cmrCtcBuild(th, lit, themed, tslot)) break;', s)
        self.assertIn('if (!spec && CMRW && CMRW.cc && h > 45 && Math.hypot(cx - CMRW.cc.x, cz - CMRW.cc.z) < 45) spec = CMRW.cc;', s)
        self.assertIn('if (CMRW) cmrFinish(CMRW);', s)
        self.assertIn('cmrStep();   // Round 195', s)

    def test_the_glass_stays_on_its_systems(self):
        s = self.s
        # the wings on the curtain wall's own chunk in the tower's glass; the winter garden on the clear system, the podium
        # in the CTC's
        w = cut(s, '          if (wing) {', '          else for(const part of (CMR_ON ? cmrNorthSlot(')
        self.assertIn('cmrGlassQuad(chG, q.p, q.n, c, style, base, gFh, q.facade)', w)
        low = cut(s, '        const low = cmrLow(cx, cz, h, t);', '        appendBuilding(getGlassChunk(cx, cz), poly, mh > 0 ? base + mh : base - 1.0, base + hTop, c, 3, base, null, lowFh);')
        self.assertIn("if (low === 'winter') { CMRW.winter++; if (GLASS_ON) lowFh = glassFh(5); }", low)
        self.assertIn("glassTowerBody(CMRW.ctc, c); lowFh = glassFh(1);", low)
        # the spine's glazed column on the CTC's own system, between its two flanks of cladding
        b = cut(s, '      const cmrCtcBuild = (th, lit, themed, tslot) => {', '      let nCrowns = 0;')
        self.assertIn('for (const [va, vb] of [[sv0, svc - hw], [svc + hw, sv1]]) {', b)
        self.assertIn('if (GLASS_ON) glassTowerBody(W.ctc, c);', b)
        self.assertIn('appendBuilding(getGlassChunk(th.cx, th.cz), [P(su0 + rec, svc - hw), P(su1, svc - hw), P(su1, svc + hw), P(su0 + rec, svc + hw)], base - 1, base + D.overrun, c, 24, base, null, GLASS_ON ? glassFh(1) : undefined);', b)
        # no new depth writes, no new samplers beyond the cladding's array
        block = cut(s, '  // ---- the two Comcast towers remodelled', '  // buildings with researched custom models skip the generic extruder;')
        self.assertNotIn('gl_FragDepth', block)
        self.assertEqual(block.count('sampler2DArray'), 1)

    def test_the_review_fixes(self):
        s = self.s
        b = cut(s, '      const cmrCtcBuild = (th, lit, themed, tslot) => {', '      let nCrowns = 0;')
        # the columns before the north podium in the fins' silver, no blue anywhere in the palette
        self.assertNotIn('CMR_C.blue', s)
        self.assertNotIn('blue: cmrCol', s)
        self.assertIn("A.beam([x, base - 0.5, z], [x, base + 22.5, z], 0.9, 0.9, [nx, 0, nz], CMR_C.fin, A === W.far)", b)
        # no louvre cap under the main roof (the bars keep theirs)
        self.assertNotIn('cmrRibbon(W.tex, main.poly', b)
        self.assertIn('cmrRibbon(W.tex, p.poly, base + p.top - 4.42, 8.84, 0.08, CMR_C.louvre, 1);', b)
        # the spine's silver brought down from the 0.78 that read stark white, the lantern glass well under the frosted 0.8
        pal = cut(s, '      const CMR_C = {', '      // a band of outer faces')
        sp = re.search(r'spine: cmrCol\(([\d.]+), ([\d.]+), ([\d.]+)\)', pal)
        self.assertTrue(sp and max(float(v) for v in sp.groups()) <= 0.62, pal)
        ln = re.search(r'lantern: cmrCol\(([\d.]+), ([\d.]+), ([\d.]+)\)', pal)
        self.assertTrue(ln and max(float(v) for v in ln.groups()) <= 0.5 and float(ln.group(2)) > float(ln.group(1)), pal)
        # the overrun as wide as the spine, from its east end over the roof
        self.assertIn('W.tex.prism([P(su1 - 0.2, sv0 - 0.3), P(su0 + 22, sv0 - 0.3), P(su0 + 22, sv1 + 0.3), P(su1 - 0.2, sv1 + 0.3)]', b)
        # the cage: from the lintel to the plan's top round the enclosure, no tanks
        cc = cut(s, '      const cmrCcCrown = (th, cp) => {', '      let nCrowns = 0;')
        self.assertIn('y0 = cp.lintel, y1 = cp.top;', cc)
        self.assertIn('const enc = insetRing(ring, CC_DIMS.inset), et = b + y1 - CC_DIMS.encGap;', cc)
        self.assertNotIn('CMR_C.concrete);\n        }', cc)
        self.assertNotIn('deck', cut(s, '  const CC_DIMS =', '\n'))

    def test_no_dynamic_uniform_index_in_a_fragment_shader(self):
        # WebGL 1 (GLSL ES 1.00, appendix A) allows a fragment shader only constant indexes into a uniform array: the
        # first cladding read uCmrRM[li] there, failed the link, and the CTC drew with no spine, overrun or lantern. The
        # layer's numbers are picked in the vertex shader, which may index by anything, and handed down as varyings
        s = self.s
        tex = cut(s, '  function cmrTexMat() {', '  // the strip, asked for once the cladding is laid')
        frag = cut(tex, 'sh.fragmentShader = ', "m.customProgramCacheKey")
        vert = cut(tex, 'sh.vertexShader = ', 'sh.fragmentShader = ')
        scr = cut(s, '  function cmrScreenMat() {', '  // buildings with researched custom models skip the generic extruder;')
        for f in (frag, cut(scr, 'sh.fragmentShader = ', 'm.customProgramCacheKey')):
            glsl = re.sub(r'\$\{[^}]*\}', '0', f)
            self.assertIsNone(re.search(r'\b[A-Za-z_]\w*\s*\[\s*[A-Za-z_]', glsl), glsl)   # no array indexed by a name
            self.assertNotIn('uniform vec2 uCmrRM', glsl)
        self.assertIn('vCmrRM = uCmrRM[li]; vCmrUv = uv / uCmrTile[li]; vCmrMean = max(uCmrMean[li], vec3(0.01));', vert)
        self.assertIn('roughnessFactor = vCmrRM.x;', frag)
        self.assertIn('metalnessFactor = vCmrRM.y;', frag)

    def test_the_night_lights_are_kept(self):
        s = self.s
        b = cut(s, '      const cmrCtcBuild = (th, lit, themed, tslot) => {', '      let nCrowns = 0;')
        # the lantern lit as the blade was: crownPanels slices with slots 100 up its height, the same gain and house colour
        self.assertIn("crownPanels.push({ geom: box(ax2.hl * 2 + 0.2, dh + 0.002, ax2.hs * 2 + 0.2, ob.cx, base + D.overrun + y + dh / 2, ob.cz, ry2), color: new THREE.Color(0x8a9da6), lit: gl, mix: 1, slot: 100 + (y + dh / 2) / hb, gain: 0.9, style: 3 });", b)
        self.assertIn('const gl = lit ? lit.clone().multiplyScalar(0.55) : new THREE.Color(0x8fa0ad);', b)
        # and in front of the slices the old themed blade's dark bars every 1.6 m (Round 85's ladder), on the same
        # night-only mesh at next to no gain (mergeColored reads a gain of 0 as 1, which drew them as light lines)
        self.assertIn('ladder: 1.6', s)
        self.assertIn("for (let y = D.ladder; y < hb - 0.3; y += D.ladder, W.ladder++) crownPanels.push({ geom: box(ax2.hl * 2 + 0.32, 0.10, ax2.hs * 2 + 0.32, ob.cx, ly0 + y, ob.cz, ry2), color: new THREE.Color(0x50616b), lit: new THREE.Color(0), mix: 1, slot: 100 + y / hb, gain: 0.001, style: 3 });", b)
        self.assertIn('tg.fill(parts[pi].gain || 1, o, o + vc)', s)
        # the Comcast Center's crown panels untouched (slots 200 up, the Phillies' solid red)
        n = cut(s, "          case 'comcast-notch': {", "          case 'notch':")
        self.assertIn('sl=200+(y+dh/2-part.y0)/(part.y1-part.y0);', n)
        self.assertIn('slot:200.999', n)

    def test_the_trim_has_two_levels(self):
        s = self.s
        st = cut(s, '  function cmrStep() {', '  // the cladding: the CTC')
        self.assertIn("if (CMR.lod === 'near' && d > CMR_FAR + 100) CMR.lod = 'far';", st)
        self.assertIn("else if (CMR.lod === 'far' && d < CMR_FAR - 100) CMR.lod = 'near';", st)
        f = cut(s, '  function cmrFinish(W) {', '  // the trim\'s level by')
        for k in ('freeOnUpload(g);', 'vdepthNoteOverlay(g);', 'CMR.near = mk(W.near, trimMat, true);', 'CMR.far = mk(W.far, trimMat, false);', 'CMR.far.visible = false;', 'if (CMR.tex) cmrArtLoad();'):
            self.assertIn(k, f)

    def test_the_art(self):
        man = json.loads((ROOT / 'comcast_art.json').read_text())
        self.assertEqual([q['id'] for q in man['layers']], ['spine', 'louvre', 'lantern', 'soffit', 'panel'])
        for k in ('strip', 'stripHalf'):
            self.assertTrue((ROOT / man[k]).exists(), man[k])
            self.assertTrue(man[k].startswith('art/comcast/'))
        from PIL import Image
        with Image.open(ROOT / man['strip']) as im, Image.open(ROOT / man['stripHalf']) as half:
            self.assertEqual(im.size, (man['size'], man['size'] * 5))
            self.assertEqual(half.size, (man['size'] // 2, man['size'] // 2 * 5))
            self.assertEqual(im.mode, 'RGB')   # opaque, never RGBA
        for q in man['layers']:
            self.assertEqual(len(q['tile']), 2)
            self.assertTrue(all(0 < v < 1 for v in q['mean']), q)
        # the lantern's glazing (the review: the frosted white with its X read as an opaque white post): sea-green, under
        # the old layer's 0.80, laid at 1.52 by 2.21 m a pane
        lan = man['layers'][2]
        self.assertEqual(lan['tile'], [6.08, 8.84])
        self.assertLess(max(lan['mean']), 0.6)
        self.assertGreater(lan['mean'][1], lan['mean'][0])
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("COMCAST_ART", text_of("comcast_art.json", "null"))', b)
        self.assertIn('"comcast_art.json"', b[b.index('for name in ("tree_art.json"'):b.index('    if (ROOT / name).exists():')])   # in build.py's art file list
        s = (ROOT / 'app.js').read_text()
        load = cut(s, '  function cmrArtLoad() {', '  // the Comcast Center\'s open crown')
        self.assertIn('artImage(artSrc(CMR_ART.strip, CMR_ART.stripHalf))', load)
        self.assertIn('CMR_U.uCmrArt.value = freeTexOnUpload(t);', load)


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class Geometry(unittest.TestCase):
    """The remodel's pure builders run on the real OSM parts (wide.b64) and on a synthetic frame."""
    @classmethod
    def setUpClass(cls):
        s = (ROOT / 'app.js').read_text()
        helpers = '\n'.join([
            cut(s, '  function signedArea(', '  function pointInPoly('),
            cut(s, '  function orientedBox(', '\n  function '),
            cut(s, '  function obbAxis(', '  function obbEnd('),
            cut(s, '  function pointInPoly(', '  function polyCentroid('),
            cut(s, '  function comcastCrownPlan(', '  function crownBandIndex('),
            cut(s, '  const CC_DIMS =', '  const CMR_FAR'),
            cut(s, '  function cmrBraces(', '  // the remodel\'s meshes and what'),
        ])
        blob = base64.b64decode((ROOT / 'wide.b64').read_text())
        hdr = struct.unpack_from('<4i', blob)
        words = struct.unpack_from('<%dh' % ((len(blob) - 16) // 2), blob, 16)
        k, parts = 0, []
        for _ in range(hdr[1]):
            n, h = words[k], words[k + 1] / 5
            k += 6
            poly = [[words[k + j * 2] / 5, words[k + j * 2 + 1] / 5] for j in range(n)]
            k += n * 2
            x = sum(p[0] for p in poly) / n; z = sum(p[1] for p in poly) / n
            if abs(x + 2028) < 40 and abs(z + 1031) < 40 and h > 45:
                parts.append({'poly': poly, 'h': h})
        script = 'const THREE=require(' + json.dumps(str(ROOT / 'three.min.js')) + ');\nconst PARTS=' + json.dumps(parts) + ';\n' + helpers + r'''
const out={};
const core=PARTS.reduce((a,b)=>a.h>b.h?a:b),cp=comcastCrownPlan(core.poly,297);
out.parts=PARTS.length;
out.wings=PARTS.map(p=>cmrWingOf(p.poly,cp)).filter(Boolean).map(w=>({depth:Math.abs(w.uo-w.ui),width:w.v1-w.v0,out:Math.sign(w.uo-w.ui)}));
// a wedge on the real frame: outward normals, the outer face leaning in, d1 deep at the top
const F={P:cp.P,ax:cp.a.ax,az:cp.a.az,px:cp.a.px,pz:cp.a.pz},w=cmrWingOf(PARTS.find(p=>cmrWingOf(p.poly,cp)).poly,cp);
const q=cmrWedge(F,w.ui,w.uo,w.v0,w.v1,0,269.6,1.0);
const cen=cp.P((w.ui+w.uo)/2,(w.v0+w.v1)/2);
out.wedge=q.map(f=>{const c=[0,1,2].map(i=>f.p.reduce((s,p)=>s+p[i],0)/4);const d=[c[0]-cen[0],c[1]-134.8,c[2]-cen[1]];return {out:d[0]*f.n[0]+d[1]*f.n[1]*0+d[2]*f.n[2]>0||f.cap===true,ny:f.n[1],facade:f.facade};});
const top=q[0].p[2],bot=q[0].p[1],u=(p)=>(p[0]-cp.ob.cx)*cp.a.ax+(p[2]-cp.ob.cz)*cp.a.az;
out.lean={bottom:Math.abs(u(bot)-w.ui),top:Math.abs(u(top)-w.ui)};
// the braces: per module a horizontal across the wall and a diagonal from its outer end up to the next one's inner end
const br=cmrBraces([0,0],[15,0],0,1,26.52,132.6,13.26,0.35);
// the north slot: the north wing's middle piece over the slot's band split into its two sides round a 13 m gap
const pcs=[];for(const p of PARTS)if(p!==core&&!cmrWingOf(p.poly,cp))pcs.push(...comcastFacadePieces(p.poly,-1,Math.min(p.h,271),cp));
const cut2=cmrNorthSlot(pcs,cp),slotted=cut2.filter(p=>p.slot);
const solid=(u,v,y)=>cut2.some(p=>y>p.y0+.01&&y<p.y1-.01&&pointInPoly(...cp.P(u,v),p.poly));
out.slot={n:slotted.length,depth:slotted.length?slotted[0].slot:0,open:!solid(0,-cp.d-1,251),above:solid(0,-cp.d-1,258),beside:solid(8,-cp.d-1,251),below:solid(0,-cp.d-1,240)};
out.braces={n:br.length,h:br.filter(m=>m[1]===m[4]).length,d:br.filter(m=>m[1]!==m[4]).every(m=>m[0]===0&&m[3]===15&&m[4]>m[1]),off:br.every(m=>m[2]===0.35&&m[5]===0.35)};
// the accumulator winds every quad to its normal; a beam is ten triangles near and two far
const A=cmrAcc(true);
A.quad([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],[0,0,1],{r:1,g:1,b:1});A.quad([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],[0,0,-1],{r:1,g:1,b:1});
let wound=true;for(let t=0;t<2;t++){const p=A.pos.slice(t*18,t*18+9),n=A.nor.slice(t*18,t*18+3);const e1=[p[3]-p[0],p[4]-p[1],p[5]-p[2]],e2=[p[6]-p[0],p[7]-p[1],p[8]-p[2]];wound&&=(e1[1]*e2[2]-e1[2]*e2[1])*n[0]+(e1[2]*e2[0]-e1[0]*e2[2])*n[1]+(e1[0]*e2[1]-e1[1]*e2[0])*n[2]>0;}
const B=cmrAcc(),Cf=cmrAcc();B.beam([0,0,0],[0,10,0],0.6,0.45,[1,0,0],{r:1,g:1,b:1});Cf.beam([0,0,0],[0,10,0],0.6,0.45,[1,0,0],{r:1,g:1,b:1},true);
const P=cmrAcc(true);P.prism([[0,0],[10,0],[10,8],[0,8]],300,342,{r:1,g:1,b:1},2,false);
const wuv=P.uv.slice(0,48);   // the four walls' six corners each (the top's uv is its plan)
out.acc={wound,beam:B.tris,flat:Cf.tris,prism:P.tris,uMax:Math.max(...wuv.filter((v,i)=>i%2===0)),vMin:Math.min(...wuv.filter((v,i)=>i%2===1)),vMax:Math.max(...wuv.filter((v,i)=>i%2===1))};
// the cage: comcastCrownPlan's lintel the cage's depth under the top
out.cage={depth:cp.top-cp.lintel,cage:CC_DIMS.cage};
const g=B.geometry();out.attrs=Object.keys(g.attributes).sort();out.released=B.pos===null;
console.log(JSON.stringify(out));
'''
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.r = json.loads(run.stdout)

    def test_both_end_wings_found_on_the_real_parts(self):
        self.assertGreaterEqual(self.r['parts'], 6)
        w = self.r['wings']
        self.assertEqual(len(w), 2, w)
        self.assertEqual(sorted(q['out'] for q in w), [-1, 1])
        for q in w:
            self.assertAlmostEqual(q['depth'], 8.3, delta=0.6)
            self.assertAlmostEqual(q['width'], 21.5, delta=1.0)

    def test_the_wedge_leans_in_and_faces_out(self):
        for f in self.r['wedge']:
            self.assertTrue(f['out'], f)
        self.assertGreater(self.r['wedge'][0]['ny'], 0.01)   # the outer face tilted up by its lean
        self.assertAlmostEqual(self.r['wedge'][0]['facade'], 21.5, delta=1.0)   # its bays from its start edge
        self.assertAlmostEqual(self.r['lean']['top'], 1.0, delta=0.05)
        self.assertAlmostEqual(self.r['lean']['bottom'], 8.3, delta=0.6)

    def test_the_north_slot(self):
        sl = self.r['slot']
        self.assertEqual(sl['n'], 1)
        self.assertAlmostEqual(sl['depth'], 7.0, delta=0.6)   # back to the core's face, the north wing's depth
        self.assertTrue(sl['open'] and sl['above'] and sl['beside'] and sl['below'], sl)

    def test_the_cage_runs_from_the_lintel(self):
        self.assertEqual(self.r['cage']['depth'], self.r['cage']['cage'])   # the screen's rows are laid on CC_DIMS.cage

    def test_the_z_braces(self):
        b = self.r['braces']
        self.assertEqual((b['n'], b['h']), (17, 9))   # nine horizontals, 26.52 to 132.6 m, and eight diagonals between them
        self.assertTrue(b['d'] and b['off'])

    def test_the_accumulator(self):
        a = self.r['acc']
        self.assertTrue(a['wound'])
        self.assertEqual((a['beam'], a['flat']), (10, 2))
        self.assertEqual(a['prism'], 10)
        self.assertAlmostEqual(a['uMax'], 36, places=3)   # metres along the ring (the art's tile divides in the vertex shader)
        self.assertEqual((a['vMin'], a['vMax']), (300, 342))   # and up it
        self.assertEqual(self.r['attrs'], ['color', 'normal', 'position'])   # 4-byte aligned float streams only
        self.assertTrue(self.r['released'])


if __name__ == '__main__':
    unittest.main()
