"""The half-mile rule and the ground pins (Round 82): every ground layer's draw path asks nearCam,
the closed blocks, the markers and the art carry pins, and the frame drives the new updates.
A text check on app.js (the paths are per-frame scene code, not a pure block)."""
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_near
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests


class NearRule(unittest.TestCase):
    def setUp(self):
        C.require(self, 'app.js')
        self.src = C.path('app.js').read_text(encoding='utf-8')

    def test_radius_and_gates(self):
        s = self.src
        self.assertIn('let NEAR_R = 804.67;', s, 'the half mile in metres')
        self.assertIn('const nearCam = (x, y, z) =>', s)
        # every ground layer asks nearCam on its draw path
        for anchor in ("if (!nearCam(v.dx, v.gy === undefined ? camera.position.y : v.gy, v.dz)) return;",   # SEPTA
                       "if (!nearCam(st.x, st.y, st.z)) continue;",                                               # Indego docks
                       "if (!nearCam(cx, cy, cz)) continue;",                                                     # Amtrak cars
                       "if (!nearCam(m.x, m.gy, m.z)) continue;   // open, but past the half mile",               # market tents
                       "if ((e.isM ? HMARK.on : PUBART.on) && nearCam(e.rec.x, e.rec.gy, e.rec.z)) near.push(e);",   # markers and art (behind their J and O layers since Round 83)
                       "const inv = closureInv, cx = camera.position.x, cy = camera.position.y, cz = camera.position.z, R = NEAR_R;"):   # closures
            self.assertIn(anchor, s, 'a ground layer lost its half-mile gate: ' + anchor[:50])
        # Round 204: the pins over them draw within PIN_R, the 0.2 mile, never past NEAR_R
        self.assertIn('const PIN_R = 321.87;', s)
        self.assertIn('r = Math.min(PIN_R, NEAR_R);', s)
        for anchor in ("if (bi < 1024 && pinNear(v.dx, v.gy + spec.h + 0.6, v.dz)) {",                            # SEPTA badges
                       "if (!pinNear(_sp.x, _sp.y, _sp.z)) continue;   // Round 204: the badge within PIN_R",       # Indego badges
                       "insideLimit(p.hx, p.hz) && pinNear(p.hx, p.hy, p.hz)) {",                                 # the Amtrak badge
                       "if (front && np < PATCO_CAP && pinNear(p.hx, p.hy, p.hz)) {",                             # the PATCO badge
                       "if (rec.o < 3 || nf >= CLOSURE_PIN_CAP || !pinNear(rec.mx, rec.my + 2.2, rec.mz)) continue;",   # closures
                       "if (!pinNear(_sp.x, _sp.y, _sp.z)) continue;   // Round 204: the pin within PIN_R, the post",   # markers and art
                       "if (!pinNear(_tp.x, _tp.y, _tp.z)) continue;   // Round 204"):                           # stops, libraries
            self.assertIn(anchor, s, 'a pin lost its 0.2 mile gate: ' + anchor[:50])
        self.assertEqual(s.count("if (!pinNear(_tp.x, _tp.y, _tp.z)) continue;   // Round 204"), 2)
        # flights and ships never ask
        a = s.index('function updateFlights('); b = s.index('function updateShips(')
        self.assertNotIn('nearCam', s[a:b], 'the flights must keep their range')
        c = s.index('function updateShips('); d = s.index('function amtrakPinTexture(')
        self.assertNotIn('nearCam', s[c:d], 'the ships must keep their range')

    def test_pins_and_frame(self):
        s = self.src
        for anchor in ("pinMesh(pinTexture('#e07a1f', '#fdfbf6', glyphDrum), CLOSURE_PIN_CAP, 'closurePin')",
                       "pinMesh(pinTexture('#d9a441', '#fdfbf6', glyphDrum), CLOSURE_PIN_CAP, 'closurePinPart')",
                       "pinMesh(pinTexture('#1f4e9c', '#f2d27a', glyphKeystone)",
                       "pinMesh(pinTexture('#b8862b', '#fdfbf6', glyphPalette)",   # a painter's palette since Round 88
                       "closurePinsUpdate(now);", "updateMarkersNear(now);", "updateMarkets(now);",
                       "pinRise(rec, now)", "pinRise(p, now)", "pinRise(v, now)", "pinSweep(now);",   # the pins' entrance (Round 88)
                       "if (rec.o < 3 || nf >= CLOSURE_PIN_CAP || !pinNear(",   # no pin over a partial closure (Round 88)
                       "if (markerPin.count) targets.push(markerPin); if (artPin.count) targets.push(artPin);",
                       "if (closurePin.count) targets.push(closurePin); if (closurePinPart.count) targets.push(closurePinPart);",
                       "markerDrawnN * 4294967296"):
            self.assertIn(anchor, s, 'missing: ' + anchor[:60])
        self.assertNotIn('const CLOSURE_R = 2500', s, 'the closures draw within NEAR_R now')
        self.assertIn('rec.x = p.x; rec.z = p.z; rec.gy = p.y; rec.yaw = p.yaw;', s, 'the records keep their yaw for the rebuild')


if __name__ == '__main__':
    unittest.main()
