#!/usr/bin/env python3
"""Bake the storefronts' shopfronts (Round 189, Mike: "Do the storefront boxes on Broad Street too") into
storefront_art.json, which build.py inlines as STOREFRONT_ART, and the atlas itself into art/storefronts/ (art_files.py:
files the page loads on demand, a phone's half copies beside them).

fetch_storefront_art.py makes each cell in two stages: the shopfront EMPTY, every pane of glass a flat chroma-key green
(lidar_cache/storefront_art_raw/frames/<id>.png), then the same image with the shop's interior painted into the panes
through /v1/images/edits (insides/<id>.png). The glass is the key, found to the pixel (KEY_*): --masks writes the edit's
mask from it (<id>-mask.png beside the frame: transparent over the panes, an API input that never ships), and the bake
pastes back ONLY the keyed pixels of the edit (a pixel's feather), so the frame and its mask stay exactly registered
whatever the edit did elsewhere. A cell whose edit is missing borrows its trade's own edits (plates: each pane's largest
clean rectangle, scaled to cover each of its panes; a grocery's corner store the groceries' and the shops'), else one of the
trade's fallback interiors (interiors/, composited behind the key), and one with none keeps dark glass (the review's
second set was framed before the API's credit ran out, and its 24 cells all borrow).

Per cell the bake finds the fascia board (the longest run of uniform rows in the top quarter, grown sideways to the pier
caps), checks it is blank (its luminance spread: lettering raises it), and measures from the foot the bulkhead's top (the
display panes' sills), the glass head and the board's bottom and top: the page keeps the bulkhead and the fascia at their
own height and rescales only the glass band between them to the storey it dresses. The cell is laid at PXM pixels a
metre (its class's nominal width by 4.2 m), its edge pixels run out across a PAD gutter so the mips never bleed, into a
shelf-packed atlas, and an opaque RGB mask atlas at half its size (bake_fronts.py: an image with any alpha under 255
reaches WebGL through a premultiplied decode on WebKit, which moves the mask's values): r the glass, g the fascia board,
b the door. The manifest names the files and carries every cell's place in the atlas (its rect in texture uv, flipped as
the page samples it), its rows, its board and its colours, and 'gen': eight cells a class for the painted shop floors
(style 5) that no OSM record dresses (banks, venues and trades kept off anonymous walls).

Usage: python3 bake_storefront_art.py [--masks] [--preview DIR] [--force]"""
import argparse, json, math, os, sys, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import art_files
from bake_fronts import blobs, dilate, erode, lum
import fetch_storefront_art as F

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'storefront_art_raw')
OUT = os.path.join(HERE, 'storefront_art.json')
PXM = 44            # atlas pixels a metre (50 until the review's second set: 110 cells at 50 wanted a 4096 by 2712 atlas,
                    # a third more memory on a phone; at 44 they fit the same 4096 by 2048)
H_M = 4.2           # every image is one storey, 4.2 m, sidewalk to the top of the fascia
CELL_H = 2 * int(round(H_M * PXM / 2))   # even, so the half-size mask's cells keep their rows
PAD = 8
AW, AH = 4096, 2048
MASK_DIV = 2
GEN_FAMS = ('retail', 'restaurant', 'cafe', 'grocery', 'bakery', 'boutique', 'salon', 'takeout')
# the key: a pane's flat chroma green (and the anti-aliased pixels at its frames, which the paste's dilation covers)
KEY_G, KEY_GAP = 0.5, 0.3
DOOR_W = (0.5, 1.15, 0.25, 0.8)   # a door leaf's glass in metres: a single leaf's least and most, a pair's leaf's least and most
SPILL = 0.05   # green over the other channels (and a fifth of the luminance) past which a pixel by the glass is the key's spill (despill)
# hand corrections, like bake_fronts.DISPLAY_DARK: a cell whose board the finder misreads, as [y0, x0, y1, x1] in
# fractions of the image from its top-left
BOARD_FIX = {}


def key_of(a):
    """The chroma-key glass of a frame (a: H by W by 3, 0 to 1) as a boolean image."""
    return (a[..., 1] > KEY_G) & (a[..., 1] - np.maximum(a[..., 0], a[..., 2]) > KEY_GAP)


def write_masks(force):
    d = os.path.join(RAW, 'frames')
    n = 0
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not f.endswith('.png') or f.endswith('-mask.png'):
            continue
        out = os.path.join(d, f[:-4] + '-mask.png')
        if os.path.exists(out) and not force:
            continue
        a = np.asarray(Image.open(os.path.join(d, f)).convert('RGB'), np.float32) / 255.0
        k = dilate(key_of(a), 3)
        rgba = np.zeros(a.shape[:2] + (4,), np.uint8)
        rgba[..., 3] = np.where(k, 0, 255)
        Image.fromarray(rgba).save(out)
        n += 1
        print(f[:-4], 'glass %.3f' % key_of(a).mean(), flush=True)
    print(n, 'masks written')


def band_of(a, key):
    """The fascia board: (y0, x0, y1, x1) in pixels, the longest run of uniform rows (small spread across the middle,
    small steps between rows: a painted board's soft gradient is one run) that starts in the top quarter, grown sideways
    while the columns' colour holds."""
    H, W = a.shape[:2]
    c0, c1 = int(.15 * W), int(.85 * W)
    med = np.median(a[:, c0:c1], 1)
    L = lum(a)
    sd = L[:, c0:c1].std(1)
    lim = int(.5 * H)
    best = (0, -1)
    y = 0
    while y < lim:
        if sd[y] >= 0.05 or key[y].any():
            y += 1
            continue
        y0 = y
        while y + 1 < lim and sd[y + 1] < 0.05 and not key[y + 1].any() and np.abs(med[y + 1] - med[y]).max() < 0.03:
            y += 1
        if y0 <= int(.25 * H) and y >= int(.04 * H) and y - y0 > best[1] - best[0]:
            best = (y0, y)
        y += 1
    y0, y1 = best
    if y1 < 0:
        return None
    cm = np.median(a[y0:y1 + 1], 0)
    x0 = x1 = W // 2
    while x0 > 0 and np.abs(cm[x0 - 1] - cm[x0]).max() < 0.03:
        x0 -= 1
    while x1 < W - 1 and np.abs(cm[x1 + 1] - cm[x1]).max() < 0.03:
        x1 += 1
    return y0, x0, y1, x1


def to_hex(c):
    return '#%02x%02x%02x' % tuple(int(round(v * 255)) for v in np.clip(c, 0, 1))


def lin(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def despill(frame, band, key):
    """The key's green thrown onto the frame (a recessed entrance's sides and ceiling mirror the panes, an angled side pane
    in shade keys only part way), taken out near the glass: within about 40 px of the key a pixel greener than paint for its
    brightness (green over its other channels by more than SPILL plus a fifth of its luminance) keeps a quarter of that
    green. The fascia board is left as it is (a green board is paint), and so is a painted frame's dark green."""
    H, W = frame.shape[:2]
    g = frame[..., 1] - np.maximum(frame[..., 0], frame[..., 2])
    small = Image.fromarray((key * 255).astype(np.uint8)).resize((max(1, W // 8), max(1, H // 8)), Image.BOX)
    near = np.asarray(small.filter(ImageFilter.MaxFilter(11)).resize((W, H), Image.NEAREST)) > 0
    m = (g > SPILL + 0.2 * lum(frame)) & ~key & near
    y0, x0, y1, x1 = band
    m[int(y0 * H):int(np.ceil(y1 * H)), int(x0 * W):int(np.ceil(x1 * W))] = False
    out = frame.copy()
    mx = np.maximum(frame[..., 0], frame[..., 2])
    out[..., 1] = np.where(m, mx + 0.25 * np.maximum(g, 0), frame[..., 1])
    return out, int(m.sum())


def largest_rect(m):
    """The largest axis-aligned rectangle of True in a boolean image (the histogram method): (y0, x0, y1, x1) inclusive,
    or None."""
    H, W = m.shape
    h = np.zeros(W, np.int32)
    best, bA = None, 0
    for y in range(H):
        h = np.where(m[y], h + 1, 0)
        st = []
        for x in range(W + 1):
            hx = h[x] if x < W else 0
            start = x
            while st and st[-1][1] >= hx:
                s0, sh = st.pop()
                A = sh * (x - s0)
                if A > bA:
                    bA, best = A, (y - sh + 1, s0, y, x - 1)
                start = s0
            st.append((start, hx))
    return best


_PLATES = {}
def plates(fam):
    """The panes of a trade's own interior edits (insides/), each the largest clean rectangle of keyed glass in a pane, as
    (image, y0, x0, y1, x1) in its pixels: the interiors a cell whose edit is missing borrows (the review's second set was
    framed before the API's credit ran out, and no edit could be made for it)."""
    if fam in _PLATES:
        return _PLATES[fam]
    out = []
    for cid, f2, cls, v, _, _ in F.cells():
        if f2 != fam:
            continue
        pi, pf = os.path.join(RAW, 'insides', cid + '.png'), os.path.join(RAW, 'frames', cid + '.png')
        if not (os.path.exists(pi) and os.path.exists(pf)):
            continue
        fr = np.asarray(Image.open(pf).convert('RGB'), np.float32) / 255.0
        k = erode(key_of(fr), 2)
        H, W = k.shape
        sm = np.asarray(Image.fromarray((k * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BOX)) > 250
        ins = Image.open(pi).convert('RGB')
        if ins.size != (W, H):
            ins = ins.resize((W, H), Image.LANCZOS)
        for by0, bx0, by1, bx1, cnt in blobs(sm):
            if cnt < 200:
                continue
            sub = np.zeros_like(sm)
            sub[by0:by1 + 1, bx0:bx1 + 1] = sm[by0:by1 + 1, bx0:bx1 + 1]
            r = largest_rect(sub[by0:by1 + 1, bx0:bx1 + 1])
            if not r:
                continue
            y0, x0, y1, x1 = r[0] + by0, r[1] + bx0, r[2] + by0, r[3] + bx0
            if (y1 - y0 + 1) * (x1 - x0 + 1) < 300:
                continue
            out.append((ins, (y0 + 1) * 4, (x0 + 1) * 4, y1 * 4 + 3, x1 * 4 + 3, cid))
    _PLATES[fam] = out
    return out


def transplant(cid, fam, frame, key):
    """A cell's interior from its trade's own edits (plates): each pane of its glass (the key closed over its bars and
    glazing bars) takes a plate, the one nearest its shape of those not yet used in the cell, scaled to cover it; or None.
    A grocery's corner store takes the groceries' and the shops' plates; the shop's and the takeout's corner frames their
    own trade's (the review: a stationer and a pizzeria showed a bodega's produce and deli case, and the takeout's second
    M was the grocery's to the shelf)."""
    pool = plates('grocery') + plates('retail') if cid in F.CORNER and fam == 'grocery' else plates(fam)
    if not pool:
        return None
    H, W = key.shape
    closed = erode(dilate(key, 7), 7)
    sm = np.asarray(Image.fromarray((closed * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BOX)) > 127
    src = Image.fromarray((np.clip(frame, 0, 1) * 255).astype(np.uint8))
    used = []
    seed = zlib.crc32(cid.encode())
    for by0, bx0, by1, bx1, cnt in sorted(blobs(sm), key=lambda b: (b[1], b[0])):
        if cnt < 6:
            continue
        y0, x0, y1, x1 = max(0, by0 * 4 - 8), max(0, bx0 * 4 - 8), min(H, by1 * 4 + 12), min(W, bx1 * 4 + 12)   # over the key's edge pixels
        bw, bh = x1 - x0, y1 - y0
        asp = bw / max(1, bh)
        order = sorted(range(len(pool)), key=lambda q: (q in used, abs(math.log(asp / ((pool[q][4] - pool[q][2]) / max(1, pool[q][3] - pool[q][1])))),
                                                       (q * 2654435761 + seed) % 97))
        q = order[0]
        used.append(q)
        im, py0, px0, py1, px1, _ = pool[q]
        pw, ph = px1 - px0, py1 - py0
        sc = max(bw / pw, bh / ph)
        cw, ch = bw / sc, bh / sc   # the plate's crop at the pane's aspect, centred
        cx0, cy0 = px0 + (pw - cw) / 2, py0 + (ph - ch) / 2
        piece = im.crop((int(cx0), int(cy0), int(math.ceil(cx0 + cw)), int(math.ceil(cy0 + ch)))).resize((bw, bh), Image.LANCZOS)
        src.paste(piece, (x0, y0))
    return np.asarray(src, np.float32) / 255.0


def composite(cid, fam, frame, key, transplant_ok=True):
    """The frame with the shop's interior in its panes: the edit's own pixels under the key (a pixel's feather), else the
    trade's fallback interior behind it, else dark glass. Returns (image, source)."""
    paste = dilate(key, 2)
    alpha = np.asarray(Image.fromarray((paste * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32)[..., None] / 255.0
    alpha = np.maximum(alpha, key[..., None].astype(np.float32))
    H, W = key.shape
    src = None
    p = os.path.join(RAW, 'insides', cid + '.png')
    if os.path.exists(p):
        ins = Image.open(p).convert('RGB')
        if ins.size != (W, H):
            ins = ins.resize((W, H), Image.LANCZOS)
        src = np.asarray(ins, np.float32) / 255.0
        how = 'inside'
    elif transplant_ok and (tp := transplant(cid, fam, frame, key)) is not None:
        src, how = tp, 'plates'
    else:
        ints = sorted(f for f in os.listdir(os.path.join(RAW, 'interiors')) if f.startswith(fam + '-') and f.endswith('.png')) \
            if os.path.isdir(os.path.join(RAW, 'interiors')) else []
        if ints:
            im = Image.open(os.path.join(RAW, 'interiors', ints[zlib.crc32(cid.encode()) % len(ints)])).convert('RGB')
            s = max(W / im.width, H / im.height)
            im = im.resize((int(math.ceil(im.width * s)), int(math.ceil(im.height * s))), Image.LANCZOS)
            ox, oy = (im.width - W) // 2, (im.height - H) // 2
            src = np.asarray(im.crop((ox, oy, ox + W, oy + H)), np.float32) / 255.0
            how = 'interior'
        else:
            src = np.zeros_like(frame) + np.array([0.05, 0.06, 0.07], np.float32)
            how = 'dark'
    out = frame * (1 - alpha) + src * alpha
    return out, how


def analyse(cid, fam, cls, frame):
    """The cell's measures and checks from its empty frame (full size, 0 to 1)."""
    H, W = frame.shape[:2]
    key = key_of(frame)
    # the board on a working copy (the key's green kept out of every test)
    s = 512 / W
    wa = np.asarray(Image.fromarray((frame * 255).astype(np.uint8)).resize((512, max(8, int(round(H * s)))), Image.BILINEAR), np.float32) / 255.0
    wk = np.asarray(Image.fromarray((key * 255).astype(np.uint8)).resize((512, wa.shape[0]), Image.BILINEAR)) > 20
    bd = band_of(wa, wk)
    if cid in BOARD_FIX:
        f = BOARD_FIX[cid]
        bd = (int(f[0] * wa.shape[0]), int(f[1] * 512), int(f[2] * wa.shape[0]), int(f[3] * 512))
    notes = []
    if bd is None:
        notes.append('no board')
        bd = (0, 0, int(.15 * wa.shape[0]), 511)
    y0, x0, y1, x1 = bd
    Hw = wa.shape[0]
    inner = lum(wa[y0 + 2:max(y0 + 3, y1 - 1), x0 + 4:max(x0 + 5, x1 - 3)])
    bstd = float(inner.std())
    if bstd > 0.07:
        notes.append('board not blank (%.3f)' % bstd)
    boardC = np.median(wa[y0 + 2:max(y0 + 3, y1 - 1), x0 + 4:max(x0 + 5, x1 - 3)].reshape(-1, 3), 0)
    boardL = float(0.2126 * lin(boardC[0]) + 0.7152 * lin(boardC[1]) + 0.0722 * lin(boardC[2]))
    # the glass's rows and the piers' columns
    share = float(key.mean())
    half = F.FAMILIES[F.FAM_IX[fam]][3]
    lo_, hi_ = (0.10, 0.50) if half else (0.18, 0.75)
    if not (lo_ <= share <= hi_):
        notes.append('glass share %.2f' % share)
    cols = np.nonzero(key.any(0))[0]
    rows_ = np.nonzero(key.any(1))[0]
    if not len(cols):
        notes.append('no glass')
        cols = np.array([int(.1 * W), int(.9 * W)]); rows_ = np.array([int(.3 * H), int(.8 * H)])
    bottoms = []
    for x in range(int(cols[0]), int(cols[-1]) + 1, 4):
        ys = np.nonzero(key[:, x])[0]
        if len(ys):
            bottoms.append(ys[-1])
    yb = float(np.percentile(bottoms, 30)) if bottoms else float(rows_[-1])   # the displays' sills (a door's glass runs lower)
    yt = float(rows_[0])
    bulkTop = 1 - (yb + 1) / H
    head = 1 - yt / H
    bandBot = 1 - (y1 + 1) / Hw
    bandTop = 1 - y0 / Hw
    if bandBot < head - 0.02:
        notes.append('board under the glass head')
        bandBot = min(1.0, head + 0.01)
    pierL, pierR = float(cols[0]) / W, float(cols[-1] + 1) / W
    pl = frame[:, :max(2, int(cols[0]))].reshape(-1, 3)
    pr = frame[:, min(W - 2, int(cols[-1]) + 1):].reshape(-1, 3)
    pierC = np.median(np.concatenate([pl, pr]), 0)
    # the door: a keyed pane standing lowest and tall for its width (its glass closed over a rail across it), a leaf's
    # width (DOOR_W: the review found a display window of 1.6 m and strips of 4 to 47 cm taken for doors in a dozen
    # cells), or a pair of narrower leaves side by side with the same foot and head (a double door's)
    door = None
    small = np.asarray(Image.fromarray((key * 255).astype(np.uint8)).resize((256, max(8, int(round(H * 256 / W)))), Image.NEAREST)) > 127
    hS = small.shape[0]
    pxm = 256 / F.CLASSES[cls][0]
    rail = max(1, int(round(0.12 * pxm)))
    vc = small.copy()
    for d in range(1, rail + 1):   # a vertical close: a door's rail between its panes
        vc |= np.roll(small, d, 0) & np.roll(small, -d, 0)
    cands = []
    for by0, bx0, by1, bx1, cnt in blobs(vc):
        bh, bw = by1 - by0 + 1, bx1 - bx0 + 1
        if bh > 0.3 * hS and bw < 0.75 * bh and cnt > 0.5 * bh * bw and DOOR_W[2] <= bw / pxm <= max(DOOR_W[1], DOOR_W[3]):
            cands.append((by1, bh, bx0, bx1, by0))
    doors = []
    for c in cands:
        leaf = lambda q: (q[3] - q[2] + 1) / pxm <= DOOR_W[3]
        mate = [q for q in cands if q is not c and leaf(c) and leaf(q) and abs(q[0] - c[0]) <= 0.03 * hS and abs(q[4] - c[4]) <= 0.05 * hS
                and (0 <= q[2] - c[3] <= 0.35 * pxm or 0 <= c[2] - q[3] <= 0.35 * pxm)]
        x0_, x1_ = c[2], c[3]
        for q in mate:
            x0_, x1_ = min(x0_, q[2]), max(x1_, q[3])
        if (mate and (x1_ - x0_ + 1) / pxm <= 1.9) or DOOR_W[0] <= (c[3] - c[2] + 1) / pxm <= DOOR_W[1]:
            doors.append((c[0], c[1], x0_, x1_))
    if doors:
        lowest = max(c[0] for c in doors)
        dc = [c for c in doors if c[0] >= lowest - 2]
        c = max(dc, key=lambda q: q[1])
        if c[0] / hS > 1 - bulkTop - 0.02 or len({(q[2], q[3]) for q in dc}) == 1:
            door = [round(c[2] / 256, 4), round((c[3] + 1) / 256, 4)]
    if door is None:
        notes.append('no door found')
    return {'key': key, 'band': (y0 / Hw, x0 / 512, (y1 + 1) / Hw, (x1 + 1) / 512), 'boardC': boardC, 'boardL': boardL,
            'bstd': bstd, 'share': share, 'rows': [bulkTop, head, bandBot, bandTop], 'pier': [pierL, pierR], 'pierC': pierC,
            'door': door, 'notes': notes}


def gutter(img, W, H, pad):
    inner = img.resize((W - 2 * pad, H - 2 * pad), Image.LANCZOS)
    a = np.asarray(inner)
    return Image.fromarray(np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode='edge'))


def bake(preview):
    cells = F.cells()
    made, missing = [], []
    for cid, fam, cls, v, _, _ in cells:
        p = os.path.join(RAW, 'frames', cid + '.png')
        if not os.path.exists(p):
            missing.append(cid)
            continue
        made.append((cid, fam, cls, v, p))
    if missing:
        print('missing frames (left out):', ', '.join(missing))
    # shelf packing, widest first, every row CELL_H + 2 PAD tall
    rowH = CELL_H + 2 * PAD
    order = sorted(made, key=lambda c: (-F.CLASSES[c[2]][0], c[0]))
    place, x, y = {}, 0, 0
    for c in order:
        cw = 2 * int(round(F.CLASSES[c[2]][0] * PXM / 2)) + 2 * PAD
        if x + cw > AW:
            x, y = 0, y + rowH
        if y + rowH > AH:
            sys.exit('the atlas is full: %d cells did not fit' % (len(order) - len(place)))
        place[c[0]] = (x, y, cw)
        x += cw
    atlas = Image.new('RGB', (AW, AH), (0, 0, 0))
    mAW, mAH, mP = AW // MASK_DIV, AH // MASK_DIV, PAD // MASK_DIV
    mask = Image.new('RGB', (mAW, mAH), (0, 0, 0))
    out_cells, sheet = [], []
    srcs = {}
    for cid, fam, cls, v, p in made:
        frame = np.asarray(Image.open(p).convert('RGB'), np.float32) / 255.0
        A = analyse(cid, fam, cls, frame)
        frame, spilled = despill(frame, A['band'], A['key'])
        if spilled > 50:
            A['notes'].append('despilled %d px' % spilled)
        comp, how = composite(cid, fam, frame, A['key'])
        srcs[how] = srcs.get(how, 0) + 1
        X, Y, cw = place[cid]
        ci = Image.fromarray((np.clip(comp, 0, 1) * 255 + 0.5).astype(np.uint8))
        atlas.paste(gutter(ci, cw, rowH, PAD), (X, Y))
        # the mask: r the glass (area-averaged to the cell), g the board, b the door's leaf
        iw, ih = cw // MASK_DIV - 2 * mP, rowH // MASK_DIV - 2 * mP
        r = np.asarray(Image.fromarray((A['key'] * 255).astype(np.uint8)).resize((iw, ih), Image.BOX), np.float32)
        g = np.zeros((ih, iw), np.float32)
        by0, bx0, by1, bx1 = A['band']
        g[int(round(by0 * ih)):int(round(by1 * ih)), int(round(bx0 * iw)):int(round(bx1 * iw))] = 255
        b = np.zeros((ih, iw), np.float32)
        if A['door']:
            b[int(round((1 - A['rows'][1]) * ih)):, int(round(A['door'][0] * iw)):int(round(A['door'][1] * iw))] = 255
        mc = np.stack([r, g, b], -1).astype(np.uint8)
        mask.paste(Image.fromarray(np.pad(mc, ((mP, mP), (mP, mP), (0, 0)), mode='edge')), (X // MASK_DIV, Y // MASK_DIV))
        gl = A['key']
        mean_in = comp[gl].mean(0) if gl.any() else np.array([0.1, 0.1, 0.1])
        u0, v0 = (X + PAD) / AW, 1 - (Y + rowH - PAD) / AH
        du, dv = (cw - 2 * PAD) / AW, (rowH - 2 * PAD) / AH
        bulkTop, head, bandBot, bandTop = A['rows']
        cell = {'id': cid, 'fam': F.FAM_IX[fam], 'cls': cls, 'nomW': F.CLASSES[cls][0],
                'rect': [round(u0, 6), round(v0, 6), round(du, 6), round(dv, 6)],
                'band': [round(A['band'][1], 4), round(bandBot, 4), round(A['band'][3], 4), round(bandTop, 4)],
                'rows': [round(bulkTop, 4), round(head, 4), round(bandBot, 4)],
                'pier': [round(A['pier'][0], 4), round(A['pier'][1], 4)], 'door': A['door'],
                'board': to_hex(A['boardC']), 'boardL': round(A['boardL'], 4), 'pierHex': to_hex(A['pierC']),
                'mean': to_hex(mean_in), 'glass': round(A['share'], 3), 'src': how}
        if A['notes']:
            cell['notes'] = A['notes']
        out_cells.append(cell)
        print('%-16s %-3s %-8s glass %.2f board %s std %.3f rows %s %s' % (cid, cls, how, A['share'], cell['board'], A['bstd'],
              cell['rows'], '; '.join(A['notes'])), flush=True)
        if preview:
            vi = ci.copy().convert('RGB')
            ov = np.asarray(vi).copy()
            Hh, Ww = ov.shape[:2]
            edge = A['key'] ^ erode(A['key'], 2)
            ov[edge] = (255, 0, 255)
            vi = Image.fromarray(ov)
            d = ImageDraw.Draw(vi)
            d.rectangle((bx0 * Ww, by0 * Hh, bx1 * Ww, by1 * Hh), outline=(0, 255, 0), width=4)
            for fr, col in ((bulkTop, (255, 255, 0)), (head, (0, 200, 255)), (bandBot, (0, 255, 0))):
                yy = (1 - fr) * Hh
                d.line((0, yy, Ww, yy), fill=col, width=3)
            if A['door']:
                d.rectangle((A['door'][0] * Ww, (1 - head) * Hh, A['door'][1] * Ww, Hh - 2), outline=(0, 120, 255), width=4)
            vi.save(os.path.join(preview, cid + '.jpg'), quality=82)
            sheet.append((cid, vi))
    # the painted shop floors' cells: of each class, a trade's first or second by turns (the second M and L of the grocery
    # and the takeout are corner stores), the first where the second is missing
    by = {c['id']: c for c in out_cells}
    gen = {}
    for cls in ('S', 'M', 'L'):
        ids = []
        for k, fam in enumerate(GEN_FAMS):
            for v in (k % 2, 0, 1, 2):
                cid = '%s-%s-%d' % (fam, cls, v)
                if cid in by:
                    ids.append(cid)
                    break
        gen[cls] = [next(k for k, c in enumerate(out_cells) if c['id'] == i) for i in ids]
    half = atlas.resize((AW // 2, AH // 2), Image.LANCZOS)
    mhalf = mask.resize((mAW // 2, mAH // 2), Image.BOX)
    man = {'v': 1, 'img': art_files.write(atlas, 'storefronts', 'storefronts', 'WEBP', quality=85, method=6),
           'imgHalf': art_files.write(half, 'storefronts', 'storefronts-half', 'WEBP', quality=82, method=6),
           'mask': art_files.write(mask, 'storefronts', 'storefronts-mask', 'PNG', optimize=True),
           'maskHalf': art_files.write(mhalf, 'storefronts', 'storefronts-mask-half', 'PNG', optimize=True),
           'w': AW, 'h': AH, 'pad': PAD, 'pxm': PXM, 'hM': H_M,
           'fams': [f[0] for f in F.FAMILIES], 'warm': [int(f[0] in ('restaurant', 'bar', 'cafe', 'bakery', 'boutique', 'venue')) for f in F.FAMILIES],
           'classes': {k: v[0] for k, v in F.CLASSES.items()}, 'cells': out_cells, 'gen': gen}
    gone = art_files.prune('storefronts')
    json.dump(man, open(OUT, 'w'), separators=(',', ':'))
    sz = sum(art_files.size(man[k]) for k in ('img', 'imgHalf', 'mask', 'maskHalf'))
    print('%d cells (%s), %s: %d bytes; art/storefronts: %d bytes (%d pruned)' % (len(out_cells), srcs, OUT, os.path.getsize(OUT), sz, gone))
    if preview and sheet:
        cols = 4
        tw = 380
        rows = []
        for i in range(0, len(sheet), cols):
            ims = [im.resize((tw, int(round(tw * im.height / im.width)))) for _, im in sheet[i:i + cols]]
            rh = max(im.height for im in ims)
            row = Image.new('RGB', (cols * (tw + 6), rh + 18), (255, 255, 255))
            d = ImageDraw.Draw(row)
            for k, im in enumerate(ims):
                row.paste(im, (k * (tw + 6), 18))
                d.text((k * (tw + 6) + 2, 2), sheet[i + k][0], fill=(0, 0, 0))
            rows.append(row)
        for j in range(0, len(rows), 6):
            part = rows[j:j + 6]
            S = Image.new('RGB', (part[0].width, sum(r.height for r in part)), (255, 255, 255))
            yy = 0
            for r in part:
                S.paste(r, (0, yy)); yy += r.height
            S.save(os.path.join(preview, 'sheet-%d.jpg' % (j // 6)), quality=80)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--masks', action='store_true', help='write the edits\' masks beside the frames, then stop')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    if a.masks:
        write_masks(a.force)
        return
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
    bake(a.preview)


if __name__ == '__main__':
    main()
