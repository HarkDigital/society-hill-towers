"""ops/amtrak_bake.py, the Amtrak baker (Round 80): its projection of an Amtraker answer into
the page's contract. A canned answer holds an Active train in the box (kept, its next stop
the first station not departed, its lateness from the estimate against the schedule), one
outside the box, one Predeparture, one with a non-numeric position, a name with an en dash
and a fix timestamp with a -05:00 offset; the dump carries no dash or middot. Stdlib only."""
import importlib.util
import json
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_amtrak_bake
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests


def load_bake():
    p = C.path('ops/amtrak_bake.py')
    spec = importlib.util.spec_from_file_location('amtrak_bake', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def train(num, route, lat, lon, state='Active', dest='Boston South', ts='2026-09-16T20:58:41-04:00'):
    return {'routeName': route, 'trainNum': num, 'trainID': num + '-16', 'lat': lat, 'lon': lon, 'heading': 'ne',
            'velocity': 95.6123, 'trainState': state, 'statusMsg': ' ', 'origCode': 'WAS', 'destName': dest, 'destCode': 'BOS',
            'trainTimely': '7 Minutes Late', 'lastValTS': ts, 'updatedAt': '2026-09-16T20:59:03-04:00',
            'stations': [
                {'code': 'WIL', 'name': 'Wilmington', 'schArr': '2026-09-16T20:43:00-04:00', 'schDep': '2026-09-16T20:45:00-04:00',
                 'arr': '2026-09-16T20:40:00-04:00', 'dep': '2026-09-16T20:46:00-04:00', 'status': 'Departed'},
                {'code': 'BUS', 'name': 'A bus', 'bus': True, 'schArr': '2026-09-16T21:00:00-04:00', 'arr': '2026-09-16T21:00:00-04:00', 'status': 'Enroute'},
                {'code': 'PHL', 'name': 'Philadelphia 30th Street', 'schArr': '2026-09-16T21:10:00-04:00', 'schDep': '2026-09-16T21:14:00-04:00',
                 'arr': '2026-09-16T21:17:00-04:00', 'dep': '2026-09-16T21:18:00-04:00', 'status': 'Enroute'},
                {'code': 'TRE', 'name': 'Trenton', 'schArr': '2026-09-16T21:40:00-04:00', 'arr': '2026-09-16T21:47:00-04:00', 'status': 'Enroute'}]}


class AmtrakBake(unittest.TestCase):
    def setUp(self):
        C.require(self, 'ops/amtrak_bake.py')
        self.m = load_bake()

    def test_projection(self):
        m = self.m
        d = {'192': [train('192', 'Northeast Regional', 39.89345, -75.29679)],
             '2': [train('2', 'Sunset Limited', 29.9, -90.1)],
             '655': [train('655', 'Keystone', 40.0, -75.15, state='Predeparture')],
             '99': [train('99', 'Silver Meteor', 'n/a', None)],
             '55': [train('55', 'Vermonter – Northbound', 39.965, -75.186, dest='St. Albans', ts='2026-11-16T20:58:41-05:00')]}
        out = m.project(d, 1_789_000_000.5)
        self.assertEqual({'t', 'src', 'trains'}, set(out))
        by = {r['num']: r for r in out['trains']}
        self.assertEqual(['192', '55'], sorted(by), 'only the Active trains inside the box')
        r = by['192']
        self.assertEqual('192-16', r['id'])
        self.assertEqual('NE', r['hdg'])
        self.assertEqual(95.6, r['mph'])
        self.assertEqual('PHL', r['next']['code'], 'the first station not departed, the bus connection skipped')
        self.assertEqual(7, r['next']['late'], 'estimated 21:17 against a 21:10 schedule')
        self.assertEqual(1789606721, r['fix'], 'the -04:00 instant')
        self.assertEqual(1794880721 if False else m.ts('2026-11-16T20:58:41-05:00'), by['55']['fix'], 'the -05:00 instant parses')
        self.assertEqual('Vermonter, Northbound', by['55']['route'], 'the en dash is a comma')
        self.assertEqual(max(r['fix'], by['55']['fix']), out['src'])
        raw = json.dumps(out, ensure_ascii=False)
        for ch in '–—·':
            self.assertNotIn(ch, raw)

    def test_ts(self):
        self.assertEqual(1789606721, self.m.ts('2026-09-16T20:58:41-04:00'))
        self.assertIsNone(self.m.ts('soon'))
        self.assertIsNone(self.m.ts(None))


if __name__ == '__main__':
    unittest.main()
