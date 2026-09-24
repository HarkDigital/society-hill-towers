# Philly3D app (Capacitor)

The iOS and Android apps are a Capacitor 8 wrapper around the same single page the site serves. Nothing here changes the
page: `npm run sync` copies `../3d-model/society-hill-towers.html` (built by `python3 build.py`) into `www/index.html`
and from there into both native projects. The page's build stays plain Python with no npm; npm lives only in this folder.

## What the page does differently inside the app (Round 155, `IN_APP` in app.js)

- Detects the app by the `Philly3DApp` user-agent marker (`appendUserAgent` in `capacitor.config.json`), by the
  `capacitor://` scheme on iOS, or by `https://localhost` on Android.
- Always builds the phone city (an iPad with a trackpad would otherwise build the desktop one).
- Reads every live feed from `https://philly3d.com` (the server allows the app's origins since Round 155), shares
  `https://philly3d.com/` links, runs ships from the relay only, sends its load beacons to philly3d.com, and registers
  no service worker.
- Hides the screenshot button where the web view has no share sheet (Android's).
- Recovers from memory trouble: a lost WebGL context reloads the page (lite only for a loss in front), and a kill during
  use leaves a breadcrumb so the next load builds the lighter city.

## What the native projects add

- **iOS** reloads the page by itself when the system kills the web content process (Capacitor's
  `WebViewDelegationHandler.webViewWebContentProcessDidTerminate` calls `webView.reload()`). Links to other sites and
  `window.open` open in Safari (Capacitor's navigation policy and `createWebViewWith`). `NSLocationWhenInUseUsageDescription`
  is in `ios/App/App/Info.plist` for the locate button.
- **Android**: Capacitor's default answer to a killed renderer is to crash the app, so
  `android/app/src/main/java/com/philly3d/app/MainActivity.java` answers true and recreates the activity with a fresh
  WebView. Outside links go to the browser through Capacitor's `launchIntent`. The manifest declares coarse and fine
  location (Capacitor's WebChromeClient asks for both at run time; the person may grant approximate only).
- Icons and splash screens from the brand mark: `python3 scripts/make-assets.py` draws `assets/`, then
  `npx @capacitor/assets generate --iconBackgroundColor '#171512' --splashBackgroundColor '#171512'`.

## Building

You need, on this Mac:

1. **Xcode** from the App Store (the command-line tools alone cannot build an app), opened once to install its
   components, then `sudo xcode-select -s /Applications/Xcode.app`.
2. **Android Studio** (it brings its own JDK and the Android SDK).
3. An **Apple Developer Program** membership for signing and TestFlight, and a **Google Play Console** account.

Then, after every page build:

```bash
cd app
npm run sync
npm run open:ios        # Xcode: pick your team under Signing & Capabilities, then Run on a phone or Archive
npm run open:android    # Android Studio: Run on a phone, or Build > Generate Signed App Bundle
```

The app id is `com.philly3d.app` (`capacitor.config.json`); change it before the first store upload if you want a
different one, since it cannot change afterwards.

## Test on a real phone before submitting

Chrome's phone emulation does not reproduce WebKit's memory accounting. Run the app on an older iPhone and a mid-range
Android phone: first load, flying around for a few minutes, background and foreground, the locate button, an outside
link, sharing a view. In Safari's Develop menu (iOS) and chrome://inspect (Android) you can watch the page's memory and
console while it runs.

## Before submitting (from the Round 156 research: 14 agents, each answer checked against its primary source)

- **Privacy policy URL**: both stores require one, and Apple wants it reachable inside the app (5.1.1(i)). A draft is
  `3d-model/privacy.html`; once approved it goes to https://philly3d.com/privacy.html and gets a link in the About panel.
- **App Privacy labels (Apple) and Data safety (Google)**: location is used only on the device and is not "collected".
  The load beacon keeps performance data, so declare Diagnostics: Performance Data, not linked to the user (or turn the
  beacon off inside the app). No tracking, no identifiers. Capacitor 8.5.2 ships its own PrivacyInfo.xcprivacy with no
  required-reason APIs, and the page's localStorage is not a required-reason API.
- **Guideline 4.2 (minimum functionality)**: Apple rejects "a repackaged website". The page is bundled, not loaded from
  the web, and is an interactive 3D city with live data, which is the kind of app-like content 4.2 asks for; say so in
  the review notes and include a short screen recording.
- **Location on iOS** asks twice: iOS's own prompt, then WebKit's per-site prompt naming "localhost", which may return on
  later launches. The @capacitor/geolocation plugin avoids the second one; wire it into the locate button after the first
  device test if it proves annoying.
- **Downloads**: neither platform saves an `<a download>` in Capacitor, so the page shows its screenshot button in the
  app only where the share sheet takes an image file.
- **Google Play**: new apps must target API 36 from Aug 31, 2026 (the project does) and ship an App Bundle. A personal
  developer account created after Nov 13, 2023 must run a closed test with 12 testers for 14 days before production;
  registering as an organization is reported to avoid that (Google's page does not say either way).
- **Dropbox**: Xcode and Gradle may trip over this CloudStorage folder the way the dev server does. If the first build
  fails on paths, copy `app/` outside Dropbox (or clone the repo there) and build from that copy.
