#!/usr/bin/env python3
"""Generate the cruiser Olympia's surfaces (Round 215, Mike, with a night screenshot of Penn's Landing: "Whatever boat this
is next to the moshulu needs to be remodeled with the Chat GPT API"), from OpenAI's image API, written to
lidar_cache/olympia_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the usage).
bake_olympia_art.py cuts them into the one atlas the ship's shader reads (olympia_art.json).

Four straight-on surfaces, each read by the page as detail over the paint it calibrates itself (the texel over the cell's
own mean, as the New Jersey's), so the white hull, the red boot top and the buff stay the page's colours and the pictures
add only the plates, the rivets, the doors, the grime and the grain (the references, looked at and never sent: Wikimedia
Commons 'OLYMPIA (C-6) in Philadelphia 20240529.jpg', 'OLYMPIA berthed at Penn's Landing 20240529.jpg', 'Olympia Penn's
Landing PA1.jpg', 'USS Olympia;c0605.jpg', and the city's 2024 3-inch orthophoto):
- hull: the white riveted side plating of an 1890s steel cruiser, 20 m by 10 m, its lapped strakes and rivet rows, no
  fittings (the page draws the portholes, the sponsons and the boot top itself)
- house: one deck level of the buff superstructure's wall, 5.4 m by 2.4 m, a door and two ports kept off the left and right
  edges so the bake's blend across the wrap meets plain wall
- deck: the spar deck's weathered pine planking, the planks along the image (the bake cuts it on its own seams)
- buff: the buff riveted plating of the funnels, the turrets and the casings, 6 m by 3 m, seamless

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
OLYMPIA_ART_MODEL picks the model (default gpt-image-2), OLYMPIA_ART_QUALITY the quality (default high). Every prompt asks
for no lettering, no logos and no people.

Usage: python3 fetch_olympia_art.py [--only id,...] [--force] [--list] [--workers 4]"""
import argparse, concurrent.futures, json, os
import fetch_storefront_art as SF   # the API plumbing: api_key, call, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'olympia_art_raw')
MODEL = os.environ.get('OLYMPIA_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('OLYMPIA_ART_QUALITY', 'high')
SF.MODEL, SF.QUALITY = MODEL, QUALITY   # what save() records in the sidecar

NONE = ' No lettering, no numbers, no markings, no logos, no people.'
CELLS = {
    'hull': ('1536x768',
             'Seamless tileable texture for a 3D model: a perfectly straight-on, orthographic photograph of a section of the '
             'side of an 1890s steel protected cruiser\'s hull above the waterline, about 20 metres long and 10 metres tall, '
             'filling the whole frame. Riveted steel hull plates painted a clean warm white, old and well kept: long '
             'horizontal strakes of overlapping plates, each lapped edge a fine raised line with a soft shadow under it, '
             'close rows of round rivet heads along every seam and up every butt joint, the plates gently rippled between '
             'the frames, a few thin rust-brown weeping streaks running straight down from rivets, faint grime and touched-up '
             'patches in slightly different whites. Flat, even, soft overcast daylight, no cast shadows, no perspective, no '
             'reflections. The texture repeats seamlessly left to right and top to bottom. No waterline, no deck edge, no '
             'railings, no portholes, no anchors, no guns, no sky, no water.' + NONE),
    'house': ('1536x768',
              'Texture for a 3D model that repeats seamlessly left to right: a perfectly straight-on, orthographic photograph '
              'of one deck level of the superstructure wall of an 1890s steel naval cruiser, exactly one storey tall: the '
              'bottom edge of the image is the deck line and the top edge is the deck edge above, about 5.4 metres wide and '
              '2.4 metres tall. Riveted steel plating painted buff, a warm ochre tan, with rows of rivets along the seams. '
              'Near the middle one narrow steel door with a rounded top, painted buff, its brass handle; to one side of it two '
              'round portholes with thick brass rims and dark glass, on the other a small louvred vent. The left and right '
              'fifths of the image are plain painted plating with only rivet seams. Light weathering, faint drips. Flat, '
              'even, soft overcast daylight, no cast shadows, no perspective. No railings, no deck surface, no sky.' + NONE),
    'deck': ('1536x768',
             'Seamless tileable texture for a 3D model: a straight-down top view of the weathered wooden upper deck of an '
             '1890s naval cruiser, about 6 metres by 3 metres, filling the whole frame. Long narrow pine deck planks exactly '
             '14 centimetres wide run perfectly straight and horizontal from the left edge to the right edge, about twenty '
             'planks from top to bottom, with thin dark caulking seams between them and staggered butt joints. The wood is '
             'weathered to a pale silvery grey with darker grain, a few warmer brown newer planks, a few small round wooden '
             'deck plugs. Flat, even, soft overcast daylight, no cast shadows, no perspective. The texture repeats seamlessly '
             'left to right and top to bottom. No objects, no steel plates, no paint.' + NONE),
    'buff': ('1536x768',
             'Seamless tileable texture for a 3D model: a perfectly straight-on, orthographic photograph of riveted steel '
             'plating from the funnel of an 1890s naval cruiser, about 6 metres wide and 3 metres tall, filling the whole '
             'frame. The steel is painted buff, a warm ochre tan, old and well kept: vertical and horizontal plate seams with '
             'rows of round rivet heads, gently rippled plates, faint soot and grime, a few small rust spots and thin drips. '
             'Flat, even, soft overcast daylight, no cast shadows, no perspective. The texture repeats seamlessly left to '
             'right and top to bottom. No pipes, no ladders, no railings, no sky.' + NONE),
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
