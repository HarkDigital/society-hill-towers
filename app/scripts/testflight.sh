#!/bin/sh
# Ship the built page to TestFlight in one step (Round 204: Mike asked for every verified deploy to reach the app too, after
# the app sat ten days behind the site). deploy_philly3d.sh runs it after the live site verifies; run it alone with
#
#   app/scripts/testflight.sh            sync -> bump -> archive -> upload -> commit the bump -> TestFlight status
#
# It ships 3d-model/society-hill-towers.html as it stands (build it first; the deploy has). The archive may use the App
# Store Connect key (~/.appstoreconnect, App Manager) for provisioning, but the upload goes through the Apple ID signed in
# to Xcode: the App Manager role has no access to the cloud-managed distribution certificate (Oct 16, build 10). A failed
# upload puts the build number back, so no number is spent on a build TestFlight never saw. Never prints the key's ids.
set -eu
cd "$(dirname "$0")/../.."
ROOT=$(pwd)
fatal() { echo "FATAL (testflight): $*" >&2; exit 1; }
command -v xcodebuild >/dev/null 2>&1 || fatal "xcodebuild not found (this needs a Mac with Xcode)"
[ -s 3d-model/society-hill-towers.html ] || fatal "no built page: run python3 3d-model/build.py first"
BUMPED="app/android/app/build.gradle app/ios/App/App.xcodeproj/project.pbxproj"
git diff --quiet -- $BUMPED || fatal "the build-number files have uncommitted changes; commit or revert them first"

echo "== sync the page and its art into the apps"
(cd app && npm run --silent sync >/dev/null)
echo "== bump the build number"
(cd app && npm run --silent bump)
N=$(sed -n 's/.*CURRENT_PROJECT_VERSION = \([0-9]*\);.*/\1/p' app/ios/App/App.xcodeproj/project.pbxproj | head -1)
undo() { git checkout -- $BUMPED; echo "build number put back (build $N was not uploaded)" >&2; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/philly3d-testflight.XXXXXX")
set --
CFG="$HOME/.appstoreconnect/philly3d.json"
if [ -f "$CFG" ]; then
  KID=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['key_id'])" "$CFG")
  ISS=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['issuer'])" "$CFG")
  KP="$HOME/.appstoreconnect/private_keys/AuthKey_$KID.p8"
  [ -f "$KP" ] && set -- -authenticationKeyPath "$KP" -authenticationKeyID "$KID" -authenticationKeyIssuerID "$ISS"
fi
echo "== archive build $N (log: $WORK/archive.log)"
if ! (cd app/ios/App && xcodebuild -project App.xcodeproj -scheme App -destination 'generic/platform=iOS' -configuration Release \
      -archivePath "$WORK/Philly3D.xcarchive" -allowProvisioningUpdates "$@" archive > "$WORK/archive.log" 2>&1); then
  tail -20 "$WORK/archive.log" >&2; undo; fatal "the archive failed"
fi
echo "== upload build $N through Xcode's account (log: $WORK/export.log)"
if ! (cd app/ios/App && xcodebuild -exportArchive -archivePath "$WORK/Philly3D.xcarchive" -exportOptionsPlist ../UploadOptions.plist \
      -exportPath "$WORK/upload" -allowProvisioningUpdates > "$WORK/export.log" 2>&1); then
  grep -iE "error" "$WORK/export.log" | tail -8 >&2; undo; fatal "the upload failed (is an Apple ID of QuincySoft LLC signed in to Xcode?)"
fi
grep -q "Upload succeeded" "$WORK/export.log" || { undo; fatal "xcodebuild exited cleanly but never reported 'Upload succeeded'"; }

echo "== commit the build number"
git add -- $BUMPED
git commit -q -m "App build $N: TestFlight upload of $(git log -1 --format=%h -- 3d-model/society-hill-towers.html)'s page"
if git remote | grep -qx gh-ssh; then git push -q gh-ssh HEAD 2>&1 | tail -1 || echo "note: push failed; the commit is local" >&2; fi
rm -rf "$WORK"
echo "uploaded: build $N is processing on TestFlight (about 15 minutes before testers can install it)"
[ -f "$CFG" ] && python3 "$ROOT/app/scripts/asc.py" status 2>/dev/null | head -2 || true
