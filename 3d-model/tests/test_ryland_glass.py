"""Round 194 (Mike: "The Ryland needs the glass treatment. That entire building is glass."). Under the glass systems the
Ryland's two bars leave the core's old glass ('Restoring the landmarks' lays them in RYLAND_GLASS, no boxed mullions) and
are built on the glass chunks in 'Raising the outer districts' on the residential window wall in their photographed blue;
?real=0 and ?glass=0 keep the old bars."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class RylandGlass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_the_bars_are_laid_for_the_systems(self):
        f = cut(self.s, "      const b = get('The Ryland');", "        liftB(m0, b);")
        self.assertIn('if (GLASS_ON) {', f)
        self.assertIn('RYLAND_GLASS.push({ poly, cx: bx, cz: bz, h: bar.h, base: rBase });', f)
        self.assertLess(f.index('continue;'), f.index("glassParts2.push({ geom: box(L, bar.h, bar.d"))   # the old bar and its mullions only off the systems

    def test_they_are_built_on_the_residential_wall(self):
        s = self.s
        self.assertIn('const RYLAND_GLASS = [], RYLAND_SYS = 8, RYLAND_BODY = 0x4f7ba1;', s)
        f = cut(s, '      for (const r of RYLAND_GLASS) {', '\n      }\n')
        self.assertIn('appendBuilding(getGlassChunk(r.cx, r.cz), r.poly, r.base - 1, r.base + r.h, c, 20, r.base, null, glassFh(RYLAND_SYS));', f)
        # laid before it is built: 'Restoring the landmarks' runs before 'Raising the outer districts'
        self.assertLess(s.index("step('Restoring the landmarks'"), s.index("step('Raising the outer districts'"))


if __name__ == '__main__':
    unittest.main()
