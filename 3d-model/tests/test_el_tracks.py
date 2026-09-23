"""Exercise production elevated-track geometry, joins, sleeper phase and batching."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ElevatedTracks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        src = (ROOT / 'app.js').read_text()
        def cut(start, end):
            a = src.index(start)
            return src[a:src.index(end, a)]
        script = r'''
const THREE=require(THREE_PATH),groupCity=new THREE.Group();
const GROUND_PITS=[];   // Round 139: the excavations elPortalClipGround also cuts (none in this harness)
const freeOnUpload=()=>{},step=(name,fn)=>fn(),siteY=(x,z)=>12+Math.sin(x/700)*3+Math.cos(z/800)*2;
const smooth=(a,b,x)=>{const t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t);};
const signedArea=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1];},0)/2;
CLIP_HELPERS
MERGE
BUILD
const out={stats:EL_STATS,meshes:groupCity.children.length,finite:true};
for(const m of groupCity.children){for(const a of Object.values(m.geometry.attributes))for(const v of a.array)if(!Number.isFinite(v))out.finite=false;}
const ties=groupCity.getObjectByName('El Cross Ties');
out.instanced=ties.isInstancedMesh;out.tieCount=ties.count;
const pts=[[0,0],[10,0],[16,6],[16,20]],ys=[12,12.5,13,14],frames=elTrackFrames(pts);
let gaugeError=0,joinError=0,topNormal=1;
for(let i=0;i<pts.length-1;i++){
 const dx=pts[i+1][0]-pts[i][0],dz=pts[i+1][1]-pts[i][1],len=Math.hypot(dx,dz),nx=-dz/len,nz=dx/len;
 for(const j of [i,i+1])gaugeError=Math.max(gaugeError,Math.abs(EL_RAIL.gauge*(frames[j][0]*nx+frames[j][1]*nz)-EL_RAIL.gauge));
}
const g=elTrackRibbon(pts,ys,frames,1.85,.06,.35,.40),pa=g.attributes.position,na=g.attributes.normal;
// Each segment has 18 vertices, with one 6-vertex end cap on the first segment.
const starts=[0,24,42];
for(let i=0;i<3;i++){
 const a=starts[i];for(let j=0;j<6;j++)topNormal=Math.min(topNormal,na.getY(a+j));
 if(i<2){const next=starts[i+1];for(const [u,v]of[[a+1,next],[a+2,next+5]])for(let c=0;c<3;c++)joinError=Math.max(joinError,Math.abs(pa.array[u*3+c]-pa.array[v*3+c]));}
}
out.gaugeError=gaugeError;out.joinError=joinError;out.topNormal=topNormal;
const flat=[[0,0],[.4,0],[2.25,0],[10.13,0]],height=[20,20.04,20.225,21.013];
const sleepers=elTrackSleepers(flat,height);
let spacingError=0,heightError=0;
for(let i=0;i<sleepers.length;i+=2){
 const a=sleepers[i];heightError=Math.max(heightError,Math.abs(a[1]-(20+a[0]*.1+.12)));
 if(i)spacingError=Math.max(spacingError,Math.abs(a[0]-sleepers[i-2][0]-.72));
}
out.sleeperSpacingError=spacingError;out.sleeperHeightError=heightError;

// A coarse sloped/tinted ground cell can span the entire narrow tunnel cut.
// Check exact footprint subtraction and attribute interpolation, not only nodes.
out.excavations=[];
for(const profile of elTrackProfiles()){
 const [a,b,c,d]=profile.bounds,x0=a-25,x1=b+25,z0=c-25,z1=d+25;
 const height=(x,z)=>20+.023*(x-x0)+.031*(z-z0),tint=(x,z)=>.2+.002*(x-x0)+.001*(z-z0);
 const p=[[x0,z0],[x1,z0],[x0,z1],[x1,z1]],g=new THREE.BufferGeometry();
 g.setAttribute('position',new THREE.Float32BufferAttribute(p.flatMap(q=>[q[0],height(...q),q[1]]),3));
 g.setAttribute('color',new THREE.Float32BufferAttribute(p.map(q=>tint(...q)),1));
 g.setIndex([0,2,1,1,2,3]);
 const result=elPortalClipGround(g),pa=result.attributes.position,co=result.attributes.color,ix=result.index;
 let area=0,buried=0,error=0,up=true;
 for(let k=0;k<ix.count;k+=3){
  const tri=[0,1,2].map(j=>{const i=ix.getX(k+j),x=pa.getX(i),z=pa.getZ(i);error=Math.max(error,Math.abs(pa.getY(i)-height(x,z)),Math.abs(co.getX(i)-tint(x,z)));return[x,z];});
  area+=Math.abs(signedArea(tri));up=up&&signedArea(tri)<0;
  for(const cut of profile.cuts){const overlap=streetIntersection(tri,cut.poly);if(overlap.length>=3)buried+=Math.abs(signedArea(overlap));}
 }
 const removed=profile.cuts.reduce((sum,c)=>sum+Math.abs(signedArea(c.poly)),0);
 let monotonic=true;for(let i=1;i<profile.stations.length&&profile.stations[i]<280;i++)monotonic=monotonic&&profile.ys[i]>=profile.ys[i-1];
 out.excavations.push({areaError:Math.abs(area-((x1-x0)*(z1-z0)-removed)),buried,error,up,monotonic,depth:siteY(...profile.pts[profile.mouth])-profile.ys[profile.mouth]-.4});
}
console.log(JSON.stringify(out));
'''
        script = script.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js')))
        clip = cut('  function streetBounds(', '  function rememberStreetTriangle(')
        clip += cut('  function streetIntersection(', '  // Cut-edge lawns')
        clip += cut('  function outsideConvex(', '  function trimTerrainPatch(')
        script = script.replace('CLIP_HELPERS', clip)
        script = script.replace('MERGE', cut('  function mergeColored(', '\n  function box('))
        script = script.replace('BUILD', cut('  const EL_TRACK =', "  // ---- Amtrak's tracks"))
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=True)
        cls.data = json.loads(result.stdout)

    def test_rails_join_and_keep_gauge_on_bends(self):
        self.assertLess(self.data['gaugeError'], 1e-6)
        self.assertEqual(self.data['joinError'], 0)
        self.assertGreater(self.data['topNormal'], .99)

    def test_sleepers_follow_slope_without_restarting_at_joints(self):
        self.assertLess(self.data['sleeperSpacingError'], 1e-9)
        self.assertLess(self.data['sleeperHeightError'], 1e-9)

    def test_portal_excavations_preserve_adjacent_ground(self):
        for cut in self.data['excavations']:
            self.assertLess(cut['areaError'], .10)
            self.assertLess(cut['buried'], .05)
            self.assertLess(cut['error'], 1e-4)
            self.assertTrue(cut['up'])

    def test_portal_grades_rise_from_below_ground(self):
        for cut in self.data['excavations']:
            self.assertTrue(cut['monotonic'])
            self.assertGreater(cut['depth'], 4.8)
        for portal in self.data['stats']['portals']:
            self.assertGreater(portal['clearance'], 4.4)
            self.assertGreater(portal['cutLength'], 50)

    def test_both_corridors_are_covered_with_bounded_draw_calls(self):
        d = self.data
        self.assertTrue(d['finite'])
        self.assertEqual(d['stats']['corridors'], 2)
        self.assertGreater(d['stats']['routeKm'], 14)
        self.assertEqual(d['stats']['runningRails'], 4)
        self.assertTrue(d['instanced'])
        self.assertEqual(d['meshes'], 3)
        self.assertEqual(d['tieCount'], d['stats']['sleepers'])
        self.assertTrue(35000 < d['tieCount'] < 60000)


if __name__ == '__main__':
    unittest.main()
