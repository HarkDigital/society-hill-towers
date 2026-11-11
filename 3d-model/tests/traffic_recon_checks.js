// Round 225: the page's traffic section as it stands, beside the same section with the old trafficReconcile and the old
// walks of every run put back, both over the runs of the shipped traffic.b64 (decoded and linked by the page's own code,
// the terrain a synthetic stand-in as in test_traffic_link.py), both fed the same dice and flown down the same path.
// tests/test_traffic_reconcile.py runs this and reads the one JSON object it prints.
//   node traffic_recon_checks.js exact     a computer and a phone: every run, need, car and instance slot compared,
//                                          reconcile by reconcile and frame by frame, and the ms each took on the way
//   node traffic_recon_checks.js time      ms a call and a frame at a steady 5 pm over City Hall
//   osascript -l JavaScript traffic_recon_checks.js <3d-model> lite
//                                          a phone's shorter flight under JavaScriptCore, whose Math.sin is not V8's
//                                          (the jitter table must be the engine's own, and is)
var IS_NODE = typeof require === 'function' && typeof process !== 'undefined';

// ---- the functions as they stood at 1b476c2 (Round 224), verbatim: tests/test_traffic_reconcile.py pins each of the four
// texts by its sha256, so the reference cannot be edited along with the page without the pin moving in plain sight
const OLD_RECONCILE = String.raw`  function trafficReconcile(now) {
    const {frac}=trafficFrac();let implied=0;
    for(const r of trafficRuns) {
      const d=Math.hypot(r.mx-camera.position.x,r.mz-camera.position.z,camera.position.y-(r.ys[0]||0));
      // Spend the finite fleet near the viewer; keep a smaller upstream reservoir.
      const w=(1-smooth(CAR_VIEW.near,CAR_VIEW.warm,d))*(1+.65*(1-smooth(450,1500,d)));
      r.want=r.closed?0:r.aadt*frac/TRAFFIC_DENSITY_KMH[r.cls]*(r.len/1000)*w;implied+=r.want;
      r.inbound=0;
    }
    TRAFFIC.scale=Math.min(1,TRAFFIC.cap*.85/Math.max(1,implied));
    for(const r of trafficRuns)for(const c of r.cars)if(!c.die&&c.destination)c.destination.inbound++;
    for(let i=0;i<trafficRuns.length;i++) {
      const r=trafficRuns[i];r.target=Math.min(50,Math.floor(r.want*TRAFFIC.scale+hash01(i*7.3)));
    }
    const needs=[];
    for(let i=0;i<trafficRuns.length;i++) {
      const r=trafficRuns[i],target=r.target,alive=r.cars.filter(c=>!c.die);let extra=alive.length-target;
      for(const car of alive) {
        // A visible car always keeps its place, even after a clock/density change.
        if(carSpotRank(car.x,car.y,car.z)===0||now-car.born<CAR_MIN_LIFE)continue;
        if(car.destination?.want>0)continue;
        if(extra>0||r.want===0){carDeath(car,now,'dieRetire',r);extra--;}
      }
      const shortage=target-alive.length-r.inbound;
      if(shortage>0) {
        const near=1-smooth(450,CAR_VIEW.far,Math.hypot(r.mx-camera.position.x,r.mz-camera.position.z));
        needs.push({r,shortage,priority:near*2+shortage/(target||1)+hash01(i+trafficFrame)*.1});
      }
    }
    needs.sort((a,b)=>b.priority-a.priority);
    let budget=trafficSeeded?(isTouch?20:75):TRAFFIC.cap,feedBudget=isTouch?8:24;
    // Round-robin demand: a busy highway cannot consume the pool before local streets.
    for(let pass=0;pass<50&&budget>0&&trafficCars<TRAFFIC.cap;pass++)for(const n of needs) {
      if(n.shortage<=pass||budget<=0||trafficCars>=TRAFFIC.cap)continue;
      let car=carSpawn(n.r,now,!trafficSeeded);
      if(!car&&trafficSeeded&&feedBudget>0){feedBudget--;car=carFeed(n.r,now);}
      if(car)budget--;else n.shortage=0;
    }
    trafficSeeded=true;trafficStatus();
  }
`;
const OLD_FEED = '    const queue=[],seen=new Set(),start=trafficRuns.indexOf(destination);\n';
const OLD_ADVANCE = '    for(const r of trafficRuns)for(let i=r.cars.length-1;i>=0;i--) {\n';
const OLD_DRAW = '    for(const r of trafficRuns)for(const car of r.cars) {\n';
// ---- and the lines that stand in their places now
const NEW_ADVANCE = '    trafficBusySort();   // Round 225: the runs holding cars, in run order: the full walk\'s order exactly, without the 46,000 empty runs\n    for(let q=0,nq=trafficBusy.length;q<nq;q++)for(let r=trafficBusy[q],i=r.cars.length-1;i>=0;i--) {\n';
const NEW_DRAW = '    trafficBusySort();   // Round 225: the advance\'s transfers put runs on the end of the list; in run order every car keeps the instance slot the full walk gave it\n    for(const r of trafficBusy)for(const car of r.cars) {\n';

// ---- the flight: places in the scene frame (City Hall is at -1603, -802), each leg a start, a velocity, a clock and frames.
// A car is not retired until it is CAR_MIN_LIFE (16 s) old, so the second leg runs 18 s before the eye jumps away
const HALL = [-1603, -802], TOWERS = [0, 0], WEST = [-5000, -2500], NE = [8000, -14000], NW = [-5500, -10000], SOUTH = [-1900, 4300];
const LEGS = [
  // [name, x, z, height, vx, vz, vy, minutes, [y, m, d], frames, dt, night, extra, frames under JavaScriptCore]
  ['seed at City Hall, Friday 5 pm', ...HALL, 150, 0, 0, 0, 1020, [2026, 11, 13], 30, 1 / 30, 0, '', 6],
  ['east along Market Street', ...HALL, 150, 55, 6, 0, 1020, [2026, 11, 13], 90, 0.2, 0, '', 90],
  ['at the kerb by the towers', ...TOWERS, 2, 0, 0, 0, 1025, [2026, 11, 13], 60, 1 / 30, 0.4, '', 0],
  ['a jump to the Northeast: the whole fleet left behind', ...NE, 600, 0, 0, 0, 1026, [2026, 11, 13], 40, 0.1, 0, '', 20],
  ['and back, the clock at 3 am', ...WEST, 30, 12, -3, 0, 180, [2026, 11, 14], 60, 0.1, 1, '', 20],
  ['a Saturday noon from 2,500 m', ...HALL, 2500, 0, 0, 0, 720, [2026, 11, 14], 40, 0.1, 0, '', 0],
  ['closed blocks round the eye', ...SOUTH, 80, -20, -30, 0, 725, [2026, 11, 14], 70, 0.1, 0, 'close', 30],   // closed at mid-leg, on the cars standing there
  ['the time slider dragged: a reconcile a frame', ...TOWERS, 300, 5, 5, 0, 725, [2026, 11, 14], 14, 1 / 30, 0, 'drag', 5],
  ['across the city at speed, climbing', ...NW, 400, 260, 190, 12, 480, [2026, 11, 16], 75, 0.2, 0, '', 0],
  ['a sweep: a new place, height and hour every third frame', ...HALL, 100, 0, 0, 0, 480, [2026, 11, 16], 45, 0.1, 0, 'sweep', 18],
];

function main(P) {
  const THREE = P.THREE, MODE = P.mode || 'exact', now0 = P.now;
  const src = P.read('app.js');
  const cutOf = (text, a, b) => { const i = text.indexOf(a); if (i < 0) throw new Error('missing ' + a); const j = text.indexOf(b, i + a.length); if (j < 0) throw new Error('missing ' + b); return text.slice(i, j); };
  const cut = (a, b) => cutOf(src, a, b);
  const once = (text, a, b) => { if (text.split(a).length !== 2) throw new Error('not exactly once: ' + a.slice(0, 80)); return text.replace(a, () => b); };

  const helpers = cut('  function septaMerge(', '  function septaVehGeom(');
  const pageSection = cut('  // ---------------------------------------------------------------- traffic', '  // ---------------------------------------------------------------- streetlights');
  const NEW_RECONCILE = cutOf(pageSection, '  function trafficReconcile(now) {', '  const TRAFFIC_DAYS=');
  const NEW_FEED = cutOf(pageSection, '    const queue=[],seen=new Set(),start=', '\n') + '\n';
  let oldSection = once(pageSection, NEW_RECONCILE, OLD_RECONCILE);
  oldSection = once(oldSection, NEW_FEED, OLD_FEED);
  oldSection = once(oldSection, NEW_ADVANCE, OLD_ADVANCE);
  oldSection = once(oldSection, NEW_DRAW, OLD_DRAW);
  // both report their needs as sorted, through one line added after the sort (the same line in each)
  const SORT_LINE = '    needs.sort((a,b)=>b.priority-a.priority);\n';
  const tap = (text) => once(text, SORT_LINE, SORT_LINE + '    if(HOOK.needs)HOOK.needs(needs);\n');
  // the closures' step empties a block as it closes (closureTraffic, Round 207): the page's own line, cut from the closures'
  // section and stood in both sections, kills the cars on a closed run and marks them closedOut, which the advance reads
  const CLOSE_HEAD = '    for (const r of trafficRuns) if (r.closed) for (const c of r.cars) if (!c.die || !c.closedOut) {';
  if (src.split(CLOSE_HEAD).length !== 2) throw new Error('closureTraffic: the line that empties a closed run, not exactly once');
  const CLOSE_OUT = '\nfunction closeOut(now){let gone=0;\n' + cut(CLOSE_HEAD, '\n') + '\nreturn gone;}\n';
  // what is left of the new code in the old section: the two helpers' own lines and nothing that calls them
  const oldCalls = (oldSection.match(/trafficBusySort\(\)|trafficIndex\(\)/g) || []).length;

  // ---- the runs: the page's decoder and linker over the shipped traffic.b64
  function realRuns() {
    const line = (a) => cut(a, '\n') + '\n';
    const body = line('  function clamp(v, a, b) {') + line('  function lerp(a, b, t) {')
      + cut('  function densify(pts, step) {', '  // Bowyer-Watson') + cut('  function unb64(b64, name) {', '  // a real macrotask boundary') + `
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
const trenchLaneY = (x, z, base) => { const o = frontOff(x, z); if (o <= TERRAIN.trenchW || o >= TERRAIN.trenchE) return base; const eo = Math.min(o - TERRAIN.trenchW, TERRAIN.trenchE - o) / 14, ez = Math.min(z - (CORE_EXT.z0 + 4), (CORE_EXT.z1 - 4) - z) / 60, t = clamp(Math.min(eo, ez), 0, 1); return lerp(base, TERRAIN.trenchFloor + 0.55, t * t * (3 - 2 * t)); };
const bridgeDeckLift = (x, z) => Math.abs(x - 4200) < 60 && Math.abs(z + 900) < 400 ? 25 : null;
const brLaneFit = (pts) => pts;
const ovpDeckY = (x, z, ux, uz) => Math.abs(ux) > 0.85 && Math.abs((((z % 1400) + 1400) % 1400) - 700) < 30 ? hill(x, z) + 8 : null;
const sunkCutNear = (x, z) => Math.abs(z - 1500) < 40 ? hill(x, z) - 6 : null;
const ovpSunkY = () => null, trafficBridge = () => {};   // Round 226: the sunken runs' own height and the tunnels' bridging runs (none on this synthetic ground)
let TRAFFIC_B64 = B64;
const trafficRuns = [];
function decode() {
${cut("    const bin = unb64(TRAFFIC_B64, 'TRAFFIC');", '    trafficPrepareGraph(trafficRuns);')}
  return trafficRuns;
}
${cut('  function trafficPrepareGraph(runs) {', "  step('Setting the traffic flowing'")}
const runs = decode(); trafficPrepareGraph(runs); return runs;`;
    return new Function('B64', 'atob', 'performance', body)(P.read('traffic.b64').trim(), P.atob, { now: now0 });
  }

  // ---- one traffic section, live: the stubs are tests/vehicles_checks.js's, with the dice and the device handed in
  const VEHICLE_ART = JSON.parse(P.read('vehicle_art.json'));
  const setup = `
const V3=THREE.Vector3,document={getElementById:()=>null,createElement:()=>({width:0,height:0,getContext:()=>new Proxy({},{get:(t,k)=>k==='measureText'?()=>({width:10}):()=>{} ,set:()=>true})})},step=()=>{},syncLayerBtn=()=>{},postRaw=m=>m;
const camera=new THREE.PerspectiveCamera(58,1.6,.75,26000),groupCity=new THREE.Group();
const clock={y:2026,m:11,d:13,minutes:1020};
const clamp=(v,a,b)=>v<a?a:v>b?b:v,lerp=(a,b,t)=>a+(b-a)*t;
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
const hash01=n=>{const s=Math.sin(n*127.1+311.7)*43758.5453;return s-Math.floor(s);};
const ZREV={on:false},REAL=true,SNOW2_ON=true,wxSurfU={uSnowAcc:{value:0},uWet:{value:0}},LITE=false,TIER2=false,location={search:''},sunWUniform={value:new V3(0,1,0)},nightUniform={value:0},lampUniform={value:0},POST={on:false};
const isTouch=TOUCH,NEAR_R=804.67,SCORES={games:[]},SEPTA_STOPS=undefined,STREET_FURN=undefined;
const inCore=()=>false,roadHalfW=()=>4.5,groundMeshLandY=()=>0,groundMeshY=()=>0,siteY=()=>0;
const ovpSunkY=()=>null;   // Round 226: no tunnels here (trafficRunUnder answers null for every run, in both sections alike)
const _sp=new V3(),_sq=new THREE.Quaternion(),_ss=new V3(),_sm=new THREE.Matrix4(),_sc=new THREE.Color();
const flushInst=()=>{},anisoOf=n=>n,freeTexOnUpload=t=>t,artImage=()=>new Promise(()=>{}),artSrc=(a,b)=>a,lampLightPatch=()=>{throw new Error('a vehicle takes vehLampPatch, never lampLightPatch');};
const lampMapU={uLampMap:{value:null},uLampBox:{value:new THREE.Vector4()},uLampOn:{value:0},uLampFade:{value:new THREE.Vector4()}},sun={intensity:1.85},sunDir=new V3(0,1,0);
const renderer={domElement:{height:800}},CORE_EXT={x0:-640,x1:770,z0:-520,z1:850};
`;
  const EXPORT = CLOSE_OUT + 'return {closeOut,carSpotRank,TRAFFIC,CARC,CAR_VIEW,CAR_MIN_LIFE,TRAFFIC_DENSITY_KMH,CARLAMP,runs:trafficRuns,busy:trafficBusy,fleet:trafficFleet,camera,clock,trafficCreateFleet,carRefreshView,trafficReconcile,trafficAdvance,trafficDraw,'
    + 'get cars(){return trafficCars;},get frame(){return trafficFrame;}};';
  function make(section, touch, shared, seed) {
    const M = Object.create(Math); let s = seed >>> 0;
    M.random = () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; };
    const HOOK = { needs: null };
    const a = new Function('THREE', 'Math', 'VEHICLE_ART', 'HOOK', 'performance', setup.replace('TOUCH', touch ? 'true' : 'false') + helpers + tap(section) + EXPORT)(THREE, M, VEHICLE_ART, HOOK, { now: now0 });
    a.HOOK = HOOK; a.dice = () => s;
    // the linked runs, each instance its own objects (the vertex arrays are read only and shared); hi is this harness's own index
    for (let i = 0; i < shared.length; i++) { const r = shared[i]; a.runs.push({ ...r, cars: [], conn: [r.conn[0].slice(), r.conn[1].slice()], hi: i }); }
    a.trafficCreateFleet();
    a.next = 0; a.lastMin = -1; a.lastDate = ''; a.recons = 0; a.needLog = null; a.tSort = 0; a.msRecon = a.msWalks = a.msFrames = 0; a.walks = []; a.frames = [];
    HOOK.needs = (needs) => { a.tSort = now0(); a.needLog = needs.map((n) => [n.r.hi, n.shortage, n.priority]); };
    return a;
  }
  // trafficStep's own cadence: a reconcile when a second has passed, the date has changed or the clock has jumped
  // (and the stopwatch: ms in the reconciles, in their walks alone, which end where the needs are sorted, and in the advance and draw)
  function stepOne(a, now, dt, night, after) {
    a.carRefreshView();
    const dkey = a.clock.y + '-' + a.clock.m + '-' + a.clock.d, dmin = Math.abs(a.clock.minutes - a.lastMin);
    let recon = false;
    if (now >= a.next || a.lastDate !== dkey || (dmin > 2 && dmin < 1437)) {
      a.next = now + 1000; a.lastMin = a.clock.minutes; a.lastDate = dkey; a.needLog = null; a.tSort = 0;
      const t = now0(); a.trafficReconcile(now); const t1 = now0();
      a.msRecon += t1 - t; a.msWalks += a.tSort - t; a.walks.push(a.tSort - t); a.recons++; recon = true;
      if (after) after(a);
    }
    const t = now0(); a.trafficAdvance(now, Math.min(dt, 0.1)); a.trafficDraw(night); const ms = now0() - t;
    a.msFrames += ms; a.frames.push(ms);
    return recon;
  }

  // ---- the comparison: everything the functions write, value for value (Object.is: a NaN is a NaN, -0 is not 0)
  const CAR_KEYS = ['id', 'kind', 'dir', 'lane', 'off', 'jit', 's', 'v', 'x', 'y', 'z', 'yaw', 'seg', 'px', 'py', 'pz', 'heading', 'pitch', 'brk', 'alpha', 'col', 'met', 'born', 'die', 'fr', 'closedOut'];
  const CARC_KEYS = ['born', 'bornSeen', 'dieRetire', 'dieEnd', 'dieClosed', 'dieSeen', 'ageSum', 'ageN', 'ageMin', 'transfers', 'blockedBirths'];
  const stat = { bad: 0, first: null, runsCompared: 0, needsCompared: 0, carsCompared: 0, slotsCompared: 0, lampsCompared: 0 };
  const fail = (what) => { stat.bad++; if (!stat.first) stat.first = what; };
  const eqArr = (x, y, n, what) => { for (let i = 0; i < n; i++) if (!Object.is(x[i], y[i])) { fail(what + '[' + i + '] ' + x[i] + ' / ' + y[i]); return; } };
  function compareReconcile(A, B, tag) {
    if (!Object.is(A.TRAFFIC.scale, B.TRAFFIC.scale)) fail(tag + ' scale ' + A.TRAFFIC.scale + ' / ' + B.TRAFFIC.scale);
    const ra = A.runs, rb = B.runs;
    for (let i = 0; i < ra.length; i++) {
      const p = ra[i], q = rb[i];
      if (!Object.is(p.want, q.want) || !Object.is(p.target, q.target) || !Object.is(p.inbound, q.inbound)) fail(tag + ' run ' + i + ' want ' + p.want + ' / ' + q.want + ' target ' + p.target + ' / ' + q.target + ' inbound ' + p.inbound + ' / ' + q.inbound);
    }
    stat.runsCompared += ra.length;
    const na = A.needLog, nb = B.needLog;
    if (!na || !nb || na.length !== nb.length) fail(tag + ' needs ' + (na && na.length) + ' / ' + (nb && nb.length));
    else for (let k = 0; k < na.length; k++) { if (na[k][0] !== nb[k][0] || !Object.is(na[k][1], nb[k][1]) || !Object.is(na[k][2], nb[k][2])) { fail(tag + ' need ' + k + ' ' + na[k] + ' / ' + nb[k]); break; } }
    stat.needsCompared += na ? na.length : 0;
  }
  function compareFrame(A, B, tag) {
    if (A.cars !== B.cars || A.frame !== B.frame || A.dice() !== B.dice()) fail(tag + ' cars ' + A.cars + ' / ' + B.cars + ' dice ' + A.dice() + ' / ' + B.dice());
    for (const k of CARC_KEYS) if (!Object.is(A.CARC[k], B.CARC[k])) fail(tag + ' CARC.' + k + ' ' + A.CARC[k] + ' / ' + B.CARC[k]);
    const ra = A.runs, rb = B.runs; let held = 0;
    for (let i = 0; i < ra.length; i++) {
      const ca = ra[i].cars, cb = rb[i].cars;
      if (ca.length !== cb.length) { fail(tag + ' run ' + i + ' holds ' + ca.length + ' / ' + cb.length); continue; }
      if (!ca.length) continue;
      if (!rb[i].busy) fail(tag + ' run ' + i + ' holds a car off the walk');
      held += ca.length;
      for (let k = 0; k < ca.length; k++) {
        const p = ca[k], q = cb[k];
        for (const key of CAR_KEYS) if (!Object.is(p[key], q[key])) fail(tag + ' run ' + i + ' car ' + k + ' ' + key + ' ' + p[key] + ' / ' + q[key]);
        if (p.run.hi !== q.run.hi || (p.leader ? p.leader.id : 0) !== (q.leader ? q.leader.id : 0) || (p.destination ? p.destination.hi : -1) !== (q.destination ? q.destination.hi : -1)) fail(tag + ' run ' + i + ' car ' + k + ' run, leader or destination');
        const pr = p.route || [], qr = q.route || [];
        if (pr.length !== qr.length || pr.some((e, j) => e.i !== qr[j].i || e.entry !== qr[j].entry)) fail(tag + ' run ' + i + ' car ' + k + ' route');
      }
    }
    if (held !== B.cars) fail(tag + ' ' + held + ' cars on the runs, ' + B.cars + ' counted');
    stat.carsCompared += held;
    // the draw: every group's count, first rewritten colour, matrices, fades, finishes, deck flags, colours and which car holds which slot
    for (let f = 0; f < A.fleet.length; f++) for (const far of [0, 1]) {
      const ga = far ? A.fleet[f].far : A.fleet[f], gb = far ? B.fleet[f].far : B.fleet[f];
      if (!ga) continue;
      const t = tag + ' fleet ' + f + (far ? ' far' : '');
      if (ga.n !== gb.n || ga.dirty !== gb.dirty || ga.body.count !== gb.body.count || ga.body.visible !== gb.body.visible || ga.body.userData.shadeN !== gb.body.userData.shadeN) { fail(t + ' n ' + ga.n + ' / ' + gb.n + ' dirty ' + ga.dirty + ' / ' + gb.dirty); continue; }
      const n = ga.n;
      eqArr(ga.body.instanceMatrix.array, gb.body.instanceMatrix.array, n * 16, t + ' matrix');
      eqArr(ga.fade.array, gb.fade.array, n, t + ' fade');
      if (ga.ext) eqArr(ga.ext.array, gb.ext.array, n * 2, t + ' ext');
      if (ga.shk) eqArr(ga.shk.array, gb.shk.array, n, t + ' shk');
      if (ga.body.instanceColor) eqArr(ga.body.instanceColor.array, gb.body.instanceColor.array, n * 3, t + ' colour');
      for (let i = 0; i < n; i++) if (ga.slots[i].id !== gb.slots[i].id) { fail(t + ' slot ' + i); break; }
      stat.slotsCompared += n;
    }
    if (A.CARLAMP.n !== B.CARLAMP.n) fail(tag + ' lamps ' + A.CARLAMP.n + ' / ' + B.CARLAMP.n);
    else if (A.CARLAMP.pos) { eqArr(A.CARLAMP.pos, B.CARLAMP.pos, A.CARLAMP.n * 3, tag + ' lamp pos'); eqArr(A.CARLAMP.lamp, B.CARLAMP.lamp, A.CARLAMP.n * 4, tag + ' lamp'); stat.lampsCompared += A.CARLAMP.n; }
  }

  function fly(pair, touch, lite) {
    const [A, B] = pair; let now = 1000; const legs = [];
    let sd = 99; const rnd = () => { sd = (Math.imul(sd, 1664525) + 1013904223) >>> 0; return sd / 4294967296; };
    const place = (a, x, y, z, yaw) => { a.camera.position.set(x, y, z); a.camera.lookAt(x + Math.sin(yaw) * 400, y - Math.min(y, 400) * 0.9, z - Math.cos(yaw) * 400); };
    for (const [name, x0, z0, h0, vx, vz, vy, minutes, date, frames0, dt, night, extra, framesLite] of LEGS) {
      const frames = lite ? framesLite : frames0;
      if (!frames) continue;
      const before = { born: B.CARC.born, retire: B.CARC.dieRetire, transfers: B.CARC.transfers, recons: B.recons, bad: stat.bad, ms: [A.msWalks, B.msWalks, A.msRecon, B.msRecon, A.msFrames, B.msFrames] };
      let x = x0, z = z0, y = h0, min = minutes, yaw = 0.6, farRetired = 0, routed = 0, closed = 0, closedOut = 0, closingSeen = 0;
      // what the plan test passed by: a car the reconcile has just retired on a run past the warm radius
      const R = B.CAR_VIEW.warm + 1, farCount = (a) => { if (a === B) for (const r of B.busy) if ((r.mx - x) ** 2 + (r.mz - z) ** 2 >= R * R) for (const c of r.cars) if (c.die === now) farRetired++; };
      for (const a of pair) { a.clock.y = date[0]; a.clock.m = date[1]; a.clock.d = date[2]; }
      for (let f = 0; f < frames; f++) {
        now += dt * 1000; x += vx * dt; z += vz * dt; y += vy * dt; yaw += 0.01;
        if (extra === 'drag') min = (min + 7) % 1440;
        if (extra === 'sweep' && f % 3 === 0) { x = -9000 + rnd() * 19000; z = -16000 + rnd() * 22000; y = [2, 30, 150, 600, 2500][Math.floor(rnd() * 5)]; min = Math.floor(rnd() * 1440); yaw = rnd() * 6.283; }
        // the blocks close half way down the leg, as a closures file lands between two frames: two runs in three within
        // 700 m of the eye, the cars standing on them killed by the page's own line (no reconcile is forced, as on the page)
        if (extra === 'close' && f === (frames >> 1)) for (const a of pair) {
          for (const r of a.runs) { r.closed = Math.hypot(r.mx - x, r.mz - z) < 700 && r.hi % 3 !== 0; if (r.closed && a === B) closed++; }
          const gone = a.closeOut(now); if (a === B) closedOut = gone;
        }
        let recon = false;
        for (const a of pair) {
          a.clock.minutes = min; place(a, x, y, z, yaw);
          // the advance's own test, on the frame it makes it: a dying car in view that it must NOT bring back, because its block closed
          if (extra === 'close' && a === B) { a.carRefreshView(); for (const r of B.busy) for (const c of r.cars) if (c.die && c.closedOut && a.carSpotRank(c.x, c.y, c.z) === 0) closingSeen++; }
          recon = stepOne(a, now, dt, night, farCount);
        }
        const tag = (touch ? 'phone ' : 'computer ') + name + ' frame ' + f;
        if (recon) compareReconcile(A, B, tag);
        compareFrame(A, B, tag);
        for (const r of B.busy) for (const c of r.cars) if (c.route && c.route.length) routed++;
      }
      const nr = Math.max(1, B.recons - before.recons);
      legs.push({ name, frames, recons: B.recons - before.recons, born: B.CARC.born - before.born, retired: B.CARC.dieRetire - before.retire, farRetired, closed, closedOut, closingSeen, transfers: B.CARC.transfers - before.transfers, routed, cars: B.cars, busy: B.busy.length, bad: stat.bad - before.bad,
        // a call: the walks old and new, the whole reconcile old and new; a frame: the advance and draw old and new
        ms: [A.msWalks, B.msWalks, A.msRecon, B.msRecon].map((v, k) => +((v - before.ms[k]) / nr).toFixed(2)).concat([A.msFrames, B.msFrames].map((v, k) => +((v - before.ms[4 + k]) / frames).toFixed(3))) });
    }
    return legs;
  }

  const pct = (v, p) => { const s = v.slice().sort((a, b) => a - b); return +s[Math.min(s.length - 1, Math.floor(s.length * p))].toFixed(3); };
  const three = (v) => ({ best: pct(v, 0), p10: pct(v, 0.1), median: pct(v, 0.5) });
  const shared = realRuns();
  const out = { engine: P.engine, mode: MODE, runs: shared.length, km: Math.round(shared.reduce((s, r) => s + r.len, 0) / 1000), oldCalls,
    aadtMin: shared.reduce((m, r) => Math.min(m, r.aadt), Infinity), clsMax: shared.reduce((m, r) => Math.max(m, r.cls), 0) };
  if (MODE === 'exact' || MODE === 'lite') {
    for (const touch of MODE === 'lite' ? [true] : [false, true]) {
      const A = make(oldSection, touch, shared, 4242), B = make(pageSection, touch, shared, 4242);
      const legs = fly([A, B], touch, MODE === 'lite');
      let jitMax = 0, jitSum = 0; for (let i = 0; i < shared.length; i++) { const s = Math.sin(i * 7.3 * 127.1 + 311.7) * 43758.5453, h = s - Math.floor(s); jitMax = Math.max(jitMax, h); jitSum += h; }
      out[touch ? 'phone' : 'computer'] = { cap: B.TRAFFIC.cap, warm: B.CAR_VIEW.warm, legs, recons: B.recons, jitMax, jitSum, densities: B.TRAFFIC_DENSITY_KMH.length,
        indexed: B.runs.every((r, i) => r.ri === i), oldIndexed: A.runs.some((r) => r.ri !== undefined), churn: Object.assign({}, B.CARC),
        ms: { reconcileOld: +(A.msRecon / A.recons).toFixed(3), reconcileNew: +(B.msRecon / B.recons).toFixed(3), walksOld: three(A.walks), walksNew: three(B.walks), frameOld: three(A.frames), frameNew: three(B.frames) } };
    }
    Object.assign(out, stat);
  } else {
    // ms a call at a steady 5 pm over City Hall, the two taking turns so a busy machine slows both alike
    for (const touch of [false, true]) {
      const A = make(oldSection, touch, shared, 77), B = make(pageSection, touch, shared, 77);
      let now = 1000;
      const pose = (a) => { a.camera.position.set(-1603, 150, -802); a.camera.lookAt(-1200, 0, -1100); };
      for (let f = 0; f < 400; f++) { now += 100; for (const a of [A, B]) { pose(a); stepOne(a, now, 0.1, 0); } }
      const tr = [[], []], tw = [[], []], tf = [[], []];   // the whole reconcile, its walks alone (the births after them are the same code in both), and a frame's advance and draw
      for (let k = 0; k < 240; k++) {
        now += 100;
        [A, B].forEach((a, w) => {
          pose(a); a.carRefreshView();
          let t = now0(), tn = 0; a.HOOK.needs = () => { tn = now0(); };
          a.trafficReconcile(now); const t1 = now0(); tr[w].push(t1 - t); tw[w].push(tn - t);
          t = now0(); a.trafficAdvance(now, 0.1); a.trafficDraw(0); tf[w].push(now0() - t);
        });
      }
      out[touch ? 'phone' : 'computer'] = { cars: B.cars, same: A.cars === B.cars && A.dice() === B.dice(), busy: B.busy.length,
        reconcileOld: three(tr[0]), reconcileNew: three(tr[1]), walksOld: three(tw[0]), walksNew: three(tw[1]), frameOld: three(tf[0]), frameNew: three(tf[1]) };
    }
  }
  return JSON.stringify(out);
}

if (IS_NODE) {
  const fs = require('fs'), path = require('path'), ROOT = path.join(__dirname, '..');
  console.log(main({ engine: 'V8', mode: process.argv[2], THREE: require('../three.min.js'), read: (n) => fs.readFileSync(path.join(ROOT, n), 'utf8'), atob, now: () => performance.now() }));
}
// JavaScriptCore: osascript calls run() with the arguments after the script's name
function run(argv) {
  ObjC.import('Foundation');
  const root = argv[0], read = (n) => $.NSString.stringWithContentsOfFileEncodingError($.NSString.alloc.initWithUTF8String(root + '/' + n), 4, null).js;
  (0, eval)(read('three.min.js'));
  const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/', T = new Int16Array(128).fill(-1);
  for (let i = 0; i < 64; i++) T[A.charCodeAt(i)] = i;
  const b64 = (s) => { const parts = []; let o = '', acc = 0, bits = 0; for (let i = 0; i < s.length; i++) { const v = T[s.charCodeAt(i)]; if (v < 0) continue; acc = ((acc << 6) | v) & 0xffff; bits += 6; if (bits >= 8) { bits -= 8; o += String.fromCharCode((acc >> bits) & 255); if (o.length > 8192) { parts.push(o); o = ''; } } } parts.push(o); return parts.join(''); };
  return main({ engine: 'JavaScriptCore', mode: argv[1] || 'lite', THREE, read, atob: b64, now: () => Date.now() });
}
