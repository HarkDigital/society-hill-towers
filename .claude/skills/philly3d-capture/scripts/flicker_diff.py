#!/usr/bin/env python3
"""Flicker diff (Round 144): z-fighting shows as pixels that change between captures a few decimetres apart.

Capture three frames 0.5 m apart with __cap as PNG (a jpeg's own noise swamps the count), e.g.
  __cap('fl-a.png', x, y, z, yaw, pitch, 8); __cap('fl-b.png', x + .4, y + .2, z - .4, ...); __cap('fl-c.png', x + .8, ...)
then: python3 flicker_diff.py captures/fl [--rows 280:640] [--crop 200,330,760,620]
It prints the pixels changing by more than 60 (summed RGB) between neighbouring frames and writes <prefix>-mask.png
(the changing pixels in red over frame a) and, with --crop, <prefix>-crop.png (a over b, doubled). Limit: the camera's
own motion changes pixels at every silhouette edge, so compare the count before and after a fix at the same poses and
read it with the crop, never alone."""
import argparse
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('prefix')
ap.add_argument('--rows', default=None, help='y0:y1 band to count, default the whole frame')
ap.add_argument('--crop', default=None, help='x0,y0,x1,y1 for the side-by-side crop')
a = ap.parse_args()
A, B, C = [np.asarray(Image.open(a.prefix + s + '.png').convert('RGB')).astype(int) for s in ('-a', '-b', '-c')]
r = slice(*map(int, a.rows.split(':'))) if a.rows else slice(None)
d = lambda X, Y: np.abs(X[r] - Y[r]).sum(2)
changing = (d(A, B) > 60) | (d(B, C) > 60)
print('pixels changing >60 between 0.5 m steps:', int(changing.sum()))
m = np.zeros_like(A); m[r][..., 0] = changing * 255
Image.fromarray((A * 0.6 + m * 0.4).clip(0, 255).astype('uint8')).save(a.prefix + '-mask.png')
if a.crop:
    x0, y0, x1, y1 = map(int, a.crop.split(','))
    ia, ib = Image.open(a.prefix + '-a.png').crop((x0, y0, x1, y1)), Image.open(a.prefix + '-b.png').crop((x0, y0, x1, y1))
    out = Image.new('RGB', (x1 - x0, 2 * (y1 - y0))); out.paste(ia, (0, 0)); out.paste(ib, (0, y1 - y0))
    out.resize((2 * (x1 - x0), 4 * (y1 - y0))).save(a.prefix + '-crop.png')
