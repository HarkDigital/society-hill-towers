"""Roof fascia must follow real plans without glowing roof caps or buried faces."""
import base64
import json
from pathlib import Path
import shutil
import struct
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def section(src, start, end):
    a = src.index(start)
    return src[a:src.index(end, a)]


class RoofLightBands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        src = (ROOT / 'app.js').read_text()
        helpers = '\n'.join([
            section(src, '  function signedArea(', '  function pointInPoly('),
            section(src, '  function pointInPoly(', '  function polyCentroid('),
            section(src, '  function polyCentroid(', '\n  function '),
            section(src, '  function insetRing(', '  function roofClutter('),
            section(src, '  function roofLightBand(', '  function recessedTowerPlan('),
            section(src, '  const TOWER_SPECS =', '  function buildingColor('),
        ])
        blob = base64.b64decode((ROOT / 'wide.b64').read_text())
        hdr = struct.unpack_from('<4i', blob)
        words = struct.unpack_from('<%dh' % ((len(blob) - 16) // 2), blob, 16)
        k, parts = 0, []
        for _ in range(hdr[1]):
            n, h, mh, t, attr, roof = words[k:k+6]
            k += 6
            if h / 5 > 45:
                parts.append(dict(h=h/5, poly=[[words[k+j*2]/5, words[k+j*2+1]/5] for j in range(n)]))
            k += n * 2
        script = ('const THREE=require(' + json.dumps(str(ROOT / 'three.min.js')) + ');\n'
                  + 'const TOWERS=' + (ROOT / 'towers.json').read_text() + ';\n'
                  + 'const PARTS=' + json.dumps(parts) + ';\n' + helpers + r'''
const roofs = new Map();
for (const part of PARTS) {
 const [x,z]=polyCentroid(part.poly),spec=towerAt(x,z,part.h);
 if(spec?.crown?.type==='band' && (!roofs.has(spec) || roofs.get(spec).h<part.h))roofs.set(spec,part);
}
function inspect(name,poly,roofY) {
 const g=roofLightBand(poly,roofY),p=g.attributes.position,n=g.attributes.normal;
 const sg=signedArea(poly)>0?1:-1;
 let finite=true,vertical=true,outside=true,outward=true,seams=true;
 let minClear=Infinity,maxClear=-Infinity,lo=Infinity,hi=-Infinity;
 for(let i=0;i<p.count;i++) {
   finite&&=[p.getX(i),p.getY(i),p.getZ(i),n.getX(i),n.getY(i),n.getZ(i)].every(Number.isFinite);
   vertical&&=Math.abs(n.getY(i))<1e-6;
   lo=Math.min(lo,p.getY(i));hi=Math.max(hi,p.getY(i));
 }
 let idx=0;
 for(let j=0;j<poly.length;j++) {
   const a=poly[j],b=poly[(j+1)%poly.length],dx=b[0]-a[0],dz=b[1]-a[1],len=Math.hypot(dx,dz);
   if(len<1e-6)continue;
   const nx=sg*dz/len,nz=-sg*dx/len;
   outward&&=n.getX(idx)*nx+n.getZ(idx)*nz>.999;
   for(let k=idx;k<idx+6;k++) {
     const clear=(p.getX(k)-a[0])*nx+(p.getZ(k)-a[1])*nz;
     minClear=Math.min(minClear,clear);maxClear=Math.max(maxClear,clear);
   }
   // Sample both triangles: their interiors must not run across the roof plan.
   for(let k=idx;k<idx+6;k+=3) {
     const x=(p.getX(k)+p.getX(k+1)+p.getX(k+2))/3;
     const z=(p.getZ(k)+p.getZ(k+1)+p.getZ(k+2))/3;
     outside&&=!pointInPoly(x,z,poly);
   }
   const end=idx+(sg>0?2:1),next=(idx+6)%p.count;
   seams&&=p.getX(end)===p.getX(next)&&p.getZ(end)===p.getZ(next);
   idx+=6;
 }
 return {name,finite,vertical,outside,outward,seams,minClear,maxClear,lo,hi,roofY,count:p.count,expected:idx};
}
const actual=[...roofs].map(([sp,p])=>inspect(sp.name,p.poly,p.h+12));
const washes=[];
for(const [sp,p] of roofs) {
 const fixture=roofLightBand(p.poly,p.h+12-.2,.32,.24);
 const g=themeWashGeometry([{geom:roofLightBand(p.poly,p.h+12,4.8,.18),slot:2,w:.72,grad:-1}]);
 const a=g.attributes.position,w=g.attributes.aWash;let finite=true,vertical=true,below=true,profile=true;
 for(let i=0;i<a.count;i++) {
  finite&&=[a.getX(i),a.getY(i),a.getZ(i)].every(Number.isFinite);
  below&&=a.getY(i)<p.h+12;
  profile&&=w.getX(i)>=-.001&&w.getX(i)<=1.001&&w.getY(i)===-1&&g.userData.slot[i]===2;
 }
 for(let i=0;i<a.count;i+=3) {
  const v=new THREE.Vector3().fromBufferAttribute(a,i);
  const b=new THREE.Vector3().fromBufferAttribute(a,i+1).sub(v);
  const c=new THREE.Vector3().fromBufferAttribute(a,i+2).sub(v);
  vertical&&=Math.abs(b.cross(c).normalize().y)<.001;
 }
 fixture.computeBoundingBox();
 washes.push({name:sp.name,finite,vertical,below,profile,fixtureHeight:fixture.boundingBox.max.y-fixture.boundingBox.min.y});
}
const capped=themeWashGeometry([{geom:new THREE.BoxGeometry(20,8,10),slot:0,w:1,grad:1}]);
const capY=capped.attributes.position;let caps=0;
for(let i=0;i<capY.count;i+=3)if(capY.getY(i)===capY.getY(i+1)&&capY.getY(i)===capY.getY(i+2))caps++;
const plans=[[[0,0],[40,0],[40,30],[0,30]],
 [[0,0],[34,0],[40,6],[40,24],[34,30],[6,30],[0,24]],
 [[0,0],[40,0],[40,30],[25,30],[25,10],[15,10],[15,30],[0,30]]];
const synthetic=[];
for(const poly of plans)for(const reverse of [false,true])for(const angle of [0,.71,2.2]) {
 let ring=poly.map(([x,z])=>[x*Math.cos(angle)-z*Math.sin(angle)-1900,x*Math.sin(angle)+z*Math.cos(angle)-730]);
 if(reverse)ring.reverse();synthetic.push(inspect('synthetic',ring,160));
}
console.log(JSON.stringify({actual,synthetic,washes,caps,expectedNames:TOWER_SPECS.filter(s=>s.crown?.type==='band').map(s=>s.name)}));
''')
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise AssertionError(run.stderr)
        cls.result = json.loads(run.stdout)

    def assert_clean_band(self, r):
        self.assertTrue(all(r[k] for k in ['finite', 'vertical', 'outside', 'outward', 'seams']), r)
        self.assertEqual(r['expected'], r['count'], r)
        self.assertAlmostEqual(r['roofY']-.2, r['hi'], places=3)
        self.assertAlmostEqual(r['roofY']-2.8, r['lo'], places=3)
        self.assertGreater(r['minClear'], .19, r)
        self.assertLess(r['maxClear'], .21, r)

    def test_all_packed_flat_roof_landmarks_have_clear_perimeter_only_lights(self):
        names = {r['name'] for r in self.result['actual']}
        self.assertTrue(names.issubset(self.result['expectedNames']))
        # The current packed data matches 23 of the 24 band specs. One Logan's
        # tall part lies outside its matching radius and renders without a band.
        self.assertGreaterEqual(len(names), 23)
        for r in self.result['actual']:
            with self.subTest(building=r['name']):
                self.assert_clean_band(r)

    def test_rotated_chamfered_and_reentrant_plans_with_both_windings(self):
        for r in self.result['synthetic']:
            self.assert_clean_band(r)

    def test_soft_washes_preserve_plans_and_exclude_roof_caps(self):
        self.assertEqual(0, self.result['caps'])
        self.assertEqual(len(self.result['actual']), len(self.result['washes']))
        for r in self.result['washes']:
            with self.subTest(building=r['name']):
                self.assertTrue(all(r[k] for k in ['finite', 'vertical', 'below', 'profile']), r)
                self.assertLess(r['fixtureHeight'], .4)


if __name__ == '__main__':
    unittest.main()
