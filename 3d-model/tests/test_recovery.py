"""The recovery round: the tiers, the gate, the context-loss crumb, the beacon and the service worker.

Mike's iPhone had not finished a session on any build since Sep 19: killed for memory, reloaded once by WebKit from the
HTTP cache (whatever Cache-Control said), killed again inside WebKit's 30 s window, and then "A problem repeatedly
occurred". The boot block (cut from app.js) is run under Node against scripted breadcrumbs to check the tier arithmetic and
the gate condition; the context-loss handler runs in the same scope, so its crumb is checked end to end through the next
load; the beacon runs before and after the lets it reads (the TDZ); sw.js runs against a stub fetch."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(src, start, end, inclusive=False):
    i = src.index(start)
    j = src.index(end, i)
    return src[i:j + (len(end) if inclusive else 0)]


class Recovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.sw = (ROOT / 'sw.js').read_text()
        cls.boot = cut(cls.src, '  const BOOT_KEY = ', '  // the installable app:')
        cls.ctx = cut(cls.src, "  canvas.addEventListener('webglcontextlost', (e) => {", '\n  });\n', inclusive=True)
        cls.beacon = cut(cls.src, '  function beacon(st, extra) {', '\n  }\n', inclusive=True)
        cls.node = shutil.which('node')

    def node_run(self, script):
        if not self.node:
            self.skipTest('Node.js unavailable')
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    # ---- the boot block under Node: one call is one load, over one shared localStorage
    def loads(self, body):
        script = r'''
const store = new Map(), sess = new Map();
const mkStore = (m) => ({ getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => { m.set(k, String(v)); }, removeItem: (k) => { m.delete(k); } });
const LS = mkStore(store), SS = mkStore(sess);
const LOAD = new Function('isTouch', 'location', 'localStorage', 'sessionStorage', 'window', 'PERF', 'document', 'performance', 'canvas', 'beacon', 'reloads',
  BOOT + `
  let shownAt = -1e9;
  let glDead = false;
` + CTX + `
  return { TIER, LITE, TIER2, LITE_R, LITE_WHY, BOOT_GATE, bootDied, bootStick, bootFails, bootMark, bootClear, dead: () => glDead };`);
function load(o) {
  o = o || {};
  const listeners = {}, win = { addEventListener: (t, f) => { (listeners[t] = listeners[t] || []).push(f); }, removeEventListener: (t, f) => { listeners[t] = (listeners[t] || []).filter((g) => g !== f); } };
  let lost = null; const beacons = [], reloads = [];
  const docL = [];
  const doc = { visibilityState: o.hidden ? 'hidden' : 'visible', addEventListener: (t, f) => docL.push(f), removeEventListener: (t, f) => { const i = docL.indexOf(f); if (i >= 0) docL.splice(i, 1); }, getElementById: () => ({ style: {}, firstElementChild: {} }) };
  const perf = { now: () => (o.now == null ? 60000 : o.now) };
  const cv = { addEventListener: (t, f) => { if (t === 'webglcontextlost') lost = f; } };
  const S = LOAD(o.touch !== false, { search: o.search || '', reload: () => reloads.push(1) }, LS, SS, win, o.perf || {}, doc, perf, cv, (st, x) => beacons.push([st, x]), reloads);
  S.listeners = listeners; S.beacons = beacons; S.reloads = reloads;
  S.lose = () => lost({ preventDefault() {} });
  S.show = () => { doc.visibilityState = 'visible'; for (const f of docL.slice()) f(); };
  S.unload = () => { for (const f of listeners.pagehide || []) f(); S.bootClear(); };   // the reload's pagehide, and the unload's hidden and blur
  return S;
}
const crumb = (step, ageS, extra) => LS.setItem('philly3d.boot', JSON.stringify(Object.assign({ step, t: Date.now() - ageS * 1000, fails: 0, lite: false, tier: 0 }, extra || {})));
const saved = () => ({ tier: JSON.parse(LS.getItem('philly3d.tier') || 'null'), lite: LS.getItem('philly3d.lite'), boot: JSON.parse(LS.getItem('philly3d.boot') || 'null') });
const pick = (S) => ({ tier: S.TIER, lite: S.LITE, t2: S.TIER2, r: S.LITE_R, why: S.LITE_WHY, gate: S.BOOT_GATE, died: S.bootDied, stick: S.bootStick, fails: S.bootFails });
const reset = () => { store.clear(); sess.clear(); };
const out = {};
BODY
console.log(JSON.stringify(out));
'''
        script = script.replace('BOOT', json.dumps(self.boot), 1).replace('CTX', json.dumps(self.ctx), 1).replace('BODY', body)
        return self.node_run(script)

    def test_tier_arithmetic(self):
        o = self.loads(r'''
reset(); out.fresh = pick(load());
reset(); out.desk = pick(load({ touch: false }));
// a full build dies mid-build: tier 1, gated, sticky (the fortnight flag a bare timestamp, the tier its own key)
reset(); crumb('Sowing the grass', 5); out.first = pick(load()); out.firstSaved = saved();
// its gated tier-1 build dies too: the count reaches 2, tier 2 and its switches
crumb('Lettering the streets', 5, { fails: 1, lite: true, tier: 1 }); out.second = pick(load()); out.secondSaved = saved();
// and tier 2 dying again stays at tier 2, the lightest there is
crumb('Lettering the streets', 5, { fails: 2, lite: true, tier: 2 }); out.third = pick(load());
// a device on its saved tier 1 dies mid-build with a clean count: the same tier would die the same way, so tier 2
reset(); LS.setItem('philly3d.tier', JSON.stringify({ tier: 1, t: Date.now() })); crumb('Sowing the grass', 5, { lite: true, tier: 1 }); out.climb = pick(load());
// a crumb from before the tiers (lite only) climbs the same way
reset(); crumb('Sowing the grass', 5, { lite: true, tier: undefined }); out.oldCrumb = pick(load());
// a saved tier holds a fortnight and no longer
reset(); LS.setItem('philly3d.tier', JSON.stringify({ tier: 2, t: Date.now() - 13 * 864e5 })); out.held = pick(load());
reset(); LS.setItem('philly3d.tier', JSON.stringify({ tier: 2, t: Date.now() - 15 * 864e5 })); out.expired = pick(load());
// the session flag alone
reset(); sess.set('philly3d.litenow', '1'); out.sess = pick(load());
// forced tiers skip the gate; ?lite=0 also forgets both keys
reset(); crumb('Sowing the grass', 5); out.force2 = pick(load({ search: '?lite=2' }));
reset(); crumb('Sowing the grass', 5); LS.setItem('philly3d.tier', JSON.stringify({ tier: 2, t: Date.now() })); LS.setItem('philly3d.lite', String(Date.now()));
out.force0 = pick(load({ search: '?lite=0' })); out.force0Saved = saved();
reset(); out.deskForced = pick(load({ touch: false, search: '?dev=1&lite=1' }));
// the desktop never takes a tier or a gate from a crumb
reset(); crumb('Sowing the grass', 5); out.deskDied = pick(load({ touch: false }));
''')
        self.assertEqual(o['fresh'], {'tier': 0, 'lite': False, 't2': False, 'r': 8000, 'why': '', 'gate': False, 'died': False, 'stick': False, 'fails': 0})
        self.assertEqual(o['desk']['tier'], 0)
        f = o['first']
        self.assertEqual((f['tier'], f['lite'], f['t2'], f['gate'], f['stick'], f['fails'], f['why']), (1, True, False, True, True, 1, 'cts'))
        self.assertEqual(o['firstSaved']['tier']['tier'], 1)
        self.assertRegex(o['firstSaved']['lite'], r'^\d{13}$', 'LITE_KEY must stay a bare timestamp: the cached builds read it with a unary plus')
        self.assertEqual(o['firstSaved']['boot']['step'], 'start')
        self.assertEqual(o['firstSaved']['boot']['tier'], 1, 'the crumb says which tier its load ran')
        s = o['second']
        self.assertEqual((s['tier'], s['t2'], s['r'], s['gate'], s['fails']), (2, True, 5000, True, 2))
        self.assertEqual(o['secondSaved']['tier']['tier'], 2)
        self.assertEqual((o['third']['tier'], o['third']['fails']), (2, 3))
        self.assertEqual(o['climb']['tier'], 2)
        self.assertEqual(o['oldCrumb']['tier'], 2)
        self.assertEqual((o['held']['tier'], o['held']['gate'], o['held']['why']), (2, False, 't'))
        self.assertEqual(o['expired']['tier'], 0)
        self.assertEqual((o['sess']['tier'], o['sess']['why']), (1, 'x'))
        self.assertEqual((o['force2']['tier'], o['force2']['gate'], o['force2']['why']), (2, False, 'f'))
        self.assertEqual((o['force0']['tier'], o['force0']['gate']), (0, False))
        self.assertIsNone(o['force0Saved']['tier'])
        self.assertIsNone(o['force0Saved']['lite'])
        self.assertEqual((o['deskForced']['tier'], o['deskForced']['lite']), (1, True))
        self.assertEqual((o['deskDied']['tier'], o['deskDied']['gate'], o['deskDied']['died']), (0, False, True))

    def test_running_deaths_and_the_gate_crumb(self):
        o = self.loads(r'''
// a lite session killed once while running: lite for this load only (the Round 154 rule), still gated
reset(); crumb('running', 30, { lite: true, tier: 1 }); out.liteRun = pick(load()); out.liteRunSaved = saved();
// the full build killed while running: sticky (the recovery round)
reset(); crumb('running', 30); out.fullRun = pick(load()); out.fullRunSaved = saved();
// a second death while running
reset(); crumb('running', 30, { lite: true, tier: 1, fails: 1 }); out.twoRun = pick(load());
// 'running' is fresh for 3 minutes, a build step for 30
reset(); crumb('running', 200); out.staleRun = pick(load());
reset(); crumb('Sowing the grass', 25 * 60); out.lateStep = pick(load());
reset(); crumb('Sowing the grass', 31 * 60); out.staleStep = pick(load());
// a crumb left at the gate is no death and no gate, but its count and its tier carry
reset(); crumb('gate', 60, { fails: 1, lite: true, tier: 1 }); out.gate = pick(load());
// and the next death after it counts from there
crumb('Sowing the grass', 5, { fails: 1, lite: true, tier: 1 }); out.afterGate = pick(load());
''')
        lr = o['liteRun']
        self.assertEqual((lr['tier'], lr['died'], lr['stick'], lr['gate']), (1, True, False, True))
        self.assertIsNone(o['liteRunSaved']['tier'])
        self.assertIsNone(o['liteRunSaved']['lite'])
        fr = o['fullRun']
        self.assertEqual((fr['tier'], fr['stick'], fr['gate']), (1, True, True))
        self.assertEqual(o['fullRunSaved']['tier']['tier'], 1)
        self.assertEqual((o['twoRun']['tier'], o['twoRun']['stick']), (2, True))
        self.assertFalse(o['staleRun']['died'])
        self.assertTrue(o['lateStep']['died'])
        self.assertFalse(o['staleStep']['died'])
        g = o['gate']
        self.assertEqual((g['died'], g['gate'], g['fails'], g['tier'], g['why']), (False, False, 1, 1, 'g'))
        self.assertEqual((o['afterGate']['fails'], o['afterGate']['tier']), (2, 2))

    def test_the_context_loss_crumb(self):
        o = self.loads(r'''
// a loss in front: the crumb says 'ctxlost', survives the reload's pagehide and the unload's clears, and the reload is gated
reset(); let S = load({ perf: { ready: 12000 } }); S.lose(); out.front = { dead: S.dead(), reloads: S.reloads.length, beacon: S.beacons.map((b) => b[0]), pagehide: (S.listeners.pagehide || []).length };
S.unload(); S.bootMark('running'); out.frontCrumb = saved().boot.step;
out.next = pick(load());
// a loss behind: no crumb, no gate
reset(); S = load({ hidden: true }); S.lose(); out.behindWait = S.reloads.length; S.show(); S.unload(); out.behindCrumb = saved().boot; out.behindReloads = S.reloads.length; out.behindNext = pick(load());
// 'ctxlost' is fresh for 3 minutes, like 'running'
reset(); crumb('ctxlost', 200, { lite: true, tier: 1 }); out.stale = pick(load());
// a second loss inside 2 minutes does not reload: it stops drawing
reset(); S = load(); sess.set('philly3d.ctxlost', String(Date.now() - 30000)); S.lose(); out.noReload = { dead: S.dead(), reloads: S.reloads.length };
// the desktop never reloads, and stops drawing too
reset(); S = load({ touch: false }); S.lose(); out.desk = { dead: S.dead(), reloads: S.reloads.length };
''')
        self.assertEqual(o['front'], {'dead': True, 'reloads': 1, 'beacon': ['ctxlost'], 'pagehide': 0})
        self.assertEqual(o['frontCrumb'], 'ctxlost')
        n = o['next']
        self.assertEqual((n['died'], n['gate'], n['tier'], n['fails']), (True, True, 1, 1))
        self.assertEqual((o['behindWait'], o['behindReloads']), (0, 1), 'a loss behind reloads once the page is in front again')
        self.assertIsNone(o['behindCrumb'])
        self.assertEqual((o['behindNext']['died'], o['behindNext']['gate']), (False, False))
        self.assertFalse(o['stale']['died'])
        self.assertEqual(o['noReload'], {'dead': True, 'reloads': 0})
        self.assertEqual(o['desk'], {'dead': True, 'reloads': 0})

    def test_review_fixes(self):
        """The review of the recovery round: a second context loss inside the two-minute guard is still a death (the tap's
        reload used to erase it); a tier-2 death refreshes the tier's fortnight; the gate waits out WebKit's 30 s window;
        the build stops on a dead context."""
        o = self.loads(r'''
reset(); let S = load({ perf: { ready: 12000 } }); sess.set('philly3d.ctxlost', String(Date.now() - 30000)); S.lose(); S.unload(); S.bootMark('running');
out.second = { crumb: saved().boot && saved().boot.step, reloads: S.reloads.length, beacon: S.beacons.map((b) => b[0]) }; out.secondNext = pick(load());
// a loss before ready leaves the dying step's crumb (a death mid-build: sticky, the tier above), in go() and in the overlay
reset(); S = load(); S.bootMark('Sowing the grass'); S.lose(); S.unload(); out.preReady = saved().boot.step; out.preReadyNext = pick(load());
reset(); S = load(); sess.set('philly3d.ctxlost', String(Date.now() - 30000)); S.bootMark('Sowing the grass'); S.lose(); S.unload(); out.preReadyOverlay = saved().boot.step;
reset(); S = load({ hidden: true }); sess.set('philly3d.ctxlost', String(Date.now() - 30000)); S.lose(); S.unload(); out.secondBehind = saved().boot;
reset(); LS.setItem('philly3d.tier', JSON.stringify({ tier: 2, t: Date.now() - 13 * 864e5 })); crumb('Sowing the grass', 5, { lite: true, tier: 2 }); out.t2 = pick(load()); out.t2Saved = saved().tier;
''')
        self.assertEqual(o['second']['crumb'], 'ctxlost', 'a second loss in front must leave its crumb through the tap reload')
        self.assertEqual(o['second']['reloads'], 0)
        self.assertEqual(o['second']['beacon'], ['ctxlost'])
        n = o['secondNext']
        self.assertEqual((n['died'], n['gate'], n['fails']), (True, True, 1))
        self.assertIsNone(o['secondBehind'], 'a loss behind is no death')
        self.assertEqual(o['preReady'], 'Sowing the grass', 'before ready the dying step names the death')
        p = o['preReadyNext']
        self.assertEqual((p['died'], p['stick'], p['gate'], p['tier']), (True, True, True, 1))
        self.assertEqual(o['preReadyOverlay'], 'Sowing the grass')
        self.assertEqual(o['t2']['tier'], 2)
        self.assertEqual(o['t2Saved']['tier'], 2)
        import time
        self.assertGreater(o['t2Saved']['t'], (time.time() - 3600) * 1000, 'a tier-2 death must refresh the tier key')
        g = cut(self.src, '  function bootGate() {', '\n  }\n')
        self.assertIn('loadedAt + 32000 - performance.now()', g, 'the gate waits out WebKit\'s 30 s crash window after the load event')
        self.assertIn("'Starting in ' + Math.ceil(left / 1000) + ' s'", g)
        b = cut(self.src, '  async function build() {', '    PERF.ready = ')
        self.assertIn('if (glDead) break;', b, 'the build stops on a dead context')

    def test_the_frame_loop_stops_on_a_dead_context(self):
        head = '  function frame(now, once) {\n'
        after = self.src[self.src.index(head) + len(head):]
        self.assertTrue(after.startswith('    if (glDead) return;'), 'the first thing a frame does is check the context')

    def test_the_gate_is_wired(self):
        s = self.src
        b = cut(s, '  async function build() {', '    let failures = 0;')
        self.assertIn('if (BOOT_GATE) await bootGate();', b, 'the gate waits before the first step')
        g = cut(s, '  function bootGate() {', '\n  }\n')
        self.assertIn("bootMark('gate');", g)
        self.assertIn("btnEnter.textContent = 'Load the City';", g)
        self.assertIn("'Philadelphia ran out of memory on this device last time. Tap to load a lighter city.'", g)
        self.assertIn("'This device ran out of memory again. Tap to load the lightest city.'", g)
        for bad in ('—', '·', '–'):
            self.assertNotIn(bad, g, 'no em dash or middot in the gate copy')
        click = cut(s, "  btnEnter.addEventListener('click', () => {", "beacon('enter'")
        self.assertIn('if (gateGo) { gateGo(); return; }', click, "the gate's tap starts the build and does not enter")
        self.assertIn('const BOOT_GATE = isTouch && bootDied && !/[?&]lite=/.test(location.search);', s)
        # the build is still started once, the old way
        self.assertEqual(len(re.findall(r'\bbuild\(\)\.then\(', s)), 1)

    def test_every_step_beacons_on_touch(self):
        self.assertIn("if (isTouch || BEACON_STEPS.has(s.msg)) beacon('step:' + s.msg,", self.src)

    def test_the_tier_2_switches(self):
        s = self.src
        self.assertIn('const LITE_R = TIER2 ? 5000 : 8000;', s)
        self.assertIn('LITE ? ((x, z) => x * x + z * z < LITE_R * LITE_R) : null, true)', s, 'the far ring reads LITE_R')
        self.assertIn('if (outer && TIER2) continue;', cut(s, "  step('Planting the street trees',", "  step('Sowing the grass'"))
        self.assertIn("if (TIER2 && typeof TRAFFIC_B64 !== 'undefined') TRAFFIC_B64 = null;", cut(s, "  step('Setting the traffic flowing',", '    const bin = unb64(TRAFFIC_B64'))
        self.assertIn('if (TIER2) { ROOF_KIT.buf = null; ROOF_KIT.n = 0; return; }', cut(s, "  step('Fitting out the rooftops',", '    const B = ROOF_KIT.buf'))

    def test_the_beacon_survives_the_tdz(self):
        script = r'''
const sent = [];
(function () {
  const BEACON = '/b', beaconSeen = new Set(); let beaconErrs = 0;
  const window = { devicePixelRatio: 3, matchMedia: () => ({ matches: true }) };
  const navigator = { hardwareConcurrency: 6, deviceMemory: 0 };
  const document = { lastModified: '09/24/2026 20:00:00' };
  const performance = { now: () => 1234.4, getEntriesByType: () => [{ type: 'reload', transferSize: 0, decodedBodySize: 26000000, workerStart: 0 }] };
  const fetch = (url) => { sent.push(url); return { catch() {} }; };
BEACON_FN
  beacon('early');   // every let and const below is still in its TDZ
  const isTouch = true, TIER = 2, LITE_WHY = 'cts';
  let bootPrev = { step: 'Lettering the landmarks and the rest', t: 0 };
  let renderer = { capabilities: { isWebGL2: true } };
  const DPR = { cur: 0.72 };
  beacon('late', { ms: 5 });
})();
console.log(JSON.stringify(sent.map((u) => Object.fromEntries(new URLSearchParams(u.split('?')[1])))));
'''.replace('BEACON_FN', self.beacon)
        early, late = self.node_run(script)
        self.assertEqual((early['st'], early['tier'], early['lr'], early['rd'], early['pv'], early['gl2'], early['tch']), ('early', '', '', '', '', '0', ''))
        self.assertEqual((late['tier'], late['lr'], late['rd'], late['pv'], late['gl2'], late['tch']), ('2', 'cts', '0.72', 'Lettering the landmarks ', '1', '1'))
        self.assertEqual((late['sa'], late['nav'], late['hc'], late['sw'], late['ms']), ('1', 'r', '1', '0', '5'))
        self.assertEqual(len(late['pv']), 24)

    def test_the_service_worker_fetches_navigations_from_the_network(self):
        self.assertNotIn('new Request(', self.sw, 'a Request built on a navigate request throws in Chrome')
        script = r'''
(function () {
const listeners = {};
const self = { addEventListener: (t, f) => { listeners[t] = f; }, skipWaiting() {}, clients: { claim() {} } };
let calls = [], mode = 'ok';
const fetch = (req, init) => {
  calls.push([typeof req === 'string' ? req : 'request:' + req.cache, init || null]);
  if (typeof req !== 'string') return Promise.resolve({ tag: 'request', redirected: false });
  if (mode === 'offline') return Promise.reject(new TypeError('offline'));
  return Promise.resolve({ tag: 'network', redirected: mode === 'redirect' });
};
SW
const nav = { mode: 'navigate', method: 'GET', url: 'https://philly3d.com/#v=1', cache: 'force-cache' };
async function fire(request) { calls = []; let p = null; listeners.fetch({ request, respondWith: (x) => { p = x; } }); return { answered: !!p, r: p ? (await p).tag : null, calls }; }
(async () => {
  const out = {};
  out.ok = await fire(nav);
  mode = 'offline'; out.offline = await fire(nav);
  mode = 'redirect'; out.redirect = await fire(nav);
  mode = 'ok'; out.sub = await fire({ mode: 'no-cors', method: 'GET', url: 'https://philly3d.com/x.json', cache: 'default' });
  out.post = await fire({ mode: 'navigate', method: 'POST', url: 'https://philly3d.com/', cache: 'default' });
  console.log(JSON.stringify(out));
})();
})();
'''.replace('SW', self.sw)
        o = self.node_run(script)
        self.assertEqual(o['ok']['r'], 'network')
        self.assertEqual(o['ok']['calls'], [['https://philly3d.com/#v=1', {'cache': 'no-cache', 'credentials': 'same-origin'}]])
        self.assertEqual(o['offline']['r'], 'request')
        self.assertEqual(o['offline']['calls'][1], ['request:force-cache', None])
        self.assertEqual(o['redirect']['r'], 'request')
        self.assertFalse(o['sub']['answered'])
        self.assertFalse(o['post']['answered'])


if __name__ == '__main__':
    unittest.main()
