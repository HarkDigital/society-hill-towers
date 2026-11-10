"""Round 225 (Stage 1 of the Nov 10 plan, BUILDCPU-1 a to c): the river's edge search asked only where it can answer.

schEdges, the Schuylkill's nearest-edge search, walked a 5 by 5 block of a string-keyed Map on every call: 25 keys built
and looked up, 2.7 M calls a load (Round 220's counter), 98% of them nowhere near the river. Round 222's schNear is that
search's own reach as a 40 m bitmap, so schEdges now returns the walk's empty answer, a fresh [80, 0], wherever schNear
is false. streetTriNear, asked once for every street triangle (2.6 M a load), built two to six strings to probe two
Maps; each Map now carries its key set as a byte a cell (bits) and the question goes to that.

Both must be EXACT: the same numbers bit for bit, or the river's bed, the bank roads' floor, the traffic's heights and
the terrain patches' trims move. So nothing here is argued; the page's own code, cut from app.js by text, runs under
Node with and without the change over the real shipped data:

  schEdges    the page's block against the same block with the gate's one line taken out, over every road point the two
              road loops ask about (wide.b64 through the page's own lotDensify, city.b64 and outskirts.b64 at 30 m, every
              segment's midpoint with them), the traffic sampler's points (traffic.b64 at 20 m), a 50 m grid of the far
              box, the river's own centreline at 10 m and 26 offsets along the normal of every outline edge: 0 answers
              differing in 2.0 M, compared with Object.is on both numbers. (The road loops also cut a street at its
              junctions, and those cuts' points are not made here: the cell proof below covers every point there is.)
  riverCarve  THE river invariant (CLAUDE.md: the drawn ground down the Schuylkill's centreline under the water sheet)
              cannot move if riverCarve is handed the same answers. Its inputs are the ground builders' nodes, so the
              page's own riverCarve runs gated and ungated at every node of the far strips (FAR_CELL 50 m, the page's
              own node formula, which is not the plain lattice: the strips stretch their cells to fit), of the NW patch
              and of the outer districts' 25 m strips, at a hill's height and, every third node, a low bank's, each
              builder passing the floor argument the page passes: 0 heights differing in 465,642 nodes, so groundMeshY,
              and with it __dbg.riverCheck() and __dbg.bankCheck(), read as before.
              drapeY hands riverCarve arbitrary points, and those are covered by the cell proof below.
  the cells   the gate's answer depends only on the 40 m cell, so one walk over every cell round the edge grid proves it
              for every point there is: wherever any of the walk's 25 cells holds an edge, schNear is true.
  streetTriNear  the page's function against the Round 124 walk it replaced (kept here verbatim), both over the Maps the
              page's own initTerrainPatches and initStreetSurfaces build from overpasses.json, street_labels.json and
              street_sdf.json, for the two strip triangles of every road segment of the three tiers and a 50 m lattice
              of the far box: 0 answers differing, and each bitmap is exactly its Map's key set.

The gate also runs under JavaScriptCore (the phone's engine) through osascript, as the suite's other JXA tests do.
`python3 tests/test_river_gate.py --numbers` prints every set's count and its microseconds a call both ways; the one
timing the suite asserts is loose on purpose (the gate at least three times faster than the walk on the far grid, where
it measures 25 to 40 times on a busy M2 Max: 2.5 us a call to 0.09 under Node over the far ring's road vertices).
"""
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.js').read_text()
COUNTER = '      SCH_STAT.calls++;   // Round 220: counted, never timed\n'
GATE = "      if (!schNear(x, z)) return [80, 0];   // Round 225: no edge within the search's block, the walk's own empty answer\n"
FIRST = '      let best = 6400, side = 0;'
NODE_LINE = 'const x = x0 + (x1 - x0) * i / nx, z = z0 + (z1 - z0) * j / nz;'


def cut(a, b, start=0):
    i = SRC.index(a, start)
    j = SRC.index(b, i + len(a))
    return SRC[i:j]


def line(a):
    """the one source line that starts with a"""
    i = SRC.index(a)
    return SRC[i:SRC.index('\n', i) + 1]


def river_js():
    """the page's Schuylkill block twice, as it ships and with the gate's line taken out, each behind a factory"""
    block = cut('  const SCH_POLYS = (typeof SCHUYLKILL_DATA', '  function schuylkillCut(x, z) {')
    assert block.count(GATE) == 1, 'the gate line is not in the block once'
    seam = '    const egrid = new Map(), segs = [];\n'   # the harness reads the edge grid's keys for the cell proof
    assert block.count(seam) == 1
    block = block.replace(seam, '    const egrid = EG.egrid = new Map(), segs = [];\n')
    plain = block.replace(GATE, '')
    assert 'schNear(x, z)) return [80, 0]' not in plain
    tail = '\n  return { schEdges, schNear, schRaster, riverCarve, schBand, stat: SCH_STAT };\n}\n'
    return (line('  function clamp(v, a, b) {') + line('  const smooth = (a, b, x) =>') + line('  const BANKS = ')
            + 'function schuylkillCut() { return 0; }\n'
            + 'function riverGated(EG) {\n  const PERF = {};\n' + block + tail
            + 'function riverPlain(EG) {\n  const PERF = {};\n' + plain + tail
            + 'const same = (a, b) => a.length === 2 && b.length === 2 && Object.is(a[0], b[0]) && Object.is(a[1], b[1]);\n' + BANKS_JS)


def terrain():
    """TERRAIN.water and .bed as the page derives them (the DEM at the origin is the datum), for riverCarve's bands"""
    try:
        G = json.loads((ROOT / 'dem.json').read_text())
        fx, fz = (0 - G['x0']) / G['cell'], (0 - G['z0']) / G['cell']
        i, j = int(fx), int(fz)
        tx, tz = fx - i, fz - j
        r0, r1 = G['rows'][j], G['rows'][j + 1]
        datum = (r0[i] * (1 - tx) + r0[i + 1] * tx) * (1 - tz) + (r1[i] * (1 - tx) + r1[i + 1] * tx) * tz
    except Exception:
        datum = 8.34
    return {'water': 0.5 - datum, 'bed': -2.0 - datum}


# where the walk has work to do: off every outline vertex and edge midpoint, along the edge's normal, either side of each
# distance the callers branch on (8 inside test, 40 and 70 the road blend, 60 the carve, 80 the reach) and past the reach
BANKS_JS = r'''
function bankOffsets(polys) {
  const xs = [];
  for (const pg of polys) for (const r of [pg.ring].concat(pg.holes || [])) for (let k = 0, n = r.length; k < n; k++) {
    const a = r[k], b = r[(k + 1) % n], dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz);
    if (L < 0.05) continue;
    for (const d of [-130, -81, -79, -61, -59, -41, -39, -9, -7, -0.5, 0, 0.5, 7, 9, 39, 41, 59, 61, 69, 71, 79, 81, 119, 121, 130, 170])
      xs.push(a[0] + dz / L * d, a[1] - dx / L * d, (a[0] + b[0]) / 2 + dz / L * d, (a[1] + b[1]) / 2 - dx / L * d);
  }
  return xs;
}
'''

NODE_MAIN = r'''
const fs = require('fs'), path = require('path');
const MODEL = %(model)s;
const location = { search: '' };
const SCHUYLKILL_DATA = JSON.parse(fs.readFileSync(path.join(MODEL, 'schuylkill.json'), 'utf8'));
const TERRAIN = %(terrain)s;
%(river)s
%(densify)s
const PARKING_SOUTH = JSON.parse(fs.readFileSync(path.join(MODEL, 'parking_south.json'), 'utf8'));
%(lot)s
%(boxes)s
const EGg = {}, EGp = {}, G = riverGated(EGg), P = riverPlain(EGp);
const out = { sets: {}, carve: {}, tri: {} };

// ---- the points
function blob(name) {
  const raw = Buffer.from(fs.readFileSync(path.join(MODEL, name), 'ascii').trim(), 'base64');
  const ab = raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.length);
  return { hdr: new Int32Array(ab, 0, 4), body: new Int16Array(ab, 16) };
}
const ATTR = new Set([0x5348545A, 0x5348545B, 0x5348545C, 0x5348545D]);   // tests/_common.py walk_scene: six header words a building, else four
function roads(name, S) {
  const { hdr, body } = blob(name), hs = ATTR.has(hdr[0]) ? 6 : 4;
  let k = 0;
  for (let i = 0; i < hdr[1]; i++) k += hs + 2 * body[k];
  const recs = [];
  for (let i = 0; i < hdr[2]; i++) {
    const n = body[k++], w = body[k++] / 10, t = body[k++];
    const pts = new Array(n);
    for (let j = 0; j < n; j++) pts[j] = [body[k++] * S, body[k++] * S];   // the page's own line, both road loops
    recs.push({ pts, w, t });
  }
  for (let i = 0; i < hdr[3]; i++) k += 2 + 2 * body[k];
  return { recs, left: body.length - k, nr: hdr[2] };
}
// what a road loop asks about: every densified vertex (groundMeshLandY, bankFloor) and every segment's midpoint (bankD)
function roadPoints(recs, dens) {
  const xs = [];
  for (const r of recs) {
    const pts = dens(r.pts);
    for (let j = 0; j < pts.length; j++) {
      xs.push(pts[j][0], pts[j][1]);
      if (j + 1 < pts.length) { const a = pts[j], q = pts[j + 1]; xs.push((a[0] + q[0]) / 2, (a[1] + q[1]) / 2); }
    }
  }
  return Float64Array.from(xs);
}
function lattice(x0, x1, z0, z1, step) {
  const xs = [];
  for (let x = x0; x <= x1; x += step) for (let z = z0; z <= z1; z += step) xs.push(x, z);
  return Float64Array.from(xs);
}
// a ground builder's nodes, by the page's own formula (mkFarGround and the outer districts' strips share it)
function nodes(x0, x1, z0, z1, cell, xs) {
  const nx = Math.max(1, Math.round((x1 - x0) / cell)), nz = Math.max(1, Math.round((z1 - z0) / cell));
  for (let j = 0; j <= nz; j++) for (let i = 0; i <= nx; i++) {
    const x = x0 + (x1 - x0) * i / nx, z = z0 + (z1 - z0) * j / nz;
    xs.push(x, z);
  }
}
// one pass of the walk as it was, its answers kept; one pass of the gated search against them. Each pass is timed whole
// (microseconds a call; the gated pass the best of three where asked, it is the short one and the machine may be busy)
function edgeSet(name, pts, timed) {
  const n = pts.length / 2, c0 = [G.stat.calls, P.stat.calls], pd = new Float64Array(n), ps = new Float64Array(n);
  let diff = 0, reach = 0, near = 0; const first = [];
  let t = performance.now();
  for (let i = 0, k = 0; k < n; i += 2, k++) { const b = P.schEdges(pts[i], pts[i + 1]); pd[k] = b[0]; ps[k] = b[1]; if (b.length !== 2) diff++; }
  const usPlain = (performance.now() - t) * 1000 / n;
  t = performance.now();
  for (let i = 0, k = 0; k < n; i += 2, k++) {
    const a = G.schEdges(pts[i], pts[i + 1]);
    if (a.length !== 2 || !Object.is(a[0], pd[k]) || !Object.is(a[1], ps[k])) { diff++; if (first.length < 5) first.push([pts[i], pts[i + 1], a, [pd[k], ps[k]]]); }
  }
  let usGated = (performance.now() - t) * 1000 / n;
  const counted = [G.stat.calls - c0[0], P.stat.calls - c0[1]];
  for (let r = 0; timed && r < 2; r++) {
    t = performance.now(); let sum = 0;
    for (let i = 0; i < pts.length; i += 2) sum += G.schEdges(pts[i], pts[i + 1])[0];
    usGated = Math.min(usGated, (performance.now() - t) * 1000 / n);
  }
  for (let i = 0, k = 0; k < n; i += 2, k++) { if (pd[k] < 80) reach++; if (G.schNear(pts[i], pts[i + 1])) near++; }
  out.sets[name] = { n, diff, reach, near, first, counted, usPlain: +usPlain.toFixed(4), usGated: +usGated.toFixed(4) };
}
const W = roads('wide.b64', 0.2), C = roads('city.b64', 0.7), O = roads('outskirts.b64', 1.0);
out.blobs = { wide: [W.nr, W.left], city: [C.nr, C.left], outskirts: [O.nr, O.left] };
const ring30 = (pts) => densify(pts, 30);   // raiseRing's own step
edgeSet('wide roads', roadPoints(W.recs, lotDensify));
edgeSet('city roads', roadPoints(C.recs, ring30));
edgeSet('outskirts roads', roadPoints(O.recs, ring30));
{
  const { hdr, body } = blob('traffic.b64'), xs = [];
  let k = 0;
  for (let wI = 0; wI < hdr[1]; wI++) {
    const n = body[k++]; k += 2;
    const unit = (hdr[3] || 200) / 1000;
    let pts = new Array(n);
    for (let j = 0; j < n; j++) pts[j] = [body[k++] * unit, body[k++] * unit];   // the traffic step's own lines
    pts = densify(pts, 20);
    for (const p of pts) xs.push(p[0], p[1]);
  }
  out.blobs.traffic = [hdr[1], body.length - k];
  edgeSet('traffic', Float64Array.from(xs));
}
edgeSet('far grid 50 m', lattice(RING_W.x0, RING_W.x1, RING_W.z0, RING_W.z1, 50), true);
{
  const xs = [];
  for (const LN of SCHUYLKILL_DATA.lines) for (const p of densify(LN, 10)) xs.push(p[0], p[1]);
  edgeSet('centreline 10 m', Float64Array.from(xs));
  edgeSet('bank offsets', Float64Array.from(bankOffsets(SCHUYLKILL_DATA.polys)));
}

// ---- riverCarve at the ground builders' own nodes
function carveSet(name, strips, cell, floor) {   // floor: as that builder calls it (the outer districts' strips pass true, R1)
  const xs = [];
  for (const s of strips) nodes(s[0], s[1], s[2], s[3], cell, xs);
  let diff = 0, carved = 0;
  for (let i = 0; i < xs.length; i += 2) {
    const x = xs[i], z = xs[i + 1];
    const yy = TERRAIN.water + ((i >> 1) %% 3 === 2 ? 0.4 : 14.25);   // a hill, and every third node a low bank: every branch of the carve
    const a = G.riverCarve(x, z, yy, floor), b = P.riverCarve(x, z, yy, floor);
    if (!Object.is(a, b)) diff++;
    if (b !== yy) carved++;
  }
  out.carve[name] = { n: xs.length / 2, diff, carved };
  edgeSet(name + ' nodes', Float64Array.from(xs));
}
const FAR_CELL = %(far_cell)s;
carveSet('far strips', [[RING_W.x0, RING_W.x1, RING_W.z0, WIDEB.z0], [RING_W.x0, RING_W.x1, WIDEB.z1, RING_W.z1],
  [RING_W.x0, WIDEB.x0, WIDEB.z0, WIDEB.z1], [WIDEB.x1, RING_W.x1, WIDEB.z0, WIDEB.z1]], FAR_CELL, undefined);
{
  // the NW patch, its hole snapped to the north strip's grid as the far step snaps it
  const NW = %(nw)s;
  const sx0 = RING_W.x0, sx1 = RING_W.x1, sz0 = RING_W.z0, sz1 = WIDEB.z0;
  const nxN = Math.max(1, Math.round((sx1 - sx0) / FAR_CELL)), nzN = Math.max(1, Math.round((sz1 - sz0) / FAR_CELL));
  const cw = (sx1 - sx0) / nxN, chz = (sz1 - sz0) / nzN;
  const i0 = Math.ceil((NW.x0 - sx0) / cw), i1 = Math.floor((NW.x1 - sx0) / cw);
  const j0 = Math.ceil((NW.z0 - sz0) / chz), j1 = Math.floor((NW.z1 - sz0) / chz);
  carveSet('NW patch', [[sx0 + i0 * cw, sx0 + i1 * cw, sz0 + j0 * chz, sz0 + j1 * chz]], 50, undefined);
}
carveSet('outer strips', [[WIDEB.x0, WIDEB.x1, WIDEB.z0, CORE_EXT.z0], [WIDEB.x0, WIDEB.x1, CORE_EXT.z1, WIDEB.z1],
  [WIDEB.x0, CORE_EXT.x0, CORE_EXT.z0, CORE_EXT.z1], [CORE_EXT.x1, WIDEB.x1, CORE_EXT.z0, CORE_EXT.z1]], 25, true);

// ---- the cell proof: the gate's answer is one bit a 40 m cell, so every cell round the edge grid settles every point
{
  const keys = new Set(EGg.egrid.keys());
  let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const key of keys) { const c = key.indexOf(':'), x = +key.slice(0, c), z = +key.slice(c + 1); x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
  let cells = 0, hidden = 0, idle = 0, withEdge = 0;
  for (let gx = x0 - 8; gx <= x1 + 8; gx++) for (let gz = z0 - 8; gz <= z1 + 8; gz++) {
    let any = false;
    for (let a = -2; a <= 2 && !any; a++) for (let b = -2; b <= 2; b++) if (keys.has((gx + a) + ':' + (gz + b))) { any = true; break; }
    // every corner region of the cell floors to it: the low corner, the middle and just under the high corner
    for (const [fx, fz] of [[0, 0], [0.5, 0.5], [0.999999, 0.999999], [0, 0.999999], [0.999999, 0]]) {
      const x = (gx + fx) * 40, z = (gz + fz) * 40;
      if (Math.floor(x / 40) !== gx || Math.floor(z / 40) !== gz) throw new Error('the probe left its cell');
      const near = G.schNear(x, z);
      if (any && !near) hidden++;
      if (!any && near) idle++;
    }
    cells++; if (any) withEdge++;
  }
  out.cells = { keys: keys.size, cells, withEdge, hidden, idle, plainKeys: EGp.egrid.size };
}

// ---- the answer itself: fresh, [80, 0], and the counter counts a gated call
{
  const c0 = G.stat.calls, a = G.schEdges(9000, 9000), b = G.schEdges(9000, 9000), p = P.schEdges(9000, 9000);
  a[0] = -1; a[1] = 7;
  const odd = [[NaN, 0], [0, NaN], [NaN, NaN], [Infinity, 0], [0, -Infinity], [1e300, -1e300], [-0, -0]];
  out.answer = { fresh: a !== b && b[0] === 80, b, p, is: Object.is(b[0], 80) && Object.is(b[1], 0), isArray: Array.isArray(b), len: b.length, calls: G.stat.calls - c0,
    odd: odd.filter((q) => !same(G.schEdges(q[0], q[1]), P.schEdges(q[0], q[1]))).length, sqrt: Math.sqrt(6400) };
}

// ---- streetTriNear against the Round 124 walk, over the Maps the page's own code builds from the shipped data
const OVP = JSON.parse(fs.readFileSync(path.join(MODEL, 'overpasses.json'), 'utf8'));
const ST_LABELS = JSON.parse(fs.readFileSync(path.join(MODEL, 'street_labels.json'), 'utf8'));
const ST_SDF = JSON.parse(fs.readFileSync(path.join(MODEL, 'street_sdf.json'), 'utf8'));
const PERF = {};
%(street)s
function streetTriWalk(ax,az,bx,bz,cx,cz) {   // Round 124's body as it stood before Round 225, verbatim
    const x0=Math.min(ax,bx,cx)-0.01,x1=Math.max(ax,bx,cx)+0.01,z0=Math.min(az,bz,cz)-0.01,z1=Math.max(az,bz,cz)+0.01;
    if(terrainRoadGrid)
      for(let x=Math.floor(x0/TERRAIN_PATCH_CELL);x<=Math.floor(x1/TERRAIN_PATCH_CELL);x++)
        for(let z=Math.floor(z0/TERRAIN_PATCH_CELL);z<=Math.floor(z1/TERRAIN_PATCH_CELL);z++)if(terrainRoadGrid.has(x+':'+z))return true;
    if(streetSurfaceIndex)
      for(let gx=Math.floor(x0/100);gx<=Math.floor(x1/100);gx++)
        for(let gz=Math.floor(z0/100);gz<=Math.floor(z1/100);gz++)if(streetSurfaceIndex.has(gx+':'+gz))return true;
    return false;
}
initTerrainPatches();
initStreetSurfaces();
function bitsOf(map) {
  const o = map.bits; let on = 0, miss = 0;
  for (let k = 0; k < o.m.length; k++) on += o.m[k];
  for (const key of map.keys()) { const c = key.indexOf(':'), x = +key.slice(0, c), z = +key.slice(c + 1); if (o.m[(z - o.z0) * o.nx + (x - o.x0)] !== 1) miss++; }
  return { keys: map.size, on, miss, bytes: o.m.length, box: [o.x0, o.z0, o.nx, o.nz] };
}
out.tri.road = bitsOf(terrainRoadGrid); out.tri.label = bitsOf(streetSurfaceIndex);
{
  // a road strip's two triangles a segment, the corners the road loops build (a and q either side by half the width)
  const T = [];
  const strips = (recs, dens) => { for (const r of recs) {
    const pts = dens(r.pts), hw = r.w / 2;
    for (let j = 0; j + 1 < pts.length; j++) {
      const a = pts[j], q = pts[j + 1]; let dx = q[0] - a[0], dz = q[1] - a[1]; const L = Math.hypot(dx, dz); if (L < 0.01) continue;
      dx /= L; dz /= L; const px = -dz * hw, pz = dx * hw;
      T.push(a[0] + px, a[1] + pz, a[0] - px, a[1] - pz, q[0] + px, q[1] + pz, a[0] - px, a[1] - pz, q[0] - px, q[1] - pz, q[0] + px, q[1] + pz);
    }
  } };
  strips(W.recs, lotDensify); strips(C.recs, ring30); strips(O.recs, ring30);
  const roadTris = T.length / 6;
  for (let x = RING_W.x0; x <= RING_W.x1; x += 50) for (let z = RING_W.z0; z <= RING_W.z1; z += 50) T.push(x, z, x + 7, z + 0.5, x + 2, z + 9);
  // the edges of the question: nothing, everything, a sliver on a cell line, far outside, and numbers that are not
  for (const t of [[0, 0, 0, 0, 0, 0], [-1e5, -1e5, 1e5, -1e5, 0, 1e5], [50, 50, 50, 50, 50, 50], [49.995, 0, 49.999, 1, 49.99, 2], [-50.005, -100.005, -50.001, -100, -50, -99.99],
    [5e4, 5e4, 5e4 + 3, 5e4, 5e4, 5e4 + 3], [-5e4, 0, -5e4 - 3, 0, -5e4, 3], [NaN, 0, 1, 1, 2, 2], [0, NaN, 1, 1, 2, 2], [NaN, NaN, NaN, NaN, NaN, NaN], [-0, -0, -0, -0, -0, -0]]) T.push(...t);
  const tris = Float64Array.from(T), n = tris.length / 6;
  const c0 = TRI_NEAR.calls, was = new Uint8Array(n);
  let diff = 0, yes = 0;
  let t = performance.now();
  for (let i = 0, k = 0; k < n; i += 6, k++) { const b = streetTriWalk(tris[i], tris[i + 1], tris[i + 2], tris[i + 3], tris[i + 4], tris[i + 5]); if (b === true) { was[k] = 1; yes++; } else if (b !== false) diff++; }
  const usWalk = (performance.now() - t) * 1000 / n;
  t = performance.now();
  for (let i = 0, k = 0; k < n; i += 6, k++) { const a = streetTriNear(tris[i], tris[i + 1], tris[i + 2], tris[i + 3], tris[i + 4], tris[i + 5]); if (a !== (was[k] === 1)) diff++; }
  let usBits = (performance.now() - t) * 1000 / n;
  const counted = TRI_NEAR.calls - c0;
  for (let r = 0; r < 2; r++) {
    t = performance.now(); let sum = 0;
    for (let i = 0; i < tris.length; i += 6) sum += streetTriNear(tris[i], tris[i + 1], tris[i + 2], tris[i + 3], tris[i + 4], tris[i + 5]) ? 1 : 0;
    usBits = Math.min(usBits, (performance.now() - t) * 1000 / n);
  }
  Object.assign(out.tri, { n, roadTris, diff, yes, counted, usWalk: +usWalk.toFixed(4), usBits: +usBits.toFixed(4) });
  // one index released, then both: the bitmap goes with its Map
  const probe = [0, 0, 10, 0, 0, 10];
  const both = streetTriNear(...probe);
  terrainRoadGrid = null; const labelOnly = [streetTriNear(...probe), streetTriWalk(...probe)];
  streetSurfaceIndex = null; const none = streetTriNear(...probe);
  const empty = cellBits(new Map());
  out.tri.released = { both, labelOnly, none, empty: [empty.nx, empty.nz, cellBitsHit(empty, -5, 5, -5, 5)] };
}
console.log(JSON.stringify(out));
'''

JXA_MAIN = r'''
const location = { search: '' };
const SCHUYLKILL_DATA = %(data)s;
const TERRAIN = %(terrain)s;
%(river)s
%(boxes)s
const EGg = {}, EGp = {}, G = riverGated(EGg), P = riverPlain(EGp);
function sweep(pts, timed) {   // (never name it run: that is osascript's entry handler)
  const c0 = [G.stat.calls, P.stat.calls], n = pts.length / 2, pd = new Float64Array(n), ps = new Float64Array(n);
  let diff = 0, reach = 0;
  let t = Date.now();
  for (let i = 0, k = 0; k < n; i += 2, k++) { const b = P.schEdges(pts[i], pts[i + 1]); pd[k] = b[0]; ps[k] = b[1]; if (b.length !== 2) diff++; if (b[0] < 80) reach++; }
  const usPlain = (Date.now() - t) * 1000 / n;
  t = Date.now();
  for (let i = 0, k = 0; k < n; i += 2, k++) { const a = G.schEdges(pts[i], pts[i + 1]); if (a.length !== 2 || !Object.is(a[0], pd[k]) || !Object.is(a[1], ps[k])) diff++; }
  let usGated = (Date.now() - t) * 1000 / n;
  const counted = [G.stat.calls - c0[0], P.stat.calls - c0[1]];
  for (let r = 0; timed && r < 2; r++) {
    t = Date.now(); let sum = 0;
    for (let i = 0; i < pts.length; i += 2) sum += G.schEdges(pts[i], pts[i + 1])[0];
    usGated = Math.min(usGated, (Date.now() - t) * 1000 / n);
  }
  return { n, diff, reach, counted, usPlain: +usPlain.toFixed(4), usGated: +usGated.toFixed(4) };
}
const far = [];
for (let x = RING_W.x0; x <= RING_W.x1; x += 50) for (let z = RING_W.z0; z <= RING_W.z1; z += 50) far.push(x, z);
const a = G.schEdges(9000, 9000), b = G.schEdges(9000, 9000);
JSON.stringify({ far: sweep(Float64Array.from(far), true), bank: sweep(Float64Array.from(bankOffsets(SCHUYLKILL_DATA.polys)), false),
  fresh: a !== b, is: Object.is(b[0], 80) && Object.is(b[1], 0) && b.length === 2 });
'''


def boxes_js():
    return line('  const RING_W = { x0: -12000,') + line('  const WIDEB = { x0: -3700,') + line('  const CORE_EXT = { x0: -640,')


def street_js():
    return cut('  const TRI_NEAR = { calls: 0 };', '  // At a tier/cut boundary') \
        + cut('  const STREET_TEXT_HEIGHT = ', '  function streetLocal(') \
        + cut('  function streetTriNear(ax,az,bx,bz,cx,cz) {', '  function rememberStreetTriangle(') \
        + cut('  const TERRAIN_PATCH_CELL = 50,', '  function rememberTerrainRoad(') \
        + cut('  const RAIL_CUTS = [', '  function railCut(')


RESULTS = {}


def node_results():
    if 'node' not in RESULTS:
        nw = re.search(r'  const P = DEMN \? (\{ x0: -?\d+, x1: -?\d+, z0: -?\d+, z1: -?\d+ \}) : null;', SRC).group(1)
        far_cell = re.search(r'    const FAR_CELL = (\d+);', SRC).group(1)
        js = NODE_MAIN % {'model': json.dumps(str(ROOT)), 'terrain': json.dumps(terrain()), 'river': river_js(),
                          'densify': cut('  function densify(pts, step) {', '\n  }\n') + '\n  }\n', 'boxes': boxes_js(),
                          'lot': cut('  const LOT_FILL_BB = ', '  function lotDensify(pts) {') + cut('  function lotDensify(pts) {', '\n  }\n') + '\n  }\n',
                          'street': street_js(), 'nw': nw, 'far_cell': far_cell}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(js)
        try:
            r = subprocess.run(['node', f.name], capture_output=True, text=True, timeout=900)
        finally:
            os.unlink(f.name)
        assert r.returncode == 0, r.stderr[-3000:]
        RESULTS['node'] = json.loads(r.stdout)
    return RESULTS['node']


class TheGateAsText(unittest.TestCase):
    def test_the_gate_follows_the_counter_and_precedes_the_walk(self):
        block = cut('    schEdges = (x, z) => {', '    };\n')
        self.assertTrue(block.startswith('    schEdges = (x, z) => {\n' + COUNTER + GATE + FIRST), block[:400])
        self.assertEqual(SRC.count('schEdges = (x, z) => {'), 1)
        self.assertEqual(SRC.count('if (!schNear(x, z)) return [80, 0];'), 1)

    def test_the_gates_answer_is_the_walks_empty_answer(self):
        block = cut('    schEdges = (x, z) => {', '    };\n')
        self.assertIn('      return [Math.sqrt(best), side];\n', block)   # best 6400 and side 0 untouched: [80, 0]
        self.assertEqual(math.sqrt(6400), 80.0)
        # nothing between the first line and the walk can change best or side
        self.assertIn(FIRST + '   // 80 m, the reach of the ±2-cell search below\n'
                      '      const gx = Math.floor(x / EC), gz = Math.floor(z / EC);\n'
                      '      for (let a = -2; a <= 2; a++) for (let b2 = -2; b2 <= 2; b2++) {\n'
                      "        const l = egrid.get((gx + a) + ':' + (gz + b2)); if (!l) continue;\n", block)

    def test_the_reach_bitmap_is_the_walks_own_block(self):
        block = cut('  if (SCH_POLYS) {', '  // the ground height under and beside the river')
        # the edge grid has one writer, done before schEdges exists, and the bitmap is that grid's keys grown two cells
        self.assertEqual(block.count('egrid.set('), 1)
        self.assertLess(block.index('egrid.set('), block.index('schEdges = (x, z) => {'))
        self.assertNotIn('egrid.delete(', block)
        self.assertIn('    for (const key of egrid.keys()) {\n'
                      "      const c = key.indexOf(':'), gx = +key.slice(0, c) - ex0, gz = +key.slice(c + 1) - ez0;\n"
                      '      for (let a = -2; a <= 2; a++) for (let b2 = -2; b2 <= 2; b2++) { const i = gx + a, j = gz + b2; if (i >= 0 && j >= 0 && i < enx && j < enz) nearM[j * enx + i] = 1; }\n', block)
        self.assertIn('schNear = (x, z) => { const i = Math.floor(x / EC) - ex0, j = Math.floor(z / EC) - ez0; return i >= 0 && j >= 0 && i < enx && j < enz && nearM[j * enx + i] === 1; };', block)
        self.assertEqual(SRC.count('schNear = '), 2)   # the declaration and this one

    def test_river_carve_reads_the_edge_search_once_and_the_builders_nodes_are_the_tests(self):
        carve = cut('  function riverCarve(x, z, yy, floor) {', '\n  }\n')
        self.assertEqual(carve.count('schEdges('), 1)
        self.assertIn('    const e = schEdges(x, z);\n    const inside = e[0] < 8 ? e[1] < 0 : schRaster(x, z);', carve)
        # its callers: the two ground builders (the nodes this test walks) and drapeY (any point: the cell proof)
        self.assertEqual(len(re.findall(r'(?<![A-Za-z.])riverCarve\(', SRC)), 4)
        far = cut('    const mkFarGround = (x0, x1, z0, z1, cell, hole, tint, sink) => {', '\n    };')
        self.assertIn('      const nx = Math.max(1, Math.round((x1 - x0) / cell)), nz = Math.max(1, Math.round((z1 - z0) / cell));', far)
        self.assertIn('        ' + NODE_LINE, far)
        self.assertIn('yy = riverCarve(x, z, yy);', far)
        self.assertIn('      [W.x0, W.x1, W.z0, WIDEB.z0], [W.x0, W.x1, WIDEB.z1, W.z1],\n      [W.x0, WIDEB.x0, WIDEB.z0, WIDEB.z1], [WIDEB.x1, W.x1, WIDEB.z0, WIDEB.z1],\n'
                      '    ]) { const tS = performance.now(); mkFarGround(x0, x1, z0, z1, FAR_CELL, nwHole, true, false);', SRC)
        self.assertIn('mkFarGround(nwHole.x0, nwHole.x1, nwHole.z0, nwHole.z1, 50, null, true, true);', SRC)
        lay = cut("  step('Laying out the ground'", "  step('Shaping the waterfront'")
        self.assertIn('      const W = { x0: -3700, x1: 2300, z0: -4480, z1: 6400 };\n      const strips = [\n'
                      '        [W.x0, W.x1, W.z0, CORE_EXT.z0], [W.x0, W.x1, CORE_EXT.z1, W.z1],\n'
                      '        [W.x0, CORE_EXT.x0, CORE_EXT.z0, CORE_EXT.z1], [CORE_EXT.x1, W.x1, CORE_EXT.z0, CORE_EXT.z1],\n      ];', lay)
        self.assertIn('        const cell = 25, nx = Math.max(1, Math.round((x1 - x0) / cell)), nz = Math.max(1, Math.round((z1 - z0) / cell));', lay)
        self.assertIn('          ' + NODE_LINE, lay)
        self.assertIn('yy = riverCarve(x, z, yy, true);', lay)
        self.assertIn(NODE_LINE, NODE_MAIN)   # the harness's nodes() is the same line


class TheBitmapsAsText(unittest.TestCase):
    """exact only while both key sets are fixed once built: every writer, read"""

    def test_each_map_is_made_keyed_and_released_in_one_place(self):
        for name, made, released in (('terrainRoadGrid', 'terrainRoadGrid = new Map();', 'terrainRoadGrid = null; TRS.w = new Float32Array(9); TRS.n = 0;'),
                                     ('streetSurfaceIndex', 'streetSurfaceIndex = new Map();', 'streetSurfaceIndex=null;streetFootprints=[];')):
            self.assertEqual(SRC.count(name + '.set('), 1, name)
            self.assertEqual(SRC.count(name + '.delete('), 0, name)
            self.assertEqual(SRC.count(name + '.clear('), 0, name)
            self.assertEqual(SRC.count(made), 1, name)
            self.assertEqual(SRC.count(released), 1, name)
            # every assignment: the declaration, the Map, the bitmap hung on it, the release
            assigns = re.findall(r'(?<![A-Za-z.])' + name + r'(?:\.\w+)?\s*=(?!=)[^;,\n]*', SRC)
            self.assertEqual(len(assigns), 4, assigns)
            self.assertEqual(SRC.count(name + '.bits = cellBits(' + name + ');'), 1, name)

    def test_the_bitmap_is_cut_after_the_last_key(self):
        labels = cut('  function initStreetSurfaces() {', '  function streetLocal(')
        self.assertLess(labels.index('streetSurfaceIndex.set(key,[]);'), labels.index('streetSurfaceIndex.bits = cellBits(streetSurfaceIndex);'))
        self.assertTrue(labels.rstrip().endswith('streetSurfaceIndex.bits = cellBits(streetSurfaceIndex);   // Round 225: streetTriNear\'s bitmap, built once the keys are all in\n  }'), labels[-300:])
        patches = cut('  function initTerrainPatches() {', '  function rememberTerrainRoad(')
        self.assertEqual(patches.count('reserve('), 3)   # the corridors', the rail cuts' and the core's box, and no other
        self.assertLess(patches.rindex('reserve(['), patches.index('terrainRoadGrid.bits = cellBits(terrainRoadGrid);'))
        self.assertIn("const reserve = bounds => terrainPatchCells(bounds,key=>{if(!terrainRoadGrid.has(key))terrainRoadGrid.set(key,[]);});", patches)
        # the one function that fills the grid afterwards only fills a bin that is there
        fill = cut('  function rememberTerrainRoad(a,b,c) {', '  function outsideConvex(')
        self.assertIn('const bin=terrainRoadGrid.get(key);if(!bin)return;', fill)
        self.assertNotIn('.set(', fill)
        # one call each, in the build, the patches' first
        self.assertEqual(SRC.count('    initTerrainPatches();\n    initStreetSurfaces();\n'), 1)
        self.assertEqual(len(re.findall(r'(?<![A-Za-z])initTerrainPatches\(\)', SRC)), 2)
        self.assertEqual(len(re.findall(r'(?<![A-Za-z])initStreetSurfaces\(\)', SRC)), 2)

    def test_street_tri_near_builds_no_string(self):
        fn = cut('  function streetTriNear(ax,az,bx,bz,cx,cz) {', '\n  }\n')
        self.assertNotIn("':'", fn)
        self.assertNotIn('.has(', fn)
        self.assertIn('if(terrainRoadGrid && cellBitsHit(terrainRoadGrid.bits,Math.floor(x0/TERRAIN_PATCH_CELL),Math.floor(x1/TERRAIN_PATCH_CELL),Math.floor(z0/TERRAIN_PATCH_CELL),Math.floor(z1/TERRAIN_PATCH_CELL)))return true;', fn)
        self.assertIn('if(streetSurfaceIndex && cellBitsHit(streetSurfaceIndex.bits,Math.floor(x0/100),Math.floor(x1/100),Math.floor(z0/100),Math.floor(z1/100)))return true;', fn)
        # the Maps' own cells: terrainPatchCells and the label index floor the same quotients
        self.assertIn('for(let x=Math.floor(bounds[0]/TERRAIN_PATCH_CELL);x<=Math.floor(bounds[1]/TERRAIN_PATCH_CELL);x++)', SRC)
        self.assertIn('for(let gx=Math.floor((f.x-ex)/100);gx<=Math.floor((f.x+ex)/100);gx++)', SRC)
        # Round 220's rule stands: counted, never timed, the helpers too
        self.assertNotIn('performance.now()', cut('  function streetTriNear(ax,az,bx,bz,cx,cz) {', '  function rememberStreetTriangle('))


@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class ThePagesOwnCodeOverTheShippedData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name in ('schuylkill.json', 'wide.b64', 'city.b64', 'outskirts.b64', 'traffic.b64', 'overpasses.json', 'street_labels.json', 'street_sdf.json', 'parking_south.json'):
            if not (ROOT / name).exists():
                raise unittest.SkipTest('input absent: ' + name)
        cls.R = node_results()

    def test_the_blobs_were_walked_whole(self):
        for name, (count, left) in self.R['blobs'].items():
            self.assertGreater(count, 5000, name)
            self.assertEqual(left, 0, name)   # the record walk ended on the body's last word

    def test_no_answer_differs_on_any_point_the_page_asks_about(self):
        sets = self.R['sets']
        self.assertEqual(sorted(sets), sorted(['wide roads', 'city roads', 'outskirts roads', 'traffic', 'far grid 50 m', 'centreline 10 m', 'bank offsets',
                                               'far strips nodes', 'NW patch nodes', 'outer strips nodes']))
        for name, s in sets.items():
            self.assertEqual(s['diff'], 0, (name, s['first']))
        self.assertGreater(sum(s['n'] for s in sets.values()), 1900000)
        self.assertEqual(sets['far grid 50 m']['n'], 571 * 629)
        self.assertGreater(sets['city roads']['n'], 350000)      # 24,277 roads: 201,644 vertices at 30 m and their segments' midpoints
        self.assertGreater(sets['wide roads']['n'], 150000)
        self.assertGreater(sets['outskirts roads']['n'], 100000)
        self.assertGreater(sets['traffic']['n'], 300000)
        self.assertGreater(sets['bank offsets']['n'], 60000)

    def test_the_sets_are_live_on_both_sides_of_the_gate(self):
        sets = self.R['sets']
        # an edge in reach on thousands of points (the walk really ran), and none on most (the gate really answered)
        for name in ('wide roads', 'city roads', 'traffic', 'far grid 50 m', 'far strips nodes', 'outer strips nodes'):
            self.assertGreater(sets[name]['reach'], 1000, name)
            self.assertLess(sets[name]['near'], 0.5 * sets[name]['n'], name)
        off = sets['bank offsets']      # round the outline itself, either side of the reach
        self.assertGreater(off['reach'], 0.5 * off['n'])
        self.assertLess(off['reach'], off['n'])
        mid = sets['centreline 10 m']   # the middle of the channel, more than 80 m from either bank where the river is wide
        self.assertGreater(mid['reach'], 0.6 * mid['n'])
        self.assertGreater(mid['near'], 0.8 * mid['n'])
        self.assertLess(sets['outskirts roads']['near'], 100)    # the towns across the line: nearly every call was a wasted walk
        far = sets['far grid 50 m']
        self.assertLess(far['near'], 0.05 * far['n'])            # 2.4% of the far box
        for name, s in sets.items():
            self.assertLessEqual(s['reach'], s['near'], name)    # in reach is always inside the bitmap

    def test_the_counter_counts_every_call(self):
        for name, s in self.R['sets'].items():
            self.assertEqual(s['counted'], [s['n'], s['n']], name)   # 'sc' on the beacon and __dbg.perf read the same count as before
        self.assertEqual(self.R['answer']['calls'], 2)

    def test_the_answer_is_a_fresh_80_0(self):
        a = self.R['answer']
        self.assertTrue(a['fresh'])                # a caller that wrote into one answer would not reach the next
        self.assertTrue(a['is']); self.assertTrue(a['isArray']); self.assertEqual(a['len'], 2)
        self.assertEqual(a['b'], [80, 0]); self.assertEqual(a['p'], [80, 0])
        self.assertEqual(a['sqrt'], 80)
        self.assertEqual(a['odd'], 0)              # NaN, the infinities and minus zero: the same answer either way

    def test_every_cell_with_an_edge_in_the_walks_block_is_in_the_bitmap(self):
        c = self.R['cells']
        self.assertGreater(c['keys'], 500)
        self.assertEqual(c['keys'], c['plainKeys'])
        self.assertGreater(c['withEdge'], c['keys'])
        self.assertEqual(c['hidden'], 0)           # THE proof: the gate never answers for a cell the walk could find an edge from
        self.assertEqual(c['idle'], 0)             # and the bitmap is no wider than the block (no walk it lets through is certain to be empty)

    def test_river_carve_hands_every_ground_node_the_same_height(self):
        carve = self.R['carve']
        self.assertEqual(sorted(carve), ['NW patch', 'far strips', 'outer strips'])
        for name, c in carve.items():
            self.assertEqual(c['diff'], 0, name)
        self.assertGreater(carve['far strips']['n'], 300000)
        self.assertGreater(carve['outer strips']['n'], 90000)
        self.assertGreater(carve['NW patch']['n'], 25000)
        # live: the carve really lowered nodes in each (the channel and the 60 m band)
        for name in ('far strips', 'outer strips', 'NW patch'):
            self.assertGreater(carve[name]['carved'], 300, name)

    def test_street_tri_near_answers_as_the_round_124_walk(self):
        t = self.R['tri']
        self.assertEqual(t['diff'], 0)
        self.assertGreater(t['roadTris'], 500000)   # two a segment: 334,290 segments
        self.assertGreater(t['yes'], 50000)        # live: the core, the corridors and the labels' cells
        self.assertLess(t['yes'], 0.5 * t['n'])
        self.assertEqual(t['counted'], t['n'])     # TRI_NEAR counts every call

    def test_each_bitmap_is_its_maps_key_set(self):
        for name in ('road', 'label'):
            b = self.R['tri'][name]
            self.assertGreater(b['keys'], 300, name)
            self.assertEqual(b['on'], b['keys'], name)
            self.assertEqual(b['miss'], 0, name)
            self.assertLess(b['bytes'], 400000, name)   # a byte a cell of the keys' box, for the build only
            self.assertEqual(b['bytes'], b['box'][2] * b['box'][3], name)

    def test_a_released_map_takes_its_bitmap_with_it(self):
        r = self.R['tri']['released']
        self.assertTrue(r['both'])
        self.assertEqual(r['labelOnly'][0], r['labelOnly'][1])
        self.assertFalse(r['none'])
        self.assertEqual(r['empty'], [0, 0, False])

    def test_the_gate_is_what_makes_it_fast(self):
        # loose on purpose (the suite runs on busy machines): measured 14 to 42 times on the far grid
        far = self.R['sets']['far grid 50 m']
        self.assertLess(far['usGated'] * 3, far['usPlain'], far)
        self.assertLess(self.R['tri']['usBits'], self.R['tri']['usWalk'], self.R['tri'])


class UnderJavaScriptCore(unittest.TestCase):
    """the phone's engine: the same block, gated and not, over the far box and round the river's own outline"""

    def test_no_answer_differs(self):
        if shutil.which('osascript') is None:
            self.skipTest('JavaScriptCore via osascript unavailable')
        if not (ROOT / 'schuylkill.json').exists():
            self.skipTest('input absent: schuylkill.json')
        js = JXA_MAIN % {'data': (ROOT / 'schuylkill.json').read_text(), 'terrain': json.dumps(terrain()), 'river': river_js(), 'boxes': boxes_js()}
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(js)
        try:
            r = subprocess.run(['osascript', '-l', 'JavaScript', f.name], capture_output=True, text=True, timeout=900)
        finally:
            os.unlink(f.name)
        self.assertEqual(0, r.returncode, 'JXA failed: ' + (r.stderr or r.stdout)[:800])
        out = json.loads(r.stdout.strip())
        RESULTS['jsc'] = out
        self.assertEqual(out['far']['n'], 571 * 629)
        self.assertEqual(out['far']['diff'], 0)
        self.assertEqual(out['bank']['diff'], 0)
        self.assertGreater(out['far']['reach'], 5000)
        self.assertGreater(out['bank']['reach'], 30000)
        self.assertTrue(out['fresh']); self.assertTrue(out['is'])
        for k in ('far', 'bank'):
            self.assertEqual(out[k]['counted'], [out[k]['n'], out[k]['n']], k)
        self.assertLess(out['far']['usGated'] * 3, out['far']['usPlain'], out['far'])   # loose, as under Node


if __name__ == '__main__':
    import sys
    if '--numbers' in sys.argv:   # the measured figures, for the devlog: python3 tests/test_river_gate.py --numbers
        sys.argv.remove('--numbers')
        print(json.dumps(node_results(), indent=1))
    unittest.main()
