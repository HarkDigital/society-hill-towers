#!/usr/bin/env python3
"""Street-level imagery for the wall-colour pass: page the Mapillary Graph API v4 image
search over the outer-districts and south boxes tile by tile, then pull every kept
image's 256 px thumbnail, so bake_wall_colors.py can read the colour of the walls that
flank each street. Mapillary imagery is CC BY-SA 4.0 (the credit goes into
DATA-LICENSE.md when the colours ship).

Boxes (lat S..N, lon W..E), cut into ~0.006 deg tiles (about 510 x 660 m):
  wide   39.915..39.986, -75.188..-75.118   the outer districts (scene_wide.json)
  south  39.890..39.9155, -75.190..-75.100  the stadium district and the port (scene_south.json)
Per tile: GET https://graph.mapillary.com/images?fields=id,geometry,compass_angle,
captured_at,thumb_256_url,is_pano&bbox=w,s,e,n&limit=2000, following paging.next.
The token comes from the MAPILLARY_TOKEN environment variable (a client token from the
developer dashboard, 'MLY|<app id>|<hex>'); it travels in the Authorization header and is
never written to disk or to provenance.jsonl.

Resumable: lidar_cache/mly_tiles/<tile>.json per tile (written atomically, skipped when
present, delete one to refetch it), lidar_cache/mly_thumbs/<id>.jpg per image (skipped
when present; a thumb URL that has expired since its tile was listed is refreshed from
the entity endpoint). 429 and 5xx answers back off and retry; a bad token stops the run.
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
import argparse, json, math, os, random, sys, time, urllib.error, urllib.parse, urllib.request
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
FIELDS = 'id,geometry,compass_angle,captured_at,thumb_256_url,is_pano'
LIMIT = 2000
TILE_DEG = 0.006
MAX_PAGES = 250          # 500k images in one tile means the paging is looping, not that the tile is dense
BOXES = [                # name, lat S, lat N, lon W, lon E
    ('wide', 39.915, 39.986, -75.188, -75.118),
    ('south', 39.890, 39.9155, -75.190, -75.100),
]
USER_AGENT = 'sht-3d-model/1.0 (philly3d.com wall-colour pass)'
TOKEN = os.environ.get('MAPILLARY_TOKEN', '').strip()


# ---------------- tiles ----------------
def grid_tiles(name, S, N, W, E, step=TILE_DEG):
    """[(tile id, (w, s, e, n)), ...]: the box cut into ceil(span / step) rows and columns,
    so no tile is wider than `step` (the search caps at 2000 per page; small tiles keep
    the paging short and the resume granular)."""
    rows = max(1, math.ceil((N - S) / step - 1e-9))
    cols = max(1, math.ceil((E - W) / step - 1e-9))
    tiles = []
    for i in range(rows):
        for j in range(cols):
            s = S + (N - S) * i / rows; n = S + (N - S) * (i + 1) / rows
            w = W + (E - W) * j / cols; e = W + (E - W) * (j + 1) / cols
            tiles.append((f'{name}-{i}-{j}', (round(w, 5), round(s, 5), round(e, 5), round(n, 5))))
    return tiles


def all_tiles():
    tiles = []
    for name, S, N, W, E in BOXES:
        tiles += grid_tiles(name, S, N, W, E)
    return tiles


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


def trim(rec):
    """One search record -> the fields we keep in the tile file (still lat/lon)."""
    g = rec.get('geometry') or {}
    c = g.get('coordinates') or [None, None]
    return {'id': str(rec.get('id')), 'lon': c[0], 'lat': c[1],
            'compass_angle': rec.get('compass_angle'), 'captured_at': rec.get('captured_at'),
            'thumb_256_url': rec.get('thumb_256_url'), 'is_pano': bool(rec.get('is_pano'))}


def fetch_tile(tid, bbox, delay):
    """Page the image search over one tile into TILE_DIR/<tid>.json; returns its records."""
    path = os.path.join(TILE_DIR, f'{tid}.json')
    if os.path.exists(path) and os.path.getsize(path) > 2:
        return json.load(open(path))['images']
    t0 = time.time()
    bbox_s = '%.5f,%.5f,%.5f,%.5f' % bbox
    url, params = f'{API}/images', {'fields': FIELDS, 'bbox': bbox_s, 'limit': LIMIT}
    recs, pages = [], 0
    while url:
        d = api_get(url, params)
        params = None                          # paging.next carries the query
        pages += 1
        recs.extend(trim(r) for r in d.get('data') or [])
        url = (d.get('paging') or {}).get('next')
        if url and pages >= MAX_PAGES:
            print(f'  {tid}: {pages} pages, stopping the paging here', flush=True)
            url = None
        time.sleep(delay)
    with open(path + '.tmp', 'w') as f:
        json.dump({'tile': tid, 'bbox': list(bbox), 'pages': pages, 'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'images': recs}, f, separators=(',', ':'))
    os.replace(path + '.tmp', path)
    if provenance:
        provenance.record('fetch_mapillary.graph', f'{API}/images', {'fields': FIELDS, 'bbox': bbox_s, 'limit': LIMIT}, len(recs), tile=tid, pages=pages)
    panos = sum(1 for r in recs if r['is_pano'])
    print(f'{tid} {bbox_s}: {len(recs)} images ({panos} panos) in {pages} page(s), {time.time() - t0:.0f}s', flush=True)
    return recs


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
    tiles = all_tiles()
    todo = [t for t in tiles if not os.path.exists(os.path.join(TILE_DIR, f'{t[0]}.json'))]
    print(f'{len(tiles)} tiles ({len(todo)} to fetch), cap {a.max_images} images', flush=True)
    per_tile, listed, panos, seen = {}, 0, 0, set()
    for tid, bbox in tiles:
        try:
            recs = fetch_tile(tid, bbox, a.delay)
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
                         'captured_at': int(r['captured_at'] or 0), 'thumb_256_url': r['thumb_256_url']})
        per_tile[tid] = keep
    usable = sum(len(v) for v in per_tile.values())
    sel = select(per_tile, a.max_images)
    print(f'{listed} listed, {panos} panoramas dropped, {usable} usable, {len(sel)} picked', flush=True)
    have = sum(1 for r in sel if os.path.exists(os.path.join(THUMB_DIR, f"{r['id']}.jpg")))
    print(f'thumbnails: {have} on disk, {len(sel) - have} to download', flush=True)
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
                   'tile_deg': TILE_DEG, 'listed': listed, 'panoramas': panos, 'usable': usable,
                   'picked': len(sel), 'images': images}, f, separators=(',', ':'))
    os.replace(OUT + '.tmp', OUT)
    if provenance:
        provenance.record('fetch_mapillary.thumbs', 'thumb_256_url (Mapillary CDN)', {'max_images': a.max_images}, len(images), listed=listed, panoramas=panos)
    print(f'{OUT}: {len(images)} images with thumbnails ({len(sel) - len(images)} failed; rerun to retry them), '
          f'{os.path.getsize(OUT):,} bytes, {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
