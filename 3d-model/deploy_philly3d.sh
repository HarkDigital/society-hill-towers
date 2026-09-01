#!/bin/sh
# Build, verify and ship the model to philly3d.com (nginx on the lionspool VPS,
# ~/.ssh/config Host lionspool-vps). FLIGHT_PROXY in the source already
# points at https://philly3d.com/adsb — same-origin here, CORS-open for the
# GitHub Pages copy — so both homes deploy the identical build.
#
#   ./deploy_philly3d.sh             tests -> build -> gzip -> stage -> keep prev
#                                    -> rsync --delay-updates -> verify live
#   ./deploy_philly3d.sh --rollback  put the previous index.html + .gz pair back
#                                    and verify the live site serves it
#
# Atomic:     rsync --delay-updates lands index.html and its gzip twin in one
#             final rename pass instead of one file at a time.
# Reversible: the pair being replaced is copied to /var/www/philly3d-prev on
#             the box first; --rollback copies it back (brand files are not
#             kept — they change rarely and any deploy restores them).
# Verified:   the script ends by fetching https://philly3d.com/ twice, once
#             identity and once gzip-encoded piped through gunzip, and compares
#             both sha256s with the local build. Any mismatch exits non-zero.
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
GZ_MAX=${GZ_MAX:-12000000}    # bytes; above this something bloated the page
                              # (measured Sep 2026: 22.98 MB page -> 12.76 MB gzip)

fatal() { echo "FATAL: $*" >&2; exit 1; }
sha() {                        # sha256 hex of a file, GNU or BSD userland
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

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
  want=$(ssh "$HOST" "sha256sum $WEB/index.html" | cut -d' ' -f1)
  echo "== verifying $URL serves sha256 $want"
  verify_live "$want"
  echo "rolled back: $URL serves the previous build ($want)."
  echo "note: $PREV now equals what is live — a second --rollback is a no-op until the next deploy."
  exit 0
fi
[ -z "${1:-}" ] || fatal "unknown argument: $1 (only --rollback is understood)"

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
grep -q "FLIGHT_PROXY = 'https://philly3d.com/adsb'" "$TMP/index.html" \
  || fatal "refusing to ship a proxyless build (FLIGHT_PROXY is not the philly3d.com /adsb passthrough)"
grep -q 'property="og:image"' "$TMP/index.html" \
  || fatal "refusing to ship an unbranded build (no og:image)"
# nginx gzip_static serves this twin; ~23 MB page -> ~12.8 MB gzip (Sep 2026)
gzip -k9f "$TMP/index.html"
GZ=$(wc -c < "$TMP/index.html.gz" | tr -d ' ')
[ "$GZ" -ge "$GZ_MIN" ] || fatal "index.html.gz is only $GZ bytes (< GZ_MIN=$GZ_MIN) — truncated build?"
[ "$GZ" -le "$GZ_MAX" ] || fatal "index.html.gz is $GZ bytes (> GZ_MAX=$GZ_MAX) — bloated build? GZ_MAX=N to override on purpose"
# stage + chmod before rsync: the laptop's CloudStorage checkout is all mode
# 600 and -az faithfully ships that, which nginx answers with a site-wide 403
# (learned the hard way; macOS openrsync has no --chmod to fix it in flight)
chmod 644 "$TMP"/*
WANT=$(sha "$TMP/index.html")
echo "   gzip $GZ bytes, sha256 $WANT"

# 3. keep the live pair, then ship
echo "== keeping the live pair in $HOST:$PREV"
ssh "$HOST" 'mkdir -p /var/www/philly3d-prev && cp -a /var/www/philly3d/index.html /var/www/philly3d/index.html.gz /var/www/philly3d-prev/ 2>/dev/null || true'
echo "== rsync"
rsync -az --delay-updates "$TMP/index.html" "$TMP/index.html.gz" \
  "$TMP/favicon.ico" "$TMP/favicon.svg" \
  "$TMP/apple-touch-icon.png" "$TMP/og.png" \
  "$HOST:$WEB/"

# 4. prove the live site serves exactly this build
echo "== verifying $URL against local sha256 $WANT"
verify_live "$WANT"
echo "deployed: $URL serves the new build (gzip $GZ bytes, sha256 $WANT)"
echo "previous pair kept in $HOST:$PREV — '$0 --rollback' restores it"
