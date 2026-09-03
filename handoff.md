# Philly3D — Handoff

Philly3D is a living, single-file Three.js model of Philadelphia: the detailed Society Hill
core (Society Hill Towers, I.M. Pei, 1964, plus ~2,800 buildings with LiDAR-measured massing
and parcel-driven facades), the wide Center City / South Philadelphia / river-wards set
(~111k buildings), and a far ring covering the rest of the city (~180k footprints merged into
block strips), on real USGS terrain with the Delaware and the Schuylkill, the bridges and
viaducts, live SEPTA vehicles, Indego, flights and ships, typical traffic from PennDOT counts,
the city's own street trees and streetlights, a solar clock with the real moon, and live
weather. It began Aug 14, 2026 as a Claude artifact of the towers and was rebranded Philly3D
on Aug 26. The repo, the folder and the built file keep the `society-hill-towers` name for
URL stability.

**Two homes, one identical build:**

- https://philly3d.com/ — Mike's IONOS VPS (nginx, ssh `Host lionspool-vps`; the box also
  serves harkpicks.com and thelionspool.com, `nginx -t` before every reload). Shipped by
  `3d-model/deploy_philly3d.sh` (build → guards → stage + `chmod 644` → `gzip -k9` → rsync).
  The VPS also serves the same-origin `/adsb` flight proxy that both homes use.
- https://harkdigital.github.io/society-hill-towers/ — GitHub Pages from
  `HarkDigital/society-hill-towers` (root `index.html` redirects into
  `3d-model/society-hill-towers.html`). Rebuild, commit, `git push`; the built page is
  committed. Pages has no CSP, so live fetches work there.
- The original claude.ai artifact copy (`claude.ai/code/artifact/04f16de9-…`) is **retired**:
  the page is 24.85 MB, far over the artifact's 16 MB cap, so it can no longer be current.
  Do not republish there; if someone reports a stale or sunny-in-the-rain page, ask which URL.

**Sizes (verified 2026-09-02):** built page 24.85 MB raw / 10.58 MB gzip, of which the towns across the line (`outskirts.b64`, real footprints plus the land-use filler) are 2.05 MB raw; 22.83 / 9.77 before them (22.98 / 12.76 before
today's byte-planar blob shuffle in build.py). `app.js` is ~11,000 lines.

**Gitignored** (everything else, including the built page, is committed): `.DS_Store`,
`.claude/`, the three raw Overpass dumps `3d-model/osm_wide_raw.json` (95 MB),
`osm_south_raw.json`, `osm_city_raw.json` (4.09 M elements), `3d-model/city_tiles/` (per-tile
fetch checkpoints), `3d-model/lidar_cache/` (footprint cache, COPC tiles, OPA rows, ortho
tiles, raw tree/pole/places/traffic downloads), and `3d-model/baseline.html`.

## What's in `3d-model/`

Every `ROOT / "..."` input of `build.py` and every `*.py` in the folder is listed here;
`python3 docs_check.py` fails if one goes missing from this table.

### The page and the app

| File | Role |
|---|---|
| `society-hill-towers.html` | The built, self-contained page (24.85 MB raw / 10.58 MB gzip). Output of `build.py`, committed, served by both homes. |
| `template.html` | Page shell: a real document head (title, description, canonical, OG/Twitter card, inlined favicons), the veil, bar, panels, the bottom credit line, and the `{{CSS}} {{DATA}} {{THREE}} {{APP}} {{ABOUT_BODY}} {{FAVICON_SVG_B64}} {{FAVICON_32_B64}} {{APPLE_ICON_B64}}` placeholders. |
| `app.js` | All application code (~11,000 lines, one IIFE). Everything interesting is here; see Architecture. |
| `style.css` | HUD chrome plus the embedded Montserrat faces (base64 woff2, OFL). |
| `about_body.html` | About panel prose, key table and credits. The panel is hidden by owner decision (since Round 22; `btnAbout` display:none, `i` unbound, code intact). |
| `three.min.js` | Three.js **r149** UMD, inlined at build. Pinned: see gotcha 11 before upgrading. |
| `build.py` | Assembles the page (stdlib only). Refuses to ship a missing or undersized input (`--allow-missing` overrides), prints a per-blob size table, and aborts on a leftover `{{PLACEHOLDER}}`, `</script` inside any blob, or a page over 25 MB. Stores the int16 blobs byte-planar (see Build). |
| `deploy_philly3d.sh` | One-command ship to philly3d.com: build, refuse a proxyless or unbranded build, stage the six files + `chmod 644`, `gzip -k9`, rsync. |
| `flight-proxy-worker.js` | Fallback recipe: a ~30-line personal Cloudflare Workers / Deno passthrough for adsb.fi, for the day the VPS `/adsb` proxy goes away. |
| `brand/` | Identity: `mark.svg`, `favicon.svg`, `make_brand.py` (renders `dist/`: favicon.ico/svg/16/32/48, apple-touch-icon, lockup, og.png), `og_raw.png` (a curated capture, do not regenerate blindly), `og_sink.py`, `preview.html`, `Montserrat-SemiBold.ttf` + `OFL.txt`. `build.py` inlines `dist/favicon.svg`, `favicon-32.png` and `apple-touch-icon.png`. |
| `MontserratItalic.ttf` | Variable font `bake_street_sdf.py` renders the street-name atlas from (OFL). |
| `requirements.txt` | Pipeline venv: shapely, numpy, pyproj, laspy[lazrs], Pillow. The build itself needs nothing. |
| `pipeline.py` | Pipeline runner; `python3 pipeline.py --graph` prints the fetch → process → pack → bake → build graph. |
| `overpass.py` | Shared tiled Overpass fetch: mirrors, backoff, per-tile checkpoints (`city_tiles/`, `wide_tiles/`, `south_tiles/`), a missing tile is fatal. |
| `philly_frame.py` | The one lat/lon to local-metres frame (LAT0/LON0/KX/KZ, `to_xz`, `to_latlon`) every pipeline script imports. |
| `provenance.py` | `record()` appends one line per fetch to `provenance.jsonl` (source, URL, query hash, element count, UTC time). |
| `ops/` | Server recipes: the captured live nginx vhost and the `.example` with the planned additions, systemd units, `septa_bake.py`, `ais_relay.py`, `uptime.md`, `README.md`. |
| `tests/` | `python3 -m unittest discover -s tests`. |
| `docs_check.py` | Stdlib check that every `build.py` input and every script here is mentioned in this section; exits non-zero naming the gaps. |

### Data embedded by `build.py`

Each of these is a `ROOT / "..."` input. The four packed int16 blobs are decoded in the app
by `unb64()`.

| File | Role |
|---|---|
| `scene.json` | Core extract in local metres: ~2,800 buildings (h, LiDAR roof form `roof`, OPA facade attrs `fa`, roof palette `rp`), roads, areas, trees. From `process_osm.py`, patched by `lidar_core.py` and `patch_scenes_facade.py`. |
| `meta.json` | Tower-facade research + landmark heights/spires, written by hand. |
| `dem.json` / `dem_wide.json` / `dem_south.json` / `dem_city.json` / `dem_nw.json` | USGS NED 10 m elevation grids in metres ASL: core 25 m cells, wide 50 m, south 50 m, city 150 m, NW hills 50 m (border pre-feathered to dem_city). `demAbs()` samples core → nw → wide → south → city. |
| `wide.b64` | The outer districts (Center City, South Philly, NoLibs, Fishtown/Kensington + the south extension) packed int16 at 0.2 m by `pack_wide.py` (magic 0x5348545A): ~111k buildings, 9.9k road runs, 1.1k areas. |
| `city.b64` | The far ring, the rest of Philadelphia, packed at 0.7 m by `pack_city.py` (magic 0x5348545C: the roof word packs the sampled colour index with a roof form and rise, from the LiDAR pass or the OSM tag) with rowhouse rows merged into block strips: ~180k buildings, 23.6k road runs. |
| `wide_names.json` | Outer landmark names + heights for the tall-building labels. |
| `wwb.json` | Walt Whitman Bridge alignment for the custom span: one eastbound I-76 carriageway (OSM ways 424803351, 886672856, 1027616621, 123617847, 1311279172) from the Schuylkill Expressway to where the bridge tag ends in Gloucester City, so the Jersey viaduct lands at grade there. |
| `outskirts.b64` | The towns across the city line (Gloucester City, Camden's south wards, Pennsauken, Cheltenham, Springfield, plus the Navy Yard's south half): the strips of the far-ring box the older fetches never covered, packed at 1.0 m by `pack_outskirts.py` from `osm_outskirts_raw.json` (legacy magic 0x53485459, no facade attributes) and decoded by the far ring's `raiseRing()`, plus the filler: synthetic strips of houses along the streets inside residential land use (or a dense street grid) beyond the city line wherever real footprints are thin. Scenery beyond the flight limit. |
| `city_limit.json` | Philadelphia's city line (OSM relation 188022) in the model frame plus the flight limit `bound`: the line buffered 2 km, clipped to the far-ring box (`fetch_boundary.py`). The camera clamps to it in every mode and SEPTA vehicles beyond it are off the map. |
| `facade_palette.json` | 30-colour roof palette (k-means of ortho-sampled roofs), embedded as `FACADE_PAL`. |
| `street_labels.json` | Street-name placements from `bake_street_labels.py`: `names[]` + flat `[nameIdx, x, z, bearing, cls]`. |
| `street_sdf.json` | The street-name SDF atlas (4096×2244 PNG) from `bake_street_sdf.py`. Rects align by index with `street_labels.json`: always re-bake both together. |
| `trees.b64` / `tree_names.json` | PPR Tree Inventory 2025 packed by `pack_trees.py` (magic 'SHTT', 0.2 m, wide tier) + species names. |
| `places.json` | Historic-district outlines + neighborhood label points from `bake_places.py` (districts are data only since Round 30c; the names render). |
| `overpasses.json` | Elevated chains, sunken runs and the Vine Street cut from `bake_overpasses.py` (527 chains / 147 km). |
| `traffic.b64` | Drivable OSM ways + PennDOT AADT from `bake_traffic.py` (magic 0x53485454) for the typical-traffic sim. |
| `nw_parks.json` / `nw_water.json` | PPR parkland polygons (city data) and full-fidelity OSM water rings (Overpass, not city data) for the NW hills patch. |
| `poles.b64` | Streets Department street-lighting poles packed by `pack_poles.py` (magic 'SHTP', 0.7 m, ~200k). |

### Pipeline scripts

`python3 pipeline.py --graph` draws the dependency graph; the rerun orders that were learned
the hard way are in `devlog.md` (Rounds 13, 15, 23, 25, 26, 39). Scripts marked *venv* need
`requirements.txt`; the rest are plain python3.

| Script(s) | Role |
|---|---|
| `fetch_wide.py` → `osm_wide_raw.json`, `dem_wide.json` | Tiled Overpass fetch for the wide area + its DEM (`fetch_wide.log`). |
| `fetch_south.py` → `osm_south_raw.json`, `dem_south.json` | South extension: the stadium complex + the Walt Whitman Bridge (`fetch_south.log`). |
| `fetch_outskirts.py` → `osm_outskirts_raw.json`, `outskirts_tiles/` | Resumable tiled fetch of the three strips of the far-ring box across the city line: south of the Navy Yard's latitude east of −75.185, the east bank above 39.915 east of −74.990, and Montgomery County above 40.100 (`fetch_outskirts.log`). Ways only, no water or park relations. |
| `fetch_landuse.py` → `osm_landuse_raw.json`, `landuse_tiles/` | Residential, commercial, industrial and retail land use over the whole far-ring box (16 tiles, ways only) for `pack_outskirts.py`'s filler: synthetic strips of houses along the streets inside land use beyond the city line wherever OSM maps the land use but few of the buildings. |
| `fetch_parking.py` → `parking_south.json` | The sports complex's surface lots (OSM amenity=parking, 87 rings) drawn as asphalt flats by the outer-districts builder; the raw answer is cached in `lidar_cache/`. |
| `parking_south.json` | Those 87 lot rings in the model frame, flattened x,z pairs. |
| `roof_tags.py` → `lidar_cache/roof_shapes.json` | OSM `roof:shape` tags from the three raw dumps (33k ways: flat, gabled, hipped, gambrel, saltbox, mansard) plus the centroid of every wide and south building way, so `pack_wide.py` can attach way ids to scene buildings. |
| `fetch_lidar_roofs.py` → `lidar_city_roofs.json`, `lidar_cache/roof_tiles/` | Citywide roof forms (flat, gable, hip with eave, ridge and ridge angle) streamed at coarse resolution from the 752 NOAA 2022 COPC tiles over HTTP, one JSON per tile, merged with `--merge`; resumable, hours for the whole city. |
| `fetch_overture.py` → `lidar_cache/overture_phl.json` | Overture Maps buildings over the far-ring box through DuckDB (heights, roof shape, facade material by OSM way id). Checked 2026-09-02: its roof and colour attributes are OSM's own tags re-exported, so it adds nothing beyond `roof_tags.py`. |
| `fetch_shops.py` → `lidar_cache/shops_raw.json`, `lidar_cache/shop_tiles/` | OSM shops, cafes, bars, banks, pharmacies and the rest (nodes and ways) over the wide and south boxes, with a small kind code. |
| `bake_storefronts.py` → `storefronts.b64` | Each business on the facade edge of its building that faces the street (line of sight, sidewalk depth, tie-break by the door): 8 int16 per storefront (magic 0x53485446): position, outward angle, width, kind, colour, floor height, flags for awning, sign and glass. `storefronts.json` beside it is the same for inspection and does not ship. |
| `fetch_mapillary.py` → `lidar_cache/mly_tiles/`, `lidar_cache/mly_thumbs/`, `lidar_cache/mly_images.json` | Mapillary street-level thumbnails over the wide and south boxes (CC BY-SA; needs `MAPILLARY_TOKEN`, a free client token from mapillary.com/dashboard/developers). Lists images from the z14 vector tiles with a stdlib protobuf reader (the Graph API bbox search fails whole neighbourhoods with "reduce the amount of data"), picks the newest per 10 m cell up to `--max-images`, resolves thumbnail URLs 50 ids at a time; `--dry-run` synthesises a test set. |
| `bake_wall_colors.py` → `wall_palette.json`, `wall_colors.json` | Wall colour per block face from the thumbnails (median of the flanking bands, sky, road and foliage discarded), quantised to a 32-colour palette and assigned per scene building, with a per-face light and dark pixel fraction classed into the trim and window hints (`wide_hint`, `south_hint`). `pack_wide.py` turns the pair into `wide_walls.b64`; a dry-run pair is ignored. Both jsons are gitignored, the blob is committed. |
| `storefronts.b64` | The baked storefronts, decoded by the app's "Dressing the storefronts" step into glazed fronts, awnings and signboards that glow after dark. |
| `bake_towers.py` → `towers.json` | The researched Center City towers (`wide_landmarks_research.json`, `wide_names.json`) as one spec each: joined to the wide footprint or part name-first (IDF-weighted tokens), then by a scored position match, height, sRGB tint, a facade archetype (glass, glass with bands, dark glass, precast grid, stone piers, pre-war stone, precast bands, brick) from the research text and an override table, a crown (pyramid, lattice, ziggurat, lantern, notch, spire, mansard, dome) and a night accent colour. |
| `towers.json` | The tower specs, inlined as `TOWERS`; "Raising the outer districts" joins each tower over 45 m to the nearest spec within its radius, gives it the archetype's facade style and tint (glass ones go to the reflective curtain wall with a band variant) and raises the crown above a body stopped short of the researched height. |
| `bake_schuylkill.py` → `schuylkill.json`, `lidar_cache/schuylkill_ways.json`, `lidar_cache/schuylkill_outline_raw.json` | The Schuylkill's real course and outline: the OSM `waterway=river` ways named Schuylkill over the city and the `natural=water` river multipolygons around them (two cached Overpass queries), the ways simplified to 3 m as `lines`, the outline faces the waterway threads united with a 60 m buffer of the ways and clipped to the modelled reach as `polys` (rings with island holes). The hand polyline in app.js is the fallback. |
| `schuylkill.json` | Inlined as `SCHUYLKILL_DATA`: `riverCarve` takes the ground inside `polys` to the bed and ramps a high bank down within 40 m outside (a 10 m scanline raster for inside/outside, a 20 m edge grid for the distance), `riverCorridor` reads the same raster, and "Raising the rest of Philadelphia" draws the polygons flat at the river level, so the shoreline is the outline and not the ground grid. `lines` remain the centreline fallback. |
| `wide_walls.b64` | The Mapillary wall colours and facade hints for the outer districts (magic 0x53485457): the 32-entry sRGB palette, then one palette-index byte per `wide.b64` building record, then one facade hint byte per building from the same block face (the fourth header word is the bytes per record, 2; 0 was the one-byte layout), trim class in bits 0-1 and window class in bits 2-3 (the fraction of the kept pixels that are light or dark in the imagery, classed by `bake_wall_colors.py`), 0 for a building without a colour. Decoded beside `wide.b64` by "Raising the outer districts": a building the imagery has seen takes its block face's colour instead of a palette draw, and the hint steers `fabricStyle` (siding, cornices, dark trim, new construction). |
| `fetch_boundary.py` → `city_limit.json` | *venv.* The city line from OSM relation 188022, buffered 2 km into the flight limit; the raw relation is cached in `lidar_cache/phila_boundary_raw.json`. |
| `fetch_city.py` → `osm_city_raw.json`, `dem_city.json`, `city_tiles/` | Resumable tiled fetch of the rest of the city: boxes A–D plus `river-wards` (Round 36) and `nw-gap` (Round 40) (`fetch_city.log`). |
| `fetch_dem_nw.py` → `dem_nw.json` | 50 m NED over the NW hills, border pre-feathered to dem_city. |
| `process_osm.py` | Raw Overpass JSON → a scene json in local metres. `SHT_DIR` / `SHT_RAW` / `SHT_OUT` env vars pick the folder, input and output; it produced `scene.json`, `scene_wide.json` and `scene_south.json` (`process_wide.log`, `process_south.log`). Normalises outer rings CCW (`ensure_ccw`). |
| `scene_wide.json` (21 MB), `scene_south.json`, `parts_wide.json` | The wide / south extracts and the OSM `building:part` skyscraper pieces: inputs to `pack_wide.py`. `report_wide.json` / `report_south.json` are their process summaries (counts, bounds, the towers' OBBs). |
| `pack_wide.py` → `wide.b64` | Packs scene_wide + scene_south + parts_wide; drops anything *touching* the core (`touchesCore`), `simplify_open` for roads, `BRIDGE_SKIP` handled in the app.  Stacked building:part ways on one footprint (centroids within 2.5 m, areas within 20 %, overlapping heights) keep only the tallest, since coincident prisms z-fight. |
| `pack_city.py` → `city.b64` | *venv.* Packs `osm_city_raw.json` with shapely block-strip merging; requires `lidar_city_heights.json`. |
| `pack_outskirts.py` → `outskirts.b64` | *venv.* Packs `osm_outskirts_raw.json` at 1.0 m with a 3 m row bridge (detached houses fuse into rows); skips anything an older fetch box owns; no LiDAR / OPA / roof join. |
| `fetch_footprints.py`, `lidar_join.py`, `lidar_core.py` | The 2022-LiDAR true-massing pass (Round 13): the City's footprint layer with LiDAR `max_hgt` → `lidar_cache/phl_footprints_local.json`; `lidar_join.py` (*venv*) patches the scene jsons in place and emits `lidar_city_heights.json`; `lidar_core.py` (*venv*) derives core roof forms from the COPC point cloud. |
| `lidar_city_heights.json` | `{OSM way id: measured h}` for the far ring; `pack_city.py` requires it. |
| `lidar_report.json` | LiDAR pass validation: coverage, histograms, known truths, top deltas. |
| `fetch_opa.py`, `opa_join.py`, `roof_colors.py`, `patch_scenes_facade.py` | Tier-1 facade pass (Round 15): OPA parcel table → per-building use / material / era / stories; ortho-sampled roof colours → `facade_palette.json`; both written into the scene files as `fa` / `rp`. `opa_join` and `roof_colors` are *venv*. |
| `fetch_trees.py` / `pack_trees.py` | PPR tree inventory → `trees.b64` + `tree_names.json`. |
| `fetch_poles.py` / `pack_poles.py` | Streets Department poles → `poles.b64`. |
| `fetch_places.py` / `bake_places.py` | Historic districts + neighborhoods → `places.json`. |
| `fetch_traffic.py` / `bake_traffic.py` | PennDOT RMSTRAFFIC → `traffic.b64` (conflated onto the raw OSM drivable ways). |
| `fetch_nw_parks.py` / `fetch_nw_water.py` | PPR parkland + water rings for the NW patch. |
| `bake_street_labels.py` → `bake_street_sdf.py` | Street-name placements from the three scene jsons, then the SDF atlas (*venv*: Pillow + numpy). Rerun both whenever a scene json is refetched. |
| `bake_overpasses.py` | Raw dumps + DEMs → `overpasses.json` (plain py3, ~1 min). Re-bake whenever the raw dumps or a DEM change. |

### Research and reports

| File | Role |
|---|---|
| `realism_research.json` | Landmark appearance research (colours, dimensions, roof forms, sources). |
| `headhouse_blocks_research.json` | Abbotts Square / 410 S Front / New Market: OPA parcels + LiDAR massing in local coords. |
| `fenestration_research.json` | Facade vocabulary (sash sizes, bay pitches, church tiers, storefronts) behind the shader styles. |
| `wide_landmarks_research.json` | Outer landmark heights/massing for ~150 buildings. |
| `south_geometry_research.json` | Stadium complex + WWB geometry notes, incl. the local-frame formula. |
| `geo_audit.json` | 35 geography gaps with lat/lon, fixes and priorities: the realism to-do list. |
| `../.audit/` | The Round 27 audit scripts (decode `wide.b64` / `city.b64` independently of the app). |

## Build & preview

```bash
cd 3d-model
python3 build.py                         # -> society-hill-towers.html (per-blob size table)
python3 -m http.server 8917              # open http://localhost:8917/society-hill-towers.html
python3 -m unittest discover -s tests    # the test suite
python3 pipeline.py --graph              # the data pipeline as a graph
python3 docs_check.py                    # every build input / script is documented above
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # pipeline deps only
```

- No toolchain: plain Python 3 assembles the page, and the build itself is stdlib-only. The
  pipeline scripts marked *venv* above need `requirements.txt` (shapely, numpy, pyproj,
  laspy[lazrs], Pillow).
- `build.py` guards: it aborts if an input is missing or suspiciously small (`--allow-missing`
  builds without it, for a deliberately blob-less test page), if any `{{PLACEHOLDER}}`
  survives, if any embedded blob contains `</script`, or if the page exceeds 25 MB. It prints
  a size table per blob so a regression is visible at build time.
- **Byte-planar blobs:** since 2026-09-01 the four int16 blobs (wide, city, trees, poles) are
  stored in the page byte-planar (all low bytes, then all high bytes) and `unb64()` in app.js
  re-interleaves them on decode. That is what took the gzip from 12.76 to 9.77 MB. The `.b64`
  files on disk and the `pack_*.py` formats are unchanged; only the page's copy is shuffled.
- **Laptop caveat:** the Browser pane's dev-server python cannot `getcwd()` inside
  CloudStorage (TCC), so serve the built page from a scratch copy (the `sht-*-scratch` entries
  in `.claude/launch.json` do exactly this), not from the checkout. Also: this checkout's files
  are mode 600, which is why `deploy_philly3d.sh` chmods its staging copy.
- **URL flags** (all off by default):
  - `?dev=1` exposes `window.__dbg` (`orbit, walk, fly, camera, renderer, scene, WX, WXFX,
    wxSurfU, waterU`, `wx('storm')`, `bolt()`, `flightTest()`, `shipTest()`, `ships()`,
    `flights()`, `indego()`, `traffic()`, `frameOnce()`, `goWalk(x,z,yaw)`,
    `goFly(x,y,z,yaw,pitch)`) plus `__dbg.perf()` (per-step build timings, frame-time
    p50/p95, `renderer.info`, heap) and a small on-screen perf readout.
  - `?dpr=N` pins the adaptive pixel ratio (default: adaptive, capped 1.75 desktop / 1.5 touch).
  - `?wx=clear|overcast|fog|drizzle|rain|downpour|storm|hail|snow|blizzard|sleet` pins the
    weather (the live Open-Meteo fetch is skipped).
  - `?logdepth=0` is the depth-buffer escape hatch (logarithmic depth is on everywhere).
- **Deploy:** `./deploy_philly3d.sh` ships philly3d.com; `git push` ships GitHub Pages. To
  check Pages is live, grep the *whole* page or its tail: app.js sits after ~20 MB of data,
  so a first-120 KB range check always reports stale.
- **Headless verification:** the pane runs no rAF even when fronted. Drive frames with
  `__dbg.frameOnce()` bursts, render twice before a capture (screenshots lag one presented
  frame), and dispatch synthetic pointer events as down *and* up on the canvas.

## Architecture (app.js)

One IIFE, top to bottom, with `// ------- banner` comments you can grep for. In order:
`config` (TOWER, COLORS) → `dom` → `helpers` → `lighting & sky` → `data-driven build` →
`overpasses` → `living water` → `terrain` → `ground, water, roads, parks` → `the city fabric`
→ `landmark spires` → `researched landmark models` → `museum ships` → `the three towers` →
`the outer districts` → `the far ring: the rest of Philadelphia` → `trees` / `street trees`
→ `labels` → `controls` → `modes & viewpoints` → `live SEPTA transit` → `layers panel` →
`street names` → `places` → `address search` → `live Indego bike share` → `live flights` →
`live ships` → `traffic` → `streetlights` → `solar clock` (and the weather) → `build & loop`.

- **Coordinates:** x = east, z = south, y = up, metres. Origin = centroid of the three towers
  (39.94547°N, 75.14475°W; `x = (lon − lon0)·111320·cos(lat0)`, `z = −(lat − lat0)·110574`).
  Every scene json and every hard-coded position uses this frame; City Hall is at
  (−1603, −802). The street grid is ~10° off the axes: never use world x for "the Front St
  line", use the fitted line `fl` / `ryG`.
- **Load pipeline:** `step(msg, fn)` pushes onto `buildSteps[]`; `build()` runs them in order
  (each try/caught, the veil's Enter button enables at the end). The steps: Laying out the
  ground → Shaping the waterfront → Paving the streets → Planting parks and piers → Raising
  2,800 buildings → Setting the steeples → Restoring the landmarks → Mooring the ships →
  Casting the concrete grid (the towers) → Raising the outer districts (`wide.b64`) →
  Raising the rest of Philadelphia (`city.b64`) → Raising the towns across the line (`outskirts.b64`) → Raising the overpasses → Planting the
  street trees → Lettering the landmarks → Lettering the streets → Naming the neighborhoods
  → Raising the Frankford El → Rolling out the SEPTA fleet → Docking the Indego bikes →
  Charting the viewpoints → Setting the traffic flowing → Lighting the streetlamps →
  Lighting the skyline. The two decode steps yield via a MessageChannel ping (setTimeout is
  clamped in hidden tabs) and render once behind the veil so uploads + frees happen during
  build.
- **Three tiers of fabric.** Core: every `scene.json` footprint extruded (`buildingGeom`,
  facade-local `aWallU/L/H`), merged into one vertex-coloured mesh on `cityMat`, small quads
  get footprint-fitted gables/hips (`quadGable`/`quadHip`, LiDAR-measured forms bypass the
  lottery). Wide: `WIDE_B64` decoded into lean indexed 700 m chunks (8-bit normals/colours)
  sharing `cityMat`, plus outer roads, parks/water, the Ben Franklin Bridge, tall labels.
  Far ring: `CITY_B64` into 2,400 m chunks, 100 m ground strips, far roads, district labels.
  **All three load on phones** (Round 7 removed the old touch skip); touch instead keeps DPR
  ≤ 1.5, 2048 shadow maps, half the wide forest, no pole meshes and no deck shadows.
  `freeOnUpload()` nulls the chunk arrays after GPU upload (they are never raycast), and the
  big `let` blobs are nulled after decode (Round 28's memory diet).
- **Facade shader:** `cityMat.onBeforeCompile` draws windows, lintels, shutters, doors in world
  space per `aStyle` (0 Georgian rowhouse, 1 church, 2 modern slab, 3 blank, 4 civic arched
  base, 5 storefront, 6 modern over double-height retail, 7 balcony-band slab, 8 post-1935
  rowhouse without shutters, 10 glass tower), `aFloorH` true floor pitch from OPA stories,
  masks AA'd with `fwidth` and faded with distance; `shtLit` lights ~1/3 of windows at night
  via `nightUniform`. Outer glass towers use `outerGlassMat`'s curtain-wall shader and
  `GLASS_TINTS`. Colours are stored for the r149 legacy pipeline (dark: ACES + noon sun lift
  flats ~2.5×; roof colours pass through the `roofInv` power curve).
- **The towers:** fully procedural from `TOWER` in "Casting the concrete grid": 18×12 bays on
  a 6 ft module, 0.42 m mullions, deep-set glass, colonnade every 3rd grid line, 94.2 m
  (CTBUH 309 ft; OSM says 89).
- **Landmarks:** `REALISM` (exact OSM names) and `REALISM_NEAR` (centroid + area matches for
  unnamed footprints) mark buildings `custom` (rebuilt in "Restoring the landmarks") or
  `recolor`; City Hall, the Liberty Places, the Art Museum, the stadiums, the Custom House,
  Independence Hall, Glory, Rotten Ralph's, the Battleship New Jersey and more are hand-built.
  `BRIDGE_SKIP` drops OSM footprints that are really bridge towers or custom-built landmarks.
- **Terrain:** `demAbs()` samples the DEM grids (datum: the towers' site at 8.34 m ASL stays
  y = 0); `siteY(x,z,'ground'|'road')` is the one function everything sits on. East of Front
  St the I-95 trench drops to −8 between `TERRAIN.trenchW/E`, Penn's Landing shelf −6.5…−7.5,
  water −10, shoreline = `SHORE`, caps in `CAPS`. Outside the core low terrain clamps above
  the water plane except east of `DEL_BANK` / inside `riverCorridor` (Schuylkill polyline).
  Each packed ring pre-scans its own water polygons (`wxWaterGrid`) and refuses any footprint
  whose centroid stands in rendered water, so nothing floats.
- **Overpasses:** `OVERPASSES` (bake_overpasses.py) drives deck ribbons, parapets, piers, the
  Vine Street cut and sunken ramps; `ovpOwned` suppresses the packed flat ribbons underneath,
  `ovpDeckY` lifts buses, labels and traffic; `BRIDGE_DECKS` registers the two custom river
  spans' real deck profiles.
- **Layering (z-fighting):** flat surfaces use the `LAYER` constants (park .06 / plaza .10 /
  sidewalk .16 / road .24 / footway .32 / pools .38), every ribbon gets a deterministic few-cm
  lift, and the renderer runs with `logarithmicDepthBuffer: true` everywhere. Never add
  coplanar flat geometry without picking a layer, and never use polygonOffset on the flats.
- **Navigation:** fly-only since Round 35. Orbit survives only as the attract loop (the veil
  and the post-Enter glide down to City Hall); the first pointer/wheel/touch/key hands control
  to fly (`autoFly`): WASD, E/Q or Space/C, shift boost, scroll sets cruise speed, clamped
  above terrain via `siteY`; touch gets a throttle joystick + ▲▼ buttons and a first-time
  tips card. Walk is reachable only through `__dbg.goWalk`. Pointer lock has a drag-look
  fallback that must stay functional.
- **Layers panel (F):** SEPTA vehicles (V; JSONP polls of TransitViewAll, street-snapped,
  badge billboards on every vehicle), Indego (B), flights (X; adsb.fi through
  `FLIGHT_PROXY = https://philly3d.com/adsb`), ships (H; aisstream.io WebSocket, key in
  `AIS_KEY`, one client per key), typical traffic (R; PennDOT AADT simulated on a road graph,
  camera-weighted budget), streetlights (G), street names (N; SDF atlas), landmark labels
  (L; **off by default by owner decision**, the citywide tier lives behind this key),
  neighborhood names (P). Address / route search on `/`. Every live layer is silent when
  its feed is unreachable and says so in the row title.
- **Picking:** tap/click raycasts the instanced fleets, pins and badges, with a screen-space
  nearest fallback; `pickOccluded` gates hits with a raycast against `rayTargets` (core
  meshes, ground, decks) and then a DEM march along the sight line (never raycast the outer
  chunks: their arrays are freed).
- **Solar clock and sky:** `solar()` (NOAA) + `lunar()` (Schlyter, epoch 2000 Jan 0.0), `clock`
  in Philadelphia local time, `applyLighting()` every frame drives sun, sky palette (`PAL`),
  fog (`fogBase` scaled by weather), hemisphere, exposure, `nightUniform`, ground retints,
  and `refreshEnv()` re-bakes the PMREM environment when the sun moves > 3°. The T panel has
  date, slider, presets and live mode.
- **Weather:** Open-Meteo current conditions every 15 min → `WX` → `wxSetTargets` eases
  `WXFX` strengths (rain, snow, hail, fog, gloom, wet, accumulation). Two camera-following
  particle boxes render precipitation, bolts spawn in storms, `wxSurfacePatch` lays snow/wet
  on every static MeshStandardMaterial, `wxGroundPatch` mottles the bare-ground planes.
  `WX` must be declared before the sky material (TDZ).
- **Street names:** `ST_LABELS` + `ST_SDF` → one indexed quad mesh draped column by column on
  the road profile, alpha from an SDF threshold (RedFormat DataTexture; LuminanceFormat is
  rejected by WebGL2).

### Added in Round 46 (Sep 1, the optimisation audit)

- **Load path:** the packed int16 blobs are stored byte-planar by build.py (`B64_PLANAR` const) and
  re-interleaved by one `unb64()`; the two ring decoders stage into `VBuf`/`IdxBuf` typed
  accumulators, seal chunks at 60k vertices and hand them to `addChunkMesh` / `flushUploads`
  (every new ring mesh draws unculled once so it uploads and frees). `ovpNear` is a 32 m bitmap
  that pre-tests footprints against the deck swaths. `yieldNow` (MessageChannel) is the only
  yield between build steps.
- **Runtime:** `renderer.shadowMap.autoUpdate` is off; `aimSun` requests a redraw when the box
  or the sun moves and `frame()` refreshes every 4th frame while vehicles move. `cullFogged`
  hides outer meshes beyond `fog.far` (view depth). `DPR` adapts the pixel ratio to frame time
  between 0.9 and the display's own ratio (`?dpr=N` pins). `flushInst(m, colorFrom)` is the
  one InstancedMesh upload helper. `PERF`/`__dbg.perf()` and the `?dev` readout carry per-step
  timings and frame p50/p95; `beacon()` posts checkpoints to `/b` on philly3d.com only.
- **Feeds:** `septaFetchBaked` reads `/septa.json` (ops/septa_bake.py) before the JSONP rotation;
  `shipRelayPoll`/`shipUpsertRelay` read `/ais.json` (ops/ais_relay.py) and only fall back to the
  direct aisstream socket while the relay is missing or stale (90 s / 60 s gates).
- **UI:** prefs persist under localStorage `philly3d.prefs` (seeded before `build()`; hash wins);
  the share hash is `#p=x,y,z,yaw,pitch&t=YYYYMMDD,minutes&l=<bitmask>` (bits: 1 SEPTA, 2 Indego,
  4 flights, 8 ships, 16 traffic, 32 lights, 64 streets, 128 labels, 256 places), written by
  `updateHash` from `frame()`; `openPanel`/`closePanels` keep one bottom panel open (Escape and a
  short canvas tap close them); the layers panel ends with 'Take me to' stops (`STOPS`, the glide
  tween `glideFly`/`stepGlide` polled from `frame()`) and 'Tour the City'; `btnShot` captures the
  GL canvas; the time panel's Play runs the sun time-lapse (`setLapse`, PMREM rebake gated by
  `envGap`); the compass is a button (`faceNorth`); a bus-route search sets `SEPTA.filter`
  (chip in `#searchOut`, status 'N of M on route R'); `searchLocal` matches the in-page name
  index (landmarks, neighborhoods, districts, named buildings, streets) before Nominatim.
- **Weather sources (Round 46 coda):** Open-Meteo `current` (cloud, precipitation, WMO code, wind,
  temperature; every 15 min) drives everything, but its code is a model estimate and rarely says
  95 while it is actually thundering, so `fetchNws()` (every 5 min) also reads the NWS: the latest
  observation at KPHL and KPNE (`presentWeather` TS / "Thunder" within 75 min) and the active
  alerts for the site. `WXFX.storm` is true for a WMO 95 to 99 code, observed thunder, a Severe
  Thunderstorm or Tornado Warning, or a Severe Thunderstorm Watch while it is raining; the bolt
  cadence is `WXFX.boltGap` (thick under a warning or observed thunder, sparse under a watch). NWS
  facts expire after 20 min. Rain streaks are 4.5 to 10 m, fall faster with altitude, and fade out
  between 350 and 1000 m up (the fog and gloom carry rain from higher). The sun disc and halo set
  with the horizon (`uSunVis`, gone below -1.1 deg) and a 60 km ground apron under the world
  (`TERRAIN.bed - 8`, `farGroundMat`) ends the city in fog instead of a diagonal against the sky
  dome. A SEPTA vehicle with no drawn street within 140 m (`v.off`, set by the road snap) is
  neither drawn nor counted: it is out past the modeled city.
- **Real lightning:** `ops/lightning_relay.py` (one MQTT subscription to the Blitzortung community
  relay, geohash topics `d/r` and `d/q`) writes `lightning.json` every 2 s with every strike inside
  110 km for 15 min; the page's `ltnPoll` reads it every 4 s (`LTN` state, `__dbg.lightning()`),
  queues new strikes within 80 km (50 miles) and `spawnStrike` draws each at its real position,
  pulled in to the 55 km apron edge along its bearing when farther; the flash scales with distance
  (floor 0.14). Three or more strikes within 40 km in ten minutes put the page in storm mode without
  forcing rain. While the feed is live the synthetic bolts stand down; without it they return.
  The readout appends "N strikes in 10 min, nearest X mi". `__dbg.strike(lat, lon)` injects one.
- **Visual constants to tune by eye:** `LANDMARK_H` (wide-ring landmark heights and spires from
  `wide_landmarks_research.json`), `RING_AO = 0.78` (bottom-vertex darkening of ring walls; 1.0
  disables), `SKY_DITHER = 1/255` and `MAT_DITHER` (banding), `anisoOf(n)` (texture anisotropy
  clamped to the hardware cap).

## Hard-won gotchas (do not relearn these)

1. **OBB frame handedness:** for any frame built from a 2D axis `(ax,az)` in this y-up
   world, the perpendicular must be `(az,-ax)`. Using `(-az,ax)` makes winding depend on
   the source polygon's direction → half your roofs get backface-culled (invisible).
2. **Sandboxed viewers:** pointer lock may be denied → the drag-look fallback must stay
   functional; `target=_blank` links may be dead; a walled-off origin gets the fair-weather
   default and no live layers (that was the artifact; it still applies to any CSP'd embed).
3. **build.py guards:** it aborts if any embedded blob contains `</script`, if a placeholder
   survives, if an input is missing/undersized, or if the page passes 25 MB. Keep it that way.
4. **OSM data quirks already corrected in code:** Marriott Old City tagged `height=4`
   (real ~16.5, overridden); Hopkinson House tagged 107 m (two sources say ~92, overridden);
   Independence Place twins kept at OSM's 96.9 m (agents disagreed: 25 vs 36 floors); the
   Custom House, Hilton, Independence Hall, Old City Hall (tagged 3.2 m!) and the museum ships
   all carried OSM's 13 m default and are rebuilt in code; swimming pools needed a separate
   Overpass query (`leisure=swimming_pool`) — the towers' pool + Delancey pool are hardcoded in
   the ground step with real OSM geometry. Both bridges' towers/anchorages are mapped as
   building footprints (`BRIDGE_SKIP`).
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
   few-cm lift (hash of its first point) so nothing is ever exactly coplanar. Duplicate
   dropping between rings must require *parallel* alignment (`nearRoadAligned`) or crossings
   vanish.
7. **Roofs must be built on the footprint, not the OBB.** `quadGable()` fits the gable to the
   (simplified, 4-vertex) footprint quad itself — eaves and gable ends meet the walls at every
   vertex. OBB roofs float beside skewed footprints (the grid is rotated ~10°). The quad must
   also be honest: convex, near-rectangular, elongated, area-matched, else extrude flat.
8. **Glass:** `refreshEnv()` re-bakes the PMREM environment (sky + sun ball + dark silhouettes)
   whenever the sun moves >3°; glass towers flagged from research render as type 10 with a
   reflective material; style 7 is the balcony-band slab (Dockside, Hopkinson).
9. **rAF is throttled** in headless/hidden tabs and the Browser pane runs none at all — don't
   trust FPS probes there; use `renderer.info` / `__dbg.perf()` and `__dbg.frameOnce()`.
10. **Never orient earcut output by the input ring's winding.**
    `THREE.ShapeUtils.triangulateShape` emits triangles in a canonical orientation (CCW in
    the shape plane) regardless of the ring's direction. Flipping caps when
    `ShapeUtils.area(v2) > 0` culled every roof on a CW ring: `process_osm.py` normalises
    rings CCW so the core and wide sets never showed it, but `pack_city.py` emits shapely
    output raw and GEOS buffers produce CW shells, so the whole far ring stood as hollow
    cardboard (Round 4). Caps always emit earcut's triangles forward; the wall quads are
    fine because their normal and winding key off the same signed-area sign.
11. **Three.js is pinned at r149 on purpose.** app.js sets `renderer.outputEncoding =
    THREE.sRGBEncoding` and `tex.encoding = THREE.sRGBEncoding` on every canvas texture;
    both were removed in r152+ (`outputColorSpace` / `ColorManagement`). More importantly,
    ~250 colour constants (`COLORS`, the facade palettes, `palTall`, `glassPal`, stored-dark
    roofs and grounds, the `roofInv` curve) are tuned by rendered swatch to the *legacy*
    colour pipeline (no sRGB→linear on input, ACES + exposure 1.06). An upgrade needs
    `THREE.ColorManagement.enabled = false`, `renderer.outputColorSpace = THREE.SRGBColorSpace`,
    the texture `colorSpace` renames, the onBeforeCompile chunk names re-checked, and then a
    pixel A/B of the whole city at noon and at night. Do not bump the vendored file casually.
12. **A frustum-culled mesh never uploads and never frees its arrays.** `freeOnUpload` hooks
    `BufferAttribute.onUpload`, which fires only when the renderer actually uploads the
    geometry, and a mesh outside the frustum is never uploaded. A chunk that is culled during
    the behind-the-veil renders keeps its full CPU arrays until the first frame that shows it,
    so the "memory diet" is only real for what those renders see; anything that must be freed
    at build time needs `frustumCulled = false` for that render (or an explicit upload), and
    anything that must stay raycastable must never go through `freeOnUpload` at all (Round
    41's tooltip kill was a raycast into a freed chunk).

More rules the log paid for (details in `devlog.md`):

- **No em dashes or middot separators in any user-facing string** (Mike's rule): veil, hints,
  cards, panel text, loading messages, tooltips. Commas, colons, sentences. Code comments and
  these docs are exempt.
- `WX` must be declared before the sky material (`refreshEnv` reads it during init, TDZ crash).
- Custom shaders that use the logdepthbuf chunks need `#include <common>` for
  `isPerspectiveMatrix` or the program dies silently and the mesh never draws.
- Never compute tight highlights on unnormalised interpolated directions over a coarse dome
  (the streaked sun); normalise per fragment.
- Colour variation must live in hue + saturation, not lightness (the day pipeline flattens
  lightness); pick flat-surface colours by rendered swatch; calibrate stored colours against a
  measured transfer curve, not a guessed divisor.
- InstancedMesh: `frustumCulled = false` (instance bounds don't follow the fleet); never bake a
  rotation into a part that gets non-uniform instance scale; every mesh sharing
  `septaMats.body` must `setColorAt` (uninitialised instance colour reads black); a shared
  program expects instance colours.
- Sin-dot lattice hashes streak into worms on integer cell ids; use a fract-cascade hash.
- Never drape a big lawn over roads on a bumpy hill; recolour the ground instead.
- SEPTA: no CORS, JSONP only; subway rows are schedule placeholders (no real L/B GPS exists).
  Flights: no ADS-B API speaks CORS; the VPS `/adsb` proxy is the transport. Ships: aisstream
  sends binary frames (`ws.binaryType = 'arraybuffer'`), one client per key, release the
  socket when hidden. Nominatim results are filtered to "Philadelphia".
- Marker visibility is a per-family owner decision: SEPTA/Indego markers are occluded by
  buildings, neighborhood names and the search pin are not. Ask which family before flipping.
- Deploy: stage + `chmod 644` before rsync (CloudStorage files are 0600 → site-wide 403);
  the nginx `/adsb` upstream must resolve at request time (`resolver … ipv6=off` + a
  variable `proxy_pass`) or an upgrade-time DNS blip keeps nginx from starting at all.
- Testing harness: synthetic PointerEvents need down *and* up on the canvas; setPointerCapture
  throws on fake pointerIds (cosmetic); layer fades run on wall time; render twice before a
  capture; close preview tabs so they don't hold the AIS key.

## State

As of 2026-09-01 both homes serve the Round 45 coda build: weather lands on every surface
(snow settles on roofs, roads and lawns; rain darkens and sheens the streets), the bare
ground reads as mottled lawn and scrub instead of perpetual snow, overcast dims honestly,
no footprint floats in rendered water, every SEPTA vehicle wears the badge billboard, the
battleship stands at her Camden berth, bridge traffic rides the real decks, and 43 citywide
landmark labels wait behind the L key (off by default). Today's batch on top of that:
`build.py` hardening and the byte-planar blob store (9.77 MB gzip), `?dpr=N`, `__dbg.perf()`
and the on-screen readout, the bottom credit line naming every source with a "credits" link,
`3d-model/tests`, `pipeline.py`, `requirements.txt`, `docs_check.py`, and this document split.
Known open items: Tier 2 (parametric storefronts from OSM shop names) and Tier 3 (photo-built
fronts) of the facade plan; a `lidar_join` pass for the nw-gap wards (they ride tag/default
heights); leafless winter trees; thunder audio (no audio system exists); a NJ bank polyline
for the residual NED shelf south of the WWB; the Penrose/PA-291 twin-carriageway grades; a
touch LOD for the far ring if phones still die (needs Mike's sign-off); and everything in
`geo_audit.json` and the wide-area backlog. **The full round-by-round log (every decision,
reversal, measurement and rerun order, Rounds 1–45 plus the VPS incident) is in
`devlog.md`; read the entry for whatever you are about to touch before changing it.**

Data © OpenStreetMap contributors (ODbL) — the OSM credit link must stay in the page. It
lives in the bottom credit line (`#osmcredit`, which now names every source and opens the
credits) and in the hidden About panel; see `DATA-LICENSE.md` for every source's terms.
