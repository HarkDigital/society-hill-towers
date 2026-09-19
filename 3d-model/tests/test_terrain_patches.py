"""Cut-edge terrain must never obscure the pavement it is filling in beside."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TerrainPatches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        src = (ROOT / 'app.js').read_text()
        helpers = src[src.index('  const groundGrids = [];'):src.index('  function offsetPolyline(')]
        densify = src[src.index('  function densify('):src.index('  // Bowyer-Watson')]
        script = r'''
const THREE=require(THREE_PATH),PERF={};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const signedArea=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1];},0)/2;
const OVP={cor:[[[0,0,0,15],[100,0,0,15]]],sk:[]},RAIL_CUTS=[],CAPS=[];
const CORE_EXT={x0:-100,x1:100,z0:-100,z1:100};
let sample=(x,z)=>.4*z+20;
const siteY=(x,z)=>sample(x,z),schEdges=null,TERRAIN={water:-1000,trenchW:0,trenchE:100};
const frontOff=x=>x,frontDem=()=>20;
HELPERS
DENSIFY
function triangles(g){const p=g.attributes.position,idx=g.index,out=[];for(let k=0;k<(idx?idx.count:p.count);k+=3)out.push([0,1,2].map(j=>{const i=idx?idx.getX(k+j):k+j;return[p.getX(i),p.getZ(i),p.getY(i)];}));return out;}
function plate(x0,x1,z0,z1,height){const p=[[x0,z0],[x1,z0],[x1,z1],[x0,z1]].map(q=>[q[0],q[1],height(...q)]);return [[p[0],p[2],p[1]],[p[0],p[3],p[2]]];}
function geometry(tris){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(tris.flatMap(t=>t.flatMap(p=>[p[0],p[2],p[1]])),3));return g;}
function area(tris){return tris.reduce((s,t)=>s+Math.abs(signedArea(t)),0);}
function run(patch,roads){initTerrainPatches();for(const tri of roads)rememberTerrainRoad(...tri);const g=trimTerrainPatch(geometry(patch)),result=triangles(g);let buriedArea=0,finite=true,up=true;
 for(const tri of result){finite=finite&&tri.flat().every(Number.isFinite);up=up&&signedArea(tri)<0;
  for(const road of roads){const p=streetIntersection(tri,road);if(p.length<3)continue;const h=triangleGrade(...tri),r=triangleGrade(...road);
   if(p.some(q=>h(...q)>r(...q)-.075))buriedArea+=Math.abs(signedArea(p));
  }
 }return {area:area(result),buriedArea,finite,up};
}
const result={};
// An oblique, narrow road crosses the interior of two large grass triangles;
// none of the original grass vertices lies in the road. Vertex-only checks fail.
const patch=plate(-40,40,-40,40,()=>20),road=[[[0,-40,15],[10,40,15],[13,40,15]],[[0,-40,15],[13,40,15],[3,-40,15]]];
result.interior=run(patch,road);
result.crossing=run(patch,[...plate(-40,40,-4,4,()=>18),...plate(-5,5,-40,40,()=>16)]);
// A proper high bridge retains every square metre of ground under it.
result.bridge=run(patch,plate(-40,40,-4,4,()=>30));
// A ramp falls through the terrain; preserve its horizontal route and trim
// the interfering grass even when the height planes cross inside a triangle.
result.ramp=run(patch,plate(-40,40,-5,5,x=>20+.1*x));
CAPS.push({kind:'deck',dy:0,z0:-40,z1:40});
result.tunnel=run(plate(1,40,-30,30,()=>20),plate(1,40,-30,30,()=>10));
CAPS.length=0;
// A box's inclined end wall extends below grade but is not a road surface.
initTerrainPatches();streetSurfaceIndex=null;
const deck=new THREE.BoxGeometry(60,8,20);deck.rotateZ(.1);deck.translate(0,20,0);
const countBefore=TERRAIN_PATCH_STATS.surfaces;rememberStreetGeometry(deck);
result.deckFaces=TERRAIN_PATCH_STATS.surfaces-countBefore;
// A terrain ribbon is a skin on the full cross slope, not a raised roadway.
const pos=[];for(let j=0;j<=10;j++)for(let i=0;i<=10;i++){const x=i*10,z=j*10;pos.push(x,sample(x,z),z);}
const ground=new THREE.BufferGeometry();ground.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));ground.setAttribute('normal',new THREE.Float32BufferAttribute(pos.map((_,i)=>i%3===1?1:0),3));
registerGround(ground,0,100,0,100,10,10,null,null,10);
const ribbon=triangles(terrainRibbon([[10,50],[90,50]],34));
result.slope={area:area(ribbon),min:Infinity,max:-Infinity};
for(const tri of ribbon)for(const p of tri){const d=p[2]-sample(p[0],p[1]);result.slope.min=Math.min(result.slope.min,d);result.slope.max=Math.max(result.slope.max,d);}
console.log(JSON.stringify(result));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('HELPERS', helpers).replace('DENSIFY', densify)
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.results = json.loads(run.stdout)

    def test_narrow_road_cuts_through_triangle_interior(self):
        self.assertAlmostEqual(self.results['interior']['area'], 6400 - 240, places=2)
        self.assertLess(self.results['interior']['buriedArea'], .001)

    def test_intersecting_roads_leave_only_the_surrounding_terrain(self):
        result = self.results['crossing']
        self.assertAlmostEqual(result['area'], 6400 - 640 - 800 + 80, places=2)
        self.assertLess(result['buriedArea'], .001)

    def test_high_bridge_preserves_ground_and_sloped_ramp_stays_open(self):
        self.assertAlmostEqual(self.results['bridge']['area'], 6400, places=2)
        self.assertLess(self.results['ramp']['buriedArea'], .001)
        for name in ('bridge', 'ramp', 'interior', 'crossing'):
            self.assertTrue(self.results[name]['finite'] and self.results[name]['up'])

    def test_intentional_tunnel_cap_and_bridge_foundations_are_preserved(self):
        self.assertAlmostEqual(self.results['tunnel']['area'], 39 * 60, places=2)
        self.assertEqual(self.results['deckFaces'], 2)

    def test_grass_follows_the_entire_cross_slope_without_round_end_spill(self):
        result = self.results['slope']
        self.assertAlmostEqual(result['area'], 80 * 34, places=2)
        self.assertGreater(result['min'], .039)
        self.assertLess(result['max'], .041)


if __name__ == '__main__':
    unittest.main()
