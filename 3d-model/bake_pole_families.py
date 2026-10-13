#!/usr/bin/env python3
"""lidar_cache/phl_poles_raw.json + poles.b64 -> pole_families.json : each packed pole's family, in poles.b64's own order.

The realism round (night#5): the Streets Department's inventory names every pole's type, and pack_poles.py keeps only the
bulb, the height and the two-luminaire bit, so the page drew a cobra head on a metal standard at every lamp in the city,
the Franklin lanterns of Head House Square and Society Hill and the wood poles of the rowhouse streets alike. This file
carries the family beside poles.b64 instead of inside it (poles.b64 stays byte for byte as committed, and with it every
pole's index, which seeds its colour and its brightness):

  0  a cobra head or davit on a metal standard (SLA, SLF, D30, SNP, MAP, SM, C20 and the like)
  1  a post-top lantern (FLP, C13, PTF, PTC, CCP and the like: Old City, Society Hill, the Avenue of the Arts, the CCD's
     pedestrian lights)
  2  a wood utility or alley pole (WP, AEL)
  3  anything else (drawn as 0)

Each packed pole is matched to the nearest surveyed pole within 2.5 m in the scene frame (the committed poles.b64 still
carries the old 85350 frame, up to 1.1 m east at the far ring; the match does not care which frame packed it). Written as
2 bits a pole, four to a byte, base64: {"n", "bits": 2, "b64", "counts"}. The page checks n against poles.b64's header
and draws every pole as a cobra head when they disagree (rerun this after any pack_poles.py run).
Run with plain python3."""
import base64, json, math, os, struct
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
from philly_frame import LON0, LAT0, KX, KZ   # the one scene frame

FAMILY_POST = {'C13', 'PTC', 'PTF', 'FLP', 'FLPT', 'PTA', 'CTP', 'CHP', 'CCP', 'CCPT'}
FAMILY_WOOD = {'WP', 'WPT', 'AEL', 'SWP'}
FAMILY_ARM = {'SLA', 'SLAT', 'SLF', 'SLFT', 'D30', 'SNP', 'MAP', 'MAPT', 'SM', 'SMP', 'C20', 'TCB', 'TP', 'PDT', 'PDTT',
              'AAMP', 'MLP', 'MLPT', 'RLP', 'SEP', 'PKY'}
MATCH_R = 2.5


def family(ptype):
    if ptype in FAMILY_POST: return 1
    if ptype in FAMILY_WOOD: return 2
    if ptype in FAMILY_ARM: return 0
    return 3


def packed_poles(path):
    raw = base64.b64decode(open(path).read().strip())
    magic, n = struct.unpack('<2i', raw[:8])
    assert magic == 0x53485450, 'poles.b64: bad magic'
    body = struct.unpack('<%dh' % (3 * n), raw[16:16 + 6 * n])
    return [(body[3 * i] * 0.7, body[3 * i + 1] * 0.7) for i in range(n)]


def main():
    survey = json.load(open(os.path.join(CACHE, 'phl_poles_raw.json')))['poles']
    cell = {}
    for lon, lat, _h, _n, _b, ptype in survey:
        x, z = (lon - LON0) * KX, (LAT0 - lat) * KZ
        cell.setdefault((int(math.floor(x / 5)), int(math.floor(z / 5))), []).append((x, z, family(ptype)))
    poles = packed_poles(os.path.join(HERE, 'poles.b64'))
    fams, miss = [], 0
    for x, z in poles:
        gx, gz = int(math.floor(x / 5)), int(math.floor(z / 5))
        best, bd = 3, MATCH_R * MATCH_R
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for sx, sz, f in cell.get((gx + a, gz + b), ()):
                    d = (sx - x) ** 2 + (sz - z) ** 2
                    if d < bd:
                        bd, best = d, f
        if bd >= MATCH_R * MATCH_R:
            miss += 1
        fams.append(best)
    packed = bytearray((len(fams) + 3) // 4)
    for i, f in enumerate(fams):
        packed[i >> 2] |= f << ((i & 3) * 2)
    c = Counter(fams)
    out = {'n': len(fams), 'bits': 2, 'counts': [c.get(k, 0) for k in range(4)], 'b64': base64.b64encode(bytes(packed)).decode('ascii')}
    open(os.path.join(HERE, 'pole_families.json'), 'w').write(json.dumps(out, separators=(',', ':')))
    print('pole_families.json: %d poles, arm/post/wood/other %s, %d unmatched (drawn as other)' % (len(fams), out['counts'], miss))


if __name__ == '__main__':
    main()
