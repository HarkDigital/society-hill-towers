"""Round 184 (Mike: load the generated art on demand): the AI-made images are files under art/ beside the page.

- every path the three manifests name exists, and its name carries the first 10 hex of its content's sha256, so a file
  never changes under its name (a browser may keep it; a rolled-back page finds its own art on the server);
- art/ holds nothing the manifests do not name (the bakes prune), and no manifest holds a data URL;
- the page loads them by relative path through artImage / artSrc, a phone taking the half copies;
- build.py refuses a missing file, deploy_philly3d.sh ships art/ before the page and never deletes there, and the app
  copies art/ into www/art."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = ('fronts.json', 'tree_art.json', 'ground_art.json')


def paths(o):
    if isinstance(o, str):
        return [o] if o.startswith('art/') else []
    if isinstance(o, dict):
        return [p for v in o.values() for p in paths(v)]
    if isinstance(o, list):
        return [p for v in o for p in paths(v)]
    return []


MANIFESTS += ('vehicle_art.json',)   # the vehicles' (the realism pass)


class Files(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.named = []
        for m in MANIFESTS:
            text = (ROOT / m).read_text()
            cls.named += paths(json.loads(text))
            assert 'data:image/' not in text, m

    def test_every_named_file_is_there_under_its_hash(self):
        self.assertGreater(len(self.named), 400)
        for p in self.named:
            f = ROOT / p
            self.assertTrue(f.exists(), p)
            m = re.fullmatch(r'art/(fronts|tiles|trees|ground|vehicles)/[a-z0-9-]+\.([0-9a-f]{10})\.(webp|png)', p)
            self.assertTrue(m, p)
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest()[:10], m.group(2), p)

    def test_nothing_unnamed_ships(self):
        on_disk = {str(f.relative_to(ROOT)) for f in (ROOT / 'art').rglob('*') if f.is_file()}
        self.assertEqual(on_disk - set(self.named), set())

    def test_every_kind_has_a_phone_copy(self):
        named = set(self.named)
        for p in named:
            if '-half' in p or '-mask' in p:
                continue
            kind, name = p.split('/')[1], p.split('/')[2].split('.')[0]
            self.assertTrue(any(q.startswith('art/%s/%s-half.' % (kind, name)) for q in named), p)


class Wiring(unittest.TestCase):
    def test_the_page_loads_them(self):
        s = (ROOT / 'app.js').read_text()
        self.assertIn('const artSrc = (full, half) => (isTouch && half ? half : full);', s)
        self.assertIn('function artImage(src) {', s)
        for call in ('artImage(artSrc(full, half))', 'artImage(artSrc(T.img, T.imgHalf))', 'artImage(artSrc(rec.img, rec.imgHalf))',
                     'artImage(artSrc(GROUND_ART.lawn, GROUND_ART.lawnHalf))'):
            self.assertIn(call, s)
        self.assertNotIn('im.src = rec.img', s)

    def test_build_guards_them(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('art file(s) the manifests name are missing', b)
        self.assertIn('still inlines data URLs', b)

    def test_deploy_ships_them_first_and_never_deletes(self):
        d = (ROOT / 'deploy_philly3d.sh').read_text()
        art, page = d.index('rsync -az "$TMP/art/" "$HOST:$WEB/art/"'), d.index('rsync -az --delay-updates "$TMP/index.html"')
        self.assertLess(art, page)
        self.assertNotIn('--delete', d)
        self.assertIn('find "$TMP/art" -type d -exec chmod 755 {} +', d)
        self.assertIn('find "$TMP" -maxdepth 1 -type f -exec chmod 644 {} +', d)   # a chmod 644 of "$TMP"/* would lock art/

    def test_the_app_carries_them(self):
        c = (ROOT.parent / 'app' / 'scripts' / 'copy-web.mjs').read_text()
        self.assertIn("resolve(here, '../../3d-model/art')", c)
        self.assertIn("cpSync(artSrc, artOut, { recursive: true });", c)


if __name__ == '__main__':
    unittest.main()
