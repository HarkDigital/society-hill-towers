#!/usr/bin/env python3
"""ADVERSARIAL re-derivation: decode wide.b64 from scratch (format read from
pack_wide.py by the verifier, not copied from the audit script) and test
footprints against elevated c<=1 deck swaths, open sunken runs, corridor."""
import base64, struct, json, math, os

MD = "/Users/michaelharkins/Hark.Digital Dropbox/Mike Harkins/Claude Code/SHT/3d-model"

raw = base64.b64decode(open(os.path.join(MD, "wide.b64")).read())
magic, nb, nr, na = struct.unpack_from("<4i", raw, 0)
assert magic in (0x5348545A, 0x53485458), hex(magic)
has_attr = magic == 0x5348545A
body = struct.unpack_from("<%dh" % ((len(raw) - 16) // 2), raw, 16)
i = 0
buildings = []
for _ in range(nb):
    if has_attr:
        n, h5, mh5, typ, attr, roof = body[i:i+6]; i += 6
    else:
        n, h5, mh5, typ = body[i:i+4]; i += 4
    pts = [(body[i+2*k] / 5.0, body[i+2*k+1] / 5.0) for k in range(n)]
    i += 2 * n
    buildings.append((h5 / 5.0, mh5 / 5.0, typ, pts))
for _ in range(nr):
    n = body[i]; i += 3 + 2 * n
for _ in range(na):
    n = body[i]; i += 2 + 2 * n
leftover = len(body) - i
print(f"decoded: nb={nb} nr={nr} na={na} leftover_int16={leftover} (0 or 1 pad ok)")
assert leftover in (0, 1), leftover

ov = json.load(open(os.path.join(MD, "overpasses.json")))

def seg_seg_dist(p1, p2, p3, p4):
    def d2(a, b): return (a[0]-b[0])**2 + (a[1]-b[1])**2
    def pt_seg(p, a, b):
        ax, az = a; bx, bz = b
        dx, dz = bx-ax, bz-az
        L2 = dx*dx + dz*dz
        if L2 == 0: return d2(p, a)
        t = max(0.0, min(1.0, ((p[0]-ax)*dx + (p[1]-az)*dz) / L2))
        return d2(p, (ax + t*dx, az + t*dz))
    def ccw(a, b, c): return (c[1]-a[1])*(b[0]-a[0]) - (b[1]-a[1])*(c[0]-a[0])
    if (ccw(p1,p2,p3)*ccw(p1,p2,p4) < 0) and (ccw(p3,p4,p1)*ccw(p3,p4,p2) < 0):
        return 0.0
    return math.sqrt(min(pt_seg(p1,p3,p4), pt_seg(p2,p3,p4), pt_seg(p3,p1,p2), pt_seg(p4,p1,p2)))

def pip(x, z, poly):
    inside = False; j = len(poly) - 1
    for k in range(len(poly)):
        xi, zi = poly[k]; xj, zj = poly[j]
        if (zi > z) != (zj > z) and x < (xj-xi)*(z-zi)/(zj-zi+1e-12)+xi: inside = not inside
        j = k
    return inside

# build swath segment lists: (x1,z1,x2,z2,halfW,label)
def chain_segs(chains, label, halfw_fn):
    out = []
    for ci, ch in enumerate(chains):
        hw = halfw_fn(ch)
        p = ch["p"]
        for a, b in zip(p, p[1:]):
            out.append((a[0], a[1], b[0], b[1], hw, f"{label}[{ci}]"))
    return out

el_segs = chain_segs([c for c in ov["el"] if c["c"] <= 1], "el_c<=1", lambda c: c["w"]/2 - 1)
sk_open = [s for s in ov["sk"] if not s.get("cov")]
sk_segs = chain_segs(sk_open, "sk_open", lambda c: c["w"]/2 - 1)
cor_segs = []
for ci, run in enumerate(ov["cor"]):
    for a, b in zip(run, run[1:]):
        cor_segs.append((a[0], a[1], b[0], b[1], max(a[3], b[3]), f"cor[{ci}]"))
print(f"el chains c<=1: {sum(1 for c in ov['el'] if c['c']<=1)}, el segs {len(el_segs)}; sk open {len(sk_open)}; cor segs {len(cor_segs)}")

# grid index of segments (cell 100 m, pad by halfW)
CELL = 100.0
grid = {}
allsegs = el_segs + sk_segs + cor_segs
for si, s in enumerate(allsegs):
    x1, z1, x2, z2, hw, _ = s
    for gx in range(int((min(x1,x2)-hw)//CELL), int((max(x1,x2)+hw)//CELL)+1):
        for gz in range(int((min(z1,z2)-hw)//CELL), int((max(z1,z2)+hw)//CELL)+1):
            grid.setdefault((gx, gz), []).append(si)

offenders = []
for h, mh, typ, poly in buildings:
    if h < 4 or len(poly) < 3: continue
    xs = [q[0] for q in poly]; zs = [q[1] for q in poly]
    cand = set()
    for gx in range(int(min(xs)//CELL), int(max(xs)//CELL)+1):
        for gz in range(int(min(zs)//CELL), int(max(zs)//CELL)+1):
            cand.update(grid.get((gx, gz), []))
    if not cand: continue
    cx = sum(xs)/len(xs); cz = sum(zs)/len(zs)
    hit = None; how = None
    edges = list(zip(poly, poly[1:] + [poly[0]]))
    for si in cand:
        x1, z1, x2, z2, hw, lab = allsegs[si]
        # (a) footprint edge within halfW of chain segment
        for (pa, pb) in edges:
            if seg_seg_dist(pa, pb, (x1, z1), (x2, z2)) < hw:
                hit, how = lab, "edge-overlap"; break
        if hit: break
        # (b) chain endpoint inside polygon (chain fully inside footprint)
        if pip(x1, z1, poly) or pip(x2, z2, poly):
            hit, how = lab, "chain-inside-poly"; break
    if hit:
        offenders.append({"x": round(cx,1), "z": round(cz,1), "h": h, "minH": mh,
                          "type": typ, "swath": hit, "how": how})

print(f"\noffenders (h>=4, footprint intersects swath): {len(offenders)}")
for o in sorted(offenders, key=lambda o: o["z"]):
    print(o)
