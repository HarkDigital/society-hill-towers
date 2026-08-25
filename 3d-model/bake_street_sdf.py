#!/usr/bin/env python3
"""Bake the street-name atlas as a signed distance field.

The runtime canvas atlas stores raster coverage at 27 px rows; magnified 5-9x at
street-level zoom it reads pixelated no matter how the edges are thresholded.
This bakes each unique name from street_labels.json at 3x (81 px, Montserrat
SemiBold Italic from the variable TTF), computes a signed distance field
(vectorized numpy chamfer EDT; no scipy dependency), downsamples to the same
27 px-row layout the app already uses, and packs it into a 4096x2244 grayscale PNG. In the
SDF, 0.5 marks the glyph edge and each step of 1/16 is one final-res texel of
distance; the app thresholds it with fwidth AA, which stays crisp at any zoom.

Output: street_sdf.json  { "w", "h", "rowH", "pad", "rects": [[x,y,w,h]...]
(aligned with street_labels.json names order; null = did not fit), "png": b64 }.

Needs: Pillow, numpy, and the Montserrat Italic variable TTF (pass its path as
argv[1]; defaults to ./MontserratItalic.ttf).

Rerun after bake_street_labels.py whenever names change:
    python3 bake_street_labels.py && python3 bake_street_sdf.py <ttf>
"""
import base64
import io
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).parent
TTF = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "MontserratItalic.ttf"

SS = 3                      # supersample factor
FS, RH, PAD = 27, 34, 9     # final-res font size, row height, padding (match app.js)
MAXW = 560                  # final-res max name width (match the old fillText clamp)
AW, AH = 4096, 2244         # atlas size
SPREAD = 8.0                # SDF range in FINAL-res texels mapped to 0..0.5

font = ImageFont.truetype(str(TTF), FS * SS)
font.set_variation_by_axes([600])

names = json.loads((ROOT / "street_labels.json").read_text())["names"]


SQ2 = 1.41421356


def _sweep(d):
    """One chamfer pass, top-to-bottom, with vectorized in-row relaxation."""
    h, w = d.shape
    idx = np.arange(w, dtype=np.float32)
    for r in range(h):
        if r:
            up = d[r - 1]
            np.minimum(d[r], up + 1.0, out=d[r])
            np.minimum(d[r][1:], up[:-1] + SQ2, out=d[r][1:])
            np.minimum(d[r][:-1], up[1:] + SQ2, out=d[r][:-1])
        np.minimum(d[r], np.minimum.accumulate(d[r] - idx) + idx, out=d[r])
        rev = (d[r] + idx)[::-1]
        np.minimum(d[r], np.minimum.accumulate(rev)[::-1] - idx, out=d[r])
    return d


def edt(mask):
    """Chamfer(1, sqrt2) distance (px) to the nearest True cell — within ~8% of
    euclidean, far below a texel over this SDF's 8-texel spread."""
    d = np.where(mask, 0.0, 1e6).astype(np.float32)
    _sweep(d)
    _sweep(d[::-1])
    return d


def name_sdf(text):
    """Render one name at SS x, SDF it, downsample to final res. Returns float 0..1."""
    x0, y0, x1, y1 = font.getbbox(text)
    w = x1 - x0
    img = Image.new("L", (w + 24 * SS, RH * SS), 0)
    ImageDraw.Draw(img).text((12 * SS - x0, RH * SS // 2), text, fill=255, font=font, anchor="lm")
    if img.width > (MAXW + 24) * SS:                 # squeeze long names like fillText did
        img = img.resize(((MAXW + 24) * SS, RH * SS), Image.LANCZOS)
    a = np.asarray(img, dtype=np.float32) / 255.0
    inside = a >= 0.5
    if not inside.any():
        return None
    d_out = edt(inside)          # distance to glyph, outside
    d_in = edt(~inside)          # distance to background, inside
    signed = (d_in - d_out) / SS  # final-res texels; positive inside
    sdf = np.clip(0.5 + signed / (2.0 * SPREAD), 0.0, 1.0)
    # box-downsample SS x
    h2, w2 = sdf.shape[0] // SS, sdf.shape[1] // SS
    sdf = sdf[: h2 * SS, : w2 * SS].reshape(h2, SS, w2, SS).mean(axis=(1, 3))
    return sdf


atlas = np.zeros((AH, AW), dtype=np.float32)
rects = []
ax, ay = PAD, 0
for i, nm in enumerate(names):
    sdf = name_sdf(nm)
    if sdf is None:
        rects.append(None)
        continue
    h2, w2 = sdf.shape
    if ax + w2 + PAD > AW:
        ax, ay = PAD, ay + RH
    if ay + RH > AH:
        rects.append(None)
        continue
    atlas[ay : ay + h2, ax : ax + w2] = np.maximum(atlas[ay : ay + h2, ax : ax + w2], sdf)
    # the rect the app maps UVs to: trim the 12 px guard bands like measureText width
    rects.append([ax + 12 - PAD, ay, w2 - 24 + 2 * PAD, RH])
    ax += w2 - 24 + 2 * PAD + PAD
    if (i + 1) % 150 == 0:
        print(f"  {i + 1}/{len(names)}")

img = Image.fromarray((atlas * 255).astype(np.uint8), "L")
buf = io.BytesIO()
img.save(buf, format="PNG", optimize=True)
png_b64 = base64.b64encode(buf.getvalue()).decode()
fit = sum(1 for r in rects if r)
out = {"w": AW, "h": AH, "rowH": RH, "fs": FS, "spread": SPREAD, "rects": rects, "png": png_b64}
(ROOT / "street_sdf.json").write_text(json.dumps(out, separators=(",", ":")))
print(f"street_sdf.json: {fit}/{len(names)} names, png {len(png_b64) // 1024} KB b64, "
      f"rows used {ay // RH + 1}")
