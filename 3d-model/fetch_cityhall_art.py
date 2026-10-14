#!/usr/bin/env python3
"""Generate City Hall's facades (Round 191, Mike: "I want City hall ... to be totally revamped"): one straight-on
elevation a cell (a wing section of four bays, a pavilion's front, a tower stage, a dormer), from OpenAI's image API,
written to lidar_cache/cityhall_art_raw/<id>.png with a sidecar <id>.json (the prompt, the model, the size, when, the
usage). bake_cityhall_art.py keys the glass, takes each picture's storeys to the building's own heights and packs the
stone atlas (S) and the tower's (T) the page wraps round the measured model.

Every pane of glass is asked for as a flat chroma-key green (#00FF00) and the centre pavilion's great arch as a flat
magenta (#FF00FF), so the bake finds the windows and the portal exactly (the glass is the mask the night's rooms and the
lamps read; the arch is cut out of the wall for the passage to the courtyard). No lettering anywhere: the dials are drawn
by the page, never by the model.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is
never printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
CH_ART_MODEL picks the model (default gpt-image-2), CH_ART_QUALITY the quality (default high).

Usage: python3 fetch_cityhall_art.py [--only id,...] [--force] [--list] [--workers 2]"""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'cityhall_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('CH_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('CH_ART_QUALITY', 'high')

# the marble and granite of the block and the tower's masonry (to 102.8 m)
FRAME_STONE = ('Architectural elevation photograph, perfectly orthographic and straight-on, of {what} of Philadelphia City '
               'Hall (John McArthur Jr., 1871 to 1901, French Second Empire), white Lee marble over a light grey granite '
               'base. The {part} fills the frame edge to edge: {edges}. {body} No perspective, no vanishing lines, no '
               'camera tilt, every window on a floor the same size, every floor line exactly level. Soft even overcast '
               'daylight, no cast shadows. The marble is cleaned warm white with faint grey weathering in deep recesses '
               'and under cornices; the carving crisp. Every pane of glass is one flat uniform pure green (#00FF00) with '
               'no reflections, no texture and no glazing bars drawn in the green; nothing else is that green. No people, '
               'no cars, no trees, no flags, no street furniture, no air conditioners, no signs, no lettering, no numbers, '
               'no plaques and no logos. Photorealistic, high detail, natural colours.')
# the tower's metal superstructure (the clock stage up), painted light grey since 1990
FRAME_METAL = ('Architectural elevation photograph, perfectly orthographic and straight-on, of {what} of the tower of '
               'Philadelphia City Hall (John McArthur Jr., 1871 to 1901, French Second Empire), built of cast-iron and '
               'steel plates painted one even light grey (#c8ccd1), cooler and greyer than white marble. The {part} fills '
               'the frame edge to edge: {edges}. {body} No perspective, no vanishing lines, no camera tilt, every line '
               'level. Soft even overcast daylight, no cast shadows, no sky. {key} No people, no birds, no flags, no '
               'lettering, no numerals, no numbers and no logos. Photorealistic, high detail, natural colours.')
GLASS = ('Every pane of glass is one flat uniform pure green (#00FF00) with no reflections, no texture and no glazing bars '
         'drawn in the green; nothing else is that green.')
# a tileable patch of the building's own plain marble, for the cornices' soffits, the returns and the slabs
FRAME_TILE = ('Seamless tileable wall texture for a 3D model: a perfectly orthographic, straight-on photograph of {what}, '
              'filling the whole frame evenly, the courses running exactly horizontally across the image. No windows, no '
              'doors, no corners or edges, no carving, no objects and no cast shadows. Soft even overcast daylight. '
              'Natural colours, photorealistic, uniform detail across the whole image so it repeats without a visible '
              'seam.')

# id, size, frame, what, part, edges, body. Sizes are multiples of 16 inside the model's 3:1, at least 655,360 pixels,
# at the cell's own proportions (bake_cityhall_art.py's CELLS gives each one's metres)
IMAGES = [
    ('ch_curtain', '1024x1728', 'stone', 'one section of a long wing of the outer facade', 'wing section',
     'the bottom edge is the pavement at the foot of the granite base, the top edge is the top of the main cornice (no '
     'roof, no mansard, no sky above it), and the left and right edges cut vertically through the middle of the two '
     'framing pilasters, so the section is exactly four window bays wide and repeats side by side',
     'A rusticated light grey granite basement storey fills the bottom fifth of the image, with one small square window in '
     'each bay. Above it two tall marble storeys, each split by a mezzanine: in every bay a tall window with a smaller '
     'square window above it. Fluted Corinthian pilasters stand between the bays on both storeys; every window has a '
     'moulded surround with carved consoles; the upper storey\'s tall windows carry alternating segmental and triangular '
     'pediments; a band of carved frieze runs under a deep modillioned cornice across the very top.'),
    ('ch_clock', '1024x992', 'metal', 'one face of the clock stage', 'clock stage face',
     'the bottom edge is the stone cornice the clock stage stands on, the top edge is the top of the segmental arched '
     'pediment over the clock, and the left and right edges are the outer faces of the corner columns',
     'A pair of engaged Corinthian columns on low pedestals stands at each side. Between them, set LOW in the face, a '
     'large circular clock dial: the dial\'s bottom edge is about one sixth of the image height above the bottom edge, its '
     'top edge a little above the middle of the image, and the dial is two fifths of the image width across. Its glass is '
     'a flat disc of pure green (#00FF00) with nothing drawn on it: no numerals, no hands, no marks. Round the dial a '
     'heavy moulded ring of painted metal and a small carved laurel garland under it. Over the dial the columns\' '
     'capitals carry a full entablature, and a tall segmental arched pediment with a carved cartouche fills the top of '
     'the image. Faint seams and rows of rivets between the painted plates.',
     'The clock dial\'s glass is one flat uniform pure green (#00FF00); nothing else is that green.'),
    ('ch_flank', '1024x1728', 'stone', 'the three bays beside the central entrance pavilion of the outer facade',
     'section', 'the bottom edge is the pavement at the foot of the granite base, the top edge is the top of the main '
     'cornice (no roof, no mansard, no sky above it), and the left and right edges cut vertically through the middle of the '
     'framing columns, so the section is exactly three window bays wide',
     'A rusticated light grey granite basement storey fills the bottom fifth of the image, with round-arched openings. '
     'Above it the principal storey of tall round-arched windows between pairs of engaged Corinthian columns, with small '
     'mezzanine windows over them, then the second storey of tall windows under triangular and segmental pediments with '
     'small balustraded balconettes at their sills, and over all a carved frieze and a deep modillioned cornice.'),
    ('ch_centre', '1104x1600', 'stone', 'the front of one of the four central entrance pavilions', 'pavilion front',
     'the bottom edge is the pavement, the top edge is the top of the attic cornice (no mansard roof, no sky above it), and '
     'the left and right edges are the outer faces of the pavilion\'s corner columns, so the pavilion is exactly three '
     'bays wide',
     'In the middle of the ground storey the great round-arched entrance to the courtyard, about one fifth of the width '
     'and one quarter of the height, its whole opening filled with one flat uniform pure magenta (#FF00FF) with nothing '
     'seen inside it; a sculpted keystone head over the arch. Pairs of free-standing Corinthian columns on tall pedestals '
     'frame the bays on all three storeys, the lowest on a rusticated light grey granite base. Over the entrance a large '
     'round-arched window with sculpted spandrels; above that a triple arched window flanked by seated allegorical figures; '
     'in the attic a carved panel of a coat of arms under a big segmental pediment; balustrades between the column '
     'pedestals.'),
    ('ch_corner', '832x1856', 'stone', 'one face of a corner pavilion', 'pavilion face',
     'the bottom edge is the pavement, the top edge is the top of the attic cornice (no mansard roof, no sky above it), and '
     'the left and right edges are the outer faces of the corner columns, so the face is one wide bay',
     'A rusticated light grey granite basement storey at the foot with one arched window. Above it two tall storeys, each '
     'with one large round-arched window between pairs of engaged Corinthian columns, sculpted spandrels over the arches; '
     'then a third storey with a pedimented window between short pilasters, and at the top a carved attic panel of '
     'garlands and a cartouche under the cornice.'),
    ('ch_court', '816x1600', 'stone', 'the courtyard face of a wing', 'courtyard wall',
     'the bottom edge is the paved courtyard floor at the foot of the granite base, the top edge is the top of the '
     'cornice (no roof, no sky above it), and the left and right edges cut vertically through the middle of the framing '
     'pilasters, so the section is exactly four window bays wide and repeats side by side',
     'Plainer than the outer fronts. A light grey granite basement with a small window in each bay; two marble storeys '
     'each split by a mezzanine, a tall window with a small square window above it in every bay, plain moulded surrounds '
     'and simple pilasters; a third storey of smaller windows; a simple moulded cornice at the top.'),
    # fix2 (the review: a smooth white field with two small arched windows, where every photograph shows channel-jointed
    # courses across the whole face, a great tripartite window with arched lunettes a third of the face wide and three slit
    # windows under it: Philadelphia_City_Hall_tower.jpg, the tower from the courtyard's south entrance, N Broad Street)
    ('ch_tower_low', '1024x1104', 'stone', 'one face of the square tower', 'tower face',
     'the bottom edge is where the tower face rises clear of its battered base, the top edge is the underside of the '
     'tower\'s first stone balcony, and the left and right edges are the outer corners of the tower',
     'The entire face, edge to edge and top to bottom, is channel-jointed banded marble: level courses about 0.6 metres '
     'high, about forty of them up the image, every horizontal joint a deep sunk V-shaped channel that casts a thin dark '
     'shadow line, faint staggered vertical joints between long blocks, the two corners finished as plain quoins in the '
     'same courses. No columns and no pilasters anywhere. In the lowest fifth, three tall narrow slit windows side by side '
     'close together in the middle, each about one twentieth of the face wide, deep set in plain reveals. A plain moulded '
     'string course crosses the whole face at about one third of the height. Above it, centred, one great tripartite '
     'window about one third of the face wide and nearly half the face tall: three tall rectangular lights side by side '
     'divided by plain stone mullions and one stone transom, under a semicircular arched head holding three smaller arched '
     'lights, all in a plain moulded arch of voussoirs with a keystone, on a plain stone sill. Plain banded courses above '
     'the arch to the top edge.'),
    ('ch_tower_mid', '1024x1056', 'stone', 'one face of the square tower above its first balcony', 'tower face',
     'the bottom edge is the floor of the first balcony, the top edge is the underside of the upper balcony, and the left '
     'and right edges are the outer faces of the rusticated corner piers',
     'Rusticated corner piers at both edges. Low down three tall narrow round-headed windows side by side behind a '
     'balustrade; above them one very tall round-arched window divided by stone mullions into three lights with an arched '
     'head; a frieze of carved round medallions runs across near the top under a moulded cornice.'),
    # fix2 (the review: the arch was twice the photographs' width against the stage and keyed as a black void; N Broad
    # Street and the aerial show a narrow glazed arch about an eighth of the face)
    ('ch_belvedere', '1344x832', 'stone', 'one face of the tower\'s belvedere stage under the clock', 'belvedere face',
     'the bottom edge is the floor of the upper balcony, the top edge is the top of the stage\'s carved entablature, and '
     'the left and right edges are the outer faces of the clustered corner columns',
     'Clusters of three Corinthian columns at both corners, and one pair of engaged Corinthian columns either side of the '
     'centre. In the middle one tall narrow round-arched window, about one eighth of the width wide and about two thirds '
     'of the height tall, divided by thin stone mullions into three narrow lights under an arched fanlight, a small stone '
     'balustrade across its foot. Carved garlands and small panels beside the arch head; between the columns plain marble '
     'panels with shallow arched niches; a richly carved entablature across the top.'),
    ('ch_dome', '704x1664', 'metal', 'one face of the tower\'s octagonal dome, unrolled flat', 'dome face',
     'the bottom edge is the dome\'s foot, the top edge is where the dome meets the lantern, and the left and right edges '
     'are the plain moulded ribs at the dome\'s corners',
     'Long vertical panels of horizontal louvres run up the face between the ribs. Two thirds of the way up a projecting '
     'dormer with an ornate round window in a scrolled frame, its glass flat pure green; small carved brackets and '
     'scrolls at the foot.', GLASS),
    ('ch_dormer_w', '704x1280', 'stone', 'one stone dormer on the slate mansard roof of a wing', 'dormer',
     'the dormer fills the frame: the bottom edge is the sill on the slate, the top edge is the top of its pediment, and '
     'the left and right edges are the outer faces of its side pilasters',
     'A tall window with a moulded marble surround between short pilasters on carved consoles, under a segmental '
     'pediment with a small carved shell. Dark grey slate only in the corners beside the pediment.'),
    ('ch_dormer_c', '704x1408', 'stone', 'the large sculpted dormer on the mansard of a corner pavilion', 'dormer',
     'the dormer fills the frame: the bottom edge is its sill, the top edge is the top of its sculpted crest, and the left '
     'and right edges are its outer edges',
     'A round-arched window flanked by two carved standing figures on scrolled consoles, under a sculpted cartouche '
     'crest with garlands. Dark grey slate only in the corners beside the crest.'),
    ('ch_aedicule', '832x1072', 'stone', 'the great central sculptural dormer on the mansard of an entrance pavilion',
     'dormer', 'the dormer fills the frame: the bottom edge is the attic cornice it stands on, the top edge is the top of '
     'its sculpted group, and the left and right edges are its outer edges',
     'A tall round-arched window between two standing caryatid figures carrying a broken segmental pediment, on which '
     'sits a sculpted group of figures round a cartouche. Dark grey slate only in the corners beside the group.'),
    ('ch_oculus', '768x912', 'stone', 'one round dormer window on the slate mansard', 'oculus dormer',
     'the dormer fills the frame: the bottom edge is its foot on the slate, the top edge is the top of its hood, and the '
     'left and right edges are its outer edges',
     'A round window in a carved marble frame with scrolled sides, a ball finial on top, and over it a small curved '
     'hood of green verdigris copper; dark grey slate shows only in the corners.'),
    ('ch_turret', '1024x1152', 'stone', 'the top stage of one of the round stair turrets in the courtyard, unrolled flat',
     'turret wall', 'the bottom edge is the courtyard cornice the turret rises above, the top edge is the top of its '
     'corbelled cornice where the slate cap begins, and the left and right edges are cut anywhere so the wall repeats '
     'seamlessly side by side',
     'Smooth marble ashlar in level courses with two small round-headed windows side by side, a moulded string course '
     'below them, and a corbelled cornice of carved brackets across the top. The pattern must tile horizontally without a '
     'seam.'),
    # fix2 (the review: a columned bay of three huge arched windows under a balustrade, where the photographs show a plain
    # banded half-drum: Philadelphia_City_Hall_tower.jpg, Tower_Courtyard_Philadelphia_City_Hall.jpg)
    ('ch_apse', '1024x1264', 'stone', 'the semicircular apse at the foot of the tower on the courtyard side, unrolled '
     'flat', 'apse wall', 'the bottom edge is the paved courtyard floor, the top edge is the top of its moulded cornice (no '
     'balustrade, no roof, no sky above it), and the left and right edges are where the half drum meets the tower',
     'Plain banded marble: level courses about 0.6 metres high with sunk horizontal joints across the whole width. At the '
     'bottom a light grey granite base about one fifth of the height tall, with one doorway in the exact middle, about one '
     'sixth of the width wide and one sixth of the height tall, framed by a blocky Gibbs surround of alternating large and '
     'small projecting stone blocks under a flat lintel of large wedge-shaped blocks; the doorway\'s whole opening is one '
     'flat uniform pure magenta (#FF00FF) with nothing seen inside it. A plain moulded string course over the base. Above '
     'it three tall narrow windows evenly spaced, at one sixth, one half and five sixths of the width, each about one '
     'twelfth of the width wide and a third of the height tall, each in the same blocky Gibbs surround of alternating '
     'projecting blocks with a flat block lintel. A second plain string course over them, then a plain banded band holding '
     'three small round oculus windows in moulded rings, one over each tall window, and at the very top a moulded cornice. '
     'No columns, no pilasters, no balustrade, no sculpture.'),
    # fix2 (the review: one office grid on every courtyard face, where the photographs show tall sash windows and big arched
    # windows on the principal floors: Philadelphia_-_Philadelphia_City_Hall_-_20230419181543.jpg and _181701.jpg); the
    # north face by the tower keeps ch_court
    ('ch_court_main', '816x1600', 'stone', 'the courtyard face of a wing', 'courtyard wall',
     'the bottom edge is the paved courtyard floor at the foot of the granite base, the top edge is the top of the '
     'cornice (no roof, no sky above it), and the left and right edges cut vertically through the middle of the framing '
     'pilasters, so the section is exactly three window bays wide and repeats side by side',
     'Plainer than the outer fronts but grand, the marble in level courses with sunk joints. A rusticated light grey granite '
     'basement storey at the foot, a sixth of the height, with one small square window in each bay. Above it the principal '
     'storey: in each bay one tall rectangular sash window in a moulded marble surround on a sill course, with a small '
     'square mezzanine window over it. Then the second principal storey: in each bay one large round-arched window, wide '
     'and tall, divided by a stone mullion and a transom into lights under a radial fanlight, in a moulded arched surround '
     'with a keystone, between plain pilasters. Then a third storey of smaller square-headed windows, and a moulded cornice '
     'on small modillions across the top. Level string courses between the storeys.'),
    # fix2: the back of the courtyard's south forecourt over the south passage (181701: an arched window over a columned
    # window over a pedimented door, the passage at the foot)
    ('ch_court_bay', '704x1584', 'stone', 'the narrow back wall of the small south forecourt of the courtyard', 'bay',
     'the bottom edge is the paved courtyard floor, the top edge is the top of the cornice (no roof, no sky above it), and '
     'the left and right edges are the wall\'s own corners, so the bay is one wide bay',
     'The marble in level courses with sunk joints. A light grey granite basement at the foot, a sixth of the height, with in '
     'its middle a round-arched passage opening about two fifths of the width wide whose crown is at three tenths of the '
     'height; the passage opening is one flat uniform pure magenta (#FF00FF) with nothing seen inside it. Above the '
     'basement, centred, a round-arched doorway in a moulded surround under a triangular pediment on carved consoles, a tall '
     'narrow window either side of it. Above that a tall window of three lights divided by two free-standing Ionic columns '
     'carrying a plain entablature. At the top a large round-arched window with a stone mullion, a transom and a radial '
     'fanlight in a moulded arched surround, under a moulded cornice. Level string courses between the storeys.'),
    ('ch_balustrade', '1536x512', 'stone', 'a straight run of the white marble balustrade along the tower\'s balconies',
     'balustrade', 'the bottom edge is the floor the balustrade stands on, the top edge is the top of its handrail, and the '
     'left and right edges are cut through the middle of two balusters so the run repeats seamlessly side by side',
     'Turned marble balusters evenly spaced between a moulded base rail and a moulded handrail. The gaps between the '
     'balusters, where the sky would show through, are filled with flat pure green (#00FF00).'),
]
TILES = [
    ('ch_ashlar', '1024x1024', 'the smooth white Lee marble ashlar of Philadelphia City Hall, about 4 metres across: '
     'rectangular blocks about 0.6 metres high and 1.4 metres long laid in level courses with staggered vertical joints, '
     'fine grey veining, very thin joints, soft grey weathering'),
    # fix2: the tower's channel-jointed courses for its battered base (it wore the old shaft picture's foot)
    ('ch_rustic', '1024x1024', 'the channel-jointed banded white Lee marble of the tower of Philadelphia City Hall, about 4.2 '
     'metres across: long blocks in level courses, exactly seven courses from the top of the image to the bottom, every '
     'horizontal joint a deep sunk V-shaped channel casting a thin dark shadow line, thin vertical joints staggered between '
     'the courses, warm white marble with faint grey veining and soft grey weathering'),
]


def prompt_of(img):
    cid, size, frame, what, part, edges, body = img[:7]
    if frame == 'metal':
        return FRAME_METAL.format(what=what, part=part, edges=edges, body=body, key=img[7] if len(img) > 7 else GLASS)
    return FRAME_STONE.format(what=what, part=part, edges=edges, body=body)


def jobs():
    out = [(i[0], i[1], prompt_of(i)) for i in IMAGES]
    out += [(t[0], t[1], FRAME_TILE.format(what=t[2])) for t in TILES]
    return out


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


def call(key, body):
    """One request with retries: (json, None) or (None, the error)."""
    err = None
    for attempt in range(4):
        req = urllib.request.Request(API, data=body, method='POST', headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=500) as r:
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


def make(key, cid, size, prompt, force):
    os.makedirs(RAW, exist_ok=True)
    png, meta = os.path.join(RAW, cid + '.png'), os.path.join(RAW, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = call(key, body)
    if not d:
        return cid, err
    img = base64.b64decode(d['data'][0]['b64_json'])
    with open(png + '.tmp', 'wb') as f:
        f.write(img)
    os.replace(png + '.tmp', png)
    json.dump({'id': cid, 'prompt': prompt, 'size': size, 'model': MODEL, 'quality': QUALITY, 'created': d.get('created'),
               'usage': d.get('usage')}, open(meta, 'w'), indent=1)
    return cid, 'made %d KB' % (len(img) // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    js = [j for j in jobs() if not only or j[0] in only]
    if a.list:
        for j in js:
            print(j[0], j[1])
        print(len(js), 'images')
        return
    key = api_key()
    print('%d images, model %s, quality %s' % (len(js), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for cid, what in ex.map(lambda j: make(key, j[0], j[1], j[2], a.force), js):
            print(cid, what, flush=True)


if __name__ == '__main__':
    main()
