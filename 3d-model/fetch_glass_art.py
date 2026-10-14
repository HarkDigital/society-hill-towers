#!/usr/bin/env python3
"""Generate the glass towers' curtain walls and the rooms behind them (Round 191, Mike: "Can we also update the glass
textures of the skyscrapers that are glass?"), from OpenAI's image API, written to lidar_cache/glass_art_raw/<stage>/<id>.png
with a sidecar <id>.json (the prompt, the model, the size, when, the usage, and for an edit the template's sha).
bake_glass_art.py cuts them into the atlases the curtain-wall shader reads (glass_systems.json names the systems).

Two stages:
- 'frames': one straight-on elevation a curtain-wall system (glass_systems.json's sixteen), a few storeys by a few bays of
  its own module repeating, every pane of vision glass a flat chroma-key green (#00FF00) and every opaque spandrel or
  railing pane a flat magenta (#FF00FF), so the bake finds the glass to the pixel; everything else (the mullions, caps,
  fins, slab covers, stone and metal panels, frit dots) in its own colour under flat overcast light. The glass itself is
  never painted: the page draws it (its reflection, its tint, the room behind it).
- 'rooms': eight interiors through /v1/images/edits on a one-point perspective template the bake draws (bake_glass_art.py
  room_template: the back wall a centred rectangle at half the image's size, the floor, the ceiling and the side walls the
  trapezoids round it), so every room's edges sit where the page's interior mapping expects them.

The key is read from OPENAI_API_KEY or ~/.config/philly3d/openai.env (KEY=value lines), never from the repo, and is never
printed. An image already on disk is kept; pass --force to make it again, or --only <id>[,<id>] to make some.
GLASS_ART_MODEL picks the model (default gpt-image-2), GLASS_ART_QUALITY the quality (default high). Every prompt asks for
no lettering, no logos and no people.

Usage: python3 fetch_glass_art.py [--stage frames|rooms] [--only id,...] [--force] [--list] [--workers 4]"""
import argparse, concurrent.futures, hashlib, io, json, os, sys
import fetch_storefront_art as SF   # the API plumbing: api_key, call, multipart, save

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'lidar_cache', 'glass_art_raw')
SYSTEMS = os.path.join(HERE, 'glass_systems.json')
MODEL = os.environ.get('GLASS_ART_MODEL', 'gpt-image-2')
QUALITY = os.environ.get('GLASS_ART_QUALITY', 'high')

FRAME = ('Seamless tileable facade texture for a 3D city model: a perfectly orthographic, straight-on elevation of a section '
         'of {what}, exactly {nf} storeys tall and {nb} bays wide, repeating seamlessly in both directions (what leaves the '
         'right edge comes back at the left, what leaves the top comes back at the bottom; every floor line and bay line '
         'evenly spaced, every bay identical, every storey identical). Every pane of vision glass is one perfectly flat, '
         'uniform chroma-key green (#00FF00): no reflection, no gradient, no texture, nothing behind it. {magenta}Everything '
         'else ({rest}) is photographed in flat, even overcast daylight with no cast shadows, at its true colour. No ground '
         'floor, no roof, no sky, no building edges or corners, no perspective, no people, no lettering, no logos.')
MAGENTA = 'Every opaque {what} is one perfectly flat, uniform magenta (#FF00FF). '

# per system: what the wall is, what the magenta is (or None), what the rest is, bays and storeys drawn, the image size.
# Bays and storeys are chosen so the drawn wall's proportions are about the image's, a whole number of the system's module
FRAMES = {
    0: ('the unitized curtain wall of a 2008 Philadelphia office skyscraper: modules 1.5 m wide by 4.15 m tall, one '
        'floor-to-ceiling vision pane per module, a 1.25 m shadow-box spandrel band of glass at each floor slab, flush slim '
        'silver-grey aluminium joints 5 cm wide between every unit, no projecting caps',
        'shadow-box spandrel glass panel', 'the slim silver-grey aluminium joints', 10, 4, '1024x1024'),
    1: ('the unitized curtain wall of a 2018 Philadelphia skyscraper: units 1.52 m wide by 4.42 m tall, a tall '
        'floor-to-ceiling vision pane and a 0.75 m back-painted spandrel glass band at each floor slab, a slender light '
        'silver vertical aluminium cap 8 cm wide projecting 10 cm on every unit joint, slim flush horizontal joints',
        'back-painted spandrel glass band', 'the light silver vertical caps and the slim joints', 10, 4, '1024x1024'),
    2: ('a 1987 stick-built curtain wall of a Philadelphia skyscraper: silver anodised aluminium caps 6.5 cm wide projecting '
        'both ways in a 1.5 m by 4 m grid, a 2.9 m vision pane and a 1.1 m spandrel glass panel at each floor, and every '
        'third floor instead of the spandrel glass a 1.4 m band of polished blue-grey granite running across the whole width',
        'spandrel glass panel (not the granite bands)', 'the silver caps and the polished blue-grey granite bands', 10, 6,
        '1024x1536'),
    3: ('a 2005 silver glass curtain wall: large flush panes 1.8 m wide by 2.9 m tall separated only by thin dark structural '
        'silicone joints 2 cm wide, a 1.1 m shadow-box spandrel band of the same flush glass at each floor slab, no mullion '
        'caps and no visible frames', 'shadow-box spandrel glass panel', 'the thin dark silicone joints', 9, 4, '1024x1024'),
    4: ('a 2016 office curtain wall: units 1.52 m wide by 4.0 m tall with floor-to-ceiling vision glass, a 0.6 m pale grey '
        'back-painted spandrel glass panel and below it a 30 cm pale brushed aluminium channel at each floor slab, slim light '
        'grey vertical caps 5 cm wide on every unit joint', 'back-painted spandrel glass panel',
        'the pale aluminium slab channels and the slim light grey caps', 10, 4, '1024x1024'),
    5: ('a glazed lantern of large clear low-iron glass panes 1.5 m wide by 4 m tall held in slim white aluminium frames',
        None, 'the slim white aluminium frames', 10, 4, '1024x1024'),
    6: ('a dark office curtain wall: black anodised aluminium mullions 10 cm wide projecting 12 cm in a 1.52 m by 3.8 m grid, '
        'a 2.6 m vision pane and a 1.2 m black back-painted spandrel glass panel at each floor',
        'back-painted spandrel glass panel', 'the black anodised mullions and transoms', 10, 4, '1024x1024'),
    7: ('a 1970s concrete office tower: continuous bands of smooth white precast concrete 1.55 m tall alternating with '
        'continuous ribbon windows 2.1 m tall divided by thin dark bronze mullions every 1.5 m',
        None, 'the white precast concrete bands and the thin dark bronze mullions', 10, 6, '1024x1536'),
    8: ('the window wall of a 2015 residential high-rise: floor-to-ceiling glass panels 1.5 m wide in slim grey aluminium '
        'frames 6 cm wide, one panel in every four with an operable vent sash in its lower part under a transom at 2.1 m, and '
        'a 40 cm white painted concrete slab edge cover at each floor', None,
        'the slim grey frames, the vent sash frames and the white slab edge covers', 8, 4, '1024x1024'),
    9: ('a 2015 residential high-rise with continuous balconies: floor-to-ceiling glass panels and sliding doors 1.5 m wide in '
        'slim grey frames, behind a 25 cm white concrete balcony slab edge at each floor and a 1.1 m tall frameless glass '
        'balcony railing standing on the slab edge in front of the lower part of the glass',
        'pane of frameless balcony railing glass', 'the slim grey frames and the white slab edges', 10, 4, '1024x1024'),
    10: ('a 2020 residential tower: floor-to-ceiling glass in slim white frames behind projecting white aluminium fins 15 cm '
         'deep, the fins alternately 0.75 m and 1.5 m apart, and a 50 cm white slab band at each floor', None,
         'the white aluminium fins, their edges and the white slab bands', 8, 4, '1024x1024'),
    11: ('a 2019 residential tower of low-iron glass: floor-to-ceiling glass panels 1.5 m wide in slim grey frames, and at '
         'every slab a 1.2 m spandrel glass panel covered by a dense pattern of small grey ceramic frit dots that thins out '
         'over the lower 1.2 m of the vision glass above it (the dots drawn grey, the clear gaps between them green in the '
         'vision glass and magenta in the spandrel)', 'spandrel glass between the frit dots',
         'the slim grey frames and the grey frit dots', 10, 4, '1024x1024'),
    12: ('an office curtain wall of tinted reflective glass in horizontal bands: silver vertical aluminium caps 6 cm wide '
         'every 1.52 m, a 2.76 m vision pane and a 1.2 m opaque spandrel glass panel flush with it at each floor',
         'opaque spandrel glass panel', 'the silver vertical caps and the slim horizontal joints', 10, 4, '1024x1024'),
    13: ('an office curtain wall of gold reflective glass: bronze anodised aluminium mullions 6 cm wide in a 1.52 m by 3.96 m '
         'grid, a vision pane and a 1.2 m spandrel panel of the same glass at each floor', 'spandrel glass panel',
         'the bronze anodised mullions and transoms', 10, 4, '1024x1024'),
    14: ('the unitized curtain wall of a 2010s office tower: units 1.52 m wide by 4.1 m tall, a tall vision pane and a 0.9 m '
         'shadow-box spandrel band of glass at each floor slab, slim dark grey aluminium frames 5 cm wide round every unit',
         'shadow-box spandrel glass panel', 'the slim dark grey aluminium frames', 10, 4, '1024x1024'),
    15: ('a hotel tower wall of two 1.5 m bays of floor-to-ceiling glass in slim grey frames, then a 1.5 m wide vertical strip '
         'of grey metal panels, repeating across the wall; a thin grey metal band at each floor', None,
         'the slim grey frames, the grey metal panel strips and the floor bands', 9, 4, '1024x1024'),
}

# the rooms: what the edit paints into the template, and the kind the page deals it to
ROOMS = [
    ('office-a', 'office', 'open-plan office with rows of white desks and task chairs, grey carpet tile and long suspended '
     'linear LED light fixtures'),
    ('office-b', 'office', 'open-plan office with long benching desks, a glass-walled meeting room at the back and pendant '
     'lights over a polished concrete floor'),
    ('office-c', 'office', 'private office with a wood desk, a desk chair, a low bookshelf and square ceiling downlights'),
    ('office-d', 'office', 'conference room with a long table and chairs, a blank dark wall screen switched off, and ceiling '
     'downlights'),
    ('home-a', 'home', 'apartment living room with a sofa, a rug, a coffee table and a lit floor lamp, curtains at the sides'),
    ('home-b', 'home', 'apartment bedroom with a made bed, lit bedside lamps on both sides and curtains at the sides'),
    ('hotel-a', 'hotel', 'hotel room with two beds against a padded headboard wall, wall lamps lit above them'),
    ('mech-a', 'mech', 'unfinished concrete floor of an office building with bare columns, exposed ductwork and a few work '
     'lights'),
]
ROOM = ('Repaint this exact layout as a photorealistic {room}. The picture is a one-point perspective view straight into the '
        'room from its window wall: the back wall is the flat rectangle in the middle, the floor, the ceiling and the two side '
        'walls are the four trapezoids around it, and every edge must stay exactly where it is drawn. Camera at mid height, '
        'level; no window frame, no glass, no reflections. Evening: the room\'s own lights are on. No people, no text, no '
        'logos, no readable screens.')


def frame_cells():
    sysd = json.load(open(SYSTEMS))['systems']
    out = []
    for s in sysd:
        k = s['id']
        what, mg, rest, nb, nf, size = FRAMES[k]
        prompt = FRAME.format(what=what, nf=nf, nb=nb, rest=rest, magenta=MAGENTA.format(what=mg) if mg else '')
        out.append(('sys%02d-%s' % (k, s['name']), prompt, size, nb, nf))
    return out


def make_frame(key, cid, prompt, size, force):
    d0 = os.path.join(RAW, 'frames')
    os.makedirs(d0, exist_ok=True)
    png, meta = os.path.join(d0, cid + '.png'), os.path.join(d0, cid + '.json')
    if os.path.exists(png) and not force:
        return cid, 'kept'
    body = json.dumps({'model': MODEL, 'prompt': prompt, 'size': size, 'quality': QUALITY, 'n': 1,
                       'output_format': 'png', 'background': 'opaque'}).encode()
    d, err = SF.call(key, SF.API, body, 'application/json')
    if not d:
        return cid, err
    SF.MODEL, SF.QUALITY = MODEL, QUALITY
    n = SF.save(png, meta, d, {'id': cid, 'stage': 'frames', 'prompt': prompt, 'size': size})
    return cid, 'made %d KB' % (n // 1024)


def make_room(key, rid, what, force):
    from bake_glass_art import room_template
    d0 = os.path.join(RAW, 'rooms')
    os.makedirs(d0, exist_ok=True)
    png, meta = os.path.join(d0, rid + '.png'), os.path.join(d0, rid + '.json')
    if os.path.exists(png) and not force:
        return rid, 'kept'
    tpl, msk = room_template()
    tb, mb = io.BytesIO(), io.BytesIO()
    tpl.save(tb, 'PNG'); msk.save(mb, 'PNG')
    tb, mb = tb.getvalue(), mb.getvalue()
    prompt = ROOM.format(room=what)
    fields = {'model': MODEL, 'prompt': prompt, 'size': '%dx%d' % tpl.size, 'quality': QUALITY, 'n': '1', 'input_fidelity': 'high'}
    body, ct = SF.multipart(fields, {'image': ('template.png', tb, 'image/png'), 'mask': ('mask.png', mb, 'image/png')})
    d, err = SF.call(key, SF.API_EDIT, body, ct)
    if not d and err and 'input_fidelity' in err:   # a model that takes no fidelity setting
        fields.pop('input_fidelity')
        body, ct = SF.multipart(fields, {'image': ('template.png', tb, 'image/png'), 'mask': ('mask.png', mb, 'image/png')})
        d, err = SF.call(key, SF.API_EDIT, body, ct)
    if not d:
        return rid, err
    SF.MODEL, SF.QUALITY = MODEL, QUALITY
    n = SF.save(png, meta, d, {'id': rid, 'stage': 'rooms', 'prompt': prompt, 'size': '%dx%d' % tpl.size,
                                'template_sha': hashlib.sha256(tb).hexdigest()[:16]})
    return rid, 'made %d KB' % (n // 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='frames', choices=('frames', 'rooms'))
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    only = set(filter(None, a.only.split(',')))
    if a.stage == 'rooms':
        jobs = [r for r in ROOMS if not only or r[0] in only]
        if a.list:
            for r in jobs:
                print(r[0], r[1])
            return
        key = SF.api_key()
        run = lambda r: make_room(key, r[0], r[2], a.force)
    else:
        jobs = [c for c in frame_cells() if not only or c[0] in only or c[0][:5] in only]
        if a.list:
            for c in jobs:
                print(c[0], c[2], '%d bays x %d storeys' % (c[3], c[4]))
            return
        key = SF.api_key()
        run = lambda c: make_frame(key, c[0], c[1], c[2], a.force)
    print('%d images, stage %s, model %s, quality %s' % (len(jobs), a.stage, MODEL, QUALITY), flush=True)
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for cid, what in ex.map(run, jobs):
            print(cid, what, flush=True)


if __name__ == '__main__':
    main()
