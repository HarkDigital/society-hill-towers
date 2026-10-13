#!/usr/bin/env python3
"""Bake the ground's textures (fetch_ground_art.py) into ground_art.json, which build.py inlines as GROUND_ART, and the
textures themselves into art/ground/ (Round 184: files the page loads on demand, a phone's copy at half; art_files.py).

Each generated image is made to tile: blended across with a copy rolled half its width (the copy at the edges, the
original in the middle, where the copy's own seam lies), then down the same way, so no seam is left anywhere; then
stored as a WebP at 1024. The page samples it where it sampled the painted meadow tile (6.5 m a repeat) and matches its
mean brightness to the painted tile's, so the scene's calibrated balance holds."""
import base64, io, json, os, sys
import art_files
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'ground_art_raw')
OUT = os.path.join(HERE, 'ground_art.json')
IDS = ('lawn', 'meadow', 'asphalt', 'concrete', 'bricks', 'yard')   # Round 184: the streets' three; Round 185 the yards'
# Round 185, the flat roofs: four kinds in one 2 by 2 atlas, each made to tile, its 960 px padded 32 px a side with its
# own wrapped edge (so bilinear filtering and the first mips never meet a neighbour), with each kind's linear mean colour
# for the page's tinting; a tile is ROOF_M metres
ROOFS = ('roof_tar', 'roof_silver', 'roof_white', 'roof_gravel')
ROOF_CELL, ROOF_PAD, ROOF_M = 1024, 32, 8.0
N = 1024


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


# Round 184: the streets' three. A regular pattern (slab joints, herringbone) cannot take the half-roll blend, which
# doubles every joint across the blend band, so those are cropped to a whole number of their own repeats instead (found
# by autocorrelation near the expected one, in px of the 1024 source), their edges cross-faded over 16 px to close the
# near-repeat; asphalt has no pattern and takes the blend. SPAN is what each image shows across in metres (its prompt),
# and the page lays a tile at m metres (the asphalt half again as large, its grain at 6 m)
SPAN = {'asphalt': 4.0, 'concrete': 3.0, 'bricks': 2.0}
REPEAT = {'concrete': (512, 512), 'bricks': (208, 100)}


def period(profile, expect):
    """The strongest repeat of a 1D autocorrelation within 0.8 to 1.25 times the expected one, in px."""
    lo, hi = int(expect * 0.8), int(expect * 1.25)
    return lo + int(np.argmax(profile[lo:hi + 1]))


def periodic(a, gid):
    L = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    L = L - L.mean()
    F = np.fft.rfft2(L)
    A = np.fft.irfft2(F * np.conj(F), s=L.shape)
    ex, ey = REPEAT[gid]
    px, py = period(A[0, :], ex), period(A[:, 0], ey)
    H, W = L.shape
    cw, ch = (W // px) * px, (H // py) * py
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    b = np.asarray(Image.fromarray(np.clip(a[y0:y0 + ch, x0:x0 + cw], 0, 255).astype(np.uint8)).resize((N, N), Image.LANCZOS), np.float32)
    k = 16
    w = np.linspace(0.5, 0.0, k)[None, :, None]
    left, right = b[:, :k].copy(), b[:, -k:][:, ::-1].copy()
    b[:, :k] = left * (1 - w) + right * w
    b[:, -k:] = (right * (1 - w) + left * w)[:, ::-1]
    w2 = np.linspace(0.5, 0.0, k)[:, None, None]
    top, bot = b[:k].copy(), b[-k:][::-1].copy()
    b[:k] = top * (1 - w2) + bot * w2
    b[-k:] = (bot * (1 - w2) + top * w2)[::-1]
    return b, cw / W * SPAN[gid], (px, py, cw // px, ch // py)


def main():
    out, metres = {}, {}
    for gid in IDS:
        p = os.path.join(RAW, gid + '.png')
        if not os.path.exists(p):
            sys.exit('no %s (run fetch_ground_art.py)' % p)
        a = np.asarray(Image.open(p).convert('RGB').resize((N, N), Image.LANCZOS), np.float32)
        if gid in REPEAT:
            a, metres[gid], rep = periodic(a, gid)
            if gid == 'concrete':
                metres[gid] = 1.5   # the crop holds one joint each way: a tile is one slab, a Philadelphia sidewalk's five feet
            print('%-8s repeats %d x %d px, %d x %d of them, %.2f m a tile' % ((gid,) + rep + (metres[gid],)))
        else:
            a = tileable(a)
            if gid in SPAN:
                metres[gid] = SPAN[gid] * 1.5
            if gid == 'yard':
                metres[gid] = 10.0
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        out[gid] = art_files.write(im, 'ground', gid, 'WEBP', quality=80, method=6)
        out[gid + 'Half'] = art_files.write(im.resize((N // 2, N // 2), Image.LANCZOS), 'ground', gid + '-half', 'WEBP', quality=80, method=6)
        print('%-8s %d KB, half %d KB' % (gid, art_files.size(out[gid]) // 1024, art_files.size(out[gid + 'Half']) // 1024))
    roofs = [p for p in (os.path.join(RAW, r + '.png') for r in ROOFS) if os.path.exists(p)]
    if len(roofs) == len(ROOFS):
        inner = ROOF_CELL - 2 * ROOF_PAD
        atlas = np.zeros((2 * ROOF_CELL, 2 * ROOF_CELL, 3), np.float32)
        means = []
        for k, p in enumerate(roofs):
            a = tileable(np.asarray(Image.open(p).convert('RGB').resize((inner, inner), Image.LANCZOS), np.float32))
            lin = (np.clip(a, 0, 255) / 255.0)
            lin = np.where(lin <= 0.04045, lin / 12.92, ((lin + 0.055) / 1.055) ** 2.4)
            means.append([round(float(v), 5) for v in lin.reshape(-1, 3).mean(0)])
            cell = np.pad(a, ((ROOF_PAD, ROOF_PAD), (ROOF_PAD, ROOF_PAD), (0, 0)), mode='wrap')
            y0, x0 = (k // 2) * ROOF_CELL, (k % 2) * ROOF_CELL
            atlas[y0:y0 + ROOF_CELL, x0:x0 + ROOF_CELL] = cell
        im = Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8))
        out['roofs'] = art_files.write(im, 'ground', 'roofs', 'WEBP', quality=82, method=6)
        out['roofsHalf'] = art_files.write(im.resize((ROOF_CELL, ROOF_CELL), Image.LANCZOS), 'ground', 'roofs-half', 'WEBP', quality=80, method=6)
        out['roofKinds'] = [r[5:] for r in ROOFS]
        out['roofMean'] = means
        out['roofPad'] = ROOF_PAD / ROOF_CELL
        metres['roof'] = ROOF_M
        print('roofs    atlas %d KB, half %d KB, means %s' % (art_files.size(out['roofs']) // 1024, art_files.size(out['roofsHalf']) // 1024, means))
    print('pruned %d old ground files' % art_files.prune('ground'))
    out['m'] = {k: round(v, 3) for k, v in metres.items()}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f MB' % (os.path.getsize(OUT) / 1e6))


if __name__ == '__main__':
    main()
