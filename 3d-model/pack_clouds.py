#!/usr/bin/env python3
"""Pack the low-poly cloud models (3d assets/Clouds/Clouds.FBX, nine meshes from 3ds Max,
Y-up, all triangles) into clouds.json for the app's low-poly cloud field (Round 67).

Each model is centred on its bounding box and scaled so its width (x extent) is 1, so the
app's per-instance scale is the cloud's width in metres; positions are rounded to 1e-4.

    {"models": [{"h": <height / width>, "d": <depth / width>, "n": <vertices>,
                 "v": [x, y, z, ...], "i": [a, b, c, ...]}, ...]}

Stdlib only: a minimal binary FBX reader (version 7400: 32-bit node records, zlib arrays).
Usage: python3 pack_clouds.py [--fbx PATH] [--out clouds.json]"""
import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_FBX = HERE.parent / '3d assets' / 'Clouds' / 'Clouds.FBX'


def read_fbx(data):
    if data[:20] != b'Kaydara FBX Binary  ':
        sys.exit('not a binary FBX')
    version = struct.unpack('<I', data[23:27])[0]
    big = version >= 7500

    def read_prop(p):
        t = data[p:p + 1]
        p += 1
        if t == b'Y':
            return struct.unpack('<h', data[p:p + 2])[0], p + 2
        if t == b'C':
            return bool(data[p]), p + 1
        if t == b'I':
            return struct.unpack('<i', data[p:p + 4])[0], p + 4
        if t == b'F':
            return struct.unpack('<f', data[p:p + 4])[0], p + 4
        if t == b'D':
            return struct.unpack('<d', data[p:p + 8])[0], p + 8
        if t == b'L':
            return struct.unpack('<q', data[p:p + 8])[0], p + 8
        if t in (b'f', b'd', b'l', b'i', b'b'):
            n, enc, clen = struct.unpack('<III', data[p:p + 12])
            p += 12
            raw = data[p:p + clen]
            p += clen
            if enc == 1:
                raw = zlib.decompress(raw)
            fmt = {b'f': 'f', b'd': 'd', b'l': 'q', b'i': 'i', b'b': 'b'}[t]
            return list(struct.unpack('<' + fmt * n, raw[:n * struct.calcsize(fmt)])), p
        if t in (b'S', b'R'):
            n = struct.unpack('<I', data[p:p + 4])[0]
            p += 4
            return data[p:p + n], p + n
        sys.exit('unknown FBX property type %r' % t)

    def read_node(p):
        if big:
            end, nprops, plen = struct.unpack('<QQQ', data[p:p + 24])
            p += 24
        else:
            end, nprops, plen = struct.unpack('<III', data[p:p + 12])
            p += 12
        nlen = data[p]
        p += 1
        name = data[p:p + nlen].decode('ascii', 'replace')
        p += nlen
        if end == 0:
            return None, p
        props = []
        for _ in range(nprops):
            v, p = read_prop(p)
            props.append(v)
        children = []
        while p < end:
            child, p = read_node(p)
            if child is None:
                break
            children.append(child)
        return (name, props, children), end

    nodes, pos = [], 27
    while pos < len(data):
        node, pos = read_node(pos)
        if node is None:
            break
        nodes.append(node)
    return version, nodes


def geometries(nodes):
    objects = next(n for n in nodes if n[0] == 'Objects')[2]
    out = []
    for g in objects:
        if g[0] != 'Geometry':
            continue
        verts = idx = None
        for c in g[2]:
            if c[0] == 'Vertices':
                verts = c[1][0]
            elif c[0] == 'PolygonVertexIndex':
                idx = c[1][0]
        if verts and idx:
            out.append((verts, idx))
    return out


def pack(verts, idx):
    n = len(verts) // 3
    xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
    cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
    w = max(xs) - min(xs) or 1.0
    v = []
    for k in range(n):
        v += [round((xs[k] - cx) / w, 4), round((ys[k] - cy) / w, 4), round((zs[k] - cz) / w, 4)]
    tris, poly = [], []
    for i in idx:   # a negative index (-i - 1) closes a polygon; fan-triangulate anything wider than a triangle
        if i < 0:
            poly.append(-i - 1)
            for k in range(1, len(poly) - 1):
                tris += [poly[0], poly[k], poly[k + 1]]
            poly = []
        else:
            poly.append(i)
    if max(tris) >= n:
        sys.exit('index out of range')
    return {'h': round((max(ys) - min(ys)) / w, 4), 'd': round((max(zs) - min(zs)) / w, 4), 'n': n, 'v': v, 'i': tris}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--fbx', default=str(DEFAULT_FBX))
    ap.add_argument('--out', default=str(HERE / 'clouds.json'))
    a = ap.parse_args()
    version, nodes = read_fbx(Path(a.fbx).read_bytes())
    models = [pack(v, i) for v, i in geometries(nodes)]
    if not models:
        sys.exit('no geometry in the FBX')
    models.sort(key=lambda m: m['n'])
    Path(a.out).write_text(json.dumps({'models': models}, separators=(',', ':')), encoding='utf-8')
    print('fbx %d: %d models, %d vertices, %d triangles -> %s (%d bytes)' % (
        version, len(models), sum(m['n'] for m in models), sum(len(m['i']) // 3 for m in models), a.out, Path(a.out).stat().st_size))


if __name__ == '__main__':
    main()
