"""Run production geometry builders: wall datums, compact attributes and landmark skins."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def section(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class Architecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        src = (ROOT / 'app.js').read_text()
        pieces = [
            section(src, '  function signedArea(', '  function pointInPoly('),
            section(src, '  function box(', '  // drop near-collinear'),
            section(src, '  function polyCentroid(', '\n  function '),
            section(src, '  function orientedBox(', '\n  function '),
            section(src, '  function obbAxis(', '  function obbEnd('),
            section(src, '  function pointInPoly(', '  function polyCentroid('),
            section(src, '  class IdxBuf {', '  const groupCity'),
            section(src, '  function towerStyle(', '  // a researched tower'),
            section(src, '  const TOWER_STYLE =', '  // the researched Center City'),
            section(src, '      const rectOf =', '      const bar ='),
        ]
        wide = section(src, '    const appendBuilding =', '    // ---- the stadiums')
        far = section(src, '    const appendB =', '    // buildings (merged block strips')
        script = r'''
const THREE = require(THREE_PATH);
const freeOnUpload=()=>{},hash01=n=>{const v=Math.sin(n)*43758.5453;return v-Math.floor(v);};
const glassTintKey=()=>.42,RING_AO=.78,v2=[],v2pool=[];
const pushV=(ch,...args)=>ch.push(...args);
HELPERS
WIDE
FAR
const out={};
const b=new VBuf(2);
for(let i=0;i<37;i++)b.push(i,0,0,0,0,1,.5,.4,.3,19,12,3.1,.5,i%2?53.7:0,53.7,41.24);
const g=b.geometry(true),a=g.attributes.aFacade;
out.packed={count:a.count,bytes:a.array.BYTES_PER_ELEMENT,normalized:a.normalized,released:b.fac===null,
 values:Array.from(a.array)};
const empty=new VBuf(2);for(let i=0;i<3;i++)empty.push(0,0,0,0,1,0,1,1,1,3,0);
out.defaults=Array.from(empty.geometry(true).attributes.aFacade.array);
const plain=new VBuf(2);plain.push(0,0,0,0,1,0,1,1,1,3,0);out.plain=!plain.geometry(false).attributes.aFacade;
const poly=[[10,20],[50,20],[50,50],[10,50]],hole=[[20,25],[20,40],[30,40],[30,25]];
out.walls=[];
for(const build of [appendBuilding,(ch,p,y0,y1,c,st,base,holes)=>appendB(ch,p,y0,y1,c,st,base)])for(const ring of [poly,[...poly].reverse()]){
 const ch=new VBuf(8);build(ch,ring,42,97,new THREE.Color(.2,.3,.4),19,12,[hole]);
 const geo=ch.geometry(true),pa=geo.attributes.position,na=geo.attributes.normal,fa=geo.attributes.aFacade;
 let wallN=0,roofN=0,valid=true,outward=true;
 for(let i=0;i<pa.count;i++){
  if(Math.abs(na.getY(i))<.1){wallN++;valid&&=fa.getY(i)===850&&Math.abs(fa.getX(i))>0;}
  else {roofN++;valid&&=fa.getX(i)===0&&fa.getY(i)===0;}
 }
 // Cross products must agree with the stored outward normals, also for hole walls.
 const va=new THREE.Vector3(),vb=new THREE.Vector3(),vc=new THREE.Vector3(),normal=new THREE.Vector3();
 for(let i=0;i<geo.index.count;i+=3){const ai=geo.index.getX(i),bi=geo.index.getX(i+1),ci=geo.index.getX(i+2);
  va.fromBufferAttribute(pa,ai);vb.fromBufferAttribute(pa,bi);vc.fromBufferAttribute(pa,ci);normal.fromBufferAttribute(na,ai);
  outward&&=vb.sub(va).cross(vc.sub(va)).dot(normal)>0;
 }
 out.walls.push({wallN,roofN,valid,outward});
}
out.plans=[];
for(const angle of [0,.17,1.3]){
 const u=[Math.cos(angle),Math.sin(angle)],v=[-u[1],u[0]],ring=recessedTowerPlan(200,-300,48.5,48.5,3.2,...u,...v);
 const area=signedArea(ring),tri=THREE.ShapeUtils.triangulateShape(ring.map(p=>new THREE.Vector2(...p)),[]);
 let triArea=0;for(const t of tri)triArea+=Math.abs(signedArea(t.map(i=>ring[i])));
 out.plans.push({n:ring.length,area,triArea});
}
out.crowns=[];
for(const sign of [-1,1])for(const top of [0,.55]){
 const geom=pyrRect({cx:0,cz:0},{ax:1,az:0,px:0,pz:sign,hl:20,hs:15},100,130,top);
 const p=geom.attributes.position,n=geom.attributes.normal;let valid=true;
 for(let i=0;i<p.count;i++){const radial=p.getX(i)*n.getX(i)+p.getZ(i)*n.getZ(i);valid&&=n.getY(i)>0&&radial>=-1e-5;}
 out.crowns.push(valid);
}
out.detail=[];
for(const name of ['Comcast Center','Comcast Technology Center','BNY Mellon Center','Three Logan Square','One Commerce Square'])for(const ring of [poly,[...poly].reverse()]){
 const parts=landmarkFacadeDetails({name},ring,12,240,70);let valid=true;
 for(const p of parts){p.geom.computeBoundingBox();const b=p.geom.boundingBox;
  valid&&=Array.from(p.geom.attributes.position.array).every(Number.isFinite)&&b.min.y>=82&&b.max.y<=252.1&&b.min.x>=9.5&&b.max.x<=50.5&&b.min.z>=19.5&&b.max.z<=50.5;
 }
 out.detail.push({n:parts.length,valid});
}
const actual=JSON.parse(require('fs').readFileSync(SCENE_PATH)).buildings.find(b=>b.name==='Cira Centre').poly;
out.cira=[];
for(const ring of [actual,[...actual].reverse()]){
 const [cx,cz]=polyCentroid(ring),geom=ciraGlassGeometry(ring,12,133),p=geom.attributes.position,n=geom.attributes.normal;
 let topInside=true,finite=true,outward=true;let lo=Infinity,hi=-Infinity;
 const roofYs=[];
 for(let i=0;i<p.count;i++){
  const x=p.getX(i),y=p.getY(i),z=p.getZ(i);finite&&=[x,y,z].every(Number.isFinite);lo=Math.min(lo,y);hi=Math.max(hi,y);
  if(y>13){topInside&&=pointInPoly(x,z,ring);roofYs.push(y);}
  if(n.getY(i)<.8)outward&&=(x-cx)*n.getX(i)+(z-cz)*n.getZ(i)>0;
  else outward&&=n.getY(i)>0;
 }
 out.cira.push({topInside,finite,outward,lo,hi,roofSpread:Math.max(...roofYs)-Math.min(...roofYs)});
}
out.styles=[landmarkFacadeStyle({name:'Comcast Technology Center',facade:'glass'}),landmarkFacadeStyle({name:'Comcast Center',facade:'glass'}),landmarkFacadeStyle({name:'FMC Tower',facade:'glass'}),landmarkFacadeStyle({name:'Cira Centre',facade:'glass'}),landmarkFacadeStyle({name:'Three Logan Square',facade:'deco'}),landmarkFacadeStyle({name:'Some glass tower',facade:'concrete_grid',glass:true})];
out.fabric=[towerStyle([0,0,5],2,1),towerStyle([5,0,3],4,1),towerStyle([0,2,5],2,1),towerStyle([3,2,2],3,1)];
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('SCENE_PATH',json.dumps(str(ROOT / 'scene_wide.json'))).replace('HELPERS', '\n'.join(pieces)).replace('WIDE', wide).replace('FAR', far)
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.result = json.loads(run.stdout)

    def test_compact_facade_measurements_survive_growth(self):
        r=self.result['packed']
        self.assertEqual((37,2,False,True),(r['count'],r['bytes'],r['normalized'],r['released']))
        for i in range(37):
            self.assertEqual([537 if i%2 else -537,412],r['values'][i*2:i*2+2])
        self.assertEqual([0]*6,self.result['defaults'])
        self.assertTrue(self.result['plain'])

    def test_both_packed_tiers_have_wall_metrics_and_correct_winding(self):
        for r in self.result['walls']:
            self.assertTrue(r['valid'] and r['outward'],r)
            self.assertGreaterEqual(r['wallN'],16)
            self.assertGreaterEqual(r['roofN'],4)

    def test_liberty_corner_recesses_preserve_a_closed_triangulatable_plan(self):
        for r in self.result['plans']:
            self.assertEqual(r['n'],12)
            self.assertAlmostEqual(r['area'],48.5**2-4*3.2**2,places=6)
            self.assertAlmostEqual(r['area'],r['triArea'],places=6)

    def test_glazed_pyramids_face_out_for_both_axis_conventions(self):
        self.assertTrue(all(self.result['crowns']))

    def test_landmark_detail_stays_on_its_building_part(self):
        for r in self.result['detail']:
            self.assertTrue(r['valid'],r)
            self.assertGreater(r['n'],4)

    def test_cira_crystal_stays_inside_its_surveyed_footprint(self):
        for r in self.result['cira']:
            self.assertTrue(r['topInside'] and r['finite'] and r['outward'],r)
            self.assertAlmostEqual(12,r['lo'],places=4)
            self.assertAlmostEqual(145,r['hi'],places=4)
            self.assertGreater(r['roofSpread'],10)

    def test_facade_selection_preserves_architectural_families(self):
        self.assertEqual([24,25,27,28,14,23],self.result['styles'])
        self.assertEqual([19,12,18,17],self.result['fabric'])

if __name__=='__main__':unittest.main()
