"""ops/closures_bake.py, the Streets Department baker (Round 79): its projection of the
city's closure permits and paving status into the page's contract. A canned answer holds a
full closure and a parking relaxation on one segment, a segment with only a dumpster permit,
a sidewalk closure, an expired permit, one starting a month out, one open to 2103 and one
with a permit link off the city's host; the paving season's statuses and this week's list
with its dedupe. Stdlib only."""
import importlib.util
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_closures_bake
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

NOW = 1_789_000_000.0   # 2026-09-09 21:06 EDT
DAY = 86400


def load_bake():
    p = C.path('ops/closures_bake.py')
    spec = importlib.util.spec_from_file_location('closures_bake', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def permit(seg, n, occ, purpose, eff_days, exp_days, ptype='Utility Work Excavation', url='https://stsweb.phila.gov/StreetClosureAPI/api/Permits/GetPermitPDF/' + 'x', line=None):
    line = line or [[-75.16, 39.98], [-75.161, 39.9805]]
    return {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': line},
            'properties': {'PermitType': ptype, 'OccupancyType': occ, 'PermitNumber': n,
                           'EffectiveDate': int((NOW + eff_days * DAY) * 1000), 'ExpirationDate': int((NOW + exp_days * DAY) * 1000),
                           'Purpose': purpose, 'Status': 'Current', 'SEG_ID': seg, 'TYPE': 'CLOSURE PERMIT', 'PermitURL': url}}


def addr(n, a):
    return {'type': 'Feature', 'geometry': None, 'properties': {'permitnumber': n, 'address': a}}


def paving(oid, status, block, line):
    return {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': line},
            'properties': {'ObjectID': oid, 'STATUS': status, 'ON_STREET': 'S 63RD ST', 'FROM_STREET': 'A', 'TO_STREET': 'B', 'BLOCK': block}}


def week(oid, block, line):
    return {'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': line},
            'properties': {'OBJECTID': oid, 'Block': block, 'OnStreet': 'X', 'FromStreet': 'Y', 'ToStreetNa': 'Z', 'WeekOf': None}}


class ClosuresBake(unittest.TestCase):
    def setUp(self):
        C.require(self, 'ops/closures_bake.py')
        self.m = load_bake()

    def test_projection(self):
        m = self.m
        feats = [
            permit('421178', '2026-1', 'Full Street Closure', 'TRENCH & INSTALL WATER & SEWER MAIN   \nPGW EUN', -10, 40),
            permit('421178', '2026-2', 'Partial Street Closure', 'RELAXATION OF PARKING REGULATIONS', -3, 20, ptype='Temporary No Parking'),
            permit('500', '2026-3', 'Partial Street Closure', 'DUMPSTER PLACEMENT', -1, 10),
            permit('600', '2026-4', 'Sidewalk Closure', 'SIDEWALK SHED', -1, 90, url='https://example.com/x'),
            permit('700', '2026-5', 'Full Street Closure', 'OLD WORK', -30, -1),
            permit('800', '2026-6', 'Full Street Closure', 'FUTURE WORK', 30, 60),
            permit('900', '2026-7', 'Partial Street Closure', 'PLUMBING', -1, 30000),
        ]
        addrs = [addr('2026-1', '2500 block of N 22ND ST'), addr('2026-4', '400 block of S 3RD ST')]
        season = [paving(1, 'Paving Complete / Line Striping Pending', '2200 block of S 63RD ST', [[-75.2, 39.9], [-75.201, 39.9005]]),
                  paving(2, 'Milling Complete / Street Adjustments Pending', '2300 block of S 63RD ST', [[-75.21, 39.91], [-75.211, 39.9105]]),
                  paving(3, 'Scheduled for Milling', '2400 block', [[-75.22, 39.92], [-75.221, 39.9205]])]
        mill = [week(9, '2300 block of S 63RD ST', [[-75.21, 39.91], [-75.211, 39.9105]])]     # the same block as season row 2
        pave = [week(10, '1200 block of MARKET ST', [[-75.16, 39.95], [-75.161, 39.9505]])]
        out = m.project(feats, addrs, season, mill, pave, NOW)
        self.assertEqual({'t', 'day', 'closures', 'paving'}, set(out))
        self.assertEqual('2026-09-09', out['day'])
        by = {r['id']: r for r in out['closures']}
        self.assertEqual(['421178', '600', '900'], sorted(by), 'the dumpster-only, expired and future segments are gone')
        r = by['421178']
        self.assertEqual(3, r['o'], 'the full closure wins; the parking relaxation does not vote')
        self.assertEqual(2, len(r['permits']), 'but it is listed')
        self.assertEqual('2026-2', r['permits'][0]['n'], 'newest first')
        self.assertEqual('Trench & Install Water & Sewer Main, PGW EUN', r['permits'][1]['why'])
        self.assertEqual('2500 Block of N 22nd St', r['addr'])
        self.assertTrue(r['permits'][1]['url'].startswith('https://stsweb.phila.gov/'))
        self.assertEqual(1, by['600']['o'])
        self.assertEqual('', by['600']['permits'][0]['url'], 'a link off the city host is blanked')
        self.assertEqual('400 Block of S 3rd St', by['600']['addr'])
        self.assertEqual(int(NOW + 180 * DAY), by['900']['permits'][0]['until'], 'an open-ended permit is capped at 180 days')
        self.assertEqual([[-75.16, 39.98], [-75.161, 39.9805]], r['g'])
        pv = out['paving']
        self.assertEqual(3, len(pv), 'two season strips plus the week list row that is a new block')
        self.assertEqual([('s1', 'paved', False), ('s2', 'milled', False), ('w10', 'paved', True)], [(p['id'], p['k'], p['week']) for p in pv])
        self.assertEqual('2200 Block of S 63rd St', pv[0]['addr'])
        raw = m.json.dumps(out)
        for ch in '–—·':
            self.assertNotIn(ch, raw)

    def test_helpers(self):
        m = self.m
        self.assertEqual(3, m.occupancy('Full Closure'))
        self.assertEqual(1, m.occupancy('Footway'))
        self.assertEqual(2, m.occupancy('Partial Closure'))
        self.assertEqual('Sidewalk Shed at 511 N Broad St, Overhead Protection', m.title('SIDEWALK SHED AT 511 N BROAD ST – OVERHEAD PROTECTION'))
        self.assertEqual([[-75.1, 39.9], [-75.11, 39.91], [-75.12, 39.92]], m.line_of({'type': 'MultiLineString', 'coordinates': [[[-75.1, 39.9], [-75.11, 39.91], [-75.12, 39.92]], [[0, 0], [1, 1]]]}))
        self.assertIsNone(m.line_of({'type': 'Point', 'coordinates': [0, 0]}))


if __name__ == '__main__':
    unittest.main()
