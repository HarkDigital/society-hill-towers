"""Round 220 (the measurement round), p07: the delivery, boot and first-frame facts on the beacons.

The beacon query gains the page's delivery (tx, enc, dec, net, di, fcp) and hc learns the validated 304 a repeat visit is;
beaconQuery previews any checkpoint's URL without sending, counting or deduplicating it (PERF.beaconQuery); a 'boot'
checkpoint goes out before build(); the ready beacon carries the build's facts (readyFacts: the steps' ms, the programs,
the flushes, what is still staged, the tower skins, the storefront wait and the prefetch's Blob); the enter beacon the
first frames' (enterFacts: frameNo, the first frame's ms, the tap's latency, the mirror's warm); and the perf, settled and
late beacons the ladder's first change and the pin images' causes (runFacts). Each function runs under Node against
stubbed state, the way tests/test_recovery.py runs beacon() through the TDZ; the text of the wiring is pinned."""
import json
from pathlib import Path
import unittest

try:
    from .test_recovery import run_node, cut          # python3 -m unittest tests.test_beacon_fields
except ImportError:
    from test_recovery import run_node, cut           # python3 -m unittest discover -s tests

ROOT = Path(__file__).resolve().parents[1]
BAD = ('—', '–', '·')   # no em dash, en dash or middot

# the two beacon functions, the one-line preview first (the first '\n  }\n' after it closes beacon() itself)
BEACON_START = '  function beaconQuery(st, extra) {'


class BeaconFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.both = cut(cls.src, BEACON_START, '\n  }\n', inclusive=True)
        cls.ready = cut(cls.src, '  function readyFacts(safe) {', '\n  }\n', inclusive=True)
        cls.enter = cut(cls.src, '  function enterFacts() {', '\n  }\n', inclusive=True)
        cls.runf = cut(cls.src, '  function runFacts() {', '\n  }\n', inclusive=True)
        cls.staged = cut(cls.src, '  PERF.staged = () => {', '\n  };\n', inclusive=True)

    # ---- the query apart from the send
    def test_the_preview_is_wired(self):
        s, b = self.src, self.both
        self.assertTrue(b.startswith('  function beaconQuery(st, extra) { return beacon(st, extra, true); }\n  function beacon(st, extra) {'))
        self.assertIn('const dry = arguments[2] === true;', b)
        self.assertIn('if (!BEACON) return null;', b)
        self.assertIn('if (!dry) {\n      if (st === \'err\') { if (++beaconErrs > 3) return null; }\n      else if (beaconSeen.has(st)) return null;\n      else beaconSeen.add(st);\n    }', b)
        self.assertIn('if (dry) return url;', b)
        self.assertLess(b.index('if (dry) return url;'), b.index("fetch(url, { method: 'POST', keepalive: true"))
        self.assertIn('  PERF.beaconQuery = beaconQuery;\n', s)
        self.assertEqual(s.count('function beacon(st, extra) {'), 1, 'the signature the other tests cut')
        # the recovery test still gets a beacon() that stands alone (readyFacts is read through safe)
        self.assertIn("if (st === 'ready') Object.assign(q, safe(() => readyFacts(safe), {}));", b)

    def test_the_delivery_fields_and_the_preview(self):
        script = r'''
const sent = [], out = {};
(function () {
  const BEACON = '/b', beaconSeen = new Set(); let beaconErrs = 0;
  const window = { devicePixelRatio: 2, matchMedia: () => ({ matches: false }) };
  const navigator = { hardwareConcurrency: 8, deviceMemory: 8 };
  const document = { lastModified: '10/22/2026 20:00:00' };
  let NAV = null, PAINT = [];
  const performance = { now: () => 5000.4, getEntriesByType: (t) => (t === 'navigation' ? (NAV ? [NAV] : []) : t === 'paint' ? PAINT : []) };
  const fetch = (url) => { sent.push(url); return { catch() {} }; };
BOTH
  const isTouch = false, TIER = 0, LITE_WHY = '';
  const renderer = { capabilities: { isWebGL2: true } }, DPR = { cur: 1.75 };
  const bootPrev = null;
  const zcField = () => 'r.1111.p';
  // a validated 304: a header-sized transfer, the whole body from the cache
  NAV = { type: 'navigate', transferSize: 812, encodedBodySize: 13050000, decodedBodySize: 30440000, requestStart: 12.5, responseEnd: 850.2, domInteractive: 1700.7, workerStart: 0 };
  PAINT = [{ name: 'first-paint', startTime: 900 }, { name: 'first-contentful-paint', startTime: 1234.6 }];
  beacon('a');
  // a full transfer
  NAV = { type: 'navigate', transferSize: 14200000, encodedBodySize: 13050000, decodedBodySize: 30440000, requestStart: 0, responseEnd: 840, domInteractive: 1700, workerStart: 0 };
  PAINT = [];
  beacon('b');
  // the old test: no bytes over the wire (a fresh cache hit)
  NAV = { type: 'reload', transferSize: 0, decodedBodySize: 26000000, workerStart: 0 };
  beacon('c');
  // no navigation entry at all
  NAV = null;
  beacon('d');
  // the preview sends nothing and counts nothing
  NAV = { type: 'navigate', transferSize: 812, encodedBodySize: 1, decodedBodySize: 200000, workerStart: 0 };
  out.preview = beaconQuery('ready', { ms: 7, fail: 0, sf: 'built' });
  out.sentAfterPreview = sent.length;
  beacon('ready', { ms: 8, fail: 0, sf: 'built' });
  out.readySent = sent.length;
  out.previewAgain = beaconQuery('ready');
  for (let i = 0; i < 5; i++) beaconQuery('err', { m: 'x' });
  for (let i = 0; i < 5; i++) beacon('err', { m: 'x' });
  out.errSent = sent.filter((u) => /st=err/.test(u)).length;
  out.returned = beacon('e');
  out.dup = beacon('e');
})();
(function () {
  const BEACON = null, beaconSeen = new Set(); let beaconErrs = 0;
BOTH
  out.none = beaconQuery('ready');
  out.noneSend = beacon('ready');
})();
console.log(JSON.stringify({ out, sent: sent.map((u) => Object.fromEntries(new URLSearchParams(u.split('?')[1]))) }));
'''.replace('BOTH', self.both)
        o = run_node(self, script)
        a, b, c, d = o['sent'][:4]
        self.assertEqual((a['st'], a['hc'], a['tx'], a['enc'], a['dec'], a['net'], a['di'], a['fcp']), ('a', '1', '812', '13050000', '30440000', '838', '1701', '1235'))
        self.assertEqual((b['hc'], b['tx'], b['net'], b['fcp']), ('0', '14200000', '840', ''))
        self.assertEqual((c['hc'], c['tx'], c['enc'], c['dec'], c['net'], c['di'], c['nav']), ('1', '0', '', '26000000', '', '', 'r'))
        self.assertEqual((d['hc'], d['tx'], d['enc'], d['dec'], d['net'], d['di'], d['fcp'], d['nav'], d['sw']), ('0', '', '', '', '', '', '', '', '0'))
        self.assertEqual((a['zc'], a['rd'], a['gl2']), ('r.1111.p', '1.75', '1'))
        out = o['out']
        self.assertTrue(out['preview'].startswith('/b?st=ready&'))
        self.assertIn('&ms=7&fail=0&sf=built', out['preview'])
        self.assertEqual(out['sentAfterPreview'], 4, 'a preview sends nothing')
        self.assertEqual(out['readySent'], 5, 'nor does it count as the checkpoint')
        self.assertIn('st=ready', out['previewAgain'], 'nor is it deduplicated')
        self.assertEqual(out['errSent'], 3, 'previews of err never spend the cap of three')
        self.assertTrue(out['returned'].startswith('/b?st=e&'))
        self.assertIsNone(out['dup'])
        self.assertIsNone(out['none'])
        self.assertIsNone(out['noneSend'])

    # ---- the ready checkpoint
    def test_the_ready_call_keeps_its_fields_and_gains_the_facts(self):
        s = self.src
        self.assertIn("beacon('ready', { ms: PERF.ready, fail: failures, sf: SF.state });", s)
        for k in ('sp:', 'prg:', 'fl:', 'flms:', 'flp:', 'pu:', 'pub:', 'tsk:', 'sfw:', 'sfb:'):
            self.assertIn(k, self.ready)
        script = r'''
const out = {};
(function () {
  const safe = (f, d) => { try { return f(); } catch (e) { return d; } };
  const PERF = { steps: [['Raising the outer districts', 12], ['Planting the street trees', 345.6]], flush: { n: 9, ms: 1234.6, p0: 40, p1: 118 }, staged: () => ({ n: 3, bytes: 2621440, mb: 2.5 }) };
  let renderer = { info: { programs: new Array(120) } }, pendingUpload = [1, 2, 3], TSKIN = { ms: 456.4 }, SF = { waitMs: 12, preBlob: 1 };
READY
  out.full = readyFacts(safe);
  TSKIN = { ms: { total: 300.2, note: 1, lay: 2 } }; SF = { waitMs: 0, preBlob: 0 };
  out.split = readyFacts(safe);
  renderer = undefined; TSKIN = { ms: null }; SF = {}; pendingUpload = []; PERF.flush = undefined; PERF.staged = undefined;
  out.bare = readyFacts(safe);
})();
console.log(JSON.stringify(out));
'''.replace('READY', self.ready)
        o = run_node(self, script)
        self.assertEqual(o['full'], {'sp': '12,345.6', 'prg': 120, 'fl': 9, 'flms': 1235, 'flp': '40:118', 'pu': 3, 'pub': 2.5, 'tsk': 456, 'sfw': 12, 'sfb': 1})
        self.assertEqual((o['split']['tsk'], o['split']['sfw'], o['split']['sfb']), (300, 0, 0), "TSKIN.ms as an object with a total; a zero is a zero")
        self.assertEqual(o['bare'], {'sp': '12,345.6', 'prg': '', 'fl': '', 'flms': '', 'flp': '', 'pu': 0, 'pub': '', 'tsk': '', 'sfw': '', 'sfb': ''})

    def test_the_flush_counter_and_what_stays_staged(self):
        s = self.src
        flush = cut(s, '  const flushUploads = (all) => {', '\n  };')
        self.assertIn('const F = PERF.flush, tf = performance.now();', flush)
        self.assertLess(flush.index('< 12)) return;'), flush.index('const F = PERF.flush'), 'the timer runs only on a flush that renders')
        self.assertLess(flush.index('if (F.p0 < 0) F.p0 = renderer.info.programs.length;'), flush.index('packResident(groupCity);'))
        self.assertLess(flush.index('pendingUpload.length = 0;'), flush.index('F.n++; F.ms += performance.now() - tf; F.p1 = renderer.info.programs.length;'))
        self.assertIn('  PERF.flush = { n: 0, ms: 0, p0: -1, p1: -1 };\n  PERF.staged = () => {', s)
        script = r'''
const pendingUpload = [], PERF = {};
STAGED
const buf = { array: new Uint16Array(8) };   // 16 bytes, shared by two interleaved attributes
pendingUpload.push({ geometry: { attributes: { position: { array: new Float32Array(3) }, normal: { array: null }, color: { isInterleavedBufferAttribute: true, data: buf }, aLane: { isInterleavedBufferAttribute: true, data: buf } }, index: { array: new Uint32Array(3) } } });
pendingUpload.push({ geometry: null });
pendingUpload.push({ geometry: { attributes: { position: { array: new Float32Array(262144) } }, index: null } });
const a = PERF.staged();
pendingUpload.length = 0;
console.log(JSON.stringify({ a, empty: PERF.staged() }));
'''.replace('STAGED', self.staged)
        o = run_node(self, script)
        self.assertEqual(o['a'], {'n': 2, 'bytes': 12 + 16 + 12 + 1048576, 'mb': 1.0}, 'a freed array nothing, a shared buffer once, the index too')
        self.assertEqual(o['empty'], {'n': 0, 'bytes': 0, 'mb': 0})

    def test_the_storefront_facts(self):
        s = self.src
        pre = cut(s, '  function sfArtPrefetch() {', '  function sfArtLoad() {')
        self.assertIn("sfArtPre[0].then((b) => { SF.preBlob = typeof Blob !== 'undefined' && b instanceof Blob ? 1 : 0; });", pre)
        step = cut(s, "  step('Dressing the storefronts'", '    let nearN = 0, baseN = 0;')
        self.assertIn('      let late = 0;\n      const waitT0 = performance.now();', step)
        self.assertIn("      clearTimeout(late);\n      sfArtP = null;", step)
        self.assertIn("      SF.waitMs = Math.round(performance.now() - waitT0);\n", step)
        self.assertLess(step.index('sfArtP = null;'), step.index('SF.waitMs ='))

    # ---- the enter, perf, settled and late checkpoints
    def test_the_enter_handler_is_wired(self):
        s = self.src
        pre = "  btnEnter.addEventListener('click', (e) => { PERF.tapT = e.timeStamp; });"
        self.assertIn(pre, s)
        self.assertLess(s.index(pre), s.index("  btnEnter.addEventListener('click', () => {\n    btnEnter.blur();"), 'the tap time is taken before the handler runs')
        enter = cut(s, "  btnEnter.addEventListener('click', () => {\n    btnEnter.blur();", '\n  });\n')
        self.assertIn("beacon('enter', { ms: Math.round(performance.now()), ...enterFacts() });", enter)
        self.assertIn('DPR.live = true; dprMode(); DPR.ch1 = 0; PACE.lastInput = performance.now();', enter)
        self.assertEqual(enter.count('...runFacts()'), 3)
        self.assertEqual(enter.count('...dprBeacon(), ...paceBeacon(), ...runFacts()'), 3)
        self.assertIn('if (DPR.live && !DPR.ch1) DPR.ch1 = DPR.chT; }', cut(s, '  function dprGo(k) {', '\n'))

    def test_the_enter_and_run_facts(self):
        script = r'''
const out = {};
(function () {
  const performance = { now: () => 10000 };
  let PERF = { tapT: 9985, frame1Ms: 123.4, enterT: 4000 }, frameNo = 7, MIRZ = { warmMs: 31, warmP: 4, warmN: 12 };
  let DPR = { ch1: 9100, nch: 3 }, PIN_OCC = { cause: { first: 1, old: 2, jump: 0, cadence: 14 }, syncN: 2, syncMs: 9.6 };
ENTER
RUN
  out.enter = enterFacts(); out.run = runFacts();
  PERF = { tapT: 1.7e12, enterT: 4000 }; MIRZ = {}; DPR = { ch1: 0 }; PIN_OCC = { cause: {} };
  out.enter2 = enterFacts(); out.run2 = runFacts();
  PERF = {}; out.enter3 = enterFacts();
})();
console.log(JSON.stringify(out));
'''.replace('ENTER', self.enter).replace('RUN', self.runf)
        o = run_node(self, script)
        self.assertEqual(o['enter'], {'fn': 7, 'f1': 123.4, 'tap': 15, 'mw': 31, 'mwp': 4, 'mwn': 12})
        self.assertEqual(o['run'], {'dc1': 5100, 'dcn': 3, 'poc': 'first:1,old:2,jump:0,cadence:14', 'pos': '2:10'})
        self.assertEqual(o['enter2'], {'fn': 7, 'f1': '', 'tap': '', 'mw': 0, 'mwp': 0, 'mwn': 0}, "an epoch timeStamp is not a latency")
        self.assertEqual(o['run2'], {'dc1': -1, 'dcn': 0, 'poc': '', 'pos': '0:0'})
        self.assertEqual(o['enter3']['tap'], '')

    # ---- the boot checkpoint
    def test_the_boot_checkpoint(self):
        s = self.src
        line = "  beacon('boot', { ms: Math.round(performance.now() - PERF.t0), cl: (() => { try { return typeof CLOUD3D.ms === 'number' ? CLOUD3D.ms : ''; } catch (e) { return ''; } })() });\n  build().then(() => {"
        self.assertIn(line, s, 'the boot beacon goes on the line before the build starts')
        self.assertEqual(s.count('build().then('), 1)

    # ---- the size of the longest beacon
    def test_the_ready_beacon_fits_the_request_line(self):
        script = r'''
const sent = [];
(function () {
  const BEACON = '/b', beaconSeen = new Set(); let beaconErrs = 0;
  const window = { devicePixelRatio: 2, matchMedia: () => ({ matches: true }) };
  const navigator = { hardwareConcurrency: 16, deviceMemory: 8, standalone: true };
  const document = { lastModified: '10/22/2026 20:00:00' };
  const NAV = { type: 'navigate', transferSize: 14200000, encodedBodySize: 13050000, decodedBodySize: 30440000, requestStart: 12.5, responseEnd: 850.2, domInteractive: 1700.7, workerStart: 1 };
  const performance = { now: () => 26900.4, getEntriesByType: (t) => (t === 'navigation' ? [NAV] : t === 'paint' ? [{ name: 'first-contentful-paint', startTime: 1234.6 }] : []) };
  const fetch = (url) => { sent.push(url); return { catch() {} }; };
BOTH
READY
  const isTouch = false, TIER = 0, LITE_WHY = 'abc';
  const steps = []; for (let i = 0; i < 48; i++) steps.push(['step ' + i, 1000 + i * 37]);
  const PERF = { steps, flush: { n: 12, ms: 2345.6, p0: 40, p1: 118 }, staged: () => ({ n: 20, bytes: 44040192, mb: 42.0 }) };
  const renderer = { capabilities: { isWebGL2: true }, info: { programs: new Array(123) } }, DPR = { cur: 1.75 };
  const bootPrev = { step: 'Lettering the landmarks and the rest', ctx: 'x'.repeat(80) };
  const zcField = () => 'rqca.1111.p0', pendingUpload = new Array(20), TSKIN = { ms: 1234 }, SF = { waitMs: 12345, preBlob: 1 };
  beacon('ready', { ms: 26900, fail: 0, sf: 'built' });
})();
console.log(JSON.stringify({ url: sent[0], bytes: sent[0].length }));
'''.replace('BOTH', self.both).replace('READY', self.ready)
        o = run_node(self, script)
        q = dict(p.split('=', 1) for p in o['url'].split('?')[1].split('&'))
        self.assertEqual(q['sp'].count('%2C'), 47, '48 steps, 47 commas')
        self.assertEqual((q['prg'], q['fl'], q['flms'], q['flp'], q['pu'], q['pub'], q['tsk'], q['sfw'], q['sfb'], q['sf']), ('123', '12', '2346', '40%3A118', '20', '42', '1234', '12345', '1', 'built'))
        self.assertLess(o['bytes'], 1200, 'the longest beacon, with its 48 steps, stays well under nginx\'s 8 KB request line: %d' % o['bytes'])

    def test_no_bad_characters_in_the_new_fields(self):
        for block in (self.both, self.ready, self.enter, self.runf, self.staged):
            for bad in BAD:
                self.assertNotIn(bad, block)


if __name__ == '__main__':
    unittest.main()
