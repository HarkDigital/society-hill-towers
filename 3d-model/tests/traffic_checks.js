// Actual runtime functions, evaluated with a small deterministic scene.
const fs=require('fs'),path=require('path'),THREE=require('../three.min.js');
const src=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8');
const cut=(a,b)=>{let i=src.indexOf(a);return src.slice(i,src.indexOf(b,i));};
const helpers=cut('  function septaMerge(','  function septaVehGeom(');
const traffic=cut('  // ---------------------------------------------------------------- traffic','  // ---------------------------------------------------------------- streetlights');
const setup=`
const V3=THREE.Vector3,isTouch=false,document={getElementById:()=>null},step=()=>{},syncLayerBtn=()=>{},postRaw=m=>m;
const camera=new THREE.PerspectiveCamera(58,1.6,.75,26000),groupCity=new THREE.Group();
camera.position.set(0,60,180);camera.lookAt(0,0,0);camera.updateMatrixWorld();
const clock={y:2026,m:9,d:18,minutes:750};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),lerp=(a,b,t)=>a+(b-a)*t;
const smooth=(a,b,v)=>{let t=clamp((v-a)/(b-a),0,1);return t*t*(3-2*t);};
const hash01=n=>{let s=Math.sin(n*127.1+311.7)*43758.5453;return s-Math.floor(s);};
`;
const create=new Function('THREE',setup+helpers+traffic+`return {TRAFFIC,CAR_MODELS,CARC,runs:trafficRuns,camera,clock,carGeom,carLightGeom,carRefreshView,carSpawn,carSample,carTransfer,carEntryGap,trafficPrepareGraph,trafficReconcile,trafficAdvance,carSpotRank,carOffset,carFeed,get count(){return trafficCars}};`);
const run=(pts,oneway=true,aadt=80000)=>{let len=0,cum=[0];for(let i=1;i<pts.length;i++){len+=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][2]-pts[i-1][2]);cum.push(len);}return {xs:Float32Array.from(pts.map(p=>p[0])),ys:Float32Array.from(pts.map(p=>p[1])),zs:Float32Array.from(pts.map(p=>p[2])),cum:Float32Array.from(cum),len,cls:2,oneway,aadt,mx:(pts[0][0]+pts.at(-1)[0])/2,mz:(pts[0][2]+pts.at(-1)[2])/2,cars:[],conn:[[],[]],want:0};};
let seed=517;Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
const out={};
{
 const a=create(THREE);a.TRAFFIC.cap=90;
 a.runs.push(run([[-600,0,0],[600,0,0]]),run([[600,0,0],[600,0,-350]]),run([[600,0,-350],[-600,0,-350]]),run([[-600,0,-350],[-600,0,0]]));a.trafficPrepareGraph(a.runs);a.carRefreshView();a.trafficReconcile(1000);
 const startB=a.CARC.bornSeen,startD=a.CARC.dieSeen;let maxPopulation=a.count;
 for(let frame=1;frame<=2400;frame++){const now=1000+frame*50;if(frame===900)a.clock.minutes=180;if(frame===1200){a.camera.position.set(800,90,-180);a.camera.lookAt(0,0,-175);a.carRefreshView();}if(frame%20===0)a.trafficReconcile(now);a.trafficAdvance(now,.05);maxPopulation=Math.max(maxPopulation,a.count);}
 out.simulation={cap:a.TRAFFIC.cap,maxPopulation,visibleBirths:a.CARC.bornSeen-startB,visibleDeaths:a.CARC.dieSeen-startD,transfers:a.CARC.transfers,actual:a.runs.reduce((s,r)=>s+r.cars.length,0),tracked:a.count};
}
{
 const a=create(THREE),r=[run([[-100,0,0],[100,0,0]]),run([[0,0,100],[0,0,0]])];a.trafficPrepareGraph(r);
 const high=[run([[-100,0,0],[100,0,0]]),run([[0,8,100],[0,8,0]])];a.trafficPrepareGraph(high);
 const parallel=[run([[-100,0,0],[100,0,0]]),run([[-50,0,1.8],[0,0,1.8]])];a.trafficPrepareGraph(parallel);
 const links=rr=>rr.reduce((n,r)=>n+r.conn[0].length/2+r.conn[1].length/2,0);
 out.graph={split:r.length,links:links(r),overpassLinks:links(high),parallelLinks:links(parallel)};
}
{
 const a=create(THREE),r=run([[-100,0,0],[0,0,0]]),next=run([[0,0,0],[100,0,0]]);a.runs.push(r,next);a.trafficPrepareGraph(a.runs);a.carRefreshView();
 const first=a.runs[0],car=a.carSpawn(first,1000,true),id=car.id,kind=car.kind,col=car.col;car.dir=1;
 const dest=a.carTransfer(first,0,car,7);const distance=car.s;
 dest.conn[1]=[0,1];car.dir=1;
 out.transfer={sameCar:dest.cars[0]===car&&car.id===id,sameLook:car.kind===kind&&car.col===col,distance,oneWayRefused:a.carTransfer(dest,0,car)===null};
}
{
 const a=create(THREE),r=run([[-400,0,0],[400,0,0]]);a.runs.push(r);a.carRefreshView();for(let i=0;i<60;i++)a.carSpawn(r,1000,true);
 let minGap=Infinity;for(const c of r.cars)for(const other of r.cars)if(c!==other&&c.lane===other.lane&&c.dir===other.dir)minGap=Math.min(minGap,Math.abs(c.s-other.s)-(a.CAR_MODELS[c.kind].l+a.CAR_MODELS[other.kind].l)/2);
 out.spacing={count:r.cars.length,minGap};
}
{
 const a=create(THREE);out.models=a.CAR_MODELS.map((m,i)=>{let g=a.carGeom(i),l=a.carLightGeom(i);l.computeBoundingBox();const b=g.boundingBox;return {signature:g.attributes.position.count+':'+b.max.x+':'+b.max.y,finite:Array.from(g.attributes.position.array).every(Number.isFinite),length:b.max.x-b.min.x,width:b.max.z-b.min.z,height:b.max.y,bottom:b.min.y,vertices:g.attributes.position.count,paintVertices:g.attributes.aPaint.count,fixedTrim:Array.from(g.attributes.aPaint.array).filter(v=>v===0).length,lampFront:l.boundingBox.max.x,bodyFront:b.max.x};});
}
{
 const a=create(THREE),r=run([[-400,0,0],[400,0,0]]);a.runs.push(r);a.carRefreshView();const leader=a.carSpawn(r,1000,true),follower=a.carSpawn(r,1000,true);
 for(const c of [leader,follower]){c.dir=1;c.lane=0;c.kind=1;c.off=a.carOffset(r,0);}leader.s=450;leader.jit=.12;leader.v=1.3;follower.s=430;follower.v=14;follower.jit=1;
 let minGap=Infinity;for(let i=1;i<300;i++){a.trafficAdvance(1000+i*50,.05);minGap=Math.min(minGap,leader.s-follower.s-a.CAR_MODELS[1].l);}
 out.following={minGap,followerSpeed:follower.v,freeSpeed:40/3.6};
}
{
 const a=create(THREE),r=run([[-70,0,0],[0,0,0]]);a.runs.push(r);a.carRefreshView();const c=a.carSpawn(r,1000,true);c.s=r.len-1;c.dir=1;c.v=10;
 for(let i=1;i<400;i++)a.trafficAdvance(1000+i*50,.05);
 out.deadEnd={persists:r.cars.includes(c),direction:c.dir,deaths:a.CARC.dieSeen};
}
{
 const a=create(THREE);
 for(const [lo,hi] of [[-800,-300],[-300,-100],[-100,-40],[-40,40],[40,400]])a.runs.push(run([[lo,0,0],[hi,0,0]],true,16000));
 a.trafficPrepareGraph(a.runs);a.carRefreshView();const dest=a.runs[3];
 const car=a.carFeed(dest,1000);let arrived=false,seen=0;
 if(car)for(let frame=1;frame<1800;frame++){a.trafficAdvance(1000+frame*50,.05);if(car.run===dest)arrived=true;if(a.carSpotRank(car.x,car.y,car.z)===0)seen++;}
 out.inflow={spawned:!!car,arrived,seen,visibleBirths:a.CARC.bornSeen,visibleDeaths:a.CARC.dieSeen,planned:car?.route.length};
}
console.log(JSON.stringify(out));
