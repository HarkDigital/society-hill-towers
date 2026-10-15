#!/usr/bin/env python3
"""Generate the Society Hill Towers' concrete (Round 195, Mike: "Remodel the Society Hill Towers, where this all started.
All 3 towers are identical, so you only need to model one."), from OpenAI's image API, written to
lidar_cache/sht_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the usage).
bake_sht_art.py makes the chosen one tile, measures its mean and writes it under art/sht/ (sht_art.json).

The towers' look is drawn by the page: Pei's cast-in-place grid (the bays, the reveals, the glass, the rooms, their blinds
and their lamps) is ray-cast in the facade shader, so the only picture it needs is the grain of the concrete itself: a
patch of the wall's surface with no edges, no windows and no joints, laid on every concrete face by its own metres and
taken only as detail over the calibrated colour (texel over the picture's mean). Several candidates are made; the bake
takes the one named on its command line.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
SHT_ART_MODEL picks the model (default gpt-image-2), SHT_ART_QUALITY the quality (default high). Every prompt asks for no
lettering, no logos and no people.

Usage: python3 fetch_sht_art.py [--only id,...] [--force] [--list] [--workers 3]"""
import argparse, concurrent.futures, json, os
import fetch_storefront_art as SF   # the API plumbing: api_key, call, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'sht_art_raw')
MODEL = os.environ.get('SHT_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('SHT_ART_QUALITY', 'high')

BASE = ('Seamless tileable surface texture for a 3D city model: a perfectly flat, straight-on, orthographic photograph of '
        'a 4 metre by 4 metre patch of {what}. {detail} Soft, even, overcast daylight from the front: no cast shadows, no '
        'highlights, no vignetting, no gradient across the picture. The patch fills the frame edge to edge and repeats '
        'seamlessly left to right and top to bottom. No edges, no corners, no windows, no joints between panels, no '
        'objects, no plants, no people, no lettering, no numbers, no logos. Photorealistic, natural colours.')

CANDIDATES = [
    ('concrete-a', 'the smooth cast-in-place architectural concrete wall of a 1964 I. M. Pei apartment tower in Philadelphia',
     'Warm light buff concrete, a pale cream beige, under a thin weathered masonry coating: very subtle large soft mottling, '
     'faint darker blotches where rain has run, fine pinholes and tiny air voids, two faint horizontal lines left by the '
     'plywood formwork, a light grey-brown film of city grime.'),
    ('concrete-b', 'the smooth formed concrete of a 1960s Philadelphia modernist tower, cast in place against plywood forms',
     'Pale warm sandy beige concrete with a soft, slightly chalky surface: faint plywood grain and the ghost of form panel '
     'edges, gentle tonal variation from one pour to the next, sparse small air pockets, and a very light, even patina of '
     'soot and weathering. The colour is uniform at a distance.'),
    ('concrete-c', 'the light buff exposed concrete of a Brutalist residential tower built in 1964',
     'Smooth cream-tan concrete, lightly sandblasted so a very fine sand aggregate shows, faint irregular clouding in the '
     'tone, small scattered pores, and a soft, uneven film of weathering that is slightly darker in places. No cracks, no '
     'stains with hard edges.'),
]


def make(key, cid, what, detail, force):
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, cid + '.png'), os.path.join(RAW, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    prompt = BASE.format(what=what, detail=detail)
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': '1024x1024', 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = SF.call(key, SF.API, body, 'application/json')
    if not d:
        return cid, err
    SF.MODEL, SF.QUALITY = MODEL, QUALITY
    n = SF.save(png, meta, d, {'id': cid, 'stage': 'concrete', 'prompt': prompt, 'size': '1024x1024'})
    return cid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    jobs = [c for c in CANDIDATES if not only or c[0] in only]
    if a.list:
        for c in jobs:
            print(c[0])
        return
    key = SF.api_key()
    print('%d images, model %s, quality %s' % (len(jobs), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for cid, what in ex.map(lambda c: make(key, c[0], c[1], c[2], a.force), jobs):
            print(cid, what, flush=True)


if __name__ == '__main__':
    main()
