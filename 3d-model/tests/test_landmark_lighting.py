"""Exercise actual landmark geometry and palette routing, including deep crown recesses."""
import base64
import struct
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
def section(s,a,b):
    i=s.index(a)
    return s[i:s.index(b,i)]

class LandmarkLighting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):raise unittest.SkipTest('Node unavailable')
        s=(ROOT/'app.js').read_text()
        helpers='\n'.join([
            section(s,'  function signedArea(','  function pointInPoly('),
            section(s,'  function pointInPoly(','  function polyCentroid('),
            section(s,'  function box(','  // drop near-collinear'),
            section(s,'  function polyCentroid(','\n  function '),
            section(s,'  function orientedBox(','\n  function '),
            section(s,'  function obbAxis(','  function obbEnd('),
            section(s,'  function landmarkFacadeDetails(', '  // One south-facing recess'),
            section(s,'  function comcastCrownPlan(',"  // Cira's chamfered"),
            section(s,'  const LIGHT_COLORS =','  function lightsDateKey('),
            section(s,'  function lightsDateKey(','  function lightsLocalKey('),
            section(s,'  function lightsThemeAt(','  function lightsLabel('),
        ])
        blob=base64.b64decode((ROOT/'wide.b64').read_text());hdr=struct.unpack_from('<4i',blob);words=struct.unpack_from('<%dh'%((len(blob)-16)//2),blob,16);k=0;parts=[]
        for _ in range(hdr[1]):
            n,h,mh,t,attr,roof=words[k:k+6];k+=6;poly=[[words[k+j*2]/5,words[k+j*2+1]/5] for j in range(n)];k+=n*2
            x=sum(p[0] for p in poly)/n;z=sum(p[1] for p in poly)/n
            if abs(x+2028)<35 and abs(z+1031)<35 and h/5>60:parts.append(dict(poly=poly,h=h/5,mh=mh/5))
        script='const COMCAST_PARTS='+json.dumps(parts)+';\nconst THREE=require('+json.dumps(str(ROOT/'three.min.js'))+');\nconst BOATHOUSES='+ (ROOT/'boathouses.json').read_text()+';\n'+helpers+r'''
const out={crowns:[],boats:[],bands:[],palettes:[]};
for(const angle of [0,.159,1.2])for(const flip of [false,true]){
 const u=[Math.cos(angle),Math.sin(angle)],v=[-u[1],u[0]];
 let p=[[-22,-14],[22,-14],[22,14],[-22,14]].map(([x,z])=>[100+u[0]*x+v[0]*z,200+u[1]*x+v[1]*z]);if(flip)p.reverse();
 const c=comcastCrownPlan(p,297),inside=(q,y)=>c.pieces.some(p=>y>p.y0&&y<p.y1&&pointInPoly(...q,p.poly));
 out.crowns.push({deep:c.d-c.back,open:!inside(c.P(0,c.d-.5),259),rear:inside(c.P(0,-c.d+.5),259),lintel:inside(c.P(0,c.d-.5),275),piers:inside(c.P(c.w-.5,0),259),top:Math.max(...c.pieces.map(p=>p.y1)),bottom:c.bottom});
}
{
 const tallest=COMCAST_PARTS.reduce((a,b)=>a.h>b.h?a:b),cp=comcastCrownPlan(tallest.poly,297);
 const parts=[...cp.pieces];for(const p of COMCAST_PARTS)parts.push(...comcastFacadePieces(p.poly,p.mh||-1,p===tallest?cp.bottom:p.h,cp));
 const solid=(u,v,y)=>parts.some(p=>y>p.y0+.01&&y<p.y1-.01&&pointInPoly(...cp.P(u,v),p.poly));
 let open=true,shaft=true,back=true,crown=true;for(const y of [249,254,262,266,269])for(const u of [-10,0,10]){
   for(const v of [cp.back+1,cp.d-.5,cp.d+4])open&&=!solid(u,v,y);
   back&&=solid(u,-cp.d+.5,y);
 }
 for(const y of [49,98,147,240])shaft&&=solid(0,cp.d+4,y);
 for(const y of [272,281,296])crown&&=solid(0,cp.d-.5,y);
 const details=landmarkFacadeDetails({name:'Comcast Center'},tallest.poly,0,cp.bottom);
 out.actual={open,shaft,back,crown,parts:COMCAST_PARTS.length,darkAtria:details.filter(p=>p.color.getHex()===0x203039).length};
 const phils=lightsPinTheme('phillies'),auto=lightsThemeAt(2026,9,18,{mlb:{'2026-09-18':true}},null),flag=lightsPinTheme('red,white,blue');
 out.phillies={manual:phils.comcastSolid,automatic:auto.comcastSolid,manualBands:[...new Set(Array.from({length:100},(_,i)=>crownBandIndex(200+(i+.5)/100,2,false,phils.comcastSolid)))],customBands:[...new Set(Array.from({length:100},(_,i)=>crownBandIndex(200+(i+.5)/100,3,false,!!flag.comcastSolid)))]};
}
for(const spec of BOATHOUSE_PLANS){
 const m=boathouseGeometry(spec,6);let finite=true,maxY=-Infinity,minY=Infinity;
 for(const p of [...m.parts,...m.lights,...m.bays]){const a=p.geom.attributes.position;for(let i=0;i<a.count;i++){finite&&=[a.getX(i),a.getY(i),a.getZ(i)].every(Number.isFinite);maxY=Math.max(maxY,a.getY(i));minY=Math.min(minY,a.getY(i));}}
 const [x,z]=polyCentroid(spec.poly);
 out.boats.push({dark:m.parts.filter(p=>p.lit&&p.lit.r===0&&p.lit.g===0&&p.lit.b===0).length/m.parts.length,n:spec.number,finite,lit:m.lights.length,parts:m.parts.length,minY,maxY,h:spec.h,replace:boathouseAt(x,z)===spec,theme:m.lights.every(p=>p.mix===1&&p.lit&&p.gain>0),bays:m.bays.length,wantBays:spec.bays,bayTheme:m.bays.every(p=>p.mix===1&&p.lit&&p.gain>0&&p.lit.r>p.lit.b)});
}
for(let n=1;n<=4;n++)for(const solid of [false,true]){
 const values=Array.from({length:1000},(_,i)=>crownBandIndex(100+(i+.5)/1000,n,solid));
 out.bands.push({n,solid,values:[...new Set(values)],monotonic:values.every((v,i)=>i===0||v>=values[i-1])});
}
out.palettes=['red,white,blue','ff0000,fefefe,0011ff','plaid,red,ffffff','ffffff','notacolor'].map(lightsPinTheme);
console.log(JSON.stringify(out));
'''
        run=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=30)
        if run.returncode:raise AssertionError(run.stderr)
        cls.result=json.loads(run.stdout)

    def test_comcast_cavity_is_open_with_real_depth_and_supported_lintel(self):
        for c in self.result['crowns']:
            self.assertTrue(c['open'] and c['rear'] and c['lintel'] and c['piers'],c)
            self.assertGreater(c['deep'],8)
            self.assertEqual((297,247),(c['top'],c['bottom']))

    def test_real_building_parts_share_one_open_recess_below_solid_crown(self):
        r=self.result['actual']
        self.assertGreater(r['parts'],3)
        self.assertTrue(r['open'] and r['shaft'] and r['back'] and r['crown'],r)
        self.assertEqual(0,r['darkAtria'])

    def test_phillies_crown_is_solid_red_and_custom_bands_remain_available(self):
        r=self.result['phillies']
        self.assertTrue(r['manual'] and r['automatic'])
        self.assertEqual([0],r['manualBands'])
        self.assertEqual([0,1,2],r['customBands'])

    def test_every_clubhouse_has_themed_architectural_outlines(self):
        boats=self.result['boats']
        self.assertEqual([2,4,5,6,7,9,10,11,12,13,14],[b['n'] for b in boats])
        for b in boats:
            self.assertTrue(b['finite'] and b['theme'] and b['replace'],b)
            self.assertGreater(b['lit']+b['bays'],25)   # the arches' bulbs moved to the bays in Round 145
            self.assertGreater(b['lit'],5)
            self.assertGreater(b['parts'],50)
            self.assertGreater(b['dark'],.90, 'Walls and roofs must not inherit the light batch default glow')
            self.assertGreater(b['minY'],4)
            self.assertLess(b['maxY'],6+b['h']+2)
            # Round 145: every bay door carries its own coloured arch (17 runs of bulbs) and a glow, amber on a plain night
            self.assertEqual(b['bays'],b['wantBays']*18,b)
            self.assertTrue(b['bayTheme'],b)

    def test_bays_and_the_custom_house_take_their_own_slots(self):
        s=(ROOT/'app.js').read_text()
        self.assertIn('const slot=themeSlotN++%4,baySlot=themeSlotN%4;',s)
        self.assertIn('for(const p of model.bays)themeParts.push({...p,slot:baySlot});',s)
        # the Custom House: three consecutive slots, the lower block, the setback's square stage, the tower
        self.assertIn('const sA = themeSlotN % 4, sB = (themeSlotN + 1) % 4, sC = (themeSlotN + 2) % 4;',s)
        self.assertIn('CUSTOM_HOUSE_AT = { poly: b.poly, ob, ry };',s)
        for part in ('sheetOf(buildingGeom(grown, null, 40.2, 0.3).translate(0, base, 0), sA, 0.5, true);','sheetOf(box(34, 9.2, 34, ob.cx, base + 44.6, ob.cz, ry), sB, 0.62, true);','sheetOf(g, sC, 0.55, true);'):
            self.assertIn(part,s)

    def test_one_to_four_bands_are_contiguous_and_solid_uses_first_color(self):
        for b in self.result['bands']:
            self.assertTrue(b['monotonic'])
            self.assertEqual([0] if b['solid'] else list(range(b['n'])),b['values'])

    def test_custom_palettes_accept_hex_and_reject_unknown_colors(self):
        p=self.result['palettes']
        self.assertEqual(['red','white','blue'],p[0]['colors'])
        self.assertEqual(['#ff0000','#fefefe','#0011ff'],p[1]['colors'])
        self.assertEqual(['red','#ffffff'],p[2]['colors'])
        self.assertEqual(['#ffffff'],p[3]['colors'])
        self.assertIsNone(p[4])

if __name__=='__main__':unittest.main()
