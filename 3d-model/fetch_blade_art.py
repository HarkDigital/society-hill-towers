#!/usr/bin/env python3
"""Generate the blade signs' blanks (the realism round two, R9: Round 189's open item, "blade signs for the 796 on street
floors"): six projecting shop signs on their brackets, each a straight-on elevation with the wall side at the left edge,
from OpenAI's image API on a transparent background, into lidar_cache/blade_art_raw/<id>.png with a sidecar .json (the
prompt, the model, the size, when, the usage). bake_blade_art.py trims them, finds each face's plate and packs the page's
one 512 square sheet.

Every blank is blank: no lettering, no logo, no wall. The page writes the shop's own OSM name on the plate itself (never
the image model: Rounds 92, 189 and 217).

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is
never printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
BLADE_ART_MODEL picks the model (default gpt-image-1.5, which takes a transparent background on this account),
BLADE_ART_QUALITY the quality (default high).

Usage: python3 fetch_blade_art.py [--only id,...] [--force] [--list] [--workers 3]"""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'blade_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('BLADE_ART_MODEL', 'gpt-image-1.5')
QUALITY = os.environ.get('BLADE_ART_QUALITY', 'high')

FRAME = ('Orthographic elevation photograph of {what}, seen exactly side-on and square to the sign face with no perspective, '
         'no foreshortening and no tilt. The bracket\'s wall plate stands at the far left edge of the frame (where the sign '
         'meets the building, which is not shown) and the sign projects to the right from it. The whole sign and its bracket '
         'fill the frame with a small even margin. The sign face is completely blank and evenly painted: no text, no '
         'lettering, no letters, no numbers, no logo, no symbol, no picture. Isolated on a fully transparent background: no '
         'wall, no building, no brick, no window, no sky, no shadow. Soft even overcast daylight, natural colours, a little '
         'honest weathering, photorealistic product photograph.')
# id, what, size (every one square: the sheet holds each at 70 to 200 px, and a square costs the least): the six shapes the page deals (round, rectangular, a hanging board on a scroll bracket, a projecting
# box, a tall vertical, a small oval)
BLADES = [
    ('round', 'a round double-sided shop blade sign about 80 cm across: a flat circular disc of painted sheet metal in deep '
     'bottle green with a raised gold-painted rim, hung by two short rings under a slim straight black wrought-iron bracket '
     'arm with a small scroll under it, the arm fixed to a small square wall plate at the left', '1024x1024'),
    ('rect', 'a rectangular double-sided wooden shop blade sign about 110 cm wide and 70 cm tall, landscape: a flat board '
     'painted warm cream with a thin dark brown moulded border, fixed at its left edge to a black steel wall bracket with '
     'two short horizontal arms, top and bottom', '1024x1024'),
    ('hanging', 'a traditional hanging shop sign: a flat rectangular double-sided painted board about 90 cm wide and 60 cm '
     'tall in dark oxblood red with a thin gold line border, hanging from two short black chains under an ornate black '
     'wrought-iron scroll bracket; the bracket\'s straight arm runs horizontally from a wall plate at the left, curling '
     'scrollwork under the arm, the board hanging below the arm', '1024x1024'),
    ('box', 'a modern projecting lightbox blade sign: a shallow rectangular sign cabinet about 120 cm wide and 55 cm tall, '
     'landscape, with a satin black aluminium frame round a plain flat white translucent acrylic face, held off a wall '
     'plate at the left by a short square black steel bracket', '1024x1024'),
    ('vertical', 'a tall narrow vertical projecting blade sign for a theatre or a bar, a flat double-sided metal panel about '
     '60 cm wide and 220 cm tall, portrait, painted deep navy blue with a thin cream border line, fixed to a tall wall plate '
     'at the left by three short black steel brackets at its top, middle and foot', '1024x1024'),
    ('oval', 'a small oval double-sided shop blade sign about 70 cm wide and 45 cm tall: a flat oval board painted charcoal '
     'black with a thin gold rim, hung from a slim curved black wrought-iron bracket arm fixed to a small wall plate at the '
     'left', '1024x1024'),
]


def jobs():
    return [(bid, FRAME.format(what=what), size) for bid, what, size in BLADES]


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


def make(key, bid, prompt, size, force):
    os.makedirs(RAW, exist_ok=True)
    base = os.path.join(RAW, bid)
    if os.path.exists(base + '.png') and not force:
        return bid, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1, 'output_format': 'png',
                       'background': 'transparent'}).encode()
    err = ''
    for attempt in range(3):
        req = urllib.request.Request(API, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=400) as r:
                j = json.load(r)
            img = base64.b64decode(j['data'][0]['b64_json'])
            if os.path.exists(base + '.png'):   # --force: the image it replaces is kept aside, never lost
                os.replace(base + '.png', base + '.prev-%d.png' % int(time.time()))
            with open(base + '.png.tmp', 'wb') as f:
                f.write(img)
            os.replace(base + '.png.tmp', base + '.png')
            json.dump({'id': bid, 'prompt': prompt, 'model': MODEL, 'size': size, 'quality': QUALITY, 'transparent': True,
                       'created': j.get('created'), 'usage': j.get('usage')}, open(base + '.json', 'w'), indent=1)
            return bid, 'made %d KB' % (len(img) // 1024)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (400, 401, 403, 429):
                return bid, 'refused %d: %s' % (e.code, msg)
            err = '%d %s' % (e.code, msg)
        except Exception as e:
            err = str(e)[:300]
        time.sleep(5 + 10 * attempt)
    return bid, 'failed: ' + err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    todo = [j for j in jobs() if not only or j[0] in only]
    if a.list:
        for bid, prompt, size in todo:
            print(bid, size, 'on disk' if os.path.exists(os.path.join(RAW, bid + '.png')) else 'to make')
        return
    key = api_key()
    print('%d images, model %s, quality %s' % (len(todo), MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for bid, what in ex.map(lambda j: make(key, j[0], j[1], j[2], a.force), todo):
            print(bid, what, flush=True)


if __name__ == '__main__':
    main()
