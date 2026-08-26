#!/usr/bin/env python3
"""OSM drivable ways + PennDOT AADT -> traffic.b64 for the ambient traffic layer.

Sources the raw Overpass dumps (NOT the scene jsons): the raw ways carry way IDs
(exact dedup between the wide and south dumps), oneway, and tunnel tags — all
three load-bearing (head-on traffic on I-95's carriageways would be glaring).
PennDOT RMSTRAFFIC segments (fetch_traffic.py) are conflated onto the ways by
nearest-parallel-edge matching; unmatched ways take a class-default AADT so the
whole rendered network carries cars, with real counts wherever the state has them.

Layout (int16 after Int32[4] header magic 0x53485454, nWays, nPts, 0):
  way: n, clsFlags, aadt10, then n x [x/0.2, z/0.2]
  clsFlags bits 0-2 class (pack_wide RT), bit 3 oneway, bit 4 penndot-matched."""
import json, math, pathlib, struct, base64

HERE = pathlib.Path(__file__).parent
WIDE = (-3700, 2300, -4480, 6400)
LAT0, LON0 = 39.945473644755005, -75.14474803850973
MX = 111320 * math.cos(math.radians(LAT0))
MZ = 110574
RT = {'motorway': 0, 'motorway_link': 0, 'trunk': 1, 'trunk_link': 1, 'primary': 2,
      'secondary': 3, 'tertiary': 4, 'residential': 5, 'living_street': 5, 'unclassified': 5}
# class-default AADT where PennDOT has no count. Per-WAY numbers: motorway ways
# are single one-way carriageways in OSM, so the default is per-carriageway
# (I-95 both directions ~90-100k); surface one-ways carry full typical volumes.
DEF_AADT = {'motorway': 45000, 'motorway_link': 14000, 'trunk': 25000, 'trunk_link': 8000,
            'primary': 12000, 'secondary': 8000, 'tertiary': 4000,
            'residential': 800, 'living_street': 800, 'unclassified': 800}
# mirror of the runtime density model, for the implied-total report
SPEED_KMH = [88, 64, 40, 34, 30, 22]
WD_FRAC = [.008, .005, .004, .004, .006, .015, .035, .062, .071, .055, .048, .050,
           .053, .052, .055, .065, .073, .078, .062, .045, .035, .028, .020, .012]

def to_xz(lat, lon):
    return ((lon - LON0) * MX, -((lat - LAT0) * MZ))

def simplify_open(pts, tol):
    if len(pts) <= 2: return pts
    def dp(seg):
        if len(seg) < 3: return seg
        a, b = seg[0], seg[-1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz) or 1e-9
        best, bi = -1, -1
        for i in range(1, len(seg) - 1):
            p = seg[i]
            dist = abs((p[0] - a[0]) * dz - (p[1] - a[1]) * dx) / L
            if dist > best: best, bi = dist, i
        if best > tol: return dp(seg[:bi + 1])[:-1] + dp(seg[bi:])
        return [a, b]
    return dp(pts)

def runs_of(pts, box, m):
    inb = lambda q: box[0] - m <= q[0] <= box[1] + m and box[2] - m <= q[1] <= box[3] + m
    runs, cur = [], []
    for i, q in enumerate(pts):
        keep = inb(q) or (i > 0 and inb(pts[i - 1])) or (i + 1 < len(pts) and inb(pts[i + 1]))
        if keep: cur.append(q)
        else:
            if len(cur) > 1: runs.append(cur)
            cur = []
    if len(cur) > 1: runs.append(cur)
    return runs

def length_of(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))

# ---- load OSM ways (wide + south raw, dedup by way id) --------------------
nodes, ways, seen = {}, [], set()
for fn in ('osm_wide_raw.json', 'osm_south_raw.json'):
    p = HERE / fn
    if not p.exists():
        print(f'WARNING: {fn} missing — its area gets no traffic'); continue
    for el in json.load(open(p)).get('elements', []):
        if el['type'] == 'node':
            nodes[el['id']] = (el['lat'], el['lon'])
        elif el['type'] == 'way' and el['id'] not in seen:
            seen.add(el['id']); ways.append(el)

sel = []
for w in ways:
    t = w.get('tags') or {}
    hw = t.get('highway')
    if hw not in RT: continue
    if t.get('area') == 'yes': continue
    if t.get('access') in ('private', 'no'): continue
    if t.get('tunnel') in ('yes', 'building_passage') or t.get('covered') == 'yes': continue
    ow = t.get('oneway', '')
    oneway = ow in ('yes', 'true', '1') or hw in ('motorway', 'motorway_link') or t.get('junction') == 'roundabout'
    pts = [to_xz(*nodes[n]) for n in w['nodes'] if n in nodes]
    if len(pts) < 2: continue
    if ow == '-1':
        pts.reverse(); oneway = True
    sel.append({'hw': hw, 'cls': RT[hw], 'oneway': oneway, 'pts': pts})

# ---- PennDOT sub-edge index ------------------------------------------------
GRID = 60
edges, egrid = [], {}
raw = HERE / 'lidar_cache' / 'traffic_raw' / 'rmstraffic.geojson'
pd_feats = json.load(open(raw))['features'] if raw.exists() else []
for f in pd_feats:
    props = f.get('properties') or {}
    aadt = props.get('CUR_AADT')
    if not aadt or aadt <= 0: continue
    g = f.get('geometry') or {}
    lines = g['coordinates'] if g.get('type') == 'MultiLineString' else [g.get('coordinates') or []]
    for line in lines:
        pl = [to_xz(c[1], c[0]) for c in line]
        for i in range(len(pl) - 1):
            ax, az = pl[i]; bx, bz = pl[i + 1]
            L = math.hypot(bx - ax, bz - az)
            if L < 0.5: continue
            ei = len(edges)
            edges.append((ax, az, bx, bz, (bx - ax) / L, (bz - az) / L, aadt, props.get('ST_RT_NO') or ''))
            for gx in range(int(min(ax, bx) // GRID), int(max(ax, bx) // GRID) + 1):
                for gz in range(int(min(az, bz) // GRID), int(max(az, bz) // GRID) + 1):
                    egrid.setdefault((gx, gz), []).append(ei)

# match distance tightens with class: a residential street 20 m from I-95's
# centerline (Water St, the Port Richmond frontages) must NOT inherit 90k AADT
MAXD = [25.0, 25.0, 18.0, 16.0, 13.0, 10.0]
# and a match whose count is implausible for the class is a false conflation
MAX_PLAUSIBLE = [200000, 200000, 60000, 60000, 20000, 15000]

def match_edge(x, z, ux, uz, maxd):
    """nearest PennDOT sub-edge within maxd meters and within ~30 deg of parallel"""
    best, bd = None, maxd * maxd
    gx, gz = int(x // GRID), int(z // GRID)
    for cx in (gx - 1, gx, gx + 1):
        for cz in (gz - 1, gz, gz + 1):
            for ei in egrid.get((cx, cz), ()):
                ax, az, bx, bz, ex, ez, aadt, rt = edges[ei]
                if abs(ux * ex + uz * ez) < 0.87: continue
                dx, dz = bx - ax, bz - az
                L2 = dx * dx + dz * dz
                tt = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / L2))
                px, pz = ax + dx * tt - x, az + dz * tt - z
                d2 = px * px + pz * pz
                if d2 < bd: bd, best = d2, ei
    return best

def has_antiparallel_sibling(ei):
    ax, az, bx, bz, ex, ez, aadt, rt = edges[ei]
    mx, mz = (ax + bx) / 2, (az + bz) / 2
    gx, gz = int(mx // GRID), int(mz // GRID)
    for cx in (gx - 1, gx, gx + 1):
        for cz in (gz - 1, gz, gz + 1):
            for oi in egrid.get((cx, cz), ()):
                if oi == ei: continue
                oax, oaz, obx, obz, oex, oez, oaadt, ort = edges[oi]
                if ort != rt: continue
                if ex * oex + ez * oez > -0.7: continue
                omx, omz = (oax + obx) / 2, (oaz + obz) / 2
                if math.hypot(omx - mx, omz - mz) < 40: return True
    return False

# ---- conflate + encode -----------------------------------------------------
body, nW, nP = [], 0, 0
matched = halved = 0
km_by_cls = [0.0] * 6
implied_peak = 0.0
wd_n = [v / sum(WD_FRAC) for v in WD_FRAC]
for w in sel:
    for run in runs_of(w['pts'], WIDE, 200):
        run = simplify_open(run, 1.2) if len(run) > 3 else run
        L = length_of(run)
        if L < 25: continue
        # sample midpoints (long segments every ~25 m) against the PennDOT index
        votes = []
        n_samp = 0
        for i in range(len(run) - 1):
            ax, az = run[i]; bx, bz = run[i + 1]
            sl = math.hypot(bx - ax, bz - az)
            if sl < 0.5: continue
            ux, uz = (bx - ax) / sl, (bz - az) / sl
            k = max(1, int(sl // 25))
            for j in range(k):
                tt = (j + 0.5) / k
                n_samp += 1
                ei = match_edge(ax + (bx - ax) * tt, az + (bz - az) * tt, ux, uz, MAXD[w['cls']])
                if ei is not None: votes.append(ei)
        aadt, is_matched = DEF_AADT[w['hw']], False
        if n_samp and len(votes) * 2 >= n_samp:
            vals = sorted(edges[ei][6] for ei in votes)
            med = vals[len(vals) // 2]
            if med <= MAX_PLAUSIBLE[w['cls']]:
                aadt = med
                is_matched = True
                matched += 1
                # a oneway OSM carriageway carries half a both-directions count —
                # unless PennDOT itself splits the carriageways (antiparallel sibling)
                med_ei = min(votes, key=lambda ei: abs(edges[ei][6] - med))
                if w['oneway'] and not has_antiparallel_sibling(med_ei):
                    aadt = aadt / 2; halved += 1
        flags = w['cls'] | (8 if w['oneway'] else 0) | (16 if is_matched else 0)
        body += [len(run), flags, min(32767, int(round(aadt / 10)))]
        for q in run:
            body += [max(-32767, min(32767, int(round(q[0] / 0.2)))),
                     max(-32767, min(32767, int(round(q[1] / 0.2))))]
        nW += 1; nP += len(run)
        km_by_cls[w['cls']] += L / 1000
        implied_peak += aadt * wd_n[17] / SPEED_KMH[w['cls']] * (L / 1000)

buf = struct.pack('<4i', 0x53485454, nW, nP, 0) + struct.pack('<%dh' % len(body), *body)
b64 = base64.b64encode(buf).decode('ascii')
(HERE / 'traffic.b64').write_text(b64)
print(f'ways {nW} ({matched} penndot-matched, {halved} halved oneways), points {nP}')
print('km by class:', ' '.join(f'{i}:{km:.0f}' for i, km in enumerate(km_by_cls)))
print(f'implied cars at weekday 17:00, whole extent: {implied_peak:.0f}')
print(f'traffic.b64: {len(buf)/1024:.0f} KB binary, {len(b64)/1024:.0f} KB base64')
