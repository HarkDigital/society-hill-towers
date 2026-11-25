"""Round 273 (a Windows visitor's beacons, Nov 24): setPointerCapture threw InvalidStateError on every press made while
the page held pointer lock. Every capture goes through one guarded helper."""
from pathlib import Path
import unittest

SRC = (Path(__file__).resolve().parents[1] / 'app.js').read_text()


class PointerCapture(unittest.TestCase):
    def test_one_guarded_capture(self):
        self.assertEqual(SRC.count('setPointerCapture('), 1)
        self.assertIn('if (document.pointerLockElement) return;\n    try { canvas.setPointerCapture(id); } catch (err)', SRC)
        self.assertEqual(SRC.count('capturePointer(e.pointerId);'), 2)


if __name__ == '__main__':
    unittest.main()
