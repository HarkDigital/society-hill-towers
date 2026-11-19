"""Round 256 (Stage 4, the ASTC art): the house fronts' GPU-ready twins (bake_astc.py, astc_art.json) and the page's
loader behind ?astc=h4|h8|f8. Every twin is the page's own container with a whole mip chain of the right block counts, of
the picture it stands for at the size it says; the loader is a phone's only, off unless asked for, and falls back to the
webp; the GPU byte table knows the two block sizes."""
import json
from pathlib import Path
import re
import struct
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MAN = json.loads((ROOT / 'astc_art.json').read_text())
FRONTS = json.loads((ROOT / 'fronts.json').read_text())


def read(rel):
    b = (ROOT / rel).read_bytes()
    assert b[:4] == b'P3DA', rel
    bw, bh, n, flags = b[4], b[5], b[6], b[7]
    w, h = struct.unpack('<II', b[8:16])
    o, levels = 16, []
    for _ in range(n):
        ln = struct.unpack('<I', b[o:o + 4])[0]
        o += 4
        levels.append(ln)
        o += ln
    return {'bw': bw, 'bh': bh, 'n': n, 'srgb': flags & 1, 'w': w, 'h': h, 'levels': levels, 'end': o, 'size': len(b)}


class Twins(unittest.TestCase):
    def test_every_front_set_has_its_four(self):
        self.assertEqual(set(MAN['fronts']), set(FRONTS['sets']))
        for name, rec in MAN['fronts'].items():
            self.assertEqual(set(rec), {'h4', 'm4'}, name)   # Round 257: Mike's pick, the half picture and mask at 4x4
            for k, rel in rec.items():
                self.assertRegex(rel, r'^art/astc-fronts/%s-%s\.[0-9a-f]{10}\.astc$' % (re.escape(name), k))

    def test_the_container_and_its_mips(self):
        src = {'h4': ('imgHalf', 4, 1), 'm4': ('maskHalf', 4, 0)}
        for name, rec in MAN['fronts'].items():
            S = FRONTS['sets'][name]
            for k, rel in rec.items():
                key, blk, srgb = src[k]
                t = read(rel)
                w, h = Image.open(ROOT / S[key]).size
                self.assertEqual((t['bw'], t['bh'], t['w'], t['h'], t['srgb']), (blk, blk, w, h, srgb), rel)
                self.assertEqual(t['end'], t['size'], rel + ': nothing after the last level')
                # GL's chain: each side halved (at least 1) down to 1 by 1, each level ceil(w/b) * ceil(h/b) blocks of 16 bytes
                lw, lh, want = w, h, []
                while True:
                    want.append(-(-lw // blk) * -(-lh // blk) * 16)
                    if lw == 1 and lh == 1:
                        break
                    lw, lh = max(1, lw // 2), max(1, lh // 2)
                self.assertEqual(t['levels'], want, rel)

    def test_the_bytes_a_texture_holds(self):
        # a half front set, picture and mask, against today's RGBA8 with mips (the plan's 7.5 MiB)
        S = FRONTS['sets']['federal']
        r = MAN['fronts']['federal']
        rgba = sum(Image.open(ROOT / S[k]).size[0] * Image.open(ROOT / S[k]).size[1] * 4 * 4 / 3 for k in ('imgHalf', 'maskHalf'))
        gpu = lambda *ks: sum(sum(read(r[k])['levels']) for k in ks)
        self.assertAlmostEqual(gpu('h4', 'm4') / rgba, 0.25, delta=0.01)


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / 'app.js').read_text()

    def test_the_app_by_default_a_phone_only(self):
        s = self.src
        # Round 257 (Mike's pick, "4x4, half size"): on in the app, a website phone only with ?astc=1, ?astc=0 refuses
        self.assertIn("const ASTC_PICK = /[?&]astc=0\\b/.test(location.search) ? '' : IN_APP || /[?&]astc=(1|h4)\\b/.test(location.search) ? 'h4' : '';", s)
        on = s[s.index('  const astcOn = () => {'):s.index('  const ASTC = { loads')]
        self.assertIn("if (!ASTC_PICK || !isTouch || typeof ASTC_ART === 'undefined' || !ASTC_ART || !renderer.capabilities.isWebGL2) return false;", on)
        self.assertIn("getExtension('WEBGL_compressed_texture_astc')", on)

    def test_the_twin_fills_the_texture_in_place_and_lets_its_blocks_go(self):
        s = self.src
        i = s.index('  function artAstc(src, tex) {')
        body = s[i:s.index('\n  }\n', i)]
        for t in ('tex.isCompressedTexture = true;', 'tex.flipY = false; tex.generateMipmaps = false;',
                  'THREE.RGBA_ASTC_4x4_Format : THREE.RGBA_ASTC_8x8_Format', 'u8[7] & 1 ? THREE.sRGBEncoding : THREE.LinearEncoding'):
            self.assertIn(t, body)
        self.assertIn("if (tex.isCompressedTexture) { tex.mipmaps = []; return; }", s)
        # the fronts take the twin when there is one and the webp otherwise, or when the twin does not come
        self.assertIn('Promise.all(AS ? [loadA(AS[ASTC_PICK], map, S.img, S.imgHalf), loadA(AS.m4, mask, S.mask, S.maskHalf)] : [load(S.img, S.imgHalf, map), load(S.mask, S.maskHalf, mask)])', s)

    def test_the_run_beacons_say_how_many_came(self):
        self.assertIn("if (as) o.as = as; }   // Round 257", self.src)
        b = (ROOT.parent / '.claude' / 'skills' / 'philly3d-capture' / 'scripts' / 'beacons.py').read_text()
        self.assertRegex(b, r"RUN2 = \([^)]*'as'\)")

    def test_the_byte_table_knows_the_blocks(self):
        self.assertIn('0x93B0: 1, 0x93D0: 1, 0x93B7: 0.25, 0x93D7: 0.25 };', self.src)

    def test_the_build_inlines_and_guards_the_manifest(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("ASTC_ART", text_of("astc_art.json", "null"))', b)
        self.assertIn('"astc_art.json"):', b)


if __name__ == '__main__':
    unittest.main()
