#!/usr/bin/env python3
"""Bake the buildings round City Hall their own facades (Round 198) into tower_art.json, which build.py inlines as
TOWER_ART, and the atlas itself into art/towers/ (art_files.py: content-hashed files, a phone's half copy).

Each strip fetch_tower_art.py made (lidar_cache/tower_art_raw/<id>.png: a straight-on elevation a few bays wide, from the
sidewalk to the cornice, the glass a flat green and the sky a flat magenta) is cut into three cells:
- the top: from the roofline (the first row the sky leaves) down to the middle of the spandrel over the first typical
  storey;
- the shaft: whole typical storeys from the middle of one spandrel to the middle of another (the storeys are found as the
  longest run of window bands of one height at one pitch), which repeat up the tower;
- the base: from the middle of the spandrel under the last typical storey down to the foot of the wall (the sidewalk the
  model draws along the foot comes off).
Across, every cell is cut to the same whole number of the strip's bays from the middle of a pier (the glass's column
profile's repeat), so the three stand on one bay line, and eased to its far edge so it repeats. Each is taken to its
metres: the bay and the storey are the research's (TOWERS), the base and the top keep the picture's own proportions at
that storey (a base the model drew a storey and a half tall stays one); the atlas holds every cell at one density, as
large as fits.

The glass: the key (a soft matte, the spill taken off the frames round it) is painted as dark glass with a little sky
in its head, each pane a shade of its own, and marked in the mask: r the glass, b its height in its window (0 at the sill,
1 at the head: the page's room light), g a number a window; opaque RGB (an alpha under 255 reaches WebGL premultiplied on
WebKit). Every cell carries its bays and storeys, the pier's and the spandrel's place (the page cuts its rooms there, so no
window straddles two), its mean colour in linear light and its glass share.

Usage: python3 bake_tower_art.py [--preview DIR] [--only id,...]   (--only bakes a few strips to the preview, no manifest)"""
import argparse, json, math, os, sys, zlib
import art_files
import numpy as np
from PIL import Image, ImageFilter
from bake_cityhall_art import dilate, label, pack, gutter
from fetch_tower_art import STRIPS   # each strip's bays as asked for

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'tower_art_raw')
OUT = os.path.join(HERE, 'tower_art.json')
KIND = 'towers'
PAD = 16              # the gutter round every cell at the computer's size (the phone's half has 8): the page caps its
                      # mip level so a read never reaches past it (TOWN_LOD in app.js)
AW = 4096             # the atlas's width; its height is what the cells need, at most AH_MAX
AH_MAX = 2048
DENS_MAX = 40.0       # px a metre at most (the cells are scaled down together until they pack)
CELL_W = 11.0         # a cell holds as many whole bays as fit in this many metres (at least one): the bays a strip drew
                      # are near alike, and the atlas holds 25 buildings at about 30 px a metre this way
GLASS = np.array([30, 36, 44], np.float32)      # the glass's own dark (sRGB), its head toward SKY
SKY = np.array([78, 90, 104], np.float32)
GAP = np.array([62, 63, 66], np.float32)        # what shows through a parapet's openings: the roof behind, in shade

# the buildings: towers.json's name (the page joins by it), the strips (one a building, a strip a face where they differ:
# 'dir' the face's outward direction in the scene frame), the research's bay and storey in metres, whether its rooms are
# homes or hotel rooms (the night's lamps and blinds) or offices, and 'pts': points inside the records that are the
# building where no towers.json spec reaches them (a part under 45 m, the churches, a block the spec's point misses)
TOWERS = {}


def tower(bid, name, strips, bay, floor, home=False, pts=(), **kw):
    TOWERS[bid] = dict(name=name, strips=strips, bay=bay, floor=floor, home=home, pts=[list(p) for p in pts], **kw)


tower('wanamaker', "Wanamaker Building (Macy's)", [{'id': 'wanamaker'}], bay=6.4, floor=4.6, pts=[(-1485, -655)], cornice=[1.6, 1.4])
# the Masonic Temple (refs/masonic): three tall granite storeys to the corbel-table cornice at about 24 m, the great SW tower
# to 62 m and its four pinnacles to 71, the slender NW belfry to 40; LANDMARK_H keeps its body at 30 m (a church, no
# spec), so a point finds it, and its towers are boxes of its own (the generic church tower is not raised: noSpire)
tower('masonic', 'Masonic Temple', [{'id': 'masonic', 'whole': (24.0, 3)}, {'id': 'masonic-tower', 'only': True, 'whole': (38.0, 3), 'bay': 10.2}],
      bay=5.6, floor=8.0, pts=[(-1528.5, -900.8)], hex='#cccdc6', noSpire=1, pin=[(-1528.5, -900.8, 24.0)],
      mass=[dict(k='box', at=[-1528.5, -900.8], w=72.0, d=43.4, y1=24.0, nobox=True, cap=dict(k='hip', h=9.0, hex='#7d8288')),
            dict(k='box', at=[-1561.9, -889.5], w=10.2, d=10.2, y0=20, y1=62, strip=1, hex='#cccdc6',
                 cap=dict(k='pins', h=9, w=1.8, hex='#c4c5be')),
            dict(k='box', at=[-1558.1, -925.0], w=5.9, d=5.9, y0=20, y1=37, strip=1, hex='#cccdc6',
                 cap=dict(k='pins', h=3.5, w=1.1, hex='#c4c5be'))])
# the Residence Inn (refs/resinn): the slab 17 by 55 m rises to about 73 m, then steps back in tiers to the central tower
# and its crown at 106 (the record is one box at 106: pinned to 73, the tiers its own boxes, each with the crown on top)
tower('resinn', 'Residence Inn Philadelphia Center City', [{'id': 'resinn'}], bay=6.5, floor=3.65, home=True, hex='#a8937a',
      pin=[(-1494.4, -789.3, 73.0)],
      mass=[dict(k='box', at=[-1494.4, -789.3], w=17.0, d=37.0, y0=72.9, y1=85.0),
            dict(k='box', at=[-1494.4, -789.3], w=15.0, d=25.0, y0=84.9, y1=98.0),
            dict(k='box', at=[-1494.4, -789.3], w=11.0, d=14.0, y0=97.9, y1=106.0)])

# Arch Street Methodist (refs/archumc): marble walls about 11 m to the eave under a steep slate gable to 22 m, the tower at
# the Broad and Arch corner to 29 m with its corner pinnacles, the octagonal spire to 64 (LANDMARK_H kept it at 25 m with a
# generic tower: pinned to the eave here, its roof, tower and spire its own)
tower('archumc', 'Arch Street United Methodist Church', [{'id': 'archumc', 'whole': (11.0, 1)}, {'id': 'archumc-tower', 'only': True, 'whole': (29.0, 3), 'bay': 8.0}], bay=4.8, floor=11.0,
      pts=[(-1548.1, -953.4)], hex='#c4c3b9', noSpire=1, pin=[(-1548.1, -953.4, 11.0)],
      mass=[dict(k='box', at=[-1548.1, -953.4], w=23.0, d=42.0, y1=11.0, nobox=True, cap=dict(k='gable', h=11.0, hex='#6e6b68', end='#c4c3b9')),
            dict(k='box', at=[-1552.7, -971.4], w=8.0, d=8.0, y1=29.0, hex='#c4c3b9', strip=1, cap=dict(k='spire', h=35.0, hex='#c8c7bd')),
            dict(k='box', at=[-1552.7, -971.4], w=8.0, d=8.0, y1=29.0, nobox=True, cap=dict(k='pins', h=4.5, w=1.0, hex='#c8c7bd'))])
# the Municipal Services Building (refs/msb): the granite grid of framed windows on a recessed lobby, the blank attic band
tower('msb', 'Municipal Services Building', [{'id': 'msb'}], bay=1.73, floor=4.0, hex='#dddcd4', glass='#4a5058')
# One South Broad (refs/osb): limestone piers between paired windows, its own parts' setbacks (wide.b64) and lantern
tower('osb', 'One South Broad (Lincoln-Liberty Building)', [{'id': 'osb'}], bay=6.2, floor=4.0, hex='#c9c4b8')
# the Widener Building (refs/widener): limestone, the colonnade under its terra cotta cornice
tower('widener', 'Widener Building', [{'id': 'widener'}], bay=6.1, floor=4.0, hex='#d3cec2', cornice=[1.8, 1.6])
# the Girard Trust tower (refs/girard) in white marble under its copper hip, and the domed banking hall beside it (the
# records wide.b64 drew as glass parts: a point names their strip)
tower('girard', 'Ritz-Carlton Philadelphia / Girard Trust Tower (10 S Broad)', [{'id': 'girard'}, {'id': 'girard-bank', 'only': True, 'whole': (20.0, 1), 'bay': 6.0}],
      bay=3.3, floor=3.7, home=True, hex='#eeeae2', cornice=[1.4, 1.2], pts=[(-1669.5, -632.2, 1)],
      mass=[dict(k='dome', at=[-1669.5, -632.5], r=11.0, y0=24.0, hex='#d8d4ca'),
            dict(k='box', at=[-1665.2, -662.5], w=35.4, d=12.6, y1=118.0, nobox=True, cap=dict(k='hip', h=5.0, hex='#8db8b0'))])
# Centre Square (refs/csq1, refs/csq2): buff precast and ribbon windows on a three-level base of piers
tower('csq1', 'Centre Square I (east tower, 1500 Market)', [{'id': 'csq1'}], bay=2.8, floor=3.8, hex='#c2b49c', glass='#2a3038')
tower('csq2', 'Centre Square II (west tower, 1500 Market)', [{'id': 'csq2'}], bay=2.8, floor=3.7, hex='#c2b49c', glass='#2a3038')
# Three Penn Center (refs/threepenn): white bands and blue-green ribbons all round
tower('threepenn', 'Three Penn Center (1515 Market)', [{'id': 'threepenn', 'baseH': 6.0}], bay=2.9, floor=3.7, hex='#e3e5e2', glass='#5c8a8c')
# One Penn Square West (refs/opsw): tan punched grid, the rounded green glass corner toward City Hall (north-east)
tower('opsw', 'One Penn Square West', [{'id': 'opsw'}, {'id': 'opsw-glass', 'dir': [0.815, -0.579], 'dot': 0.8, 'bay': 1.5}],
      bay=3.0, floor=3.95, hex='#a99b87', glass='#2f4a44')

# the Wanamaker (refs/wanamaker, the NRHP nomination): granite on a limestone base, the two-storey arcade under the cornice
TOWERS['wanamaker'].update(bay=6.1, floor=5.0, cornice=[1.8, 1.8], hex='#bdb6ad')
# the Land Title Building (refs/landtitle): the 1902 south tower to 101 m in banded masonry under its colonnade and cornice,
# the 1897 north building (its two records, pinned to 62 m) in brick with oriels
tower('landtitle', 'Land Title Building (100 S Broad)', [{'id': 'landtitle'}, {'id': 'landtitle-north', 'only': True, 'bay': 6.0}],
      bay=4.2, floor=3.9, hex='#d6d2c8', cornice=[2.0, 2.0], pts=[(-1673.0, -578.0, 1), (-1692.0, -581.0, 1)],
      pin=[(-1673.0, -578.0, 62.0), (-1692.0, -581.0, 62.0)])
# PSFS (refs/psfs): the slab's long faces with limestone piers, its cantilevered north end in ribbons, the black spine (a
# record of its own, pinned to 148 m), the base's black granite; the sign on the slab's roof reads east and west, white on
# blue by day and red after dark; the 1948 mast on the spine
tower('psfs', 'PSFS Building / Loews Philadelphia Hotel', [{'id': 'psfs'}, {'id': 'psfs-north', 'dir': [0.167, -0.986], 'dot': 0.85},
      {'id': 'psfs-spine', 'only': True}], bay=5.2, floor=3.8, home=True, hex='#b5b0a6',
      pts=[(-1328.9, -658.4, 2), (-1318.6, -682.3), (-1338.1, -685.0), (-1349.2, -684.9)], pin=[(-1328.9, -658.4, 148.0)],
      mass=[dict(k='sign', at=[-1321.4, -682.8], axis=1, y0=141.0, h=8.2, post=1.5, panel='#1f4f86', day='#f2f2ee', night='#ff2a1c'),
            dict(k='mast', at=[-1328.9, -658.4], y0=148.0, h=79.0, w=5.0, top=1.2)])
# the Marriott Downtown (refs/marriott): rose-taupe precast, punched windows with teal glass
tower('marriott', 'Philadelphia Marriott Downtown (1201 Market)', [{'id': 'marriott'}], bay=3.0, floor=3.05, home=True,
      hex='#a8978f', glass='#3d7f7a')
# the North American Building (refs/northam): red-brown masonry, pedimented windows over the storefronts
tower('northam', 'North American Building', [{'id': 'northam'}], bay=3.4, floor=3.7, hex='#8a6a5e')
# the Ellington, the former Greenfield Building (refs/ellington): buff brick piers, a limestone base, a dentilled cornice
tower('ellington', 'The Ellington', [{'id': 'ellington'}], bay=3.5, floor=3.6, home=True, hex='#c6ae86', cornice=[1.5, 1.5])

# One Parkway (refs/oneparkway): brushed stainless steel panels, fins every fourth column; wide.b64 holds only OSM's 59 m
# part over its north two thirds, so its 18 storeys stand again as boxes on its own outline (the west third set back)
tower('oneparkway', 'One Parkway', [{'id': 'oneparkway'}], bay=1.95, floor=4.1, hex='#a9b0b3', glass='#2d2e34',
      mass=[dict(k='box', at=[-1798.5, -1069.3], w=52.7, d=38.9, y1=78.8), dict(k='box', at=[-1791.4, -1043.6], w=30.1, d=9.6, y1=78.8)])
# Five Penn Center (refs/fivepenn): buff piers and spandrels, deep-set dark glass, the glass podium of about 2016
tower('fivepenn', 'Five Penn Center (1601 Market)', [{'id': 'fivepenn'}], bay=7.6, floor=3.75, hex='#bdb4a4', glass='#1c2228')

# Four Penn Center (refs/fourpenn): stone bands and green ribbons; wide.b64 holds only its penthouse part (88 m), so the
# 74 by 31 m slab stands again to 85 m on OSM's outline
tower('fourpenn', 'Four Penn Center', [{'id': 'fourpenn', 'baseH': 6.5}], bay=3.3, floor=3.75, hex='#cfc7b8', glass='#5e7d72',
      mass=[dict(k='box', at=[-1918.7, -897.9], w=74.0, d=31.4, y1=85.0)])
# One Penn Center (refs/onepenn): limestone piers, carved spandrels, the toothed parapet; the slab pinned to 95 m under its
# attic spine (100.6), the lower rear wings over the station its own too
tower('onepenn', 'One Penn Center at Suburban Station (1617 JFK)', [{'id': 'onepenn', 'bayAuto': True}], bay=2.9, floor=3.9, hex='#c8c0ae',
      glass='#6f7f86', pts=[(-1900.1, -1008.7), (-1905.1, -1008.8)], pin=[(-1878.4, -954.5, 95.0)])
# the Wells Fargo Building (refs/wellsfargo): limestone, the colonnaded crowns on its H's wings (its parts in wide.b64)
tower('wellsfargo', 'Wells Fargo Building (123 S Broad)', [{'id': 'wellsfargo'}], bay=3.2, floor=3.9, hex='#c4bfb4',
      glass='#2a3a48', cornice=[1.5, 1.4])
# Two Penn Center (refs/twopenn): white enamel bands and blue ribbon glass, not a curtain wall (towers.json's 'real')
tower('twopenn', 'Two Penn Center (1500 JFK)', [{'id': 'twopenn'}], bay=3.0, floor=3.7, hex='#e4e0d6', glass='#3a6e96')
# the Bellevue (refs/bellevue): banded buff stone, its carved top under the dark curved mansard bonnets at its corners
tower('bellevue', 'The Bellevue (Hyatt at the Bellevue, 200 S Broad)', [{'id': 'bellevue'}], bay=3.6, floor=3.9, home=True,
      hex='#d8cdb6', cornice=[1.6, 1.5],
      mass=[dict(k='box', at=at, w=13.0, d=13.0, y1=80.0, nobox=True, cap=dict(k='mansard', h=8.0, hex='#3b4048'))
            for at in ([-1699.0, -374.2], [-1691.6, -417.6], [-1742.2, -381.6], [-1734.8, -425.0])])
# Jefferson Tower, the former Aramark Tower (refs/jefftower): granite bands and dark ribbons, maroon bands every third storey
tower('jefftower', 'Jefferson Tower (1101 Market, former Aramark Tower)', [{'id': 'jefftower'}], bay=3.0, floor=3.8,
      hex='#b9a594', glass='#2c3a48')
# the towers round them whose bodies the packer lost (it kept only the OSM part): Eight Penn Center, a glass curtain wall
# (its glass system, towers.json 'real'), 23 storeys on its own outline under the penthouse part
BODIES = [dict(k='glassbox', name='Eight Penn Center', at=[-1980.8, -911.0], w=39.2, d=25.1, y1=86.5)]

# by-eye overrides of what the finder takes (rows of the picture): 'foot' the wall's foot, 'roof' the roofline,
# 'typ' the typical storeys' first and last band (counted from the top, 0 the topmost band the finder lists)
FIX = {
    'landtitle': {'typ': (4, 8)},   # the storey of round-arched windows under the colonnade has the typical storeys' height: it is the top's
}


def lum(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def keys(a):
    """The green glass (a soft matte 0..1 and its hard core) and the magenta sky."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = np.maximum(r, b)
    soft = np.clip((g - mx - 40.0) / 90.0, 0, 1) * (g > 1.25 * mx + 10)
    hard = (g - mx > 90) & (g > 1.6 * mx + 20)
    mag = (r > 170) & (b > 170) & (g < 120) & (np.abs(r - b) < 70)
    return soft, hard, mag


def runs(v, thr):
    """(start, end) of each run of v over thr (end inclusive)."""
    out, s = [], None
    for i, x in enumerate(v):
        if x > thr and s is None:
            s = i
        elif x <= thr and s is not None:
            out.append((s, i - 1)); s = None
    if s is not None:
        out.append((s, len(v) - 1))
    return out


def period(profile, expect):
    """The strongest repeat of a profile within 0.6 to 1.5 times the expected one, in pixels (fractional), or None."""
    p = profile - profile.mean()
    n, best, lag0 = len(p), 0.0, None
    for lag in range(max(4, int(expect * 0.6)), min(n - 4, int(expect * 1.5)) + 1):
        c = float(np.dot(p[:-lag], p[lag:])) / (n - lag)
        if c > best:
            best, lag0 = c, lag
    if lag0 is None:
        return None
    # refine to a fraction of a pixel by the parabola through the peak's neighbours
    def cc(l):
        return float(np.dot(p[:-l], p[l:])) / (n - l)
    a, b, c = cc(lag0 - 1), cc(lag0), cc(lag0 + 1)
    d = a - 2 * b + c
    return lag0 + (0.5 * (a - c) / d if abs(d) > 1e-9 else 0.0)


def edges(sid, a, hard, mag):
    """The strip's roofline (the first row the sky leaves) and the wall's foot (the sidewalk's edge, when one is drawn)."""
    H, W = hard.shape
    fx = FIX.get(sid, {})
    magf = mag.mean(1)
    roof = fx.get('roof')
    if roof is None:
        roof = 0
        for y in range(H // 2):
            if magf[y] > 0.5:
                roof = y + 1
    foot = fx.get('foot')
    if foot is None:
        L = lum(a).mean(1)
        lo = int(H * 0.88)
        d = np.abs(np.diff(L[lo:]))
        k = int(np.argmax(d))
        foot = lo + k + 1 if d[k] > 18 else H
        gy = np.nonzero(hard.mean(1) > 0.02)[0]
        if len(gy) and foot <= gy.max():
            foot = H
    return roof, foot


def find(sid, a, soft, hard, mag):
    """The strip's rows: the roofline, the foot, the typical storeys' bands and their pitch; and its bay repeat."""
    H, W = hard.shape
    fx = FIX.get(sid, {})
    magf = mag.mean(1)
    roof = fx.get('roof')
    if roof is None:
        roof = 0
        for y in range(H // 2):
            if magf[y] > 0.5:
                roof = y + 1
    # the foot: in the bottom eighth, the strongest step of the row's mean luminance (the sidewalk's edge), when strong
    foot = fx.get('foot')
    if foot is None:
        L = lum(a).mean(1)
        lo = int(H * 0.88)
        d = np.abs(np.diff(L[lo:]))
        k = int(np.argmax(d))
        foot = lo + k + 1 if d[k] > 18 else H
        # the glass of the base never stands below the foot
        gy = np.nonzero(hard.mean(1) > 0.02)[0]
        if len(gy) and foot <= gy.max():
            foot = H
    gr = hard[roof:foot].mean(1)
    raw = [(y0 + roof, y1 + roof) for y0, y1 in runs(gr, 0.04) if y1 - y0 >= 4]
    # a window's sashes and lights are one band: a gap under a fifth of the taller neighbour's height and 6 px (a
    # meeting rail, a transom, an arch's springing) closes
    bands = []
    for b in raw:
        if bands and b[0] - bands[-1][1] < 6 + 0.2 * max(b[1] - b[0], bands[-1][1] - bands[-1][0]):
            bands[-1] = (bands[-1][0], b[1])
        else:
            bands.append(b)
    bands = [b for b in bands if b[1] - b[0] >= 8]
    # the typical storeys: the longest run of consecutive bands of one height (14% of the run's first) at one pitch (12%):
    # the model draws a little perspective into a tall strip, its storeys a few pixels taller toward the foot
    best = (0, 0)
    for i in range(len(bands)):
        j = i
        while j + 1 < len(bands):
            hr, h1 = bands[i][1] - bands[i][0], bands[j + 1][1] - bands[j + 1][0]
            if abs(h1 - hr) > 0.14 * hr:
                break
            if j > i:
                p0, p1 = bands[i + 1][0] - bands[i][0], bands[j + 1][0] - bands[j][0]
                if abs(p1 - p0) > 0.12 * p0:
                    break
            j += 1
        if j - i > best[1] - best[0]:
            best = (i, j)
    if 'typ' in fx:
        best = tuple(fx['typ'])
    i0, i1 = best
    if i1 - i0 < 2:
        raise SystemExit('%s: found %d typical storeys in %d bands (%s): set FIX' % (sid, i1 - i0 + 1, len(bands), bands))
    pitch = (bands[i1][0] - bands[i0][0]) / (i1 - i0)
    # the bay: the glass's column profile over the typical storeys
    rows = slice(bands[i0][0], bands[i1][1] + 1)
    col = hard[rows].mean(0).astype(np.float64)
    nb = STRIPS[sid]['nb'] if sid in STRIPS else 4
    px = period(col, W / nb)
    if px is None:
        raise SystemExit('%s: no bay repeat' % sid)
    return dict(roof=roof, foot=foot, bands=bands, i0=i0, i1=i1, pitch=pitch, px=px, col=col)


def mid_pier(col, px, W):
    """The column a pier's middle stands on (the emptiest phase of the glass's repeat), first from the left."""
    k = int(round(px))
    acc = np.zeros(k)
    cnt = np.zeros(k)
    for x in range(W):
        acc[int(x % px) % k] += col[x]; cnt[int(x % px) % k] += 1
    prof = acc / np.maximum(cnt, 1)
    # the middle of the widest stretch at the minimum (a pier is a flat run of no glass)
    lo = prof.min() + 0.02
    zero = prof <= lo
    best, bs = None, -1
    for s in range(k):
        if zero[s] and not zero[(s - 1) % k]:
            n = 0
            while zero[(s + n) % k] and n < k:
                n += 1
            if n > bs:
                bs, best = n, (s + n / 2.0) % px
    return best if best is not None else float(np.argmin(prof))


def paint_glass(a, soft, hard, seed, tint=None):
    """The key painted as glass: dark, a little sky toward each window's head, each window a shade of its own (tint: the
    building's photographed glass, sRGB hex, for its body and a lighter turn of it for the head); and the mask's channels
    (r the glass, g a number a window, b the height in the window)."""
    H, W = hard.shape
    # windows: the panes with their muntins (the hard key closed across 6 px), each its own number and height
    win = dilate(hard, 3)
    lab, boxes = label(win)
    vp = np.zeros((H, W), np.float32)
    num = np.zeros((H, W), np.float32)
    shade = np.ones((H, W), np.float32)
    rng = np.random.RandomState(seed)
    for k, (y0, x0, y1, x1, c) in enumerate(boxes):
        sel = lab[y0:y1 + 1, x0:x1 + 1] == k + 1
        ys = np.arange(y0, y1 + 1, dtype=np.float32)[:, None]
        v = (y1 - ys) / max(1.0, y1 - y0)
        vp[y0:y1 + 1, x0:x1 + 1][sel] = np.broadcast_to(v, sel.shape)[sel]
        num[y0:y1 + 1, x0:x1 + 1][sel] = 1 + (k * 37) % 254
        shade[y0:y1 + 1, x0:x1 + 1][sel] = 0.85 + 0.3 * rng.rand()
    # the spill on the frames round the glass: green over the other channels taken down to them
    near = dilate(soft > 0, 3) & (soft < 1)
    gmax = np.maximum(a[..., 0], a[..., 2])
    sp = near & (a[..., 1] > gmax + 4)
    a[sp, 1] = gmax[sp] + 4
    t = np.clip(vp, 0, 1)[..., None] ** 2.2
    G0, S0 = GLASS, SKY
    if tint:
        c = np.array([int(tint[1:3], 16), int(tint[3:5], 16), int(tint[5:7], 16)], np.float32)
        G0, S0 = c * 0.85, np.minimum(255, c * 1.25 + 30)
    g = (G0[None, None] * (1 - t) + S0[None, None] * t) * shade[..., None]
    g += (rng.rand(H, W, 1).astype(np.float32) - 0.5) * 4
    al = soft[..., None]
    out = a * (1 - al) + g * al
    mk = np.zeros((H, W, 3), np.float32)
    mk[..., 0] = soft * 255
    mk[..., 1] = num * (soft > 0.5)
    mk[..., 2] = np.clip(vp, 0, 1) * 255 * (soft > 0.05)
    return out, mk


def ease_wrap(a, frac=0.05):
    """A cell that repeats across: each side eased toward the far side's edge (half way at the very edge)."""
    W = a.shape[1]
    n = max(2, int(W * frac))
    out = a.copy()
    w = np.linspace(0.5, 0.0, n)[None, :, None]
    mid = (a[:, :1] + a[:, W - 1:W]) / 2
    out[:, :n] = a[:, :n] * (1 - w) + mid * w
    out[:, W - n:] = a[:, W - n:] * (1 - w[:, ::-1]) + mid * w[:, ::-1]
    return out


def zone_grid(hard, y0, y1, pitch):
    """A zone's storeys (whole, at least one) and the spandrel's place in a storey from its foot (the emptiest row)."""
    nf = max(1, int(round((y1 - y0) / pitch)))
    prof = hard[y0:y1].mean(1)
    if not len(prof):
        return nf, 0.0
    H = y1 - y0
    k = int(round(pitch))
    acc = np.zeros(k); cnt = np.zeros(k)
    for y in range(H):
        f = (H - 1 - y) % pitch   # from the zone's foot
        acc[int(f) % k] += prof[y]; cnt[int(f) % k] += 1
    pr = acc / np.maximum(cnt, 1)
    return nf, round((float(np.argmin(pr)) + 0.5) / k, 3)


def bake_whole(sid, spec, a, soft, hard, mag):
    """A whole wall (spec['whole']: its height in metres and its storeys): one cell from the roofline to the foot, whole
    bays across (the full width for a strip of one bay), which the page lays from the foot up, repeated when the wall is
    taller than it."""
    H, W = hard.shape
    roof, foot = edges(sid, a, hard, mag)
    nb = STRIPS[sid]['nb'] if sid in STRIPS else 1
    hm, nf = spec['whole']
    if nb > 1:
        col = hard[roof:foot].mean(0).astype(np.float64)
        px = period(col, W / nb)
        if px is None:
            raise SystemExit('%s: no bay repeat' % sid)
        x0 = mid_pier(col, px, W)
        nbays = min(int((W - x0) // px), max(1, int(CELL_W // spec['bay'])))
        xs = (x0, x0 + nbays * px)
    else:
        px, nbays, xs = float(W), 1, (0.0, float(W))
    a, mk = paint_glass(a, soft, hard, zlib.crc32(sid.encode()) % 10000, spec.get('glass'))
    box = (int(round(xs[0])), roof, int(round(xs[1])), foot)
    nf2, spand = zone_grid(hard[box[1]:box[3], box[0]:box[2]], 0, foot - roof, (foot - roof) / nf)
    cell = dict(col=a[roof:foot, box[0]:box[2]], msk=mk[roof:foot, box[0]:box[2]], m=[round(nbays * spec['bay'], 3), hm],
                nb=nbays, nf=nf, spand=spand, src=box, whole=1)
    f = dict(bands=[], i0=0, i1=0, roof=roof, foot=foot)
    return dict(cells={'shaft': cell}, nb=nbays, px=px, pitch=(foot - roof) / nf, pier=0.0, find=f)


def bake_strip(sid, spec, preview):
    """One strip's three cells at their source resolution, with their metres."""
    im = Image.open(os.path.join(RAW, sid + '.png')).convert('RGB')
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    soft, hard, mag = keys(a)
    # the sky the cells keep (between a balustrade's balusters, a crenellation's merlons, the fins over a parapet): the
    # shade of the roof behind them, never the key's magenta
    near = dilate(mag, 1)
    a[near] = GAP
    if spec.get('whole'):
        return bake_whole(sid, spec, a, soft, hard, mag)
    f = find(sid, a, soft, hard, mag)
    bands, i0, i1, pitch, px = f['bands'], f['i0'], f['i1'], f['pitch'], f['px']
    a, mk = paint_glass(a, soft, hard, zlib.crc32(sid.encode()) % 10000, spec.get('glass'))
    # the spandrel's middle under / over each typical band
    def below(i):   # under band i: half way to the next band down (or half a spandrel)
        if i + 1 < len(bands):
            return (bands[i][1] + bands[i + 1][0]) / 2.0
        return bands[i][1] + (pitch - (bands[i][1] - bands[i][0])) / 2.0
    def above(i):
        if i > 0:
            return (bands[i - 1][1] + bands[i][0]) / 2.0
        return bands[i][0] - (pitch - (bands[i][1] - bands[i][0])) / 2.0
    y_top = f['roof']
    # the top's foot just over the first typical storey's windows, the base's head just under the last's: each keeps the
    # whole spandrel beside it (the belt course, the entablature, the frieze a base or a crown ends in), and the storeys
    # between are cut from the middle of one spandrel to the middle of another
    y_top_end = bands[i0][0] - 2
    y_base = bands[i1][1] + 2
    # the shaft: whole storeys between the middles of two interior spandrels, as many as there are (at most three)
    k = min(3, i1 - i0 - 1) if i1 - i0 >= 2 else 1
    s0 = below(i0)                 # under the first typical band
    s1 = below(i0 + k)
    # across: whole bays from a pier's middle
    bay, floor = spec['bay'], spec['floor']
    if spec.get('bayAuto'):   # the bay the picture's own proportions give at the research's storey (its repeat a group of windows)
        bay = round(px / (pitch / floor), 2)
        spec['bay'] = bay
    x0 = mid_pier(f['col'], px, W)
    nbays = min(int((W - x0) // px), max(1, int(CELL_W // bay)))
    xs = (x0, x0 + nbays * px)
    ppm = pitch / floor            # the picture's px a metre up, from its storey
    cells = {}
    for zone, (ya, yb) in (('top', (y_top, y_top_end)), ('shaft', (s0, s1)), ('base', (y_base, f['foot']))):
        ya, yb = int(round(ya)), int(round(yb))
        if yb - ya < 8:
            continue
        box = (int(round(xs[0])), ya, int(round(xs[1])), yb)
        col = a[box[1]:box[3], box[0]:box[2]]
        msk = mk[box[1]:box[3], box[0]:box[2]]
        hm = (yb - ya) / ppm if zone != 'shaft' else k * floor
        if zone != 'shaft' and spec.get(zone + 'H'):   # the research's own height for a base or a top the model drew short
            hm = spec[zone + 'H']
        nf, spand = zone_grid(hard[box[1]:box[3], box[0]:box[2]], 0, yb - ya, pitch)
        if zone == 'shaft':
            nf = k
        cells[zone] = dict(col=col, msk=msk, m=[round(nbays * bay, 3), round(hm, 3)], nb=nbays, nf=nf, spand=spand, src=box)
    pier = round(((x0 - xs[0]) % px) / px, 3)   # 0: every cell starts at a pier's middle
    return dict(cells=cells, nb=nbays, px=px, pitch=pitch, pier=pier, find=f)


def to_density(cell, dens):
    """A cell's colour and mask at dens px a metre (the colour eased across where it repeats)."""
    w, h = max(8, int(round(cell['m'][0] * dens))), max(8, int(round(cell['m'][1] * dens)))
    c = Image.fromarray(np.clip(cell['col'], 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
    m = Image.fromarray(np.clip(cell['msk'], 0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    c = np.asarray(c).astype(np.float32)
    c = ease_wrap(c, 0.03)
    return c, np.asarray(m).astype(np.float32)


def srgb_lin(v):
    v = v / 255.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


TOWERS_STRIP = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='')
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
    for bid, t in TOWERS.items():
        for s in t['strips']:
            TOWERS_STRIP[s['id']] = dict(s, bay=s.get('bay', t['bay']), floor=s.get('floor', t['floor']), glass=s.get('glass', t.get('glass')), bid=bid)
    strips = {}
    for sid, spec in TOWERS_STRIP.items():
        if only and sid not in only:
            continue
        if not os.path.exists(os.path.join(RAW, sid + '.png')):
            if only:
                sys.exit('%s: no picture yet (fetch_tower_art.py --only %s)' % (sid, sid))
            print('%-14s no picture yet, left out' % sid)
            continue
        strips[sid] = bake_strip(sid, spec, a.preview)
        s = strips[sid]
        f = s['find']
        print('%-14s %d bays of %.0f px, storey %.1f px, %d bands, typical %d..%d, roof %d foot %d; %s' % (
            sid, s['nb'], s['px'], s['pitch'], len(f['bands']), f['i0'], f['i1'], f['roof'], f['foot'],
            ', '.join('%s %.1fx%.1f m (%d storeys)' % (z, c['m'][0], c['m'][1], c['nf']) for z, c in s['cells'].items())))
        if a.preview:
            im = Image.open(os.path.join(RAW, sid + '.png')).convert('RGB')
            from PIL import ImageDraw
            d = ImageDraw.Draw(im)
            for z, c in s['cells'].items():
                x0, y0, x1, y1 = c['src']
                d.rectangle((x0, y0, x1 - 1, y1 - 1), outline={'top': (255, 0, 0), 'shaft': (0, 0, 255), 'base': (255, 160, 0)}[z], width=4)
            im.save(os.path.join(a.preview, sid + '-cut.jpg'), quality=85)
    if only:   # a few strips to the preview only (none written without one)
        if not a.preview:
            return
        dens = 32.0
        for sid, s in strips.items():
            for z, c in s['cells'].items():
                col, msk = to_density(c, dens)
                tiled = np.concatenate([col, col], 1) if z != 'shaft' else np.concatenate([np.concatenate([col, col], 1)] * 2, 0)
                Image.fromarray(np.clip(tiled, 0, 255).astype(np.uint8)).save(os.path.join(a.preview, '%s-%s.jpg' % (sid, z)), quality=88)
                Image.fromarray(np.clip(msk, 0, 255).astype(np.uint8)).save(os.path.join(a.preview, '%s-%s-mask.png' % (sid, z)))
        return
    # the atlas: every cell at one density, the largest that packs (each strip's cells in their order: top, shaft, base)
    order = [(sid, z) for sid in strips for z in ('top', 'shaft', 'base') if z in strips[sid]['cells']]
    dens = DENS_MAX
    while True:
        sizes = [(max(8, int(round(strips[s]['cells'][z]['m'][0] * dens))), max(8, int(round(strips[s]['cells'][z]['m'][1] * dens)))) for s, z in order]
        pos = pack(sizes, AW, AH_MAX, PAD)
        if pos is not None:
            break
        dens *= 0.96
    AH = max(p[1] + s[1] + PAD for p, s in zip(pos, sizes))
    AH = int(math.ceil(AH / 64.0) * 64)
    atlas = np.zeros((AH, AW, 3), np.float32)
    matlas = np.zeros((AH, AW, 3), np.float32)
    rect = {}
    for (sid, z), (x, y), (w, h) in zip(order, pos, sizes):
        col, msk = to_density(strips[sid]['cells'][z], dens)
        atlas[y:y + h, x:x + w] = col[:h, :w]
        matlas[y:y + h, x:x + w] = msk[:h, :w]
        wrap = 'xy' if z == 'shaft' else True
        gutter(atlas, x, y, w, h, PAD, wrap)
        gutter(matlas, x, y, w, h, PAD, wrap)
        rect[(sid, z)] = [x, y, w, h]
    img = Image.fromarray(np.clip(atlas, 0, 255).astype(np.uint8))
    mimg = Image.fromarray(np.clip(matlas, 0, 255).astype(np.uint8))
    half = img.resize((AW // 2, AH // 2), Image.LANCZOS)
    mhalf = mimg.resize((AW // 2, AH // 2), Image.BILINEAR)
    mquarter = mimg.resize((AW // 4, AH // 4), Image.BILINEAR)
    files = {
        'img': art_files.write(img, KIND, 'atlas', 'WEBP', quality=84, method=6),
        'imgHalf': art_files.write(half, KIND, 'atlas-half', 'WEBP', quality=82, method=6),
        'mask': art_files.write(mhalf, KIND, 'atlas-mask', 'PNG', optimize=True),
        'maskHalf': art_files.write(mquarter, KIND, 'atlas-mask-half', 'PNG', optimize=True),
    }
    towers = {}
    for bid, t in TOWERS.items():
        out_strips = []
        for s in t['strips']:
            sid = s['id']
            if sid not in strips:
                continue
            st = strips[sid]
            cells = {}
            for z, c in st['cells'].items():
                x, y, w, h = rect[(sid, z)]
                col = atlas[y:y + h, x:x + w]
                mean = srgb_lin(col.reshape(-1, 3)).mean(0)
                glass = float((matlas[y:y + h, x:x + w, 0] > 127).mean())
                cells[z] = dict(r=[x, y, w, h], m=c['m'], nb=c['nb'], nf=c['nf'], pier=st['pier'], spand=c['spand'],
                                mean=[round(float(v), 4) for v in mean], glass=round(glass, 3))
                if c.get('whole'):
                    cells[z]['whole'] = 1
            extra = {'only': 1} if s.get('only') else {}
            if s.get('dot') is not None:
                extra['dot'] = s['dot']
            sb = TOWERS_STRIP[sid]['bay']
            if abs(sb - t['bay']) > 1e-6:
                extra['bay'] = sb
            out_strips.append(dict(dir=s.get('dir'), **extra, **cells))
        if out_strips:
            towers[bid] = dict(name=t['name'], bay=t['bay'], floor=t['floor'], home=1 if t['home'] else 0, pts=t['pts'],
                               strips=out_strips, **{k: v for k, v in t.items() if k not in ('name', 'strips', 'bay', 'floor', 'home', 'pts')})
    out = dict(v=1, w=AW, h=AH, pad=PAD, dens=round(dens, 2), towers=towers, bodies=BODIES, **files)
    print('atlas %dx%d at %.1f px/m, %d cells of %d buildings; %d KB, half %d KB, mask %d KB, mask half %d KB; pruned %d' % (
        AW, AH, dens, len(order), len(towers), art_files.size(files['img']) // 1024, art_files.size(files['imgHalf']) // 1024,
        art_files.size(files['mask']) // 1024, art_files.size(files['maskHalf']) // 1024, art_files.prune(KIND)))
    with open(OUT + '.tmp', 'w') as fo:
        json.dump(out, fo, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    if a.preview:
        img.save(os.path.join(a.preview, 'atlas.jpg'), quality=85)
        mimg.save(os.path.join(a.preview, 'atlas-mask.png'))
    print('wrote', OUT, '%.1f KB' % (os.path.getsize(OUT) / 1024))


if __name__ == '__main__':
    main()
