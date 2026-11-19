// pin flash runs (Round 262): headless Chrome (Metal) over CDP drives pin_through.js (beside this file) through three scripted
// flights (south: a descent over South Philly; oldcity: a flight over Old City's blocks; turn: 12 s turning in place) on a
// phone-sized touch page at 30 fps (--desk: 1280x720 at 60 fps), then its post pass for each: through (pin-frames shown with
// the tip covered by the page's own 3 by 3 rule from the frame's own eye), throughDeep (a 5 by 5 all covered), flashes (a
// pin big, gone and big again, or the reverse, inside 6 frames), jolts (half its size or more in one frame), shownOfClear.
// The layers are seeded (stops, stations, markers, art, libraries, test closures; no live feeds unless --planes, which holds
// the test aircraft so a phone draws its near and complete images in turn).
// usage: node pin_flash.mjs <dir holding the page and art/> <page> <query> <label> <variants.json|-> [--desk] [--planes]
//          [--flights south,oldcity,turn] [--posts posts.json] [--grab oldcity:240:0]
//   variants.json: [{ lo, hi, blend, r, hide, show }, ...] handed to __dbg.pinSoft before each set of flights (a ?pinsoft=1 page)
//   posts.json: post-pass overrides scored from ONE recorded run ({ mode: 'tent'|'dil', lo, hi, blend, r }): the gate is
//     recomputed from the recorded images, so many shapes cost one flight (the CPU's state stays the page's)
//   --grab flight:frames:first writes each drawn frame as frames-<label>/f####.jpg (frames_to_mp4.swift makes a video)
//   Writes flash-<label>.json in the working directory and prints one row per run.
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, rmSync, statSync, createReadStream, existsSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import net from 'node:net';
const args = process.argv.slice(2);
const [dir, page, query, label, varPath] = args;
const DESK = args.includes('--desk'), PLANES = args.includes('--planes');
const pi = args.indexOf('--posts'), POSTS = pi >= 0 ? JSON.parse(readFileSync(args[pi + 1], 'utf8')) : [null];
const gi = args.indexOf('--grab'), GRAB = gi >= 0 ? args[gi + 1].split(':') : null;   // flight:frames[:first]
const fi = args.indexOf('--flights'), ONLY = fi >= 0 ? args[fi + 1].split(',') : null;
const variants = varPath && varPath !== '-' ? JSON.parse(readFileSync(varPath, 'utf8')) : [null];
const PM_SRC = readFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), 'pin_through.js'), 'utf8');
const freePort = () => new Promise((res) => { const sv = net.createServer(); sv.listen(0, '127.0.0.1', () => { const p = sv.address().port; sv.close(() => res(p)); }); });
const root = path.resolve(dir);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]), f = path.join(root, u);
  if (!existsSync(f) || !statSync(f).isFile()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); createReadStream(f).pipe(res);
});
const sp = await freePort();
await new Promise((r) => server.listen(sp, '127.0.0.1', r));
const W = DESK ? 1280 : 740, H = DESK ? 720 : 360;
const url = 'http://127.0.0.1:' + sp + '/' + page + '?' + query + '#t=20261119,780';
const port = await freePort(), udd = mkdtempSync(path.join(os.tmpdir(), 'p3d-flash-'));
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--remote-debugging-port=' + port, '--user-data-dir=' + udd, '--no-first-run',
  '--no-default-browser-check', '--window-size=' + W + ',' + H, '--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--use-angle=metal', '--enable-webgl', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ver = null;
for (let i = 0; i < 150 && !ver; i++) { await sleep(200); try { ver = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json(); } catch (e) {} }
const ws = new WebSocket(ver.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map(), cons = [];
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data);
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error' && cons.length < 20) cons.push(m.params.args.map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 600));
  if (m.method === 'Runtime.exceptionThrown' && cons.length < 20) cons.push('exception: ' + String(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 600));
  if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } });
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Runtime.enable'); await S('Page.enable');
if (!DESK) { await S('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 }); await S('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1.25, mobile: true }); }
else await S('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
const prefs = { septa: false, indego: false, flights: PLANES, ships: false, traffic: true, closures: true, markers: true, art: true, stops: true, stations: true, civic: true };
await S('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__held = []; window.requestAnimationFrame = (cb) => { window.__held.push(cb); return 0; };' +
  "try { localStorage.setItem('philly3d.guide', '1'); localStorage.setItem('philly3d.prefs', " + JSON.stringify(JSON.stringify(prefs)) + "); } catch (e) {}" });
const ev = async (expr) => { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error((r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text); return r.result.value; };
const t0 = Date.now();
await S('Page.navigate', { url });
for (;;) { await sleep(500); if (await ev("(() => { const b = document.getElementById('btnEnter'); return !!(b && !b.disabled && window.__dbg && window.__dbg.goFly); })()")) break; if (Date.now() - t0 > 15 * 60000) throw new Error('never ready'); }
await ev("for (const id of ['btnGuideClose', 'btnEnter']) { const el = document.getElementById(id); if (el) el.click(); } 1");
await ev('__dbg.closureTest(); 1');
const inj = await ev(PM_SRC);
await ev('__PM.fps = ' + (DESK ? 60 : 30) + '; 1');
const FL = {
  south: '__PM.fly(-1300, 170, 2400, -1300, 120, 1600, 40, -0.3, 0)',
  oldcity: '__PM.fly(-900, 130, 500, -100, 110, -300, 40, -0.3, 0.25)',
  turn: '__PM.turn(-1000, 140, 1200, -0.3, 0, 15, 12)',
};
if (GRAB) {
  const [gname, gn, g0] = GRAB, dirOut = path.join(process.cwd(), 'frames-' + label);
  const { mkdirSync } = await import('node:fs'); mkdirSync(dirOut, { recursive: true });
  await ev("__PM.frames = []; __PM.grab = (f) => __PM.frames.push(__dbg.renderer.domElement.toDataURL('image/jpeg', 0.88)); 1");
  if (PLANES) await ev('__dbg.flightTest && __dbg.flightTest(); 1');
  await ev(`(async () => { await __PM.run(${FL[gname]}.slice(${+g0 || 0}, ${(+g0 || 0) + +gn}), '${gname}'); return 1; })()`);
  const n = await ev('__PM.frames.length');
  for (let i = 0; i < n; i += 20) { const b = await ev('__PM.frames.slice(' + i + ', ' + (i + 20) + ')'); b.forEach((d, k) => writeFileSync(path.join(dirOut, 'f' + String(i + k).padStart(4, '0') + '.jpg'), Buffer.from(d.split(',')[1], 'base64'))); }
  console.log('grabbed', n, dirOut, JSON.stringify(cons.slice(0, 5)));
  ws.close(); chrome.kill(); server.close(); process.exit(0);
}
const out = { label, url, buildSecs: Math.round((Date.now() - t0) / 1000), inj, runs: [] };
for (const v of variants) {
  if (v) out.soft = await ev('__dbg.pinSoft(' + JSON.stringify(v) + ')');
  for (const [name, expr] of Object.entries(FL)) {
    if (ONLY && !ONLY.includes(name)) continue;
    if (PLANES) await ev('__dbg.flightTest && __dbg.flightTest(); 1');
    const r0 = await ev(`(async () => await __PM.run(${expr}, '${name}'))()`);
    for (const po of POSTS) {
    const p = await ev('__PM.post(' + JSON.stringify(po ? { soft: po } : {}) + ')'), r = { run: r0 }, v2 = po ? Object.assign({}, v, po) : v;
    out.runs.push({ variant: v2, flight: name, frames: r.run.frames, onScreen: p.onScreen, displayed: p.displayed, through: p.through, throughPins: p.throughPins,
      flashes: p.flashes, flashOff: p.flashOff, flashOn: p.flashOn, flashPer1k: p.flashPer1k, jolts: p.jolts, joltPer1k: p.joltPer1k, eases: p.eases, partial: p.partial, tv: p.tv,
      deep: p.deep, throughDeep: p.throughDeep, plain: p.plain, missPlain: p.missPlain, blinks: p.blinks, shownOfClear: p.shownOfClear, latCov: p.latCov, latView: p.latView, gateOff: p.gateOff });
    console.error(label, JSON.stringify(v2), name, 'through', p.through, 'flashes', p.flashes, 'jolts', p.jolts, 'onScreen', p.onScreen, 'shownOfClear', p.shownOfClear, 'thrDeep', p.throughDeep, '/', p.deep, 'missPlain', p.missPlain, '/', p.plain);
    }
  }
}
out.console = cons;
writeFileSync(path.join(process.cwd(), 'flash-' + label + '.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out.runs.map((r) => [r.variant && JSON.stringify(r.variant), r.flight, r.onScreen, r.through, r.flashes, r.jolts, r.shownOfClear])));
ws.close(); chrome.kill(); server.close();
try { rmSync(udd, { recursive: true, force: true }); } catch (e) {}
process.exit(0);
