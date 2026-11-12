#!/usr/bin/env python3
"""Bake the walking people's atlases (Round 227): the character sheets fetch_people_art.py made (lidar_cache/
people_art_raw/<id>.png, six pictures of one person in a row on transparency) cut into their six poses and packed into
ONE atlas for every figure, with a phone's half and a computer's sharp copy beside it (art/people/, art_files.py), and
people_art.json, which build.py inlines as PEOPLE_ART.

Per sheet:
- the six poses are the six largest connected pieces of its alpha (grown a few pixels first, so a strap or a wisp of
  hair stays with its owner), left to right in fetch_people_art.POSES' order; a sheet whose figures touch falls back to
  CUTS (the figure's own six column ranges) and then to the emptiest columns near the sixths;
- a picture that came out left-for-right (a shoulder bag on the other shoulder from behind) is mirrored: FLIP;
- the faint outer haze of the alpha goes and the colour of every soft edge pixel is taken from the solid pixels beside
  it, so nothing of whatever the model matted the figure against rides in on the edge;
- every pose is brought to ONE scale a figure: the passing frame of each view stands the figure's full height, the
  contact frame as much shorter as the sheet drew it (never more than 4%: a real step's dip), the lowest shoe on the
  cell's bottom edge and the figure's own vertical axis (the centre of its mass) on the cell's centre line, because
  the page turns the card about that line and an off-centre figure would swim. A full stride is wider than half a
  figure's height, so a figure fills only FILL of its cell's height (0.8 to 0.9): the manifest's `tall` is the height
  the WHOLE cell stands for, the person's own height over that fill.

The sharp atlas is drawn first, each pose resampled once from its sheet in premultiplied floating point; the full and
half atlases are that picture reduced by exactly 2 and 4, so the three share one layout to the pixel (every cell edge
is a multiple of 16 px in the full atlas, so the mips stay on the grid too). Cells are CELL_W by CELL_H with GUTTER
clear pixels on every side. Then, per atlas, the figures' colour is bled out under the clear pixels: the page uploads
the picture premultiplied and builds its mips from that (handoff's gotcha 16, the tree cards' path), and a lossy WebP
smears chroma across an edge, so the colour beyond the edge must be the figure's own, never black or white.

`cells[view][frame]` is the INNER rect [x, y, w, h] in full-atlas pixels, y from the top; "side" faces the picture's
right and the page mirrors it. The atlases are not powers of two: WebGL 2 mips them as they are, and three.js rescales
them on WebGL 1.

Usage: python3 bake_people_art.py [--contact out.png]   (PEOPLE_ART_RAW moves the raw folder, as in the fetch)"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
import art_files
from fetch_people_art import FIGURES, POSES, MID_POSES, RAW

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'people_art.json')
VIEWS = ['front', 'back', 'side']
FRAMES = 4                      # one step: 0 the contact (legs apart), 1 the down, 2 the passing (legs together), 3 the up
# (Round 237: the down and the up are the in-between sheet's, <id>-mid.png; before it a view was two frames, a stride and
# a stand, and the walk read as a flip between them)
CELL_W, CELL_H, GUTTER = 128, 256, 8     # the full atlas; the half is 0.5 of these and the sharp 2.0
SHARP = 2
DIP_MAX = 0.04                  # a contact frame stands at most this much shorter than its view's passing frame
QUALITY = 86                    # lossy colour; the alpha is kept lossless (alpha_quality 100) so the edge stays clean
# figure id: the (view, frame) pictures to mirror. p01's tote hangs from her right shoulder in five pictures and from
# her left in the back contact
FLIP = {'p01': [('back', 0), ('back', 1)]}
# figure id: six (x0, x1) column ranges in sheet pixels, for a sheet whose figures touch (none of the first three do)
CUTS = {}


def components(m):
    """Labels of a boolean array's 4-connected pieces and their count (a depth-first fill; the arrays are 768 by 512)."""
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


def dilate(m, k):
    for _ in range(k):
        e = m.copy()
        e[1:, :] |= m[:-1, :]; e[:-1, :] |= m[1:, :]; e[:, 1:] |= m[:, :-1]; e[:, :-1] |= m[:, 1:]
        m = e
    return m


def slice_sheet(fid, a, POSES=POSES):
    """The sheet's six poses as boolean masks at the sheet's size, left to right, and how they were found."""
    al = a[..., 3]
    H, W = al.shape
    small = al[::2, ::2] > 0.16
    grown = dilate(small, 2)                       # 4 sheet pixels: a detached strap or lock of hair joins its figure
    lab, n = components(grown)
    area = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    big = [i + 1 for i in np.argsort(-area)[:len(POSES)]]
    tall = {i: np.ptp(np.nonzero((lab == i).any(1))[0]) + 1 for i in big}
    ok = len(big) == len(POSES) and min(area[i - 1] for i in big) > 0.3 * area.max() and min(tall.values()) > 0.75 * max(tall.values())
    if ok:
        big.sort(key=lambda i: np.nonzero((lab == i).any(0))[0].mean())
        masks = []
        for i in big:
            m = np.repeat(np.repeat(lab == i, 2, 0), 2, 1)[:H, :W]
            masks.append(m)
        return masks, 'alpha pieces'
    if fid in CUTS:
        cuts, how = CUTS[fid], 'CUTS'
    else:   # the emptiest column within a twelfth of the sheet of each sixth
        col = (al > 0.16).sum(0)
        xs = [0]
        for k in range(1, len(POSES)):
            c, r = W * k // len(POSES), W // (2 * len(POSES))
            xs.append(c - r + int(np.argmin(col[c - r:c + r])))
        xs.append(W)
        cuts, how = list(zip(xs[:-1], xs[1:])), 'emptiest columns'
    if len(cuts) != len(POSES):
        sys.exit('%s: CUTS wants %d column ranges' % (fid, len(POSES)))
    masks = []
    for x0, x1 in cuts:
        m = np.zeros((H, W), bool)
        m[:, x0:x1] = True
        if not (al[:, x0:x1] > 0.5).any():
            sys.exit('%s: nothing between columns %d and %d' % (fid, x0, x1))
        masks.append(m)
    return masks, how


def spread(rgb, w, passes):
    """Run the colour of the pixels w marks out into the others, a four-neighbour average a pass (the tree bake's bleed).
    No wrap at the borders. Returns the colour and the mask of what now has one."""
    rgb = rgb * w[..., None]
    w = w.astype(np.float32)
    for _ in range(passes):
        if w.min() > 0:
            break
        acc = np.zeros_like(rgb); n = np.zeros_like(w)
        src = rgb * w[..., None]
        acc[1:] += src[:-1]; n[1:] += w[:-1]
        acc[:-1] += src[1:]; n[:-1] += w[1:]
        acc[:, 1:] += src[:, :-1]; n[:, 1:] += w[:, :-1]
        acc[:, :-1] += src[:, 1:]; n[:, :-1] += w[:, 1:]
        fill = (w == 0) & (n > 0)
        rgb[fill] = acc[fill] / n[fill][:, None]
        w = np.where(fill, 1.0, w)
    return rgb, w > 0


def cut_pose(a, mask):
    """One pose off its sheet: cropped to what it shows, the outer haze gone, every soft edge pixel in the colour of the
    solid pixels beside it. Straight (not premultiplied) float RGBA."""
    al = np.where(mask, a[..., 3], 0.0)
    al = np.clip((al - 0.06) / 0.90, 0, 1)         # a faint outer haze goes; a solid pixel stays solid
    ys, xs = np.nonzero(al > 0.5)
    y0, y1, x0, x1 = max(0, ys.min() - 3), ys.max() + 4, max(0, xs.min() - 3), xs.max() + 4
    al = al[y0:y1, x0:x1]
    rgb = a[y0:y1, x0:x1, :3].copy()
    solid = al > 0.92
    bled, got = spread(rgb, solid, 6)
    soft = ~solid & got
    rgb[soft] = bled[soft]
    al = np.where(got, al, 0.0)                    # nothing further than six pixels from a solid one is the figure
    return np.dstack([rgb, al])


def measure(p):
    """A pose's box of solid pixels (x0, y0, x1, y1, exclusive) and its vertical axis: the centre of its mass."""
    al = p[..., 3]
    ys, xs = np.nonzero(al > 0.5)
    col = al.sum(0)
    axis = float((col * (np.arange(al.shape[1]) + 0.5)).sum() / col.sum())
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1), axis


def feet_apart(pose):
    """How far apart the feet stand, in figure heights: the width of the solid pixels in the pose's lowest eighth."""
    p, box = pose[0], pose[1]
    al = p[..., 3]
    h = box[3] - box[1]
    xs = np.nonzero((al[box[3] - max(1, h // 8):box[3]] > 0.5).any(0))[0]
    return float(xs.max() - xs.min() + 1) / h


def resample(p, k):
    """The pose scaled by k, in premultiplied floating point (a channel at a time: no 8-bit premultiplied step)."""
    h, w = p.shape[:2]
    tw, th = max(1, int(round(w * k))), max(1, int(round(h * k)))
    pm = np.dstack([p[..., :3] * p[..., 3:4], p[..., 3:4]]).astype(np.float32)
    out = np.dstack([np.asarray(Image.fromarray(np.ascontiguousarray(pm[..., c])).resize((tw, th), Image.LANCZOS)) for c in range(4)])
    out[..., 3] = np.clip(out[..., 3], 0, 1)
    return out, tw / w, th / h


def reduce2(pm):
    """A premultiplied float picture at half its size (Lanczos: three source pixels a side, inside the gutter)."""
    h, w = pm.shape[:2]
    out = np.dstack([np.asarray(Image.fromarray(np.ascontiguousarray(pm[..., c])).resize((w // 2, h // 2), Image.LANCZOS)) for c in range(4)])
    out[..., 3] = np.clip(out[..., 3], 0, 1)
    return out


def finish(pm, gutter, rects):
    """A premultiplied float atlas as the 8-bit straight-alpha picture that ships: the alpha's last faint ringing gone
    and nothing left outside the cells (rects, in this picture's pixels: a reduction rings a few percent of a shoe's
    sole over the bottom edge it stands on), the colour divided back out and bled under the clear pixels as far as the
    gutter and a little more."""
    inside = np.zeros(pm.shape[:2], bool)
    for x, y, w, h in rects:
        inside[y:y + h, x:x + w] = True
    al = np.where(inside, np.clip((pm[..., 3] - 0.02) / 0.97, 0, 1), 0.0)
    have = pm[..., 3] > 0.2                         # a pixel covered enough for its own colour to be trusted
    rgb = np.where(have[..., None], pm[..., :3] / np.maximum(pm[..., 3:4], 1e-4), 0.0)
    rgb, _ = spread(np.clip(rgb, 0, 1), have, gutter + 6)
    out = np.dstack([np.clip(rgb, 0, 1), al])
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8))


def layout(n):
    """Where n figures' cells go: each figure a row of views times frames, the figures in `per` columns of such rows, chosen for
    the smallest longer side. Returns per, the full atlas's size and a function from (figure, view, frame) to its
    inner rect in full-atlas pixels."""
    pw, ph = CELL_W + 2 * GUTTER, CELL_H + 2 * GUTTER
    best = None
    for per in range(1, n + 1):
        rows = -(-n // per)
        w, h = per * len(VIEWS) * FRAMES * pw, rows * ph
        if best is None or (max(w, h), w * h) < best[0]:
            best = ((max(w, h), w * h), per, w, h)
    _, per, w, h = best

    def rect(i, view, frame):
        col = (i % per) * len(VIEWS) * FRAMES + VIEWS.index(view) * FRAMES + frame
        return [col * pw + GUTTER, (i // per) * ph + GUTTER, CELL_W, CELL_H]
    return per, w, h, rect


def bake_figure(fid, tall):
    path = os.path.join(RAW, fid + '.png')
    if not os.path.exists(path):
        sys.exit('missing sheet %s (run fetch_people_art.py)' % path)
    mid = os.path.join(RAW, fid + '-mid.png')
    if not os.path.exists(mid):
        sys.exit('missing in-between sheet %s (run fetch_people_art.py --mid)' % mid)
    poses, how = {}, []
    for sheet, order in ((path, POSES), (mid, MID_POSES)):
        a = np.asarray(Image.open(sheet).convert('RGBA'), np.float32) / 255.0
        masks, h = slice_sheet(fid, a, order)
        how.append(h)
        for (view, frame), m in zip(order, masks):
            p = cut_pose(a, m)
            if (view, frame) in FLIP.get(fid, ()):
                p = p[:, ::-1].copy()
            poses[(view, frame)] = (p,) + measure(p)
    how = ' + '.join(how)
    # the in-between sheet is another photograph: it came back 5 to 15% lighter than the first (measured over the solid
    # pixels), which flickers as the frames alternate. Each view's two in-betweens take a gain a channel, in linear
    # light, that brings their mean to the mean of the view's contact and passing
    gains = {}
    for view in VIEWS:
        def mean(fs):
            px = np.concatenate([poses[(view, f)][0][..., :3][poses[(view, f)][0][..., 3] > 0.9] for f in fs])
            return (px ** 2.2).mean(0)
        g = mean((0, 2)) / np.maximum(mean((1, 3)), 1e-4)
        gains[view] = [round(float(v), 3) for v in g]
        for f in (1, 3):
            p, box, axis = poses[(view, f)]
            p = p.copy()
            p[..., :3] = np.clip(p[..., :3] ** 2.2 * g, 0, 1) ** (1 / 2.2)
            poses[(view, f)] = (p, box, axis)
    # the in-betweens by what they show, not by what they were asked to be: of a profile's two, the one with its feet
    # further apart is the down (just after the contact) and the narrower the up (just after the passing). The model
    # draws a profile's up wider than asked as often as not, and played the other way round the legs would close and
    # open again inside one step
    # (the profile only: from the front or behind the feet stand side by side at every moment, and the lowest eighth's
    # width says nothing about the stride)
    swapped = []
    for view in ('side',):
        if feet_apart(poses[(view, 3)]) > feet_apart(poses[(view, 1)]):
            poses[(view, 1)], poses[(view, 3)] = poses[(view, 3)], poses[(view, 1)]
            swapped.append(view)
    # one scale a figure: each view's passing frame at the full height, its contact frame at the height the sheet drew
    # beside it (the dip, bounded), and the whole figure shrunk until its widest pose fits the cell about its axis
    SH, SW = CELL_H * SHARP, CELL_W * SHARP
    # the in-between sheet is its own photograph at its own scale: its two frames of a view against the taller of the two
    rel = {}
    hgt = lambda k: poses[k][1][3] - poses[k][1][1]
    for view in VIEWS:
        rel[(view, 2)] = 1.0
        rel[(view, 0)] = float(min(1.0, max(1.0 - DIP_MAX, hgt((view, 0)) / hgt((view, 2)))))
        top = max(hgt((view, 1)), hgt((view, 3)))
        for f in (1, 3):
            rel[(view, f)] = float(min(1.0, max(1.0 - DIP_MAX, hgt((view, f)) / top)))
    reach = 0.0   # the widest half extent about the axis, in figure heights
    for key, (p, box, axis) in poses.items():
        h = box[3] - box[1]
        reach = max(reach, rel[key] * max(axis - box[0], box[2] - axis) / h)
    fill = min(1.0, (SW / 2 - 3) / (reach * SH))    # three sharp pixels to spare each side: no stride is cut by its rect
    cells = {}
    for key, (p, box, axis) in poses.items():
        k = fill * rel[key] * SH / (box[3] - box[1])
        r, kx, ky = resample(p, k)
        cell = np.zeros((SH, SW, 4), np.float32)
        ox = int(round(SW / 2 - axis * kx))
        oy = SH - int(round(box[3] * ky))            # the lowest solid row on the cell's bottom edge
        ys0, xs0 = max(0, -oy), max(0, -ox)
        ys1, xs1 = min(r.shape[0], SH - oy), min(r.shape[1], SW - ox)
        cell[oy + ys0:oy + ys1, ox + xs0:ox + xs1] = r[ys0:ys1, xs0:xs1]
        cells[key] = cell
    keys = [(v, f) for v in VIEWS for f in range(FRAMES)]
    info = {'how': how, 'fill': fill, 'src_h': [hgt(k) for k in keys], 'rel': [round(rel[k], 4) for k in keys],
            'reach': reach, 'gains': gains, 'spread': [round(feet_apart(poses[k]), 3) for k in keys], 'swapped': swapped}
    return cells, round(tall / fill, 3), info


def contact(path, man):
    """The review sheet, from the files as they ship: a band a figure. Left, the sharp cells on mid grey, each view's two
    frames side by side. Right, the full cells on brick red, night blue and mid grey, and the half cells on all three."""
    GROUNDS = {'grey': (128, 128, 128), 'brick': (142, 64, 50), 'night': (16, 22, 44)}
    at = man['atlas']
    full = Image.open(os.path.join(HERE, at['img'])).convert('RGBA')
    half = Image.open(os.path.join(HERE, at['imgHalf'])).convert('RGBA')
    sharp = Image.open(os.path.join(HERE, at['imgSharp'])).convert('RGBA')
    LBL = 18
    N = len(VIEWS) * FRAMES
    bandH = CELL_H * SHARP + LBL
    Wd = N * CELL_W * SHARP + 12 * CELL_W + 40
    sheet = Image.new('RGB', (Wd, bandH * len(man['figures'])), (40, 40, 40))
    d = ImageDraw.Draw(sheet)

    def strip(src, s, fig, ground, x, y):
        w, h = int(CELL_W * s), int(CELL_H * s)
        bg = Image.new('RGBA', (N * w, h), GROUNDS[ground] + (255,))
        i = 0
        for cv in fig['cells']:
            for c in cv:
                bg.alpha_composite(src.crop((int(c[0] * s), int(c[1] * s), int((c[0] + c[2]) * s), int((c[1] + c[3]) * s))), (i * w, 0))
                i += 1
        sheet.paste(bg.convert('RGB'), (x, y))

    for n, fig in enumerate(man['figures']):
        y = n * bandH
        d.text((4, y + 3), '%s  tall %.2f m a cell  sharp cells %dx%d: each view contact, down, passing, up'
               % (fig['id'], fig['tall'], CELL_W * SHARP, CELL_H * SHARP), fill=(230, 230, 230))
        strip(sharp, SHARP, fig, 'grey', 0, y + LBL)
        x = N * CELL_W * SHARP + 20
        d.text((x, y + 3), 'full cells %dx%d on brick and night; below on grey, and the half cells' % (CELL_W, CELL_H), fill=(230, 230, 230))
        strip(full, 1, fig, 'brick', x, y + LBL)
        strip(full, 1, fig, 'night', x + N * CELL_W + 20, y + LBL)
        strip(full, 1, fig, 'grey', x, y + LBL + CELL_H)
        hx = x + N * CELL_W + 20
        strip(half, 0.5, fig, 'grey', hx, y + LBL + CELL_H)
        strip(half, 0.5, fig, 'brick', hx + N // 2 * CELL_W, y + LBL + CELL_H)
        strip(half, 0.5, fig, 'night', hx, y + LBL + CELL_H + CELL_H // 2)
    sheet.save(path)
    return sheet.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contact', default='', help='also write the review sheet to this PNG')
    a = ap.parse_args()
    if len({f[0] for f in FIGURES}) != len(FIGURES):
        sys.exit('two figures share an id')
    per, W, H, rect = layout(len(FIGURES))
    sharp = np.zeros((H * SHARP, W * SHARP, 4), np.float32)   # premultiplied
    figures = []
    for i, (fid, who, tall, season) in enumerate(FIGURES):
        cells, cell_tall, info = bake_figure(fid, tall)
        for (view, frame), cell in cells.items():
            x, y, w, h = [v * SHARP for v in rect(i, view, frame)]
            sharp[y:y + h, x:x + w] = cell
        figures.append({'id': fid, 'tall': cell_tall, 'season': season,
                        'cells': [[rect(i, view, frame) for frame in range(FRAMES)] for view in VIEWS]})
        print('%s  cut by %s  %.2f m, fills %.3f of the cell, so the cell stands %.3f m  sheet heights %s  frame heights %s  widest reach %.3f\n'
              '     feet apart (figure heights, front/back/side by frame) %s  in-betweens swapped %s  their colour gains %s'
              % (fid, info['how'], tall, info['fill'], cell_tall, info['src_h'], info['rel'], info['reach'], info['spread'], info['swapped'] or 'none', info['gains']))
    full = reduce2(sharp)
    half = reduce2(full)
    kw = dict(quality=QUALITY, method=6, alpha_quality=100, exact=True)
    at = lambda s: [[int(v * s) for v in r] for f in figures for view in f['cells'] for r in view]   # every cell's rect at a copy's scale
    man = {'v': 1, 'frames': FRAMES, 'views': VIEWS,
           'atlas': {'img': art_files.write(finish(full, GUTTER, at(1)), 'people', 'people', 'WEBP', **kw),
                     'imgHalf': art_files.write(finish(half, GUTTER // 2, at(0.5)), 'people', 'people-half', 'WEBP', **kw),
                     'imgSharp': art_files.write(finish(sharp, GUTTER * SHARP, at(SHARP)), 'people', 'people-sharp', 'WEBP', **kw),
                     'w': W, 'h': H},
           'figures': figures}
    gone = art_files.prune('people')
    with open(OUT + '.tmp', 'w') as f:
        json.dump(man, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    gpu = lambda s: int(W * s) * int(H * s) * 4 * 4 // 3
    for key, s in (('img', 1), ('imgHalf', 0.5), ('imgSharp', SHARP)):
        print('%-8s %-44s %4dx%-4d %8d B on disk, %5.2f MB on the GPU with its mips' % (key, man['atlas'][key], W * s, H * s, art_files.size(man['atlas'][key]), gpu(s) / 1e6))
    print('%d figures, %d to a row of the atlas, pruned %d; wrote %s' % (len(figures), per, gone, OUT))
    if a.contact:
        print('contact sheet %s %dx%d' % ((a.contact,) + contact(a.contact, man)))


if __name__ == '__main__':
    main()
