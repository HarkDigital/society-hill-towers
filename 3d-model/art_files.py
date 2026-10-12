"""The generated art's files (Round 184, Mike's call: art loads on demand from philly3d.com instead of being inlined in
the page). The bakes write every image under 3d-model/art/<kind>/ with the first 10 hex of its sha256 in its name, so a
file never changes under a name: a browser may keep it forever, and a rolled-back page still finds its own art on the
server (deploy_philly3d.sh adds files there and never deletes). The page reads the paths from the small manifests
build.py still inlines. `write` returns the path relative to the page; `prune` removes the files of a kind the bake
did not write this time, so the checkout holds only what the current manifests name."""
import hashlib, io, os

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, 'art')
_written = {}


def write(im, kind, name, fmt='WEBP', **kw):
    b = io.BytesIO()
    im.save(b, fmt, **kw)
    data = b.getvalue()
    ext = {'WEBP': 'webp', 'PNG': 'png', 'JPEG': 'jpg'}[fmt]
    rel = 'art/%s/%s.%s.%s' % (kind, name, hashlib.sha256(data).hexdigest()[:10], ext)
    path = os.path.join(HERE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path + '.tmp', 'wb') as f:
            f.write(data)
        os.replace(path + '.tmp', path)
    _written.setdefault(kind, set()).add(os.path.basename(path))
    return rel


def size(rel):
    return os.path.getsize(os.path.join(HERE, rel))


def prune(kind):
    d = os.path.join(ART, kind)
    keep = _written.get(kind, set())
    gone = 0
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f not in keep:
                os.remove(os.path.join(d, f))
                gone += 1
    return gone
