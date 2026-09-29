"""Round 168: no middot and no em dash in a user-facing string of the page's chrome (the CLAUDE.md rule: commas, colons,
sentences). The Sun & sky panel's Skyline Theme menu carried five middots ("Eagles · Green & White"); they are colons now.

Every text node and every attribute a person reads or hears (title, aria-label, placeholder, alt, label, value of a
button or an option, a meta description) in template.html and about_body.html is checked, with the entities resolved,
so an &middot; or an &mdash; cannot slip past either. Comments, scripts and styles are exempt, as the rule exempts code."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
# the middot and its look-alikes (the hyphenation point, the bullet and dot operators, the Greek ano teleia), the em dash
BANNED = {'·': 'middot', '‧': 'hyphenation point', '∙': 'bullet operator', '⋅': 'dot operator',
          '·': 'ano teleia', '—': 'em dash'}
READ_ATTRS = {'title', 'aria-label', 'aria-description', 'aria-roledescription', 'placeholder', 'alt', 'label', 'content', 'value'}


class Strings(HTMLParser):
    """Collects (line, kind, text) for every user-facing string, outside <script> and <style>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        for k, v in attrs:
            if v and k in READ_ATTRS:
                self.out.append((self.getpos()[0], tag + '@' + k, v))

    def handle_startendtag(self, tag, attrs):
        for k, v in attrs:
            if v and k in READ_ATTRS:
                self.out.append((self.getpos()[0], tag + '@' + k, v))

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.out.append((self.getpos()[0], 'text', data.strip()))


def strings(name):
    p = Strings()
    p.feed((ROOT / name).read_text())
    p.close()
    return p.out


class NoMiddotsOrEmDashes(unittest.TestCase):
    def test_the_chrome_and_the_about_panel(self):
        for name in ('template.html', 'about_body.html'):
            found = strings(name)
            self.assertGreater(len(found), 10, name + ': the parser found the page\'s strings')
            bad = [(line, kind, text, BANNED[ch]) for line, kind, text in found for ch in BANNED if ch in text]
            self.assertEqual(bad, [], name + ': a user-facing string carries a middot or an em dash')

    def test_the_skyline_theme_menu_reads_with_colons(self):
        opts = [t for _, k, t in strings('template.html') if k == 'text']
        for want in ('Automatic: Games & Calendar', 'Eagles: Green & White', 'Phillies: Red & White',
                     'Sixers: Blue, Red & White', 'Flyers: Orange & White'):
            self.assertIn(want, opts)

    def test_the_parser_sees_an_entity_and_skips_code(self):
        p = Strings()
        p.feed('<p title="a &middot; b">x &mdash; y</p><script>// a · comment — in code</script><!-- · -->')
        p.close()
        texts = [t for _, _, t in p.out]
        self.assertEqual(texts, ['a · b', 'x — y'])


if __name__ == '__main__':
    unittest.main()
