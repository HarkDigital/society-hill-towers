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
| `template.html` | Page shell: a real document head (title, description, canonical, OG/Twitter card, inlined favicons), the veil, bar, panels, the bottom credit line, and the `{{CSS}} {{DATA}} {{THREE}} {{REBUILDS}} {{APP}} {{ABOUT_BODY}} {{FAVICON_SVG_B64}} {{FAVICON_32_B64}} {{APPLE_ICON_B64}}` placeholders. |
| `privacy.html` | The privacy policy (Round 164), served at https://philly3d.com/privacy.html by `deploy_philly3d.sh` (which checks the live copy) and linked from the About panel (`#aboutPrivacy`). It covers the site and the apps: Google Analytics runs on the website only (`GA_ID` and `ON_SITE` in app.js), Search Console, the load beacon, location on the device. Change the date at the top with any change. |
| `app.js` | All application code (~22,800 lines, one IIFE). Everything interesting is here; see Architecture. |
| `rebuilds/_kit.js`, `rebuilds/<id>.js` | The landmark rebuilds (Round 161): the modelling kit (`RB.kit(THREE)`: frames, boxes, extrusions, roofs, pediments, columns and colonnades, window grids, crenellations, canvas signs, per-material merge; `K.mat` takes a photo colour and stores it for the legacy pipeline, calibrated on the Museum of Art's Kasota stone) and one file per rebuilt building (`t30` 30th Street Station, `ww` the Fairmount Water Works, `esp` Eastern State Penitentiary, `dl` the Divine Lorraine, `gc` Founder's Hall, `rtm` the Reading Terminal, `shot` the Sparks Shot Tower), each `RB.add({ id, name, center, skip, views, build(api) })`. `build.py` inlines them as one script ahead of `app.js`; the wide loop skips the generic footprints under each `skip` ring and 'Rebuilding the landmarks' builds them through a small api (see Architecture's rebuild note in devlog Round 161). |
| `style.css` | HUD chrome plus the embedded Montserrat faces (base64 woff2, OFL). |
| `about_body.html` | About panel prose, key table and credits. The panel is hidden by owner decision (since Round 22; `btnAbout` display:none, `i` unbound, code intact). |
| `three.min.js` | Three.js **r149** UMD, inlined at build. Pinned: see gotcha 11 before upgrading. |
| `build.py` | Assembles the page (stdlib only). `SHT_BUILD_OUT=<path>` writes the page and its manifest elsewhere (a scratch test build), `SHT_REBUILDS=t30,gc` (or `none`) keeps only those rebuilds. Refuses to ship a missing or undersized input (`--allow-missing` overrides), prints a per-blob size table, and aborts on a leftover `{{PLACEHOLDER}}`, `</script` inside any blob, or a page over 25 MB. Stores the int16 blobs byte-planar (see Build). |
| `deploy_philly3d.sh` | One-command ship to philly3d.com: build, refuse a proxyless or unbranded build, stage the eight files (the page as index.html, four brand files, `manifest.webmanifest`, `sw.js`) + `chmod 644`, `gzip -k9`, rsync. |
| `manifest.webmanifest` | The installable app's manifest, written by `build.py` beside the page (Round 53): name, `start_url` and `scope` `./`, standalone display, ink theme and background, the three icons as data URLs. Linked from the template by relative href, so it serves at philly3d.com/ and under Pages' `3d-model/`. |
| `sw.js` | The network-only service worker (Round 53): its real fetch handler is what lets Chrome and Edge offer Install. Caches nothing (the page is rebuilt every deploy). Registered by `app.js` over https only. |
| `index.html` | Pages' redirect to the page, so the manifest's `start_url` `./` resolves there too (on the VPS the page itself is index.html). |
| `flight-proxy-worker.js` | Fallback recipe: a ~30-line personal Cloudflare Workers / Deno passthrough for adsb.fi, for the day the VPS `/adsb` proxy goes away. |
| `brand/` | Identity: `mark.svg`, `favicon.svg`, `make_brand.py` (renders `dist/`: favicon.ico/svg/16/32/48, apple-touch-icon, lockup, og.png), `og_raw.png` (a curated capture, do not regenerate blindly), `og_sink.py`, `preview.html`, `Montserrat-SemiBold.ttf` + `OFL.txt`. `make_pwa_icons.py` (renders `dist/icon-192.png`, `icon-512.png`, `icon-512-maskable.png` for the manifest). `build.py` inlines `dist/favicon.svg`, `favicon-32.png` and `apple-touch-icon.png` into the page and the three app icons into the manifest. |
| `MontserratItalic.ttf` | Variable font `bake_street_sdf.py` renders the street-name atlas from (OFL). |
| `requirements.txt` | Pipeline venv: shapely, numpy, pyproj, laspy[lazrs], Pillow. The build itself needs nothing. |
| `pipeline.py` | Pipeline runner; `python3 pipeline.py --graph` prints the fetch → process → pack → bake → build graph. |
| `overpass.py` | Shared tiled Overpass fetch: mirrors, backoff, per-tile checkpoints (`city_tiles/`, `wide_tiles/`, `south_tiles/`), a missing tile is fatal. |
| `philly_frame.py` | The one lat/lon to local-metres frame (LAT0/LON0/KX/KZ, `to_xz`, `to_latlon`) every pipeline script imports. |
| `provenance.py` | `record()` appends one line per fetch to `provenance.jsonl` (source, URL, query hash, element count, UTC time). |
| `ops/` | Server recipes: the captured live nginx vhost and the `.example` with the planned additions, systemd units, `septa_bake.py`, `ais_relay.py`, `uptime.md`, `README.md`. |
| `tests/` | `python3 -m unittest discover -s tests`. `test_concerts_bake.py` (Round 56) projects a canned Ticketmaster answer through ops/concerts_bake.py and checks the 9 am instants across both DST changes. `test_vbuf.py` (Round 54) runs the packed rings' `VBuf` under JavaScriptCore with the vendored three.min.js: the facade attributes and the glass tint survive growth and reach `geometry(true)`; the glass upload asks for it. `test_pack_common.py` (Round 71) checks the packers' shared guards: the stacked dedupe keeps the taller record, the coplanar inset moves the smaller record by the packer's own quantum and leaves party walls alone. `test_aqi.py` (Round 75) runs the air-quality block under JavaScriptCore: the EPA breakpoints, the categories, the haze curve and the reading cleaner. `test_markets_bake.py` and `test_markets_js.py` (Round 76) check the market bake's parsing and run the clock predicate `marketOpenAt` under JavaScriptCore (a Sunday market, a summer season, a season that wraps New Year). `test_markers_bake.py` (Round 77) checks the marker and art bake: types, the year, the dash rule, the plaque suffix, the 2 m nudge, the Active filter, the centroid, the material scan, the image rule, the column counts. `test_landmarks_bake.py` (Round 78) checks the places bake: the parent collapse to the weighted centroid, a named parcel beside its parent, the drop rules and classes, a recurring name split by distance, the dash rule, City Hall in the frame. `test_closures_bake.py` (Round 79) projects a canned Streets Department answer through ops/closures_bake.py: the occupancy vote, the permits that do not vote, the expired and the not-yet, the 180-day cap, the link host rule, the address join, the paving statuses and the week list's dedupe. `test_amtrak_bake.py` and `test_rail.py` (Round 80) project a canned Amtraker answer through ops/amtrak_bake.py (the box, the Active filter, the next stop and its lateness, the timestamp offsets, the dash rule) and check `rail_amtrak.json` (the box, 30 to 600 track km, the three stations within 120 m of a track) and that app.js still reads it. `test_patco.py` (Round 141) checks `patco.json` (two chains, the stops in order with the portals between Franklin Square and City Hall, every date resolving to a service, the Sep 26 swap day) and the page's wiring. `test_layers.py` (Round 83) pins the fourteen layer keys' order, the link markers, the hash width, a row and a key per layer and the reset map. `test_near.py` (Round 82) checks that every ground layer's draw path asks `nearCam`, that the flights and ships never do, and that the pins and the frame's calls are wired. `test_lights_bake.py` and `test_lights_js.py` (Round 81) check the illumination calendar's bake (the colour words and aliases, the team and cause fallbacks, the cleaned names, the Philadelphia dates across DST, the dedupe and the year cut, the two writers) and run the resolver `lightsThemeAt` under JavaScriptCore with the clock's DST helpers (a game day beats the calendar in team order, preseason never counts, the shortest request wins, the pin forms). |
| `tests/test_cap_construction.py` | Round 104: elevated CAP geometry, full-width highway/boulevard clearances, supports outside traffic lanes, and obsolete path/access-road clipping at the construction boundary. |
| `tests/test_landmark_lighting.py` | Rounds 103/108: single Comcast recess below a solid crown, clearance through the actual packed shoulders, no false lower openings, solid Phillies crown and preserved custom bands; rotated plans, eleven themed clubhouse outlines and custom hex palettes. |
| `tests/test_roof_light_bands.py` | Rounds 117/118: all 23 rendered flat-roof landmark fixtures and soft wash skins follow their packed footprints, with no horizontal glowing caps, buried faces or open corner seams; checks clearance, winding, falloff coordinates and rotated concave/chamfered plans. |
| `tests/theme_lighting_gpu.html` | Round 118: runs the production HDR post pipeline and architectural bloom hooks in both depth modes, with opaque/transparent emitters, red/blue/green halos, preserved broad-panel colors, occluded sources and bloom-masked pins; verifies smooth wash edges and daylight-off behavior on the direct-render fallback. |
| `tests/glass_optics_gpu.html` | Round 120: production glass Fresnel/environment response, stable pane distortion, polished panes with matte frames/masonry, linear reflection-probe color and daylight-only sun glints in both depth modes. |
| `tests/window_interiors_gpu.html` | Round 119: production room illumination in both depth modes; gradients, recessed edges, home/office temperatures, stable occupancy at near/far scales, custom apartment night/day behavior, horizontal glass rejection and dark sash frames. |
| `tests/comcast_gpu.html` | Round 108: production Comcast crown panels and shader, full red face/roof coverage, custom three-color bands, no light across the recess, standard/logarithmic depth and bloom color conversion. |
| `tests/test_architecture.py` / `tests/buildings_gpu.html` | Round 101: production geometry checks for compact wall dimensions, landmark trim, Liberty plans, pyramid normals and Cira's faceted mass; browser GPU gallery checks all 30 base facade styles, packed/core agreement and day/night output in four depth/detail configurations. |
| `tests/test_venues.py` | Runs the actual venue builders with vendored Three.js under Node: finite geometry, terrace heights, regulation football-field dimensions and N8W bearing, a clear playing field, texture bounds, no overlapping baseball-field triangles, flush inward-facing football scoreboards and housings, and a city-scale triangle budget. |
| `tests/test_transport_geometry.py` | Runs production terrain/road helpers with vendored Three.js under Node: cross-slope and midspan clearance, core paths, continuous coverage at stepped tier seams and terrain holes, lane attributes, rail-bed widths, unchanged clear bridge grades, shared bend edges without overlapping triangles, and exact rail portal endpoints. |
| `tests/test_i95_elevation.py` | Round 121: continuous southern I-95 carriageways across the core boundary, scoped mainline classification, gradual emergence, exact ramp joins, deck ownership, lane attributes and traffic using the deck even below the surrounding earth. |
| `tests/test_terrain_patches.py` | Round 102: exact road/landscape intersections, narrow roads crossing triangle interiors, junction unions, ramps, preserved ground under bridges and intentional tunnel caps, top-face filtering, and terrain-following grass without end-cap spill. |
| `tests/test_street_labels.py` | Runs actual street-label geometry under Node: full-width pavement clearance on slopes, interior crests, custom deck heights, crossing-bridge separation, terrain ridges, complete atlas UVs and upward faces. Round 98 also audited all 3,774 baked placements against road/ground triangles. |
| `tests/test_pins.py` | Runs production pin rendering/picking helpers under Node: shared scene-depth policy for every family, rejection of blocked pin hits, transparent-corner rejection, Indego atlas tiles, and overlap ordering among unobstructed pins; since Round 169 a pin the gate hides never takes the tap. |
| `tests/test_pin_fade.py` | Round 169: the pins' state and cadence under Node against scripted images: hidden until an image drawn after the pin came into view clears it, a covered answer hides at once, showing keeps the guard and the fade in, no blink at an edge, an image every 2nd drawn frame on a phone while moving (every frame on a computer) and one the frame the eye stops, near images between complete ones with a far tip in view, a pin the reconcile only moved to another slot keeping its state. |
| `tests/test_zbuf.py` | Round 192: reversed-Z depth. The default (reversed where a throwaway context has `EXT_clip_control` and a complete 4x `DEPTH32F_STENCIL8` framebuffer, the real context checked again), `zrevCheck` against fake contexts, `zrevInstall` run under Node on a stand-in renderer over the vendored three (the projection swapped only inside render, clear 0, GEQUAL/GREATER, the shadow pass standard, the frustum's far plane, the sorts, the clear-to-near guard), the AO's decode, the mirror's reversed oblique row with and without the river in view, the mirror's point-sprite twins' depth (`MIRZ`: the oblique depth of each pixel on the sprite's plane, what stands in front on its ray hides it), the cloud deck's programs and the aircraft's rectangles (`cloudRects`, `cloudRectsFit`), the page's only `gl_FragDepth` writes and every `gl_Position.z` it sets, the depth-mode choice under Node (the clip test, the crumb, the Android hold, `?zbuf=rev` over both), `zrevFail`'s crumb and single reload and that a lost context leaves neither (`zrevLost`: the second review's must-fix), the phone target's blit checked at once in the build (`zrevPresent(true)`), the mirror twins warmed behind the veil (`mirzWarm`), the per-target clear guard, and `zc` on every beacon. |
| `tests/test_pin_gate.py` | Round 169: the CPU's answers under Node against synthetic images (one image, two, reach, arrival, the placards' answer under motion), a tap asking the gate's own images (`pinGateShows`), and the text of the vertex gate. |
| `tests/environment_gpu.html` | Round 106: production grass, pavement, weather, water and sky GPU checks in four depth/detail configurations; stable filtering, lane paint, wet/snow layering, sky-colour reflections, night brightness and independent river/fountain ripple scales. |
| `tests/test_traffic.py` / `tests/traffic_checks.js` | Rounds 107/112: production traffic lifecycle and geometry under Node, upstream inflow to empty visible streets, citywide baked coverage and short connectors; population caps, camera/clock changes, visible-car preservation, T-junction connectivity, separated overpasses, route transfers, following gaps, birth spacing and one-way dead ends. |
| `tests/traffic_gpu.html` | Round 107: all six production vehicle models, paint/trim separation, fixed-size coverage fades, shadow and lamp fades across standard/logarithmic depth and bloom hooks. Add `#gallery` to view the fleet. |
| `tests/pins_gpu.html` | Round 105: production pin materials on the GPU; foreground buildings fully/partially hide badges, search pins and event connectors/anchors, with standard/logarithmic depth and bloom material variants. |
| `tests/pin_readback_gpu.html` | Round 167: the production `PIN_ASYNC` block on a real WebGL 2 context; the depth image read back through a pixel pack buffer behind a fence lands byte for byte the synchronous read's image, with its own capture's matrices, and three's synchronous read (the building tap's) works while it is in flight. Round 169: an image drawn while the read is in flight goes into the other target and leaves the read as it was. |
| `tests/pin_gate_gpu.html` | Round 169: the production `PIN_GATE_GLSL` vertex gate on a real GPU collapses exactly the pins the CPU's `pinOccAnswer` calls covered or unknown (700 tips: no image, one image, one reaching 900 m, a near image with an older complete one, the complete one alone). |
| `tests/clouds_gpu.html` | Browser GPU regression page; serve `3d-model` and open `/tests/clouds_gpu.html`. Loads the production cloud shader and tests desktop/touch sample budgets with standard/log depth: altitude intervals, lower/upper banks, varied bases, clear/overcast coverage, stable pixels, and foreground/background occlusion. Separate from the Python suite. |
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
| `city.b64` | The far ring, the rest of Philadelphia, packed at 0.7 m by `pack_city.py` (magic 0x5348545C: the roof word packs the sampled colour index with a roof form and rise, from the LiDAR pass or the OSM tag) with rowhouse rows merged into block strips (each strip carrying the OPA word most common among its own members and the roof palette entry nearest their mean colour, Round 65; the cell-wide mode before it shipped the far ring's roofs at half their luminance): ~180k buildings, 23.6k road runs. |
| `wide_names.json` | Outer landmark names + heights for the tall-building labels. |
| `wwb.json` | Walt Whitman Bridge alignment for the custom span: one eastbound I-76 carriageway (OSM ways 424803351, 886672856, 1027616621, 123617847, 1311279172) from the Schuylkill Expressway to where the bridge tag ends in Gloucester City, so the Jersey viaduct lands at grade there. |
| `outskirts.b64` | The towns across the city line (Gloucester City, Camden's south wards, Pennsauken, Cheltenham, Springfield, plus the Navy Yard's south half): the strips of the far-ring box the older fetches never covered, packed at 1.0 m by `pack_outskirts.py` from `osm_outskirts_raw.json` (legacy magic 0x53485459, no facade attributes) and decoded by the far ring's `raiseRing()`, plus the filler: synthetic strips of houses along the streets inside residential land use (or a dense street grid) beyond the city line wherever real footprints are thin. Scenery beyond the flight limit. |
| `city_limit.json` | Philadelphia's city line (OSM relation 188022) in the model frame plus the flight limit `bound`: the line buffered 2 km, clipped to the far-ring box (`fetch_boundary.py`). The camera clamps to it in every mode and SEPTA vehicles beyond it are off the map. |
| `facade_palette.json` | 30-colour roof palette (k-means of ortho-sampled roofs), embedded as `FACADE_PAL`. |
| `street_labels.json` | Street-name placements from `bake_street_labels.py`: `names[]` + flat `[nameIdx, x, z, bearing, cls]`. |
| `street_sdf.json` | The street-name SDF atlas (4096×2244 PNG) from `bake_street_sdf.py`. Rects align by index with `street_labels.json`: always re-bake both together. |
| `trees.b64` / `tree_names.json` | PPR Tree Inventory 2025 packed by `pack_trees.py` (magic 'SHTT', 0.7 m units with the unit in the header's fourth slot in mm, the whole city since Round 87: 150,887 trees, 49,038 in the wide box and 101,849 beyond it) + species names. The wide box draws its full forest on a 3x3 chunk grid; the trees beyond it take the phone crown on an 8x8 grid over the city. |
| `places.json` | Historic-district outlines + neighborhood label points from `bake_places.py` (districts are data only since Round 30c; the names render). |
| `patco.json` | PATCO's track and timetable over the Ben Franklin Bridge from `bake_patco.py` (Round 141): the two tracks from OSM ordered Philadelphia to Camden with tunnel and bridge flags, the four stops and the portals along each, the bridge-crossing trips per service and direction (the two bracketing stops' minutes), the calendar resolved to a service mask a day (with the swap-day repair) and a weekly fallback (about 9.5 KB). The page re-seats the tracks on the modelled deck and runs scheduled, not live, trains. |
| `i95.json` | I-95's carriageways from `bake_i95.py` (Round 148): the chains in the direction of travel, 0.1 m, about 7 KB. The page stands a 12 m highway lamp every 50 m on each carriageway's outer shoulder, in the city and past the city line, except where the road is on an elevated deck (the deck standards light it) or a pole already stands. |
| `rail_amtrak.json` | Amtrak's tracks through the city from `bake_rail.py` (Round 80): the OSM `railway=rail` ways Amtrak operates plus the Northeast Corridor and Keystone Corridor ways by name, every track its own line with tunnel and bridge flags, 1.5 m simplified, clipped to the far-ring box (713 lines, 213 track km, 72 KB). The app builds a snap grid the live trains ride and draws the corridor as ballast and rails. |
| `landmarks.json` | The City basemap's named places from `bake_landmarks.py` (Round 78): 5,932 sites (schools, colleges, places of worship, hospitals, parks, rec centers, cemeteries, museums, historic sites, venues, public buildings, stations, bridges, named buildings, natural features) as `{names, l: [nameIdx, x, z, cls, ...]}` for the search index only (`LM_KIND` in app.js decodes `cls`). |
| `markers.json` | The 348 PHMC historical markers in Philadelphia and the City's 224 active Percent for Art works from `bake_markers.py` (Round 77): `m` rows `[x, z, type, year, name, location, text]` (type 0 Roadside, 1 City, 2 Plaque), `a` rows `[x, z, mat, title, artist, date, medium, where, img]`. The app raises a blue-and-gold post per marker and a plinth per work, always on, with cards and search entries. |
| `markets.json` | The City's 34 farmers' markets from `bake_markets.py` (Round 76): scene-frame point, per-weekday hours in minutes with the city's notes, the season, the payments, operator, address, website. The app pitches striped tents at each while its clock says the market is open. |
| `boathouses.json` | Round 103: eleven surveyed OSM clubhouse footprints, architectural palettes, bay counts and approximate roof heights for the custom Boathouse Row models. Inlined as `BOATHOUSES`; matching generic buildings and porch annexes are suppressed in both packed tiers. |
| `lights.json` | BOMA Philadelphia's Building Illumination Calendar from `bake_lights.py` (Round 81): `{t, rows: [{from, to, c: [colours], n: name}]}`, one row per dated request, colours from the title's words, names cleaned. The app lights the skyline crowns and the Ben Franklin Bridge in the night's colour (a Philadelphia game day's team colour first). |
| `overpasses.json` | Elevated chains, sunken runs and the Vine Street cut from `bake_overpasses.py` (527 chains / 147 km). |
| `traffic.b64` | Drivable OSM ways + PennDOT AADT from `bake_traffic.py` (magic 0x53485454) for the typical-traffic sim. Round 112 includes the city and supplemental drives, 29,749 ways / 5,614 km before terrain cuts. Header word 3 is the coordinate unit in millimetres (700; zero means legacy 200). Shared junction vertices and short connectors survive baking. |
| `nw_parks.json` / `nw_water.json` | PPR parkland polygons (city data) and full-fidelity OSM water rings (Overpass, not city data) for the NW hills patch. |
| `poles.b64` | Streets Department street-lighting poles packed by `pack_poles.py` (magic 'SHTP', 0.7 m, ~200k). |
| `paved.b64` | The paved ground packed by `pack_paved.py` (int16 header 'PV' 0x5056, version 1, whole metres, rings closed implicitly): every unbuilt surface outside the core that is asphalt, concrete or ballast in life, by kind (1 surface lot, 2 industrial / port / commercial / retail yard, 3 rail yard, 4 apron; 4,677 / 1,053 / 24 / 25 rings, 54k vertices, 317 KB base64 on 2026-09-04), laid by the app under the parks and the streets so the meadow stops showing on it. |

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
| `fetch_paved.py` → `osm_paved_raw.json`, `paved_tiles/` | Surface parking (amenity=parking minus the multi-storey, underground, rooftop, carport and garage-box kinds), the paved land uses the landuse fetch leaves out (railway, port, depot, garages, brownfield, construction, quarry, landfill), aeroway=apron and man_made=works over the whole far-ring box (16 tiles, ways only, checkpointed like `landuse_tiles/`). Run with `OVERPASS_MIRRORS=https://overpass-api.de/api/interpreter`: the other mirrors time out on this box. |
| `pack_paved.py` → `paved.b64` | *shapely.* Reads that and `osm_landuse_raw.json` (industrial, commercial, retail; residential stays meadow), projects with `philly_frame.py`, clips to the far-ring box, drops rings centred in the core, unions each kind so nothing of one kind is coplanar (a lot inside a yard is another kind and draws above it), drops holes, simplifies at 1 m, floors at 200 m2 (lots) / 400 m2 (the rest), CCW whole metres sorted by kind then centroid so the blob is stable. |
| `roof_tags.py` → `lidar_cache/roof_shapes.json` | OSM `roof:shape` tags from the three raw dumps (33k ways: flat, gabled, hipped, gambrel, saltbox, mansard) plus the centroid of every wide and south building way, so `pack_wide.py` can attach way ids to scene buildings. |
| `fetch_lidar_roofs.py` → `lidar_city_roofs.json`, `lidar_cache/roof_tiles/` | Citywide roof forms (flat, gable, hip with eave, ridge and ridge angle) streamed at coarse resolution from the 752 NOAA 2022 COPC tiles over HTTP, one JSON per tile, merged with `--merge`; resumable, hours for the whole city. |
| `fetch_overture.py` → `lidar_cache/overture_phl.json` | Overture Maps buildings over the far-ring box through DuckDB (heights, roof shape, facade material by OSM way id). Checked 2026-09-02: its roof and colour attributes are OSM's own tags re-exported, so it adds nothing beyond `roof_tags.py`. |
| `fetch_shops.py` → `lidar_cache/shops_raw.json`, `lidar_cache/shop_tiles/` | OSM shops, cafes, bars, banks, pharmacies and the rest (nodes and ways) over the wide and south boxes, with a small kind code. Round 189: the fetch runs under `main()`, so `bake_storefronts.py` imports its tables and `businesses()` (the same rows with their OSM tags) without fetching; re-run in a scratch copy of the tiles, `shops_raw.json` came out byte for byte. |
| `bake_storefronts.py` → `storefronts.b64`, `storefront_info.json` | Each business on the facade edge of its building that faces the street (line of sight, sidewalk depth, tie-break by the door): 8 int16 per storefront (magic 0x53485446): position, outward angle, width, kind, colour, floor height, flags for awning, sign and glass. `storefronts.json` beside it is the same for inspection and does not ship. Round 189: it re-encodes the blob and refuses to write anything when it differs from `storefronts.b64` on disk (prints the first differing record; `--rebake` overrides), and writes the sidecar in the records' order (see `storefront_info.json`). The review's second pass: each laid span is measured on the rings the page DRAWS (the core's `scene.json` rings and `wide.b64`'s records decoded, so it reads `wide.b64` too: `drawn_rings`, `drawn_host`), sampled every 10 cm along its wall (`wall_profile`): the wall must be there (no panel past a corner), in view (no footprint, a neighbour's or the host's own bay, in the 45 degree cone 3 m deep in front of it: `SPAN_PROBE`) and flush (at most `SPAN_FLUSH` 30 cm proud anywhere once the wall's lean against the record's angle, `lean`, is taken out and handed to the page as a turn); the best window within the record's room (`best_window`, `SPAN_SLIDE` 3 m either side, never past the midpoint to a neighbour laid on its line) takes it at its laid width or narrower, under `SPAN_MIN` 3.4 m it is hidden; a business inside a `shop=mall` way of the shop tiles (Liberty Place, the Fashion District) is hidden. The wall's out and in go to the sidecar as found, never clamped (the second review: a 1.2 m clamp laid five panels on tower hosts, Insomnia Cookies on Broad Street among them, 1.3 to 1.5 m in front of a base drawn 1.4 to 2.8 m behind the record's line; a face is found within `SPAN_REACH` 3 m, and the int16 guard holds the rest). `--debug i,j` prints the profiles. |
| `fetch_mapillary.py` → `lidar_cache/mly_tiles/`, `lidar_cache/mly_thumbs/`, `lidar_cache/mly_images.json` | Mapillary street-level thumbnails over the wide and south boxes (CC BY-SA; needs `MAPILLARY_TOKEN`, a free client token from mapillary.com/dashboard/developers). Lists images from the z14 vector tiles with a stdlib protobuf reader (the Graph API bbox search fails whole neighbourhoods with "reduce the amount of data"), picks the newest per 10 m cell up to `--max-images`, resolves thumbnail URLs 50 ids at a time; `--dry-run` synthesises a test set. |
| `bake_wall_colors.py` → `wall_palette.json`, `wall_colors.json` | Wall colour per block face from the thumbnails (median of the flanking bands, sky, road and foliage discarded), quantised to a 32-colour palette and assigned per scene building, with a per-face light and dark pixel fraction classed into the trim and window hints (`wide_hint`, `south_hint`). `pack_wide.py` turns the pair into `wide_walls.b64`; a dry-run pair is ignored. Both jsons are gitignored, the blob is committed. |
| `storefronts.b64` | The baked storefronts, decoded by the app's "Dressing the storefronts" step into glazed fronts, awnings and signboards that glow after dark. Round 189: under the realistic look on WebGL 2 each record is a generated photographic shopfront (`sfBuild`); `?real=0`, `?sfart=0`, WebGL 1 or art that does not arrive keep the boxes, built inline as they were. Never repacked: what the panels need beyond it rides in `storefront_info.json`. |
| `storefront_info.json` | Inlined as `STOREFRONT_INFO` (Round 189, `bake_storefronts.py`): per storefront in `storefronts.b64`'s order, its OSM name (short name first, cleaned, at most 40 characters: a longer one is cut at its best joint, `cut_name`, before a separator, an '&' joining two names, after a word that ends a business's name, before a connector or at a word, and never left on a connector), and `stride` int16 (9 since `v` 2, base64 `rec`): the shift along the wall from the side-by-side layout of records sharing a wall line and the drawn wall's window (dm), the laid width (dm, 0 hidden), the drawn wall's outermost and innermost point over the span at its middle's line (cm, the rings the page draws, the lean taken out, never clamped), the host's storey height (dm, from its OPA storeys), the trade family (the art's thirteen; a restaurant is the takeout's counter by `amenity=fast_food`, its cuisine (`TAKEOUT_CUISINE`, and since the third review the counters' `COUNTER_CUISINE`), `takeaway=only`, a name that says so (`TAKEOUT_NAME`) or a Chinese restaurant outside `CENTER_CITY`), the opening hours' index (`hours`: the weekday's span (the one most of Monday to Friday keep), Saturday's and Sunday's, open and close in minutes, and a seventh value with a bit for each weekday it keeps shut, Monday the first, parsed from OSM `opening_hours`; a weekday open on another span than the rest keeps theirs), the span's end bits plus the host's height, and the panel's turn to its wall (the lean, in ten-thousandths). The page uses it only when its `n` matches the blob's and its length the stride; `b64sha` names the blob it was baked against. |
| `fetch_storefront_art.py` / `bake_storefront_art.py` → `storefront_art.json`, `art/storefronts/` | The storefronts' shopfronts (Round 189): `fetch_storefront_art.py` asks OpenAI's image API (`gpt-image-2`, quality high, the key only from `OPENAI_API_KEY` or `~/.config/philly3d/openai.env`) for 110 cells (83, then the review's second set: a second M and L a trade and a third S for the groceries, numbered on after the first so its prompts stand, the grocery's, the shop's and the takeout's second M and L corner stores, `CORNER`), thirteen trades (`FAMILIES`) by four width classes (`CLASSES`: S 4.5 m, M 6, L 8.5, XL 11, every one 4.2 m tall at its own aspect), each made in two stages into `lidar_cache/storefront_art_raw/`: `frames/` the shopfront empty with every pane a flat chroma-key green and a blank fascia board, then `insides/` the shop's interior painted into the panes through `/v1/images/edits` with the key's mask (`bake_storefront_art.py --masks` writes `<id>-mask.png` beside each frame, an API input only); `interiors/` is the fallback. The API's credit ran out after 24 of the second set's 27 frames and before any of their edits, so a cell with no edit borrows its trade's (`plates`: the largest clean rectangle of each pane of the trade's own edits, a grocery's corner store the groceries' and the shops', the shop's and the takeout's corner frames their own trade's, as `interior_of` asks the edit for; `transplant` scales one to cover each pane of the cell, its bars and glazing bars closed over); a cell with no frame is left out. `bake_storefront_art.py` pastes back only the keyed pixels of each edit (so frame and mask stay registered), finds the fascia board and checks it is blank, measures the bulkhead's top, the glass head and the board from the foot, finds the door (a leaf's glass 0.5 to 1.15 m, or a pair of leaves of 0.25 to 0.8 m, its rail closed over: `DOOR_W`), and packs a 4096x2048 shelf atlas at 44 px/m (50 until the second set, which at 50 wanted a third more atlas) with 8 px gutters, its phone half, and an opaque RGB mask atlas at half (r glass, g board, b door) and its half, all through `art_files.py`; the manifest carries every cell's rect, band, rows, piers, door, board colour and luminance, each cell's joinery colour (`frame`, `frame_colour`), and `gen` (the cells the painted shop floors use: of each class a trade's first or second by turns, in `gen_order`'s order: split four and four so the most alike pair, by joinery colour and `GEN_ALIKE`'s trades, is on one side, and laid on alternate places, since the shader deals a wall's units an odd stride apart). It refuses an atlas wider than 4096 or over 2^24 pixels (the page packs a cell's corner as x + w y in one float). `--preview DIR` writes overlays and contact sheets. |
| `storefront_art.json` | Inlined as `STOREFRONT_ART` (Round 189): the shopfront atlas's files under `art/storefronts/` and its cells, read by 'Dressing the storefronts' (`sfBuild`, `sfPanelHook`, the names' slot atlas `sfNamesInit` / `sfStep`) and by the facade hook's style-5 ground floor (`SF_PARTA`, `sfPartU`); `__dbg.sf()` (`__dbg.sf(r)` lists the panels within r metres, `__dbg.sf('list')` every panel, `__dbg.sf('repeats')` the pairs wearing one cell). |
| `fetch_cityhall_art.py` / `bake_cityhall_art.py` → `cityhall_art.json`, `art/cityhall/` | City Hall's facades (Round 191): `fetch_cityhall_art.py` asks OpenAI's image API (`gpt-image-2`, quality high, the key only from `OPENAI_API_KEY` or `~/.config/philly3d/openai.env`) for 24 straight-on elevations into `lidar_cache/cityhall_art_raw/<id>.png` with a sidecar `.json` (`IMAGES`, `TILES`, `WALLS`: a wing section of four bays, the three bays beside a centre pavilion, a centre pavilion's front with its great arch a flat magenta, a corner pavilion's face, the courtyard's plain north wall, its east, west and south walls with their great arched windows (`ch_court_main`) and the bay over each passage's courtyard end with its small arch a flat magenta (`ch_court_bay`), the tower's channel-jointed shaft with its great tripartite window, its middle stage and its belvedere with a narrow glazed arch, the clock stage with its dial a flat green disc and no numerals, a face of the dome, the wing dormer, the corner pavilions' and the centre pavilions' sculptural dormers, the oculus, a turret's top stage, the apse's banded half drum with its door a flat magenta, a balustrade, plain ashlar and the tower's channel-jointed courses (`ch_rustic`); fix3: a face of the centre crowns' cornice
box with its bracket frieze and pediment, the sky beside the pediment a flat magenta (`ch_crown`), the base course's granite
(`ch_granite`, a tile) and a bay of a passage's wall, rusticated marble over a granite dado (`ch_vest`, `WALLS`)), every pane a flat chroma-key green; `--only`, `--force`, `--list`, an image on disk kept. `lidar_cache/cityhall_art_raw/aside/` keeps the first clock (its dial set too high) and the first tower shaft, belvedere and apse (`_v1`, Round 191's second review). `bake_cityhall_art.py` keys the glass (`KEY_*`) and its spill, fills each pane with dark glass inside a dark sash frame with a meeting rail and a muntin down a wide pane (none of it glass in the mask; b on the glass its height in the pane, 2 to 117), the dial with its teal and a gilt ring (mask b 200), the balustrade's sky to be cut (b 60), every magenta opening with the passage's shade (`PORTAL`, b 120: the far level has no passage); the key takes any green standing `KEY_GAP` over the other channels and `KEY_K` times the larger (fix1: the shaded green in the arched windows' heads); blurs any carving drawn as lettering (`SOFTEN`), calibrates each picture's median stone to `MARBLE` (the block's weathered grey), the tower's masonry to `TOWER_STONE` (cleaner), the granite to `GRANITE` or its paint to `METAL`, and takes every recess darker (`SOOT`); tones each block of the tower's channel-jointed courses its own and cuts in the head joints the picture left out (`courses`, fix3); keeps a window's number and height on its sash bars and a few pixels out over the stone (fix3: filtered, a bar's 0 drew every sash a dotted line at night); fills the crown box's keyed sky and measures its pediment (`ped`) and every outer front's lowest sill (`sill`, which the water table stands under); takes each picture's storeys to the building's (`CELLS` rows: 5.57, 15.78 and 26.63 m on the wings); measures the arches, the apse's door and the dial and carries `COLS`, the free-standing columns measured by hand on the centre and corner pictures, into the manifest in metres; and skyline-packs the 24 cells into one 2048 atlas at about 25 px/m (`dens` weights) with 16 px gutters (wrapped for the cells that tile), an opaque RGB mask at half (r glass, g the window's number, b the flags) and a phone's halves, all through `art_files.py`. `--preview DIR` writes the atlas and mask. |
| `cityhall_art.json` | Inlined as `CITYHALL_ART` (Round 191): the atlas's files under `art/cityhall/`, every cell's rect (`cells`, texture uv, v up), size in metres (`m`) and mean colour (`mean`, the far level's vertex colours), and `meta` (the centre pavilion's arch and columns, the corner pavilion's columns, the courtyard bay's small arch, the apse's door, the clock's dial; fix3: the crown box's pediment and each outer front's lowest sill), read by `buildCityHallReal` (`chModel`, `chTower`, `chDials`); `__dbg.cityHall()` (`'off'` / `'on'` hides its own meshes for the A/B, `'near'` / `'far'` / `'auto'` pins the level). |
| `fetch_glory_art.py` / `bake_glory_art.py` → `glory_art.json`, `art/glory/`, `lidar_cache/glory_art_raw/` | Glory Beer Bar & Kitchen's art (Round 191, Mike: City Hall and Glory "totally revamped"). `fetch_glory_art.py` asks OpenAI's image API (`gpt-image-2`, quality high, opaque, the key only from `OPENAI_API_KEY` or `~/.config/philly3d/openai.env`, never printed) in four stages into `lidar_cache/glory_art_raw/<stage>/<id>.png` with a sidecar `<id>.json` (prompt, model, size, usage, and an edit's source and mask sha): `frames` (variants of the two straight-on elevations of 126 Chestnut, 8.6 by 9.3 m at 1536x1664: the granite ground floor and second storey, and the three brick storeys with their corbelled cornice, every pane a flat chroma-key green; lower-a and lower-b from `LOWER`, whose "pointed four-centred" arches came out as gothic lancets, lower-c to lower-f from Round 191's `LOWER2`, which gives the storey in metres: coupled Tuscan columns, a flat lintel dipping 35 cm between the capitals, two casements a bay, no hood moulds or tracery, doors glazed to a short kick rail, a warm buff granite), `glass` (the chosen upper frame with window glass painted into its key through `/v1/images/edits`), `rooms` (two variants each of the bar, 1536x784, and the room upstairs, 1536x608, from just inside the front in one-point perspective, empty, evening) and `crowd` (the chosen rooms with people added over their floors). `CHOSEN` names the variants picked by eye (lower-e, upper-b, ground-empty-b, upper-empty-a); `--only`, `--force`, `--list`; an image on disk is kept. Fifteen calls in all (eleven in the first build, four lower frames in Round 191's fixes). `bake_glory_art.py --masks` writes the edits' masks beside their sources (an API input only: the upper frame's over its key, each room's over its floor below 2.1 m in its own projection less the bar's shelving); the bake finds the key (hue 100 to 140, saturation over 0.55, value over 0.5, closed a pixel; refused outside 0.15 to 0.45 of the lower and 0.10 to 0.22 of the upper), measures the openings from it in metres (the four doors grown out to their dark frames, the four arches with their crown at the middle and their spring at the top of the frame's stile 4% in from each side, refused when the rise is over `ARCH_RISE_MAX` 0.5 m, the columns in pairs in the gaps, the twelve windows grown to the brick across and the white frame up and down, then set to their stack's and storey's medians; `NOMINAL` stands in with a warning), fills the lower key and its 2 px rim from the dark frame round it only (`fill_dark`: no green in a mip and no pale rim round a pane), the upper's with the frames' own colour, takes the brick's saturation down by `BRICK_DESAT` and tints the granite toward red by `STONE_TINT` (rendered, hue 30 to 34 at HSV saturation 0.10 to 0.15 against the photographs' 30 and 0.12), pastes the glass edit inside the upper key only, and lays the 2048x1280 facade atlas (both elevations at 117 px/m in 8 px gutters, then eight tileable swatches: granite (`granite_swatch`: four jointless patches of the piers' faces in a 2 by 2 quilt, their low frequencies flattened, 0.68 m a tile; Round 191's review found the old one's stone joint drawing a ladder up every pier side; its grain and weather are the shader's), brick, concrete (a fine aggregate's grain over a faint mottle since Round 191's third review), iron, the old sign box's pale worn white-grey enamel (190, 192, 186) chipped to rust in small ragged flakes with thin rust runs (`peel_swatch`, every field periodic; its first pale blue read as a glass slab, its second grey-sage as darker and greener than the photograph), the lanterns' glow, the roof, and the rust of the box's cap (`rust_swatch`); every plain swatch from `noise_swatch`, whose fields are `periodic` (tiled three by three before the resize, the middle kept: Round 191's third review found its coarse field unwrapped, a seam down the stoop and through every step)), its opaque RGB mask at half (r glass: the lower elevation's from `regular_lites`, every sash's lites set to their columns' and rows' medians, the sash grown two source pixels toward its outer frame, every muntin a straight bar two texels wide on the texel boundary nearest its middle, so every lite is a rectangle of whole texels and the mask holds only 0 and 255 there, and the same bars painted into the atlas in the frame's colour, `paint_bars` (Round 191's third review: the image's own bars wobbled a texel and bulged at every crossing); the upper's key grown two full-size pixels toward the outer frame only, never into a bar between two panes of one opening: `pane_bars`, what closing the key by 4 px fills, stays 0 two texels wide at the mask's size, `bar_texels`, so the doors' 2 by 6 lites a leaf and the casements' 2 by 8 keep their muntins, which Round 191's first fix had filled to a third or two thirds of the glass; g the pane or window number, b the upper windows' height 0 to 64, 200 the bar's glass, 216 the room upstairs', 240 the glow: the page reads the categories by position, g and b at the mask's full size), the 1024 wide room atlas (the open rooms full width, the shut ones at half) and its mask (r bulbs, g the back bar's glow), every file with its phone half. `BACK` is each chosen room's back wall rectangle, measured once by hand (a plate without one is refused); `CORNICE` the granite cornice by hand; `CAPITAL` the piers' painted capitals by hand (their foot and top, the end two's margins from the party walls, the inner ones' overhang), which the cap boxes stand on; `door_leaves` the eight door leaves from the regular sashes (`LEAF_STILE` 0.1 m outside their glass, the leaves' head `TRANSOM_BAR` 0.11 m under the transoms' glass, both by hand), refused when not found. `--preview DIR` writes the atlases. |
| `glory_art.json` | Inlined as `GLORY_ART` (Round 191): the paths under `art/glory/`, the elevations' rects and measures (`lower`: `bays`, `doorTop`, `doorFoot`, `arcade`, `spring`, `crown`, `sill2`, `cols`, `colR`, `cornice`, `capital`, `leaves` (each bay's [outer, middle, outer] and the leaves' `top`); `upper`: `win`, each as the photograph saw it, the image's left the EAST end), the swatches' rects and metres a tile, the room plates' rects, back walls and room boxes, and `gen` (the model, the chosen variants and any measuring warnings). Read by the app's `api.glory` (`gloryFacadeMat`, `gloryU`) and by `rebuilds/glory.js`, which mirrors every measure into its frame. |
| `rebuilds/glory.js` | Glory Beer Bar & Kitchen on its own lot (Round 191): scene building 2541, 126 Chestnut (the old builder in 'Restoring the landmarks' stood on 120, two lots east, and stays for `?real=0` and `?glory=0`). One merged near mesh of 4,686 triangles on one facade material, one draw (the holed elevations with every opening cut and set back on its own pixels under a segmental head, the piers and the capitals' boxes on the painted capitals (`capital`), the coupled Tuscan columns on a torus and plinth under an echinus and abacus, both cornices, the sills and lintels, the shell and rear range, the penthouse and bulkhead, the stoop and its steps, the railings and their cast band, the Juliet balconet with a 0.12 m belly and a band of scrolls, the caged jar lanterns with their bulbs on gooseneck arms (the globe's normals the round jar's at every corner, `quadN`), the blade sign's bracket, the old sign box in its strut frame on a rusted rounded cap, the menu case, the cafe's black pedestal tables with their aprons and galvanized chairs with three curved back slats and a turned-down seat edge, the bar's east door leaf of the entrance standing open (aGl mode 6, the leaf's own pixels, folded away while the door is shut: `uGlDoor`, the hours and fair weather; the shader opens its doorway on the recessed face, `frame.leaf`), and since Round 191's review the signs themselves, aGl mode 4 on the page-lettered canvas) and a far mesh of 78 triangles (its stoop's railings one strip a run); aGl (four normalized bytes: the mode, the swatch or part, unused, the shade a recess or underside takes, `SH`) says how the facade shader colours each face. Mode 5 is the cast lace (`GLORY_LACE_GLSL` in the app, one strip two faces back to back a run: kind 0 the stoop's band of cast fleurons a picket (a pointed arch from scrolled feet, a spade over it, a drop inside, strokes of about 2 cm) and a heavy ring at each post, 1 the balconet's scrolls, 2 a whole railing for the far level), cut by its signed distance with `discard`, the pixels a bar part covers dithered by its share, and cut at its line in the shadow pass; Round 191's second review found the six-piece rings it replaced drawing as plain hexagons. `frame.drips` (the capitals', the sill course's and the cornice's foot) and `frame.signbox` hand the shader the stone's drip lines and the old box's extent; `frame.bays`, `arcade` and `bayY` the openings whose light falls out through their glass after dark (`glSpill`), `fw` the east return the shader paints black over the storefront. It hands the app the block's walk as paving (`G.paved`, `REBUILD_PAVED`: no grass tuft is sown there). Its `ref.apron` is the walk in front of its own frontage, 2.4 m out: a tap whose hit stands there names Glory (its signs, lanterns and old box tapped from the sidewalk opened the generic card), and the lot is tested 0.3 m past the hit, never 1.5 m (an oblique tap on 128's front named Glory). Without `api.glory` (the Node tests) it builds the same meshes on `K.mat` stand-ins. `real: true`: the rebuild step skips it under `?real=0`, and `?glory=0` skips it by its own id. Its card asks the city for the parcel at `ref.parcel`, the OPA point inside the lot. |
| `art/glory/` | Glory's facade atlas and mask, its room atlas and mask, each with a `-half` phone copy, named by content hash; loaded on demand (`gloryLoad`), never inlined, and uploaded one a frame (`gloryUpload`, Round 191's third review: the four landed in consecutive frames). Every device fetches only their bytes at the rebuild step and decodes them the first time the eye comes within `GLORY_DECODE_R` 600 m after Enter (200 m on the recovery tier, `TIER2`, which never loads the rooms: the bar's glass glows plain warm) (a phone since Round 191's review, the Round 189 rule; a computer since its second review: decoded at the step, the art held about 28.6 MB of every computer session's GPU with its mips, the facade 14.0, its mask 3.5, the rooms 6.7, their mask 1.7 and the signs' canvas 2.8). Once decoded a phone holds about 7.2 MB on its GPU (the facade half 3.5, its mask 0.87, the rooms half 1.67, their mask 0.42, the signs' canvas 0.7) and never lets it go when the eye leaves Old City: acceptable under the deferral, and the first thing to release if a phone's memory needs it. |
| `glass_systems.json` | The glass towers' curtain-wall systems (Round 192), hand-authored from the references each entry names: sixteen systems (Comcast's unitized flush joints and shadow boxes, the CTC's units and caps, Liberty's 1987 blue reflective grid and granite bands, Cira's silver, FMC's icy office floors and clear flats, the clear low-iron lantern, the dark grid, 1818 Market's white ribbons, two residential window walls, white fins, a frit, the reflective bands, gold, the generic unitized, the jagged blue), each with its bay, floor, module (`nbM` bays by `nfM` floors in one atlas cell), F0 and transmittance (Vitro's data: modern low-e 0.07 to 0.12, the 1980s coatings and silver 0.20 to 0.35), coating saturation, pane bow and roller wave, spandrel kind and back, frame colour, metalness, roughness and `tint` (whether the authored colour sets an atlas frame of one material), rooms, an upper datum (Comcast's crown at 269 m, the CTC's hotel at 213.5, FMC's flats at 140), low-iron corners and the lobby's height; `towers` names a system and a glass colour for every towers.json glass tower (1818 Market as white concrete ribbons and The Laurel as warm grey glass are the research's reassignments; the review put The Laurel and 1919 Market, both residential, on the residential wall), frame metalness for a painted mullion low (PVDF paint, 0.25 to 0.45: the review), frame colours and spandrel backs the colour the surface shows in the sun (the page draws them at the fabric's register, `GLASS_PAINT` = FACADE_GAIN: the second review), each tower's `body` its photographed glass (the third review: by day the page takes the glass's reflectance from it, `coatSat` 1 everywhere; F0 is the references' and serves after dark and as the share the corners, crown and lobby keep), `frame.slim` the joints the bake thins a generated elevation to (Comcast 70 mm and 140 mm a floor, the generic unitized 75 and 160: the second review's white graph paper), `generic` the system of each glass cladding kind, `styleDefault` a style's where a wall names none. `bake_glass_art.py` copies it whole into `glass_art.json`; re-bake after any edit (`tests/test_glass_towers.py` checks they agree). |
| `fetch_glass_art.py` / `bake_glass_art.py` → `glass_art.json`, `art/glass/` | The glass towers' art (Round 192). `fetch_glass_art.py` asks OpenAI's image API (`gpt-image-2`, quality high, the key only from `OPENAI_API_KEY` or `~/.config/philly3d/openai.env`, through `fetch_storefront_art.py`'s plumbing) for one straight-on elevation a system (`FRAMES`: a few storeys by a few bays of its own module, every vision pane a flat chroma-key green and every opaque spandrel or railing pane a flat magenta) into `lidar_cache/glass_art_raw/frames/`, and eight rooms (`ROOMS`: four offices, a living room, a bedroom, a hotel room, an unfinished floor) through `/v1/images/edits` on the one-point perspective template the bake draws (`room_template`) into `rooms/`; `--only`, `--force`, a sidecar json beside each image. `bake_glass_art.py` keys each frame (a soft matte, the spill taken out), finds its repeat both ways near the system's module, aligns every repeat to their mean (a few pixels each way: the model never draws two bays alike) and folds them into one module (refusing a fold whose repeats disagree, `MUDDY`, or a key left in the frame), starts it at a mullion's middle and the foot of a vision band (the floor line), fills the keyed pixels from the frame round them (push-pull: no green in any mip), thins the joints of a system with `frame.slim` (`slim`: the glass grown into the frame, cyclically, each axis by its own radius, until the vertical joint and the opaque rows a floor are the wanted sightlines; `joints` measures them, the cell records before and after), measures the vision band's sill and head, the glass's shares and the frame's mean, and writes the frames as one strip of sixteen 256-pixel square tiles, a system a tile (`tile`: the module resampled periodically, Lanczos over a 3 by 3 tiling, its foot the tile's first row), an opaque RGB PNG (r vision glass, g spandrel or railing glass, b the frame's detail: its luminance over twice the frame's mean, which the page multiplies by the system's frame colour, so a fragment makes one fetch; the albedo itself goes only to `--preview`) and its 128-pixel phone half, which the page uploads as a texture array with REPEAT and mips (Round 192's review: the first cut's 2048x1024 shelf atlas held each cell's footprint in an 8 px gutter and dropped every wall to a flat mean a block out); the rooms go to a 1536x1152 atlas (cells 384x576), a computer's only (no half copy), each with its back wall's scale across and up and its vanishing point, measured by eye (`BACK`: the edit keeps the view but not the back wall's size; `back_wall_check` reports the drift), its lit and day means. `--preview DIR` writes each cell, a tiled copy and the atlases. |
| `glass_art.json` | Inlined as `GLASS_ART` (Round 192): the systems, towers and generic kinds of `glass_systems.json`, the frames' strip under `art/glass/` (`frames`, `framesHalf`, `tile`) and each system's measures (`cells`: module size, sill, head, coverage, secondary, frame mean in linear light, which `glassSysPack` takes to the scene's working values), the room atlas and its cells (rect, back-wall scale across and up, vanishing point, lit and day means). Read by `glassSysPack` (the systems into `uGS`, ten vec4 each), the wide loop's routing (`glassSysOfSpec`, `glassGenericSys`, `glassTowerBody`, `glassBody`) and 'Glazing the towers' (the frames as a `DataArrayTexture`; the rooms by `glassRoomsLoad` on the first dusk); `__dbg.glass()`. |
| `glass_calibrate.py` → `tests/glass_calibration.json`, `tests/glass_calibration_poses.json` | The glass towers' day calibration (Round 192's reviews): renders the built page headless at the standard noon poses through the capture skill's `render.mjs`, each five ways (as drawn, the glass's material as a flat mask, each tower's glass by a three-bit code of its own in two views that survive the tone curve, `tower_code`, and the glass alone without its frames), takes each researched tower's own glass (its code's pixels in its projected box, else the code nearest its axis) and its mean's CIE76 delta E and b* gap from its reference swatch (`SW`: 28 towers, each its photographed glass, the body `glass_systems.json` gives it), and writes the measures with a fingerprint of the glass's GLSL and systems. Each tower is judged only where it stands in the open (`JUDGE`: 400 pixels of its own glass, two fifths of its height, the eye no more than 20 m over its top: from above a wall mirrors the city under it), the poses frozen in `tests/glass_calibration_poses.json` by `--judge`; the third review widened the poses to the review's eight, the CTC's south face at mid-level, Comcast's shaded north-east face, four at 60 m and five aimed at the lower towers. `tests/test_glass_calibration.py` holds each tower's median over its judged poses within delta E 15 and b* 6 (`HUE_B`), the towers still open (`OPEN`, each with its recorded gap and the reason, for Mike) no worse than recorded, Comcast and the CTC within both at every pose the review named (`NAMED`), Comcast's frames against its glass at 100 m under `CONTRAST` 2, One Liberty's crown (`REGION`), and fails if the glass changed since the measure: re-run `python3 glass_calibrate.py --judge` after `build.py` whenever the glass's shaders or `glass_systems.json` change (about six minutes; `--shots DIR` measures shots already rendered). |
| `bake_towers.py` → `towers.json` | The researched Center City towers (`wide_landmarks_research.json`, `wide_names.json`) as one spec each: joined to the wide footprint or part name-first (IDF-weighted tokens), then by a scored position match, height, sRGB tint, a facade archetype (glass, glass with bands, dark glass, precast grid, stone piers, pre-war stone, precast bands, brick) from the research text and an override table, a crown (pyramid, lattice, ziggurat, lantern, notch, spire, mansard, dome) and a night accent colour. |
| `towers.json` | The tower specs, inlined as `TOWERS`; "Raising the outer districts" joins each tower over 45 m to the nearest spec within its radius, gives it the archetype's facade style and tint (glass ones go to the reflective curtain wall with a band variant) and raises the crown above a body stopped short of the researched height. |
| `bake_schuylkill.py` → `schuylkill.json`, `lidar_cache/schuylkill_ways.json`, `lidar_cache/schuylkill_outline_raw.json` | The Schuylkill's real course and outline: the OSM `waterway=river` ways named Schuylkill over the city and the `natural=water` river multipolygons around them (two cached Overpass queries), the ways simplified to 3 m as `lines`, the outline faces the waterway threads united with a 60 m buffer of the ways and clipped to the modelled reach as `polys` (rings with island holes). The hand polyline in app.js is the fallback. |
| `schuylkill.json` | Inlined as `SCHUYLKILL_DATA`: `riverCarve` takes the ground inside `polys` to the bed and ramps a high bank down within 40 m outside (a 10 m scanline raster for inside/outside, a 20 m edge grid for the distance), `riverCorridor` reads the same raster, and "Raising the rest of Philadelphia" draws the polygons flat at the river level through `flatShorePoly` (vertices carry their shore distance in the colour alpha for the shallows and foam in `liquify`), so the shoreline is the outline and not the ground grid. `lines` remain the centreline fallback. |
| `bake_delaware.py` → `delaware.json`, `lidar_cache/delaware_coastline_raw.json` | The tidal Delaware's outline: OSM maps the estuary below Trenton as `natural=coastline`, not water polygons, so no packed tier holds its surface; the coastline ways from Marcus Hook to Bristol are polygonised against the query box and the faces holding seed points out on the river are kept (islands and tributary mouths fall out as holes), clipped to 48 km of the origin, `polys` the outline and `beyond` the outline minus the far ring's ground box. Round 55 coda. |
| `delaware.json` | Inlined as `DELAWARE_DATA`: `delawareAt(x, z)` (point in the outline, holes excluded) is the shoreline test for the far ground's cells beyond the DEM grids and for the whole reach from the Navy Yard south (`delawareTurn`, z past 6,300; Round 66 closed the two-row gap at 7,500 to 7,600 that stood as a strip across the channel), and `beyond` is drawn flat at the river level over the apron so the river runs on to the fog past the world the camera can reach. |
| `pack_common.py` | The building packers' shared guards (Round 71): `dedupe_stacked` (two records on one footprint with overlapping heights keep the taller) and `nudge_coplanar` / `inset_ring` (the smaller of two records whose walls share a plane facing the same way is inset per link, over the packer's coordinate grid so the int16 rounding cannot cancel it). pack_wide.py carried them from the outer districts' z-fight rounds; pack_city.py and pack_outskirts.py use them since Round 71 (1.05 m and 1.5 m insets on their 0.7 m and 1.0 m grids). |
| `pack_clouds.py` → `clouds.json` | The low-poly cloud models: reads `3d assets/Clouds/Clouds.FBX` (nine meshes from 3ds Max, Y-up, all triangles) with a stdlib binary-FBX reader, centres each on its bounding box and scales its width to 1, and writes the vertices (1e-4) and triangle indices. Round 67. |
| `clouds.json` | Inlined as `CLOUDS_DATA`: the app's low-poly cloud field (`CLOUD_FIELD`, `cloudFieldUpdate`) instances the nine models over 750 m cells about the camera by hash, with a probability, a size and a grey that follow `WX.cover`, drifting with the deck's wind. Round 67; reverted the same day (Round 67 coda, Mike: not working), so the field is built only behind `?clouds=lowpoly` and the ray-marched deck is the default. |
| `fetch_fronts.py` / `bake_fronts.py` → `fronts.json` | The house fronts of the facade prototype (Oct 12): `fetch_fronts.py` asks OpenAI's image API (`gpt-image-2`, 768x1280, the key only in `~/.config/philly3d/openai.env` or `OPENAI_API_KEY`, never the repo) for one straight-on elevation a prompt, party wall to party wall and sidewalk to cornice, sixteen a set for fifteen house types (Round 181: `federal`, `southrow`, `shop`, `victorian`, `porch` made without its porch, `airlite`, `newbuild`, `stonetwin`, `siding`; Round 184: `univcity` made without its porch, `chestnut`, `manayunk`, `loft`, `mixeduse`, `rittenhouse`), none with a painted awning or canopy (the page builds them), plus 25 square tower tiles (`TILES`: glass, dark glass, precast, Art Deco, brick, concrete balcony slab, silver fins, black grid, brick office, glass balconies, and since Round 184 gold glass, green glass, ribbon windows, brutalist, limestone, marble, terracotta, blue bands, unitized, hotel, granite, white fins, dark brick, metal panel, grey grid; 1024, four floors by ten bays), into `lidar_cache/fronts_raw/<set>/` (kept unless `--force`). `bake_fronts.py` cuts each set into a 4 by 4 atlas of 384x768 cells with an 8 px edge gutter (WebP, and a phone's copy at half), a half-size mask atlas (r glass, g a number per window, b the door) from its window finder (dark neutral glass at 384x640, a 1 px close, shutters as narrow boxes against a sash, green never glass, the door the tallest dark opening in the lowest third), each cell's cornice colour and ground-floor span (`gf`, what an awning covers), the shop glass marked in the mask (b 128), each tower tile cropped to whole bay and floor repeats with cross-faded edges and sized in metres (`bake_tile`, written at 640 and a phone's 320); every image goes to `art/fronts/` and `art/tiles/` through `art_files.py` (Round 184), never into the json; `--placeholder` draws stand-ins for engine work, `--partial` skips a set with no fronts yet, `--preview DIR` writes each front with its boxes. |
| `fronts.json` | Inlined as `FRONTS_DATA` (Round 184: the paths of the atlases under `art/`, not the images): the atlases, masks and cells 'Fitting the house fronts' lays near the eye (`frontNote` from the core, outer-district and far-ring loops, `frontSetOf` by the record and, for the six Round 184 sets, by place in `FR_AREAS`, `frontSide`, `frontsLay`, instanced fronts a set and shared cornices, stoops, awnings and porches; a set's atlas loads the first time one of its houses is near and the least recently wanted are let go past `FR_KEEP`, eight on a computer and four on a phone, `frontSetDrop`), and the tower tiles 'Cladding the towers' lays (`towerSkinNote`, `TOWER_TILE_OF`, `TOWER_TILE_ALT`); `__dbg.fronts()`, `__dbg.frontNear(x, z, set)` and `__dbg.frontsRadius(r)`. |
| `fetch_tree_art.py` / `bake_tree_art.py` → `tree_art.json` | The street trees as their species (Oct 12): `fetch_tree_art.py` asks OpenAI's image API (`gpt-image-1.5`, 1024, medium, transparent background; `gpt-image-2` refuses transparency on this account; the key only in `~/.config/philly3d/openai.env`) for 28 looks (`LOOKS`, the inventory's commonest species and a broadleaf for the rest; Round 184 added magnolia, dogwood, serviceberry, silver maple, Crimson King, sycamore, river birch, willow, spruce and holly) by view (`side`: the whole tree level from far off; `top`: its crown straight down, as an aerial map shows it) and season (summer, autumn and winter, and spring for the eight that flower; the pine, spruce and holly summer only): 172 images into `lidar_cache/tree_art_raw/<look>/`. `bake_tree_art.py` keys a winter image's haze (the model fills the gaps between twigs with opaque pale haze: `dehaze` keys the crown on darkness and spares the trunk's column), crops, fits each into a square cell (side 320 standing on its foot, top 160 centred), bleeds its colour into the clear pixels, firms its alpha, records its framing (`hf`, `ar`, `df`) and maps every species onto a look (`LOOK_OF`, `speciesLook`), each image to `art/trees/` with a phone's half (`art_files.py`). `--preview DIR` writes each on a sky colour. |
| `tree_art.json` | Inlined as `TREE_ART`: the looks, the images' paths under `art/trees/` by look, view and season, and `speciesLook`. 'Planting the street trees' draws a tree as one card (`TREE_ART_VERT`, `treeArtPatch`) when it is present; `?trees=lowpoly` keeps Round 58's crowns. |
| `fetch_ground_art.py` / `bake_ground_art.py` → `ground_art.json` | The ground's textures (Round 183): two straight-down photographs from OpenAI's image API (`gpt-image-2`), a mown lawn and a rougher verge about 6.5 m across, made to tile by the bake (a blend with a half-rolled copy across, then down) and stored as WebP; Round 184 added the streets' three (asphalt, concrete slabs, herringbone brick), the patterned two cropped to whole repeats by autocorrelation instead of blended (`periodic`), each tile's size in metres in `m`. Every image goes to `art/ground/` with a phone's half. Inlined as `GROUND_ART`; `loadGroundArt` swaps the lawn and verge in for the painted meadow tile, toned to its mean (`?ground=painted` keeps the painted tile), and hands the streets' three to `surfTexPatch` (`uAsph`, `uConc`, `uBrick`, `uStScale`: on the street grid's axes, chosen by the surface's own colour, a ratio to the texture's mean; `?streets=plain` keeps them off). |
| `fetch_vehicle_art.py` / `bake_vehicle_art.py` → `vehicle_art.json` | The vehicles' views (the realism pass, Oct 12): OpenAI's image API (key from `~/.config/philly3d/openai.env`, never printed), `gpt-image-1.5` on a magenta key for the six car kinds' side, plan, front and rear views and the transit fleet's sides and fronts (the SEPTA bus and trolley, Amtrak's ACS-64, Acela and Amfleet, PATCO), `gpt-image-2` for the container stacks, raw into `lidar_cache/vehicle_art_raw/` (gitignored). The bake keys and crops them, takes each vehicle's 40-station profile and its wheels from the side view, and packs the cars' and the transit fleet's atlases with lossless masks (R paint, carried over the panel gaps; G glass; B lamps) and the container tiles into `art/vehicles/` through `art_files.write`, each with a phone's half. Inlined as `VEHICLE_ART`; `vehLoft` lofts the bodies from the profiles, `carArtMaterial` / `transitArtMaterial` wrap them (`?vart=0` keeps the boxes). |
| `fetch_street_furniture.py` / `bake_street_furniture.py` → `street_furniture.json` | OpenStreetMap's traffic signals, stop signs, signalised crossings, fire hydrants, benches and waste baskets over the city's box (the realism pass): Overpass (overpass-api.de first) in 3 x 3 tiles cached in `lidar_cache/furniture_tiles/`, then into the scene frame at 0.5 m inside the city line, signal nodes within 22 m merged into one junction, a signalised crossing with no junction near kept as a mid-block signal. Flat [x, z] lists per kind (about 141 KB, ODbL), inlined as `STREET_FURN`; the page stands a signal pole on every corner of a junction from the traffic runs that end there, the stop signs, SEPTA's stop poles, hydrants about every 95 m where the map has none, inside the half-mile rule (`?furniture=0` off). |
| `tests/test_realism_vehicles.py` / `tests/vehicles_checks.js` / `tests/vehicle_lamps_gpu.html` | The realism pass's vehicles: the manifest, the lofted cars' sizes and budgets, the parked rows (both kerbs, clear of every moving lane, the hydrants' gaps, the half-mile rule), the furniture's corners, the lamp share, the headlights' pools on the paved surfaces only, the shades and the traffic's far copies, run under Node over the real traffic section (`vehicles_checks.js`); the GPU page draws the production lamp shaders on a real GPU (floor-size lamps keep their light, heads face front and tails back, a far signal's lens dark by day). |
| `fetch_wall_art.py` / `bake_wall_art.py` → `wall_art.json` | The walls' and pitched roofs' materials (the realism pass): nine straight-on wall photographs (brick red, dark and painted, render, limestone, Formstone, marble, granite, concrete), four roof surfaces (architectural shingle, slate, standing-seam metal, three-tab) and a fresh roof snow from OpenAI's image API (`gpt-image-2`, key in `~/.config/philly3d/openai.env`, raws in `lidar_cache/wall_art_raw/`). The bake cuts each coursed one on its own joints (`course_tile`), tiles the rest, packs a 3 by 3 and a 2 by 2 padded atlas with each kind's mean and metres per tile, and writes them with a phone's half to `art/walls/`. Inlined as `WALL_ART`. `loadWallArt` hands them to the facade hook (`wallArtU`); the walls' atlas, its GLSL (`FAB_WALL_FN`, `fabWallKind`) and the landmark rebuilds' triplanar stone and brick (`landmarkDetail`) are a computer's only (`WALL_ART_DEV`; `?walls=plain` off), the pitched roofs' everyone's (`?pitched=plain` off), and the snow loads the first time it lies (`facadeFrame`). |
| `bake_landmask.py` → `land_mask.json` | The ground's land mask (the realism pass, Oct 12; the review's fixes Oct 13). One RGB picture over pack_city.py's CITY box at 20 m a texel, built only from files the build already ships. R is built up: footprints from wide.b64, city.b64 and outskirts.b64 drawn at 5 m, averaged and blurred, and taken out of parks. G is woods: the PPR parkland rings from nw_parks.json, plus big-park interiors away from roads and buildings where trees.b64 finds few trees (inside the city line only, because the survey stops there), plus a share of the unbuilt ground past the city line. The edges are blurred and broken by a seeded noise. G is exactly 0 on any texel a water ring touches (the scenes' kind 1 areas, nw_water.json, schuylkill.json, delaware.json) or an open Amtrak or PATCO track (rail_amtrak.json, patco.json), drawn at 5 m and grown by one 5 m pixel; the wood field plants nothing on a zero. B is river bank: 1 at the Schuylkill's and the tidal Delaware's edge, 0 by 60 m inland. There is no alpha, because a browser may premultiply by it. Written lossless to `art/land/` with a phone's half through `art_files.py`. `python3 bake_landmask.py preview.jpg` writes the channels side by side. It is a pipeline.py stage (bake_landmask), so re-run it after any repack of the tiers, the trees, the rivers, the water or the rail. |
| `land_mask.json` | Inlined as `LAND_MASK`: the mask's paths under `art/land/` and its box. `loadVegArt` loads it linear, clamped and unflipped into `vegU.uLand`. `surfTexPatch`'s realism part (`vegGrassGLSL`, `vegAfterGLSL`) lays yards and alleys on built-up ground, the forest canopy in the woods, and the bank and tide band at the rivers. On a computer the wood field reads G and B back once (`woodAt`: bilinear for density, null on a zero texel). Off under `?real=0` and at TIER 2. |
| `sidewalks.b64` | The outer districts' sidewalks baked by `bake_sidewalks.py`. Int32 header 'SHWW' 0x53485757, nRings, version 1, 0; then int16 per ring: n, kind (5 concrete, 6 brick), x0 and z0 in 0.2 m units, and n - 1 deltas. Every band a city street carries (half width plus 4.0 / 3.5 / 3.2 / 2.8 m by class), filled to the facades where a strip under 5.2 m was left, minus the carriageways, footprints, water and the core's box. Rings are cut only at the bake's 400 m tile edges: 72 m across at the median, 150 m at p90, none over 400. 12,192 rings and 266,264 points, about 5 km2, 1.49 MB base64 (2026-10-12). Laid under REAL by 'Paving the sidewalks' (swGeometry, straight into typed arrays): a computer lays all of them at load in 57 squares of 1,200 m; a phone lays the 200 m squares within NEAR_R as the eye moves (updateStreets), each ring fading out over the circle's last 220 m (swFadePatch); a LITE build lays none. The tuft field tests the rings in this form (sidewalkAt). |
| `bake_sidewalks.py` → `sidewalks.b64` | *shapely.* Reads `wide.b64` itself (the streets and footprints exactly as the page draws them), `overpasses.json` (a street a deck owns is not at grade), the water (wide.b64's areas, `schuylkill.json`, `delaware.json`) and `places.json`'s historic districts, plus the Queen Village and Washington Square West boxes, for the brick. Per 400 m tile with a margin: the base band; a morphological closing with the footprints (2.6 m out and back, kept within 6.5 m of a kerb); less everything that is not sidewalk; cut to the tile; simplified (`--simplify`, 0.25 m by default) and snapped to 0.2 m. Parts under 2 m2 are dropped, holes split away, and every ring written simple and CCW. |
| `fetch_street_art.py` / `bake_street_art.py` → `street_art.json` | The streets' generated textures (the realism pass, Oct 12): seven images from OpenAI's image API (`gpt-image-2`, quality high, key from `~/.config/philly3d/openai.env`, raw in `lidar_cache/street_art_raw/`). They are three straight-down single lanes, an elevated road's concrete side, the El's riveted girder, a main-line track with ties, and a lot's asphalt. The bake makes each tileable, stacks the three lanes end to end into one lane-wide strip (14.175 m a repeat), finds the ballast's two rails and crops it to whole 0.6 m tie pitches. It writes WebP with a phone half copy to `art/streets/`, and each image's linear mean and size in metres to the manifest. Inlined as `STREET_ART`. `loadStreetArt` hands them to `lanePatchReal` (`uLaneWear`), `deckWallPatch` (`uConcWall`, `uElSteel`), `ballastPatch` and `lotPatch`. `?streets=plain` keeps them off; steel and ballast load on a computer only. |
| `fetch_water_art.py` | Generates the water's textures (the pier deck's concrete, white water) with OpenAI's image API (gpt-image-2, high, 1024) into `lidar_cache/water_art_raw/<id>.png` plus sidecar json. The key comes from OPENAI_API_KEY or `~/.config/philly3d/openai.env`, never printed; `--force`, `--only`. |
| `bake_water_art.py` | Makes the water textures tile (the deck cropped to whole slab repeats and cross-faded, the foam half-roll blended) and writes them through `art_files.write` into `art/water/` with a phone half copy, plus `water_art.json`. |
| `water_art.json` | Manifest of the water art (pierdeck, foam, their half copies, metres per tile, linear means); build.py inlines it as `WATER_ART`; the page loads the files on demand via `artImage(artSrc(...))`. |
| `art/water/` | The generated pier-deck and white-water WebPs (full and half), named by content hash; loaded on demand, never inlined. |
| `pole_families.json` | Each packed pole's family, 2 bits a pole in `poles.b64`'s own order (0 cobra head or davit, 1 post-top lantern, 2 wood or alley pole, 3 other, drawn as 0), from `bake_pole_families.py`; the page ignores it when its count is not `poles.b64`'s. |
| `bake_pole_families.py` | `lidar_cache/phl_poles_raw.json` + `poles.b64` → `pole_families.json` (nearest surveyed pole within 2.5 m; rerun after any `pack_poles.py`). |
| `tests/test_realism_post_shadows.py` / `tests/shadows_gpu.html` | Realism pass, post and shadows: runs the far map's rewrite of r149's light loop on the vendored three (the sun reads both maps, the black light is never lit, a third light still is, radius 2 shades the near box too). Under node against stubs it runs shadowRoles (late meshes, held casters, a flat made at night, the apron's pin, a phone), keyWeather and moonShadowsOff (the reasons, the idle sweep, the return re-aiming the map, the clear sky's fill with the sunlit level kept, a phone's fog untouched), aimSun (the light follows sunDir while idle and no map is drawn), and the far map's turn (a time-lapse gives it frames, the outer casters leave the near map high up, a new size, a moving box waiting a second). It also pins the flags, the occlusion's floor and the phone grade's hook. The GPU page draws the far map and a tree card into a sun's map. |
| `art_files.py` → `art/` | Round 184 (Mike: load the generated art on demand): the bakes' shared writer. Every image is a file under `art/<kind>/` named by the first 10 hex of its sha256, so a file never changes under its name; `prune` removes a kind's files the bake did not write this time. The page loads them by relative path (`artImage`, `artSrc` picks a phone's half), `build.py` refuses a manifest naming a missing file or still holding a data URL, `deploy_philly3d.sh` ships `art/` before the page and never deletes on the box, and the app's `copy-web.mjs` copies it into `www/art`. |
| `wide_walls.b64` | The Mapillary wall colours and facade hints for the outer districts (magic 0x53485457): the 32-entry sRGB palette, then one palette-index byte per `wide.b64` building record, then one facade hint byte per building from the same block face (the fourth header word is the bytes per record, 2; 0 was the one-byte layout), trim class in bits 0-1 and window class in bits 2-3 (the fraction of the kept pixels that are light or dark in the imagery, classed by `bake_wall_colors.py`), 0 for a building without a colour. Decoded beside `wide.b64` by "Raising the outer districts": a building the imagery has seen takes its block face's colour instead of a palette draw, and the hint steers `fabricStyle` (siding, cornices, dark trim, new construction). |
| `fetch_boundary.py` → `city_limit.json` | *venv.* The city line from OSM relation 188022, buffered 2 km into the flight limit; the raw relation is cached in `lidar_cache/phila_boundary_raw.json`. |
| `fetch_city.py` → `osm_city_raw.json`, `dem_city.json`, `city_tiles/` | Resumable tiled fetch of the rest of the city: boxes A–D plus `river-wards` (Round 36) and `nw-gap` (Round 40) (`fetch_city.log`). Its tile cache is keyed by tile NAME, not by query, so widening the query means deleting `city_tiles/` and refetching 510 MB. |
| `fetch_city_streets.py` → `city_streets_raw.json`, `city_streets_tiles/` | Round 87. The street classes `fetch_city.py`'s query never carried (`unclassified`, `living_street`, `pedestrian`), over the same boxes, as a supplement rather than a wider query on that 510 MB cache. In Fairmount Park those are the connecting drives, and without them the far ring carried 68 per cent of the park's road length against the wide tier's 90 and a quarter of its run endpoints dangled in the grass. Uses `out geom` (no node recursion: minutes a tile became seconds); `pack_city.py` merges it, and degrades to the pre-Round-87 class list when the file is absent. |
| `fetch_dem_nw.py` → `dem_nw.json` | 50 m NED over the NW hills, border pre-feathered to dem_city. |
| `process_osm.py` | Raw Overpass JSON → a scene json in local metres. `SHT_DIR` / `SHT_RAW` / `SHT_OUT` env vars pick the folder, input and output; it produced `scene.json`, `scene_wide.json` and `scene_south.json` (`process_wide.log`, `process_south.log`). Normalises outer rings CCW (`ensure_ccw`). |
| `scene_wide.json` (21 MB), `scene_south.json`, `parts_wide.json` | The wide / south extracts and the OSM `building:part` skyscraper pieces: inputs to `pack_wide.py`. `report_wide.json` / `report_south.json` are their process summaries (counts, bounds, the towers' OBBs). |
| `pack_wide.py` → `wide.b64` | Packs scene_wide + scene_south + parts_wide; drops anything *touching* the core (`touchesCore`), `simplify_open` for roads, `BRIDGE_SKIP` handled in the app.  Stacked building:part ways on one footprint (centroids within 2.5 m, areas within 20 %, overlapping heights) keep only the tallest, since coincident prisms z-fight. |
| `pack_city.py` → `city.b64` | *venv.* Packs `osm_city_raw.json` with shapely block-strip merging; requires `lidar_city_heights.json`. |
| `pack_outskirts.py` → `outskirts.b64` | *venv.* Packs `osm_outskirts_raw.json` at 1.0 m with a 3 m row bridge (detached houses fuse into rows); skips anything an older fetch box owns; no LiDAR / OPA / roof join. |
| `fetch_footprints.py`, `lidar_join.py`, `lidar_core.py` | The 2022-LiDAR true-massing pass (Round 13): the City's footprint layer with LiDAR `max_hgt` → `lidar_cache/phl_footprints_local.json`; `lidar_join.py` (*venv*) patches the scene jsons in place and emits `lidar_city_heights.json` (Round 160: a City footprint whose `max_hgt` the point cloud contradicts, a flat LiDAR roof from `lidar_city_roofs.json` over half of it and `approx_hgt` agreeing with that roof, is a confirmed spike and contributes `approx_hgt`, places of worship excepted; `lidar_report.json` lists them under `confirmed_spikes` and `spike_released`); `lidar_core.py` (*venv*) derives core roof forms from the COPC point cloud. |
| `lidar_city_heights.json` | `{OSM way id: measured h}` for the far ring; `pack_city.py` requires it. |
| `lidar_report.json` | LiDAR pass validation: coverage, histograms, known truths, top deltas. |
| `fetch_opa.py`, `opa_join.py`, `roof_colors.py`, `patch_scenes_facade.py` | Tier-1 facade pass (Round 15): OPA parcel table → per-building use / material / era / stories; ortho-sampled roof colours → `facade_palette.json`; both written into the scene files as `fa` / `rp`. `opa_join` and `roof_colors` are *venv*. |
| `fetch_trees.py` / `pack_trees.py` | PPR tree inventory → `trees.b64` + `tree_names.json`. Citywide since Round 87 (151,726 rows against the wide box's 50,073); the per-page cache in `lidar_cache/tree_pages/<env hash>/` is keyed by envelope so a widened box never reads the old box's pages back. |
| `fetch_poles.py` / `pack_poles.py` | Streets Department poles → `poles.b64`. |
| `fetch_places.py` / `bake_places.py` | Historic districts + neighborhoods → `places.json`. |
| `fetch_patco.py` → `lidar_cache/patco_raw/PATCO_GTFS.zip`, `lidar_cache/patco_raw/osm_patco.json` | PATCO's public GTFS (the permalink its developer page links, National RTAP) and the Overpass `railway=subway` ways PATCO operates between 8th and Market and Broadway (`out geom`), plain python3, a generic User-Agent. |
| `bake_patco.py` → `patco.json` | Plain python3 (stdlib, zipfile): the two main tracks stitched by shared end nodes (service ways dropped), 1.5 m simplified per way, cut to 150 m past 8th and Market and Broadway, the stops projected on, the portal-to-portal run; the trips reduced to the bridge-crossing minutes; `calendar.txt` then `calendar_dates` then the swap-day repair; prints the chains, the flag changes and the headways over the span. Warns, never fails, once the feed has ended. |
| `bake_i95.py` → `i95.json` | Plain python3 (stdlib): the motorway ways of `osm_city_raw.json` whose ref names I 95 (not the links), stitched by shared end nodes into chains in the direction of travel and simplified to 2 m; prints the chains, the km and the extent (Round 148: 182 ways, 4 chains, 59.5 km, from past the airport to Bucks County). |
| `bake_rail.py` → `rail_amtrak.json`, `lidar_cache/rail_amtrak_raw.json` | Overpass, plain python3 (a stdlib Douglas-Peucker): the Amtrak-operated `railway=rail` ways over the far-ring box, service and industrial ways dropped, tunnel/covered and bridge flags kept, projected with `philly_frame.py`, clipped and simplified; prints the track km and the nearest line's distance to 30th Street, North Philadelphia and Overbrook (3, 6 and 15 m). `--force` refetches. |
| `fetch_landmarks.py` / `bake_landmarks.py` | The City basemap's `Landmark_Poly` (9,202) and `Landmark_Points` (1,147) → `landmarks.json`: archived, non-public and neighborhood rows dropped, utility, industrial, plain retail, housing and parking subtypes dropped, the rest classed by SUBTYPE (`TYPE` is a small integer and `LABEL` a Y/N flag in the city's file); the site key is NAME else PARENT_NAME, a parent's spot the area-weighted mean of its parcels' centroids, a recurring name a new site past 400 m, largest first so the app's dedupe keeps the biggest. `bake()` is pure (`tests/test_landmarks_bake.py`). |
| `fetch_markers.py` / `bake_markers.py` | The PHMC historical markers in Philadelphia County (data.pa.gov Socrata `xt8f-pzzz`, public domain) and the City's `Percent_for_Art_Public` layer → `markers.json`: types by name, the year from the dedication date, the state's ` - PLAQUE` suffix stripped, two markers on one spot 2 m apart; artworks only when Active, the 40 m buffer polygon's centroid, a material scan of the medium, the image link only on the city's S3 bucket; every string cleaned (dashes, whitespace, no `</script`); a point inside one of the page's building footprints (`scene.json` polys plus `wide.b64` and `city.b64` decoded through `tests/_common.py`) is stepped 2.5 m out past the nearest wall (`FootGrid`). `bake()` is pure (`tests/test_markers_bake.py`). |
| `fetch_septa_stops.py` / `bake_septa_stops.py` | SEPTA's GTFS release (`github.com/septadev/GTFS` releases/latest, about 22 MB, cached in `lidar_cache/septa_raw/`) and the Arrivals API's station list → `septa_stops.json`: every bus and trolley stop (route types 3 and 0; the subway stays out) inside the flight limit with its GTFS stop id, name without the near/far-side suffix and the routes serving it, and every Regional Rail station inside the limit under the name the Arrivals API takes (matched on stop id). 0.5 m units. Round 133. |
| `septa_stops.json` | The stops and stations above: `{bus: {id, x, z, n, r}, rail: {id, x, z, n}}`, inlined as `SEPTA_STOPS` (8,469 stops, 64 stations, 432 KB). |
| `fetch_civic.py` / `bake_civic.py` | The Free Library's 54 branches (`library_locations`) and Parks and Recreation's recreation and older adult centers (`PPR_Program_Sites`, the pools left out) from the City ArcGIS, cached in `lidar_cache/civic_raw/` → `civic.json`: name, address, zip, phone and branch page for a library; name, kind and gym flag for a center; a point inside a drawn footprint stepped 2.5 m out past the wall with `bake_markers.py`'s `FootGrid`. No hours: none are published as data. Round 134. |
| `civic.json` | Those branches and centers, `{lib: [[x, z, name, address, zip, phone, url]], rec: [[x, z, name, kind, gym]]}`, inlined as `CIVIC_DATA` (16 KB). |
| `fetch_markets.py` / `bake_markets.py` | The City's `Farmers_Markets` layer (ArcGIS, one page) → `markets.json`: hours `HH:MM` to minutes (an end at or before its start gains twelve hours: the feed's `01:00` is one in the afternoon), the season from month names (day 1 and the month's last day when the day is missing; `Yes` for year round; no months at all means open all year by weekday), the `Yes` payment flags, websites normalised, dashes to commas. `bake()` is pure (`tests/test_markets_bake.py`). |
| `fetch_lights.py` / `bake_lights.py` | BOMA Philadelphia's Building Illumination Calendar (Squarespace, `?format=json`, every page) → `lights.json`: the colour words of each title in order (aliases folded, a rainbow expanded), a team or cause keyword when the title names none (Go Birds is green), names stripped of the lighting clause and the (Copy) suffixes, dates as Philadelphia calendar days, duplicates collapsed, rows older than a year dropped. `bake_lights.py --fetch --out` is the VPS mode (the concerts writer, the previous file kept on a bad answer). `bake()` is pure (`tests/test_lights_bake.py`). |
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
  - `?dpr=N` pins the adaptive pixel ratio (default: adaptive, capped 1.75 desktop / 1.25 touch, floored 0.9 / 0.72;
    `__dbg.dpr()` shows the ladder, the open trial and the beacon fields).
  - `?wx=clear|overcast|fog|drizzle|rain|downpour|storm|hail|snow|blizzard|sleet` pins the
    weather (the live Open-Meteo fetch is skipped).
  - Depth (Round 192): reversed-Z float depth is the default wherever the probe grants it (`ZPROBE`, `zcField`, the `zc`
    beacon field); `?zbuf=log` forces r149's logarithmic depth (the fallback every device without `EXT_clip_control` gets),
    `?logdepth=0` is still plain 24-bit depth (z-fights on the tower skins), `?cloudz=old` keeps the cloud deck writing its
    depth everywhere; `__dbg.zbuf()` reports the mode, the probe, the blit, the guard and the deck's programs, and
    `__dbg.cloudRects(false)` turns the aircraft's rectangles off (the spike's planes drawn over the clouds, for an A/B).
    `?zbuf=rev` overrides the two holds (the crumb a failed float target leaves, `philly3d.zbuf`, a fortnight; an Android
    phone, unmeasured); `?mirz=0` or `__dbg.mirz(false)` draws the river mirror's point sprites without their twins (the
    review's must-fix, for an A/B; `__dbg.mirz()` also says what the warm-up built, `warm.n` points and `warm.programs`);
    `?bolts=0` or `__dbg.bolts(false)` stands a storm's synthetic bolts down, so two storm captures can be compared.
- **Deploy:** `./deploy_philly3d.sh` ships philly3d.com; `git push` ships GitHub Pages. To
  check Pages is live, grep the *whole* page or its tail: app.js sits after ~20 MB of data,
  so a first-120 KB range check always reports stale.
- **Headless verification:** the pane runs no rAF even when fronted. Drive frames with
  `__dbg.frameOnce()` bursts, render twice before a capture (screenshots lag one presented
  frame), and dispatch synthetic pointer events as down *and* up on the canvas.
- **Parity sets** (Round 192's second review; the capture skill's 7d has the long form): turn `btnTraffic` and `btnShips`
  off in every pose, and `btnFlights` unless the pose holds a test aircraft (the typical traffic's reconcile runs every 1,000 ms of REAL time, so a faster build spawns its cars
  elsewhere even where main matches itself exactly; and ships still arrive over the aisstream WebSocket when Chrome's
  `setBlockedURLs` blocks `ais.json`); stand a storm's bolts down (`?bolts=0`, main patched alike); a weather preset eases
  per frame (tau 1.8 s at dt 0.05), so a pose that tests the cloud switch must hold the eye relative to the current drop,
  not at a fixed height; take the second main run (the noise) from the same session, since a live feed that lands in one
  run and not the other (the air, the weather) moves a whole sheet; and keep the night water poses (`poses-nw`, with the
  held helicopter's lights over the Delaware and Boathouse Row at 0.35 m) in any depth parity set.

## Architecture (app.js)

One IIFE, top to bottom, with `// ------- banner` comments you can grep for. In order:
`config` (TOWER, COLORS) → `dom` → `helpers` → `lighting & sky` → `data-driven build` →
`overpasses` → `living water` → `terrain` → `ground, water, roads, parks` → `the city fabric`
→ `landmark spires` → `researched landmark models` → `museum ships` → `the three towers` →
`the outer districts` → `the far ring: the rest of Philadelphia` → `trees` / `street trees`
→ `labels` → `controls` → `modes & viewpoints` → `live SEPTA transit` → `layers panel` →
`street names` → `places` → `address search` → `live Indego bike share` → `live flights` →
`live ships` → `traffic` → `streetlights` → `skyline lights` → `solar clock` (and the weather) → `build & loop`.

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
  sharing `cityMat`, plus outer roads, parks/water, the Ben Franklin Bridge (Round 66: trusses
  over the roadway, latticed towers, granite portals, stored-dark blue measured through the
  pipeline), tall labels.
  Far ring: `CITY_B64` into 2,400 m chunks, 100 m ground strips, far roads, district labels.
  **All three load on phones** (Round 7 removed the old touch skip); touch instead keeps DPR
  ≤ 1.25, 2048 shadow maps, half the wide forest, no pole meshes and no deck shadows.
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
- **City Hall (Round 191):** under the realistic look `buildCityHallReal` builds the measured building (the `CITY_HALL`
  table, in its own frame: `B0`, U along `fl.n`, V along `fl.d`) in 'Raising the outer districts' at Round 81's place, so its
  one themed slot (`chSlot`) is taken where it always was and its bronzes (Penn, the four eagles, the four groups) ride the
  themed mesh; `?real=0` runs Round 81's block untouched (`cityHallFloodPatch` and `hallMat` as they were). `chModel` makes
  two levels in one buffer format (positions in the frame, the cell's own uv or metres, `aK` the cell or minus a kind,
  `aCol` four bytes): the near (about 25k triangles: walls laid cell by cell on the atlas, cornices as extruded profiles,
  dormers, the measured columns, the portals' passages, the turrets, the apse, the mansards and crowns, the tower's stages,
  the dome's octagonal lathe, the lantern) and the far (about 5.8k with its floor and the glass houses: the same plan in
  boxes and two-step roofs, the centre crowns, shoulders and aedicules, the corner pavilions' great dormers, the wings'
  dormers and the flanks' trim as the near level has them, its floor in two colours); one program for both (`chMaterial`: the atlas, the mask's glass and rooms, the slate's generated texture, the
  decks' generated tar, the coffered vaults, the setts, the beaded trim, the glazing bars, the weathering by height, the
  rain, the lamps, `wxSurfacePatch` patched in (never `userData.wxSurf`: that marks a flat on the ground and keeps it out
  of the river's mirror), `cityHallFloodPatchReal`), the balustrades' and the cresting's sky cut in it on their own cell
  and in their shadow by `chCutDepth` (fix2 folded fix1's second program back: under the log depth buffer every program
  writes gl_FragDepth, so the split bought nothing), the dials apart (`chDials`, hands to the model clock, their sphere
  taken after the hands), the courtyard and apron one canvas and the compass another (`chFloor`, `chCompassCanvas`, its
  pavers and granite slabs laid by the shader). A passage's part carries its shade under 1 in `aCol`'s fourth byte: the
  shader multiplies the indirect light by it, keeps the facade's flood off it and lights it with its own lanterns at night.
  The ground (fix2): NED had a 2.7 m pit in the courtyard and the fronts 0.4 to 0.7 m low, so under the realistic look
  `demAbs` takes `CH_GRADE`'s plane fitted to the LiDAR's ground round the walls, eased back to NED by 40 m, and the
  building stands on the measurements' datum, `CH_GRADE.datum - DATUM`; its faces run 1.2 m under it (`foot`, the picture's
  foot row) to meet the ground, the courtyard is laid flat at `CITY_HALL.court0`, the passages run level from the pavement
  to it and end in a wall with the bay's small arch (the north one in the apse's door). Fix1's rules: every face is wound to the normal it is
  handed (`b.tri`), and a face's outside is on the right of its walk (`face(A, B)`, a ring walked counter-clockwise from
  above); a profile that starts in from a wall gets a ledge back to it (`hipRoof`), a stage narrower than the one under it
  a ledge (`ledge`), an overhang its soffit; `tests/test_landmark_cityhall.py` casts rays from round the building and fails
  on any first hit that is a back face over 60 m, or on more than 0.1% of them anywhere. `cityHallStep` picks the level
  by the eye's distance from the box (`CH_NEAR_R` 400 m, 420 on a phone, 40 m hysteresis) and loads a phone's art within
  `CH_ART_R`; tier 2 draws the far level alone and takes the half art within `CH_NEAR_R`. City Hall's outline was dropped
  at pack and its tower's parts go with `BRIDGE_SKIP`; the outer districts' loop skips Dilworth Park's café (`CH_CAFE`,
  OSM's footprint drawn as a three-storey house) and its two headhouses (`CH_HEADHOUSE`, building=roof canopies drawn as
  beige boxes) and `chCafe` builds them as the glass they are. The loop has a `CH` of its own (the chunk size), so the
  landmark block there names no City Hall state: `chBuildSafe` builds it and, on a throw, takes back its meshes, themed
  parts and ground claims and lets Round 81's block stand. `REBUILD_OCC` holds its wings, the café and the headhouses;
  `__dbg.cityHall()`. Fix3 (the third review): the dials' frame is `chDialFaces` (a face's right as a viewer outside sees it is
  (nv, -nu); the test turns the hands to 15:00 on every face); the water table and the faces' feet are the base course's
  granite tile (`vG`), its head 0.12 m under the front's lowest sill (`waterTop`, the bake's `sill`); a passage's direct light
  goes with its shade (no shadow-map leak inside), its walls are the vestibule's picture (`vest`), with red granite columns,
  ribs and lanterns, its floor a border and a diagonal field (its width rides the floor's seed); the glass kinds (13 the
  lantern's and the skylights', 14 the pavilions' with 3 m mullions) take the daylight through them by Fresnel's share,
  a stronger sky reflection and at night a lit interior, their bars dark steel, never the flood; the bronzes and the
  apron's statues are forms (`CHS`: shells, tubes, blobs, lathes; `chPennForm` 3.3k triangles, `chGroupForm` 2.4k,
  `chEagleForm` 0.7k on the themed mesh; `chHorseForm` and `chStandForm` in the near level's bronze, `CH_STATUES` from
  OSM's nodes), the groups on the tower's own pedestals (`CH_PED`); `chDress` adds the courtyard's lamp posts, turret
  lanterns, areaway railings and the north apron's bollards (a phone keeps the lamps); Dilworth Park's café at the plaza's
  north-west corner (OSM way 333931838) is a third `CH_HEADHOUSE`; a phone paints the floor's canvases on its first near frame
  (`CH.floorPaint`); the pins' depth image and the building tap draw the far level in the near one's place
  (`userData.occStandIn` in `occRender`).
- **The Irish Famine Memorial (Round 197):** under the realistic look 'Restoring the landmarks' calls `famineBuild` at
  Mike's place and heading (`FAMINE.c` 84, 104, the long axis with Spruce Street, the famine at the west end, the bow east);
  `?real=0` builds Round 129's block untouched and no flag. `famineForms(lo, far, ground)` lays every part in the memorial's
  own frame (u with Spruce Street, v toward it, y over the plinth's foot): the plinth's flat granite panels round
  `famOutline`, the dark paved circle on the ground (`ground` is `drapeY` there), the planked hull (`famGun`, `famDeck`,
  `famBow`, `famPlan`, `famSect`), the gangway (`FAM_GW`), the rock (`FAM_ROCK`, kept on the plinth), the cross, the luggage
  and the people (`FAM_FIGS` through `famFigure`, CHS's forms: thirty-one and four children); `famPoleForms` the pole;
  `famMerge` one indexed buffer of float position, normal and `aFm` (the kind, the cavity, the kind's two coordinates). One
  program for both levels (`famMat`, `famU`: the bronze's patina, metal and grain, the granite, the paving, the pole; Round
  184's floods and the pole's wash after dark), near and far meshes switched in `famineStep` (`FAMINE.nearR` 250 m, 30 m
  hysteresis, a depth pass asked at each switch); the flag is its own mesh (`famFlagGeom`, `famFlagMat`: the cloth's shape
  in the vertex shader, its heading eased to `WX.windX/Z`, its wave on `waterU.uTime`, never a shadow caster). The trees are
  kept off the plinth and 2.4 m off the pole (`registerPoly`), the tufts off the paved circle and the drum (`noSow` and
  `REBUILD_PAVED`, which the park's sow reads), the walker off both (`addColSeg`). `__dbg.famine()` ('near', 'far', 'auto'
  pin the level); `tests/test_remodel_famine.py` builds the forms under Node.
- **Terrain:** `demAbs()` samples the DEM grids (datum: the towers' site at 8.34 m ASL stays
  y = 0); `siteY(x,z,'ground'|'road')` is the one function everything sits on. East of Front
  St the I-95 trench drops to −8 between `TERRAIN.trenchW/E`, Penn's Landing shelf −6.5…−7.5,
  water −10, shoreline = `SHORE`, existing plaza caps in `CAPS`. Penn's Landing is a
  separate `CAP_SITE` construction model with elevated girders, partial decking and
  a fenced bare yard; it must not restore the future lawn in `siteY`. Outside the core low terrain clamps above
  the water plane except east of `DEL_BANK` / inside `riverCorridor` (Schuylkill polyline).
  Each packed ring pre-scans its own water polygons (`wxWaterGrid`) and refuses any footprint
  whose centroid stands in rendered water, so nothing floats.
- **Overpasses:** `OVERPASSES` (bake_overpasses.py) drives deck ribbons, parapets, piers, the
  Vine Street cut and sunken ramps; `ovpOwned` suppresses the packed flat ribbons underneath,
  `ovpDeckY` lifts buses, labels and traffic; `BRIDGE_DECKS` registers the two custom river
  spans' real deck profiles.
- **Layering (z-fighting):** flat surfaces use the `LAYER` constants (park .06 / plaza .10 /
  sidewalk .16 / road .24 / footway .32 / pools .38), every ribbon gets a deterministic few-cm
  lift, and the renderer runs reversed-Z float depth (Round 192) or, where that is refused, `logarithmicDepthBuffer: true`.
  Never add coplanar flat geometry without picking a layer, and never use polygonOffset on the flats (the log fallback
  ignores it).
- **Navigation:** fly-only since Round 35. Orbit survives only as the attract loop (the veil
  and the post-Enter glide down to City Hall); the first pointer/wheel/touch/key hands control
  to fly (`autoFly`): WASD, E/Q or Space/C, shift boost, scroll sets cruise speed, clamped
  above terrain via `siteY`; touch gets a throttle joystick + ▲▼ buttons and a first-time
  tips card. Walk is reachable only through `__dbg.goWalk`. Pointer lock has a drag-look
  fallback that must stay functional.
- **Layers panel (F):** SEPTA vehicles (V; JSONP polls of TransitViewAll, street-snapped,
  badge billboards on every vehicle), Indego (B), flights (X; adsb.fi through
  `FLIGHT_PROXY = https://philly3d.com/adsb`), ships (H; aisstream.io WebSocket, key in
  `AIS_KEY`, one client per key), Amtrak trains (K; Round 80: `/amtrak.json` baked every 30 s
  by `ops/amtrak_bake.py` from Amtraker, the page pulling Amtraker itself when the file is
  150 s stale; consists articulated along the baked `rail_amtrak.json` tracks by `railSnap` /
  `railWalk`, dead-reckoned between fixes), typical traffic (R; PennDOT AADT simulated on a road graph,
  camera-weighted bounded pool, six vehicle models, connected routes and following gaps), street closures (U; Round 79: `/closures.json` baked every 30 min by
  `ops/closures_bake.py` from the Streets Department's StreetSmartPHL permits and paving
  status, drums and cones posted on the snapped block, paving strips, a closed block empties the
  typical traffic), streetlights (G), street names (N; SDF atlas), landmark labels
  (L; **off by default by owner decision**, the citywide tier lives behind this key),
  neighborhood names (P), historical markers (J) and public art (O; Round 83, the two rows after Street
  Closures, default on, their counts the record totals). Address / route search on `/`. Every live layer is silent when
  its feed is unreachable and says so in the row title. The share link's `l=` mask carries
  fourteen bits since Round 83 (1024 Amtrak, 2048 closures, 4096 markers, 8192 art) with 16384
  marking a fourteen-bit link, 4096 alone a twelve-bit one and 1024 alone a ten-bit one;
  `parseHash` keeps `& 32767`. `tests/test_layers.py` pins the order, the markers and the rows.
- **Skyline lights (Round 81):** after dark the researched crowns flagged `theme` in `towers.json`
  (BNY Mellon's lattice with a wash skin, the Comcast Center's, Three Logan's, FMC's and Cira's
  crown floors under wash sleeves, Two Logan's pyramid, One South Broad's lantern, PECO's new
  `band` crown), One and Two Liberty Place's chevron trim, City Hall's tower (the metalwork and
  clock faces tinted, wash sheets on the shaft and clock stage, floodlit from below) and the Ben
  Franklin Bridge (the cable and suspender boxes, LED nodes every 6 m along the cables and the
  floor edges, a wash on the piers and legs) glow in the night's colour. One merged mesh
  (`themeParts` → `themeMat`: the vertex colour by day, `aLit` the house night colour, `aMix`
  how far the theme replaces it, `aSlot` which of four colours), one additive sheet mesh
  (`themeSheets`, colours rewritten as the theme eases) and one point cloud (`bfbNodes`);
  the bridge's 148 walkway lamps are an instanced mesh with glow points on `poleMat`. The
  resolver `lightsThemeAt` (pure, tested) takes a Philadelphia game day first (Eagles,
  Phillies, Flyers, Sixers; regular season and postseason, home or away; ESPN's scoreboard
  for the day viewed, four small answers once per day per session, `lightsFetchDate`), then
  the calendar's most specific row (`lights.json`, built in and refreshed from
  `/lights.json` when the served `t` is newer), else the house white; it follows the MODEL
  date like the markets. Colours convert sRGB → linear before the emissive (gotcha 11) with a
  luminance lift up to 2.2 for dim hues; changes ease 20 s; a `?lights=` pin lands at once.
  No layer bit. `__dbg.lights(name)`, `__dbg.lightsState()`, `__dbg.lightsSettle()`.
- **The half-mile rule (Round 82):** `NEAR_R` (804.67 m) and `nearCam(x, y, z)` gate every ground layer's
  draw path (SEPTA in `updateTransit`, the Indego docks in `indegoRebuild` on the streetlights' cadence,
  the Amtrak cars and badge, the closures' `closuresReconcile`, the markers' and art's `markersReconcile`
  from a 400 m cell map with the records' kept yaw, the market tents in `updateMarkets(now)`) and the
  screen-space pick fallbacks; flights and ships keep their range. The closed blocks, the markers and
  the art carry pins (`pinTexture` / `pinMesh`: the aircraft badge's casing, masked out of the bloom,
  depth-tested), composed every frame at the SEPTA badges' size rule; `casterSig` counts the posts,
  plinths and drums so the shadow map follows them. `__dbg.near(m)`, `__dbg.nearState()`.
- **Round 85's corridor and bank (Mike: the tracks broken all over the city, strips across the Schuylkill, the
  bank roads clipped, the tracks short of 30th Street):** the corridor step stitches the 713 OSM ways into 57
  chains by half-metre node keys, samples each chain at 20 m on the drawn ground (`groundMeshLandY`), ramps
  every bridge-tagged or over-water run between its abutments (floored 9 m over water only when it crosses the
  outline) with the approaches climbing over eight samples, pins chain ends to shared node heights, smooths the
  free points twice, and draws each chain as one skirted ribbon with rails, plus a steel deck and piers under
  the bridge runs. `RAIL_CUTS` are the two portal cuts at 30th Street (`railCut` joins `cutHole`, so the wide
  ground opens over them; the rail step draws their floors, walls, collars and headwalls); the covered points
  inside the station box take flag 4, a straight lower-level grade, are drawn, and the trains ride through.
  The bank: `groundMeshLandY` returns null under water + 0.85 or within 40 m of the Schuylkill's outline, the
  road loops floor a non-deck roadway at water + 1.2, covered sunken chains draw only their exposed stretches
  with a face to the bed, and `bake_overpasses.py` tests over-water against `schuylkill.json`'s polygons.
  `__dbg.rail()` gives the counts and the step's own check (`under`, `underMax`, `floatMax`, `grade`), `__dbg.railSnap`
  the grid (`gradeAt`, `underAt` locate the extremes); the critique pass floored every span and free point at the drawn ground + 0.45 (a fill carries the
  ballast, no deck or pier within 1.2 m of the ground, no pier within 8 m of a street), pinned a node to a span's
  or the shed's height else the shared ground reading, gated the road floor and a new quay skirt to 60 m of the
  Schuylkill's outline (`bankFloor`: water + 1.2 inside the outline eased to the datum across the 40 m band, read by
  the road loops, the traffic, the drums and the buses, mirrored by `sch_bank` in `bake_overpasses.py`, which also
  floors an elevated deck at its DEM + 0.45), dipped the cut collar under any deck it crosses, rebuilt the cut walls
  as 10 m pieces following the ground outside them with a ring of ground-following collar sheets sized from the
  25 m hole cells, pinned a node to the mean of its span or shed ends, anchored the shed grade to the cut floors,
  and dropped the Norfolk Southern ways from `bake_rail.py` (operator tag). The striped LED parts (the Comcast crowns, the FMC) carry slots of 4 and
  up, stripe indices into `uStripe0..3` reduced by `uStripeN`: a team's `stripes` pair from `LIGHT_TEAMS`, else
  the night's own colours.
- **Round 84's lit set:** the arena's band and wash, the Liberty Places' gable-edge neon (`neon()` in the
  landmark block, a bar between two world points), One Liberty's white spire and red beacon (mix 0: never
  the theme), City Hall washed whole (sheets on the block and every pavilion, the mansards and caps
  floodlit), William Penn rebuilt (24 primitives, a warm flood at mix 0.25), Rocky at `pt(101, -47)` of
  the museum frame, the Comcast crowns in four bands with slots `(tslot + k) % 4` so several colours
  stack, and `TALL_LIT_H` 120 in `bake_towers.py` giving every tall tower a `band` or notch strip.
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
  `WX` must be declared before the sky material (TDZ). Round 75 adds the air: `fetchAqi()`
  every 15 min reads the city's Air Management Services core-site readings (ArcGIS, CORS
  open), `aqiFromRows` cleans them (nulls, the -999 sentinel, rows over 12 h old since the
  layer lags by hours, two PM2.5 sites minimum), `applyAqi` sets `AQI` and the `WXFX.tHaze`/`tHazeTint` targets (eased over
  20 s), and `applyLighting` multiplies both fog distances by `WXFX.haze` and lerps sky, fog
  and sun toward the smoke tones by `WXFX.hazeTint`. `?aqi=` pins it; `tests/test_aqi.py`
  runs the pure block under JavaScriptCore.
- **Street names:** `ST_LABELS` + `ST_SDF` → one indexed quad mesh draped column by column on
  the road profile, alpha from an SDF threshold (RedFormat DataTexture; LuminanceFormat is
  rejected by WebGL2).
- **Storefronts (Round 189):** 'Dressing the storefronts' is async: under REAL on WebGL 2 with `STOREFRONT_ART` it
  awaits the art (at most 10 s more) and makes the two textures (`sfTextures`: the atlas sRGB, the mask linear). A
  computer asks for the art at the top of `build()` (`sfArtLoad`) and takes it as ImageBitmaps decoded off the main thread
  (`SF_BITMAP`: `imageOrientation: 'flipY'`, `premultiplyAlpha: 'none'`), uploaded with `flipY` false and closed in the
  texture's `onUpdate` (`sfBitmapTex`), which leaves `tex.image` a `{ width, height }` stub: these two textures can never
  be uploaded again (nothing re-uploads them; a lost context is never rebuilt). A desktop Safari before 17 or Firefox
  before 98 ignores the flip, so `SF_BITMAP` keeps them on the `<img>` path (GLTFLoader's line); Safari 26 was checked the
  right way up. A phone fetches only the bytes at the top of the build (`sfArtPrefetch`, two blobs, 380 KB) and makes and
  decodes its `<img>` from them at the step (`freeTexOnUpload` lets it go): the third review found the two decoded half
  images, about 10 MB, held through the far ring's uploads, the build's peak; a fetch that fails asks for the file at the
  step. It builds one InstancedMesh of panels (`sfBuild`: a 16-vertex
  unit, the front and its two returns and cap; per instance its cell rect, fascia band, size, trade and sign kind, near
  flag, rows and hours, all Float32 vec4, and `aSfSlot`, the name's slot) plus one of canvas awnings (`frontAwning`'s
  flat unit; a scalloped valance's lobes cut in the shader by the metre, `aSfNear` carrying 2 for it). The record's place
  comes from `STOREFRONT_INFO` when its `n` matches (`sfInfo`): shifted along the wall, at its laid width, turned by its
  lean, its face 6 cm proud of the drawn wall's outermost point with returns back past the innermost, its foot under
  the lowest ground and its shopfront from the highest sidewalk 1.5 m out up to the host's storey plus 0.7 m; every test
  (the custom models', the street floors', the house fronts') is made at the laid span, 1.2 m inside the wall's measured
  line (the record's line moved out by the sidecar's out). A house front under the span's ends or middle (`sfFrontCells`,
  `sfFrontsAt`) dissolves the panel near the eye, and one that is not a shop set becomes its shop set (`sfShopSet`) so its
  raised door never shows over the board, switched only once the build has stood (`toShop`). The cell: the record's trade and the width
  class nearest its width, the variant by the colour byte (a chain wears one front), and when a panel within `SF_NEIGH_R`
  30 m already wears it, whichever way it faces (across the street and round the corner count since the third review),
  the trade's next, then its cells at a width within `SF_STRETCH`, then its siblings' (`SF_SIB`); mirrored by a hash of
  the name. A panel on a style-5 wall the facade shader dresses with its own shopfronts (Part A) takes the shader's units:
  the outer districts' and the far ring's wall loops call `sfHostNote` for every style-5 wall (`SF_HOST`: the records'
  laid lines in 40 m cells, decoded once from `STOREFRONTS_B64` and the sidecar by `sfPlace`, the same placement
  `sfBuild` makes), which ports the shader's unit rule and its fascia height (`sfPartTop`: facadeFp, rowHead, roofGap,
  rows and facadeScale for that wall); `sfBuild` takes each run of panels on one wall to the nearest joints of the units
  (`sfSnapRun`) and raises them over the fascia, so no unit is cut by a panel. Change the shader's Part A unit rule or its
  storey and `sfPartTop` and `sfHostNote` must follow (the harness test pins the 25 m wall's three units). The core's walls
  (`buildingGeom`) are not noted. The hours' fourth float carries the weekdays a shop keeps shut (the sidecar's seventh
  value, a bit a weekday, Monday the first). The shader (`sfPanelHook`, top level) keeps the bulkhead and fascia native
  and meets the storey by cutting up to `SF_CROP` 0.5 m off the glass's head before it rescales what is left, wraps each
  return in its end's pier by depth, dims the painted interior under
  `glassOpticsPatch`'s reflection, shifts it 35 cm deep on a computer, writes the name from the slot atlas into the board,
  lights the interior through its picture by the hours on the model clock (`sfStep` sets `uSfClock`), and dissolves on the
  near flag with the fronts' dither. The names (`sfNamesInit`, `sfNamesAssign`, `sfNamesFlush`, `sfDrawName`): a red-only
  CanvasTexture of 32 slots (16 on a phone) uploaded once, its canvas then dropped, each slot redrawn into one slot-sized
  canvas and copied with `copyTextureToTexture`; the nearest named, front-facing panels in view within 160 m (90 on a
  phone) hold them, re-assigned every 0.4 s (0.6) or 8 m. The painted shop floors take the same two textures in the
  facade hook (`SF_PARTA`, `sfPartU`, on once they are up: `uSfOn`). `__dbg.sf()`.

### Added in Round 46 (Sep 1, the optimisation audit)

- **Load path:** the packed int16 blobs are stored byte-planar by build.py (`B64_PLANAR` const) and
  re-interleaved by one `unb64()`; the two ring decoders stage into `VBuf`/`IdxBuf` typed
  accumulators, seal chunks at 60k vertices and hand them to `addChunkMesh` / `flushUploads`
  (every new ring mesh draws unculled once so it uploads and frees). `ovpNear` is a 32 m bitmap
  that pre-tests footprints against the deck swaths. `yieldNow` (MessageChannel) is the only
  yield between build steps.
- **Runtime:** `renderer.shadowMap.autoUpdate` is off; `aimSun` requests a redraw when the box
  or the sun moves and `frame()` refreshes every 4th frame while vehicles move. `cullFogged`
  hides outer meshes beyond `fog.far` (view depth). `DPR` adapts the pixel ratio on a ladder
  from the display's ratio under `DPR_CAP` (1.75 desktop, 1.25 touch) down to 0.9 / 0.72, judged from Enter on; since
  Round 166 every step is an A-B-A trial kept only when it pays (`dprJudge`; `tests/test_dpr_controller.py`) (`?dpr=N` pins); since Round 192 a frame of 250 ms or more is a slow frame like any other (only a page hidden since the last frame, `DPR.away`, or a frame over `DPR_AWAY` 4 s abandons a trial), so a struggling Mac steps down. `flushInst(m, colorFrom)` is the
  one InstancedMesh upload helper. `PERF`/`__dbg.perf()` and the `?dev` readout carry per-step
  timings and frame p50/p95; `beacon()` posts checkpoints to philly3d.com's `/b` from the site and the
  apps; the `perf` (60 s after Enter) and `settled` (180 s) beacons add frame p50/p95, calls, triangles and the
  controller's record (`dpt` trials kept and undone each way, `dpm` time-weighted ratio, `dpl` lowest ratio tried, `dpv`
  the display's interval, `dpf` the last frame ms at each rung).
- **Feeds:** `septaFetchBaked` reads `/septa.json` (ops/septa_bake.py) before the JSONP rotation;
  `shipRelayPoll`/`shipUpsertRelay` read `/ais.json` (ops/ais_relay.py) and only fall back to the
  direct aisstream socket while the relay is missing or stale (90 s / 60 s gates); `concertsPoll`
  reads `/concerts.json` (ops/concerts_bake.py, Ticketmaster's Philadelphia music listings baked every
  15 min with the key on the VPS) every 10 min, drops everything when the file is 3 h old, and
  has no keyless fallback (Round 56); a venue the page knows by name is pinned at its building
  (`VENUE_NAMED`, Round 66: Ticketmaster's geocoder misses half the city's halls by up to 1.2 km).
- **UI:** prefs persist under localStorage `philly3d.prefs` (seeded before `build()`; hash wins) and the
  first-visit guide under `philly3d.guide` (Round 60: `#guide`, `GUIDE_SLIDES`, the ? button and key);
  the Graphics choice under `philly3d.gfx` (Round 168: `GFX`, `gfxSet`, the strip at the top of the Layers
  panel; never in the prefs or the hash) and the crash tiers under `philly3d.tier`, `philly3d.lite`,
  `philly3d.tiersoft`, `philly3d.tierrun`, `philly3d.tierok` and `philly3d.tierv` (the boot block);
  the share hash is `#p=x,y,z,yaw,pitch&t=YYYYMMDD,minutes&l=<bitmask>` (bits: 1 SEPTA, 2 Indego,
  4 flights, 8 ships, 16 traffic, 32 lights, 64 streets, 128 labels, 256 places, 512 concerts;
  1024 marks a ten-bit link, a nine-bit link keeps the concerts at their default), written by
  `updateHash` from `frame()`; `openPanel`/`closePanels` keep one bottom panel open (Escape and a
  short canvas tap close them); the layers panel (640 px, rows in two columns, Round 59) ends with 'Take me to' stops (`STOPS`, the glide
  tween `glideFly`/`stepGlide` polled from `frame()`) and 'Tour the City'; `btnShot` captures the
  GL canvas; the time panel's Play runs the sun time-lapse (`setLapse`, PMREM rebake gated by
  `envGap`); the compass is a button (`faceNorth`); a bus-route search sets `SEPTA.filter`
  (chip in `#searchOut`, status 'N of M on route R'); `searchLocal` matches the in-page name
  index (landmarks, neighborhoods, districts, the farmers' markets, the historical markers and
  artworks, and since Round 78 the city basemap's 5,900 named places from `landmarks.json`:
  schools, churches, parks, rec centers, hospitals and the rest, each with its own kind label;
  named buildings, streets) before Nominatim. `add()` drops the same name within 150 m under any
  kind, so a label's entry wins over the city layer's.
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
    41's tooltip kill was a raycast into a freed chunk). Round 167: a mesh a step builds after
    the last `flushUploads(true)` (the trees, the tie runs) goes into `pendingUpload` unculled
    and `frame()` sets it culled after the first frame, which is drawn behind the veil, so it
    uploads there without an extra render (and without compiling programs the weather pass
    would dispose).

13. **Render targets and r149's colour pipeline (Round 51).** A render-target pass is forced to
    LinearEncoding but is still tone-mapped for every toneMapped material, so a post pipeline
    that tone-maps in its composite must run the renderer at `NoToneMapping` (`POST.on`), or
    the scene is mapped twice (the milky river). Custom ShaderMaterials without the
    tonemapping/encodings chunks (the dome, the cloud deck) write raw and must hand the
    composite the pre-image (`pUndo`); `toneMapped: false` built-ins were sRGB-encoded by the
    renderer and take `pUndoLin` (`postRaw`). A depth-only target gets a 16-bit depth
    renderbuffer, depth+stencil gets 24 bits. `renderer.info` resets per `render()` call.
14. **Additive light in a float target is unbounded.** The canvas clamped a thousand fogged
    far lamps at white; a half-float target sums them past it into a band that blooms. Under
    the post pipeline additive light materials use MAX blending, premultiplied (`postRaw`).
15. **`onBeforeCompile` is the program cache key.** r149 keys a material's program on
    `onBeforeCompile.toString()`; a wrapper closure with the same source as another shares its
    program. Set `customProgramCacheKey` whenever a hook is wrapped or parameterised.
16. **Canvas sprites premultiply.** A CanvasTexture's clear texels come back black, and the
    mips bleed that into every alpha-cut edge (the tufts read as dark specks from height).
    Paint, then upload the pixel array as a DataTexture with the clear texels filled with
    the sprite's own colour (`paintTuftTex`).
17. **A sheet over a heightfield must be built ON the mesh, not sampled from the DEM (Round
    52).** `drapedPoly` samples `siteY` (bilinear on the 50 m DEM) at jittered points and caps
    them at ~420 (`sqrt(area / 420)`), so a big lot was draped at 36 to 61 m against the 25 m
    ground mesh, which is linear on its own triangles: two different linear reads of one
    surface, half a metre apart, and the ground rose through the sheet as green blobs however
    the lifts were tuned (Round 47 codas 5 and 6). Outside the core use `conformDrape`, which
    clips the polygon to the registered ground triangles (`groundGrids`, `groundMeshY`) so every
    sheet triangle lies in one ground triangle and the offset is exact everywhere; `drapedPoly`
    is only the fallback past the registered grids and in the core.
18. **r149 hands `onBeforeCompile` the renderer as its second argument**, so a patch function
    assigned bare (`m.onBeforeCompile = patch`) must never test a second parameter for
    truthiness (`opt === true`). And `Material.copy()`/`clone()` drop `onBeforeCompile` and
    `customProgramCacheKey`: give clones their hooks after cloning, or use a factory.
19. **Anti-aliased lines: centre the ramp on the edge.** A `smoothstep(halfW - px, halfW, d)`
    ramp lies inside the line and eats a full pixel of it, so a 0.12 m line vanished from 150 m
    up (one pixel is the line's width there). `lnLine` in `lanePatch` ramps from
    `halfW - px/2` to `halfW + px/2`, which preserves the coverage, plus a width floor and a
    gain floor so far streets keep a faint stripe.
20. **Markers and labels must not bloom.** Under the post pipeline a `postRaw` sprite's white
    hands the composite a pre-image far above the bright pass threshold. The bright pass reads
    the target's alpha as its mask (the cloud deck's coverage rides there), so
    `postRaw(mat, { mask: true })` blends colour normally and writes zero alpha under the sprite.
21. **A transparent shader divides by its coverage, never by its faded alpha (Round 53).** The
    marched cloud deck accumulates premultiplied colour and un-premultiplies at the end; the
    first pass divided by the alpha after the 14 to 26 km distance fade, and where the fade
    reached zero the divide put NaN, which the blend drew as a bowed black line along the deck's
    far edge. Keep the coverage (`1 - T`) for every divide and apply the fade to the alpha alone.

22. **`VBuf.geometry(false)` attaches nothing (Round 54).** The curtain-wall chunks uploaded with it
    for five rounds, so the outer glass shader's `aStyle` read 0 everywhere and no researched
    curtain-wall variant had ever drawn. Every mesh on `cityMat`, `coreMat` or `outerGlassMat` must
    come from `geometry(true)` or `mergeColored(parts, ao, true)`, which carry aStyle, aFloorH,
    aBase and the Round 54 glass tint `aTint`. Round 101 adds packed `aFacade`: two signed
    decimetre shorts (signed wall width for U=0/L, and wall-top height); the core keeps its float
    aWallU/L/H attributes. Decode the packed endpoints in the vertex shader before interpolation.
    `tests/test_vbuf.py` runs the buffer for real under
    JavaScriptCore and checks the upload mode. And a glass tint must be a per-vertex attribute, never
    a world-position hash: 28 m cells cut one tower into three colours.
23. **The style word is `st + 32 * variant`: test the low five bits (Round 88).** `fabricStyle`
    packs the dark and tall variants of a plain row at 32 and up, and the wide loop's
    `if (style >= 20)` glass test read the whole word, so 70,000 rowhouses drew as blank tinted
    glass for two weeks and read as a pink inner tier with a hard seam. `isGlassStyle` (20 to 31)
    is the test; never compare a style word against a threshold without masking the variant.
24. **`schEdges` returns a distance only as far as its grid search reaches (Round 88).** It started
    `best` at 40² over a ±2-cell search of 20 m cells, so it never said more than 40, and the
    Round 87 bank blend in `groundMeshLandY` (40 to 70 m) took t = 0 everywhere: every road in the
    city read the DEM instead of the drawn mesh and the 100 m far mesh cut through the strips.
    It reads to 80 m now (`EC` 40, `best` 6400); a band that starts where the read caps is a
    band that never engages. And a flat quad at two centreline heights is never "on" a
    heightfield: `drapeConvex` is how a strip sits on the drawn ground.
25. **A margin one tier cedes must be a margin the other tier really paves (Round 88).** The far
    ring skipped the wide box's 200 m margin outright, but the wide extract only holds ways that
    ENTER its box, so a road running alongside the edge was in neither blob (21 km, I-76 at
    Passyunk). Cede by geometry (`wideOwned`), not by box.
26. **Debug a "wrong material" by painting materials, not by reading code (Round 88).** Wrapping
    a material's `onBeforeCompile` in the pane to force `gl_FragColor` a flat colour, with a new
    `customProgramCacheKey`, showed in one frame which material owned the salmon rowhouses; three
    investigators reading the shader had concluded nothing was tier-specific. And never `await`
    between `frameOnce()` and a canvas `getImageData` read, or the compositor hands back black.

More rules the log paid for (details in `devlog.md`):

- **Street meshes are welded, not a soup (Round 122).** `roadStrip` and `roadFan` emit through
  `roadWeld`: one vertex per distinct point of a strip, keyed at a centimetre, and the street
  index still sees every triangle. A new emitter that pushes three fresh vertices a triangle
  into `rc.pos` puts back the 6 M vertices that took a phone past iOS's memory limit. Measure a
  phone's footprint with the injected GPU counter described in devlog Round 122, under a touch
  profile, before and after anything that adds geometry citywide.

- Southern I-95 approach (Round 121): `bake_overpasses.py` keeps the bridge and untagged embankment ways south of the mapped tunnel exit in one continuous profile, plus their connected core ramps. The `core` tag on these records bypasses the artificial core-box clip; it does not raise adjacent Front Street or Columbus Boulevard. Ramp merge nodes survive profile simplification. Core `ribbon` roads cede owned segments to the deck, which carries its own lane attributes. Cars, live buses, closures and label height lookup use their aligned deck directly, including below the bare-earth elevation on the emerging approach. Elevations are model estimates, not a surveyed engineering profile. Re-bake street labels after changing overpass data.
- Window optics (Round 120): `glassOpticsPatch` supplies low-roughness dielectric glass, stronger coated-glass Fresnel on curtain walls, less diffuse interior fill and small deterministic pane-normal variations. Shared facade masks exclude sash frames and preserve parapet clearances; custom apartment and Ryland hooks use their existing room coordinates. Keep the roughness override after weather patches and do not reassign it later in the curtain-wall hook. The reflection dome decodes display colors to linear exactly once, paints approximate cloud cover across its hemisphere and uses the compact sun glint with twilight/cover attenuation. PMREM blur is 0.012. This is a shared sky/ground/silhouette probe, not per-building ray tracing; no extra scene passes, render targets or window lights.
- Window interiors (Round 119): `WINDOW_INTERIOR_GLSL` is shared by generic facades, curtain-wall skyscrapers, Ryland and the Society Hill towers. `roomLight` keys occupancy to room coordinates and a facade seed: warm individual rooms for homes, mixed-temperature suites of 2-3 rooms for offices. Ceiling/lamp gradients, shaded reveals, partial blinds, curtains and low interior shadows replace the flat emission. Facade branches supply actual opening UVs and subtract their sash/mullion masks from the emission; roofline masks remain intact. Fine interior detail averages out by pixel footprint, while room identity remains fixed. The three modelled towers carry `aInterior` (UV, seed, lobby flag) through `mergeColored`, shared by glass and curtain overlays. No added light sources or draw calls; expensive interior work is skipped in daylight. Curtain-wall base emission is white so the shader's color temperatures are not tinted amber twice.
- Architectural lighting (Round 118): `architecturalBloom` reserves HDR scene alpha above 1 for visible light sources, using separate alpha blend factors on transparent emitters. `ARCH_BRIGHT_GLSL` extracts a filtered, hue-aware halo without boosting visible RGB into pastel. Opaque occluders overwrite the tag; labels retain their zero bloom mask. The composite protects the emitter's own color/grid. No extra render targets or scene passes. The mobile/no-bloom path keeps the soft geometry/material falloff.
- Flat-roof lighting (Rounds 117/118): `roofLightBand` follows the actual footprint. Flat crowns now have a 0.32 m fixture below the parapet and a separate 4.8 m softly fading wash. `themeWashGeometry` strips horizontal caps; `themeWashPatch` feathers both boundaries and distinguishes uplights, downlights and broad washes. Never use a filled oriented bounding box for roof lights: it crosses chamfers/recesses and leaves glowing slabs on the roof. Theme slots/materials remain shared. The packed-data test covers all 23 currently rendered band landmarks; One Logan's tall footprint currently lies outside its spec matching radius and has no band.

- **No em dashes or middot separators in any user-facing string** (Mike's rule): veil, hints,
  cards, panel text, loading messages, tooltips. Commas, colons, sentences. Code comments and
  these docs are exempt.
- `WX` must be declared before the sky material (`refreshEnv` reads it during init, TDZ crash).
- Custom shaders that use the logdepthbuf chunks need `#include <common>` for
  `isPerspectiveMatrix` or the program dies silently and the mesh never draws.
- Reversed Z (Round 192, `ZREV`, `zrevInstall`): inside `renderer.render` a perspective camera's projection has its z row
  rewritten (near at depth 1, far at 0), the depth clears to 0 and every depth function is flipped; outside it
  `camera.projectionMatrix` is three's own. So: (1) never write `gl_FragDepth` in a new program (it costs the early depth
  test the round bought; the cloud deck's depth-writing program is the one exception, `tests/test_zbuf.py` counts the
  writes) and never set `gl_Position.z` without both conventions (`ZREV.on ? ... : ...`, as the sky dome, the deck's
  clamp, the wakes' and the vehicle shadows' hair toward the eye do); (2) a perspective render target that holds depth
  must be float or the gain is gone (`zrevFloatDepth` re-specifies a target's renderbuffer as `DEPTH32F_STENCIL8` /
  `DEPTH_COMPONENT32F` after three makes it; `zrevDT` hands a small target a float depth texture), and check what it
  returns at full size (`zrevFail`: a crumb that keeps log depth a fortnight, and one reload where the frame itself is
  lost), but never on a LOST context, which fails every check (36061, CONTEXT_LOST_WEBGL) and belongs to the
  webglcontextlost handler: every check returns first on `zrevLost()` (the second review: a resize between the loss and
  the handler wrote the crumb and raced the handler's reload); (3) a `renderer.clear()` outside a render clears to 1, which is the near plane here: a render that does not clear
  its own depth is guarded per target (`ZREV.clr`, a WeakSet kept until a reversed render draws there), but a new pass
  that draws a perspective camera with `autoClear` off should clear inside its own render; (4) the shadow pass and every
  orthographic camera keep the standard convention (the clip control is switched back for them); (5) the river mirror's
  oblique row is not a distance (depth 1 - k h / d): anything whose fragments share one depth (a point sprite, a quad
  pinned to its anchor's depth) is wrong against it, so the mirror's pass swaps every Points object onto a twin
  (`MIRZ`, `mirzTwin`) that writes the depth of its own pixel on the sprite's plane, and clips the vertex-depth glows past
  the mirror's far plane as log depth did; a new kind of sprite or billboard in the mirror needs the same, and its twin
  is built behind the veil on the second frame (`mirzWarm`: the points and the mirror's lights alone on layer 30, drawn
  once into a scratch target), so a Points object made after that frame compiles its twin in flight. A program that
  `discard`s keeps its early depth test only partly on Apple's GPUs: City Hall's balustrade cut (one program since fix2)
  is the one large case left.
- The cloud deck (Round 192): under the low bank's lowest base minus 25 m it draws `cloudMatNoZ`, which writes no depth and
  sits on the far plane, in both depth modes; every aircraft over the base on the screen gets a rectangle (`cloudRects`,
  sixteen at most) that the twin leaves to `cloudDeckZ`, the depth-writing program cut to them and scissored to their
  union, so a plane over the base stays veiled by the cloud in front of it. Anything else that ever stands over 400 m
  (the storm's lowest base) needs the same treatment.
- Ground/water/sky palette (Round 106): `ROAD_COLORS` is shared by core/wide/far roads and bridge decks; use `COLORS.paving` for concrete walks/aprons. `surfTexPatch` classifies green against **both** red and blue so blue-gray asphalt never becomes meadow. Grass detail fades to its mean. Water's sky uniforms are copied and converted to linear before fog's post conversion; do not mutate the dome palette. `liquify` cache keys include ripple scale/amplitude/speed/touch budget. `uTwilight` must be copied to the reflection dome in `refreshEnv`.
- Comcast Center (Round 108): one south-facing recess at modeled heights 247–271 m, below the intact 271–297 m crown. These are photographic proportions, not surveyed elevations. `specTopPlan` anchors `comcastFacadePieces` so lower shoulder records cannot fill the opening. Keep lower atria glazed; dark applied panels looked like extra holes. Crown slots 200–201 identify this building; `uComcastSolid` routes both automatic and manually selected Phillies nights to red across the whole crown, including the roof. Custom palettes retain bands; other buildings keep their palettes.
- Comcast crown grid (Round 111): `aCrownGrid` carries local wall distance, height above the building base and face width through `mergeColored`. `crownPanelPatch` modulates the themed light with mullions, posts and floor bands, aligned with the daytime glass. Keep the footprint-integrated bars to avoid distant shimmer. Zero coordinates on the roof and CTC preserve their lighting. The crown GPU fixture needs an opaque backing like the real building so far-side light panels cannot overwrite the visible grid.
- City Hall floodlights (Round 109): `cityHallFloodPatch` uses Gaussian pools centered on the corner/entrance pavilions and tower, blended in block coordinates. Keep the connecting wings' soft falloff and continuous vertical fade; hard `step` masks and repeating height resets made visible lighting cutoffs. Slate roofs stay dark and the existing theme/night uniforms drive the wash. `tests/city_hall_gpu.html` checks shader continuity and the actual facade hook in both depth modes.
- Rocky placement (Round 113): the museum-frame `pt(38, 0)` light pedestal carries the statue, feet at terrace T + 0.9 m, facing the Oval. The former lawn-side figure/base is removed. `rockySite` carries the built position into local search, including its raised anchor height.
- Roofline clearance (Round 114): the shared `facadeHook` reserves `roofGap` and fits the window-only `fv` coordinates to complete rows, using `rowHead` for each style's full frame/lintel. Keep masonry/cornices in physical `v` coordinates and preserve `windowArea` on far averaged light. `tests/facade_roofline_gpu.html` checks roof glass/emission across heights, variants, attribute formats and detail/depth modes; `tests/buildings_gpu.html` checks the full material set.
- El portals / I-95 walls (Round 116): `elTrackProfiles()` is the shared cached rail/deck/excavation profile. `elPortalClipGround` cuts exact narrow openings into wide/far indexed terrain while preserving outside triangles and attributes; the registry keeps the original surface grade for road fitting. Use `elPortalAt` to exclude vegetation. Portal masonry shares the El structure batch. Straight Front Street trench walls must stay within `CORE_EXT.z0/z1`; extending them into the outer districts created the white wall across Callowhill's curved highway lanes.
- El tracks (Round 115): `elTrackFrames` / `elTrackRibbon` build shared mitered rails above the existing `EL_TRACK` deck profile. `elTrackSleepers` keeps distance phase through joints; the ties are instanced boxes in runs of about 500 m (`tieRuns`, Round 167), each culled by its own sphere and never hidden by distance (a hide past 700 m changed 751 pixels of an El overview through antialiasing and was taken out on review); PATCO's ties go through the same helper. There are four running rails, outside third rails and two track beds on each elevated corridor. `__dbg.elTracks()` and `tests/test_el_tracks.py` check this. L1/B1 live-feed records were verified as placeholder locations again on Sep 18, 2026; never label timetable-based subway animation as live GPS.
- Traffic coverage and inflow (Round 112): the bake reads wide, south and city raw OSM plus the optional city-street supplement. Match the rendered far-ring residential extent; never extend cars onto omitted streets. Simplify only between shared junctions, retain links down to 2 m, and read the header coordinate unit. `carFeed` searches upstream for offscreen spawn positions and reserves incoming cars against destination demand. Planned routes preserve one-way directions and building/terrain depth; births remain outside the frustum. Nearby streets get a modest density lift and refill priority within the same 2,200 desktop / 550 touch pool.
- Traffic continuity (Round 107): `trafficCars` includes retiring vehicles and must stay within `TRAFFIC.cap`; never truncate a draw batch to control population. After loading, births and removals must be outside the camera frustum or beyond the fade radius. Visible cars survive density changes and hold at unresolved dead ends. `trafficPrepareGraph` splits T-junctions with horizontal/height tolerances; do not connect stacked roads. `CAR_MODELS` dimensions drive spacing and lamp locations. Every fleet's body, lights and shadow material must share `aCarFade`; fades change coverage, never vehicle scale. Day/night counts are simulated AADT, not live vehicle locations.
- Never compute tight highlights on unnormalised interpolated directions over a coarse dome
  (the streaked sun); normalise per fragment.
- Moon terminator (Round 110): the sky shader blends through a phase-dependent penumbra, capped for thin crescents, with a screen-footprint filter computed outside the disc branch. Preserve the transparent unlit hemisphere and the original phase/position calculation. `tests/moon_gpu.html` exercises small/enlarged crescents through full moons, reversed orientations and both depth modes.
- Colour variation must live in hue + saturation, not lightness (the day pipeline flattens
  lightness); pick flat-surface colours by rendered swatch; calibrate stored colours against a
  measured transfer curve, not a guessed divisor.
- InstancedMesh: `frustumCulled = false` (instance bounds don't follow the fleet; r149's constructor sets it, and the
  test reads the geometry's own sphere, the unit shape's at the origin). A STATIC instanced mesh may cull only with
  `fitInstSphere`'s sphere round every instance as its shader draws it (Round 167: the trees, with the crowns' lump and
  sway, and the tie runs), set before any upload can drop the matrices; such a mesh is never a ray target. Never bake a
  rotation into a part that gets non-uniform instance scale; every mesh sharing
  `septaMats.body` must `setColorAt` (uninitialised instance colour reads black); a shared
  program expects instance colours.
- Sin-dot lattice hashes streak into worms on integer cell ids; use a fract-cascade hash.
- Storefronts (Round 189): `storefronts.b64` is never repacked (`bake_storefronts.py` refuses a blob that differs from
  the file unless `--rebake`; `tests/test_storefronts.py` pins its sha256): anything new per storefront rides in
  `storefront_info.json` in its order, which the page uses only when the counts match. Measure a panel's wall on the
  rings the page draws (wide.b64's grid moved a wall 10 cm and it stood through a panel's end), never the extract's, and
  never clamp what it finds: test a panel 1.2 m inside that measured line, never the record's (a tower's base drawn 2.6 m
  behind the line left the record's point in front of the wall and the panel in the air). The awnings cast their shadow
  through their own depth material (`sfAwningDepthMat`: the dissolve at the camera's position, `sfEyeU`, not the light's
  `cameraPosition`, and the scallops); a material that casts a shadow and discards needs one. The
  'Dressing the storefronts' step less its new path is pinned by sha (`tests/test_realism_storefronts.py`): the old
  boxes stay byte for byte. The art is off at tier 2, like the fronts. The shopfront art's mask is
  opaque RGB like the fronts' (WebKit's premultiplied decode moves any value under an alpha below 255). The names' atlas
  is updated after upload, so it is never `freeTexOnUpload`'d and the panels' `aSfSlot` stream is never freed (do not
  `freeOnUpload` the panel geometry). The panels never go through `pendingUpload` (its pass would cull them afterwards); since
  the third review their geometry's sphere holds every instance (`sfInstSphere`), which the water mirror's reach reads
  (the unit's own sphere at the origin cut them from the mirror wherever the eye stood 3.5 km from it). The old boxes are built inline in the step, unchanged, for `?real=0`, `?sfart=0`, WebGL 1 and art
  that does not arrive: keep that body as it is. The art is generated in two stages (`fetch_storefront_art.py`): an empty
  shopfront with chroma-key green panes, then the interior painted into them through an edit; the bake pastes back only
  the keyed pixels and takes the green's spill off the frames near the glass (`despill`), never off the board. A phone
  must never decode the art before the step (the third review: the decoded half images were held through the far ring's
  uploads): `build()` only prefetches its bytes there. A computer's two storefront textures are ImageBitmaps closed after
  their upload, their `tex.image` a stub: never set `needsUpdate` on them again. Any integer read from a varying is
  rounded before it is taken apart (`floor(x + 0.5)`: the slot's index was the last one that was not). The Part A host
  notes (`sfHostNote`, `sfPartTop`) are a port of the facade shader's unit and storey rule for style 5: change one, change
  the other.
- Never drape a big lawn over roads on a bumpy hill; recolour the ground instead.
- SEPTA: no CORS, JSONP only; subway rows are schedule placeholders (no real L/B GPS exists).
  Flights: no ADS-B API speaks CORS; the VPS `/adsb` proxy is the transport. Ships: aisstream
  sends binary frames (`ws.binaryType = 'arraybuffer'`), one client per key, release the
  socket when hidden. Nominatim results are filtered to "Philadelphia".
- Marker visibility: the user explicitly requires every pin family to be blocked by buildings
  (Round 105). `pinSceneDepth` enforces depth testing for all badges, search pins and event
  connectors/anchors. Preserve this across new pin types. Neighborhood map names are labels,
  not item pins. Pin selection filters occluded hits before applying draw-order priority.
  Round 167: on WebGL 2 the pins' depth image (`pinOccCapture`) is read through a pixel pack
  buffer behind a fence (`PIN_ASYNC`, `pinOccIssue`, `pinOccPoll`) and installed with its own
  capture's matrices only once the fence passes; the first image, a resize, WebGL 1 and any
  failure read synchronously, and the building tap's `occRender` read always does. A turn
  that finds a read in flight tries again the next frame. A fence passes only between tasks,
  so a probe looping `frameOnce` in one task sees no new image until it yields (the capture
  skill's `__cap`, `__frames` and pin sweep yield a task a frame; `__dbg.pinAsync(false)`
  forces the synchronous read).
- Deploy: stage + `chmod 644` before rsync (CloudStorage files are 0600 → site-wide 403);
  the nginx `/adsb` upstream must resolve at request time (`resolver … ipv6=off` + a
  variable `proxy_pass`) or an upgrade-time DNS blip keeps nginx from starting at all.
- **The glass towers (Round 192).** A curtain-wall system rides the aSFT floor byte as `-(sys + 1)` (`glassFh`;
  `vGSy` decodes it, a wall with none takes `styleDefault` by its style), so a new system costs no stream. Under
  `GLASS_ON` a researched glass wall lays no skin, and a part the research flags as glass (t 10) takes its cladding
  kind's system: never lay a skin over a glass wall again, it doubled the shading, and never route a wall onto the curtain
  wall by the cladding's lottery (the third review: 197 towers and 234 mid-rises, the limestone former Main Post Office
  among them, turned to stark dark glass where main drew the lottery's pick as a pale skin). The city probe (`CITYENV`) is the glass's own `envMap`, never
  `scene.environment` (every program would recompile); its proxy leaves out the towers within 160 m of each centre (a
  tower that close filled half a face of the cube where the parallax looks a kilometre out), and after each bake the
  second centre's sampler is pointed at the new target (the old one is disposed: a stale pointer drew University City's
  glass black). A pixel of curtain wall is a share of frame and a share of glass: their materials are summed by area
  with metalness 0 (a blended metalness turned every far wall into grey paint). The review's lessons: colours here are the
  scene's working values (gotcha 11), never `convertSRGBToLinear` (the first cut drew every frame, spandrel and proxy wall
  at half the city's brightness); the frames are a texture array with REPEAT and mips, never an atlas whose footprint is
  clamped (an isotropic clamp dropped every wall to a flat mean a block out), and the procedural frame is box filtered per
  axis (`gBand`); the probe bakes on the frame refreshEnv asks, after applyLighting, on every device (a gap or a
  still-only rule held a daylit probe into the night), and holds no sun sprite (the glint is the key light's); a frame's
  diffuse fill is the sky probe's, never the city probe's lit windows; and the far rooms are never blocks of rooms
  (strips a floor high, specks, then the share). The second review's lessons: every sky-derived term is the probe's own
  decoded radiance, never the dome's raw uniforms (`cHorizon`, `cZenith` are display colours; envSky draws them through
  `pFromSRGB`): the frames' and caps' fill is `SKYIRR`, the probe read at roughness 1 along six axes into a 6 x 1
  half-float target after each bake (an ambient cube, three `texelFetch` a fragment, no readback), at the fabric's 0.9;
  the proxy reads the sky probe itself for its fill and hazes with the city's own aerial perspective (`apU`, the fog's
  colour); the proxy's colours are in the scene's register (a wall at FACADE_GAIN, the ground at the city's mean from
  above), and so are the frames' and spandrels' paint (`GLASS_PAINT`): at a hex as an albedo a frame is nearly four times
  a wall. A phone's glass materials take a probe of the city probe's own size before their first compile (r149 keys a
  program on its envMap's size and keeps both), and the city probe shares the water's 128 generator. A glazed crown
  (style 29) is its tower's system in slim procedural frames, plant behind it, and sloped glass carries no pane's tilt,
  tint or frame. A home is lit by its apartment and its far light is the units under the pixel box filtered (`gHomeBox`),
  never point taps. Measure the proxy against the city with the second review's probe (the scene and the proxy rendered
  from one camera into float targets) before touching its colours. The third review's lessons: no light inside the glass
  that every view sees may be a Lambert term on the pane (0.4 of the transmittance squared drew every sunlit curtain wall
  as matte beige putty): the sun inside is the floor patch the eye's ray reaches from above, and the daylit room and the
  ceiling's bounce together stay under a quarter of what the pane reflects at normal view (`gCapRef`). The calibration is
  met through the reflection: by day the reflectance is the tower's photographed glass in linear light (`uGlassW.z` 2.0,
  the hue to the 1.6, `uGlassW.w`), after dark the references' F0 (a near mirror of a lit city stood 55% over main among
  the towers). A wall reflects a ray on as far down as it came in: seen from above a curtain wall mirrors the city and
  reads darker than its street photographs, so judge a colour from at or under a tower's top. A body is a hex in the legacy
  register: take its hue to linear light before it tints a reflection (as a working value a blue is half as blue). A lit
  room behind glass is far over the night's exposure: its displayed light falls with the transmittance only to the 0.35
  (`pow(gVLT / 0.5, 0.35)`), the offices' lit share is the fabric's, and the far glow is about a near room's own light
  (`GLASS_FAR_LUM`). `tests/test_glass_towers.py`,
  `tests/test_glass_calibration.py` (re-run `glass_calibrate.py` after any change to the glass), `tests/glass_systems_gpu.html`.
- Testing harness: synthetic PointerEvents need down *and* up on the canvas; setPointerCapture
  throws on fake pointerIds (cosmetic); layer fades run on wall time; render twice before a
  capture; close preview tabs so they don't hold the AIS key.

## State

As of 2026-09-11 the working tree is the Round 54 build (the material rework: masonry joints in relief, cornice and edge shading, roof seams, less metallic glass, one glass tint per building as the `aTint` vertex byte, the curtain-wall attributes restored on the outer glass upload with terrain-relative floor datums and the two Comcast rhythms, the CTC blade crown, slate-teal water, softer meadow, rebalanced key and fill, 18 cloud steps, the slate and limestone HUD; see the devlog entry) over the Round 53 build (the marched cumulus, the lighter fabric, the seven ship hulls, the installable app) over the Round 52 build (the game's ground: the meadow
on all bare ground with one shared mottle, lane paint on every road, stored-dark lots, the
conformant drape that ended the terrain clipping through lots and parks, the weather pass restored
on every textured flat, the markers masked out of the bloom; see the devlog entry) over the Round 51
build (the nature pass: the post pipeline, the painted meadow and tuft field, the lumpy crowns
under leaf cards, the cloud deck, the deep-blue body water). Before it, as of 2026-09-01, both homes served the Round 45 coda build: weather lands on every surface
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

Data © OpenStreetMap contributors (ODbL) — the OSM credit link must stay in the page. Since
Round 87 it lives only in the About panel, which names every source and is opened by the guide's
Credits link (`#guideCredits`) or the `i` key; the bottom credit line (`#osmcredit`) is gone on
every device. See `DATA-LICENSE.md` for every source's terms.
