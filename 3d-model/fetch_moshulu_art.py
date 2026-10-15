#!/usr/bin/env python3
"""Generate the Moshulu's textures (Round 195, Mike: "Remodel ... The Moshulu"): square-on photographs from OpenAI's image API
of her riveted hull plating and her teak deck, into lidar_cache/moshulu_art_raw/<id>.png with a sidecar .json.
bake_moshulu_art.py makes them tile, derives each one's relief and writes moshulu_art.json.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never printed. An image
already on disk is kept; --force makes it again, --only <id>[,<id>] makes some."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'moshulu_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('MOSHULU_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('MOSHULU_QUALITY', 'high')
SIZE = '1024x1024'

FRAME = ('Seamless tileable texture for a 3D city model: a photograph taken square-on to {what}, filling the whole frame '
         'evenly. No perspective, no horizon, no shadows of objects, no people, no objects, no edges or borders, no text, no '
         'lettering, no logos. Soft even overcast daylight. Natural colours, photorealistic, uniform detail across the whole '
         'image so it repeats without a visible seam.')
ARTS = [
    # the hull (refs: Commons 20240529, the 2017 restaurant photographs): riveted plating painted a deep navy blue. The page
    # divides the mean out and paints the calibrated blue and the red bottom through it, so the plates, rivets and
    # weathering are what this brings
    ('hull', 'the side of the steel hull of an old four-masted sailing ship built in 1904, about four metres across: '
     'overlapping riveted steel plates in horizontal strakes about one metre tall with vertical butt joints, neat rows of '
     'round rivet heads along every seam, the whole surface painted a deep navy blue in thick gloss marine paint, gently '
     'weathered, faint thin rust streaks below a few rivets, brush marks and a few small paint touch-ups, no portholes, no '
     'windows, no water'),
    # the decks (refs: the 2017 restaurant photographs, the poop and the forecastle): weathered teak planking
    ('deck', 'the weathered teak deck of an old sailing ship seen from straight above, about three metres across: long '
     'straight teak planks about fifteen centimetres wide running left to right across the whole frame, black pitch-caulked '
     'seams between the planks, staggered butt joints, small round wooden plugs over the fastenings, the wood weathered to '
     'a warm grey-brown with darker oiled patches'),
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
