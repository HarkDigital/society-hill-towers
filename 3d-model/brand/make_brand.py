#!/usr/bin/env python3
"""Generate the Philly3D brand rasters into brand/dist/.

sips does the SVG rasterizing (verified crisp with alpha on this macOS),
PIL assembles the ico, flattens the touch icon, sets the wordmark, and
composites the share card. Rerun after editing mark.svg / favicon.svg /
og_raw.png. og.png is skipped (with a notice) until og_raw.png exists.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)

INK = (0x17, 0x15, 0x12)
PAPER = (0xEF, 0xE9, 0xDC)
BRONZE = (0xC8, 0x9B, 0x5E)


def sips_png(svg, size, out):
    subprocess.run(
        ["sips", "-s", "format", "png", "-z", str(size), str(size), str(svg), "--out", str(out)],
        check=True, capture_output=True,
    )
    return Image.open(out).convert("RGBA")


def favicons():
    renders = {}
    for n in (16, 32, 48):
        renders[n] = sips_png(ROOT / "favicon.svg", n, DIST / f"favicon-{n}.png")
    renders[48].save(DIST / "favicon.ico", format="ICO",
                     append_images=[renders[32], renders[16]])
    (DIST / "favicon.svg").write_bytes((ROOT / "favicon.svg").read_bytes())
    print("favicons: 16/32/48 png, ico, svg")


def touch_icon():
    mark = sips_png(ROOT / "mark.svg", 512, DIST / "_mark512.png")
    plate = Image.new("RGBA", (180, 180), INK + (255,))
    m = mark.resize((148, 148), Image.LANCZOS)
    plate.alpha_composite(m, (16, 16))
    plate.convert("RGB").save(DIST / "apple-touch-icon.png")
    print("apple-touch-icon: 180x180 on ink")


def wordmark(height):
    """Render PHILLY3D with 0.22em tracking, 3D in bronze, transparent ground."""
    font = ImageFont.truetype(str(ROOT / "Montserrat-SemiBold.ttf"), height)
    track = round(height * 0.22)
    chars = [(c, PAPER) for c in "PHILLY"] + [(c, BRONZE) for c in "3D"]
    widths = []
    for c, _ in chars:
        box = font.getbbox(c)
        widths.append((box[0], box[2] - box[0]))
    total = sum(w for _, w in widths) + track * (len(chars) - 1)
    ascent, descent = font.getmetrics()
    im = Image.new("RGBA", (total + 8, ascent + descent + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4
    for (c, color), (lsb, w) in zip(chars, widths):
        d.text((x - lsb, 4), c, font=font, fill=color + (255,))
        x += w + track
    return im.crop(im.getbbox())


def lockup():
    mark = Image.open(DIST / "_mark512.png").convert("RGBA")
    word = wordmark(150)
    mh = 232
    m = mark.resize((mh, mh), Image.LANCZOS)
    m = m.crop(m.getbbox())
    gap = 56
    pad = 8
    w = m.width + gap + word.width + pad * 2
    h = max(m.height, word.height) + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.alpha_composite(m, (pad, (h - m.height) // 2))
    im.alpha_composite(word, (pad + m.width + gap, (h - word.height) // 2))
    im.save(DIST / "lockup.png")
    print(f"lockup: {im.size}")


def og_card():
    raw = ROOT / "og_raw.png"
    if not raw.exists():
        print("og.png SKIPPED: capture brand/og_raw.png first (see og_sink.py)")
        return
    im = Image.open(raw).convert("RGB")
    tw, th = 1200, 630
    scale = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    im = im.crop(((im.width - tw) // 2, (im.height - th) // 2,
                  (im.width - tw) // 2 + tw, (im.height - th) // 2 + th))
    # legibility bed for the lockup: ink gradient rising from the bottom edge
    grad = Image.new("L", (1, th), 0)
    for y in range(th):
        a = max(0.0, (y - th * 0.52) / (th * 0.48))
        grad.putpixel((0, y), int(150 * a * a))
    shade = Image.new("RGB", (tw, th), INK)
    im = Image.composite(shade, im, grad.resize((tw, th)))
    lk = Image.open(DIST / "lockup.png").convert("RGBA")
    lw = 430
    lk = lk.resize((lw, round(lk.height * lw / lk.width)), Image.LANCZOS)
    im = im.convert("RGBA")
    im.alpha_composite(lk, (60, th - lk.height - 52))
    im.convert("RGB").save(DIST / "og.png", optimize=True)
    print(f"og.png: {tw}x{th}, {(DIST / 'og.png').stat().st_size // 1024} KB")


favicons()
touch_icon()
lockup()
og_card()
(DIST / "_mark512.png").unlink(missing_ok=True)
print("done ->", DIST)
