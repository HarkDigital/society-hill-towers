#!/usr/bin/env python3
"""Bake the sports complex's generated surfaces (fetch_stadium_art.py) into what the venues' programs read (Round 195):
stadium_art.json, the manifest build.py inlines as STADIUM_ART, and the images under art/stadiums/ (art_files.py: a content
hash in every name, a phone's half copy beside each).

- walls: the six outer walls (Citizens Bank Park's brick, the Linc's glazed sides and braced ends, the arena's fins, podium
  and drum) as the strips of one atlas, 1024 wide, STRIP_H tall each, a strip a wall's whole height. Each picture's bay is
  found from the autocorrelation of its column profile, a whole number of bays is cut from it and laid across the strip's
  full width, so the texture's own horizontal repeat carries the wall along its length (no fract in the shader, no seam in
  the mips); PAD rows of each strip's edge are repeated above and below it so a mip level never reads its neighbour. The
  manifest gives each strip's aspect (the bays' width over the wall's height, as drawn) and its mean colour (the far level
  and the frames before the atlas arrives).
- tiles: the seat rows, the turf and the infield clay, 512 square, repeating both ways. The seat rows are cut to a whole
  number of rows and seats; then every tile is made to wrap by blending it with itself rolled by half under a mask that
  keeps the original in the middle. The seats keep only their shading and where they are: red is the luminance, green the
  seat mask (the navy's blue over its red), blue the luminance again, so one picture serves the ballpark's blue and the
  Linc's midnight green, which the page tints.

Usage: python3 bake_stadium_art.py"""
import json, os, sys
import numpy as np
from PIL import Image
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'stadium_art_raw')
OUT = os.path.join(HERE, 'stadium_art.json')
KIND = 'stadiums'
STRIP_W, STRIP_H, PAD = 1024, 256, 8
WALLS = ['cbp-brick', 'linc-glass', 'linc-screen', 'arena-fins', 'arena-podium', 'arena-drum']
TILE = 512
SEAT_GRID = (8, 4)   # seats by rows in a tile: one seat 64 by 128 pixels


def load(cid):
    p = os.path.join(RAW, cid + '.png')
    if not os.path.exists(p):
        sys.exit('missing %s: run fetch_stadium_art.py first' % p)
    return Image.open(p).convert('RGB')


def period(profile, lo, hi):
    """The strongest repeat of a 1-D profile between lo and hi samples (its autocorrelation's peak)."""
    x = profile - profile.mean()
    n = len(x)
    ac = np.correlate(x, x, 'full')[n - 1:]
    ac = ac / (ac[0] + 1e-9)
    hi = min(hi, n - 1)
    k = lo + int(np.argmax(ac[lo:hi]))
    # a sub-sample peak by the parabola through its neighbours
    if 0 < k < n - 1:
        a, b, c = ac[k - 1], ac[k], ac[k + 1]
        d = a - 2 * b + c
        if abs(d) > 1e-9:
            return float(k + 0.5 * (a - c) / d)
    return float(k)


def edge_profile(arr, axis):
    """The mean absolute gradient across the other axis: bay lines, piers and seat edges stand out of it."""
    g = np.abs(np.diff(arr.mean(axis=2), axis=1 - axis))
    return g.mean(axis=axis)


def wrap_blend(a, frac=0.22):
    """Make a tile wrap: blend it with itself rolled by half, the original kept in the middle."""
    h, w = a.shape[:2]
    r = np.roll(np.roll(a, h // 2, axis=0), w // 2, axis=1)
    yy = np.abs(np.linspace(-1, 1, h))[:, None]
    xx = np.abs(np.linspace(-1, 1, w))[None, :]
    m = np.clip((1 - np.maximum(yy, xx)) / frac, 0, 1)[..., None]
    m = m * m * (3 - 2 * m)
    return a * m + r * (1 - m)


def bake_wall(cid):
    im = load(cid)
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    p = period(edge_profile(a, 0), 48, w // 2)
    k = max(1, int(w / p + 0.02))
    cut = min(w, int(round(k * p)))
    x0 = (w - cut) // 2
    crop = im.crop((x0, 0, x0 + cut, h))
    body = crop.resize((STRIP_W, STRIP_H - 2 * PAD), Image.LANCZOS)
    b = np.asarray(body).astype(np.float32)
    # the whole-bay cut leaves the seam within a pixel or two: blend the last 16 columns into the first
    n = 16
    for i in range(n):
        t = (i + 1) / (n + 1)
        b[:, STRIP_W - n + i] = b[:, STRIP_W - n + i] * (1 - t) + b[:, i] * t
    strip = np.concatenate([np.repeat(b[:1], PAD, axis=0), b, np.repeat(b[-1:], PAD, axis=0)], axis=0)
    mean = b.reshape(-1, 3).mean(axis=0)
    return strip, {'id': cid, 'bays': k, 'period': round(float(p), 2), 'aspect': round(cut / h, 4), 'mean': [int(round(c)) for c in mean]}


def bake_seats():
    """One seat in its row, the median of every seat in the picture laid over each other at the measured pitch (so the
    tile is exactly periodic and as crisp as one seat), repeated SEAT_GRID across the tile; the page varies them seat by
    seat"""
    im = load('seats')
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    py = period(edge_profile(a, 1), 60, h // 2)   # the rows
    px = period(edge_profile(a, 0), 30, w // 4)   # the seats
    ny, nx = int(h / py), int(w / px)
    cw, ch = TILE // SEAT_GRID[0], TILE // SEAT_GRID[1]
    cells = []
    for j in range(ny):
        for i in range(nx):
            x0, y0 = i * px, j * py
            if x0 + px > w or y0 + py > h:
                continue
            # the cell resampled to its tile size: an affine map from the tile cell to the picture
            c = im.transform((cw, ch), Image.AFFINE, (px / cw, 0, x0, 0, py / ch, y0), resample=Image.BICUBIC)
            cells.append(np.asarray(c).astype(np.float32))
    cell = np.median(np.stack(cells), axis=0)
    c = np.tile(cell, (SEAT_GRID[1], SEAT_GRID[0], 1))
    r, g, bl = c[..., 0], c[..., 1], c[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * bl
    blue = np.clip((bl - r - 6) / 30.0, 0, 1)   # the navy's blue over its red; the grey treads have none
    seat_l = lum[blue > 0.5].mean() if (blue > 0.5).any() else lum.mean()
    tread_l = lum[blue < 0.1].mean() if (blue < 0.1).any() else lum.mean()
    # the luminance normalised in each material (128 its mean) so the page's tint and concrete keep their own value
    nl = np.where(blue > 0.5, lum / max(seat_l, 1), lum / max(tread_l, 1))
    out = np.stack([np.clip(nl * 128, 0, 255), blue * 255, np.clip(lum, 0, 255)], axis=-1)
    meta = {'rows': SEAT_GRID[1], 'seats': SEAT_GRID[0], 'seatShare': round(float(blue.mean()), 3), 'cells': len(cells),
            'pitch': [round(float(px), 2), round(float(py), 2)]}
    return out, meta


def bake_tile(cid):
    im = load(cid)
    a = np.asarray(im.resize((TILE, TILE), Image.LANCZOS)).astype(np.float32)
    c = wrap_blend(a, 0.3)
    return c, [int(round(v)) for v in c.reshape(-1, 3).mean(axis=0)]


def save(arr, name, lossless=False):
    """A picture and its phone's half copy. The seat tile is data (its channels a luminance and a mask): lossless, or the
    codec's chroma subsampling would bleed the mask into the luminance"""
    im = Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8))
    kw = {'lossless': True, 'quality': 100, 'method': 6} if lossless else {'quality': 90, 'method': 6}
    full = art_files.write(im, KIND, name, 'WEBP', **kw)
    half = art_files.write(im.resize((im.width // 2, im.height // 2), Image.LANCZOS), KIND, name + '-half', 'WEBP', **kw)
    return full, half


def main():
    strips, info = [], []
    for cid in WALLS:
        s, m = bake_wall(cid)
        strips.append(s)
        info.append(m)
        print('%-13s %d bays of %.1f px, aspect %.3f, mean %s' % (cid, m['bays'], m['period'], m['aspect'], m['mean']))
    atlas = np.concatenate(strips, axis=0)
    walls, walls_h = save(atlas, 'walls')
    seats, sm = bake_seats()
    seats_f, seats_h = save(seats, 'seats', lossless=True)
    print('seats         %d rows, %d seats a tile, seat share %.2f, the median of %d seats at a pitch of %s px' % (sm['rows'], sm['seats'], sm['seatShare'], sm['cells'], sm['pitch']))
    tiles = {}
    for cid in ('grass', 'clay'):
        t, mean = bake_tile(cid)
        f, hf = save(t, cid)
        tiles[cid] = (f, hf, mean)
        print('%-13s mean %s' % (cid, mean))
    man = {
        'walls': walls, 'wallsHalf': walls_h, 'stripH': STRIP_H, 'pad': PAD, 'strips': info,
        'seats': seats_f, 'seatsHalf': seats_h, 'seatRows': sm['rows'], 'seatCols': sm['seats'], 'seatShare': sm['seatShare'],
        'grass': tiles['grass'][0], 'grassHalf': tiles['grass'][1], 'grassMean': tiles['grass'][2],
        'clay': tiles['clay'][0], 'clayHalf': tiles['clay'][1], 'clayMean': tiles['clay'][2],
    }
    json.dump(man, open(OUT, 'w'), indent=1)
    gone = art_files.prune(KIND)
    files = (walls, walls_h, seats_f, seats_h, *[x for v in tiles.values() for x in v[:2]])
    total = sum(art_files.size(p) for p in files)
    print('wrote %s, %d files %.0f KB, pruned %d' % (os.path.basename(OUT), len(files), total / 1024, gone))


if __name__ == '__main__':
    main()
