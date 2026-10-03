"""Round 170: the app keeps the person's choices in native storage too (Mike: use Capacitor Preferences for the app builds).

iOS may clear a web view's localStorage when the phone runs short of space, and the layers, the Graphics pick, the hidden
events and the guide's seen mark lived only there. Inside the app every write of those four keys now also goes to
@capacitor/preferences (Capacitor.Plugins.Preferences, injected by the bridge), and each launch reconciles the two: a key
the native store holds that localStorage lost is written back, with one reload a tab while the city is still building when
it shapes the load; a key localStorage holds differently is copied over. The crash tiers stay in localStorage alone. The
boot block runs under Node through test_recovery's harness with a fake plugin whose calls answer asynchronously."""
import json
from pathlib import Path
import unittest

try:
    from .test_recovery import boot_script, run_node, cut          # python3 -m unittest tests.test_kept
except ImportError:
    from test_recovery import boot_script, run_node, cut           # python3 -m unittest discover -s tests

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT.parent / 'app'

# a fake @capacitor/preferences: a native Map, every call answering a tick later as the bridge does; fail makes get reject
PLUGIN = r'''
const native = new Map();
let failGet = false;
const tick = () => new Promise((r) => setTimeout(r, 1));
const cap = { Plugins: { Preferences: {
  get: ({ key }) => tick().then(() => { if (failGet) throw new Error('bridge'); return { value: native.has(key) ? native.get(key) : null }; }),
  set: ({ key, value }) => tick().then(() => { native.set(key, value); }),
  remove: ({ key }) => tick().then(() => { native.delete(key); }),
} } };
const settle = () => new Promise((r) => setTimeout(r, 20));
const N = (k) => (native.has(k) ? native.get(k) : null);
const R = () => { reset(); native.clear(); failGet = false; };   // a fresh device: both stores empty
const kept = (S) => ({ on: S.KEPT.on, ready: S.KEPT.ready, restored: S.KEPT.restored.slice(), copied: S.KEPT.copied.slice(), reloaded: S.KEPT.reloaded, failed: S.KEPT.failed, reloads: S.reloads.length });
'''


class Kept(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def loads(self, body):
        script = boot_script(self.src, PLUGIN + '(async () => {\n' + body + '\nconsole.log(JSON.stringify(out));\n})().catch((e) => { console.error(e); process.exit(1); });')
        script = script.rsplit('console.log(JSON.stringify(out));', 1)[0]   # the harness's own synchronous print goes
        return run_node(self, script)

    def test_the_site_keeps_nothing_natively(self):
        o = self.loads(r'''
R(); native.set('philly3d.gfx', JSON.stringify({ pick: 'sharper', t: 1 }));
const S = load({ cap });   // not the app: the plugin is never asked
S.gfxSet('smoother'); await settle();
out.k = kept(S); out.ls = J('philly3d.gfx').pick; out.native = JSON.parse(N('philly3d.gfx')).pick;
''')
        self.assertFalse(o['k']['on'])
        self.assertTrue(o['k']['ready'])
        self.assertEqual(o['ls'], 'smoother')
        self.assertEqual(o['native'], 'sharper', 'the site never writes the native store')

    def test_the_first_launch_of_this_build_copies_localstorage_over(self):
        o = self.loads(r'''
R();
LS.setItem('philly3d.prefs', JSON.stringify({ septa: false }));
LS.setItem('philly3d.gfx', JSON.stringify({ pick: 'smoother', t: 1 }));
LS.setItem('philly3d.guide', '1');
const S = load({ app: true, cap }); await settle();
out.k = kept(S);
out.native = { prefs: N('philly3d.prefs'), gfx: N('philly3d.gfx'), guide: N('philly3d.guide'), ev: N('philly3d.hiddenEvents'), tier: N('philly3d.tierv') };
''')
        self.assertTrue(o['k']['on'] and o['k']['ready'])
        self.assertEqual(o['k']['reloads'], 0)
        self.assertEqual(sorted(o['k']['copied']), ['philly3d.gfx', 'philly3d.guide', 'philly3d.prefs'])
        self.assertEqual(o['native']['prefs'], '{"septa":false}')
        self.assertEqual(json.loads(o['native']['gfx'])['pick'], 'smoother')
        self.assertEqual(o['native']['guide'], '1')
        self.assertIsNone(o['native']['ev'])
        self.assertIsNone(o['native']['tier'], 'the crash tiers stay in localStorage alone')

    def test_a_cleared_web_view_gets_its_choices_back_with_one_reload(self):
        o = self.loads(r'''
R();
native.set('philly3d.prefs', JSON.stringify({ septa: false, labels: true }));
native.set('philly3d.gfx', JSON.stringify({ pick: 'smoother', t: 1 }));
const first = load({ app: true, cap });
out.firstPick = first.GFX.pick; out.firstTier = first.TIER;
await settle();
out.first = kept(first); out.boot = J('philly3d.boot'); out.flag = SS.getItem('philly3d.keptback');
first.unload();
// the reload: localStorage now holds what the native store kept
const second = load({ app: true, cap }); await settle();
out.second = kept(second); out.secondPick = second.GFX.pick; out.secondTier = second.TIER;
out.prefs = J('philly3d.prefs');
''')
        self.assertEqual(o['firstPick'], 'auto', 'the first load read a cleared localStorage')
        self.assertEqual(sorted(o['first']['restored']), ['philly3d.gfx', 'philly3d.prefs'])
        self.assertTrue(o['first']['reloaded'])
        self.assertEqual(o['first']['reloads'], 1)
        self.assertIsNone(o['boot'], 'the reload clears the breadcrumb: it is no death')
        self.assertEqual(o['flag'], '1')
        self.assertEqual(o['second']['reloads'], 0)
        self.assertEqual(o['second']['restored'], [])
        self.assertEqual(o['secondPick'], 'smoother')
        self.assertEqual(o['secondTier'], 1, 'Smoother builds the lite city on touch')
        self.assertEqual(o['prefs'], {'septa': False, 'labels': True})

    def test_the_guide_alone_comes_back_without_a_reload(self):
        o = self.loads(r'''
R(); native.set('philly3d.guide', '1');
const S = load({ app: true, cap }); await settle();
out.k = kept(S); out.guide = LS.getItem('philly3d.guide');
''')
        self.assertEqual(o['k']['restored'], ['philly3d.guide'])
        self.assertEqual(o['k']['reloads'], 0)
        self.assertEqual(o['guide'], '1')

    def test_one_reload_a_tab_and_never_once_the_city_stands(self):
        o = self.loads(r'''
R(); native.set('philly3d.prefs', '{"septa":false}');
SS.setItem('philly3d.keptback', '1');
const again = load({ app: true, cap }); await settle();
out.again = kept(again); out.againLs = LS.getItem('philly3d.prefs');
R(); native.set('philly3d.prefs', '{"septa":false}');
const late = load({ app: true, cap, perf: { ready: 12000 } }); await settle();
out.late = kept(late); out.lateLs = LS.getItem('philly3d.prefs');
''')
        for k in ('again', 'late'):
            self.assertEqual(o[k]['reloads'], 0, k)
            self.assertTrue(o[k]['ready'], k)
            self.assertEqual(o[k]['restored'], ['philly3d.prefs'], k)
            self.assertEqual(o[k + 'Ls'], '{"septa":false}', k + ': written back for the next launch')

    def test_a_write_before_the_reconcile_waits_for_it(self):
        o = self.loads(r'''
// a changed pick made before the native answer lands: held, then copied
R(); native.set('philly3d.gfx', JSON.stringify({ pick: 'sharper', t: 1 })); LS.setItem('philly3d.gfx', JSON.stringify({ pick: 'sharper', t: 1 }));
const S = load({ app: true, cap });
S.gfxSet('smoother'); out.pendingNative = JSON.parse(N('philly3d.gfx')).pick; out.held = [...S.KEPT.pending];
await settle(); out.after = JSON.parse(N('philly3d.gfx')).pick; out.k = kept(S);
// a default written into a cleared localStorage before the saved value arrives never reaches the native store
R(); native.set('philly3d.prefs', '{"septa":false}');
const T = load({ app: true, cap });
T.keepSet('philly3d.prefs', '{"septa":true}');
await settle(); out.native = N('philly3d.prefs'); out.ls = LS.getItem('philly3d.prefs'); out.t = kept(T);
''')
        self.assertEqual(o['pendingNative'], 'sharper')
        self.assertEqual(o['held'], ['philly3d.gfx'])
        self.assertEqual(o['after'], 'smoother')
        self.assertEqual(o['k']['reloads'], 0)
        self.assertEqual(o['native'], '{"septa":false}', 'the saved value survives the default')
        self.assertEqual(o['ls'], '{"septa":false}')
        self.assertEqual(o['t']['reloads'], 1)

    def test_after_the_reconcile_every_write_and_removal_goes_to_both(self):
        o = self.loads(r'''
R(); const S = load({ app: true, cap }); await settle();
S.keepSet('philly3d.hiddenEvents', '{"mlb:1":9e12}');
S.keepSet('philly3d.prefs', '{"septa":false}');
S.keepSet('philly3d.tier', '{"tier":2}');   // not a kept key: localStorage only
await settle(); out.set = { ev: N('philly3d.hiddenEvents'), prefs: N('philly3d.prefs'), tier: N('philly3d.tier') };
S.keepRemove('philly3d.prefs');   // Reset Layers
await settle(); out.removed = N('philly3d.prefs'); out.ls = LS.getItem('philly3d.prefs');
''')
        self.assertEqual(o['set']['ev'], '{"mlb:1":9e12}')
        self.assertEqual(o['set']['prefs'], '{"septa":false}')
        self.assertIsNone(o['set']['tier'])
        self.assertIsNone(o['removed'])
        self.assertIsNone(o['ls'])

    def test_a_failed_bridge_leaves_both_copies_working(self):
        o = self.loads(r'''
R(); failGet = true; native.set('philly3d.prefs', '{"septa":false}');
const S = load({ app: true, cap }); S.gfxSet('smoother');
await settle(); out.k = kept(S); out.ls = J('philly3d.gfx').pick; out.native = N('philly3d.gfx'); out.prefs = N('philly3d.prefs');
''')
        self.assertTrue(o['k']['ready'])
        self.assertEqual(o['k']['reloads'], 0)
        self.assertEqual(o['k']['failed'], 4)
        self.assertEqual(o['ls'], 'smoother')
        self.assertEqual(json.loads(o['native'])['pick'], 'smoother', 'a pending write still goes')
        self.assertEqual(o['prefs'], '{"septa":false}', 'an unread key is left alone')

    def test_every_kept_write_goes_through_keepset(self):
        s = self.src
        for line in ("try { keepSet(GFX_KEY, JSON.stringify({ pick: GFX.pick, t: Date.now() })); }",
                     "try { keepSet(GUIDE_KEY, '1'); } catch (e) { }",
                     "try { keepSet(PREFS_KEY, JSON.stringify(o)); } catch (e) { }",
                     "try { keepRemove(PREFS_KEY); } catch (e) { }",
                     "function hiddenEvSave() { try { keepSet(HIDDEN_EV_KEY, JSON.stringify(hiddenEv)); }"):
            self.assertIn(line, s)
        for key in ('GFX_KEY', 'GUIDE_KEY', 'PREFS_KEY', 'HIDDEN_EV_KEY'):
            self.assertNotIn('localStorage.setItem(' + key, s)
            self.assertNotIn('localStorage.removeItem(' + key, s)
        self.assertIn("const KEPT_KEYS = ['philly3d.prefs', 'philly3d.gfx', 'philly3d.hiddenEvents', 'philly3d.guide'];", s)
        self.assertLess(s.index('const KEPT = {'), s.index('function gfxSave()'), 'KEPT stands before anything that can save the pick')

    @unittest.skipUnless(APP.exists(), 'no app/ project')
    def test_the_plugin_is_installed_and_declared(self):
        import plistlib
        pkg = json.loads((APP / 'package.json').read_text())
        self.assertIn('@capacitor/preferences', pkg['dependencies'])
        self.assertIn('CapacitorPreferences', (APP / 'ios' / 'App' / 'CapApp-SPM' / 'Package.swift').read_text())
        self.assertIn("include ':capacitor-preferences'", (APP / 'android' / 'capacitor.settings.gradle').read_text())
        # UserDefaults is a required-reason API: CA92.1, the app's own data, read and written by the app alone
        pm = plistlib.loads((APP / 'ios' / 'App' / 'App' / 'PrivacyInfo.xcprivacy').read_bytes())
        self.assertEqual(pm['NSPrivacyAccessedAPITypes'], [{'NSPrivacyAccessedAPIType': 'NSPrivacyAccessedAPICategoryUserDefaults', 'NSPrivacyAccessedAPITypeReasons': ['CA92.1']}])


if __name__ == '__main__':
    unittest.main()
