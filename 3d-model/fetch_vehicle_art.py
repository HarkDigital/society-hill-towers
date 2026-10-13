#!/usr/bin/env python3
"""Generate the vehicles' images (Oct 12, Mike: "please do anything necessary to make this look more photo realistic and
less cartoony ... all surfaces/water/anything you can improve"): orthographic views of the typical traffic's six car
kinds, the SEPTA bus and trolley, Amtrak's three car kinds, a PATCO car and the RiverLink ferry, from OpenAI's image API
on a transparent background, into lidar_cache/vehicle_art_raw/<id>.png with a sidecar .json; and the container stacks
the cargo ships carry, opaque. bake_vehicle_art.py cuts them to their real proportions and packs the page's atlases.

Every view is a plain elevation (side, plan, front or rear) with no perspective, because the page wraps it straight onto
the model's own faces: a side view's u runs along the length, its v up the height. The cars are painted plain white so
the page can tint each one its own colour through the paint mask the bake finds; the transit liveries are painted as
they run, with no lettering, no route numbers and no logos.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never printed. An image
already on disk is kept; --force makes it again, --only <id>[,<id>] makes some. VEHICLES_MODEL (default gpt-image-1.5,
which takes a transparent background on this account) and VEHICLES_QUALITY (default high)."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'vehicle_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('VEHICLES_MODEL', 'gpt-image-1.5')
OPAQUE_MODEL = os.environ.get('VEHICLES_OPAQUE_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('VEHICLES_QUALITY', 'high')

TAIL = ('No people, no driver, no text, no lettering, no numbers, no logos, no badges, no number plate. Isolated on a fully '
        'transparent background: no floor, no road, no shadow, no reflection under it. Soft even overcast daylight, '
        'natural colours, photorealistic studio product photograph.')
SIDE = ('Orthographic side elevation of {what}, seen exactly side-on from its mid height with no perspective and no '
        'foreshortening, the front pointing to the right, the whole vehicle filling the frame from edge to edge '
        'horizontally with a small even margin. ' + TAIL)
TOP = ('Orthographic plan view of {what}, seen from directly above with no perspective, the front pointing to the right, '
       'the whole vehicle filling the frame from edge to edge horizontally with a small even margin: the roof, the bonnet, '
       'the windscreen and the rear window seen from straight above. ' + TAIL)
FRONT = ('Orthographic front elevation of {what}, seen exactly head-on from its mid height with no perspective, '
         'centred and filling the frame vertically with a small even margin, headlights off. ' + TAIL)
REAR = ('Orthographic rear elevation of {what}, seen exactly from straight behind at its mid height with no perspective, '
        'centred and filling the frame vertically with a small even margin, tail lights off. ' + TAIL)

PAINT = ('clean plain white paint with no stripes, dark tinted glass, black tyres on plain dark charcoal grey alloy wheels, '
         'black plastic bumpers and trim')
CARS = [
    ('compact', 'a generic modern compact five-door hatchback car with ' + PAINT),
    ('sedan', 'a generic modern four-door mid-size sedan car with ' + PAINT),
    ('wagon', 'a generic modern five-door estate car (station wagon) with ' + PAINT),
    ('suv', 'a generic modern mid-size five-seat SUV with ' + PAINT),
    ('pickup', 'a generic modern full-size four-door crew-cab pickup truck with an open empty cargo bed and ' + PAINT),
    ('van', 'a generic modern high-roof cargo van (like a Ford Transit) with no windows behind the front doors, clean plain '
     'white paint, dark tinted glass, black tyres on black steel wheels, black plastic bumpers'),
]
TRANSIT = [
    ('bus_side', SIDE, 'a 40-foot low-floor hybrid city transit bus in Philadelphia\'s SEPTA colours: a white body, a dark '
     'blue lower band with thin red and blue stripes along the side, a continuous dark tinted window band, two sets of '
     'glazed doors, a rear engine grille, a low roof equipment pod, black tyres on silver wheels', '1536x1024'),
    ('bus_front', FRONT, 'a 40-foot low-floor city transit bus in Philadelphia\'s SEPTA colours: white with a dark blue '
     'lower band, a large one-piece windscreen, a blank dark destination sign over it, black bumper', '1024x1024'),
    ('bus_rear', REAR, 'a 40-foot low-floor city transit bus in Philadelphia\'s SEPTA colours: white with a dark blue lower '
     'band, a rear engine grille, a small dark rear window, black bumper', '1024x1024'),
    ('trolley_side', SIDE, 'a 15-metre single-body Kawasaki light rail street trolley car in Philadelphia\'s SEPTA colours: '
     'a white and light grey body with red and blue stripes, large side windows, two sets of doors, a trolley pole folded '
     'down on the roof, the wheels hidden behind low skirts', '1536x1024'),
    ('trolley_front', FRONT, 'a Kawasaki light rail street trolley car in Philadelphia\'s SEPTA colours: white and grey with '
     'red and blue stripes, a large flat windscreen, a blank dark destination sign above it', '1024x1024'),
    ('amfleet_side', SIDE, 'a 26-metre Amtrak Amfleet stainless steel passenger coach: fluted corrugated stainless sides, a '
     'long row of small rounded-corner windows, a thin red, white and blue stripe just below the windows, a door at each '
     'end, dark bogies under each end', '1536x1024'),
    ('acs64_side', SIDE, 'an Amtrak Siemens ACS-64 electric locomotive: a silver grey body, a broad dark blue stripe along '
     'the lower side with a thin red line, cab windows at both ends, a folded pantograph on the roof, dark bogies', '1536x1024'),
    ('acs64_front', FRONT, 'an Amtrak Siemens ACS-64 electric locomotive cab end: a silver grey nose, two cab windows, a '
     'dark blue band with a thin red line, headlights off, a black pilot below', '1024x1024'),
    ('acela_side', SIDE, 'a modern high-speed train power car with a long streamlined nose to the right: a silver and dark '
     'grey body, a dark window band at the cab, a thin red stripe, dark bogies', '1536x1024'),
    ('acela_front', FRONT, 'the streamlined nose of a modern high-speed train power car: silver and dark grey, a wide '
     'dark wraparound cab window, headlights off', '1024x1024'),
    ('patco_side', SIDE, 'a 20-metre stainless steel PATCO rapid transit subway car: a stainless steel body with a red belt '
     'stripe below the windows, four sets of sliding doors, large windows, dark bogies', '1536x1024'),
    ('patco_front', FRONT, 'the cab end of a stainless steel PATCO rapid transit subway car: a red belt stripe, a flat end '
     'with two windows and a centre door, headlights off', '1024x1024'),
    ('ferry_side', SIDE, 'a 25-metre white passenger river ferry: a white hull with a blue band along the sheer, a glazed '
     'main cabin with a row of large windows, an open upper deck with railings under a blue canopy, a small pilothouse, '
     'seen from the water line up', '1536x1024'),
]
OPAQUE = [
    # the stack's ends (the first make came back end-on, the doors of the boxes: it dresses the stack's fore and aft faces)
    ('containers', 'Orthographic side view of a long stack of 40-foot shipping containers on a cargo ship deck, three '
     'tiers high and filling the whole frame edge to edge: corrugated steel boxes in faded dark blue, rust red, white, '
     'grey, dark green, orange and brown, a little rust streaking, corner castings visible, no logos, no text, no '
     'lettering, no ship hull, no sky, flat even overcast light, photorealistic.', '1536x1024'),
    ('containers_side', 'Orthographic elevation photograph of the long side of a stack of 40-foot shipping containers '
     'on a cargo ship, exactly two containers long and three tiers high, filling the whole frame edge to edge: each '
     'container a long box about five times as long as it is tall, seen broadside along its full corrugated length, '
     'vertical corrugations, corner castings at each end, in faded dark blue, rust red, white, grey, dark green, orange '
     'and brown, a little rust streaking. No doors, no logos, no text, no lettering, no ship hull, no sky, flat even '
     'overcast light, photorealistic.', '1536x1024'),
]


def jobs():
    out = []
    for cid, what in CARS:
        out.append((cid + '_side', SIDE.format(what=what), '1536x1024', True))
        out.append((cid + '_top', TOP.format(what=what), '1536x1024', True))
        out.append((cid + '_front', FRONT.format(what=what), '1024x1024', True))
        out.append((cid + '_rear', REAR.format(what=what), '1024x1024', True))
    for tid, frame, what, size in TRANSIT:
        out.append((tid, frame.format(what=what), size, True))
    for oid, prompt, size in OPAQUE:
        out.append((oid, prompt, size, False))
    return out


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


def make(key, vid, prompt, size, transparent, force):
    os.makedirs(RAW, exist_ok=True)
    base = os.path.join(RAW, vid)
    if os.path.exists(base + '.png') and not force:
        return vid, 'kept'
    model = MODEL if transparent else OPAQUE_MODEL
    req_body = {'model': model, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1, 'output_format': 'png'}
    if transparent:
        req_body['background'] = 'transparent'
    body = json.dumps(req_body).encode()
    err = ''
    for attempt in range(4):
        req = urllib.request.Request(API, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=400) as r:
                j = json.load(r)
            img = base64.b64decode(j['data'][0]['b64_json'])
            with open(base + '.png.tmp', 'wb') as f:
                f.write(img)
            os.replace(base + '.png.tmp', base + '.png')
            json.dump({'id': vid, 'prompt': prompt, 'model': model, 'size': size, 'quality': QUALITY,
                       'transparent': transparent, 'created': j.get('created'), 'usage': j.get('usage')},
                      open(base + '.json', 'w'), indent=1)
            return vid, 'made %d KB' % (len(img) // 1024)
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (400, 401, 403):
                return vid, 'refused %d: %s' % (e.code, msg)
            err = '%d %s' % (e.code, msg)
        except Exception as e:
            err = str(e)[:300]
        time.sleep(5 + 10 * attempt)
    return vid, 'failed: ' + err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    key = api_key()
    only = set(filter(None, a.only.split(',')))
    todo = [j for j in jobs() if not only or j[0] in only]
    print('%d images, model %s (opaque %s), quality %s' % (len(todo), MODEL, OPAQUE_MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for vid, what in ex.map(lambda j: make(key, j[0], j[1], j[2], j[3], a.force), todo):
            print(vid, what, flush=True)


if __name__ == '__main__':
    main()
