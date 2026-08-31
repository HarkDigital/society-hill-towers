#!/usr/bin/env python3
"""Deeper probe: chains whose SEGMENTS cross the window, plus all buildings in the window."""
import base64, json, math, struct, os

MODEL = '/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model'
BOX = (100, 600, 750, 1500)

def seg_in_box(x0, z0, x1, z1, box, pad=20):
    # coarse: clip segment against expanded box via sampling
    for t in [k / 20 for k in range(21)]:
        x = x0 + t * (x1 - x0); z = z0 + t * (z1 - z0)
        if box[0] - pad <= x <= box[1] + pad and box[2] - pad <= z <= box[3] + pad:
            return True
    return False

ov = json.load(open(os.path.join(MODEL, 'overpasses.json')))
print('--- el chains with SEGMENTS crossing box ---')
for ci, ch in enumerate(ov['el']):
    p = ch['p']
    hits = [j for j in range(len(p) - 1) if seg_in_box(p[j][0], p[j][1], p[j + 1][0], p[j + 1][1], BOX)]
    if hits:
        print('el[%d] c=%d w=%.1f nsegs_in=%d totpts=%d span y %.1f..%.1f' % (
            ci, ch['c'], ch['w'], len(hits), len(p), min(q[2] for q in p), max(q[2] for q in p)))
        for j in hits[:6]:
            print('   seg %d: %s -> %s' % (j, [round(v,1) for v in p[j]], [round(v,1) for v in p[j+1]]))
print('--- sk runs crossing box ---')
for ci, ch in enumerate(ov.get('sk', [])):
    p = ch['p']
    hits = [j for j in range(len(p) - 1) if seg_in_box(p[j][0], p[j][1], p[j + 1][0], p[j + 1][1], BOX)]
    if hits:
        print('sk[%d] c=%d w=%.1f cov=%s nsegs_in=%d' % (ci, ch['c'], ch['w'], ch.get('cov'), len(hits)))
        for j in hits[:4]:
            print('   seg %d: %s -> %s' % (j, [round(v,1) for v in p[j]], [round(v,1) for v in p[j+1]]))
print('--- cor runs crossing box ---')
for ci, run in enumerate(ov.get('cor', [])):
    hits = [j for j in range(len(run) - 1) if seg_in_box(run[j][0], run[j][1], run[j + 1][0], run[j + 1][1], BOX)]
    if hits:
        print('cor[%d] nsegs_in=%d sample %s' % (ci, len(hits), [round(v,1) for v in run[hits[0]]]))

# summary of ALL el chain endpoints near the waterfront strip x 0..700, z 0..2500
print('--- all el chains with any vertex in x 0..700, z 0..2500 ---')
for ci, ch in enumerate(ov['el']):
    pts = [q for q in ch['p'] if 0 <= q[0] <= 700 and 0 <= q[1] <= 2500]
    if pts:
        print('el[%d] c=%d w=%.1f n_in=%d first_in=%s last_in=%s' % (
            ci, ch['c'], ch['w'], len(pts), [round(v,1) for v in pts[0]], [round(v,1) for v in pts[-1]]))

raw = base64.b64decode(open(os.path.join(MODEL, 'wide.b64')).read())
magic, nb, nr, na = struct.unpack_from('<4i', raw, 0)
body = struct.unpack_from('<%dh' % ((len(raw) - 16) // 2), raw, 16)
i = 0
inbox = []
for _ in range(nb):
    n = body[i]; h = body[i+1]/5.0; minh = body[i+2]/5.0; bt = body[i+3]; i += 6
    pts = [(body[i+2*k]/5.0, body[i+2*k+1]/5.0) for k in range(n)]
    i += 2*n
    cx = sum(q[0] for q in pts)/n; cz = sum(q[1] for q in pts)/n
    if 200 <= cx <= 500 and 850 <= cz <= 1400 and h >= 8:
        inbox.append((h, bt, n, round(cx,1), round(cz,1)))
inbox.sort(key=lambda r: -r[0])
print('--- buildings h>=8 with mean-centroid in 200..500 x 850..1400 (top 25 of %d) ---' % len(inbox))
for r in inbox[:25]:
    print('h=%5.1f t=%d n=%2d at (%s, %s)' % r)
