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
# the streets' detail textures (Round 184) cover less ground: their own frames say how much
FRAME_STREET = ('Seamless tileable texture for a 3D city model: a photograph taken looking straight down at {what}, filling '
                'the whole frame evenly. No perspective, no shadows of objects, no paint markings, no objects, no edges or '
                'borders. Soft even overcast daylight. Natural colours, photorealistic, uniform detail across the whole image '
                'so it repeats without a visible seam.')
# the woods from the air (the realism pass): the frame a canopy texture is made in, 80 m of closed forest straight down
CANOPY = ('Seamless tileable aerial orthophoto taken straight down from 600 metres over dense mixed deciduous forest in '
          'Fairmount Park, Philadelphia, {season}, about 80 metres across the frame. No ground visible except where the season '
          'bares it, no paths, no roads, no buildings, no water, no clearings, no text, no vignette; uniform density and '
          'exposure across the whole image so it repeats without a visible seam. Photorealistic.')
GROUNDS = [
    ('lawn', 'a mown park lawn in a Philadelphia city park in summer: dense green turf grass with slight variation in '
     'tone, a few clover patches'),
    ('meadow', 'a rougher, less tended urban grass verge in late summer: grass of mixed greens and straw-dry blades, '
     'clover, a few dandelion leaves and small patches of bare brown soil showing through'),
    ('asphalt', 'a patch of worn city street asphalt about four metres across: fine dark grey aggregate, a few darker '
     'tar-sealed cracks and a slightly lighter repaired patch, no lane markings', 'street'),
    ('concrete', 'a concrete city sidewalk about three metres across: four square slabs with tooled joints between them, '
     'light grey with faint stains and wear', 'street'),
    ('bricks', 'an old red brick sidewalk in Society Hill, Philadelphia, about two metres across: bricks laid in a '
     'herringbone pattern, weathered, some darker and some lighter, fine sand in the joints', 'street'),
    # Round 185 (Mike: make it look photo realistic; he chose roof and ground textures): the flat roofs' four and the yards'
    ('roof_tar', 'an old flat rowhouse roof of black modified bitumen in Philadelphia, about eight metres across: dark '
     'charcoal with a few irregular lighter repair patches, faint tar-sealed cracks and a little dust, no regular seams', 'roof'),
    ('roof_silver', 'a flat rowhouse roof coated with silver aluminium roof paint in Philadelphia, about eight metres across: '
     'weathered silver grey with darker streaks, brush marks and a few small patches, no regular seams', 'roof'),
    ('roof_white', 'a white TPO membrane flat roof of a commercial building, about eight metres across: off-white with grey dirt '
     'streaks, scuffs and a few faint irregular welded seams', 'roof'),
    ('roof_gravel', 'a ballasted flat roof covered in loose grey and tan river gravel, about eight metres across, uniform', 'roof'),
    # the realism round two (R4): three more of each kind, what a Philadelphia flat roof carries at 8 m (the four above stay
    # its variant 0); bake_ground_art.py takes every one to its kind's own mean, so only the near roofs change
    ('roof_tar_1', 'an old flat rowhouse roof of black modified bitumen in Philadelphia, about eight metres across, patched '
     'many times: several large irregular patches of newer, blacker membrane lapped over the faded charcoal sheet, their '
     'edges sealed with glossy lines of tar, a few smaller dabs of roof cement and faint cracks', 'roofvar'),
    ('roof_tar_2', 'an old flat rowhouse roof of black modified bitumen in Philadelphia, about eight metres across: dark '
     'charcoal with two or three broad irregular pale grey dried ponding stains where rainwater stood, rings of fine silt '
     'and dust at their edges, faint tar-sealed cracks', 'roofvar'),
    ('roof_tar_3', 'a flat roof of dark grey granulated cap sheet in Philadelphia, about eight metres across, laid in wide '
     'overlapping strips with a few long lapped seams running at slightly different angles, tar bleeding out along them, '
     'one small round metal roof drain with a black ring of tar around it, a little dust', 'roofvar'),
    ('roof_silver_1', 'a flat rowhouse roof in Philadelphia, about eight metres across, its silver aluminium roof coating '
     'old and worn thin: weathered silver grey with the black bitumen beneath showing through in irregular dark patches and '
     'along cracks, brush marks', 'roofvar'),
    ('roof_silver_2', 'a flat rowhouse roof coated with silver aluminium roof paint in Philadelphia, about eight metres '
     'across: weathered silver grey with two broad brownish grey dried ponding stains and rings of dirt where water stood, a '
     'darker streak running to a small round drain', 'roofvar'),
    ('roof_silver_3', 'a flat rowhouse roof coated with silver aluminium roof paint in Philadelphia, about eight metres '
     'across: older dull silver with a few irregular, brush-edged patches of fresher, brighter silver coating over repairs, '
     'two narrow strips of silver seam tape, scattered small dark spots of tar', 'roofvar'),
    ('roof_white_1', 'a white TPO membrane flat roof of a commercial building, about eight metres across: off-white sheets '
     'joined by long welded seams and a few strips of seam tape at irregular spacing, grey dirt tracks where people walk, '
     'scuffs', 'roofvar'),
    ('roof_white_2', 'a white TPO membrane flat roof of a commercial building, about eight metres across: off-white, '
     'weathered and evenly dulled by fine grey dust, with soft, faint, irregular tan grey ponding marks spread thinly over '
     'much of the surface, no distinct spots, a few faint seams', 'roofvar'),
    ('roof_white_3', 'a white TPO membrane flat roof of a commercial building, about eight metres across: off-white with '
     'several rectangular welded repair patches a little whiter than the weathered sheet around them, grey scuffed foot '
     'paths and fine dust', 'roofvar'),
    ('roof_gravel_1', 'a ballasted flat roof covered in loose grey and tan river gravel, about eight metres across, the '
     'stones spread thinner in a few small irregular places where the dark membrane beneath shows through', 'roofvar'),
    ('roof_gravel_2', 'a ballasted flat roof covered in loose grey and tan river gravel, about eight metres across, the '
     'stones finer and more silted in broad irregular low areas, darker grey brown silt between them, uniform', 'roofvar'),
    ('roof_gravel_3', 'a ballasted flat roof covered in loose grey and tan river gravel, about eight metres across, with '
     'darker patches of silt and a little green moss in the low spots and the stones piled more thickly in places', 'roofvar'),
    ('yard','the ground of urban backyards and a vacant lot in Philadelphia, about ten metres across: a patchwork of cracked '
     'grey concrete, bare packed brown dirt, patches of weeds and grass and a little gravel, no fences, no objects'),
    # the realism pass (Mike: "make this look more photo realistic and less cartoony ... all surfaces/water/anything"): the
    # ground's broad variation from the air, the woods' canopy by season, the river banks and the yards (tidemud, litter
    # and snow were made and looked at; bake_ground_art.py does not use them)
    ('parkmacro', 'Seamless tileable aerial orthophoto taken straight down from 1,500 metres over a 240-metre-wide stretch of '
     'mown municipal parkland turf in Philadelphia in early October, soft high-overcast light. Only large-scale variation: '
     'lighter dry straw-tinted patches on the rises, darker greener damp swales, faint pale desire lines of worn grass and '
     'compacted soil, a subtle irregular mowing pattern. No trees, no tree shadows, no paved paths, no buildings, no people, '
     'no water, no sports markings, no text, no vignette; uniform exposure edge to edge so it repeats without a visible '
     'seam. Photorealistic.', 'aerial'),
    ('canopy_summer', CANOPY.format(season='in midsummer: a closed canopy of individual rounded tree crowns 8 to 18 metres '
     'across packed edge to edge (oak, tulip poplar, beech, maple), sunlit crown tops with natural soft shadow in the gaps '
     'between crowns, varied greens from dark to yellow-green'), 'aerial'),
    ('canopy_autumn', CANOPY.format(season='in late October: a closed canopy of individual rounded tree crowns 8 to 18 metres '
     'across packed edge to edge, mostly green and olive crowns with scattered yellow, orange, russet and a few red crowns, '
     'natural slightly muted colour, soft shadow in the gaps between crowns'), 'aerial'),
    ('canopy_winter', CANOPY.format(season='in winter with every deciduous tree bare: a grey-brown mesh of branches and twigs '
     'of crowns 8 to 18 metres across, the brown leaf-litter forest floor visible between them, a few dark green conifer '
     'crowns'), 'aerial'),
    ('riprap', 'a river bank armoured with riprap on the Schuylkill River in Philadelphia, about six metres across: tightly '
     'packed angular grey granite and brown sandstone boulders thirty to eighty centimetres across, dark damp gaps between '
     'them, a thin film of dried grey river silt on the lower stones, a few small tufts of grass in the joints'),
    ('tidemud', 'the tidal edge of the Delaware River at low tide, about six metres across: smooth wet grey-brown silt and mud '
     'with scattered pebbles, broken mussel shells and a few strands of dark river weed, glistening wet patches'),
    ('litter', 'a mown city park lawn in early November, about three metres across, covered unevenly by fallen leaves: maple, '
     'oak and London plane leaves in brown, tan, yellow and orange lying flat over green grass, thicker in some places than '
     'others'),
    ('alley', 'the ground behind Philadelphia rowhouses seen from above, about ten metres across: cracked grey concrete back '
     'patios of different ages separated by thin seams, a strip of patched asphalt alley, small squares of bare dirt with '
     'weeds, a few darker stains and drain grates; no fences, no walls, no objects, no people'),
    ('snow', 'fresh undisturbed snow about five centimetres deep on a flat open city lot in Philadelphia, about six and a half '
     'metres across: soft white with faint blue-grey wind undulations, tiny ice-crystal glints, a few softened half-filled '
     'footprints, no grass showing, no objects'),
]
# the roofs' frame (Round 185): a drone's view straight down at a roof surface, nothing standing on it
FRAME_ROOF = ('Seamless tileable texture for a 3D city model: an aerial photograph taken by a drone looking straight down at '
              '{what}, filling the whole frame evenly. No perspective, no parapets, no edges or borders, no vents, no '
              'skylights, no HVAC units, no shadows of objects, no objects. Soft even overcast daylight. Natural colours, '
              'photorealistic, uniform detail across the whole image so it repeats without a visible seam.')
# the realism round two: the variants' frame, the same with room for what lies flat in the surface (a drain, a patch, tape)
FRAME_ROOF_VAR = ('Seamless tileable texture for a 3D city model: an aerial photograph taken by a drone looking straight down '
                  'at {what}, filling the whole frame evenly. No perspective, no parapets, no walls, no roof edges, no borders '
                  'or frame, no vents, no skylights, no HVAC units, no pipes, nothing standing on the roof and no shadows of '
                  'objects: only what lies flat in the roof surface itself. No text, no lettering, no painted markings, no '
                  'logos. Soft even overcast daylight. Natural colours, photorealistic, the detail spread across the whole '
                  'image so it repeats without a visible seam.')


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


def make(key, gid, what, force, kind=None):
    os.makedirs(RAW, exist_ok=True)
    base = os.path.join(RAW, gid)
    if os.path.exists(base + '.png') and not force:
        return gid, 'kept'
    prompt = what if kind == 'aerial' else (FRAME_STREET if kind == 'street' else FRAME_ROOF if kind == 'roof' else FRAME_ROOF_VAR if kind == 'roofvar' else FRAME).format(what=what)
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
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        for gid, what in ex.map(lambda g: make(key, g[0], g[1], a.force, g[2] if len(g) > 2 else None), jobs):
            print(gid, what, flush=True)


if __name__ == '__main__':
    main()
