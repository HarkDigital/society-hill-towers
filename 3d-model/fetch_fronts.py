#!/usr/bin/env python3
"""Generate the house fronts for the facade prototype (Oct 12, Mike: "prototype both blocks with AI-generated
fronts"): one straight-on elevation per prompt from OpenAI's image API, written to lidar_cache/fronts_raw/<set>/<id>.png
with a sidecar <id>.json (the prompt, the model, the size, when). bake_fronts.py cuts them into the atlas.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is
never printed. A front already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
FRONTS_MODEL picks the model (default gpt-image-2), FRONTS_QUALITY the quality (default high).

Each prompt asks for ONE house filling the frame: the party walls at the left and right edges, the sidewalk line at
the foot, the top of the cornice at the head, no perspective, no sky, flat overcast light, dark unlit glass. That is
what lets the page stretch a front across a house's own street wall, and lets the bake find the windows by their
dark glass."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'fronts_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('FRONTS_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('FRONTS_QUALITY', 'high')
SIZE = '768x1280'   # 3:5, both sides multiples of 16 (gpt-image-2 takes any such size between 1:3 and 3:1)

FRAME = ('Architectural front elevation photograph, perfectly orthographic and straight-on, of ONE {what} in {where}, '
         'Philadelphia. The facade fills the whole frame edge to edge: the left and right edges of the image are the party '
         'walls shared with the neighbouring houses (no gaps, no neighbouring houses, no side walls visible), the bottom '
         'edge is the sidewalk line at the foot of the front steps, and the top edge is the top of the cornice (no roof, '
         'no sky). No perspective, no vanishing lines, no camera tilt, every window the same size on its floor. Soft even '
         'overcast daylight with no cast shadows. No people, no cars, no trees, no street signs, no lettering or house '
         'numbers. The window glass is dark and unlit with crisp frames. Photorealistic, high detail, natural colours.')

SH = 'Society Hill'
SP = 'South Philadelphia'
FRONTS = [
    # Society Hill: three storeys and a half, 18th- and early 19th-century rows on Spruce, Pine and Delancey
    ('federal', 'f1', SH, 'three-storey Federal-style rowhouse of red brick laid in Flemish bond, three bays wide, a black '
     'six-panel front door with a semicircular fanlight in the left bay, white marble front steps, white six-over-six '
     'double-hung windows with black louvred shutters and marble sills, a plain white wooden box cornice'),
    ('federal', 'f2', SH, 'three-storey Georgian rowhouse of deep red brick, three bays, a door with a rectangular transom '
     'and fluted wooden pilasters in the right bay, marble steps with black wrought-iron railings, white flat-arch '
     'lintels with keystones, a white modillion cornice'),
    ('federal', 'f3', SH, 'three-storey Greek Revival townhouse of smooth pressed red brick over a white marble basement, '
     'three bays, a recessed doorway in a white marble surround, tall parlour-floor windows with a black iron balconette '
     'on the second floor, marble lintels and sills, a white dentil cornice'),
    ('federal', 'f4', SH, 'three-storey Federal rowhouse with its brick painted a soft warm cream, three bays, a dark green '
     'door with a fanlight, white marble steps, dark green louvred shutters, a white box cornice'),
    ('federal', 'f5', SH, 'three-storey Federal rowhouse of dark brownish-red brick, two bays wide, the door in the right '
     'bay with a four-light transom, marble steps, black shutters, simple stone sills and lintels, a narrow white '
     'cornice'),
    ('federal', 'f6', SH, 'three-storey 1960s modernist infill townhouse of dark red brick in Society Hill, a recessed '
     'entrance with a plain dark door, tall narrow vertical windows with dark metal frames, a flat brick parapet'),
    ('federal', 'f7', SH, 'four-storey Italianate townhouse of red brick with brownstone trim, three bays, segmental-arched '
     'window heads, a brownstone stoop of five steps with iron railings, a deep bracketed wooden cornice painted '
     'dark brown'),
    ('federal', 'f8', SH, 'three-storey Federal rowhouse of orange-red brick in Flemish bond with glazed headers, three '
     'bays, a red door with a fanlight and a white wooden door surround, marble steps, white shutters folded back, a '
     'white box cornice with a simple moulding'),
    # South Philadelphia: two-storey rows on the small streets between the numbered ones
    ('southrow', 's1', SP, 'two-storey red brick rowhouse, two bays wide, a white aluminium storm door and one window on '
     'the ground floor under a scalloped aluminium awning, two windows upstairs, a two-step concrete stoop, a plain '
     'brick parapet with a thin metal cap'),
    ('southrow', 's2', SP, 'two-storey rowhouse faced in grey-beige formstone (cast stone veneer), two bays, a metal awning '
     'over the door and front window, a glass-block window on the ground floor, two white vinyl windows upstairs, a '
     'marble step'),
    ('southrow', 's3', SP, 'two-storey brick rowhouse with a projecting second-floor bay window clad in painted dark green '
     'wood with three sashes, a dark door and one window on the ground floor, a small metal cornice above the bay'),
    ('southrow', 's4', SP, 'two-storey rowhouse with its brick painted dusty blue, two bays, a red front door, white '
     'window trim, a white bracketed wooden cornice, two marble steps'),
    ('southrow', 's5', SP, 'two-storey late 19th-century brick rowhouse, two bays, tall narrow two-over-two windows with '
     'white marble lintels and sills, three white marble steps, an Italianate bracketed pressed-metal cornice painted '
     'brown'),
    ('southrow', 's6', SP, 'two-storey rowhouse with a stucco front painted pale yellow, two bays, a striped green and '
     'white aluminium awning over the door and window, a white storm door, two windows upstairs'),
    ('southrow', 's7', SP, 'renovated two-storey brick rowhouse, two bays, new black-framed windows, a modern dark grey '
     'front door with a narrow glass panel, a black metal canopy over the door, a clean brick parapet'),
    ('southrow', 's8', SP, 'two-storey brown brick rowhouse, two bays, a black metal security storm door, a window '
     'air-conditioner in one upstairs window, a faded aluminium awning, a single concrete step'),
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


def make(key, set_, fid, where, what, force):
    out_dir = os.path.join(RAW, set_)
    os.makedirs(out_dir, exist_ok=True)
    png, meta = os.path.join(out_dir, fid + '.png'), os.path.join(out_dir, fid + '.json')
    if os.path.exists(png) and not force:
        return fid, 'kept'
    prompt = FRAME.format(what=what, where=where)
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': SIZE, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    for attempt in range(4):
        req = urllib.request.Request(API, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            img = base64.b64decode(d['data'][0]['b64_json'])
            with open(png + '.tmp', 'wb') as f:
                f.write(img)
            os.replace(png + '.tmp', png)
            json.dump({'id': fid, 'set': set_, 'prompt': prompt, 'model': MODEL, 'size': SIZE, 'quality': QUALITY,
                       'created': d.get('created'), 'usage': d.get('usage')}, open(meta, 'w'), indent=1)
            return fid, 'made %d KB' % (len(img) // 1024)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (400, 401, 403):
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
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    key = api_key()
    only = set(filter(None, a.only.split(',')))
    jobs = [f for f in FRONTS if not only or f[1] in only]
    print('%d fronts, model %s, %s, quality %s' % (len(jobs), MODEL, SIZE, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for fid, what in ex.map(lambda f: make(key, f[0], f[1], f[2], f[3], a.force), jobs):
            print(fid, what, flush=True)


if __name__ == '__main__':
    main()
