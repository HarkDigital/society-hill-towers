#!/usr/bin/env python3
"""Audit of the road-suppression radius against baked overpass/sunken chains.

OLD rule (app.js ovpOwned): a packed road segment is suppressed when all three of
start/mid/end have SOME aligned (|cos| >= 0.8) chain segment within (hw + 3.0),
where hw = w/2 for elevated chains and w/2 + 2 for sunken ones, looked up through
a 28 m grid whose cells are seeded with each chain seg's bbox expanded by hw.

PROPOSED rule: fixed 2.6 m radius in place of hw + 3.0.

Metric D per road segment = max over {start, mid, end} of the min distance to an
aligned chain segment (the smallest fixed radius at which the rule would fire).
"""
import base64, struct, array, json, math, os, collections

MODEL = '/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model'

# ---------------------------------------------------------------- decode roads
def decode(path, coord_scale_div, magic_expect):
    raw = base64.b64decode(open(path).read())
    magic, nb, nr, na = struct.unpack('<4i', raw[:16])
    assert magic == magic_expect, hex(magic)
    body = array.array('h')
    body.frombytes(raw[16:])
    i = 0
    for _ in range(nb):                      # building: n,h,minH,type,attr,roof, pts
        n = body[i]; i += 6 + 2 * n
    roads = []
    for _ in range(nr):                      # road: n, w*10, type, pts
        n, w10, rt = body[i], body[i + 1], body[i + 2]; i += 3
        pts = []
        for k in range(n):
            pts.append((body[i] * coord_scale_div, body[i + 1] * coord_scale_div))
            i += 2
        roads.append((w10 / 10.0, rt, pts))
    return roads

roads = [(src, w, rt, pts) for src, path, sc, mg in (
            ('wide', os.path.join(MODEL, 'wide.b64'), 0.2, 0x5348545A),
            ('city', os.path.join(MODEL, 'city.b64'), 0.7, 0x5348545B))
         for (w, rt, pts) in decode(path, sc, mg)]

# ---------------------------------------------------------------- chain segs
OVP = json.load(open(os.path.join(MODEL, 'overpasses.json')))
segs = []  # (ax, az, bx, bz, hw, cls) ; cls = original chain class c for both kinds
for c in OVP['el']:
    for i in range(len(c['p']) - 1):
        a, b = c['p'][i], c['p'][i + 1]
        segs.append((a[0], a[1], b[0], b[1], c['w'] / 2.0, c['c']))
for c in OVP['sk']:
    for i in range(len(c['p']) - 1):
        a, b = c['p'][i], c['p'][i + 1]
        segs.append((a[0], a[1], b[0], b[1], c['w'] / 2.0 + 2.0, c['c']))

CELL = 28.0
# exact app grid (expansion = hw) for the faithful OLD-rule simulation
grid_old = collections.defaultdict(list)
# generous grid (expansion covers a 15 m query from anywhere in the cell)
grid_wide = collections.defaultdict(list)
GEN = 15 + CELL * 1.5
for idx, (ax, az, bx, bz, hw, cls) in enumerate(segs):
    for g, e in ((grid_old, hw), (grid_wide, GEN)):
        x0 = math.floor((min(ax, bx) - e) / CELL); x1 = math.floor((max(ax, bx) + e) / CELL)
        z0 = math.floor((min(az, bz) - e) / CELL); z1 = math.floor((max(az, bz) + e) / CELL)
        for gx in range(x0, x1 + 1):
            for gz in range(z0, z1 + 1):
                g[(gx, gz)].append(idx)

def pt_seg_dist(x, z, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    l2 = dx * dx + dz * dz or 1e-9
    t = ((x - ax) * dx + (z - az) * dz) / l2
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    px, pz = ax + dx * t - x, az + dz * t - z
    return math.hypot(px, pz)

def hit_old(x, z, ux, uz):
    """faithful ovpOwned point test: single 28 m cell, aligned, dist < hw + 3."""
    for s in grid_old.get((math.floor(x / CELL), math.floor(z / CELL)), ()):
        ax, az, bx, bz, hw, cls = segs[s]
        dx, dz = bx - ax, bz - az
        sl = math.hypot(dx, dz) or 1.0
        if abs((dx * ux + dz * uz) / sl) < 0.8: continue
        if pt_seg_dist(x, z, ax, az, bx, bz) < hw + 3.0: return True
    return False

def aligned_min(x, z, ux, uz, cap):
    """min distance to an aligned chain seg (generous grid), plus that seg's class/hw."""
    best, bcls, bhw = None, None, None
    for s in grid_wide.get((math.floor(x / CELL), math.floor(z / CELL)), ()):
        ax, az, bx, bz, hw, cls = segs[s]
        dx, dz = bx - ax, bz - az
        sl = math.hypot(dx, dz) or 1.0
        if abs((dx * ux + dz * uz) / sl) < 0.8: continue
        d = pt_seg_dist(x, z, ax, az, bx, bz)
        if d <= cap and (best is None or d < best):
            best, bcls, bhw = d, cls, hw
    return best, bcls, bhw

def any_min(x, z, cap):
    best = None
    for s in grid_wide.get((math.floor(x / CELL), math.floor(z / CELL)), ()):
        ax, az, bx, bz, hw, cls = segs[s]
        d = pt_seg_dist(x, z, ax, az, bx, bz)
        if d <= cap and (best is None or d < best):
            best = d
    return best

BINS = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 9), (9, 12), (12, 15)]
def bin_of(d):
    for lo, hi in BINS:
        if lo <= d < hi: return f'{lo}-{hi}'
    return None

hist = collections.defaultdict(int)          # (sameclass, bin) -> n
n_near = 0                                   # segments within 15 m of any chain
n_near_unaligned = 0                         # near a chain but no aligned seg within 15 for all 3 pts
old_supp = 0
old_supp_beyond = []                         # collateral: OLD suppressed, D > 2.6
escapes = []                                 # same-class motorway-family, 2.6 < D < 4
new_supp = {2.6: 0, 3.0: 0, 3.5: 0, 4.0: 0}
d_all_same, d_all_other = [], []

for src, w, rt, pts in roads:
    for i in range(len(pts) - 1):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        ux, uz = x1 - x0, z1 - z0
        L = math.hypot(ux, uz) or 1.0
        ux, uz = ux / L, uz / L
        mx, mz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
        # 15 m qualification: min over the three sample points of unaligned distance
        near = min((d for d in (any_min(x0, z0, 15), any_min(mx, mz, 15), any_min(x1, z1, 15))
                    if d is not None), default=None)
        if near is None: continue
        n_near += 1
        # rule-equivalent radius D
        trip = [aligned_min(x0, z0, ux, uz, 200), aligned_min(mx, mz, ux, uz, 200),
                aligned_min(x1, z1, ux, uz, 200)]
        old = hit_old(x0, z0, ux, uz) and hit_old(x1, z1, ux, uz) and hit_old(mx, mz, ux, uz)
        if old: old_supp += 1
        if any(t[0] is None for t in trip) or max(t[0] for t in trip) >= 15:
            n_near_unaligned += 1
            if old:  # suppressed by old rule yet no aligned seg per generous metric? (shouldn't happen)
                old_supp_beyond.append((mx, mz, f'old-suppressed but unaligned?! rt={rt}'))
            continue
        D = max(t[0] for t in trip)
        mcls, mhw = trip[1][1], trip[1][2]   # class of chain nearest the midpoint
        same = (mcls <= 1 and rt <= 1) or (mcls == rt)
        hist[('same' if same else 'other'), bin_of(D)] += 1
        (d_all_same if same else d_all_other).append(D)
        for r in new_supp:
            if D < r: new_supp[r] += 1
        if old and D > 2.6:
            old_supp_beyond.append((mx, mz,
                f'rt={rt} chain_c={mcls} chain_hw={mhw:.1f} D={D:.2f} old_r={mhw + 3:.1f} {"SAME" if same else "OTHER"} src={src} w={w:.0f}'))
        if same and mcls <= 1 and 2.6 <= D < 4:
            escapes.append((mx, mz, f'rt={rt} chain_c={mcls} D={D:.2f} src={src}'))

out = {
    'n_road_polylines': len(roads),
    'n_segments_within_15m': n_near,
    'n_near_but_unaligned': n_near_unaligned,
    'old_rule_suppressed': old_supp,
    'old_suppressed_D_gt_2.6_collateral': len(old_supp_beyond),
    'same_class_escapes_2.6_to_4_motorway': len(escapes),
    'suppressed_at_2.6': new_supp[2.6], 'suppressed_at_3.0': new_supp[3.0],
    'suppressed_at_3.5': new_supp[3.5], 'suppressed_at_4.0': new_supp[4.0],
}
print(json.dumps(out, indent=1))
print('\nhistogram D (rule-equivalent radius), same-class vs other:')
for lo, hi in BINS:
    b = f'{lo}-{hi}'
    print(f'  {b:>6} m   SAME {hist[("same", b)]:5d}   OTHER {hist[("other", b)]:5d}')
print('\ncollateral (old suppressed, D>2.6):', len(old_supp_beyond))
for x, z, d in old_supp_beyond[:60]: print(f'  ({x:8.1f},{z:8.1f}) {d}')
print('\nescapes (same-class motorway 2.6<=D<4):', len(escapes))
for x, z, d in escapes[:60]: print(f'  ({x:8.1f},{z:8.1f}) {d}')
if d_all_same:
    ds = sorted(d_all_same)
    print('\nsame-class D percentiles: p50=%.2f p90=%.2f p95=%.2f p99=%.2f max=%.2f'
          % (ds[len(ds)//2], ds[int(len(ds)*.9)], ds[int(len(ds)*.95)], ds[int(len(ds)*.99)], ds[-1]))
if d_all_other:
    do = sorted(d_all_other)
    print('other D percentiles: p50=%.2f p10=%.2f min=%.2f' % (do[len(do)//2], do[int(len(do)*.1)], do[0]))
