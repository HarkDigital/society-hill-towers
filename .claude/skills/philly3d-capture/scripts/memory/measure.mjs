// Live memory per build step, GC-normalized: headless Chrome over CDP loads a staged build (with the WebGL hook injected
// in the page), and at every change of the loading message forces a full GC and reads the V8 heap actually in use.
// usage: node measure.mjs <url> <label> <port>
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import path from 'node:path';
const [url, label, portArg] = process.argv.slice(2);
const port = +portArg || 9340;
const DIR = path.dirname(new URL(import.meta.url).pathname);
const udd = mkdtempSync(path.join(DIR, 'prof-' + label + '-'));
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--remote-debugging-port=' + port, '--user-data-dir=' + udd,
  '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--enable-precise-memory-info', '--no-first-run', '--no-default-browser-check', '--window-size=740,360', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ver = null;
for (let i = 0; i < 100 && !ver; i++) { await sleep(200); try { ver = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json(); } catch (e) {} }
const ws = new WebSocket(ver.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } });
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Runtime.enable'); await S('Network.enable'); await S('Page.enable'); await S('HeapProfiler.enable');
await S('Network.setBlockedURLs', { urls: ['https://*', 'wss://*'] });
await S('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
await S('Emulation.setDeviceMetricsOverride', { width: 740, height: 360, deviceScaleFactor: 1.25, mobile: true });
await S('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__held = []; const __raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = (cb) => { window.__held.push(cb); return 0; };' });
const ev = async (expr) => { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.exceptionDetails ? { __err: (r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text } : r.result.value; };
const live = async () => { await S('HeapProfiler.collectGarbage'); const h = await S('Runtime.getHeapUsage'); return Math.round(h.usedSize / 1048576); };
const gpu = async () => ev("window.__gpu ? [Math.round((__gpu.buf + __gpu.tex + __gpu.rb) / 1048576), Math.round(__gpu.misBytes / 1048576)] : -1");
const t0 = Date.now();
await S('Page.navigate', { url });
const steps = []; let last = '', ready = false, peakLive = 0, peakAt = '';
while (Date.now() - t0 < 30 * 60000) {
  await sleep(250);
  const st = await ev("(() => { const b = document.getElementById('btnEnter'); const m = document.getElementById('loadmsg'); return (b && !b.disabled ? 'READY ' : '') + (m ? m.textContent : ''); })()");
  if (typeof st !== 'string') continue;
  const key = st.replace(/, \d+%$/, '');
  if (key !== last) {
    last = key;
    const L = await live(), G = await gpu();
    steps.push([Math.round((Date.now() - t0) / 1000), L, G, key.slice(0, 44)]);
    if (L > peakLive) { peakLive = L; peakAt = key; }
    process.stderr.write(steps[steps.length - 1].join(' | ') + '\n');
  }
  if (st.startsWith('READY')) { ready = true; break; }
}
const atReady = { live: await live(), gpu: await gpu() };
// Enter and the first frames, driven by the page's own frameOnce (rAF is held)
await ev("document.getElementById('btnEnter').click(); for (let i = 0; i < 6; i++) __dbg.frameOnce(); 1");
const afterFrames = { live: await live(), gpu: await gpu() };
await ev("for (const y of [0, 1.57, 3.14, -1.57]) { __dbg.goFly(0, 300, 0, y, -0.2); for (let i = 0; i < 2; i++) __dbg.frameOnce(); } 1");
const afterLook = { live: await live(), gpu: await gpu() };
const extra = await ev("({ terr: __dbg.PERF.terrainPatches, mis: window.__gpu && __gpu.mis, failed: __dbg.PERF.failed, boot: __dbg.PERF.boot || null, pack: __dbg.PERF.pack || null, programs: __dbg.renderer.info.programs.length, tris: __dbg.renderer.info.render.triangles })");
const out = { label, ready, secs: Math.round((Date.now() - t0) / 1000), peakLive, peakAt, atReady, afterFrames, afterLook, extra, steps };
writeFileSync(path.join(DIR, 'meas-' + label + '.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify({ label, ready, secs: out.secs, peakLive, peakAt, atReady, afterFrames, afterLook, extra }, null, 1));
ws.close(); chrome.kill();
process.exit(0);
