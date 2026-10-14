#!/usr/bin/env python3
"""The glass towers' day calibration (Round 192's review: "too dark, too grey, and the blue is lost"). Renders the built
page headless at the standard noon poses (the capture skill's render.mjs on this Mac's GPU), each pose five times: as
drawn, with the glass's whole material as a flat mask (uGlassK.z 6), each tower's glass by a code of its own (7 and 8: its
body's bytes hashed, three bits a view) and the glass alone without its frames (9). For each researched tower in SWATCHES
the mean sRGB colour of its own glass (its code's pixels inside its projected box, the frames left out) is compared with
the tower's reference swatch: within its CIE76 delta E and its b* within HUE_B of the swatch's (delta E alone let a blue
tower pass as grey). Writes tests/glass_calibration.json, which tests/test_glass_calibration.py checks: every tower within
both bounds at each pose it is judged at, and the measure taken on the shaders and systems the page has now (a fingerprint
of the glass's GLSL and of glass_art.json's systems and towers), so a change to the glass that is not re-measured fails.
Round 192's second review added a pose a hundred metres off Comcast's south face at noon, where the frames must not stand out
of its glass (the 90th over the 10th percentile of the whole face's luminance, CONTRAST), and One Liberty's crown (REGION).
The third review: every researched glass tower with a reference colour (the review's reading of the refs: the W's jagged
blue, the Ritz's and Murano's blues, PNC's and 2000 Market's dark glass, the residential walls' greys), the poses widened to
the review's eight plus the CTC's south face at mid-level and the shaded north faces from Market's north side, each tower
judged at the poses where it is in the open (JUDGE: at least 400 pixels of its own glass and two fifths of its height in
view; a tower seen as a sliver past its neighbours mirrors them, not the sky its photographs were taken under), and the
measure by the tower's own code (the system's colour, the commonest in the box's top third, had measured One Liberty's
glass for PNC and Two Penn).

Usage: python3 glass_calibrate.py [--keep DIR] [--shots DIR]   (after python3 build.py; about six minutes; --shots
measures shots already rendered)"""
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
RENDER = HERE.parent / '.claude' / 'skills' / 'philly3d-capture' / 'scripts' / 'render.mjs'
OUT = HERE / 'tests' / 'glass_calibration.json'
W, H, FOV = 1280, 800, 58.0
C = [2026, 10, 14, 780]
# the standard poses: noon on Oct 14 in clear air: from the south-west over the skyline, a low flight over Rittenhouse, from
# the south over South Philadelphia, University City looking east, Rittenhouse looking north, Broad Street from the south,
# Market's north side looking south at the shaded north faces, Market at 90 m, the CTC's south face at mid-level, Comcast's
# shaded north-east faces at mid-level (the CTC hides its north face from Market), a hundred metres off Comcast's south face,
# One Liberty's crown
POSES = {
    'skyline-sw-day': {'pos': [-3100, 230, 250], 'look': [-2000, 150, -900], 'clock': C},
    'lowflight-day': {'pos': [-2500, 260, -250], 'look': [-2050, 150, -950], 'clock': C},
    'south-day': {'pos': [-1800, 150, 600], 'look': [-1950, 150, -850], 'clock': C},
    'univcity-east': {'pos': [-2700, 180, -650], 'look': [-3300, 120, -900], 'clock': C},
    'rittenhouse-north': {'pos': [-2250, 150, 50], 'look': [-2250, 110, -700], 'clock': C},
    'broad-south': {'pos': [-1600, 150, 450], 'look': [-1690, 110, -500], 'clock': C},
    'market-north': {'pos': [-2350, 160, -1650], 'look': [-2350, 110, -850], 'clock': C},
    'market-south-low': {'pos': [-2300, 90, -600], 'look': [-2300, 90, -950], 'clock': C},
    'ctc-mid': {'pos': [-2190, 150, -960], 'look': [-2201, 150, -1057], 'clock': C},
    'comcast-north-150': {'pos': [-1700, 150, -1400], 'look': [-2041, 150, -1025], 'clock': C},
    'comcast-south-100': {'pos': [-2035, 130, -920], 'look': [-2041, 140, -1025], 'clock': C},
    'onelib-crown': {'pos': [-1975, 240, -655], 'look': [-1995, 250, -784], 'clock': C},
    # and at 50 to 60 m, the height a photograph from a street or a low roof sees the lower towers from: Rittenhouse looking
    # north, Broad Street looking north, Chestnut west of the Schuylkill looking east, the river at Cira looking west, and one
    # aimed at each lower tower no other pose judges (2116 Chestnut, 1706 Rittenhouse, Two Penn, the Honickman, CHOP)
    'rittenhouse-60': {'pos': [-2250, 60, -320], 'look': [-2250, 60, -700], 'clock': C},
    'broad-60': {'pos': [-1640, 60, -300], 'look': [-1690, 60, -700], 'clock': C},
    'market-west-60': {'pos': [-2900, 60, -760], 'look': [-2450, 60, -860], 'clock': C},
    'river-60': {'pos': [-2950, 60, -1100], 'look': [-3350, 60, -1050], 'clock': C},
    'chestnut2116-50': {'pos': [-2560, 50, -330], 'look': [-2611, 60, -568], 'clock': C},
    'walnut1706-50': {'pos': [-2100, 50, -60], 'look': [-2143, 60, -293], 'clock': C},
    'twopenn-50': {'pos': [-1790, 50, -1150], 'look': [-1789, 40, -867], 'clock': C},
    'honickman-50': {'pos': [-1230, 50, -300], 'look': [-1228, 55, -557], 'clock': C},
    'chop-50': {'pos': [-3500, 50, 230], 'look': [-3569, 57, -18], 'clock': C},
}
# the reference swatches (sRGB), each tower's photographed glass as the refs read it (the body glass_systems.json gives it),
# with the poses it is judged at (JUDGE's, frozen from the run: a pose it no longer stands in the open at fails the test)
# and its tolerance (CIE76 delta E: under about 12 a viewer calls two greys the same family and lightness, past 20 a
# different colour)
SW = {
    'Comcast Center': '#8FA3AE', 'Comcast Technology Center': '#A9B6BA', 'One Liberty Place': '#5D7F9E', 'Two Liberty Place': '#5D7F9E',
    'Cira Centre': '#A7B5C0', 'FMC Tower at Cira Centre South': '#7F9BB0', 'Evo at Cira Centre South': '#4B5762',
    'The W and Element Philadelphia (1441 Chestnut)': '#4E78A2', 'The Residences at The Ritz-Carlton': '#6C93AE',
    'The Laurel Rittenhouse Square (1911 Walnut)': '#8E8A82', 'Murano (2101 Market)': '#6E9EB4', '2116 Chestnut': '#7D9A90',
    'G. Fred DiBona Jr. Building (1901 Market, Independence Blue Cross)': '#4F6476', 'Arthaus (301-311 S Broad)': '#8C9AA4',
    'PNC Bank Building (1600 Market)': '#3A4148', '2000 Market Street': '#2F3539', 'Eleven Penn Center (1835 Market)': '#5B748A',
    '10 Rittenhouse Square (1801 Walnut)': '#9CAEBB', '1706 Rittenhouse': '#7F95A8', 'Two Penn Center (1500 JFK)': '#9FA6AB',
    'Ten Penn Center (1801 Market)': '#6F7C85', '1650 Arch Street': '#4A5056', 'Jefferson Health Honickman Center (1101 Chestnut)': '#AAB8C2',
    'Riverwalk I and II (30 N 23rd / 2200 Arch)': '#8E9AA6', '3025 JFK Boulevard': '#8FA5B3', 'The Alexander (1601 Vine)': '#9EACB6',
    'CHOP Roberts Center for Pediatric Research': '#9DB5C8', '1818 Market Street': '#3B4246',
}
JUDGED = json.loads((HERE / 'tests' / 'glass_calibration_poses.json').read_text()) if (HERE / 'tests' / 'glass_calibration_poses.json').exists() else {}
SWATCHES = {k: (v, JUDGED.get(k, [p for p in POSES if p != 'onelib-crown']), 15) for k, v in SW.items()}
SWATCHES['One Liberty Place (crown)'] = ('#5D7F9E', ['onelib-crown', 'skyline-sw-day'], 15)
# a swatch measured over part of a tower: the tower it is part of and the heights (world metres) its box is cut to
REGION = {'One Liberty Place (crown)': ('One Liberty Place', 205.0, 268.0)}
# the frames against the glass: the 90th over the 10th percentile of the luminance over the tower's whole face, at most
CONTRAST = {('Comcast Center', 'comcast-south-100'): 2.0}
# the hue bound: the glass's b* within this of the swatch's
HUE_B = 6.0
# a tower is judged where at least this many pixels of its own glass and this share of its height are in view, and where the
# eye stands no more than this over its top: a wall reflects a ray on as far down as it came in, so seen from above a curtain
# wall mirrors the city under it and reads darker than any photograph of it from the street, under the sky it mirrors there
JUDGE = (400, 0.4, 20.0)
# the poses the review named for the two Comcast towers: mid-level and the shaded north faces (they must stay judged)
NAMED = {'Comcast Center': ['comcast-south-100', 'market-south-low', 'comcast-north-150'], 'Comcast Technology Center': ['ctc-mid', 'market-north']}
# the towers still open at this round's end, each with its median delta E and b* gap over its judged poses (the test holds
# them there, so no change makes them worse unseen) and what keeps it from its swatch; for Mike
OPEN = {
    'The W and Element Philadelphia (1441 Chestnut)': (11.0, 10.6, 'its photographed blue (b* -27) is deeper than a coated pane keeps under Schlick\'s grazing white and the haze: b* -13 to -19 at its judged poses (the review measured -2 to -8)'),
    'Murano (2101 Market)': (14.0, 13.5, 'five of its seven judged poses see its south faces, which mirror the sky toward the sun, white round the sun\'s aureole at noon; its north faces from Market\'s north side and from the west keep its blue'),
    'The Laurel Rittenhouse Square (1911 Walnut)': (9.5, -6.9, 'a warm greige glass mirroring a blue sky reads a little blue: b* -1 to -3 against the swatch\'s +4.8, one point past the bound'),
    'Eleven Penn Center (1835 Market)': (16.2, 4.8, 'its west face from 60 m mirrors the dark low city west of it (L* 25); its other faces are within 4'),
    'Jefferson Health Honickman Center (1101 Chestnut)': (17.0, -0.4, 'judged at one pose, its south face from 50 m mirroring the sky toward the sun (L* 58 against 74)'),
    'Riverwalk I and II (30 N 23rd / 2200 Arch)': (17.4, 1.1, 'both judged poses see it among Center City\'s towers, which it mirrors (L* 47 to 50 against 63)'),
    'Two Penn Center (1500 JFK)': (None, None, 'no standard pose sees two fifths of its height: 80 m among Penn Center\'s towers'),
    '1818 Market Street': (20.5, -1.8, 'its ribbon windows\' dark glass (L* 27 head-on) mirrors the sky at the slant most poses see a ribbon at, L* 45 to 65, and from below it mirrors the sky overhead'),
}
QUERY = 'dev=1&dpr=1&wx=clear#l=132156'


def fingerprint():
    """The glass's shaders and systems: what a calibration was measured on."""
    src = (HERE / 'app.js').read_text()
    parts = []
    for name in ('GLASS_SYS_PARS', 'GLASS_SYS_MAIN', 'GLASS_ENV_PARS', 'CITYENV_GLSL_F'):
        m = re.search(r'const %s = `(.*?)`;' % name, src, re.S)
        parts.append(m.group(1) if m else '')
    for fn in ('function glassSysPack() {', 'function glassSysHook(sh) {', 'function cityEnvBake(only) {'):
        a = src.index(fn)
        parts.append(src[a:src.index('\n  }\n', a)])
    art = json.loads((HERE / 'glass_art.json').read_text())
    parts.append(json.dumps([art['systems'], art['towers'], art.get('cells')], sort_keys=True))
    return hashlib.sha256('\n'.join(parts).encode()).hexdigest()[:16]


def hex_rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def lab(rgb):
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = M @ c / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def delta_e(a, b):
    return float(np.linalg.norm(lab(a) - lab(b)))


def project(pose, pts):
    """Screen pixels of world points for a pose (the page's goFly: yaw from north, pitch, no roll; a 58 degree vertical
    field), None behind the eye."""
    p, l = np.array(pose['pos'], float), np.array(pose['look'], float)
    d = l - p
    yaw, pitch = math.atan2(d[0], -d[2]), math.atan2(d[1], math.hypot(d[0], d[2]))
    f = np.array([math.sin(yaw) * math.cos(pitch), math.sin(pitch), -math.cos(yaw) * math.cos(pitch)])
    r = np.array([math.cos(yaw), 0.0, math.sin(yaw)])
    u = np.cross(r, f)
    foc = (H / 2) / math.tan(math.radians(FOV) / 2)
    out = []
    for q in pts:
        v = np.asarray(q, float) - p
        z = v @ f
        if z <= 1:
            return None
        out.append((W / 2 + (v @ r) / z * foc, H / 2 - (v @ u) / z * foc))
    return out


def tower_box(pose, t, ys=None):
    rr = min(t.get('r', 30), 45)
    pts = [(t['x'] + dx, y, t['z'] + dz) for dx in (-rr, rr) for dz in (-rr, rr) for y in (ys or (0, t['h'] + 5))]
    s = project(pose, pts)
    if not s:
        return None
    xs, ys = [q[0] for q in s], [q[1] for q in s]
    x0, x1, y0, y1 = max(0, int(min(xs))), min(W, int(max(xs))), max(0, int(min(ys))), min(H, int(max(ys)))
    return (x0, y0, x1, y1) if x1 - x0 > 2 and y1 - y0 > 2 else None


def towers_by_name():
    return {t['name']: t for t in json.loads((HERE / 'towers.json').read_text())['towers']}


def tower_code(name, t):
    """A researched tower's glass code in views 7 and 8 (app.js gDbgId): its body as the chunk stores it (its hex at 0.66,
    truncated to a byte), hashed in single precision as the shader hashes it, three bits a view"""
    sysd = json.loads((HERE / 'glass_systems.json').read_text())['towers'].get(name, {})
    hexc = sysd.get('body') or t.get('hex')
    if not hexc:
        return None
    b = [np.float32(int((int(hexc[i:i + 2], 16) / 255 * 0.66) * 255)) for i in (1, 3, 5)]
    d = np.float32(b[0] * np.float32(0.1371)) + np.float32(b[1] * np.float32(0.3791))
    d = np.float32(d + np.float32(b[2] * np.float32(0.0937)))
    i = np.float32(d - np.floor(d))
    i8 = np.float32(i * np.float32(8.0))
    return int(np.floor(i8)), int(np.floor(np.float32(i8 - np.floor(i8)) * np.float32(8.0)))


CODED = []   # the measures taken by a tower's own code (the rest by the axis)


def code_of(I):
    """A view's three bits a pixel: each channel full or dark"""
    return (I[..., 0] > 115).astype(int) + 2 * (I[..., 1] > 115) + 4 * (I[..., 2] > 115)


def own_pixels(name, t, A, B, sub, box, ax):
    """The tower's own glass: the pixels of its code in both views (the third review: the system's colour, picked as the
    commonest in the box's top third, measured One Liberty's glass for PNC and Two Penn), else, for a tower whose code
    is not known or not found, the code with the most pixels near its own projected axis"""
    k = code_of(A) * 8 + code_of(B)
    c = tower_code(name, t)
    if c is not None:
        own = sub & (k == c[0] * 8 + c[1])
        if own.sum() >= 100:
            CODED.append(name)
            return own
    x0, y0, x1, y1 = box
    vals, cnt = np.unique(k[sub], return_counts=True)
    xs = np.arange(A.shape[1])[None, :].repeat(A.shape[0], 0)
    sw = max(0.3 * (x1 - x0), 8.0)
    best, bs = None, -1.0
    for v, n in zip(vals, cnt):
        if n < 30:
            continue
        sc = n * math.exp(-((xs[sub & (k == v)].mean() - ax) / sw) ** 2)
        if sc > bs:
            best, bs = v, sc
    return None if best is None else sub & (k == best)


def measure(shots):
    towers = {t['name']: t for t in json.loads((HERE / 'towers.json').read_text())['towers']}
    res = {}
    for tn, (hexc, poses, tol) in SWATCHES.items():
        reg = REGION.get(tn)
        t = towers[reg[0] if reg else tn]
        for pn in poses:
            I = np.asarray(Image.open(shots / (pn + '.jpg')).convert('RGB')).astype(float)
            M = np.asarray(Image.open(shots / (pn + '-MASK.jpg')).convert('RGB')).astype(float)
            Gl = np.asarray(Image.open(shots / (pn + '-GLASS.jpg')).convert('RGB')).astype(float)
            A = np.asarray(Image.open(shots / (pn + '-ID.jpg')).convert('RGB')).astype(float)
            B = np.asarray(Image.open(shots / (pn + '-ID2.jpg')).convert('RGB')).astype(float)
            gm = (M[..., 0] > M[..., 1] + 25) & (M[..., 2] > M[..., 1] + 25)
            box = tower_box(POSES[pn], t, reg[1:] if reg else None)
            if box is None:
                continue
            x0, y0, x1, y1 = box
            sub = np.zeros_like(gm); sub[y0:y1, x0:x1] = gm[y0:y1, x0:x1]
            if sub.sum() < 200:
                continue
            c = project(POSES[pn], [(t['x'], (reg[1] + reg[2]) / 2 if reg else t['h'] * 0.55, t['z'])])
            if not c:
                continue
            own = own_pixels(reg[0] if reg else tn, t, A, B, sub, box, c[0][0])
            if own is None or own.sum() < 100:
                continue
            # the colour is the glass's own (no frame, spandrel or cap: view 9), the contrast the whole face's (frames and glass)
            gl = own & (Gl[..., 0] > Gl[..., 1] + 25) & (Gl[..., 2] > Gl[..., 1] + 25)
            sub = gl if gl.sum() >= 100 else own
            mean = [round(float(v), 1) for v in I[sub].mean(0)]
            lum = (I[own] * [0.2126, 0.7152, 0.0722]).sum(-1)
            rows = np.where(own.sum(1) >= 3)[0]
            vis = (rows.max() - rows.min() + 1) / max(y1 - y0, 1) if len(rows) else 0.0
            p10, p90 = np.percentile(lum, 10), np.percentile(lum, 90)
            res.setdefault(tn, {})[pn] = {'mean': mean, 'px': int(sub.sum()), 'dE': round(delta_e(mean, hex_rgb(hexc)), 1),
                                          'db': round(float(lab(mean)[2] - lab(hex_rgb(hexc))[2]), 1),
                                          'p10': round(float(p10), 1), 'p90': round(float(p90), 1), 'contrast': round(float(p90 / max(p10, 1.0)), 2),
                                          'vis': round(float(vis), 2), 'face': [round(float(v), 1) for v in I[own].mean(0)]}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', default='')
    ap.add_argument('--shots', default='')
    ap.add_argument('--judge', action='store_true', help='freeze each tower\'s judged poses (JUDGE) from this run')
    a = ap.parse_args()
    if a.judge:
        global SWATCHES
        SWATCHES = {k: (v[0], [p for p in POSES if p != 'onelib-crown'] if k not in REGION else v[1], v[2]) for k, v in SWATCHES.items()}
    if a.shots:
        res = measure(Path(a.shots))
    else:
        if not RENDER.exists():
            sys.exit('the capture skill\'s render.mjs is missing: ' + str(RENDER))
        tmp = Path(tempfile.mkdtemp(prefix='glass-cal-'))
        try:
            stage = tmp / 'serve'; stage.mkdir()
            shutil.copy(HERE / 'society-hill-towers.html', stage / 'page.html')
            shutil.copytree(HERE / 'art', stage / 'art')
            poses = []
            for pn, p in POSES.items():
                for suf, z in (('', 0), ('-MASK', 6), ('-ID', 7), ('-ID2', 8), ('-GLASS', 9)):
                    poses.append({'name': pn + suf, 'pos': p['pos'], 'look': p['look'], 'clock': p['clock'], 'js': '__dbg.glass().u.uGlassK.value.z = %d' % z})
            (tmp / 'poses.json').write_text(json.dumps(poses))
            shots = Path(a.keep) if a.keep else tmp / 'shots'
            r = subprocess.run(['node', str(RENDER), '--dir', str(stage), '--page', 'page.html', '--poses', str(tmp / 'poses.json'), '--out', str(shots),
                                '--query', QUERY, '--w', str(W), '--h', str(H)], capture_output=True, text=True, timeout=3000)
            if r.returncode != 0:
                sys.exit('render failed: ' + (r.stderr or r.stdout)[-2000:])
            summary = json.loads(r.stdout[r.stdout.index('{'):])
            if summary.get('failed') or any('rror' in c for c in summary.get('console', [])):
                sys.exit('the page reported: ' + json.dumps({'failed': summary.get('failed'), 'console': summary.get('console')})[:2000])
            res = measure(shots)
        finally:
            if not a.keep:
                shutil.rmtree(tmp, ignore_errors=True)
    if a.judge:
        J = {}
        for tn, per in res.items():
            if tn in REGION:
                continue
            th = towers_by_name()[tn]['h']
            J[tn] = [pn for pn in POSES if pn in per and per[pn]['px'] >= JUDGE[0] and per[pn]['vis'] >= JUDGE[1] and POSES[pn]['pos'][1] <= th + JUDGE[2]]
        (HERE / 'tests' / 'glass_calibration_poses.json').write_text(json.dumps(J, indent=1) + '\n')
        for tn in SWATCHES:
            SWATCHES[tn] = (SWATCHES[tn][0], J.get(tn, SWATCHES[tn][1]), SWATCHES[tn][2])
        res = {tn: {pn: m for pn, m in per.items() if pn in SWATCHES[tn][1]} for tn, per in res.items()}
    out = {'note': 'glass_calibrate.py: each researched tower\'s glass at the poses it is judged at against its reference swatch (CIE76 delta E and b*), and the frames against the glass where CONTRAST bounds it',
           'fingerprint': fingerprint(), 'swatches': {k: {'hex': v[0], 'poses': v[1], 'tol': v[2]} for k, v in SWATCHES.items()},
           'hueB': HUE_B, 'judge': list(JUDGE), 'named': NAMED, 'open': {k: list(v) for k, v in OPEN.items()},
           'contrast': [{'tower': k[0], 'pose': k[1], 'max': v} for k, v in CONTRAST.items()], 'measured': res}
    OUT.write_text(json.dumps(out, indent=1) + '\n')
    bad = 0
    for tn, per in res.items():
        for pn, m in per.items():
            f = ('dE' if m['dE'] > SWATCHES[tn][2] else '') + (' b*' if abs(m['db']) > HUE_B else '')
            bad += 1 if f else 0
            print('%-44s %-17s %-24s dE %5.1f db %+5.1f (tol %d)  px %6d vis %.2f  p90/p10 %.2f %s' % (tn[:44], pn, m['mean'], m['dE'], m['db'], SWATCHES[tn][2], m['px'], m['vis'], m['contrast'], f))
    print('measures %d, failing %d, coded %d' % (sum(len(v) for v in res.values()), bad, len(CODED)))


if __name__ == '__main__':
    main()
