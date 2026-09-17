"""bake_markets.py (Round 76): the City's farmers' markets parsed for the clock. The hour
strings ('9:00' without its zero, an end of '01:00' that is one in the afternoon), the season
(month names with a missing day defaulting to the first and the last of the month, 'Yes' for
year round, no months at all meaning open all year by weekday), the payment flags, the
website normalisation, the dash rule on names, and the frame (Headhouse lands in the core)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from bake_markets import bake, parse_hhmm, website_of   # noqa: E402


def feat(name, lon=-75.1445, lat=39.9426, **props):
    p = {'name': name, 'operator': 'The Food Trust', 'address': '2nd and Lombard Streets',
         'season_year_round': 'No', 'payment_snap': 'Yes', 'payment_credit': 'No'}
    p.update(props)
    return {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]}, 'properties': p}


class Markets(unittest.TestCase):
    def test_parse_hhmm(self):
        self.assertEqual(540, parse_hhmm('9:00'))
        self.assertEqual(870, parse_hhmm('14:30'))
        self.assertIsNone(parse_hhmm(None))
        self.assertIsNone(parse_hhmm('noon'))
        self.assertIsNone(parse_hhmm('25:00'))

    def test_hours_and_the_afternoon_fix(self):
        m = bake([feat('Germantown Kitchen Garden', hours_sat_start='09:00', hours_sat_end='01:00',
                       hours_sun_start='10:00', hours_sun_end='14:00', hours_sun_exceptions='Winter Months – closes at 1pm',
                       hours_mon_start='10:00', hours_mon_end=None)])[0]
        self.assertEqual([540, 780], m['h']['6'], "an end at or before the start is twelve hours later ('01:00' is 13:00)")
        self.assertEqual([600, 840, 'Winter Months, closes at 1pm'], m['h']['0'], 'the note rides along, its dash a comma')
        self.assertNotIn('1', m['h'], 'a day without a parsable end is dropped')

    def test_season(self):
        rows = bake([
            feat('A', season_opening_month='May', season_closing_month='October'),
            feat('B', season_opening_month='June', season_opening_day=12, season_closing_month='November', season_closing_day=20),
            feat('C', season_year_round='Yes', season_opening_month='May'),
            feat('D'),
        ])
        by = {m['n']: m for m in rows}
        self.assertEqual(([5, 1], [10, 31]), (by['A']['o'], by['A']['c']), 'day 1 opening, the last of the month closing')
        self.assertEqual(([6, 12], [11, 20]), (by['B']['o'], by['B']['c']))
        self.assertTrue(by['C']['yr'])
        self.assertIsNone(by['C']['o'], 'a year-round market carries no season')
        self.assertFalse(by['D']['yr'])
        self.assertIsNone(by['D']['o'], 'no months at all: open all year by weekday')

    def test_payments_website_name_and_frame(self):
        m = bake([feat("Headhouse Farmer’s Market — Shambles", payment_credit='Yes', payment_fmnp='Yes',
                       payment_philly_food_bucks='yes', contact_website='Thefoodtrust.org/what-we-do/')])[0]
        self.assertEqual(['SNAP', 'Credit', 'FMNP', 'Philly Food Bucks'], m['pay'])
        self.assertEqual('https://thefoodtrust.org/what-we-do/', m['web'])
        self.assertEqual("Headhouse Farmer’s Market, Shambles", m['n'], 'the em dash becomes a comma')
        self.assertTrue(abs(m['x'] - -3) < 30 and abs(m['z'] - 324) < 30, 'the Shambles lands beside the towers: %r' % ((m['x'], m['z']),))
        self.assertEqual('', website_of('N/A'))
        self.assertEqual('https://www.egreenevents.com', website_of('www.egreenevents.com'))
        self.assertEqual('https://farmtocitymarkets.com', website_of('https://FarmToCityMarkets.com'))

    def test_clip_and_order(self):
        rows = bake([feat('Zed', lon=-75.2, lat=39.95), feat('alpha'), feat('Far away', lon=-74.0, lat=40.5)])
        self.assertEqual(['alpha', 'Zed'], [m['n'] for m in rows], 'sorted by name, the point outside the far ring dropped')


if __name__ == '__main__':
    unittest.main()
