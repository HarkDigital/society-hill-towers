#!/usr/bin/env python3
"""Wall colours for the outer districts from Mapillary street-level thumbnails
(fetch_mapillary.py), aggregated per block face and quantised to a 32-entry palette:

  wall_palette.json  {"wall": ["#rrggbb" x32], "counts": [...], ...}
                     sRGB as the photos show it. The app stores its colours DARK for the
                     r149 legacy pipeline (see roofInv / ROOF_PAL in app.js) and must
                     convert these the same way; nothing here is pre-darkened.
  wall_colors.json   {"wide": [palette index or -1 per building of scene_wide.json],
                      "south": [the same for scene_south.json],
                      "wide_hint", "south_hint": [the facade hint byte per building, 0
                      where the building has no colour]}

How a colour gets from a photo to a building:
  1. Every road of scene_wide.json / scene_south.json is walked segment by segment
     (consecutive pts pairs, which in OSM data are block faces). The images within 25 m
     of a segment are its candidates.
  2. An image's wall sample is the per-channel median of the 35..60 % band of its left
     third and of its right third (buildings flank the street; the middle third is road
     and sky), after discarding sky-like pixels (blue-dominant and bright, blown white, the light
     neutral grey of overcast and haze, and any cool cast on a light or mid pixel, which
     is skylight on a shaded wall or car glass, never brick), road-like pixels (dark and
     grey) and foliage (green-dominant). A third
     keeping fewer than a fifth of its pixels gives no sample.
  3. Which block face each third looks at follows from the image's compass angle against
     the segment's bearing (model frame: x east, z south, so north is -z). Looking along
     the segment (within 30 deg), the camera's left is the segment's left; looking back,
     they swap. A camera looking along a street stands on it: the view counts only
     within half the road's width plus 4 m of the centreline (a car lane or the
     sidewalk), which keeps a sideways view on one street from passing as an along
     view of the cross street it happens to point down. Looking sideways (within 30 deg
     of the normal), both thirds see the one face the camera points at, and count only
     from the street itself, away from its ends. Oblique views in between are skipped:
     at a diagonal crossing they belong to the other street.
  4. A face's colour is the median of its samples (at least --min-samples, default 3);
     a face short of samples borrows the median of its whole road's same side.
  5. Every building takes the nearest street segment within 30 m of its footprint
     (streets before service roads; motorways and trunks never count), the side the
     footprint lies on, and that face's colour, or -1 with no coloured face.
  6. k-means (seed 7) over all face colours gives the 32-entry palette, sorted light to
     dark; each building stores the index of its face's cluster.
  7. Beside its colour, a sample carries two fractions of the pixels the filter kept:
     light (min channel > 165: white trim, cornices, formstone, light siding, painted
     walls) and dark (max channel < 70: window glass, doors, dark trim, deep shadow
     under bays). A face takes the median of each across its samples (a face borrowing
     its road side's colour borrows its fractions too), and the building's hint byte
     classes them: trim in bits 0-1 (1 light fraction < 0.08, 2 in [0.08, 0.22), 3 at
     0.22 and above), windows in bits 2-3 (1 dark fraction < 0.12, 2 in [0.12, 0.30),
     3 at 0.30 and above), both 0 for a building without a colour. The colour path is
     untouched by the fractions: the palette and indices are what they were before them.

--dry-run reads fetch_mapillary.py's synthetic set under lidar_cache/mly_dry/ and checks
the recovered face colours against its truth.json. Plain python3; Pillow reads the
thumbnails (without it only records carrying their colours inline are usable); numpy is
used when it imports, pure Python otherwise."""
import argparse, json, math, os, random, sys, time
from collections import defaultdict
try:
    from PIL import Image
except ImportError:
    Image = None
try:
    import numpy as np
except ImportError:
    np = None

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
SCENES = [('wide', 'scene_wide.json'), ('south', 'scene_south.json')]
IMAGES = 'lidar_cache/mly_images.json'
THUMBS = 'lidar_cache/mly_thumbs'
DRY_DIR = 'lidar_cache/mly_dry'
PALETTE_OUT, COLORS_OUT = 'wall_palette.json', 'wall_colors.json'

IMG_REACH = 25.0        # images this close to a segment are its candidates
ON_STREET = (5.0, 12.0) # an along view must stand on the street: half its width + 4 m, clamped to this
PERP_REACH = 10.0       # a sideways view counts only from the street it faces
PERP_END = 8.0          # and not from the intersection at either end
ALONG_SLACK = 5.0       # an along view may stand this far past the segment's ends
BLD_REACH = 30.0        # footprint to street centreline
CELL = 50.0             # spatial hash
K = 32
BAND = (0.35, 0.60)      # of the image height: the near walls either side of a dashcam's horizon
LIGHT_MIN = 165          # a kept pixel whose min channel clears this is light: trim, formstone, paint
DARK_MAX = 70            # a kept pixel whose max channel stays under this is dark: glass, doors, shadow
TRIM_CLASS = (0.08, 0.22)    # light fraction: class 1 below the first cut, 2 between, 3 from the second
WINDOW_CLASS = (0.12, 0.30)  # dark fraction: the same three classes
ALONG_COS = math.cos(math.radians(30))   # |heading . bearing| above this: looking along the street
PERP_SIN = math.sin(math.radians(30))     # ... below this: looking at one face; in between the view is oblique and skipped
NO_FACE = {'motorway', 'motorway_link', 'trunk', 'trunk_link'}
STREETS = {'residential', 'tertiary', 'secondary', 'primary', 'unclassified', 'living_street', 'pedestrian'}
SKIP_BUILDINGS = {'ship', 'stadium', 'arena'}


# ---------------- geometry ----------------
def project(ax, az, bx, bz, px, pz):
    """(distance, t along a->b unclamped, closest point) of p against segment a-b."""
    dx, dz = bx - ax, bz - az
    t = ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz)
    tc = 0.0 if t < 0 else 1.0 if t > 1 else t
    qx, qz = ax + dx * tc, az + dz * tc
    return math.hypot(px - qx, pz - qz), t, qx, qz


def cells(x0, z0, x1, z1):
    for cx in range(math.floor(x0 / CELL), math.floor(x1 / CELL) + 1):
        for cz in range(math.floor(z0 / CELL), math.floor(z1 / CELL) + 1):
            yield (cx, cz)


def median_ch(samples, ch):
    v = sorted(s[ch] for s in samples)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def median_rgb(samples):
    """The per-channel median colour of samples that may carry more than three channels."""
    return tuple(int(round(median_ch(samples, ch))) for ch in range(3))


def median_fracs(samples):
    """(light fraction, dark fraction) medians of (r, g, b, light, dark) samples."""
    return (median_ch(samples, 3), median_ch(samples, 4))


def frac_class(v, cuts):
    return 1 if v < cuts[0] else 2 if v < cuts[1] else 3


def hint_byte(fracs):
    """trim class in bits 0-1, window class in bits 2-3 (see step 7 of the module docstring)."""
    return frac_class(fracs[0], TRIM_CLASS) | (frac_class(fracs[1], WINDOW_CLASS) << 2)


# ---------------- the wall sample of one thumbnail ----------------
def keep_px(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if b >= 140 and b > r + 15 and b >= g - 4 and mx > 130: return False   # blue sky
    if mn > 235: return False                                              # blown sky
    if mn > 185 and mx - mn < 28: return False                             # overcast sky, cloud, haze
    if b > r + 6 and mx > 150: return False                                # hazy sky, distant air
    if b > r + 10 and mx > 110: return False                               # skylight on a shaded wall, car glass
    if mx < 100 and mx - mn < 30: return False                             # asphalt, shadowed road
    if g > r + 18 and g > b + 18: return False                             # foliage
    return True


def band_sample_py(im, x0, x1, y0, y1):
    """(r, g, b, lightFrac, darkFrac) of the band, or None when the filter keeps too little."""
    px = list(im.crop((x0, y0, x1, y1)).getdata())
    kept = [p for p in px if keep_px(*p)]
    if len(kept) < max(20, 0.2 * len(px)):
        return None
    light = sum(1 for p in kept if min(p) > LIGHT_MIN)
    dark = sum(1 for p in kept if max(p) < DARK_MAX)
    return median_rgb(kept) + (light / len(kept), dark / len(kept))


def band_sample_np(arr, x0, x1, y0, y1):
    sub = arr[y0:y1, x0:x1].reshape(-1, 3)
    r, g, b = sub[:, 0], sub[:, 1], sub[:, 2]
    mx, mn = sub.max(1), sub.min(1)
    drop = ((b >= 140) & (b > r + 15) & (b >= g - 4) & (mx > 130)) | (mn > 235) \
        | ((mn > 185) & (mx - mn < 28)) | ((b > r + 6) & (mx > 150)) | ((b > r + 10) & (mx > 110)) \
        | ((mx < 100) & (mx - mn < 30)) | ((g > r + 18) & (g > b + 18))
    m = ~drop
    nk = int(m.sum())
    if nk < max(20, 0.2 * len(sub)):
        return None
    rgb = tuple(int(round(float(v))) for v in np.median(sub[m], axis=0))
    return rgb + (int((mn[m] > LIGHT_MIN).sum()) / nk, int((mx[m] < DARK_MAX).sum()) / nk)


def wall_samples(rec, thumbs):
    """(left third sample, right third sample), each an (r, g, b, lightFrac, darkFrac) or None."""
    if 'rgb_l' in rec or 'rgb_r' in rec:          # a dry run without Pillow: colours only, no fractions
        return (tuple(rec['rgb_l']) + (0.0, 0.0) if rec.get('rgb_l') else None,
                tuple(rec['rgb_r']) + (0.0, 0.0) if rec.get('rgb_r') else None)
    path = os.path.join(thumbs, f"{rec['id']}.jpg")
    if Image is None or not os.path.exists(path):
        return (None, None)
    try:
        im = Image.open(path).convert('RGB')
    except Exception:
        return (None, None)
    w, h = im.size
    y0, y1 = int(h * BAND[0]), int(h * BAND[1])
    third = w // 3
    if np is not None:
        arr = np.asarray(im, dtype=np.int16)
        return band_sample_np(arr, 0, third, y0, y1), band_sample_np(arr, w - third, w, y0, y1)
    return band_sample_py(im, 0, third, y0, y1), band_sample_py(im, w - third, w, y0, y1)


# ---------------- palette ----------------
def kmeans(colors, k, seed=7, iters=40):
    """Deterministic k-means over (r, g, b) tuples: k-means++ seeding from a seeded RNG,
    an empty cluster re-seeded to the point farthest from its centroid. Returns
    (centroids, labels)."""
    rng = random.Random(seed)
    uniq = sorted(set(colors))
    k = max(1, min(k, len(uniq)))
    cent = [uniq[rng.randrange(len(uniq))]]
    d2 = [sum((a - b) ** 2 for a, b in zip(p, cent[0])) for p in uniq]
    while len(cent) < k:
        tot = sum(d2)
        if tot <= 0:
            break
        r, acc = rng.random() * tot, 0.0
        for p, w in zip(uniq, d2):
            acc += w
            if acc >= r:
                cent.append(p)
                break
        else:
            cent.append(uniq[-1])
        d2 = [min(w, sum((a - b) ** 2 for a, b in zip(p, cent[-1]))) for p, w in zip(uniq, d2)]
    if np is not None:
        X = np.array(colors, np.float64)
        C = np.array(cent, np.float64)
        for _ in range(iters):
            lab = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2).argmin(1)
            new = C.copy()
            for j in range(len(C)):
                m = lab == j
                if m.any():
                    new[j] = X[m].mean(0)
                else:
                    far = ((X - C[lab]) ** 2).sum(1).argmax()
                    new[j] = X[far]
            if np.allclose(new, C):
                break
            C = new
        lab = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2).argmin(1)
        return [tuple(int(round(v)) for v in c) for c in C], [int(l) for l in lab]
    labels = [0] * len(colors)
    for _ in range(iters):
        sums = [[0.0, 0.0, 0.0, 0] for _ in cent]
        for i, p in enumerate(colors):
            best, bj = None, 0
            for j, c in enumerate(cent):
                d = (p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2
                if best is None or d < best:
                    best, bj = d, j
            labels[i] = bj
            s = sums[bj]
            s[0] += p[0]; s[1] += p[1]; s[2] += p[2]; s[3] += 1
        new = []
        for j, s in enumerate(sums):
            if s[3]:
                new.append((s[0] / s[3], s[1] / s[3], s[2] / s[3]))
            else:
                far = max(range(len(colors)), key=lambda i: sum((a - b) ** 2 for a, b in zip(colors[i], cent[labels[i]])))
                new.append(tuple(float(v) for v in colors[far]))
        if all(abs(a - b) < 1e-6 for c1, c2 in zip(new, cent) for a, b in zip(c1, c2)):
            break
        cent = new
    return [tuple(int(round(v)) for v in c) for c in cent], labels


def luminance(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true', help='use the synthetic set under lidar_cache/mly_dry/ and check it against its truth')
    ap.add_argument('--images', default=None, help=f'image list (default {IMAGES})')
    ap.add_argument('--thumbs', default=None, help=f'thumbnail folder (default {THUMBS})')
    ap.add_argument('--min-samples', type=int, default=3, help='samples a face needs before it gets a colour (default 3)')
    a = ap.parse_args()
    images_path = a.images or (os.path.join(DRY_DIR, 'mly_images.json') if a.dry_run else IMAGES)
    thumbs = a.thumbs or (os.path.join(DRY_DIR, 'thumbs') if a.dry_run else THUMBS)
    if not os.path.exists(images_path):
        sys.exit(f'{images_path} missing: run fetch_mapillary.py{" --dry-run" if a.dry_run else ""} first')
    t0 = time.time()
    meta = json.load(open(images_path))
    images = meta['images']
    if meta.get('dry_run') and not a.dry_run:
        print('note: the image list is a synthetic dry run', flush=True)
    print(f'{len(images)} images from {images_path}' + (' (synthetic)' if meta.get('dry_run') else ''), flush=True)

    img_grid = defaultdict(list)
    for i, r in enumerate(images):
        img_grid[(math.floor(r['x'] / CELL), math.floor(r['z'] / CELL))].append(i)
    sample_cache = {}

    def samples_of(i):
        if i not in sample_cache:
            sample_cache[i] = wall_samples(images[i], thumbs)
        return sample_cache[i]

    scenes = {tag: json.load(open(path)) for tag, path in SCENES}
    # ---- segments and their faces ----
    segs = []                                   # (tag, ri, si, ax, az, bx, bz, ux, uz, L, cls)
    faces = defaultdict(list)                   # (tag, ri, si, side) -> [rgb]
    road_side = defaultdict(list)               # (tag, ri, side) -> [rgb]
    used = set()
    kinds = defaultdict(int)
    for tag, _ in SCENES:
        for ri, road in enumerate(scenes[tag].get('roads', [])):
            pts, cls = road.get('pts') or [], road.get('t')
            for si in range(len(pts) - 1):
                (ax, az), (bx, bz) = pts[si], pts[si + 1]
                L = math.hypot(bx - ax, bz - az)
                if L < 0.5:
                    continue
                ux, uz = (bx - ax) / L, (bz - az) / L
                segs.append((tag, ri, si, ax, az, bx, bz, ux, uz, L, cls))
                reach = IMG_REACH
                on_street = min(ON_STREET[1], max(ON_STREET[0], (road.get('w') or 7) / 2 + 4))
                lx, lz = uz, -ux                    # the segment's left (north when it runs east)
                for cell in cells(min(ax, bx) - reach, min(az, bz) - reach, max(ax, bx) + reach, max(az, bz) + reach):
                    for i in img_grid.get(cell, ()):
                        r = images[i]
                        d, t, qx, qz = project(ax, az, bx, bz, r['x'], r['z'])
                        if d > reach:
                            continue
                        th = math.radians(r['compass_angle'] or 0.0)
                        cx, cz = math.sin(th), -math.cos(th)
                        dot = cx * ux + cz * uz
                        if abs(dot) >= ALONG_COS:                   # along the street: a face per flank
                            if d > on_street or t * L < -ALONG_SLACK or t * L > L + ALONG_SLACK:
                                continue
                            sl, sr = samples_of(i)
                            pairs = ((sl, 'L'), (sr, 'R')) if dot > 0 else ((sl, 'R'), (sr, 'L'))
                            kind = 'along'
                        elif abs(dot) <= PERP_SIN:                  # sideways: both flanks see the one face
                            if d > PERP_REACH or t * L < PERP_END or (1 - t) * L < PERP_END:
                                continue
                            both = [s for s in samples_of(i) if s is not None]
                            if not both:
                                continue
                            s = both[0] if len(both) == 1 else \
                                tuple((p + q) // 2 for p, q in zip(both[0][:3], both[1][:3])) + \
                                tuple((p + q) / 2 for p, q in zip(both[0][3:], both[1][3:]))
                            pairs = ((s, 'L' if cx * lx + cz * lz > 0 else 'R'),)
                            kind = 'side'
                        else:                                       # oblique: neither flank is this street's
                            continue
                        for s, side in pairs:
                            if s is None:
                                continue
                            faces[(tag, ri, si, side)].append(s)
                            road_side[(tag, ri, side)].append(s)
                            used.add(i)
                            kinds[kind] += 1
    face_rgb, face_frac, borrowed = {}, {}, 0    # (tag, ri, si, side) -> rgb, -> (light, dark) fractions
    for key, lst in faces.items():
        if len(lst) >= a.min_samples:
            face_rgb[key] = median_rgb(lst)
            face_frac[key] = median_fracs(lst)
    for s in segs:
        tag, ri, si = s[:3]
        for side in 'LR':
            key = (tag, ri, si, side)
            pool = road_side.get((tag, ri, side), ())
            if key not in face_rgb and len(pool) >= a.min_samples:
                face_rgb[key] = median_rgb(pool)
                face_frac[key] = median_fracs(pool)
                borrowed += 1
    opened = sum(1 for v in sample_cache.values() if v != (None, None))
    print(f'images: {len(sample_cache)} opened, {opened} with a wall sample, {len(used)} used '
          f'({kinds["along"]} along-street samples, {kinds["side"]} sideways); '
          f'{len(segs)} segments, {len(face_rgb)} faces coloured ({borrowed} from their road\'s side), {time.time() - t0:.0f}s', flush=True)

    # ---- buildings -> faces ----
    seg_grid = defaultdict(list)
    lit = set()                                  # cells holding a segment with a coloured face
    for k, s in enumerate(segs):
        if s[10] in NO_FACE:
            continue
        for cell in cells(min(s[3], s[5]), min(s[4], s[6]), max(s[3], s[5]), max(s[4], s[6])):
            seg_grid[cell].append(k)
            if (s[0], s[1], s[2], 'L') in face_rgb or (s[0], s[1], s[2], 'R') in face_rgb:
                lit.add(cell)
    result, coloured, face_of = {}, {}, {}
    for tag, _ in SCENES:
        blds = scenes[tag].get('buildings', [])
        idx = [-1] * len(blds)
        hint = [0] * len(blds)
        n = 0
        for bi, b in enumerate(blds):
            poly = b.get('poly') or []
            if len(poly) < 3 or b.get('t') in SKIP_BUILDINGS:
                continue
            xs = [p[0] for p in poly]; zs = [p[1] for p in poly]
            cx, cz = sum(xs) / len(xs), sum(zs) / len(zs)
            rad = max(math.hypot(x - cx, z - cz) for x, z in poly)
            cl = list(cells(min(xs) - BLD_REACH, min(zs) - BLD_REACH, max(xs) + BLD_REACH, max(zs) + BLD_REACH))
            if not any(c in lit for c in cl):
                continue
            cands = set()
            for c in cl:
                cands.update(seg_grid.get(c, ()))
            best = None
            for k in cands:
                tag2, ri, si, ax, az, bx, bz, ux, uz, L, cls = segs[k]
                if tag2 != tag:
                    continue
                dc, t, qx, qz = project(ax, az, bx, bz, cx, cz)
                if dc - rad > BLD_REACH:
                    continue
                d = min(project(ax, az, bx, bz, x, z)[0] for x, z in poly)
                if d > BLD_REACH:
                    continue
                key = (0 if cls in STREETS else 1, d)
                if best is None or key < best[0]:
                    side = 'L' if (cx - qx) * uz + (cz - qz) * (-ux) > 0 else 'R'
                    best = (key, (tag, ri, si, side))
            if best and best[1] in face_rgb:
                face_of[(tag, bi)] = best[1]
                coloured[(tag, bi)] = face_rgb[best[1]]
                n += 1
        result[tag] = (idx, hint, n, len(blds))

    # ---- palette ----
    face_keys = sorted(face_rgb)
    face_cols = [face_rgb[k] for k in face_keys]
    if face_cols:
        cent, lab = kmeans(face_cols, K)
    else:
        cent, lab = [], []
    order = sorted(range(len(cent)), key=lambda j: -luminance(cent[j]))
    remap = {old: new for new, old in enumerate(order)}
    palette = [cent[j] for j in order]
    counts = [0] * len(palette)
    face_idx = {}
    for k, l in zip(face_keys, lab):
        face_idx[k] = remap[l]
        counts[remap[l]] += 1
    while len(palette) < K:                      # fewer distinct face colours than entries: pad with greys
        v = 48 + (len(palette) - len(cent)) * 6
        palette.append((v, v, v)); counts.append(0)
    for tag, (idx, hint, n, total) in result.items():
        for (t2, bi), key in face_of.items():
            if t2 == tag:
                idx[bi] = face_idx[key]
                hint[bi] = hint_byte(face_frac[key])
    hist = {'trim': [0] * 4, 'window': [0] * 4}      # class 0 is a building without a colour
    for tag, (idx, hint, n, total) in result.items():
        for h in hint:
            hist['trim'][h & 3] += 1
            hist['window'][(h >> 2) & 3] += 1

    # ---- write ----
    stats = {tag: {'buildings': total, 'coloured': n} for tag, (idx, hint, n, total) in result.items()}
    hints = {'note': 'buildings per class, both scenes; class 0 is a building without a colour. trim (bits 0-1): '
                     f'1 light fraction < {TRIM_CLASS[0]}, 2 to {TRIM_CLASS[1]}, 3 above; window (bits 2-3): '
                     f'1 dark fraction < {WINDOW_CLASS[0]}, 2 to {WINDOW_CLASS[1]}, 3 above',
             'trim': hist['trim'], 'window': hist['window']}
    with open(PALETTE_OUT, 'w') as f:
        json.dump({'src': 'Mapillary street-level imagery (CC BY-SA 4.0) via fetch_mapillary.py, aggregated by bake_wall_colors.py',
                   'note': 'sRGB as seen in the photos, light to dark. The app stores colours dark for the r149 legacy pipeline (see roofInv in app.js) and converts these itself.',
                   'dry_run': bool(meta.get('dry_run')), 'images_used': len(used), 'faces': len(face_rgb),
                   'wall': ['#%02x%02x%02x' % c for c in palette], 'counts': counts, 'buildings': stats, 'hints': hints}, f, indent=1)
    out = {}
    for tag, _ in SCENES:
        out[tag] = result[tag][0]
    for tag, _ in SCENES:
        out[tag + '_hint'] = result[tag][1]
    with open(COLORS_OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(COLORS_OUT + '.tmp', COLORS_OUT)
    print(f'coverage: {len(used)} images used, {len(face_rgb)} block faces coloured', flush=True)
    for tag, (idx, hint, n, total) in result.items():
        nf = sum(1 for k in face_rgb if k[0] == tag)
        ns = sum(1 for s in segs if s[0] == tag)
        print(f'  {tag}: {nf}/{2 * ns} faces, {n}/{total} buildings coloured ({100 * n / max(1, total):.1f}%)', flush=True)
    nc = sum(hist['trim'][1:])
    print(f'hints over {nc} coloured buildings: trim light < {TRIM_CLASS[0]:.0%} {hist["trim"][1]}, '
          f'to {TRIM_CLASS[1]:.0%} {hist["trim"][2]}, above {hist["trim"][3]}; '
          f'windows dark < {WINDOW_CLASS[0]:.0%} {hist["window"][1]}, to {WINDOW_CLASS[1]:.0%} {hist["window"][2]}, '
          f'above {hist["window"][3]}', flush=True)
    top = sorted(range(len(palette)), key=lambda j: -counts[j])[:8]
    print('palette: ' + ', '.join(f'#{palette[j][0]:02x}{palette[j][1]:02x}{palette[j][2]:02x} x{counts[j]}' for j in top), flush=True)
    print(f'{PALETTE_OUT}: {len(palette)} entries; {COLORS_OUT}: {os.path.getsize(COLORS_OUT):,} bytes ({time.time() - t0:.0f}s)', flush=True)

    # ---- dry run: the recovered faces against the truth ----
    if a.dry_run:
        truth_path = os.path.join(DRY_DIR, 'truth.json')
        if not os.path.exists(truth_path):
            sys.exit(f'{truth_path} missing')
        truth = {(t['file'], t['road']): t for t in json.load(open(truth_path))['streets']}
        errs, other = [], 0
        for key, rgb in face_rgb.items():
            t = truth.get(key[:2])
            if not t:
                other += 1
                continue
            want = t[key[3]]
            errs.append(max(abs(rgb[c] - want[c]) for c in range(3)))
        b_on = sum(1 for (tag, bi), key in face_of.items() if key[:2] in truth)
        mean = sum(errs) / max(1, len(errs))
        print(f'truth check: {len(errs)} faces on the synthetic streets, max channel error mean {mean:.1f}, '
              f'worst {max(errs) if errs else 0}; {other} faces on other roads (intersection bleed); '
              f'{b_on}/{len(face_of)} coloured buildings sit on the synthetic streets', flush=True)
        if not errs or mean > 8 or max(errs) > 30:
            sys.exit('dry run FAILED: the recovered face colours do not match truth.json')
        print('dry run OK', flush=True)


if __name__ == '__main__':
    main()
