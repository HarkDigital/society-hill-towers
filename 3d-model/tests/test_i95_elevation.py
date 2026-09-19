"""I-95's southern approach must survive the core boundary as a continuous deck."""
import ast
import json
import math
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def height_at(chain, z):
    for a, b in zip(chain['p'], chain['p'][1:]):
        if min(a[1], b[1]) <= z <= max(a[1], b[1]):
            t = (z - a[1]) / (b[1] - a[1])
            return a[2] + t * (b[2] - a[2])
    raise AssertionError(f'Missing carriageway at z={z}')


class I95Elevation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse((ROOT / 'bake_overpasses.py').read_text())
        names = {'i95_south_approach', 'i95_approach_y', 'clip_core', 'emit_runs'}
        module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
        cls.bake = {'DATUM': 8.34, 'CORE': (-640, 770, -520, 850)}
        exec(compile(module, 'bake_overpasses.py', 'exec'), cls.bake)
        cls.data = json.loads((ROOT / 'overpasses.json').read_text())
        cls.mains = [c for c in cls.data['el'] if c.get('core') == 'i95']
        cls.ramps = [c for c in cls.data['el'] if c.get('core') == 'i95-ramp']

    def test_only_the_emerging_i95_mainline_is_promoted(self):
        classify = self.bake['i95_south_approach']
        tags = {'highway': 'motorway', 'ref': 'I 95'}
        self.assertTrue(classify(tags, [[80, 685], [22, 970]]))
        self.assertTrue(classify(dict(tags, bridge='yes'), [[104, 764], [128, 664]]))
        for other in [dict(tags, tunnel='yes'), dict(tags, ref='I 76'), dict(tags, highway='primary')]:
            self.assertFalse(classify(other, [[80, 685], [22, 970]]))
        self.assertFalse(classify(tags, [[80, 100], [100, 300]]))
        self.assertFalse(classify(tags, [[400, 685], [450, 970]]))

    def test_approach_gradually_connects_tunnel_and_viaduct(self):
        profile = self.bake['i95_approach_y']
        self.assertAlmostEqual(-6.05, profile(230, 1.5))
        self.assertAlmostEqual(8.3, profile(850, 1.5))
        ys = [profile(z, 1.5) for z in range(220, 1001)]
        self.assertTrue(all(0 <= b - a < .045 for a, b in zip(ys, ys[1:])))

    def test_core_clip_preserves_the_entire_selected_approach(self):
        points = [[80, z, 6] for z in (250, 500, 750, 850, 950, 1200)]
        emit = self.bake['emit_runs']
        self.assertEqual([(points, 0, 1)], emit([], [], (0, 1), points, keep_core=True))
        self.assertNotEqual(points, emit([], [], (0, 1), points)[0][0])

    def test_both_baked_carriageways_cross_the_old_boundary_at_height(self):
        self.assertEqual(2, len(self.mains))
        for main in self.mains:
            self.assertLess(min(p[1] for p in main['p']), 240)
            self.assertGreater(max(p[1] for p in main['p']), 3500)
            for z in (825, 850, 875, 900, 950, 1000):
                self.assertGreater(height_at(main, z), 5)
            for a, b in zip(main['p'], main['p'][1:]):
                self.assertLess(abs(b[2] - a[2]) / math.hypot(b[0] - a[0], b[1] - a[1]), .055)

    def test_ramps_meet_the_through_deck_without_a_vertical_step(self):
        self.assertEqual(2, len(self.ramps))
        junctions = 0
        for ramp in self.ramps:
            for p in (ramp['p'][0], ramp['p'][-1]):
                best = (math.inf, math.inf)
                for main in self.mains:
                    for a, b in zip(main['p'], main['p'][1:]):
                        dx, dz = b[0]-a[0], b[1]-a[1]
                        t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dz)/(dx*dx+dz*dz)))
                        d = math.hypot(p[0]-a[0]-dx*t, p[1]-a[1]-dz*t)
                        if d < best[0]:
                            best = (d, abs(p[2]-a[2]-(b[2]-a[2])*t))
                if best[0] < 1:
                    junctions += 1
                    self.assertLess(best[1], .03)
        self.assertEqual(3, junctions)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_production_deck_index_and_paint_follow_the_raised_geometry(self):
        src = (ROOT / 'app.js').read_text()
        index = src[src.index('  const OVP = '):src.index("  // ---- the outer districts' streets")]
        lookup = src[src.index('  const OVP_OWN_R = '):src.index('  // the Vine Street open cut:')]
        norms = src[src.index('    const norms = (pts) =>'):src.index('    // ---- the decks held')]
        ribbon = src[src.index('    const boxRibbon = '):src.index('    const boxAt = ')]
        traffic = src[src.index('        const x = pts[j][0], z = pts[j][1];'):src.index('        if (dead) { if (cur && cur.xs.length > 1)')]
        script = f"""
const THREE=require({json.dumps(str(ROOT / 'three.min.js'))});
const OVERPASSES=require({json.dumps(str(ROOT / 'overpasses.json'))});
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
{index}
{lookup}
{norms}
const parts=[],rememberStreetArray=()=>{{}};
{ribbon}
// The surrounding earth can be higher than a road emerging from the core cut.
const inCore=()=>true,inCapSite=()=>false,groundMeshLandY=()=>100,siteY=()=>100;
const bankFloor=()=>-1000,frontOff=()=>0,bridgeDeckLift=()=>null,sunkCutNear=()=>null;
const LAYER={{road:.24}},TERRAIN={{trenchW:10,trenchE:72}};
function trafficHeight(x0,z0,dx,dz){{
 const pts=[[x0-dx,z0-dz],[x0,z0],[x0+dx,z0+dz]],j=1,cls=0;
 {traffic}
 return y+lift;
}}
let samples=0,maxError=0,trafficError=0,notOwned=0,painted=0,vertices=0;
for(const c of OVP.el.filter(c=>c.core==='i95')){{
 for(let i=1;i<c.p.length;i++){{
  const a=c.p[i-1],b=c.p[i],dx=b[0]-a[0],dz=b[1]-a[1],length=Math.hypot(dx,dz);
  for(let j=1;j<20;j++){{
   const t=j/20,x=a[0]+dx*t,z=a[1]+dz*t;
   if(z<240||z>1250)continue;
   const y=ovpDeckY(x,z,dx/length,dz/length);
   maxError=Math.max(maxError,y===null?Infinity:Math.abs(y-a[2]-(b[2]-a[2])*t));samples++;
   trafficError=Math.max(trafficError,Math.abs(trafficHeight(x,z,dx/length,dz/length)-y-.1));
   if(!ovpOwned(x,z,x+dx/length,z+dz/length))notOwned++;
  }}
 }}
 boxRibbon(c.p,c.w/2,0,-1.7,new THREE.Color(),new THREE.Color(),null,null,true,1);
}}
for(const part of parts){{
 const a=part.geom.attributes;
 if(!a.aLane)continue;
 if(a.position.count!==a.aLane.count)throw Error('paint/position count mismatch');
 for(let i=0;i<a.aLane.count;i++){{
  if(!Number.isFinite(a.aLane.getY(i))||a.aLane.getW(i)!==1)throw Error('invalid lane attributes');
 }}painted++;vertices+=a.aLane.count;
}}
console.log(JSON.stringify({{samples,maxError,trafficError,notOwned,painted,vertices}}));
"""
        result = subprocess.run(['node', '-e', script], text=True, capture_output=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr[-2000:])
        data = json.loads(result.stdout)
        self.assertGreater(data['samples'], 500)
        self.assertLess(data['maxError'], 1e-8)
        self.assertLess(data['trafficError'], 1e-8)
        self.assertEqual(0, data['notOwned'])
        self.assertEqual(2, data['painted'])
        self.assertGreater(data['vertices'], 350)


if __name__ == '__main__':
    unittest.main()
