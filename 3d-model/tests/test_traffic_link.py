"""Round 158: the traffic linker from typed arrays (the phones' memory) builds exactly the graph the Map linker did.

trafficPrepareGraph splits every run where another run's end meets its middle and then links the ends that meet. It
kept a 'gx:gz' Map of JS arrays over every 20 m segment (616,000 entries, about 39 MB), built all 46,145 new runs while
the 32,300 old ones lived, and put the ends in a second string-keyed Map of small objects. The page now counts a
compressed-row cell index inside a nested function, lets each old run go as its pieces are made, and sweeps the ends
from one sort. This decodes the real traffic.b64 with the page's own step code (terrain stubbed with a deterministic
synthetic surface that has overpass bands, a sunk cut, a river and a dead zone, so the height test and the dead-water
splits both fire), runs the old linker (below, verbatim but for its name) and the page's, and requires every run's
keys, typed arrays (bit for bit), numbers and conn lists (order included) to match. It also runs each linker alone in
its own Node process and reports its peak heap, and the peak of heap plus ArrayBuffers, over the pre-link baseline."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

# The linker as it stood at Round 157 (app.js, 'function trafficPrepareGraph'), renamed oldPrepareGraph.
OLD = r'''
  function oldPrepareGraph(runs) {
    // OSM ways often meet the MIDDLE of another way. Split at those endpoints
    // before linking; endpoint-only links made ordinary intersections dead ends.
    // Small horizontal tolerance + a height check never joins stacked overpasses.
    const cell=32,grid=new Map(),cuts=runs.map(()=>[]),tol=.8;
    const key=(x,z)=>Math.floor(x/cell)+':'+Math.floor(z/cell);
    for(let ri=0;ri<runs.length;ri++) {
      const r=runs[ri];
      for(let j=0;j<r.xs.length-1;j++) {
        for(let x=Math.floor((Math.min(r.xs[j],r.xs[j+1])-tol)/cell);x<=Math.floor((Math.max(r.xs[j],r.xs[j+1])+tol)/cell);x++)
          for(let z=Math.floor((Math.min(r.zs[j],r.zs[j+1])-tol)/cell);z<=Math.floor((Math.max(r.zs[j],r.zs[j+1])+tol)/cell);z++) {
            const k=x+':'+z;if(!grid.has(k))grid.set(k,[]);grid.get(k).push(ri,j);
          }
      }
    }
    for(let ri=0;ri<runs.length;ri++)for(const e of [0,runs[ri].xs.length-1]) {
      const r=runs[ri],x=r.xs[e],z=r.zs[e],y=r.ys[e],near=grid.get(key(x,z))||[];
      for(let k=0;k<near.length;k+=2) {
        const qi=near[k],j=near[k+1];if(qi===ri)continue;
        const q=runs[qi],dx=q.xs[j+1]-q.xs[j],dz=q.zs[j+1]-q.zs[j],l2=dx*dx+dz*dz;
        if(l2<.01)continue;
        const t=clamp(((x-q.xs[j])*dx+(z-q.zs[j])*dz)/l2,0,1),s=q.cum[j]+t*(q.cum[j+1]-q.cum[j]);
        if(s<1.5||s>q.len-1.5)continue;
        if(Math.hypot(q.xs[j]+t*dx-x,q.zs[j]+t*dz-z)>tol||Math.abs(q.ys[j]+(q.ys[j+1]-q.ys[j])*t-y)>1.5)continue;
        cuts[qi].push(s);
      }
    }
    const split=[];
    for(let ri=0;ri<runs.length;ri++) {
      const r=runs[ri],stops=[0,...cuts[ri].sort((a,b)=>a-b).filter((v,i,a)=>!i||v-a[i-1]>1),r.len];
      for(let k=0;k<stops.length-1;k++) {
        const lo=stops[k],hi=stops[k+1],ss=[lo,...Array.from(r.cum).filter(s=>s>lo+.01&&s<hi-.01),hi];
        const xs=[],ys=[],zs=[],cum=[];let j=0;
        for(const s of ss){while(j<r.cum.length-2&&s>r.cum[j+1])j++;const t=(s-r.cum[j])/(r.cum[j+1]-r.cum[j]||1);xs.push(lerp(r.xs[j],r.xs[j+1],t));ys.push(lerp(r.ys[j],r.ys[j+1],t));zs.push(lerp(r.zs[j],r.zs[j+1],t));cum.push(s-lo);}
        split.push({...r,xs:Float32Array.from(xs),ys:Float32Array.from(ys),zs:Float32Array.from(zs),cum:Float32Array.from(cum),len:hi-lo,mx:(xs[0]+xs[xs.length-1])*.5,mz:(zs[0]+zs[zs.length-1])*.5,cars:[],conn:[[],[]]});
      }
    }
    runs.length=0;for(const r of split)runs.push(r);   // Round 153: a spread of 46,145 arguments can overflow a phone's stack
    const ends=new Map();
    for(let i=0;i<runs.length;i++)for(const e of [0,1]) {
      const r=runs[i],j=e?r.xs.length-1:0,k=Math.floor(r.xs[j])+':'+Math.floor(r.zs[j]);
      if(!ends.has(k))ends.set(k,[]);ends.get(k).push({i,e,x:r.xs[j],y:r.ys[j],z:r.zs[j]});
    }
    for(const list of ends.values())for(const a of list) {
      for(let x=Math.floor(a.x)-1;x<=Math.floor(a.x)+1;x++)for(let z=Math.floor(a.z)-1;z<=Math.floor(a.z)+1;z++)
        for(const b of ends.get(x+':'+z)||[])if(a.i!==b.i&&Math.hypot(a.x-b.x,a.z-b.z)<=tol&&Math.abs(a.y-b.y)<=1.5)runs[a.i].conn[a.e].push(b.i,b.e);
    }
  }
'''

# The step's decoder is cut from app.js, so the runs are made exactly as the page makes them; only the terrain is a
# stand-in (the heights change which ends meet, never whether the two linkers agree).
SCRIPT = r'''
const fs = require('fs'), path = require('path');
const ROOT = process.env.TL_ROOT, MODE = process.env.TL_MODE;
const src = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8');
const cut = (a, b) => { const i = src.indexOf(a); if (i < 0) throw new Error('app.js lacks ' + a); const j = src.indexOf(b, i + a.length); if (j < 0) throw new Error('app.js lacks ' + b); return src.slice(i, j); };
const line = (a) => cut(a, '\n') + '\n';
const helpers = line('  function clamp(v, a, b) {').replace('function clamp(', 'function clamp0(') + line('  function lerp(a, b, t) {').replace('function lerp(', 'function lerp0(')
  + cut('  function densify(pts, step) {', '  // Bowyer-Watson') + cut('  function unb64(b64, name) {', '  // a real macrotask boundary');
const decodeBody = cut("    const bin = unb64(TRAFFIC_B64, 'TRAFFIC');", '    trafficPrepareGraph(trafficRuns);');
const linker = cut('  function trafficPrepareGraph(runs) {', "  step('Setting the traffic flowing'");
const OLD = process.env.TL_OLD;

// the memory probe: every Math call and every clamp / lerp in the linkers ticks, and every 512th tick samples the heap
// as it stands, garbage and all; with TL_LIVE every 32,768th tick collects first, so the sample is what is still
// reachable (what a phone keeps once its collector has run under pressure)
const LIVE = process.env.TL_LIVE === '1', MASK = LIVE ? 32767 : 511;
const RM = globalThis.Math; let on = false, ticks = 0, peakH = 0, peakT = 0;
const sample = () => { if (LIVE) global.gc(); const m = process.memoryUsage(); if (m.heapUsed > peakH) peakH = m.heapUsed; const t = m.heapUsed + m.arrayBuffers; if (t > peakT) peakT = t; };
const tick = () => { if (on && (++ticks & MASK) === 0) sample(); };
const PM = Object.create(RM);
for (const f of ['floor', 'abs', 'ceil', 'round']) { const g = RM[f]; PM[f] = (x) => { tick(); return g(x); }; }
for (const f of ['min', 'max', 'hypot']) { const g = RM[f]; PM[f] = function (a, b) { tick(); return arguments.length === 2 ? g(a, b) : g.apply(RM, arguments); }; }

const body = helpers + `
function clamp(v, a, b) { tick(); return clamp0(v, a, b); }
function lerp(a, b, t) { tick(); return lerp0(a, b, t); }
const TERRAIN = { water: -7.34, trenchW: -40, trenchE: 40, trenchFloor: -9 }, CORE_EXT = { z0: -900, z1: 900 }, LAYER = { road: 0.06 };
const hill = (x, z) => 9 * Math.sin(x / 610) * Math.cos(z / 740) + 4 * Math.sin((x + z) / 233) + 0.0015 * z;
const riverCorridor = (x, z) => Math.abs(x * 0.8 + z * 0.6 + 2500) < 90;
const demY = (x, z) => riverCorridor(x, z) ? TERRAIN.water - 2 : hill(x, z);
const siteY = (x, z) => hill(x, z);
const groundMeshLandY = (x, z) => (Math.floor(x / 500) + Math.floor(z / 500)) % 3 === 0 ? null : hill(x, z) + 0.1;
const bankFloor = () => -Infinity;
const inCapSite = (x, z) => Math.abs(x + 300) < 120 && Math.abs(z - 200) < 120;
const inCore = (x, z) => Math.abs(x) < 1200 && Math.abs(z) < 900;
const frontOff = (x, z) => x * 0.98 + z * 0.17;
const bridgeDeckLift = (x, z) => Math.abs(x - 4200) < 60 && Math.abs(z + 900) < 400 ? 25 : null;
// elevated decks: an east-west street inside a 60 m band every 1,400 m rides 8 m up, so the cross streets under it
// meet it in plan but not in height
const ovpDeckY = (x, z, ux, uz) => Math.abs(ux) > 0.85 && Math.abs((((z % 1400) + 1400) % 1400) - 700) < 30 ? hill(x, z) + 8 : null;
const sunkCutNear = (x, z) => Math.abs(z - 1500) < 40 ? hill(x, z) - 6 : null;
let TRAFFIC_B64 = B64;
const trafficRuns = [];
function decode() {
${decodeBody}
  return trafficRuns;
}
${linker}
${OLD}
return { decode, newLink: trafficPrepareGraph, oldLink: oldPrepareGraph };`;
const api = new Function('Math', 'B64', 'tick', 'atob', body)(PM, fs.readFileSync(path.join(ROOT, 'traffic.b64'), 'utf8').trim(), tick, atob);
const runs = api.decode();
const before = runs.length;
const clone = (rs) => rs.map((r) => ({ ...r, xs: r.xs.slice(), zs: r.zs.slice(), ys: r.ys.slice(), cum: r.cum.slice(), cars: [] }));
const same = (a, b) => {
  if (ArrayBuffer.isView(a)) {
    if (!ArrayBuffer.isView(b) || a.constructor !== b.constructor || a.length !== b.length) return false;
    const ua = new Uint8Array(a.buffer, a.byteOffset, a.byteLength), ub = new Uint8Array(b.buffer, b.byteOffset, b.byteLength);
    for (let i = 0; i < ua.length; i++) if (ua[i] !== ub[i]) return false;
    return true;
  }
  if (Array.isArray(a)) return Array.isArray(b) && a.length === b.length && a.every((v, i) => same(v, b[i]));
  return Object.is(a, b);
};
const compare = (A, B) => {
  let bad = 0, first = null, links = 0, maxConn = 0;
  if (A.length !== B.length) { bad++; first = 'count ' + A.length + ' vs ' + B.length; }
  for (let i = 0; i < Math.min(A.length, B.length); i++) {
    const a = A[i], b = B[i], ka = Object.keys(a), kb = Object.keys(b);
    let ok = ka.join() === kb.join();
    for (const k of ka) if (!same(a[k], b[k])) { ok = false; if (!first) first = 'run ' + i + ' field ' + k; }
    if (!ok) { bad++; if (!first) first = 'run ' + i + ' keys ' + ka.join() + ' / ' + kb.join(); }
    links += a.conn[0].length / 2 + a.conn[1].length / 2; maxConn = Math.max(maxConn, a.conn[0].length / 2, a.conn[1].length / 2);
  }
  return { bad, first, links, maxConn };
};
// a dense random tangle about the origin: ends on a 0.25 m lattice (zero and negative coordinates included), repeated
// vertices, four deck levels a metre or more apart, and T-junctions dropped within the 0.8 m tolerance of another
// run's middle, so the corner cases the real network may not happen to hold are held here
const fuzz = (seed) => {
  let sd = seed; const rnd = () => { sd = (Math.imul(sd, 1664525) + 1013904223) >>> 0; return sd / 4294967296; };
  const out = [];
  for (let k = 0; k < 4000; k++) {
    let x, z;
    if (out.length && rnd() < 0.45) { const q = out[Math.floor(rnd() * out.length)], j = Math.floor(rnd() * (q.xs.length - 1)), t = rnd(); x = q.xs[j] + (q.xs[j + 1] - q.xs[j]) * t + (rnd() - 0.5) * 1.4; z = q.zs[j] + (q.zs[j + 1] - q.zs[j]) * t + (rnd() - 0.5) * 1.4; }
    else { x = Math.round((rnd() - 0.5) * 2400) / 4; z = Math.round((rnd() - 0.5) * 2400) / 4; }
    const lvl = [0, 1.2, 3, 8][Math.floor(rnd() * 4)], pts = [[x, z]], nseg = 1 + Math.floor(rnd() * 6);
    let a = rnd() * 6.283;
    for (let s = 0; s < nseg; s++) { const L = rnd() < 0.1 ? 0 : rnd() * 60; a += (rnd() - 0.5) * 0.8; x += Math.cos(a) * L; z += Math.sin(a) * L; pts.push([rnd() < 0.3 ? Math.round(x * 4) / 4 : x, rnd() < 0.3 ? Math.round(z * 4) / 4 : z]); }
    const m = pts.length, cum = new Float32Array(m); let L = 0;
    for (let j = 1; j < m; j++) { L += Math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]); cum[j] = L; }
    if (L < 2) continue;
    const len = cum[m - 1];
    out.push({ xs: Float32Array.from(pts.map((p) => p[0])), zs: Float32Array.from(pts.map((p) => p[1])), ys: Float32Array.from(pts.map(() => lvl + rnd() * 0.4)), cum, len, cls: Math.floor(rnd() * 6), oneway: rnd() < 0.3, aadt: 1000, mx: pts[m >> 1][0], mz: pts[m >> 1][1], want: 0, cars: [] });
  }
  return out;
};
if (MODE === 'compare') {
  const A = clone(runs), B = clone(runs);
  runs.length = 0;
  api.oldLink(A); api.newLink(B);
  const o = compare(A, B);
  const deadEnds = A.reduce((n, r) => n + (r.conn[0].length ? 0 : 1) + (r.conn[1].length ? 0 : 1), 0);
  const fz = [11, 12, 13].map((seed) => { const F = fuzz(seed), FA = clone(F), FB = clone(F); api.oldLink(FA); api.newLink(FB); const c = compare(FA, FB); return { seed, before: F.length, after: FA.length, bad: c.bad, first: c.first, links: c.links }; });
  console.log(JSON.stringify(Object.assign(o, { before, after: A.length, deadEnds, keys: Object.keys(A[0]).join(), km: Math.round(A.reduce((s, r) => s + r.len, 0) / 1000), fuzz: fz })));
} else {
  const link = MODE === 'old' ? api.oldLink : api.newLink;
  global.gc(); global.gc();
  const m0 = process.memoryUsage(), base = m0.heapUsed, baseT = m0.heapUsed + m0.arrayBuffers;
  peakH = base; peakT = baseT; on = true;
  const t0 = Date.now();
  link(runs);
  sample(); on = false;
  const ms = Date.now() - t0;
  global.gc(); global.gc();
  const m1 = process.memoryUsage();
  const MB = (v) => Math.round(v / 1e5) / 10;
  console.log(JSON.stringify({ mode: MODE + (LIVE ? ' live' : ''), runs: runs.length, ms, baseHeapMB: MB(base), peakHeapMB: MB(peakH - base), peakHeapPlusBuffersMB: MB(peakT - baseT), retainedMB: MB(m1.heapUsed + m1.arrayBuffers - baseT), samples: Math.floor(ticks / (MASK + 1)) }));
}
'''


class TrafficLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        if not (ROOT / 'traffic.b64').exists():
            raise unittest.SkipTest('traffic.b64 absent')

    def node(self, mode, live=False):
        env = dict(os.environ, TL_ROOT=str(ROOT), TL_MODE=mode, TL_OLD=OLD, TL_LIVE='1' if live else '0')
        r = subprocess.run(['node', '--expose-gc', '--max-old-space-size=4096', '-e', SCRIPT], capture_output=True, text=True, timeout=600, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-4000:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_identical_graph(self):
        o = self.node('compare')
        self.assertEqual(o['bad'], 0, o)
        self.assertGreater(o['after'], o['before'] + 5000, o)   # the mid-way splits fired
        self.assertGreater(o['links'], 50000, o)
        self.assertGreater(o['deadEnds'], 100, o)                # and so did the misses: height, dead water, true ends
        self.assertEqual(o['keys'], 'xs,zs,ys,cum,len,cls,oneway,aadt,mx,mz,want,cars,conn', o)
        for f in o['fuzz']:
            self.assertEqual(f['bad'], 0, f)
            self.assertGreater(f['after'], f['before'] + 500, f)
            self.assertGreater(f['links'], 1000, f)

    def test_memory(self):
        old, new = self.node('old'), self.node('new')
        old_live, new_live = self.node('old', live=True), self.node('new', live=True)
        print('\n  traffic linker (MB over the pre-link baseline)')
        for o in (old, new, old_live, new_live):
            print('    ' + json.dumps(o))
        self.assertEqual(old['runs'], new['runs'])
        # the old peak is the grid, the second run set and the ends Map on top of the first; the new one must come in
        # well under it, both as allocated and as still reachable
        self.assertLess(new['peakHeapPlusBuffersMB'], old['peakHeapPlusBuffersMB'] * 0.75, (old, new))
        self.assertLess(new_live['peakHeapPlusBuffersMB'], old_live['peakHeapPlusBuffersMB'] * 0.75, (old_live, new_live))


if __name__ == '__main__':
    unittest.main()
