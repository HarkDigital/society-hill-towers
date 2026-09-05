# CLAUDE.md

Philly3D (repo `HarkDigital/society-hill-towers`) is a living, single-file Three.js model of
Philadelphia: a detailed Society Hill core, the wide Center City / South Philly set, and a far
ring covering the whole city, on USGS terrain, with live SEPTA / Indego / flights / ships,
typical traffic, a solar clock and live weather. Live at https://philly3d.com/ (VPS) and
https://harkdigital.github.io/society-hill-towers/ (Pages). Everything is in `3d-model/`;
`app.js` (~11,000 lines, one IIFE) is the whole application, `build.py` inlines it with the
data into `society-hill-towers.html` (24.85 MB raw / 10.58 MB gzip). The old claude.ai
artifact copy is retired (over the 16 MB cap); never republish there.

## Coordinate frame

x = east, z = south, y = up, metres. Origin = the towers' centroid, 39.94547 N, 75.14475 W
(`x = (lon − lon0)·111320·cos(lat0)`, `z = −(lat − lat0)·110574`). City Hall is at
(−1603, −802). Every scene json, packed blob and hard-coded position uses this frame. The
street grid is ~10° off the axes: use the fitted Front St line (`fl`/`ryG`), never raw x.
`siteY(x, z, 'ground'|'road')` is the one function that puts anything on the terrain. The
flight limit is the city line buffered 2 km (`city_limit.json`, `insideLimit`/`clampLimit`):
the camera never leaves it, the towns beyond it are scenery.

## Commands

```bash
cd 3d-model
python3 build.py                         # build the page; prints a per-blob size table
python3 -m http.server 8917              # preview at http://localhost:8917/society-hill-towers.html
python3 -m unittest discover -s tests    # tests
python3 pipeline.py --graph              # the data pipeline (fetch -> process -> pack -> bake -> build)
python3 docs_check.py                    # handoff.md's file table covers every input and script
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # pipeline deps only
```

Laptop caveat: the Browser pane's dev server cannot `getcwd()` inside CloudStorage, so serve
the built page from a scratch copy (the `sht-*-scratch` entries in `.claude/launch.json`),
not from the checkout. The pane runs no rAF: drive frames with `__dbg.frameOnce()`.

## Hard constraints

- No npm, no bundler, no framework: plain Python 3 build, vendored `three.min.js` (r149,
  pinned; see handoff gotcha 11 before touching it), one self-contained HTML that GitHub
  Pages can serve as a file. Every asset is inlined (fonts, icons, data).
- `build.py` must keep its guards: missing/undersized input, leftover `{{PLACEHOLDER}}`,
  `</script` inside a blob, page over 25 MB.
- The OpenStreetMap credit link (`#osmcredit`, bottom credit line) must stay. Data terms are
  in `DATA-LICENSE.md`; code is MIT (`LICENSE`).
- No em dashes or middot separators in any user-facing string (veil, hints, cards, panels,
  tooltips, loading messages). Commas, colons, sentences. Docs and code comments are exempt.
- Owner decisions that stand until Mike says otherwise: landmark labels OFF by default (the
  citywide tier is behind the L key); the About panel stays out of the bar (the "Credits" link in the bottom credit line opens it); fly is the only mode
  (orbit is the attract loop, walk is `__dbg.goWalk` only); SEPTA/Indego markers are occluded
  by buildings, neighborhood names and the search pin are not; roof forms come from the LiDAR
  streaming pass, then OSM roof:shape, then the lottery, packed in the roof word (see
  pack_city.py); storefronts come from `storefronts.b64`, and the outer districts' wall colours
  from Mapillary block faces (`wide_walls.b64`, colour byte plus a trim/window hint byte; a dry-run bake
  never ships); facades come from the 19-style vocabulary in `fabricStyle`/`towerStyle` (app.js) and the
  Center City towers from `towers.json` (research-derived facade archetype, crown, tint); the
  Schuylkill's course and its park reach's water come from `schuylkill.json` (OSM waterway ways),
  and `pack_wide.py` insets any record whose wall shares a plane with a larger one; the look leans toward
  Cities: Skylines 2 (reflective tinted window glass with sun-aware reveals, brick, stone, panel and stucco
  textures in the facade shader, a deep-blue sky with a ray-marched cumulus deck (a 720 m slab from 1,900 m,
  `CLOUD_STEPS` samples, sunlit tops and self-shaded bellies) whose shadows slant by the
  sun, clear air 8 to 40 km by day (the whole city stands clear from any height) and about 3 to 16 km by night, deep-blue body-colour water as a moving noise field with no
  shore tint, a painted olive meadow on every green AND on all bare ground (Round 52: `groundSurfMat`, the
  same meadow and the same darker-blotch mottle as the parks, parks and ground are one surface; no park
  shade spread, no ground retint), an instanced tuft field near the camera on parks and bare ground, lumpy
  flat-shaded low-poly crowns under leaf cards, wind in the crowns and blades, saturated palettes, rooftop
  clutter on desktop, awnings, lane paint on every road (`aLane` + `lanePatch`: a double yellow centre from
  6.5 m wide, white dashes by width, edge lines on the divided highways, nothing on service and footways),
  stored-dark asphalt lots (`LOT_COL`) with stall stripes that fade past 500 m, and every surface lot, industrial and retail yard, rail yard and apron in the city paved from `paved.b64` (`fetch_paved.py` / `pack_paved.py`, the 'Paving the lots and yards' step, `conformDrape` under the parks), and on desktop WebGL2 an HDR
  post pipeline: half-float target, ACES + sRGB composite, bloom on the sun, the glints and the cloud rims
  with the markers and labels masked out of it (`postRaw(mat, { mask: true })`), `?bloom=0` off), never its
  assets; every flat outside the core (parks, lots, aprons) is laid with `conformDrape` on the drawn ground
  mesh (`groundGrids`/`groundMeshY`), never with `drapedPoly` (its point cap put big sheets at 36 to 61 m
  against a 25 m mesh and the ground rose through them); the Round 50
  key-to-fill ratio (sun 2.0, hemi 0.10 + 0.36 dayF) and the deep-blue zenith stand; a search result glides in and
  circles its spot until the first input takes flight (live buses are followed, not circled).
  The clock is never remembered: every load is Philadelphia's own time, and only a copied
  link carries a pinned clock. The two stadiums are built after the wide loop from
  `south_geometry_research.json` and light up at night; the sports complex is asphalt with
  striped stalls (`parking_south.json`), and ESPN scoreboards put a score bubble over a venue
  during a Philadelphia home game.
  Phones: portrait shows the turn-sideways gate, the Move and Look thumb pads stay faintly
  visible in flight, and `detFarUniform` keeps lit windows alive to desktop distances.
- Commit the built page with the source, then push and run `deploy_philly3d.sh` after every
  verified update without asking (Mike, Sep 5, 2026: no permission needed to deploy from here on).

## URL flags

`?dev=1` exposes `window.__dbg` (camera/fly/scene/renderer handles, `wx('storm')`, `bolt()`,
`flightTest()`, `shipTest()`, `frameOnce()`, `goFly(...)`, `goWalk(...)`, `post`, `postMats()`, `skyMat`,
`cloudDeck`, `sunLight`, `hemi`, `refreshEnv()`, `perf()` with
per-step build timings, frame-time p50/p95, `renderer.info` and heap) plus an on-screen perf
readout. `?dpr=N` pins the adaptive pixel ratio. `?wx=<preset>` pins weather
(clear, overcast, fog, drizzle, rain, downpour, storm, hail, snow, blizzard, sleet).
`?logdepth=0` is the depth-buffer escape hatch.

## Where things are

`app.js` reads top to bottom with `// ---- banner` comments (grep them): config, dom,
helpers, lighting & sky, data-driven build, overpasses, living water, terrain, ground/water/
roads/parks, the city fabric (facade shader), landmark spires, researched landmark models,
museum ships, the three towers, the outer districts (`wide.b64`), the far ring and the towns
across the city line (`city.b64` and `outskirts.b64`, one `raiseRing()` decoder), trees, labels, controls, modes & viewpoints, live SEPTA transit, layers panel, street names,
places, address search, live Indego, live flights, live ships, traffic, streetlights, solar
clock + weather, build & loop; the post pipeline sits with the renderer near the top. Build steps are `step('Name', fn)` calls run in order by
`build()`. `template.html` is the chrome, `style.css` the HUD + embedded Montserrat,
`about_body.html` the hidden About panel. Pipeline scripts and data files are tabulated in
`handoff.md` ("What's in 3d-model/").

## Deploy

`3d-model/deploy_philly3d.sh` builds and rsyncs to the VPS (philly3d.com; stages + chmods
644 because this checkout's files are 0600). `git push` publishes GitHub Pages (the built
page is committed). Both homes ship the identical build. Verify Pages by grepping the tail of
the page, not its head.

## Read before changing anything

`handoff.md`: file table, build, architecture, and the "Hard-won gotchas" (winding, z-fight
layers, earcut orientation, the r149 colour pipeline, freeOnUpload vs frustum culling).
`devlog.md`: the full round-by-round log, Rounds 1–45 plus the VPS incident, with every
decision, reversal and measured fact. Find the entry for whatever you are touching first.
