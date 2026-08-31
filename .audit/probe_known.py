#!/usr/bin/env python3
"""Probe the known-offender window x 200-500 z 850-1400: what chains and buildings are there."""
import base64, json, math, struct, os

MODEL = '/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model'
BOX = (200, 500, 850, 1400)  # x0 x1 z0 z1, generous probing

ov = json.load(open(os.path.join(MODEL, 'overpasses.json')))
print('--- el chains touching box (any class) ---')
for ci, ch in enumerate(ov['el']):
    pts = [q for q in ch['p'] if BOX[0] - 100 <= q[0] <= BOX[1] + 100 and BOX[2] - 100 <= q[1] <= BOX[3] + 100]
    if pts:
        ys = [q[2] for q in pts]
        print('el[%d] c=%d w=%.1f e=%s npts_in=%d y %.1f..%.1f  first=%s last=%s' % (
            ci, ch['c'], ch['w'], ch.get('e'), len(pts), min(ys), max(ys),
            [round(v, 1) for v in pts[0]], [round(v, 1) for v in pts[-1]]))

raw = base64.b64decode(open(os.path.join(MODEL, 'wide.b64')).read())
magic, nb, nr, na = struct.unpack_from('<4i', raw, 0)
body = struct.unpack_from('<%dh' % ((len(raw) - 16) // 2), raw, 16)
i = 0
bs = []
for _ in range(nb):
    n = body[i]; h = body[i + 1] / 5.0; minh = body[i + 2] / 5.0; bt = body[i + 3]
    i += 6
    pts = [(body[i + 2 * k] / 5.0, body[i + 2 * k + 1] / 5.0) for k in range(n)]
    i += 2 * n
    bs.append((h, minh, bt, pts))

def centroid(p):
    a = cx = cz = 0.0
    for j in range(len(p)):
        x0, z0 = p[j]; x1, z1 = p[(j + 1) % len(p)]
        cr = x0 * z1 - x1 * z0
        a += cr; cx += (x0 + x1) * cr; cz += (z0 + z1) * cr
    if abs(a) < 1e-9:
        return sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p)
    a *= 0.5
    return cx / (6 * a), cz / (6 * a)

# distance from point to a chain
def dist_to_chain(x, z, p):
    best = 1e18
    for j in range(len(p) - 1):
        x0, z0, x1, z1 = p[j][0], p[j][1], p[j + 1][0], p[j + 1][1]
        dx = x1 - x0; dz = z1 - z0
        L2 = dx * dx + dz * dz
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((x - x0) * dx + (z - z0) * dz) / L2))
        d = math.hypot(x - (x0 + t * dx), z - (z0 + t * dz))
        best = min(best, d)
    return best

mot = [(ci, ch) for ci, ch in enumerate(ov['el']) if ch['c'] <= 1]
print('--- buildings with centroid in box, h>=3, with min dist to any c<=1 el chain ---')
cnt = 0
for h, minh, bt, pts in bs:
    cx, cz = centroid(pts)
    if not (BOX[0] <= cx <= BOX[1] and BOX[2] <= cz <= BOX[3]):
        continue
    if h < 3:
        continue
    best = 1e18; bci = -1
    for ci, ch in mot:
        d = dist_to_chain(cx, cz, ch['p'])
        if d < best:
            best = d; bci = ci
    if best < 60:
        hw = ov['el'][bci]['w'] / 2.0 - 1.0
        print('h=%5.1f minh=%4.1f t=%d nverts=%2d centroid=(%7.1f,%7.1f) dist=%6.1f to el[%d] (w=%.1f, swath hw=%.1f) %s' % (
            h, minh, bt, len(pts), cx, cz, best, bci, ov['el'][bci]['w'], hw, 'IN' if best <= hw else ''))
        cnt += 1
print('shown:', cnt)
