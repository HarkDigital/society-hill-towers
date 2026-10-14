#!/usr/bin/env python3
"""Bake City Hall's facades (Round 191, Mike: "I want City hall ... to be totally revamped") into cityhall_art.json,
which build.py inlines as CITYHALL_ART, and one atlas with its mask into art/cityhall/ (art_files.py: files the page loads
on demand, a phone's half copies beside them).

fetch_cityhall_art.py makes one straight-on elevation a cell (lidar_cache/cityhall_art_raw/<id>.png): a wing section of
four bays, the three bays beside a centre pavilion, a centre pavilion's front, a corner pavilion's face, the courtyard's
wall (fix2: the plain north face's, the east, west and south faces' with their great arched windows, and the bay over each
passage's courtyard end), the tower's stages, the clock stage, a face of the dome, the dormers, a turret's top stage, the
apse, a balustrade, a patch of plain ashlar and the tower's channel-jointed courses. Every pane is a flat chroma-key green,
and every opening the page cuts (the centre pavilion's great arch, the bay's small arch, the apse's door) a flat magenta.

Per cell the bake:
- crops the picture to the part (CELLS: the pavement under a facade, the background beside the clock stage's columns);
- keys the glass (KEY_*) to the pixel, takes the key's green spill off the frames round it, and fills each pane with dark
  glass, lighter toward its head, inside a dark sash frame with a meeting rail across a tall sash and a muntin down a wide
  one (fix2); the clock's dial (the largest key in the clock cell) is filled with the dial's teal and a gilt ring, every
  magenta opening with the passage's shade (the near level cuts the opening there; the far level has no passage, fix1);
- blurs out any carving the image model drew as lettering (SOFTEN), calibrates the picture's median stone to the
  photographs' weathered marble (MARBLE), the tower's cleaner masonry (TOWER_STONE) or its painted metal (METAL), and
  takes every recess of the stone darker (SOOT, fix2);
- takes its storeys to the building's own (rows: a pixel row of the picture to a height in metres, piecewise linear,
  so the string courses meet the cornices the page builds at the measured heights, 5.57, 15.78 and 26.63 m on the wings);
- is laid at a common pixels-a-metre (the largest that packs every cell into AW by AH with PAD of gutter, times the
  cell's dens weight: the courtyard and the apse are seen from nearer the ground but less often) and its edge pixels run
  out across the gutter, wrapped for a cell that tiles (the wings, the courtyard, the turret, the balustrade, the ashlar).

The mask is opaque RGB at MASK_DIV of the atlas (bake_fronts.py's convention: an image with alpha reaches WebGL through a
premultiplied decode on WebKit): r the glass, g the window's number (1 to 255, for the night's rooms), b on the glass the
height within its pane (2 at its foot to 117 at its head, fix2), b 200 the dial's glass, 120 a dark void and 60 the sky
between the balusters (cut out). The manifest names the files and carries every cell's rect in texture uv (v up, as the page
samples a flipped image), its size in metres, its mean colour (the far level's vertex colours), and what the page builds
to the picture: the portal's arch on the centre pavilion, the small arch on the courtyard's bay and the apse's door
(fix2), the dial's centre and radius on the clock stage.

Usage: python3 bake_cityhall_art.py [--preview DIR]"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'cityhall_art_raw')
OUT = os.path.join(HERE, 'cityhall_art.json')
AW, AH = 2048, 2048
PAD = 16
MASK_DIV = 2
FILL = 0.97          # the share of the atlas the packer first tries the cells' area at (it steps down 1% a try until they pack)
MARBLE = (182, 176, 164)   # the block's marble with its soiling, as the photographs read it (fix2, the review: at (201, 196,
                           # 184) the block read pristine white, 190 to 220 in the sun and 191 under an overcast, where the
                           # photographs show a weathered warm grey under a cleaner tower)
TOWER_STONE = (190, 186, 176)   # the tower's masonry to 102.8 m: cleaner than the block (cleaned with the tower's restoration),
                                # warmer than the painted iron above it (fix1: S Broad Street at dusk reads the belvedere (149, 152,
                                # 143) under the clock stage's (154, 165, 169) and the dome's (155, 168, 176): the two-tone tower)
SOOT = 0.55                # fix2: the recesses' soot, how far a pixel darker than its surroundings is taken darker still
METAL = (188, 192, 198)    # the tower's paint from the clock stage up (0xc8ccd1 in the photographs' sun; a shade under it here,
                           # where the sun and the sky's specular add their own)
GLASS_TOP, GLASS_FOOT = (58, 70, 80), (20, 27, 33)   # a pane's sky reflection at its head, its dark foot
FRAME = (52, 48, 44)       # the meeting rail of a sash
DIAL, GILT = (90, 144, 138), (213, 193, 152)        # the dial's teal glass and its gilding
VOID = (16, 17, 19)
PORTAL = (36, 34, 31)      # the portal's arch on the centre pavilion's picture: the passage's shade (fix1: the stone, so the far
                           # level showed a blank wall where the arch is)
KEY_GAP, KEY_K = 35, 1.6  # a pane's green: over the other channels by KEY_GAP and KEY_K times the larger (fix1: the old key,
                          # green over 140 and 70 over the rest, left the shaded green in every arched window's head)
SPILL = 8                 # a frame pixel by the glass whose green stands this far over red and blue is the key's spill

# id: source, (width, height) in metres, crop (x0, y0, x1, y1) in source pixels or None, rows [(pixel row from the crop's
# top, metres from the cell's foot)], 'stone', 'tower' or 'metal', wraps across, density weight
CELLS = {
    'curtain': ('ch_curtain', (16.0, 26.63), (0, 0, 1024, 1688), [(0, 26.63), (115, 25.23), (860, 15.78), (1465, 5.57), (1688, 0)], 'stone', True, 1.0),
    'flank': ('ch_flank', (16.0, 26.63), (0, 0, 1024, 1665), [(0, 26.63), (110, 25.23), (760, 15.78), (1370, 5.57), (1665, 0)], 'stone', True, 1.0),
    'centre': ('ch_centre', (27.0, 39.28), (0, 0, 1104, 1550), [(0, 39.28), (1550, 0)], 'stone', False, 1.0),
    'corner': ('ch_corner', (16.5, 38.13), (0, 0, 832, 1828), [(0, 38.13), (650, 26.63), (1190, 15.78), (1645, 5.57), (1828, 0)], 'stone', False, 1.0),
    'court': ('ch_court', (16.0, 31.5), (0, 0, 816, 1560), [(0, 31.5), (320, 26.63), (900, 15.78), (1390, 5.57), (1560, 0)], 'stone', True, 0.6),
    # fix2: the courtyard's east, west and south faces (tall sash and great arched windows) and the bay over each passage's
    # courtyard end (an arched window over a columned one over a pedimented door, the passage's own small arch at its foot);
    # the north face by the tower and the forecourt's sides keep 'court'
    'court_main': ('ch_court_main', (16.0, 31.5), (0, 0, 816, 1510), [(0, 31.5), (330, 26.63), (810, 15.78), (1330, 5.57), (1510, 0)], 'stone', True, 0.72),
    'court_bay': ('ch_court_bay', (14.0, 31.5), (0, 0, 704, 1520), [(0, 31.5), (1290, 5.57), (1520, 0)], 'stone', False, 0.72),
    'tower_low': ('ch_tower_low', (22.6, 24.5), None, [(0, 24.5), (1104, 0)], 'tower', False, 0.85),   # fix2: the channel-jointed shaft
    'tower_mid': ('ch_tower_mid', (21.0, 21.5), None, [(0, 21.5), (1056, 0)], 'tower', False, 0.85),
    'belvedere': ('ch_belvedere', (21.0, 12.6), None, [(0, 12.6), (832, 0)], 'tower', False, 0.9),
    'clock': ('ch_clock', (20.0, 20.6), (60, 25, 964, 910), [(0, 20.6), (885, 0)], 'metal', False, 0.9),
}
LATE = {
    'dome': ('ch_dome', (7.1, 19.0), None, [(0, 19.0), (1664, 0)], 'metal', False, 0.9),
    'dormer_w': ('ch_dormer_w', (2.4, 4.4), None, [(0, 4.4), (1280, 0)], 'stone', False, 1.2),
    'dormer_c': ('ch_dormer_c', (4.0, 8.0), None, [(0, 8.0), (1408, 0)], 'stone', False, 1.1),
    'aedicule': ('ch_aedicule', (8.0, 10.3), None, [(0, 10.3), (1072, 0)], 'stone', False, 1.0),
    'oculus': ('ch_oculus', (2.0, 2.4), None, [(0, 2.4), (912, 0)], 'stone', False, 1.3),
    'turret': ('ch_turret', (8.5, 9.6), None, [(0, 9.6), (1152, 0)], 'stone', True, 0.8),
    'apse': ('ch_apse', (19.8, 24.5), (20, 55, 990, 1180), [(0, 24.5), (1125, 0)], 'stone', False, 0.7),   # fix2: the banded half-drum, its door centred
    'rustic': ('ch_rustic', (4.65, 3.56), (0, 183, 1024, 967), [(0, 3.56), (784, 0)], 'tower', 'xy', 1.0),   # fix2: four of the tower's courses, for the batter
    'ashlar': ('ch_ashlar', (4.0, 4.0), None, [(0, 4.0), (1024, 0)], 'stone', 'xy', 1.0),
    'balus': ('ch_balustrade', (3.3, 1.1), None, [(0, 1.1), (512, 0)], 'stone', True, 1.4),
}


# the free-standing columns measured on the pictures (source pixels, after the crop): the shaft's centre across, the
# capital's top, the shaft's top and foot, its diameter. The page stands a half-round column on the wall at each, its
# capital and base, wearing the picture projected from the wall, so the built column covers the painted one at any angle
COLS = {
    # the centre pavilion: the principal storey's two pairs and two singles, the upper storey's tall and short columns
    'centre': [(78, 712, 770, 1085, 60), (269, 712, 770, 1085, 58), (338, 712, 770, 1085, 60), (763, 712, 770, 1085, 60), (829, 712, 770, 1085, 58), (1023, 712, 770, 1085, 60),
               (82, 130, 195, 520, 56), (282, 130, 195, 520, 48), (340, 240, 295, 520, 50), (767, 240, 295, 520, 52), (825, 130, 195, 520, 50), (1022, 130, 195, 520, 56)],
    # the flank's two great columns of the principal storey (the half columns at the cell's edges are left painted)
    'flank': [(347, 800, 840, 1300, 52), (675, 800, 840, 1300, 52)],
    # the corner pavilion's face: the paired columns at both edges on the principal and the second storeys
    'corner': [(52, 1240, 1300, 1565, 55), (120, 1240, 1300, 1565, 55), (708, 1240, 1300, 1565, 57), (778, 1240, 1300, 1565, 56),
               (57, 695, 755, 1095, 46), (116, 695, 755, 1095, 48), (737, 695, 755, 1095, 46), (795, 695, 755, 1095, 46)],
}


def lum(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy or dx:
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def label(m):
    """4-neighbour connected components of a boolean image: (labels, [(y0, x0, y1, x1, count)]) with labels from 1."""
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    boxes = []
    n = 0
    for y0 in range(H):
        row = m[y0]
        for x0 in np.nonzero(row & (lab[y0] == 0))[0]:
            if lab[y0, x0]:
                continue
            n += 1
            lab[y0, x0] = n
            st = [(y0, x0)]
            ya = yb = y0; xa = xb = x0; c = 0
            while st:
                y, x = st.pop()
                c += 1
                if y < ya: ya = y
                if y > yb: yb = y
                if x < xa: xa = x
                if x > xb: xb = x
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        st.append((yy, xx))
            boxes.append((ya, xa, yb, xb, c))
    return lab, boxes


def box_blur(L, r):
    """A box blur of radius r (summed-area table, edges clamped)."""
    H, W = L.shape
    P = np.pad(L, ((r + 1, r), (r + 1, r)), mode='edge').astype(np.float64)
    S = P.cumsum(0).cumsum(1)
    k = 2 * r + 1
    return ((S[k:k + H, k:k + W] - S[0:H, k:k + W] - S[k:k + H, 0:W] + S[0:H, 0:W]) / (k * k)).astype(np.float32)


# fix2: carving the image model drew as lettering (an inscription round the forecourt bay's arch, illegible but read as
# letters), blurred out in source pixels: (cell, centre x, centre y, inner radius, outer radius, lowest row)
SOFTEN = [('court_bay', 350, 317, 126, 158, 330)]


def soften(cid, a):
    from PIL import ImageFilter
    for c, cx, cy, r0, r1, ymax in SOFTEN:
        if c != cid:
            continue
        H, W = a.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.hypot(xx - cx, yy - cy)
        m = (d >= r0) & (d <= r1) & (yy <= ymax)
        bl = np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(np.float32)
        a[m] = bl[m]
    return a


def keys(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = np.maximum(r, b)
    green = (g - mx > KEY_GAP) & (g > KEY_K * mx + 8)
    magenta = (r > 170) & (b > 170) & (g < 110)
    return green, magenta


def prep(cid, spec):
    """One cell's colour and mask at its source resolution (cropped), and what the page builds to it."""
    src, (wm, hm), crop, rows, kind, wrap, dens = spec
    im = Image.open(os.path.join(RAW, src + '.png')).convert('RGB')
    if crop:
        im = im.crop(crop)
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    green, magenta = keys(a)
    green = dilate(green, 1) & ~magenta
    magenta = dilate(magenta, 1)
    # the key's spill on the frames round the glass: green over the other channels there, taken down to their mean
    near = dilate(green | magenta, 4) & ~(green | magenta)
    gmax = np.maximum(a[..., 0], a[..., 2])
    sp = near & (a[..., 1] - gmax > SPILL)
    a[sp, 1] = gmax[sp] + SPILL * 0.3
    far = dilate(green, 2) & ~green   # a frame pixel right by a pane: any green cast at all taken off
    sp2 = far & (a[..., 1] > gmax)
    a[sp2, 1] = gmax[sp2]
    spm = near & (np.minimum(a[..., 0], a[..., 2]) - a[..., 1] > SPILL)
    a[spm, 0] = a[spm, 1]; a[spm, 2] = a[spm, 1]
    # the stone's calibration: the median of everything that is not a key to the photographs' colour, per channel
    rest = ~(green | magenta)
    med = np.median(a[rest], axis=0)
    tgt = np.array(METAL if kind == 'metal' else TOWER_STONE if kind == 'tower' else MARBLE, np.float32)
    a = np.clip(a * (tgt / np.maximum(med, 1.0)), 0, 255)
    a = soften(cid, a)
    # fix2, the soot: a pixel darker than the stone round it (a joint, a reveal, the underside of a cornice, the deep of a
    # carving) taken darker still, as the photographs' weathered marble holds its dirt in every recess; the painted iron is
    # cleaner and keeps its picture
    if kind != 'metal':
        L = lum(np.where((green | magenta)[..., None], med[None, None], a))
        Lb = box_blur(L, max(2, int(round(0.35 * W / wm))))
        f = np.clip(L / np.maximum(Lb, 1.0), 0.35, 1.0) ** SOOT
        a = a * f[..., None]
    lab, boxes = label(green)
    mask = np.zeros((H, W, 3), np.uint8)
    meta = {}
    dial = void = 0
    if boxes:
        big = 1 + int(np.argmax([bx[4] for bx in boxes]))
        if cid == 'clock':
            dial = big   # (fix2: the belvedere's arch is glazed now, a window like any other, no longer a void)
    yy, xx = np.mgrid[0:H, 0:W]
    win = 0
    for k, (y0, x0, y1, x1, c) in enumerate(boxes, start=1):
        m = lab == k
        if c < 12:
            continue
        if k == dial:
            cx, cy, rr = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2
            d = np.hypot(xx - cx, yy - cy) / rr
            col = np.zeros((H, W, 3), np.float32) + np.array(DIAL, np.float32)
            col *= (0.92 + 0.08 * (yy - y0) / max(1, y1 - y0))[..., None]
            ring = (np.abs(d - 0.88) < 0.035) | (np.abs(d - 0.66) < 0.02)
            ang = np.arctan2(yy - cy, xx - cx)
            ticks = (d > 0.70) & (d < 0.84) & (np.abs(((ang / (2 * np.pi) * 12) + 0.5) % 1 - 0.5) < 0.06)
            col[ring | ticks] = GILT
            a[m] = col[m]
            mask[m] = (255, 0, 200)
            meta['dial'] = [cx / W, 1 - cy / H, rr / W, rr / H]   # centre (u, v from the foot) and radius as fractions
            continue
        if k == void:
            a[m] = VOID
            mask[m] = (0, 0, 120)
            continue
        if cid == 'balus':   # the sky between the balusters: cut out by the page (b 60), its colour the stone's for the mips
            a[m] = np.median(a[rest], axis=0)
            mask[m] = (0, 0, 60)
            continue
        win += 1
        t = np.clip((yy - y0) / max(1, y1 - y0), 0, 1)
        col = np.array(GLASS_TOP, np.float32)[None, None] * (1 - t[..., None]) + np.array(GLASS_FOOT, np.float32)[None, None] * t[..., None]
        a[m] = col[m]
        mask[m, 0] = 255
        mask[m, 1] = 1 + (win - 1) % 255
        # fix2: the pane's own height in the blue (2 at its foot to 117 at its head, under the dial's 200 and the void's 120),
        # for the night's rooms: a lamp-lit ceiling over a darker floor, a blind drawn part way
        mask[m, 2] = np.round(2 + 115 * (1 - t[m])).astype(np.uint8)
        h, w = y1 - y0 + 1, x1 - x0 + 1
        # fix2 (the review: every pane a flat navy panel): the sash's frame round the glass, its meeting rail, and a muntin
        # down a wide pane, in the frames' dark bronze, none of it glass in the mask (worked in the pane's own box)
        ppm_s = W / wm
        fr = max(2, int(round(0.055 * ppm_s)))
        by0, by1, bx0, bx1 = max(0, y0 - 1), min(H, y1 + 2), max(0, x0 - 1), min(W, x1 + 2)
        mb = m[by0:by1, bx0:bx1]
        inner = ~dilate(~mb, fr) if min(h, w) > 4 * fr else mb
        bars = mb & ~inner
        if h > 1.6 * w and h > 40:   # a tall sash: the meeting rail across its middle
            ry = y0 + int(h * 0.52) - by0
            th = max(2, int(h * 0.022), fr)
            bars[ry:ry + th] |= mb[ry:ry + th]
        if w / ppm_s > 0.9 and h / ppm_s > 1.0:   # a wide pane: one muntin down its middle
            cx0 = (x0 + x1) // 2 - bx0 - fr // 2
            bars[:, cx0:cx0 + fr] |= mb[:, cx0:cx0 + fr]
        reg = a[by0:by1, bx0:bx1]
        reg[bars] = FRAME
        mreg = mask[by0:by1, bx0:bx1]
        mreg[bars] = 0
    if magenta.any():
        a[magenta] = PORTAL   # the far level draws no passage: the arch reads dark there (the near level cuts it open)
        mask[magenta] = (0, 0, 120)
        ys, xs = np.nonzero(magenta)
        # the arch: its span and crown, and its springing, the highest row the opening holds 95% of its width
        widths = magenta.sum(1)
        full = widths.max()
        spring = int(np.nonzero(widths >= 0.95 * full)[0].min())
        meta['arch'] = [xs.min() / W, (xs.max() + 1) / W, ys.min(), spring, ys.max() + 1]   # rows remapped below
    return a, mask, meta


def remap_rows(img, rows, hm, ppm, w_out, resample):
    """The picture's rows taken to the cell's metres, band by band (rows: (pixel row, metres) from the top down)."""
    H_out = int(round(hm * ppm))
    out = Image.new(img.mode, (w_out, H_out))
    ys = [int(round((hm - m) * ppm)) for _, m in rows]
    for (p0, _), (p1, _), y0, y1 in zip(rows, rows[1:], ys, ys[1:]):
        if y1 <= y0 or p1 <= p0:
            continue
        band = img.crop((0, p0, img.width, p1)).resize((w_out, y1 - y0), resample)
        out.paste(band, (0, y0))
    return out


def row_to_m(rows, p):
    for (p0, m0), (p1, m1) in zip(rows, rows[1:]):
        if p0 <= p <= p1:
            return m0 + (m1 - m0) * (p - p0) / max(1e-6, p1 - p0)
    return rows[-1][1]


def blend_wrap(a, frac=0.06, axis=1):
    """A cell that tiles: each side strip eased toward the far side's edge pixels (half way at the very edge, none
    frac of the way in), so the two edges meet on one colour where the cell repeats."""
    if axis == 0:
        return blend_wrap(a.transpose(1, 0, 2), frac, 1).transpose(1, 0, 2)
    W = a.shape[1]
    n = max(2, int(W * frac))
    out = a.copy()
    w = np.linspace(0.5, 0.0, n)[None, :, None]
    edgeL, edgeR = a[:, :1], a[:, W - 1:W]
    mid = (edgeL + edgeR) / 2
    out[:, :n] = a[:, :n] * (1 - w) + mid * w
    out[:, W - n:] = a[:, W - n:] * (1 - w[:, ::-1]) + mid * w[:, ::-1]
    return out


def pack(sizes, aw, ah, pad):
    """Rects for (w, h) sizes on a skyline, tallest first, each at the lowest place it fits (the leftmost of those);
    None when they do not fit. Positions are the cells' own corners inside their pad."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    sky = [(0, aw, 0)]   # (x0, x1, height of the skyline there)
    pos = [None] * len(sizes)
    for i in order:
        w, h = sizes[i][0] + 2 * pad, sizes[i][1] + 2 * pad
        best = None
        xs = sorted({seg[0] for seg in sky} | {seg[1] - w for seg in sky if seg[1] - w >= 0})
        for x in xs:
            if x < 0 or x + w > aw:
                continue
            top = max(seg[2] for seg in sky if seg[0] < x + w and seg[1] > x)
            if top + h <= ah and (best is None or (top, x) < (best[1], best[0])):
                best = (x, top)
        if best is None:
            return None
        x, top = best
        pos[i] = (x + pad, top + pad)
        nxt = []
        for x0, x1, hh in sky:
            if x1 <= x or x0 >= x + w:
                nxt.append((x0, x1, hh))
                continue
            if x0 < x:
                nxt.append((x0, x, hh))
            if x1 > x + w:
                nxt.append((x + w, x1, hh))
        nxt.append((x, x + w, top + h))
        sky = sorted(nxt)
    return pos


def gutter(atlas, x, y, w, h, pad, wrap):
    """Run a cell's edge pixels out across its gutter (wrapped across for a cell that tiles)."""
    a = atlas
    if wrap:
        a[y:y + h, x - pad:x] = a[y:y + h, x + w - pad:x + w]
        a[y:y + h, x + w:x + w + pad] = a[y:y + h, x:x + pad]
    else:
        a[y:y + h, x - pad:x] = a[y:y + h, x:x + 1]
        a[y:y + h, x + w:x + w + pad] = a[y:y + h, x + w - 1:x + w]
    if wrap == 'xy':
        a[y - pad:y, x - pad:x + w + pad] = a[y + h - pad:y + h, x - pad:x + w + pad]
        a[y + h:y + h + pad, x - pad:x + w + pad] = a[y:y + pad, x - pad:x + w + pad]
    else:
        a[y - pad:y, x - pad:x + w + pad] = a[y:y + 1, x - pad:x + w + pad]
        a[y + h:y + h + pad, x - pad:x + w + pad] = a[y + h - 1:y + h, x - pad:x + w + pad]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    cells = dict(CELLS)
    cells.update(LATE)
    have = {k: v for k, v in cells.items() if os.path.exists(os.path.join(RAW, v[0] + '.png'))}
    missing = sorted(set(cells) - set(have))
    if missing:
        sys.exit('ERROR: no picture for ' + ', '.join(missing) + ' (run fetch_cityhall_art.py)')
    prepped = {}
    for cid, spec in have.items():
        prepped[cid] = prep(cid, spec)
        print('prepped', cid, flush=True)
    ids = sorted(have)
    # the largest common pixels a metre that packs
    area = sum(have[i][1][0] * have[i][1][1] * have[i][6] ** 2 for i in ids)
    ppm = (AW * AH * FILL / area) ** 0.5
    while True:
        sizes = [(int(round(have[i][1][0] * ppm * have[i][6])), int(round(have[i][1][1] * ppm * have[i][6]))) for i in ids]
        pos = pack(sizes, AW, AH, PAD)
        if pos:
            break
        ppm *= 0.99
    atlas = np.zeros((AH, AW, 3), np.float32)
    mask = np.zeros((AH, AW, 3), np.uint8)
    man = {'v': 1, 'size': [AW, AH], 'ppm': round(ppm, 3), 'cells': {}, 'm': {}, 'mean': {}, 'meta': {}}
    for i, cid in enumerate(ids):
        src, (wm, hm), crop, rows, kind, wrap, dens = have[cid]
        col, msk, meta = prepped[cid]
        w, h = sizes[i]
        x, y = pos[i]
        cppm = h / hm
        ci = remap_rows(Image.fromarray(col.astype(np.uint8)), rows, hm, cppm, w, Image.LANCZOS)
        mi = remap_rows(Image.fromarray(msk), rows, hm, cppm, w, Image.NEAREST)
        c = np.asarray(ci).astype(np.float32)[:h, :w]
        if c.shape[0] < h:
            c = np.concatenate([c, np.repeat(c[-1:], h - c.shape[0], 0)], 0)
        if wrap:
            c = blend_wrap(c)
        if wrap == 'xy':
            c = blend_wrap(c, axis=0)
        m = np.asarray(mi)[:h, :w]
        atlas[y:y + h, x:x + w] = c
        mask[y:y + h, x:x + w] = m
        gutter(atlas, x, y, w, h, PAD, wrap)
        gutter(mask, x, y, w, h, PAD, wrap)
        # texture uv with v up (the page's flipped image): [u0, v0, u1, v1]
        man['cells'][cid] = [round(x / AW, 6), round(1 - (y + h) / AH, 6), round((x + w) / AW, 6), round(1 - y / AH, 6)]
        man['m'][cid] = [wm, hm]
        stone = c[m[..., 0] == 0]
        man['mean'][cid] = [round(float(v) / 255, 4) for v in stone.mean(0)]
        if 'arch' in meta:
            u0, u1, ycrown, yspring, yfoot = meta['arch']
            meta['arch'] = [round(u0 * wm, 3), round(u1 * wm, 3), round(row_to_m(rows, yspring), 3), round(row_to_m(rows, ycrown), 3)]
        if 'dial' in meta:
            cu, cv, ru, rv = meta['dial']
            Hs = rows[-1][0]
            cy_m = row_to_m(rows, (1 - cv) * Hs)
            meta['dial'] = [round(cu * wm, 3), round(cy_m, 3), round(ru * wm, 3), round(rv * hm, 3)]
        if cid in COLS:   # [across, capital's top, shaft's top, shaft's foot, radius] in metres
            Ws = (crop[2] - crop[0]) if crop else Image.open(os.path.join(RAW, src + '.png')).width
            meta['cols'] = [[round(x / Ws * wm, 3), round(row_to_m(rows, ct), 3), round(row_to_m(rows, st), 3), round(row_to_m(rows, sf), 3), round(dd / 2 / Ws * wm, 3)]
                            for (x, ct, st, sf, dd) in COLS[cid]]
        if meta:
            man['meta'][cid] = meta
    img = Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8))
    mimg = Image.fromarray(mask)
    half = img.resize((AW // 2, AH // 2), Image.LANCZOS)
    mhalf = mimg.resize((AW // MASK_DIV, AH // MASK_DIV), Image.NEAREST)
    mquart = mimg.resize((AW // (2 * MASK_DIV), AH // (2 * MASK_DIV)), Image.NEAREST)
    man['img'] = art_files.write(img, 'cityhall', 'cityhall', 'WEBP', quality=88, method=6)
    man['imgHalf'] = art_files.write(half, 'cityhall', 'cityhall-half', 'WEBP', quality=85, method=6)
    man['mask'] = art_files.write(mhalf, 'cityhall', 'cityhall-mask', 'PNG', optimize=True)
    man['maskHalf'] = art_files.write(mquart, 'cityhall', 'cityhall-mask-half', 'PNG', optimize=True)
    man['maskDiv'] = MASK_DIV
    with open(OUT, 'w') as f:
        json.dump(man, f, separators=(',', ':'))
    gone = art_files.prune('cityhall')
    sz = sum(art_files.size(man[k]) for k in ('img', 'imgHalf', 'mask', 'maskHalf'))
    print('%d cells at %.1f px/m, %s: %d bytes; art/cityhall: %d bytes (%d pruned)' % (len(ids), ppm, OUT, os.path.getsize(OUT), sz, gone))
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        img.save(os.path.join(a.preview, 'atlas.jpg'), quality=90)
        Image.fromarray(mask).save(os.path.join(a.preview, 'mask.png'))


if __name__ == '__main__':
    main()
