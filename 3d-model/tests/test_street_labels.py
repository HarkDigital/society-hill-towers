"""Street names clear actual pavement across their complete texture footprint."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StreetLabels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        source = (ROOT / 'app.js').read_text()
        helpers = source[source.index('  const groundGrids = [];'):source.index('  function offsetPolyline(')]
        script = r'''
const THREE=require(THREE_PATH),PERF={};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const signedArea=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1];},0)/2;
const schEdges=null,TERRAIN={water:-1000};const siteY=()=>0;
const ST_LABELS={l:[0,0,0,0,0]},ST_SDF={fs:27,rowH:34,rects:[[0,0,500,34]]};
HELPERS
function reset(){groundGrids.length=0;coreRoadGround=null;streetFootprints=[];initStreetSurfaces();return streetFootprints[0];}
function grid(f){
 const p=[];for(let j=0;j<=10;j++)for(let i=0;i<=20;i++){const x=-100+i*10,z=-10+j*2;p.push(x,f(x,z),z);}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(p.map((_,i)=>i%3===1?1:0),3));
 registerGround(g,-100,100,-10,10,20,10,null,null,10,true);
}
function plate(x0,x1,z0,z1,fn,dx=0,dz=0){
 const a=[x0,z0,fn(x0,z0)],b=[x1,z0,fn(x1,z0)],c=[x1,z1,fn(x1,z1)],d=[x0,z1,fn(x0,z1)];
 rememberStreetTriangle(a,b,c,dx,dz);rememberStreetTriangle(a,c,d,dx,dz);
}
function inspect(mesh,top){
 let min=Infinity,finite=true,winding=true;
 for(let k=0;k<mesh.index.length;k+=3){
  const tri=mesh.index.slice(k,k+3).map(i=>mesh.vertices[i]);winding=winding&&signedArea(tri)<0;
  for(let u=0;u<=12;u++)for(let v=0;v<=12-u;v++){
   const w=[u/12,v/12,1-(u+v)/12],p=[0,1,2].map(j=>tri.reduce((s,q,i)=>s+q[j]*w[i],0));
   finite=finite&&p.every(Number.isFinite);min=Math.min(min,p[2]-top(p[0],p[1]));
  }
 }
 return {min,finite,winding,uvMin:Math.min(...mesh.uv),uvMax:Math.max(...mesh.uv),triangles:mesh.index.length/3};
}
const results={};let f=reset();
const slope=(x,z)=>12+.22*x+.35*z;
grid((x,z)=>slope(x,z)-.24);plate(-70,70,-10,10,slope);
results.slope=inspect(streetLabelGeometry(f,60,4,()=>1),slope);
// A narrow crest inside a label cell, missed by vertex-only ground/deck reads.
f=reset();grid(()=>0);
const crest=x=>4+Math.max(0,2-Math.abs(x-1.3)*2);
for(const [a,b] of [[-70,.3],[.3,1.3],[1.3,2.3],[2.3,70]])plate(a,b,-8,8,(x,z)=>crest(x)+.2*z);
results.crest=inspect(streetLabelGeometry(f,60,4,()=>.38),(x,z)=>crest(x)+.2*z);
// An authored road deck well above the DEM plus an unrelated crossing bridge.
f=reset();grid(()=>0);plate(-70,70,-8,8,()=>15,1,0);plate(-4,4,-8,8,()=>40,0,1);
results.deck=inspect(streetLabelGeometry(f,60,4,()=>.38),()=>15);
results.deck.maxHeight=Math.max(...streetLabelGeometry(f,60,4,()=>.38).vertices.map(p=>p[2]));
// Ground can peak between vertices independently of the recorded pavement.
f=reset();const ridge=(x,z)=>Math.max(0,8-Math.abs(x-10))+.3*z;grid(ridge);
results.ground=inspect(streetLabelGeometry(f,60,4,()=>.38),ridge);
// Baked atlas width is retained in full; no 10-column truncation or slope cap.
results.long=inspect(streetLabelGeometry(f,150,4,()=>50),()=>0);
console.log(JSON.stringify(results));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('HELPERS', helpers)
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.results = json.loads(result.stdout)

    def test_steep_grade_and_cross_slope_clear_pavement(self):
        self.assertGreaterEqual(self.results['slope']['min'], .179)

    def test_road_crest_inside_text_triangle_is_not_missed(self):
        self.assertGreaterEqual(self.results['crest']['min'], .179)

    def test_elevated_road_and_crossing_bridge_keep_distinct_levels(self):
        self.assertGreaterEqual(self.results['deck']['min'], .179)
        self.assertLess(self.results['deck']['maxHeight'], 16)

    def test_ground_triangle_interiors_stay_below_names(self):
        self.assertGreaterEqual(self.results['ground']['min'], .179)

    def test_complete_atlas_finite_geometry_and_visible_faces(self):
        for result in self.results.values():
            self.assertTrue(result['finite'] and result['winding'])
            self.assertEqual(result['uvMin'], 0)
            self.assertEqual(result['uvMax'], 1)
        self.assertGreater(self.results['long']['triangles'], 100)


if __name__ == '__main__':
    unittest.main()
