#!/usr/bin/env python3
"""Ground-floor businesses over the outer districts -> lidar_cache/shops_raw.json, the input
of bake_storefronts.py (which hangs a storefront on the street-facing wall of the nearest
footprint). OpenStreetMap nodes and ways tagged shop=*, craft=*, or one of the storefront
amenities (restaurant, cafe, bar, pub, fast food, bank, pharmacy, ice cream, marketplace,
cinema, theatre, nightclub, dentist, clinic, post office, library) over the wide box
(lat 39.915-39.986, lon -75.188..-75.118) plus the south box (lat 39.890-39.9155,
lon -75.190..-75.100), fetched as tiles through overpass.py (checkpoints in
lidar_cache/shop_tiles/, delete a tile to refetch it). Ways come back with `out center`, so
each carries a centre; their vertices ride along as skeleton nodes so a node business that
sits inside a way business of the same kind (the supermarket's own node inside the
supermarket's building) can be dropped as a duplicate. Businesses whose OSM level says
they are upstairs or in a concourse (level set, no 0 or 1 in it) are skipped: the pass is
about what a walker sees at street level.

Output rows: {"x", "z", "kind", "name"} in the model frame (philly_frame.py), kind being
0 generic shop, 1 restaurant or fast food, 2 cafe or ice cream, 3 bar, pub or nightclub,
4 bank, office-like or post office, 5 pharmacy, dentist, clinic, 6 grocery, supermarket,
convenience, marketplace, 7 clothes, boutique, jewelry, shoes, 8 hair, beauty, tattoo,
9 cinema, theatre, library, 10 craft, hardware or other trade.
Data terms: OpenStreetMap, ODbL (../DATA-LICENSE.md). Plain python3."""
import json, os, sys
from collections import Counter
from overpass import fetch_tiles, grid_tiles
from philly_frame import LON0, LAT0, KX, KZ

BOXES = [   # (tile id prefix, S, N, W, E, rows, cols): the wide box and the south box
    ('shopw', 39.915, 39.986, -75.188, -75.118, 2, 2),
    ('shops', 39.890, 39.9155, -75.190, -75.100, 1, 2),
]
CACHE_DIR = 'lidar_cache/shop_tiles'
OUT = 'lidar_cache/shops_raw.json'
AMENITY = ('restaurant', 'cafe', 'bar', 'pub', 'fast_food', 'bank', 'pharmacy', 'ice_cream', 'marketplace',
           'cinema', 'theatre', 'nightclub', 'dentist', 'clinic', 'post_office', 'library')
AMENITY_RE = '^(' + '|'.join(AMENITY) + ')$'

# ---- kind mapping
AMENITY_KIND = {'restaurant': 1, 'fast_food': 1, 'cafe': 2, 'ice_cream': 2, 'bar': 3, 'pub': 3, 'nightclub': 3,
                'bank': 4, 'post_office': 4, 'pharmacy': 5, 'dentist': 5, 'clinic': 5, 'marketplace': 6,
                'cinema': 9, 'theatre': 9, 'library': 9}
SHOP_KIND = {
    'supermarket': 6, 'convenience': 6, 'grocery': 6, 'greengrocer': 6, 'deli': 6, 'butcher': 6, 'seafood': 6,
    'bakery': 6, 'pastry': 6, 'cheese': 6, 'wine': 6, 'alcohol': 6, 'beverages': 6, 'health_food': 6,
    'frozen_food': 6, 'general': 6, 'variety_store': 6, 'dairy': 6, 'spices': 6, 'tea': 6, 'confectionery': 6,
    'coffee': 2, 'ice_cream': 2,
    'clothes': 7, 'boutique': 7, 'jewelry': 7, 'jewellery': 7, 'shoes': 7, 'bag': 7, 'fabric': 7, 'fashion': 7,
    'watches': 7, 'tailor': 7, 'bridal': 7, 'leather': 7, 'fashion_accessories': 7, 'department_store': 7,
    'second_hand': 7, 'sewing': 7, 'wool': 7,
    'hairdresser': 8, 'beauty': 8, 'tattoo': 8, 'massage': 8, 'cosmetics': 8, 'nails': 8, 'perfumery': 8,
    'hairdresser_supply': 8, 'barber': 8,
    'hardware': 10, 'doityourself': 10, 'trade': 10, 'paint': 10, 'locksmith': 10, 'tyres': 10, 'car_repair': 10,
    'car_parts': 10, 'glaziery': 10, 'electrical': 10, 'plumbing': 10, 'tool_hire': 10, 'building_materials': 10,
    'houseware': 10, 'appliance': 10,
    'chemist': 5, 'medical_supply': 5, 'optician': 5,
    'money_lender': 4, 'pawnbroker': 4, 'insurance': 4, 'estate_agent': 4, 'travel_agency': 4,
}
SHOP_SKIP = {'no', 'vacant', 'yes', 'disused', 'empty', 'closed', 'mall'}   # not a storefront (or a whole mall: its tenants are)


def kind_of(t):
    """Kind index for an element's tags, or None if it is not a storefront business."""
    a = t.get('amenity')
    if a in AMENITY_KIND: return AMENITY_KIND[a]
    s = t.get('shop')
    if s:
        s = s.split(';')[0].strip()
        if s in SHOP_SKIP: return None
        return SHOP_KIND.get(s, 0)
    if t.get('craft'): return 10
    return None


def primary(t):
    """The tag that makes it a business, for the same-kind duplicate test."""
    a = t.get('amenity')
    if a in AMENITY_KIND: return ('amenity', a)
    if t.get('shop'): return ('shop', t['shop'].split(';')[0].strip())
    if t.get('craft'): return ('craft', t['craft'].split(';')[0].strip())
    return None


def ground_floor(t):
    """False when the level tag says upstairs or below ground (level set, no 0 or 1 in it).
    1 is kept: US mappers use it for the ground floor as often as not."""
    lv = t.get('level')
    if not lv: return True
    for part in lv.replace(',', ';').split(';'):
        part = part.strip()
        if '-' in part[1:]:   # a range like 0-2
            a, b = part[1:].split('-', 1) if part.startswith('-') else part.split('-', 1)
            try:
                lo, hi = float(('-' if part.startswith('-') else '') + a), float(b)
                if lo <= 1 and hi >= 0: return True
            except ValueError: return True
            continue
        try:
            if float(part) in (0.0, 1.0): return True
        except ValueError:
            return True
    return False


def tileQuery(bbox):
    return f'''[out:json][timeout:170];
(
  node["shop"]({bbox}); node["craft"]({bbox}); node["amenity"~"{AMENITY_RE}"]({bbox});
) -> .n;
(
  way["shop"]({bbox}); way["craft"]({bbox}); way["amenity"~"{AMENITY_RE}"]({bbox});
) -> .w;
.n out body qt;
.w out center qt;
.w > -> .wn;
.wn out skel qt;'''


def to_xz(lat, lon):
    return (lon - LON0) * KX, (LAT0 - lat) * KZ


def pip(x, z, poly):
    inside = False; j = len(poly) - 1
    for i in range(len(poly)):
        xi, zi = poly[i]; xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / (zj - zi) + xi: inside = not inside
        j = i
    return inside


tiles = []
for name, S, N, W, E, rows, cols in BOXES:
    tiles += grid_tiles(name, S, N, W, E, rows, cols)
elements = fetch_tiles(tiles, tileQuery, CACHE_DIR, pause=5)
print(f'{len(elements)} elements over {len(tiles)} tiles', flush=True)

coords = {el['id']: to_xz(el['lat'], el['lon']) for el in elements if el.get('type') == 'node' and 'lat' in el}
rows, way_polys = [], []   # way_polys: (ring, primary tag) for the node-in-way duplicate test
n_node = n_way = n_level = n_notshop = 0
for el in elements:
    t = el.get('tags') or {}
    if not t: continue
    k = kind_of(t)
    if k is None: n_notshop += 1; continue
    if not ground_floor(t): n_level += 1; continue
    if el['type'] == 'node':
        x, z = coords[el['id']]
        rows.append({'x': round(x, 2), 'z': round(z, 2), 'kind': k, 'name': t.get('name', ''), '_p': primary(t), '_node': True})
        n_node += 1
    elif el['type'] == 'way' and el.get('center'):
        x, z = to_xz(el['center']['lat'], el['center']['lon'])
        ring = [coords[n] for n in el.get('nodes', []) if n in coords]
        if len(ring) >= 4 and ring[0] == ring[-1]: way_polys.append((ring[:-1], primary(t)))
        rows.append({'x': round(x, 2), 'z': round(z, 2), 'kind': k, 'name': t.get('name', ''), '_p': primary(t), '_node': False})
        n_way += 1

# a node inside a way carrying the same primary tag is the same business mapped twice
cells = {}
for ring, p in way_polys:
    xs = [q[0] for q in ring]; zs = [q[1] for q in ring]
    for gx in range(int(min(xs) // 100), int(max(xs) // 100) + 1):
        for gz in range(int(min(zs) // 100), int(max(zs) // 100) + 1):
            cells.setdefault((gx, gz), []).append((ring, p))
kept, n_dup = [], 0
for r in rows:
    if r['_node']:
        dup = False
        for ring, p in cells.get((int(r['x'] // 100), int(r['z'] // 100)), ()):
            if p == r['_p'] and pip(r['x'], r['z'], ring): dup = True; break
        if dup: n_dup += 1; continue
    kept.append({'x': r['x'], 'z': r['z'], 'kind': r['kind'], 'name': r['name']})

os.makedirs('lidar_cache', exist_ok=True)
json.dump(kept, open(OUT, 'w'), separators=(',', ':'), ensure_ascii=False)
kinds = Counter(r['kind'] for r in kept)
print(f'businesses: {n_node} nodes + {n_way} ways ({n_notshop} tagged elements not a storefront, '
      f'{n_level} upstairs or below ground, {n_dup} nodes duplicated by a way of the same kind) -> {len(kept)} written', flush=True)
print('by kind: ' + ', '.join(f'{k}:{kinds[k]}' for k in sorted(kinds)), flush=True)
print(f'{OUT}: {os.path.getsize(OUT):,} bytes', flush=True)
