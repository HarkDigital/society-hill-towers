#!/usr/bin/env python3
"""Generate the streets' own textures (Oct 12, Mike: "please do anything necessary to make this look more photo realistic
and less cartoony ... all surfaces"): straight-down photographs of one traffic lane's wear, the weathered concrete side of
an elevated highway, the El's riveted steel and a main line's ties and ballast, from OpenAI's image API, into
lidar_cache/street_art_raw/<id>.png with a sidecar .json. bake_street_art.py makes them tile and writes street_art.json.

The ground's textures (fetch_ground_art.py, ground_art.json) stay apart: these are the streets' own, in their own
manifest. The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never
printed. An image already on disk is kept; --force makes it again, --only <id>[,<id>] makes some."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'street_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('STREET_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('STREET_QUALITY', 'high')

# one lane, its length running down the image (the page samples it across the lane and along the road)
LANE = ('Seamless tileable texture for a 3D city model: an orthographic photograph looking straight down at ONE traffic '
        'lane of an old Philadelphia city street, the lane running vertically from the top edge to the bottom edge and '
        'filling the frame from the left edge to the right edge, about 3.6 metres across and 14 metres long. {what} No '
        'paint markings, no kerb, no manholes, no objects, no shadows of objects, no perspective. Soft even overcast '
        'daylight, natural colours, photorealistic. The top and bottom edges must match so it repeats vertically without '
        'a seam.')
WALL = ('Seamless tileable texture for a 3D city model: a straight-on photograph of {what} No perspective, no text, no '
        'graffiti, no objects, no edges or borders. Soft even overcast daylight, natural colours, photorealistic, uniform '
        'detail across the whole image so it repeats without a visible seam.')
ARTS = [
    ('lanewear_a', 'Weathered dark grey asphalt with fine aggregate; a darker oily drip stain band running down the centre '
     'of the lane; two slightly lighter, smoother tyre-polished wheel paths either side of it; a few black tar-sealed '
     'crack lines, mostly running lengthwise; one rectangular patch of newer, darker asphalt from a utility repair; two '
     'small cold-patched potholes.', LANE, '1024x1536'),
    ('lanewear_b', 'Old grey asphalt, sun-faded, with fine exposed aggregate; a faint darker oil drip band down the middle '
     'of the lane; two smoother, slightly polished wheel paths; long thin black tar-sealed cracks running lengthwise and '
     'a few short transverse ones; a narrow strip of newer asphalt across the lane where a trench was filled.', LANE,
     '1024x1536'),
    ('lanewear_c', 'Worn asphalt of a city street in mid tone grey with darker blotches; an oil drip band down the centre '
     'of the lane; polished wheel paths; a network of tar-sealed cracks; a rectangular darker asphalt patch near one '
     'edge and a small round cold patch.', LANE, '1024x1536'),
    ('concrete_wall', 'the weathered vertical concrete side of an elevated highway in Philadelphia, about four metres '
     'across: board-formed grey concrete with faint horizontal form lines, dark vertical water and rust streaks running '
     'down from the top edge, pale efflorescence stains, a few patched spalls.', WALL, '1024x1024'),
    ('el_steel', 'the riveted steel plate girder of an old elevated railway in Philadelphia, about three metres across: '
     'dark grey-green paint, rows of round rivet heads along the flanges and stiffeners, orange rust bleeding down from '
     'the rivets and the lower flange, weathered and grimy.', WALL, '1024x1024'),
    ('ballast_ties', None, ('Seamless tileable texture for a 3D city model: an orthographic photograph looking straight '
     'down at a single railway track of a busy American main line, the track running vertically from top edge to bottom '
     'edge, the ballast shoulder filling the frame edge to edge horizontally (about 3.4 metres across, 5 metres long): '
     'grey concrete ties at regular 0.6 metre spacing running horizontally across the frame on crushed grey granite '
     'ballast, two steel rails with polished tops and rust-brown sides running vertically, brown rust and oil staining '
     'between the rails, a few weeds at the edges. No overhead wires, no objects, no shadows of objects, no perspective, '
     'soft even overcast daylight, photorealistic, the top and bottom edges match so it repeats vertically without a '
     'seam.'), '1024x1536'),
    ('lot_asphalt', None, ('Seamless tileable texture for a 3D city model: an orthographic photograph looking straight '
     'down at the weathered asphalt of a city parking lot in Philadelphia, about six metres across: grey asphalt with '
     'fine aggregate, dark oil stains in the middle of where cars park, tar-sealed cracks, a little grit. No paint '
     'markings, no cars, no objects, no shadows of objects, no perspective, no edges or borders. Soft even overcast '
     'daylight, natural colours, photorealistic, uniform detail so it repeats without a visible seam.'), '1024x1024'),
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


def make(key, gid, prompt, size, force):
    os.makedirs(RAW, exist_ok=True)
    base = os.path.join(RAW, gid)
    if os.path.exists(base + '.png') and not force:
        return gid, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
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
            json.dump({'id': gid, 'prompt': prompt, 'model': MODEL, 'size': size, 'quality': QUALITY,
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
    jobs = []
    for gid, what, frame, size in ARTS:
        if only and gid not in only:
            continue
        jobs.append((gid, frame.format(what=what) if what else frame, size))
    with concurrent.futures.ThreadPoolExecutor(3) as ex:
        for gid, res in ex.map(lambda j: make(key, j[0], j[1], j[2], a.force), jobs):
            print(gid, res, flush=True)


if __name__ == '__main__':
    main()
