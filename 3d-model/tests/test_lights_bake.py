"""bake_lights.py and fetch_lights.py (Round 81): BOMA Philadelphia's Building Illumination
Calendar parsed to dated colour rows. The colour words of the real title shapes (aliases
folded, 'light blue' never blue, the rainbow, the team and cause fallbacks), the names without
their lighting clause and their (Copy) suffixes (never an em dash or a middot in any output),
the Philadelphia calendar days of the epoch-millisecond instants (an end at midnight steps
back a day), the bake's dedupe, drop report, year cut and sort, main()'s two writers (no .gz
twin in the repo, the twin on the VPS, the previous file kept on a dead feed), and
fetch_lights.fetch_all against two fake pages. Stdlib only, no network."""
import contextlib
import datetime as dt
import gzip
import io
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import bake_lights as B                                                   # noqa: E402
import fetch_lights as F                                                  # noqa: E402
from bake_lights import bake, bake_rows, clean_name, local_dates, parse_colors, COLORS, RAINBOW   # noqa: E402

BAD = re.compile('[‒–—―·•]')
UTC = dt.timezone.utc
NOW = 1789531200.0 + 12 * 3600      # 2026-09-16 12:00 EDT; the year cut falls on 2025-09-16
DAY = 86400_000


def ms(y, m, d, hh=4, mm=0):
    """Epoch milliseconds of a UTC instant (04:00Z is Eastern midnight in summer)."""
    return int(dt.datetime(y, m, d, hh, mm, tzinfo=UTC).timestamp() * 1000)


def item(id_, title, start, end=None):
    return {'id': id_, 'title': title, 'startDate': start, 'endDate': end if end is not None else start + DAY - 60_000,
            'addedOn': 1, 'updatedOn': 2, 'fullUrl': '/building-illumination-calendar/' + id_}


class Colors(unittest.TestCase):
    def test_title_shapes(self):
        cases = [
            ('Pulmonary Fibrosis Awareness Month - LIGHT UP BLUE!', ['blue']),
            ('Alopecia Areata Awareness Month - LIGHT UP BLUE & YELLOW!', ['blue', 'yellow']),
            ('GO FLYERS!!  Light up ORANGE!!', ['orange']),
            ('Trigeminal Neuralgia Awareness Day - LIGHT UP TEAL/CYAN', ['teal', 'cyan']),
            ('Celebration of Italian National Day - LIGHT UP GREEN/WHITE/RED', ['green', 'white', 'red']),
            ("Shriners Children's Philadelphia 100 Year Anniversary - LIGHT UP RED & WHITE!", ['red', 'white']),
            ('National Donate Life Month - BLUE and/or GREEN', ['blue', 'green']),
            ("St. Joseph's Prep 175th Anniversary - LIGHT UP CRIMSON and/or GRAY", ['crimson', 'gray']),
            ('Kidney Cancer Awareness Month - ORANGE', ['orange']),
            ('World Down Syndrome Day (BLUE/YELLOW)', ['blue', 'yellow']),
            ('Elora For a Cure - LIGHT UP BLUE/PURPLE', ['blue', 'purple']),
            ('THE PHILLIES - Paint The Town Red, White, &amp; Blue', ['red', 'white', 'blue']),
            ('Paint The Town Red PHILLIES Opening Day', ['red']),
            ('Community Is Stronger Than Cancer Day! Light Up - RED, MAROON, WHITE', ['red', 'maroon', 'white']),
            ('International Angelman Day - LIGHT UP BLUE/MAGENTA/YELLOW/GREEN', ['blue', 'magenta', 'yellow', 'green']),
        ]
        for title, want in cases:
            with self.subTest(title=title):
                self.assertEqual(want, parse_colors(title))

    def test_aliases(self):
        self.assertEqual(['lightblue'], parse_colors('Light up LIGHT BLUE for the babies'), "'light blue' is lightblue, never blue")
        self.assertEqual(['lightblue', 'white'], parse_colors('Sky Blue and White'))
        self.assertEqual(['magenta'], parse_colors('World Caring Day - Light up DARK PINK!'), "'dark pink' is magenta, never pink")
        self.assertEqual(['blue'], parse_colors('BOMA 2024 International Conference - LIGHT UP BOMA BLUE!!'))
        self.assertEqual(['gray', 'silver'], parse_colors('LIGHT UP GREY and Silver'))
        self.assertEqual(['cyan', 'teal', 'green', 'gold', 'purple'], parse_colors('aqua, turquoise, lime, amber, violet'))
        self.assertEqual(RAINBOW, parse_colors('Rainbow lights for June'))
        self.assertEqual(['orange'], parse_colors('#OrangeUp for Kidney Cancer Awareness Month '))
        self.assertEqual(['red', 'maroon', 'white'], parse_colors('RED, MAROON, WHITE, RED'), 'duplicates removed, order kept')
        self.assertEqual([], parse_colors('Golden Goldenrod Redford Whitehall Pinkerton Navigation'), 'word boundaries: no colour inside a longer word')
        self.assertEqual(['green'], parse_colors('Global Greening Initiative'), "'greening' is not the word green; the St. Patrick's fallback supplies it")

    def test_fallbacks(self):
        self.assertEqual(['pink'], parse_colors('Breast Cancer Awareness (Copy) (Copy)'))
        self.assertEqual(['pink'], parse_colors("Helen's Angels - 15th Annual Tinis for Tatas"))
        self.assertEqual(['green'], parse_colors('GO BIRDS!!! '))
        self.assertEqual(['green'], parse_colors('Philadelphia Eagles Playoff Push! '))
        self.assertEqual(['orange'], parse_colors('FLYERS HOME OPENER'))
        self.assertEqual(['blue'], parse_colors('76ers Home Home Opener'))
        self.assertEqual(['blue', 'gold'], parse_colors('Philadelphia Union Eastern Conference Semifinal Game | LIGHT UP BLUE &amp; GOLD'))
        self.assertEqual(['blue', 'gold'], parse_colors('Philadelphia Union Home Opener'))
        self.assertEqual(['red'], parse_colors('PAINT THE TOWN RED!  GO PHILS!'))
        self.assertEqual(RAINBOW, parse_colors('Light Up for Pride Month'))
        self.assertEqual(['green'], parse_colors('Happy St. Patrick’s Day!  Global Greening 2025'))
        self.assertEqual(['gold'], parse_colors('The Fight With Lights Against Pediatric Cancer'))
        self.assertEqual(['teal'], parse_colors('Ovarian Cancer Awareness Month'))
        self.assertEqual([], parse_colors('Welcome Cherelle Parker - 100th Mayor of Philadelphia'), 'no colour, no cause: dropped')
        self.assertEqual([], parse_colors(''))
        self.assertEqual([], parse_colors(None))

    def test_lexicon(self):
        for k in COLORS:
            self.assertEqual(k, k.lower())
            self.assertEqual([k], parse_colors('Light up %s!' % k.upper()))
        for c in RAINBOW:
            self.assertIn(c, COLORS)
        for c in ('lightblue', 'magenta', 'gray', 'cyan', 'crimson', 'maroon', 'burgundy', 'silver', 'lavender', 'navy', 'gold'):
            self.assertIn(c, COLORS)


class Names(unittest.TestCase):
    CASES = [
        ('Pulmonary Fibrosis Awareness Month - LIGHT UP BLUE!', 'Pulmonary Fibrosis Awareness Month'),
        ('GO BIRDS!!! ', 'Go Birds'),
        ('GO BIRDS Light up GREEN!', 'Go Birds'),
        ('GO FLYERS!!  Light up ORANGE!!', 'Go Flyers'),
        ('World Down Syndrome Day (BLUE/YELLOW)', 'World Down Syndrome Day'),
        ('Epilepsy Education Everywhere Purple Day (PURPLE)', 'Epilepsy Education Everywhere Purple Day'),
        ('World Young Rheumatic Disease Day (WORD Day) - BLUE', 'World Young Rheumatic Disease Day (WORD Day)'),
        ('Breast Cancer Awareness (Copy) (Copy)', 'Breast Cancer Awareness'),
        ('FLYERS HOME OPENER | LIGHT UP ORANGE', 'Flyers Home Opener'),
        ('Kidney Cancer Awareness Month - ORANGE', 'Kidney Cancer Awareness Month'),
        ('National Donate Life Month - BLUE and/or GREEN', 'National Donate Life Month'),
        ("St. Joseph's Prep 175th Anniversary - LIGHT UP CRIMSON and/or GRAY", "St. Joseph's Prep 175th Anniversary"),
        ('Philadelphia Union Eastern Conference Semifinal Game | LIGHT UP BLUE &amp; GOLD', 'Philadelphia Union Eastern Conference Semifinal Game'),
        ('Philadelphia 76ers 25-26 Season Opener | LIGHT UP BLUE', 'Philadelphia 76ers 25-26 Season Opener'),
        ('76ERS HOME OPENER', '76ers Home Opener'),
        ('PAINT THE TOWN RED!  GO PHILS! (Copy)', 'Paint The Town Red, Go Phils'),
        ('PAINT THE TOWN RED - LIGHT UP FOR THE PHILLIES OPENING DAY!!', 'Paint The Town Red, Phillies Opening Day'),
        ('Truist Championship- LIGHT UP PURPLE', 'Truist Championship'),
        ('Alzheimer’s Association of America’s International Conference 2024. LIGHT UP PURPLE!', 'Alzheimer’s Association of America’s International Conference 2024'),
        ('Community Is Stronger Than Cancer Day! Light Up - RED, MAROON, WHITE', 'Community Is Stronger Than Cancer Day'),
        ('Light up for PRIDE MONTH!  ', 'Pride Month'),
        ('Go Green for St. Patrick’s Day', 'St. Patrick’s Day'),
        ('National 4-H Week "GO GREEN DAY" - LIGHT UP GREEN', 'National 4-H Week "GO GREEN DAY"'),
        ('World Smile Day – Event theme: Lighting up the World with Smiles ', 'World Smile Day, Event theme: Lighting up the World with Smiles'),
        ('Welcome Cherelle Parker - 100th Mayor of Philadelphia', 'Welcome Cherelle Parker, 100th Mayor of Philadelphia'),
        ('Rare Disease Day "Light UP for Rare" - LIGHT UP ORANGE/BLUE/PURPLE', 'Rare Disease Day "Light UP for Rare"'),
        ('Light Up for Rare – Rare Disease Day ', 'Rare Disease Day'),
        ('LIGHT UP DARK PINK', 'Light Up Dark Pink'),
        ('Celebrate the 27th Annual Lights On Afterschool - LIGHT UP TEAL/BLUE!', 'Celebrate the 27th Annual Lights On Afterschool'),
    ]

    def test_cleaning(self):
        for title, want in self.CASES:
            with self.subTest(title=title):
                self.assertEqual(want, clean_name(title))

    def test_hud_rule(self):
        for title, _ in self.CASES:
            out = clean_name(title)
            self.assertFalse(BAD.search(out), 'a dash or middot survived in %r' % out)
            self.assertEqual(out, out.strip())
            self.assertNotIn('  ', out)
            self.assertNotIn('(Copy)', out)
        self.assertEqual('Headhouse Market, Shambles', clean_name('Headhouse Market — Shambles'), 'the em dash becomes a comma')
        self.assertEqual('Day, Night', clean_name('Day · Night'))

    def test_script_guard(self):
        with self.assertRaises(ValueError):
            clean_name('Bad </script><script>alert(1)</script> - LIGHT UP BLUE')


class Dates(unittest.TestCase):
    def test_summer_span(self):
        self.assertEqual(('2026-09-16', '2026-09-18'), local_dates(1789531200440, 1789790340440))

    def test_winter_midnight_is_that_day(self):
        self.assertEqual(('2025-11-11', '2025-11-11'), local_dates(ms(2025, 11, 11, 5), ms(2025, 11, 12, 4, 59)))

    def test_late_morning_start(self):
        self.assertEqual('2026-06-12', local_dates(ms(2026, 6, 12, 15), ms(2026, 6, 13, 3, 59))[0])

    def test_end_at_midnight_steps_back(self):
        self.assertEqual(('2026-03-05', '2026-03-06'), local_dates(ms(2026, 3, 5, 5), ms(2026, 3, 7, 5)), 'an end at exactly local midnight belongs to the day before')
        self.assertEqual(('2026-03-05', '2026-03-05'), local_dates(ms(2026, 3, 5, 5), ms(2026, 3, 6, 5, 4)), 'and so does 00:04')
        self.assertEqual(('2026-03-05', '2026-03-06'), local_dates(ms(2026, 3, 5, 5), ms(2026, 3, 6, 5, 5)), 'but 00:05 is the new day')

    def test_end_before_start_clamps(self):
        self.assertEqual(('2026-09-16', '2026-09-16'), local_dates(1789531200440, 1789531200440 - 3 * DAY))


class Bake(unittest.TestCase):
    def items(self):
        return [
            item('a', 'National Breast Cancer Awareness Month | LIGHT UP PINK (Copy)', ms(2026, 10, 1), ms(2026, 10, 3, 3, 59)),
            item('b', 'National Breast Cancer Awareness Month | LIGHT UP PINK', ms(2026, 10, 1), ms(2026, 10, 3, 3, 59)),
            item('c', 'Welcome Cherelle Parker - 100th Mayor of Philadelphia', ms(2026, 9, 20)),
            item('d', 'Kidney Cancer Awareness Month - ORANGE', ms(2025, 3, 8, 5), ms(2025, 3, 10, 4, 59)),      # ended 18 months before NOW
            item('e', 'Pulmonary Fibrosis Awareness Month - LIGHT UP BLUE!', 1789531200440, 1789790340440),
            item('f', 'Ovarian Cancer Awareness - LIGHT UP TEAL', ms(2025, 9, 18), ms(2025, 9, 21, 3, 59)),         # ended 2025-09-20, inside the year
            item('g', 'GO BIRDS!!! ', ms(2026, 9, 12), ms(2026, 9, 14, 3, 59)),
            item('h', 'Childhood Cancer Awareness Month - LIGHT UP GOLD!', ms(2026, 9, 4), ms(2026, 9, 6, 3, 59)),
            item('i', 'Childhood Cancer Awareness Month - LIGHT UP YELLOW', ms(2026, 9, 4), ms(2026, 9, 6, 3, 59)),
            {'id': 'j', 'title': 'No dates - LIGHT UP RED'},
        ]

    def test_rows(self):
        rows, dropped = bake_rows(self.items(), NOW)
        self.assertEqual(['Welcome Cherelle Parker - 100th Mayor of Philadelphia'], dropped, 'the colourless title is reported')
        names = [(r['from'], r['to'], r['c'], r['n']) for r in rows]
        self.assertEqual([
            ('2025-09-18', '2025-09-20', ['teal'], 'Ovarian Cancer Awareness'),
            ('2026-09-04', '2026-09-05', ['gold'], 'Childhood Cancer Awareness Month'),
            ('2026-09-04', '2026-09-05', ['yellow'], 'Childhood Cancer Awareness Month'),
            ('2026-09-12', '2026-09-13', ['green'], 'Go Birds'),
            ('2026-09-16', '2026-09-18', ['blue'], 'Pulmonary Fibrosis Awareness Month'),
            ('2026-10-01', '2026-10-02', ['pink'], 'National Breast Cancer Awareness Month'),
        ], names, 'sorted by (from, to, n); the (Copy) twin collapsed; the row older than a year gone; the same dates in two colours both kept')
        for r in rows:
            self.assertEqual(sorted(r), ['c', 'from', 'n', 'to'])

    def test_contract(self):
        out = bake(self.items(), NOW)
        self.assertEqual(['rows', 't'], sorted(out))
        self.assertEqual(float(NOW), out['t'])
        self.assertIsInstance(out['t'], float)
        s = json.dumps(out, separators=(',', ':'), ensure_ascii=False)
        self.assertNotIn('</script', s.lower())
        self.assertFalse(BAD.search(s), 'no dash or middot anywhere in the file')
        self.assertEqual(out['rows'], bake_rows(self.items(), NOW)[0])

    def test_year_cut_edge(self):
        keep = item('k', 'Edge - LIGHT UP RED', ms(2025, 9, 15), ms(2025, 9, 17, 3, 59))     # ends 2025-09-16, the cutoff day itself
        cut = item('l', 'Edge - LIGHT UP RED', ms(2025, 9, 14), ms(2025, 9, 16, 3, 59))      # ends 2025-09-15
        rows, _ = bake_rows([keep, cut], NOW)
        self.assertEqual([('2025-09-15', '2025-09-16')], [(r['from'], r['to']) for r in rows])

    def test_empty(self):
        self.assertEqual(([], []), bake_rows([], NOW))
        self.assertEqual({'t': float(NOW), 'rows': []}, bake(None, NOW))


class Main(unittest.TestCase):
    """main()'s writers, on a temp dir: the pipeline run writes lights.json alone, the VPS run
    (--out or --fetch) the .gz twin too, and a dead feed keeps the previous file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = (B.RAW, B.OUT, F.fetch_all, B.time.time)
        B.time.time = lambda: NOW      # main() bakes on the wall clock; pinned to NOW, or row f ages past the year cut on 2026-09-21 and the counts drift (Round 125)
        B.RAW = os.path.join(self.tmp.name, 'boma.json')
        B.OUT = os.path.join(self.tmp.name, 'lights.json')
        with open(B.RAW, 'w') as f:
            json.dump(Bake().items(), f)
        self.quiet = contextlib.redirect_stdout(io.StringIO())   # main() reports to stdout; the suite stays clean
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        B.RAW, B.OUT, F.fetch_all, B.time.time = self.saved
        self.tmp.cleanup()

    def test_pipeline_mode_no_gz(self):
        self.assertEqual(0, B.main([]))
        d = json.load(open(B.OUT))
        self.assertEqual(6, len(d['rows']))
        self.assertFalse(os.path.exists(B.OUT + '.gz'), 'the repo never gains a lights.json.gz')
        self.assertNotIn('\n', open(B.OUT).read(), 'compact json like the other bakes')

    def test_out_publishes_twin(self):
        out = os.path.join(self.tmp.name, 'served', 'lights.json')
        os.makedirs(os.path.dirname(out))
        self.assertEqual(0, B.main(['--out', out, '-v']))
        raw = open(out, 'rb').read()
        self.assertEqual(raw, gzip.decompress(open(out + '.gz', 'rb').read()), 'the .gz twin is the file')
        self.assertEqual(0o644, os.stat(out).st_mode & 0o777)
        self.assertEqual(6, len(json.loads(raw)['rows']))
        self.assertFalse([n for n in os.listdir(os.path.dirname(out)) if n.endswith('.tmp')], 'no temp file left behind')

    def test_fetch_failure_keeps_previous(self):
        out = os.path.join(self.tmp.name, 'lights.json')
        with open(out, 'w') as f:
            f.write('{"t":1,"rows":[]}')

        def dead():
            raise RuntimeError('http 503')
        F.fetch_all = dead
        self.assertEqual(1, B.main(['--fetch', '--out', out]))
        self.assertEqual('{"t":1,"rows":[]}', open(out).read(), 'the previous file stands')
        self.assertFalse(os.path.exists(out + '.gz'))

    def test_fetch_mode_uses_fetch_all(self):
        out = os.path.join(self.tmp.name, 'lights.json')
        F.fetch_all = lambda: Bake().items()[4:5]
        self.assertEqual(0, B.main(['--fetch', '--out', out]))
        d = json.load(open(out))
        self.assertEqual(['Pulmonary Fibrosis Awareness Month'], [r['n'] for r in d['rows']])
        self.assertTrue(os.path.exists(out + '.gz'))
        F.fetch_all = lambda: [Bake().items()[2]]     # only the colourless title: an empty parse
        self.assertEqual(1, B.main(['--fetch', '--out', out]))
        self.assertEqual(d, json.load(open(out)), 'an empty parse keeps the previous file')


class Fetch(unittest.TestCase):
    def test_pages(self):
        def full(id_, title, start):
            it = item(id_, title, start)
            it.update({'body': '<p>ignored</p>', 'excerpt': 'x', 'urlId': id_, 'categories': [], 'tags': []})
            return it
        pages = {
            F.page_url(): {'collection': {'itemCount': 4},
                           'pagination': {'nextPage': True, 'nextPageOffset': 1700000000000, 'nextPageUrl': '/x?offset=1700000000000', 'pageSize': 30},
                           'upcoming': [full('a', 'A - LIGHT UP BLUE', 300)],
                           'past': [full('b', 'B - LIGHT UP RED', 100)]},
            F.page_url(1700000000000): {'collection': {'itemCount': 4},
                                        'pagination': {'nextPage': False, 'nextPageOffset': None, 'pageSize': 30},
                                        'upcoming': [],
                                        'past': [full('b', 'B - LIGHT UP RED', 100), full('c', 'C', 200), {'title': 'no id', 'startDate': 1, 'endDate': 2},
                                                 {'id': 'd', 'title': 'no dates'}]},
        }
        calls = []

        def get(url):
            calls.append(url)
            return pages[url]
        items = F.fetch_all(get)
        self.assertEqual([F.page_url(), F.page_url(1700000000000)], calls, 'the pagination is followed to the last page')
        self.assertTrue(calls[1].endswith('?format=json&offset=1700000000000'))
        self.assertEqual(['b', 'c', 'a'], [it['id'] for it in items], 'deduped by id, sorted by startDate')
        for it in items:
            self.assertEqual(set(F.KEEP), set(it), 'only the trimmed keys are kept')
            self.assertIsInstance(it['startDate'], int)
            self.assertIsInstance(it['endDate'], int)
        self.assertEqual('https://www.bomaphila.com/building-illumination-calendar?format=json', F.page_url())

    def test_stops_without_pagination(self):
        items = F.fetch_all(lambda url: {'collection': {}, 'upcoming': [item('a', 'A', 1)], 'past': []})
        self.assertEqual(['a'], [it['id'] for it in items])


if __name__ == '__main__':
    unittest.main()
