#!/usr/bin/env python3
"""The installable app's icons into brand/dist/: icon-192.png and icon-512.png (the mark on
the ink plate, like the apple-touch-icon) and icon-512-maskable.png (the mark inside the
maskable safe zone, the outer fifth left to the plate, so Android's circles and squircles
crop nothing). build.py inlines them into manifest.webmanifest as data URLs. Deterministic
for a given sips and Pillow; run again only when mark.svg changes."""
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
INK = (0x17, 0x15, 0x12)


def sips_png(svg, size, out):
    subprocess.run(["sips", "-s", "format", "png", "-z", str(size), str(size), str(svg), "--out", str(out)],
                   check=True, capture_output=True)
    return Image.open(out).convert("RGBA")


def plate(size, mark_frac, out):
    mark = sips_png(ROOT / "mark.svg", 1024, DIST / "_mark1024.png")
    im = Image.new("RGBA", (size, size), INK + (255,))
    m = round(size * mark_frac)
    mk = mark.resize((m, m), Image.LANCZOS)
    im.alpha_composite(mk, ((size - m) // 2, (size - m) // 2))
    im.convert("RGB").save(out, optimize=True)
    print(f"{out.name}: {size}x{size}, mark {mark_frac:.2f}, {out.stat().st_size // 1024} KB")


def main():
    DIST.mkdir(exist_ok=True)
    plate(192, 0.78, DIST / "icon-192.png")
    plate(512, 0.78, DIST / "icon-512.png")
    plate(512, 0.60, DIST / "icon-512-maskable.png")
    (DIST / "_mark1024.png").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
