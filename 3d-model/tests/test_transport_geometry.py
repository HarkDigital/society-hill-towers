"""Execute the production road/terrain helpers against folded heightfields.

Coverage, clearance and lane attributes are checked on generated triangles, including
core sidewalks, riverbank road grades, grid seams, cut cells and rail-bed widths.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TransportGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = Path(os.environ.get('TRANSPORT_APP', ROOT / 'app.js')).read_text()
        helpers = src[src.index('  const groundGrids = [];'):src.index('  function offsetPolyline(')]
        ribbon = src[src.index('  function ribbon('):src.index('  // Lane paint:')]
        densify = src[src.index('  function densify('):src.index('  // Bowyer-Watson')]
        rail_start = src.index('    const strip = (pts, ys, w, off, col, side, bots)')
        rail = src[rail_start:src.index('    let drawnSeg =', rail_start)]
        code = r'''
const THREE=require(THREE_PATH),PERF={};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),hash01=()=>0;
const signedArea=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1];},0)/2;
const schEdges=null,TERRAIN={water:-1000};let sample=(x,z)=>0;
const siteY=(x,z)=>sample(x,z);
HELPERS
RIBBON
DENSIFY
const parts=[];
RAIL_STRIP
function reset(){groundGrids.length=0;CORE_RESET}
function grid(x0,x1,z0,z1,nx,nz,f,skip=null,hole=null,core=false){
  const p=[];for(let j=0;j<=nz;j++)for(let i=0;i<=nx;i++){const x=x0+(x1-x0)*i/nx,z=z0+(z1-z0)*j/nz;p.push(x,f(x,z),z);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(p.map((_,i)=>i%3===1?1:0),3));
  registerGround(g,x0,x1,z0,z1,nx,nz,hole,skip,(x1-x0)/nx,core);
}
function measure(p,index=null,ground=groundMeshY){
  let min=Infinity,area=0,finite=true;
  const idx=index||Array.from({length:p.length/3},(_,i)=>i);
  for(let k=0;k<idx.length;k+=3){const a=idx[k]*3,b=idx[k+1]*3,c=idx[k+2]*3;
    area+=Math.abs((p[b]-p[a])*(p[c+2]-p[a+2])-(p[b+2]-p[a+2])*(p[c]-p[a]))/2;
    for(let u=0;u<=6;u++)for(let v=0;v<=6-u;v++){
      const A=u/6,B=v/6,C=1-A-B,x=p[a]*A+p[b]*B+p[c]*C,y=p[a+1]*A+p[b+1]*B+p[c+1]*C,z=p[a+2]*A+p[b+2]*B+p[c+2]*C;
      finite=finite&&[x,y,z].every(Number.isFinite);const g=ground(x,z);if(g!==null)min=Math.min(min,y-g);
    }
  }return {min,area,finite};
}
function road(a,b,hw,onMesh,ya,yb){const rc={pos:[],col:[],idx:[],n:0},lanes=[];
  const len=Math.hypot(b[0]-a[0],b[1]-a[1]);roadStrip(rc,(i,...q)=>lanes.push(...q),a,b,(b[0]-a[0])/len,(b[1]-a[1])/len,hw,ya,yb,.3,onMesh,80,80,80,0,len,0);
  return {...measure(rc.pos,rc.idx),laneCount:lanes.length/4,vertices:rc.n,laneFinite:lanes.every(Number.isFinite)};
}
const result={};
reset();grid(0,100,0,100,10,10,(x,z)=>Math.max(0,10-Math.abs(x-50))+.2*z);
result.bank=road([2,50],[98,50],5,false,10.3,10.3);
result.surface=road([2,50],[98,50],5,true,10.3,10.3);
reset();sample=(x,z)=>.35*z;grid(0,100,0,100,10,10,sample,null,null,true);
const path=ribbon([[10,50],[90,50]],6,.32),street=ribbon([[10,50],[90,50]],12,.24,null,{cls:0});
result.path=measure(path.attributes.position.array,null,sample);
result.core=measure(street.attributes.position.array,null,sample);
result.core.lanes=street.attributes.aLane.count===street.attributes.position.count;
reset();grid(0,50,0,100,5,10,(x,z)=>.2*z);grid(50,100,0,100,5,10,(x,z)=>.2*z);
result.seam=road([10,50],[90,50],4,true,10.3,10.3);
reset();grid(0,50,0,100,5,10,(x,z)=>.2*z);grid(50,100,0,100,5,10,(x,z)=>.2*z+3);
result.step=road([10,50],[90,50],4,true,10.3,13.3);
reset();grid(0,50,0,100,5,10,(x,z)=>.2*z+3);
result.edge=road([10,50],[70,50],4,false,10.3,10.3);

reset();const skip=new Uint8Array(4);skip[1]=1;grid(0,20,0,20,2,2,(x,z)=>.5*z,skip);
result.cut=road([2,5],[18,5],2,true,2.8,2.8);
reset();const hs=new Uint8Array(16);for(let j=1;j<3;j++)for(let i=1;i<3;i++)hs[j*4+i]=1;
grid(0,40,0,40,4,4,()=>0,hs,{x0:10,x1:30,z0:10,z1:30});grid(10,30,10,30,4,4,(x,z)=>.4*Math.min(x-10,30-x,z-10,30-z));
result.patch=road([2,20],[38,20],2,true,.3,.3);
reset();grid(0,100,0,100,10,10,(x,z)=>Math.max(0,9-Math.abs(x-50))+.6*z);
const a=[2,50],b=[98,50],lift=typeof trackTerrainLift==='function'?trackTerrainLift(a,b,30.75,30.75,2.1,.75):0;
result.rail={lift,...measure([2,30.75+lift,47.9,98,30.75+lift,47.9,98,30.75+lift,52.1,2,30.75+lift,47.9,98,30.75+lift,52.1,2,30.75+lift,52.1])};
result.bridgeLift=typeof trackTerrainLift==='function'?trackTerrainLift(a,b,60,60,6,.64):0;

// Small successive bends previously left both an outside notch and an inside overlap.
reset();grid(0,100,0,100,10,10,()=>0);
const curve=[[10,15],[35,15],[58,22],[78,42]],width=4;
const edges=typeof routeOffsets==='function'?routeOffsets(curve):null;
const roadMeshes=[];
for(let i=0;i+1<curve.length;i++){
 const a=curve[i],b=curve[i+1],dx=b[0]-a[0],dz=b[1]-a[1],len=Math.hypot(dx,dz),rc={pos:[],col:[],idx:[],n:0};
 roadStrip(rc,()=>{},a,b,dx/len,dz/len,width,.3,.3,.3,true,80,80,80,0,len,0,edges&&edges[i],edges&&edges[i+1]);
 roadMeshes.push(rc);
}
function triangles(p,index=null){const out=[],idx=index||Array.from({length:p.length/3},(_,i)=>i);for(let i=0;i<idx.length;i+=3)out.push(idx.slice(i,i+3).map(k=>[p[k*3],p[k*3+2]]));return out;}
function intersectionArea(a,b){
 let poly=a,sign=Math.sign(signedArea(b));
 for(let i=0;i<3&&poly.length;i++){
  const p=b[i],q=b[(i+1)%3],out=[];
  const f=v=>sign*((q[0]-p[0])*(v[1]-p[1])-(q[1]-p[1])*(v[0]-p[0]));
  for(let j=0;j<poly.length;j++){
   const u=poly[j],v=poly[(j+1)%poly.length],fu=f(u),fv=f(v);
   if(fu>=0)out.push(u);if((fu>=0)!==(fv>=0)){const t=fu/(fu-fv);out.push([u[0]+t*(v[0]-u[0]),u[1]+t*(v[1]-u[1])]);}
  }poly=out;
 }return poly.length>2?Math.abs(signedArea(poly)):0;
}
let roadOverlap=0,seamError=0;
for(let i=0;i+1<roadMeshes.length;i++){
 const a=roadMeshes[i],b=roadMeshes[i+1];
 for(const ta of triangles(a.pos,a.idx))for(const tb of triangles(b.pos,b.idx))roadOverlap+=intersectionArea(ta,tb);
 // True offset-line intersection, independent of the production helper.
 const prev=curve[i],p=curve[i+1],next=curve[i+2],l0=Math.hypot(p[0]-prev[0],p[1]-prev[1]),l1=Math.hypot(next[0]-p[0],next[1]-p[1]);
 const d0=[(p[0]-prev[0])/l0,(p[1]-prev[1])/l0],d1=[(next[0]-p[0])/l1,(next[1]-p[1])/l1],den=1+d0[0]*d1[0]+d0[1]*d1[1];
 for(const sg of [-1,1]){
  const x=p[0]-(d0[1]+d1[1])/den*width*sg,z=p[1]+(d0[0]+d1[0])/den*width*sg;
  for(const mesh of [a,b]){let closest=Infinity;for(let k=0;k<mesh.pos.length;k+=3)closest=Math.min(closest,Math.hypot(mesh.pos[k]-x,mesh.pos[k+2]-z));seamError=Math.max(seamError,closest);}
 }
}
result.joints={roadOverlap,seamError};
strip(curve,new Float64Array(curve.length).fill(1),4.2,-.25,new THREE.Color(),0);
const railPos=parts.pop().geom.attributes.position.array,railTris=triangles(railPos);
let railOverlap=0;
for(let i=0;i<railTris.length;i++)for(let j=i+1;j<railTris.length;j++)railOverlap+=intersectionArea(railTris[i],railTris[j]);
result.joints.railOverlap=railOverlap;
result.joints.railTriangles=railTris.length;
result.runs=typeof visibleRailRuns==='function'?visibleRailRuns([0,0,1,1,0,5,0]):[];
result.miterBounds=typeof routeOffsets==='function'?routeOffsets([[0,0],[0,0],[20,0],[0,.01]]).every(p=>p.every(Number.isFinite)&&Math.hypot(...p)<=2.000001):false;

console.log(JSON.stringify(result));
'''
        code = code.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js')))
        code = code.replace('HELPERS', helpers).replace('RIBBON', ribbon).replace('DENSIFY', densify)
        code = code.replace('RAIL_STRIP', rail)
        code = code.replace('CORE_RESET', 'coreRoadGround=null;' if 'let coreRoadGround' in helpers else '')
        run = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=40)
        if run.returncode:
            raise AssertionError(run.stderr[-3000:])
        cls.results = json.loads(run.stdout)

    def test_roads_clear_ridges_and_uphill_edges(self):
        for name in ('bank', 'surface'):
            with self.subTest(name=name):
                r = self.results[name]
                self.assertGreaterEqual(r['min'], .299)
                self.assertAlmostEqual(960, r['area'], places=2)
                self.assertTrue(r['finite'] and r['laneFinite'])
                self.assertEqual(r['vertices'], r['laneCount'])

    def test_core_streets_and_paths_clear_cross_slopes(self):
        for name, minimum in [('core', .21), ('path', .31)]:
            self.assertGreaterEqual(self.results[name]['min'], minimum)
        self.assertTrue(self.results['core']['lanes'])

    def test_grid_seams_and_patch_have_complete_single_coverage(self):
        for name, area in [('seam', 640), ('patch', 144), ('step', 640), ('edge', 480)]:
            r = self.results[name]
            self.assertAlmostEqual(area, r['area'], places=2)
            self.assertGreaterEqual(r['min'], .299)

    def test_cut_only_falls_back_inside_the_missing_cell(self):
        self.assertAlmostEqual(64, self.results['cut']['area'], places=2)
        self.assertGreaterEqual(self.results['cut']['min'], .299)

    def test_rail_clearance_covers_width_and_midspan(self):
        self.assertGreater(self.results['rail']['lift'], 9)
        self.assertGreaterEqual(self.results['rail']['min'], .749)

    def test_road_bends_share_edges_without_overlapping_faces(self):
        self.assertLess(self.results['joints']['roadOverlap'], 1e-6)
        self.assertLess(self.results['joints']['seamError'], 1e-6)
        self.assertTrue(self.results['miterBounds'])

    def test_ballast_bends_have_no_coplanar_fans_or_overlaps(self):
        self.assertLess(self.results['joints']['railOverlap'], 1e-4)
        self.assertEqual(6, self.results['joints']['railTriangles'])

    def test_tunnel_flags_hide_only_their_own_segments(self):
        self.assertEqual([[0, 2], [4, 6]], self.results['runs'])

    def test_clear_bridges_keep_their_height(self):
        self.assertEqual(0, self.results['bridgeLift'])


if __name__ == '__main__':
    unittest.main()
