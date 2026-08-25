# LiDAR True-Massing Pass — Implementation Brief

**Goal:** replace every guessed building height in the Society Hill Towers 3D model with a
LiDAR-measured one — all ~250k buildings (core + wide + far ring) — and add measured roof
forms (flat / gable / hip + ridge direction) for the core, so the model's massing is *true*
instead of heuristic. This is "option 1" of the accuracy plan; option 2 (OPA parcel join
for era-correct facades) is out of scope here but noted where it hooks in.

**Read `handoff.md` at the repo root FIRST.** It documents the architecture, build loop,
delivery rules, and a long list of hard-won gotchas. This file only adds what the LiDAR
pass needs. The repo root IS the git repo (`HarkDigital/society-hill-towers`); delivery is
always: rebuild → verify → commit → push → wait for GitHub Pages → give Mike
https://harkdigital.github.io/society-hill-towers/ (never artifacts — see memory).

---

## 1. Why: the current height situation

- Core (`3d-model/scene.json`, ~2,800 buildings): heights from OSM `height`/`building:levels`
  where tagged, else defaults in `process_osm.py`. Maybe 10–15% are real.
- Wide set (`pack_wide.py` → `wide.b64`, ~108k incl. `building:part`): same story
  (`parseH`, `HDEF` defaults: house 8.0, office 10, …).
- Far ring (`pack_city.py` → `city.b64`, ~142k after merging): same defaults, then
  height-bucketed /4 for the rowhouse-strip merge.
- Known hand overrides exist and must KEEP WINNING over LiDAR: the `REALISM` map heights,
  Marriott Old City 16.5, Hopkinson House 92, the towers 94.2, plus every custom landmark.
  LiDAR should *confirm* these, not replace them.
- Precedent in-repo: `headhouse_blocks_research.json` was built from 2017 LiDAR massing
  for the Abbotts Square blocks — the approach is proven on this model at block scale.

## 2. Data sources

- **LiDAR:** PASDA (Pennsylvania Spatial Data Access, pasda.psu.edu) hosts free
  Philadelphia LiDAR — 2022 (QL1) and older 2015/2018 county flights — as LAZ tiles,
  usually EPSG:2272 (PA State Plane South, US survey feet, NAVD88). Alternative: USGS 3DEP
  via The National Map. **Check first whether the city/PASDA publishes prebuilt DSM/DTM
  rasters** — if yes, skip point-cloud processing entirely and just do raster math.
- **Footprints:** use the model's own polygons so heights key perfectly:
  - Core: `scene.json` buildings (local meters already).
  - Wide/far: the raw Overpass dumps `osm_wide_raw.json` / `osm_city_raw.json` are
    **gitignored and may be absent** — refetch with `fetch_wide.py` / `fetch_city.py`
    (resumable, checkpoints in `city_tiles/`). The packers already parse them; the height
    lookup keys on **OSM way id**, which the raw dumps carry.
- **Terrain reference:** repo `dem*.json` are 10 m USGS NED grids used at runtime for the
  ground; do NOT use them for building heights. Heights must be **AGL from the LiDAR's own
  DTM** (nDSM = DSM − DTM), which makes them datum-independent — the app's y=0 datum
  (towers' site, 8.34 m ASL) never enters the pipeline.

## 3. Coordinate frame

Local model frame: origin 39.945474 N, −75.144748 W; **x = (lon + 75.144748) · 85350**,
**z = (39.945474 − lat) · 110574** (meters; x east, z south, y up). City coverage box in
local meters: x −12000..16500, z −21700..9700 (see `pack_city.py` `CITY`). Convert LiDAR
EPSG:2272 → WGS84 with pyproj, then apply the formulas. Work in a venv
(`pip install shapely rasterio pyproj laspy` or PDAL); `pack_city.py` already expects a
shapely venv.

## 4. Pipeline (recommended shape)

1. **Tile inventory:** compute the WGS84 bbox of the CITY box, list intersecting LAZ/raster
   tiles, download (tens of GB for the county — cache outside the repo, gitignore).
2. **Build a 1 m nDSM once** (rasterio; from prebuilt DSM/DTM if available, else PDAL
   pipeline: ground-classified returns → DTM, first returns → DSM). Keep it as tiled
   GeoTIFFs; don't try to hold the county in RAM.
3. **Zonal stats per footprint:** for every building polygon (eroded ~0.5 m to avoid edge
   bleed from neighbors/trees), sample nDSM: `height = P90` of pixels (P90 beats max —
   ignores antennas/trees overhanging; beats mean — ignores courtyards). Guard: <6 pixels →
   keep the current default; clamp 2.5..550.
4. **Emit `lidar_heights.json`:** `{ "<osm way id>": h_m }` for wide/far; for the core,
   check whether `scene.json` buildings retain ids — if not, key by rounded centroid
   `"x.x,z.z"` and match in `process_osm.py` at regeneration time (or patch scene.json
   directly with a one-off script; scene.json IS committed).
5. **Roof forms (core, stretch: wide):** per footprint, on the nDSM pixels: near-zero
   height variance → flat; else fit two dominant planes (RANSAC or aspect-histogram of
   the gradient): two opposed aspects → gable (ridge azimuth = aspect ± 90°), four →
   hip. Emit `{id: {form, ridgeDeg, eave, ridge}}`. Target the ~2,800 core buildings
   first — that's where Mike walks.
6. **Integrate:**
   - `process_osm.py`: prefer lookup height over tags/defaults; write roof fields into
     scene.json entries (`roof: 'gable'|'hip'|'flat'`, `ridgeDeg`, `eaveH`).
   - `pack_wide.py` / `pack_city.py`: prefer lookup in `parseH`. Far-ring bucketing (/4)
     improves automatically.
   - `app.js` generic pass (search "historic rowhouses get pitched gable roofs"): when a
     building carries measured roof data, USE it (form + real eave/ridge) and skip the
     hash-lottery; keep all the current honesty guards (convex quad, area match,
     h < 12.5 gable cap) as fallback for unmeasured buildings. Custom/REALISM buildings:
     untouched — spec heights always win.
   - Wide-format roof flags would need a format bump — the b64 headers carry magic numbers
     (`0x53485458` wide / `0x53485459` city); if you extend the record, bump the magic and
     keep the decoder backward-compatible. Only do this if core results look great.
7. **Repack + rebuild:** `python3 pack_wide.py`, `python3 pack_city.py` (venv), then
   `python3 build.py` in `3d-model/`. Watch page size: currently 14.29 MB; the artifact
   cap is 16 MB (heights don't change size; roof flags barely).

## 5. Validation (do all of these)

- **Known truths:** towers ≈ 94 (they're hand-built anyway), City Hall ≈ 167,
  One Liberty ≈ 288, Society Hill rowhouses 9–12, Head House ≈ 8–10. The overridden
  buildings (Marriott 16.5, Hopkinson ≈ 92) — LiDAR should land near the override, not
  the old OSM lie.
- **Distributions:** before/after histogram; count of buildings on defaults → ~0; flag
  the top 50 largest |Δh| for eyeballing (they're either great fixes or pipeline bugs —
  bridges, water towers, and construction sites will show up here).
- **Visual pass:** localhost build + the headless screenshot loop (below): Society Hill
  aerials, Chestnut St streetwall, North Philly far ring, and a skyline shot — compare
  against the pre-change build.

## 6. Session mechanics (from the current thread — saves you an hour)

- Build: `cd 3d-model && python3 build.py`. Syntax check app.js first:
  `node -e "new Function(require('fs').readFileSync('app.js','utf8'))"`.
- Preview: a static server usually already runs on :8917 (another session's); just open
  `http://localhost:8917/society-hill-towers.html?dev=1` in the Browser pane. If the pane
  reports 0×0, `resize_window` to 1400×900 and dispatch a resize event.
- Headless screenshots: `?dev=1` exposes `__dbg` (`goFly(x,y,z,yaw,pitch)`, `frameOnce()`,
  `scene`, `camera`). Draw canvas `#gl` into a 2D canvas, `toDataURL('image/jpeg')`, POST
  to a tiny Python sink on 127.0.0.1:8919, Read the JPEG. Yaw 0 = north, π = south,
  positive rotates through east; pitch negative looks down.
- Deploy: commit + push, then poll Pages for a marker string **with a TAIL range request**
  (`curl -r -1500000 <pages url> | grep <marker>`) — app.js sits at the END of the 14 MB
  file; head-range polling never matches.
- Verify claims with raycasts, not eyeballs, when geometry is in question
  (`new THREE.Raycaster(origin, dir).intersectObjects(__dbg.scene.children, true)`).

## 7. Gotchas that will bite this task specifically

- **Never orient earcut output by the input ring's winding** — triangulateShape returns
  canonically-CCW triangles; caps always emit forward. (This was the far-ring hollow-
  building bug.)
- **Roof rule:** roofs must sit on the walls that were actually built — never on an OBB
  of a non-rectangular footprint. If LiDAR says "gable" but the footprint fails the
  honest-quad guards, prefer flat over floating.
- **Below-grade rule:** anything that meets the ground (walls, columns, trunks) extends
  below grade; terrain is lifted per-centroid and slopes will expose bottoms otherwise.
- **No coplanar boxes:** overlapping massing boxes must interpenetrate at *different*
  widths or clear entirely, or they shimmer.
- **Colors are legacy-linear:** the pipeline lifts stored colors ~2.2–2.5×; judge by
  rendered swatch, never by hex intuition.
- The Philly grid is ~10° off the world axes — never derive orientation from world-x.
- LiDAR epochs: buildings built/demolished since the flight will disagree with 2024+ OSM
  footprints (empty footprint → nDSM ≈ 0 → keep default; new towers missing from old
  flights → prefer the newest flight; the 2022 QL1 is safest).

## 8. Definition of done

1. Zero buildings on `HDEF`/default heights in all three sets (except <6-pixel guards).
2. Core buildings carry measured roof form + ridge; the generic gable lottery only runs
   for unmeasured/guard-failing footprints.
3. Validation table (section 5) in the commit message or a `lidar_report.json`.
4. Rebuilt page verified locally (screenshots at the four standard views), pushed, Pages
   confirmed serving, link handed to Mike, and `handoff.md` updated with a round entry
   describing the pipeline + where the lookup files live.
