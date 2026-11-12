#!/usr/bin/env python3
"""Bake the walking people's atlases (Round 227; Round 242: eight pictures a step, thirty figures, one atlas a wardrobe).
The strips fetch_people_art.py made (lidar_cache/people_art_raw/<id>-<view>.png, eight pictures of one person in a row,
the eight moments of one step, on transparency) are cut into their pictures and packed into ONE atlas a WARDROBE (cold,
cool, warm) with a phone's half beside it (art/people/, art_files.py), and people_art.json, which build.py inlines as
PEOPLE_ART. The page loads the one wardrobe the temperature asks for.

Per strip:
- the eight pictures are the eight largest connected pieces of its alpha (grown a few pixels first, so a strap or a wisp
  of hair stays with its owner), left to right; a strip whose figures touch falls back to the emptiest columns near the
  eighths. A strip that came back opaque is keyed on its chroma green first (chroma);
- the faint outer haze of the alpha goes and the colour of every soft edge pixel is taken from the solid pixels beside
  it, so nothing of whatever the model matted the figure against rides in on the edge;
- every picture of a view is brought to ONE scale, the strip's own: the strip is one photograph at one scale, so the view's
  tallest picture stands the figure's full height and the others as the strip drew them beside it (a step's dip is in the
  picture, bounded at DIP_MAX against a picture drawn smaller); the lowest shoe on the cell's bottom edge;
- the picture is placed by its BODY: the centre of the head and the trunk (the solid pixels between BODY[0] and BODY[1] of
  its height from the top) on the cell's centre line, so the walker's trunk glides on at an even pace while its legs and
  arms move about it. Round 227 placed each picture by its whole mass, so a stride's legs pulled the body back and forth
  across the card, a few centimetres each picture: part of what read as disjointed. The page turns the card about the
  centre line, and the body on it does not swim. A full stride is wider than half a figure's height, so a figure fills
  only FILL of its cell's height: the manifest's `tall` is the height the WHOLE cell stands for, the person's own height
  over that fill.

The full atlas is drawn first at twice its size, each picture resampled once from its strip in premultiplied floating
point, and reduced by exactly 2, and the half by 2 again, so the two share one layout to the pixel (every cell edge is a
multiple of 16 px in the full atlas, so the mips stay on the grid too). Cells are CELL_W by CELL_H with GUTTER clear
pixels on every side. Then, per atlas, the figures' colour is bled out under the clear pixels: the page uploads the
picture premultiplied and builds its mips from that (handoff's gotcha 16, the tree cards' path), and a lossy WebP smears
chroma across an edge, so the colour beyond the edge must be the figure's own, never black or white. There is no sharp
atlas since Round 242: the strips' figures stand about 440 px tall, which the full cell's 256 px already holds.

`cells[view][frame]` is the INNER rect [x, y, w, h] in full-atlas pixels, y from the top; "side" faces the picture's
right and the page mirrors it. The atlases are not powers of two: WebGL 2 mips them as they are, and three.js rescales
them on WebGL 1.

Usage: python3 bake_people_art.py [--contact out.png]   (PEOPLE_ART_RAW moves the raw folder, as in the fetch; the
contact sheet is written once a wardrobe, <out>-<wardrobe>.png)"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
import art_files
from fetch_people_art import FIGURES, FRAMES, WARDROBES, RAW, raw_path

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'people_art.json')
VIEWS = ['front', 'back', 'side']   # the manifest's (and the page's) order
CELL_W, CELL_H, GUTTER = 128, 256, 8     # the full atlas; the half is 0.5 of these
MASTER = 2                      # drawn at twice the full size, then reduced
DIP_MAX = 0.08                  # a picture stands at most this much shorter than its view's tallest
BODY = (0.06, 0.42)             # the head and the trunk, as shares of the figure's height from the top of its head
QUALITY = 86                    # lossy colour; the alpha is kept lossless (alpha_quality 100) so the edge stays clean
# the wardrobes by the temperature (degrees F) the page hands over from one to the next: under the first cold, over the
# second warm (app.js, peopleWardrobe, reads them from the manifest)
TEMPS = [50, 70]


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


def chroma(a):
    """A strip that came back opaque on its chroma green: its alpha from how far each pixel is from the green, and the
    green's spill taken out of the edge only (green no higher than the larger of red and blue within EDGE pixels of the
    keyed ground), so an olive parka keeps its own green."""
    if a[..., 3].min() < 0.99:
        return a
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    k = np.clip((g - np.maximum(r, b) - 0.12) / 0.30, 0, 1)      # 1 on the green, 0 on anything a person wears
    out = a.copy()
    out[..., 3] = 1 - k
    edge = dilate(k > 0.02, 3)
    out[..., 1] = np.where(edge, np.minimum(g, np.maximum(r, b)), g)
    return out


def slice_strip(fid, a, n=FRAMES):
    """The strip's n pictures as boolean masks at the strip's size, left to right, and how they were found."""
    al = a[..., 3]
    H, W = al.shape
    small = al[::2, ::2] > 0.16
    grown = dilate(small, 2)                       # 4 strip pixels: a detached strap or lock of hair joins its figure
    lab, cnt = components(grown)
    area = np.bincount(lab.ravel(), minlength=cnt + 1)[1:]
    big = [i + 1 for i in np.argsort(-area)[:n]]
    tall = {i: np.ptp(np.nonzero((lab == i).any(1))[0]) + 1 for i in big}
    if len(big) == n and min(area[i - 1] for i in big) > 0.3 * area.max() and min(tall.values()) > 0.75 * max(tall.values()):
        big.sort(key=lambda i: np.nonzero((lab == i).any(0))[0].mean())
        return [np.repeat(np.repeat(lab == i, 2, 0), 2, 1)[:H, :W] for i in big], 'alpha pieces'
    col = (al > 0.16).sum(0)                       # the emptiest column within a sixteenth of the strip of each eighth
    xs = [0]
    for k in range(1, n):
        c, r = W * k // n, W // (2 * n)
        xs.append(c - r + int(np.argmin(col[c - r:c + r])))
    xs.append(W)
    masks = []
    for x0, x1 in zip(xs[:-1], xs[1:]):
        if not (al[:, x0:x1] > 0.5).any():
            sys.exit('%s: nothing between columns %d and %d' % (fid, x0, x1))
        # inside the columns, the figure's own pieces: the largest and any whose middle lies over it, never the toe of a
        # neighbour's stride that reached across the cut
        sl = lab[:, x0 // 2:(x1 + 1) // 2]
        ids, cnt_ = np.unique(sl[sl > 0], return_counts=True)
        top = ids[np.argmax(cnt_)]
        tx = np.nonzero((sl == top).any(0))[0]
        keep = [i for i in ids if i == top or tx.min() <= np.nonzero((sl == i).any(0))[0].mean() <= tx.max()]
        sm = np.zeros(lab.shape, bool)
        sm[:, x0 // 2:(x1 + 1) // 2] = np.isin(sl, keep)
        m = np.repeat(np.repeat(sm, 2, 0), 2, 1)[:H, :W]
        m[:, :x0] = False; m[:, x1:] = False
        masks.append(m)
    return masks, 'emptiest columns'


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
    """One picture off its strip: cropped to what it shows, the outer haze gone, every soft edge pixel in the colour of the
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
    """A picture's box of solid pixels (x0, y0, x1, y1, exclusive) and its vertical axis: the centre of the body (the head
    and the trunk, BODY), which the legs and arms move about."""
    al = p[..., 3]
    ys, xs = np.nonzero(al > 0.5)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    h = y1 - y0
    band = al[y0 + int(BODY[0] * h):y0 + int(BODY[1] * h)]
    col = (band > 0.5).sum(0).astype(np.float64)
    axis = float((col * (np.arange(al.shape[1]) + 0.5)).sum() / col.sum())
    return (int(xs.min()), y0, int(xs.max()) + 1, y1), axis


def feet_apart(pose):
    """How far apart the feet stand, in figure heights: the width of the solid pixels in the picture's lowest eighth."""
    p, box = pose[0], pose[1]
    al = p[..., 3]
    h = box[3] - box[1]
    xs = np.nonzero((al[box[3] - max(1, h // 8):box[3]] > 0.5).any(0))[0]
    return float(xs.max() - xs.min() + 1) / h


def resample(p, k):
    """The picture scaled by k, in premultiplied floating point (a channel at a time: no 8-bit premultiplied step)."""
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
    poses, how = {}, []
    for view in VIEWS:
        path = raw_path(fid, view)
        if not os.path.exists(path):
            sys.exit('missing strip %s (run fetch_people_art.py)' % path)
        a = chroma(np.asarray(Image.open(path).convert('RGBA'), np.float32) / 255.0)
        masks, h = slice_strip(fid + '-' + view, a)
        how.append(view + ' ' + h)
        for frame, m in enumerate(masks):
            p = cut_pose(a, m)
            poses[(view, frame)] = (p,) + measure(p)
    SH, SW = CELL_H * MASTER, CELL_W * MASTER
    hgt = lambda k: poses[k][1][3] - poses[k][1][1]
    rel = {}
    for view in VIEWS:   # one scale a strip: its tallest picture at the full height and the rest as drawn beside it
        top = max(hgt((view, f)) for f in range(FRAMES))
        for f in range(FRAMES):
            rel[(view, f)] = float(max(1.0 - DIP_MAX, hgt((view, f)) / top))
    reach = 0.0   # the widest half extent about the axis, in figure heights
    for key, (p, box, axis) in poses.items():
        h = box[3] - box[1]
        reach = max(reach, rel[key] * max(axis - box[0], box[2] - axis) / h)
    fill = min(0.92, (SW / 2 - 3) / (reach * SH))   # three master pixels to spare each side: no stride is cut by its rect
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
    side = [round(feet_apart(poses[('side', f)]), 3) for f in range(FRAMES)]
    info = {'how': ', '.join(how), 'fill': fill, 'rel': [round(rel[k], 3) for k in keys], 'reach': reach, 'side': side,
            # a strip whose passing is not its narrowest picture, or whose contact is not among its widest, is out of order
            'order': 'ok' if side.index(min(side)) in (3, 4, 5) and side[0] >= 0.8 * max(side) else 'CHECK'}
    return cells, round(tall / fill, 3), info


def contact(path, ward, fig_man, full, half):
    """The review sheet for one wardrobe, from the files as they ship: a band a figure, its 24 full cells on mid grey
    (front, back, side, each its eight pictures), then the side's eight at half on brick red."""
    LBL = 16
    N = len(VIEWS) * FRAMES
    bandH = CELL_H + LBL
    sheet = Image.new('RGB', (N * CELL_W + 20 + FRAMES * CELL_W // 2, bandH * len(fig_man)), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for n, fig in enumerate(fig_man):
        y = n * bandH
        d.text((4, y + 2), '%s %s  tall %.2f m a cell' % (ward, fig['id'], fig['tall']), fill=(230, 230, 230))
        bg = Image.new('RGBA', (N * CELL_W, CELL_H), (128, 128, 128, 255))
        i = 0
        for cv in fig['cells']:
            for c in cv:
                bg.alpha_composite(full.crop((c[0], c[1], c[0] + c[2], c[1] + c[3])), (i * CELL_W, 0))
                i += 1
        sheet.paste(bg.convert('RGB'), (0, y + LBL))
        hb = Image.new('RGBA', (FRAMES * CELL_W // 2, CELL_H // 2), (142, 64, 50, 255))
        for i, c in enumerate(fig['cells'][VIEWS.index('side')]):
            hb.alpha_composite(half.crop((c[0] // 2, c[1] // 2, (c[0] + c[2]) // 2, (c[1] + c[3]) // 2)), (i * CELL_W // 2, 0))
        sheet.paste(hb.convert('RGB'), (N * CELL_W + 20, y + LBL))
    sheet.save(path)
    return sheet.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contact', default='', help='also write a review sheet a wardrobe, <this without .png>-<wardrobe>.png')
    a = ap.parse_args()
    if len({f[0] for f in FIGURES}) != len(FIGURES):
        sys.exit('two figures share an id')
    man = {'v': 2, 'frames': FRAMES, 'views': VIEWS, 'temps': TEMPS, 'wardrobes': {}}
    kw = dict(quality=QUALITY, method=6, alpha_quality=100, exact=True)
    total = {'full': 0, 'half': 0}
    for ward in WARDROBES:
        figs = [f for f in FIGURES if f[3] == ward]
        if not figs:
            sys.exit('no figure wears the %s wardrobe' % ward)
        per, W, H, rect = layout(len(figs))
        master = np.zeros((H * MASTER, W * MASTER, 4), np.float32)   # premultiplied
        fig_man = []
        for i, (fid, who, tall, _, carry) in enumerate(figs):
            cells, cell_tall, info = bake_figure(fid, tall)
            for (view, frame), cell in cells.items():
                x, y, w, h = [v * MASTER for v in rect(i, view, frame)]
                master[y:y + h, x:x + w] = cell
            fig_man.append({'id': fid, 'tall': cell_tall, 'cells': [[rect(i, view, frame) for frame in range(FRAMES)] for view in VIEWS]})
            print('%s %s  %s  %.2f m, fills %.3f, cell %.3f m  heights %s\n     side feet apart %s  order %s'
                  % (ward, fid, info['how'], tall, info['fill'], cell_tall, info['rel'], info['side'], info['order']))
        full = reduce2(master)
        half = reduce2(full)
        at = lambda s: [[int(v * s) for v in r] for f in fig_man for view in f['cells'] for r in view]
        im_full, im_half = finish(full, GUTTER, at(1)), finish(half, GUTTER // 2, at(0.5))
        man['wardrobes'][ward] = {'atlas': {'img': art_files.write(im_full, 'people', 'people-' + ward, 'WEBP', **kw),
                                            'imgHalf': art_files.write(im_half, 'people', 'people-' + ward + '-half', 'WEBP', **kw),
                                            'w': W, 'h': H},
                                  'figures': fig_man}
        gpu = lambda s: int(W * s) * int(H * s) * 4 * 4 // 3
        total['full'] = max(total['full'], gpu(1)); total['half'] = max(total['half'], gpu(0.5))
        for key, s in (('img', 1), ('imgHalf', 0.5)):
            p = man['wardrobes'][ward]['atlas'][key]
            print('  %-8s %-46s %4dx%-4d %8d B on disk, %5.2f MB on the GPU with its mips' % (key, p, W * s, H * s, art_files.size(p), gpu(s) / 1e6))
        if a.contact:
            out = a.contact[:-4] if a.contact.endswith('.png') else a.contact
            print('  contact sheet %s-%s.png %dx%d' % ((out, ward) + contact(out + '-' + ward + '.png', ward, fig_man,
                  Image.open(os.path.join(HERE, man['wardrobes'][ward]['atlas']['img'])).convert('RGBA'),
                  Image.open(os.path.join(HERE, man['wardrobes'][ward]['atlas']['imgHalf'])).convert('RGBA'))))
    gone = art_files.prune('people')
    with open(OUT + '.tmp', 'w') as f:
        json.dump(man, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('%d figures in %d wardrobes, pruned %d; one wardrobe at a time on the GPU: up to %.1f MB on a computer, %.1f MB on a phone; wrote %s'
          % (len(FIGURES), len(WARDROBES), gone, total['full'] / 1e6, total['half'] / 1e6, OUT))


if __name__ == '__main__':
    main()
