#!/usr/bin/env python3
"""Philly3D data pipeline runner (stdlib only).

Every stage of the model's data flow is declared once in STAGES as
(name, script, inputs, outputs, needs) plus a fetch flag and optional env, with the
inputs/outputs taken from what each script actually opens and writes and the order
from the rerun notes in handoff.md:

  fetch_wide / fetch_south / fetch_city -> process_osm (x3) -> LiDAR + facade pass
  (fetch_footprints -> lidar_join -> lidar_core, fetch_opa -> opa_join -> roof_colors
  -> patch_scenes_facade) -> pack_wide / pack_city -> the side bakes (trees, poles,
  traffic, places, street labels + SDF, overpasses, NW hills patch) -> brand -> build.

A stage is due when any output is missing or older than any input (mtime, with a
1 s tolerance for same-checkout files); --force overrides. Fetch stages (anything
that talks to Overpass / ArcGIS / Carto / OpenTopoData / PennDOT, which can take
hours and change committed data) are REFUSED unless --allow-fetch is passed.

  python3 pipeline.py --graph            print the DAG
  python3 pipeline.py --list             list stages with scripts and outputs
  python3 pipeline.py --dry-run          print the plan, run nothing
  python3 pipeline.py                    run every due stage (fetches refused)
  python3 pipeline.py --from pack_wide   pack_wide and everything downstream of it
  python3 pipeline.py --only build       just that stage
  python3 pipeline.py --force --only bake_street_sdf --python /path/to/venv/python

Inputs and outputs are relative to 3d-model/. A trailing '?' marks an optional file
(the script copes without it); a '*' makes the entry a glob. Scripts run with cwd =
3d-model/ (they open relative paths) under the interpreter given by --python
(default: this one; the shapely / numpy / Pillow stages need one that has them, see
requirements.txt).
"""
import argparse
import collections
import glob
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
MTIME_TOL = 1.0     # seconds; files from one git checkout differ by milliseconds

Stage = collections.namedtuple('Stage', 'name script inputs outputs needs fetch env note')


def S(name, script, inputs=(), outputs=(), needs=(), fetch=False, env=None, note=''):
    return Stage(name, script, tuple(inputs), tuple(outputs), tuple(needs), fetch, dict(env or {}), note)


SCENES = ('scene.json', 'scene_wide.json', 'scene_south.json')
OPA = tuple('lidar_cache/opa_%s.json' % t for t in ('core', 'wide', 'south', 'city'))
ROOF = tuple('lidar_cache/roof_%s.json' % t for t in ('core', 'wide', 'south', 'city'))

STAGES = [
    # ---- raw OSM + elevation ------------------------------------------------------
    S('fetch_wide', 'fetch_wide.py',
      outputs=['osm_wide_raw.json', 'dem_wide.json'], fetch=True,
      note='Overpass 4x4 tiles (Center City / South Philly / NoLibs / Fishtown) + OpenTopoData 50 m NED grid'),
    S('fetch_south', 'fetch_south.py',
      outputs=['osm_south_raw.json', 'dem_south.json'], fetch=True,
      note='stadium complex + Walt Whitman Bridge, 3 Overpass tiles + 50 m DEM rows'),
    S('fetch_city', 'fetch_city.py',
      outputs=['osm_city_raw.json', 'dem_city.json', 'city_tiles/*.json'], fetch=True,
      note='rest of Philadelphia: 6 boxes of Overpass tiles checkpointed in city_tiles/, 150 m DEM (skipped when present)'),
    S('process_core', 'process_osm.py',
      inputs=['osm_raw.json'], outputs=['scene.json', 'report.json'],
      note='core extract; osm_raw.json is NOT kept in the repo (refetch only if ever needed) and scene.json is since patched in place by lidar_core / patch_scenes_facade'),
    S('process_wide', 'process_osm.py',
      inputs=['osm_wide_raw.json'], outputs=['scene_wide.json', 'report_wide.json'], needs=['fetch_wide'],
      env={'SHT_RAW': 'osm_wide_raw.json', 'SHT_OUT': 'scene_wide.json', 'SHT_REPORT': 'report_wide.json'}),
    S('process_south', 'process_osm.py',
      inputs=['osm_south_raw.json'], outputs=['scene_south.json', 'report_south.json'], needs=['fetch_south'],
      env={'SHT_RAW': 'osm_south_raw.json', 'SHT_OUT': 'scene_south.json', 'SHT_REPORT': 'report_south.json'}),
    # ---- LiDAR true massing (handoff Round 13) ---------------------------------------
    S('fetch_footprints', 'fetch_footprints.py',
      outputs=['lidar_cache/phl_footprints_local.json'], fetch=True,
      note='LI_BUILDING_FOOTPRINTS (546k polygons, 2022-LiDAR max_hgt) via ArcGIS REST, resumable pages'),
    S('lidar_join', 'lidar_join.py',
      inputs=['lidar_cache/phl_footprints_local.json', 'osm_city_raw.json', *SCENES],
      outputs=['lidar_city_heights.json', 'lidar_cache/core_join.json', 'lidar_report.json', 'scene_wide.json', 'scene_south.json'],
      needs=['fetch_footprints', 'fetch_city', 'process_core', 'process_wide', 'process_south'],
      note='shapely; patches scene_wide/scene_south heights in place; --skip-city reuses the committed LUT'),
    S('lidar_core', 'lidar_core.py',
      inputs=['scene.json', 'lidar_cache/core_join.json?', 'lidar_cache/laz/*.copc.laz?'],
      outputs=['lidar_cache/core_grids.npz', 'lidar_report.json', 'scene.json'], needs=['lidar_join'], fetch=True,
      note='numpy / laspy[lazrs] / pyproj / shapely; downloads the 9 NOAA COPC tiles when lidar_cache/laz/ is empty; patches scene.json roof forms in place'),
    # ---- Tier-1 facade pass (handoff Round 15) ---------------------------------------
    S('fetch_opa', 'fetch_opa.py',
      outputs=['lidar_cache/opa_rows.csv'], fetch=True,
      note='OPA properties table (583k rows) from phl.carto.com, paginated + resumable'),
    S('opa_join', 'opa_join.py',
      inputs=['lidar_cache/opa_rows.csv', 'osm_city_raw.json', *SCENES],
      outputs=[*OPA, 'lidar_report.json'], needs=['fetch_opa', 'fetch_city', 'lidar_core'],
      note='shapely'),
    S('roof_colors', 'roof_colors.py',
      inputs=['osm_city_raw.json', *SCENES],
      outputs=['lidar_cache/roof_palette.json', *ROOF], needs=['opa_join'], fetch=True,
      note='numpy / Pillow / shapely; downloads 2024 3-inch ortho tiles into lidar_cache/tiles/ as needed'),
    S('patch_scenes_facade', 'patch_scenes_facade.py',
      inputs=['lidar_cache/roof_palette.json', *OPA, *ROOF, *SCENES],
      outputs=['facade_palette.json', 'lidar_report.json', *SCENES], needs=['opa_join', 'roof_colors'],
      note='writes fa / rp into the three scene jsons in place (idempotent)'),
    # ---- packed tiers --------------------------------------------------------------
    S('pack_wide', 'pack_wide.py',
      inputs=['scene_wide.json', 'scene_south.json?', 'parts_wide.json?', 'wide_landmarks_research.json?'],
      outputs=['wide.b64'], needs=['process_wide', 'process_south', 'lidar_join', 'patch_scenes_facade'],
      note='parts_wide.json (building:part pieces) is hand-maintained'),
    S('pack_city', 'pack_city.py',
      inputs=['osm_city_raw.json', 'lidar_city_heights.json?', 'lidar_cache/opa_city.json?', 'lidar_cache/roof_city.json?'],
      outputs=['city.b64'], needs=['fetch_city', 'lidar_join', 'opa_join', 'roof_colors'],
      note='shapely (rowhouse rows merged into block strips)'),
    S('fetch_outskirts', 'fetch_outskirts.py',
      outputs=['osm_outskirts_raw.json', 'outskirts_tiles/*.json'], fetch=True,
      note='the towns across the city line: 3 strips of Overpass tiles checkpointed in outskirts_tiles/ (no DEM, dem_city covers them)'),
    S('fetch_landuse', 'fetch_landuse.py',
      outputs=['osm_landuse_raw.json', 'landuse_tiles/*.json'], fetch=True,
      note='residential / commercial / industrial / retail land use over the far-ring box, 16 tiles, for the filler'),
    S('pack_outskirts', 'pack_outskirts.py',
      inputs=['osm_outskirts_raw.json', 'osm_landuse_raw.json?', 'city_limit.json?', 'city.b64?', 'wide.b64?'], outputs=['outskirts.b64'],
      needs=['fetch_outskirts', 'fetch_landuse', 'fetch_boundary', 'pack_city', 'pack_wide'],
      note='shapely; 1.0 m units, rows fused with a 3 m bridge, no LiDAR / OPA / roof join; plus the land-use filler beyond the city line'),
    S('fetch_boundary', 'fetch_boundary.py',
      outputs=['city_limit.json'], fetch=True,
      note='the city line (OSM relation 188022) and the 2 km flight limit; the raw relation is cached in lidar_cache/'),
    # ---- side bakes ---------------------------------------------------------------
    S('fetch_trees', 'fetch_trees.py',
      outputs=['lidar_cache/phl_trees_raw.json'], fetch=True, note='PPR Tree Inventory 2025, wide envelope, ArcGIS pages'),
    S('pack_trees', 'pack_trees.py',
      inputs=['lidar_cache/phl_trees_raw.json', 'lidar_cache/phl_footprints_local.json?'],
      outputs=['trees.b64', 'tree_names.json'], needs=['fetch_trees', 'fetch_footprints']),
    S('fetch_poles', 'fetch_poles.py',
      outputs=['lidar_cache/phl_poles_raw.json'], fetch=True, note='Streets Department Street_Poles (203k), ArcGIS pages'),
    S('pack_poles', 'pack_poles.py',
      inputs=['lidar_cache/phl_poles_raw.json'], outputs=['poles.b64'], needs=['fetch_poles']),
    S('fetch_traffic', 'fetch_traffic.py',
      outputs=['lidar_cache/traffic_raw/rmstraffic.geojson'], fetch=True, note='PennDOT RMSTRAFFIC AADT for the wide envelope'),
    S('bake_traffic', 'bake_traffic.py',
      inputs=['osm_wide_raw.json', 'osm_south_raw.json', 'lidar_cache/traffic_raw/rmstraffic.geojson'],
      outputs=['traffic.b64'], needs=['fetch_wide', 'fetch_south', 'fetch_traffic']),
    S('fetch_places', 'fetch_places.py',
      outputs=['lidar_cache/places_raw/historic_districts.geojson', 'lidar_cache/places_raw/neighborhoods.geojson'], fetch=True,
      note='historic districts (Carto) + neighborhoods (OpenDataPhilly); cached until deleted'),
    S('bake_places', 'bake_places.py',
      inputs=['lidar_cache/places_raw/historic_districts.geojson', 'lidar_cache/places_raw/neighborhoods.geojson'],
      outputs=['places.json'], needs=['fetch_places']),
    S('fetch_dem_nw', 'fetch_dem_nw.py',
      inputs=['dem_city.json'], outputs=['dem_nw.json'], needs=['fetch_city'], fetch=True,
      note='50 m NED over the NW hills, checkpointed in lidar_cache/dem_nw_elev.json, border feathered to dem_city'),
    S('fetch_nw_parks', 'fetch_nw_parks.py', outputs=['nw_parks.json'], fetch=True, note='PPR_Properties inside the NW patch (ArcGIS)'),
    S('fetch_nw_water', 'fetch_nw_water.py', outputs=['nw_water.json'], fetch=True, note='full-fidelity water rings inside the NW patch (Overpass)'),
    S('bake_overpasses', 'bake_overpasses.py',
      inputs=['osm_wide_raw.json', 'osm_south_raw.json', 'city_tiles/*.json?', 'scene.json',
              'dem.json?', 'dem_wide.json?', 'dem_south.json?', 'dem_nw.json?', 'dem_city.json?'],
      outputs=['overpasses.json'], needs=['fetch_wide', 'fetch_south', 'fetch_city', 'process_core', 'fetch_dem_nw'],
      note='~1 min plain py3; rebake whenever a raw dump or DEM changes'),
    S('bake_street_labels', 'bake_street_labels.py',
      inputs=['scene.json', 'scene_wide.json?', 'scene_south.json?', 'overpasses.json?'],
      outputs=['street_labels.json'], needs=['process_core', 'process_wide', 'process_south', 'bake_overpasses'],
      note='rerun after any scene refetch or overpass rebake'),
    S('bake_street_sdf', 'bake_street_sdf.py',
      inputs=['street_labels.json', 'MontserratItalic.ttf'], outputs=['street_sdf.json'], needs=['bake_street_labels'],
      note='numpy / Pillow'),
    # ---- brand + page -----------------------------------------------------------------
    S('make_brand', 'brand/make_brand.py',
      inputs=['brand/favicon.svg', 'brand/mark.svg', 'brand/Montserrat-SemiBold.ttf', 'brand/og_raw.png?'],
      outputs=['brand/dist/favicon.svg', 'brand/dist/favicon-16.png', 'brand/dist/favicon-32.png', 'brand/dist/favicon-48.png',
               'brand/dist/favicon.ico', 'brand/dist/apple-touch-icon.png', 'brand/dist/lockup.png', 'brand/dist/og.png?'],
      note='Pillow + macOS sips'),
    S('build', 'build.py',
      inputs=['template.html', 'style.css', 'three.min.js', 'app.js', 'scene.json', 'meta.json?', 'about_body.html?',
              'dem.json?', 'dem_wide.json?', 'wide.b64?', 'dem_south.json?', 'wwb.json?', 'wide_names.json?', 'dem_city.json?',
              'city.b64?', 'facade_palette.json?', 'street_labels.json?', 'trees.b64?', 'tree_names.json?', 'places.json?',
              'street_sdf.json?', 'overpasses.json?', 'traffic.b64?', 'dem_nw.json?', 'nw_parks.json?', 'nw_water.json?',
              'poles.b64?', 'outskirts.b64?', 'city_limit.json?', 'brand/dist/favicon.svg', 'brand/dist/favicon-32.png', 'brand/dist/apple-touch-icon.png'],
      outputs=['society-hill-towers.html'],
      needs=['process_core', 'pack_wide', 'pack_city', 'pack_outskirts', 'fetch_boundary', 'patch_scenes_facade', 'bake_street_labels', 'bake_street_sdf',
             'pack_trees', 'bake_places', 'bake_overpasses', 'bake_traffic', 'fetch_dem_nw', 'fetch_nw_parks',
             'fetch_nw_water', 'pack_poles', 'make_brand', 'fetch_wide', 'fetch_south', 'fetch_city'],
      note='assembles the single-file page'),
]

BY_NAME = collections.OrderedDict((s.name, s) for s in STAGES)


# ------------------------------------------------------------------------- DAG utils
def validate():
    """Unknown needs, cycles, and inputs whose producer is not an (indirect) need."""
    problems = []
    for s in STAGES:
        for n in s.needs:
            if n not in BY_NAME:
                problems.append('%s needs unknown stage %r' % (s.name, n))
    producers = collections.defaultdict(set)
    for s in STAGES:
        for o in s.outputs:
            producers[o.rstrip('?')].add(s.name)
    anc = ancestors()
    for s in STAGES:
        for i in s.inputs:
            key = i.rstrip('?')
            prod = producers.get(key, set()) - {s.name}
            if prod and not (prod & anc[s.name]):
                problems.append('%s reads %s (made by %s) without needing it' % (s.name, key, ', '.join(sorted(prod))))
    return problems


def ancestors():
    out = {}

    def walk(name, seen):
        if name in out:
            return out[name]
        if name in seen:
            raise SystemExit('cycle through stage %r' % name)
        seen.add(name)
        acc = set()
        for n in BY_NAME[name].needs:
            if n in BY_NAME:
                acc.add(n)
                acc |= walk(n, seen)
        out[name] = acc
        return acc
    for s in STAGES:
        walk(s.name, set())
    return out


def dependents():
    out = collections.defaultdict(set)
    for s in STAGES:
        for n in s.needs:
            out[n].add(s.name)
    return out


def topo_order():
    """Kahn's algorithm, declared order as the tie-break."""
    indeg = {s.name: len([n for n in s.needs if n in BY_NAME]) for s in STAGES}
    deps = dependents()
    ready = [s.name for s in STAGES if indeg[s.name] == 0]
    order = []
    while ready:
        name = ready.pop(0)
        order.append(name)
        for d in sorted(deps[name], key=lambda n: list(BY_NAME).index(n)):
            indeg[d] -= 1
            if indeg[d] == 0:
                ready.append(d)
        ready.sort(key=lambda n: list(BY_NAME).index(n))
    if len(order) != len(STAGES):
        raise SystemExit('cycle in STAGES: %s never became ready' % sorted(set(BY_NAME) - set(order)))
    return order


def closure_downstream(name):
    deps = dependents()
    out = {name}
    todo = [name]
    while todo:
        n = todo.pop()
        for d in deps[n]:
            if d not in out:
                out.add(d)
                todo.append(d)
    return out


# ---------------------------------------------------------------------- file checks
def resolve(spec):
    """spec -> (optional, [existing absolute paths]). Globs expand; plain names map to one path or none."""
    optional = spec.endswith('?')
    pat = spec[:-1] if optional else spec
    if '*' in pat:
        paths = [pathlib.Path(p) for p in sorted(glob.glob(str(HERE / pat)))]
    else:
        p = HERE / pat
        paths = [p] if p.exists() else []
    return optional, pat, paths


def rel(p):
    try:
        return str(pathlib.Path(p).relative_to(HERE))
    except ValueError:
        return str(p)


def evaluate(stage, force):
    """-> (status, reason) with status in RUN / UP-TO-DATE / BLOCKED (fetch handled by caller)."""
    missing_in = []
    newest_in = None
    for spec in stage.inputs:
        optional, pat, paths = resolve(spec)
        if not paths:
            if not optional:
                missing_in.append(pat)
            continue
        for p in paths:
            m = p.stat().st_mtime
            if newest_in is None or m > newest_in[0]:
                newest_in = (m, rel(p))
    if missing_in:
        return 'BLOCKED', 'missing input%s: %s' % ('s' if len(missing_in) > 1 else '', ', '.join(missing_in))
    missing_out = []
    oldest_out = None
    for spec in stage.outputs:
        optional, pat, paths = resolve(spec)
        if not paths:
            if not optional:
                missing_out.append(pat)
            continue
        for p in paths:
            m = p.stat().st_mtime
            if oldest_out is None or m < oldest_out[0]:
                oldest_out = (m, rel(p))
    if force:
        return 'RUN', '--force'
    if missing_out:
        return 'RUN', 'missing output%s: %s' % ('s' if len(missing_out) > 1 else '', ', '.join(missing_out))
    if newest_in and oldest_out and newest_in[0] > oldest_out[0] + MTIME_TOL:
        return 'RUN', '%s is newer than %s' % (newest_in[1], oldest_out[1])
    return 'UP-TO-DATE', 'outputs newer than every input' if newest_in else 'outputs present (no inputs)'


def plan(selected, force, allow_fetch):
    """[(stage, status, reason)] in topological order; RUN cascades to selected dependents
    that read a running stage's outputs."""
    rows = []
    will_run = set()
    producers = collections.defaultdict(set)
    for s in STAGES:
        for o in s.outputs:
            producers[o.rstrip('?')].add(s.name)
    for name in topo_order():
        s = BY_NAME[name]
        if name not in selected:
            rows.append((s, 'SKIP', 'not selected'))
            continue
        status, reason = evaluate(s, force)
        if status != 'BLOCKED':
            upstream = sorted(p for i in s.inputs for p in producers.get(i.rstrip('?'), ()) if p in will_run and p != name)
            if upstream and status != 'RUN':
                status, reason = 'RUN', 'upstream %s reruns' % ', '.join(upstream)
            elif upstream and status == 'RUN':
                reason += '; upstream %s reruns' % ', '.join(upstream)
        if status == 'RUN' and s.fetch and not allow_fetch:
            status, reason = 'REFUSED', 'fetch stage (pass --allow-fetch); ' + reason
        if status == 'RUN':
            will_run.add(name)
        rows.append((s, status, reason))
    return rows


# ------------------------------------------------------------------------- printing
def print_graph():
    order = topo_order()
    width = max(len(n) for n in order)
    print('Philly3D pipeline DAG (%d stages, topological order; "<-" = the stages a stage needs)' % len(order))
    for name in order:
        s = BY_NAME[name]
        needs = ', '.join(s.needs) if s.needs else '(source)'
        flag = '  [fetch]' if s.fetch else ''
        print('  %-*s <- %s%s' % (width, name, needs, flag))
    sinks = [n for n in order if not dependents()[n]]
    print('roots: %s' % ', '.join(n for n in order if not BY_NAME[n].needs))
    print('sinks: %s' % ', '.join(sinks))
    for p in validate():
        print('WARNING: ' + p, file=sys.stderr)


def print_list():
    width = max(len(s.name) for s in STAGES)
    for name in topo_order():
        s = BY_NAME[name]
        print('%-*s  %-24s %s' % (width, name, s.script, '[fetch]' if s.fetch else ''))
        if s.inputs:
            print('%*s    in : %s' % (width, '', ', '.join(s.inputs)))
        print('%*s    out: %s' % (width, '', ', '.join(s.outputs)))
        if s.env:
            print('%*s    env: %s' % (width, '', ' '.join('%s=%s' % kv for kv in s.env.items())))
        if s.note:
            print('%*s    %s' % (width, '', s.note))


def print_plan(rows, args, python):
    print('Plan  (3d-model = %s)' % HERE)
    print('      python = %s   force = %s   allow-fetch = %s   dry-run = %s'
          % (python, 'yes' if args.force else 'no', 'yes' if args.allow_fetch else 'no', 'yes' if args.dry_run else 'no'))
    width = max(len(s.name) for s, _, _ in rows)
    counts = collections.Counter()
    for i, (s, status, reason) in enumerate(rows, 1):
        counts[status] += 1
        if status == 'SKIP' and not args.verbose:
            continue
        print('  %2d  %-*s  %-10s  %s' % (i, width, s.name, status, reason))
    print('Summary: %d to run, %d up to date, %d blocked, %d refused, %d not selected'
          % (counts['RUN'], counts['UP-TO-DATE'], counts['BLOCKED'], counts['REFUSED'], counts['SKIP']))
    if counts['REFUSED']:
        print('         refused fetch stages need --allow-fetch (they take hours and rewrite committed data)')


# --------------------------------------------------------------------------- running
def run_stage(stage, python):
    script = HERE / stage.script
    if not script.exists():
        print('  FAILED: script %s does not exist' % stage.script)
        return False
    env = dict(os.environ)
    env.update(stage.env)
    cmd = [python, str(script)]
    print('\n=== %s: %s%s' % (stage.name, ' '.join(cmd[1:]), (' (env %s)' % ' '.join('%s=%s' % kv for kv in stage.env.items())) if stage.env else ''))
    sys.stdout.flush()
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(HERE), env=env)
    dt = time.time() - t0
    if r.returncode != 0:
        print('  FAILED (exit %d after %.0f s)' % (r.returncode, dt))
        return False
    missing = [pat for spec in stage.outputs for (opt, pat, paths) in [resolve(spec)] if not paths and not opt]
    if missing:
        print('  FAILED: finished in %.0f s but did not write %s' % (dt, ', '.join(missing)))
        return False
    print('  ok (%.0f s)' % dt)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog='\n'.join(__doc__.split('\n\n')[1:]))
    ap.add_argument('--graph', action='store_true', help='print the DAG and exit')
    ap.add_argument('--list', action='store_true', help='list stages with scripts, inputs, outputs and exit')
    ap.add_argument('--from', dest='from_stage', metavar='STAGE', help='run STAGE and everything downstream of it')
    ap.add_argument('--only', metavar='STAGE', help='run just STAGE')
    ap.add_argument('--dry-run', action='store_true', help='print the plan without running anything')
    ap.add_argument('--force', action='store_true', help='run selected stages regardless of file times')
    ap.add_argument('--allow-fetch', action='store_true', help='permit fetch stages (network downloads)')
    ap.add_argument('--python', default=sys.executable, help='interpreter for the stage scripts (default: this one)')
    ap.add_argument('--verbose', '-v', action='store_true', help='also list not-selected stages in the plan')
    args = ap.parse_args(argv)

    if args.graph:
        print_graph()
        return 0
    if args.list:
        print_list()
        return 0
    for name in (args.from_stage, args.only):
        if name is not None and name not in BY_NAME:
            print('unknown stage %r; stages: %s' % (name, ', '.join(BY_NAME)), file=sys.stderr)
            return 2
    if args.from_stage and args.only:
        print('--from and --only are mutually exclusive', file=sys.stderr)
        return 2
    if args.only:
        selected = {args.only}
    elif args.from_stage:
        selected = closure_downstream(args.from_stage)
    else:
        selected = set(BY_NAME)
    for p in validate():
        print('WARNING: ' + p, file=sys.stderr)

    rows = plan(selected, args.force, args.allow_fetch)
    print_plan(rows, args, args.python)
    to_run = [s for s, status, _ in rows if status == 'RUN']
    if args.dry_run or not to_run:
        if not to_run and not args.dry_run:
            print('Nothing to do.')
        return 0

    done = 0
    for s in to_run:
        # re-evaluate right before running: an upstream stage may just have refreshed our inputs
        status, reason = evaluate(s, args.force)
        if status == 'BLOCKED':
            print('\n=== %s: BLOCKED (%s) — stopping' % (s.name, reason))
            return 1
        if status == 'UP-TO-DATE' and not args.force:
            print('\n=== %s: up to date after upstream ran (%s), skipping' % (s.name, reason))
            continue
        if not run_stage(s, args.python):
            print('\nStopped at %s after %d stage%s.' % (s.name, done, '' if done == 1 else 's'))
            return 1
        done += 1
    print('\nDone: %d stage%s ran.' % (done, '' if done == 1 else 's'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
