import { readFileSync } from 'node:fs';
const snap = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const M = snap.snapshot.meta, NF = M.node_fields.length, EF = M.edge_fields.length;
const nT = M.node_types[0], eT = M.edge_types[0], S = snap.strings, N = snap.nodes, E = snap.edges;
const iType = M.node_fields.indexOf('type'), iName = M.node_fields.indexOf('name'), iSelf = M.node_fields.indexOf('self_size'), iEC = M.node_fields.indexOf('edge_count');
const eType = M.edge_fields.indexOf('type'), eName = M.edge_fields.indexOf('name_or_index'), eTo = M.edge_fields.indexOf('to_node');
const n = N.length / NF, first = new Uint32Array(n + 1);
for (let i = 0, e = 0; i < n; i++) { first[i] = e; e += N[i * NF + iEC] * EF; } first[n] = E.length;
const par = new Int32Array(n).fill(-1), parE = new Array(n);
for (let i = 0; i < n; i++) for (let e = first[i]; e < first[i + 1]; e += EF) {
  const t = eT[E[e + eType]]; if (t === 'weak') continue; const to = E[e + eTo] / NF;
  if (par[to] < 0) { par[to] = i; parE[to] = (t === 'element' || t === 'hidden') ? '[]' : S[E[e + eName]]; }
}
const nm = (i) => nT[N[i * NF + iType]] + ':' + (S[N[i * NF + iName]] || '').slice(0, 40);
function chain(i, d) { let s = nm(i), k = i; for (let q = 0; q < d && par[k] >= 0; q++) { s = nm(par[k]) + ' .' + parE[k] + ' > ' + s; k = par[k]; } return s; }
for (const [label, test] of [['closures', (i) => nT[N[i * NF + iType]] === 'closure' && !S[N[i * NF + iName]]], ['arrays', (i) => nT[N[i * NF + iType]] === 'object' && S[N[i * NF + iName]] === 'Array'], ['strings', (i) => nT[N[i * NF + iType]] === 'string'], ['numbers', (i) => nT[N[i * NF + iType]] === 'number']]) {
  const h = new Map();
  for (let i = 0; i < n; i++) if (test(i)) { let k = i; for (let q = 0; q < 2 && par[k] >= 0; q++) k = par[k]; const key = chain(i, 3).replace(/\[\d+\]/g, '[]'); h.set(key, (h.get(key) || 0) + 1); }
  console.log('== ' + label + ' by retainer chain (top 8)');
  for (const [k, v] of [...h].sort((a, b) => b[1] - a[1]).slice(0, 8)) console.log('  ' + v + '  ' + k.slice(-300));
}
