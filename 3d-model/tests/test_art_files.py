"""Round 184 (Mike: load the generated art on demand): the AI-made images are files under art/ beside the page.

- every path the three manifests name exists, and its name carries the first 10 hex of its content's sha256, so a file
  never changes under its name (a browser may keep it; a rolled-back page finds its own art on the server);
- art/ holds nothing the manifests do not name (the bakes prune), and no manifest holds a data URL;
- the page loads them by relative path through artImage / artSrc, a phone taking the half copies;
- build.py refuses a missing file, deploy_philly3d.sh ships art/ before the page and never deletes there, and the app
  copies the files a phone can ask for into www/art (Round 225: never the whole folder, tests/test_app_art.py).

Round 225 (the Nov 10, 2026 plan's Stage 1, DELIVERY-1 step 1): the deploy sends the server only the art it does not
have (rsync --ignore-existing). Until then every deploy re-dated all 782 files, and nginx's ETag is a file's time and
size, so every visitor's cached art was downloaded again after each one (up to 33.6 MB on a computer).
- every file under art/, read from the disk and not from the manifests, is named by its own content's hash, which is
  what makes skipping an existing name safe; art_files.unhashed is the deploy's own refusal of anything else;
- the flag does what the deploy needs with this machine's rsync: a file that is there keeps its time (so its ETag), a
  new one is sent, and the flag reaches the receiving side's command line;
- what the old rsync did on the way stays guaranteed: the modes, and every local file on the box at its own size."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import art_files  # noqa: E402  (hashlib, io, os, re and sys only: no imaging library is needed to check names)
MANIFESTS = ('fronts.json', 'tree_art.json', 'ground_art.json', 'wall_art.json', 'land_mask.json', 'water_art.json', 'street_art.json')   # the walls, the land mask, the water and the streets: the realism pass


def paths(o):
    if isinstance(o, str):
        return [o] if o.startswith('art/') else []
    if isinstance(o, dict):
        return [p for v in o.values() for p in paths(v)]
    if isinstance(o, list):
        return [p for v in o for p in paths(v)]
    return []


MANIFESTS += ('vehicle_art.json',)   # the vehicles' (the realism pass)
MANIFESTS += ('storefront_art.json',)   # the storefronts' shopfronts (Round 189)
MANIFESTS += ('cityhall_art.json',)   # City Hall's facades (Round 191)
MANIFESTS += ('glory_art.json',)   # Glory Beer Bar & Kitchen's elevations, swatches and rooms (Round 191)
MANIFESTS += ('glass_art.json',)   # the glass towers' frame and room atlases (Round 192)
MANIFESTS += ('tavern_art.json',)   # A Man Full of Trouble's atlas (Round 199)
MANIFESTS += ('indhall_art.json',)   # Independence Hall's atlas (Round 210)
MANIFESTS += ('tower_art.json',)   # the buildings round City Hall in their own facades (Round 198)
MANIFESTS += ('sht_art.json',)   # the Society Hill Towers' concrete (Round 195)
MANIFESTS += ('liberty_art.json',)   # One and Two Liberty Place's granite base and crown glazing (Round 195)
MANIFESTS += ('comcast_art.json',)   # the Comcast Technology Center's cladding strip (Round 195)
MANIFESTS += ('stadium_art.json',)   # the sports complex's walls, seat rows, turf and clay (Round 195)
MANIFESTS += ('nj_art.json',)   # the USS New Jersey's plating, bulkhead, deck and teak (Round 195)
MANIFESTS += ('moshulu_art.json',)   # the Moshulu's hull plating and teak deck (Round 195)
MANIFESTS += ('olympia_art.json',)   # the cruiser Olympia's plating, superstructure, deck and buff (Round 215)
MANIFESTS += ('blade_art.json',)   # the blade signs' six blanks (the realism round two, R9)
MANIFESTS += ('street_floor_art.json',)   # the street floors made again, behind ?streetfloor= (Round 243)
MANIFESTS += ('bridge_art.json',)   # the Delaware bridges' steel, granite and concrete and the Ben Franklin's anchorage (Round 195)
MANIFESTS += ('people_art.json',)   # the walking people's atlases, one a wardrobe (Rounds 227 and 242)


class Files(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.named = []
        for m in MANIFESTS:
            text = (ROOT / m).read_text()
            cls.named += paths(json.loads(text))
            assert 'data:image/' not in text, m

    def test_every_named_file_is_there_under_its_hash(self):
        self.assertGreater(len(self.named), 400)
        for p in self.named:
            f = ROOT / p
            self.assertTrue(f.exists(), p)
            m = re.fullmatch(r'art/(fronts|tiles|trees|ground|walls|land|water|streets|vehicles|storefronts|cityhall|glory|glass|tavern|indhall|towers|sht|liberty|comcast|stadiums|nj|moshulu|olympia|bridges|blades|people|floors)/[a-z0-9-]+\.([0-9a-f]{10})\.(webp|png)', p)
            self.assertTrue(m, p)
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest()[:10], m.group(2), p)

    def test_nothing_unnamed_ships(self):
        on_disk = {str(f.relative_to(ROOT)) for f in (ROOT / 'art').rglob('*') if f.is_file()}
        self.assertEqual(on_disk - set(self.named), set())

    def test_every_file_on_the_disk_is_named_by_its_hash(self):
        # Round 225: the proof behind the deploy's --ignore-existing, taken from the folder the deploy stages and not
        # from the manifests (the two tests above tie the one to the other): 782 files on Nov 10, 2026, 0 exceptions
        on_disk = [f for f in (ROOT / 'art').rglob('*') if f.is_file()]
        self.assertGreater(len(on_disk), 700)
        for f in on_disk:
            m = re.fullmatch(r'[a-z0-9-]+\.([0-9a-f]{10})\.(webp|png)', f.name)
            self.assertTrue(m, f)
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest()[:10], m.group(1), f)
            self.assertEqual(len(f.relative_to(ROOT / 'art').parts), 2, f)   # art/<kind>/<file>, nothing deeper or loose
        self.assertEqual({str(f.relative_to(ROOT)) for f in on_disk}, set(self.named))
        self.assertEqual(art_files.unhashed(), [])   # the deploy's own check agrees

    def test_every_kind_has_a_phone_copy(self):
        named = set(self.named)
        for p in named:
            if '-half' in p or '-mask' in p:
                continue
            if p.startswith('art/glass/rooms.'):   # Round 192's review: the glass's room pictures are a computer's (a phone never draws them)
                continue
            kind, name = p.split('/')[1], p.split('/')[2].split('.')[0]
            if name.endswith('-sharp'):   # Round 227: a sharp copy is a computer's; a phone takes its record's half
                name = name[:-6]
            self.assertTrue(any(q.startswith('art/%s/%s-half.' % (kind, name)) for q in named), p)


class Wiring(unittest.TestCase):
    def test_the_page_loads_them(self):
        s = (ROOT / 'app.js').read_text()
        self.assertIn('const artSrc = (full, half) => (isTouch && half ? half : full);', s)
        self.assertIn('function artImage(src) {', s)
        for call in ('artImage(artSrc(full, half))', 'artImage(artSrc(T.img, T.imgHalf))', 'artImage(artSrc(rec.img, rec.imgHalf))',
                     'artImage(artSrc(GROUND_ART.lawn, GROUND_ART.lawnHalf))', 'artImage(artSrc(A.img, A.imgHalf)), artImage(artSrc(A.mask, A.maskHalf))'):
            self.assertIn(call, s)
        self.assertNotIn('im.src = rec.img', s)

    def test_build_guards_them(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('art file(s) the manifests name are missing', b)
        self.assertIn('still inlines data URLs', b)

    def test_deploy_ships_them_first_and_never_deletes(self):
        d = (ROOT / 'deploy_philly3d.sh').read_text()
        # Round 225 moved this pin: the art's rsync carries --ignore-existing (see OnlyNewArt below)
        art, page = d.index('rsync -az --ignore-existing "$TMP/art/" "$HOST:$WEB/art/"'), d.index('rsync -az --delay-updates "$TMP/index.html"')
        self.assertLess(art, page)
        self.assertNotIn('--delete', d)
        self.assertIn('find "$TMP/art" -type d -exec chmod 755 {} +', d)
        self.assertIn('find "$TMP" -maxdepth 1 -type f -exec chmod 644 {} +', d)   # a chmod 644 of "$TMP"/* would lock art/

    def test_the_app_carries_them(self):
        # Round 225: the files a phone can ask for, by art-touch.mjs's list from the page it copies, never the whole folder
        # (365 full-size files, 33.4 MB, that no app launch reads); tests/test_app_art.py holds the list to artSrc's rule
        c = (ROOT.parent / 'app' / 'scripts' / 'copy-web.mjs').read_text()
        self.assertIn("resolve(here, '../../3d-model')", c)
        self.assertIn("import { artNamed, artTouch } from './art-touch.mjs';", c)
        self.assertIn("copyFileSync(join(from, p), to);", c)
        self.assertNotIn('cpSync', c)


def nginx_etag(path):
    """nginx's ETag for a static file: its modification time and its size, in hex."""
    st = os.stat(path)
    return '"%x-%x"' % (int(st.st_mtime), st.st_size)


class OnlyNewArt(unittest.TestCase):
    """Round 225: the deploy's art rsync sends only what the server does not have."""

    @classmethod
    def setUpClass(cls):
        cls.d = (ROOT / 'deploy_philly3d.sh').read_text()

    def test_the_names_come_from_the_content(self):
        a = (ROOT / 'art_files.py').read_text()
        self.assertIn("rel = 'art/%s/%s.%s.%s' % (kind, name, hashlib.sha256(data).hexdigest()[:10], ext)", a)

    def test_unhashed_names_what_must_not_ship(self):
        with tempfile.TemporaryDirectory() as t:
            kind = Path(t) / 'fronts'
            kind.mkdir()
            good = b'the bytes of an image'
            (kind / ('row-a.%s.webp' % hashlib.sha256(good).hexdigest()[:10])).write_bytes(good)
            self.assertEqual(art_files.unhashed(t), [])
            run = subprocess.run([sys.executable, str(ROOT / 'art_files.py'), 'check', t], capture_output=True, text=True, timeout=60)
            self.assertEqual((run.returncode, run.stdout), (0, ''))
            (kind / 'row-b.0123456789.webp').write_bytes(b'bytes that do not hash to that')   # a name that lies
            (kind / 'lawn.webp').write_bytes(good)                                           # no hash at all
            (kind / ('ROW.%s.webp' % hashlib.sha256(good).hexdigest()[:10])).write_bytes(good)   # not the bakes' alphabet
            (Path(t) / '.DS_Store').write_bytes(b'Bud1')                                     # the Finder's
            wrong = ['.DS_Store', 'fronts/ROW.%s.webp' % hashlib.sha256(good).hexdigest()[:10], 'fronts/lawn.webp', 'fronts/row-b.0123456789.webp']
            self.assertEqual(art_files.unhashed(t), wrong)
            run = subprocess.run([sys.executable, str(ROOT / 'art_files.py'), 'check', t], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(run.stdout.split(), wrong)
            self.assertIn('4 file(s)', run.stderr)

    def test_the_real_art_passes_the_deploys_check(self):
        run = subprocess.run([sys.executable, str(ROOT / 'art_files.py'), 'check', str(ROOT / 'art')], capture_output=True, text=True, timeout=120)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, '', ''))

    def test_the_deploy_sends_only_what_the_box_lacks(self):
        d = self.d
        flagged = 'rsync -az --ignore-existing "$TMP/art/" "$HOST:$WEB/art/"'
        self.assertEqual(d.count(flagged), 1)
        self.assertNotIn('rsync -az "$TMP/art/"', d)             # the plain copy that re-dated every file is gone
        self.assertIn('cp -R art "$TMP/art"', d)                 # and not cp -Rp: the staged times no longer matter
        self.assertNotIn('--size-only', d)                       # with -t that still resets a skipped file's time
        # the page, its gzip twin and the brand files are replaced at every deploy: only the art skips
        page = d[d.index('rsync -az --delay-updates "$TMP/index.html" "$TMP/index.html.gz"'):]
        page = page[:page.index('"$HOST:$WEB/"') + len('"$HOST:$WEB/"')]
        self.assertNotIn('existing', page)
        for line in d.splitlines():
            if line.startswith('rsync '):
                self.assertTrue(line.startswith(flagged) or line.startswith('rsync -az --delay-updates "$TMP/index.html"'), line)

    def test_the_deploy_refuses_a_name_that_is_not_its_hash(self):
        d = self.d
        check = d.index('python3 art_files.py check "$TMP/art" \\\n  || fatal "refusing to ship art that is not named by its content\'s hash')
        self.assertLess(d.index('cp -R art "$TMP/art"'), check)
        self.assertLess(check, d.index('ssh "$HOST" "mkdir -p $PREV'))   # before anything on the box is touched
        self.assertLess(check, d.index('rsync -az --ignore-existing'))

    def test_the_deploy_keeps_what_the_old_rsync_guaranteed(self):
        d = self.d
        send = d.index('rsync -az --ignore-existing "$TMP/art/" "$HOST:$WEB/art/"')
        # the modes: staged 755 and 644 for what is sent, and put right on the box for what is not sent any more
        self.assertIn('find "$TMP/art" -type f -exec chmod 644 {} +', d)
        for fix in ('find $WEB/art -type d ! -perm 755 -exec chmod 755 {} +', 'find $WEB/art -type f ! -perm 644 -exec chmod 644 {} +'):
            self.assertEqual(d.count(fix), 1)
            self.assertLess(d.index(fix), send)
        # every local file is on the box afterwards, at its own size (an existing file is never repaired by the rsync)
        after = d.index('ssh "$HOST" "cd $WEB/art && $ART_LS" > "$TMP/art-remote.raw" || fatal "could not list $HOST:$WEB/art"')
        miss = d.index('ART_MISS=$(LC_ALL=C comm -23 "$TMP/art-local.txt" "$TMP/art-remote.txt")')
        stop = d.index('[ -z "$ART_MISS" ] || fatal "art files missing on $HOST after rsync, or there at another size')
        page = d.index('rsync -az --delay-updates "$TMP/index.html"')
        self.assertTrue(send < after < miss < stop < page)
        # one file of each of four kinds is still fetched over https and compared by sha256
        live = d.index('for kind in fronts tiles trees ground; do')
        self.assertLess(page, live)
        self.assertIn('[ "$(sha "$TMP/live-art")" = "$(sha "$TMP/art/$kind/$f")" ] || fatal "the live art/$kind/$f does not match this one"', d)
        self.assertNotIn('--delete', d)

    def test_a_moved_etag_warns_and_never_fails_the_deploy(self):
        # both verifiers: by then the art has landed and the old page is still live and correct
        d = self.d
        was = d.index('ETAG_WAS=$(curl -sI --max-time 30 "${URL}art/$ART_PROBE" 2>/dev/null | etag_line) || ETAG_WAS=""')
        now = d.index('ETAG_NOW=$(curl -sI --max-time 30 "${URL}art/$ART_PROBE" 2>/dev/null | etag_line) || ETAG_NOW=""')
        self.assertTrue(was < d.index('rsync -az --ignore-existing') < now)
        warn = [l for l in d.splitlines() if 'the ETag of art/$ART_PROBE moved' in l]
        self.assertEqual(len(warn), 1)
        self.assertTrue(warn[0].strip().startswith('|| echo "WARNING: '), warn[0])
        self.assertTrue(warn[0].rstrip().endswith('>&2'))
        self.assertNotIn('fatal', warn[0])
        # the probe is a file the box had before the rsync, at its right size
        self.assertIn('ART_PROBE=$(LC_ALL=C comm -12 "$TMP/art-local.txt" "$TMP/art-before.txt" | head -1 | cut -d\' \' -f1)', d)

    def helpers(self):
        """The script's three text helpers, cut out by their first words (nothing in them reaches a network)."""
        cut = [l for l in self.d.splitlines() if l.startswith(("ART_LS='", 'art_rows() {', 'etag_line() {'))]
        self.assertEqual(len(cut), 3)
        for word in ('ssh', 'rsync', 'curl', 'scp'):
            self.assertNotIn(word, ' '.join(cut))
        return '\n'.join(cut) + '\n'

    def test_the_listing_is_every_file_with_its_size(self):
        # the real art, listed by the script's own command and reduced by its own filter
        with tempfile.TemporaryDirectory() as t:
            script = 'set -eu\n' + self.helpers() + '(cd "$1" && $ART_LS) > "$2/raw"\nart_rows "$2/raw"\n'
            run = subprocess.run(['sh', '-c', script, 'sh', str(ROOT / 'art'), t], capture_output=True, text=True, timeout=120)
            self.assertEqual((run.returncode, run.stderr), (0, ''))
            want = sorted('./%s %d' % (f.relative_to(ROOT / 'art').as_posix(), f.stat().st_size)
                          for f in (ROOT / 'art').rglob('*') if f.is_file())
            self.assertGreater(len(want), 700)
            self.assertEqual(run.stdout.splitlines(), want)
            # the server's wc (GNU): padded counts and a total line a batch, in whatever order find met the files
            raw = Path(t) / 'gnu'
            raw.write_text('  165780 ./fronts/row-b.1111111111.webp\n     900 ./fronts/row-a.0000000000.webp\n  166680 total\n'
                           '12 ./trees/oak-half.2222222222.webp\n      12 total\n7 ./ground/total\n')
            run = subprocess.run(['sh', '-c', 'set -eu\n' + self.helpers() + 'art_rows "$1"\n', 'sh', str(raw)], capture_output=True, text=True, timeout=60)
            self.assertEqual((run.returncode, run.stderr), (0, ''))
            self.assertEqual(run.stdout.splitlines(), ['./fronts/row-a.0000000000.webp 900', './fronts/row-b.1111111111.webp 165780',
                                                       './ground/total 7', './trees/oak-half.2222222222.webp 12'])

    def test_the_etag_is_read_from_either_protocols_headers(self):
        sh = 'set -eu\n' + self.helpers() + 'etag_line\n'
        for head, want in (('HTTP/2 200 \r\nserver: nginx\r\ncontent-length: 165780\r\netag: "6ade87aa-28794"\r\naccept-ranges: bytes\r\n\r\n', '"6ade87aa-28794"\n'),
                           ('HTTP/1.1 200 OK\r\nServer: nginx\r\nETag: "6ade87aa-58f48"\r\n\r\n', '"6ade87aa-58f48"\n'),
                           ('HTTP/2 404 \r\nserver: nginx\r\n\r\n', ''), ('', '')):
            run = subprocess.run(['sh', '-c', sh], input=head.encode(), capture_output=True, timeout=60)
            self.assertEqual((run.returncode, run.stdout.decode(), run.stderr.decode()), (0, want, ''))

    @unittest.skipUnless(shutil.which('rsync'), 'no rsync on this machine')
    def test_rsync_leaves_what_is_there_alone(self):
        """The flag itself, with this machine's rsync and the script's own flags, through a stand-in remote shell that
        runs the receiving side here: a file the box has keeps its time, so its ETag, and its bytes; a new file is sent;
        and the control (the flags the deploy used until Round 225) re-dates the same file, which is what every deploy did."""
        flags = re.search(r'^rsync (-az --ignore-existing) "\$TMP/art/" "\$HOST:\$WEB/art/"$', self.d, re.M).group(1).split()
        with tempfile.TemporaryDirectory() as t:
            t = Path(os.path.realpath(t))
            self.assertNotIn(' ', str(t))   # a remote shell splits the receiving command on spaces, as ssh does
            rsh = t / 'rsh'
            rsh.write_text('#!/bin/sh\n# drop the host, note the receiving command, run it here\nshift\necho "$*" >> "$RSH_LOG"\nexec "$@"\n')
            rsh.chmod(0o755)
            src = t / 'staged' / 'fronts'
            src.mkdir(parents=True)
            same, other = b'an image the box already has', b'what a wrong file would hold'
            name = 'row-a.%s.webp' % hashlib.sha256(same).hexdigest()[:10]
            (src / name).write_bytes(same)
            (src / 'row-new.0000000000.webp').write_bytes(b'baked since the last deploy')
            (src / 'row-odd.1111111111.webp').write_bytes(same)
            deploy, last = 1_794_000_000, 1_792_000_000   # this deploy's second (what cp -R stamps) and the last one's
            for f in src.iterdir():
                f.chmod(0o644)
                os.utime(f, (deploy, deploy))

            def box(tag):
                d = t / tag / 'art' / 'fronts'
                d.mkdir(parents=True)
                (d / name).write_bytes(same)
                (d / 'row-odd.1111111111.webp').write_bytes(other)   # same name, other bytes: only a hash name rules this out
                (d / 'row-old.2222222222.webp').write_bytes(b'art an older page still names')
                for f in d.iterdir():
                    f.chmod(0o644)
                    os.utime(f, (last, last))
                return d

            def send(fl, d, log):
                env = dict(os.environ, RSH_LOG=str(log))
                run = subprocess.run(['rsync', *fl, '-e', str(rsh), str(src.parent) + '/', 'box:' + str(d.parent) + '/'],
                                     capture_output=True, text=True, timeout=120, env=env)
                self.assertEqual(run.returncode, 0, run.stderr)
                return log.read_text()

            new = box('new')
            before = nginx_etag(new / name)
            self.assertEqual(before, '"%x-%x"' % (last, len(same)))
            cmd = send(flags, new, t / 'new.log')
            self.assertIn(' --ignore-existing ', cmd)                # the receiving rsync is told, not only this one
            self.assertEqual(nginx_etag(new / name), before)         # the ETag outlives the deploy
            self.assertEqual((new / name).read_bytes(), same)
            self.assertEqual((new / 'row-odd.1111111111.webp').read_bytes(), other)   # never repaired: hence the size check
            self.assertEqual(int((new / 'row-odd.1111111111.webp').stat().st_mtime), last)
            self.assertEqual((new / 'row-new.0000000000.webp').read_bytes(), b'baked since the last deploy')
            self.assertEqual((new / 'row-new.0000000000.webp').stat().st_mode & 0o777, 0o644)
            self.assertTrue((new / 'row-old.2222222222.webp').exists())   # added, never deleted

            old = box('old')
            cmd = send(['-az'], old, t / 'old.log')
            self.assertNotIn('ignore-existing', cmd)
            self.assertEqual(nginx_etag(old / name), '"%x-%x"' % (deploy, len(same)))   # same bytes, a new ETag: the fault
            self.assertNotEqual(nginx_etag(old / name), before)


if __name__ == '__main__':
    unittest.main()
