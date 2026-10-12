"""A ship's card links to that ship (Oct 12, Mike: "The marine traffic links are not tracking individual ships. All ships
go to the same URL").

Round 61 linked MarineTraffic's /en/ais/details/ships/mmsi:N. By Oct 2026 MarineTraffic redirected every such URL to one
world map (/en/ais/home/centerx:-12.0/centery:25.0/zoom:4), and its ship pages need its own ship id, which AIS does not
carry. VesselFinder's /vessels/details/ takes the MMSI itself. The ships' cards and the ferry's card share shipLink."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ShipLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        a = cls.s.index('  function shipLink(v) {')
        cls.fn = cls.s[a:cls.s.index('\n  }\n', a)]

    def test_links_the_ship_by_mmsi(self):
        self.assertIn('href="https://www.vesselfinder.com/vessels/details/\' + m + \'"', self.fn)
        self.assertIn("if (!/^[0-9]{9}$/.test(m)) return '';", self.fn)
        self.assertIn('on VesselFinder</a>', self.fn)

    def test_no_marinetraffic_link(self):
        # its mmsi: pages all land on the same map; nothing in the page may link there
        self.assertNotIn('marinetraffic.com', self.s)

    def test_both_cards_use_it(self):
        self.assertIn('      shipLink(v));', self.s)   # the ships' card
        self.assertIn('      shipLink(v);', self.s)    # the ferry's card


if __name__ == '__main__':
    unittest.main()
