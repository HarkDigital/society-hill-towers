"""JavaScript syntax check of app.js through JavaScriptCore (osascript -l JavaScript):
the source is parsed with `new Function(src)` and never executed. Skips when
osascript is unavailable (non-macOS hosts)."""
import json
import shutil
import subprocess
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_js
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

JXA = '''ObjC.import("Foundation");
var p = %s;
var s = $.NSString.stringWithContentsOfFileEncodingError($.NSString.alloc.initWithUTF8String(p), 4, null);
if (s.isNil()) { "READFAIL " + p; }
else { var src = s.js; try { new Function(src); "OK " + src.length; } catch (e) { "SYNTAX " + e.name + ": " + e.message; } }'''


def jsc_parse(path):
    """-> (status, detail): status 'OK' / 'SYNTAX' / 'READFAIL' / 'UNAVAILABLE'."""
    if shutil.which('osascript') is None:
        return 'UNAVAILABLE', 'osascript not on PATH'
    try:
        r = subprocess.run(['osascript', '-l', 'JavaScript', '-e', JXA % json.dumps(str(path))],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 'UNAVAILABLE', str(e)
    out = (r.stdout or '').strip()
    if r.returncode != 0 and not out:
        return 'UNAVAILABLE', (r.stderr or '').strip()[:300]
    status, _, detail = out.partition(' ')
    return status, detail


class AppJsSyntax(unittest.TestCase):

    def test_app_js_parses(self):
        C.require(self, 'app.js')
        status, detail = jsc_parse(C.path('app.js'))
        if status == 'UNAVAILABLE':
            self.skipTest('JavaScriptCore via osascript unavailable: ' + detail)
        self.assertNotEqual('READFAIL', status, 'JXA could not read app.js: ' + detail)
        self.assertEqual('OK', status, 'app.js does not parse: ' + detail)
        self.assertGreater(int(detail), 100000, 'app.js read back suspiciously short (%s chars)' % detail)

    def test_app_js_has_no_script_terminator(self):
        """build.py inlines app.js into a <script> tag, so a literal '</script' would end the page early."""
        C.require(self, 'app.js')
        src = C.path('app.js').read_text(encoding='utf-8')
        self.assertNotIn('</script', src.lower())


if __name__ == '__main__':
    unittest.main()
