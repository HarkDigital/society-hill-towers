// Headless captures of a staged Philly3D build, for work that cannot share the Browser pane (parallel agents, before and
// after sets). Serves a folder itself on a free port (or takes a URL), launches its own headless Chrome over CDP on the
// Mac's GPU, loads the page, waits for Ready, enters, and for each pose sets the clock, flies there, drives frames with
// the page's own frameOnce (rAF is held), and saves the canvas as a JPEG. At most three renders run at once on this
// machine (a page takes 2 to 3 GB): a fourth waits for a slot.
//
// usage: node render.mjs --dir <folder holding the page and its art/> --page society-hill-towers.html --poses <poses.json>
//                        --out <outdir> [--query "dev=1&dpr=1"] [--w 1280] [--h 800] [--frames 24] [--gpu metal|swiftshader]
//    or: node render.mjs <url> <poses.json> <outdir> [same options]
//   poses.json: [{ "name": "oldcity-day", "pos": [x, y, z], "yaw": rad, "pitch": rad, "clock": [2026, 10, 12, 840] }, ...]
//     or { "name", "pos", "look": [x, y, z], "clock" } to aim at a point. clock minutes are Philadelphia local; add
//     "js": "<expression>" to run in the page before the frames (a weather preset, a toggle).
//   --eval <file.js> runs that file's expression in the page after the last pose and prints its value (a probe).
//   --png saves lossless PNGs (for flicker_diff.py) in place of the JPEGs.
//   --touch emulates a phone (touch points, mobile metrics, pixel ratio 1.25): the page's isTouch path; use --w 740 --h 360.
//   Prints a JSON summary (files written, PERF.failed, the page's first 40 console warnings and errors, ms per pose).
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, mkdirSync, rmSync, statSync, createReadStream, existsSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import net from 'node:net';
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const pos0 = args.filter((a, i) => !a.startsWith('--') && !(i > 0 && args[i - 1].startsWith('--')));
const PNG = args.includes('--png');   // lossless captures (flicker_diff.py: a jpeg's own noise swamps the count)
const W = +opt('w', 1280), H = +opt('h', 800), gpu = opt('gpu', 'metal'), FR = +opt('frames', 24);
const freePort = () => new Promise((res) => { const sv = net.createServer(); sv.listen(0, '127.0.0.1', () => { const p = sv.address().port; sv.close(() => res(p)); }); });
let url = pos0[0], posesPath = pos0[1], outdir = pos0[2], server = null;
if (opt('dir')) {
  const root = path.resolve(opt('dir')), page = opt('page', 'society-hill-towers.html');
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.css': 'text/css', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };
  server = http.createServer((req, res) => {
    const u = decodeURIComponent(req.url.split('?')[0]), f = path.join(root, u);
    if (!f.startsWith(root) || !existsSync(f) || !statSync(f).isFile()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); createReadStream(f).pipe(res);
  });
  const sp = await freePort();
  await new Promise((r) => server.listen(sp, '127.0.0.1', r));
  url = 'http://127.0.0.1:' + sp + '/' + page + '?' + opt('query', 'dev=1&dpr=1');
  posesPath = opt('poses'); outdir = opt('out');
}
if (!url || !posesPath || !outdir) { console.error('usage: node render.mjs --dir <folder> --page <file> --poses <poses.json> --out <outdir> [--query ...]'); process.exit(2); }
// a slot: three renders at once on this machine
const SLOTS = 3, slotBase = path.join(os.tmpdir(), 'p3d-render-slot-');
let slot = null;
for (let tries = 0; slot === null; tries++) {
  for (let k = 0; k < SLOTS && slot === null; k++) {
    const d = slotBase + k;
    try { mkdirSync(d); slot = d; } catch (e) { try { if (Date.now() - statSync(d).mtimeMs > 20 * 60000) rmSync(d, { recursive: true, force: true }); } catch (e2) {} }
  }
  if (slot === null) { if (tries % 30 === 0) console.error('waiting for a render slot'); await new Promise((r) => setTimeout(r, 2000)); }
}
const releaseSlot = () => { try { rmSync(slot, { recursive: true, force: true }); } catch (e) {} };
process.on('exit', releaseSlot);
const port = +opt('port', 0) || await freePort();
const poses = JSON.parse(readFileSync(posesPath, 'utf8'));
mkdirSync(outdir, { recursive: true });
const udd = mkdtempSync(path.join(os.tmpdir(), 'p3d-render-'));
const flags = ['--headless=new', '--remote-debugging-port=' + port, '--user-data-dir=' + udd, '--no-first-run', '--no-default-browser-check',
  '--window-size=' + W + ',' + H, '--ignore-gpu-blocklist', '--enable-gpu-rasterization'];
if (gpu === 'swiftshader') flags.push('--use-angle=swiftshader', '--enable-unsafe-swiftshader'); else flags.push('--use-angle=metal', '--enable-webgl');
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [...flags, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ver = null;
for (let i = 0; i < 150 && !ver; i++) { await sleep(200); try { ver = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json(); } catch (e) {} }
if (!ver) { console.error('chrome did not start'); releaseSlot(); process.exit(1); }
const ws = new WebSocket(ver.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
const consoleErr = [];   // the page's warnings and errors (a shader that fails to compile says so only here)
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data);
  if (m.method === 'Runtime.consoleAPICalled' && (m.params.type === 'error' || m.params.type === 'warning') && consoleErr.length < 40)
    consoleErr.push(m.params.type + ': ' + m.params.args.map((a) => (a.value !== undefined ? String(a.value) : a.description || '')).join(' ').slice(0, 1500));
  if (m.method === 'Runtime.exceptionThrown' && consoleErr.length < 40) consoleErr.push('exception: ' + String((m.params.exceptionDetails.exception && m.params.exceptionDetails.exception.description) || m.params.exceptionDetails.text).slice(0, 1500));
  if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } });
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Runtime.enable'); await S('Page.enable');
if (args.includes('--touch')) {   // a phone: touch points and mobile metrics, so the page takes its isTouch path (fewer trees, half textures, no post)
  await S('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await S('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1.25, mobile: true });
} else await S('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
// rAF held: frames are driven by __dbg.frameOnce, so a capture is exactly the frame drawn
await S('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__held = []; window.requestAnimationFrame = (cb) => { window.__held.push(cb); return 0; };' +
  "try { localStorage.setItem('philly3d.guide', '1'); } catch (e) {}" });
const ev = async (expr) => { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.exceptionDetails ? { __err: (r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text } : r.result.value; };
const t0 = Date.now();
await S('Page.navigate', { url });
let ready = false;
while (Date.now() - t0 < 20 * 60000) {
  await sleep(500);
  const st = await ev("(() => { const b = document.getElementById('btnEnter'); return !!(b && !b.disabled && window.__dbg && window.__dbg.goFly); })()");
  if (st === true) { ready = true; break; }
}
if (!ready) { console.error('page never became ready'); chrome.kill(); if (server) server.close(); process.exit(1); }
const buildSecs = Math.round((Date.now() - t0) / 1000);
await ev("for (const id of ['btnGuideClose', 'btnEnter']) { const el = document.getElementById(id); if (el) el.click(); } for (const id of ['btnTransit', 'btnIndego']) { const el = document.getElementById(id); if (el && el.classList.contains('on')) el.click(); } 1");
const out = [];
for (const p of poses) {
  const t1 = Date.now();
  const clock = p.clock || [2026, 10, 12, 780];
  let yaw = p.yaw, pitch = p.pitch;
  if (p.look) { const dx = p.look[0] - p.pos[0], dy = p.look[1] - p.pos[1], dz = p.look[2] - p.pos[2]; yaw = Math.atan2(dx, -dz); pitch = Math.atan2(dy, Math.hypot(dx, dz)); }
  await ev(`__dbg.setClock(${clock.join(',')}); __dbg.goFly(${p.pos.join(',')}, ${yaw}, ${pitch}); 1`);
  if (p.js) await ev(p.js);
  // frames with a task between them, so asynchronous loads (art, readbacks) land
  for (let i = 0; i < FR; i++) { await ev('__dbg.frameOnce(); 1'); await sleep(i < 4 ? 250 : 60); }
  const data = await ev(PNG ? "(() => { __dbg.frameOnce(); return __dbg.renderer.domElement.toDataURL('image/png'); })()" : "(() => { __dbg.frameOnce(); return __dbg.renderer.domElement.toDataURL('image/jpeg', 0.9); })()");
  if (typeof data !== 'string') { out.push({ name: p.name, error: data && data.__err }); continue; }
  const f = path.join(outdir, p.name + (PNG ? '.png' : '.jpg'));
  writeFileSync(f, Buffer.from(data.split(',')[1], 'base64'));
  out.push({ name: p.name, file: f, ms: Date.now() - t1 });
}
const failed = await ev('__dbg.PERF.failed');
const evalOut = opt('eval') ? await ev(readFileSync(opt('eval'), 'utf8')) : undefined;   // --eval <file.js>: an expression run after the poses, its value printed
console.log(JSON.stringify({ url, buildSecs, failed, console: consoleErr, eval: evalOut, shots: out }, null, 1));
ws.close(); chrome.kill(); if (server) server.close();
try { rmSync(udd, { recursive: true, force: true }); } catch (e) {}
process.exit(0);
