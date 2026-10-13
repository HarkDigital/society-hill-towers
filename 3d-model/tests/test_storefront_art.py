"""Round 189: the storefronts' generated shopfronts (bake_storefront_art.py -> storefront_art.json, art/storefronts/).

Every trade has a cell at the narrowest and the widest class, every cell lies inside the atlas with its fascia band and
rows inside it, the phone's copies are exactly half, the masks are opaque RGB (an alpha under 255 reaches WebGL through a
premultiplied decode on WebKit), the painted shop floors' cells exist and keep the banks, venues and trades off anonymous
walls, and the generator takes its key only from the environment or ~/.config/philly3d/openai.env and never prints it."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads((ROOT / 'storefront_art.json').read_text())

    def test_every_trade_has_its_narrowest_and_widest(self):
        import fetch_storefront_art as F
        self.assertEqual(self.m['fams'], [f[0] for f in F.FAMILIES])
        have = {(c['fam'], c['cls']) for c in self.m['cells']}
        for k in range(len(F.FAMILIES)):
            self.assertIn((k, 'S'), have)
            self.assertIn((k, 'XL'), have)
        self.assertEqual(self.m['classes'], {'S': 4.5, 'M': 6.0, 'L': 8.5, 'XL': 11.0})

    def test_the_cells_lie_inside(self):
        W, H, pad = self.m['w'], self.m['h'], self.m['pad']
        for c in self.m['cells']:
            u0, v0, du, dv = c['rect']
            self.assertTrue(0 <= u0 and u0 + du <= 1 and 0 <= v0 and v0 + dv <= 1, c['id'])
            self.assertAlmostEqual(du * W, c['nomW'] * self.m['pxm'], delta=1.01)   # its class's width at the atlas's pixels a metre
            self.assertAlmostEqual(dv * H, self.m['hM'] * self.m['pxm'], delta=1.01)
            b = c['band']
            self.assertTrue(0 <= b[0] < b[2] <= 1 and 0 < b[1] < b[3] <= 1, c['id'])
            bulk, head, bandBot = c['rows']
            self.assertTrue(0 < bulk < head <= bandBot + 1e-6 < 1, c['id'])
            self.assertAlmostEqual(bandBot, b[1], places=4)
            self.assertTrue(0 <= c['pier'][0] < c['pier'][1] <= 1)
            self.assertTrue(0 < c['boardL'] < 1)
            self.assertNotIn('no glass', c.get('notes', []), c['id'])

    def test_the_doors(self):
        # the review: a 1.6 m display window and strips of 4 to 47 cm were taken for doors; a door is a leaf's glass or a
        # pair's, in every cell but the roll-up door's
        doors = [c for c in self.m['cells'] if c['door']]
        self.assertGreaterEqual(len(doors), len(self.m['cells']) - 2)
        for c in doors:
            w = (c['door'][1] - c['door'][0]) * c['nomW']
            self.assertTrue(0.5 <= w <= 1.9, (c['id'], w))

    def test_the_second_set(self):
        ids = {c['id'] for c in self.m['cells']}
        self.assertGreaterEqual(sum(1 for c in self.m['cells'] if c['cls'] in ('M', 'L')), 46)
        for cid in ('grocery-M-1', 'grocery-S-2', 'retail-L-1', 'takeout-M-1'):   # corner stores
            self.assertIn(cid, ids)

    def test_the_painted_floors_cells(self):
        g = self.m['gen']
        for cls in ('S', 'M', 'L'):
            self.assertGreaterEqual(len(g[cls]), 6)
            for k in g[cls]:
                c = self.m['cells'][k]
                self.assertEqual(c['cls'], cls)
                self.assertNotIn(self.m['fams'][c['fam']], ('bank', 'venue', 'trade'))

    def test_the_files(self):
        from PIL import Image

        def info(rel):
            with Image.open(ROOT / rel) as im:
                return im.size, im.mode
        self.assertEqual(info(self.m['img'])[0], (self.m['w'], self.m['h']))
        self.assertEqual(info(self.m['imgHalf'])[0], (self.m['w'] // 2, self.m['h'] // 2))
        self.assertEqual(info(self.m['mask']), ((self.m['w'] // 2, self.m['h'] // 2), 'RGB'))
        self.assertEqual(info(self.m['maskHalf']), ((self.m['w'] // 4, self.m['h'] // 4), 'RGB'))


class Generator(unittest.TestCase):
    def test_the_key(self):
        s = (ROOT / 'fetch_storefront_art.py').read_text()
        self.assertIn("os.environ.get('OPENAI_API_KEY')", s)
        self.assertIn("os.path.expanduser('~/.config/philly3d/openai.env')", s)
        self.assertNotIn('codex', s)
        for line in s.splitlines():
            if 'print(' in line:
                self.assertNotIn('key', line.split('print(', 1)[1].split(')')[0].replace("'key'", ''))

    def test_the_prompts_forbid_lettering_and_people(self):
        import fetch_storefront_art as F
        for cid, fam, cls, v, prompt, size in F.cells():
            self.assertIn('completely blank: no lettering, no logo', prompt)
            self.assertIn('No people', prompt)
            w, h = (int(q) for q in size.split('x'))
            self.assertEqual((w % 16, h % 16), (0, 0))
            self.assertLessEqual(max(w / h, h / w), 3.0)
        self.assertEqual(len(F.cells()), 110)   # 83, and the review's second M and L a trade and third S for the groceries
        # the second set is numbered on: every first-set cell keeps its prompt (the images on disk were made from them)
        first = [c for c in F.cells() if not (c[2] in F.MORE and c[3] >= F.VARIANTS[c[2]]) and not (c[2] == 'S' and c[3] >= F.VARIANTS['S'])]
        self.assertEqual(len(first), 83)
        self.assertIn('no readable text, labels, menus, logos or signs', F.INSIDE_SF)


if __name__ == '__main__':
    unittest.main()
