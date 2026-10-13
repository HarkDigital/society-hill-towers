#!/usr/bin/env python3
"""Bake the vehicles' images (fetch_vehicle_art.py) into vehicle_art.json, which build.py inlines as VEHICLE_ART, and the
atlases themselves into art/vehicles/ (files the page loads on demand, a phone's copy at half; art_files.py).

Two atlases and their masks. The cars': each of the typical traffic's six kinds as a side, a plan, a front and a rear
view, every one cropped to the body (the plan and the end views lose the mirrors) and resampled to the kind's real
proportions, so the page can wrap it straight onto its own faces. The transit atlas: the SEPTA bus and trolley, Amtrak's
ACS-64, Acela power car and Amfleet coach and a PATCO car, as side, front and rear views, and a roof strip each made
from the side view's own roof line. A mask at half the atlas's size marks the paint (R, the cars only: they are painted
white and the page tints them), the glass (G) and the lamps (B).

Each vehicle also gets its profile: at STATIONS stations along its length, the silhouette's top and bottom (fractions
of the height), the body's bottom with the wheels taken out, the glass's lowest edge (the belt) and the plan's half
width, which the page lofts into the body; and its two wheels' centres and radius, which it builds as wheels. The plan
is warped along its length so its greenhouse lies over the side view's: two separate images of 'a generic sedan' put
the windscreen in different places, and the roof would wear the bonnet. The container stacks' two textures (the long
side and the doors) are written as they are, tiled across."""
import json, os, sys
import numpy as np
from PIL import Image
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'vehicle_art_raw')
OUT = os.path.join(HERE, 'vehicle_art.json')
STATIONS = 40
BELT_MIN = 0.56   # a car's glass never sits under 56% of its height: lower down the dark is tyres and arches (the van's 42%)
BELT_MIN_KIND = {'van': 0.42}
# the page's CAR_MODELS (l, w, h): the atlas is sized by them; the page scales the profiles by its own
CARS = [('compact', 3.85, 1.72, 1.46), ('sedan', 4.65, 1.82, 1.43), ('wagon', 4.8, 1.85, 1.55),
        ('suv', 4.85, 1.98, 1.86), ('pickup', 5.5, 2.02, 1.86), ('van', 5.65, 2.05, 2.48)]
# the tyres' real radii (m): the images give the wheels' places along the car but not a radius that survives the dark
# arches round them (every fit came out 10 to 40% large), so the radius is the kind's own
TYRE_R = {'compact': 0.31, 'sedan': 0.33, 'wagon': 0.33, 'suv': 0.37, 'pickup': 0.40, 'van': 0.36}
# transit: id, length, width, height (m), the views it has; a missing rear takes the front
TRANSIT = [('bus', 12.2, 2.6, 3.1, ('front', 'rear')), ('trolley', 15.3, 2.6, 3.4, ('front',)),
           ('acs64', 20.3, 3.0, 4.3, ('front',)), ('acela', 21.0, 3.1, 4.2, ('front',)),
           ('amfleet', 25.9, 3.05, 4.0, ()), ('patco', 20.4, 3.1, 3.9, ('front',))]
CAR_PX = 300     # a car's side view is this many px tall in the full atlas, before any shrink to fit
TRANSIT_PX = 220
PAD = 6
ATLAS = 2048


def load(vid):
    p = os.path.join(RAW, vid + '.png')
    if not os.path.exists(p):
        sys.exit('no %s (run fetch_vehicle_art.py)' % p)
    return np.asarray(Image.open(p).convert('RGBA'), np.float32) / 255.0


def crop_alpha(a, thr=0.5):
    m = a[..., 3] > thr
    rows = np.where(m.sum(1) >= 3)[0]
    cols = np.where(m.sum(0) >= 3)[0]
    return a[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


def hsv(a):
    rgb = a[..., :3]
    v = rgb.max(-1)
    s = (v - rgb.min(-1)) / np.maximum(v, 1e-4)
    return v, s


def smooth1(x, k=3):
    x = np.asarray(x, np.float32)
    if k <= 1:
        return x
    pad = np.pad(x, (k // 2, k // 2), mode='edge')
    return np.array([np.median(pad[i:i + k]) for i in range(len(x))], np.float32)


def silhouette(a, thr=0.5):
    """Per column: the first and last opaque row (top, bottom), -1 where the column is empty."""
    m = a[..., 3] > thr
    H, W = m.shape
    any_ = m.any(0)
    top = np.where(any_, m.argmax(0), -1)
    bot = np.where(any_, H - 1 - m[::-1].argmax(0), -1)
    return top, bot


def stations_of(W):
    return [(i / (STATIONS - 1)) * (W - 1) for i in range(STATIONS)]


def window(W, c):
    h = max(1, int(round(W / (2 * STATIONS))))
    return max(0, int(c) - h), min(W, int(c) + h + 1)


def glass_mask(a):
    v, s = hsv(a)
    return np.clip((0.34 - v) / 0.12, 0, 1) * np.clip((0.5 - s) / 0.2, 0, 1) * (a[..., 3] > 0.5)


def paint_mask(a):
    v, s = hsv(a)
    return np.clip((v - 0.55) / 0.15, 0, 1) * np.clip((0.2 - s) / 0.1, 0, 1)


def grow(m, n):
    """A float mask grown by n px (4-neighbour max)."""
    for _ in range(n):
        m = np.maximum.reduce([m, np.roll(m, 1, 0), np.roll(m, -1, 0), np.roll(m, 1, 1), np.roll(m, -1, 1)])
    return m


def seam_paint(a, p, g):
    """The paint mask taken over the panel gaps and the paint's soft edges: the light, unsaturated texels within 3 px of
    the paint that are not glass. Left out, they kept the white the cars were painted, and every dark car on the page wore
    white lines along its doors and its outline."""
    v, s = hsv(a)
    near = grow(p, 3) * np.clip((v - 0.3) / 0.15, 0, 1) * np.clip((0.3 - s) / 0.1, 0, 1) * (1 - g)
    return np.maximum(p, near)


def lamp_mask(a, front):
    v, s = hsv(a)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    red = np.clip((s - 0.45) / 0.2, 0, 1) * (r > g * 1.6) * (r > b * 1.6) * (v > 0.35)
    return red if not front else np.zeros_like(v)


def profile_side(a, wheels_expected=True, tyre=None, belt_min=BELT_MIN):
    """The side view's silhouette at the stations, the wheels and the body's bottom without them."""
    H, W = a.shape[:2]
    top, bot = silhouette(a)
    g = glass_mask(a)
    yT, yB, belt = [], [], []
    for c in stations_of(W):
        c0, c1 = window(W, c)
        t = top[c0:c1]; b = bot[c0:c1]
        t = t[t >= 0]; b = b[b >= 0]
        if not len(t):
            yT.append(0.0); yB.append(0.0); belt.append(-1.0); continue
        tt, bb = float(np.min(t)), float(np.max(b))
        yT.append(1 - tt / (H - 1)); yB.append(1 - bb / (H - 1))
        # the glass's lowest edge in the upper part of the column (the tyres are dark too, low down)
        lim = int(min(tt + 0.62 * (bb - tt), (1 - belt_min) * (H - 1)))
        col = g[int(tt):lim, c0:c1].mean(1) if lim > tt else np.zeros(0)
        rows = np.where(col > 0.45)[0]
        belt.append(1 - (tt + rows[-1]) / (H - 1) if len(rows) >= 3 else -1.0)
    wheels = []
    if wheels_expected:
        contact = (bot >= (H - 1) - 0.025 * H) & (bot >= 0)
        runs, c = [], 0
        while c < W:
            if contact[c]:
                c0 = c
                while c < W and (contact[c] or (c + 3 < W and contact[c:c + 4].any())):
                    c += 1
                runs.append((c0, c - 1))
            c += 1
        runs = sorted(sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:2])
        for (r0, r1) in runs:
            cx = (r0 + r1) / 2
            # beside the contact patch the silhouette's bottom is the tyre's own arc, up to where the tyre meets the
            # body's skirt: y = r - sqrt(r^2 - dx^2), so r = (dx^2 + y^2) / 2y from every column whose lift is small
            est = []
            for c in range(max(0, int(cx - 0.4 * H)), min(W, int(cx + 0.4 * H))):
                if bot[c] < 0:
                    continue
                yb = (H - 1) - bot[c]
                if 3 <= yb <= 0.11 * H:
                    dx = c - cx
                    est.append((dx * dx + yb * yb) / (2 * yb))
            rad = float(np.median(est)) if len(est) >= 6 else 0.23 * H
            rad = float(np.clip(rad, 0.15 * H, 0.32 * H)) if tyre is None else tyre * (H - 1)
            wheels.append([round(cx / (W - 1), 4), round(rad / (H - 1), 4)])
    # the body's bottom: the silhouette's, except over a wheel, where it is the sill between the wheels
    xs = np.array([i / (STATIONS - 1) for i in range(STATIONS)])
    yB = np.array(yB, np.float32)
    bodyB = yB.copy()
    if len(wheels) == 2:
        L, Hh = W - 1, H - 1
        near = np.zeros(STATIONS, bool)
        for wx, wr in wheels:
            near |= np.abs(xs - wx) * L < 1.12 * wr * Hh
        mid = (xs > wheels[0][0]) & (xs < wheels[1][0]) & ~near
        sill = float(np.median(yB[mid])) if mid.any() else 0.18
        bodyB = np.where(near, np.maximum(yB, sill), yB)
        bodyB = np.maximum(bodyB, np.where(near, sill, 0))
    return {'yT': smooth1(yT, 3), 'yB': yB, 'bodyB': bodyB, 'belt': smooth1(belt, 5), 'wheels': wheels}


def glass_profile(g, lo=0.0, hi=1.0):
    H, W = g.shape
    f = g[int(lo * H):int(hi * H)].mean(0)
    k = max(3, W // 60)
    return np.convolve(f, np.ones(k) / k, mode='same')


def span(f, thr):
    idx = np.where(f > thr)[0]
    if len(idx) < 3:
        return None
    return idx[0] / (len(f) - 1), idx[-1] / (len(f) - 1)


def warp_x(a, src_knots, dst_knots):
    """Resample columns so that a feature at dst_knots[i] (fraction) comes from src_knots[i] (fraction)."""
    H, W = a.shape[:2]
    u = np.linspace(0, 1, W)
    s = np.interp(u, dst_knots, src_knots) * (W - 1)
    s0 = np.clip(np.floor(s).astype(int), 0, W - 1)
    s1 = np.clip(s0 + 1, 0, W - 1)
    t = (s - s0)[None, :, None]
    return a[:, s0] * (1 - t) + a[:, s1] * t


def top_view(a, side, pickup=False):
    """The plan, its rows cropped to the body's width, warped so its greenhouse lies over the side view's."""
    a = crop_alpha(a)
    H, W = a.shape[:2]
    top, bot = silhouette(a)
    ok = (top >= 0)
    half = np.where(ok, (bot - top) / 2.0, 0)
    cen = np.where(ok, (bot + top) / 2.0, H / 2)
    mid = slice(int(0.15 * W), int(0.85 * W))
    body = float(np.median(half[mid]))
    cz = float(np.median(cen[mid]))
    r0, r1 = int(round(cz - body)), int(round(cz + body)) + 1
    padr = max(0, -r0), max(0, r1 - H)
    a = np.pad(a, ((padr[0], padr[1]), (0, 0), (0, 0)))
    r0 += padr[0]; r1 += padr[0]
    a = a[r0:r1]
    # the roof's two edges in each view: in the side, where the silhouette stands within 3.5% of its full height; in
    # the plan, the windscreen's back edge (the front-most dark run across the centre band) and the edge of the dark run
    # behind it (the rear window; the van has none, the pickup's bed is not looked at)
    Hs, Ws = side.shape[:2]
    stp, _ = silhouette(side)
    roofc = np.where((stp >= 0) & (stp <= stp[stp >= 0].min() + 0.035 * Hs))[0]
    ss = (roofc[0] / (Ws - 1), roofc[-1] / (Ws - 1)) if len(roofc) > 3 else None
    v, _ = hsv(a)
    Hc = a.shape[0]
    band = ((v < 0.3) & (a[..., 3] > 0.5))[int(0.3 * Hc):int(0.7 * Hc)].mean(0)
    k = max(3, W // 80)
    band = np.convolve(band, np.ones(k) / k, mode='same')
    lo = int((0.42 if pickup else 0.04) * W)
    runs, c = [], lo
    while c < int(0.96 * W):
        if band[c] > 0.5:
            c0 = c
            while c < int(0.96 * W) and band[c] > 0.5:
                c += 1
            if c - c0 >= 0.02 * W:
                runs.append((c0, c - 1))
        c += 1
    st = None
    if runs:
        ws = runs[-1]
        behind = [r for r in runs[:-1] if r[1] < ws[0]]
        st = ((behind[-1][1] if behind else 0.03 * W) / (W - 1), ws[0] / (W - 1))
    warped = False
    # only the windscreen's top is pinned: the roof's back edge is a gentle slope in a side view and no edge at all on a
    # hatch, and it was the windscreen landing on the roof (or the bonnet on the glass) that showed
    if ss and st and 0.2 < st[1] < 0.97:
        a2 = [0, st[1], 1]; b2 = [0, ss[1], 1]
        ratios = [(b2[i + 1] - b2[i]) / max(1e-3, a2[i + 1] - a2[i]) for i in range(2)]
        if all(0.6 < r < 1.6 for r in ratios):
            a = warp_x(a, a2, b2)
            warped = True
    # the plan's half width at the stations, as a fraction of the body's half width (mirrors clipped)
    H2, W2 = a.shape[:2]
    t2, b2 = silhouette(a)
    hw = []
    for c in stations_of(W2):
        c0, c1 = window(W2, c)
        tt, bb = t2[c0:c1], b2[c0:c1]
        okk = tt >= 0
        if not okk.any():
            hw.append(0.3); continue
        hw.append(float(min(1.0, np.median((bb[okk] - tt[okk]) / 2.0) / (H2 / 2.0))))
    return a, smooth1(hw, 3), warped, (ss, st)


def end_view(a):
    """A front or rear view cropped across to the body's width (the mirrors fall outside)."""
    a = crop_alpha(a)
    H, W = a.shape[:2]
    m = a[..., 3] > 0.5
    widths, cens = [], []
    for row in range(int(H * 0.5), int(H * 0.92)):
        cols = np.where(m[row])[0]
        if len(cols):
            widths.append((cols[-1] - cols[0]) / 2.0); cens.append((cols[-1] + cols[0]) / 2.0)
    body = float(np.percentile(widths, 80)) if widths else W / 2
    cz = float(np.median(cens)) if cens else W / 2
    c0, c1 = int(round(cz - body)), int(round(cz + body)) + 1
    padc = max(0, -c0), max(0, c1 - W)
    a = np.pad(a, ((0, 0), (padc[0], padc[1]), (0, 0)))
    return a[:, c0 + padc[0]:c1 + padc[0]]


def erode(m, n):
    """A mask shrunk by n px (4-neighbour)."""
    for _ in range(n):
        m = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1)
    return m


def fill_clear(a, under=None, shrink=3):
    """Transparent texels take the nearest opaque colour (so filtering and the mips never meet the void); under a given
    row fraction they take a dark undercarriage instead. The silhouette's own rim is taken in by `shrink` px first: the
    generator's matte leaves a light fringe there, which the page drew as a white outline round a dark car."""
    rgb = a[..., :3].copy()
    al = erode(a[..., 3] > 0.5, shrink)
    if under is not None:
        H = a.shape[0]
        rows = np.arange(H)[:, None] >= int(under * H)
        rgb[~al & rows] = 0.07
        al = al | rows
    # repeated dilation by shifting: cheap and good enough for a few hundred px
    filled = al.copy()
    for _ in range(64):
        if filled.all():
            break
        nb_rgb = np.zeros_like(rgb); nb_n = np.zeros(rgb.shape[:2], np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(filled, (dy, dx), (0, 1))
            sr = np.roll(rgb, (dy, dx), (0, 1))
            nb_rgb += sr * sh[..., None]; nb_n += sh
        grow = (~filled) & (nb_n > 0)
        rgb[grow] = nb_rgb[grow] / nb_n[grow][:, None]
        filled |= grow
    return rgb


def resize(arr, w, h):
    if arr.ndim == 2:
        im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
        return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255
    im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255


def pack(items, size, scale0):
    """Shelf packing of (key, rgb, mask, w, h) at a scale that fits; returns placements and the scale."""
    scale = scale0
    while True:
        rects = [(k, max(8, int(w * scale)), max(8, int(h * scale))) for k, w, h in items]
        order = sorted(range(len(rects)), key=lambda i: -rects[i][2])
        x = y = shelf = 0
        place = {}
        ok = True
        for i in order:
            k, w, h = rects[i]
            if w + 2 * PAD > size:
                ok = False; break
            if x + w + 2 * PAD > size:
                x = 0; y += shelf; shelf = 0
            if y + h + 2 * PAD > size:
                ok = False; break
            place[k] = (x + PAD, y + PAD, w, h)
            x += w + 2 * PAD; shelf = max(shelf, h + 2 * PAD)
        if ok:
            return place, scale
        scale *= 0.94


def compose(place, imgs, size):
    rgb = np.zeros((size, size, 3), np.float32)
    msk = np.zeros((size, size, 3), np.float32)
    for k, (x, y, w, h) in place.items():
        c, m = imgs[k]
        c = resize(c, w, h); m = np.stack([resize(m[..., i], w, h) for i in range(3)], -1)
        # each rect is padded with its own edge, so bilinear filtering and the first mips never meet a neighbour
        cp = np.pad(c, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='edge')
        mp = np.pad(m, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='edge')
        rgb[y - PAD:y + h + PAD, x - PAD:x + w + PAD] = cp
        msk[y - PAD:y + h + PAD, x - PAD:x + w + PAD] = mp
    return rgb, msk


def rect_of(place, k, size):
    x, y, w, h = place[k]
    return [round(x / size, 6), round(y / size, 6), round((x + w) / size, 6), round((y + h) / size, 6)]


def write_atlas(name, rgb, msk, out):
    im = Image.fromarray(np.clip(rgb * 255, 0, 255).astype(np.uint8))
    mk = Image.fromarray(np.clip(msk * 255, 0, 255).astype(np.uint8))
    S = im.size[0]
    out['atlas'] = art_files.write(im, 'vehicles', name, 'WEBP', quality=86, method=6)
    out['atlasHalf'] = art_files.write(im.resize((S // 2, S // 2), Image.LANCZOS), 'vehicles', name + '-half', 'WEBP', quality=84, method=6)
    # lossless: a lossy WebP's chroma bleeds one channel into the next at every edge (the lamp channel lit red outlines by night)
    out['mask'] = art_files.write(mk.resize((S // 2, S // 2), Image.LANCZOS), 'vehicles', name + '-mask', 'WEBP', lossless=True, quality=100, method=6)
    out['maskHalf'] = art_files.write(mk.resize((S // 4, S // 4), Image.LANCZOS), 'vehicles', name + '-mask-half', 'WEBP', lossless=True, quality=100, method=6)
    print('%-8s atlas %d KB, half %d KB, mask %d KB' % (name, art_files.size(out['atlas']) // 1024, art_files.size(out['atlasHalf']) // 1024, art_files.size(out['mask']) // 1024))


def rnd(v, n=4):
    return [round(float(x), n) for x in v]


def cars():
    items, imgs, kinds = [], {}, []
    for cid, l, w, h in CARS:
        side = crop_alpha(load(cid + '_side'))
        Hs, Ws = side.shape[:2]
        asp = (Ws / Hs) / (l / h)
        if abs(asp - 1) > 0.15:
            print('  %s side: aspect %.2f of the real one (re-roll it with fetch_vehicle_art.py --force --only %s_side)' % (cid, asp, cid))
        bm = BELT_MIN_KIND.get(cid, BELT_MIN)
        prof = profile_side(side, tyre=TYRE_R[cid] / h, belt_min=bm)
        top, hw, warped, spans = top_view(load(cid + '_top'), side, pickup=(cid == 'pickup'))
        front = end_view(load(cid + '_front'))
        rear = end_view(load(cid + '_rear'))
        # masks: paint (R), glass (G, gated to where glass can be), lamps (B)
        def masks(a, gate=None, front_end=None):
            g = glass_mask(a)
            if gate is not None:
                g = g * gate
            lm = lamp_mask(a, front_end) if front_end is not None else np.zeros(a.shape[:2], np.float32)
            p = seam_paint(a, paint_mask(a) * (a[..., 3] > 0.5), g) * (a[..., 3] > 0.5)
            return np.stack([p, g, lm], -1)
        Hs, Ws = side.shape[:2]
        st, sb = silhouette(side)
        rows = np.arange(Hs)[:, None]
        upper = ((rows < (st + 0.62 * (sb - st))[None, :]) & (rows < (1 - bm) * (Hs - 1))).astype(np.float32)
        Ht = top.shape[0]
        rr = np.arange(Ht)[:, None] / max(1, Ht - 1)
        gate_top = ((rr > 0.1) & (rr < 0.9)).astype(np.float32) * np.ones((1, top.shape[1]))
        if cid == 'pickup':
            gate_top[:, :int(0.42 * top.shape[1])] = 0
        def gate_end(a):
            H = a.shape[0]
            r = np.arange(H)[:, None] / max(1, H - 1)
            return ((r > 0.06) & (r < 0.5)).astype(np.float32) * np.ones((1, a.shape[1]))
        def filled(a):
            f = fill_clear(a)
            return f, np.concatenate([f, np.ones(a.shape[:2] + (1,), np.float32)], -1)
        for key, a, gate, fe in (('side', side, upper, None), ('top', top, gate_top, None), ('front', front, gate_end(front), True), ('rear', rear, gate_end(rear), False)):
            f, fa = filled(a)
            imgs[cid + ':' + key] = (f, masks(fa, gate, fe))
        # the paint's own white, linear, so the page can tint it to any colour
        pm = paint_mask(side) * (side[..., 3] > 0.5)
        lin = np.where(side[..., :3] <= 0.04045, side[..., :3] / 12.92, ((side[..., :3] + 0.055) / 1.055) ** 2.4)
        ref = float((lin.mean(-1) * pm).sum() / max(1, pm.sum()))
        px = CAR_PX
        items += [(cid + ':side', px * l / h, px), (cid + ':top', px * l / h, px * w / h),
                  (cid + ':front', px * w / h, px), (cid + ':rear', px * w / h, px)]
        kinds.append({'id': cid, 'paintRef': round(ref, 4), 'wheels': prof['wheels'],
                      'prof': [rnd([prof['yT'][i], prof['yB'][i], prof['bodyB'][i], prof['belt'][i], hw[i]]) for i in range(STATIONS)],
                      'warped': warped})
        print('%-8s wheels %s, paint white %.3f, plan warped %s %s' % (cid, prof['wheels'], ref, warped,
              'side %.2f-%.2f plan %.2f-%.2f' % (spans[0] + spans[1]) if spans[0] and spans[1] else ''))
    place, scale = pack(items, ATLAS, 1.0)
    print('cars atlas scale %.3f' % scale)
    rgb, msk = compose(place, imgs, ATLAS)
    out = {'size': ATLAS}
    write_atlas('cars', rgb, msk, out)
    for k in kinds:
        for v in ('side', 'top', 'front', 'rear'):
            k[v] = rect_of(place, k['id'] + ':' + v, ATLAS)
    out['kinds'] = kinds
    return out


def transit():
    items, imgs, kinds = [], {}, []
    for tid, l, w, h, views in TRANSIT:
        side = crop_alpha(load(tid + '_side'))
        Hs, Ws = side.shape[:2]
        asp = (Ws / Hs) / (l / h)
        if abs(asp - 1) > 0.15:
            print('  %s side: aspect %.2f of the real one' % (tid, asp))
        prof = profile_side(side, wheels_expected=False)   # a bus's or a train's wheels are painted on its skirt
        # the roof line: pods, pantographs and trolley poles stand over it and are cut off (the page draws a box roof)
        yT = np.array(prof['yT'])
        roof = float(np.percentile(yT[int(0.1 * STATIONS):int(0.9 * STATIONS)], 30))
        cut = int(round((1 - roof) * (Hs - 1))) - 2
        body = side[max(0, cut):]
        Hb = body.shape[0]
        g = glass_mask(body)
        st, sb = silhouette(body)
        rows = np.arange(Hb)[:, None]
        upper = (rows < int(0.72 * Hb)).astype(np.float32) * np.ones((1, body.shape[1]))
        mk = np.stack([np.zeros_like(g), g * upper, lamp_mask(body, False)], -1)
        fb = fill_clear(body, under=0.86)
        mk = np.stack([np.zeros_like(g), glass_mask(np.concatenate([fb, np.ones(fb.shape[:2] + (1,), np.float32)], -1)) * upper, mk[..., 2]], -1)
        imgs[tid + ':side'] = (fb, mk)
        # the roof strip: each column's colour a few px under its own roof line
        cols = []
        for c in range(body.shape[1]):
            t = st[c] if st[c] >= 0 else 0
            cols.append(body[min(Hb - 1, t + 4), c, :3])
        strip = np.repeat(np.array(cols)[None], 32, 0) * 0.92
        imgs[tid + ':roof'] = (strip, np.zeros(strip.shape[:2] + (3,), np.float32))
        hb = h * (1 - (1 - roof))   # the body's own height under the roof line
        px = TRANSIT_PX
        items += [(tid + ':side', px * l / h, px), (tid + ':roof', px * l / h, px * 0.25)]
        ends = {}
        for v in views:
            e = end_view(load(tid + '_' + v))
            He = e.shape[0]
            r = np.arange(He)[:, None] / max(1, He - 1)
            gate = ((r > 0.1) & (r < 0.55)).astype(np.float32) * np.ones((1, e.shape[1]))
            fe = fill_clear(e, under=0.9)
            fea = np.concatenate([fe, np.ones(fe.shape[:2] + (1,), np.float32)], -1)
            imgs[tid + ':' + v] = (fe, np.stack([np.zeros(e.shape[:2], np.float32), glass_mask(fea) * gate, np.zeros(e.shape[:2], np.float32)], -1))
            items.append((tid + ':' + v, px * w / h, px))
        # the profile under the roof line, as fractions of the body's height
        yTb = np.minimum(yT, roof) / roof
        kinds.append({'id': tid, 'roof': round(roof, 4), 'prof': [rnd([yTb[i], prof['yB'][i] / roof]) for i in range(STATIONS)], 'views': list(views)})
        print('%-8s roof line %.3f of the side view, ends %s' % (tid, roof, ','.join(views) or 'none'))
    place, scale = pack(items, ATLAS, 1.0)
    print('transit atlas scale %.3f' % scale)
    rgb, msk = compose(place, imgs, ATLAS)
    out = {'size': ATLAS}
    write_atlas('transit', rgb, msk, out)
    for k in kinds:
        for v in ['side', 'roof'] + k['views']:
            k[v] = rect_of(place, k['id'] + ':' + v, ATLAS)
        if 'rear' not in k['views'] and 'front' in k['views']:
            k['rear'] = k['front']
    out['kinds'] = kinds
    return out


def containers():
    out = {}
    for vid, key in (('containers_side', 'side'), ('containers', 'end')):
        p = os.path.join(RAW, vid + '.png')
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGB')
        a = np.asarray(im.resize((1024, 512) if key == 'side' else (512, 512), Image.LANCZOS), np.float32)
        # across the tile's width the two ends meet: cross-fade the outer 24 px so the stack repeats along a hull
        k = 24
        wgt = np.linspace(0.5, 0.0, k)[None, :, None]
        left, right = a[:, :k].copy(), a[:, -k:][:, ::-1].copy()
        a[:, :k] = left * (1 - wgt) + right * wgt
        a[:, -k:] = (right * (1 - wgt) + left * wgt)[:, ::-1]
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        out[key] = art_files.write(im, 'vehicles', 'containers-' + key, 'WEBP', quality=82, method=6)
        out[key + 'Half'] = art_files.write(im.resize((im.size[0] // 2, im.size[1] // 2), Image.LANCZOS), 'vehicles', 'containers-' + key + '-half', 'WEBP', quality=80, method=6)
    # the side tile is two boxes long and as many tiers as the image drew: the page lays it by the box
    out['boxesAcross'] = 2
    out['tiers'] = 7
    return out


def main():
    out = {'stations': STATIONS, 'cars': cars(), 'transit': transit(), 'containers': containers()}
    print('pruned %d old vehicle files' % art_files.prune('vehicles'))
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    print('wrote', OUT, '%.1f KB' % (os.path.getsize(OUT) / 1e3))


if __name__ == '__main__':
    main()
