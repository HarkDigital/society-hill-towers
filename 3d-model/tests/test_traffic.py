"""Production traffic lifecycle, routing and vehicle geometry regressions (Node/Three)."""
import base64
import struct
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TrafficTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('Node unavailable')
        run = subprocess.run(['node', str(ROOT/'tests/traffic_checks.js')], capture_output=True, text=True, timeout=60)
        if run.returncode:
            raise AssertionError(run.stderr or run.stdout)
        cls.results = json.loads(run.stdout)

    def test_bounded_pool_and_visible_continuity(self):
        r=self.results['simulation']
        self.assertLessEqual(r['maxPopulation'],r['cap'])
        self.assertEqual(0,r['visibleBirths'])
        self.assertEqual(0,r['visibleDeaths'])
        self.assertGreater(r['transfers'],5)
        self.assertEqual(r['actual'],r['tracked'])

    def test_junctions_link_interior_nodes_but_not_overpasses(self):
        self.assertEqual({'split':3,'links':6,'overpassLinks':0,'parallelLinks':0},self.results['graph'])

    def test_transfer_keeps_vehicle_identity_and_distance(self):
        r=self.results['transfer']
        self.assertTrue(r['sameCar'] and r['sameLook'])
        self.assertAlmostEqual(7,r['distance'])
        self.assertTrue(r['oneWayRefused'])

    def test_spawn_respects_headway(self):
        self.assertGreater(self.results['spacing']['count'],4)
        self.assertGreaterEqual(self.results['spacing']['minGap'],9.99)

    def test_empty_visible_street_gets_continuous_upstream_inflow(self):
        r=self.results['inflow']
        self.assertTrue(r['spawned'] and r['arrived'])
        self.assertGreater(r['seen'],10)
        self.assertEqual(0,r['visibleBirths'])
        self.assertEqual(0,r['visibleDeaths'])
        self.assertEqual(0,r['planned'])

    def test_baked_network_covers_outer_neighborhoods_and_keeps_connectors(self):
        data=base64.b64decode((ROOT/'traffic.b64').read_text())
        magic,ways,points,mm=struct.unpack_from('<4i',data)
        self.assertEqual(0x53485454,magic)
        unit=(mm or 200)/1000
        words=struct.unpack_from('<%dh'%((len(data)-16)//2),data,16)
        k=0; short=0; samples=[]
        for _ in range(ways):
            n,flags,aadt=words[k:k+3];k+=3
            pts=[(words[k+j*2]*unit,words[k+j*2+1]*unit) for j in range(n)];k+=n*2
            length=sum(((x2-x1)**2+(z2-z1)**2)**.5 for (x1,z1),(x2,z2) in zip(pts,pts[1:]))
            short+=2<=length<25
            samples.extend(pts)
        self.assertEqual(len(words),k)
        self.assertGreater(short,100)
        self.assertGreater(ways,20000)
        # West Philadelphia, Northwest and Northeast must all have drivable data.
        for x,z in [(-5000,-2500),(-5500,-10000),(8000,-14000)]:
            self.assertTrue(any(abs(px-x)<900 and abs(pz-z)<900 for px,pz in samples),(x,z))
        self.assertFalse(any(abs(px/unit)>=32767 or abs(pz/unit)>=32767 for px,pz in samples))

    def test_six_distinct_real_size_models(self):
        models=self.results['models']
        self.assertEqual(6,len(models))
        self.assertEqual(6,len({m['signature'] for m in models}))
        for m in models:
            self.assertTrue(m['finite'])
            self.assertGreater(m['length'],3.5)
            self.assertLess(m['length'],6)
            self.assertGreater(m['width'],1.6)
            self.assertLess(m['height'],2.6)
            self.assertAlmostEqual(0,m['bottom'],places=5)
            self.assertEqual(m['vertices'],m['paintVertices'])
            self.assertGreater(m['fixedTrim'],0)
            self.assertGreater(m['lampFront'],m['bodyFront'])

    def test_following_vehicles_do_not_overtake(self):
        r=self.results['following']
        self.assertGreaterEqual(r['minGap'],2.49)
        self.assertLess(r['followerSpeed'],r['freeSpeed'])

    def test_visible_dead_end_never_reverses_a_one_way(self):
        self.assertTrue(self.results['deadEnd']['persists'])
        self.assertEqual(1,self.results['deadEnd']['direction'])
        self.assertEqual(0,self.results['deadEnd']['deaths'])

if __name__ == '__main__':
    unittest.main()
