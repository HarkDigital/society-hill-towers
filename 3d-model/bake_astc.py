"""Round 256 (Stage 4 of the Nov 10 plan, the ASTC art; Mike, Nov 18: "Do the next phase"): GPU-ready twins of the
phone's art, so a phone holds a quarter or a sixteenth of the bytes an RGBA8 texture costs and decodes nothing.

The first kind is the house fronts (fronts.json), for the side by side the plan asks for before anything is on by
default: per set, the half picture at 4x4 and 8x8 blocks, the full picture at 8x8 (four times the texels for the bytes of
the half at 4x4) and the half window mask at 4x4. The encoder is macOS's own (ImageIO; tools/astc_enc.swift, compiled
here with swiftc, so nothing is downloaded), which writes 4x4 and 8x8 blocks only.

Every twin carries its whole mip chain, made here: a colour map is averaged in linear light (the GPU's own mips of an
sRGB texture are), a mask in its coded values. three's flipY does not apply to compressed data, and none is needed:
ImageIO's ASTC writer already stores the block rows bottom first, as GL reads them (measured: a flip here as well drew every
atlas upside down). The container is the page's own (no KTX parser in the page): 'P3DA', block width, block height,
levels, flags (1 sRGB), width and height as little-endian u32; then each level's byte count (u32) and its ASTC blocks.
Files go under art/astc-<kind>/ named by their content's hash (art_files.write_bytes); astc_art.json names them.

usage: python3 bake_astc.py   (macOS with Xcode's swiftc)"""
import io, json, os, struct, subprocess, sys, tempfile
import numpy as np
from PIL import Image

import art_files

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL_SRC = os.path.join(HERE, 'tools', 'astc_enc.swift')
OUT = os.path.join(HERE, 'astc_art.json')
BLOCK = {'44': (4, 4), '88': (8, 8)}

_lut = np.array([((i / 255) / 12.92) if i / 255 <= 0.04045 else (((i / 255) + 0.055) / 1.055) ** 2.4 for i in range(256)], np.float64)


def to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def half(a, srgb):
    """One mip level down, as GL sizes it (each side halved, at least 1), a 2 by 2 box (a lone row or column kept)."""
    h, w = a.shape[:2]
    nh, nw = max(1, h // 2), max(1, w // 2)
    a = a[:nh * 2 if h > 1 else 1, :nw * 2 if w > 1 else 1]
    if h > 1:
        a = (a[0::2] + a[1::2]) / 2
    if w > 1:
        a = (a[:, 0::2] + a[:, 1::2]) / 2
    return a


def chain(im, srgb):
    """The level images as uint8 RGB arrays, the base first, down to 1 by 1."""
    a = np.asarray(im.convert('RGB'))   # unflipped: ImageIO writes the block rows bottom first, as GL reads them (the first try flipped here too and drew every atlas upside down)
    f = _lut[a] if srgb else a.astype(np.float64) / 255
    out = []
    while True:
        lv = to_srgb(f) if srgb else f
        out.append(np.clip(np.round(lv * 255), 0, 255).astype(np.uint8))
        if f.shape[0] == 1 and f.shape[1] == 1:
            return out
        f = half(f, srgb)


def encoder(tmp):
    exe = os.path.join(tmp, 'astc_enc')
    subprocess.run(['swiftc', '-O', '-o', exe, TOOL_SRC], check=True, capture_output=True)
    return exe


def twin(exe, tmp, path, block, srgb, kind, name):
    im = Image.open(os.path.join(HERE, path))
    levels = chain(im, srgb)
    jobs = []
    for i, lv in enumerate(levels):
        p = os.path.join(tmp, '%s-%d.png' % (name, i))
        Image.fromarray(lv, 'RGB').save(p)
        jobs.append('%s\t%s\t%s' % (p, p[:-4] + '.astc', block))
    jf = os.path.join(tmp, name + '.tsv')
    open(jf, 'w').write('\n'.join(jobs) + '\n')
    r = subprocess.run([exe, jf], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('bake_astc: the encoder failed on %s: %s' % (path, r.stdout + r.stderr))
    bw, bh = BLOCK[block]
    body = io.BytesIO()
    for i, lv in enumerate(levels):
        raw = open(os.path.join(tmp, '%s-%d.astc' % (name, i)), 'rb').read()
        if raw[:4] != b'\x13\xab\xa1\x5c' or (raw[4], raw[5]) != (bw, bh):
            sys.exit('bake_astc: %s level %d is not %dx%d ASTC' % (path, i, bw, bh))
        w, h = int.from_bytes(raw[7:10], 'little'), int.from_bytes(raw[10:13], 'little')
        blocks = raw[16:]
        want = -(-lv.shape[1] // bw) * -(-lv.shape[0] // bh) * 16
        if (w, h) != (lv.shape[1], lv.shape[0]) or len(blocks) != want:
            sys.exit('bake_astc: %s level %d came back %dx%d, %d bytes (want %dx%d, %d)' % (path, i, w, h, len(blocks), lv.shape[1], lv.shape[0], want))
        body.write(struct.pack('<I', len(blocks)))
        body.write(blocks)
    w0, h0 = levels[0].shape[1], levels[0].shape[0]
    head = b'P3DA' + bytes([bw, bh, len(levels), 1 if srgb else 0]) + struct.pack('<II', w0, h0)
    rel = art_files.write_bytes(head + body.getvalue(), kind, name, 'astc')
    return rel, w0, h0


def main():
    fronts = json.load(open(os.path.join(HERE, 'fronts.json')))
    out = {'v': 1, 'fronts': {}}
    kind = 'astc-fronts'
    with tempfile.TemporaryDirectory() as tmp:
        exe = encoder(tmp)
        for name, S in fronts['sets'].items():
            rec = {}
            for key, path, block, srgb in (('h4', S['imgHalf'], '44', True), ('h8', S['imgHalf'], '88', True),
                                           ('f8', S['img'], '88', True), ('m4', S['maskHalf'], '44', False)):
                rel, w, h = twin(exe, tmp, path, block, srgb, kind, '%s-%s' % (name, key))
                rec[key] = rel
                print('%-10s %s %4dx%-4d %8d bytes  %s' % (name, key, w, h, art_files.size(rel), rel))
            out['fronts'][name] = rec
    gone = art_files.prune(kind)
    json.dump(out, open(OUT, 'w'), indent=1, sort_keys=True)
    total = sum(art_files.size(p) for r in out['fronts'].values() for p in r.values())
    print('astc_art.json: %d front sets, %.1f MB of twins%s' % (len(out['fronts']), total / 1e6, ', %d stale removed' % gone if gone else ''))


if __name__ == '__main__':
    main()
