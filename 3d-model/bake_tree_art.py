#!/usr/bin/env python3
"""Bake the street trees' images (fetch_tree_art.py) into tree_art.json, which build.py inlines as TREE_ART, and the
images themselves into art/trees/ (Round 184: files the page loads on demand, a phone's copy at half; art_files.py).

Per look, view and season: the generated image keyed (a winter image's opaque pale haze between the twigs, which the
model leaves in place of transparency, goes clear: dehaze keys the crown on darkness and spares the trunk),
cropped to what it shows, fitted into a square cell (a side view standing on the cell's foot, centred; a top view
centred), its colour bled out into the clear pixels so a mip never fringes dark or white, its alpha firmed (a fine twig
at 0.3 survives the alpha test), and stored as a WebP. Each records its framing: a side view the fraction of the cell's
height the tree fills (hf) and its width over its height (ar); a top view the fraction of the cell the crown spans (df).

Every species in tree_names.json maps onto a look by its name (LOOK_OF, first match wins; anything else the broadleaf),
written as speciesLook[] in the names' order. SIDE and TOP are the stored cell sizes; the page draws them at these on a
computer and at half on a phone."""
import argparse, base64, io, json, os, re, sys
import art_files
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'tree_art_raw')
OUT = os.path.join(HERE, 'tree_art.json')
# the realism pass (ground-vegetation 11): stored at 448 and 224 so a computer draws a near tree from a picture as large as
# it shows (the page caps a phone's cells at the old 128 and 64, from the half copies)
SIDE, TOP = 448, 224
QUALITY = 78
# 'turning' (the realism pass): a fifth of the crown coloured, between summer and autumn
SEASONS = ('summer', 'turning', 'autumn', 'winter', 'spring')
# peak colour as a photograph shows it, not as the model paints it (ground-vegetation 4): the autumn and bloom images
# lose a fifth of their saturation and a twentieth of their value
MUTE = {'autumn': (0.82, 0.95), 'spring': (0.82, 0.95)}

LOOK_OF = [   # (look, species name pattern), on the inventory's common names; Round 184 added ten looks ahead of the
    # broader patterns they used to fall under
    ('sycamore', r'american sycamore'),
    ('plane', r'plane|sycamore'),
    ('silvermaple', r'silver maple'),
    ('crimsonking', r'crimson king|royal red|schwedler|faassen'),
    ('redmaple', r'red maple|freeman|red sunset'),
    ('sugarmaple', r'maple|boxelder'),
    ('magnolia', r'magnolia'),
    ('dogwood', r'dogwood'),
    ('serviceberry', r'serviceberry|amelanchier'),
    ('pear', r'pear'),
    ('cherry', r'cherry|plum|prunus|apricot|peach'),
    ('locust', r'locust|pagoda|sophora|yellowwood|coffeetree|coffee tree|mimosa|silk tree'),
    ('pinoak', r'pin oak|willow oak|shingle oak|laurel oak'),
    ('redoak', r'\boak'),
    ('willow', r'willow'),
    ('riverbirch', r'birch'),
    ('zelkova', r'zelkova'),
    ('elm', r'elm|hackberry'),
    ('ginkgo', r'ginkgo'),
    ('lilac', r'lilac|fringe'),
    ('redbud', r'redbud'),
    ('crabapple', r'crab|malus|apple|hawthorn|crape|crepe|smoke|witch|parrotia|golden ?rain'),
    ('linden', r'linden|basswood|hornbeam|hophornbeam'),
    ('sweetgum', r'sweetgum|tulip|katsura|sassafras|blackgum|black gum|tupelo|persimmon'),
    ('holly', r'holly|\byew\b'),
    ('spruce', r'spruce|\bfir\b|hemlock'),
    ('pine', r'pine|cedar|juniper|arborvitae|cypress|cryptomeria|sequoia|redwood|larch'),
]
LOOKS = ['plane', 'redmaple', 'sugarmaple', 'cherry', 'pear', 'locust', 'redoak', 'pinoak', 'zelkova', 'ginkgo', 'lilac',
         'redbud', 'crabapple', 'linden', 'sweetgum', 'pine', 'elm',
         'magnolia', 'dogwood', 'serviceberry', 'silvermaple', 'crimsonking', 'sycamore', 'riverbirch', 'willow', 'spruce',
         'holly', 'broadleaf']


def look_of(name):
    for look, rx in LOOK_OF:
        if re.search(rx, name, re.I):
            return look
    return 'broadleaf'


def dehaze(a, view):
    """A winter image's haze. The model fills the gaps between the twigs with an opaque pale haze in place of
    transparency (50 to 75% of the covered pixels of 15 of the 18 winter images), and twigs are dark, so the crown is
    keyed on darkness: full under a luminance of 0.42, gone over 0.60. The trunk is spared, pale bark and all (the
    planetree's is cream), as a central column a fifth of the tree wide through its lowest 28%; a top view is all crown."""
    rgb, al = a[..., :3], a[..., 3]
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    dark = np.clip((0.60 - lum) / 0.18, 0, 1)
    if view == 'top':
        a[..., 3] = al * dark
        return a
    ys, xs = np.nonzero(al > 0.06)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    H, W = al.shape
    yy, xx = np.mgrid[0:H, 0:W]
    low = np.clip((yy - (y0 + (y1 - y0) * 0.72)) / ((y1 - y0) * 0.04), 0, 1)
    mid = np.clip(1 - (np.abs(xx - (x0 + x1) / 2) - (x1 - x0) * 0.10) / ((x1 - x0) * 0.03), 0, 1)
    # Round 184: the column spares bark, not haze: a near-white grey there (the willow's curtain of twigs left a white
    # blot at its foot) still goes; pale bark is a warm cream or a birch's pinkish white, saturation 0.18 and up
    sat = rgb.max(-1) - rgb.min(-1)
    haze = np.clip((lum - 0.78) / 0.08, 0, 1) * np.clip((0.08 - sat) / 0.04, 0, 1)
    trunk = low * mid * (1 - haze)
    a[..., 3] = al * (trunk + (1 - trunk) * dark)
    return a


def bleed(a, passes=24):
    """Run the colour of covered pixels out into the clear ones (four-neighbour average), alpha untouched."""
    rgb = a[..., :3] * (a[..., 3:4] > 0.02)
    w = (a[..., 3] > 0.02).astype(np.float32)
    for _ in range(passes):
        if w.min() > 0:
            break
        acc = np.zeros_like(rgb); n = np.zeros_like(w)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(rgb * w[..., None], dy, 0), dx, 1)
            n += np.roll(np.roll(w, dy, 0), dx, 1)
        fill = (w == 0) & (n > 0)
        rgb[fill] = acc[fill] / n[fill][:, None]
        w = np.where(fill, 1.0, w)
    a[..., :3] = rgb
    return a


def mute(a, sat, val):
    """Saturation toward the pixel's own luminance, then the value down, alpha untouched."""
    rgb = a[..., :3]
    lum = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])[..., None]
    a[..., :3] = np.clip((lum + (rgb - lum) * sat) * val, 0, 1)
    return a


def prep(path, view, season):
    a = np.asarray(Image.open(path).convert('RGBA'), np.float32) / 255.0
    if season == 'winter':
        a = dehaze(a, view)
    if season in MUTE:
        a = mute(a, *MUTE[season])
    al = a[..., 3]
    ys, xs = np.nonzero(al > 0.06)
    if not len(xs):
        raise ValueError('empty image ' + path)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    a = a[y0:y1, x0:x1]
    h, w = a.shape[:2]
    N = SIDE if view == 'side' else TOP
    inner = N - 4                                   # two pixels clear at each edge, for the mips
    k = inner / max(h, w)
    tw, th = max(1, round(w * k)), max(1, round(h * k))
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((tw, th), Image.LANCZOS)
    cell = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    ox = (N - tw) // 2
    oy = N - 2 - th if view == 'side' else (N - th) // 2     # a side view stands on the foot, a top view is centred
    cell.paste(im, (ox, oy))
    c = np.asarray(cell, np.float32) / 255.0
    c[..., 3] = np.clip((c[..., 3] - 0.08) / 0.55, 0, 1)    # firm: a fine twig at 0.3 passes the test, the faint edge goes
    c = bleed(c)
    out = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8))
    meta = {'hf': round(th / N, 4), 'ar': round(w / h, 4)} if view == 'side' else {'df': round(max(tw, th) / N, 4)}
    return out, meta


def art(im, name):
    """The image as a file under art/trees/ (Round 184, art_files), and a phone's copy at half."""
    half = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    return (art_files.write(im, 'trees', name, 'WEBP', quality=QUALITY, method=6, alpha_quality=90),
            art_files.write(half, 'trees', name + '-half', 'WEBP', quality=QUALITY, method=6, alpha_quality=90))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    names = json.load(open(os.path.join(HERE, 'tree_names.json')))
    images, total = {}, 0
    for look in LOOKS:
        d = os.path.join(RAW, look)
        for view in ('side', 'top'):
            for season in SEASONS:
                p = os.path.join(d, '%s-%s.png' % (view, season))
                if not os.path.exists(p):
                    continue
                im, meta = prep(p, view, season)
                full, half = art(im, '%s-%s-%s' % (look, view, season))
                total += art_files.size(full)
                images.setdefault(look, {}).setdefault(view, {})[season] = dict(meta, img=full, imgHalf=half)
                if a.preview:
                    os.makedirs(a.preview, exist_ok=True)
                    bg = Image.new('RGBA', im.size, (110, 130, 160, 255)); bg.alpha_composite(im)
                    bg.convert('RGB').save(os.path.join(a.preview, '%s-%s-%s.jpg' % (look, view, season)), quality=85)
    missing = [lk for lk in LOOKS if not (images.get(lk, {}).get('side', {}).get('summer') and images[lk].get('top', {}).get('summer'))]
    if missing:
        sys.exit('looks without a summer side and top: %s (run fetch_tree_art.py)' % ', '.join(missing))
    species_look = [LOOKS.index(look_of(n)) for n in names['names']]
    print('pruned %d old tree files' % art_files.prune('trees'))
    out = {'v': 2, 'looks': LOOKS, 'side': SIDE, 'top': TOP, 'speciesLook': species_look, 'images': images}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    n = sum(len(v) for lk in images.values() for v in lk.values())
    print('%d images, %d KB of WebP, wrote %s (%.2f MB)' % (n, total // 1024, OUT, os.path.getsize(OUT) / 1e6))
    from collections import Counter
    print('species per look:', dict(Counter(LOOKS[i] for i in species_look)))


if __name__ == '__main__':
    main()
