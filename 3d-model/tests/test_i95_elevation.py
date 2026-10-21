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
        # Round 212: three, the Columbus Boulevard off-ramp and on-ramp no longer chained nose to nose into one hairpin
        self.assertEqual(3, len(self.ramps))
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

    def test_no_chain_doubles_back(self):
        """Round 212 (Mike: cars "flying up to the elevated section" at Fairmount Avenue): a chain never turns back on
        itself. Two branches leaving one node, or a divided mainline's two carriageways, were chained nose to nose and the
        profile held the turn in the air; pick_next and fill_path take the same turn limit now."""
        for key in ('el', 'sk'):
            for c in self.data[key]:
                P = c['p']
                for a, b, d in zip(P, P[1:], P[2:]):
                    ax, az, bx, bz = b[0] - a[0], b[1] - a[1], d[0] - b[0], d[1] - b[1]
                    la, lb = math.hypot(ax, az), math.hypot(bx, bz)
                    if la > 1 and lb > 1:
                        self.assertGreater((ax * bx + az * bz) / (la * lb), -0.3, '%s chain turns back at %s' % (key, b))

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
const bankFloor=()=>-1000,frontOff=()=>0,bridgeDeckLift=()=>null,sunkCutNear=()=>null,trenchLaneY=(x,z,y)=>y;
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


def node_json(script):
    result = subprocess.run(['node', '-e', script], text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise AssertionError(result.stderr[-2000:])
    return json.loads(result.stdout)


class MarketStreetCrossing(unittest.TestCase):
    """Round 216 (Mike, over I-95 at Market Street, #p=336.2,30.6,-523.7): Market Street was a narrow deck at Front
    Street's height that dropped 6 m at the trench's east wall, I-95's lanes climbed up under it to Front Street's height
    at the core's edge, and the outer districts' bare DEM stood over the trench there as a slab across the lanes."""

    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.data = json.loads((ROOT / 'overpasses.json').read_text())

    def test_the_bridge_is_baked_whole_as_one_core_chain(self):
        tree = ast.parse((ROOT / 'bake_overpasses.py').read_text())
        module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'penns_landing_bridge'], type_ignores=[])
        env = {}
        exec(compile(module, 'bake_overpasses.py', 'exec'), env)
        is_bridge = env['penns_landing_bridge']
        tags = {'highway': 'unclassified', 'bridge': 'yes', 'layer': '1', 'name': 'Market Street'}
        self.assertTrue(is_bridge(tags, [[396.6, -461.1], [232.2, -492.2], [111.3, -495.6]]))
        self.assertTrue(is_bridge(dict(tags, name="Penn's Landing Road"), [[367.4, -270.9], [396.6, -461.1]]))
        self.assertFalse(is_bridge(dict(tags, bridge='no'), [[396.6, -461.1], [232.2, -492.2]]))
        self.assertFalse(is_bridge(dict(tags, name='Walnut Street'), [[396.6, -461.1], [232.2, -492.2]]))
        self.assertFalse(is_bridge(tags, [[396.6, -561.1], [232.2, -592.2]]))   # outside the core: the bake's own profile
        market = [c for c in self.data['el'] if c.get('core') == 'market']
        self.assertEqual(1, len(market))
        c = market[0]
        self.assertEqual(13, c['w'])
        self.assertEqual([0, 0], c['e'])
        ends = sorted([c['p'][0][:2], c['p'][-1][:2]])
        self.assertEqual([[111.3, -495.6], [367.4, -270.9]], ends)   # 2nd Street to Penn's Landing Road's south end, every node
        self.assertGreaterEqual(len(c['p']), 25)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_the_trench_carries_on_north_with_no_climb_at_the_core_edge(self):
        src = self.src
        trench = src[src.index('  function trenchLaneY('):src.index("  // Penn's Landing CAP: a construction-stage")]
        out = node_json(f"""
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x)),lerp=(a,b,t)=>a+(b-a)*t;
const CORE_EXT={{x0:-640,x1:770,z0:-520,z1:850}},DATUM=8.34;
const TERRAIN={{trenchW:10,trenchE:72,trenchFloor:1.5-DATUM}};
// the offset from Front Street is x; the DEM falls 5 m across the trench as the real one does north of the core
const frontOff=(x,z)=>x,trenchDip=()=>0,demY=(x,z)=>1.0-0.075*x-0.004*(-520-z);
{trench}
const Z0=CORE_EXT.z0,L=TRENCH_NORTH_L,res={{edge:[],climb:-Infinity,maxGrade:0,far:[],outside:[]}};
for(const o of [15,25,38,52,62,70]){{
  res.edge.push([trenchLaneY(o,Z0+0.01,99),trenchNorthY(o,Z0-0.01)]);
  if(o>=24&&o<=58)for(let z=Z0;z<Z0+300;z+=2)res.climb=Math.max(res.climb,trenchLaneY(o,z,99));
  let prev=null;for(let z=Z0-0.01;z>Z0-L-20;z-=1){{const y=trenchNorthY(o,z)??(demY(o,z)-0.05);if(prev!==null)res.maxGrade=Math.max(res.maxGrade,Math.abs(y-prev));prev=y;}}
  res.far.push([trenchNorthY(o,Z0-L+0.01),demY(o,Z0-L+0.01)-0.05,trenchNorthY(o,Z0-L-0.01)]);
}}
res.outside=[trenchNorthY(5,Z0-50),trenchNorthY(80,Z0-50),trenchNorthY(40,Z0+1)];
res.floor=TERRAIN.trenchFloor;
console.log(JSON.stringify(res));
""")
        for lanes, ground in out['edge']:
            self.assertAlmostEqual(out['floor'] - 0.05, lanes, places=6)   # the core's lanes come down onto the trench's ground...
            self.assertAlmostEqual(lanes, ground, places=3)                # ...which carries on past the edge at the same height
        self.assertLessEqual(out['climb'], out['floor'] + 0.55 + 1e-9)       # never up toward Front Street (base) at the edge
        self.assertLess(out['maxGrade'], 0.06)
        for near_end, dem, past in out['far']:
            self.assertAlmostEqual(dem, near_end, places=2)                 # up to the outer districts' ground by its end
            self.assertIsNone(past)
        self.assertEqual([None, None, None], out['outside'])

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_the_deck_clears_what_it_crosses_and_meets_the_streets(self):
        src = self.src
        dens = src[src.index('  function densify(pts, step)'):src.index('  // Bowyer-Watson Delaunay')]
        solve = src[src.index('  const MARKET_GRADE = '):src.index('  marketDeckSolve();')]
        out = node_json(f"""
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const LAYER={{road:0.24}},TRENCH_CLEAR=5.0,TERRAIN={{trenchW:10,trenchE:72}},PERF={{}},ovpIndex=()=>{{}};
// a synthetic Front Street frame: the offset from it is x, the along-street coordinate z
const frontOff=(x,z)=>x,capAlong=(x,z)=>z,capPoint=(o,s)=>[o,s],plazaLift=()=>0;
const cityY=(x,z)=>1.0-0.004*x;                       // the street rising inland
const siteY=(x,z,mode)=>x<10?cityY(x,z):x<72?1.6:-5.0; // the trench's cross street (siteY's frontDem) stood 0.3 m over Front Street
const trenchLaneY=(x,z,base)=>x>10&&x<72?-6.29:base;
const D={{roads:[
  {{t:'secondary',w:11,name:'Front Street',pts:[[0,-300],[0,300]]}},
  {{t:'motorway',w:16,name:'I-95',pts:[[40,-300],[40,300]]}},
  {{t:'primary',w:13,name:'Columbus Boulevard',pts:[[100,-300],[100,300]]}},
  {{t:'unclassified',w:7,name:'Market Street',pts:[[-120,0],[320,0]]}},
  {{t:'residential',w:7,name:'a stub on the chain',pts:[[320,0],[320,80]]}},
]}};
const OVP={{el:[{{core:'market',c:5,w:13,e:[1,1],p:[[-120,0,9],[320,0,9]]}}]}};
{dens}
{solve}
marketDeckSolve();
const c=OVP.el[0],P=c.p,yAt=(x)=>{{for(let i=0;i+1<P.length;i++)if(P[i][0]<=x&&x<=P[i+1][0])return P[i][2]+(P[i+1][2]-P[i][2])*(x-P[i][0])/(P[i+1][0]-P[i][0]);return null;}};
let grade=0;for(let i=0;i+1<P.length;i++)grade=Math.max(grade,Math.abs(P[i+1][2]-P[i][2])/Math.hypot(P[i+1][0]-P[i][0],P[i+1][1]-P[i][1]));
console.log(JSON.stringify({{e:c.e,x0:P[0][0],x1:P[P.length-1][0],y0:P[0][2],y1:P[P.length-1][2],i95:yAt(40),col:yAt(100),trench:[yAt(12),yAt(40),yAt(70)],gap:[yAt(75),yAt(85),yAt(95)],grade,perf:PERF.marketDeck[0],front:cityY(8.5,0)+0.27}}));
""")
        dep = 1.15
        self.assertEqual([0, 0], out['e'])
        self.assertGreaterEqual(out['i95'] - dep - (-6.29 + 0.24), 5.0 - 1e-6)   # TRENCH_CLEAR to the deck's underside
        self.assertGreaterEqual(out['col'] - dep - (-5.0 + 0.24), 5.0 - 1e-6)
        self.assertGreaterEqual(out['perf']['clear'], 5.0 - 1e-6)
        for y in out['trench']:
            self.assertAlmostEqual(out['front'], y, delta=0.02)   # Front Street's own height over the trench, not frontDem's
        lo = min(out['i95'], out['col'])
        for y in out['gap']:
            self.assertGreaterEqual(y, lo - 1e-9)                   # level over the shelf between I-95 and Columbus Boulevard
        self.assertLessEqual(out['grade'], 0.055 + 1e-6)
        self.assertGreater(out['x0'], -10)                          # trimmed at Front Street: the street meets it there, at grade
        self.assertLess(out['x0'], 10)
        self.assertAlmostEqual(1.0 - 0.004 * out['x0'] + 0.27, out['y0'], delta=0.06)
        self.assertLess(out['x1'], 320)                             # and down to the street past Columbus Boulevard
        self.assertAlmostEqual(-5.0 + 0.27, out['y1'], delta=0.06)
        self.assertNotIn('Front Street', out['perf']['crossings'])
        self.assertNotIn('a stub on the chain', out['perf']['crossings'])


if __name__ == '__main__':
    unittest.main()
