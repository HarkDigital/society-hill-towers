#!/usr/bin/env python3
"""Generate the ground's textures (Oct 12, Mike: "If you could also update the grass/ground textures that would be great"):
straight-down photographs of a patch of ground about 6.5 m across, from OpenAI's image API, into
lidar_cache/ground_art_raw/<id>.png with a sidecar .json. bake_ground_art.py makes them tile and writes ground_art.json.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never printed. An image
already on disk is kept; --force makes it again, --only <id>[,<id>] makes some."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'ground_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('GROUND_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('GROUND_QUALITY', 'high')
SIZE = '1024x1024'

FRAME = ('Seamless tileable ground texture for a 3D city model: a photograph taken looking straight down from about '
         'ten metres up at {what}, a patch about six and a half metres across filling the whole frame evenly. No '
         'horizon, no perspective, no shadows of objects, no trees, no paths, no people, no objects, no edges or borders. '
         'Soft even overcast daylight. Natural colours, photorealistic, uniform detail across the whole image so it '
         'repeats without a visible seam.')
GROUNDS = [
    ('lawn', 'a mown park lawn in a Philadelphia city park in summer: dense green turf grass with slight variation in '
     'tone, a few clover patches'),
    ('meadow', 'a rougher, less tended urban grass verge in late summer: grass of mixed greens and straw-dry blades, '
     'clover, a few dandelion leaves and small patches of bare brown soil showing through'),
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
    jobs = [g for g in GROUNDS if not only or g[0] in only]
    with concurrent.futures.ThreadPoolExecutor(2) as ex:
        for gid, what in ex.map(lambda g: make(key, g[0], g[1], a.force), jobs):
            print(gid, what, flush=True)


if __name__ == '__main__':
    main()
