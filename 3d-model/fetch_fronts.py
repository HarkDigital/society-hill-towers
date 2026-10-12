#!/usr/bin/env python3
"""Generate the house fronts for the facade prototype (Oct 12, Mike: "prototype both blocks with AI-generated
fronts"): one straight-on elevation per prompt from OpenAI's image API, written to lidar_cache/fronts_raw/<set>/<id>.png
with a sidecar <id>.json (the prompt, the model, the size, when). bake_fronts.py cuts them into the atlas.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is
never printed. A front already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
FRONTS_MODEL picks the model (default gpt-image-2), FRONTS_QUALITY the quality (default high).

Each prompt asks for ONE house filling the frame: the party walls at the left and right edges, the sidewalk line at
the foot, the top of the cornice at the head, no perspective, no sky, flat overcast light, dark unlit glass. That is
what lets the page stretch a front across a house's own street wall, and lets the bake find the windows by their
dark glass."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'fronts_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('FRONTS_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('FRONTS_QUALITY', 'high')
SIZE = '768x1280'   # 3:5, both sides multiples of 16 (gpt-image-2 takes any such size between 1:3 and 3:1)

FRAME = ('Architectural front elevation photograph, perfectly orthographic and straight-on, of ONE {what} in {where}, '
         'Philadelphia. The facade fills the whole frame edge to edge: the left and right edges of the image are the party '
         'walls shared with the neighbouring houses (no gaps, no neighbouring houses, no side walls visible), the bottom '
         'edge is the sidewalk line at the foot of the front steps, and the top edge is the top of the cornice (no roof, '
         'no sky). No perspective, no vanishing lines, no camera tilt, every window the same size on its floor. Soft even '
         'overcast daylight with no cast shadows. No people, no cars, no trees, no street signs, no lettering or house '
         'numbers, no awnings and no canopies. The window glass is dark and unlit with crisp frames. Photorealistic, high '
         'detail, natural colours.')

SH = 'Society Hill'
SP = 'South Philadelphia'
EP = 'East Passyunk Avenue, South Philadelphia'
NP = 'North Philadelphia'
WP = 'West Philadelphia'
NE = 'Northeast Philadelphia'
FT = 'Fishtown'
GT = 'Germantown'
KS = 'Kensington'
FRONTS = [
    # Society Hill: three storeys and a half, 18th- and early 19th-century rows on Spruce, Pine and Delancey
    ('federal', 'f1', SH, 'three-storey Federal-style rowhouse of red brick laid in Flemish bond, three bays wide, a black '
     'six-panel front door with a semicircular fanlight in the left bay, white marble front steps, white six-over-six '
     'double-hung windows with black louvred shutters and marble sills, a plain white wooden box cornice'),
    ('federal', 'f2', SH, 'three-storey Georgian rowhouse of deep red brick, three bays, a door with a rectangular transom '
     'and fluted wooden pilasters in the right bay, marble steps with black wrought-iron railings, white flat-arch '
     'lintels with keystones, a white modillion cornice'),
    ('federal', 'f3', SH, 'three-storey Greek Revival townhouse of smooth pressed red brick over a white marble basement, '
     'three bays, a recessed doorway in a white marble surround, tall parlour-floor windows with a black iron balconette '
     'on the second floor, marble lintels and sills, a white dentil cornice'),
    ('federal', 'f4', SH, 'three-storey Federal rowhouse with its brick painted a soft warm cream, three bays, a dark green '
     'door with a fanlight, white marble steps, dark green louvred shutters, a white box cornice'),
    ('federal', 'f5', SH, 'three-storey Federal rowhouse of dark brownish-red brick, two bays wide, the door in the right '
     'bay with a four-light transom, marble steps, black shutters, simple stone sills and lintels, a narrow white '
     'cornice'),
    ('federal', 'f6', SH, 'three-storey 1960s modernist infill townhouse of dark red brick in Society Hill, a recessed '
     'entrance with a plain dark door, tall narrow vertical windows with dark metal frames, a flat brick parapet'),
    ('federal', 'f7', SH, 'four-storey Italianate townhouse of red brick with brownstone trim, three bays, segmental-arched '
     'window heads, a brownstone stoop of five steps with iron railings, a deep bracketed wooden cornice painted '
     'dark brown'),
    ('federal', 'f8', SH, 'three-storey Federal rowhouse of orange-red brick in Flemish bond with glazed headers, three '
     'bays, a red door with a fanlight and a white wooden door surround, marble steps, white shutters folded back, a '
     'white box cornice with a simple moulding'),
    # South Philadelphia: two-storey rows on the small streets between the numbered ones
    ('southrow', 's1', SP, 'two-storey red brick rowhouse, two bays wide, a white aluminium storm door and one window on '
     'the ground floor, two windows upstairs, a two-step concrete stoop, a plain brick parapet with a thin metal cap'),
    ('southrow', 's2', SP, 'two-storey rowhouse faced in grey-beige formstone (cast stone veneer), two bays, a glass-block '
     'window on the ground floor, two white vinyl windows upstairs, a marble step'),
    ('southrow', 's3', SP, 'two-storey brick rowhouse with a projecting second-floor bay window clad in painted dark green '
     'wood with three sashes, a dark door and one window on the ground floor, a small metal cornice above the bay'),
    ('southrow', 's4', SP, 'two-storey rowhouse with its brick painted dusty blue, two bays, a red front door, white '
     'window trim, a white bracketed wooden cornice, two marble steps'),
    ('southrow', 's5', SP, 'two-storey late 19th-century brick rowhouse, two bays, tall narrow two-over-two windows with '
     'white marble lintels and sills, three white marble steps, an Italianate bracketed pressed-metal cornice painted '
     'brown'),
    ('southrow', 's6', SP, 'two-storey rowhouse with a stucco front painted pale yellow, two bays, a white storm door '
     'and one window on the ground floor, two windows upstairs'),
    ('southrow', 's7', SP, 'renovated two-storey brick rowhouse, two bays, new black-framed windows, a modern dark grey '
     'front door with a narrow glass panel, a clean brick parapet'),
    ('southrow', 's8', SP, 'two-storey brown brick rowhouse, two bays, a black metal security storm door, a window '
     'air-conditioner in one upstairs window, a single concrete step'),
    # East Passyunk Avenue: three-storey rows with shops on the ground floor (Oct 12, Mike: "generate storefronts")
    ('shop', 'p1', EP, 'three-storey brick rowhouse with a corner-bar storefront on the ground floor: dark stained wood '
     'panelling, two large plate-glass windows either side of a recessed glazed door, a blank dark wooden signboard over '
     'the shopfront, two sash windows on each upper floor, a bracketed cornice'),
    ('shop', 'p2', EP, 'three-storey brick rowhouse with a bakery storefront on the ground floor: a white and green tiled '
     'base, wide display windows with thin bronze frames, a glazed door at one side, a blank cream signboard, '
     'Italianate windows with stone lintels above'),
    ('shop', 'p3', EP, 'three-storey painted brick rowhouse (sage green) with a cafe storefront: black steel-framed '
     'floor-to-ceiling glazing in a grid, a black door, a blank black signboard band, white-trimmed sash windows above'),
    ('shop', 'p4', EP, 'three-storey 19th-century building with a cast-iron storefront painted dark red: slender fluted '
     'columns, tall display windows, a recessed entry, a blank cornice board over the shopfront, brick upper floors with '
     'arched window heads and a pressed-metal cornice'),
    ('shop', 'p5', EP, 'two-storey brick rowhouse with a 1960s aluminium storefront: a wide plate-glass window and a glass '
     'door in silver aluminium frames, a blank white signboard, a stuccoed upper floor with two windows'),
    ('shop', 'p6', EP, 'three-storey brick rowhouse with a boutique storefront in painted wood (deep navy): a bay of small '
     'display panes over a panelled base, a recessed door with a transom, a blank navy signboard, sash windows above'),
    ('shop', 'p7', EP, 'three-storey brick rowhouse with a corner-store front: a metal roll-down security gate raised '
     'halfway over a glass shop door and window, a blank faded signboard, a stucco-faced ground floor, sash windows '
     'above'),
    ('shop', 'p8', EP, 'three-storey limestone-trimmed brick building with a restaurant storefront: tall arched wooden '
     'French doors and windows across the ground floor, a blank stone sign panel, three windows on each upper floor, a '
     'stone cornice'),
    # Oct 12, citywide (Mike: "much of the app is still showing the old style where buildings have no doors and all
    # look alike"): the city's other row and house types, one set a type, assigned by the property records
    ('victorian', 'v1', NP, 'three-storey Italianate brick rowhouse, three bays, tall two-over-two windows with carved '
     'brownstone lintels, a wooden door with a transom at one side up three brownstone steps, a deep bracketed wooden '
     'cornice painted dark green'),
    ('victorian', 'v2', NP, 'three-storey brownstone-fronted rowhouse, three bays, segmental arched window heads, a pair '
     'of tall wooden doors with a glass transom up a brownstone stoop, a bracketed cornice'),
    ('victorian', 'v3', NP, 'three-storey red brick Queen Anne rowhouse, two bays, decorative brick bands, arched windows '
     'on the top floor, a stained-glass transom over a dark wooden door, a pressed-metal cornice'),
    ('victorian', 'v4', NP, 'three-storey rowhouse with its brick painted white, three bays, black window frames, a black '
     'door, a white bracketed cornice'),
    ('victorian', 'v5', NP, 'three-storey worn red brick rowhouse, three bays, stone sills, one window boarded with '
     'plywood, a metal security door, a plain brick cornice'),
    ('victorian', 'v6', NP, 'three-storey rowhouse of dark red brick with yellow brick trim around the windows, three '
     'bays, a deep red door, a decorative pressed-tin cornice painted cream'),
    ('victorian', 'v7', NP, 'three-storey renovated brick rowhouse, three bays, new black-framed windows, a modern '
     'charcoal door, the original bracketed cornice painted black'),
    ('victorian', 'v8', NP, 'three-storey rowhouse with a stucco front painted pale grey, three bays, white trim, a teal '
     'door, a simple cornice'),
    ('porch', 'h1', WP, 'two-storey half of a brick twin house (the porch removed): a front door and a wide window on the '
     'ground floor, two windows upstairs, red brick with white trim'),
    ('porch', 'h2', WP, 'two-storey half of a twin house (the porch removed) with a grey Wissahickon stone ground floor and '
     'stucco above, a dark wooden door, a double window, two windows upstairs with green shutters'),
    ('porch', 'h3', WP, 'two-storey half of a brick twin house (the porch removed), tan brick, a door with sidelights, a '
     'three-part window, two upstairs windows with stone lintels'),
    ('porch', 'h4', WP, 'two-storey house front (the porch removed) clad in white clapboard, a blue door, a double window, '
     'two upstairs windows with black shutters'),
    ('porch', 'h5', WP, 'two-storey half of a brick twin house (the porch removed) with its brick painted dark red, a white '
     'door, a wide window, two upstairs windows'),
    ('porch', 'h6', WP, 'two-storey half of a twin house (the porch removed), yellow-brown brick, a wooden door with a '
     'small glass panel, a picture window, two upstairs windows with arched brick heads'),
    ('porch', 'h7', WP, 'two-storey house front (the porch removed) in grey stucco, a red door, a double window, two '
     'upstairs windows'),
    ('porch', 'h8', WP, 'two-storey half of a stone twin house (the porch removed), rough grey schist with white mortar, a '
     'dark green door, white window frames'),
    ('airlite', 'a1', NE, 'two-storey 1950s Northeast Philadelphia "airlite" brick rowhouse: a single garage door at the '
     'bottom of the front, the front door and a large picture window up a short flight of steps above it, two windows '
     'upstairs, a flat roof line'),
    ('airlite', 'a2', NE, 'two-storey 1940s brick rowhouse, light tan brick, a front door at one side, a wide picture '
     'window, two upstairs windows, a small stone band'),
    ('airlite', 'a3', NE, 'two-storey 1950s rowhouse of orange-red brick with a garage door below and a glass-block window '
     'beside the front door, two upstairs windows'),
    ('airlite', 'a4', NE, 'two-storey 1930s brick rowhouse with a flat front, a dark door with a small arched window, a '
     'three-part window on the ground floor, two windows upstairs, decorative brick at the top'),
    ('airlite', 'a5', NE, 'two-storey 1950s brick rowhouse with the ground floor clad in white aluminium siding, a garage '
     'door, a front door, two upstairs windows'),
    ('airlite', 'a6', NE, 'two-storey 1940s brown brick rowhouse, a white storm door, a picture window, two upstairs '
     'windows with white vinyl frames'),
    ('airlite', 'a7', NE, 'two-storey 1950s rowhouse of pale grey brick, a garage door below, a red front door, a picture '
     'window and two upstairs windows'),
    ('airlite', 'a8', NE, 'two-storey 1930s Tudor-style brick rowhouse with a little stucco-and-timber detail at the top, '
     'an arched wooden door, leaded windows'),
    ('newbuild', 'n1', FT, 'three-storey 2020s new-construction rowhouse: a garage door and a glass front door on the '
     'ground floor, dark grey brick, black-framed windows, charcoal fibre-cement panels on the top floor'),
    ('newbuild', 'n2', FT, 'three-storey 2010s new rowhouse in red brick with large black-framed windows and a recessed '
     'glass entrance, a wood-slat accent panel'),
    ('newbuild', 'n3', FT, 'three-storey 2020s rowhouse clad in white brick with black windows and a black garage door'),
    ('newbuild', 'n4', FT, 'three-storey 2010s rowhouse with grey stucco and vertical wood cladding, tall windows, a glass '
     'front door'),
    ('newbuild', 'n5', FT, 'four-storey 2020s condo rowhouse in dark brick with floor-to-ceiling windows and small black '
     'Juliet balconies'),
    ('newbuild', 'n6', FT, 'three-storey 2010s rowhouse with tan brick on the ground floor and dark blue fibre-cement '
     'panels above, black windows'),
    ('newbuild', 'n7', FT, 'three-storey 2020s rowhouse of black brick with bronze window frames and a wooden front door'),
    ('newbuild', 'n8', FT, 'three-storey 2010s rowhouse with red brick below and grey metal cladding above, a garage door'),
    ('stonetwin', 'g1', GT, 'two-and-a-half-storey Germantown house front of grey Wissahickon schist stone, a white '
     'panelled door with a fanlight, white six-over-six windows with black shutters'),
    ('stonetwin', 'g2', GT, 'two-storey colonial stone house front, rough grey stone, a red door, white windows'),
    ('stonetwin', 'g3', GT, 'two-storey half of a stone twin house, schist stone below and stucco above, a dark wooden door, '
     'windows with green shutters'),
    ('stonetwin', 'g4', GT, 'two-storey Colonial Revival house front of red brick with a white door surround with pilasters, '
     'white windows with black shutters'),
    ('stonetwin', 'g5', GT, 'two-storey Tudor Revival house front, stone ground floor, stucco and dark timber above, an '
     'arched wooden door, leaded casement windows'),
    ('stonetwin', 'g6', GT, 'two-storey stone house front with a wide arched entry and white trim'),
    ('stonetwin', 'g7', GT, 'two-storey Victorian twin house front clad in painted wooden shingles (sage green), white '
     'trim, a dark door'),
    ('stonetwin', 'g8', GT, 'two-storey stucco house front painted cream, a blue door, white windows with blue shutters'),
    ('siding', 'k1', KS, 'two-storey rowhouse clad in white vinyl siding, a white aluminium storm door, one window on the '
     'ground floor and two upstairs, a concrete step'),
    ('siding', 'k2', KS, 'two-storey rowhouse clad in pale blue aluminium siding, a black security door, white windows'),
    ('siding', 'k3', KS, 'two-storey rowhouse in beige vinyl siding with a glass-block window and a brown door'),
    ('siding', 'k4', KS, 'two-storey rowhouse in grey vinyl siding, white windows, a red door'),
    ('siding', 'k5', KS, 'two-storey rowhouse with a formstone ground floor and yellow aluminium siding upstairs'),
    ('siding', 'k6', KS, 'two-storey rowhouse in green vinyl siding, white trim, a white door'),
    ('siding', 'k7', KS, 'two-storey rowhouse clad in white aluminium siding with a window air-conditioner upstairs'),
    ('siding', 'k8', KS, 'two-storey rowhouse in tan vinyl siding with brick showing on the ground floor, a dark door'),
]

# the towers' facade sections (Oct 12, Mike: "regenerate the skyscrapers to look more realistic"): square, four storeys by
# ten bays (about 16 m a side), meant to repeat in both directions; bake_fronts.py crops each to its own period
TILE_SIZE = '1024x1024'
TILE_FRAME = ('Seamless tileable facade texture for a 3D city model: a perfectly orthographic, straight-on elevation of a '
              'section of the wall of {what} in Center City Philadelphia, exactly four storeys tall and ten window bays '
              'wide. The section repeats seamlessly in both directions: what leaves the right edge comes back at the left, '
              'what leaves the top comes back at the bottom, and every floor line and bay line is evenly spaced. Only the '
              'repeating wall: no ground floor, no roof, no sky, no building edges or corners. Flat even daylight, no '
              'shadows, no reflections of other buildings, no people, no lettering. Photorealistic, high detail.')
TILES = [
    ('tower', 'glass', 'a 1990s office tower clad in a blue-green glass curtain wall: slim silver vertical mullions at '
     'every bay and dark grey spandrel panels at every floor slab'),
    ('tower', 'glassdark', 'a 1980s office tower of dark bronze reflective glass with continuous silver aluminium '
     'horizontal bands at every floor'),
    ('tower', 'precast', 'a 1960s office tower of white precast concrete: a deep grid of square concrete frames, one '
     'recessed dark window set in each'),
    ('tower', 'deco', 'a 1920s Art Deco office tower: buff limestone piers running up between the bays, recessed '
     'windows with dark cast-metal spandrel panels between floors bearing geometric ornament'),
    ('tower', 'brick', 'a postwar apartment tower of tan brick with punched aluminium windows, two to a bay, a few '
     'window air-conditioners'),
    ('tower', 'resi', 'a 1970s concrete residential high-rise with a continuous balcony slab at every floor, glass '
     'sliding doors and pale concrete railings'),
    ('tower', 'silver', 'a 2010s office tower with a silver-blue glass curtain wall and slim vertical aluminium fins at '
     'every bay'),
    ('tower', 'blackgrid', 'a 1970s office tower with a grid of black anodized aluminium and dark tinted glass'),
    ('tower', 'officebrick', 'a 1920s red brick office building with punched windows in pairs and limestone sills and bands'),
    ('tower', 'glassresi', 'a 2010s residential tower of blue-green glass with glass-railed balconies at every floor'),
]


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


def make(key, set_, fid, prompt, size, force):
    out_dir = os.path.join(RAW, set_)
    os.makedirs(out_dir, exist_ok=True)
    png, meta = os.path.join(out_dir, fid + '.png'), os.path.join(out_dir, fid + '.json')
    if os.path.exists(png) and not force:
        return fid, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    for attempt in range(4):
        req = urllib.request.Request(API, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            img = base64.b64decode(d['data'][0]['b64_json'])
            with open(png + '.tmp', 'wb') as f:
                f.write(img)
            os.replace(png + '.tmp', png)
            json.dump({'id': fid, 'set': set_, 'prompt': prompt, 'model': MODEL, 'size': size, 'quality': QUALITY,
                       'created': d.get('created'), 'usage': d.get('usage')}, open(meta, 'w'), indent=1)
            return fid, 'made %d KB' % (len(img) // 1024)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (400, 401, 403):
                return fid, 'refused %d: %s' % (e.code, msg)
            err = '%d %s' % (e.code, msg)
        except Exception as e:
            err = str(e)[:300]
        time.sleep(5 + 10 * attempt)
    return fid, 'failed: ' + err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    key = api_key()
    only = set(filter(None, a.only.split(',')))
    jobs = [(f[0], f[1], FRAME.format(what=f[3], where=f[2]), SIZE) for f in FRONTS]
    jobs += [(t[0], t[1], TILE_FRAME.format(what=t[2]), TILE_SIZE) for t in TILES]
    jobs = [j for j in jobs if not only or j[1] in only]
    print('%d images, model %s, quality %s' % (len(jobs), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for fid, what in ex.map(lambda j: make(key, j[0], j[1], j[2], j[3], a.force), jobs):
            print(fid, what, flush=True)


if __name__ == '__main__':
    main()
