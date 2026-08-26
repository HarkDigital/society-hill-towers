#!/usr/bin/env python3
"""lidar_cache/phl_poles_raw.json -> poles.b64 : the Streets Department's street
lighting inventory packed for the app (int16, 0.7 m units, citywide).
Layout: Int32[4] header (magic 0x53485450 'SHTP', nPoles, 0, 0), then
Int16 x3 per pole: x/0.7, z/0.7, packed.
packed bits: 0-1 lamp kind (0 LED, 1 HPS, 2 unknown), 2-8 height in feet
(defaults baked here when the survey says 0), 9 two-luminaire flag.
Filtering: clip to the far-ring box, dedupe within 1.2 m. Sorted row-major so
the delta-friendly layout gzips well. Run with plain python3."""
import base64, json, os, struct

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'lidar_cache')
LON0, LAT0, KX, KZ = -75.144748, 39.945474, 85350.0, 110574.0
CITY = (-12000, 16500, -21700, 9700)
S = 0.7
MAGIC = 0x53485450   # 'SHTP'
# survey height 0 = unrecorded; default by pole family (wood/alley poles carry
# their luminaires lower than the 25 ft streetlight standard)
HDEF_BY_TYPE = {'WP': 20, 'AEL': 15, 'C13': 13, 'PTC': 18, 'PTF': 18}

def main():
    raw = json.load(open(os.path.join(CACHE, 'phl_poles_raw.json')))['poles']
    kept = []
    seen = set()
    n_clip = n_dupe = 0
    for lon, lat, hft, nlum, bulb, ptype in raw:
        x = (lon - LON0) * KX
        z = (LAT0 - lat) * KZ
        if not (CITY[0] <= x <= CITY[1] and CITY[2] <= z <= CITY[3]):
            n_clip += 1
            continue
        key = (int(x / 1.2), int(z / 1.2))
        if key in seen:
            n_dupe += 1
            continue
        seen.add(key)
        h = int(hft) if hft and 8 <= hft <= 127 else HDEF_BY_TYPE.get(ptype, 25)
        kind = 0 if bulb == 'LED' else (1 if bulb == 'HPS' else 2)
        lum2 = 1 if (nlum or 1) >= 2 else 0
        packed = kind | (min(127, h) << 2) | (lum2 << 9)
        kept.append((int(round(x / S)), int(round(z / S)), packed))
    kept.sort(key=lambda p: (p[1] >> 6, p[0]))   # ~45 m rows: gzip-friendly locality
    body = bytearray(struct.pack('<4i', MAGIC, len(kept), 0, 0))
    for xi, zi, pk in kept:
        assert -32767 <= xi <= 32767 and -32767 <= zi <= 32767
        body += struct.pack('<3h', xi, zi, pk)
    b64 = base64.b64encode(bytes(body)).decode('ascii')
    open(os.path.join(HERE, 'poles.b64'), 'w').write(b64)
    from collections import Counter
    kc = Counter(p[2] & 3 for p in kept)
    print(f'kept {len(kept)} poles (clipped {n_clip}, dupes {n_dupe}); kinds LED/HPS/unk: '
          f'{kc.get(0,0)}/{kc.get(1,0)}/{kc.get(2,0)}')
    print(f'poles.b64 {len(b64)/1e6:.2f} MB base64', flush=True)

if __name__ == '__main__':
    main()
