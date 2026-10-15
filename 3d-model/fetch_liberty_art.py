#!/usr/bin/env python3
"""Generate One and Two Liberty Place's near detail (Round 195, Mike: "Remodel Liberty One, Liberty 2, ..."): the granite
base the towers stand on and the frames of the glazed crowns, from OpenAI's image API, written to
lidar_cache/liberty_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the usage).
bake_liberty_art.py keys the glass and packs the atlas the page lays on the towers' bases and crown slopes (LIBERTY_ART).

The references (Wikimedia Commons, the Library of Congress's Highsmith photograph, archipedia's entry) were looked at, never
sent: the base is three storeys of polished dark blue-grey granite with large lobby windows and an acid blue trim, the crown's
sloped glazing silver anodised caps over reflective glass. Every pane of glass is asked for as a flat chroma-key green
(#00FF00), so the bake finds the glass to the pixel (the page draws it: its reflection by day, the lobby's light after dark).
No lettering, no logos and no people anywhere.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
LIB_ART_MODEL picks the model (default gpt-image-2), LIB_ART_QUALITY the quality (default high).

Usage: python3 fetch_liberty_art.py [--only id,...] [--force] [--list] [--workers 3]"""
import argparse, concurrent.futures, json, os
import fetch_storefront_art as SF   # the API plumbing: api_key, call, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'liberty_art_raw')
MODEL = os.environ.get('LIB_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('LIB_ART_QUALITY', 'high')

GLASS = ('Every pane of glass is one flat uniform pure green (#00FF00) with no reflections, no texture, nothing behind it and '
         'no glazing bars drawn in the green; nothing else in the image is that green.')
FRAME = ('Architectural elevation photograph, perfectly orthographic and straight-on, of {what} The section fills the frame '
         'edge to edge and repeats seamlessly left to right: what leaves the right edge comes back at the left. {body} '
         + GLASS + ' No perspective, no vanishing lines, no camera tilt, every line exactly level and plumb. Soft even overcast '
         'daylight, no cast shadows, no sky, no ground, no street, no sidewalk. No people, no cars, no trees, no flags, no '
         'signs, no lettering, no numbers, no plaques and no logos. Photorealistic, high detail, natural colours.')

# id: (what, body, size)
CELLS = {
    # the lobby storeys on Market and 17th: tall glass between polished granite piers
    'base-lobby': ('the three-storey granite base of a 1987 Philadelphia postmodern office skyscraper (One Liberty Place, '
                   'Helmut Jahn), exactly 12 metres wide and 12 metres tall.',
                   'Polished dark blue-grey granite (a deep grey with a faint blue cast and fine black and white crystals, '
                   'mirror polished) clads everything that is not glass. Two structural bays: a granite pier 1.4 m wide at the '
                   'centre and a half pier 0.7 m wide at each side edge, a granite plinth 0.6 m tall along the bottom, a granite '
                   'spandrel band 0.9 m tall at 7.5 m, and a deep granite fascia 2.2 m tall along the top with a thin pale '
                   'acid-blue (light turquoise) painted metal reveal line 8 cm tall set into it. In each bay a double-height '
                   'lobby window from the plinth to the spandrel band in slim silver anodised aluminium frames (three tall '
                   'panes side by side and a transom at 3 m), and above the band a row of three second-storey windows.',
                   '1024x1024'),
    # the granite base's plainer walls (the returns, the back of the block, the stepped corners)
    'base-wall': ('the three-storey granite base of a 1987 Philadelphia postmodern office skyscraper (One Liberty Place, '
                  'Helmut Jahn), exactly 12 metres wide and 12 metres tall.',
                  'Polished dark blue-grey granite (a deep grey with a faint blue cast and fine black and white crystals, '
                  'mirror polished) laid in large rectangular panels 1.5 m wide and 0.9 m tall with fine straight joints, '
                  'clads the whole wall; a granite plinth 0.6 m tall along the bottom, a deep granite fascia 2.2 m tall along '
                  'the top with a thin pale acid-blue (light turquoise) painted metal reveal line 8 cm tall set into it, and '
                  'one row of three square windows 1.8 m wide on each of the two upper storeys in slim silver aluminium '
                  'frames, centred in each half of the wall.',
                  '1024x1024'),
    # the crown's sloped glazing seen square on (the bake keys the panes and keeps the caps)
    'glazing': ('the sloped glazing of the stepped glass crown of a 1987 postmodern skyscraper, photographed exactly '
                'perpendicular to the glass, a section exactly 6 metres wide and 6 metres tall.',
                'Silver anodised aluminium pressure caps 8 cm wide run straight down the slope every 1.5 m (four bays) and '
                'flat horizontal silver caps 6 cm wide cross them every 1.5 m (four courses), each with a thin dark rubber '
                'gasket line along both its edges; the aluminium is lightly weathered with faint grey streaks below each '
                'horizontal cap.',
                '1024x1024'),
}


def make(key, cid, force):
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, cid + '.png'), os.path.join(RAW, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    what, body, size = CELLS[cid]
    prompt = FRAME.format(what=what, body=body)
    req = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                      'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = SF.call(key, SF.API, req, 'application/json')
    if not d:
        return cid, err
    SF.MODEL, SF.QUALITY = MODEL, QUALITY   # the sidecar's record of what made it
    n = SF.save(png, meta, d, {'id': cid, 'prompt': prompt, 'size': size})
    return cid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    jobs = [c for c in CELLS if not only or c in only]
    if a.list:
        for c in jobs:
            print(c, CELLS[c][2])
        return
    key = SF.api_key()
    print('%d images, model %s, quality %s' % (len(jobs), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for cid, what in ex.map(lambda c: make(key, c, a.force), jobs):
            print(cid, what, flush=True)


if __name__ == '__main__':
    main()
