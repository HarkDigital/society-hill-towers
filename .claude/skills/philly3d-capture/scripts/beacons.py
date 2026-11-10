"""Reduce philly3d.com's /b beacon log into per-load phases (Round 218, 220).

usage: ssh lionspool-vps "zcat -f /var/log/nginx/access.log /var/log/nginx/access.log.1 /var/log/nginx/access.log.[2-9].gz | grep '/b?'" > beacons.txt
       python3 beacons.py beacons.txt [--all]

A load is a run of lines from one ip and user agent whose t (performance.now() at the send) climbs. Each step beacon's ms is
that step's own duration; a computer beacons eight steps (BEACON_STEPS), a phone every one. Phases per load: t0 (navigation
start to app.js's first line) = ready.t - ready.ms; boot = the first step's start - t0; build = the step ms summed; gaps =
everything else before ready; enter_gap = ready to the Enter tap. Since Round 220 the beacons also carry the navigation
timing (tx, enc, dec, net, di, fcp), a boot checkpoint, every step's ms on ready (sp), the GPU bytes (gb, gbp, gbw) and each
phased step's parts (fd fl fg ff fr fa, wd wl wf, sm sp sf sc, ld lb lt lf, ts tl tf, cw cl cf): --all prints them.

Round 226 (measurement round two) added, and --all prints each decoded (FIELDS names every number; a list's numbers are
joined by dots and its entries by underscores, which a query never escapes):
  every beacon: ws fs rs (the navigation's workerStart, fetchStart and responseStart, ms), gbs (GPU MB: buffers, textures,
    renderbuffers, and the part of the textures a framebuffer has attached).
  ready: cold (1, 0, or '' with under ten programs timed), lk (the programs timed and their ms apart, with the median
    program's), l5 (a cold load's five slowest programs, tag.ms), tu (texture calls), fll (flush renders by step), gw (each
    step's own yield wait, in sp's order), gi (the yields inside a step), gy (every yield), gf (the fences behind the
    flushes), hd hn (ms hidden before Ready and how often), bl (the ms of this load's bail beacon), cap (compressed formats
    and limits), db (the drawing buffer), gbf (geometry MB by family), on (scene objects and a matrix pass, us), an (art
    loads that ended in null), wn (measurement wraps that threw).
  enter: cold, f1p f1k f1t f15 (the first frame's programs, timers, texture calls and slowest), lit (ms from Ready to the
    lit button), eb (1 when the fallback timer drew the first frame).
  bail: cold. A bail is the first hide before Ready, not an abandonment: each is printed with whether Ready came later.
  ctxlost: d=1 is a computer's (Round 226 beacons it; before, only a phone's was sent), ar and ae after Ready and Enter.
  perf, settled, late: stl (stalls of 250 ms or more after Enter), prg, db, gbf, pl (pin landings), pt (the pins'
    captures), eh (eye-height bands), js (the JavaScript before the draw in five parts), fgl (frame gap after a landing
    frame against the rest), trm (the traffic reconcile's worst ms), an.
  pc, the last session's crumb, reads q.. for the 20 s after Ready: q seconds since Ready, e since Enter, f frames, m the
    last frame gap and w the worst (ms), gb b x r the GPU MB (all, buffers, textures, renderbuffers), p programs, l lit.
The medians are printed for cold and warm loads apart.
"""
import collections
import re
import statistics
import sys
import urllib.parse

# Round 226: the numbers of each dotted field, in order
FIELDS = {
    'lk': ('programs', 'compile_ms', 'link_ms', 'query_ms', 'intro_ms', 'drain_ms', 'median_ms'),
    'f1k': ('programs', 'compile_ms', 'link_ms', 'query_ms', 'intro_ms', 'drain_ms'),
    'tu': ('calls', 'ms'), 'f1t': ('calls', 'ms'),
    'gy': ('yields', 'ms', 'longest_ms', 'after_flush', 'after_flush_ms'),
    'gf': ('fences', 'late', 'lo_ms', 'hi_ms', 'longest_lo_ms', 'step', 'pending'),
    'gbs': ('buffers_mb', 'textures_mb', 'renderbuffers_mb', 'attached_mb'),
    'gbf': ('chunks_mb', 'roads_mb', 'flats_mb', 'instanced_mb', 'rest_mb', 'unsized'),
    'on': ('objects', 'matrix_us'),
    'stl': ('stalls', 'ms', 'with_programs', 'with_programs_ms', 'longest_ms'),
    'pl': ('landings', 'ms'),
    'pt': ('captures', 'tris_k', 'calls', 'cpu_tenths_ms', 'near'),
    'eh': ('under_12m', 'to_150m', 'to_755m', 'above'),
    'js': ('land_tenths', 'sim_tenths', 'live_tenths', 'steps_tenths', 'pins_tenths', 'frames'),
    'fgl': ('after_landing_tenths', 'landing_frames', 'other_tenths', 'other_frames'),
}
# the list fields: an entry's numbers
LISTS = {'fll': ('step', 'flushes', 'ms', 'programs'), 'gi': ('step', 'yields', 'ms')}
CAPS = {'a': 'ASTC', 'b': 'BPTC', 's': 'S3TC', 'r': 'RGTC', 'e': 'ETC2', '1': 'ETC1', 'p': 'PVRTC', 'k': 'parallel-compile', 't': 'gpu-timer'}
READY2 = ('cold', 'lk', 'l5', 'tu', 'fll', 'gw', 'gi', 'gy', 'gf', 'hd', 'hn', 'bl', 'cap', 'db', 'gbs', 'gbf', 'on', 'an', 'wn', 'ws', 'fs', 'rs')
ENTER2 = ('cold', 'f1', 'f1p', 'f1k', 'f1t', 'f15', 'lit', 'eb', 'tap')
RUN2 = ('stl', 'prg', 'db', 'gbs', 'gbf', 'pl', 'pt', 'eh', 'js', 'fgl', 'trm', 'an')


def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return v


def decode(key, value):
    """A Round 226 field as something a person can read: a dotted field as a dict of its named numbers, a list field as
    its entries, the slowest programs as (tag, ms) pairs; anything else as it came."""
    if value is None or value == '':
        return value
    if key in FIELDS:
        return dict(zip(FIELDS[key], [num(x) for x in value.split('.')]))
    if key in LISTS:
        return [dict(zip(LISTS[key], [num(x) for x in e.split('.')])) for e in value.split('_') if e]
    if key in ('l5', 'f15'):
        return [(e.rsplit('.', 1)[0], num(e.rsplit('.', 1)[1])) for e in value.split('_') if '.' in e]
    if key == 'gw':
        w = [num(x) for x in value.split('.')]
        top = sorted(((ms, i) for i, ms in enumerate(w) if isinstance(ms, int)), reverse=True)[:5]
        return {'steps': len(w), 'ms': sum(x for x in w if isinstance(x, int)), 'longest': [(i, ms) for ms, i in top if ms > 0]}
    if key == 'cap':
        p = value.split('.')
        return {'formats': [CAPS.get(c, c) for c in p[0] if c != '0'], 'max_texture': num(p[1]) if len(p) > 1 else '', 'max_samples': num(p[2]) if len(p) > 2 else ''}
    return value


def decoded(q, keys):
    return {k: decode(k, q.get(k)) for k in keys if q.get(k) not in (None, '')}


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
        # Round 226: a bail is the first hide before Ready, paired here with whether Ready came later in the same load; a
        # lost context is printed whatever else the load sent (a computer's is d=1)
        for st, t, q in ev:
            if st == 'bail':
                print(f"{L['start']} {kind} {name} bail at t={t} step={q.get('step', '')!r} cold={q.get('cold', '')}: " + (f"ready came later, at t={ready[0][1]} (hidden {ready[0][2].get('hd', '?')} ms in {ready[0][2].get('hn', '?')})" if ready and ready[0][1] >= t else 'no ready followed'))
            elif st == 'ctxlost':
                print(f"{L['start']} {kind} {name} ctxlost at t={t} front={q.get('f', '')} computer={q.get('d', '0')} after_ready={q.get('ar', '')} after_enter={q.get('ae', '')} gb={q.get('gb', '')} gbs={q.get('gbs', '')}")
        if not ready or not steps:
            continue
        rt = ready[0][1]; rms = int(ready[0][2]['ms']); t0 = rt - rms
        first = steps[0]; boot = first[1] - int(first[2].get('ms', 0)) - t0
        bsum = sum(int(q.get('ms', 0)) for st, t, q in steps)
        eg = (int(enter[0][2]['ms']) - rt) if enter else None
        cold = {'1': 'cold', '0': 'warm'}.get(ready[0][2].get('cold', ''), '')   # Round 226: cold and warm loads apart
        agg[(kind, name, q0.get('tier'), cold)].append((t0, boot, bsum, rms - boot - bsum, rms, eg))
        print(f"{L['start']} {kind} {name} tier={q0.get('tier')} cores={q0.get('cores')} tx={q0.get('tx', '')} net={q0.get('net', '')} fcp={q0.get('fcp', '')} gb={ready[0][2].get('gb', '')} {cold}: t0={t0} boot={boot} build={bsum} gaps={rms - boot - bsum} ready={rms} enter_gap={eg}")
        durs = sorted(((int(q.get('ms', 0)), st[5:]) for st, t, q in steps), reverse=True)
        print('    top steps: ' + ', '.join(f'{n[:28]} {d}' for d, n in durs[:8]))
        if show_all:
            for st, t, q in steps:
                extra = {k: v for k, v in q.items() if k in ('fd', 'fl', 'fn', 'fg', 'ff', 'fr', 'fa', 'rk', 'rkn', 'wd', 'wl', 'wf', 'sm', 'sp', 'sf', 'sc', 'wj', 'ld', 'lb', 'lt', 'lf', 'ts', 'tl', 'tf', 'cw', 'cl', 'cf', 'gb')}
                if extra:
                    print('    ', st[5:][:30], extra)
            print('    ready:', {k: ready[0][2].get(k) for k in ('sp', 'prg', 'fl', 'flms', 'flp', 'pu', 'pub', 'tsk', 'sfw', 'sfb', 'gb', 'gbp', 'gbw', 'gbm')})
            print('    ready, round two:', decoded(ready[0][2], READY2))
            if q0.get('pc'):
                print('    last session\'s crumb (pc):', q0.get('pc'), 'at step', q0.get('pv', ''))
            for st, t, q in enter:
                print('    enter, round two:', decoded(q, ENTER2))
            for st, t, q in perf:
                print('    ', st, {k: q.get(k) for k in ('p50', 'p95', 'calls', 'tris', 'dpr', 'fg', 'jp', 'jr', 'dc1', 'dcn', 'poc', 'pos', 'gt', 'gtn', 'pr', 'rf', 'cm', 'sdn', 'sfd', 'gb')})
                print('    ', st + ', round two:', decoded(q, RUN2))
    print('\nMEDIANS by (device, tier, cold or warm): t0, boot, build, gaps, ready, enter_gap')
    for k, v in agg.items():
        med = lambda i: statistics.median([x[i] for x in v if x[i] is not None]) if any(x[i] is not None for x in v) else None
        print(k, 'n=', len(v), [med(i) for i in range(6)])


if __name__ == '__main__':
    main()
