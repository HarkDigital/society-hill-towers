#!/usr/bin/env python3
"""ADVERSARIAL re-derivation of the suppression audit. Independent decoder:
formats read directly from pack_wide.py / pack_city.py / app.js by the verifier.

wide.b64: b64 -> Int32[4] LE header (magic 0x5348545A, nb, nr, na) + Int16 LE body.
  building: n, h*5, minH*5, type, attr, roof, n*(x*5, z*5)   [meters = v/5]
  road:     n, w*10, rt, n*(x*5, z*5)
city.b64: magic 0x5348545B, same layout, coords stored as clip(x/0.7) [meters = v*0.7]
overpasses.json: el chains {c, w, p:[[x,z,y],...]}, sk chains (+cov), cor.
App rule (app.js ovpOwned): seg suppressed iff ALL of start/mid/end have an
aligned (|cos|>=0.8 between road-seg dir and chain-seg dir) chain segment within
radius. NEW radius fixed 2.6; OLD radius = chain hw+3 (hw = w/2 el, w/2+2 sk).
D := max over the 3 sample points of (min aligned distance). Suppressed iff D<r.
"""
import json, struct, base64, math, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '3d-model')

def decode(path, magic_expect, to_m):
    buf = base64.b64decode(open(os.path.join(ROOT, path)).read())
    magic, nb, nr, na = struct.unpack_from('<4i', buf, 0)
    assert magic == magic_expect, hex(magic)
    body = struct.unpack_from('<%dh' % ((len(buf) - 16) // 2), buf, 16)
    i = 0
    # buildings
    for _ in range(nb):
        n = body[i]; i += 6 + 2 * n
    roads = []
    for _ in range(nr):
        n, w10, rt = body[i], body[i+1], body[i+2]; i += 3
        pts = [(body[i + 2*k] * to_m, body[i + 2*k + 1] * to_m) for k in range(n)]
        i += 2 * n
        roads.append((rt, w10 / 10.0, pts))
    return nb, nr, na, roads

nbw, nrw, naw, roadsW = decode('wide.b64', 0x5348545A, 0.2)
nbc, nrc, nac, roadsC = decode('city.b64', 0x5348545B, 0.7)
print(f'wide: nb={nbw} nr={nrw} na={naw}; city: nb={nbc} nr={nrc} na={nac}; total road polylines={nrw+nrc}')

ovp = json.load(open(os.path.join(ROOT, 'overpasses.json')))
segs = []  # (ax,az,bx,bz,hw,cls)
for c in ovp['el']:
    for a, b in zip(c['p'], c['p'][1:]):
        segs.append((a[0], a[1], b[0], b[1], c['w'] / 2.0, c['c']))
for c in ovp['sk']:
    for a, b in zip(c['p'], c['p'][1:]):
        segs.append((a[0], a[1], b[0], b[1], c['w'] / 2.0 + 2, -2 if c.get('cov') else -1))
print(f'chain segments={len(segs)} (el chains={len(ovp["el"])}, sk chains={len(ovp["sk"])})')

CELL = 33.0
grid = {}
for si, (ax, az, bx, bz, hw, cls) in enumerate(segs):
    x0, x1 = min(ax, bx) - 16, max(ax, bx) + 16
    z0, z1 = min(az, bz) - 16, max(az, bz) + 16
    for gx in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
        for gz in range(int(math.floor(z0 / CELL)), int(math.floor(z1 / CELL)) + 1):
            grid.setdefault((gx, gz), []).append(si)

def point_info(x, z, ux, uz):
    """(min aligned dist, min any dist) to chain segs within grid reach (else inf)."""
    da = dany = math.inf
    for si in grid.get((int(math.floor(x / CELL)), int(math.floor(z / CELL))), ()):
        ax, az, bx, bz, hw, cls = segs[si]
        dx, dz = bx - ax, bz - az
        sl = math.hypot(dx, dz) or 1.0
        t = ((x - ax) * dx + (z - az) * dz) / (sl * sl)
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        d = math.hypot(ax + dx * t - x, az + dz * t - z)
        if d < dany: dany = d
        if abs((dx * ux + dz * uz) / sl) < 0.8: continue
        if d < da: da = d
    return da, dany

def old_hit(x, z, ux, uz):
    for si in grid.get((int(math.floor(x / CELL)), int(math.floor(z / CELL))), ()):
        ax, az, bx, bz, hw, cls = segs[si]
        dx, dz = bx - ax, bz - az
        sl = math.hypot(dx, dz) or 1.0
        if abs((dx * ux + dz * uz) / sl) < 0.8: continue
        t = ((x - ax) * dx + (z - az) * dz) / (sl * sl)
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        if math.hypot(ax + dx * t - x, az + dz * t - z) < hw + 3: return True
    return False

OFF = [(-3952.5, -6953.8), (-3980.2, -6902.7), (4819.9, -4756.5),
       (408.2, -1732.4), (-1754.8, 3770.8), (-630.3, -1293.8)]

within15 = 0; no_aligned = 0
sup26 = sup30 = sup40 = supOld = 0
oldOnly_beyond26 = 0
hist = {}
matches = {i: [] for i in range(len(OFF))}
nsegs = 0
for src, roads in (('wide', roadsW), ('city', roadsC)):
    for rt, w, pts in roads:
        for (ax, az), (bx, bz) in zip(pts, pts[1:]):
            nsegs += 1
            ux, uz = bx - ax, bz - az
            L = math.hypot(ux, uz) or 1.0
            ux /= L; uz /= L
            mx, mz = (ax + bx) / 2, (az + bz) / 2
            infos = [point_info(ax, az, ux, uz), point_info(mx, mz, ux, uz), point_info(bx, bz, ux, uz)]
            dmin_any = min(i[1] for i in infos)
            if dmin_any >= 15: continue
            within15 += 1
            D = max(i[0] for i in infos)
            if math.isinf(D):
                no_aligned += 1
            else:
                b = min(int(D), 14)
                hist[b] = hist.get(b, 0) + 1
                if D < 2.6: sup26 += 1
                if D < 3.0: sup30 += 1
                if D < 4.0: sup40 += 1
            old = old_hit(ax, az, ux, uz) and old_hit(mx, mz, ux, uz) and old_hit(bx, bz, ux, uz)
            if old:
                supOld += 1
                if math.isinf(D) or D > 2.6: oldOnly_beyond26 += 1
            for oi, (ox, oz) in enumerate(OFF):
                if min(math.hypot(ax - ox, az - oz), math.hypot(bx - ox, bz - oz), math.hypot(mx - ox, mz - oz)) < 20:
                    matches[oi].append((src, rt, round(L, 1),
                                        [round(i[0], 2) for i in infos], round(D, 2) if not math.isinf(D) else 'inf',
                                        (round(ax, 1), round(az, 1)), (round(bx, 1), round(bz, 1)), old))

print(f'road segments total={nsegs}, within 15 m of a chain={within15}, of those no-aligned-chain={no_aligned}')
print(f'suppressed @2.6={sup26} @3.0={sup30} @4.0={sup40}; OLD rule suppressed={supOld}, old-suppressed with D>2.6 (collateral)={oldOnly_beyond26}')
print('D histogram (1 m bins, aligned only):', dict(sorted(hist.items())))
for oi, (ox, oz) in enumerate(OFF):
    print(f'\n== offender {oi+1} reported at ({ox},{oz}): {len(matches[oi])} nearby road segs ==')
    for m in sorted(matches[oi], key=lambda m: (m[4] if isinstance(m[4], float) else 999)):
        print('  src=%s rt=%d len=%.1f dists=%s D=%s a=%s b=%s oldSup=%s' % (m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7]))
