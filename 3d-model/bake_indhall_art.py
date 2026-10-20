#!/usr/bin/env python3
"""Bake Independence Hall's art (Round 210; fetch_indhall_art.py made the images) into indhall_art.json, which build.py
inlines as INDHALL_ART, and its one atlas into art/indhall/ (a file the page loads on demand, a phone's copy at half;
art_files.py). The cutting is A Man Full of Trouble's (bake_tavern_art.py, imported):
  swatches  brick (Flemish bond, cut on its own courses and joints by bake_wall_art.course_tile, 7 cm a course, its glazed
            headers eased toward the stretchers), shingle (cut on its courses, 12 cm), paint and stone (the half-roll
            blend), each with its size in metres and its linear mean, padded with its own wrapped edge;
  elements  the three keyed sashes first (the page's shader takes elements 0 to 2 as glazed: their chroma-key panes are
            measured and repainted on an exact regular grid, which the page's glass meets to the texel), then the
            doorways, the Palladian window, the round-headed sash, the clock dial, the oculus, the wing door and the
            cellar grille, each with an edge-replicated gutter of 32 texels (the tavern's 8 held a far doorway to its mean).
Every element is laid at the same pixels a metre, the largest that packs into ATLAS_W by ATLAS_H.

The raw images are in lidar_cache/indhall_art_raw (INDHALL_ART_RAW overrides); CHOSEN names the variant used for each,
by eye against the reference photos (fetch_indhall_art.py lists them).

Usage: python3 bake_indhall_art.py [--check]   (--check writes the atlas to RAW/look-atlas.png only)"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
import art_files
import bake_wall_art as BW
import bake_tavern_art as BT

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('INDHALL_ART_RAW') or os.path.join(HERE, 'lidar_cache', 'indhall_art_raw')
OUT = os.path.join(HERE, 'indhall_art.json')
CHOSEN = {'brick': 'brick-a', 'shingle': 'shingle-a', 'paint': 'paint-a', 'stone': 'stone-a', 'sashG': 'sashG-a',
          'sashU': 'sashU-b', 'sashW': 'sashW-a', 'door': 'door-a', 'tdoor': 'tdoor-a', 'palladian': 'palladian-a',
          'arch': 'arch-a', 'clock': 'clock-a', 'oculus': 'oculus-a', 'wdoor': 'wdoor-b', 'cellar': 'cellar-a'}
# the swatches: (key, course in metres or None, what an uncoursed image shows across in metres, inner cell px)
SWATCHES = [('brick', 0.07, None, 448), ('shingle', 0.12, None, 448), ('paint', None, 1.0, 224), ('stone', None, 0.6, 224)]
SW_PAD = 32
# each swatch's colour as the hall shows it, set by eye in the scene against the reference photos
SW_GAIN = {'brick': (1.0, 0.97, 0.95), 'shingle': (0.8, 0.76, 0.72), 'paint': (0.97, 0.97, 0.95), 'stone': (0.95, 0.96, 0.97)}
# the elements: (key, width, height in metres, the glass's sashes as [cols, rows] each top to bottom, or None); the
# glazed first, in the shader's order
ELEMENTS = [('sashG', 1.60, 4.00, [[3, 4], [3, 4]]), ('sashU', 1.60, 3.40, [[3, 4], [3, 4]]), ('sashW', 1.20, 2.30, [[3, 3], [3, 3]]),
            ('door', 2.20, 4.40, None), ('tdoor', 3.20, 5.00, None), ('palladian', 3.80, 5.40, None), ('arch', 1.50, 3.90, None),
            ('clock', 2.80, 2.80, None), ('oculus', 1.60, 1.60, None), ('wdoor', 1.30, 2.70, None), ('cellar', 1.20, 0.60, None)]
GUTTER = 32   # the page samples up to 28 texels in (ihU.uTvGut), so a doorway seen across the square keeps its picture
ATLAS_W, ATLAS_H = 2048, 2048


def load(name):
    p = os.path.join(RAW, CHOSEN.get(name, name) + '.png')
    if not os.path.exists(p):
        sys.exit('no %s (run fetch_indhall_art.py)' % p)
    return np.asarray(Image.open(p).convert('RGB'), np.float32)


def make_swatch(key, course_m, span_m):
    a = load(key)
    if course_m:
        t, mx, my, rep = BW.course_tile(a, course_m, 'indhall_' + key)
        if key == 'brick' and BT.HEADER_EASE > 0:
            t = BT.ease_headers(t)
    else:
        t, mx, my = BW.tileable(a), span_m, span_m
        rep = 'indhall_%s: blended, %.2f m' % (key, span_m)
    t = BT.flatten(t) * np.array(SW_GAIN.get(key, (1, 1, 1)), np.float32)[None, None, :]
    return t, mx, my, rep


def uv_rect(x, y, w, h):
    """An atlas rect [u0, v0, du, dv] in three's uv (v up from the image's foot, flipY)."""
    return [round(x / ATLAS_W, 6), round(1 - (y + h) / ATLAS_H, 6), round(w / ATLAS_W, 6), round(h / ATLAS_H, 6)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    sw = {}
    for key, course_m, span_m, inner in SWATCHES:
        t, mx, my, rep = make_swatch(key, course_m, span_m)
        print(rep)
        t = np.asarray(Image.fromarray(np.clip(t, 0, 255).astype(np.uint8)).resize((inner, inner), Image.LANCZOS), np.float32)
        sw[key] = (np.pad(t, ((SW_PAD, SW_PAD), (SW_PAD, SW_PAD), (0, 0)), mode='wrap'), mx, my, BW.lin_mean(t), inner)
    src = {}
    for key, wm, hm, sashes in ELEMENTS:
        a = load(key)
        g = None
        if sashes:
            rects, bu, bv, drawn = BT.glass_grid(a, sashes)
            hs = [r[3] - r[1] for r in rects]
            if len(sashes) == 2 and (drawn != [r for _, r in sashes] or abs(hs[0] - hs[1]) > 0.01 * max(hs)):
                print('%-9s drawn %s over the sashes (%d and %d px tall), equalised to %s' % (key, drawn, hs[0], hs[1], [r for _, r in sashes]))
                a, rects = BT.equalise(a, rects)
            a = BT.paint_glass(a, rects, sashes, bu, bv)
            H, W = a.shape[:2]
            g = {'rects': [[x0 / W, 1 - y1 / H, x1 / W, 1 - y0 / H] for (x0, y0, x1, y1) in rects], 'grid': [[c, r] for c, r in sashes],
                 'bar': [bu / W, bv / H]}
            print('%-9s %d sash(es), bars %.1f x %.1f px, glass %s' % (key, len(rects), bu, bv, ' '.join('%d..%d x %d..%d' % (r[0], r[2], r[1], r[3]) for r in rects)))
        src[key] = (a, g)
    ppm = 220
    while ppm > 80:
        items = [(k, v[0].shape[1], v[0].shape[0]) for k, v in sw.items()]
        dims = {}
        for key, wm, hm, _ in ELEMENTS:
            w, h = int(round(wm * ppm)), int(round(hm * ppm))
            dims[key] = (w, h)
            items.append((key, w + 2 * GUTTER, h + 2 * GUTTER))
        at = BT.pack(items, ATLAS_W, ATLAS_H)
        if at:
            break
        ppm -= 4
    print('elements at %d px a metre' % ppm)
    A = np.zeros((ATLAS_H, ATLAS_W, 3), np.float32) + 128
    man = {'v': 1, 'w': ATLAS_W, 'h': ATLAS_H, 'ppm': ppm, 'sw': {}, 'el': {}}
    for k, (cell, mx, my, mean, inner) in sw.items():
        x, y = at[k]
        A[y:y + cell.shape[0], x:x + cell.shape[1]] = cell
        man['sw'][k] = {'rect': uv_rect(x + SW_PAD, y + SW_PAD, inner, inner), 'm': [round(mx, 3), round(my, 3)], 'mean': mean}
    for key, wm, hm, sashes in ELEMENTS:
        a, g = src[key]
        w, h = dims[key]
        im = np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), np.float32)
        x, y = at[key]
        A[y:y + h + 2 * GUTTER, x:x + w + 2 * GUTTER] = BT.grow(im, GUTTER)
        e = {'rect': uv_rect(x + GUTTER, y + GUTTER, w, h), 'size': [wm, hm], 'mean': BW.lin_mean(im)}
        if g:
            e.update({'glass': [[round(v, 5) for v in r] for r in g['rects']], 'grid': g['grid'], 'bar': [round(g['bar'][0], 5), round(g['bar'][1], 5)]})
        man['el'][key] = e
    im = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
    if args.check:
        im.save(os.path.join(RAW, 'look-atlas.png'))
        print('wrote', os.path.join(RAW, 'look-atlas.png'))
        return
    man['img'] = art_files.write(im, 'indhall', 'atlas', 'WEBP', quality=86, method=6)
    man['imgHalf'] = art_files.write(im.resize((ATLAS_W // 2, ATLAS_H // 2), Image.LANCZOS), 'indhall', 'atlas-half', 'WEBP', quality=84, method=6)
    print('atlas %d KB, half %d KB' % (art_files.size(man['img']) // 1024, art_files.size(man['imgHalf']) // 1024))
    print('pruned %d old indhall files' % art_files.prune('indhall'))
    with open(OUT + '.tmp', 'w') as f:
        json.dump(man, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f KB' % (os.path.getsize(OUT) / 1e3))


if __name__ == '__main__':
    main()
