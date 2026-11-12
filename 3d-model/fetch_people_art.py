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

Usage: python3 fetch_people_art.py [--mid] [--only id,...] [--force] [--list] [--workers 3]"""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('PEOPLE_ART_RAW') or os.path.join(HERE, 'lidar_cache', 'people_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('PEOPLE_ART_MODEL', 'gpt-image-1.5')
QUALITY = os.environ.get('PEOPLE_ART_QUALITY', 'high')
SIZE = '1536x1024'   # six figures in one row: each about 250 px wide and 480 to 560 tall

# the sheet's six pictures, left to right: (view, frame). bake_people_art.py reads this order. Frames run through one
# step: 0 the contact (legs apart), 1 the down (the weight landing), 2 the passing (legs together), 3 the up (the
# swinging leg reaching forward). The first sheet holds the contact and the passing; the in-between sheet (MID, Round
# 237) the down and the up
POSES = [('front', 0), ('front', 2), ('back', 0), ('back', 2), ('side', 0), ('side', 2)]
MID_POSES = [('front', 1), ('front', 3), ('back', 1), ('back', 3), ('side', 1), ('side', 3)]
EDIT_API = 'https://api.openai.com/v1/images/edits'

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

# Round 237 (Mike: "The people are a bit disjointed. Can we smooth out their gait?"): two pictures a view made the walk a
# flip between a stride and standing still. The in-between sheet is an EDIT of the figure's own first sheet (the image
# endpoint's edits with input_fidelity high), so the face, the clothes and the bag are the first sheet's, and asks for
# the two moments an animator draws between those two: the down and the up. <id>-mid.png beside <id>.png.
MID_SHEET = ('The attached picture is a sheet of six cut-out photographs of one real person walking, in one row: from the '
             'front in mid stride, from the front in the passing position, from behind in mid stride, from behind in the '
             'passing position, in side profile in the contact position, and in side profile in the passing position. '
             'Make a NEW sheet of the SAME person: exactly the same face, hair, build, clothes and colours, at exactly '
             'the same scale and in the same soft overcast light, six NEW full-body pictures in ONE horizontal row on a '
             'fully transparent background, evenly spaced with a clear gap between each figure and the next, the heads level '
             'and the shoes level, nothing cut off. These six show the two IN-BETWEEN moments of the same walk that an '
             'animator draws between the stride and the passing position. From left to right: '
             '(1) seen from the FRONT walking toward the camera, the DOWN position just after a stride: the front foot now '
             'flat on the ground and taking the weight with its knee a little bent, the back foot\'s heel lifted, the feet '
             'still apart but closer than in a full stride, the arms swung part of the way; '
             '(2) seen from the FRONT walking toward the camera, the UP position just after passing: upright on one straight '
             'leg, the other leg swinging forward with its knee bent and its foot lifted just off the ground a little ahead, '
             'the feet close together, the arms only slightly swung; '
             '(3) seen from directly BEHIND walking away, the DOWN position: the forward foot flat and taking the weight, '
             'the back foot\'s heel lifted so part of its sole shows, the feet apart but closer than in a full stride, the '
             'arms swung part of the way; '
             '(4) seen from directly BEHIND walking away, the UP position: upright on one straight leg, the other knee bent '
             'and its foot lifted just off the ground, swinging forward, the feet close together, the arms only slightly '
             'swung; '
             '(5) an exact SIDE PROFILE walking toward the right edge of the frame, the DOWN position: the front leg bent at '
             'the knee under the body\'s weight with its foot flat, the back leg trailing with its heel lifted high and only '
             'its toes on the ground, the feet about two thirds of a full stride apart, the arms swinging opposite to the '
             'legs; '
             '(6) an exact SIDE PROFILE walking toward the right edge of the frame, the UP position, a moment after the legs '
             'have passed each other: the legs like a narrow pair of scissors only just opened, the supporting leg straight '
             'and under the hips with its heel starting to rise, the swinging leg a little ahead of it with the knee bent and '
             'its foot in the air, clear of the ground, so the two feet are only about one shoe length apart. This sixth '
             'figure is far narrower than the fifth; the arms close to the sides and only just swinging. '
             '{carry} '
             'Every picture is taken level from chest height with a long lens, no perspective distortion. No ground, no '
             'floor, no shadow under the feet, no backdrop, no frame lines, no text, no labels, no numbers, no logos. A '
             'photograph of an ordinary person, not an illustration, not a 3D render, not a game character.')

# what each figure carries, said plainly for the in-between sheet (asked to keep "the bag", a figure with none grew one)
MID_CARRY = {
    'p01': 'She carries the same plain tan canvas tote bag hanging from her own right shoulder in all six pictures, as in the attached sheet.',
    'p02': 'He carries NOTHING: his hands are empty, and there is no bag, no strap and no backpack anywhere in any of the six pictures.',
    'p03': 'He wears the same plain black backpack on both shoulders in all six pictures, as in the attached sheet.',
}

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


def multipart(fields, files):
    """A multipart/form-data body: fields {name: value}, files [(name, filename, bytes)]."""
    b = '----philly3d%d' % int(time.time() * 1000)
    out = []
    for k, v in fields.items():
        out.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode())
    for k, fn, data in files:
        out.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: image/png\r\n\r\n' % (b, k, fn)).encode() + data + b'\r\n')
    out.append(('--%s--\r\n' % b).encode())
    return b''.join(out), 'multipart/form-data; boundary=' + b


def make(key, fid, prompt, force, mid=False):
    os.makedirs(RAW, exist_ok=True)
    src = os.path.join(RAW, fid + '.png')
    base = os.path.join(RAW, fid + ('-mid' if mid else ''))
    if os.path.exists(base + '.png') and not force:
        return fid, 'kept'
    if mid:
        if not os.path.exists(src):
            return fid, 'no first sheet to edit'
        body, ctype = multipart({'model': MODEL, 'prompt': prompt, 'size': SIZE, 'quality': QUALITY, 'n': '1', 'output_format': 'png',
                                 'background': 'transparent', 'input_fidelity': 'high'}, [('image[]', fid + '.png', open(src, 'rb').read())])
        url = EDIT_API
    else:
        body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': SIZE, 'quality': QUALITY, 'n': 1, 'output_format': 'png',
                           'background': 'transparent'}).encode()
        ctype, url = 'application/json', API
    err = ''
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': ctype})
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
                       'edit_of': fid + '.png' if mid else None, 'poses': MID_POSES if mid else POSES, 'created': j.get('created'),
                       'usage': j.get('usage')}, open(base + '.json', 'w'), indent=1)
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
    ap.add_argument('--mid', action='store_true', help='the in-between sheets (<id>-mid.png), each an edit of its first sheet')
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    todo = [j for j in jobs() if not only or j[0] in only]
    if a.mid:
        todo = [(fid, MID_SHEET.format(carry=MID_CARRY[fid])) for fid, _ in todo]
    suf = '-mid' if a.mid else ''
    if a.list:
        for fid, prompt in todo:
            print(fid + suf, SIZE, 'on disk' if os.path.exists(os.path.join(RAW, fid + suf + '.png')) else 'to make')
        return
    key = api_key()
    print('%d %ssheets, model %s, %s, quality %s' % (len(todo), 'in-between ' if a.mid else '', MODEL, SIZE, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for fid, what in ex.map(lambda j: make(key, j[0], j[1], a.force, a.mid), todo):
            print(fid, what, flush=True)


if __name__ == '__main__':
    main()
