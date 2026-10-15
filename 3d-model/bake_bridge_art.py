#!/usr/bin/env python3
"""Bake the Delaware bridges' art (Round 195) into bridge_art.json, which build.py inlines as BRIDGE_ART, and the images
themselves into art/bridges/ (art_files.py: files the page loads on demand, a phone's half copies beside them).

fetch_bridge_art.py makes five pictures in lidar_cache/bridge_art_raw/. This bake makes two textures of them:
  detail  1024 square, one tileable surface a channel, each the picture's luminance over its own mean (128 is the mean,
          so the page multiplies a part's own colour by twice the texel and a mip far away leaves the colour as it is):
          r the riveted painted steel (3 m a tile), g the rock-faced granite (4.8 m a tile, eight 0.6 m courses), b the
          weathered concrete (4 m a tile). Each is made periodic first: the picture is laid over a copy of itself moved by
          half a tile both ways, the copy showing only in a band round the edges (BLEND), so the seam the model left at
          the border falls where the copy is drawn and the copy's own seam falls in the middle of the original, where the
          original is drawn. The granite keeps its courses level: the copy is moved by a whole number of courses.
  elev    1024 square sRGB: the Ben Franklin's anchorage pylon above the deck (8 by 16 m, the left half) and one bay of the
          anchorage wall's top band (cut at the middle of two pilasters, so the page lays bay after bay along a wall, with
          a cross-fade at the cut for the rock-faced course under it), each in a gutter of its own edge pixels (PAD) so a
          mip never reads its neighbour. Their rects are in the manifest as [u0, v0, u1, v1], v up from the bottom.
Every half copy is the same image at half the size (a phone's).

Usage: python3 bake_bridge_art.py [--preview DIR]"""
import argparse, json, os
import numpy as np
from PIL import Image
import art_files
import fetch_bridge_art as F

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = F.RAW
OUT = os.path.join(HERE, 'bridge_art.json')
DET = 1024                    # the detail texture's side
BLEND = 0.16                  # the copy's band at the border, a fraction of the side
TILE_M = {'steel': 3.0, 'granite': 4.8, 'concrete': 4.0}   # metres a tile (the prompts' own)
COURSES = 8                   # the granite's courses in a tile
EL = 1024                     # the elevation atlas's side
PAD = 8
PYLON_M = (8.0, 16.0)         # the pylon face, metres (the prompt's)
FRIEZE_M = 7.5                # the wall band's height, metres (the prompt's); its bay's width follows from the cut
FRIEZE_CUT = (525, 1005)      # the frieze picture's x span of one bay, measured by hand on frieze.png (1536 by 768): the
                              # middles of its second and third pilasters (440 to 610 and 920 to 1090 px)
SEAM_PX = 18                  # the cross-fade at the frieze's cut


def lum(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def periodic(L, shift_y=None):
    """L: a square float image. The image over a copy of itself moved half a tile each way (the y move a whole number
    of courses when given), the copy shown only within BLEND of the border."""
    n = L.shape[0]
    sy = n // 2 if shift_y is None else shift_y
    C = np.roll(np.roll(L, n // 2, axis=1), sy, axis=0)
    t = np.arange(n) / (n - 1)
    edge = np.minimum(t, 1 - t)                                   # 0 at the border, 0.5 in the middle
    w1 = np.clip(1 - edge / BLEND, 0, 1)
    w1 = w1 * w1 * (3 - 2 * w1)
    W = np.maximum(w1[None, :], w1[:, None])                      # the copy's weight
    return L * (1 - W) + C * W


def detail_channel(name):
    im = Image.open(os.path.join(RAW, name + '.png')).convert('RGB').resize((DET, DET), Image.LANCZOS)
    L = lum(np.asarray(im, dtype=np.float32) / 255.0)
    sy = None
    if name == 'granite':
        sy = int(round(DET / COURSES)) * (COURSES // 2)            # half the tile in whole courses
    P = periodic(L, sy)
    m = float(P.mean())
    return np.clip(P / m * 0.5, 0, 1), m


def pad(img, p):
    a = np.asarray(img)
    a = np.pad(a, ((p, p), (p, p), (0, 0)), mode='edge')
    return Image.fromarray(a)


def bake(preview=None):
    out = {}
    chans, means = [], {}
    for k in ('steel', 'granite', 'concrete'):
        c, m = detail_channel(k)
        chans.append(c)
        means[k] = round(m, 4)
    D = Image.fromarray((np.stack(chans, -1) * 255 + 0.5).astype(np.uint8), 'RGB')
    out['detail'] = art_files.write(D, 'bridges', 'detail', 'WEBP', quality=92, method=6)
    out['detailHalf'] = art_files.write(D.resize((DET // 2, DET // 2), Image.LANCZOS), 'bridges', 'detail-half', 'WEBP', quality=90, method=6)
    out['detailTile'] = [TILE_M['steel'], TILE_M['granite'], TILE_M['concrete']]
    out['detailMean'] = [means['steel'], means['granite'], means['concrete']]
    # the elevations
    A = Image.new('RGB', (EL, EL), (128, 128, 128))
    py = Image.open(os.path.join(RAW, 'pylon.png')).convert('RGB')
    pw, ph = EL // 2 - 2 * PAD, EL - 2 * PAD
    A.paste(pad(py.resize((pw, ph), Image.LANCZOS), PAD), (0, 0))
    rects = {'pylon': [PAD / EL, PAD / EL, (PAD + pw) / EL, (PAD + ph) / EL]}
    fz = np.asarray(Image.open(os.path.join(RAW, 'frieze.png')).convert('RGB'), dtype=np.float32)
    x0, x1 = FRIEZE_CUT
    bay = fz[:, x0:x1].copy()
    # the cut's cross-fade: the bay's last SEAM_PX columns blend into the columns just past its first edge, so the right
    # edge of one bay runs on into the left edge of the next
    for j in range(SEAM_PX):
        w = (j + 1) / (SEAM_PX + 1)
        bay[:, -SEAM_PX + j] = bay[:, -SEAM_PX + j] * (1 - w) + fz[:, x0 + j] * w
    bh = EL // 2 - 2 * PAD
    bw = int(round(bh * bay.shape[1] / bay.shape[0]))
    bayIm = Image.fromarray(np.clip(bay, 0, 255).astype(np.uint8)).resize((bw, bh), Image.LANCZOS)
    ox, oy = EL // 2, 0
    A.paste(pad(bayIm, PAD), (ox, oy))
    # v up from the bottom: the frieze sits in the image's top half
    rects['frieze'] = [(ox + PAD) / EL, 1 - (oy + PAD + bh) / EL, (ox + PAD + bw) / EL, 1 - (oy + PAD) / EL]
    rects['pylon'] = [PAD / EL, 1 - (PAD + ph) / EL, (PAD + pw) / EL, 1 - PAD / EL]
    out['elev'] = art_files.write(A, 'bridges', 'elev', 'WEBP', quality=90, method=6)
    out['elevHalf'] = art_files.write(A.resize((EL // 2, EL // 2), Image.LANCZOS), 'bridges', 'elev-half', 'WEBP', quality=88, method=6)
    out['rects'] = {k: [round(v, 5) for v in r] for k, r in rects.items()}
    out['pylonM'] = list(PYLON_M)
    out['friezeM'] = [round(FRIEZE_M * bay.shape[1] / bay.shape[0], 3), FRIEZE_M]   # one bay's width and the band's height
    out['bytes'] = {k: art_files.size(out[k]) for k in ('detail', 'detailHalf', 'elev', 'elevHalf')}
    gone = art_files.prune('bridges')
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print('bridge_art.json', out['bytes'], 'pruned', gone)
    if preview:
        os.makedirs(preview, exist_ok=True)
        D.save(os.path.join(preview, 'detail.png'))
        A.save(os.path.join(preview, 'elev.png'))
        # each channel tiled 2 by 2, to see its seams
        for i, k in enumerate(('steel', 'granite', 'concrete')):
            ch = np.asarray(D)[..., i]
            Image.fromarray(np.tile(ch, (2, 2))).resize((1024, 1024)).save(os.path.join(preview, 'tile-%s.png' % k))
        fb = np.asarray(bayIm)
        Image.fromarray(np.tile(fb, (1, 3, 1))).save(os.path.join(preview, 'frieze-3.png'))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default=None)
    a = ap.parse_args()
    bake(a.preview)
