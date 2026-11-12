// South Broad Street's median (Round 238), run for real under Node: the page's own broadMedianFit, broadMedU,
// broadMedianDraw and broadMedSlots over the wide set's streets (scene_wide.json, typed as pack_wide.py types them), with
// the page's own streetJunctions for the crossings' places, and stubs for the ground and the road mesh. Prints one JSON
// object for tests/test_broad_median.py.
const fs = require('fs'), path = require('path'), THREE = require('../three.min.js');
const ROOT = path.join(__dirname, '..');
const src = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8');
const cut = (a, b) => { const i = src.indexOf(a); if (i < 0) throw new Error('missing ' + a); const j = src.indexOf(b, i); if (j < 0) throw new Error('missing ' + b); return src.slice(i, j); };
const block = cut("  // ---- South Broad Street's median (Round 238", "  // the moving lane's sideways shift on a one-lane one-way street");
const junctions = cut('  function streetJunctions(', '  // The realistic lane shader (REAL; lanePatch hands over to it)');
const joins = cut('  const isAirfield = ', '  // an outer street\'s lane class');
const RT = { motorway: 0, motorway_link: 0, trunk: 1, trunk_link: 1, primary: 2, secondary: 3, tertiary: 4, residential: 5, living_street: 5, unclassified: 5, pedestrian: 6 };
const scene = JSON.parse(fs.readFileSync(path.join(ROOT, 'scene_wide.json'), 'utf8'));
const recs = [];
scene.roads.forEach((r, i) => { if (RT[r.t] !== undefined && r.pts.length > 1) recs.push({ pts: r.pts, w: r.w, t: RT[r.t], i, name: r.name || '' }); });
const setup = `
const REAL = true, location = { search: SEARCH }, PERF = {}, LAYER = { road: 0.24 }, COLORS = { asphalt: 0x0c0c0b };
const ROAD_COLORS = [0x0b0b0a, 0x0b0b0a, 0x0c0c0b, 0x0c0c0b, 0x0d0d0c, 0x0e0e0d];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v)), lerp = (a, b, t) => a + (b - a) * t;
const hash01 = (n) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
const streetAge = () => 1, groundMeshLandY = () => 0, groundMeshY = () => 0, siteY = () => 0, roadWeldBegin = () => {};
const roadWeld = (rc, x, y, z, fresh) => { const i = rc.n++; rc.pos.push(x, y, z); fresh(i); rc.idx.push(i); };
const drapeRouteQuad = (ring, lift, emit) => { for (const k of [0, 1, 2, 0, 2, 3]) emit(ring[k][0], ring[k][2], ring[k][1]); return true; };
const PARKED = { on: true }, PARK_FILL = { k: 1.25 }, PARK_PITCH = 6.5, PARK_JIT = 1.0;
`;
const make = (search) => new Function('THREE', 'SEARCH', setup + joins + junctions + block +
  'return { BROAD_MED_ON, BROAD_MED, BROAD_SLOTS, broadMedE, broadMedianFit, broadMedAt, broadMedU, broadMedianDraw, broadMedSlots, streetJunctions, STREET_JOINS, PERF };')(THREE, search);
const out = {};
for (const q of ['?broadmed=0', '?parkmid=1', '?real=1']) out['on' + q] = make(q).BROAD_MED_ON;
const P = make('');
const JX = P.streetJunctions(recs, P.STREET_JOINS, P.STREET_JOINS, null);
const F = P.broadMedianFit(recs, JX), M = P.BROAD_MED, A = M.a;
out.fit = P.PERF.broadMed;
out.sides = [...F.side.values()].reduce((o, v) => (o[v] = (o[v] || 0) + 1, o), {});
out.names = [...new Set([...F.side.keys()].map((ri) => recs[ri].name))];
out.blocks = F.blocks.map((b) => b.map((v) => +v.toFixed(1)));
out.half = { 1: F.half[1].length, '-1': F.half[-1].length };
// every named street over the median's line lies in a gap of the row and of both halves
const inAny = (s, list) => list.some((g) => s >= g[0] && s <= g[1]);
out.crossings = [];
recs.forEach((r) => {
  if (r.name === 'South Broad Street' || r.t > 5) return;
  for (let j = 0; j + 1 < r.pts.length; j++) {
    const a = P.broadMedAt(F, r.pts[j][0], r.pts[j][1]), b = P.broadMedAt(F, r.pts[j + 1][0], r.pts[j + 1][1]), d0 = a.lat - a.mid, d1 = b.lat - b.mid;
    if (d0 * d1 > 0 || d0 === d1) continue;
    const s = a.s + (b.s - a.s) * d0 / (d0 - d1);
    if (s < 0 || s > F.L) continue;
    const blocksOf = (bl) => bl.some((g) => s > g[0] && s < g[1]);
    out.crossings.push([r.name, +s.toFixed(1), inAny(s, F.gaps), !blocksOf(F.blocks), !blocksOf(F.half[1]), !blocksOf(F.half[-1])]);
  }
});
// the carriageways' paint: at every point of every record, u at its centre line is the edge's distance e, its kerb's u is
// the half width the shader reads, three lanes, the inner moving lane (1.6 m in, a car 1 m either side) clear of the paint
let eMin = Infinity, eMax = -Infinity, kerbErr = 0, lanes = new Set(), innerFlank = Infinity, pts = 0;
for (const [ri, sg] of F.side) {
  const r = recs[ri], hw = r.w / 2;
  for (const p of r.pts) {
    const at = P.broadMedAt(F, p[0], p[1]);
    if (at.s < 5 || at.s > F.L - 5) continue;
    const ox = F.nx * sg, oz = F.nz * sg, c = P.broadMedU(F, sg, p[0], p[1], hw), k = P.broadMedU(F, sg, p[0] + ox * hw, p[1] + oz * hw, hw);
    const inner = P.broadMedU(F, sg, p[0] - ox * 1.6, p[1] - oz * 1.6, hw);
    eMin = Math.min(eMin, c[0]); eMax = Math.max(eMax, c[0]);
    kerbErr = Math.max(kerbErr, Math.abs(k[0] - k[1]));
    lanes.add(Math.max(1, Math.floor(c[1] / 3.3 + 0.5)));
    innerFlank = Math.min(innerFlank, inner[0] - 1.0);
    pts++;
  }
}
out.paint = { pts, eMin: +eMin.toFixed(3), eMax: +eMax.toFixed(3), kerbErr: +kerbErr.toFixed(4), lanes: [...lanes], innerFlank: +innerFlank.toFixed(3) };
// the separation every sample, and the clearance between a parked van (2.1 m wide, 0.15 m off the middle) and the inner
// moving car (2 m wide, 1.6 m off its carriageway's centre line)
let clear = Infinity, mMin = Infinity, mMax = -Infinity;
for (let k = 0; k < F.N; k++) { const sp = F.sep[k], e = P.broadMedE(sp); clear = Math.min(clear, sp / 2 - 1.6 - 1.0 - 0.15 - 1.05); mMin = Math.min(mMin, sp - 2 * e); mMax = Math.max(mMax, sp - 2 * e); }
out.clear = +clear.toFixed(3); out.m = [+mMin.toFixed(2), +mMax.toFixed(2)];
// the strip: every vertex's u, half width, s and class, and its extent across the median
const rc = { pos: [], col: [], idx: [], n: 0 }, lane = [];
P.broadMedianDraw(F, rc, (v, u, s, hw, cls) => { lane[v] = [u, s, hw, cls]; }, recs);
let uMin = Infinity, uMax = -Infinity, hwMin = Infinity, hwMax = -Infinity, sMin = Infinity, clsMax = 0, mid = Infinity, outMin = Infinity, outMax = -Infinity;
for (let v = 0; v < rc.n; v++) {
  const [u, s, hw, cls] = lane[v], x = rc.pos[v * 3], z = rc.pos[v * 3 + 2], at = P.broadMedAt(F, x, z), m = at.sep - 2 * P.broadMedE(at.sep), d = Math.abs(at.lat - at.mid);
  uMin = Math.min(uMin, u + m / 2); uMax = Math.max(uMax, u); hwMin = Math.min(hwMin, hw); hwMax = Math.max(hwMax, hw); sMin = Math.min(sMin, s); clsMax = Math.max(clsMax, cls);
  if (d < 0.01) mid = Math.min(mid, Math.abs(u + m / 2));   // the middle: u is -m/2 from either half
  if (d > 1) { outMin = Math.min(outMin, d - m / 2); outMax = Math.max(outMax, d - m / 2); }
}
out.strip = { verts: rc.n, tris: rc.idx.length / 3, cols: rc.col.length / 3, uMinPlusHalf: +uMin.toFixed(3), uMax: +uMax.toFixed(3), hw: [+hwMin.toFixed(2), +hwMax.toFixed(2)], sMin: +sMin.toFixed(2), clsMax, midErr: +mid.toFixed(4), outer: [+outMin.toFixed(3), +outMax.toFixed(3)] };
// the row
const S = P.BROAD_SLOTS;
let inBlock = true, latMax = 0, fills = new Set(), yaws = [0, 0];
for (let i = 0; i < S.length; i += 6) {
  const at = P.broadMedAt(F, S[i], S[i + 1]);
  if (!F.blocks.some((b) => at.s > b[0] + 2 && at.s < b[1] - 2)) inBlock = false;
  latMax = Math.max(latMax, Math.abs(at.lat - at.mid));
  fills.add(S[i + 5]);
  yaws[Math.cos(S[i + 3]) * F.ux - Math.sin(S[i + 3]) * F.uz > 0 ? 0 : 1]++;
}
out.row = { slots: S.length / 6, inBlock, latMax: +latMax.toFixed(3), y: S[2], fillMin: +Math.min(...fills).toFixed(3), fillMax: +Math.max(...fills).toFixed(3), yaws };
console.log(JSON.stringify(out));
