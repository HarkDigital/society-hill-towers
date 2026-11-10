"""The generated art's files (Round 184, Mike's call: art loads on demand from philly3d.com instead of being inlined in
the page). The bakes write every image under 3d-model/art/<kind>/ with the first 10 hex of its sha256 in its name, so a
file never changes under a name: a browser may keep it forever, and a rolled-back page still finds its own art on the
server (deploy_philly3d.sh adds files there and never deletes). The page reads the paths from the small manifests
build.py still inlines. `write` returns the path relative to the page; `prune` removes the files of a kind the bake
did not write this time, so the checkout holds only what the current manifests name. `unhashed` is the deploy's proof of
the first sentence (Round 225): deploy_philly3d.sh sends the server only the files it does not have, which is right only
while a name can never come to mean other bytes."""
import hashlib, io, os, re, sys

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


def unhashed(root=ART):
    """The files under root whose name does not carry the first 10 hex of its own content's sha256, as paths relative to
    root (Round 225: the deploy's art rsync runs --ignore-existing, so every deploy stops re-dating all 782 files and
    with them nginx's ETag, which is a file's time and size; a file the server has is therefore never sent again, and
    one that is not named by its hash would be frozen there at its first copy. Measured Nov 10, 2026: 782 files,
    43,584,928 bytes, 0 exceptions). Anything counts, a .DS_Store too: the deploy stages the folder whole."""
    bad = []
    for d, _, files in os.walk(root):
        for f in files:
            path = os.path.join(d, f)
            m = re.fullmatch(r'[a-z0-9-]+\.([0-9a-f]{10})\.(?:webp|png|jpg)', f)
            with open(path, 'rb') as fh:
                if not m or hashlib.sha256(fh.read()).hexdigest()[:10] != m.group(1):
                    bad.append(os.path.relpath(path, root))
    return sorted(bad)


if __name__ == '__main__':
    # python3 art_files.py check [dir]: exit 1 and name the offenders (deploy_philly3d.sh runs it on the staged copy)
    if len(sys.argv) < 2 or sys.argv[1] != 'check' or len(sys.argv) > 3:
        sys.exit('usage: python3 art_files.py check [dir]')
    where = sys.argv[2] if len(sys.argv) > 2 else ART
    if not os.path.isdir(where):
        sys.exit('art_files: %s is not a folder' % where)
    wrong = unhashed(where)
    for w in wrong:
        print(w)
    if wrong:
        sys.exit('art_files: %d file(s) under %s are not named by their content\'s hash' % (len(wrong), where))
