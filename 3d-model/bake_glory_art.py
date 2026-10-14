#!/usr/bin/env python3
"""Bake Glory Beer Bar & Kitchen's art (Round 191) into glory_art.json, which build.py inlines as GLORY_ART, and the images
themselves into art/glory/ (art_files.py: files the page loads on demand, a phone's half copies beside them).

fetch_glory_art.py makes the two elevations of 126 Chestnut Street with every pane a flat chroma-key green (frames/), the
upper one again with real glass painted into the key (glass/upper.png), and the two rooms behind the bar's glass, empty
(rooms/) and with people (crowd/). This bake:
  --masks   writes the edits' masks beside their sources (an API input that never ships): the upper frame's, transparent
            over its key; each chosen room's, transparent over its floor zone below 2.1 m in the room's own one-point
            projection (BACK below), less the ceiling and the bar's shelving on the right wall;
  (default) finds the key (hue 100 to 140 degrees, saturation over 0.55, value over 0.5, closed by a pixel), measures the
            openings the model must cut from it (the four doors, the four arches and their columns, the twelve windows,
            in metres on the wall; a measure that fails falls back to the research's nominal numbers WITH A WARNING, and
            arches rising more than ARCH_RISE_MAX are refused), fills the lower key and its rim from the dark frames round
            it and the upper's with the frames' own colour pushed in from round it (so no green and no pale rim reaches a
            mip), tints the granite toward the street's warm buff (STONE_TINT), pastes the
            glass edit back inside the upper key only, and lays the facade atlas (the lower elevation left, the upper
            right, both at the same pixels a metre, and a row of tileable swatches under them: granite (jointless patches
            of the piers' faces, granite_swatch), brick, concrete, iron, the old sign box's pale enamel chipped to rust
            (peel_swatch), the lanterns' glow, the roof and the rust of the box's cap (rust_swatch); every plain one
            periodic, noise_swatch), its mask at half size (an opaque RGB PNG, never RGBA: bake_fronts.py; the lower
            elevation's lites regular rectangles of whole texels with straight bars, regular_lites, the same bars
            painted into the atlas, paint_bars; the upper's muntins held at 0 two texels wide, pane_bars and bar_texels),
            the door leaves for the open door (door_leaves), the interior atlas (the open rooms at 1024 wide, the closed
            at 512) and its mask, and every half copy.
The mask: r the glass; g a number per pane (lower) or per window (upper: both sashes); b the upper windows' height inside
the window, 0 at the sill to 64 at the head (the house fronts' convention, so roomLight reads it as theirs), 200 the bar's
glass on the ground floor, 216 the second storey's, 240 the glow swatch. The interior mask: r the bulbs, the string lights,
the pendants and the sconces (bright small blobs), g the back bar's glow.

Usage: python3 bake_glory_art.py [--masks] [--preview DIR]"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageFilter
import art_files
from bake_fronts import blobs, dilate, erode, lum
import fetch_glory_art as F

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = F.RAW
OUT = os.path.join(HERE, 'glory_art.json')
W_M, H_M = 8.6, 9.3          # each elevation's wall, metres
AW, AH = 2048, 1280          # the facade atlas
PAD = 8
EW, EH = 1008, 1090          # an elevation in the atlas (117 px a metre), in a PAD gutter
SW = 152                     # a swatch, in its own PAD gutter
SW_Y = EH + 2 * PAD + PAD    # the swatch row's top
MASK_DIV = 2
IW = 1024                    # the interior atlas's width
ROOM = {'ground': (0.30, 8.30, 0.50, 4.60), 'upperroom': (0.30, 8.30, 5.30, 8.50)}   # the shader's room boxes [x0, x1, y0, y1], metres
DEPTH = 22.0                 # both rooms run 22 m back
# the back wall's rectangle on each chosen room plate [x0, y0, x1, y1] as fractions of the image from its bottom-left,
# measured once by hand on the image (the plate is refused without one). ground-empty-b: the brick back wall and the pale
# passage beside it, 703 to 815 px across and 362 to 442 px down of 1536 by 784 (taller for its width than the front:
# the shader takes each axis's own scale); upper-empty-a: the back bar between the cream panels either side of it, 680 to
# 853 px across and 243 to 332 px down of 1536 by 608
BACK = {'ground-empty-b': [0.4577, 0.4362, 0.5306, 0.5383], 'upper-empty-a': [0.4427, 0.4539, 0.5553, 0.6003]}
# the research's nominal numbers (metres from the west party wall and the sidewalk), the fallback for a failed measure
NOMINAL = {
    'bays': [[0.45, 2.0], [2.5, 4.05], [4.55, 6.1], [6.6, 8.15]], 'doorTop': 4.0, 'doorFoot': 0.45,
    'arcade': [[0.5, 1.95], [2.6, 3.95], [4.65, 6.0], [6.7, 8.1]], 'spring': 7.6, 'crown': 8.25, 'sill2': 5.25,
    'cols': [2.08, 2.42, 4.13, 4.47, 6.18, 6.52], 'colR': 0.15, 'cornice': [8.6, 9.3], 'capital': {'y': [3.9, 4.1], 'ends': [0.0, 0.0], 'out': 0.05},
    'win': [[u0, u0 + 1.0, y0, y0 + 1.75] for y0 in (0.65, 3.45, 6.25) for u0 in (0.75, 2.8, 4.8, 6.85)],
}
SWATCHES = ['granite', 'brick', 'concrete', 'iron', 'rustblue', 'glow', 'roof', 'rust']
SW_M = {'granite': 1.2, 'brick': 1.0, 'concrete': 1.5, 'iron': 1.0, 'rustblue': 0.8, 'glow': 1.0, 'roof': 3.0, 'rust': 0.5}   # metres a tile


def load(p):
    return np.asarray(Image.open(p).convert('RGB'), np.float32) / 255.0


def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def key_of(a):
    """The chroma-key glass: hue 100 to 140 degrees, saturation over 0.55, value over 0.5, closed by a pixel."""
    mx, mn = a.max(-1), a.min(-1)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    hue = np.where(mx == g, 60 * (b - r) / d + 120, 0)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    k = (hue > 100) & (hue < 140) & (sat > 0.55) & (mx > 0.5)
    return erode(dilate(k, 1), 1)


def chosen(stage, kind):
    return os.path.join(RAW, stage, F.CHOSEN[kind] + '.png')


def write_masks():
    up = chosen('frames', 'upper')
    if os.path.exists(up):
        a = load(up)
        k = dilate(key_of(a), 3)
        rgba = np.zeros(a.shape[:2] + (4,), np.uint8)
        rgba[..., 3] = np.where(k, 0, 255)
        Image.fromarray(rgba).save(up[:-4] + '-mask.png')
        print('upper glass mask: key %.3f' % key_of(a).mean())
    for kind in ('ground', 'upperroom'):
        p = chosen('rooms', kind)
        if not os.path.exists(p) or F.CHOSEN[kind] not in BACK:
            print(kind, 'no plate or no back wall rectangle yet')
            continue
        im = Image.open(p)
        W, H = im.size
        z = crowd_zone(kind, W, H)
        rgba = np.zeros((H, W, 4), np.uint8)
        rgba[..., 3] = np.where(z, 0, 255)
        Image.fromarray(rgba).save(p[:-4] + '-crowdmask.png')
        print(kind, 'crowd mask %.3f' % z.mean())


def crowd_zone(kind, W, H):
    """Where the edit may paint people: under 2.1 m over the room's floor in its own one-point projection (the side walls'
    and the back wall's lines at that height, rays from the vanishing point), the right wall above 1.2 m left alone (the
    bar's shelving, and the mantelpiece upstairs)."""
    x0, y0, x1, y1 = BACK[F.CHOSEN[kind]]
    rx0, rx1, ry0, ry1 = ROOM[kind]
    hf = 2.1 / (ry1 - ry0)
    s = (np.arange(W) + 0.5) / W
    r = 1 - (np.arange(H) + 0.5) / H
    S, R = np.meshgrid(s, r)
    back_h = y0 + hf * (y1 - y0)
    lim = np.where(S < x0, hf + (back_h - hf) * S / max(x0, 1e-3),
                   np.where(S > x1, hf + (back_h - hf) * (1 - S) / max(1 - x1, 1e-3), back_h))
    z = R < lim
    hr = 1.2 / (ry1 - ry0)
    lim_r = hr + (y0 + hr * (y1 - y0) - hr) * (1 - S) / max(1 - x1, 1e-3)
    z &= ~((S > x1) & (R > lim_r))
    return z


# Round 191's review: lower-b's second storey was four steep pointed lancets (a church front from across the street). The
# real storey's soffit dips between the capitals in a low arch of about 0.3 to 0.5 m: a frame whose key-measured rise is
# over ARCH_RISE_MAX is refused
ARCH_RISE_MAX = 0.5
# the granite as the street sees it (refs, gloryphilly IMG6: a warm buff, about (206, 193, 181), hue 30, HSV saturation
# 0.12): the chosen frame's piers came out at (220, 200, 175), hue 33, and the render's warm sun, its sky fill and the filmic
# grade carry a stone toward yellow and take half its saturation (rendered with the frame as it came, 0.07 at hue 40 to 46;
# the first build's 0.04 read as marble), so the stone is tinted a little toward red by STONE_TINT (the frames, the doors
# and the key are near black or keyed and barely move)
STONE_TINT = (1.0, 0.965, 0.985)


def toward_stone(a, k):
    return np.where(k[..., None], a, np.clip(a * np.array(STONE_TINT, np.float32), 0, 1))


def fill_dark(a, k):
    """The keyed panes and their anti-aliased rim filled from the dark frame round them only (Round 191's review: filled
    from every pixel round it, the rim came out a light lavender that traced every pane of the doors and transoms in
    dashes within about 6 m): the push-pull fill takes only frame pixels (luminance under 0.35) as known, and whatever no
    frame pixel reaches falls back to fill_key."""
    dark = (~k) & (lum(a) < 0.35)
    out = a.copy()
    known = dark.astype(np.float32)
    todo = k.copy()
    for rad in (2, 6, 18):
        if not todo.any():
            break
        w = to_img(np.repeat(known[..., None], 3, -1)).filter(ImageFilter.GaussianBlur(rad))
        c = to_img(out * known[..., None]).filter(ImageFilter.GaussianBlur(rad))
        wv = np.asarray(w, np.float32)[..., :1] / 255.0
        cv = np.asarray(c, np.float32) / 255.0
        ok = (wv[..., 0] > 0.02) & todo
        out[ok] = np.clip(cv / np.maximum(wv, 1e-3), 0, 1)[ok]
        known = np.where(ok, 1.0, known); todo &= ~ok
    return fill_key(out, todo) if todo.any() else out


def granite_swatch(lo, k, meas):
    """The granite every side, jamb, reveal and soffit wears: four jointless patches of the piers' faces in a 2 by 2 quilt,
    each with its low frequencies flattened to the stone's mean (no baked shading), so a face tiled with it carries the
    piers' grain and nothing else. Round 191's review: cut from the band over the doors, the old swatch held a stone joint
    and its shadow, and tiled at 0.45 m it drew a ladder up every pier side and jamb. A window is jointless when no row's
    and no column's mean departs from the window's own by a joint's contrast. Returns (image, metres a tile)."""
    H, W = k.shape
    pxm = H / H_M
    side = 0.34
    n = int(side * pxm)
    edges = [[0.0, meas['bays'][0][0]]] + [[meas['bays'][i][1], meas['bays'][i + 1][0]] for i in range(3)] + [[meas['bays'][3][1], W_M]]
    L = lum(lo)
    cands = []
    for pi, (e0, e1) in enumerate(edges):
        if e1 - e0 < side + 0.12:
            continue
        cxp = int((e0 + e1) / 2 / W_M * W)
        for y in np.arange(1.0, meas['doorTop'] - 0.6, 0.08):
            yy = int(H - (y + side) * pxm)
            win = L[yy:yy + n, cxp - n // 2:cxp - n // 2 + n]
            if win.shape != (n, n) or k[yy:yy + n, cxp - n // 2:cxp - n // 2 + n].any():
                continue
            hp = win - np.asarray(Image.fromarray((win * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(n / 3)), np.float32) / 255
            score = max(np.abs(hp.mean(1)).max(), np.abs(hp.mean(0)).max())
            cands.append((score, pi, y, yy, cxp))
    cands.sort()
    pick, used = [], set()
    for c in cands:
        if c[1] in used:
            continue
        pick.append(c); used.add(c[1])
        if len(pick) == 4:
            break
    while len(pick) < 4:
        pick.append(cands[len(pick)])
    mean = np.mean([lo[yy:yy + n, cx - n // 2:cx - n // 2 + n].reshape(-1, 3).mean(0) for _, _, _, yy, cx in pick], 0)
    q = SW // 2
    out = np.zeros((SW, SW, 3), np.float32)
    for i, (_, _, _, yy, cx) in enumerate(pick):
        p = lo[yy:yy + n, cx - n // 2:cx - n // 2 + n]
        lowf = np.asarray(to_img(p).filter(ImageFilter.GaussianBlur(n / 4)), np.float32) / 255
        flat = np.clip(p - lowf + mean, 0, 1)
        t = np.asarray(tileable(to_img(flat).resize((q, q), Image.LANCZOS)), np.float32) / 255
        out[(i // 2) * q:(i // 2) * q + q, (i % 2) * q:(i % 2) * q + q] = t
    print('granite swatch: patches at', [(int(c[1]), round(float(c[2]), 2), round(float(c[0]), 4)) for c in pick])
    return to_img(out), round(2 * side, 3)


def peel_swatch(seed):
    """The old projecting sign box's face (refs, the Bright MLS street view: a weathered pale white-grey enamelled sheet-metal
    box, its enamel chipped to rust in small ragged flakes, brown rust run down its face): the enamel, the chips, a mottle
    of grime, and thin rust runs. Every field is periodic, so the swatch tiles without a cross-fade cutting the
    flakes. Round 191's second review: the first swatch's pale sky blue and its big cloud-shaped peels read as a glossy
    glass slab; the grime at its edges and the rust from its top are the shader's, by the box's own frame (uGlBox)."""
    rs = np.random.RandomState(seed)
    n = SW
    def smooth(cells, blur, shape=None):   # periodic value noise: the cells tiled three by three, upsampled, the middle kept
        z = rs.rand(*(shape or (cells, cells)))
        big = np.tile(z, (3, 3))
        im = Image.fromarray((big * 255).astype(np.uint8)).resize((3 * n, 3 * n), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
        z = np.asarray(im, np.float32)[n:2 * n, n:2 * n] / 255
        return (z - z.min()) / max(z.max() - z.min(), 1e-3)
    # Round 191's third review: the grey-sage (164, 168, 153) rendered a mid grey-sage, darker and greener than the Bright
    # MLS view's pale, worn white-grey enamel; the enamel is now (190, 192, 186) and what shows through a chip is rust
    base = np.array([190, 192, 186], np.float32) / 255
    lo_n, mid, fine = smooth(5, 5), smooth(14, 2), smooth(38, 0.6)
    out = base[None, None, :] * (0.88 + 0.16 * lo_n[..., None]) * (0.96 + 0.08 * mid[..., None])
    # the chips: small and ragged (a mid field cut by a fine one), rusted steel in them
    flake = (mid * 0.55 + fine * 0.45 + lo_n * 0.2) > 0.8
    out = np.where(flake[..., None], np.array([118, 82, 58], np.float32) / 255 * (0.85 + 0.25 * fine[..., None]), out)
    lip = (np.roll(flake, 1, 0) | np.roll(flake, 1, 1)) & ~flake   # the paint's broken edge, shaded under and beside a flake
    out = np.where(lip[..., None], out * 0.84, out)
    # grime: a darker mottle settled in the low field
    out = out * (1 - 0.18 * np.clip(0.6 - lo_n, 0, 1)[..., None])
    cols = np.clip((smooth(0, 0.6, (1, 29)) - 0.78) / 0.22, 0, 1)   # a few thin runs
    runs = cols * (0.25 + 0.75 * smooth(0, 4, (3, 1)))
    out = out * (1 - runs[..., None] * 0.55) + np.array([104, 66, 42], np.float32) / 255 * runs[..., None] * 0.55
    return to_img(out)


def rust_swatch(seed):
    """The old sign box's bottom cap (refs, the Bright MLS view: a dark rusty curved sheet): dark rusted steel, a mottle of
    brown and a few orange flecks, periodic."""
    rs = np.random.RandomState(seed)
    n = SW
    def smooth(cells, blur):
        big = np.tile(rs.rand(cells, cells), (3, 3))
        im = Image.fromarray((big * 255).astype(np.uint8)).resize((3 * n, 3 * n), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
        z = np.asarray(im, np.float32)[n:2 * n, n:2 * n] / 255
        return (z - z.min()) / max(z.max() - z.min(), 1e-3)
    a, b = smooth(6, 4), smooth(24, 1)
    dark, brown, orange = (np.array(c, np.float32) / 255 for c in ((40, 29, 24), (84, 52, 34), (124, 70, 38)))
    out = dark + (brown - dark) * (a * 0.8 + b * 0.2)[..., None]
    out = np.where(((a * 0.5 + b * 0.5) > 0.84)[..., None], orange * (0.8 + 0.2 * b[..., None]), out)
    return to_img(out)


# the brick's colour on the street (the research: an orange red, #bf856c in an overcast photo): the generated brick came out
# more saturated (#a86444), and beside the procedural walls of the block it read as painted orange. Its saturation is taken
# down by BRICK_DESAT about its own luminance (the glass edit gets the same, pasted inside the key afterwards)
BRICK_DESAT = 0.22


def toward_brick(a, k):
    L = lum(a)[..., None]
    out = L + (a - L) * (1 - BRICK_DESAT)
    return np.where(k[..., None], a, np.clip(out, 0, 1))


def fill_key(a, k):
    """The keyed pixels filled with the frame's own colour pushed in from round them (a push-pull fill), so no green
    reaches a mip."""
    out = a.copy()
    known = (~k).astype(np.float32)
    for rad in (3, 10, 30, 90):
        if not (known < 0.5).any():
            break
        w = to_img(np.repeat(known[..., None], 3, -1)).filter(ImageFilter.GaussianBlur(rad))
        c = to_img(out * known[..., None]).filter(ImageFilter.GaussianBlur(rad))
        wv = np.asarray(w, np.float32)[..., :1] / 255.0
        cv = np.asarray(c, np.float32) / 255.0
        fill = cv / np.maximum(wv, 1e-3)
        ok = (wv[..., 0] > 0.02) & (known < 0.5)
        out[ok] = np.clip(fill[ok], 0, 1)
        known = np.where(ok, 1.0, known)
    return out


def groups(bl, n, axis):
    """n clusters of blobs (y0, x0, y1, x1, cnt) along axis (1 = x, 0 = y), split at the n - 1 widest gaps between their
    centres."""
    if len(bl) < n:
        return None
    c = sorted(bl, key=lambda b: (b[axis] + b[axis + 2]) / 2)
    cs = [(b[axis] + b[axis + 2]) / 2 for b in c]
    gaps = sorted(range(len(cs) - 1), key=lambda i: cs[i + 1] - cs[i], reverse=True)[:n - 1]
    cut = sorted(gaps)
    out, s = [], 0
    for g in cut:
        out.append(c[s:g + 1]); s = g + 1
    out.append(c[s:])
    return out


def union(g):
    return (min(b[0] for b in g), min(b[1] for b in g), max(b[2] for b in g), max(b[3] for b in g))


def grow(L, box, dark, lim=0.32, tol=4):
    """A pane group's box grown out to the frame round it: while the column (or row) through the box's middle half is dark
    (dark True) or bright and pale (dark False: a white sash frame on brick), at most a tenth of the image; a line of
    lighter paint across a door (a panel's moulding) does not stop it, only four lines in a row past the limit do."""
    y0, x0, y1, x1 = box
    H, W = L.shape
    test = (lambda v: v < lim) if dark else (lambda v: v > lim)
    ym0, ym1 = y0 + (y1 - y0) // 4, y1 - (y1 - y0) // 4
    xm0, xm1 = x0 + (x1 - x0) // 4, x1 - (x1 - x0) // 4
    col = lambda x: test(np.median(L[ym0:ym1, x])) if 0 <= x < W else False
    row = lambda y: test(np.median(L[y, xm0:xm1])) if 0 <= y < H else False
    def run(p, step, ok, cap):
        n = 0
        while n < cap and any(ok(p + step * (j + 1)) for j in range(tol)):
            p += step; n += 1
        while not ok(p) and n > 0:   # back off the light lines it ran over at its end
            p -= step; n -= 1
        return p
    x0 = run(x0, -1, col, W // 10)
    x1 = run(x1, 1, col, W // 10)
    y0 = run(y0, -1, row, H // 10)
    y1 = run(y1, 1, row, H // 10)
    return y0, x0, y1, x1


def measure_lower(a, k):
    """The ground floor's four doors, the second storey's four arches and its columns, in metres. Returns (measures,
    warnings, blobs by kind)."""
    H, W = k.shape
    pxm, L = H / H_M, np.where(k, 0.0, lum(a))   # the key's green is the opening, not a bright wall
    bl = [b for b in blobs(k) if b[4] > 150]
    lo = [b for b in bl if (b[0] + b[2]) / 2 > 0.5 * H]
    hi = [b for b in bl if (b[0] + b[2]) / 2 <= 0.5 * H]
    M, warn = {}, []
    U = lambda x: round(x / W * W_M, 3)
    Y = lambda y: round((H - y) / pxm, 3)
    gl = groups(lo, 4, 1)
    if gl:
        bays, tops, feet = [], [], []
        for g in gl:
            y0, x0, y1, x1 = grow(L, union(g), True)
            bays.append([U(x0), U(x1 + 1)]); tops.append(Y(y0)); feet.append(Y(y1 + 1))
        M['bays'], M['doorTop'], M['doorFoot'] = bays, round(float(np.median(tops)), 3), round(float(np.median(feet)), 3)
    else:
        warn.append('ground bays not found')
    gh = groups(hi, 4, 1)
    if gh:
        arc, springs, crowns, sills = [], [], [], []
        for g in gh:
            y0, x0, y1, x1 = grow(L, union(g), True)
            arc.append([U(x0), U(x1 + 1)]); sills.append(Y(y1 + 1))
            # the arch: the topmost dark row at the bay's middle is the crown, and the spring the top of the frame's own stile
            # 4% of the opening in from either side (Round 191: the old spring, the highest row dark across nine tenths of the
            # opening, fell 0.6 m down a low arch whose grown box took in a sliver of stone at each side)
            cx, wide = (x0 + x1) // 2, x1 - x0
            yc = y0
            while yc > 0 and L[yc - 1, cx - 2:cx + 3].mean() < 0.32:
                yc -= 1
            sides = []
            for xs in (x0 + max(2, int(0.04 * wide)), x1 - max(2, int(0.04 * wide))):
                y, light = (y0 + y1) // 2, 0
                while y > 0 and light < 3:   # up the stile, over a light line or two (a fillet, a highlight)
                    y -= 1
                    light = light + 1 if L[y, xs - 1:xs + 2].mean() >= 0.32 else 0
                sides.append(y + 3)
            ys = int(np.median(sides))
            springs.append(Y(ys)); crowns.append(Y(yc))
        M['arcade'], M['spring'], M['crown'], M['sill2'] = arc, round(float(np.median(springs)), 3), round(float(np.median(crowns)), 3), round(float(np.median(sills)), 3)
        # the columns: a pair in every gap between two arches, a quarter of the gap either side of its middle
        cols = []
        for i in range(3):
            g0, g1 = arc[i][1], arc[i + 1][0]
            c, q = (g0 + g1) / 2, (g1 - g0) / 4
            cols += [round(c - q, 3), round(c + q, 3)]
        M['cols'], M['colR'] = cols, round(min(0.16, max(0.08, (arc[1][0] - arc[0][1]) / 4 * 0.92)), 3)
    else:
        warn.append('second-storey arches not found')
    return M, warn, (lo, hi)


def measure_upper(a, k):
    """The twelve windows of floors 3 to 5 [u0, u1, y0, y1] in metres over the upper elevation's foot, each grown out to its
    white frame; and each pane's window number."""
    H, W = k.shape
    pxm, L = H / H_M, np.where(k, 1.0, lum(a))   # the key's green is the window, not brick
    Sat = np.where(k, 0.0, (a.max(-1) - a.min(-1)) / np.maximum(a.max(-1), 1e-6))
    bl = [b for b in blobs(k) if b[4] > 400]
    rows = groups(bl, 3, 0)
    win, warn, number = [], [], {}
    if not rows:
        return {}, ['upper windows not found'], number
    n = 0
    for row in sorted(rows, key=lambda r: -union(r)[2]):   # bottom storey first
        cols = groups(row, 4, 1)
        if not cols:
            warn.append('a storey without four windows')
            continue
        for c in cols:
            # across, out to the brick (the white frame and its shade are unsaturated, the brick orange); up and down, over
            # the white frame only (the stone sill and lintel are pale too)
            _, x0, _, x1 = grow(1.0 - Sat, union(c), False, 0.72, 1)
            y0, _, y1, _ = grow(L, union(c), False, 0.72, 1)
            win.append([round(x0 / W * W_M, 3), round((x1 + 1) / W * W_M, 3), round((H - y1 - 1) / pxm, 3), round((H - y0) / pxm, 3)])
            for b in c:
                number[b[:4]] = n
            n += 1
    if len(win) != 12:
        warn.append('%d upper windows, not 12' % len(win))
        return {}, warn, number
    # the windows stand in four stacks and three storeys: each stack takes its windows' median sides and each storey their
    # median sill and head (a curtain drawn across a frame, or a sash's shade, moves one window's edge, not the wall's)
    med = lambda v: round(float(np.median(v)), 3)
    for c in range(4):
        u0, u1 = med([win[r * 4 + c][0] for r in range(3)]), med([win[r * 4 + c][1] for r in range(3)])
        for r in range(3):
            win[r * 4 + c][0], win[r * 4 + c][1] = u0, u1
    for r in range(3):
        y0, y1 = med([win[r * 4 + c][2] for c in range(4)]), med([win[r * 4 + c][3] for c in range(4)])
        for c in range(4):
            win[r * 4 + c][2], win[r * 4 + c][3] = y0, y1
    return {'win': win}, warn, number


def tileable(im):
    """A square crop made to tile: blended with itself shifted by half a tile, the seams' cross-fade weighted to the
    middle (a swatch is read only where no elevation is: the sides, the reveals, the stoop)."""
    a = np.asarray(im, np.float32)
    n = a.shape[0]
    s = np.roll(np.roll(a, n // 2, 0), n // 2, 1)
    t = np.abs(np.linspace(-1, 1, n))
    w = np.minimum(1, np.maximum(t[:, None], t[None, :]) * 1.6 - 0.3).clip(0, 1)[..., None]
    return Image.fromarray(np.clip(a * (1 - w) + s * w, 0, 255).astype(np.uint8))


def periodic(z, n, blur=0.0):
    """A field of random cells made into an n by n tile that wraps: the cells tiled three by three, resized and blurred as
    one, the middle kept (the resize and the blur see the neighbouring tiles, so the tile's edges meet themselves)."""
    big = np.tile(z, (3, 3))
    im = Image.fromarray((np.clip(big, 0, 1) * 255).astype(np.uint8)).resize((3 * n, 3 * n), Image.BICUBIC)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, np.float32)[n:2 * n, n:2 * n] / 255


def noise_swatch(rgb, amp, seed, streak=None, scales=((8, 0.5), (24, 0.7)), fine=0.45):
    """A plain material's tile: its colour with value noise at each (cells a tile, share) of scales and a per-texel grain,
    every field periodic (Round 191's third review: the coarse field was resized without wrapping and never made to tile,
    so every concrete tile ended at a hard edge, a seam down the stoop's deck and through every tread and riser, and
    another every 1.5 m along its fascia)."""
    rs = np.random.RandomState(seed)
    n = SW
    base = np.ones((n, n, 3), np.float32) * np.array(rgb, np.float32) / 255
    nz = sum(w * (periodic(rs.rand(c, c), n) - 0.5) for c, w in scales)
    gr = rs.rand(n, n) - 0.5   # a texel's own grain: no structure to cross the edge
    out = base * (1 + amp * (nz[..., None] * 1.2 + gr[..., None] * fine))
    if streak is not None:
        cols = rs.rand(1, n) ** 6
        st = periodic(np.repeat(cols, 4, 0), n, 1.5)[..., None]
        out = out * (1 - st) + np.array(streak, np.float32) / 255 * st
    return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8))


def gutter(canvas, im, x, y):
    """Paste im at (x, y) with its edge pixels run out PAD pixels all round."""
    w, h = im.size
    canvas.paste(im, (x, y))
    a = np.asarray(canvas).copy()
    a[y - PAD:y, x:x + w] = a[y:y + 1, x:x + w]
    a[y + h:y + h + PAD, x:x + w] = a[y + h - 1:y + h, x:x + w]
    a[y - PAD:y + h + PAD, x - PAD:x] = a[y - PAD:y + h + PAD, x:x + 1]
    a[y - PAD:y + h + PAD, x + w:x + w + PAD] = a[y - PAD:y + h + PAD, x + w - 1:x + w]
    return Image.fromarray(a)


def uv_rect(x, y, w, h, aw, ah):
    """A pixel rectangle as texture uv [u0, v0, du, dv] (v up from the image's foot, as three samples a flipped image)."""
    return [round(x / aw, 6), round(1 - (y + h) / ah, 6), round(w / aw, 6), round(h / ah, 6)]


def blob_px(a):
    """The interior mask's bulbs: bright small blobs (a lamp, a bulb on a string, a globe), by threshold."""
    L = lum(a)
    hot = L > max(0.82, float(np.percentile(L, 99.3)))
    out = np.zeros_like(hot)
    for y0, x0, y1, x1, c in blobs(hot):
        if c < 900 and (y1 - y0) < 60 and (x1 - x0) < 60:
            out[y0:y1 + 1, x0:x1 + 1] |= hot[y0:y1 + 1, x0:x1 + 1]
    return out


def pane_bars(k, r=4):
    """The bars between the panes of one opening (the doors' and the casements' muntins, 5 to 6 pixels of the 179 a metre):
    what closing the key by r pixels fills that is not key. A gap wider than 2r (a mullion between two casements, a door's
    meeting stiles, the transom bar) stays frame."""
    return erode(dilate(k, r), r) & ~k


def bar_texels(bars, shape):
    """The mask texels a bar holds at 0: each texel the bar covers more than half of, and where that leaves a bar one texel
    wide across it, the neighbour it covers more of, so every bar is two texels (3.4 cm at the mask's 1.7) whatever its
    phase on the grid."""
    cov = np.asarray(Image.fromarray((bars * 255).astype(np.uint8)).resize((shape[1], shape[0]), Image.BOX), np.float32) / 255
    core = cov > 0.5
    out = core.copy()
    for ax in (0, 1):
        lo_, hi_ = np.roll(cov, 1, ax), np.roll(cov, -1, ax)        # the neighbour before and after along ax
        one = core & ~np.roll(core, 1, ax) & ~np.roll(core, -1, ax)
        out |= np.roll(one & (lo_ >= hi_) & (lo_ > 0.05), -1, ax)   # the one before
        out |= np.roll(one & (hi_ > lo_) & (hi_ > 0.05), 1, ax)     # the one after
    return out


def clusters(bl, axis, gap=12):
    """Blobs (y0, x0, y1, x1, cnt) grouped by their centres along axis (1 = x, 0 = y): a new group where two centres in
    order lie more than gap pixels apart."""
    c = sorted(bl, key=lambda b: (b[axis] + b[axis + 2]) / 2)
    out = [[c[0]]]
    for a, b in zip(c, c[1:]):
        if (b[axis] + b[axis + 2]) / 2 - (a[axis] + a[axis + 2]) / 2 > gap:
            out.append([])
        out[-1].append(b)
    return out


def regular_lites(k, shape):
    """The lower elevation's glass at the mask's size, every lite a rectangle of whole texels, and its muntins straight
    (Round 191's third review: the bars followed the generated image's hand-drawn ones, a door leaf's vertical bar jogging a
    texel between lites and bulging at every crossing, and every lite a rounded rectangle). Each sash (the key closed over
    its muntins) has its lites in columns and rows: a column's sides and a row's head and foot are their lites' medians, the
    sash grows two source pixels toward its outer frame (the pane's rim, as before), and every muntin is a bar two texels
    wide on the texel boundary nearest its middle. Returns (glass, bars, sashes): the glass texels, the bars as source pixel
    rectangles (x0, y0, x1, y1) for the atlas, and each sash's box and its lites' columns and rows."""
    H, W = k.shape
    h, w = shape
    sx, sy = w / W, h / H
    glass = np.zeros(shape, bool)
    bars, sashes = [], []
    lites = [b for b in blobs(k) if b[4] > 30]
    med = lambda v: float(np.median(v))
    for s in blobs(erode(dilate(k, 4), 4)):
        if s[4] < 400:
            continue
        y0, x0, y1, x1 = s[:4]
        inn = [l for l in lites if l[0] >= y0 - 1 and l[2] <= y1 + 1 and l[1] >= x0 - 1 and l[3] <= x1 + 1]
        if not inn:
            continue
        cols, rows = clusters(inn, 1), clusters(inn, 0)
        L, R = [med([l[1] for l in c]) for c in cols], [med([l[3] + 1 for l in c]) for c in cols]
        T, B = [med([l[0] for l in r]) for r in rows], [med([l[2] + 1 for l in r]) for r in rows]
        gx0, gx1 = int(round((L[0] - 2) * sx)), int(round((R[-1] + 2) * sx))
        gy0, gy1 = int(round((T[0] - 2) * sy)), int(round((B[-1] + 2) * sy))
        glass[gy0:gy1, gx0:gx1] = True
        for j in range(len(cols) - 1):
            c = int(round((R[j] + L[j + 1]) / 2 * sx))
            glass[gy0:gy1, c - 1:c + 1] = False
            bars.append(((c - 1) / sx, gy0 / sy, (c + 1) / sx, gy1 / sy))
        for i in range(len(rows) - 1):
            c = int(round((B[i] + T[i + 1]) / 2 * sy))
            glass[c - 1:c + 1, gx0:gx1] = False
            bars.append((gx0 / sx, (c - 1) / sy, gx1 / sx, (c + 1) / sy))
        sashes.append({'box': (L[0], T[0], R[-1], B[-1]), 'cols': len(cols), 'rows': len(rows)})
    return glass, bars, sashes


def paint_bars(a, bars, col):
    """The regular bars painted into the elevation in the frame's colour, each pixel by the share of it a bar covers."""
    out = a.copy()
    H, W = a.shape[:2]
    for x0, y0, x1, y1 in bars:
        ix0, ix1, iy0, iy1 = max(int(np.floor(x0)), 0), min(int(np.ceil(x1)), W), max(int(np.floor(y0)), 0), min(int(np.ceil(y1)), H)
        cx = np.clip(np.minimum(np.arange(ix0, ix1) + 1, x1) - np.maximum(np.arange(ix0, ix1), x0), 0, 1)
        cy = np.clip(np.minimum(np.arange(iy0, iy1) + 1, y1) - np.maximum(np.arange(iy0, iy1), y0), 0, 1)
        cov = (cy[:, None] * cx[None, :])[..., None]
        out[iy0:iy1, ix0:ix1] = out[iy0:iy1, ix0:ix1] * (1 - cov) + np.asarray(col, np.float32) * cov
    return out


def door_leaves(sashes, H, W):
    """The ground floor's door leaves (the sashes of two columns and more than four rows, under the second storey's sill
    line) in metres from the image's left (its east end): per bay [outer, middle, outer], each outer the leaf's glass less
    its stile, the middle the meeting stiles' line; and the leaves' head, a transom bar under the transoms' glass (the
    single-lite sashes over them)."""
    pxm = H / H_M
    leaves = sorted([s for s in sashes if s['cols'] == 2 and s['rows'] > 4 and s['box'][1] > 0.5 * H], key=lambda s: s['box'][0])
    trans = [s for s in sashes if s['cols'] == 1 and s['rows'] == 1 and s['box'][1] > 0.5 * H]
    if len(leaves) != 8 or not trans:
        return None
    U = lambda x: round(x / W * W_M, 3)
    bays = []
    for a, b in zip(leaves[0::2], leaves[1::2]):
        bays.append([U(a['box'][0]) - LEAF_STILE, round((U(a['box'][2]) + U(b['box'][0])) / 2, 3), U(b['box'][2]) + LEAF_STILE])
    foot = float(np.median([s['box'][3] for s in trans]))
    return {'bays': [[round(v, 3) for v in q] for q in bays], 'top': round((H - foot) / pxm - TRANSOM_BAR, 3)}


# the door leaves' stiles outside their glass and the transom bar under the transoms' glass, metres, measured once by hand on
# lower-e (the leaf's glass 0.1 m in from its hinge edge, the transom bar 0.11 m)
LEAF_STILE, TRANSOM_BAR = 0.1, 0.11


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--masks', action='store_true')
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    if a.masks:
        write_masks()
        return
    lowp, upp = chosen('frames', 'lower'), chosen('frames', 'upper')
    if not (os.path.exists(lowp) and os.path.exists(upp)):
        sys.exit('ERROR: no chosen frames (run fetch_glory_art.py --stage frames)')
    lo, up = load(lowp), load(upp)
    klo, kup = key_of(lo), key_of(up)
    up = toward_brick(up, kup)
    lo = toward_stone(lo, klo)
    sl, su = float(klo.mean()), float(kup.mean())
    if not (0.15 <= sl <= 0.45) or not (0.10 <= su <= 0.22):
        sys.exit('ERROR: the key covers %.3f of the lower elevation and %.3f of the upper (expected 0.15 to 0.45 and 0.10 to 0.22)' % (sl, su))
    Ml, wl, (blo, bhi) = measure_lower(lo, klo)
    Mu, wu, number = measure_upper(up, kup)
    meas = dict(NOMINAL)
    meas.update(Ml); meas.update(Mu)
    for w in wl + wu:
        print('WARNING:', w, '(the nominal numbers stand in)')
    rise = meas['crown'] - meas['spring']
    if rise > ARCH_RISE_MAX:
        sys.exit('ERROR: %s\'s arches rise %.2f m over their springing (the real storey\'s low arch is 0.3 to 0.5 m; at most %.2f)' % (F.CHOSEN['lower'], rise, ARCH_RISE_MAX))
    meas['cornice'] = CORNICE.get(F.CHOSEN['lower'], NOMINAL['cornice'])
    meas['capital'] = CAPITAL.get(F.CHOSEN['lower'], NOMINAL['capital'])
    # the glass: the edit pasted back inside the key only, else dark glass
    gp = os.path.join(RAW, 'glass', 'upper.png')
    upf = fill_key(up, dilate(kup, 2))
    if os.path.exists(gp):
        g = Image.open(gp).convert('RGB')
        if g.size != (up.shape[1], up.shape[0]):
            g = g.resize((up.shape[1], up.shape[0]), Image.LANCZOS)
        ga = np.asarray(g, np.float32) / 255
        al = np.asarray(to_img(np.repeat(dilate(kup, 2)[..., None], 3, -1).astype(np.float32)).filter(ImageFilter.GaussianBlur(0.8)), np.float32)[..., :1] / 255
        al = np.maximum(al, dilate(kup, 1)[..., None].astype(np.float32))
        upf = upf * (1 - al) + ga * al
        glass_src = 'edit'
    else:
        upf = np.where(kup[..., None], np.array([0.09, 0.10, 0.11], np.float32), upf)
        glass_src = 'dark'
        print('WARNING: no glass edit yet: the upper windows are dark glass')
    lof = fill_dark(lo, dilate(klo, 2))   # over the key's anti-aliased edge too, from the dark frame only: no green fringe and no pale rim round a pane in any mip
    # the lower elevation's lites regular at the mask's size, and their straight bars painted in the frame's own colour (the
    # median of the image's bars as filled), so the bar the mask keeps is the bar the atlas shows
    glass_lo, bars_lo, sashes_lo = regular_lites(klo, (EH // MASK_DIV, EW // MASK_DIV))
    lof = paint_bars(lof, bars_lo, np.median(lof[pane_bars(klo)], 0))   # the bars' pixels as filled from the dark frame (lo's carry the key's green rim)
    leaves = door_leaves(sashes_lo, *klo.shape)
    if not leaves:
        sys.exit('ERROR: the ground floor\'s eight door leaves and their transoms were not found')
    # ---- the facade atlas
    atlas = Image.new('RGB', (AW, AH), (128, 128, 128))
    xl, xu, ye = PAD, PAD * 3 + EW, PAD
    atlas = gutter(atlas, to_img(lof).resize((EW, EH), Image.LANCZOS), xl, ye)
    atlas = gutter(atlas, to_img(upf).resize((EW, EH), Image.LANCZOS), xu, ye)
    pxm_src = lo.shape[0] / H_M
    sw_imgs = {}
    # granite from the piers' faces (granite_swatch), brick from between the bottom storey's windows
    sw_imgs['granite'], SW_M['granite'] = granite_swatch(lo, klo, meas)
    wn = meas['win']
    bu0, bu1 = wn[0][1] + 0.08, wn[1][0] - 0.08
    by0 = wn[0][2] + 0.25
    side = min(bu1 - bu0, 1.0)
    crop = to_img(up).crop((int(bu0 / W_M * up.shape[1]), int(up.shape[0] - (by0 + side) * pxm_src), int((bu0 + side) / W_M * up.shape[1]), int(up.shape[0] - by0 * pxm_src)))
    sw_imgs['brick'] = tileable(crop.resize((SW, SW), Image.LANCZOS))
    SW_M['brick'] = round(side, 3)
    # poured concrete: a fine aggregate's grain over a faint mottle, no clouds (Round 191's third review: the 8 cm field at
    # 14% read as camouflage)
    sw_imgs['concrete'] = noise_swatch((125, 118, 109), 0.07, 1, scales=((5, 0.25), (18, 0.5), (48, 0.45)), fine=0.6)
    sw_imgs['iron'] = noise_swatch((38, 40, 42), 0.10, 2)
    sw_imgs['rustblue'] = peel_swatch(3)
    sw_imgs['glow'] = noise_swatch((255, 207, 138), 0.03, 4)
    sw_imgs['roof'] = noise_swatch((76, 74, 71), 0.14, 5)
    sw_imgs['rust'] = rust_swatch(6)
    swatches = {}
    for i, name in enumerate(SWATCHES):
        x = PAD + i * (SW + 2 * PAD)
        atlas = gutter(atlas, sw_imgs[name], x, SW_Y)
        swatches[name] = {'rect': uv_rect(x, SW_Y, SW, SW, AW, AH), 'm': SW_M[name], 'i': i}
    # ---- the mask, at half size
    mk = np.zeros((AH // MASK_DIV, AW // MASK_DIV, 3), np.uint8)

    def mask_elev(k, x, kind, pane_no):
        h0, w0 = k.shape
        r = np.zeros((h0, w0), np.uint8); g = np.zeros_like(r); b = np.zeros_like(r)
        r[k] = 255
        # g and b over each pane's box and two pixels round it, so the glass's eased edge (r, below) always finds them
        if kind == 'lower':
            for i, bb in enumerate(sorted(blo + bhi, key=lambda t: (t[0], t[1]))):
                y0, x0, y1, x1 = bb[0] - 2, bb[1] - 2, bb[2] + 3, bb[3] + 3
                g[y0:y1, x0:x1] = (i + 1) % 256
                b[y0:y1, x0:x1] = 200 if (bb[0] + bb[2]) / 2 > 0.5 * h0 else 216
        else:
            pxm = h0 / H_M
            for (y0, x0, y1, x1), wi in pane_no.items():
                w = meas['win'][wi]
                y0, x0, y1, x1 = y0 - 2, x0 - 2, y1 + 3, x1 + 3
                g[y0:y1, x0:x1] = wi + 1
                ys = (h0 - np.arange(y0, y1) - 0.5) / pxm
                t = np.clip((ys - w[2]) / max(w[3] - w[2], 0.1), 0, 1)
                b[y0:y1, x0:x1] = (t[:, None] * 64 + 0.5).astype(np.uint8)
        img = Image.fromarray(np.stack([r, g, b], -1)).resize((EW // MASK_DIV, EH // MASK_DIV), Image.NEAREST)
        # r: the glass's cover, eased at its edges by a box resize. The glass is grown two full-size pixels toward the outer
        # frame only, so it covers the pane's rim (at none, the rim drew the facade's own colour as a pale line round every
        # pane, Round 191's review), and never into a bar between two panes of one opening (pane_bars), which stays at 0 two
        # texels wide at the mask's size (bar_texels): grown into from both sides, the muntins were one texel at a third or two
        # thirds of the glass, and the French doors and the casements drew as single dark sheets by day and unbroken glowing
        # panes at night (Round 191's second review)
        # the lower elevation's lites are regular rectangles of whole texels with straight bars (regular_lites, Round 191's
        # third review: the image's own bars wobbled a texel and every lite was rounded)
        if kind == 'lower':
            rr = glass_lo.astype(np.uint8) * 255
        else:
            bars = pane_bars(k)
            rr = to_img(np.repeat((dilate(k, 2) & ~bars)[..., None].astype(np.float32), 3, -1)).resize((EW // MASK_DIV, EH // MASK_DIV), Image.BOX)
            rr = np.asarray(rr)[..., 0].copy()
            rr[bar_texels(bars, (EH // MASK_DIV, EW // MASK_DIV))] = 0
        arr = np.asarray(img).copy()
        arr[..., 0] = rr
        y = ye // MASK_DIV
        mk[y:y + EH // MASK_DIV, x // MASK_DIV:x // MASK_DIV + EW // MASK_DIV] = arr
    mask_elev(klo, xl, 'lower', None)
    mask_elev(kup, xu, 'upper', number)
    gx = PAD + SWATCHES.index('glow') * (SW + 2 * PAD)
    mk[(SW_Y - PAD) // 2:(SW_Y + SW + PAD) // 2, (gx - PAD) // 2:(gx + SW + PAD) // 2, 2] = 240
    mask_img = Image.fromarray(mk)
    # ---- the interior atlas: the open rooms at full width, the closed at half, side by side
    plates, rows = {}, []
    room_imgs = {}
    for kind in ('ground', 'upperroom'):
        ep = chosen('rooms', kind)
        if not os.path.exists(ep):
            print('WARNING: no %s room plate yet' % kind)
            continue
        if F.CHOSEN[kind] not in BACK:
            sys.exit('ERROR: the %s plate %s has no back wall rectangle (BACK)' % (kind, F.CHOSEN[kind]))
        cp = os.path.join(RAW, 'crowd', ('ground' if kind == 'ground' else 'upper') + '.png')
        room_imgs[kind] = (Image.open(cp).convert('RGB') if os.path.exists(cp) else Image.open(ep).convert('RGB'), Image.open(ep).convert('RGB'), os.path.exists(cp))
    ih = PAD
    lay = {}
    for kind, (op, cl, crowd) in room_imgs.items():
        w0, h0 = op.size
        hh = int(round(IW * h0 / w0))
        lay[kind + '-open'] = (0, ih, IW, hh, op)
        ih += hh + PAD
    ch_y, cx = ih, 0
    chh = 0
    for kind, (op, cl, crowd) in room_imgs.items():
        w0, h0 = cl.size
        hh = int(round((IW // 2 - PAD) * h0 / w0))
        lay[kind + '-closed'] = (cx, ch_y, IW // 2 - PAD, hh, cl)
        cx += IW // 2
        chh = max(chh, hh)
    IH = ((ch_y + chh + PAD) + 7) // 8 * 8 if room_imgs else 8
    iat = Image.new('RGB', (IW, IH), (20, 16, 12))
    imk = np.zeros((IH // MASK_DIV, IW // MASK_DIV, 3), np.uint8)
    for name, (x, y, w, h, im) in lay.items():
        r = im.resize((w, h), Image.LANCZOS)
        iat.paste(r, (x, y))
        ra = np.asarray(r, np.float32) / 255
        bulbs = dilate(blob_px(ra), 1)
        warm = (ra[..., 0] > 0.55) & (ra[..., 0] > ra[..., 2] * 1.5) & (lum(ra) > 0.35)
        sub = np.zeros((h, w, 3), np.uint8)
        sub[..., 0] = np.where(bulbs, 255, 0)
        sub[..., 1] = np.asarray(to_img(np.repeat(warm[..., None].astype(np.float32), 3, -1)).filter(ImageFilter.GaussianBlur(2)))[..., 0]
        sm = Image.fromarray(sub).resize((w // MASK_DIV, h // MASK_DIV), Image.BOX)
        imk[y // MASK_DIV:y // MASK_DIV + h // MASK_DIV, x // MASK_DIV:x // MASK_DIV + w // MASK_DIV] = np.asarray(sm)
        kind = name.rsplit('-', 1)[0]
        plates[name] = {'rect': uv_rect(x, y, w, h, IW, IH), 'back': BACK[F.CHOSEN[kind]], 'room': ROOM[kind]}
    # ---- write
    files = {}
    files['img'] = art_files.write(atlas, 'glory', 'facade', 'WEBP', quality=90, method=6)
    files['imgHalf'] = art_files.write(atlas.resize((AW // 2, AH // 2), Image.LANCZOS), 'glory', 'facade-half', 'WEBP', quality=88, method=6)
    files['mask'] = art_files.write(mask_img, 'glory', 'facade-mask', 'PNG', optimize=True)
    files['maskHalf'] = art_files.write(mask_img.resize((AW // 4, AH // 4), Image.NEAREST), 'glory', 'facade-mask-half', 'PNG', optimize=True)
    interior = None
    if lay:
        im_mask = Image.fromarray(imk)
        interior = {
            'img': art_files.write(iat, 'glory', 'rooms', 'WEBP', quality=86, method=6),
            'imgHalf': art_files.write(iat.resize((IW // 2, IH // 2), Image.LANCZOS), 'glory', 'rooms-half', 'WEBP', quality=84, method=6),
            'mask': art_files.write(im_mask, 'glory', 'rooms-mask', 'PNG', optimize=True),
            'maskHalf': art_files.write(im_mask.resize((IW // 4, IH // 4), Image.BOX), 'glory', 'rooms-mask-half', 'PNG', optimize=True),
            'w': IW, 'h': IH, 'depth': DEPTH, 'plates': plates,
            'crowd': {k: v[2] for k, v in room_imgs.items()},
        }
    gone = art_files.prune('glory')
    man = {
        'v': 1, **files, 'w': AW, 'h': AH, 'pxm': round(EW / W_M, 3),
        'lower': {'rect': uv_rect(xl, ye, EW, EH, AW, AH), **{k: meas[k] for k in ('bays', 'doorTop', 'doorFoot', 'arcade', 'spring', 'crown', 'sill2', 'cols', 'colR', 'cornice', 'capital')}, 'leaves': leaves},
        'upper': {'rect': uv_rect(xu, ye, EW, EH, AW, AH), 'win': meas['win'], 'glass': glass_src},
        'swatches': swatches,
        'interior': interior,
        'gen': {'model': F.MODEL, 'chosen': F.CHOSEN, 'warnings': wl + wu},
    }
    json.dump(man, open(OUT, 'w'), separators=(',', ':'))
    print('glory_art.json: lower key %.3f, upper key %.3f, glass %s, %d plates, pruned %d' % (sl, su, glass_src, len(plates), gone))
    for k in ('img', 'imgHalf', 'mask', 'maskHalf'):
        print(' ', k, files[k], art_files.size(files[k]) // 1024, 'KB')
    if interior:
        for k in ('img', 'imgHalf', 'mask', 'maskHalf'):
            print(' ', k, interior[k], art_files.size(interior[k]) // 1024, 'KB')
    print(json.dumps({k: man['lower'][k] for k in man['lower'] if k != 'rect'}))
    print(json.dumps(man['upper']['win']))
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        atlas.save(os.path.join(a.preview, 'facade.jpg'), quality=90)
        mask_img.save(os.path.join(a.preview, 'facade-mask.png'))
        if lay:
            iat.save(os.path.join(a.preview, 'rooms.jpg'), quality=90)
            Image.fromarray(imk).save(os.path.join(a.preview, 'rooms-mask.png'))


# the granite cornice over the second storey [y0, y1] in metres over the sidewalk, measured once by hand on the chosen
# lower elevation (the corona's foot to the image's top)
CORNICE = {'lower-b': [8.6, 9.3], 'lower-e': [8.78, 9.3]}
# the piers' painted capitals, measured once by hand on the chosen lower elevation (Round 191's second review: the cap boxes
# ran 0.1 m under them and out to the party walls, their undersides a pale slab past the painted end): y their foot (the
# shadow line under the cyma) and top, ends the end capitals' margins from the image's left (east) and right (west) edges,
# out how far an inner capital runs past its pier either side
CAPITAL = {'lower-e': {'y': [3.94, 4.08], 'ends': [0.2, 0.15], 'out': 0.05}}

if __name__ == '__main__':
    main()
