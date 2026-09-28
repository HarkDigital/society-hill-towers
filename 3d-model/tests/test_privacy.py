"""Round 164: the privacy policy, published and linked, and Google Analytics kept to the website.

Mike: "publish the privacy policy and link it from About. I am going to be adding google analytics and google search
console." privacy.html is served at https://philly3d.com/privacy.html (deploy_philly3d.sh ships it and checks the live
copy), the About panel links it (Apple wants the policy reachable inside the app), and it describes Google Analytics as the
website's only (the apps' privacy manifest and App Store labels declare no analytics). The one Google Analytics loader is
app.js's, behind ON_SITE (philly3d.com and never the app), with Google's advertising features off, as the policy says."""
import html
from pathlib import Path
import plistlib
import re
import unittest

MODEL = Path(__file__).resolve().parents[1]


def text_of(page):
    t = re.sub(r'<style.*?</style>', '', page, flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>', ' ', t))


class Privacy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = (MODEL / 'privacy.html').read_text()
        cls.app = (MODEL / 'app.js').read_text()
        cls.tpl = (MODEL / 'template.html').read_text()

    def test_the_policy_says_what_the_site_and_apps_do(self):
        t = text_of(self.policy)
        self.assertNotIn('—', t)
        self.assertNotIn('·', t)
        self.assertIn('Last updated', t)
        self.assertIn('Google Analytics (the website only)', t)
        self.assertIn('The Philly3D apps for iPhone, iPad and Android do not include Google Analytics.', t)
        self.assertIn('Google Search Console', t)
        self.assertIn('not used to show you ads', t)
        self.assertIn('privacy@philly3d.com', t)
        self.assertNotIn('No analytics services', t)          # the old promise, untrue once Analytics is on

    def test_about_links_it(self):
        self.assertRegex(self.tpl, r'<p id="aboutPrivacy"><a href="https://philly3d\.com/privacy\.html" target="_blank" rel="noopener">Privacy Policy</a>')
        about = self.tpl[self.tpl.index('<div id="about"'):]
        self.assertLess(about.index('id="aboutPrivacy"'), about.index('<div class="credits">'))

    def test_the_deploy_ships_and_checks_it(self):
        d = (MODEL / 'deploy_philly3d.sh').read_text()
        self.assertIn('cp privacy.html "$TMP/"', d)
        self.assertIn('"$TMP/privacy.html"', d)
        self.assertIn('the live privacy.html does not match this one', d)

    def test_analytics_only_on_the_site_without_ad_features(self):
        self.assertNotIn('googletagmanager', self.tpl)        # never a plain tag, which would run inside the app too
        self.assertEqual(self.app.count('googletagmanager.com/gtag/js'), 1)
        block = self.app[self.app.index("  const GA_ID = '"):]
        block = block[:block.index("  const beaconSeen")]
        self.assertIn('if (GA_ID && ON_SITE) {', block)
        self.assertIn("allow_google_signals: false, allow_ad_personalization_signals: false", block)
        self.assertIn("const ON_SITE = !IN_APP && /(^|\\.)philly3d\\.com$/.test(location.hostname);", self.app)
        # the app declares no analytics data, which is why the loader must never run there
        pm = MODEL.parent / 'app' / 'ios' / 'App' / 'App' / 'PrivacyInfo.xcprivacy'
        if pm.exists():
            kinds = {d['NSPrivacyCollectedDataType'] for d in plistlib.loads(pm.read_bytes())['NSPrivacyCollectedDataTypes']}
            self.assertNotIn('NSPrivacyCollectedDataTypeProductInteraction', kinds)


if __name__ == '__main__':
    unittest.main()
