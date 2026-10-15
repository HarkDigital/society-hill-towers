#!/usr/bin/env python3
"""Bake One and Two Liberty Place's near detail (Round 195) from fetch_liberty_art.py's pictures into liberty_art.json and
its images under art/liberty/ (art_files.write: each named by its content's hash, with a -half copy a phone takes).

- base: the granite base's two elevations (the lobby bays and the plainer wall), each 12 m by 12 m, side by side in one
  1024 by 512 atlas (Round 195's review: the 2048 by 1024 cost a computer 11.2 MB with its mips for a base drawn within a
  kilometre, and the phone's 1024 by 512 already read well at the street; a phone now takes 512 by 256). Alpha is the stone
  and the frames (255) against the glass (0), which the page reads as the mask: polished granite where it is 1, a reflective
  pane over a dim interior that lights after dark (the lobby cell only) where it is 0.
- glazing: the crowns' sloped glazing, a 3 m tile, 256 square: two ribs parallel to the eave a course (1.5 m) and a faint
  mullion down the slope every 1.5 m, nothing else (Round 195's review: the first bake's caps both ways at full strength laid
  a white square grid over the slopes and read as solar panels; the photographs, the Library of Congress's Highsmith view
  above all, show light glass slopes with thin silver ribs along them). Each rib's cross-section, colour and gaskets are the
  generated photograph's own horizontal caps (fetch_liberty_art.py's 'glazing'), their profile taken by the median along the
  cap between the crossings and drawn at 7 cm, a third of its contrast taken out; the mullions are its vertical caps at 5 cm
  and a fifth of their cover. Alpha is the ribs' cover over the glass (0); the page lays the tile a few centimetres over the
  crown's glass, blended.
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
GLAZE_M = 3.0              # the glazing tile, metres a side (two 1.5 m courses of ribs, two faint mullions)
GLAZE_PX = 256             # its pixels a side
RIB_M, MUL_M = 0.07, 0.05  # a rib's and a mullion's width drawn, metres (the photograph's caps with their gaskets were 13 cm)
RIB_FLAT = 0.33            # the share of a rib's contrast taken out (its colour toward its own mean)
MUL_COVER = 0.2            # a mullion's alpha against a rib's


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


def runs(low):
    """The runs where `low` holds: (first, last) index pairs."""
    out, i, n = [], 0, len(low)
    while i < n:
        if low[i]:
            j = i
            while j < n and low[j]:
                j += 1
            out.append((i, j - 1))
            i = j
        else:
            i += 1
    return out


def cap_profile(a, green, axis):
    """The caps along one axis as one cross-section: for each cap (a run of rows, axis 0, or columns, axis 1, under half
    green) a few pixels either side, each line's median colour and cover along the cap with the crossing caps left out,
    the caps' profiles averaged. Returns (rgb [n, 3], cover [n])."""
    if axis == 1:
        a, green = a.transpose(1, 0, 2), green.T
    caps = runs(green.mean(1) < 0.5)
    cross = green.mean(0) < 0.5                        # the crossing caps' columns
    keep = ~np.convolve(cross, np.ones(9), 'same').astype(bool)
    if len(caps) < 2 or keep.sum() < 50:
        sys.exit('glazing: found %d caps along axis %d' % (len(caps), axis))
    pad, prof, cov = 3, [], []
    w = max(b - a0 for a0, b in caps) + 1 + 2 * pad
    for a0, b in caps:
        r0 = a0 - pad
        if r0 < 0 or r0 + w > a.shape[0]:
            continue
        rows = a[r0:r0 + w][:, keep]
        g = green[r0:r0 + w][:, keep]
        f = 1.0 - g.mean(1)
        rgb = np.array([np.median(rows[i][~g[i]], 0) if f[i] > 0.02 else np.zeros(3) for i in range(w)])
        prof.append(rgb)
        cov.append(f)
    return np.mean(prof, 0), np.mean(cov, 0)


def draw_line(n, centre, width_px, rgb, cover):
    """A cap's profile resampled to width_px pixels about `centre` on an axis of n pixels: (rgb [n, 3], alpha [n])."""
    src = np.linspace(0, 1, len(cover))
    out_rgb, out_a = np.zeros((n, 3)), np.zeros(n)
    for i in range(n):
        for off in (-n, 0, n):                          # the tile wraps
            t = (i + 0.5 - centre - off) / width_px + 0.5
            if 0.0 <= t <= 1.0:
                out_a[i] = np.interp(t, src, cover)
                out_rgb[i] = [np.interp(t, src, rgb[:, c]) for c in range(3)]
    return out_rgb, out_a


def glazing():
    a = np.asarray(Image.open(os.path.join(RAW, 'glazing.png')).convert('RGB')).astype(np.float32)
    a = despill(a, key(a))
    green = key(a)
    rib_rgb, rib_cov = cap_profile(a, green, 0)        # the horizontal caps: the ribs along the eave
    mul_rgb, mul_cov = cap_profile(a, green, 1)        # the vertical caps: the mullions down the slope
    # a third of each cap's contrast out (toward its own cover-weighted mean)
    for rgb, cov in ((rib_rgb, rib_cov), (mul_rgb, mul_cov)):
        m = (rgb * cov[:, None]).sum(0) / max(cov.sum(), 1e-6)
        rgb[:] = rgb + (m - rgb) * RIB_FLAT * (cov[:, None] > 0.02)
    n, pm = GLAZE_PX, GLAZE_PX / GLAZE_M
    # the ribs at a quarter and three quarters of the tile (never cut by its edge), the mullions the same across
    rr, ra = np.zeros((n, 3)), np.zeros(n)
    mr, ma = np.zeros((n, 3)), np.zeros(n)
    for c in (n * 0.25, n * 0.75):
        r1, a1 = draw_line(n, c, RIB_M * pm, rib_rgb, rib_cov)
        sel = a1 > ra
        rr[sel], ra[sel] = r1[sel], a1[sel]
        r2, a2 = draw_line(n, c, MUL_M * pm, mul_rgb, mul_cov)
        sel = a2 > ma
        mr[sel], ma[sel] = r2[sel], a2[sel]
    ma *= MUL_COVER
    # the image: rows are v (down the slope), columns u (along the eave); a rib over a mullion where they cross
    A_rib = ra[:, None] * np.ones((1, n))
    A_mul = np.ones((n, 1)) * ma[None, :]
    alpha = A_rib + A_mul * (1 - A_rib)
    rgb = (rr[:, None, :] * A_rib[..., None] + mr[None, :, :] * (A_mul * (1 - A_rib))[..., None]) / np.maximum(alpha, 1e-6)[..., None]
    rgba = np.dstack([np.clip(rgb * alpha[..., None], 0, 255), alpha * 255.0]).round().astype(np.uint8)   # premultiplied
    caps = (rgb * alpha[..., None]).reshape(-1, 3).sum(0) / max(alpha.sum(), 1e-6)
    return rgba, {'caps': [round(float(v), 1) for v in caps], 'cover': round(float(alpha.mean()), 4),
                  'ribs': {'m': RIB_M, 'course': GLAZE_M / 2}, 'mullions': {'m': MUL_M, 'cover': MUL_COVER}}


def resize_pm(im, size):
    """A premultiplied RGBA image resized channel by channel (Pillow's own RGBA resize premultiplies again and divides
    back out, which leaves a cap's full colour on the half-covered texels at its edge)."""
    return Image.merge('RGBA', [c.resize(size, Image.LANCZOS) for c in im.split()])


def main():
    lobby, ml = base_cell('base-lobby')
    line = reveal_row(np.asarray(Image.open(os.path.join(RAW, 'base-lobby.png')).convert('RGB').resize((1024, 1024), Image.LANCZOS)).astype(np.float32))
    wall, mw = base_cell('base-wall', line)   # its fascia's reveal on the lobby's row
    ml['reveal'] = mw['reveal'] = round(1 - line / 1024, 4)
    atlas = Image.fromarray(np.concatenate([lobby, wall], axis=1))
    gz, mg = glazing()
    gim = Image.fromarray(gz)
    kind = 'liberty'
    atlas = resize_pm(atlas, (1024, 512))
    base = art_files.write(atlas, kind, 'base', 'WEBP', quality=90, method=6)
    base_h = art_files.write(resize_pm(atlas, (512, 256)), kind, 'base-half', 'WEBP', quality=88, method=6)
    glz = art_files.write(gim, kind, 'glazing', 'WEBP', quality=92, method=6)
    glz_h = art_files.write(resize_pm(gim, (GLAZE_PX // 2, GLAZE_PX // 2)), kind, 'glazing-half', 'WEBP', quality=90, method=6)
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
    print('pruned %d; lobby glass %.3f, wall glass %.3f, glazing ribs %.3f of the tile' % (gone, ml['glass'], mw['glass'], mg['cover']))


if __name__ == '__main__':
    main()
