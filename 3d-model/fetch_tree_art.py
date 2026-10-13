#!/usr/bin/env python3
"""Generate the street trees' images (Oct 12, Mike: "Can you have Open AI create more realistic looking trees? The data
for tree species already exists in the app. Can we make them look like their real life counterparts?").

One image per species look, view and season from OpenAI's image API, on a transparent background, written to
lidar_cache/tree_art_raw/<look>/<view>-<season>.png with a sidecar .json (the prompt, the model, the usage). The looks
cover the PPR inventory's commonest species (the top thirty are 70% of its 150,887 trees); bake_tree_art.py maps every
species onto a look and cuts the images into the page's atlases. Views: 'side', the whole tree from base to crown seen
level from far off, and 'top', its crown seen straight down. Seasons: summer, autumn and winter for every look, spring
for the flowering ones.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never printed. An
image already on disk is kept; --force makes it again, --only <look>[,<look>] or --view / --season narrow the run.
TREES_MODEL (default gpt-image-2) and TREES_QUALITY (default medium: a tree is a few hundred pixels on screen)."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'tree_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('TREES_MODEL', 'gpt-image-1.5')   # gpt-image-2 refuses a transparent background on this account
QUALITY = os.environ.get('TREES_QUALITY', 'medium')
SIZE = '1024x1024'

SIDE = ('Botanical reference photograph of ONE mature {what} street tree as it grows in Philadelphia, {season}. Seen '
        'straight from the side at eye level from far away, so there is no perspective distortion: the whole tree from the '
        'base of the trunk at the bottom centre of the frame to the top of the crown near the top, nothing cut off. '
        '{habit} The tree stands alone on a fully transparent background: no ground, no grass, no tree pit, no shadow, '
        'no sky, no other trees, no buildings, no people, no text. Soft natural daylight from the upper left. '
        'Photorealistic, true to the species\' real leaves, bark and branching.')
TOP = ('Aerial photograph of the crown of ONE mature {what} street tree in Philadelphia, {season}, taken from high '
       'above by a drone looking straight down, as a crown looks in an aerial map: the whole crown centred and filling '
       'about nine tenths of the frame, its outline irregular and lobed as real crowns are. At this height single leaves '
       'are far too small to see: the crown reads as clumps of foliage with sunlit tops and shaded gaps between them, '
       'and the trunk is hidden under the canopy. {habit} The crown floats on a fully transparent background: no '
       'ground, no sidewalk, no shadow, no other trees, no text. Soft natural daylight from the upper left. '
       'Photorealistic.')

SUMMER = 'in full summer leaf'
WINTER = ('in winter with no leaves at all, only its bare branches and twigs showing the species\' own branching; the '
          'twigs are dark grey-brown and every gap between them is fully transparent, with no white or grey haze, mist, '
          'frost or glow round the crown')
# (look, species as the prompt names it, its habit, its autumn, its spring or None)
LOOKS = [
    ('plane', 'London planetree (Platanus x acerifolia)', 'A broad, rounded spreading crown on a tall trunk with '
     'peeling camouflage bark in cream, olive and grey patches; big maple-like leaves.', 'in autumn, its leaves turned '
     'tawny yellow and light brown', None),
    ('redmaple', 'red maple (Acer rubrum)', 'An oval to rounded crown on a smooth grey trunk; three-lobed leaves.',
     'at peak autumn colour, its whole crown brilliant scarlet and orange-red', None),
    ('sugarmaple', 'sugar maple (Acer saccharum)', 'A dense, rounded oval crown on a stout grey trunk; five-lobed '
     'leaves.', 'at peak autumn colour, its crown glowing orange and golden yellow', None),
    ('cherry', 'Kwanzan flowering cherry (Prunus serrulata)', 'A small vase-shaped tree with spreading upright '
     'branches and shiny reddish-brown bark with horizontal lenticels.', 'in autumn, its leaves bronze, orange and '
     'yellow', 'in full spring bloom, covered in clusters of deep pink double blossoms'),
    ('pear', 'Callery pear (Pyrus calleryana)', 'A dense upright oval to teardrop crown with many steep branches; '
     'glossy leaves.', 'in late autumn, its glossy leaves deep burgundy, red and purple', 'in full spring bloom, '
     'covered in masses of small white blossoms'),
    ('locust', 'thornless honeylocust (Gleditsia triacanthos inermis)', 'A light, open, airy spreading crown of '
     'fine feathery compound leaves that lets the light through, on a dark trunk.', 'in autumn, its fine leaflets '
     'golden yellow', None),
    ('redoak', 'northern red oak (Quercus rubra)', 'A broad, rounded, heavy crown on a massive trunk with ridged '
     'dark bark; pointed lobed leaves.', 'in autumn, its leaves russet red and brown', None),
    ('pinoak', 'pin oak (Quercus palustris)', 'A pyramidal crown on a straight central trunk, the upper branches '
     'rising, the middle ones level and the lower ones drooping; deeply cut pointed leaves.', 'in autumn, its leaves '
     'bronze-red and russet', None),
    ('zelkova', 'Japanese zelkova (Zelkova serrata)', 'A graceful vase-shaped crown from many upright branches '
     'fanning out from a short trunk; small serrated leaves.', 'in autumn, its leaves rusty orange, red and yellow',
     None),
    ('ginkgo', 'ginkgo (Ginkgo biloba)', 'A tall, upright, open crown with sparse ascending branches; fan-shaped '
     'leaves.', 'at peak autumn colour, its whole crown a uniform brilliant butter yellow', None),
    ('lilac', 'Japanese tree lilac (Syringa reticulata)', 'A small rounded tree with a short trunk and shiny '
     'cherry-like reddish bark.', 'in autumn, its leaves yellow-green and pale yellow', 'in early summer bloom, '
     'covered in large creamy white flower plumes'),
    ('redbud', 'eastern redbud (Cercis canadensis)', 'A small tree with a spreading flat-topped crown and a few '
     'zig-zag branches; heart-shaped leaves.', 'in autumn, its heart-shaped leaves yellow', 'in early spring bloom, '
     'its bare branches covered in tiny magenta-pink flowers, before the leaves'),
    ('crabapple', 'flowering crabapple (Malus)', 'A small, rounded, dense, spreading tree with a short trunk.',
     'in autumn, its leaves yellow and orange with small red fruit', 'in full spring bloom, covered in pink and '
     'white blossoms'),
    ('linden', 'littleleaf linden (Tilia cordata)', 'A dense, neat pyramidal to oval crown on a straight trunk; '
     'small heart-shaped leaves.', 'in autumn, its leaves yellow', None),
    ('sweetgum', 'sweetgum (Liquidambar styraciflua)', 'A tall pyramidal crown on a straight trunk; star-shaped '
     'leaves.', 'at peak autumn colour, its star-shaped leaves a mix of purple, crimson, orange and yellow', None),
    ('pine', 'eastern white pine (Pinus strobus)', 'A conifer with a soft, irregular pyramidal crown of long '
     'blue-green needles in layered horizontal branches.', None, None),
    ('elm', 'American elm (Ulmus americana)', 'A tall, wide vase-shaped crown, the limbs arching out and the twigs '
     'drooping at the tips.', 'in autumn, its leaves yellow', None),
    ('broadleaf', 'mixed-species shade tree, a typical young urban hardwood', 'A rounded, slightly irregular crown '
     'on a straight grey trunk.', 'in autumn, its leaves a mix of yellow, orange and green', None),
    # Round 184: ten more looks, so the inventory's next species stop borrowing a neighbour's
    ('magnolia', 'saucer magnolia (Magnolia x soulangeana)', 'A low, spreading, multi-stemmed tree with smooth grey bark and '
     'large leathery leaves.', 'in autumn, its leaves dull yellow and brown', 'in early spring bloom, its bare branches '
     'covered in large pink-and-white goblet-shaped flowers'),
    ('dogwood', 'flowering dogwood (Cornus florida)', 'A small tree with a flat-topped, layered crown of horizontal branches.',
     'at peak autumn colour, its leaves deep red and purple with red berries', 'in spring bloom, its layered branches '
     'covered in white four-petalled flowers'),
    ('serviceberry', 'serviceberry (Amelanchier)', 'A small, upright, multi-stemmed tree with smooth grey bark.',
     'at peak autumn colour, its leaves orange and red', 'in early spring bloom, covered in clouds of small white flowers'),
    ('silvermaple', 'silver maple (Acer saccharinum)', 'A large, fast-growing tree with a broad, irregular, open crown and '
     'deeply cut leaves whose silvery undersides show.', 'in autumn, its leaves pale yellow', None),
    ('crimsonking', "'Crimson King' Norway maple (Acer platanoides)", 'A dense, rounded crown of large leaves that are deep '
     'maroon-purple all summer.', 'in autumn, its leaves dark bronze and brown', None),
    ('sycamore', 'American sycamore (Platanus occidentalis)', 'A very large tree with an open, wide crown and striking white '
     'peeling upper bark on the branches; big broad leaves.', 'in autumn, its leaves dull brown and tan', None),
    ('riverbirch', 'river birch (Betula nigra)', 'A graceful multi-stemmed tree with peeling salmon-pink and cream bark and a '
     'light oval crown of small leaves.', 'in autumn, its leaves clear yellow', None),
    ('willow', 'weeping willow (Salix babylonica)', 'A broad tree with long weeping branches that hang down like curtains of '
     'narrow leaves.', 'in autumn, its hanging leaves yellow', None),
    ('spruce', 'Colorado blue spruce (Picea pungens)', 'A conifer with a dense, symmetrical, narrow pyramidal shape of '
     'stiff silvery blue-green needles all the way to the ground.', None, None),
    ('holly', 'American holly (Ilex opaca)', 'A broad pyramidal evergreen of dense, spiny, dark glossy green leaves with '
     'scattered red berries.', None, None),
]


# the realism pass: a turning stage between summer and autumn (a city's trees colour a fifth at a time, not all at once), in
# the hue each look turns
TURNING = ('in early autumn as the colour is just starting: the crown is still mostly {base}, with about a fifth of the leaves '
           'turned {hue}, scattered on the outer branches and at the top, the rest {rest}; natural, slightly muted colour')
TURN_HUE = {
    'plane': 'yellow-brown', 'redmaple': 'scarlet', 'sugarmaple': 'orange and gold', 'cherry': 'bronze and orange',
    'pear': 'burgundy and red', 'locust': 'yellow', 'redoak': 'russet', 'pinoak': 'bronze', 'zelkova': 'rusty orange',
    'ginkgo': 'butter yellow', 'lilac': 'pale yellow', 'redbud': 'yellow', 'crabapple': 'yellow and orange',
    'linden': 'yellow', 'sweetgum': 'purple and crimson', 'elm': 'yellow', 'broadleaf': 'yellow and orange',
    'magnolia': 'dull yellow', 'dogwood': 'deep red', 'serviceberry': 'orange and red', 'silvermaple': 'pale yellow',
    'crimsonking': 'dark bronze', 'sycamore': 'tan and brown', 'riverbirch': 'yellow', 'willow': 'yellow',
}


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


def jobs_for(look):
    lid, what, habit, autumn, spring = look
    # a flowering look's summer is after its bloom (the tree lilac's first summer image came out in flower)
    seasons = [('summer', SUMMER + (', after flowering, with no flowers or seed heads at all' if spring else ''))]
    if autumn:
        seasons += [('autumn', autumn), ('winter', WINTER)]
        if lid in TURN_HUE:
            base, rest = ('deep maroon-purple', 'maroon') if lid == 'crimsonking' else ('summer green', 'green')
            seasons.append(('turning', TURNING.format(base=base, hue=TURN_HUE[lid], rest=rest)))
    if spring:
        seasons.append(('spring', spring))
    out = []
    for sname, sdesc in seasons:
        for view, frame in (('side', SIDE), ('top', TOP)):
            out.append((lid, view, sname, frame.format(what=what, season=sdesc, habit=habit)))
    return out


def make(key, lid, view, season, prompt, force):
    d = os.path.join(RAW, lid)
    os.makedirs(d, exist_ok=True)
    base = os.path.join(d, '%s-%s' % (view, season))
    if os.path.exists(base + '.png') and not force:
        return base, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': SIZE, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'transparent'}).encode()
    err = ''
    for attempt in range(4):
        req = urllib.request.Request(API, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                j = json.load(r)
            img = base64.b64decode(j['data'][0]['b64_json'])
            with open(base + '.png.tmp', 'wb') as f:
                f.write(img)
            os.replace(base + '.png.tmp', base + '.png')
            json.dump({'look': lid, 'view': view, 'season': season, 'prompt': prompt, 'model': MODEL, 'size': SIZE,
                       'quality': QUALITY, 'created': j.get('created'), 'usage': j.get('usage')},
                      open(base + '.json', 'w'), indent=1)
            return base, 'made %d KB, %s output tokens' % (len(img) // 1024, (j.get('usage') or {}).get('output_tokens'))
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (400, 401, 403):
                return base, 'refused %d: %s' % (e.code, msg)
            err = '%d %s' % (e.code, msg)
        except Exception as e:
            err = str(e)[:300]
        time.sleep(5 + 10 * attempt)
    return base, 'failed: ' + err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--view', default='')
    ap.add_argument('--season', default='')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    key = api_key()
    only = set(filter(None, a.only.split(',')))
    jobs = [j for lk in LOOKS if not only or lk[0] in only for j in jobs_for(lk)]
    jobs = [j for j in jobs if (not a.view or j[1] == a.view) and (not a.season or j[2] == a.season)]
    print('%d images, model %s, %s, quality %s' % (len(jobs), MODEL, SIZE, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for base, what in ex.map(lambda j: make(key, j[0], j[1], j[2], j[3], a.force), jobs):
            print(os.path.relpath(base, RAW), what, flush=True)


if __name__ == '__main__':
    main()
