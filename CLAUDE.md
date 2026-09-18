# CLAUDE.md

Philly3D (repo `HarkDigital/society-hill-towers`) is a living, single-file Three.js model of
Philadelphia: a detailed Society Hill core, the wide Center City / South Philly set, and a far
ring covering the whole city, on USGS terrain, with live SEPTA / Indego / flights / ships,
typical traffic, a solar clock and live weather. Live at https://philly3d.com/ (the VPS, and the
only home since Mike retired the GitHub Pages copy on Sep 17, 2026). Everything is in `3d-model/`;
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
The whole verification loop is the `philly3d-capture` skill (`.claude/skills/philly3d-capture/`,
the one part of `.claude/` that is committed): the staging and before/after steps, the capture
sink and `__cap` helper, the day and night pose tables and the `__dbg` probe list, and the pane
gotchas that cost the most time (the hidden tab's throttling, the reload that does not reload,
`document.hidden` never clearing, the uniforms `applyLighting` overwrites every frame). Read it
before any visual round rather than rediscovering it.

## Hard constraints

- No npm, no bundler, no framework: plain Python 3 build, vendored `three.min.js` (r149,
  pinned; see handoff gotcha 11 before touching it), one self-contained HTML that any static
  host can serve as a file. Every asset is inlined (fonts, icons, data).
- `build.py` must keep its guards: missing/undersized input, leftover `{{PLACEHOLDER}}`,
  `</script` inside a blob, page over `MAX_HTML` (75 MB since Sep 2, a runaway tripwire, not a
  target; the binding constraints are load time and phone memory).
- The OpenStreetMap credit link must stay reachable in the page, but no longer on screen: the bottom credit
  line (`#osmcredit`) is gone on every device at Mike's call (Round 87, after Round 69 had already hidden it on
  phones), and the attributions live in the About panel, which names every source. The way in is the guide's
  Credits link (`#guideCredits`, now shown at every width) plus the `i` key; the `i` button stays hidden.
  Data terms are in `DATA-LICENSE.md`; code is MIT (`LICENSE`).
- No em dashes or middot separators in any user-facing string (veil, hints, cards, panels,
  tooltips, loading messages). Commas, colons, sentences. Docs and code comments are exempt.
- Owner decisions that stand until Mike says otherwise: landmark labels OFF by default (the
  citywide tier is behind the L key); the About panel stays out of the bar (the "Credits" link in the bottom credit line opens it); fly is the only mode
  (orbit is the attract loop, walk is `__dbg.goWalk` only); everything that stands on the ground draws only within half a mile of the eye (Round 82, Mike: `NEAR_R` 804.67 m, the straight-line distance, so the circle tightens with height; the SEPTA vehicles and badges, the Indego docks, the Amtrak trains, the closures' drums, cones and pins, the marker posts, the plinths and the market tents; flights and ships keep their range; the concert placards and score bubbles are building-anchored events and keep theirs); every street outside the core is painted ON the drawn ground (Round 88, Mike: "if the elevation is going to cause clipping the road needs to be painted just above that elevation": `drapeConvex` cuts each strip and bend disc against the registered ground's cells so it sits exactly its lift above the mesh everywhere, `roadStrip` / `roadFan` in both loops, the decks and the bank roads keep the flat quad, `__dbg.roads()` counts them), the elevated decks are lifted over the drawn ground with a 7% grade limiter and `ovpIndex()` rebuilt after them, the far ring cedes a road in the wide box's 200 m margin only where `wideOwned` finds a wide segment along it (the wide extract holds only ways that enter its box, and `pack_city.py` cuts a local way out of the 150 m band only when the way has a node inside the box), and `schEdges` reads to 80 m (at 40 the Round 87 bank blend in `groundMeshLandY` handed every road in the city the DEM); the wide loop routes a building to the curtain-wall glass only for `isGlassStyle` (20 to 31: the style word carries variant flags at 32 and up, and `style >= 20` drew 70,000 rowhouses as glass from Sep 2 to Round 88, which was the pink inner tier); the lamps are a photocell (`lampUniform`: first light 1.5 degrees over the horizon, full at -3, the cloud deck bringing it 3.5 degrees forward and storm gloom 2 more; the windows take the same advance), the moon takes the sun's deck term and `glintK` kills the water's sparkle under a deck, the cloud deck is the low and mid cloud with the high layer taken out of the total's 0.45 share (`WX.high`) and a METAR layer based at 6 km or more not counted; the skyline theme's gain is saturation-aware (a saturated hue takes 0.3 of a white's, so the red stays red under ACES), the stadiums' night sheets are neutral white, and the Walt Whitman carries the Ben Franklin's lamp standard every 36 m a side with no LED strings; the closed blocks, the historical markers and the public art carry pins since Round 82 (the aircraft badge's casing in the layer's colours: orange or gold with a drum, PHMC blue with the keystone, gold with a plinth; `pinTexture` / `pinMesh`), the trains had theirs from Round 80; SEPTA/Indego markers and the ground pins are occluded
  by buildings, and so are the concert placards and score bubbles (Round 62: a roof-grid line of sight, `losClear`,
  their pins depth-tested), neighborhood names and the search pin are not; roof forms come from the LiDAR
  streaming pass, then OSM roof:shape, then the lottery, packed in the roof word (see
  pack_city.py); storefronts come from `storefronts.b64`, and the outer districts' wall colours
  from Mapillary block faces (`wide_walls.b64`, colour byte plus a trim/window hint byte, 21.9% of the tier
  photographed; a dry-run bake never ships; the far ring and the towns draw their low walls from a
  1,024-colour reservoir of the outer districts' final wall colours (Round 57) at `FAR_LIGHT` 1.0, an exact
  statistical match, with only the roof caps lifted (`FAR_CAP_LIGHT` 1.23, matching the two tiers' cap means):
  Round 68's 1.8 gain was compensating a structural difference with a colour error and clipped 81.8% of the
  far ring's red channels at 1.0, which is the pale salmon Mike called out in Round 87, so it went and
  `farGain` keeps a monotone soft knee in place of the clamp; within the outer districts `wallInv`'s
  `WALL_LIFT` 0.45, `WALL_FOLD_MAX` 0.6 and `WALL_WARM` 1.3 hold the photographed and invented populations
  within 4% of each other, from 94.5% (measure with `__dbg.colStats()` across the York Street band before
  touching any of them), and since Round 65 every merged far-ring strip carries its own members'
  roof colour and OPA word instead of its 400 m cell's mode, so no tier reads darker past the outer districts' edge);
  the far ring draws the same road classes as the wide tier since Round 87 (`fetch_city_streets.py` supplements
  `fetch_city.py`'s query with `unclassified`, `living_street` and `pedestrian`, which is what Fairmount Park's
  drives are tagged, and `pack_city.py`'s `LOCAL_CLASSES` cuts all of them out of the wide box so the two tiers
  never pave one street twice; `service` stays out of both, so a park drive can still end where a service road
  meets it); facades come from the 19-style vocabulary in `fabricStyle`/`towerStyle` (app.js) and the
  Center City towers from `towers.json` (research-derived facade archetype, crown, tint); the
  Schuylkill's course and its park reach's water come from `schuylkill.json` (OSM waterway ways),
  and the packers inset any record whose wall shares a plane with a larger one facing the same way (`pack_common.py`, Round 71: the far ring
  and the towns too, over their own coordinate grids) while the facade shader fades a floor pattern under 1.5 render pixels a floor (`rowPx`) rather than alias it, by day only: after dark the
  lit windows stand to the distances they always did (Round 73 coda); the look leans toward
  Cities: Skylines 2 (reflective tinted window glass with sun-aware reveals, one glass tint per building carried
  as the `aTint` vertex byte (never a world-position hash), brick, stone, panel and stucco textures in the facade
  shader with every joint in anti-aliased relief, cornice and wall-end shading, limestone trim and mortar, seamed
  roof membranes (Round 54), a deep-blue sky with a ray-marched cumulus deck (a 720 m slab from 1,900 m,
  `CLOUD_STEPS` samples, sunlit tops and self-shaded bellies; Round 67's field of Mike's nine low-poly cloud models from `3d assets/Clouds`
  (`CLOUDS_DATA`, `CLOUD_FIELD`) was reverted the same day at his call and is built only behind `?clouds=lowpoly`) whose shadows slant by the
  sun, the real Moon (Round 64: `lunar()` checks against JPL DE421 within 0.06 degrees; drawn `MOON_SCALE` 2.0 times its
  true size with the near side's maria in a celestial-north frame, only its lit part ever drawn, by day washed by
  the sky, never through the sun's glare, its halo 0.06 by the square of the lit fraction since Round 73), clear air 8 to 40 km by day (the whole city stands clear from any height) and about 3 to 16 km by night, both scaled by the city's live PM2.5 since Round 75 (Air Management Services' hourly core-site readings, `AQI`/`WXFX.haze`: 22 ug/m3 keeps the full distance, an Unhealthy day is 0.28 of it with a tan smoke tint on the sky, fog and sun, the AQI on the time panel), slate-teal body-colour water (`COLORS.water` 0x163038, Round 54) as a moving noise field with calm
  ripples and only a restrained shoreline lift (no foam line, no lit floor), a painted olive meadow on every green AND on all bare ground (Round 52: `groundSurfMat`, the
  same meadow and the same darker-blotch mottle as the parks, parks and ground are one surface; no park
  shade spread, no ground retint), an instanced tuft field near the camera on parks and bare ground, lumpy
  flat-shaded low-poly crowns with no leaf cards on any device (Round 58; `CARDS` above 0 brings them back); the PPR tree
  survey is citywide since Round 87 (150,887 packed, 106,887 drawn against 40,982: West Fairmount Park held zero trees
  before it), the wide box keeping the 80-face crown on its 3x3 chunk grid while the 101,849 trees beyond it take the
  phone's 20-face crown on an 8x8 city grid (the 80-face crown on all of them measured 18.0 M triangles a frame against
  13.4 M), `boleH` capped at 9 m so a 60-inch park oak carries its crown clear of the grass, and the woodland tint from
  PPR's parkland rings on all four far ground strips, not only the NW patch; wind in the crowns and blades, saturated palettes, rooftop
  clutter on desktop, awnings, lane paint on every road (`aLane` + `lanePatch`: a double yellow centre from
  6.5 m wide, white dashes by width, edge lines on the divided highways, nothing on service and footways),
  stored-dark asphalt lots (`LOT_COL`) with stall stripes that fade past 500 m, and every surface lot, industrial and retail yard, rail yard and apron in the city paved from `paved.b64` (`fetch_paved.py` / `pack_paved.py`, the 'Paving the lots and yards' step, `conformDrape` under the parks), and on desktop WebGL2 an HDR
  post pipeline: half-float target, ACES + sRGB composite, bloom on the sun, the glints and the cloud rims
  with the markers and labels masked out of it (`postRaw(mat, { mask: true })`), `?bloom=0` off), never its
  assets; every flat outside the core (parks, lots, aprons) is laid with `conformDrape` on the drawn ground
  mesh (`groundGrids`/`groundMeshY`), never with `drapedPoly` (its point cap put big sheets at 36 to 61 m
  against a 25 m mesh and the ground rose through them); the Round 54
  key-to-fill ratio (sun 1.85, hemi 0.12 + 0.42 dayF, the Sep 8 rebalance of Round 50's 2.0 / 0.10 + 0.36) and the deep-blue zenith stand;
  the outer curtain wall uploads with `geometry(true)` (aStyle, aBase, aTint; `tests/test_vbuf.py` guards it) and reads
  terrain-relative floor datums, the Comcast towers have their own rhythms (styles 24 / 25) and the CTC a `blade` crown,
  researched landmarks never take the random penthouse or mast; the HUD is slate panels with limestone lines
  (`--panel`, `--line`, `--limestone` in style.css, the manifest and theme-color follow `--ink` 0x161a1e); a search result glides in and
  circles its spot until the first input takes flight (live buses are followed, not circled).
  The clock is never remembered: every load is Philadelphia's own time, and only a copied
  link carries a pinned clock. The two stadiums are built after the wide loop from
  `south_geometry_research.json` and light up at night; the sports complex is asphalt with
  striped stalls (`parking_south.json`), and ESPN scoreboards put a score bubble over a venue
  during a Philadelphia home game. Ticketmaster's listings (Round 56: `ops/concerts_bake.py` bakes them
  to concerts.json on the VPS every 15 minutes, the key only ever in `/etc/philly3d/concerts.env`) put a
  concert placard over its venue from 9 am Philadelphia time on the day of the show until the show ends,
  judged by real time, never the pinned clock (the farmers' markets are the opposite, Round 76: `markets.json` from `fetch_markets.py` / `bake_markets.py`, the 34 city markets pitch striped tents in four colourways only while the MODEL clock says they are open, a pinned clock included, `marketOpenAt` in app.js, tap a tent for the card, search by name; and Round 77's `markers.json` from `fetch_markers.py` / `bake_markers.py`: the 348 PHMC historical markers as blue-and-gold posts on the sidewalk facing their street with the full text on a wide card, the 224 active Percent for Art works as plinths, both in the search index, each behind its own layer since Round 83 (Historical Markers on J, bit 4096; Public Art on O, bit 8192; `LAYER_MASK_V4` 16384 marks a fourteen-bit link, `parseHash` keeps 32767); and Round 78's `landmarks.json` from `fetch_landmarks.py` / `bake_landmarks.py`, the city basemap's 5,932 named places in the search index only, fifteen kinds through `LM_KIND`, labels still off; and Round 79's live street closures: `ops/closures_bake.py` on the VPS trims the Streets Department's StreetSmartPHL permits and paving status to `closures.json` every 30 minutes, the page posts drums across a closed block and cones along a partial or footway closure, lays fresh asphalt strips on the season's paved blocks, empties typical traffic on a closed block (`CLOSE_TRAFFIC`), the U key and the twelfth layer bit 2048 with `LAYER_MASK_V3` 4096 marking a twelve-bit link; and Round 80's Amtrak trains on the eleventh bit 1024 and the K key: `bake_rail.py` bakes the Amtrak-operated OSM rail ways to `rail_amtrak.json`, the page draws the corridor and rides the trains along it (`railSnap`, `railWalk`, consists by route; since Round 85 the ways are stitched into chains by their shared nodes before anything is drawn, one height profile per chain with the chain ends pinned to shared node heights, a bridge-tagged or over-water run ramped between its abutments with a steel deck and piers and floored 9 m over the water only where it crosses the Schuylkill's outline, the ballast a continuous skirted ribbon on the drawn ground, and 30th Street Station's covered lower level held 7 m under the concourse plateau and reached through two open portal cuts, `RAIL_CUTS` / `railCut`, headwalls with dark mouths, the trains riding through under them; Round 87: a chain carries its tunnel and bridge flags PER SEGMENT from the way each belongs to, never combined from the endpoints of a simplified chord (the old OR turned six tunnels of 32 to 223 m in Fairmount Park into 1,130 m of undrawn holes and an AND surfaced the station's lower level mid-concourse), the shed window is `RAIL_STATION` and contains both cuts whole (the hand-typed z band cut through them and left 889 m undrawn with all eight tracks stopping 7 to 36 m short of the mouth), and `RAIL_LIFT` 0.75 stands the ballast proud of the ground instead of flush with it), `ops/amtrak_bake.py` writes `amtrak.json` every 30 s from Amtraker with the page pulling Amtraker itself when the file is stale, Amtraker credited under ODC-By; the reckoning is Round 87's: `AMTRAK_RUN` 480 s must cover the measured fix lag plus interval (at 240 the head parked for 169 s of every 224 and then teleported by 169 times its speed, which is what Mike saw), `AMTRAK_SNAP` 400 m, `adv` signed and rate-limited, the trains integrating REAL elapsed time rather than the render loop's clamped dt, the direction a world unit vector re-derived against each chain's tangent (a sign is meaningless across chains stored in opposite order), `railSnap` taking a `prefer` chain with a 1.5 m margin and `RAIL_STEP` 6 m so a consist cannot hop the parallel track 4 m away (12 to 22 per cent of a curving consist's cars did), and the direct fallback carrying the clock offset the baked path learns; Mike removed SEPTA rail in Round 20 as underground, and Amtrak is on the surface (Round 85 dropped Norfolk Southern's Harrisburg Line, 36 freight ways up the Schuylkill's east bank the name clause had matched); and Round 81's skyline lights: after dark the researched crowns flagged `theme` in `towers.json`, One and Two Liberty Place's chevron trim, City Hall's floodlit tower and the Ben Franklin Bridge's cable strings, deck nodes and tower wash glow in the night's colour, a Philadelphia game day's team colour first (Eagles, Phillies, Flyers, Sixers, regular season and postseason, home or away, ESPN's scoreboard for the day viewed), else the cause on BOMA Philadelphia's Building Illumination Calendar (`lights.json` from `fetch_lights.py` / `bake_lights.py`, inlined at build and re-baked twice a day on the VPS, the served copy taken when newer), else every element's own white; the theme follows the MODEL date like the markets, several colours are dealt across the buildings and run in bands along the bridge, every change eases 20 s, no layer bit, `?lights=<team|colour|hex|off>` pins it, the PSFS sign never takes it, and the bridge's walkways carry a lamp a panel a side on the streetlamps' material; Round 84, Mike with four photos: the Xfinity Mobile Arena lights with the skyline (a band under the roof edge, a wash on the upper wall), One and Two Liberty Place carry the neon along the sloping edges of every gable end (the nested chevrons; the eave trim unlit; One Liberty's spire white every night with a red beacon, its central bays proud of each face), the whole of City Hall is washed (the block, the mansards, every pavilion), William Penn is rebuilt from the postcard and floodlit warm, Rocky stands on his plinth at the foot of the museum steps, the Comcast Center's crown floors (20 m) and the top third of the CTC's blade (48 m) light in four stacked bands that take a night's several colours (the flag on a red, white and blue night; the blade's length stays white), and every tower of 120 m or more without a night accent gets one (`TALL_LIT_H` in `bake_towers.py`: a `band` on a flat parapet, a strip on a notch, 37 themed towers); Round 85, Mike with two more photos: the FMC Tower carries a light line on every floor edge of its real footprint (`led` in `towers.json`, `ledRing`), the Comcast Center's crown is an LED line proud of every crown floor on the style's own pitch over a dim wash, the CTC's fin is slender with a ladder of light bars, every one in the night's colour and the top third cycling a many-colour night, thin LED parts carry `aGain` 1.6 on the theme mesh and, on a team night, the team's stripe pair (`stripes` in `LIGHT_TEAMS`: green and white, red and white, orange and white, blue, red and white) through a second uniform bank (`uStripe0..3`, slots of 4 and up are stripe indices) while the skyline keeps the one team colour; and the river bank: a road within the Schuylkill's 40 m bank carve reads the DEM, never the carved slope (`groundMeshLandY`), no roadway sits under 1.2 m over the water, the tunnel-tagged Expressway chains draw only where they stand clear of the ground, and `bake_overpasses.py` decides over-water from the river's outline so the crossings stand 13 to 20 m up); one placard per building, the venues within 130 m each under their own
  heading (the Fillmore, the Foundry and Brooklyn Bowl are one building); the M key and the tenth layer bit; the pin lands on the roof
  from the build's `ROOF_GRID`, or on the score venues' roofs, stacking over a game there; a venue the page knows by name stands at its
  building whatever point the feed carries (`VENUE_NAMED`, Round 66: Ticketmaster's geocoder misses half the halls by up to 1.2 km).
  The Ben Franklin Bridge is Round 66's: Ben Franklin blue measured through the pipeline, the trusses over the roadway, granite portals.
  Phones: portrait shows the turn-sideways gate, the Move and Look thumb pads stay faintly
  visible in flight, and `detFarUniform` keeps lit windows alive to desktop distances; a phone also runs the plain shadow filter, redraws
  the buses' depth pass every 12th frame, caps its pixel ratio at 1.25 and may drop it to 0.72 under load, judged every 15 frames
  (Rounds 72 and 74), aims its shadow box at the camera in 300 m steps and freezes it above 600 m (Round 74). The first visit
  meets the guide (Round 60: `#guide`, eight cards on dots from `GUIDE_SLIDES`, computer and phone copy by
  `isTouch`, `localStorage philly3d.guide`), and the ? button beside the camera brings it back; the touch
  primer that followed the first touch is gone.
- The page is an installable app (Round 53): `build.py` writes `manifest.webmanifest` beside it,
  `sw.js` is the network-only worker (registered over https only, caches nothing), both deploy to
  the site root, `3d-model/index.html` is the Pages redirect for `start_url` `./`, and `fitView()`
  refits the canvas from every frame (the installed window resizes during the build).
- Commit the built page with the source, then push and run `deploy_philly3d.sh` after every
  verified update without asking (Mike, Sep 5, 2026: no permission needed to deploy from here on).

## URL flags

`?dev=1` exposes `window.__dbg` (camera/fly/scene/renderer handles, `wx('storm')`, `bolt()`,
`flightTest()`, `shipTest()`, `frameOnce()`, `goFly(...)`, `goWalk(...)`, `post`, `postMats()`, `skyMat`,
`cloudDeck`, `sunLight`, `hemi`, `refreshEnv()`, `railWalk(x, z, dx, dz, dist, chain)` (Round 87: pass a chain in and read `[6]` out to prove a consist stays on one track), `colStats()` (per-tier means of the wall and roof colours handed to the
chunk builders, styles, OPA words and roof forms, whole tier and a band either side of York Street), `perf()` with
per-step build timings, frame-time p50/p95, `renderer.info` and heap) plus an on-screen perf
readout. `?dpr=N` pins the adaptive pixel ratio. `?wx=<preset>` pins weather
(clear, overcast, fog, drizzle, rain, downpour, storm, hail, snow, blizzard, sleet) and, alone,
pins the air at Good. `?aqi=<n|good|moderate|usg|unhealthy|veryunhealthy|hazardous>` pins the
air quality (Round 75: the live PM2.5 scales the clear-air distances and tints a smoke day;
`__dbg.aqi(n)`, `__dbg.aqiState()`).
`?logdepth=0` is the depth-buffer escape hatch.

## Where things are

`app.js` reads top to bottom with `// ---- banner` comments (grep them): config, dom,
helpers, lighting & sky, data-driven build, overpasses, living water, terrain, ground/water/
roads/parks, the city fabric (facade shader), landmark spires, researched landmark models,
museum ships, the three towers, the outer districts (`wide.b64`), the far ring and the towns
across the city line (`city.b64` and `outskirts.b64`, one `raiseRing()` decoder), trees, labels, controls, modes & viewpoints, live SEPTA transit, layers panel, street names,
places, address search, live Indego, live flights, live ships, live Amtrak trains (their tracks
sit before the SEPTA fleet step), traffic, streetlights, the skyline lights (Round 81: the theme resolver, the bridge's strings and lamps), the live street closures, farmers'
markets on the clock, the historical markers and public art,
solar clock + weather (and the air quality), build & loop; the post pipeline sits with the renderer near the top. Build steps are `step('Name', fn)` calls run in order by
`build()`. `template.html` is the chrome, `style.css` the HUD + embedded Montserrat,
`about_body.html` the hidden About panel. Pipeline scripts and data files are tabulated in
`handoff.md` ("What's in 3d-model/").

## Deploy

`3d-model/deploy_philly3d.sh` builds and rsyncs to the VPS and verifies philly3d.com against
the local sha256 (stages + chmods 644 because this checkout's files are 0600). **philly3d.com is
the site.** Mike retired the GitHub Pages copy on Sep 17, 2026: do not deploy to it, wait on it
or verify it. `git push` is now only for the history, and the built page is still committed as
the artifact of record.

Pushing from this machine needs the `gh-ssh` remote, not `origin`. `origin` is HTTPS and the
keychain does not serve its credential to a non-interactive shell; `~/.ssh/harkdigital_laptop`
is the repo's `philly3d-laptop` deploy key (read/write since Aug 26) AND the VPS key, but
`~/.ssh/config`'s `Host github.com` block pins the unrelated Phade deploy key with
`IdentitiesOnly yes`, so ssh never offers it to github.com. The `github-sht` alias does, and
`gh-ssh` points at it: `git push gh-ssh main`. Two repo-scoped deploy keys cannot share one
`Host github.com` entry, which is why it is an alias. `origin` stays HTTPS on purpose: this
checkout lives in Dropbox, so a machine-local alias in `.git/config` would follow it to the
other Mac and break there.

## Read before changing anything

`handoff.md`: file table, build, architecture, and the "Hard-won gotchas" (winding, z-fight
layers, earcut orientation, the r149 colour pipeline, freeOnUpload vs frustum culling).
`devlog.md`: the full round-by-round log, Rounds 1–45 plus the VPS incident, with every
decision, reversal and measured fact. Find the entry for whatever you are touching first.
