#!/usr/bin/env python3
"""Bake the glass towers' curtain walls and rooms (Round 192, Mike: "Can we also update the glass textures of the
skyscrapers that are glass?") into glass_art.json, which build.py inlines as GLASS_ART, and the atlases themselves into
art/glass/ (art_files.py: files the page loads on demand, a phone's half copies beside them).

The systems are glass_systems.json's sixteen (hand-authored from the references: each system's bay, floor, module, glass
optics, spandrel and rooms), copied into the manifest whole with the towers and the generic kinds, so the page reads one
object. The art:

- frames: fetch_glass_art.py's elevations (lidar_cache/glass_art_raw/frames/<sys>.png), every vision pane a flat
  chroma-key green and every opaque spandrel or railing pane a flat magenta. The key is a soft matte (green over the other
  channels from 0.25 to 0.6, its anti-aliased edge kept), the image's own repeat found both ways (the strongest repeat of
  the glass profile near the system's module: nbM bays by nfM floors) and every repeat folded into one module, the mean of
  all of them (so a blemish averages out and the module is exactly periodic), started at a mullion's middle and at the
  foot of a vision band (the floor line: a floor is its vision glass with the spandrel over it), resampled to 64 pixels a
  metre (a cell at most 512 a side). A fold whose repeats disagree, or a key that leaks into the frame, is refused.
  The albedo's keyed pixels are filled by a push-pull of the frame round them (no green in any mip); the one atlas, an
  opaque RGB PNG (never RGBA: WebKit's premultiplied decode), holds r the vision glass, g the secondary glass (the
  spandrel's or the railing's), b the frame's detail (its luminance over twice the frame's mean: the page multiplies the
  system's frame colour by twice it, so a fragment makes one fetch; the albedo itself is written only to --preview). Measured per cell: the vision band's sill and head
  (fractions of a floor), the vision and secondary coverage and the frame's mean colour (linear), which the page draws in
  place of the texture where a pane is under three pixels.
- rooms: eight interiors through /v1/images/edits on the one-point perspective template room_template draws (the back wall
  a centred rectangle at B_SCALE of the image, so the page's interior mapping knows where every face lies); each checked
  against the template (the back wall's four edges within 3% of where they were drawn), with its day mean (the picture at a
  quarter, a room by daylight) and its lit mean. The model keeps the view but not the back wall's size, so each room's
  back wall is measured (BACK) and the page projects through its own scale and vanishing point.

Shelf-packed into a 2048 x 1024 frame atlas (gutters filled by wrapping the cell, so a sample past its edge is the
module's own continuation) and a 1536 x 1152 room atlas (cells 384 x 576), each with a half copy for a phone.

Usage: python3 bake_glass_art.py [--preview DIR] [--template OUT.png]"""
import argparse, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'glass_art_raw')
SYSTEMS = os.path.join(HERE, 'glass_systems.json')
OUT = os.path.join(HERE, 'glass_art.json')
PXM = 64            # atlas pixels a metre
CELL_MAX = 512
PAD = 8
AW, AH = 2048, 1024
RW, RH, RCW, RCH = 1536, 1152, 384, 576   # the room atlas and its cells
B_SCALE = 0.5       # the template's back wall, a fraction of the picture each way
KEY_LO, KEY_HI = 0.25, 0.6
MUDDY = 0.16        # a fold is refused when its repeats' masks disagree by more than this on average
# the rooms' back walls as the model drew them, [x0, y0, x1, y1] in fractions of the picture from its top-left, read by eye
# off a 20 by 20 grid: the edit keeps the template's one-point view and its vanishing point near the centre but not the back
# wall's size (an open office it drew three widths deep, a bedroom one), so each cell carries its own scale across and up
# and its vanishing point, and the page's interior mapping projects through them (back_wall_check measures the drift)
BACK = {'office-a': [0.325, 0.40, 0.68, 0.55], 'office-b': [0.365, 0.36, 0.64, 0.52], 'office-c': [0.28, 0.245, 0.725, 0.725],
        'office-d': [0.21, 0.31, 0.78, 0.73], 'home-a': [0.24, 0.34, 0.77, 0.70], 'home-b': [0.23, 0.255, 0.77, 0.68],
        'hotel-a': [0.18, 0.33, 0.81, 0.68], 'mech-a': [0.35, 0.37, 0.65, 0.52]}


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def keys(rgb):
    """The two soft mattes of an sRGB float image: the green key (vision glass) and the magenta key (secondary glass)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    gk = np.clip((g - np.maximum(r, b) - KEY_LO) / (KEY_HI - KEY_LO), 0, 1)
    mk = np.clip((np.minimum(r, b) - g - KEY_LO) / (KEY_HI - KEY_LO), 0, 1)
    return gk, mk


def period(profile, expect, lo=0.75, hi=1.33):
    """The strongest repeat of a 1D profile within lo to hi times the expected one, refined to a fraction of a pixel by a
    parabola through the peak, or None."""
    p = profile - profile.mean()
    n = len(p)
    cs = {}
    for lag in range(max(4, int(expect * lo) - 1), min(n - 8, int(expect * hi) + 2) + 1):
        cs[lag] = float(np.dot(p[:-lag], p[lag:])) / (n - lag)
    lags = [l for l in cs if int(expect * lo) <= l <= int(expect * hi) + 1]
    if not lags:
        return None
    best = max(lags, key=lambda l: cs[l])
    if cs[best] <= 0.05 * float(np.dot(p, p)) / n:
        return None
    a, b, c = cs.get(best - 1, cs[best]), cs[best], cs.get(best + 1, cs[best])
    den = a - 2 * b + c
    off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return best + max(-0.5, min(0.5, off))


def bilinear(img, x, y):
    """img sampled at float pixel centres (x, y) (arrays), clamped at the borders."""
    H, W = img.shape[:2]
    x = np.clip(x - 0.5, 0, W - 1.001)
    y = np.clip(y - 0.5, 0, H - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    if img.ndim == 3:
        fx, fy = fx[..., None], fy[..., None]
    a, b = img[y0, x0], img[y0, x0 + 1]
    c, d = img[y0 + 1, x0], img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fold(stack, x0, y0, pw, ph, ow, oh, shifts=None):
    """Every whole repeat of the (pw by ph pixel) module starting at (x0, y0), each resampled to ow by oh (moved by its own
    shift in source pixels when given): returns the list and each repeat's origin."""
    H, W = stack.shape[:2]
    gx = (np.arange(ow) + 0.5) / ow * pw
    gy = (np.arange(oh) + 0.5) / oh * ph
    X, Y = np.meshgrid(gx, gy)
    reps, org = [], []
    k = 0
    while x0 + (k + 1) * pw <= W + 0.5:
        m = 0
        while y0 + (m + 1) * ph <= H + 0.5:
            dx, dy = shifts[len(reps)] if shifts else (0.0, 0.0)
            reps.append(bilinear(stack, X + x0 + k * pw + dx, Y + y0 + m * ph + dy))
            org.append((k, m))
            m += 1
        k += 1
    return reps, org


def align(stack, x0, y0, pw, ph, ow, oh, ch, rounds=2, r=6):
    """Each repeat's own shift (whole source pixels within r each way) that best matches the mean of all of them on the
    channels ch (the glass mattes), twice over: the model never draws two bays exactly alike, and a global period alone
    blurred every mullion by its drift across the picture."""
    reps, _ = fold(stack, x0, y0, pw, ph, ow, oh)
    shifts = [(0.0, 0.0)] * len(reps)
    sx, sy = ow / pw, oh / ph   # output pixels a source pixel
    for _ in range(rounds):
        ref = np.mean([q[..., ch].sum(-1) for q in reps], axis=0)
        ref = ref - ref.mean()
        new = []
        for q, (dx0, dy0) in zip(reps, shifts):
            g = q[..., ch].sum(-1)
            g = g - g.mean()
            best, bd = -1e18, (0, 0)
            for ddy in range(-r, r + 1):
                for ddx in range(-r, r + 1):
                    c = float((np.roll(np.roll(g, -int(round(ddy * sy)), 0), -int(round(ddx * sx)), 1) * ref).sum())
                    if c > best:
                        best, bd = c, (ddx, ddy)
            new.append((dx0 + bd[0], dy0 + bd[1]))
        shifts = new
        reps, _ = fold(stack, x0, y0, pw, ph, ow, oh, shifts)
    return reps, shifts


def runs(mask1d):
    """The cyclic runs of True in a 1D bool array: [(start, length)]."""
    n = len(mask1d)
    if mask1d.all():
        return [(0, n)]
    if not mask1d.any():
        return []
    s = int(np.argmin(mask1d))   # start the walk at a False
    out, i = [], 0
    while i < n:
        j = (s + i) % n
        if mask1d[j]:
            st, ln = j, 0
            while i < n and mask1d[(s + i) % n]:
                ln += 1
                i += 1
            out.append((st, ln))
        else:
            i += 1
    return out


def push_pull(col, w):
    """col (H, W, 3) where weight w (H, W) is 0 filled from the weighted surroundings, cyclically (a pyramid of weighted
    means, pulled back up)."""
    if w.min() > 0.999:
        return col
    levels = [(col * w[..., None], w)]
    while min(levels[-1][1].shape) > 2:
        c, ww = levels[-1]
        H, W = ww.shape
        H2, W2 = (H + 1) // 2, (W + 1) // 2
        cp = np.zeros((H2 * 2, W2 * 2, 3)); wp = np.zeros((H2 * 2, W2 * 2))
        cp[:H, :W] = c; wp[:H, :W] = ww
        c2 = cp.reshape(H2, 2, W2, 2, 3).sum((1, 3)); w2 = wp.reshape(H2, 2, W2, 2).sum((1, 3))
        levels.append((c2, w2))
    # pull: from the coarsest up, a level's empty texels take the coarser level's mean
    c, ww = levels[-1]
    mean = c / np.maximum(ww, 1e-6)[..., None]
    mean[ww < 1e-6] = (c.sum((0, 1)) / max(ww.sum(), 1e-6))
    for c, ww in reversed(levels[:-1]):
        H, W = ww.shape
        up = np.repeat(np.repeat(mean, 2, 0), 2, 1)[:H, :W]
        own = c / np.maximum(ww, 1e-6)[..., None]
        k = np.clip(ww, 0, 1)[..., None]
        mean = own * k + up * (1 - k)
    return col * w[..., None] + mean * (1 - w[..., None])


def bake_frame(sysd, fr):
    """One system's frame: (albedo uint8 HxWx3 sRGB, mask uint8 HxWx3, info) or (None, None, why)."""
    import fetch_glass_art as FG
    sid = sysd['id']
    nb_drawn, nf_drawn = FG.FRAMES[sid][3], FG.FRAMES[sid][4]
    im = Image.open(fr).convert('RGB')
    a = np.asarray(im).astype(np.float64) / 255
    H, W = a.shape[:2]
    gk, mk = keys(a)
    glass = np.clip(gk + mk, 0, 1)
    nbM, nfM = sysd['nbM'], sysd['nfM']
    pw = period(glass.mean(0), nbM * W / nb_drawn)
    ph = period(glass.mean(1) + 0.5 * mk.mean(1), nfM * H / nf_drawn)
    if not pw or not ph:
        return None, None, 'no repeat found (%s, %s)' % (pw, ph)
    # the module's phase: fold from the image's corner first, find the frame's middle column and the floor line there
    # the frame's own colour, premultiplied by how much of a pixel is frame and the key's spill taken out of the edges, so a
    # pixel the repeats disagree on never carries the key's green into the albedo
    w = 1 - glass
    de = a.copy()
    de[..., 1] = np.where(gk > 0, np.minimum(de[..., 1], np.maximum(de[..., 0], de[..., 2])), de[..., 1])
    for c in (0, 2):
        de[..., c] = np.where(mk > 0, np.minimum(de[..., c], de[..., 1] + 0.08), de[..., c])
    stack = np.concatenate([de * w[..., None], w[..., None], gk[..., None], mk[..., None]], axis=2)
    m0 = np.mean(fold(stack, 0.0, 0.0, pw, ph, int(round(pw)), int(round(ph)))[0], axis=0)
    colg = (m0[..., 4] + m0[..., 5]).mean(0)
    # the frame's middle: the centre of the longest run of columns with the least glass
    thr = colg.min() + 0.25 * (colg.max() - colg.min())
    rr = runs(colg <= thr)
    st, ln = max(rr, key=lambda q: q[1])
    xm = (st + ln / 2.0) % len(colg)
    # the floor line: the bottom of the vision band over the thickest band without vision glass (image rows run down)
    rowv = m0[..., 4].mean(1)
    rv = runs(rowv < 0.5 * rowv.max())
    if not rv:
        return None, None, 'no opaque band'
    bst, bln = max(rv, key=lambda q: q[1])
    ytop = bst % len(rowv)   # the band's top row: the vision run above it ends here
    x0 = (xm / len(colg)) * pw
    y0 = ((ytop / len(rowv)) * ph) - ph   # the module ends at the band's top: it starts a module above
    while y0 < 0:
        y0 += ph
    while x0 >= pw:
        x0 -= pw
    mw_m, mh_m = nbM * sysd['bay'], nfM * sysd['floor']
    s = min(PXM, CELL_MAX / mw_m, CELL_MAX / mh_m)
    ow, oh = int(round(mw_m * s)), int(round(mh_m * s))
    reps, shifts = align(stack, x0, y0, pw, ph, ow, oh, [4, 5])
    if len(reps) < 3:
        return None, None, 'only %d whole repeats' % len(reps)
    R = np.array(reps)
    mod = R.mean(0)
    dis = np.abs(R[..., 4] + R[..., 5] - (mod[..., 4] + mod[..., 5])[None]).mean()
    if dis > MUDDY:
        return None, None, 'muddy fold (%.3f)' % dis
    fw = mod[..., 3]
    rgb = mod[..., :3] / np.maximum(fw, 1e-6)[..., None]
    vg, sg = np.clip(mod[..., 4], 0, 1), np.clip(mod[..., 5], 0, 1)
    gl = np.clip(vg + sg, 0, 1)
    # a key that leaks: green or magenta left in the frame after the matte (a frame pixel that is mostly key colour)
    fr_px = gl < 0.05
    if fr_px.any():
        g2, m2 = keys(rgb)
        leak = float(((g2 > 0.02) | (m2 > 0.02))[fr_px].mean())
        if leak > 0.02:
            return None, None, 'key leaks into the frame (%.3f)' % leak
    alb = push_pull(rgb, np.clip(fw * 4 - 0.2, 0, 1))   # where a quarter of the repeats or more saw frame, its own colour
    # the vision band's sill and head in the module's lowest floor (rows run down: the floor's foot is the last row)
    fh = oh / nfM
    low = vg[int(round(oh - fh)):, :].mean(1)[::-1]   # from the floor line up
    on = np.where(low > 0.5 * max(low.max(), 1e-6))[0]
    sill, head = (float(on[0]) / fh, float(on[-1] + 1) / fh) if len(on) else (0.0, 1.0)
    frame_w = (1 - gl)
    fmean = (lin(alb) * frame_w[..., None]).sum((0, 1)) / max(frame_w.sum(), 1e-6)
    info = {'sys': sid, 'pw': round(pw, 2), 'ph': round(ph, 2), 'reps': len(reps), 'disagree': round(float(dis), 4),
            'size': [ow, oh], 'pxm': round(s, 2), 'sill': round(sill, 4), 'head': round(head, 4),
            'coverage': round(float(vg.mean()), 4), 'secondary': round(float(sg.mean()), 4),
            'frameMean': [round(float(v), 4) for v in fmean]}
    # the frame's detail as its luminance over twice the frame's mean (the page multiplies the system's frame colour by twice
    # it): one fetch a fragment, where an albedo atlas beside the mask was a second the old procedural wall never paid
    L = (lin(np.clip(alb, 0, 1)) * [0.2126, 0.7152, 0.0722]).sum(-1)
    detail = np.clip(L / (2 * max(float((fmean * [0.2126, 0.7152, 0.0722]).sum()), 1e-4)), 0, 1)
    A = (np.clip(alb, 0, 1) * 255 + 0.5).astype(np.uint8)
    M = (np.stack([vg, sg, detail], -1) * 255 + 0.5).astype(np.uint8)
    return A, M, info


def gutter(arr, pad):
    """A cell wrapped round by pad pixels each way (the module's own continuation)."""
    return np.pad(arr, ((pad, pad), (pad, pad), (0, 0)), mode='wrap')


def pack(sizes, W, H, pad):
    """Shelf packing, tallest first: [x, y] of each cell's inner corner (top-left, image rows down), or None."""
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i][1])
    pos = [None] * len(sizes)
    x = y = sh = 0
    for i in order:
        w, h = sizes[i][0] + 2 * pad, sizes[i][1] + 2 * pad
        if x + w > W:
            x, y, sh = 0, y + sh, 0
        if y + h > H:
            return None
        pos[i] = [x + pad, y + pad]
        x += w
        sh = max(sh, h)
    return pos


def room_template(W=1024, H=1536, b=B_SCALE):
    """The rooms' one-point perspective template: the back wall a centred rectangle at b of the picture each way, the
    floor, the ceiling and the side walls flat-shaded trapezoids round it, their edges drawn dark; and the edit's mask
    (transparent everywhere: the whole picture is repainted, the layout kept)."""
    im = Image.new('RGB', (W, H), (128, 128, 128))
    d = ImageDraw.Draw(im)
    x0, x1 = W * (1 - b) / 2, W * (1 + b) / 2
    y0, y1 = H * (1 - b) / 2, H * (1 + b) / 2
    d.polygon([(0, 0), (W, 0), (x1, y0), (x0, y0)], fill=(206, 206, 202))            # the ceiling
    d.polygon([(0, H), (W, H), (x1, y1), (x0, y1)], fill=(92, 88, 84))              # the floor
    d.polygon([(0, 0), (x0, y0), (x0, y1), (0, H)], fill=(150, 148, 144))           # the left wall
    d.polygon([(W, 0), (x1, y0), (x1, y1), (W, H)], fill=(140, 138, 134))           # the right wall
    d.rectangle((x0, y0, x1, y1), fill=(170, 168, 162))                             # the back wall
    for seg in (((0, 0), (x0, y0)), ((W, 0), (x1, y0)), ((0, H), (x0, y1)), ((W, H), (x1, y1))):
        d.line(seg, fill=(40, 40, 40), width=4)
    d.rectangle((x0, y0, x1, y1), outline=(40, 40, 40), width=4)
    mask = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    return im, mask


def back_wall_check(im, b=B_SCALE):
    """How far (a fraction of the picture) the generated room's back-wall edges stand from the template's: each of the
    four edges is found as the strongest luminance step within 10% of where it was drawn."""
    a = np.asarray(im.convert('L')).astype(np.float64) / 255
    H, W = a.shape
    gx = np.abs(np.diff(a, axis=1)); gy = np.abs(np.diff(a, axis=0))
    x0, x1, y0, y1 = W * (1 - b) / 2, W * (1 + b) / 2, H * (1 - b) / 2, H * (1 + b) / 2
    ys, xs = slice(int(y0 + 0.1 * (y1 - y0)), int(y1 - 0.1 * (y1 - y0))), slice(int(x0 + 0.1 * (x1 - x0)), int(x1 - 0.1 * (x1 - x0)))
    off = []
    for e, prof, n in ((x0, gx[ys].mean(0), W), (x1, gx[ys].mean(0), W), (y0, gy[:, xs].mean(1), H), (y1, gy[:, xs].mean(1), H)):
        lo, hi = int(e - 0.1 * n), int(e + 0.1 * n)
        k = lo + int(np.argmax(prof[lo:hi]))
        off.append(abs(k + 0.5 - e) / n)
    return max(off), off


def bake_rooms(preview):
    import fetch_glass_art as FG
    kinds = []
    cells = []
    atlas = Image.new('RGB', (RW, RH), (0, 0, 0))
    cols = RW // RCW
    for k, (rid, kind, _) in enumerate(FG.ROOMS):
        p = os.path.join(RAW, 'rooms', rid + '.png')
        if not os.path.exists(p):
            return None, 'room %s not made yet' % rid
        im = Image.open(p).convert('RGB')
        worst, offs = back_wall_check(im)
        if rid not in BACK:
            return None, 'room %s: no back wall measured (BACK)' % rid
        x0, y0, x1, y1 = BACK[rid]
        bx, by = x1 - x0, y1 - y0
        vp = [x0 / (1 - bx), 1 - y0 / (1 - by)]   # the vanishing point, in texture uv (v from the foot)
        cell = im.resize((RCW, RCH), Image.LANCZOS)
        cx, cy = (k % cols) * RCW, (k // cols) * RCH
        atlas.paste(cell, (cx, cy))
        a = lin(np.asarray(cell).astype(np.float64) / 255)
        lit = a.mean((0, 1))
        cells.append({'id': rid, 'kind': kind, 'rect': [round(cx / RW, 6), round(1 - (cy + RCH) / RH, 6), round(RCW / RW, 6), round(RCH / RH, 6)],
                      'b': [round(bx, 4), round(by, 4)], 'vp': [round(vp[0], 4), round(vp[1], 4)],
                      'meanDay': [round(float(v) * 0.25, 4) for v in lit], 'meanLit': [round(float(v), 4) for v in lit],
                      'drift': round(worst, 4)})
        if kind not in kinds:
            kinds.append(kind)
    half = atlas.resize((RW // 2, RH // 2), Image.LANCZOS)
    if preview:
        atlas.save(os.path.join(preview, 'rooms-atlas.jpg'), quality=88)
    return {'rooms': art_files.write(atlas, 'glass', 'rooms', 'WEBP', quality=85, method=6),
            'roomsHalf': art_files.write(half, 'glass', 'rooms-half', 'WEBP', quality=80, method=6),
            'roomSize': [RW, RH], 'roomCells': cells}, None


def bake(preview):
    S = json.load(open(SYSTEMS))
    out = {'v': 1, 'systems': S['systems'], 'towers': S['towers'], 'generic': S['generic'], 'glassKinds': S['glassKinds'],
           'styleDefault': S['styleDefault'], 'rooms': None, 'mask': None}
    cells, arts, why = [], [], []
    for sysd in S['systems']:
        fr = os.path.join(RAW, 'frames', 'sys%02d-%s.png' % (sysd['id'], sysd['name']))
        if not os.path.exists(fr):
            why.append('sys %d: no frame yet' % sysd['id'])
            continue
        A, M, info = bake_frame(sysd, fr)
        if A is None:
            why.append('sys %d: %s' % (sysd['id'], info))
            continue
        print('sys %2d %-10s module %6.1f x %6.1f px, %2d repeats, disagree %.3f, cell %s at %.1f px/m, sill %.3f head %.3f, cover %.3f + %.3f' % (
            sysd['id'], sysd['name'], info['pw'], info['ph'], info['reps'], info['disagree'], info['size'], info['pxm'], info['sill'],
            info['head'], info['coverage'], info['secondary']))
        cells.append(info); arts.append((A, M))
        if preview:
            Image.fromarray(A).save(os.path.join(preview, 'sys%02d-alb.png' % sysd['id']))
            Image.fromarray(M).save(os.path.join(preview, 'sys%02d-mask.png' % sysd['id']))
            tile = np.tile(A, (3, 4, 1))
            Image.fromarray(tile).save(os.path.join(preview, 'sys%02d-tiled.jpg' % sysd['id']), quality=88)
    for w in why:
        print('  ' + w)
    if len(cells) == len(S['systems']):
        pos = pack([c['size'] for c in cells], AW, AH, PAD)
        if pos is None:
            sys.exit('ERROR: the frame cells do not fit a %d x %d atlas' % (AW, AH))
        alb = np.zeros((AH, AW, 3), np.uint8); msk = np.zeros((AH, AW, 3), np.uint8)   # the albedo only for the preview
        for c, (A, M), (x, y) in zip(cells, arts, pos):
            w, h = c['size']
            alb[y - PAD:y + h + PAD, x - PAD:x + w + PAD] = gutter(A, PAD)
            msk[y - PAD:y + h + PAD, x - PAD:x + w + PAD] = gutter(M, PAD)
            # in texture uv, as the page samples it (flipY: v from the atlas's foot)
            c['rect'] = [round(x / AW, 6), round(1 - (y + h) / AH, 6), round(w / AW, 6), round(h / AH, 6)]
        ai, mi = Image.fromarray(alb), Image.fromarray(msk)
        out.update({'mask': art_files.write(mi, 'glass', 'glass-mask', 'PNG', optimize=True),
                    'maskHalf': art_files.write(mi.resize((AW // 2, AH // 2), Image.BILINEAR), 'glass', 'glass-mask-half', 'PNG', optimize=True),
                    'size': [AW, AH], 'pad': PAD, 'cells': sorted(cells, key=lambda c: c['sys'])})
        if preview:
            ai.save(os.path.join(preview, 'atlas-alb.png')); mi.save(os.path.join(preview, 'atlas-mask.png'))
        rooms, err = bake_rooms(preview)
        if rooms:
            out['rooms'] = rooms
        else:
            print('  rooms: ' + err)
    else:
        print('the frame atlas waits for all %d systems (%d baked)' % (len(S['systems']), len(cells)))
    gone = art_files.prune('glass')
    with open(OUT, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
        f.write('\n')
    print('glass_art.json: %d systems, %d towers, atlas %s, rooms %s; pruned %d' % (len(out['systems']), len(out['towers']),
          'yes' if out['mask'] else 'no', 'yes' if out['rooms'] else 'no', gone))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='')
    ap.add_argument('--template', default='', help='write the rooms\' template to this path and stop')
    a = ap.parse_args()
    if a.template:
        room_template()[0].save(a.template)
        return
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
    bake(a.preview)


if __name__ == '__main__':
    main()
