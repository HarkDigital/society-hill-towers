"""The realism round two, R9: the blade signs (Round 189's open item, "blade signs for the 796 on street floors").

A storefront on a generated street floor has no panel and so no board, and one under a generated shop front loses its board
and name within the fronts' radius. Each hangs a projecting blade sign: one of six generated blanks on one 512 square sheet
(blade_art.json, bake_blade_art.py; never lettered), the shop's OSM name lettered by the page, lit by its hours, the shapes
by trade with the neighbour's rule; ?blades=0 leaves them out. The blanks clear a house front's awning (bladeAwnNote, run
under Node here).
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.js').read_text()


def cut(start, end):
    a = APP.index(start)
    return APP[a:APP.index(end, a)]


SECTION = cut('  // ---- the blade signs (the realism round two, R9', "  step('Raising the overpasses'")


class Blades(unittest.TestCase):
    def test_the_flag_and_the_gates(self):
        # off with ?blades=0, and only where the storefronts' art is built (the realistic look, WebGL 2, ?sfart=0 not given)
        self.assertIn("const BL_ON = SF_ART_ON && typeof BLADE_ART !== 'undefined' && !!BLADE_ART && Array.isArray(BLADE_ART.shapes) && BLADE_ART.shapes.length === 6 && !/[?&]blades=0\\b/.test(location.search);", SECTION)
        self.assertIn('const SF_ART_ON = REAL && ', APP)
        # no tier, Graphics choice or pace gate: every phone tier that has the records draws them (Round 218's rule)
        self.assertEqual(re.findall(r'\b(TIER2?|LITE|tierAuto|GFX|PACE)\b', SECTION), [])
        # ?signs=0 leaves them blank, as it does the boards
        self.assertIn('const nm = SF_SIGNS ? names.push(r.name) - 1 : -1;', SECTION)

    def test_wired_into_the_storefronts_the_build_and_the_loop(self):
        build = cut('  function sfBuild(', '  // ---- the names (Round 189)')
        self.assertIn('{ baseN++; if (BL_ON) blWant.push({ i, cx, cz, nx, nz, w, out, fh, fp, hostH, fam, hrs, name, near: 0 }); continue; }', build)
        self.assertIn('if (BL_ON) { try { bladeBuild(blWant.concat(recs.filter((r) => r.near))); } catch (e) {', build)
        self.assertLess(build.index('try { sfNamesInit(); }'), build.index('bladeBuild('))
        self.assertIn('    if (BL_ON) bladeArtLoad();', cut('  async function build() {', '    let failures = 0;'))
        self.assertIn('    sfStep(now);   // Round 189: the storefronts\' clock and names\n    bladeStep(now);', APP)
        self.assertIn('if (BL.awn) bladeAwnNote(px + rx * s0, pz + rz * s0, rx, rz, s1 - s0, yA, nx, nz);', cut('  function frontsLay(', '  function updateFronts('))
        # the mesh is made outside the storefronts' block (its test counts two instanced meshes there)
        self.assertEqual(SECTION.count('new THREE.InstancedMesh('), 1)

    def test_the_hard_rules(self):
        # every instance stream Float32 (no 1- or 3-byte stream, Round 158), no depth written by hand, no lettering in the art
        self.assertNotIn('Uint8BufferAttribute', SECTION)
        self.assertNotIn('Int8Array(N', SECTION)
        for m in re.finditer(r'const at = \(k\) => new THREE\.InstancedBufferAttribute\(new (\w+)\(N \* k\), k\);', SECTION):
            self.assertEqual(m.group(1), 'Float32Array')
        self.assertNotIn('gl_FragDepth', SECTION)
        self.assertIn('mesh.castShadow = false;', SECTION)
        # the sheet goes up premultiplied, left linear, and the shader divides the coverage out and decodes the colour
        self.assertIn('t.premultiplyAlpha = true;', SECTION)
        self.assertNotIn('sRGBEncoding', SECTION)
        self.assertIn('blArt.rgb / max(blArt.a, 1e-3)', SECTION)
        self.assertIn('BL_U.uBlMap.value = freeTexOnUpload(t);', SECTION)

    def test_the_sheet(self):
        man = json.loads((ROOT / 'blade_art.json').read_text())
        self.assertEqual([s['id'] for s in man['shapes']], ['round', 'rect', 'hanging', 'box', 'vertical', 'oval'])
        self.assertEqual((man['w'], man['h']), (512, 512))
        for k in ('img', 'imgHalf'):
            self.assertTrue(man[k].startswith('art/blades/'), k)
            self.assertTrue((ROOT / man[k]).exists(), man[k])
        self.assertLess((ROOT / man['img']).stat().st_size + (ROOT / man['imgHalf']).stat().st_size, 200_000)
        for s in man['shapes']:
            u0, v0, du, dv = s['rect']
            self.assertTrue(0 <= u0 and u0 + du <= 1 and 0 <= v0 and v0 + dv <= 1, s['id'])
            x0, y0, x1, y1 = s['plate']
            self.assertTrue(0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1, s['id'])
            self.assertTrue(0.3 <= s['size'][0] <= 1.5 and 0.3 <= s['size'][1] <= 2.2, s['id'])
        self.assertEqual([s['vertical'] for s in man['shapes']].count(True), 1)
        self.assertEqual([s['lightbox'] for s in man['shapes']].count(True), 1)
        # the page reads it: build.py inlines the manifest and ships its files
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("BLADE_ART", text_of("blade_art.json", "null"))', b)
        self.assertIn('"blade_art.json"', b[b.index('ART_FILES = []'):b.index('ART_BYTES = ')])

    def test_every_trade_deals_all_six(self):
        pref = json.loads(re.search(r'const BL_PREF = (\[\[.*?\]\]);', SECTION, re.S).group(1))
        fams = json.loads((ROOT / 'storefront_art.json').read_text())['fams']
        self.assertEqual(len(pref), len(fams))
        for p in pref:
            self.assertEqual(sorted(p), [0, 1, 2, 3, 4, 5])

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_an_awning_raises_the_blade_over_it(self):
        fn = cut('  function bladeAwnNote(', '  // the names: the panels\' scheme')
        js = fn + (
            'const BL = { awn: { grid: new Map([["0:0", [0, 1, 2]]]), lift: { array: new Float32Array(3), needsUpdate: false },'
            ' x: Float32Array.from([2, 5, 2]), z: Float32Array.from([0.1, 0.05, 6]), y0: Float32Array.from([3.8, 3.8, 3.8]),'
            ' top: Float32Array.from([1e9, 5.0, 1e9]), h: Float32Array.from([0.8, 0.8, 0.8]), raised: 0, gone: 0 } };'
            # an awning along x from 0 to 6 m on the wall z = 0 (normal +z), its top at 4.3 m: the first blade rises 0.62 m,
            # the second has no room under its roof and goes, the third (6 m off the wall) is not on its line
            'bladeAwnNote(0, 0, 1, 0, 6, 4.3, 0, 1);'
            'const a = Array.from(BL.awn.lift.array).map((v) => +v.toFixed(3));'
            # laid again lower: nothing moves down
            'bladeAwnNote(0, 0, 1, 0, 6, 3.9, 0, 1);'
            'console.log(JSON.stringify([a, Array.from(BL.awn.lift.array).map((v) => +v.toFixed(3)), BL.awn.raised, BL.awn.gone, BL.awn.lift.needsUpdate]));')
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        first, again, raised, gone, flagged = json.loads(r.stdout)
        self.assertEqual(first, [0.62, -100, 0])
        self.assertEqual(again, first)
        self.assertEqual((raised, gone, flagged), (1, 1, True))


if __name__ == '__main__':
    unittest.main()
