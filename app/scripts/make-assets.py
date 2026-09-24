#!/usr/bin/env python3
"""The app's source images for @capacitor/assets, from the brand's own mark (../3d-model/brand/mark.svg), the way
brand/make_pwa_icons.py draws the web app's icons: the mark on the ink plate.
  assets/icon-only.png        1024 square, the mark at 0.78 on ink (iOS takes it as is; no transparency)
  assets/icon-foreground.png  1024 square, the mark at 0.60 on transparent (Android's adaptive icon safe zone)
  assets/icon-background.png  1024 square, plain ink
  assets/splash.png, splash-dark.png  2732 square, ink with the mark at 0.18
Then: npx @capacitor/assets generate --iconBackgroundColor '#171512' --splashBackgroundColor '#171512'"""
import subprocess
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
MARK = HERE.parent / '3d-model' / 'brand' / 'mark.svg'
OUT = HERE / 'assets'
INK = (0x17, 0x15, 0x12)


def mark(size):
    tmp = OUT / '_mark.png'
    subprocess.run(['sips', '-s', 'format', 'png', '-z', str(size), str(size), str(MARK), '--out', str(tmp)], check=True, capture_output=True)
    im = Image.open(tmp).convert('RGBA'); tmp.unlink()
    return im


def plate(size, frac, bg, out):
    m = round(size * frac)
    im = Image.new('RGBA', (size, size), bg)
    im.alpha_composite(mark(1024).resize((m, m), Image.LANCZOS), ((size - m) // 2, (size - m) // 2))
    (im.convert('RGB') if bg[3] == 255 else im).save(out, optimize=True)
    print(out.name, size, frac)


OUT.mkdir(exist_ok=True)
plate(1024, 0.78, INK + (255,), OUT / 'icon-only.png')
plate(1024, 0.60, (0, 0, 0, 0), OUT / 'icon-foreground.png')
Image.new('RGB', (1024, 1024), INK).save(OUT / 'icon-background.png')
plate(2732, 0.18, INK + (255,), OUT / 'splash.png')
plate(2732, 0.18, INK + (255,), OUT / 'splash-dark.png')
