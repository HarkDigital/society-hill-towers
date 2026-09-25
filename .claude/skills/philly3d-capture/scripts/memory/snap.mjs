// Heap snapshot of a staged build at the first loading message matching a pattern; summarised by constructor and by the
// largest strings. usage: node snap.mjs <url> <label> <port> <pattern>
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import path from 'node:path';
const [url, label, portArg, pat] = process.argv.slice(2);
const port = +portArg || 9360;
const DIR = path.dirname(new URL(import.meta.url).pathname);
const udd = mkdtempSync(path.join(DIR, 'snapprof-' + label + '-'));
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--remote-debugging-port=' + port, '--user-data-dir=' + udd,
  '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-first-run', '--window-size=740,360', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ver = null;
for (let i = 0; i < 100 && !ver; i++) { await sleep(200); try { ver = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json(); } catch (e) {} }
const ws = new WebSocket(ver.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map(); let chunks = [];
ws.addEventListener('message', (ev) => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } else if (m.method === 'HeapProfiler.addHeapSnapshotChunk') chunks.push(m.params.chunk); });
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);
await S('Runtime.enable'); await S('HeapProfiler.enable'); await S('Network.enable');
await S('Network.setBlockedURLs', { urls: ['https://*', 'wss://*'] });
await S('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
await S('Emulation.setDeviceMetricsOverride', { width: 740, height: 360, deviceScaleFactor: 1.25, mobile: true });
await S('Page.addScriptToEvaluateOnNewDocument', { source: 'window.requestAnimationFrame = (cb) => 0;' });
await S('Page.navigate', { url });
const re = new RegExp(pat, 'i'); const t0 = Date.now();
while (Date.now() - t0 < 10 * 60000) {
  await sleep(100);
  const r = await S('Runtime.evaluate', { expression: "(document.getElementById('loadmsg')||{}).textContent||''", returnByValue: true });
  if (re.test(r.result.value)) { console.error('at: ' + r.result.value); break; }
}
await S('HeapProfiler.collectGarbage');
await S('HeapProfiler.takeHeapSnapshot', { reportProgress: false });
const raw = chunks.join(''); writeFileSync(path.join(DIR, 'snap-' + label + '.heapsnapshot'), raw);
const snap = JSON.parse(raw);
const M = snap.snapshot.meta, F = M.node_fields, NF = F.length, types = M.node_types[0], strs = snap.strings, nodes = snap.nodes;
const iType = F.indexOf('type'), iName = F.indexOf('name'), iSelf = F.indexOf('self_size');
const by = new Map(); const bigStr = [];
for (let i = 0; i < nodes.length; i += NF) {
  const t = types[nodes[i + iType]], nm = strs[nodes[i + iName]], sz = nodes[i + iSelf];
  const key = t === 'object' || t === 'closure' || t === 'native' ? t + ':' + nm : t;
  const e = by.get(key) || [0, 0]; e[0] += sz; e[1]++; by.set(key, e);
  if ((t === 'string' || t === 'concatenated string' || t === 'sliced string') && sz > 200000) bigStr.push([sz, nm.slice(0, 60)]);
}
const top = [...by.entries()].sort((a, b) => b[1][0] - a[1][0]).slice(0, 30).map(([k, v]) => Math.round(v[0] / 1048576 * 10) / 10 + ' MB  x' + v[1] + '  ' + k);
bigStr.sort((a, b) => b[0] - a[0]);
const out = { label, total: Math.round(nodes.length / NF), top, bigStrings: bigStr.slice(0, 25).map((s) => Math.round(s[0] / 1048576 * 10) / 10 + ' MB  ' + JSON.stringify(s[1])) };
writeFileSync(path.join(DIR, 'snap-' + label + '.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
ws.close(); chrome.kill(); process.exit(0);
