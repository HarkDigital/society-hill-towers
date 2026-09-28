"""Round 163: the iOS app ready for TestFlight (the code side).

The Capacitor project in ../app: the app runs in landscape only (the page's rotate gate would face a portrait phone or a
small iPad), and so full screen on an iPad (App Store validation wants every orientation or UIRequiresFullScreen); export
compliance is answered in the plist (HTTPS only, exempt); the device requirement is arm64, not the template's armv7; the
app target ships its own privacy manifest (no tracking, the load beacon's performance and diagnostic data, not linked,
for app functionality; no required-reason APIs) and the project really copies it; the launch screen has no white frame;
the asset catalog holds no stray files; the geolocation plugin is installed and registered, so iOS asks once, and the
page takes the fix from it inside the app; the build number has a one-command bump."""
import json
from pathlib import Path
import plistlib
import re
import unittest

MODEL = Path(__file__).resolve().parents[1]
APP = MODEL.parent / 'app'
IOS = APP / 'ios' / 'App'


@unittest.skipUnless(APP.exists(), 'no app/ project')
class AppIos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = plistlib.loads((IOS / 'App' / 'Info.plist').read_bytes())
        cls.pbx = (IOS / 'App.xcodeproj' / 'project.pbxproj').read_text()

    def test_landscape_only_and_full_screen(self):
        land = ['UIInterfaceOrientationLandscapeLeft', 'UIInterfaceOrientationLandscapeRight']
        self.assertEqual(self.info['UISupportedInterfaceOrientations'], land)
        self.assertEqual(self.info['UISupportedInterfaceOrientations~ipad'], land)
        self.assertIs(self.info['UIRequiresFullScreen'], True)

    def test_export_compliance_device_and_location_string(self):
        self.assertIs(self.info['ITSAppUsesNonExemptEncryption'], False)
        self.assertEqual(self.info['UIRequiredDeviceCapabilities'], ['arm64'])
        self.assertIn('locate button', self.info['NSLocationWhenInUseUsageDescription'])
        # ITMS-90683 (build 1, Sep 28): ion-ios-geolocation compiles in a requestAlwaysAuthorization branch, so Apple's scan
        # wants the Always string too, though nothing calls it. The app still asks when in use only: the plugin requests
        # .whenInUse and nothing else, and there is no background location mode.
        self.assertIn('never uses your location in the background', self.info['NSLocationAlwaysAndWhenInUseUsageDescription'])
        self.assertNotIn('location', self.info.get('UIBackgroundModes', []))
        plug = APP / 'node_modules' / '@capacitor' / 'geolocation' / 'ios' / 'Sources' / 'GeolocationPlugin' / 'GeolocationPlugin.swift'
        if plug.exists():
            src = plug.read_text()
            self.assertIn('requestLocationAuthorisation(type: .whenInUse)', src)
            self.assertNotIn('type: .always', src)

    def test_the_privacy_manifest(self):
        pm = plistlib.loads((IOS / 'App' / 'PrivacyInfo.xcprivacy').read_bytes())
        self.assertIs(pm['NSPrivacyTracking'], False)
        self.assertEqual(pm['NSPrivacyTrackingDomains'], [])
        self.assertEqual(pm['NSPrivacyAccessedAPITypes'], [])
        kinds = {d['NSPrivacyCollectedDataType']: d for d in pm['NSPrivacyCollectedDataTypes']}
        self.assertEqual(set(kinds), {'NSPrivacyCollectedDataTypePerformanceData', 'NSPrivacyCollectedDataTypeOtherDiagnosticData'})
        for d in kinds.values():
            self.assertIs(d['NSPrivacyCollectedDataTypeLinked'], False)
            self.assertIs(d['NSPrivacyCollectedDataTypeTracking'], False)
            self.assertEqual(d['NSPrivacyCollectedDataTypePurposes'], ['NSPrivacyCollectedDataTypePurposeAppFunctionality'])
        # the target copies it: a file reference, a build file, and the build file in the Resources phase
        ref = re.search(r'(\w{24}) /\* PrivacyInfo\.xcprivacy \*/ = \{isa = PBXFileReference;', self.pbx).group(1)
        bf = re.search(r'(\w{24}) /\* PrivacyInfo\.xcprivacy in Resources \*/ = \{isa = PBXBuildFile; fileRef = ' + ref, self.pbx).group(1)
        res = re.search(r'/\* Resources \*/ = \{\s*isa = PBXResourcesBuildPhase;.*?files = \((.*?)\);', self.pbx, re.S).group(1)
        self.assertIn(bf, res)

    def test_signs_as_quincysoft(self):
        # Mike's team for every app (Sep 28): with it set, Xcode's automatic signing registers com.philly3d.app, which is
        # what App Store Connect's New App list needs before it offers the bundle id
        self.assertEqual(self.pbx.count('DEVELOPMENT_TEAM = 72U2ZL3GVM;'), 2)            # Debug and Release
        self.assertIn('DevelopmentTeam = 72U2ZL3GVM;', self.pbx)                          # the target attribute Xcode reads
        self.assertEqual(self.pbx.count('CODE_SIGN_STYLE = Automatic;'), 2)
        self.assertNotRegex(self.pbx, r'DEVELOPMENT_TEAM = (?!72U2ZL3GVM;)')

    def test_launch_screen_and_assets(self):
        sb = (IOS / 'App' / 'Base.lproj' / 'LaunchScreen.storyboard').read_text()
        self.assertNotIn('systemBackgroundColor', sb)                  # white in light mode: a flash before the dark city
        cat = IOS / 'App' / 'Assets.xcassets' / 'Splash.imageset'
        named = {i['filename'] for i in json.loads((cat / 'Contents.json').read_text())['images']}
        self.assertEqual(named, {p.name for p in cat.glob('*.png')})    # every image referenced, none stray

    def test_one_location_prompt(self):
        pkg = json.loads((APP / 'package.json').read_text())
        self.assertIn('@capacitor/geolocation', pkg['dependencies'])
        self.assertIn('bump', pkg['scripts'])
        self.assertIn('CapacitorGeolocation', (IOS / 'CapApp-SPM' / 'Package.swift').read_text())
        self.assertIn("include ':capacitor-geolocation'", (APP / 'android' / 'capacitor.settings.gradle').read_text())
        src = (MODEL / 'app.js').read_text()
        self.assertIn("const appGeo = () => { const C = IN_APP && window.Capacitor; return (C && C.Plugins && C.Plugins.Geolocation) || null; };", src)
        loc = src[src.index('  function locateMe() {'):src.index("  if (btnLocate) btnLocate.addEventListener('click', locateMe);")]
        self.assertLess(loc.index('const G = appGeo();'), loc.index('navigator.geolocation.getCurrentPosition'))   # the plugin first


if __name__ == '__main__':
    unittest.main()
