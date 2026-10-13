#!/usr/bin/env python3
"""Bake the streets' generated textures (fetch_street_art.py) into street_art.json, which build.py inlines as
STREET_ART, and the images into art/streets/ (files the page loads on demand, a phone's copy at half; art_files.py).

  lanewear   the three lane photographs stacked end to end into one strip a lane wide, each joint cross-faded over
             LANE_XF px and the strip's own ends too, so it repeats along the road without a seam; their brightness
             pulled halfway to a common mean, so a section reads older or newer without a lane turning to a patchwork.
             The page lays it across one lane (mirrored lane to lane, so the lane edges meet themselves) and LANE_M
             metres a photograph along the road
  ballast    the main line's ties and ballast, cropped to a whole number of tie pitches (found by autocorrelation
             along the track) so the ties repeat exactly; the two rails' columns are found (the columns that change
             least down the image) and written as fractions of the width, so the page lays the texture's rails under
             the drawn ones at standard gauge
  concrete   the elevated roads' weathered concrete side and the El's riveted steel: square, mirrored by the page
  el_steel   (MirroredRepeatWrapping) so they tile without a blend ghosting their joints
  lot        a parking lot's oil-stained asphalt, made to tile both ways (the half-roll blend; it has no pattern)

Each texture's linear mean luminance rides along so the page applies it as a ratio and keeps every surface's own
calibrated colour."""
import json, os, sys
import numpy as np
from PIL import Image
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'street_art_raw')
OUT = os.path.join(HERE, 'street_art.json')
LANES = ('lanewear_a', 'lanewear_c', 'lanewear_b')
LANE_W, LANE_H, LANE_XF = 384, 576, 72        # one photograph at 384 x 576 px, cross-faded over 72 px a joint
LANE_M = 5.4                                  # metres along the road a photograph spans (3.6 m across, 2:3)
TIE_PITCH = 0.6                               # metres
LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


def lin(a):
    v = np.clip(a, 0, 255) / 255.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def lum_mean(a):
    return float((lin(a).reshape(-1, 3) @ LUM).mean())


def load(gid, size=None):
    p = os.path.join(RAW, gid + '.png')
    if not os.path.exists(p):
        sys.exit('no %s (run fetch_street_art.py)' % p)
    im = Image.open(p).convert('RGB')
    if size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, np.float32)


def tileable(a):
    """Seamless in x, then in y: a blend with a half-rolled copy, the copy at the edges (bake_ground_art.py's)."""
    for axis in (1, 0):
        n = a.shape[axis]
        r = np.roll(a, n // 2, axis=axis)
        t = np.arange(n, dtype=np.float32)
        w = np.clip(np.minimum(t, n - 1 - t) / (n * 0.22), 0, 1)
        w = w * w * (3 - 2 * w)
        w = w[None, :, None] if axis == 1 else w[:, None, None]
        a = a * w + r * (1 - w)
    return a


def lane_strip():
    parts = [load(g, (LANE_W, LANE_H)) for g in LANES]
    means = [lum_mean(p) for p in parts]
    target = float(np.mean(means))
    parts = [p * (0.5 + 0.5 * (target / m) ** (1 / 2.2)) for p, m in zip(parts, means)]   # halfway to the mean, in display terms
    k = LANE_XF
    ramp = np.linspace(0.0, 1.0, k, dtype=np.float32)[:, None, None]
    ramp = ramp * ramp * (3 - 2 * ramp)
    # each part keeps its own middle; the k rows at a joint are the previous part's last k blended into the next's first k
    rows = []
    n = len(parts)
    for i, p in enumerate(parts):
        nxt = parts[(i + 1) % n]
        rows.append(p[k:-k])
        rows.append(p[-k:] * (1 - ramp) + nxt[:k] * ramp)
    strip = np.concatenate(rows, axis=0)
    return strip, len(parts) * (LANE_H - k) / LANE_H * LANE_M


def autoperiod(profile, lo, hi):
    p = profile - profile.mean()
    ac = np.correlate(p, p, mode='full')[len(p) - 1:]
    return lo + int(np.argmax(ac[lo:hi + 1]))


def ballast():
    a = load('ballast_ties')                       # 1024 x 1536, the track running down the image
    H, W = a.shape[:2]
    L = lin(a) @ LUM
    # the ties: the strongest repeat of the mean row brightness across the middle, near the 12 or so the prompt implies
    prof = L[:, int(W * 0.38):int(W * 0.62)].mean(axis=1)
    per = autoperiod(prof, 60, 220)
    n = H // per
    y0 = (H - n * per) // 2
    a = a[y0:y0 + n * per]
    # the rails: the columns that change least down the image (continuous steel), one either side of the middle
    std = (lin(a) @ LUM).std(axis=0)
    left = int(np.argmin(std[int(W * 0.15):int(W * 0.5)])) + int(W * 0.15)
    right = int(np.argmin(std[int(W * 0.5):int(W * 0.85)])) + int(W * 0.5)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((512, int(round(512 * a.shape[0] / W / 2)) * 2), Image.LANCZOS)
    return out, n, per, (left / W, right / W)


def main():
    out = {}
    strip, metres = lane_strip()
    im = Image.fromarray(np.clip(strip, 0, 255).astype(np.uint8))
    out['lanewear'] = art_files.write(im, 'streets', 'lanewear', 'WEBP', quality=82, method=6)
    out['lanewearHalf'] = art_files.write(im.resize((im.width // 2, im.height // 2), Image.LANCZOS), 'streets', 'lanewear-half', 'WEBP', quality=80, method=6)
    out['lanewearM'] = round(metres, 3)
    out['lanewearMean'] = round(lum_mean(strip), 5)
    print('lanewear  %d x %d px, %.2f m a repeat, mean %.4f' % (im.width, im.height, metres, out['lanewearMean']))
    bim, nties, per, rails = ballast()
    out['ballast'] = art_files.write(bim, 'streets', 'ballast', 'WEBP', quality=82, method=6)
    out['ballastHalf'] = art_files.write(bim.resize((bim.width // 2, bim.height // 2), Image.LANCZOS), 'streets', 'ballast-half', 'WEBP', quality=80, method=6)
    out['ballastM'] = round(nties * TIE_PITCH, 3)
    out['ballastRails'] = [round(rails[0], 4), round(rails[1], 4)]
    out['ballastMean'] = round(lum_mean(np.asarray(bim, np.float32)), 5)
    print('ballast   %d x %d px, %d ties at %d px, rails at %.3f and %.3f of the width' % (bim.width, bim.height, nties, per, rails[0], rails[1]))
    for gid, key in (('concrete_wall', 'concrete'), ('el_steel', 'steel')):
        a = load(gid, (768, 768))
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        out[key] = art_files.write(im, 'streets', key, 'WEBP', quality=82, method=6)
        out[key + 'Half'] = art_files.write(im.resize((384, 384), Image.LANCZOS), 'streets', key + '-half', 'WEBP', quality=80, method=6)
        out[key + 'Mean'] = round(lum_mean(a), 5)
        print('%-9s mean %.4f' % (key, out[key + 'Mean']))
    a = tileable(load('lot_asphalt', (768, 768)))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    out['lot'] = art_files.write(im, 'streets', 'lot', 'WEBP', quality=82, method=6)
    out['lotHalf'] = art_files.write(im.resize((384, 384), Image.LANCZOS), 'streets', 'lot-half', 'WEBP', quality=80, method=6)
    out['lotMean'] = round(lum_mean(a), 5)
    out['m'] = {'concrete': 4.0, 'steel': 3.0, 'lot': 6.0}
    for k in ('lanewear', 'ballast', 'concrete', 'steel', 'lot'):
        print('%-9s %d KB, half %d KB' % (k, art_files.size(out[k]) // 1024, art_files.size(out[k + 'Half']) // 1024))
    print('pruned %d old street files' % art_files.prune('streets'))
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
