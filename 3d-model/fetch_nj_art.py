#!/usr/bin/env python3
"""Generate the USS New Jersey's surfaces (Round 195, Mike: "Remodel ... Battleship NJ"), from OpenAI's image API, written to
lidar_cache/nj_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the usage).
bake_nj_art.py cuts them into the one atlas the ship's shader reads (nj_art.json).

Four straight-on surfaces, each read by the page as detail over the paint it calibrates itself (the texel over the cell's
own mean), so the haze grey, the boot topping and the red bottom stay the page's colours and the pictures add only the
plates, the doors, the grit and the grain:
- hull: the welded side plating above the waterline, 20 m by 10 m, no fittings (the page draws the hull number, the
  anchors and the hawse pipes itself)
- bulkhead: one deck level of the superstructure's wall, deck to overhead (2.7 m), 5.4 m wide, its door and portholes
  kept off the left and right edges so the bake's blend across the wrap meets plain wall
- deck: the painted non-skid steel of the upper decks and the fantail, 8 m by 4 m
- teak: the main deck's weathered planking, the planks along the image (the bake cuts it on its own caulking seams, so
  the wrap across the planks is a seam)

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
NJ_ART_MODEL picks the model (default gpt-image-2), NJ_ART_QUALITY the quality (default high). Every prompt asks for no
lettering, no logos and no people.

Usage: python3 fetch_nj_art.py [--only id,...] [--force] [--list] [--workers 4]"""
import argparse, concurrent.futures, json, os
import fetch_storefront_art as SF   # the API plumbing: api_key, call, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'nj_art_raw')
MODEL = os.environ.get('NJ_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('NJ_ART_QUALITY', 'high')
SF.MODEL, SF.QUALITY = MODEL, QUALITY   # what save() records in the sidecar

NONE = ' No lettering, no numbers, no markings, no logos, no people.'
CELLS = {
    'hull': ('1536x768',
             'Seamless tileable texture for a 3D model: a perfectly straight-on, orthographic photograph of a section of the '
             'side of an American battleship\'s hull above the waterline, about 20 metres long and 10 metres tall, filling '
             'the whole frame. Large welded steel hull plates painted US Navy haze gray, a light neutral blue-grey: the '
             'horizontal and vertical plate seams faintly visible as fine raised lines, a few rows of small round rivet heads '
             'along some seams, gently rippled plating between the frames, subtle patches of touched-up paint in slightly '
             'different greys, a few faint thin rust streaks running straight down from tiny drain holes, light grime. Flat, '
             'even, soft overcast daylight, no cast shadows, no perspective, no reflections. The texture repeats seamlessly '
             'left to right and top to bottom. No waterline, no deck edge, no railings, no portholes, no anchors, no sky, no '
             'water.' + NONE),
    'bulkhead': ('1536x768',
                 'Texture for a 3D model that repeats seamlessly left to right: a perfectly straight-on, orthographic '
                 'photograph of one deck level of a US Navy battleship\'s superstructure wall, exactly one storey tall: the '
                 'bottom edge of the image is the steel deck line and the top edge is the overhead deck edge, about 5.4 metres '
                 'wide and 2.7 metres tall. A flat welded steel bulkhead painted US Navy haze gray. Near the middle stands one '
                 'grey steel watertight door with rounded corners, its raised coaming and its dogging handles; to one side of it '
                 'two round portholes with thick steel rims and dark glass, and on the other a small louvered vent and a '
                 'vertical pipe with a junction box. The left and right fifths of the image are plain painted bulkhead with '
                 'only faint weld seams. Light weathering, faint drips. Flat, even, soft overcast daylight, no cast shadows, '
                 'no perspective. No railings, no deck surface, no sky, no signs, no stencils.' + NONE),
    'deck': ('1536x768',
             'Seamless tileable texture for a 3D model: a straight-down top view of a battleship\'s painted steel deck, about '
             '8 metres by 4 metres, filling the whole frame: dark grey non-skid deck paint with a fine gritty surface, faint '
             'welded plate seams, a few flush round deck fittings and recessed tie-down cups, scuffs, worn lighter patches '
             'and faint rust spots. Flat, even, soft overcast daylight, no cast shadows, no perspective. The texture repeats '
             'seamlessly left to right and top to bottom. No painted lines, no stencils, no objects.' + NONE),
    'teak': ('1536x768',
             'Seamless tileable texture for a 3D model: a straight-down top view of a battleship\'s weathered teak wood main '
             'deck, about 6 metres by 3 metres, filling the whole frame. Long narrow teak planks exactly 15 centimetres wide '
             'run perfectly straight and horizontal from the left edge to the right edge, about twenty planks from top to '
             'bottom, with thin black pitch caulking seams between them and staggered butt joints. The wood is weathered to a '
             'silvery grey-brown with darker grain and a few warmer brown newer replacement planks, a few small round steel '
             'deck plugs. Flat, even, soft overcast daylight, no cast shadows, no perspective. The texture repeats seamlessly '
             'left to right and top to bottom. No objects, no steel plates, no paint.' + NONE),
}


def make(key, cid, force):
    size, prompt = CELLS[cid]
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, cid + '.png'), os.path.join(RAW, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = SF.call(key, SF.API, body, 'application/json')
    if not d:
        return cid, err
    n = SF.save(png, meta, d, {'id': cid, 'prompt': prompt, 'size': size})
    return cid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    ids = [c for c in CELLS if not only or c in only]
    if a.list:
        for c in ids:
            print(c, CELLS[c][0])
        return
    key = SF.api_key()
    print('%d images, model %s, quality %s' % (len(ids), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for cid, msg in ex.map(lambda c: make(key, c, a.force), ids):
            print(cid, msg, flush=True)


if __name__ == '__main__':
    main()
