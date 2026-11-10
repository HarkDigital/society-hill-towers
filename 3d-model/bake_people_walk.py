#!/usr/bin/env python3
"""traffic.b64 + the packed footprints -> people_walk.b64 : how far the nearest wall stands from each street's centreline.

Round 227 (Mike, Nov 9, 2026: people on the sidewalks, walking). The walkers keep to a line behind the kerb of every
street the typical traffic runs on, and the page has to know whether a wall stands on that line. It cannot ask at run
time: the flight's collision columns are 4 m cells (a wall is known to 2 m either way), and the far ring's footprints
are gone once their walls are built. So the walls are measured here, against the same ways the page decodes.

What is measured: every way of class 2 to 5 (primary to residential; nobody walks a motorway or a trunk road) is
densified exactly as the page's traffic step densifies it, sampled every STEP metres of its length, and from each sample
a ray is cast square to the way on either side to REACH metres. The first building wall it meets (scene.json's core
buildings and towers, wide.b64, city.b64, outskirts.b64: the footprints the page draws, a part floating MINH_OPEN metres
or more up left out, as are roofs on posts) is that sample's centreline-to-wall distance on that side.

What is stored: CENTRELINE to wall, never kerb to wall. The page takes its own drawn half width off (in the core that
is the scene road's own width, known only at run time; elsewhere PARK_HW by class).

Keyed by way and by distance along the way, NOT by the page's run index. The page's runs cannot be reproduced by a
bake: the traffic step drops a way's vertices over dead water and inside the cap's site, lifts it onto decks and
bridges, and the linker cuts a run only where another run's end meets it within 1.5 m of HEIGHT, all read from the built
terrain (the same decoder gives 46,145 runs on a flat ground and 46,131 on the page). So each way is cut here in plan
alone into intervals, wherever another way's end lies within CUT_TOL of it (the linker's rule without the height) and
wherever another way crosses its middle (the walkers' own nodes, peopleCross in app.js), each interval a block's side
or less; and the page (under ?people=1) tags every run with its way's index and its start's distance along the way
and reads the intervals its own length overlaps. tests/test_people_walk.py proves the tag and the reading for every run.

An interval's value on a side is the PCT-th percentile of its samples, the first and last END_TRIM metres left out
(the samples inside a junction look down the cross street), a short interval keeping its middle third. The fifth
percentile and not the least: one bay, stoop record or misregistered footprint in a block must not close the whole
side (measured over the network's 51,532 intervals at the page's rule, 1.4 m of walk at least: the least sample leaves
67.8 / 78.1 / 92.3 per cent of the kerb walkable in the core / the outer districts / the far ring, the fifth percentile
70.4 / 79.8 / 93.4, the tenth 73.3 / 81.5 / 94.2), and not the tenth, which puts three times the length of walk line
inside a wall (0.08 to 0.10 per cent of it against 0.01 to 0.03). The end trim moves the walkable share by under a point.

Neighbouring intervals of one way are merged when their codes are equal, or when all four are ROOMY: a wall ROOMY_M
or more beyond the class's drawn half width (PARK_HW, the page's table) takes the full setback whatever its distance,
so the page lays the same walk line from the lesser of the two. That is what brings the file under 100 KB: 51,533
intervals as cut, 38,119 written.

Layout (little endian; people_walk.b64 is its base64):
  Int32[4] header: magic 0x53485057, nWays (traffic.b64's own count), nRecords, params
           params = LEN_UNIT_DM | PCT << 8 | CODE_BASE_DM << 16
  bitmap   ceil(nWays / 8) bytes, bit (way & 7) of byte (way >> 3): the way has records (a class 0 or 1 way has none)
  lo, hi   nRecords bytes each: the records' low bytes, then their high bytes (two smooth streams for DEFLATE). A record
           is 16 bits: R code in bits 0 to 5, L code in bits 6 to 11, bit 12 set on a way's last record. R is the right
           of the way's own direction (the page's side +1, the normal (-tz, tx) of the tangent t), L its left
  lens     one byte for every record that is not its way's last, in the records' order: the interval's length in
           LEN_UNIT_DM units (2 m), 1 to 255, each boundary rounded from the way's start. A way's last interval runs
           to its end; an interval over 510 m is written as two records with the same codes
  a code   0 to 61: the wall stands (CODE_BASE_DM + code) decimetres from the centreline, the floor of the measured
           distance, 0 for 3.8 m or less (no room beside the narrowest street the page draws); 62: a wall 10 m or
           more out, within REACH; 63: none within REACH
people_walk.b64 is a derivative database of OpenStreetMap data (ODbL): see ../DATA-LICENSE.md.
Needs numpy (requirements.txt). About half a minute."""
import base64, json, math, pathlib, struct, sys, time
from array import array

HERE = pathlib.Path(__file__).resolve().parent
MAGIC = 0x53485057
STEP = 2.0            # metres between samples along a way
REACH = 25.4          # a ray's length, metres
PCT = 5               # an interval's value is this percentile of its samples
END_TRIM = 8.0        # metres left out at each end of an interval (a junction's box)
CUT_TOL = 0.8         # the page's linker tolerance, in plan
MINH_OPEN = 2.5       # a part whose underside is this high is walked under
LEN_UNIT_DM = 20      # an interval's length byte counts 2 m
PARK_HW = [8, 8, 6.5, 5.5, 4.5, 3.5]   # app.js's PARK_HW: the drawn half width by class (tests/test_people_walk.py holds the two equal)
ROOMY_M = 3.8         # the full setback's 2.0 m and the wall's 0.8 m, and a metre for a core street drawn wider than its class
CODE_BASE_DM = 38     # code 0 is 3.8 m or less: under the narrowest drawn half width (2.5 m) and the least walk (1.4 m)
CODE_FAR, CODE_NONE = 62, 63   # a wall 10 m or more out but in reach, and no wall in reach
CODE_FAR_M = 10.0     # room for the full setback beside any street the page draws under 14.4 m wide
LOOK_TRIM = 3.0       # the page reads a run's stretch drawn in this far, past a boundary's 1 m of rounding
DENSIFY = 20.0        # the page's densify(pts, 20)
CORE = (-640, 770, -520, 850)        # CORE_EXT in app.js: wide.b64 packs no building inside it


def blob(name):
    raw = base64.b64decode((HERE / name).read_text())
    hdr = struct.unpack('<4i', raw[:16])
    body = array('h')
    body.frombytes(raw[16:16 + ((len(raw) - 16) // 2) * 2])
    return hdr, body


def load_ways():
    """traffic.b64's ways as the page's step reads them: (cls, oneway, [(x, z), ...]) in metres."""
    hdr, b = blob('traffic.b64')
    if hdr[0] != 0x53485454:
        sys.exit('ERROR: traffic.b64 has the wrong magic')
    unit = (hdr[3] or 200) / 1000
    ways, k = [], 0
    for _ in range(hdr[1]):
        n, flags = b[k], b[k + 1]
        k += 3
        ways.append((flags & 7, bool(flags & 8), [(b[k + 2 * j] * unit, b[k + 2 * j + 1] * unit) for j in range(n)]))
        k += 2 * n
    return ways


def densify(pts, step=DENSIFY):
    """app.js's densify(), operation for operation."""
    out = [pts[0]]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, math.ceil(L / step))
        for j in range(1, k + 1):
            out.append((a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k))
    return out


def arcs(pts):
    """Cumulative length along a polyline: the 'distance along the way' every record here is keyed by."""
    out, L = [0.0], 0.0
    for i in range(1, len(pts)):
        L += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        out.append(L)
    return out


def load_walls():
    """Every wall the page stands at the ground, as an (n, 4) array of ax, az, bx, bz, with the tier each came from."""
    import numpy as np
    segs, tiers = [], []

    def ring(pts, tier):
        n = len(pts)
        if n < 3:
            return
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            if a[0] != b[0] or a[1] != b[1]:
                segs.append((a[0], a[1], b[0], b[1]))
                tiers.append(tier)

    scene = json.loads((HERE / 'scene.json').read_text())
    for bd in scene['buildings']:
        if bd.get('t') in ('roof', 'ship') or (bd.get('minH') or 0) >= MINH_OPEN:
            continue
        ring(bd['poly'], 0)
    for tw in scene.get('towers', []):
        ring(tw['corners'], 0)
    for name, scale, tier in (('wide.b64', 0.2, 1), ('city.b64', 0.7, 2), ('outskirts.b64', 1.0, 3)):
        hdr, b = blob(name)
        has_attr = hdr[0] in (0x5348545A, 0x5348545D, 0x5348545B, 0x5348545C)
        if not has_attr and hdr[0] not in (0x53485458, 0x53485459):
            sys.exit('ERROR: %s has an unknown magic %x' % (name, hdr[0]))
        k = 0
        for _ in range(hdr[1]):
            n, minh, typ = b[k], b[k + 2] / 5, b[k + 3]
            k += 6 if has_attr else 4
            if typ != 7 and minh < MINH_OPEN:      # 7: a roof on posts, or a ship
                ring([(b[k + 2 * j] * scale, b[k + 2 * j + 1] * scale) for j in range(n)], tier)
            k += 2 * n
    return np.array(segs, dtype=np.float64), np.array(tiers, dtype=np.uint8)


class WallGrid:
    """The walls in CELL metre cells, compressed rows: cell -> the segments whose box touches it."""
    CELL = 32.0

    def __init__(self, segs):
        import numpy as np
        self.np = np
        self.segs = segs
        C = self.CELL
        x0 = np.floor(np.minimum(segs[:, 0], segs[:, 2]) / C).astype(np.int64)
        x1 = np.floor(np.maximum(segs[:, 0], segs[:, 2]) / C).astype(np.int64)
        z0 = np.floor(np.minimum(segs[:, 1], segs[:, 3]) / C).astype(np.int64)
        z1 = np.floor(np.maximum(segs[:, 1], segs[:, 3]) / C).astype(np.int64)
        self.gx0, self.gz0 = int(x0.min()), int(z0.min())
        self.w, self.h = int(x1.max()) - self.gx0 + 1, int(z1.max()) - self.gz0 + 1
        cells, ids = [], []
        nx, nz = x1 - x0 + 1, z1 - z0 + 1
        for dx in range(int(nx.max())):
            for dz in range(int(nz.max())):
                m = (nx > dx) & (nz > dz)
                if not m.any():
                    continue
                cells.append((x0[m] + dx - self.gx0) * self.h + (z0[m] + dz - self.gz0))
                ids.append(np.nonzero(m)[0])
        cells, ids = np.concatenate(cells), np.concatenate(ids)
        order = np.argsort(cells, kind='stable')
        self.ids = ids[order]
        self.start = np.searchsorted(cells[order], np.arange(self.w * self.h + 1))

    def near(self, x0, x1, z0, z1):
        """The segments in the cells a box touches (each once)."""
        np, C = self.np, self.CELL
        ax, bx = max(0, int(math.floor(x0 / C)) - self.gx0), min(self.w - 1, int(math.floor(x1 / C)) - self.gx0)
        az, bz = max(0, int(math.floor(z0 / C)) - self.gz0), min(self.h - 1, int(math.floor(z1 / C)) - self.gz0)
        if ax > bx or az > bz:
            return self.ids[:0]
        parts = [self.ids[self.start[gx * self.h + az]:self.start[gx * self.h + bz + 1]] for gx in range(ax, bx + 1)]
        got = np.concatenate(parts) if len(parts) > 1 else parts[0]
        return np.unique(got) if len(got) else got


def way_samples(pts, arc, step=STEP):
    """Sample points at step/2, 3 step/2, ... along a densified way: arrays of arc, x, z and the unit tangent."""
    import numpy as np
    L = arc[-1]
    n = int(L // step)
    if n < 1:
        s = np.array([L / 2])
    else:
        s = (np.arange(n) + 0.5) * (L / n)
    a = np.asarray(arc)
    P = np.asarray(pts, dtype=np.float64)
    j = np.clip(np.searchsorted(a, s, side='right') - 1, 0, len(a) - 2)
    seg = a[j + 1] - a[j]
    t = np.where(seg > 0, (s - a[j]) / np.where(seg > 0, seg, 1), 0)
    d = P[j + 1] - P[j]
    x = P[j, 0] + d[:, 0] * t
    z = P[j, 1] + d[:, 1] * t
    ln = np.hypot(d[:, 0], d[:, 1])
    ln[ln == 0] = 1
    return s, x, z, d[:, 0] / ln, d[:, 1] / ln


def cast(grid, x, z, tx, tz, reach=REACH, chunk=48):
    """The first wall on either side of each sample, square to the way: (right, left) distances, inf where none in
    reach. Right is the page's side +1, the normal (-tz, tx)."""
    np = grid.np
    n = len(x)
    right = np.full(n, np.inf)
    left = np.full(n, np.inf)
    nx, nz = -tz, tx
    for i0 in range(0, n, chunk):
        sl = slice(i0, min(n, i0 + chunk))
        px, pz = x[sl], z[sl]
        ids = grid.near(px.min() - reach, px.max() + reach, pz.min() - reach, pz.max() + reach)
        if not len(ids):
            continue
        S = grid.segs[ids]
        ex, ez = S[:, 2] - S[:, 0], S[:, 3] - S[:, 1]
        # P + t N = A + u E, one line for both sides: t over 0 is the right side, under 0 the left
        den = nx[sl, None] * ez[None, :] - nz[sl, None] * ex[None, :]
        wx, wz = S[None, :, 0] - px[:, None], S[None, :, 1] - pz[:, None]
        with np.errstate(divide='ignore', invalid='ignore'):
            t = (wx * ez[None, :] - wz * ex[None, :]) / den
            u = (wx * nz[sl, None] - wz * nx[sl, None]) / den
        ok = (np.abs(den) > 1e-12) & (u >= 0) & (u <= 1) & (np.abs(t) <= reach)
        right[sl] = np.where(ok & (t > 0), t, np.inf).min(axis=1)
        left[sl] = np.where(ok & (t < 0), -t, np.inf).min(axis=1)
    return right, left


def way_cuts(ways, dense, arcl):
    """Where each way is cut into intervals, in plan: where another way's end meets its middle (the page's cutsOf without
    the height test) and where another way crosses its middle (the page's linker joins no such crossing, so its runs
    carry on through them; the walkers' own graph, peopleCross in app.js, turns at them). A motorway crosses nothing at
    grade and cuts nothing. Per way, the sorted distances along it, none within 1.5 m of its own ends or 1 m of the cut
    before."""
    C = 32.0
    cells = {}
    for wi, pts in enumerate(dense):
        for j in range(len(pts) - 1):
            a, b = pts[j], pts[j + 1]
            for gx in range(int(math.floor((min(a[0], b[0]) - CUT_TOL) / C)), int(math.floor((max(a[0], b[0]) + CUT_TOL) / C)) + 1):
                for gz in range(int(math.floor((min(a[1], b[1]) - CUT_TOL) / C)), int(math.floor((max(a[1], b[1]) + CUT_TOL) / C)) + 1):
                    cells.setdefault((gx, gz), []).append((wi, j))
    cuts = [[] for _ in ways]
    for wi, pts in enumerate(dense):
        if len(pts) < 2 or ways[wi][0] == 0:
            continue
        for e in (pts[0], pts[-1]):
            for qi, j in cells.get((int(math.floor(e[0] / C)), int(math.floor(e[1] / C))), ()):
                if qi == wi:
                    continue
                a, b = dense[qi][j], dense[qi][j + 1]
                dx, dz = b[0] - a[0], b[1] - a[1]
                l2 = dx * dx + dz * dz
                if l2 < 0.01:
                    continue
                t = min(1.0, max(0.0, ((e[0] - a[0]) * dx + (e[1] - a[1]) * dz) / l2))
                s = arcl[qi][j] + t * (arcl[qi][j + 1] - arcl[qi][j])
                if s < 1.5 or s > arcl[qi][-1] - 1.5:
                    continue
                if math.hypot(a[0] + t * dx - e[0], a[1] + t * dz - e[1]) > CUT_TOL:
                    continue
                cuts[qi].append(s)
    for lst in cells.values():
        n = len(lst)
        if n < 2:
            continue
        for i in range(n):
            wi, j = lst[i]
            ca = ways[wi][0]
            a, b = dense[wi][j], dense[wi][j + 1]
            ax, az, bx, bz = a[0], a[1], b[0] - a[0], b[1] - a[1]
            for k in range(i + 1, n):
                qi, m = lst[k]
                if qi == wi:
                    continue
                cb = ways[qi][0]
                if ca == 0 or cb == 0 or (ca < 2 and cb < 2):
                    continue
                c, d = dense[qi][m], dense[qi][m + 1]
                dx, dz = d[0] - c[0], d[1] - c[1]
                den = bx * dz - bz * dx
                if abs(den) < 1e-9:
                    continue
                tt = ((c[0] - ax) * dz - (c[1] - az) * dx) / den
                if tt < 0 or tt > 1:
                    continue
                uu = ((c[0] - ax) * bz - (c[1] - az) * bx) / den
                if uu < 0 or uu > 1:
                    continue
                sa = arcl[wi][j] + tt * (arcl[wi][j + 1] - arcl[wi][j])
                sb = arcl[qi][m] + uu * (arcl[qi][m + 1] - arcl[qi][m])
                if 1.5 <= sa <= arcl[wi][-1] - 1.5:
                    cuts[wi].append(sa)
                if 1.5 <= sb <= arcl[qi][-1] - 1.5:
                    cuts[qi].append(sb)
    out = []
    for c in cuts:
        c.sort()
        keep = []
        for v in c:
            if not keep or v - keep[-1] > 1:
                keep.append(v)
        out.append(keep)
    return out


def code_of(q):
    """A distance in metres (inf for none in reach) as the blob's 6-bit code."""
    if not math.isfinite(q):
        return CODE_NONE
    if q >= CODE_FAR_M:
        return CODE_FAR
    return max(0, min(CODE_FAR - 1, int(math.floor(q * 10 + 1e-9)) - CODE_BASE_DM))


def code_metres(c):
    """The code back as the page reads it: metres from the centreline to the wall (the floor of the measured value)."""
    return math.inf if c == CODE_NONE else CODE_FAR_M if c == CODE_FAR else (CODE_BASE_DM + c) / 10


def interval_value(s, d, lo, hi):
    """One side of one interval: the PCT-th percentile of the samples between lo and hi, the ends trimmed, as a code."""
    import numpy as np
    trim = min(END_TRIM, (hi - lo) / 3)
    m = (s >= lo + trim) & (s <= hi - trim)
    if not m.any():
        m = (s >= lo) & (s <= hi)
    if not m.any():
        return CODE_NONE
    v = np.sort(d[m])
    return code_of(float(v[int(math.floor((len(v) - 1) * PCT / 100))]))


def merge(recs, cls):
    """recs: [[length, R, L], ...] along one way of class cls, R and L codes. Neighbours merge when their codes are
    equal, or when all four are roomy for the class: a wall ROOMY_M or more past the class's drawn half width takes the
    full setback whatever its exact distance, so the page lays the same walk line from the lesser of the two."""
    roomy = min(CODE_FAR, int(round((PARK_HW[cls] + ROOMY_M) * 10)) - CODE_BASE_DM)   # the two open codes are roomy beside any street
    out = []
    for ln, r, l in recs:
        if out:
            p = out[-1]
            if (p[1] == r and p[2] == l) or min(p[1], p[2], r, l) >= roomy:
                p[0] += ln
                p[1], p[2] = min(p[1], r), min(p[2], l)
                continue
        out.append([ln, r, l])
    return out


def measure(ways=None, progress=False):
    """Every way's samples: a list, per way, of None (class 0 or 1, or no length) or (arc, right, left, x, z)."""
    ways = ways or load_ways()
    segs, tiers = load_walls()
    grid = WallGrid(segs)
    out = []
    t0 = time.time()
    for wi, (cls, _, pts) in enumerate(ways):
        if cls < 2 or cls > 5 or len(pts) < 2:
            out.append(None)
            continue
        dp = densify(pts)
        arc = arcs(dp)
        if arc[-1] <= 0:
            out.append(None)
            continue
        s, x, z, tx, tz = way_samples(dp, arc)
        r, l = cast(grid, x, z, tx, tz)
        out.append((s, r, l, x, z))
        if progress and wi % 5000 == 0:
            print('  way %d of %d, %.0f s' % (wi, len(ways), time.time() - t0), flush=True)
    return out


def encode(ways, samples):
    dense = [densify(p) if len(p) > 1 else list(p) for _, _, p in ways]
    arcl = [arcs(p) for p in dense]
    cuts = way_cuts(ways, dense, arcl)
    U = LEN_UNIT_DM / 10
    bitmap = bytearray((len(ways) + 7) // 8)
    lo, hi, lens = bytearray(), bytearray(), bytearray()
    stats = {'raw': 0, 'merged': 0, 'written': 0, 'ways': 0}
    for wi, sm in enumerate(samples):
        if sm is None:
            continue
        s, r, l = sm[0], sm[1], sm[2]
        stops = [0.0] + cuts[wi] + [arcl[wi][-1]]
        recs = [[stops[k + 1] - stops[k], interval_value(s, r, stops[k], stops[k + 1]), interval_value(s, l, stops[k], stops[k + 1])] for k in range(len(stops) - 1)]
        stats['raw'] += len(recs)
        recs = merge(recs, ways[wi][0])
        stats['merged'] += len(recs)
        # the boundaries to whole units, each rounded from the way's start so they never drift; an interval that rounds
        # to nothing hands its codes to the next (the lesser of each), and one over 255 units is written as two
        out, pos, end, carry = [], 0, 0.0, None
        for k, (ln, rr, ll) in enumerate(recs):
            if carry:
                rr, ll = min(rr, carry[0]), min(ll, carry[1])
                carry = None
            if k == len(recs) - 1:
                out.append((rr, ll, None))
                break
            end += ln
            u = int(round(end / U)) - pos
            if u < 1:
                carry = (rr, ll)
                continue
            pos += u
            while u > 255:
                out.append((rr, ll, 255))
                u -= 255
            out.append((rr, ll, u))
        bitmap[wi >> 3] |= 1 << (wi & 7)
        for k, (rr, ll, u) in enumerate(out):
            v = rr | ll << 6 | (0x1000 if u is None else 0)
            lo.append(v & 255)
            hi.append(v >> 8)
            if u is not None:
                lens.append(u)
        stats['written'] += len(out)
        stats['ways'] += 1
    hdr = struct.pack('<4i', MAGIC, len(ways), stats['written'], LEN_UNIT_DM | PCT << 8 | CODE_BASE_DM << 16)
    return hdr + bytes(bitmap) + bytes(lo) + bytes(hi) + bytes(lens), stats


def decode(raw):
    """The blob back: per way, [] or [(start, end or None, R code, L code), ...], metres along the way (the reference
    for the page's peopleBlob())."""
    magic, nw, nrec, params = struct.unpack('<4i', raw[:16])
    if magic != MAGIC:
        raise ValueError('bad magic')
    U = (params & 255) / 10
    nb = (nw + 7) // 8
    bitmap, lo, hi, lens = raw[16:16 + nb], raw[16 + nb:16 + nb + nrec], raw[16 + nb + nrec:16 + nb + 2 * nrec], raw[16 + nb + 2 * nrec:]
    out, k, kl = [], 0, 0
    for wi in range(nw):
        rec = []
        if bitmap[wi >> 3] >> (wi & 7) & 1:
            pos = 0
            while True:
                v = lo[k] | hi[k] << 8
                k += 1
                if v & 0x1000:
                    rec.append((pos * U, None, v & 63, v >> 6 & 63))
                    break
                rec.append((pos * U, (pos + lens[kl]) * U, v & 63, v >> 6 & 63))
                pos += lens[kl]
                kl += 1
        out.append(rec)
    if k != nrec or kl != len(lens):
        raise ValueError('the record count and the body disagree')
    return out


def lookup(recs, s0, s1, side):
    """The reference for the page's peopleClearCode(): the least code among the intervals that the stretch s0..s1 of
    the way overlaps, the stretch drawn in by LOOK_TRIM at each end (to its middle at most) so a neighbour it only
    touches is not read. CODE_NONE for a way with no records."""
    if not recs:
        return CODE_NONE
    t = min(LOOK_TRIM, (s1 - s0) / 2)
    a, b = s0 + t, s1 - t
    best = CODE_NONE
    for st, en, r, l in recs:
        if st <= b and (en is None or en > a):
            best = min(best, r if side > 0 else l)
    return best


def main():
    t0 = time.time()
    ways = load_ways()
    print('measuring %d ways against the walls' % len(ways), flush=True)
    samples = measure(ways, progress=True)
    raw, stats = encode(ways, samples)
    out = HERE / 'people_walk.b64'
    out.write_text(base64.b64encode(raw).decode('ascii'))
    import gzip
    print('people_walk.b64: %d ways with intervals, %d intervals before merging, %d written, %d bytes raw, %d base64, %d gzip of the base64, %.0f s'
          % (stats['ways'], stats['raw'], stats['written'], len(raw), len(base64.b64encode(raw)), len(gzip.compress(base64.b64encode(raw), 9)), time.time() - t0))


if __name__ == '__main__':
    main()
