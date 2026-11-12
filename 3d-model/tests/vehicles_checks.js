// The realism pass's vehicles, run for real under Node: the lofted cars from the baked profiles, the parked cars laid
// along a small street plan, and a signalised junction's furniture. The traffic section is evaluated as the page has it,
// over a few stubs for what lives outside it (the ground, the camera, the canvas). Prints one JSON object.
const fs = require('fs'), path = require('path'), THREE = require('../three.min.js');
const ROOT = path.join(__dirname, '..');
const src = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8');
const cut = (a, b) => { const i = src.indexOf(a); if (i < 0) throw new Error('missing ' + a); return src.slice(i, src.indexOf(b, i)); };
const helpers = cut('  function septaMerge(', '  function septaVehGeom(');
const traffic = cut('  // ---------------------------------------------------------------- traffic', '  // ---------------------------------------------------------------- streetlights');
// the drawn road grid every tier writes (Round 236: a parked row asks it for a street alongside its kerb)
const roadGrid = cut('  const SEPTA_RG_CELL = 36;', '  function septaSnapRoad(');
const VEHICLE_ART = JSON.parse(fs.readFileSync(path.join(ROOT, 'vehicle_art.json'), 'utf8'));
const setup = `
const V3=THREE.Vector3,document={getElementById:()=>null,createElement:()=>({width:0,height:0,getContext:()=>new Proxy({},{get:(t,k)=>k==='measureText'?()=>({width:10}):()=>{} ,set:()=>true})})},step=()=>{},syncLayerBtn=()=>{},postRaw=m=>m;
const camera=new THREE.PerspectiveCamera(58,1.6,.75,26000),groupCity=new THREE.Group();
camera.position.set(0,40,0);camera.lookAt(0,0,-50);camera.updateMatrixWorld();
const clock={y:2026,m:10,d:12,minutes:870};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),lerp=(a,b,t)=>a+(b-a)*t;
const smooth=(a,b,v)=>{let t=clamp((v-a)/(b-a),0,1);return t*t*(3-2*t);};
const hash01=n=>{let s=Math.sin(n*127.1+311.7)*43758.5453;return s-Math.floor(s);};
const ZREV={on:false},REAL=true,SNOW2_ON=true,wxSurfU={uSnowAcc:{value:0},uWet:{value:0}},LITE=false,TIER2=false,location={search:SEARCH},sunWUniform={value:new V3(0,1,0)},nightUniform={value:0},lampUniform={value:0},POST={on:false};
const isTouch=TOUCH,NEAR_R=804.67,SCORES={games:[]},SEPTA_STOPS=undefined;
const inCore=()=>CORE_HW!==null,roadHalfW=()=>CORE_HW===null?4.5:CORE_HW,groundMeshLandY=()=>0,groundMeshY=()=>0,siteY=()=>0;
const _sp=new V3(),_sq=new THREE.Quaternion(),_ss=new V3(),_sm=new THREE.Matrix4(),_sc=new THREE.Color();
const flushInst=()=>{},anisoOf=n=>n,freeTexOnUpload=t=>t,artImage=()=>new Promise(()=>{}),artSrc=(a,b)=>a,lampLightPatch=()=>{throw new Error('a vehicle takes vehLampPatch, never lampLightPatch');};
const lampMapU={uLampMap:{value:null},uLampBox:{value:new THREE.Vector4()},uLampOn:{value:0},uLampFade:{value:new THREE.Vector4()}},sun={intensity:1.85},sunDir=new V3(0,1,0);
const renderer={domElement:{height:800}},CORE_EXT={x0:-640,x1:770,z0:-520,z1:850};
`;
const out = {};
// SEARCH: the page's query (Round 233: '?parked=old&carscale=1' is Round 188's parking and real-size cars, '' the new plan)
const OLD = '?parked=old&carscale=1';
const make = (touch, art, furn, coreHw, search = '') => new Function('THREE', 'VEHICLE_ART', 'STREET_FURN', 'CORE_HW', 'SEARCH', setup.replace('TOUCH', touch ? 'true' : 'false') + helpers + roadGrid + traffic +
  'return {CAR_MODELS,carArtGeom,vehLoft,VART,trafficRuns,trafficCreateFleet,trafficFleet,PARKED,parkedInit,parkedLay,carSample,runHydrants,parkHalfW,FURN,furnInit,furnCell,TRAFFIC,camera,setReady:()=>{trafficReady=true;},' +
  'carArtMaterial,transitArtMaterial,carMapPatch,CARMAP,parkedSides,parkedShift,carOffset,carLaneCount,CAR_OFFW,PARK_CLEAR,trafficDraw,trafficHold,VEH_SHADOWS,vehShadowSync,vehShadowMaterial,vehShadowU,CAR_LOD_D,CAR_SHADE_D,furnGeoms,' +
  'CAR_K,PARK2,PARK_BOTH,PARK_AIR,PARK_KERB,PARK_PITCH,PARK_FILL,parkKerbIn,carGeom,carLightGeom,septaRoadAdd,SRG,PARK_MED,PARK_MED_GAP,PARK_TWIN_GAP,FURN_KINDS,FURN_ARM,streetInside,furnMedian};')(THREE, art ? VEHICLE_ART : undefined, furn, coreHw === undefined ? null : coreHw, search);
// the cars: every kind's near and far body at its real size, every uv inside the atlas
for (const touch of [false, true]) {
  const a = make(touch, true);
  out[touch ? 'carsTouch' : 'cars'] = a.CAR_MODELS.map((m, k) => {
    const g0 = a.carArtGeom(k, 0), g1 = a.carArtGeom(k, 1);
    g0.computeBoundingBox();
    const b = g0.boundingBox, uv = g0.attributes.uv.array;
    let uvOk = true; for (const v of uv) if (!(v >= 0 && v <= 1)) uvOk = false;
    const box = a.carGeom(k); box.computeBoundingBox();
    return { name: m.name, k: a.CAR_K, realL: m.real.l, realW: m.real.w, realH: m.real.h, boxLen: box.boundingBox.max.x - box.boundingBox.min.x, boxTop: box.boundingBox.max.y, l: m.l, w: m.w, h: m.h, len: b.max.x - b.min.x, wid: b.max.z - b.min.z, top: b.max.y, bottom: b.min.y,
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
  const a = make(false, false, undefined, undefined, OLD);
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
  const a = make(false, false, F, undefined, '?signals=old');   // Round 239: the old poles behind ?signals=old
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
  const a = make(false, false, F, undefined, '?signals=old');
  a.trafficRuns.push(run([[60, 60], [300, 60]], 1, false), run([[60, 60], [-200, 60]], 1, false), run([[60, 60], [60, 300]], 3, false), run([[60, 60], [60, -200]], 3, false));
  a.furnInit();
  const rows = a.furnCell(0), poles = [];
  for (let i = 0; i < rows.length; i += 6) if (rows[i] === 0) poles.push([Math.round((rows[i + 1] - 60) * 10) / 10, Math.round((rows[i + 3] - 60) * 10) / 10]);
  out.furnitureWide = { poles: poles.sort((p, q) => p[0] - q[0] || p[1] - q[1]) };
}
// the moving lanes against the parked rows: every class, one-way or two, every drawn half width from 2 to 9 m; wherever a
// kerb parks, its cars' centres stand the widest van's width clear of every moving lane's (a parked car at hw - 1.12)
{
  const a = make(false, false, undefined, undefined, OLD);
  const bad = [];
  let parkedCases = 0, oneSide = 0;
  for (const cls of [2, 3, 4, 5]) for (const oneway of [false, true]) for (let hw = 2; hw <= 9.001; hw += 0.05) {
    const r = { cls, oneway, mx: hw * 7.1, mz: cls * 3.3, xs: [0, 100], zs: [0, 0], ys: [0.3, 0.3] };
    const sides = a.parkedSides(r, hw);
    if (!sides.length) continue;
    parkedCases++;
    let shift = 0;
    if (sides.length === 1) { oneSide++; shift = -sides[0] * 1.07; }
    const lanes = [];
    for (let l = 0; l < a.carLaneCount(r); l++) {
      if (oneway) lanes.push((l - (a.carLaneCount(r) - 1) * 0.5) * 3.2 + shift);
      else lanes.push(a.CAR_OFFW[cls], -a.CAR_OFFW[cls]);   // each way's lane, on its own right
    }
    for (const sd of sides) {
      const u = sd * (hw - 1.12);
      for (const l of lanes) if (Math.abs(u - l) < 2.05 - 1e-9) bad.push({ cls, oneway, hw: +hw.toFixed(2), side: sd, lane: l });
    }
  }
  out.clearance = { bad: bad.slice(0, 8), nBad: bad.length, parkedCases, oneSide, tertiaryHw45: a.parkedSides({ cls: 4, oneway: false, mx: 0, mz: 0 }, 4.5).length, offw4: a.CAR_OFFW[4] };
}
// a two-way tertiary street outside the core (PARK_HW 4.5): both kerbs park, clear of the lanes moved in to 1.3 m; and a
// one-lane one-way street in the core 2.8 m to the kerb: one kerb parks and the moving car keeps to the other half
{
  const a = make(false, false, undefined, undefined, OLD);
  a.trafficRuns.push(run([[0, 0], [300, 0]], 4, false));
  a.trafficCreateFleet(); a.setReady(); a.parkedInit(); a.parkedLay(0);
  const zs = [];
  for (const p of a.PARKED.meshes) { const e = p.m.instanceMatrix.array; for (let i = 0; i < p.m.count; i++) zs.push(Math.round(e[i * 16 + 14] * 100) / 100); }
  out.tertiary = { n: zs.length, offsets: [...new Set(zs.map((z) => Math.abs(z)))].sort(), sides: [...new Set(zs.map(Math.sign))].sort(), lane: a.carOffset(a.trafficRuns[0], 0) };
  const b = make(false, false, undefined, 2.8, OLD);
  b.trafficRuns.push(run([[0, 0], [300, 0]], 5, true));
  b.trafficCreateFleet(); b.setReady(); b.parkedInit(); b.parkedLay(0);
  const zb = [];
  for (const p of b.PARKED.meshes) { const e = p.m.instanceMatrix.array; for (let i = 0; i < p.m.count; i++) zb.push(Math.round(e[i * 16 + 14] * 100) / 100); }
  const r = b.trafficRuns[0], lane = b.carOffset(r, 0), sample = {};
  b.carSample(r, 150, 1, lane, sample);
  out.narrowOneWay = { n: zb.length, z: [...new Set(zb)].sort(), laneZ: Math.round(sample.z * 100) / 100, hw: 2.8 };
}
// Round 233, the new plan (Mike: "There are parked cars clogging up many streets"): every car at CAR_K; each parked car
// its own flank off the kerb; a moving van passing the widest parked one with PARK_AIR to spare on every class and width,
// on the street; no two-way or multi-lane street losing a kerb it parked under Round 188; a narrow one-way street's blocks
// split between both kerbs and one about PARK_BOTH; each block side's fill about its class's mean
{
  const a = make(false, false), o = make(false, false, undefined, undefined, OLD);
  const vanW = a.CAR_MODELS[5].w, bad = [], lost = [];
  let cases = 0;
  for (const cls of [2, 3, 4, 5]) for (const oneway of [false, true]) for (let hw = 2; hw <= 9.001; hw += 0.05) {
    const r = { cls, oneway, mx: hw * 7.1, mz: cls * 3.3, xs: [0, 100], zs: [0, 0], ys: [0.3, 0.3] };
    const sides = a.parkedSides(r, hw), was = o.parkedSides(r, hw);
    if (was.length === 2 && sides.length < 2 && !(oneway && a.carLaneCount(r) === 1)) lost.push({ cls, oneway, hw: +hw.toFixed(2) });
    if (!sides.length) continue;
    cases++;
    const shift = sides.length === 1 && oneway && a.carLaneCount(r) === 1 ? -sides[0] * 1.07 : 0, lanes = [];
    for (let l = 0; l < a.carLaneCount(r); l++) {
      if (oneway) lanes.push((l - (a.carLaneCount(r) - 1) * 0.5) * 3.2 + shift);
      else lanes.push(a.CAR_OFFW[cls], -a.CAR_OFFW[cls]);
    }
    for (const sd of sides) {
      const u = sd * (hw - a.parkKerbIn(5));
      for (const l of lanes) {
        if (Math.abs(u - l) < vanW + a.PARK_AIR - 1e-9) bad.push({ cls, oneway, hw: +hw.toFixed(2), side: sd, lane: l, sep: +Math.abs(u - l).toFixed(3) });
        if (Math.abs(l) + vanW / 2 > hw + 1e-9) bad.push({ cls, oneway, hw: +hw.toFixed(2), lane: l, off: true });
      }
    }
  }
  // twenty parallel one-way residential blocks, 300 m each, and ten two-way tertiaries apart from them, laid at 14:30; each
  // side's fill counted against its own slots (the hydrants and bus stops take theirs before the fill)
  const P = make(false, false);
  for (let i = 0; i < 20; i++) P.trafficRuns.push(run([[-300 + i * 30, -150], [-300 + i * 30, 150]], 5, true));
  for (let i = 0; i < 10; i++) P.trafficRuns.push(run([[-150, 200 + i * 20], [150, 200 + i * 20]], 4, false));
  P.trafficCreateFleet(); P.setReady(); P.parkedInit(); P.parkedLay(0);
  const where = (x, z) => {
    if (Math.abs(z) <= 151) { const ri = Math.round((x + 300) / 30); if (ri >= 0 && ri < 20 && Math.abs(x - (-300 + ri * 30)) < 4) return ['r', ri, x > -300 + ri * 30 ? 0 : 1, Math.abs(x - (-300 + ri * 30))]; }
    else if (z > 190) { const tj = Math.round((z - 200) / 20); if (tj >= 0 && tj < 10 && Math.abs(z - (200 + tj * 20)) < 5) return ['t', tj, z > 200 + tj * 20 ? 0 : 1, Math.abs(z - (200 + tj * 20))]; }
    return null;
  };
  const cnt = { r: Array.from({ length: 20 }, () => [0, 0]), t: Array.from({ length: 10 }, () => [0, 0]) }, slotN = { r: Array.from({ length: 20 }, () => [0, 0]), t: Array.from({ length: 10 }, () => [0, 0]) }, offs = [];
  for (const rows of P.PARKED.slots.values()) for (let i = 0; i < rows.length; i += 7) { const w = where(rows[i], rows[i + 2]); if (w) slotN[w[0]][w[1]][w[2]]++; }
  for (const p of P.PARKED.meshes) { const e = p.m.instanceMatrix.array; for (let i = 0; i < p.m.count; i++) {
    const w = where(e[i * 16 + 12], e[i * 16 + 14]); if (!w) continue;
    cnt[w[0]][w[1]][w[2]]++; if (w[0] === 'r') offs.push([p.kind, w[3]]);
  } }
  const res = cnt.r, both = res.filter((c) => c[0] && c[1]).length;
  const sideFill = []; res.forEach((c, ri) => c.forEach((n, sd) => { if (slotN.r[ri][sd]) sideFill.push(n / slotN.r[ri][sd]); }));
  const tSlots = slotN.t.flat().reduce((s, v) => s + v, 0), tCars = cnt.t.flat().reduce((s, v) => s + v, 0);
  const kerbOk = offs.every(([k, d]) => Math.abs(d - (3.5 - P.PARK_KERB - P.CAR_MODELS[k].w / 2)) < 0.01);
  out.parked2 = { carK: a.CAR_K, park2: a.PARK2, oldPark2: o.PARK2, oldK: o.CAR_K, clear: +a.PARK_CLEAR.toFixed(3), cases, nBad: bad.length, bad: bad.slice(0, 6), lost,
    both, blocks: res.length, sideFillMin: +Math.min(...sideFill).toFixed(2), sideFillMax: +Math.max(...sideFill).toFixed(2),
    sideFillMean: +(sideFill.reduce((s, v) => s + v, 0) / sideFill.length).toFixed(3), kerbOk, nOffs: offs.length,
    tertBoth: cnt.t.filter((c) => c[0] && c[1]).length, tertFill: +(tCars / tSlots).toFixed(3), resSlots: slotN.r.flat().reduce((s, v) => s + v, 0),
    knobs: (() => { const q = make(false, false, undefined, undefined, '?parkboth=0&parkfill=1.25&carscale=0.92'); return { both: q.PARK_BOTH, fill: q.PARK_FILL.k, k: q.CAR_K }; })() };
}
// Round 236 (Mike: "Parked cars in the middle of city streets is not [natural]"): a divided street mapped as two one-way
// ways parks its outer kerbs only. Six groups of 300 m streets, each drawn into the road grid as the page draws it (its
// own half width and class), laid at 14:30 and every kerb's slots counted (the slots, so no fill draw decides a count):
// - overlap: two primaries (2 lanes, 6.5 m to the kerb) 11 m apart, driven opposite ways (the drawn halves overlap);
// - median: the same 24 m apart (an 11 m median, under PARK_TWIN_GAP);
// - wide: the same 30 m apart (a 17 m median: a boulevard that keeps its inner kerbs);
// - tertiaries: two two-way tertiaries 19 m apart (10 m between kerbs, over PARK_MED_GAP: both park every kerb);
// - right: a one-way primary with a two-way primary 24 m off its right kerb (the twin rule is the left kerb's only);
// - motorway: a one-way secondary with a motorway's drawn edge over its left kerb (never the street alongside)
{
  const groups = [
    ['overlap', [[-150, -300, 150, -300, 2, true], [150, -311, -150, -311, 2, true]]],
    ['median', [[-150, -200, 150, -200, 2, true], [150, -224, -150, -224, 2, true]]],
    ['wide', [[-150, -100, 150, -100, 2, true], [150, -130, -150, -130, 2, true]]],
    ['tertiaries', [[-150, 0, 150, 0, 4, false], [-150, 19, 150, 19, 4, false]]],
    ['right', [[-150, 100, 150, 100, 2, true], [-150, 124, 150, 124, 2, false]]],
    ['motorway', [[-150, 200, 150, 200, 3, true]]],
  ];
  const lay = (search) => {
    const P = make(false, false, undefined, undefined, search);
    for (const [, rs] of groups) for (const [x0, z0, x1, z1, cls, ow] of rs) P.trafficRuns.push(run([[x0, z0], [x1, z1]], cls, ow));
    for (const r of P.trafficRuns) P.septaRoadAdd(r.xs[0], r.zs[0], r.xs[1], r.zs[1], P.parkHalfW(r), r.cls);
    P.septaRoadAdd(-150, 192, 150, 192, 8, 0);   // the motorway, 8 m to its edge, over the secondary's left kerb
    P.trafficCreateFleet(); P.setReady(); P.parkedInit(); P.parkedLay(0);
    // each kerb's slots: the run (eastbound or westbound, so its right kerb is south or north of it) and the side
    const kerbs = {};
    let ri = 0;
    for (const [g, rs] of groups) rs.forEach(([x0, z0, x1], j) => {
      const r = P.trafficRuns[ri++], hw = P.parkHalfW(r), east = x1 > x0;
      for (const side of [1, -1]) {
        const zk = z0 + (east ? side : -side) * (hw - 1.0);   // a parked car's centre about a metre in from the kerb
        let n = 0;
        for (const rows of P.PARKED.slots.values()) for (let i = 0; i < rows.length; i += 7) if (Math.abs(rows[i + 2] - zk) < 0.35 && Math.abs(rows[i]) < 151) n++;
        kerbs[g + j + (side > 0 ? 'R' : 'L')] = n;
      }
    });
    return { kerbs, med: P.PARK_MED, gaps: [P.PARK_MED_GAP, P.PARK_TWIN_GAP], drawn: P.SRG.n };
  };
  out.median = Object.assign(lay(''), { old: lay('?parkmid=1') });
}
// the vehicles' own lamp share, written by their own patch on the materials' real shaders (review: a text replace on
// another patch's output matched nothing once that output changed)
{
  const a = make(false, true);
  const sh = (lib) => ({ uniforms: {}, vertexShader: THREE.ShaderLib[lib].vertexShader, fragmentShader: THREE.ShaderLib[lib].fragmentShader });
  const car = sh('physical'); a.carArtMaterial(0).onBeforeCompile(car);
  const bus = sh('standard'); a.transitArtMaterial(true, 0).onBeforeCompile(bus);
  const train = sh('standard'); a.transitArtMaterial(false, 1).onBeforeCompile(train);
  const share = (s) => (s.fragmentShader.match(/float lk = ([0-9.]+) \*/) || [])[1] || null;
  out.lampShare = { car: share(car), bus: share(bus), train: share(train), uniforms: ['uLampMap', 'uLampBox', 'uLampOn', 'uLampFade'].every((k) => car.uniforms[k] && bus.uniforms[k]),
    once: (car.fragmentShader.match(/uniform float uLampOn;/g) || []).length };
  // the headlights' pools: a lane-painted road, a lot and a deck take them, a green does not (sixteen texture units)
  const ground = (extra) => ({ uniforms: {}, vertexShader: '', fragmentShader: extra + '\nvoid main() {\n#include <emissivemap_fragment>\n}' });
  const road = ground('varying vec4 vLane;'), lot = ground('uniform sampler2D uLotTex; uniform float uLotM;'), deck = ground('uniform sampler2D uConcWall;'), lawn = ground('uniform sampler2D uGrass;');
  for (const g of [road, lot, deck, lawn]) { a.carMapPatch(g, 'vec3(0.0)'); a.carMapPatch(g, 'vec3(0.0)'); }
  const has = (g) => (g.fragmentShader.match(/uniform sampler2D uCarMap;/g) || []).length;
  out.carMap = { on: a.CARMAP.on, road: has(road), lot: has(lot), deck: has(deck), lawn: has(lawn) };
  // the shades: the sun's reads the shadow map where it lands and carries log depth, both fade with the fog, a deck's
  // collapses; the real shaders the materials are built on
  const sm = a.vehShadowMaterial(true, false, true), bm = a.vehShadowMaterial(true, true, false);
  const s1 = { uniforms: {}, vertexShader: THREE.ShaderLib.shadow.vertexShader, fragmentShader: THREE.ShaderLib.shadow.fragmentShader };
  const s2 = { uniforms: {}, vertexShader: THREE.ShaderLib.basic.vertexShader, fragmentShader: THREE.ShaderLib.basic.fragmentShader };
  sm.onBeforeCompile(s1); bm.onBeforeCompile(s2);
  out.shades = { sunType: sm.type, blobType: bm.type, sunFog: sm.fog, blobFog: bm.fog,
    maskRead: s1.fragmentShader.includes('float bk = mix(1.0, getShadowMask(), max(shIn, uShadeOut));') && !s1.fragmentShader.includes('opacity * ( 1.0 - getShadowMask() )'),
    maskWhere: s1.uniforms.uShadeOut === a.vehShadowU.uShadeOut && s1.uniforms.uCoreBox.value.toArray().join() === '-640,770,-520,850' && s1.vertexShader.includes('vShXZ = wpS.xz;'),
    outerOff: a.vehShadowU.uShadeOut.value,
    shadowAtShade: s1.vertexShader.includes('worldPosition = wpS;'), logDepth: ['#include <logdepthbuf_pars_vertex>', '#include <logdepthbuf_vertex>', 'vFragDepth = 1.0 + gl_Position.w * 0.9993'].every((t) => s1.vertexShader.includes(t)) && s1.fragmentShader.includes('#include <logdepthbuf_fragment>'),
    logOrder: s1.vertexShader.indexOf('vec4 mvPosition = viewMatrix * wpS;') < s1.vertexShader.indexOf('#include <logdepthbuf_vertex>') && s1.vertexShader.indexOf('#include <logdepthbuf_vertex>') < s1.vertexShader.indexOf('#include <worldpos_vertex>'),
    fog: [s1, s2].every((x) => x.fragmentShader.includes('shFog = fogFactor;') && x.fragmentShader.includes('(1.0 - shFog)')),
    fogAfter: [s1, s2].every((x) => x.fragmentShader.indexOf('shFog = fogFactor;') > x.fragmentShader.indexOf('#include <fog_fragment>')),
    deck: s1.vertexShader.includes('if (aShK < 0.5) gl_Position'), blobDeck: s2.vertexShader.includes('aShK') };
}
// the moving traffic's far copies and its shades' reach: cars at 40, 400 and 1,200 m; the near one the full body, the
// others the far copy, the farthest written last and out of its shades' count; a shade with nothing to draw is hidden
{
  const a = make(false, true);
  a.trafficRuns.push(run([[0, 0], [2000, 0]], 2, false));
  a.trafficCreateFleet();
  const r = a.trafficRuns[0];
  const mk = (x, kind) => ({ px: x, py: 0.3, pz: 0, x, y: 0.3, z: 0, kind, alpha: 1, heading: 0, col: 0xffffff, met: 0, brk: 0, seg: 0, s: x, dir: 1 });
  r.cars.push(mk(1200, 1), mk(40, 1), mk(400, 1), mk(300, 3)); a.trafficHold(r);   // Round 225: trafficDraw walks the runs on trafficBusy, so cars put on a run by hand are held the way carSpawn and carTransfer hold them
  a.camera.position.set(0, 2, 0);
  a.trafficDraw(0); a.vehShadowSync();
  const f = a.trafficFleet[1], f3 = a.trafficFleet[3];
  const shadeOf = (b) => a.VEH_SHADOWS.filter((m) => m.userData.body === b).map((m) => ({ n: m.count, vis: m.visible }));
  out.lod = { lodD: a.CAR_LOD_D, shadeD: a.CAR_SHADE_D, nearN: f.n, farN: f.far.n, farShadeN: f.far.body.userData.shadeN, nearShadeN: f.body.userData.shadeN,
    farXs: Array.from({ length: f.far.n }, (_, i) => f.far.body.instanceMatrix.array[i * 16 + 12]),
    nearTris: f.body.geometry.index ? f.body.geometry.index.count / 3 : f.body.geometry.attributes.position.count / 3,
    farTris: f.far.body.geometry.index ? f.far.body.geometry.index.count / 3 : f.far.body.geometry.attributes.position.count / 3,
    nearShades: shadeOf(f.body), farShades: shadeOf(f.far.body), emptyShades: shadeOf(a.trafficFleet[0].body), kind3Near: f3.n, kind3Far: f3.far.n,
    visible: { near: f.body.visible, far: f.far.body.visible, empty: a.trafficFleet[0].body.visible } };
}
// the furniture's geometry as plain triangles: an indexed part copied without its index drew slivers across the street
{
  for (const [name, search, touch] of [['furnGeom', '', false], ['furnGeomOld', '?signals=old', false], ['furnGeomTouch', '', true]]) {
    const a = make(touch, false, undefined, undefined, search), G = a.furnGeoms();
    const longest = {}, box = {};
    for (const k of Object.keys(G)) {
      const p = G[k].attributes.position.array; let m = 0;
      for (let i = 0; i < p.length; i += 9) for (const [u, v] of [[0, 3], [3, 6], [6, 0]]) m = Math.max(m, Math.hypot(p[i + u] - p[i + v], p[i + u + 1] - p[i + v + 1], p[i + u + 2] - p[i + v + 2]));
      longest[k] = +m.toFixed(2);
      G[k].computeBoundingBox(); const b = G[k].boundingBox; box[k] = [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z].map((v) => +v.toFixed(3));
    }
    const streams = {};   // every vertex stream's bytes per vertex (never 1 or 3: WebKit's Metal backend pads a copy)
    for (const k of Object.keys(G)) for (const [nm, at] of Object.entries(G[k].attributes)) streams[k + '.' + nm] = at.itemSize * at.array.BYTES_PER_ELEMENT;
    out[name] = { tris: Object.fromEntries(Object.keys(G).map((k) => [k, G[k].attributes.position.count / 3])), longest, box, streams, indexed: Object.keys(G).filter((k) => G[k].index) };
  }
}
// ---- the mast arms (Round 239): a junction's rows, as a list of kinds with places
const furnRows = (a, key) => {
  const rows = a.furnCell(key || 0), K = a.FURN_KINDS, got = {};
  for (let i = 0; i < rows.length; i += 6) (got[K[rows[i]]] = got[K[rows[i]]] || []).push({ x: rows[i + 1], y: rows[i + 2], z: rows[i + 3], yaw: rows[i + 4], ex: rows[i + 5] });
  return got;
};
const r1 = (v) => Math.round(v * 10) / 10;
const sortP = (ps) => ps.map((p) => [r1(p.x), r1(p.z)]).sort((p, q) => p[0] - q[0] || p[1] - q[1]);
// a head's facing (fx, fz), whether it hangs across the junction from the drivers it faces, and its place across their way
// (+ the driver's right as they drive in along -f)
const headInfo = (h) => { const fx = Math.cos(h.yaw), fz = -Math.sin(h.yaw); return { fx: +fx.toFixed(3), fz: +fz.toFixed(3), across: fx * h.x + fz * h.z < 0, right: r1(fz * h.x - fx * h.z), y: +h.y.toFixed(2) }; };
const armInfo = (r) => ({ x: r1(r.x), z: r1(r.z), y: +r.y.toFixed(2), L: +r.ex.toFixed(2), dx: +Math.cos(r.yaw).toFixed(3), dz: +(-Math.sin(r.yaw)).toFixed(3) });
const summary = (a, got) => ({ poles: sortP(got.pole || []), posts: sortP(got.post || []), arms: (got.arm || []).map(armInfo), heads: (got.head || []).map(headInfo),
  groups: [...new Set((got.head || []).map((h) => Math.floor(h.ex)))].sort(), peds: (got.ped || []).length, pedGroups: [...new Set((got.ped || []).map((h) => Math.floor(h.ex)))].sort(),
  // the arm's reach: every head hangs on an arm of its pole, at the arm's height, within its length
  onArm: (got.head || []).filter((h) => Math.abs(h.y - (a.FURN_ARM.armY - a.FURN_ARM.headDrop)) < 0.01).every((h) => (got.arm || []).some((r) => { const dx = Math.cos(r.yaw), dz = -Math.sin(r.yaw), s = (h.x - r.x) * dx + (h.z - r.z) * dz, o = Math.abs(-(h.x - r.x) * dz + (h.z - r.z) * dx); return o < 0.01 && s > 0 && s < r.ex; })),
  sg: { ...a.FURN.sg } });
{
  // a four-way of two two-way secondaries (5.5 m to the kerb): a mast pole on each corner, the far right corner of one
  // approach each, its arm square across that approach over its one moving lane, a head there and one on the pole
  const F = { sig: [0, 0], stop: [], hyd: [], bench: [], bin: [] };
  const a = make(false, false, F);
  a.trafficRuns.push(run([[0, 0], [300, 0]], 3, false), run([[0, 0], [-300, 0]], 3, false), run([[0, 0], [0, 300]], 3, false), run([[0, 0], [0, -300]], 3, false));
  a.furnInit();
  out.armsFour = summary(a, furnRows(a));
}
{
  // South Broad Street: two one-way carriageways (6.5 m half widths, 12 m apart, overlapping a metre like the drawn ones)
  // crossing a two-way secondary, its signal mapped on three approaches 12 to 15 m apart; the drawn streets in the road
  // grid as every tier writes them. One junction, its poles behind the outer kerbs, none on the asphalt or the median
  const F = { sig: [-12, -30, 12, 28, -12, 0], stop: [], hyd: [], bench: [], bin: [] };
  const a = make(false, false, F);
  a.trafficRuns.push(run([[-6, -300], [-6, 0]], 2, true), run([[-6, 0], [-6, 300]], 2, true), run([[6, 300], [6, 0]], 2, true), run([[6, 0], [6, -300]], 2, true),
    run([[-6, 0], [-300, 0]], 3, false), run([[6, 0], [300, 0]], 3, false), run([[-6, 0], [6, 0]], 3, false));
  for (const [x0, z0, x1, z1, hw, cls] of [[-6, -300, -6, 300, 6.5, 2], [6, -300, 6, 300, 6.5, 2], [-300, 0, 300, 0, 5.5, 3]]) a.septaRoadAdd(x0, z0, x1, z1, hw, cls);
  a.furnInit();
  const got = furnRows(a), s = summary(a, got), poles = [...(got.pole || []), ...(got.post || [])];
  s.junctions = a.FURN.junctions.length;
  s.onStreet = poles.filter((p) => a.streetInside(p.x, p.z, 0.4)).length;
  s.onMedian = poles.filter((p) => a.furnMedian(p.x, p.z)).length;
  // a pole stood on the median (x = 0) is dropped; one stood in a carriageway is moved out to the kerb
  s.medianPole = a.furnMedian(0, 10);
  out.armsBroad = s;
}
{
  // South Broad by Walnut: only the west carriageway (southbound) has a node at the crossing; the east one (northbound,
  // 13 m off) runs straight past it in one run, and so does Walnut (one-way west) across it. The east carriageway is
  // found as the twin, so the east corners stand behind its kerb, not in it
  const F = { sig: [-12, 0], stop: [], hyd: [], bench: [], bin: [] };
  const a = make(false, false, F);
  a.trafficRuns.push(run([[-6, -300], [-6, 0]], 2, true), run([[-6, 0], [-6, 300]], 2, true), run([[7, 300], [7, -300]], 2, true),
    run([[300, 0], [-6, 0]], 5, true), run([[-6, 0], [-300, 0]], 5, true));
  for (const [x0, z0, x1, z1, hw, cls] of [[-6, -300, -6, 300, 6.5, 2], [7, -300, 7, 300, 6.5, 2], [-300, 0, 300, 0, 3.5, 5]]) a.septaRoadAdd(x0, z0, x1, z1, hw, cls);
  a.furnInit();
  const J = a.FURN.junctions[0], got = furnRows(a, Math.floor(J.x / 160) * 100003 + Math.floor(J.z / 160)), s = summary(a, got), poles = [...(got.pole || []), ...(got.post || [])];
  s.onStreet = poles.filter((p) => a.streetInside(p.x, p.z, 0.4)).length;
  out.armsTwin = s;
}
{
  // Center City: a one-way street west crossing a one-way street south (5.5 m half widths): two approaches, so two mast
  // poles (the northwest and southwest corners), their arms over both moving lanes, and a post on each other corner
  const F = { sig: [0, 0], stop: [], hyd: [], bench: [], bin: [] };
  const a = make(false, false, F);
  a.trafficRuns.push(run([[300, 0], [0, 0]], 3, true), run([[0, 0], [-300, 0]], 3, true), run([[0, -300], [0, 0]], 3, true), run([[0, 0], [0, 300]], 3, true));
  a.furnInit();
  out.armsOneWay = summary(a, furnRows(a));
}
{
  // a signalised mid-block crossing on a two-way street that runs straight through: a pole a crosswalk's width past it on
  // each side, at the driver's right
  const F = { sig: [0, 0], stop: [], hyd: [], bench: [], bin: [] };
  const a = make(false, false, F);
  a.trafficRuns.push(run([[-200, 0], [200, 0]], 3, false));
  a.furnInit();
  out.armsMid = summary(a, furnRows(a));
}
console.log(JSON.stringify(out));
