#!/usr/bin/env python3
"""Bake the cruiser Olympia's surfaces (fetch_olympia_art.py, Round 215) into olympia_art.json, which build.py inlines as
OLYMPIA_ART, and the atlas itself into art/olympia/ (a file the page loads on demand, a phone's copy at half; art_files.py).

One 2048 by 1024 atlas of four 1024 by 512 cells, two across and two down, each padded with its own wrapped edge so the
mips and the filter never meet a neighbour: the hull's white plating, one deck level of the buff superstructure's wall,
the spar deck's planking and the buff plating of the funnels and turrets. The page reads every cell as detail over its
own paint (the texel over the cell's linear mean, olMaterial), so the white, the red and the buff stay the page's colours.

How each repeats (bake_nj_art.py's cuts, the same code):
- hull: across only, its last tenth cross-faded into its first and cut off; up it runs from the deck edge down and the
  page clamps it, so its strakes follow the sheer
- house: across only, the same way (its door stays one door); up it is one deck level, clamped
- deck: cut up the image on its own caulking seams a whole number of planks apart and blended along the planks; its
  metres from the planks' 14 cm
- buff: both ways, the half-roll blend

Usage: python3 bake_olympia_art.py [--preview DIR]"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
import art_files
import bake_wall_art as BW   # tileable, blend_axis, period_crop, lin_mean

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'olympia_art_raw')
OUT = os.path.join(HERE, 'olympia_art.json')
CW, CH, PAD = 1024, 512, 16          # a cell, its wrapped pad
CELLS = ['hull', 'house', 'deck', 'buff']
# what each picture shows across and up, in metres (its prompt); the deck's comes from its planks
SPAN = {'hull': (20.0, 10.0), 'house': (5.4, 2.4), 'buff': (6.0, 3.0)}
PLANK = 0.14


def load(cid):
    p = os.path.join(RAW, cid + '.png')
    if not os.path.exists(p):
        sys.exit('no %s (run fetch_olympia_art.py)' % p)
    return np.asarray(Image.open(p).convert('RGB'), np.float32)


def resize(a, w, h):
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), np.float32)


def edge_wrap(a, share=0.1):
    """Seamless across: the last `share` of the width cross-faded into the first and cut off, so the wrap meets the
    picture's own next column."""
    W = a.shape[1]
    b = int(W * share)
    w = np.linspace(0, 1, b, dtype=np.float32)
    w = (w * w * (3 - 2 * w))[None, :, None]
    out = a[:, :W - b].copy()
    out[:, :b] = a[:, :b] * w + a[:, W - b:] * (1 - w)
    return out


def cell(cid):
    """A cell's tile at the cell's inner size, its span in metres and a line for the log."""
    a = load(cid)
    H0, W0 = a.shape[:2]
    if cid == 'deck':
        b, k, pp = BW.period_crop(a, 0, 20, 120)   # the seams, a whole number of planks
        if not k:
            sys.exit('deck: no plank period')
        b = BW.blend_axis(b, 1)
        my = k * PLANK
        mx = my * b.shape[1] / b.shape[0]
        rep = 'deck: %d planks of %d px, %.2f x %.2f m' % (k, pp, mx, my)
    elif cid == 'buff':
        b = BW.tileable(a)
        mx, my = SPAN[cid]
        rep = 'buff: blended both ways, %.1f x %.1f m' % (mx, my)
    else:
        b = edge_wrap(a)
        mx, my = SPAN[cid][0] * b.shape[1] / W0, SPAN[cid][1]
        rep = '%s: wrapped across, %.2f x %.1f m, clamped up' % (cid, mx, my)
    t = resize(b, CW - 2 * PAD, CH - 2 * PAD)
    return t, mx, my, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    A = np.zeros((2 * CH, 2 * CW, 3), np.float32)
    means, metres = [], []
    for k, cid in enumerate(CELLS):
        t, mx, my, rep = cell(cid)
        print(rep)
        means.append(BW.lin_mean(t))
        metres.append([round(mx, 3), round(my, 3)])
        c = np.pad(t, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='wrap')
        y0, x0 = (k // 2) * CH, (k % 2) * CW
        A[y0:y0 + CH, x0:x0 + CW] = c
        if a.preview:
            os.makedirs(a.preview, exist_ok=True)
            Image.fromarray(np.clip(np.concatenate([np.concatenate([t, t], 1)] * 2, 0), 0, 255).astype(np.uint8)).save(os.path.join(a.preview, cid + '-tile2x2.jpg'), quality=88)
    im = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
    out = {'v': 1, 'cells': CELLS, 'grid': [2, 2], 'pad': [PAD / CW, PAD / CH], 'mean': means, 'm': metres}
    out['img'] = art_files.write(im, 'olympia', 'atlas', 'WEBP', quality=86, method=6)
    out['imgHalf'] = art_files.write(im.resize((CW, CH), Image.LANCZOS), 'olympia', 'atlas-half', 'WEBP', quality=84, method=6)
    if a.preview:
        im.save(os.path.join(a.preview, 'atlas.jpg'), quality=88)
    print('atlas %d KB, half %d KB' % (art_files.size(out['img']) // 1024, art_files.size(out['imgHalf']) // 1024))
    print('pruned %d old files' % art_files.prune('olympia'))
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f KB' % (os.path.getsize(OUT) / 1e3))


if __name__ == '__main__':
    main()
