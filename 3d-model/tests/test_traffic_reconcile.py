"""Round 225: trafficReconcile without four walks of every run, and the advance and the draw without two more a frame.

trafficReconcile ran once a second (and on every frame of a time-slider drag) and walked all 46,131 runs four times: a
three-argument Math.hypot and two smoothsteps a run, every run's cars for the inbound counts, a Math.sin hash of a large
argument a run, and a filter() array a run, though only a run within CAR_VIEW.warm of the eye can want a car. It now
passes a run by in plan (want 0, target 0, inbound 0), reads the jitter from a table, and works the targets and the needs
from one list of the runs that are near or still hold a car. trafficAdvance and trafficDraw, which walked every run every
frame to find the few hundred holding cars, walk trafficBusy in run order.

Nothing may change: tests/traffic_recon_checks.js evaluates the page's traffic section twice over the runs of the shipped
traffic.b64 (the page's own decoder and linker), once as it stands and once with the functions as they stood at 1b476c2
put back (their text is kept in that file), hands both the same dice and flies both down the same path as a computer and
as a phone: a seeding, a moving eye, a jump that leaves the whole fleet behind, heights from 2 to 2,500 m, a 3 am and a
weekend clock, blocks that close on the cars standing in them (the closures' own line), a time-slider drag and a random
sweep. After every reconcile every run's want, target and
inbound and every need's run, shortage and priority must be the same value (Object.is), and after every frame every car
on every run (place, speed, fade, leader, destination, route), the counters behind __dbg.trafficChurn, the dice, and
every instance the draw wrote (matrix, fade, finish, colour, lamp, and which car holds which slot). A shorter phone
flight runs under JavaScriptCore through osascript, whose Math.sin does not return V8's bits: the jitter table must be
the engine's own. The run also reports the ms each took, printed below.

The reference is only worth what its text is: each of the four old texts in the harness is pinned here by its sha256,
taken from git's 1b476c2 copy of app.js, so the function and its reference cannot be edited together unnoticed."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ROOT / 'tests' / 'traffic_recon_checks.js'


def cut(text, a, b):
    i = text.index(a)
    return text[i:text.index(b, i + len(a))]


# The harness's reference texts as git holds them at 1b476c2 (Round 224): trafficReconcile whole, from its header to the
# line before TRAFFIC_DAYS, and the three one-line walks, each of which stood exactly once in that app.js. (length in
# characters, sha256 of the UTF-8 text.) To check one by hand:
#   git show 1b476c2:3d-model/app.js | python3 -c "import sys,hashlib;t=sys.stdin.read();i=t.index('  function trafficReconcile(now) {');print(hashlib.sha256(t[i:t.index('  const TRAFFIC_DAYS=',i)].encode()).hexdigest())"
# A pin that has to move means the proof is being run against something other than the function this round replaced.
OLD_TEXTS = {
    'OLD_RECONCILE': (2219, 'f47a270b83880bb13175fc01eba92afde7a45a66941f01e35132aafcef74897e'),
    'OLD_FEED': (74, '99ff61d0151b92b27d1d8733e6b1b73507b9de49bacb7dc0a7d6fdc5570ec3a8'),
    'OLD_ADVANCE': (69, '4099577d5297bcd37d45ef412dae62420bf506cf4c6ac6f828c16e23b516b822'),
    'OLD_DRAW': (58, 'fe02a8f34009bcc13738d721b4d5986cd5dfcb88d2399ddaf1002f5313cb1d83'),
}


def old_texts(harness):
    """The four reference texts as the harness's JavaScript evaluates them: one String.raw template (no substitution, no
    backtick: the text between the backticks is the string) and three single-quoted lines whose only escape is \\n."""
    out = {}
    head = 'const OLD_RECONCILE = String.raw`'
    if harness.count(head) != 1:
        raise AssertionError('OLD_RECONCILE is not declared exactly once')
    out['OLD_RECONCILE'] = cut(harness, head, '`')[len(head):]
    if '${' in out['OLD_RECONCILE']:
        raise AssertionError('a substitution in the String.raw reference')
    for name in ('OLD_FEED', 'OLD_ADVANCE', 'OLD_DRAW'):
        m = re.findall(r"^const %s = '([^'\n]*)';$" % name, harness, re.M)
        if len(m) != 1:
            raise AssertionError('%s is not declared exactly once as one single-quoted line' % name)
        if '\\' in m[0].replace('\\n', ''):
            raise AssertionError('%s carries an escape other than a newline' % name)
        out[name] = m[0].replace('\\n', '\n')
    return out


class TrafficReconcileText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.fn = cut(cls.src, '  function trafficReconcile(now) {', '  const TRAFFIC_DAYS=')
        cls.harness = CHECKS.read_text()
        cls.olds = old_texts(cls.harness)
        cls.old = cls.olds['OLD_RECONCILE']

    def test_the_reference_is_pinned_by_its_hash(self):
        # the proof rests on these four texts being 1b476c2's: a grep of a few of their lines would pass an edit made to
        # the function and its reference together, a hash does not
        self.assertEqual(sorted(self.olds), sorted(OLD_TEXTS))
        for name, (length, digest) in OLD_TEXTS.items():
            text = self.olds[name]
            self.assertEqual(len(text), length, name)
            self.assertEqual(hashlib.sha256(text.encode('utf-8')).hexdigest(), digest, name)
        # and the harness puts each back by name, once, into a copy of the page's section: the old section is nothing else
        h = self.harness
        for line in ('  let oldSection = once(pageSection, NEW_RECONCILE, OLD_RECONCILE);\n',
                     '  oldSection = once(oldSection, NEW_FEED, OLD_FEED);\n',
                     '  oldSection = once(oldSection, NEW_ADVANCE, OLD_ADVANCE);\n',
                     '  oldSection = once(oldSection, NEW_DRAW, OLD_DRAW);\n',
                     "      const A = make(oldSection, touch, shared, 4242), B = make(pageSection, touch, shared, 4242);\n",
                     "      const A = make(oldSection, touch, shared, 77), B = make(pageSection, touch, shared, 77);\n"):
            self.assertEqual(h.count(line), 1, line)
        self.assertEqual(h.count('oldSection = '), 4)          # nothing else is done to it
        self.assertEqual(len(re.findall(r'\bOLD_(?:RECONCILE|FEED|ADVANCE|DRAW)\b', h)), 8)   # each declared once and used once

    def test_the_reference_is_the_old_function(self):
        # the four walks, the hash and the filter this round took out are what the reference still does
        self.assertEqual(self.old.count('for(const r of trafficRuns)'), 2)
        self.assertEqual(self.old.count('for(let i=0;i<trafficRuns.length;i++) {'), 2)
        self.assertIn('hash01(i*7.3)', self.old)
        self.assertIn('alive=r.cars.filter(c=>!c.die)', self.old)

    def test_one_walk_of_the_runs_and_no_array_a_run(self):
        f = self.fn
        self.assertEqual(f.count('for(let i=0;i<N;i++) {'), 1)
        self.assertNotIn('of trafficRuns', f)
        self.assertNotIn('trafficRuns.length;i++', f)
        self.assertNotIn('.filter(', f)
        self.assertNotIn('hash01(i*7.3)', f)
        # far runs are passed by in plan, a metre past the warm radius, with all three numbers written; a far run still
        # on trafficBusy goes on the list, so a car left on it is retired
        self.assertIn('const far2=trafficJitOk&&CAR_VIEW.warm>CAR_VIEW.near&&isFinite(frac)?(CAR_VIEW.warm+1)*(CAR_VIEW.warm+1):Infinity;', f)
        self.assertIn('      r.inbound=0;\n      if(dx*dx+dz*dz>=far2){r.want=0;r.target=0;if(r.busy)work[nw++]=i;continue;}\n', f)
        # the near runs take the old arithmetic, operand for operand
        self.assertIn('const d=Math.hypot(dx,dz,cy-(r.ys[0]||0));', f)
        self.assertIn('const r=runs[i],dx=r.mx-cx,dz=r.mz-cz;', f)
        self.assertIn('cx=camera.position.x,cy=camera.position.y,cz=camera.position.z;', f)
        for line in ('      const w=(1-smooth(CAR_VIEW.near,CAR_VIEW.warm,d))*(1+.65*(1-smooth(450,1500,d)));\n',
                     '      r.want=r.closed?0:r.aadt*frac/TRAFFIC_DENSITY_KMH[r.cls]*(r.len/1000)*w;implied+=r.want;\n',
                     '    TRAFFIC.scale=Math.min(1,TRAFFIC.cap*.85/Math.max(1,implied));\n'):
            self.assertIn(line, f)
            self.assertIn(line, self.old)
        self.assertIn('r.target=Math.min(50,Math.floor(r.want*TRAFFIC.scale+jit[i]));', f)

    def test_the_needs_and_the_births_are_the_old_text(self):
        # from the shortage test to the end: the priority, the sort, the budgets, the round robin, carSpawn and carFeed
        tail = '      if(shortage>0) {\n'
        self.assertEqual(self.fn[self.fn.index(tail):], self.old[self.old.index(tail):])
        for line in ('        if(carSpotRank(car.x,car.y,car.z)===0||now-car.born<CAR_MIN_LIFE)continue;\n',
                     '        if(car.destination?.want>0)continue;\n',
                     "        if(extra>0||r.want===0){carDeath(car,now,'dieRetire',r);extra--;}\n"):
            self.assertIn(line, self.fn)
            self.assertIn(line, self.old)

    def test_the_table_is_never_made_in_the_linker(self):
        # tests/test_traffic_link.py compares every run's keys with the old linker's, and the step's decode body runs there
        linker = cut(self.src, '  function trafficPrepareGraph(runs) {', "  step('Setting the traffic flowing'")
        step = cut(self.src, "  step('Setting the traffic flowing'", '  function trafficFrac() {')
        for text in (linker, step):
            self.assertNotIn('trafficIndex', text)
            self.assertNotIn('.ri', text)
        idx = cut(self.src, '  function trafficIndex() {', '  function trafficBusySort() {')
        self.assertIn('const h=hash01(i*7.3);trafficJit[i]=h;if(!(h<1))trafficJitOk=false;trafficRuns[i].ri=i;', idx)
        self.assertIn('if(trafficJit.length===n&&(!n||trafficRuns[n-1].ri===n-1))return;', idx)
        self.assertIn('trafficJit=new Float64Array(n);', idx)   # the hash's own doubles, not rounded to float32

    def test_the_frame_walks_the_busy_runs_in_run_order(self):
        adv = cut(self.src, '  function trafficAdvance(now,dt) {', '  // the realism pass: past CAR_LOD_D a car is its far copy')
        draw = cut(self.src, '  function trafficDraw(night) {', '  function updateTraffic(now,dt) {')
        for text in (adv, draw):
            self.assertNotIn('of trafficRuns', text)
            self.assertEqual(text.count('trafficBusySort();'), 1)
        self.assertIn('for(let q=0,nq=trafficBusy.length;q<nq;q++)for(let r=trafficBusy[q],i=r.cars.length-1;i>=0;i--) {', adv)
        self.assertLess(adv.index('trafficLeaders();'), adv.index('trafficBusySort();'))   # the leaders' walk drops the empty runs first
        self.assertIn('for(const r of trafficBusy)for(const car of r.cars) {', draw)
        feed = cut(self.src, '  function carFeed(destination,now) {', '  function trafficIndex() {')
        self.assertIn('start=trafficRuns[destination.ri]===destination?destination.ri:trafficRuns.indexOf(destination);', feed)

    def test_the_busy_list_comes_out_in_run_order(self):
        """trafficBusySort alone, cut from the page: a list in order but for the runs added at its end (none, a few, more
        than the 64 it slides into place, the whole list) comes out in run order with every run still on it once."""
        if not shutil.which('node'):
            self.skipTest('Node.js unavailable')
        block = cut(self.src, '  let trafficJit=new Float64Array(0)', '  function trafficReconcile(now) {')
        script = 'const trafficRuns=[],trafficBusy=[];const hash01=n=>{const s=Math.sin(n*127.1+311.7)*43758.5453;return s-Math.floor(s);};\n' + block + r'''
let sd = 7; const rnd = () => { sd = (Math.imul(sd, 1664525) + 1013904223) >>> 0; return sd / 4294967296; };
for (let i = 0; i < 5000; i++) trafficRuns.push({ cars: [] });
let cases = 0, bad = 0, slid = 0, whole = 0, still = 0, unindexed = trafficRuns.some((r) => r.ri !== undefined);
for (let c = 0; c < 3000; c++) {
  const pick = new Set(); const n = Math.floor(rnd() * 900), tail = c % 5 === 0 ? 0 : c % 5 === 4 ? Math.floor(rnd() * 600) : Math.floor(rnd() * 70);
  while (pick.size < n) pick.add(Math.floor(rnd() * 5000));
  const head = [...pick].sort((a, b) => a - b), end = [];
  while (end.length < tail) { const i = Math.floor(rnd() * 5000); if (!pick.has(i)) { pick.add(i); end.push(i); } }
  if (c % 97 === 0) end.sort((a, b) => a - b);        // a tail that is itself in order
  if (c % 89 === 0) head.reverse();                   // and a list out of order from its start
  trafficBusy.length = 0; for (const i of head.concat(end)) trafficBusy.push(trafficRuns[i]);
  let p = 1; while (p < trafficBusy.length && trafficBusy[p].ri > trafficBusy[p - 1].ri) p++;
  const left = trafficBusy.length - p; if (left <= 0) still++; else if (left > 64) whole++; else slid++;
  trafficBusySort();
  const want = [...pick].sort((a, b) => a - b);
  cases++;
  if (trafficBusy.length !== want.length || trafficBusy.some((r, k) => r !== trafficRuns[want[k]])) bad++;
}
console.log(JSON.stringify({ cases, bad, slid, whole, still, unindexed, indexed: trafficRuns.every((r, i) => r.ri === i), table: trafficJit.length, ok: trafficJitOk, jit0: trafficJit[1234] === hash01(1234 * 7.3) }));'''
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        o = json.loads(r.stdout)
        self.assertEqual((o['cases'], o['bad']), (3000, 0), o)
        self.assertGreater(o['slid'], 1000, o)      # the insertion's path
        self.assertGreater(o['whole'], 400, o)      # the whole sort's
        self.assertGreater(o['still'], 400, o)      # and the list already in order, left alone
        self.assertFalse(o['unindexed'])
        self.assertTrue(o['indexed'] and o['ok'] and o['jit0'])   # the first call made the index and the jitter table
        self.assertEqual(o['table'], 5000)


class TrafficReconcileExact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        if not (ROOT / 'traffic.b64').exists():
            raise unittest.SkipTest('traffic.b64 absent')
        r = subprocess.run(['node', str(CHECKS), 'exact'], capture_output=True, text=True, timeout=900)
        if r.returncode:
            raise AssertionError(r.stderr[-4000:] or r.stdout[-4000:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])
        print('\n  traffic reconcile, %d runs of traffic.b64 under Node (ms; a busy machine slows both alike)' % cls.o['runs'])
        for dev in ('computer', 'phone'):
            m = cls.o[dev]['ms']
            print('    %-8s reconcile walks %s -> %s, whole call mean %.1f -> %.1f, advance and draw a frame %s -> %s' % (
                dev, json.dumps(m['walksOld']), json.dumps(m['walksNew']), m['reconcileOld'], m['reconcileNew'], json.dumps(m['frameOld']), json.dumps(m['frameNew'])))

    def test_zero_differences(self):
        o = self.o
        self.assertEqual(o['bad'], 0, o['first'])
        self.assertGreater(o['runs'], 40000)                 # the whole shipped network
        self.assertGreater(o['runsCompared'], 5000000)       # every run after every reconcile
        self.assertGreater(o['needsCompared'], 50000)        # each need's run, shortage and priority, in the sorted order
        self.assertGreater(o['carsCompared'], 500000)        # every car on every run after every frame
        self.assertEqual(o['slotsCompared'], o['carsCompared'])   # and every one of them drawn in the same instance slot
        self.assertGreater(o['lampsCompared'], 500000)
        self.assertEqual(o['oldCalls'], 3)                   # the reference section holds the two helpers and calls neither

    def test_both_devices_flew_the_whole_path(self):
        for dev, cap, warm in (('computer', 3000, 3300), ('phone', 550, 2200)):
            d = self.o[dev]
            self.assertEqual((d['cap'], d['warm']), (cap, warm))
            self.assertEqual(len(d['legs']), 10)
            self.assertGreaterEqual(d['recons'], 80)
            self.assertTrue(d['indexed'])                    # the page's section made its index
            self.assertFalse(d['oldIndexed'])                # and the reference never did: it ran the old walks
            legs = {l['name'].split(':')[0].split(',')[0]: l for l in d['legs']}
            for l in d['legs']:
                self.assertEqual(l['bad'], 0, l)
                self.assertGreater(l['recons'], 0, l)
                self.assertGreater(l['transfers'], 0, l)
            self.assertGreater(legs['seed at City Hall']['born'], cap * 0.8)                # the seeding fills most of the fleet
            self.assertGreater(legs['east along Market Street']['retired'], 100)            # a moving eye sheds cars behind it
            self.assertGreater(legs['east along Market Street']['routed'], 500)             # and carFeed's routed cars drive in
            jump = legs['a jump to the Northeast']
            self.assertGreater(jump['farRetired'], 50)       # cars on runs the plan test passes by are still retired
            self.assertGreaterEqual(jump['retired'], jump['farRetired'])
            shut = legs['closed blocks round the eye']
            self.assertGreater(shut['closed'], 50)
            self.assertGreater(shut['closedOut'], 30)        # the cars standing on a block as it closed, killed by the closures' own line
            self.assertEqual(d['churn']['dieClosed'], shut['closedOut'])
            self.assertGreater(shut['closingSeen'], 5)       # and some of them dying in view: the advance may not bring those back
            self.assertEqual(legs['the time slider dragged']['recons'], legs['the time slider dragged']['frames'])   # a reconcile a frame
            self.assertGreater(legs['a sweep']['retired'], 100)
            self.assertGreater(d['churn']['dieRetire'], 1000)
            self.assertGreater(d['churn']['dieEnd'], 50)
            self.assertGreater(d['churn']['blockedBirths'], 1000)
            self.assertEqual(d['churn']['dieSeen'], 0)       # the rule the walks must not touch: no car retired in view

    def test_the_shipped_data_meets_the_plan_tests_conditions(self):
        # a far run's old want is aadt x frac / density x km x 0: exactly +0 only for a volume of 0 or more and a class
        # the density table holds, and its old target the floor of its jitter: 0 only under 1
        self.assertGreaterEqual(self.o['aadtMin'], 0)
        for dev in ('computer', 'phone'):
            self.assertLess(self.o['clsMax'], self.o[dev]['densities'])
            self.assertLess(self.o[dev]['jitMax'], 1)

    def test_the_stall_is_gone(self):
        for dev in ('computer', 'phone'):
            m = self.o[dev]['ms']
            self.assertLess(m['walksNew']['best'] * 3, m['walksOld']['best'], m)       # measured 7 to 12 times
            self.assertLess(m['walksNew']['median'] * 2, m['walksOld']['median'], m)
            self.assertLess(m['frameNew']['best'], m['frameOld']['best'], m)


class TrafficReconcileJavaScriptCore(unittest.TestCase):
    def test_zero_differences_on_the_phones_engine(self):
        if not shutil.which('osascript'):
            self.skipTest('JavaScriptCore via osascript unavailable')
        if not (ROOT / 'traffic.b64').exists():
            self.skipTest('traffic.b64 absent')
        r = subprocess.run(['osascript', '-l', 'JavaScript', str(CHECKS), str(ROOT), 'lite'], capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-2000:])
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o['engine'], 'JavaScriptCore')
        self.assertEqual(o['bad'], 0, o['first'])
        d = o['phone']
        self.assertEqual((d['cap'], d['warm']), (550, 2200))
        self.assertTrue(d['indexed'])
        self.assertFalse(d['oldIndexed'])
        self.assertLess(d['jitMax'], 1)
        self.assertGreaterEqual(d['recons'], 30)
        self.assertGreater(o['runsCompared'], 1000000)
        self.assertGreater(o['needsCompared'], 2000)
        self.assertGreater(o['carsCompared'], 30000)
        self.assertEqual(o['slotsCompared'], o['carsCompared'])
        self.assertGreater(d['churn']['dieRetire'], 200)
        self.assertGreater(d['churn']['dieClosed'], 10)      # a block closed on its cars here too
        self.assertGreater(sum(l['farRetired'] for l in d['legs']), 50)
        self.assertGreater(sum(l['routed'] for l in d['legs']), 500)
        m = d['ms']
        print('\n  traffic reconcile under JavaScriptCore, a phone (ms): walks %s -> %s, advance and draw a frame %s -> %s' % (
            json.dumps(m['walksOld']), json.dumps(m['walksNew']), json.dumps(m['frameOld']), json.dumps(m['frameNew'])))


if __name__ == '__main__':
    unittest.main()
