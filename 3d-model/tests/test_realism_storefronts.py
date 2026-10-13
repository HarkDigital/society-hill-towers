"""Round 189 (Mike: "Do the storefront boxes on Broad Street too"): the page's generated shopfronts.

- the realistic look on WebGL 2 with the art (SF_ART_ON) builds the panels; ?real=0, ?sfart=0, WebGL 1 or art that does
  not arrive in 10 s build the old boxes exactly as before, inline in the step (their strings stand where they stood);
- the hooks are written at the top level, never in the step (a hook written in a build step keeps its whole scope);
- every stream the panels and their awnings upload is Float32 at a stride of 4, 8, 12 or 16 (a phone: Round 158);
- the names' atlas is red only, never freed on upload (its slots are written after it), and the step's slots stream stays;
- the sidecar is used only when its count is the blob's;
- the painted shop floors (style 5) take the same atlas in the facade hook behind SF_PARTA (REAL and WebGL 2) and uSfOn;
- build.py inlines the sidecar and the manifest and holds the manifest to the art guards."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def cut(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


class Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()
        cls.block = cut(cls.s, "  // ---- the storefronts' shopfronts (Round 189", "  step('Dressing the storefronts'")
        cls.step = cut(cls.s, "  step('Dressing the storefronts'", "  step('Raising the overpasses'")

    def test_the_gates(self):
        self.assertIn("const SF_ART_ON = REAL && !!renderer.capabilities.isWebGL2 && typeof STOREFRONT_ART !== 'undefined' && !!STOREFRONT_ART && !!STOREFRONT_ART.cells && !/[?&]sfart=0\\b/.test(location.search);", self.block)
        self.assertIn("const SF_SIGNS = SF_ART_ON && !TIER2 && !/[?&]signs=0\\b/.test(location.search);", self.block)
        self.assertIn("const SF_PARTA = REAL && !!renderer.capabilities.isWebGL2 && typeof STOREFRONT_ART !== 'undefined'", self.s)

    def test_the_old_boxes_stay_as_they_were(self):
        st = self.step
        new = st.index('if (SF_ART_ON) {')
        old = st.index('    let nearN = 0, baseN = 0;\n    for (let i = 0; i < n; i++) {')
        self.assertLess(new, old)
        legacy = st[old:]
        for line in ("parts.push({ geom: mk(w - 0.2, glassH + 0.5, 0.10, 0.12, gy + 0.25 + (glassH + 0.5) / 2, 0), color: cFrame, style: 3, near });",
                     "if (flags & 1) parts.push({ geom: mk(w - 0.5, 0.12, 1.1, 0.62, gy + fh + 0.05, -0.32), color: AWNING[col], style: 3, near });",
                     "'#include <emissivemap_fragment>\\ntotalEmissiveRadiance += vLit * uNight * 2.2;'",
                     'STOREFRONT_N = made; STOREFRONT_NEAR = nearN; STOREFRONT_BASE = baseN;'):
            self.assertIn(line, legacy)
        # the new path returns only when it built; art late or failed falls through to the boxes
        newp = st[new:old]
        self.assertIn("await Promise.race([sfArtLoad(), new Promise((r) => setTimeout(() => r(null), 10000))]);", newp)
        self.assertIn("if (built) { SF.state = 'built'; STOREFRONT_N = SF.n; STOREFRONT_NEAR = SF.near; STOREFRONT_BASE = SF.base; return; }", newp)
        self.assertNotIn('onBeforeCompile', newp)
        self.assertNotIn('aFrontNear', self.block)

    def test_the_hooks_live_at_the_top(self):
        for name in ('sfPanelHook', 'sfAwningHook', 'sfPanelMat', 'sfAwningMat', 'sfBuild', 'sfNamesInit', 'sfStep'):
            self.assertIn('  function ' + name + '(', self.block)
            self.assertNotIn('function ' + name + '(', self.step)
        self.assertIn("m.customProgramCacheKey = () => rich ? 'storefront-panels|wx' : 'storefront-panels|wx|lite';", self.block)
        # the panel's dissolve is the fronts' own dither line on the instance's near flag
        self.assertIn('if (ign <= 1.0 - smoothstep(uFrR * 0.8, uFrR, fd)) discard; }', self.block)
        self.assertIn("lampLightPatch(sh, 'vSfW', 'wall');\n    wxSurfacePatch(sh);", self.block)
        # every read is textureGrad, from gradients taken in uniform flow at the top of main
        self.assertIn("'sfDx = dFdx(vSfP.xy); sfDy = dFdy(vSfP.xy);',", self.block)
        self.assertNotIn('texture2D(uSf', self.block)

    def test_every_stream_is_four_byte_aligned(self):
        b = self.block
        self.assertFalse(re.search(r'new (Uint8|Int8|Uint16|Int16)Array\([^)]*\)\s*,\s*\d', b))
        for m in re.finditer(r'new THREE\.(Float32BufferAttribute|InstancedBufferAttribute|BufferAttribute)\(([^;]*)', b):
            args = m.group(2)
            if m.group(1) != 'Float32BufferAttribute':
                self.assertIn('Float32Array', args, args)
            if args.startswith('new Float32Array(N * k), k)'):
                continue   # the helper below, called with 4 and 1
            k = re.search(r',\s*(\d)\)', args)
            self.assertTrue(k and int(k.group(1)) in (1, 2, 3, 4), args)
        self.assertIn('const at = (k) => new THREE.InstancedBufferAttribute(new Float32Array(N * k), k);', b)
        self.assertIn('const aCell = at(4), aBand = at(4), aDim = at(4), aInfo = at(4), aHours = at(4), aSlot = at(1);', b)
        self.assertNotIn('setColorAt', cut(self.s, '  function sfPanelGeometry(', '  function sfAwningHook('))

    def test_the_names(self):
        b = self.block
        init = cut(self.s, '  function sfNamesInit(', '  function sfNamesRedraw(')
        self.assertIn('tex.format = THREE.RedFormat;', init)
        self.assertNotIn('freeTexOnUpload', init)
        self.assertIn('renderer.initTexture(tex)', init)
        self.assertIn('renderer.copyTextureToTexture(_sfPos.set(col * S.SW, (S.rows - 1 - row) * S.SH), S.cell.tex, S.tex);', b)
        build = cut(self.s, '  function sfBuild(', '  function sfNamesInit(')
        self.assertNotIn('freeOnUpload(geo)', build)   # aSfSlot is rewritten by the names
        self.assertIn('for (const a of [aCell, aBand, aDim, aInfo, aHours]) { a.onUpload(dropUploadedArray); }', build)
        self.assertIn("aSlot.setUsage(THREE.DynamicDrawUsage);", build)
        self.assertIn('sfStep(now);   // Round 189', self.s)

    def test_the_sidecar_is_checked(self):
        f = cut(self.s, '  function sfInfo(', '  function sfBuild(')
        self.assertIn('if (!I || I.n !== n || !I.rec) return null;', f)
        self.assertIn('return rec.length === n * 8 ?', f)

    def test_the_painted_shop_floors(self):
        s = self.s
        self.assertIn("if (SF_PARTA) Object.assign(shader.uniforms, sfPartU);", s)
        self.assertIn("'      if (st == 5 && uSfOn > 0.5 && local && wallTop >= 3.4 && det > 0.001) {',", s)
        self.assertIn("SF_PARTA ? '      awnOn *= 1.0 - sfWall;' : '',", s)
        # the paint stands where the art does not: the painted shop and awning strings are as they were
        self.assertIn("'      float shop = rectM(m, vec2(0.0, 1.7), vec2(1.5, 2.5), aa) * isShop;',", s)
        self.assertIn("'      float awnOn = step(3.72, wallTop) * float(st == 5) * inWall * det * step(fv, 4.0);',", s)
        self.assertIn("if (SF_PARTA) { sfPartU.uSfArt.value = map; sfPartU.uSfMaskA.value = mask; sfPartU.uSfOn.value = 1; SF.partA = true; }", self.step)

    def test_the_build(self):
        b = (ROOT / 'build.py').read_text()
        self.assertIn('const("STOREFRONT_INFO", text_of("storefront_info.json", "null"))', b)
        self.assertIn('const("STOREFRONT_ART", text_of("storefront_art.json", "null"))', b)
        self.assertRegex(b, r'for name in \([^)]*"storefront_art\.json"\):')

    def test_no_dash_in_what_shows(self):
        b = self.block
        for c in ('—', '·'):
            self.assertNotIn(c, b)


if __name__ == '__main__':
    unittest.main()
