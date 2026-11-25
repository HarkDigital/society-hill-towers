"""Round 275 (Stage 5, the street lettering's fit: 1.2 to 1.84 s of every iPhone launch): the fit's two lifts take exact
shortcuts (groundMaxIn, and each remembered surface's bound by its highest point and by the triangle's corners). Under Node
with the page's own helpers, random ground grids (with a hole and skipped cells) and random pavement under random labels:
the geometry with the shortcuts is the geometry without them to the bit, and the shortcuts did answer most lifts. On the
real page, PERF.streetLabels.hash under ?dev reads the same with and without ?labelfit=old on both paths (Nov 24)."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()

SIM = r'''
const THREE=require(THREE_PATH),PERF={};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const signedArea=p=>p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1];},0)/2;
const schEdges=null,TERRAIN={water:-1000};const siteY=()=>0;
const ST_LABELS={l:[]},ST_SDF={fs:27,rowH:34,rects:[[0,0,500,34]]};
HELPERS
let seed=SEED;const rnd=()=>{seed=(seed*1103515245+12345)&0x7fffffff;return seed/0x7fffffff;};
function grid(x0,z0,n,cell,f,hole,skip,roads){
  const p=[];for(let j=0;j<=n;j++)for(let i=0;i<=n;i++){const x=x0+i*cell,z=z0+j*cell;p.push(x,f(x,z),z);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(p.map((_,i)=>i%3===1?1:0),3));
  registerGround(g,x0,x0+n*cell,z0,z0+n*cell,n,n,hole,skip,cell,roads);
}
const wav=(x,z)=>3*Math.sin(x*0.031)+2*Math.cos(z*0.047)+0.02*x;
const skip=new Uint8Array(40*40);for(let k=0;k<skip.length;k++)skip[k]=rnd()<0.06?1:0;
grid(-400,-400,40,20,wav,{x0:-60,x1:-20,z0:100,z1:160},skip,false);
grid(-100,-100,20,10,(x,z)=>wav(x,z)+0.1,null,null,true);
// labels: the page's own loop, minus the atlas, over random placements with pavement under them
const L=[];for(let n=0;n<120;n++)L.push(0,(rnd()-0.5)*700,(rnd()-0.5)*700,rnd()*360,Math.floor(rnd()*12));
ST_LABELS.l=L;initStreetSurfaces();
for(const f of streetFootprints){
  const pave=(x,z)=>wav(x,z)+0.15+(rnd()<0.3?rnd()*0.6:0)+(rnd()<0.05?4:0);
  for(let k=0;k<6;k++){
    const cx=f.x+(rnd()-0.5)*f.hw*2,cz=f.z+(rnd()-0.5)*f.hh*2,s=3+rnd()*10;
    const a=[cx-s,cz-s],b=[cx+s,cz-s],c=[cx+s,cz+s],d=[cx-s,cz+s];
    const tri=(p,q,r)=>rememberStreetTriangle([p[0],p[1],pave(p[0],p[1])],[q[0],q[1],pave(q[0],q[1])],[r[0],r[1],pave(r[0],r[1])]);
    tri(a,b,c);tri(a,c,d);
  }
}
const out=[];
for(const f of streetFootprints){const m=streetLabelGeometry(f,f.hw,f.hh,(x,z)=>wav(x,z)+0.38);for(const v of m.vertices)out.push(v[0],v[1],v[2]);}
const fb=new Uint32Array(new Float32Array(out).buffer);let h=0x811c9dc5>>>0;for(const u of fb){h^=u;h=Math.imul(h,16777619)>>>0;}
console.log(JSON.stringify({hash:h,n:out.length/3,LF,quick:LF_QUICK}));
'''


def run(seed, old):
    helpers = SRC[SRC.index('  const groundGrids = [];'):SRC.index('  function offsetPolyline(')]
    pre = "const location = { search: '?labelfit=old' };\n" if old else ''
    script = pre + SIM.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('HELPERS', helpers).replace('SEED', str(seed))
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout)


class LabelFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        cls.runs = [(run(s, False), run(s, True)) for s in (3, 17, 101)]

    def test_same_geometry_to_the_bit(self):
        for new, old in self.runs:
            self.assertTrue(new['quick'])
            self.assertFalse(old['quick'])
            self.assertGreater(new['n'], 1000)
            self.assertEqual(new['hash'], old['hash'], (new, old))

    def test_the_shortcuts_answer_lifts(self):
        for new, _ in self.runs:
            self.assertGreater(new['LF']['tSkip'], 0, new)
            self.assertGreater(new['LF']['sSkip'], 0, new)
            self.assertGreater(new['LF']['tRun'], 0, new)   # the hole, the skipped cells and the steep cells still run the walk

    def test_wiring(self):
        self.assertIn("const LF_QUICK = typeof location === 'undefined' || !/[?&]labelfit=old\\b/.test(location.search)", SRC)
        self.assertIn("stats.quick = { on: LF_QUICK, ...LF };", SRC)


if __name__ == '__main__':
    unittest.main()
