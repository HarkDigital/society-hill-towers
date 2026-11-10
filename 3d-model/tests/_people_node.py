"""Round 227: the walkers' core under Node, shared by test_people.py and test_people_walk.py.

HARNESS cuts out of app.js, by its own marker lines, the traffic step's decoder, the linker, the street grid
(streetInside), the parked cars' half width and deck test, and the whole people section, and stands them on a stand-in
ground: flat by default, or ROUGH (hills, a river with dead water, a dead site, deck bands 8 m up: the things that make
the page's runs differ from any bake's). make(opt) returns the section's own functions and state. The drawn streets are
the runs themselves at their class's half width, which is what the page's road passes draw outside the core."""
import json
import os
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

HARNESS = r'''
const fs = require('fs'), path = require('path');
const ROOT = process.env.PP_ROOT;
const src = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8');
const cut = (a, b) => { const i = src.indexOf(a); if (i < 0) throw new Error('app.js lacks ' + a); const j = src.indexOf(b, i + a.length); if (j < 0) throw new Error('app.js lacks ' + b); return src.slice(i, j); };
const line = (a) => cut(a, '\n') + '\n';
const helpers = line('  function clamp(v, a, b) {') + line('  function lerp(a, b, t) {') + cut('  function densify(pts, step) {', '  // Bowyer-Watson') + cut('  function unb64(b64, name) {', '  // a real macrotask boundary');
const decodeBody = cut("    const bin = unb64(TRAFFIC_B64, 'TRAFFIC');", '    trafficPrepareGraph(trafficRuns);');
const linker = cut('  function trafficPrepareGraph(runs) {', "  step('Setting the traffic flowing'");
const streets = cut('  const SEPTA_RG_CELL = 36;', '  function septaSnapRoad(');
const parked = line('  const PARK_HW = [') + line('  const parkHalfW = (r) =>') + cut('  function parkedRunOK(r) {', '  const _pkS = {};');
const people = cut('  // ---- people on the sidewalks (Round 227', '  // ---- people on the sidewalks: the section ends');
const FLAT = `
const riverCorridor = () => false, demY = () => 0, siteY = () => 0, groundMeshLandY = () => null, inCapSite = () => false, inCore = () => false;
const bridgeDeckLift = () => null, ovpDeckY = OPT.deck || (() => null), sunkCutNear = () => null;`;
// tests/test_traffic_link.py's ground: the height test and the dead-water splits both fire
const ROUGH = `
const hill = (x, z) => 9 * Math.sin(x / 610) * Math.cos(z / 740) + 4 * Math.sin((x + z) / 233) + 0.0015 * z;
const riverCorridor = (x, z) => Math.abs(x * 0.8 + z * 0.6 + 2500) < 90;
const demY = (x, z) => riverCorridor(x, z) ? TERRAIN.water - 2 : hill(x, z);
const siteY = (x, z) => hill(x, z);
const groundMeshLandY = (x, z) => (Math.floor(x / 500) + Math.floor(z / 500)) % 3 === 0 ? null : hill(x, z) + 0.1;
const inCapSite = (x, z) => Math.abs(x + 300) < 120 && Math.abs(z - 200) < 120;
const inCore = (x, z) => Math.abs(x) < 1200 && Math.abs(z) < 900;
const bridgeDeckLift = (x, z) => Math.abs(x - 4200) < 60 && Math.abs(z + 900) < 400 ? 25 : null;
const ovpDeckY = (x, z, ux, uz) => Math.abs(ux) > 0.85 && Math.abs((((z % 1400) + 1400) % 1400) - 700) < 30 ? hill(x, z) + 8 : null;
const sunkCutNear = (x, z) => Math.abs(z - 1500) < 40 ? hill(x, z) - 6 : null;`;
function make(opt) {
  opt = opt || {};
  const body = helpers + `
const location = { search: OPT.search === undefined ? '?people=1' : OPT.search }, TIER2 = !!OPT.tier2, isTouch = !!OPT.touch;
const TERRAIN = { water: -7.34 }, LAYER = { road: 0.06 };
${opt.rough ? ROUGH : FLAT}
const bankFloor = () => -Infinity, roadHalfW = () => 4.5, trenchLaneY = (x, z, b) => b, brLaneFit = (p) => p;
const furnY = OPT.furnY || ((x, z) => siteY(x, z)), smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const clock = { y: 2026, m: 11, d: 10, minutes: 17 * 60 }, WXFX = { rain: 0, hail: 0, snow: 0 };
const VIEW = { rank: 2, calls: 0, refresh: 0 }, carSpotRank = (x, y, z) => { VIEW.calls++; return typeof VIEW.rank === 'function' ? VIEW.rank(x, y, z) : VIEW.rank; }, carRefreshView = () => { VIEW.refresh++; };
const camera = { position: { x: 0, y: 2, z: 0 } };
let TRAFFIC_B64 = B64, PEOPLE_WALK_B64 = WALK, trafficReady = false; const trafficRuns = [];
${streets}
${parked}
${people}
function decode() {
${decodeBody}
  return trafficRuns;
}
${linker}
function boot() {
  decode(); const pre = trafficRuns.length; trafficPrepareGraph(trafficRuns);
  for (const r of trafficRuns) for (let j = 0; j + 1 < r.xs.length; j++) septaRoadAdd(r.xs[j], r.zs[j], r.xs[j + 1], r.zs[j + 1], PARK_HW[r.cls], r.cls);
  trafficReady = true; return pre;
}
return { boot, runs: trafficRuns, PEOPLE, PEOPLE_ON, PEOPLE_DENS, VIEW, camera, clock, WXFX, PARK_HW, streetInside, parkedRunOK, peopleInit, peopleCross, peopleNext, peopleTrace, peopleFill, peopleOff, peopleClearCode, peopleDbg, peoplePin,
  peopleReset, peopleClosed, peopleShare, peopleHash, peoplePiece, next: () => _plN, piece: () => _plQ, walkB64: () => PEOPLE_WALK_B64 };`;
  const walk = opt.walk === undefined ? fs.readFileSync(path.join(ROOT, 'people_walk.b64'), 'utf8').trim() : opt.walk;
  return new Function('B64', 'WALK', 'atob', 'OPT', body)(fs.readFileSync(path.join(ROOT, 'traffic.b64'), 'utf8').trim(), walk, atob, opt);
}
// every piece's two sides traced, whatever the eye's budget
function traceAll(A) {
  const P = A.PEOPLE, N = A.runs.length;
  for (let i = 0; i < N; i++) { A.peopleCross(i); for (let k = 0; k <= P.xN[i]; k++) for (let b = 0; b < 2; b++) if (P.sideTrail[(P.pieceBase[i] + k) * 2 + b] === -1) A.peopleTrace(i, k, b); }
}
// fills until nothing near the eye is left untraced
function settle(A, out, x, y, z) { let n = 0, calls = 0; do { n = A.peopleFill(out, x, y, z); calls++; } while (A.PEOPLE.stat.pending && calls < 2000); return n; }
'''


def have():
    return bool(shutil.which('node')) and all((ROOT / f).exists() for f in ('traffic.b64', 'people_walk.b64'))


def node(script, timeout=900, gc=False):
    """Runs HARNESS + script under Node; the last line of its output, as JSON."""
    env = dict(os.environ, PP_ROOT=str(ROOT))
    cmd = ['node', '--max-old-space-size=4096'] + (['--expose-gc'] if gc else []) + ['-e', HARNESS + script]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    if r.returncode:
        raise AssertionError(r.stderr[-4000:])
    return json.loads(r.stdout.strip().splitlines()[-1])
