// The realism pass's vehicles, run for real under Node: the lofted cars from the baked profiles, the parked cars laid
// along a small street plan, and a signalised junction's furniture. The traffic section is evaluated as the page has it,
// over a few stubs for what lives outside it (the ground, the camera, the canvas). Prints one JSON object.
const fs = require('fs'), path = require('path'), THREE = require('../three.min.js');
const ROOT = path.join(__dirname, '..');
const src = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8');
const cut = (a, b) => { const i = src.indexOf(a); if (i < 0) throw new Error('missing ' + a); return src.slice(i, src.indexOf(b, i)); };
const helpers = cut('  function septaMerge(', '  function septaVehGeom(');
const traffic = cut('  // ---------------------------------------------------------------- traffic', '  // ---------------------------------------------------------------- streetlights');
const VEHICLE_ART = JSON.parse(fs.readFileSync(path.join(ROOT, 'vehicle_art.json'), 'utf8'));
const setup = `
const V3=THREE.Vector3,document={getElementById:()=>null,createElement:()=>({width:0,height:0,getContext:()=>new Proxy({},{get:(t,k)=>k==='measureText'?()=>({width:10}):()=>{} ,set:()=>true})})},step=()=>{},syncLayerBtn=()=>{},postRaw=m=>m;
const camera=new THREE.PerspectiveCamera(58,1.6,.75,26000),groupCity=new THREE.Group();
camera.position.set(0,40,0);camera.lookAt(0,0,-50);camera.updateMatrixWorld();
const clock={y:2026,m:10,d:12,minutes:870};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),lerp=(a,b,t)=>a+(b-a)*t;
const smooth=(a,b,v)=>{let t=clamp((v-a)/(b-a),0,1);return t*t*(3-2*t);};
const hash01=n=>{let s=Math.sin(n*127.1+311.7)*43758.5453;return s-Math.floor(s);};
const REAL=true,LITE=false,TIER2=false,location={search:''},sunWUniform={value:new V3(0,1,0)},nightUniform={value:0},lampUniform={value:0},POST={on:false};
const isTouch=TOUCH,NEAR_R=804.67,SCORES={games:[]},SEPTA_STOPS=undefined;
const inCore=()=>false,roadHalfW=()=>4.5,groundMeshLandY=()=>0,groundMeshY=()=>0,siteY=()=>0;
const _sp=new V3(),_sq=new THREE.Quaternion(),_ss=new V3(),_sm=new THREE.Matrix4(),_sc=new THREE.Color();
const flushInst=()=>{},anisoOf=n=>n,freeTexOnUpload=t=>t,artImage=()=>new Promise(()=>{}),artSrc=(a,b)=>a,lampLightPatch=()=>{};
const renderer={domElement:{height:800}};
`;
const out = {};
const make = (touch, art, furn) => new Function('THREE', 'VEHICLE_ART', 'STREET_FURN', setup.replace('TOUCH', touch ? 'true' : 'false') + helpers + traffic +
  'return {CAR_MODELS,carArtGeom,vehLoft,VART,trafficRuns,trafficCreateFleet,trafficFleet,PARKED,parkedInit,parkedLay,carSample,runHydrants,parkHalfW,FURN,furnInit,furnCell,TRAFFIC,camera,setReady:()=>{trafficReady=true;}};')(THREE, art ? VEHICLE_ART : undefined, furn);
// the cars: every kind's near and far body at its real size, every uv inside the atlas
for (const touch of [false, true]) {
  const a = make(touch, true);
  out[touch ? 'carsTouch' : 'cars'] = a.CAR_MODELS.map((m, k) => {
    const g0 = a.carArtGeom(k, 0), g1 = a.carArtGeom(k, 1);
    g0.computeBoundingBox();
    const b = g0.boundingBox, uv = g0.attributes.uv.array;
    let uvOk = true; for (const v of uv) if (!(v >= 0 && v <= 1)) uvOk = false;
    return { name: m.name, l: m.l, w: m.w, h: m.h, len: b.max.x - b.min.x, wid: b.max.z - b.min.z, top: b.max.y, bottom: b.min.y,
      tris: g0.attributes.position.count / 3, farTris: g1.attributes.position.count / 3, finite: Array.from(g0.attributes.position.array).every(Number.isFinite), uvOk,
      parts: [...new Set(Array.from(g0.attributes.aPart.array))].sort() };
  });
}
// a street plan: a one-way residential street (both kerbs), a two-way residential street (none: its two lanes fill it), a
// two-way secondary (both kerbs), the three meeting at a junction at the origin
const run = (pts, cls, oneway) => { let len = 0; const cum = [0]; for (let i = 1; i < pts.length; i++) { len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); cum.push(len); }
  return { xs: Float32Array.from(pts.map((p) => p[0])), ys: Float32Array.from(pts.map(() => 0.3)), zs: Float32Array.from(pts.map((p) => p[1])), cum: Float32Array.from(cum), len, cls, oneway, aadt: 1000,
    mx: (pts[0][0] + pts.at(-1)[0]) / 2, mz: (pts[0][1] + pts.at(-1)[1]) / 2, cars: [], conn: [[], []], want: 0 }; };
{
  const a = make(false, false);
  a.trafficRuns.push(run([[0, 0], [0, -200]], 5, true), run([[0, 0], [200, 0]], 5, false), run([[0, 0], [-200, 0]], 3, false));
  for (const r of a.trafficRuns) r.conn[0] = [9, 0];   // each meets the others at the origin
  a.trafficCreateFleet(); a.setReady(); a.parkedInit(); a.parkedLay(0);
  const cars = [];
  for (const p of a.PARKED.meshes) { const e = p.m.instanceMatrix.array; for (let i = 0; i < p.m.count; i++) cars.push({ x: e[i * 16 + 12], y: e[i * 16 + 13], z: e[i * 16 + 14], kind: p.kind, lod: p.lod, fx: e[i * 16], fz: e[i * 16 + 2] }); }
  const on = (pred) => cars.filter(pred);
  const res = { total: cars.length, oneway: on((c) => Math.abs(c.x) < 6 && c.z < 0), twoWayRes: on((c) => c.x > 0 && Math.abs(c.z) < 6), secondary: on((c) => c.x < 0 && Math.abs(c.z) < 7) };
  out.parked = { total: res.total, oneway: res.oneway.length, twoWayRes: res.twoWayRes.length, secondary: res.secondary.length,
    onewayOffsets: [...new Set(res.oneway.map((c) => Math.round(Math.abs(c.x) * 100) / 100))].sort(),
    secondaryOffsets: [...new Set(res.secondary.map((c) => Math.round(Math.abs(c.z) * 100) / 100))].sort(),
    nearestToJunction: Math.min(...cars.map((c) => Math.hypot(c.x, c.z))), farthest: Math.max(...cars.map((c) => Math.hypot(c.x, c.y - 40, c.z))), r: a.PARKED.r,
    secondaryFacing: res.secondary.map((c) => Math.sign(c.fx) * Math.sign(c.z)).every((v) => v === res.secondary.map((c) => Math.sign(c.fx) * Math.sign(c.z))[0]),
    lods: [...new Set(cars.map((c) => c.lod))].sort(), y: [...new Set(cars.map((c) => +c.y.toFixed(2)))] };
  // the hydrants the map lacks: every parked car keeps clear of them
  const hyd = [];
  a.trafficRuns.forEach((r, ri) => { const hy = a.runHydrants(r, ri), o = {}; for (let h = 0; h < hy.length; h += 2) { a.carSample(r, hy[h], 1, hy[h + 1] * (a.parkHalfW(r) + 0.55), o); hyd.push([o.x, o.z]); } });
  out.parked.hydrants = hyd.length;
  out.parked.nearestToHydrant = Math.min(...cars.map((c) => Math.min(...hyd.map((h) => Math.hypot(c.x - h[0], c.z - h[1])))));
}
// a signalised four-way junction of two secondaries, a stop sign 20 m up a residential street, a hydrant in the road
{
  const F = { sig: [0, 0], stop: [6, 160], hyd: [200, 2], bench: [], bin: [] };   // 0.5 m units: the stop at (3, 80) on the one-way street, the hydrant at (100, 1) in the road
  const a = make(false, false, F);
  a.trafficRuns.push(run([[0, 0], [300, 0]], 3, false), run([[0, 0], [-300, 0]], 3, false), run([[0, 0], [0, 300]], 3, false), run([[0, 0], [0, -300]], 3, false), run([[3, 120], [3, 0.1]], 5, true));
  a.furnInit();
  const rows = a.furnCell(0 * 100003 + 0), kinds = ['pole', 'head', 'stop', 'bus', 'hyd', 'bench', 'bin'], got = {};
  for (let i = 0; i < rows.length; i += 6) (got[kinds[rows[i]]] = got[kinds[rows[i]]] || []).push({ x: rows[i + 1], z: rows[i + 3], yaw: rows[i + 4], ex: rows[i + 5] });
  const heads = got.head || [];
  out.furniture = { poles: (got.pole || []).map((p) => [Math.round(p.x * 10) / 10, Math.round(p.z * 10) / 10]),
    heads: heads.length, headsOutward: heads.every((h) => (Math.cos(h.yaw) * h.x - Math.sin(h.yaw) * h.z) > 0),
    groups: [...new Set(heads.map((h) => Math.floor(h.ex)))].sort(),
    stop: (got.stop || []).map((p) => ({ x: +p.x.toFixed(2), z: +p.z.toFixed(2), fx: +Math.cos(p.yaw).toFixed(2), fz: +(-Math.sin(p.yaw)).toFixed(2) })),
    hyd: (got.hyd || []).map((p) => ({ x: +p.x.toFixed(2), z: +p.z.toFixed(2) })),
    // each hydrant's distance from the nearest street's centreline: the mapped one pushed out of the carriageway, the made ones at the kerb's back
    hydKerb: [...new Set((got.hyd || []).map((p) => +Math.min(Math.abs(p.z), Math.abs(p.x), Math.abs(p.x - 3) + (p.z > 120 ? 1e9 : 0)).toFixed(2)))].sort() };
}
// a wide street (class 1, 8 m to the kerb) crossing a narrow one (class 3, 5.5 m) at (60, 60), its signal mapped 12 m up an
// approach: each pole stands 1.6 m behind both kerbs, at the corner of the streets as they are drawn, not of the node
{
  const F = { sig: [120, 144], stop: [], hyd: [], bench: [], bin: [] };
  const a = make(false, false, F);
  a.trafficRuns.push(run([[60, 60], [300, 60]], 1, false), run([[60, 60], [-200, 60]], 1, false), run([[60, 60], [60, 300]], 3, false), run([[60, 60], [60, -200]], 3, false));
  a.furnInit();
  const rows = a.furnCell(0), poles = [];
  for (let i = 0; i < rows.length; i += 6) if (rows[i] === 0) poles.push([Math.round((rows[i + 1] - 60) * 10) / 10, Math.round((rows[i + 3] - 60) * 10) / 10]);
  out.furnitureWide = { poles: poles.sort((p, q) => p[0] - q[0] || p[1] - q[1]) };
}
console.log(JSON.stringify(out));
