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
