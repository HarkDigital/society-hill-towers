"""Round 246 (Mike: "Make the concert and sport boxes look cooler"): the new score and concert placards behind ?placards=new.

With the flag off nothing changes: the old markup, the old ball and the old CSS. With it on, the cards carry no logo (no brand
marks), keep the X and its data attributes (eventHide, eventTapRestore), make no new kind of material (the ring and the ripple are
the ball's own MeshBasicMaterial through pinSceneDepth), keep the one-mile rule and the occlusion, and say nothing with a dash or a
middot. scoreCardHTML and concertCardHTML are cut from app.js and run under Node against sample games and shows."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlacardsNew(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()
        cls.css = (ROOT / 'style.css').read_text()

    def test_flag_gates_it(self):
        s = self.src
        self.assertIn("const PLACARDS_NEW = /[?&]placards=new\\b/.test(location.search);", s)
        sset = s[s.index('  function scoresSet(games) {'):s.index('  const EVENT_PIN_R = 1609.34;')]
        # the old path is untouched: its markup, its border colour, its ball
        self.assertIn("} else el.innerHTML = logo + '<span class=\"txt\"><span class=\"live\"></span>'", sset)
        self.assertIn("if (ok && !PLACARDS_NEW) el.style.borderColor = '#' + g.color;", sset)
        self.assertIn("new THREE.SphereGeometry(2.4, 10, 8)", sset)
        cset = s[s.index('  function concertsSet(events) {'):s.index('  function concertsRender() {')]
        self.assertIn("} else el.innerHTML = img + '<span class=\"txt\">' + body", cset)
        # every new rule is scoped to the flag's class
        block = self.css[self.css.index('/* Round 246'):]
        block = block[:block.index('@media (prefers-reduced-motion: reduce) { .lbl.score.pn')]
        block = re.sub(r'/\*.*?\*/', '', block, flags=re.S)
        for sel in re.findall(r'^([^{}\n/@][^{}]*)\{', block, re.M):
            if sel.strip().startswith(('0%', '50%')):
                continue
            for part in sel.split(','):
                self.assertIn('.pn', part, part)

    def test_x_occlusion_and_mile_kept(self):
        s = self.src
        self.assertIn("el.innerHTML = scoreCardHTML(g) + (g.id ? EVENT_X.replace('<button ', '<button data-kind=\"s\" data-i=\"' + i + '\" ') : '');", s)
        self.assertIn("el.innerHTML = concertCardHTML(sp, all, first) + EVENT_X.replace('<button ', '<button data-kind=\"c\" data-i=\"' + CONCERTS.shown.length + '\" ');", s)
        # the ring and the ripple go with the tether: shown or hidden whole, by the same out-of-range and blocked answer
        self.assertIn("if (g.marks) placardMarksTick(g.marks, !out && !blocked, performance.now());", s)
        self.assertIn("if (s.marks) placardMarksTick(s.marks, !out && !blocked, 0);", s)
        marks = s[s.index('  function placardMarks('):s.index('  const _pmv = new V3();')]
        self.assertEqual(set(re.findall(r'new THREE\.(\w+Material)', marks)), {'MeshBasicMaterial'})
        self.assertEqual(marks.count('pinSceneDepth('), 3)
        # the ripple never fades under the pins' alphaTest (0.5): 0.95 - 0.43 = 0.52
        self.assertIn('m.ripple.material.opacity = 0.95 - 0.43 * ph;', s)
        # no logo on the new card
        self.assertNotIn('logo', s[s.index('  function scoreCardHTML(g) {'):s.index('  function placardMarks(')])

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_cards_under_node(self):
        s = self.src
        helpers = s[s.index('  const TEAM_NAME = {'):s.index('  // the roof\'s mark under the new placards')]
        ccard = s[s.index('  function concertCardHTML(sp, all, first) {'):s.index('  function concertsSet(events) {')]
        esc = s[s.index('  const septaEsc = '):].split('\n', 1)[0]
        plain = s[s.index('  const plainText = '):].split('\n', 1)[0]
        clock = s[s.index('  const concertClock = '):].split('\n', 1)[0]
        script = r'''
const THREE = { Color: class { constructor(r, g, b) { this.r = r; this.g = g; this.b = b; }
  getHSL(o) { const r = this.r, g = this.g, b = this.b, mx = Math.max(r, g, b), mn = Math.min(r, g, b); o.l = (mx + mn) / 2; o.s = 0; o.h = 0; if (mx !== mn) { const d = mx - mn; o.s = o.l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn); o.h = mx === r ? ((g - b) / d + (g < b ? 6 : 0)) / 6 : mx === g ? ((b - r) / d + 2) / 6 : ((r - g) / d + 4) / 6; } return o; }
  setHSL(h, s2, l) { const f = (p, q, t) => { if (t < 0) t += 1; if (t > 1) t -= 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < 0.5 ? q : t < 2 / 3 ? p + (q - p) * 6 * (2 / 3 - t) : p; }; if (!s2) { this.r = this.g = this.b = l; return this; } const q = l <= 0.5 ? l * (1 + s2) : l + s2 - l * s2, p = 2 * l - q; this.r = f(p, q, h + 1 / 3); this.g = f(p, q, h); this.b = f(p, q, h - 1 / 3); return this; } } };
''' + esc + '\n' + plain + '\n' + clock + '\n' + helpers + '\n' + ccard + r'''
const out = {
  live: scoreCardHTML({ k: 'mlb', live: true, us: 'PHI', uscore: '4', them: 'NYM', tscore: '2', at: 'Away', detail: 'Bot 7th, Away' }),
  pre: scoreCardHTML({ k: 'nba', pre: true, us: 'PHI', them: 'BOS', at: 'Away', detail: '11/12 - 7:30 PM EST, Away' }),
  fin: scoreCardHTML({ k: 'nhl', us: 'PHI', uscore: '2', them: 'PIT', tscore: '3', at: 'Home', detail: 'Final/OT, Home' }),
  nba: scoreCardHTML({ k: 'nba', live: true, us: 'PHI', uscore: '88', them: 'BOS', tscore: '90', at: 'Home', detail: '8:41 - 3rd, Home' }),
  eagles: teamTint('004c54'),
  show: concertCardHTML({ venues: [{ name: 'The Fillmore – Philadelphia', rows: [{ artist: 'Kurt Vile', time: '20:00', url: 'https://www.ticketmaster.com/event/1' }, { artist: 'Waxahatchee', tba: true }] }] },
    [{ time: '20:00' }], { image: 'https://s1.ticketm.net/a.jpg' }),
};
console.log(JSON.stringify(out));
'''
        r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertIn('<span class="pt">Phillies</span><span class="pa">Away</span><span class="ps"><i></i>Live</span>', o['live'])
        self.assertIn('<div class="pb"><div class="pr up"><span class="ab">PHI</span><span class="sc">4</span></div>', o['live'])
        self.assertIn('<div class="pd">Bot 7th</div>', o['live'])                 # Home or Away is in the kicker, not twice
        self.assertIn('<div class="pm">PHI<em>at</em>BOS</div><div class="pd">7:30 PM EST</div>', o['pre'])
        self.assertIn('<span class="ps">Today</span>', o['pre'])
        self.assertIn('<div class="pr up"><span class="ab">PIT</span>', o['fin'])
        self.assertIn('<div class="pd">Final/OT</div>', o['fin'])
        self.assertIn('<div class="pd">8:41, 3rd</div>', o['nba'])                 # ESPN's spaced hyphen reads as a comma
        r2, g2, b2 = map(int, re.match(r'rgb\((\d+),(\d+),(\d+)\)', o['eagles']).groups())
        self.assertGreater(max(r2, g2, b2) + min(r2, g2, b2), 2 * 0.57 * 255)    # midnight green lifted to read on slate
        self.assertIn('<div class="cn">The Fillmore, Philadelphia</div>', o['show'])
        self.assertIn('<span class="ps">Tonight</span>', o['show'])
        self.assertIn('<span class="ct">8:00 PM</span><a href="https://www.ticketmaster.com/event/1"', o['show'])
        self.assertIn('<span class="ct">Time to be announced</span>', o['show'])
        for k, v in o.items():
            text = re.sub(r'<[^>]+>', ' ', v)
            self.assertNotRegex(text, '[—·]', k)


if __name__ == '__main__':
    unittest.main()
