#!/usr/bin/env python3
"""Generate the water's textures (Oct 12, the realism pass, Mike: "make this look more photo realistic and less cartoony.
This should apply to all surfaces/water/anything"): straight-down photographs from OpenAI's image API of a pier's deck and of
white water, into lidar_cache/water_art_raw/<id>.png with a sidecar .json. bake_water_art.py makes them tile and writes
water_art.json.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never printed. An image
already on disk is kept; --force makes it again, --only <id>[,<id>] makes some."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'water_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('WATER_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('WATER_QUALITY', 'high')
SIZE = '1024x1024'

FRAME = ('Seamless tileable texture for a 3D city model: a photograph taken looking straight down at {what}, filling the '
         'whole frame evenly. No perspective, no horizon, no shadows of objects, no people, no boats, no objects, no edges or '
         'borders. Soft even overcast daylight. Natural colours, photorealistic, uniform detail across the whole image so it '
         'repeats without a visible seam.')
ARTS = [
    # the piers' decks (water#6): the Delaware's old piers are concrete decks on timber and concrete piles
    ('pierdeck', 'the weathered concrete deck of an old pier on the Delaware River waterfront in Philadelphia, about six '
     'metres across: pale grey concrete slabs with straight expansion joints, dark tar-filled cracks, rust stains, '
     'a few darker patched areas and faint tyre marks, no paint markings'),
    # white water (water#8, water#10): the Fairmount Dam's apron and the ships' wakes
    ('foam', 'churning white water foam on a brown-green river just below a low weir, about six metres across: white foam '
     'streaks, lacy bubble rafts and thin foam lines over dark olive water, evenly spread across the frame'),
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


def make(key, gid, what, force):
    os.makedirs(RAW, exist_ok=True)
    base = os.path.join(RAW, gid)
    if os.path.exists(base + '.png') and not force:
        return gid, 'kept'
    prompt = FRAME.format(what=what)
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': SIZE, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png'}).encode()
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
            json.dump({'id': gid, 'prompt': prompt, 'model': MODEL, 'size': SIZE, 'quality': QUALITY,
                       'created': j.get('created'), 'usage': j.get('usage')}, open(base + '.json', 'w'), indent=1)
            return gid, 'made %d KB' % (len(img) // 1024)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (400, 401, 403):
                return gid, 'refused %d: %s' % (e.code, msg)
            err = '%d %s' % (e.code, msg)
        except Exception as e:
            err = str(e)[:300]
        time.sleep(5 + 10 * attempt)
    return gid, 'failed: ' + err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    key = api_key()
    only = set(filter(None, a.only.split(',')))
    jobs = [g for g in ARTS if not only or g[0] in only]
    with concurrent.futures.ThreadPoolExecutor(2) as ex:
        for gid, what in ex.map(lambda g: make(key, g[0], g[1], a.force), jobs):
            print(gid, what, flush=True)


if __name__ == '__main__':
    main()
