#!/bin/sh
# Build, verify and ship the model to philly3d.com (nginx on the lionspool VPS,
# ~/.ssh/config Host lionspool-vps). FLIGHT_PROXY in the source already
# points at https://philly3d.com/adsb — same-origin here, CORS-open for the
# (the GitHub Pages copy was retired Sep 17 2026; philly3d.com is the site.)
#
#   ./deploy_philly3d.sh             tests -> build -> gzip -> stage -> keep prev
#                                    -> rsync art/ (new files only) -> rsync --delay-updates -> verify live
#   ./deploy_philly3d.sh --rollback  put the previous index.html + .gz pair back
#                                    and verify the live site serves it
#   ./deploy_philly3d.sh --no-testflight   the deploy alone, without the app upload below
#
# The app follows the site (Round 204, Mike: every deploy goes to TestFlight too): once the live site verifies, a Mac with
# Xcode runs ../app/scripts/testflight.sh (sync, bump, archive, upload, commit the bump). A failed upload is a warning, never
# a failed deploy: the site is already live. PHILLY3D_TESTFLIGHT=0 skips it the same as the flag.
#
# Atomic:     rsync --delay-updates lands index.html and its gzip twin in one
#             final rename pass instead of one file at a time.
# Reversible: the pair being replaced is copied to /var/www/philly3d-prev on
#             the box first; --rollback copies it back (brand files are not
#             kept — they change rarely and any deploy restores them).
# Verified:   the script ends by fetching https://philly3d.com/ twice, once
#             identity and once gzip-encoded piped through gunzip, and compares
#             both sha256s with the local build. Any mismatch exits non-zero.
# Art:        art/ ships before the page, added and never deleted, and since Round 225 a file the
#             box already has is left alone (rsync --ignore-existing): its name is its content's
#             hash, so it cannot have changed, and nginx's ETag for it (its time and size) now
#             outlives a deploy. Every local file must be on the box at its own size afterwards.
# Gated:      the test suite runs before anything is built (warns if tests/
#             does not exist yet), and the gzip must fall inside
#             GZ_MIN..GZ_MAX bytes (a truncated or bloated build never ships).
#
# Overrides (environment): PHILLY3D_HOST (ssh alias), GZ_MIN, GZ_MAX.
set -eu
cd "$(dirname "$0")"

HOST=${PHILLY3D_HOST:-lionspool-vps}
WEB=/var/www/philly3d
PREV=/var/www/philly3d-prev
URL=https://philly3d.com/
GZ_MIN=${GZ_MIN:-8000000}     # bytes; below this the build is truncated or empty
GZ_MAX=${GZ_MAX:-36000000}    # bytes; above this something bloated the page (raised 12 -> 36 MB with the 75 MB raw tripwire, 2026-09-02)
                              # (measured Sep 2026, byte-planar blobs: 22.8 MB page -> 9.8 MB gzip)

fatal() { echo "FATAL: $*" >&2; exit 1; }
sha() {                        # sha256 hex of a file, GNU or BSD userland
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# The art's listing (Round 225), the same command here and on the box: wc -c prints "<bytes> ./<kind>/<name>" a file
# and a total line a batch; art_rows keeps the files' lines as "./<kind>/<name> <bytes>" rows, sorted HERE in the C
# locale so the two machines' collations never meet in comm. etag_line reads the ETag out of a response's headers.
ART_LS='find . -type f -exec wc -c {} +'
art_rows() { awk 'substr($2, 1, 2) == "./" { print $2, $1 }' "$1" | LC_ALL=C sort; }
etag_line() { tr -d '\r' | awk 'tolower($1) == "etag:" { print $2; exit }'; }

# verify_live SHA — fetch the live page identity and gzip-encoded, both must
# hash to SHA. Cache-busting query + no-cache so a max-age=600 copy anywhere
# between here and nginx cannot vouch for a deploy that did not land.
verify_live() {
  bust="?deploy=$(date +%s)"
  curl -fsS --max-time 300 -H 'Accept-Encoding: identity' -H 'Cache-Control: no-cache' \
    -o "$TMP/live-identity.html" "$URL$bust" \
    || fatal "could not fetch $URL (identity)"
  curl -fsS --max-time 300 -H 'Accept-Encoding: gzip' -H 'Cache-Control: no-cache' \
    -D "$TMP/live-gzip.hdr" -o "$TMP/live-gzip.bin" "$URL$bust" \
    || fatal "could not fetch $URL (gzip)"
  grep -iq '^content-encoding: *gzip' "$TMP/live-gzip.hdr" \
    || fatal "live page was not served gzip-encoded (gzip_static off, or index.html.gz missing on the box)"
  gunzip -c "$TMP/live-gzip.bin" > "$TMP/live-gzip.html" \
    || fatal "live gzip body did not gunzip"
  got_id=$(sha "$TMP/live-identity.html")
  got_gz=$(sha "$TMP/live-gzip.html")
  if [ "$got_id" != "$1" ] || [ "$got_gz" != "$1" ]; then
    echo "FATAL: live page does not match — expected sha256 $1" >&2
    echo "       identity fetch: $got_id" >&2
    echo "       gunzipped gzip: $got_gz" >&2
    echo "       roll back with: $0 --rollback" >&2
    exit 1
  fi
}

if [ "${1:-}" = "--rollback" ]; then
  echo "== rolling back $HOST:$WEB to the pair kept in $PREV"
  ssh "$HOST" "test -s $PREV/index.html && test -s $PREV/index.html.gz" \
    || fatal "no previous pair on $HOST:$PREV — nothing to roll back to"
  # copy beside, then rename: a reader never sees a half-written page
  ssh "$HOST" "cp -a $PREV/index.html.gz $WEB/.rb.index.html.gz \
    && cp -a $PREV/index.html $WEB/.rb.index.html \
    && chmod 644 $WEB/.rb.index.html.gz $WEB/.rb.index.html \
    && mv -f $WEB/.rb.index.html.gz $WEB/index.html.gz \
    && mv -f $WEB/.rb.index.html $WEB/index.html" \
    || fatal "rollback copy failed on $HOST"
  want=$(ssh "$HOST" "sha256sum $WEB/index.html" | cut -d' ' -f1) || want=""
  [ -n "$want" ] || fatal "could not read the remote hash of $WEB/index.html (no pipefail in sh: an empty hash would have passed)"
  echo "== verifying $URL serves sha256 $want"
  verify_live "$want"
  echo "rolled back: $URL serves the previous build ($want)."
  echo "note: $PREV now equals what is live — a second --rollback is a no-op until the next deploy."
  exit 0
fi
TESTFLIGHT=${PHILLY3D_TESTFLIGHT:-1}
if [ "${1:-}" = "--no-testflight" ]; then TESTFLIGHT=0; shift; fi
[ -z "${1:-}" ] || fatal "unknown argument: $1 (only --rollback and --no-testflight are understood)"

# 1. tests first — nothing is built, let alone shipped, on a red suite
if [ -d tests ]; then
  echo "== tests"
  python3 -m unittest discover -s tests || fatal "test suite failed — nothing deployed"
else
  echo "WARN: no tests/ directory here yet — skipping the test suite" >&2
fi

# 2. build + stage
echo "== build"
python3 build.py
for f in brand/dist/favicon.ico brand/dist/favicon.svg \
         brand/dist/apple-touch-icon.png brand/dist/og.png; do
  [ -f "$f" ] || fatal "missing $f (run brand/make_brand.py)"
done
cp society-hill-towers.html "$TMP/index.html"
cp brand/dist/favicon.ico brand/dist/favicon.svg \
   brand/dist/apple-touch-icon.png brand/dist/og.png "$TMP/"
# the installable app: the manifest build.py writes beside the page, and the network-only
# service worker (both linked from the page by relative URL, so they sit at the site root)
[ -s manifest.webmanifest ] || fatal "missing manifest.webmanifest (build.py writes it)"
cp manifest.webmanifest sw.js "$TMP/"
# the privacy policy (Round 164: published at /privacy.html, linked from About; the App Store wants it reachable in the app)
[ -s privacy.html ] || fatal "missing privacy.html"
cp privacy.html "$TMP/"
grep -q "FLIGHT_PROXY = 'https://philly3d.com/adsb'" "$TMP/index.html" \
  || fatal "refusing to ship a proxyless build (FLIGHT_PROXY is not the philly3d.com /adsb passthrough)"
grep -q 'property="og:image"' "$TMP/index.html" \
  || fatal "refusing to ship an unbranded build (no og:image)"
# nginx gzip_static serves this twin; 22.8 MB page -> 9.8 MB gzip (Sep 2026, byte-planar blobs)
gzip -k9f "$TMP/index.html"
GZ=$(wc -c < "$TMP/index.html.gz" | tr -d ' ')
[ "$GZ" -ge "$GZ_MIN" ] || fatal "index.html.gz is only $GZ bytes (< GZ_MIN=$GZ_MIN) — truncated build?"
[ "$GZ" -le "$GZ_MAX" ] || fatal "index.html.gz is $GZ bytes (> GZ_MAX=$GZ_MAX) — bloated build? GZ_MAX=N to override on purpose"
# stage + chmod before rsync: the laptop's CloudStorage checkout is all mode
# 600 and -az faithfully ships that, which nginx answers with a site-wide 403
# (learned the hard way; macOS openrsync has no --chmod to fix it in flight)
find "$TMP" -maxdepth 1 -type f -exec chmod 644 {} +
# the generated art (Round 184, Mike: load it on demand): files beside the page
# under art/, each named by its content's hash, so a file never changes under
# its name. Staged with the same modes (dirs 755), shipped BEFORE the page that
# names them, added and never deleted on the box (a rolled-back page still
# finds its own art). build.py already refused a manifest naming a missing file.
[ -d art ] || fatal "missing art/ (the bakes write it: bake_fronts.py, bake_tree_art.py, bake_ground_art.py)"
cp -R art "$TMP/art"
find "$TMP/art" -type d -exec chmod 755 {} +
find "$TMP/art" -type f -exec chmod 644 {} +
# Round 225: the rsync below never sends a file the box already has, which is right only while a name cannot come to
# mean other bytes. So every staged file must carry the first 10 hex of its own sha256 in its name (782 of 782 on
# Nov 10, 2026), a stray .DS_Store included: anything else would be frozen on the box at its first copy.
python3 art_files.py check "$TMP/art" \
  || fatal "refusing to ship art that is not named by its content's hash (the deploy never sends an existing name again)"
ART_N=$(find "$TMP/art" -type f | wc -l | tr -d ' ')
WANT=$(sha "$TMP/index.html")
echo "   gzip $GZ bytes, sha256 $WANT"

# 3. keep the live pair, then ship
echo "== keeping the live pair in $HOST:$PREV"
ssh "$HOST" "mkdir -p $PREV && cp -a $WEB/index.html $WEB/index.html.gz $PREV/ 2>/dev/null || true"
# Round 225: only the files the box does not have. Until now this was a plain rsync -az of a fresh `cp -R`, so every
# staged copy carried the deploy's own second, rsync wrote that time over all 782 files (43.6 MB) and nginx's ETag,
# which is a file's time and size, changed for every one of them at every deploy: a returning visitor's cached art
# answered 200 instead of 304 and was downloaded again, up to 33.6 MB on a computer and 10.2 MB on a phone
# (measured Nov 10, 2026 with curl -sI: files baked Oct 12 to 24 all answered last-modified Oct 25 22:50:18, the
# second of the last deploy). --ignore-existing never touches a file that is there, its time included, the first
# deploy with the flag too (cp -Rp would have re-dated them all once more, to whatever git last did here). What the
# old rsync did on the way is now done on purpose: the modes of what is already there are put right first (a chmod
# moves no modification time, so no ETag), and since a wrong file on the box is no longer overwritten, the listing
# check compares every file's size as well as its name.
ssh "$HOST" "mkdir -p $WEB/art && chmod 755 $WEB/art \
  && find $WEB/art -type d ! -perm 755 -exec chmod 755 {} + \
  && find $WEB/art -type f ! -perm 644 -exec chmod 644 {} + \
  && cd $WEB/art && $ART_LS" > "$TMP/art-before.raw" || fatal "could not prepare and list $HOST:$WEB/art"
(cd "$TMP/art" && $ART_LS) > "$TMP/art-local.raw"
art_rows "$TMP/art-local.raw" > "$TMP/art-local.txt"
art_rows "$TMP/art-before.raw" > "$TMP/art-before.txt"
ART_NEW=$(LC_ALL=C comm -23 "$TMP/art-local.txt" "$TMP/art-before.txt" | wc -l | tr -d ' ')
# one file the box already has, and the ETag it answers with before anything is sent
ART_PROBE=$(LC_ALL=C comm -12 "$TMP/art-local.txt" "$TMP/art-before.txt" | head -1 | cut -d' ' -f1)
ART_PROBE=${ART_PROBE#./}
ETAG_WAS=""
if [ -n "$ART_PROBE" ]; then
  ETAG_WAS=$(curl -sI --max-time 30 "${URL}art/$ART_PROBE" 2>/dev/null | etag_line) || ETAG_WAS=""
fi
echo "== rsync the art ($ART_N files, $ART_NEW the box does not have)"
rsync -az --ignore-existing "$TMP/art/" "$HOST:$WEB/art/"
ssh "$HOST" "cd $WEB/art && $ART_LS" > "$TMP/art-remote.raw" || fatal "could not list $HOST:$WEB/art"
art_rows "$TMP/art-remote.raw" > "$TMP/art-remote.txt"
ART_MISS=$(LC_ALL=C comm -23 "$TMP/art-local.txt" "$TMP/art-remote.txt")
[ -z "$ART_MISS" ] || fatal "art files missing on $HOST after rsync, or there at another size (an existing file is never sent again: remove a wrong one on the box and deploy again): $(echo "$ART_MISS" | head -3 | tr '\n' ' ')"
# a warning and never a failed deploy: the art has landed and is correct, this is the visitors' cache alone
if [ -n "$ETAG_WAS" ]; then
  ETAG_NOW=$(curl -sI --max-time 30 "${URL}art/$ART_PROBE" 2>/dev/null | etag_line) || ETAG_NOW=""
  [ "$ETAG_NOW" = "$ETAG_WAS" ] \
    || echo "WARNING: the ETag of art/$ART_PROBE moved across the art rsync ($ETAG_WAS to ${ETAG_NOW:-none}): the box's art was re-dated and every visitor's cached copy with it" >&2
fi
echo "== rsync"
rsync -az --delay-updates "$TMP/index.html" "$TMP/index.html.gz" \
  "$TMP/favicon.ico" "$TMP/favicon.svg" \
  "$TMP/apple-touch-icon.png" "$TMP/og.png" \
  "$TMP/manifest.webmanifest" "$TMP/sw.js" "$TMP/privacy.html" \
  "$HOST:$WEB/"

# 4. prove the live site serves exactly this build
echo "== verifying $URL against local sha256 $WANT"
verify_live "$WANT"
curl -fsS --max-time 60 -H 'Cache-Control: no-cache' -o "$TMP/live-privacy.html" "${URL}privacy.html?deploy=$(date +%s)" \
  || fatal "could not fetch ${URL}privacy.html"
[ "$(sha "$TMP/live-privacy.html")" = "$(sha "$TMP/privacy.html")" ] || fatal "the live privacy.html does not match this one"
# one art file of each kind, fetched over https and compared byte for byte (nginx serves art/ as plain files)
for kind in fronts tiles trees ground; do
  f=$(cd "$TMP/art" && ls "$kind" 2>/dev/null | head -1)
  [ -n "$f" ] || continue
  curl -fsS --max-time 60 -o "$TMP/live-art" "${URL}art/$kind/$f" || fatal "could not fetch ${URL}art/$kind/$f"
  [ "$(sha "$TMP/live-art")" = "$(sha "$TMP/art/$kind/$f")" ] || fatal "the live art/$kind/$f does not match this one"
done
# Round 244 (the plan's Stage 1): the two server settings Round 225's coda installed (ops/philly3d.vhost.live), checked on
# the live site. Warnings, never a failed deploy: the build is live and right, and these are the visitors' caches. (1) The
# art is answered as immutable for a year, so a returning visitor never asks for it again. (2) A request that came through
# a proxy (a Via header) is still handed the gzip page: without gzip_proxied nginx sent it the 34 MB identity copy
f=$(cd "$TMP/art" && ls fronts 2>/dev/null | head -1)
if [ -n "$f" ]; then
  curl -sI --max-time 30 "${URL}art/fronts/$f" 2>/dev/null | tr -d '\r' | grep -iq '^cache-control:.*max-age=31536000.*immutable' \
    || echo "WARNING: ${URL}art/fronts/$f is not served 'max-age=31536000, immutable': the art's year of caching is gone from the vhost (ops/philly3d.vhost.live)" >&2
fi
curl -s --max-time 300 -o /dev/null -D "$TMP/live-via.hdr" -H 'Accept-Encoding: gzip' -H 'Via: 1.1 proxy' -H 'Cache-Control: no-cache' "$URL?deploy=$(date +%s)" \
  && tr -d '\r' < "$TMP/live-via.hdr" | grep -iq '^content-encoding: *gzip' \
  || echo "WARNING: a request through a proxy (Via) was not handed the gzip page: gzip_proxied is gone from the vhost (ops/philly3d.vhost.live)" >&2
echo "deployed: $URL serves the new build (gzip $GZ bytes, sha256 $WANT) and its $ART_N art files ($ART_NEW sent, the rest left as they were)"
echo "previous pair kept in $HOST:$PREV — '$0 --rollback' restores it"

# 5. the app follows the site (Round 204)
if [ "$TESTFLIGHT" = 1 ]; then
  if command -v xcodebuild >/dev/null 2>&1 && [ -x ../app/scripts/testflight.sh ]; then
    echo "== TestFlight: the same page to the iOS app"
    ../app/scripts/testflight.sh || echo "WARNING: the TestFlight upload failed (the site is live); run app/scripts/testflight.sh again" >&2
  else
    echo "note: no Xcode here, so no TestFlight upload; run app/scripts/testflight.sh on the Mac"
  fi
fi
