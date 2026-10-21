#!/usr/bin/env python3
"""Bake the sports complex's generated surfaces (fetch_stadium_art.py) into what the venues' programs read (Round 195):
stadium_art.json, the manifest build.py inlines as STADIUM_ART, and the images under art/stadiums/ (art_files.py: a content
hash in every name, a phone's half copy beside each).

- walls: the eight outer walls (Citizens Bank Park's brick, the Linc's glazed sides and braced ends, the arena's fins, podium
  and drum; since the review's round the Linc's office block and the ballpark's gate atriums) as the strips of one atlas, 1024 wide, STRIP_H tall each, a strip a wall's whole height. Each picture's bay is
  found from the autocorrelation of its column profile, a whole number of bays is cut from it and laid across the strip's
  full width, so the texture's own horizontal repeat carries the wall along its length (no fract in the shader, no seam in
  the mips); PAD rows of each strip's edge are repeated above and below it so a mip level never reads its neighbour. The
  manifest gives each strip's aspect (the bays' width over the wall's height, as drawn) and its mean colour (the far level
  and the frames before the atlas arrives). The alpha channel is the glass: 255 a pane, 128 the wall (never under 128, so a
  premultiplying decoder cannot lose the colour), found per picture by its own rule (MASKS: a pane's colour against its
  brick, panels and mullions); the page makes a pane smooth and lights some of them after dark, by the bays and the rows
  each strip's entry carries (WINDOWS: how many rows of panes a strip's height holds, and the share lit at night). The
  first cut called every dark pixel glass, so the podium's spandrels lit as two cream stripes and the office block's pale
  panes never lit.
- board: the left field board's picture, cropped to the board's 16:9 and stored at 1024 by 576 (the page sets it into
  the screens' canvas: the canvas cartoon read as a children's game).
- tiles: the seat rows, the turf and the infield clay, 512 square, repeating both ways. The seat rows are cut to a whole
  number of rows and seats; then every tile is made to wrap by blending it with itself rolled by half under a mask that
  keeps the original in the middle. The seats keep only their shading and where they are: red is the luminance, green the
  seat mask (the navy's blue over its red), blue the luminance again, so one picture serves the ballpark's blue and the
  Linc's midnight green, which the page tints.

Usage: python3 bake_stadium_art.py"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'stadium_art_raw')
OUT = os.path.join(HERE, 'stadium_art.json')
KIND = 'stadiums'
STRIP_W, STRIP_H, PAD = 1024, 256, 8
# (strip id, the raw picture): the podium's strip is the glazed one since the review's round ('arena-podium' stays on disk)
WALLS = [('cbp-brick', 'cbp-brick'), ('linc-glass', 'linc-glass'), ('linc-screen', 'linc-screen'), ('arena-fins', 'arena-fins'),
         ('arena-podium', 'arena-podium-glass'), ('arena-drum', 'arena-drum'), ('linc-office', 'linc-office'), ('cbp-atrium', 'cbp-atrium'),
         ('cbp-pattison', 'cbp-pattison'), ('cbp-alley', 'cbp-alley'), ('cbp-ivy', 'cbp-ivy')]   # Round 217: the ballpark's own three
# a strip's panes: rows of them in its height, the rows' offset (the page's row is floor(sv * rows + off), sv 0 at the foot:
# the offset puts a boundary between two rows of panes, never through one, as the pictures were measured), and the share lit
# after dark (0 for a wall without glass)
WINDOWS = {'cbp-brick': (2, -0.16, 0.45), 'linc-glass': (2, 0.0, 0.8), 'linc-screen': (1, 0.0, 0), 'arena-fins': (1, 0.0, 0),
           'arena-podium': (2, 0.1, 0.85), 'arena-drum': (1, 0.0, 0), 'linc-office': (3, 0.04, 0.55), 'cbp-atrium': (2, 0.06, 0.9),
           # (the Pattison front's rows are unequal: 4.76 a height puts the boundaries at 0.25, 0.46 and 0.67, between the
           # storefront's two storeys and the window rows, as the picture was measured)
           'cbp-pattison': (4.76, -0.19, 0.5), 'cbp-alley': (1, 0.0, 0.7), 'cbp-ivy': (1, 0.0, 0)}


def glass_mask(src, a):
    """Where a picture's panes are, by its own colours (sRGB 0..255): its brick, panels, mullions and copings are not glass"""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    yf = np.linspace(0, 1, a.shape[0])[:, None]
    if src == 'cbp-brick':   # dark green-grey panes in the brick, under the cornice, over the granite
        return (lum < 70) & (yf > 0.07) & (yf < 0.86)
    if src == 'linc-glass':   # grey-green panes between the brick piers, under the truss band, over the base
        return (r - b < 18) & (lum > 40) & (lum < 140) & (yf > 0.15) & (yf < 0.83)
    if src == 'arena-podium-glass':   # the two bands' blue-grey glass against the charcoal panels
        return (b - r > 7) & (lum > 40)
    if src == 'linc-office':   # the pale blue panes against the grey panels
        return (b - r > 14) & (lum > 60)
    if src == 'cbp-pattison':   # the blue-grey panes against the red brick, the tan precast and the red granite base
        return (b - r > 5) & (lum < 120) & (yf > 0.05) & (yf < 0.9)
    if src == 'cbp-alley':   # the dark interiors under the half-raised shutters
        return (lum < 45) & (yf > 0.4) & (yf < 0.8)
    if src == 'cbp-atrium':   # the curtain wall's panes: not the brick, the green steel, the granite or the coping
        return (r - g < 20) & (g - r < 18) & (lum < 160) & (yf > 0.06) & (yf < 0.88)
    return np.zeros(a.shape[:2], bool)
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


def bake_wall(cid, src):
    im = load(src)
    a = np.asarray(im).astype(np.float32)
    # (opened by a 3 pixel window: a dark brick in the wall is not a pane)
    mask = Image.fromarray((glass_mask(src, a) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    h, w = a.shape[:2]
    p = period(edge_profile(a, 0), 48, w // 2)
    k = max(1, int(w / p + 0.02))
    cut = min(w, int(round(k * p)))
    x0 = (w - cut) // 2
    crop = im.crop((x0, 0, x0 + cut, h))
    body = crop.resize((STRIP_W, STRIP_H - 2 * PAD), Image.LANCZOS)
    mb = np.asarray(mask.crop((x0, 0, x0 + cut, h)).resize((STRIP_W, STRIP_H - 2 * PAD), Image.BOX)).astype(np.float32)
    b = np.concatenate([np.asarray(body).astype(np.float32), (128 + mb * 127 / 255)[..., None]], axis=2)
    # the whole-bay cut leaves the seam within a pixel or two: blend the last 16 columns into the first
    n = 16
    for i in range(n):
        t = (i + 1) / (n + 1)
        b[:, STRIP_W - n + i] = b[:, STRIP_W - n + i] * (1 - t) + b[:, i] * t
    strip = np.concatenate([np.repeat(b[:1], PAD, axis=0), b, np.repeat(b[-1:], PAD, axis=0)], axis=0)
    mean = b[..., :3].reshape(-1, 3).mean(axis=0)
    rows, off, lit = WINDOWS[cid]
    return strip, {'id': cid, 'bays': k, 'period': round(float(p), 2), 'aspect': round(cut / h, 4), 'mean': [int(round(c)) for c in mean],
                   'rows': rows, 'off': off, 'lit': lit, 'glass': round(float((mb > 127).mean()), 3)}


def bake_board():
    """The left field board's picture: the middle 16:9 of the photograph, a little low (the field, not the sky)"""
    im = load('board')
    w, h = im.size
    ch = int(w * 9 / 16)
    y0 = min(h - ch, int((h - ch) * 0.6))
    return np.asarray(im.crop((0, y0, w, y0 + ch)).resize((1024, 576), Image.LANCZOS)).astype(np.float32)


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
    kw = {'lossless': True, 'quality': 100, 'method': 6} if lossless else {'quality': 90, 'method': 6, 'alpha_quality': 100}
    full = art_files.write(im, KIND, name, 'WEBP', **kw)
    half = art_files.write(im.resize((im.width // 2, im.height // 2), Image.LANCZOS), KIND, name + '-half', 'WEBP', **kw)
    return full, half


def main():
    strips, info = [], []
    for cid, src in WALLS:
        s, m = bake_wall(cid, src)
        strips.append(s)
        info.append(m)
        print('%-13s %d bays of %.1f px, aspect %.3f, mean %s, glass %.0f%%' % (cid, m['bays'], m['period'], m['aspect'], m['mean'], m['glass'] * 100))
    atlas = np.concatenate(strips, axis=0)
    walls, walls_h = save(atlas, 'walls')
    if os.environ.get('STADIUM_MASK_PREVIEW'):   # the glass a strip found, for a look: the wall dimmed, the panes as they are
        pv = atlas[..., :3] * np.where(atlas[..., 3:] > 191, 1.0, 0.25)
        Image.fromarray(np.clip(pv, 0, 255).astype(np.uint8)).save(os.environ['STADIUM_MASK_PREVIEW'])
    board, board_h = save(bake_board(), 'board')
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
        'walls': walls, 'wallsHalf': walls_h, 'stripH': STRIP_H, 'pad': PAD, 'strips': info, 'board': board, 'boardHalf': board_h,
        'seats': seats_f, 'seatsHalf': seats_h, 'seatRows': sm['rows'], 'seatCols': sm['seats'], 'seatShare': sm['seatShare'],
        'grass': tiles['grass'][0], 'grassHalf': tiles['grass'][1], 'grassMean': tiles['grass'][2],
        'clay': tiles['clay'][0], 'clayHalf': tiles['clay'][1], 'clayMean': tiles['clay'][2],
    }
    json.dump(man, open(OUT, 'w'), indent=1)
    gone = art_files.prune(KIND)
    files = (walls, walls_h, board, board_h, seats_f, seats_h, *[x for v in tiles.values() for x in v[:2]])
    total = sum(art_files.size(p) for p in files)
    print('wrote %s, %d files %.0f KB, pruned %d' % (os.path.basename(OUT), len(files), total / 1024, gone))


if __name__ == '__main__':
    main()
