#!/usr/bin/env python3
"""The glass towers' day calibration (Round 192's review: "too dark, too grey, and the blue is lost"). Renders the built
page headless at the standard noon poses (the capture skill's render.mjs on this Mac's GPU), each pose three times: as
drawn, with the glass alone as a flat mask (uGlassK.z 6) and with each curtain-wall system a colour of its own (5). For
each researched tower in SWATCHES the mean sRGB colour of its glass is taken over the mask inside the tower's projected
box (the box's own system colour only, so a tower behind it does not count), and compared with the tower's reference
swatch by CIE76 delta E. Writes tests/glass_calibration.json, which tests/test_glass_calibration.py checks: every tower
within its tolerance, and the measure taken on the shaders and systems the page has now (a fingerprint of the glass's
GLSL and of glass_art.json's systems and towers), so a change to the glass that is not re-measured fails the suite.
Round 192's second review added a pose a hundred metres off Comcast's south face at noon, where the tower must keep its
swatch and its frames must not stand out of its glass (the 90th over the 10th percentile of the face's luminance, CONTRAST:
the first cut's white joints over dark panes measured 3.3), and One Liberty's crown (REGION: the tower's box cut to the
crown's heights), whose chevrons had gone to a white lattice over tan.

Usage: python3 glass_calibrate.py [--keep DIR]   (after python3 build.py; about two minutes)"""
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
RENDER = HERE.parent / '.claude' / 'skills' / 'philly3d-capture' / 'scripts' / 'render.mjs'
OUT = HERE / 'tests' / 'glass_calibration.json'
W, H, FOV = 1280, 800, 58.0
# the standard poses: noon on Oct 14 in clear air, from the south-west over the skyline, a low flight over Rittenhouse, from
# the south over South Philadelphia
POSES = {
    'skyline-sw-day': {'pos': [-3100, 230, 250], 'look': [-2000, 150, -900], 'clock': [2026, 10, 14, 780]},
    'lowflight-day': {'pos': [-2500, 260, -250], 'look': [-2050, 150, -950], 'clock': [2026, 10, 14, 780]},
    'south-day': {'pos': [-1800, 150, 600], 'look': [-1950, 150, -850], 'clock': [2026, 10, 14, 780]},
    'comcast-south-100': {'pos': [-2035, 130, -920], 'look': [-2041, 140, -1025], 'clock': [2026, 10, 14, 780]},
    'onelib-crown': {'pos': [-1975, 240, -655], 'look': [-1995, 250, -784], 'clock': [2026, 10, 14, 780]},
}
# the reference swatches (sRGB), from the references glass_systems.json cites for each tower and the review's reading of
# them: Comcast a light silver blue (its own body), the CTC a pale neutral, the Liberty Places a mid blue, Cira a bright
# silver, The Laurel a warm greige; with the poses each is judged at and its tolerance (CIE76 delta E: under about 12
# a viewer calls two greys the same family and lightness, past 20 a different colour; the review's failures were 20 to 35)
SWATCHES = {
    'Comcast Center': ('#8FA3AE', ['skyline-sw-day', 'lowflight-day', 'comcast-south-100'], 15),
    'Comcast Technology Center': ('#A9B6BA', ['skyline-sw-day', 'south-day'], 15),
    'One Liberty Place': ('#5D7F9E', ['skyline-sw-day', 'lowflight-day'], 15),
    'Two Liberty Place': ('#5D7F9E', ['skyline-sw-day', 'lowflight-day'], 15),
    'Cira Centre': ('#A7B5C0', ['south-day'], 15),
    'The Laurel Rittenhouse Square (1911 Walnut)': ('#8E8A82', ['skyline-sw-day', 'lowflight-day'], 15),
    'One Liberty Place (crown)': ('#5D7F9E', ['onelib-crown', 'skyline-sw-day'], 15),
}
# a swatch measured over part of a tower: the tower it is part of and the heights (world metres) its box is cut to
REGION = {'One Liberty Place (crown)': ('One Liberty Place', 205.0, 268.0)}
# the frames against the glass: the 90th over the 10th percentile of the luminance over the tower's own glass, at most
CONTRAST = {('Comcast Center', 'comcast-south-100'): 2.0}
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


def measure(shots):
    towers = {t['name']: t for t in json.loads((HERE / 'towers.json').read_text())['towers']}
    res = {}
    for tn, (hexc, poses, tol) in SWATCHES.items():
        reg = REGION.get(tn)
        t = towers[reg[0] if reg else tn]
        for pn in poses:
            I = np.asarray(Image.open(shots / (pn + '.jpg')).convert('RGB')).astype(float)
            M = np.asarray(Image.open(shots / (pn + '-MASK.jpg')).convert('RGB')).astype(float)
            Y = np.asarray(Image.open(shots / (pn + '-SYS.jpg')).convert('RGB')).astype(float)
            gm = (M[..., 0] > M[..., 1] + 25) & (M[..., 2] > M[..., 1] + 25)
            box = tower_box(POSES[pn], t, reg[1:] if reg else None)
            if box is None:
                continue
            x0, y0, x1, y1 = box
            sub = np.zeros_like(gm); sub[y0:y1, x0:x1] = gm[y0:y1, x0:x1]
            if sub.sum() < 200:
                continue
            # the tower's own system colour: the commonest in the top third of its box (a tower's crown stands clear of
            # the ones in front of it), then every pixel of that colour in the box
            q = (Y // 24).astype(int); k = q[..., 0] * 10000 + q[..., 1] * 100 + q[..., 2]
            top = np.zeros_like(sub); yt = y0 + max(3, (y1 - y0) // 3); top[y0:yt, x0:x1] = sub[y0:yt, x0:x1]
            if reg:
                # part of a tower seen close: its own colour at the part's projected middle (the box's top third can hold
                # a taller neighbour behind it: the crown's first measure read Comcast)
                c = project(POSES[pn], [(t['x'], (reg[1] + reg[2]) / 2, t['z'])])
                if c:
                    cx, cy = int(c[0][0]), int(c[0][1])
                    top = np.zeros_like(sub); top[max(0, cy - 15):cy + 15, max(0, cx - 15):cx + 15] = sub[max(0, cy - 15):cy + 15, max(0, cx - 15):cx + 15]
            vals, cnt = np.unique(k[top if top.sum() >= 30 else sub], return_counts=True)
            sub &= k == vals[np.argmax(cnt)]
            if sub.sum() < 100:
                continue
            mean = [round(float(v), 1) for v in I[sub].mean(0)]
            lum = (I[sub] * [0.2126, 0.7152, 0.0722]).sum(-1)
            p10, p90 = np.percentile(lum, 10), np.percentile(lum, 90)
            res.setdefault(tn, {})[pn] = {'mean': mean, 'px': int(sub.sum()), 'dE': round(delta_e(mean, hex_rgb(hexc)), 1),
                                          'p10': round(float(p10), 1), 'p90': round(float(p90), 1), 'contrast': round(float(p90 / max(p10, 1.0)), 2)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', default='')
    a = ap.parse_args()
    if not RENDER.exists():
        sys.exit('the capture skill\'s render.mjs is missing: ' + str(RENDER))
    tmp = Path(tempfile.mkdtemp(prefix='glass-cal-'))
    try:
        stage = tmp / 'serve'; stage.mkdir()
        shutil.copy(HERE / 'society-hill-towers.html', stage / 'page.html')
        shutil.copytree(HERE / 'art', stage / 'art')
        poses = []
        for pn, p in POSES.items():
            for suf, z in (('', 0), ('-MASK', 6), ('-SYS', 5)):
                poses.append({'name': pn + suf, 'pos': p['pos'], 'look': p['look'], 'clock': p['clock'], 'js': '__dbg.glass().u.uGlassK.value.z = %d' % z})
        (tmp / 'poses.json').write_text(json.dumps(poses))
        shots = Path(a.keep) if a.keep else tmp / 'shots'
        r = subprocess.run(['node', str(RENDER), '--dir', str(stage), '--page', 'page.html', '--poses', str(tmp / 'poses.json'), '--out', str(shots),
                            '--query', QUERY, '--w', str(W), '--h', str(H)], capture_output=True, text=True, timeout=1500)
        if r.returncode != 0:
            sys.exit('render failed: ' + (r.stderr or r.stdout)[-2000:])
        summary = json.loads(r.stdout[r.stdout.index('{'):])
        if summary.get('failed') or any('rror' in c for c in summary.get('console', [])):
            sys.exit('the page reported: ' + json.dumps({'failed': summary.get('failed'), 'console': summary.get('console')})[:2000])
        res = measure(shots)
    finally:
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    out = {'note': 'glass_calibrate.py: each researched tower\'s glass at the standard noon poses against its reference swatch (CIE76 delta E), and the frames against the glass where CONTRAST bounds it',
           'fingerprint': fingerprint(), 'swatches': {k: {'hex': v[0], 'poses': v[1], 'tol': v[2]} for k, v in SWATCHES.items()},
           'contrast': [{'tower': k[0], 'pose': k[1], 'max': v} for k, v in CONTRAST.items()], 'measured': res}
    OUT.write_text(json.dumps(out, indent=1) + '\n')
    for tn, per in res.items():
        for pn, m in per.items():
            print('%-44s %-17s %-24s dE %5.1f (tol %d)  p90/p10 %.2f' % (tn[:44], pn, m['mean'], m['dE'], SWATCHES[tn][2], m['contrast']))


if __name__ == '__main__':
    main()
