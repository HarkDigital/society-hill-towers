#!/usr/bin/env python3
"""Bake the Moshulu's textures (fetch_moshulu_art.py, Round 195) into moshulu_art.json, which build.py inlines as MOSHULU_ART,
and the textures themselves into art/moshulu/ (files the page loads on demand when the eye comes near her, a phone's copy at
half; art_files.py).

Both pictures are rows: the hull's riveted strakes and the deck's planks run left to right. So each is cropped down the
frame to a whole number of its own rows (found by autocorrelation near the expected pitch), which makes it repeat up and
down exactly, and its left and right edges are cross-faded over a narrow band, where a plate's or a plank's middle meets
another's and no seam is doubled (a half-roll blend would ghost the butt joints across the frame). Each is stored as a
WebP at 1024 with its linear mean, which the page divides out, so a texture brings the plates, rivets, seams and
weathering and never moves the calibrated paint or teak; and with the metres it spans along and up the hull (or across the
deck), from the rows' pitch: a hull strake of 1.3 m, a deck plank of 15 cm, each stretched along the run so a plate or a
plank is as long as the real ones."""
import json, os, sys
import art_files
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'moshulu_art_raw')
OUT = os.path.join(HERE, 'moshulu_art.json')
N = 1024
ROW = {'hull': (256, 1.3), 'deck': (54, 0.15)}       # the expected row pitch in px of the 1024 source, and a row's metres
STRETCH = {'hull': 1.5, 'deck': 2.0}                 # a tile's width over its height: plates 3 to 5 m long, planks 4 to 8 m
EDGE = 24                                           # px of the left and right cross-fade


def rows(a, expect):
    """The row pitch in px, from the autocorrelation of the luminance down the frame, and its phase: the first seam (the
    darkest row of the frame's mean profile, summed over every repeat), where the crop starts, so the tile's own top and
    bottom edges fall on a seam and a plate or a plank is never cut through its middle."""
    L = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    prof = L.mean(axis=1)
    L = L - L.mean(axis=0, keepdims=True)
    F = np.fft.rfft(L, axis=0)
    A = np.fft.irfft(F * np.conj(F), n=L.shape[0], axis=0).mean(axis=1)
    lo, hi = int(expect * 0.8), int(expect * 1.25)
    py = lo + int(np.argmax(A[lo:hi + 1]))
    n = len(prof)
    phase = int(np.argmin([prof[ph:n:py][:max(1, (n - ph) // py)].mean() for ph in range(py)]))
    return py, phase


def bake(gid):
    p = os.path.join(RAW, gid + '.png')
    if not os.path.exists(p):
        sys.exit('no %s (run fetch_moshulu_art.py)' % p)
    a = np.asarray(Image.open(p).convert('RGB').resize((N, N), Image.LANCZOS), np.float32)
    expect, metres = ROW[gid]
    py, y0 = rows(a, expect)
    n = max(1, (N - y0) // py)
    ch = n * py
    b = np.asarray(Image.fromarray(np.clip(a[y0:y0 + ch], 0, 255).astype(np.uint8)).resize((N, N), Image.LANCZOS), np.float32)
    w = np.linspace(0.5, 0.0, EDGE)[None, :, None]
    left, right = b[:, :EDGE].copy(), b[:, -EDGE:][:, ::-1].copy()
    b[:, :EDGE] = left * (1 - w) + right * w
    b[:, -EDGE:] = (right * (1 - w) + left * w)[:, ::-1]
    up = round(n * metres, 3)
    return b, {'rows': n, 'pitch': py, 'phase': y0, 'up': up, 'along': round(up * STRETCH[gid], 3)}


def lin_mean(a):
    v = np.clip(a, 0, 255) / 255.0
    v = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return [round(float(x), 5) for x in v.reshape(-1, 3).mean(0)]


def main():
    out, metres, means = {}, {}, {}
    for gid in ('hull', 'deck'):
        a, info = bake(gid)
        metres[gid] = [info['along'], info['up']]
        means[gid] = lin_mean(a)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        out[gid] = art_files.write(im, 'moshulu', gid, 'WEBP', quality=82, method=6)
        out[gid + 'Half'] = art_files.write(im.resize((N // 2, N // 2), Image.LANCZOS), 'moshulu', gid + '-half', 'WEBP', quality=82, method=6)
        print('%-5s %d rows of %d px from %d, a tile %.2f m along by %.2f m, %d KB, half %d KB, mean %s' % (
            gid, info['rows'], info['pitch'], info['phase'], info['along'], info['up'], art_files.size(out[gid]) // 1024,
            art_files.size(out[gid + 'Half']) // 1024, means[gid]))
    print('pruned %d old moshulu files' % art_files.prune('moshulu'))
    out['m'] = metres
    out['mean'] = means
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f KB' % (os.path.getsize(OUT) / 1e3))


if __name__ == '__main__':
    main()
