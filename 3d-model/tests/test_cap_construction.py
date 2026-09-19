"""Penn's Landing is an elevated work site with unobstructed live road corridors."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def section(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class CapConstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        s = (ROOT / 'app.js').read_text()
        helpers = '\n'.join([
            section(s, '  function sampleDem(', '  function demAbs('),
            section(s, '  const fl =', '  const slips ='),
            section(s, '  function shelfY(', '  const PLAZA_R'),
            section(s, '  function box(', '  // drop near-collinear'),
        ])
        script = '''const THREE=require(THREE_PATH),D=DATA,G=DEM;
const DATUM=8.34,clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),lerp=(a,b,t)=>a+(b-a)*t;
const TERRAIN={trenchW:10,trenchE:72,trenchFloor:1.5-DATUM,shelfLo:2.4-DATUM,shelfHi:4-DATUM};
const LAYER={road:.24};
const demY=(x,z)=>sampleDem(G,x,z,8.34)-DATUM;
const siteY=(x,z)=>frontOff(x,z)<10?cityY(x,z):(frontOff(x,z)<72?TERRAIN.trenchFloor:shelfY(x,z));
// Surface tessellation is covered by transport/terrain tests. Keep these tests
// focused on the actual structural geometry and construction boundary clipping.
const flatPoly=(poly,holes,y)=>{const g=drapedPoly(poly,0);const a=g.attributes.position;for(let i=0;i<a.count;i++)a.setY(i,y);return g;};
const drapedPoly=(poly,up)=>{const shape=new THREE.Shape(poly.map(p=>new THREE.Vector2(p[0],-p[1])));const g=new THREE.ShapeGeometry(shape);g.rotateX(-Math.PI/2);const a=g.attributes.position;for(let i=0;i<a.count;i++)a.setY(i,siteY(a.getX(i),a.getZ(i))+up);return g;};
HELPERS
const m=capConstructionGeometry(),out={top:m.top,bottom:m.bottom,finite:true,counts:{},minClear:Infinity,pierHits:[],clipped:[]};
const active=D.roads.filter(r=>/motorway/.test(r.t)||/columbus boulevard/i.test(r.name||''));
const kept=[];
for(const r of active)for(let i=0;i+1<r.pts.length;i++){
 const a=r.pts[i],b=r.pts[i+1],L=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!L)continue;
 const nx=-(b[1]-a[1])/L,nz=(b[0]-a[0])/L;
 for(let j=0;j<=Math.ceil(L);j++)for(const side of [-1,0,1]){
  const t=j/Math.ceil(L),x=lerp(a[0],b[0],t)+side*nx*r.w/2,z=lerp(a[1],b[1],t)+side*nz*r.w/2;
  if(!inCapSite(x,z)||frontOff(x,z)>128)continue;
  let y=shelfY(x,z)+LAYER.road;
  if(/motorway/.test(r.t)){
   const o=frontOff(x,z),blend=clamp(Math.min(o-10,72-o)/14,0,1);
   y=lerp(frontDem(z),TERRAIN.trenchFloor+.55,blend*blend*(3-2*blend))+LAYER.road;
  }
  kept.push({x,z,y,name:r.name});out.minClear=Math.min(out.minClear,m.bottom-y);
 }
}
for(const p of m.parts){
 out.counts[p.kind]=(out.counts[p.kind]||0)+1;
 for(const v of p.geom.attributes.position.array)if(!Number.isFinite(v))out.finite=false;
 if(p.kind==='pier'||p.kind==='footing'){
  p.geom.computeBoundingBox();const c=p.geom.boundingBox.getCenter(new THREE.Vector3());
  const hit=kept.find(q=>Math.hypot(q.x-c.x,q.z-c.z)<1.1);
  if(hit)out.pierHits.push([c.x,c.z,hit.name]);
 }
}
const cross=[capPoint(-20,-210),capPoint(290,-210)],within=[capPoint(140,-230),capPoint(170,-230)],outside=[capPoint(-20,-390),capPoint(-20,-100)];
out.runs=[cross,within,outside].map(p=>capClipRoad(p).length);
for(const r of D.roads.filter(r=>!/motorway/.test(r.t)&&!/columbus boulevard|front street/i.test(r.name||'')))for(const run of capClipRoad(r.pts))for(let i=0;i+1<run.length;i++){
 const a=run[i],b=run[i+1];
 if(inCapSite((a[0]+b[0])/2,(a[1]+b[1])/2))out.clipped.push(r.name);
}
out.center=inCapSite(...capPoint(55,-220));out.front=inCapSite(...capPoint(0,-220));out.river=inCapSite(440,-220);
out.bare=CAPS.every(c=>c.kind!=='park');
console.log(JSON.stringify(out));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('DATA', (ROOT/'scene.json').read_text()).replace('DEM', (ROOT/'dem.json').read_text()).replace('HELPERS', helpers)
        run = subprocess.run(['node'], input=script, capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.result = json.loads(run.stdout)

    def test_structural_geometry_is_finite_and_has_open_girders(self):
        r = self.result
        self.assertTrue(r['finite'])
        self.assertGreater(r['counts']['girder'], 300)
        self.assertGreater(r['counts']['fence'], 150)
        self.assertGreater(r['counts']['crane'], 20)
        self.assertLess(r['counts']['deck'], r['counts']['girder']/5)

    def test_live_roads_have_vertical_and_horizontal_clearance(self):
        self.assertGreaterEqual(self.result['minClear'], 5.5)
        self.assertEqual([], self.result['pierHits'])

    def test_paths_and_access_roads_stop_at_the_work_zone(self):
        self.assertEqual([2, 0, 1], self.result['runs'])
        self.assertEqual([], self.result['clipped'])

    def test_work_zone_replaces_future_park_without_covering_front_or_river(self):
        r = self.result
        self.assertTrue(r['bare'] and r['center'])
        self.assertFalse(r['front'] or r['river'])


if __name__ == '__main__':
    unittest.main()
