"""Reduce philly3d.com's /b beacon log into per-load phases (Round 218, 220).

usage: ssh lionspool-vps "zcat -f /var/log/nginx/access.log /var/log/nginx/access.log.1 /var/log/nginx/access.log.[2-9].gz | grep '/b?'" > beacons.txt
       python3 beacons.py beacons.txt [--all] [--coldms=<n>]

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
  enter: cold, f1p (the programs the first frame added) and, on a cold load alone, f1k f1t f15 (its timers, texture calls
    and slowest: a warm load's timers come off at Ready), lit (ms from Ready to the lit button), eb (1 when the fallback
    timer drew the first frame).
  bail: cold. A bail is the first hide before Ready, not an abandonment: each is printed with whether Ready came later.
  ctxlost: d=1 is a computer's (Round 226 beacons it; before, only a phone's was sent), ar and ae after Ready and Enter.
  perf, settled, late: stl (stalls of 250 ms or more after Enter), prg, db, gbf, pl (pin landings), pt (the pins'
    captures), eh (eye-height bands), js (the JavaScript before the draw in five parts), fgl (frame gap after a landing
    frame against the rest), trm (the traffic reconcile's worst ms), an.
  part two, the cold run on demand and the link probe:
    every beacon of a load salted by ?cold=<n>: cs (the n). Such a load is a dev's cold run, never a visitor's: it is
      printed 'salted' and reduced apart, so the cold medians are the public's own.
    ready, on a cold load that ran the probe (once a device and build): pp, whole numbers joined by dots: the state (1 whole,
      2 stopped early for time, 5 a GL error on the way; and alone, 3 nothing to probe with, 4 a copy did not link, 6 it
      threw), whether KHR_parallel_shader_compile is offered, the first single program's ms (issue to linked) and its first
      draw's, the three's issue, the one synchronous call behind them and the wait, their first draws, the last single's ms
      and draw, the five second draws (what the wait alone costs), the build's own ms for the program copied, its fragment
      source in thousands of characters, and the whole probe's ms (already inside Ready); ppk, the copied program's tag.
      decode adds batched_over_serial, the three's issue + call + wait over three times the singles' mean (Stage 3, linking
      ahead, is built for an engine only where it is under 0.5), where_it_waits (issue: the link call itself blocks; call:
      the command stream stalls behind a link; wait: neither, the status query waits) and first_draw_share, the first draw's
      part of a program linked alone and drawn. Every probe is listed again after the medians.
  pc, the last session's crumb, reads q.. for the 20 s after Ready: q seconds since Ready, e since Enter, f frames, m the
    last frame gap and w the worst (ms), gb b x r the GPU MB (all, buffers, textures, renderbuffers), p programs, l lit.
The medians are printed for cold and warm loads apart. The page calls a load cold when its median program (lk's seventh
number) is over 60 ms (40 in the round's first cut, which a warm but busy Mac crossed: 37.6 to 45 ms in Chrome, 71 to 74 in
a WKWebView); --coldms=<n> cuts the line again from that median, whatever flag the page sent, so an old log or a doubtful
one can be reduced at another line. gf's last two numbers (the review): the ms the fence calls themselves took, and the
state, 0 laid throughout, 1 stopped at a slow call, 2 never laid (a touch device, or an engine that is not Chromium: WebKit's
fenceSync waits for the GPU process, 0.3 to 2.7 s a load when measured), 3 no fenceSync. Where the state is 2 read the waits
after a flush in gy instead.
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
    'gf': ('fences', 'late', 'lo_ms', 'hi_ms', 'longest_lo_ms', 'step', 'pending', 'call_ms', 'state'),
    'gbs': ('buffers_mb', 'textures_mb', 'renderbuffers_mb', 'attached_mb'),
    'gbf': ('chunks_mb', 'roads_mb', 'flats_mb', 'instanced_mb', 'rest_mb', 'unsized'),
    'on': ('objects', 'matrix_us'),
    'stl': ('stalls', 'ms', 'with_programs', 'with_programs_ms', 'longest_ms'),
    'pl': ('landings', 'ms'),
    'pt': ('captures', 'tris_k', 'calls', 'cpu_tenths_ms', 'near'),
    'eh': ('under_12m', 'to_150m', 'to_755m', 'above'),
    'js': ('land_tenths', 'sim_tenths', 'live_tenths', 'steps_tenths', 'pins_tenths', 'frames'),
    'fgl': ('after_landing_tenths', 'landing_frames', 'other_tenths', 'other_frames'),
    'pp': ('state', 'khr_offered', 'serial_ms', 'serial_draw_ms', 'batch_issue_ms', 'batch_call_ms', 'batch_wait_ms', 'batch_draw_ms', 'serial2_ms', 'serial2_draw_ms', 'redraw_ms', 'build_ms',
           'frag_kchars', 'probe_ms'),
}
# the list fields: an entry's numbers
LISTS = {'fll': ('step', 'flushes', 'ms', 'programs'), 'gi': ('step', 'yields', 'ms')}
FENCE_STATE = {0: 'laid', 1: 'stopped-at-a-slow-call', 2: 'never-laid-here', 3: 'no-fenceSync'}
PROBE_STATE = {1: 'whole', 2: 'stopped-early', 3: 'nothing-to-probe-with', 4: 'a-copy-did-not-link', 5: 'gl-error', 6: 'threw'}
CAPS = {'a': 'ASTC', 'b': 'BPTC', 's': 'S3TC', 'r': 'RGTC', 'e': 'ETC2', '1': 'ETC1', 'p': 'PVRTC', 'k': 'parallel-compile', 't': 'gpu-timer'}
READY2 = ('cold', 'cs', 'lk', 'l5', 'pp', 'ppk', 'tu', 'fll', 'gw', 'gi', 'gy', 'gf', 'hd', 'hn', 'bl', 'cap', 'db', 'gbs', 'gbf', 'on', 'an', 'wn', 'ws', 'fs', 'rs')
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
        d = dict(zip(FIELDS[key], [num(x) for x in value.split('.')]))
        if key == 'gf' and 'state' in d:
            d['state'] = FENCE_STATE.get(d['state'], d['state'])
        if key == 'pp':
            return probe(d)
        return d
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


def probe(d):
    """The link probe's numbers with what they answer (part two): batched over serial, where the wait lands and the first
    draw's share. A probe that did not run whole keeps its state's name and whatever numbers came."""
    d = dict(d)
    d['state'] = PROBE_STATE.get(d.get('state'), d.get('state'))
    ints = lambda *ks: all(isinstance(d.get(k), int) for k in ks)
    if ints('serial_ms', 'batch_issue_ms', 'batch_call_ms', 'batch_wait_ms'):
        singles = [d[k] for k in ('serial_ms', 'serial2_ms') if isinstance(d.get(k), int) and d[k] > 0]
        batch = d['batch_issue_ms'] + d['batch_call_ms'] + d['batch_wait_ms']
        if singles and batch > 0:
            one = sum(singles) / len(singles)
            d['batched_over_serial'] = round(batch / (3 * one), 2)
            d['under_half'] = d['batched_over_serial'] < 0.5
            d['where_it_waits'] = max(('issue', d['batch_issue_ms']), ('call', d['batch_call_ms']), ('wait', d['batch_wait_ms']), key=lambda e: e[1])[0]
            if ints('serial_draw_ms'):
                draws = [d[k] for k, s in (('serial_draw_ms', 'serial_ms'), ('serial2_draw_ms', 'serial2_ms')) if isinstance(d.get(k), int) and isinstance(d.get(s), int) and d[s] > 0]
                d['first_draw_share'] = round(sum(draws) / (sum(draws) + sum(singles)), 2) if draws else ''
    return d


def decoded(q, keys):
    return {k: decode(k, q.get(k)) for k in keys if q.get(k) not in (None, '')}


LINE = re.compile(r'^(\S+).*\[([^\]]+)\] "(?:GET|POST) /b\?(\S+)')


def loads_of(path):
    loads = []
    with open(path) as fh:
        for line in fh:
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


def cold_of(q, line=None):
    """'cold', 'warm' or '' for a ready beacon: the page's own flag, or with --coldms the median program (lk's seventh
    number) against that line. '' when the page timed under ten programs, or sent no round-two fields."""
    if line is None:
        return {'1': 'cold', '0': 'warm'}.get(q.get('cold', ''), '')
    lk = (q.get('lk') or '').split('.')
    if q.get('cold', '') == '' or len(lk) < 7 or not lk[6].isdigit():
        return ''
    return 'cold' if int(lk[6]) > line else 'warm'


def main():
    path = sys.argv[1]
    show_all = '--all' in sys.argv
    coldms = next((float(a.split('=', 1)[1]) for a in sys.argv[2:] if a.startswith('--coldms=')), None)
    agg = collections.defaultdict(list)
    probes = []
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
        cold = cold_of(ready[0][2], coldms)   # Round 226: cold and warm loads apart (the page's flag, or --coldms against the median)
        if ready[0][2].get('cs'):   # part two: a load salted by ?cold=<n> is a dev's cold run on demand, reduced apart from the visitors'
            cold = ('salted ' + cold).strip()
        if ready[0][2].get('pp'):
            probes.append((L['start'], kind, name, cold, ready[0][2].get('ppk', ''), decode('pp', ready[0][2]['pp'])))
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
    if probes:
        print('\nLINK PROBES (part two): batched over serial under 0.5 is an engine that links side by side')
        for start, kind, name, cold, tag, d in probes:
            if isinstance(d, dict) and 'batched_over_serial' in d:
                print(f"{start} {kind} {name} {cold}: {tag} batched/serial={d['batched_over_serial']} ({'UNDER HALF' if d['under_half'] else 'not under half'}) serial={d['serial_ms']},{d.get('serial2_ms', '')} "
                      f"batch={d['batch_issue_ms']}+{d['batch_call_ms']}+{d['batch_wait_ms']} waits_in={d['where_it_waits']} first_draw_share={d.get('first_draw_share', '')} khr={d.get('khr_offered', '')} probe_ms={d.get('probe_ms', '')} state={d['state']}")
            else:
                print(f"{start} {kind} {name} {cold}: {tag} state={d.get('state') if isinstance(d, dict) else d}")


if __name__ == '__main__':
    main()
