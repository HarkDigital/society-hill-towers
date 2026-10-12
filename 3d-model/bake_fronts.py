#!/usr/bin/env python3
"""Bake the house fronts (the facade prototype, Oct 12) into fronts.json, which build.py inlines as FRONTS_DATA.

Per set, the fronts made by fetch_fronts.py (lidar_cache/fronts_raw/<set>/<id>.png) are cut into an atlas of CELL-sized
cells (each front stretched to the cell, its edge pixels run out into a PAD gutter so the mips never bleed), and a mask
atlas in the same layout at a quarter of the size: r is the window glass, g a number per window (the page lights each
window by its number), b the door. The windows are found by their dark glass: the pixels well under the front's own
median, closed across the muntins, cut into connected blobs and kept when a blob is a filled, window-shaped box; a tall
dark box standing on the foot of the front is the door. RUNS are the street centrelines (scene frame) whose houses take
a set. --placeholder draws plain stand-in fronts instead (engine work only: they never ship, the bake says so).

Usage: python3 bake_fronts.py [--placeholder] [--preview DIR]   (--preview writes each front with its mask over it)"""
import argparse, base64, io, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'fronts_raw')
OUT = os.path.join(HERE, 'fronts.json')
CELL = (512, 1024)   # px per front in the atlas, 1:2; the page stretches a cell to the wall it dresses
PAD = 8
MASK_DIV = 2
COLS = 4

# one front's nominal width and wall height in metres: the page cuts a wider wall into round(width / w) fronts
SETS = {   # step: the stoop's colour (photo sRGB): marble in Society Hill, concrete and worn marble to the south
    'federal': {'w': 5.8, 'h': 11.0, 'gain': 0.88, 'step': '#e4e0d6'},    # Society Hill: three storeys and a half, three bays
    'southrow': {'w': 4.7, 'h': 7.8, 'gain': 0.88, 'step': '#bdb8ae'},    # South Philadelphia: two storeys, two bays
}
# street centrelines (scene frame, from the street labels: Spruce's at (-341, 53) bearing 9 degrees, Wilder's at
# (-1335, 1592) bearing 10, each run ending at its cross streets' centrelines)
RUNS = [
    {'set': 'federal', 'name': 'Spruce Street, 300 block', 'a': [-315.0, 57.1], 'b': [-177.0, 79.0]},
    {'set': 'southrow', 'name': 'Wilder Street, 900 block', 'a': [-1406.0, 1579.5], 'b': [-1268.0, 1603.8]},
]


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def erode(m, r):
    return ~dilate(~m, r)


def blobs(m):
    """Connected components of a boolean image (4-neighbour), as lists of (y, x) bounding boxes and pixel counts."""
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    out, n = [], 0
    for y0 in range(H):
        row = m[y0]
        for x0 in np.nonzero(row & (lab[y0] == 0))[0]:
            if lab[y0, x0]:
                continue
            n += 1
            stack = [(y0, x0)]
            lab[y0, x0] = n
            ys0 = ye = y0; xs0 = xe = x0; cnt = 0
            while stack:
                y, x = stack.pop()
                cnt += 1
                ys0 = min(ys0, y); ye = max(ye, y); xs0 = min(xs0, x); xe = max(xe, x)
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        stack.append((yy, xx))
            out.append((ys0, xs0, ye, xe, cnt))
    return out


def find_openings(img):
    """Windows and the door of one front, as fractions of its width and height from the top-left: (wins, door)."""
    # at half the generated size (768 x 1280): a muntin is about 2 px and the white frame between a shutter and its sash
    # about 5, so a 1 px close joins a sash's panes and leaves the shutters beside it apart
    W, H = 384, 640
    a = np.asarray(img.convert('RGB').resize((W, H), Image.BILINEAR), np.float32) / 255.0
    L = lum(a)
    med = float(np.median(L))
    # glass is darker than the wall and neutral or cool, where brick is warm: a dark red brick reads as dark as a pane
    # by brightness alone, so a pane is well under the median and no redder than a grey, or very dark whatever its hue
    # (measured on the first five: a sky-lit pane reads 0.16 to 0.2 against a 0.35 brick, so the bar is 0.85 of the
    # median, held to neutral colours; a painted shutter is green, never glass, and is left out whatever its darkness)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g - r > 0.025) & (g - b > 0.015)
    dark = (((L < 0.85 * med) & (r - b < 0.06)) | ((L < 0.3 * med) & (r - b < 0.12))) & ~green   # brick in deep shade stays red
    closed = erode(dilate(dark, 1), 1)
    cand, door = [], None
    for y0, x0, y1, x1, _ in blobs(closed):
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        if bw < W * 0.035 or bh < H * 0.05:   # an awning's shadow line, a sliver
            continue
        fill = dark[y0:y1 + 1, x0:x1 + 1].mean()
        if fill < 0.55 or bw / bh > 2.5 or (bh > H * 0.35 and y1 < H * 0.85) or y0 > H * 0.85:   # bands, lattices, basement grilles (a tall door on a two-storey front is no band)
            continue
        cand.append([x0, y0, x1, y1])
    # the door: the tallest dark opening reaching into the lowest third, taller than a sash (a stoop can lift it) and
    # clearly taller than the openings' usual height (a green or red door is not dark glass, and then no window stands in)
    hs = sorted(c[3] - c[1] for c in cand)
    typical = hs[len(hs) // 2] if hs else 0
    for c in cand:
        x0, y0, x1, y1 = c
        if y1 > H * 0.7 and (y1 - y0) > max(H * 0.15, typical * 1.15) and (x1 - x0) / (y1 - y0) < 0.7 and (door is None or y1 - y0 > door[3] - door[1]):
            door = c
    # a shutter is a narrow box with another box against its side at the same height (its sash, a frame away); a
    # narrow modern window stands clear of its neighbours
    def shutter(c):
        x0, y0, x1, y1 = c
        if (x1 - x0) / (y1 - y0) >= 0.36:
            return False
        gap = max(6, (x1 - x0) * 0.6)
        for o in cand:
            if o is c or o is door:
                continue
            over = min(y1, o[3]) - max(y0, o[1])
            if over > 0.3 * (y1 - y0) and (0 <= o[0] - x1 <= gap or 0 <= x0 - o[2] <= gap):   # a split sash covers half
                return True
        return False
    wins = [(c[0] / W, c[1] / H, (c[2] + 1) / W, (c[3] + 1) / H) for c in cand if c is not door and not shutter(c)]
    if door:
        door = (door[0] / W, door[1] / H, (door[2] + 1) / W, (door[3] + 1) / H)
    wins.sort(key=lambda b: (round(b[1] * 20), b[0]))
    return wins, door


def placeholder(set_, k):
    """A plain stand-in front (engine work only)."""
    rng = np.random.default_rng(1000 + k * 17 + (0 if set_ == 'federal' else 500))
    W, H = CELL
    bricks = [(150, 74, 56), (132, 66, 52), (168, 96, 70), (120, 70, 60), (190, 160, 130)]
    base = bricks[k % len(bricks)]
    a = np.zeros((H, W, 3), np.float32) + base
    a += rng.normal(0, 7, (H, W, 1))
    for y in range(0, H, 9):   # mortar courses
        a[y:y + 1] *= 0.82
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    floors = 3 if set_ == 'federal' else 2
    bays = 3 if set_ == 'federal' else 2
    top = int(H * 0.06)
    d.rectangle((0, 0, W, top), fill=(236, 232, 222))
    fh = (H - top - int(H * 0.08)) / floors
    for f in range(floors):
        for b in range(bays):
            if f == floors - 1 and b == (0 if k % 2 else bays - 1):
                cx = (b + 0.5) * W / bays
                d.rectangle((cx - W * 0.1, H - fh * 0.95, cx + W * 0.1, H - 12), fill=(30, 30, 34))
                continue
            cx, cy = (b + 0.5) * W / bays, top + (f + 0.5) * fh
            ww, wh = W * 0.16, fh * 0.55
            d.rectangle((cx - ww / 2 - 6, cy - wh / 2 - 6, cx + ww / 2 + 6, cy + wh / 2 + 6), fill=(236, 232, 222))
            d.rectangle((cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2), fill=(36, 44, 52))
            d.line((cx, cy - wh / 2, cx, cy + wh / 2), fill=(236, 232, 222), width=4)
            d.line((cx - ww / 2, cy, cx + ww / 2, cy), fill=(236, 232, 222), width=4)
    return im


def gutter(cell_img, W, H, pad):
    """The front shrunk into the cell inside the pad, its edge pixels run out across the gutter."""
    inner = cell_img.resize((W - 2 * pad, H - 2 * pad), Image.LANCZOS)
    a = np.asarray(inner)
    return Image.fromarray(np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode='edge'))


def data_url(im, fmt, **kw):
    b = io.BytesIO()
    im.save(b, fmt, **kw)
    mime = {'WEBP': 'image/webp', 'PNG': 'image/png', 'JPEG': 'image/jpeg'}[fmt]
    return 'data:%s;base64,%s' % (mime, base64.b64encode(b.getvalue()).decode('ascii'))


def bake_set(set_, fronts, preview):
    W, H = CELL
    n = len(fronts)
    rows = math.ceil(n / COLS)
    atlas = Image.new('RGB', (COLS * W, rows * H), (0, 0, 0))
    mW, mH, mP = W // MASK_DIV, H // MASK_DIV, PAD // MASK_DIV
    mask = Image.new('RGB', (COLS * mW, rows * mH), (0, 0, 0))
    cells = []
    for k, (fid, im) in enumerate(fronts):
        col, row = k % COLS, k // COLS
        atlas.paste(gutter(im.convert('RGB'), W, H, PAD), (col * W, row * H))
        wins, door = find_openings(im)
        m = Image.new('RGB', (mW, mH), (0, 0, 0))
        d = ImageDraw.Draw(m)
        iw, ih = mW - 2 * mP, mH - 2 * mP
        for j, (x0, y0, x1, y1) in enumerate(wins):
            d.rectangle((mP + x0 * iw, mP + y0 * ih, mP + x1 * iw - 1, mP + y1 * ih - 1), fill=(255, (j * 37 + 11) % 256, 0))
        if door:
            x0, y0, x1, y1 = door
            d.rectangle((mP + x0 * iw, mP + y0 * ih, mP + x1 * iw - 1, mP + y1 * ih - 1), fill=(0, 0, 255))
        mask.paste(m, (col * mW, row * mH))
        # the cornice's colour: the front's top 3% (the page projects a cornice of it along the wall's head)
        top = np.asarray(im.convert('RGB').resize((64, 200), Image.BILINEAR))[:6].reshape(-1, 3)
        cor = '#%02x%02x%02x' % tuple(int(v) for v in np.median(top, axis=0))
        cells.append({'id': fid, 'wins': len(wins), 'door': [round(v, 3) for v in door] if door else None, 'cornice': cor})
        if preview:
            v = im.convert('RGB').resize((W, H))
            o = ImageDraw.Draw(v)
            for x0, y0, x1, y1 in wins:
                o.rectangle((x0 * W, y0 * H, x1 * W, y1 * H), outline=(255, 220, 0), width=3)
            if door:
                o.rectangle((door[0] * W, door[1] * H, door[2] * W, door[3] * H), outline=(0, 200, 255), width=3)
            v.save(os.path.join(preview, '%s-%s.jpg' % (set_, fid)), quality=85)
    spec = SETS[set_]
    return {'img': data_url(atlas, 'WEBP', quality=82, method=6), 'mask': data_url(mask, 'PNG', optimize=True),
            'cols': COLS, 'rows': rows, 'cell': [W, H], 'pad': PAD, 'w': spec['w'], 'h': spec['h'], 'gain': spec['gain'],
            'step': spec['step'], 'cells': cells}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--placeholder', action='store_true')
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
    sets = {}
    for set_ in SETS:
        if a.placeholder:
            fronts = [('p%d' % k, placeholder(set_, k)) for k in range(8)]
        else:
            d = os.path.join(RAW, set_)
            names = sorted(f for f in os.listdir(d) if f.endswith('.png')) if os.path.isdir(d) else []
            fronts = [(os.path.splitext(f)[0], Image.open(os.path.join(d, f))) for f in names]
        if not fronts:
            sys.exit('no fronts for %s in %s (run fetch_fronts.py, or --placeholder for engine work)' % (set_, RAW))
        sets[set_] = bake_set(set_, fronts, a.preview)
        print('%-9s %d fronts, %d windows, %d doors, atlas %d KB, mask %d KB' % (
            set_, len(fronts), sum(c['wins'] for c in sets[set_]['cells']), sum(bool(c['door']) for c in sets[set_]['cells']),
            len(sets[set_]['img']) * 3 // 4 // 1024, len(sets[set_]['mask']) * 3 // 4 // 1024))
    out = {'v': 1, 'placeholder': a.placeholder, 'sets': sets, 'runs': RUNS}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.2f MB' % (os.path.getsize(OUT) / 1e6), '(placeholder)' if a.placeholder else '')


if __name__ == '__main__':
    main()
