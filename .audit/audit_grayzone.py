#!/usr/bin/env python3
"""Detail dump of the 2-6 m gray zone + cutoff sweep."""
import importlib.util, sys, math, json, collections
spec = importlib.util.spec_from_file_location('a', '/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/.audit/audit_suppression_radius.py')
# re-run inline instead: copy the loaders
exec(open('/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/.audit/audit_suppression_radius.py').read().split("BINS =")[0])

gray = []
sweep = collections.Counter()   # cutoff -> suppressed count (same+other)
Ds = []
for src, w, rt, pts in roads:
    for i in range(len(pts) - 1):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        ux, uz = x1 - x0, z1 - z0
        L = math.hypot(ux, uz) or 1.0
        ux, uz = ux / L, uz / L
        mx, mz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
        near = min((d for d in (any_min(x0, z0, 15), any_min(mx, mz, 15), any_min(x1, z1, 15))
                    if d is not None), default=None)
        if near is None: continue
        trip = [aligned_min(x0, z0, ux, uz, 200), aligned_min(mx, mz, ux, uz, 200),
                aligned_min(x1, z1, ux, uz, 200)]
        if any(t[0] is None for t in trip) or max(t[0] for t in trip) >= 15: continue
        D = max(t[0] for t in trip)
        mcls = trip[1][1]
        same = (mcls <= 1 and rt <= 1) or (mcls == rt)
        Ds.append((D, same))
        if 2.0 <= D < 6.0:
            gray.append((D, src, rt, w, mcls, same, L, (x0, z0), (x1, z1),
                         [round(t[0], 2) for t in trip]))

print('gray zone 2-6 m, sorted by D:')
for D, src, rt, w, mcls, same, L, a, b, tds in sorted(gray):
    print(f'  D={D:5.2f} {src} rt={rt} w={w:4.1f} chain_c={mcls} {"SAME " if same else "OTHER"} segLen={L:6.1f} '
          f'a=({a[0]:8.1f},{a[1]:8.1f}) b=({b[0]:8.1f},{b[1]:8.1f}) d3={tds}')
print()
for cut in (2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.5, 4.0, 4.5, 5.0):
    s = sum(1 for D, sm in Ds if D < cut and sm)
    o = sum(1 for D, sm in Ds if D < cut and not sm)
    print(f'cutoff {cut:4.1f}: suppress SAME {s:5d}  OTHER {o:3d}')
