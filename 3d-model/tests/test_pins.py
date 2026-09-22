"""Floating pin rendering and selection share one annotation policy."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Pins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node.js unavailable')
        cls.source = (ROOT / 'app.js').read_text()
        helpers = cls.source[cls.source.index('  const PIN_ANCHOR_GLSL'):cls.source.index('  function pinMesh(')]
        script = r'''
const THREE=require(THREE_PATH),clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
HELPERS
const result={};
const wall=new THREE.Mesh(new THREE.BoxGeometry(8,8,8),new THREE.MeshBasicMaterial());
const badge=pinSceneDepth(new THREE.InstancedMesh(new THREE.PlaneGeometry(4,5),new THREE.MeshBasicMaterial(),2));
const line=pinSceneDepth(new THREE.Line(new THREE.BufferGeometry(),new THREE.LineBasicMaterial()));
const ball=pinSceneDepth(new THREE.Mesh(new THREE.SphereGeometry(),new THREE.MeshBasicMaterial()));
result.render=[badge,line,ball].map(m=>({depthTest:m.material.depthTest,depthWrite:m.material.depthWrite,transparent:m.material.transparent,order:m.renderOrder,alphaTest:m.material.alphaTest}));
// Round 126: a flat pin carries its anchor's depth in the vertex shader, chained after any shader hook the material already had (Indego's atlas remap)
const chained=new THREE.MeshBasicMaterial();let prevRan=false;chained.onBeforeCompile=(sh)=>{prevRan=true;sh.vertexShader=sh.vertexShader.replace('#include <uv_vertex>','vUv = uv;');};
pinSceneDepth(new THREE.InstancedMesh(new THREE.PlaneGeometry(),chained,1));
const sh={vertexShader:'#include <uv_vertex>\n#include <project_vertex>\n#include <logdepthbuf_vertex>\n',fragmentShader:''};chained.onBeforeCompile(sh,null);
const sh2={vertexShader:'#include <logdepthbuf_vertex>\n',fragmentShader:''};badge.material.onBeforeCompile(sh2,null);
result.anchor={prevRan,keepsPrev:sh.vertexShader.includes('vUv = uv;'),anchorLog:sh.vertexShader.includes('vFragDepth = 1.0 + pinA.w'),anchorPlain:sh.vertexShader.includes('gl_Position.z = pinA.z / pinA.w * gl_Position.w'),instanced:sh.vertexShader.includes('instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0)'),badgeToo:sh2.vertexShader.includes('pinA'),keyDiffers:chained.customProgramCacheKey()!==badge.material.customProgramCacheKey(),lineHook:(()=>{const s3={vertexShader:'#include <logdepthbuf_vertex>\n',fragmentShader:''};line.material.onBeforeCompile(s3,null);return s3.vertexShader;})()};
result.wall={depthTest:wall.material.depthTest,depthWrite:wall.material.depthWrite,transparent:wall.material.transparent};
const point=new THREE.Vector3(0,0,-10);
const hit=(object,id=0,distance=10)=>({object,instanceId:id,distance,point,uv:new THREE.Vector2(.5,.5)});
const solid=hit(wall),icon=hit(badge,0,20);
result.hiddenPin=pickSceneHit([solid,icon],()=>true)===null;
result.visiblePin=pickSceneHit([solid,icon],()=>false)===icon;
result.hiddenSolid=pickSceneHit([solid],()=>true)===null;
result.visibleSolid=pickSceneHit([solid],()=>false)===solid;
let alpha=0,lastPixel;
const image={width:256,height:320,getContext:()=>({getImageData:(x,y)=>{lastPixel=[x,y];return {data:[255,255,255,alpha]};}})};
badge.material.map=new THREE.CanvasTexture(image);
result.clearCorner=pickSceneHit([icon,solid],()=>false)===solid;
result.clearCornerBehindWall=pickSceneHit([icon,solid],()=>true)===null;
alpha=255;result.opaqueFace=pickSceneHit([icon,solid],()=>false)===icon;
const uv=new THREE.Vector2(.25,.75);pinHitOpaque({...icon,uv});
result.pixel=lastPixel;result.originalUV=uv.toArray();
image.width=4096;image.height=2048;
badge.geometry.setAttribute('aTile',new THREE.InstancedBufferAttribute(new Float32Array([2/32,1-4/16,7/32,1-10/16]),2));
pinHitOpaque({...icon,instanceId:1});result.indegoPixel=lastPixel;
const other=pinSceneDepth(new THREE.InstancedMesh(new THREE.PlaneGeometry(),new THREE.MeshBasicMaterial(),2));
const later=hit(other,0,100);
result.batchOrder=pickPinHit([icon,later],()=>false)===later;
const last=hit(other,1,200);result.instanceOrder=pickPinHit([last,later],()=>false)===last;
const hiddenLater={...later,point:new THREE.Vector3(1,0,-100)};
result.hiddenDoesNotSteal=pickSceneHit([icon,hiddenLater],x=>x===1)===icon;
icon.point=new THREE.Vector3(1,0,-20);
result.blockedPinFallsBack=pickSceneHit([icon,solid],x=>x===1)===solid;
console.log(JSON.stringify(result));
'''.replace('THREE_PATH', json.dumps(str(ROOT / 'three.min.js'))).replace('HELPERS', helpers)
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=20)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.result = json.loads(run.stdout)

    def test_badges_and_pin_connectors_respect_scene_depth(self):
        badge, line, ball = self.result['render']
        for material in (badge, line, ball):
            self.assertTrue(material['depthTest'])
            self.assertTrue(material['transparent'])
            self.assertGreater(material['order'], 60)
        # Round 126: a flat pin writes its anchor's depth so the pins sort among themselves, its
        # clear pixels kept out by alphaTest; the search tether stays a plain line that writes none
        for material in (badge, ball):
            self.assertTrue(material['depthWrite'])
            self.assertEqual(0.5, material['alphaTest'])
        self.assertFalse(line['depthWrite'])
        self.assertEqual(self.result['wall'], {'depthTest': True, 'depthWrite': True, 'transparent': False})

    def test_flat_pins_carry_their_anchor_depth(self):
        a = self.result['anchor']
        for key in ('prevRan', 'keepsPrev', 'anchorLog', 'anchorPlain', 'instanced', 'badgeToo', 'keyDiffers'):
            self.assertTrue(a[key], key)
        self.assertNotIn('pinA', a['lineHook'])   # the tether's default hook (three's no-op) leaves its shader alone

    def test_buildings_block_pins_and_hidden_pins_do_not_take_clicks(self):
        for key in ('hiddenPin', 'visiblePin', 'hiddenSolid', 'visibleSolid', 'hiddenDoesNotSteal', 'blockedPinFallsBack'):
            self.assertTrue(self.result[key], key)

    def test_transparent_texture_corners_do_not_steal_clicks(self):
        for key in ('clearCorner', 'clearCornerBehindWall', 'opaqueFace'):
            self.assertTrue(self.result[key], key)
        self.assertEqual(self.result['pixel'], [64, 80])
        self.assertEqual(self.result['originalUV'], [.25, .75])

    def test_indego_picking_uses_its_own_instance_atlas_tile(self):
        self.assertEqual(self.result['indegoPixel'], [960, 1216])

    def test_overlapping_pins_select_the_last_drawn_icon(self):
        self.assertTrue(self.result['batchOrder'] and self.result['instanceOrder'])

    def test_every_pin_family_uses_the_shared_policy(self):
        for anchor in ('pinSceneDepth(m);', 'pinSceneDepth(mesh);', 'pinSceneDepth(septaBadge);',
                       'pinSceneDepth(indegoBadge);', 'pinSceneDepth(pin);', 'pinSceneDepth(shipAnchor);',
                       'pinSceneDepth(amtrakPin);'):
            self.assertIn(anchor, self.source)
        self.assertEqual(self.source.count('pinSceneDepth(line);'), 2)  # scores + concerts
        self.assertEqual(self.source.count('pinSceneDepth(ball);'), 2)
        self.assertIn('const h = pickSceneHit(hits, pickOccluded);', self.source)


if __name__ == '__main__':
    unittest.main()
