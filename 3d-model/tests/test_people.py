"""Round 227: the walkers' core (app.js, '// ---- people on the sidewalks'), the page's own text under Node.

The section is cut from app.js with the traffic step's decoder, the linker, the street grid and the parked cars' deck
test (tests/_people_node.py), and run on the real traffic.b64 and people_walk.b64. What is held:
  - the walk is a permutation of the half edges and every face closes (the walkers' own nodes: where two runs cross in
    the middle of both, which the traffic's linker does not join);
  - every side of every piece on the network traces to a trail or to nobody; nobody on a motorway or a trunk road, a
    deck, a closed block, or the strip between two carriageways; no point of any trail on a drawn street; a face too
    long to walk round gives each piece its own out-and-back trail;
  - a slot is a function of the trail and the second alone: the same t gives the same walkers, whatever was traced
    first, and a slot is back in its place after its own period;
  - the fill's contract: the stride, the cap, the radius, the fades, nothing above 60 m, the height at the walker's own
    line, presence by the clock and the weather and changed only off the screen, and no allocation a call;
  - without ?people=1 (and on tier 2) the section is inert and the decoder's runs are what they were."""
import re
import sys
import unittest
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _people_node as pn   # noqa: E402

ROOT = pn.ROOT
BANNER, END = '  // ---- people on the sidewalks (Round 227', '  // ---- people on the sidewalks: the section ends'

# the half edges' orbits, walked with the page's own peopleNext and no cap: what the capped trace must agree with
ORBITS = r'''
function orbits(A) {
  const P = A.PEOPLE, runs = A.runs, N = runs.length;
  for (let i = 0; i < N; i++) A.peopleCross(i);
  const H = P.nPieces * 2, nxt = new Int32Array(H), hr = new Int32Array(H), hk = new Int32Array(H), plen = new Float64Array(H);
  let turns = 0;
  for (let i = 0; i < N; i++) for (let k = 0; k <= P.xN[i]; k++) for (let b = 0; b < 2; b++) {
    const id = (P.pieceBase[i] + k) * 2 + b; hr[id] = i; hk[id] = k;
    A.peopleNext(i, k, b ? -1 : 1); const n = A.next(); nxt[id] = (P.pieceBase[n.ri] + n.k) * 2 + (n.d < 0 ? 1 : 0); if (n.turn) turns++;
  }
  const hit = new Int32Array(H); for (let h = 0; h < H; h++) hit[nxt[h]]++;
  let notPerm = 0; for (let h = 0; h < H; h++) if (hit[h] !== 1) notPerm++;
  const face = new Int32Array(H).fill(-1), faces = []; let unclosed = 0;
  for (let h0 = 0; h0 < H; h0++) {
    if (face[h0] >= 0) continue;
    let h = h0, Pm = 0, area = 0, n = 0, closed = false, px = 0, pz = 0, fx = 0, fz = 0, first = true, turn = false, longest = 0;
    for (let g = 0; g < 2 * H; g++) {
      face[h] = faces.length;
      const len = A.peoplePiece(hr[h], hk[h], h & 1 ? -1 : 1, 0), Q = A.piece(); plen[h] = len; Pm += len; n++; longest = Math.max(longest, len);
      for (let j = 0; j < Q.n; j++) { if (first) { fx = Q.x[0]; fz = Q.z[0]; first = false; } else area += px * Q.z[j] - Q.x[j] * pz; px = Q.x[j]; pz = Q.z[j]; }
      if (nxt[h] === (h ^ 1)) turn = true;
      h = nxt[h]; if (h === h0) { closed = true; break; } if (face[h] >= 0) break;
    }
    if (!closed) unclosed++;
    faces.push({ P: Pm, A: Math.abs(area + px * fz - fx * pz) / 2, n, turn, longest });
  }
  return { H, nxt, hr, hk, plen, face, faces, notPerm, unclosed, turns };
}
'''

GRAPH = ORBITS + r'''
const A = make({}); A.boot(); A.peopleInit();
const P = A.PEOPLE, runs = A.runs, N = runs.length, O = orbits(A);
let dead = 0, cross = 0; for (let i = 0; i < N; i++) { cross += P.xN[i]; for (let e = 0; e < 2; e++) if (!runs[i].conn[e].length) dead++; }
traceAll(A);
let untraced = 0, on01 = 0, medianWalked = 0, medians = 0, giantNotSolo = 0, giantSides = 0, giantWalked = 0, walkLen = 0, kerbLen = 0;
for (let h = 0; h < O.H; h++) {
  const r = runs[O.hr[h]], tid = P.sideTrail[h], f = O.faces[O.face[h]];
  if (tid === -1) untraced++;
  if (r.cls >= 2) { kerbLen += O.plen[h]; if (tid >= 0) walkLen += O.plen[h]; }
  if (tid >= 0 && r.cls < 2) on01++;
  if (!f.turn && 2 * f.A / f.P < P.medianW) { medians++; if (tid >= 0) medianWalked++; }
  if (f.n > P.faceMax || f.P > P.faceCap + f.longest) { giantSides++; if (tid >= 0) { giantWalked++; const T = P.trails[tid]; if (T.closed || T.len > O.plen[h] * 1.3 + 10) giantNotSolo++; } }
}
let loops = 0, shuttles = 0, nan = 0, inStreet = 0, badPeriod = 0, maxSlots = 0, maxLen = 0, slots = 0, pts = 0, shortTrail = 0, notRising = 0;
for (const T of P.trails) {
  if (T.closed) loops++; else shuttles++;
  if (Math.abs(T.P - (T.closed ? T.len : 2 * T.len)) > 1e-6) badPeriod++;
  if (T.len < 6) shortTrail++;
  maxSlots = Math.max(maxSlots, T.n); maxLen = Math.max(maxLen, T.len); slots += T.n; pts += T.xs.length;
  for (let j = 0; j < T.xs.length; j++) { if (!isFinite(T.xs[j] + T.ys[j] + T.zs[j] + T.cum[j])) nan++; if (A.streetInside(T.xs[j], T.zs[j], 0)) inStreet++; if (j && !(T.cum[j] > T.cum[j - 1])) notRising++; }
  if (T.closed && Math.hypot(T.xs[0] - T.xs[T.xs.length - 1], T.zs[0] - T.zs[T.zs.length - 1]) > 1e-6) badPeriod++;
}
console.log(JSON.stringify({ runs: N, crossings: cross / 2, pieces: P.nPieces, dead, turns: O.turns, notPerm: O.notPerm, unclosed: O.unclosed, faces: O.faces.length, untraced, on01, medians, medianWalked, giantSides, giantWalked, giantNotSolo,
  loops, shuttles, nan, inStreet, badPeriod, shortTrail, notRising, maxSlots, maxLen, slots, pts, walkShare: walkLen / kerbLen, sides: Array.from(P.sides), corners: Array.from(P.corners), dropped: P.stat.dropped }));
'''

ROUGH = r'''
const A = make({ rough: true }); A.boot(); A.peopleInit();
const P = A.PEOPLE, runs = A.runs, N = runs.length;
const tally = () => { let onDeck = 0, deckRuns = 0, on01 = 0, onClosed = 0, untraced = 0, walked = 0, inStreet = 0;
  for (let i = 0; i < N; i++) { const r = runs[i], deck = !A.parkedRunOK(r); if (deck) deckRuns++; for (let k = 0; k <= P.xN[i]; k++) for (let b = 0; b < 2; b++) { const tid = P.sideTrail[(P.pieceBase[i] + k) * 2 + b]; if (tid === -1) untraced++; if (tid >= 0) { walked++; if (deck) onDeck++; if (r.cls < 2) on01++; if (r.closed) onClosed++; } } }
  for (const T of P.trails) for (let j = 0; j < T.xs.length; j++) if (A.streetInside(T.xs[j], T.zs[j], 0)) inStreet++;
  return { onDeck, deckRuns, on01, onClosed, untraced, walked, inStreet, trails: P.trails.length }; };
traceAll(A); const open = tally();
// close every seventh walked run, as a closures file would
let closed = 0; for (let i = 0; i < N; i += 7) if (runs[i].cls >= 2) { runs[i].closed = true; closed++; }
const gen0 = P.gen; A.peopleClosed(); const reset = P.gen - gen0, cleared = P.trails.length;
traceAll(A); const shut = tally();
A.peopleClosed(); const same = P.gen - gen0;   // the same closures again: nothing is thrown away
for (let i = 0; i < N; i++) runs[i].closed = false;
A.peopleClosed(); traceAll(A); const again = tally();
console.log(JSON.stringify({ runs: N, open, closed, reset, cleared, shut, same, reopened: P.gen - gen0, again }));
'''

FILL = r'''
const key = (out, n) => { const rows = []; for (let i = 0; i < n; i++) rows.push(Array.from(out.subarray(i * 8, i * 8 + 8)).map((v) => v.toFixed(4)).join(',')); return rows.sort().join(';'); };
const SLOPE = (x, z) => 0.01 * x + 3;   // a ground that tilts across the streets: the height must be read at the walker's own line
const A = make({ furnY: SLOPE }); A.boot();
const P = A.PEOPLE, out = new Float32Array(P.cap * P.stride), out2 = new Float32Array(P.cap * P.stride);
const POSE = [[-1603, -802], [-2000, -330], [-1700, 2600]], eyeY = (x, z) => SLOPE(x, z) + 2;
A.clock.d = 14; A.clock.minutes = 13 * 60; A.peoplePin(5000000);   // a Saturday at one: every slot present
const o = { on: A.PEOPLE_ON, stride: P.stride, cap: P.cap, r: P.r, shareFull: A.peopleShare() };
const [px, pz] = POSE[0];
const n1 = settle(A, out, px, eyeY(px, pz), pz), n2 = A.peopleFill(out2, px, eyeY(px, pz), pz);
o.n = n1; o.sameT = n1 === n2 && key(out, n1) === key(out2, n2);
// the contract, walker by walker
let far = 0, unit = 0, fig = 0, phase = 0, fadeBad = 0, edge = 0, mid = 0, yOff = 0, inStreet = 0;
for (let i = 0; i < n1; i++) {
  const x = out[i * 8], y = out[i * 8 + 1], z = out[i * 8 + 2], hx = out[i * 8 + 3], hz = out[i * 8 + 4], f = out[i * 8 + 5], ph = out[i * 8 + 6], fade = out[i * 8 + 7];
  const d = Math.hypot(x - px, y - eyeY(px, pz), z - pz);
  if (d > P.r + 1e-3) far++;
  if (Math.abs(Math.hypot(hx, hz) - 1) > 1e-3) unit++;
  if (f !== Math.floor(f) || f < 0 || f >= P.figures) fig++;
  if (!(ph >= 0 && ph < 1)) phase++;
  if (!(fade >= 0 && fade <= 1)) fadeBad++;
  if (d > 0.99 * P.r && fade > 0.01) edge++;
  if (d > 4 && d < 0.8 * P.r && Math.abs(fade - 1) > 1e-6) mid++;
  if (Math.abs(y - SLOPE(x, z)) > 0.02) yOff++;
  if (A.streetInside(x, z, 0)) inStreet++;
}
Object.assign(o, { far, unit, fig, phase, fadeBad, edge, mid, yOff, inStreet, present: P.stat.present, slots: P.stat.slots });
// a slot is back in its place after its own period: the place worked out here from the trail's own arrays, and found in the fill
const place = (T, k, t) => {
  const per = T.P, v = T.v[k]; let s = T.s0[k] + v * t, dir = v < 0 ? -1 : 1; s -= per * Math.floor(s / per); if (!T.closed && s > T.len) { s = per - s; dir = -1; }
  let j = 0; while (j < T.cum.length - 2 && T.cum[j + 1] <= s) j++;
  const sl = T.cum[j + 1] - T.cum[j], u = (s - T.cum[j]) / sl, hx = (T.xs[j + 1] - T.xs[j]) / sl * dir, hz = (T.zs[j + 1] - T.zs[j]) / sl * dir, w = T.lat[k] / 255 * P.lat;
  return [T.xs[j] + (T.xs[j + 1] - T.xs[j]) * u - hz * w, T.zs[j] + (T.zs[j + 1] - T.zs[j]) * u + hx * w, hx, hz];
};
const found = (buf, n, p) => { for (let i = 0; i < n; i++) if (Math.hypot(buf[i * 8] - p[0], buf[i * 8 + 2] - p[1]) < 0.02 && Math.hypot(buf[i * 8 + 3] - p[2], buf[i * 8 + 4] - p[3]) < 0.01) return true; return false; };
let checked = 0, missed = 0, moved = 0, wrongHalf = 0, kinds = [0, 0];
for (const T of P.trails) for (let k = 0; k < T.n && checked < 400; k++) {
  const p = place(T, k, 5000000);
  if (Math.hypot(p[0] - px, p[1] - pz) > P.r * 0.75) continue;   // well inside the circle, so the fill must hold it
  checked++; kinds[T.closed ? 0 : 1]++;
  if (!found(out, n1, p)) missed++;
  const t2 = 5000000 + T.P / Math.abs(T.v[k]), q = place(T, k, t2);
  if (Math.hypot(q[0] - p[0], q[1] - p[1]) > 0.02) moved++;
  A.peoplePin(t2); const m = A.peopleFill(out2, px, eyeY(px, pz), pz); if (!found(out2, m, p)) missed++;
  // and half a period on it is somewhere else (or, on an out-and-back trail, on its way back)
  const h = place(T, k, 5000000 + T.P / Math.abs(T.v[k]) / 2); if (Math.hypot(h[0] - p[0], h[1] - p[1]) < 0.02 && T.len > 20 && h[2] * p[2] + h[3] * p[3] > 0.9) wrongHalf++;
}
A.peoplePin(5000000);
Object.assign(o, { checked, missed, moved, wrongHalf, kinds });
// whatever was traced first: a second page that came to this corner last holds the same walkers
const B = make({ furnY: SLOPE }); B.boot(); B.clock.d = 14; B.clock.minutes = 13 * 60; B.peoplePin(5000000);
const ob = new Float32Array(P.cap * P.stride);
settle(B, ob, POSE[2][0], eyeY(...POSE[2]), POSE[2][1]); settle(B, ob, POSE[1][0], eyeY(...POSE[1]), POSE[1][1]); settle(B, ob, px + 300, eyeY(px + 300, pz - 250), pz - 250);
const nb = settle(B, ob, px, eyeY(px, pz), pz);
o.sameWhateverOrder = nb === n1 && key(ob, nb) === key(out, n1);
// height: nothing over 60 m, and the last 12 m of it fade
o.high = A.peopleFill(out2, px, SLOPE(px, pz) + 61, pz);
const nh = A.peopleFill(out2, px, SLOPE(px, pz) + 54, pz); let hmax = 0; for (let i = 0; i < nh; i++) hmax = Math.max(hmax, out2[i * 8 + 7]); o.fade54 = [nh, hmax];
// a caller's own radius and cap
const n80 = A.peopleFill(out2, px, eyeY(px, pz), pz, 80, 600); let far80 = 0; for (let i = 0; i < n80; i++) if (Math.hypot(out2[i * 8] - px, out2[i * 8 + 1] - eyeY(px, pz), out2[i * 8 + 2] - pz) > 80.001) far80++;
o.r80 = [n80, far80, n80 < n1];
const nc0 = A.peopleFill(out2, px, eyeY(px, pz), pz, 150, 10); let nc = 0; for (let i = 0; i < 60; i++) nc = A.peopleFill(out2, px, eyeY(px, pz), pz, 150, 10); o.capped = [nc0, nc <= 10 && nc >= 5, P.rk < 1]; P.rk = 1;
// presence: the hour's share, the weekday, the rain; and a slot comes or goes only off the screen
A.clock.d = 10; A.clock.minutes = 17 * 60; const wd = A.peopleShare(); A.WXFX.rain = 0.6; const wet = A.peopleShare(); A.WXFX.rain = 0; A.clock.minutes = 3 * 60; const night = A.peopleShare();
o.share = [wd, wet / wd, night];
A.clock.d = 14; A.clock.minutes = 13 * 60; A.peopleFill(out, px, eyeY(px, pz), pz); const full = P.stat.present;
A.clock.minutes = 3 * 60; A.VIEW.rank = 0; A.VIEW.calls = 0; A.VIEW.refresh = 0; A.peopleFill(out, px, eyeY(px, pz), pz); const watched = P.stat.present, asked = A.VIEW.calls, refreshed = A.VIEW.refresh;
A.VIEW.rank = 2; A.peopleFill(out, px, eyeY(px, pz), pz); const unseen = P.stat.present;
A.clock.minutes = 13 * 60; A.VIEW.rank = 0; A.peopleFill(out, px, eyeY(px, pz), pz); const stillGone = P.stat.present; A.VIEW.rank = 2; A.peopleFill(out, px, eyeY(px, pz), pz); const back = P.stat.present;
o.flip = { full, watched, asked, refreshed, unseen, stillGone, back, slots: P.stat.slots };
// the switch and the count
const d0 = A.peopleDbg(); A.peopleDbg(false); const off = A.peopleFill(out, px, eyeY(px, pz), pz); const d1 = A.peopleDbg(true); const onAgain = A.peopleFill(out, px, eyeY(px, pz), pz);
o.dbg = { keys: Object.keys(d0).join(), fill: Object.keys(d0.fill).join(), near: !!d0.near, loops: d0.loops, shuttles: d0.shuttles, off, live: d1.live, onAgain, pinned: d0.t };
// no allocation a call, once the streets near are traced: 20,000 fills
if (global.gc) { global.gc(); global.gc(); const h0 = process.memoryUsage().heapUsed; for (let i = 0; i < 20000; i++) { A.peoplePin(5000000 + i / 30); A.peopleFill(out, px + (i % 50) * 0.2, eyeY(px, pz), pz); } global.gc(); global.gc(); o.heapGrowth = process.memoryUsage().heapUsed - h0; }
// the cost, three times the density (about 500 walkers drawn): the best of 600 fills
P.boost = () => 3; A.peopleReset(); settle(A, out, px, eyeY(px, pz), pz); let best = Infinity, drawn = 0; for (let i = 0; i < 600; i++) { A.peoplePin(6000000 + i / 60); const a = performance.now(); drawn = A.peopleFill(out, px, eyeY(px, pz), pz); best = Math.min(best, performance.now() - a); }
o.cost = { drawn, slots: P.stat.slots, bestMs: best };
console.log(JSON.stringify(o));
'''

OFF = r'''
const sum = (A) => { let s = 0, links = 0; for (const r of A.runs) { for (let j = 0; j < r.xs.length; j++) s += r.xs[j] * 3 + r.zs[j] * 5 + r.ys[j] * 7 + r.cum[j]; s += r.len + r.cls + r.mx + r.mz; links += r.conn[0].length + r.conn[1].length; } return [A.runs.length, s, links]; };
const o = {};
for (const [name, opt] of [['off', { search: '' }], ['other', { search: '?people=10&dev=1' }], ['tier2', { tier2: true }], ['on', { search: '?dev=1&people=1' }]]) {
  const A = make(opt); const text0 = A.walkB64() !== null; A.boot();
  const out = new Float32Array(4800), n = A.peopleFill(out, -1603, 2, -802), P = A.PEOPLE;
  o[name] = { on: A.PEOPLE_ON, live: P.live, ready: P.ready, textKept: text0, keys: Object.keys(A.runs[0]).join(), sum: sum(A), n, arrays: Object.keys(P).filter((k) => ArrayBuffer.isView(P[k])).join(), trails: P.trails.length, ways: P.ways, viewCalls: A.VIEW.calls, scratch: !!(A.next() || A.piece()), dbg: A.peopleDbg() };
}
// the walls missing or wrong: nobody walks, nothing throws
for (const [name, walk] of [['noWalls', ''], ['badWalls', 'AAAAAAAAAAAAAAAAAAAAAAAA']]) { const A = make({ walk }); A.boot(); const out = new Float32Array(4800); o[name] = { n: A.peopleFill(out, -1603, 2, -802), live: A.PEOPLE.live, ready: A.PEOPLE.ready }; }
console.log(JSON.stringify(o));
'''


def section():
    src = (ROOT / 'app.js').read_text(encoding='utf-8')
    return src, src[src.index(BANNER):src.index(END)]


def code_of(text):
    return '\n'.join(line.split('//')[0] for line in text.splitlines())


class Text(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src, cls.sec = section()
        cls.code = code_of(cls.sec)

    def test_the_section_stands_after_the_parked_cars_and_before_the_linker(self):
        s = self.src
        self.assertEqual(s.count(BANNER), 1)
        self.assertEqual(s.count(END), 1)
        self.assertLess(s.index('  // ---- parked cars'), s.index(BANNER))
        self.assertLess(s.index('  function updateParked(now) {'), s.index(BANNER))
        self.assertEqual(s[s.index(END):].split('\n', 2)[1], '  function trafficPrepareGraph(runs) {')

    def test_off_by_default_and_never_on_tier_two(self):
        self.assertIn("const PEOPLE_ON = /[?&]people=1\\b/.test(location.search) && !TIER2;", self.sec)
        self.assertIn("if (!PEOPLE_ON || !P.live) return 0;", self.sec)
        self.assertIn("if (!PEOPLE_ON && typeof PEOPLE_WALK_B64 !== 'undefined') PEOPLE_WALK_B64 = null;", self.sec)

    def test_it_draws_nothing(self):
        # Round 227 is the data and the logic: no mesh, material, program or shader text, and no build step
        for word in ('THREE', 'Material', 'Mesh', 'gl_', 'onBeforeCompile', 'uniform', 'step(', 'groupCity', 'scene.add'):
            self.assertNotIn(word, self.code, word)

    def test_the_fill_allocates_nothing_and_keys_nothing_by_a_string(self):
        fill = code_of(self.sec[self.sec.index('  function peopleFill('):self.sec.index('  // __dbg.people(): the count of everything')])
        for word in ('new ', '=>', '.push(', '.map(', '.filter(', '.slice(', "' +", "+ '", '`', 'Map', 'Set(', '...'):
            self.assertNotIn(word, fill, word)
        self.assertNotRegex(fill, r'=\s*\[')
        self.assertNotRegex(fill, r'=\s*\{')
        # and what it calls every walker allocates nothing either: the place along a trail is worked out in the loop
        self.assertNotIn('peopleAlong(', fill)
        self.assertNotIn('peoplePiece(', fill)

    def test_no_dashes_or_middots_in_the_code(self):
        self.assertNotIn('—', self.code)
        self.assertNotIn('·', self.code)

    def test_the_decoder_tags_only_under_the_flag(self):
        step = self.src[self.src.index("  step('Setting the traffic flowing'"):self.src.index('  function trafficFrac() {')]
        self.assertIn("const pplTag = typeof PEOPLE_ON !== 'undefined' && PEOPLE_ON;", step)
        self.assertIn("if (pplTag) PEOPLE.ways = hdr[1];", step)
        self.assertIn("if (pplTag) { const dp = densify(pts, 20);", step)
        self.assertIn("if (!cur) { cur = { xs: [], zs: [], ys: [] }; if (pplTag) cur.j0 = j; }", step)
        self.assertIn("if (pplTag) { const tr = trafficRuns[trafficRuns.length - 1]; tr.wi = wI; tr.ws = wArc[r.j0 + j0]; }", step)
        # every mention of the people in the step is behind the tag
        for line in code_of(step).splitlines():
            if ('PEOPLE' in line or 'wArc' in line or 'cur.j0' in line) and line.strip() != 'let wArc = null;':
                self.assertIn('pplTag', line, line)
        # the distance along the way is measured before the bridge's lane fit, as the bake measures it
        self.assertLess(step.index('if (pplTag) { const dp = densify(pts, 20);'), step.index('pts = brLaneFit(densify(pts, 20));'))

    def test_the_hooks(self):
        self.assertTrue("    if (PEOPLE_ON) peopleClosed();   // Round 227: a closed block is walked by nobody\n  }\n  function closuresReconcile() {" in self.src, 'closureTraffic does not tell the walkers')
        self.assertTrue("      people: peopleDbg, peopleAt: peoplePin, peopleProbe," in self.src, '__dbg lacks people, peopleAt and peopleProbe')
        build = (ROOT / 'build.py').read_text(encoding='utf-8')
        self.assertTrue('let_blob("PEOPLE_WALK_B64", "people_walk.b64")' in build, 'build.py does not inline people_walk.b64')
        self.assertRegex(build, r'"people_walk\.b64": \d')


@unittest.skipUnless(pn.have(), 'Node.js, traffic.b64 or people_walk.b64 unavailable')
class Graph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = pn.node(GRAPH)
        print('\n  the walkers on the whole network (a flat ground): ' + ', '.join('%s %s' % (k, round(v, 3) if isinstance(v, float) else v) for k, v in cls.o.items()))

    def test_the_walk_is_a_permutation_and_every_face_closes(self):
        o = self.o
        self.assertEqual(o['runs'], 46145)
        self.assertGreater(o['crossings'], 5000)            # the crossings the traffic's linker does not join
        self.assertEqual(o['pieces'], o['runs'] + 2 * o['crossings'])
        self.assertEqual(o['notPerm'], 0)
        self.assertEqual(o['unclosed'], 0)
        self.assertEqual(o['turns'], o['dead'])             # the walk turns round at a dead end and nowhere else
        self.assertGreater(o['faces'], 15000)

    def test_every_side_is_traced_to_a_trail_or_to_nobody(self):
        o = self.o
        self.assertEqual(o['untraced'], 0)
        self.assertEqual(o['nan'], 0)
        self.assertEqual(o['badPeriod'], 0)                 # a loop's period is its length, an out-and-back trail's twice it
        self.assertEqual(o['shortTrail'], 0)
        self.assertEqual(o['notRising'], 0)
        self.assertGreater(o['loops'], 5000)
        self.assertGreater(o['shuttles'], 5000)
        self.assertGreater(o['walkShare'], 0.75)            # of the class 2 to 5 kerb length
        self.assertLess(o['walkShare'], 0.95)
        self.assertLessEqual(o['maxSlots'], 400)
        self.assertLess(o['maxLen'], 2500)                  # no trail longer than a face the trace walks round

    def test_nobody_on_a_highway_a_median_or_a_street(self):
        o = self.o
        self.assertEqual(o['on01'], 0)
        self.assertGreater(o['medians'], 500)
        self.assertEqual(o['medianWalked'], 0)
        self.assertEqual(o['inStreet'], 0)                  # not one point of 500,000 on a drawn street
        self.assertGreater(o['sides'][6], 500)              # and the strips with a street close behind them, on a face of any length

    def test_a_face_too_long_gives_each_piece_its_own_trail(self):
        o = self.o
        self.assertGreater(o['giantSides'], 5000)
        self.assertGreater(o['giantWalked'], 2000)
        self.assertEqual(o['giantNotSolo'], 0)

    def test_the_corners_join(self):
        met, touch, bend, slant = self.o['corners'][:4]
        refused = sum(self.o['corners'][4:])
        self.assertGreater(met, 40000)                      # two walk lines cut where they meet: a block's corner
        self.assertGreater(touch + bend + slant, 5000)
        self.assertLess(refused, 0.01 * (met + touch + bend + slant))


@unittest.skipUnless(pn.have(), 'Node.js, traffic.b64 or people_walk.b64 unavailable')
class Rough(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = pn.node(ROUGH)

    def test_nobody_on_a_deck_a_highway_or_a_street(self):
        for name in ('open', 'shut', 'again'):
            t = self.o[name]
            self.assertGreater(t['deckRuns'], 300, name)
            self.assertEqual((t['onDeck'], t['on01'], t['untraced'], t['inStreet']), (0, 0, 0, 0), name)
            self.assertGreater(t['walked'], 50000, name)

    def test_a_closed_block_is_walked_by_nobody(self):
        o = self.o
        self.assertGreater(o['closed'], 4000)
        self.assertEqual(o['reset'], 1)                     # the traces are let go once
        self.assertEqual(o['cleared'], 0)
        self.assertEqual(o['shut']['onClosed'], 0)
        self.assertLess(o['shut']['walked'], o['open']['walked'] - 5000)
        self.assertEqual(o['same'], 1)                      # the same closures again cost nothing
        self.assertEqual(o['reopened'], 2)
        self.assertEqual(o['again']['walked'], o['open']['walked'])
        self.assertEqual(o['again']['trails'], o['open']['trails'])


@unittest.skipUnless(pn.have(), 'Node.js, traffic.b64 or people_walk.b64 unavailable')
class Fill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = pn.node(FILL, gc=True)

    def test_the_buffer(self):
        o = self.o
        self.assertTrue(o['on'])
        self.assertEqual((o['stride'], o['cap'], o['r']), (8, 600, 150))
        self.assertGreater(o['n'], 100)                     # City Hall on a Saturday at one
        self.assertLessEqual(o['n'], o['cap'])
        for k in ('far', 'unit', 'fig', 'phase', 'fadeBad', 'edge', 'mid', 'yOff', 'inStreet'):
            self.assertEqual(o[k], 0, k)
        self.assertEqual(o['shareFull'], 1)
        self.assertEqual(o['present'], o['slots'])

    def test_the_same_second_gives_the_same_walkers(self):
        self.assertTrue(self.o['sameT'])
        self.assertTrue(self.o['sameWhateverOrder'])        # whichever streets were traced first

    def test_a_slot_is_back_after_its_period(self):
        o = self.o
        self.assertGreater(o['checked'], 40)
        self.assertGreater(min(o['kinds']), 5)              # loops and out-and-back trails both
        self.assertEqual((o['missed'], o['moved'], o['wrongHalf']), (0, 0, 0))

    def test_height_radius_and_cap(self):
        o = self.o
        self.assertEqual(o['high'], 0)                      # nothing from 60 m over the ground
        self.assertGreater(o['fade54'][0], 0)
        self.assertLess(o['fade54'][1], 0.9)                # and the last of it fades
        self.assertGreater(o['r80'][0], 0)
        self.assertEqual(o['r80'][1], 0)
        self.assertTrue(o['r80'][2])
        self.assertEqual(o['capped'], [10, True, True])     # never over the cap, and at the cap the circle draws in

    def test_presence_follows_the_clock_and_the_rain(self):
        wd, wet, night = self.o['share']
        self.assertAlmostEqual(wd, 0.95, places=6)          # a Tuesday at five
        self.assertAlmostEqual(wet, 0.4, places=6)          # rain leaves four in ten
        self.assertLess(night, 0.02)

    def test_a_slot_changes_only_off_the_screen(self):
        f = self.o['flip']
        self.assertEqual(f['full'], f['slots'])
        self.assertEqual(f['watched'], f['full'])           # three in the morning, everyone in view: nobody goes
        self.assertGreater(f['asked'], 0.9 * f['full'])
        self.assertEqual(f['refreshed'], 1)                 # the frustum is brought up to date once a call
        self.assertLess(f['unseen'], 0.05 * f['full'])      # out of view they are gone
        self.assertEqual(f['stillGone'], f['unseen'])       # and nobody comes back in view
        self.assertEqual(f['back'], f['full'])

    def test_the_probe_and_the_switch(self):
        d = self.o['dbg']
        for k in ('on', 'live', 'ready', 'loops', 'shuttles', 'trails', 'slots', 'traced', 'share', 'why', 'fill', 'near'):
            self.assertIn(k, d['keys'].split(','))
        self.assertEqual(d['fill'], 'drawn,present,slots,trails,pending,ms,fills')
        self.assertGreater(d['loops'], 0)
        self.assertEqual(d['off'], 0)
        self.assertTrue(d['live'])
        self.assertGreater(d['onAgain'], 0)
        self.assertEqual(d['pinned'], 5000000)

    def test_no_allocation_a_call(self):
        self.assertLess(self.o['heapGrowth'], 400_000, self.o['heapGrowth'])   # 20,000 fills

    def test_the_cost(self):
        c = self.o['cost']
        print('\n  peopleFill at three times the density: %d drawn of %d slots worked, best %.3f ms' % (c['drawn'], c['slots'], c['bestMs']))
        self.assertGreater(c['drawn'], 300)
        self.assertLess(c['bestMs'], 1.0)                   # 0.10 ms on a quiet Mac; the line is loose, the machine may be busy


@unittest.skipUnless(pn.have(), 'Node.js, traffic.b64 or people_walk.b64 unavailable')
class Off(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = pn.node(OFF)

    def test_inert_without_the_flag(self):
        for name in ('off', 'other', 'tier2'):
            t = self.o[name]
            self.assertFalse(t['on'], name)
            self.assertFalse(t['live'], name)
            self.assertFalse(t['ready'], name)
            self.assertEqual(t['n'], 0, name)
            # the runs are the decoder's own (tests/test_traffic_link.py's list), no table is made, nothing is asked
            self.assertEqual(t['keys'], 'xs,zs,ys,cum,len,cls,oneway,aadt,mx,mz,want,cars,busy,conn', name)
            self.assertEqual(t['arrays'], '', name)
            self.assertFalse(t['scratch'], name)
            self.assertEqual((t['trails'], t['ways'], t['viewCalls']), (0, 0, 0), name)
            self.assertEqual(t['dbg']['on'], False, name)
            self.assertNotIn('near', t['dbg'], name)

    def test_the_flag_changes_nothing_but_the_tags(self):
        on, off = self.o['on'], self.o['off']
        self.assertTrue(on['on'])
        self.assertEqual(on['keys'], off['keys'].replace(',conn', ',wi,ws,conn'))
        self.assertEqual(on['sum'], off['sum'])             # every vertex, height, length and link as without it
        self.assertEqual(on['ways'], 29749)
        self.assertTrue(on['ready'])
        self.assertTrue(on['textKept'])

    def test_no_walls_no_walkers(self):
        for name in ('noWalls', 'badWalls'):
            self.assertEqual((self.o[name]['n'], self.o[name]['live'], self.o[name]['ready']), (0, False, False), name)


if __name__ == '__main__':
    unittest.main()
