#!/usr/bin/env python3
"""Bake the water's textures (fetch_water_art.py) into water_art.json, which build.py inlines as WATER_ART, and the textures
themselves into art/water/ (files the page loads on demand, a phone's copy at half; art_files.py).

pierdeck, the piers' concrete deck: its slab joints are a regular pattern, which the half-roll blend would double across the
blend band, so it is cropped to a whole number of its own repeats (found by autocorrelation near the expected one) with
the edges cross-faded over 16 px, as bake_ground_art.py does the sidewalk. foam, white water over olive water: no pattern,
so blended with a half-rolled copy across and down. Each is stored as a WebP at 1024 with its linear mean, which the
page divides out so a texture brings detail and never moves the calibrated albedo."""
import json, os, sys
import art_files
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'water_art_raw')
OUT = os.path.join(HERE, 'water_art.json')
N = 1024
SPAN = {'pierdeck': 6.0, 'foam': 6.0}       # what each prompt shows across, metres
REPEAT = {'pierdeck': (370, 510)}            # the deck's slab repeat in px of the 1024 source, the expected one


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


def period(profile, expect):
    lo, hi = int(expect * 0.8), int(expect * 1.25)
    return lo + int(np.argmax(profile[lo:hi + 1]))


def periodic(a, gid):
    """Cropped to whole repeats of the pattern, resized back to N, the edges cross-faded: (image, metres a tile, repeat)."""
    L = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    L = L - L.mean()
    F = np.fft.rfft2(L)
    A = np.fft.irfft2(F * np.conj(F), s=L.shape)
    ex, ey = REPEAT[gid]
    px, py = period(A[0, :], ex), period(A[:, 0], ey)
    H, W = L.shape
    cw, ch = max(1, W // px) * px, max(1, H // py) * py
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
    return b, round(cw / W * SPAN[gid], 3), (px, py, cw // px, ch // py)


def lin_mean(a):
    v = np.clip(a, 0, 255) / 255.0
    v = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return [round(float(x), 5) for x in v.reshape(-1, 3).mean(0)]


def main():
    out, metres, means = {}, {}, {}
    for gid in ('pierdeck', 'foam'):
        p = os.path.join(RAW, gid + '.png')
        if not os.path.exists(p):
            sys.exit('no %s (run fetch_water_art.py)' % p)
        a = np.asarray(Image.open(p).convert('RGB').resize((N, N), Image.LANCZOS), np.float32)
        if gid in REPEAT:
            a, metres[gid], rep = periodic(a, gid)
            print('%-8s repeats %d x %d px, %d x %d of them, %.2f m a tile' % ((gid,) + rep + (metres[gid],)))
        else:
            a = tileable(a)
            metres[gid] = SPAN[gid]
        means[gid] = lin_mean(a)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        out[gid] = art_files.write(im, 'water', gid, 'WEBP', quality=80, method=6)
        out[gid + 'Half'] = art_files.write(im.resize((N // 2, N // 2), Image.LANCZOS), 'water', gid + '-half', 'WEBP', quality=80, method=6)
        print('%-8s %d KB, half %d KB, mean %s' % (gid, art_files.size(out[gid]) // 1024, art_files.size(out[gid + 'Half']) // 1024, means[gid]))
    print('pruned %d old water files' % art_files.prune('water'))
    out['m'] = metres
    out['mean'] = means
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f KB' % (os.path.getsize(OUT) / 1e3))


if __name__ == '__main__':
    main()
