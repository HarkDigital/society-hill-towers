#!/usr/bin/env python3
"""aisstream.io -> /var/www/philly3d/ais.json relay for philly3d.com.

Why: an aisstream.io free key streams to ONE client at a time, so the page's
direct WebSocket meant the first open tab won the river and every other viewer
saw it empty. This relay holds the single upstream socket on the VPS, keeps
the fleet in memory keyed by MMSI, and every 4 s writes a static ais.json
(+ .gz twin for gzip_static) that any number of viewers can poll.

Output contract (the page parses exactly this -- keep it):

    {"t":   <unix seconds of this write>,
     "src": <unix seconds of the last message received from aisstream, 0 before the first>,
     "ships": [ {"mmsi": int,
                 "lat": float, "lon": float,
                 "sog": knots (float), "cog": degrees (float) or null,
                 "hdg": TrueHeading 0-359, 511 when the sensor reports unknown, null when absent,
                 "name": str ("" unknown), "type": AIS ship type int (0 unknown),
                 "len": Dimension A+B metres or null, "beam": C+D metres or null,
                 "dest": str ("" unknown), "nav": NavigationalStatus int or null,
                 "t": unix seconds of this vessel's last position report}, ... ]}

Only vessels with at least one position report are listed (ShipStaticData
alone gives nothing to place); a vessel unseen for 30 minutes is dropped.
Extraction mirrors app.js shipMsg: name from MetaData.ShipName or
ShipStaticData.Name (whichever arrived last, trimmed), length = A+B, beam =
C+D (raw metres -- the page clamps), type / destination from ShipStaticData,
sog / cog / heading / nav status from PositionReport. The page treats "t"
older than 60 s as "relay down"; a fresh "t" with an old "src" means the
relay is alive but upstream has gone quiet and it is reconnecting (backoff
15 s -> 4 min with jitter, exactly as the page did).

Key: AISSTREAM_KEY in the environment (systemd: EnvironmentFile=/etc/philly3d/ais.env,
a KEY=value file, mode 600) or --env-file to read that file directly. The key
is never logged or written anywhere.

Stdlib only: a minimal RFC 6455 client over ssl (aisstream sends BINARY frames
carrying UTF-8 JSON, plus the odd ping). No pip. Python 3.9+.

Usage:
    ais_relay.py [--out /var/www/philly3d/ais.json] [--env-file /etc/philly3d/ais.env] [-v]
"""
import argparse
import base64
import gzip
import hashlib
import json
import logging
import os
import random
import signal
import socket
import ssl
import struct
import sys
import tempfile
import threading
import time

WS_HOST = 'stream.aisstream.io'
WS_PORT = 443
WS_PATH = '/v0/stream'
# the subscription the page sends (app.js shipConnect)
BBOX = [[[39.80, -75.45], [40.08, -74.82]]]
FILTER = ['PositionReport', 'ShipStaticData']
DEFAULT_OUT = '/var/www/philly3d/ais.json'
DEFAULT_ENV = '/etc/philly3d/ais.env'
WRITE_EVERY = 4.0                  # seconds between ais.json writes
STALE_AFTER = 30 * 60              # drop a vessel unseen this long (page despawns at 30 min too)
SOCK_TIMEOUT = 30.0                # recv timeout; a ping goes out on each one
SILENT_LIMIT = 3                   # 3 x 30 s without a byte -> reconnect
BACKOFF_MIN = 15.0
BACKOFF_MAX = 240.0
MAX_FRAME = 4 * 1024 * 1024
KEYS = ('mmsi', 'lat', 'lon', 'sog', 'cog', 'hdg', 'name', 'type', 'len', 'beam', 'dest', 'nav', 't')

log = logging.getLogger('ais-relay')


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# ---------------------------------------------------------------- WebSocket client
class WSClient:
    """Just enough RFC 6455 to be a well-behaved client: TLS, handshake with
    Sec-WebSocket-Accept check, masked sends, fragment reassembly, ping/pong,
    close. Frames are parsed from a buffer without consuming partial ones, so a
    recv timeout mid-frame leaves the stream intact for the next call."""

    GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

    def __init__(self, host, port, path, timeout, tls=True):
        raw = socket.create_connection((host, port), timeout=timeout)
        if tls:
            ctx = ssl.create_default_context()
            self.sock = ctx.wrap_socket(raw, server_hostname=host)
        else:
            self.sock = raw
        self.sock.settimeout(timeout)
        self.buf = b''
        self.frag = bytearray()
        self.frag_op = None
        self.wlock = threading.Lock()
        key = base64.b64encode(os.urandom(16)).decode('ascii')
        req = ('GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
               'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n'
               'User-Agent: philly3d-ais-relay/1 (+https://philly3d.com)\r\n\r\n') % (path, host, key)
        self.sock.sendall(req.encode('ascii'))
        head = b''
        while b'\r\n\r\n' not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError('connection closed during handshake')
            head += chunk
            if len(head) > 65536:
                raise ConnectionError('handshake response too long')
        head, _, self.buf = head.partition(b'\r\n\r\n')
        lines = head.decode('latin-1').split('\r\n')
        if ' 101 ' not in lines[0] + ' ':
            raise ConnectionError('handshake refused: %s' % lines[0][:120])
        hdrs = {}
        for line in lines[1:]:
            k, _, v = line.partition(':')
            hdrs[k.strip().lower()] = v.strip()
        expect = base64.b64encode(hashlib.sha1((key + self.GUID).encode('ascii')).digest()).decode('ascii')
        if hdrs.get('sec-websocket-accept') != expect:
            raise ConnectionError('bad Sec-WebSocket-Accept')

    def _fill(self, n):
        """Ensure the buffer holds n bytes; a timeout leaves it intact."""
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError('connection closed')
            self.buf += chunk

    def recv_frame(self):
        self._fill(2)
        b1, b2 = self.buf[0], self.buf[1]
        ln = b2 & 0x7F
        hl = 2
        if ln == 126:
            self._fill(4)
            ln = struct.unpack('!H', self.buf[2:4])[0]
            hl = 4
        elif ln == 127:
            self._fill(10)
            ln = struct.unpack('!Q', self.buf[2:10])[0]
            hl = 10
        masked = bool(b2 & 0x80)
        if masked:
            hl += 4
        if ln > MAX_FRAME:
            raise ConnectionError('frame of %d bytes refused' % ln)
        self._fill(hl + ln)
        frame, self.buf = self.buf[:hl + ln], self.buf[hl + ln:]
        payload = frame[hl:]
        if masked:                                   # servers must not mask, but be lenient
            mask = frame[hl - 4:hl]
            payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        return bool(b1 & 0x80), b1 & 0x0F, payload

    def recv_message(self):
        """Next complete text/binary message as (opcode, bytes); control
        frames are answered inline. Raises socket.timeout on silence."""
        while True:
            fin, op, payload = self.recv_frame()
            if op == 0x8:
                code = struct.unpack('!H', payload[:2])[0] if len(payload) >= 2 else 1005
                try:
                    self.send_frame(0x8, payload[:2])
                except OSError:
                    pass
                raise ConnectionError('server closed the socket (%d)' % code)
            if op == 0x9:
                self.send_frame(0xA, payload)
                continue
            if op == 0xA:
                continue
            if op in (0x1, 0x2):
                if fin:
                    return op, payload
                self.frag = bytearray(payload)
                self.frag_op = op
                continue
            if op == 0x0:
                if self.frag_op is None:
                    raise ConnectionError('continuation frame without a start')
                self.frag += payload
                if fin:
                    op0, data = self.frag_op, bytes(self.frag)
                    self.frag_op, self.frag = None, bytearray()
                    return op0, data
                continue
            raise ConnectionError('unknown opcode %d' % op)

    def send_frame(self, op, payload=b''):
        head = bytearray([0x80 | op])
        n = len(payload)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack('!H', n)
        else:
            head.append(0x80 | 127)
            head += struct.pack('!Q', n)
        mask = os.urandom(4)
        head += mask
        body = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        with self.wlock:
            self.sock.sendall(bytes(head) + body)

    def send_text(self, text):
        self.send_frame(0x1, text.encode('utf-8'))

    def ping(self):
        self.send_frame(0x9, b'philly3d')

    def close(self):
        try:
            self.send_frame(0x8, struct.pack('!H', 1000))
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


# ---------------------------------------------------------------- fleet
class Fleet:
    def __init__(self):
        self.lock = threading.Lock()
        self.v = {}
        self.src = 0.0
        self.msgs = 0

    def handle(self, d, now):
        """Fold one aisstream message into the fleet (mirrors app.js shipMsg)."""
        meta = d.get('MetaData') or {}
        mmsi = meta.get('MMSI')
        if not _num(mmsi):
            try:
                mmsi = int(mmsi)
            except (TypeError, ValueError):
                return
        mmsi = int(mmsi)
        mt = d.get('MessageType')
        msg = d.get('Message') or {}
        with self.lock:
            self.src = now
            self.msgs += 1
            v = self.v.get(mmsi)
            if v is None:
                v = {'mmsi': mmsi, 'lat': None, 'lon': None, 'sog': 0.0, 'cog': None, 'hdg': None,
                     'name': '', 'type': 0, 'len': None, 'beam': None, 'dest': '', 'nav': None,
                     't': 0, 'seen': now}
                self.v[mmsi] = v
            v['seen'] = now
            name = meta.get('ShipName')
            if isinstance(name, str) and name.strip():
                v['name'] = name.strip()
            if mt == 'PositionReport' and isinstance(msg.get('PositionReport'), dict):
                m = msg['PositionReport']
                lat, lon = m.get('Latitude'), m.get('Longitude')
                if not (_num(lat) and _num(lon)):
                    return
                v['lat'] = round(float(lat), 6)
                v['lon'] = round(float(lon), 6)
                sog = m.get('Sog')
                v['sog'] = round(float(sog), 1) if _num(sog) else 0.0
                cog = m.get('Cog')
                v['cog'] = round(float(cog), 1) if _num(cog) else None
                th = m.get('TrueHeading')
                v['hdg'] = int(th) if _num(th) else None
                ns = m.get('NavigationalStatus')
                v['nav'] = int(ns) if _num(ns) else None
                v['t'] = int(now)
            elif mt == 'ShipStaticData' and isinstance(msg.get('ShipStaticData'), dict):
                s = msg['ShipStaticData']
                nm = s.get('Name')
                if isinstance(nm, str) and nm.strip():
                    v['name'] = nm.strip()
                dim = s.get('Dimension')
                if isinstance(dim, dict):
                    a, b, c, e = (dim.get(k) for k in ('A', 'B', 'C', 'D'))
                    length = (a if _num(a) else 0) + (b if _num(b) else 0)
                    beam = (c if _num(c) else 0) + (e if _num(e) else 0)
                    if length > 4:
                        v['len'] = int(length)
                    if beam > 1:
                        v['beam'] = int(beam)
                tp = s.get('Type')
                if _num(tp) and int(tp):
                    v['type'] = int(tp)
                dest = s.get('Destination')
                if isinstance(dest, str) and dest.strip():
                    v['dest'] = dest.strip()

    def snapshot(self, now):
        with self.lock:
            for m in [m for m, v in self.v.items() if now - v['seen'] > STALE_AFTER]:
                del self.v[m]
            ships = [{k: v[k] for k in KEYS} for v in self.v.values() if v['lat'] is not None]
            src = self.src
        ships.sort(key=lambda s: s['mmsi'])
        return {'t': int(now), 'src': int(src), 'ships': ships}


# ---------------------------------------------------------------- output
def write_atomic(path, data, mode=0o644):
    d = os.path.dirname(os.path.abspath(path)) or '.'
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.', suffix='.tmp', dir=d)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def publish(path, obj):
    raw = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    gz = gzip.compress(raw, compresslevel=6, mtime=0)
    write_atomic(path + '.gz', gz)       # twin first, so it is never older than the .json
    write_atomic(path, raw)
    return len(raw), len(gz)


# ---------------------------------------------------------------- upstream loop
class Link:
    """Holder for the live socket so the main thread can yank it on shutdown."""
    ws = None


def reader(key, fleet, stop, link):
    backoff = BACKOFF_MIN
    while not stop.is_set():
        ws = None
        got = 0
        try:
            log.info('connecting to wss://%s%s', WS_HOST, WS_PATH)
            ws = WSClient(WS_HOST, WS_PORT, WS_PATH, SOCK_TIMEOUT)
            link.ws = ws
            ws.send_text(json.dumps({'APIKey': key, 'BoundingBoxes': BBOX, 'FilterMessageTypes': FILTER}))
            silent = 0
            while not stop.is_set():
                try:
                    _op, payload = ws.recv_message()
                except socket.timeout:
                    silent += 1
                    if silent >= SILENT_LIMIT:
                        raise ConnectionError('no data for %d s' % int(SILENT_LIMIT * SOCK_TIMEOUT))
                    ws.ping()
                    continue
                silent = 0
                try:
                    d = json.loads(payload.decode('utf-8'))
                except (UnicodeDecodeError, ValueError):
                    log.debug('undecodable frame of %d bytes', len(payload))
                    continue
                if not isinstance(d, dict):
                    continue
                if 'error' in d and 'MessageType' not in d:
                    # e.g. {"error": "Api Key Is Not Valid"} -- keep backing off, never spin
                    raise ConnectionError('upstream says: %s' % str(d.get('error'))[:200])
                fleet.handle(d, time.time())
                got += 1
                if got == 1:
                    backoff = BACKOFF_MIN
                    log.info('stream live')
        except (OSError, ConnectionError) as e:             # ssl.SSLError, socket errors, our own
            log.warning('upstream: %s', e)
        except Exception:
            log.exception('unexpected error on the upstream socket; reconnecting')
        finally:
            link.ws = None
            if ws is not None:
                ws.close()
        if stop.is_set():
            break
        delay = backoff * (0.7 + random.random() * 0.6)
        log.info('reconnecting in %.0f s (%d messages this session)', delay, got)
        stop.wait(delay)
        backoff = min(backoff * 2, BACKOFF_MAX)


# ---------------------------------------------------------------- main
def load_key(env_file):
    key = os.environ.get('AISSTREAM_KEY', '').strip()
    if not key and env_file and os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, _, val = line.partition('=')
                if k.strip() == 'AISSTREAM_KEY':
                    key = val.strip().strip('"\'')
    return key


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=DEFAULT_OUT, help='output path (default %(default)s)')
    ap.add_argument('--env-file', default=DEFAULT_ENV,
                    help='KEY=value file read when AISSTREAM_KEY is not in the environment (default %(default)s)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format='%(asctime)s %(name)s %(levelname)s %(message)s',
                        stream=sys.stderr)
    key = load_key(a.env_file)
    if not key:
        log.error('no AISSTREAM_KEY in the environment or %s', a.env_file)
        return 2

    fleet = Fleet()
    stop = threading.Event()
    link = Link()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    t = threading.Thread(target=reader, args=(key, fleet, stop, link), name='upstream', daemon=True)
    t.start()
    log.info('writing %s every %.0f s', a.out, WRITE_EVERY)
    while not stop.wait(WRITE_EVERY):
        try:
            snap = fleet.snapshot(time.time())
            raw, gz = publish(a.out, snap)
            log.debug('%d ships, %d B (%d B gz)', len(snap['ships']), raw, gz)
        except Exception:
            log.exception('write failed; will retry')
    ws = link.ws
    if ws is not None:
        ws.close()                     # unblocks the reader's recv so it can see stop
    t.join(timeout=5)
    log.info('stopped')
    return 0


if __name__ == '__main__':
    sys.exit(main())
