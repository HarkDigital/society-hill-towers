#!/usr/bin/env python3
"""Bake the ground's textures (fetch_ground_art.py) into ground_art.json, which build.py inlines as GROUND_ART.

Each generated image is made to tile: blended across with a copy rolled half its width (the copy at the edges, the
original in the middle, where the copy's own seam lies), then down the same way, so no seam is left anywhere; then
stored as a WebP at 1024. The page samples it where it sampled the painted meadow tile (6.5 m a repeat) and matches its
mean brightness to the painted tile's, so the scene's calibrated balance holds."""
import base64, io, json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'ground_art_raw')
OUT = os.path.join(HERE, 'ground_art.json')
IDS = ('lawn', 'meadow')
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


def main():
    out = {}
    for gid in IDS:
        p = os.path.join(RAW, gid + '.png')
        if not os.path.exists(p):
            sys.exit('no %s (run fetch_ground_art.py)' % p)
        a = np.asarray(Image.open(p).convert('RGB').resize((N, N), Image.LANCZOS), np.float32)
        a = tileable(a)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        b = io.BytesIO()
        im.save(b, 'WEBP', quality=80, method=6)
        out[gid] = 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode('ascii')
        print('%-7s %d KB' % (gid, len(b.getvalue()) // 1024))
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f MB' % (os.path.getsize(OUT) / 1e6))


if __name__ == '__main__':
    main()
