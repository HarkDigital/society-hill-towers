#!/bin/sh
# Build and ship the model to philly3d.com (nginx on the lionspool VPS,
# ~/.ssh/config Host lionspool-vps). The VPS copy rides the server's own
# same-origin /adsb flight passthrough, so FLIGHT_PROXY is rewritten at
# deploy time; the repo source stays '' for the GitHub Pages copy.
set -e
cd "$(dirname "$0")"
python3 build.py
TMP=$(mktemp -d)
sed "s|const FLIGHT_PROXY = '';|const FLIGHT_PROXY = '/adsb';|" society-hill-towers.html > "$TMP/index.html"
grep -q "FLIGHT_PROXY = '/adsb'" "$TMP/index.html"   # refuse to ship without the rewrite
gzip -k9f "$TMP/index.html"                          # nginx gzip_static serves this, 18.4 -> 10.3 MB
rsync -az "$TMP/index.html" "$TMP/index.html.gz" lionspool-vps:/var/www/philly3d/
rm -rf "$TMP"
echo "deployed to https://philly3d.com/"
