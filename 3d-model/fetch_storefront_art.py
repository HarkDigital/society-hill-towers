#!/usr/bin/env python3
"""Generate the storefronts' shopfronts (Round 189, Mike: "Do the storefront boxes on Broad Street too"): one straight-on
elevation of a ground-floor shopfront per cell, by trade and width, from OpenAI's image API, written to
lidar_cache/storefront_art_raw/<stage>/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the
usage, and for an edit the mask's sha). bake_storefront_art.py cuts them into the atlas both the OSM storefronts and the
painted shop floors (style 5) wear.

Two stages, so the glass is found exactly: 'frames' makes each shopfront with every pane of glass a flat chroma-key green
(#00FF00) and a blank fascia, bake_storefront_art.py --masks finds the key and writes <id>-mask.png beside it (transparent
over the panes), and 'insides' sends the frame and that mask to /v1/images/edits for the shop's interior seen through the
glass. The bake pastes back only the keyed pixels, so the frame and its mask stay registered to the pixel. 'interiors' is
the fallback (two interiors a trade, composited behind the key by the bake) for edits that drift or are refused. (The first
pilot asked for dark, empty glass instead; dark wood, recess shadows and grey frames are as dark as such panes, so no
finder could cut them out: six of those frames are kept aside in pilot_dark/.)

The review's second set (the M and L classes held one cell a trade, and twelve next-door pairs wore the same one): a
second M and L for every trade, and a third S for the corner groceries, dealt AFTER the first set (MORE, S3) so every
earlier cell keeps its prompt and its image; the second M and L of the grocery, the shop and the takeout are Philadelphia
corner stores (CORNER: the gate's box over the fascia, the windows behind bars, the shelves packed to the ceiling).

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is
never printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
SF_ART_MODEL picks the model (default gpt-image-2), SF_ART_QUALITY the quality (default high).

Every prompt asks for no lettering, no logos, no people and a completely blank sign board: the page writes the shop's own
OSM name on the board itself (never the image model).

Usage: python3 fetch_storefront_art.py [--stage frames|insides|interiors] [--only id,...] [--force] [--list] [--workers 4]"""
import argparse, base64, concurrent.futures, hashlib, json, os, sys, time, urllib.request, urllib.error, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'storefront_art_raw')
API = 'https://api.openai.com/v1/images/generations'
API_EDIT = 'https://api.openai.com/v1/images/edits'
MODEL = os.environ.get('SF_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('SF_ART_QUALITY', 'high')

# the width classes: a nominal width in metres at the image's 4.2 m height, its size (multiples of 16, inside the
# model's 1:3 to 3:1), the layout of its bays
CLASSES = {
    'S': (4.5, '1024x960', 'A glazed shop door with a transom light stands at the {side} end, and beside it one large display '
          'window over a low bulkhead.'),
    'M': (6.0, '1280x896', 'A recessed glazed entrance door with a transom light stands in the middle, between two large '
          'display windows over low bulkheads.'),
    'L': (8.5, '1536x768', 'Three large display windows stand over low bulkheads, with a recessed glazed entrance door with a '
          'transom light between the second and the third.'),
    'XL': (11.0, '1536x592', 'It is a wide double-fronted shop: four large display bays divided by slim mullions over low '
           'bulkheads, and a central recessed glazed entrance with a pair of glass doors.'),
}
# how many cells a class holds per trade (the third XL for the trades the city has most of)
VARIANTS = {'S': 2, 'M': 1, 'L': 1, 'XL': 2}
XL3 = ('retail', 'restaurant', 'takeout', 'cafe', 'grocery')
# the review's second set, numbered on after the first so no earlier cell's prompt moves: one more M and L a trade, one
# more S for the corner groceries
MORE = {'M': 1, 'L': 1}
S3 = ('grocery',)

# the shopfront's construction, cycled per trade so no two neighbouring cells share one
MATERIALS = {
    'alu_brick': 'slim black anodised aluminium frames set in a red brick wall, red brick piers at both ends',
    'green_wood': 'a deep-green painted wooden shopfront with raised-panel wooden bulkheads and slim wooden mullions, '
                  'painted wooden pilasters at both ends',
    'cast_iron': 'a Victorian cast-iron shopfront painted dark oxblood red, slender fluted iron columns between the bays and '
                 'at both ends',
    'bronze_granite': 'bronze aluminium frames between polished grey granite piers, a polished granite bulkhead',
    'white_tile': 'white-painted wooden frames over a bulkhead of small white and black ceramic tiles, white painted '
                  'pilasters at both ends',
    'steel_buff': 'brushed stainless steel frames in a buff brick wall, buff brick piers at both ends',
    'chrome_vitrolite': 'a 1950s shopfront of polished chrome frames, with black structural glass panels on the piers and '
                        'the bulkhead',
    'limestone_bronze': 'smooth pale limestone piers and a limestone base, tall bronze-framed windows',
    'gate_brick': 'dark aluminium frames in a red brick wall, and a plain grey steel box for a roll-down security gate '
                  'mounted across the top under the fascia, the gate fully rolled up and out of sight',
    'rollup': 'a brick wall holding a wide closed corrugated steel roll-up door painted grey, and one display window beside '
              'it',
    'navy_wood': 'a painted navy-blue wooden shopfront with panelled wooden bulkheads, painted pilasters at both ends',
    'bronze_tan': 'dark bronze 1970s aluminium storefront framing in a tan brick wall, tan brick piers at both ends',
    'dark_wood': 'a dark stained wooden shopfront with small-paned windows over a panelled wooden base, dark wooden '
                 'pilasters at both ends',
    'corner_bars': 'dark aluminium frames in a painted brick wall, plain black steel security bars fixed across the display '
                   'windows, and a plain grey steel box for a roll-down security gate mounted across the top under the '
                   'fascia, the gate fully rolled up and out of sight',
    'corner_gate': 'a worn red brick wall with plain dark aluminium frames, a plain grey steel box for a roll-down security '
                   'gate mounted across the top under the fascia, the gate fully rolled up, scuffed paint on the bulkheads',
}
BOARDS = ('black', 'dark green', 'cream', 'deep oxblood red', 'navy blue', 'white', 'charcoal grey', 'deep burgundy',
          'pale grey', 'forest green')
WHERES = ('South Philadelphia', 'Center City', 'Fishtown', 'North Philadelphia', 'East Passyunk Avenue',
          'Old City')

# the trades (bake_storefronts.py FAMILIES has the same order): name, what, materials, half glass, interior
FAMILIES = [
    ('retail', 'neighbourhood shop', ('alu_brick', 'steel_buff', 'gate_brick', 'chrome_vitrolite', 'bronze_tan', 'navy_wood'), 0,
     'a small shop: shelves of boxed goods in plain unbranded packaging, display stands, a counter at the back'),
    ('restaurant', 'sit-down restaurant', ('green_wood', 'cast_iron', 'alu_brick', 'white_tile', 'bronze_granite', 'dark_wood'), 0,
     'a restaurant: set tables with white cloths and chairs, pendant lamps, a bar at the back'),
    ('takeout', 'takeout pizza and cheesesteak shop', ('bronze_tan', 'steel_buff', 'gate_brick', 'chrome_vitrolite', 'alu_brick'), 0,
     'a takeout shop: a service counter under a blank dark menu board, a drinks cooler, a few stools, bright ceiling lights'),
    ('cafe', 'coffee shop', ('white_tile', 'green_wood', 'alu_brick', 'navy_wood', 'steel_buff'), 0,
     'a coffee shop: an espresso counter, a pastry case, small round tables and chairs, potted plants'),
    ('bar', 'neighbourhood corner bar', ('dark_wood', 'green_wood', 'cast_iron', 'alu_brick'), 1,
     'a bar: a long wooden bar, rows of bottles on backlit shelves, bar stools, warm low light'),
    ('bank', 'bank branch', ('limestone_bronze', 'bronze_granite', 'limestone_bronze'), 1,
     'a bank: a bright lobby, teller counters, a few desks'),
    ('pharmacy', 'pharmacy', ('steel_buff', 'bronze_tan', 'alu_brick', 'white_tile'), 1,
     'a pharmacy: bright white aisles of shelves with plain unbranded boxes, a pharmacy counter at the back'),
    ('grocery', 'corner grocery store', ('gate_brick', 'bronze_tan', 'steel_buff', 'alu_brick', 'gate_brick'), 0,
     'a corner grocery: shelves packed with plain unbranded goods, a deli counter, glass-door drink coolers'),
    ('bakery', 'bakery', ('white_tile', 'green_wood', 'cast_iron', 'navy_wood'), 0,
     'a bakery: glass cases of bread loaves and pastries, wooden shelves of bread behind the counter'),
    ('boutique', 'clothing boutique', ('navy_wood', 'cast_iron', 'alu_brick', 'white_tile', 'chrome_vitrolite'), 0,
     'a clothing boutique: racks of clothes, a mannequin, folded clothes on wooden tables'),
    ('salon', 'hair salon', ('alu_brick', 'white_tile', 'chrome_vitrolite', 'steel_buff'), 0,
     'a hair salon: styling chairs facing large mirrors, a reception desk, plants'),
    ('venue', 'small theatre', ('limestone_bronze', 'cast_iron', 'bronze_granite'), 1,
     'a small theatre lobby: warm lights, a ticket counter, poster cases holding blank posters'),
    ('trade', 'hardware store', ('rollup', 'gate_brick', 'bronze_tan', 'rollup'), 0,
     'a hardware store: tools hanging on pegboard, shelves of paint cans in plain unlabelled tins, bins of parts'),
]
FAM_IX = {f[0]: k for k, f in enumerate(FAMILIES)}
# the corner stores among the second set (the review: every trade's art was upscale and tidy, and the corner stores along
# Philadelphia's avenues are neither): what, the material and the interior, in place of the trade's own
CORNER_WHAT = 'Philadelphia corner store'
CORNER_INSIDE = ('a cluttered Philadelphia corner store: shelves crammed to the ceiling with snacks and plain unbranded '
                 'packaged goods, racks of chip bags in plain unprinted wrappers, glass-door drink coolers, a counter behind a '
                 'tall clear plexiglass security screen, bright fluorescent ceiling lights')
CORNER = {'grocery-M-1': 'corner_bars', 'grocery-L-1': 'corner_gate', 'grocery-S-2': 'corner_bars',
          'retail-M-1': 'corner_gate', 'retail-L-1': 'corner_bars', 'takeout-M-1': 'corner_bars', 'takeout-L-1': 'corner_gate'}

FRAME_SF = ('Architectural front elevation photograph, perfectly orthographic and straight-on, of the ground-floor shopfront '
            'of ONE {what} on a commercial street in {where}, Philadelphia, about {w:g} metres wide and exactly one storey '
            '(4.2 metres) tall. The shopfront fills the frame edge to edge: the bottom edge of the image is the sidewalk line '
            'at the foot of its bulkhead and door, the top edge is the top of its sign fascia, and the left and right edges are '
            'the masonry piers at its ends (no neighbouring shops, no upper floors, no sky, no side walls, no sidewalk). '
            '{layout}{half} The construction: {material}. Across the whole top runs a plain flat fascia board for the shop\'s '
            'sign, about 70 centimetres tall, painted one even {board}, completely blank: no lettering, no logo, no numbers, no '
            'pictures. Every pane of glass (the display windows, the door glass and any transom lights) is filled with a flat, '
            'uniform, pure chroma-key green (#00FF00) with no texture, no reflections and no shading, so the panes can be cut '
            'out later; the frames, mullions, bulkheads, piers and the door are real materials. No '
            'perspective, no vanishing lines, every vertical line vertical. Soft even overcast daylight, no cast shadows, no '
            'reflections of the street. No people, no cars, no trees, no awnings or canopies, no posters, no menus, no '
            'stickers, no signs, no lettering or logos anywhere. Photorealistic, high detail, natural colours.')
HALF = {1: ' The windows are set high over a solid base of stone or brick about one metre tall; the door goes down to the '
           'sidewalk.'}
INSIDE_SF = ('Fill only the transparent window and door glass with what is seen through clean shop glass from the sidewalk by '
             'day: the softly lit interior of {interior}, with natural depth and perspective, its own warm ceiling lights on, '
             'seen straight on. Goods in plain unbranded packaging; no readable text, labels, menus, logos or signs anywhere, '
             'no people. Keep everything outside the glass exactly as it is: the frames, mullions, bulkheads, piers and the '
             'blank fascia board stay unchanged.')
INTERIOR_SF = ('Photograph of the softly lit interior of {interior}, seen straight on through a shop window from the sidewalk '
               'by day, at eye level, natural depth, warm ceiling lights on. Goods in plain unbranded packaging; no readable '
               'text, labels, menus, logos or signs anywhere, no people, no window frame. Photorealistic, natural colours.')


def cells():
    """Every cell, as (id, family, class, variant, prompt, size): the trades in order, the classes S, M, L, XL, then the
    second set (MORE, S3) numbered on from the trade's first, so the first set's prompts are what they were."""
    out = []
    for fk, (fam, what, mats, half, interior) in enumerate(FAMILIES):
        n = 0
        plan = []
        for cls in ('S', 'M', 'L', 'XL'):
            nv = VARIANTS[cls] + (1 if cls == 'XL' and fam in XL3 else 0)
            plan += [(cls, v) for v in range(nv)]
        plan += [('S', VARIANTS['S'])] if fam in S3 else []
        plan += [(cls, VARIANTS[cls] + j) for cls in ('M', 'L') for j in range(MORE.get(cls, 0))]
        for cls, v in plan:
            w, size, layout = CLASSES[cls]
            cid = '%s-%s-%d' % (fam, cls, v)
            mat = MATERIALS[CORNER[cid]] if cid in CORNER else MATERIALS[mats[(n + fk) % len(mats)]]
            board = BOARDS[(fk * 3 + n * 7) % len(BOARDS)]
            where = WHERES[(fk + n) % len(WHERES)]
            if fam in ('restaurant', 'grocery') and cls == 'XL' and v == 1:
                where = 'Chinatown'
            lay = layout.format(side='left' if (n + fk) % 2 == 0 else 'right')
            prompt = FRAME_SF.format(what=CORNER_WHAT if cid in CORNER else what, where=where, w=w, layout=lay,
                                     half=HALF.get(half, ''), material=mat, board=board)
            out.append((cid, fam, cls, v, prompt, size))
            n += 1
    return out


def interior_of(cid, fam):
    """What the edit paints into a cell's glass: the trade's interior, or a corner store's."""
    return CORNER_INSIDE if cid in CORNER else FAMILIES[FAM_IX[fam]][4]


def api_key():
    k = os.environ.get('OPENAI_API_KEY')
    if k:
        return k.strip()
    p = os.path.expanduser('~/.config/philly3d/openai.env')
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line.startswith('OPENAI_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    sys.exit('no OPENAI_API_KEY in the environment or ~/.config/philly3d/openai.env')


def multipart(fields, files):
    """A multipart/form-data body: fields {name: str}, files {name: (filename, bytes, type)}."""
    b = uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode())
    for k, (fn, data, ct) in files.items():
        out.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: %s\r\n\r\n' % (b, k, fn, ct)).encode())
        out.append(data)
        out.append(b'\r\n')
    out.append(('--%s--\r\n' % b).encode())
    return b''.join(out), 'multipart/form-data; boundary=' + b


def call(key, url, body, ctype):
    """One request with retries: (json, None) or (None, the error)."""
    err = None
    for attempt in range(4):
        req = urllib.request.Request(url, data=body, method='POST', headers={'Authorization': 'Bearer ' + key, 'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req, timeout=400) as r:
                return json.load(r), None
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:400]
            if e.code in (400, 401, 403):
                return None, 'refused %d: %s' % (e.code, msg)
            err = '%d %s' % (e.code, msg)
        except Exception as e:
            err = str(e)[:300]
        time.sleep(5 + 10 * attempt)
    return None, 'failed: ' + str(err)


def save(png, meta, d, info):
    img = base64.b64decode(d['data'][0]['b64_json'])
    with open(png + '.tmp', 'wb') as f:
        f.write(img)
    os.replace(png + '.tmp', png)
    info.update({'model': MODEL, 'quality': QUALITY, 'created': d.get('created'), 'usage': d.get('usage')})
    json.dump(info, open(meta, 'w'), indent=1)
    return len(img)


def make_frame(key, cid, prompt, size, force):
    d0 = os.path.join(RAW, 'frames')
    os.makedirs(d0, exist_ok=True)
    png, meta = os.path.join(d0, cid + '.png'), os.path.join(d0, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = call(key, API, body, 'application/json')
    if not d:
        return cid, err
    n = save(png, meta, d, {'id': cid, 'stage': 'frames', 'prompt': prompt, 'size': size})
    return cid, 'made %d KB' % (n // 1024)


def make_inside(key, cid, fam, size, force):
    fr = os.path.join(RAW, 'frames', cid + '.png')
    mk = os.path.join(RAW, 'frames', cid + '-mask.png')
    d0 = os.path.join(RAW, 'insides')
    os.makedirs(d0, exist_ok=True)
    png, meta = os.path.join(d0, cid + '.png'), os.path.join(d0, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    if not os.path.exists(fr) or not os.path.exists(mk):
        return cid, 'no frame or mask yet (run the frames, then bake_storefront_art.py --masks)'
    prompt = INSIDE_SF.format(interior=interior_of(cid, fam))
    fb, mb = open(fr, 'rb').read(), open(mk, 'rb').read()
    fields = {'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': '1', 'input_fidelity': 'high'}
    body, ct = multipart(fields, {'image': (cid + '.png', fb, 'image/png'), 'mask': (cid + '-mask.png', mb, 'image/png')})
    d, err = call(key, API_EDIT, body, ct)
    if not d and err and 'input_fidelity' in err:   # a model that takes no fidelity setting
        fields.pop('input_fidelity')
        body, ct = multipart(fields, {'image': (cid + '.png', fb, 'image/png'), 'mask': (cid + '-mask.png', mb, 'image/png')})
        d, err = call(key, API_EDIT, body, ct)
    if not d:
        return cid, err
    n = save(png, meta, d, {'id': cid, 'stage': 'insides', 'prompt': prompt, 'size': size,
                            'frame_sha': hashlib.sha256(fb).hexdigest()[:16], 'mask_sha': hashlib.sha256(mb).hexdigest()[:16]})
    return cid, 'made %d KB' % (n // 1024)


def make_interior(key, fam, k, force):
    cid = '%s-%d' % (fam, k)
    d0 = os.path.join(RAW, 'interiors')
    os.makedirs(d0, exist_ok=True)
    png, meta = os.path.join(d0, cid + '.png'), os.path.join(d0, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    prompt = INTERIOR_SF.format(interior=FAMILIES[FAM_IX[fam]][4])
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': '1536x1024', 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = call(key, API, body, 'application/json')
    if not d:
        return cid, err
    n = save(png, meta, d, {'id': cid, 'stage': 'interiors', 'prompt': prompt, 'size': '1536x1024'})
    return cid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='frames', choices=('frames', 'insides', 'interiors'))
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    cs = [c for c in cells() if not only or c[0] in only]
    if a.list:
        for c in cs:
            print(c[0], c[5])
        print(len(cs), 'cells')
        return
    key = api_key()
    if a.stage == 'interiors':
        jobs = [(f[0], k) for f in FAMILIES for k in range(2) if not only or f[0] in only]
        run = lambda j: make_interior(key, j[0], j[1], a.force)
    elif a.stage == 'insides':
        jobs = cs
        run = lambda c: make_inside(key, c[0], c[1], c[5], a.force)
    else:
        jobs = cs
        run = lambda c: make_frame(key, c[0], c[4], c[5], a.force)
    print('%d images, stage %s, model %s, quality %s' % (len(jobs), a.stage, MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for cid, what in ex.map(run, jobs):
            print(cid, what, flush=True)


if __name__ == '__main__':
    main()
