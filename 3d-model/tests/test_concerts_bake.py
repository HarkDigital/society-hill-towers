"""ops/concerts_bake.py, the Ticketmaster baker: its projection of a Discovery answer into
the page's contract. A canned answer holds one ordinary show, one with the time to be
announced, one cancelled, one outside the Music segment and one without a venue position;
only the first two become placards, and the show-day instants come out as 9 am Philadelphia
time across both daylight-saving changes of 2026. Stdlib only."""
import datetime as dt
import importlib.util
import unittest
from zoneinfo import ZoneInfo

try:
    from . import _common as C          # python3 -m unittest tests.test_concerts_bake
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

TZ = ZoneInfo('America/New_York')


def load_bake():
    p = C.path('ops/concerts_bake.py')
    spec = importlib.util.spec_from_file_location('concerts_bake', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def event(eid, name, date, local_time, status='onsale', segment='Music', venue=True, tba=False, artist='The Band', tba_with_datetime=False):
    start = {'localDate': date, 'dateTBD': False, 'dateTBA': False, 'timeTBA': tba, 'noSpecificTime': False}
    if tba and tba_with_datetime:
        start['dateTime'] = '2026-09-12T03:59:00Z'
    if local_time and not tba:
        start['localTime'] = local_time + ':00'
        start['dateTime'] = dt.datetime.strptime(date + ' ' + local_time, '%Y-%m-%d %H:%M').replace(tzinfo=TZ).astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    ev = {'id': eid, 'name': name, 'url': 'https://www.ticketmaster.com/event/' + eid,
          'images': [{'ratio': '16_9', 'url': 'https://s1.ticketm.net/dam/a/x.jpg', 'width': 640, 'height': 360, 'fallback': False},
                     {'ratio': '16_9', 'url': 'https://s1.ticketm.net/dam/a/y.jpg', 'width': 305, 'height': 172, 'fallback': False},
                     {'ratio': '3_2', 'url': 'https://s1.ticketm.net/dam/a/z.jpg', 'width': 1024, 'height': 683, 'fallback': False}],
          'dates': {'start': start, 'timezone': 'America/New_York', 'status': {'code': status}},
          'classifications': [{'segment': {'name': segment}, 'genre': {'name': 'Rock'}}],
          '_embedded': {'attractions': [{'name': artist}], 'venues': [{'id': 'v1', 'name': 'The Met Philadelphia', 'city': {'name': 'Philadelphia'},
                                                                        'location': ({'latitude': '39.9701', 'longitude': '-75.1591'} if venue else {})}]}}
    return ev


class ConcertsBake(unittest.TestCase):
    def setUp(self):
        C.require(self, 'ops/concerts_bake.py')
        self.m = load_bake()

    def test_projection_keeps_only_placards(self):
        m = self.m
        pages = [{'page': {'totalPages': 1}, '_embedded': {'events': [
            event('e1', 'Kurt Vile – Back to Moon Beach Tour', '2026-09-12', '20:00'),
            event('e2', 'Sun Ra Arkestra · Late Show', '2026-09-12', '', tba=True),
            event('e3', 'Cancelled Show', '2026-09-12', '19:00', status='canceled'),
            event('e4', 'A Comedy Night', '2026-09-12', '19:00', segment='Comedy'),
            event('e5', 'No Venue Position', '2026-09-12', '19:00', venue=False),
            event('e1', 'A Duplicate', '2026-09-12', '20:00'),
        ]}}]
        out = m.project(pages, 1_789_000_000)
        self.assertEqual(['t', 'day', 'events'], list(out.keys()))
        self.assertEqual(2, len(out['events']))
        e1, e2 = out['events']
        self.assertEqual('e2', e1['id'])   # the TBA show sorts first (no start)
        self.assertEqual('Sun Ra Arkestra, Late Show', e1['name'], 'middots become commas')
        self.assertTrue(e1['tba'] and e1['time'] == '' and e1['start'] is None)
        self.assertEqual('Kurt Vile, Back to Moon Beach Tour', e2['name'], 'dashes become commas')
        self.assertEqual('20:00', e2['time'])
        self.assertEqual({'id': 'v1', 'name': 'The Met Philadelphia', 'lat': 39.9701, 'lon': -75.1591}, e2['venue'])
        self.assertEqual('https://s1.ticketm.net/dam/a/y.jpg', e2['image'], 'the smallest 16:9 image at least 300 px wide')
        self.assertEqual('Rock', e2['genre'])
        self.assertEqual('The Band', e2['artist'])
        self.assertEqual(e2['start'] + 4 * 3600, e2['until'])
        # the TBA show stands to local midnight
        self.assertEqual(int(dt.datetime(2026, 9, 13, 0, 0, tzinfo=TZ).timestamp()), e1['until'])

    def test_show_day_instant_is_nine_am_philadelphia_across_dst(self):
        m = self.m
        for date, utc_hour in (('2026-03-08', 13), ('2026-03-07', 14), ('2026-11-01', 14), ('2026-10-31', 13), ('2026-07-04', 13)):
            rec = m.project_event(event('x', 'X', date, '20:00'))
            frm = dt.datetime.fromtimestamp(rec['from'], dt.timezone.utc)
            self.assertEqual((date, 9, 0), (dt.datetime.fromtimestamp(rec['from'], TZ).strftime('%Y-%m-%d'), dt.datetime.fromtimestamp(rec['from'], TZ).hour, dt.datetime.fromtimestamp(rec['from'], TZ).minute))
            self.assertEqual(utc_hour, frm.hour, date + ' 9 am Philadelphia should be ' + str(utc_hour) + ':00 UTC')
            self.assertEqual(rec['start'] + 4 * 3600, rec['until'])

    def test_tba_end_is_the_next_local_midnight_across_dst(self):
        m = self.m
        for date, nxt in (('2026-11-01', '2026-11-02'), ('2026-03-08', '2026-03-09'), ('2026-09-12', '2026-09-13')):
            rec = m.project_event(event('x', 'X', date, '', tba=True))
            self.assertIsNone(rec['start'])
            self.assertEqual(int(dt.datetime.strptime(nxt, '%Y-%m-%d').replace(tzinfo=TZ).timestamp()), rec['until'], date)
            self.assertEqual((0, 0), (dt.datetime.fromtimestamp(rec['until'], TZ).hour, dt.datetime.fromtimestamp(rec['until'], TZ).minute))

    def test_tba_flag_wins_over_a_stray_datetime(self):
        rec = self.m.project_event(event('x', 'X', '2026-09-12', '', tba=True, tba_with_datetime=True))
        self.assertTrue(rec['tba'])
        self.assertIsNone(rec['start'])
        self.assertEqual(int(dt.datetime(2026, 9, 13, 0, 0, tzinfo=TZ).timestamp()), rec['until'])

    def test_after_midnight_set_opens_the_evening_before(self):
        rec = self.m.project_event(event('x', 'X', '2026-09-13', '00:30'))
        self.assertEqual(int(dt.datetime(2026, 9, 12, 12, 30, tzinfo=TZ).timestamp()), rec['from'])
        self.assertEqual(rec['start'] + 4 * 3600, rec['until'])
        self.assertLess(rec['from'], rec['start'])

    def test_window_is_local_midnight_in_utc(self):
        m = self.m
        # 2026-07-04 15:00 EDT: the window opens at 04:00Z that day and runs three days
        now = dt.datetime(2026, 7, 4, 15, 0, tzinfo=TZ).timestamp()
        start, end, day = m.window(now, 3)
        self.assertEqual(('2026-07-04T04:00:00Z', '2026-07-07T04:00:00Z', '2026-07-04'), (start, end, day))

    def test_key_never_in_logs_or_output(self):
        m = self.m
        out = m.project([{'page': {}, '_embedded': {'events': [event('e1', 'X', '2026-09-12', '20:00')]}}], 1_789_000_000)
        import json
        self.assertNotIn('apikey', json.dumps(out))
        self.assertEqual('', m.load_key('/nonexistent/concerts.env'))


if __name__ == '__main__':
    unittest.main()
