"""Round 243 (Mike, Nov 12, from street level north of City Hall: "I see this texture a lot on the ground floor of large
buildings. It is not good. Can we swap it out with something better?"): the street floors under the generated tower and
mid-rise walls (bake_fronts.py bake_base, the realism pass's critic gap 4), made again, behind `?streetfloor=`.

What he saw: a street floor's window mask (red where the picture is glass: glossy by day, lit after dark) is found by
bake_base from the picture's darkness alone, and on the glass-heavy pictures, whose panes carry reflections and an
interior as dark as their frames, it came out as salt and pepper. Every pane then drew as patches of glossy reflection
and patches of matte black, the blocky black shapes in the lobby glass of 1,573 tower bases (lobby1 561, lobby2 358,
office1 466, office2 188) and of 7,627 more (shop1, shop2, aptmod1, aptmod2, loft1, loft2).

Two answers, each a set of records the page lays over FRONTS_DATA.bases (app.js streetFloorBases):
- clean: the same pictures, each ragged mask redrawn as its panes' own rectangles (MASK_RECTS, measured off the 768 by 512
  tile on a 40 by 20 grid), so a pane is all glass; the seven masks that were already whole are kept as they are;
- lit: clean, and the three glass lobbies (lobby1, lobby2, office2) and office1 made again (fetch: this script's
  --fetch, gpt-image-2 at bake_fronts' frame) with clear glass onto a lit lobby, the black void of the old prompt's "the
  glass dark and unlit" gone, each with its rectangles (LIT).

Writes street_floor_art.json and art/floors/. Usage: python3 bake_street_floors.py [--preview DIR]"""
import argparse, json, os, sys
import art_files
import numpy as np
from PIL import Image, ImageDraw
from bake_fronts import BASE_TOP, BASE_FOOT, BASE_H, RAW5

HERE = os.path.dirname(os.path.abspath(__file__))
LIT_RAW = os.path.join(RAW5, 'base_lit')
MW, MH = 384, 256   # the masks' size (bake_base's)

# each ragged street floor's panes, x0, y0, x1, y1 as shares of the tile (u along the street, v down from the head)
MASK_RECTS = {
    'lobby1': [(0, .02, .147, .953), (.247, .02, .753, .953), (.859, .02, 1, .953)],
    'lobby2': [(0, .045, 1, .918)],
    'office2': [(0, .088, .147, .898), (.182, .088, .341, .898), (.378, .088, .479, .898), (.517, .088, .62, .898),
                (.655, .088, .755, .898), (.794, .088, .889, .898), (.927, .088, 1, .898)],
    'aptmod1': [(.15, .297, .397, .902), (.501, .297, .87, .902)],
    'aptmod2': [(0, .094, .05, .928), (.208, .094, .426, .928), (.508, .094, .758, .928), (.846, .094, 1, .928)],
    'loft1': [(.147, .156, .43, .738), (.927, .156, 1, .738)],
    'shop1': [(.098, .098, .388, .8), (.43, .098, .664, .8), (.703, .098, .947, .8), (.277, .8, .382, .9)],
    'shop2': [(0, .195, .026, .752), (.076, .195, .349, .752), (.397, .195, .599, .88), (.651, .195, .918, .752),
              (.97, .195, 1, .752)],
    'loft2': [(.081, .127, .358, .898), (.436, .127, .605, .898), (.651, .127, .927, .898)],
}
# the lit lobbies: the base kind, the raw picture it is made from (two made a kind, the one kept named), its panes
LIT = {
    'lobby1': ('lobby1_2', [(0, .049, .099, .87), (.198, .049, .8, .902), (.898, .049, 1, .87)]),
    'lobby2': ('lobby2_2', [(0, .152, 1, .889)]),
    'office1': ('office1_2', [(0, .078, .161, .898), (.224, .078, .758, .898), (.818, .078, 1, .898)]),
    'office2': ('office2_2', [(0, .1, .182, .86), (.232, .1, .495, .86), (.534, .1, .779, .86), (.828, .1, 1, .86)]),
}


def rect_mask(rects, lit=False):
    """red: the panes (glossy by day, darkened and lit after dark); green, a lit lobby's panes only: the picture is its
    own light after dark (app.js reads it under ?streetfloor=lit)"""
    mk = np.zeros((MH, MW, 4), np.uint8)
    mk[..., 3] = 255
    for x0, y0, x1, y1 in rects:
        sl = (slice(int(round(y0 * MH)), int(round(y1 * MH))), slice(int(round(x0 * MW)), int(round(x1 * MW))))
        mk[sl + (0,)] = 255
        if lit:
            mk[sl + (1,)] = 255
    return Image.fromarray(mk)


def tile(im):
    """bake_base's own cut: the sidewalk and the sill over the storey off, the edges cross-faded with each other"""
    im = im.convert('RGB')
    im = im.crop((0, int(round(im.height * BASE_TOP)), im.width, int(round(im.height * BASE_FOOT))))
    a = np.asarray(im.resize((1024, 683), Image.LANCZOS), np.float32)
    k = 24
    w = np.linspace(0.5, 0.0, k)[None, :, None]
    left, right = a[:, :k].copy(), a[:, -k:][:, ::-1].copy()
    a[:, :k] = left * (1 - w) + right * w
    a[:, -k:] = (right * (1 - w) + left * w)[:, ::-1]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def preview_of(im, mk, path):
    a = np.asarray(im.convert('RGB').resize((MW, MH), Image.LANCZOS)).astype(float)
    g = np.asarray(mk)[..., 0] > 127
    a[g] = a[g] * 0.45 + np.array([255, 0, 0]) * 0.55
    Image.fromarray(a.astype(np.uint8)).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
    fronts = json.load(open(os.path.join(HERE, 'fronts.json')))
    bases = fronts['bases']
    clean = {}
    for b, rects in MASK_RECTS.items():
        if b not in bases:
            sys.exit('no street floor %s in fronts.json' % b)
        mk = rect_mask(rects)
        clean[b] = {'mask': art_files.write(mk, 'floors', b + '-mask', 'PNG', optimize=True)}
        if a.preview:
            preview_of(Image.open(os.path.join(HERE, bases[b]['img'])), mk, os.path.join(a.preview, 'clean-%s.png' % b))
        print('clean %-8s %d panes, %.0f%% glass' % (b, len(rects), 100 * (np.asarray(mk)[..., 0] > 127).mean()))
    lit = {}
    for b, (raw, rects) in LIT.items():
        t = tile(Image.open(os.path.join(LIT_RAW, raw + '.png')))
        mk = rect_mask(rects, True)
        lit[b] = {'img': art_files.write(t.resize((768, 512), Image.LANCZOS), 'floors', 'lit-' + b, 'WEBP', quality=80, method=6),
                  'imgHalf': art_files.write(t.resize((384, 256), Image.LANCZOS), 'floors', 'lit-' + b + '-half', 'WEBP', quality=78, method=6),
                  'mask': art_files.write(mk, 'floors', 'lit-' + b + '-mask', 'PNG', optimize=True),
                  'w': round(BASE_H * 1536 / (1024 * (BASE_FOOT - BASE_TOP)), 2), 'h': BASE_H, 'raw': raw}
        if a.preview:
            preview_of(t, mk, os.path.join(a.preview, 'lit-%s.png' % b))
        print('lit   %-8s from %s, %d panes, %d KB' % (b, raw, len(rects), art_files.size(lit[b]['img']) // 1024))
    print('pruned %d old floor files' % art_files.prune('floors'))
    out = {'v': 1, 'clean': clean, 'lit': lit}
    with open(os.path.join(HERE, 'street_floor_art.json'), 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    print('street_floor_art.json: %d clean masks, %d lit floors' % (len(clean), len(lit)))


if __name__ == '__main__':
    main()
