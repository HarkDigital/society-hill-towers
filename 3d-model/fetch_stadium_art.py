#!/usr/bin/env python3
"""Generate the sports complex's surfaces (Round 195, Mike: "Remodel ... The stadiums/arena"), from OpenAI's image API,
written to lidar_cache/stadium_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the
usage). bake_stadium_art.py makes them tile and packs them into what the venues' three programs read (stadium_art.json).

Two kinds:
- 'wall': one straight-on elevation of a venue's outer wall, the whole height from the walk to its top, a few bays of its
  own module repeating left to right, under flat overcast light (the page lights it). The bake finds the bay's period,
  cuts a whole number of bays and lays them as one strip of the walls' atlas, so a wall repeats it along its length.
- 'tile': a top-down surface that repeats both ways: the seat rows (one picture for both stadiums: the bake keeps the
  seats' shading and a mask of where the seats are, and the page tints them the venue's own blue or midnight green), the
  turf and the infield clay. The bake cuts a whole number of seat rows and seats and blends the edges.

The reference photographs (Wikimedia Commons, the arena's own 2024 news pictures) were looked at for the descriptions only;
none is ever sent to the API. Every prompt asks for no lettering, no logos and no people.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
STADIUM_ART_MODEL picks the model (default gpt-image-2), STADIUM_ART_QUALITY the quality (default high).

Usage: python3 fetch_stadium_art.py [--only id,...] [--force] [--list] [--workers 3]"""
import argparse, concurrent.futures, json, os, sys
import fetch_storefront_art as SF   # the API plumbing: api_key, call, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'stadium_art_raw')
MODEL = os.environ.get('STADIUM_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('STADIUM_ART_QUALITY', 'high')

WALL = ('Seamless horizontally tileable facade texture for a 3D city model: a perfectly orthographic, straight-on elevation '
        'of {what}. The picture shows the wall\'s whole height and nothing else: its foot exactly at the bottom edge of the '
        'picture and its top exactly at the top edge, no ground, no sidewalk, no sky. The wall repeats seamlessly from side '
        'to side (what leaves the right edge comes back at the left), every bay identical and evenly spaced. Photographed in '
        'flat, even overcast daylight with no cast shadows, at its true colours. No perspective, no building corners, no '
        'people, no vehicles, no trees, no lettering, no signs, no logos, no screens.')
PHOTO = ('A photograph for a 3D city model: {what} Photographic, natural colour. No people, no players, no lettering, no numbers, '
         'no logos, no scoreboard graphics, no advertising.')
TILE = ('Seamless tileable texture for a 3D city model: {what} Repeating seamlessly in both directions (what leaves the right '
        'edge comes back at the left, what leaves the top comes back at the bottom). Flat, even overcast daylight with no cast '
        'shadows. No people, no lettering, no logos, no lines painted on it.')

# id: (kind, description, size)
ITEMS = {
    'cbp-brick': ('wall', 'the outer wall of a 2004 Philadelphia major league ballpark built to look like the city\'s old '
                  'brick industrial buildings, 14 metres tall and 8 bays wide: warm red brick in several blended shades laid '
                  'in running bond, a base course of pale grey granite 1.2 metres tall, two thin bands of pale precast stone '
                  'across the wall, deep brick piers between the bays, in every bay two tall narrow openings one above the '
                  'other glazed with dark green-grey tinted glass in dark green painted steel frames, and a dark green painted '
                  'steel cornice along the top', '1536x512'),
    'linc-glass': ('wall', 'the long side wall of a 2003 American football stadium, 18 metres tall and 6 bays wide: a tall glass '
                   'curtain wall of grey-green tinted glass in a grid of slim silver aluminium mullions, divided into bays by '
                   'tall rust-red brick piers about 1.2 metres wide, a band of exposed light grey steel structure along the '
                   'top, and a grey concrete base', '1536x512'),
    'linc-screen': ('wall', 'the end wall of a 2003 American football stadium, 20 metres tall and 6 frames wide: dark charcoal '
                    'grey metal panels crossed by very large X-shaped diagonal steel braces painted dark grey, each X filling '
                    'a square steel frame about 9 metres wide, slim horizontal joints between the panels', '1536x512'),
    'arena-fins': ('wall', 'the corner block of an indoor sports arena after its 2024 renovation, 24 metres tall and 6 bays wide: '
                   'a dark charcoal wall behind closely spaced horizontal brushed silver aluminium fins running the full width, '
                   'one fin every 70 centimetres from the foot to the top, a slim vertical joint every 6 metres', '1536x512'),
    'arena-podium': ('wall', 'the lower podium of a modern indoor sports arena, 14 metres tall and 8 bays wide: dark grey metal '
                     'panel cladding with two long continuous horizontal bands of dark tinted glazing in slim black mullions '
                     '(the club level and the concourse), a recessed dark band at the foot, slim joints between the panels',
                     '1536x512'),
    'arena-drum': ('wall', 'the curved upper wall of a modern indoor sports arena, 20 metres tall: smooth very light grey, almost '
                   'white, insulated metal panels 1.5 metres wide by 3 metres tall in a precise grid with thin dark shadow '
                   'joints, a faint tone variation from panel to panel, a slim horizontal reveal band two thirds of the way up',
                   '1536x512'),
    # the review's round (Round 195's fixes): the arena's podium glazed as the 2024 photographs show it (the first strip was
    # opaque panels with two black bands; 'arena-podium' stays on disk), the Linc's office block, the ballpark's gate atriums
    # and a picture for the left field board (the canvas cartoon read as a children's game)
    'arena-podium-glass': ('wall', 'the lower podium of an indoor sports arena after its 2024 renovation, 14 metres tall and 8 '
                           'bays wide: two long continuous horizontal bands of floor-to-ceiling dark tinted glazing, the club '
                           'level above and the concourse below, each about 4.5 metres tall, in slim black aluminium mullions '
                           'every 1.5 metres, the glass dark grey-blue with faint reflections, a band of dark charcoal metal '
                           'panels at each floor slab between them, dark charcoal metal panel cladding along the top, a '
                           'recessed dark base at the foot', '1536x512'),
    'linc-office': ('wall', 'three storeys of the office block of a 2003 American football stadium, 14 metres tall and 8 bays '
                    'wide, cut from the middle of a taller facade so the pattern continues seamlessly from the top edge to the '
                    'bottom edge: dark charcoal grey metal panel cladding, tall vertical strips of dark tinted glass between '
                    'slim dark grey metal piers in every bay, a thin dark metal spandrel band at every floor, the glass dark grey '
                    'with faint sky reflections', '1536x512'),
    'cbp-atrium': ('wall', 'the glazed entrance atrium of a 2004 brick ballpark, 18 metres tall and 8 bays wide: a tall glass '
                   'curtain wall of slightly green-grey glass in a grid of dark green painted steel mullions and transoms, '
                   'divided into bays by deep red brick piers about 1.5 metres wide standing on pale grey granite bases 1.2 '
                   'metres tall, a dark green steel band across the whole wall at 6 metres, a pale precast stone coping along '
                   'the top', '1536x512'),
    # Round 217 (Mike: "I also want Citizen's bank park to be completely remodeled"): the Pattison Avenue front (Commons'
    # Citizensbankparkside.jpg) and Ashburn Alley's concession buildings (Center_Field_Wall_at_Citizens_Bank_Park); the ivy
    # ('cbp-ivy', made in Round 195 and unused till now) dresses the batter's eye
    'cbp-pattison': ('wall', 'the Pattison Avenue street front of a 2004 Philadelphia major league ballpark: a four-storey red '
                     'brick office and club block 18 metres tall and 6 identical bays. A base 1.4 metres tall of polished deep '
                     'red granite panels with a thin black granite band along its top. Tall brick piers about 2.5 metres wide in '
                     'several blended shades of red brick rise the full height between the bays, each standing on a pale '
                     'pinkish-tan precast stone block 3 metres tall. In every bay: at the bottom a tall glazed opening two '
                     'storeys high of dark blue-grey tinted glass in slim dark grey aluminium frames, recessed into the wall; '
                     'above it two storeys each with a pair of tall narrow windows of dark blue-grey tinted glass in dark grey '
                     'frames with pale stone sills; near the top a chain of three diamond shapes laid in black brick across '
                     'the bay; a pale pinkish-tan precast cornice along the top', '1536x512'),
    'cbp-alley': ('wall', 'the low brick concession buildings along the outfield promenade of a 2004 Philadelphia ballpark, '
                  '6 metres tall and 8 identical bays: red brick in several blended shades laid in running bond; in every bay '
                  'a wide service opening 3 metres tall with a dark green painted steel roll-up shutter half raised over a '
                  'dimly lit counter and a dark interior; a dark green painted steel canopy band 0.5 metres deep across the '
                  'wall over the openings; plain brick piers between the bays; a pale pinkish-tan precast coping along the top',
                  '1536x512'),
    'board': ('photo', 'the picture on a ballpark\'s giant outdoor video board between innings, filling the frame edge to edge: '
              'a wide high view of an empty major league baseball field at dusk under the lights, from high behind home plate '
              'looking toward centre field, the green outfield with mowing stripes, the brown infield dirt, the pitcher\'s '
              'mound, the outfield wall and empty dark blue seats beyond under a deep blue evening sky, slightly soft as on a '
              'large LED screen.', '1536x1024'),
    'seats': ('tile', 'a straight-on view perpendicular to a sloped stadium seating tier: rows of empty dark navy blue plastic '
              'folding stadium seats with their backs up, standing on pale grey concrete treads, exactly 6 rows top to bottom '
              'and 12 seats side by side, every row and every seat identical and evenly spaced, the narrow grey concrete '
              'tread visible between one row\'s seat backs and the next row\'s seats. No aisles, no stairs, no railings, no '
              'cup holders.', '1024x1024'),
    'grass': ('tile', 'a straight top-down photograph of a major league stadium\'s natural grass turf, freshly mown, dense fine '
              'blades, rich even green with the faint natural variation of real turf, no mowing stripes.', '1024x1024'),
    'clay': ('tile', 'a straight top-down photograph of a groomed baseball infield\'s red-brown clay, a fine dragged surface with '
             'faint drag marks and a few scattered tiny pebbles, even colour.', '1024x1024'),
}


def prompt_of(cid):
    kind, what, size = ITEMS[cid]
    return {'wall': WALL, 'tile': TILE, 'photo': PHOTO}[kind].format(what=what), size


def make(key, cid, force):
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, cid + '.png'), os.path.join(RAW, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    prompt, size = prompt_of(cid)
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = SF.call(key, SF.API, body, 'application/json')
    if not d:
        return cid, err
    SF.MODEL, SF.QUALITY = MODEL, QUALITY
    n = SF.save(png, meta, d, {'id': cid, 'kind': ITEMS[cid][0], 'prompt': prompt, 'size': size})
    return cid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    unknown = only - set(ITEMS)
    if unknown:
        sys.exit('unknown ids: ' + ', '.join(sorted(unknown)))
    jobs = [c for c in ITEMS if not only or c in only]
    if a.list:
        for c in jobs:
            print(c, ITEMS[c][0], ITEMS[c][2])
        return
    key = SF.api_key()
    print('%d images, model %s, quality %s' % (len(jobs), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for cid, what in ex.map(lambda c: make(key, c, a.force), jobs):
            print(cid, what, flush=True)


if __name__ == '__main__':
    main()
