#!/usr/bin/env python3
"""Generate the buildings round City Hall their own facades (Round 198, Mike: "The buildings around city hall look too
generic. Make them look more like real life."), from OpenAI's image API, written to lidar_cache/tower_art_raw/<id>.png
with a sidecar <id>.json (the prompt, the model, the size, when, the usage).

One picture a building (two where its faces differ, PSFS's): a straight-on elevation of a narrow vertical strip of its
main street face, a few bays wide, from the sidewalk to the top of its cornice, with its base, a few of its typical
storeys and its top in one picture, so the three share one stone, one colour and one bay rhythm. bake_tower_art.py cuts
each strip into the base, the shaft (whole typical storeys, which repeat up the tower) and the top, at the building's own
bay and storey (TOWERS below, from the research each entry names), and packs them into the atlas 'Cladding the towers'
wraps round the building's own walls by name.

Every pane of glass is asked for as a flat chroma-key green (#00FF00), so the bake finds the windows to the pixel (the
night's rooms and the reflections read them), and the sky over the top as a flat magenta (#FF00FF), so the bake finds
the roofline. No lettering, no signs, no logos: the page draws the PSFS sign itself, as geometry.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is
never printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
TOWER_ART_MODEL picks the model (default gpt-image-2), TOWER_ART_QUALITY the quality (default high).

Usage: python3 fetch_tower_art.py [--only id,...] [--force] [--list] [--workers 2]"""
import argparse, concurrent.futures, json, os, sys
import fetch_storefront_art as SF   # the API plumbing: api_key, call, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'tower_art_raw')
MODEL = os.environ.get('TOWER_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('TOWER_ART_QUALITY', 'high')

STRIP = ('Architectural elevation photograph for a 3D city model, perfectly orthographic and straight-on: a narrow '
         'vertical strip of {where} of {name} in Philadelphia ({desc}). The strip is exactly {nb} identical window bays '
         'wide, and its left and right edges cut vertically through the middle of a pier, so it repeats seamlessly side by '
         'side. From the bottom edge up it shows: {base}; above that exactly {nf} identical typical storeys, {typical}; and '
         'at the top {top}. The bottom edge is the sidewalk line at the foot of the wall. Above the top of the {topword} '
         'the sky is one perfectly flat, uniform magenta (#FF00FF) up to the top edge, about a twelfth of the image. No '
         'perspective, no vanishing lines, no camera tilt: every floor line exactly level, every window of a storey the '
         'same, the wall flat to the camera. Soft even overcast daylight, no cast shadows. Every pane of window glass is '
         'one flat, uniform pure green (#00FF00) with no reflection, no blinds, no curtains and no texture; the window '
         'frames, sashes, muntins and mullions are drawn in their own colour, and nothing else is that green. {colours} No '
         'people, no cars, no trees, no flags, no street furniture, no air conditioners, no awnings, no signs, no '
         'lettering, no numbers, no plaques and no logos. Photorealistic, high detail, natural colours.')

# a low building's whole wall (the Masonic Temple's three storeys, a church's nave, a tower's stages): the strip is the
# wall itself from the sidewalk to its cornice, no storey repeating
WHOLE = ('Architectural elevation photograph for a 3D city model, perfectly orthographic and straight-on: a narrow vertical '
         'strip of {where} of {name} in Philadelphia ({desc}). The strip is exactly {nb} identical bays wide, and its left '
         'and right edges cut vertically through the middle of a pier, so it repeats seamlessly side by side. From the '
         'bottom edge up it shows: {base}; and at the top {top}. The bottom edge is the sidewalk line at the foot of the '
         'wall. Above the top of the {topword} the sky is one perfectly flat, uniform magenta (#FF00FF) up to the top edge, '
         'about a twelfth of the image. No perspective, no vanishing lines, no camera tilt: every course exactly level, '
         'every bay the same, the wall flat to the camera. Soft even overcast daylight, no cast shadows. Every pane of '
         'window glass is one flat, uniform pure green (#00FF00) with no reflection, no stained glass pattern, no blinds '
         'and no texture; the window frames, tracery, mullions and leading are drawn in their own colour, and nothing else '
         'is that green. {colours} No people, no cars, no trees, no flags, no railings, no street furniture, no signs, no '
         'lettering, no numbers, no plaques and no logos. Photorealistic, high detail, natural colours.')

# the strips: id -> the prompt's fields and the picture's size (multiples of 16, at the strip's own proportions, at least
# 655,360 pixels, inside 1:3). Each entry's research is in bake_tower_art.py TOWERS (its bay, its storey, its zones)
STRIPS = {}


def sz(w_m, h_m, mp=1.6e6):
    """A picture size at a strip's proportions (its sky over it), multiples of 16, inside 3:1, about mp pixels."""
    r = min(3.0, max(1 / 3.0, h_m * 1.09 / w_m))
    w = (mp / r) ** 0.5
    W, H = int(round(w / 16)) * 16, int(round(w * r / 16)) * 16
    return '%dx%d' % (W, H)


def strip(sid, size, **kw):
    kw.setdefault('nf', 5)   # the typical storeys a strip shows (the shaft cell takes up to three from between them)
    STRIPS[sid] = dict(size=size, **kw)


strip('wanamaker', sz(18.3, 70.0), name='the Wanamaker Building (Daniel Burnham, 1902 to 1911, a Florentine Renaissance '
      'palazzo department store)', where='the Market Street front', desc='light warm grey granite over a limestone base',
      nb=3, nf=5,
      base='a two-storey limestone base about 13 m tall: giant fluted limestone pilasters between the bays, a large plate '
           'glass display window in each bay on the ground floor and a second-floor window over a recessed panelled '
           'spandrel, capped by a massive stone entablature and dentilled cornice',
      typical='rusticated granite ashlar with deep horizontal channelled joints, each bay holding a pair of tall six-over-six '
              'double-hung sash windows with dark green frames set in deep reveals and divided by a narrow stone mullion',
      top='a dentilled entablature, then a two-storey arcade of one round arch with radiating stone voussoirs a bay, each '
          'arch capping a pair of tall windows running through both storeys over panelled spandrels, a stone belt course, '
          'a frieze storey of small square windows and a heavy bracketed and dentilled granite cornice', topword='cornice',
      colours='The granite is light warm grey (#bdb6ad), the limestone base a little paler (#c9c1b3), the window frames '
              'dark green.')


strip('masonic', '1024x1600', name='the Masonic Temple (James H. Windrim, 1873, Norman Romanesque)', where='the Filbert Street side',
      desc='light grey granite ashlar, coursed and slightly rock-faced, with smooth dressed trim', nb=3,
      base='a raised ground storey about 7 m tall over a darker granite water table, one round-arched window in each bay with '
           'a moulded granite surround, a moulded string course over it; then the very tall principal storey, about 10 m, '
           'one very tall narrow round-arched window in each bay set in a deep moulded granite surround with slender '
           'colonnettes and a projecting sill on corbels; then an upper storey of a pair of small round-arched windows in '
           'each bay divided by a colonnette; flat granite pilaster strips run up between the bays from the water table to '
           'the cornice', top='an arcaded Lombard corbel table of small round arches under a plain projecting granite '
           'cornice', topword='cornice', typical=None,
      colours='The granite is a pale cool grey (#cccdc6), the water table a shade darker (#b8b9b2), the window sashes '
              'dark grey-green (#3a3c3e).')
strip('masonic-tower', '704x2112', name='the Masonic Temple (James H. Windrim, 1873, Norman Romanesque)',
      where='the great square corner tower, above the main cornice, one face of it', desc='light grey granite ashlar, '
      'coursed and slightly rock-faced, with smooth dressed trim', nb=1,
      base='the bottom edge is the main cornice of the building; the tower face is a square shaft framed by two clasping '
           'buttresses with string courses; first a tall stage with one large wheel (rose) window in a round moulded '
           'surround, then a stage of three tall slender round-arched windows divided by colonnettes, then an arcaded '
           'corbel table and a stage of tall paired round-arched belfry openings with deep jambs and colonnettes, then a '
           'second arcaded corbel table', top='a pierced granite balustrade parapet with the stone bases of the corner '
           'pinnacles at its two ends', topword='parapet', typical=None,
      colours='The granite is a pale cool grey (#cccdc6), the openings dark grey-green (#3a3c3e).')
strip('resinn', '800x2048', name='the Market Street National Bank Building (Ritter and Shay, 1930, Art Deco), now the '
      'Residence Inn', where='the East Penn Square front, facing City Hall', desc='tan-brown face brick on a steel frame, '
      'buff terra cotta and polychrome glazed terra cotta ornament', nb=3,
      base='a four-storey base about 18 m tall: a ground floor of shopfronts with dark granite pilasters and a dark '
           'fascia, then a banking hall of very tall narrow steel multi-pane windows, one in each bay, between fluted buff '
           'terra cotta piers, capped by a continuous Mayan-style terra cotta frieze of blue-grey garland swags between '
           'black hexagonal grilles on buff',
      typical='each bay a group of three narrow windows with white sashes (each window split by a centre mullion and a '
              'transom), separated by slim brick mullion strips, with a wide solid brick pier between the groups; the '
              'brick piers run continuously up the whole shaft with no horizontal string courses, and the spandrel panel '
              'under each window is recessed patterned brick a touch darker',
      top='a top storey of round-arched windows, then the parapet where every brick pier rises above the roofline as a '
          'stepped buttress-like fin capped with buff and orange terra cotta chevron and plume ornaments, a stepped '
          'crenellated parapet between them', topword='parapet',
      colours='The brick is a warm tan-brown (#a8937a), the base terra cotta buff-pink (#cdb49a), the ornament orange '
              '(#b4692e) and turquoise (#2e7f9a), the sashes off-white.', nf=5)


strip('archumc', sz(14.4, 11.0), name='the Arch Street Methodist Church (1870, Gothic Revival)', where='the long nave flank '
      'on Broad Street', desc='pale coursed marble ashlar, white to light grey with faint grey weathering', nb=3,
      base='a low marble plinth, then in each bay one tall two-light pointed lancet window with simple tracery in the head '
           'and a moulded hood mould, set between stepped marble buttresses with gabled weatherings', typical=None,
      top='a moulded marble eave course along the top of the wall', topword='eave course',
      colours='The marble is pale grey-white (#c4c3b9), the plinth a shade darker (#bcbcb0), the stained glass leading dark.')
strip('msb', sz(13.8, 37.0), name='the Municipal Services Building (Vincent Kling, 1965)', where='one face of an arm',
      desc='light grey granite cladding with deep projecting granite window surrounds', nb=8,
      base='a recessed two-storey glass lobby, dark-framed full-height glazing set well back in shadow behind tall tapering '
           'granite piers, one pier every four window bays, carrying a deep plain granite fascia band',
      typical='a strict grid of single punched windows, one per bay, each set in its own projecting granite picture-frame '
              'surround with splayed bevelled sides, so the face reads as rows of shallow boxes; flat light grey granite '
              'between the surrounds, no piers and no ribbons',
      top='a blank windowless granite attic band about two storeys tall with vertical recessed flutes about one bay '
          'apart, ending in a plain flat parapet', topword='parapet',
      colours='The granite is off-white light grey (#dddcd4), the window sashes dark bronze (#5a5650).')
strip('osb', sz(18.6, 43.0), name='One South Broad, the Lincoln-Liberty Building (1932, Art Deco)', where='the Broad Street '
      'front', desc='very light grey limestone ashlar on a steel frame, flat Art Deco carved panels', nb=3,
      base='a three-storey base of polished light granite with tall three-storey shop and lobby windows between flat '
           'granite piers, a plain granite band over them',
      typical='each bay a pair of single punched windows about 1.3 by 2.1 m with dark grey frames, the bays separated by '
              'continuous slightly projecting limestone piers running unbroken up the shaft, flush limestone spandrels',
      top='a setback storey where the piers end in stepped Art Deco caps and flat carved limestone fan and chevron panels '
          'fill the spandrels, then a plain limestone parapet', topword='parapet',
      colours='The limestone is very light warm grey (#c9c4b8), the granite base a little warmer (#b9ae9e), the window '
              'frames dark grey (#3c3d40).')
strip('widener', sz(18.3, 51.0), name='the Widener Building (Horace Trumbauer, 1915, Beaux-Arts)', where='the South Penn '
      'Square front, facing City Hall', desc='smooth Indiana limestone over a granite base, a glazed terra cotta cornice',
      nb=3,
      base='a two-storey base about 12 m tall: a giant order of fluted Corinthian pilasters framing two-storey shop '
           'openings, the ground floor glass and the mezzanine glass with an ornamental dark bronze spandrel between them, '
           'then an entablature with a plain frieze and a dentilled cornice',
      typical='each bay a pair of punched double-hung windows (two over two lights, very dark green frames) set in a '
              'shallow recessed vertical panel with sunk limestone spandrel panels between the floors, thin flat limestone '
              'piers between the bays',
      top='a balustraded ledge, then a three-storey colonnade of fluted engaged Corinthian columns between the bays with '
          'grouped three-light windows recessed between them over dark green metal spandrels, a full entablature and a heavy '
          'modillioned terra cotta main cornice, and over it a plain limestone attic storey of small square windows',
      topword='attic storey',
      colours='The limestone is warm light grey (#d3cec2), the granite base grey (#b9b6ae), the frames and spandrels very '
              'dark green (#2e3f3b).')
strip('girard', sz(16.5, 51.5), name='the Girard Trust Building (McKim, Mead and White, 1931), now the Ritz-Carlton',
      where='the South Penn Square front, facing City Hall', desc='white marble ashlar with faint grey veining', nb=5,
      base='a three-storey base of white marble with taller windows in moulded surrounds and cornice heads on the ground '
           'floor, capped by a balustraded marble cornice',
      typical='a uniform grid of single punched one-over-one windows about 1.4 by 2.1 m with dark bronze frames, one per '
              'bay, in a smooth flat marble wall with no piers',
      top='a three-storey colonnade zone where the windows of three storeys are linked into tall recessed strips with dark '
          'red-brown metal spandrels between flat marble pilasters with simple capitals, then one attic storey of plain '
          'windows, and a projecting marble main cornice with urns along its edge', topword='cornice',
      colours='The marble is bright white (#eeeae2), the frames dark bronze, the strip spandrels dark red-brown (#5a3e37).')
strip('girard-bank', sz(12.0, 20.0), name='the Girard Trust Company banking hall (McKim, Mead and White, 1908), now the '
      'Ritz-Carlton\'s rotunda', where='its side wall on Broad Street', desc='white marble', nb=2,
      base='a marble plinth, then in each bay one tall round-arched window with a moulded marble surround and a keystone, '
           'set between giant fluted Ionic pilasters running the full height', typical=None,
      top='a full marble entablature with a plain frieze and a dentilled cornice, and over it a low marble attic with a '
          'balustrade', topword='balustrade',
      colours='The marble is bright white (#eeeae2), the window frames dark bronze.')
for cid, nm, fl in (('csq1', 'Centre Square East (Vincent Kling, 1973)', 3.8), ('csq2', 'Centre Square West (Vincent Kling, 1974)', 3.7)):
    strip(cid, sz(14.0, 40.0), name='the ' + nm, where='a long face of the tower', desc='buff precast concrete panels with '
          'continuous ribbon windows', nb=5,
          base='a three-level base on massive square buff concrete piers with the glazing recessed deep in shadow: a glass '
               'lobby floor, a recessed glazed second level and a third level of dark louvre grilles, under a deep plain beam',
          typical='a continuous horizontal ribbon window on every floor set back behind the face of the precast, its panes '
                  '1.4 m wide between dark bronze mullions, the glass dark grey-bronze; directly under each ribbon a dark '
                  'recessed sill slot crossed by small trapezoidal precast brackets under every second mullion, then a '
                  'smooth buff precast spandrel band',
          top='a tall plain precast parapet band one storey high cut by a large, deeply recessed rectangular opening',
          topword='parapet', colours='The precast is buff sand (#c2b49c), the mullions dark bronze (#2a2622).')


strip('threepenn', sz(14.5, 34.0), name='Three Penn Center (1958, International Style)', where='its Market Street face',
      desc='continuous ribbon windows alternating with smooth white spandrel bands', nb=5,
      base='a single tall ground storey of dark-framed shopfront glass partly recessed behind slim dark columns, under a '
           'plain white fascia band',
      typical='a continuous horizontal ribbon window on every floor, its panes 1.45 m wide and 2.0 m tall between thin '
              'aluminium mullions, the glass a light blue-green heat-absorbing tint, and between the ribbons an equally '
              'strong smooth white spandrel band about 1.7 m tall with faint horizontal joints, flush with the glass; no '
              'vertical piers anywhere',
      top='the last white spandrel band as the parapet', topword='parapet',
      colours='The spandrels are white (#e3e5e2), the mullions natural aluminium, the base dark (#3a3d3c).')
strip('opsw', sz(15.0, 35.0), name='One Penn Square West (1980s)', where='its 15th Street face', desc='tan precast and '
      'masonry panels with punched windows', nb=5,
      base='a two-storey base of grey-tan stone piers with dark-framed storefront and lobby glazing between them',
      typical='a uniform grid of single punched square-ish windows about 1.6 by 1.8 m, one per bay, with dark grey-green '
              'frames and green-tinted glass, set in a flat tan wall with no piers and no string courses',
      top='a top storey of large deeply recessed rectangular openings, loggia-like, under a plain tan parapet',
      topword='parapet', colours='The wall is tan light brown (#a99b87), the base grey-tan (#8f887c), the frames dark '
      'grey-green (#2f4a4c).')
strip('opsw-glass', sz(9.0, 35.0), name='One Penn Square West (1980s)', where='its rounded green glass corner bay facing '
      'City Hall, shown flat', desc='a gridded curtain wall of green reflective glass', nb=6,
      base='a two-storey glazed lobby of tall green-tinted glass panes in dark frames',
      typical='a gridded curtain wall with dark grey-green mullions about 1.5 m apart, on every floor a vision pane and '
              'below it a spandrel pane of opaque dark green reflective glass (the spandrel panes drawn dark green, not '
              'keyed)', top='a plain dark green metal coping', topword='coping',
      colours='The frames are dark grey-green (#2f4a4c), the spandrel glass deep reflective green (#2c4a40).')


strip('landtitle', sz(12.6, 50.0), name='the Land Title Building (Daniel Burnham, 1902), the south tower', where='the Broad '
      'Street front', desc='light grey to near-white masonry in horizontally banded courses over a granite base', nb=3,
      base='a four-storey base about 18 m tall: two-storey square granite pilasters with simple capitals framing tall '
           'openings, a plain frieze, then two storeys of single windows and a projecting cornice',
      typical='a single punched window a bay, about 1.5 by 2.3 m, a pair of sashes with dark bronze frames recessed in '
              'banded rusticated masonry with continuous horizontal channelled joints, no piers',
      top='a storey of round-arched windows, a belt course, a three-storey colonnade of engaged Corinthian columns with '
          'one window a storey between them, an entablature with an attic storey of small windows and a heavy dentilled '
          'and modillioned cornice', topword='cornice',
      colours='The masonry is near-white light grey (#d6d2c8), the granite base slightly pinker (#cfc5c1), the frames '
              'dark bronze.')
strip('landtitle-north', sz(12.0, 62.0), name='the Land Title Building (Daniel Burnham, 1897), the north building',
      where='the Broad Street front', desc='buff-grey brick laid with deeply raked horizontal joints and stone trim', nb=2,
      base='a two-storey granite base unified by a round-arched arcade, one arch a bay, glazed shopfronts in the arches',
      typical='brick piers running up between the bays; one bay a flat wall with a pair of windows, the next a three-sided '
              'projecting oriel bay window of three windows, alternating; dark bronze frames',
      top='the piers ending in round arches over the top storey, a frieze attic of small arched windows and a deep '
          'bracketed cornice', topword='cornice',
      colours='The brick is buff grey (#b1aa9a), the granite and stone trim light grey (#cfc5c1), the frames dark.')
strip('psfs', sz(15.6, 40.0), name='the PSFS Building (Howe and Lescaze, 1932, International Style)', where='the long east '
      'face of the office slab', desc='projecting buff limestone piers and recessed light grey-buff brick spandrels', nb=3,
      base='a three-storey base about 18 m tall of polished black granite: a tall double-height wall of large aluminium '
           'framed glass with slim stainless steel mullions, a blank band of large polished dark granite slabs above it',
      typical='limestone piers 0.4 m proud running unbroken up the face between the bays, each bay holding one group of four '
              'steel casement lights with white frames, about 3.3 m wide and 1.6 m tall, set back behind the piers, and a '
              'matte light grey-buff brick spandrel about 2.1 m tall between the window bands',
      top='the top storey with taller full-width glazing set back under a thin flat coping, the piers ending flat at the '
          'coping', topword='coping',
      colours='The limestone piers are buff grey (#c4beb2), the brick spandrels grey-buff (#b5b0a6), the base granite near '
              'black (#2e3236), the casement frames white.')
strip('psfs-north', sz(15.0, 40.0), name='the PSFS Building (Howe and Lescaze, 1932, International Style)', where='the '
      'cantilevered north end of the office slab on Market Street', desc='continuous ribbon windows and brick bands', nb=4,
      base='a three-storey base of polished black granite and a tall double-height wall of large aluminium framed glass '
           'with slim stainless steel mullions, then two storeys of light grey stone with grouped windows',
      typical='one continuous horizontal ribbon of white-framed steel casements across the whole width on every floor, and '
              'between the ribbons a continuous band of matte light grey-buff brick, no piers',
      top='the top storey of taller full-width glazing under a thin flat coping', topword='coping',
      colours='The brick bands are grey-buff (#b5b0a6), the base granite near black (#2e3236), the stone light grey '
              '(#c4beb2), the casement frames white.')
strip('psfs-spine', sz(10.0, 36.0), name='the PSFS Building (Howe and Lescaze, 1932)', where='the end face of its black '
      'service spine', desc='glazed black brick', nb=2,
      base='a three-storey base of polished black granite with a few tall dark doors',
      typical='a pair of small square punched windows with white steel frames in each bay of a flat wall of glazed black '
              'brick, a little sheen on the brick',
      top='storeys of horizontal metal louvre openings in the black brick under a flat black coping', topword='coping',
      colours='The brick is glossy near black (#1c2023), the base granite near black (#2e3236), the window frames white.')
strip('marriott', sz(12.0, 34.0), name='the Philadelphia Marriott Downtown (BLT Architects, 1995)', where='its tower face',
      desc='tinted rose-taupe precast concrete with punched windows', nb=4,
      base='a podium of precast with horizontal banding, larger paired windows between the bands and a granite-like base '
           'course with dark-framed entrance glazing',
      typical='single nearly square punched windows about 1.5 by 1.5 m with white frames and teal-tinted glass, almost '
              'flush, one a bay in an even grid on plain precast wall',
      top='a plain precast parapet with a thin moulded band', topword='parapet',
      colours='The precast is a dusky rose taupe (#a8978f), the base course paler (#b9b2aa), the frames white.')
strip('northam', sz(13.6, 40.0), name='the North American Building (1900)', where='its Broad Street front',
      desc='reddish-brown masonry', nb=4,
      base='a five-storey base: a modern two-storey storefront of grey granite piers and black-framed glass, then three '
           'storeys of channelled red-brown stone with moulded window surrounds and alternating triangular and segmental '
           'pediments over the fourth-floor windows, and a cornice band',
      typical='single punched one-over-one windows about 1.2 by 2.0 m with dark bronze frames in a plain regular grid on '
              'smooth red-brown masonry, no piers and no spandrel panels',
      top='a plain flat parapet with a thin light coping', topword='coping',
      colours='The masonry is red-brown (#8a6a5e), the base granite grey (#9c978d), the frames dark bronze.')
strip('ellington', sz(10.5, 34.0), name='the Ellington, formerly the Greenfield Building (about 1924, Chicago school)',
      where='its 15th Street face', desc='buff tan brick over a light limestone base', nb=3,
      base='a three-storey base about 14 m tall: light limestone piers framing ground-floor shopfronts and large multi-pane '
           'second-floor windows, a stone third storey and a moulded belt course',
      typical='one wide window a bay, a pair of sashes about 2.2 by 1.9 m with dark bronze frames, between continuous '
              'buff brick piers slightly proud of recessed brick spandrel panels',
      top='a top storey set off by a stone belt course, then a projecting moulded stone cornice with dentils',
      topword='cornice', colours='The brick is buff tan (#c6ae86), the limestone pale (#cfc4ae), the frames dark bronze.')


strip('oneparkway', sz(11.7, 36.0), name='One Parkway (built as the Bell Telephone headquarters, about 1970)', where='its '
      'face on Arch Street', desc='a brushed stainless steel panel skin', nb=6,
      base='a dark recessed glazed ground storey about 6 m tall behind the continuing steel fins',
      typical='flat brushed stainless steel panels with fine seams, one panel column per window, a single punched window '
              'about 0.95 by 1.9 m in each column with thin silver frames, nearly flush, the steel panel continuing below '
              'it as the spandrel; a narrow full-height darker bronze-tone stainless fin projecting between every fourth '
              'column', top='one taller top storey of closely spaced tall narrow vertical windows, two to a column, under '
              'a plain flat stainless parapet', topword='parapet',
      colours='The steel is light grey (#a9b0b3), the fins darker (#64625d), the ground storey dark (#2e3236).')
strip('fivepenn', sz(15.2, 36.0), name='Five Penn Center (about 1970)', where='its Market Street face', desc='light buff-grey '
      'stone piers and spandrels framing deep-set dark glass', nb=2,
      base='a two-storey glass curtain wall podium of clear and dark glass storefronts with dark mullions, wrapping the '
           'foot of the tower',
      typical='continuous full-height buff stone piers about 1.2 m wide every bay, between them on every floor a deep-set '
              'window wall of four lights about 1.5 m wide with dark bronze frames and dark smoky grey-bronze glass, under '
              'a buff stone spandrel band about 1.4 m tall set slightly behind the pier face',
      top='a plain light stone parapet band about one storey deep', topword='parapet',
      colours='The stone is light buff grey (#bdb4a4), the frames dark bronze (#2b2b2b), the podium dark (#3a4148).')


strip('fourpenn', sz(13.2, 34.0), name='Four Penn Center (1964)', where='its JFK Boulevard face', desc='horizontal bands of light '
      'buff stone spandrels alternating with near-continuous strip windows', nb=4,
      base='one tall glazed ground storey of storefront glass slightly recessed under a dark grey fascia band',
      typical='one continuous glazed strip per floor about 1.7 m tall, divided by light silver aluminium mullions into '
              'lights about 1.65 m wide with a heavier mullion every two lights and a thin dark head band above the glass, '
              'the glass light green tinted, alternating with a flush light buff stone spandrel band',
      top='a plain buff stone spandrel-height parapet', topword='parapet',
      colours='The stone is light buff (#cfc7b8), the mullions silver (#b9bcba), the fascia dark grey (#3b4044).')
strip('onepenn', sz(13.0, 40.0), name='One Penn Center at Suburban Station (Graham, Anderson, Probst and White, 1930, Art '
      'Deco)', where='its end face on 16th Street', desc='Indiana limestone piers with recessed carved spandrels on a '
      'polished black granite base with bronze trim', nb=2,
      base='a two-storey base of polished black granite with tall bronze-framed Art Deco windows with bronze grilles over '
           'bronze doors and rows of stylised bronze wheat ornament, a row of small carved limestone balconettes over it',
      typical='continuous limestone piers rising unbroken between vertical strips of single windows about 1.5 by 2.1 m '
              '(two lights and a transom, dark grey-bronze frames), the windows grouped two, two and three with wide piers '
              'between the groups, each window over a recessed carved limestone spandrel panel with shallow geometric '
              'Art Deco relief', top='the parapet where every pier rises past the roofline as a stepped Art Deco pinnacle, '
          'so the top reads as a row of notched teeth, with pierced lacy limestone cresting between them',
      topword='pinnacles',
      colours='The limestone is standard grey (#c8c0ae), the base granite near black (#1d1c1a), the trim bronze (#8c6e44).')
strip('wellsfargo', sz(9.6, 52.0), name='the Wells Fargo Building, the former Fidelity-Philadelphia Trust Building (Simon '
      'and Simon, 1928)', where='a wing on Broad Street', desc='smooth Indiana limestone ashlar on a rusticated base', nb=3,
      base='a five-storey base about 22 m tall: a ground storey and mezzanine of heavy rusticated ashlar with a tall '
           'round-arched opening with bronze doors and amber leaded glass, a dentil and modillion cornice, then two '
           'storeys of smooth ashlar and a bracketed belt course',
      typical='single punched one-over-one windows about 1.3 by 2.1 m with dark grey frames and thin projecting stone '
              'sills, in a regular grid on a flat smooth limestone wall, no piers',
      top='a heavy modillioned cornice, a short attic with a band of carved medallions, then a two-storey colonnade of '
          'tall paired windows between flat pilasters under a top cornice', topword='top cornice',
      colours='The limestone is light grey (#c4bfb4), the base a little darker (#aca29a), the frames dark grey (#2a2e33).')
strip('twopenn', sz(14.5, 34.0), name='Two Penn Center (1958)', where='its JFK Boulevard face', desc='white spandrel '
      'bands alternating with ribbon windows', nb=5,
      base='a tall glazed lobby storey with slim aluminium mullions recessed under a white fascia',
      typical='a continuous horizontal ribbon window on every floor between thin light aluminium mullions about 1.5 m '
              'apart, the glass blue, and between the ribbons an opaque white enamel spandrel band of about the same '
              'height, flush, no piers', top='the last white band as the parapet', topword='parapet',
      colours='The bands are off-white (#e4e0d6), the mullions light aluminium (#c9cccc).')


strip('bellevue', sz(11.0, 44.0), name='the Bellevue, the former Bellevue-Stratford Hotel (G. W. and W. D. Hewitt, 1904, French '
      'Renaissance)', where='its Broad Street front', desc='warm buff stone and brick in horizontal banded rustication',
      nb=3, base='a three-storey base of heavy channelled limestone, the ground floor with tall shop and lobby openings, '
           'the second floor a row of tall round-arched windows with carved keystones and small iron balconettes, a '
           'heavy moulded cornice over it',
      typical='walls of warm buff ashlar laid in continuous horizontal banded rustication, each bay a pair of one-over-one '
              'windows with dark frames in moulded stone surrounds, a few windows with small wrought iron balconettes',
      top='a richly carved top: a balustraded balcony course, two storeys of windows framed by carved stone cartouches, '
          'garlands and consoles, and a deep ornate modillioned cornice', topword='cornice',
      colours='The stone is warm buff (#d8cdb6), the frames dark bronze, the ironwork black.')
strip('jefftower', sz(14.0, 36.0), name='Jefferson Tower, the former Aramark Tower (Kohn Pedersen Fox, 1984)', where='its '
      'Market Street face', desc='pink-tan granite bands and dark blue-grey ribbon windows', nb=5,
      base='a two-storey base of polished pink-tan granite with tall dark glass storefronts and a recessed entrance',
      typical='a continuous horizontal ribbon of dark blue-grey reflective glass on every floor, between slim dark '
              'mullions about 1.5 m apart, and between the ribbons a band of flamed pink-tan granite about the same '
              'height; every third storey the granite band is a deep maroon granite instead',
      top='a plain granite parapet band over the last ribbon', topword='parapet',
      colours='The granite is pink tan (#b9a594), the accent bands maroon (#6e3a36), the glass dark blue grey.')


strip('archumc-tower', '704x2112', name='the Arch Street Methodist Church (1870, Gothic Revival)', where='one face of its '
      'square corner tower, below the spire', desc='pale coursed marble ashlar with carved marble trim', nb=1,
      base='a pointed-arch portal with moulded orders and a crocketed gable over it at the foot, between two angle '
           'buttresses that rise the whole height with gabled offsets; above the portal a stage with a pair of tall '
           'narrow lancet windows under hood moulds, a moulded string course, then a tall belfry stage with one large '
           'pointed opening of five slender lancet lights with simple tracery', typical=None,
      top='a band of small carved gablets over the belfry and a crenellated marble parapet, the angle buttresses ending '
          'in the bases of crocketed pinnacles at the two corners', topword='parapet',
      colours='The marble is pale grey-white (#c4c3b9), the openings dark, the louvres in the belfry dark grey.')


def jobs(only):
    out = []
    for sid, s in STRIPS.items():
        if only and sid not in only:
            continue
        prompt = (WHOLE if s.get('typical') is None else STRIP).format(**{k: v for k, v in s.items() if k != 'size'})
        out.append((sid, prompt, s['size']))
    return out


def make(key, sid, prompt, size, force):
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, sid + '.png'), os.path.join(RAW, sid + '.json')
    if os.path.exists(png) and not force:
        return sid, 'kept'
    if os.path.exists(png):   # a picture made again keeps the one it replaces beside it
        aside = os.path.join(RAW, 'aside')
        os.makedirs(aside, exist_ok=True)
        k = 1
        while os.path.exists(os.path.join(aside, '%s_v%d.png' % (sid, k))):
            k += 1
        os.replace(png, os.path.join(aside, '%s_v%d.png' % (sid, k)))
        if os.path.exists(meta):
            os.replace(meta, os.path.join(aside, '%s_v%d.json' % (sid, k)))
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = SF.call(key, SF.API, body, 'application/json')
    if not d:
        return sid, err
    SF.MODEL, SF.QUALITY = MODEL, QUALITY
    n = SF.save(png, meta, d, {'id': sid, 'prompt': prompt, 'size': size})
    return sid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    js = jobs(only)
    if a.list:
        for sid, prompt, size in js:
            print(sid, size, len(prompt))
        return
    key = SF.api_key()
    print('%d images, model %s, quality %s' % (len(js), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for sid, what in ex.map(lambda j: make(key, j[0], j[1], j[2], a.force), js):
            print(sid, what, flush=True)


if __name__ == '__main__':
    main()
