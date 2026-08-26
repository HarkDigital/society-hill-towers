#!/bin/sh
# Build and ship the model to philly3d.com (nginx on the lionspool VPS,
# ~/.ssh/config Host lionspool-vps). FLIGHT_PROXY in the source already
# points at https://philly3d.com/adsb — same-origin here, CORS-open for the
# GitHub Pages copy — so both homes deploy the identical build.
set -e
cd "$(dirname "$0")"
python3 build.py
for f in brand/dist/favicon.ico brand/dist/favicon.svg \
         brand/dist/apple-touch-icon.png brand/dist/og.png; do
  [ -f "$f" ] || { echo "FATAL: missing $f (run brand/make_brand.py)"; exit 1; }
done
TMP=$(mktemp -d)
cp society-hill-towers.html "$TMP/index.html"
grep -q "FLIGHT_PROXY = 'https://philly3d.com/adsb'" "$TMP/index.html"   # refuse to ship a proxyless build
grep -q 'property="og:image"' "$TMP/index.html"      # refuse to ship an unbranded build
gzip -k9f "$TMP/index.html"                          # nginx gzip_static serves this, 18.4 -> 10.3 MB
rsync -az "$TMP/index.html" "$TMP/index.html.gz" \
  brand/dist/favicon.ico brand/dist/favicon.svg \
  brand/dist/apple-touch-icon.png brand/dist/og.png \
  lionspool-vps:/var/www/philly3d/
rm -rf "$TMP"
echo "deployed to https://philly3d.com/"
