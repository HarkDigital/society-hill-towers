#!/usr/bin/env python3
"""Bake the walls' and the pitched roofs' materials (fetch_wall_art.py) into wall_art.json, which build.py inlines as
WALL_ART, and the atlases themselves into art/walls/ (files the page loads on demand, a phone's copy at half; art_files.py).

A coursed material (brick, ashlar, marble, granite, slate, shingle) cannot take the ground's half-roll blend: its joints
would double across the blend band. So each is cut on its own courses: the mortar lines are found from the row profile
(the course period by autocorrelation, the mortar's phase as the most extreme fold of it), the image is cropped from one
mortar centre to another an even number of courses down, and every course is cut between two of its own vertical joints
a common width apart, stretched the few per cent it takes to meet that width. Every edge of the tile is then a joint and
the tile repeats with no seam in the pattern. The rest (render, Formstone, concrete, standing-seam metal across its seams,
the snow) take the half-roll blend. A tile's size in metres follows from the measured course: a brick course is 7.5 cm,
a block or a slate course its prompt's size.

The walls are one 3 by 3 atlas (each cell padded with its own wrapped edge, so mips and filtering never meet a
neighbour), the pitched roofs a 2 by 2 one, the snow its own tile; with each kind's linear mean colour, which the page
divides out so a wall keeps its calibrated colour and takes only the texture's grain."""
import json, os, sys
import art_files
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'wall_art_raw')
OUT = os.path.join(HERE, 'wall_art.json')
N = 1024
# (id, the size of one course in metres or None for an uncoursed material, None or 'x' to cut only across)
WALLS = [('wall_brick_red', 0.075), ('wall_brick_dark', 0.075), ('wall_brick_painted', 0.075), ('wall_stucco', None),
         ('wall_ashlar', 0.6), ('wall_formstone', 0.16), ('wall_marble', 0.6), ('wall_granite', 0.5), ('wall_concrete', None)]
# what an uncoursed image shows across, in metres (its prompt)
SPAN = {'wall_stucco': 3.0, 'wall_formstone': 2.4, 'wall_concrete': 3.0, 'pitch_metal': 4.0, 'roof_snow': 8.0}
PITCHED = [('pitch_shingle', 0.143), ('pitch_slate', 0.2), ('pitch_metal', None), ('pitch_tab', 0.127)]
WALL_CELL, WALL_PAD, WALL_GRID = 640, 32, 3
PITCH_CELL, PITCH_PAD, PITCH_GRID = 1024, 32, 2
LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


def tileable(a):
    """Seamless in x, then in y: a blend with a half-rolled copy, the copy at the edges."""
    for axis in (1, 0):
        n = a.shape[axis]
        r = np.roll(a, n // 2, axis=axis)
        t = np.arange(n, dtype=np.float32)
        w = np.clip(np.minimum(t, n - 1 - t) / (n * 0.22), 0, 1)
        w = w * w * (3 - 2 * w)
        w = w[None, :, None] if axis == 1 else w[:, None, None]
        a = a * w + r * (1 - w)
    return a


def smooth1(p, s):
    """A gaussian blur of a 1D profile (reflected ends)."""
    r = int(3 * s) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(p, r, mode='reflect'), k, mode='same')[r:-r]


def autoperiod(p, lo, hi):
    """The course period of a detrended profile: the first autocorrelation peak within [lo, hi] px that reaches half
    the strongest one there."""
    p = p - p.mean()
    n = len(p)
    f = np.fft.rfft(p, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    ac /= ac[0] + 1e-9
    seg = ac[lo:hi + 1]
    peaks = [i for i in range(1, len(seg) - 1) if seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1]]
    if not peaks:
        return None
    top = max(seg[i] for i in peaks)
    for i in peaks:
        if seg[i] >= 0.5 * top:
            return lo + i
    return None


def extremes(q, sgn, sep, thr):
    """Local extremes of sgn * q over thr, at least sep apart (the stronger kept)."""
    s = sgn * q
    idx = [i for i in range(1, len(s) - 1) if s[i] >= s[i - 1] and s[i] >= s[i + 1] and s[i] > thr]
    idx.sort(key=lambda i: -s[i])
    keep = []
    for i in idx:
        if all(abs(i - j) >= sep for j in keep):
            keep.append(i)
    return sorted(keep)


def course_tile(a, course_m, gid):
    """Cut a coursed image on its own mortar lines and joints; returns (tile, metres across, metres up, report)."""
    L = a @ LUM
    H, W = L.shape
    p = L.mean(axis=1)
    p = p - smooth1(p, 40)
    py = autoperiod(p, 10, 260)
    if not py:
        raise SystemExit('%s: no course period' % gid)
    # the mortar's phase: the fold of the row profile by the period, its most extreme bin, and its sign
    ph = np.zeros(py)
    cnt = np.zeros(py)
    for y in range(H):
        ph[y % py] += p[y]
        cnt[y % py] += 1
    ph /= np.maximum(cnt, 1)
    ph -= ph.mean()
    phi = int(np.argmax(np.abs(ph)))
    sgn = 1.0 if ph[phi] > 0 else -1.0
    # every mortar centre, each refined to the profile's own extreme within a quarter period of where it should be
    ys = []
    y = phi
    while y < H:
        lo, hi = max(0, int(y - py * 0.25)), min(H, int(y + py * 0.25) + 1)
        yy = lo + int(np.argmax(sgn * p[lo:hi]))
        if not ys or yy - ys[-1] > py * 0.5:
            ys.append(yy)
        y = yy + py
    if len(ys) < 3:
        raise SystemExit('%s: %d mortar lines' % (gid, len(ys)))
    n = len(ys) - 1
    if n % 2 and n > 2:
        n -= 1   # an even count of courses, so a running bond's alternation carries across the wrap
    ys = ys[:n + 1]
    # each course's vertical joints, from the column profile of its middle rows
    courses, spans = [], []
    for c in range(n):
        y0, y1 = ys[c], ys[c + 1]
        m0, m1 = int(y0 + (y1 - y0) * 0.3), int(y1 - (y1 - y0) * 0.3)
        q = L[m0:max(m1, m0 + 1)].mean(axis=0)
        q = q - smooth1(q, 12)
        js = extremes(q, sgn, max(6, int(py * 0.9)), 0.6 * np.std(q))
        courses.append((y0, y1, js))
        if len(js) > 1:
            spans.extend(np.diff(js))
    jmed = float(np.median(spans)) if spans else W * 0.1
    Wt = int(W - 1.6 * jmed)
    rows, stretch, fails = [], [], 0
    rng = np.random.default_rng(sum(map(ord, gid)))
    for (y0, y1, js) in courses:
        best = None
        for i, ja in enumerate(js):
            if ja > 2.2 * jmed:
                break
            for jb in js[i + 1:]:
                d = abs((jb - ja) - Wt)
                if best is None or d < best[0]:
                    best = (d, ja, jb)
        band = a[y0:y1]
        if best is None or best[0] > 0.08 * Wt:
            fails += 1
            ja, jb = (W - Wt) // 2, (W - Wt) // 2 + Wt
        else:
            ja, jb = best[1], best[2]
        stretch.append((jb - ja) / Wt)
        im = Image.fromarray(np.clip(band[:, ja:jb], 0, 255).astype(np.uint8)).resize((Wt, y1 - y0), Image.LANCZOS)
        # a course cut on its own joints repeats by itself, so it may be rolled: each by its own amount, or every course
        # would carry its cut joint at the tile's edge, a stack joint the height of the tile
        rows.append(np.roll(np.asarray(im, np.float32), int(rng.integers(0, Wt)), axis=1))
    tile = np.concatenate(rows, axis=0)
    mx = Wt * course_m / py
    my = n * course_m
    rep = '%s: course %d px, %d courses, joints %.0f px apart, %d of %d courses cut on their joints, stretch %.3f to %.3f, %.2f x %.2f m' % (
        gid, py, n, jmed, n - fails, n, min(stretch), max(stretch), mx, my)
    return tile, mx, my, rep


def blend_axis(a, axis):
    """The half-roll blend along one axis only (a pattern that runs straight along it, so the rolled copy meets itself)."""
    n = a.shape[axis]
    r = np.roll(a, n // 2, axis=axis)
    t = np.arange(n, dtype=np.float32)
    w = np.clip(np.minimum(t, n - 1 - t) / (n * 0.22), 0, 1)
    w = w * w * (3 - 2 * w)
    w = w[None, :, None] if axis == 1 else w[:, None, None]
    return a * w + r * (1 - w)


def period_crop(a, axis, lo, hi):
    """Crop along an axis from one feature line (a seam, a board joint) to another a whole number of periods on: the
    period by autocorrelation of the profile across it, the line's phase as the most extreme fold. Returns the crop and
    the count of periods, or (a, 0) when the image has no period there."""
    L = a @ LUM
    q = L.mean(axis=1 - axis)
    q = q - smooth1(q, 30)
    pp = autoperiod(q, lo, hi)
    if not pp:
        return a, 0, 0
    n = len(q)
    ph = np.zeros(pp)
    for i in range(n):
        ph[i % pp] += q[i]
    ph -= ph.mean()
    phi = int(np.argmax(np.abs(ph)))
    k = (n - 1 - phi) // pp
    sl = [slice(None), slice(None)]
    sl[axis] = slice(phi, phi + k * pp)
    return a[tuple(sl)], k, pp


def lined_tile(a, gid, span_m):
    """Standing seams (lines both ways: the seams up the slope and the panel joints across) are cut on their own lines
    both ways and need no blend; board-formed concrete is cut on its board lines up and blended along them."""
    W0, H0 = a.shape[1], a.shape[0]
    if gid == 'pitch_metal':
        b, kx, px = period_crop(a, 1, 30, 400)
        b, ky, py = period_crop(b, 0, 60, 600)
        if not kx:
            b = blend_axis(b, 1)
        if not ky:
            b = blend_axis(b, 0)
    else:
        b, ky, py = period_crop(a, 0, 20, 300)
        kx, px = 0, 0
        b = blend_axis(b, 1)
        if not ky:
            b = blend_axis(b, 0)
    mx = span_m * b.shape[1] / W0
    my = span_m * b.shape[0] / W0
    return b, mx, my, '%s: %d x %d lines (%d, %d px), %.2f x %.2f m' % (gid, kx, ky, px, py, mx, my)


def lin_mean(a):
    lin = np.clip(a, 0, 255) / 255.0
    lin = np.where(lin <= 0.04045, lin / 12.92, ((lin + 0.055) / 1.055) ** 2.4)
    return [round(float(v), 5) for v in lin.reshape(-1, 3).mean(0)]


def make_kind(gid, course_m):
    p = os.path.join(RAW, gid + '.png')
    if not os.path.exists(p):
        sys.exit('no %s (run fetch_wall_art.py)' % p)
    a = np.asarray(Image.open(p).convert('RGB').resize((N, N), Image.LANCZOS), np.float32)
    if course_m:
        return course_tile(a, course_m, gid)
    if gid in ('pitch_metal', 'wall_concrete'):
        return lined_tile(a, gid, SPAN[gid])
    return tileable(a), SPAN[gid], SPAN[gid], '%s: blended, %.1f m' % (gid, SPAN[gid])


def atlas(kinds, cell, pad, grid, name, out, key):
    inner = cell - 2 * pad
    A = np.zeros((grid * cell, grid * cell, 3), np.float32)
    means, metres = [], []
    for k, (gid, course_m) in enumerate(kinds):
        t, mx, my, rep = make_kind(gid, course_m)
        print(rep)
        t = np.asarray(Image.fromarray(np.clip(t, 0, 255).astype(np.uint8)).resize((inner, inner), Image.LANCZOS), np.float32)
        Image.fromarray(np.clip(np.concatenate([t, t], 1), 0, 255).astype(np.uint8)).save(os.path.join(RAW, gid + '-tile2.png'))   # a look at the wrap
        means.append(lin_mean(t))
        metres.append([round(mx, 3), round(my, 3)])
        c = np.pad(t, ((pad, pad), (pad, pad), (0, 0)), mode='wrap')
        y0, x0 = (k // grid) * cell, (k % grid) * cell
        A[y0:y0 + cell, x0:x0 + cell] = c
    im = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
    out[key] = art_files.write(im, 'walls', name, 'WEBP', quality=84, method=6)
    out[key + 'Half'] = art_files.write(im.resize((grid * cell // 2, grid * cell // 2), Image.LANCZOS), 'walls', name + '-half', 'WEBP', quality=82, method=6)
    out[key + 'Kinds'] = [g.split('_', 1)[1] for g, _ in kinds]
    out[key + 'Mean'] = means
    out[key + 'M'] = metres
    out[key + 'Pad'] = pad / cell
    out[key + 'Grid'] = grid
    print('%-7s atlas %d KB, half %d KB' % (name, art_files.size(out[key]) // 1024, art_files.size(out[key + 'Half']) // 1024))


def main():
    out = {}
    atlas(WALLS, WALL_CELL, WALL_PAD, WALL_GRID, 'walls', out, 'walls')
    atlas(PITCHED, PITCH_CELL, PITCH_PAD, PITCH_GRID, 'pitched', out, 'pitched')
    p = os.path.join(RAW, 'roof_snow.png')
    if os.path.exists(p):
        a = tileable(np.asarray(Image.open(p).convert('RGB').resize((N, N), Image.LANCZOS), np.float32))
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        out['snow'] = art_files.write(im, 'walls', 'roof-snow', 'WEBP', quality=80, method=6)
        out['snowHalf'] = art_files.write(im.resize((N // 2, N // 2), Image.LANCZOS), 'walls', 'roof-snow-half', 'WEBP', quality=80, method=6)
        out['snowMean'] = lin_mean(a)
        out['snowM'] = SPAN['roof_snow']
    print('pruned %d old wall files' % art_files.prune('walls'))
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f KB' % (os.path.getsize(OUT) / 1e3))


if __name__ == '__main__':
    main()
