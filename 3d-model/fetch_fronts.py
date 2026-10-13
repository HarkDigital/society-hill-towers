#!/usr/bin/env python3
"""Generate the house fronts for the facade prototype (Oct 12, Mike: "prototype both blocks with AI-generated
fronts"): one straight-on elevation per prompt from OpenAI's image API, written to lidar_cache/fronts_raw/<set>/<id>.png
with a sidecar <id>.json (the prompt, the model, the size, when). bake_fronts.py cuts them into the atlas.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is
never printed. A front already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some (an id
that is also a set's name is refused: name it <set>/<id>, base/shop1 for the shop street floor).
FRONTS_MODEL picks the model (default gpt-image-2), FRONTS_QUALITY the quality (default high).

Each prompt asks for ONE house filling the frame: the party walls at the left and right edges, the sidewalk line at
the foot, the top of the cornice at the head, no perspective, no sky, flat overcast light, dark unlit glass. That is
what lets the page stretch a front across a house's own street wall, and lets the bake find the windows by their
dark glass.

Realism pass (Oct 12, Mike: "make this look more photo realistic and less cartoony"): every set but the South
Philadelphia rows and the lofts was made at 768 by 1280 whatever its house, so the page stretched a four-storey
Rittenhouse front to 1.42 times its height. Those sets are made again at their own houses' proportions (SIZES, with the
storey count spelled out so the floors repeat evenly), into lidar_cache/fronts5_raw/<set>/ beside the first run (which
stays as it was), and a set of one-storey shops joins them (shop1)."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'fronts_raw')
RAW5 = os.path.join(HERE, 'lidar_cache', 'fronts5_raw')   # the realism pass's fronts at their own proportions
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('FRONTS_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('FRONTS_QUALITY', 'high')
SIZE = '768x1280'   # 3:5, both sides multiples of 16 (gpt-image-2 takes any such size between 1:3 and 3:1)
# the realism pass: each set at its nominal house's width to height (bake_fronts.py SETS w, h), and its storeys, which the
# prompt spells out so every upper floor is the same height (the page repeats or drops whole storeys to fit a taller or
# shorter wall, never stretches one). southrow and loft were already at their proportions and are not made again
SIZES = {'federal': ('720x1360', 'three storeys'), 'victorian': ('688x1408', 'three storeys'), 'newbuild': ('704x1408', 'three storeys'),
         'shop': ('704x1376', 'three storeys'), 'rittenhouse': ('640x1504', 'four storeys'), 'mixeduse': ('624x1504', 'four storeys'),
         'univcity': ('736x1296', 'three storeys'), 'airlite': ('832x1248', 'two storeys over a raised basement'),
         'siding': ('800x1248', 'two storeys'), 'manayunk': ('736x1264', 'two storeys'), 'porch': ('1024x1280', 'two storeys'),
         'stonetwin': ('1072x1280', 'two storeys'), 'chestnut': ('1216x1280', 'two storeys'), 'shop1': ('1024x768', 'one storey')}
STOREYS = (' The building is exactly {n} tall under its cornice; every upper storey is the same height and its floor line runs '
           'level across the whole width.')


def storeys(n):
    return ' The building is exactly one storey tall under its parapet.' if n == 'one storey' else STOREYS.format(n=n)

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
    # Round 184 (Mike: "I added another $100 ... so we can use that to model many more items"): 16 fronts a type, six more types
    ('federal', 'f9', SH, 'three-storey Federal rowhouse of soft orange brick, a white Doric door surround, a black door with a rectangular transom, six-over-six windows, marble steps, a white cornice'),
    ('federal', 'f10', SH, 'three-storey Federal rowhouse with its brick painted pale yellow, a dark green door with a fanlight, black shutters, a white box cornice'),
    ('federal', 'f11', SH, 'three-storey Georgian townhouse with a stone belt course between the floors, white sash windows, a pedimented wooden door surround'),
    ('federal', 'f12', SH, 'three-storey Federal rowhouse with a dark arched carriage passage beside the front door, red brick in Flemish bond, white trim'),
    ('federal', 'f13', SH, 'three-storey 1820s rowhouse in weathered red brick with white marble lintels and a blue door up marble steps'),
    ('federal', 'f14', SH, 'three-storey Federal rowhouse with its brick painted grey-blue, white trim, a black door with a fanlight'),
    ('federal', 'f15', SH, 'three-storey restored Federal rowhouse of deep red brick, a white six-panel door with sidelights, black iron railings on marble steps'),
    ('federal', 'f16', SH, 'three-storey Federal rowhouse with window boxes of red geraniums under the first-floor windows, red brick, black shutters'),
    ('southrow', 's9', SP, 'two-storey red brick rowhouse with a white marble stoop of three steps and a wooden door with a small stained-glass panel'),
    ('southrow', 's10', SP, 'two-storey rowhouse faced in pink-beige formstone with a glass-block window beside the door'),
    ('southrow', 's11', SP, 'two-storey brick rowhouse painted mint green with white trim and a white door'),
    ('southrow', 's12', SP, 'two-storey dark red brick rowhouse with a black wrought-iron grille over the ground-floor window and a white door'),
    ('southrow', 's13', SP, 'two-storey rowhouse with a tan stucco front, a brown door and white windows'),
    ('southrow', 's14', SP, 'two-storey brown brick rowhouse with a large ground-floor picture window'),
    ('southrow', 's15', SP, 'two-storey rowhouse with grey siding upstairs and red brick on the ground floor'),
    ('southrow', 's16', SP, 'two-storey rowhouse with white-painted brick, a black door and black window frames'),
    ('shop', 'p9', EP, 'three-storey brick building with a corner bodega on the ground floor: a metal roll-down gate half raised, a glass door, shelves of goods behind the window, a blank signboard'),
    ('shop', 'p10', EP, 'three-storey brick rowhouse with a pizza shop storefront: a red and white tiled base, a big plate-glass window, a blank signboard'),
    ('shop', 'p11', EP, 'three-storey light orange-red brick rowhouse with white stone window sills and lintels above a neighbourhood bar on the ground floor: dark wood panelling, small leaded windows, a blank signboard'),
    ('shop', 'p12', EP, 'three-storey rowhouse with a modern hair salon storefront: a white frame, a wide window, a blank signboard'),
    ('shop', 'p13', EP, 'two-storey building with a laundromat storefront: a wide aluminium-framed window showing washing machines inside, a blank signboard'),
    ('shop', 'p14', EP, 'three-storey building with a small bank branch on the ground floor: smooth limestone, a tall arched window and a bronze door'),
    ('shop', 'p15', EP, 'three-storey brick building with an old hardware store front: wooden display windows, a recessed door, a blank signboard'),
    ('shop', 'p16', EP, 'three-storey rowhouse with a coffee shop storefront in green-painted wood with folding glass windows and a blank signboard'),
    ('victorian', 'v9', NP, 'three-storey brownstone rowhouse with a high stoop and a carved door hood'),
    ('victorian', 'v10', NP, 'three-storey red brick rowhouse with ornate cast-iron window hoods painted black'),
    ('victorian', 'v11', NP, 'three-storey brick rowhouse with tall double wooden doors and dark green trim'),
    ('victorian', 'v12', NP, 'three-storey rowhouse with orange-red painted brick and cream trim'),
    ('victorian', 'v13', NP, 'three-storey brick rowhouse with heavy carved stone window surrounds and a carved stone door frame'),
    ('victorian', 'v14', NP, 'three-storey yellow brick rowhouse with round-arched windows'),
    ('victorian', 'v15', NP, 'three-storey rowhouse with stucco painted terracotta and a dark green door'),
    ('victorian', 'v16', NP, 'three-storey brick rowhouse being restored, new white windows on two floors, a red door'),
    ('porch', 'h9', WP, 'two-storey half of a red brick twin house (the porch removed), a wooden door with an oval glass panel'),
    ('porch', 'h10', WP, 'two-storey half of a twin house (the porch removed) clad in brown wooden shingles'),
    ('porch', 'h11', WP, 'two-storey half of a twin house (the porch removed) in white stucco with dark half-timbering upstairs'),
    ('porch', 'h12', WP, 'two-storey half of a yellow brick twin house (the porch removed)'),
    ('porch', 'h13', WP, 'two-storey half of a twin house (the porch removed) with its brick painted lavender grey'),
    ('porch', 'h14', WP, 'two-storey half of a twin house (the porch removed), stone ground floor and red brick above'),
    ('porch', 'h15', WP, 'two-storey half of a red brick twin house (the porch removed) with leaded-glass upper sashes'),
    ('porch', 'h16', WP, 'two-storey half of a twin house (the porch removed) in green clapboard'),
    ('airlite', 'a9', NE, 'two-storey 1950s brick rowhouse with a garage door below, the front door up steps with a white iron railing'),
    ('airlite', 'a10', NE, 'two-storey 1940s brick rowhouse with a large three-part picture window and a stone sill'),
    ('airlite', 'a11', NE, 'two-storey 1940s rowhouse in pale yellow brick with green trim'),
    ('airlite', 'a12', NE, 'two-storey rowhouse with white stone veneer on the ground floor and red brick above'),
    ('airlite', 'a13', NE, 'two-storey red brick rowhouse with a white garage door and a glass-block window'),
    ('airlite', 'a14', NE, 'two-storey 1930s rowhouse with a Tudor-arched door and patterned brickwork'),
    ('airlite', 'a15', NE, 'two-storey brown brick rowhouse with a black security storm door'),
    ('airlite', 'a16', NE, 'two-storey tan brick rowhouse with a modern replacement garage door'),
    ('newbuild', 'n9', FT, 'four-storey 2020s townhouse in light grey brick with large windows'),
    ('newbuild', 'n10', FT, 'three-storey 2010s rowhouse with black metal cladding and a wooden front door'),
    ('newbuild', 'n11', FT, 'three-storey 2020s red brick rowhouse with black steel window frames'),
    ('newbuild', 'n12', FT, 'three-storey 2010s rowhouse in white stucco with wooden slat accents'),
    ('newbuild', 'n13', FT, 'three-storey 2020s rowhouse in grey brick with a bronze metal panel'),
    ('newbuild', 'n14', FT, 'three-storey 2010s rowhouse with corrugated metal and large glass windows'),
    ('newbuild', 'n15', FT, 'three-storey 2020s rowhouse in brick and sage green fibre cement'),
    ('newbuild', 'n16', FT, 'three-storey 2010s townhouse in charcoal brick with a glass-block stair window'),
    ('stonetwin', 'g9', GT, 'two-storey stone Colonial house front with a flat white portico frame round the door'),
    ('stonetwin', 'g10', GT, 'two-storey stone house front with a red door and white windows with black shutters'),
    ('stonetwin', 'g11', GT, 'two-storey half of a twin house in grey stone and white stucco'),
    ('stonetwin', 'g12', GT, 'two-storey Victorian stone twin-house front with arched windows'),
    ('stonetwin', 'g13', GT, 'two-storey stucco house front painted yellow with white trim'),
    ('stonetwin', 'g14', GT, 'two-storey red brick Colonial Revival house front with green shutters'),
    ('stonetwin', 'g15', GT, 'two-storey stone house front with a wide picture window'),
    ('stonetwin', 'g16', GT, 'two-storey half of a stone twin house with wooden shingles on the upper floor'),
    ('siding', 'k9', KS, 'two-storey rowhouse in white vinyl siding with a blue door'),
    ('siding', 'k10', KS, 'two-storey rowhouse in grey aluminium siding over a formstone base'),
    ('siding', 'k11', KS, 'two-storey rowhouse in beige siding with brown trim'),
    ('siding', 'k12', KS, 'two-storey rowhouse in blue siding with white trim'),
    ('siding', 'k13', KS, 'two-storey rowhouse in yellow siding over a brick base'),
    ('siding', 'k14', KS, 'two-storey rowhouse in green aluminium siding'),
    ('siding', 'k15', KS, 'two-storey rowhouse with red brick below and white siding above'),
    ('siding', 'k16', KS, 'two-storey rowhouse in tan siding with white security bars on the ground-floor window'),
    ('univcity', 'u1', 'University City, West Philadelphia', 'three-storey half of a large Victorian twin house (the porch removed), grey stone ground floor, red brick above, tall windows, a decorative gable band at the top'),
    ('univcity', 'u2', 'University City, West Philadelphia', 'three-storey half of a Queen Anne twin house (the porch removed) in red brick with patterned wooden shingles on the top floor'),
    ('univcity', 'u3', 'University City, West Philadelphia', 'three-storey half of a Victorian twin house (the porch removed) in green serpentine stone with brownstone trim'),
    ('univcity', 'u4', 'University City, West Philadelphia', 'three-storey half of a twin house (the porch removed) in yellow brick with white trim and tall sash windows'),
    ('univcity', 'u5', 'University City, West Philadelphia', 'three-storey half of a Victorian twin house (the porch removed) with its brick painted dark red and cream trim'),
    ('univcity', 'u6', 'University City, West Philadelphia', 'three-storey half of a stone twin house (the porch removed), rough grey stone, arched windows'),
    ('univcity', 'u7', 'University City, West Philadelphia', 'three-storey half of a twin house (the porch removed) in red brick with a large stained-glass stair window'),
    ('univcity', 'u8', 'University City, West Philadelphia', 'three-storey half of a twin house (the porch removed) clad in painted wooden shingles, dark green'),
    ('univcity', 'u9', 'University City, West Philadelphia', 'three-storey half of a brick twin house (the porch removed) with stone lintels and a heavy wooden door'),
    ('univcity', 'u10', 'University City, West Philadelphia', 'three-storey half of a twin house (the porch removed), brownstone below and stucco above'),
    ('univcity', 'u11', 'University City, West Philadelphia', 'three-storey half of a Victorian twin house (the porch removed) in orange brick with black window frames'),
    ('univcity', 'u12', 'University City, West Philadelphia', 'three-storey half of a twin house (the porch removed), grey stone with white window frames'),
    ('univcity', 'u13', 'University City, West Philadelphia', 'three-storey half of a Colonial Revival twin house (the porch removed) in red brick with white shutters'),
    ('univcity', 'u14', 'University City, West Philadelphia', 'three-storey half of a twin house (the porch removed) in pale stucco with a red door'),
    ('univcity', 'u15', 'University City, West Philadelphia', 'three-storey half of a twin house (the porch removed) in dark brick with a decorative brick top band'),
    ('univcity', 'u16', 'University City, West Philadelphia', 'three-storey half of a twin house (the porch removed) in beige brick with green trim'),
    ('chestnut', 'c1', 'Chestnut Hill', 'large two-and-a-half-storey stone house front of grey Wissahickon schist, a central white door with a fanlight, white windows with black shutters'),
    ('chestnut', 'c2', 'Chestnut Hill', 'large stone Colonial Revival house front with a white pedimented door surround and multi-pane windows'),
    ('chestnut', 'c3', 'Chestnut Hill', 'large stone house front with tall casement windows and a heavy oak door in a stone arch'),
    ('chestnut', 'c4', 'Chestnut Hill', 'large Tudor Revival house front, stone ground floor, stucco and dark timbers above'),
    ('chestnut', 'c5', 'Chestnut Hill', 'large Georgian stone house front, symmetrical, with five windows across the upper floor'),
    ('chestnut', 'c6', 'Chestnut Hill', 'large stone house front with dark green shutters and a red door'),
    ('chestnut', 'c7', 'Chestnut Hill', 'large stucco house front painted cream with stone trim and black shutters'),
    ('chestnut', 'c8', 'Chestnut Hill', 'large brick Colonial house front with white trim and a fanlight over the door'),
    ('chestnut', 'c9', 'Chestnut Hill', 'large stone and shingle house front with a wide double window'),
    ('chestnut', 'c10', 'Chestnut Hill', 'large stone house front with leaded-glass windows and an arched door'),
    ('chestnut', 'c11', 'Chestnut Hill', 'large grey stone house front with white window frames and a blue door'),
    ('chestnut', 'c12', 'Chestnut Hill', 'large stone farmhouse-style front with white trim'),
    ('chestnut', 'c13', 'Chestnut Hill', 'large Victorian stone house front with arched windows and a carved door'),
    ('chestnut', 'c14', 'Chestnut Hill', 'large stucco house front painted white with dark timber accents'),
    ('chestnut', 'c15', 'Chestnut Hill', 'large stone house front with two front doors (a twin) and green shutters'),
    ('chestnut', 'c16', 'Chestnut Hill', 'large stone house front with tall sash windows and a white door with sidelights'),
    ('manayunk', 'm1', 'Manayunk', 'narrow two-storey brick rowhouse on a steep hillside street, a door up four concrete steps, two windows upstairs'),
    ('manayunk', 'm2', 'Manayunk', 'narrow two-storey rowhouse in red brick with a white door and white window trim, a short stoop'),
    ('manayunk', 'm3', 'Manayunk', 'narrow two-storey rowhouse in grey stone with a red door'),
    ('manayunk', 'm4', 'Manayunk', 'narrow two-storey rowhouse in blue siding with white trim'),
    ('manayunk', 'm5', 'Manayunk', 'narrow two-storey rowhouse with its brick painted cream and a black door'),
    ('manayunk', 'm6', 'Manayunk', 'narrow two-storey rowhouse of stone and brick with a wooden door'),
    ('manayunk', 'm7', 'Manayunk', 'narrow two-storey brick rowhouse with green shutters'),
    ('manayunk', 'm8', 'Manayunk', 'narrow two-storey rowhouse in yellow siding with a brick base'),
    ('manayunk', 'm9', 'Manayunk', 'narrow two-storey brick rowhouse with a modern black door and black windows'),
    ('manayunk', 'm10', 'Manayunk', 'narrow two-storey stucco rowhouse painted terracotta'),
    ('manayunk', 'm11', 'Manayunk', 'narrow two-storey rowhouse of rough grey stone with white windows'),
    ('manayunk', 'm12', 'Manayunk', 'narrow two-storey brick rowhouse with a glass-block window'),
    ('manayunk', 'm13', 'Manayunk', 'narrow two-storey rowhouse in white siding with a red door'),
    ('manayunk', 'm14', 'Manayunk', 'narrow two-storey brown brick rowhouse with a stone lintel over each window'),
    ('manayunk', 'm15', 'Manayunk', 'narrow two-storey rowhouse with formstone on the ground floor'),
    ('manayunk', 'm16', 'Manayunk', 'narrow two-storey brick rowhouse with an iron railing on its steep front steps'),
    ('loft', 'l1', 'Old City', 'five-storey 1890s brick loft warehouse front, four bays of tall windows, a cast-iron ground floor with large openings'),
    ('loft', 'l2', 'Old City', 'five-storey red brick warehouse converted to loft apartments, black steel windows, a stone cornice'),
    ('loft', 'l3', 'Old City', 'six-storey cream brick loft building with large multi-pane windows and a granite ground floor'),
    ('loft', 'l4', 'Old City', 'five-storey dark brick industrial loft with arched windows on the top floor'),
    ('loft', 'l5', 'Old City', 'four-storey brick warehouse with loading doors on each floor and a hoist beam at the top'),
    ('loft', 'l6', 'Old City', 'five-storey loft building with a cast-iron front painted dark green, tall windows'),
    ('loft', 'l7', 'Old City', 'five-storey brick loft with a faded painted band across the brick and tall windows'),
    ('loft', 'l8', 'Old City', 'six-storey concrete-frame loft with brick infill and wide steel windows'),
    ('loft', 'l9', 'Old City', 'five-storey brown brick warehouse with stone sills and a shopfront on the ground floor'),
    ('loft', 'l10', 'Old City', 'four-storey brick loft with round-arched windows and a decorative brick cornice'),
    ('loft', 'l11', 'Old City', 'five-storey red brick factory loft with tall multi-pane windows'),
    ('loft', 'l12', 'Old City', 'five-storey loft building in yellow brick with black window frames'),
    ('loft', 'l13', 'Old City', 'six-storey brick loft with a ground-floor cafe behind large glass'),
    ('loft', 'l14', 'Old City', 'five-storey brick warehouse with blind arches and small windows'),
    ('loft', 'l15', 'Old City', 'four-storey stone and brick commercial building with tall windows'),
    ('loft', 'l16', 'Old City', 'five-storey brick loft with a rusticated granite base'),
    ('mixeduse', 'x1', 'Center City', 'four-storey Center City brick building with a shop on the ground floor (blank signboard) and three floors of apartments'),
    ('mixeduse', 'x2', 'Center City', 'four-storey building with a restaurant ground floor in black frames and brick above'),
    ('mixeduse', 'x3', 'Center City', 'four-storey Chinatown building with a red-painted ground-floor shop and decorative green tile trim, blank signs'),
    ('mixeduse', 'x4', 'Center City', 'four-storey limestone-fronted building with a boutique on the ground floor'),
    ('mixeduse', 'x5', 'Center City', 'four-storey building with a cafe ground floor and white painted brick above'),
    ('mixeduse', 'x6', 'Center City', 'four-storey brick building with tall windows and a ground-floor bar'),
    ('mixeduse', 'x7', 'Center City', 'four-storey building with a modern glass ground floor and grey brick above'),
    ('mixeduse', 'x8', 'Center City', 'four-storey Victorian commercial building with cast-iron ground floor and brick above'),
    ('mixeduse', 'x9', 'Center City', 'four-storey building with a pharmacy ground floor and tan brick above'),
    ('mixeduse', 'x10', 'Center City', 'four-storey Chinatown building in red brick with a teahouse on the ground floor, blank signboard'),
    ('mixeduse', 'x11', 'Center City', 'four-storey building with a bakery ground floor and cream stucco above'),
    ('mixeduse', 'x12', 'Center City', 'four-storey brick building with a bookshop ground floor and dark green trim'),
    ('mixeduse', 'x13', 'Center City', 'four-storey building with a gallery ground floor and black steel windows above'),
    ('mixeduse', 'x14', 'Center City', 'four-storey stone building with an arched ground floor entrance and shop windows'),
    ('mixeduse', 'x15', 'Center City', 'four-storey building with a deli ground floor and red brick above'),
    ('mixeduse', 'x16', 'Center City', 'four-storey building in white terracotta with a shop ground floor'),
    ('rittenhouse', 'r1', 'Rittenhouse Square', 'four-storey brownstone townhouse near Rittenhouse Square, a high stoop, a carved door surround, tall windows'),
    ('rittenhouse', 'r2', 'Rittenhouse Square', 'four-storey limestone townhouse with elegant tall windows and a wrought-iron balcony rail on the second floor'),
    ('rittenhouse', 'r3', 'Rittenhouse Square', 'four-storey red brick townhouse with white marble trim and black shutters'),
    ('rittenhouse', 'r4', 'Rittenhouse Square', 'four-storey Beaux-Arts limestone townhouse with carved window surrounds'),
    ('rittenhouse', 'r5', 'Rittenhouse Square', 'four-storey brownstone with arched windows and a heavy wooden door'),
    ('rittenhouse', 'r6', 'Rittenhouse Square', 'four-storey brick townhouse with a flat cornice and tall French windows'),
    ('rittenhouse', 'r7', 'Rittenhouse Square', 'four-storey grey stone townhouse with a black door and brass hardware'),
    ('rittenhouse', 'r8', 'Rittenhouse Square', 'four-storey brick townhouse painted white with black window frames'),
    ('rittenhouse', 'r9', 'Rittenhouse Square', 'four-storey Gothic Revival brownstone with pointed arch windows'),
    ('rittenhouse', 'r10', 'Rittenhouse Square', 'four-storey Italianate townhouse in red brick with a bracketed cornice'),
    ('rittenhouse', 'r11', 'Rittenhouse Square', 'four-storey brick townhouse with flower boxes and a dark green door'),
    ('rittenhouse', 'r12', 'Rittenhouse Square', 'four-storey limestone townhouse with a rusticated ground floor'),
    ('rittenhouse', 'r13', 'Rittenhouse Square', 'four-storey brownstone with stone pilasters between the windows'),
    ('rittenhouse', 'r14', 'Rittenhouse Square', 'four-storey red brick Federal-style townhouse with a fanlight door'),
    ('rittenhouse', 'r15', 'Rittenhouse Square', 'four-storey brick townhouse with a modern glass door and restored windows'),
    ('rittenhouse', 'r16', 'Rittenhouse Square', 'four-storey stone townhouse with ornate iron railings at the stoop'),
    # the realism pass: one-storey shops (a shop's record under 7 m wore a three-storey front squashed to half its height)
    ('shop1', 'o1', SP, 'single-storey red brick corner grocery with a wide aluminium display window and a glass door, a plain painted sign band with no lettering, a brick parapet with a metal cap'),
    ('shop1', 'o2', SP, 'single-storey 1950s buff brick takeout shop with a wide plate-glass window, a stainless steel and glass door and a plain sign band'),
    ('shop1', 'o3', SP, 'single-storey shop with a stucco front painted cream, a big display window in a red frame, a glass door and a plain sign band'),
    ('shop1', 'o4', NP, 'single-storey hair salon in a converted garage of grey painted concrete block, a wide black-framed window and a glass door'),
    ('shop1', 'o5', NE, 'single-storey 1960s laundromat of tan brick with a long aluminium storefront window and a glass door'),
    ('shop1', 'o6', SP, 'single-storey dry cleaner of red brick with a glass-block panel beside a display window and a glass door, a plain sign band'),
    ('shop1', 'o7', KS, 'single-storey auto parts store of white painted block, a metal roll-down gate raised over a glass front and a steel door'),
    ('shop1', 'o8', NP, 'single-storey storefront of brown brick with a display window behind a black security grille and a steel door'),
    ('shop1', 'o9', KS, 'single-storey corner bar of dark brick with two small glass-block windows and a heavy wooden door'),
    ('shop1', 'o10', 'Center City', 'single-storey 1920s shop with a limestone front, a recessed glazed entrance and two display windows in bronze frames'),
    ('shop1', 'o11', NP, 'single-storey takeout restaurant of yellow brick with a wide window and a glass door, a plain sign band'),
    ('shop1', 'o12', NE, 'single-storey pharmacy of red brick with a long display window and an automatic glass door'),
    ('shop1', 'o13', FT, 'single-storey cafe with a black-painted wooden storefront, large windows and a glazed door'),
    ('shop1', 'o14', KS, 'single-storey tyre shop of painted concrete block with a wide roll-up garage door and a small office window'),
    ('shop1', 'o15', EP, 'single-storey deli with a green-painted wood and glass storefront over a tiled base'),
    ('shop1', 'o16', 'Chestnut Hill', 'single-storey florist with a timber shopfront painted dark blue and large display windows'),
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
    ('tower', 'goldglass', 'a 1980s office tower clad in gold reflective glass with thin bronze mullions'),
    ('tower', 'greenglass', 'a 1990s office tower of green-tinted glass with white aluminium horizontal bands'),
    ('tower', 'ribbon', 'a 1960s office tower with continuous horizontal ribbon windows between bands of pale grey stone'),
    ('tower', 'brutalist', 'a 1970s brutalist concrete tower with a deep waffle grid of concrete and recessed dark windows'),
    ('tower', 'limestone', 'a 1930s office tower of buff limestone with tall narrow punched windows'),
    ('tower', 'marble', 'a 1950s office building clad in white marble with a grid of dark windows'),
    ('tower', 'terracotta', 'a 1910s office building of cream glazed terracotta with paired windows and ornament between floors'),
    ('tower', 'blueband', 'a 2000s tower of blue glass with white spandrel bands at every floor'),
    ('tower', 'unitized', 'a 2020s tower with a unitized glass curtain wall of large clear panes and slim dark frames'),
    ('tower', 'hotel', 'a 1980s hotel tower of pinkish precast concrete with punched windows'),
    ('tower', 'granite', 'a 1980s postmodern office tower in polished red granite with dark glass windows'),
    ('tower', 'fins', 'a 2010s office tower with glass and thin vertical white fins'),
    ('tower', 'darkbrick', 'a 2020s residential tower of dark brown brick with large black-framed windows'),
    ('tower', 'metalpanel', 'a 2000s tower with silver metal panels and square windows'),
    ('tower', 'greygrid', 'a 1970s office tower with a grid of grey precast panels and bronze-tinted windows'),
    # Round 185 (Mike: make it look photo realistic, facades everywhere): the mid-rise buildings' walls, three to ten storeys
    ('tower', 'aptbrick', 'a 1920s six-storey red brick apartment building with pairs of white double-hung windows and limestone sills'),
    ('tower', 'gardenapt', 'a 1960s apartment building of tan brick with aluminium sliding windows'),
    ('tower', 'loftbrick', 'a 1910s red brick industrial loft with large multi-pane steel windows between brick piers'),
    ('tower', 'warehouse', 'a concrete-frame warehouse with red brick infill panels and wide steel windows'),
    ('tower', 'institution', 'a 1930s brick school building with tall multi-pane windows and limestone bands between floors'),
    ('tower', 'modernapt', 'a 2020s mid-rise apartment building clad in grey and wood-tone fibre-cement panels with large black-framed windows'),
    ('tower', 'commercial', 'a 1950s commercial building of buff brick with long horizontal metal-framed windows'),
    ('tower', 'paintedbrick', 'a building of white-painted brick with black-framed double-hung windows'),
    ('tower', 'officemid', 'a 1980s mid-rise office building of tan precast concrete with continuous bands of dark windows'),
    ('tower', 'stucco', 'a 1990s apartment building with cream stucco walls and white-framed windows'),
]


# the realism pass (critic gap 4): the walls' street floor. The tower and mid-rise walls start 4 or 5 m up, and under them
# stood the procedural ground floor and its storefront boxes; each wall kind now stands on one of these, one storey tall
# and repeating along the street, two of each kind (lidar_cache/fronts5_raw/base/)
BASE_SIZE = '1536x1024'
BASE_FRAME = ('Seamless horizontally tileable facade texture for a 3D city model: a perfectly orthographic, straight-on '
              'elevation of the street-level ground floor of {what} in Center City Philadelphia, exactly one storey about 4.5 '
              'metres tall, filling the frame from the sidewalk line at the bottom edge to the floor line of the storey above at '
              'the top edge, and repeating seamlessly at the left and right edges (what leaves the right edge comes back at the '
              'left): {detail}. No people, no signs, no lettering, no house numbers, no cars, no trees, no awnings and no '
              'canopies, no perspective, soft even overcast daylight with no cast shadows, the glass dark and unlit. '
              'Photorealistic, high detail, natural colours.')
BASES = [
    ('base', 'shop1', 'a mixed-use brick building', 'a run of shopfronts, large dark display windows in black metal frames, a recessed glass shop door, slim red brick piers between the bays and a grey granite base course'),
    ('base', 'shop2', 'a 1920s commercial block', 'cast-iron and wood shopfronts painted dark green with tall display windows over panelled bases and a recessed glazed entrance'),
    ('base', 'apt1', 'a 1920s red brick apartment building', 'a recessed glass entrance in a carved limestone surround, tall windows with black iron grilles and a limestone water table at the foot'),
    ('base', 'apt2', 'a 1950s tan brick apartment building', 'a glazed entrance with aluminium doors, wide windows with aluminium frames and a brick planter wall at the foot'),
    ('base', 'aptmod1', 'a 2020s apartment building', 'a glass lobby entrance, large black-framed windows and dark grey brick and fibre cement panels'),
    ('base', 'aptmod2', 'a 2010s apartment building', 'floor-to-ceiling glass in slim dark frames between pale stone panels, a glass entrance door'),
    ('base', 'lobby1', 'a 1980s glass office tower', 'a lobby wall of dark tinted glass in aluminium mullions, a revolving door and polished grey granite piers and base'),
    ('base', 'lobby2', 'a 2010s glass office tower', 'a tall clear glass lobby wall in slim steel mullions with glass doors and a stone floor line'),
    ('base', 'office1', 'a 1960s office building', 'aluminium storefront glazing with dark glass, square precast concrete piers, a granite base course and a recessed lobby door'),
    ('base', 'office2', 'a 1970s office building', 'a colonnade of dark bronze-clad piers with dark glass between them and a plain concrete base'),
    ('base', 'stone1', 'a 1920s Art Deco office tower', 'a rusticated limestone base with tall arched openings filled with dark glass and bronze doors'),
    ('base', 'stone2', 'a 1930s stone office building', 'polished red granite piers, dark glass display windows in bronze frames and a recessed entrance'),
    ('base', 'loft1', 'a converted brick warehouse', 'large multi-pane steel-framed shop windows between heavy red brick piers and a wide loading door'),
    ('base', 'loft2', 'a converted concrete-frame loft building', 'big glazed openings in black steel frames between painted concrete columns and a glass entrance'),
    ('base', 'school1', 'a 1930s brick school', 'a limestone base course, tall multi-pane windows and a recessed entrance with double wooden doors in a stone surround'),
    ('base', 'school2', 'a 1960s brick institutional building', 'a glazed entrance with aluminium doors, a band of windows over a brick base and a concrete sill line'),
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


def make(key, set_, fid, prompt, size, force, root=RAW):
    out_dir = os.path.join(root, set_)
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


def pick_jobs(only, sets=''):
    """Every image this script makes, as (set, id, prompt, size, root), narrowed to --only's ids and --sets' sets. An id is
    a file's name inside its set, and one can name two things: the street floor 'shop1' (base/shop1) and the one-storey
    shop set 'shop1' (o1 to o16), so a bare name that is also a set's is refused (the review: --only shop1 made the street
    floor again), and set/id names exactly one."""
    jobs = [(f[0], f[1], FRAME.format(what=f[3], where=f[2]) + (storeys(SIZES[f[0]][1]) if f[0] in SIZES else ''),
             SIZES[f[0]][0] if f[0] in SIZES else SIZE, RAW5 if f[0] in SIZES else RAW) for f in FRONTS]
    jobs += [(t[0], t[1], TILE_FRAME.format(what=t[2]), TILE_SIZE, RAW) for t in TILES]
    jobs += [(b[0], b[1], BASE_FRAME.format(what=b[2], detail=b[3]), BASE_SIZE, RAW5) for b in BASES]
    clash = sorted(t for t in only if '/' not in t and t in {j[0] for j in jobs})
    if clash:
        sys.exit('--only takes ids, and %s is also a set: pass --sets %s for the set, or base/%s for its street floor'
                 % (clash[0], clash[0], clash[0]))
    return [j for j in jobs if (not only or j[1] in only or j[0] + '/' + j[1] in only) and (not sets or j[0] in sets.split(','))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--sets', default='', help='only these sets (comma separated; tower for the tiles)')
    a = ap.parse_args()
    jobs = pick_jobs(set(filter(None, a.only.split(','))), a.sets)
    key = api_key()
    print('%d images, model %s, quality %s' % (len(jobs), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for fid, what in ex.map(lambda j: make(key, j[0], j[1], j[2], j[3], a.force, j[4]), jobs):
            print(fid, what, flush=True)


if __name__ == '__main__':
    main()
