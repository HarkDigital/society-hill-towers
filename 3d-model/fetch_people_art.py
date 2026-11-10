#!/usr/bin/env python3
"""Generate the walking people's character sheets (Round 227, Mike: "people on the sidewalks, walking").

One sheet a figure from OpenAI's image API on a transparent background: six full-body pictures of the SAME person in one
row, so the views match one another, in the order POSES gives (front, back and side, each at the two moments of a walk
that make a two-frame step: the contact, legs apart, and the passing, legs together). Written to
lidar_cache/people_art_raw/<id>.png with a sidecar .json (the prompt, the model, the size, the usage).
bake_people_art.py cuts every sheet into its six poses and packs the page's atlases.

A figure is one record of FIGURES: its id, one line saying who it is and what it wears, its height in metres and its
wardrobe's season. The full set is more records, nothing else: the three here are the test the proposal's verifiers
asked to see walking before the rest is made.

No lettering, no logo, no brand, no uniform and nobody in particular: the figures are ordinary and generic, seen from
4 m at the nearest. Every sheet is looked at before it is kept (six whole figures, one person, one scale, a true
profile, no ground or shadow); a reject is made again with --force, which keeps the picture it replaces beside it.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never printed.
PEOPLE_ART_RAW moves the raw folder (a worktree has no lidar_cache of its own), PEOPLE_ART_MODEL picks the model
(default gpt-image-1.5, which takes a transparent background on this account; gpt-image-2 refuses one) and
PEOPLE_ART_QUALITY the quality (default high, as the blade signs). Medium was tried first, eight sheets of it: the six
pictures did not hold one person (a knitted cap turned into a peaked cap in the profiles, a man bald from the front had
a full head of hair from behind, a woman grew a beard, a backpack went missing in one profile) and the figures read as
game characters. The first three sheets at high were all kept.

What the prompt had to learn, sheet by sheet (keep these when the wording changes):
- "legs together" is not enough for the second frame of a view: the profile came back as a second stride until the
  prompt called it the PASSING position, said it is NOT a stride, and described the one narrow column the legs make;
- a hat, glasses and a beard are where the six pictures drift apart: describe hair plainly and leave the rest off;
- the model cannot keep a shoulder bag on one shoulder from the front and from behind. A picture that came out
  left-for-right is mirrored in the bake (bake_people_art.py's FLIP) rather than asked for again;
- the figures stand about 480 to 560 px tall in the 1024: enough for the sharp atlas's 512 px cell and no more.

Usage: python3 fetch_people_art.py [--only id,...] [--force] [--list] [--workers 3]"""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('PEOPLE_ART_RAW') or os.path.join(HERE, 'lidar_cache', 'people_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('PEOPLE_ART_MODEL', 'gpt-image-1.5')
QUALITY = os.environ.get('PEOPLE_ART_QUALITY', 'high')
SIZE = '1536x1024'   # six figures in one row: each about 250 px wide and 480 to 560 tall

# the sheet's six pictures, left to right: (view, frame). bake_people_art.py reads this order.
POSES = [('front', 0), ('front', 1), ('back', 0), ('back', 1), ('side', 0), ('side', 1)]

SHEET = ('A sheet of six cut-out photographs of the SAME real person, of the kind architects place in their renderings: '
         '{who}. A real adult\'s proportions: the head is small, about one seventh of the full height, and the legs are '
         'half of it; never stocky, never big-headed, never a doll or a cartoon. The six pictures stand in ONE horizontal '
         'row on a fully transparent background, evenly spaced, with a clear empty gap between each figure and the next '
         'so that no figure touches or overlaps another. All six are at exactly the same scale, the heads level with one '
         'another and the shoes level with one another, and each figure is whole from the top of the head to the soles of '
         'the shoes with nothing cut off. The same face, the same hair, the same clothes and the same bag in all six, and '
         'left and right stay true: what is on the person\'s own right side in the front view is on their own right side '
         'from behind too, so it appears on the other side of the picture. From left to right: '
         '(1) seen from the FRONT, walking briskly straight toward the camera, caught in mid stride: one leg swung well '
         'forward with its knee bent and its foot lifted clear in front, the other leg straight and trailing behind, the '
         'two feet plainly apart, one arm swung forward and the other back; '
         '(2) seen from the FRONT, facing the camera, in the PASSING position of the walk, which is NOT a stride: upright '
         'and at full height, the two legs together and straight, both feet side by side under the body, and both arms '
         'hanging close to the sides; '
         '(3) seen from directly BEHIND, walking briskly straight away from the camera, caught in mid stride: one leg '
         'trailing behind with its heel lifted so the sole of that shoe shows, the other leg forward, the two feet plainly '
         'apart, one arm swung forward and the other back; '
         '(4) seen from directly BEHIND, facing away from the camera, in the PASSING position of the walk, which is NOT a '
         'stride: upright and at full height, the two legs together and straight, both feet side by side under the body '
         'with neither sole showing, and both arms hanging close to the sides; '
         '(5) an exact SIDE PROFILE, walking toward the right edge of the frame, in the CONTACT position of an animator\'s '
         'walk cycle: the legs wide apart in a full step, the front heel touching down and the back foot pushing off '
         'from its toe, the arms swinging opposite to the legs; '
         '(6) an exact SIDE PROFILE, facing the right edge of the frame, in the PASSING position of an animator\'s walk '
         'cycle, which is NOT a stride: the body upright and at its tallest, the supporting leg straight and vertical '
         'under the hips, the other knee bent a little with its foot lifted just off the ground right beside the '
         'supporting ankle, so that from the side the two legs overlap into one narrow column and both feet are under '
         'the body, no more than a shoe apart; the arms hang straight down beside the hips. This sixth figure is the '
         'narrowest of the six, and it carries the same bag as the others. '
         'Leave a wide clear gap between the fifth figure and the sixth: the fifth figure\'s front foot comes nowhere '
         'near the sixth figure. '
         'Every picture is taken level from chest height, from far away with a long lens, so there is no perspective '
         'distortion. Soft, even, overcast daylight from all round, with no cast shadows and no hard highlights. No ground, '
         'no floor, no pavement, no shadow under the feet, no backdrop, no frame lines, no text, no labels, no numbers, no '
         'logos and no lettering anywhere, plain clothes with no prints. Muted, realistic colours, natural skin, real '
         'cloth with its own creases. A photograph of an ordinary person on an ordinary weekday: not fashion, not an '
         'illustration, not a 3D render, not a game character.')

SEASONS = {
    'cold': 'dressed for a cold, dry November day',
    'warm': 'dressed for a warm summer day',
}

# id, who (one line: age, build, skin, hair, what they wear and carry), height in metres, the wardrobe's season
FIGURES = [
    ('p01', 'a woman in her early forties of medium, fairly slim build with dark brown skin, a soft feminine face with no facial hair and short natural black hair, in a '
            'charcoal grey wool coat that ends at mid thigh, a plain dull green scarf, dark blue jeans and flat brown '
            'leather ankle boots, with a plain tan canvas tote bag hanging from her right shoulder', 1.65, 'cold'),
    ('p02', 'a heavyset man in his late sixties with pale skin, thick short grey hair that covers the whole top of his head in every view (he is not bald) and grey stubble, bare-headed, no glasses, '
            'in a plain navy blue quilted winter jacket with a plain collar and no hood, zipped up, loose khaki trousers '
            'and plain dark brown walking shoes, carrying nothing, his hands empty', 1.76, 'cold'),
    ('p03', 'a slim man in his middle twenties with light brown skin and short black hair, in a plain olive green hooded '
            'parka with the hood down, plain black trousers and plain grey trainers, wearing a plain black backpack on '
            'both shoulders', 1.80, 'cold'),
]


def prompt_of(fig):
    fid, who, tall, season = fig
    return SHEET.format(who=who + ', ' + SEASONS[season])


def jobs():
    return [(f[0], prompt_of(f)) for f in FIGURES]


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


def make(key, fid, prompt, force):
    os.makedirs(RAW, exist_ok=True)
    base = os.path.join(RAW, fid)
    if os.path.exists(base + '.png') and not force:
        return fid, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': SIZE, 'quality': QUALITY, 'n': 1, 'output_format': 'png',
                       'background': 'transparent'}).encode()
    err = ''
    for attempt in range(3):
        req = urllib.request.Request(API, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=400) as r:
                j = json.load(r)
            img = base64.b64decode(j['data'][0]['b64_json'])
            if os.path.exists(base + '.png'):   # --force: the sheet it replaces is kept aside with its sidecar, never lost
                stamp = int(time.time())
                os.replace(base + '.png', base + '.prev-%d.png' % stamp)
                if os.path.exists(base + '.json'):
                    os.replace(base + '.json', base + '.prev-%d.json' % stamp)
            with open(base + '.png.tmp', 'wb') as f:
                f.write(img)
            os.replace(base + '.png.tmp', base + '.png')
            json.dump({'id': fid, 'prompt': prompt, 'model': MODEL, 'size': SIZE, 'quality': QUALITY, 'transparent': True,
                       'poses': POSES, 'created': j.get('created'), 'usage': j.get('usage')}, open(base + '.json', 'w'), indent=1)
            return fid, 'made %d KB' % (len(img) // 1024)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (400, 401, 403, 429):   # a refusal is not retried: every call is counted against a budget
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
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    todo = [j for j in jobs() if not only or j[0] in only]
    if a.list:
        for fid, prompt in todo:
            print(fid, SIZE, 'on disk' if os.path.exists(os.path.join(RAW, fid + '.png')) else 'to make')
        return
    key = api_key()
    print('%d sheets, model %s, %s, quality %s' % (len(todo), MODEL, SIZE, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for fid, what in ex.map(lambda j: make(key, j[0], j[1], a.force), todo):
            print(fid, what, flush=True)


if __name__ == '__main__':
    main()
