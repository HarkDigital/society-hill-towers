"""Round 162: the first-run flow and the guide's one type scale.

Mike: "I want users to select the filters they want to see initially. Then walk through the how to. Several slides
currently have not uniform font sizes." A first visit opens the guide on a layer picker (every layer once, in the layers
panel's own names and icons, switched through the panel's own toggles), then the how-to cards; the ? button opens the
how-to alone. Every card has two sizes, the title and the rest (the key labels at the body's size), iOS text autosizing
is off, a long card scrolls, and an installed app is never told to add itself to the home screen."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def js_array(src, name):
    m = re.search(r'const ' + name + r' = (\[.*?\]);\n', src, re.S)
    return json.loads(re.sub(r",\s*\]", "]", m.group(1).replace("'", '"')))


class GuideFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / 'app.js').read_text()
        cls.css = (ROOT / 'style.css').read_text()
        cls.tpl = (ROOT / 'template.html').read_text()

    def test_the_picker_offers_every_layer_once(self):
        keys = js_array(self.app, 'LAYER_KEYS')
        groups = js_array(self.app, 'PICK_GROUPS')
        picked = [k for _, ks in groups for k in ks]
        self.assertEqual(sorted(picked), sorted(keys))
        btn = dict(re.findall(r"(\w+): '(btn\w+)'", re.search(r'const PICK_BTN = \{(.*?)\};', self.app).group(1)))
        self.assertEqual(sorted(btn), sorted(keys))
        for k, b in btn.items():
            self.assertIn('id="' + b + '"', self.tpl, k)             # the chip takes the panel row's name and icon

    def test_the_first_visit_picks_then_the_guide_and_the_help_button_skips_it(self):
        self.assertIn('openGuide(0, true); }, 900);', self.app)      # the first visit
        self.assertIn('function toggleGuide() { if (GUIDE.open) closeGuide(); else openGuide(0); }', self.app)
        self.assertIn('guideBuild(!!pick);', self.app)
        self.assertIn("GUIDE.n = GUIDE_SLIDES.length + off;", self.app)
        self.assertNotRegex(self.app, r'GUIDE\.i === GUIDE_SLIDES\.length - 1')   # the card count includes the picker

    def test_the_picker_switches_through_the_panels_own_toggles(self):
        self.assertIn('const toggles = layerToggles();', self.app)    # Reset Layers and the picker share one map
        self.assertIn("if (c) { const t = layerToggles()[c.dataset.layer]; if (t) t(); pickSync(); }", self.app)
        self.assertIn("v === 'all' ? true : v === 'none' ? false : LAYER_DEFAULTS[k]", self.app)

    def test_an_installed_app_is_not_told_to_install(self):
        self.assertIn("rows[kind].filter(([k]) => !(IN_APP && k === 'Install'))", self.app)

    def test_one_type_scale(self):
        c = self.css
        self.assertIn('html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }', c)
        # the card's text: title and body; the key label at the body's size, in each context
        self.assertIn('#guide .grow { font-size: 13px;', c)
        self.assertIn('#guide .gk { flex: 0 0 136px; font-size: 13px;', c)
        self.assertEqual(c.count('#guide .grow, #guide .gk, #guide .pick-intro, #guide .pick, #guide .pick-preset, #guide .pick-group { font-size: 12px;'), 2)
        # nothing smaller survives for a card's text (the Round 60 9 to 11.5 px steps are gone)
        for m in re.finditer(r'#guide \.(gk|grow|stitle)[^{]*\{([^}]*)\}', c):
            fs = re.search(r'font-size:\s*([\d.]+)px', m.group(2))
            if fs:
                self.assertGreaterEqual(float(fs.group(1)), 12, m.group(0)[:80])
        self.assertIn('#guide .slide { overflow-y: auto;', c)          # a long card scrolls, it never clips


if __name__ == '__main__':
    unittest.main()
