"""Round 124: the boot breadcrumb and the lite build. Source-level checks that the pieces a phone's
self-healing load depends on stay wired: the breadcrumb at every step, the clear on a survived
load and on an ordinary leave, the sticky choice, and the three things a lite build drops."""
import os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class BootLite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = open(os.path.join(HERE, '..', 'app.js'), encoding='utf-8').read()

    def test_breadcrumb_is_written_and_cleared(self):
        s = self.src
        for anchor in ("bootMark('start');", "bootMark(s.msg);", "bootMark('ready');",
                       "setTimeout(bootClear, 20000);", "window.addEventListener('pagehide', bootClear);"):
            self.assertIn(anchor, s, 'missing: ' + anchor)

    def test_lite_is_touch_only_unless_forced(self):
        s = self.src
        self.assertIn("(isTouch && (bootDied || liteSticky) && !/[?&]lite=0\\b/.test(location.search))", s)
        self.assertIn("const LITE_KEY = 'philly3d.lite', LITE_DAYS = 14;", s)

    def test_what_a_lite_build_drops(self):
        s = self.src
        self.assertIn("if (LITE) { OUTSKIRTS_B64 = null; return; }", s, 'a lite build raises no towns')
        self.assertIn("LITE ? ((x, z) => x * x + z * z < LITE_R * LITE_R) : null, true)", s, 'the lite far ring keeps its streets and areas whole')
        self.assertIn("const SHADOW_RES = LITE ? 1024 :", s)

    def test_a_phone_keeps_only_the_towns_inside_the_limit(self):
        self.assertIn("false, isTouch ? insideLimit : null);", self.src)

    def test_streets_are_welded(self):
        s = self.src
        self.assertIn('function roadWeld(rc, x, y, z, fresh)', s)
        self.assertNotIn('rc.idx.push(rc.n++);', s, 'a street emitter is pushing a triangle soup again')


if __name__ == '__main__':
    unittest.main()
