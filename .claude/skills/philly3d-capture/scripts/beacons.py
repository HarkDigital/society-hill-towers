"""Reduce philly3d.com's /b beacon log into per-load phases (Round 218, 220).

usage: ssh lionspool-vps "zcat -f /var/log/nginx/access.log /var/log/nginx/access.log.1 /var/log/nginx/access.log.[2-9].gz | grep '/b?'" > beacons.txt
       python3 beacons.py beacons.txt [--all]

A load is a run of lines from one ip and user agent whose t (performance.now() at the send) climbs. Each step beacon's ms is
that step's own duration; a computer beacons eight steps (BEACON_STEPS), a phone every one. Phases per load: t0 (navigation
start to app.js's first line) = ready.t - ready.ms; boot = the first step's start - t0; build = the step ms summed; gaps =
everything else before ready; enter_gap = ready to the Enter tap. Since Round 220 the beacons also carry the navigation
timing (tx, enc, dec, net, di, fcp), a boot checkpoint, every step's ms on ready (sp), the GPU bytes (gb, gbp, gbw) and each
phased step's parts (fd fl fg ff fr fa, wd wl wf, sm sp sf sc, ld lb lt lf, ts tl tf, cw cl cf): --all prints them.
"""
import collections
import re
import statistics
import sys
import urllib.parse

LINE = re.compile(r'^(\S+).*\[([^\]]+)\] "(?:GET|POST) /b\?(\S+)')


def loads_of(path):
    loads = []
    for line in open(path):
        m = LINE.search(line)
        if not m:
            continue
        q = dict(urllib.parse.parse_qsl(m.group(3)))
        ua = line.split('"')[-2]
        t = int(q.get('t', '0') or 0)
        last = loads[-1] if loads else None
        if last and last['ip'] == m.group(1) and last['ua'] == ua and t >= last['last'] and t - last['last'] < 3600000:
            last['ev'].append((q.get('st'), t, q)); last['last'] = t
        else:
            loads.append({'ip': m.group(1), 'ua': ua, 'start': m.group(2)[:20], 'ev': [(q.get('st'), t, q)], 'last': t})
    return loads


def device(load):
    q0 = load['ev'][0][2]
    kind = 'phone' if q0.get('tch') == '1' else 'desk'
    ua = load['ua']
    name = 'iPhone' if 'iPhone' in ua else 'iPad' if 'iPad' in ua else 'Android' if 'Android' in ua else 'Mac' if 'Macintosh' in ua else 'Win' if 'Windows' in ua else 'other'
    return kind, name + (' app' if 'Philly3DApp' in ua else '')


def main():
    path = sys.argv[1]
    show_all = '--all' in sys.argv
    agg = collections.defaultdict(list)
    for L in loads_of(path):
        ev = L['ev']; q0 = ev[0][2]
        ready = [e for e in ev if e[0] == 'ready']; steps = [e for e in ev if e[0] and e[0].startswith('step:')]
        enter = [e for e in ev if e[0] == 'enter']; perf = [e for e in ev if e[0] in ('perf', 'settled', 'late')]
        kind, name = device(L)
        if not ready or not steps:
            continue
        rt = ready[0][1]; rms = int(ready[0][2]['ms']); t0 = rt - rms
        first = steps[0]; boot = first[1] - int(first[2].get('ms', 0)) - t0
        bsum = sum(int(q.get('ms', 0)) for st, t, q in steps)
        eg = (int(enter[0][2]['ms']) - rt) if enter else None
        agg[(kind, name, q0.get('tier'))].append((t0, boot, bsum, rms - boot - bsum, rms, eg))
        print(f"{L['start']} {kind} {name} tier={q0.get('tier')} cores={q0.get('cores')} tx={q0.get('tx', '')} net={q0.get('net', '')} fcp={q0.get('fcp', '')} gb={ready[0][2].get('gb', '')}: t0={t0} boot={boot} build={bsum} gaps={rms - boot - bsum} ready={rms} enter_gap={eg}")
        durs = sorted(((int(q.get('ms', 0)), st[5:]) for st, t, q in steps), reverse=True)
        print('    top steps: ' + ', '.join(f'{n[:28]} {d}' for d, n in durs[:8]))
        if show_all:
            for st, t, q in steps:
                extra = {k: v for k, v in q.items() if k in ('fd', 'fl', 'fn', 'fg', 'ff', 'fr', 'fa', 'rk', 'rkn', 'wd', 'wl', 'wf', 'sm', 'sp', 'sf', 'sc', 'wj', 'ld', 'lb', 'lt', 'lf', 'ts', 'tl', 'tf', 'cw', 'cl', 'cf', 'gb')}
                if extra:
                    print('    ', st[5:][:30], extra)
            print('    ready:', {k: ready[0][2].get(k) for k in ('sp', 'prg', 'fl', 'flms', 'flp', 'pu', 'pub', 'tsk', 'sfw', 'sfb', 'gb', 'gbp', 'gbw', 'gbm')})
            for st, t, q in perf:
                print('    ', st, {k: q.get(k) for k in ('p50', 'p95', 'calls', 'tris', 'dpr', 'fg', 'jp', 'jr', 'dc1', 'dcn', 'poc', 'pos', 'gt', 'gtn', 'pr', 'rf', 'cm', 'sdn', 'sfd', 'gb')})
    print('\nMEDIANS by (device, tier): t0, boot, build, gaps, ready, enter_gap')
    for k, v in agg.items():
        med = lambda i: statistics.median([x[i] for x in v if x[i] is not None]) if any(x[i] is not None for x in v) else None
        print(k, 'n=', len(v), [med(i) for i in range(6)])


if __name__ == '__main__':
    main()
