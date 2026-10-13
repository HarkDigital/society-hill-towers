#!/usr/bin/env python3
"""Bake the house fronts (the facade prototype, Oct 12) into fronts.json, which build.py inlines as FRONTS_DATA, and
the atlases themselves into art/fronts/ and art/tiles/ (Round 184: files the page loads on demand, art_files.py).

Per set, the fronts made by fetch_fronts.py (lidar_cache/fronts_raw/<set>/<id>.png) are cut into an atlas of CELL-sized
cells (each front stretched to the cell, its edge pixels run out into a PAD gutter so the mips never bleed), and a mask
atlas in the same layout at a quarter of the size: r is the window glass, g a number per window (the page lights each
window by its number), b the door. The windows are found by their dark glass: the pixels well under the front's own
median, closed across the muntins, cut into connected blobs and kept when a blob is a filled, window-shaped box; a tall
dark box standing on the foot of the front is the door. The page finds every house's street wall itself (Round 181). --placeholder draws plain stand-in fronts instead (engine work only: they never ship, the bake says so).

The realism pass (Oct 12, Mike: "make this look more photo realistic and less cartoony"): a set made again at its own
houses' proportions (fetch_fronts.py SIZES, lidar_cache/fronts5_raw/<set>/, taken when all sixteen are there) carries
its image's width to height ('aspect'), and every cell its storeys ('rows': the top of the ground floor and of the
upper storeys' band, from the foot, and how many upper storeys), found from its rows of windows, so the page fills a
taller or shorter wall with whole storeys at the image's own scale instead of stretching the front. The mask's alpha is
each window's height inside it (0.5 at the sill to 1 at the head, the page's room light), and each cell its wall's mean
colour ('wall'). The tower tiles' masks are folded over their own repeats into one clean window per bay and floor
(the percentile mask of the glass kinds was salt and pepper after dark), with the spandrel's height ('spandV') and the
pier's place in the bay ('pierU').

Usage: python3 bake_fronts.py [--placeholder] [--preview DIR]   (--preview writes each front with its mask over it)"""
import argparse, base64, io, json, math, os, sys
import art_files
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'fronts_raw')
RAW5 = os.path.join(HERE, 'lidar_cache', 'fronts5_raw')   # the realism pass's fronts at their own proportions
OUT = os.path.join(HERE, 'fronts.json')
CELL = (384, 768)   # px per front in the atlas, 1:2; the page stretches a cell to the wall it dresses (Round 184: 16 a
# set, 4 by 4, and a phone's copy at half, 192 by 384)
CELL_WIDE = (768, 576)   # the realism pass: a set of wide fronts (the one-storey shops, 4:3)
CELL_SQUARE = (512, 640)   # and of near-square ones (the porch twins, the stone houses: 0.8 to 0.95)
PAD = 8
MASK_DIV = 2
COLS = 4

# one front's nominal width and wall height in metres: the page cuts a wider wall into round(width / w) fronts
SETS = {   # w, h: a front's nominal width and wall height (m); step: the stoop's colour (photo sRGB); awn: the share of houses
    # whose ground floor takes a 3D awning. Round 181: the city's other house types, each picked by the property records
    'federal': {'w': 5.8, 'h': 11.0, 'gain': 0.88, 'step': '#e4e0d6', 'awn': 0.0},     # Society Hill: three storeys and a half, three bays
    'southrow': {'w': 4.7, 'h': 7.8, 'gain': 0.88, 'step': '#bdb8ae', 'awn': 0.45},    # South Philadelphia: two storeys, two bays
    'shop': {'w': 5.6, 'h': 11.0, 'gain': 0.88, 'step': '#bdb8ae', 'awn': 0.6},        # shops under two floors of flats
    'victorian': {'w': 5.6, 'h': 11.5, 'gain': 0.88, 'step': '#b9a08a', 'awn': 0.0},   # North Philadelphia, Fairmount: three storeys
    'porch': {'w': 6.4, 'h': 8.0, 'gain': 0.88, 'step': '#bdb8ae', 'awn': 0.0},        # West Philadelphia twins (the page builds the porch)
    'airlite': {'w': 5.0, 'h': 7.5, 'gain': 0.88, 'step': '#c4bfb5', 'awn': 0.3},      # the Northeast's 1930s to 1950s rows
    'newbuild': {'w': 5.5, 'h': 11.0, 'gain': 0.88, 'step': '#9a9a98', 'awn': 0.0},    # Fishtown, Point Breeze: 2010s and 2020s
    'stonetwin': {'w': 7.5, 'h': 9.0, 'gain': 0.88, 'step': '#c9c3b8', 'awn': 0.0},    # Germantown, Mount Airy: stone and stucco
    'siding': {'w': 4.8, 'h': 7.5, 'gain': 0.88, 'step': '#bdb8ae', 'awn': 0.35},      # Kensington, Port Richmond: siding rows
    # Round 184: six more, each with its own place or record (frontSetOf in app.js)
    'univcity': {'w': 6.8, 'h': 12.0, 'gain': 0.88, 'step': '#b9a08a', 'awn': 0.0},    # University City's Victorian twins (porched)
    'chestnut': {'w': 9.0, 'h': 9.5, 'gain': 0.88, 'step': '#c9c3b8', 'awn': 0.0},     # Chestnut Hill's stone houses
    'manayunk': {'w': 4.4, 'h': 7.6, 'gain': 0.88, 'step': '#bdb8ae', 'awn': 0.15},    # Manayunk's narrow hillside rows
    'loft': {'w': 12.0, 'h': 20.0, 'gain': 0.88, 'step': '#9a9a98', 'awn': 0.2},       # Old City, Callowhill: loft warehouses
    'mixeduse': {'w': 6.0, 'h': 14.5, 'gain': 0.88, 'step': '#bdb8ae', 'awn': 0.55},   # Center City: a shop under three floors
    'rittenhouse': {'w': 6.4, 'h': 15.0, 'gain': 0.88, 'step': '#b9a08a', 'awn': 0.0}, # Rittenhouse: four-storey townhouses
    # the realism pass: one-storey shops (a shop's record under 7 m)
    'shop1': {'w': 7.0, 'h': 5.25, 'gain': 0.88, 'step': '#bdb8ae', 'awn': 0.6},
}
# the sets whose fronts were made without their porch: the page builds one (Round 184: a flag, not the name)
PORCHED = ('porch', 'univcity')
# the towers' facade tiles (fetch_fronts.py TILES): one bay's width and one floor's height in metres, and whether the wall
# is mostly glass (its mask is then the darker half of the glass, not dark panes in a light wall)
TILES = {'glass': (1.6, 4.0, True), 'glassdark': (1.6, 4.0, True), 'precast': (1.6, 3.8, False), 'deco': (1.6, 3.9, False),
         'brick': (1.6, 2.9, False), 'resi': (1.6, 2.9, False), 'silver': (1.6, 4.0, True), 'blackgrid': (1.6, 3.8, True),
         'officebrick': (1.6, 3.7, False), 'glassresi': (1.6, 3.1, True),
         # Round 184: fifteen more kinds
         'goldglass': (1.6, 4.0, True), 'greenglass': (1.6, 4.0, True), 'ribbon': (1.6, 3.8, False), 'brutalist': (1.6, 3.8, False),
         'limestone': (1.6, 3.9, False), 'marble': (1.6, 3.8, False), 'terracotta': (1.6, 3.9, False), 'blueband': (1.6, 4.0, True),
         'unitized': (1.6, 4.0, True), 'hotel': (1.6, 2.9, False), 'granite': (1.6, 3.9, False), 'fins': (1.6, 4.0, True),
         'darkbrick': (1.6, 3.0, False), 'metalpanel': (1.6, 3.6, False), 'greygrid': (1.6, 3.8, False),
         # Round 185: the mid-rise walls
         'aptbrick': (1.6, 3.1, False), 'gardenapt': (1.6, 2.9, False), 'loftbrick': (1.6, 4.2, False), 'warehouse': (1.6, 4.5, False),
         'institution': (1.6, 4.2, False), 'modernapt': (1.6, 3.1, False), 'commercial': (1.6, 3.6, False),
         'paintedbrick': (1.6, 3.2, False), 'officemid': (1.6, 3.7, False), 'stucco': (1.6, 2.9, False)}
TILE = 1024        # the tower tiles are cropped at this, then written at 640 and a phone's 320 (Round 184: 25 kinds)
TILE_OUT = 640


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def erode(m, r):
    return ~dilate(~m, r)


def blobs(m):
    """Connected components of a boolean image (4-neighbour), as lists of (y, x) bounding boxes and pixel counts."""
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    out, n = [], 0
    for y0 in range(H):
        row = m[y0]
        for x0 in np.nonzero(row & (lab[y0] == 0))[0]:
            if lab[y0, x0]:
                continue
            n += 1
            stack = [(y0, x0)]
            lab[y0, x0] = n
            ys0 = ye = y0; xs0 = xe = x0; cnt = 0
            while stack:
                y, x = stack.pop()
                cnt += 1
                ys0 = min(ys0, y); ye = max(ye, y); xs0 = min(xs0, x); xe = max(xe, x)
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        stack.append((yy, xx))
            out.append((ys0, xs0, ye, xe, cnt))
    return out


def find_openings(img, fill_min=0.55):
    """Windows and the door of one front, as fractions of its width and height from the top-left: (wins, door). A front
    where no window passes is tried again at a fill of 0.38 (Round 184: panes with a sky reflection read under half dark,
    two of the 240 fronts, a loft and a mixed-use block); the bar stays where it was for every front that finds one."""
    # at half the generated size (768 x 1280): a muntin is about 2 px and the white frame between a shutter and its sash
    # about 5, so a 1 px close joins a sash's panes and leaves the shutters beside it apart
    # the realism pass: a wide front (the one-storey shops) at 640 by 480; every upright one still at 384 by 640, where
    # the thresholds below were set (they are fractions of the front; the shutter's shape is the one test in pixels)
    W, H = (640, 480) if img.width > img.height else (384, 640)
    a = np.asarray(img.convert('RGB').resize((W, H), Image.BILINEAR), np.float32) / 255.0
    L = lum(a)
    med = float(np.median(L))
    # glass is darker than the wall and neutral or cool, where brick is warm: a dark red brick reads as dark as a pane
    # by brightness alone, so a pane is well under the median and no redder than a grey, or very dark whatever its hue
    # (measured on the first five: a sky-lit pane reads 0.16 to 0.2 against a 0.35 brick, so the bar is 0.85 of the
    # median, held to neutral colours; a painted shutter is green, never glass, and is left out whatever its darkness)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g - r > 0.025) & (g - b > 0.015)
    dark = (((L < 0.85 * med) & (r - b < 0.06)) | ((L < 0.3 * med) & (r - b < 0.12))) & ~green   # brick in deep shade stays red
    closed = erode(dilate(dark, 1), 1)
    cand, door = [], None
    for y0, x0, y1, x1, _ in blobs(closed):
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        if bw < W * 0.035 or bh < H * 0.05:   # an awning's shadow line, a sliver
            continue
        fill = dark[y0:y1 + 1, x0:x1 + 1].mean()
        wide = img.width > img.height   # a one-storey shop: its display window is most of the front, and no band
        if fill < fill_min or bw / bh > (4.0 if wide else 2.5) or (not wide and bh > H * 0.35 and y1 < H * 0.85) or y0 > H * 0.85:   # bands, lattices, basement grilles (a tall door on a two-storey front is no band)
            continue
        cand.append([x0, y0, x1, y1])
    # the door: the tallest dark opening reaching into the lowest third, taller than a sash (a stoop can lift it) and
    # clearly taller than the openings' usual height (a green or red door is not dark glass, and then no window stands in)
    hs = sorted(c[3] - c[1] for c in cand)
    typical = hs[len(hs) // 2] if hs else 0
    for c in cand:
        x0, y0, x1, y1 = c
        if y1 > H * 0.7 and (y1 - y0) > max(min(H * 0.15, W * 0.22), typical * 1.15) and (x1 - x0) / (y1 - y0) < 0.7 and (door is None or y1 - y0 > door[3] - door[1]):
            door = c
    # a shutter is a narrow box with another box against its side at the same height (its sash, a frame away); a
    # narrow modern window stands clear of its neighbours
    def shutter(c):
        x0, y0, x1, y1 = c
        if (x1 - x0) / (y1 - y0) >= 0.36:
            return False
        gap = max(6, (x1 - x0) * 0.6)
        for o in cand:
            if o is c or o is door:
                continue
            over = min(y1, o[3]) - max(y0, o[1])
            if over > 0.3 * (y1 - y0) and (0 <= o[0] - x1 <= gap or 0 <= x0 - o[2] <= gap):   # a split sash covers half
                return True
        return False
    wins = [(c[0] / W, c[1] / H, (c[2] + 1) / W, (c[3] + 1) / H) for c in cand if c is not door and not shutter(c)]
    if door:
        door = (door[0] / W, door[1] / H, (door[2] + 1) / W, (door[3] + 1) / H)
    wins.sort(key=lambda b: (round(b[1] * 20), b[0]))
    if not wins and fill_min > 0.4:
        return find_openings(img, 0.38)
    return wins, door


def storeys(wins, door):
    """The front's storeys from its rows of openings, as fractions of its height from the foot: [the top of the ground
    floor, the top of the upper storeys' band, how many upper storeys], or None when fewer than two rows were found. A
    row is the openings whose spans overlap or nearly meet (a sash's two halves are one window: the finder may cut it at
    the meeting rail); the ground floor's top is halfway between its openings' heads and the next row's sills, and the
    upper storeys are as tall as their sills are apart."""
    boxes = sorted([(1 - b[3], 1 - b[1]) for b in wins + ([door] if door else [])])   # (sill, head) from the foot
    if len(boxes) < 2:
        return None
    hs = sorted(h - s for s, h in boxes)
    gap = 0.3 * hs[len(hs) // 2]
    rows = []
    for s_, h_ in boxes:
        if rows and s_ <= rows[-1][1] + gap:
            rows[-1][1] = max(rows[-1][1], h_)
            rows[-1][2].append(s_)
        else:
            rows.append([s_, h_, [s_]])
    rows = [r for r in rows if r[1] - r[0] > 0.025]
    if len(rows) < 2:
        return None
    sill = [r[0] for r in rows]
    head = [r[1] for r in rows]
    gf = (head[0] + sill[1]) / 2
    m = len(rows) - 1
    st = (sill[-1] - sill[1]) / (m - 1) if m >= 2 else (head[1] - sill[1]) + 2 * (sill[1] - gf)
    band = min(0.99, gf + m * st)
    if not (0.06 < gf < 0.7) or st < 0.04 or band < gf + 0.12:
        return None
    return [round(gf, 4), round(band, 4), m]


def wall_colour(im, wins, door):
    """The wall's mean colour (sRGB hex), its openings, the cornice's band (the top 12%) and the foot (8%) left out."""
    a = np.asarray(im.convert('RGB').resize((96, int(round(96 * im.height / im.width)))), np.float32) / 255.0
    H, W = a.shape[:2]
    keep = np.ones((H, W), bool)
    keep[:int(H * 0.12)] = False
    keep[int(H * 0.92):] = False
    for x0, y0, x1, y1 in wins + ([door] if door else []):
        keep[int(y0 * H):int(np.ceil(y1 * H)), int(x0 * W):int(np.ceil(x1 * W))] = False
    px = a[keep] if keep.any() else a.reshape(-1, 3)
    lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4).mean(0)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return '#%02x%02x%02x' % tuple(int(round(v * 255)) for v in np.clip(srgb, 0, 1))


def placeholder(set_, k):
    """A plain stand-in front (engine work only)."""
    rng = np.random.default_rng(1000 + k * 17 + (0 if set_ == 'federal' else 500))
    W, H = CELL
    bricks = [(150, 74, 56), (132, 66, 52), (168, 96, 70), (120, 70, 60), (190, 160, 130)]
    base = bricks[k % len(bricks)]
    a = np.zeros((H, W, 3), np.float32) + base
    a += rng.normal(0, 7, (H, W, 1))
    for y in range(0, H, 9):   # mortar courses
        a[y:y + 1] *= 0.82
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    floors = 3 if set_ == 'federal' else 2
    bays = 3 if set_ == 'federal' else 2
    top = int(H * 0.06)
    d.rectangle((0, 0, W, top), fill=(236, 232, 222))
    fh = (H - top - int(H * 0.08)) / floors
    for f in range(floors):
        for b in range(bays):
            if f == floors - 1 and b == (0 if k % 2 else bays - 1):
                cx = (b + 0.5) * W / bays
                d.rectangle((cx - W * 0.1, H - fh * 0.95, cx + W * 0.1, H - 12), fill=(30, 30, 34))
                continue
            cx, cy = (b + 0.5) * W / bays, top + (f + 0.5) * fh
            ww, wh = W * 0.16, fh * 0.55
            d.rectangle((cx - ww / 2 - 6, cy - wh / 2 - 6, cx + ww / 2 + 6, cy + wh / 2 + 6), fill=(236, 232, 222))
            d.rectangle((cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2), fill=(36, 44, 52))
            d.line((cx, cy - wh / 2, cx, cy + wh / 2), fill=(236, 232, 222), width=4)
            d.line((cx - ww / 2, cy, cx + ww / 2, cy), fill=(236, 232, 222), width=4)
    return im


def gutter(cell_img, W, H, pad):
    """The front shrunk into the cell inside the pad, its edge pixels run out across the gutter."""
    inner = cell_img.resize((W - 2 * pad, H - 2 * pad), Image.LANCZOS)
    a = np.asarray(inner)
    return Image.fromarray(np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode='edge'))


def data_url(im, fmt, **kw):
    b = io.BytesIO()
    im.save(b, fmt, **kw)
    mime = {'WEBP': 'image/webp', 'PNG': 'image/png', 'JPEG': 'image/jpeg'}[fmt]
    return 'data:%s;base64,%s' % (mime, base64.b64encode(b.getvalue()).decode('ascii'))


def bake_set(set_, fronts, preview):
    aspect = fronts[0][1].width / fronts[0][1].height
    W, H = CELL_WIDE if aspect > 1 else CELL_SQUARE if aspect >= 0.7 else CELL
    n = len(fronts)
    rows = math.ceil(n / COLS)
    atlas = Image.new('RGB', (COLS * W, rows * H), (0, 0, 0))
    mW, mH, mP = W // MASK_DIV, H // MASK_DIV, PAD // MASK_DIV
    # alpha: a window's height inside it from 0.5 at the sill to 1 at its head, and 1 everywhere else (never under a
    # half, so no browser's premultiplied decode can eat the colour channels)
    mask = Image.new('RGBA', (COLS * mW, rows * mH), (0, 0, 0, 255))
    cells = []
    for k, (fid, im) in enumerate(fronts):
        col, row = k % COLS, k // COLS
        atlas.paste(gutter(im.convert('RGB'), W, H, PAD), (col * W, row * H))
        wins, door = find_openings(im)
        m = Image.new('RGBA', (mW, mH), (0, 0, 0, 255))
        d = ImageDraw.Draw(m)
        iw, ih = mW - 2 * mP, mH - 2 * mP
        shop = set_ in ('shop', 'shop1', 'mixeduse')   # the realism pass: the shop under the flats is a shop too
        st = storeys(wins, door)
        # the shop's display glass: an opening in its ground floor (under the storeys' first floor line, the realism pass:
        # a fixed 0.6 from the head took a taller front's second floor for its shop window)
        gf_top = st[0] if st else (0.6 if set_ == 'shop1' else 0.4)
        # and on a front of storeys, only the openings that stand on the shop's own sill line: a tall shop window whose
        # head nearly meets the first floor's sills merges the two rows in storeys(), and the first floor's sashes were
        # lit as display glass (the realism pass's review of the shop mask)
        # (and never higher than a stoop's rise over the sidewalk: a shop whose own front is dark wood finds no opening
        # there, and its first floor's sashes were the lowest it found)
        s_min = min([1 - b[3] for b in wins + ([door] if door else [])] or [0])
        sill_top = 1.0 if set_ == 'shop1' else min(0.15, s_min + max(0.08, 0.4 * gf_top))
        for j, (x0, y0, x1, y1) in enumerate(wins):
            # b 128 marks a shop's display glass (the lower 40% of a shop front): lit more often and brighter
            gx0, gy0, gx1, gy1 = mP + x0 * iw, mP + y0 * ih, mP + x1 * iw - 1, mP + y1 * ih - 1
            ya, yb = int(round(gy0)), int(round(gy1))
            disp = shop and 1 - (y0 + y1) / 2 < gf_top and 1 - y1 < sill_top
            for y in range(ya, yb + 1):
                vp = (yb - y) / max(1, yb - ya)
                d.rectangle((gx0, y, gx1, y), fill=(255, (j * 37 + 11) % 256, 128 if disp else 0, int(round(128 + 127 * (1 - vp)))))
        if door:
            x0, y0, x1, y1 = door
            d.rectangle((mP + x0 * iw, mP + y0 * ih, mP + x1 * iw - 1, mP + y1 * ih - 1), fill=(0, 0, 255, 255))
        mask.paste(m, (col * mW, row * mH))
        # the cornice's colour: the front's top 3% (the page projects a cornice of it along the wall's head)
        top = np.asarray(im.convert('RGB').resize((64, 200), Image.BILINEAR))[:6].reshape(-1, 3)
        cor = '#%02x%02x%02x' % tuple(int(v) for v in np.median(top, axis=0))
        # the ground floor's openings: the span an awning covers, and the top it hangs over. Centred in the lowest 40% on a
        # front of three storeys or fewer; on a taller one in its lowest floor and a sixth (Round 184: on four-storey
        # mixed-use fronts and lofts the lowest 40% held the second floor's windows too, and the awning hung at their sills)
        gf_line = 0.3 if aspect > 1 else max(0.6, 1 - 1.15 / (SETS[set_]['h'] / 3.4))   # a one-storey shop is all ground floor
        gfo = [b for b in wins + ([door] if door else []) if (b[1] + b[3]) / 2 > gf_line]
        gf = [round(min(b[0] for b in gfo), 3), round(max(b[2] for b in gfo), 3), round(min(b[1] for b in gfo), 3)] if gfo else None
        cell = {'id': fid, 'wins': len(wins), 'door': [round(v, 3) for v in door] if door else None, 'cornice': cor, 'gf': gf,
                'wall': wall_colour(im, wins, door)}
        if st:
            cell['rows'] = st
        cells.append(cell)
        if preview:
            v = im.convert('RGB').resize((W, H))
            o = ImageDraw.Draw(v)
            for x0, y0, x1, y1 in wins:
                o.rectangle((x0 * W, y0 * H, x1 * W, y1 * H), outline=(255, 220, 0), width=3)
            if door:
                o.rectangle((door[0] * W, door[1] * H, door[2] * W, door[3] * H), outline=(0, 200, 255), width=3)
            v.save(os.path.join(preview, '%s-%s.jpg' % (set_, fid)), quality=85)
    spec = SETS[set_]
    # Round 184: files, not data URLs (art_files), and a phone's copy at half (its pad halves with it, so a cell's
    # fractions hold)
    half = atlas.resize((atlas.width // 2, atlas.height // 2), Image.LANCZOS)
    mhalf = mask.resize((mask.width // 2, mask.height // 2), Image.NEAREST)
    return {'img': art_files.write(atlas, 'fronts', set_, 'WEBP', quality=82, method=6),
            'imgHalf': art_files.write(half, 'fronts', set_ + '-half', 'WEBP', quality=80, method=6),
            'mask': art_files.write(mask, 'fronts', set_ + '-mask', 'PNG', optimize=True),
            'maskHalf': art_files.write(mhalf, 'fronts', set_ + '-mask-half', 'PNG', optimize=True),
            'cols': COLS, 'rows': rows, 'cell': [W, H], 'pad': PAD, 'w': spec['w'], 'h': spec['h'], 'gain': spec['gain'],
            'step': spec['step'], 'awn': spec.get('awn', 0), 'porch': int(set_ in PORCHED), 'aspect': round(aspect, 4), 'maskA': 1,
            'cells': cells}


def period(profile, expect):
    """The strongest repeat of a 1D profile within 0.6 to 1.5 times the expected one, in pixels, or None."""
    p = profile - profile.mean()
    n, best, lag0 = len(p), 0.0, None
    for lag in range(max(4, int(expect * 0.6)), min(n // 2, int(expect * 1.5)) + 1):
        c = float(np.dot(p[:-lag], p[lag:])) / (n - lag)
        if c > best:
            best, lag0 = c, lag
    return lag0 if best > 0.05 * float(np.dot(p, p)) / n else None


def fold_mask(glass, nx, ny):
    """The realism pass: a tile's window mask folded over its own repeats (nx bays by ny floors) into one bay and floor,
    the mean of every repeat, cut at a half and laid back over the tile, so every window is the same clean opening; with
    the height inside each opening (0 at its sill, 1 at its head) and the spandrel's height in the floor (from its foot,
    the row with the least glass), and the pier's place in the bay (the column with the least glass: the page's rooms are
    cut there, so no window straddles two). None when the repeats do not agree (a muddy fold: the period was not the windows')."""
    H, W = glass.shape
    Ux, Uy = max(4, int(round(W / nx))), max(4, int(round(H / ny)))
    ys, xs = np.mgrid[0:H, 0:W]
    ux = np.minimum(Ux - 1, ((xs % (W / nx)) / (W / nx) * Ux).astype(int))
    uy = np.minimum(Uy - 1, ((ys % (H / ny)) / (H / ny) * Uy).astype(int))
    acc = np.zeros((Uy, Ux)); cnt = np.zeros((Uy, Ux))
    np.add.at(acc, (uy, ux), glass.astype(np.float64)); np.add.at(cnt, (uy, ux), 1)
    unit = acc / np.maximum(cnt, 1)
    if (np.abs(unit - 0.5) > 0.3).mean() < 0.6:
        # a curtain wall whose mullions do not repeat with the bays: its floors still do, so the glass is the rows of the
        # floor that are glass across the whole tile (a ribbon a floor)
        prof = unit.mean(1, keepdims=True)
        if (np.abs(prof - 0.5) > 0.25).mean() < 0.7:
            return None
        unit = np.repeat(prof, Ux, 1)
    u = unit > 0.5
    u = erode(dilate(u, 1), 1)      # closed across a mullion's shadow
    u = dilate(erode(u, 1), 1)      # and opened, so no speck survives
    if not u.any() or u.all():
        return None
    u = fill_openings(u)
    # the height inside each opening: per column of the unit, each vertical run of glass from 0 at its foot to 1 at its head
    vp = np.zeros(u.shape)
    for x in range(Ux):
        y = 0
        while y < Uy:
            if not u[y, x]:
                y += 1
                continue
            y1 = y
            while y1 + 1 < Uy and u[y1 + 1, x]:
                y1 += 1
            n = max(1, y1 - y)
            for k in range(y, y1 + 1):
                vp[k, x] = (y1 - k) / n
            y = y1 + 1
    spand = round(1 - (int(np.argmin(u.mean(1))) + 0.5) / Uy, 3)
    pier = round((int(np.argmin(u.mean(0))) + 0.5) / Ux, 3)
    return u[uy, ux], vp[uy, ux], spand, pier


def fill_openings(u):
    """The realism pass's review of the lit towers: the glass a tile's paint shows dark is only part of each opening (a
    light curtain, a blind or a bright sky reflection fills the rest), and lit, a window glowed as a curtain-shaped cut-out.
    Each of the unit's dark shapes is filled out to its own box (the unit turned first so its emptiest column and row sit
    at its edges, and no opening is cut by them), unless the box would be most of the unit (a curtain wall's glass, or a
    ribbon of it, keeps its own shape) or the shape is a thread across it (under a fifth of its box)."""
    Uy, Ux = u.shape
    ry, rx = int(np.argmin(u.mean(1))), int(np.argmin(u.mean(0)))
    v = np.roll(np.roll(u, -ry, 0), -rx, 1)
    out = v.copy()
    for y0, x0, y1, x1, cnt in blobs(v):
        box = (y1 - y0 + 1) * (x1 - x0 + 1)
        if box < 0.8 * Uy * Ux and cnt >= 0.2 * box:
            out[y0:y1 + 1, x0:x1 + 1] = True
    return np.roll(np.roll(out, ry, 0), rx, 1)


# the realism pass's review of the lit towers: the tiles whose windows the dark-glass test cannot see (light curtains, a
# light or a ribbed glass, steel sash over a dark brick) and that are found instead as whatever is not their wall, the
# wall being the tile's commonest colour ('common') or its spandrel's ('spandrel'); each picked by eye from the overlays
# of all three tests over every masonry tile
WIN_BY_WALL = {'darkbrick': 'common', 'greygrid': 'common', 'hotel': 'common', 'loftbrick': 'common', 'officemid': 'spandrel'}


def wall_windows(m, glass, nx, ny, how):
    """A tile's windows as what is not its wall: its colour folded over its repeats into one bay and floor, the wall's
    colour found there (the fullest bin of a coarse histogram, or the median of the row the dark-glass test finds
    emptiest), and every texel further from it than the wall's own texels stray, or much darker, laid back over the tile."""
    H, W = glass.shape
    Ux, Uy = max(4, int(round(W / nx))), max(4, int(round(H / ny)))
    ys, xs = np.mgrid[0:H, 0:W]
    ux = np.minimum(Ux - 1, ((xs % (W / nx)) / (W / nx) * Ux).astype(int))
    uy = np.minimum(Uy - 1, ((ys % (H / ny)) / (H / ny) * Uy).astype(int))
    acc = np.zeros((Uy, Ux, 3)); cnt = np.zeros((Uy, Ux, 1)); ga = np.zeros((Uy, Ux))
    np.add.at(acc, (uy, ux), m); np.add.at(cnt, (uy, ux), 1); np.add.at(ga, (uy, ux), glass.astype(float))
    U = acc / np.maximum(cnt, 1)
    if how == 'common':
        q = np.clip((U * 6).astype(int), 0, 5)
        key = q[..., 0] * 36 + q[..., 1] * 6 + q[..., 2]
        wall = np.median(U[key == np.bincount(key.ravel(), minlength=216).argmax()], axis=0)
        T = 0.13
    else:
        row = U[int(np.argmin((ga / np.maximum(cnt[..., 0], 1)).mean(1)))]
        wall = np.median(row, axis=0)
        T = max(0.09, 3.0 * float(np.median(np.sqrt(((row - wall) ** 2).sum(-1)))) + 0.05)
    win = (np.sqrt(((U - wall) ** 2).sum(-1)) > T) | (lum(U) < 0.6 * float(lum(wall[None, None])[0, 0]))
    return win[uy, ux]


def bake_tile(tid, im, preview):
    """One tower tile: cropped to a whole number of its own bay and floor repeats, the edges cross-faded, at TILE px,
    with a half-size window mask; its size in metres from the repeats it holds."""
    bayW, floorH, glassy = TILES[tid]
    a = np.asarray(im.convert('RGB'), np.float32) / 255.0
    H, W = a.shape[:2]
    L = lum(a)
    px, py = period(L.mean(0), W / 10), period(L.mean(1), H / 4)
    nx = max(1, W // px) if px else 10
    ny = max(1, H // py) if py else 4
    cw, ch = (nx * px if px else W), (ny * py if py else H)
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    t = Image.fromarray((a[y0:y0 + ch, x0:x0 + cw] * 255).astype(np.uint8)).resize((TILE, TILE), Image.LANCZOS)
    b = np.asarray(t, np.float32)
    k = 16   # cross-fade each edge with the opposite one so a near-repeat closes
    w = np.linspace(0.5, 0.0, k)[None, :, None]
    left, right = b[:, :k].copy(), b[:, -k:][:, ::-1].copy()
    b[:, :k] = left * (1 - w) + right * w
    b[:, -k:] = (right * (1 - w) + left * w)[:, ::-1]
    w2 = np.linspace(0.5, 0.0, k)[:, None, None]
    top, bot = b[:k].copy(), b[-k:][::-1].copy()
    b[:k] = top * (1 - w2) + bot * w2
    b[-k:] = (bot * (1 - w2) + top * w2)[::-1]
    t = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8))
    m = np.asarray(t.resize((TILE // 2, TILE // 2), Image.BILINEAR), np.float32) / 255.0
    Lm = lum(m)
    if glassy:
        glass = Lm < np.percentile(Lm, 60)
    else:
        med = float(np.median(Lm))
        glass = ((Lm < 0.72 * med) & (m[..., 0] - m[..., 2] < 0.08)) | (Lm < 0.3 * med)
        if tid in WIN_BY_WALL and px and py:
            glass = wall_windows(m, glass, nx, ny, WIN_BY_WALL[tid])
    mk = np.zeros(m.shape[:2] + (4,), np.uint8)
    mk[..., 3] = 255
    folded = fold_mask(glass, nx, ny) if px and py else None
    spand = pier = None
    if folded is not None:
        glass, vpos, spand, pier = folded
        mk[..., 3] = np.where(glass, np.round(128 + 127 * vpos), 255).astype(np.uint8)
    mk[..., 0] = np.where(glass, 255, 0)
    if preview:
        t.save(os.path.join(preview, 'tile-%s.jpg' % tid), quality=85)
        Image.fromarray(mk).save(os.path.join(preview, 'tile-%s-mask.png' % tid))
    full, half = t.resize((TILE_OUT, TILE_OUT), Image.LANCZOS), t.resize((TILE_OUT // 2, TILE_OUT // 2), Image.LANCZOS)
    mki = Image.fromarray(mk)
    return {'img': art_files.write(full, 'tiles', tid, 'WEBP', quality=80, method=6),
            'imgHalf': art_files.write(half, 'tiles', tid + '-half', 'WEBP', quality=78, method=6),
            'mask': art_files.write(mki.resize((TILE_OUT // 2, TILE_OUT // 2), Image.NEAREST), 'tiles', tid + '-mask', 'PNG', optimize=True),
            'w': round(nx * bayW, 2), 'h': round(ny * floorH, 2), 'nb': int(nx), 'nf': int(ny), 'glass': glassy,
            'period': [int(px or 0), int(py or 0)], 'folded': int(folded is not None), 'spandV': spand, 'pierU': pier}


BASE_H = 4.5   # a street floor's height in metres (fetch_fronts.py BASE_FRAME)
BASE_TOP, BASE_FOOT = 0.05, 0.92   # the share of a street floor's image kept, from its head


def bake_base(bid, im, preview):
    """The realism pass (critic gap 4): one street floor under the tower and mid-rise walls, made to repeat along the
    street: its edges cross-faded with each other, written at 768 by 512 and a phone's 384 by 256, with a window mask
    (its dark glass, lit after dark); its width in metres from its height (one storey, BASE_H)."""
    # the sidewalk the model draws along the foot and the sill of the storey over it along the head come off (a pale
    # band of paving at a wall's foot read as a plinth of light)
    im = im.convert('RGB')
    im = im.crop((0, int(round(im.height * BASE_TOP)), im.width, int(round(im.height * BASE_FOOT))))
    a = np.asarray(im.resize((1024, 683), Image.LANCZOS), np.float32)
    k = 24
    w = np.linspace(0.5, 0.0, k)[None, :, None]
    left, right = a[:, :k].copy(), a[:, -k:][:, ::-1].copy()
    a[:, :k] = left * (1 - w) + right * w
    a[:, -k:] = (right * (1 - w) + left * w)[:, ::-1]
    t = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    m = np.asarray(t.resize((384, 256), Image.BILINEAR), np.float32) / 255.0
    Lm = lum(m)
    med = float(np.median(Lm))
    glass = ((Lm < 0.6 * med) & (m[..., 0] - m[..., 2] < 0.08)) | (Lm < 0.25 * med)
    glass = dilate(erode(erode(dilate(glass, 1), 1), 1), 1)
    glass[int(0.92 * glass.shape[0]):] = False   # the sidewalk line is never glass
    mk = np.zeros(m.shape[:2] + (4,), np.uint8)
    mk[..., 0] = np.where(glass, 255, 0)
    mk[..., 3] = 255
    if preview:
        t.save(os.path.join(preview, 'base-%s.jpg' % bid), quality=85)
        Image.fromarray(mk[..., :3]).save(os.path.join(preview, 'base-%s-mask.png' % bid))
    return {'img': art_files.write(t.resize((768, 512), Image.LANCZOS), 'tiles', 'base-' + bid, 'WEBP', quality=80, method=6),
            'imgHalf': art_files.write(t.resize((384, 256), Image.LANCZOS), 'tiles', 'base-' + bid + '-half', 'WEBP', quality=78, method=6),
            'mask': art_files.write(Image.fromarray(mk), 'tiles', 'base-' + bid + '-mask', 'PNG', optimize=True),
            'w': round(BASE_H * 1536 / (1024 * (BASE_FOOT - BASE_TOP)), 2), 'h': BASE_H}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--placeholder', action='store_true')
    ap.add_argument('--preview', default='')
    ap.add_argument('--partial', action='store_true', help='skip a set with no fronts yet (engine work while a run is going)')
    a = ap.parse_args()
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
    sets = {}
    for set_ in SETS:
        if a.placeholder:
            fronts = [('p%d' % k, placeholder(set_, k)) for k in range(8)]
        else:
            # the realism pass: a set made again at its own proportions, once all sixteen are there
            d5 = os.path.join(RAW5, set_)
            n5 = sorted(f for f in os.listdir(d5) if f.endswith('.png')) if os.path.isdir(d5) else []
            d = d5 if len(n5) >= 16 else os.path.join(RAW, set_)
            names = sorted(f for f in os.listdir(d) if f.endswith('.png')) if os.path.isdir(d) else []
            fronts = [(os.path.splitext(f)[0], Image.open(os.path.join(d, f))) for f in names]
        if not fronts and a.partial:
            print('%-9s skipped: no fronts yet' % set_)
            continue
        if not fronts:
            sys.exit('no fronts for %s in %s (run fetch_fronts.py, or --placeholder for engine work)' % (set_, RAW))
        sets[set_] = bake_set(set_, fronts, a.preview)
        print('%-9s %d fronts, %d windows, %d doors, atlas %d KB, mask %d KB' % (
            set_, len(fronts), sum(c['wins'] for c in sets[set_]['cells']), sum(bool(c['door']) for c in sets[set_]['cells']),
            art_files.size(sets[set_]['img']) // 1024, art_files.size(sets[set_]['mask']) // 1024))
    tiles = {}
    td = os.path.join(RAW, 'tower')
    if not a.placeholder and os.path.isdir(td):
        for f in sorted(os.listdir(td)):
            tid = os.path.splitext(f)[0]
            if f.endswith('.png') and tid in TILES:
                tiles[tid] = bake_tile(tid, Image.open(os.path.join(td, f)), a.preview)
                print('tile %-9s %d x %d bays and floors, %.1f x %.1f m, period %s, %d KB' % (
                    tid, tiles[tid]['nb'], tiles[tid]['nf'], tiles[tid]['w'], tiles[tid]['h'], tiles[tid]['period'],
                    art_files.size(tiles[tid]['img']) // 1024))
    bases = {}
    bd = os.path.join(RAW5, 'base')
    if not a.placeholder and os.path.isdir(bd):
        for f in sorted(os.listdir(bd)):
            if f.endswith('.png'):
                bid = os.path.splitext(f)[0]
                bases[bid] = bake_base(bid, Image.open(os.path.join(bd, f)), a.preview)
                print('base %-9s %.2f x %.1f m, %d KB' % (bid, bases[bid]['w'], bases[bid]['h'], art_files.size(bases[bid]['img']) // 1024))
    print('pruned %d old front files, %d old tile files' % (art_files.prune('fronts'), art_files.prune('tiles')))
    out = {'v': 5, 'placeholder': a.placeholder, 'sets': sets, 'tiles': tiles, 'bases': bases}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f MB' % (os.path.getsize(OUT) / 1e6), '(placeholder)' if a.placeholder else '')


if __name__ == '__main__':
    main()
