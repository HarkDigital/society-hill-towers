#!/usr/bin/env python3
"""Generate Independence Hall's own art (Round 210, Mike: "Can we have independence hall remodeled with the chat GPT
api?"): the materials and the openings of the 1753 Pennsylvania State House, its 1828 steeple and its 1898 wings, from
OpenAI's image API, written to lidar_cache/indhall_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the
size, when, the usage). bake_indhall_art.py cuts them into the one atlas the page's hall wears.

Two kinds of image, as A Man Full of Trouble's (fetch_tavern_art.py):
  swatches  the Flemish bond brick with its glazed headers, the cedar shingles of the roofs, the white paint of the
            trim and the steeple, and the grey marble of the quoins, the belt course, the panels and the keystones: each a
            straight-on photograph of the material alone, which the bake cuts on its own courses or blends, so it repeats;
  elements  the openings as the hall has them (refs, looked at and never sent: Wikimedia Commons 'Independence Hall
            South Facade.jpg', 'NorthFacade2.jpg', 'The Independence Hall North.jpg', 'Independence National Historical
            Park INDE0002.jpg', and HABS PA-1430 'WEST WING, VIEW FROM NORTH' and the north aerial view): the main block's
            tall twelve-over-twelve sashes of the ground floor and the upper floor, the wings' smaller twelve-over-twelve
            sash, the Chestnut Street doorway, the tower's south doorway, the tower's Palladian window, the round-headed
            sash of the end walls and the tower's sides, the steeple's clock dial, the tower's oculus, the wings'
            six-panel door and the cellar grilles. Each fills the frame from frame edge to frame edge at its own
            proportions; the three sashes' panes are a flat chroma-key green (#00FF00) so the bake finds the glass exactly
            and the page draws the glass itself (its reflections and the rooms behind it).
Which variant is chosen is CHOSEN in bake_indhall_art.py, set by eye against the reference photos (every image is looked
at).

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; --force makes it again, --only <id>[,<id>] makes some. INDHALL_ART_MODEL picks
the model (default gpt-image-2), INDHALL_ART_QUALITY the quality (default high), INDHALL_ART_RAW the folder (default
lidar_cache/indhall_art_raw). Every prompt asks for no lettering, no logos and no signs.

Usage: python3 fetch_indhall_art.py [--only id,...] [--force] [--list] [--workers 2]"""
import argparse, concurrent.futures, json, os
import fetch_storefront_art as SF   # the API plumbing (the key, retries) is the storefronts'

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('INDHALL_ART_RAW') or os.path.join(HERE, 'lidar_cache', 'indhall_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('INDHALL_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('INDHALL_ART_QUALITY', 'high')
# each element at its own proportions (width by height in metres, as bake_indhall_art.py's ELEMENTS; the model's sizes
# in multiples of 16)
SIZES = {'swatch': '1024x1024', 'sashG': '640x1600', 'sashU': '752x1600', 'sashW': '832x1600', 'door': '800x1600',
         'tdoor': '1024x1600', 'palladian': '1120x1600', 'arch': '624x1616', 'clock': '1024x1024', 'oculus': '1024x1024',
         'wdoor': '768x1600', 'cellar': '1536x768'}
FALLBACK = {'640x1600': '1024x1536', '752x1600': '1024x1536', '832x1600': '1024x1536', '800x1600': '1024x1536',
            '1024x1600': '1024x1536', '1120x1600': '1024x1536', '624x1616': '1024x1536', '1536x768': '1536x1024'}

ENDING = ('Soft even overcast daylight with no cast shadows. No people, no plants, no signs, no lettering, no numbers, no '
          'logos, no flags. Photorealistic, high detail, natural colours.')
SWATCH = ('Seamless tileable texture for a 3D city model: a photograph taken looking straight at {what}, perpendicular to '
          'it, filling the whole frame evenly{courses}. No edges, no corners, no openings, no objects, no cast shadows. '
          'Soft even overcast daylight. Natural colours, photorealistic, uniform detail across the whole image so it '
          'repeats without a visible seam.')
KEY = ('Every pane of glass is filled with flat, uniform, pure chroma-key green (#00FF00) with no texture, no reflections '
       'and no shading, so the panes can be cut out later; the wood is real painted wood.')
GLASS = ('Every pane is old hand-made window glass, dark and slightly wavy, reflecting a pale overcast sky with faint '
         'reflections. ')
WHITE = 'painted a clean bright white, old and well kept, with soft wear on the edges'
ELEVATION = ('Architectural elevation photograph, perfectly orthographic and straight-on, {what} of Independence Hall, '
             'the 1753 Pennsylvania State House in Philadelphia. The image is exactly the {frame} and what is inside it, '
             'filling the frame edge to edge: {edges} {inside} All the wood is ' + WHITE + '. The whole image is {w} '
             'metres wide and {h} metres tall. {key}No perspective, no vanishing lines, every vertical line vertical. No '
             'brick, no wall, nothing outside the frame. ')
SASH_EDGES = ('the left, right and top edges of the image are the outer edges of a plain flat wooden window frame about '
              '{casing} centimetres wide, and the bottom edge is a projecting painted wooden sill.')

JOBS = [
    # the swatches
    ('brick-a', 'swatch', SWATCH.format(
        what='the Flemish bond brickwork of Independence Hall in Philadelphia, a 1750s Georgian brick wall, about 1.8 '
             'metres across and about twenty-six courses high',
        courses=', the courses running exactly horizontally. Every course alternates a long stretcher and a short header '
                'end, each header centred over a stretcher of the course below; the headers are glazed, a dark '
                'purplish-grey with a faint sheen; the stretchers are smooth, regular, dark warm red to red-brown '
                'bricks; thin pale grey lime mortar joints, struck flush; gentle even weathering and a little soot')),
    ('brick-b', 'swatch', SWATCH.format(
        what='the old Flemish bond brick wall of an eighteenth-century Georgian public building in Philadelphia, about '
             '1.8 metres across and about twenty-six courses high',
        courses=', the courses running exactly horizontally. In every course long red-brown stretchers alternate with '
                'short header ends, every header a darker glazed brick, plum to blue-grey, so the wall has a regular '
                'checker of dark headers; the stretchers deep brick red, crisp and regular; thin light grey mortar; '
                'gentle overall weathering')),
    ('shingle-a', 'swatch', SWATCH.format(
        what='a pitched roof of weathered cedar wood shingles on an eighteenth-century Georgian public building in '
             'Philadelphia, about two metres across',
        courses=', the courses running exactly horizontally with about twelve centimetres of each shingle exposed, '
                'shingles of random widths from eight to thirty centimetres with narrow staggered gaps, weathered '
                'warm grey-brown wood, a little darker than silver, with slight grime')),
    ('shingle-b', 'swatch', SWATCH.format(
        what='a roof of old dark weathered cedar shingles in straight courses on a colonial building in Philadelphia, '
             'about two metres across',
        courses=', the butts in straight horizontal courses about twelve centimetres apart, shingles of random widths '
                'with narrow dark gaps staggered between courses, dark grey-brown weathered wood')),
    ('paint-a', 'swatch', SWATCH.format(
        what='a flat old wooden board ' + WHITE + ', about one metre across',
        courses=': one continuous smooth painted surface with no joints, the faint wood grain running horizontally '
                'through many coats of white paint, soft brush marks along the grain, very fine hairline crazing')),
    ('stone-a', 'swatch', SWATCH.format(
        what='a dressed block of weathered grey marble in the quoins of an eighteenth-century Philadelphia building, '
             'about sixty centimetres across',
        courses=': a smooth tooled face of pale grey to blue-grey marble with soft darker grey veining and faint '
                'speckles, two centuries of gentle weathering and a little grime in the pores')),
    ('stone-b', 'swatch', SWATCH.format(
        what='the face of an old grey soapstone-like marble block on a colonial Philadelphia facade, about sixty '
             'centimetres across',
        courses=': a flat smooth face, mid grey with a slight green-blue cast, fine darker mottling and soft veins, '
                'evenly weathered')),
    # the elements: the sashes (glazed, keyed)
    ('sashG-a', 'sashG', ELEVATION.format(
        what='of one tall ground-floor window', frame='window frame', edges=SASH_EDGES.format(casing=12),
        inside='Inside the frame a very tall twelve-over-twelve double-hung wooden sash window: the upper sash and the '
               'lower sash each three panes wide and four panes tall, twenty-four tall panes in all, eight rows of three, '
               'slender muntins about two and a half centimetres wide and a wider meeting rail at exactly half the '
               'height.',
        w='1.60', h='4.00', key=KEY + ' ') + ENDING),
    ('sashG-b', 'sashG', ELEVATION.format(
        what='of one tall ground-floor window', frame='window frame', edges=SASH_EDGES.format(casing=12),
        inside='Inside the frame a colonial twelve-over-twelve sash: EIGHT horizontal rows of panes, three panes in each '
               'row, every pane taller than it is wide, the meeting rail between the fourth and the fifth row at exactly '
               'half the window\'s height, thin muntins.',
        w='1.60', h='4.00', key=KEY + ' ') + ENDING),
    ('sashU-a', 'sashU', ELEVATION.format(
        what='of one upper-floor window', frame='window frame', edges=SASH_EDGES.format(casing=12),
        inside='Inside the frame a tall twelve-over-twelve double-hung wooden sash window: each sash three panes wide '
               'and four panes tall, twenty-four panes in all, eight rows of three, slender muntins and a wider meeting '
               'rail at exactly half the height.',
        w='1.60', h='3.40', key=KEY + ' ') + ENDING),
    ('sashU-b', 'sashU', ELEVATION.format(
        what='of one upper-floor window', frame='window frame', edges=SASH_EDGES.format(casing=12),
        inside='Inside the frame an old twelve-over-twelve sash: eight rows of three panes, the upper and the lower sash '
               'equal, the meeting rail at half the height, thin muntins.',
        w='1.60', h='3.40', key=KEY + ' ') + ENDING),
    ('sashW-a', 'sashW', ELEVATION.format(
        what='of one window of the two-storey brick wing building beside the main hall', frame='window frame',
        edges=SASH_EDGES.format(casing=10),
        inside='Inside the frame a twelve-over-twelve double-hung wooden sash window: each sash three panes wide and four '
               'panes tall, eight rows of three panes, slender muntins and a meeting rail at exactly half the height.',
        w='1.20', h='2.30', key=KEY + ' ') + ENDING),
    ('sashW-b', 'sashW', ELEVATION.format(
        what='of one window of the colonial brick wing building', frame='window frame', edges=SASH_EDGES.format(casing=10),
        inside='Inside the frame a twelve-over-twelve sash: eight rows of three small panes, the meeting rail at half the '
               'height, thin muntins.',
        w='1.20', h='2.30', key=KEY + ' ') + ENDING),
    # the doorways
    ('door-a', 'door', ELEVATION.format(
        what='of the Chestnut Street front doorway', frame='doorway\'s white wooden surround',
        edges='the left, right and top edges of the image are the outer edges of a moulded white wooden door surround '
              'about twenty centimetres wide with a plain frieze and a small moulded cornice head across the top, and the '
              'bottom edge is a grey marble threshold.',
        inside='Inside the surround a pair of tall heavy panelled wooden doors, each leaf with six raised and fielded '
               'panels, under a fixed rectangular transom window of small panes.',
        w='2.20', h='4.40', key=GLASS) + ENDING),
    ('door-b', 'door', ELEVATION.format(
        what='of the main north doorway', frame='doorway\'s white wooden surround',
        edges='the left, right and top edges of the image are the outer edges of a white moulded wooden architrave about '
              'twenty centimetres wide under a simple flat cornice head, and the bottom edge is a grey marble threshold.',
        inside='Inside it a pair of tall panelled colonial doors painted white, each leaf with raised panels, under a '
               'transom of small panes in a single row.',
        w='2.20', h='4.40', key=GLASS) + ENDING),
    ('tdoor-a', 'tdoor', ELEVATION.format(
        what='of the doorway in the base of the brick tower on Independence Square', frame='doorway\'s white classical '
             'frontispiece',
        edges='the left, right and top edges of the image are the outer edges of a white painted wooden classical '
              'frontispiece: two flat Doric pilasters at the sides on plain bases, carrying a full entablature across the '
              'top (architrave, frieze and a projecting cornice), and the bottom edge is a grey marble step.',
        inside='Between the pilasters a pair of tall dark green panelled wooden doors, each leaf with raised panels, under '
               'a semicircular fanlight of radiating wooden bars.',
        w='3.20', h='5.00', key=GLASS) + ENDING),
    ('tdoor-b', 'tdoor', ELEVATION.format(
        what='of the south tower doorway', frame='doorway\'s white classical surround',
        edges='the left, right and top edges are the outer edges of a white wooden frontispiece of two pilasters and an '
              'entablature with a projecting cornice across the top, and the bottom edge is a grey marble step.',
        inside='Inside, a pair of tall panelled doors painted dark green under a rectangular transom of small panes.',
        w='3.20', h='5.00', key=GLASS) + ENDING),
    ('palladian-a', 'palladian', ELEVATION.format(
        what='of the great Palladian (Venetian) window in the tower over the south door', frame='window\'s white '
             'wooden frame',
        edges='the image is exactly the window\'s white wooden frame and its sashes, filling the frame edge to edge: '
              'its outer edges are the edges of the image, the bottom edge a projecting white sill.',
        inside='A tall round-headed central window with a semicircular top filled with radiating glazing bars over a '
               'twelve-over-twelve sash, flanked by two narrower rectangular side windows each a small-paned sash, the '
               'three separated by slender white pilasters; the side windows topped by a small white entablature at the '
               'height where the centre arch springs; a white moulded archivolt round the arch with a keystone at its '
               'crown. The top corners of the image beside the arch are plain flat white board.',
        w='3.80', h='5.40', key=GLASS) + ENDING),
    ('palladian-b', 'palladian', ELEVATION.format(
        what='of the tower\'s Venetian window', frame='window\'s white wooden frame',
        edges='its outer edges are the image\'s edges, the bottom a projecting sill.',
        inside='A three-part Palladian window: a taller arched centre light with a fan of glazing bars in its '
               'semicircular head over small-paned sashes, two narrower flat-headed side lights of small panes, white '
               'pilasters between them, an entablature over the side lights and a moulded arch with a keystone over the '
               'centre. The top corners beside the arch are flat white panels.',
        w='3.80', h='5.40', key=GLASS) + ENDING),
    ('arch-a', 'arch', ELEVATION.format(
        what='of one tall round-headed window', frame='window\'s white wooden frame',
        edges='the left, right and bottom edges of the image are the outer edges of a plain white wooden frame about ten '
              'centimetres wide with a projecting sill at the bottom; the top of the frame is a full semicircle whose '
              'crown touches the top edge of the image.',
        inside='Inside the frame a twelve-over-twelve double-hung sash, three panes across, with a semicircular fanlight '
               'of radiating glazing bars above it filling the round head. The two top corners of the image outside the '
               'semicircle are flat white.',
        w='1.50', h='3.90', key=GLASS) + ENDING),
    ('arch-b', 'arch', ELEVATION.format(
        what='of one round-arched sash window', frame='window\'s white wooden frame',
        edges='the left, right and bottom edges are the outer edges of a plain white frame with a sill at the bottom, the '
              'top of the frame a semicircle touching the top edge of the image.',
        inside='A small-paned double-hung sash three panes wide with a fan-shaped semicircular light above it. The two top '
               'corners outside the arch are flat white.',
        w='1.50', h='3.90', key=GLASS) + ENDING),
    # the steeple's clock and the tower's oculus
    ('clock-a', 'clock', ('Architectural elevation photograph, perfectly orthographic and straight-on, of one of the four '
        'clock faces of the 1828 wooden steeple of Independence Hall in Philadelphia, filling the frame edge to edge: a '
        'large round white clock dial with black Roman numerals round its rim, a black chapter ring and minute track, '
        'black hands at ten past ten, in a round moulded white wooden bezel; the four corners of the square image round '
        'the dial filled with carved white wooden scroll ornament (spandrels) on a flat white board. Everything is '
        'painted white except the numerals, the rings and the hands. The whole image is 2.8 metres square. No '
        'perspective. ') + ENDING),
    ('clock-b', 'clock', ('Architectural elevation photograph, perfectly orthographic and straight-on, of a large '
        'Georgian clock face on a white painted wooden steeple, filling the frame edge to edge: a round white dial with '
        'black Roman numerals, black hands, a slim black ring, in a moulded white circular frame, the corners of the '
        'square image white carved scroll spandrels. The whole image is 2.8 metres square. No perspective. ') + ENDING),
    ('oculus-a', 'oculus', ('Architectural elevation photograph, perfectly orthographic and straight-on, of one round '
        'window (an oculus) in the brick tower of Independence Hall in Philadelphia, filling the frame edge to edge: a '
        'circular window whose white moulded wooden frame touches all four edges of the square image, the glass divided '
        'by white glazing bars radiating from a small central circle; ' + GLASS + 'The four corners of the image outside '
        'the circle are flat white. The whole image is 1.6 metres square. No perspective, no brick. ') + ENDING),
    ('oculus-b', 'oculus', ('Architectural elevation photograph, perfectly orthographic and straight-on, of a round bull\'s '
        'eye window with a white wooden frame touching the four edges of the square image and a cross of white glazing '
        'bars; ' + GLASS + 'The corners outside the circle are flat white. The whole image is 1.6 metres square. No '
        'perspective. ') + ENDING),
    # the wings' doors and the cellar grilles
    ('wdoor-a', 'wdoor', ELEVATION.format(
        what='of one doorway of the two-storey brick wing building', frame='door frame',
        edges='the left, right and top edges of the image are the outer edges of a plain flat white wooden door frame '
              'about twelve centimetres wide, and the bottom edge is a grey marble threshold.',
        inside='Inside the frame a heavy six-panel colonial wooden door painted white, its panels raised and fielded: two '
               'small panels at the top, two tall in the middle, two at the bottom, a black iron latch.',
        w='1.30', h='2.70', key='No glass is visible. ') + ENDING),
    ('wdoor-b', 'wdoor', ELEVATION.format(
        what='of one doorway of the colonial wing building', frame='door frame',
        edges='the left, right and top edges are the outer edges of a plain white frame, the bottom edge a marble '
              'threshold.',
        inside='A white six-panel door with raised panels and an old brass knob.',
        w='1.30', h='2.70', key='No glass is visible. ') + ENDING),
    ('cellar-a', 'cellar', ('Architectural elevation photograph, perfectly orthographic and straight-on, of one low '
        'cellar window opening at the foot of the brick wall of Independence Hall in Philadelphia, filling the frame '
        'edge to edge: the image is exactly the opening and its plain grey marble surround (the surround\'s outer edges '
        'are the image\'s edges): closely spaced vertical black iron bars over a dark shadowed recess. The whole image is '
        '1.2 metres wide and 0.6 metres tall. No brick, no perspective. ') + ENDING),
    ('cellar-b', 'cellar', ('Architectural elevation photograph, perfectly orthographic and straight-on, of a small '
        'basement window grille: black iron bars over a dark opening in a grey stone frame filling the image edge to '
        'edge. The whole image is 1.2 metres wide and 0.6 metres tall. No perspective. ') + ENDING),
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
