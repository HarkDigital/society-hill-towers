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
# the realism round two (R4): each kind's quadrant holds four variants in its own 2 by 2 (variant 0 the Round 185 picture,
# then roof_<kind>_1 to _3 from fetch_ground_art.py), each 432 px made to tile and taken to its kind's linear mean (per
# channel, in linear light), so a far roof, which is its kind's mean, is exactly what it was. A variant is padded with
# its own wrapped edge, ROOF_EXT px on the quadrant's outside, where another kind's albedo lies, and ROOF_INT px toward its
# kind's other variants (one mean, the same surface), so the quadrant's edge holds through mip 7 and a 512 px cell does not
# carry a 64 px pad on every side
ROOF_VARS, ROOF_EXT, ROOF_INT = 4, 64, 16


def roof_var(a, mean, k=4):
    """A variant taken to its kind's linear mean per channel (a few rounds, so what clips at white is made up elsewhere)."""
    lin = np.clip(a, 0, 255) / 255.0
    lin = np.where(lin <= 0.04045, lin / 12.92, ((lin + 0.055) / 1.055) ** 2.4)
    for _ in range(k):
        lin = np.clip(lin * (np.asarray(mean) / np.maximum(lin.reshape(-1, 3).mean(0), 1e-6)), 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055) * 255.0
N = 1024
# the realism pass (ground-vegetation and water's bank findings): the ground's own set, kept apart under 'veg' with each
# image's metres a tile and its linear mean colour (the page takes a texture's detail as a ratio to its mean): the parks'
# broad variation from the air, the woods' canopy by season, the river banks' riprap and the yards behind the rows (the
# tidal mud and the leaf fall are drawn in the shader: a phone's ground program has no texture units to spare)
VEG = {'parkmacro': 240.0, 'canopy_summer': 70.0, 'canopy_autumn': 70.0, 'canopy_winter': 70.0, 'riprap': 6.0,
       'alley': 10.0, 'snow': 6.5}
# the realism round two (D8): the lying snow (fetch_ground_art.py made it in the first pass and it stayed raw "for want of
# texture units"); the page lays it through the alley's sampler on the bare ground's program while snow lies, so it takes
# no unit of its own, and only as a ratio to its own mean, so the snow keeps the weather's calibrated white


def lin_mean(a):
    lin = np.clip(a, 0, 255) / 255.0
    lin = np.where(lin <= 0.04045, lin / 12.92, ((lin + 0.055) / 1.055) ** 2.4)
    return [round(float(v), 5) for v in lin.reshape(-1, 3).mean(0)]


def tileable(a, quiet=False):
    """Seamless in x, then in y: a blend with a half-rolled copy, the copy at the edges. quiet (the realism round two's
    roof variants): the copy rolled by whatever share between a quarter and three quarters lays the least of the picture's
    own features in the edge band, where the copy shows (the half roll lays a drain in the middle again at the edge, so a
    tile carried two)."""
    for axis in (1, 0):
        n = a.shape[axis]
        t = np.arange(n, dtype=np.float32)
        w = np.clip(np.minimum(t, n - 1 - t) / (n * 0.22), 0, 1)
        w = w * w * (3 - 2 * w)
        s = n // 2
        if quiet:
            # a feature: the 2% of pixels farthest from their own 31 px neighbourhood (a drain's ring, a stain's edge, a
            # patch's lap), counted along each column (row)
            L = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            B = L.copy()
            for ax in (0, 1):
                m = B.shape[ax]
                c = np.cumsum(np.concatenate([B.take(range(-15, 0), axis=ax), B, B.take(range(0, 15), axis=ax)], axis=ax), axis=ax)
                c = np.concatenate([np.zeros_like(c.take([0], axis=ax)), c], axis=ax)
                B = (c.take(range(31, m + 31), axis=ax) - c.take(range(0, m), axis=ax)) / 31.0
            D = np.abs(L - B)
            f = (D > np.quantile(D, 0.98)).sum(axis=0 if axis == 1 else 1).astype(np.float64)
            cost = [float(((1 - w) * np.roll(f, k)).sum()) for k in range(n // 4, 3 * n // 4 + 1)]
            s = n // 4 + int(np.argmin(cost))
        r = np.roll(a, s, axis=axis)
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
    roofs = [os.path.join(RAW, r + ('_%d' % v if v else '') + '.png') for r in ROOFS for v in range(ROOF_VARS)]
    if all(os.path.exists(p) for p in roofs):
        inner = ROOF_CELL // 2 - ROOF_EXT - ROOF_INT
        atlas = np.zeros((2 * ROOF_CELL, 2 * ROOF_CELL, 3), np.float32)
        means = []
        for k in range(len(ROOFS)):
            for v in range(ROOF_VARS):
                src = Image.open(roofs[k * ROOF_VARS + v]).convert('RGB')
                if v == 0:   # the kind's mean as Round 185 took it (its picture at 960), so the manifest's four are unchanged
                    means.append(lin_mean(tileable(np.asarray(src.resize((ROOF_CELL - 2 * ROOF_PAD,) * 2, Image.LANCZOS), np.float32))))
                a = roof_var(tileable(np.asarray(src.resize((inner, inner), Image.LANCZOS), np.float32), quiet=v > 0), means[k])
                # the quadrant's outside takes the wide pad, the side toward the kind's other variants the narrow one
                cx, cy = v % 2, v // 2
                cell = np.pad(a, ((ROOF_INT if cy else ROOF_EXT, ROOF_EXT if cy else ROOF_INT), (ROOF_INT if cx else ROOF_EXT, ROOF_EXT if cx else ROOF_INT), (0, 0)), mode='wrap')
                y0, x0 = (k // 2) * ROOF_CELL + cy * (ROOF_CELL // 2), (k % 2) * ROOF_CELL + cx * (ROOF_CELL // 2)
                atlas[y0:y0 + ROOF_CELL // 2, x0:x0 + ROOF_CELL // 2] = cell
                print('roof %-7s variant %d mean %s (its kind %s)' % (ROOFS[k][5:], v, lin_mean(a), means[k]))
        im = Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8))
        out['roofs'] = art_files.write(im, 'ground', 'roofs', 'WEBP', quality=82, method=6)
        out['roofsHalf'] = art_files.write(im.resize((ROOF_CELL, ROOF_CELL), Image.LANCZOS), 'ground', 'roofs-half', 'WEBP', quality=80, method=6)
        out['roofKinds'] = [r[5:] for r in ROOFS]
        out['roofMean'] = means
        out['roofPad'] = [ROOF_EXT / ROOF_CELL, ROOF_INT / ROOF_CELL]   # shares of a kind's quadrant: its outside, between its variants
        metres['roof'] = ROOF_M
        print('roofs    atlas %d KB, half %d KB, means %s' % (art_files.size(out['roofs']) // 1024, art_files.size(out['roofsHalf']) // 1024, means))
    else:
        print('roofs    missing %s (run fetch_ground_art.py): the page goes without them' % ', '.join(os.path.basename(p) for p in roofs if not os.path.exists(p)))
    veg = {}
    for gid, mt in VEG.items():
        p = os.path.join(RAW, gid + '.png')
        if not os.path.exists(p):
            print('%-14s missing (run fetch_ground_art.py --only %s): the page goes without it' % (gid, gid))
            continue
        a = tileable(np.asarray(Image.open(p).convert('RGB').resize((N, N), Image.LANCZOS), np.float32))
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        fn = gid.replace('_', '-')   # a file's name is lower case, digits and hyphens (tests/test_art_files.py)
        veg[gid] = {'img': art_files.write(im, 'ground', fn, 'WEBP', quality=80, method=6),
                    'imgHalf': art_files.write(im.resize((N // 2, N // 2), Image.LANCZOS), 'ground', fn + '-half', 'WEBP', quality=80, method=6),
                    'm': mt, 'mean': lin_mean(a)}
        print('%-14s %d KB, half %d KB, %g m a tile' % (gid, art_files.size(veg[gid]['img']) // 1024, art_files.size(veg[gid]['imgHalf']) // 1024, mt))
    out['veg'] = veg
    print('pruned %d old ground files' % art_files.prune('ground'))
    out['m'] = {k: round(v, 3) for k, v in metres.items()}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f MB' % (os.path.getsize(OUT) / 1e6))


if __name__ == '__main__':
    main()
