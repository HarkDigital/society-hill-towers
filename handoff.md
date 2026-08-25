# Society Hill Towers 3D Model — Handoff

Interactive 3D model of Society Hill Towers (I.M. Pei, 1964), ~2,800 detailed Society Hill
buildings, and ~108,000 simplified buildings across Center City, South Philadelphia, Northern
Liberties and Fishtown/Kensington, published as a Claude artifact. Built Aug 14–15, 2026.

**Live artifact:** https://claude.ai/code/artifact/04f16de9-5902-4bd0-abf1-09e71f816b50

**GitHub / Pages (added Aug 24):** repo `HarkDigital/society-hill-towers`
(https://github.com/HarkDigital/society-hill-towers), served at
https://harkdigital.github.io/society-hill-towers/ (root `index.html` redirects into
`3d-model/society-hill-towers.html`). The two raw Overpass dumps (`osm_wide_raw.json`,
`osm_south_raw.json`) are gitignored — everything else, including the built page, is
committed. To update the site: rebuild, commit, `git push`. Note: unlike the artifact,
GH Pages has no CSP, so a Pages-only feature could fetch external data (e.g. live weather).

> ⚠️ **Keeping the same URL from a new machine/conversation:** the artifact is keyed to
> the publishing conversation + file path. From a *different* conversation, republish by
> passing the URL above as the `url` parameter of the Artifact tool (or tell Claude
> "update my existing artifact at <URL>"). Publishing without it creates a second,
> separate artifact.

## What's in `3d-model/`

| File | Role |
|---|---|
| `society-hill-towers.html` | The built, self-contained page (~1.3 MB). This is what gets published. |
| `template.html` | Page shell with `{{CSS}} {{DATA}} {{THREE}} {{APP}} {{ABOUT_BODY}}` placeholders |
| `app.js` | All application code (~1,800 lines). Everything interesting is here. |
| `style.css` | HUD chrome (title block, control bar, labels, About panel) |
| `about_body.html` | Prose + spec table injected into the About panel |
| `build.py` | Assembles the final HTML. Run `python3 build.py` in this folder. |
| `scene.json` | Processed OSM data: buildings/roads/areas/trees in local meters |
| `process_osm.py` | Raw Overpass JSON → `scene.json` (needs `osm_raw.json`, not kept here — refetch if ever needed) |
| `meta.json` | Tower-facade research + landmark heights/spires (baked in at build) |
| `realism_research.json` | Landmark-appearance research (colors, dimensions, roof forms, sources) |
| `headhouse_blocks_research.json` | Abbotts Square / 410 S Front / New Market blocks — OPA parcels + LiDAR massing with local coords |
| `fenestration_research.json` | Facade vocabulary (sash sizes, bay pitches, church tiers, storefronts) behind the shader styles |
| `geo_audit.json` | 35 geography gaps with lat/lon, fixes, priorities — the to-do list for further realism |
| `dem.json` / `dem_wide.json` | USGS NED 10 m elevation grids (25 m cells core, 50 m wide), meters above sea level |
| `fetch_wide.py` → `osm_wide_raw.json` (95 MB, not needed after packing) | Tiled Overpass fetch for the wide area + wide DEM |
| `scene_wide.json` (21 MB) → `pack_wide.py` → `wide.b64` (5 MB) | Outer districts packed as int16 at 0.2 m; `parts_wide.json` = OSM `building:part` skyscraper pieces |
| `wide_names.json`, `wide_landmarks_research.json` | Outer landmark names for labels; Center City / North / South research |
| `fetch_south.py` → `osm_south_raw.json`, `scene_south.json`, `dem_south.json`, `wwb.json` | South extension: stadium complex + Walt Whitman Bridge (merged by `pack_wide.py`) |
| `three.min.js` | Three.js r149 UMD (inlined at build — CSP forbids CDNs in artifacts) |

## Build & preview

```bash
cd 3d-model && python3 build.py
python3 -m http.server 8917   # then open http://localhost:8917/society-hill-towers.html
```

- Append **`?dev=1`** to expose `window.__dbg = { orbit, walk, camera, renderer, goWalk(x,z,yaw) }`
  for scripted camera placement while debugging. Without the flag nothing is exposed.
- No build tools/npm needed; plain Python 3 + a browser.

## Architecture (app.js)

- **Coordinates:** x = east, z = south, y = up, meters. Origin = centroid of the three
  towers (39.94547°N, 75.14475°W). `scene.json` and all hardcoded positions use this frame.
- **Load pipeline:** `buildSteps[]` run sequentially by `build()` (each step try/caught;
  veil's Enter button enables at the end). Steps: ground/water/pools → streets+sidewalks →
  parks/piers → generic buildings → steeples → landmark restorations → the three towers →
  trees → labels → viewpoints.
- **Generic fabric:** every OSM footprint extruded and merged into one mesh (vertex colors,
  one draw call). Small residential quads get OBB-fitted **gable roofs + chimneys**
  (`orientedBox`/`gableGeom`). A `onBeforeCompile` shader on `cityMat` draws windows,
  lintels, shutters, and doors procedurally in world space on wall faces.
- **The towers:** fully procedural in the `TOWER` config + "Casting the concrete grid" step.
  Facade spec is research-backed: 18×12 bays on a 6 ft module, 0.42 m mullions, deep-set
  1.4×2.2 m windows, colonnade every 3rd grid line, 94.2 m / 31 stories (OSM tags say 89 —
  CTBUH says 309 ft; we use 94.2).
- **Landmarks:** the `REALISM` map (exact OSM names) marks buildings `custom` (skipped by
  the generic pass, rebuilt in "Restoring the landmarks" with researched forms) or
  `recolor` (generic geometry, corrected color/height). Notables: The Ryland (two offset
  glass bars + white grid), Head House + open Shambles arcade, Merchants' Exchange curved
  colonnade + lantern, St. Peter's white spire (west tower), Old Pine's yellow temple
  (colonnade faces north), Mother Bethel (spired tower at NW corner).
- **Navigation:** custom orbit (damped, grab-style pan) + walk mode (pointer lock with
  drag-look fallback for sandboxed iframes, collision vs building edges via a spatial
  hash, touch joystick) + **fly mode** (Aug 24: key 3 / Fly button; free 3D WASD flight
  sharing walk's look state, E/Q or Space/C for up/down, shift boost ×3.2, scroll wheel
  sets cruise speed 10–500 m/s, clamped above terrain via `siteY`, no collision; takes
  off from the current camera pose). Landmark labels are HTML divs projected per frame.
- **Layering (z-fighting):** flat surfaces use the `LAYER` constants (park .06 / plaza .10 /
  sidewalk .16 / road .24 / footway .32 / pools .38) **and** the renderer runs with
  `logarithmicDepthBuffer: true`. Don't add coplanar flat geometry without picking a layer.
- **Terrain (added Aug 15):** the city is a plateau at y=0; east of Front St the I-95 trench
  drops to -8 between `TERRAIN.trenchW/E` (offsets from the **Front St line fit `fl`** — the
  grid is ~10° off the axes, so never use world x for this), the Penn's Landing shelf sits at
  -6.5…-7.5, water at -10. The shoreline is the `SHORE` polyline `x(z)` (Penn's Landing bulge,
  marina basin notch, pull-back south of the ships). `siteY(x,z,'ground'|'road')` is the one
  function everything uses to sit on the terrain (roads bridge the trench, tunnel under the
  park cap; `walkY` for the walker). Cap decks (Foglietta, Vietnam memorial) and the Park at
  Penn's Landing are in `CAPS`. Ships (`t:'ship'`) get hulls/masts in "Mooring the ships" with
  water slips carved around them.
- **Facade styles:** every merged part carries an `aStyle` attribute read by the `cityMat`
  shader: 0 Georgian rowhouse (1.9 m bays, 6/6 sash, door every 3rd bay with fanlight),
  1 church (two tiers, arched above), 2 modern slab, 3 blank, 4 civic arched base (Head House),
  5 storefront, 6 modern over double-height retail (Abbotts Square). Dimensions come from
  `fenestration_research.json`.
- **Solar clock:** `solar()` is NOAA's algorithm for the site; `clock` holds Philadelphia local
  time (US DST rules in `tzOffsetMin`); `applyLighting()` runs every frame and drives sun
  direction/intensity/color, sky palette (`PAL` night/twilight/day), fog, hemisphere, exposure,
  `nightUniform` (lit windows in the facade shader via `shtLit` → emissive) and the tower
  glass emissives. The T panel (`#timepanel`) has a date input, slider, presets, and live mode.
- **Elevation:** `demAbs()` samples the core 25 m grid, falling back to the wide 50 m grid; the
  datum is the towers' site (8.34 m ASL) so the towers stay at y=0. `cityY` guards the strip
  along Front St against DEM samples that fell into the I-95 trench. Every builder lifts its
  geometry with `siteY()`; building walls extend 1.5 m below grade so slopes never show gaps.
- **Facade-local coordinates:** `buildingGeom()` builds walls edge by edge with `aWallU/L/H`
  attributes so the shader centers bays on each facade (no corner-cut windows) and drops rows
  above the eave; the shader masks are anti-aliased with `fwidth` and fade at distance.
- **Outer districts:** "Raising the outer districts" decodes `WIDE_B64` (header magic
  0x53485458: n, h*5, minH*5, type, int16 coords), builds lean indexed chunks (700 m, 8-bit
  normals/colors) sharing `cityMat`, outer roads, parks/water, the Ben Franklin Bridge, and
  tall-building labels. Skipped on touch devices. ~2 M triangles / ~90 draw calls in wide views.
- **Location-matched landmarks:** unnamed OSM footprints (Abbotts Square, 410 at Society Hill,
  New Market Complex) are matched by centroid + area in `REALISM_NEAR` and built via `getKey()`.
  Massing/heights come from `headhouse_blocks_research.json` (Philadelphia OPA + 2017 LiDAR).
  `geo_audit.json` lists the remaining geography gaps with priorities (Washington Square
  layout, Independence Square fences, Chart House, RiverRink, Ben Franklin Bridge…).

## Hard-won gotchas (do not relearn these)

1. **OBB frame handedness:** for any frame built from a 2D axis `(ax,az)` in this y-up
   world, the perpendicular must be `(az,-ax)`. Using `(-az,ax)` makes winding depend on
   the source polygon's direction → half your roofs get backface-culled (invisible).
2. **Artifact sandbox:** no external requests (inline everything), pointer lock may be
   denied → the drag-look fallback must stay functional; `target=_blank` links may be dead.
3. **build.py guards:** it aborts if any embedded blob contains `</script`. Keep it that way.
4. **OSM data quirks already corrected in code:** Marriott Old City tagged `height=4`
   (real ~16.5, overridden); Hopkinson House tagged 107 m (two sources say ~92, overridden);
   Independence Place twins kept at OSM's 96.9 m (agents disagreed: 25 vs 36 floors); the
   Custom House, Hilton, Independence Hall, Old City Hall (tagged 3.2 m!) and the museum ships
   all carried OSM's 13 m default and are rebuilt in code; swimming pools needed a separate Overpass query
   (`leisure=swimming_pool`) — the towers' pool + Delancey pool are hardcoded in the
   ground step with real OSM geometry.
5. **Name matching:** `REALISM` uses exact `b.name` equality ('Head House' vs
   'Head House Market' are different buildings — the latter is the open Shambles shed,
   `open: true` keeps it walkable and tree-free but uncollidable).
6. **Flicker = duplicates.** OSM returns whole ways, so the core extract contains streets/parks/
   buildings that extend beyond its bbox; the wide set must drop anything *touching* the core
   (`touchesCore` in pack_wide.py, any-vertex rule, not centroid) and the app clips core street
   ribbons at the core boundary (`runsOf`). Skyscraper `building:part` pieces sit exactly on
   their outlines → outlines containing a part centroid are dropped. Flat polygons over terrain
   must be draped with interior vertices (`drapedPoly`, Delaunay) and ribbons densified
   (`densify`, 10 m) or they cut through the hills. Do NOT use polygonOffset on the layered
   flats — at grazing angles its slope term overpowers the real 8–16 cm gaps and surfaces
   visibly swap (that was the Aug 23 road flicker). Instead every ribbon gets a deterministic
   few-cm lift (hash of its first point) so nothing is ever exactly coplanar.
7. **Roofs must be built on the footprint, not the OBB.** `quadGable()` fits the gable to the
   (simplified, 4-vertex) footprint quad itself — eaves and gable ends meet the walls at every
   vertex. OBB roofs float beside skewed footprints (the grid is rotated ~10°).
8. **Glass:** `refreshEnv()` re-bakes the PMREM environment (sky + sun ball + dark silhouettes)
   whenever the sun moves >3°; glass towers flagged from research render as type 10 with a
   reflective material; style 7 is the balcony-band slab (Dockside, Hopkinson).
9. **rAF is throttled** in headless/hidden tabs — don't trust FPS probes there; use
   `renderer.info` (currently ~20 calls / ~330k tris).

## State & backlog

Done and verified: everything above, on desktop + mobile viewports, zero console errors.
Reviewed by a 25-agent adversarial pass (pan-basis math bug, trees-in-buildings, and debug
leakage were found and fixed).

Built in the Aug 15 fidelity pass: terrain/trench/shoreline/basin, museum ships, Custom House
(85 m), Hilton (70 m), Independence Hall steeple, Congress Hall / Old City Hall / Carpenters'
cupolas, Second & First Bank porticos, the towers' 1 m podium plaza with berms, Abbotts Square
and its neighbors, flush gable ends + box cornices, the styled facade shader.

Built Aug 23: solar clock + time panel; DEM terrain; facade-local windows + AA; Abbotts' square
north end; pool clear of berms; the wide expansion (Center City, South Philly, NoLibs,
Fishtown/Kensington) with `building:part` skyscrapers, generic church steeples, outer labels, and
the Ben Franklin Bridge on OSM/DRPA geometry.

Realism pass (Aug 24, from the owner's 18th-floor south-tower photos + a 4-agent research
sweep with photo-sampled colors):
- **Sky:** day palette now a real clear-noon blue (zenith `#4279c4`, horizon `#c8dcea`,
  photographic sRGB values for 40°N summer); water material roughened (0.42) with envMap
  intensity 0.55 so the river reads blue-gray instead of mirroring the bright sky. Note:
  the pale washed noon look at grazing angles predates this change (verified against a
  baseline build) — it is the noon sun + fog, not a regression.
- **Ben Franklin Bridge** rebuilt: "Ben Franklin blue" steel `#8fb4c6` / cables `#7c9bac`
  (Pantone 550C territory, pixel-sampled), lattice towers with 3 portal struts + 2 X-brace
  panels above deck and one X below (matches DRPA photos), thin roadway on an 8.5 m open
  stiffening truss (chords/diagonals/verticals), warm-granite tower piers `#b78771`, and
  50 m stepped granite anchorage towers `#b0a99e` (61×50 m) the roadway threads through.
- **Walt Whitman Bridge:** repainted the researched sage green (steel `#75a889`, cables
  `#6b9478` — DRPA "federal standard green", photo-sampled); towers corrected to the real
  Ammann form: clean legs with ONE deep top portal + ONE below-deck strut, no mid-height
  bracing.
- **Dockside** rebuilt as its real stepped ziggurat (BLT Architects, 16 stories, ~53 m):
  4-storey cream garage podium (terracotta waterline band, dark opening + oval-porthole
  bands, seafoam round 'ship's-wheel' vent near the river end), sheer full-height slab on
  the river half, ~7 two-storey terraced setbacks cascading toward the shore, floors locked
  to the style-7 2.75 m shader grid, balcony rails per floor, three tilted ship-funnel
  wind scoops on the river-end roof.
- **Center City glass:** outer glass towers get a world-space curtain-wall shader
  (onBeforeCompile on `outerGlassMat`: 4.0 m floor spandrels 22% darker, 1.5 m vertical
  mullions, fwidth-AA'd, distance-faded) + `GLASS_TINTS` location-matched signature
  colors (Liberty Place blue `#6899c4`, Comcast silver `#b4c2c8`, CTC `#a3b1b8`, FMC
  `#b5d0dc`…) over a bluer default `glassPal`.
- **`BRIDGE_SKIP`:** OSM maps both bridges' towers/anchorages as building footprints which
  rendered as window-checkered boxes on the towers — the wide pass now drops footprints
  within 45–60 m of those six points.
- **Dev harness:** `?dev=1` `__dbg` now also exposes `scene`, `fly`, `goFly(x,y,z,yaw,pitch)`
  and `frameOnce()` (synchronous update+render — works while the tab is hidden/rAF-throttled;
  pair with drawing the canvas into a 2D canvas + POSTing the JPEG to a local sink for
  headless screenshot verification).

Realism round 2 (Aug 24, afternoon — driven by Mike's artifact screenshots):
- **Road flicker root cause found and fixed:** pack_wide never clipped roads against the
  core, so every core street carried a coplanar wide-set duplicate (THE longstanding
  shimmer); the app now drops wide road segments whose endpoints are both inside
  `CORE_EXT`±38 (core's `runsOf` covers to +40). Also: wide road quads were double-wound
  (both windings shared vertices, so `computeVertexNormals` summed to ~zero and random
  quads shaded black) — now single-wound on a DoubleSide material; wide road classes get
  separated lifts (motorway highest) so crossing carriageways never z-fight.
- **I-95 now runs down IN the trench** (custom ribbon height fn for `/motorway/` within
  the corridor, floor+0.55); cross streets still bridge at grade; trench floor lightened.
- **White slab on the Delaware fixed:** the core city heightfield pinned everything east
  of the trench at trench-floor height (above water) out to the core bbox edge — river
  cells now drop to `TERRAIN.bed`.
- **"Missing" building faces fixed:** the facade shader's detail fade keyed on
  `fwidth(uW)`, which explodes on edge-on walls and blanked whole facades at grazing
  angles; `det` now keys on `fwidth(v)` only.
- **City Hall tower** rebuilt at (−1603,−802) (OSM parts skipped): buff masonry shaft to
  102.7 m, light-gray clock stage to 122 m with 7.9 m amber faces on dark surrounds,
  4-sided tapering top to 152.4 m, cupola, and an 11.3 m patina-bronze Penn to 167 m —
  research-backed (548 ft total, two-tone stone/metal split at 337 ft).
- **One & Two Liberty Place** rebuilt (parts skipped; complex mid-rises kept): blue-glass
  shafts through the curtain-wall shader, nested cross-gable crown tiers (4 on One to a
  288 m needle mast, 2 on Two to its 258 m finial) with white eave/ridge trim reading as
  the real chevrons. Grid frame from the Front-St line fit (`ryG`).
- **Plaza fixes:** `plazaLift` feather widened 4→16 m with smoothstep (the tight linear
  falloff aliased into wedges through the 10 m drapes — Mike's "clipping"); tree trunks
  extended 0.8 m below grade; trees excluded from the berm ellipsoids (`bermSpots`);
  pool water recolored `#3fa9c9` with a white coping ring (footprint stays OSM-exact —
  verified: model streets match raw OSM within 4–6 cm mean).
- **Live weather:** Open-Meteo current cloud cover + wind for the site, fetched at load
  + every 15 min — gated off claude/usercontent hostnames (artifact CSP), so it is live
  on GitHub Pages/local and falls back to fair-weather in the artifact. Drives a
  procedural FBM cloud layer in the sky shader (uCloud/uTime/uWind/uCloudLight), sun
  dimming (×(1−0.72·cover)), sky graying, and a ☁ % readout in the T panel. `__dbg.WX`
  lets you force cover in dev.

A second 19-agent adversarial pass on round 2 confirmed and fixed: motY band edges 1 m
narrower than siteY's trench band (7 m vertex spikes — now exact-edged, blended over 14 m
laterally and 60 m at the core z-boundaries so I-95 ramps out instead of burying); the
wide-road core clip erased streets the core extract lacks (now also requires
`nearRoad(…, 3.5)` so only true duplicates drop); One Liberty's tier-1 eave floated 7 m
above its shaft; cloud drift phase now accumulates (`uCloudOff += wind·dt` — wind updates
used to teleport the deck); weather changes force an env rebake and dim the baked env sun;
grazing-angle shutter/door hash terms re-gated with `detU`; heightfield river margin −4 m;
cap-deck trunks lifted clear of the I-95 tunnel. NOTE: `WX` must stay declared before the
sky material — `refreshEnv` reads it during init (TDZ crash otherwise).

Round 3 (Aug 24, evening — night lighting, City Hall, stadiums, whole-city groundwork):
- **Night windows fixed:** `shtLit` used `step(0.42, lit)` but `lit` is always ≥ 0.45 by
  construction, so EVERY window glowed. Now ~1/3 of windows light at varied warmth
  (`step(0.82, lit)`), and as the pattern fades with distance facades keep a soft
  aggregate glow (`mix(0.115, …, det)`) instead of dying to gray. The outer glass towers
  get per-panel lit windows via the curtain-wall shader (`gLit`/`gWall`/`gSpand` globals
  feeding `totalEmissiveRadiance`), night intensity 0.55.
- **City Hall completed:** the main Second Empire block was entirely missing (outline
  dropped at pack for containing part centroids; wings never mapped as parts) — now
  custom-built: hollow square with courtyard (appendBuilding + holes, style 1 arched
  windows), mansard wing prisms, corner + center pavilions with slate caps, staged
  tower, white clock stage with corner turrets, amber clocks on dark surrounds, ogee
  dome (stacked 4-side frustums), lantern, dark-bronze Penn. Skip radius 24 at
  (−1603,−802).
- **Stadiums reworked from photos:** CBP = brick drum + upper horseshoe OPEN beyond the
  outfield (`arcOf` ring-arc helper), pale-green canopy band, dark-red light standards,
  infield dirt diamond; the Linc = dark lower bowl, silver sideline stands, steel wing
  canopies with white fascia, 4 corner masts; Xfinity Arena = dark walls, pale roof
  slab, glass rotunda, purple screens. Stadium fields are fan-triangulated (earcut
  threw on the OSM rings — the fields never rendered before) and OSM pitch/park drapes
  inside the venues are skipped (they z-fought the bowls).
- **Low-terrain flooding fixed:** NED reads made-land near/below 0 ASL at the sports
  complex etc.; outside the core, low terrain now clamps just above the water plane
  UNLESS east of the `DEL_BANK` Delaware west-bank polyline (there it still dives to the
  bed = river). Wide/far OSM water polygons draw at water+0.55 (above the clamp).
- **Whole city SHIPPED:** `fetch_city.py` (resumable, per-tile checkpoints in
  `city_tiles/`, both gitignored with the 377 MB `osm_city_raw.json`) fetched University
  City/West/SW+airport, North Philly, the Northeast, and Roxborough/Germantown + a 150 m
  `dem_city.json`; `pack_city.py` (needs shapely — venv, `pip install shapely`) MERGES
  rowhouse rows into block strips (buffer 1.8 union per 400 m cell, height-bucketed /4),
  drops sheds, and packs at 0.7 m into `city.b64` (magic 0x53485459, 7.1 MB b64:
  373k buildings → 142k solids, 18k road runs, 964 areas). App step 'Raising the rest of
  Philadelphia' decodes it (2400 m chunks on cityMat, 100 m far ground strips, far roads
  with the same continuity treatment, far district labels); `DEM_CITY` slots into demAbs;
  bounds/fog widen to the full city (fog 2400/13000). Page = 14.25 MB — the artifact cap
  is 16 MB, so any future data must fit ~1.7 MB or go Pages-only. PHL's runways/taxiways/
  aprons pack as roads/areas and read beautifully. `COLORS.skyGround` lightened + the
  dome's below-horizon slope softened (from altitude the dome shows past the world edge).
- **Road continuity audit (agent) + fixes:** pack_wide's CLOSED-ring simplifier was
  amputating the final segment of every wide road (now `simplify_open` + run-splitting
  at bbox exits — THE "roads stop mid-block" bug); river crossings now render as bridge
  decks (class ≤ primary lifts to water+13/+20 inside `riverCorridor` = east of DEL_BANK
  or within 260 m of the SCHUYLKILL polyline) instead of vanishing, minor roads still
  skip; wide/far quad strips get joint fans at bends; duplicate-dropping now requires
  PARALLEL alignment (`nearRoadAligned`, midpoint too) so crossings/carriageways survive;
  road heights snap per shared endpoint (`ySnap` maps — no steps at OSM way splits);
  the wide lift blends to the core formula within 60 m of the seam. pack_city splits
  runs instead of truncating/point-filtering. FUTURE (for Mike's traffic goal): pack a
  shared node table + edges with class/oneway/bridge flags and generate both render
  geometry and a routable graph from it — see the audit in this session's notes.

**"Hollow buildings" on Mike's machine (Aug 24 night):** his screenshots show near walls
losing the depth test (far walls' fronts punching through, triangle-shaped slivers) SE of
City Hall. NOT reproducible in the Chromium in-app browser; the packed rings, winding,
and normals were all verified correct programmatically (3.36 M wall tris, 0 winding/normal
mismatches; 1 invalid ring in 112k, elsewhere). Diagnosis: `logarithmicDepthBuffer`
(per-fragment gl_FragDepth writes) misbehaving on his browser — Safari/Metal WebGL2 is the
known offender. Fix: Safari UA now gets a standard depth buffer (near 1.0, far 26000 —
also raised from 9000 for the citywide view; ?logdepth=1/0 forces either path). If hollow
walls ever show on Chrome too, this diagnosis is wrong — reopen with an exact-view repro.

**RESOLVED (Aug 24, round 4): the far-ring hollow buildings were a real winding bug, not
Safari.** `THREE.ShapeUtils.triangulateShape` (earcut) emits triangles in a CANONICAL
orientation — CCW in the shape plane — regardless of the input ring's winding (verified
empirically in node: CW and CCW squares/L-shapes all come back CCW). The roof-cap code in
`appendBuilding` (wide) and `appendB` (far ring) flipped the triangles when
`ShapeUtils.area(v2) > 0`, i.e. exactly for rings that arrive CW in numeric (x,z). The wide
set never showed it because process_osm.py `ensure_ccw`-normalizes every outer ring; but
pack_city.py emits shapely output raw, and GEOS/JTS buffer produces **CW shells** — so every
merged block strip (and ~half the solo talls) got a downward-facing, backface-culled roof:
walls stood like cardboard cutouts with the ground showing through. The fix: caps ALWAYS
emit earcut's triangles forward (CCW in the (x,−z) plane = up-facing in world). The wall
quads were always correct (their normal and winding both key off the same signed-area sign,
so they cancel). Gotcha for the future: **never orient earcut output by the input ring's
winding.**

South extension (Aug 23): Lincoln Financial Field and Citizens Bank Park are `stadium` relations →
rendered as seating bowls (type 8) around sunken fields, with the Linc's sideline canopies and
CBP's light towers; Xfinity Mobile Arena (ex-Wells Fargo Center, type 9) as a flat-topped oval;
the Walt Whitman Bridge follows OSM's motorway alignment (`wwb.json`) with towers at ±305 m of the
water-crossing midpoint, deck 46 m over the river.

Wide-area backlog (research in `wide_landmarks_research.json` has heights/massing for ~150
buildings): the Market-Frankford El viaduct (railway ways were fetched but not packed — add
`railway=subway` ways as an elevated ribbon at +7 m along Front St / Kensington Ave); City Hall's
tower is in via `building:part` but the Penn statue / clock stage are plain; church-specific
heights (St. Michael's 50 m, St. Peter the Apostle 70 m, Assumption BVM twin towers) could replace
the generic steeple; Piazza/Schmidt's Commons, Waterfront Square towers and Rivers Casino are
plain OSM boxes; Camden's Battleship New Jersey and Adventure Aquarium are not modeled.

Ideas discussed but not built (see also `geo_audit.json`):
- Dusk/night mode with lit windows (would suit the bronze-glass towers)
- Guided fly-through tour of the viewpoints
- Marriott's hipped wing roofs (currently a flat dark cap); Hopkinson House balcony relief
  (currently color only); The Ryland's rooftop pool (OSM has it, but its true position
  falls off our smaller OSM-footprint deck)
- Penn's Landing park-cap construction area is bare in current imagery — could model the
  finished park

Round 4 (Aug 24, late — Mike's screenshot-driven fixes):
- **Far-ring roofs restored** (the cap-winding bug above — the headline fix).
- **Towers pinned to the researched 18×12 bays.** `bays` was derived from the OSM
  footprint (`round(inner/1.83)`) and two of the three towers (W 32.91/32.21) rounded to
  17 wide-face bays; Mike counted 18 on the real building. Now
  `s.len >= max(W,Dp)-0.01 ? 18 : 12`. Colonnade columns also extend 0.9 m below grade
  (they sat exactly at podium height and could show a float gap on the drape).
- **William Penn statue** on City Hall sculpted from primitives (plinth, calves, flared
  coat, torso, cravat, head, brimmed hat, left arm extended NE + hand, right arm with
  charter box), `cPenn 0x4c4536`. Feet at +155.8, hat crown ≈ +167 (548 ft) — matches
  the photo silhouette from skyline distance.
- **The Ryland** recolored: bars `0x4f7ba1` (Liberty-family blue), mullion grid and
  3-floor bands `#3d5a73` (darker than the glass, curtain-wall rhythm), parapet screen
  `0x6c93b4`. It used to read white — Mike: "it does not appear white in real life."
- **SHT pool terrace rebuilt level.** Root cause of BOTH the "odd shaped pool" and the
  "pillars clipping": the pool/coping/deck were 4-corner `flatPoly`s lifted per-vertex by
  `siteY`, and the terrace sits ON the plaza feather (58→74 m), so each plane tilted
  differently (deck corner +0.5 m, pool corner +0.04) and they sliced each other and the
  colonnade line. Now: one level skirted slab (`buildingGeom(deck, [pool], ref+0.14,
  ref-1.8)` at `ref` = highest ground under the deck), pool as a true hole with inner
  walls, water sunk in-ground at top−0.12, flush coping ring at top+0.012 with the pool
  hole, and 16 `poolTreeSpots` ringing the deck 3.1 m out (planted through the tree
  step's `clear()` so none land in buildings/roads).
- **Grass actually darker.** The pipeline stores colors WITHOUT sRGB→linear conversion
  (r149 legacy color mode) and ACES+noon sun lift flats ~2.5×: `0x5d7247` rendered pale
  mint (`0x3b3833` asphalt renders light gray, same reason). `COLORS.park` is now
  `0x243818` / `parkDark 0x1d2c13`, area brighteners trimmed (core 0.84+0.16·h, far
  0.82+0.18·h), canopies slightly deeper (base L 0.17-0.23 S 0.46+, lumps L 0.24-0.33).
  Lesson: pick flat-surface colors by RENDERED swatch, not by hex intuition.
- **Skyscraper facades.** Tall (h>45) wide/far buildings draw from `palTall` (precast
  tan, aluminum, blue-gray, dark curtain, bronze, limestone, buff, charcoal, steel blue)
  with tighter value jitter; style-2 windows enlarged (0.74·pitch × 1.95); and the
  facade shader's distance fade now converges styles 2/6/7 to the true wall+glass
  average (`mix(diffuse, vec3(.115,.13,.155), .48)`, weight 0.92) instead of reverting
  to pale wall — distant towers used to wash to white boxes.
- **Hidden-tab loads no longer crawl:** both decode steps' `yieldNow` use a
  MessageChannel ping (setTimeout is clamped to 1 s+ in hidden tabs; the far-ring decode
  took minutes headless).

Round 5 (Aug 24, night):
- **South-tower pillars floating (Mike's screenshot, "stopping short of the ground"):**
  the podium plateau was purely radial (`PLAZA_R` 58 + 16 m feather from the towers'
  center) but the south tower's SE corner sits ~70 m out — the lawn feathered DOWN
  under the fixed-height tower base, so its colonnade and lobby glass hung up to
  ~0.9 m above the local ground. Fix: `plazaLift` now also carries a full-height
  rectangular pad per tower (footprint + 5 m, 12 m feather, rotated to each tower's
  angle; `towerPads`), so ground under every footprint is exactly podium level; the
  lobby glass also runs 0.8 m below grade like the columns. Verified at the exact
  vantage: no gap at any column or the glass line, all three towers.
- **Philadelphia Museum of Art rebuilt** (was a flat 10 m OSM extrusion on the hill):
  custom golden-temple massing in its own Parkway-rotated frame at (−3112, −2242),
  axis (0.717, 0.697) — terrace plinth, central temple block (ridge +34) with stepped
  podium, 8-column portico, golden pediment shell + nested brick-red tympanum, rear
  range with outward gable ends, two forward wings (ridge +26) with 6-column
  pavilions facing the court, blue-gray tile gable prisms (`roof()` helper — gPrism
  is grid-locked, this one rotates into the museum frame; rotate, never mirror, or
  the winding flips), octagonal court fountain, and the Rocky steps as eight broad
  flights interpolating down the DEM toward Eakins Oval. Walls are style 1 (arched
  fenestration). The OSM footprint is dropped via `BRIDGE_SKIP` (−3094, −2225, r 130).
  Colors are stored dark for the legacy pipeline: walls 0x8a744c, roofs 0x2e3d47.

Round 6 (Aug 24, late night):
- **Night window lights carry ~3.5× farther on tall buildings.** The facade patterns
  fade with `det` for anti-aliasing, which collapsed distant towers into solid dark
  shapes at night. Both shaders now have a second LOD: past the per-window fade,
  3×2-window CLUSTERS (constant per superblock, ~20% lit at window-like brightness)
  stay resolvable until `det2` (thresholds 0.55/1.5 on fwidth(v) in cityMat;
  1.0/2.8 on max(aaU,aaV) in the curtain shader) fades them into the aggregate glow.
  Styles 2/6/7 only (`sbLit = -1` sentinel means "style has no cluster LOD" — do not
  let the ladder run for rowhouses or the mid-band aggregate glow dies). Balance
  matters: the first cut used 40% clusters at 0.4–0.9 and towers turned into cream
  checkerboards even at dusk — keep cluster fraction × brightness ≈ the per-window
  layer average.
- **Ground no longer reads as water at dusk/dawn/night:** `groundMats` (core
  `groundMat` + far `farGroundMat`) are retinted every frame in `applyLighting` —
  night 0x232321 → twilight warm earth 0x55503f → day `COLORS.ground` — using the
  same night/twi/dayF blend as the sky. The fixed pale sage albedo caught the cool
  ambient after sunset and read as flooded terrain.

Round 7 (Aug 25):
- **Viewpoints dropdown removed from the bar** (Mike's request). The viewpoint list +
  functions remain in 'Charting the viewpoints' behind an `if (sel)` guard, so a
  future UI can re-add a `#viewpoints` element and everything rewires itself.
- **Landmark labels default OFF** (`labelsOn = false`); the Aa button starts dimmed
  (`syncLabelsBtn`), L key / button still toggle.
- **Full map on mobile**: the `isTouch` gates that skipped the wide set and the far
  ring (and `haveWide`) are removed — phones now load all ~250k buildings
  (~5.9 M tris, verified in mobile emulation). The guards dated from before the
  merged-strip packing and MessageChannel yields; DPR stays capped at 1.5 and
  shadows at 2048 on touch.
- **Fly is now fully usable on touch**: on-screen ▲/▼ hold-buttons (`#flyctl`,
  right-thumb reach, shown only in fly mode on touch) climb/descend like E/Q, and
  the left joystick doubles as a THROTTLE — its magnitude now runs past the ring to
  2.4 (`Math.min(2.4, d/44)`), fly scales speed by it (`jm`), the nub display clamps
  to the ring, and WALK is unaffected because applyWalk normalizes the wish vector.
  Verified: ▲ press climbs in emulation; joystick math shared with desktop paths.

Round 8 (Aug 25):
- **Touch fly tips modal** (`#flytips`): on touch, the FIRST Fly tap shows a control
  card (left thumb joystick + throttle, right thumb look, ▲▼ climb) and only the
  Okay button proceeds into fly mode; later taps skip it (`flyTipsSeen`, per load).
- **The bar's icon buttons (Aa / ◐ / i) were invisible glyphs**: they carry the
  `.panel` class but the `.seg button, #bar .iconbtn` reset sets
  `background: transparent` at higher specificity, so they floated bare over the
  scene. A follow-up `#bar .iconbtn` rule restores a dark rgba(23,21,18,.85)
  panel + border. (The seg buttons stay transparent — their wrapper carries the
  panel.)

Round 9 (Aug 25 — four landmark rebuilds from Mike's reference photos):
- **Battleship New Jersey (BB-62)**: the wide set's `USS New Jersey` t='ship' footprint
  (996, 663, Camden shore) used to render as a 13 m hull-shaped box. The wide loop now
  intercepts it (`njPoly`) and a custom builder extrudes the real OSM hull outline
  (water−1.5 → +8.7), detects the bow as the pointier OBB end (it points north, toward
  the BFB), and adds superstructure decks, the forward tower, two funnels with black
  caps, masts, and three triple 16-inch turrets (turret 2 superfiring on a barbette,
  turret 3 trained aft) — all in the hull's frame via `at2`/`shipBox`/`shipCyl`.
- **US Custom House** rebuilt: limestone base, deep-brick shaft to 40 m (style-2 grid),
  square stone stage, two flat-faceted octagonal drums (`toNonIndexed` +
  `computeVertexNormals` — indexed cylinders shade like smooth cones), colonnade
  lantern, dome, finial to ~90 m. Matches the brick-below/white-crown photo.
- **Man Full of Trouble Tavern** (OSM name 'Man Full of Troubles Tavern', by the pool):
  custom gambrel roof (two slopes a side + pentagon gable ends, built in the OBB frame;
  `detail` material is DoubleSide so winding is safe), cream pent between floors +
  cornice, two dormers with pyramid caps, end chimney.
- **Glory Beer Bar & Kitchen, 126 Chestnut**: OSM maps the lot as THREE unnamed boxes
  front-to-back; matched via REALISM_NEAR **area-weighted** centroids (the app's
  polyCentroid, not a vertex mean) — front (64.6,−309) = dark cast-iron section with
  5 granite piers + transom + cornice on the STREET face (chosen as whichever OBB face
  points north — this parcel's LONG axis runs to the street, don't assume the
  perpendicular), mid connector, rear 5-story brick in style 5 (storefront style =
  same sash windows as style 0 but NO shutters; the photo has none).
- **Gable spike guard**: the generic rowhouse gable pass now requires the simplified
  quad to be CONVEX before pitching (crossed/concave quads produced roof spikes).
  NOTE: one leaning ridge sliver remains visible from Chestnut St street level near
  Glory (a legally-convex but heavily skewed neighbor quad) — cosmetic, backlog.

Data © OpenStreetMap contributors (ODbL) — the credit link in the About panel must stay.
