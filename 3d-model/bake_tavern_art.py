#!/usr/bin/env python3
"""Bake A Man Full of Trouble's art (Round 199; fetch_tavern_art.py made the images) into tavern_art.json, which build.py
inlines as TAVERN_ART, and its one atlas into art/tavern/ (a file the page loads on demand, a phone's copy at half;
art_files.py).

The atlas holds four swatches, each in its own cell padded with its own wrapped edge so mips and filtering never meet a
neighbour, and the house's openings, each with an edge-replicated gutter:
  swatches  brick (Flemish bond, cut on its own courses and joints by bake_wall_art.course_tile, 7 cm a course, its
            glazed headers eased HEADER_EASE of the way toward the stretchers: the generated ones stand out as a black
            checker where the photographs' read only a little darker), shingle (cut on its courses, 13 cm), paint and
            marble (the half-roll blend). Each with its size in metres and its linear mean;
  elements  the door under its transom, the ground floor's shuttered window, the nine-over-nine sash, the two leaves of
            the upper floor's shutters (one image cut at its meeting stiles), the dormers' six-over-six sash. A glazed
            element's chroma-key panes are measured (the runs of key down its columns and across its rows: the panes'
            outer edges, how many across and down in each sash, the bars between them) and repainted on that exact
            regular grid, the glass a dark neutral and the bars the casing's own paint with a rounded profile, so the
            page's glass (the grid in uniforms: its reflections and its rooms) meets the picture's bars to the texel.
Every element is laid at the same PPM pixels a metre, the largest that packs into ATLAS_W by ATLAS_H.

The raw images are in lidar_cache/tavern_art_raw (TAVERN_ART_RAW overrides); CHOSEN names the variant used for each, by
eye against the reference photos (Wikimedia Commons 'A Man Full of Trouble Tavern', 'Man Full of Trouble Tavern -
Philadelphia (2642072807)', 'Vernacular - 18th Century - Philadelphia, PA - A Man Full of Trouble Tavern (1)' and '(2)').

Usage: python3 bake_tavern_art.py [--check]   (--check writes the atlas and a look at each element to RAW/look-*.png only)"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageFilter
import art_files
import bake_wall_art as BW

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('TAVERN_ART_RAW') or os.path.join(HERE, 'lidar_cache', 'tavern_art_raw')
OUT = os.path.join(HERE, 'tavern_art.json')
CHOSEN = {'brick': 'brick-a', 'shingle': 'shingle-a', 'paint': 'paint-a', 'marble': 'marble-a', 'door': 'door-a',
          'winshut': 'winshut-a', 'sash': 'sash-d', 'shutpair': 'shutpair-c', 'dsash': 'dsash-a'}
# the swatches: (key, course in metres or None, what an uncoursed image shows across in metres, inner cell px)
SWATCHES = [('brick', 0.07, None, 448), ('shingle', 0.127, None, 448), ('paint', None, 1.0, 224), ('marble', None, 0.6, 224)]
SW_PAD = 32
# each swatch's colour as the house shows it, set by eye in the scene against the reference photos (the generated shingles
# came out a pale silver that read as asphalt in the sun, the paint a cold white)
SW_GAIN = {'brick': (1.06, 1.0, 0.96), 'shingle': (0.74, 0.69, 0.63), 'paint': (0.9, 0.88, 0.8), 'marble': (0.92, 0.92, 0.92)}
HEADER_EASE = 0.7   # how far a glazed header's colour is taken toward the stretchers' (0 keeps the generated checker)
# the elements: (key, width, height in metres, the glass's sashes as [cols, rows] each top to bottom, or None)
ELEMENTS = [('door', 1.15, 2.85, [[4, 1]]), ('sash', 1.10, 1.95, [[3, 3], [3, 3]]), ('dsash', 0.95, 1.12, [[3, 2], [3, 2]]),
            ('winshut', 1.15, 1.95, None), ('shutL', 0.45, 1.85, None), ('shutR', 0.45, 1.85, None)]
GUTTER = 8
ATLAS_W, ATLAS_H = 2048, 1024
GLASS_RGB = np.array([30.0, 33.0, 36.0], np.float32)   # the glass's own dark under the page's optics
LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


def load(name):
    p = os.path.join(RAW, CHOSEN.get(name, name) + '.png')
    if not os.path.exists(p):
        sys.exit('no %s (run fetch_tavern_art.py)' % p)
    return np.asarray(Image.open(p).convert('RGB'), np.float32)


def key_of(a):
    """The chroma key's strength at each pixel: 1 on the flat green, falling to 0 through the anti-aliased edge."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return np.clip((g - np.maximum(r, b) - 40.0) / 120.0, 0, 1)


def runs(profile, thr):
    """[start, end) runs where the profile is over thr."""
    on = profile > thr
    out, s = [], None
    for i, v in enumerate(on):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i))
            s = None
    if s is not None:
        out.append((s, len(on)))
    return out


def ease_headers(t):
    """The glazed headers toward the stretchers: a header is a dark brick with little red in it (the stretchers are red,
    the mortar pale), found per pixel and feathered, and its colour is scaled by HEADER_EASE of the way to the stretchers'
    mean, so it keeps its own grain and reads a little darker and duller than a stretcher, as the photographs' do."""
    L = t @ LUM
    red = (t[..., 0] - t[..., 2]) / (t[..., 0] + 1.0)
    st = (L > 60) & (L < 150) & (red > 0.45)
    hd = (L < 95) & (red < 0.35)
    m = np.asarray(Image.fromarray((hd * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255.0
    ratio = t[st].reshape(-1, 3).mean(0) / np.maximum(t[hd].reshape(-1, 3).mean(0), 1.0)
    k = (HEADER_EASE * m)[..., None]
    print('headers: %.0f%% of the tile, stretchers %s, headers %s' % (100 * hd.mean(), np.round(t[st].reshape(-1, 3).mean(0)), np.round(t[hd].reshape(-1, 3).mean(0))))
    return t * (1 - k) + t * ratio[None, None, :] * 0.82 * k


def flatten(t, frac=0.18):
    """A tile's light taken out at its own scale (a generated swatch is lit a little brighter on one side, and repeated
    over a gable it banded the wall every 1.3 m): each channel over its wrapped blur, times its mean."""
    n = t.shape[0]
    big = np.concatenate([np.concatenate([t] * 3, 1)] * 3, 0)
    im = Image.fromarray(np.clip(big, 0, 255).astype(np.uint8))
    bl = np.asarray(im.filter(ImageFilter.GaussianBlur(n * frac)), np.float32)[n:2 * n, t.shape[1]:2 * t.shape[1]]
    return t / np.maximum(bl, 1.0) * t.reshape(-1, 3).mean(0)[None, None, :]


def make_swatch(key, course_m, span_m):
    a = load(key)
    if course_m:
        t, mx, my, rep = BW.course_tile(a, course_m, 'tavern_' + key)
        if key == 'brick' and HEADER_EASE > 0:
            t = ease_headers(t)
    else:
        t, mx, my = BW.tileable(a), span_m, span_m
        rep = 'tavern_%s: blended, %.2f m' % (key, span_m)
    t = flatten(t) * np.array(SW_GAIN.get(key, (1, 1, 1)), np.float32)[None, None, :]
    return t, mx, my, rep


def glass_grid(a, sashes):
    """Measure a glazed element's panes: per sash its glass rect [x0, y0, x1, y1] in pixels (the panes' outer edges), the
    bars across and down, and how many rows of panes each sash was drawn with (the sashes split at the widest gap down the
    rows, the meeting rail). Returns ([rect per sash], bar across px, bar down px, [rows drawn per sash])."""
    k = key_of(a)
    cols = runs(k.mean(axis=0), 0.08)
    rows = runs(k.mean(axis=1), 0.08)
    if len(cols) != sashes[0][0]:
        sys.exit('panes: %d columns of key, wanted %d' % (len(cols), sashes[0][0]))
    groups = [rows]
    if len(sashes) == 2:
        if len(rows) < 2:
            sys.exit('panes: %d rows of key for two sashes' % len(rows))
        gaps = [rows[i + 1][0] - rows[i][1] for i in range(len(rows) - 1)]
        i = int(np.argmax(gaps))
        groups = [rows[:i + 1], rows[i + 1:]]
    gaps_c = [cols[i + 1][0] - cols[i][1] for i in range(len(cols) - 1)]
    gaps_r = [g[j + 1][0] - g[j][1] for g in groups for j in range(len(g) - 1)]
    rects = [[cols[0][0], g[0][0], cols[-1][1], g[-1][1]] for g in groups]
    bu = float(np.median(gaps_c)) if gaps_c else 0.0
    bv = float(np.median(gaps_r)) if gaps_r else bu
    return rects, bu, bv, [len(g) for g in groups]


def equalise(a, rects):
    """Two sashes drawn unequal (the model draws nine over six, however it is asked; the house's are nine over nine, refs)
    made equal: the meeting rail's own pixels moved to the middle of the glass, each sash's rect the half either side; the
    panes are repainted on their grids after this."""
    (x0, ta, x1, ba), (_, tb, _, bb) = rects
    rail = tb - ba
    mid = (ta + bb) / 2.0
    na, nb = int(round(mid - rail / 2.0)), int(round(mid - rail / 2.0)) + rail
    out = a.copy()
    out[na:nb, x0:x1] = a[ba:tb, x0:x1]
    return out, [[x0, ta, x1, na], [x0, nb, x1, bb]]


def paint_glass(a, rects, sashes, bu, bv):
    """Repaint every sash's glass rect on its regular grid: glass where the page draws glass, the bars between in the
    casing's own paint (its median beside the rect) with a rounded profile; the key's anti-aliased fringe outside the
    rects is taken back to the paint."""
    out = a.copy()
    k = key_of(a)
    wood_px = a[(k < 0.01) & ((a @ LUM) > np.percentile(a @ LUM, 40))]
    wood = np.median(wood_px.reshape(-1, 3), axis=0)
    H, W = k.shape
    ss = 4
    for (x0, y0, x1, y1), (c, r) in zip(rects, sashes):
        pw = (x1 - x0 - (c - 1) * bu) / c
        ph = (y1 - y0 - (r - 1) * bv) / r
        Pu, Pv = pw + bu, ph + bv
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        cov = np.zeros(xs.shape, np.float32)
        prof = np.zeros(xs.shape, np.float32)
        for sy in range(ss):
            for sx in range(ss):
                u = xs + (sx + 0.5) / ss - x0
                v = ys + (sy + 0.5) / ss - y0
                fu, fv = np.mod(u, Pu), np.mod(v, Pv)
                gu, gv = fu < pw, fv < ph
                cov += (gu & gv)
                # the bar's rounded profile: lit along its middle, shaded toward its edges
                du = np.where(gu, 1.0, np.abs((fu - pw) / max(bu, 1e-3) - 0.5) * 2.0)
                dv = np.where(gv, 1.0, np.abs((fv - ph) / max(bv, 1e-3) - 0.5) * 2.0)
                prof += np.minimum(du, dv)
        cov /= ss * ss
        prof /= ss * ss
        bar = wood[None, None, :] * (1.06 - 0.22 * prof[..., None] ** 2)
        n = (np.random.default_rng(int(x0 * 7 + y0)).random(cov.shape).astype(np.float32) - 0.5) * 4.0
        glass = GLASS_RGB[None, None, :] + n[..., None]
        out[y0:y1, x0:x1] = glass * cov[..., None] + bar * (1 - cov[..., None])
        k[y0:y1, x0:x1] = 0
    # the fringe the rects did not cover: the key's green taken back to the paint by its strength
    out = out * (1 - k[..., None]) + wood[None, None, :] * k[..., None]
    return out


def grow(a, gutter):
    return np.pad(a, ((gutter, gutter), (gutter, gutter), (0, 0)), mode='edge')


def pack(items, W, H):
    """Skyline packing, tallest first, each item where its top lands lowest (the leftmost of those): {key: (x, y)}, or
    None when they do not fit."""
    sky = np.zeros(W, np.int64)
    at = {}
    for key, w, h in sorted(items, key=lambda it: (-it[2], -it[1])):
        if w > W:
            return None
        best = None
        for x in range(0, W - w + 1, 4):
            y = int(sky[x:x + w].max())
            if best is None or y < best[1]:
                best = (x, y)
        x, y = best
        if y + h > H:
            return None
        sky[x:x + w] = y + h
        at[key] = (x, y)
    return at


def uv_rect(x, y, w, h):
    """An atlas rect [u0, v0, du, dv] in three's uv (v up from the image's foot, flipY)."""
    return [round(x / ATLAS_W, 6), round(1 - (y + h) / ATLAS_H, 6), round(w / ATLAS_W, 6), round(h / ATLAS_H, 6)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    # the swatches
    sw = {}
    for key, course_m, span_m, inner in SWATCHES:
        t, mx, my, rep = make_swatch(key, course_m, span_m)
        print(rep)
        t = np.asarray(Image.fromarray(np.clip(t, 0, 255).astype(np.uint8)).resize((inner, inner), Image.LANCZOS), np.float32)
        sw[key] = (np.pad(t, ((SW_PAD, SW_PAD), (SW_PAD, SW_PAD), (0, 0)), mode='wrap'), mx, my, BW.lin_mean(t), inner)
    # the elements, measured and repainted at their own resolution
    src = {}
    for key, wm, hm, sashes in ELEMENTS:
        if key in ('shutL', 'shutR'):
            continue
        a = load(key)
        g = None
        if sashes:
            rects, bu, bv, drawn = glass_grid(a, sashes)
            if len(sashes) == 2 and drawn != [r for _, r in sashes]:
                print('%-8s drawn %s over the sashes, equalised to %s' % (key, drawn, [r for _, r in sashes]))
                a, rects = equalise(a, rects)
            a = paint_glass(a, rects, sashes, bu, bv)
            H, W = a.shape[:2]
            g = {'rects': [[x0 / W, 1 - y1 / H, x1 / W, 1 - y0 / H] for (x0, y0, x1, y1) in rects], 'grid': [[c, r] for c, r in sashes],
                 'bar': [bu / W, bv / H]}
            print('%-8s %d sash(es), bars %.1f x %.1f px, glass %s' % (key, len(rects), bu, bv, ' '.join('%d..%d x %d..%d' % (r[0], r[2], r[1], r[3]) for r in rects)))
        src[key] = (a, g)
    # the shutters' two leaves: the pair cut at its meeting stiles (the darkest column near its middle)
    pair = load('shutpair')
    H, W = pair.shape[:2]
    prof = (pair @ LUM).mean(axis=0)
    mid = int(W * 0.42) + int(np.argmin(prof[int(W * 0.42):int(W * 0.58)]))
    src['shutL'] = (pair[:, :mid], None)
    src['shutR'] = (pair[:, mid:], None)
    print('shutters cut at %d of %d px' % (mid, W))
    # the largest scale that packs
    ppm = 320
    while ppm > 120:
        items = [(k, v[0].shape[1], v[0].shape[0]) for k, v in sw.items()]
        dims = {}
        for key, wm, hm, _ in ELEMENTS:
            w, h = int(round(wm * ppm)), int(round(hm * ppm))
            dims[key] = (w, h)
            items.append((key, w + 2 * GUTTER, h + 2 * GUTTER))
        at = pack(items, ATLAS_W, ATLAS_H)
        if at:
            break
        ppm -= 4
    print('elements at %d px a metre' % ppm)
    A = np.zeros((ATLAS_H, ATLAS_W, 3), np.float32) + 128
    man = {'v': 1, 'w': ATLAS_W, 'h': ATLAS_H, 'ppm': ppm, 'sw': {}, 'el': {}}
    for k, (cell, mx, my, mean, inner) in sw.items():
        x, y = at[k]
        A[y:y + cell.shape[0], x:x + cell.shape[1]] = cell
        man['sw'][k] = {'rect': uv_rect(x + SW_PAD, y + SW_PAD, inner, inner), 'm': [round(mx, 3), round(my, 3)], 'mean': mean}
    for key, wm, hm, sashes in ELEMENTS:
        a, g = src[key]
        w, h = dims[key]
        im = np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), np.float32)
        x, y = at[key]
        A[y:y + h + 2 * GUTTER, x:x + w + 2 * GUTTER] = grow(im, GUTTER)
        e = {'rect': uv_rect(x + GUTTER, y + GUTTER, w, h), 'size': [wm, hm], 'mean': BW.lin_mean(im)}
        if g:
            e.update({'glass': [[round(v, 5) for v in r] for r in g['rects']], 'grid': g['grid'], 'bar': [round(g['bar'][0], 5), round(g['bar'][1], 5)]})
        man['el'][key] = e
    im = Image.fromarray(np.clip(A, 0, 255).astype(np.uint8))
    if args.check:
        im.save(os.path.join(RAW, 'look-atlas.png'))
        print('wrote', os.path.join(RAW, 'look-atlas.png'))
        return
    man['img'] = art_files.write(im, 'tavern', 'atlas', 'WEBP', quality=86, method=6)
    man['imgHalf'] = art_files.write(im.resize((ATLAS_W // 2, ATLAS_H // 2), Image.LANCZOS), 'tavern', 'atlas-half', 'WEBP', quality=84, method=6)
    print('atlas %d KB, half %d KB' % (art_files.size(man['img']) // 1024, art_files.size(man['imgHalf']) // 1024))
    print('pruned %d old tavern files' % art_files.prune('tavern'))
    with open(OUT + '.tmp', 'w') as f:
        json.dump(man, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f KB' % (os.path.getsize(OUT) / 1e3))


if __name__ == '__main__':
    main()
