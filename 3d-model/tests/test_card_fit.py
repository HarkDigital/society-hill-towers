"""Round 165: two things the first run in the iOS Simulator showed.

The near me card, opened over the "You are here" mark in the middle of a landscape phone, was taller than the room above
the mark and lost its top under the screen's edge. Every anchored card is now placed by one function, vehinfoAt, which
keeps it inside the window and the safe area, and the card scrolls when it is taller than the window. And the veil's
Explore arrow (U+2197) drew as a blue emoji tile on iOS: it carries U+FE0E, the text presentation selector."""
from pathlib import Path
import re
import unittest

MODEL = Path(__file__).resolve().parents[1]


class CardFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (MODEL / 'app.js').read_text()
        cls.css = (MODEL / 'style.css').read_text()

    def test_every_card_goes_through_one_placement(self):
        self.assertFalse(re.search(r"vehinfoEl\.style\.transform = 'translate\(-50%", self.app))
        self.assertEqual(self.app.count('function vehinfoAt(px, py) {'), 1)
        self.assertEqual(self.app.count('vehinfoEl.style.transform'), 1)      # vehinfoAt's own write, nobody else's
        self.assertGreaterEqual(self.app.count('vehinfoAt('), 16)
        fn = self.app[self.app.index('function vehinfoAt(px, py) {'):]
        fn = fn[:fn.index('\n  }\n')]
        self.assertIn('env(safe-area-inset-left,0px)', fn)
        self.assertIn('Math.max(vehInset[0], Math.min(py - h,', fn)          # the top wins over the bottom

    def test_the_card_never_outgrows_the_window(self):
        rule = re.search(r'^#vehinfo \{[^}]*\}', self.css, re.M).group(0)
        self.assertTrue('max-height: calc(100dvh - 16px' in rule, rule)
        self.assertTrue('overflow-y: auto;' in rule, rule)

    def test_the_explore_arrow_is_text_not_emoji(self):
        self.assertIn("#veil .enter:not(:disabled)::after { content: '\\2197\\FE0E';", self.css)


if __name__ == '__main__':
    unittest.main()
