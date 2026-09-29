"""Round 168: the Graphics choice (Smoother, Auto, Sharper) and the city's tier it sets.

Mike approved a plan to up the visuals and the performance on his iPhone. A strip at the top of the Layers panel offers
three words, Auto in the middle and the default; the pick is a device setting in its own localStorage key (never in
philly3d.prefs or a share link, and Reset Layers leaves it alone), `?gfx=` pins it for a test without saving, and on touch
it sets the city's tier: Smoother at least the lite city, Sharper always the full city (forgetting every saved crash tier),
Auto the crash rules (tests/test_recovery.py). gfxSet calls the live hooks another part of the round adds. The boot block
runs under Node through test_recovery's harness; the status line's function runs under Node against stubbed state."""
import json
from pathlib import Path
import re
import unittest

try:
    from .test_recovery import boot_script, run_node, cut          # python3 -m unittest tests.test_gfx
except ImportError:
    from test_recovery import boot_script, run_node, cut           # python3 -m unittest discover -s tests

ROOT = Path(__file__).resolve().parents[1]
BAD = ('—', '–', '·', '&mdash;', '&middot;', '&ndash;')   # no em dash, en dash or middot in a user-facing string


class Gfx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.tpl = (ROOT / 'template.html').read_text()
        cls.css = (ROOT / 'style.css').read_text()

    def loads(self, body):
        return run_node(self, boot_script(self.src, body))

    # ---- the strip
    def test_the_strip_is_a_radiogroup_at_the_top_of_the_layers_panel(self):
        t = self.tpl
        panel = t[t.index('<div id="layerspanel"'):t.index('<div id="timepanel"')]
        self.assertLess(panel.index('class="panelnote"'), panel.index('id="gfx"'))
        self.assertLess(panel.index('id="gfx"'), panel.index('class="lgrid"'), 'the strip sits above the layer rows')
        strip = panel[panel.index('<div class="gfx" id="gfx">'):panel.index('<div class="lgrid">')]
        self.assertIn('<span class="gfxlabel" id="gfxLabel">Graphics</span>', strip)
        self.assertIn('role="radiogroup" aria-labelledby="gfxLabel"', strip)
        radios = re.findall(r'<button type="button" role="radio" data-gfx="(\w+)" aria-checked="(\w+)" tabindex="(-?\d)"[^>]*title="([^"]+)">(\w+)</button>', strip)
        self.assertEqual([(r[0], r[4]) for r in radios], [('smoother', 'Smoother'), ('auto', 'Auto'), ('sharper', 'Sharper')], 'Auto in the middle')
        self.assertEqual([(r[1], r[2]) for r in radios], [('false', '-1'), ('true', '0'), ('false', '-1')], 'Auto is the default, and the one tab stop')
        self.assertEqual([r[3] for r in radios], ['Steadier Flight, Cooler Phone', 'Balanced for This Device', 'The Whole City, Full Resolution'])
        self.assertIn('<div class="gfxnote" id="gfxNote" aria-live="polite"><span id="gfxNoteText">', strip)
        self.assertIn('<button type="button" id="gfxReload" class="mini" hidden>Reload Now</button>', strip)
        for bad in BAD:
            self.assertNotIn(bad, strip)

    def test_the_strip_looks_like_the_hud(self):
        c = self.css
        self.assertIn('#layerspanel .gfxseg button { flex: 1 1 0; min-width: 0; min-height: 44px;', c, '44 px finger targets')
        self.assertIn('#layerspanel .gfxseg button.active { color: var(--ink); background: var(--bronze); }', c)
        self.assertIn('#layerspanel .gfxseg { flex: 1; min-width: 0; border: 1px solid var(--line-strong);', c)
        self.assertIn('@media (pointer: coarse) { #layerspanel .gfxnote .mini { min-height: 44px; } }', c)

    def test_the_arrows_move_the_pick_and_never_fly(self):
        k = cut(self.src, "  if (gfxSeg) gfxSeg.addEventListener('keydown', (e) => {", '\n  });\n')
        self.assertIn("k === 'ArrowRight' || k === 'ArrowDown' ? (i + 1) % 3", k)
        self.assertIn("k === 'Home' ? 0 : k === 'End' ? 2", k)
        self.assertIn('e.stopPropagation();', k, "the window's keydown flies on an arrow")
        self.assertIn('gfxSet(GFX_PICKS[j]);', k)
        self.assertIn("if (gfxReload) gfxReload.addEventListener('click', () => location.reload());", self.src)

    # ---- storage
    def test_the_pick_is_the_devices_own(self):
        s = self.src
        self.assertIn("const GFX_KEY = 'philly3d.gfx', GFX_PICKS = ['smoother', 'auto', 'sharper'];", s)
        self.assertIn("localStorage.setItem(GFX_KEY, JSON.stringify({ pick: GFX.pick, t: Date.now() }))", s)
        reset = cut(s, "  document.getElementById('btnResetLayers').addEventListener('click', () => {", '\n  });\n')
        for w in ('GFX', 'gfx'):
            self.assertNotIn(w, reset, 'Reset Layers leaves the Graphics choice alone')
        for fn in ('  function writePrefs() {', '  function layerFlags() {', '  function viewState('):
            self.assertNotIn('GFX', cut(s, fn, '\n  }\n'), fn.strip() + ' must not carry the pick')
        # a ?gfx= test pin never rides a copied link (the site's Copy Link carries the rest of the query)
        q = cut(s, '  const shareQuery = () => {', '\n  };\n')
        self.assertIn(".replace(/[?&]gfx=[^&#]*/g, '').replace(/^&/, '?')", q)
        strip = lambda x: re.sub(r'^&', '?', re.sub(r'[?&]gfx=[^&#]*', '', x))
        self.assertEqual([strip(x) for x in ('?gfx=sharper', '?gfx=sharper&dev=1', '?dev=1&gfx=auto', '?wx=snow&gfx=auto&dev=1', '?dev=1')],
                         ['', '?dev=1', '?dev=1', '?wx=snow&dev=1', '?dev=1'])

    def test_the_api_is_defined_before_the_tier_and_the_resolution_ladder(self):
        s = self.src
        self.assertLess(s.index('  const GFX = (() => {'), s.index('  const TIER = qLite'))
        self.assertLess(s.index('  function gfxSet(pick) {'), s.index('  const TIER = qLite'))
        self.assertLess(s.index('  const TIER = qLite'), s.index('  const DPR = {'))

    def test_load_storage_and_the_pin(self):
        o = self.loads(r'''
reset(); let S = load(); out.fresh = { pick: S.GFX.pick, pinned: S.GFX.pinned, saved: saved().gfx, tier: S.TIER };
reset(); LS.setItem('philly3d.gfx', JSON.stringify({ pick: 'smoother', t: 1 })); S = load(); out.stored = { pick: S.GFX.pick, tier: S.TIER, why: S.LITE_WHY };
reset(); LS.setItem('philly3d.gfx', JSON.stringify({ pick: 'ultra', t: 1 })); out.junk = load().GFX.pick;
reset(); LS.setItem('philly3d.gfx', '{not json'); out.broken = load().GFX.pick;
// ?gfx= pins the pick for a test: the stored pick is ignored and nothing is written, not even a live change
reset(); LS.setItem('philly3d.gfx', JSON.stringify({ pick: 'smoother', t: 1 })); LS.setItem('philly3d.tier', JSON.stringify({ tier: 2, t: Date.now() }));
S = load({ search: '?gfx=sharper' }); out.pin = { pick: S.GFX.pick, pinned: S.GFX.pinned, tier: S.TIER, why: S.LITE_WHY, kept: saved().tier };
S.gfxSet('auto'); out.pinSet = { pick: S.GFX.pick, saved: saved().gfx.pick };
reset(); out.pinBad = load({ search: '?gfx=ultra' }).GFX.pinned;
''')
        self.assertEqual(o['fresh'], {'pick': 'auto', 'pinned': False, 'saved': None, 'tier': 0}, 'Auto by default, and a load writes nothing')
        self.assertEqual(o['stored'], {'pick': 'smoother', 'tier': 1, 'why': 'p'})
        self.assertEqual((o['junk'], o['broken']), ('auto', 'auto'))
        p = o['pin']
        self.assertEqual((p['pick'], p['pinned'], p['tier'], p['why']), ('sharper', True, 0, 'tp'))
        self.assertEqual(p['kept']['tier'], 2, 'a pinned Sharper forgets nothing')
        self.assertEqual(o['pinSet'], {'pick': 'auto', 'saved': 'smoother'})
        self.assertFalse(o['pinBad'])

    def test_gfx_set_saves_and_calls_the_hooks(self):
        o = self.loads(r'''
reset(); let S = load(); const calls = [];
S.GFX.hooks.push((p) => calls.push('a:' + p), () => { throw new Error('boom'); }, (p) => calls.push('c:' + p));
let ui = 0; S.GFX.ui = () => { ui++; };
const err = console.error; console.error = () => {};
out.same = S.gfxSet('auto'); out.bad = S.gfxSet('ultra'); out.quiet = { calls: calls.slice(), ui };
out.set = S.gfxSet('smoother'); out.after = { pick: S.GFX.pick, saved: saved().gfx, calls: calls.slice(), ui };
S.gfxSet('sharper'); S.gfxSet('auto'); console.error = err;
out.all = calls;
''')
        self.assertEqual((o['same'], o['bad']), (False, False))
        self.assertEqual(o['quiet'], {'calls': [], 'ui': 0}, 'no change, no hook')
        self.assertTrue(o['set'])
        a = o['after']
        self.assertEqual((a['pick'], a['saved']['pick'], a['calls'], a['ui']), ('smoother', 'smoother', ['a:smoother', 'c:smoother'], 1))
        self.assertIsInstance(a['saved']['t'], int)
        self.assertEqual(o['all'], ['a:smoother', 'c:smoother', 'a:sharper', 'c:sharper', 'a:auto', 'c:auto'], 'a hook that throws does not stop the others')

    # ---- the tier per pick
    def test_the_tier_per_pick(self):
        o = self.loads(r'''
const as = (p, o2) => { if (p) LS.setItem('philly3d.gfx', JSON.stringify({ pick: p, t: 1 })); const S = load(o2); return { pick: S.GFX.pick, tier: S.TIER, why: S.LITE_WHY, gate: S.BOOT_GATE, fell: S.GFX.fell }; };
for (const p of ['smoother', 'auto', 'sharper']) {
  reset(); out['fresh_' + p] = as(p);
  // a fortnight's tier 2 saved by a build death
  reset(); LS.setItem('philly3d.tier', JSON.stringify({ tier: 2, t: Date.now() })); LS.setItem('philly3d.lite', String(Date.now())); out['sticky_' + p] = as(p); out['stickySaved_' + p] = saved();
  // the lite city died mid-build (a death at tier 1)
  reset(); crumb('Sowing the grass', 5, { lite: true, tier: 1 }); out['build1_' + p] = as(p);
  // the full city died while running
  reset(); crumb('running', 30); out['run0_' + p] = as(p);
  // the desktop has no tiers
  reset(); LS.setItem('philly3d.tier', JSON.stringify({ tier: 2, t: Date.now() })); out['desk_' + p] = as(p, { touch: false });
  // a forced tier wins over the pick
  reset(); out['forced_' + p] = as(p, { search: '?lite=2' });
}
''')
        tiers = lambda k: tuple(o[k + '_' + p]['tier'] for p in ('smoother', 'auto', 'sharper'))
        self.assertEqual(tiers('fresh'), (1, 0, 0), 'Smoother is the lite city, Auto and Sharper the full city')
        self.assertEqual(tiers('sticky'), (2, 2, 0), 'Sharper builds the full city whatever a crash saved')
        self.assertEqual(tiers('build1'), (2, 2, 2), "a death in Sharper's build hands the pick to Auto (test_a_death_at_sharper)")
        self.assertEqual((o['build1_sharper']['pick'], o['build1_sharper']['fell']), ('auto', True))
        self.assertEqual(tiers('run0'), (1, 1, 0))
        self.assertEqual(tiers('desk'), (0, 0, 0))
        self.assertEqual(tiers('forced'), (2, 2, 2))
        self.assertEqual(o['fresh_smoother']['why'], 'p')
        self.assertEqual(o['sticky_sharper']['why'], 'tsp', 'the beacon still says what was saved, and that the pick overrode it')
        self.assertEqual(o['sticky_auto']['why'], 'ts')
        # every death still meets the gate, whatever the pick
        self.assertEqual([o['run0_' + p]['gate'] for p in ('smoother', 'auto', 'sharper')], [True, True, True])
        self.assertEqual([o['build1_' + p]['gate'] for p in ('smoother', 'auto', 'sharper')], [True, True, True])
        # Sharper forgets the saved crash tiers at load; the other picks keep them
        self.assertIsNone(o['stickySaved_sharper']['tier'])
        self.assertIsNone(o['stickySaved_sharper']['lite'])
        self.assertEqual(o['stickySaved_auto']['tier']['tier'], 2)
        self.assertEqual(o['stickySaved_smoother']['tier']['tier'], 2)

    def test_a_death_at_sharper(self):
        o = self.loads(r'''
// a death while running keeps Sharper and the full city, behind the gate
reset(); LS.setItem('philly3d.gfx', JSON.stringify({ pick: 'sharper', t: 1 })); crumb('running', 30); let S = load();
out.run = { pick: S.GFX.pick, fell: S.GFX.fell, tier: S.TIER, gate: S.BOOT_GATE, saved: saved() };
// a death during its build hands the pick back to Auto (it would die at every launch behind the veil), and Auto's rules take it
reset(); LS.setItem('philly3d.gfx', JSON.stringify({ pick: 'sharper', t: 1 })); crumb('Sowing the grass', 5); S = load();
out.build = { pick: S.GFX.pick, fell: S.GFX.fell, tier: S.TIER, gate: S.BOOT_GATE, why: S.LITE_WHY, saved: saved() };
// picking Sharper again takes the full city back and forgets the crash (the next launch)
S.gfxSet('sharper'); out.again = { fell: S.GFX.fell, saved: saved(), next: S.gfxTierFor('sharper'), nextAuto: S.gfxTierFor('auto') };
S.unload(); S = load(); out.againLoad = { pick: S.GFX.pick, tier: S.TIER };
// a pinned Sharper never falls back (the address says Sharper)
reset(); crumb('Sowing the grass', 5); S = load({ search: '?gfx=sharper' }); out.pinned = { pick: S.GFX.pick, fell: S.GFX.fell, tier: S.TIER };
''')
        r = o['run']
        self.assertEqual((r['pick'], r['fell'], r['tier'], r['gate']), ('sharper', False, 0, True))
        self.assertIsNone(r['saved']['soft'], "Sharper forgets the running death's tier")
        self.assertEqual(list(r['saved']['run']), ['0'], 'but the run log keeps it, for Auto')
        b = o['build']
        self.assertEqual((b['pick'], b['fell'], b['tier'], b['gate'], b['why']), ('auto', True, 1, True, 'ctsa'))
        self.assertEqual(b['saved']['gfx']['pick'], 'auto')
        self.assertEqual(b['saved']['tier']['tier'], 1)
        a = o['again']
        self.assertFalse(a['fell'])
        self.assertIsNone(a['saved']['tier'])
        self.assertIsNone(a['saved']['lite'])
        self.assertEqual((a['next'], a['nextAuto']), (0, 0), 'once Sharper forgot the crash, Auto forecasts the full city too')
        self.assertEqual(o['againLoad'], {'pick': 'sharper', 'tier': 0})
        self.assertEqual(o['pinned'], {'pick': 'sharper', 'fell': False, 'tier': 0})

    def test_sharper_forgets_live(self):
        o = self.loads(r'''
reset(); LS.setItem('philly3d.tier', JSON.stringify({ tier: 1, t: Date.now() })); LS.setItem('philly3d.lite', String(Date.now()));
LS.setItem('philly3d.tiersoft', JSON.stringify({ tier: 2, t: Date.now() })); LS.setItem('philly3d.tierrun', JSON.stringify({ 0: Date.now() })); sess.set('philly3d.litenow', '1');
let S = load(); out.before = { tier: S.TIER, next: [S.gfxTierFor('smoother'), S.gfxTierFor('auto'), S.gfxTierFor('sharper')] };
S.gfxSet('sharper'); out.after = { saved: saved(), sess: sess.get('philly3d.litenow') || null, next: [S.gfxTierFor('smoother'), S.gfxTierFor('auto'), S.gfxTierFor('sharper')] };
// Smoother and Auto forget nothing
reset(); LS.setItem('philly3d.tier', JSON.stringify({ tier: 1, t: Date.now() })); S = load(); S.gfxSet('smoother'); S.gfxSet('auto'); out.others = saved().tier;
// the desktop forecasts the full city for every pick, and a forced tier stays forced
reset(); S = load({ touch: false }); out.desk = [S.gfxTierFor('smoother'), S.gfxTierFor('auto'), S.gfxTierFor('sharper')];
reset(); S = load({ search: '?lite=1' }); out.forced = [S.gfxTierFor('smoother'), S.gfxTierFor('auto'), S.gfxTierFor('sharper')];
''')
        self.assertEqual(o['before'], {'tier': 2, 'next': [2, 2, 0]})
        a = o['after']
        for k in ('tier', 'lite', 'soft'):
            self.assertIsNone(a['saved'][k], k)
        self.assertEqual(list(a['saved']['run']), ['0'], 'the run log is evidence, and stays')
        self.assertIsNone(a['sess'])
        self.assertEqual(a['next'], [1, 0, 0])
        self.assertEqual(o['others']['tier'], 1)
        self.assertEqual(o['desk'], [0, 0, 0])
        self.assertEqual(o['forced'], [1, 1, 1])

    # ---- the status line
    def note(self, cases):
        says = cut(self.src, '  const GFX_SAYS = {', '  function gfxUi() {')
        script = 'const out = [];\nfor (const c of ' + json.dumps(cases) + ''') {
  const f = new Function('GFX', 'TIER', 'qLite', 'isTouch', 'gfxTierFor', ''' + json.dumps(says) + ''' + '\\n  return gfxNote();');
  out.push(f({ pick: c.pick, fell: !!c.fell }, c.tier, c.forced ? ['?lite=1', '1'] : null, c.touch !== false, (p) => c.next[p]));
}
console.log(JSON.stringify(out));'''
        return run_node(self, script)

    def test_the_status_line(self):
        full = {'smoother': 1, 'auto': 0, 'sharper': 0}
        cases = [
            dict(pick='smoother', tier=1, next={'smoother': 1, 'auto': 0, 'sharper': 0}),
            dict(pick='auto', tier=0, next=full),
            dict(pick='sharper', tier=0, next=full),
            dict(pick='smoother', tier=0, next=full),                                         # picked live on the full city
            dict(pick='auto', tier=1, next={'smoother': 1, 'auto': 0, 'sharper': 0}),       # picked live on the lite city
            dict(pick='auto', tier=1, next={'smoother': 1, 'auto': 1, 'sharper': 0}),       # Auto after a crash
            dict(pick='sharper', tier=1, next={'smoother': 1, 'auto': 1, 'sharper': 0}),
            dict(pick='auto', tier=1, fell=True, next={'smoother': 1, 'auto': 1, 'sharper': 0}),
            dict(pick='smoother', tier=2, next={'smoother': 2, 'auto': 2, 'sharper': 0}),
            dict(pick='auto', tier=2, next={'smoother': 1, 'auto': 1, 'sharper': 0}),       # a clean session will climb
            dict(pick='smoother', tier=0, touch=False, next={'smoother': 0, 'auto': 0, 'sharper': 0}),
            dict(pick='auto', tier=0, touch=False, next={'smoother': 0, 'auto': 0, 'sharper': 0}),
            dict(pick='sharper', tier=0, touch=False, next={'smoother': 0, 'auto': 0, 'sharper': 0}),
            dict(pick='auto', tier=1, forced=True, next={'smoother': 1, 'auto': 1, 'sharper': 1}),
        ]
        got = self.note(cases)
        want = [
            ['Smoother: a lighter city and a faster frame rate.', False],
            ['Auto: sharp when this device can keep up.', False],
            ['Sharper: the full city at the highest resolution, a steadier 30 frames a second.', False],
            ['Smoother: a lighter city and a faster frame rate. The lighter city loads the next time Philly3D opens.', True],
            ['Auto: sharp when this device can keep up. The whole city loads the next time Philly3D opens.', True],
            ['Auto: sharp when this device can keep up. Using a lighter city after a crash. Sharper brings the full city back.', False],
            ['Sharper: the full city at the highest resolution, a steadier 30 frames a second. The whole city loads the next time Philly3D opens.', True],
            ['Auto: sharp when this device can keep up. Sharper ran out of memory, so Graphics are back on Auto.', False],
            ['Smoother: a lighter city and a faster frame rate. Using the lightest city after a crash.', False],
            ['Auto: sharp when this device can keep up. A fuller city loads the next time Philly3D opens.', True],
            ['Smoother: a softer picture and a faster frame rate.', False],
            ['Auto: sharp when this device can keep up.', False],
            ['Sharper: the highest resolution this screen allows.', False],
            ['Auto: sharp when this device can keep up.', False],
        ]
        self.assertEqual(got, want)
        for text, _ in got:
            for bad in BAD:
                self.assertNotIn(bad, text)

    def test_the_gate_and_the_guide(self):
        g = cut(self.src, '  function bootGate() {', '\n  }\n')
        self.assertIn("GFX.fell ? 'Philadelphia ran out of memory at Sharper last time. Tap to load a lighter city.'", g)
        self.assertIn("TIER === 0 ? 'Philadelphia ran out of memory on this device last time. Tap to load the full city again.'", g)
        for bad in BAD:
            self.assertNotIn(bad, g)
        layers = cut(self.src, "    ['Layers', {", "    ['The live city', {")
        d, t = layers.split('      t: [')
        self.assertIn("['Graphics', 'At the top of the Layers panel. Smoother keeps the flight quick and steady, Sharper draws at the highest resolution, and Auto balances the two.']", d)
        self.assertIn("['Graphics', 'At the top of the Layers panel. Smoother keeps the flight steady and the phone cool, Sharper shows the whole city at full resolution, and Auto balances the two.']", t)
        for bad in BAD:
            self.assertNotIn(bad, layers)

    def test_a_clean_session_is_marked_from_its_own_enter_listener(self):
        s = self.src
        w = cut(s, "  btnEnter.addEventListener('click', () => setTimeout(() => {", '  }, 0));\n')
        self.assertIn("if (!veil.classList.contains('hidden') || GFX.okT) return;", w, "the gate's tap is not Enter")
        self.assertIn('if (TIER < 1 || glDead || document.visibilityState !== \'visible\') return;', w)
        self.assertIn("localStorage.setItem(TIER_OK_KEY, JSON.stringify({ tier: TIER, t: Date.now() }))", w)
        self.assertIn('}, 180000);', w)
        enter = cut(s, "  btnEnter.addEventListener('click', () => {\n    btnEnter.blur();", '\n  });\n')
        self.assertNotIn('TIER_OK_KEY', enter, 'the Enter handler itself is not edited for it')


if __name__ == '__main__':
    unittest.main()
