// Round 220's verification: serve a built page AS philly3d.com through CDP Fetch interception (so ON_SITE holds and the page
// sends its real beacons), record every beacon the page composes, read the new PERF probes, and compare the page's own GPU
// byte accounting with the capture skill's gpuhook totals. usage: node probe_measure.mjs <dir> <page.html> <query> <label> <port> <phone|desk> [waitPerfSeconds]
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const [dir, page, query, label, portArg, device, waitArg] = process.argv.slice(2);
const port = +portArg || 9340, waitPerf = +(waitArg || 0);
const DIR = path.dirname(fileURLToPath(import.meta.url));
const udd = mkdtempSync(path.join(DIR, 'prof-' + label + '-'));
const phone = device === 'phone';
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--remote-debugging-port=' + port, '--user-data-dir=' + udd,
  '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--enable-precise-memory-info', '--no-first-run', '--no-default-browser-check', '--host-resolver-rules=MAP philly3d.com 127.0.0.1', phone ? '--window-size=740,360' : '--window-size=1280,720', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ver = null;
for (let i = 0; i < 100 && !ver; i++) { await sleep(200); try { ver = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json(); } catch (e) {} }
const ws = new WebSocket(ver.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map(); const handlers = new Map();
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); }
  else if (m.method && handlers.has(m.method)) handlers.get(m.method)(m.params, m.sessionId);
});
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Runtime.enable'); await S('Network.enable'); await S('Page.enable'); await S('HeapProfiler.enable');
await S('Network.setBlockedURLs', { urls: ['https://*', 'wss://*'] });
if (phone) {
  await S('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await S('Emulation.setDeviceMetricsOverride', { width: 740, height: 360, deviceScaleFactor: 1.25, mobile: true });
  await S('Emulation.setUserAgentOverride', { userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Safari/604.1' });
}
await S('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__held = []; const __raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = (cb) => { window.__held.push(cb); return 0; };' });
// philly3d.com resolves to this machine (host-resolver-rules) and a plain http server on <port+600> serves <dir>, so ON_SITE
// holds and the page sends its real beacons to /b (a 501 from http.server, which the page ignores): recorded here
const beacons = [];
handlers.set('Network.requestWillBeSent', (p) => { const u = p.request && p.request.url; if (u && /\/b\?/.test(u)) beacons.push({ t: Date.now(), method: p.request.method, url: u, bytes: u.length }); });
const http = spawn('python3', ['-m', 'http.server', String(port + 600), '--bind', '127.0.0.1'], { cwd: dir, stdio: 'ignore' });
await sleep(800);
const ev = async (expr) => { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.exceptionDetails ? { __err: (r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text } : r.result.value; };
const live = async () => { await S('HeapProfiler.collectGarbage'); const h = await S('Runtime.getHeapUsage'); return Math.round(h.usedSize / 1048576); };
const gpu = async () => ev("window.__gpu ? { hook: Math.round((__gpu.buf + __gpu.tex + __gpu.rb) / 1048576), hookBuf: Math.round(__gpu.buf / 1048576), hookTex: Math.round(__gpu.tex / 1048576), hookRb: Math.round(__gpu.rb / 1048576), page: (window.__dbg && __dbg.PERF && __dbg.PERF.gpuMem) ? __dbg.PERF.gpuMem() : null } : -1");
const t0 = Date.now();
const url = 'http://philly3d.com:' + (port + 600) + '/' + page + (query ? '?' + query : '');
await S('Page.navigate', { url });
const steps = []; let last = '', ready = false;
while (Date.now() - t0 < 12 * 60000) {
  await sleep(250);
  const st = await ev("(() => { const b = document.getElementById('btnEnter'); const m = document.getElementById('loadmsg'); return (b && !b.disabled ? 'READY ' : '') + (m ? m.textContent : ''); })()");
  if (typeof st !== 'string') continue;
  const key = st.replace(/, \d+%$/, '');
  if (key !== last) { last = key; steps.push([Math.round((Date.now() - t0) / 1000), key.slice(0, 44)]); process.stderr.write(steps[steps.length - 1].join(' | ') + '\n'); }
  if (st.startsWith('READY')) { ready = true; break; }
  if (/^Error/.test(key)) break;
}
const errors = await ev("(window.__errs || [])");
const atReady = { live: await live(), gpu: await gpu() };
const perfReady = await ev("(() => { const P = __dbg.PERF; const pick = (o, ks) => { const r = {}; for (const k of ks) if (o && o[k] !== undefined) r[k] = typeof o[k] === 'function' ? o[k]() : o[k]; return r; }; return pick(P, ['far', 'wide', 'fit', 'sch', 'triNear', 'roofKitNote', 'streetLabels', 'traffic', 'flush', 'staged', 'frame1Ms', 'steps', 'failed', 'readyMs']); })()");
const tskin = await ev("(() => { try { return typeof TSKIN !== 'undefined' ? TSKIN.ms : (window.__dbg.fronts ? __dbg.fronts().towers : null); } catch (e) { return String(e); } })()");
// Enter and the first frames, driven by the page's own frameOnce (rAF is held)
await ev("document.getElementById('btnEnter').click(); for (let i = 0; i < 6; i++) __dbg.frameOnce(); 1");
const afterFrames = { live: await live(), gpu: await gpu() };
await ev("for (const y of [0, 1.57, 3.14, -1.57]) { __dbg.goFly(0, 300, 0, y, -0.2); for (let i = 0; i < 2; i++) __dbg.frameOnce(); } 1");
const afterLook = { live: await live(), gpu: await gpu() };
const gput = await ev("(() => { try { return { gpu: window.__dbg.gpu ? __dbg.gpu() : null, beacon: (typeof gputBeacon === 'function') ? gputBeacon() : 'n/a' }; } catch (e) { return String(e); } })()");
if (waitPerf > 0) { await sleep(waitPerf * 1000); for (let i = 0; i < 3; i++) await ev("__dbg.frameOnce(); 1"); await sleep(1500); }
const afterPerf = { live: await live(), gpu: await gpu() };
const stepBeacons = beacons.filter((b) => /st=step/.test(b.url)).length;
const out = { label, url, ready, secs: Math.round((Date.now() - t0) / 1000), errors, atReady, afterFrames, afterLook, afterPerf, perfReady, tskin, gput, beacons: beacons.map((b) => ({ method: b.method, bytes: b.bytes, q: Object.fromEntries(new URL(b.url).searchParams) })), stepBeacons, steps };
writeFileSync(path.join(DIR, 'measure-' + label + '.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify({ label, ready, secs: out.secs, errors, atReady, afterFrames, afterLook, afterPerf, perfReady, tskin, gput, beaconCount: beacons.length, stepBeacons, kinds: beacons.map((b) => new URL(b.url).searchParams.get('st')).filter((s) => !/^step/.test(s)), longest: Math.max(0, ...beacons.map((b) => b.bytes)) }, null, 1));
ws.close(); chrome.kill(); http.kill();
