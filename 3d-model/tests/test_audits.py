"""Ported .audit/ probes (Round 27's ten-agent cleanup sweep), rewritten against the
committed data with the model directory resolved from this file:

  far-ring buildings vs motorway decks  (.audit/audit_city_motorway.py, verify_city_motorway_indep.py)
  wide buildings straddling deck swaths (.audit/audit_wide_decks.py, verify_wide_decks.py)
  street labels sliced by crossing decks (.audit/audit_label_slices.py, verify_label_slices.py)
  road-suppression radius               (.audit/audit_suppression_radius.py, verify_suppression.py)
  parapet tangles / pier-through-deck   (.audit/parapet_tangle_audit.py, verify_parapet_tangles.py)

Each test also checks that the runtime guard the audit led to is still present in
app.js (ovpStraddle / ovpOwned / mouthAt), because several findings are handled at
load time rather than in the packed data.
"""
import collections
import math
import unittest

try:
    from . import _common as C          # python3 -m unittest tests.test_audits
except ImportError:
    import _common as C                 # python3 -m unittest discover -s tests

# handoff.md Round 27: 7 wide-set footprints straddle I-95/I-676 decks edge-on and are
# skipped at runtime by ovpStraddle. A larger count means new straddlers were packed.
WIDE_DECK_BASELINE = 7
# handoff.md Round 27 counted 190 overlap regions citywide (47 junction mouths, 128 braids,
# 15 twins); the Round 40 nw-gap rebake (527 chains) measures 226 with this port.
PARAPET_REGION_BASELINE = 226


def _app_js():
    p = C.path('app.js')
    return p.read_text(encoding='utf-8') if p.exists() else ''


def swath_grid(ov, cell=64.0):
    """c<=1 elevated chains at halfW = w/2 - 1 (the audit band), plus open sunken runs
    and the corridor, indexed for point / edge tests."""
    g = C.SegGrid(cell)
    for ch in ov['el']:
        if ch.get('c', 99) > 1:
            continue
        hw = ch['w'] / 2.0 - 1.0
        for a, b in zip(ch['p'], ch['p'][1:]):
            g.add(a[0], a[1], b[0], b[1], hw + 1.0, (hw, 'elevated'))
    for ch in ov.get('sk', []):
        if ch.get('cov') == 1:
            continue
        hw = ch['w'] / 2.0 - 1.0
        for a, b in zip(ch['p'], ch['p'][1:]):
            g.add(a[0], a[1], b[0], b[1], hw + 1.0, (hw, 'sunken-open'))
    for run in ov.get('cor', []):
        for a, b in zip(run, run[1:]):
            hw = max(a[3], b[3])
            g.add(a[0], a[1], b[0], b[1], hw + 1.0, (hw, 'corridor'))
    return g


def hit_kinds(grid, x, z):
    out = set()
    for idx in grid.at(x, z):
        ax, az, bx, bz, (hw, kind) = grid.segs[idx]
        if kind in out:
            continue
        if C.seg_dist(x, z, ax, az, bx, bz) <= hw:
            out.add(kind)
    return out


def deck_offenders(buildings, grid, edge_test):
    """Buildings (h >= 4) whose centroid or >= 60 % of vertices lie in a swath, or
    (edge_test) whose outline comes within halfW of a swath centerline."""
    offenders = []
    for n, h, mh, bt, pts in buildings:
        if h < 4:
            continue
        xs = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        if not grid.bbox_touches(min(xs), max(xs), min(zs), max(zs)):
            continue
        cx, cz = C.mean_centroid(pts)
        kinds = set(hit_kinds(grid, cx, cz))
        how = 'centroid' if kinds else ''
        if not kinds:
            votes = collections.Counter()
            for x, z in pts:
                for k in hit_kinds(grid, x, z):
                    votes[k] += 1
            kinds = {k for k, c in votes.items() if c >= 0.6 * n}
            if kinds:
                how = '%d/%d verts' % (max(votes.values()), n)
        if not kinds and edge_test:
            cand = grid.in_bbox(min(xs), max(xs), min(zs), max(zs))
            for idx in cand:
                ax, az, bx, bz, (hw, kind) = grid.segs[idx]
                for k in range(n):
                    a, b = pts[k], pts[(k + 1) % n]
                    if C.seg_seg_dist(a[0], a[1], b[0], b[1], ax, az, bx, bz) <= hw:
                        kinds.add(kind)
                        break
            if kinds:
                how = 'edge straddles swath'
        if kinds:
            offenders.append((round(cx, 1), round(cz, 1), round(h, 1), how, sorted(kinds)))
    return offenders


class DeckAudits(unittest.TestCase):

    def test_far_ring_buildings_clear_of_motorway_decks(self):
        """audit_city_motorway: no city.b64 building (h >= 4) with its centroid, or 60 % of its
        vertices, inside a c<=1 elevated deck band (w/2 - 1). Round 27 left the far ring clean."""
        C.require(self, 'city.b64', 'overpasses.json')
        ov = C.load_json('overpasses.json')
        grid = C.SegGrid(64.0)
        for ax, az, bx, bz, ch in C.chain_segments(ov, ('el',), max_class=1):
            hw = ch['w'] / 2.0 - 1.0
            grid.add(ax, az, bx, bz, hw + 1.0, (hw, 'elevated'))
        off = deck_offenders(C.walk_scene('city.b64')['buildings'], grid, edge_test=False)
        self.assertEqual([], off, '%d far-ring buildings sit in motorway deck bands: %s' % (len(off), off[:10]))

    def test_wide_buildings_straddling_decks_are_guarded(self):
        """audit_wide_decks: wide.b64 footprints in / across the c<=1 deck swaths, the open
        Vine cut and the corridor. These are real OSM footprints under I-95 / I-676 that
        the app skips at runtime (ovpStraddle), so the count is bounded by the Round 27
        baseline instead of asserted zero — and the runtime guard must still exist."""
        C.require(self, 'wide.b64', 'overpasses.json', 'app.js')
        self.assertIn('ovpStraddle', _app_js(), 'app.js lost the ovpStraddle footprint guard')
        ov = C.load_json('overpasses.json')
        off = deck_offenders(C.walk_scene('wide.b64')['buildings'], swath_grid(ov), edge_test=True)
        print('\n  wide buildings straddling deck swaths: %d (baseline %d)' % (len(off), WIDE_DECK_BASELINE))
        for o in off[:12]:
            print('    at (%s, %s) h=%s %s %s' % o)
        self.assertLessEqual(len(off), WIDE_DECK_BASELINE,
                             '%d wide footprints straddle deck swaths (baseline %d): %s' % (len(off), WIDE_DECK_BASELINE, off[:10]))


class LabelAudit(unittest.TestCase):

    def test_street_labels_not_sliced_by_decks(self):
        """audit_label_slices: a label span (len(name) * 0.31 * TH[cls] each side of its anchor
        along its bearing) must not pass within w/2 + 1 of an elevated chain that crosses it
        (|cos| < 0.72). bake_street_labels.py shifts or drops such labels; sliced == 0."""
        C.require(self, 'street_labels.json', 'overpasses.json')
        TH = [7.0, 5.6, 4.4]
        COS_CROSS = 0.72
        d = C.load_json('street_labels.json')
        names, flat = d['names'], d['l']
        self.assertEqual(0, len(flat) % 5, 'street_labels.json "l" is not a flat list of 5-tuples')
        ov = C.load_json('overpasses.json')
        grid = C.SegGrid(250.0)
        for ax, az, bx, bz, ch in C.chain_segments(ov, ('el',)):
            dx, dz = bx - ax, bz - az
            L = math.hypot(dx, dz)
            if L < 0.01:
                continue
            th = ch['w'] / 2.0 + 1.0
            grid.add(ax, az, bx, bz, th, (dx / L, dz / L, th, ch['c']))
        sliced = []
        for li in range(len(flat) // 5):
            ni, x, z, b, cls = flat[li * 5:li * 5 + 5]
            self.assertTrue(0 <= ni < len(names), 'label nameIdx out of range')
            self.assertIn(cls, (0, 1, 2))
            half = len(names[ni]) * 0.31 * TH[cls]
            ang = math.radians(b)
            ux, uz = math.cos(ang), math.sin(ang)
            p1x, p1z, p2x, p2z = x - ux * half, z - uz * half, x + ux * half, z + uz * half
            for idx in grid.in_bbox(min(p1x, p2x), max(p1x, p2x), min(p1z, p2z), max(p1z, p2z)):
                ax, az, bx, bz, (sux, suz, th, c) = grid.segs[idx]
                if abs(ux * sux + uz * suz) >= COS_CROSS:
                    continue
                if C.seg_seg_dist(p1x, p1z, p2x, p2z, ax, az, bx, bz) < th:
                    sliced.append((names[ni], x, z, c))
                    break
        self.assertEqual([], sliced, '%d of %d labels are sliced by crossing decks: %s' % (len(sliced), len(flat) // 5, sliced[:12]))


class SuppressionAudit(unittest.TestCase):

    def test_suppression_radius_separates_duplicates_from_neighbors(self):
        """audit_suppression_radius: for every packed road segment near a baked chain, D =
        the larger of the two endpoints' distance to the nearest ALIGNED (|cos| >= 0.8)
        chain segment — the smallest fixed radius at which ovpOwned would drop it. Round 27
        chose 2.6 m because the distribution is bimodal (true duplicates under 2 m, real
        neighbors beyond 5 m). Guard: the gray zone [2.6, 5) must stay a sliver, duplicates
        must dominate, and the ovpOwned rule must still be in app.js."""
        C.require(self, 'wide.b64', 'city.b64', 'overpasses.json', 'app.js')
        self.assertIn('ovpOwned', _app_js(), 'app.js lost the ovpOwned road-suppression rule')
        ov = C.load_json('overpasses.json')
        CELL = 28.0
        grid = C.SegGrid(CELL)
        pad = 15 + CELL * 1.5
        for kind, extra in (('el', 0.0), ('sk', 2.0)):
            for ax, az, bx, bz, ch in C.chain_segments(ov, (kind,)):
                grid.add(ax, az, bx, bz, pad, (ch['w'] / 2.0 + extra, ch['c']))

        def aligned_min(x, z, ux, uz):
            best, bcls = None, None
            for idx in grid.at(x, z):
                ax, az, bx, bz, (hw, cls) = grid.segs[idx]
                dx, dz = bx - ax, bz - az
                sl = math.hypot(dx, dz) or 1.0
                if abs((dx * ux + dz * uz) / sl) < 0.8:
                    continue
                d = C.seg_dist(x, z, ax, az, bx, bz)
                if d <= 15 and (best is None or d < best):
                    best, bcls = d, cls
            return best, bcls

        hist = collections.Counter()
        near = 0
        gray = same_dup = same_total = 0
        for name in ('wide.b64', 'city.b64'):
            for n, w, rt, pts in C.walk_scene(name)['roads']:
                for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
                    if not grid.at(x0, z0) and not grid.at(x1, z1):
                        continue
                    ux, uz = x1 - x0, z1 - z0
                    L = math.hypot(ux, uz) or 1.0
                    ux /= L
                    uz /= L
                    d0, c0 = aligned_min(x0, z0, ux, uz)
                    d1, c1 = aligned_min(x1, z1, ux, uz)
                    if d0 is None or d1 is None:
                        continue
                    near += 1
                    D = max(d0, d1)
                    same = (c0 <= 1 and rt <= 1) or (c0 == rt)
                    hist[('same' if same else 'other', min(int(D), 14))] += 1
                    if 2.6 <= D < 5.0:
                        gray += 1
                    if same:
                        same_total += 1
                        if D < 2.6:
                            same_dup += 1
        self.assertGreater(near, 500, 'too few road segments near chains for the audit to mean anything (%d)' % near)
        print('\n  suppression D histogram (%d near+aligned segments; gray zone [2.6,5) = %d):' % (near, gray))
        for b in range(0, 15):
            print('    %2d-%2d m  same %5d  other %4d' % (b, b + 1, hist[('same', b)], hist[('other', b)]))
        self.assertLessEqual(gray / near, 0.02, 'gray zone [2.6, 5) holds %.1f%% of near segments — the 2.6 m radius is no longer a clean cut' % (100.0 * gray / near))
        self.assertGreaterEqual(same_dup / max(1, same_total), 0.6, 'only %.0f%% of same-class near segments are true duplicates (< 2.6 m)' % (100.0 * same_dup / max(1, same_total)))


class ParapetAudit(unittest.TestCase):

    def test_overpasses_structure(self):
        """overpasses.json shape the app + audits rely on: el/sk chains with class 0..6, positive
        width, >= 2 [x, z, y] points, 2-entry end flags; sk carries cov; cor runs of [x, z, floorY, halfW]."""
        C.require(self, 'overpasses.json')
        ov = C.load_json('overpasses.json')
        for k in ('el', 'sk', 'cor'):
            self.assertIn(k, ov)
        for kind in ('el', 'sk'):
            for i, ch in enumerate(ov[kind]):
                with self.subTest(kind=kind, chain=i):
                    self.assertTrue(0 <= ch['c'] <= 6, 'class %s' % ch['c'])
                    self.assertGreater(ch['w'], 0)
                    self.assertGreaterEqual(len(ch['p']), 2)
                    self.assertTrue(all(len(q) == 3 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in q) for q in ch['p']))
                    self.assertEqual(2, len(ch.get('e', [0, 0])))
                    zero = sum(1 for a, b in zip(ch['p'], ch['p'][1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6)
                    self.assertEqual(0, zero, 'zero-length segment in chain')
                    if kind == 'sk':
                        self.assertIn(ch.get('cov'), (0, 1))
        for run in ov['cor']:
            self.assertGreaterEqual(len(run), 2)
            self.assertTrue(all(len(q) == 4 and q[3] > 0 for q in run))
        self.assertGreater(len(ov['el']), 100, 'suspiciously few elevated chains')

    def test_parapet_overlap_regions_bounded(self):
        """parapet_tangle_audit: places where two different decks overlap laterally (closest
        approach < hwA + hwB) at nearly the same height (|dy| < 2.5), clustered at 40 m.
        Handled at runtime (parapet segments inside another deck's footprint are skipped,
        mouthAt keeps the ramp-exit gaps), so the region count is bounded by the measured
        baseline (+25 %) rather than asserted zero — and the runtime rule must still exist."""
        C.require(self, 'overpasses.json', 'app.js')
        self.assertIn('mouthAt', _app_js(), 'app.js lost the mouthAt parapet-gap rule')
        ov = C.load_json('overpasses.json')
        chains = ov['el']
        maxhw = max(ch['w'] for ch in chains) / 2.0
        grid = C.SegGrid(100.0)
        for ci, ch in enumerate(chains):
            for a, b in zip(ch['p'], ch['p'][1:]):
                if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
                    continue
                grid.add(a[0], a[1], b[0], b[1], 2 * maxhw + 1.0, (ci, a[2], b[2]))

        def closest(a, b):
            p1x, p1z = a[0], a[1]
            d1x, d1z = a[2] - a[0], a[3] - a[1]
            p2x, p2z = b[0], b[1]
            d2x, d2z = b[2] - b[0], b[3] - b[1]
            rx, rz = p1x - p2x, p1z - p2z
            A = d1x * d1x + d1z * d1z
            E = d2x * d2x + d2z * d2z
            F = d2x * rx + d2z * rz
            Cc = d1x * rx + d1z * rz
            B = d1x * d2x + d1z * d2z
            den = A * E - B * B
            s = 0.0 if den < 1e-12 else max(0.0, min(1.0, (B * F - Cc * E) / den))
            t = (B * s + F) / E if E > 1e-12 else 0.0
            if t < 0.0:
                t = 0.0
                s = max(0.0, min(1.0, -Cc / A)) if A > 1e-12 else 0.0
            elif t > 1.0:
                t = 1.0
                s = max(0.0, min(1.0, (B - Cc) / A)) if A > 1e-12 else 0.0
            qx = p1x + d1x * s - (p2x + d2x * t)
            qz = p1z + d1z * s - (p2z + d2z * t)
            return math.hypot(qx, qz), s, t

        events = []
        checked = set()
        for lst in grid.cells.values():
            for ii in range(len(lst)):
                for jj in range(ii + 1, len(lst)):
                    si, sj = (lst[ii], lst[jj]) if lst[ii] < lst[jj] else (lst[jj], lst[ii])
                    if (si, sj) in checked:
                        continue
                    checked.add((si, sj))
                    a, b = grid.segs[si], grid.segs[sj]
                    ci, ya0, ya1 = a[4]
                    cj, yb0, yb1 = b[4]
                    if ci == cj:
                        continue
                    lim = chains[ci]['w'] / 2.0 + chains[cj]['w'] / 2.0
                    if min(a[0], a[2]) - lim > max(b[0], b[2]) or min(b[0], b[2]) - lim > max(a[0], a[2]):
                        continue
                    if min(a[1], a[3]) - lim > max(b[1], b[3]) or min(b[1], b[3]) - lim > max(a[1], a[3]):
                        continue
                    d, s, t = closest(a, b)
                    if d >= lim:
                        continue
                    dy = (ya0 + (ya1 - ya0) * s) - (yb0 + (yb1 - yb0) * t)
                    if abs(dy) >= 2.5:
                        continue
                    events.append(((a[0] + (a[2] - a[0]) * s + b[0] + (b[2] - b[0]) * t) / 2.0,
                                   (a[1] + (a[3] - a[1]) * s + b[1] + (b[3] - b[1]) * t) / 2.0))
        # cluster within 40 m (union-find over a 40 m grid)
        MERGE = 40.0
        parent = list(range(len(events)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        eg = collections.defaultdict(list)
        for ei, (x, z) in enumerate(events):
            eg[(int(x // MERGE), int(z // MERGE))].append(ei)
        for (gx, gz), lst in eg.items():
            for dgx in (-1, 0, 1):
                for dgz in (-1, 0, 1):
                    other = eg.get((gx + dgx, gz + dgz))
                    if not other:
                        continue
                    for ei in lst:
                        for ej in other:
                            if ei < ej and (events[ei][0] - events[ej][0]) ** 2 + (events[ei][1] - events[ej][1]) ** 2 <= MERGE * MERGE:
                                ri, rj = find(ei), find(ej)
                                if ri != rj:
                                    parent[rj] = ri
        regions = len({find(i) for i in range(len(events))})
        print('\n  parapet overlap: %d events in %d regions (baseline %d)' % (len(events), regions, PARAPET_REGION_BASELINE))
        self.assertLessEqual(regions, int(PARAPET_REGION_BASELINE * 1.25),
                             '%d deck-overlap regions (baseline %d): new tangles were baked' % (regions, PARAPET_REGION_BASELINE))


if __name__ == '__main__':
    unittest.main()
