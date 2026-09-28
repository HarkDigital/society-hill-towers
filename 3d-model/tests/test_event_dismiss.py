"""Round 167: an X on every score bubble and concert placard, and a tap on the building to bring it back.

Mike: "I would like an X in the upper right corner to get rid of concert and sporting events. The pin should not come back
unless someone taps on the building those events are happening in." A dismissed event is remembered by id in localStorage
(philly3d.hiddenEvents, id -> the moment it can be forgotten) so it stays down through polls, re-renders and reloads; a tap
whose point lands within the venue's radius brings it back and is spent on that (no property card). The wiring is checked
statically, and eventHide / eventTapRestore are cut from app.js and run under Node against stubs."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EventDismiss(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.css = (ROOT / 'style.css').read_text()

    def test_the_x_is_on_both_kinds_of_label(self):
        s = self.src
        self.assertIn("const EVENT_X = '<button type=\"button\" class=\"lx\" aria-label=\"Hide this until you tap its building\">\u00d7</button>';", s)
        self.assertIn("EVENT_X.replace('<button ', '<button data-kind=\"s\" data-i=\"' + i + '\" ')", s)
        self.assertIn("EVENT_X.replace('<button ', '<button data-kind=\"c\" data-i=\"' + CONCERTS.shown.length + '\" ')", s)
        rule = re.search(r'\.lbl\.score \.lx \{[^}]*\}', self.css).group(0)
        self.assertIn('pointer-events: auto', rule)                   # #labels is click-through; the X is not
        self.assertIn('top: -9px; right: -9px', rule)                 # the upper right corner
        self.assertIn('.lbl.score .lx::after { content: \'\'; position: absolute; inset: -11px; }', self.css)

    def test_dismissed_stays_down(self):
        s = self.src
        self.assertIn("const HIDDEN_EV_KEY = 'philly3d.hiddenEvents';", s)
        self.assertIn("for (const k in o) if (typeof k === 'string' && k.length < 80 && o[k] > now) out[k] = o[k];", s)   # expired ones pruned on load
        self.assertIn("g.hidden = !!g.id && evHidden(['s:' + g.id]);", s)
        self.assertIn("const ids = all.map((e) => 'c:' + e.id), hidden = evHidden(ids);", s)
        self.assertIn("if (g.hidden) continue;   // dismissed (Round 167)", s)
        self.assertIn("if (s.hidden) continue;   // dismissed (Round 167)", s)
        # an off-screen or blocked bubble is hidden, not only transparent, so its X cannot catch a tap
        self.assertIn("el.style.opacity = '0'; el.style.visibility = 'hidden'; continue; }   // hidden, not only clear", s)
        # a dismissed game leaves no gap in the arena's stack, and the placards over the games re-stack
        self.assertIn("SCORE_VENUES[o.k] === v && !o.hidden", s)
        self.assertIn("SCORE_VENUES[g.k] === sv && !g.hidden", s)

    def test_the_tap_brings_it_back_first(self):
        s = self.src
        pick = s[s.index('  function bldgPick(cx, cy) {'):s.index('  function updateBldgPick() {')]
        i_pt = pick.index('p = bldgPointAt(cx, cy, 14000);')
        i_restore = pick.index('eventTapRestore(p[0], p[2])) return true;')
        i_far = pick.index('if (p[4] > 3000) return false;')
        i_ground = pick.index('if (p[1] < g + 2) return false;')
        self.assertLess(i_pt, i_restore)
        self.assertLess(i_restore, i_far)                               # a stadium's field or a far hall still counts
        self.assertLess(i_far, i_ground)
        self.assertIn('function bldgPointAt(cx, cy, maxD = 3000) {', s)
        self.assertIn('return [o.x + dir.x * t, o.y + dir.y * t, o.z + dir.z * t, t, vz];', s)

    def test_no_dashes_in_what_the_viewer_reads(self):
        for t in ("notice('Hidden. Tap its building to bring it back.', 5000);", 'aria-label="Hide this until you tap its building"'):
            self.assertIn(t, self.src)
            self.assertNotRegex(t, '[—·]')

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_hide_and_restore_under_node(self):
        s = self.src
        block = s[s.index('  function eventHide(kind, i) {'):s.index("  labelsRoot.addEventListener('click', (e) => {")]
        script = r'''
const store = {};
const hiddenEv = {};
function hiddenEvSave() { store.saved = JSON.stringify(hiddenEv); }
const evHidden = (ids) => ids.length > 0 && ids.every((id) => hiddenEv[id] > Date.now());
let notes = [], relaid = 0;
function notice(t) { notes.push(t); }
const SCORE_LEN = { mlb: 3 * 3600000, nfl: 3.3 * 3600000, nhl: 2.6 * 3600000, nba: 2.4 * 3600000 };
const ARENA = { x: -2327, z: 4892, r: 110 };
const SCORE_VENUES = { mlb: { x: -1857, z: 4383, r: 170 }, nfl: { x: -1946, z: 4954, r: 170 }, nhl: ARENA, nba: ARENA };
const SCORES = { games: [{ id: 'mlb:1', k: 'mlb', start: Date.now() }, { id: 'nhl:2', k: 'nhl', start: Date.now() }] };
const CONCERTS = { shown: [{ x: -342, z: 456, r: 60, rows: [{ id: 'A', until: Date.now() / 1000 + 3600 }, { id: 'B', until: Date.now() / 1000 + 7200 }], ids: ['c:A', 'c:B'] }] };
function scoresSet(games) {   // the stub re-derives hidden the way scoresSet and concertsSet do
  relaid++;
  SCORES.games = games; for (const g of games) g.hidden = evHidden(['s:' + g.id]);
  for (const c of CONCERTS.shown) c.hidden = evHidden(c.ids);
}
BLOCK
const out = {};
out.hideS = eventHide('s', 0); out.hideC = eventHide('c', 0);
out.afterHide = { mlb: SCORES.games[0].hidden, nhl: SCORES.games[1].hidden, show: CONCERTS.shown[0].hidden, keys: Object.keys(hiddenEv).sort() };
out.expiryPastGame = hiddenEv['s:mlb:1'] > Date.now() + 3 * 3600000;
out.missFar = eventTapRestore(-1857, 4383 + 400);            // 400 m off the ballpark: nothing
out.missNeighbour = eventTapRestore(-342 + 90, 456);        // the building 90 m down the street: nothing
out.stillHidden = SCORES.games[0].hidden && CONCERTS.shown[0].hidden;
out.hitBall = eventTapRestore(-1857 + 120, 4383 - 60);      // the ballpark's stands
out.afterBall = { mlb: SCORES.games[0].hidden, show: CONCERTS.shown[0].hidden };
out.hitHall = eventTapRestore(-342 + 20, 456 - 25);         // the hall itself
out.afterHall = { show: CONCERTS.shown[0].hidden, keys: Object.keys(hiddenEv) };
out.notes = notes; out.relaid = relaid;
console.log(JSON.stringify(out));
'''.replace('BLOCK', block)
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertTrue(o['hideS'] and o['hideC'])
        self.assertEqual(o['afterHide'], {'mlb': True, 'nhl': False, 'show': True, 'keys': ['c:A', 'c:B', 's:mlb:1']})
        self.assertTrue(o['expiryPastGame'])
        self.assertFalse(o['missFar'])
        self.assertFalse(o['missNeighbour'])
        self.assertTrue(o['stillHidden'])
        self.assertTrue(o['hitBall'])
        self.assertEqual(o['afterBall'], {'mlb': False, 'show': True})
        self.assertTrue(o['hitHall'])
        self.assertEqual(o['afterHall'], {'show': False, 'keys': []})
        self.assertEqual(o['notes'], ['Hidden. Tap its building to bring it back.'] * 2)


if __name__ == '__main__':
    unittest.main()
