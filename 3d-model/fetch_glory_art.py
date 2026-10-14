#!/usr/bin/env python3
"""Generate Glory Beer Bar & Kitchen's own art (Round 191, Mike: "I want City hall and Glory Beer Bar and Kitchen to be
totally revamped"): the two straight-on elevations of 126 Chestnut Street (the granite ground floor and second storey, and
the three brick storeys over them) and the two rooms seen through its glass (the bar on the ground floor, the board-game
room upstairs), from OpenAI's image API, written to lidar_cache/glory_art_raw/<stage>/<id>.png with a sidecar <id>.json
(the prompt, the model, the size, when, the usage, and for an edit the source's and the mask's sha). bake_glory_art.py cuts
them into the facade atlas, its mask and the interior atlas rebuilds/glory.js wears.

The stages follow fetch_storefront_art.py's, so the glass is found exactly:
  frames   lower-a to lower-f and upper-a/b: each elevation with every pane of glass a flat chroma-key green (#00FF00)
           (lower-c to lower-f from LOWER2, Round 191's review: lower-b's arches were gothic lancets);
  glass    upper: the chosen upper frame with real window glass painted into the key through /v1/images/edits (the mask is
           bake_glory_art.py --masks's, transparent over the key). The lower frame keeps its key: the page draws the rooms
           behind those panes itself;
  rooms    ground-empty-a/b and upper-empty-a/b: each room from just inside the front, straight down its length in one-point
           perspective, empty, in the evening;
  crowd    ground and upper: the chosen empty room with people added over the floor (the mask is the bake's).
Which variant is chosen is CHOSEN below, set by eye against the reference photos (every image was looked at).

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; --force makes it again, --only <id>[,<id>] makes some. GLORY_ART_MODEL picks the
model (default gpt-image-2), GLORY_ART_QUALITY the quality (default high). Every image is opaque (no transparency), so
gpt-image-1.5 is never needed. The reference photos of the building were looked at for these prompts and never sent.

Every prompt asks for no lettering, no logos and no signs: the bar's name is drawn by the page on its own sign boards.

Usage: python3 fetch_glory_art.py [--stage frames|glass|rooms|crowd] [--only id,...] [--force] [--list] [--workers 2]"""
import argparse, concurrent.futures, hashlib, json, os, sys
import fetch_storefront_art as SF   # the API plumbing (the key, multipart, retries) is the storefronts'

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'glory_art_raw')
API = 'https://api.openai.com/v1/images/generations'
API_EDIT = 'https://api.openai.com/v1/images/edits'
MODEL = os.environ.get('GLORY_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('GLORY_ART_QUALITY', 'high')
# the sizes are the surfaces' own proportions: each elevation 8.6 by 9.3 m at about 179 px a metre; each room's front
# opening as the shader's room box frames it (the bar 8.0 by 4.1 m, the room upstairs 8.0 by 3.2 m); FALLBACK when refused
SIZES = {'lower': '1536x1664', 'upper': '1536x1664', 'ground': '1536x784', 'upperroom': '1536x608'}
FALLBACK = {'1536x1664': '1024x1104', '1536x784': '1024x528', '1536x608': '1024x400'}
# the variants picked by eye (bake_glory_art.py reads these)
# Round 191: lower-e (the pairs of plump Tuscan columns, a low arch, two casements a bay, doors glazed to a short kick rail;
# lower-f's columns were slender, lower-c and lower-d stood single columns)
CHOSEN = {'lower': 'lower-e', 'upper': 'upper-b', 'ground': 'ground-empty-b', 'upperroom': 'upper-empty-a'}

ENDING = ('Soft even overcast daylight with no cast shadows. No people, no cars, no trees, no signs, no lettering, no '
          'numbers, no logos, no lamps, no awnings, no railings, no planters. Photorealistic, high detail, natural colours.')
KEY = ('Every pane of glass is filled with flat, uniform, pure chroma-key green (#00FF00) with no texture, no reflections '
       'and no shading, so the panes can be cut out later; the frames, muntins, doors, panels and {stone} are real '
       'materials. No perspective, no vanishing lines, every vertical line vertical.')
LOWER = ('Architectural front elevation photograph, perfectly orthographic and straight-on, of the ground floor and the '
         'second storey of ONE narrow 1853 Greek Revival commercial building on Chestnut Street in Old City, Philadelphia, '
         '8.6 metres wide. The facade fills the frame edge to edge: left and right edges are the party walls (no '
         'neighbours), the bottom edge is the sidewalk line, the top edge is the top of the projecting granite cornice over '
         'the second storey (no brick above, no sky). '
         'The ground floor, a little over half the image\'s height, is pale grey speckled weathered granite with faint soot. '
         'Five square granite piers (the two end ones narrower) with plain moulded block capitals divide four equal bays. '
         'Each bay holds a pair of very tall narrow wooden doors painted near-black dark brown: each leaf glazed with small '
         'panes two wide and five tall over a short panelled base, under a two-pane transom, in a dark painted wooden frame. '
         'A plain smooth blank granite lintel band runs across the whole width above them. '
         'The second storey: four equal bays separated by pairs of slender engaged round granite columns with simple '
         'capitals. Shallow pointed four-centred granite arches spring from the capitals over each bay. Each bay holds a '
         'pair of tall black steel casement windows with small rectangular panes, three wide and seven tall, the top row '
         'following the arch, above a plain dark painted metal panel about 60 cm tall at the sill. '
         'A projecting moulded granite cornice crowns the second storey. ' + KEY.format(stone='granite') + ' ' + ENDING)
# Round 191, the review: lower-b's second storey came out as four steep pointed lancets under moulded hood arches on thin
# ringed colonnettes, a church front from across the street, though LOWER asked for "shallow pointed four-centred" arches.
# The real storey is a flat granite lintel on plump paired Tuscan columns whose soffit dips between the capitals in a very
# low arch (a rise of about 0.3 to 0.5 m), two separate black steel casements in each bay with no hood and no tracery; and
# the doors are glazed nearly to a short kick rail, and the granite is a warm buff. LOWER2 says so in metres, and the bake
# refuses a frame whose key-measured arch rise is over ARCH_RISE_MAX (bake_glory_art.py). lower-c and lower-d (the first
# wording) stood single columns between the bays, so the pairs are spelled out for lower-e and lower-f
LOWER2 = ('Architectural front elevation photograph, perfectly orthographic and straight-on, of the ground floor and the '
          'second storey of ONE narrow 1853 Greek Revival granite store front on Chestnut Street in Old City, Philadelphia, '
          '8.6 metres wide and 9.3 metres tall. The facade fills the frame edge to edge: the left and right edges are the '
          'party walls (no neighbours), the bottom edge is the sidewalk, the top edge is the top of the granite cornice (no '
          'brick above, no sky). The stone is smooth dressed warm buff-cream granite, a light warm beige (never grey, never '
          'white), lightly weathered with faint soot, its joints few and far apart. '
          'GROUND FLOOR, the bottom 45 percent of the image: five plain square granite piers with simple moulded block '
          'capitals at 4 metres divide four equal bays; the two end piers are narrower. Each bay holds a pair of very tall '
          'narrow wooden doors painted near-black, each leaf glazed almost to the floor with small panes two wide and six '
          'tall over only a short solid kick rail about 30 centimetres high, under a two-pane transom, in a dark painted '
          'wooden frame. A plain smooth granite band runs across the whole width over the capitals, then a thin projecting '
          'granite sill course at 4.9 metres. '
          'SECOND STOREY, from 4.9 to 8.6 metres: four tall window bays. Between each two bays stands a COUPLED PAIR of '
          'engaged round Tuscan columns, two columns side by side almost touching, so the storey has six columns in three '
          'pairs (plain smooth shafts about 30 centimetres thick, a plain rounded cushion capital under a square abacus, a '
          'simple base, no rings, no flutes), with a flat plain pilaster at each end. Over the columns a flat plain '
          'granite lintel runs straight across the whole width. Between each pair of capitals the lintel\'s underside dips '
          'in one very shallow, nearly flat segmental arch that rises only 35 centimetres over the 1.5 metre bay: it springs '
          'at the capitals at 7.9 metres and its middle is at 8.25 metres. The arches are NOT pointed and NOT gothic: no '
          'lancets, no hood mouldings, no tracery, no keystones, no mouldings round the arches. Each bay holds TWO separate '
          'tall black steel casement windows side by side, meeting at a plain centre mullion, each casement three panes wide '
          'and seven panes tall with its top edge following the shallow arch, over a plain dark painted metal panel about 50 '
          'centimetres tall at the sill. '
          'A projecting moulded granite cornice crowns the second storey from 8.6 to 9.3 metres. ' + KEY.format(stone='granite') + ' ' + ENDING)
UPPER = ('Architectural front elevation photograph, perfectly orthographic and straight-on, of the third, fourth and fifth '
         'storeys of ONE narrow 1853 Greek Revival commercial building on Chestnut Street in Old City, Philadelphia, 8.6 '
         'metres wide. The facade fills the frame edge to edge: left and right edges are the party walls (no neighbours), '
         'the bottom edge is where the brick meets a granite cornice below, which is not shown, and the top edge is the top '
         'of the brick parapet (no sky). The wall is orange-red brick in running bond with thin pale lime mortar, gently '
         'weathered. On each storey four evenly spaced one-over-one double-hung sash windows with white-painted wooden '
         'frames and sashes, plain smooth stone sills and flat stone lintels, the windows stacked in four vertical columns, '
         'each window about 1 metre wide and 1.75 metres tall. At the top a corbelled brick cornice: three stepped '
         'projecting brick courses over a row of brick dentils, with no metal. ' + KEY.format(stone='brick') + ' ' + ENDING)
GLASS = ('Fill only the masked panes with real window glass: dark glass softly reflecting a pale overcast sky and brick '
         'buildings across the street, a few windows with pale roller blinds or curtains partly drawn, every window '
         'different; change nothing outside the mask. No lettering, no logos, no people.')
ROOM_FRAME = ('Photograph of the inside of {room} in the evening, taken from just inside the front windows looking straight '
              'back down the room in exact one-point perspective, the vanishing point near the centre, level camera, '
              'symmetric framing: the image\'s edges are the room\'s front opening (its side walls, floor and ceiling run '
              'from the image\'s edges toward the centre) and the far back wall is a centred rectangle about a quarter of '
              'the image\'s width. {inside} No people, no text, no signs, no logos, no lettering anywhere, TV screens dark. '
              'Photorealistic, natural colours.')
GROUND_ROOM = ('a long narrow Philadelphia beer bar', 'Right wall: a long dark wooden bar with metal-and-wood stools, a back '
               'bar of glassware and bottles under warm light, a row of plain chrome beer taps; nearest the front a wide '
               'plain area of old exposed red brick. Left wall: cream plaster with tall wooden high-top tables and stools. '
               'Black ceiling with exposed silver round ducts, strings of warm bistro bulbs, cast-iron columns down the '
               'middle, honey-coloured wood floor, warm 2700 K light.')
UPPER_ROOM = ('the long narrow second-floor room of a Philadelphia beer bar', 'Cream walls above a grey panelled wainscot, '
              'a dark wood antique mantelpiece on the right wall, globe wall sconces; criss-crossing strings of warm bistro '
              'bulbs under a dark grey ceiling with one silver duct, a cluster of glass globe pendants, two cast-iron '
              'columns; long rustic farmhouse tables with dark cross-back chairs; a small bar at the far back.')
CROWD = {'ground': 'Add a lively evening crowd of patrons standing at the bar and seated at the tables, softly out of focus, '
                   'no readable faces, no text or logos on clothing or anywhere, change nothing outside the mask.',
         'upper': 'Add people seated at the tables playing board games and talking, softly out of focus, no readable faces, '
                  'no text or logos on clothing or anywhere, change nothing outside the mask.'}


def jobs(stage):
    """(id, kind, prompt, size) for a stage."""
    if stage == 'frames':
        return [('lower-a', 'lower', LOWER, SIZES['lower']), ('lower-b', 'lower', LOWER, SIZES['lower']),
                ('lower-c', 'lower', LOWER2, SIZES['lower']), ('lower-d', 'lower', LOWER2, SIZES['lower']),
                ('lower-e', 'lower', LOWER2, SIZES['lower']), ('lower-f', 'lower', LOWER2, SIZES['lower']),
                ('upper-a', 'upper', UPPER, SIZES['upper']), ('upper-b', 'upper', UPPER, SIZES['upper'])]
    if stage == 'rooms':
        g = ROOM_FRAME.format(room=GROUND_ROOM[0], inside=GROUND_ROOM[1])
        u = ROOM_FRAME.format(room=UPPER_ROOM[0], inside=UPPER_ROOM[1])
        return [('ground-empty-a', 'ground', g, SIZES['ground']), ('ground-empty-b', 'ground', g, SIZES['ground']),
                ('upper-empty-a', 'upperroom', u, SIZES['upperroom']), ('upper-empty-b', 'upperroom', u, SIZES['upperroom'])]
    if stage == 'glass':
        return [('upper', 'upper', GLASS, SIZES['upper'])]
    if stage == 'crowd':
        return [('ground', 'ground', CROWD['ground'], SIZES['ground']), ('upper', 'upperroom', CROWD['upper'], SIZES['upperroom'])]
    return []


def save(png, meta, d, info):
    import base64
    img = base64.b64decode(d['data'][0]['b64_json'])
    with open(png + '.tmp', 'wb') as f:
        f.write(img)
    os.replace(png + '.tmp', png)
    info.update({'model': MODEL, 'quality': QUALITY, 'created': d.get('created'), 'usage': d.get('usage')})
    json.dump(info, open(meta, 'w'), indent=1)
    return len(img)


def make(key, stage, jid, kind, prompt, size, force):
    d0 = os.path.join(RAW, stage)
    os.makedirs(d0, exist_ok=True)
    png, meta = os.path.join(d0, jid + '.png'), os.path.join(d0, jid + '.json')
    if os.path.exists(png) and not force:
        return jid, 'kept'
    if stage in ('frames', 'rooms'):
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
        n = save(png, meta, d, {'id': jid, 'stage': stage, 'prompt': prompt, 'size': sz})
        return jid, 'made %d KB at %s' % (n // 1024, sz)
    # an edit: the chosen source and the bake's mask beside it (transparent where the edit may paint)
    src_stage = 'frames' if stage == 'glass' else 'rooms'
    src = os.path.join(RAW, src_stage, CHOSEN[kind] + '.png')
    mk = os.path.join(RAW, src_stage, CHOSEN[kind] + ('-mask.png' if stage == 'glass' else '-crowdmask.png'))
    if not os.path.exists(src) or not os.path.exists(mk):
        return jid, 'no source or mask yet (run the stage before, then bake_glory_art.py --masks)'
    from PIL import Image
    w, h = Image.open(src).size
    sz = '%dx%d' % (w, h)
    fb, mb = open(src, 'rb').read(), open(mk, 'rb').read()
    fields = {'model': MODEL, 'prompt': prompt, 'size': sz, 'quality': QUALITY, 'n': '1', 'input_fidelity': 'high'}
    body, ct = SF.multipart(fields, {'image': (jid + '.png', fb, 'image/png'), 'mask': (jid + '-mask.png', mb, 'image/png')})
    d, err = SF.call(key, API_EDIT, body, ct)
    if not d and err and 'input_fidelity' in err:   # a model that takes no fidelity setting
        fields.pop('input_fidelity')
        body, ct = SF.multipart(fields, {'image': (jid + '.png', fb, 'image/png'), 'mask': (jid + '-mask.png', mb, 'image/png')})
        d, err = SF.call(key, API_EDIT, body, ct)
    if not d:
        return jid, err
    n = save(png, meta, d, {'id': jid, 'stage': stage, 'prompt': prompt, 'size': sz, 'source': CHOSEN[kind],
                            'source_sha': hashlib.sha256(fb).hexdigest()[:16], 'mask_sha': hashlib.sha256(mb).hexdigest()[:16]})
    return jid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='frames', choices=('frames', 'glass', 'rooms', 'crowd'))
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    js = [j for j in jobs(a.stage) if not only or j[0] in only]
    if a.list:
        for j in js:
            print(a.stage, j[0], j[3])
        return
    key = SF.api_key()
    print('%d images, stage %s, model %s, quality %s' % (len(js), a.stage, MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for jid, what in ex.map(lambda j: make(key, a.stage, j[0], j[1], j[2], j[3], a.force), js):
            print(jid, what, flush=True)


if __name__ == '__main__':
    main()
