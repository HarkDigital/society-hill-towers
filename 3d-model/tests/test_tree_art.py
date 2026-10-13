"""The trees as their species look (Oct 12, Mike: "Can you have Open AI create more realistic looking trees? The data for
tree species already exists in the app. Can we make them look like their real life counterparts?").

tree_art.json (bake_tree_art.py) maps every species onto one of 18 looks and holds each look's side and top images by
season; the page draws a tree as a side card and a top card and turns each look's season with the model's date
(treeSeasonOf, run here under node). ?trees=lowpoly keeps Round 58's crowns."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Data(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((ROOT / 'tree_art.json').read_text())
        cls.names = json.loads((ROOT / 'tree_names.json').read_text())

    def test_every_look_has_its_seasons(self):
        d = self.d
        self.assertEqual(len(d['looks']), 28)   # Round 184: ten more
        for look in d['looks']:
            im = d['images'][look]
            for view in ('side', 'top'):
                self.assertIn('summer', im[view], (look, view))
                if look not in ('pine', 'spruce', 'holly'):
                    self.assertIn('autumn', im[view], (look, view))
                    self.assertIn('winter', im[view], (look, view))
                for rec in im[view].values():
                    # Round 184: files under art/trees/, a phone's half beside each
                    for k in ('img', 'imgHalf'):
                        self.assertRegex(rec[k], r'^art/trees/[a-z]+-(side|top)-[a-z]+(-half)?\.[0-9a-f]{10}\.webp$')
                        self.assertTrue((ROOT / rec[k]).exists(), rec[k])
                    if view == 'side':
                        self.assertTrue(0.3 <= rec['hf'] <= 1.0, (look, rec['hf']))
                    else:
                        self.assertTrue(0.5 <= rec['df'] <= 1.0, (look, rec['df']))
        for look in ('cherry', 'pear', 'redbud', 'crabapple', 'lilac', 'magnolia', 'dogwood', 'serviceberry'):
            self.assertIn('spring', d['images'][look]['side'], look)

    def test_species_map_onto_their_looks(self):
        d, names = self.d, self.names['names']
        self.assertEqual(len(d['speciesLook']), len(names))
        look = {n: d['looks'][d['speciesLook'][i]] for i, n in enumerate(names)}
        for name, want in (('London Planetree', 'plane'), ('Red Maple', 'redmaple'), ('Norway Maple', 'sugarmaple'),
                           ('Callery Pear', 'pear'), ('Kwanzan Cherry', 'cherry'), ('Honeylocust', 'locust'),
                           ('Northern Red Oak', 'redoak'), ('Pin Oak', 'pinoak'), ('Japanese Zelkova', 'zelkova'),
                           ('Ginkgo', 'ginkgo'), ('Japanese Tree Lilac', 'lilac'), ('Eastern Redbud', 'redbud'),
                           ('Little Leaf Linden', 'linden'), ('Sweetgum', 'sweetgum'), ('Eastern White Pine', 'pine'),
                           # Round 184's ten, each ahead of the broader pattern it used to fall under
                           ('American Sycamore', 'sycamore'), ('Silver Maple', 'silvermaple'), ('Crimson King Norway Maple', 'crimsonking'),
                           ('Saucer Magnolia', 'magnolia'), ('Kousa Dogwood', 'dogwood'), ('Apple Serviceberry', 'serviceberry'),
                           ('River Birch', 'riverbirch'), ('Weeping Willow', 'willow'), ('Willow Oak', 'pinoak'),
                           ('Colorado Spruce', 'spruce'), ('Douglas Fir', 'spruce'), ('American Holly', 'holly'), ('Yew', 'holly')):
            self.assertIn(name, look)
            if name in look:
                self.assertEqual(look[name], want, name)


def fn(src, name):
    a = src.index('  function ' + name + '(')
    return src[a:src.index('\n  }\n', a) + 4]


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Seasons(unittest.TestCase):
    def test_calendar(self):
        s = (ROOT / 'app.js').read_text()
        a = s.index('  const TREE_CAL = {')
        cal = s[a:s.index('\n  };\n', a) + 5]
        js = cal + fn(s, 'treeSeasonOf') + r'''
const doy = (m, d) => Math.round((Date.UTC(2026, m - 1, d) - Date.UTC(2026, 0, 1)) / 864e5);
const at = (look, m, d) => treeSeasonOf(look, doy(m, d));
console.log(JSON.stringify({
  julyMaple: at('redmaple', 7, 15), janOak: at('redoak', 1, 15), oct12Maple: at('redmaple', 10, 12),
  oct12Ginkgo: at('ginkgo', 10, 12), nov1Oak: at('redoak', 11, 1), apr10Cherry: at('cherry', 4, 10),
  apr10Oak: at('redoak', 4, 10), junLilac: at('lilac', 6, 10), decPine: at('pine', 12, 20), dec31Elm: at('elm', 12, 31),
}));
'''
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o['julyMaple'][:2], ['summer', 'summer'])
        self.assertEqual(o['janOak'][:2], ['winter', 'winter'])
        a, b, t = o['oct12Maple']
        # the realism pass: the change is Oct 17 to Nov 14 on average, so on Oct 12 the red maples (8 days early) have just begun
        self.assertEqual((a, b), ('summer', 'autumn')); self.assertTrue(0.0 < t < 0.2, t)   # red maples turn first
        self.assertEqual(o['oct12Ginkgo'][:2], ['summer', 'summer'])                        # ginkgos last
        self.assertEqual(o['nov1Oak'][:2], ['summer', 'autumn'])
        self.assertEqual(o['apr10Cherry'][:2], ['spring', 'spring'])                         # the cherries in bloom
        self.assertEqual(o['apr10Oak'][:2], ['winter', 'winter'])
        self.assertEqual(o['junLilac'][1], 'spring')                                         # the tree lilac blooms in June
        self.assertEqual(o['decPine'][:2], ['summer', 'summer'])
        self.assertEqual(o['dec31Elm'][:2], ['winter', 'winter'])


class Atlas(unittest.TestCase):
    """Round 184's ten looks ran past the foot of an atlas laid out six cells a row for 18, and those trees (the broadleaf
    among them) drew as striped boxes: every look's two cells must lie on the canvas, on a computer and on a phone."""

    @unittest.skipUnless(shutil.which('node'), 'node is not installed')
    def test_every_look_fits(self):
        s = (ROOT / 'app.js').read_text()
        d = json.loads((ROOT / 'tree_art.json').read_text())
        js = ('const THREE = { CanvasTexture: function (c) { this.image = c; } };\n'
              'const renderer = { capabilities: { getMaxAnisotropy: () => 8 } };\n'
              'const document = { createElement: () => ({ getContext: () => ({}) }) };\n'
              'const TREE_ART = ' + json.dumps({k: d[k] for k in ('looks', 'side', 'top')}) + ';\n'
              'const out = [];\n'
              'for (const isTouch of [false, true]) {\n' + fn(s, 'treeArtAtlas') +
              '  for (const v of ["side", "top"]) { const a = treeArtAtlas(v); out.push([isTouch, v, a.N, a.A, a.C]); }\n}\n'
              'console.log(JSON.stringify(out));')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        cells = 2 * len(d['looks'])
        for touch, view, N, A, C in json.loads(r.stdout):
            last = cells - 1
            self.assertLessEqual((last % C + 1) * N, A, (touch, view))
            self.assertLessEqual((last // C + 1) * N, A, (touch, view))
            self.assertGreaterEqual(N, 128 if view == 'side' and not touch else 64, (touch, view))
        # the drawing and the shader read the same columns
        self.assertIn('x = (k % at.C) * at.N, y = Math.floor(k / at.C) * at.N', s)
        self.assertIn('float col = mod(k, ${C.toFixed(1)}), row = floor(k / ${C.toFixed(1)} + 1e-3);', s)
        self.assertIn('TREE_ART_VERT(S.N, S.A, S.AH, T.N, T.A, T.AH, S.C)', s)   # the realism pass: a computer's canvas is as tall as its rows
        self.assertNotIn('k % 6', s)


class Page(unittest.TestCase):
    def test_wiring(self):
        s = (ROOT / 'app.js').read_text()
        self.assertIn("!/[?&]trees=lowpoly\\b/.test(location.search)", s)
        self.assertIn('im.customDepthMaterial = dmat;', s)   # the cards cast their own shapes, turned to the sun
        self.assertIn("projectionMatrix[3][3] > 0.5 ? -fwd : normalize(eye - mid)", s)
        # one card a tree, its picture cross-dissolving from the side view to the top view as the view steepens
        self.assertIn("vec4 tx = tTw <= 0.0 ? a : tTw >= 1.0 ? b : mix(a, b, tTw);", s)
        self.assertIn("const crown = im.material !== trunkMat && !im.userData.treeCard;", s)
        self.assertIn("TREEART.at = -1e9;   // a new date turns the trees' seasons on the next frame", s)
        self.assertIn('if (TREEART.side) { TREEART.uResH.value = renderer.domElement.height || 900; updateTreeArt(now); }', s)
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("TREE_ART", text_of("tree_art.json", "null"))', b)


if __name__ == '__main__':
    unittest.main()
