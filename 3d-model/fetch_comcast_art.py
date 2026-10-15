#!/usr/bin/env python3
"""Generate the Comcast towers' cladding (Round 195, Mike: "Remodel ... both Comcast towers"; photographic realism) from
OpenAI's image API, written to lidar_cache/comcast_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the
size, when, the usage). bake_comcast_art.py folds each into a seamless tile and packs the strip the page's cladding
material reads (CMR in app.js: the Comcast Technology Center's spine, its louvres, its frosted lantern, its canopy's soffit
and its dark grey panels).

Each image is one straight-on elevation of a surface the photographs show, a whole number of its own modules repeating
(the CTC's units are 1.52 m by 4.42 m, Enclos), under flat overcast light, so the page can lay it at its true size. Every
prompt asks for no lettering, no logos and no people.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
COMCAST_ART_MODEL picks the model (default gpt-image-2), COMCAST_ART_QUALITY the quality (default high).

Usage: python3 fetch_comcast_art.py [--only id,...] [--force] [--list] [--workers 3]"""
import argparse, concurrent.futures, json, os
import fetch_storefront_art as SF   # the API plumbing: api_key, call, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'comcast_art_raw')
MODEL = os.environ.get('COMCAST_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('COMCAST_ART_QUALITY', 'high')

TILE = ('Seamless tileable texture for a 3D city model: a perfectly orthographic, straight-on view of {what}, repeating '
        'seamlessly in both directions (what leaves the right edge comes back at the left, what leaves the top comes back at '
        'the bottom; every joint evenly spaced). Photographed in flat, even overcast daylight with no cast shadows from '
        'anything outside the surface and no reflections of buildings or sky. No building edges or corners, no ground, no '
        'sky, no perspective, no people, no lettering, no logos.')

# id: (what, size, the tile's size in metres [along, up]); the layers' order is the page's (CMR_LAYERS)
TILES = {
    'spine': ('the smooth pale silver-grey metal cladding of the concrete core of a 2018 glass skyscraper: satin-finish '
              'light silver aluminium panels exactly 4 panels wide and 2 panels tall, every panel 1.52 m wide by 4.42 m tall '
              'and the same size, separated by thin straight recessed dark grey joints, a faint vertical brushed grain and a '
              'very slight tonal variation from panel to panel; no windows and no glass', '1024x1536', [6.08, 8.84]),
    'louvre': ('the mechanical floors\' screen of a 2018 skyscraper: dark charcoal grey anodised aluminium horizontal louvre '
               'blades 15 cm apart, every blade tilted down with a thin dark shadow line beneath it and the dark plant room '
               'barely visible between the blades, held by slim vertical charcoal mullions exactly 1.52 m apart; exactly 2 '
               'mullion bays wide and 4.42 m tall', '1024x1536', [3.04, 4.42]),
    'lantern': ('the illuminated lantern crowning a 2018 skyscraper, by day: tall panels of acid-etched frosted white glass '
                '1.52 m wide by 4.42 m tall in slim silver aluminium frames, exactly 4 panels wide and 2 panels tall, and '
                'behind the frosted glass the soft, blurred pale grey silhouette of a steel cross-brace, one large X from '
                'corner to corner of the whole picture; the glass otherwise an even milky white with a faint cool tint, '
                'nothing clear and nothing behind it in focus', '1024x1536', [6.08, 8.84]),
    'soffit': ('the underside of a building\'s cantilevered entrance canopy, looking straight up: a ceiling of long warm '
               'brown hardwood slats 8 cm wide with dark 2 cm gaps between them, all running the same way, exactly 30 slats '
               'across, the wood with a natural grain and a slight tonal variation from slat to slat; no lights, no fixtures',
               '1024x1024', [3.0, 3.0]),
    'panel': ('the dark charcoal grey metal cladding of a skyscraper\'s elevator core: painted aluminium plate panels exactly '
              '2 panels wide and 1 panel tall, every panel 1.52 m wide by 4.42 m tall, separated by thin straight recessed '
              'black joints, a faint satin sheen and a slight tonal variation from panel to panel; no windows and no glass',
              '1024x1536', [3.04, 4.42]),
}
ORDER = ['spine', 'louvre', 'lantern', 'soffit', 'panel']


def make(key, tid, force):
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, tid + '.png'), os.path.join(RAW, tid + '.json')
    if os.path.exists(png) and not force:
        return tid, 'kept'
    what, size, _ = TILES[tid]
    prompt = TILE.format(what=what)
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = SF.call(key, SF.API, body, 'application/json')
    if not d:
        return tid, err
    SF.MODEL, SF.QUALITY = MODEL, QUALITY
    n = SF.save(png, meta, d, {'id': tid, 'prompt': prompt, 'size': size, 'tile_m': TILES[tid][2]})
    return tid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    jobs = [t for t in ORDER if not only or t in only]
    if a.list:
        for t in jobs:
            print(t, TILES[t][1], TILES[t][2])
        return
    key = SF.api_key()
    print('%d images, model %s, quality %s' % (len(jobs), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for tid, what in ex.map(lambda t: make(key, t, a.force), jobs):
            print(tid, what, flush=True)


if __name__ == '__main__':
    main()
