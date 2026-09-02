#!/usr/bin/env python3
"""philly3d lightning relay: real strikes for the page, from the Blitzortung community network.

Subscribes (plain MQTT 3.1.1 over TCP, standard library only) to the public
Blitzortung relay that the Home Assistant integration uses, keeps every strike
inside --radius-km of the towers for --window-min minutes, and publishes
/var/www/philly3d/lightning.json every 2 s (atomic rename, gzip twin for
nginx gzip_static), which the page polls every 4 s and renders as bolts at the
real positions. One upstream connection for every viewer.

    {"t": <unix write time>, "src": <unix time of the last strike received>,
     "n10": <strikes in the last 10 min within 80 km>, "nearest_km": <or null>,
     "strikes": [[t_unix, lat, lon, km], ...]}      # oldest first

Topics are geohash-based (blitzortung/1.1/d/r/4/...): 'dr' and 'dq' together
cover latitude 33.75 to 45 N, longitude 78.75 to 67.5 W, which is far more than
50 miles around Philadelphia. Payload: {"lat", "lon", "status", "region", "time" (ns)}.
Data (c) Blitzortung.org contributors, for personal and non-commercial use.

    lightning_relay.py --out /var/www/philly3d/lightning.json
    lightning_relay.py --out /tmp/lightning.json --seconds 40     # a timed test run
"""
import argparse, json, logging, math, os, socket, struct, sys, threading, time
from collections import deque

try:
    from septa_bake import write_atomic, publish     # same directory on the VPS (/opt/philly3d)
except Exception:                                    # standalone fallback (a test run from elsewhere)
    import gzip, tempfile
    def write_atomic(path, data, mode=0o644):
        d = os.path.dirname(path) or '.'
        fd, tmp = tempfile.mkstemp(prefix='.lightning-', dir=d)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
            os.chmod(tmp, mode); os.replace(tmp, path)
        except Exception:
            try: os.unlink(tmp)
            except OSError: pass
            raise
    def publish(path, obj):
        raw = json.dumps(obj, separators=(',', ':')).encode()
        gz_path = path + '.gz'
        buf = gzip.compress(raw, compresslevel=6, mtime=0)
        write_atomic(gz_path, buf)          # the gz twin first: gzip_static must never serve a stale one
        write_atomic(path, raw)

log = logging.getLogger('lightning')
HOST, PORT = 'blitzortung.ha.sed.pl', 1883
TOPICS = ['blitzortung/1.1/d/r/#', 'blitzortung/1.1/d/q/#']
LAT0, LON0 = 39.9455, -75.1447          # the towers, the page's origin
KEEPALIVE = 60
BACKOFF_MIN, BACKOFF_MAX = 5, 120


def km_from_site(lat, lon):
    return 111.32 * math.hypot(lat - LAT0, (lon - LON0) * math.cos(math.radians(LAT0)))


# ---- a small MQTT 3.1.1 client: CONNECT, SUBSCRIBE, PINGREQ, PUBLISH parsing
def _str(s):
    b = s.encode(); return struct.pack('>H', len(b)) + b

def _remlen(n):
    out = b''
    while True:
        d = n % 128; n //= 128
        out += bytes([d | (0x80 if n else 0)])
        if not n: return out

def _packet(t, body):
    return bytes([t]) + _remlen(len(body)) + body


class Mqtt:
    def __init__(self, host, port, timeout=8):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(2.0)
        self.buf = b''
        self.last_tx = time.time()
        cid = 'philly3d-lightning-%d' % (int(time.time()) % 100000)
        var = _str('MQTT') + bytes([4, 0x02]) + struct.pack('>H', KEEPALIVE) + _str(cid)
        self.sock.sendall(_packet(0x10, var))
        ack = self._read_exact(4)
        if len(ack) < 4 or ack[0] >> 4 != 2 or ack[3] != 0:
            raise ConnectionError('CONNACK refused: %s' % ack.hex())

    def _read_exact(self, n):
        out = b''
        deadline = time.time() + 10
        while len(out) < n and time.time() < deadline:
            try:
                c = self.sock.recv(n - len(out))
            except socket.timeout:
                continue
            if not c: break
            out += c
        return out

    def subscribe(self, topics):
        body = struct.pack('>H', 1)
        for t in topics: body += _str(t) + bytes([0])
        self.sock.sendall(_packet(0x82, body))
        self.last_tx = time.time()

    def ping(self):
        self.sock.sendall(b'\xc0\x00'); self.last_tx = time.time()

    def messages(self):
        """Yield (topic, payload) forever; raises on a dead socket."""
        while True:
            if time.time() - self.last_tx > KEEPALIVE / 2: self.ping()
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk: raise ConnectionError('socket closed')
            self.buf += chunk
            while len(self.buf) >= 2:
                mult, ln, i = 1, 0, 1
                while True:
                    if i >= len(self.buf): ln = None; break
                    d = self.buf[i]; ln += (d & 127) * mult; mult *= 128; i += 1
                    if not (d & 128): break
                if ln is None or len(self.buf) < i + ln: break
                t = self.buf[0] >> 4; body = self.buf[i:i + ln]; self.buf = self.buf[i + ln:]
                if t == 3:
                    tl = struct.unpack('>H', body[:2])[0]
                    yield body[2:2 + tl].decode(errors='replace'), body[2 + tl:]

    def close(self):
        try: self.sock.sendall(b'\xe0\x00')
        except OSError: pass
        try: self.sock.close()
        except OSError: pass


class Strikes:
    def __init__(self, radius_km, window_min):
        self.radius = radius_km; self.window = window_min * 60
        self.q = deque(); self.lock = threading.Lock(); self.src = 0.0

    def add(self, lat, lon, t_s):
        km = km_from_site(lat, lon)
        if km > self.radius: return False
        with self.lock:
            self.q.append((round(t_s, 3), round(lat, 5), round(lon, 5), round(km, 1)))
            self.src = max(self.src, t_s)
        return True

    def snapshot(self):
        now = time.time()
        with self.lock:
            while self.q and now - self.q[0][0] > self.window: self.q.popleft()
            arr = sorted(self.q)
            src = self.src
        recent = [s for s in arr if now - s[0] <= 600 and s[3] <= 80]
        nearest = min((s[3] for s in recent), default=None)
        return {'t': round(now, 1), 'src': round(src, 1), 'n10': len(recent), 'nearest_km': nearest, 'strikes': arr}


def reader(strikes, stop):
    backoff = BACKOFF_MIN
    while not stop.is_set():
        m = None
        try:
            log.info('connecting to %s:%d', HOST, PORT)
            m = Mqtt(HOST, PORT)
            m.subscribe(TOPICS)
            backoff = BACKOFF_MIN
            got = 0
            for topic, payload in m.messages():
                if stop.is_set(): break
                try:
                    d = json.loads(payload.decode('utf-8'))
                    lat, lon = float(d['lat']), float(d['lon'])
                    t_ns = float(d.get('time', 0))
                    t_s = t_ns / 1e9 if t_ns > 1e12 else time.time()
                except (ValueError, KeyError, TypeError):
                    continue
                if abs(time.time() - t_s) > 900: t_s = time.time()   # a wrong clock upstream: trust arrival
                if strikes.add(lat, lon, t_s):
                    got += 1
                    if got % 50 == 1: log.info('%d strikes kept so far', got)
        except Exception as e:
            log.warning('link down: %s', e)
        finally:
            if m: m.close()
        if stop.is_set(): break
        time.sleep(backoff)
        backoff = min(BACKOFF_MAX, backoff * 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default='/var/www/philly3d/lightning.json')
    ap.add_argument('--radius-km', type=float, default=110.0, help='keep strikes inside this (the page draws to 80 km)')
    ap.add_argument('--window-min', type=float, default=15.0)
    ap.add_argument('--interval', type=float, default=2.0, help='seconds between writes')
    ap.add_argument('--seconds', type=float, default=0, help='run this long then exit (a test)')
    ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.v else logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    strikes = Strikes(a.radius_km, a.window_min)
    stop = threading.Event()
    th = threading.Thread(target=reader, args=(strikes, stop), daemon=True); th.start()
    import signal
    for sg in (signal.SIGTERM, signal.SIGINT): signal.signal(sg, lambda *_: stop.set())
    t_end = time.time() + a.seconds if a.seconds else None
    try:
        while not stop.is_set():
            snap = strikes.snapshot()
            try:
                publish(a.out, snap)
            except Exception as e:
                log.error('write failed: %s', e)
            if t_end and time.time() >= t_end: break
            stop.wait(a.interval)
    finally:
        stop.set()
        snap = strikes.snapshot()
        log.info('exit: %d strikes in the window, %d in the last 10 min within 80 km', len(snap['strikes']), snap['n10'])


if __name__ == '__main__':
    main()
