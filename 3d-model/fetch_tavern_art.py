#!/usr/bin/env python3
"""Generate A Man Full of Trouble's own art (Round 199, Mike: "Man Full of Trouble needs to look like the other newer
textures"): the materials and the openings of the 1759 house at 127 Spruce Street, from OpenAI's image API, written to
lidar_cache/tavern_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the usage).
bake_tavern_art.py cuts them into the one atlas the page's tavern material wears.

Two kinds of image:
  swatches  the Flemish bond brick with its glazed headers, the cedar shingles of the roof, the pent and the dormers,
            the cream paint of the trim, and the marble of the steps: each a straight-on photograph of the material
            alone, which the bake cuts on its own courses (bake_wall_art.course_tile) or blends, so it repeats;
  elements  the openings as the house has them on Spruce (refs: Wikimedia Commons, 'A Man Full of Trouble Tavern' and
            'Man Full of Trouble Tavern - Philadelphia', and HABS PA-51-PHILA-276A): the six-panel door under its
            four-light transom, the ground floor's window behind its closed board shutters, the nine-over-nine sash of the
            upper floor, a pair of the upper floor's raised-panel shutters (each leaf is cut out by the bake), and the
            dormers' six-over-six sash. Each fills the frame from casing edge to casing edge, at the casing's own
            proportions, every pane a flat chroma-key green (#00FF00) so the bake finds the glass exactly: the page draws
            the glass itself (its reflections and the rooms behind it).
Which variant is chosen is CHOSEN in bake_tavern_art.py, set by eye against the reference photos (every image was looked
at). The reference photos were looked at for these prompts and never sent.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; --force makes it again, --only <id>[,<id>] makes some. TAVERN_ART_MODEL picks
the model (default gpt-image-2), TAVERN_ART_QUALITY the quality (default high), TAVERN_ART_RAW the folder (default
lidar_cache/tavern_art_raw). Every prompt asks for no lettering, no logos and no signs.

Usage: python3 fetch_tavern_art.py [--only id,...] [--force] [--list] [--workers 2]"""
import argparse, concurrent.futures, json, os
import fetch_storefront_art as SF   # the API plumbing (the key, retries) is the storefronts'

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('TAVERN_ART_RAW') or os.path.join(HERE, 'lidar_cache', 'tavern_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('TAVERN_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('TAVERN_ART_QUALITY', 'high')
# each element at its casing's own proportions (width by height in metres, the model's sizes in multiples of 16)
SIZES = {'swatch': '1024x1024', 'door': '656x1632', 'winshut': '944x1600', 'sash': '912x1616', 'shutpair': '784x1616',
         'dsash': '1088x1280'}
FALLBACK = {'656x1632': '1024x1536', '944x1600': '1024x1536', '912x1616': '1024x1536', '784x1616': '1024x1536',
            '1088x1280': '1024x1024'}

ENDING = ('Soft even overcast daylight with no cast shadows. No people, no plants, no signs, no lettering, no numbers, no '
          'logos. Photorealistic, high detail, natural colours.')
SWATCH = ('Seamless tileable texture for a 3D city model: a photograph taken looking straight at {what}, perpendicular to '
          'it, filling the whole frame evenly{courses}. No edges, no corners, no openings, no objects, no cast shadows. '
          'Soft even overcast daylight. Natural colours, photorealistic, uniform detail across the whole image so it '
          'repeats without a visible seam.')
KEY = ('Every pane of glass is filled with flat, uniform, pure chroma-key green (#00FF00) with no texture, no reflections '
       'and no shading, so the panes can be cut out later; the wood is real painted wood.')
ELEVATION = ('Architectural elevation photograph, perfectly orthographic and straight-on, {what} of a restored 1759 '
             'brick house in Society Hill, Philadelphia. The image is exactly the wooden casing and what is inside it, '
             'filling the frame edge to edge: the left, right and top edges of the image are the outer edges of a plain '
             'flat wooden casing about {casing} centimetres wide, and the bottom edge is {foot}. {inside} All the wood is '
             'painted one warm off-white cream, old and lightly weathered, with soft wear on the edges and a little grime '
             'low down. The whole image is {w} metres wide and {h} metres tall. {key}No perspective, no vanishing lines, '
             'every vertical line vertical. No brick, no wall, no steps, nothing outside the casing. ')
CREAM = 'painted one warm off-white cream'

JOBS = [
    # the swatches
    ('brick-a', 'swatch', SWATCH.format(
        what='the eighteenth-century Flemish bond brickwork of a 1759 colonial house in Society Hill, Philadelphia, about '
             '1.8 metres across and about twenty-six courses high',
        courses=', the courses running exactly horizontally. Every course alternates a long stretcher and a short header '
                'end, each header centred over a stretcher of the course below; the headers are glazed, dark blue-grey to '
                'purple-black with a faint sheen; the stretchers are soft handmade orange-red to deep red bricks with '
                'slightly irregular rounded edges and small pits; pale grey-buff lime mortar joints about one centimetre '
                'wide, slightly recessed and weathered; faint soot and rain staining')),
    ('brick-b', 'swatch', SWATCH.format(
        what='the old Flemish bond brick wall of a restored 1759 Philadelphia tavern, about 1.8 metres across and about '
             'twenty-six courses high',
        courses=', the courses running exactly horizontally. In every course long red stretchers alternate with short '
                'header ends, and every header is a darker glazed brick, blue-black to plum, so the wall has a regular '
                'checker of dark headers; the stretchers vary from salmon and orange-red to brick red, handmade with '
                'softly rounded arrises; light buff lime mortar, struck flush and weathered; gentle overall weathering')),
    ('shingle-a', 'swatch', SWATCH.format(
        what='a pitched roof of weathered hand-split cedar wood shingles on a restored 1759 colonial Philadelphia house, '
             'about two metres across',
        courses=', the courses running exactly horizontally with about thirteen centimetres of each shingle exposed, '
                'shingles of random widths from eight to thirty centimetres with narrow staggered gaps, weathered '
                'silver-grey wood with warmer brown streaks and a little grime')),
    ('shingle-b', 'swatch', SWATCH.format(
        what='a roof of old weathered cedar shakes on an eighteenth-century house in Philadelphia, about two metres across',
        courses=', the butts in straight horizontal courses about thirteen centimetres apart, shingles of random widths '
                'with narrow dark gaps staggered between courses, grey-brown weathered wood, slightly curled butt edges')),
    ('paint-a', 'swatch', SWATCH.format(
        what='a flat old wooden board ' + CREAM + ', about one metre across',
        courses=': one continuous smooth painted surface with no joints, the faint wood grain running horizontally '
                'through many coats of paint, soft brush marks along the grain, very fine hairline crazing and a little '
                'grime')),
    ('marble-a', 'swatch', SWATCH.format(
        what='the worn top of an old white marble doorstep in Philadelphia, about sixty centimetres across',
        courses=': white to pale grey marble with soft grey veining, worn smooth by two centuries of feet, faint grime '
                'in the pores')),
    # the elements
    ('door-a', 'door', ELEVATION.format(
        what='of one front doorway', casing=10, foot='the threshold',
        inside='Inside the casing: at the top a fixed transom window of four equal panes side by side in one row, with '
               'slender wooden muntins, about 35 centimetres tall; under it a heavy six-panel colonial door: two small '
               'raised panels at the top, two tall raised panels in the middle and two raised panels at the bottom, with '
               'moulded edges, a brass knob, a small brass keyhole escutcheon and a brass mail slot in the middle rail.',
        w='1.15', h='2.85', key=KEY + ' ') + ENDING),
    ('door-b', 'door', ELEVATION.format(
        what='of one front doorway', casing=10, foot='the threshold',
        inside='Inside the casing: across the top a fixed four-light transom (four equal panes in a row between thin '
               'muntins, about 35 centimetres tall); under it a six-panel colonial door, its panels raised and fielded, '
               'two short ones at the top, two tall ones in the middle and two at the bottom, with an old brass knob and a '
               'brass letter slot on the lock rail.',
        w='1.15', h='2.85', key=KEY + ' ') + ENDING),
    ('winshut-a', 'winshut', ELEVATION.format(
        what='of one ground-floor window with its pair of solid wooden shutters closed', casing=10,
        foot='a projecting painted wooden sill',
        inside='Inside the casing two closed shutter leaves meet in the middle, covering the window entirely: each leaf '
               'is made of flush vertical boards with one plain horizontal rail across its middle, with black iron strap '
               'hinges at its outer edge near the top and the bottom and a small black iron latch where the leaves meet.',
        w='1.15', h='1.95', key='No glass is visible. ') + ENDING),
    ('winshut-b', 'winshut', ELEVATION.format(
        what='of one ground-floor window shut behind a pair of closed panelled shutters', casing=10,
        foot='a projecting painted wooden sill',
        inside='Inside the casing two closed shutter leaves meet in the middle, covering the window entirely: each leaf a '
               'flat stile-and-rail frame with two plain flush panels, one above the other, a black iron strap hinge at '
               'its outer edge near the top and the bottom, and a small iron bar latch across the meeting stiles.',
        w='1.15', h='1.95', key='No glass is visible. ') + ENDING),
    ('sash-a', 'sash', ELEVATION.format(
        what='of one upper-floor window', casing=10, foot='a projecting painted wooden sill',
        inside='Inside the casing a nine-over-nine double-hung wooden sash window: the upper sash and the lower sash each '
               'three panes wide and three panes tall, eighteen panes in all, with slender wooden muntins about two and a '
               'half centimetres wide and a wider meeting rail where the two sashes meet.',
        w='1.10', h='1.95', key=KEY + ' ') + ENDING),
    ('sash-b', 'sash', ELEVATION.format(
        what='of one upper-floor window', casing=10, foot='a projecting painted wooden sill',
        inside='Inside the casing an old nine-over-nine double-hung sash: two sashes of nine panes each (three across, '
               'three down), thin muntins, the meeting rail a little heavier, the sash frames a little wider at the '
               'bottom rail.',
        w='1.10', h='1.95', key=KEY + ' ') + ENDING),
    # the review of a and b: both drew nine over six; the house's (refs, the two Commons photographs) are nine over nine
    ('sash-c', 'sash', ELEVATION.format(
        what='of one upper-floor window', casing=10, foot='a projecting painted wooden sill',
        inside='Inside the casing a nine-over-nine double-hung wooden sash window, the two sashes exactly the same: the '
               'upper sash three panes wide and three panes tall, and the lower sash ALSO three panes wide and three panes '
               'tall, eighteen equal panes in all, six rows of three, every pane a little taller than it is wide, slender '
               'muntins about two and a half centimetres wide and a wider meeting rail across the middle.',
        w='1.10', h='1.95', key=KEY + ' ') + ENDING),
    ('sash-d', 'sash', ELEVATION.format(
        what='of one tall upper-floor window', casing=10, foot='a projecting painted wooden sill',
        inside='Inside the casing a colonial nine-over-nine sash window: SIX horizontal rows of panes, three panes in '
               'each row, the meeting rail between the third and the fourth row at exactly half the window\'s height, so '
               'the lower sash has three rows of panes just like the upper sash; slender muntins.',
        w='1.10', h='1.95', key=KEY + ' ') + ENDING),
    ('shutpair-a', 'shutpair', ('Architectural elevation photograph, perfectly orthographic and straight-on, of a pair of '
        'closed raised-panel wooden window shutters of a restored 1759 Philadelphia house, side by side and meeting in '
        'the middle, filling the frame edge to edge (the image\'s edges are the shutters\' outer edges): each leaf a '
        'stile-and-rail frame with two raised and fielded panels of about equal height, one above the other, small black '
        'iron hinge straps at the outer edge near the top and the bottom. Painted one warm off-white cream, old and '
        'lightly weathered. The whole image is 0.90 metres wide and 1.85 metres tall. No glass, no casing, no wall, no '
        'perspective, every vertical line vertical. ') + ENDING),
    ('shutpair-b', 'shutpair', ('Architectural elevation photograph, perfectly orthographic and straight-on, of two '
        'closed panelled wooden shutter leaves of an eighteenth-century Philadelphia house side by side, filling the '
        'frame edge to edge: each leaf with a top panel and a bottom panel, both raised, a middle rail between them, '
        'painted warm off-white cream, weathered, black iron hinge straps. The whole image is 0.90 metres wide and 1.85 '
        'metres tall. No glass, no casing, no wall, no perspective. ') + ENDING),
    # the review of a and b: the house's shutters have three raised panels a leaf (refs: a short one at the top)
    ('shutpair-c', 'shutpair', ('Architectural elevation photograph, perfectly orthographic and straight-on, of a pair of '
        'closed raised-panel wooden window shutters of a restored 1759 Philadelphia house, side by side and meeting in '
        'the middle, filling the frame edge to edge (the image\'s edges are the shutters\' outer edges): each leaf a '
        'stile-and-rail frame with THREE raised and fielded panels one above the other: a short nearly square panel at '
        'the top, a tall panel in the middle, and a medium panel at the bottom. Small black iron hinge straps at the outer '
        'edge near the top and the bottom. Painted one warm off-white cream, old and lightly weathered. The whole image '
        'is 0.90 metres wide and 1.85 metres tall. No glass, no casing, no wall, no perspective, every vertical line '
        'vertical. ') + ENDING),
    ('dsash-a', 'dsash', ELEVATION.format(
        what='of one dormer window', casing=8, foot='the casing\'s own bottom edge',
        inside='Inside the casing a six-over-six double-hung wooden sash window: each sash three panes wide and two panes '
               'tall, with slender muntins and a meeting rail.',
        w='0.95', h='1.12', key=KEY + ' ') + ENDING),
    ('dsash-b', 'dsash', ELEVATION.format(
        what='of one small dormer window', casing=8, foot='the casing\'s own bottom edge',
        inside='Inside the casing an old six-over-six sash: the upper and the lower sash each three panes across and two '
               'down, thin muntins, a slightly heavier meeting rail.',
        w='0.95', h='1.12', key=KEY + ' ') + ENDING),
]


def make(key, jid, kind, prompt, force):
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, jid + '.png'), os.path.join(RAW, jid + '.json')
    if os.path.exists(png) and not force:
        return jid, 'kept'
    size = SIZES[kind]
    d, err, sz = None, None, size
    for sz in (size, FALLBACK.get(size)):
        if not sz:
            break
        body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': sz, 'quality': QUALITY, 'n': 1,
                           'output_format': 'png', 'background': 'opaque'}).encode()
        d, err = SF.call(key, API, body, 'application/json')
        if d or not (err and 'size' in err.lower()):
            break
    if not d:
        return jid, err
    import base64
    img = base64.b64decode(d['data'][0]['b64_json'])
    with open(png + '.tmp', 'wb') as f:
        f.write(img)
    os.replace(png + '.tmp', png)
    json.dump({'id': jid, 'kind': kind, 'prompt': prompt, 'size': sz, 'model': MODEL, 'quality': QUALITY,
               'created': d.get('created'), 'usage': d.get('usage')}, open(meta, 'w'), indent=1)
    return jid, 'made %d KB at %s' % (len(img) // 1024, sz)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    js = [j for j in JOBS if not only or j[0] in only]
    if a.list:
        for j in js:
            print(j[0], SIZES[j[1]])
        return
    key = SF.api_key()
    print('%d images, model %s, quality %s, into %s' % (len(js), MODEL, QUALITY, RAW), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for jid, what in ex.map(lambda j: make(key, j[0], j[1], j[2], a.force), js):
            print(jid, what, flush=True)


if __name__ == '__main__':
    main()
