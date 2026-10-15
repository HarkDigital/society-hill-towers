#!/usr/bin/env python3
"""Bake the Society Hill Towers' concrete (Round 195; fetch_sht_art.py made the candidates) into sht_art.json, which
build.py inlines as SHT_ART, and the picture itself into art/sht/ (a file the page loads on demand, a phone's copy at
half; art_files.py).

The page draws the towers' grid, reveals, glass and rooms itself (the facade shader's ray-cast, app.js 'Casting the
concrete grid'); the picture is only the grain of the concrete, laid by the face's own metres on every concrete surface
and divided by its own linear mean, so a wall keeps its calibrated colour and takes the texture's detail. So it is made
flat before it is made to tile: the picture's broad light (anything wider than about a fifth of it) is divided out, then
it is blended with a half-rolled copy of itself at the edges (bake_wall_art.tileable), so the tile repeats with no seam.

Usage: python3 bake_sht_art.py [--pick concrete-b]"""
import argparse, json, os, sys
import art_files
import numpy as np
from PIL import Image, ImageFilter
from bake_wall_art import tileable, lin_mean

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'sht_art_raw')
OUT = os.path.join(HERE, 'sht_art.json')
N = 1024
TILE_M = 4.0   # what the picture shows across, in metres (its prompt)


def flatten(im):
    """The picture over its own broad light, at its mean: a gradient or a vignette in the generated picture would repeat
    at every tile as a band."""
    a = np.asarray(im, np.float32)
    blur = np.asarray(im.filter(ImageFilter.GaussianBlur(N / 5)), np.float32)
    out = a / np.maximum(blur, 1.0) * a.reshape(-1, 3).mean(0)
    return np.clip(out, 0, 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pick', default='concrete-b')
    a = ap.parse_args()
    src = os.path.join(RAW, a.pick + '.png')
    if not os.path.exists(src):
        sys.exit('no %s: run fetch_sht_art.py first' % src)
    im = Image.open(src).convert('RGB').resize((N, N), Image.LANCZOS)
    t = tileable(flatten(im))
    tile = Image.fromarray(np.clip(t + 0.5, 0, 255).astype(np.uint8))
    out = {'v': 1, 'note': 'Round 195: the Society Hill Towers\' concrete (fetch_sht_art.py, bake_sht_art.py). img a tile '
           'tileM metres across, imgHalf a phone\'s copy, mean its linear mean colour (the page divides it out).'}
    out['concrete'] = {
        'id': a.pick,
        'img': art_files.write(tile, 'sht', 'concrete', 'WEBP', quality=86, method=6),
        'imgHalf': art_files.write(tile.resize((N // 2, N // 2), Image.LANCZOS), 'sht', 'concrete-half', 'WEBP', quality=84, method=6),
        'mean': lin_mean(np.asarray(tile, np.float32)),
        'tileM': TILE_M,
    }
    gone = art_files.prune('sht')
    json.dump(out, open(OUT, 'w'), indent=1)
    c = out['concrete']
    print('%s: %s (%d KB), %s (%d KB), mean %s, %g m a tile; %d old file(s) pruned' % (
        a.pick, c['img'], art_files.size(c['img']) // 1024, c['imgHalf'], art_files.size(c['imgHalf']) // 1024, c['mean'], TILE_M, gone))


if __name__ == '__main__':
    main()
