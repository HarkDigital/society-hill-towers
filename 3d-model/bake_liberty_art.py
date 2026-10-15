#!/usr/bin/env python3
"""Bake One and Two Liberty Place's near detail (Round 195) from fetch_liberty_art.py's pictures into liberty_art.json and
its images under art/liberty/ (art_files.write: each named by its content's hash, with a -half copy a phone takes).

- base: the granite base's two elevations (the lobby bays and the plainer wall), each 12 m by 12 m, side by side in one
  2048 by 1024 atlas. Alpha is the stone and the frames (255) against the glass (0), which the page reads as the mask:
  polished granite where it is 1, a smooth dark pane that mirrors the sky and lights after dark where it is 0.
- glazing: the crowns' sloped glazing, cut to two bays by two courses between the centres of its caps (3 m by 3 m, so it
  tiles: half a cap at each edge), 512 square. Alpha is the caps (255) over the glass (0); the page lays it a few
  centimetres over the crown's glass and keeps only the caps (alphaTest).
Both store their colour premultiplied by the alpha (the glass's texels black), and the page divides it back out: a browser
may drop the colour under a transparent texel as it decodes (lossy WebP and premultiplying decoders do), and a mip that
averages a cap with the glass beside it then keeps the cap's own colour instead of darkening toward whatever was there.

Usage: python3 bake_liberty_art.py   (after fetch_liberty_art.py)"""
import json, os, sys
import numpy as np
from PIL import Image
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'liberty_art_raw')
OUT = os.path.join(HERE, 'liberty_art.json')
KEY_GAP, KEY_K = 35, 1.6   # a pane's green: over the other channels by KEY_GAP and KEY_K times the larger (City Hall's key)
SPILL = 8                  # a frame pixel by the glass whose green stands this far over red and blue is the key's spill
BASE_M = (12.0, 12.0)      # the base's elevations, metres across and up
GLAZE_M = 3.0              # the glazing tile, metres a side (two 1.5 m bays by two 1.5 m courses)


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy or dx:
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def key(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = np.maximum(r, b)
    return (g - mx > KEY_GAP) & (g > KEY_K * mx + 8)


def despill(a, green):
    """The key's spill on the frames round the glass taken down to the other channels' mean."""
    near = dilate(green, 4) & ~green
    gmax = np.maximum(a[..., 0], a[..., 2])
    sp = near & (a[..., 1] - gmax > SPILL)
    a[sp, 1] = gmax[sp] + SPILL * 0.3
    return a


def reveal_row(a):
    """The acid-blue reveal line's row in the fascia (the brightest blue-over-red row in the top fifth)."""
    top = a[:205]
    score = (top[..., 2] - top[..., 0]).mean(1) + 0.5 * top.mean((1, 2))
    return int(np.argmax(score))


def align_top(a, src, dst, below=300):
    """The rows over `below` remapped so the reveal at row src lands on row dst (a piecewise linear stretch of the
    fascia), so the two elevations' fascias meet at a corner."""
    rows = np.arange(below, dtype=np.float32)
    srcr = np.where(rows <= dst, rows * src / max(dst, 1), src + (rows - dst) * (below - src) / max(below - dst, 1))
    i0 = np.clip(np.floor(srcr).astype(int), 0, a.shape[0] - 1)
    i1 = np.clip(i0 + 1, 0, a.shape[0] - 1)
    f = (srcr - i0)[:, None, None]
    out = a.copy()
    out[:below] = a[i0] * (1 - f) + a[i1] * f
    return out


def base_cell(cid, line=None):
    im = Image.open(os.path.join(RAW, cid + '.png')).convert('RGB').resize((1024, 1024), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    if line is not None:
        a = align_top(a, reveal_row(a), line)
    green = dilate(key(a), 1)
    a = despill(a, green)
    stone = a[~green]
    al = np.where(green, 0.0, 1.0)
    rgba = np.dstack([np.clip(a, 0, 255) * al[..., None], al * 255.0]).astype(np.uint8)
    return rgba, {'glass': round(float(green.mean()), 4), 'stone': [round(float(v), 1) for v in stone.mean(0)]}


def cap_centres(prof):
    """The centres of the caps along one axis: runs where the green share falls under half."""
    low = prof < 0.5
    out, i, n = [], 0, len(prof)
    while i < n:
        if low[i]:
            j = i
            while j < n and low[j]:
                j += 1
            out.append((i + j - 1) / 2.0)
            i = j
        else:
            i += 1
    return out


def glazing():
    im = Image.open(os.path.join(RAW, 'glazing.png')).convert('RGB')
    a = np.asarray(im).astype(np.float32)
    green = key(a)
    cx, cy = cap_centres(green.mean(0)), cap_centres(green.mean(1))
    if len(cx) < 3 or len(cy) < 3:
        sys.exit('glazing: found %d and %d caps, need three each way' % (len(cx), len(cy)))
    # two periods each way between cap centres: half a cap at every edge, so the tile repeats
    x0, x1, y0, y1 = cx[0], cx[2], cy[0], cy[2]
    crop = im.crop((int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)))).resize((512, 512), Image.LANCZOS)
    c = np.asarray(crop).astype(np.float32)
    g = key(c)
    c = despill(c, g)
    frame = ~g
    mean = c[frame].mean(0)
    al = np.where(frame, 1.0, 0.0)
    rgba = np.dstack([np.clip(c, 0, 255) * al[..., None], al * 255.0]).astype(np.uint8)
    return rgba, {'caps': [round(float(v), 1) for v in mean], 'cover': round(float(frame.mean()), 4),
                  'periods': [round((x1 - x0) / 2, 1), round((y1 - y0) / 2, 1)]}


def main():
    lobby, ml = base_cell('base-lobby')
    line = reveal_row(np.asarray(Image.open(os.path.join(RAW, 'base-lobby.png')).convert('RGB').resize((1024, 1024), Image.LANCZOS)).astype(np.float32))
    wall, mw = base_cell('base-wall', line)   # its fascia's reveal on the lobby's row
    ml['reveal'] = mw['reveal'] = round(1 - line / 1024, 4)
    atlas = Image.fromarray(np.concatenate([lobby, wall], axis=1), 'RGBA')
    gz, mg = glazing()
    gim = Image.fromarray(gz, 'RGBA')
    kind = 'liberty'
    base = art_files.write(atlas, kind, 'base', 'WEBP', quality=90, method=6)
    base_h = art_files.write(atlas.resize((1024, 512), Image.LANCZOS), kind, 'base-half', 'WEBP', quality=88, method=6)
    glz = art_files.write(gim, kind, 'glazing', 'WEBP', quality=92, method=6)
    glz_h = art_files.write(gim.resize((256, 256), Image.LANCZOS), kind, 'glazing-half', 'WEBP', quality=90, method=6)
    gone = art_files.prune(kind)
    man = {
        'v': 1,
        'base': {'img': base, 'imgHalf': base_h, 'm': list(BASE_M), 'cells': {'lobby': [0, 0, 0.5, 1], 'wall': [0.5, 0, 1, 1]},
                 'means': {'lobby': ml, 'wall': mw}},
        'glazing': {'img': glz, 'imgHalf': glz_h, 'm': GLAZE_M, **mg},
        'refs': ['https://commons.wikimedia.org/wiki/Category:One_Liberty_Place', 'https://commons.wikimedia.org/wiki/Category:Two_Liberty_Place',
                 'https://archipediavm.upress.virginia.edu/buildings/PA-02-PH112', 'https://www.loc.gov/item/2011630484/'],
    }
    json.dump(man, open(OUT, 'w'), indent=1)
    for p in (base, base_h, glz, glz_h):
        print('%-48s %6d KB' % (p, art_files.size(p) // 1024))
    print('pruned %d; lobby glass %.3f, wall glass %.3f, glazing caps %.3f of the tile' % (gone, ml['glass'], mw['glass'], mg['cover']))


if __name__ == '__main__':
    main()
