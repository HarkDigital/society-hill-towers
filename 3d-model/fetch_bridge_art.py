#!/usr/bin/env python3
"""Generate the Delaware bridges' surfaces (Round 195, Mike: "Remodel ... the bridges"), from OpenAI's image API, written
to lidar_cache/bridge_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the usage).
bake_bridge_art.py makes the two textures the page reads from them (bridge_art.json names them).

Two kinds of picture:
- the tileable surfaces, each a flat square of one material photographed straight on under overcast light, repeating
  seamlessly both ways: the riveted, painted steel of the towers, trusses and floors (painted a neutral light grey, so the
  page can tint it Ben Franklin blue, the Whitman's green, the Tacony-Palmyra's green or the Betsy Ross's white), the
  rock-faced granite of the Ben Franklin's anchorages and piers and the Tacony-Palmyra's piers, and the weathered concrete
  of the Whitman's and the Betsy Ross's piers and anchorages;
- two straight-on elevations of Paul Cret's granite at the Ben Franklin's anchorages: a corner pylon's face above the
  deck (the cornice, the four grilled windows, the corbels, the blank panel and the bronze door: Camden_anchor_tower and
  New_Jersey_anchor_tower, July 2026, on Commons, viewed for reference only and never sent here), and the anchorage wall's
  top band (the cornice and the row of grilled windows in their recessed bays, 2012_Ben_Franklin_Bridge_west_anchorage).

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
BRIDGE_ART_MODEL picks the model (default gpt-image-2), BRIDGE_ART_QUALITY the quality (default high). Every prompt asks
for no lettering, no logos and no people.

Usage: python3 fetch_bridge_art.py [--only id,...] [--force] [--list] [--workers 3]"""
import argparse, concurrent.futures, json, os
import fetch_storefront_art as SF   # the API plumbing: api_key, call, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'bridge_art_raw')
MODEL = os.environ.get('BRIDGE_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('BRIDGE_ART_QUALITY', 'high')

TILE = ('Seamless tileable texture for a 3D city model: a perfectly orthographic, straight-on photograph of {what}. '
        'The picture shows about {m} metres by {m} metres of the surface and repeats seamlessly in both directions (what '
        'leaves the right edge comes back at the left, what leaves the top comes back at the bottom). Flat, even overcast '
        'daylight, no shadows cast from outside the frame, no perspective, no vignette; the surface fills the whole frame '
        'with no edges, corners, sky or ground. No lettering, no numbers, no logos, no people.')
ELEV = ('A perfectly orthographic, straight-on architectural elevation photograph of {what} Flat, even overcast daylight, '
        'no shadows cast from outside the frame, no perspective; the face fills the whole frame edge to edge, with no sky, '
        'no ground, no other buildings, no bridge steel in front of it. No lettering, no inscriptions, no numbers, no logos, '
        'no people.')

# id: (prompt, size)
IMAGES = {
    'steel': (TILE.format(m=3, what=(
        'the riveted structural steel of a 1920s suspension bridge, painted in a smooth, even, LIGHT NEUTRAL GREY industrial '
        'paint (no blue, no green, no rust colour overall: the model tints it later): built-up steel plates with straight '
        'butt seams, a horizontal splice plate and two vertical stiffener plates, regular rows of round domed rivet heads '
        'about 2.5 cm across along every seam and plate edge, the paint in fair condition with a faint brushed texture, a '
        'few tiny chips and very faint grime streaks running down')), '1024x1024'),
    'granite': (TILE.format(m=4.8, what=(
        'a rock-faced (quarry-faced) granite ashlar wall of a 1926 bridge anchorage: light grey granite blocks with a faint '
        'warm buff cast, each block\'s face rough, split and gently bulging, thin recessed pale mortar joints, perfectly '
        'level courses exactly 0.6 metres tall (eight courses in the picture), blocks 1.0 to 1.6 metres long with the '
        'vertical joints staggered course to course, a few faint rust-brown and darker grey water stains')), '1024x1024'),
    'concrete': (TILE.format(m=4, what=(
        'the weathered surface of a 1950s cast-in-place concrete bridge pier: light grey concrete with faint horizontal '
        'form-board lines about 30 cm apart, small air pockets, subtle mottling and faint darker water streaks running '
        'down')), '1024x1024'),
    'pylon': (ELEV.format(what=(
        'one face of a 1926 granite pylon standing at the corner of the anchorage of a great steel suspension bridge in '
        'Philadelphia, designed by Paul Cret, from the bridge deck to its top: a plain square tower face 8 metres wide and '
        '16 metres tall in smooth dressed light grey granite ashlar laid in level courses with fine joints and faint '
        'rust-brown water stains; at the very top a moulded granite cornice and a low plain parapet; under the cornice a '
        'row of four tall narrow window openings, each filled with a dark bronze ornamental grille; below them a band of '
        'four small projecting square stone corbels; in the lower half a tall recessed doorway with a dark bronze paneled '
        'door, flanked by two flat granite pilasters each with a small carved square medallion near its top, and over the '
        'door between the medallions a plain blank recessed stone panel with nothing carved on it.')), '768x1536'),
    'frieze': (ELEV.format(what=(
        'the top band of the long side wall of a 1926 granite bridge anchorage designed by Paul Cret, 15 metres wide and '
        '7.5 metres tall, repeating seamlessly left to right: along the top a moulded granite cornice; under it a row of '
        'exactly three identical bays, each a tall recessed panel between flat smooth granite pilasters, with one small '
        'square window in the upper part of the panel filled with a dark bronze lattice grille and a sloping granite sill '
        'below it; the pilasters and the panels in smooth dressed light grey granite ashlar; across the bottom of the '
        'picture a level string course and below it the rock-faced, rough split granite blocks of the wall beneath. '
        'Faint rust-brown water stains running down under the sills.')), '1536x768'),
}


def make(key, iid, force):
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, iid + '.png'), os.path.join(RAW, iid + '.json')
    if os.path.exists(png) and not force:
        return iid, 'kept'
    prompt, size = IMAGES[iid]
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = SF.call(key, SF.API, body, 'application/json')
    if not d:
        return iid, err
    SF.MODEL, SF.QUALITY = MODEL, QUALITY
    n = SF.save(png, meta, d, {'id': iid, 'prompt': prompt, 'size': size})
    return iid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    jobs = [k for k in IMAGES if not only or k in only]
    if a.list:
        for k in jobs:
            print(k, IMAGES[k][1])
        return
    key = SF.api_key()
    print('%d images, model %s, quality %s' % (len(jobs), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for iid, what in ex.map(lambda k: make(key, k, a.force), jobs):
            print(iid, what, flush=True)


if __name__ == '__main__':
    main()
