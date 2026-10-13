#!/usr/bin/env python3
"""Bake the land mask (the realism pass, Oct 12: Mike asked for the whole model "more photo realistic and less cartoony";
ground-vegetation 8, 9 and 10): one RGB picture over the terrain's whole box (pack_city.py CITY) that tells the ground
shader what a patch of bare ground is, so it stops being one lawn from Delaware County to the Northeast. No alpha: a
browser may premultiply an image's colour by it on the way to the GPU, which would wipe the data wherever it is low.

  R  built up: the share of the ground under building footprints (wide.b64, city.b64, outskirts.b64), drawn at 5 m and
     averaged to the mask's 20 m, then blurred over about 60 m, and taken out where the ground is a park or a green
     (the scenes' park areas and the parkland rings). Rowhouse blocks read 0.5 and up, parkland and open ground 0. The
     shader lays yards, patios and alleys on built-up ground and keeps the lawn where it is low.
  G  woods: the PPR parkland rings (nw_parks.json, already in the build) and the interiors of the scenes' big parks, away
     from the drives and the buildings and where the street tree survey (trees.b64) finds few trees, since a surveyed tree
     is a maintained one standing in a lawn;
     past the city line, a share of whatever is not built up (Delaware County and Montgomery County are canopy and
     roofs). The shader lays the generated forest canopy there.
  B  river bank: 1 at the Schuylkill's and the tidal Delaware's edge (schuylkill.json, delaware.json), 0 by 60 m inland,
     so the shader's tide band and riprap follow the two rivers and never the creeks (whose water stands at its own
     stepped levels) or low flat ground away from them.

No new data: every source is a file the build already ships. Writes art/land/landmask.<hash>.webp (lossless) and a phone's
half beside it through art_files.py, and land_mask.json (the paths and the box), which build.py inlines as LAND_MASK.
Frame: philly_frame.py's model frame (x east, z south, metres)."""
import base64, json, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'land_mask.json')
CITY = (-12000.0, 16500.0, -21700.0, 9700.0)    # pack_city.py CITY (x0, x1, z0, z1)
PX = 20.0                                         # metres a mask pixel
FINE = 4                                          # footprints drawn at PX / FINE, then averaged
W, H = int((CITY[1] - CITY[0]) / PX), int((CITY[3] - CITY[2]) / PX)
# blob: (file, coordinate unit in metres, int16 words in a building's header)
BLOBS = (('wide.b64', 0.2), ('city.b64', 0.7), ('outskirts.b64', 1.0))
ATTR_MAGICS = (0x5348545A, 0x5348545B, 0x5348545C, 0x5348545D)


def read_blob(name, unit):
    """(buildings, roads, areas) of a scene blob, each a list of (kind, [(x, z), ...]) in metres."""
    raw = base64.b64decode(open(os.path.join(HERE, name), 'rb').read().strip())
    magic, nb, nr, na = struct.unpack_from('<4i', raw, 0)
    body = np.frombuffer(raw, dtype='<i2', offset=16)
    hs = 6 if magic in ATTR_MAGICS else 4
    i, out = 0, ([], [], [])
    for _ in range(nb):
        n = int(body[i]); p = body[i + hs:i + hs + 2 * n].astype(np.float64) * unit
        out[0].append((int(body[i + 3]), p.reshape(-1, 2))); i += hs + 2 * n
    for _ in range(nr):
        n = int(body[i]); p = body[i + 3:i + 3 + 2 * n].astype(np.float64) * unit
        out[1].append((int(body[i + 2]), p.reshape(-1, 2), body[i + 1] / 10.0)); i += 3 + 2 * n
    for _ in range(na):
        n = int(body[i]); p = body[i + 2:i + 2 + 2 * n].astype(np.float64) * unit
        out[2].append((int(body[i + 1]), p.reshape(-1, 2))); i += 2 + 2 * n
    return out


def canvas(scale=1):
    return Image.new('L', (W * scale, H * scale), 0)


def to_px(pts, scale=1):
    k = scale / PX
    return [((x - CITY[0]) * k, (z - CITY[2]) * k) for x, z in pts]


def fill(im, ring, scale=1, v=255):
    if len(ring) >= 3:
        ImageDraw.Draw(im).polygon(to_px(ring, scale), fill=v)


def grow(mask, px):
    """A binary mask grown by px pixels (3 by 3 max filters)."""
    im = Image.fromarray(mask)
    for _ in range(px):
        im = im.filter(ImageFilter.MaxFilter(3))
    return np.asarray(im)


def dist_px(mask, upto):
    """The distance in pixels (0 to upto) from a binary mask, by successive growth."""
    d = np.full(mask.shape, float(upto), np.float32)
    cur = mask.copy()
    d[cur > 127] = 0
    for k in range(1, upto + 1):
        cur = grow(cur, 1)
        d[(cur > 127) & (d > k)] = k
    return d


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    blds, roads, areas = [], [], []
    for name, unit in BLOBS:
        b, r, a = read_blob(name, unit)
        blds += b; roads += r; areas += a
        print('%-14s %7d buildings %7d roads %6d areas' % (name, len(b), len(r), len(a)))
    # R: footprints at 5 m, averaged to 20 m, blurred
    fine = canvas(FINE)
    for _, ring in blds:
        fill(fine, ring, FINE)
    built = np.asarray(fine.resize((W, H), Image.BOX), np.float32) / 255.0
    built_soft = np.asarray(Image.fromarray((built * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255.0
    R = np.clip(built_soft * 1.6, 0, 1)
    # B: the scenes' park areas (kind 0) and the PPR parkland
    park = canvas()
    for kind, ring in areas:
        if kind == 0:
            fill(park, ring)
    parkland = canvas()
    for fl in json.load(open(os.path.join(HERE, 'nw_parks.json')))['polys']:
        fill(parkland, list(zip(fl[0::2], fl[1::2])))
    parkland = np.asarray(parkland)
    park = np.maximum(np.asarray(park), parkland)
    B = np.asarray(Image.fromarray(park).filter(ImageFilter.GaussianBlur(1.0)), np.float32) / 255.0
    # G: woods, the parkland away from the drives and the buildings, where the survey finds few trees
    rd = canvas()
    dr = ImageDraw.Draw(rd)
    for _, pts, w in roads:
        dr.line(to_px(pts), fill=255, width=1)
    road_d = dist_px(np.asarray(rd), 4) * PX                    # metres to the nearest road, to 80
    bld_d = dist_px(((built > 0.08) * 255).astype(np.uint8), 4) * PX
    th, tb = None, base64.b64decode(open(os.path.join(HERE, 'trees.b64'), 'rb').read().strip())
    hdr = struct.unpack_from('<4i', tb, 0)
    tv = np.frombuffer(tb, dtype='<i2', offset=16)[:hdr[1] * 4].reshape(-1, 4).astype(np.float64)
    tq = hdr[3] / 1000 if hdr[3] > 0 else 0.2
    tx, tz = (tv[:, 0] * tq - CITY[0]) / PX, (tv[:, 1] * tq - CITY[2]) / PX
    ok = (tx >= 0) & (tx < W) & (tz >= 0) & (tz < H)
    dens = np.zeros((H, W), np.float32)
    np.add.at(dens, (tz[ok].astype(int), tx[ok].astype(int)), 1.0)
    dens = np.asarray(Image.fromarray(np.clip(dens * 40, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.0)), np.float32) / 255.0
    pl = np.asarray(Image.fromarray(parkland).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255.0
    # and the scenes' own big parks (Pennypack, Tacony Creek, Cobbs Creek and FDR have no parkland ring here): only their
    # interiors, 50 m and more from a road, a little thinner than the parkland
    pk = np.asarray(Image.fromarray(park).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255.0
    far = smooth(20, 70, road_d) * smooth(20, 70, bld_d) * (1 - smooth(0.04, 0.35, dens))
    woods = np.maximum(pl, pk * 0.8 * smooth(50, 80, road_d)) * far
    # past the city line, a share of the unbuilt ground
    lim = canvas()
    fill(lim, json.load(open(os.path.join(HERE, 'city_limit.json')))['city'])
    inside = np.asarray(lim.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255.0
    sub = (1 - inside) * 0.55 * (1 - smooth(0.1, 0.5, R)) * smooth(10, 50, road_d)
    G = np.clip(np.maximum(woods, sub), 0, 1)
    G = np.asarray(Image.fromarray((G * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)), np.float32) / 255.0
    # A: the two rivers' banks
    water = canvas()
    s = json.load(open(os.path.join(HERE, 'schuylkill.json')))
    d = json.load(open(os.path.join(HERE, 'delaware.json')))
    for p in s['polys'] + d['polys'] + d.get('beyond', []):
        fill(water, p['ring'])
        for h in p.get('holes', []):
            fill(water, h, v=0)
    wd = dist_px(np.asarray(water), 4) * PX                     # metres from the water, to 80 (0 on it)
    A = np.where(np.asarray(water) > 127, 1.0, 1 - smooth(10, 60, wd)).astype(np.float32)
    R = R * (1 - B)
    rgb = np.stack([R, G, A], -1)
    im = Image.fromarray(np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8))
    full = art_files.write(im, 'land', 'landmask', 'WEBP', lossless=True, method=6)
    half = art_files.write(im.resize((W // 2, H // 2), Image.BOX), 'land', 'landmask-half', 'WEBP', lossless=True, method=6)
    print('pruned %d old land files' % art_files.prune('land'))
    out = {'img': full, 'imgHalf': half, 'box': [CITY[0], CITY[2], CITY[1] - CITY[0], CITY[3] - CITY[2]], 'px': PX,
           'w': W, 'h': H, 'channels': 'R built up, G woods, B river bank'}
    with open(OUT + '.tmp', 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    for k, c in zip('RGB', (R, G, A)):
        print('%s mean %.3f, share over 0.5 %.3f' % (k, float(c.mean()), float((c > 0.5).mean())))
    print('%d x %d at %g m, %d KB, half %d KB, wrote %s' % (W, H, PX, art_files.size(full) // 1024, art_files.size(half) // 1024, OUT))
    if len(sys.argv) > 1:   # a preview: the four channels side by side
        prev = Image.new('RGB', (W * 2, H * 2))
        for k, c in enumerate((R, G, A, B)):
            prev.paste(Image.fromarray((c * 255).astype(np.uint8)).convert('RGB'), ((k % 2) * W, (k // 2) * H))
        prev.resize((W, H)).save(sys.argv[1], quality=85)


if __name__ == '__main__':
    main()
