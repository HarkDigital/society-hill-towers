#!/usr/bin/env python3
"""Near-miss sweep: buildings h>=4 whose FOOTPRINT comes within w/2+8 of any c<=1 el chain,
in band z 600..1800 (any x). Reports min distance from footprint edge to chain centerline."""
import base64, json, math, struct, os

MODEL = '/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model'
ov = json.load(open(os.path.join(MODEL, 'overpasses.json')))
chains = [(ci, ch) for ci, ch in enumerate(ov['el']) if ch['c'] <= 1]

raw = base64.b64decode(open(os.path.join(MODEL, 'wide.b64')).read())
magic, nb, nr, na = struct.unpack_from('<4i', raw, 0)
body = struct.unpack_from('<%dh' % ((len(raw) - 16) // 2), raw, 16)
i = 0
bs = []
for _ in range(nb):
    n = body[i]; h = body[i+1]/5.0; bt = body[i+3]; i += 6
    pts = [(body[i+2*k]/5.0, body[i+2*k+1]/5.0) for k in range(n)]
    i += 2*n
    bs.append((h, bt, pts))

def seg_seg_dist(ax, az, bx, bz, cx, cz, dx, dz):
    def pt_seg(px, pz, x0, z0, x1, z1):
        ux, uz = x1 - x0, z1 - z0
        L2 = ux*ux + uz*uz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px-x0)*ux + (pz-z0)*uz)/L2))
        return math.hypot(px - (x0 + t*ux), pz - (z0 + t*uz))
    def cross(ox, oz, px, pz, qx, qz): return (px-ox)*(qz-oz) - (pz-oz)*(qx-ox)
    d1 = cross(cx, cz, dx, dz, ax, az); d2 = cross(cx, cz, dx, dz, bx, bz)
    d3 = cross(ax, az, bx, bz, cx, cz); d4 = cross(ax, az, bx, bz, dx, dz)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(pt_seg(ax, az, cx, cz, dx, dz), pt_seg(bx, bz, cx, cz, dx, dz),
               pt_seg(cx, cz, ax, az, bx, bz), pt_seg(dx, dz, ax, az, bx, bz))

rows = []
for h, bt, pts in bs:
    if h < 4:
        continue
    czm = sum(q[1] for q in pts)/len(pts)
    if not (600 <= czm <= 1800):
        continue
    best = (1e18, None)
    for ci, ch in chains:
        p = ch['p']
        for j in range(len(p)-1):
            # quick reject
            if max(p[j][1], p[j+1][1]) < czm - 400 or min(p[j][1], p[j+1][1]) > czm + 400:
                continue
            for k in range(len(pts)):
                a = pts[k]; b = pts[(k+1) % len(pts)]
                d = seg_seg_dist(a[0], a[1], b[0], b[1], p[j][0], p[j][1], p[j+1][0], p[j+1][1])
                if d < best[0]:
                    best = (d, (ci, ch['w'], j))
    if best[1] and best[0] <= best[1][1]/2 + 8:
        cxm = sum(q[0] for q in pts)/len(pts)
        ci, w, j = best[1]
        rows.append((best[0], h, bt, round(cxm,1), round(czm,1), ci, w))
rows.sort()
print('%d candidates (footprint edge within w/2+8 of a c<=1 centerline, z 600..1800):' % len(rows))
for d, h, bt, cx, cz, ci, w in rows:
    inside = 'FOOTPRINT OVERLAPS SWATH' if d <= w/2 - 1 else ('touches swath' if d <= w/2 else 'near miss')
    print('edge-dist=%5.1f (w=%4.1f hw=%4.1f) h=%5.1f t=%d at (%7.1f, %7.1f) vs el[%d]  %s' % (
        d, w, w/2-1, h, bt, cx, cz, ci, inside))
