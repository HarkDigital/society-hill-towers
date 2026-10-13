#!/usr/bin/env python3
"""Generate the walls' and the pitched roofs' materials (the realism pass, Mike: "make this look more photo realistic and
less cartoony ... all surfaces"): straight-on photographs of a patch of brick, render, stone, concrete, shingle, slate and
standing-seam metal, and a fresh snow on a flat roof, from OpenAI's image API, into lidar_cache/wall_art_raw/<id>.png
with a sidecar .json. bake_wall_art.py makes them tile on their own courses and writes wall_art.json.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env, never from the repo, and is never printed. An image
already on disk is kept; --force makes it again, --only <id>[,<id>] makes some."""
import argparse, base64, concurrent.futures, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'wall_art_raw')
API = 'https://api.openai.com/v1/images/generations'
MODEL = os.environ.get('WALL_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('WALL_QUALITY', 'high')
SIZE = '1024x1024'

# a wall seen square on: the facade shader lays it in metres along the wall and up it, under its own windows
FRAME_WALL = ('Seamless tileable wall texture for a 3D city model: a perfectly orthographic, straight-on photograph of '
              '{what}, filling the whole frame evenly, the courses running exactly horizontally across the image. No '
              'windows, no doors, no corners or edges, no pipes, no signs, no graffiti, no plants, no objects and no cast '
              'shadows. Soft even overcast daylight. Natural colours, photorealistic, uniform detail across the whole image '
              'so it repeats without a visible seam.')
# a pitched roof seen square on to its slope, the courses across the image (the shader lays them along the eave)
FRAME_PITCH = ('Seamless tileable texture for a 3D city model: a photograph taken looking straight at a pitched roof '
               'surface, perpendicular to the slope, of {what}, filling the whole frame evenly, the courses running '
               'exactly horizontally across the image. No ridge, no eaves, no edges, no chimneys, no vents, no skylights, '
               'no gutters, no objects, no cast shadows. Soft even overcast daylight. Natural colours, photorealistic, '
               'uniform detail so it repeats without a visible seam.')
FRAME_ROOF = ('Seamless tileable texture for a 3D city model: an aerial photograph taken by a drone looking straight down at '
              '{what}, filling the whole frame evenly. No perspective, no parapets, no edges or borders, no vents, no '
              'skylights, no HVAC units, no shadows of objects, no objects. Soft even overcast daylight. Natural colours, '
              'photorealistic, uniform detail across the whole image so it repeats without a visible seam.')
WALLS = [
    ('wall_brick_red', 'an old red brick wall of a nineteenth-century Philadelphia rowhouse, about 2.4 metres across and '
     'about thirty courses high: standard American bricks in running bond, bricks varying from orange-red to deep red with '
     'a few purplish-brown ones, slightly worn edges, light grey lime mortar joints about one centimetre wide and slightly '
     'recessed, faint soot and weathering'),
    ('wall_brick_dark', 'a 1920s apartment building wall of dark brown and charcoal wire-cut brick in running bond, about '
     '2.4 metres across and about thirty courses high, dark grey mortar joints, even light weathering'),
    ('wall_brick_painted', 'a painted brick rowhouse wall in Philadelphia, about 2.4 metres across and about thirty courses '
     'high: bricks in running bond under thin weathered off-white paint, the courses and mortar joints reading clearly '
     'through the paint, a few small flaked spots showing red brick, faint grime'),
    ('wall_stucco', 'a cement-parged party wall of a Philadelphia rowhouse, about three metres across: light warm grey '
     'render with faint trowel arcs, hairline cracks, small patches and faint vertical rain stains'),
    ('wall_ashlar', 'smooth buff Indiana limestone ashlar on a Philadelphia commercial building, about 3.6 metres across: '
     'rectangular blocks about 0.6 metres high and 1.2 metres long laid in courses with staggered vertical joints, thin '
     'joints, slight grey weathering and soft soot staining'),
    ('wall_formstone', 'Formstone cast-stone veneer on a South Philadelphia rowhouse, about 2.4 metres across: irregular '
     'faux fieldstone shapes in grey and beige with raised mortar joints, slightly dirty'),
    ('wall_marble', 'polished white Vermont marble ashlar of a Philadelphia civic building, about 3.6 metres across: '
     'rectangular blocks about 0.6 metres high and 1.2 metres long laid in courses with staggered vertical joints, fine '
     'grey veining and soft grey soot weathering'),
    ('wall_granite', 'grey Pennsylvania granite ashlar, rough-dressed rectangular blocks about 0.5 metres high and 1.0 metre '
     'long laid in courses with staggered vertical joints, about 3.6 metres across, speckled grey stone, fine joints'),
    ('wall_concrete', 'a weathered precast concrete wall panel of a 1960s office building, about three metres across: '
     'light grey concrete with fine exposed aggregate, small air pores, faint water stains, no joints'),
]
PITCHED = [
    ('pitch_shingle', 'charcoal grey architectural asphalt shingles on a Philadelphia twin house, about four metres across, '
     'slightly weathered with a few darker algae streaks'),
    ('pitch_slate', 'an old natural blue-grey Pennsylvania slate roof on a Victorian house, about four metres across, '
     'rectangular slates in staggered courses, a few lighter replaced slates and faint lichen'),
    ('pitch_metal', 'a painted standing-seam metal roof in dull dark green with slight chalking, the raised seams running '
     'vertically up the slope every 45 centimetres, about four metres across'),
    ('pitch_tab', 'weathered brown three-tab asphalt shingles on an older rowhouse, about four metres across, faded and '
     'patchy with a few replaced tabs'),
]
ROOFS = [
    ('roof_snow', 'a flat Philadelphia rowhouse roof under an even fresh layer of snow about five centimetres deep, about '
     'eight metres across: smooth white with faint wind ripples, a few slightly greyer thin patches and soft drifts, no '
     'footprints'),
]
JOBS = [(i, w, FRAME_WALL) for i, w in WALLS] + [(i, w, FRAME_PITCH) for i, w in PITCHED] + [(i, w, FRAME_ROOF) for i, w in ROOFS]


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


def make(key, gid, what, frame, force):
    os.makedirs(RAW, exist_ok=True)
    base = os.path.join(RAW, gid)
    if os.path.exists(base + '.png') and not force:
        return gid, 'kept'
    prompt = frame.format(what=what)
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
    jobs = [j for j in JOBS if not only or j[0] in only]
    with concurrent.futures.ThreadPoolExecutor(3) as ex:
        for gid, what in ex.map(lambda j: make(key, j[0], j[1], j[2], a.force), jobs):
            print(gid, what, flush=True)


if __name__ == '__main__':
    main()
