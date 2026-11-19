"""Round 258 (Mike, Nov 18: "Fix the canvas bug"): after a search in the app the city was drawn in about three quarters of
the screen. The search field computed to 12px on a phone (`#searchpanel input` out-ranked the touch rule's `#searchInput`),
iOS zoomed the page in on it, and the canvas kept the zoomed window's size after the keyboard went. A field a phone types
in must be 16px on touch, by a selector that out-ranks every rule that sets its size."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def specificity(sel):
    ids = len(re.findall(r'#[\w-]+', sel))
    cls = len(re.findall(r'\.[\w-]+|\[[^\]]+\]|:(?!:)[\w-]+', sel))
    els = len(re.findall(r'(?:^|[\s>+~])([a-z][\w-]*)', sel))
    return (ids, cls, els)


class InputZoom(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = (ROOT / 'style.css').read_text()

    def test_the_touch_rule_out_ranks_every_size_rule_on_the_search_field(self):
        css = re.sub(r'/\*.*?\*/', '', self.css, flags=re.S)
        touch = []
        for m in re.finditer(r'@media \(pointer: coarse\) \{(.*?)\n\}', css, re.S):
            for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', m.group(1)):
                if 'font-size: 16px' in body:
                    touch += [s.strip() for s in sel.split(',') if 'searchInput' in s]
        self.assertEqual(touch, ['#searchpanel #searchInput', '#searchpanel #searchInput'])
        # every rule that sizes the search field's font, outside the touch blocks
        flat = re.sub(r'@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}', '', css)
        rivals = []
        for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', flat):
            if 'font-size' not in body:
                continue
            for s in sel.split(','):
                s = s.strip()
                if s.endswith('#searchInput') or s.endswith('#searchpanel input') or s == 'input':
                    rivals.append(s)
        self.assertIn('#searchpanel input', rivals)
        for r in rivals:
            self.assertGreater(specificity('#searchpanel #searchInput'), specificity(r), r)


if __name__ == '__main__':
    unittest.main()
