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
  by buildings, neighborhood names and the search pin are not; a search result glides in and
  circles its spot until the first input takes flight (live buses are followed, not circled).
  The clock is never remembered: every load is Philadelphia's own time, and only a copied
  link carries a pinned clock. The two stadiums are built after the wide loop from
  `south_geometry_research.json` and light up at night; the sports complex is asphalt with
  striped stalls (`parking_south.json`), and ESPN scoreboards put a score bubble over a venue
  during a Philadelphia home game.
  Phones: portrait shows the turn-sideways gate, the Move and Look thumb pads stay faintly
  visible in flight, and `detFarUniform` keeps lit windows alive to desktop distances.
- Commit the built page with the source. Do not push or deploy unless asked.

## URL flags

`?dev=1` exposes `window.__dbg` (camera/fly/scene/renderer handles, `wx('storm')`, `bolt()`,
`flightTest()`, `shipTest()`, `frameOnce()`, `goFly(...)`, `goWalk(...)`, `perf()` with
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
clock + weather, build & loop. Build steps are `step('Name', fn)` calls run in order by
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
