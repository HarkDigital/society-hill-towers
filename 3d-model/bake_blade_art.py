#!/usr/bin/env python3
"""Bake the blade signs' sheet (the realism round two, R9): the six blanks fetch_blade_art.py made (lidar_cache/
blade_art_raw/<id>.png, transparent) trimmed to their pixels, each scaled to its real size at one density, shelf-packed
into one 512 square RGBA sheet with a phone's 256 square half beside it (art/blades/, art_files.py), and blade_art.json,
which build.py inlines as BLADE_ART.

Per blank the bake finds:
- the body: the sign itself without its bracket, chains or scrolls (the alpha eroded until the thin iron is gone, the
  largest piece grown back), whose real width (BODY_M) sets the blank's scale;
- the plate: the largest centred rectangle of the face's own paint, seeded at the body's middle and grown over the
  pixels within PLATE_TOL of its colour (inside a rim, a gold line or a moulding), inset by PLATE_INSET: where the page
  letters the shop's name;
- the plate's luminance (light letters on a dark face, dark on a light one) and where the blank meets the wall (its
  left edge, always: the prompts stand the wall plate there).

The colour under every clear pixel is bled out from the sign (the page uploads the sheet premultiplied and divides the
coverage back out, as the tree cards do, so no black fringe comes in with the mips either way). Every blank is read
before it is kept: no letters, no wall, no perspective."""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'blade_art_raw')
OUT = os.path.join(HERE, 'blade_art.json')
SHEET = 512
PAD = 6
# id: the body's real width in metres (the disc, the board, the cabinet, the panel), whether it hangs from its bracket
# (the bracket's arm is the blank's top: the page sets that at the mount height), whether it is a lightbox (its face lit
# through), whether its name runs up the panel, and the plate's aspect a name reads best in (width over height)
SHAPES = [
    ('round', 0.75, True, False, False, 1.6),
    ('rect', 0.95, False, False, False, 2.0),
    ('hanging', 0.85, True, False, False, 2.0),
    ('box', 1.00, False, True, False, 2.8),
    ('vertical', 0.55, False, False, True, 0.3),
    ('oval', 0.70, True, False, False, 2.2),
]
PLATE_TOL = 40      # a face pixel's largest channel difference from the face's own colour (sRGB 0 to 255)
PLATE_INSET = 0.06  # the plate's margin inside the face, a share of its width and height each side


def erode(m, k):
    for _ in range(k):
        e = m.copy()
        e[1:, :] &= m[:-1, :]; e[:-1, :] &= m[1:, :]; e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]
        m = e
    return m


def dilate(m, k):
    for _ in range(k):
        e = m.copy()
        e[1:, :] |= m[:-1, :]; e[:-1, :] |= m[1:, :]; e[:, 1:] |= m[:, :-1]; e[:, :-1] |= m[:, 1:]
        m = e
    return m


def components(m):
    """Labels of a boolean array's 4-connected pieces (a breadth-first fill; the arrays here are at most 256 square)."""
    lab = np.zeros(m.shape, np.int32)
    h, w = m.shape
    n = 0
    for y0, x0 in zip(*np.nonzero(m)):
        if lab[y0, x0]:
            continue
        n += 1
        lab[y0, x0] = n
        st = [(y0, x0)]
        while st:
            y, x = st.pop()
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n
                    st.append((yy, xx))
    return lab, n


def flood(m, y0, x0):
    out = np.zeros(m.shape, bool)
    if not m[y0, x0]:
        return out
    h, w = m.shape
    out[y0, x0] = True
    st = [(y0, x0)]
    while st:
        y, x = st.pop()
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not out[yy, xx]:
                out[yy, xx] = True
                st.append((yy, xx))
    return out


def inscribed(region, cy, cx, pref):
    """The rectangle centred at (cy, cx) lying (99%) inside region that holds a name best: the largest over a range of
    aspects, a rectangle's area discounted by how far its aspect is from pref (a round face's square holds less of a
    name than the wider band across it): (y0, x0, y1, x1)."""
    h, w = region.shape
    best, area = None, 0
    for asp in (0.2, 0.25, 0.3, 0.36, 0.43, 0.5, 0.6, 0.7, 0.85, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.3, 2.6, 3.0, 3.5, 4.0):
        lo, hi = 1.0, float(max(h, w))
        while hi - lo > 0.5:
            s = (lo + hi) / 2
            hw, hh = s * asp ** 0.5 / 2, s / asp ** 0.5 / 2
            y0, y1, x0, x1 = int(round(cy - hh)), int(round(cy + hh)), int(round(cx - hw)), int(round(cx + hw))
            if y0 < 0 or x0 < 0 or y1 >= h or x1 >= w or y1 <= y0 or x1 <= x0 or region[y0:y1 + 1, x0:x1 + 1].mean() < 0.99:
                hi = s
            else:
                lo = s
        hw, hh = lo * asp ** 0.5 / 2, lo / asp ** 0.5 / 2
        sc = 4 * hw * hh / (1 + 0.6 * abs(np.log(asp / pref)))
        if sc > area:
            area, best = sc, (cy - hh, cx - hw, cy + hh, cx + hw)
    return best


def analyse(bid, pref):
    im = Image.open(os.path.join(RAW, bid + '.png')).convert('RGBA')
    a = np.asarray(im)[:, :, 3]
    ys, xs = np.nonzero(a > 16)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    px = np.asarray(im).astype(np.float32)
    H, W = px.shape[:2]
    # the body at a quarter's scale: the solid alpha eroded past the iron, the largest piece grown back
    q = 4
    sm = np.asarray(im.resize((max(1, W // q), max(1, H // q)), Image.BOX))[:, :, 3] > 160
    core = erode(sm, 4)
    lab, n = components(core)
    if not n:
        sys.exit(bid + ': no body found')
    big = 1 + int(np.argmax(np.bincount(lab.ravel())[1:]))
    body = dilate(lab == big, 4) & sm
    by, bx = np.nonzero(body)
    bb = [bx.min() * q, by.min() * q, (bx.max() + 1) * q, (by.max() + 1) * q]   # x0, y0, x1, y1 in the trimmed image
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    # the plate: the face's own paint, seeded at the body's middle (a 31 px window's median)
    win = px[int(cy) - 15:int(cy) + 16, int(cx) - 15:int(cx) + 16, :3].reshape(-1, 3)
    ref = np.median(win, axis=0)
    paint = (np.abs(px[:, :, :3] - ref).max(axis=2) < PLATE_TOL) & (px[:, :, 3] > 200)
    paint = np.asarray(Image.fromarray((paint * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5))) > 127   # weathering specks
    face = flood(paint, int(cy), int(cx))
    fy, fx = np.nonzero(face)
    fcy, fcx = (fy.min() + fy.max()) / 2, (fx.min() + fx.max()) / 2
    r = inscribed(face, fcy, fcx, pref)
    iy, ix = (r[2] - r[0]) * PLATE_INSET, (r[3] - r[1]) * PLATE_INSET
    plate = [r[1] + ix, r[0] + iy, r[3] - ix, r[2] - iy]   # x0, y0, x1, y1 in the trimmed image (y down)
    c = ref / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    lum = float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])
    return {'im': im, 'W': W, 'H': H, 'body': bb, 'plate': plate, 'lum': lum, 'ref': [int(v) for v in ref], 'face_px': int(face.sum())}


def shelf(sizes, side):
    """Shelf-pack (w, h) boxes into a side square, tallest first: their (x, y) or None when they do not fit."""
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i][1])
    at = [None] * len(sizes)
    x = y = rowH = 0
    for i in order:
        w, h = sizes[i]
        if w + 2 * PAD > side:
            return None
        if x + w + 2 * PAD > side:
            x, y, rowH = 0, y + rowH, 0
        if y + h + 2 * PAD > side:
            return None
        at[i] = (x + PAD, y + PAD)
        x += w + 2 * PAD
        rowH = max(rowH, h + 2 * PAD)
    return at


def bleed(rgba):
    """The colour under every clear pixel, the sign's own spread outward (premultiplied blurs at falling radii)."""
    arr = np.asarray(rgba).astype(np.float32)
    a = arr[:, :, 3:4] / 255.0
    out = arr[:, :, :3].copy()
    filled = a[:, :, 0] > 0.5
    for rad in (2, 6, 16, 40):
        pm = Image.fromarray(np.clip(np.concatenate([arr[:, :, :3] * a, a * 255], axis=2), 0, 255).astype(np.uint8))
        bl = np.asarray(pm.filter(ImageFilter.GaussianBlur(rad))).astype(np.float32)
        ba = bl[:, :, 3:4] / 255.0
        col = bl[:, :, :3] / np.maximum(ba, 1e-3)
        take = (~filled) & (ba[:, :, 0] > 0.02)
        out[take] = col[take]
        filled |= take
    out[~filled] = arr[:, :, :3][a[:, :, 0] > 0.5].mean(axis=0)
    keep = a[:, :, 0] > 0.0
    out[keep] = arr[:, :, :3][keep]
    return Image.fromarray(np.concatenate([np.clip(out, 0, 255), arr[:, :, 3:4]], axis=2).astype(np.uint8))


def main():
    found = {s[0]: analyse(s[0], s[5]) for s in SHAPES if os.path.exists(os.path.join(RAW, s[0] + '.png'))}
    missing = [bid for bid, *_ in SHAPES if bid not in found]
    if missing:
        sys.exit('missing blanks: ' + ', '.join(missing) + ' (run fetch_blade_art.py)')
    # the one density every blank is scaled to: the largest that packs
    lo, hi = 40.0, 600.0
    for _ in range(40):
        pxm = (lo + hi) / 2
        sizes = []
        for bid, bodyM, *_ in SHAPES:
            f = found[bid]; k = pxm * bodyM / (f['body'][2] - f['body'][0])
            sizes.append((max(4, int(round(f['W'] * k))), max(4, int(round(f['H'] * k)))))
        if shelf(sizes, SHEET):
            lo = pxm
        else:
            hi = pxm
    pxm = int(lo)
    sizes, ks = [], []
    for bid, bodyM, *_ in SHAPES:
        f = found[bid]; k = pxm * bodyM / (f['body'][2] - f['body'][0])
        ks.append(k); sizes.append((max(4, int(round(f['W'] * k))), max(4, int(round(f['H'] * k)))))
    at = shelf(sizes, SHEET)
    sheet = Image.new('RGBA', (SHEET, SHEET), (0, 0, 0, 0))
    shapes = []
    for i, (bid, bodyM, hang, lightbox, vertical, _pref) in enumerate(SHAPES):
        f, (w, h), (x, y), k = found[bid], sizes[i], at[i], ks[i]
        small = f['im'].convert('RGBa').resize((w, h), Image.LANCZOS).convert('RGBA')
        sheet.paste(small, (x, y))
        sx, sy = w / f['W'], h / f['H']
        fr = lambda b: [round(b[0] * sx / w, 4), round(1 - b[3] * sy / h, 4), round(b[2] * sx / w, 4), round(1 - b[1] * sy / h, 4)]   # fractions of the cell, y up
        shapes.append({'id': bid, 'rect': [round(x / SHEET, 5), round(1 - (y + h) / SHEET, 5), round(w / SHEET, 5), round(h / SHEET, 5)],
                       'size': [round(w / pxm, 3), round(h / pxm, 3)], 'body': [round(float(v), 4) for v in fr(f['body'])], 'plate': [round(float(v), 4) for v in fr(f['plate'])],
                       'lum': round(f['lum'], 4), 'face': f['ref'], 'hang': hang, 'lightbox': lightbox, 'vertical': vertical})
        print('%-8s %3dx%-3d at %3d,%-3d  %.2f x %.2f m  plate %s  lum %.3f' % (bid, w, h, x, y, w / pxm, h / pxm, shapes[-1]['plate'], f['lum']))
    sheet = bleed(sheet)
    half = sheet.convert('RGBa').resize((SHEET // 2, SHEET // 2), Image.LANCZOS).convert('RGBA')
    gen = {}
    for bid, *_ in SHAPES:
        j = os.path.join(RAW, bid + '.json')
        if os.path.exists(j):
            m = json.load(open(j)).get('model')
            gen[m] = gen.get(m, 0) + 1
    man = {'v': 1, 'img': art_files.write(sheet, 'blades', 'blades', 'WEBP', quality=90, method=6, exact=True),
           'imgHalf': art_files.write(half, 'blades', 'blades-half', 'WEBP', quality=88, method=6, exact=True),
           'w': SHEET, 'h': SHEET, 'pxm': pxm, 'shapes': shapes, 'gen': gen}
    gone = art_files.prune('blades')
    with open(OUT, 'w') as fh:
        json.dump(man, fh, separators=(',', ':'))
    print('%d px/m, %s %d B, %s %d B, pruned %d; wrote %s' % (pxm, man['img'], art_files.size(man['img']), man['imgHalf'], art_files.size(man['imgHalf']), gone, OUT))


if __name__ == '__main__':
    main()
