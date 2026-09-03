#!/usr/bin/env python3
"""Street-level imagery for the wall-colour pass: list every Mapillary image over the
outer-districts and south boxes from the z14 vector tiles, then pull every kept image's
256 px thumbnail, so bake_wall_colors.py can read the colour of the walls that flank
each street. Mapillary imagery is CC BY-SA 4.0 (DATA-LICENSE.md, the credit line).

Boxes (lat S..N, lon W..E):
  wide   39.915..39.986, -75.188..-75.118   the outer districts (scene_wide.json)
  south  39.890..39.9155, -75.190..-75.100  the stadium district and the port (scene_south.json)
Listing: GET https://tiles.mapillary.com/maps/vtp/mly1_public/2/14/{x}/{y}, the Mapbox
vector tile whose "image" layer is a point per image with captured_at, compass_angle, id
and is_pano (decoded here with a stdlib protobuf reader; one tile is ~10 MB and lists
~170k images in Center City). The Graph API's bbox search was the first draft and is
gone: it answers "reduce the amount of data" (HTTP 500) for whole neighbourhoods
however small the box or the limit. Thumbnail URLs come afterwards in batches of 50
from GET https://graph.mapillary.com/?ids=...&fields=thumb_256_url.
The token comes from the MAPILLARY_TOKEN environment variable (a client token from the
developer dashboard, 'MLY|<app id>|<hex>'); it travels in the Authorization header (the
tile server takes it as access_token) and is never written to disk or provenance.jsonl.

Resumable: lidar_cache/mly_tiles/<tile>.json per z14 tile (written atomically, skipped
when present, delete one to refetch it), lidar_cache/mly_thumbs/<id>.jpg per image
(skipped when present; a thumb URL that has expired is refreshed from the entity
endpoint). 429 and 5xx answers back off and retry; a bad token stops the run.
Panoramas are dropped. --max-images (default 40000) caps the thumbnails: when the boxes
list more, the pick round-robins across tiles taking the newest image of each 10 m cell
first, so the cap thins dashcam sequences rather than dropping whole streets.
Output lidar_cache/mly_images.json:
  {"images": [{"id", "x", "z", "compass_angle", "captured_at"}, ...], ...}
x, z in the model frame (philly_frame.py), compass_angle degrees clockwise from north,
captured_at ms since the epoch. Only images whose thumbnail is on disk are listed.

--dry-run: no network, no token. Synthesises 300 images along a few streets of
scene_wide.json / scene_south.json with a known wall colour per block face and writes
them under lidar_cache/mly_dry/ (thumbs as JPEGs when Pillow imports, the colours inline
in the records when it does not) plus truth.json, so bake_wall_colors.py --dry-run can be
checked end to end without a token. Plain python3; Pillow optional."""
import argparse, gzip, json, math, os, random, struct, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
try:
    import provenance   # append-only fetch log (3d-model/provenance.jsonl); optional
except Exception:
    provenance = None
from philly_frame import to_xz

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
CACHE = 'lidar_cache'
TILE_DIR = os.path.join(CACHE, 'mly_tiles')
THUMB_DIR = os.path.join(CACHE, 'mly_thumbs')
OUT = os.path.join(CACHE, 'mly_images.json')
DRY_DIR = os.path.join(CACHE, 'mly_dry')

API = 'https://graph.mapillary.com'
TILES = 'https://tiles.mapillary.com/maps/vtp/mly1_public/2'
TILE_Z = 14              # the zoom whose "image" layer carries every image as a point
BATCH = 50               # ids per thumbnail-URL lookup
BOXES = [                # name, lat S, lat N, lon W, lon E
    ('wide', 39.915, 39.986, -75.188, -75.118),
    ('south', 39.890, 39.9155, -75.190, -75.100),
]
USER_AGENT = 'sht-3d-model/1.0 (philly3d.com wall-colour pass)'
TOKEN = os.environ.get('MAPILLARY_TOKEN', '').strip()


# ---------------- tiles ----------------
def lon2x(lon, z=TILE_Z):
    return (lon + 180.0) / 360.0 * (1 << z)


def lat2y(lat, z=TILE_Z):
    r = math.radians(lat)
    return (1.0 - math.log(math.tan(r) + 1.0 / math.cos(r)) / math.pi) / 2.0 * (1 << z)


def tile_lonlat(x, y, px, py, extent, z=TILE_Z):
    """Tile-local integer coordinates -> (lon, lat)."""
    n = 1 << z
    lon = (x + px / extent) / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * (y + py / extent) / n))))
    return lon, lat


def z14_tiles():
    """[(tile id, x, y), ...]: every z14 tile any box touches, each once."""
    seen, tiles = set(), []
    for name, S, N, W, E in BOXES:
        for x in range(int(lon2x(W)), int(lon2x(E)) + 1):
            for y in range(int(lat2y(N)), int(lat2y(S)) + 1):
                if (x, y) in seen:
                    continue
                seen.add((x, y))
                tiles.append((f'z{TILE_Z}-{x}-{y}', x, y))
    return tiles


def in_boxes(lon, lat):
    return any(S <= lat <= N and W <= lon <= E for _, S, N, W, E in BOXES)


# ---------------- Mapbox vector tiles (protobuf, stdlib) ----------------
def _varint(b, i):
    r = sh = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7f) << sh; sh += 7
        if c < 0x80:
            return r, i


def _fields(b):
    """(field number, wire type, value) over one protobuf message."""
    i, n = 0, len(b)
    while i < n:
        key, i = _varint(b, i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 1:
            v = b[i:i + 8]; i += 8
        elif wt == 2:
            ln, i = _varint(b, i); v = b[i:i + ln]; i += ln
        elif wt == 5:
            v = b[i:i + 4]; i += 4
        else:
            raise ValueError(f'protobuf wire type {wt}')
        yield f, wt, v


def _packed(b):
    out, i = [], 0
    while i < len(b):
        v, i = _varint(b, i); out.append(v)
    return out


def _zz(v):
    return (v >> 1) ^ -(v & 1)


def mvt_points(buf, layer_name):
    """The point features of one layer of a Mapbox vector tile:
    [(px, py, {property: value}), ...] in tile units, plus the layer's extent."""
    if buf[:2] == b'\x1f\x8b':
        buf = gzip.decompress(buf)
    for f, wt, lay in _fields(buf):
        if f != 3:
            continue
        name, keys, vals, feats, extent = '', [], [], [], 4096
        for f2, wt2, v in _fields(lay):
            if f2 == 1:
                name = v.decode('utf-8', 'replace')
            elif f2 == 3:
                keys.append(v.decode('utf-8', 'replace'))
            elif f2 == 4:
                val = None
                for f3, wt3, vv in _fields(v):
                    if f3 == 1: val = vv.decode('utf-8', 'replace')
                    elif f3 == 2: val = struct.unpack('<f', vv)[0]
                    elif f3 == 3: val = struct.unpack('<d', vv)[0]
                    elif f3 in (4, 5): val = vv
                    elif f3 == 6: val = _zz(vv)
                    elif f3 == 7: val = bool(vv)
                vals.append(val)
            elif f2 == 5:
                extent = v
            elif f2 == 2:
                feats.append(v)
        if name != layer_name:
            continue
        pts = []
        for fe in feats:
            tags, typ, geom = [], 0, []
            for f3, wt3, v in _fields(fe):
                if f3 == 2: tags = _packed(v)
                elif f3 == 3: typ = v
                elif f3 == 4: geom = _packed(v)
            if typ != 1:
                continue
            props = {keys[tags[k]]: vals[tags[k + 1]] for k in range(0, len(tags) - 1, 2)}
            x = y = 0
            i = 0
            while i < len(geom):
                cmd, cnt = geom[i] & 7, geom[i] >> 3; i += 1
                if cmd != 1:
                    break
                for _ in range(cnt):
                    x += _zz(geom[i]); y += _zz(geom[i + 1]); i += 2
                    pts.append((x, y, props))
        return pts, extent
    return [], 4096


# ---------------- Graph API ----------------
class TokenError(RuntimeError):
    pass


def api_get(url, params=None, attempts=8, timeout=90):
    """GET one Graph API page as a dict. 429 and 5xx (and network drops) back off
    5, 10, 20 ... 120 s and retry; 401/403 with an OAuth error code stop the run."""
    if params:
        url = url + ('&' if '?' in url else '?') + urllib.parse.urlencode(params)
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers={'Authorization': 'OAuth ' + TOKEN, 'User-Agent': USER_AGENT})
        wait = min(120, 5 * (2 ** attempt))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.load(r)
            if isinstance(d, dict) and 'error' in d:
                err = d['error'] if isinstance(d['error'], dict) else {'message': str(d['error'])}
                if err.get('code') == 190 or 'token' in str(err.get('message', '')).lower():
                    raise TokenError(err.get('message', 'bad token'))
                raise RuntimeError('graph error: ' + str(err)[:200])
            return d
        except TokenError:
            raise
        except urllib.error.HTTPError as e:
            body = ''
            try:
                body = e.read().decode('utf-8', 'replace')[:300]
            except Exception:
                pass
            if e.code in (400, 401, 403) and ('OAuth' in body or '"code":190' in body.replace(' ', '') or 'token' in body.lower()):
                raise TokenError(f'HTTP {e.code}: {body}')
            if e.code == 404:
                raise
            if e.code == 429:
                ra = e.headers.get('Retry-After') if e.headers else None
                try:
                    wait = max(wait, float(ra))
                except (TypeError, ValueError):
                    pass
            elif e.code < 500 and e.code != 408:
                raise RuntimeError(f'HTTP {e.code}: {body}')
            last = e
        except Exception as e:      # URLError, timeout, bad JSON, remote disconnect
            last = e
        print(f'  retry {attempt + 1}/{attempts} in {wait:.0f}s ({last})', flush=True)
        time.sleep(wait)
    raise RuntimeError(f'gave up on {url.split("?")[0]}: {last}')


def get_bytes(url, attempts=6, timeout=120):
    """One binary GET with the same back-off as api_get (the tile server)."""
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        wait = min(120, 5 * (2 ** attempt))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise TokenError(f'HTTP {e.code} from the tile server')
            if e.code == 404:
                return b''
            if e.code < 500 and e.code not in (408, 429):
                raise RuntimeError(f'HTTP {e.code}')
            last = e
        except Exception as e:
            last = e
        print(f'  retry {attempt + 1}/{attempts} in {wait:.0f}s ({last})', flush=True)
        time.sleep(wait)
    raise RuntimeError(f'gave up on {url.split("?")[0]}: {last}')


def fetch_tile(tid, x, y, delay):
    """The image layer of one z14 tile into TILE_DIR/<tid>.json (images inside the
    boxes only, still lon/lat); returns its records."""
    path = os.path.join(TILE_DIR, f'{tid}.json')
    if os.path.exists(path) and os.path.getsize(path) > 2:
        return json.load(open(path))['images']
    t0 = time.time()
    url = f'{TILES}/{TILE_Z}/{x}/{y}'
    buf = get_bytes(url + '?access_token=' + urllib.parse.quote(TOKEN, safe=''))
    pts, extent = mvt_points(buf, 'image') if buf else ([], 4096)
    recs, listed = [], len(pts)
    for px, py, pr in pts:
        lon, lat = tile_lonlat(x, y, px, py, extent)
        if not in_boxes(lon, lat):
            continue
        recs.append({'id': str(pr.get('id')), 'lon': round(lon, 7), 'lat': round(lat, 7),
                     'compass_angle': pr.get('compass_angle'), 'captured_at': pr.get('captured_at'),
                     'is_pano': bool(pr.get('is_pano'))})
    time.sleep(delay)
    with open(path + '.tmp', 'w') as f:
        json.dump({'tile': tid, 'z': TILE_Z, 'x': x, 'y': y, 'in_tile': listed, 'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'images': recs}, f, separators=(',', ':'))
    os.replace(path + '.tmp', path)
    if provenance:
        provenance.record('fetch_mapillary.tiles', url, {'layer': 'image'}, len(recs), tile=tid, in_tile=listed, bytes=len(buf))
    panos = sum(1 for r in recs if r['is_pano'])
    print(f'{tid}: {listed} images in the tile, {len(recs)} in the boxes ({panos} panos), {len(buf) / 1e6:.1f} MB, {time.time() - t0:.0f}s', flush=True)
    return recs


def resolve_thumb_urls(recs, delay):
    """Fill rec['thumb_256_url'] for every record, BATCH ids per Graph API call."""
    t0, got = time.time(), 0
    for i in range(0, len(recs), BATCH):
        chunk = recs[i:i + BATCH]
        try:
            d = api_get(f'{API}/', {'ids': ','.join(r['id'] for r in chunk), 'fields': 'thumb_256_url'})
        except TokenError:
            raise
        except Exception as e:
            print(f'  thumbnail URLs {i}..{i + len(chunk)}: {e}; those will be retried on a rerun', flush=True)
            continue
        for r in chunk:
            u = (d.get(r['id']) or {}).get('thumb_256_url') if isinstance(d, dict) else None
            if u:
                r['thumb_256_url'] = u; got += 1
        if (i // BATCH) % 100 == 99:
            print(f'  {i + len(chunk)}/{len(recs)} thumbnail URLs ({time.time() - t0:.0f}s)', flush=True)
        time.sleep(delay)
    print(f'thumbnail URLs: {got} of {len(recs)} resolved in {time.time() - t0:.0f}s', flush=True)


# ---------------- the pick ----------------
def select(per_tile, cap):
    """Round-robin across tiles, each tile ordered newest-first per 10 m cell (rank 0 of
    every cell before rank 1 of any), so the cap thins sequences evenly."""
    ordered = []
    for tid in sorted(per_tile):
        cells = {}
        for r in per_tile[tid]:
            cells.setdefault((math.floor(r['x'] / 10), math.floor(r['z'] / 10)), []).append(r)
        ranked = []
        for lst in cells.values():
            lst.sort(key=lambda r: (-(r['captured_at'] or 0), r['id']))
            ranked.extend((rank, -(r['captured_at'] or 0), r['id'], r) for rank, r in enumerate(lst))
        ranked.sort(key=lambda t: t[:3])
        ordered.append([t[3] for t in ranked])
    sel, i = [], 0
    while len(sel) < cap and any(i < len(lst) for lst in ordered):
        for lst in ordered:
            if i < len(lst):
                sel.append(lst[i])
        i += 1
    return sel[:cap]


# ---------------- thumbnails ----------------
def fetch_thumb(rec, attempts=4):
    """Download rec['thumb_256_url'] to THUMB_DIR/<id>.jpg. Returns True when the file is
    there. 403/410 (the signed URL expired) refreshes the URL once; 404 gives up."""
    path = os.path.join(THUMB_DIR, f"{rec['id']}.jpg")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return True
    url = rec.get('thumb_256_url')
    refreshed = False
    for attempt in range(attempts):
        if not url:
            return False
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if data[:2] != b'\xff\xd8':
                raise RuntimeError('not a JPEG')
            with open(path + '.tmp', 'wb') as f:
                f.write(data)
            os.replace(path + '.tmp', path)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if e.code in (403, 410) and not refreshed:
                refreshed = True
                try:
                    url = api_get(f"{API}/{rec['id']}", {'fields': 'thumb_256_url'}).get('thumb_256_url')
                    continue
                except TokenError:
                    raise
                except Exception:
                    return False
            time.sleep(2 + 3 * attempt)
        except Exception:
            time.sleep(2 + 3 * attempt)
    return False


# ---------------- dry run ----------------
WALLS = [                # sRGB as a street photo shows them
    (155, 85, 65), (132, 70, 52), (110, 60, 45), (180, 178, 170), (222, 214, 196),
    (232, 230, 224), (150, 140, 120), (190, 150, 110), (140, 150, 135), (120, 90, 70),
    (168, 96, 74), (200, 190, 176),
]
SKY, ROAD, TREE, FAR = (146, 186, 232), (70, 70, 72), (60, 110, 50), (172, 162, 150)


def polyline_length(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def along(pts, s):
    """Point and unit direction at arc length s along the polyline."""
    for i in range(len(pts) - 1):
        (ax, az), (bx, bz) = pts[i], pts[i + 1]
        L = math.hypot(bx - ax, bz - az)
        if L <= 0:
            continue
        if s <= L or i == len(pts) - 2:
            t = min(1.0, s / L)
            return (ax + (bx - ax) * t, az + (bz - az) * t), ((bx - ax) / L, (bz - az) / L)
        s -= L
    return pts[-1], (1.0, 0.0)


def compass(dx, dz):
    """Model-frame direction (x east, z south) -> degrees clockwise from north."""
    return math.degrees(math.atan2(dx, -dz)) % 360.0


def pick_streets(rng, want):
    """A few named residential streets of each scene, 150..600 m long, at least 400 m
    apart so their images cannot bleed into each other."""
    out = []
    for tag, path, n in want:
        d = json.load(open(path))
        got = []
        for ri, r in enumerate(d['roads']):
            if r.get('t') not in ('residential', 'tertiary') or not r.get('name') or len(r['pts']) < 2:
                continue
            L = polyline_length(r['pts'])
            if not 150 <= L <= 600:
                continue
            cx = sum(p[0] for p in r['pts']) / len(r['pts']); cz = sum(p[1] for p in r['pts']) / len(r['pts'])
            if any(math.hypot(cx - gx, cz - gz) < 400 for _, _, _, _, gx, gz in got + out):
                continue
            got.append((tag, ri, r['name'], r['pts'], cx, cz))
            if len(got) >= n:
                break
        out += got
    return out


def make_thumb(path, left, right, rng, tree):
    """A 256 x 192 street view: sky, a wall on each flank with its own skyline and its own
    kerb line, the road and a far facade in the middle third, a tree now and then. The
    35..65 % band of each flank therefore holds some sky and some road around the wall,
    which is what the bake must discard."""
    from PIL import Image, ImageDraw
    w, h = 256, 192
    im = Image.new('RGB', (w, h), SKY)
    dr = ImageDraw.Draw(im)
    third = w // 3
    for x0, x1, col in ((0, third, left), (2 * third, w, right)):
        top = int(h * rng.uniform(0.12, 0.42))
        kerb = int(h * rng.uniform(0.58, 0.72))
        dr.rectangle([x0, top, x1 - 1, kerb], fill=col)
        dr.rectangle([x0, kerb, x1 - 1, h - 1], fill=ROAD)
    dr.rectangle([third, int(h * 0.48), 2 * third - 1, int(h * 0.58)], fill=FAR)
    dr.rectangle([third, int(h * 0.58), 2 * third - 1, h - 1], fill=ROAD)
    if tree:
        dr.ellipse([8, int(h * 0.30), third - 4, int(h * 0.60)], fill=TREE)
    im.save(path, quality=88)


def dry_run(n_images=300, seed=7):
    rng = random.Random(seed)
    try:
        from PIL import Image  # noqa: F401
        have_pil = True
    except ImportError:
        have_pil = False
    thumbs = os.path.join(DRY_DIR, 'thumbs')
    os.makedirs(thumbs, exist_ok=True)
    streets = pick_streets(rng, [('wide', 'scene_wide.json', 4), ('south', 'scene_south.json', 2)])
    if not streets:
        sys.exit('dry run: no streets found in the scene files')
    total = sum(polyline_length(s[3]) for s in streets)
    truth, images, n = [], [], 0
    t_base = 1717200000000                              # 2024-06-01 in ms
    for k, (tag, ri, name, pts, _, _) in enumerate(streets):
        L = polyline_length(pts)
        cols = rng.sample(WALLS, 2)
        truth.append({'file': tag, 'road': ri, 'name': name, 'L': list(cols[0]), 'R': list(cols[1])})
        count = max(6, round(n_images * L / total)) if k < len(streets) - 1 else n_images - n
        for m in range(count):
            if n >= n_images:
                break
            s = (m + 0.5) * L / count
            (px, pz), (dx, dz) = along(pts, s)
            lx, lz = dz, -dx                            # the left of the segment's own direction
            forward = m % 2 == 0
            cx, cz = (dx, dz) if forward else (-dx, -dz)
            if m % 7 == 3:                              # a sideways view at one flank
                look_left = (m // 7) % 2 == 0
                cx, cz = (lx, lz) if look_left else (-lx, -lz)
                face = cols[0] if look_left else cols[1]
                l_rgb = r_rgb = face
            else:
                l_rgb, r_rgb = (cols[0], cols[1]) if forward else (cols[1], cols[0])
            # a car in the right lane of its travel direction, with a little jitter
            rx, rz = -cz, cx
            x = px + rx * 2.5 + rng.uniform(-0.6, 0.6)
            z = pz + rz * 2.5 + rng.uniform(-0.6, 0.6)
            rec = {'id': f'dry{n:05d}', 'x': round(x, 1), 'z': round(z, 1),
                   'compass_angle': round((compass(cx, cz) + rng.uniform(-6, 6)) % 360, 1),
                   'captured_at': t_base + n * 1000}
            if have_pil:
                make_thumb(os.path.join(thumbs, rec['id'] + '.jpg'), l_rgb, r_rgb, rng, tree=(n % 5 == 0))
            else:
                rec['rgb_l'], rec['rgb_r'] = list(l_rgb), list(r_rgb)
            images.append(rec)
            n += 1
    out = os.path.join(DRY_DIR, 'mly_images.json')
    with open(out, 'w') as f:
        json.dump({'src': 'synthetic dry run of fetch_mapillary.py (no Mapillary data)', 'dry_run': True,
                   'seed': seed, 'thumbs': 'thumbs/' if have_pil else None, 'images': images}, f, separators=(',', ':'))
    with open(os.path.join(DRY_DIR, 'truth.json'), 'w') as f:
        json.dump({'streets': truth}, f, indent=1)
    for t in truth:
        print(f"  {t['file']} road {t['road']} {t['name']}: L {t['L']} R {t['R']}", flush=True)
    print(f'dry run: {len(images)} synthetic images on {len(streets)} streets -> {out}'
          f' ({"JPEG thumbs" if have_pil else "no Pillow: colours inline in the records"})', flush=True)


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--max-images', type=int, default=40000, help='thumbnail cap (default 40000)')
    ap.add_argument('--delay', type=float, default=0.3, help='seconds between search pages (default 0.3)')
    ap.add_argument('--workers', type=int, default=6, help='parallel thumbnail downloads (default 6)')
    ap.add_argument('--dry-run', action='store_true', help='no network: synthesise test images under lidar_cache/mly_dry/')
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
        return
    if not TOKEN:
        sys.exit('MAPILLARY_TOKEN is not set (a client token from https://www.mapillary.com/dashboard/developers); '
                 'use --dry-run to test without one')
    os.makedirs(TILE_DIR, exist_ok=True)
    os.makedirs(THUMB_DIR, exist_ok=True)
    tiles = z14_tiles()
    todo = [t for t in tiles if not os.path.exists(os.path.join(TILE_DIR, f'{t[0]}.json'))]
    print(f'{len(tiles)} z{TILE_Z} tiles ({len(todo)} to fetch), cap {a.max_images} images', flush=True)
    per_tile, listed, panos, seen = {}, 0, 0, set()
    for tid, x, y in tiles:
        try:
            recs = fetch_tile(tid, x, y, a.delay)
        except TokenError as e:
            sys.exit(f'Mapillary rejected the token: {e}')
        keep = []
        for r in recs:
            listed += 1
            if r['is_pano']:
                panos += 1
                continue
            if r['lon'] is None or r['lat'] is None or r['id'] in seen:
                continue
            seen.add(r['id'])
            x, z = to_xz(r['lat'], r['lon'])
            keep.append({'id': r['id'], 'x': round(x, 1), 'z': round(z, 1),
                         'compass_angle': round(float(r['compass_angle'] or 0.0), 1),
                         'captured_at': int(r['captured_at'] or 0)})
        per_tile[tid] = keep
    usable = sum(len(v) for v in per_tile.values())
    sel = select(per_tile, a.max_images)
    print(f'{listed} listed, {panos} panoramas dropped, {usable} usable, {len(sel)} picked', flush=True)
    have = sum(1 for r in sel if os.path.exists(os.path.join(THUMB_DIR, f"{r['id']}.jpg")))
    print(f'thumbnails: {have} on disk, {len(sel) - have} to download', flush=True)
    try:
        resolve_thumb_urls([r for r in sel if not os.path.exists(os.path.join(THUMB_DIR, f"{r['id']}.jpg"))], a.delay)
    except TokenError as e:
        sys.exit(f'Mapillary rejected the token while resolving thumbnail URLs: {e}')
    t0, done, ok = time.time(), 0, 0
    try:
        with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
            for got in ex.map(fetch_thumb, sel):
                done += 1
                ok += bool(got)
                if done % 2000 == 0:
                    print(f'  {done}/{len(sel)} thumbnails ({ok} ok, {time.time() - t0:.0f}s)', flush=True)
    except TokenError as e:
        sys.exit(f'Mapillary rejected the token while refreshing a thumbnail URL: {e}')
    images = [{'id': r['id'], 'x': r['x'], 'z': r['z'], 'compass_angle': r['compass_angle'], 'captured_at': r['captured_at']}
              for r in sel if os.path.exists(os.path.join(THUMB_DIR, f"{r['id']}.jpg"))]
    with open(OUT + '.tmp', 'w') as f:
        json.dump({'src': 'Mapillary Graph API v4 image search + thumb_256 (CC BY-SA 4.0), model frame (philly_frame.py)',
                   'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                   'boxes': [{'name': b[0], 'lat': [b[1], b[2]], 'lon': [b[3], b[4]]} for b in BOXES],
                   'zoom': TILE_Z, 'listed': listed, 'panoramas': panos, 'usable': usable,
                   'picked': len(sel), 'images': images}, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    if provenance:
        provenance.record('fetch_mapillary.thumbs', 'thumb_256_url (Mapillary CDN)', {'max_images': a.max_images}, len(images), listed=listed, panoramas=panos)
    print(f'{OUT}: {len(images)} images with thumbnails ({len(sel) - len(images)} failed; rerun to retry them), '
          f'{os.path.getsize(OUT):,} bytes, {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
