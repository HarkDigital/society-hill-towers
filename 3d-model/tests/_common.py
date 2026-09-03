"""Shared helpers for the Philly3D test suite.

Stdlib only: the packed blobs are 4-10 MB of base64, so everything decodes through
array/struct (never numpy) and the decoded scenes are cached per process so the
audit tests can share one walk of city.b64 / wide.b64.

Blob formats (from the pack script docstrings, cross-checked against the app.js
decoders named in BLOBS):
  wide.b64 / city.b64  Int32[4] header (magic, nBuildings, nRoads, nAreas), int16 body
      building: n, h*5, minH*5, type, attr, roof, n x (x, z)   (attr/roof absent in the
                legacy 0x53485458 / 0x53485459 formats)
      road:     n, w*10, type, n x (x, z)
      area:     n, kind, n x (x, z)
  trees.b64    header (magic, nTrees, nNames, 0); 4 int16 per tree: x*5, z*5, dbh_in, nameIdx
  poles.b64    header (magic, nPoles, 0, 0);      3 int16 per pole: x/0.7, z/0.7, packed bits
  traffic.b64  header (magic, nWays, nPts, 0);    way: n, clsFlags, aadt/10, n x (x/0.2, z/0.2)
"""
import array
import base64
import collections
import json
import math
import pathlib
import struct
import sys

MODEL = pathlib.Path(__file__).resolve().parents[1]      # .../3d-model (never a hardcoded /Users path)
REPO = MODEL.parent

# file -> (accepted magics, coordinate unit in meters, app.js load step that decodes it)
BLOBS = {
    'wide.b64':    ((0x5348545D, 0x5348545A, 0x53485458), 0.2, 'Raising the outer districts'),   # 0x5348545D: packed roof word
    'city.b64':    ((0x5348545C, 0x5348545B, 0x53485459), 0.7, 'Raising the rest of Philadelphia'),   # 0x5348545C: packed roof word
    'outskirts.b64': ((0x53485459,), 1.0, 'Raising the towns across the line'),   # pack_outskirts.py: no attr words
    'storefronts.b64': ((0x53485446,), 0.2, 'Dressing the storefronts'),   # bake_storefronts.py: 8 int16 per storefront
    'trees.b64':   ((0x53485454,), 0.2, 'Planting the street trees'),
    'poles.b64':   ((0x53485450,), 0.7, 'Lighting the streetlamps'),
    # bake_traffic.py reuses the tree magic 'SHTT' (0x53485454) — both its docstring
    # and the app decoder agree, so that is the "right" magic for this blob.
    'traffic.b64': ((0x53485454,), 0.2, 'Setting the traffic flowing'),
}
INT16_SAT = 32767
WIDE_BOX = (-3700, 2300, -4480, 6400)        # pack_wide.py WIDE (x0, x1, z0, z1)
CITY_BOX = (-12000, 16500, -21700, 9700)     # pack_city.py CITY


# ----------------------------------------------------------------------------- files
def path(name):
    return MODEL / name


def require(tc, *names):
    """skipTest unless every named file exists under 3d-model/."""
    missing = [n for n in names if not (MODEL / n).exists()]
    if missing:
        tc.skipTest('input absent: ' + ', '.join(missing))


_json_cache = {}


def load_json(name):
    if name not in _json_cache:
        _json_cache[name] = json.loads((MODEL / name).read_text(encoding='utf-8'))
    return _json_cache[name]


# ----------------------------------------------------------------------------- blobs
def split_blob(raw):
    """bytes -> (header tuple of 4 int32, int16 array). Raises ValueError on a short/odd blob."""
    if len(raw) < 16:
        raise ValueError('blob shorter than the 16-byte header (%d bytes)' % len(raw))
    if (len(raw) - 16) % 2:
        raise ValueError('int16 body has an odd byte count (%d)' % (len(raw) - 16))
    hdr = struct.unpack_from('<4i', raw, 0)
    body = array.array('h')
    body.frombytes(raw[16:])
    if sys.byteorder == 'big':
        body.byteswap()
    return hdr, body


_blob_cache = {}


def decode_b64(name):
    """(header, int16 body) of a committed .b64 blob, cached per process."""
    if name not in _blob_cache:
        raw = base64.b64decode((MODEL / name).read_text(encoding='ascii').strip())
        _blob_cache[name] = split_blob(raw)
    return _blob_cache[name]


def _count_sat(body, start, count):
    n = 0
    for k in range(start, start + count):
        v = body[k]
        if v == INT16_SAT or v == -INT16_SAT:
            n += 1
    return n


_scene_cache = {}


def walk_scene(name):
    """Walk wide.b64 or city.b64 record by record.

    Returns a dict: header, nb, nr, na, unit, has_attr, leftover (int16 not consumed),
    saturated {'buildings','roads','areas'} (coordinates at +/-32767),
    buildings [(n, h, minH, type, pts)], roads [(n, w, type, pts)], areas [(n, kind, pts)]
    with pts already in meters.
    """
    if name in _scene_cache:
        return _scene_cache[name]
    hdr, body = decode_b64(name)
    magics, unit, _step = BLOBS[name]
    magic, nb, nr, na = hdr
    has_attr = magic in (0x5348545A, 0x5348545B, 0x5348545C, 0x5348545D)
    hs = 6 if has_attr else 4
    i = 0
    L = len(body)
    buildings, roads, areas = [], [], []
    sat = {'buildings': 0, 'roads': 0, 'areas': 0}
    try:
        for _ in range(nb):
            n = body[i]
            p0 = i + hs
            pts = [(body[p0 + 2 * k] * unit, body[p0 + 2 * k + 1] * unit) for k in range(n)]
            sat['buildings'] += _count_sat(body, p0, 2 * n)
            buildings.append((n, body[i + 1] / 5.0, body[i + 2] / 5.0, body[i + 3], pts))
            i = p0 + 2 * n
        for _ in range(nr):
            n = body[i]
            p0 = i + 3
            pts = [(body[p0 + 2 * k] * unit, body[p0 + 2 * k + 1] * unit) for k in range(n)]
            sat['roads'] += _count_sat(body, p0, 2 * n)
            roads.append((n, body[i + 1] / 10.0, body[i + 2], pts))
            i = p0 + 2 * n
        for _ in range(na):
            n = body[i]
            p0 = i + 2
            pts = [(body[p0 + 2 * k] * unit, body[p0 + 2 * k + 1] * unit) for k in range(n)]
            sat['areas'] += _count_sat(body, p0, 2 * n)
            areas.append((n, body[i + 1], pts))
            i = p0 + 2 * n
    except IndexError:
        raise AssertionError('%s: record walk ran past the end of the int16 body at index %d of %d '
                             '(%d/%d buildings, %d/%d roads, %d/%d areas read)'
                             % (name, i, L, len(buildings), nb, len(roads), nr, len(areas), na))
    out = dict(header=hdr, nb=nb, nr=nr, na=na, unit=unit, has_attr=has_attr, leftover=L - i,
               saturated=sat, buildings=buildings, roads=roads, areas=areas)
    _scene_cache[name] = out
    return out


def walk_traffic():
    """traffic.b64 -> dict(header, ways [(n, flags, aadt10, pts m)], consumed, leftover, saturated)."""
    hdr, body = decode_b64('traffic.b64')
    unit = BLOBS['traffic.b64'][1]
    i = 0
    ways = []
    sat = 0
    L = len(body)
    try:
        for _ in range(hdr[1]):
            n, flags, aadt10 = body[i], body[i + 1], body[i + 2]
            p0 = i + 3
            pts = [(body[p0 + 2 * k] * unit, body[p0 + 2 * k + 1] * unit) for k in range(n)]
            sat += _count_sat(body, p0, 2 * n)
            ways.append((n, flags, aadt10, pts))
            i = p0 + 2 * n
    except IndexError:
        raise AssertionError('traffic.b64: way walk ran past the body at index %d of %d' % (i, L))
    return dict(header=hdr, ways=ways, consumed=i, leftover=L - i, saturated=sat)


def walk_trees():
    hdr, body = decode_b64('trees.b64')
    n = hdr[1]
    if len(body) < 4 * n:
        raise AssertionError('trees.b64: body holds %d int16 but the header promises %d trees x 4' % (len(body), n))
    sat = sum(1 for i in range(n) for k in (0, 1) if abs(body[4 * i + k]) == INT16_SAT)
    trees = [(body[4 * i] * 0.2, body[4 * i + 1] * 0.2, body[4 * i + 2], body[4 * i + 3]) for i in range(n)]
    return dict(header=hdr, trees=trees, leftover=len(body) - 4 * n, saturated=sat)


def walk_poles():
    hdr, body = decode_b64('poles.b64')
    n = hdr[1]
    if len(body) < 3 * n:
        raise AssertionError('poles.b64: body holds %d int16 but the header promises %d poles x 3' % (len(body), n))
    sat = sum(1 for i in range(n) for k in (0, 1) if abs(body[3 * i + k]) == INT16_SAT)
    poles = [(body[3 * i] * 0.7, body[3 * i + 1] * 0.7, body[3 * i + 2]) for i in range(n)]
    return dict(header=hdr, poles=poles, leftover=len(body) - 3 * n, saturated=sat)


# -------------------------------------------------------------------------- geometry
def mean_centroid(pts):
    n = len(pts)
    return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n


def ring_area(pts):
    a = 0.0
    for i in range(len(pts)):
        u, v = pts[i], pts[(i + 1) % len(pts)]
        a += u[0] * v[1] - v[0] * u[1]
    return abs(a) / 2.0


def seg_dist(px, pz, ax, az, bx, bz):
    """distance from point to segment ab"""
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz))


def seg_seg_dist(p1x, p1z, p2x, p2z, q1x, q1z, q2x, q2z):
    """exact 2D distance between segments p1-p2 and q1-q2 (0 when they cross)"""
    def cross(ox, oz, ax, az, bx, bz):
        return (ax - ox) * (bz - oz) - (az - oz) * (bx - ox)
    o1 = cross(p1x, p1z, p2x, p2z, q1x, q1z)
    o2 = cross(p1x, p1z, p2x, p2z, q2x, q2z)
    o3 = cross(q1x, q1z, q2x, q2z, p1x, p1z)
    o4 = cross(q1x, q1z, q2x, q2z, p2x, p2z)
    if ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0)):
        return 0.0
    return min(seg_dist(p1x, p1z, q1x, q1z, q2x, q2z), seg_dist(p2x, p2z, q1x, q1z, q2x, q2z),
               seg_dist(q1x, q1z, p1x, p1z, p2x, p2z), seg_dist(q2x, q2z, p1x, p1z, p2x, p2z))


class SegGrid:
    """Uniform-cell spatial index over segments; each segment is registered in every
    cell its (padded) bbox touches, so a single-cell lookup at a point finds every
    segment whose padded band can contain that point."""

    def __init__(self, cell):
        self.cell = float(cell)
        self.cells = collections.defaultdict(list)
        self.segs = []

    def add(self, ax, az, bx, bz, pad, payload=None):
        idx = len(self.segs)
        self.segs.append((ax, az, bx, bz, payload))
        c = self.cell
        for gx in range(int(math.floor((min(ax, bx) - pad) / c)), int(math.floor((max(ax, bx) + pad) / c)) + 1):
            for gz in range(int(math.floor((min(az, bz) - pad) / c)), int(math.floor((max(az, bz) + pad) / c)) + 1):
                self.cells[(gx, gz)].append(idx)
        return idx

    def key(self, x, z):
        return (int(math.floor(x / self.cell)), int(math.floor(z / self.cell)))

    def at(self, x, z):
        return self.cells.get(self.key(x, z), ())

    def bbox_touches(self, x0, x1, z0, z1):
        c = self.cell
        for gx in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for gz in range(int(math.floor(z0 / c)), int(math.floor(z1 / c)) + 1):
                if (gx, gz) in self.cells:
                    return True
        return False

    def in_bbox(self, x0, x1, z0, z1):
        c = self.cell
        out = set()
        for gx in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for gz in range(int(math.floor(z0 / c)), int(math.floor(z1 / c)) + 1):
                out.update(self.cells.get((gx, gz), ()))
        return out


# ------------------------------------------------------------------------------- DEM
def grid_extent(g):
    return (g['x0'], g['x0'] + (g['nx'] - 1) * g['cell'], g['z0'], g['z0'] + (g['nz'] - 1) * g['cell'])


def bilinear(g, x, z):
    """Bilinear sample of a {x0, z0, cell, nx, nz, rows} grid; None outside or at a null corner."""
    fx = (x - g['x0']) / g['cell']
    fz = (z - g['z0']) / g['cell']
    if fx < 0 or fz < 0 or fx > g['nx'] - 1 or fz > g['nz'] - 1:
        return None
    i = max(0, min(g['nx'] - 2, int(fx)))
    j = max(0, min(g['nz'] - 2, int(fz)))
    tx = max(0.0, min(1.0, fx - i))
    tz = max(0.0, min(1.0, fz - j))
    r0, r1 = g['rows'][j], g['rows'][j + 1]
    c = (r0[i], r0[i + 1], r1[i], r1[i + 1])
    if any(v is None for v in c):
        return None
    a = c[0] * (1 - tx) + c[1] * tx
    b = c[2] * (1 - tx) + c[3] * tx
    return a * (1 - tz) + b * tz


def percentile(sorted_vals, q):
    if not sorted_vals:
        return None
    k = min(len(sorted_vals) - 1, int(round(q * (len(sorted_vals) - 1))))
    return sorted_vals[k]


# ------------------------------------------------------------------------ overpasses
def chain_segments(ov, kinds=('el',), min_class=None, max_class=None):
    """Flatten overpasses.json chains into (ax, az, bx, bz, chain) tuples."""
    out = []
    for kind in kinds:
        for ch in ov.get(kind, []):
            c = ch.get('c', 0)
            if min_class is not None and c < min_class:
                continue
            if max_class is not None and c > max_class:
                continue
            p = ch['p']
            for a, b in zip(p, p[1:]):
                out.append((a[0], a[1], b[0], b[1], ch))
    return out
