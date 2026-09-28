"""The App Store Connect API from the command line, for TestFlight chores (Round 165, Sep 28: the first invites).

No packages: the ES256 token is signed with openssl and the calls go through urllib. The key and its ids never live in the
repo: ~/.appstoreconnect/philly3d.json holds {"key_id", "issuer", "app_id"} and the private key is
~/.appstoreconnect/private_keys/AuthKey_<key_id>.p8 (App Manager, QuincySoft LLC), both 0600. Nothing here prints the key
or the token; only Apple's answers.

  python3 app/scripts/asc.py status                  # every build's beta state, every group's testers and builds
  python3 app/scripts/asc.py invite <email>          # send or resend a tester's invitation to Philly3D
  python3 app/scripts/asc.py GET /v1/apps/<id>       # any other call; POST and PATCH take a JSON body as the third arg

The same key uploads without Xcode's sign-in: add -authenticationKeyPath, -authenticationKeyID and
-authenticationKeyIssuerID to the xcodebuild -exportArchive in app/README.md step 7."""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HOME = os.path.expanduser('~/.appstoreconnect')
CONF = json.load(open(os.path.join(HOME, 'philly3d.json')))
KEY_PATH = os.path.join(HOME, 'private_keys', 'AuthKey_' + CONF['key_id'] + '.p8')
OPENSSL = '/opt/homebrew/bin/openssl' if os.path.exists('/opt/homebrew/bin/openssl') else shutil.which('openssl')
API = 'https://api.appstoreconnect.apple.com'


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def der_to_raw(der):
    # openssl writes ECDSA-Sig-Value ::= SEQUENCE { r INTEGER, s INTEGER }; a JWT wants the 64-byte r||s
    assert der[0] == 0x30
    i = 2 if der[1] < 0x80 else 2 + (der[1] & 0x7f)
    out = b''
    for _ in range(2):
        assert der[i] == 0x02
        n = der[i + 1]
        out += der[i + 2:i + 2 + n].lstrip(b'\x00').rjust(32, b'\x00')
        i += 2 + n
    return out


def token(ttl=1100):
    now = int(time.time())
    head = b64u(json.dumps({'alg': 'ES256', 'kid': CONF['key_id'], 'typ': 'JWT'}, separators=(',', ':')).encode())
    body = b64u(json.dumps({'iss': CONF['issuer'], 'iat': now, 'exp': now + ttl, 'aud': 'appstoreconnect-v1'}, separators=(',', ':')).encode())
    with tempfile.NamedTemporaryFile() as f:
        f.write((head + '.' + body).encode()); f.flush()
        der = subprocess.run([OPENSSL, 'dgst', '-sha256', '-sign', KEY_PATH, f.name], check=True, capture_output=True).stdout
    return head + '.' + body + '.' + b64u(der_to_raw(der))


def call(method, path, body=None):
    req = urllib.request.Request(path if path.startswith('http') else API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw.decode(errors='replace')


def ok(st, js):
    if st >= 300:
        sys.exit(f'{st} {json.dumps(js)[:800]}')
    return js


def status():
    app = CONF['app_id']
    js = ok(*call('GET', f'/v1/builds?filter[app]={app}&include=buildBetaDetail&fields[builds]=version,processingState,expired,uploadedDate,buildBetaDetail&fields[buildBetaDetails]=internalBuildState,externalBuildState'))
    det = {d['id']: d['attributes'] for d in js.get('included', [])}
    for b in js['data']:
        a, d = b['attributes'], det.get(b['relationships']['buildBetaDetail']['data']['id'], {})
        print(f"build {a['version']}: {a['processingState']}, internal {d.get('internalBuildState')}, external {d.get('externalBuildState')}{', expired' if a['expired'] else ''}")
    for g in ok(*call('GET', f'/v1/betaGroups?filter[app]={app}&fields[betaGroups]=name,isInternalGroup'))['data']:
        testers = ok(*call('GET', f"/v1/betaGroups/{g['id']}/betaTesters?fields[betaTesters]=email,state"))['data']
        builds = ok(*call('GET', f"/v1/betaGroups/{g['id']}/builds?fields[builds]=version"))['data']
        kind = 'internal' if g['attributes']['isInternalGroup'] else 'external'
        print(f"group {g['attributes']['name']} ({kind}): builds {', '.join(x['attributes']['version'] for x in builds) or 'none'}")
        for t in testers:
            print(f"  {t['attributes']['email']}: {t['attributes']['state']}")


def invite(email):
    found = ok(*call('GET', f"/v1/betaTesters?filter[email]={urllib.request.quote(email)}&filter[apps]={CONF['app_id']}&fields[betaTesters]=email,state"))['data']
    if not found:
        sys.exit(f'{email} is not a tester of this app; add them to a group first')
    ok(*call('POST', '/v1/betaTesterInvitations', {'data': {'type': 'betaTesterInvitations', 'relationships': {
        'app': {'data': {'type': 'apps', 'id': CONF['app_id']}},
        'betaTester': {'data': {'type': 'betaTesters', 'id': found[0]['id']}}}}}))
    print(f'invitation sent to {email}')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['status']:
        status()
    elif a[:1] == ['invite'] and len(a) == 2:
        invite(a[1])
    elif len(a) >= 2:
        st, js = call(a[0].upper(), a[1], json.loads(a[2]) if len(a) > 2 else None)
        print(st)
        print(json.dumps(js, indent=1) if not isinstance(js, str) else js)
    else:
        sys.exit(__doc__)
