"""Round 185 (Mike: "How can we make this entire model look more photo realistic ... It still looks very much like
minecraft, or a kid's game"): the realistic look, step 1. On the desktop post pipeline, ambient occlusion from the
city's own depth (copied at the pins' depth wipe, before it is cleared) and a filmic grade in the composite; on every
device a quieter lawn and a warm bounce by night. ?real=0 is the old palette, ?ao=0 the look without the occlusion,
?ao=show the occlusion alone."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent


class Realism(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = (ROOT / 'app.js').read_text()

    def test_the_switches(self):
        s = self.s
        self.assertIn("const REAL = !/[?&]real=0\\b/.test(location.search);", s)
        self.assertIn("const AO = { on: REAL && POST.on && !/[?&]ao=0\\b/.test(location.search),", s)
        self.assertIn("uAOShow: { value: /[?&]ao=show\\b/.test(location.search) ? 1 : 0 }", s)

    def test_the_depth_is_copied_before_the_pins_clear_it(self):
        s = self.s
        self.assertIn("pinDepthClear.onBeforeRender = (r) => { aoCopyDepth(r); r.state.buffers.depth.setMask(true); r.clearDepth(); };", s)
        a = s.index('  function aoCopyDepth(r) {')
        f = s[a:s.index('\n  }\n', a)]
        self.assertIn('r.getRenderTarget() !== postRT', f)        # never a pin capture's or the light map's pass
        self.assertIn('gl.DEPTH_BUFFER_BIT, gl.NEAREST', f)
        self.assertIn('gl.bindFramebuffer(gl.FRAMEBUFFER, src);', f)   # three's own binding back
        # the copy's format is the scene target's renderbuffer's (DEPTH24_STENCIL8), or the blit fails
        self.assertIn('new THREE.DepthTexture(w, h, THREE.UnsignedInt248Type); dt.format = THREE.DepthStencilFormat;', s)

    def test_the_occlusion_reads_whole_texels(self):
        # a half-res pixel's centre sits on the line between two depth texels; unsnapped, its neighbours were the same
        # texel on alternate rows and every flat banded
        self.assertIn("'  vec2 tx = 1.0 / uRes, uv0 = (floor(vUv * uRes) + 0.5) * tx;',", self.s)
        self.assertIn("pow(uFar + 1.0, d) - 1.0", self.s)   # r149's log depth, linearised

    def test_lights_keep_their_light(self):
        self.assertIn("float hot = smoothstep(0.9, 2.5, max(c.r, max(c.g, c.b))); c *= mix(mix(1.0, ao, uAOK), 1.0, max(hot, core));", self.s)

    def test_every_device(self):
        s = self.s
        self.assertIn("grass, ' + (REAL ? '0.70' : '0.88') + ');'", s)
        self.assertIn("if (REAL) { hemi.color.lerp(_c2.set(0x3a3240), 0.5 * night); hemi.groundColor.lerp(_c2.set(0x3a2814), 0.7 * night); }", s)


if __name__ == '__main__':
    unittest.main()
