#!/usr/bin/env python3
"""Generate the walking people's pictures (Round 227, Mike: "people on the sidewalks, walking"; Round 242: "make it smoother
still and have many more different looking people. They should also be dressed specific to the season").

Three STRIPS a figure, each eight full-body pictures of one person in one row: the eight equal moments of ONE step of a
walk, seen from the side, from the front and from behind. The side strip is made from words alone; the front and the back
are EDITS of it, so all three are the same person. Written to lidar_cache/people_art_raw/<id>-<view>.png with a sidecar
.json (the prompt, the model, the size, the usage). bake_people_art.py cuts every strip into its eight pictures and packs
one atlas a wardrobe.

A figure is one record of FIGURES: its id, one line saying who it is and what it wears, its height in metres and its
WARDROBE: cold, cool or warm. The page draws one wardrobe at a time, chosen by the temperature (app.js, peopleWardrobe),
so each wardrobe is a crowd of its own weather and mixed inside it (a cool day has a coat and a T-shirt in it too).

Every figure is MIRROR-SAFE: the page draws the second step of a cycle as the first one mirrored (from the front and from
behind the other leg leads), so nothing is carried on one side only. Hands are empty or a backpack is worn on both
shoulders: no tote, no shoulder bag, no crossbody strap, no cup, no phone, no umbrella.

No lettering, no logo, no brand, no uniform and nobody in particular: the figures are ordinary and generic, seen from
4 m at the nearest. Every strip is looked at before it is kept (eight whole figures, one person, one scale, the step's
moments in order, no ground or shadow); a reject is made again with --force, which keeps the picture it replaces beside
it.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never printed.
PEOPLE_ART_RAW moves the raw folder (a worktree has no lidar_cache of its own), PEOPLE_ART_MODEL picks the model and
PEOPLE_ART_QUALITY the quality.

What the pictures had to learn (keep these when the wording changes):
- Rounds 227 and 237 asked gpt-image-1.5 for six pictures a sheet, two moments of each view, and then for an edit with
  two more: it could not hold a moment it was asked for (a profile's "up" came back a stride as often as not, so the
  bake ordered the in-betweens by how far apart the feet stood), and a step of four pictures still read as stepping;
- optical flow between those pictures (OpenCV's DIS) made fair in-betweens from the front and behind and ghost legs from
  the side, where a leg swings 30 px between pictures;
- a sixteen-picture Muybridge cycle from gpt-image-1.5 came back as nineteen strides with a cartoon face;
- gpt-image-2.6 draws the eight moments of one step in order, the passing narrowest, one person in all eight, and
  returns the figures already cut out on transparency when asked for a flat chroma green ground (the bake keys the green
  itself if a strip ever comes back opaque). Its pictures are about 440 px tall: the atlas's 256 px cell and no more;
- a hat, glasses and a beard are where the pictures drift apart: describe them plainly or leave them off.

Usage: python3 fetch_people_art.py [--only id,...] [--views side,front,back] [--force] [--list] [--workers 4]"""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get('PEOPLE_ART_RAW') or os.path.join(HERE, 'lidar_cache', 'people_art_raw')
API = 'https://api.openai.com/v1/images/generations'
EDIT_API = 'https://api.openai.com/v1/images/edits'
MODEL = os.environ.get('PEOPLE_ART_MODEL', 'gpt-image-2.6-sunburst')
QUALITY = os.environ.get('PEOPLE_ART_QUALITY', 'high')
SIZE = '1536x1024'   # eight figures in one row: each about 190 px wide and 430 to 460 tall

VIEWS = ['side', 'front', 'back']   # the order they are made in: the side from words, the other two edits of it
FRAMES = 8                           # the eight equal moments of one step, 0 the contact; the passing is 4

STEPS = {
    'side': ('in exact SIDE PROFILE, facing and walking toward the right edge of the frame',
             '1: contact, the legs at their widest, the right leg forward with its heel just touching down, the left leg behind '
             'on its toes. 2: the right foot rolling flat, the legs a little less wide. 3: the down, the right foot flat with its '
             'knee bent under the weight, the left heel high. 4: the left foot leaving the ground, the left knee bending as the '
             'leg starts to swing forward. 5: the passing, upright, the right leg straight under the hips, the left foot just '
             'off the ground beside the right ankle, both legs overlapping in one narrow column. 6: the left leg swinging ahead '
             'of the right, its knee bent, the feet a short step apart. 7: the up, the right heel rising, the left leg reaching '
             'forward almost straight. 8: the left heel about to touch down, the legs nearly as wide as in picture 1.'),
    'front': ('seen from straight in FRONT, walking straight toward the camera, the face to the camera',
              '1: contact, the right leg forward with its heel just touching down and the left leg behind, the feet a stride '
              'apart in depth. 2: the right foot rolling flat. 3: the down, the right knee a little bent under the weight, the '
              'left heel lifted behind. 4: the left foot leaving the ground behind. 5: the passing, upright and tallest, the '
              'left foot just off the ground beside the right ankle. 6: the left leg swinging forward past the right, its knee '
              'bent. 7: the up, the right heel rising, the left leg reaching forward. 8: the left heel about to touch down.'),
    'back': ('seen from straight BEHIND, walking straight away from the camera, the back of the head to the camera',
             '1: contact, the right leg forward with its heel just touching down and the left leg behind with its heel lifted so '
             'its sole shows. 2: the right foot rolling flat. 3: the down, the right knee a little bent under the weight, the '
             'left sole showing. 4: the left foot leaving the ground behind, its sole showing. 5: the passing, upright and '
             'tallest, the left foot just off the ground beside the right ankle. 6: the left leg swinging forward past the '
             'right, its knee bent. 7: the up, the right heel rising so its sole shows, the left leg reaching forward. 8: the '
             'left heel about to touch down ahead.'),
}

STRIP = ('{lead}as an animator\'s reference strip: EIGHT full-body photographs of this person {how}, in ONE horizontal row, '
         'evenly spaced, read left to right as the eight equal moments of ONE step of a relaxed walk. {beats} From each picture '
         'to the next the legs and arms move by a small, even amount, like consecutive frames of a film; the arms swing opposite '
         'to the legs. Every figure at exactly the same scale, heads level and shoes on one level line, each centred in its own '
         'equal slot with a clear gap between neighbours, nothing cut off. Level camera at chest height with a long lens, soft '
         'even overcast daylight. {carry} Plain flat pure chroma-key green background (#00FF00), perfectly even all over, no '
         'ground, no floor, no shadow on the ground, no lines, no numbers, no text, no logos, plain clothes with no prints or '
         'lettering. A real photograph of an ordinary person on an ordinary day in the city, not an illustration, not a 3D '
         'render, not a game character.')
LEAD_NEW = 'A picture of {who}, {season}, '
LEAD_EDIT = ('Make a NEW picture of the SAME person as in the attached picture, exactly the same face, hair, build, clothes, '
             'colours and anything carried, ')

WARDROBES = {
    'cold': 'dressed for a cold winter day in Philadelphia',
    'cool': 'dressed for a mild spring or autumn day in Philadelphia',
    'warm': 'dressed for a warm summer day in Philadelphia',
}
CARRY = {
    'none': 'The hands are empty in every picture: nothing is carried, no bag, no strap, no cup and no phone.',
    'pack': 'The same backpack is worn on BOTH shoulders in every picture, its two straps over both shoulders; nothing else is '
            'carried and the hands are empty.',
}

# id, who (one line: age, build, skin, hair, what they wear), height in metres, wardrobe, what is carried (CARRY)
FIGURES = [
    # cold: under about 50 F
    ('c01', 'a woman in her early forties of medium, fairly slim build with dark brown skin and short natural black hair, in a '
            'charcoal grey wool coat that ends at mid thigh, a plain dull green scarf, dark blue jeans and flat brown leather '
            'ankle boots', 1.65, 'cold', 'none'),
    ('c02', 'a heavyset man in his late sixties with pale skin and thick short grey hair, bare-headed, no glasses, in a plain '
            'navy blue quilted winter jacket zipped up, loose khaki trousers and plain dark brown walking shoes', 1.76, 'cold', 'none'),
    ('c03', 'a slim man in his middle twenties with light brown skin and short black hair, in a plain olive green hooded parka '
            'with the hood down, plain black trousers and plain grey trainers, with a plain black backpack', 1.80, 'cold', 'pack'),
    ('c04', 'an East Asian woman in her late twenties with straight black hair to her shoulders, in a long camel wool coat to '
            'the knee, a plain black knitted beanie, black trousers and black leather ankle boots, with a small plain black '
            'backpack', 1.62, 'cold', 'pack'),
    ('c05', 'a tall, broad Black man of about fifty with a short neat greying beard, in a plain black knitted cap, a long dark '
            'grey wool overcoat, charcoal trousers and black leather shoes', 1.88, 'cold', 'none'),
    ('c06', 'a white woman in her middle seventies with short white hair, in a long plain maroon quilted coat, a light grey '
            'knitted scarf, grey wool trousers and flat black shoes', 1.58, 'cold', 'none'),
    ('c07', 'a Latino young man of about eighteen with short curly dark brown hair, in a plain black puffer jacket, plain grey '
            'sweatpants and plain white sneakers, with a plain dark blue backpack', 1.74, 'cold', 'pack'),
    ('c08', 'a South Asian man in his middle thirties with short black hair and a short neat black beard, in a dark green '
            'waxed cotton field jacket, a plain grey knitted scarf, blue jeans and brown leather boots', 1.75, 'cold', 'none'),
    ('c09', 'a white woman of about thirty with red-blonde hair in a low bun, in a light grey puffer coat to the knee, a plain '
            'cream knitted hat, black leggings and tan winter boots', 1.68, 'cold', 'none'),
    ('c10', 'a Black woman of about sixty with short grey natural hair, in a burgundy wool coat to the knee, a plain mustard '
            'yellow scarf, dark trousers and black low boots', 1.63, 'cold', 'none'),
    # cool: about 50 to 70 F
    ('m01', 'a white man in his middle forties with short brown hair, in a plain navy blue zip-up windbreaker, khaki chinos '
            'and plain white leather sneakers', 1.79, 'cool', 'none'),
    ('m02', 'a Black woman in her middle twenties with long box braids tied back, in a plain blue denim jacket over a plain '
            'white T-shirt, black jeans and plain white sneakers, with a small tan backpack', 1.70, 'cool', 'pack'),
    ('m03', 'an East Asian man of about sixty with short grey and black hair, in a plain beige lightweight jacket zipped half '
            'way over a light blue collared shirt, grey trousers and black leather shoes', 1.70, 'cool', 'none'),
    ('m04', 'a Latina woman of about forty with wavy dark brown hair to her shoulders, in a plain burgundy knitted sweater, '
            'dark blue jeans and brown leather ankle boots', 1.60, 'cool', 'none'),
    ('m05', 'a white young woman of about nineteen with long straight blonde hair, in a plain grey hooded sweatshirt with the '
            'hood down, black leggings and plain white sneakers, with a plain black backpack', 1.66, 'cool', 'pack'),
    ('m06', 'a South Asian man of about thirty with short black hair, in a plain olive green bomber jacket over a plain black '
            'T-shirt, dark blue jeans and plain grey sneakers', 1.77, 'cool', 'none'),
    ('m07', 'a white woman of about seventy with short silver hair, in a plain light blue quilted vest over a white long-sleeved '
            'top, tan trousers and white walking shoes', 1.60, 'cool', 'none'),
    ('m08', 'a Black man in his middle thirties with a shaved head, in a plain dark grey crewneck sweatshirt, black jogging '
            'trousers and plain black sneakers, with a plain black backpack', 1.83, 'cool', 'pack'),
    ('m09', 'a white woman of about fifty with a brown chin-length bob, in a long charcoal wool coat worn open over a black '
            'sweater, black trousers and flat black shoes', 1.67, 'cool', 'none'),
    ('m10', 'a Latino man of about twenty-two with short black hair, in a plain white T-shirt, blue jeans and plain white '
            'sneakers', 1.75, 'cool', 'none'),
    # warm: over about 70 F
    ('w01', 'a woman in her early thirties of slim build with light olive skin and long dark brown hair tied back in a low '
            'ponytail, in a plain sleeveless rust-orange cotton top, light blue denim shorts to mid thigh and plain white canvas '
            'sneakers', 1.66, 'warm', 'none'),
    ('w02', 'a Black man of about thirty with short twisted hair, in a plain light grey T-shirt, khaki shorts to the knee and '
            'plain white sneakers, with a plain black backpack', 1.80, 'warm', 'pack'),
    ('w03', 'a white man of about sixty, bald on top with a short fringe of grey hair, in a plain light blue short-sleeved '
            'button shirt, beige chino trousers and brown leather loafers', 1.75, 'warm', 'none'),
    ('w04', 'an East Asian woman of about twenty-two with long straight black hair worn loose, in a plain pale yellow '
            'short-sleeved cotton sundress to the knee and plain white flat sandals', 1.60, 'warm', 'none'),
    ('w05', 'a Black woman of about forty-five with short natural hair, in a plain coral short-sleeved blouse, white linen '
            'trousers and tan flat sandals', 1.68, 'warm', 'none'),
    ('w06', 'a Latino young man of about eighteen with short black hair, in a plain oversized white T-shirt, black athletic '
            'shorts to the knee and plain black sneakers', 1.72, 'warm', 'none'),
    ('w07', 'a South Asian woman in her middle thirties with long black hair in a single braid, in a plain teal short-sleeved '
            'tunic top, loose light grey trousers and flat tan sandals', 1.58, 'warm', 'none'),
    ('w08', 'a white woman of about twenty-eight with short curly red hair, in a plain navy blue T-shirt, olive green cargo '
            'shorts and plain grey trainers, with a small plain grey backpack', 1.70, 'warm', 'pack'),
    ('w09', 'a Black man of about seventy with short white hair, in a plain white short-sleeved polo shirt with no logo, grey '
            'trousers and black leather shoes', 1.74, 'warm', 'none'),
    ('w10', 'a heavyset white man in his middle thirties with a short brown beard and short brown hair, in a plain maroon '
            'T-shirt, dark grey shorts to the knee and plain black sneakers', 1.82, 'warm', 'none'),
]


def prompt_of(fig, view):
    fid, who, tall, ward, carry = fig
    how, beats = STEPS[view]
    lead = LEAD_NEW.format(who=who, season=WARDROBES[ward]) if view == 'side' else LEAD_EDIT
    return STRIP.format(lead=lead, how=how, beats=beats, carry=CARRY[carry])


def jobs(views=VIEWS):
    return [(f[0], v, prompt_of(f, v)) for f in FIGURES for v in views]


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


def raw_path(fid, view):
    return os.path.join(RAW, '%s-%s.png' % (fid, view))


def make(key, fid, view, prompt, force):
    os.makedirs(RAW, exist_ok=True)
    base = raw_path(fid, view)[:-4]
    if os.path.exists(base + '.png') and not force:
        return fid, view, 'kept'
    ref = raw_path(fid, 'side')
    if view != 'side':
        if not os.path.exists(ref):
            return fid, view, 'no side strip to edit'
        body, ctype = multipart({'model': MODEL, 'prompt': prompt, 'size': SIZE, 'quality': QUALITY, 'n': '1', 'output_format': 'png'},
                                [('image[]', os.path.basename(ref), open(ref, 'rb').read())])
        url = EDIT_API
    else:
        body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': SIZE, 'quality': QUALITY, 'n': 1, 'output_format': 'png'}).encode()
        ctype, url = 'application/json', API
    err = ''
    for attempt in range(3):
        req = urllib.request.Request(url, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                j = json.load(r)
            img = base64.b64decode(j['data'][0]['b64_json'])
            if os.path.exists(base + '.png'):   # --force: the strip it replaces is kept aside with its sidecar, never lost
                stamp = int(time.time())
                os.replace(base + '.png', base + '.prev-%d.png' % stamp)
                if os.path.exists(base + '.json'):
                    os.replace(base + '.json', base + '.prev-%d.json' % stamp)
            with open(base + '.png.tmp', 'wb') as f:
                f.write(img)
            os.replace(base + '.png.tmp', base + '.png')
            json.dump({'id': fid, 'view': view, 'prompt': prompt, 'model': MODEL, 'size': SIZE, 'quality': QUALITY,
                       'edit_of': os.path.basename(ref) if view != 'side' else None, 'frames': FRAMES, 'created': j.get('created'),
                       'usage': j.get('usage')}, open(base + '.json', 'w'), indent=1)
            return fid, view, 'made %d KB' % (len(img) // 1024)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (400, 401, 403, 429):   # a refusal is not retried: every call is counted against a budget
                return fid, view, 'refused %d: %s' % (e.code, msg)
            err = '%d %s' % (e.code, msg)
        except Exception as e:
            err = str(e)[:300]
        time.sleep(5 + 10 * attempt)
    return fid, view, 'failed: ' + err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--views', default=','.join(VIEWS))
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    views = [v for v in VIEWS if v in a.views.split(',')]
    todo = [j for j in jobs(views) if not only or j[0] in only]
    if a.list:
        for fid, view, prompt in todo:
            print(fid, view, SIZE, 'on disk' if os.path.exists(raw_path(fid, view)) else 'to make')
        return
    key = api_key()
    print('%d strips, model %s, %s, quality %s' % (len(todo), MODEL, SIZE, QUALITY), flush=True)
    # the side strips first: the front and the back are edits of them
    for group in ([j for j in todo if j[1] == 'side'], [j for j in todo if j[1] != 'side']):
        with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
            for fid, view, what in ex.map(lambda j: make(key, j[0], j[1], j[2], a.force), group):
                print(fid, view, what, flush=True)


if __name__ == '__main__':
    main()
