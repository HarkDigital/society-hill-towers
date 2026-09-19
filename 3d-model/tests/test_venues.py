"""Run the actual venue builders with vendored Three.js, without a browser/GPU.

Checks the generated geometry, rather than matching its source text: regulation
field dimensions and bearing, finite meshes, open playing fields, and terraced
seating. Canvas drawing is stubbed; rendered textures are checked in the preview.
"""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VenueGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = (ROOT / 'app.js').read_text()
        snippet = src[src.index('    const venueSurface = (ring, y) =>'):src.index('    const nb = hdr[1];')]
        code = r'''
const THREE = require(THREE_PATH), V3 = THREE.Vector3;
const c = new THREE.Color(), nightUniform = {value:0}, flood=[], themeParts=[];
const renderer = {capabilities:{getMaxAnisotropy:()=>8}};
const ctx = new Proxy({}, {get:(_,k)=>k==='createLinearGradient'?()=>({addColorStop(){}}):()=>{},set:()=>true});
const document = {createElement:()=>({getContext:()=>ctx})};
let maps=[], solids=[];
const getChunk=()=>({});
const appendBuilding=(ch,poly,y0,y1,col,style,base,holes)=>solids.push({poly,y0,y1,holes});
const addChunkMesh=(g,m)=>{maps.push(g);return new THREE.Mesh(g,m);};
const box=(w,h,d,x,y,z,ry=0)=>new THREE.BoxGeometry(w,h,d).rotateY(ry).translate(x,y,z);
SNIPPET
function run(ball){
  venueParts.length=0;maps=[];solids=[];
  buildStadium({poly:[],cx:ball?-1857:-1946,cz:ball?4383:4954,base:0,def:{baseball:ball,home:[-1861,4429]}},[]);
  const parts=venueParts.map(p=>p.geom), all=parts.concat(maps);
  const finite=all.every(g=>Array.from(g.attributes.position.array).every(Number.isFinite));
  const rows=new Set();let tris=0,blocked=0;
  const probes=[[0,0],[-40,-15],[-40,15],[40,-15],[40,15]];
  const ang=-8*Math.PI/180,ux=Math.sin(ang),uz=-Math.cos(ang),vx=Math.cos(ang),vz=Math.sin(ang);
  function local(x,z){const dx=x+1938.4,dz=z-4939.4;return [dx*ux+dz*uz,dx*vx+dz*vz];}
  const cross=(a,b,p)=>(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]);
  for(const g0 of parts){
    const g=g0.index?g0.toNonIndexed():g0,p=g.attributes.position.array;
    for(let j=0;j<p.length;j+=9){
      tris++;const h=[p[j+1],p[j+4],p[j+7]];
      if(Math.max(...h)-Math.min(...h)<.001&&h[0]>2&&h[0]<50)rows.add(h[0].toFixed(2));
      if(!ball&&Math.min(...h)>2){
        const a=local(p[j],p[j+2]),b=local(p[j+3],p[j+5]),c=local(p[j+6],p[j+8]);
        if(Math.abs(cross(a,b,c))<.01)continue;
        for(const q of probes){const v=[cross(a,b,q),cross(b,c,q),cross(c,a,q)];if(v.every(x=>x>.01)||v.every(x=>x<-.01))blocked++;}
      }
    }
  }
  const field=maps.find(g=>g.type==='PlaneGeometry'&&Math.abs(g.parameters.width-48.768)<.001);
  let extent=null;
  if(field){const p=field.attributes.position.array,u=[],v=[];for(let j=0;j<p.length;j+=3){const q=local(p[j],p[j+2]);u.push(q[0]);v.push(q[1]);}extent=[Math.max(...u)-Math.min(...u),Math.max(...v)-Math.min(...v)];}
  const ballField=ball?maps.find(g=>g.type==='BufferGeometry'&&!!g.attributes.uv):null;
  let uvOk=true;
  if(ballField)uvOk=Array.from(ballField.attributes.uv.array).every(v=>v>=0&&v<=1);
  // Inspect the built faces and housings in field coordinates, not their input angles.
  const screenGeometry=maps.filter(g=>g.type==='PlaneGeometry'&&Math.abs(g.parameters.width-29.3)<.001);
  const screens=screenGeometry.map(g=>{
    const p=g.attributes.position.array,n=g.attributes.normal.array,u=[],v=[];
    for(let j=0;j<p.length;j+=3){const q=local(p[j],p[j+2]);u.push(q[0]);v.push(q[1]);}
    const sign=Math.sign(u.reduce((a,b)=>a+b,0));
    return {depth:Math.max(...u)-Math.min(...u),width:Math.max(...v)-Math.min(...v),inward:-sign*(n[0]*ux+n[2]*uz)};
  });
  const screenCases=parts.filter(g=>g.type==='BoxGeometry'&&Math.abs(g.parameters.width-31.1)<.001).map(g=>{
    const p=g.attributes.position.array,u=[];for(let j=0;j<p.length;j+=3)u.push(local(p[j],p[j+2])[0]);
    return Math.max(...u)-Math.min(...u);
  });
  // Pairwise polygon clipping detects coplanar overlap anywhere on the field,
  // including the foul-corner triangles the old centroid fan drew twice.
  let fieldOverlap=0;
  if(ballField){
    const g=ballField.index?ballField.toNonIndexed():ballField,p=g.attributes.position.array,triangles=[];
    for(let j=0;j<p.length;j+=9){const t=[[p[j],p[j+2]],[p[j+3],p[j+5]],[p[j+6],p[j+8]]];if(cross(...t)<0)t.reverse();triangles.push(t);}
    function intersectionArea(subject,clip){
      let out=subject;
      for(let j=0;j<3&&out.length;j++){
        const a=clip[j],b=clip[(j+1)%3],input=out;out=[];
        let prev=input[input.length-1],pd=cross(a,b,prev);
        for(const q of input){const d=cross(a,b,q);
          if((d>=0)!==(pd>=0)){const t=pd/(pd-d);out.push([prev[0]+(q[0]-prev[0])*t,prev[1]+(q[1]-prev[1])*t]);}
          if(d>=0)out.push(q);prev=q;pd=d;
        }
      }
      let area=0;for(let j=1;j+1<out.length;j++)area+=cross(out[0],out[j],out[j+1])/2;
      return Math.abs(area);
    }
    for(let i=0;i<triangles.length;i++)for(let j=i+1;j<triangles.length;j++)fieldOverlap+=intersectionArea(triangles[i],triangles[j]);
  }
  return {finite,tris,rows:rows.size,blocked,extent,uvOk,screens,screenCases,fieldOverlap,fieldFound:!!(field||ballField)};
}
console.log(JSON.stringify({football:run(false),baseball:run(true)}));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('SNIPPET', snippet)
        result = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=40)
        if result.returncode:
            raise AssertionError(result.stderr[-2000:])
        cls.geometry = json.loads(result.stdout)

    def test_meshes_are_finite_and_terraced(self):
        for venue in self.geometry.values():
            self.assertTrue(venue['finite'])
            self.assertGreater(venue['rows'], 45)
            self.assertGreater(venue['tris'], 5000)
            self.assertLess(venue['tris'], 70000, 'venue detail should remain a small city-scale batch')

    def test_football_field_is_regulation_size_and_north_eight_west(self):
        field = self.geometry['football']
        self.assertTrue(field['fieldFound'])
        self.assertAlmostEqual(109.728, field['extent'][0], places=2)
        self.assertAlmostEqual(48.768, field['extent'][1], places=2)

    def test_no_decks_or_roofs_bridge_the_football_field(self):
        self.assertEqual(0, self.geometry['football']['blocked'])

    def test_baseball_field_texture_fits_its_polygon(self):
        self.assertTrue(self.geometry['baseball']['fieldFound'])
        self.assertTrue(self.geometry['baseball']['uvOk'])

    def test_baseball_field_has_no_overlapping_triangles(self):
        self.assertLess(self.geometry['baseball']['fieldOverlap'], 0.01,
                        'coplanar field triangles must not overlap and flicker')

    def test_football_scoreboards_are_flush_with_end_zones_and_face_inward(self):
        venue = self.geometry['football']
        self.assertEqual(2, len(venue['screens']))
        self.assertEqual(2, len(venue['screenCases']))
        for screen in venue['screens']:
            self.assertLess(screen['depth'], 0.01)
            self.assertAlmostEqual(29.3, screen['width'], places=2)
            self.assertGreater(screen['inward'], 0.9999)
        for depth in venue['screenCases']:
            self.assertAlmostEqual(1.6, depth, places=2)


if __name__ == '__main__':
    unittest.main()
