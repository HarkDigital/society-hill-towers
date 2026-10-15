#!/usr/bin/env python3
"""Bake the Comcast towers' cladding (Round 195) into comcast_art.json, which build.py inlines as COMCAST_ART, and the strip
itself into art/comcast/ (art_files.py: a file the page loads on demand, a phone's half copy beside it).

fetch_comcast_art.py makes five straight-on elevations (lidar_cache/comcast_art_raw/): the Comcast Technology Center's
spine panels, its louvres, its frosted lantern, its canopy's soffit and its dark grey core panels. This bake cuts each to a
whole number of its own modules between two of its joints (CROP: the joints found once on the images by their column and
row darkness, a module's repeat between the first and last chosen, so the cut tiles with its own joint on the seam), takes
out the light the model painted falling across a plain one (FLAT), folds
the last few per cent of every edge into the opposite one (a tile the model drew a hair off its period still meets itself),
resizes it to a SIZE square, and stacks the five in the page's order (fetch_comcast_art.ORDER) into one strip, a layer a
square, which the page uploads as one texture array (cmrArtLoad). Each layer's mean colour in linear light goes in the
manifest: the page draws the layer's detail over its own calibrated colour (the image over its mean), so the art moves no
surface's brightness. Opaque RGB, never RGBA.

Usage: python3 bake_comcast_art.py [--preview DIR]"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
import art_files
import fetch_comcast_art as F

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'comcast_art.json')
SIZE = 512
FOLD = 0.03   # the share of each edge folded into the opposite one
# the plain surfaces whose light the model painted falling off across the picture: the plane that fits each channel's
# light over the crop (least squares in x and y) is divided out round its mean before the fold, so a tile has no gradient
# to show as a band at its seam (the lantern keeps its: the brace's X is its large scale)
FLAT = {'spine', 'louvre', 'soffit', 'panel'}
# per tile: the crop [x0, y0, x1, y1] in the 1024-wide source between two of its joints, and the tile's size in metres
# [along, up] as the crop holds it. spine: its vertical joints at 280, 512 and 744 and its horizontal at 767 (2 panels by
# 1, the joint mid-tile); louvre: the mullions at 271 and 751 (one bay) and 48 blades on a 32 px period; lantern: the frames'
# centres at 10 and 1019 across (4 panels) and 7 and 1531 up (2), the brace's X from corner to corner; soffit: the gaps at 22
# and 1006 (29 slats on a 33.9 px period), the slats' own length folded; panel: the joints at 148 and 637 (2 panels) and
# 14 and 768 (one)
CROP = {
    'spine': ([280, 384, 744, 1151], [3.04, 4.42]),
    'louvre': ([271, 0, 751, 1536], [1.52, 4.42]),
    'lantern': ([10, 7, 1019, 1531], [6.08, 8.84]),
    'soffit': ([22, 0, 1006, 1024], [2.9, 3.0]),
    'panel': ([148, 14, 637, 768], [3.04, 4.42]),
}


def fold(a, k):
    """Fold the last k of each edge into the opposite edge (a linear cross-fade over k), both axes: the result tiles."""
    h, w = a.shape[:2]
    out = a.copy()
    kx, ky = max(1, int(w * k)), max(1, int(h * k))
    for i in range(kx):
        t = (i + 0.5) / kx
        out[:, i] = a[:, i] * t + a[:, w - kx + i] * (1 - t)
    out = out[:, :w - kx]
    a2 = out.copy()
    for j in range(ky):
        t = (j + 0.5) / ky
        out[j] = a2[j] * t + a2[h - ky + j] * (1 - t)
    return out[:h - ky]


def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    tiles, layers = [], []
    for tid in F.ORDER:
        src = os.path.join(F.RAW, tid + '.png')
        if not os.path.exists(src):
            sys.exit('missing %s: run fetch_comcast_art.py' % src)
        im = Image.open(src).convert('RGB')
        if im.width != 1024:
            sys.exit('%s is %d wide; the crops are measured on the 1024-wide image' % (tid, im.width))
        box, tile_m = CROP[tid]
        cut = im.crop(tuple(box))
        arr = np.asarray(cut, float) / 255.0
        if tid in FLAT:
            h, w = arr.shape[:2]
            yy, xx = np.mgrid[0:h, 0:w]
            A = np.stack([np.ones(h * w), (xx.ravel() - w / 2) / w, (yy.ravel() - h / 2) / h], 1)
            for ch in range(3):
                coef = np.linalg.lstsq(A, arr[..., ch].ravel(), rcond=None)[0]
                plane = (A @ coef).reshape(h, w)
                arr[..., ch] = np.clip(arr[..., ch] / np.maximum(plane, 0.02) * coef[0], 0, 1)
        arr = fold(arr, FOLD)
        t = Image.fromarray(np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8)).resize((SIZE, SIZE), Image.LANCZOS)
        mean = srgb_to_lin(np.asarray(t, float) / 255.0).reshape(-1, 3).mean(0)
        tiles.append(t)
        layers.append({'id': tid, 'tile': tile_m, 'mean': [round(float(v), 4) for v in mean]})
        if a.preview:
            os.makedirs(a.preview, exist_ok=True)
            t.save(os.path.join(a.preview, tid + '.png'))
            Image.fromarray(np.tile(np.asarray(t), (2, 3, 1))).save(os.path.join(a.preview, tid + '-tiled.png'))
    strip = Image.new('RGB', (SIZE, SIZE * len(tiles)))
    for i, t in enumerate(tiles):
        strip.paste(t, (0, SIZE * i))
    files = {
        'strip': art_files.write(strip, 'comcast', 'cladding', 'WEBP', quality=90, method=6),
        'stripHalf': art_files.write(strip.resize((SIZE // 2, SIZE // 2 * len(tiles)), Image.LANCZOS), 'comcast', 'cladding-half', 'WEBP', quality=88, method=6),
    }
    gone = art_files.prune('comcast')
    man = {'note': 'bake_comcast_art.py: the Comcast Technology Center\'s cladding, a strip of square layers in the page\'s order (CMR_LAYERS), each tile\'s size in metres and its mean in linear light',
           'size': SIZE, 'layers': layers, **files}
    json.dump(man, open(OUT, 'w'), separators=(',', ':'))
    print('comcast_art.json: %d layers, pruned %d' % (len(layers), gone))
    for k in files:
        print(' ', k, files[k], art_files.size(files[k]) // 1024, 'KB')


if __name__ == '__main__':
    main()
