# Philly3D development log

The round-by-round log that lived under "State & backlog" in `handoff.md` until
2026-09-01, moved here verbatim. Nothing was rewritten: the only additions are the
`###` headings (inserted above each round or dated block so the file is navigable)
and this preamble. "Everything above", "the About panel" and similar references in
the early entries point at the handoff.md of the day they were written; the current
architecture, file table, build commands and gotchas live in `handoff.md`, and the
agent-facing summary in `CLAUDE.md`.

Rounds 1 and 2 are the "Realism pass" and "Realism round 2" entries; the numbered
rounds start at 3. Rounds 22 to 25's first half are logged as bullets inside Round
21's entry (they were shipped from one session).

### Initial build (Aug 14-15)

Done and verified: everything above, on desktop + mobile viewports, zero console errors.
Reviewed by a 25-agent adversarial pass (pan-basis math bug, trees-in-buildings, and debug
leakage were found and fixed).

### Aug 15 fidelity pass

Built in the Aug 15 fidelity pass: terrain/trench/shoreline/basin, museum ships, Custom House
(85 m), Hilton (70 m), Independence Hall steeple, Congress Hall / Old City Hall / Carpenters'
cupolas, Second & First Bank porticos, the towers' 1 m podium plaza with berms, Abbotts Square
and its neighbors, flush gable ends + box cornices, the styled facade shader.

### Aug 23: solar clock, DEM terrain, the wide expansion

Built Aug 23: solar clock + time panel; DEM terrain; facade-local windows + AA; Abbotts' square
north end; pool clear of berms; the wide expansion (Center City, South Philly, NoLibs,
Fishtown/Kensington) with `building:part` skyscrapers, generic church steeples, outer labels, and
the Ben Franklin Bridge on OSM/DRPA geometry.

### Round 1: Realism pass (Aug 24)

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

### Round 2: Realism round 2 (Aug 24, afternoon)

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

### Round 2 adversarial pass (Aug 24)

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

### Round 3 (Aug 24, evening)

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

### "Hollow buildings" report (Aug 24 night)

**"Hollow buildings" on Mike's machine (Aug 24 night):** his screenshots show near walls
losing the depth test (far walls' fronts punching through, triangle-shaped slivers) SE of
City Hall. NOT reproducible in the Chromium in-app browser; the packed rings, winding,
and normals were all verified correct programmatically (3.36 M wall tris, 0 winding/normal
mismatches; 1 invalid ring in 112k, elsewhere). Diagnosis: `logarithmicDepthBuffer`
(per-fragment gl_FragDepth writes) misbehaving on his browser — Safari/Metal WebGL2 is the
known offender. Fix: Safari UA now gets a standard depth buffer (near 1.0, far 26000 —
also raised from 9000 for the citywide view; ?logdepth=1/0 forces either path). If hollow
walls ever show on Chrome too, this diagnosis is wrong — reopen with an exact-view repro.

### Hollow buildings RESOLVED (Aug 24, Round 4)

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

### South extension (Aug 23)

South extension (Aug 23): Lincoln Financial Field and Citizens Bank Park are `stadium` relations →
rendered as seating bowls (type 8) around sunken fields, with the Linc's sideline canopies and
CBP's light towers; Xfinity Mobile Arena (ex-Wells Fargo Center, type 9) as a flat-topped oval;
the Walt Whitman Bridge follows OSM's motorway alignment (`wwb.json`) with towers at ±305 m of the
water-crossing midpoint, deck 46 m over the river.

### Wide-area backlog

Wide-area backlog (research in `wide_landmarks_research.json` has heights/massing for ~150
buildings): the Market-Frankford El viaduct (railway ways were fetched but not packed — add
`railway=subway` ways as an elevated ribbon at +7 m along Front St / Kensington Ave); City Hall's
tower is in via `building:part` but the Penn statue / clock stage are plain; church-specific
heights (St. Michael's 50 m, St. Peter the Apostle 70 m, Assumption BVM twin towers) could replace
the generic steeple; Piazza/Schmidt's Commons, Waterfront Square towers and Rivers Casino are
plain OSM boxes; Camden's Battleship New Jersey and Adventure Aquarium are not modeled.

### Ideas discussed but not built

Ideas discussed but not built (see also `geo_audit.json`):
- Dusk/night mode with lit windows (would suit the bronze-glass towers)
- Guided fly-through tour of the viewpoints
- Marriott's hipped wing roofs (currently a flat dark cap); Hopkinson House balcony relief
  (currently color only); The Ryland's rooftop pool (OSM has it, but its true position
  falls off our smaller OSM-footprint deck)
- Penn's Landing park-cap construction area is bare in current imagery — could model the
  finished park

### Round 4 (Aug 24, late)

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

### Round 5 (Aug 24, night)

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

### Round 6 (Aug 24, late night)

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

### Round 7 (Aug 25)

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

### Round 8 (Aug 25)

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

### Round 9 (Aug 25)

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

### Round 10 (Aug 25)

Round 10 (Aug 25 — "broken roofs" root-caused, three separate defects):
- **Dishonest gable quads**: the gable pass accepts only a simplified quad that is
  convex, near-rectangular (adjacent-edge |cos| ≤ 0.35), clearly elongated
  (long/span ≥ 1.35), and area-matched to the true footprint (±14%) — skewed
  diamonds tented into leaning pyramids, squarish quads spiked.
- **Paper-thin slivers**: OSM party walls/alley strips mapped as buildings (effective
  width 2·area/perimeter < 1.7 m) extruded into 15 m floating blade walls — now
  clamped to 3.2 m garden-wall height.
- **Gables on commercial lofts**: eligibility capped at h < 12.5 m (was 17) — the
  14-15 m flat-roofed Old City lofts were getting long ridge gables whose edge-on
  slopes towered over the streetwall as "blades" (THE Chestnut St spike by Glory:
  a perfectly honest 17×4.9 m gable on a 4-storey loft). Society Hill's 8-12 m
  rowhouse gables verified intact after the cap.
- **Glory finished to the photo**: upper three brick floors now span the whole lot
  flush with the iron front at the street (OSM steps the tall mass back — a lot-
  spanning box bridges it), GLORY board (red band on white) over the transom, the
  tall verdigris blade sign on the pier, and the wrought-iron lightwell railing.
- **Round 10b LOCATION CORRECTION (Mike)**: the three parcels first customized were
  at the 2nd St corner — WRONG. Philly numbers ascend WESTWARD from Front on the
  100-block, so 126 Chestnut is a quarter block in from FRONT St: the deep narrow
  lot with area-weighted centroid (115.1, −283.8). The corner parcels reverted to
  generic; the builder now dresses that single lot (iron front + piers + signs +
  brick floors 3-5 over the front 26 m, low rear range down the 40 m lot).

### Round 11 (Aug 25)

Round 11 (Aug 25):
- **Independence Hall rebuilt to the photo**: gable block (was hip) with white
  ridge-deck balustrade, paired brick end-chimney masses, marble string course;
  engaged south tower — brick shaft (style-1 arches), white cornice + balustrade,
  clock stage with 4 rimmed dials, bell chamber with dark open arches, upper
  balustrade, faceted dark bell roof, drum, spire, gilt ball + vane to ~51 m;
  style-4 brick arcades auto-spanned to Congress Hall and Old City Hall (length
  computed from the OBB gap along the block axis).
- **Glory round 2 (Mike)**: full walk-in porch — ground floor recessed 2.3 m
  behind the pier line, iron band above forms the ceiling; z-fight fix — the
  footprint-extrusion + box mix had coplanar walls, replaced by ALL-box massing
  where every pair either clears or interpenetrates at a different width (the
  session's z-fight rule: never coplanar, always offset or interpenetrating);
  the sign is now REAL "GLORY" lettering — a small CanvasTexture (Futura-stack
  900 red on white, sRGB encoding) on a MeshBasicMaterial plane added straight
  to groupCity (unlit = reads as a lit sign at night; lifted via siteY, not
  liftB). First in-model text — the pattern to copy for future signage.

### Round 12 (Aug 25)

Round 12 (Aug 25 — grounding pass, "situate everything"):
- **classic() OBB-gable fallback REMOVED**: non-quad footprints retry simplifyRing
  at 1.4 m; still no quad → flat cap, dormers skipped. OBB roofs floated beside
  L-plan walls (City Tavern's chimney-side floaters).
- **Independence Hall explicit massing**: its OSM footprint is the whole 84 m
  complex, so the round-11 OBB-derived balustrade/string-courses stretched 100 m
  bands across the facade (Mike's "white line"). Now a pt2(u, s) frame from the
  north face: 33x13.4 block + footprint-true quadGable, 19 m ridge balustrade,
  end chimneys, string courses on the block only, hyphen arcades (style 4),
  two-story wing pavilions with 4-side caps, the full steeple. No classic() call.
- **columnRow sinks 2.2 m below grade** (like walls/trunks): colonnades lift at the
  building centroid and sloping lawns left the Second Bank's SOUTH portico columns
  airborne (proved by raycast: ankle-height rays passed through to the wall).
  Both banks also gained sunk marble stylobate slabs under their porticos.
- **Glory round 3**: engaged pier order flush with the brick plane (nothing proud
  of the building), floor-2 glazing recessed 0.5 m, ground floor a real 2.4 m
  walk-in porch, widths pulled 15 cm off the lot lines (party-wall shimmer), sign
  board mounted proud of the pier plane so nothing clips the lettering.

### Round 13 (Aug 25)

Round 13 (Aug 25 — the LiDAR true-massing pass, per `lidar-massing-plan.md`):
- **Every guessed height replaced by a 2022-LiDAR measurement.** Shortcut found per the
  brief's "check for prebuilt products first": the City of Philadelphia's
  `LI_BUILDING_FOOTPRINTS` ArcGIS layer carries `max_hgt` (ft AGL) derived from the
  2022 QL1 flight for 546k footprints (99.9% populated, validated against Comcast
  towers/BNY/FMC/the towers themselves to ~1%; The Laurel confirms the 2022 epoch;
  buildings finished after the flight have NULL and correctly keep their OSM values).
  No county-wide point-cloud processing needed for heights.
- **Pipeline** (all committed): `fetch_footprints.py` (paginated GeoJSON → local-frame
  cache), `lidar_join.py` (shapely STRtree polygon-overlap join → patches
  `scene_wide.json`/`scene_south.json` h in place, emits `lidar_city_heights.json`
  {way id: h} for pack_city + `lidar_cache/core_join.json`), `lidar_core.py` (core
  roof forms from the raw point cloud + scene.json patch). Join rules: coverage ≥25%,
  area-weighted mean, dominant-tall-mass rule (tallest pieces covering ≥50% set the
  height — a tower sharing its OSM way with a podium must not read short),
  contamination guard (max_hgt > 3× approx_hgt = crane/tree → skip), and talls >30 m
  are RAISE-ONLY (OSM max-height tag semantics; Independence Place twins stay 96.9,
  known wrong-high tags are REALISM-overridden anyway). `pack_city.py` `parseH` now
  takes the way id: measured beats levels/defaults, explicit height tag survives if
  taller. Coverage: wide 96.7%, core 98.7%, far ring 90.8%, south 77% (the misses are
  Camden/out-of-county — no city data — plus post-2022 construction and demolitions).
- **Core roof forms measured** (`lidar_core.py`): the 9 NOAA Digital Coast COPC tiles
  covering the core (EPSG:6347, NAVD88, leaf-off Apr 2022, ~285M pts — the flight is
  ground/non-ground classified only, NO building class) → 0.5 m first-return min/max
  grids; cells with max−min > 4 m are bare-branch canopy and dropped; roof surface =
  per-cell MIN (tree-robust in leaf-off). Per building (eroded 0.5 m): AGL percentiles
  off a class-2 ground grid, flat if P95−P08 < 1.15, else axial aspect statistics on
  the roof-grid gradient — |Σw·e^{2iθ}| ≥ 0.5 → gable (ridge ⊥ mean aspect),
  else |Σw·e^{4iθ}| ≥ 0.5 → hip (axis disambiguated toward the OBB long axis).
  Result: 714 gables + 220 hips + 1,863 measured flats; eave = P08, ridge = P97.
  scene.json entries now carry `roof: [form, eave, ridge, ridgeRad]` (1 gable / 2 hip /
  [0] measured-flat) and `h` = ridge for pitched, P90 parapet for flat. Alignment was
  verified against the towers' 94 m cliffs (zero shift needed; NAD83(2011)↔WGS84 ≪
  the 0.5 m erosion).
- **app.js consumes measurements**: measured forms bypass the hash lottery and the
  h<12.5 cap (guessed gables keep both); the honest-quad guards stay for everyone —
  a measured-pitched footprint that fails them extrudes FLAT at eave+0.35·rise, never
  a floating slope. `quadGable` takes a measured ridge-direction hint (eave pair =
  axially closest to the ridge), new `quadHip` builds inset-ridge hips (measured only).
  Steeples now seat at the measured eave so they interpenetrate pitched roofs instead
  of floating at ridge height. Measured-flat (`roof:[0]`) suppresses the gable lottery
  — a measured flat stays flat.
- **quadGable bowtie bug found and fixed** (pre-existing, shipped): the ridge-near
  end passed to `slopeQuad` assumed ev[0].b always touches ge[0] — true only when the
  ring starts on a long edge. The other half of all gabled rowhouses rendered each
  slope as two wrong-diagonal triangles: a see-through wedge + a coplanar double wedge
  (~25% of the roof plane each). Verified by point-coverage test in node (area sums
  hid it — overlap cancels gap); now the near ridge end is chosen by shared vertex.
- **Validation** (`lidar_report.json`: stats, coverage, before/after histograms, known
  truths, top-50 deltas, method): One Liberty 251.5 (roof; spire is custom-built),
  Comcast Center 299.3 (real 297), CTC 343.6 (1,121 ft), BNY Mellon 242.4 (792 ft),
  Three Logan 226 (739 ft), Commerce Squares 174.4, Society Hill rowhouses 9–16 m
  ridges. Marriott Old City measured 14.0 vs the OSM height=4 lie (16.5 override still
  wins). Hilton measured 72.2 vs the research-built 70. Raycast-verified in the built
  page: flats within ±0.5 m of data, gable/hip ridges on the money, towers untouched
  at 97.1, zero console errors, 4.2M tris / 140 calls. Page 14.42 MB (was 14.29;
  city.b64 7.17 MB after real heights spread the merge buckets — still under 16).
- **Files**: `lidar_cache/` (gitignored) holds the 546k-footprint cache, the 9 COPC
  tiles (1.7 GB), `core_grids.npz`, `core_join.json`, and `scene_pre_lidar_backup.json`
  (scene.json as it was before the patch). Committed: the three scripts,
  `lidar_city_heights.json` (6.2 MB way-id LUT the far-ring pack needs), and
  `lidar_report.json`. Re-running from scratch: `fetch_footprints.py` (plain py3) →
  `lidar_join.py` (venv: shapely) → `lidar_core.py` (venv: laspy[lazrs], pyproj,
  numpy; re-downloads tiles via `lidar_cache/core_tiles.json` naming if absent) →
  repack wide/city → build. `--skip-city` on lidar_join reuses the committed LUT;
  `--grids-only` on lidar_core stops after the grid build.
- Known limits: Camden + county-line slivers keep OSM/default heights (no city data;
  NJ LiDAR would be a separate source); `building:part` skyscraper pieces keep their
  OSM stack heights by design; the south set's 77% is the stadium/navy-yard fringe.

### Round 14 (Aug 25)

Round 14 (Aug 25 — Rotten Ralph's, from Mike's Street View reference):
- **201 Chestnut (NW corner of 2nd & Chestnut) custom-built to the photo.** The lot is
  two OSM strips front-to-back — both matched in `REALISM_NEAR` (keys `ralphs` +
  `ralphsMid`, the latter builderless so the generic pass skips it) and spanned by one
  massing in the front strip's OBB frame: white corner block (LiDAR parapet ~8.9 m)
  wearing a continuous arcade of tall blue-framed round-arched windows — 9 bays on
  Chestnut, 5 on 2nd — each bay = dark glass rect + half-disc (walls material, style 3
  — the `detail` material renders glass pale, walls render it dark), a blue
  RingGeometry arch, engaged jambs and a white sill; storefront base with engaged
  piers, recessed dark glass, blue double door, blue/white striped awning (26
  alternating tilted boxes — geometric stripes, no texture, night-correct); white
  spandrel band and ledge, brick parapet band + coping wrapping both street faces
  (east-face copies get slightly DIFFERENT heights — the wrap-around bands meet at the
  corner and identical heights would put coplanar top faces there); roof deck,
  bulkhead, flue; hanging corner blade sign as TWO back-to-back CanvasTexture planes
  (one DoubleSide plane mirrors the text on its far side — the Glory-sign pattern
  extended for blade signs). The taller rear mass (the graffiti party wall in the
  photo) stays generic, recolored dark brick via a non-custom `REALISM_NEAR` spec
  ({color, style} without mode — that path recolors in place).
- Frame conventions for corner buildings (copy for future ones): u along the front
  made WEST, s across made SOUTH toward the street, P(u,d) walks the front line from
  the EAST corner; wall face planes land inset (FS/FE) and every applied piece ENGAGES
  its plane (crosses it) — proud decals on a solid box, since recessed glass inside a
  solid extrusion is invisible.

### Round 15 (Aug 25)

Round 15 (Aug 25 — Tier 1 of "every building like the photo": data-driven facades):
- **Every generic building now carries measured facade attributes.** Two new data
  sources joined onto all ~250k buildings:
  1. **OPA property records** (`fetch_opa.py` → 583,680 rows from phl.carto SQL API;
     `opa_join.py` collapses condo units to 508k sites by rounded point, then
     point-in-footprint joins with a 12 m nearest fallback — a site informs EVERY
     footprint containing it, because the core scene, wide scene and raw dump each
     carry their own copy of a building). Per building: use (row/detached/apts/
     store+dwell/commercial/industrial/civic), material (masonry/frame/stone/mixed),
     era (8 buckets from year_built; 'OLD STYLE'/'POST WAR'/'MODERN' code hints when
     year is missing), stories. Coverage: core 2,374/2,834, wide 100,835/111k,
     south 4,394, far ring 326,232 ways.
  2. **Sampled roof colors** (`roof_colors.py`): the city's public CityImagery_2024_3in
     tile cache (tiles.arcgis.com, z17 ≈ 0.92 m/px) sampled per footprint — median RGB
     inside the 0.8 m-eroded polygon (median rides over branches; 6,683 tiles cached in
     `lidar_cache/tiles/`), k-means'd to a 30-color palette. 510,219/519,599 sampled
     (98.2%). Palette in `facade_palette.json` (committed; build.py embeds as
     FACADE_PAL).
- **Where it lands** (`patch_scenes_facade.py` writes `b.fa=[use,mat,era,stories]` +
  `b.rp=paletteIdx` into all three scene files; packers carry TWO extra int16 per
  building — attr word u(3)|mat(3)|era(4)|floorH(5) and roof index; magics bumped
  0x5348545A wide / 0x5348545B city, old formats still decode):
  - Wall palettes by material×era (deep colonial brick → orange 1900s → postwar tan +
    perma-stone → modern blends; siding pastels for frame; Wissahickon-schist grays
    for stone — Germantown/Mt Airy read right now; industrial/commercial pools).
  - Styles from parcels: mixed-use/commercial ground floors get storefront style 5,
    industrial gets blank 3, and post-1935 residential gets NEW STYLE 8 — the style-0
    rowhouse dress with wider bays and NO shutters (shutters everywhere was wrong for
    North Philly). Pre-war keeps style 0 with shutters.
  - **True floor counts**: new per-vertex `aFloorH` attribute (quantized ×10 into an
    Int8; 0 = style default) feeds the shader's floor pitch for styles 0/5/8 and 2 —
    a 2-story postwar row now draws 2 window rows, not 3. Core parts get it through
    mergeColored (the single attribute-injection point), wide/far through the chunk
    builders. Guarded: only when h/stories ∈ [2.2, 5.2].
  - **Roof colors everywhere**: wide/far caps take the sampled color as cap vertex
    color (appendBuilding/appendB grew fh + capColor params); core flat roofs get a
    thin overlay cap (`capGeom`, emit-forward earcut) — at hFlat+0.09 because the
    rowhouse "cornice ring" is really a SOLID SLAB to +0.06 whose cream top used to
    play roof on every rowhouse; measured gable/hip slopes use the sampled color too.
- **Roof color calibration is a POWER CURVE, not a divisor**: on sunlit tops the
  legacy-linear lift + ACES render stored S as R ≈ 31.5·S^0.423 (darks amplified
  ~6×, lights ~2.3×). `roofInv` inverts per channel; canvas-pixel probes confirm
  rendered ≈ ortho-sampled within ~10 units across the range ([43,43,42] asphalt →
  [33,32,29]). Lesson recorded: calibrate stored colors against a MEASURED transfer
  curve, not a guessed constant.
- Page: 15.86 MB (+1.43 for the two words/building). Still under the 16 MB artifact
  cap but with only ~0.14 MB headroom — the NEXT data addition goes Pages-only or
  requires trimming. Zero console errors; 3.6M tris in city views (+30k for overlay
  caps). Old-format b64s still decode (dry-run verified before the data landed).
- Files: `fetch_opa.py`, `opa_join.py`, `roof_colors.py`, `patch_scenes_facade.py`,
  `facade_palette.json` committed; `lidar_cache/` additionally holds `opa_rows.csv`
  (77 MB), `opa_pages/`, `opa_{core,wide,south,city}.json`, `roof_{...}.json`,
  `roof_palette.json`, and `tiles/` (6.7k ortho jpegs). Rerun order:
  fetch_opa → opa_join (venv) → roof_colors (venv) → patch_scenes_facade →
  pack_wide → pack_city (venv) → build.

### Round 16 (Aug 25)

Round 16 (Aug 25 — live SEPTA transit + the Frankford El):
- **Real-time vehicles.** SEPTA's public API sends NO CORS headers on either host
  (api.septa.org/api or www3.septa.org/api) but both honor JSONP (`?callback=`), so
  the app polls via short-lived `<script>` tags — works on GH Pages/localhost, and
  under the artifact CSP the tags simply never load (layer silently empty; the S bar
  button hides). `TransitViewAll` (~370 KB) every 15 s (25 s touch; skipped while
  `document.hidden`, refreshed on visibilitychange) + `TrainView` for Regional Rail.
  Hosts auto-flip after 3 consecutive failures.
- **What the feed really contains (measured, do not relearn):** subway L1/B1–B3 rows
  are schedule placeholders — `VehicleID: None/0/block_*_schedBasedVehicle`,
  `late: 998`, bogus `timestamp: 63240`, every one pinned at 15th St
  (39.952187, −75.15995). **SEPTA publishes no real subway GPS anywhere JSONP-able**
  (GTFS-RT is protobuf, no CORS), so the L and B are honestly absent. Filter: real
  vehicles need a fleet VehicleID, epoch timestamp (> 1e9), fix age < 5 min. ~700
  buses + ~40 trolleys (T/G/D) + NHSL M1 tracked in the city bbox
  (39.855–40.145, −75.30–−74.94); TrainView trains carry `consist` → car count.
- **Rendering:** ONE InstancedMesh (cap 1600) for all solid vehicles — unit box
  merged with a proud dark glass band, vertex colors × per-instance line color
  (bus silver, trolley green, G1 gold, NHSL purple, RR stainless), matrix scale =
  class dims; Regional Rail expands to its real consist, cars spaced along the
  heading. Second InstancedMesh (256, MeshBasic, depthTest:false, opacity 0.34,
  renderOrder 44) = x-ray ghosts for vehicles inside approximate underground boxes
  (CC commuter tunnel, subway–surface trolley tunnel) drawn 5.5 m below grade.
  `frustumCulled = false` on both (instance bounds don't follow the fleet — the
  classic InstancedMesh culling gotcha). Positions tween from poll to poll
  (t/(POLL+1.5 s), snap on > 420 m jumps); heading from the API compass, or derived
  from displacement when the API says 0 (rotY = atan2(cosθ, sinθ)); yaw rate-capped
  2.6 rad/s. Vehicles ride `siteY(x,z,'road')` + 0.22 (cached until they move 2.5 m);
  RR clamps to water+11 over rivers. `applyLighting` drives body emissive (warm
  interior glow) by `nightUniform`. 2 draw calls for the whole fleet.
- **Picking:** tap/click (orbit mode, or any touch) raycasts the two instanced
  meshes; `#vehinfo` card (route chip tinted per line, destination, kind · cars ·
  late/early/on-time · in-the-tunnel, next stop) follows the vehicle per frame and
  its text refreshes each poll. V key / the S bar button toggle the layer (button
  title shows the live tracked count); first successful poll after the veil lifts
  flashes a hint. Projection uses the scene origin from scene.json
  (39.945473644755, −75.14474803850973; x=(lon−lon0)·111320·cos(lat0),
  z=−(lat−lat0)·110574 — City Hall lands at (−1609, −766), matching the model).
- **The Frankford El is BUILT** (was backlog): OSM `railway=subway` non-tunnel ways
  seeded from named Market-Frankford ways, grown through short unnamed connectors,
  chained, loop-split at the far end (the two tracks join at the terminals — one
  centerline per corridor, ~2 m lateral error), Douglas-Peucker 1.6 m → `EL_TRACK`
  int arrays baked in app.js (~800 B): Callowhill portal → Frankford TC (10.2 km)
  and 46th St portal → 69th St (4.6 km). Deck = per-segment pitched boxes at
  ground+9.2 (7-pt moving average ×2), side rail strips, steel bents every ~24 m
  where clearance > 3.4 m, portal ramps descending into the ground over the first
  170 m (each chain STARTS at its portal). mergeColored + plain Lambert
  vertexColors; casts shadows. ~60 k tris, 1 draw call. If SEPTA ever publishes
  real subway GPS, elevated L trains should ride this deck (+9.2, snap to the
  EL_TRACK polyline within ~60 m).
- Files touched: app.js (SEPTA block before 'Charting the viewpoints' + hooks in
  frame/applyLighting/keydown), template.html (S button, #vehinfo card),
  style.css (#vehinfo), about_body.html (live-transit paragraph + SEPTA/Open-Meteo
  credits). Page 15.89 MB. Verified live: ~690 vehicles tracked, 739 solid + 21
  ghost instances, pick card shows real Route 17 "to 2nd-Market · on time · next:
  Market St & 4th St", toggle both ways, zero app console errors, 44 calls/1.9 M
  tris in the test view. NOTE for tests: synthetic PointerEvents with fake
  pointerIds make the orbit handler's setPointerCapture throw — use real pointers
  or ignore that error.

### Round 17 (Aug 25)

Round 17 (Aug 25 — rebrand to Philadelphia, transit pins, museum grounds, WWB):
- **Rebrand:** the fixed "Society Hill Towers" title block is REMOVED (template +
  CSS); the intro veil is now city-general ("A living model of / PHILADELPHIA",
  Enter the city); page <title> = "Philadelphia". The About panel keeps the tower
  history. File name stays society-hill-towers.html (URL stability).
- **Transit pins + findability:** every live vehicle flies a bobbing map pin
  (cone+ball InstancedMesh, cap 1024, MeshBasic vertex colors ×2, one per vehicle
  over the lead car; underground ghosts pin at street level). Pins scale with
  camera distance (clamp(dist/240, 1..8)) so they stay findable citywide. Picking:
  pins are raycast targets too, and a screen-space fallback picks the nearest
  vehicle within 30 px of a tap — plus the solid vehicle geometry gained skirt,
  windshield, roof HVAC and wheel blocks (all in the one instanced geometry).
  Picking works in EVERY mode (Mike's request): under pointer lock (desktop
  walk/fly) a click picks under the CROSSHAIR — screen center, 46 px fallback —
  since the cursor doesn't exist; lock state is sampled at pointerDOWN
  (vpWasLocked) so the lock-acquiring click still picks at the cursor. Unlocked
  (orbit/drag-look/touch) keeps the 8 px tap-vs-drag filter at pointer coords.
  BUS pins are SEPTA-logo badges (Mike's request): the official mark's SVG paths
  (Wikimedia SEPTA.svg, 500×369 box) are Path2D-filled into a 256×320
  CanvasTexture (white rounded badge + pointer tip, sRGB, anisotropy 4) on an
  instanced PlaneGeometry that BILLBOARDS the camera each frame
  (_sqB = camera.quaternion; transparent, depthWrite:false, renderOrder 12, no
  instanceColor so the texture keeps its colors). Trolleys/RR/NHSL keep the
  line-colored lollipop pins so line type stays readable. The About panel
  carries the SEPTA trademark/non-affiliation notice. NOTE: the Pages
  "is-it-live" poll must grep the FULL page or its tail — app.js markers sit
  after the ~14 MB data blob, so a first-120 KB range check reports stale.
  NOTE: the Sketchfab "SEPTA bus model" Mike linked is isDownloadable:false with
  no license — cannot be used; the procedural body got upgraded instead.
- **Art Museum grounds (Mike's screenshot):** three separate defects fixed —
  (1) OSM paved/park drapes near the hilltop rendered as sheared slabs (flatPoly
  per-vertex on the steep hill): all non-water areas within r190 of (−3080,−2210)
  are skipped, plus any paved-kind poly with a vertex in the museum zone;
  (2) the Rocky steps let the DEM bulge poke white stripes between flights: each
  flight now tops out just above the terrain under it (5-point sample) with a
  bottom-up monotonic sweep (never rises downhill), boxes deepened to −7;
  (3) "fill the white with green": the WIDE 25 m ground heightfield now carries
  vertex colors (groundMat clone + vertexColors, pushed into groundMats so the
  day/night retint still works) and cells inside the Fairmount zone
  (x −3690..−2480, z −2950..−1720) are tinted by the park/ground channel RATIO,
  feathered 80 m. A draped lawn was tried first and REJECTED: on the bumpy hill
  it rode above the road ribbons (the ground mesh interpolates coarser than
  siteY — never drape a big lawn over roads; recolor the ground instead).
- **Walt Whitman un-disjointed** (Mike's screenshot) — three defects:
  (1) OSM's motorway line hops carriageways mid-river (15 m right-angle jog at
  mid-span, wiggle at the NJ anchorage) — the span ±660 m around mid is now
  projected onto its straight chord before building (real bridge is dead
  straight), cum re-measured; (2) packed motorway river-deck segments under the
  custom deck: skipped via wwbNear(x, z[, r]) (distance to the raw WWB_PTS
  polyline, default r 85) in BOTH the wide and far road builders (deck-lifted
  segments only, so land approaches keep their ramps); (3) the flat gray band
  "second bridge" on the water was the wide ground heightfield: NED reads a
  made-land shelf ~3 m above water across the crossing — cells x 880..1950
  with demY in [water+0.6, water+4.5) within 260 m of the alignment now drop to
  the bed. Also: bridge-outline paved areas near the alignment are skipped in
  both area loops. Residual NED shelf patches remain in the south Delaware AWAY
  from the bridge (no NJ bank polyline yet — future fix would trace one).
- Verified: museum green + straight steps, WWB continuous with water under the
  deck, pins render/pick (Route 9 card via pin click), toggle, 692 tracked live,
  zero new console errors. Page 15.90 MB.

### Round 18 (Aug 25)

Round 18 (Aug 25 — address search, logo button, street-snapped buses):
- **Address search** (Mike's request): a magnifier bar button (+ `/` key) opens
  `#searchpanel` (timepanel-styled, bottom center) → OpenStreetMap Nominatim,
  key-less/CORS-open, `bounded=1` to the model box (viewbox −75.30,40.145,
  −74.94,39.855) → up to 5 result rows; the first (or a clicked row) flies the
  ORBIT camera there (goalTarget/goalR 300/goalPhi glide — setMode(ORBIT) first)
  and drops a bronze pin (septaPinGeom + gold basic material, distance-scaled,
  bobbing) with a `.lbl.smark` label for 20 s (updateSearchMark in frame()).
  Hidden under the artifact CSP like every live fetch. Nominatim credit in
  About. Verified: "Citizens Bank Park" lands at (−1855,4373) — the modeled
  stadium is at (−1869,4375); "Independence Hall" pins (−450,−377).
- **The S button now wears the SEPTA mark**: inline SVG (official paths + warm
  white backing rect) in `#btnTransit`; `#btnSearch` gets a stroked magnifier
  SVG (currentColor). `#bar .iconbtn svg` sizing in style.css.
- **Buses no longer clip buildings** (Mike's screenshots — GPS scatter ±10 m +
  straight tweens cutting corners at intersections): a road-network spatial
  hash (`septaRoadGrid`, 36 m cells; fed UNdensified drivable segments — core
  loop alongside addRoadSeg (non-pedestrian), wide + far loops pre-densify for
  t ≤ 5) gives `septaSnapRoad(x,z,maxD)` = nearest-centerline projection.
  updateTransit snaps buses+trolleys (never RR/NHSL/ghosts) every ~120 ms
  staggered, then exponentially glides DISPLAY coords (v.dx/v.dz, τ≈140 ms —
  smooths the segment-flip pop at intersections). Everything visual (cars,
  pins, badges, card follow, pick fallback) uses v.dx/v.dz; raw v.x/v.z stays
  for yaw derivation and the next snap. Snap radius 20 m — a vehicle farther
  off the grid (depot, private lot) rides raw.

### Round 19 (Aug 25)

Round 19 (Aug 25 — street names on the roadways, search fenced to the city):
- **Street-name labels** (Mike's request): `bake_street_labels.py` computes
  placements offline from scene.json + scene_wide.json + scene_south.json (the
  packed wide/far road formats carry NO names — that's why baking, not decode)
  → `street_labels.json` (4,719 labels, 915 unique names, ~108 KB), embedded by
  build.py as ST_LABELS. Format: names[] + flat [nameIdx, x, z, bearingDeg,
  cls]. cls 0 major / 1 minor / 2 core-detail. Spacing 220–600 m by class,
  min length 40–200 m, same-name dedupe within 90 m, wide placements inside
  CORE_EXT±40 dropped (core places its own, denser, incl. named alleys).
  Bearing pre-flipped for north-up readability (west→east / south→north).
  Runtime ('Lettering the streets'): every unique name drawn once into a
  4096×2048 canvas atlas (24 px rows, sRGB, aniso 8) and all labels merged into
  ONE indexed quad mesh lying flat on the roads — quad frame dir=(cos b, sin b),
  glyph-up=(dz, −dx); y = siteY(road) + [0.66, 0.5, 0.38] by cls (clears the
  class-separated ribbon lifts). MeshBasicMaterial transparent depthWrite:false
  renderOrder 5; applyLighting lerps text color 0x413d34 (day, dark on light
  asphalt) → 0x99938a (night). Toggle: St bar button / N key (default ON).
  Rerun the bake whenever a scene json is refetched.
- **Search fenced to Philadelphia proper**: the Nominatim viewbox spans the
  rivers, so Camden/Gloucester results leaked in — rows are now filtered to
  display_name containing "Philadelphia" ("Broadway" → no match; Pat's still
  found). Page 16.03 MB (artifact cap irrelevant — Pages-only delivery).

### Round 20 (Aug 25)

Round 20 (Aug 25 — night buses, rail removed, route search):
- **Night buses fixed** (Mike's screenshot: solid glowing white bricks): the
  material-wide emissive washed everything. Now the vehicle geometry carries an
  `aGlow` vertex attribute (1 on the glass band + windshield, 0 elsewhere;
  septaColored/septaMerge carry it) and bodyMat (Lambert, onBeforeCompile,
  uniforms.uNight = nightUniform) adds emissive ONLY there (warm ×0.8) plus a
  faint ×0.10 body presence. Verified at 11 PM: dark body, lit windows.
- **Rail layer REMOVED at Mike's request** ("mostly underground and not easy
  to track"): TrainView no longer polled, Regional Rail consists + NHSL gone,
  the ghost/x-ray mesh deleted (septaGhost, septaPickG, ghostMat all removed);
  T-trolleys inside the subway–surface tunnel simply aren't drawn (`v.ug` →
  skip). STREET TROLLEYS KEPT deliberately — they're surface, well-tracked,
  bus-like; drop them too if Mike asks for literal buses-only. septaKindOf
  now nulls L1/B1–B3/M1. About panel rewritten to match.
- **Route search** (Mike's request): a query that matches a live route
  ("33", "G1", "route 47", case-insensitive; routeLabel or raw id) short-
  circuits Nominatim and lists that route's live vehicles nearest-first
  (up to 8 rows: dest + next stop); clicking a row — or submitting — flies
  the orbit camera to the bus (goalR 220) and opens its card
  (searchGoToBus). Non-route queries geocode as before. ~605 street
  vehicles tracked at verify time (565 badges + 38 trolley pins).
- **Typography** (Mike: "looks very AI… less distinguishable aesthetic"): the
  Futura/Helvetica system stacks are replaced by EMBEDDED faces (base64 woff2
  in style.css, ~115 KB, OFL): `--display` = Libre Caslon Text (Caslon — the
  letter of colonial Philadelphia printing; veil title, bar buttons, kickers,
  About prose at 400) and `--body` = Alegreya Sans (400/500/700; UI, cards,
  street-label atlas at 500 — the 'Lettering the streets' step is now async
  and awaits document.fonts.load before drawing the canvas atlas). Mono stays
  system. The GLORY / Rotten Ralph's canvas SIGNS keep their Futura stacks on
  purpose (real-world signage, not UI). Page 16.14 MB.

### Round 21 (Aug 25)

Round 21 (Aug 25 — de-AI pass 2 + sun + bus alignment + layers panel):
- **Mono replaced** (Mike: "the biggest indicator of AI"): --mono is now embedded
  Courier Prime 400/700 (typewriter, archival) with Courier fallbacks. Kickers,
  hints, key chips, coordinates all read typewritten now.
- **No em dashes or middot separators in any user-facing text** (Mike's rule —
  KEEP IT THAT WAY in future UI strings): veil, About, fly tips, hints, cards,
  search rows, loading messages, timeSun readout all rewritten with commas,
  colons, and sentences. Hints are now capitalized sentences ("Drag to orbit.
  Scroll to zoom."). fmtTime's null placeholder is '' (was an em dash). Code
  comments and handoff/memory are exempt (not user-facing).
- **Street names**: now Libre Caslon Text ITALIC 400 (embedded; the classic
  engraved-map street hand), atlas 27 px in 34 px rows, text height per class
  [7.0, 5.6, 4.4] m, day color darkened to 0x2c2822 and night pale 0xa8a296 —
  bigger, darker, unmistakably cartographic. 'Lettering the streets' awaits
  document.fonts.load('italic 27px ...') before drawing.
- **Buses align to their street** (Mike's screenshot: diagonal bus): septa-
  SnapRoad now also returns the matched segment's unit axis; when snapped, the
  yaw target becomes that axis SIGNED to within 90° of the API/displacement
  heading (v.sdx/v.sdz), so GPS heading noise can't park a bus diagonally.
  Unsnapped vehicles keep the raw heading; the 2.6 rad/s cap animates corners.
- **Layers panel** (Mike: "filters all live in 1 button"): Aa/St/SEPTA bar
  buttons are gone; one Layers button (stacked-squares SVG, key F) opens
  #layerspanel with three .lrow toggle buttons that keep the OLD IDS
  (btnTransit with the SEPTA logo + a live count span #transitCount, btnStreets,
  btnLabels) so all existing wiring held; sync fns now toggle .on (bronze
  square .lmark). V/N/L shortcuts unchanged.
- **Street labels drape the road profile** (Mike's screenshot: label ends
  swallowed by sloping streets near the trench): each label is no longer one
  flat quad at the center height — it tessellates into columns every ~7 m of
  text length, each column at siteY(road)+LIFT, so the text follows Front St
  grades and the Delaware Expressway label now visibly rides down INTO the
  trench. ~6 extra siteY samples per label at build, negligible.
- **Round 22 additions (same day):** ALL type is now Montserrat (embedded
  0,400/0,500/0,600/0,700/1,600 — Caslon/Alegreya/Courier embeds REMOVED;
  hierarchy by weight: kickers 600, hints 500, street labels italic-600 27 px;
  readouts tabular-nums, time-panel readout wraps as clean rows, clock says
  "(live)" not "· live"). The About panel is HIDDEN for now (btnAbout
  display:none, the i key unbound — code intact) with a tiny fixed #osmcredit
  bottom-right keeping ODbL attribution. The towers' address labels are gone.
  The intro camera now settles on CITY HALL (orbit target −1603, 78, −802,
  goalR 700; default aimSun moved to −1450, −700). The Ryland (and every core
  glass landmark sharing rylandGlassMat) gets photo-matched night glass:
  onBeforeCompile per-panel warm lit windows (world-space 2.9×3.13 m cells,
  ~34% lit, ryh hash) + fully glowing lowest ~10 m above each part's aBase
  (lobby/amenity), driven by uNight — the old flat emissiveIntensity wash is
  gone. MOBILE FLICKER: logarithmicDepthBuffer is ON for every browser again —
  the Safari standard-depth fallback (obsoleted when round 4 proved the hollow
  buildings were a winding bug) was quantizing the few-cm flat gaps into heavy
  shimmer on phones; ?logdepth=0 stays as the escape hatch. sht-32's
  #btnLayers svg sizing line is preserved. If Mike still sees phone flicker
  after this, get an exact-view repro before touching depth again.
- **Round 23: street lettering is a baked SDF** (Mike: still pixelated after
  the fwidth sharpening — a raster atlas can't survive 5-9x magnification).
  `bake_street_sdf.py` (Pillow + numpy; vectorized chamfer EDT, no scipy;
  MontserratItalic.ttf variable font committed, wght 600) renders every unique
  name at 3x, signs the distance, downsamples to the SAME 27 px-row layout, and
  packs a 4096x2244 grayscale PNG into street_sdf.json (embedded as ST_SDF).
  'Lettering the streets' prefers it: PNG → canvas → R channel →
  DataTexture(RedFormat) — NOT LuminanceFormat, which WebGL2 texStorage
  rejects (GL_INVALID_ENUM 0x1909, no mipmaps → invisible labels) — and the
  material is alphaMap-based with the alphamap chunk REPLACED by an SDF
  threshold on .r (0.5 level-set, fwidth AA). Geometry/UV/drape unchanged; the
  old canvas path remains as fallback when ST_SDF is null. Rerun order:
  bake_street_labels.py → bake_street_sdf.py → build. Landed together with
  sht-32's always-visible markers (Mike's rule: neighborhood names + SEPTA/
  Indego markers + the search pin NEVER hide behind buildings — depthTest
  false + renderOrder 11/12 on nbMat, pinMat, badgeMat, Indego badgeMat, the
  bronze search pin). Page 18.94 MB.
- **Round 24 (sht-32's session, logged here on its behalf):** e80bd98 — the
  Ryland's night panels now light in FACADE space (the world-axis cell lattice
  cut half-lit fragments on the ~10°-rotated bars). Implementation note: it
  derives the facade axis from per-fragment derivatives rather than an OBB-axis
  uniform — a single shared axis would stripe the bars' END walls; the
  aBase-relative floor rows and the amenity band from round 22 are unchanged.
  Same commit: tree species read at a glance (chroma-separated palette,
  vase/pyramid/column silhouettes) on the PPR inventory. Two shader lessons to
  keep: (1) sin-dot lattice hashes streak into "worms" on integer cell ids —
  use a fract-cascade hash for cell lotteries; (2) make species/albedo
  variation live in HUE + SATURATION, not lightness — the daylight pipeline
  (legacy lift + ACES) flattens lightness differences.
- **Round 25: Mike REVERSED the x-ray call for vehicle markers** — buildings
  now occlude the SEPTA pins/badges and the Indego badges again (depthTest
  back to default on pinMat, the SEPTA badgeMat, and the Indego badgeMat;
  renderOrder kept for transparent sorting). Neighborhood names and the bronze
  search pin KEEP depthTest:false (he named only the SEPTA and Indego
  markers). Decision history: always-visible was his explicit ask earlier the
  same evening, reversed hours later — if it comes up again, ask which of the
  four marker families he means before flipping anything.
- **The sun is round now** (Mike's screenshot: vertical streak): the sky dome
  is coarse (32×18) and the fragment shader used INTERPOLATED vDir unnormalized,
  so pow(dot, 420) followed the mesh's vertex meridians. The shader now
  normalizes per fragment and draws a true angular disc
  (smoothstep on acos, ~0.6° radius) + gaussian halo + wide pow glow. NEVER
  compute tight specular-style highlights on unnormalized interpolated
  directions over a coarse dome. Page 16.20 MB.

### Round 25 (Aug 25)

Round 25 (Aug 25 — overpasses, the Vine Street cut, and living water; Mike's ask):
- **Elevated roads are REAL now.** `bake_overpasses.py` reads the raw dumps
  (osm_wide_raw + osm_south_raw + city_tiles/*, dedup by way id — the packed road
  formats carry no bridge/tunnel/layer tags) and bakes `overpasses.json` (~77 KB,
  embedded as OVERPASSES): 446 elevated chains / 118 km (I-95 viaduct incl. Front
  & Reed, I-676 ramps, Schuylkill bridges, Betsy Ross/Platt approaches, Roosevelt,
  pedestrian bridges), 11 sunken runs, 1 open-cut corridor. Pipeline: classify
  (bridge|layer>0 elev; tunnel|layer<0 sunk), chain through junctions (same
  highway TYPE first, then straightest-turn > cos 50°; motorway/motorway_link
  share a class code so class alone fragments at every gore — the hw string
  matters), absorb plain gaps ≤ ~350 m for motorway-family (embankments between
  viaduct sections; I-95 South Philly is 83% bridge-tagged with 30-290 m plain
  gaps), slope-limited profiles (4.2%/5.5%/9%) against the app-replicated DEM
  clamps, junction pinning via node_y (sunk chains solve first, ramps pin to
  solved mainlines), ends ramp to grade at plain roads but HOLD at custom-bridge
  names (Ben Franklin/Walt Whitman skipped entirely). Streets whose every
  under-crossing is sunken (or in the core I-95 trench corridor) get lift 0.45
  (bridges over cuts stay at street grade — naive layer lifts would hump Market
  St over the trench). SUNKEN GRADE GOTCHA: NED dips into the expressway cuts
  themselves, so sunken targets sample the RIM (max of ±30/±44 m lateral) or the
  Vine floor undulated 5 m.
- **App side** (module block after wwbNear): ovpGrid/ovpSegs hash; `ovpOwned`
  (both ends + mid aligned in a chain footprint) suppresses the packed flat
  ribbons in BOTH the wide and far road loops (septaRoadAdd still runs pre-drop,
  so bus snapping keeps those centerlines); `ovpDeckY(x,z,ux,uz)` lifts buses
  (updateTransit, aligned to v.sdx/sdz so passing UNDER a viaduct never lifts)
  and street-label columns; `vineCut(x,z,pad)` = corridor test + floor.
  Step 'Raising the overpasses' (after the far ring, so septaRoadGrid is full):
  deck box ribbons (mitered, DoubleSide; embankment skirts to ground where
  clearance < 2.2), edge parapets, piers every 21-26 m (hammerhead + twin
  columns for motorway; skipped where `crossingRoadNear` finds a non-parallel
  street below — septaSnapRoad alone returns only the NEAREST segment, which is
  the deck's own centerline, so it can NOT be used for this), pier bases to the
  riverbed when over water. The Vine cut: wide heightfield cells touching the
  corridor are INDEX-skipped (pos/col stay parallel — the Fairmount tint), walls
  floor portals from the corridor runs, 34 m grade collar aprons hide the ragged
  hole rim, median barrier where halfW < 19, sunken carriageway ribbons down at
  floor level. keepTree skips the corridor. Colors stored DARK (walls 0x5a5751,
  floor 0x2f2d29) per the render-lift lesson. Walk mode still walks the grade
  over the cut (visual hole only — siteY untouched).
- **The water breathes** (`liquify(mat, scale, amp, speed)` injection shared by
  waterMat, riverMat = wide+far water polys split out of areaParts, the basin
  mat, and pool water split from its decks): four directional gradient waves
  (46/21/9.5/4.1 m at river scale) tilt the shading normal (0.92 mix), a ±7.5%
  three-wave albedo shimmer keeps matte altitude views alive, and an explicit
  sun-glitter term (pow 140 on the perturbed normal, world-space cameraPosition)
  rides totalEmissiveRadiance — the material stays deliberately rough (0.42) so
  the river never mirrors, hence glitter must be explicit. uWAmp follows the
  live wind (0.5 calm → 1.8 at ~9 m/s), uWDir the wind direction, uSun copies
  sunDir every frame (at night that's the MOON: glitter × (1 − uNite·0.85) or it
  reads as sequins), distance fade flattens beyond ~2.6 km against aliasing.
  uTime advances by dt in frame() (frozen under prefers-reduced-motion; NOTE
  dt-based, so headless frameOnce pairs barely advance it — verify by jumping
  waterU.uTime, exposed in __dbg).
- Verified in-browser at noon and night: viaduct + underpasses at Front & Reed,
  Vine cut walls/floor/decks (vehicle crossing ON the Broad St deck), Schuylkill
  piers in the water, BFB/WWB/core untouched, zero console errors. Page 19.05 MB
  (Pages-only delivery). Rerun order: bake_overpasses.py (plain py3, ~1 min) →
  build; re-bake whenever the raw dumps are refetched.

### Round 26 (Aug 25/26)

Round 26 (Aug 25/26 — label audit, junction smoothing, the Vine cut reworked, portals
under the caps, and the real Moon; all from Mike's three follow-ups):
- **Street label placement audit**: OSM names motorway_link ramps by DESTINATION
  (five links down the I-95 trench are literally named Market Street), and the
  core bake lettered links — link classes now skipped. 824 Camden/NJ labels also
  read as misplaced Philly streets from across the river: the bake now drops
  east-of-Delaware placements (its own DEL_BANK copy is TIGHTER than the app's
  terrain polyline south of the stadiums, or Gloucester City NJ leaks through).
  3,784 labels / 648 names survive. street_sdf.json re-baked (rects align by
  index with the names list — ALWAYS re-bake both together). Runtime: labels on
  roads running > 2.5 m under the ground skip (the half-swallowed name at the
  caps), and per-column rise is clamped to 1 m per 7 m so ends stop climbing
  trench walls (steep streets at 14% still read). Analytic audit result: zero
  non-expressway labels inside cuts, 13 benign under-deck footprint overlaps.
- **Junction smoothing** (Mike's gore screenshot): the bake emits end kinds per
  run (0 = ramps to grade, 1 = pinned junction / held), profiles get 3-tap
  smoothing x2 AFTER the slope-limit and BEFORE node_y registration (ramps pin
  to the smoothed mainline). Runtime: junction ends nose 6 m INTO the joining
  deck (interpenetrate, never butt), grade ends keep parapet-free 14 m leads,
  and parapets/median barriers BREAK at every ramp mouth on the correct side
  (juncGrid of flagged chain ends carrying the ramp's approach direction; a
  radial-only test would gap both parapets). No barrier crosses a ramp exit.
- **Vine cut reworked**: the corridor bakes from the TWO longest carriageway
  chains only (a ramp had been pairing in, spiking halfW to 34), 12 m stations,
  width clamped 14-24 and smoothed, floor rim-sampled (NED dips into the cut
  itself — sunken grades sample max of +-30/44 m lateral) and clamped above
  WATER+1.4 (the river-clamped covered west end had dragged the open cut to
  -13). Walls wear proud coping caps, floor 0x262421 with pale gutter strips,
  carriageways 0x33312d with near-white edge lines, portal header beams at the
  covered ends, median barrier where halfW < 20 with mouth gaps. Sunken RAMPS
  outside the corridor get their own narrow walled cuts + ground holes + collar
  aprons; COVERED runs (cov flag, split in the bake) suppress the packed road
  but leave the ground alone — without the flag the I-76 tunnel under 30th St
  Station dug a 600 m ground hole (caught by the audit).
- **I-95 under Foglietta**: the caps existed but were paper-thin one-sided
  flats. The waterfront mesh is DoubleSide now; each deck cap gets portal faces
  (trenchFloor up to the deck edge) + header beams at both z faces, and the
  park cap gets portal faces at Chestnut and Walnut ends — raycast-verified:
  horizontal rays in the trench hit portal walls exactly at cap boundaries,
  I-95 runs beneath at -6.
- **The Moon is real**: lunar() (Schlyter's theory + topocentric parallax; the
  epoch is 2000 Jan 0.0 = Dec 31 1999, NOT J2000.0 — being 1.5 days off shifts
  the moon 20 degrees, found when the 2026-08-12 eclipse anchor failed).
  Validated: eclipse instant sun-moon separation 0.47 deg k=0.0%, full moon
  2026-08-28 k=100.0%, tonight waxing gibbous 95%. Sky shader draws a phased
  disc on the per-fragment normalized dome dir (nd, the sun-streak lesson):
  terminator ellipse from k, bright-limb tangent computed in WORLD SPACE as the
  sun dir minus its moon-dir component (no spherical trig, tilt automatically
  right), 11% earthshine, halo by phase, hidden by day/clouds (uMoonI).
  applyLighting: night light follows the real moon (intensity 0.05+0.13k when
  up, dim high fill when down), water glitter aims at glintDir (sun by day,
  moon when up, straight down = off on moonless nights). T panel readout gained
  a moon segment ("Waxing Gibbous 95%, Up SE"). Verified live at 9:16 PM: disc
  SE over Camden with the moonglade on the Delaware beneath it.
- Page 18.43 MB (smaller: 830 fewer labels + tighter SDF atlas). Zero console
  errors. Rerun order unchanged: bake_overpasses -> bake_street_labels ->
  bake_street_sdf -> build.

### Round 27 (Aug 26)

Round 27 (Aug 26 — the cleanup sweep; Mike: sloppy ramp barriers, cut-off names,
disconnected streets, a building through I-95; verified by a 10-agent audit
workflow (5 audits + 5 adversarial verifiers, all confirmed) over the packed data):
- **Disconnected streets ROOT CAUSE**: ovpOwned suppressed packed segments within
  chainWidth/2 + 3 m (11 m on motorways) — it ate the surface streets running
  beside embankments. Now a FIXED 2.6 m aligned test on the two ENDPOINTS only
  (the audit proved the distance distribution is bimodal: 1,879 true duplicates
  under 2 m, neighbors beyond 5 m; requiring the midpoint too let curved
  duplicates escape where the simplified chain corner-cuts the arc). Known
  limit: ~2 orphan fragments citywide whose START bulges > 2.6 m still escape,
  hidden under decks.
- **Building through the viaduct**: 7 wide-set OSM footprints (h 11-13 m)
  straddle I-95/I-676 decks (Mike's is at (-50.9, 1364.5) by South Front).
  CRITICAL: centroid tests catch only 2 of 7 — they straddle EDGE-ON, so
  ovpStraddle walks every footprint EDGE (3 m steps) against the c<=1 swaths at
  halfW - 1, plus open cuts and the corridor. Far ring audited CLEAN (145k
  buildings, nearest miss 3.1 m outside the band).
- **Sliced labels**: bake_street_labels now keeps every station's text span
  clear of crossing decks and the cut's coping walls (|cos| < 0.72 crossings
  within w/2 + 1.2): shift along bearing +-22/42/62 m (must stay on the street
  via near_way), else drop. 35 of 36 sliced labels shifted, 1 dropped (Spring
  Garden inside the I-95 ramp fan). Audit re-run after: sliced = 0.
- **Parapet tangles**: 190 overlap regions citywide (47 junction mouths, 128
  braids, 15 twin runs). One rule clears them: a parapet segment lying INSIDE
  another chain's deck footprint (lateral < other hw - 0.4, |dy| < 2.5) is
  skipped — handles gores, braids, AND twin carriageways' facing rails without
  special cases (mouthAt keeps the side-aware ramp-exit gaps). Piers now skip
  where another deck passes between ground and soffit (92 stations, stacked
  interchanges). KNOWN LIMIT: the Penrose/PA-291 twin carriageways run ~3 m
  apart vertically for a few hundred meters (one carries a layer-2 way, its
  slope-limited profile stays high) — reads as independent grades from any
  ground view, left alone; a twin-leveling bake pass is the fix if it ever
  bothers anyone.
- Page 18.44 MB, zero console errors. Audit scripts live in .audit/ (untracked).
  The audits decode wide.b64/city.b64 independently — formats confirmed
  byte-exact against pack_wide.py (0.2 m units) and pack_city.py (0.7 m units).

### Round 28 (Aug 26)

Round 28 (Aug 26 — the mobile memory diet; Mike: "will not load on mobile"):
- Diagnosis: the live build loads fine on an iPhone 17 Pro Max SIMULATOR (WebKit,
  reaches Ready, enters, renders) and in Chromium mobile emulation with zero
  console errors — so no mobile code break; real devices are dying on PEAK
  MEMORY (the simulator borrows Mac RAM; real iOS kills a tab around ~1.4 GB).
- Fixes, measured 536 -> 431 MB JS heap (Chromium A/B, same machine):
  1. `freeOnUpload(g)`: every attribute + index of the wide/far building chunks
     and the wide/far road meshes nulls its CPU array after GPU upload (the
     onUpload callback). 83 megageometry meshes freed; they are never raycast
     (rayTargets holds only core meshes, ground, and the overpass mesh).
  2. A `renderer.render(scene, camera)` fires INSIDE each decode step right
     after the chunk loop, behind the veil, so the upload+free happens during
     build instead of retaining everything until the first visible frame; the
     per-chunk source arrays (plain JS number arrays, the real peak) are nulled
     as each geometry is built.
  3. The four big base64 blobs (WIDE_B64, CITY_B64, TREES_B64, ST_SDF) are
     emitted as `let` by build.py and nulled by the app right after decoding.
  4. The overpass mesh stops casting shadows on touch devices.
  5. window 'error' handler writes 'Error: ...' into #loadmsg — a phone that
     fails to load now SAYS why instead of sitting on a silent veil. If Mike
     reports a failure again, ask what the veil text says (an error message, a
     stuck step name, or Safari's repeated-reload page = still memory).
- KNOWN LIMIT: this cannot be confirmed on Mike's physical phone from here. If
  it still dies, the next lever is a touch LOD for the far ring (conflicts with
  his round-7 "full map on mobile" ask, so it needs his sign-off). Page 18.44 MB.

### Round 29 (Aug 26)

Round 29 (Aug 26 — night lights de-blobbed + live flights; Mike's asks):
- **The big square night lights are GONE**: the round-6 cluster LOD (3x2-window
  superblocks past the per-window fade) in BOTH cityMat and outerGlassMat read as
  yellow slabs that popped away on approach. Removed; windows fade straight into
  the aggregate glow, which also dimmed (cityMat 0.115 -> 0.05, curtain 0.22 ->
  0.10). Distant facades now read dark with soft presence; the remaining pale
  far-city look under a bright moon is MOONLIGHT on tan roofs (physically fair,
  scales with phase). shtLit is wall-gated — roofs never emit.
- **Live flights layer** ('X' key / Layers row): adsb.fi community ADS-B around
  PHL (30 nm), procedural ~120-tri airliners on bodyMat (cabin glow band at
  night via aGlow), true track/pitch, white double-blink strobes phase-hashed
  per airframe, dead reckoning between fixes (glide capped 50 s), tap-for-card
  (callsign, type, operator, altitude, speed) via the shared picker (ALL
  pick branches now clear pickedPlane and vice versa), #vehinfo follow.
  THE CORS WALL (measured, do not relearn): NO flight API speaks CORS to
  browsers — adsb.fi/adsb.lol send no ACAO, adsb.one 403s, airplanes.live wants
  email approval, OpenSky reflects an allowlist. The fetch rides rotating
  public passthroughs [allorigins.win, corsproxy.io] at a 90 s cadence with
  dead reckoning bridging the gaps; each failure rotates hosts and retries.
  allorigins throttles per client IP (this machine burned its budget testing —
  fresh viewers get their own), corsproxy 403'd this automated browser but is
  built for real https origins. FLIGHT_PROXY at the top of the flight section
  accepts a personal Cloudflare Worker URL and unlocks a 10 s cadence — the
  real fix, needs Mike's CF account (worker recipe in the session log).
  Dev: `__dbg.flightTest()` seeds 3 synthetic aircraft (approach, climbout,
  taxiing at PHL) to verify the render path without the feed — this caught a
  real bug (bodyMat is septaInit-local; module access is septaMats.body).
  `__dbg.flights()` reports tracked/ok/fails/host. Layer hidden under the
  artifact CSP like all live layers. adsb.fi credit in the About body.

### Round 29b (Aug 26)

Round 29b (Aug 26 — Mike: planes frozen): dead reckoning had a 50 s glide cap
and stale planes were only pruned by a SUCCESSFUL poll, so when the public
passthroughs went quiet everything froze mid-air. Now planes fly their last
track indefinitely: descending arrivals settle onto the field (y floors at
ground + 5, 'landed'), anything leaving the model bounds or stale > 300 s
(landed > 90 s) despawns, a fresh fix > 3.2 km away snaps instead of swooping,
the card notes 'Estimated Track, Awaiting Signal' past 25 s, and failed polls
retry the next host after 8 s (3 min lockout only after 3 full cycles).
NOTE for headless testing: the Browser pane runs NO rAF even when fronted —
animation must be verified with frameOnce bursts (400 calls closed 775 m of
easing gap and 37 m of descent), never by wall-clock waits.

### Round 29c (Aug 26)

Round 29c (Aug 26 — Mike: neighborhood names invisible by day): the nb labels
were white atlas glyphs TINTED dark then ACES-lifted to ghost gray over the
pale noon city. Now the atlas bakes a cartographic halo for neighborhood names
(pale 7 px casing rgba(248,244,233,.95) + dark core #2e2a22, final colors),
nbMat is untinted white with toneMapped false, and the day/night color lerp is
gone (the two-tone glyph reads on pale noon ground AND dark night ground by
construction). District labels in the same atlas stay single-tone white so
their bronze tint keeps working. Verified at noon and night over South Philly.

### Round 30 (Aug 26)

Round 30 (Aug 26 — live ships; Mike: boat traffic on the rivers): AIS layer via
the aisstream.io WebSocket (wss://stream.aisstream.io/v0/stream) — WebSockets
have NO CORS wall, so unlike the flight feed the page connects DIRECTLY; the
only requirement is a free aisstream.io API key pasted into AIS_KEY (top of the
ships section). Until the key exists the Layers row hides but __dbg.shipTest()
still injects three synthetic vessels (container ship, tug, moored tanker) so
the pipeline stays provable. Subscription bbox [[39.80,-75.45],[40.08,-74.82]],
PositionReport + ShipStaticData; vessels keyed by MMSI carry real AIS
dimensions (A+B length, C+D beam), type names, destination; moored/anchored
(nav status 1/5 or SOG < 0.25) hold station, movers dead-reckon along COG
(extrapolation capped 10 min, despawn 30 min stale). Unit hull scaled
(len, clamp(len*0.09), beam) per instance; card: type chip, name, speed or
Moored, length, Bound For. Key 'H', row hidden without a key.
TWO INSTANCING GOTCHAS (cost a build each): (1) never bake a rotation into a
part that gets NON-UNIFORM instance scale — the 45-degree bow prow sheared
into a detached blade; taper with axis-aligned steps instead. (2) a mesh
sharing septaMats.body MUST setColorAt (white if no tint wanted): the shared
program expects instance colors and an uninitialized attribute reads zeros —
the whole ship rendered ink black.

### Round 30b (Aug 26)

Round 30b (Aug 26 — ships LIVE): Mike's aisstream.io key is installed in
AIS_KEY (visible in the public page by his informed choice; rotate at
aisstream.io if ever abused). CRITICAL DECODE GOTCHA: aisstream sends BINARY
frames — set ws.binaryType = 'arraybuffer' and TextDecoder-decode before
JSON.parse, or every message fails silently (the socket looks healthy, zero
vessels arrive). shipStatus() now fires on first sight of each MMSI so the
Layers count is live. Verified with real traffic: SPIRIT OF PHILADELPHIA
moored at Penn's Landing, tug EMERALD COAST, cargo ship TISCAPA — vessels
whose ShipStaticData arrives before any PositionReport hold off rendering
until their first fix (dx undefined guard). __dbg.ships().list dumps the
live fleet with positions.

### Round 30c (Aug 26)

Round 30c (Aug 26 — Mike: no boats visible + "janky gold lines"): (1) The
aisstream free key streams to ONE client at a time — the dev preview tab had
been holding the connection, so Mike's page got refused (close 1006 before
open) and showed an empty river while 36 real vessels were tracked. The page
now RELEASES the socket whenever its tab is hidden or the layer is toggled
off (visibilitychange + shipRelease), reconnects ~1.2 s after becoming
visible, and backs off exponentially with jitter (15 s -> 4 min) when
refused, so the visible tab usually wins the key. DEV RULE: close preview
tabs when done or they starve Mike's session; the multi-viewer fix is a
Cloudflare Durable Object fanning one upstream stream out to N viewers.
(2) The historic-district bronze street inlays AND their bronze labels are
REMOVED at Mike's request (round 17 built them; he called them janky gold
lines). District data stays in places.json. The P row is now 'Neighborhood
Names' and governs only those; btnPlaces hides when PLACES.nb is absent.

### Round 30d (Aug 26)

Round 30d (Aug 26 — Mike: watching real approach traffic from the condo, zero
planes in the app): the flight layer starved because the free public CORS
passthroughs died out from under Round 29 — measured from a real page origin
(GH Pages) this afternoon: allorigins.win 522 (origin dead, ~20 s hang — NOT
the per-IP throttle Round 29 assumed), corsproxy.io 403 "Server-side requests
are not allowed on your plan" (proxying is paywalled now, real https origins
included), codetabs.com 522, cors.lol / cors.eu.org / thingproxy / the CF demo
worker all dead, and OpenSky now reflects ONLY its own origin in ACAO (its
anonymous REST API still answers — 397 credits remained — but no browser can
read it cross-origin). adsb.fi/adsb.lol still ship no ACAO; hexdb.io DOES
serve ACAO * but is registry-only, no positions. The feed itself is healthy:
62 aircraft in the Philly box direct from adsb.fi at test time.
Fix shipped: (1) flight-proxy-worker.js — a ~30-line personal passthrough
(Cloudflare Workers or Deno Deploy free tier, recipe in the file) locked to
the fixed adsb.fi query, ACAO *, 8 s upstream cache, stale-beats-empty; Mike
deploys it and pastes the URL into FLIGHT_PROXY (takes precedence, 10 s
cadence, any number of viewers cost adsb.fi ≤ 1 req / 8 s). (2) Rotation is
now [FLIGHT_PROXY, allorigins, codetabs] — corsproxy dropped for good,
codetabs kept despite today's 522 because these things resurrect.
(3) flightPoll's fetch gets AbortSignal.timeout(15 s) — a hanging 522 proxy
used to stall the whole rotation for minutes. (4) Never-fed + out-of-hosts
now says so (Layers title 'Feed Unreachable — Set FLIGHT_PROXY In app.js' +
one console.warn) instead of a lying quiet zero.
Verified end to end against the LIVE feed through a local same-origin
stand-in with the worker's exact semantics: 10 real aircraft tracked
(ok:true, badge 10) — GA singles low over PNE, airliners descending the PHL
approach, one framed on camera SW of the site. The pipeline is fine; only
transport died. Until FLIGHT_PROXY is filled, the deployed page shows planes
only if a public passthrough resurrects.

### Round 30e (Aug 26)

Round 30e (Aug 26 — Mike: drop BANK OF UTAH TRUSTEE from the card, add a PHL
pin so planes read from distance): (1) ownOp is gone from the flight card —
adsb.fi's field names the registered owner, which for leased metal is a
trustee bank, not an airline; callsign + type carry the identity. (2) Every
aircraft now flies a billboarded PHL pin: the SEPTA bus-badge recipe (same
256x320 canvas frame + pointer tip, camera-quaternion billboard, distance
scale) but navy-bodied in a warm-white casing — the Round 29c two-tone trick,
because a white badge vanishes against pale sky. Wordmark is hand-set type
('phl', sky-blue sail clipped over the p), NOT the airport's trademark art.
Scale clamp(dist/135, 2.2, 190) holds ~34 px at any range; material is
fog: false + toneMapped: false or the 11 km haze eats it (measured: with fog
on, a pin over PHL from the towers was a ghost). Pins raycast-pick like the
plane body (flightPick maps both). Note per the passthrough die-off: Mike's
page had planes again this morning because allorigins RESURRECTED, exactly
as the rotation bet it would; FLIGHT_PROXY remains the reliable path.

### Round 31 (Aug 26)

Round 31 (Aug 26 — Mike: spin the project up on philly3d.com): the model now
lives on Mike's IONOS VPS (74.208.76.220, ssh Host lionspool-vps, root +
id_ed25519 — the box also serves harkpicks.com and thelionspool.com; don't
break them, nginx -t before every reload). Staged and verified same-day:
/var/www/philly3d (index.html + a -k9 gzip twin served via gzip_static,
18.4 -> 10.3 MB), vhost sites-enabled/philly3d (port 80 until certs), and —
the point of self-hosting — a same-origin /adsb nginx passthrough to the
fixed adsb.fi Philly query (8 s shared proxy_cache in conf.d/adsb_cache.conf,
stale-on-error, ACAO *): the VPS copy has FLIGHT_PROXY rewritten to '/adsb'
at deploy (10 s cadence, NO CORS wall, no public passthroughs, no worker).
Verified via --resolve before DNS: / 200, /adsb 200 with 60 live aircraft.
deploy_philly3d.sh is the one-command redeploy (build -> sed -> gzip ->
rsync); the repo source keeps FLIGHT_PROXY='' for the GH Pages copy.
COMPLETED same day once Mike flipped DNS (@ A + www CNAME at IONOS):
certbot certonly --webroot issued philly3d.com + www (auto-renew scheduled),
the vhost now redirects 80 -> 443 (ACME path stays open on 80 for renewals),
and https://philly3d.com/ verified: TLS clean, gzip 10.3 MB, /adsb 200 with
57 live aircraft and ACAO *. FLIGHT_PROXY in app.js is now
'https://philly3d.com/adsb' for BOTH homes — same-origin on the VPS,
CORS-ridden on GH Pages — 10 s cadence everywhere, and deploy_philly3d.sh
no longer rewrites anything (identical build ships to both; its grep guard
refuses a proxyless build). flight-proxy-worker.js stays as the fallback
recipe if the VPS ever goes away.

### Round 32 (Aug 26)

Round 32 (Aug 26 — Mike: show traffic from the OpenDataPhilly catalog; helicopters
shouldn't wear the phl pin): the Typical Traffic layer (R, default on, Layers row
between Ships and Street Names). No public feed of live car positions exists, so
this is the honest inversion: PennDOT RMSTRAFFIC AADT (fetch_traffic.py, 593
segments cached in lidar_cache/traffic_raw/) conflated onto the raw OSM drivable
ways (bake_traffic.py — way-ID dedup across wide+south dumps, oneway/tunnel tags
kept, per-class match distance 25→10 m with parallelism ≥0.87 and plausibility
caps so Water St never inherits I-95's count; 5,605 ways, 2,250 matched, 1,706
oneways halved where PennDOT counts both carriageways together) into traffic.b64
(123 KB, magic 0x53485454). The app section (// ------- traffic, before the solar
clock) precomputes per-vertex y through the whole terrain story — motY trench
blend for core cls-0, river decks +20/13 for cls≤1, dead-split over water for
minor classes, wwbNear culled, ovpDeckY riding viaducts, sunkCutNear for cls≤1
only (crossing streets must NOT dive into the Vine cut) — then simulates cars
per run at AADT · hourlyFrac(clock) / speed(class) · km, weekday/weekend curves,
reconciled every 600 ms and instantly on slider jumps. Cap 900 desktop / 300
touch with a global scale: rush hour shows a stated "1:9 Sample" in the tooltip,
3 AM runs at a true 1:1 (382 cars). Bodies are one InstancedMesh on
septaMats.body (setColorAt every frame — slots shift as cars retire; palette
stored dark); lights are a second MeshBasic InstancedMesh (fixed warm-white
emissive can't do red taillights), opacity ramped off nightUniform — white
pairs forward, red aft, free by day. Verified in-browser: cars down IN the
I-95 trench (y≈-5), taillights at night, counts 893/5 PM vs 382/3 AM, mobile
cap honored. Also: rotorcraft pins. flightPinTexture(kind) now draws a chunky
side-view helicopter (rotor/cabin/boom/skids, sky-blue canopy) in the same
badge casing; a second flightPinH InstancedMesh takes p.heli traffic (ADS-B
category A7 or a ~55-code type set, sticky across polls, len forced to A7's
12 m) while fixed wing keeps the phl wordmark. flightTest() gained a test
EC135. PennDOT credit added to template credits + about_body; R in the About
key table.

### Round 33 (Aug 26)

Round 33 (Aug 26 — Mike: helis should BE helis and be clickable, traffic only
shows in a few spots, and drop the phl mark for a generic plane): three fixes.
(1) Rotorcraft now fly a real model: heliGeom (cabin pod, canopy, cowl, boom,
red fin, tail rotor, skids — 13 boxes) plus a separate heliRotor InstancedMesh
(two crossed blades) spun about local Y per frame (16.5 rad/s, per-airframe
phase from the hex), both on septaMats.body next to flightMesh. The aircraft
loop now routes bodies by p.heli with split counters (iF fixed wing / iH heli)
and split pick arrays — the old shared flightPick[i] silently misindexed pins
once the counters diverged. (2) Picking: heliMesh and flightPinH joined the
raycast targets (the heli pin was never clickable — that was the whole bug),
fAct counts either mesh, and the resolver maps heli hits through heliPick.
Verified by dispatched pointer events: heli card (PD1 · Eurocopter EC135) and
plane card both open. (3) The phl wordmark pin is retired: fixed wing now
wears the material-icons flight glyph (the layers panel's own path, Path2D at
6.6x) in the same navy badge, sky-blue nose accent — no lettering. (4) Traffic
rework: the car budget now follows the camera (full weight ≤1.5 km of the eye,
gone past 4 km, 3D distance) instead of spreading over all 1,080 km — runs are
chunked to ~400 m at decode (6,052 runs) so long ways resolve finely, cap
raised 900→2,200 desktop / 300→550 touch, and the tooltip says "1:N Sample
Nearby" (suffix only below scale 0.85 — it used to claim 1:2 at 0.98). Around
the default orbit that lands near TRUE density: 2,148 cars at Wed 5 PM at
1:1.4, the Vine Expressway visibly flowing; the whole-extent implied is still
~8k so distant wards go quiet until you fly there. Same-frame gotcha learned:
pane screenshots lag one PRESENTED frame behind frameOnce — render twice
before capturing.

### Round 34 (Aug 26)

Round 34 (Aug 26 — Mike: cars popping in/out is jarring, and no headlights at
night): the traffic sim grew a road graph and real optics. (1) Runs sharing an
endpoint (same OSM node — chunked pieces of one way included, their endpoints
are bit-identical floats) now connect through a joint map built at decode;
carTransfer flows a car reaching its run end onto a connecting run (weighted
reservoir pick: next street's AADT × straightness, no entering a one-way at
its far end, dot < −0.55 U-turns refused, true dead ends ease out in place).
Cars are frame-stamped (car.fr) so a transferred car renders the same frame in
its new run and isn't double-advanced. This kills the biggest jar: 400 m chunk
ends used to hard-splice a car every ~50 s per car. (2) Churn hides: spawns
sample three spots and keep the farthest from the camera; reconcile retires
farthest-first; fades lengthened 700→900 ms. (3) The "no headlights" bug was
depth testing: the lamp boxes sat flush INSIDE the body box, so the body
occluded them from every angle but dead ahead. Lamps now sit proud of the nose
and tail (0.22 m at x ±2.32 on a ±2.2 body), the material went
AdditiveBlending, and per frame at night the lamp instance scales by
clamp(dist/150, 1, 5) so a light pair never drops below a couple of pixels —
headlights read from blocks away, sheet metal doesn't. Verified at the
Schuylkill Expressway at night: white pairs approaching, red pairs receding,
queues reading as strings of lights; 300-frame soak at 2,200 cars ≈ 0.8 ms/
frame, no errors, population stable.

### Round 35 (Aug 26)

Round 35 (Aug 26 — Mike: kill orbit and walk as modes; load orbiting City
Hall; first interaction flies; veil backs onto a wide Center City): the mode
bar is gone (the three seg buttons removed from template #bar; 1/2/3 key
dispatch removed; btnOrbit/btnWalk/btnFly consts and listeners deleted).
Orbit survives ONLY as the attract loop: introSpin now starts true, orbit
opens at r 3400 → goalR 2600 (the veil's zoomed-out Center City), Enter sets
goalR 700 for the cinematic glide down to the existing City Hall target, and
the circle keeps turning until the first real interaction. autoFly() — wired
into pointerdown, wheel, touchstart, and the movement keys (w a s d e q,
space, arrows) — hands control to fly mode from wherever the circle happens
to be; on touch it also raises the flyTips overlay once. setMode grew a
noLock arg: searchGoTo/searchGoToBus no longer setMode(ORBIT) (which would
have yanked users back into a dead mode) — searchFlyTo() parks the fly camera
at a vantage above the hit, cursor unlocked so the desktop result list stays
usable. Hints and the About key table rewrote to fly-only; the veil sub line
now says "Take the controls and fly it." Walk remains reachable only through
__dbg.goWalk (?dev). Verified: veil over the wide skyline, Enter glide,
synthetic pointerdown → fly with crosshair + "Click the scene" hint (pointer
lock correctly defers to a real gesture).

### Round 36 (Aug 26)

Round 36 (Aug 26 — Mike: a bare quarter of the city with buses floating on
roadless ground; and the load still opened on SHT before cutting to City
Hall): two root causes. (1) The city fetch had a literal hole: the four BOXES
in fetch_city.py stop at the wide box's east edge (-75.118) below 39.986 and
at -75.060 below 40.050 — Fishtown's east end, Port Richmond, Bridesburg,
Harrowgate, Juniata and west Frankford were never fetched. A fifth box
('river-wards', 39.915–40.050, -75.118..-74.990, 4×3 tiles) fills it: 813k
new elements, osm_city_raw 3.79M elements, city.b64 7.9 → 9.06 MB (165,350
buildings, 22,635 roads), page 18.62 → 19.74 MB. fetch_city.py also learned
to skip the DEM refetch when dem_city.json exists (checkpoint parity with the
tiles). The new wards ride tag/HDEF heights — lidar_city_heights.json predates
them, so a future lidar_join pass would true them up; ambient traffic still
ends at the wide box by design. (2) The SHT-then-cut on load: the camera's
first placement only happened in frame one of the rAF loop, so the two
mid-build veil renders ("upload now, behind the veil") drew from the camera's
DEFAULT pose at the origin — which is the towers' centroid. One line after
the orbit const — applyOrbit(0) — parks the camera on the wide Center City
shot before anything renders.

### Round 37 (Aug 26)

Round 37 (Aug 26 — Mike: no tooltips through buildings): the pick pipeline
gained an occlusion gate. pickOccluded(tx,ty,tz) casts from the eye toward the
candidate with raycaster.far = distance − 1.6 against rayTargets (ground,
core fabric, landmark walls, tower concrete, overpass decks — the old
double-click focus list) plus outerMeshes (wide + far-ring chunks; bounding
spheres prune, so the click-time cost matches what double-click focus always
paid). Three gates: the instanced hit (tested at hits[0].point — a pin
peeking over a roofline still picks, its vehicle hidden below doesn't), the
nearest-to-tap fallback winners (bus at gy+2.5, dock at y+2), and the tree
pick (canopy march + trunk fallback — the march itself happily crossed
walls). Verified with shipTest: MSC ALTAIR picks from altitude with a clear
line, refuses from street level behind a kilometre of Society Hill fabric.
Harness note: synthetic PointerEvents must dispatch BOTH down and up on the
canvas — window-dispatched ups never reach the canvas listener and the pick
silently no-ops (cost one confused test round).

### Round 38 (Aug 26)

Round 38 (Aug 26 — branding: Philly3D): the site has an identity now. New
`3d-model/brand/`: hand-drawn `mark.svg` (City Hall tower + Penn, bronze
silhouette, evenodd apertures) and `favicon.svg` (64-box, ink plate, paper
clock disc); `make_brand.py` renders dist/ — sips does SVG→PNG (sips-316
rasterizes SVG with alpha fine; qlmanage flattens alpha, unusable), PIL
assembles the 16/32/48 ico, flattens the 180 apple-touch on ink, sets the
PHILLY3D wordmark (Montserrat-SemiBold.ttf, per-char 0.22em tracking, 3D in
bronze) and composites the 1200x630 `og.png` share card from `og_raw.png`.
The card shot: `og_sink.py` (127.0.0.1:8123) + `?dev=1` — the attract
orbit's target IS City Hall (-1603, 78, -802), so setting orbit
theta/phi/r frames it exactly; layer fades run on WALL time, so a capture
one frame after a toggle still shows the old state (wait real seconds
between set and capture). template.html is now a real document (doctype,
html lang, head, body — page left quirks mode, compatMode CSS1Compat;
verified safe: app.js never touches document.body, all chrome is
position:fixed) with full meta: title "Philly3D: A Living Model of
Philadelphia", description, canonical https://philly3d.com/, theme-color
ink, OG/Twitter card pointing at https://philly3d.com/og.png, and three
new build.py placeholders inlining favicon svg/png32/apple-touch as data:
URIs (guard tuple extended; base64 can't contain '<'). The veil card
carries the mark (inline SVG above the kicker, `#veil .veilmark`, 60px
bronze). deploy_philly3d.sh now refuses builds without og:image and
rsyncs favicon.ico/favicon.svg/apple-touch-icon.png/og.png next to
index.html(.gz); the GH Pages shim and README wear the brand too. Do not
regenerate dist/ blindly: og_raw.png is a curated capture (dusk minute
1219, orbit theta 0.16 phi 1.30 r 900, labels off, traffic on).

### Round 39 (Aug 26)

Round 39 (Aug 26 — begun on the desk machine and cut off mid-round; Mike, from
the laptop: pick it back up and deploy): two features arrived nearly whole and
needed only their last wire. (1) Streetlights (G, Layers row between Traffic
and Street Names, default on): the Streets Department's Street_Poles inventory
(fetch_poles.py, 203,058 rows via the City ArcGIS) packs to poles.b64
(pack_poles.py — int16 x/z at 0.7 m units, far-ring clip, 1.2 m dedupe, magic
'SHTP', 200,805 kept, 1.6 MB; packed bits carry lamp kind, surveyed height in
feet with per-family defaults, and a two-luminaire flag). Every pole is one
additive glow point at night — PointsMaterial with an onBeforeCompile
perspective size clamped to a 2-px floor (the headlight trick), LED warm
white, HPS amber, unknowns dim and mixed, amplitude scaled by height and
luminaire count — opacity ramped off nightUniform so lamps lead the
headlights at civil dusk. Desktop adds 1,600 instanced pole meshes (tapered
shaft + arm + head at a 9 m reference, y-scaled to surveyed height) within
1 km, reconciled every 900 ms or 220 m of camera travel; touch skips the
meshes entirely. (2) The northwest finally has its hills: dem_nw.json
(fetch_dem_nw.py — 50 m NED over East Falls / Manayunk / Roxborough / the
Wissahickon / Chestnut Hill, checkpointed like the city DEM, border
pre-feathered toward dem_city over 250 m so no consumer needs seam logic)
samples ahead of dem_city in demAbs and in bake_overpasses (overpasses.json
rebaked). The far ground cuts the patch's footprint out of the north strip
along the strip's own 100 m grid lines (T-junction verts only) and lays a
50 m vertex-colored mesh in the hole: woodland tint from the City's own PPR
parkland boundaries (fetch_nw_parks.py, 32 polys — the central Wissahickon
has no park polygon in the OSM extract; fetch_city.py now also asks for
nature_reserve relations so the next full refetch carries it), park
membership blurred one cell so the green feathers instead of stair-stepping,
big OSM park drapes dropped inside the patch (the tinted ground IS the park),
and water rebuilt from full-fidelity rings (fetch_nw_water.py, 93 polys)
draped at 30 m on the terrain so the creek descends its real stepped profile
with the bed dug 3 m under it. Buildings straddling the sharpened slopes
settle to their LOWEST corner inside the patch — a centroid base left
downhill walls floating. Also from the desk session: lidar_join trued the
river wards' heights (lidar_city_heights/report), city.b64 repacked.
The interruption point was build.py: app.js and template were done (button,
key table, credits, G binding) but the four blobs were never inlined —
DEM_NW / NW_PARKS / NW_WATER / POLES_B64 (a `let`, the app frees it after
decode) now ride data_js like their siblings; page 19.74 → 21.69 MB.
Verified in-pane on the laptop: 201k badge, zero console errors across the
whole drive, the night carpet from altitude tracing every street, G on/off
both ways, gorge relief + woodland tint + descending creek, Manayunk blocks
grounded on the slope, the 50 m/100 m border seam invisible, pole meshes
standing by day, 1.41 ms/frame at night with all layers on. Residual: at
long grazing range the draped creek can dash where terrain rises between its
30 m samples — invisible near and from altitude; nudge the drape offset or
subdivision if it ever bothers. Laptop notes: the pane's dev-server python
cannot getcwd() inside CloudStorage (TCC), so the built page is served from
the session scratchpad (launch.json's scratch entry exists for exactly this;
the preview entries went machine-relative `-d 3d-model`). Deploy could NOT
run from the laptop: ~/.ssh has no lionspool key (phade.app is a different
box — 74.208.219.49, not the .76.220 VPS) and no GitHub credential (the
resident github key is the Phade deploy key, repo-scoped, push denied) — so
this round is committed but unshipped. From the desk machine: `git push`
publishes the GH Pages home, `./deploy_philly3d.sh` ships philly3d.com; the
commit itself rides Dropbox there. Or authorize the laptop once (VPS
authorized_keys + a GitHub credential) and it can ship both from here on.

### Round 39 coda (same evening)

Round 39 coda (same evening — Mike authorized the laptop): the repo now has a
write deploy key `philly3d-laptop` (GitHub repo settings; key file
~/.ssh/harkdigital_laptop, push via GIT_SSH_COMMAND with -F /dev/null so the
resident Phade deploy key is never offered first), and the same pubkey sits
in the VPS authorized_keys (planted by root password from the laptop;
`lionspool-vps` aliased in the laptop's ~/.ssh/config). Both homes then
shipped from the laptop — and the VPS deploy promptly served a site-wide
403: this checkout lives in CloudStorage where every file is mode 600, and
`rsync -az` faithfully delivered index.html and all four brand files
unreadable (uid 501, 0600) — nginx refused everything. chown root / chmod
644 on the box restored service inside ten minutes. Permanent fix in
deploy_philly3d.sh: ALL six shipped files now stage into $TMP and get
`chmod 644` there before rsync (macOS openrsync rejects --chmod, so the
modes are fixed at the staging copy, portable to both machines); re-deployed
end-to-end from the laptop to prove it. Verified live: philly3d.com 200 with
the new 11.97 MB gzip and btnLights in the served page, og/favicons 200, and
the GH Pages home serving the new 21.69 MB build byte-identical.

### Round 40 (Aug 26)

Round 40 (Aug 26 — Mike: East Mount Airy, West Oak Lane, and Cedarbrook all
look empty): the Round 36 lesson had a sibling. Above 40.050 the 'northeast'
box only starts at -75.130 and 'northwest' only reaches -75.190 — the wedge
between them (exactly those three neighborhoods, plus Chestnut Hill's east
flank along Stenton) was never fetched, and the new NW terrain made the bare
ground impossible to miss. A sixth box ('nw-gap', 40.050–40.100,
-75.190..-75.130, 3x3 tiles) fills it: ~316k new elements, osm_city_raw
3.79M → 4.09M, city.b64 9.06 → 10.30 MB (165,350 → 180,167 buildings,
22,635 → 23,642 roads), page 21.69 → 22.94 MB; overpasses rebaked (527
chains, 146.7 km). Fetched to 40.100 so the fabric tapers past the county
line instead of cliffing at it. The new wards ride tag/HDEF heights exactly
as the river wards first did — the next lidar_join pass trues them up.
Laptop note: pack_city needs shapely, absent from the CommandLineTools
python here — pip3 install --user shapely (2.0.7) and this box is a full
build machine too. Verified in-pane: all three neighborhood labels over
dense rowhouse fabric, zero console errors; shipped to both homes the same
evening.

### Round 41 (Aug 26)

Round 41 (Aug 26 — Mike, three at once: no tooltips pop when clicked ("the
line of sight thing messed something up"), no streetlights in the three new
neighborhoods, and the night skyline reads as dark blobs ringed by
streetlights): (1) The tooltip kill was real and the instinct half right —
Round 37's occlusion gate was the scene of the crash, but the trigger was
freed geometry: freeOnUpload nulls chunk vertex arrays after GPU upload, and
pickOccluded's second raycast (outerMeshes) threw a TypeError the moment a
sight line clipped a freed chunk's bounding sphere — one uncaught throw in
the pointerup handler killed every card in the city. R37's own verification
never saw it: its street-level refusal short-circuited on rayTargets, and
its altitude shot never crossed a freed sphere. The gate now raycasts
rayTargets (unchanged) and then MARCHES the sight line against demY (40 m
steps, 30 m head / 12 m tail skips) — cheaper than the raycast ever was,
and the NW gorge walls finally occlude honestly; far-district walls no
longer gate (they never did — every invocation that pruned in threw).
Diagnosed by patching Raycaster.prototype.intersectObjects to log during a
synthetic click: the second occlusion call vanished mid-flight, and the
console held the TypeError. (2) The "missing" neighborhood streetlights are
not missing: poles.b64 carries 925 lamps in West Oak Lane, 578 in
Cedarbrook, 553 in East Mount Airy (denser than the Olney baseline) and
they render — the dark fabric is across Cheltenham Ave: the nw-gap fetch
tapers into Montgomery County by design, but the Streets Department
inventory is city-only (27 poles out there), so La Mott stands dark behind
lit Cedarbrook. Left as is: the county line reading dark is the truth.
(3) The skyline grew windows that survive distance: buildings ≥45 m from
every tier (core scene loop, wide decode, far-ring decode — collected into
tallGlow) wear a new 'Lighting the skyline' step: additive points scattered
on the shaft perimeter (seeded hashes so the same offices burn every night,
42% dark, warm white/amber with a 16% cool minority, 0.8 m proud of the
wall so depth keeps them), with the streetlamp px-floor trick (1.5–4.5 px)
TIMES smoothstep(420, 1150) on camera distance so near towers keep their
painted facade windows and far towers become columns of light. Independent
of the G layer (windows aren't street lighting) and alive even without
POLES_B64. Verified in-pane: the bus card (38 to Wissahickon TC) and an
Indego card pop at the exact vantage that used to die silently, Center City
reads as lit towers from 2–7 km, Cedarbrook's lamps burn against dark
La Mott, zero real console errors (synthetic PointerEvents do throw
setPointerCapture InvalidStateErrors — inactive pointerId, cosmetic,
test-harness-only). Shipped to both homes.

### VPS incident (Aug 27)

VPS incident (Aug 27, 06:31–15:35 UTC — Mike: philly3d.com refuses to
connect): all three sites on the lionspool box were down nine hours, and the
deploy was innocent. unattended-upgrades restarted nginx at 06:31; the
startup config test hit "host not found in upstream opendata.adsb.fi"
(sites-enabled/philly3d line 30 — the /adsb proxy_pass, whose hostname nginx
resolves at CONFIG LOAD; the same upgrade run was bouncing systemd-resolved,
so the one DNS lookup that gates the whole config failed) and nginx refused
to start — harkpicks.com and thelionspool.com dark too. Recovery:
systemctl start nginx (nginx -t passed once DNS was back). Root-cause fix in
the vhost (backup at /root/philly3d.vhost.bak-aug27; the enabled file is a
symlink — edit sites-AVAILABLE): the /adsb location now carries
`resolver 127.0.0.53 valid=300s ipv6=off` + `set $adsb_host
opendata.adsb.fi` + proxy_pass via the variable, which defers DNS to request
time — nginx can now ALWAYS start, and a resolver failure at worst 502s
/adsb (proxy_cache_use_stale error still serves the 8 s stale copy).
ipv6=off is load-bearing: the box has no v6 egress (curl -6 dies), and a
runtime AAAA answer would strand the proxy. Verified: nginx -t + reload
clean, all three sites answer, /adsb 200 with 28 live aircraft, cached
repeat 200. If a second belt is ever wanted: a systemd drop-in with
Restart=on-failure / RestartSec=30 would self-heal transient start failures
of ANY cause — not added (minimal touch on a shared box).

### Round 42 (Aug 31)

Round 42 (Aug 31 — Mike: "the other day it was raining and the site was
showing a sunny blue sky", then: rain when it rains, lightning when there is
lightning, snow when it snows, everything that accurately depicts weather):
the sunny-rain sighting was almost certainly the claude.ai artifact copy,
where the CSP wall keeps the fair-weather default by design (philly3d.com's
feed verified live mid-session: ☁ 71% badge) — or a silently swallowed fetch
failure, which also falls back sunny. Either way the model could only gray a
sky; now it weathers. The Open-Meteo current call now carries
rain/showers/snowfall/temperature_2m (°F) alongside weather_code, and
wxSetTargets classifies the WMO code into eased strengths (WXFX): rain,
snow, hail, fog, storm gloom. Two camera-following particle boxes render
precipitation on the GPU — 9 k rain streaks as line pairs, 11 k snowflakes
as soft points with per-flake fall speed and sway — advected in world space
and mod-wrapped around the camera, so flying through a storm streams it past
correctly instead of carrying it along. Custom-shader lesson learned the
hard way: the logdepthbuf chunks need `#include <common>` for
isPerspectiveMatrix, or the program dies silently and the mesh simply never
draws (the stale console error from the pre-fix load masqueraded as current
for a while on top of that). Box, streak length and alpha scale with camera
altitude — the first street-level cut vanished into 1-px subtlety, so the
ground box is 8× denser with 4.5 m streaks — and precipitation fades out
above ~2.6 km. Thunderstorm codes (95/96/99) schedule bolts every
2.6–11.6 s: a jagged polyline rebuilt per strike 1.3–4.1 km out, 240 ms
triple-flicker, its flash spread through applyLighting (sky and cloud-deck
flare, hemisphere boost) scaled by strike distance. Storm gloom sinks the
whole deck toward charcoal (sun −55%, cloud light −55%); plain rain carries
0.5× gloom so wet days read wet. Weather fog (codes 45/48) collapses
scene.fog to 55/850 — the three build-stage fog widenings now write a
fogBase that applyLighting scales live, and rain/snow/gloom thicken the murk
too. Snow whitens the bare-ground mats and terrain (τ≈40 s settle/melt);
roofs and roads keep their baked vertex colors — accumulation there is a
future pass, as is any wet-street look and thunder audio (no audio system
exists). The clock readout now reads e.g. "☁ 98% 74°F Thunderstorm".
?wx=clear|overcast|fog|drizzle|rain|downpour|storm|hail|snow|blizzard|sleet
pins conditions for demos anywhere including the artifact; ?dev's __dbg
gains WXFX, wx('storm') and bolt(). prefers-reduced-motion keeps the sky and
fog response but drops particles and the lightning strobe. Verified locally
at street and altitude for rain/downpour/storm (bolt caught on camera)/
blizzard/fog and the live no-param path (real 98% overcast rendered as
such); shipped to both homes.

### Round 43 (Sep 1)

Round 43 (Sep 1 — Mike: snow on rooftops and roads, wet-street sheen in rain,
and green spaces white when accumulation is happening): one shared fragment
patch (wxSurfacePatch) now lays weather on every static surface instead of
just the bare-ground planes. It injects after color_fragment /
roughnessmap_fragment / metalnessmap_fragment: an up-facing weight from the
view-space normal against world up (rotation-invariant, so it needs no new
varyings), a world-position hash for patchiness (world pos rebuilt from
cameraPosition − vViewPosition · mat3(viewMatrix) — no transpose(), WebGL1-
safe), snow as a mix toward pale white on up-faces with a 0.14 frost floor
on walls so the grazing-angle rowhouse sea pales too, wet as darkening plus
a roughness drop AND a metalness lift. The metalness lift is the load-
bearing half of the sheen: plain darkening dies in the ACES shoulder (a
0.62× diffuse on a sun-lit pale surface tone-maps to nearly the same pixel
— verified with a GPU-side getUniform + getShaderSource probe when the
first cut looked like a no-op), and dielectric fresnel only gleams at
grazing angles, so mix(metalness → 0.32, weighted toward dark surfaces)
is what makes the whole sky sheet across wet asphalt in aerial views.
Applied in build().then before the first render (nothing recompiles):
chained onto cityMat after its facade hook (whose replaces keep the literal
includes), plain-assigned to every hookless MeshStandardMaterial; water
(liquify), vehicles, glass, street text and poles keep their own programs,
which also keeps moving things from wearing the weather. Parks and lawns
are up-facing polygons, so green spaces whiten with accumulation (tree
crowns keep summer green with only the frost floor — flocking leafless
winter trees is its own future project). WXFX gains wet (in τ25 s, dry-out
τ300 s) and snow accumulation semantics: settle τ40 s, melt τ600 s (τ180 s
above 38 °F, and above 38 °F the stick target drops to a quarter — slush);
uniforms update before the reduced-motion early-return so those users keep
surface weather. Sky reads milk during/after snow (snow·0.55 / acc·0.3
lerp), fog whitens with lying snow, and the old applyLighting groundMats
snow lerp is gone — the shader owns it now. Verified: blizzard aerial
(whole city blanketed, streets/roofs/parks white, walls brick), street-
level white ground underfoot, downpour A/B at fixed camera (wet: cooler,
darker, sky-sheened; dry: warm and bright), clear-weather regression
pixel-identical, zero console errors. Shipped to both homes.

### Round 44 (Sep 1)

Round 44 (Sep 1 — Mike, six at once: landmark labels all over the city, include
the Battleship NJ, clean up buildings in the water, SEPTA/Indego icons sized
like the plane icons, anchor icons for boats, bridge traffic up on the actual
decks, more realistic water): the battleship was the best one — the custom
BB-62 build (hull + turrets + funnels off the OSM outline) has existed since
its round but its capture gate read `t === 7`, and the wide repack changed the
type code, so njPoly stayed null and the 270 m hull extruded as a generic
windowed apartment slab afloat mid-river — Mike's screenshot exactly. The gate
now captures by berth radius + >180 m bbox diagonal, any type code, and the
ship stands at her moorings again. Right behind it, the general rule both
rings now enforce: any footprint whose centroid ground reads river channel
(demY < water + 0.5 inside riverCorridor) is bad data and never extrudes —
nothing floats. Citywide labels: ~43 hand-placed landmarks (lat/lon through
the SEPTA frame) cover every quarter — Independence Hall to Fort Mifflin,
Boathouse Row to the Northeast Airport, Cliveden, Valley Green, the
universities, the Camden shore incl. 'USS New Jersey (BB-62)' and the Ben
Franklin Bridge — and the far-label fade widened 2200/3400 → 4200/6800 so
they actually read from a citywide vantage. Pins: SEPTA badge/pin and Indego
badge now share the aircraft formula (dist/135, so identical on-screen size
up close) but cap at 14 — the first cut used the flights' 190 cap and five
hundred buses turned altitude views into a badge blizzard; 14 restores the
old ~1.9 km fade radius. Ships wear a new anchor badge (same navy casing as
the aircraft pins, fouled-anchor glyph, billboarded, distance-scaled, in the
pick targets so tapping it opens the vessel card). Bridge traffic: the two
custom spans register their real deck profiles in BRIDGE_DECKS (BFB chord +
deckY, WWB polyline + arc-length profile) and the traffic bake consults
bridgeDeckLift() — the WWB dead-kill (`wwbNear`) is gone, so the Whitman
carries cars ON its deck, and the BFB's flat water+20 guess is replaced by
the true rising roadway. Water: the corduroy moiré was the regular 4-octave
gradient-wave sum aliasing at mid-range — each octave now carries a
pixel-footprint weight (fwidth-based, bows out before its wavelength falls
under a few pixels), plus a fifth off-axis mid octave, two slow crossed
gust envelopes that drift ruffled lanes and glassy calms across the reach,
and a broad low-power sun lobe under the point sparkle. Verified: battleship
at berth (turrets, masts, no slab), WWB cars on the deck, label sweep from
2.6 km reads Penn to the Aquarium, anchor badges over shipTest vessels, no
console errors. Shipped to both homes.

### Round 45 (Sep 1, same day)

Round 45 (Sep 1, same day — Mike: still buildings in the water, the ground
reads as perpetual snow when it isn't snowing, trolley pins should match the
bus pins): the surviving floater was in the Heinz refuge impoundment —
Round 44's dem/corridor test only knew the Delaware east bank and the
Schuylkill, and Philly-side standing water never qualified. Now each packed
ring pre-scans its own area records (wxWaterGrid: skim buildings and roads by
record layout, scanline-rasterize every kind-1 water polygon into a 24/30 m
grid) and the building pass refuses anything whose centroid stands in
rendered water — ground truth by construction. A python decode of both b64s
confirmed the kill list: 70 footprints, all genuinely in water (refuge
boardwalk structures, Schuylkill-mouth piers, three boat sheds). The
"perpetual snow" was NOT stuck weather state (uSnowAcc provably 0) — it was
the overcast wash: a full cloud deck kept fair-weather brightness, and the
white PMREM dome over-lit every up-facing flat into chalk. Overcast now
darkens honestly: cloud light −15 %·cover (which also calms the env bake),
hemisphere −22 %·cover, bare-ground flats −15 %·cover toward earth. And every
SEPTA vehicle — trolley and el included — wears the badge billboard now; the
line-colored lollipop pins are retired (septaPin still serves the search
marker). Verified: refuge water empty, West Philly all-badges, warmer
overcast tone, no console errors. Shipped to both homes.

### Round 45 coda (same afternoon)

Round 45 coda (same afternoon — Mike: still reads as snow, figure out
something else for ground cover): the overcast dimming was treating the
symptom; the disease was one uniform pale tone blanketing every bare-earth
plane. wxGroundPatch now runs under the weather pass on all groundMats: a
two-octave world-space value-noise mottle mixing a grass multiplier
(0.58, 0.72, 0.42) against dry-earth (0.98, 0.93, 0.74) at ~80 m patches with
~22 m and ~3 m detail, both finer octaves fading by pixel footprint so far
ground stays calm (the water-moire lesson applied to land). Multipliers, not
replacement colors — applyLighting's day/night retint still owns the base,
and the chained snow/wet pass lays OVER the mottle (hooked at map_fragment,
before color_fragment, precisely so the chain order lands snow on top).
The flats now read as scrub and lawn from the air on any gray day, and
forced accumulation still whites them out completely. Shipped to both homes.

### Round 46 (Sep 1, evening: the optimisation audit)

Mike asked what could be optimised or improved, open to anything. A read-only audit
(17 finder angles, every finding adversarially re-verified, 150 findings, 145 kept)
became the plan in the session notes; he approved all of it except three owner
calls: labels stay off by default, the About panel stays out of the bar (the credit
line's Credits link opens it), and the full build stays behind the veil. Everything
below lives on the `audit-batch-1` branch.

- **Payload.** build.py stores the four int16 blobs byte-planar (header, then every
  low byte, then every high byte): DEFLATE sees two smooth streams and the gzipped
  page drops 12.76 MB to 9.77 MB with no packer change; app.js's one `unb64()`
  re-interleaves (the charCodeAt loop, 6x faster than `Uint8Array.from(str, fn)`).
  traffic.b64 stays interleaved (short deltas grow 5% shuffled). The four identical
  Montserrat faces became one variable `font-weight: 400 700` rule.
- **Load path.** The two ring decoders stage vertices in growable typed arrays
  (`VBuf`/`IdxBuf`, 24 B per vertex instead of ~92 boxed), seal chunks at 60k
  vertices (all Uint16 indices) and upload a dozen at a time as they seal; every
  new ring mesh draws unculled exactly once so a chunk behind the veil camera no
  longer keeps its CPU copy until first seen (a frustum-culled mesh never uploads
  and never frees). Measured in the same visible pane: peak heap 2,763 MB to 691 MB,
  far ring 1.9 s to 1.0 s, outer districts 1.0 s to 0.6 s, Ready 4.9 s to 2.7 s,
  same 9.99 M vertices. An occupancy bitmap pre-tests footprints against the
  overpass swaths (9.3 M string-keyed Map probes gone); the covered-tunnel class
  no longer erases the rowhouses above it. build() yields through the shared
  MessageChannel helper instead of setTimeout(10), which background tabs clamp
  to 1 s (23 steps of that was 23 s of sleep).
- **Runtime.** The shadow map redraws only when aimSun moves the box or the sun,
  when the dock set changes, or every 4th frame while vehicles move; solar/lunar
  are memoised per clock minute; fabric chunks wholly beyond fog.far are skipped
  (view-depth test; in true fog 236 of 467 meshes drop); the facade shader takes
  the far average straight away once `det` is zero; the pixel ratio adapts to
  frame time between 0.9 and the display's own ratio (`?dpr=N` pins it); instance
  buffers upload only their live range through one `flushInst`; the dead
  `septaPin` mesh, the per-frame ship recolour, the per-frame card innerHTML
  and the Indego atlas repaint (now signature-gated) are gone.
- **Regressions fixed.** The Enter button kept focus in Chromium so W A S D and
  every hotkey were dead until a canvas click (the keydown guard bailed on any
  BUTTON; now only Space/Enter, clicks blur, Cmd/Ctrl/Alt chords are ignored);
  359 district steeples were wound inward and culled; tree taps needed a live
  vehicle on screen; the first search blurred its own input; Ships off
  reconnected on the next frame; a dead SEPTA feed left ghost buses; the weather
  fetch had no timeout, retry or hidden-tab gate; DST evenings read an hour off;
  the flight rotation walked two dead proxies on one blip; far-ring roads paved
  a 170 m band twice at the wide seam.
- **Feeds.** SEPTA is read from the VPS's baked `septa.json` (ops/septa_bake.py,
  every 10 s, ~16 KB instead of 343 KB per pull) with the JSONP rotation as
  fallback; ships poll `ais.json` from ops/ais_relay.py (one aisstream socket
  held server-side, stdlib WebSocket client) with the direct socket as fallback
  until the relay is live and the key is rotated. Both server pieces, the nginx
  additions (Cache-Control, gzip_vary, hardening headers, www redirect, /b beacon
  endpoint, static feed files), the systemd restart drop-in and the uptime recipe
  are in `3d-model/ops/` for Mike to apply; nothing was changed on the box.
- **Instrumentation.** `?dev=1` shows a 1 Hz readout and `__dbg.perf()` returns
  per-step build timings, frame p50/p95, renderer.info and the heap; on
  philly3d.com the page sends one 204 beacon per checkpoint to `/b` (no IP kept).
- **Data and pipeline.** lidar_join.py reran over the whole city (424,652 measured
  ways, the NW wedge now trued) and pack_city.py repacked with the fixed packer
  (area centroid guard, saturation is fatal, Douglas-Peucker ring budgets,
  missing LUTs fatal unless `--allow-missing`); pack_wide clips rings to the
  int16 box (the truncated Fairmount ring); one `philly_frame.py` projection for
  every script; `overpass.py` per-tile checkpoints for all three fetches;
  `pipeline.py --graph`, `tests/` (27 tests, stdlib), `requirements.txt`,
  `provenance.py`, `docs_check.py`; handoff.md rewritten and this log split out.
- **UX.** Preferences persist (localStorage), views are shareable
  (`#p=x,y,z,yaw,pitch&t=...&l=mask`, Copy Link), the three panels are mutually
  exclusive with Escape and tap-away, `aria-pressed`/`aria-expanded`/`aria-live`,
  a landscape-phone breakpoint, 44 px targets, download progress on the veil,
  and the always-visible credit line naming every data source.

Still open after this round: applying the ops recipes on the VPS (Mike's go per
change), rotating the aisstream key once the relay is live, `git gc` with Dropbox
paused (615 loose objects, 709 MB), the ~12 areas still packed by both tiers in
pack_wide's 500 m margin, and Tier 2 of the facade plan.

### Round 46 coda (Sep 1, night: lightning, rain, the horizon, stray buses)

Mike, from a screenshot at altitude at dusk: an hour of lightning over the city and none in the
model; rain that reads as long, thin, slow lines; the sun still visible after sunset from high up
over a hard world edge; SEPTA pins floating outside the city. Checked live: Open-Meteo's current
code said 80 (showers, 0.6 mm) while the NWS had a Severe Thunderstorm Watch up and KPHL was
reporting heavy rain, so the model could never have known. The NWS API is CORS-open and now feeds
`WXFX.storm` beside Open-Meteo (see the handoff's weather-sources note); tonight's conditions put
the page in storm mode with watch-cadence bolts and the readout "Light rain, Thunderstorm Watch".
Rain streaks lost the altitude scaling that drew 21 m spaghetti (now 4.5 to 10 m), fall faster the
higher the camera, and fade out by a kilometre up. The sun disc and halo now set with the horizon
(`uSunVis`), the env-bake sun hides below it, and a 60 km apron of far-ground material under the
whole world turns the old diagonal edge against the sky dome into ground fading into fog. Buses
and trolleys with no drawn street within 140 m are marked `v.off` by the road snap and are neither
drawn, counted nor pickable. Verified in-pane: storm state from the live NWS watch, bolt flash,
short streaks at 380 m and none at 1300 m, the disc gone at 7:50 PM, the horizon clean from 1.5 km.

### Round 46 coda 2 (Sep 1, late: real lightning)

Mike, still no lightning: the storms were over Delaware and the Jersey shore, not the city, and
he wanted the strikes within 50 miles. No free API carries lightning, but the Blitzortung
community network publishes strikes over a public MQTT relay (the Home Assistant feed) on
geohash topics; probed live, it delivered 129 strikes within 160 km in 30 s. `ops/lightning_relay.py`
(stdlib MQTT client) keeps one subscription and writes `lightning.json` for the page, which polls
it every 4 s and draws each new strike at its real position (`spawnStrike`; the bolt generator now
takes a ground point, `spawnBoltAt`), pulled in to the apron edge when farther than 55 km, with a
distance-scaled flash. Verified locally against the live relay: 62 strikes in ten minutes, nearest
26 miles, bolts on the horizon toward New Jersey, readout "62 strikes in 10 min, nearest 28 mi".
The relay runs on the VPS as `lightning-relay.service`; the static file rides `location /` with
`gzip_static` like the other feeds.

### Round 46 coda 3 (Sep 1, late: lightning toned down)

Mike: the lightning was jarring and repetitive, too many flashes. With several hundred strikes in
ten minutes across the 110 km relay window, every 4 s poll had a handful of fresh strikes and each
drew at once with the full triple strobe. Now each poll keeps only the two nearest fresh strikes,
the page draws one at a time and never faster than every 2.5 to 5 s, a strike beyond 9 km gets a
single soft pulse with the bolt capped at 0.6 opacity instead of the triple strobe, and the sky
flash falls off as 1100 / distance in metres with a floor of 0.05, so a strike 36 km out over
New Jersey barely stirs the deck while one over Center City still lights the world. Verified on the
live site: storm on from the relay, one bolt drawn with the next held in the queue behind the gap,
far-strike flash at the floor. Deployed and pushed as e7b12c7.

### Round 47 (Sep 2): the towns across the line, a flight limit, orbit on search, the Whitman lands in Jersey

Mike, four asks: people can fly much too far outside the city; Gloucester City NJ should look
like an actual town with buildings, and so should the rest of the surroundings; a searched
location should start orbiting on arrival; the Jersey end of the Walt Whitman needs fixing.

- **Why the surroundings were empty.** The far ring packs everything inside its box
  (-12000..16500, -21700..9700) that the fetches brought home, and the six `fetch_city.py`
  boxes plus the wide and south boxes are lat/lon rectangles that stop at the city's own
  extents: three strips of the box were never fetched at all: south of 39.915 east of
  -75.185 (the Navy Yard's south half and, across the river, Gloucester City, Camden's
  Fairview and Morgan Village, Brooklawn, Westville, Bellmawr, Mount Ephraim, Audubon,
  Oaklyn, Haddon Township), east of -74.990 between 39.915 and 40.050 (Pennsauken's east,
  Merchantville, Cherry Hill's edge) and north of 40.100 west of -75.130 (Whitemarsh,
  Springfield, Wyndmoor, Cheltenham's north, Abington). OSM counts before fetching:
  Gloucester City 1,471 mapped buildings, the south strip 31,892, east 2,921, north 2,099.
- **The outskirts tier.** `fetch_outskirts.py` (30 tiles, ways only: the Delaware's water
  relation would have dragged in the whole river) -> `osm_outskirts_raw.json` ->
  `pack_outskirts.py` -> `outskirts.b64`: 1.0 m units, the far ring's no-attribute layout
  (legacy magic 0x53485459, no LiDAR / OPA / roof join exists across the line), rows fused
  with a 3 m bridge instead of 1.8 so detached houses merge into strips, 16-vertex rings,
  60-vertex areas, and anything whose centroid an older fetch box owns is skipped.
  Fetched 358,015 elements in 30 tiles (36 MB raw); packed 31,576 buildings in
  (4,408 owned by older tiers) to 25,526 strips, 7,501 road runs and 251 areas: 963 KB
  binary, 1.28 MB base64, 4.5 s. The far-ring step is split into `raiseRing(bin, S, label)` (buildings, roads,
  areas into staged chunks) and `uploadRing(R)`, with the terrain built between the two in
  the city step; a new step "Raising the towns across the line" runs the same decoder on
  the outskirts blob. build.py: PLANAR + REQUIRED + `let_blob("OUTSKIRTS_B64")`; tests:
  BLOBS / RING_CAPS / EMBEDDED entries and an `OutskirtsHandoff` test (every outskirts
  centroid inside the box and outside every owned box); pipeline stages; handoff rows.
  Page 24.08 MB raw (+1.30 MB), 10.29 MB gzip, under the 25 MB tripwire and inside the
  deploy gate; 28 tests green.
- **Overpass stall.** The first fetch sat 13 minutes on one tile: `overpass.private.coffee`
  hangs (60 s+ on a one-line count query, main mirror 1 s, kumi 52 s) and the rotation
  retries through it with a 190 s timeout each pass. `overpass.py` now honours
  `OVERPASS_MIRRORS=url[,url]` for a run; probe the mirrors with a tiny `out count` first.
- **The flight limit.** `fetch_boundary.py` pulls OSM relation 188022 (the city line,
  367.5 km2, the state line mid-river), writes `city_limit.json`: `city` (177 points at
  40 m) and `bound`, the line buffered 2 km, simplified 120 m, clipped to the far-ring box
  less 300 m (47 points). `insideLimit` / `clampLimit` (nearest ring point, 3 m in) run in
  applyFly, setMode(FLY), applyHashView, panOrbit and walk; SEPTA vehicles beyond the
  limit are `v.off`. Verified: a jump to (6000, 5000) lands at (3320, 4551), 2 km past
  the state line at the Whitman; (-14000, -8000) -> (-10844, -9747); (2000, -20000) ->
  (4818, -17739); City Hall untouched. The towns beyond are scenery seen from the edge.
- **Jersey ground.** Every low cell east of the rough `DEL_BANK` dived to the riverbed,
  and south of the stadiums that polyline drifts into Gloucester City, so its filled
  riverfront read as open water and its low blocks were dropped as "floating".
  `stateLineX(z)` (the city ring's easternmost crossing, cached per 10 m of z) gives
  `njLand`: more than 400 m past the state line is land, and `eastOfDelaware` excludes it,
  which fixes the far and wide terrain, `siteY`, the building drop and the road deck
  lift in one place.
- **The Whitman lands.** `wwb.json` used to interleave both carriageways (the zigzag
  east of the chord fix) and stopped at x 2649 with the deck 20 m up in mid-air. It is
  now one eastbound carriageway (OSM ways 424803351, 886672856, 1027616621, 123617847,
  1311279172) to where the bridge tag ends at (2777, 4866). The profile is one function,
  `profY(sv)`, shared by the deck and `BRIDGE_DECKS.yAt`: the Jersey approach descends
  from W0 + 37 at the cable end to ground + 0.8 at the polyline's end and the ground floor
  (+6 m) fades over the last 250 m so it can land; `wwbUnder()` drops packed motorway
  ribbons within 30 m of the alignment east of x 1750 short of the landing, or the packed
  I-76 would pave a flat twin under the viaduct.
- **Orbit on search.** `searchFlyTo` now glides (`glideFly`, 0.9 to 2.6 s by hop) to the
  vantage and its `done` callback, `orbitAround`, switches to orbit with r / theta / phi
  taken from the camera pose (no jump), `orbitSpin` turning 0.12 rad/s (~50 s a lap) until
  any input takes flight through `autoFly`, as after Enter. Buses keep the fly follow
  (`noOrbit`); reduced motion parks without spinning; the hash is frozen while circling.
  Verified: "Independence Hall" -> the orbit hint, target (-451, 32, -371), r 286 m, theta
  +0.171 rad in 1.5 s, camera moving.
- **Review pass** (four finder angles, twelve verified, one refuted) before the commit:
  the south fetch box was listed as "owned" whole, but pack_wide packs buildings only
  inside WIDE (x <= 2300, lon -75.118), so the strip east of that between lat 39.890
  and 39.9155, northern Gloucester City and the Whitman's landing, ~1,050 buildings,
  was packed by no tier (the owned box now stops where pack_wide stops; roads and areas
  keep pack_wide's 200 m and 500 m margins); the far ring's wide-seam road skip
  (`inWide` both ends) also ran for the outskirts and ate 2.4 km of Gloucester City
  streets south of z 6134, where the wide data ends (`raiseRing` takes a `wideSeam` flag,
  the far ring only); a Nominatim hit named "Philadelphia ..." outside the city (the
  Philadelphia Country Club in Gladwyne, Philadelphia Avenue in Bensalem) passed the
  name filter and the search circled a spot beyond the limit, so the rows are now also
  tested with `insideLimit`, `orbitAround` clamps its target and `applyOrbit` clamps the
  circling camera; route search listed and flew to `v.off` buses (now excluded); a search
  typed from a locked look had its glide cancelled by the first mouse movement (the lock
  is released first); the compass eased to north while the search spin undid it
  (`faceNorth` clears `orbitSpin`); `stateLineX` picked the Bucks County line above the
  Poquessing mouth (null there now, latent since no low cells sit there); and the new
  tier test had landed below the file's `__main__` guard.
- Deployed to philly3d.com and pushed to main on Mike's go. Follow-ups: run
  `bake_overpasses.py` over `outskirts_tiles/` too (the I-76 / I-676 / 42 interchange at
  the bridge's foot is flat ribbons); the 150 m DEM still floods marsh cells along Newton
  and Big Timber creeks; the bound's northeast tip is cut by the box.

### Round 47 coda (Sep 2, afternoon: a stale tab, the filler, the landing, phones)

Mike, from a tab that still held the old page (philly3d.com sends no Cache-Control, so an
open tab or a heuristically cached copy keeps the previous build): the Whitman's Jersey end
still a pile of tilted slabs, the surroundings still bare, search not orbiting, and was the
lightning real? Checked live: the served page is the new build (the outskirts step runs in
256 ms, no failures), a search circles Rittenhouse Square on desktop and under touch
emulation, and the lightning was real, 24 Blitzortung strikes within 80 km in ten minutes,
nearest 73 km, with a heat advisory and an overcast sky over the city itself.

- **The landing, again.** The old zigzag tail was the stale tab, but the new profile had its
  own flaw: a per-point ground floor sampled the 150 m DEM every 20 m, so the last boxes
  pitched up and down a few metres against their neighbours. The last 400 m are now one
  straight grade from the viaduct down to a metre above the highest ground under them.
- **The filler.** Mike: the surroundings need something other than open space where people
  live, accurate or not. OpenStreetMap maps the land use across the suburbs even where it
  maps few of the buildings, so `fetch_landuse.py` pulls residential, commercial, industrial
  and retail land use over the whole far-ring box (16 tiles) and `pack_outskirts.py` marches
  every street inside residential land use beyond the city line, placing 11 m deep strips
  of houses at a 14 m pitch fused six at a time, and boxes along the main roads through
  commercial (40 m) and industrial (60 m) land use, only where real footprints cover under
  10% of the ground within 150 m, never on a footprint, a road, a park or water, and never
  inside the city line (the far ring's own Cheltenham and Lower Merion slivers get filled
  too). Where nobody drew the land use either, a class-5 street with at least
  eight other street segments within 120 m counts as a neighbourhood. Result: 24,005 strips
  (23,854 residential, 90 commercial, 61 industrial) from 77,563 accepted slots; 71% of the
  street corridors beyond the line now stand within 40 m of a building, 46% of the whole
  band (which is mostly river, marsh, farmland and parks). outskirts.b64 grows to 49,509
  buildings, 2.05 MB base64.
- **Phones.** Mike's three asks: the lit windows died at half the desktop distance because
  a phone has half the pixels per window, so `uDetFar` (0.55 on touch devices) stretches
  the facade detail fade and the outer glass fade, and the tower window points come in
  from 200 m at 2.2 px instead of 420 m at 1.5 px; a portrait gate (`#rotate`, phones only:
  coarse pointer, portrait, under 820 px) asks for the phone sideways; and the two thumb
  pads, Move on the left and Look on the right, are faintly there whenever a touch device
  flies (`body.touchfly`), the joystick docking on Move and Look brightening while a
  finger looks. Page 24.85 MB raw, 10.58 MB gzip, 150 KB under the 25 MB tripwire; 28 tests green.
  Deployed and pushed on Mike's standing go.

### Round 47 coda 2 (Sep 2, evening: the stadiums, the clock, the rain)

Mike, with aerials of both venues: the stadiums need work and should light up at night,
Citizens Bank Park carries a building that is not there, a new tab kept his old time
setting, and the long thin rain looks dumb.

- **The phantom.** LiDAR's building-footprint join gave every small footprint around the
  ballpark, the light-tower bases, 74 m (the tallest steel measured from the sunken field),
  and a 2,700 m2 lot beside them the same 74 m: five thin towers and one tall slab next to
  the bowl. The wide loop now captures those records: a footprint under 220 m2 taller than
  30 m within 300 m of a stadium becomes a mast position, anything larger is clamped to
  12 m, and the two `t == 8` bowls are built after the loop, once their masts are known.
- **The bowls, from `south_geometry_research.json`.** Citizens Bank Park: brick drum to
  15 m, the Terrace horseshoe to 40 m in precast with green seats on top, the patina canopy
  over the top rows, light standards where LiDAR found them (the four corners only as a
  fallback), the left-field scoreboard with a video board. Lincoln Financial Field: brick
  base, end-zone stands to 30 m, sideline decks to 46 m in precast with midnight-green
  seats, the two wing canopies with white fascia, four corner masts to 66 m. Colours are
  stored dark for the r149 pipeline (the research hexes came out cyan and mint at first).
- **Lit at night.** The fields, the mast heads and the scoreboard live in their own mesh
  whose material adds `diffuse x 2.4 x uNight`, and floodlight sprites (additive points,
  3 to 16 px by distance, one per mast head at the ballpark, eleven along each canopy edge
  at the Linc) come on with the streetlamps in `updateLights` and scale with the pixel
  ratio like the tower windows. Verified: 31 sprites, on at 21:30, off by day.
- **The clock.** `writePrefs` no longer stores the clock and the boot no longer restores
  it: every load is Philadelphia's own time. The address bar never carries `t=` either
  (a reopened tab must wake to the real time); only the copied link does, when the clock
  is pinned, so a shared moment still opens at its moment.
- **The rain.** 0.9 m dashes at street level (a drop over one frame) stretching to 2.3 m
  from altitude, 16,000 of them instead of 9,000 at 4.5 to 10 m, slightly brighter.

### Round 47 coda 3 (Sep 2, evening: the stale tab, closed)

Mike's go on the VPS: `location /` on philly3d.com now sends `Cache-Control: no-cache`
(nginx -t, reload, backup kept as philly3d.bak-20260902). A page load revalidates every
time and gets a 304 when nothing changed; the feed files revalidate too; `/adsb` keeps
its own no-store. Verified: GET / returns the header with the gzip body, /index.html
and /lightning.json carry it, a conditional request answers 304. (A bare HEAD on / does
not carry it, an nginx index-redirect quirk; browsers send GET.) `ops/philly3d.vhost.live`
recaptured.

### Round 47 coda 4 (Sep 2, night: the Linc's roof, more light, the lots)

Mike, with a live screenshot and a Google aerial: a partial roof over the Linc's field that
is not there, more stadium lights for both with a glow at night, and the neighbourhood is
mostly parking lots, not lawn.

- **The roof.** `upperRing` built each deck band from two arcs voted separately: the outer
  ring's points passing keepFn and the inner ring's points passing the same test. The inner
  ring is a 0.55 copy, so fewer of its points passed, the arcs were unequal, the band
  polygon crossed itself and earcut roofed the field. The band now takes the outer arc's
  INDICES on the inner ring (same vertex order), a proper ring every time, and the end-zone
  stands, which the old vote had silently skipped, stand at 30 m.
- **More light.** Three floodlights across every mast head (the ballpark's surveyed
  standards, the Linc's four corners), sixteen a side along the Linc's canopy edges, sprites
  up to 18 px; and a night halo: additive warm sheets (`haloMat`, opacity 0.16 x night) over
  every deck and both fields, on with the streetlamps.
- **The lots.** `fetch_parking.py` pulls OSM amenity=parking for the sports complex (87
  surface lots, garages skipped) into `parking_south.json`, and the outer-districts builder
  lays them as asphalt flats a hair above the lawn: NRG's lots, the ballpark's, the Linc's,
  Lot P, Lot M East.

### Round 47 coda 5 (Sep 2, late: asphalt with stalls, live scores)

Mike: there is no grass in that district, fill it with parking lot and draw the spaces;
and show live score bubbles over the arena and stadiums while a game is on.

- **The sheet and the stalls.** No OSM land-use polygon covers the complex, so
  `fetch_parking.py` closes the 79 lots west of 7th Street over the streets and plazas
  between them (buffer 90 m, erode 60 m: 11 sheets) and the builder lays the sheets under
  the lots, both in stored-dark asphalt. Each lot then gets its stalls in the app: ticks
  2.7 m apart on both sides of a back-to-back line, double rows 18.5 m apart along the
  lot's long axis, clipped to the ring, one LineSegments mesh shown within 3.5 km of the
  complex (1 px lines alias into noise beyond).
- **Scores.** ESPN's public scoreboards (CORS-open, cached seconds at their end) for MLB,
  NFL, NHL and NBA, polled once a minute while the tab is visible, backing off on failure.
  A game counts when its state is `in` and the home side is PHI, and its bubble sits over
  that sport's venue: the ballpark, the Linc, the arena (Flyers and 76ers stack if ever
  both). The bubble is a label: a live dot, "PHI 4, NYM 2", the clock or inning, the home
  colour on the border; hidden beyond 14 km. `__dbg.scoreTest()` stages one at each venue.
  ESPN joined the credit line and the About text.

### Round 47 coda 6 (Sep 2, late: the sheet holds, the rows read)

Mike: still a mess, grass through the asphalt, and the lot lines need loads of work. Two
faults. The sheet was a flat polygon (`flatPoly`) spanning ground that undulates by half
a metre, so the mottled lawn rose through it wherever the terrain sat above the plane,
and the closed union of lots left holes and ragged edges; the sheet is now the convex hull
of the complex's lots clipped to its block (Broad to 7th, Packer Avenue to the Delaware
Expressway) and DRAPED on the terrain with `drapedPoly` at 20 m, as the big parks are,
with each lot draped on top. And the stalls were ticks alone, which read as noise from
altitude; each double row now carries its two stall-front lines the length of the row
plus the ticks, rows follow the street grid (whichever grid axis the lot's long side is
nearer), every line clipped to its lot. From 600 m the lots read as rows; from 100 m as
stalls.

Still patches (Mike): the ground is a 25 m heightfield off a 50 m elevation grid and the
sheet was draped at 20 m, two linear reads of one surface that disagree by more than the
10 cm the sheet had, so its facets showed as jagged green blobs. The sheet is now draped at
8 m and the lots at 10 m, the stack lifted to 12, 13.5 and 16.5 cm (streets sit at 24), and
nothing rises through it from 700 m or 250 m.

### Round 47 coda 7 (Sep 2, night: the buried Schuylkill, the blue overcast)

Mike: the Schuylkill is covered by grass in one section (the reach between the Columbia and
Falls bridges), and a 92% overcast day still shows a blue sky.

- **Why the river vanished.** Above the Fairmount Dam the pool sits a couple of metres over
  the tidal water plane, and the 50 m and 100 m elevation grids smear the banks across a
  150 m river, so the ground stood well above the flat water. The outer districts only
  showed the Boathouse Row reach because their water plane lies under everything; the far
  ring's strip had no water at all there: the Schuylkill is an OSM multipolygon whose member
  ways carry no tags, so neither packer ever held a ring for it. And the rough centerline
  the corridor tests used ran a kilometre WEST of the river north of Center City.
- **The fix.** `SCHUYLKILL` retraced bridge to bridge from Flat Rock Dam to League Island.
  `schuylkillCut()` (1 within 60 m of the centerline, 0 at 95 m, dam to the NW patch) carves
  both ground builders to the riverbed, `drapeY()` carves every draped polygon the same way
  so Fairmount Park dips under the water instead of roofing it (park drapes touching the
  reach sample at 30 m), and a flat sheet of the river material under the reach between the
  outer districts' box and the patch gives the channel its water; the patch keeps its own
  draped river. Verified top-down at Peters Island and at the Falls seam.
- **The overcast.** Cover already tinted the sky, but only halfway to a blue-gray. Past 75%
  cover the dome now goes to a neutral overcast gray and the sun dims harder, and KPHL's
  observed cloud layers (an OVC or BKN deck) raise cover over the model's estimate.

### Round 47 coda 8 (Sep 2, evening: every game, home or away, and the hour after)

Mike, with the Phillies playing in Arizona and no bubble: every Eagles, Phillies, 76ers and
Flyers game should show while it is on and for an hour after it ends, away games included.
The poll had gated on the home side being PHI. Now any event with a Philadelphia
competitor counts: live, its bubble hangs over that sport's venue with the Philadelphia
side first, the clock or inning, and "away" on the road; final, it stays an hour with the
score and a still gray dot. The hour runs from the moment the feed turned the game final,
or, for a page that arrived after that, from the start time plus a typical length (3 h
MLB, 3.3 h NFL, 2.6 h NHL, 2.4 h NBA). Polls every 45 s while something is on, 90 s otherwise.

Mike: the Phillies logo, a pin down to the stadium, and the bubble higher. The bubble now
carries the team's logo from the feed (ESPN's own CDN, only that host, removed if it fails
to load), hangs at 135 m over the ballpark, 150 over the Linc and 115 over the arena, and a
line in the team colour drops from it to a small ball on the roof.

### Round 48 (Sep 2, night): roofs, storefronts, wall colours, the 75 MB tripwire

Mike: bump the tripwire to 75 MB and the gzip gate in proportion, then all four of the
realism sources at once: LiDAR roof shapes, Mapillary wall colours, OSM storefronts,
Overture attributes. Three agents ran the fetches in parallel; the app and packer work
stayed with the lead.

- **Tripwire.** build.py's MAX_HTML 25 -> 75 MB, the deploy gzip gate 12 -> 36 MB, the
  test's limit likewise. The page was 24.9 MB; this round leaves it at 24.95 MB.
- **What "the LiDAR we already use" actually was.** The core's roof forms come from nine
  full-resolution COPC tiles (1.7 GB) of the 752-tile, 100 GB NOAA 2022 dataset; the rest of
  the city only ever had the City's footprint layer, two heights per building, and its
  max-minus-typical height does not separate pitched from flat (median 0.6 m on the core's
  measured gables). So: `fetch_lidar_roofs.py` streams every tile at coarse resolution
  through COPC's octree over HTTP (a few MB a tile instead of 130), classifies each OSM
  footprint with lidar_core's method on the coarse grid, and writes per-tile JSON merged
  into `lidar_city_roofs.json`; it runs for hours in the background and is picked up by the
  packers whenever it is merged. Meanwhile `roof_tags.py` pulls OSM's own roof:shape tags
  (33,020 ways: 26.5k flat, 6.2k gable, 270 hip) and every wide/south way centroid.
- **The roof word.** pack_city (magic 0x5348545C) and pack_wide (0x5348545D) pack the
  sampled roof-colour index with a form and a rise in one int16: (idx + 1) & 0x1FF |
  form << 9 | rise << 12, form 0 unresolved, 1 gable, 2 hip, 3 skillion, 4 known flat.
  pack_wide attaches way ids to the id-less scene buildings by centroid (4 m). A merged strip
  keeps its form only when the piece is one building. Far ring: 1,788 gables, 165 hips,
  1,775 known flats; outer districts: 662 forms.
- **Raising them.** `roofBits` decodes the word, `roofPlan` decides (a measured or tagged
  form, else the core's lottery for small unresolved houses at rowhouse height), `roofQuad`
  demands an honest quad or, new here, the oriented box when the footprint fills 80% of it
  (a bay or a twin's jog no longer forfeits the roof), and `raisePitched` stops the walls at
  the eave and pushes quadGable / hipGeom straight into the chunk (`pushGeom`). Rise from
  the LiDAR pass when measured, else a third of the span. Verified: the tagged houses of
  Eastwick carry gables; Center City unchanged; the Northeast rows stay flat, correctly,
  and its twins wait on the LiDAR pass.
- **Storefronts (Tier 2).** `fetch_shops.py` (2,478 OSM businesses over the wide and south
  boxes) and `bake_storefronts.py` (2,341 placed on the street-facing wall of their building,
  with line-of-sight and sidewalk-depth rules that the literal nearest-road rule needed;
  50 KB blob, magic 0x53485446). The app's "Dressing the storefronts" step gives each a dark
  frame band and glass proud of the wall (full height, or the lower half for banks, clinics
  and theatres), an awning in the trade's colour where a shop would hang one, a signboard
  above, and the glass and sign glow after dark through an `aLit` colour attribute.
- **Wall colours.** `fetch_mapillary.py` and `bake_wall_colors.py` are written and pass an
  end-to-end dry run on synthetic streets (the bake recovers every face within 1/255), but
  Mapillary's API needs a client token we do not have: a free developer registration on
  mapillary.com. Not in the build until a real pass exists; the dry-run outputs are
  gitignored.
- **Overture.** Checked through DuckDB in a minute (807k buildings in the box, 2026-08-19
  release): its roof shapes and colours are OSM's tags verbatim, its extra is heights we
  already have from the City's LiDAR. Nothing ships from it.
- **First LiDAR merge, same night.** 133 of 752 tiles streamed (about 15 MB a tile at the
  chosen resolution, 1.7 s of processing each): 17,148 buildings resolved, 6,960 gables,
  1,218 hips, 8,970 measured flats; 18,455 measured forms available to the far ring after
  the join, 1,706 attached in the outer districts. Fox Chase and Rhawnhurst's twins and
  singles carry their real gables and hips. Repacked and deployed; the rest of the city
  follows when the run completes.
- **The run completed** in 15.9 minutes for 743 tiles (levels 0 to 2 of each COPC octree,
  1.6 m spacing, 13 to 26 MB a tile, 9 GB streamed of the 100 GB dataset), zero failures:
  73,267 buildings resolved (24,751 gables, 3,555 hips, 44,961 measured flats), 12.8% of
  the city's footprints, essentially everything six metres or wider; the narrow rowhouses
  are left unresolved on purpose so a wrong "measured flat" never switches the lottery off.
  Validated against the core's full-resolution pass: heights median 0.00 m off, ridge
  angles median 2.3 degrees, pitched precision 0.78 and recall 0.83; against OSM's tags,
  88% agreement. The far ring now carries 16,639 gables, 2,477 hips and 15,747 known flats;
  the outer districts 7,958 forms. Repacked and deployed.

### Mapillary wall colours (Sep 2)

- Mike registered the Philly3D application on Mapillary and passed the client token; it
  lives only in `MAPILLARY_TOKEN` for the run (never in a file, the log or
  `provenance.jsonl`, and the log is grepped for `MLY|` after every run).
- The Graph API bbox search that `fetch_mapillary.py` was written against is unusable
  here: the third tile of the wide box answered HTTP 500 "Please reduce the amount of
  data you're asking for" on every retry, and so did its quarters down to 150 m, and so
  did `fields=id&limit=10` over the whole tile, while a 33 m box inside it answered an
  empty list. Two tiles worked, the rest of the neighbourhood did not. The listing was
  rewritten on the z14 vector tiles (`tiles.mapillary.com/maps/vtp/mly1_public/2/14/x/y`,
  Mapbox vector tile protobuf decoded with a 90-line stdlib reader): the "image" layer
  is a point per image with `captured_at`, `compass_angle`, `id` and `is_pano`, one Center
  City tile is 9.9 MB and lists 174k images. Thumbnail URLs then come from the batched
  entity endpoint (`/?ids=...&fields=thumb_256_url`, 50 per call).
- The listing: 31 z14 tiles, 1,098,710 images inside the two boxes, 25,489 panoramas
  dropped, 1,073,221 usable, 40,000 picked (newest per 10 m cell, round-robin across
  tiles), 39,969 thumbnail URLs resolved in 826 s, thumbnails at about ten a second.
- The build side was wired and proven on the dry-run pair before the real bake landed:
  `pack_wide.py` writes `wide_walls.b64` (magic 0x53485457: the sRGB palette, then one
  byte per `wide.b64` building record) from `wall_palette.json` + `wall_colors.json`,
  refusing a dry-run pair; `build.py` inlines it as `WIDE_WALLS_B64` (floor 100 KB);
  "Raising the outer districts" decodes it beside the wide blob, converts the palette
  through `roofInv` like `ROOF_PAL`, and a building the imagery has seen (h <= 45 m,
  type <= 6) takes its block face's colour with the usual per-building jitter;
  `__dbg.walls()` counts them. First attempt put the colour line in `raiseRing` (the
  anchor matched the far ring's palette pick, whose jitter seed differs by one constant),
  which failed the far ring with "WALLS is not defined"; moved to the wide loop, 145 of
  the dry-run buildings coloured, no failed step. `wide.b64` itself is byte-identical
  across the repack.
- The real bake, first cut (the original 35..65 % band, the original sky filter):
  31,643 thumbnails opened, 27,229 with a wall sample, 24,729 block faces coloured, 26,919
  of 111,078 wide buildings (24.2%) and 241 of 6,374 south. The palette was wrong for
  Philadelphia: by face count 51% neutral grey, 19% blue-grey, 30% warm. A contact sheet
  of the thumbnails showed why: they are dashcam frames, the camera at about 1.3 m, so
  the horizon sits mid-frame and the 35..65 % band straddles it, half wall and half the
  parked cars, road haze and car glass below the horizon. A band above the horizon
  (20..50 %) was worse (38% cool): overcast sky and haze are light neutral greys the
  blue-sky rule never catches. The fix is the pixel filter, not the band: drop light
  low-chroma pixels (min channel over 185, spread under 28: overcast, cloud, haze), any
  cool cast on a light or mid pixel (blue over red by 6 at max over 150, by 10 at max
  over 110: skylight on a shaded wall, car glass, distant air), band 35..60 %. On a 2,500
  image sample that turns the sample mix from 49 / 26 / 25 (warm / grey / cool) to
  67 / 24 / 9, and the baked palette to 59 / 32 / 9 by face count: desaturated bricks,
  browns and taupes with a third greys, which is what South and West Philadelphia are.
- Final bake: 21,349 images used, 20,769 block faces, 24,868 wide buildings (22.4%) and
  158 south; `pack_wide.py` carries 24,611 of the 112,808 packed records (the rest are
  parts or dropped by the packer's own filters), and the app applies 24,564 (towers over
  45 m and stadium types keep their palettes). Rendering transfer `wallInv` in the wide
  step, tuned on the South Jessup Street blocks below Passyunk at 1 PM: sRGB to linear, luminance lifted on
  a 0.6 power so a 0.2 photo grey lands at 0.38 (the palLow register), any blue-over-red
  or green-over-both cast folded to a neutral grey of the same luminance (a first draft
  boosted chroma on every colour and turned the greys sage green), and a 1.25 chroma
  return on warm colours only. A face's median is one colour for a whole block, and the
  Point Breeze blocks came out as uniform charcoal rows, so each building takes three
  parts the measured colour to one part its own palette draw, plus a second jitter: the
  face keeps its tone, the houses get their variety back. Page 25.10 MB raw, 10.71 MB gzip.

## Round 49: the ballpark diamond, a facade vocabulary, the Center City towers (Sep 2-3)

Mike: "I would love to see an actual baseball diamond on the field and the scoreboard looks
to be very off kilter", "really overhaul the center city skyscrapers ... varied building
styles", "for the rest of the city, can we add more building styles that dont all look
identical? Can you use the mapillary data to inform some other styles?"

- Citizens Bank Park: the field decal is now a diamond at MLB geometry from the home plate
  the research placed: 90 ft bases, the rubber 60 ft 6 in out, the infield skin cut by the
  95 ft arc about the rubber, the grass square inside the base paths, mound and plate
  circles, chalk foul lines to the fence and a 4.5 m warning track along the outfield
  wall (the `inner` ring's sector in front of home). The board was an axis-aligned slab
  standing on the outfield grass; it now sits on the left-field stands where the ray from
  home plate through the research point leaves the bowl, square to the sightline, a dark
  frame with the housing proud of it and the lit face toward the plate.
- The facade vocabulary grew from 9 styles to 19 (the `aStyle` word, see `fabricStyle` in
  app.js): 9 Victorian row (segmental-arched heads, dentil cornice), 10 porch front (a
  recessed dark porch band with posts and a trim roof line, paired sashes above), 11
  siding or formstone (lap lines, no lintels), 12 industrial loft (nine-pane sashes on a
  4.2 m bay, loading doors), 13 new construction (wide dark-framed windows, a floor line in
  shadow), and five tower archetypes: 14 stone piers, 15 horizontal bands, 16 precast grid,
  17 pre-war stone (paired narrow sashes, a shadow band every eight floors), 18 residential
  slab (window band and balcony line). The word also carries a variant in its top bits:
  dark trim and tall sashes. The reflective curtain wall (`outerGlassMat`) reads a variant
  the same way: 21 silver spandrel bands, 22 dark glass, 23 a light concrete grid.
- `fabricStyle` replaces `opaStyle` at all three tiers: OPA era and use pick the family
  (pre-1900 Georgian or Victorian, 1900-1935 Victorian or porch front for the larger
  twins, mid-century plain or siding, post-1990 new construction, industrial lofts,
  storefronts and lofts for commercial), a per-building draw spreads it, and churches take
  the arched style and civic buildings the arcaded one. Towers without a researched spec
  take `towerStyle` by era, and `palTall` gained darks, limestone, blue-grey glass and
  brick.
- The imagery informs the fabric: `bake_wall_colors.py` now measures, per block face, the
  fraction of kept pixels that are light (white trim, cornices, formstone, paint) and
  dark (glass, doors), classes them (trim 1/2/3, window 1/2/3) and `pack_wide.py` writes
  a second byte per building into `wide_walls.b64` (header word 4 = 2 bytes per record,
  planar). Over the 25,026 coloured buildings the trim classes split 78 / 19 / 3 %, and
  the light fraction does separate painted and cornice-heavy faces from plain brick
  (the lightest palette entries are 93-100 % class 2-3, the brick reds 0-5 %). In the
  app a trim-3 face wears siding where it would have been a plain row, a trim-2 brick
  face becomes a Victorian with white cornices, a trim-1 face keeps its dark trim, and a
  window-3 face after 1990 reads as new construction.
- The Center City towers: `bake_towers.py` reads `wide_landmarks_research.json` (155 researched
  buildings with massing text, a photographed facade hex and a glass flag) and `wide_names.json`
  and writes `towers.json`, 113 specs joined to the wide footprints name-first (IDF-weighted
  tokens, 55 of the 77 research towers), then by a scored position match (the research's
  "calibrated grid" drifts against the real 9.5 degree grid), 112 joined, one unmatched (1001
  South Broad, still construction in OSM). Each spec carries a facade archetype
  (concrete_grid 29, glass 26, deco 25, brick 11, glass_bands 8, stone_piers 6, glass_dark 4, precast_bands 4), a crown
  (flat 86, notch 8, spire 7, dome 3, lantern 2, custom 2, lattice 1, ziggurat 1, sloped 1, pyramid 1, mansard 1) and a night accent. In the wide loop a
  building over 45 m takes the nearest spec within 35 m: its hex through `wallInv` for the
  masonry archetypes, straight for the glass ones (the research hexes already sit where the
  hand tints did), the archetype's style, and for the glass archetypes the reflective curtain
  wall with the band variant. A crowned tower's body stops short of the researched height and
  the crown kit raises the last metres after the loop (it must run before the chunks upload:
  the first placement, after the glass upload, wrote into freed buffers and failed the whole
  step): rectangle pyramids and frusta over the footprint's oriented box, an open lattice of
  bars for BNY Mellon, stepped tiers that keep the facade for Three Logan, lit lanterns for
  the Comcast Technology Center and One South Broad, part-plan notches, masts and the PSFS
  sign. 52 crowns raised. Page 25.31 MB raw, 10.73 MB gzip.

- Mike's morning look: "there is no red skyscraper in philly", the reflective glass "no
  good", "I hardly see a change", and flickering (the Man Full of Trouble tavern, a building
  low-left of his Market West shot). Fixes: a `towerInv` transfer for the masonry tower hexes
  (linear, a 0.8-power lift, chroma pulled to 0.62; Three Logan Square's granite goes from
  orange to the muted red-brown it is), the glass tints at 0.66 with the reflective material
  at metalness 0.7, roughness 0.12, envMap 1.15 (it mirrored the overcast sky into white
  slabs), a vertical sky gradient on the curtain wall, stronger spandrel and mullion contrast,
  and above all a slower detail fade for the tower styles and the curtain wall: the rowhouse
  fade ended at about 900 m, which is nearer than most skyline vantages, so every tower
  read as its flat far average. Floor bands and window strips now hold to about 3 km.
  Flat-topped towers over 60 m get a mechanical penthouse (a third of the plan, set toward
  one end, darker) and a third of them a mast, so the boxes stop being sheer boxes.
- Flicker: the tavern was built twice (a generic `classic()` gable model and the detailed
  gambrel model on one footprint); the generic one is gone. `pack_wide.py` now drops
  stacked building:part ways on one footprint (centroids within 2.5 m, areas within 20 %,
  overlapping height ranges keep only the tallest): 56 parts, the Comcast Technology
  Center's nine coincident prisms among them, 46 groups in all. The far ring and the
  outskirts had none. Before-and-after captures of nine matched views were rendered
  offscreen at 1280 x 720 from the previous deployed page and this one (a small POST
  server in the scratchpad saves what the page posts) and sent to Mike.

- Mike, later: still flicker on some buildings (a speckled two-thirds of a banded tower), and
  "the Schuylkill river is still all out of whack". The speckle was two walls on one plane
  facing the same way: a building:part sharing its street face with the outline it sits
  in, a wing flush with the tower, neighbouring outlines drawn over each other; 98 such
  pairs in the wide tier, 63 on towers. `pack_wide.py` now finds them (parallel, same
  outward normal, within 0.12 m, overlapping along the wall by over a metre and in height)
  and insets the smaller record 0.4 m, a chain 0.4 m more per link, in passes until none
  is left: 110 records inset, 3 pairs left. The first try at 0.18 m lost half its work to
  the packer's 0.2 m grid. The river: the hand polyline the carve followed wandered up to
  500 m off the water through the park, and no tier carried the riverbank north of the
  dam. `bake_schuylkill.py` pulls the OSM waterway=river ways named Schuylkill from
  Overpass (145 fragments, side channels included), `schuylkillCut` and `riverCorridor`
  follow every fragment, and their 65 m buffer united and clipped to the dam-to-East-Falls
  reach is the water sheet (`schuylkill.json`, 83 ha, two island holes), drawn a hand
  below the tiers' own sheets. The river now runs from East Falls to the dam where it is.

- Mike: "the river still has very pixelated spots", and "make the water look like the water
  in Cities Skylines". The staircase was the 25 m ground grid surfacing through the sheet:
  the carve followed the centreline at 60 to 95 m while the sheet followed the outline, and
  wherever a bank was steep (Lemon Hill, the Schuylkill Banks south of the dam, where there
  was no carve at all) the grid's interpolated surface crossed the water plane in steps.
  `bake_schuylkill.py` now also fetches the natural=water river multipolygons around the
  waterway (six faces, 1,304 ha with the 60 m ribbon filling gaps, two island holes) and
  the app carves to that outline: a 10 m scanline raster says inside or outside, a 20 m
  edge grid gives the distance and the side near the edge; inside goes to the bed, and
  within 40 m outside a bank ramps down to a hand above the water, so the crossing sits at
  the outline. Both ground builders and the park drapes call the one `riverCarve`, the
  corridor test reads the raster, and the whole modelled river is drawn from the outline
  (the tiers' own sheets sit 5 cm above and win where they exist). Water: COLORS.water to a
  blue-green, riverMat and the Delaware's waterMat to roughness 0.3, metalness 0.15,
  envMap 0.55 (cuts at 0.2 / 0.32 / 1.15 and 0.27 / 0.22 / 0.78 both turned the Delaware into
  a pale sheet at a grazing angle: the sky's horizon is bright and the river is wide), waves at amplitude 1.0 and speed 0.8, a fresnel term in `liquify` that
  mixes 0.38 toward a sky blue at grazing angles, and the sky's reflection itself tinted
  blue and dimmed to 0.62 in `lights_fragment_end` (the pale sheet was the horizon coming
  back untinted) and leaves deep water under the eye, the look of the
  game's water without its translucency (the bed under our sheets is a flat plane).

- Mike: "Do whatever you need to do to make it look more like cities skylines." The game's
  water shows its depth: shallows lighten and green toward the bank, a band of foam rides
  the shoreline, the surface is calmer under the bank. Ours had one flat colour because the
  sheets were earcut polygons with vertices only on the outline. `flatShorePoly` now builds
  every water sheet (the baked Schuylkill outline, both packed tiers' water polygons) as
  earcut plus two or one levels of triangle splitting, and writes each vertex's distance to
  the nearest edge (a 30 m grid of the outline's edges) into a fourth colour channel, 0 at
  the bank to 1 at 60 m; `mergeWater` merges the sheets with a four-channel colour, which
  makes r149 define USE_COLOR_ALPHA so `liquify` reads `vColor.a`: the colour mixes from a
  lighter, greener shallow to a deeper channel over the first 25 m, animated foam takes the
  first 6 m, the wave normals fall to half under the bank, and `diffuseColor.a` is reset so
  the alpha never reaches the blend. The tiers' own Schuylkill pieces yield to the baked
  sheet (centroid inside the outline) so the foam is not hidden under a deep-water copy 5
  cm above. The Delaware's core sheet carries no alpha and stays deep (its edge is the
  bulkhead). Still not the game: no translucency (the bed is a flat plane) and no reflected
  buildings (no planar pass).

- Mike, with a Reddit clip of a three.js Cities: Skylines clone: "I want the water to look
  like that. Remove the foam though, that looks really broken on our site." The clip's water
  is a deep saturated teal with dense fine wavelets and glints across the whole surface, and
  shallows where the bottom shows through, no foam band. Changes in `liquify` and the two
  water materials: the foam is gone; the shallows mix toward a sand-and-silt bottom colour
  over the first twenty metres of shore distance instead (a lighter teal wash between); a
  value-noise wavelet field (two scrolling layers at 2.4 m and 1.15 m, slopes by finite
  differences, each faded out before its pixel footprint could alias) joins the normal, and
  the long sine swells step back to about half so the texture comes from noise rather than
  parallel crests (they read as stripes on the Delaware); the large-scale colour banding
  drops to a third; the glitter lobes widen; the body colour deepens twice and the mirror
  drops (envMap 0.4, fresnel 0.2, the sky reflection at half) because under our sky and
  ACES a wide sheet went pale at every earlier setting.

- Mike: "I am still seeing foam remnants in places" (a pale band along the Penn's Landing
  bulkhead). It was the shallows gradient landing on edges that are not shores: the seam
  between two adjacent water polygons, a tier's clip edge, a bulkhead. `flatShorePoly` now
  counts an edge as shore only where the ground 4 m outside it stands above the water
  (`siteY` against TERRAIN.water + 0.4, the outward side from the ring's winding, flipped for
  holes), so seams and quays carry no shore distance, and the shallows themselves are a
  quiet teal lightening of about a fifth over the first twenty-five metres, no bottom colour.

## Round 50: the game's look for the buildings (Sep 3)

Mike: "Can we make the building styles identical to cities skylines?" then "Do it". Identical is
out (their models and textures are copyrighted, and the model is built from the real
footprints), so the round borrows what gives the game its look, in the order that shows most.

- The grade: more ambient fill and a little less sun, a touch more exposure. The first cut
  (hemi 0.14 + 0.68 dayF, sun 1.42, exposure 0.96 + 0.16 dayF) bleached the light walls to
  white and flattened the shading, and a second at 0.12 + 0.56 / 1.52 / 0.94 + 0.12 was still
  pale; settled at hemi 0.12 + 0.50 dayF (was 0.10 + 0.45), sun 1.56 (was 1.7), exposure
  0.93 + 0.10 dayF (was 0.95 + 0.11), the day sky fill 0xdde7f2 and ground fill 0x9c8e74, and
  the saturation instead of the brightness: every facade and roof through `cityMat` gains a
  fifth of chroma at the top of the colour block, and the Mapillary warm chroma goes to 1.6.
  Before-and-after captures of seven matched views went to Mike.
- Palettes brighter and more saturated across the tiers: `palLow` gains painted pastels
  (cream, pale blue, sage, pale yellow) beside brighter bricks, `palCom` and `palInd` lift,
  the OPA pools and the core's `buildingPalette` are scaled 1.14 / 1.09 / 1.05 per channel,
  and the Mapillary transfer lifts on a 0.56 power with warm chroma 1.4. Flat roofs without a
  measured colour take the wall at 0.72 instead of 0.93: a membrane, not a pale slab.
- Rooftop clutter (`roofClutter`, desktop only): a parapet lip round roofs over 400 m2 (the
  footprint as a wall with its 0.35 m inset as the hole), HVAC boxes in a loose row along the
  long axis (one per 450 m2, up to four), a stair bulkhead on buildings over 10 m and 350 m2,
  a water tank on a quarter of the pre-1935 commercial and industrial roofs, a chimney on a
  third of the flat rowhouses. The outer districts get all of it, the far ring boxes on
  roofs over 600 m2 only (its wall builder takes no holes), the core none yet.
- The facade shader: windows sit back in the wall (a shadow under the head, 0.38 deep over
  the top 0.3 m), frames heavier (0.22 / 0.2 instead of 0.16 / 0.14), and every storefront
  bay wears an awning at 3.45 m in red, green, blue or cream by the bay's hash.

- Mike, with a photo of a sunlit glass-and-stone skyline: "I dont think you are getting
  me... I want a full rework of building styles. I also want the sky and lighting to take
  it's cues from the Cities Skylines 2 style." Three things, none of them a nudge:
  - Every window in the city reflects. `cityMat` now sets roughness 0.16 and metalness
    0.8 per fragment where the facade chain found glass (`shtGlass`, hooked into
    `roughnessmap_fragment` and `metalnessmap_fragment`), with envMapIntensity 0.9 (was
    0.25), so the sky, the sun and the PMREM skyline come back in the window grids while
    the walls stay matte. The glass takes a tint per building (blue, teal, bronze, grey,
    green on the tower styles, a dark blue-grey on the rows) from a 28 m hash of the
    wall's position, and the lit variation rides on top.
  - Windows sit in the wall: `revealShade` reads the sun (uSunW, the live sunDir) against
    the wall's tangent and normal and throws the jamb's shadow onto the glass on the sun's
    side and the head's shadow under the top, deeper the higher the sun and the more the
    wall faces it, with a faint ambient rim; applied in the rowhouse family, the curtain
    grid and the precast grid. Walls also darken over their bottom 5 m (ground contact).
  - The sky: zenith 0x2d68c8 and horizon 0xc2d8ee (deeper, more saturated), a 0.6 gradient
    exponent, a wider warm glow round the sun, cumulus from a four-octave fbm on the sky
    plane with a second sample toward the sun lighting the tops and shading the bases and
    the thick cores a shade darker, cover still from the live weather. The haze goes blue
    (0xcdd8e6, was sand) and the fog to 1700..6200 m for the game's clear air. Lighting:
    sun 1.82, hemi 0.10 + 0.40 dayF, exposure 0.94 + 0.11 dayF, sun colour 0xffe5b8: a
    stronger key and less fill, the contrast in his photo.

- Mike: "THIS NEEDS A DEEP REWORK" with a list: the foam still showing, the fog, the water
  "nothing like" the game's, the buildings' textures, the ground. Done in one pass:
  - Water: the sum of sines is gone (from height it read as diagonal stripes across the
    Delaware); the surface is five octaves of value-noise slope in wind-aligned coordinates
    (34, 15, 6.5, 2.6 and 1.2 m), crests shortened across the wind, each octave scrolling
    at its own pace and fading before its footprint aliases; no colour banding from the
    crests; no shore tint of any kind (the last lightening read as foam on the Camden
    bank), only the wave damping under the bank; roughness 0.15, metalness 0.12, envMap 0.7
    with the sky reflection still tinted blue.
  - Fog: clear air runs 5 to 16 km now (was 1.7 to 6.2), weather still shrinks it.
  - Facades: the wall between the windows has a material within about sixty metres: brick
    courses (75 mm, joints staggered 110 mm, mortar lighter, a colour per brick) where the
    wall is brickish, stone coursing (0.55 m, joints staggered 0.6 m) on the masonry towers
    and civic fronts, panel seams every 3.3 m by 3.0 m on the precast and curtain grids, a
    mottle on stucco and paint; a 4 m weathering blotch at every range; gravel mottle on
    every up-facing city surface. Shader only, no new geometry.
  - Ground: parks, lawns, roads, decks, plazas and the overpasses take `surfTexPatch`:
    three scales of world-space noise, blotches, tufts and blades on anything green, a
    quiet mottle and speckle on the greys, the finer scales fading with their footprint.
    The bare ground already had its own mottle (`wxGroundPatch`).

## Round 51: the nature pass, the game's ground, trees, clouds, lighting and moving water (Sep 3)

Mike, with a Reddit link (r/ClaudeCode, "build me Cities: Skylines in three.js"): the water
"needs movement", and the grassy ground, the tree models, the clouds and the lighting should
look like that post's. The post was reached this time (its `.rss` feed answers where the HTML
and `r.jina.ai` are Cloudflare-403'd; the video came down as the CMAF stream and was framed
with a Swift AVAssetImageGenerator script, ffmpeg not being installed): the earlier report
that it was unreachable was wrong. Its look is the game's own, stylised: olive meadows, soft
rounded low-poly canopies in groves, a lit cumulus deck with cast shadows, deep blue water,
warm lamps that bloom after dark. The round ran across two sessions (the first was cut off
with a handoff in its scratch directory and the milky river open) and was reviewed by a
workflow (four lenses over the diff, two skeptics per finding; four art-direction lenses
against the reference frames, measured with PIL, and one synthesis).

- The post pipeline (`POST`, `postInit`, `renderPost`, desktop WebGL2 with
  `EXT_color_buffer_float`; `?bloom=0` turns it off). The frame is drawn into a half-float
  4x multisampled target and finished by a composite pass that does exposure + ACES + sRGB by
  hand (`ACES_GLSL`, r149's exact RRT/ODT constants) with a bright-pass bloom (threshold 1.25,
  strength 0.45, two quarter-res separable blurs): the sun disc, the water's glitter and the
  white cloud rims glow. Hard-won:
  - The renderer runs with `NoToneMapping` while the pipeline owns the frame. r149 forces
    LinearEncoding on a render-target pass but still applies `renderer.toneMapping` to every
    toneMapped material, so the first cut mapped the scene twice (once into the target, once
    in the composite) and the river read milky, (182,205,210) at the probe pixel against the
    direct path's (157,197,209); the fix put it back to (161,201,212). The dome and the cloud
    deck hand the composite the pre-image of their raw colour (`pUndo`, the algebraic inverse),
    which stays right under a linear target; the `toneMapped: false` materials (the street
    and tower light points, the car lights, the stadium floods and halos, the flight and ship
    pins, the neighbourhood atlas) hand it the pre-image without the sRGB decode (`pUndoLin`,
    `postRaw`), since the renderer used to encode them.
  - Additive lights saturate instead of summing (`postRaw` swaps AdditiveBlending for MAX
    blending, premultiplied so the opacity fade still works). The 8-bit canvas clamped a
    thousand fogged far lamps at white; the float target summed them past it into a solid
    white band on the night horizon that the bloom then spread. Neither a 2.4 threshold nor the
    shorter night fog touched it; the blend equation did.
  - The canvas skips the browser's multisampled backbuffer when the pipeline will own the
    frame (probed on a throwaway WebGL2 context before the real one exists), the target has
    `stencilBuffer: true` (r149 gives a depth-only target a 16-bit depth renderbuffer; depth
    with stencil is DEPTH24_STENCIL8, the 24 bits the layered flats need), and `perf()` reports
    the scene pass (`renderer.info` resets per pass, the old readout counted the composite quad:
    1 call, 2 triangles).
  - A wrapped `onBeforeCompile` needs a `customProgramCacheKey`: r149 keys programs on the
    hook's `toString()`, so two closures with the same source share one program (the first
    live water experiment's tint stuck through four "variants").
- Water. The body colour is 0x07297b and `liquify` damps the Lambert terms (direct diffuse
  0.25, indirect 0.5): the stored teal was a lit floor, at noon lifted to a pale cyan from every
  height and by every lever (env 0.7 to 0.35 moved the probe 15 counts), where the game's water
  is a body colour at any sun height with the reflection and the glints on top. Reflection tint
  vec3(0.30, 0.52, 0.95) x 0.45, env 0.7. The mid-river probe reads (81,129,182) at noon from
  40 m (the reference sea about (40,110,180)); the core sheet and the outer sheet agree. The
  movement: the top octaves scroll faster and two mid octaves domain-warp in time, so the
  pattern changes rather than slides.
- Ground. `paintGrassTex` paints a tileable 1024 meadow (a noise base drying to olive and
  thinning to dirt, a clumpy mottle, stroke grain, tufts, flower specks), sampled at 6.5 m
  with a 20 degree rotated 11.3 m copy (the period) and a rotated 47 m macro copy normalised
  by the tile's mean luminance, tinted by the flat's own colour (`surfTexPatch`,
  `texU.uGrass`). The first cut was lime: the critique measured the reference meadows at hue
  66 to 77 degrees and a luminance spread of 12 to 28 against our 100 degrees and 51 to 73, so
  the base went olive, rgb(54,72,26) drying to (88,92,38), the strokes to W^2/32 at 0.74..0.9
  and 1.08..1.3 lum and alpha 0.55, the tuft strokes onto the base hue, the flowers to W^2/16000
  and muted. The tuft field (`grassInit`, `grassSow`, `grassStep`, `grassUpdate`): an
  InstancedMesh of crossed alpha-cut cards wearing `paintTuftTex` (14 blades in a 1.6 rad
  fan, 0.007..0.017 W wide, lighter than the ground from foot (72,88,38) to tip (156,162,88); a
  first cut's 24 wide blades read as agaves), uploaded as a DataTexture with the clear texels
  filled with blade green (a canvas premultiplies them to black and the mips bled it, so every
  tuft was a dark speck from height), 28k on desktop and 9k on touch within 160 m of the
  camera, 0.16..0.36 m tall, thinning out from 10 to 45 m above and toward the rim, re-sown
  when the camera moves 70 m at 5,000 tries a frame, swaying on the water clock, cloud shaded.
- Trees. The crowns are lumpy flat-shaded blobs: every vertex of the unit icosahedron steps
  0.79..1.21 by a hash of its position seeded per tree, and a three-octave mottle breaks each
  facet into clusters, so a crown is a low-poly puff that catches the sun instead of a smooth
  ball; matte (roughness 1, env 0.25: the sky's sheen read as a second object). Leaf cards on
  desktop: 32 on the core's crowns, 14 on the wide tier's and on the vases, pyramids and conifer
  spires, each a random-facing alpha-cut quad of 0.42..0.56 crown units on a shell at 0.42..0.6,
  wearing `paintLeafTex` (a 0.55 R backing disc, the outer half leaves over holes, a bright heart
  and a dark rim so the light has no side); lit on the crown's own normal without the
  DoubleSide flip (half the cards had shown their dark backs, a salt-and-pepper the critique
  traced to r149's `faceDirection`); a lit-top, dark-underside gradient on cards and core.
  One colour path: `cardTint` (the species HSL normalised on green, eased 0.30 to white) on the
  cards, and the core and its two lumps at the same tint times the sprite's mean
  (`texU.leafNorm`) x 0.06, so a ginkgo is one yellow object. The core is 0.7 of the crown. The
  wide tier's second lobe is dropped (3.2M triangles a frame; the displacement gives every
  crown its asymmetry): the high view fell from 14.1M to about 10M triangles. Trunks store
  0x2b2119 (0x5b4a38 read as cream under the legacy lift).
- Clouds and light. `cloudMat`, a 64 km plane at 1,900 m that follows the camera, carries the
  same fbm the ground shadows use, lit by a second sample toward the sun (rims where a puff thins
  toward the light, grey bellies, warmed by the sun's colour, dimmed by the sky's cloud light),
  edges 0.20 / 0.40 and rim gain 6.0 after the critique (the first cut was streaky stratus),
  an HDR rim of +0.15 for the bloom, hazed out past 14..26 km; the dome's own cumulus is kept
  to the horizon band. Cloud shadows slant by the sun (`uCloudSlant`, sunDir.xz x 1900 /
  sunDir.y) at 0.45 x 0.85 dayF (was 0.62). Sun 2.0, hemi 0.10 + 0.36 dayF (from 1.82 and
  0.40); the critique's 3:1 key-to-fill and paler sky band were declined, Mike's Round 50 key
  and deep-blue sky stand. Night air is shorter (fog near and far x (1 - 0.5 night) and
  (1 - 0.42 night)) and lit windows dim 45 % between 1.5 and 7 km, so the far city sinks into
  the sky instead of massing white on the horizon.
- Wind: the canopy material sways per tree with a small flutter; the wide tier's crowns are an
  80-face icosahedron; every crown's saturation rises 15 %.
- Verified in the pane: the seven canonical views at noon, overcast and night, the water at 40
  and 420 m, Rittenhouse and Washington Squares at eye level and from above, dusk; no build step
  failed, no console errors beyond the known CORS line for the SEPTA relay off-origin.
  Triangles 10..11.6M and 230..310 calls at the standard views (the pane's frame timing is not
  trustworthy: no rAF, and gl.finish returns before the GPU process). Before-and-after sheets of
  the seven views went to Mike.
- The review's last confirmed findings, closed after the first deploy in a final pass: the cloud
  deck's `gl_FragColor.a *= 0.5` (meant for the bloom mask) halved its colour blend too, so the
  deck was half transparent under post (the streaky stratus of the first cut; the coverage is the
  mask now); the rain and snow shaders write display colour and take the pre-image like the dome;
  the fog colour goes into the linear target as its pre-image (`pUndoColor`, the inverse ACES in
  JS) and the deck fogs after its own pre-image, so the far haze meets the horizon again instead
  of coming out of the composite darker; the bright pass sees linear light, so its threshold is
  1.25 + 1.2 dayF (2.45 by day, when a sunlit wall or snow sits near 2, 1.25 by night for the
  lamps and windows); the veil's upload renders draw into the float target so every program
  compiles once, in the post variant; the tuft sow skips from 90 m up (every tuft was rejected
  there anyway) and is time-boxed at 2.5 ms a frame. And one structural water bug the synthesis
  found: `liquify` mixed the world-space wave normal into r149's view-space PBR normal, so the
  sheet's shading turned with the camera; it goes in through `mat3(viewMatrix)` now (the glint
  and fresnel keep their own world-space math), the probe pixel (61,117,177).
- Left open: procedural textures, never the game's assets; no SSAO (the crowns' gradient and
  the wall-base darkening are the contact cues); reflections are the env-map probe, not planar;
  the critique's remaining proposals (a chroma macro on the meadow, edge-on card fading, HDR
  lamp cores with a night bloom threshold, a lifted night palette, ico(0) crowns with distance
  gating on the wide tier, samples 2 on the float target above DPR 1.25) wait on Mike.

## Round 52: the game's ground, lane paint, dark lots, the conformant drape, the pins (Sep 3)

Mike, with a CS2 frame and three of ours: make all the ground look like the game's (the light
ground cover darker, the light green areas exactly like the park grass), lines on the roads,
the parking lots a bit darker, and the terrain still clipped through the lots and other flats.
Later, with a dusk screenshot: the pins had a glow that flickered. The round ran as a spec
reviewed by three lenses before any code (34 findings, two blockers: a `force` parameter that
would have received r149's renderer, and a mottle that lived only on the bare ground), three
worktree agents on disjoint packages, a merge, captures, tuning, then a review workflow over
the diff with two skeptics per finding.

- **The ground is the meadow.** `COLORS.ground` is 0x223418, a hair under the park's 0x243818,
  and every bare-earth material (the core heightfield and shelf, the wide strips, the far strips
  and the 60 km apron, the NW hills, the overpass collars) is a `groundSurfMat`: `surfTexPatch`
  with the meadow forced (`opt === true`, never truthiness, since r149 hands the renderer as the
  second argument), one material per tier with no `clone()` (r149's copy drops the hooks). The
  game's darker blotches are one mottle in the meadow branch shared by ground, parks and lawns
  (`gtn1..3`, dark floor vec3(0.60, 0.66, 0.50) at 83 m and 22 m, a fine grain at 2.9 m, never
  lighter than the base); the old pale `wxGroundPatch` and the per-frame ground retint are gone
  (the ground was retinted because the pale sage read as water at dusk; the olive does not). The
  per-polygon park shade is flat (`PARK_SHADE_SPREAD` 0) so no park polygon shows as a patch;
  the NW woodland tint keys on `WOODLAND` 0x1b2c12.
- **The weather pass came back.** Round 51's `surfMat` hook was an own property, so the hookup
  at the end of build() skipped every park, road, lot and deck: snow and wet never reached them
  (confirmed: snow forced to 1.0 whitened roofs and bare ground only). `cloudShadowPatch` is
  idempotent, `surfMat` and `groundSurfMat` flag `userData.wxSurf`, and the hookup wraps those
  (`wxSurfacePatch` first, then the material's own chain, re-keyed on the wrapped hook per
  gotcha 15) so the snow lands over the meadow and the paint. The comment that said the hookup
  ran before the first render was wrong: `flushUploads` compiles everything behind the veil and
  the hooks land through the first frame's `refreshEnv` refetch.
- **Lane paint.** Every road ribbon carries `aLane` = (signed across-distance, distance along,
  half width, class); `lanePatch` paints in the fragment shader: a double yellow centre on
  two-way streets from 6.5 m wide (Philadelphia's one-way streets get one too, the game's look
  over accuracy, oneway is not in the data), white dashes (3 m on, 6 m off) at `round(hw / 3.3)`
  lanes a side, on the divided highways (motorway/trunk, tier classes 0 and 1) lanes across the
  width at 3.7 m with solid edge lines and no yellow, nothing on service, footway and pedestrian
  ways (core regexes; tiers t == 6 or w < 5.5). The paint is 0.16 m wide (wider than life, the
  game's are), never thinner than a pixel with a coverage-preserving gain floored at 0.55, dashes
  to their mean past aliasing (keyed on the along-road derivative), gone past 2.4 m a pixel. The
  first cut read bare from 150 m up: its anti-aliasing ramp lay inside the line and ate a pixel
  of it; `lnLine` centres the ramp on the edge. The joint fans drop 2 cm below their strips so the
  strips win the paint at every bend (a raised fan would poke through crossing streets). The
  tiers stage the attribute in a growable Float32Array; the far ring skips it on phones. Three
  road materials only (`roadMat`): core asphalt, wide rc, far rc. Fans on a grade still kink the
  paint a little at bends below 80 m: accepted.
- **The clipping, for good.** `drapedPoly` caps its interior points at about 420
  (`sqrt(area / 420)`), so the 559,000 m2 Navy Yard lot was draped at 36 m and the 1.55 km2 fill
  sheet at 61 m against a 25 m ground mesh, and every sheet sampled the DEM's bilinear read
  while the mesh is linear on its own triangles: two reads of one surface half a metre apart.
  Now the ground meshes register their own vertex heights and normals as they are built
  (`groundGrids`, the NW patch searched before the north far strip, skipped and hole cells
  return null), `groundMeshY` reads the drawn ground exactly, and `conformDrape` lays a polygon
  on it per grid row: whole cells are the ground's own two triangles, boundary cells are clipped
  to the cell and split by the diagonal and earcut forward on (x, -z), slivers and off-piece
  centroids dropped, the overhang past every grid (Fairmount past the wide box) on `drapedPoly`.
  The wide parks, the far ring's parks and aprons (collected in `raiseRing`, built in
  `uploadRing` once the far ground exists; the far ring used to perimeter-drape 777 parks under
  40,000 m2), the sports complex's fill sheets and lots all ride it; nested rings lift by area so
  nothing is coplanar; the wide streets read the drawn ground where it is land
  (`groundMeshLandY`, the bridge logic keeps `siteY` over water) and densify at 6 m through the
  lot sheets; the stall stripes follow the ground per 3 m sample. 2,050 polygons, 118k
  triangles, about 1.1 s in the hidden pane. The far ring's streets keep `siteY` (the far grids
  do not exist when `raiseRing` paves): open.
- **Lots.** Stored-dark 0x0e0d0c over a 0x0b0b0a sheet (about 114 displayed against the
  streets' 200; the first cut at 0x23 read 173: the legacy pipeline feeds stored values to the
  shader as linear, not as albedo, and the env map was never the reason they read light). The
  stall stripes fade out between 500 and 1500 m instead of aliasing into moire from altitude.
- **Tufts on the bare ground.** The field sows the meadow outside the core as a second source at
  0.4x the park density (rejecting roads, water, the lots and the parks, which sow themselves);
  there is no footprint test outside the core, a blade at a wall base is accepted.
- **The pins.** Under the post pipeline a flight or ship pin's white frame handed the composite
  a pre-image far above the bright pass's threshold, so every marker wore a bloom halo that
  shimmered as the quarter-res blur resampled it. `postRaw(mat, { mask: true })` (the pins and
  the neighbourhood atlas) blends the colour as before and writes a zero alpha under the sprite,
  which is the bloom mask the bright pass already reads for the cloud deck.
- **The review's confirmed findings, closed** (three lenses over the diff, two skeptics per
  finding, six of eight confirmed): the footprint-gated noise terms in the meadow and the
  neutral mottle faded to zero instead of their mean, so every green went 20 to 26 percent
  darker past 1 to 4 m and 8 to 30 m per pixel, a dark front that moved with the camera (they
  fade to 0.5 now, the far mean equals the near one); PHL's and PNE's runways and taxiways ride
  class 5 in `pack_city` at 45 and 16 m and were painted as seven-lane streets with a double
  yellow (class 5 wider than 10 m is unmarked now); the far ring's roads were paved inside
  `raiseRing` before the far strips existed, so they read the DEM while the parks conformed to
  the mesh and a hillside park could cut through its street (the roads are decoded there and
  paved by `paveRoads` at upload, after the far ground registers); the bare-ground tuft sow knew
  only the Delaware's bank and the lots, so tufts stood in every pond and on the airport aprons
  (one `noSow` keep-off list: the lots, every water ring in both tiers, the far aprons, the NW
  creeks, prefiltered per sow), and bare tufts top out under 0.295, the lowest street lift, so a
  wide street's shoulders outside the 4 m road reject cannot show a blade; and the ground colour
  is the park's exactly (0x243818: the hair of difference was a 6 percent tint step along every
  park outline). Refuted: that the hookup needs an explicit recompile (the first frame's env
  refetch is the mechanism, as documented).
- **Darker still (Mike: "the ground cover is still too light").** A 20 percent darker stored
  green moved the display 7 percent (the tint ratio is clamped and ACES compresses it), so the
  brightness lever is `MEADOW_GAIN` (0.72) on the painted meadow itself in `surfTexPatch`: a
  street-level lawn goes from about (104, 126, 66) to (91, 112, 59) displayed, Washington Square
  from (88, 109, 52) to (70, 89, 45), the game's olive. One number to move again.
- **Buildings darker (Mike: too light beside the darker ground and water).** The fabric was
  overexposed: a sunlit wall sits near 1.5 in linear light and a noon roof near 1.9, deep in the
  ACES shoulder, so a 0.55 gain moved the display under a tenth (brick 220 to 198). `FACADE_GAIN`
  0.22 on the walls and `ROOF_GAIN` 0.14 on anything facing up, applied at the top of the facade
  shader on the fabric material of all three tiers (the lit windows are an emissive term and
  keep their glow): brick walls 220 to 138, cream walls 160 to 143, roofs 189 to 162 at noon,
  the game's mid tones, and the saturation the shoulder had flattened comes back with it.
- **Round 52 coda, from the live site (Mike): Society Hill darker than its neighbours, the
  distant haze, a paler sky than the new ground.** The fabric gain exposed a palette gap the
  shoulder had hidden: the core's brick palette and sampled roofs sit a fifth darker and redder
  than the outer districts' photo-sampled walls (117 against 139 displayed in matched oblique
  views), so the core stood out as a dark block. The core mesh now rides `coreMat`, the same
  facade shader from a `facadeHook(gainWalls, gainRoofs, saturation)` factory at 0.42 / 0.28
  and no saturation boost (the tiers keep 0.22 / 0.14 and 1.2), keyed apart by hand (gotcha
  15) and chained into the weather pass like `cityMat`: 133 against 139 now. The clear air runs
  8 to 40 km by day (was 2.4 to 13 km, a white horizon from any height), the night factors
  keep the night at about 2.8 to 16 km so the far windows do not band the horizon (Round 51's
  finding), weather still shrinks it. The sky is deeper and more saturated: zenith 0x2260c8,
  horizon 0xa6c6ea (the fog takes the horizon colour by day, so the far haze is blue, not
  white), haze 0xb6c9e4.
- **Round 52 coda 2, the paved ground (Mike, with a Google aerial: grass where there is asphalt
  in life).** Every unbuilt surface had become the meadow, the port terminals, the rail yards, the
  industrial lots, the big-box lots and the refineries with it. `fetch_paved.py` pulls the whole
  far-ring box's surface parking (amenity=parking, not the multi-storey, underground or rooftop
  kinds, not the ones that are buildings), rail yards, brownfield and construction land, works and
  aprons from Overpass (16 tiles in `paved_tiles/`, 287 s against overpass-api.de, the only
  mirror answering), and `pack_paved.py` joins them with the land-use extract's industrial,
  commercial and retail polygons into `paved.b64`: int16 whole metres in the model frame, four
  kinds (lots, yards, rail, aprons), each kind's rings unioned so nothing of one kind sits
  coplanar, holes dropped (parks and buildings inside draw above), the core box kept out, 5,779
  rings and 53,584 vertices in 317 KB of base64. The app's new step 'Paving the lots and yards'
  lays every ring on the drawn ground with `conformDrape` (about a second for 5,779 rings, 288k
  triangles in all with the parks) under the parks (0.04 to 0.055 against 0.06), under the
  sports complex sheets and the streets, keeps the tuft sow off them, and colours lots the sports
  lots' asphalt, yards a shade under concrete, rail yards a warm ballast grey. A lot 5 mm over a
  yard shimmered from 500 m: the gap is 1.5 cm. Verified at the port, Columbus Boulevard, the
  Navy Yard, the refinery, the airport and Tacony. What stays green is real: parks, the
  interchange infields, residential blocks (the game's look), and anything OSM has not mapped.
- Verified in the pane at noon, dusk, night and under snow: the sports complex and the Navy Yard
  lot with no ground through them, South Philly and Center City from 600 m, the rowhouse blocks
  from 60 m, a street at eye level (yellow, dashes, tufts), the core lawns and Washington
  Square, the waterfront shelf, the NW hills; 33 tests pass. Before-and-after captures are in the
  session's scratchpad.

## Round 53: the cumulus in depth, a lighter fabric, a hull for every class of ship (Sep 5)

- **The cloud deck marched (Mike: flat and two-dimensional).** Round 51's deck was one plane at
  1,900 m carrying a 2D fbm, lit by a second sample toward the sun: a textured sheet, however it
  was lit. The plane is now only where the eye's ray enters a slab 720 m deep, and `cloudMat`
  marches up through it (`CLOUD_STEPS`: 10 on desktop, 5 on phones, an interleaved-gradient
  start offset at 0.7 of a step, extinction 0.009 per metre of density): the base field is the
  same one the ground shadows read, eroded with height by `hf * (0.06 + 0.40 * hf)` so a puff of
  ordinary density stands about 300 m and only the densest cores reach the top, the columns lean
  0.09 field units per unit height so the sides billow, and each sample is lit by a coarser
  (three-octave) sample toward the sun and a step up the slab (thinner toward the light means
  sunlit; the bellies self-shade at 0.45 of the sky, the tops take all of it). The coarse and fine
  octaves are split (`cfbmL`, `cfbmH`) so the sun-ward difference carries no fine-octave bias.
  Seen from the ground at a slant the puffs show their sides and rounded tops; the horizon band
  reads a solid field, as a cumulus sky does. The camera never rises above the deck (the flight
  ceiling is 1,600 m), so the march has one case. Two things found on the way: the first pass
  divided the rim glow by the alpha AFTER the 14 to 26 km fade, and a divide by the fade's zero put
  NaN, drawn black, in a bowed line along the deck's far edge (gotcha 21: divide by the coverage,
  never by the faded alpha); and a white-noise start offset at eight steps speckled the whole
  deck, so it took the interleaved-gradient pattern, ten steps and a lower extinction. Cost in the
  pane: 2.3 to 2.5 ms per frame at the sky view, within noise.
- **The fabric a quarter lighter (Mike: too dark now).** `FACADE_GAIN` 0.22 to 0.27, `ROOF_GAIN`
  0.14 to 0.17, the core's pair 0.42 / 0.28 to 0.52 / 0.34 (the core-to-tier ratio kept). Measured
  on matched captures, a rowhouse band went 101 to 111 displayed, an oblique Center City band 122
  to 131, the wide view 110 to 120.
- **A hull for every class (Mike: can we tell the type, and use different boats?).** Yes: the
  stream's ShipStaticData and the relay's `type` carry the AIS type code, which the card already
  named. The code is kept on the vessel (`v.tc`) and `SHIP_KIND(type, len)` picks one of seven
  hulls, each its own instanced mesh with `SHIP_CAP` slots and its own height rule (`SHIP_H`):
  the workboat (the old hull, for unknown codes), the container ship (bays of coloured boxes fore
  and aft of the house, three tiers midships), the tanker (long and low, a forecastle, the catwalk
  and manifold, a six-deck house aft), the tug (short and fat, the fender band, the wheelhouse
  forward, a red stack; codes 31, 32, 52), the passenger vessel (white hull, blue band, two window
  decks; 60s and the high-speed 40s), the small craft (pleasure, fishing, pilot, tenders, and
  anything 20 m or under), and the patrol boat in haze grey (35, 51, 55). The picker reads the hit
  mesh's kind, the anchor badges keep one list. `shipTest()` now seeds eight vessels, one of every
  kind. Verified with the test fleet from the water and from 60 m; 34 tests pass.

- **Round 53 coda (Mike, with a photo of the real sky and two screenshots: the deck still looked
  bad, and the installed app opened half blank).** The photo: a half-covered cumulus sky under a thin
  high veil, white tops, cool grey bases, the far clouds flattening into a bright haze. The app under
  the live weather: a tan sheet closing the sky, cut off by a straight line at 26 km with a pale band
  under it. Four causes, four fixes. (1) The deck's far quad was clipped by the camera's 26 km far
  plane, so the 14 to 26 km alpha fade was really an edge: the deck's vertex shader now holds clip z
  inside the frustum (the fragment depth still comes from the log path and saturates at 1, so nearer
  geometry keeps covering it), the plane is 200 km, and the deck thins by elevation over the last
  three degrees above the horizon, where the fog has already made it the haze colour; the dome's own
  cumulus band narrowed to those degrees. (2) Colour: the shade greys were warmed by a 0.35 mix of
  the sun's colour on everything; now the bellies are a cool grey (0.50, 0.55, 0.64, the photo's),
  only the sunlit faces take 0.18 of the sun, and under a full overcast the sheet pales (light comes
  down through it) instead of going leaden. (3) Lighting: the sun-ward sample sat 44 m away, inside
  the coarse field's smallest feature, so every point read mid grey; it now sits 125 m toward the sun
  and a step up the slab, and `lit = 0.55 - 3.5 * (that sample's density excess)`: outside the cloud
  toward the sun means lit, deep means dark, with thin edges glowing through. Flat dark bases and
  bright tops, as in the photo. (4) Cover: Open-Meteo's `cloud_cover` is the total, and a cirrus veil
  over a half-covered sky reports 80 or more; the fetch now asks for the low, mid and high covers and
  the deck takes `max(low, 0.8 mid, 0.45 total)`. Twelve steps on desktop (the ten-step grain still
  showed), the start offset at 0.6 of a step, the bellies' ambient floor 0.62.
- **The installable app.** `build.py` writes `manifest.webmanifest` beside the page (start_url and
  scope `./`, standalone, the ink theme, three icons as data URLs from the new
  `brand/make_pwa_icons.py`), the template links it and carries the Apple web-app metas and
  `viewport-fit=cover`, `sw.js` is a network-only worker registered over https (Chrome and Edge want
  a real fetch handler before they offer Install; nothing is cached because the page is rebuilt
  every deploy), `3d-model/index.html` redirects so `./` resolves on Pages, the HUD's fixed corners
  add the safe-area insets, and the deploy stages the manifest and worker at the site root. The
  half-blank window: the app's window opens at one size and lays out at another, and the resize
  landed during the build, before the listener existed (it was registered after the build steps),
  so the canvas kept its first size while the CSS layout took the new one. `fitView()` now runs on
  `resize`, on `visualViewport` resize, and from every frame that finds the window a different size
  from the one the canvas was last fitted to.

## Round 64: the Moon you can see (Sep 15)

- **Mike: can we add the moon and have it be accurate to location and moon cycle?** The page
  has carried a real Moon since Round 26 (`lunar()`, Schlyter's theory with topocentric
  parallax, the phase from the Sun-Moon elongation, the night light and the moonglade following
  it), and it checks against JPL DE421 through skyfield at six instants across a year (this
  evening's crescent, the Sep 26 full moon, a last quarter, two below-horizon instants and the
  Aug 12 eclipse): within 0.06 degrees in azimuth and elevation and 0.15 percent in illuminated
  fraction. What nobody saw was the disc: drawn at its true half degree it was eight pixels on
  a laptop, and it was switched off whenever the sun stood above about seven degrees below the
  horizon, so a first-quarter afternoon or this week's crescent, which sets soon after dusk,
  never showed. Now: `MOON_SCALE` 2.5 draws the disc at 2.5 times its real angular radius
  (`MOON_R`, the `uMoonR` uniform; one number), which reads as a moon on a phone or a laptop and
  still sits naturally in the sky. The face is the near side's maria as soft, noise-warped
  ellipses (Crisium, Fecunditatis, Tranquillitatis, Serenitatis, Imbrium, Procellarum, Nubium,
  Humorum, Nectaris, Tycho's bright spot) in a frame whose up is celestial north projected onto
  the disc (`uMoonN`) and whose right is the sky's right (`uMoonE`), so Procellarum rides the
  left and Crisium the upper right the way they do over Philadelphia, and the face turns through
  the night with the parallactic angle. The terminator frame (`uMoonU`/`uMoonV`, from the world
  sun and moon vectors) is unchanged. The disc stands by day as well: `uMoonD` (the sun's
  elevation from -7 to 1 degrees) washes it, the dark part vanishing into the sky and the lit
  part standing pale over it; the halo belongs to the night; and it is lost in the sun's glare
  within about ten degrees of the sun (new moon). `__dbg.lunar`, `solar` and `moon()` expose the
  ephemeris. Verified in the pane by capture: tonight's 24 percent crescent low in the south-west
  at dusk, lit on the right; the Sep 26 full moon in the south-east with the maria in their
  places (an enlarged capture due south, north up, matched the naked-eye layout); a first-quarter
  moon pale in the afternoon blue on Sep 19.

## Round 65: the far ring's roofs in their own colours (Sep 15)

- **Mike: can we get back to working on the disparity in building colors from the Mapillary
  data?** The divide Round 57 answered (a darker, redder city past York Street, the outer
  districts' north edge) was still there from any height, so this round measured before it
  touched anything. A per-tier tally on the dev handle (`__dbg.colStats()`: the mean wall
  colour handed to the chunk builder, the roof caps, the styles, the OPA words, the roof forms,
  for the whole tier and for a 700 m band either side of York) showed the walls already equal:
  Round 57's reservoir gives the far ring exactly the outer districts' mean wall colour (0.652,
  0.443, 0.334 against 0.653, 0.445, 0.335). The roofs were not. In the band the far ring's caps
  averaged 0.157 in the app's register against 0.239 next door, though the data files put the
  two sides' per-building roof colours only 10 percent apart (0.206 against 0.228). The cause was
  in `pack_city.py`: it merges each 400 m cell's low rows into strips and handed every strip in
  the cell ONE roof palette index and ONE OPA attribute word, the most common in the whole cell.
  The mode of a palette histogram is dark: the four most frequent bins in North Philadelphia
  are the tar-roof greys (sRGB 85 to 113) while the light roofs scatter across a dozen bins, so
  the cell mode shipped the band's roofs at 0.104, half their measured luminance, and every
  strip in a cell wore one era's facade. Now each merged piece takes the OPA word most common
  among ITS OWN members and, for the roof, the sampled colour of the member whose luminance in
  the app's register (roofInv, the 2.364 power that compresses the darks) is nearest the
  members' mean, so a strip reads like its own houses and the colour is always one a roof in it
  was measured as: the band's caps now tally 0.209 against the 0.206 per-building truth (the
  outer districts' 0.228 beside them is the data's own gap). A first cut snapped the palette
  entry nearest the members' mean sRGB colour and landed at 0.195 in the page, below even a
  per-strip mode in simulation: averaging light and dark roofs in sRGB and snapping to the
  palette leans dark once the power curve is applied. The pack keeps every count
  and byte (180,107 buildings, 10.20 MB), only the attribute and roof words change; the repack
  also adopts `philly_frame.py`, so the far ring stands where the scene does instead of up to
  1.1 m east of it.
- **What the experiments ruled out**, so nobody repeats them: a plain lit material (no facade
  shader) renders the two tiers equal (1.02 and 1.03 north to south), so the geometry, the
  normals, the shadows and the fog are not the divide; live shader bisections on `cityMat`
  (wrapping `onBeforeCompile` under a new `customProgramCacheKey`, a deliberate darkening as the
  control) with the roof branch off, the wall-detail branch off, one style forced for every
  building, floor heights zeroed, and equal wall and roof gains moved the tier ratio by two
  points at most. Uniform overrides (`detFar`, the sun's intensity, `castShadow`) are rewritten
  every frame by `applyLighting` and prove nothing. Region means of a capture mislead too: most
  pixels between the buildings are streets, lots and meadow, so the decisive measure masks the
  facade material with a control render (`diffuseColor.rgb *= 0.3`, a pixel that darkens is a
  building) and compares building pixels alone. On the shipped build they match across York
  within two percent, oblique (0.99) and straight down (0.98), and the ground between them within
  three. What still reads as a darker city past the line is coverage, not colour: the far ring's
  merged strips fill their blocks with roof, so buildings are 62 percent of its pixels against 35
  percent in the outer districts, where the gaps between houses show meadow, lots and lit
  streets; the far ring also has no street trees. That is the page-budget merge (city.b64 is
  39 percent of the page), a geometry decision for another round. The residual 8 percent gap in
  the sampled roof colours themselves (0.209 against 0.228 per building) is part geography and
  part the old KX=85350 frame that sampled the far ring's ortho pixels 1.1 m east of each
  footprint; a `roof_colors.py` rerun from the 7,422 cached tiles would re-cluster the palette
  and re-pack every tier, a round of its own. The proper cure for the WALLS, a Mapillary pass over the far ring, stays open: the
  five-reader map put it at about 352,000 thumbnails (7.5 hours, 3.5 GB) for the fetched boxes,
  a by-way-id LUT and a `city_walls.b64` side blob in the `wide_walls.b64` layout, and it needs
  the MAPILLARY_TOKEN, which this machine does not hold.
- Also: CLAUDE.md said the far ring drew "from the same palette by frequency", the cut Round 57
  reversed; it now says the reservoir. The `wallInv` comment quoted 0.6 and 1.25 where the code
  has said 0.56 and 1.6 since Round 50. `__dbg.colStats()` stays as a dev tally.

## Round 64 coda: smaller, and no dark side (Sep 15)

- **Mike: make the moon a bit smaller, and the dark part of the moon should not be visible.**
  `MOON_SCALE` 2.5 to 2.0 (the disc is now twice its real angular size). The 11 percent
  earthshine that drew the unlit part as a dim grey disc is gone: the disc's blend into the sky
  is weighted by the lit fraction at each fragment (`inD * uMoonI * lit`), so the dark limb is
  sky, by night and by day, and a thin crescent is a clean arc. Verified by capture at four
  moments: tonight's crescent at dusk, the Sep 26 full moon, the Sep 19 afternoon first quarter,
  and a six percent waning crescent before dawn on Oct 8.

## Round 63: the card's link under the lock (Sep 15)

- **Mike: on desktop the FlightAware links cannot be clicked, the tooltip just disappears.** Two
  causes, both in the card. Under pointer lock (the desktop flight controls) there is no cursor:
  the click that meant to land on the link was a canvas pointerup, the crosshair pick found no
  plane at screen centre and closed the card. `cardUnlock()` now releases the lock the moment a
  plane or ship card opens (the way `openGuide` does), the hint reads 'Click the scene to take the
  controls', the link takes a real click and the next click on the scene locks again. Second, the
  plane and ship cards are rebuilt every render (`cardSet` rewrites `innerHTML` whenever a rounded
  altitude or speed changes), and a rewrite between mousedown and mouseup replaced the anchor under
  the pointer, so the browser fired the click on the card instead of the link. `cardHold` (a press
  on the card, cleared on the window's pointerup or pointercancel) and, off touch, a `:hover` on
  the card hold the markup still; the values catch up when the pointer leaves. Verified in the pane:
  a locked crosshair pick of a seeded plane calls `exitPointerLock` once and opens the card with its
  link; with a press on the card a second card's markup does not replace it, and it does on release.

## Round 62: no placards through buildings (Sep 11)

- **Mike: do not show placards through buildings, and remove that item from the how-to.** The
  concert placards and the score bubbles are DOM labels projected onto the screen, so nothing in
  the scene could hide them, and the packed tiers cannot be raycast (gotcha 12). `losClear(x, y,
  z)` samples the ray from the camera to the placard's anchor every 60 m or so against the roof
  grid the build fills (`roofCell`, the tallest roof of each 100 m cell, absolute y) and the
  drawn ground (`groundMeshY`): a cell whose roof, or whose ground, stands above the ray hides the
  label; the camera's first 120 m and the anchor's last 45 m are left out so the block beside the
  camera and the venue's own roof never count, and anything under 150 m away is always clear.
  `scoresRender` and `concertsRender` fold it into their off-screen test, and the pins (the line
  and the ball) are depth-tested now, so a building in front hides them the way it hides the
  transit pins. Coarse by design: a tower's whole 100 m cell blocks the ray, so a placard just
  past a tower's edge can drop a moment early; `__dbg.los(x, y, z)` answers for a point. The
  guide's 'Placards' row (which said they showed through buildings) is gone from both copies.

## Round 61: a page for every aircraft and ship (Sep 11)

- **Mike: add FlightAware links for all the air traffic by flight number, and the same for the
  boats with whatever site that information comes from.** A picked aircraft's card ends with
  "Track AAL1776 on FlightAware" (flightaware.com/live/flight/ plus the ADS-B ident, an airline
  code and number or a tail number; a blank or odd callsign, or a test seed, gets no link). The
  ship positions come from aisstream.io, which has no page per vessel, so a picked ship's card
  ends with "Track MMSI 366999123 on MarineTraffic", the public lookup for an AIS identity
  (marinetraffic.com/en/ais/details/ships/mmsi:). Both open in a new tab, both are `.vlink` in
  the card's limestone. `__dbg.cardFor('flight', hex)` and `cardFor('ship', mmsi)` open a card
  without a canvas pick, for checking.

## Round 60: the guide (Sep 11)

- **Mike: remove the mobile how-to for movement, add a pop-up how-to for first visits that also
  comes back from a question-mark button beside the camera, dot navigation and not scrollable,
  covering everything in the app, the filters, the navigation and every other function, with the
  instructions specific to computers and phones.** `#guide` replaces the touch primer (`#flytips`,
  the card that followed the first touch on a phone; its markup, CSS and code are gone). Eight cards
  built at first open from one table (`GUIDE_SLIDES`: a title and rows of control plus sentence,
  each row in a computer and a phone version, chosen by `isTouch`): welcome and the city line;
  flying (drag, W A S D, E and Q, Shift, scroll and the compass, or the Move pad, the look drag,
  the climb buttons and the sideways gate); the layers panel and its keys; the live city (SEPTA,
  Indego, flights and ships, traffic, streetlights); concerts and games; names and places; time
  and sky; search, Copy Link, the camera, the credits and installing the app. The card is a fixed
  600 by 400 (the screen less a margin on a phone, the type a step down under 460 px tall), the
  cards fade in place, never scroll; dots, Back and Next (Done on the last), the arrow keys, a
  swipe and Escape turn and close it; the dimmed city behind it closes it too. A first visit meets
  it 0.9 s after Enter, `localStorage philly3d.guide` remembers, and the ? button in the bar beside
  the camera (or the ? key) brings it back; the About table lists the key. The hint line under
  the bar still says the two-line version of the controls.
- **The review of the cards (57 agents: the copy against the code, the dialog, the markup and
  CSS; 26 confirmed, one refuted).** Copy: the I key did not open About (it does now, beside ?);
  the bronze historic-district inlays were removed rounds ago (the row and the About table's P
  line say neighborhood names); the tree inventory is the outer districts' (Center City and South
  Philadelphia), not the city's; traffic is PennDOT's counts where the state counts and class
  averages elsewhere; 200,000 lamps, not 203,000; Back and Next, not arrows; the flight limit is
  a little past the city line; a route search follows a bus; a phone's camera opens the share
  sheet; the install paths per platform. Dialog: the first-visit timer yields to a guide already
  opened or dismissed; opening releases the pointer lock (the camera kept flying under the cards
  with no cursor); Tab cycles inside the dialog; the swallowed keys are default-prevented (/ opened
  a find bar); Done carries its own title; the dots are tabs with panels. CSS: my #flytips removal
  had eaten the shared kicker-weight rule (every panel's kicker fell to 500; restored); the card
  heights carry dvh twins and max-height 100 percent; the small-type rule also applies under
  520 px wide; the ? button matches its neighbours' width; the dots are 24 px targets round a 9 px
  disc; the stale comment is gone.

## Round 59: the layers panel wide, the tour gone (Sep 11)

- **Mike, with a phone-width screenshot of the layers panel: make it more horizontal than vertical,
  and remove Tour the City, it does nothing.** The panel is 640 px wide (the viewport less 24 on a
  phone) with the ten layer rows in two columns (`.lgrid`), Reset Layers and Copy Link side by
  side, and the eight 'Take me to' stops in four columns; under 560 px the rows fall to one column
  and the stops to two. The Tour the City button and its footer are gone from the panel and the
  About table's Esc line no longer mentions a tour; the tour code (`tour`, `tourStart`, `stepTour`)
  stays in app.js unreachable behind its null-guarded button, to be removed with the next pass
  through the viewpoints.

## Round 58: one kind of tree (Sep 11)

- **Mike, with a street-level screenshot in the core: most of the tree models seem to have a mix
  of a low-poly and more realistic tree, and it needs fixing.** Round 51's desktop tree was two
  objects: a faceted, lumpy icosahedron crown shrunk to 0.7 under a ring of 32 alpha-cut leaf-card
  quads (14 in the outer districts), and at close range the two read as exactly that, a dark
  blob with sprites poking through it, beside buildings that are clean low-poly boxes. Phones
  always drew the crowns alone. The cards are retired on every device (`CARDS = 0`; the code
  stays, a number above 0 brings them back): the crowns stand at full size in the species colours
  the crown path already carried (`TREE_STYLE`, stored dark for the legacy lift), with the lumpy
  per-vertex displacement, the three-octave mottle, the top-lit and dark-undersided sway shader,
  and the conifers at their card-less lightness; the crowns alone came out lighter and yellower
  than the old mix, and a lightness cut did nothing (the day pipeline flattens albedo lightness,
  the TREE_STYLE note), so the depth comes from the sway shader's top-lit multiplier, a fifth
  darker and greener (0.86, 0.98, 0.76 at the top, 0.40, 0.50, 0.38 below, against the card era's
  1.12, 1.08, 0.92 and 0.52, 0.60, 0.48), with the hue 0.04 toward green. One object per tree, the
  same look at every
  distance and on every device, and the leaf material, its painted sprite and the card
  instancing no longer draw (the cards were a second instanced mesh per chunk). Verified at
  street level and from 90 m before and after; 43 tests pass.

## Round 56 coda: the rooms of one building (Sep 11)

- **Mike: the Foundry is inside the Fillmore, Brooklyn Bowl is on the east side of that same
  building, and tonight's Brooklyn Bowl show was on the Fillmore's placard.** Ticketmaster lists
  the three as venues 40 to 115 m apart, and the page merged any venues within 60 m into one
  placard under the first venue's name, so Brooklyn Bowl's show sat under a Fillmore heading and
  the Foundry, 115 m off, got a placard of its own. A placard is one per building now
  (`CONCERT_MERGE` 130 m), and inside it every venue keeps its own heading with its shows in
  start order beneath, venues ordered by their first show; the image is the first any of them
  carries. The feed itself was right (venue ids `KovZ917AEtU` Brooklyn Bowl, `KovZpZAEkteA` the
  Fillmore, `KovZpZAEktdA` the Foundry); the grouping was the page's. Ticketmaster's Fillmore
  point (39.9658, -75.1347) sits on the same block as the app's own `LANDMARK_H` row for it.
- **And the arena's pin (Mike: it needs to move south-east, over the arena).** Ticketmaster's
  point for the Xfinity Mobile Arena (39.90455, -75.17363) lies 390 m north-west of the
  building, in the park, past the 220 m radius the score venues had; a placard now moves onto
  the nearest score venue within 500 m (the arena, the ballpark or the stadium) and hangs where
  a game's bubble would, so the pin lands on the arena's roof.
- **And the Fillmore's (Mike: move the pin right above that building, it is just off).** The
  group took its first venue's point, Ticketmaster's Foundry point 90 m south-east of the
  building, in the lot. A placard stands at the mean of its venues' points now, and `VENUE_AT`
  puts the three rooms of that building at the building's own packed centroid (839.3, -2224.4),
  the app's `LANDMARK_H` row for it, so the pin drops onto its roof.

## Round 57: the far ring in the outer districts' colours (Sep 11)

- **Mike, with a screenshot from over Francisville: a distinct difference in building colour along
  a divide.** The divide was the outer districts' north edge (York Street, `WIDEB.z0`): inside it
  every low wall takes three parts its Mapillary block-face colour to one part the palette draw
  (Round 48), outside it the far ring and the towns across the line drew their palettes alone, a
  darker, redder city past a straight line. Asked for the buildings outside the sampled area to
  read lighter and closer to those inside. Now the outer districts loop samples the FINAL colour of
  every low building it raises (photographed or not) into a deterministic reservoir of 1,024
  (`WIDE_COLS`, `wideColSample`), and `raiseRing` gives each rowhouse, apartment, church and shop
  under 45 m a colour drawn from it by the building's hash, so the far ring carries exactly the
  outer districts' distribution of wall colours, only not tied to the specific block. Two cuts on
  the way: every far building blended toward a Mapillary palette colour drawn by frequency, which
  turned the whole north tan (the outer districts' look is the MIX of photographed and plain walls,
  and the far ring's plain walls come from the same OPA class pools, yet still read redder); then
  the same share of far buildings as the photographed share, still redder than the tier beside it.
  The reservoir matches by construction. The proper cure (a Mapillary pass over the whole city)
  stays open. Verified from the same viewpoint before and after; 43 tests pass.

## Round 56: concerts over their venues (Sep 11)

- **Mike: use the Ticketmaster Discovery API and display concerts like the sports scores on a
  placard, visible from 9 am the day of the show, pinned to its location.** Same shape as the
  scores, with the key kept off the page. `ops/concerts_bake.py` (stdlib, modelled on the SEPTA
  baker: atomic writer, the .gz twin first, the previous file kept on any bad answer) asks the
  Discovery API for the Music segment within 12 km of City Hall from local midnight through three
  days, up to four pages of 200 (the API's deep-paging cap), and writes `concerts.json`: `t`, the
  local `day`, and one record per event with name, artist, genre, the ticket url, one 16:9 image
  url from ticketm.net, the venue's id, name and position, the local date and time, `tba`, `start`,
  and the two instants the page compares with real time: `from` (09:00 America/New_York on the
  show day, by zoneinfo, so the DST changes are the server's problem and `tests/test_concerts_bake.py`
  checks both of 2026's) and `until` (start plus four hours, or local midnight after a TBA time).
  Cancelled and postponed shows, TBD dates, venues without a position and anything outside the Music
  segment are dropped; dashes and middots become commas (the HUD rule). A oneshot service on a 15 min
  timer (`concerts-bake.timer`, 96 bakes a day against the key's 5,000 calls), `EnvironmentFile`
  `/etc/philly3d/concerts.env` (mode 600, root, Mike's to create), the sandbox lines the AIS relay
  uses, a README section, and a `location = /concerts.json` block in the vhost example for the
  GitHub Pages copy (a VPS edit that waits for his go, like the others).
- **The page.** `CONCERTS` beside `SCORES`: `concertsPoll` reads the file every 10 minutes while
  visible (the scores' gates, `serverNow` for staleness, a 3 h stale rule that drops every placard,
  no keyless fallback, silence on a miss), `concertsRefresh` re-reads the window once a minute from
  `Date.now()` and rebuilds only when the set of open shows changes, `concertsSet` builds the
  placards exactly as `scoresSet` does (a `.lbl.score.concert` div: the image when its host is
  ticketm.net, artist or event name, venue and clock time or "time to be announced", a "Tickets on
  Ticketmaster" link that opens the event page, limestone border and pin; one placard per venue,
  a hall with two shows tonight lists both in start order, since stacked placards covered each
  other) and `concertsRender`
  projects them with the scores' 14 km cut. Position: the venue's lat/lon through `SEPTA_GEO`,
  skipped outside the flight limit. The pin lands on the roof from the new `ROOF_GRID`: the three
  building loops note the tallest roof (absolute y, quarter metres in an Int16, 184 KB) of every
  footprint of 250 m2 or more into 100 m cells of the far box, so a placard at a hall the packed
  tiers built drops onto its roof without raycasting a freed chunk (gotcha 12); a venue the grid
  does not know stands 12 m; the arena, the ballpark and the stadium reuse `SCORE_VENUES` and stack
  22 m over a game there. The placard hangs 60 m over the roof.
- **The layer.** 'Live Concerts' in the layers panel with a count and the M key (the free letters
  were J K M O U Y Z), the tenth layer bit (512) with a marker bit (1024) on every written mask so a
  nine-bit link from before this round keeps the concerts at their default (on); the prefs blob needs
  no migration. `__dbg.concerts()`, `__dbg.roofAt(x, z)` and `__dbg.concertTest()` (six staged shows,
  from The Met to the Freedom Mortgage Pavilion, open now). Credits: the bottom line, the About
  panel and DATA-LICENSE.md name Ticketmaster and the non-affiliation. Verified in the pane with the
  staged shows and with a fixture file baked from a canned answer through the real baker; the feed
  itself goes live when Mike installs the baker and the key on the VPS.

## Round 55: the Delaware below the Navy Yard (Sep 11)

- **Boats on dry land south of the airport (Mike, with a satellite view).** The AIS ships stood on
  green ground west and south of the airport because the river was not there. Two causes. The
  river-bank test (`DEL_BANK`, an x-of-z polyline) describes the north-south reach only; below the
  Navy Yard the Delaware turns west past Fort Mifflin, Hog Island, the airport and Essington, and
  every low cell there fell on the polyline's "made land" side, so the far ground clamped the
  channel (about -1.3 m in `dem_city`) to just above the water plane. And the water sheet was the
  18 km square about the towers (x and z within 9,000), which ends at the airport's south shore.
  Now `southReach(x, z)` (z past 7,600, x under 3,400) counts as river in `eastOfDelaware`, so
  the DEM decides there (the 150 m grid separates the channel from the 1 to 4 m banks cleanly, and
  the tidal marsh under 0.6 m reads as water), the sheet spans the far ring's ground box (x
  -12,200 to 16,700, z -21,900 to 9,900), `offGridRiver` (z past the DEM's last row, x under
  -5,800) drops the ground to the bed where the strip used to repeat that row's mid-channel
  values as a false bank, and a second sheet carries the river past the world's south edge to
  the Jersey bank off Billingsport (z 10,900), over the apron. Verified at the airport, Essington
  and the Navy Yard; the wide box and the NE reach unchanged; 36 tests pass.
- **Round 55 coda (Mike, with a screenshot: the river still cuts off south-east of the airport,
  and a thin strip of river runs along the south edge of the map).** Both were the rectangle: the
  world's ground box ends about 500 m south of the airport's shore, and a band of water along
  that edge is neither the river's course nor absent. The river now comes from OpenStreetMap:
  `bake_delaware.py` (a new pipeline step, `delaware.json`, `DELAWARE_DATA`). OSM maps the
  tidal Delaware two ways, as `natural=coastline` below Tinicum (one strand up both banks from
  the bay; `is_in` never returns it, since a coastline is not an area) and as unnamed
  `natural=water` + `water=river` multipolygons above (relation 52618 is the Philadelphia reach),
  so no packed tier ever carried its surface. The bake fetches both over Marcus Hook to Bristol
  plus the `waterway=river` ways named Delaware River, polygonises the whole network against
  the query box and keeps the faces the centreline threads (the river is a chain of faces where
  the reaches meet; a hand-placed seed on a bank once dragged a 2,500 km2 land face in, so faces
  over 400 km2 are never water): one polygon of 117 km2 within 48 km of the origin, 38 islands
  as holes. The app draws the part outside the ground box flat at the river level over the apron
  (`beyond`, three pieces, 79 km2, so the river runs on to the fog past the world the camera can
  reach, Wilmington's reach one way and Bristol's the other) and uses `delawareAt(x, z)` as the
  shoreline for the far ground's cells beyond the DEM grids and for the reach below the Navy
  Yard (river wins where the outline says so, the DEM still carves the creeks and the marsh).
  The Round 55 rectangle (`offGridRiver`, the second sheet) is gone. Page +100 KB raw (the
  outline at 4 m and whole metres). And the strip's real root, found when a band of river showed
  along the box's east edge north of Torresdale once the sheet spanned "the box": Round 55 sized
  the sheet to the flight `bounds` (x -12,200 to 16,700, z -21,900 to 9,900), but the far ground is
  `RING_W` (x -12,000 to 16,500, z -21,700 to 9,700, the DEM's extent), so 200 m of sheet lay over
  the apron along every edge, a band of river wherever the eye reached it. The sheet and the bake's
  box are `RING_W` now. Found on the way and fixed too: past every DEM grid `demAbs` clamped to the
  WIDE grid's edge sample (the Delaware at Camden on the east), where the widest grid, dem_city, is
  the right one; nothing inside the ground box reaches that branch any more, but a stray query
  beyond it reads the far DEM's own edge.
- **Round 55 coda 2 (Mike: the Schuylkill River Trail is under water, trees and lampposts in the
  river).** Not the carve (`riverCarve` keeps the bank at water + 0.9 outside the outline) but
  the outline: `bake_schuylkill.py` united the OSM riverbank faces with the centreline buffered
  60 m each side so a gap in the outline still carries water, and that ribbon widened every reach
  the outline already bounds: 120 m against the 100 m between the walls at Center City, so the
  Schuylkill Banks stood in the water from JFK to Locust. The ribbon now buffers only the parts
  of the centreline that run outside the faces (the gaps), and the reach narrows by 45 to 55 m at
  JFK and Market (154 to 109 m, 161 to 106 m), 18 m at Chestnut, 17 at Walnut, 21 at Locust, with
  the east bank 10 to 36 m back off the trail; the park reach, where the ribbon is the outline,
  is unchanged. The trees and lamps were never in the river, the river was on the bank.

## Round 54: the material rework, one glass tint per building, the Center City towers defined (Sep 11)

The Sep 8 handoff notes (`aesthetic-updates.md`, cut from a Codex session on another checkout that
never reached this repo or GitHub) described three passes; this round reimplements them from the
descriptions against the Round 53 tree. Shading only: no measured geometry, terrain, data layer or
build input changed except the two Comcast crown records in `towers.json`. Nothing here is a survey
measurement: the panel widths, trim tones and crown proportions are visual approximations.

- **Masonry, trim, roofs, glazing.** The facade shader's mortar went from a 0.7 mix of a warm grey to a
  0.5 mix of a quieter limestone tone (0.60, 0.58, 0.53), the stone joints from 0.72 at 0.6 to 0.80 at
  0.5, the panel seams from 0.2 to 0.14, and the lintels, sills and trim colours a step toward the
  wall. Every joint now stands in relief: `jointRelief(d, w, aa)` returns a signed, anti-aliased
  triangle profile about the joint's centre line (the lip above shades the joint, the lip below
  catches the light), scaled by the sun's elevation (`relK = 0.35 + 0.65 * sunE`) at 0.12 on brick
  courses (7.5 cm), 0.10 on the stone (55 cm) and 0.06 on the panel seams (3.3 m), so a wall reads as
  laid, not printed. Local shading: on a `local` wall the last 0.6 m at each end takes 0.09 of shade
  (quoins and party walls) and the 1.1 m under the eave 0.12 (the cornice's own shadow), towers at
  0.4 of that. Roof membranes carry seams every 0.95 m along the grid (rotated 10 degrees with the
  streets) at 0.07 and a fine aggregate at 0.10, both faded by the pixel footprint before they could
  alias (`rnear`, gone past about 0.12 m per pixel). Glazing is less metallic everywhere: the facade
  windows 0.8 / 0.16 to 0.62 / 0.22 metalness and roughness, the outer curtain wall 0.7 / 0.12 to
  0.55 / 0.20, the core towers 0.7 / 0.1 to 0.55 / 0.18, the Ryland 0.85 / 0.06 to 0.7 / 0.12.
- **One glass tint per building (the bronze, grey and teal bands).** The fragment shader picked a
  tower's glass palette from a hash of 28 m world cells, so one wall crossing a cell edge changed
  colour mid-facade and a tall tower wore three tints up its height. Every vertex now carries `aTint`,
  a normalized byte from `glassTintKey(colour, style)` (a hash of the unshaded wall colour and the
  facade style, assigned before the ambient-occlusion ramp): `VBuf` grows, uploads and releases it with
  the style, base and floor height, `mergeColored(parts, ao, true)` fills it per part (or a part's own
  `tint`), the two ring pushers pass it on every wall vertex, and the shader reads `bid = vTint`. The
  tint is constant across a building's walls and height; the per-window lighting and reflections stay.
- **The Center City towers defined.** The curtain-wall upload called `ch.geometry(false)`, which
  attaches no attributes, so `outerGlassMat`'s `aStyle` read 0 on every researched glass tower and the
  three curtain-wall variants (21 Liberty Place bands, 22 dark glass, 23 the concrete grid) had never
  drawn (gotcha 22). The glass chunks upload with `geometry(true)`, the shader takes `aBase` for a
  terrain-relative floor datum (`yG = y - base`; the bands used to count from sea level, so a tower
  on the hill had a half-floor at its foot), and the Liberty Place crowns merge with explicit style 21
  and their base. The rhythm: spandrels narrower (21: 0.9 to 0.55, 22: 0.3 to 0.22, 23: 0.55 to 0.4,
  the default 0.5 to 0.32), mullions finer (0.05 to 0.035, the grid's 0.45 to 0.3), and two new
  variants by name: 24 the Comcast Technology Center (4.6 m floors, pale vertical fins at 1.5 m, a
  thin floor line) and 25 the Comcast Center (4.15 m floors, silver horizontal bands, a fine mullion);
  dark glass and the concrete grid keep their treatments. Glass-tagged OSM parts (`t === 10`) join
  the researched matching (they used to be excluded, so a tower whose shaft is a glass part never
  found its spec), and `towerAt(x, z, h)` matches a section above 300 m within 55 m instead of 35 (the
  CTC's spine, whose centroid sits off the tower's). A researched landmark never draws the random
  mechanical penthouse or mast any more. Crowns: a pre-pass over the packed body finds the tallest
  footprint matching each spec (`specTop`), and only that section raises the crown, once per spec
  (`crowned`): the before build counted 43 crowns for 18 crowned specs because every podium piece
  within a spec's radius raised its own pyramid or lantern; the after build raises one per spec. A
  section within 92% of the researched height ends at exactly that height (the tops end at the
  researched architectural height), every section that runs past the crown datum stops at the datum
  (an upper `building:part` used to run through the crown), and a scene that stops short of the
  research (the Inquirer's clock tower over its 61 m block) keeps its crown on its own top, at that
  height. `?dev=1` logs every spec match (`__dbg.towers().log`: name, crown, h, mh, top, near). The
  CTC crown is a `blade`: a narrow lit slab (0.86 of the long axis, 0.16 of the short, 38 m) standing
  in a dark frame of two posts and two rails on a low plinth, in place of the 18 m lantern box;
  `bake_towers.py` pins it (`C('blade', 38)`, `CROWNS` and `CROWN_H` know the type, `CROWN_CUTS` cuts
  the body for it) and the Comcast Center's notch carries `sides: 3` (recessed on both ends and one
  long face, the other flush). Re-baked: only those two records changed.
- **Atmosphere.** The river is slate teal (`COLORS.water` 0x07297b to 0x163038; the first try, 0x0a3644,
  rendered a bright turquoise through the legacy lift), the ripples calmer (`liquify` amplitude 1.0 to
  0.75, the gust envelope 0.45 + 0.8 to 0.5 + 0.6), the sky reflection cooler and lighter (the fresnel
  mix (0.42, 0.53, 0.62) at 0.17, the indirect specular tint (0.36, 0.58, 0.82) at 0.42), and a
  restrained shoreline lift returns on the sheets that carry a shore distance: the last 0.4 of `wsh`
  lightens 0.3 of the way toward a shallows teal by day (the Round 50 rule was no shore tint of any
  kind; this one is a lift of the body colour, never a foam line). The meadow's blotches soften
  (0.60, 0.66, 0.50 to 0.68, 0.72, 0.58), its grain 0.16 to 0.12, its macro drift 0.24 to 0.18, and it
  loses 12 percent of its saturation. Paving a shade darker: `PAVED_COL`, `LOT_COL`, `LOT_FILL_COL`
  and `COLORS.asphalt` (0x3b3833 to 0x37342f). The daylight key and fill rebalance: sun 2.0 to 1.85,
  hemisphere 0.10 + 0.36 dayF to 0.12 + 0.42 dayF (the Round 50 ratio was the owner's; the Sep 8
  notes moved it and this round follows them). `CLOUD_STEPS` 12 / 5 to 18 / 6. The streetlight cores
  are smaller at night (the point floor 2.0 to 1.6 px, the ceiling 9 to 7.5, the sprite's solid disc
  0.18 to 0.08 of its radius with a longer falloff).
- **The HUD.** Slate panels and limestone lines: `--ink` 0x171512 to 0x161a1e, `--panel` a slate
  rgba(30, 36, 42, 0.8), every hard-coded warm-ink rgba in `style.css` follows, the lines are
  limestone (`--line`, `--line-strong`), the label pins and tower labels take the new `--limestone`
  pair, the manifest and the theme-color meta follow the ink. Bronze stays on the buttons.
- **Verification.** `tests/test_vbuf.py` is new: it cuts the `IdxBuf` and `VBuf` classes out of app.js
  and runs them under JavaScriptCore with the vendored three.min.js (which loads under JXA: the UMD
  takes `globalThis`), pushes 40 vertices through an 8-slot buffer (three doublings) and checks that
  style, base, floor height and the tint byte reach `geometry(true)` intact, that the staging arrays
  are released, and that `geometry(false)` stays attribute-free; plus a static check that the glass
  upload asks for `geometry(true)` and that the outer glass shader declares `aStyle` and `aBase`. 36
  tests pass with the one expected failure. Built (25.80 MB, 7.7 KB over Round 53), `docs_check` ok,
  the browser console clean of shader errors, matched captures at noon and 21:30 from the skyline,
  the waterfront, the CTC crown, Spruce Street and a rowhouse face, before and after.

### Facade-accuracy plan status

**The LiDAR true-massing pass and Tier 1 of the facade-accuracy plan are done.**
Tier 2 (parametric storefront/signage kit from OSM shop names) and Tier 3 (photo-built
fronts like Rotten Ralph's/Glory) are the remaining rungs; `lidar-massing-plan.md`'s
option 2 (OPA join) is now executed as part of Tier 1.

Data © OpenStreetMap contributors (ODbL) — the credit link in the About panel must stay.

## Round 66: the venues where they stand, the river past Fort Mifflin, the blue bridge (Sep 16)

- **Mike, with a screenshot: the Underground Arts placard is a ways off; verify every venue we
  show.** A placard stands where Ticketmaster's venue record puts it, and Ticketmaster's geocoder
  misses half of Philadelphia's halls. Measured against each venue's street address (Nominatim,
  the OSM outline where there is one): Underground Arts sat 1,150 m south-east of 1200 Callowhill,
  on Independence Mall (the screenshot); Franklin Music Hall and Union Transfer shared one point
  at 6th and Fairmount, 558 and 714 m from their buildings; the Kimmel Cultural Campus and the
  Miller Theater shared a point at City Hall, 705 and 590 m off; Stateside Live stood 985 m east
  of the Live! casino; the Mann's TD Pavilion 215 m off in its lawn; MilkBoy 186 m; the Met 54 m,
  the Fillmore 35 m, NOTO 34 m, the TLA 13 m and Nikki Lopez (304 South St, a 150-cap room two
  doors from the TLA, so the two share a placard, each under its own heading) 4 m, all fine. The
  cure is `VENUE_NAMED`: a venue the page knows by name is pinned at its building whatever point
  the feed carries (the OSM outline's centroid in the model frame, or the address point where OSM
  has no outline), 26 halls from the Academy of Music and World Cafe Live to Johnny Brenda's and
  the Tower Theater, keyed by name rather than id so a duplicate venue record lands right too;
  `VENUE_AT` by id stays for the Fillmore's three rooms. The full venue list on the VPS was not
  consulted (the key never leaves the box; the sandbox refused the read), so the halls not yet
  seen in a feed are pinned from their addresses, unverified against Ticketmaster's points.
  Two rules moved with it: `CONCERT_MERGE` 130 to 80 m (the Fillmore's three rooms now share one
  exact point, and 130 merged Underground Arts with NOTO, 127 m up 12th Street, at a pin between
  them; the TLA and Nikki Lopez, 73 m apart on one block, still share), and a spot the tables
  placed snaps onto a score venue only within 120 m, not 500 (Stateside Live's placard had walked
  from the casino onto the stadium, 430 m off). Verified in the pane with the day's real feed
  widened to open every listed show at once: every fixed placard's pin lands on its own building.
- **Mike, with a screenshot: that strange strip of land over the river east of the airport.** A
  green ribbon 2.6 km long crossed the Delaware from Fort Mifflin to the Jersey bank at National
  Park, at an angle to the channel. It was two rows of the far ground's own vertices, z 7,500 and
  7,600, standing at made-land height (`TERRAIN.water` + 0.45) clear across the river: the far
  ground consulted the river outline (`delawareAt`) only beyond the DEM grids or in `southReach`,
  which starts past 7,600, and the Delaware between the Navy Yard and 7,500 was wet only by
  accident, because `bake_schuylkill.py` clips at z 7,500 and its polygon swallowed the Delaware's
  face at the confluence, so `riverCarve` was doing the outline's job up to its clipped edge. The
  x-of-z bank line (`DEL_BANK`) cannot describe the reach where the river turns west, the known
  Round 55 failure. `delawareTurn(x, z)` (z past 6,300, x under 3,400) now makes the outline the
  shoreline for every far-ground cell from the Navy Yard south; `southReach` keeps its flooding
  rule for low land. `__dbg.groundAt(-4000, 7550).mesh` went from -7.46 (0.38 m proud of the water
  plane) to -10.41 (the bed); the strip is gone from the same viewpoint.
- **Mike, with a photo: make the Ben Franklin Bridge look more like it does in real life.** Round
  1's bridge was white in the sun: its "Ben Franklin blue" `#8fb4c6` was a photographed sRGB
  value, and the legacy pipeline (handoff gotcha 11) lifts a stored colour, so it rendered at 214
  223 226. The pipeline was measured instead of guessed: a first cut at `#2f5c8c` captured at
  133 171 198 on the sunlit tower face, the ACES fit inverted from that (k 0.88 on a vertical face
  at 9 am, 1.78 on the roadway), and the stored values set for the photo's colours: steel
  `#2452a6` for about 120 165 205 in the sun and 40 80 125 in shade, granite `#5a3d26` for 165
  140 112, asphalt `#262422`, the walkways `#6e6656`. And the form: the real stiffening trusses
  rise ABOVE the roadway (8.2 m Warren trusses in the cable planes, 12 m panels, the seven lanes
  of asphalt between them, the PATCO tracks outboard under walkways raised 3 m with a rail), the
  suspenders land on the trusses' top chords and the cable sags to 2 m over them at mid-span, the
  towers have battered legs (8.5 m below the deck, 6.8 above) on granite piers with copings,
  heavy latticed X panels (2.4 m members, two above the deck and one below), portal struts at
  the pier, the deck, mid-height and the cap, saddle housings and a cornice, and the anchorages
  are granite with a 32 m arched portal the roadway threads through (a solid base, piers,
  springing and crown blocks, the stepped housing above with a string course). The floor narrows
  to 30 m inside the anchorages and the walkways stop there. Traffic rides `deckY` + 1.3 (the
  asphalt's top). Verified by capture from the river, the Camden tower and the Philadelphia deck.

## Round 66 coda: no road under the bridge (Sep 16)

- **Mike, with a screenshot: the road under the bridge should not be visible.** The wide road
  loop turns a major road's river crossing into a flat "deck" 20 m over the water, and the Ben
  Franklin's OSM carriageways got one beneath the real roadway at 41 m, a grey band the length
  of the span. The Whitman has had `wwbNear` since Round 12 for exactly this; `bfbNear(x, z)`
  (60 m of the chord between the anchorages) now skips the deck segments in the wide and far
  road loops the same way, and the on-land approaches keep their ribbons. The bridge block
  reads its anchorages from the shared `BFB_A`/`BFB_B`. Verified by capture from over the
  Philadelphia anchorage looking down the span.

## Round 67: low-poly clouds (Sep 16)

- **Mike: look in 3d assets/Clouds and use the low-poly models to illustrate cloud cover; keep
  the current setup intact in case I go back.** `Clouds.FBX` is a 3ds Max export of nine
  faceted cloud meshes (31 to 132 vertices, 58 to 260 triangles, Y-up, all triangles);
  `pack_clouds.py` reads it with a stdlib binary-FBX reader (version 7400: 32-bit node records,
  zlib arrays), centres each mesh on its bounding box, scales its width to 1 and writes
  `clouds.json` (25 KB, inlined as `CLOUDS_DATA`). The page instances them over a field of
  1,100 m cells about the camera (`CLOUD_FIELD`, `cloudFieldUpdate`: 15.4 km out on desktop
  with a second layer 500 m higher, 8.8 km and one layer on touch): each cell draws a cloud by
  hash with probability 1.25 times the cover (the second layer from 0.35 cover), sized 340 to
  800 m and growing 80 percent by full cover, so a clear day (8 percent) scatters a few puffs
  and an overcast one (92 percent, 1,582 instances) packs the sky with overlapping slabs; the
  field drifts with the deck's wind (its noise runs 0.0008 per metre, so `wxWind` times 1,000
  is metres per second) and rebuilds when the camera or the drift crosses a cell or the cover
  moves 2.5 percent. One ShaderMaterial lights the facets from the derivative normal: white
  tops, bellies blued by the sky (seen from below always, they stay bright), a touch of the
  sun's colour (0.35 of `cSun` read tan at 9 am; 0.15 now), the sky's cloud light for night,
  gloom and lightning, an overcast grey by `uCloud`, the pre-image handed to the post composite
  (gotcha 13) and the fog. The ray-marched deck stays whole behind `?clouds=deck`, and the
  ground's cloud shadows still follow the deck's noise field in both modes (an open item: the
  shadows do not fall under these clouds). First cut: 750 m cells and 170 to 400 m clouds read
  as a dense band of small dark lumps at the horizon, and the bellies at 0.66 grey turned every
  sky dour; larger, fewer and brighter fixed both. `__dbg.clouds()`. Verified by capture at
  8, 45 and 92 percent cover from the ground and from the flight ceiling. 43 tests pass.

## Round 68: the far side lighter (Sep 16)

- **Mike, with a screenshot from over East Park: the buildings without Mapillary data should
  look like the ones that have it; they can be lighter without using Mapillary, so the divide
  is less jarring.** The divide is York Street again: the outer districts (Brewerytown,
  Fairmount) read pale pink-tan and the far ring (Strawberry Mansion, North Philadelphia) brown.
  Round 65 had matched the tiers at the building level and blamed the rest on coverage; from this
  viewpoint the read is what counts, and it was measured: masked building pixels (no meadow, no
  white, no water or sky) averaged 129 114 99 on the far side, luminance 116, against 166 152
  140, luminance 154, on the near side, a third darker, with a redder cast (blue over red 0.77
  against 0.84). `colStats()` now tallies `widePhoto` and `widePlain` too, and in the stored
  register the photographed walls are the darker set (0.547 0.397 0.275 against 0.681 0.456
  0.350), so the plain walls inside the outer districts are not what darkens the far side; the
  block strips' wall-to-wall roofs, no street trees and no yards are. `farLight()` lifts every
  low wall the far ring and the towns draw from the reservoir, and every roof cap they carry,
  by `FAR_LIGHT` 1.8 after folding 15 percent toward the luminance grey (`FAR_DESAT`), clamped
  at the register's 1.0 (the lean chunks store 8-bit colours). Two cuts: 1.35 took the far side
  from 116 to 131 (the register saturates, so the gain runs ahead of the read); 1.8 to 145,
  within six percent of the near side, at 153 144 130 against 165 151 140. Verified by capture
  from the same pose and from over Nicetown looking north: nothing blown out, the industrial
  boxes and the rowhouse strips a shade paler. The Round 65 note stands as history: the
  coverage difference is real, and this round compensates it rather than closing it.

## Round 67 coda: the deck again (Sep 16)

- **Mike: the low-poly clouds are not working, revert that.** The ray-marched deck is the
  default sky again. The field stays in the code and its 25 KB of models in the page, built
  only behind `?clouds=lowpoly`, so it costs nothing until he wants another look; `?clouds=deck`
  no longer means anything. Verified in the pane: the deck draws by default and `__dbg.clouds()`
  reports the field off.

## Round 69: the phone's screen (Sep 16)

- **Mike, with two phone screenshots: centre the loading screen's content on mobile, remove
  the copyright line at the bottom, remove the explainer box at bottom left, put "Move" in the
  centre of its circle the way "Look" is, and move the compass and the climb buttons as far
  right as they go with 5 px of padding.** The veil's short-viewport rule (max-height 460 px)
  had pinned the card to the top so the Enter button stayed reachable on a scrolling screen; it
  is centred now, with auto margins on the card so it still scrolls when taller than the
  screen. Under a coarse pointer the hint box and the credit line are hidden, the compass and
  `#flyctl` sit 5 px (plus the safe-area inset) off the right edge, and the Move pad keeps its
  label through the flight (it went transparent under the stick before; the hint box had also
  covered its lower half, which is what made the word look off-centre). The OpenStreetMap
  attribution stays reachable on phones through a Credits link in the guide's kicker
  (`#guideCredits`, phones only: it closes the guide and opens the About panel, which carries
  every credit), so the data terms hold with the line gone; desktop keeps the bottom line.
  Verified in the pane at 740 by 360 with touch emulation: the veil card centred, no hint, no
  credit line, Move and Look both labelled, the compass 5 px from the edge.

## Round 70: the phone's clouds, and the buttons at the edge (Sep 16)

- **Mike, with a phone screenshot: make the clouds a little less pixelated and more together;
  move the bottom and right-hand buttons closer to the edge.** The deck marched 6 samples on
  touch (18 on desktop), so each step was 120 m of slab and the per-pixel jitter that hides
  banding (0.6 of a step) scattered every sample by up to 72 m from its neighbour's: the clouds
  read as stipple, torn at every edge. `CLOUD_STEPS` is 12 on touch now with the jitter at 0.4
  of a step, a quarter of the old scatter. Buttons: the compass and `#flyctl` had 5 px plus the
  safe-area inset, and a notched phone reports 59 px on both sides in landscape, so they stood
  64 px off the edge; on a coarse pointer they are 5 px flat now and the bar 6 px off the bottom
  (the home indicator's inset dropped too, at his call). Verified by capture at 740 by 360 with
  touch emulation: the mean step between neighbouring pixels inside the clouds fell from 8.4 to
  2.8 grey levels (a third of the speckle), the offsets measured in the DOM at 5, 5 and 6 px.

## Round 71: the flicker at East Falls (Sep 16)

- **Mike, with a phone recording: some buildings still have this flickering effect; the one near
  the centre of the frame; knock it out model-wide.** The frames, pulled with AVFoundation
  (there is no ffmpeg here; `frames.swift` in the scratchpad), showed a teal tower with a banded
  grey face whose stripes drifted diagonally from frame to frame. The tower is the 89 m one by
  the Schuylkill at East Falls (`city.b64` record at -4875, -6457), a far-ring solo. Two causes
  were chased, and both are closed.
- **Walls on one plane.** The far ring's packer had none of the guards the outer districts' has
  carried since the z-fight rounds (`dedupe_stacked`, `nudge_coplanar`): they live in
  `pack_common.py` now and pack_city.py and pack_outskirts.py run them too, with the inset
  1.5 times each packer's coordinate grid (1.05 m on city.b64's 0.7 m, 1.5 m on the towns'
  1.0 m) so the int16 rounding cannot cancel it. The re-pack found 16 shared same-facing walls
  in the far ring (rowhouse strips flush with a taller neighbour, the Penn Medicine towers,
  a pair at the airport) and none in the towns; the blobs' sizes and counts are unchanged
  (180,107 and 25,526 buildings). `tests/test_pack_common.py` (6 tests) pins the guards. None
  of the 16 was the East Falls tower.
- **The bands.** The real cause was the facade shader: the tower branch keeps a tower's window
  detail alive to 3.5 m a pixel on desktop and, through the phone's `uDetFar` 0.55, to 6.4 m a
  pixel there, and a 3.2 m floor at six metres a pixel is half a pixel per floor: the horizontal
  glass bands of the band styles (15, 18, 7) cannot be anti-aliased at that footprint, only
  aliased, and the `aa` smoothstep of each edge leaves a moire that drifts with the camera. The
  detail chain is now gated by render pixels per floor (`rowPx` = 3.2 / fwidth(v): nothing under
  1.5, full above 3.5) and the mullions and balcony posts along a wall by pixels per bay
  (`colK`), whatever the platform's stretch; past the gate the far average takes over, which is
  what those pixels can honestly show. Measured at 740 by 360 with touch emulation on the
  tower's face: the mean vertical step between neighbouring pixels fell from 44.5 to 12.8 grey
  levels 700 m out and from 16.0 to 4.5 at 1.2 km, the sky control at 3.7 both times. On desktop
  a tower's windows now fade between about 900 m and 2 km instead of holding to 3.4 km; the
  night windows on phones fade at the same footprint, since a lit band under two pixels a floor
  shimmered too. 49 tests pass.

## Round 72: the phone's frame rate (Sep 16)

- **Mike: a lot of frame rate drop when moving around the city on mobile; is there anything we
  can do?** Read from the frame loop rather than measured (no phone here, and the pane runs no
  animation frames), three costs stood out that a phone pays and a desktop shrugs off, and none
  changes the look. The shadow depth pass (2,048 square on touch, every caster in the box: the
  core, the landmarks, the trees, the buses) redrew every fourth frame whenever SEPTA buses were
  on, which they are by default, and again every time the camera crossed a third of the shadow
  box: on a phone it redraws every twelfth frame for the buses now, a lag of a fifth of a second
  on a bus's shadow that no one will see. The soft shadow filter (`PCFSoftShadowMap`) samples the
  depth map several times for every lit pixel; a phone uses `PCFShadowMap`, the plain filter,
  whose harder edge at 2,048 square over a 600 to 1,800 m box is a texel of 0.3 to 0.9 m. And
  the adaptive pixel ratio, which steps down 15 percent whenever the median frame passes 22 ms,
  stopped at 0.9 on every device; a phone may go to 0.72 now, a fifth of the pixels of its 1.5
  cap, and climbs back the moment frames run short. What was already in place and stays: the
  chunks frustum-cull after their upload, the lane paint, the light poles and the traffic are
  off on touch, the grass is a third of the desktop's, the SEPTA badges are instanced sprites.
  Next levers if it still stutters, each a visible trade: the cloud march back from 12 to 8 on
  touch, fewer water octaves, fewer tree crowns near the camera. Verified in the pane with touch
  emulation that the page builds, the shadows draw and the ratio floor reads 0.72; the frame rate
  itself is Mike's to judge on the phone. 49 tests pass.

## Round 73: the moon's glare, and the phone again (Sep 16)

- **Mike: still choppy on the phone at times; lessen the moon glare and make it proportionate to
  how much of the moon is visible.** The moon first. Its halo was 0.10 of white at the disc,
  falling off by exp(-0.22 (angle / radius)^2) and scaled by the lit fraction; it is 0.06 now,
  falls off by 0.32, and scales by the square of the lit fraction, so a half moon carries a
  quarter of the full moon's halo and a crescent next to none. The disc's night brightness
  follows the fraction too: the full moon at 0.9 of the white it was, a half moon at 0.7, a
  crescent's sliver at 0.6; the day wash is untouched, and the disc stays out of the bloom
  (the dome's alpha masks everything but the sun). Measured on the desktop full moon of Sep 26
  at 9:30 pm through the post pipeline: the disc's mean fell from 141 to 126 grey levels and
  the ring 1.2 to 2 radii out from 41 to 36 over the sky (the rest of that ring is the disc's
  edge spread by the capture), with a crescent captured for the proportional case.
- **The phone, round two.** The levers the last round named: the cloud march 12 to 9 on touch
  with the jitter at 0.35 (the stipple metric sat at 8.4 at 6 steps and 2.8 at 12, so 9 lands
  near 4); the water skips its two finest octaves on touch (2.6 and 1.2 m, under a phone's pixel
  almost everywhere, two of five noise passes gone from every water pixel); the shadow box
  re-aims after half its extent instead of a third, so the depth pass redraws half as often on
  the move; and the grass field is 6,000 tufts, from 9,000. Not yet touched, the next candidates
  if it still stutters: the SEPTA poll (370 KB parsed on the main thread every 25 s) could move
  to a worker, and the phone's pixel cap of 1.5 could fall to 1.25. 49 tests pass.

## Round 73 coda: the towers' lights come back (Sep 16)

- **Mike, with a night screenshot from the phone: why do the larger buildings show no lights
  from such a close distance? It ruins the immersion.** Round 71's gate, which fades a facade's
  floor pattern under 1.5 render pixels a floor so the day's bands cannot moire, gated the lit
  windows too: they ride on the same masks (`shtLit` is `glass * litOn` by `det`), and a phone's
  render pixels are large, so every tower past a few hundred metres went dark after sunset while
  the far glow and the rowhouses close by still sparkled. The gate is the day's now
  (`mix(gate, 1.0, uNight)`): after dark the detail chain stands to the distances it did before
  Round 71, which on a phone is the `uDetFar` stretch Mike asked for in the first place. Verified
  by capture at 740 by 360 with touch emulation, over Center City at night before and after.

## Round 74: the turn at altitude (Sep 16)

- **Mike: smooth, until I am flying through the sky and I turn around; that is when it gets
  choppy.** The first suspect was the shadow box, aimed a third of its extent ahead of the
  view, so that a turn might re-aim it and cost a depth pass of every caster in a 900 m box.
  Measured in the pane with touch emulation by counting depth-pass requests over a scripted
  180 degree turn at 700 m with the buses off: none, in the old build too. The re-aim test
  measures the camera's distance from the box's centre, not the aim point's, so a turn in
  place never moves it; the suspect was innocent. What a turn does change is the load: facing
  Center City from 700 m draws 8.1 M triangles in 384 calls against 4.6 M in 200 facing South
  Philly (74 neighbourhood and landmark labels on screen either way), and the
  adaptive pixel ratio took two seconds (30-frame windows, 15 percent steps) to settle after a
  turn into the dense half, the choppy stretch. On touch it judges every 15 frames and steps
  down by a fifth now, and its cap is 1.25 instead of 1.5 (the fill cost is the square: 0.7 of
  the pixels at the top). Kept from the investigation, since each removes a depth pass a phone
  paid for nothing: the box is aimed at the camera itself on touch, grows in 300 m steps
  instead of 100 (a climb re-aimed every 100 m), and is frozen above 600 m (`shadowFrozen`: no
  re-aim, no bus refresh), where no shadow can be read. Desktop keeps the look-ahead, the 100 m
  steps and the 30-frame windows. 49 tests pass.

## Round 75: the air you can see (Sep 16)

- **Mike, from the open-data survey: air quality drives the haze.** The survey of the city's
  data sites (the ArcGIS Hub behind data-phl.opendata.arcgis.com is the real store, 6,332
  items; OpenDataPhilly its catalog of 470; developer.phila.gov a CMS gateway that 403s
  scripts; the phlapi repo a 2012 prototype) turned up the Department of Public Health's Air
  Management Services layer `LATEST_CORE_SITE_READINGS`: eight monitoring sites, hourly PM2.5,
  PM10, ozone, NO2, SO2 and CO, CORS open, no key. Probed at 14:00 EDT: six sites report
  PM2.5 (5.6 to 7.7 ug/m3, mean 6.5, AQI 36), three report ozone (52 to 56 ppb), the rest are
  null, and one field carried a -999 sentinel. The page reads it every 15 minutes beside the
  weather (the readings are hourly, so a value is at most 75 minutes old).
- **What it does.** The particulate is what the eye sees, so the citywide PM2.5 mean sets the
  clear-air distance through Koschmieder's rule (visual range about 3.9 over the extinction,
  fine particles about 4.6 m2 a gram): the multiplier `k = 22 / PM2.5`, clamped to 0.08 to 1,
  so 22 ug/m3 keeps the 40 km a clear day already has, the top of Moderate (35) is 0.63 of
  it, an Unhealthy day (80) 0.28, wildfire smoke (260) 0.08. A smoke tint (0 to 30 ug/m3
  nothing, 1 from 120) warms the horizon and the fog toward tan (0xb89a72 sky, 0xa88a62 fog,
  the June 2023 look), dulls the zenith, and dims the sun 30 percent toward 0xff7a30. Both
  ease over 20 s (`WXFX.haze`, `WXFX.hazeTint`), and both multiply the existing night and
  weather factors, so fog still collapses the air (55 / 850 m with smoke on top) and night
  still shortens it. The AQI on the time panel ("Air quality: 36, Good") is the larger of the
  PM2.5 index (EPA's 2024 breakpoints) and the ozone index, the hourly ozone read against the
  8-hour table (an approximation, stated in the code). A reading needs two PM2.5 sites under
  twelve hours old (the first cut was three, and the live check at 22:40 found the layer's
  latest sample still the 14:00 hour, so every row failed it; the layer lags by hours, and an
  afternoon reading still describes the day's air); a feed silent for a day eases the air
  back to clear.
- **Pins.** `?aqi=<n|good|moderate|usg|unhealthy|veryunhealthy|hazardous>` (PM2.5 5, 30, 45,
  80, 160, 260), `__dbg.aqi(n)`, `__dbg.aqiState()`; a `?wx=` preset alone pins the air at
  Good so a weather demo stays reproducible.
- **Measured in the pane** at 700 m over Center City at noon: Good 8,000 / 40,000 m as before;
  Unhealthy 2,200 / 11,000 by day and 770 / 4,400 at night (the far windows sink into the
  haze, no white band); Hazardous 677 / 3,385 under a tan sky with the city gone past the
  outer districts. The pane composites a frame late, so a screenshot follows a one-second
  wait. 51 tests pass (`tests/test_aqi.py` runs the pure block under JavaScriptCore).

## Round 76: the farmers' markets on the clock (Sep 16)

- **Mike's pick from the survey: farmers' markets on the clock.** The City's `Farmers_Markets`
  layer (34 points, one ArcGIS page) carries per-weekday hours as `HH:MM` strings, the season
  as a month name plus a day, `Yes` for year round, the payments each market takes and a
  website. `fetch_markets.py` caches the GeoJSON, `bake_markets.py` parses it into
  `markets.json` (9 KB): hours to minutes keyed by JS weekday, an end at or before its start
  twelve hours later (Germantown Kitchen Garden's `01:00` is one in the afternoon), a missing
  day defaulting to the first and the last of the month, two seasonal rows with no months at
  all (University Square, the Castor and Hellerman pop-up) left open all year by weekday,
  websites normalised (`Thefoodtrust.org`, `www.egreenevents.com`), dashes to commas. 34
  kept, 16 year round, none dropped.
- **What it does.** `step('Pitching the market tents')` snaps each market to its nearest
  street (`septaSnapRoad`, 40 m) for the row's axis and puts three to five tents 3.4 m apart on
  the market's own side, facing the road (on the centreline itself, a closed street, they face
  across it). A tent is about 120 triangles: four posts, a table with three crates, an
  eight-gore canopy alternately white and its stripe with a valance, in four colourways as
  four instanced meshes with their own Lambert materials (a stripe is two vertex colours, and
  a shared instance-colour program reads black). `updateMarkets` re-evaluates only when the
  clock's date or minute changes (the live tick, a slider drag, a preset, a lapse step, a hash
  clock) through `marketOpenAt`: the weekday's hours, end exclusive, then the season, a
  November-to-March season wrapping New Year. The tent count folds into the shadow caster
  signature so an opening market gets its shadows. Tap a tent (or the market point from the
  air) for the card: Open or Closed, "Open today 10:00 AM to 2:00 PM" or "Closed today, opens
  Sunday 10:00 AM", the season and days, the payments with cash implied, operator, address,
  the city's note, the website. The search index knows every market as a "Farmers Market" and
  opens the card on arrival whether or not the tents are up; `__dbg.markets()`,
  `__dbg.setClock(y, m, d, min)`, `cardFor('market', name)`.
- **Measured in the pane** with the clock pinned: Sunday Sep 20 at 11:00 three markets open
  (Headhouse, Dickinson Square, Schuylkill River Park, 12 tents), Saturday Sep 19 thirteen
  (56 tents), Monday none. Captures: Clark Park's row on the Baltimore Avenue sidewalk,
  Rittenhouse's canopies and crates on Walnut at 18th, and Headhouse's tents standing under
  the Shambles roof, where the market really is, so from the air a Sunday and a Monday look
  alike there and at street level the stripes show between the piers. 58 tests pass
  (`tests/test_markets_bake.py`, `tests/test_markets_js.py` under JavaScriptCore).

## Round 77: the historical markers and the public art (Sep 16)

- **Mike's pick from the survey: markers and public art.** Two sources. The Pennsylvania
  Historical and Museum Commission's markers on the state portal (Socrata `xt8f-pzzz`, public
  domain): 348 in Philadelphia County, City 244, Roadside 99, Plaque 5, with name,
  dedication date, location and the marker text itself (104 KB of text, the longest 464
  characters), seven coordinate pairs shared by two markers, eleven rows with an undocumented
  `status = True` (kept; the bake prints them). The City's Percent for Art layer: 239 works
  whose polygons are 40 m buffers (the centroid is the spot), Active 224, Inaccessible 10
  (interior works), In Progress 5; an S3 PDF link for 130 of the kept works and the literal
  "No image available" for the rest; the streetview links mostly "N/A". `fetch_markers.py`
  caches both, `bake_markers.py` writes `markers.json` (177 KB): arrays not objects, whole
  metres, types by name, the state's " - PLAQUE" suffix stripped, twins nudged 2 m apart,
  Active works only, a material scan of the medium (bronze 54, steel 86, stone 18, other 66),
  the image link only on the city's bucket, every string cleaned and none carrying `</script`.
  One more rule came from the pane: the Clothespin's plinth was nowhere at Centre Square
  because its buffer centroid lies inside the podium's footprint, thirty metres from any
  street, and a post inside a building mass is a post nobody sees. The bake now tests every
  point against the page's own footprints (scene.json's core polys and the two packed tiers,
  decoded through the test suite's walker in 1.5 s, 296k rings in a 64 m grid) and steps an
  inside point 2.5 m out past the nearest wall (`FootGrid`, three tries for a point that
  lands in the next building): 59 markers and 135 of the 224 artworks moved, which says
  where the city's art points really sit, at the building's address.
- **What it does.** `step('Raising the historical markers')`: two instanced meshes for the
  posts (Roadside: a 1.14 by 1.07 m plate from 1.3 m; City: 0.71 by 1.0 m from 1.4 m; a dark
  post, a gold frame, the blue plate proud of it, five gold lines of text on either face and a
  keystone finial, about 170 triangles) and four for the art (a stone plinth with an upright
  form in bronze, steel, stone or a verdigris). Each has its own Lambert material (a shared
  instance-colour program reads black), casts shadows, and is always on like the streetlamps.
  Placement: `siteY` ground and `septaSnapRoad` within 30 m for the yaw that faces the
  street; a marker within 9 m of the centreline (the roadway, or the block behind the kerb
  where a geocode lands) moves to the sidewalk 5.5 m out on its own side, a work within 3 m
  to 4.5 m. The five wall plaques get a card and a search entry, no post. The picker takes a
  hit on a post or a plinth, or the nearest of the 567 within 30 px of the tap, and the card
  follows the post: PHMC chip, name, the full text in a scrolling wide card (`#vehinfo.wide`,
  `.vtext`), location, "Dedicated 1993, City marker", the Commission's credit; for a work the
  title, artist, "1970, Metal, stainless steel", where, the Percent for Art credit and a link
  to the image PDF, never inlined. The search box knows every marker and title
  ("Historical Marker", "Public Art") and arrives with the card open; `__dbg.markers()`,
  `cardFor('marker', name)`, `cardFor('art', title)`.
- **Measured in the pane**: 343 posts and 224 plinths raised; captures of "Common Sense" on
  the far sidewalk of 3rd Street facing the road, the Betsy Ross City marker on the lawn at
  Arch Street, and the art plinths; from 90 m over Independence Mall the posts are the
  pinpricks they are in life. Page 26.21 MB, plus 188 KB raw for the two layers.
  63 tests pass (`tests/test_markers_bake.py`).

## Round 78: the named places in the search box (Sep 16)

- **Mike's pick from the survey: named places for search.** The City basemap's Landmarks:
  `Landmark_Poly` (9,202 polygons) and `Landmark_Points` (1,147). The file is not what its
  field names suggest: `TYPE` is a small integer 0 to 12, `LABEL` a Y/N flag for the city's
  own labelling, and only `SUBTYPE` carries the class; 3,796 polygons have no `NAME` and are
  the parcels of a `PARENT_NAME` (a park's lawns and courts, a rec center's buildings), 115
  and 32 rows are archived, 347 are `PUBLIC_ = N` (the water department's yards), and the
  point layer carries 142 neighborhoods that `places.json` already has. `fetch_landmarks.py`
  pages both layers; `bake_landmarks.py` drops the archived, the non-public, the
  neighborhoods, the utility yards, industrial sites, communication towers, plain retail,
  housing and parking lots, classes the rest by subtype into fifteen kinds (school, college,
  place of worship, hospital, park, rec center, cemetery, museum, historic site, venue,
  public building, station, bridge, named building, natural feature), keys a site on NAME
  else PARENT_NAME with the area-weighted mean of its parcels' centroids (a university lands
  mid-campus), splits a recurring name into another site past 400 m and sorts the largest
  first. 5,932 places from 10,349 rows (worship 1,582, park 862, school 719, site 572,
  college 512, building 327, civic 273, museum 213, rec 207, hospital 193, venue 177, station
  92, cemetery 77, nature 76, bridge 50), `landmarks.json` 272 KB, the page 26.48 MB.
- **In the app**, search only: `LANDMARKS` joins `buildNameIx` after the named buildings,
  with `LM_KIND` decoding the class into a kind and `KIND_LABEL` naming it in the result
  row ("Julia R. Masterman School, School"); `add()` now drops the same name within 150 m
  under any kind, so a label's entry wins over the city layer's (Independence Hall appears
  once) and the biggest of a recurring name over the rest; a park, a cemetery or a college
  glides to 400 m and keeps its pin. The landmark label tier stays as it was, off by default
  (5,900 DOM labels is not a tier). The guide's Search rows gain "a school, a church, a
  park"; `__dbg.nameIx()`, `__dbg.search(q)`.
- **Measured in the pane**: the index grows from 1,934 entries to 7,156; "masterman" returns
  the school, "palumbo" the park, the rec center and the Academy at Palumbo, "christ church"
  the marker, the park and the cemetery; a panel search for "Clark Park" lists the Saturday
  market first and the park second, and "Palumbo Recreation Center" glides to 457 m off the
  rec center and circles it. One fix fell out of that check: with the pane's sparse frames
  the glide jumped from start to end in one frame and `orbitAround` read the camera before
  `applyFly` had carried it, so the circle ran from the old spot a kilometre off; it now
  starts from `fly.pos`, the glide's landing, which a stalled frame on a phone would have hit
  the same way. 67 tests pass (`tests/test_landmarks_bake.py`).

## Round 79: the closed blocks (Sep 16)

- **Mike's pick from the survey: live street closures and paving.** The Streets Department
  keeps its StreetSmartPHL map on the City ArcGIS (CORS open, no key, updated every 30
  minutes): closure permits as city centreline segments with type, occupancy, dates, purpose
  and the permit link (6,761 rows, all "Current", 5,775 in force on Sep 16, of which 1,213
  full closures, 4,353 partial and 211 sidewalk; the partials are mostly parking
  relaxations for dumpsters), the paving season's status per block (1,832 rows: 601
  scheduled for milling, 468 paving scheduled by PennDOT, 416 paved with striping pending,
  175 complete, 112 ready to pave, 30 paved by PennDOT, 30 milled and waiting), and this
  week's milling and paving lists (empty today). A date filter works only as
  `ExpirationDate>=CURRENT_TIMESTAMP` (epoch literals return 400), some expiries run to
  2103, and the purposes are padded, capitalised free text. Three GeoJSON pages of a
  megabyte each per viewer per half hour is the wrong shape, so `ops/closures_bake.py` on
  the VPS (a oneshot on a 30-minute timer, the concerts baker's skeleton without the key)
  fetches the permits in force, joins LaneClosure_Master's addresses by permit number,
  groups by segment with the strictest occupancy of the permits that vote (parking
  relaxations, dumpsters, containers, loading zones and valet stands do not; a segment with
  only those is dropped), caps an open-ended permit at 180 days, drops one starting more
  than a week out, title-cases the purposes with the city's acronyms kept, keeps a permit
  link only on stsweb.phila.gov, and writes `closures.json`: 4,695 closures (1,086 full, 124
  sidewalk) from 5,775 permits and 476 paving strips, 2 MB raw and 187 KB gzipped. The
  page treats a file three hours old as a stopped baker.
- **In the page** (`step('Posting the street closures')`, the U key, the twelfth layer bit):
  each segment's length-midpoint is snapped to the drawn street with `septaSnapRoad` and the
  whole line moved by that offset (the city's centreline sits a few metres off OSM's, and the
  endpoints are at intersections where a snap finds the cross street), then trimmed 7 m at
  each end. A closed block gets a barricade row of drums across each end (three to seven
  by the street's width, the core's road grid knowing the width and the outer streets taken
  at 4.5 m) and one every 10 m down its middle; a partial closure cones every 6 m along one
  kerb; a closed sidewalk cones every 8 m on the pavement. Heights follow the traffic
  layer's road formula with the bridge decks and the overpasses. 84,896 objects posted
  citywide, drawn within 2.5 km of the camera on the streetlights' cadence (two instanced
  meshes, standard materials so the build-end weather pass lays snow on them, 6,000 each on
  desktop and 1,200 on a phone). The paving strips are `ribbon`s six centimetres over the
  lane paint (polygon offset is banned on the flats), fresh black for the paved blocks and a
  rough grey for the milled, one merged mesh each. Typical traffic wants no cars on a run
  whose midpoint lies within 25 m of a fully closed block's (`CLOSE_TRAFFIC`, 83 runs today;
  a run is a chunk up to 400 m, so it is coarse and Mike can flip the constant). Tap a drum,
  a cone or the block's midpoint for the card: Closed, Partly Closed or Sidewalk Closed, the
  block's address, each permit's purpose and type with its dates ("Through Dec 28, 2026"),
  the permit link, "Streets Department Permit". `__dbg.closures()`, `closureNear(x, z, o)`,
  `pavingNear(x, z)`, `closureTest()` (a full closure on Locust, a partial on Spruce, a
  sidewalk on 3rd, a paved block of Pine), `cardFor('closure', addr)`.
- **The layer bits.** Ten keys became twelve: bit 1024 is reserved for Round 80's Amtrak
  trains (its flag, row sync and toggle exist now so the bit holds still), 2048 is the
  closures, `LAYER_MASK_V3 = 4096` marks a twelve-bit link and `layersFromMask` tests it
  before the ten-bit marker (a twelve-bit link with the trains on has 1024 set as a layer, not
  a marker); `parseHash` widened its mask to 8191. A ten-bit link keeps both new layers at
  their defaults. The vhost gains a `location = /closures.json` block (max-age 120, ACAO *)
  for Mike to apply, and `ops/README.md` a section 8.
- **Measured in the pane** with a live bake served from the scratch directory: 4,695 records
  and 84,896 posted objects landed, 5,615 drawn from the first camera, 83 traffic runs
  closed; captures of the barricade row of drums across the Unit Block of S 2nd Street with
  more down its middle, the cones along the far kerb of the 100 block of Walnut, and the
  darkened 700 block of Locust; `closureTest()` seeds three blocks by the towers and the
  card reads "Closed, 300 Block of Locust St, Trench and Install Water Main, Utility Work
  Excavation, Through Oct 16, 2026". A twelve-bit link with the closures bit clear
  (`#l=6143`) loads the layer off and the U key brings it back; a ten-bit link (`#l=2047`)
  keeps it on. 69 tests pass (`tests/test_closures_bake.py`). The baker itself is Mike's to
  install on the VPS (ops/README section 8) with the vhost block; until then the row stands
  with an empty count and reads Feed Offline after three misses.

## Round 80: Amtrak on the Northeast Corridor (Sep 16)

- **Mike's pick from the survey, his call to revisit rail: Amtrak comes in.** SEPTA's
  Regional Rail went out in Round 20 as underground and hard to track; every Amtrak train
  through the city runs on the surface (the Arsenal bridge, 30th Street, Zoo, the North
  Philadelphia viaduct, Frankford Junction, Holmesburg, Torresdale; the Keystones west past
  Overbrook), and Amtraker (a community mirror of Amtrak's own tracker by piemadd, ODC-By
  1.0, CORS open, a User-Agent required) had 218 trains and seven inside the box on Sep 16.
  Its answer is the whole country, 1.29 MB raw and 121 KB gzipped a pull, and Amtrak's
  fixes come about every 224 seconds on average.
- **The track.** Nothing in the page held a rail polyline (fetch_wide.py pulls the ways,
  nothing keeps them; the El is the only track). `bake_rail.py` asks Overpass for the
  railway=rail ways Amtrak operates over the far-ring box plus the Northeast Corridor and
  Keystone Corridor ways by name, drops the 130 service and industrial ways, keeps each
  way's tunnel/covered and bridge flags, clips, simplifies to 1.5 m (a stdlib
  Douglas-Peucker) and writes `rail_amtrak.json`: 713 lines (every track its own), 213 track
  km, 21 lines in tunnel (the 30th Street shed), 224 on bridges, 72 KB; the nearest line is
  3 m from 30th Street Station, 6 m from North Philadelphia and 15 m from Overbrook. The
  page's `step('Laying the Northeast Corridor')` builds a 36 m snap grid (`railSnap` gives
  the point, tangent, height and flags; `railWalk` walks the rails for a distance, the
  heading kept continuous across segments) and draws the corridor from 20 m segments: a
  ballast slab and, on desktop, two rails, the profile smoothed like the El's, a bridge held
  at its higher abutment and 9 m over the water, the tunnel runs in the grid and not drawn.
- **The baker and the page.** `ops/amtrak_bake.py` (a loop service, 30 s, gzip, the
  concerts skeleton) keeps the Active trains inside a box 11 km beyond the model's with
  route, position, compass heading, speed, the fix time, destination, the first station not
  yet departed and its lateness, and writes `amtrak.json`, a few hundred bytes. The page
  polls it every 30 s, treats 150 s stale as a stopped baker and then pulls Amtraker itself
  every 60 s through the same projection (`amtrakProject`), retrying the baked file every 5
  min. A fix snaps to the track; the compass letter signs the direction against the tangent
  when it speaks clearly (never a yaw), the displacement since the last fix decides
  otherwise, else the sign stands. The target is the fix walked along the rails by what the
  train ran since (`AMTRAK_RUN` 240 s at most, raised from 180 when the live check found
  fixes 171 and 201 s old); the head runs on at the train's speed and converges on the
  target over about four seconds, never backing, and a target more than 600 m off snaps. The
  consist follows car by car back along the rails (an ACS-64 and eight Amfleets for a
  Regional, a power car, eight coaches and a power car for an Acela, five coaches for a
  Keystone), each car re-snapped so a 26 m coach follows the curve, a car in the shed not
  drawn; the cars ride the fleet's night material with a glowing window band, a badge with
  a train's face floats over the head car, and the card gives "Train 192 to Boston South,
  9 Cars, 60 mph, Next Stop: Philadelphia 30th Street, 7 Min Late" with Amtrak's own
  track-your-train link. The K key and the eleventh layer bit, the row after Live Ships,
  Amtraker in the credit line and the About panel with the service-mark notice.
- **Measured in the pane** with a live bake served locally: two Northeast Regionals landed
  on the first poll (177 southbound past Torresdale at 100 mph drawn with its loco, eight
  coaches and pin; 198 at the box edge held back by the limit); captures of 177 on its drawn
  track across the neighbourhood, the Acela seed on the North Philadelphia viaduct with the
  red stripe leading, the viaduct from the air with the tracks drawn, and 30th Street with
  the stopped seed hidden in the shed. Page 26.61 MB (the track 72 KB, the code about 30 KB).
  73 tests pass (`tests/test_amtrak_bake.py`, `tests/test_rail.py`). The baker service and the
  vhost block are Mike's to install (ops/README section 9); until then the page rides the
  direct pull.
- **Installed (Sep 17, 04:08 UTC, on Mike's go).** Both bakers went to the VPS: `closures_bake.py`
  on its 30-minute timer (the first bake wrote 4,694 closures and 476 strips, 2 MB, 187 KB
  gzipped) and `amtrak_bake.py` as a loop service (no trains in the box at midnight, a 44-byte
  file). The live vhost, which had none of the example's per-feed blocks (its one `location /`
  serves every feed same-origin with `no-cache`), gained `location = /closures.json`
  (max-age 120) and `location = /amtrak.json` (max-age 15), both `gzip_static` with ACAO *
  for the Pages copy; `nginx -t` passed, the reload took, and the first curl after it still
  hit an old worker (the old headers for a second, then the new). The capture in
  `ops/philly3d.vhost.live` is the new live file.

## Round 81: the skyline's lighting theme, and lamps on the Ben Franklin Bridge (Sep 17)

- **Mike, with five photos: the skyscrapers and the Ben Franklin Bridge usually wear a light
  theme, almost always the colour of the team playing that day (Eagles first, then Phillies,
  Flyers, Sixers), otherwise BOMA Philadelphia's Building Illumination Calendar; add it, and
  put lampposts along the bridge at the photo's density.** His picks in planning: regular season
  and postseason count, home or away, preseason never; the calendar is baked into the page at
  every build and re-baked twice a day on the VPS.
- **The sources.** BOMA's page is Squarespace: `?format=json` returns the events collection
  (`upcoming` and `past`, 30 a page, `pagination.nextPageOffset` to walk it; 212 entries from
  December 2022 to November 2026, epoch-millisecond dates starting at Eastern midnight), the
  colour only in the title ("LIGHT UP BLUE!", "GREEN/WHITE/RED", "PINK & BLUE", "(BLUE/YELLOW)",
  and 69 titles with no colour word: "GO BIRDS!!!", "FLYERS HOME OPENER", "Breast Cancer
  Awareness"); no CORS header, so `fetch_lights.py` pages it and `bake_lights.py` parses it
  (the colour words in title order with aliases folded and a rainbow expanded, a team or cause
  keyword when the title names none, the lighting clause and the "(Copy)" duplicates stripped,
  dates as Philadelphia calendar days through `zoneinfo`, rows older than a year dropped): 94
  rows from the 212, nine titles dropped for naming no colour (Welcome Cherelle Parker, Election
  Day, World Smile Day and the like, all past). The DRPA publishes no bridge schedule, only a
  request form (the fan site's "lighting schedule" page has none either), so the bridge follows
  the same theme. ESPN's season schedules answer a browser (`teams/phi/schedule`) but run 0.8 to
  2.8 MB a league and list only the current season type (the NHL and NBA were in preseason on
  Sep 17), so the page reads the scoreboard for the day it is showing instead
  (`scoreboard?dates=YYYYMMDD`, 22 to 230 KB a league, every event carrying its
  `season.type`), four answers once per day viewed per session; curl gets 403 from ESPN, a
  browser does not, so the game days are the page's, never the VPS's.
- **What glows.** A themed crown is a `theme` flag in `towers.json` (`bake_towers.py`'s
  override table: the Comcast Center, both Liberty Places, BNY Mellon, Three Logan, FMC (given
  the `lit` it lacked), Cira, Two Logan, One South Broad, and the PECO Building with a new `band`
  crown, a 2.6 m LED band around the parapet that cuts nothing off the body); the CTC's blade
  and the PSFS sign keep their own colour, as Mike's skyline photo shows the CTC white while the
  city is green. Their lit parts, the Liberty Places' chevron trim (the eave bands and ridge
  caps, never lit before), City Hall's turrets, dome frusta, lantern and clock faces (mix 0.55
  and 0.3: floodlit metal, tinted amber faces) and the bridge's 160 cable boxes and suspenders
  ride one merged mesh, `themeParts` → `themeMat`: the vertex colour is the day colour,
  `aLit` the house night colour (what each glowed before), `aMix` how far the theme replaces
  it, `aSlot` which of the night's four colours (`mergeColored` carries the three attributes
  when any part has a `lit`), the emissive `mix(aLit, uTheme[slot], uThemeOn * aMix) * uNight *
  2.4`. Wash sheets (`themeSheets`: one additive mesh through `postRaw`, colours rewritten as
  the theme eases, MAX-blended over the facade) give BNY's lattice its glowing faces, the
  Comcast Center, Three Logan, FMC and Cira their lit crown floors, City Hall's shaft and clock
  stage the floodlit wash (weights 0.5 and 0.45, brighter at the foot and fading up: the
  first cut at 0.9 flat was an opaque green block), and the bridge's piers and legs theirs.
  A two-colour night deals the colours across the buildings in build order (One Liberty blue,
  Two Liberty pink) and in bands of ten panels along the bridge. 348 themed parts, 13 sheets.
- **The bridge.** 148 walkway lamps, one a panel a side outside the anchorage runs (12.3 m,
  the photo's spacing), a 4.2 m shaft with a lantern head as one instanced mesh that casts
  shadows, their heads warm LED points on the streetlamps' own material so they obey the G
  layer and civil dusk; 636 LED nodes every 6 m along each main cable and each floor edge (the
  first cut put the deck nodes on the walkway line, where they blended with the lamps into
  pinkish dots); the cable strings' house colour a pale white. The DRPA's own 2023 LED system
  runs the suspenders and cables and does colour effects, white by default.
- **The resolver and the clock.** `lightsThemeAt` (a pure block, `tests/test_lights_js.py`
  runs it under JavaScriptCore with the clock's DST helpers): the first team in the order whose
  day set holds the date, else the calendar row containing it with the shortest span (ties to
  the later start: a one-day request beats a month), else the house white. It follows the
  MODEL date like the markets, so a pinned clock shows that night's colour; the served
  `/lights.json` replaces the built-in copy when its `t` is newer. Changes ease twenty seconds
  (the haze's curve); a `?lights=<team|colour[,colour]|hex|off>` pin lands at once. The time
  panel gains "Lights: green, Go Birds", "Lights: teal, OCD Awareness Week", "Lights: white".
  The palette is sRGB and the emissive is linear (gotcha 11): the first build read mint, the
  colours now convert with `convertSRGBToLinear` and a luminance lift up to 2.2 for dim hues.
- **Found on the way.** BNY Mellon's lattice had stood inside its shaft since Round 54: a
  researched tower whose record is a glass-tower part (`t === 10`) was drawn to its full height
  on that branch instead of the crown datum `hTop`; it is cut now and the pyramid stands over
  the shaft with its mast.
- **Verified in the pane** with `?lights=eagles` at night: the skyline from South Philly (CTC
  white, the rest green), the Liberty chevrons, BNY's pyramid, the Logans, One South Broad's
  lantern, PECO's band, FMC and Cira, City Hall's wash, the bridge from the river and along the
  span (cables, suspenders, nodes, lamps, piers); `?lights=off` gives white strings and every
  crown its old colour; `pink,blue` deals the pair; noon shows nothing lit and white chevrons;
  the live path with the pane's hidden flag spoofed resolves Sep 17 to "red, Go Phils" once the
  scoreboard lands (the calendar's "blue, Pulmonary Fibrosis Awareness Month" until then),
  Sep 29 to "orange, Go Flyers" from the calendar, Oct 12 to "teal, OCD Awareness Week"; the
  phone viewport renders it without bloom. 11.9 M triangles and 387 calls at the skyline pose.
- **On the VPS (Sep 17, 04:52 UTC, Mike's pick).** `fetch_lights.py` and `bake_lights.py` in
  `/opt/philly3d`, `lights-bake.timer` every twelve hours (the first bake 94 rows, 8.8 KB, 2.3
  KB gzipped), `location = /lights.json` (max-age 600, ACAO * for the Pages copy) in the live
  vhost after a backup and `nginx -t`, captured back into `ops/philly3d.vhost.live`.
  97 tests pass (24 new: `test_lights_bake.py`, `test_lights_js.py`; `test_towers.py` learned
  the `band` crown, `test_build.py` the `LIGHTS_CAL` const). Page 26.65 MB (+35 KB). Devlog,
  handoff, DATA-LICENSE (a BOMA section, ESPN's scoreboards among the live feeds), README,
  CLAUDE.md, ops/README section 10, the credit lines and the About panel, the guide's card.

## Round 82: pins for the closed blocks, the markers and the art, and the half-mile rule (Sep 17)

- **Mike: add pins for the road closures, the Amtrak trains and the historical markers, and show
  only the markers within half a mile of the user for everything on the ground; boats and planes
  stay visible; asked which layers, he said SEPTA, Indego and every other ground-based item.**
  The trains had their badge since Round 80 (the aircraft casing with a train's face over the head
  car), so the new pins are the closed blocks', the markers' and the art's.
- **The pins.** One billboard recipe already served the flights, the ships, the SEPTA badges and
  the trains (a 256 by 320 canvas, the rounded badge over a pointer tip, a plane 4.6 by 5.75 m
  scaled with distance); `pinTexture(body, frame, paint)` and `pinMesh(tex, cap, key)` factor its
  casing and mesh (masked out of the bloom, depth-tested like the SEPTA badges: buildings occlude
  them) and three glyphs paint inside: a drum for a closed block (orange for a full closure,
  gold for a partial one, the card's own chip colours), the Commission's keystone in gold on PHMC
  blue for a marker, a plinth with its upright form on gold for an artwork. The pins ride their
  layer (the U key for the closures; the markers and art have no bit), sit 2.2 m over a block's
  midpoint and 3.2 m and 2.9 m over a post and a plinth, and take the SEPTA badges' size rule
  (dist/135, 2.2 to 14). Each is in the tap targets with its own pick list and opens the existing
  card; the screen-space fallbacks now walk the drawn records only, so a tap never opens a card
  for a post that is not there.
- **The half-mile rule.** `NEAR_R` 804.67 m and `nearCam(x, y, z)`, the straight-line distance to
  the eye, so the circle tightens with height: from 700 m up only what stands within about 400 m
  of the point below draws. SEPTA vehicles and badges gate in `updateTransit` (they keep moving
  unseen, the pick arrays in step); the Indego docks, bikes and badges in `indegoRebuild`, now run
  on the streetlights' cadence (900 ms or 220 m of travel) as well as per poll; the Amtrak cars and
  badge per car; the closures' drums and cones in `closuresReconcile` (2.5 km before), nearest
  first; the markers and art from a new 400 m cell map in `markersReconcile` (the static build of
  Round 77 became a camera-centred rebuild; the records keep the yaw `place()` gave them, which the
  build used to drop); the market tents in `updateMarkets(now)`, which now re-deals on camera
  movement as well as on the clock, the open list unchanged. The flights and ships never ask.
  `casterSig` counts the posts, plinths and drums so the shadow map follows them (the drums had
  cast stale shadows since Round 79, masked by the movers' cadence). `__dbg.near(m)` moves the
  radius, `__dbg.nearState()` counts what each layer draws.
- **Measured in the pane** by day over Old City with the live closures file: from 150 m, 57 closed
  blocks with their pins, 266 drums, 506 cones, 61 posts and 40 plinths each under a pin; from
  700 m over the same spot 14 blocks, 14 posts, 17 plinths; at 45 m 46 blocks, 59 posts, 36
  plinths; `near(250)` leaves 5 blocks, 2 posts, 9 plinths. Synthetic taps on a keystone pin, a
  plinth pin, a full closure's pin and a partial one's opened the PHMC, Art, Closed and Partly
  Closed cards. 99 tests pass (`tests/test_near.py`). Page 26.66 MB (+11 KB). Devlog, handoff,
  README, CLAUDE.md.

## Round 83: the markers and the art on their own layers (Sep 17)

- **Mike: add filter options for art, street closures, historical markers.** The closures had
  their row and the U key since Round 79; the markers and the art were always on with no bit
  (Round 77). Two rows after Street Closures now: Historical Markers (J, bit 4096, the count 348)
  and Public Art (O, bit 8192, the count 224), default on, in `layerFlags` / `setLayerFlags`, the
  reset map and the guide's Keys line. `LAYER_MASK_V4` 16384 marks a fourteen-bit link (4096
  alone still reads as a twelve-bit one, 1024 alone a ten-bit one; a new link carries the V4
  marker only, since 1024 and 4096 are layers in it), `parseHash` keeps 32767. The flags gate
  `markersReconcile` (Round 82's camera-centred rebuild), a toggle sets `markerReconAt` to 0 so
  the next frame re-deals, and a toggle off drops the open card. `tests/test_layers.py` pins the
  key order (the link format), the markers, the hash width, a row and key per layer and the reset
  map; `test_near.py` follows the gated reconcile line.
- **Measured in the pane:** clicks and the J and O keys (the first-visit guide holds the keyboard
  until its close button) take 61 posts and 40 plinths with their pins to 0 and back, the
  address bar's `l=` reads 32639 with both on and 20351 with both off, Reset Layers restores
  them. 101 tests pass. Page 26.66 MB (+2.6 KB). Devlog, handoff, README, CLAUDE.md.

## Round 84: the arena, the chevrons, City Hall whole, William Penn, Rocky, the Comcast bands (Sep 17)

- **Mike, with four photos across three messages:** the Xfinity Mobile Arena should be lit with
  the bridge and the skyscrapers; One Liberty Place needs its real lighting pattern and a closer
  massing (the photo: the neon tracing the sloping edges of every gable end, nested chevrons up
  to the white spire and its red beacon); the whole of City Hall lit, not the tower alone (his
  screenshot); William Penn closer to the postcard; the Rocky statue at the Art Museum steps; the
  two Comcast crowns more dynamic, several colours at once, their sections more accurate (the
  photo: the Comcast Center's crown and the top of the CTC's blade in red, white and blue bands);
  and more lights on the tall Center City towers that have none.
- **The chevrons.** `crown()` in the landmark block now runs a lit bar (`neon()`, a cylinder between
  two world points, radius 0.34) along both sloping edges of each gable end on all four faces of
  every tier (32 on One Liberty, 16 on Two), in themeParts at mix 1; the eave bands and ridge caps
  went back to unlit white trim. One Liberty's finial, mast and needle light white every night
  (mix 0) with a red beacon sphere at 288 m, and its shaft gained the four central bays 1.4 m
  proud of each face; Two Liberty's finial lights white. Verified by capture from the south-east
  at 230 m: the nested green chevrons, the white spire, the beacon.
- **City Hall whole.** A wash sheet round the block (149.6 by 144.6 m to +28, weight 0.45, floodlit
  from below), sheets on the four corner pavilions and the three centre ones, the wings' mansards
  and every pavilion cap floodlit at mix 0.5 like the dome. **William Penn** is 24 primitives now:
  the draped drum, buckled shoes, stockinged calves, breeches, the coat flaring to the knee with its
  buttoned front and sash, the shoulders, the cravat, the long hair behind the face, the broad brim
  and the domed crown, the left arm out over the city with its cuff and hand, the right down to the
  charter at the hip; stored very dark (0x221a10, the first two cuts read as pale tan under the
  lift, gotcha 11) and floodlit warm at mix 0.25 (a half read as a solid green figure).
- **Rocky** stands at `pt(101, -47)` of the museum frame, the foot of the steps on the right when
  you face the museum, on a two-tier granite plinth: boots, legs, trunks, torso, shoulders, head,
  both arms raised with the gloves; the first spot, `pt(106, -40)`, put him inside a street tree.
- **The arena** lights with the skyline: an LED band under the roof edge of the upper tier and a
  wash on its wall, its own slot. **The Comcast crowns:** the Comcast Center's notch grew from 8 to
  20 m and its wash became four stacked bands, the CTC's blade from 38 to 48 m with its top third
  in four bands and the rest white; the bands take slots `(tslot + k) % 4`, so a two-colour night
  alternates and a red, white and blue night reads red, white, blue, red from the bottom (the
  captured flag). **More lights:** `TALL_LIT_H` 120 in `bake_towers.py` gives every tower that tall
  without a night accent one, a `band` crown on a flat parapet or a strip on a notch, themed: 24
  bands, 38 lit and 37 themed towers (from 12 and 10). 451 themed parts, 28 wash sheets.
- **Measured in the pane:** the chevrons and spire, City Hall whole in green with Penn warm, the
  arena green from the south, the Comcast pair and the skyline under `red,white,blue`, Penn and
  Rocky by day up close. 101 tests pass. Page 26.67 MB (+9.5 KB). Devlog, handoff, README,
  CLAUDE.md.

## Round 85: the corridor made continuous, the station portals, the river bank, the Comcast and FMC lights (Sep 17)

- **Mike, with three screenshots and a photo:** the two Comcast crowns should light on Eagles days and
  every themed night, several colours, and look far better; the FMC Tower's signature look (a light
  line on every floor, the whole tower stacked bands); the railroad tracks broken all over the city;
  the roads on the river bank clipped; the tracks short of 30th Street Station; strips across the
  Schuylkill near 30th Street; verify none of it anywhere else. Then: fix everything found, verify,
  deploy. Ultracode: a workflow of five investigators (the rail data, the rail code, the river-bank
  roads, the station's geometry, the lighting design) with a completeness critic, and the pane.
- **What was actually broken.** The data was almost perfectly stitched (1,400 of 1,426 endpoints
  shared exactly, 29 switch nodes) and no untagged way lay on the water. The breaks were the code's:
  every OSM way took its own height pass (a one-sided smoothing window at each end, so the shared
  node had two heights: 507 of 646 joints stepped 0.3 m or more, 254 a metre, 29 four metres), a
  short way collapsed to a shelf at its own mean, every bridge-tagged way was held flat at its
  higher abutment AND floored at 9 m over the water whether or not it crossed any (63 street
  overbridges lifted, 24 by more than 3 m, every one a vertical drop at both ends), the 20 m boxes
  showed open faces at every step, and the slab rode the bilinear DEM while the eye sees the drawn
  mesh. The "strips across the river" were the bridge ways themselves, flat grey ribbons 14 to 16 m
  over the water with nothing under them, one track's middle piece 5 m lower than its neighbour. The
  tracks stopped short because OSM tags the lower level from Chestnut Street to the parking podium
  tunnel=yes and the step drew nothing tunnel-flagged; the DEM reads the whole block as the
  concourse plateau, 7 m above the approaches, so the last 30 m of each approach was buried too.
- **The corridor now.** The ways are stitched into 57 chains by half-metre node keys; each chain is
  sampled at 20 m on the drawn ground (`groundMeshLandY`, the DEM where the mesh is absent); every
  run that is bridge-tagged or inside the Schuylkill's outline is one span ramped between its two
  abutments (never an interior ground reading, never flat at the higher end), floored 9 m over the
  water only when it is wet, its approaches climbing over eight samples; the chain ends are pinned
  to the height every chain at that node shares (0.00 m steps at all 29 junctions in the replay); the
  free points smooth twice. Each chain is one ribbon, mitred at every bend, with a skirt from its
  edges down to the drawn ground (an embankment reading, never a floating slab), rails on desktop,
  and under every bridge run a 1.4 m steel deck with a pier every other segment down to the ground
  or to the riverbed. 713 lines, 57 chains, 10,539 segments drawn.
- **30th Street.** The station's centre is (-3197, -1158), not the (-3200, -840) the code carried
  (that is the IRS block). The covered points inside the station box take flag 4 and a straight
  lower-level grade between the approaches, held 60 m out from each portal; they are drawn (under the
  plateau, visible only in the cuts) and the trains ride through them. Two open cuts (`RAIL_CUTS`:
  south, 62 by 62 m from Chestnut Street to the old Post Office's face, floor -4.3; north, 86 by 26 m
  at the parking podium's face, floor -4.2) join `cutHole`, so the wide ground opens over them; the
  rail step lays their floors, side walls to the plateau, grass collars over the opened cells, and a
  headwall at each closed end with a near-black recessed mouth spanning the tracks. Verified from the
  north cut: the tracks converge into the dark mouth under the podium's headwall.
- **The river bank.** Three mechanisms, all from the river-roads investigator's replay: the
  tunnel-tagged I-76 pair on the west bank was drawn as slabs through the carved bank (covered
  sunken chains now draw only where they stand clear of the drawn ground, with a face down to the
  bed); a road within the 40 m bank carve read the carved slope and sawtoothed between water + 0.9
  and + 4.5 every 15 m (`groundMeshLandY` returns null under water + 0.85 or inside the carve band,
  so a bank road stands on the DEM, and no non-deck roadway sits under water + 1.2); and
  `bake_overpasses.py` tested over-water against the pre-Round-49 hand polyline, a kilometre west of
  the river through Center City, so the Vine, JFK and Chestnut crossings solved 5 to 8 m over the
  water (the bake now tests the river's own outline and floors its touch-downs at water + 1.4; el 63
  8.5, el 91 8.2, el 178 6.4 where they were 5.0, 6.2 and 0.6). The paved yards never crossed the
  river.
- **The lights.** The FMC Tower carries an LED line on every floor edge of its real footprint
  (`led` in towers.json; `ledRing` rings the polygon, the OBB slab floated 3 m off its rounded
  corners), slots cycling in blocks of five floors so a flag night stacks, and a white sign bar on
  each long face; the Comcast Center's crown is an LED line proud of every crown floor on the style
  25 pitch of 4.15 m with a dim wash between (the roof strip now caps the drawn crown block; it used
  to sit 25 m past the recessed face); the CTC's fin is 0.72 of the long axis and 0.08 of the short,
  a dark body behind a ladder of light bars every 1.6 m, every bar in the night's colour and the top
  third cycling a many-colour night; thin LED parts carry `aGain` 1.6 through `mergeColored` and the
  theme shader so a line has the radiance a wash box has. 534 themed parts. Verified: the FMC as
  stacked green bands from the South Street bridge, the Comcast pair in green and in red, white and
  blue.
- **The critique pass (the workflow's completeness critic and six follow-ups, then a citywide survey in the
  pane: every open rail sample against the drawn ground, `__dbg.railSnap` and `__dbg.groundAt` on a 20 m
  grid, 6,283 samples).** What the first build still had: 508 samples under the drawn ground and 202 more
  than a metre under, on the North Philadelphia and Frankford viaducts, the Torresdale reach and the
  Manayunk line, because a bridge-tagged run was ramped straight between its abutments while the bare-earth
  DEM carries the earth fill between the actual bridges, and because the smoothing pulled the free points
  under every crest (the wedges surfacing through the grass at Powelton Yard); the new road floor firing
  on every road on land under 1.1 m ASL citywide (FDR Park, the sports complex at -1.6 m ASL, the airport:
  a 0.75 m shelf with the traffic under it); the bank roads standing on the DEM with up to 6 m of air over
  the carved slope; the ballast skirt bottoming at the DEM over the same carve; a chain end pinned by
  `max` to a neighbour's approach lift; the rail cut's grass collar burying Schuylkill Avenue's ramp; the
  covered I-76 slab drawn wherever the ground is holed; a train's badge hidden in the station shed; a
  pier every 40 m wherever the deck stands, a street's carriageway included; and, from the rail-data
  investigator, Norfolk Southern's Harrisburg Line (36 freight ways, 21 km up the Schuylkill's east bank
  from East Falls through Manayunk to the city line) matched by the bake's name clause since Round 80:
  no Amtrak train runs on it. Fixed: every span and every free point floors at the drawn ground + 0.45
  (a fill carries the ballast; the deck and piers are skipped where the deck would sit within 1.2 m of the
  ground, a pier within 8 m of a street's centreline too); a node's height is a span's or the shed's where
  one ends there, else the ground reading every chain shares; the skirt reaches the drawn mesh, carve
  included; the road floor and a new quay skirt (from each ribbon edge down to the drawn mesh, in the road's
  colour at 0.7, lane class 2) apply within 60 m of the Schuylkill's outline only, the typical traffic
  taking the same floor; the collar dips 0.7 m under any baked deck it crosses; a holed cell counts as
  the DEM's ground for the covered slabs; the badge rides the shed with the cars; the decks, piers, cut
  walls, headwalls and mouths sit on their own shadow-casting mesh; `bake_rail.py` drops any way whose
  operator tag is not Amtrak's (677 lines, 191.8 km, from 713 and 213.2). After: 5,328 open samples, six
  under the drawn ground and all six inside the two station cuts where the track is meant to be, 17
  standing over 3 m (approach embankments, skirted), the steepest 20 m 11 percent on the Grays Ferry
  approach where the bank itself climbs. `__dbg.rail()` now reports `under`, `underMax`, `floatMax` and
  `grade` from the step's own profiles (16, 6.5 m in the cuts, 4.1 m, 17 percent at the cut floors).
- **The follow-ups' refinements, taken.** The bank floor is one function, `bankFloor(x, z)`: water + 1.2
  inside the Schuylkill's outline, eased to the low-land datum across the 40 m carve band, nothing beyond,
  read by both road loops, the typical traffic, the closures' drums and the SEPTA vehicles, and mirrored in
  `bake_overpasses.py` (`sch_bank`, so the eleven off-river touch-downs the first bake had lifted, FDR
  Park's path bridges among them, return to grade + 0.3). A quay skirt samples the drawn mesh at the
  chord's quarter points as well as its ends (516 m of daylight under a straight bottom in the replay,
  none after). The overpasses' skirts and pier feet, and the rail bridges' pier feet, reach the drawn
  mesh, carve included (25 deck points and 53 piers had hovered up to 9.6 m over the carved bank). A
  node's height is the mean of the span or shed ends meeting there, else the shared ground reading (the
  max had pinned two shed heads to the concourse plateau, a 6 m face inside the south cut). The shed grade
  anchors to the first and last samples inside a cut at that cut's floor + 0.45, and the open stubs within
  40 m of a cut join the shed rule, so the rails ride 0.3 m proud of the slab on every track. A train at
  the platforms carries its badge over the concourse. The bake floors an elevated deck at its DEM + 0.45
  (Schuylkill Avenue's ramp had solved 1.7 to 4.2 m under the drawn ground because the slope limit could not
  climb the concourse's rise; seven short at-grade pieces now clear the ground and are kept).
- **The cuts, reworked from the last follow-up.** The side walls had stood flat at the concourse height
  while the yard beside them lies up to 8 m lower, a freestanding walled trench; they now follow the ground
  outside them in 10 m pieces from nothing at the open end to the full retaining wall at the headwall
  (the south cut's head from the DEM at the headwall, 3.2, not 4.0). cutHole drops a whole 25 m cell when
  any corner lies within a metre of the box, so the apron is a ring of 28 m collars centred 15 m outside
  every edge, built as sheets that follow the ground at every vertex (a ribbon is flat across its width,
  and a grade road beside it poked through on the cross slope), the open end's under the ballast where
  the tracks cross it, the headwall's over the shed's drawn strips; a collar dips under a deck that
  crosses it by 0.7 m but never more than 0.6 m under its own ground. The mouth is the full inner width,
  so the two outer tracks enter it instead of the wall. A deck over a cut (Chestnut Street) stands on
  piers to the cut floor. Verified from over Chestnut looking into the cut, from the yard at the headwall,
  from the plateau into the north cut and from the east across its apron.
- **The stripe palette (the critic's fourth gap, the follow-up's design).** On a team night the resolver
  hands one colour and all four slots took it, so every Round 85 per-floor deal collapsed to solid green on
  precisely the Eagles nights Mike named. The skyline rule stands (Round 81's photo: the city green, the
  CTC white), so the striped LED parts alone take a second bank: a part whose slot is 4 or more is a
  stripe index (`4 + tslot + k`), the shader reduces it by the live palette's length (`uStripe0..3`,
  `uStripeN`), and `LIGHT_TEAMS` carries each team's pair: green and white for the Eagles, red and white
  for the Phillies, orange and white for the Flyers, blue, red and white for the Sixers (a three-colour
  palette cycles three, no doubled first colour). A calendar night or a pin deals its own colours to the
  stripes, so Round 84's flag capture reads exactly as it did; the label still names the skyline. The
  contents of the four palettes are a guess at how Philadelphia lights and Mike's to change.
- **Found and left, reported to Mike.** Kelly Drive on the far ring (East Park, about (-4230, -3480)) has
  a road ribbon that dips through a hillside and steps where it re-emerges. An A/B against the deployed
  build at the same pose is pixel for pixel the same: the far ring's 50 m ground grid against the roads'
  30 m chords on a steep bank, a level-of-detail matter of the far ring since it was built, not a broken
  join and not this round's. The road loops sample every vertex straight off the drawn ground, so the
  rails' shared-node fix has no road equivalent to make.
- 101 tests pass (tests/test_lights_js.py knows the stripes). Page 26.70 MB (+29 KB). Devlog, handoff, README, CLAUDE.md, the About panel.

## Round 86: the Amtrak card links to the train, not the tracker (Sep 17)

- **Mike: change the Amtrak links to go to that specific train on railrat.net.** Round 80 gave the
  train card Amtrak's own `track-your-train.html`, which is the tracker's front door: it names no
  train, so the reader arrives at a map and has to find the train again. RailRat (unofficial,
  sourced from Amtrak's Track Your Train map) publishes one page per scheduled train number at
  `railrat.net/trains/<num>/`, so the card now points there: `encodeURIComponent(p.num)` in the
  href, `septaEsc(p.num)` in the text, "Track Train 655 on RailRat". One line in `amtrakCard`,
  matching how the flight and ship cards hand off to FlightAware and MarineTraffic.
- **Coverage checked before the switch, not assumed.** RailRat carries the scheduled numbers only,
  not every number in a range: 2151 answers 200 and 2170 and 2253 are 404s, which is why the
  `__dbg.amtrakTest()` fixture's invented Acela 2170 became 2151, a real run. Every number the live
  feed carried at the time of the change (171 Northeast Regional, 609 and 650 Keystone, 2158 and
  2159 Acela) resolves, as do the four fixture trains (192, 2151, 655, 90). Amtraker reports trains
  that are actually running, so their numbers are scheduled numbers; an empty `num` degrades to
  `railrat.net/trains//`, which serves the index rather than a 404.
- **Credits unchanged.** Amtraker stays the data source in the card line, the About panel and
  DATA-LICENSE; RailRat is an outbound tracking link and is credited nowhere, exactly as
  FlightAware and MarineTraffic are not.
- Verified in the pane: `cardFor` on all four fixture trains returns the per-train href, no
  `amtrak.com` remains anywhere in the document, and the Acela card reads "TRACK TRAIN 2151 ON
  RAILRAT". 101 tests pass. Page 26.70 MB (+18 bytes).

## Round 87: the parks planted, the far ring's colour seam closed, the trains stopped jumping, the credit line retired (Sep 17)

**Mike, with three screenshots of the Fairmount Park reach, the 30th Street cut and a high oblique
over the Northeast: "This section of the model still is very broken. The streets and train tracks
are all broken up, the trains jump around when they are on the tracks. Tree coverage is not
correct. The tracks need to go all the way into the tunnel under 30th st station and overall this
entire area needs work." And: "There is still a distinct difference from the buildings colored with
mapillary data and those that arent. we need to get that closer to one another." Mid-round: "remove
the copyright data at the bottom of the screen. That can live in the info panel."**

Five investigators over the five subsystems, then the fixes and a capture pass. Every number below
is measured, before and after, not estimated.

### The colour seam: Round 68's gain was spending itself on the clamp

`__dbg.colStats()` across the York Street band, the same rowhouse neighbourhood 700 m either side
of the wide tier's edge:

| population | before | after | note |
|---|---|---|---|
| `wideBand` (outer districts) | 0.508 | 0.510 | untouched |
| `farBand` (far ring) | **0.821** | **0.497** | the step across the boundary: +62% to −2.5% |
| `wideBandCap` | 0.228 | 0.228 | |
| `farBandCap` | **0.377** | **0.257** | +65% to +13% |
| `widePhoto` (Mapillary) | **0.420** | **0.477** | |
| `widePlain` (fallback) | 0.496 | 0.496 | |
| photo against fallback | **−15.4%** | **−3.8%** | |
| `far` tier / `wide` tier | 0.816 / 0.480 | 0.494 / 0.492 | +70% to +0.4% |

`FAR_LIGHT` 1.8 with `FAR_DESAT` 0.15 went in Round 68 because from over East Park the far side
rendered a third darker (masked building pixels 116 against 154). It was compensating a structural
difference with a colour error, and paying for it twice: at 1.8 the per-channel `Math.min(1, …)`
pinned **81.8% of the far ring's red channels at exactly 1.0** and crushed the tier's red spread
from 0.101 to 0.073, which is arithmetically the uniform pale salmon Mike photographed, and 6.3% of
the reservoir came out pure white, drawn per merged block strip at a 366 m² mean footprint, which is
the white patches. The old comment admitted it: "the register saturates, so the gain runs ahead of
the read."

So the walls take **no gain at all** (`FAR_LIGHT` 1.0): the 1,024-colour reservoir already holds the
outer districts' own final colours, so 1.0 is an exact statistical match by construction. What was
real in Round 68's reading is the roof **caps** — `city.b64`'s roof words draw a darker set of
`ROOF_PAL` entries than `wide.b64`'s, 0.202 against 0.248, and the far ring is merged block strips
with wall-to-wall roofs seen from above — so `FAR_CAP_LIGHT` 1.23 matches the two tiers' cap means
instead of lifting the whole city 80%. `farGain` keeps a monotone soft knee above 0.8 in place of
the clamp, so any future gain never flattens hue. The structural half of Round 68's problem is
closed by this round's trees, which is what it was really looking at.

Within the outer districts, three constants in `wallInv`, all measured by sweep:

- `WALL_LIFT` 0.56 → **0.45**. The only knob that moves luminance; 0.42 closes the gap to nothing
  and 0.45 leaves the photographs a shade darker than the invented colours, which is the direction
  the measurement should win.
- `WALL_FOLD_MAX`, new, **0.6**. The cool-cast fold was capped at 1 and with the divisor at
  `0.12 * lum` it saturated for every cool palette entry: **14 of the 32 folded to exactly zero
  chroma and painted 8,145 buildings flat neutral grey**, a quarter darker than the brick around
  them. Those are the grey patches. Raising the divisor is measured dead (0.12 → 0.50 moves 8,145
  to 7,895, because `f` still saturates); the cap is what has to move.
- `WALL_WARM` 1.6 → **1.3**. At 1.6 the blue channel clipped to zero on six entries (`#643c27`
  reached chroma 0.79), which is where the photographed population's saturation spread of 0.185
  against the fallback's 0.099 came from.

The three populations now sit inside 4% of one another in the register, against 94.5% before.

### Tree coverage: the survey was clipped to the wide box

`fetch_trees.py` fetched the wide tier's envelope only and `pack_trees.py` clipped to the same box,
so **West Fairmount Park held 0 trees** and East Park 572 (2.3/ha against 150 to 400 in real closed
canopy) — those 572 being the Kelly Drive rows. Everything past x = −3700 stood bare: West
Philadelphia, Southwest, the Northeast, and every park in them. The fetch is now the whole city:
**151,726 trees against 50,073**, and the packer keeps 150,887 of them (49,038 in the wide box,
101,849 beyond it). The PPR 2025 inventory turns out to cover park interiors, not only streets, so
West Fairmount Park goes from 0 to **11,229** trees and East Park from 572 to **8,264** — real
surveyed positions, so no procedural fill was needed.

Two things had to move for it. The blob's quantum: int16 at 0.2 m saturates at ±6,553 m and the city
reaches x = 15,871 and z = −21,229, so a widened clip would have tripped the packer's own assert.
It is **0.7 m** now, poles.b64's quantum, and the header's fourth slot (a zero until now) carries
the unit in millimetres so the decoder never guesses. And the page needed a third tree tier: the
wide box keeps its full forest on the 3×3 chunk grid, and the trees beyond it draw on an 8×8 grid
over the city, one crown and one trunk mesh per non-empty chunk so each culls whole.

The outer crown is the 20-face icosahedron phones have had since Round 58, not the wide tier's
80-face one. That was measured, not assumed: the wide tier's crown on all 101,849 outer trees cost
**18.0 M triangles** a frame at the skyline, park and seam poses against 13.4 M this way and 11.9 M
before the round. `canMat` does the rest — its per-vertex random scale lumps every crown and its
3D-noise mottle breaks up the facets — so the tiers differ in smoothness, not in character. A
per-chunk detail swap on camera distance would buy the near ones back and is the obvious next step.

Raising the survey citywide exposed a law tuned on street trees: `boleH`, the trunk height, was
capped at 5.2 m, and the parks brought trees of 40 to 60 inches whose crown radius clamps at 7.5 m.
Held to a 5.2 m bole their crowns reached within centimetres of the grass (the canopy shader's
per-vertex scale runs to 1.21) and read as boulders lying in the field. The cap is **9 m** now, so a
60-inch oak carries its crown 2.6 m clear. Street trees are unaffected: their dbh never binds the
new cap, and the wide-tier close-up is pixel-identical before and after.

The **woodland tint** now reaches the whole city. `nwParkAt` is built from PPR's own parkland rings
and has always been citywide (West Fairmount Park 4.72 km², East Fairmount 2.34, the Wissahickon
6.71), but the only `mkFarGround` call that asked for a tint was the NW patch, whose box stops at
z = −6600 — north of almost the whole park. The four far strips now carry it too, on a separate flag
from the NW creek-bed drop that used to share it. Measured straight down from 500 m: West Park's
ground reads **[59, 75, 45]** against **[74, 87, 60]** for non-park ground beyond it, 17% darker.

### The Amtrak corridor and the 30th Street cut: two bugs, both in flag handling

`hidden` segments **89 → 37**, drawn 9,499 → 9,559.

The corridor's flags were the OR of both endpoints of a chord applied to every 20 m sample of it,
and at a stitched joint one endpoint belongs to the neighbouring way — so a tunnel bit walked
backwards over a whole simplified chord. Six tunnels of 32 to 223 m in Fairmount Park became six
undrawn holes of 81 to 266 m, **1,130 m in all**, which is what left isolated strips of 12, 89 and
260 m between the Zoo and Belmont. An AND is not the fix either: tried first, it cost a covered run
its first and last sample and surfaced the station's lower level 7.6 m mid-concourse (`__dbg.rail()`
reported a 38.7% grade at (−3206, −954), which is how it was caught). A chain now carries its
flags **per segment**, taken from the way each segment belongs to, and nothing bleeds in either
direction.

The tracks stopped short of the portals because the `shed` predicate's window was hand-typed as
`z > -1380 && z < -830` and **it cut through both cut footprints** (south z −870.8…−795.2, north
−1396…−1370). A covered sample in the excluded half never got flag 4, so `hidden()` dropped its
whole run: **889 m of track went undrawn and all eight tracks stopped 7 to 36 m short of the mouth**
with bare cut floor in front, which is exactly Mike's screenshot. `RAIL_STATION` spans Chestnut
Street to the podium and contains both cuts whole. `under` rises 20 → 34 and both readings are at
(−3202, −839), the south cut: more of the covered level is drawn under the plateau now, which is the
point.

`RAIL_LIFT`, new, **0.75** where the floor was 0.45: the ballast top sat 0.20 m over the ground and
the railhead 0.36, and half the park corridor's samples were within 0.25 m of the mesh, so the
surviving track read as pale strips lying on the grass rather than a roadbed on a skirt.

### The trains

Four causes, all measured:

- **`AMTRAK_RUN` 240 → 480 s.** This was the jumping. Round 80's own measurements have Amtraker's
  fixes arriving 171 to 201 s old and about 224 s apart, so when a fix lands the previous one needs
  roughly 409 s of reckoning behind it. Capped at 240 the head ran out 55 s after each fix, **sat
  parked for the remaining 169 s, then teleported by 169 × v** when the next one arrived: 605 m at
  8 mph, 4.5 km at 60 mph, over the 600 m snap threshold for every train that was moving at all.
  `AMTRAK_SNAP` comes down to 400 m, `adv` is signed so a head that has run ahead backs up instead
  of waiting, the catch-up rate is clamped to half the train's own speed plus 5 m/s, and the speed
  eases out over `AMTRAK_FADE` 60 s instead of switching off in one frame.
- **The consist hopped tracks.** `railWalk`'s step was 30 m, so one 24 to 27 m coupling walk was a
  single straight chord followed by a free nearest-track snap, and the corridor's tracks sit a median
  4.0 m apart with 73% of close neighbours on different chains. A 13° bend threw the tail 5.5 m
  sideways onto the parallel track; simulated over the real grid that put 12 to 22% of a curving
  consist's cars on another chain, changing membership every frame, with 377 tunnel-flag mismatches
  blinking cars out of existence and bridge-flag flips stepping them metres vertically. `railSegs`
  carries the chain now, `railSnap` takes a `prefer` chain with a 1.5 m margin, and `RAIL_STEP` is
  6 m, which holds the overshoot under 1.4 m at the worst bend in the corridor. Verified with the
  new `__dbg.railWalk` probe: **every car of all four `amtrakTest` fixtures stays on the head's
  chain, 0 off-chain against 12 to 22% before.**
- **The render loop's dt clamp.** Trains integrated against `Math.min(rawMs / 1000, 0.05)`, so at
  15 fps a train advanced at three quarters of its true speed and at 10 fps at half, and the head
  fell behind its own target by 0.25 to 0.5 v a second and crossed the snap threshold unaided. The
  half-mile rule means trains only draw when the camera is close, which is when the frame rate is
  lowest. They keep their own real-time delta now, capped at a second.
- **The direction was a sign.** A sign is only meaningful against the chain it was measured on, and
  686 of the corridor's 2,351 near-parallel neighbour pairs are stored in opposite point order, so a
  fix that snapped to the 4 m neighbour under GPS noise could apply the old sign to a chain running
  the other way and walk the train backwards by twice its reckoning, consist reversed. It is a world
  unit vector now, re-derived against each new chain's tangent. `AMTRAK_HDG` also gained the eight
  16-point compass keys it was missing, which had been yielding no direction at all for NNE, ENE and
  their kin. And the direct Amtraker fallback now carries the clock offset the baked path learns,
  so a skewed client clock no longer biases the whole reckoning by S × v.

Head motion over 60 real-time frames: max step 1.41 m, max Δy 0.10 m, zero tunnel flips, on all four
fixtures.

### The far ring's roads

Not finished this round, and the reason is in the next section. Four fixes did land, all free:

- **The bank band's 6.7 m step.** `groundMeshLandY` handed a road inside the Schuylkill's 40 m
  carve to the DEM (Round 85, so a bank road would not follow the carved slope down to the water),
  but it switched at the band edge, and the DEM is smeared 150 m there and stands 3.5 m over the
  carved ground at the median and 12.5 m at the worst. One 30 m interval of Kelly Drive stepped
  6.7 m. The two reads are now mixed over `BANK_BLEND` 30 m, so they meet in a ramp.
- **Unmitred joints.** The far ring laid its fan disc at interior bends only, so where two OSM ways
  met at a node the ribbons butted together square and the grass showed through the corner, up to
  7.86 m of it in the park. A run's ends now take a disc too, and only where another run really ends
  there (240 of the park's 333 endpoint keys are shared), so a genuine dangling end stays square.
- **Far-ring traffic rode the raw DEM** while its own road ribbon read the drawn mesh. Same read now.
- `__dbg.railWalk` joins the probe list.

### What is not done

The far ring never fetched `unclassified`, `living_street` or `pedestrian` — and in Fairmount Park
those ARE the connecting drives: Lemon Hill Drive, Waterworks Drive, Aquarium Drive and Sedgley
Drive are all `unclassified`. Measured over the park's own rings, the far ring's class list carries
**68% of the road length against the wide tier's 90%**, and **84 of its 333 run endpoints (25%) are
true dangling ends**, a median 27 m from the nearest other road. That is the "road just stops in the
grass" in the screenshot, and it is the one part of Mike's first message this round does not fix.

`fetch_city_streets.py` and the `pack_city.py` merge are written and the classes are wired
(`RT` gains `unclassified` and `living_street` at width 7 and `pedestrian` at 5, `LOCAL_CLASSES`
cuts all of them out of the wide box so the two tiers never pave the same street twice). It is a
supplement rather than a wider `fetch_city.py` query on purpose: the 92 tiles in `city_tiles/` are
keyed by tile name and not by query, so widening that query means refetching 510 MB of buildings,
parks and water to get a few megabytes of streets. Overpass throttled the envelope badly (tiles
alternating between 1 s and 240 s) but ran to completion in about two hours.

Two lessons worth keeping: a tile cache keyed by name and not by query is a trap, and
`fetch_trees.py`'s page cache now carries a hash of its envelope for exactly that reason; and
`out geom` instead of an `out body` with the node recursion took a tile from minutes to seconds.

### The credit line

**Mike, mid-round: remove the copyright data at the bottom of the screen, it can live in the info
panel.** `#osmcredit` is gone on every device, which extends Round 69's phone decision to the
desktop, and `#guideCredits` — the guide's "Credits" link, which was the phone path — now shows at
every width. The About panel is the home, and it is reachable by that link and by the `i` key; the
`i` button stays out of the bar, as it has since Round 53. Checked before removing anything: every
source the bottom line named is already credited in the panel, and the panel's formal `.credits`
block gained the five it was carrying only in prose (the Streets Department's closure permits, the
PHMC markers, Percent for Art, the basemap Landmarks, Amtraker, Air Management Services and
Ticketmaster), so the attribution of record is complete in one place. ODbL asks for the notice in
the Produced Work, not on the screen at all times.

- Verified by capture at the same poses as the screenshots: the York Street seam reads as one city,
  West Fairmount Park is planted and tinted, the Zoo corridor runs unbroken, both 30th Street
  portals take the rails into the dark, the wide tier's street trees are unchanged. Triangles
  **13.4 to 13.6 M** at the skyline, park and seam poses against 11.9 M in Round 84, 372 to 484
  draw calls. 101 tests pass (`tests/_common.walk_trees` reads the header's unit;
  `test_blobs.test_tree_names_consistent` asserts the city box, no saturation, and more than 50,000
  trees past the wide box so the far ring cannot go bare again). Page 27.80 MB (+1.10 MB, the tree
  blob). Devlog Round 87, handoff, README, CLAUDE.md, DATA-LICENSE, the About panel.

### Round 87 coda: the park's drives (same day)

The fetch finished: 92 tiles, **584 ways** (417 `unclassified`, 155 `pedestrian`, 12
`living_street`, 539 KB), and `city.b64` repacked to **24,171 road runs from 23,643**, 10.21 MB
base64 from 10.20. In the two Fairmount Park rings the far ring now draws **60.0 km of road against
50.2 km, 382 runs against 317**, and the names are the ones that were missing: Lansdowne Drive,
Horticultural Drive, Belmont Mansion Drive, Chamounix Drive, States Drive, Cedar Grove Drive,
Sweetbriar Lane, South Georges Hill Drive, Zoological Drive, Lemon Hill Drive, Sedgley Drive.

One correction to the investigation that produced this, worth recording because it changes what the
fix was for. The report framed it as dangling ends: "84 of 333 run endpoints (25%) are true dangling
ends, a median 27.3 m from the nearest other road." Measured inside the park rings rather than over
a box, and against the nearest vertex of any **other run** rather than against other endpoints, the
median distance from a run end to another road was **0.0 m before the change** — the network was not
disconnected, it was **thin**. Ends more than 15 m from another road went 11 → 31 of 685, because the
new drives terminate where `service` roads and footpaths meet them and neither tier carries those
(`pack_wide.py` drops `service` too, and keeping the tiers' class sets identical is the point). So
this round added 9.8 km of real park drives and about twenty new stubs with them; it did not close
the stubs, and the honest read of the screenshot is that the park was under-roaded, not unstitched.

Page 27.82 MB (+17 KB). 101 tests pass. Triangles unchanged at 13.4 to 13.6 M: roads are cheap.

### Round 87 coda 2: GitHub Pages retired, and how to push from this laptop (same day)

**Mike: "This project no longer needs GH Pages. The site should always be most updated at
philly3d.com."** So the Pages copy is out of the deploy ritual: CLAUDE.md, the README's header,
`deploy_philly3d.sh`'s comment and `build.py`'s docstring no longer name it, and CLAUDE.md's
standing instruction to "verify Pages by grepping the tail of the page" is gone, since it would
have sent a future round waiting on a build nobody reads. The page is still committed as the
artifact of record and `git push` still runs, for the history.

Left in place deliberately, because they are cheap and harmless and removing them is a change to
a live host: `3d-model/index.html` (the Pages `start_url` redirect), and the `ACAO *` headers on
the VPS's per-feed location blocks, which the Pages copy needed to read `closures.json`,
`amtrak.json` and `lights.json` cross-origin. Flagged for Mike rather than removed.

And the push itself, which cost this round an hour of wrong diagnosis. `git push` fails from a
non-interactive shell because `origin` is **HTTPS** and the osxkeychain helper returns nothing
there. I read `~/.ssh/config` mapping `harkdigital_laptop` to `lionspool-vps` and concluded it was
a VPS-only key, and proposed generating a new deploy key; Mike pointed out the repo has had a
read/write deploy key called `philly3d-laptop` since Aug 26. Its fingerprint
(`SHA256:p0kArEXJu5Vy8Agbkgjgd5FgidNCzTJS5xdV+Ztgr7U`) **is** `harkdigital_laptop` — the one key
authorizes both the VPS and this repo. What actually blocked SSH was the `Host github.com` block
pinning the unrelated **Phade** deploy key with `IdentitiesOnly yes`, so ssh never offered the
right key to github.com. Two repo-scoped deploy keys cannot share one `Host github.com` entry, so
the fix is an alias: `Host github-sht` with `IdentityFile ~/.ssh/harkdigital_laptop`, and a second
remote `gh-ssh` pointing at it. `origin` stays HTTPS on purpose, because this checkout lives in
Dropbox and a machine-local alias in `.git/config` would follow it to the other Mac and break
there. The key I had generated was deleted unused.

## Round 88: the roads painted on the ground, the inner tier's rowhouses back in brick, the lamps on an overcast dusk, the bar at the top (Sep 17)

**Mike, with a screenshot of the Passyunk Avenue interchange at dusk: "The scene at
`#p=-4486.3,354.9,2650.5,1.675,-0.601` is terrible. This is what I am talking about. We cannot
have roads cutting off like this. If the elevation is such that it is going to cause clipping,
the road needs to be painted just above that elevation. You have the data, make it happen. The
disparity between the inner and outer ring needs to be lessened. This is way off. Move the
buttons to the top of the screen and make them yellow to match the logo. The time of day button
should have a sun icon on it. At this hour of day the street lights are on in the real
Philadelphia so they should be here as well. What time do you have them set to come on?" Then,
through the round: the red reads as pink, make it a vibrant Phillies red; the moon is hidden by
cloud but the moonlight still comes through; it is not that cloudy in Philly, where does the
cloud cover come from; the stadiums are orange, they should be lit normally with no colour hue;
lamp posts on the Walt Whitman like the Ben Franklin's, no colour lights; the Stateside Live pin
is on the casino, Stateside Live is at the south-west corner of 11th and Pattison.**

Every number below is measured in the pane before and after, on this laptop, with the deployed
build as the baseline.

### The interchange: three faults on top of each other

The screenshot showed I-76's carriageways and the Passyunk and 26th Street ramps as tilted
slabs cut off in the grass, with the streetlamps standing in a line where the road should have
been. Three separate things were wrong there, and each of them was citywide.

**1. The seam gap.** The far ring skipped every segment with both ends within 200 m of the wide
box on the assumption that the wide set paves that margin (`pack_wide`'s `runs_of(..., 200)`
carries a way 200 m past the box). But the wide extract only holds ways that ENTER its box
(`fetch_wide.py`'s bbox is the box itself), so a road running alongside the edge inside the
margin was in neither tier. Decoding both blobs offline and testing every ceded far-ring segment
against a 40 m grid of the wide segments: **21.1 km of road ceded to a tier that does not carry
it**, 5.74 km of it motorway (86 segments), 7.43 km primary and secondary, 5.97 km residential.
Nothing strictly inside the box was lost. I-76 between x -3900 and -3811 at Passyunk is in that
band, which is why it stopped dead. `wideRoadAdd` now indexes the wide loop's raw segments and
the far ring cedes a margin segment only where `wideOwned` finds a direction-aligned wide segment
within 3 m of both ends and the midpoint (the same shape as `ovpOwned`; 3 m for the two packers'
simplification tolerances). Inside the box itself the old unconditional skip stands, measured
safe. The packer had the same gap one layer down: `pack_city.py` cut the local classes out of the
box's 150 m band whether or not the wide set had them. 139 main-set ways (13.9 km: Napoli Way,
Genoa Drive, South 24th Street, Bambrey Terrace) and 26 supplementary ways (1.7 km) never enter
the box and were in neither blob. The cut now applies only to a way with a node inside the box,
and `city.b64` is repacked (the numbers are in the coda below).

**2. Every road in the city read the DEM, not the drawn ground, since Round 87.** Round 87's
`BANK_BLEND` in `groundMeshLandY` eases a bank road from the DEM to the mesh between 40 and 70 m
from the Schuylkill's edge. `schEdges` searched two 20 m cells around the point and started
`best` at 1600, so it never returned a distance over 40. Every street farther than that from the
river fell into the blend at t = 0 and took `dem + (mesh - dem) * 0`: the DEM. The far ring's
100 m mesh sits up to a couple of metres off the DEM's bilinear read on any slope, so the strips
went under it mid-span. `EC` is 40 and `best` 6400 (80 m, the reach of the ±2-cell search), the
blend band exists again, and the mesh is what the roads read.

**3. The strips were flat quads.** A strip took its two centreline heights and nothing else, so on
any cross slope one edge sank in and across a ridge of the mesh the middle did. `drapeConvex`
(with `conformDrape`) cuts a convex ring against the registered ground's cells and their
diagonals, so every triangle lies inside one ground triangle and the strip sits exactly its lift
above the drawn mesh at every point; convexity spares the earcut, each cut piece is a fan, and a
ring wholly inside one ground triangle comes back as its own two triangles. `roadStrip` and
`roadFan` route both loops through it wherever the segment stands on registered land clear of the
bank blend; a deck, a bank road, the water and the Vine Street cut keep the flat quad. The lane
paint's u and s are linear in the position, so the attributes come from it. Measured after:
**313,208 strips draped, 8,147 flat; 69,554 bend and end discs draped, 1,012 flat; 1.66 M road
triangles** against about 1.06 M before, 3.0 s of build in a hidden pane (inflated, see the
gotchas). `__dbg.roads()` reports it.

**And the decks.** The baked chains' profiles are solved against the DEM (`bake_overpasses.py`),
so they dipped under the drawn mesh as well: sampling every chain at 10 m across five points of
its width, **191 of the 534 elevated chains were under the ground somewhere, by up to 6.5 m**
(chain 466 in the NW hills, over the 50 m patch), and the terrain sliced their ends off on a
diagonal. In 'Raising the overpasses' every chain is now densified to 13 m in place, each point
raised to clear the highest of five ground reads across the deck by `DECK_LIFT` (0.64 m), and a
lifted point pulls its neighbours up so the deck never falls from it faster than `DECK_GRADE`
7%. With the lift counted, 482 chains move (most by the 0.64 at their grade ends), the most by
7.14 m. `ovpIndex` rebuilds the deck index afterwards so `ovpDeckY` carries the traffic and the
buses on the lifted decks.

Verified by capture: the interchange from Mike's pose and from 60 m at two angles (every
carriageway and ramp continuous, the decks proud of the ground, the flat roads painted on it),
top-down at 450 m, the NW hills' streets following the terrain, the north seam at Diamond Street
continuous across the box edge.

### The "inner and outer ring disparity" was 70,000 rowhouses drawn as glass

Round 87 had measured the two tiers' stored colours to an exact statistical match, and by day
from 300 m they render alike. From 1,500 m they did not: top-down over the box edge in West
Philadelphia, outer half against inner half, **noon 101/111/92 against 126/131/118, dusk 27/28/26
against 45/43/42, night 11 against 18**. Patching the facade shader in the pane to paint every
fragment it owns showed the inner tier's salmon rowhouses did not take the paint at all: they were
not the facade material. Painting the curtain-wall glass material magenta turned every one of
them magenta. The wide loop routes a building to the glass chunks with `if (style >= 20)`, and
`fabricStyle`'s word is `st + 32 * variant` (the dark and the tall variants of a plain row, in
place since Sep 2's nineteen-style vocabulary, commit 3236c4d), so **every variant 1, 2 or 3 row,
about 70,700 of the tier's 111,996 buildings, was drawn as blank tinted glass**: flat salmon
walls, salmon roofs, no brick, no windows, and a hard seam against the far ring, which routes
nothing there. That was the pink Mike saw in the outer districts, and the distinct look of the
unphotographed buildings Round 87 chased with colour constants: a photographed face with trim
keeps variant 0 and rendered right. `isGlassStyle` (20 to 31) at the three tests. After: **noon
102/112/94 against 108/115/103, dusk 32/34/31 against 36/37/36, night 16/17/17 against 17/17/18**.
The luminance step across the seam at 1,500 m went from +25% to +5% by day, +62% to +11% at dusk
and +64% to +4% at night. Verified by capture at 60 m in Point Breeze: brick, windows, dark roofs
and the pitched forms on the rows that were salmon boxes in the deployed build and in Round 86's.

### The lamps: a sun angle, not a photocell

The lamps read `nightUniform`, which is `1 - smooth(-9, 1, el)`, through a remap that started at
the horizon and was full at -2 degrees, and nothing in it knew the weather. A photocell fires at
an ambient level. `applyLighting` now derives `elAmb = el - 3.5 * cover - 2 * gloom` and writes
`lampUniform = 1 - smooth(-3, 1.5, elAmb)`: first light 1.5 degrees over the horizon in clear air,
full at -3, and a full deck brings that forward 3.5 degrees, about twenty minutes here. The windows
(`nightUniform`) take the same advance. The poles, the bridge lamps, the stadium floods and the
skyline sheets read `lampUniform`; the headlights follow it a beat later. Measured at 18:50 on the
model clock: overcast 0.59, clear 0.

### The moon through the deck, and the cloud cover's source

At night `sunLight` is swung onto the moon with `(0.05 + 0.13 k) * (1 - 0.6 cover)`, so under a
full deck the moon kept 40% of its light while `uMoonI` had already erased its disc at 15%, and
the water's glint had no cloud term at all. The moon now takes the sun's own deck term
(`deckK`, 12% at full cover) and `glintK` scales the water's sparkle and the reveals through a new
`uGlint` (0.13 at full cover, measured). The cloud cover is Open-Meteo's `current` block
(cloud_cover with its low, mid and high layers) every 15 minutes, with KPHL's and KPNE's METAR
able to raise it, never lower it. The deck's share of the TOTAL (0.45) let a cirrus sky through
as cumulus: this evening's reading was 60 total, 62 high, 4 low, 0 mid, KPHL "Partly Cloudy",
scattered at 3,048 m, and the page drew a deck at 0.27 of dark-bellied puffs at dusk. The high
layer is now subtracted from the total before that share is read, a METAR layer based at 6 km or
more is cirrus and does not count, and the layer is kept in `WX.high`.

### The bar, the red, the stadiums, the Walt Whitman, Stateside Live

The bar sits at the top centre, its icons in the mark's gold (`--bronze`), white when open, the
layers, search and time panels hanging 74 px under it (66 on a phone, 62 on a short viewport),
and the time button carries a sun. The guide's copy follows (top bar; the Credits link above). On
a 375 px phone the bar spans 62 to 314 and the compass starts at 326. The dev readout moved to
the bottom right, out from under the bar.

The red: `LIGHT_COLORS.red` 0xff2a2a at 2.4 radiance measured **(231, 129, 108)** on the lit
bands, salmon. Under the ACES fit a pure red that bright leaks into green and blue through the
input matrix; held near 1.0 it stays red. The theme shader's gain is now saturation-aware, a
saturated hue taking 0.3 of what a white does (the whites keep today's brightness): **(206, 87,
86)** after, verified by capture on the Liberty Places' chevrons and the crown bands. The
stadiums' night sheets were 0xffd9a0 at 0.16, which over a black bowl read as an orange fill:
neutral 0xf2f1ec at 0.11 now, the floods and the field glow as they were. The Xfinity Mobile
Arena keeps the skyline theme Mike asked for in Round 84. The Walt Whitman carries the Ben
Franklin's lamp standard every 36 m a side along both deck edges, 196 posts, their heads on the
streetlamps' warm points, no LED strings (344 bridge lamp points in all). Stateside Live is the
14 m complex at the south-west corner of 11th and Pattison (`VENUE_NAMED` at -2120, 4570, found
by walking `roofAt` over the block: 676 samples at 14 m, centroid -2135, 4565); the old
`/stateside|live!? casino/` entry had put it on the casino and the old Xfinity point stood on the
ballpark's lot east of 11th.

### Found and left

- Kelly Drive's chords through the hillside (Round 85's note) are moot: the drape follows the
  mesh now. Not re-surveyed this round.
- The perf readout in the pane says the drape costs about 3 s at build in a hidden tab, which
  the gotchas file says to distrust; a visible-pane timing is owed before anyone tunes it.
- The first message of the round that arrived inside a tool result (pins: no partly-closed
  construction pins, a palette on the art pins, a smoother pin entrance) was not acted on; it is
  awaiting Mike's word in chat.

101 tests pass. Page 27.84 MB.

### Round 88 coda: the far ring repacked (same day)

`pack_city.py` ran on this laptop under a fresh `.venv` (shapely 2.1.2), 3 min 17 s. Roads
24,171 to 24,277: 164 runs added (28.18 km) and 58 removed (12.74 km, the old cut-at-the-band
versions of ways now kept whole), net +15.4 km, 109 of the added runs (11.47 km) wholly inside
the 150 m band, all residential, tertiary or unclassified. South 24th Street stands at Oregon
Avenue again. The buildings drifted with the shapely version, not the change: 180,107 to
180,097, the mean ring 6.91 to 6.43 vertices, the footprint 66.24 to 65.95 km² (−0.4%), every
attribute and roof word count the same, the blob 10.21 to 9.76 MB. Checked at 60 m in Grays
Ferry against the previous blob: the same buildings, the same colours. Page 27.39 MB (−436 KB
against HEAD).

### Round 88 coda 2: the pins, and the Phillies' own red (same day)

**Mike: "Yes to the pins" (no partly closed construction pins, there are too many; a painter's
palette on the art pins; the pins animate in jarringly), and, with a screenshot of the skyline
on the Phillies night: "the red lights should match the red in the Phillies P".**

The pins. A partial closure no longer carries a pin (its cones and its card stay; `closurePinPart`
is built at count 0 for the pick lists). The art pin's glyph is a palette: the board with its
thumb hole, five wells and a brush across it, drawn into the same 256 x 320 casing. And every pin
eases in: `pinRise(rec, now)` keeps a map from the record itself to the frame it was first drawn,
and the pin's billboard scale takes an ease-out cubic over 550 ms from nothing, again after a
second out of reach; the closures' blocks, the markers, the art, the trains and the SEPTA badges
all pass through it, and a sweep drops entries unseen for half a minute. Measured on an art pin
after a jump into Old City: scale 0, 1.88, 3.08, 4.02, 4.61, 4.97, 5.14, 5.21 over the first eight
frames at 60 ms, then steady. `__dbg.pins()` counts the tracked records.

The red. The morning's fix had pulled the bands from salmon to (206, 87, 86), and the residual green
and blue turned out to be the LED parts' own grey-blue DAY colour lit by the moon and the sky
hemisphere at night: hiding the additive sheet changed nothing, the theme mesh alone carried it.
An LED emits, it does not reflect the sky, so the theme shader takes a themed part's diffuse to a
tenth after dark, and the palette's red is the Phillies' own #e81828. The bands measured **(234,
29, 48)** against the P's (232, 24, 40), with the saturated gain back up to 0.42 of a white's
(0.3 had left them at 211 red). Verified by capture on the chevrons and the crown bands.

### Round 88 coda 3: the cars on their own deck, spawned out of sight, and Cira's crown (Sep 18)

**Mike, with a screenshot from the Spring Garden Street bridge looking south
(`#p=-3005.2,14.7,-1665.9,3.136,-0.035`): "the cars are animating in and look like they are
flying well above the roadway. Also is there a better way we can have them animate in so they
don't just pop up out of nowhere and then disappear? Please take a look at the building on the
right also, the top of it appears to be leaning off the edge of the building."**

The flying. `ovpDeckY` handed a street the HIGHEST aligned deck within a half width and a metre
and a half of the point, so wherever two chains braid or fork (I-76 at Spring Garden has the
mainline at 3 to 13 m and two ramps at 3 to 8.5 m within a few metres of it) a car on the lower
deck took the upper one's height for the stretch they overlapped, and a frontage street beside a
viaduct rode the viaduct. The street IS one chain, within the 2.6 m `ovpOwned` uses, so the read
is now the nearest aligned segment within `OVP_OWN_R` 4 m and nothing beyond it. The buses and the
closures' drums read the same function.

The popping. A car already scaled in over 900 ms, but it chose its spawn spot by distance alone
from three candidates, and on a bridge at 15 m every candidate on a 400 m run is in view.
`carSpotHidden` tests a spot against the eye: behind it, more than about 52 degrees off the view
axis, or past 700 m; `carSpawn` draws six candidates and takes a hidden one over any visible one,
the farthest among equals, so cars enter the world where nobody is looking and drive into view.
The fade covers the runs with no hidden spot at all; the reconcile still retires the farthest
cars first.

The crown. The Cira Centre's `sloped` crown keeps 62 per cent of the plan, and the plan was a
rectangle of the footprint's oriented bounding BOX; Cira's footprint is a parallelogram, so the
crown block stood outside the real walls on one side. The crown is now the footprint itself cut
by one line at `keep` of its length (the Comcast Center's sides-3 plan is unchanged), the wash
sheet sized from the cut ring. Verified by capture from the bridge with the camera turned to it.

## Round 89: the strips in the river, the cars' churn, and a share card (Sep 18)

Three things from Mike, in one session.

### The three strips of land in the river

**Mike, with `#p=-3630.8,845.7,-2291.0,-0.524,-0.781&l=17777` over the Schuylkill between Mantua
and East Park: "we still have those 3 thin strips of land appearing in this view in the river.
That should not be happening."**

Four hypotheses went down before the right one, and the discipline of killing each with a
measurement is the only reason the fifth was found rather than guessed at:

- **The ground bridging the channel.** The far strips there are a 100 m grid and the river is
  about 120 m wide, which is the classic way a river gets bridged. Measured `groundAt().mesh`
  along every 10 m row through the reach: the carved channel bottoms out at −9.4 m or lower in
  **every** row, 196 of 196. Not it.
- **The water outline missing the channel.** Walked the river's own centreline through the reach
  at 10 m: 344 of 344 samples fall inside the outline. Not it.
- **A tier's green sheet drawn over the water.** Two Fairmount Park rings do cover water there,
  but kind 0 is `conformDrape`d onto the drawn ground, which inside the river is the carved bed
  6 to 7 m BELOW the water sheet, so a park sheet there is invisible. The far ring's own
  `natural=water` polygons (kind 1) are skipped when their centroid is inside `schRaster`. Not it.
- **Corner-cutting by a coarse outline.** The ring's edges run to 445 m, so this was plausible,
  and 43 cells within 45 m of the centreline do read dry, but they cluster into one 80 by 100 m
  patch and a dozen one-cell specks. One patch is not three strips.

What it was: **the water ring is self-intersecting, so the polygon is invalid.** Shapely:
`Ring Self-intersection[-5320.9, -7319.2]`, `is_valid False`. The page triangulates that ring
with earcut, and earcut on an invalid ring leaves whole pockets untriangulated, so the water
sheet had holes in it and the carved channel showed through them. The holes need not be anywhere
near the intersection, which is why every position-based test came up clean.

The cause is at the emit, not in the geometry. Every stage of `bake_schuylkill.py` is valid,
including `simplify(1.5)`; it is **rounding the coordinates to 0.1 m for the json** that breaks
it. The union of the riverbank faces with the buffered centreline leaves a handful of zero-width
spikes, where the boundary runs out and straight back, and the two sides sit 4 to 6 mm apart
(measured: edge pairs 130/132 near (−8247, −9788) and 1330/1332 near (−8150, −9840)). Rounding
moves each vertex up to half a quantum and the two sides cross. Measured at three precisions: at
0.1 m invalid, at 0.01 m still invalid, at 0.001 m valid. Erosion and dilation at 0.05, 0.15 and
0.3 m does not help, because the spike is not a sliver of area.

So the bake **despikes** instead: a vertex whose two neighbours are closer than 0.25 m is a needle
tip and goes. Six vertices leave the ring (1,449 to 1,443 before rounding, 1,300 to 1,292 as
shipped), the area is unchanged to three decimals at 12.839 km², and the ring survives 0.1 m
rounding. `emit_ring` does despike, round and de-duplicate together, and the bake now refuses to
write a ring that is not simple or a polygon that is not valid.

`tests/test_schuylkill.py` guards the shipped file, in the standard library only: a grid sweep for
crossing edges, and a needle test. Checked against the old file, which fails it with a 0.000 m
needle at (−5277.6, −7360.6), and against the new one, which passes. Verified by capture straight
down over the reach and at Mike's own camera: the channel runs unbroken.

Left alone and recorded: the one 80 by 100 m patch at x −3390..−3320, z −2110..−2020 that the
outline genuinely calls dry. The half-width is 60 m and my test threshold was 45 m off a fitted
centreline, so that may well be real bank; it is not what the screenshot showed.

### The cars

**Mike: "The cars are now popping up and disappearing even quicker. Can we sort that out?"**

Round 88's coda had made the cars spawn out of sight, and made this worse. Instrumented first
(`__dbg.trafficChurn`, births and deaths by cause with the age at death), camera held still on the
Spring Garden bridge:

| | before | after |
|---|---|---|
| births a second | 214 | 166 |
| retirements a second | 165 | 113 |
| dead-end deaths a second | 52 | 54 |
| mean age at death | 2,126 ms | 3,586 ms |
| youngest death | **0 ms** | |
| population swing, camera still | **378** | **0** |
| **visible births a second** | not instrumented | **10** |
| **visible deaths a second** | not instrumented | **6** |

Four causes, each measured:

1. **Spawn and retire were fighting.** Coda 3 picked the FARTHEST hidden spot to be born in, and
   the reconcile retires the farthest car first, so a new car was the next one killed: the
   youngest death was 0 ms, a car retired in the frame it was born. `carSpotRank` replaces
   `carSpotHidden` with three ranks, and within a rank `carSpawn` now takes the NEAREST spot, so a
   car is born just off the edge of the view and drives into it.
2. **Every junction crossing cost a birth and a death.** The population is regulated per run while
   the cars move between runs, so a car leaving run A put A one under target, which backfilled at
   once, and B one over, which shed at once. About 2,100 cars on city blocks cross a junction every
   nine seconds or so, which is the ~230 a second the tally showed. A one-car deadband on both
   sides absorbs the transfer, and the population went from swinging 378 with a still camera to
   dead flat.
3. **Nothing checked whether a car was in view when it died.** The retire pass sorted by distance,
   and a car 700 m down a straight road from a bridge is in full view. It sorts by rank first now,
   and spends a car in view only when the run is more than four over target. `CAR_MIN_LIFE` 4 s
   also keeps a newborn off the retire list, so no car is born and killed inside its own 900 ms
   fade.
4. **Dead ends.** A car that reaches a run the network hands on nowhere from faded out in place,
   54 a second. Out of sight that is fine; in view it now turns round, which is what a car at a
   dead end does, and dies only once it is off the screen or has turned six times.

93 per cent of births and 95 per cent of deaths now happen where the viewer cannot see them, and
at street level and from the skyline pose the visible deaths measure zero.

### A share card

**Mike: "Can we add a share button that creates a share card for users to send links to exact
coordinates?"**

The machinery existed: `viewState(true)` is the string the address bar already carries, plus the
clock when it is pinned, and `applyHashView` lands on it exactly. What was missing was a way to
get at it. `#btnShare` joins the bar between the camera and the `?`, and opens `#sharepanel` on
the same strip as layers, search and time, one panel at a time, Escape closing it like the others.

The card names the place from the baked neighborhoods layer (`PLACES.nb`, nearest within 2.6 km,
else Philadelphia), gives the latitude and longitude to five decimals through the scene frame's own
inverse, the eye height and the sixteen-point heading, and carries the link in a read-only field
with Copy Link beside it. It refreshes on `updateHash`'s own 500 ms cadence while open, so what
you copy is what you are looking at. `navigator.share` appears as a second button where the
platform has it (phones) and stays hidden where it does not. The clipboard write falls back to
selecting the field and `execCommand`, and then to telling the reader to press Command C, so it
works on an insecure origin too.

Verified in the pane: the card reads "Queen Village, 39.93733, −75.14826, 240 m up, facing NW" at
the skyline pose; the link carries the pose, the pinned clock and the layer mask; loading it back
lands the camera at exactly (1100, 140, 250) with yaw −1.347 and pitch −0.100; the panel is
exclusive with the other three both ways and closes on Escape.

- 103 tests pass (`tests/test_schuylkill.py`). Page 27.40 MB (+12.6 KB). Devlog Round 89,
  CLAUDE.md.

### Round 89 coda: the strips in the river, actually found (Sep 18)

**Mike, with three arrows on the Schuylkill between Parkside and East Park: "These strips of land
need to not be there. This is like the 8th time we've been over this. They do not exist in real
life."**

They were still there, and the reason this took eight goes is that every check before this one
measured the wrong thing. Recording both mistakes, because they are the lesson:

1. **A per-row minimum hides the defect it is looking for.** Earlier in this same session I walked
   every 10 m row across the reach and reported the LOWEST drawn ground in each: −9.4 m or lower in
   196 of 196 rows, which read as "the channel is carved everywhere". It is. The ridge sits *beside*
   the trough, in the same row, and taking the minimum threw it away.
2. **The water level was guessed, not measured.** I tested the ground against −2 m. `TERRAIN.water`
   is `0.5 - DATUM` and `DATUM` is the DEM at the towers' centroid, so the sheet is at **−7.34** in
   model units. Recovered exactly from the carve floor: `bedMin` −10.94 = `TERRAIN.bed − 0.6`, so
   DATUM is 8.34. Against −2 m nothing looked wrong; against −7.34 the ground rose **1.10 m over the
   water**.

What it is: the far strips were a **100 m** grid, `riverCarve` only pulls down the grid NODES that
fall inside the river, and a 150 m DEM has no idea the channel is there. So wherever no node landed
in the water, one triangle spanned the whole 120 m channel at land height. Measured across all three
bands, the bed dips to −10.94 either side and ridges back to **−6.24, −6.78 and −6.87** in the
middle. Confirmed the bands are on that grid by walking +x and reading the slope breaks: every
100 m plus the quad diagonal, against a clean 100 m off the river.

Three things were wrong with the water treatment, all now fixed:

- `FAR_CELL` is **50 m**. At 50 no triangle's hypotenuse reaches across a 120 m channel, so the
  carve always has nodes in the water. One constant, used by the strips and by the NW hole's
  snapping (which hardcoded 100 and would have torn).
- `riverCarve`'s eased band ran to 40 m with a floor of `water + 0.9`, which is **0.4 m ABOVE the
  sheet**: the bank poked through its own river at the edge. The band runs to 60 m now, so a 50 m
  cell straddling the bank has every corner pulled down.
- That floor is a metre **under** the sheet. At `water + 0.3` there was only 0.2 m of headroom and
  one 10 m peak still came through on the centreline past Manayunk.

**`__dbg.riverCheck()`** is the durable part: one call that walks the river's own centreline at 10 m
and reports every sample where the drawn ground rides above the sheet, skipping anything past the
sheet's own `z_range`. It exists so this is never hand-rolled again.

| | before | after |
|---|---|---|
| centreline samples over the sheet, whole river | many | **1** |
| worst, in the reach Mike photographed | **+1.10 m** | under the sheet |
| worst anywhere | | **+0.04 m**, one sample past Manayunk |
| meadow-green pixels on the centreline, reach | **20 of 1,045** | **0** |
| triangles, skyline pose | 13.6 M | 14.4 M |

The pixel test is the one that matches what Mike sees: fly straight down in 400 m steps so a 10 m
band is tens of pixels, project every centreline point, and read the rendered colour. The 7 pale
hits that remain are 149 to 191 grey at x −4180..−4219, which is the Girard Avenue bridge deck
crossing the water, as it should.

The 0.8 M extra triangles are the price of the finer strips, and they buy better terrain under
every far-ring road as well. Verified by capture at Mike's own camera and closer.

- 103 tests pass. Page 27.41 MB (+3.1 KB). Devlog, CLAUDE.md, the capture skill's probe table.

## Round 90: the sports banners on the day of the game, and Home or Away (Sep 18)

**Mike: "Can we have the sporting events act like the concerts for the day of? Also on the sports
banners, change the away/home to be Away/Home."**

The concerts had the better rule and the scores did not share it. A concert placard rises at 9 am
Philadelphia time on the day of the show and stands until the show ends; a score bubble only
appeared once the game was already `in`, so a Phillies day game was invisible all morning and the
city gave no sign anything was on. The bubble now rises at the same 9 am instant.

`scoreDayStart(startMs)` is the page's own version of what `ops/concerts_bake.py` bakes for a show.
The scores have no baker, so it takes ESPN's start instant, asks the zone itself for the
Philadelphia calendar day (`toLocaleDateString('en-CA', { timeZone: 'America/New_York' })` renders
YYYY-MM-DD), and turns that local 9 am back into UTC through the clock's own `tzOffsetMin`. Checked
across a DST boundary: a 7:05 pm EDT start in September opens at 13:00Z, a 1 pm EST start in January
at 14:00Z, and the spring-forward Sunday at 13:00Z, all of them 9:00 AM in Philadelphia.

Before the game there is no score to show, so the first line reads the matchup, `PHI vs NYM` at home
and `PHI at NYM` away, with ESPN's start time under it, and the dot goes a still bronze
(`.lbl.score.pre`) rather than the live red or the final grey. Once ESPN flips the state to `in` the
score takes over, and the hour past the final is unchanged. The upper bound on the pre-game window
is only a guard against a feed that never flips.

Found while wiring it: ESPN reports a **postponed or canceled** game in the same `pre` state, which
under the new rule would have parked a banner over the venue all day for a game nobody is playing.
Those are skipped on the status name.

And the banner now says **Home** or **Away**, capitalised. It used to append ", away" in lower case
and say nothing at all for a home game.

Verified by reading the rendered banners rather than eyeballing them, all four states at once from
`__dbg.scoreTest()`, which grew an away pre-game fixture so both the `vs` and `at` forms are covered:

```
live away   PHI 4, NYM 2    Bot 7th, Away        red dot, pulsing
live home   PHI 17, DAL 10  3rd 8:41, Home       red dot, pulsing
final       PHI 2, PIT 3    Final/OT, Home       grey dot, still
pre away    PHI at BOS      7:30 PM ET, Away     bronze dot, still
```

- 103 tests pass. Page 27.41 MB (+2.6 KB). Devlog Round 90, CLAUDE.md. CLAUDE.md's Round 88 note
  naming `carSpotHidden` also corrected: Round 89 replaced it with `carSpotRank`.


## Round 91: a local interface design review (Sep 18)

Mike asked for a review, suggestions, and a more aesthetically pleasing app. The local
review build keeps the City Hall mark, Montserrat, charcoal and gold, the top navigation,
the existing layer defaults and the renderer. The interface now has a unified navigation
dock, labelled desktop actions, a redesigned welcome with measured assembly progress,
and eight described destinations in Explore. Layers uses switches, Sun & sky separates
its facts and shows selected presets, and Share, the guide, About, and map cards share
the same spacing and panel treatment. A small neighborhood/time readout orients desktop
visitors.

Search results are native buttons. Edits and panel switches invalidate pending address
lookups. The guide's hidden slides are inert, Credits participates in its focus loop,
and the welcome isolates background controls until entry. Outdated guide directions
were corrected. The share card also refreshes during automatic orbit: updateHash's
orbit guard previously skipped its refresh and left the visible coordinates and URL
frozen, even though the copy action itself calculated the current pose.

Verified in the local browser at desktop, 844 by 390, and 390 by 844: destination glide,
local City Hall search, Tab to results, cleared-query suggestions, panel switching,
night preset and selected state, guide slide bounds, and the credits route. The time
panel shows live weather and air quality separately from the selected solar clock.
The Python suite passes 103 tests with one expected failure; the air-quality and skyline
light UI assertions were updated from the former concatenated line to their labelled
facts. JavaScript syntax, build guards, documentation coverage, and a focused share
refresh/cadence check pass. This is a local review, not a deployment. The page adds
about 24 KB without new assets or dependencies. DESIGN-REVIEW.md records the findings,
next-work priorities, and validation limits.

## Round 92: stadiums, skyline, and night lighting (Sep 18)

Mike asked to revamp the 3D model, especially the South Philadelphia stadiums and
skyline. Replaced the two block-like stadium builders with actual stepped seating
bands, aisles, concourses, glazing, roof structures, and procedural playing surfaces.
Citizens Bank Park has an open three-tier horseshoe, warning track and diamond,
lattice light standards, the larger current PhanaVision proportions, and a neon bell.
The Linc has a regulation-size N8W field with markings and goals, sideline and end-zone
tiers, scoreboard openings, tapered canopies, roof ribs, tiebacks, and solar modules.
Separate deck segments prevent an end-zone polygon from roofing over the field.

The arena now has a curved roof eyebrow, roof seams and plant, glass entrances and
three canopies, northeast/northwest/south screens, and visible corner strut lights
following the existing theme calendar. Venue screens show identity graphics rather
than fabricated game data. The old flat additive stadium halos are removed; a merged
material carries per-vertex neutral floodlight response, while canvas textures carry
the fields and signs. Night parking paint now dims with daylight instead of glowing
white. Smaller floodlight sprites and a soft bloom threshold keep point lights cleaner.

One and Two Liberty Place's shafts now use their intended silver-banded glass style,
with deeper blue tints and thinner crown trim. The Comcast pair has more restrained
glass. CTC's broad imported 142 m office wings are raised to an estimated 213.5 m
terrace datum beneath the existing hotel, including the occlusion grid; its total
height stays 342 m. Raised facade chevrons and three-story belts follow the imported
plans. Curtain-wall panels have restrained variation and grouped occupied offices;
window lighting has warm/cool variation and less white glare. Added four Explore
views, bringing the list to twelve.

Compared the existing and revised skyline at (-900,250,-180,-0.98,-0.05), Sep 18 at
17:30. Inspected all three venues in daylight and at night, including a green skyline
theme with neutral stadium fields, readable markings, scoreboard openings, the bell,
and the arena's roof and corner lights. No console/shader errors in the final browser
check. The final Linc view reports about 14.49 M triangles versus a roughly 14 M city;
frame times in this pane are not a physical-device performance benchmark. Explore
navigation and its scrolling twelve-stop panel work in the preview. A requested
viewport override did not change this pane's reported 1280x720 viewport and was reset;
no new physical-mobile or touch-device rendering claim is made.

JavaScript syntax, build guards, docs_check, and git diff --check pass. The suite runs
107 tests with one pre-existing expected failure, including four new tests executing
the actual venue geometry with vendored Three.js under Node. The page is 27.45 MB;
this model pass adds about 12 KB of app source, no libraries or downloaded assets.
MODEL-REVIEW.md records the references and remaining approximations, including CBP's
unexcavated field terrain and the estimated CTC terrace. This remains a local review
build, with no production deployment.

## Round 93: blue seats and fuller outfield at Citizens Bank Park (Sep 18)

Mike asked for blue baseball seats, outfield seating, and a scoreboard rotation.
All three main tiers and the alternating row shades now use blue. Expanded low
left- and right-field terraces follow the angular fence, with 22 rows, split
sections and aisles, rear promenades and railings, and a center-field batter's-eye
gap. Brick pavilions sit behind the new seating. PhanaVision and its steel supports
rotate together about 26 degrees toward home plate.

Rebuilt the single-file page. JavaScript syntax, the four venue geometry tests,
and whitespace checks pass. Visually checked the elevated view and the view from
behind home plate in daylight and at night; the browser reports no errors.
The two detailed venue batches total 56,042 triangles. Changes remain local.

## Round 94: flush Linc scoreboards and a stable baseball field (Sep 18)

Mike supplied model screenshots and real stadium photos, asking to align the Linc's
scoreboards and fix flickering on the baseball field. The Linc boards used the field
bearing with the wrong sign for PlaneGeometry's rotation convention. Both displays
and housings now derive their facing from the inward field axis, rotating 16 degrees
to sit flush across the end-zone openings.

CBP's concave foul-corner outline had been triangulated as a centroid fan. That fan
overlapped itself and had reversed face winding, causing coplanar flicker and dark
daylight shading. The authored outline now uses ShapeUtils polygon triangulation:
one correctly wound surface with the existing texture and field boundaries.

Added two geometry regressions: triangle intersection area on the actual baseball
mesh, and field-relative alignment of both football displays and their cases.
Both failed before the fixes and pass afterward. All six venue tests, JavaScript
syntax, the build guards, docs_check, and whitespace checks pass. Browser checks
cover CBP from behind home plate and during its overview glide, and the Linc from
the overview and an aligned (-1909.87,170,5142.4,-0.139626,-0.63) pose at 12:30.
The field is clean at those angles, both boards align with the seating, and the
final browser error log is empty. Rebuilt locally; no production deployment.


## Round 95: streets, paths and rail clear the terrain (Sep 18)

Mike reported streets, roads, paths and railway tracks being clipped by elevation.
The remaining flat fallbacks were the problem: core ribbons used centreline heights,
bank roads bypassed ground conformance, a partly uncovered/holed road reverted its
entire strip to a flat quad, and the wide tier built its boundary roads before the
far heightfields existed. Rail beds also checked their centres rather than their
full width and the terrain between samples.

Road ribbons, strips and bend fans now split at ground cells/diagonals across their
whole footprints. Only missing cells use the original grade; bank/bridge grades stay
as minimums. Each tier seam clears both adjacent mesh edges. The core ground now
ends exactly at CORE_EXT instead of overshooting by a rounded cell, and has a
road-only registry entry so hand-built core plazas retain their placement.
Wide road ownership is registered immediately, preserving far-tier deduplication,
but the geometry is built after all terrain tiers are ready.

The browser comparison found a second source of clipping: wide park polygons that
extended beyond the wide mesh had already been draped on the DEM, floating above
the eventual far mesh and burying roads. Their surfaces now wait for the finished
ground too; small wide parks also conform. At East Park the isolated pale road
fragments now join into continuous routes. No new map data or rendering dependencies.

Rail clearance covers the entire ballast footprint, including bends and ridges
between samples. Shared chain endpoints stay aligned and trains use the corrected
height profile. Covered 30th Street approaches retain their portal levels. Elevated
road clearance checks the two actual deck triangles between samples before its
existing grade limiter runs; tunnel geometry keeps its existing treatment.

Six new geometry regression tests execute the source helpers against synthetic
slopes, ridges, terrain holes and stepped tier seams. Five of the six test groups
failed against the pre-change source and pass after the fixes. The full suite ran
115 tests in 12.35 s, with one pre-existing expected failure. Node syntax, the build,
docs_check and whitespace checks pass. Rebuilt page: 27.45 MB.

An ignored, instrumented browser build tested vertices, edge midpoints and centroids
of generated transport triangles against the actual drawn heightfields. Its final
16,931,866 surface-transport samples contain no values below ground (minimums:
core roads 0.139 m, paths 0.160 m, wide 0.239 m, far 0.221 m, towns 0.254 m,
elevated roads 0.592 m, surface ballast 0.500 m). This is a sampled mesh-clearance
check, not a proof of visibility through all buildings or hand-built overlays;
intentional tunnels and the covered station area are excluded from the rail audit.
Terrain collars are counted separately, also with no buried samples. Audit code
stays in ignored .audit previews, outside the shipped page.

Visual checks: East Park (-3980,180,-3340,0.55,-0.55), 30th Street's south approach
(-3000,150,-690,-0.4,-0.56), and the Roxborough Park river/hillside routes
(-8550,220,-9750,-0.2,-0.65). Browser errors were empty. Changes remain local.


## Round 96: continuous road and rail bends (Sep 18)

Mike supplied the exact view (-3744.1,166.8,-2508.3,-1.706,-0.552), showing jagged
highway edges and broken-looking tracks near Mantua. Round 95's heightfield audit
could establish clearance but could not detect overlapping or disconnected bend
geometry. The exact-view comparison confirmed that independent rectangular road
segments left notches on the outside of bends and overlapping surfaces inside.
Rail strips additionally put coplanar fan triangles over the ballast and rails.

Core ribbons, wide roads, far roads and surface rail strips now share cross-sections
at bends using bounded miter offsets. Terrain conformance remains in place; authored
grades use the actual triangular surface, keeping adjacent ends at identical heights.
Rail ballast and both rails follow the same joins with no coplanar fill discs. Bank
skirts follow the corrected road edges. Road endpoint caps remain for joins between
separate OSM ways. Hairpin miters are limited to twice the half width.

The rail drawing loop was also still testing the next point's tunnel bit when ending
a visible run. Since flags belong to segments, this omitted one visible segment
before a tunnel. Visible runs now include the final endpoint of their last surface
segment and continue to the actual portal; intentionally covered segments stay hidden.

Three added tests cover road bend overlap and matching edge coordinates, ballast
triangle overlap/counts, and tunnel segment ranges. On the Round 95 source the bend
fixture had 6.38 m2 of road overlap and 24.67 m2 of ballast overlap. With the change,
both are zero to test tolerance. The full suite runs 118 tests with the existing one
expected failure. JavaScript syntax, build guards, docs_check and whitespace checks
pass. The citywide sampled audit again reports no buried surface-transport points
among 16,052,238 samples (same exclusions and limits as Round 95). No browser errors.

Compared before and after at Mike's exact camera and Sep 18, 12:30 with clear weather.
The Expressway edges are continuous through the curve, the tracks remain continuous,
and the previous protruding strip ends are gone. Also inspected the 30th Street south
portal from (-3235,85,-650,0.055,-0.55); the tracks reach the entrance. Rebuilt the local single-file page;
production has not been updated by this pass.

## Round 97: welcome-screen title case (Sep 18)

Mike asked for title case throughout the welcome screen except its descriptive
paragraph. Updated the kicker, headline, facts, ready button, progress accessibility
label and footer. Removed the kicker's forced uppercase. Loading messages use title
case at display time, preserving internal step names and acronyms such as SEPTA.
The descriptive paragraph is unchanged. Rebuilt locally; syntax, representative
loading-copy checks, exact paragraph comparison and whitespace checks pass. Inspected
the rendered welcome screen and accessibility tree at the ready state.

## Round 98: street labels follow the rendered pavement (Sep 18)

Mike reported clipped street names at (-3547.8,163.9,-2087.9,0.478,-0.800).
Reproduced the missing ends of Martin Luther King Junior Drive and missing middle
of Schuylkill Expressway. Labels sampled the road's DEM centerline rather than the
rendered pavement, used the same height across their width, and capped neighboring
column rises at one metre. This forced text below slopes and raised road sections.

A temporary spatial index now retains actual road-top triangles only where baked
labels need them, including core ribbons, wide/far streets and their endpoint caps,
elevated/cut roads, and the custom Ben Franklin and Walt Whitman decks. Labels use
shared grids at <=4 m spacing in both directions, the complete existing SDF atlas
rectangle, and at least 18 cm clearance. Each text triangle also checks intersections
with road triangles and terrain-cell edges/diagonals; interior crests cannot be
missed by vertex samples. Removed the downward slope clamp. The temporary index is
released after the single label mesh is built. Depth testing remains enabled;
unrelated crossing decks are excluded from the supporting-road lookup, and the
covered-road suppression is preserved.

The instrumented city build compares the previous height algorithm with the final
Float32 label geometry. Of 3,774 placements, 336 previously intersected terrain or
supporting pavement; the worst was a Walt Whitman Bridge label ~42.96 m below the
custom deck. Afterward, all 3,774 placements render with zero intersecting triangles
or buried samples across 243,752 triangles and 6,824,948 sample checks; minimum
sampled clearance is 0.18004 m. Thirteen placements have no recorded road triangle
(Aquarium Drive, Ogden Street, and eleven small streets/courts); these were checked
against actual terrain using the fallback grade. This audit concerns road/ground
intersection, not visibility through vehicles, buildings, bridge structures, or
from every possible camera angle. Local audit generator and reference build are
in `.audit/street-labels/` and `3d-model/.audit/`.

Five new Node-backed regression tests cover steep longitudinal/cross slopes,
interior road crests, raised decks versus crossing bridges, ground ridges, complete
texture coverage, finite coordinates and upward winding. The full suite runs 123
tests with one pre-existing expected failure. Syntax/build/docs/whitespace checks
pass. Compared the exact reported view before/after in the browser: both names
are complete. Additional bridge/cut views check elevated and depressed placement.
The rebuilt page is local; this pass has not deployed to production.

## Round 99: intact, clickable pins above buildings (Sep 18)

Mike reported building faces cutting through art pins and requested that no pin
kind clip buildings. Reproduced this on the Puma pin at The Caring Center beside
North 31st Street, using (-3637,52,-1959,-0.600,-0.250) at Sep 18, 21:00. A roof
cut away the left side of the palette badge.

All annotation pins now use `pinOverlay`: transparent, depth test/write disabled,
render order 100. This covers the shared art/historical/closure badge builder,
SEPTA, Indego, both aircraft variants, ships, Amtrak, search destinations, and the
score/concert connector lines and anchor balls. Pins remain at their geographic
anchors and retain their distance gates, layer toggles and entrance animation.
Their complete faces paint over the city; the physical vehicles, docks, marker
posts, art forms and buildings keep normal depth testing.

Picking now gives visible annotations priority over scene models and bypasses
the building-occlusion gate for icon hits. Transparent parts of the badge texture
are rejected, including Indego's per-instance atlas tiles. Overlapping icons pick
the last drawn batch/instance. Physical-model and ground fallback picks still
respect buildings. The formerly hidden part of Puma's icon was clicked in the
browser and correctly opened the Puma / Eric Berg / The Caring Center card.

Six new tests cover overlay materials (including line/ball connectors), selection
through building depth, transparent-corner click-through, per-instance bike atlas
coordinates, overlapping badges and all pin-family call sites. Full suite: 129
tests, one pre-existing expected failure. Syntax, build, documentation coverage
and whitespace checks pass. The nighttime before/after view confirms the roof no
longer cuts the badge. Local rebuilt preview only; not deployed.

The runtime material audit confirmed all ten live badge batches (art, historical,
full/partial closures, SEPTA, Indego, fixed-wing/helicopter, ships and Amtrak) use
the shared overlay policy. The daylight comparison also shows a complete icon.
Browser console: no errors. Audit preview/generator are kept under the ignored
`.audit/pin-clipping/` and `3d-model/.audit/` directories.

## Round 100: clouds at varied elevations, smoother volume (Sep 18)

Mike reported that the clouds all sat at the invisible flight boundary and looked
pixelated. The old renderer started every cloud on a 1,900 m plane, assumed the
camera was always below it, and used 18 desktop / 9 touch samples with a random
per-pixel offset. The flight ceiling remains 1,600 m.

Replaced that plane with two world-space atmospheric bands. Lower-bank bases vary
from 780 to 1,720 m, with independently varying depth up to 980 m; the upper bank
starts between 3,000 and 3,850 m with up to 1,150 m depth. Different pattern scales,
seeds and wind speeds separate them. A camera-centred enclosing mesh supplies view
rays only: cloud density stays in world space, and the ray intervals work below,
inside and above lower banks, including downward views. Fragment depth comes from
the first cloud contribution rather than the enclosing mesh, so foreground
buildings hide clouds and clouds can veil more distant geometry. Both standard
and logarithmic depth are supported. Ground shadows retain an approximate mean
lower-bank projection at 1,550 m.

Removed the pixel-random march offsets. Stable midpoint integration, filtered noise
at pixel and sample footprints, vertical boundary smoothing, and a small 3D density
component give softer edges and fuller shapes. A lower optical density and diffuse
heavy-weather lighting reduce harsh bands. The maximum budgets are 64 + 36 samples
on desktop and 32 + 20 on touch, with interval rejection, empty-sample skips and
transmittance early exits. Existing weather, sun/night colour, fog and wind controls
remain connected. The opt-in low-poly fallback also uses the varied height bands.

Validation: built and inspected clear skies at 350 m and 1,450 m and heavy overcast
above the skyline. The desktop preview at DPR 1.25 reported p50 16.8 ms initially and 33.3 ms
in the final overcast view (p95 33.4 ms); these are local observations, not a
mobile benchmark or a guaranteed frame rate.
`tests/clouds_gpu.html` loads the actual app shader and checks four combinations of
desktop/touch budgets and standard/log depth, including camera heights, downward
rays, zero weather cover, clear versus overcast, fixed-view stability, near-wall
occlusion, clouds in front of distant geometry, varied bases and the upper bank.
All four variants pass. The density slice measured 375 m of base variation across
its sampled 12 km strip; no foreground pixels bled through. The Python suite runs
129 tests with one pre-existing expected failure. The page is rebuilt locally.

## Round 101: building fabric and recognizable skyscrapers (Sep 18)

Mike asked for a model-wide building review with particular attention to real-world
Center City skyscrapers. Compared the existing live scene with the RAMSA Comcast
Center project, Enclos' CTC/Cira facade studies and photographs, and Liberty Place
references linked in MODEL-REVIEW.md. Kept the imported plans/heights and the
previous stadium, terrain, labeling, pin and cloud work.

- `VBuf` now carries `aFacade` as two signed decimetre shorts. Signed wall width
  encodes the two U endpoints (negative=start, positive=end); the second short is
  the wall top above `aBase`. The vertex shader decodes before interpolation.
  Both packed builders supply these values for courtyard and exterior walls;
  roofs/trim default to zero. Core float attributes still work with the same hook.
  Four bytes/vertex rather than three new floats, about 59 MiB of GPU storage in
  this build; upload releases staging arrays. Keep this endpoint encoding in mind
  if adding intermediate vertices to wall quads in the future.
- All fabric styles benefit from wall-fitting windows, eave shadows and a restrained
  coping/frieze/base treatment. Frames are quieter, sash/mullion detail survives
  the final glass-tint mix, and windows have subtle blind/pane variation.
  Style 19 provides brick apartment windows, with the OPA masonry palette preserved.
  Mid/high-rise selection now preserves industrial lofts and uses the mapped era.
- Replaced the outer curtain-wall hook with differentiated framing, stable panel
  variation, view-dependent procedural sheen and grouped warm/cool night offices.
  Actual sky reflections still use the existing environment. Floors and mullions
  fade separately by pixel footprint. Styles 24/25 remain the Comcast pair;
  26 is Liberty's central bays, 27 FMC, 28 Cira and 29 enclosed glazed crowns.
- Liberty shafts gain recessed corners; Two Liberty gains central bays too. The
  crown trim is finer, and mechanical-crown windows no longer compete with the
  nighttime chevrons. The source/model height and existing theme system remain.
- Landmarks gain restrained coping, corner lines and stone piers in the existing
  trim batch. Comcast Center gains south-facing sky-atrium accents, and CTC gains
  mechanical belts and a quieter hotel stack. Three Logan's rose-gray stone and
  `stone_piers` style are persisted in both towers.json and bake_towers.py.
- BNY Mellon's pyramid gains glass below the ribs and additional horizontal rings,
  with its excessive mast shortened. Winding respects either OBB convention; the
  opaque skin stays inside the existing night-wash sheet. Enclosed-crown style 29
  suppresses office lights in this steep pyramid as well as the Liberty crowns.
- Cira Centre previously shared the rectangular `notch` builder despite its
  `sloped` crown type. It now has a continuous faceted, inward-leaning glass mass
  and a sloping roof, capped at the researched 133 m and inside the surveyed plan.
  Its upper night-wash skin follows that geometry. This is a visual approximation
  of the documented complex facade, not exact construction geometry.

Verification: production geometry helpers run under Node in the seven new
`tests/test_architecture.py` cases (buffer growth/defaults/release, both tiers'
wall datums and winding, Liberty plan triangulation, pyramid normals, part-bound
trim, Cira footprint/height bounds, and facade family selection).
`tests/buildings_gpu.html` compiles the real material hooks for all 30 base styles,
checks 20 packed/core facade matches and 28 lit style families, plus subdued
mechanical crowns, for all four detail-budget/depth-mode combinations. All pass
with zero shader errors. The instrumented city audit found complete wall metrics
on 8,530,716 nonblank packed wall vertices. Live daytime neighborhood/tower views
and the nighttime downtown cluster were inspected. Full suite: 136 tests, one
existing expected failure. `node --check`, build, docs check and whitespace checks
pass. Audit pages and the start-of-turn source snapshot are under ignored .audit
folders; the shipping page has no review controls. Rebuilt locally, not deployed.


## Round 102: cut-edge grass no longer swallows streets (Sep 18)

Mike's exact Logan Square view (`#p=-1913.8,144.6,-1406.9,-0.321,-1.097`)
showed grass covering most of the Vine Street frontage and parts of Franklin
Town Boulevard. Reproduced it in the browser, then hid the cut-edge grass alone:
the entire road network underneath was intact. These secondary terrain meshes
were absent from the earlier heightfield-only clearance audit.

- Expressway/ramp grass now uses `terrainRibbon`: a skin on the ground triangles,
  without a road ribbon's centreline minimum grade, random lift or round end caps.
- A build-only spatial index retains actual pavement near cut patches and the core
  landscape. `trimTerrainPatch` subtracts interfering road footprints by convex
  triangle intersection, including narrow roads passing through the interior of
  a large grass triangle. It leaves ground under clear high bridges in place.
  The safety margin is 8 cm and the index is released before live feed setup.
- Rail portal grass gets the same protection using the actual road and ballast
  tops. Core parks and the waterfront promenade also had incidental path/street
  overlaps; those are fitted to the existing pavement. The promenade waits for
  both road tiers. Explicit I-95 park/plaza caps retain the roads below them.
- Pitched bridge end walls were being recorded as upward-facing pavement. Only
  sufficiently upward-facing box surfaces now participate in road-label and
  terrain clearance; below-grade foundation faces are not driving the checks.

The instrumented sweep examined 2,280,731 road/path surface triangles against
480,544 captured overlay triangles, plus 15,926,510 heightfield samples. It uses
exact projected triangle intersections for overlays, not just centreline probes.
Before: 25,140 intersecting road-cut-grass/road triangle pairs and 614 rail-cut-
grass/road pairs. After: zero for both; minimum remaining overlap clearance is
8.09 cm and 17.86 cm respectively. The promenade also has zero interfering
pairs (8.02 cm minimum). Far/town parks, sports lots and paved yards remain clear.
Core park flags outside the authored I-95 cap areas are gone.

This is a geometry clearance audit, not a claim every object in the model is
visible from every camera. It intentionally also reports covered I-95 decks,
water/fountain fixtures, cut-floor/tunnel transitions, and bridge-abutment edge
contacts; those are distinct from the grass strips covering ordinary streets.
The report summary is preserved under ignored `.audit/road-overlays/` along
with the before source, audit generator and before/after preview pages.

Browser spot checks cover the exact report, eastern Vine Street, the Chestnut
Street bridge, MLK Drive/Schuylkill Expressway and the northern station approach.
Five new production-helper regressions cover the subtraction geometry, full
cross-slope skin, high bridges, ramps, tunnel caps and bridge end-face filtering.
The page is rebuilt locally with no new dependencies. Not deployed.

Final validation: 141 tests, one existing expected failure; JavaScript syntax,
build guards, documentation coverage and whitespace checks pass. No browser
errors in the audit preview. The normal preview is reopened at Mike’s exact pose.


## Round 103 — Comcast crowns, City Hall floodlighting and Boathouse Row

Mike supplied six reference photos and requested the Comcast Center's defining
upper cutout, fully illuminated selectable crown bands, cleaner Technology Center
bracing, architectural rather than blanket City Hall lighting, and accurate day
and night Boathouse Row models.

- Comcast Center now has a real 37 m crown assembly: side piers, a recessed
  mechanical back wall, a dark soffit and a supported lintel. The rectangular
  recess is physical geometry on both broad faces, not a dark decal. Its depth
  and relative proportions are visual interpretations of the supplied photograph.
  The existing mapped lower wings and other towers' notch crowns are preserved.
- Continuous LED panels cover the crown's exterior faces at night, leaving the
  recess dark. They disappear by day to expose the underlying glass and mullions.
  Both Comcast crowns select contiguous horizontal bands from a 1–4 color palette;
  normalized height replaces the old repeated floor-by-floor color cycling.
  A separate raw-color material preserves saturated red/blue without a gray
  daylight lighting contribution. CTC uses a frosted lantern and slim baffles.
- CTC's repetitive V geometry is replaced by alternating single diagonal members
  on the office elevations. Short return walls and the hotel retain clean glazing.
- City Hall has its own facade material: repeated arched storeys, illumination
  concentrated on the tower and projecting pavilions, restrained connecting walls,
  cornice courses and pilasters, dark slate roofs, and theme-responsive upper metal.
  Floodlight color multiplies the actual stone and window shading. The old solid
  overlay sleeves flattened the windows and have been removed from this landmark.
- Eleven Boathouse Row clubhouse plans come from the existing raw OSM data.
  `boathouses.json` records their plans, palettes and visual height approximations.
  Custom models add distinct cross-gables/dormers, masonry and half-timber facades,
  river-facing arched boat doors, upper windows, balconies, a small turret, quay
  landings and roof/arch/trim outline lights. Generic duplicates are suppressed in
  both city tiers. The outlines follow the current skyline theme automatically.
- Sun & Sky now offers Automatic, Warm White, team palettes, Red/White/Blue,
  Purple/Gold and custom 1–4 color palettes, plus banded/solid Comcast crowns.
  Manual changes apply immediately. `lights` and `bands` are kept in shared URLs;
  encoded comma-separated hex palettes are parsed with URLSearchParams.

Reference interpretation also checked against the architect's project pages:
https://www.ramsa.com/expertise/project/comcast-center and
https://www.fosterandpartners.com/projects/comcast-technology-center .
Club identities and ordering were cross-checked with the Schuylkill Navy:
https://boathouserow.org/boathouse-row-beyond-history/ . No downloaded textures,
new dependencies or deployment. The photographic forms remain lightweight
architectural approximations rather than a survey-grade reconstruction.

Validation: rebuilt the 27.50 MB standalone page; JavaScript syntax, documentation
inventory (49 build inputs and 62 scripts), and whitespace checks passed. The full
suite ran 145 tests with one existing expected failure. Browser checks covered
day/night views of all four landmarks, red/white/blue and solid crown lighting,
custom one-to-four-color controls, and palette restoration from shared URLs.
The normal preview loaded without browser errors.


## Round 104 — Penn's Landing CAP as an elevated construction site

Replaced the authored finished lawn and 70 planted trees at the I-95 cap with a
construction-stage model based on the supplied photo. The site follows the rotated
Front Street grid between Chestnut and Walnut, instead of the old horizontal
rectangle. Separate I-section beams, median/edge piers, bearings and limited poured
decking span I-95; only the northern section of the Columbus Boulevard extension
has beams. Blue hoarding encloses a graded riverside staging yard with stockpiles,
material stacks, cabins and two lattice crawler cranes. These are representative
construction details, not a survey or live inventory of site equipment.

Removed the park-specific terrain slope and its solid portal faces. Existing
Foglietta/Vietnam memorial decks remain. Cap height includes the modeled motorway
ramp shoulders and both boulevard carriageways; the clearance regression samples
full roadway widths at one-metre intervals. Its minimum modeled clearance is
5.65 m, and no pier/footing intersects the sampled road corridors. The median
support line was shifted to account for the highway's curve at the south end.

Obsolete footpaths and access roads are split at the construction fence, including
segments whose endpoints both lie outside the zone. Typical local-road traffic,
surveyed/procedural trees, and former park lamps are suppressed within the site.
I-95 and Columbus Boulevard stay open under the structure. The riverside yard
uses a level earthwork surface to avoid grass breaking through a mismatched drape.

Reference status: PennDOT's June 30, 2026 update describes staged beam setting and
support-pier work over I-95 and Columbus Boulevard:
https://95revive.com/news/cap-construction-update-summer-2026/ .

Validation: four new structural/boundary regressions; full suite ran 149 tests
with one existing expected failure. Standalone page rebuilt (27.51 MB).
Browser verification covered the supplied aerial viewpoint and both highway
approaches beneath the beams. No browser errors; syntax, documentation inventory
and whitespace checks passed. The normal preview is left at the supplied pose.


## Round 105 — Buildings block every pin family

The user explicitly requested no pins visible through buildings, superseding the
Round 99 annotation overlay treatment. Renamed the shared helper to
`pinSceneDepth` and enabled depth testing for all its materials. This covers art,
historical markers, closures, SEPTA, Indego, Amtrak, aircraft/helicopters, ships,
search destinations, and score/concert connectors and anchor balls. Depth writes
remain off so transparent billboard rectangles do not mask other geometry.
Occlusion uses the actual GPU scene depth, including packed building meshes whose
CPU vertex data has been released. Layer toggles, distance limits, anchors and
entrance animation are retained.

Pin hit selection now runs the existing scene-occlusion check before draw-order
priority, allowing unobstructed hits to win over a hidden pin. Search destination
text additionally uses the line-of-sight rule already applied to event placards.
The neighborhood-name atlas remains a cartographic label layer rather than a pin.

Revised the six pin helper regressions to require depth-tested pins and rejection
of blocked picks. Added `tests/pins_gpu.html`, which runs the production shared
policy and bloom material hook with standard and logarithmic depth: badges, search
pins, event lines and anchor balls produce zero changed pixels behind a foreground
wall, appear in front or when uncovered, and badges respect partial building edges.
All four GPU configurations passed.

Full validation: 149 Python/Node tests, with one existing expected failure;
JavaScript syntax, documentation inventory and whitespace checks pass. Browser
verification at the Puma artwork on North 31st Street confirms the roof now
blocks the intersecting portion of the icon. The page reports no browser errors.

## Round 106 — Ground, river and sky material pass

Rebalanced the city’s environmental palette as one system. Streets now use a
shared charcoal/slate palette across the core, wide and far districts and the
bridge decks. Concrete walks, aprons and waterfront paving use warmer mineral
tones; brick walks/plazas, parking lots, service yards and rail ballast have more
distinct, restrained colours. Core sidewalks and the Society Hill plaza now use
the procedural surface treatment. Daytime street text is darker for contrast.
The green-surface classifier checks green against both red and blue, keeping
cool gray asphalt from accidentally receiving a grass texture.

The deterministic meadow tile retains its fine blades and mipmaps, with softer
tufts, greener colour, less dry-yellow contrast and much gentler macro variation.
The distance filters still fade detail to its mean, so the lawn does not darken
or shimmer when zooming out. Existing terrain/transport geometry is unchanged.

Water has a deeper green-blue body, a subtle olive-silt shoreline tint, gentler
long waves and restrained highlights. Angle-dependent reflections now use the
live sky palette in scene-linear light; solar/lunar glints use the active light
colour. The sky and weather continue to drive the shared river, basin and pool
materials. `liquify` now keys programs by its closure parameters so river and
fountain ripple scales cannot alias to the same compiled shader.

Clear sky shifts from the former violet-blue toward atmospheric blue and pearl
haze. Twilight has a peach horizon toward the sun and a cooler opposite horizon;
night uses a deeper navy/blue-gray palette. The reflection dome carries the new
twilight uniform. Sun/moon positions, cloud altitude, weather effects and the
existing lighting intensity/exposure remain intact.

Validation: `tests/environment_gpu.html` renders the actual production shaders
in four desktop/touch × standard/logarithmic depth configurations. All pass:
stable frozen surfaces, near/far grass brightness, mineral asphalt classification,
lane paint, rain darkening, snow layering, animated water, distinct fountain
scales, warm/cool sky response, darker night water and directional twilight.
The full suite ran 149 tests with one existing expected failure. Syntax,
documentation inventory and whitespace checks pass; the standalone page is rebuilt.
Visual checks covered Logan Square streets, Society Hill/waterfront paving,
Boathouse Row/Fairmount lawns and both rivers in daylight, sunset and night,
plus overcast at the Delaware. No browser errors were reported.

## Round 107 — Continuous traffic and a varied vehicle fleet

Replaced the traffic layer's unbounded reconciliation/render truncation with a
single bounded population that includes retiring vehicles. Cars already in view
keep their identities through time-of-day and density changes; new traffic is
prepared offscreen or beyond a broad distance fade. The initial population is
seeded under the loading screen. Offscreen births start at full coverage, while
distant transitions use a fixed-size ordered coverage fade instead of shrinking
cars into the pavement. Bodies, headlights and shadow passes share that fade.

The graph now splits ways where other endpoints meet their interiors: 6,052
runs become 9,047 connected pieces, preserving the same 1,080 km of roads.
Height checks preserve overpasses, and one-way direction is respected. Vehicles
retain their model, paint and distance overshoot through transfers, steer through
joints more smoothly, use discrete lanes and maintain length-aware following
gaps with gradual acceleration. Unresolved visible dead ends hold vehicles until
they can continue or leave view; they no longer force a U-turn or visible removal.
This remains ambient traffic, without a traffic-signal or cross-traffic priority
simulation.

Six distinct metric models replace the single three-box sedan: compact, sedan,
wagon, SUV, pickup and delivery van. Sloping glass, painted roofs, mirrors,
neutral trim, four tires with hubs, pickup beds and taller cargo bodies give
them distinct silhouettes. Six instanced batches retain the desktop/touch
population limits; commercial vehicles occur more often on arterials.

Validation: seven new production-code tests cover the pool over two simulated
minutes including camera and clock changes, graph connectivity/grade separation,
route identity and overshoot, birth spacing, following, dead ends and geometry.
The full suite ran 156 tests with one existing expected failure. GPU checks pass
for all models, paint/trim separation, fixed-size half fades, hidden lamps/shadows
and standard/logarithmic depth with and without bloom hooks. At the same fixed
Schuylkill viewpoint, a 20-second baseline recorded 55 visible births and 80
visible removals; the revised build recorded zero of each. A second 20-second
nighttime check after moving to the Delaware waterfront also recorded zero.
These are observed samples, not a guarantee covering every camera movement.
The standalone page is rebuilt; syntax, documentation and whitespace checks pass.

## Round 108 — Comcast Center opening and Phillies crown correction

Corrected the previous interpretation of the reference photograph. The dark
applied panels at 49, 98 and 147 m made the closed lower sky atria look like
additional cutouts, so those overlays are removed and the façade stays glazed.
The actual upper recess moves below a separate, complete lantern: modeled
247–271 m opening, 271–297 m crown. These datums are visual approximations of the
supplied photo. The rear façade remains closed. The architect's description of
the glazed tower and lower sky atria was also checked at
https://www.ramsa.com/expertise/project/comcast-center .

The cut is shared across the tallest shaft and its imported shoulder sections.
Previously those 266.8 m shoulders filled the bottom of the opening, leaving a
false shelf. `comcastFacadePieces` clips each affected horizontal slice against
the common opening. Side piers, recessed back wall and soffit make the depth
physical; no coping or LED panel spans the void. The daylight crown has clearer
glass instead of the former dark mechanical tint.

The crown's four faces and roof receive continuous light panels, above rather
than around the recess. Slots 200–201 identify Comcast Center within the shared
crown batch. Both the automatic Phillies game-day theme and the manual Phillies
selection set `uComcastSolid`, producing solid Phillies red without changing
other buildings' stripe palettes. Explicit custom palettes still select broad
horizontal bands and the existing solid option still works.

Validation: the 158-test suite passed with one existing expected failure.
Regression checks exercise the actual packed building parts and all rotated
opening plans. `tests/comcast_gpu.html` renders the production crown geometry and
shader in four standard/logarithmic depth and bloom combinations: every sampled
face and roof pixel is RGB (232, 24, 40) under Phillies, while the custom flag
palette retains three bands. A full-city canvas probe independently confirms
the same red. Day/night front, opposite and angled views were checked in the
browser without errors. Syntax, documentation and whitespace checks pass; the
self-contained page is rebuilt.

## Round 109 — Soft City Hall floodlight gradients

Mike pointed out the unnatural straight edges in City Hall's themed illumination.
The old fragment shader used binary pavilion masks and a brightness reset every
28 m up the tower. `cityHallFloodPatch` replaces these with overlapping Gaussian
light pools at the corner pavilions, entrance pavilions and tower. A soft union
keeps overlaps from forming bright seams, and continuous vertical attenuation
with a broad clock-stage wash removes the repeated horizontal cutoffs. The field
uses the block's world-space axes so separate wall meshes share the same gradient.
Window/stone detail, dark slate roofs and the existing night/theme controls remain.
Compared the old/new full-city views and inspected red, green and white nights
plus daylight in the local browser; the connecting walls now taper smoothly.

Validation: production shader GPU checks pass with standard and logarithmic depth,
including red/green/white routing and zero added light by day. Across the sampled
facade, the largest adjacent brightness change is 2/255 horizontally and 1/255
vertically; corner pools remain twice as bright as connecting wings. The real
procedural facade hook compiles and renders in both modes. All 158 Python tests
pass with the one existing expected failure. JavaScript syntax, documentation
inventory and whitespace checks pass; rebuilt the 27.52 MB standalone page.

## Round 110 — Soft lunar terminator

Mike requested a gentle fade between the visible moon and its unlit side. The
previous 0.07-radius blend read as a rigid edge at the normal display size. The
sky shader now uses a 0.22-radius blend at quarter phase, tapering it with the
lunar chord and available phase width so thin crescents retain their shape.
Screen-space filtering sets a minimum antialiasing width on small displays;
derivatives are evaluated outside the conditional disc branch. New and full
moon endpoints are explicit. Position, orientation, phase calculations, maria,
outer limb and the existing phase-scaled halo are preserved; no earthshine disc
is added.

Validation: `tests/moon_gpu.html` renders the production sky shader at 24- and
96-pixel moon diameters with standard and logarithmic depth. Quarter-phase
10–90% transitions cover 4 and 12 pixels respectively; integrated mask areas
stay within 0.24 percentage points of the requested phases. New moon is empty,
reversed bright-limb orientations match, and day/night plus post-pipeline shaders
compile cleanly. Crescent, quarter, gibbous and full samples and the actual city
sky were inspected. Syntax, documentation and whitespace checks pass; the
standalone page is rebuilt at 27.52 MB.

## Round 111 — Comcast Center's illuminated façade grid

Mike supplied nighttime references showing the crown's fine vertical mullions and
horizontal floor bands through the themed lighting. The independent light skin
had been obscuring that glass detail. Its shader now retains the full theme color
between darker framing: 1.52 m mullions, stronger posts every four panes, 4.15 m
floor bands and corner framing. Panel-local metric coordinates share the daylight
façade's datum and stay continuous through the half-metre lighting slices. The
periodic bars are integrated over the pixel footprint to soften under-resolution
detail without thickening it into flickering screen-width lines. The roof and CTC
carry zero grid coordinates. No additional geometry or draw calls are introduced.
Phillies still fills the crown red, and custom palettes keep their selected bands.

Validation: the production crown GPU check passes standard/logarithmic depth and
post on/off, with visible mullion and floor-band contrast in red and green, custom
red/white/blue bands, a red roof, and no lighting across the opening. In the red
sample the pane is RGB (232,24,40), a mullion (209,21,35), and a floor band
(150,11,22). The fixture now includes the opaque crown behind its lighting skin,
as in the actual city; without it, far-side panels incorrectly overwrite front
samples. The 158-test Python suite passes with one existing expected failure.
The full city is inspected from Mike's view. Syntax, documentation and whitespace
checks pass; rebuilt the standalone page (27.52 MB).

## Round 112 — Restore visible, sustained traffic

The no-pop-in pass had left visible streets under-supplied: cars could only be
born offscreen, random junction choices favoured busy arterials, and no upstream
route was reserved to refill an empty visible block. The traffic bake also still
ended at the old wide-area boundary, leaving most roads west of the Schuylkill
view without any traffic data. Short ways under 25 m and simplified junction
vertices had broken additional connections.

The bake now includes city OSM and the supplemental park drives, deduplicated by
way ID. It follows the rendered far-ring residential extent, retains connectors
down to 2 m, and simplifies only between shared junctions. The new 700 mm unit in
the header covers the city without int16 coordinate saturation; the decoder also
accepts the legacy zero/200 mm header. The baked network contains 29,749 ways and
5,614 km before runtime water/site cuts. The compact junction-preserving bake
adds about 0.69 MB to the previous standalone build, now 28.21 MB.

Initial loading seeds the visible roads uniformly. Later shortages search
upstream for an offscreen spawn and reserve a legal route into the empty block;
inbound vehicles count against demand. Junction choices account for occupancy,
nearby streets get refill priority and a modest density lift, and offscreen
surplus vehicles release pool slots. The 2,200 desktop / 550 touch limit, six
vehicle models, lane spacing, directional links, depth and coverage fades remain.
Visible vehicles still survive density changes and unresolved dead ends.

Validation: the full suite ran 160 tests with one existing expected failure;
the nine traffic tests passed again after compacting the bake and matching the
rendered street extent. New cases check actual upstream arrivals without visible
births/deaths, retained short links, geographic coverage and unsaturated packing.
The full city was inspected at the Schuylkill, Center City and waterfront, in
daylight and evening. The original Center City sample had 11 moving cars within
the frustum; the first revised sample had 127, with zero visible births/removals
across the sampled camera transition. These are frustum counts, not an occlusion
or whole-city guarantee. The final evening Schuylkill sample had 342 moving cars
versus one in the baseline. Observed desktop frame-time medians remained around
17 ms. Build, syntax, documentation and whitespace checks pass. No deployment.

## Round 113 — Rocky on the upper pedestal

Moved the existing bronze Rocky figure from the lawn beside the lower steps to
the center of the light octagonal pedestal on the museum's upper landing, as
requested. His feet meet the pedestal top at T + 0.9 m, and he retains the
raised-glove pose facing Eakins Oval. Removed the old two-tier base and the
former fountain's hidden water insert. The local Rocky search entry now shares
the built statue's horizontal position and pedestal elevation.

Verified the rebuilt city in close and museum-wide views: the figure is centered
and rests on the light stone, with no duplicate at the old location. The search
anchor matches (-3084.754, 19.819972, -2215.514). Browser error log was empty.
JavaScript syntax, build, documentation and whitespace checks pass.

## Round 114 — complete window rows below the roofline

The shared fabric shader now reserves an opaque roofline band: roughly 0.65–0.9 m
on low buildings, 0.85–1.4 m on masonry towers, and 1.25 m below the deeper
Victorian/siding cornices. Window coordinates fit complete rows into the available
wall with at most 17% vertical compression. The highest point of each opening,
including its frame/lintel, must fit; storefronts, fanlights and other ground-floor
variants use the same clearance. Masonry courses and roof trim retain their real
world coordinates. Both the core float wall attributes and packed citywide wall
attributes use this shared behavior. Purpose-built curtain walls, landmark crown
lighting and the Society Hill Towers' existing parapets retain their own treatment.
Distant averaged window light also stops below the roofline.

Validation: the production shader passed 2,184 GPU roof-clearance cases across 26
façade variants, seven building heights, explicit/fallback floor heights,
core/packed attributes, elevated bases, three detail budgets and both depth modes.
The original shader fails the same regression on Georgian and stone-pier façades.
All 30 building-material styles also passed the existing four GPU configurations,
including packed/core equivalence and nighttime illumination. The Python suite
ran 160 tests with one existing expected failure. Syntax, build and docs checks
passed. Also inspected close and neighborhood-wide Old City views in daylight and
at night; the browser error log was empty. Rebuilt the local HTML; no deployment.

## Round 115 — tracks on the elevated railway

Added two complete tracks to both existing Market–Frankford elevated alignments:
14.84 km from the Callowhill and 46th Street portals toward Frankford and 69th
Street. Each has a dark track bed, paired running rails with feet/webs/heads,
outside third rails, and 41,236 instanced cross-ties at a continuous 0.72 m pitch.
`elTrackFrames` and `elTrackRibbon` share mitered cross-sections through bends;
`elTrackSleepers` keeps its distance phase across segment boundaries. All details
ride the existing smoothed and portal-ramped deck profile. Pitched deck boxes now
use their slope length. Three meshes total, two added draw calls; upload releases
static geometry buffers. `__dbg.elTracks()` reports counts.

Visually checked North Front Street, West Market Street and the Kensington bend.
The four running rails stay continuous and the ties sit on the deck. No browser
errors. Three production geometry tests cover bend gauge/join continuity, upward
railhead normals, sleeper phase on uneven segment lengths and sloped profiles,
finite full-route geometry and instancing. The full suite passed 163 tests with
one existing expected failure. Build, JavaScript syntax, documentation and
whitespace checks passed. Rebuilt locally; no deployment.

Also checked SEPTA's public API documentation (https://api.septa.org/) and actual
TransitView responses for L1, B1, B2 and B3 on Sep 18, 2026. L1 returned five rows
and B1 seven; all twelve had exactly the same coordinates (39.952187, -75.15995),
VehicleID "None" and Offset 998. B2/B3 were empty. These are not usable vehicle
positions. Existing bus/trolley live tracking stays in place. No subway trains
were presented as live. A future timetable-based animation must explicitly say
its positions are estimated; a reliable live subway layer requires another feed.

## Round 116 — I-95 wall extent and El tunnel approaches

The broad white barrier across the Callowhill lanes was the core's hand-built
Front Street trench wall, extrapolated from z = -1200 to 1800 although the
constructed trench and its heightfield end at CORE_EXT (-520 to 850). Toggling
that mesh in the reported view confirmed the cause. Bound both straight walls
to the actual core trench; mapped overpasses keep their own parapets outside it.

Both El alignments now share a cached `elTrackProfiles` result for rails, deck,
excavation and portal masonry. The first 280 m climbs smoothly from a tunnel
5.6 m below the starting ground to the elevated alignment. Concrete retaining
walls, coping, a lintel and a short shadowed covered continuation frame each
entrance. Rails and ties remain continuous into the tunnel. Portal details join
the existing structure batch, adding no draw calls. `__dbg.elTracks()` also
reports each portal and its excavated length (77.4 m Callowhill, 170 m West Market).

`elPortalClipGround` subtracts the exact 9 m-wide opening from indexed wide/far
heightfield triangles, retaining outside ground and interpolated heights,
normals and colours. It does not remove coarse 25/50 m cells or lower adjoining
highway pavement. The ground registry retains the surrounding surface grade for
road fitting; `elPortalAt` explicitly excludes trees and grass from the opening.
The close-up visual pass caught floating grass instances and verified their
exclusion. No change to SEPTA live-data behavior.

Checked the reported aerial view, both tunnel mouths at track level and the
remaining Society Hill trench. No browser errors. Extended the production El
geometry tests with excavation-area conservation, zero ground coverage inside
the openings, interpolated attributes, upward winding, rising portal grades and
tunnel clearance. All 165 tests passed with one existing expected failure;
JavaScript syntax and the local HTML build passed. No deployment.

## Round 117 — Roof lighting follows the building footprint

The reported view at (-1593.8, 208.4, -712.0) exposed a solid red slab cutting
across the chamfered/recessed rooftop next to the green-lit W/Element tower.
The generic flat-roof `band` crown was a filled oriented bounding box, so its
horizontal faces spilled across roofs and its sides ignored the actual plan.

`roofLightBand` now builds only a vertical perimeter fascia from the surveyed
footprint, with shared mitered corners, 0.20 m wall clearance and its upper edge
0.20 m below the roof. No horizontal luminous roof cap remains. All flat-roof
band crowns use the helper; existing theme colours, palette slots and batches
are preserved, with no extra draw calls.

Compared before/after at the exact reported camera with the user's red, white
and green palette, then checked the opposite side in daylight and at night,
plus surrounding western skyline bands. No browser errors. Production-geometry
tests audit all 23 currently rendered band landmarks against the real packed
plans, plus rotated rectangles, chamfers and concave returns in both windings.
They check finite positions, outward vertical faces, roof exclusion, joined
corners and clearance. One Logan's existing spec does not match its tall packed
part, so it has no band to audit; no matching/data changes in this round.

The 167-test suite completed successfully with one existing expected failure.
JavaScript syntax, build, documentation coverage and whitespace checks passed.
Local preview rebuilt; no deployment.

## Round 118 — Soft architectural theme lighting

The roof in the reported Murano-area view (-2641.1, 208.5, -1042.4) still read
as a painted stripe after the footprint correction. Replaced the 2.6 m solid
flat-crown bands with narrow 0.32 m fixtures beneath the parapet and a separate
4.8 m facade wash that falls smoothly downward. Notched/sloped crowns now use
their actual wall plans for both fixtures and wash instead of filled roof boxes.
All wash skins discard horizontal caps and use continuous shader falloff,
including feathered upper/lower edges and distinct uplight/downlight profiles.

The shared theme rendering now explicitly identifies architectural emitters for
bloom. Saturated red/blue sources previously sat below the luminance threshold,
so increasing brightness either did nothing or washed them toward pastel.
`architecturalBloom` encodes source coverage above 1 in the existing HDR scene
alpha, preserving ordinary geometry and pin masks. Transparent lights use
independent alpha blending without changing their color blending. The bright
pass filters four samples and extracts a restrained peak-channel halo; the
composite protects the source pixels so large crowns retain their colors/grid.
Opaque buildings still block the source before the blur. Theme fixtures,
Comcast crown panels, City Hall, wash skins, bridge nodes and the existing
Boathouse Row outline batch share this treatment. No extra scene passes,
render targets or per-fixture draw calls. Direct-render/mobile clients retain
the softer fixtures and facade falloff without post-process bloom.

Visual checks covered the exact reported roof, the nearby skyline, Comcast's
custom bands and solid Phillies crown, City Hall, Boathouse Row and daylight.
No browser errors. The new GPU regression runs the production post pipeline
with standard/log depth and opaque/transparent sources: colored halos fade,
covered sources remain blocked, labels do not glow, and large panels preserve
their palette. The red fixture measures (232,24,40) while its surrounding halo
fades to black. Fallback wash gradients and daylight-off checks also pass;
existing Comcast-grid and City Hall GPU pages pass. The 168-test Python/Node
suite completed with one existing expected failure. Syntax, build, documentation
coverage and whitespace checks passed. Local build only, no deployment.


## Round 119 — Layered interior window lighting

Replaced the uniformly filled lit windows across houses and skyscrapers with a
shared room shader. Homes have warm, offset lamp pools and shaded window reveals;
offices have a broader ceiling wash, mixed warm/neutral/cool temperatures and
suite-level occupancy. Individual rooms vary in brightness, with partial blinds,
curtains and quiet shadows near the floor. The opening coordinates follow each
facade style's actual windows, including paired and arched sashes and storefronts.
Sash bars, mullions and residential posts now block the interior emission instead
of lighting up with the glass. Existing parapet clearances and theme lighting stay
in place. The curtain-wall material starts from white emission so its own room
colors are not multiplied by a second amber tint.

The same treatment covers Ryland's custom glass and the explicitly modelled
Society Hill towers. The latter carry local room coordinates through their merged
glass and curtain geometry, so their overlays agree on the room being lit. Lobby
glass gets a softer continuous ceiling wash. All room identities are deterministic;
fine lighting detail converges to an average by pixel footprint. No per-window
light objects, additional draw calls, textures or render targets. Interior shader
work is skipped when the night lighting is off.

Visual review compared the original flat windows with the new house windows,
Society Hill / Ryland, Center City offices, Comcast and the wider skyline, plus
daylight. Runtime reported no shader errors. The new GPU page checks actual room
profiles and production apartment/facade hooks in standard/logarithmic depth:
all occupied test rooms have a recessed gradient; occupancy is identical across
repeated renders and the low-resolution pass; home/office temperatures differ;
sash frames stay dark; horizontal glass and daylight have no interior emission.
The roofline GPU sweep passed 2,184 cases with zero glass or light in the top
half-metre. All 30 facade styles compile under both depth modes and detail budgets.
The Python/Node suite completed 168 tests with one existing expected failure.
Local preview rebuilt; no deployment.


### Round 120: Reflective glass windows (Sep 19)

Reworked window optics across the shared house/apartment facade styles, Center
City curtain walls, Ryland and Society Hill Towers. A shared glass shader now
separates polished panes from matte sash frames and masonry, uses dielectric
Fresnel with a stronger coated-glass response on skyscrapers, and reduces the
opaque diffuse fill behind the glass. Small fixed variations in pane normals
and surface roughness break up perfectly uniform reflections; subpixel distortion
fades by footprint. The existing warm interior gradients, room identities,
window grids, roofline gaps and themed crown lighting remain in place.

The shared environment probe now decodes the sky's display colors to linear
radiance, with sharper PMREM filtering and approximate weather-driven clouds
across the reflection hemisphere. The oversized reflected sun was replaced by
a compact glint that follows the sun's color, twilight and cloud cover. Removed
the separate painted skyline tint from curtain-wall diffuse color. Reflections
are still the lightweight shared sky/ground/building-silhouette approximation,
not per-building scene captures or ray tracing. No new scene draws, render
targets, textures or per-window lights.

Visual checks covered houses, apartment glazing, Center City towers and Comcast
in daylight and after dark. The new production GPU test checks angle-dependent
reflection strength, blue-sky response, deterministic frames, pane/frame/masonry
roughness isolation, linear probe colors and a hidden reflected sun at night in
both depth modes. The existing interior-lighting GPU checks pass unchanged.

All 30 facade styles passed the four depth/detail configurations without shader
errors. The complete Python/Node suite ran 168 tests with one existing expected
failure; syntax, build guards, documentation coverage and whitespace checks passed.
The roofline GPU sweep passed all 2,184 cases with zero glass or emission in the
upper clearance strip. Local preview rebuilt; no deployment.


### Round 121: Continuous elevated I-95 southern approach (Sep 19)

Fixed the abrupt drop in Mike's view at `(218.4,119.5,1006.7,-0.899,-0.364)`.
The overpass baker clipped decks at the rectangular detailed-core boundary, and
untagged I-95 embankment segments between mapped bridges fell back to the core's
generic trench. Both carriageways now continue across that boundary, through
their connected southern approach, and gradually descend toward the mapped
tunnel exit. The vertical profile is a model estimate rather than surveyed data.
Only the two existing mainline chains and two connected ramp chains change;
532 other elevated chains, all sunken runs and the Vine corridor remain identical.

Ramp junction nodes now survive profile simplification so the joining road has
the same xyz as the through deck. The core street builder cedes owned road
segments to the actual deck, whose lane attributes now paint the elevated
surface. Cars, live buses, closures and the label height lookup take their
aligned deck height even when the surrounding bare-earth sample is higher.
This eliminated a measured 6.49 m traffic height error along the emerging ramps.
Re-baked street labels moved one Columbus Boulevard placement clear of a ramp;
the 3,774-label count and the font atlas/name ordering stay unchanged.

Browser checks covered the reported view and lower/northern approach views.
All three ramp-to-mainline joins agree exactly after runtime terrain clearance;
189 local traffic samples agree with deck height plus wheel clearance within
0.000003 m. The new tests exercise the classifier, continuous baked carriageways,
gradual transition, exact joins, production ownership/height lookups, lane
geometry and below-earth traffic heights. The terrain test also checks core
deck suppression without removing crossing streets. The full suite ran 175
tests with one existing expected failure; syntax, build, documentation coverage
and whitespace checks passed. Local preview rebuilt; no deployment.

## Round 122 — the phone's memory, the SEPTA feed, and Rounds 120 and 121 brought over (Sep 19)

**Mike, after the folder went live: "The mobile version is loading multiple times and then I am
getting the error 'a problem repeatedly occurred on philly3d.com'. Also, wire up septa and ais."
And, with `GLASS-I95-HANDOFF.md`: "Can you make these changes as well."**

### Rounds 120 and 121 ported, not redone

The handoff describes finished work in a second checkout (`~/Desktop/Codex/SHT`). A recursive
diff showed that tree to be this one plus exactly those two rounds, with no line here missing
there, so the ten files were copied across as they stood (`app.js`, `bake_overpasses.py`,
`overpasses.json`, `street_labels.json`, four test files, `devlog.md`, `handoff.md`). The page
built here came out byte-identical to the Codex build, and the suite ran the handoff's own 175.

### The phone: measured, not guessed

"A problem repeatedly occurred" is iOS killing a tab for memory and giving up after the reloads.
Every build was staged with a counter injected ahead of the page (it wraps `bufferData`,
`deleteBuffer`, `texImage2D`, `texStorage2D` and `renderbufferStorage`, and logs the JS heap at
each build step) and loaded under a touch profile (740 x 360, coarse pointer, so `isTouch`):

| build | GPU buffers settled | JS heap peak | JS heap at Ready |
|---|---|---|---|
| Round 86 | 602 MB | 993 MB | 565 MB |
| Round 88 | 716 MB | 1,627 MB | 536 MB |
| Round 90 | 780 MB | 1,280 MB | about 460 MB |
| Round 121 (what was live) | **890 MB** | 1,292 MB | **1,222 MB** |
| Round 122 | **764 MB** | 1,567 MB | **676 MB** |

The largest single step in that table is Round 88's own street drape: it handed every street to
its mesh as a triangle SOUP, three fresh vertices a triangle through boxed JS arrays, and by
Round 121 that was 2.92 M triangles on 8.75 M vertices. Within one strip a vertex is a function
of its position alone (the ground's height, the lane paint's u and s, one colour), so `roadWeld`
welds the soup as it arrives: a map of the strip's points at a centimetre, a repeat costing an
index and nothing else, the street index (labels, terrain clearance) still fed every triangle
through `rememberStreetTriangle`. 8.75 M vertices became 2.78 M. `packNormals` stores the street
meshes' normals as normalized bytes the way `VBuf` packs the buildings' (12 B to 3). An
attribution pass over the scene (bytes by material) put the fabric at about 390 MB for 13.35 M
vertices, already packed at 29 B, and everything else under 65 MB a material, so the streets
were the place to cut. Peak heap is GC-timing noise in a throttled pane (Round 88 itself read
1,627); the heap at Ready and the settled buffers are the honest columns. Verified by capture on
the desktop profile: the Passyunk interchange and Spruce Street with their lane paint, and Round
121's I-95 view. Not verifiable from here: a real phone. If it still dies, the next tranche is a
phone-only street path (no subdivision in the far ring) and the 158 MB of textures.

Found on the way and left: the drape costs 34 s of build in a hidden pane against Round 88's 3 s
in the same conditions, so Rounds 95 and 96 made it about ten times dearer; and the shader
program count went from 28 (Round 90) to 70.

### The VPS: SEPTA live, AIS staged

`/septa.json`, `/ais.json` and `/b` had answered 404 since the vhost was hand-merged: the live
file never carried their locations, and `septa-bake` was never installed. With Mike's word: the
vhost backed up to `/root/philly3d.vhost.bak-2026-09-19-183137`, two `location =` blocks added
after the lights block in the amtrak block's shape (`gzip_static`, `max-age=10`, ACAO `*`),
`nginx -t` green, reload; `septa-bake.service` installed and enabled (the script on the box
already matched the repo's by sha256). `/septa.json` answers 614 vehicles, 8 s old, gzipped.
`ais_relay.py` and `ais-relay.service` are installed but NOT started: the relay needs the
aisstream key in `/etc/philly3d/ais.env`, and placing a key is Mike's to do (one command, in the
session's reply). Until then the page's own socket fallback carries the ships as before. `/b`
stays 404: the beacon is the owner's decision (ops/README section 5).

## Round 123 — the welcome card's copy (Sep 19)

**Mike, with a screenshot of the welcome card: remove the period after Philadelphia, change "A
New Perspective" to "Data In Motion", remove "Fly above the skyline. Follow the rhythm of the
streets. Discover a living Philadelphia, from the rivers to the rooftops.", remove "Made for the
Curious. Built for Exploring."**

`template.html`: the title is `Philadelphia` over `Data In Motion` (no period on either line, to
match the first), and the `.sub` paragraph and the `.welcomehint` footer are gone from the
markup. Their CSS rules stay, harmless, so a later line can come back without restyling. The
facts row and the button close up under the title. Verified by the pane's own screenshot of the
card during load. 175 tests pass.

## Round 124 — the phone again: a lighter phone build, a breadcrumb, and a lite build it can fall back to (Sep 19)

**Mike, after Round 122 went out: "a problem repeatedly occurred on philly3d.com".**

Round 122's cut was not deep enough, and from here a phone's limit cannot be seen, only the
page's footprint under a touch profile. Two lessons about that instrument first. Chrome's
`usedJSHeapSize` is mostly garbage during a load: the same build read a 1,048 MB peak in one run
and 1,483 in the next, and both settled to about 450 MB live after a nudge to the collector, so
the heap columns in Round 122's table are noise and only the GPU columns are honest. And the
probe's texture figure assumes four bytes a pixel, so an R8 atlas reads four times its size.

What every phone now gets:

- **Only the towns inside the flight limit.** The towns across the line are scenery the camera can
  never reach, and they cost 164 MB of GPU buffers. `raiseRing` takes an optional `keepAt`; a
  touch device passes `insideLimit` (the city line buffered 2 km: the Navy Yard's south half, the
  near bank of Camden, the first streets over the county line) and the rest goes to meadow. 66 MB.
- **The Indego badge atlas at half size** (`INDEGO_ATLAS_K`): 4096 x 2048 was a 33 MB canvas and a
  44 MB texture with its mips for badges drawn at a few dozen pixels. The UVs are fractions of the
  atlas, so only the canvas and the drawing transform change.
- **The streets' build, faster on every device.** A first guess blamed `drapeConvex` clipping
  each strip against all ten ground grids, and a bounding-box rejection went in (harmless, the
  same triangles). It was the wrong suspect: 20,000 drapes cost 120 ms. The time was in what each
  emitted triangle did next: `rememberStreetTriangle` paid for four arrays, a bounds array, a Set
  and a closure for every one of 2.9 M street triangles before finding, nearly always, that no
  label frame and no terrain patch stood in its cell. `streetTriNear` asks that first, on bare
  numbers, with a box a centimetre generous so its no is exactly the full walk's no. Same pane
  state, back to back: **32.7 s to 18.6 s of street build, 116 s to 83 s to Ready** (about 3 s
  and 18 s when the pane is not throttled), with the terrain index's counts (210,154 surfaces,
  44,573 triangles, 27,048 trimmed) and the labels' 243,752 triangles identical before and after.
  And thirty million fewer short-lived objects for a phone's collector. A lesson for the capture
  skill: the pane's throttle state changes between loads, so a timing is only comparable with
  the load taken immediately beside it.

Settled GPU buffers under the touch profile: 890 MB (what was live this morning), 764 (Round
122), **708** now, against Round 86's 602.

And what a phone that still dies gets, because guessing its limit a third time is not a plan:

- **A breadcrumb.** `bootMark` writes the current build step to `localStorage` (`philly3d.boot`)
  at every step and at Ready; `bootClear` takes it back 20 s after Ready (the first frames upload
  another fifth of the geometry, so the city has to stand a while) and on `pagehide`, which an
  ordinary leave fires and a kill does not. A load that finds a fresh breadcrumb knows the last
  one died, and at which step.
- **A lite build.** A touch load that finds one builds LITE: no towns at all, the far ring's
  BUILDINGS only within `LITE_R` 8 km of the centre (its streets, parks and ground stay citywide,
  so the map still reads), a 1024 shadow map. **532 MB** of buffers and 8.2 M triangles against
  15.7 M. The choice sticks to that device for a fortnight (`philly3d.lite`), or every other visit
  would try the full build and die again; then it gets another go. `?lite=1` forces it on any
  device, `?lite=0` forbids it and clears the flag, `__dbg.boot()` reports what was found.

Verified in the pane: the breadcrumb read "Raising the rest of Philadelphia" mid-load; a leftover
breadcrumb planted from another page on the origin made the next touch load report one failure
and build lite; the lite numbers above; `tests/test_boot_lite.py` guards the wiring and that no
street emitter pushes a soup again. 180 tests pass. Not verifiable from here: the phone itself.

## Round 125 — where you are: a location button (Sep 22)

Mike: "Can we add a feature/button that puts users right where they actually are using
Geolocation? If they are not in Philadelphia, take them to City Hall and show a message along the
lines of 'You are not located in Philadelphia'."

A target button (`#btnLocate`) sits in the bar after Sun & sky, before the camera. It asks the
browser for one fix on the tap and never before it (`navigator.geolocation.getCurrentPosition`,
low accuracy, a 12 s timeout, a fix up to a minute old accepted), converts it through the scene
frame like a SEPTA vehicle, and tests it against the REAL city line: `CITY_LIMIT.city`, the OSM
relation that `city_limit.json` has carried beside the buffered `bound` since the boundary was
fetched, not the 2 km flight buffer. Camden and Cheltenham are within the buffer and are not
Philadelphia, so they get the City Hall answer.

- **In the city:** `searchFlyTo` glides in and circles the spot, as a search result does, under a
  "You are here" search mark, with a notice that says so. A fix coarser than 400 m (a desktop on
  wifi) reads from 600 m instead of 300 and the notice gives the radius in feet or miles.
- **Anywhere else, or no fix to be had:** the City Hall viewpoint (`viewpoints`, the same glide
  as the Explore row) and a notice: "You are not located in Philadelphia. Here is City Hall
  instead." A declined prompt and a failed fix get their own line to the same place; a browser
  without the API too.
- **The notice** is a new element, `#notice`, a slate line centred under the bar for 7 s with a
  short ease-in, because `#hint` is hidden on phones and the card follows a scene anchor.
  `role="status"` for readers.
- The position is used once for the glide and kept nowhere. The guide's last card says so.
- `__dbg.locateAt(lat, lon, acc)` drives the same path with a given fix, `__dbg.inPhiladelphia(x, z)`
  tests the line, `__dbg.notice(text)` shows a line.

Verified in the pane: `inPhiladelphia` true at Independence Hall, false at the Camden waterfront and
at Cherry Hill; a fix at Independence Hall glided the camera to an orbit about (-451, -371) under a
"You are here" mark; a Cherry Hill fix parked the camera at the City Hall stop (-1560, 145, -280)
with the notice under the bar; the real button with the browser's geolocation stubbed showed the
busy pulse while waiting, took the fix, and on a code 1 error went to City Hall with the declined
line; at 812 by 375 the bar holds all seven buttons and the notice sits 12 px under it. 180 tests,
the two `test_lights_bake` failures fail identically at HEAD (a fixture row count, 6 against 5) and
were: `deploy_philly3d.sh` gates on the suite and refused. Fixture row f ended on 2025-09-20 and the two
`Main` tests baked on the wall clock, so on 2026-09-21 it aged past `KEEP_DAYS` and the count fell from 6 to 5.
The tests now pin `bake_lights.time.time` to the file's NOW. 180 tests pass. Page 28.25 MB, +5 KB.

## Round 126 — the Marriott's porte-cochere, and the pins' depth (Sep 22)

Mike, with a screenshot of the Marriott Old City from over Front Street: "The portico for the old
city marriott is in the wrong place. It should be in the corner behind the tree from this angle."
Then, with a second screenshot of a bus on Columbus Boulevard wearing a marker pin and an art pin
from blocks away over its badge: "I should not be able to see further pins clipping through closer
pins. I am also still seeing a lot of building clipping with the pins."

### The porte-cochere

The canopy was anchored to the polygon's westernmost vertex, which is the far end of the north wing.
It now finds the L's inner corner itself: the reflex vertex with the longest pair of edges, the face
leaving it (the north wing's courtyard side), the outward normal by `pointInPoly` (a winding guess
first put it inside the wing), and stands 2 to 16 m along that face from the corner, 7.5 m into the
courtyard beside the circular drive, aligned by `ryAlign`. Verified by capture at Mike's own pose
(`p=3.9,22.8,-90.3,1.281,-0.379`): the canopy is in the corner behind the tree.

### The pins

Every pin is a screen-facing quad that holds its size with distance, so beside a facade it can stand
the size of a house. `pinSceneDepth` depth-tested its own corners against the city, which sliced it
wherever the facade passed through the quad, and wrote no depth, which left the pins in draw order
among themselves: the SEPTA badges are built before the markers and the art, so a marker three blocks
off painted over the bus in front of it, which is Mike's screenshot.

Now every corner of a pin carries the depth of its ANCHOR, the instance origin at the pin's tip
(`PIN_ANCHOR_GLSL`, chained after any hook the material already had: Indego's atlas remap, `postRaw`'s
exposure undo, with `customProgramCacheKey` telling the programs apart). Nothing beside the tip cuts
the quad, only a wall in front of the tip hides it, so Round 62's occlusion stands. With one depth per
pin the flat pins write depth (`alphaTest` 0.5 keeps the sprite's clear pixels out) and sort among
themselves whatever the draw order. Under the logarithmic depth buffer the fragment depth comes from
`vFragDepth`, so that carries the anchor's w; the plain buffer takes `gl_Position.z`; the WebGL1
no-extension path takes the log of it. The search tether stays a plain line that writes none.

Verified in the pane, same poses before and after: at the densest pin cluster near 12th and Walnut
the art pin stands whole beside a facade with the marker pin behind it; from 70 m behind a live bus
on Market Street the badge covers the marker and art pins beyond it whole, the marker's blue peeking
over the badge's top edge as it should; no shader errors in the console. `tests/test_pins.py` now
asserts the flat pins write depth at `alphaTest` 0.5, the tether does not, the anchor block lands in
the vertex shader on both depth paths, a chained hook still runs, and the two programs never share a
cache key. 181 tests pass. Page 28.25 MB.

## Round 127 — pins shown or hidden whole, the corner smear, A Man Full of Trouble, the street names, the lights on load (Sep 22)

Mike, in a run of messages with screenshots: a marker pin still cut by a building; "I dont want the
concert pins to clip through buildings, they should be obscured if a building is in between"; "remove
whatever that black shadow in the upper left corner is"; A Man Full of Trouble "needs to be reworked"
with a photo; street names "a bit lighter to stand out, not a ton"; "the colored lights seem to start
off white and then slowly change into the proper color".

### Pins: all or nothing

Round 126 gave a pin its tip's depth, which stopped walls BESIDE a pin slicing it, but any building
nearer than the tip still cut the part of the pin it overlapped on screen. Now:

- **Nothing cuts a pin.** `pinDepthClear`, an invisible mesh at renderOrder 99, clears the depth buffer
  in its `onBeforeRender` (with the depth mask forced on, or the clear does nothing after a
  depthWrite-false object). The pins at 100 then sort only among themselves on their anchor depths.
- **A hidden pin is hidden whole.** Every few frames (5 desktop, 10 touch) `pinOccCapture` draws the
  city's view distance into a 256-pixel-wide target with a packed-RGBA override material, every
  transparent, line, point and pin object hidden, the shadow map untouched, and reads it back. Each
  instanced pin carries `aPinVis`; `pinOccApply` tests every tip against the image through the
  capture's own matrices (a 3x3 neighbourhood, 2.5 m + 2% bias) and a hidden pin collapses to a point.
  Taps skip a hidden pin. `__dbg.pinOcc()` reports captures and hidden counts.
- **Concert placards and score bubbles** (a DOM placard, a tether and a ball) are shown or hidden
  together by `pinBlocked` on their roof landing point, the depth image within 4 km, `losClear`'s
  roof grid beyond it. The tethers draw with the pins now, so no building cuts them either.

Measured: street-level poses in Center City hide 19 to 34 pins whole; beside a facade the art pin
stands whole over the building's edge where Round 126 cut it. 181 tests.

### The black smear

The 74 landmark labels (off by default) were created with `visible: false` but at full opacity, so
`updateLabels`, which only hides a label it thinks is visible, never touched them: they sat stacked
just above the screen's top-left corner and their box shadows bled into view. A label now hides
whenever its opacity is not already 0.

### A Man Full of Trouble

Three faults: the storefront pass dressed its street face as a shop under a purple awning (storefronts
never checked for a researched model; now they skip any custom footprint), the old model's pent,
cornice and dormers faced north, away from Spruce Street, and its walls took style 0, the generic
window pattern. Rebuilt from Mike's photo on blank walls: window, door, window, door below, four
windows above in cream shutters, a shingled pent on a cream fascia, a cream cornice, a steep gable
roof with two dormers, a chimney at the west end and one behind the ridge, downspouts. Calibrated in
the pane: the detail material lifts a sunlit flat far past its stored value, so shingles stored
`#33241b` read pale beige at 2 pm and `#120c08` reads the photo's cedar brown.

### Street names and the lights

The day ink goes from `0x0b1013`, the asphalt's own value, to `ST_INK_DAY` `0x323c46`; a first try
at `0x4a5661` read clearly pale, more than Mike asked. The skyline lights landed their first
evaluation, but that runs before the day's scoreboard and the served calendar arrive, and their
arrival eased twenty seconds from white; data for the date already in view now lands at once, and
only a change of date eases.

## Round 128 — Foglietta Plaza and the Vietnam memorial on the I-95 deck (Sep 22)

Mike, at `#p=142.3,14.9,212.8,0.457,-0.630`: "this view is rendering the sidewalks above the street.
That entire area is actually above 95. Foglietta plaza and the veterans memorial."

The core's two caps were raw z bands, -25 to 64 and 64 to 122. At the trench the street grid runs
10 degrees off the axes, so Dock Street crosses at z 25 to 35 and Spruce at z 130 to 144: the first band
roofed 55 m of open trench north of Dock Street and the second stopped short of Spruce, leaving the
whole memorial's lawns and paths lying in the cut beside the lanes. And even where a band was right,
the plaza never showed: the slab stood 0.12 m over the ground, and as a single quad over its span it
interpolated straight between its ends and stood over the ground mid-span too, so every capped metre
was a bare pale sheet with trees on it (the old Foglietta band included, measured by hiding meshes one
at a time over the deck and reading the pixel).

Now one deck, `{ s0: 11, s1: 222 }` in the along-Front coordinate (`capAt`, square to the cross streets),
from Dock Street's south kerb to the memorial park's south edge, both read off the OSM park outlines;
the slab is a 5 m by 4 grid on `frontDem` 0.3 m under the drawn ground, flush with the trench walls,
with a concrete fascia down its river edge where it stands over the shelf; the portals follow the new
ends. The expressway's painted name follows the motorway's own grade in the core cut (it floated at
street level across Dock Street) and is not painted under the deck. `tests/test_terrain_patches.py`
seeds the new cap form. Verified by capture: the plaza's lawns and path grid, Spruce Street across it,
the memorial's circle, I-95 diving under at Dock Street and out past the memorial. 181 tests.

## Round 129 — the Irish Famine Memorial, and light in the stadium lots (Sep 22)

Mike, with two photos: "Can we also add a statue similar to the Irish Famine Memorial on the corner of
spruce and 38th parallel?" Then: "We need lamp posts in the parking lots for the stadium. They look too
dark at night."

**The memorial** stands in a paved apron north-east of Spruce and 38th Parallel Place (84, 104), its long
axis with Spruce Street: a rounded granite plinth, a low bronze rock of jittered low-poly lumps rising to
a prow at the east end, nineteen cloaked figures on and around it a touch over life size (hats, shawls,
bundles, the low famine end's figures kneeling), two Celtic crosses and three gravestones at the west end.
Representative, not a survey of the thirty-five figures. The trees, the grass tufts and the walker are
kept off it (`registerPoly`, `noSow`, collision segments). The bronze and granite are stored nearly black
(`#050403`, `#0b0c0d`): the detail material's lift, as the tavern's roof measured in Round 127, read the
first pass's `#0c0806` as milk-chocolate brown.

**The lots**: 741 light masts on a 42 m grid square to the street grid, 5 m in from every lot's edge in
`parking_south.json` (`LOT_LAMPS`, laid in the lot loop), ride the streetlamp inventory as 15 m LED
poles (glow points, the near pole meshes, the G layer, the photocell), and each pools its light on the
asphalt: a 27 m disc between the lot and its stall lines, fading from the foot, additive, on the lamps'
own switch (`lotPools`, `lotPoolU`). The pools overlap into one lit field around the arena, the Linc
and the ballpark. Verified by capture at 9:30 pm and 2 pm. 181 tests.

## Round 130 — sidewalks that stop at the kerb, zebras for crossings (Sep 22)

Mike, with a screenshot of Head House Square: "Sidewalks/crosswalks overlapping look pretty bad. Can we
clean that up somehow?"

Four things overlapped in the core's street pass, all at once at Head House:

- **Generated sidewalks crossed the cross street.** Each street's two 3 m sidewalks ran on to the node in
  the middle of every junction, straight over the other street's carriageway. They now wait until every
  carriageway is known and stop at the kerb of any street they would cross (`walkJobs`, a local
  carriageway grid `carSegs`/`carHit`, 1.5 m samples).
- **Mapped footways doubled them.** OSM's separately mapped sidewalks lay beside the generated ones as a
  second, misaligned band. A footway stretch running alongside a street that has generated sidewalks
  (parallel within 0.85, inside the sidewalk band) is dropped; a mapped cycle lane along a carriageway
  is dropped rather than bricked over the road.
- **Crossings were brick bands over the asphalt.** Where a footway crosses a carriageway (square to it
  within 0.6) it is painted as a zebra: bars 3.2 m along the traffic every 1.1 m across the walk.
- **2nd Street's setts ran through Pine's junction** as a grey band, and Pine's own extract stopped 12 m
  short on each side: setts now sit just under any asphalt, and a same-named street whose two pieces stop
  within 32 m, in line and with no footprint between, is joined (Pine at 2nd, South 2nd across Pine).

`PERF.walks` counts it: 385 of 418 sidewalk lines cut at a kerb, 323 of 674 footways partly dropped as
duplicates, 227 zebras; `PERF.roadJoins` 2. Verified by capture at Pine and at Lombard. 181 tests.

## Round 131 — weather alerts, and cooling and warming centers (Sep 22)

The first of the six features Mike picked from the list of things Philadelphians would use (the plan:
alerts, tap a building, transit stops with arrivals and departure boards, near me, libraries and rec
centers).

`fetchNws` already asked the Weather Service for the model point's active alerts every five minutes, and
read only the storm events out of them. `alertsSet` now keeps every active alert (tests and cancels
dropped, expired ones dropped): a new one shows once in the Round 125 notice line for 12 s (held until the
loading veil is gone, so an alert that lands during the build is not lost), and the time panel lists them
("Weather alert: Heat Advisory until 10 PM") while they stand. Philadelphia publishes no machine-readable
Code Red or Code Blue, so a heat product (Heat Advisory, Excessive or Extreme Heat) or a cold one (Cold
Weather Advisory, Extreme Cold, Wind Chill, Freeze) stands in: it brings in the city's operating sites from
OEM's `Warming_Cooling_Sites_PUBLICVIEW` layer (`site_status` open, a site marked no for the kind left
out: 57 today, mostly libraries and rec centers), counted on the panel and named in the notice. Times are
real Philadelphia time (`alertClock`), never the pinned model clock. `__dbg.alertTest(event)`,
`__dbg.alerts()`; `tests/test_alerts.py` (the heat and cold lists, the clock's zone, one alerts poll).
Verified in the pane with a Heat Advisory and a Wind Chill Advisory fixture.

## Round 132 — tap a building for its property card (Sep 22)

The second of Mike's six. A tap that finds no pin, vehicle, dock or tree now asks what solid stands under
it: `bldgPointAt` renders the city's view distance through that one pixel (the camera's view offset, the
pin occlusion's override material through the shared `occRender`, every instanced mesh hidden), so the
outer chunks `freeOnUpload` leaves un-raycastable answer as exactly as the core. A hit 2 m or more over
the drawn ground is a building; the card anchors there (`updateBldgPick`) and reads "Looking up this
building" while the city's database answers (phl.carto.com, open to the browser): the PWD parcel under a
point 1.5 m in from the wall joined to its OPA record (address, the year the city records, stories, use;
a condominium gives its building and floor area instead of one unit), then the Philadelphia Register and
the local historic district, and L&I permits issued within a year nearby. No owner names, no values;
`bldgSql` only ever writes two fixed-point numbers into a query, and a newer tap cancels an older
lookup. The link opens the property on property.phila.gov.

Verified in the pane: the tavern gives "127-29 Spruce St, Built 1895, as the city records it, Colleges &
University, Philadelphia Register of Historic Places, Society Hill Historic District" (the city's year for
a 1759 house, which is why the card says whose year it is); a freed far-district rowhouse gives "2601
Tulip St, Built 1875, 3 stories, Row Typical"; the middle of Washington Square opens nothing.
`tests/test_building_card.py`. `__dbg.bldgTap(x, y)`.

## Round 133 — bus stops with the buses on their way, Regional Rail departure boards (Sep 22)

The third of Mike's six ("bus stop arrivals", "Regional Rail departure boards"; stations on by default,
bus stops behind their toggle).

**Data.** `fetch_septa_stops.py` caches SEPTA's GTFS release and the Arrivals API's station list;
`bake_septa_stops.py` writes `septa_stops.json` (432 KB, inlined as `SEPTA_STOPS`): 8,469 bus and trolley
stops inside the flight limit (route types 3 and 0; the subway stays out as Mike decided in Round 20) with
their GTFS ids, cleaned names and routes, and 64 Regional Rail stations under the name the departure board
takes plus the name a rider knows (the API still calls Jefferson Station "Market East").

**Layers.** Bus Stops (C, bit 16384, off) and Rail Stations (Y, bit 32768, on); bit 65536 is reserved for
Round 135's libraries and rec centers so one new marker covers all three: `LAYER_MASK_V5` 131072, read
first, `parseHash` keeps 262143, and a fourteen-bit link (whose 16384 is its marker, not the stops) still
decodes. Pins within the half mile, a bus on SEPTA blue, a rail car on slate, `pinRise`, the Round 127
occlusion; stations are in the search index and arrive with their board.

**The cards.** The plan meant a stop's card to read scheduled times from SEPTA's BusSchedules endpoint;
since this afternoon it answers every query, with or without a callback, with "An invalid parameter was
used", including the one the morning's probe confirmed. So the card promises no minutes: from the live v2
feeds (open to the browser) it lists the buses on their way, by route and headsign, how many stops away
(v2/stops gives each route's stop order by direction, v2/trips each bus's next stop) and how late each is
running, "arriving" inside 180 m. A station's card is its departure board from the Arrivals API (JSONP):
time, line, destination, lateness, track, a track change flagged, and any elevator the v2 feed reports out.
Both refresh every 30 s while open.

Verified in the pane with live data at 5:15 pm: Suburban Station listed six departures ("5:19 PM,
Lansdale/Doylestown to Doylestown, 2 min late, track 1"); Market St & 15th St listed "Route 33 to
5th-Market: 1 stop away, 4 min late" and four more; 134 stop pins within the half mile at City Hall.
`tests/test_septa_stops.py` (the file's shape and bounds, the board names, the link across V3, V4, V5).

## Round 134 — libraries and rec centers (Sep 22)

Taken before "near me" so that card can name the nearest branch from its first version. Mike chose pins
without hours: the Free Library publishes no hours as data (its site answers scripts with a bot check) and
Parks and Recreation's layers carry none, so nothing on a card can be wrong. `fetch_civic.py` /
`bake_civic.py` → `civic.json` (16 KB, `CIVIC_DATA`): the 54 branches (name, address, zip, phone, branch
page) and 163 centers (157 recreation, 6 older adult; the pools left out as Mike declined them in
September; the gym flag kept), 53 library points and 8 center points stepped out of their own footprints
with `bake_markers.py`'s `FootGrid` so their pins stand in the open under Round 127's occlusion. The layer
is the reserved bit 65536 on Z, off by default; a book on Free Library red, a ball on Parks green; the
cards give the address and phone and link the branch's page or the Parks & Rec Finder for hours; both are
in the search index and arrive with their card. Verified in the pane (Parkway Central's card, a playground's,
the search hit, the link's bit). `tests/test_civic.py`, the layer test's Z row.

## Round 135 — near me (Sep 22)

The last of the six. When the Round 125 location lands inside the city, `nearMeOpen` puts a card on the
"You are here" mark listing what is around, each row a place to glide to that opens its own card: the two
nearest bus stops within 400 m with the buses on their way (Round 133's `busComing`), the nearest Regional
Rail station within 1.5 km with its next two departures, the two nearest Indego docks with bikes within
800 m, closures within 250 m, markets open now on the model clock within 1.5 km, the nearest library within
2.5 km, and an active weather alert with the nearest open cooling or warming center (Round 131). Empty
sections are left out; distances are straight-line, feet under a tenth of a mile, miles above. The data
is read whether or not its layer is on, and the position is still kept nowhere.

Verified in the pane with a fix at Rittenhouse Square and live data: W Rittenhouse Square & Locust St
(350 ft, "Route 17 to 20th-Johnston: next stop"), Walnut St & 19th St (Routes 21 and 12), Suburban Station
(0.4 mi, the 5:30 and 5:32 departures), the Philadelphia City Institute library (450 ft); the first row
opened the stop's own card. The hidden pane never polls Indego or the closures (the `document.hidden`
gotcha), so their rows were checked in the code (the docks' records carry the `x`/`z` the card reads),
not live. `tests/test_near_me.py`.

The plan's six are done: Rounds 131 (alerts), 132 (tap a building), 133 (stops and departure boards),
134 (libraries and rec centers), 135 (near me), after Rounds 127 to 130 took Mike's messages that came in
while they were being built.


## Round 136 — the review's fixes (Sep 22)

An adversarial review of Rounds 127 to 135 (a workflow of finders by dimension, each finding put to
skeptics told to refute it) confirmed 44 findings, several of them the same defect found from two sides.
All of them are fixed here.

**Pins.** A pin carrying `aPinVis` is drawn whole over any nearer building (Round 127), so the pick now
asks that same per-instance visibility and nothing else: the old ray to the hit point refused the part of
a drawn pin that overlapped a nearer facade, and the tap fell through to the building's property card.
Pins without the attribute keep the ray test. `PIN_OCC.far` is 30 km, not 4: past 4 km every flight and
ship pin read as visible, so they drew through the skyline and the hills. The capture hides the sky dome,
the cloud deck and anything that does not write depth (the dome at 5,200 m was hiding distant pins at the
screen's sides), and it runs only when the eye has moved 0.3 m or turned, or two seconds have passed:
the city it records does not change on its own, and every fifth frame was a full opaque re-render and a
`readPixels` stall while the camera sat still. `bake_septa_stops.py` steps a stop or station point that
falls inside one of the page's footprints 2.5 m out past the wall with `bake_markers.py`'s `FootGrid`
(232 of them), so a pin no longer hides behind its own building.

**Building taps.** The click that takes pointer lock on desktop (fly or walk) no longer opens a card
(`vpLockReq`). The one-pixel depth render keeps to 3 km. A river's sheet, the two bridges' corridors
(`bfbNear`, `wwbNear`) and any mapped deck within 4 m of the hit (`ovpDeckY`) are not buildings. A failed
lookup reads "The city's property records did not answer", not "No property record here". The permits
are this property's, by its nine-digit OPA account (only digits ever reach the query), not anything within
25 m. A condominium no longer shows PWD's `gross_area`, which is the lot's. Every lookup obeys
`septaCanFetch` like the other feeds.

**Cards.** `oldPick()` names the pre-Round-132 cards, and an async result for a building, stop or near me
card checks it, so a lookup that lands after another card opened no longer overwrites it. `.wide` has one
owner (`updateMarkerPick`: a marker or the near me card). The near card rerenders its rows from a `dirty`
flag that waits out `cardHold` and a hover (the Round 63 lost click). Its cooling or warming row opens a
real card (`kind: 'site'`), every row labels its search mark, a sidewalk-only closure says so, the Indego
and closure rows appear only while those layers are on and polled, and a SEPTA call that did not answer
reads "SEPTA did not answer" rather than "no bus". `routeStops` drops a failed route from its cache, and
`busComing` returns null when no route answered.

**Keys.** C is descend again, as it always was. Bus Stops is Y, Rail Stations is Z, and the libraries
and rec centers have no letter (the layers panel turns them on). A held key toggles a layer once.

**Streets.** Round 130's road-join pass is gone: its two joins paved across Bainbridge Green and through
Lawrence Court's turning circle, and Pine at 2nd was never split. The core's I-95 lanes no longer register
as streets a footway crosses, so the Foglietta and Vietnam memorial deck paths and the Spruce, Dock and
Market sidewalks over the highway stay paths instead of zebras or cuts (`PERF.walks` zebras 194, cut 375).
The setts sit at road minus 1.5 cm with a 1 cm jitter, between the sidewalks and the asphalt, so the
cross streets' sidewalk ends no longer draw over the cobbles at Head House.

**Lights and alerts.** The same-day snap waits for a date change's ease to settle. An alert is a hazard
keyed by its event and onset to the minute, so the NWS's routine updates are not announced again; every
new hazard is announced (up to three on one line); the veil hold re-reads the list when it ends; the span
is the hazard's onset and ends ("from" when it is still ahead, no "until" when it is open-ended), not the
message's expiry; and the time panel and near me read only what is still in effect, the centers only
while a heat or cold alert is.

**Credits and pipeline.** The About panel and `DATA-LICENSE.md` credit SEPTA's GTFS, v2 and Arrivals
feeds, the Weather Service, OEM's sites, the Free Library, PPR and the city's property records, and say
the location is kept nowhere. `pipeline.py`'s build step needs the stops and civic bakes, and the stops
bake needs the footprints it now reads.

Verified in the pane (building taps on the sky, the Delaware, the bridge deck, the tavern and a far-ring
row; combined and "from ... until" alerts; the near card wide with the site card) and in captures of the
Foglietta deck, Bainbridge Green and Head House. 199 tests pass.

## Round 137 — the South Tower's five windows in the skyline's colours (Sep 22)

Mike, pointing back at the five windows he boxed in red on the South Tower's south face before Round 131
(the question then went unanswered because nothing about those panes differed from their neighbours):
"light up those specific windows with the same colors the skyline had every night". They are the 14th row
of glass down from the parapet, floor index 16 of 30, and bays 5 to 9 counted from the west; the variation
panes in that row (curtains at bays 3, 4 and 10) sit just outside them, exactly as in his screenshot.

The tower glass already lights each room from its own coordinates (`towerRoomCoordinates`: the bay and
floor in `aInterior.xy`, the face's seed in `.z`), so no geometry was added. `towerGlassMat` compiles
`apartmentWindowHook` with a `THEMED_ROOMS` define and the `shtWinU` uniforms: `uLitWin` holds the face's
seed, the floor and the bay range, and a room that matches all three emits the night's colour after dark
in place of a lamp, by the crowns' own formula (`uNight` 2.4 times the colour, a saturated hue at 0.42 of a
white's gain), a touch darker toward the frame so it still reads as a room. With the post pipeline it
blooms like the crowns (`THEMED_BLOOM`, the target's alpha, only for those rooms). The face is found by
its outward normal (`shtSouthSide`), the tower by name (`SHT_THEMED`), and the variation loop leaves the
five bare. By day the glass is untouched.

The colours ride the theme: `lightsRetarget` deals the night's colours across the five in order
(`shtWinDeal`: one colour fills all five, green, white and red read green, white, red, green, white),
`THEME.wtgt`/`wcur` ease them with the crowns over 20 s and land them on the first evaluation, and a
plain night is the white the skyline's white nights are (`themeLift`, the same lift the crowns take).
`__dbg.lightsState().windows` reports the face, the colours and the uniforms.

Verified in the pane at 9:30 pm: the five uniforms equal the crowns' (`cb0205` on a Phillies pin, the
Ben Franklin Bridge the same red behind them), green, white, red, green, white on a three-colour pin, the
white on a plain night, all green on an Eagles pin, and the same row by day at Mike's framing with plain
glass in it; compiled and lit with `?bloom=0`, the phones' path. `tests/test_sht_windows.py`.

An adversarial review of the round (three lenses, the shader, the theme's timing, the selection, each
finding put to a skeptic) found one real defect, and it was Round 136's, not this round's: the same-day
landing (Round 127) never fired. Round 136 made it `if (sameDay && THEME.settled)`, but `lightsRetarget`
ends by clearing `THEME.settled`, so the test read a flag just cleared and was always false; on an
unpinned game day the scoreboard answers after the first evaluation, and the skyline (and now the five
windows) eased from white to the team colour for about a minute, Mike's Round 127 complaint back. The
flag is now read before the retarget (`wasSettled`). Measured in the pane with a served calendar landing
after the page had settled on a plain night: the old build's theme weight was 0.002 one frame later and
0.005 the next (still white, easing); this build's is 1 on the first frame, the crowns and the windows
purple at once. The pane checks before it all used pins, which set `seeded` themselves, which is why they
missed it. `tests/test_sht_windows.py` holds the order.

## Round 138 — pins that ease instead of flashing (Sep 23)

Mike: "I am now seeing a problem with the pins flashing and disappearing while I move around. Is there a
smoother way we can handle this?" Round 127's pins are shown or hidden whole from a 256-pixel depth image of
the city, recaptured every fifth frame while the eye moves; each capture decided every pin's `aPinVis` as 0
or 1 and the pin snapped to a point or back. A tip beside a building's edge lands on either side of it from
one capture to the next, so it blinked. Round 136 made it more common: it stepped 232 stop and station points
out of their footprints to 2.5 m from the wall, which is exactly that edge.

`pinOccUpdate` now keeps a state per pin slot (`pinOccState`): a pin changes its mind only when two captures
agree, or when the answer has held `PIN_HOLD` 0.45 s (a moving pin while the eye is still, when no capture
comes); a new state is kept at least `PIN_DWELL` 0.3 s (passing a narrow gap does not blink it); and
`aPinVis` eases over `PIN_FADE` 0.2 s on a smoothstep, so the pin sinks into its tip and rises out of it. A
pin new to its slot (a larger count, or a slot handed to a pin more than 30 m away when the set reshuffles)
takes its answer at once, since `pinRise` brings it in. The pick still refuses a pin under half size.

Measured in the pane with the same layer mask (every fixed-pin layer on, every moving one off) over three
scripted flights (Old City at 28 and 22 m, Market Street at 45 m, 150 frames each), counting a blink as a
pin that hides and returns within 12 frames without moving: the old build 31 blinks and 364 hard flips,
two agreeing captures alone 8 and 183, with the dwell 0 blinks and 135 changes, every one eased. About
22 ms a frame in the pane either way. `tests/test_pin_fade.py` runs the block under Node against scripted
captures (a one-capture blip ignored, two captures hide it on a monotone ease, the dwell, the still-eye
timeout, a new pin in a slot).

## Round 139 — 207 E Wildey St, demolished and dug out (Sep 23)

Mike, with a camera link and two photos of the lot: "can we remove the home at 207 E Wildey St? It is the one
with the crosshair dot on the roof. That should be replaced with a hole in the ground, a la the attached
photos". The city's records agree: a full demolition permit in February, the vacant two-storey frame house
hand-demolished and the permit closed May 11, 2026, new construction permitted Sep 1 (three storeys, with
sheeting, shoring and underpinning) and an excavation permit Sep 15.

The house was wide.b64 record 74399 (6.2 by 9.7 m, 7 m), the one record under the link's centre ray. It is
skipped at run time, not repacked: `pack_wide.py` reproduces its blobs byte for byte, so a repack would be
safe for the data, but removing a record renumbers the 38,352 after it, and the runtime seeds each wide
building's palette, facade, pitched-roof lottery, clutter and the far ring's colour reservoir by the record
number, so a third of the tier would have changed its look. `DEMOLISHED` holds scene points; the loop skips
the footprint holding one before any consumer sees it and still counts it in `wideColK`, so the reservoir
deals exactly as before.

`GROUND_PITS` rings are cut out of the drawn ground by `elPortalClipGround`, the exact convex cut the El
portal already uses (the lot sits inside one 25 m cell, so dropping cells or lowering nodes was out). The ring
runs the house's party-wall lines out to the parcel's front and rear lines (PWD's parcel, 6.3 by 18.3 m). The
new step 'Digging on East Wildey Street' builds a closed pit under it on a bilinear grid of the lot: a hand of
churned mud with tyre ruts at the front, a ramp to about 1.45 m, a deeper underpinning trench along the left
foundation, a spoil mound, a lip at the rear, soil walls from the drawn grade (`groundMeshY`, the uncut plane,
so the rim meets the cut) down to the floor's own edge. The neighbours' foundations are bare where their walls
stand on the lot line (205's concrete block with the surveyor's orange marks, a canvas texture; 209's poured
concrete), 4 cm proud of the line, because the wide tier's walls run a metre under grade and would fight them.
Above grade the facade shader paints windows on every wall, and these party walls had been hidden behind the
house, so each takes a blank skin up to its own eave (`PIT_NEIGH`, noted in the wide loop with the roof plan's
rise): 205's grey stucco and the new 209's siding. In it, from the photos: the wooden trench box at the rear,
boards leaning on the block and two on the floor, the blue drum by the right foundation, the black basin on
the front apron, a rubble pile at the front left, and black mesh fencing with an orange band down the right
side of the front. The grass is kept off the lot (`noSow`): its tufts sit at the uncut grade and would float.

Checked in the pane: from Mike's link the lot is a dug gap in the row; from the sidewalk and from the photo's
front right corner the block, marks, boards, box, drum, basin, rubble and fence read as in his photos, with no
seam at the rim. `tests/test_ground_pits.py` walks the packed tier: the point names exactly one house (74399),
the ring is convex and holds only that house, clears the drawn street, and its party-wall spans end on the
neighbours' corners; plus the wiring. The El tracks' Node harness gains a `GROUND_PITS` stub.

An adversarial review (two lenses, a skeptic per finding) confirmed one defect, found from both sides: the pit
floor copied the ground builders' index order, but its axes (along the front, then toward the rear) are mirrored
against x and z, so every floor normal pointed down. DoubleSide hid it in the lit colour; the weather wrap and the
shadow bias read the raw normal, so snow and rain would have skipped the floor and its shadow lookups sat 1.4 m
under it; the front and right wall strips faced outward too. The floor now picks its winding from the ring's
handedness, and each strip flips itself to face its `inward` vector.

Noted for Mike, not done: the model's right neighbour (74404) is the old house on 209, demolished in April
2025; the two new attached houses on 209 and 211 (finished this year) are not in the source data.

## Round 140 — the lamps light the city (Sep 23)

Three messages from Mike in a row, one cause. "https://philly3d.com/#p=239.4,463.7,6151.6,... There is a lot of
flickering going on in this view"; over the stadium lots, "can we have those larger light circles be more
diffused?"; and "The lamp posts are not putting out enough light at night. it is much too dark throughout the
city", with a South Philly street at 32 m as the example. The flicker at 464 m over the Navy Yard was Round 130's
pool discs on the stadium lots: laid a few centimetres over the asphalt, they lost the depth test wherever a lot
rose above them, black specks that crawled as the eye moved (the log depth buffer writes the fragment depth, so
a polygon offset does nothing). They were hard-edged too. And the other 200,000 lamps lit nothing: a point of
light each, the streets under them black.

Now the lamps light the surfaces themselves. Every pole and lot mast is splatted as a soft pool (a broad
Gaussian cut at its radius, 2.4 times the mounting height between 10 and 30 m, 40 m for a mast at a quarter of a
pole's weight so the overlapping lots do not wash white) into a light map: a render target `LAMPMAP.span` square
(12 km at 2048 px on a desktop, 8 km at 1024 on a phone) drawn by an orthographic camera looking down, re-centred
ahead of the eye in steps of a sixteenth of its span (further ahead the higher it flies), and drawn only while the
lamps are on. `lampLightPatch` puts it in `surfTexPatch`, so the ground, the roads, the lots, the parks and the
plazas add their own colour times the light (`LAMP_GAIN` 4, calibrated on Mike's street at 9:30 pm), and in the
facade shader, where it washes vertical faces only and fades out between 2.5 and 11 m over the building's base,
so the lower storeys glow and the roofs stay dark. Nothing lies over a surface any more, so nothing can fight it,
and the pools are as soft as the splat. The map fades out over the last 6 % of its edge; past it the city is the
carpet of lamp points it was.

Checked in the pane at 9:30 pm at all four of Mike's views: the South Philly street lit, with its verges and the
first storeys of the rowhouses; the stadium lots in soft overlapping pools with no specks; the Navy Yard's roads
carrying their pools; Center City's streets glowing between the towers. `__dbg.lampMap()` and `__dbg.lampGain(k)`.
`tests/test_lamp_light.py` proves the map's texel for a world point is the one the shaders read (the page's own
camera setup under Node) and holds the wiring.

The round's adversarial review (three lenses, a skeptic per finding) confirmed six findings, all fixed the same
day. (1) The lit ground's far edge jumped: the map's edge fade (6 % of its span, 720 m) was narrower than its
750 m re-centre step, so from altitude a band of the city switched lit or dark in one frame. The light now ends on
a circle round the unsnapped look-ahead point (`uLampFade`, radius span/2 less a step, fading over 15 % of the
span), set every frame and always inside the snapped map; measured across a forced re-centre at 1,400 m, the lamp
light per screen row changed by at most 0.8 of a grey level. (2) Unbounded on bright surfaces: on snow the pools
came out three to six times brighter than the same snow at noon and bloomed. The term now takes the albedo at most
at 0.35 and rolls off anything over 0.5 toward 1.0, under the night bloom threshold; the dark asphalt it was set on
is untouched. (3) Every surfMat face took full light whatever its orientation: piers, the I-95 cap's soffit and the
Wildey Street skins glowed. The ground path now lights only faces turned up. (4) The grass tufts were unlit dark
specks on lit ground: they take the patch in a 'blade' mode. (5, 6) Six GPU harnesses (buildings, City Hall,
glass optics, window interiors, facade roofline, environment) cut the facade hook or surfTexPatch out of app.js
and threw on the new call; each now cuts `lampLightPatch` and stubs `lampMapU`, and all six pass in the pane.

## Round 141 — scheduled PATCO trains over the Ben Franklin Bridge (Sep 23)

Mike asked whether the PATCO trains over the bridge could be tracked. A research workflow (official feeds, third
parties, direct probes, a skeptic) found no live source at all: no GTFS-realtime, no JSON behind PATCO's site or
app, nothing on the registries, the "live" third-party trackers schedule-based or rider-sourced; PATCO's own advisory
committee minutes say the train data stays on a closed signal network, with real-time "still being explored" into
2026. Mike: "yes, add the scheduled PATCO trains on the bridge".

Data. `fetch_patco.py` takes PATCO's public GTFS (the permalink its developer page links, feed 19, valid Sep 21 to
Dec 31 2026) and the OSM ways PATCO operates between 8th and Market and Broadway (Overpass, `out geom`, a generic
User-Agent). `bake_patco.py` stitches the two main tracks by shared end nodes (the crossovers, spurs and yard ways
dropped; right-hand running confirmed by `railway:preferred_direction`), keeps each from 150 m past 8th and Market to
150 m past Broadway with tunnel, bridge and covered flags, projects the four stops on, reduces every bridge-crossing
trip to its two bracketing minutes (Franklin Square or 8th and Market, City Hall or Broadway) and resolves the
calendar to a service mask a day with a swap-day repair: feed 19's Sep 26 adds the Bike MS timetable and removes
194 Sunday, which does not run that Saturday, so a literal reading ran both (114 duplicate trips); a service added on
a date that shares over a quarter of its trips with a base service running that date now replaces it. 9.5 KB.

Track. OSM seats the tracks 11.9 m north and 15.3 m south of the model's bridge axis, which is the roadway and the
truss line, so `patcoTracks()` re-seats them at 17.75 m either side on the span and through the anchorages (the floor
outboard of the trusses, under the walkway, as on the real bridge) and eases back to OSM over the approaches. The bed
follows the deck's floor on the span (`bfbDeckY`, now the bridge block's own profile too) and a profile on the
approaches: out of the 5th Street mouth at 6.2 %, level over I-95 and its ramps, down to the anchorage; on the Camden
side down to the portals. 'Laying the PATCO tracks' lays ballast, rails, a third rail and 6,363 ties over 4.6 km,
a viaduct with 72 piers (none on a street) where the bed stands over 2.2 m, a retained fill under that, and a walled
cut with a lintelled, dark mouth at 5th Street (18 cut quads out of the drawn ground through `elPortalClipGround`);
Camden's ground and roads leave no room for a true below-grade mouth, so the tracks run into covered portal boxes.

The bridge had to make room: a car is about 3.8 m tall and the walkway was 3.1 m over the floor, so the walkways,
their rails and lamps rise 1.5 m (0.2 m over a car's roof); the lower tower legs split so the track and walkway pass
under the upper legs; the first tower strut ends inside the cable planes; each anchorage portal pier became an outer
pier, a lintel over the track and a floor block in the landward half; the floor runs full width through the
anchorages.

Trains. A trip crossing the bridge runs between its two scheduled minutes on a trapezoid (accelerating over the first
15 %, braking over the last) along its track, drawn only between the mouths and PATCO_COVER 25 m into the Philadelphia
tunnel (the ground hides that part, so a train slides in) and hidden once its tail is inside a Camden box. Consists
are not in the timetable, so a stated rule sets them: six cars into the city in the morning peak and out of it in the
evening peak, four through the day, two at night and on owl runs. The clock is the model's: live, a train is where
the timetable puts it now; on a pinned clock it runs on from the pinned minute. The cars (stainless, the blue and
PATCO-red belts, a window band that glows after dark) ride the trains layer (K) with Amtrak's, keep the half-mile
rule, carry a red pin with a car's face, and open a card: "Westbound to Philadelphia", "Scheduled, Shown With 6
Cars", "Next Stop: Franklin Square, 8:01 AM", "Timetable Position, Not Live", a PATCO Schedules link. Outside the feed's
dates the weekly pattern stands in and the card says Typical Timetable. The layer row is now "Trains", its count
Amtrak's tracked trains plus PATCO's running ones. A pre-existing bug fixed on the way: five pick branches (closures,
markers and art, the screen-space closure and marker fallbacks, the trees) left `pickedTrain` set, so with a train
card open, tapping one of those opened its card and the next frame put the train's back.

Verified in the pane at 8:00 am (a six-car westbound mid-span on the north track under the walkway, its pin over the
trusses, the card) and 9:30 pm (the window band lit), with captures of the Philadelphia viaduct, the cut and its
mouth, and both Camden portals; `__dbg.patcoCheck()`: the bed on the span exactly the floor's top, the walkway 0.205 m
over a car's roof. `tests/test_patco.py`.

The round's adversarial review (four lenses: the schedule, the geometry, the bridge, the integration; a skeptic per
finding, with node replays against the real patco.json and the packed roads) confirmed fourteen findings, all fixed
before shipping. The clock: on a pinned clock the drift grew without bound and the bridge emptied once it passed the
day's last run (and nothing looked at tomorrow's owls), a re-pinned minute took back the old drift, and the live
seconds, measured from a midnight the tz helper puts an hour off on the autumn change, went negative for that hour.
Now the live clock is the HUD's own minute plus the second within it, a pinned clock's trains run through its hour
and start again from its minute, and the recon also reads tomorrow's service. Camden: a 3.5 to 4 m gap between the
anchorage and the viaduct (a run following the anchorage now starts at its face); the north track ran along the edge
of the 16 m westbound road ribbon and its portal box stood on it (the north track is now eased 3 m north of OSM's
line and its mouth is at 1,620 m along, measured clear of every wide road and footprint); its rails stopped 4.7 m
short of the box; a westbound car showed 3 m of nose outside the box (the cars now test their own ends by arc length
from each face); and the approach smoothing read the tunnels' flat -35.9 m beds past the window and dove the north
box's roof (the tunnels now continue the grades, and the smoothing reads only the window). Elsewhere: the cut was
known only to the ground mesh, so tufts floated over it and a footway was drawn across it (the cut now keeps the
sow, the trees and the narrow ways off); piers stood inside 16 m carriageways and through the elevated I-95 decks
(a pier now clears a road centreline by 9.6 m and every deck's width); the cars rode 0.28 m over the rails at the
span's grade breaks (they now sit on their truck centres); the ties' instanced mesh was frustum-culled against the
origin and vanished from most views, and so were the El's since it was built; and a bus opened from search left a
train card's record set, so the train card took the slot back. Measured after: the walkway 0.205 m over a car's roof,
the bed on the span exactly the floor's top, 58 piers, 6,343 ties, 4.57 km of track.

## Round 142 — the new houses at 209 and 211 E Wildey St (Sep 23)

Mike: "add the new houses at 209 and 211 E Wildey". Round 139 had noted them: the model's right neighbour of the pit
(wide record 74404) was the old semi-detached house on 209, demolished in 2025 (ZP-2025-000103, DP-2025-000011); the lot
was split in two (ZP-2025-000106) and a mirrored pair of attached single-family houses built on it (RP-2025-003196 and
-003197, both completed), listed this year as 19 ft by 58 ft lots, three storeys over a finished basement, a Roman
brick facade with oversized loft windows, a roof deck. The listing's front photo (both houses, 207's lot bare beside
them) and its rear-patio photo are the model.

74404 joins `DEMOLISHED` (skipped at run time, counted in `wideColK`, as 207 was). The new step 'Raising 209 and 211
East Wildey Street' (`buildWildeyRow`) lays the pair in the row's own frame, on the pit's right line and along its front
line (`WILDEY_ROW`: 5.79 m each, 12.5 m deep, coping at 11.2 m, roof at 10.45 m), carried out by one right-handed basis:
per house a front wall cut round two openings (the recessed two-storey window bay, 0.30 m deep, and the recessed ground
floor, 0.35 m) with their backs and reveals, the canvas facade drawn in facade metres (pale grey Roman brick in 5.2 cm
courses, two black loft windows of four sashes each, stone sills, the string-course groove, the black party-line
reveal, the door on the outer side, the shopfront over a black base, globe sconces), mirrored for 211; a black steel
canopy; grey siding on the exposed side walls (209's faces the pit, 211's the parking beside it); white board-and-batten
at the back with a glazed ground floor and two windows a floor; a membrane roof with a porcelain paver deck behind a
rail at 3.2 m, a charcoal pilothouse with a glass door and a condenser at the back; a paver patio in a cedar fence.
After dark an emissive map scaled by the night uniform lights some rooms and not others, the shopfronts and the sconces.
The pit's right foundation now runs the new house's whole depth from the street line (`right: [0, 0.685]`), and an
empty strip run is skipped rather than built degenerate.

Checked in the pane from the street by day and at 9:30 pm, from over the pit and from behind; `tests/test_ground_pits.py`
covers both demolished records, the right span against `WILDEY_ROW.depth`, and the step's order before the sow.

## Round 143 — pins that showed at the screen's edges and vanished when faced (Sep 23)

Mike: "I can see them on either side of my screen, but then I turn in their direction and they disappear". Two causes,
both measured in the pane by sweeping the heading 0.02 rad a frame at 60 Hz from four fixed eyes and counting pins that
showed on screen and then vanished while still on screen (from a fixed eye nothing can change what hides a pin, so
every such vanishing is wrong). The deployed build: 135 of 189 on-screen showings ended that way.

1. The depth image covered exactly the screen, and a tip outside it read as visible. While the eye turns the image is
   up to five frames old, so a pin swinging in from a side behind a building was tested against an image it was not in,
   shown, and hidden once a capture caught up. The image now covers 1.5 times the screen each way at the same pixel
   density (384 px wide on a desktop, 240 on a phone), through its own camera carrying the real near and far (the log
   depth buffer reads far; a fresh camera's 2,000 m broke it); `occRender` takes the camera, and the building tap
   still uses the screen's.
2. A tip on a building's edge fell on either side of it as the image's pixels shifted with the heading, and two
   captures could agree either way, so it flipped. Now a shown pin keeps showing while anything in a 5 by 5
   neighbourhood lies behind its tip, and a hidden one returns on the 3 by 3 test (`pinOccVisible`'s `rad`).

After: 5 of 47. The showings fell because the occluded pins no longer flash in at the edges. `__dbg.pinOcc(true)` now
lists each pin's raw verdict, state and pending count, and `__dbg.pinOccAt(x, y, z)` its view depth against the image;
`tests/test_pin_fade.py` gains the edge case and the wide image's wiring.

## Round 144 — the rail yard's flicker, softer and wider lamps, lit elevated highways (Sep 23)

Three messages from Mike. (1) "https://philly3d.com/#p=169.2,286.7,5947.6,-0.497,-0.336 I am still seeing lots of
flickering at this view on the concrete": the concrete is the Packer Avenue rail yard (paved.b64 kind 3) with
ordinary yards (kind 2) inside it, and the yards, rail yards and aprons all sat at 0.04 m. pack_paved.py unions each
kind, but the kinds overlap one another: yards under aprons over 389,000 m2 and under rail yards over 154,000 m2 (rail
yards and aprons never; lots over all of them already at 0.055). Coplanar, they fought in dark patches that moved with
the eye. The yards now sit at 0.025, so every overlapping pair keeps at least the 1.5 cm a lot keeps over a yard;
three frames 0.5 m apart from Mike's link show no patches.

(2) "Can we diffuse all of the lamposts more and have that light stretch a bit further?": each splat into the light
map is 1.4 times wider (a pole's radius 3.4 times its mounting height between 14 and 42 m, a lot mast 56 m) with a
flatter Gaussian (1.9 against 3.2) and a peak of 0.8, so the light spreads over the sidewalks instead of pooling under
the head. Compared at 9:30 pm over Spruce Street and a South Philly grid against the deployed build.

(3) "lamp posts should not clip through elevated highways. The highways also need lamp posts where they are elevated
so they look lit up like in real life", with a link over the Vine Street Expressway at 5th Street: a line of heads ran
down the deck's middle (the poles of the street beneath standing through it), and their pools lit the deck's top in
bands from below, the light map being flat. A packed pole within a deck's half width and 2 m, the deck more than a
metre over the pole's ground, is no longer raised (1,401 of them). Every elevated stretch of every deck (more than
4.5 m over the drawn ground) now carries a 12 m LED standard at the deck edge every 42 m, staggered, both sides on a
deck 22 m wide or more, its arm turned in over the lanes (`poleInv.ROT`), 2,476 in all; they ride the poles'
arrays, so they draw as poles near the eye, glow as points and splat pools into the light map, which lights the deck
through the road material. The Ben Franklin and the Walt Whitman keep their own lamps. `__dbg.PERF.lampsDeck`.

## Round 145 — the Custom House's three zones, and Boathouse Row's bay doors in their own colour (Sep 23)

Mike, with two night photos: "The customs house on 2nd st needs to be lit up at night. They recently added new
colored lights that have 3 lighting zones for different colors". One photo shows the whole building washed warm white
with a lit ring at the lantern's head; the other, the lower block and the tower in gold and the setback's pavilions in
blue. The Custom House model (Restoring the landmarks) now records its footprint and frame (`CUSTOM_HOUSE_AT`), and
the skyline lights give it three uplight washes on three consecutive theme slots: the lower block (its footprint grown
0.6 m, from the ground to 40 m), the setback's square stage (40 to 49 m) and the tower (the two octagonal drums and
the lantern, 49 to 81.5 m, 8-sided sheets proud of each), plus a ring of light at the lantern's head on the tower's
slot. A two-colour night deals them gold, blue, gold, as in the second photo; a plain night washes all three in their
own white, as in the first. Checked with `__dbg.lights('gold,blue')` and on a plain night at 9:30 pm.

Then: "Can we also add another color lights to the bay doors on the boathouse row homes?" The bulbs round each boat
bay's arch were on the house's outline slot. They now go with a new `bays` list on the slot after the outline's,
with a soft glow on the doors inside each arch (the door boards moved 3 cm out in front of it). A themed night lights
the bays in the next colour (blue outlines with gold bays, then the reverse, down the row); a plain night keeps the
white outlines with amber bays. `tests/test_landmark_lighting.py` counts every clubhouse's bay lights and checks the
slots and the Custom House's zones.

## Round 146 — the lamps light the trees, the upper storeys and a little of the roofs (Sep 23)

Mike, with a night screenshot over a South Philly street: "At night, the trees do not reflect the light from the lamps
and appear black", then "the tops of the buildings need to be lit up a bit. Can we have the street lights diffuse
upwards more to light up more than just the bottom of buildings?" Round 140's light map reached the ground, the roads,
the lower storeys and the grass tufts, but not the crowns or the trunks, and a wall's wash was gone by 11 m.

The crowns (`canMat`) and trunks now call `lampLightPatch` in a new `crown` mode, a flat gate of 0.12 on every face:
at 0.8 and then 0.35 they came out lime green, daylight at night, because a crown's albedo reaches the patch's 0.35 cap
and the result sits at its 0.5 roll-off either way. The wall gate fades over 3 to 22 m instead of 2.5 to 11 and never
below 0.3, and a roof (a face turned up or down) takes 0.3 of a wall's light where Round 140 gave it none. Compared at
9:30 pm over Spruce Street, a South Philly grid and a wide view south of Washington Avenue against the deployed build.

## Round 147 — the lamps a tad dimmer, and the wash fading out up the walls (Sep 23)

Mike, on Round 146: "Everything is a tad too bright now. We also dont need the upward diffusion on the large
buildings. It should diffuse out in a gradient at some point." `LAMP_GAIN` 4.0 to 3.2 (a fifth down, for the ground,
the roads, the trees and the walls alike), and the wall gate loses Round 146's 0.3 floor: the wash fades smoothly from
3 m to nothing at 16 m, so a tower's upper storeys are dark again and a rowhouse's front is lit to about its second
floor; a roof takes 0.3 of a wall's light at its own height, which a low roof catches and a tall one does not. Compared
against Round 146 at 9:30 pm over Spruce Street and south of Washington Avenue with the skyline behind.

## Round 148 — lamps along the piers and along I-95, in the city and past it (Sep 23)

Mike, with a night screenshot north along the Delaware: "All of the piers in the city should have lamp posts lining the
outside of them", then "can you light up 95 south even outside of the city?"

Piers: both builders now note their rings (`PIER_RINGS`: the core's `D.areas` piers at their deck height, the outer
tier's paved flats at the ground plus 1.2 m). The outer tier's kind 2 mixes piers with aprons and plazas, so the lamps
go only on an edge whose outside, 6 m out, is open water (the Delaware's outline or the Schuylkill's raster): a 7 m
lamp every 28 m, the rhythm carried round corners, 0.8 m in from the edge with its arm over the deck, none within 10 m
of a pole already there; 674 lamps. The splat loop had treated every lamp after the packed poles as a lot mast (a 56 m
pool at a quarter weight), the deck standards included, which is how Round 144 tuned them and so they stay; a pier
lamp now takes a 20 m pool at a fifth of a pole's weight, because a pale pier lined both sides washed white at 56 m and
still did at 24 m and half weight (checked with the gain at zero: it was the lamps).

I-95: the packed tiers carry no names, so `bake_i95.py` reads the far ring's raw dump (`osm_city_raw.json`) for the
motorway ways whose ref names I 95, stitches them by shared end nodes into chains in the direction of travel and
simplifies them to 2 m (`i95.json`: 182 ways, 4 chains, 59.5 km, from past the airport in Delaware County to Bucks
County, 7 KB, inlined as `I95_DATA`). The page stands a 12 m highway lamp every 50 m on each carriageway's outer
shoulder (the right of travel, 7.5 m off the centreline), the arm over the lanes, except where the road rides an
elevated deck (its standards light it), in the Vine Street cut, or within 10 m of a pole or a standard: 621 lamps.
`__dbg.PERF.lampsDeck` counts both. Checked at 9:30 pm south-west past the airport and over the South Philly piers.

## Round 149 — sharper on phones (Sep 23)

Mike: "The model is somewhat blurry/grainy on mobile. is there anything we can do about that?" A phone's screen is
about 3 device pixels to the point, and the page drew at most 1.25 (Round 74's cap, from 1.5) and dropped to 0.72 under
load, then the browser stretched the image: under half the screen's sharpness each way, and the fine noise textures
went grainy at the floor. Offered moderate (1.75 / 0.9), sharp (2.0 / 1.0) or leave it; Mike chose sharp. Touch now caps
at 2.0 and floors at 1.0, the 15-frame adaptive step unchanged (it still sheds resolution by a fifth when the median
frame runs over 22 ms). Checked in the pane's phone emulation at 740 by 360: a 2x drawing buffer of 1480 by 720. Not
checked on a real phone from here: an older phone will sit at the 1.0 floor and may run warmer; the numbers are
`DPR_CAP` and `DPR.min` if it needs pulling back.

## Round 150 — the roofs a little lit at night, and hardware on them (Sep 23)

Mike: "the tops of the buildings look too dark. Can we light them just a bit at night?", then "Can we also add air
conditioning and other hardware to roofs? They look too plain."

The glow: the lamps' wash stops at 16 m since Round 147, so the roofs had only the moon and the hemisphere. The facade
hook now adds `ROOF_NIGHT` (0.3) of a face's own colour after dark wherever the face turns up (smoothstep 0.35 to 0.75 on
the world normal, so the pitched slopes count), at any height: a city's sky glow, not a lamp. 0.12 read unchanged.

The hardware: the existing clutter was desktop only, gave a rowhouse at most a chimney on a third of them, and baked
into the chunks. `roofClutter` now notes every flat roof of the packed tiers before its touch return (`ROOF_KIT`: centre,
top, long axis, half sizes, seed; 185,552 roofs, 8 floats each), and 'Fitting out the rooftops' builds five instanced
meshes: a condenser with its fan grille, a commercial rooftop unit with two grilles and a hood, a hatch with its lid, a
vent stack with its cap, a dish on a mast turned south-south-west. Within 420 m of the eye (260 on a phone), nearest
160 m cell first and up to each mesh's cap, every roof's kit is laid from its seed, again when the eye has moved 30 m or
1.5 s have passed: a roof one house deep and longer than 14 m is a strip cut into 5.4 m houses, each with a condenser in
seven of ten, a hatch in about half, one or two vents and a dish in about a fifth; a single house takes one house's kit;
a bigger roof takes rooftop units by area on a jittered grid, hatches, vents and, under 900 m2, a few condensers. They
take the roofs' night glow too. Two misses on the way: `put` had no default scale, so four kinds drew as NaN and only the
dishes showed; and the colours had to be stored at about a fifth of their look (the legacy lift), as every flat is.
Pitched roofs take nothing (a gable carries no condenser in the model). `__dbg.roofKit()`, `tests/test_roof_kit.py`.

## Round 151 — the RiverLink ferry, on its timetable (Sep 23)

Mike, with RiverLink's departure table: "Can we add the riverlink ferry to camden? I assume there is no actual location
data for that, but maybe on a schedule?" Scheduled, never live, on the ships layer, one vessel (the Freedom) between the
two OSM ferry landings (Penn's Landing at 211 S. Columbus Blvd, Camden at Wiggins Park; the berths found by walking
from each landing toward the other until the Delaware's outline, then 9 m out). The 2026 season from
riverlinkferry.com: full service May 23 to Sep 7, Tuesday to Sunday and the Memorial Day and Labor Day Mondays, Camden
departing on the half hour 10:30 to 4:30 and Philadelphia on the hour 11:00 to 5:00, Saturday and Sunday adding 9:30,
5:30 and 6:30 from Camden and 10:00, 6:00 and 7:00 from Philadelphia; weekends only Sep 8 to Oct 27; and on a model date
with a Freedom Mortgage Pavilion show in the Ticketmaster feed, a shuttle from two hours before the show until four after.
`ferryDay` builds the day's candidates and takes them in time order only from where the boat is and only once it is free
(a 12 minute crossing and a minute's margin), so the timetable can never put it in two places. A crossing is a cubic arc
bowed 70 m downstream, eased like PATCO's runs, and the boat swings round off the berth over its first eighth; between
runs it lies at its berth as it came in, Camden overnight and out of season. Model: a pointed white hull with a blue
sheer band, the glazed main cabin (lit after dark), an open upper deck under a blue canopy, the pilothouse, a stack.
A ferry pin, and a card sharing the trains' slot: "To Camden, Wiggins Park, Arrives 11:12 AM" or "Docked at Penn's
Landing, Next Departure 11:00 AM" or "No Sailings Today", always "Timetable Position, Not Live", with the schedule's
link. The model date is a Wednesday after Labor Day, so today it lies at Camden. `__dbg.ferry()`, `__dbg.ferryCard()`,
`tests/test_ferry.py` (the season, the holiday Mondays, the weekend extras, the alternation, a show-day shuttle).

## Round 152 — the RiverLink ferry is M/V Freedom, on its own AIS (Sep 23)

Mike: "Does the ferry show up on our marine traffic website? If so can we leverage that data for location?" It does:
the Freedom broadcasts AIS as MMSI 368417620 ("M/V FREEDOM", 28 m), and the aisstream relay was already carrying it,
reporting it stopped at Wiggins Park within a few metres of where Round 151's timetable berthed it. So Round 151 drew it
twice: the ships layer's generic hull with an anchor pin and a "Vessel M/V FREEDOM" card, and the scheduled ferry
beside it (Mike's screenshot of the live site). Then: "this boat is the riverlink so get rid of the riverlink schedule
and label M/V Freedom as the Riverlink."

The timetable is gone (the season, the sailings, the show-day shuttle, the arcs, the berths, the schedule link). The
ships loop still eases the Freedom's fix like any vessel's, then skips drawing it (`FERRY_MMSI`); `updateFerry` stands the
Round 151 model and the ferry pin at that fix under the ships layer's own rules (on with the layer, gone with the 30 minute
despawn, live whatever the model clock says). Heading: the vessel's own compass when AIS carries one (both ingest paths
now note it as `v.th`; the Freedom reports 94 degrees moored, with course over ground a meaningless 360), else its course
while under way, else its last heading, else across the river toward the nearer landing. The card: "RiverLink Ferry",
"M/V Freedom", "Docked at Camden, Wiggins Park" (within 80 m of a landing and under half a knot) or "Under Way, 6.2 kn,
Toward Philadelphia" or "Stopped on the Delaware", "Live Position (AIS), Fix 8 min Ago", the MarineTraffic link.
Checked in the pane against the live relay: one boat at the Camden pier, the card as above, 44 vessels in the layer.
`tests/test_ferry.py` now pins the AIS wiring and that no timetable is left.

Round 152's review (three lenses: the live and timetable switch, position and heading, integration; a skeptic per
finding, 12 agents, the skeptics polling the live relay) ran on the first cut, which still kept the timetable as a
fallback; it confirmed thirteen findings. Three went with the timetable (the switch flapping every few missed moored
reports, the jump from the timetable spot on load, the next departure ignoring the landing). The rest are fixed. The
ships loop reckons a moving fix up to 10 minutes, and the Freedom's reports reach the relay one to three minutes apart,
so a crossing ferry slid past its berth into Wiggins Park while its card said live: the ferry now eases its own fix,
reckoned at most 30 s and never onto land (`delawareAt`), which also frees it from the ships loop's SHIP_CAP break that
could freeze it at its first fix. Its heading eases instead of snapping at each fix. "Toward Camden/Philadelphia" comes
from the course over ground, not the bow, so a ferry backing out is named for where it is going. The relay's fix ages
now run on the server's clock (the response's Date), not the viewer's, for every vessel. And turning the trains layer
off no longer closes an open ferry card (they share the card slot; this predated Round 152). `__dbg.ferryFix(x, z, hdg,
sog, age)` plants a fix: a two minute old one at 8 knots ends 30 s on, in the river, not 500 m inland.

## Round 153 — phones working again (Sep 24)

Mike: "The app is again not working on mobile. What can we do to fix this. I am just about ready to package this up as
an app and submit to the markets. This needs to be addressed immediately." Measured under the pane's touch emulation,
the build before Round 142 against the one deployed: the drawing buffer 925 by 450 against 1480 by 720 (Round 149's
2.0 pixel ratio: 2.6 times the pixels of every frame, with the multisampled backbuffer on top, over the same 11 million
triangles), textures 108 MB against 148 MB (Round 142's ten Wildey canvases at 1024), the JS heap 497 MB against 579 MB.
The hotfix: touch goes back to Round 74's 1.25 cap and 0.72 floor (Round 149 reverted: any raise needs a real phone
first), the Wildey canvases are 512 on a phone, and `PIER_RINGS` (every paved flat's outline, held only for the pier
lamps) is emptied once they are placed. After: 925 by 450, 123 MB of textures, a 521 MB heap.

## Round 154 — the phones' memory: what only the build needed now goes (Sep 24)

After Round 153's hotfix Mike chose to go ahead with the no-visual-cost savings from a read-only audit (16 agents:
heap retention, the phone's GPU and triangle budget, app web views; a skeptic per proposed saving; a ranked plan).

- The SEPTA road-snap grid (buses onto their streets, the overpass junction test, the grass sow) was a Map of 36 m cells,
  each a JS array with a copy of every segment whose bounding box touched it: about 717,000 entries, 65 to 75 MB of heap
  on a phone, most of it grown inside 'Raising the rest of Philadelphia', the heaviest step. The road passes now append
  to one Float64Array (`SRG`) and the first read freezes a dense index over the data's own extent (count, prefix sum,
  fill; the same cells, the same order), about 7 MB. `tests/test_septa_grid.py` runs it under Node against the old Map
  over random networks, a write after the freeze included: identical answers on 7,000 queries.
- The 43 inline data scripts (and their 43 progress ticks) kept their 27 MB of text attached to the page after their
  values were read: build.py tags them `data-blob` and the page removes them when its build is done.
- The far ground strips' vertex arrays are freed on upload (never raycast); the ground registry's normals, which kept
  them alive and are read only by build steps, are released when the build is done (`groundPlaneN` and `conformDrape`
  fall back to straight up after that).
- One spread of 46,145 arguments into `runs.push` (the traffic graph) is a loop: a spread that size can overflow a phone's
  stack.
Measured under touch emulation: the heap 486 MB (521 after the hotfix, 579 on Round 152, 497 before Round 142), the
page's script text 2 MB (29 MB), the build clean, the far ring drawn.

## Round 155 — the page ready for the Capacitor app (Sep 24)

From the audit's app list, the page-side part (Mike: the app is to be packaged with Capacitor). `IN_APP` (the wrapper's
'Philly3DApp' user-agent marker, capacitor://, or https://localhost) always takes the phone path, so an iPad with a
trackpad no longer builds the desktop city; the five philly3d.com feeds (concerts, Amtrak, lights, closures, lightning)
are relative only on the dev server (`DEV_LOCAL`), so in the app they no longer resolve into the bundle; share links and
Copy Link carry https://philly3d.com/ in the app (with only the page's own lights and bands settings); the service
worker registers only on the site; ships run from the relay alone in the app; the beacon reaches philly3d.com/b from the
app; the one unguarded AbortSignal.timeout is guarded. Phones recover by themselves: after a lost WebGL context the page
reloads (once in any two minutes), and a memory kill during use now counts, because the breadcrumb says 'running' while
the city is in front.

An adversarial review of the first cut (two lenses, a skeptic per finding, 10 agents) confirmed eight findings, all
fixed before this shipped: a context loss in the background (routine on iOS and Android) was taken for a memory death
and pinned lite for a fortnight, so now a background loss reloads the full build once the page is in front and a loss in
front makes only that tab lite (`philly3d.litenow` in sessionStorage); a 'running' crumb is fresh for three minutes, not
thirty, and one death while running makes that load lite while the fortnight needs a death mid-build or a second one
(a swipe from the app switcher or an in-app browser's Done never runs pagehide); the crumb is cleared on hidden, blur
and pagehide, and a hidden tab's timer no longer erases the one in front; www.philly3d.com counts as the site again (it
had lost its worker and Copy Link its query); only the app rewrites share links, so the dev server shares its own; the
app marker is tested before the dev-server test; the overlay after a second loss reloads on a tap in the app. Left for
Mike's go, since they are VPS edits: CORS on concerts.json and lightning.json, and exposing the Date header on the feeds.

## Round 156 — the Capacitor project (Sep 24)

Mike: "yes to the server change, set up the Capacitor project". The server: concerts.json and lightning.json now answer
any origin (the app's are capacitor://localhost and https://localhost), and every feed that did already (septa, ais,
amtrak, closures, lights, adsb) exposes its Date header, so the app reads the server's clock; tested, reloaded, backed up
to /root/philly3d.vhost.bak.20260924151152, and ops/philly3d.vhost.live is the live file again (it had lacked the septa
and ais blocks).

The app lives in app/, beside the page and apart from it (the page's build stays npm-free): Capacitor 8.5.2 with the App
plugin, app id com.philly3d.app, `appendUserAgent: 'Philly3DApp'` (the marker the page's IN_APP reads), the https scheme
on Android. `npm run sync` copies the built page into www/index.html and both native projects. Checked in Capacitor's own
source rather than taken on trust: iOS already reloads a killed web content process and sends other sites and
window.open to Safari; Android's default answer to a killed renderer crashes the app, so MainActivity answers true and
recreates the activity; Android asks for coarse and fine location at run time, so the manifest declares both, and iOS
has its location prompt text. Icons and splash come from the brand mark (scripts/make-assets.py, then @capacitor/assets:
74 Android, 7 iOS). The page hides the screenshot button in the app where the web view has no share sheet (Android).
node_modules and the build folders are marked for Dropbox to skip. Building needs Xcode, Android Studio and the two
developer accounts, none of them on this Mac yet: app/README.md.

## Round 157 — a phone's far windows (Sep 24)

Mike: "On mobile, the lights on buildings are not visible until you get very close. Is there anything we can do about
that that doesn't involve breaking the app on mobile?" Measured first, the same night poses at 740 x 360 touch (pixel
ratio 1.25, 925 x 450 render pixels) and at 1480 x 720 desktop (1.75, 2590 x 1260): from Society Hill the desktop draws
window grids on the Center City towers 1 to 2 km out and the phone draws grey slabs with a few skyline points. The
cause is not `detFarUniform` (it stretches `det`, which holds a phone's tower windows to about 2.7 km) but the second
gate in `resolved`: a room is drawn only while a floor spans 0.8 to 2.4 render pixels, and under that both facade
shaders fall back to a flat glow, 0.035 of warm light in the fabric and 0.055 in the curtain-wall glass, a quarter to a
fifth of the rooms' own mean (about 0.48 of rooms lit at 0.47 each, times the glass share). With a third of the pixels
a phone crosses that gate at a third of the distance: its towers fade 0.63 to 1.9 km where a desktop's fade 1.8 to 5.3.

The fix, touch only (`FAR_LIT = isTouch`; the desktop's shader strings are the untouched else branches, and a desktop
capture differed only in the pins, the wind in the trees and a theme colour caught mid-ease): under the resolved rooms
both shaders draw a pyramid of room blocks (`FAR_LIT_GLSL`). Each axis takes its own level, 2 to the L bays or floors,
so a block is at least two render pixels each way and a slanted wall gets narrow blocks rather than ones sized by its
worse axis; the four blocks around the level are blended, so a block never pops as the eye closes in. A block is lit at
odds of 0.35 and 1.37 times the rooms' brightness when it is, so the mean is the rooms' 0.48 (the test runs the hash)
while a block reads as a light rather than a lit wall, in the rooms' own warm tints. The blocks' weight is the desktop's
own resolve (its det at uDetFar 1 and its pixels-a-floor gate) evaluated at `FAR_K` 2.4 times the phone's pixels, so
the specks stand exactly as far as a desktop's windows do. The first cut faded them by a fixed 3.5 to 6 km instead, and
lit every mid-rise at 2.5 km into a field of specks busier than a desktop ever shows; the second cut's blocks were
three pixels on the worse axis and cool white, which read as a mosaic. The blocks are anchored to the wall: two frames
3 m apart hold the same pattern, moved with the buildings. Cost: no geometry, texture or memory; eight hashes on the
far wall pixels, cheaper than the roomLight the near ones already run. No pixel-ratio change (Round 153 stands).
`tests/test_far_lit.py`.

## Round 158 — the iPhone's memory, measured (Sep 24 to 25)

Mike: "The PWA is still getting the error on load". The server's beacons said more than any phone could: his iPhone
(iOS 27; Safari, the home-screen app and Chrome) had not finished a session on any build since Sep 19. On the builds up to
Sep 17 it reached the 60 s mark in 14 of 22 loads; since, 20 loads, 4 ready, none past a minute. Every death on the
Sep 23 to 25 builds came after the 'Planting the street trees' beacon, with the next load inside a second or two (WebKit's
one automatic reload), and no JavaScript error ever came from a phone: iOS killed the page for memory, reloaded it once,
and on the second death showed "A problem repeatedly occurred". Eleven of those reloads ran an OLDER build with no request
reaching the server at all, the Sep 5 build as late as Sep 18.

Four workflows (investigation 16 agents, implementation 4 in worktrees, two ANGLE skeptics, two reviews 17 agents) and the
primary sources settled the mechanics. WebKit charges WebGL buffers and textures to the page's own process, so the jetsam
limit covers JS and GPU together. It reloads a killed page with ReturnCacheDataElseLoad ("We allow stale content when
reloading a WebProcess that's been killed or crashed"), a session restore the same, and the service worker's fetch(e.request)
passed that mode through: hence the stale builds. And its ANGLE Metal backend copies every vertex attribute whose stride or
offset is not a multiple of 4 into a padded buffer it keeps as long as the buffer lives (kVertexAttribBufferStrideAlignment,
VertexArrayMtl::syncDirtyAttrib, on every Safari from 17.0 to 26): the chunks' 3-byte normals and colours and their three
1-byte words cost 49 B a vertex on an iPhone where they upload 29, and a WebGL audit (wrapping vertexAttribPointer and
bufferData) measured those hidden copies at 247 MB.

Measured, not guessed: a headless Chrome over CDP forcing a GC at every build step, with the WebGL audit injected, on
tonight's build, the merged fixes, and the two Sep 17 builds from git, the last that worked on his phone and the first that
did not. The pane's heap readings (800 to 1,500 MB) were garbage Chrome had not collected; the live heap at ready is 114 MB.
GPU plus hidden copies after the first frames: Sep 17 (worked) 981 MB, tonight 1,167, now 875. The build's worst moment
(live heap plus GPU): about 920, 1,200 and 830 MB. JS with its typed arrays at ready (full snapshots): about 260 then, 200 now.

What changed:
- The chunks on 4-byte streams (VBuf): normal and colour in stride-4 interleaved buffers read as three items, style, floor
  height and tint in one aSFT word (fourth byte 255 = bytes; mergeColored writes raw floats with 0), decoded through macros
  to the exact old values (a test runs all 256 bytes in float32 math); road colours through rgbStride4. 32 B a vertex, none
  copied. The audit reads 0 MB of padded copies now.
- A heap snapshot at 'Raising the outer districts' held 1.87 M arrays, 1.7 M boxed numbers and 345,000 closures: every road
  triangle near a terrain patch kept as an object with a triangleGrade closure, 165 MB alive from the street steps to 'Rolling
  out the SEPTA fleet', exactly the steps where the phones died. Nine float32 words each now (TRS); the trimmed ground is
  identical (359,902 surfaces, 105,662 triangles, 33,061 trims either way).
- The traffic linker on typed arrays, byte-identical graph (tests/test_traffic_link.py); the data scripts dropped before the
  build; the street-name SDF read in bands; one small numeric lamp grid; static texture sources freed after upload on touch;
  late meshes freed; no pole inventory on touch; ground normals dropped after paving; the weather pass's orphaned programs
  disposed; the resident flats, lots, roads and overpass packed (Int8x4 normals, Uint16 colours on 8-byte strides), facade
  geometry keeping its float normals (its window grid is world-anchored: a byte normal slid it a metre on the Custom House).
- Recovery: sw.js revalidates every navigation (no-cache: never stale, a 304 when unchanged); a touch load that finds a death
  waits behind a gate ("Philadelphia ran out of memory on this device last time. Tap to load a lighter city."), the build held
  until 32 s after load so WebKit's crash window has passed; tier 1 (today's LITE) then tier 2 (far ring 5 km, no far trees,
  traffic or roof kit); full-build deaths and context losses count; a second loss inside two minutes is still recorded;
  beacons carry the tier, why, standalone, navigation type, cache hit, render ratio and the previous crumb, and every step on
  touch.

Pixel diffs of desktop and phone, day and night, differ only in pins, swaying trees and cars. 279 tests. Left for Mike: the
gate's copy and tier 2's contents, and (a VPS edit) Cache-Control no-store on / so a crash reload outside the worker has no
copy to go stale.

## Round 159 — the skyscrapers' pale fade (Sep 25)

Mike, with two night screenshots (the phone's towers pale grey slabs, the desktop's dark with lit windows): "The
skyscrapers are too lightly colored at distance." Not Round 157's far blocks: the Round 156 build showed the same pale
towers at the same poses. Both window shaders faded from the resolved rooms to the far glow by blending the light's colour
(shtLamp, gLamp) and its amount (shtLit, gLit) separately, then multiplying the two. The product lights every dark room
part way through the fade: an unlit window at resolved 0.5 gave (0.035 + 0.965 / 2) x 0.82 / 2 = 0.21 where the blend of its
ends is 0.015, some fifteen times over, so a tower in its fade glowed pale grey from wall to wall. A phone's fade lies at
0.6 to 2 km, right in the view; a desktop's at 2 to 5 km. Both shaders now blend the finished light (the colour carries it,
the amount is 1), exact at both ends. Captures at the same poses: the phone's towers dark with lit windows like the
desktop's, and the desktop's far towers no longer pale. tests/test_far_lit.py holds the blend and its arithmetic.

## Round 160 — the Reading Terminal's 125 m slab (Sep 27)

Mike: fix the 125 m LiDAR bug first. Found while modelling the Reading Terminal for the landmark proposals: a sheer
curtain-wall slab 125 m tall, 82 m wide and 13 m deep stood behind the headhouse in every view. It was OSM way 335512395,
the two-storey link between the headhouse and the train shed (building:levels 2, no height), packed at 125.2 m. Two faults
compounded. The City footprint over the headhouse reads max_hgt 125.07 m over approx_hgt 44.5 m, a ratio of 2.81 under
the 3x contamination guard, while the point cloud's own roof pass measures the headhouse way flat at 44.6 m (P90), so the
max is a spike (a crane, a mast or a bad return) the guard missed. And the pre-LiDAR snapshot is not pristine there: it
was frozen from a scene an earlier in-place join had already patched, so it holds 125.1 for the headhouse outline and the
link, and the tall protection (never lower a snapshot tall) defended the spike. Rebuilding the snapshot was ruled out:
process_osm on today's extract differs from it on 99,000 of 111,000 records (Comcast Center 6 m), because the scene's
heights came from research passes, not raw tags. Neither building:levels (Centre Square, Jefferson Tower and ARIA carry
their podium's levels on the tower outline) nor the ratio alone separates a spike from a real tower or steeple.

lidar_join.py now CONFIRMS a spike with two witnesses against the max: an OSM way whose LiDAR roof is flat (P90 - P10 under
1 m, so anything taller covers under a tenth of it) covers half the footprint and the max stands over 1.5 x that roof +
10 m, and the City's approx_hgt agrees with that roof within 25 % while the max is at least twice it. A confirmed spike
contributes approx_hgt; places of worship keep the max (a steeple is indistinguishable from a spike in these numbers, and
the app gives steeples their own LANDMARK_H rows); and the protection no longer defends a snapshot tall that is exactly
what the spiked join gives. 51 footprints confirmed citywide. A plain rerun of the old code reproduces all 117,442 wide and
south heights exactly, and pack_wide reproduces wide.b64 byte for byte, so every change is the rule's: 43 scene records
lower, 36 packed (25 in h, 11 in h and the storey pitch derived from it), no geometry, order, road, area or wall colour
moved. The big ones: the link and the headhouse outline 125.1 to 44.5, Blue Horizon 63 to 22, the Academy of the Fine Arts
55.7 to 21.9, the Athenaeum 45.4 to 18, a block at Broad and Locust 65.1 to 28.1. The far ring's lidar_city_heights.json is
kept (--skip-city; a rerun would also carry the old KX frame fix). Captures at the same poses: the slab is gone from 12th
and Market, from the air and from the west; 113 tower specs and 233 crown matches either way. The link is still 44.5 m, not
its real 14: the footprint covers the headhouse and the link together; the Reading Terminal rebuild replaces both. The
Marriott skybridge (building:min_level 1, ignored by process_osm) still stands on 12th Street; the rebuild draws its own.
tests/test_lidar_spike.py.

## Round 161 — seven landmarks rebuilt (Sep 27)

Mike: "add all the proposed buildings". The Sep 25 design study modelled seven landmarks the city drew as generic blocks,
or not at all, from their real plans (HABS and HAER drawings, OSM footprints, photos), each by a research agent, an
independent reviewer and a revision pass, in a scratch harness that loaded the stock build, skipped the generic
footprints and mounted the model at the same camera, clock and weather (the private page "Philly3D Landmark Proposals"):
30th Street Station (20,118 triangles), the Fairmount Water Works with the dam's crest (24,928), Eastern State
Penitentiary, wall, towers, front and all fifteen cellblocks (21,806), the Divine Lorraine with its lit sign (32,269),
Founder's Hall (36,030), the Reading Terminal headhouse and train shed (33,718) and the Sparks Shot Tower, which the app
never drew (3,080).

They live in 3d-model/rebuilds/: _kit.js (the study's modelling kit, RB.kit(THREE); K.mat stores a photo colour for the
legacy pipeline, calibrated on the Museum of Art's Kasota stone) and one file per building, RB.add({ id, name, center,
skip, views, build(api) }), inlined by build.py as one script ahead of app.js. app.js reads RB.defs: a wide footprint
whose centroid lies in a skip ring is skipped at run time like DEMOLISHED (wideColK still counts it, its roof note kept
for losClear and the placards) and its outline joins REBUILD_OCC; 'Rebuilding the landmarks', right after the outer
districts (the wide ground grids are registered, nothing later moves them), builds each def through an api of the app's
own handles (the drawn ground, nightUniform, lampUniform, lampMapU, WXFX.dayF, the meadow material, occupy, pinAt), draws
it unculled once behind the veil so a phone frees its arrays there, and counts a def that throws in PERF.failed. Trees
keep off a rebuild's ground (trunk within 2 m, or a crown overhanging a ring a def registered below its top: the drawn
crown, CR x st[3] across), the packed poles too, the storefronts off every skip ring, and 30th Street's Rail Stations pin
moves onto the attic where the new concourse no longer hides it. The ports replaced the harness's scene lookups with
those handles and dropped its emulation (tree and pole clearing, the storefront cut, the pin wrap), which the app now
does itself. build.py: SHT_BUILD_OUT writes a scratch page, SHT_REBUILDS keeps only the named rebuilds.

Verified: all 24 of the study's views, day and night, against its reviewed captures: the same poses, 0.02 to 3.4 % of
pixels different (cars, swaying trees, pins, the night's theme colour), no page errors, no failed steps. A four-lens
review (wiring, porting, phones, build) with an adversarial check on each finding confirmed 11 of 21, all fixed: the
kit's builder held every pre-merge part through the defs' shader hooks (so a phone's freeOnUpload freed almost nothing;
parts.clear() after the merge), the meshes missed the behind-the-veil upload, the Shot Tower owned no ground (a surveyed
Goldenrain tree grew through its shaft), ten Reading Terminal storefronts stood in the skip ring, the skip left holes in
ROOF_GRID, a failed def went uncounted, the Reading Terminal's sign canvases stayed resident on touch, SHT_REBUILDS
ignored unknown ids, and stale comments. Phone emulation, GC-normalised: live heap at ready 113 to 115 MB, GPU 667 to
681 MB with no padded copies (every stream a 4-byte multiple), the worst moment (live plus GPU at the towns' upload) 867
to 890..910 MB against the Sep 17 build's 920. tests/test_rebuilds.py builds every def under Node against r149 (finite, on
its site, under 40k triangles, 4-byte streams, the skip counts per def against wide.b64, the app's wiring and the page).
The capture skill's memory tools now decode their own path (the checkout's spaces broke them).

## Round 162 — the first-run flow: pick your layers, then the how-to (Sep 27)

Mike, for the app on its way to TestFlight: "I want users to select the filters they want to see initially. Then walk
through the how to. Several slides currently have not uniform font sizes. Fix that."

The flow. A first visit's Enter opens the guide on one more card, "Choose what you see": the seventeen layers as toggle
chips in three groups (Getting around, Around the city, On the map), each in the layers panel's own name and icon, with
Recommended (the shipped defaults, landmark labels, bus stops and libraries off), All and None. A chip switches its layer
live through the panel's own toggle (layerToggles(), now shared with Reset Layers), so a feed's polls start and stop with
it and the choice is saved like any other (philly3d.prefs); a chip always shows the flag as it is. Next goes on to the
eight how-to cards; the ? button opens the how-to alone. Exercised headless: the picker first with 17 chips on the
defaults, None then saved all off, Recommended plus Landmark Labels saved exactly that and the panel agreed, Next to
Welcome, closing marks the guide seen, ? reopens at Welcome with eight cards.

The type. In Chrome every card already computed the same sizes; the unevenness is iOS's text autosizing, which in
landscape (the only way a phone sees the city) inflates a paragraph it judges long and leaves a short one alone, so The
live city's long rows grew past Flying's short ones. html now sets -webkit-text-size-adjust: 100%. The cards also carried
three sizes in every row (a 23 px title, 12 px text and 9 px spaced capitals for the key labels, 19/11/9 on a phone) and
the Round 60 step-down rules had been dead since the redesign overrode them: now two sizes, the title and everything
else, the key labels at the body's size in bold bronze (22/13 px on a computer, 18/12 on a phone), one scale in one
place. Measured on every card, computer and phone: one size set each. A card with more than fits scrolls with a fade at
its foot (Search, share and more had clipped its Install row on a computer), the card is a little roomier (700 by 560),
and a new card opens at its top. Inside the app the Install row (Add to Home Screen) is left out. tests/test_guide.py.

## Round 163 — the iOS app ready for TestFlight, the code side (Sep 27)

Mike: "do the code side for TestFlight now". Xcode is not on this Mac (the command-line tools only), so nothing here was
built or archived; every file was linted (plutil, xmllint) and the page's side exercised headless.

- Info.plist: landscape only on iPhone and iPad (the page's rotate gate would face a portrait phone, and a small iPad in
  portrait matches its 820 px query too), UIRequiresFullScreen (App Store validation wants every iPad orientation
  otherwise), ITSAppUsesNonExemptEncryption false (HTTPS only, exempt), arm64 in place of the template's armv7.
- ios/App/App/PrivacyInfo.xcprivacy, the app target's own manifest, added to the target's Resources in the pbxproj: no
  tracking, no tracking domains, no required-reason APIs; the load beacon's Performance Data and Other Diagnostic Data,
  not linked, for app functionality. Location is not collected (the fix never leaves the phone; the near-me card asks
  SEPTA by stop number).
- The launch screen's background is the splash's own ink, not systemBackgroundColor (white in light mode); the three
  unreferenced 2732 px template splash files are gone.
- One location prompt: @capacitor/geolocation 8.2.2, registered by cap sync on both platforms (CapApp-SPM's Package.swift,
  capacitor.settings.gradle). Inside the app the page takes the fix from Capacitor.Plugins.Geolocation (the bridge
  injects it, no bundler), so iOS asks once in its own prompt; WKWebView's navigator.geolocation asked again naming
  "localhost". Posing as the app headless with a stubbed plugin: a grant flew to City Hall, said "You are here." and
  opened the near-me card; a refusal checked the permission and said "Location access was declined. Here is City Hall
  instead."; navigator.geolocation was never called. A browser takes the old path.
- npm run sync: the app's bundled page is the current build (it was Sep 25's). npm run bump raises iOS's
  CURRENT_PROJECT_VERSION and Android's versionCode together for each upload after the first (tried on a copy).
- app/README.md: what is done, and TestFlight step by step (Xcode and the team, sync, bump, signing, App Store Connect's
  record and privacy labels, archive and upload, internal and external testers). tests/test_app_ios.py guards the lot.

Left for Mike: the Apple Developer account and Xcode, the App Store Connect record, and the privacy policy (the draft,
3d-model/privacy.html, is accurate; publishing it and linking it from About waits on his go).

## Round 164 — the privacy policy published, and Google Analytics kept to the website (Sep 28)

Mike: "publish the privacy policy and link it from About. I am going to be adding google analytics and google search
console if you need to mention anything about those."

- privacy.html is at https://philly3d.com/privacy.html: deploy_philly3d.sh stages it with the page and fails unless the
  live copy hashes the same. The About panel links it (#aboutPrivacy, in the credits' bronze, above the data credits):
  Apple wants the policy reachable inside the app, where the link opens in Safari.
- The policy (dated Sep 28) now covers Google Analytics on the website only: what it records (pages, time, referrer,
  city and country from an IP it does not keep, device and browser, a random identifier in a cookie), no advertising
  features, the shortest retention Google allows, Google's policy and opt-out links; Search Console (how the site shows in
  Google Search, as totals, nothing about visitors); "no analytics services" is gone from the promises, the children's
  section says the site does not knowingly collect from under-13s.
- One loader, app.js's GA_ID behind ON_SITE (philly3d.com, never the app, never a dev or scratch host), off until the
  measurement ID is filled in, with allow_google_signals and allow_ad_personalization_signals false. The apps' privacy
  manifest and App Store labels declare no analytics, so a plain tag in template.html, which would run inside the app, is
  what tests/test_privacy.py refuses. The property's Enhanced measurement must not count history changes as page views:
  updateHash rewrites the address every 500 ms in flight.
- Xcode was installed with its license not yet accepted, which turns /usr/bin's python3 and git into license errors;
  commands here ran with DEVELOPER_DIR=/Library/Developer/CommandLineTools (the scratch server's launch entry too).

Round 164 coda (Sep 28), the first Xcode build: with the license accepted, xcodebuild still needed its first-launch
components (xcodebuild -runFirstLaunch, no password), then built the app for a device (Release, unsigned) straight from
the Dropbox folder in 19 s: BUILD SUCCEEDED, two harmless upstream warnings (Capacitor's App plugin, AppIntents). The
bundle holds PrivacyInfo.xcprivacy, the landscape-only and export-compliance Info.plist, the geolocation plugin
(registered in packageClassList and linked), and the live page byte for byte. Package.resolved is committed so every
build resolves the same Capacitor and ion-ios-geolocation. No simulator runtime is installed yet, and no signing identity:
archiving for TestFlight waits on the Apple ID and team in Xcode.


## Round 165 — the first run in the iOS Simulator (Sep 28)

Mike: "install the simulator runtime and run it. I am logged into xcode with my apple ID. I do not see the bundle when
trying to create in app store connect."

- The iOS 27.0 Simulator runtime (8.05 GB, `xcodebuild -downloadPlatform iOS`) is installed; the app built for an iPhone
  17 simulator (Debug) and ran. iOS turns the landscape-only app on its side on a portrait device, as it should. The
  build loads to Ready, the first visit opens the layer picker ("Choose what you see") and then the how-to cards in one
  type scale, and the Locate button raises exactly one prompt, iOS's own, with the Info.plist's words; with a simulated fix
  at 39.9496, -75.1503 and Allow While Using App it glides in, marks "You are here" and opens the near me card.
- Two faults showed, both fixed. The near me card is taller than the room above the mark in the middle of a landscape
  phone (402 points) and lost its top under the screen's edge: the fifteen places that positioned the card
  (`vehinfoEl.style.transform = 'translate(-50%,-100%) ...'`) now call one `vehinfoAt(px, py)`, which keeps the card
  standing on its point but slides it back inside the window and the safe area (the notch and the home bar, read once per
  size from a probe because JS cannot read env()), the top winning over the bottom; `#vehinfo` has a max-height of the
  window and scrolls past it. The web on a phone has the same landscape height, so the site gets it too. And the veil's
  Explore arrow (U+2197 in `.enter::after`) drew as a blue emoji tile on iOS: it carries U+FE0E now.
  tests/test_card_fit.py.
- After a reinstall the gate reads "ran out of memory last time": simctl's install kills the app in the foreground, with
  the Round 158 crumb still set. A user's force quit or an App Store update backgrounds the app first, which clears it.
- The bundle ID: the project had no team (DEVELOPMENT_TEAM empty), so com.philly3d.app was never registered as an App ID,
  and App Store Connect's New App list shows only App IDs registered on the team. Xcode's account holds two teams,
  QuincySoft LLC (a paid company team) and a free Personal Team; choosing the paid team under Signing & Capabilities
  registers the ID, or it can be registered at developer.apple.com under Identifiers.

Round 165 coda (Sep 28), the team: Mike: "QuincySoft LLC is always the team i use." The App target now carries
DEVELOPMENT_TEAM 72U2ZL3GVM in both configurations and DevelopmentTeam in its target attributes, as Xcode's own picker
writes them, with automatic signing; the simulator build still succeeds. Xcode registers com.philly3d.app under
QuincySoft LLC the first time it resolves signing (the Signing & Capabilities tab or a device build), and only then does App
Store Connect's New App list offer the bundle id. tests/test_app_ios.py guards the team; app/README.md's step 4 says so.

Round 165 second coda (Sep 28), the bundle id registered (Mike: "go ahead and register it"). A device build with
-allowProvisioningUpdates created an Apple Development certificate (Michael Harkins, S935B3DCBU) and QuincySoft's wildcard
development profile (XC Wildcard, 72U2ZL3GVM.*), but no explicit App ID: an app with no capabilities signs for development
under the wildcard, and App Store Connect never lists a wildcard. Only App Store signing needs the explicit id, so the app
was archived and exported for app-store-connect with destination export (a local IPA, nothing uploaded): that registered
com.philly3d.app as "XC com philly3d app" (72U2ZL3GVM.com.philly3d.app) with the profile "iOS Team Store Provisioning
Profile: com.philly3d.app", signed by the team's existing cloud-managed Apple Distribution certificate (expires Aug 4, 2027).
The exported App.ipa (13.5 MB, 1.0 (1)) is signed com.philly3d.app / 72U2ZL3GVM and carries the live page byte for byte.
App Store Connect's New App list now has the bundle id; the upload waits on the app record and Mike's go.

Round 165 third coda (Sep 28), the first TestFlight upload (Mike: "app record created, upload it to TestFlight"). The icon
checked first (1024 by 1024, no alpha, the City Hall mark), then the same archive, 1.0 (1), com.philly3d.app, exported with
destination upload through the Xcode account: "Upload succeeded", processing on Apple's side. The options are
app/ios/UploadOptions.plist and app/README.md step 7 has the two commands. Build 1 is spent: `npm run bump` before the next.

Round 165 fourth coda (Sep 28), ITMS-90683 on build 1: App Store Connect accepted build 1 but mailed "Missing purpose string
in Info.plist": NSLocationAlwaysAndWhenInUseUsageDescription. Apple's scan found requestAlwaysAuthorization in
ion-ios-geolocation (IONGLOCAuthorisationRequestType's .always branch); @capacitor/geolocation only ever requests
.whenInUse, so the prompt stays When In Use and nothing runs in the background, but the key is required once the symbol is
linked. Info.plist carries it now ("only while you are using the app ... never uses your location in the background");
tests/test_app_ios.py, which had refused the key, now requires it and guards the real invariant (the plugin asks
.whenInUse and nothing else, no location background mode). npm run bump made it build 2 (Android versionCode 2 with it),
archived and uploaded the same way: "Upload succeeded".

Round 165 fifth coda (Sep 28), the TestFlight invites (Mike: "Still havent gotten the invite. Are you able to send
directly?"). Mike made an App Store Connect API key (App Manager); it lives in ~/.appstoreconnect/private_keys (0600) with
its ids in ~/.appstoreconnect/philly3d.json, never in the repo. app/scripts/asc.py signs the ES256 token with openssl (no
packages; the DER signature converted to r||s, checked 20 of 20 against a throwaway key) and reads the truth: both builds
VALID and internal IN_BETA_TESTING, both groups (18F and the new "Philly 3D") holding both builds and both testers, Mike
INSTALLED, Kaitlin INVITED. "Ready to Submit" on the web is the external state and never held an internal tester back. The
invitation to Kaitlin was resent through POST /v1/betaTesterInvitations (201). `asc.py status` and `asc.py invite <email>`
are the chores from here on (app/README.md step 7).

## Round 166 — the resolution controller lowers the ratio only where lowering it buys time (Sep 28)

Mike, from the TestFlight app (build 2): "The graphics are looking pretty pixelated. Are we able to spruce those up while
maintaining performance?" Then: "Do the smarter resolution controller", and "ship build 3 to TestFlight when it's ready".

- The evidence, from the server's beacon log. His iPhone (app, tier 0, fly) started at the touch cap, 1.25, and by the 60 s
  perf beacon sat at the floor, 0.72, a quarter of the screen's own resolution each way, with p50 29 ms, p95 104, 380 calls
  and 10.7 M triangles. Every phone perf beacon since Sep 25 that reports the render ratio ended at 0.72, the site's as well
  as the app's, with p50 anywhere from 17 to 75 ms at 8 to 10.7 M triangles. The phones are held back by geometry, so every
  step down cost sharpness and bought nothing, and the way back up (four windows under 13 ms) never came: a 60 Hz display
  never shows a frame under 16.7 ms. The history (a workflow reading Rounds 72 to 161): Round 153 blamed Round 149's 2.0 / 1.0
  for the phone deaths, but the deaths began four days before Round 149 and survived its revert, and Round 158 found them in
  ANGLE's padded vertex copies (247 MB) and 165 MB of road closures on the heap; the ratio's own cost is the drawing buffer,
  about 24 MB at 1.25 on a landscape iPhone with the multisampled backbuffer, which the page already allocates at load.
- The controller (`dprInit`, `dprJudge`, `dprGap`, `dprBeacon` after `applyDPR`; frame()'s hook): a ladder of rungs from the
  cap down by Round 74's steps to the floor (touch 1.25, 1.0, 0.8, 0.72; desktop 1.75, 1.49, 1.26, 1.07, 0.9; no rung so close
  to the floor that the last step could not buy 12% in pixels). Judged from Enter on, per window (15 frames on a phone), on
  the mean without the slowest fifth, since a median of display-paced frames jumps a whole refresh at a time. Every step is
  an A-B-A trial: three windows over 22 ms start a step down, one window settles, two are measured at the trial rung, one
  more back at the rung before; kept only when every trial window beats the lightest look at the rung before by 12%. A step
  up starts on headroom against the display's own interval (the fastest frames snapped to 144, 120, 90, 60 Hz, or 30 in Low
  Power Mode) or once a level has stood 10 s, and is kept inside 85% of the budget or at most 8% dearer than the heaviest look.
  A refused step holds 20 s doubling to 320 s and is retried only on a load 20% heavier (down) or lighter (up), or after the
  320 s; trials are 20 s apart unless three windows run over 40 ms; a kept step holds the reverse step at least 30 s, doubling
  when steps keep reversing; the first refusal from the cap tries the floor once (frames paced at 60 Hz can gain nothing one
  rung down and half at the floor); a gap over 250 ms abandons a trial and forgets the windows. The cap is unchanged, so the
  load's peak is unchanged; a geometry-bound phone now rests at 1.25, three times the pixels it rested at, about 15 MB more.
- Reviewed by a workflow on three lenses (the loop's logic, how iPhones really pace and reallocate, telemetry and tests),
  each finding put to a skeptic. The first design (a median, one look at the rung before, 13 ms headroom, no reverse holds)
  failed in the reviewers' simulations: a 60 Hz phone that stepped down never came back (99% of the time below the cap), a
  view swinging on an 8 s turn sank a geometry-bound phone to 0.72 (76%), a trial straddling the app in the background was
  judged across the gap, and a pixel-bound phone near the budget flipped 5.6 to 8.4 times a minute. All of it is fixed and
  tested. What stays: snow and 1 px lines are sized in drawing-buffer pixels, so on phones they now draw at 0.58 of the size
  they had at 0.72; on desktop a rung change reallocates the post pipeline's target (rare now).
- The beacons: `perf` (60 s after Enter) and the new `settled` (180 s, named so `st=perf&` stays one sample a session) carry
  `dpt` (down kept, down undone, up kept, up undone), `dpm` (the time-weighted ratio), `dpl` (the lowest ratio tried), `dpv`
  (the display's interval) and `dpf` (the last frame ms at each rung): on a real phone they say what the ratio bought. The
  privacy policy's beacon sentence now says the page reports again one and three minutes into the city, and how smoothly it
  draws. `__dbg.dpr()`. tests/test_dpr_controller.py (17 tests) cuts the DPR literal, the controller and the hook out of
  app.js and runs modelled devices frame by frame under Node: geometry-bound (constant, 60 Hz paced, noisy, a drifting view,
  the app backgrounded mid-trial, Low Power Mode) stays at the cap; pixel-bound steps down, stops where the gain stops, finds a
  gain only at the floor, answers a load that turns heavy within seconds, and does not hunt.
- The site waits for the phone: the resting ratio rises, so build 3 goes to TestFlight first, and philly3d.com gets it once a
  session on Mike's iPhone reaches the `settled` beacon without a crash crumb.

Round 166 coda (Sep 28): build 3 (1.0 (3), npm run bump, the page byte for byte in the archive) uploaded to App Store
Connect through app/ios/UploadOptions.plist: "Upload succeeded". Both internal groups have access to all builds, so it
reaches Mike and Kaitlin when processing ends. philly3d.com stays on HEAD~ until a build 3 session reaches `settled`.

## Round 167 — an X on the event markers, and the no-visible-change triangle cuts (Sep 28)

Mike: "go ahead with the no-visible-change package. Also I would like an X in the upper right corner to get rid of concert
and sporting events. The pin should not come back unless someone taps on the building those events are happening in."

- The X: every score bubble and concert placard carries a small round mark on its upper right corner (`.lbl.score .lx`,
  a 20 px mark with a finger-sized target around it; #labels stays click-through). `eventHide` records the event's own id
  (`s:<espn id>` for a game, `c:<ticketmaster id>` for each show on a placard) in localStorage `philly3d.hiddenEvents`
  with the moment it can be forgotten (the game's start plus its typical length plus three hours; the show's end plus an
  hour), prunes expired ids on load, and re-lays the labels: a dismissed game leaves no gap in the arena's two-bubble
  stack and the placards over the games re-stack; the bubble, its tether and its ball stay down through every poll,
  re-render and reload, while a new game or show at the same building is a new id and shows. A notice under the bar says
  "Hidden. Tap its building to bring it back." `bldgPick` now takes its point out to 14 km (a placard shows that far) and
  asks `eventTapRestore` before anything else: a point within 60 m of a placard's spot (`EVENT_TAP_R`, the halls stand on
  their own centroids) or within a score venue's own radius (170 m for the ballpark and the stadium, 110 m for the arena,
  so the field and the stands count) brings its events back, and that tap opens no property card; a tap with nothing
  hidden, or on another building, is the building card as before (still 3 km). A bubble off screen or behind a building
  is now hidden with visibility as well as opacity, so its X cannot catch a tap while invisible. Checked in the pane:
  the X is the element under its own centre; the ballpark's bubble hid and came back from a tap on the stands; hiding the
  lower arena bubble dropped the upper one to 114 m; a TLA placard stayed hidden through a full reload and returned from a
  tap on the hall; a later tap on the same hall opened its property card. The privacy policy's device-storage list names
  the closed markers. tests/test_event_dismiss.py (the wiring, and eventHide / eventTapRestore under Node).
- Build 3 on Mike's iPhone (Sep 28, 7:02 PM, after dark): ready 10.5 s, and at the 60 s perf beacon p50 79 ms, p95 106, 9.9 M
  triangles, the display paced at 30 Hz (dpv 33.3: Low Power Mode or a hot phone), dpt 1.1.0.0 (one step down undone, the
  floor probe kept: at night the phone was partly fill-bound, 40 ms at 1.25 and 32 or less at 0.72), dpm 0.77. The page died
  75 to 85 s after Enter at 0.72, the ratio the old controller would have sat at, and the next launch took the gate and
  tier 1 (pv running, lr cts). The only real-phone death the log holds since Round 158 (the 11:24 one was the Simulator
  reinstall); slow sessions are not new (p50 56 to 75 ms at every hour since Sep 16). So the crumb now says what the city was
  doing: bootRun writes it every 5 s with bootCtx (s seconds since Enter, r the ratio, t an open trial, n ratio changes, c
  seconds since the last, v the display's interval, d the day factor, m the recent frame median), and every beacon of the
  next load carries it as pc. Mike asked whether a server upgrade would help: no, the city is built and drawn on the phone;
  the server only serves the page and the small live feeds.


## Round 167 (part) — the trees and the ties cull, and the pins' depth image is read without waiting (Sep 28)

Mike approved the "no visible change" package to cut what phones draw. His iPhone's beacons: 9 to 12 M triangles a frame at
about 29 ms, geometry-bound, and about 7.5 M of them drawn in every view because the big meshes can never be culled. This
part takes three items.

- The trees cull. r149's InstancedMesh constructor sets `frustumCulled = false`, so the 68 tree meshes (2.27 M triangles on a
  phone) drew in every view: the hand-set chunk spheres in `instMesh` were never consulted. `fitInstSphere` (beside
  `pendingUpload`) now sets each mesh's geometry sphere round every instance as drawn: each instance's copy of the shape's
  own sphere through its matrix, a crown grown by `CROWN_GROW` 1.21 (canMat's lumps, `0.79 + 0.42 * vh` about the shape's
  origin) plus `CROWN_SLACK` 0.1 of the unit shape (the sway reaches 0.07), 2 m of margin. Checked in the page against the
  real data: 68 meshes, 111,683 instances, 10.1 M vertex positions at both lump extremes plus the sway, every one at least
  2.02 m inside its sphere. The hand-set spheres (chunk centre at y 10, half diagonal plus 40 m) are gone with their helpers.
- The ties cull. The El's 41,236 sleepers and PATCO's 6,343 were two InstancedMeshes whose box's sphere sat at the origin
  (0.57 M triangles from everywhere). `tieRuns` poses them in runs of up to `TIE_RUN` 500 m of track (a step over 10 m
  starts a new run: the next track or corridor), 41 meshes in two groups ('El Cross Ties', 'PATCO Cross Ties'), each culled
  by its own fitted sphere; `tieRunsNear` (every frame, before anything renders) hides a run whose box is farther than
  `TIE_NEAR` 700 m, or farther than where a tie's 0.24 m is 0.15 of a drawing-buffer pixel (`TIE_PX_M` times the focal length:
  700 m on a phone at 1.25, about 1 km at 720p, 1.8 km on a 2x desktop). Each run keeps what the one mesh had: `freeOnUpload`
  on its box, its matrices dropped at upload through `dropUploadedArray` (the sphere is taken first).
- Gotcha 12: every newly culled mesh goes into `pendingUpload` unculled and `frame()` sets it culled after the first frame,
  which is drawn behind the veil, so each uploads there as before with no extra render (an extra flush at the build's end
  would also compile programs the weather pass then disposes). `tieRunsNear` hides nothing until that frame has drawn.
- The pins' depth image no longer stalls the page. `pinOccCapture` read it with `readRenderTargetPixels` into an array every
  10th frame on a phone, which waits for the GPU to draw the whole city into the target (the likely source of the 104 ms
  p95). On WebGL 2 the read now goes into a pixel pack buffer behind a fence (`PIN_ASYNC`, `pinOccIssue`): three's own
  `readRenderTargetPixels` with the buffer bound and 0 as the offset, the buffer unbound in a `finally` at once, `fenceSync`,
  `flush`. `pinOccPoll`, first thing in every frame, asks the fence and once it has passed copies the pixels with
  `getBufferSubData` and only then installs that capture's view and projection, so the image and its matrices always match;
  the frame it lands counts as the capture for the Round 138 agreement (`PIN_OCC.fresh`). One read in flight ('busy' skips a
  turn and keeps its cadence); the first image, a resize, a jump of the eye over `PIN_JUMP` 300 m since the last capture (a
  shared link, a located fix; the fastest flight covers under 270 m between captures), WebGL 1, a refused first read (one
  `getError` check), a lost context, or a fence that has not passed in 120 frames counted only after a task has ended (a
  fence passes only between tasks) take the synchronous read, the last three for good. `__dbg.pinAsync(false)` forces it.
  The capture cadence and `PIN_FADE`/`PIN_HOLD`/`PIN_DWELL` are unchanged; the building tap's `occRender` still reads at once.
- Measured headless (Chrome, SwiftShader, phone emulation 740 x 360 at 1.25, touch, e292604 against this build, concerts
  seeded so the pin capture runs, traffic on). Main pass, triangles and calls a frame:
  entry 9.40 M / 356 to 8.18 M / 330 (-1.22 M), skyline 11.12 M / 450 to 10.40 M / 432 (-0.72 M), high looking north
  12.34 M / 574 to 11.38 M / 552 (-0.97 M), Center City looking west at 250 m 8.97 M / 343 to 7.45 M / 310 (-1.52 M),
  Spruce Street 9.97 M / 388 to 8.95 M / 360 (-1.02 M), 150 m looking north 11.64 M / 485 to 10.90 M / 467 (-0.74 M): the
  trees drew 1.34 to 2.13 M of their 2.27 M and the ties none of their 0.57 M at these six. The pin capture (clock pinned):
  9.56 to 8.46 M, 11.77 to 10.97, 12.42 to 11.70, 9.33 to 8.03, 10.21 to 9.37, 11.99 to 11.28 M a capture. Hooked GPU
  681.3 MB at ready and 859.4 MB after the first frames in both, `__gpu.mis` 0 in both; live heap 115.0 / 117.6 MB against
  115.2 / 117.9. SwiftShader cannot price the stall (its GPU is the CPU, which was loaded to 60 to 120 by other work), so the
  readPixels audit is the proof: the old build made a synchronous 240 x 117 read at every capture, this one only at the first
  image and at each pose jump, and issued the others in 0.3 ms (max 0.9).
- `tests/pin_readback_gpu.html` runs the production `PIN_ASYNC` block on a real WebGL 2 context: the image read through the
  pack buffer is the synchronous one byte for byte (0 of 115,200 differ), lands after one poll, carries its capture's
  matrices, and three's synchronous read of another target works while it is in flight (PASS under SwiftShader).
- Pixels, same poses at 925 x 450, share of pixels more than 8/255 apart: with the pin and live layers off, the El up
  Front Street from 70 m 0.0014% (6 px, max 22) and from 120 m 0.0086% (36 px, max 42), skyline 0.0014%, the Ben Franklin
  at night from the river 0.0005% (2 px), a night view by the span 0%; with the pin layers on, Center City 0.0010%, skyline
  0.0014%, 150 m north 0.0094%, a park 0.0029%, the skyline at night 0.0053%. Three views differed by 0.2 to 0.5%, all of it
  live AIS anchor pins present in one run and not the other (the AIS socket got past the blocked-URL list in one run) and a
  PATCO train's lights; the crops at 5x show the same geometry.
- tests/test_cull.py (16): `fitInstSphere` under Node against random poses of every tree shape and the tie box (every vertex
  as the shader can move it inside, the box right), the crown bounds against the shader's own literals, every tree mesh fitted
  and pending, the tie runs' wiring and their hiding by distance and by sharpness, the first-frame release, and the async block
  against a scripted WebGL 2 context (landing with its own matrices, busy, resize, jump, WebGL 1, a refused read, a fence that
  never passes counted only across tasks, a lost context) and pinOccUpdate with landings a frame late. test_el_tracks checks
  every El tie inside its run's sphere and within 500 m of the run's first; test_memory_cuts and test_patco follow the ties
  into `tieRuns`. The capture skill's `pin_sweep.js` yields a task every frame (in one task no fence can pass) and its
  `gpuhook.js` counts a pixel pack buffer against its own binding (it read the array buffer's and overwrote that size).
- Not taken: the two bridges' walkway lamps (`bfbLampMesh` and the Walt Whitman's, 340 lamps, 12,240 triangles) are the only
  other static InstancedMeshes; they have no fitted sphere and are 0.1% of a frame. The roof kit, the grass, the cars, the
  pins and the fleets are re-laid round the eye or move, and keep `frustumCulled = false`.

Round 167 (part) review coda (Sep 28): an independent verifier compared e292604 with db18f58 on the phone canvas and found
the ties' distance hide visible. Confirmed, and fixed with the three minor points.

- The hide is gone. `tieRunsNear` hid a run past `TIE_NEAR` 700 m on a rule that looked only at a tie's 0.24 m width; its
  2.6 m length is still about 1.5 px there, antialiasing mixed it into the bed, and a whole 500 m run switched at once. Our
  own captures had missed it because none faced the El from far off. Measured headless on the real GPU (Chrome, ANGLE Metal,
  Apple M2 Max; phone emulation 740 x 360 at 1.25, traffic and the pin and live layers off, clock pinned), share of pixels
  more than 8/255 from e292604: db18f58 differed by 808 px (0.194%, max 57) in the El overview (`goFly(-200, 400, -400,
  0.46, -0.25)`), 95 looking across the El from 830 m, 57 high looking north and 72 in the El overview at night, all on the
  El and PATCO lines; this build 0, 11, 0 and 18, at the load-to-load floor (e292604 against itself: 0 to 70 px a view,
  scattered roof and grass pixels, none on the tracks), and the El crops of the two show the same pixels. On SwiftShader,
  the verifier's renderer, the El overview is 0 px by day and 3 at night (751 and 86 for db18f58 there), across the El 14. The runs still frustum-cull, which
  changes no pixel: `tests/test_cull.py` now checks from 400 random eyes that a run with any corner of any tie in the frustum
  always passes three's own `intersectsObject`. `TIE_RUN` stays 500 m: 250 m runs would draw 50 k fewer tie triangles at the
  skyline, 9 k at 150 m and none at the other poses, for 6 to 20 more calls (a Node census of the El's own ties).
- A pin capture turn that finds a read in flight tries again the next frame (`PIN_OCC.retry`) instead of waiting for the
  next multiple of `every`, so late fences cost no whole cadence. Under the page's own rAF loop on the real GPU a read lands
  3 to 4 frames after it goes (150 to 400 ms at the headless 20 to 30 fps), under the cadence, so the retry never fires
  there: 10 or 11 images installed in each of three 111-frame turns, against 11 for e292604 and 10 or 11 for db18f58, and
  0 blinks in all three builds (frame p95 there 83 to 117 ms against e292604's 117 to 150). In the bench's unpaced loop,
  where fences ran over 10 frames late, each read went as the last landed. A real phone's latency is still unmeasured.
- The capture skill's `cap.js`: `__cap` and `__frames` yield a task between frames and are async (await each); a name ending
  in `.png` is written as a PNG, which `flicker_diff.py` always asked for. SKILL.md section 7 says why.
- `EL_STATS.addedDrawCalls` is gone (the ties are 31 runs, a draw each in view); `__dbg.cull()` drops `tieNear` and adds
  `tieTrisAll`.
- Numbers, e292604 against this build, same Metal bench with concerts seeded and traffic on. Main pass, triangles and calls a
  frame: entry 9.40 M / 356 to 8.33 M / 340 (-1.07 M), skyline 11.24 M / 450 to 10.76 M / 447 (-0.48 M), high looking north
  12.49 M / 574 to 11.96 M / 583 (-0.53 M, 9 more calls: 31 tie runs in view), Center City west at 250 m 9.19 M / 343 to
  7.83 M / 320 (-1.36 M), Spruce Street 10.18 M / 388 to 9.32 M / 370 (-0.86 M), 150 m north 11.83 M / 485 to 11.38 M / 486
  (-0.45 M). The ties in view: 155 k of their 571 k at entry, Center City and the street, 222 k at the skyline, 285 k at
  150 m, 416 k high looking north (db18f58's hide drew none at these six, which is where its larger numbers came from). The
  pin capture: 9.56 to 8.61 M, 11.77 to 11.49, 12.62 to 12.33, 9.54 to 8.38, 10.45 to 9.74, 12.23 to 12.06 M. Hooked GPU 681.3
  MB at ready in both, 874.3 against 874.4 MB after the first frames (the pack buffer, 0.11 MB), `__gpu.mis` 0 in both; live
  heap 115.0 / 117.7 against 115.2 / 117.9 MB. `tests/pin_readback_gpu.html` passes on Metal as on SwiftShader.
- Tests: `test_cull.py` (18) drops the hide's test for `test_no_run_is_hidden_by_distance` and the random-eye culling check,
  fits the tree shapes cut from app.js itself (the vase is `concatGeo`'s cylinder and scaled icosahedron cap, both crown
  details), and adds `test_a_busy_turn_tries_again_the_next_frame` (a fence 14 frames late: an image every 14 frames, where
  the old turn gave one every 20).

## Round 167 (part) — the city-wide flats go in as frustum-culled tiles, and the merge (Sep 28)

- A merged world-space mesh that spans the city has one bounding sphere as wide as the city, so frustum culling never
  dropped it: every view drew the far ring's streets (1.10 M triangles on a phone), its ground strips (0.66 M), the outer
  districts' streets (0.55 M), the overpass decks (0.37 M), the lots and yards (0.24 M) and the far parks (0.12 M) whole.
  `tileGeometry` cuts each into grid tiles by triangle centroid before the first upload (every triangle's vertices bit for
  bit and in order within its tile; every attribute's type, item size, normalisation, usage, interleaved stride and offset;
  the upload hooks; a Uint16 index where packIndex would make one; the source consumed attribute by attribute), `tileMesh`
  gives each tile the source's material, order, layers, shadow flags, userData and hooks, and `addTiles` stages them like the
  chunks. `TILE_CELL`: streets and decks 4.8 km, ground 7.2 km, lots 9.6 km, the ring's areas 19.2 km, the outer districts'
  streets 1.8 km, chosen from a 600 m cut of every mesh on a phone's frustum at six poses; the far water, the outer
  districts' parks and the street lettering stay whole (no cell paid for its calls). The decks' tiles are the raycast
  targets. `?tiles=0` draws them whole. tests/test_tiles.py.
- Independent verification (headless phone path, e292604 against the tiles alone): 0.67 to 1.64 M triangles fewer a frame at
  six poses and 0.60 to 1.54 M fewer in each pin capture, for 47 to 115 more draw calls; GPU after the first frames 859 to
  852 MB, padded copies 0 in both, every tile uploaded and freed, pixels within the baseline's own run-to-run noise (0 to
  0.007% over 8/255, the entry view and the far views bit-identical). Two corrections to the author: the claimed drop in the
  load's peak live heap (257 to 201 MB) did not hold under a second sampler, and the far ring's 48 tiles, staged just after
  uploadRing's own flush, set off one extra whole-scene render in the towns loop; a run of one mesh's tiles now counts once
  toward flushUploads' dozen. Seams: where two flat triangles overlap exactly, the later one wins, and tiling changes which;
  nothing showed with the real materials at 104 seam spots. The draw calls' cost on a real iPhone is unmeasured: build 5's
  perf beacons against build 4's will say.
- The merge of r167-cull and r167-tiles into main: devlog entries side by side, and one copy of the drain both parts added
  after the first frame (whatever was staged after the last flush, the trees, the tie runs and the late tiles, culls from the
  second frame). The merged page loads with no failed step in the pane: 202 tiles, 31 of 68 tree meshes and 10 of 41 tie runs
  drawn over Center City looking west, the pins' async read issued and landed on WebGL 2. 360 tests.
- The merged page against build 4's (measure.mjs, phone emulation 740 x 360 at 1.25): triangles after the look round
  10,037,853 to 7,692,802 (-23%), GPU after the first frames 877 to 870 MB and after the look 892 to 885, padded copies 0 in
  both, live heap at ready 115 to 116 MB, the load's peak live heap 256 to 257 (unchanged, as the verifier found), no failed
  step. Build 5 carries it to TestFlight.

## Round 168 (part) — the Graphics choice and a fairer crash rule (Sep 29)

Mike approved a plan to up the visuals and the performance on his iPhone (the TestFlight app). This part is the choice, its
storage, the city's tier it sets and the crash rule; the frame rate and the resolution ladder are another part of the round,
which hooks into it.

- The choice: a Graphics strip at the top of the Layers panel, under the panel note (quality/ux.md's placement): Smoother,
  Auto (the middle, and the default), Sharper, a radiogroup on the old mode bar's `.seg` in the panels' language (limestone
  lines, the chosen word in bronze, 44 px targets), the arrow keys moving the pick with wrap, Home and End, and never flying
  (the window's keydown flies on an arrow, so the group stops them). One status line under it, `#gfxNote`: "Smoother: a
  lighter city and a faster frame rate.", "Auto: sharp when this device can keep up.", "Sharper: the full city at the highest
  resolution, a steadier 30 frames a second." (on a computer "a softer picture and a faster frame rate" and "the highest
  resolution this screen allows"), then one of "The lighter city loads the next time Philly3D opens." / "The whole city
  loads the next time Philly3D opens." with a Reload Now button when the pick changes the tier, "Using a lighter city after a
  crash. Sharper brings the full city back." under Auto on a crash tier, "Sharper ran out of memory, so Graphics are back on
  Auto." and "Using the lightest city after a crash." The how-to's Layers card has a Graphics row on both copies.
- Storage and the API: localStorage `philly3d.gfx` as `{ pick, t }`, never in `philly3d.prefs` or a link (the site's Copy
  Link drops a `?gfx=`), and Reset Layers leaves it alone; `?gfx=smoother|auto|sharper` pins it for a test and writes
  nothing. `GFX` (`pick`, `pinned`, `hooks`), `gfxSet(pick)` and `gfxTierFor(pick)` are defined in the boot block before the
  tier and the resolution ladder, so both can read them; `gfxSet` saves, calls every hook with the new pick (one that throws
  does not stop the others) and refreshes the strip. Hooks are for what can change live; the tier waits for a launch.
- The tier on touch: Smoother builds tier 1 at least (a death still takes it to 2), Sharper always tier 0 and forgets the saved
  crash tiers when picked and at load, Auto the crash rules. One exception to "always", my call against the plan's letter:
  a death DURING Sharper's build hands the pick back to Auto (saved, the gate says "Philadelphia ran out of memory at Sharper
  last time. Tap to load a lighter city."), because that build would die at every launch behind the veil, where the Layers
  panel cannot be reached and the app has no address bar. A death while running keeps Sharper and the full city ("Tap to load
  the full city again."): that city stood long enough to change the pick. A `?gfx=` pin never falls back.
- The fairer crash rule (quality/tiers.md's Q1): a death mid-build is sticky for a fortnight as before; the `|| !bootPrev.lite`
  clause that made one death while running on the full city sticky is gone. A death while running makes the next load one
  tier lighter than the one that died and holds that tier (`philly3d.tiersoft`) only until a clean session: a session that
  stands 180 s after Enter in front writes `philly3d.tierok` (its own listener on the Enter button, a task after the click,
  so the gate's tap does not count), and the next load climbs one tier, 2 to 1 to the full city. A second death while running
  at the same tier within 14 days (`philly3d.tierrun`) is sticky. `?lite=0` forgets all of it. The beacon's `lr` gains r (the
  soft tier), u (a climb), p (the pick set the tier) and a (Sharper fell back to Auto).
- Build 6's first load forgets the old rules' tier and fortnight flag once (`philly3d.tierv` 2): Mike's phone has built the
  lighter city since build 3's one death while running on Sep 28, and would have until about Oct 12.
- Checked in headless Chrome (SwiftShader, phone emulation 740 x 360 at 1.25 with touch, and 1280 x 800): the strip renders
  in both (quality/gfx-strip.png, gfx-strip-smoother.png, gfx-strip-desk.png); a touch or a click on each word moves the
  bronze, `aria-checked` and the tab stop, rewrites the note and `philly3d.gfx`; the arrows went Sharper to Smoother to
  Sharper, Home to Smoother, Down to Auto, focus following, no fly key held and the eye moved 0 m; a pushed hook saw every
  change in order; Reset Layers left the pick and its time as they were; on the phone, Smoother from the full city showed
  Reload Now, and the reload built tier 1 (lr p), while the computer never shows it. Ten crumb situations loaded as expected
  (none: 0; mid-build: 1, gated, sticky; running: 1, gated, soft; left at the gate: 1; Mike's locked phone: 0, migrated; a
  climb: 0, lr u; a second running death: 1, sticky; Sharper mid-build: 1 on Auto; Sharper running: 0, gated; Smoother: 1).
  End to end: a running death's load (tier 1, gated, soft), the gate's tap and the build, no mark at 170 s after Enter and
  the mark at 185 s, an ordinary leave, and the next launch built the full city (lr u, the soft tier and the mark gone).
- tests/test_gfx.py (13); tests/test_recovery.py's harness is shared and runs the new rules (the soft tier's climb, the
  second running death, the migration); tests/test_boot_lite.py follows. The privacy policy's storage list names the
  Graphics choice.

## Round 168 — the integration, and Mike's two calls (Sep 29)

- Merged into main: r168-gfx (the Graphics strip and the fairer crash rule, with the migration that frees Mike's phone from
  the Oct 12 lock), r168-vdepth (the far facades' vertex-stage log depth on phones: 16 to 24% off a Mac frame by day, 20 to 37%
  at night, sub-pixel speckle 1 to 5 km out the only change), r168-misc (the lamp glow's vertex depth, the pins' capture over
  the flats from 20 m up, incremental traffic order, the theme menu's middots), on top of the pacing commit. All merged without
  a conflict; test_glow_depth's global count of the vertex-depth switch now allows the far facades' one constant.
- Mike's answers to the two look-changing questions: "Turn them off" (moon shadows after dusk) and "Only buildings hide pins".
  A phone's key light stops casting once it is the moon's (the sun 3 degrees under), one recompile each way per session; the
  pins' capture leaves out every instanced mesh (trees, cars, tie runs, rooftop units), both the async and the synchronous read.
- The reviewers' loose ends: VDEPTH's warm-up restores culling only on meshes it unculled (a mesh still staged in pendingUpload
  is left to that list's drain), vdepthInit is guarded (a failure leaves fragment depth and a PERF.failed entry), and the
  flats comment records the rare flips toward showing an independent sweep still found (about 1 in 10,000 from 20 m up).
  Left as is: the capture-only raised-street mesh (0.73 MB) uploads with the first capture rather than behind the veil.

Round 168 build 6 check (Sep 29): an independent measure against build 5 (M2 Max, Metal, phone emulation, interleaved blocks)
found build 6 11 to 45% cheaper at every pose at the same ratio, Auto's 1.6 costing about what build 5 cost at 1.25, the pins'
capture drawing 41 to 47% fewer triangles, memory and load unchanged, 12 frames a second parked and 30 touched, Auto climbing to
1.6 within 3 s on a 3x screen; the only visible changes the moon's shadows at night and distant rooftop speckle. An integration
review found one HIGH: the moon-shadow toggle through castShadow recompiled every lit program (1.3 to 2 s at a dusk crossing on
the Mac, 85 to 126 programs kept). Now `moonShadowsOff` turns off r149's per-object receiveShadow uniform on every receiving mesh
once the key light is the moon's and restores it at sunrise: in the probe the dusk crossing took 140 ms over two frames with 9
new programs (the night-only materials build 5 also compiles there), back to day 26 ms, no new programs. The review's lesser
findings are fixed: a stall or the app's return resets the controller whatever the pace judges, the beacons' choice letter is
m / a / s, PERF.ring keeps only motion frames, a playing time-lapse counts as motion, and the display interval is measured afresh
after a Graphics change.

## Round 169 — no pin through a building (Sep 29)

Mike, from the TestFlight app on his iPhone 18 Pro Max, with a screenshot (bus stops, markers, art and closures over Society
Hill): "I am still seeing pins through buildings when I first turn to look at them. They quickly disappear but I want to avoid
this at all costs."

Why it happened: a tip outside the depth image read as VISIBLE; a shown pin hid only after two captures agreed or PIN_HOLD
0.45 s had passed, then kept the state PIN_DWELL 0.3 s and faded over PIN_FADE 0.2 s; Round 143's 5 by 5 test kept a shown pin
while anything two image pixels round its tip was clear; and a phone drew an image every 10th drawn frame (three a second at
the paced 30), read back a frame or three later. A pin behind a building showed for up to a second as the eye turned, and a
pin whose own 3 by 3 neighbourhood was covered could show forever from a still eye (22 of them at one Society Hill eye).

What changed (app.js, the pin occlusion section and pinSceneDepth):
- Unknown is hidden. `pinOccAnswer` returns 1 clear, 0 covered, -1 unknown: no image, the tip outside it, behind its eye or
  past its reach, or the image drawn before the pin came into view. A pin coming into view (`pinZone`: in front, inside the
  capture's own 1.5 times the screen), new in its slot or back with its layer starts hidden (`arr`, its arrival frame) and
  shows only once an image drawn after its arrival says it is clear; a pin waiting asks for an image at the moving cadence.
- A covered answer hides at once, no fade out, no hold, no dwell (`pinOccStep`). Showing keeps the guard: one image after an
  unknown, two images (or PIN_HOLD of a still eye) and PIN_DWELL since the last covered answer after a covered one, then the
  0.2 s fade in. Round 143's 5 by 5 stay-visible test is gone: it could show a pin whose own 3 by 3 was covered, and against a
  gate that hides at once it would snap pins back without the guard. An edge pin now stays hidden instead of blinking.
- The gate: every instanced pin's vertex shader reads the latest images itself (`PIN_GATE`, `PIN_GATE_GLSL`): the packed
  depth through NEAREST targets, each image's own view and projection, the CPU's 3 by 3 rule and need exactly, and collapses
  the pin when its tip is covered, outside, past the reach or with no image yet; aPinVis still multiplies in. So a pin is hidden
  the frame an image that covers it is drawn. tests/pin_gate_gpu.html runs the production shader on the GPU against the CPU's
  answers: 700 of 700 tips agree in each of four set-ups (one image, one reaching 900 m, a near image with an older complete
  one, the complete one alone), and every pin is collapsed with no image yet (headless Chrome, Metal, M2 Max).
- The cadence: drawing an image (the gate reads it at once) is apart from reading it back (the CPU's state, the taps, the
  placards). While the eye moves or turns an image every drawn frame on a computer and every 2nd on a phone
  (`PIN_OCC_MOVE_EVERY`), and at once whenever the newest no longer holds the screen widened 1.25 times (`pinOccCovers`); a
  still eye keeps the old cadence. Two targets per kind take turns and an image is never drawn into the one a read is in
  flight from; one read in flight, of the newest image, at most every 4th frame on a phone and 2nd on a computer
  (`PIN_OCC_READ_EVERY`): a read's landing (getBufferSubData) is a synchronous call that waits while the GPU process catches
  up, 4 to 5 ms a landing in headless Chrome, 2.0 ms a frame when it landed every other frame, 0.7 at every 4th.
- The reach, to keep an image every 2nd frame cheap on a phone: an image goes only as far as the farthest tip in view needs
  (10% and 50 m on, never under PIN_REACH_MIN 300 m), and its frustum's far plane culls the city beyond. The ground pins all
  stand within the half mile: an image of them draws 1.4 to 2.0 M triangles and 0.55 to 0.74 ms of the M2's GPU against the
  3.4 to 5.9 M and 1.1 to 1.7 ms of one to the camera's far plane (four places, phone-sized). A flight, a ship or a placard in
  view would take every image out to it (the flights draw anywhere in the city box), so there are two kinds: the complete image
  reaches every tip, and while a tip past PIN_NEAR (900 m) stands in view a phone draws it only every 10th frame while moving
  (`PIN_OCC_FULL_EVERY`) and a near image (945 m, every ground pin) in the frames between. A tip past the near image's reach
  reads each of its 3 by 3 samples through both (`occImgBoth`): clear when nothing within the near reach stands in it and the
  complete image, read along the same ray at the tip's depth, lies behind the tip in all four of its pixels round the ray.
- The placards (concert placards, score bubbles) have no gate: `pinBlocked` keeps the same state per tip (`PIN_TIPS`, by
  where it stands, so a feed's new records carry it over), and once the eye has moved or turned since the image it reads was
  drawn, `pinOccTipAnswer` carries back the nine samples an image drawn now would take (exact for a turn) and calls the tip
  clear only when every image pixel is clear along the segment a nearer building could have slid across since (the eye's move
  in the image's frame over the nearest depth round the tip); otherwise covered, so a placard at a narrow gap does not blink.
- `__dbg.pinOcc()` counts images by kind and cause, `__dbg.pinGate()` names the images the gate reads, `__dbg.PIN_OCC` for
  knobs. The building tap and the Round 168 capture rules (only buildings, the flats from 20 m up) are as they were.

Measured (headless Chrome on the M2 Max's GPU through ANGLE Metal, phone emulation 740 x 360 at 1.25 with touch, the page's
own frames at 30 a second of real time with a two-frame swap-chain backlog; every static pin layer on, bus stops and libraries
included, six concert and four game fixtures for placards; a ground truth at every frame's exact camera by the page's own
capture rule, only buildings; `pin_through.js` in the capture skill):
- Through a building (a pin shown with its tip covered), twelve scripted runs over Society Hill, Center City and the Delaware
  waterfront (turns at 45, 90 and 180 degrees a second from 25 to 60 m up; flights at 10, 30 and 80 m/s, 6,464 frames): the
  instanced pins 37,246 pin-frames in 5,202 frames before, 423 in 358 frames after (98.9% fewer), 67 to 198 distinct pins a
  run before, 0 to 63 after, each for a frame; the placards 505 before, 7 after. Every one of the 423 but two falls on a
  frame when a phone draws no image (the gate reads the image of the frame before, its pixel grid a turn or a move away: a tip
  within about a pixel of a building's edge); the two are far tips read through the older complete image.
- On a computer (1280 x 720, 60 a second, an image every frame), five runs (turns at 90 degrees a second over Society Hill
  and Center City, flights at 30 and 80 m/s, 2,582 frames): 12,135 pin-frames in 1,964 frames and 436 placard-frames
  before, 0 and 0 after.
- How long a pin that comes into clear view takes to appear (displayed past half its fade), on the phone: from out of view,
  median 0 to 167 ms and 90th percentile 67 to 267 ms by run; from behind a building (the guard), median 33 to 433 ms and 90th
  percentile 67 to 533 ms. Before, 0: everything showed at once, through buildings included. Of the pin-frames the truth calls
  clear, 58 to 86% are shown after against 75 to 100% before. The difference is mostly pins at a roof line that the images
  call covered and clear by turns, held by the guard (of such hidden frames on a turn and a flight, the truth itself had called
  the pin covered within the ten frames before in 87 to 90%), then pins waiting for an image after coming into view, and the
  fade in.
- GPU (the profiler's method: EXT_disjoint_timer_query_webgl2 round each frame, a one-pixel readPixels to settle the queue):
  an image costs the M2 at phone size 1.1 to 1.7 ms and 3.4 to 5.9 M triangles to the camera's far plane, 0.8 to 1.2 ms to 3
  km, 0.55 to 0.74 ms and 1.4 to 2.0 M triangles to 945 m. While moving a phone drew one every 10th frame before (0.11 to 0.17
  ms and 0.34 to 0.59 M triangles a frame on average) and one every 2nd after (0.28 to 0.37 ms and 0.7 to 1.0 M; with a far tip
  in view, four near to one complete, 0.33 to 0.47 ms and 0.9 to 1.4 M), against a frame of 6 to 9 M triangles. The frame's GPU
  time along four scripted paths (a turn, flights at 30 and 80 m/s) averaged 17.3 ms before and 17.3 after without the event
  fixtures, 17.4 and 17.4 with them: the difference is inside the runs' noise of about half a millisecond. Still, nothing is
  drawn after the image the eye stopped on, as before, and the gate's texture reads (9 to 36 a pin vertex, a few hundred pins)
  are too small to time.
- CPU (the page's frame, M2): 4.4 to 5.3 ms before, 4.5 to 5.4 after.
- Memory: 871.4 MB of WebGL buffers, textures and renderbuffers after the runs against 870.8 before (four targets of 240 x
  117 and their depth where there was one, +0.64 MB), `__gpu.mis` 0 in both, no new vertex stream; the live heap after a GC 128
  MB after, 146 before (a second 112 KB image buffer).

What is not zero, and why:
- A phone draws an image every 2nd frame while moving, so on the frames between the gate reads an image one frame old: a tip
  within about a pixel of an edge can read clear there and covered from the exact camera, for that one frame (0 to 105
  pin-frames a run, 423 in all). `PIN_OCC_MOVE_EVERY = 1` on a phone makes it zero, for a near image every frame (1.4 to 2.0 M
  triangles, 0.55 to 0.74 ms of the M2 at phone size, and a phone is geometry-bound).
- A far tip (a flight, a ship, a placard) read through the near image and a complete one up to ten frames older: what stands
  past 945 m shifts up to a pixel in that time; 2 pin-frames in all.
- The placards have no gate and read an image a frame or more old; the motion test covers what a move or a turn can slide
  over them, but a building's corner can still cut between four pixel centres: 7 placard-frames in 3,158 shown. The test hides
  more placards while the eye moves (3,158 shown against 8,505 before) and brings them back once it stops.

Tests: tests/test_pin_fade.py (the state and the cadence under Node against scripted images, 13), tests/test_pin_gate.py (the
answers against synthetic images and the gate's text, 4), tests/test_cull.py's PinAsync rewritten for drawing apart from
reading (9), test_occ_flats and test_pace follow the one capture call; tests/pin_gate_gpu.html (new) and
tests/pin_readback_gpu.html (a read in flight while the next image is drawn) pass on the GPU.

### Round 169, the review (Sep 29)

An independent check of the commit above (its own counter: headless Chrome on the M2's GPU through Metal, phone-sized, the
page's own frames, every pin layer and the event fixtures on, a ground truth at every drawn frame's exact camera, eight
scripted scenarios of turns, holds and flights) found the through-building problem almost solved and two faults, and a third
came out of checking the taps:

- The stop gap. A phone draws an image every 2nd frame while the eye moves, so the eye stops on a frame that drew none as
  often as not, and the still cadence then waited 10 frames, and only for a change over 30 cm or 0.2 degrees, before drawing
  the pose the eye rests at: the gate read the image of the step before, and a pin fading in showed through a building's edge
  for up to 9 frames (0.3 s), the thing Mike described. Our reruns found a 49-frame one: a 10 m/s flight's last step (16 cm)
  was under the 30 cm, so no image came for the whole hold. Now `pinOccDue` draws one image the first still frame the eye
  stands anywhere but where the newest image was drawn (the moving test's own centimetre and 1e-9): one image a stop.
- Blinks, a regression. The half-mile reconcile writes a layer's slots afresh in a new order every 900 ms or 220 m of a flight,
  and a slot whose tip moved over 30 m was a new arrival: hidden until an image drawn after it said clear, then the fade in.
  About 300 blinks per eight scenarios on a phone, up to twenty pins at once every 0.8 s of a flight, 153 on a computer, none
  in Round 168: Round 138's complaint back. Now a new slot first looks for its pin among the frame before's tips (`pinOccCarry`,
  the nearest within `PIN_CARRY` 30 m, the distance that makes a slot new) and carries its state; only a pin that was nowhere
  near arrives. The gate still hides a carried pin the frame an image covers it.
- Taps. While the eye moves the gate reads images a few frames newer than the CPU's, so a pin could stand at half its fade or
  more while the gate hid it, and `pickPinHit` took the tap: synthetic taps the frame the page drew, over four places while
  turning, opened the hidden pin's own card 290 times in 290. Now `pinGateShows` reads the gate's images back at the tap
  (synchronously, once each) and asks what the gate asks. And the ray test for whatever else a tap finds (a marker's post, a
  plinth, a bus, a dock, a tent, a train, a tree: `pickOccluded`) knows only the core's buildings, so a tap on a Center City
  building over a hidden marker opened the marker's card, still or moving, in Round 168 too; `pinGateCovers` now refuses a
  point those images put behind a building, while the newest image is the eye's own (drawn this frame or the one before, or
  the eye has not moved since: with no pin in view no image is drawn, and an old one says nothing of where the eye is). After:
  no tap opens the hidden pin's card, and 20 of 366 open any card, each of something standing clear near the tap point (a
  tree's crown, another marker's post); still, the reviewer's taps give the pin's card on a shown pin and the property card on
  a hidden one or a building (Round 168 and the commit above gave a hidden Center City marker's card through its building).

Numbers, the reviewer's counter and scenarios (the clock pinned to Sep 26 at 11:00, every layer on; a phone 740 x 360 at 1.25
with touch, 25 to 28 frames a second under the counter). Pin-frames shown through a building by the design truth:

| Scenario (scene x, z; eye height) | Round 168 | the commit above (two runs) | now (three runs) |
|---|---|---|---|
| SH, Society Hill (150, 420), 110 m | 4,161 | 91 / 66 | 82 / 72 / 91 |
| CC, Center City (-1250, -650), 140 m | 8,801 | 17 / 25 | 28 / 23 / 24 |
| DW, the Delaware (420, -350), 35 m | 8,585 | 81 / 42 | 55 / 44 / 55 |
| OC (-200, -150), 50 m | 9,838 | 36 / 54 | 39 / 40 / 30 |
| FT (600, -1700), 70 m | 1,908 | 36 / 28 | 41 / 28 / 36 |
| SP, South Philly (-1500, 3800), 90 m | 16 | 2 / 1 | 1 / 1 / 3 |
| OC street, 20 m/s at 8 m | 9,366 | 4 / 2 | 3 / 3 / 0 |
| OC walk, 1.5 m/s at 5 m | 10,440 | 0 / 0 | 0 / 2 / 0 |
| Total | 53,115 | 267 / 218 | 249 / 213 / 239 |

- Every one is a single frame. Of 683 events (a pin through a building on a frame; pins standing at one spot count once), 678
  fall on a frame a phone draws no image (the gate reads the image of the frame before: a tip within about a pixel of a
  building's edge), 3 are far tips read through the older complete image, 2 fall on a fresh image (the packed depth's
  precision at an edge). No event lasts two frames in three runs (the counter's 2 and 3 frame events are pins at one spot
  counted each on one frame). The placards: 0. A computer, five scenarios twice: 0 and 0 (18,741 in Round 168).
- Blinks (a shown pin hidden while the truth calls it clear, then shown again): 301 and 293 before (272 and 274 of them slot
  changes), 49, 26 and 28 now, none a slot change. The rest are far flights, 5 to 9 km off, that the two-image rule (all four
  of the complete image's pixels round a carried ray) hides at a skyline during a turn for a median 1 or 2 frames: the
  conservative side, never through a building. A computer: 153 before (all slot changes), 0 and 1 now.
- Appearing (a phone, to half the fade): from off screen a median 0 to 115 ms and a 90th percentile 118 to 215 ms by scenario
  (before: 0 to 125 and 144 to 186); from behind a building a median 0 to 482 ms, 90th percentile up to 530 (before: 194 to
  270, up to 680). Of the pin-frames the truth calls clear, 0.92 to 0.99 are shown (before 0.88 to 0.98; Round 168 0.95 to 1.0).
- GPU per frame, four phone paths, frames driven one at a time behind a timer query and a one-pixel sync, two runs each
  interleaved: moving 30.0 / 28.1 ms in Round 168, 29.9 / 29.0 before, 29.2 / 29.4 now; still 30.5 / 28.4, 30.5 / 29.1,
  29.0 / 30.0; identical runs differ by 2 to 3 ms. The page's CPU while moving 5.1 / 5.1, 6.3 / 5.8, 6.2 / 6.1 ms (the commit
  above's reads, as the reviewer found); still 4.6 / 4.5, 4.9 / 4.7, 5.1 / 4.6. WebGL memory 870.6, 871.2 and 871.2 MB,
  `__gpu.mis` empty in all.

Not done: `PIN_OCC_MOVE_EVERY = 1` on a phone (an image every frame while moving) would take away nearly all the single frames
(the reviewer: 2 pin-frames left, both the fresh-image precision case) for about 1.9 ms more GPU a moving frame on the M2 on
average (-1.6 to +5.3, noisy), on a phone that is already geometry-bound. The frames it would remove are tips within about one
image pixel of an edge, the slack the 3 by 3 rule allows every frame anyway (the reviewer: a third of shown pin-frames have a tip
up to about 7 CSS px inside a building's outline, in Round 168 as now).

Tests: test_pin_fade.py (the stop's image, a 16 cm last step included; a pin that changes slots keeps its state), test_pin_gate.py
(a tap asks the gate's images; `pinGateCovers` answers only on the eye's own image), test_pins.py (a pin the gate hides never
takes the tap). 435 tests.

## Round 169 (part) — the Met stands at Broad and Poplar, and build 7 (Sep 29)

- Mike: "Fix the location of the Met on north broad. The map location when searching is wrong. The met is at the south west
  corner of broad and poplar." The citywide label list (Round 44), which is also what search finds, had 'The Met Philadelphia'
  at 39.96851, -75.15852, 211 m south of the building; OSM way 335078446 (The Met, addr:housename Metropolitan Opera House)
  centres at 39.96983, -75.16030, scene (-1326.8, -2693.7). Checking the whole list against landmarks.json's point for each
  name found seven more: the Divine Lorraine 347 m north of the hotel (beside the Met), the Mann Center 563 m, Freedom
  Mortgage Pavilion 697 m, Chestnut Hill College 2.2 km, Frankford Arsenal 825 m, Christ Church 80 m, Valley Green Inn 190 m.
  Each is now its OSM outline centroid. The campuses, the Navy Yard, the Italian Market, Laurel Hill and the airport are
  areas and keep their hand-set points.
- VENUE_NAMED pins a Met concert (`/\bthe met\b|metropolitan opera/i`) and a Freedom Mortgage Pavilion one to their buildings:
  Ticketmaster's point for the Met (39.9701, -75.1591) is across Broad Street, 106 m off.
- tests/test_landmark_labels.py: every label within 90 m of the basemap's point for its name (400 m for the listed areas),
  the Met on its outline and south-west of the corner, the Divine Lorraine on its rebuild, the Met regex matching the Met and
  not the Metropolitan Bakery.
- Merged r169-pins (the pins never through a building, with the review's fixes) and shipped both as build 7. 438 tests.

## Round 170 — the app keeps the person's choices natively (Oct 3)

- Mike: "use Capacitor Preferences for the app builds." iOS may clear a web view's data when the phone runs short of space,
  and the layers (`philly3d.prefs`), the Graphics pick (`philly3d.gfx`), the dismissed events (`philly3d.hiddenEvents`) and
  the guide's seen mark (`philly3d.guide`) lived only in localStorage. `@capacitor/preferences` 8.0.1 is in `app/` (UserDefaults
  on iOS, SharedPreferences on Android), and the page reaches it as `Capacitor.Plugins.Preferences`, as it does geolocation.
- localStorage stays the working copy every read takes, synchronously; inside the app those four keys write through
  `keepSet` / `keepRemove` to both. Each launch reconciles once: a key the native store holds that localStorage lost is
  written back, with one reload a tab (`sessionStorage philly3d.keptback`) while the city is still building (`PERF.ready`)
  when it shapes the load (not the guide, read only at the first Enter); a key localStorage holds differently is copied over
  (the first launch of this build). Writes before the reconcile reach localStorage only and are copied after, so a default
  written into a cleared web view never overwrites the saved value. The reload clears the breadcrumb first, so it is no
  death. The crash tiers and the breadcrumb stay in localStorage alone (written every build step, synchronously). The block
  stands before the Graphics choice: gfxSave runs during the boot after a death in Sharper's build, and KEPT in its TDZ
  there made the first draft's gfxSave throw into its own catch and save nothing (the boot harness caught it).
- iOS privacy manifest: UserDefaults is a required-reason API, declared with CA92.1 (the plugin ships no manifest of its own).
- tests/test_kept.py (10 tests, the boot block under Node with a fake async plugin); test_recovery's harness takes
  `IN_APP` and `window.Capacitor` and starts at the new block. 448 tests.
- In the iOS Simulator (iPhone 17, iOS 27): the first launch copied the guide mark into UserDefaults; with prefs and a
  Smoother pick seeded natively and `Library/WebKit` deleted, the relaunch restored all three into localStorage, reloaded
  once, built tier 1 with `fails: 0`, and stood with the landmark labels on. The simulator build tool's xcodebuild hung
  reading the CloudStorage checkout; xcodebuild from the shell with a scratch `-derivedDataPath` built it.
- Build 8 (1.0 (8), `npm run bump`, the page byte for byte in the archive, the Preferences plugin linked, the manifest's
  UserDefaults entry in the bundle) archived and uploaded through app/ios/UploadOptions.plist: "Upload succeeded".

## Round 171 — the loading screen is just Philadelphia (Oct 5)

- Mike: "Remove the Data in motion and a living city from the loading screen." The veil's kicker ("Philly3D / A Living
  City") and the heading's second line ("Data In Motion") are gone; the heading reads Philadelphia under the mark, with the
  facts, the button and the progress below as before. Their now-unused rules went from style.css (the veil's kicker in all
  four places, `#veil h2 span` in both). The brand's tag at the top left ("A city in motion") and the page title stay.
  Checked in the pane at 800x600 and at a landscape phone's 844x390. 448 tests.

## Round 172 — a phone flies faster the higher it is (Oct 5)

- Mike, from the app: "Movement in the app is very sluggish." Two things in the evidence. The phone perf beacons (Sep 23 to
  Oct 1, app and site) run 29 to 79 ms a frame median at 4.0 to 10.7 M triangles and 200 to 524 calls, with the paced app's
  JS only 5 to 9 ms of it (`jp`): the phones are held by the GPU, which is a round of its own. And the controls: a desktop
  raises `fly.speed` with the wheel (10 to 500 m/s), a phone has no wheel, so it flew at 90 m/s (216 at full stick) at every
  height, and from 500 m up the city crawled past.
- On touch `applyFly` now scales the speed with the height over the ground (`flyAltK`): unchanged up to `FLY_ALT_REF` 80 m,
  then in proportion, capped at `FLY_ALT_MAX` 6 times from 480 m. Measured in the pane at a phone's size: 90 m/s at 30 m,
  132 at 120, 331 at 300, 540 at 900 (before the stick's throttle). The desktop is unchanged. 448 tests.
- Build 9 (1.0 (9), `npm run bump`, the page byte for byte in the archive: Rounds 171 and 172) uploaded through
  app/ios/UploadOptions.plist: "Upload succeeded".

## Round 173 — every ship's card links to that ship (Oct 12)

- Mike: "The marine traffic links are not tracking individual ships. All ships go to the same URL." The cards built a
  different href for each MMSI, but MarineTraffic now redirects every `/en/ais/details/ships/mmsi:N` to one world map
  (`/en/ais/home/centerx:-12.0/centery:25.0/zoom:4`, followed in the pane), its search URL 404s, and its ship pages want
  its own ship id, which AIS does not carry. `shipLink` now opens VesselFinder's `/vessels/details/<MMSI>`, which takes the
  MMSI itself: the Freedom's 368417620 opened "MV FREEDOM", position two minutes old. The ships' cards and the ferry's
  share it. `tests/test_ship_link.py` keeps marinetraffic.com out of the page. 451 tests.

## Round 174 — Society Hill's roofs match the city round it (Oct 12)

- Mike, with a screenshot over Old City looking south: "there appears to be a distinct cutoff where there is no roof
  hardware on buildings in society hill", then "those buildings all appear to stand out from the rest color wise". Both
  are the core's edge (`CORE_EXT`, x -640 to 770, z -520 to 850). Round 150's hardware is laid from `ROOF_KIT` notes, and
  only the packed tiers' loops called `roofClutter`; 'Raising 2,800 buildings' never did, so the condensers, hatches and
  vents stopped at Market Street. The core's flat roofs now take the tiers' clutter and note (in world space after the
  lift, the clutter's tier colours pulled back by `FACADE_GAIN / CORE_FACADE_GAIN`): 5,001 pieces laid with the eye over
  Society Hill.
- The colour: measured with only the two fabric materials drawn (the fabric meshes and the lights on a spare layer, the
  camera on it alone), the walls matched across the edge (116 against 117 displayed, saturation 0.18 both) but the roofs
  did not: 101 to 110 against 86 to 88, saturation 0.13 to 0.15 against 0.17 to 0.21, straight down over the west and north
  edges. Round 52 coda gave the core its own gains (then 0.42 / 0.28, Round 53's 0.52 / 0.34) against a dark wall gap; the
  tiers' colours were reworked many times since and the roof gain was left high. Both tiers' roofs are `ROOF_PAL` entries,
  so the core's roofs now render at the tiers' own gain and saturation (`CORE_ROOF_GAIN = ROOF_GAIN`, `CORE_ROOF_SAT` 1.2
  through a roof-only term in `facadeHook`): 87 / 88 at the west edge, 81 / 86 at the north. The south edge's 91 / 73 is
  Queen Village's darker sampled roofs, not the tiers (an empirical 0.20 and 1.45 matched the west and north closer and
  left the three edges further apart on average, +8 against +4). Before and after at both edges in the pane.
  `tests/test_core_roofs.py`. 453 tests.

## Round 175 — house fronts on two blocks, the facade prototype (Oct 12)

- Mike, after a robotaxi game on a real San Francisco (mindblown.ai's Teleoperator: about 130 whole-house front images
  in seven sets, each with its window, bay and cornice map): "I would love for the buildings to be much more varied",
  then "prototype both blocks with AI-generated fronts", then "deploy the two blocks so I can see them on my phone".
  Measured first: 71% of the outer districts' 112,000 buildings draw two facade styles (Victorian row 38%, Georgian
  row 33%), and 93% of the far ring's 180,000 five row styles.
- `fetch_fronts.py` asks OpenAI's image API (`gpt-image-2`, 768x1280, high; the key only in
  `~/.config/philly3d/openai.env`) for sixteen straight-on fronts, party wall to party wall and sidewalk to cornice:
  eight Society Hill (`federal`: Flemish bond, fanlights, marble steps, shutters, a Greek Revival, an Italianate, a 1960s
  infill) and eight South Philadelphia (`southrow`: brick, formstone, a bay front, painted and stucco fronts, awnings).
  `bake_fronts.py` cuts each set into a 2048 atlas of 512x1024 cells with an 8 px gutter, a half-size mask (r glass,
  g a number per window, b the door) and each cell's cornice colour. Its window finder took five passes on the real
  fronts: dark NEUTRAL glass at 384x640 (a dark red brick reads as dark as a pane by brightness alone, a sky-lit pane is
  0.16 to 0.2 against a 0.35 brick), a 1 px close (a muntin is 2 px, the frame between a shutter and its sash 5), a
  narrow box against a sash is a shutter but a narrow modern window standing clear is not, green is never glass, deep
  shade on brick stays red, the door is the tallest dark opening in the lowest third and taller than the usual opening.
- The page: the core's and the outer districts' loops hand every house near a run (`RUNS`: Spruce Street's 300 block,
  Wilder Street's 900 block, from the street labels) to `frontNote`; 'Hanging the house fronts' finds each one's street
  wall (`frontEdge`: within 15 degrees of the run, 2.5 to 16 m off it, facing it), lays a quad 5 cm proud of it from the
  ground to the wall top cut into round(width / front width) cells, deals the cells so neighbours never match, and
  projects each cell's cornice (34 cm) and a stoop under a found door (`frontBox`). A wall two or more fronts wide takes
  them only at a row strip's depth (18 m: Wilder Street's corner loft had taken six; a 22 m limit on every house cost
  Spruce Street fourteen of its deep rows). Glass is glossy by day; after dark four houses in ten light about two windows
  in three, only the dark glass inside the mask glowing, and the street lamps wash the fronts (`lampLightPatch`). A
  phone takes the atlases at half size through a canvas freed on upload. 77 fronts (35 and 42), fronts.json 1.43 MB.
  Before and after at street level and from 30 m on both blocks, and on the phone path at 740x360.
  `tests/test_fronts.py`. 460 tests.

## Round 176 — every gable end faces out of its house (Oct 12)

- Mike, with a screenshot over Spruce Street's 300 block: "The roofs look broken. they are missing a piece on the side so
  you cant see into them". Not the fronts (the deployed build before them drew the same). `quadGable` turns each end
  triangle (A, B, R) so its normal points away from the quad's centre, but read the horizontal normal as
  (Bz - Az, -(Bx - Ax)) where (B - A) x (R - A) gives (-(Bz - Az), Bx - Ax): every gable end was wound into its house and
  culled by the front-side fabric materials, so wherever a pitched row ended, met a lower neighbour or stood alone, you
  looked into the roof. One sign, and it was citywide: the core, the outer districts' and far ring's pitched rows through
  `raisePitched`, and the researched gables all use `quadGable` (since the realism pass, 8770d0a). Before and after over the
  row: the corner house's end went from a see-through tan triangle to its brick gable. `tests/test_gable_ends.py` runs the
  page's own `quadGable` under node on a quad in four rotations, both windings and three ridge directions (it fails on
  the old line). 461 tests.

## Round 177 — 3D awnings, East Passyunk's shopfronts and clad towers (Oct 12)

- Mike: "The awnings being drawn on in 2d is not great. I want to add more depth to this. I would also like to generate
  storefronts and regenerate the skyscrapers to look more realistic also".
- Awnings: every prompt now says no awnings and no canopies (`FRAME`), and the five South Philadelphia fronts that had one
  were made again without (the old ones kept in `fronts_raw/southrow-painted-awnings/`). The bake records each cell's
  ground-floor span (`gf`: the openings centred in the lowest 40%), and `frontAwning` builds one over it for a set's share
  of its houses (`awn`: none in Society Hill, 45% on the South Philadelphia rows, 60% of the shops): a canopy sloping 0.55
  to 0.7 m down to 0.95 to 1.35 m out, a valance (scalloped aluminium on the rows, a straight band on the shops), closed
  sides, stripes from the shader by metres along the wall (`AWNING_KINDS`), double sided, casting shadows on a computer.
- Shops: eight East Passyunk storefronts (a corner bar, a bakery, a cafe, a cast-iron front, a 1960s aluminium front, a
  boutique, a corner store with its gate half up, a restaurant's arched doors), with blank signboards, on a third run
  (`RUNS`: the 1500 and 1600 blocks, from the avenue's labels at 313 degrees). The mask marks the display glass (b 128),
  lit in nine shops in ten at a warm display light; only near-neutral pixels inside a box glow (a shop's stained wood and
  navy boards stay dark). 47 shopfronts laid.
- Towers: six square facade tiles (glass with silver mullions and grey spandrels, dark bronze banded glass, a white
  precast grid, Art Deco limestone piers with cast spandrels, tan brick with punched windows, a concrete balcony slab),
  each cropped by the bake to whole repeats of its own bay and floor (autocorrelation), the edges cross-faded, sized in
  metres. Every tower of 35 m and up in both loops, but the researched curtain walls (styles 24 to 29), hands its walls
  to `towerSkinNote` with its kind (`towers.json`'s facade, else its drawn style); 'Cladding the towers' lays the tile 12
  cm proud of every wall from 5 m up (the lobby keeps its storefront), repeating in metres from an offset of its own,
  tinted by the tower's own colour (half on glass, two fifths on masonry: one limestone tile on every masonry tower turned
  the skyline beige on the first pass). After dark a floor lights by suites of three to six bays, about one in three
  (a bay at a time read as salt and pepper on the first pass). 844 tower sections in six meshes, 1.5 s to build.
- A phone takes the tiles at half size like the fronts. fronts.json 2.64 MB. Today against new at six identical poses
  (East Passyunk at street level, from above and at night; Center City at 160 m, low among the towers and at night).
  The rooftop boxes floating over East Passyunk's corner and its flat grey shopfront panel are in today's build too.
  `tests/test_fronts.py` (tiles, awnings, the no-awning prompts, the cladding hooks). 465 tests.

## Round 178 — rooftop hardware stands only on its roof (Oct 12)

- Seen in Round 177's captures and in the build before it: condensers, a hatch and a vent hanging in the air beside a
  wedge-shaped corner building on East Passyunk Avenue (eye (-1370, 2.0, 1481.9) toward (-1351, 3.9, 1475)). Round 150's
  `ROOF_KIT` note kept only the roof's oriented box, and `roofKitLay` scatters units across up to 1.4 to 1.6 times its half
  length, so on a roof that is not its own box some stood beyond the roof at roof height; `roofClutter`'s baked boxes used
  the same box. It was not one building: measured over the whole city, only 36,714 of 187,752 noted roofs (20%) fill their
  box; 73,322 are a few cells short, 52,331 have a rear ell or similar (two thirds to five sixths of the box), and 25,000
  are half or less (wedges, Ls, courtyards).
- Each note now carries an occupancy mask of its box, 8 cells along the long axis by 6 across, in the lay's own frame
  (its perpendicular is (-uz, ux), the opposite of `obbAxis`'s): a cell is on the roof when its centre and the corners of
  its middle half are inside the footprint and outside its holes (the whole corners dropped every row's edge cells, 18%
  of the units). 48 bits in two floats, exact in a float32 (`ROOF_KIT_STRIDE` 10, from 8). Every unit and dish in the
  lay asks it (`roofKitOn`), the baked boxes are tested against the footprint itself, the core passes its courtyards, and
  a roof with no cell left takes no note (5 in the city). Near the eye over Society Hill the lay places 4,093 units where
  it placed 4,766: the 673 gone stood over yards, beside ells and off wedges. `__dbg.roofKit()` reports `partial`, `empty`,
  `hist` (roofs by cells on, in eighths) and `off`. Before and after at street level and from 45 m on East Passyunk, over
  Society Hill and straight down over two South Philadelphia blocks: the floating units gone, the roofs' own unchanged.
- `tests/test_roof_kit.py` (Round 150's file) gains the mask run under node on a rectangle, an L and a courtyard, and the
  gating of every placement. 468 tests.

## Round 179 — the trees look like their species, by the season (Oct 12)

- Mike: "Can you have Open AI create more realistic looking trees? The data for tree species already exists in the app.
  Can we make them look like their real life counterparts?" The PPR inventory carries 296 species over 150,887 trees, the
  top thirty 70% of them; Round 58's trees were faceted crowns in twelve species colours.
- `fetch_tree_art.py` asks OpenAI's image API for 18 looks (London planetree, red and sugar maple, Kwanzan cherry, Callery
  pear, honeylocust, northern red and pin oak, zelkova, ginkgo, Japanese tree lilac, redbud, crabapple, linden, sweetgum,
  white pine, elm, a generic broadleaf), each from the side (the whole tree, level, from far off) and from straight above
  (as an aerial map shows a crown), in summer, autumn and winter, and in bloom for the five that flower: 114 images on a
  transparent background. `gpt-image-2` refuses a transparent background on this account, so `gpt-image-1.5` at medium.
  The first top view drew single leaves the size of a hand; the prompt now asks for the crown as clumps seen from high
  up. The model fills the gaps between winter twigs with an opaque pale haze (50 to 75% of the covered pixels of 15 of the
  18): `bake_tree_art.py`'s `dehaze` keys the crown on darkness and spares the trunk's column (the planetree's bark is
  cream). The bake crops, fits, bleeds and firms each image into a square cell, records its framing, and maps every
  species onto a look (`LOOK_OF`); `tree_art.json` is 2.46 MB.
- The page draws a tree as one card (`TREE_ART_VERT`, `treeArtPatch`): standing on its trunk and turned about it to the
  eye while the view is low, leaning back to face the eye as the view steepens (pivoting up to the card's middle), its
  picture cross-dissolving from the side view to the top view between 0.55 and 0.82 of the way to straight down, its size
  from the tree's height to its crown's span. The first pass drew a side card and a top card and dithered between them,
  which read as speckled, see-through crowns from the air; and the card was first built after `beginnormal_vertex` read
  its variables, which left every tree black. In the shadow pass the eye is the sun (a low sun casts the side, a high one
  the crown; the depth shader has `beginnormal_vertex` only under displacement, so the pass is told, not sniffed). Cards
  are sized to the crowns as Round 58's shader drew them (1.21 times), or the city's canopy shrank by a fifth.
- Seasons follow the model's date per look (`TREE_CAL`, `treeSeasonOf`): leaf-out over April 10 to May 5, the colour over
  October from a look's own offset (red maples and honeylocusts first, oaks, ginkgos and pears last), leaf fall over
  November; cherries, pears, redbuds and crabapples in bloom late March to mid-April, the tree lilac in June. Each look's
  two current seasons sit in the atlases (`treeArtSeason`, a canvas a view, six cells a row, half size on a phone) and
  every tree turns on a day of its own within a change, so a block colours tree by tree. A clock change turns them on the
  next frame. `?trees=lowpoly` keeps Round 58's crowns.
- Cost: from the air over Washington Square the trees draw 0.2 M triangles a frame against 5.5 M (the whole frame 7.0 M
  against 12.4 M), and on a phone's view 85 k; draw calls a few fewer. Before and after at street level on Spruce Street,
  over Washington Square and straight down, and July, October, January, April and a night in October; the phone path at
  740x360. `tests/test_tree_art.py` (the data, the species mapping, the calendar under node, the wiring);
  `tests/test_cull.py` counts the cards' mesh in the fitted list. 472 tests.

## Rounds 180 to 183 — doors everywhere, house fronts citywide, more towers, a real lawn (Oct 12)

- Mike: "Have you worked in the new building styles yet? much of the app is still showing the old style where buildings
  have no doors and all look alike. Did you do anything with the skyscrapers?", then "Go for it. If you could also update
  the grass/ground textures that would be great".
- Round 180, doors: the facade shader drew a door every third bay (`step(2.5, mod(cell.x, 3.0))`) on the Georgian and
  postwar rows only, on brick only, and a rowhouse wall is two or three bays wide, so most houses had none and the
  Victorian rows (38% of the outer districts), the siding rows and the porch fronts never did. A wall of up to three bays
  now takes its door in an end bay chosen per wall (`doorBay`, a hash of the wall's length and base), a wider one keeps
  one every third bay, and every row style (0, 8, 9, 10, 11) takes one, painted or brick.
- Round 181, house fronts citywide: 48 more fronts from `gpt-image-2` in six sets (`victorian`, North Philadelphia and
  Fairmount; `porch`, West Philadelphia twins made without their porch; `airlite`, the Northeast's rows with garages;
  `newbuild`, Fishtown and Point Breeze; `stonetwin`, Germantown and Mount Airy; `siding`, Kensington), nine with Round
  175's three. Round 175's hand-placed runs are gone: every loop hands each house to `frontNote` with its OPA word, and
  `frontSetOf` picks its set (commercial a shopfront, frame siding, stone a stone twin, the last thirty years a new build,
  the 1920s to 1950s the Northeast's rows, a porch front a porch, else by height a Victorian or a two-storey row; the core
  Federal). Only ten floats a house are kept (its oriented box, ground, wall top, seed, set), because the streets that
  decide its front are not all indexed until the far ring is built and keeping 290,000 outlines that long would cost a
  phone its memory. Near the eye ('Fitting the house fronts', after the far ring) `frontSide` takes the box side whose
  probe finds a road running along it nearest (a long side 6 m worse, so a corner house keeps its front on the main
  street; under node in the tests: the north street wins though the side street is nearer), once a house, and
  `frontsLay` fills instanced meshes: a front a set, and shared cornices, stoops, awnings and porches (a deck, a roof on
  two posts and a rail, over the ground floor of the porch set), refilled as the rooftop hardware is (30 m or 1.5 s, the
  nearest cells first, 0.3 ms a lay); the fronts dissolve into the facade, dithered, over the radius's last fifth (380 m,
  240 on a phone). A set's atlas decodes and uploads the first time one of its houses is near; a phone takes it at half
  size and frees the canvas on upload. 254,674 houses noted (109,147 on a phone, which skips the far ring): 115,072
  two-storey rows, 47,166 Northeast rows, 37,538 Victorians, 15,167 porch twins, 14,387 new builds, 10,573 shopfronts,
  8,866 siding rows, 4,052 stone houses, 1,853 Federal rows. `__dbg.frontNear(x, z, set)`, `__dbg.frontsRadius(r)`.
- Round 182, towers: four more tiles (silver fins, a black grid, a 1920s brick office, glass balconies), two or more
  dealt per style and per researched facade (`TOWER_TILE_ALT`) so neighbouring towers of one era differ, and the
  cladding moved after the far ring and dresses its towers too: 1,181 tower walls against 844.
- Round 183, the ground: a mown lawn and a rougher verge from `gpt-image-2`, made to tile by `bake_ground_art.py` (a
  blend with a half-rolled copy across, then down: no seam in a 3 by 2 repeat), swapped in for the painted meadow tile
  by `loadGroundArt`, each toned to the painted tile's linear mean (its brightness matched, its colour pulled halfway
  to the olive) so the scene's calibrated balance holds; the verge comes through the lawn on an 83 m noise, more of it
  on bare ground. `?ground=painted` keeps the painted tile.
- Before and after: a North Philadelphia street (live, the drawn facades with doors, with the fronts), and the fronts at
  street level in South, North and West Philadelphia, Fishtown, Kensington, Germantown, the Northeast and on East
  Passyunk, and from 45 m; the phone path at 740x360. `tests/test_fronts.py` (the nine sets, the set choice and the street
  side under node, the wiring), `tests/test_doors_ground.py`; `tests/test_memory_cuts.py` follows the fronts' and the
  towers' textures to their new places. 477 tests.

## Round 184 — the generated art loads on demand; fifteen house types, 25 tower tiles, 28 tree looks, the streets (Oct 12)

- Mike: "I added another $100 to the chat gpt api so we can use that to model many more items", and, asked, chose to
  load the generated art separately from philly3d.com rather than inline it, with all four of more variety per type,
  more house types, storefronts and streets, and trees and towers.
- The page had reached 20.4 MB of gzip with the art inlined as data URLs, about 8 MB of it images. Now every generated
  image is a file under `3d-model/art/<kind>/` named by the first 10 hex of its sha256 (`art_files.py`: `write` and
  `prune`), and the manifests build.py still inlines (`fronts.json`, `tree_art.json`, `ground_art.json`) carry paths.
  The page loads a file the first time it needs it (`artImage`, one retry after 4 s, null when it cannot be had: a
  front set or a tower tile that does not load leaves the procedural facade standing, a tree image is asked again at
  the next season pass and its cell keeps what it held), and a phone takes the bake's half copy (`artSrc`), so it
  neither downloads nor decodes the full size and no longer halves the atlases through a canvas. A phone also lets a
  decoded `<img>` go once the GPU holds it (`freeTexOnUpload`). build.py refuses a manifest naming a missing file or
  still holding a data URL; `deploy_philly3d.sh` stages `art/` with 755 and 644 modes, rsyncs it BEFORE the page,
  never deletes on the box (a rolled-back page still finds its own art), checks every file landed and fetches one of
  each kind over https against its sha256; the app's `copy-web.mjs` copies it into `www/art`.
- Variety and types: `fetch_fronts.py` made 183 more fronts and tiles from `gpt-image-2`: sixteen fronts a set for the
  nine sets (eight each before), and six new sets with their own places (`FR_AREAS`, scene-frame boxes): `univcity`
  (University City's three-storey Victorian twins, made without their porch, which the page builds, now a set flag
  `porch` rather than the set's name), `chestnut` (Chestnut Hill's stone houses, up to 900 m2), `manayunk` (the narrow
  hillside rows), `loft` (an old factory or warehouse of three to seven floors anywhere, and any old commercial block of
  four floors and up in Old City, Callowhill and Northern Liberties), `mixeduse` (a shop under three floors of flats: a
  commercial building of 11 m and up in Center City, 13.5 m elsewhere) and `rittenhouse` (four-storey townhouses west
  of Broad). The atlas went from 512x1024 cells, 4 by 2, to 384x768, 4 by 4 (a phone's half 192x384). Fifteen sets at
  about 27 MB of GPU atlas each on a computer would add up over a long flight, so the least recently wanted are let go
  past `FR_KEEP` (eight, four on a phone; `frontSetDrop`), never one the current lay wants. The tower tiles went from
  ten kinds to 25 (gold glass, green glass, ribbon windows, brutalist, limestone, marble, terracotta, blue bands,
  unitized, hotel precast, red granite, white fins, dark brick, metal panel, grey grid), dealt among each style's and
  researched facade's alternates, written at 640 (a phone's 320) and fetched all at once (one kind at a time cost the
  build 4.3 s of round trips).
- Trees: ten more looks from `gpt-image-1.5` (magnolia, dogwood and serviceberry with their spring bloom, silver maple,
  Crimson King, American sycamore, river birch, willow, and spruce and holly evergreen), each ahead of the broader
  pattern it used to fall under in `LOOK_OF` (the dogwoods, magnolias and serviceberries were crabapples, the spruces,
  firs, hemlocks, hollies and yews pines), with `TREE_CAL` dates. The winter haze keying spared a near-white blot at the
  willow's foot (its curtain of twigs); the trunk column now spares bark only, saturation 0.18 and up, and keys a
  near-white grey there too. A season pass asks for every image it needs at once.
- Streets: three more ground textures from `gpt-image-2`, worn asphalt, concrete sidewalk slabs and a Society Hill
  herringbone brick walk. A regular pattern cannot take the lawn's half-roll blend (it doubles every joint across the
  band), so `bake_ground_art.py` crops those two to whole repeats found by autocorrelation (the herringbone 208 by 100 px,
  4 by 10 of them, 1.62 m a tile; the concrete one slab, 1.5 m) and cross-fades the edges over 16 px. `surfTexPatch`
  lays them on every paved surface that is not the bare ground, on the street grid's own axes (the fitted Front Street
  line), by the surface's own colour (reddish brick, dark asphalt, light grey concrete), as a ratio to the texture's
  mean so the calibrated colours hold, the asphalt as the mean of two tilings (6 m, and 9.7 m at 37 degrees) so no
  patch repeats, on up-facing faces only, gone past 0.7 m a pixel. `?streets=plain` keeps them off.
- Two fronts' windows went unfound (a loft and a mixed-use block whose panes carry a sky reflection, under half of each
  box dark): `find_openings` tries a front again at a fill of 0.38 when none passes at 0.55, so no other front changes.
  A third (`p11`, a dark-brick bar front) was remade in lighter brick. On fronts of four storeys and more the "lowest
  40%" rule for the ground floor took the second floor's windows too and hung the awnings at their sills; the band is
  now the lowest floor and a sixth by the set's height (`gf_line`).
- The page: 29.56 MB raw and 12.62 MB of gzip against 39.8 and 20.4; 489 art files, 18.2 MB, fetched as they are
  needed (a desktop session in South Philadelphia and Center City asked for about 140, a phone only half copies and
  masks: 125 halves of 135). `?dev=1` at street level: the southrow, Victorian, University City, Rittenhouse, loft,
  mixed-use, Manayunk and Chestnut Hill fronts, the herringbone walks and asphalt in Society Hill, 24 of the 25 tower
  kinds laid (1,181 walls), one front set let go past the cap; the phone path at 740x360. `tests/test_art_files.py`
  (every named file under its own hash, nothing unnamed in `art/`, a phone copy of each, the loaders, the build guard,
  the deploy order and modes, the app copy); `tests/test_fronts.py` (fifteen sets of sixteen, 25 tiles, the six sets'
  places under node), `tests/test_tree_art.py` (28 looks, the new species), `tests/test_doors_ground.py` (five ground
  textures, their metres), `tests/test_memory_cuts.py` (eleven `freeTexOnUpload` uses). 484 tests.
- Image API spend this round: 183 fronts and tiles and 3 street textures from `gpt-image-2` at high quality, 58 tree
  images from `gpt-image-1.5` at medium (the sidecars hold each one's tokens).
- Round 184 coda, the same evening (Mike, with a screenshot of a park: striped red and green boxes among the trees,
  "I am assuming they are trees that did not load properly"): the tree atlases were Round 179's, six cells a row on a
  canvas sized for 18 looks, and the 28 looks' cells 36 to 55 lay past its foot. The ten looks there (dogwood,
  serviceberry, silver maple, Crimson King, sycamore, river birch, willow, spruce, holly and the broadleaf, which 81
  species fall back to) sampled the clamped edge row: stretched stripes on an opaque card. Round 184's own South
  Philadelphia capture held one, taken for a hedge. `treeArtAtlas` now lays the cells in as many columns as a square of
  them needs (8) on the same canvas, each cell shrunk to fit (a side card 256 px on a computer against 320, 128 on a
  phone; the canvas, and so the memory, unchanged), the drawing and the shader reading the same column count (`C`), and
  throws if the cells do not fit. `tests/test_tree_art.py` lays out the atlas under node for a computer and a phone and
  checks the last look's cells lie on the canvas. Washington Square by day from 45 m and 18 m and the South Philadelphia
  street: every tree a picture. 485 tests.
- Round 184 coda, the street names (Mike, with a screenshot at Front and Laurel Streets under I-95: "The street text is
  messed up at this view"): a name takes the highest remembered pavement under each of its vertices, and a deck running
  ALONGSIDE a street passes the crossing-bridge test (aligned within 0.75), so North Front Street's letters stood up the
  side of the I-95 deck, and the label's own height took the deck wherever a vertex came within 4 m of an aligned chain.
  Now a surface more than `STREET_OVER_MAX` 3 m over the label's own pavement (the LOWEST remembered surface under its
  centreline at that point along it, else its height) is passing over and neither sets nor lifts it, and whether a name
  is on a deck is decided once along its length (five of nine points within 4 m of an aligned chain; `onDeck`), a deck
  name then taking the deck anywhere on the deck's own width (`ovpDeckY(..., wide)`). `__dbg.PERF.streetLabels` counts a
  name lifted more than 1.5 m off its own street anywhere (`warped`, `warpedAt`): 68 of 3,773 before, 25 after (14 deck
  names at a deck's end, 11 older ground cases: the Vine Street cut, 30th Street, the I-76 ramps at Packer Avenue).
  `tests/test_street_labels.py` adds a deck alongside a street over the label's edge (fails on the old code).
- Round 184 coda, the Irish Famine Memorial (Mike, with a night screenshot: "The irish famine memorial needs to be lit at
  night"): its bronze and granite are stored near black for the detail material's daylight lift, and nothing lit them,
  so after dark they stood as a black cut-out. They go to their own mesh (`famine-memorial`; the paved apron stays in
  the shared detail mesh) whose material adds, on the lamps' photocell (`lampUniform`), warm ground floods round the
  plinth: a face takes light as the square of how far it turns out toward the ring of floods, falling off with height
  over the plaza (e to the -0.5 a metre), as nine times its own colour, with a faint warm sheen. Daylight unchanged.
  Captured at 9 pm close and from the corner, and at 1 pm.

## Round 185 — the realistic look, step 1: occlusion, a filmic grade, a city's night (Oct 12)

- Mike: "How can we make this entire model look more photo realistic, similar to the game i sent in this thread
  initially? It still looks very much like minecraft, or a kid's game." Asked, he chose the realism work before the
  Custom House rebuild, and all three of lighting, shading and colour; roof and ground textures; facades everywhere. The
  diagnosis from the captures: no ambient occlusion (every box sits on the ground like a toy block), a saturated palette
  (lime lawns, flat grey roofs, spotless pavements: the Cities: Skylines brief since Round 54), flat untextured roofs from
  the air, hard flat light and a black ground by night, boxy cars. This round is the first.
- Ambient occlusion (desktop post pipeline, `AO`): the scene target is 4x MSAA with a depth renderbuffer, and the pins
  wipe the depth partway through the frame (`pinDepthClear`, renderOrder 99), so the city's depth is blitted at that
  moment, only while drawing into postRT, into a DEPTH24_STENCIL8 depth texture (`aoCopyDepth`; r149 resolves depth in a
  blit when the formats match, and the copy restores three's own framebuffer binding). Scalable ambient obscurance at half
  resolution: r149's log depth linearised (w = (far + 1)^d - 1, checked against a readback: a distinct, smooth value on
  every row), normals from the depth (the nearer neighbour per axis), a radius of 5% of the distance (1.5 to 40 m), twelve
  taps on a three-turn spiral rotated per pixel, a bias of 8% of the radius plus 6 cm (the roads' ribbons carry small
  steps), faded within 10 m of the eye and past 2.5 km, then a depth-aware blur across and down. The composite darkens
  the scene's own light by it before the bloom and tone mapping, never a lamp, a lit window or the sun. The first cut
  banded every flat in the city: a half-res pixel's centre lies on the line between two depth texels, and on alternate
  rows its neighbours were the same texel, so the normals there were garbage; the lookups snap to a texel's centre.
- The grade (`gradeU`, after ACES on the display colour): saturation 0.84, contrast 1.05 about the mid tones, warm lights
  and cool shadows. On every device: the lawn keeps 0.70 of its saturation (0.88 before), and by night the hemisphere's
  sky takes half a warm grey and its ground 0.7 of a sodium brown with 0.06 more intensity, the light the lamps throw back
  off the pavement. `?real=0` is the old palette, `?ao=0` the look without the occlusion, `?ao=show` the occlusion alone,
  `__dbg.real()` its uniforms. Before and after in Old City at 3:30 pm, a South Philadelphia street at noon and 9 pm, and
  over the Delaware from 230 m; the effect is real but modest from the air, where the roofs and the lawns are most of the
  picture (step 2). `tests/test_realism.py`. 491 tests.

## Round 185, step 2 — roofs and yards (Oct 12)

- From the air most of the picture is roofs, and two things made it a toy town. The roof lottery (an unresolved small
  house of rowhouse height takes a gable) dealt four in five of them gables, so South Philadelphia's rows stood as long
  lines of little peaked roofs; Philadelphia's rows are flat-roofed (a slight fall to the back). `roofLot(style, fa)`
  now takes the share by the house's own kind on the realistic look: 0.75 for the porch twins (style 10) and the stone
  houses, 0.5 for frame houses, 0.2 for the oldest brick rows, 0.04 for the postwar, Victorian, siding and new rows,
  0.3 otherwise (the old 0.8 under `?real=0`; the core's own LiDAR and Federal-gable lottery unchanged: Society Hill's
  Federal houses are pitched). Flat, those rows take the rooftop hardware too.
- And every flat roof was one calibrated colour. Four generated roof surfaces (`fetch_ground_art.py` ROOF frame, a drone
  looking straight down, nothing standing on the roof): black modified bitumen with repairs, silver aluminium coating,
  a white TPO membrane, gravel ballast, baked into one 2 by 2 atlas (`bake_ground_art.py` ROOFS: each made to tile, its
  960 px padded 32 px a side with its own wrapped edge, the kinds' linear means beside it), loaded by `loadGroundArt`
  into `roofArtU`, which every facade material reads. The facade shader's roof branch deals a kind per house (silver 36%,
  tar 30%, white 20%, gravel 14%; a sampled black or white roof keeps it), on the street grid's axes at 8 m a tile through
  `textureGrad` (the atlas cell's fract would otherwise pick the smallest mip along every tile edge), as three quarters the
  texture's own colour in the roofs' register and a quarter its grain on the roof's colour, gone past 1.4 m a pixel. The
  first seed was the tint byte, and a row on one block face shares its wall colour and so its tint: whole neighbourhoods
  drew one kind; the seed is now the house's base to the centimetre (`uRoofDbg` paints the kinds red, green, blue, yellow).
- The bare ground: a generated yard and vacant-lot surface (cracked concrete, packed dirt, weeds) comes through the lawn
  on a 55 m noise at the painted tile's brightness (`uYard`), so the alleys and yards between rows stop reading as lawn.
- Before and after over South Philadelphia from 90 m, over the Delaware from 230 m and in Old City. 494 tests.

## Round 185, step 3 — the mid-rise walls (Oct 12)

- Mike chose facades everywhere, and said there were credits for more. Between the house fronts (near the eye) and the
  tower cladding (35 m and up) stood every apartment block, loft, warehouse, school, office and shop with flats over it
  of three to ten storeys, all on the procedural window grid. Ten more generated wall tiles from `gpt-image-2`
  (`aptbrick`, a 1920s red brick apartment; `gardenapt`, 1960s tan brick; `loftbrick`; `warehouse`, concrete frame and
  brick infill; `institution`, a 1930s school; `modernapt`, fibre-cement panels; `commercial`, 1950s buff brick with
  ribbon windows; `paintedbrick`; `officemid`, 1980s precast with window bands; `stucco`), baked as the towers' are
  (`bake_tile`, 35 kinds now). `midSkinNote` hands 'Cladding the towers' every building of 9 to 35 m in the outer
  districts and the far ring that no house front dresses (`frontSetOf` < 0: the front quad sits 5 cm proud and the
  cladding 12, so they never meet), from 4 m up (the shopfront or lobby keeps the ground floor), its kind dealt by its
  facade style (`MID_KINDS`: a loft a loft or a warehouse, a residential slab garden apartments, brick or stucco, new
  construction fibre cement or dark brick, a school limestone or institutional brick, and so on; otherwise brick first).
  A computer only (`MID_SKIN`, `?midskin=0`): 13,350 buildings, about 190 bytes a wall, which a phone keeps for the
  towers and the house fronts. Captured over Center City, Rittenhouse and Washington Square West. 495 tests.

## Round 186 — the Custom House rebuilt (Oct 12)

- Mike, with his own night photo (IMG_0221, Oct 1 at 7:17 pm, a plain night on the lights calendar): "The us customs house
  needs a lot of work". The model was a base block to 9 m, a brick shaft over the whole block to 40 m, a 33 m box and
  stepped white octagons to a cone; Round 145's wash ran the whole block to 40 m, so the night's theme (teal tonight, OCD
  Awareness Week) painted the building teal brick and all. Sources: Wikipedia, GSA, HABS and WHYY (17 storeys, 87 to 91 m,
  a four-storey base under a fourteen-storey brick and limestone Art Deco tower, an octagonal lantern after the
  lighthouses of antiquity; Ritter & Shay, 1932 to 1934).
- Rebuilt in 'Restoring the landmarks' to `CH_DIMS`: the base over the block (limestone ground floor in the civic arched
  style, brick, a limestone top storey of arched windows under a balustrade, 26 m); a 32 m brick shaft with limestone
  centre panels to 58 m; a setback balustrade with a stone eagle at each corner and urns between; a 24 m pale stage
  between brick corner piers to 67 m, a 21 m attic and cornice with urns at its corners; the octagonal lantern to 80.5 m
  with a pilaster at each corner and a tall dark latticed arch in each face, its cornice, a dark dome (stored near black:
  the detail material lifts a flat far past its stored value) and an antenna, about 88 m to the dome.
- Its night (`CUSTOM_HOUSE_AT`): gold on the base's top storey and on the lantern, light blue on the pale stage, a red
  ring on the dome 1.4 to 2.3 m over its foot (clear of the lantern's cornice from the street), never the brick. A wash
  sheet can now carry its own plain-night colour (`sheetOf(..., house)`, `themeWashGeometry`'s per-vertex `house`, eased
  into the theme's colour as THEME.on comes up), so a plain night is the photo's gold, blue and red and a themed night
  deals the theme across the three slots as before. Captured by day and on the photo's night, from the street at 2nd
  and Walnut and from 95 m. `tests/test_landmark_lighting.py` follows the zones.

## Round 187 — no front off its wall (Oct 12)

- Mike: "Some of the new building fronts are obviously off kilter when applied to the buildings." A front lies on a side
  of the house's fitted (minimum-area) box, and `frontNote` took any outline whose box was up to 1.8 times its area, so a
  trapezoid on a diagonal street (East Passyunk, Ridge, Germantown Avenue), a wedge at a fork or a house with a recessed
  front put its front on a box side that is not its wall: standing off it at an angle or bridging a recess. Now
  `frontHonest` marks the box sides the outline's own edges run along (within 4 degrees and 35 cm, over 85% of the side),
  packed over the set index in the note's tenth float (`set + 16 * mask`, read as `& 15` and `>> 4`), and `frontSide`
  takes only an honest side; a house with none keeps the procedural facade, doors and all. 16,221 of 257,158 houses
  turned away citywide, 240,937 noted. `tests/test_fronts.py` (a rectangle four sides, a trapezoid with its end leaning 10
  degrees three, a house with a 1.2 m recess across its front three). Also a headless renderer for the capture skill
  (`scripts/render.mjs`: serves a folder on a free port, its own headless Chrome on the Mac's GPU, three renders at a time),
  so parallel work can capture without the Browser pane.

## Round 188 — the realism pass: ten workstreams (Oct 12 to 13)

- Mike: "Some of the new building fronts are obviously off kilter when applied to the buildings. Can we shape that up
  and please do anything necessary to make this look more photo realistic and less cartoony. This should apply to all
  surfaces/water/anything you can improve to look more real. Use all of the Open AI credits if you must." Round 187
  turned the askew fronts away; this round fits every front to its own wall line and takes the rest of the model with
  it.
- How it ran: an audit of 20 reference views by eight auditors and a critic (102 findings), then ten workstreams, each
  in its own git worktree on its own branch (realism/<area>), each implemented, adversarially reviewed (every verdict
  "fix") and fixed, then merged on realism/integrate. The first run stopped on the weekly usage limit with three
  workstreams unfinished and was resumed. About 300 new generated images (gpt-image-2 and gpt-image-1.5): 224 house
  fronts in 14 sets at their houses' own proportions plus a one-storey shop set, 16 street floors, 14 wall and roof
  materials, 7 street textures, 2 water textures, 39 vehicle views, and the ground's canopies, alleys and park macro.
- The integration's own findings. (1) Sixteen texture units: every branch added maps to the one ground program, and
  merged, the roads, the lots and the elevated decks (one sampler more each) failed to link and drew nothing, I-95
  included. The wet streets now read the lamp map under the lamp patch's own name (LAMP_WX_DECL, declared by the
  weather when it runs first; the lamp patch keys its once-guard on its own `uniform float uLampOn;`), a paved surface
  (a lane-painted road or deck, a lot, a structure's concrete or steel) takes no grass and no vegetation maps
  (surfTexPatch's `paved`), and the ground's review added vegBudget, which drops the pass's extra pictures by #define
  while a program would sample more than the GPU has; the headlight pools (carMapPatch) go in before it. Measured on
  the merged build: 232 programs on a computer and 135 on a phone, none failed, at most 15 and 13 units. (2) The
  vehicles took the streetlamps' pools at the old full strength on every face while the realistic patch had taken the
  city's to LAMP_REAL_K: a white car under a lamp stood out of a dark street like a daytime one. vehLampPatch now
  takes 0.85 of uLampReal.y, the faces turned up the most. (3) keyWeather merged post-shadows' clear-sky fill and
  exposure compensation with sky-atmos's sunDeckK (the deck's share only; fog and rain counted once inside). (4) The
  lamp posts: the streets branch's pedestrian post gave way to night-lamps' families (cobra heads, the Franklin
  lanterns, the wood poles). (5) The worktrees' lidar_cache symlink had been committed by a merge and is out again
  (.gitignore now names it without the slash).
- The render tool (`.claude/skills/philly3d-capture/scripts/render.mjs`) now prints the page's first 40 console
  warnings and errors (a shader that fails to link says so only there) and takes `--eval <file.js>`, an expression run
  after the last pose; a sampler probe over `renderer.info.programs` found the failing programs.
- Before and after: the 20 reference views on a computer and eight as a phone, against the deployed build. The white
  band along the night horizon on a phone was already in the deployed build.

### House fronts and tower skins (realism/fronts-skins)

Realism pass, fronts and skins (Oct 12 to 13, Mike: "make this look more photo realistic and less cartoony", use the
OpenAI credits). What was left of "off kilter" after Round 187 was the box: a front lay on the oriented box's side, so
a wall 30 cm inside it carried a paper front floating proud, a wall 4 degrees off it was crossed on the slant, and a
side the wall covered 85% of was overhung. frontHonest now fits each honest side's own line through the outline's
edges (offset, angle, span; one word a side in FRONTS.fit) and frontsLay lays the front there: offset median 0 and
95th percentile 14 cm, angle 95th percentile 1.9 degrees. The fronts had been stretched 1.2 to 1.55 times their
images' height, because every set was made at 768 by 1280 whatever its house. Fourteen sets were made again at their
houses' proportions with their storeys spelled out, and a one-storey shop set joins them. The bake reads each cell's
storeys from its rows of windows, and the shader keeps the ground floor and cornice band at the image's scale and
repeats or drops whole storeys between. A front now takes the cell nearest its house's own colour. It wears a 22 cm
moulded crown, not the second cornice slab, and no foam stoops. Its reveals shade by the sun, and it takes the rain,
snow and cloud shadows the walls round it take. The storefront boxes dissolve on the fronts' own dither under a
generated shop front, signalled through the sign of their vertex red so no new stream is uploaded. Their glass was
getting lit as display and painted over the shop's own door. After dark the luminance gate is gone: a front's window
is the facade's own roomLight over the whole opening the bake found. A shop's display lights where its painted glass
is dark and keeps its own pattern; the first try lit it as a white sheet, then as a grey photograph, and the fix was
the display's own relative luminance. The tower and mid-rise skins start and end on bay lines along whole walls (a
curved wall's facets are one wall) and meet the roof on a spandrel, with a parapet over the tall plain towers. Their
masks are filled to each window's box, with five tiles found by their wall's colour, and lit as roomLight rooms cut at
each tile's own pier and spandrel. The night towers had been showing curtain-shaped cut-outs and black stencils; they
now show lit rooms. Sixteen generated street floors now stand under the walls that start 4 or 5 m up. One measured
cost: the weather, the clouds and the rooms in a program per skin kind took Cladding the towers from 1.5 s to 10 s of
compiling behind the veil. Every kind now shares one program through uniforms (1.3 to 1.5 s), and the sixteen front
sets share one too, so no set compiles in flight.

Realism pass, fronts and skins, the review (Oct 13). The masks had carried each window's height in alpha, and an image
with any alpha under 255 reaches WebGL on WebKit through a premultiplied decode. That moved every window's number in
green by one across its rows, so on the iPhone each lit window would have drawn as bands of different rooms; headless
Chrome decodes straight, which is why no render showed it. The masks are opaque RGB now and the height rides in blue,
which also turned the rooms right way up: the old alpha had the ceiling glow at the sill. The shop displays had been
lit across the whole box find_openings returns, which on a dark front is the whole ground floor, so a black or green
cast-iron front glowed bone white with its frames, pilasters and doors. The bake now finds the glass inside the box
(near neutral, darker than the box's own dark, in pane-shaped pieces) and lights that alone. A third of a Center City
shop's display box is glass; the lacquered Chinatown front and the grille are left dark. The storefront boxes now give
way only on the side a front is actually laid on, and only once its atlas has arrived. ?real=0 shows Round 184's
fronts again. The skyline's speckle came from roomLight lighting half the rooms at every hour behind a constant cut.
The towers' share now follows the model clock (offices at two fifths by nine, a fifth by three; homes fill toward
seven and empty toward three), and a window a few pixels across gives half its light. The wide and near-square sets
came back inside Round 184's 4.7 MP budget. Measured on the phone path: the fronts, skins and street floors cost 1 to
3 ms of a 24 to 28 ms frame, and the heap settles at 307 MB after GC against main's 301.

Not done:
- real iPhone check: No device is reachable from here. The fix removes the cause (masks are opaque, so WebKit does no
  premultiplied decode), and a test simulates the round trip on every mask. Mike should still look at a lit block on
  the phone after the deploy.
- merge integration check: These programs depend on roomLight(vec2, vec2, float, float) in WINDOW_INTERIOR_GLSL, on
  wxSurfacePatch's replace points, and on the 'Dressing the storefronts' step. That can only be checked after the
  branches are merged: rebuild, then read renderer.info.programs diagnostics. This branch's diagnostics are clean on
  desktop, touch and ?real=0.
- buildings#7 (penthouses), buildings#0 step 6, gap#7 (b) parallax: Unchanged from the first report: the researched
  crowns are Mike's call, the procedural storefront atlas is optional, and the shader budget went to the night rooms.
- five light-glass tiles: Unchanged: aptbrick, commercial, institution, warehouse and resi still light only part of
  each window.
- shop fronts the bake finds no display for: find_openings is unchanged, and some one-storey and mixed-use fronts have
  display panes it does not find (for example under a roll shutter). Those stay dark after dark, as before.

### Shadows, exposure and the post pipeline (realism/post-shadows)

- Mike: "please do anything necessary to make this look more photo realistic and less cartoony". Shadows were the
  biggest gap. Outside the core nothing took part: the outer districts', the far ring's and the towns' buildings cast
  and received nothing, and neither did the ground, parks, streets or lots around them, so a rowhouse threw nothing
  into its street and Rittenhouse's towers nothing onto the square. `shadowRoles` fixes this with flags alone (r149's
  receiveShadow is a per-object uniform, so no program changes): on a computer the merged buildings cast and receive,
  and every weather-hooked flat and the tree cards receive. It runs on the first frame and again every 900th, so the
  closures' paving strips get their roles too. A phone gains no casters until the iPhone's beacons say what they cost.
  The tree cards had never cast: r149 never uploads viewMatrix to a MeshDepthMaterial, so `tCard` built every card
  from a zero matrix; the depth variant now reads modelViewMatrix. A card's lookup now stands 0.6 of its crown toward
  the sun, out of its own shadow. Girard College's apron gave up its getter pin, so Founder's Hall's shadow runs
  across it.
- `FARSH`: past the near box, a black second directional light whose 4096 map covers 3.6 to 8 km. It is not CSM:
  `lights_fragment_begin` is rewritten once before anything compiles, the sun reads the near map and then the far one,
  and the black light is never lit. Buildings only, drawn on a quarter-box move or a third of a degree of sun.
  ?shadowwide=0 and Smoother turn it off. `keyWeather`: real overcast, rain and fog cast no shadows, so the key fades
  as the deck closes, in fog and in rain, and comes back as sky. The occlusion is leaned on harder, every receiver
  goes off under 0.04 (moonShadowsOff now keeps reasons) and the depth passes idle. The camera exposes the grey day up
  to 1.5 times. The occlusion's black creases fade for taps toward the eye, with a 0.5 floor. `BLOOMW` adds three wide
  levels for a lamp's glare (?bloomwide=0). A phone tone maps through CustomToneMapping with the grade in linear
  light.
- Measured headless on this Mac: the outer casters cost the near map 0.7 ms per redraw at 90 m and 7 ms at 600 m (a
  box full of roofs fills the whole map), so the movers' redraw runs every 8th frame above 250 m. The far map's
  lookups are within the noise, and the busiest program binds 9 of 16 texture units. Probes: `__dbg.gpu()`,
  `__dbg.pickAt()` (it named ref 16's "grey box": a rooftop condenser on the roof of the building the pose's eye
  stands inside), `__dbg.shadowAudit()`, `__dbg.shadowRoles(false)`, `__dbg.farShadows(false)` and `__dbg.keyLight()`.
  `tests/test_realism_post_shadows.py` and `tests/shadows_gpu.html`.

- Mike: "please do anything necessary to make this look more photo realistic and less cartoony". Shadows were the
  biggest gap. Outside the core nothing took part: the outer districts', the far ring's and the towns' buildings cast
  and received nothing, and neither did the ground, parks, streets or lots around them. `shadowRoles` fixes this with
  flags alone (r149's receiveShadow is a per-object uniform). On a computer the merged buildings cast and receive (505
  casters), and every weather-hooked flat and the tree cards receive. It runs on the first frame and again every
  900th. A phone gains no casters until the iPhone's beacons say what they cost. The tree cards had never cast: r149
  never uploads viewMatrix to a MeshDepthMaterial, so the depth variant now reads modelViewMatrix. That fix is not
  gated by REAL, so under ?real=0 the cards cast too. A card's lookup stands 0.6 of its crown toward the sun. Girard
  College's apron gave up its getter pin.
- `FARSH`: past the near box, a black second directional light carries a far map 3.6 to 8 km across.
  `lights_fragment_begin` is rewritten once before anything compiles: the sun reads the near map, then the far one,
  and the black light is never lit. The far map holds buildings only. It is 2048 under Auto (24 MB of GPU memory) and
  4096 under Sharper (96 MB, an RGBA8 target plus r149's 16-bit depth). The headless A/B at 90, 300 and 600 m showed
  no difference between the sizes. Its normal offset is a texel and a half. It is drawn on a quarter-box move (at most
  once a second while moving) or on a third of a degree of sun. In a time-lapse, where the near map is redrawn every
  frame, it waits two frames and takes the third, and the near map is drawn the next frame (6 far draws in 48 frames,
  against none). Above 250 m (back under 220) the outer districts leave the near map: `FARSH.wide`, shadow.radius 2,
  makes the far map shade the near box too, the darker of the two. With no far map (Smoother, ?shadowwide=0) they cast
  nothing up there.
- The measurements, headless on this Mac with other renders sharing the GPU, so the timer samples are bimodal (about 1
  ms, or 25 to 45 ms). The earlier figures (near map 8 ms at 600 m, far draws 2 to 6 ms with means near 20) were
  medians and means under that contention. The minimums: the near map at 600 m costs about 1 ms with or without the
  outer casters, and a far draw 0.9 to 1.1 ms at 600 m and 0.9 ms at 90 m. The first draws were not the outliers.
  Still open: the frames around a far draw over Center City from 600 m reached 24 to 106 ms on the CPU, against 5 for
  a plain frame. Over South Philly from 90 m they cost 1 to 2 ms more. `__dbg.gpu(true)` now keeps 32 samples a pass,
  with the shadow passes' CPU time and draw calls (`shadowFarCpu`, `shadowFarCalls`). Measure this on the Mac itself.
- `keyWeather`: real overcast, rain and fog cast no shadows, so the key fades as the deck closes, in fog and in rain,
  and comes back as sky. The occlusion is leaned on harder and every receiver goes off under 0.04 (moonShadowsOff
  keeps reasons). While idle the depth passes stop, but the light keeps turning. The review found a phone's moonlight
  held at the boot direction all night, because aimSun returned before writing it. A mesh that turns its own receiving
  on meanwhile is swept into the list every 60th frame. The camera exposes a grey day up to 1.5 times. A phone's fog
  takes no inverse any more: r149 mixes it in after the tone mapping, and the division had put the overcast haze at
  two thirds of the sky. On a clear day the sky's share of the light rises 1.8 times, and the exposure gives back what
  that adds to a sunlit street, so sunlit levels stand and the shade comes up. Merged with the sky's own fill, Broad
  Street's shaded asphalt goes from (34, 47, 56) to (44, 54, 60), and Rittenhouse's lawns under the trees are no
  longer black. The occlusion's black creases fade for taps toward the eye, with a 0.5 floor. `BLOOMW` adds three wide
  levels of glare. A phone tone maps through CustomToneMapping with the grade in linear light. The dome, the clouds
  and the pins are not graded on a phone.

Not done:
- review SHOULD: phone grade on the dome, clouds and pins: The comment is corrected instead. Grading them on a phone
  means editing their own shaders under uPost 0 (sky-atmos's region). The environment bake also renders the dome with
  uPost 0, so a grade there would change the IBL on every device.
- review SHOULD: the far map's CPU cost per draw: Measured but not explained. Over Center City from 600 m, the frame
  around a far draw reached 24 to 106 ms on the CPU, headless; from 90 m over South Philly it was 1 to 2 ms over a
  plain frame. The render budget (five runs) was used up. The wrapper now records shadowFarCpu and shadowFarCalls, and
  the one-second floor caps how often a flight pays it. Measure on Mike's Mac before merging.
- gap#2 (step 3): As before: weighting the AO toward indirect light needs the direct share written into the facade
  hook, surfTexPatch and the fronts, which are other workstreams' regions.
- gap#12 (Auto gate on p95 under 14 ms): As before: desktop frames are vsync-paced, so the gate would switch the
  passes off everywhere.
- sky-light#8 (b, c), critic objection 0/1 height-map shadows: As before: CSM was rejected, and a height-map lookup
  would need taps in other workstreams' shaders.
- weather#2 (part 3), vehicles-props#12 (fronts customDepthMaterial): As before: done by sky-atmos, and the ghosts
  were the roof kit.

### Sky, air and clouds (realism/sky-atmos)

Realism pass, sky and air, second try. The first commit made the air a medium: exponential height fog on true
distance, visibility from the weather, skyglow, a rain deck that drops, and a lightning ribbon. Its clouds still read
as airbrushed lenses and melted wax, so this commit rebuilds the cumulus. On a computer with WebGL2, the GPU draws two
tiling noise volumes once at boot into 3D render targets, slice by slice: a 128-cubed Perlin-Worley shape at 2.6 km
per tile and a 64-cubed Worley detail at 420 m. That takes 50 to 205 ms on the headless Metal GPU, with no files. The
2D field the ground's shadows already read still decides where a cell stands, so every shadow lies under its cloud.
The cell's strength lifts the top of a flat-based body that rounds over it, the shape carves the billows, and the
detail erodes the edges: wisps under the base, billows above. The first render was a field of extruded columns and
curtains. Measured in numpy, the remapped Perlin-Worley sits between 0.69 and 0.92 (5th to 95th percentile), too
narrow to carve anything, so it is spread to the full range. Coverage was fitted to the shadows' share: 9% of a slice
at 22% cover, 23% at 45%. Three taps up the sun's ray, using Beer's law plus a gentler multiple-scattering octave,
keep cores grey rather than black. The jittered coarse entry speckled every opaque edge, so the march now backs up 0.7
of a step at each cloud face and walks it in thirds. Far billows ease to their mean, or the distant deck broke into
popcorn. Phones and WebGL1 keep the first phase; their generated GLSL is identical to the last commit's. Stars: the 24
brightest at their real places by sidereal time; Polaris rendered at x 647 where the math put it. They vanish under a
deck, in fog, rain or smoke. At night the lamps' light in the low air is now added light under one law for the city,
the deck and the dome. A fog night had shown a dark band over the horizon and dark holes in the deck, because the open
dome took 0.6 of the glow while the deck took all of it. The dome's far cloud band is lit from below at night, and the
env probe re-bakes as the weather eases in. The white band of lit windows on a phone's night horizon predates this
pass (main shows it too).

Realism pass, sky and air, the merge review. The sky branch and the weather's key light met in applyLighting, and
three things there were wrong without either side conflicting in text. First, the sun was dimmed for fog twice, once
in the sky's deck share and again in keyWeather, so a fog morning's sun was 0.3 of a tenth of itself. Second, the
camera's lift was computed from the old deck share rather than from the sun the city actually lost, so a 0.7 cover day
kept 0.79 of its sun and was still exposed 17 per cent brighter. Third, keyWeather divided a phone's fog colour by
that lift, as if the haze were exposed with the city. It is not: r149 mixes the fog after the tone map and the
encoding, in display colour. The compiled phone program puts the tone map at offset 9882 and the fog at 10329. So the
phone's far haze and its dome were both up to 1.5 times darker than the computer's in fog and rain. Now the deck's
share goes to keyWeather, keyWeather takes fog and rain once, and nothing scales the fog colour. A phone's fog morning
is the same milk as a computer's. The cull line is back where Rounds 51 and 52 put it: 40 km by day and 16 km by
night, where the new air had pushed it to 50 and 20. A street-level eye in radiation fog now culls at 2.2 km instead
of 9.2, because the ground-fog layer is counted along the clearest ray to a 360 m roof. The old wall closes the last
quarter so a dropped chunk never pops. In the clouds, a weak cell had kept its strongest puffs at full density, which
left hard white islands off every cumulus. A cell's strength now caps its density, the far deck eases to half density,
and the walk in thirds reads the field at the coarse step's filtering. The specks and jagged edges are gone and the
cloud forms are the same. A phone's 32 steps carried the per-pixel jitter as salt-and-pepper fixed to the screen, so a
phone marches from the midpoints again. The volumes now stand down on a weak integrated GPU and under Smoother
(?clouds3d=1 forces them). They also give way to the first phase if their program fails to link, which was checked
live by forcing the switch mid-session. Their shadows project from the volumes' own 1,250 m.

Not done:
- review SHOULD (measure desktop cost on Intel/AMD at 1440p; half-resolution deck): No Intel or AMD GPU is reachable
  from here; renders only run on this Mac's headless Metal. Instead the volumes are gated off for weak GPUs and
  Smoother, with ?clouds3d=1 to force them for the measurement. A half-resolution deck with depth-aware upsampling is
  a larger change to the render path; it is left for the next round if the measurement asks for it.
- review SHOULD (vFogV on a real iPhone): No device here. The cost is reduced (vFogDepth is now derived from vFogV, so
  +2 floats rather than +3), and the phone path compiled and rendered under --touch with 0 bad programs. Still to be
  checked on a real iPhone before shipping.
- night#9 (desktop lamp-map in-scatter), weather#11 (scud, rain shafts), sky-light#4 (a)/(b), night#1 (f), sky-light#6
  (AI coverage map, temporal reprojection): Unchanged from the previous report: they belong to other workstreams, or
  no generated texture was the right answer. No OpenAI credits were used.

### Walls and pitched roofs (realism/facade-shader)

The realism pass, facade shader (Mike: "please do anything necessary to make this look more photo realistic and less
cartoony"). The walls and pitched roofs are now generated photographs rather than analytic patterns. fetch_wall_art.py
made nine walls and four roofs with gpt-image-2, and bake_wall_art.py cut each coursed one on its own joints so it
tiles with no seam. A wall takes only the texture's grain over its kind's mean, so the calibrated colours and the York
Street bands do not move. The joinery, stone and awnings stay out of it (trimM), and rain runs, splash and sill stains
weather it. A flat roof keeps its dealt kind at any height. The far roof had been going back to one grey past about
150 m; the kinds now spread from tar 0.8 to white membrane 1.9. Snow and wet land after the gains: the s02 snow pose
had every roof black tar and the street white, and now the roofs are the whitest thing in the aerial. The rooms follow
the model clock: homes peak at 0.55 at 21:00 and fall to 0.06 by 04:30, offices run 0.80 at 17:30 down to 0.10, and
lamps are 2700 to 5000 K instead of half the suites pale blue. A computer sees a room behind the glass by day and by
night (interior mapping), and glass that looks below its horizon reflects the city's share instead of open sky. The
second commit is about the roofs from the air and the street. The packed tiers' eaves overhang their walls 0.3 m along
their own plane. The hips' eaves had stood 0.3 m out at the wall's height, a slit of sky under every one from the
street. A computer boxes every eave in with a fascia and a soffit: 167,878 quads over 33,386 gables and 4,269 hips,
about 26 MB. Rows read as rows from the air, with a brick party-wall coping under a coated cap on both sides of every
rowhouse and across strips of rows within ROOFKIT.r. In the pitched districts, a detached L is roofed as a main hip
with a cross wing run into it to its ridge, so they meet in valleys. The cross wing sits 3 cm low where a face of each
is one plane. That is 13 houses, because roofL takes only footprints within half a metre of an ideal L (14,171
candidates sampled offline, 449 honest Ls, most of them not detached lottery winners). ?real=0 keeps the old look
throughout. __dbg.facade() reports the wall art, the rooms' shares and the pitched counts.

The realism pass, facade shader (Mike: "please do anything necessary to make this look more photo realistic and less
cartoony"). The walls and pitched roofs are now generated photographs rather than analytic patterns. fetch_wall_art.py
made nine walls and four roofs with gpt-image-2, and bake_wall_art.py cut each coursed one on its own joints so it
tiles with no seam. A wall takes only the texture's grain over its kind's mean, so the calibrated colours and the York
Street bands do not move. The joinery, stone and awnings stay out of it (trimM), and rain runs, splash and sill stains
weather it. A flat roof keeps its dealt kind at any height, the kinds spread from tar at 0.8 to white membrane at 1.9.
Snow and wet now land after the gains: the s02 snow pose had every roof black tar under a white street, and now the
roofs are the whitest thing in the aerial. The rooms follow the model clock: homes peak at 0.55 at 21:00 and fall to
0.06 by 04:30, offices go from 0.80 at 17:30 down to 0.10, and lamps run 2700 to 5000 K. A computer sees a room behind
the glass by day and by night. Glass that looks below its horizon reflects the city instead of open sky. The second
commit added eaves, L roofs and party-wall copings. The review's round then fixed what that commit had overreached.
The towers' skins went back to fronts-skins' own material, which takes the clock through one occBind line at the
merge. The walls' art became a computer's whole (WALL_ART_DEV): the phone program carries no wall kind, detail or
gable-end branch, and no phone rebuild is re-hooked (136 programs on the phone path, none bad). Its gradients are now
taken before the branch that the glass's edge splits within a pixel quad. The snow block runs only when it snows or
rains, and the weathering only where the detail stands. ?real=0 is the old look again under weather; the difference
image against main shows only snowflakes. The copings had been laying party walls every 5.4 m across apartment slabs,
garages and schools, because a roof note knew only its box. Each note now carries a row flag: a row or a corner store,
by the OPA word or the type, no more than 14 m up. The kit takes the snow itself (its own hook keeps the weather's re-
hook off it), so a coping is a white cap on a brick wall, not a brown line across a white roof. The eave boxes are the
outer districts' only: 41,984 quads where there were 167,878. Everywhere else a roof sits flush on its walls, since an
overhang with no soffit under it is a slit of sky from the street (a roof is one-sided), which every hip in the far
ring showed. occUpdate no longer makes a Date every frame. __dbg.facade() reports the wall art, the rooms' shares and
the pitched counts.

Not done:
- night#6 tower skins in this branch: The tower-skin material belongs to fronts-skins, which rewrote it with a REAL
  branch. The share goes to the merger as one `occBind(sh);` line in that branch, after `sh.uniforms.uSkinG =
  skinU.uSkinG; sh.uniforms.uSkinF = skinU.uSkinF;`.
- buildings#13 (city cube probe): A probe of a new size recompiles every lit program. Only the horizon occlusion term
  shipped.
- buildings#11 parts 4 and 5: The LiDAR ridge azimuth would need wide.b64 and city.b64 repacked, which is forbidden.
  Rows never take gables since Round 185. T and U plans stay flat.
- night#7 (fronts' pane rects, tower-skin interiors): These belong to fronts-skins.
- eave boxes in the far ring: Cut at the review's request (167,878 to 41,984 quads). The far ring and the towns get
  flush roofs instead.
- build.py / test manifest-line conflicts with streets, water and vehicles: These are the same tuple and count lines
  every art branch adds. Integrate has already resolved streets and water, and my branch merges clean into integrate.
  The vehicles conflict needs the same one-line resolution when vehicles is merged.

### Ground and vegetation (realism/ground-veg)

Realism pass, the ground and the vegetation (Oct 12 and 13). Mike asked for the whole model "more photo realistic and
less cartoony", and the ground was most of the cartoon. From the air every tree wore a black outline: the canvas atlas
premultiplied its clear texels to black and the mips bled it into every crown, so the atlas now stays premultiplied
and the shader divides the coverage back out. Each card is lit as a dome, and each tree is its own picture: mirrored,
sized and tinted by its seed, with its root plate under the grass. A computer draws the cells at 448 and 224. Autumn
came a month early and all at once, so the turn now averages Oct 17 to Nov 14. Each tree turns over its own stretch
through a new turning picture (fifty gpt-image-1.5 images, a fifth of the crown coloured), and the bake mutes the peak
colours. Under REAL the lawn keeps its photographed colour and its two tilings' contrast, with a generated 240 m
parkland macro and winter dormancy. A land mask baked from the build's own blobs, parkland and river outlines
(bake_landmask.py) tells the bare ground what it is: yards, patios and alleys behind the rows; a generated forest
canopy by season in the woods, with a wood field of species cards within 1.5 km on a computer; and at the two rivers'
banks riprap, wet silt and the tide's stain, through one TIDE snippet any surface can take. A canopy map of all
106,808 crowns, built like the lamp map, gives shade under them, their cast shadow past the live box and on phones,
and the November leaf fall. Tufts are packed into 45 m in the lawn's own colour. Snow lies in drifts, flattens the
grass and whitens the boughs. On the retry, a guard went in. The other passes each add a sampler to the ground's
programs, and a lot would have sampled 17 textures against the 16 nearly every GPU allows. surfTexPatch now ends by
counting what a program samples and, while it is over, drops this pass's extras through their #ifndefs: the riprap
first, then the macro, the alley, the canopy. The count missed by four at first: the physical material's source
declares four maps inside #ifdefs that are off. ?vegtex pins the limit, and __dbg.veg().budget lists every program.

The realism pass, ground and vegetation, the review's round (Oct 13). The branch now sits on the integration branch.
The paved surfaces' arm in vegSurfPatch declares no pictures, and the other arm keeps each one behind its own #ifndef,
so the texture guard can still take them out. The reviewer found the woods standing in the water: about 10 km2 of
reservoirs, lakes and creeks, plus the Amtrak corridor, could take wood trees. The land mask now draws every water
ring and every open track at 5 m and zeroes any 20 m texel they touch, and the wood field plants nothing on a zero.
Checked at 2.5 m against the rings and every 8.5 m along the tracks, nothing is left. (The reviewer's East Park
Reservoir point is the parkland beside it; the reservoir's own ring is 500 m west and was always clear.) The far
south-west rectangle was every Delaware County park wooded whole, because the tree survey stops at the city line and
every park past it read as treeless. The park rule stops there now, and stand edges are broken by noise in the mask
and again in the field. The woods are darker, greyer and a deeper green than a street tree. A sow goes up to the GPU
once instead of every frame. Under the frame noise of three headless Chromes, the field's cost could not be told from
zero: one draw call and 36,000 triangles. ?real=0 shows Round 185's trees again: every look change sits behind REAL,
while the premultiplied atlas and the later calendar stay for everyone. The turning picture's orange cap now comes in
clumps, half of them back to the crown's own olive, and a tree changes clump by clump. The atlas canvas is only the
first fill. Once uploaded its backing store goes (56 MB on a computer), and a season's change sends up only the cells
it redrew. On a phone the riprap is out of every program and the canopy map's instance data is let go. GC-normalised
and against the WebGL hook, a phone stands at 146 MB of live heap and 904 MB of GPU after the look round, the same as
the integration branch. Main was 122 and 855; that gap is the whole merged pass, every workstream. The piers' piles
take the tide band, and the land mask bake joins the pipeline.

Not done:
- ground-vegetation#2 (e) art regeneration: Still not regenerated. The dome normal and per-tree variation cover the
  lit side. No AI images were made this run.
- ground-vegetation#10 variants: Still one picture per look and season, varied per tree by mirror, size, width and
  tint.
- desktop atlas size: The 448/224 cells were kept at TIER 0 (about 75 MB of GPU with mips). The review's other two
  costs are fixed: the canvas backing store is freed and season changes no longer re-upload the whole canvas. Cells of
  384/192 would save about 20 MB if Mike wants that trade.
- wood field GPU cost on real hardware: Headless GPU timers were dominated by three Chromes sharing the GPU, so on and
  off were indistinguishable. Geometry is measured (+1 call, +35.7k triangles). A clean frame-time A/B needs a visible
  pane or a real machine, using ?woods=0 or __dbg.woods(on).
- canopy map RG format on phones: Halving the phone's 4 MB canopy target to RG8 was considered but not done: it is a
  render-target format change I could not verify on a real phone.

### Streets (realism/streets)

Realism pass, the streets (Oct 12 to 13). Mike asked for "photo realistic and less cartoony" on every surface, and the
streets were the most cartoonish thing in an aerial frame: the Skylines grey ribbon calibrated to show near 200,
brighter than the roofs, the core's charcoal running navy under the sky's fill, a double yellow on every 7 m rowhouse
street, and lawn from the kerb to the front steps. Under REAL (?real=0 keeps all of it) the asphalt is re-keyed
neutral-warm at about 0.45 of its old linear value. Each street is a little older or newer than the next, so an aerial
reads block by block as fresh blacktop and faded grey (sRGB 92 on Pine in sun, 115 to 125 on a South Philly street). A
new lane shader works on the street's own axes: oil down each lane, the wheel paths, three generated lane photographs
laid lane by lane, utility cuts, manholes, the gutter and a kerb, and paint 12 cm wide in worn amber. The junctions
are found once per tier (15,171 arms in the outer districts, 41,786 in the far ring) and ride aLane.w as a reach that
interpolates exactly, so every crossing gets continental bars or two lines, a stop bar over its inbound half and no
lane lines through the box. A residential way under 9 m is unmarked (2,117 of 2,917 are one-way, and the rest carry no
centre line in life either), decided from the width so nothing was repacked. bake_sidewalks.py paves 5 km2 of the
outer districts from the kerbs to the facades: brick in the historic districts, 397k triangles on a computer, the half
mile on a phone (+1% in view), none in a LITE city. The lots lay stall rows and oil on their own frame. The decks and
the El take generated concrete and riveted steel. The cobra heads are galvanized, and every lamp under 5 m is a black
lantern post. The main line shows its ties. The paving season's strips are now streets themselves: on the street's own
width rather than 8 m over the sidewalks, cut square, the fresh course near black. Rendered against the current build
at sixteen poses plus a phone set. The shaded core streets now read near black (about 35), which belongs to the fill
light, not the asphalt.

Realism pass, the streets, the review round (Oct 13). The reviewer found the stop bars on the outbound half of every
two-way street: u = offset·(-dz, dx) is the right of travel in this frame, not the left. The bar now covers u ≥ 0 when
the junction lies ahead, and a top-down render at Washington and Broad puts both bars on the east halves, south of the
box. PHL's runways and taxiways ride pack_city's class 5 at 45 m and 16 m. They had been paired by the junction search
and given continental bars, full-width stop bars, kerbs and manholes; isAirfield now keeps them out of the search and
gives them a class of their own, plain asphalt. The lots' stall phases were taken on an angle the shader could not
rebuild, so the rows started anywhere; they are now quantized first and anchored on the lot's own edge, which a test
checks to the centimetre. The sidewalks were the real work. The first cut staged 3.6 M boxed entries and uploaded all
395 tiles on a phone, which only ever drew the twenty-five near it. The rings now stay in their Int16 form and are
laid straight into typed arrays: a computer lays them at load in 57 squares of 1,200 m (24 draw calls at the s09
aerial, where the 400 m tiles would have added 113), and a phone lays the 200 m squares within the half mile as it
flies, nearest first, about 3 ms a frame, dropping each one 200 m behind the circle. Each ring fades out at its own
distance over the last 220 m, so a phone's aerial shows no ring of squares. The tuft field had kept 266,000 sidewalk
points alive through noSow; it now tests the rings in place. Measured GC-normalised on the headless phone path, the
branch stood 14 MB of live heap over HEAD at ready (132 against 118) and 6 MB of GPU (824 against 818), with no padded
copies. Reading the code afterwards traced the 14 MB to the decks' material hook, written inline in 'Raising the
overpasses', which kept that whole step's scope and its part geometries alive for the session: Round 158's leak again.
It, the El's hook and the lot sheets' hook are now module-level functions, and a test keeps them out of their steps.
That fix was not re-measured. The phone's PACE fields saturate at 999 ms under SwiftShader in both builds, so the lane
shader's fine detail could not be costed there; it is now a computer's only, with PERF.laneDetail for an A/B on a real
device.

Not done:
- streets#4 (oneway/lanes bits): Needs a repack of wide.b64 and city.b64, which the task and CLAUDE.md forbid. Broad
  Street's two carriageways still each draw as a two-way street with their own double yellow, and the stop bars follow
  that.
- streets#9 (parapet profile, El girder geometry): Only the material side was done; the deck and El geometry and their
  triangle counts are unchanged.
- streets#13 (emissive lens): Not done; the night glow still comes from the pole glow sprites and LAMPMAP.
- gap#1 (dithered side feather): Not done; a hard edge matches real milling and paving cuts.
- re-measuring the phone heap after the hook fix: The five-run budget was spent: desk-new, desk-head, touch-new,
  touch-head and desk-verify. The +14 MB is attributed to the decks' inline hook by reading the code, and the fix is
  not verified by a run.
- PHL's white aprons: Pre-existing and identical in HEAD: COLORS.paving through ringAreaParts renders near white. It
  was not in the review and was left alone.
- streets#1, #6, #10, #12: Not my ids. #1 is the owner's lettering and is untouched.

### Water (realism/water)

- Mike: "please do anything necessary to make this look more photo realistic and less cartoony. This should apply to
  all surfaces/water/anything". Every change is REAL-gated; ?real=0 keeps Round 54's slate-teal water, which this
  supersedes, so show it to him with the other look reversals as one set.
- The water's shading is now the physics. `liquifyReal` uses Schlick Fresnel against the water's own sky-only probe
  (`waterEnvBake`: the glass's generator and 256 cube with the sun disc and placeholder boxes hidden, the water
  materials' own envMap, re-baked at the end of refreshEnv), undone through the tone curve as the dome is. The body is
  an olive-grey estuary, a greener Schuylkill, lit by the scene's lights and the shadow map under 1 - F, so the
  bridges shade the river.
- The waves are a tileable FFT slope field from a Phillips spectrum made at load (`makeWaveSlopes`), with the variance
  a footprint loses widening the glitter. The glitter is a Beckmann lobe sized by Cox and Munk's wind law, HDR with
  point facets on a computer and clamped to 3 on a phone.
- On a computer the city stands in the rivers through a half-size planar mirror (`reflRender`, layer 5 via
  `reflSweep`, its own counts apart from POST's, ?refl=0), and at night the lamps stretch into pillars. Ships and the
  ferry draw bow waves, foam and Kelvin arms; rain rings the water near the eye; cloud greys it.
- Water on high ground is built where it stands: Swann's basin with its jets, the Eakins Oval pools, Dilworth flush,
  and the reservoirs at their own level with a bank wall. Piers over the water are decks at the bulkhead on creosote
  piles, and the Washington Avenue Pier is a lawn on such a deck. The Fairmount Dam's water now falls.
- Coda, measured from the air: the first decks drew 220 of 255 because a hex is a linear albedo here (0x5c5a54), the
  white slabs again. At 0x24231f they draw 165, with the fascia and piles darker. The core's Delaware is one quad with
  no shore alpha while the outer sheets carry one, so the shallows term drew a straight seam along the pierhead line;
  liquifyReal no longer has a shore term.
- The Schuylkill above the dam's crest is a calm pool (`wPool`), so Boathouse Row mirrors by day and its outlines
  stand in the water at night. The Delaware went from khaki (70, 76, 61) to olive-grey (67, 77, 66) from 380 m. Tests:
  `tests/test_realism_water.py` (21 checks, including the pool expression evaluated at Boathouse Row, the tailwater
  and the Delaware).

- Mike: "please do anything necessary to make this look more photo realistic and less cartoony. This should apply to
  all surfaces/water/anything". Every change is REAL-gated. ?real=0 keeps Round 54's slate-teal water, which this
  supersedes, so show it to him with the other look reversals as one set.
- The water's shading is now the physics. `liquifyReal` uses Schlick Fresnel against the water's own sky-only probe
  (`waterEnvBake`: the sun disc and the placeholder boxes hidden, the water materials' own envMap, re-baked at the end
  of refreshEnv; a phone's is a 128 cube from its own generator). The body is an olive-grey estuary and the Schuylkill
  a greener one, lit by the scene's lights and, on a computer, the shadow map, under 1 - F.
- The waves are a tileable FFT slope field from a Phillips spectrum, made at load (`makeWaveSlopes`). The glitter is a
  Beckmann lobe sized by Cox and Munk's wind law: HDR on a computer, clamped to 3 on a phone.
- On a computer the city stands in the rivers through a half-size planar mirror (`reflRender`, ?refl=0 turns it off),
  and at night the lamps stretch into pillars. Ships and the ferry draw bow waves, foam and Kelvin arms; rain rings
  the water near the eye; cloud greys it.
- Piers over the water are decks at the bulkhead on creosote piles, and the Washington Avenue Pier is a lawn on such a
  deck. The Fairmount Dam's water now falls. The Schuylkill above the crest is a calm pool (`wPool`), so Boathouse Row
  mirrors by day.
- Coda, the review (Oct 13). First: water on high ground had levelled every ring. Mill Run, Cobbs Creek and the NW
  streams, ribbons falling 15 to 60 m, stood across their neighbourhoods as raised channels and granite walls.
  `waterRingGate` now builds a ring only when it is compact (4 pi A / P^2 of at least 0.2; creeks are 0.01 to 0.05),
  its own ground lies within 1.5 m for a basin and 6 m for a lake, a lake's level would stand at most 2.5 m over its
  lowest shore, and it is outside the NW patch, whose packed rings NW_WATER replaces. Coping goes on fountains and the
  outer districts' small rings only, and `bankWall` stops at the ground beside it. Everything else is buried as on
  main. That includes East Park's and Belmont's reservoirs, which read 7.8 and 11.4 m of relief on the 150 m DEM.
  Built: 29 basins, 19 ponds and 26 lakes.
- Second: the mirror's 3.5 km reach did nothing, because the oblique near plane leaves the projection with no far
  plane. 1.8, 2.5 and 3.5 km all drew the same 4.85 M triangles at Penn's Landing. `reflReach` now leaves out of the
  pass any mesh wholly past the reach: Penn's Landing went to 2.68 M triangles and Boathouse Row from 6.08 M to 1.85
  M, which is 22 to 60 percent of the scene pass instead of 66 to 85, with the same picture. The mirror is also
  cropped to the water's box on the screen, skipped when no water is within reach, and redrawn every 4th frame for a
  still eye.
- Tests: `tests/test_realism_water.py` (24 checks).

Not done:
- review-should-mirror-p95: I could not measure p50/p95 against ?refl=0 on a weaker Mac: only this machine's headless
  Chrome was available. I measured triangle and call counts per pose instead (in implemented).
- review-should-docs-check: I was told not to edit handoff.md. docs_check.py still exits 1 until the three handoffRows
  below are added at merge. The unit suite passes.
- review-should-phone-shader-measure: I could not measure frame time on a real iPhone against PACE. The only trim made
  is dropping the river's shadow lookup on touch. The two wave taps, env tap, five noises, Beckmann term and 4-wake
  loop are unchanged and unmeasured on a device.
- water#9: (unchanged) The baked shore SDF was not built; the seam is fixed without it.
- night#3: (unchanged) No phone fallback for light pillars, and no SSR.

### Vehicles and street furniture (realism/vehicles)

The realism pass, vehicles. Mike asked for photorealism everywhere, and the streets were the biggest tell: a South
Philly block with no car at either kerb, cars that floated, and a pastel fleet. The traffic now drives the six kinds
lofted from generated side, plan, front and rear views, painted from a real street's mix (white, black and greys
first, in sRGB taken to linear). The buses, trolleys, Amtrak and PATCO wear generated liveries. Near the eye, parked
cars line both kerbs of every street with room for them, each slot's car fixed by its hash, clear of junctions, bus
stops and the hydrants, and gone with the Traffic layer. OpenStreetMap's signals, stop signs, benches and bins stand
at the corners, signal poles 1.6 m behind both kerbs at each street's own width (one width along the bisector stood
Broad Street's poles in the carriageway), with hydrants where the map has none. Every ground vehicle's sun shadow is
projected flat onto the road under a stencil, with a contact shade beneath, so no mover redraws the depth pass. Lamps
are points that read from the front or the back, and a sprite at its floor is now drawn flat: at two pixels every
pixel centre sat out on the falloff, which is why no aircraft ever showed its navigation lights. The aircraft
themselves had drawn black for as long as the flights layer has existed: r149 picks a shared material's program by
instancing, never by instance colour, so the planes read the ships' missing instanceColor as zero. Ships got a lofted
hull in true colours, deck-house windows, container stacks and a wake.

The realism pass, vehicles, the review before the merge. The headlight pools were wired into the end of
lampLightPatch, and under the realistic lamps that function returns before reaching that line, so the 512 map was
drawn every night for nothing. Moving the call into the realistic patch would have added a seventeenth sampler to the
green surfaces, whose programs already used all sixteen texture units, and the roads would have stopped linking. The
pools now come from the end of surfTexPatch and only on the paved surfaces (the lane-painted roads, lots and decks),
which the integration had already relieved of six samplers; on a trial merge every program links and the pool shows on
the road ahead of a van. The vehicles' third of a lamp's light had been a text replace on another patch's GLSL, and
the realistic patch writes that line differently, so the vehicles now have their own patch with the share written in
it. With no mover redrawing the depth pass, a sailing ship's container stacks and the ferry left their shadows on the
water astern for up to a minute; they cast nothing now, and the roof kit asks for its own redraw when it relays. A
parked row now has to clear the outermost moving lane by a van's width: the tertiary lanes move in to 1.3 m, and a
narrow one-way parks one kerb with its lane moved to the other half. The sun's shade on the road reads the shadow map
where it lands, but only where the street itself draws building shadows (the core, and the outer streets once they
receive), because a street that never draws its building's shadow would otherwise show a car with no shadow in plain
sun. Both shades fade with the fog. Trains, and cars on decks and bridges, keep only the contact shade. Cars past 220
m draw their 180-triangle copy and cars past 760 m draw no shades. At the same phone poses as main, triangles are
flat, about 33 to 56 more draw calls, and no frame got slower. The review renders turned up two defects of our own:
stop-sign and bus-stop posts merged from three's indexed boxes without their index, which drew slivers across the
street, and pale outlines on dark cars where the paint mask leaves thin gaps.

Not done:
- vehicles-props#11: People: still not attempted. The effort went to the review's fixes, two new defects the review
  renders turned up (bus-stop slivers, pale outlines on dark cars), and the merge verification.
- vehicles-props#7 (lanes from OSM): Still skipped. Lanes per direction need traffic.b64 repacked, which shifts every
  run's lanes, and there were no renders left to verify that.
- review SHOULD (15 MB of phone textures): Measured and reported, not cut. A quarter-size phone atlas would visibly
  blur close cars at phone resolution, and the masks need all three channels and their mips.

### Night lamps (realism/night-lamps)

Realism round, night-lamps. The lamps now light pools, not a wash. At 5.9 m a texel, Round 140's light map could not
hold a pool: poles 30 to 40 m apart merged into one plateau, and Round 146's cap at 0.5 brought every lit street to
the same grey, so a street at night read like an overcast day. A near map (LAMPNEAR: 1024 px half float over 640 m on
a computer, 512 px over 400 m on a phone, half float wherever the device can draw into it) is drawn from the same
splats around where the eye meets the ground. Each splat has a pool's own shape: a cosine-cubed core from the head's
own height, cut off past 1.8 heads' heights the way a full cut-off head stops at about 60 degrees, plus a 0.10
shoulder. Each lamp is scaled to put on the ground exactly the light its far splat puts there, so the far carpet and a
street's average are unchanged. Surfaces take the light as irradiance times their own colour at LAMP_REAL_K 0.5. Both
maps' gains carry that factor, so the two rebuilds that read the far map with their own patch (Eastern State and the
Reading Terminal) are lit the same as the street outside. A wall reads the ground 2.5 m in front of itself and is lit
up to the height of the heads, and its glass takes a tenth. Measured from 70 m over South Philly: 21 to 26 luma
between two pools against 165 to 170 under a head. The first cut, with no cut-off, left 38 to 57 between them, and the
old wash 116. Two things were wrong in the first captures and corrected before commit. The glare at 1.6 m hung an orb
two or three lanterns wide round every near lamp on a clear night; it is now 0.8 m in clear air and grows to 3.2 m
only in rain, snow or fog. The 8-bit phone near map rounded each colour channel separately, which showed as purple and
green blotches on a pale pavement. Each glow sits at its head, and every arm reaches over the nearest street. The
survey's families (pole_families.json) give Head House and Society Hill their Franklin lanterns and the rowhouse
streets their wood poles. Wet air adds halos to every lamp and takes some saturation and contrast out of the grade,
added to whatever base grade is set. One thing remains: South Philly's streets are pale (the surface patch reads them
as concrete by colour) and their poles are dense, so at street level they still read brighter and more even than real
asphalt. ?real=0 brings back Round 146's wash; __dbg.lampReal(k) tunes the strength.

Realism round, night-lamps. The lamps now light pools, not a wash. At 5.9 m a texel, Round 140's light map could not
hold a pool: poles 30 to 40 m apart merged into one plateau, and a street at night read like an overcast day. A near
map (LAMPNEAR: 1024 px half float over 640 m on a computer, 256 px over 400 m on a phone) is drawn from the same
splats around where the eye meets the ground. Each pool is a cosine-cubed core from the head's own height, cut off
past 1.8 heads' heights the way a full cut-off head stops at about 60 degrees, plus a 0.10 shoulder. Each lamp puts on
the ground exactly the light its far splat puts there, so the far carpet and a street's average are unchanged.
Surfaces take the light as irradiance times their own colour at LAMP_REAL_K 0.5, through uLampReal.y. A wall reads the
ground 2.5 m in front of itself and is lit up to the height of the heads, and its glass takes a tenth. Measured from
70 m over South Philly: 21 to 26 luma between two pools against 165 to 170 under a head (the old wash: 116). Each glow
sits at its head, every arm reaches over the nearest street, and the survey's families (pole_families.json) give Head
House and Society Hill their Franklin lanterns and the rowhouse streets their wood poles. The review found four things
and they are fixed. First, this branch and realism/weather both wrote the composite's saturation, contrast and bloom,
each taking the other's output as its base, and the grade ran away within frames. The wet air's grade, bloom and halos
are now weather's alone, and the glare is a lens's in every weather. Second, this branch had put LAMP_REAL_K into the
far map's shared gain, which also halved weather's wet-street glints and lamp-lit rain. uLampBox.w is LAMP_GAIN over
the store again, and the two rebuilds that read the far map get the factor from a box of their own (LAMP_RB_U). Third,
in fog the fog chunk's mix painted a grey ball the size of the sprite round every near lamp. The glare's shape now
rides its alpha and fades to nothing inside the sprite, and fog dims it rather than tinting it grey. Fourth, ?real=0
had moved the glow and arms too; it is back to the shaft top and the old hashed arms, matching main. A phone's near
map is now a quarter of the memory and is held while the eye only turns, and the 8-bit fallback rounds each splat by
its own remainder so a dark gap keeps its mean. One thing remains: South Philly's streets are pale and densely poled,
so at street level they still read brighter and more even than real asphalt. ?real=0 brings back Round 146's wash;
__dbg.lampReal(k) tunes the strength.

Not done:
- weather#10: Removed from this branch at the reviewer's instruction: realism/weather owns it. That branch's wxGrade
  owns the grade and bloom; this branch had written the same three uniforms with the same constants, and the two hooks
  ran the grade away. wxHaloMesh owns the wet-air halo; this branch's lampHaloU glow halo and its wet-air glare growth
  stacked three halos on each lamp in fog. lampNightFx now writes no post uniform, lampHaloU and LAMP_GRADE0 are gone,
  the glow sprite is Round 54's again, and the glare no longer changes with weather. A trial merge onto
  realism/integrate (git merge-tree, clean) has wxGrade as the only writer of uSat, uCon and uBloom. Rendered in fog
  and rain, the grade holds.
- night#5 (step 6, bloom mip chain): The bloom chain lives in the shared post composite (renderPost/postComp), which
  post-shadows and sky-atmos edit; not touched here.
- streets#10 (Type II stretch along the street): In simulation, stretching each pool along the street refilled the
  gaps between neighbouring heads, the opposite of what the finding asks for.
- night#0 (step 3, HPS share packed in G): The near map stores each lamp's own RGB, so sodium and LED colours already
  mix per lamp.
- night#5 (phones: lanterns, lenses, glare, arm rotation): POLE_MESH_CAP is 0 on phones and they build no ROT (Round
  158 memory cut), so their glow and pools stay at the shaft top. Phones do get the near map and the cut-off pools.

### Weather (realism/weather)

Realism, weather (two commits on realism/weather). The first pass made the wet street a dielectric film, but the
renders showed three faults: puddles read as dark stains by day, a white sun spot sat in the rain at noon, and on a
phone the wet street went white at night. The cause of the first two was the probe. It is dimmer than the dome it is
drawn from and it carries the sun's disc. So the film now reflects the dome's own gradient, taken back through
pUndoColor to the light the composite makes of it, scaled by 1.2 for the deck. The canyon term still stands in for the
buildings across a street. Puddles are a third darker inside a soaked rim: dark from above and bright sky mirrors
toward the horizon, which is how a wet street photographs. The lamps' first streaks were GGX, and the lobe's long
tails laid a broad white column under every lamp at any gain. The lobe is now a narrow anisotropic Gaussian (the
film's roughness along the line of sight, a fifth of it across), broken into glitter by the asphalt grain. The gain
was set by eye on South Broad at 9 pm: 60 is faint, 200 burns white, and 90 was kept. A pool on a wet street loses a
third of its light, since water fills the pores. The phone never keeps a lamp inventory (Round 158), and mirroring the
light map's pools along the ray is what washed its street white, so a phone now draws no streaks and its wet street
simply goes darker. Snow had a pill problem: a flake at the lens drew its whole thirtieth-of-a-second trail at three
and a half times its width. A near flake is now a faint soft disc, the trail is a sixtieth of a second, and there are
45,000 flakes on a computer, so the snowfall reads against a dark wall. Both dials are on __dbg.wxTune({ sky, glint
}).

Realism, weather, the review round. The branch had grown a second name for the lamp map, and once every workstream
merged, the ground programs passed sixteen texture units and every road failed to link. So the branch now sits on the
integration branch and takes its LAMP_WX_DECL. The wet streets read the lamp patch's own uLampMap on a computer, and a
phone's lamp patch declares it as it always did. The lights in wet air had been built twice, once in the night pass (a
grown glow sprite, grown glare and a grade read once) and once in the weather (a halo point and a relative grade).
Every lamp wore two halos, and since the weather ran first, a page loaded in the rain kept its lowered saturation for
the whole session. The weather keeps the only copy. wxGrade is the grade's one weather writer, always relative to its
owners' base, and the halo became the cheap one. It has an angular size, as forward scatter does: 5.2 degrees across
within 187 m, shrinking past that as the core does. It fades by the weather's extinction length (300 m in fog, 450 in
snow, 900 in rain), throws an unseen lamp out of the clip box in its vertex shader, and takes its depth from the
vertex like the glow itself. It is drawn once, empty, on the first frame, so its program compiles behind the veil. Its
strength was set by eye in fog on South Broad at 9 pm: at 0.056 and 0.24 the lamps were dots, at 0.11 and 0.55 the far
lamps ran into one white band, and 0.09 and 0.4 lies between. A dry street now pays nothing for the puddles, which sit
in a branch on the wetness uniform, and a lawn is the surface's own word (surfTexPatch's isGreen), so a brown winter
lawn no longer mirrors like asphalt. By day the rain had all but vanished at street level. It is now 24,000 streaks on
a computer at 2.4 times the alpha, about two pixels across on any screen, which shows on brick and all but goes
against the sky. The snow gives up half as much of its light to its trail and is a shade whiter. Both keep their night
alpha, because at night only the lamp-lit ones should show. Main's snow frames were re-rendered with the preset
snapped: they show its discs and the checkerboard, which are gone here.

Not done:
- perf at the final values: I was limited to five render runs and spent them on before and after, computer and phone.
  Per-frame times (readPixels-synced, 48 frames) were taken with the halo at its earlier 0.056/0.24 and 16,000 drops,
  not at the final 0.09/0.4 and 24,000. The first three runs also ran at the same time and fought over the GPU, so the
  absolute numbers are noise. Results, p50/p95 ms. Computer, main: rain night 57/69, dry night 111/240, blizzard
  126/228, dry day 153/264. Computer, branch: rain night 135/191, dry night 146/231, blizzard 108/152, dry day
  124/174. Phone path, main (contended): rain night 70/116, dry night 74/132, blizzard 64/147, dry day 37/87. Phone
  path, branch (mostly alone): rain night 21.8/34.9, dry night 19.3/32.4, blizzard 35.1/49.0, dry day 43.0/62.5. The
  only trustworthy figure is the within-build delta on the phone path: rain at night costs about 2.5 ms p50 (13%) over
  the same dry night. On the computer the rain night was not slower than the dry night, within noise. __dbg.perf()'s
  own p50/p95 stay empty under the headless renderer, because frameOnce frames are not recorded.
- phone at the final dials: The phone after-run used the earlier halo and alpha. The final values are uniform
  constants on the same code path and were checked on the computer only.
- blizzard veil: The blizzard is denser than before but still sparse at street level. The heavy white veil depends
  mostly on fog distance (sky-atmos) and on the far shells; at 0.7 flakes per cubic metre the near box cannot carry it
  alone.
- screen-space reflections: Out of scope this round, per the task.

## Round 189 — the storefronts' shopfronts (Oct 13)

- Mike: "Do the storefront boxes on Broad Street too." The 2,341 OSM storefronts (storefronts.b64) were still a navy glass
  slab, a dark frame band, a tilted plank awning and a flat sign box each, and the facade shader's style-5 shop floors
  still painted coloured bays with flat awning bands: the cartoon the realism pass took out of everything else.
- The finding that set the scope: the reference view '12-broad-street' stands near 13th and Lombard, 180 m east of Broad,
  and what it shows is style 5's painted bays (no OSM record within 35 m). South Broad itself has both kinds: record 612
  (Oriental Chinese Restaurant, 11.8 m) a white slab with a plank awning beside a style-5 building's red, green, blue and
  white bands; record 606 (Cinemug, 4.7 m) a navy box between two generated house fronts; North Broad's record 1671 a
  grocery box with a mint awning on an office corner. Both are now dressed from one generated atlas.
- The art (fetch_storefront_art.py, gpt-image-2 at high quality): 83 cells, thirteen trades (the kind split by OSM tags:
  takeout from sit-down by amenity=fast_food or cuisine, bakery and specialty food from grocery by shop=) in four width
  classes at 4.2 m tall (S 4.5 m 1024x960, M 6 m 1280x896, L 8.5 m 1536x768, XL 11 m 1536x592), two S and two or three XL a
  trade. 172 calls: 6 dark-glass pilots (kept aside), 3 keyed pilots, 80 frames, 83 edits; no re-rolls. Every one read on
  contact sheets: no lettering, logos, people or perspective; every fascia blank (luminance spread 0.003 to 0.025
  against the 0.07 bar).
- Two stages so the glass is exact. The dark-glass pilots defeated a glass finder (dark wood frames, recess shadows and
  grey frames all as dark as the panes: k-means thresholds, eroded cores and per-blob refinement still took recess walls
  for glass or dropped a pane). So the frame is made EMPTY with every pane a flat chroma-key green, the key is the mask,
  and /v1/images/edits paints the interior into it; the edit redraws the whole image (a board's green shifts, mullions
  inside the dilated mask go), and the bake pastes back only the keyed pixels with a pixel's feather, so frame and mask
  stay registered. The key's green thrown on recessed entrances' sides and ceilings (plain to see in about fifteen cells,
  and every pane's anti-aliased edge) is taken out within
  about 40 px of the glass (green over the other channels by more than 0.05 plus a fifth of the luminance), never off
  the board, and painted green frames keep their colour.
- The bake (bake_storefront_art.py): the board (the longest run of uniform rows from the top quarter, grown sideways),
  the bulkhead's top, the glass head and the board's bottom from the foot, the piers, a door in 81 of 83, the glass 0.16
  to 0.45 of a cell; a 4096x2048
  shelf atlas at 50 px/m in nine rows, WebP q85, a phone's half, and the opaque RGB mask (r glass, g board, b door) at
  half and quarter: art/storefronts/ is 1.56 MB.
- The sidecar (bake_storefronts.py -> storefront_info.json, 110.6 KB, never a repack): names for 2,282 of 2,341 (short
  name first, cleaned, 40 characters at a word); the trades; hours parsed from 1,009 of 1,112 OSM opening_hours strings;
  the layout of records sharing a wall (189 groups, 382 moved, 269 shrunk, 5 dropped; laid on the decoded 0.2 m
  positions with a 0.2 m gap, and grouped by shared wall as well as by overlap, or a pair slid apart ran into the shop
  beside it); the drawn wall over each span (out p50/p95 1/27 cm, in p5/p50 -59/-1 cm). storefronts.b64 came out byte for
  byte (sha256 1c7e5d45 pinned); fetch_shops.py's fetch moved under main() and re-ran in a scratch copy of the tiles to
  an identical shops_raw.json.
- The page: one InstancedMesh of panels (1,513 on a computer, 527 of them dissolving under generated shop fronts as the
  boxes did, 796 on generated street floors skipped, 1 hidden by the layout; 2,054 on a phone) and two of canvas awnings
  (456 flat, 249 scalloped). Each panel at its laid width, 6 cm proud of the drawn wall's outermost point with returns back
  past the innermost, from under the lowest ground to its host's storey plus 0.7 m; the bulkhead and fascia native, the
  glass band rescaled; the interior dimmed under glassOpticsPatch's reflection and shifted 35 cm deep on a computer; the
  OSM name in the page's own type on the board ("Oriental Chinese Restaurant", "Cinemug", "OH BROTHER" checked
  legible), channel letters lit for the shops, banks and groceries, a gooseneck wash for the rest; the interior lit through
  its own picture by the hours on the model clock, a closed shop's display in one in three. The step took 233 ms on a
  computer (112 before: the atlas's upload) and 83 ms on a phone (125).
- The painted shop floors (style 5) wear the same atlas in the facade hook (SF_PARTA, behind uSfOn): whole shopfronts of
  the class that fills the wall with the least stretch, eight cells a class from the trades that suit an anonymous wall,
  lit after dark by their trade's hours (uOcc.w now carries the model's minute).
- Samplers: panels 8 on a computer and 7 on a phone, awnings 5 and 4, the fabric 9 to 11 and 7 to 9; every program
  linked. Phone memory (the GC-normalised gpuhook run): GPU after the look-around 915 to 919 MB, the 1-byte stride-4
  streams unchanged at 54,536. A computer adds about 57 MB of textures (atlas 44.7, mask 11.2, names 1.4, red only).
- Checks: a tap on the 606 panel opens its building's card; ?real=0 renders as HEAD's (clouds and tufts aside); ?sfart=0
  shows the old boxes and painted bays under the realistic look; the phone's far view shows no wall through a panel.
- Not done, to offer Mike: roll-down gates on closed shops (nothing draws them; the second review took out the unused flag), names on the
  generated house fronts' boards for the 527 records that dissolve under them, blade signs for the 796 on street floors,
  shop bases where OSM shops stand, style 6's double-height bays.
- The review (realism, phone and correctness reviewers, then the fixes on the same branch):
  - The painted shop floors kept their paint wherever Part A could not fit whole shopfronts (a wall under 3.4 m tall, a
    short chamfered corner, a wall without its own coordinates): flat grey panes and a striped awning band beside the
    photographs, and a white slab after dark, in Mike's own reference view. Now no style-5 wall is painted once the art is
    up: a wall 2.6 m long and 2.9 m tall takes shopfronts (one S down to 0.58 of its width), anything less keeps masonry
    with the style's sashes. Units along a wall step through the class's eight cells by a stride of 1, 3, 5 or 7, so no
    two side by side share one, and the wall's hash takes its facing (a corner building's faces of one length had all
    worn one cell). Part A's cells pack their atlas corner into one float: 25 uniform rows, not 31.
  - Panels overhung their walls (Greensgrow's pier and awning stood a metre past the corner over a lawn: the bake's 4 m
    minimum on a 3 to 5 m edge) or bridged jogs as boxes up to 2 m deep (179 records with out minus in of 0.6 m or more;
    Ratchada a kiosk with a streaked return). The bake now measures every span on the walls the page draws (wide.b64
    decoded, the core's own rings): sampled every 10 cm, a sample counts where the host's wall is there, in view (nothing
    in the 45 degree cone 3 m deep in front of it) and flush (at most 30 cm proud anywhere, once the wall's lean against
    the record's angle is taken out and handed to the page as a turn, at most 8.5 degrees). The best window in the
    record's room (3 m either side, never past the midpoint to a neighbour on its line) takes the laid width or narrower;
    under 3.4 m it is hidden. 169 narrowed, 429 slid, 904 turned (most by under a degree), 91 hidden for no wall (Ratchada,
    Oneal's, Rudi's, Greensgrow among them, and stalls inside the Reading Terminal), 32 in a shop=mall (Liberty Place, the
    Fashion District: the brick Victorian fronts strung along a curtain-wall tower), out p95 13 cm. A return now wears its
    end's pier wrapped round the corner by depth in metres. 'Pub On Passyunk Eas' was not a neighbour: wide.b64's 0.2 m grid
    drew the host's wall 10 cm out at one end and it stood through the panel; measured on the drawn ring it reads whole,
    and so does SOUTH FELLINI. The sidecar is v2, 9 int16 a record (the turn).
  - A house front and a panel clashed (BP Shop: a front's awning over the panel's board; Cinemug: a residential front's
    raised door over the board) because the near flag was tested at the record's own point. Every test (the custom models,
    the street floors, the fronts) is now at the laid span, the fronts at its ends and middle; a shop front under it
    dissolves the panel near the eye as before, and any other front under it becomes its shop set (149 did), so the two
    never stand on one wall. 676 panels dissolve near the eye (527 before).
  - Identical shopfronts next door (12 adjacent pairs, 32 within 15 m): the M and L classes held one cell a trade. A
    second set was generated (fetch_storefront_art.py: a second M and L a trade, a third S for the groceries, the
    grocery's, shop's and takeout's second M and L Philadelphia corner stores with a gate's box over the fascia and bars on
    the windows, numbered on so no first-set prompt moved). The API's credit ran out after 24 of 27 frames and before any
    of their edits (bakery-L-1, boutique-L-1, venue-M-1 have no frame and are left out), so those cells borrow interiors
    from their trade's own edits (bake_storefront_art.py plates and transplant: each pane's largest clean rectangle,
    scaled to cover each pane, bars and glazing bars kept; contact sheets read clean, no key left). 107 cells; the atlas
    stays 4096x2048 at 44 px/m (at 50 it wanted 4096x2712, a third more on a phone). The neighbour's rule now works on
    laid positions and falls back to the trade's next width within a 0.25 log stretch, then its siblings' (7 borrowed):
    0 panels within 15 m facing the same way wear one cell.
  - The scalloped valance stretched to lobes a metre wide: the scallops are cut in the shader by the metre (a whole number
    of about 33 cm), and the flat and scalloped awnings are one mesh and one program (two programs compiled from one
    shader before; the phone's program count back to the pre-round 121).
  - Phone: the art promise held both decoded images for the page's life (the half atlas and mask, about 10 MB of bitmap
    on WebKit): sfArtP is let go after the race, and no storefront image survives a forced GC after Enter (two did). The
    name cell's canvas is willReadFrequently (the iPhone simulator's copy cost 1 to 2 ms against 2 to 19), the names'
    mips are rebuilt on the last copy that actually runs, the names' setup is caught on its own, and the panels and the
    awnings go into the scene only once everything is made. The art is off at tier 2, like the fronts and the furniture.
  - Look: the glass's band meets a short storey by cutting up to 50 cm off its head (the transom's rows) before it is
    squashed (median storey 3.75 m against the art's 4.2; the panes had read squat at 0.82); the day's interior gain 0.62
    to 0.42 and the coating 0.08 to 0.10 (the shop had read as a lit photograph by day); an open shop's room never darker
    than its ceiling lights (Pub On Passyunk East at 21:30 now reads lit); the parallax held inside its cell; the door
    channel found by a leaf's width (0.5 to 1.15 m, or a pair of 0.25 to 0.8 m) in 106 of 107 cells, none a display
    window. Snow lies on the awnings (held snow, Old City).
  - Measured: computer 1,404 panels (sfBuild 75 ms; the step 310 ms with the upload), phone 1,939 (59 ms; step 96).
    Samplers on a phone: panels 7, awnings 4, fabric 9 (headless); on a computer panels 8, awnings 5, fabric 11, and 15 at
    most anywhere (the ground's, as before the round), by the second review's count (7, 4, 10 and 14 headless, which binds
    one shadow map fewer). Phone GPU (GC-normalised gpuhook run, swiftshader, 740x360)
    869 / 902 / 919 MB at ready, after the first frames and after the look-around, against the pre-round build's 865 /
    898 / 915: still +4 MB. ?real=0 renders as the pre-round build (mean difference under 1 of 255, the tufts aside); the
    old boxes' step is byte for byte the pre-round one less the new path (its sha is pinned in the tests). Tests: the
    sidecar's walls, parse_hours on real OSM strings, and the vertex shader's hours run under node (yesterday's late close).
  - Not done: the curtain-wall hosts' own aluminium cells (the malls' tenants are hidden instead); names on the generated
    shop fronts' boards (676 panels dissolve under them); the iPhone's compile time for the facade program and the RedFormat
    names on a device (the simulator's Safari runs them; TestFlight before a deploy); the three frames the credit stopped.
- The second review (realism, phone and correctness again), then the fixes on the same branch:
  - Five panels on tower hosts stood 1.3 to 1.5 m in front of their wall, Insomnia Cookies on Broad Street a white board
    off the granite base with an open gap behind its end pier (a raycast hit the base 2.52 m behind the record's line).
    bake_storefronts.py held the measured wall's out and in to 1.2 m, and the page tested the street floors 1.2 m inside
    the record's line, still in front of the wall. The bake writes what it finds now (a face is found within SPAN_REACH
    3 m; the int16 guard holds the rest): Insomnia -2.64 m, Girasole -2.75, Talula's Daily -1.47, Talula's Garden -1.42,
    Del Frisco's -1.61, and no other record changed. The page makes every test (the custom models, the street floors,
    the house fronts) 1.2 m inside the wall's measured line, so all five are on their towers' generated street floors and
    skipped like the rest (791 to 796 on a computer; 256 to 260 on a phone, where Girasole's tower has no street floor
    and its panel now stands on the drawn wall, 6 cm proud, not 1.5 m off it); the oblique renders show the base's own
    granite and openings where the board stood. The test that pinned the clamp is replaced by one that no laid record
    sits at it or at the reach, and a node harness that runs sfBuild checks every test point against the sidecar.
  - Phone, the painted shop floors: every pane and door was beaded with the brick's mortar. trimM was set to 1 - glass on
    the shopfront, which left the wall's material g(1 - g) of every mask edge, and a phone (no wall art) drew it as dots.
    The wall's material is kept off the whole shopfront (trimM 1 there); the --touch render of reference view 12 is clean,
    the computer's unchanged.
  - The second set's corner stores went to the wrong trades: the shop's and the takeout's corner frames borrowed the
    groceries' plates, so a stationer and a skate shop showed a bodega's produce and jars and South Side Pizza showed
    grocery-M-1's deli case to the shelf. Only the groceries' corner cells take the bodega now (interior_of for the edits,
    transplant for the plates); the shop's take shelves of boxed goods and the takeout's a counter, stools and a cooler.
    The atlas was re-baked at its size (the mask is the same file). The image API still answered 429 credit exhausted,
    so the real edits for the 24 borrowed cells and the 3 missing frames wait on credit.
  - Part A squeezed one S to 0.58 of its width on 2.6 to 3.4 m walls (half-metre doors on Ratchada's corner): it starts
    at 3.4 m now, the panels' own SPAN_MIN (SF_PARTA_MIN), and shorter walls keep masonry with the style's sashes.
  - The awnings cast their shadows through three's own depth material, which knew neither the dissolve nor the scallops.
    They have their own (sfAwningDepthMat) with the colour program's cuts, the dissolve at the camera's position (the
    shadow pass's cameraPosition is the light's). Rendering only the awnings from the sun in Chinatown: 474 shadow texels
    against 1,938 for the plain material with the eye there, 1,918 against 1,938 with it 100 km off (the scallops).
  - Integer words decoded from varyings are rounded first (the open and sign word, the trade and sign kind, the awnings'
    flags). The house fronts are switched to their shop set only once the build stands (a throw left the old boxes over
    a switched front). The neighbour's rule reads a 16 m grid, not every panel laid. SF_LATE now writes the late-sign
    trades into the vertex shader (it was dead, the shader typed its own list); the unused gate bit and hours flag are
    gone. A cut name drops a trailing connector ('IDK Smash Burgerz &' reads 'IDK Smash Burgerz'). The race's timer is
    cleared.
  - The step's long task: the atlas, the mask and sfBuild were one 320 ms task on a computer. A computer now decodes the
    art into ImageBitmaps off the main thread (flipped as decoded, closed once uploaded; pixel for pixel the same picture)
    and each upload and sfBuild is a task of its own: the atlas 83 to 116 ms (176 from the <img>), the mask 2, sfBuild 75
    to 80; the longest task in the step 109 to 139 ms. A phone keeps its <img> (WebKit's bitmap options untested on a
    device).
  - Measured: a computer 1,399 panels (1,404 before), a phone 1,935 (1,939); 150 fronts switched (149). Programs 148 on a
    computer and 121 on a phone, as before (the awnings' depth program takes the default's place); every one linked.
    Samplers unchanged (headless: panels 7, awnings 4, their depth 0, fabric 10, 14 at most; a phone 7, 4, 9 and 13).
    Phone GPU (the same gpuhook run against 4aa0999): 869 / 902 / 919 MB for both, live heap 136 MB for both, programs
    121. ?real=0 renders as 4aa0999's (mean difference 0.2 to 0.33 of 255: the tufts and a live flight pin). Tests: a
    node harness runs sfBuild over the real records (the test points on the wall line, the faces on it, no neighbour
    sharing a cell, the front switched only by a build that stands, the trimmed names, Part A's stride), 768 OK.
  - Declined: drawing the slot's name on a generated front's board or letting the panel win under a front (676 panels
    still dissolve near the eye, 150 of them over a residential front switched to a shop set: the brief keeps the
    dissolve, and which should win is Mike's call); a chain's own hours for Insomnia Cookies (neither Philadelphia branch
    carries opening_hours in OSM, a typed table would be invented data, and the record now stands on a street floor and
    is not drawn); packing the mask tighter (low on a phone, +0 MB); more uniform room (no uniform was added; the fabric's
    fragment side stays at about 190 vector slots of WebGL 2's 224). Recorded, not changed: a switched front can bring a
    shop set the eye would not otherwise load (17 places, about 5 to 7.5 MB more on a phone while there, within the
    headroom).
- The third review (realism, phone and correctness again), then the fixes on the same branch:
  - Phone (the one must): the art was downloaded and decoded at the top of the build, and both decoded half images
    (2048x1024 and 1024x512, about 10 MB of pixels) lived through the far ring's uploads, the build's peak (276 MB live
    at 'Raising the Towns Across the Line, Uploading') and the window where iPhones have died; neither the gpuhook nor the
    GC-normalised heap sees decoded images, so the second review's +0 MB did not cover them, and tier 1 did it too. A
    phone now fetches only the bytes at the top of the build (sfArtPrefetch: two blobs, 380 KB, nothing decoded) and
    makes and decodes its <img> from them at the step; a fetch that fails (a page opened as a file) asks for the file
    there. The reviewer's check (phone emulation, a forced GC and queryObjects at every loading message): before, both
    images alive from 'Laying Out the Ground' through 'Paving the Lots and Yards'; after, none through 'Raising the Towns
    Across the Line', the two blob images only at the storefront step (sampled under 'Paving the Lots and Yards', which
    only the step can make) and gone by 'Lettering the Streets'; the server saw each file asked for once, at the top. A
    computer keeps its ImageBitmap prefetch.
  - A desktop Safari before 17 or Firefox before 98 ignores createImageBitmap's imageOrientation, and with flipY false
    would draw every panel and painted shop floor from the wrong rows of the atlas: SF_BITMAP keeps those on the <img>
    (three's GLTFLoader draws the same line; the reviewer checked Safari 26.6.2 flips as asked).
  - The awnings' stripes were a fixed smoothstep in fract space, stair-stepped at 20 to 25 m and shimmering further out,
    the house fronts' awnings the same. One helper for both (AWN_STRIPE_GLSL): the stripe box-filtered over the pixel's
    footprint along it (the length of its screen gradient: fwidth's sum read a diagonal stripe up to twice as fine and
    greyed the slope of an awning seen up the street, found in the first render), going to the two colours' mean as a
    stripe falls from 1.4 pixels to under one. The house fronts' awnings take it under the realistic look only (?real=0
    keeps its edge). The Happy Rooster and Marathon renders: soft edges where the steps were.
  - The awnings' cheeks were a flat panel in one colour (the stripe's at their end: a plain white board on a blue and white
    awning seen obliquely). A cheek and a valance's end now wear the stripes upright across their depth, as the cloth is
    cut, a shade darker with a binding along the sloped edge; the slope is lighter toward the front bar it is pulled taut
    over, with a faint sag between rafters a metre apart and a pale crease along the fold, and the valance sits a shade
    under the slope (Together Skateboarding's solid red reads as cloth).
  - A panel on a style-5 wall stood over the facade shader's own shopfronts (Part A) without either knowing of the other:
    at Hibachi 2 Go on South Broad its pier cut a bakery unit through its door frame and the unit's fascia showed 0.3 m
    over its top; Prudential Savings Bank, KFC on North Broad and Green Valley Bank the same. The outer districts' and the
    far ring's wall loops now note every style-5 wall the shader dresses (sfHostNote, 73,989 walls in 16 to 20 ms: the
    records' laid lines in 40 m cells, decoded once by sfPlace, the placement sfBuild makes), with the shader's unit rule
    and its fascia height ported (sfPartTop: facadeFp, rowHead, roofGap, rows and facadeScale); sfBuild takes each run of
    panels on one wall out or in to the nearest joints of the units (sfSnapRun, at least one unit, at most 12.5 m alone),
    seated on the wall's own line and normal, and over the fascia. 817 walls host 823 runs; 814 panels changed span and
    269 were raised (computer). The width classes moved with them (XL 581 to 402, L 119 to 324, M 204 to 312, S 495 to
    361). Hibachi 2 Go, Green Valley Bank, Prudential and KFC now stand between whole units with nothing over their tops.
    The core's walls (buildingGeom) are not noted; its fronts dress them near the eye.
  - The neighbour's rule counted only panels facing the same way within 15 m: 30 drawn pairs within 30 m wore one cell, 8
    facing each other across a street (Ho Sai Gai and Jade Harbor in Chinatown, identical fronts 15 m apart), 5 round a
    corner. It counts any panel within SF_NEIGH_R 30 m now, whichever way it faces: 0 pairs within 30 m, no unavoidable
    repeat, 12 borrowed cells (7 before). 25 m left 17 pairs between 25 and 30 m and saved 6 borrows.
  - On view 12 two Part A units side by side wore one navy frame over two racks of clothes (a cafe's cell and a
    boutique's) and read as one shop of two bays. The shader deals a wall's units an odd stride apart, so the units side by
    side always come from the other half of the places: bake_storefront_art.py now measures each cell's joinery colour
    (frame, between the glass's columns, neither glass nor board) and orders gen so the most alike pairs (that colour, and
    GEN_ALIKE's trades: the shop and the boutique, the restaurant and the cafe, the cafe and the bakery, the grocery and
    the takeout, the restaurant and the takeout) sit on one half (gen_order). The atlas files are byte for byte the same;
    only the manifest moved. View 12 now shows a dark-framed restaurant beside a salon with a white door frame.
  - Trade fidelity: Hajimaru Ramen, Hibachi 2 Go and Oriental Chinese Restaurant showed one white-tablecloth dining room.
    The counters' cuisines (noodle, ramen, poke, dumplings), takeaway=only, a name that says so ('2 Go', 'To Go',
    'Takeout', 'Express') and a Chinese restaurant outside Center City now take the takeout's counter and stools: 28
    records, Chinatown's and Center City's dining rooms kept (Jade Harbor, Ho Sai Gai). A heuristic, said so in the bake.
  - Names: the bake cut at 40 characters and stripped only ' ,-&' ('Greater Philadelphia Health Action Inc.:',
    "Francoluigi's Italian Restaurant & High"). cut_name takes the head before a separator, before an '&' or 'and' joining
    two names, after a word that ends a business's name, before a connector, else at a word, and never leaves a connector
    or separator: 14 names re-cut ('Greater Philadelphia Health Action', "Francoluigi's Italian Restaurant", 'Philadelphia
    Brewing Company', 'Weitzman National Museum'); names that fit are untouched ('Ooh La La' keeps its La).
  - Hours: parse_hours kept Wednesday's span for every weekday, so 'Tu-Su 17:00-24:00' opened on Mondays. Each hours entry
    has a seventh value now, a bit for each weekday the shop keeps shut (Monday the first; a day OSM does not name is
    shut), which the vertex shader reads from the hours' spare fourth float (today's and last night's span both); the
    weekday span is the one most of Monday to Friday keep. 141 of 702 hours entries carry a shut weekday. The limit that
    stays is in the docstring: one weekday span, so 'Mo-We 11:00-21:00; Th-Fr 11:00-23:00' closes at 21:00 all week.
  - The name's slot index was the one integer word not rounded before it is taken apart (slot 4 arriving as 3.9999998
    read row 1, column 3.99): floor(vSfBand.w + 0.5) now.
  - uSfPartU packed each cell's corner as x + 4096 y and the facade shader decoded it with 4096 written in. Both sides take
    the atlas's own width now (SF_AW), SF_PARTA refuses an atlas over 2^24 pixels, and bake_storefront_art.py refuses one
    wider than 4096 (the decode's guard holds to there).
  - The water mirror's reach read the panels' and awnings' geometry sphere, the unit's at the scene's origin, so it cut
    them from the mirror wherever the eye stood more than 3.5 km from the origin and kept them everywhere nearer. Each
    sphere holds its instances now (sfInstSphere); a mirror that is up draws them (2 calls, about 18k triangles).
  - handoff.md had the textures as two freeTexOnUpload'd images: the computer's ImageBitmaps (flipY false, closed in
    onUpdate, tex.image a stub, never re-uploadable), the old-browser caveat and the phone's bytes-only prefetch are in its
    Storefronts bullet and gotchas now, with the Part A host port and the hours' seventh value.
  - Corrections to the record above. Programs: the awnings' depth program is one more on a computer, not the default's
    place (the reviewer's six-pose tour: 144 on the pre-round build, 145 on this branch; a phone casts none, 130 on both);
    this round's thirteen-pose tour reads 148 for both 0f70cad and this fix. The fabric's 'about 190 vector slots of the
    224' is the computer's unpacked upper bound (packed 108 to 133); a phone's is 103 to 129 unpacked, 65 to 90 packed:
    more headroom than recorded. The second report said the 676 dissolving panels' names 'show only beyond the fronts'
    radius'; they never show: sfNamesAssign gives a slot only within uSfK.z (160 m, 90 on a phone) and never to a near
    panel inside frR (380 m, 240), and such a panel has dissolved within 0.8 frR. Now 679 of 1,399 panels on a computer
    carry the near flag and 665 of the 1,367 named never show their name; on Broad Street (30 m either side of its line
    from City Hall to Snyder Avenue) 20 of 35 panels, the Broad and Snyder row among them (Broad and Snyder Pharmacy, The
    Classics Unisex Salon and Hub, Selbe's African Hair Braiding, China Garden, Metro by T-Mobile) under blank house-front
    boards. Whether the front's board carries the OSM name or the panel wins near the eye is for Mike.
  - Phone memory, for context (the reviewer's and this run agree that it is the pre-round build's own): at street level in
    phone emulation (swiftshader, 740x360 at 1.25) the pre-round build already reaches 991 MB GPU on Broad Street (ref12),
    972 in Old City and 973 on Passyunk, over the 981 MB 'known-good' figure, which is the 915 after the overhead
    look-around; the second review's build added 3 to 4 MB at every pose. This fix's gpuhook run against 0f70cad: 869 /
    913 / 930 MB at ready, after the first frames and after the look-around for both, and 1,005 / 968 / 968 / 987 / 987 at
    the five street poses for both (ref12, Chinatown, Walnut, Old City, Passyunk); live heap peak 276 and 277 MB. +0 MB.
  - Measured (computer, headless Metal): 1,399 panels (1,935 on a phone), 658 awnings (233 scalloped), 163 fronts switched
    (150: the snapped spans meet more fronts), near 679 (676); every program linked (148 on the tour, 124 on the phone
    tour), samplers at most 15 on a computer and 13 on a phone as before; 'Dressing the storefronts' 185 to 272 ms;
    'Raising the outer districts' 3,390 to 3,463 ms against 3,377 (a first run after a shader change read 4,189 to 5,412:
    macOS's Metal shader cache, not the notes, which take 16 to 20 ms). ?real=0 renders as 0f70cad's (the boxes pixel for
    pixel; the differences are the traffic and the tufts). Tests: 772, OK with the one expected failure; the node harness
    now also runs the host notes and the snap (a 25 m wall's three units, the joints, the raise), the sphere, the 30 m
    rule, the cut names, the takeout rule and the shut weekdays through the vertex shader.
  - Declined: tiling the panels so the mirror and three's culling could skip them away from the shops (2 calls and about
    18k triangles in a mirror; tiles would add draw calls to every main pass); the names question above (Mike's); the
    core's walls in the host notes (fronts there). Still waiting on API credit: the 24 borrowed second-set interiors and the
    3 missing frames.

## Round 190 — the pins grow smaller as you come on (Oct 14)

- Mike, with a screenshot of the Langstroth marker's pin filling half the view from the sidewalk on Front Street: "Pins need
  to scale down in size as you get closer to them." Every pin (SEPTA, Indego, the aircraft, ships, Amtrak, the ferry, PATCO,
  the closures, the markers and the art, the bus stops and stations, the libraries and rec centres) took the aircraft badge's
  rule (Round 44 gave it to the SEPTA and Indego badges), distance / 135 held at 2.2 at least: past 300 m a pin keeps its size on the screen, and from 300 m in
  it stood at its full 10 by 12.6 m and grew on the screen as the eye came on, fifteen times its far size at 20 m.
- `pinScaleAt(d, cap)`, the one rule for all eleven: the far size on the screen to `PIN_NEAR_D` 300 m (unchanged there, no
  jump at the knee), easing down to `PIN_NEAR_K` of it at `PIN_NEAR_D0` 30 m and closer: 0.6 on a computer, 0.75 on a phone,
  which keeps more to tap. Measured on the Langstroth marker at 1280 by 800: 120 m, about 70 px tall before and 16 after;
  10 m, a 10 m billboard before and a 13 px badge on top of the post after. `tests/test_pin_scale.py` runs the rule under
  node (the far size, the knee, the near fraction, never larger closer in, the caps).
- Coda, the same day. Mike: "The pins now get way too small when you get very close to them. Their minimum size should be
  how they look at a half mile away." The first cut eased a pin to 0.6 of its far size inside 30 m (a 13 px badge at 10 m).
  Past 300 m a pin already held one size on the screen, the size it has at half a mile (NEAR_R), so `pinScaleAt` is now that
  rule all the way in: distance / 135 under each pin's cap, a pin growing smaller in the world as the eye comes on and never
  on the screen. Rendered at the Langstroth marker: the badge at 10 m stands the size of the markers seen from 800 m.
  `tests/test_pin_scale.py` asserts the half-mile size at every distance, computer and phone alike.

## Round 191 — City Hall rebuilt (Oct 13)

- Mike: "I added more api credits with open AI. I want City hall and Glory Beer Bar and Kitchen to be totally revamped", and
  of the city as a whole, that it "looks better, but it isn't where I want it to be". City Hall was Round 81's block: a
  148 by 143 m box to 27 m with a 64 by 59 courtyard, white pyramids for every mansard, a tower of three shafts and a white
  clock box under a stack of pointed frustums, Penn on top. Measured against the building it stood 18.5 m too far south
  (its south wing in South Penn Square's roadway, lawn where the north wing and pavilion stand), its two plan dimensions
  were swapped, its centre pavilions were 41 m against 61.8, its dials white day and night, and its slate read white (the
  shared trim material's metalness of 0.3 lifted 0x51565b by its reflections).
- Sources (the research pass, all in the scratchpad's landmarks/cityhall/refs, never shipped and never sent to the image
  API): NOAA's 2022 QL1 LiDAR at full density over a 220 m box (1.99 M points, 41 a square metre: the roof and cornice
  lines, the tower's slices, the courtyard's walks from the intensity), OSM relation 4720912, Frederick Turner's 1909
  "Illustrated description" (the storey heights, the dial's 26 ft, the statue's 37 ft), HABS PA-1530 (the north front's
  bays, the tower's section), Structure magazine (granite to the basement, Lee marble to 337 ft, slate mansards with
  cast-iron cresting), the Inquirer's account of the two-tone tower (the cast-iron skin replaced with coated plates in
  1984 to 1990, painted light grey), the 2024 LED system (static white by default, colours for occasions, the dials
  yellow on every night), and some fifty photographs on Commons.
- The model (app.js, `CITY_HALL`, `buildCityHallReal` at Round 81's place in 'Raising the outer districts', so the one
  themed slot it takes is taken where it always was): in the building's own frame (B0 on Penn Square, U along the grid's
  fl.n, V along fl.d, one datum, the ground's 0.7 m fall to the north showing as the plinth's reveal). The plan is the
  LiDAR's: 144 by 148.8 m, each front corner pavilion, curtain of four bays, flank of three, the centre pavilion of 27 m
  (the north one standing furthest out, the tower behind it), the 69 by 61.7 m courtyard off-centre to the north with its
  south forecourt, the six round stair turrets, the apse at the tower's foot, the south wing's two light wells, the
  stair blocks on the roof. Heights: the basement 5.57, the principal storey 15.78, the main cornice 26.63; the curtains'
  mansard to its curb at 32.8 and the deck at 36; the flanks' bell mansard to 39.4; the centre pavilions' attic cornice
  at 39.28, their shoulders to the body roof at 49, the crown to 57, its iron cresting to 59.6, the finial to 61.8 and the
  pole to 73.5; the corner pavilions' cornice at 38.13, their mansard's curb at 45.4 and the cap at 48.8. The tower: the
  base in the courtyard to 26.6, the batter to 40, the shaft with its rusticated piers to 64.5, the first balcony on its
  brackets, the stage of the tall arched window to 87.5, the upper balcony all round, the belvedere with its clustered
  columns to the marble's end at 102.8, the painted clock stage to 123.4 (square to 117, an octagon above), the octagonal
  dome on the measured profile to 142, the lantern's drum with its eight ribs, the gallery, the cupola to 155.6 and Penn
  to 167.0.
- The facades are photographs (fetch_cityhall_art.py, gpt-image-2 at high quality, 19 calls: 18 kept and the first
  clock, whose dial stood in the top half of the face, set aside): straight-on elevations of a wing section of four bays,
  the three bays beside a centre pavilion, a centre pavilion's front, a corner pavilion's face, the courtyard's wall, the
  tower's three masonry stages, the clock stage, a face of the dome, the three dormers and the oculus, a turret's head, the
  apse, a balustrade and plain ashlar, every pane a flat chroma-key green, the centre's great arch a flat magenta, the dial
  a flat green disc with no numerals. Each read before the next batch: orthographic, keyed clean, no lettering, the
  marble warm white. bake_cityhall_art.py keys the glass and its spill, fills the panes with dark glass and a sash's
  meeting rail, calibrates each picture's stone to the photographs' marble (0xc9c4b8) and the tower's paint, takes each
  picture's storeys to the building's (so the painted string courses meet the cornices built at 5.57, 15.78 and 26.63),
  measures the arch (5.0 m wide, its crown at 8.6) and the dial (its centre at 109.6 m, 7.5 m across), and carries the
  free-standing columns measured by hand on the centre, corner and flank pictures; one 2048 atlas at 26 px/m and a mask
  at half (r glass, g the window's number, b the dial, a void, the balustrade's sky), a phone's halves: art/cityhall/ is
  832 KB (a computer downloads 660 KB, a phone 172 KB).
- Whatever stands proud of a wall wears the wall's own picture projected straight on (`proud`, `moulding`, `column`): the
  cornices as extruded profiles (the main cornice 1.1 m out, 1.4 m tall), the columns as half-round shafts with capitals
  and bases on the painted ones (12 on each centre pavilion, 8 on each outer face of a corner pavilion, 2 on each flank),
  the balconies and their brackets; so the relief and the painting agree from any side. The portals are real openings
  with their passages to the courtyard (the cast-iron vault grey, darker toward the middle, warm under its lanterns at
  night; the north one under the tower to the apse's door). The slate takes the pitched roofs' generated slate along its
  slope with its courses; the cresting is the balustrade's picture cut against the sky. The courtyard is its red pavers,
  the darker cross of walks between the portals and the painted compass (no letters), the apron round the building
  granite, both one canvas on the drawn ground.
- The tower's paint is a shade greyer and cooler than the marble (the two-tone tower). The dials are their own mesh: a
  canvas a dial drawn by the page (the teal glass of its panes, the gilt chapter ring, sixty marks and the Roman
  numerals, the white moulded ring), their hands set to the model's clock once a minute, and after dark a deep yellow on
  the lamps' photocell, never themed (the photographs' yellow dial on a red tower). Penn is Round 84's postcard figure
  with its arms mirrored (the photographs show the RIGHT arm out over the city and the charter in the LEFT hand against
  the hip, on a tree stump behind the left leg: Williampennfront.jpg and Williampennleftside.jpg), at the statue's own
  11.4 m between 155.6 and 167.0, his bronze stored darker (Round 84's rendered about 0x554e3e in the realistic look's sun
  against the photographs' 0x3a3228). The four eagles stand over the dials and four three-figure groups on the diagonal
  corners at the dome's foot, all on the themed mesh, the eagles and groups taking less of the floods than Penn. The US
  flag flies on the north pavilion's pole (the shader's stripes and canton, no texture).
- The night: `cityHallFloodPatchReal` is Round 109's soft pools moved onto the measured plan (the corner pavilions, the
  four centre pavilions and a column up the tower from its roofs to Penn's feet), never on the glass, the tower at full
  strength and the block at 0.8; the plain-night colour is still Round 109's amber (`CH_HOUSE`; the 2024 system's default
  is a static white, about 0xf3ead9, one constant if Mike wants it), a themed night washes it in the theme's colour as
  before. A share of the windows' rooms is lit by the hour (0.42 of the towers' office share, `skinLateAt`: about one in
  seven at half past nine).
- Cost: one program for both levels ('city-hall-real'), two small ones (the dials, the floor). Near (within 650 m, 420 on a
  phone, 40 m of hysteresis): 15,929 triangles (14,905 on a phone: six-sided columns), the dials 144, the floor 258; 3
  colour-pass draws and 1 shadow-pass draw more than with it hidden (the A/B at d_mid_nw on a computer and at p_d_mid_nw
  on a phone). Far: 3,401 triangles in 1 draw, 1 in the shadow pass. Budgets 60k / 30k near, 6k far, 7 calls: met. The
  bronzes are 95 parts on the shared themed mesh (Round 81's City Hall shares were about 2.9k triangles). Textures: a
  computer 26.7 MB for the atlas and mask with their mips (the dials' and the floor's canvases about 8 MB more); a phone
  6.7 MB and nothing until it comes within 1 km; tier 2 never loads the art and draws the far level from the cells' mean
  colours. Every stream a multiple of 4 bytes (the colour four normalized bytes).
- Integration: the outer districts' loop leaves OSM's outline grown 2 m to the model (`CITY_HALL.ring`; the old 24 m skip
  circle stays for ?real=0), the wings hold `REBUILD_OCC` (no tree, pole or storefront; the courtyard's trees stay), the
  roof grid has the crowns, the caps and the tower, the courtyard and apron are kept off the tufts. The viewpoint, the orbit
  target, the skyglow point, the locate fallback, the label, PATCO's stop and the pins (the shell hides them) are as
  they were: the tower's axis is (-1602.44, -801.19), within a metre of the old (-1603, -802).
- ?real=0 renders as the pre-round build at d_mid_nw, n_plain_mid_nw and d_nbroad_street (the differences are the live
  flights' pins and the traffic); `cityHallFloodPatch` is byte for byte the old (tests/city_hall_gpu.html cuts it). Every
  program linked in every render (no console errors). Renders: before/ and after/ in the scratchpad's landmarks/cityhall,
  27 computer views (day, dusk, a plain night, the calendar's teal, an Eagles night) and the 3 phone views, with pairs.
- Tests: tests/test_landmark_cityhall.py (the table, the one slot, the gate, the old block and its flood patch pinned, the
  manifest's cells and what the page builds to them, the level's constants, and chModel run under Node: both levels'
  budgets, sound indices and normals, the tops within half a metre); test_art_files and test_memory_cuts follow the new
  art and canvases. 787 tests, OK with the one expected failure.
- Not done, to offer Mike: Dilworth Park is still lawn (the real one is mostly a granite plaza with the fountain and the
  cafe); the plain night's amber against the LED system's white; the courtyard's lanterns and the ornamental gates of
  2015; the figure groups and eagles are simple forms; the cresting and the balustrades cast solid shadows (three's own
  depth material knows nothing of the cut); Penn's figure is still Round 84's primitives.

## Round 191, the review's fixes (Oct 14)

- Two reviews of the rebuild (the integration and the realism critics) found it sound in plan and heights but broken in
  ways a Philadelphian sees from the street. Every must-fix is in; the should-fixes are in but two (below).
- The dome floated. The clock stage's octagonal head (117 to 123.4 m) was walked with its outside on the left: the loop
  swapped its corner names and swapped them back in the call, so all eight faces looked in, were culled from outside, and a
  band of sky 4 to 6 m tall showed between the dials and the dome's foot from every street (the eagles and the groups hung
  in it). `face(A0, B0)` now. A node harness cast 6,000 rays at the model from round it (the street, a flight round the
  tower, the skyline) and counted every first hit that was a back face: 163 near and 180 far (2.7 and 3.0 per cent). Behind
  the octagon it found the rest: the upper balcony's slab with no soffit, the lantern's gallery likewise, the 1.5 m band
  between the shaft's head and the stage of the tall window and the 2.2 m one between the upper balcony and the belvedere
  (both open all round), the ledges where each narrower stage stands on the one under it, the dome's head under the drum,
  the clock's columns open at both ends, the dome's ribs standing off its corners with no cheeks, and on the block a slot
  at the foot of every mansard (each profile started 0.4 to 0.6 m in from the wall, and the cornice under it closes on the
  wall's line), the courtyard mansard's 0.5 m slot, every cornice's open back where it runs past a wall's end, the passages
  standing 5 cm proud of both walls, and the north passage crossing the courtyard's north wall and the tower base's south
  face. All closed (`ledge`, `band`, `cyl`'s soffit, `hipRoof`'s ledge, `moulding`'s back): 3 of 25,000 rays near and 8 far
  (the far level's flat trims at grazing angles), none over 60 m. tests/test_landmark_cityhall.py runs it on both levels on
  both devices and also checks that every wall of the tower over the roofs faces away from its axis.
- The centre pavilions' roofs (the main elevation from Broad and from Market) are rebuilt to the photographs (S Broad at
  Locust, Market Street, HABS's 1982 elevated view of the north front, the 1965 and 2019 aerials): the crown, a narrow
  mansard rising straight from the middle bay's cornice (13 m deep, 2.2 m of batter on every face) to a bracketed cornice
  box at 53.6 to 57.0 m, its pyramid to 59.6 with the cresting round its foot, the finial to 61.8; its hips in broad carved
  white trim (1.1 m, beaded by the shader); the caryatid aedicule climbing its face to 50.6; either side a segmental
  shoulder, a quarter-ellipse of slate from the pavilion's edge at the cornice to the crown's face at 46.1, its lunette on
  the front framed in a 0.95 m carved curve with its oculus; behind them the body's attic in stone with its cornice at 49
  and the old straight mansard down its sides. The LiDAR's 49.0, 57.0, 59.6 and 61.8 stand. Every other mansard (the
  wings', the flanks', the corner pavilions', their cap stages) has its hips and its curb in carved trim (`rib`), the corner
  caps are the white cornice boxes the aerials show, and the curtains carry the hooded bull's-eyes over their dormers
  (the photographs' green copper bonnets are hoods on small upper dormers, not on the big ones).
- The bronzes were khaki: as the themed parts' matte paint even 0x150f09 rendered about rgb 115 in the sun. They carry a
  negative gain now, which the themed mesh's shader takes as patinated bronze (metalness 0.62, roughness 0.42) and every
  other themed part ignores; stored 0x0b0906. Penn's median in the S Broad telephoto is 60, the haze floor there (the
  belvedere's black arch at the same distance reads 60); the groups and the eagles near black on the low flight. The night
  flood is untouched.
- The portals: the light-blue specks round the east arch were the balustrade's discard firing on the mask's filtered edges
  of the arch's void (b 120 through the band 0.16 to 0.33); the discard now lives only in a second program for the
  balustrades and the cresting, gated on their own cell (`chSplit`, `chMaterial(.., true)`), so the building keeps its
  early depth test, and its shadow cuts the same way (`chCutDepth`: they cast solid boards before). The courtyard's holes
  stood 0.35 m off their passages (the bay's centre, not the arch's); they are cut to the arch's own centre now, and the
  string course and the water table stop either side of every opening. The north passage ends at the tower's foot in a
  wall with a door of 3.26 by 4.2 m, which the apse's two middle facets open on the courtyard through a short passage of
  its own (it stood out of the apse as a black slab). The passages wear the ashlar on their walls, a coffered vault with
  a rosette in each coffer, granite setts underfoot, and their shade is now the sky they cannot see (the colour's fourth
  byte multiplies the indirect light; as an albedo it left the walls at 125). Their floors ride the drawn ground: the
  ground round the building stands 2.0 to 2.9 m over the courtyard's (Y0, the building's datum) and the apron drawn under
  the wings showed through them.
- The courtyard is the photographs' dark red-brown brick (0x6a2f23 on the canvas, about rgb 99, 51, 47 in shade against
  their 94 to 103, 49, 47 to 52), the shader laying 0.2 by 0.1 m pavers in a running bond with their own shades and sand
  joints and 1.5 by 0.75 m slabs on the granite walks, both faded by footprint.
- The rest: the far level keeps the aedicules, the great dormers, the shoulders' oculi, the crowns' and the shoulders' trim
  and the flag (the switch at 650 m changed the silhouette most there); the decks take the flat roofs' generated tar with
  a lapped seam every 0.9 m and twelve glazed ridge skylights; the bake keys any green standing 35 over the other channels
  and 1.6 times the larger (the arched windows' shaded heads kept a band of it: 1,012 pixels in the flank cell, none now),
  calibrates the tower's masonry to (187, 182, 170) against the paint's (188, 192, 198) (S Broad at dusk reads the
  belvedere (149, 152, 143) under the clock's (154, 165, 169)), and fills the portal's arch with the passage's shade; the
  lantern's drum has its ring of framed oculi; the river's mirror draws the building (the weather is `wxSurfacePatch`
  patched in, not `userData.wxSurf`, which marks a flat and kept the walls out of the mirror while the dials and bronzes
  stayed in it); the dials' bounding sphere is taken with the hands on the dials (it was 905 m round the origin); tier 2
  takes the half art within 420 m (it was a windowless cream box from the street); Dilworth Park's café, which OSM's
  footprint drew as a three-storey house before the south-west pavilion, is skipped in the outer districts' loop (as
  DEMOLISHED is) and built as a single storey of glass. The loop's old skip of City Hall's outline never fired (the outline
  was dropped at pack; the tower's parts go with BRIDGE_SKIP) and is gone; it would have thrown had it fired, the loop's
  own CH being the chunk size.
- Not done: the 2048 by 1536 atlas (the cells with their gutters fill 85 per cent of the 2048 square; at 1536 the packer
  reaches 22.3 px/m against 25.9, and a height that is not a power of two is resized to one on WebGL 1); a better Penn and
  figured groups (to offer Mike: coat skirts, the hat's brim, the charter and the stump; three figures a group). Penn's
  arms stay as the photographs show them (the right arm out), which changes Round 84's postcard figure: Mike's yes is
  asked for. The plain night's amber against the LED system's white is still his call. The ground round the building
  stands 2 to 3 m over its datum, so the water table and part of the basement are under the sidewalk on all four fronts;
  whether the courtyard is that much lower than Penn Square, or the DEM is wrong under the building, wants a survey.
- Cost: near 23,853 triangles on a computer and 22,589 on a phone (the trim, the shoulders, the closures and the café),
  the cut-outs 192, the dials 144, the floor 258; far 4,312. At d_mid_nw the A/B adds 6 draws near (the near mesh, the
  cut-outs, the dials and the floor; the near mesh and the cut-outs in the shadow pass) and 2 far, on both devices.
  Budgets 60k and 30k near, 6k far: met. Textures as they were (26.7 MB a computer, 6.7 a phone). No console error in any
  render. ?real=0 matches the pre-fix build but for the live traffic and the tufts. 791 tests, OK with the one expected
  failure.

## Round 191, the second review's fixes (Oct 14)

- Two more reviews (the realism and the integration critics) on the fixed rebuild: the plan and the heights stood, but a
  Philadelphian from the street saw a buried basement, a blank tower shaft, chess-piece bronzes, glowing passages, blank
  boxes over the courtyard, a cartoon compass and a viewpoint that did not show the building. Every must-fix is in, and
  the should-fixes but one (below). The round is renumbered 191: main's Round 190 is the pins' scale.
- The ground. NOAA's 2022 LiDAR's ground returns put the courtyard at 13.91 m (NAVD88) and the sidewalks round it at 13.06
  to 13.22 (north), 13.61 (south), 13.39 to 13.51 (east) and 13.58 (west): the courtyard stands 0.3 to 0.8 m OVER the
  street. NED, which the drawn ground is, had a 2.7 m pit in the courtyard and pulled the fronts 0.4 to 0.7 m down with
  it, and the building stood on the pit (its datum 2.47, the drawn ground 4.5 to 5.4 at the fronts): 1.75 to 2.9 m of the
  5.57 m basement was under the pavement on every front. Under the realistic look `demAbs` now takes `CH_GRADE`, a plane
  fitted to the LiDAR's ground within 4 m of the walls (13.473 m at the centre, 0.00318 a metre to the south and 0.00083 to
  the west; rms 0.15 m), out to 10 m beyond the building's box and eased back to NED by 40, so the streets, the apron and
  everything siteY seats move with it; the building stands on the measurements' own datum, 13.57 m (Y0 5.23 against
  2.47). Measured at the fronts against the datum: north -0.40, south +0.10, east -0.21, west -0.08, the north-east corner
  -0.42. Every face on the datum is carried 1.2 m under it in its picture's foot row (`foot`), the water table runs from
  the pavement (it stood 1.5 to 3.0 m up, across the basement's windows), the courtyard is laid flat at its own level
  (`court0`, 0.34 m over the datum), and the passages run level from the pavement at the mouth to the courtyard's floor.
  The whole granite storey shows on every front, its arched windows whole and the portals tall.
- The tower's shaft (40 to 64.5 m, the largest surface on the building) is a new picture: channel-jointed courses across
  the whole face, three slit windows low, a string course, and the great tripartite window with its arched lunettes a
  third of the face wide (the photographs from the courtyard's south entrance and N Broad Street). The battered base wears
  the same courses (`rustic`, a new tile) where it wore the old picture's foot. The belvedere's arch is a narrow glazed
  window with mullions (it was a black hole twice the photographs' width). The apse is the photographs' plain banded half
  drum: three oculi under a moulded cornice, three narrow windows in blocky Gibbs surrounds, a granite base with its door
  in the same surround; the page cuts the door where the picture paints it (2.04 by 5.16 m), builds the surround's jambs,
  lintel and keystone proud of the two facets either side of the apex, and runs a real cornice round its head.
- The courtyard: 'court' (the plain office grid) only on the north face by the tower and the forecourt's sides; the east,
  west and south faces in `court_main`, tall sashes and great arched windows on the principal floors; over each passage's
  courtyard end the bay (`court_bay`, 14 m: an arched window over a columned one over a pedimented door, the passage's own
  small arch at its foot, 20230419181543 and _181701). The passages end 0.7 m inside the courtyard's wall in a wall with
  that small arch and its reveal (the great arch ran straight through). The centre pavilions' bodies over the wings,
  the blank boxes over every courtyard view: their backs are the mansard the 2019 aerial shows, three framed oculi in it,
  and their walls below take their picture at its own size to the attic's cornice. The compass is its own canvas
  (`chCompassCanvas`, 18 m at 57 px a metre, 43 on a phone): the muted steel blue and navy star of thirty-two points, tan
  points between, a white sawtooth rim, and Holme's 1682 grid between the two rivers in the middle with the year in a
  roundel (it was a saturated blue disc with a four-point star at 6.4 px a metre); the floor shader's test for the grey
  granite missed the walks (they drew flat), so they now lay their slabs with their joints and their own tones.
- The passages: the facade's flood no longer reaches inside (a passage's part carries its shade under 1 in `aCol`'s fourth
  byte, and the flood is multiplied out by it; it lit the west passage a flat beige on a plain night and teal on a themed
  one); they have their own dim warm lanterns, strongest by the mouths. By day their walls take the vault's occlusion,
  darker toward the middle and toward the springing (at the south mouth the wall reads 112 low and 87 high against the
  vault's 42, where it was 158 against 50), their courses and blocks are drawn by the shader so a phone keeps them, a dark
  granite base course runs along the floor, and the floor meets the courtyard's level, no step.
- The bronzes: one group of three draped figures (a man with his arm raised over the city, a woman with a child against
  her, robes, mantles, heads, arms from shoulder to hand) and one eagle with fanned, notched spread wings, modelled once and
  laid four times each in the themed mesh's one draw (about 860 and 110 triangles). The bronze is stored lighter, 0x221c15,
  at metalness 0.82: as 0x0b0906 Penn's coat measured (16, 18, 17) in the sun, flat black; it now shows its form.
- The lantern (Philadelphia_City_Hall-zoom.jpg; the LiDAR saw nothing under the gallery's overhang): a short neck off the
  dome's head, the ring wall out to the gallery's line with its mouldings and band, the glazed gallery behind its railing
  under a projecting roof, the fluted cupola and Penn's pedestal (it was a 7.5 m can with two dark oculi like eyes).
- Realism: every pane has its dark sash frame, meeting rail and a muntin down a wide one (the bake, none of it glass in
  the mask) and at night a room behind it (its ceiling lit over a darker floor from the pane's own height, which the mask's
  blue now carries; a blind part way down in some; they were flat beige cards); the slate is a neutral charcoal and the
  decks a dark tar (they read blue); the block's marble is weathered, (182, 176, 164) where it was (201, 196, 184), its
  recesses sooted in the bake and its lower storeys dirtier by the height, the tower cleaner (190, 186, 176); the stone
  darkens in the rain; the gallery's, the skylights' and the glass houses' glazing has bars.
- Dilworth Park: the two windowless beige boxes across the lower west front were the concourse's headhouses (OSM's
  building=roof canopies): skipped in the outer districts' loop like the café (`CH_HEADHOUSE`, wideColK counted) and built
  in glass (`chCafe`); the west front is paved in granite to the plaza (the lawn ran into the portal's mouth), and no park
  tuft grows on City Hall's paving.
- The 'City Hall' viewpoint and the locate fallback stand on Broad Street's axis, 430 m south of the building and 80 m
  up, aimed at the tower (130 m east of the axis it was a wall of towers).
- Integration: the cut-outs' own program is folded back (under the log depth buffer every program writes gl_FragDepth, so
  it kept no early depth test for the rest; it cost a colour draw, a shadow draw and a program), the cut gated on the
  balustrade's cell, `chCutDepth` the near level's shadow; the near level switches at 400 m on a computer (at 650 it is 40
  px wide; the far level now keeps the wings' dormers and the flanks' trim, and the levels forced at 400 m differ on 0.5
  per cent of the pixels by more than 24 from the north and 1.6 from the west, most of it the traffic between the two
  shots; 0.36 per cent at 760 m); a failed build takes back its meshes, themed parts and ground claims and lets Round 81's block
  stand (`chBuildSafe`: the landmark block in the outer districts' step has the loop's own CH, the chunk size, so it names
  none of City Hall's state); the stale tier 2 comment is gone.
- Not done: Penn up close is still Round 84's primitives with the arms the photographs show (to offer Mike: the coat's
  skirts, the hat's brim, the charter and the stump); the plain night's amber against the LED system's white is his call;
  the near and far levels share no LOD for the bronzes (they ride the themed mesh, one draw at any distance, 3.9k
  triangles).
- Cost: near 25,458 triangles on a computer (24,194 on a phone) with the café and the headhouses, far 5,817, the dials 144,
  the floor 252. At d_mid_nw the A/B adds 4 draws near (the near mesh in colour and shadow, the dials, the floor; it was 6)
  and 2 far, on both devices; 51.2k triangles near on a computer, 48.8k on a phone, both passes. Programs: city-hall-real,
  its cut depth, the dials, the floor. Art: six gpt-image-2 calls at high (the shaft, the belvedere and the apse made
  again, the old ones kept in the raw cache's aside/ as _v1; the courtyard's two cells and the courses new), 21 cells at
  25.1 px/m in the one 2048 atlas; art/cityhall/ 886 KB (a computer 699 KB, a phone 187 KB); textures 26.7 MB on a computer
  and 6.7 on a phone, as they were. ?real=0 renders as before but for the traffic and the tufts.
## Round 191, the third review's fixes (Oct 14)

- A third pair of reviews (the realism and the integration critics) on the rebuild: the plan, the ground and the
  pictures stood, but the clocks ran backward, the water table wore the windows, the sun leaked into a passage, the
  bronzes and Penn were still stacked primitives, a deli stood on Dilworth Park and its glass houses were black slabs.
  Every must-fix is in, and the should-fixes but the ones named at the foot.
- The dials. `chDials` laid every face's 3 o'clock along (-nv, nu), which is the viewer's LEFT: every dial read IIX at
  its head with III at nine, and its hands ran counter-clockwise (at 14:00 the hour hand stood at ten). Facing a face, the
  viewer looks along -n with y up, so his right is -n x y = (nv, -nu); `chDialFaces` gives each face's frame and the
  canvas and the hands share it. A Node test turns the hands to 15:00 on every face: the hour hand to the viewer's right,
  the minute hand up, III to the east on the south face. Against the 2025 photograph the numerals now fill the chapter band
  (0.635 to 0.915 of the radius, tall and condensed on their radii; they were half its size in a ring of sixty minute marks
  the face does not have), and the glass's twelve radial bars and three rings are drawn only on the glow (lit from behind
  at night), never by day.
- The water table and the feet. The band wore the wall's picture projected straight on, so where the basement's arches
  come down below 1.5 m (the flanks' to 0.74 m, the corner pavilions' to 0.94) their lower panes were painted on a
  projecting stone band and cut off at its head, at eye level on every walk past; the 1.2 m `foot` under the datum
  stretched the picture's bottom row into streaks on the plinth. Both are now the base course's own granite (a new tile,
  `ch_granite`, calibrated to the painted basements' grey), by the metre along the face (`vG`), and the band's head stands
  0.12 m under the face's lowest sill as the bake measures it (`sill` in the manifest, `waterTop`: 0.62 on the flanks, 0.82
  on the corner pavilions, 1.5 on the wings and the centre pavilions).
- The passages. A jagged sunlit strip ran the length of the north passage at the foot of one wall at 14:00 with the sun
  south-south-west: shadow-map leakage at the wall and floor. A passage's direct light now goes with the shade its part
  carries (`chSun`: whole at the mouth's 0.72, gone by 3 m in). Their walls are a new picture of the vestibules' own
  rusticated marble over a granite dado of diamond-cut panels (`ch_vest`, 20231007134150), a pair of engaged polished red
  granite columns on grey granite bases with marble capitals every 6 m (9 on a phone), a rib over each pair across the
  vault (a computer's), a lantern of lit glass hung on a rod from the crown between pairs, and the floor a border of small
  tesserae along the walls round a field of two-toned slabs on the diagonal (the floor's width rides its seed). At night
  their own lanterns' light is a little dimmer on the lighter marble.
- The bronzes and Penn, now forms (`CHS`: shells of rings with a ripple of folds round them, tubes along a path, blobs,
  lathes; smooth normals, laid in a figure's own frame). The groups (`chGroupForm`, 2.4k triangles, 1.2k on a phone): a
  man with a staff raised, his robe and mantle in deep folds, his hair and feathers; a woman in a shawl drawn over her
  head, a child on her hip; a dog at their feet; on the tower's own white drums on the octagon's chamfered corners
  (`CH_PED`), where they stood on black bronze boxes. The eagles (`chEagleForm`, 0.7k): an upright body on its talons on
  the stone over each dial, the head turned and the beak hooked, the wings 0.1 m thick and fingered, facing front, raised
  46 degrees to a span of 3.7 m (12 ft; they were 2 m bat wings on a post). Penn (`chPennForm`, 3.3k, 2.0k on a phone), at
  the pose Mike approved from the postcard: the broad-brimmed, low-crowned Quaker hat over long hair; the coat flaring to
  the knee in folded skirts, open over a waistcoat; tapered sleeves to big turned-back cuffs; the right hand open and palm
  down over the city; the charter rolled in the left fist with its loose end hanging; breeches, stockings, buckled shoes;
  the stump behind the left leg. All on the themed mesh's one draw, 15.7k triangles on a computer and 9.0k on a phone.
- Dilworth Park. The one-storey box at the plaza's north-west corner that the storefront pass dressed as a deli (red
  awnings, 'Dilworth Park Café' and 'Dilworth Park Farmer's Market') is OSM's way 333931838, building=retail, with the
  Dilworth Park Café's node in it: the park's café is that north pavilion of glass (OSM's south-west building, the one
  `CH_CAFE` takes, is a kiosk). It is the third `CH_HEADHOUSE`, skipped in the outer districts' loop and built in glass, its
  ring in `REBUILD_OCC` so no storefront panel hangs on it. The glass houses were opaque near-black panes behind a stark
  cream grid that the lamps lit into a wireframe at night, cream even on a red night. The pavilions' glass is its own kind
  now (14): by day the daylit room and plaza through it by Fresnel's share, darker at the stairs' foot, and a stronger sky
  reflection; at night their interiors lit, ceilings brighter than floors; slim dark steel mullions every 3 m; a thin pale
  roof slab standing out 0.45 m; never the facade's flood. The lantern's gallery and the skylights keep their bars, dark
  steel now.
- The crowns, the lantern and the night. The centre pavilions' cornice boxes, dead centre under the tower in both axial
  views, wear a new picture (`ch_crown`: a frieze of eleven carved consoles, dentils and a deep cornice), the consoles built
  proud where the picture has them (a computer's), and a pediment with its masked tympanum built on each face's cornice to
  the picture's measure (`ped`), the cresting stopped either side of it. The lantern's ring wall has two moulded courses
  and sixteen consoles under the gallery's floor; the gallery has twelve piers with its glass set 0.3 m back between them
  (it was one black glazed band with a white grid, an airport's control tower). The night's flood takes `1 - max(ny, 0)`,
  so an uplight lights a soffit: every string course and cornice underside drew a hard dark stripe. The bake keeps a
  window's number and height on its sash bars and runs them a few pixels over the stone round it: filtered, a bar's 0
  read as another window's, and the night drew every basement sash a dotted line of lit and unlit rooms.
- The courses, the floor, the apron and the courtyard. The tower's batter and shaft read as siding under an overcast:
  the bake now tones each block of the channel-jointed courses its own (sd 3.5 per cent) and cuts in the staggered head
  joints the picture left out (in the picture rather than the shader, where they cost nothing and line up with its
  courses). The floor's slabs keep their own tones out to where they are two pixels across, their joints a softer grey
  fading before they alias, the granite's speckle and the wear of the traffic in broad patches; the compass is painted
  on the same slabs, through their joints and grain, a little dulled. On the apron, the generals McClellan and Reynolds
  on horseback flank the north portal and Wanamaker, Bullitt and McKinley stand on their pedestals (OSM's nodes; the
  forms in a metallic bronze, the pedestals in the base course's granite, in the near level), with bollards along the
  north curb; in the courtyard, eight black lamp posts by the passages' ends and the apse, a lantern on each turret, the
  iron railings round the areaways either side of the passages' ends (a computer's), and at night the lamps' pools on
  its floor.
- Integration. A phone paints the floor's two canvases on its first near frame (they were uploaded at the build on every
  phone, 4.5 MB whether or not it came near City Hall), the compass at 512 px (28 px a metre). The pins' depth image and the
  building tap draw the far level in the near one's place (`userData.occStandIn` in `occRender`): it is drawn every frame
  in flight. The far level's four portals are a recess of the passage's tone, where they were the picture's black arches
  and flipped at a phone's switch. A failed build also gives back the ground its drapes took from the tuft sow and lets
  Dilworth Park's pavilions stand as boxes. The 'City Hall' viewpoint, the locate fallback: 300 m up on Broad Street's
  axis 330 m out, over the canyon's towers, the whole block and tower in view (80 m up and 430 m out the canyon's walls
  filled four fifths of the frame).
- Not done, and why: the sun's shadow keeps the near level (the far level's would take every cornice's shadow off the
  walls); trees and tables on the apron and in the courtyard (the city's tree survey keeps its own there, and the tables
  are moved about); McKinley's allegorical group (his figure alone on a tall pedestal) and the Catto memorial; the weedy
  vacant-lot ground across South Penn Square and Broad (main's, out of City Hall's scope). Mike's two decisions stand
  open: Penn's right arm out as the photographs show it, and the plain night's amber against the LED system's white.
- Cost. The near level 39,284 triangles on a computer and 29,648 on a phone (its budgets 60k and 30k: a phone keeps the
  painted consoles on the crowns, its column pairs 9 m apart, no ribs, railings or bollards), the far 5,873 with its floor
  and the three glass houses (5,572 for the model alone, against the test's 6,000: the far level's turrets are six-sided
  now, and its pedestals plain drums), the dials 144, the floor 252. The bronzes on the themed mesh 15.7k on a computer
  and 9.0k on a phone, no draw of their own. On a phone, measured with City Hall hidden and shown at six places (still:
  the lowest of 8 frames with the shadow forced; moving: the highest with the eye stepping 0.6 m a frame): the near
  level +4 draws and +62k to +67k triangles still, +7 and +68k to +74k moving; the far level +2 and +15k to +21k still,
  +3 and +21k to +27k moving. On a computer the far shadow map's own cadence swings that A/B by 50k either way, so by count:
  still the near level's colour and shadow passes and the dials and floor, +4 draws and 79k; moving the pins' depth image
  adds the far level's 5.9k in the near's place (it drew the near level's 39k). Programs as before: city-hall-real, its cut
  depth, the dials, the floor; no link failures. Art: three gpt-image-2 calls at high (the crown box, 1536 by 896; the
  granite, 1024; the passage's wall, 1024 by 1120); 24 cells at 25.2 px a metre in the one 2048 atlas; art/cityhall/ 911 KB
  (a computer 715 KB, a phone 196 KB); the textures as they were, 26.7 MB on a computer and 6.7 on a phone, and a phone's
  floor and compass, 2.8 MB, only once it has come near. ?real=0 renders as HEAD did but for the traffic and the tufts
  (0.05 to 0.2 per cent of the pixels). Tests: 807, OK with the one expected failure.


## Round 191, Glory Beer Bar & Kitchen on its own lot (Oct 14)

- Mike: "I added more api credits with open AI. I want City hall and Glory Beer Bar and Kitchen to be totally revamped."
  Glory is 126 Chestnut Street, Old City, the south side between Front and 2nd. Round 10b's builder pro-rated house
  numbers along the block and put it on 120 (scene 2806, 4.9 m wide, four storeys, LiDAR 14.6 m): a white column of
  five piers with a tiny Futura GLORY board, two lots east. The OPA address point for 126 (101.01, -284.81) lies in 2541,
  and the Historical Commission's 2003 inventory (5 storeys, 4 bays, 1853, granite storefront pilasters, engaged granite
  columns with pointed-arch surrounds, 1/1 windows above, a corbelled brick cornice), Sanborn's 1916 plate (about 27.5 ft,
  60 ft, back to Ionic St) and the LiDAR (19.5 m, 23.7 m at the bulkhead) all agree. Under the realistic look 2541 is held
  back (REALISM_NEAR, key 'glory126', never 'glory', so the old builder cannot run on it) and rebuilds/glory.js builds the
  building on it; 120 goes back to the generic fabric, whose shuttered four storeys are the real 120's. ?real=0 and the
  new ?glory=0 keep the old builder on 120 exactly (rendered against before/: identical but for the clouds).
- The art (fetch_glory_art.py, gpt-image-2, high, opaque): 11 calls. Frames: two lower elevations (the granite ground
  floor and second storey, 8.6 by 9.3 m at 1536x1664, every pane chroma-key green) and two upper (the brick storeys);
  lower-b kept for its pointed arches (the inventory's "pointed-arch granite window surrounds"; lower-a's were round), upper-b
  for its storeys (its sills 0.64, 3.43 and 6.28 m over the granite cornice against the research's 0.65, 3.45, 6.25;
  upper-a's bottom row stood at 0.13). One glass edit into the upper key (blinds, curtains, the street reflected, every
  window different). Rooms: two of the bar (1536x784) and two of the room upstairs (1536x608) in one-point perspective;
  ground-empty-b (the bar down the right, the brick by the doors, the ducts and string lights, the cast-iron columns) and
  upper-empty-a (the mantel on the right, the globe cluster, the wainscot) kept; then one crowd edit of each over its
  floor (people at the bar and the high-tops; people at board games upstairs). Every image looked at: no lettering, no
  logos, a pure key.
- The bake (bake_glory_art.py): the key 0.199 of the lower and 0.190 of the upper (the plan's 0.25 to 0.45 for the lower
  was a guess: the bake now refuses outside 0.15 to 0.45). Measured from the key: the doors 0.44 to 4.04 m, four bays,
  the arcade's sill course 4.92, spring 7.77 and crown 8.32, the column pairs a quarter of each gap either side of its
  middle (r 0.11), twelve windows 1.07 by 1.83 m set to their stacks' and storeys' medians; no warnings. Two measuring
  fixes found on the overlays: the key's green is bright, so it counts as the opening (dark) for the doors and as the
  window (pale) for the sashes, and a door's lighter panel moulding no longer stops the growth (four lines in a row
  past the limit do). The brick came out at #a86444, more saturated than the street's orange red, and read as paint
  beside the block's procedural walls: its saturation goes down 22% (BRICK_DESAT). The atlas 2048x1280 (both
  elevations at 117 px/m, seven swatches), the mask at half, the rooms 1024x1224 (open full width, shut at half) and
  their mask. A computer downloads 847 KB, a phone 226 KB.
- The model: 3,950 triangles near (budget 6,000), 62 far, 24 for the signs; built in 8 to 9 ms. One draw for the
  facade, one for the signs. The fronts are holed (a grid between the openings' edges; an arch's head leaves two
  spandrel fans) and every opening is set back on its own pixels (doors 0.25, casements 0.20, sashes 0.12), so straight
  on it is the photograph and obliquely it has depth; the piers, their capitals, the sill course, eight engaged half
  columns, the granite cornice's profile (fascia, cyma, corona, wash) and the corbelled brick cornice are real; the
  shell's party walls stand 5 cm inside the lot lines; the rear range is four storeys to Ionic St with the stucco
  penthouse, the stair bulkhead to 23 m and two skylights. The stoop is 1.7 m deep with three steps from the entrance
  bay, black railings with a crossed scroll band, the Juliet railing in the east bay, two caged lanterns on the piers
  either side of the door, the blade sign on its bracket off the pier east of the door, the board over the door tilted
  out 8 degrees, the bronze 126 plaque, the menu case, the faded blue sign box high on the east edge, and two bistro
  tables and six galvanized chairs that the vertex shader (and the shadow pass's own depth material) folds away while
  the bar is shut.
- The page (api.glory): one facade material (atlas, mask, rooms, rooms' mask, the signs' canvas for the mural) with a
  swatch tiled in metres on each face's own plane; the bar's glass is interior mapping (the eye's ray through the pane
  into a room box, the hit's fractions scaled toward the plate's vanishing point by e / (e + z) per axis, from each
  plate's back wall measured by hand), open or shut plates mixed by the model clock's hours (Mon to Wed 4 PM to 2 AM,
  Thu to Sun 12 PM to 2 AM; upstairs from 5 PM), the mural painted on the bar's brick by the doors, the bulbs twinkling
  after dark, a shut room dark but for a red exit sign; the flats' windows take roomLight after dark; the lanterns glow
  with the photocell and light the piers, signs and stoop within 3.5 m, and go into the light map as two 7 m warm pools.
  GLORY is drawn by the page in vector slab-serif glyphs (painted and cut shapes, so no two windings meet), the trade
  line in a typewriter face, never by the image model.
- Four faults the renders found: (1) the facade drew the placeholder's grey: a texture uploaded behind the veil as a
  one-texel WebGL 2 immutable store takes no image of another size, so gloryLoad lets it go first; (2) everything was
  mirrored: the photographs look south, so their left is the EAST end, and the def now mirrors every measure into its
  frame (the entrance is the second bay from the west, the blade sign east of it, as on the street); (3) every box's
  sides were granite (the swatch's name, not its index, went into the bytes); (4) a striped band under the granite
  cornice: a face reaching 9.3 m took its top corners from the upper elevation, interpolating its uv across the atlas
  through the swatches; a face now takes its elevation from its own middle. And a swatch's gradients are held to its
  8-texel gutter, or a soffit seen edge on read a mip coarse enough to take its neighbours in.
- The street: Chestnut between 2nd and Front is drawn 9 m wide with 3.7 m walks to the building line (it was 13 m with
  1.2 m of walk, and the stoop and steps would have stood in the lane); the realistic look's alone. The neighbours that
  the new front showed up: 128-130 takes the sash and the painted shop floor in its own dark red, 122-124 the painted
  shop floor (both dressed by Round 189's shopfronts).
- Search: "glory" finds Glory Beer Bar & Kitchen (a new kind, bar, ranked 2 so the three Glory churches do not come
  first) and glides to the far sidewalk looking at its front with the mark at the door and its card open. A tap on the
  building opens the same card (Open or Closed by the model clock, today's hours, what it is, the address, built 1853),
  then the city's register, district and permit rows; Website and Property Record.
- Measured (headless, this Mac's GPU, before against after at the same poses and clock): a computer at the street-across
  pose 511 calls and 7.18 M triangles against 509 and 7.18 M (+2 calls, +2.8 k); a phone, counted per object over four
  frames, 466 against 462 (Glory's 2, and one car of traffic more), 4.50 M triangles against 4.51 M. Programs: five on a
  computer (the facade and the signs, each in its one- and two-shadow-map variants, and the shadow pass's fold), three on
  a phone (the review's count; this entry first said three). A phone (measure.mjs, GC-normalised): 875 MB GPU at ready against 869,
  936 after the look against 930, no padded copies, a live heap of 124 MB at ready either way, peak 282 against 281.
- Not done: the stair-side railings' scrolls, single dentils (the corbel's dentil course is a slab carrying the photo's),
  the neighbours' awnings (122-124's green "124 Offices", 128-130's burgundy) and 122-124's black strip; VDEPTH for the
  facade on a phone. For Mike: Yelp also lists an "Oberon" at 126 Chestnut (Dec 2025): a name for the room upstairs, or
  a new tenant?

## Round 191, the review's fixes to Glory (Oct 14)

- The review (renders at the builder's poses, day, night and phone, against the Bright MLS street view, Wanderlog's
  close-up and gloryphilly's own photos) found eight things that must change and a dozen that should. All but four are
  done; the branch is rebased onto main's Round 190 (the pins) and every "Round 190" of Glory's is now 191.
- The second storey was a church front: lower-b's four steep pointed lancets under moulded hood arches on thin ringed
  colonnettes, though LOWER had asked for "shallow pointed four-centred" arches. The real storey is a flat granite lintel
  on plump coupled Tuscan columns whose soffit dips between the capitals in a very low arch, two black steel casements a
  bay, no hoods, no tracery. `LOWER2` says so in metres (a 35 cm rise over the 1.5 m bay, springing at 7.9, the middle
  at 8.25; six columns in three coupled pairs; the doors glazed to a 30 cm kick rail; a warm buff granite). Four calls:
  lower-c and lower-d stood single columns, lower-f's were slender, lower-e has the pairs, the low arches, two casements
  meeting at a mullion and the short kick rails, and is CHOSEN. Fifteen calls in all now (6,194 + 2,722 input and
  67,995 + 38,928 output tokens).
  - The bake's spring is now the top of the frame's own stile 4% in from each side (the old rule, the highest row dark
    across nine tenths of the opening, fell 0.6 m down a low arch whose grown box took in a sliver of stone), and a frame
    whose rise is over `ARCH_RISE_MAX` 0.5 m is refused: lower-b measures 0.58 and is; lower-e 0.04 (its frame's head is
    nearly flat, flatter than the real soffit's 0.3 to 0.5 m: an under-rise, not a lancet). Spring 8.149, crown 8.185,
    the sill course 4.79, the columns at 2.30, 2.60, 4.17, 4.45, 6.01, 6.30 (r 0.139), the cornice 8.78 to 9.3 by hand.
  - glory.js: a head is now the segment of a circle through both springs and the crown (eight pieces), and the columns
    stand on a round torus and a square plinth under a round echinus and a square abacus whose top is the springing.
- The granite drew a ladder up every pier side, jamb and reveal: the swatch, cut from the band over the doors, held a stone
  joint and its shadow, and tiled at 0.45 m it put a dark wedge every 0.45 m. `granite_swatch` quilts four jointless
  patches of the piers' faces (a window is jointless when no row or column mean departs from its own; the old swatch's
  worst row departed 0.213, the new one's 0.008, `test_the_granite_swatch_has_no_joint` holds it under 0.05), each with
  its low frequencies flattened to the stone's mean, at 0.68 m a tile.
- A pale dashed outline ran round every door and transom pane within about 6 m: the key's anti-aliased rim, filled from
  every pixel round it, came out a light lavender, and the half-size glass mask stopped short of it. `fill_dark` fills the
  key and its 2 px rim from the dark frame only, and the mask's glass is grown two full-size pixels before the box resize.
- The bar's lit glass went black from about 100 m, and across the street the panes flipped between the two rooms as a
  mosaic of streaks: the shader told the bar's glass (b 196 to 222), the room upstairs (208 up) and the flats (66 down) by
  the mask's codes, which a mip averages with the frames' zeros (0.97 of the code at mip 0, 0.32 at mip 3, 0 at mip 5).
  Now by position in the facade's frame: the bar's glass under the granite cornice (9.3 m) times the mask's filtered cover,
  the room upstairs from 4.6 m, the flats above 9.3; the flats' window number and height inside the window are read at the
  mask's full size (`GLMASK0`: textureGrad with zero gradients; `GL_`-named macros are reserved and failed the link the
  first time). Rendered with a narrowed lens from 100 and 190 m by night against the page before: the four casements and
  the doors lit where they were black (fix1/pairs/z-night-aerial-190.jpg), and the arcade from across the street reads as
  the room with its string lights. A ray from the walk looking up into the arcade reads the near ceiling from 1.2 m in and
  darker (`glCeil`), not the plate's stretched top row.
- The trade line ran under the sign's border at both ends: it is measured first and fitted to 0.82 of the panel (Chrome
  headless, with and without American Typewriter: both inside the border). GLORY's glyphs are heavier and tighter (stems
  0.32 of the cap, counters smaller, a gap of 3 where it was 7), the trade in a lighter weight, as on the real board.
- The cafe read as concrete slabs: the chairs are galvanized steel now (a metal, 0.7, roughness 0.4, albedo 0.34), with
  thin splayed legs, two raked uprights and two slats curved round the seat, open below; the tables black steel tops on a
  pedestal and a cross foot. The lanterns' wash on them takes their (1 - metalness) share.
- The card never had the city's rows: the tap and the search asked for the parcel at the front or on the walk, about 4 m
  north of the PWD lot in Old City. A business the page knows carries its own point inside the lot (`ref.parcel`, the OPA
  point for 126) and the card asks there. A tap's point is already 1.5 m into the building hit, so `gloryAt` takes no pad
  (a metre's pad gave a tap on 128's party wall Glory's card).
- Should-fixes done:
  - The granite is warm: `STONE_TINT` (1.0, 0.965, 0.985) in the bake; rendered by day at hue 30 to 34 and HSV saturation
    0.10 to 0.15 against the photograph's 30 and 0.12 (gloryphilly IMG6), where it was 0.04 and read as marble.
  - The old sign box is pale faded-blue painted sheet metal peeling to primer with thin rust runs (`peel_swatch`, every
    field periodic so it tiles without a cross-fade cutting the blotches), in a black strut frame: a top and a bottom arm,
    a raking brace and a stile down its outer end, two wall plates.
  - The lanterns are caged jars on gooseneck arms: a black cap, a clear globe drawn opaque with its bulb drawn on it where
    the eye's ray passes the lantern's centre (a pale filament by day; after dark a hot core and a warm halo), four wires
    and a belly ring.
  - The door heads, jambs and sills of every opening and every swatch box's underside take a shade (aGl's fourth byte,
    `SH`: a head 0.59, a jamb 0.35, an underside 0.31, a sill 0.12): the light granite heads read as planks over the doors.
  - The railings carry a band of rings, a ring a picket pair, for the cast band; the Juliet railing is a balconet bowed
    0.34 m out with the same band.
  - The signs are faces of the near mesh (aGl mode 4 samples the canvas the facade already held for the mural), so the
    near level is one draw and the signs come and go with it at 200 and 170 m. Measured with traffic and the pins off at
    the street-across pose: 377 calls against 378, 5.62 M triangles against 5.61 M; the oblique and sidewalk poses the
    same, a call fewer each. Programs: three on a computer (the facade in its one- and two-shadow-map variants, the fold),
    two on a phone. The near mesh is 5,412 triangles (the rings, the lanterns and the chairs' slats), 62 far, 5,474 in
    all against the 6,000 budget, built in 10 ms.
  - `?glory=0` skips the def by its own id; `real: true` means the realistic look's alone again (a City Hall def marked
    real would have gone with `?glory=0`). Rendered: under `?glory=0` every other rebuild builds and Glory does not.
  - A phone fetches Glory's four images as bytes at the step and decodes them the first time the eye comes within
    `GLORY_DECODE_R` 600 m after Enter (the swatches' means stand in): probed headless, still pending after Enter over
    City Hall, decoded at the first pose on Chestnut. A session that never comes to Old City never holds the 7.2 MB.
  - On a phone Glory's brick keeps `GLORY_PHONE_SAT` 0.62 of its saturation: the fabric there has no walls' atlas and
    its neighbours rendered at 0.12 to 0.14 against Glory's 0.34 (the photographs' 0.32); now 0.22.
  - The narrowed block of Chestnut is one-way (OSM's oneway, which traffic.b64 carries) with one lane between the parked
    cars: no lane paint. The core's scene roads carry no oneway tag, so every other one-way core street of two lanes'
    width still gets a double yellow; that wants the tag carried into scene.json, outside Glory.
- Declined, and why:
  - The far mesh into the core's merged chunk: the chunk's material cannot sample Glory's atlas, so past 200 m Glory would
    wear generic windows; the far mesh is 62 triangles, frustum-culled, one draw only where Glory is in view.
  - VDEPTH for the facade on a phone: the near mesh is hidden past 200 m and its line would be 300; the far mesh would
    cross at 300 m, where it is 62 triangles over a few hundred pixels. A twin is one more program to compile on every
    phone for no measurable time.
  - The neighbours (noted, as the brief asked): 122-124 is a generic box with white six-light sashes and a deli front; the
    real one is a Neoclassical front of about 1925 with tripartite windows, brick roundels and a wide cornice, the green
    "124 Offices" awning and a black-painted brick strip against Glory's east wall. Its awning comes from Round 189's
    shopfront cells; a front of its own wants a rebuild of its own.
- Pre-existing, for the record: a green ground strip shows between the kerb and the generated sidewalk on core streets
  (in the `?glory=0` render too); the OSM footprints on this block stand about 4 m north of the PWD parcels, so the
  neighbours' cards say "No property record here".
- Renders: fix1/r3 (computer), fix1/p2 (phone), fix1/z-old and z-new (the page before against after at narrowed
  lenses), fix1/pairs (before against after: the review's own renders where the pose is theirs).

## Round 191, the second review's fixes to Glory (Oct 14)

- The second review rendered the first fixes by day, by night, in rain and on a phone, tapped every part of the front
  from both sidewalks and across the street, and measured the LOD switch and the art's memory. Two must-fixes and nine
  should-fixes; all are done but the neighbours (noted) and the Oberon question (Mike's).

### The muntins
- The pale-rim fix had taken them. The mask's glass was grown two full-size pixels before its box resize, from both
  sides of every 5 to 6 px muntin, so a door's or a casement's bars came out one texel at 85 or 170 (a third or two thirds
  glass) and 1.7 cm wide: by day the French doors and the steel casements drew as single dark sheets, at night as
  unbroken glowing panes. The dense black grid of small lites is the defining texture of both storeys (the Bright MLS
  view; gloryphilly IMG4 and IMG6): 2 by 6 a door leaf, 2 by 8 a casement.
- The bake now finds the bars between the panes of one opening (`pane_bars`: what closing the key by 4 px fills; a
  casement's mullion, a door's meeting stiles and the transom bar are wider and stay frame), grows the glass only toward
  the outer frame, and holds every bar at 0 two texels wide at the mask's size (`bar_texels`: the texels a bar covers
  more than half of, and its fuller neighbour where that leaves one): 3.4 cm, 95% of the bars exactly two texels, the
  rest at the ends where a bar meets the frame. A phone's quarter mask, nearest, keeps one.
- The shader sharpens the glass's cover where the mask is magnified (a texel spread over many pixels within a few
  metres) and leaves it filtered once a pixel spans a texel, so a far pane averages its glass and bars.
- Checked by night close up (2 and 3 m) and across the street: the bars silhouette black against the lit rooms; by day
  they read as a grid of lites. From 50 m up a casement is a few pixels and its glass and bars average into a glow. No
  pale rim came back: the atlas already fills the bars with the dark frame (`fill_dark`).

### The tap
- From the sidewalk the blade sign, the lanterns and the old sign box opened the generic card (and, once the city
  answered, "No property record here"): the point 1.5 m along a ray running along the street is still over the walk.
- `ref.apron` is the walk in front of the lot's own frontage, 2.4 m out; a tap whose hit stands there names Glory
  (`gloryApron`). The lot itself is now tested 0.3 m past the hit, not 1.5 m: probing showed an oblique tap on 128's
  front from the west sidewalk naming Glory through the long push. Probed from the west and east sidewalks and across
  the street: the blade, its far end, both lanterns, the sign box, a pier and the brick name Glory, 128's and 124's fronts
  open their own cards, and the west sidewalk's blade card fills with the register and district rows.

### The rest
- The old sign box: grey-sage paint (164, 168, 153) gone to primer in small ragged flakes, a mottle of grime, thin rust
  runs in the swatch; in the shader, by the box's own frame (`uGlBox`), grime toward its edges, rust run down from its
  top and creeping up from its foot, matte (roughness 0.8), and only 0.12 of the street lamps' wash. Its foot is a
  rounded cap of rusted sheet (a new eighth swatch, `rust_swatch`). It no longer reads as sky-blue glass by day or glows
  teal at night.
- The granite: a salt and pepper grain on each face's own plane (3 mm grains over a 1 cm mottle, each faded out before
  a pixel spans it: seen at 2 to 3 m), and the weather by place on the front, never by tile: streaks under the capitals,
  the sill course and the cornice (`frame.drips`), a footing darker to the walk, a few old anchor holes with a rust run on
  the piers. The jointless swatch test stands.
- The undersides and heads: an underside darkens toward the wall it leaves, a door head and its jambs toward the door
  at the back of the recess; measured on the review's pose the head soffit went from 114 to 97 against the face's 188,
  now a gradient rather than a plank. The capitals' boxes stand on the painted capitals (3.94 to 4.08 m, measured by
  hand: `CAPITAL`), the end two short of the party walls by the painted 0.15 and 0.2 m, so no cap's underside runs out
  past its painted end.
- The cast lace: the stoop band's six-piece rings rendered as hexagons and the balconet read as a birdcage. Both are now
  one strip a run cut in the shader (aGl mode 5, `GLORY_LACE_GLSL`, `discard`, the part-covered pixels dithered by
  their share, the shadow pass cut at the same line): quatrefoils a picket pair, a lily between, a ring round each post;
  the balconet flat-fronted with a 0.12 m belly and a band of S scrolls. The near mesh went from 5,412 to 4,198 triangles.
- The cafe chairs at night: the street lamps' wash lands right after the emissive include, so the facade hands it a
  face's share of its colour there (`glLampK`: a metal's 1 - metalness, the old box 0.12) and restores it for the lights.
  The chairs read mid grey at night, not white plastic.
- The bar at night: the room's night term from 1.6 to 2.6, and a warm glow that comes in with the distance (`GLORY_FAR`,
  8 to 70 m, 0.75), since from above the plate shows the room's dark floor. Measured with the default lens (58 degrees,
  each opening's mean luma over its glass box, bars included, against the flats' windows; the review's own renders for
  before): across the street the arcade 39 to 99 became 53 to 106 and the doors 46 to 72 became 57 to 81, against the
  flats' brightest 90 and lit mean 72; at 50 m 122 to 128 against 140 and 113; at 100 m 141 to 157 against 127; at
  190 m 34 to 46 became 146 to 151 against 145 and 91. The open bar is now the brightest glass on the front from 100 m.
- The art's memory: a computer decoded Glory's four images at the step in every session (about 28.6 MB of GPU with the
  mips). Every device now fetches the bytes at the step and decodes them the first time the eye comes within 600 m after
  Enter. A phone, once decoded, holds about 7.2 MB and never releases it after the eye leaves Old City: noted in
  handoff with the numbers, acceptable under the deferral.
- The LOD switch: the far level's stoop carries its railings as the lace's whole-railing kind, one strip a run (78
  triangles far, up from 62). Same pose at 195 m, near against far: 51 pixels differ by more than 24 levels in Glory's
  window by night, 87 by day, about what the review found; the slab no longer goes bare.

### Budgets
- Glory: near 4,198 triangles (5,412 before), far 78 (62), 4,276 in all against 6,000; one draw at either level; two or
  three Glory programs in a headless run as the shadow variants compile (the facade in one and two shadow maps, the
  fold), two on the phone; no link failures, only the old 'Unable to serialize Texture' warnings. The frame's totals at the review's five perf poses moved by run-to-run scene noise
  (377 to 380 calls across the street), not by Glory, which draws the same one call.
- Streams unchanged: aGl four normalized bytes, every stream a multiple of four bytes.

### Noted, not changed
- The neighbours: 122-124 lacks the full-height black-painted brick strip against Glory's east edge in the Bright MLS
  view, its "124 Offices" green awning and its Neoclassical front; both neighbours' white six-over-six generic sashes look
  plainer beside Glory's photographic front. Grass tufts grow from the paving at the stoop's foot (the same under
  `?glory=0`). In rain neither Glory's granite nor its neighbours darken or shine wet; that is city-wide.
- For Mike: Yelp lists an "Oberon" at 126 Chestnut.
- The balconet's scrolls at a grazing angle from directly below dither to a fine perforated look; that is the lace's
  honest coverage with no multisampled alpha.
- Renders: landmarks/glory/fix2/r3 and r4 (computer), p1 (phone), g0 (`?glory=0`), pairs (the review's renders on the
  left), lod_n_195.png and lod_d_195.png (near against far at one pose).

## Round 191, the third review's fixes to Glory (Oct 14)

- The third review looked at Glory from 0.6 m to 300 m by day, at dusk and at night, on a computer and on a phone, on the
  recovery tier, through the search's landing and a frame-time trace. Five must-fixes and eleven should-fixes. All are
  done but two, said below; no new images were asked of OpenAI (fifteen calls in all stands).

### The stone
- The second review's grain, hashed square cells of 3 mm stepped to dark and light specks over a 1 cm mottle, read as
  digital dither up close: diagonal rows of cells (the sin hash's lattice), sandpaper at 1.4 m. The photographs' stone is
  smooth and pale, its only marks close up the stains, the drips and the old anchor holes.
- Now smooth value noise (a sin-free hash, `glH2`, eased between its cells, `glVN`) in three turned octaves of 4 mm,
  1.2 cm and 4.5 cm, about 5% all told, each faded out by the pixel's footprint before it spans the octave's cells. The
  drips, the footing and the anchor holes are unchanged.

### The muntins
- Within 2 m the bars followed the generated image's hand-drawn ones: a door leaf's vertical bar jogging a texel between
  lites, bulging at every crossing, and every lite a rounded rectangle, the 0.5 contour of the filtered mask sharpened.
- The bake (`regular_lites`): every sash (the key closed over its muntins) has its lites in columns and rows; a column's
  sides and a row's head and foot are their lites' medians, the sash grows two source pixels toward its outer frame, and
  every muntin is a straight bar two texels wide on the texel boundary nearest its middle. The lower elevation's mask now
  holds only 0 and 255, and all 232 lites (eight leaves of twelve, eight transoms, eight casements of sixteen) are filled
  rectangles. The same bars are painted into the atlas in the frame's own colour (`paint_bars`, the median of the image's
  bars as filled from the dark frame: the raw image's carry the key's green rim, which the first try painted).
- The shader reads the mask texel by texel where it is magnified, its edges eased over a pixel (`textureGrad` at the
  texel-snapped coordinate, with the true gradients, on WebGL 2), and filtered as before where a pixel spans a texel.
  At 0.9 m and 1.4 m the bars are straight and the corners square (r1/d04, r1/d03, r1/n02).

### The seams
- `noise_swatch` built its blotches from cells resized without wrapping and never made them tile, so every concrete tile
  (1.5 m) and roof tile (3 m) ended at a hard edge: a seam down the stoop's deck and through every tread and riser, and
  every 1.5 m along its fascia. Every field is now `periodic` (the cells tiled three by three before the resize, the
  middle kept); without the grain a tile's wrap is no harder than any step inside it (tested). The concrete is a fine
  aggregate's grain over a faint mottle at 7%, not 8 cm clouds at 14%. No seam shows on the stoop, the steps or the fascia
  (r1/e01, r1/e04).

### The bar at night, from the street
- From the sidewalks and walking up Chestnut the deep reveals hide the lit glass, which is right, but nothing warm came
  out: the stoop, the steps and the jambs took only the street lamps and the two lanterns, and the open bar looked shut
  beside 128's glowing shop.
- In the facade shader, by position, no new geometry: each lit opening is a warm panel (2700 K) at its glass, its light
  from the nearest point of the glass's middle half (so a jamb sees across it, a head and the stoop up and down into it),
  N dot L, falling off as 1 / (1 + 1.2 d squared) to nothing at 3.2 m from the glass, and none behind its plane
  (`glSpill`). The four doors take the bar's hours, the four arches the room upstairs'. It lights the jambs, the heads,
  the stoop's deck, the steps, the railings and the chairs; the deck in front of the bar now glows from either sidewalk
  (r2/n03, r2/n04, r2/k02).
- The bar's own door leaf stands open while it is open in fair weather (no rain, snow or hail falling, over 50 F where
  the live weather says): the east leaf of the entrance, as in the Bright MLS view and gloryphilly IMG6, swung out 92
  degrees on its outer stile, both faces from its own pixels in the elevation (aGl mode 6: dark glossy glass, no room
  behind it), folded away in both passes when shut (`uGlDoor`). Its doorway on the recessed face is all glass, the room
  interior-mapped through it, rough rather than glazed. The bake measures the leaves from the regular sashes
  (`door_leaves`: the stile 0.1 m outside the glass, the head 0.11 m under the transoms' glass). The entrance was the
  darkest bay by day; now the bar shows through it (r2/d01, r1/d03).

### The search
- The search's mark stood at the door, a 5.2 m pin for 20 s: in the very view the search lands on, it covered the GLORY
  board, the entrance and the middle bays, and from 200 m it sat on the front as a cream disc. It stands over the parapet
  now, 20 m up, above the landing frame's top (about 15.5 m at 13 m) and still marking the place on the way in
  (r2/glide-landed-day, -night).
- '126 chestnut' fell through to the address lookup, which landed without the card. The index carries the address under
  the bar's own name: '126 chestnut', '126 Chestnut St' and '126 chestnut street' all find Glory.

### The rest
- The east return: 124's front stands back 1.1 to 1.3 m from the lot line, so Glory's own east party wall shows full
  height from the east, drawn as red brick. It is painted black over the storefront (from 4.1 m), the brick's relief
  through the paint, red brick only beside the granite base, as the Bright MLS view from that sidewalk shows (r1/e08).
- A tap under 2 m opened nothing: the generic ground rule ran before Glory's tests. They are asked first now, for any hit
  over the walk's own level (10 cm). Probed from the west sidewalk, across the street, the east sidewalk and 12 m up:
  the door at 1.2 and 1.6 m, the open leaf, a stoop railing, a chair, the stoop's deck and a step name Glory; the walk
  itself and 128's and 124's ground floors open nothing.
- The lanterns: the globe's normals are the round jar's at every corner (`quadN`, the same triangles), so it shades
  round; the glow is an amber filament (about 2700 K) and lower, so the tone curve keeps its colour.
- The stoop's band: its 1.3 cm lines and 6 cm quatrefoils read as a thin chain of rings. Now a cast fleuron a picket,
  as gloryphilly IMG6 shows: a pointed arch from scrolled feet that meet the next one's, a spade over its point and a drop
  inside, strokes of about 2 cm, the motif filling the band, and a heavy ring round each post (prototyped as a numpy port
  first; r1/e03).
- The chairs: at 0.7 metalness the sky mirrored in the seats as light blue plastic. Galvanized steel is a dull metal now
  (0.25 metalness, 0.58 roughness, a mid grey); the backs have three slats curved round the seat, and the seat a
  turned-down edge. The tables' tops have an apron and a satin black.
- The old sign box: its enamel is the photograph's pale worn white-grey (190, 192, 186), chipped to rust.
- The block: the meadow showed in a strip before 122 and 124's set-back front. The narrowed block of Chestnut lays its
  walks 5 m wide, on under the fronts (unseen where a front is on the line), and the block's walk is handed to the app
  as paving (`G.paved`, `REBUILD_PAVED`), where no grass tuft is sown whatever ring sowed it: the tufts at the stoop's foot
  are gone too (none on the block's walk, probed).
- The GLORY board after dark: lit from below by the lanterns' warm wash, and its canvas read a little sharper (a -0.6
  mip bias), so across the street at night the L keeps its foot and the trade's line stays.
- The room upstairs across the street at night showed big dark diagonals over every casement: from the street below
  it is mostly its ceiling, which the plate holds only as its top rows run to the vanishing point. The ceiling is drawn
  in the shader as IMG4 shows it: slate-grey paint, the spiral duct down the middle, strings of bulbs across the room.
  The outer two casements still show the side walls' cream, as a room seen from below would.
- The recovery tier: tier 2 decoded all of Glory's art. It decodes only within 200 m (the near level's reach) and never
  loads the rooms; the open bar's glass glows a plain warm after dark (also before the art lands anywhere). Probed with
  `?lite=2` on the phone: art loaded, rooms 0, the rooms' textures the 1 by 1 placeholders (about 2.1 MB of the phone's
  7.2 not held).
- The uploads: a decoded image waits in `GLORY.upq` and `gloryStep` sends one a frame (`gloryUpload`, through
  `renderer.initTexture`). The four now land in four frames (frames 2 to 5 of a session that starts beside Glory). On the
  review's own trace (a flight in from 900 m at 5 m a frame, headless), the landing frame went from 134 to 115 ms and the
  next from 69 to 18; the atlas with its mips is still one upload of about 100 ms headless on its own, and the 60 fps
  work should time it on a device.

### Budgets
- Glory: near 4,686 triangles (4,198 before: the open leaf 8, the chairs' slats and edges and the tables' aprons the
  rest), far 78; 4,764 in all against 6,000; one draw at either level. Two Glory programs on the phone, no link failures
  on the computer, the phone or tier 2, only the old 'Unable to serialize Texture' warnings.
- The phone at the review's six perf poses: Glory one call of 4,686 triangles near, one of 78 far (300 m).
- Streams unchanged: aGl four normalized bytes, every stream a multiple of four bytes. No new sampler.

### Not done
- The bar's glass by day from across the street: the upper middle casements still read as dark sheets (the room
  upstairs shut by day, its glass as dark as its bars at 15 m). Unchanged from the reviews' renders.
- At 0.6 m beside a pier (the review's e02 pose) a sliver of Glory's empty interior and the ground under it shows past
  the pier's corner. It was there before this round and it is not a hole: the page's camera clips at 0.75 m (its near
  plane under the log depth buffer), and the jamb there lies 0.6 to 0.85 m ahead of the eye.

### Renders
- landmarks/glory/fix3: r1 and r2 (computer), phone (six poses and three of the integration review's), lite2 (tier 2),
  hitch (the trace), g0 and r0 (`?glory=0`, `?real=0`), look/ (crops, pairs, the band prototype).

## Round 192, reversed-Z depth (Oct 14)

- Mike asked for an innovative way to hold about 60 fps. The investigation (four measurements, four designs, two spikes,
  two independent checks) found that most of each frame went on shading city nobody sees: r149's logarithmic depth buffer
  writes `gl_FragDepth` from every fragment of every program, and a shader that writes depth loses the GPU's early depth
  test and, on Apple's tile GPUs, hidden-surface removal, so the 7 to 17 layers each pixel rasterizes are all shaded in
  full. Phase 1 of its plan ships here: reversed-Z float depth through `EXT_clip_control`, the default wherever it can be
  had, rebased from perf spike 1 (branch perf/perf-spike1, d144d3f and 83744ca) onto Round 191's main and finished.
- The picture is the old one, with four differences the parity renders below name: a fine, even speckle of 1 to 4
  levels on far edges, and three places where the same cause (the four samples of a multisampled pixel each keep their
  own depth now, where the log buffer handed them the fragment's one) changes a fine pattern stably, all three
  corrected by the second review (Parity); and a phone's far mid-rises, which now draw as a computer's do, a decision
  for Mike before this deploys (The depth mode). The frames are 1.1 to 6 times faster (nothing is gained where nothing
  is hidden: a view of the sky alone). The first review found the river mirror drawing the far shore's lamps through the
  walls in front of them at dusk and at night, which a parity set without a night mirror pose had missed; fixed below.

### The depth mode
- A throwaway WebGL 2 context must report `EXT_clip_control` AND a complete 4x multisampled `DEPTH32F_STENCIL8`
  framebuffer over RGBA8 (and over RGBA16F where the post pipeline will own the frame) (`zrevCheck`). On a computer the
  same context already answered the post pipeline's float question; a phone makes one it never made before (and lets it
  go at once). The real context then passes the same
  check before anything is built on it; if it does not (never seen), its canvas is swapped for a fresh one and the page
  builds on log depth, since the phone path's reversed canvas has no depth buffer of its own.
- Without the extension, or with `?zbuf=log`, the page is r149's log depth as before; `?logdepth=0` is still plain 24-bit
  depth (it z-fights on the tower skins from the air, the spike measured 8,297 px). `ZPROBE` holds the answers.
- How it draws (the spike's design, unchanged): inside `renderer.render` every perspective camera's z row is rewritten so
  the near plane is depth 1 and the far plane 0, the clip control is ZERO_TO_ONE, the depth clears to 0 and every depth
  function is flipped (LESS to GREATER) through a wrapped `setFunc` whose cache holds the flipped value; outside the call
  `camera.projectionMatrix` is three's own, so every `.project()`, ray, label and pin gate is untouched. The shadow pass
  and orthographic cameras keep the standard convention. The render lists' z sorts and the frustum's far plane are put
  right, r149's PMREM gets a depth clear. The wrappers are one function now, `zrevInstall`, run under Node by the tests.
- Float depth wherever a perspective camera draws: the post pipeline's multisampled target and the river mirror re-specify
  three's depth renderbuffer as `DEPTH32F_STENCIL8` (`zrevFloatDepth`), the phone draws into its own 4x RGBA8 +
  `DEPTH32F_STENCIL8` target blitted to a canvas made without antialias or depth (`zrevPresent`; its depth is invalidated
  before the resolve so a tiled GPU never stores it), and the pins' capture and both taps take a float depth texture.
- The far facades' vertex-depth twins (`VDEPTH`, Round 168) exist only under log depth; under reversed Z every program
  already keeps its early test, so they stay off. That changes a phone's picture (the review): beige and grey mid-rises 1
  to 2 km off lose the darker pilaster and floor lines the twins drew; the branch draws them as main does with
  `?vdepth=0` (Chrome's phone path at the 745 m overcast pose: mean difference against main 1.44, main's own `?vdepth=0`
  1.11, the branch under `?zbuf=log` 0.37), which is also how a computer draws them. The floor pattern's fade reads
  `fwidth` of the wall's own coordinate, not the depth, so it is not the fade; the twins' programs are the originals plus
  one `#undef`, and what differs is how the depth resolves: the twins give each of a pixel's samples its own depth while
  what lies on a far wall keeps the fragment's one, which decides the coplanar ties there. So the phone's far facades now
  look as the computer's and as the phone's did before Round 168. This is the one known visible change from main on a
  phone, and it must not ship as a default nobody chose: before the deploy Mike sees the side by side (scratchpad
  perf/phase1/fix2/work/vdepth-decision-phone-ov745.png: main, main with `?vdepth=0`, this build, this build under
  `?zbuf=log`, Chrome's phone path at 745 m under an overcast) and his answer goes here. The second review measured it at
  night too: at hz-600-n 0.92% of the pixels over 24 levels against a noise of 0.004%, the mean brightness the same
  (77.80 against 77.82) and the lit share 1.4% lower. Mike's answer: not yet given (pending at the second review's
  fixes).

### The spike's loose ends
- Planes over the clouds: the spike's depth-free deck let an airliner above the cloud base draw in front of the cloud it
  stands behind. Every aircraft over the lowest base on the screen now gets a rectangle of the drawing buffer round its
  bounding sphere (`cloudRects`: sixteen at most, merged nearest-together past that; a sphere the near plane cuts takes the
  screen), the depth-free twin discards inside them, and `cloudDeckZ`, the depth-writing program cut to them
  (`CLOUD_RECT_IN`) and scissored to their union, draws them exactly as the deck always did. The same pixel test in both
  programs, so they tile the screen. A held airliner at 1,272 m behind an overcast and a drizzle deck is veiled as before;
  with the rectangles off (`__dbg.cloudRects(false)`, the spike's behaviour) it shows through (work/plane4-crops.png).
  All three cloud programs compile behind the veil (`CLOUDZ.warm`), none in flight.
- The mirror's stencil: the spike gave the river mirror a float depth texture and no stencil, so the vehicle shadows in
  the reflection could darken twice. It keeps `DEPTH24_STENCIL8`'s stencil as `DEPTH32F_STENCIL8`. The parity renders
  caught one more thing here: `zrevFloatDepth` makes the target's framebuffers, and three sets a target texture's
  parameters only then, so called before the mirror's anisotropy it left the mirror without its anisotropic filter and
  the boathouses' reflections smeared to a blur (the pixel statistics called it a mean of 1.5; the eye caught it). The
  anisotropy is set first now, and a test holds the order.
- The mirror with no river in view: when no frustum corner ray climbs from the water the spike set the reversed row to
  null, and the mirror drew with the plain projection, everything under the water included. The row's slope is floored
  instead; the water still clips, and nothing over it reaches the image either, which is what such a view reflects.
- The clear to the near plane: a `renderer.clear()` made outside a render clears to 1, the near plane in reversed Z, so a
  reversed render that keeps the depth it finds would draw nothing. Every such clear is remembered by its target; a
  perspective render with `autoClear` (or `autoClearDepth`) off on a target cleared that way since a reversed render last
  drew there, or under r149's PMREM, clears to 0 first (`ZREV.clr`, a WeakSet since the review: the first build kept one
  slot that any render emptied, so a clear on T, then an orthographic render on T or a reversed one on U, left T's next
  render on the near plane; `ZREV.guard` counts). Today only PMREM needs it (24 guarded clears a pose over 24 poses, all
  of them its probe faces, as before the review); every other pass clears inside its own render.
- The direct MSAA-to-canvas blit works only because r149's context is alpha:true (the check's standalone probe failed it
  with INVALID_OPERATION on an alpha:false canvas), so the two-step fallback stays: the first present checks its blit and
  falls back to a resolve into a plain RGBA8 renderbuffer and a copy.
- The camera's projection row was saved in a Float32Array and put back rounded to float32 after every render: doubles now.

### The clouds under both depth modes
- `CLOUD_NOZ`, the deck's twin that writes no depth and sits on the far plane, is drawn under the low bank's lowest base
  minus 25 m in both depth modes (`cloudDeckStep`), with the aircraft's rectangles in both. Under log depth it buys less
  than the measurements promised: on this Mac's GPU (ANGLE over Metal) the depth the other programs wrote from their
  fragments seems to cost the twin its early rejection too; `?zbuf=log` against the old build gains 14 to 50 ms at
  Retina only where the deck covers much of the screen behind near walls (City Hall's front, Glory, Sansom), nothing from
  the air, and 2 to 14 ms on the phone path.
- `?cloudz=old` still keeps the depth-writing deck everywhere, and plain depth (`?logdepth=0`) always does.

### The Mac's resolution controller
- frame() abandoned the trial on any frame of 250 ms or more (`dprGap`). Mike's Mac at 1.75 has a 95th percentile of 133
  to 433 ms, so its controller almost never acted (beacons: it stayed at 1.75, at 1.49 in its best session). A frame of
  250 ms or more is a slow frame now, judged with the rest (the window's mean leaves out its slowest fifth); only time
  away from the page is a gap: a page hidden now or since the last frame (`DPR.away`, set by visibilitychange) or a frame
  over `DPR_AWAY` 4 s. Simulated in `tests/test_dpr_controller.py`: in the test's own model (every frame's cost the
  square of the ratio, so each step down pays), a fill-bound Mac with a tail of 300 ms frames steps from 1.75 to the floor
  in about 80 s where the old rule never moved it; a 400 ms hitch every 10 s on a fast Mac moves nothing; the minute in
  the background and a reported two-second absence still abandon the trial. In the page itself, with frames modelled on
  this build's Retina timings (35.5 + 12.3 r squared ms, one frame in eight at 3.6 times, 263 ms; the review's run), the
  controller stepped 1.75 to 1.488 after 23 s and then refused 1.264 because that step bought under 12% (`DPR_GAIN`): it
  settles where the gain stops, 1.26 to 1.49 on those timings, not at the floor.
- For Mike (the second review): the controller now works, so a Mac that is strongly held back by its pixels walks all the
  way to the 0.9 floor; in the reviewer's in-page model (15 + 27.6 r squared ms, a 350 ms frame every 12th) that took
  about 80 s. That is by design, and the softer image would be the sign. With reversed Z his Mac is far less held back by
  its pixels (Retina from the air 68 to 80 ms, at street level 20 to 37), so expect it to settle at 1.49 to 1.26.
- The same rule runs on a paced phone, which the task did not ask about: a phone's first flight compiles programs in
  clusters of about a second. `tests/test_dpr_controller.py` now flies a geometry-bound phone paced at 30 through
  clusters of four 280 ms frames (five of them, and a dense half minute of one every 2.5 s): no step down is tried, under
  the new rule or the old; a phone held back by its pixels, which needs the step anyway, takes it during the hitches
  (4.9 s) where the old rule waited until they were over (32 s).

### The beacon
- Every beacon carries `zc`: the mode (`rev`, `log` or `std`; then `q` when a flag forced it, `c` when a crumb kept log
  depth, `a` when an Android phone did), the throwaway context's three answers (the extension, the framebuffer, the clip
  volume seen to clip; `-` when not asked), an `x` when the real context refused what the throwaway one granted, and the
  blit (`d` direct, `t` two-step, `x` both failed, `p` the post pipeline's own resolve, `-` none yet), with a trailing `0`
  when any float depth target (the scene's, the phone's own, the mirror's, the occlusion copy) came back incomplete or a
  blit failed. Chrome on this Mac: `rev.111.p` (computer), `rev.111.d` (phone path); WebKit the same; `?zbuf=log`:
  `logq.---.-`. After the TestFlight build, Mike's iPhone will say whether iOS 18.7 has the extension; an Android phone's
  `loga.111.-` will say whether it could have had it. A `zbuf` beacon (`zf`, `zs`) marks the load that left a crumb.

### Measured
- Interleaved A/B/L in one headless Chrome 155 over Metal on the M2 Max (A the old build at b2938ce, B this one, L this
  one with `?zbuf=log`), rotating blocks of drained frames at each pose, minimum and block-median deltas; other processes
  held 76 to 92% of the GPU throughout (the Simulator, the Claude app, WindowServer), so only same-run ratios are robust.
  Draw calls and triangles match pose for pose; where a run's earlier poses left the arms in different states (Spruce at
  Retina, the waterfront at 1 MP) they differ both ways, and Spruce alone draws 513 calls and 8.07 M triangles in both.
- Retina (1728 by 1117 at 1.75), minimum ms A / B, B over A: aerial 116 / 73 (0.63), sp90 135 / 75 (0.56), Broad 144 / 43
  (0.30), Sansom 179 / 30 (0.17), Spruce 134 / 59 (0.44), waterfront 81 / 65 (0.80), night aerial 124 / 78 (0.63), rain
  sp90 133 / 74 (0.55), close against City Hall's north front 154 / 34 (0.22), Glory 170 / 42 (0.25), storm at 420 m 112 / 69 (0.61),
  the 64-frame flight 149 / 81 (0.55). Block-median deltas 22 to 161 ms.
- 1 MP (1280 by 800): aerial 63 / 42 (0.67), sp90 63 / 33 (0.52), Broad 85 / 24 (0.28), Sansom 70 / 21 (0.30), Spruce 70 /
  28 (0.40), waterfront 27 / 24 (0.88), night aerial 67 / 49 (0.73), rain 50 / 35 (0.70), City Hall 81 / 23 (0.28), Glory
  76 / 21 (0.28), storm 46 / 42 (0.91), flight 73 / 38 (0.52).
- Phone path (touch, 925 by 450): aerial 32.5 / 23.9 (0.74), sp90 30.7 / 17.8 (0.58), Broad 34.2 / 14.5 (0.42), Sansom
  35.1 / 14.0 (0.40), night aerial 48.9 / 34.8 (0.71), rain 45.3 / 17.9 (0.40), City Hall 26.4 / 13.7 (0.52), Glory 37.4 /
  13.7 (0.37), storm 31.6 / 21.9 (0.69), flight 41.8 / 22.1 (0.53).
- Real WebKit (a WKWebView on macOS 26, the engine of Safari and of the iOS app; the check's harness, A and B
  interleaved): `EXT_clip_control` and the framebuffer granted, `rev.11.p` on the computer and `rev.11.d` (the direct blit)
  on the phone path (two digits: these runs came before the clip test, whose third digit makes them `rev.111.p` and
  `rev.111.d`), no console errors. Retina, minimum ms A / B: aerial 145 / 81 (0.56), sp90 151 / 86 (0.57), Broad
  196 / 43 (0.22), Sansom 195 / 34 (0.17), Spruce 159 / 63 (0.40), waterfront 94 / 71 (0.76), night aerial 150 / 89
  (0.59), rain 157 / 90 (0.57), storm 125 / 74 (0.59), the Schuylkill 117 / 74 (0.63), City Hall 161 / 42 (0.26) and at
  night 210 / 47 (0.22), Glory 186 / 39 (0.21) and at night 188 / 39 (0.21), pins in Old City 149 / 73 (0.49), an
  airliner behind an overcast (the sky alone) 185 / 198 (1.07). Phone path: aerial 30 / 23, sp90 27 / 19, Broad 30 / 16,
  Sansom 28 / 16, night aerial 33 / 25, rain 29 / 20, storm 31 / 24, City Hall 29 / 14, Glory 31 / 13 and at night 35 /
  15, pins 38 / 20, the overcast sky 22 / 14.
- The sky alone (looking up into the deck from 10 m, Chrome Retina): 166 / 162 overcast, 84 / 89 clear, within this
  machine's noise either way; nothing is hidden there for the early test to save. The first review's 1 MP run had B
  slower there (block medians 65.2 against 76.8 ms); the second review's interleaved run does not reproduce it: the
  overcast with the test aircraft held at 1 MP, minimum 40.0 / 38.9 ms and median 44.6 / 42.8 (0.97), at Retina 0.95,
  WebKit's phone path 0.56. Reversed Z costs nothing measurable where it saves nothing.
- Phone memory (the capture skill's measure.mjs: phone emulation on SwiftShader, which grants the extension too,
  `rev.11.d` before the clip test, `rev.111.d` after): GPU by the hook 873 / 906 / 930 MB at ready, after the first frames and after the look round, against
  886 / 919 / 943 (+13 MB); live heap 126 / 137 / 138 MB in both, peak 279 MB in both. The hook counts every
  renderbuffer at 4 bytes a sample and never the canvas: the +13 MB is the phone's own 4x RGBA8 and 4x float depth
  target, which takes the place of the canvas's 4x backbuffer and its depth that the hook never saw; counted honestly
  the change is +2 to +7 MB (the float depth at 5 to 8 bytes a sample). The pins' two capture targets' float depth is
  about 0.4 MB more than their 16-bit renderbuffers.
- What it means for Mike (estimated from his beacons times these ratios): his Mac's 100 ms median at 1.75 becomes about
  55 to 65 ms from the air and 20 to 45 ms at street level, and the repaired controller can now trade resolution for the
  rest. On the iPhone, if iOS 18.7 has the extension, a faster frame shows as sharpness at 30 fps (PACE and the Graphics
  ladder), not as 60 fps; that is the plan's later phases and Mike's call.

### Parity
- Chrome, the computer path, 48 poses (day, night, rain, storm, fog, the fifteen hard poses of the check: the climb through
  the cloud switch at 735 to 775 m, inside and over the deck, the Schuylkill mirror, the Delaware from 8 m, the bridge and
  Broad Street at night; City Hall and Glory close up, day and night; the mirror at Boathouse Row and the Expressway; pins
  in Old City, by City Hall, at Reading Terminal and at night; an airliner held behind overcast, drizzle and a clear deck),
  each in A, B, L and a second A (the noise). B against A: mean 0.1 to 4.1 levels (the aerial poses highest), the second A
  against A 0.0 to 4.8 (moving traffic). The diff images are a fine speckle on far edges, no structural difference; plain
  depth's `?logdepth=0` differs from A by more than B does at the same poses (aerial 3.7 against 3.0), which puts the
  speckle on the per-sample depth and not on reversed Z. L against A is the noise everywhere (the log fallback with the
  depth-free deck draws the old picture).
- That paragraph understated it (the second review). With each sample keeping its own depth, three fine patterns change,
  stably, where the noise run shows nothing: at lots-sports-300 the stadium bowl's front rows, main's dark checker, become
  lighter stripes (p99 16, 0.36% of the pixels over 24 levels, the noise 0.000%, the same numbers in WebKit); at
  rowroofs-250 the rowhouse parapet lines change (p99 17 against 0); and far lit windows speckle at night (hz-600-n 0.45%,
  hz-2000-dusk 0.64%, against 0.00%). None of it is z-fighting: in the shifted-frame flicker test the stadium's pixels
  flip 0.167% from frame to frame in B against 0.189% in A, and B is equal or lower at all eight flicker poses. Crops:
  scratchpad perf/phase1/fix2/work/fl-lots-strip.png (the flicker strip at the stadium) and work/crop-lots2.png (A, B
  and the difference at the bowl).
- One-pixel seams resolve differently in places: at Glory across the street at night a single row on the cornice under
  the sign is the band's lighter face under reversed Z where the log buffer drew the darker one.
- The phone path, 15 poses: the same picture.
- The storm at 360 m once came out brighter in B and in L: a synthetic lightning flash (random by design), gone on a rerun;
  settled with the bolts stood down in the review's fixes below.
- This set had no mirror at dusk or at night, which is how the mirror's lamps (the review's must-fix, below) went unseen:
  the night water poses (`poses-nw`, ten) belong in it, and the review's fixes give their figures. The second review
  added two as regressions for the mirror's sprite twins: the held helicopter's navigation lights reflected in the
  Delaware (`mx-heli-n`: with `?mirz=0` 2.77% of the pixels over 24 levels from main, against 0.17% for the twins and a
  noise of 0.10%, a sprite kind, the flight lamps' Points, the first set did not exercise) and a 0.35 m graze at
  Boathouse Row (`mx-low-n`). The list is twelve poses now (scratchpad perf/phase1/fix2/work/poses-nw.json).
- WebKit, 16 computer poses at 3024 by 1954 and 12 on the phone path (lossless PNGs): B against A mean 0.0 to 1.7 on
  the computer, 0.3 to 2.8 on the phone (traffic and pins coming and going), the same picture. The marker pins in Old
  City were missing from the second arm of the computer run; rerun with B first and `?zbuf=log` second they show in B
  and are missing from the second arm again: the harness's second view, not the depth.
- Picks and taps: `pickAt` at 35 points from the air hits the same object at the same distance and point in A and B;
  four building taps open the same cards.
- `?real=0`: eight poses, the old palette under reversed Z against it under log depth: the same fine edge speckle
  (aerial 4.1, Glory 0.1), the same picture; the only console lines are the old 'Unable to serialize Texture' warnings.

### Not done
- City Hall's balustrade cut stays in its main program (fix2 folded it back because log depth gave the split nothing);
  under reversed Z a program that discards keeps its early test only in part on Apple's GPUs, and splitting the cut back
  out would buy something at City Hall close up. Not measured separately.
- Anything that ever stands over 400 m (the storm's lowest base) other than an aircraft would need the aircraft's
  treatment; today the tallest thing in the city stands at about 357 m.
- iOS: untested on a phone (no device here). The `zc` beacon will answer from Mike's iPhone, and the clip test now
  refuses an implementation that lists the extension and does not clip by it.
- Android: held on log depth (the review), which departs from the task's "reversed wherever the probe passes" and is
  Mike's decision, not a finished one. The reason: the phone path draws into its own 4x RGBA8 and 4x float depth target
  and blits it; on the Mac that took the place of the canvas's own multisampled backbuffer, which was real memory too,
  but Chrome on an Android tiler resolves an antialiased canvas for nothing (implicit-resolve multisampling), where these
  buffers would add about 48 bytes a pixel and a resolve pass. Until one device is measured an Android phone keeps the
  old path and its beacon says what it could have had (`loga.111.-`: how many Android phones could take reversed Z);
  `?zbuf=rev` tries it. One measured device (its memory and its frame, `?zbuf=rev` against the default) lifts or keeps
  the hold.
- Windows (D3D11): `DEPTH32F_STENCIL8` is 8 bytes a sample there against `DEPTH24_STENCIL8`'s 4 (on Apple's GPUs the 24-bit
  format is already stored as the float one, so nothing changes): about 40 MB more at 1080p and 165 MB at a 4K screen at
  1.5, over the post target, the occlusion copy and the mirror. Untested: watch the desktop beacons from Windows.
- Not this round's, and the same in main: the first frames after Enter compile 37 to 49 programs (0.7 to 1.6 s), the 17th
  frame of a first flight 57 more (about 1 s) and the first night 15 more (the mirror's sprite twins, which added five
  there and nine at Boathouse Row, are built behind the veil since the second review); every jump waits 3 to 240 ms on
  the pins' synchronous read. Phase 2 material.
- Phases 2 to 5 of the plan (visibility, the frame budget, the far picture, the near-first load).

### Renders and data
- scratchpad perf/phase1/build: work/sheet-desk-1..4.jpg, work/sheet-ch2-1.jpg, work/sheet-phone-1..2.jpg (A, B, L,
  |B-A| x4, |A2-A| x4 per pose; the statistics in work/parity-*.txt), work/sheet-wk-desk-1..2.jpg and
  work/sheet-wk-phone-1..2.jpg (WebKit), work/sheet-real0.jpg, work/plane4-crops.png (the aircraft), work/crop2-*.png and
  work/final-mirror.png (the mirror), timing/*.json and timing/table-chrome.txt, the tools in tools/ (tri.mjs with an arm
  per page, wk2, shots.sh, parity.py, wksheet.py, table.py, memory/).

### Round 192, the review's fixes (Oct 14)

An independent review of the commit above (parity in Chrome and in real WebKit, correctness, performance) found one thing
on the screen and a list of loose ends. Its parity set had something the first one did not: the river mirror at dusk and at
night (`poses-nw`: the Delaware from 5 m under the Ben Franklin Bridge on an Eagles night and on a plain one, the bridge's
span and the river from 90 m, the towers from the south at 40 m, Boathouse Row from the water and from 30 m, Penn's
Landing at 40 m, and the Delaware at dusk and by day). Those poses are in the round's parity list now.

- The mirror's lamps (the must-fix). At night the far shore reflected as a broad amber band across the whole width of
  the water where main shows thin, sparse streaks, in Chrome and in WebKit; `?refl=0` made the branch match, and the
  review's energy probe (the mirror image's summed light, objects taken out one by one) put all of the difference on the
  Points objects, the streetlamps' glow most (4,602 in main, 9,632 here, at Boathouse Row). The cause is the mirror's
  reversed oblique row: its depth is 1 - k h / d, h a point's height over the water and d its view depth, which falls along
  every ray from the mirrored eye (so every surface sorts true) but is not a distance, and a point sprite carries its
  centre's one depth over every pixel it covers. The upper pixels of a far lamp's glow stood nearer than the walls and the
  ground in front of them, and drew. Under log depth the mirror's depth was the distance and the sprite stayed hidden.
  The fix: in the mirror's pass every Points object draws a twin of its material (`MIRZ`, `mirzTwin`, `mirzSwap`) whose
  fragments write the depth of their own pixel on the sprite's plane, the plane square to the view at the centre's depth,
  which is the sprite a distance depth draws; over such a plane the oblique depth is linear in the window's pixels, so one
  slope (the row's x and y over the projection's scale, per pixel) serves every sprite. Then a second, smaller cause showed:
  with the twins alone the Delaware's far shore still put 35% more lamp light into the mirror, all of it lamps past 3.5 km.
  Log depth's far plane (the mirror camera's, its reach) clipped the streetlamps' glow and the wet air's halo, whose log
  depth is the vertex's own (Round 168), and the reversed row's tilted far surface lets a low far lamp through; the twins
  clip those two past the mirror's far plane and put every other point past it on the far plane, behind whatever the
  mirror drew there, as log depth did. The scene pass draws the originals, which keep their early depth test; under log
  depth there are no twins. `?mirz=0` or `__dbg.mirz(false)` is the A/B; the review's other option (the plain reversed row
  and a height discard in every program of the mirror) would have compiled every program twice.
  Measured, the share of pixels over 24 levels from main, the review's figure / now / a second main (the noise) / now
  under `?zbuf=log`: Boathouse Row from the water 2.15 / 0.09 / 0.04 / 0.05%, the Delaware with the lights off 4.05 / 0.48 /
  0.42 / 0.50%, the Delaware on the Eagles night 4.49 / 0.50 / 0.36 / 0.47%; the other seven poses at the noise but for the
  traffic and the live flights, which differ between the two builds' code paths (the log fallback has this build's and
  shows the same). The energy probe, four loads of each interleaved: Boathouse Row 12,996 to 13,629 in main, 13,120 to
  13,545 here (+0.8% on the means; the log fallback 13,393; 18,562 with the twins off), the Delaware 22,365 to 22,369
  against 22,227 to 22,257 (-0.6%). WebKit (the check's harness, A, B and a second A): the Delaware 0.050% (the review's
  1.475, noise 0.000), Boathouse Row 0.061% (2.198, noise 0.157). The twins cost nothing measurable: the night water poses
  at Retina 0.36 to 0.60 of main's frame and within a millisecond of `?mirz=0` either way, at 1 MP 0.46 to 0.64.
- The guard per target. One slot that any render emptied let a clear on T, then an orthographic render on T or a reversed
  one on U, hand T's next reversed render a depth at the near plane (the review's latent case; no pass does it today). A
  WeakSet of cleared targets now, each kept until a reversed render draws there (`ZREV.clr`); the tests run both
  sequences. In the page it still guards only PMREM's probe faces, 24 a pose.
- A float depth target that fails at run time. The probe tries 16 by 16; a full-size target that came back incomplete
  drew black for the session, the two-step blit was recorded as working unchecked, and `zc`'s trailing 0 read only the
  scene target. Now `zrevFail`: the first failure leaves a crumb (`philly3d.zbuf`, when and what) that keeps every load
  for a fortnight on log depth, as a death keeps a phone's tier, and a `zbuf` beacon; a lost frame (the post pipeline's
  target, the phone's own, both blits) reloads once onto log depth (sessionStorage stops a loop), a lost mirror or
  occlusion copy switches that pass off for the session. `zc`'s 0 covers all four targets and the blit.
- The extension seen to work. A driver that lists `EXT_clip_control` and still clips by the old volume would draw every
  frame wrong with no way back; the throwaway context now draws one point at z = -0.5 w and one at +0.5 w under ZERO_TO_ONE
  and one at -0.5 w after switching back, and only the first may vanish (`zrevClipWorks`). `zc` carries the answer as a
  third digit: `rev.111.p` on the computer and `rev.111.d` on the phone path, in Chrome and in WebKit.
- Android phones keep log depth until one is measured: the phone path's own 4x targets took the place of a real
  multisampled backbuffer on the Mac, but Chrome on an Android tiler resolves an antialiased canvas for nothing, and there
  the targets and the blit would be about 48 bytes a pixel and a resolve pass more. Their beacon says what they could have
  had (`loga.111.-`); `?zbuf=rev` overrides this and the crumb.
- Pins through buildings, re-measured run by run. The capture skill's `pin_through.js` drew its ground truth into a 16-bit
  depth, which under reversed Z loses about 20 m at 1 km; it takes a float depth texture now, in both arms. Six runs along
  Old City to City Hall (a turn over Old City at 60 m, the flight to Independence Hall at 45 m, a turn at Washington Square
  12 m up, the flight to Broad and Walnut at 30 m, on to City Hall at 70 m, a turn by City Hall at 25 m; every pin layer
  on, the concert fixtures for placards), each with its own truth pass: on a computer at 60 a second (2,733 frames) 0 pins
  through in main and 0 here, placards 4 in main and 0 here; on the phone path at 30 a second (1,369 frames) 70 in main and
  69 here, run by run 15 / 15, 41 / 40, 10 / 10, 3 / 3, 1 / 1, 0 / 0 (Round 169's residue, frames a phone draws no image).
- Storm parity. A storm's synthetic bolts fall at random moments, so two storm captures differed by a flash (the review's
  +4.3 and +3.0 levels) and main against itself moved too. `?bolts=0` or `__dbg.bolts(false)` stands them down as a live
  lightning feed does (main patched alike for the comparison): six storm poses on the computer at +0.01 levels over the
  frame against main, main against itself 0.00 to 0.01; the phone path's two +0.05 and +0.06 against a noise of 0.05; the
  WebKit phone path's tower storm +0.12 against +0.04. What remains over the noise there is live flights.
- A phone's far mid-rises (see The depth mode): a decision, explained above.
- Phone memory, re-measured (measure.mjs, phone emulation on SwiftShader): GPU by the hook 873 / 906 / 930 MB in main and
  886 / 919 / 943 here, live heap 126 / 137 / 138 and 126 / 136 / 138, peak 279 in both: as before the review.
- The wording: the controller's note, the extra context, the City Hall comments and pinOccCam's, all corrected above and
  in the code.
- Not taken: a measured Android device and a measured Windows machine (none here: the hold and the beacons instead);
  splitting City Hall's balustrade cut back out (not measured); finding a fault in main's vertex-depth twins (they are
  the originals compiled with one `#undef`; the difference is the per-sample depth, and the phone now draws as a
  computer does).
- Tests: `tests/test_zbuf.py` 17 (the twins' depth against the oblique row on 1,548 sprite pixels, worst error 3e-16, and
  everything on a pixel's ray in front of the sprite's plane hides it while the bare centre depth let some through; the
  depth-mode choice under Node with fake contexts, the clip test, the crumb, its fortnight, the Android hold and
  `?zbuf=rev` over both; `zrevFail`; the guard's two new sequences); the suite 854.
- Renders and data: scratchpad perf/phase1/fix1: work/cmp-nw/sheet-*.jpg and work/nw-crops-fix.png (the night water,
  A, B, |B-A| x4, |A2-A| x4), work/cmp-gen, work/cmp-stm and work/cmp-ph (the general, storm and phone sets),
  work/pin-through.txt, timing/nwt-*.json, tools/memory/meas-*192f.json, raw/wknw2.json and raw/wkph.json (WebKit).

### Round 192, the second review's fixes (Oct 14)

A second independent review (correctness, parity, performance) of the two commits above found one thing that had to be
fixed before this ships and a list of smaller ones. The corrections to the entry above (the parity paragraph, the sky
alone, the controller and the Android hold as Mike's to know and decide, the old two-digit `zc` figures) are made in
place; this is what changed in the code, and what was measured.

- A lost context was read as a float-depth failure (the must-fix). On a lost context `checkFramebufferStatus` answers
  36061 and `getError` CONTEXT_LOST_WEBGL, and any frame that changes the drawing buffer's size between the loss and the
  webglcontextlost handler (a resolution trial undone on the first frame back from the background, a step, `fitView`)
  ran the checks: the reviewer's repro (`forceContextLoss`, the ratio times 0.9, one frame) wrote the fortnight's crumb
  (`post 36061` on a computer, `sub 36061` on the phone path), a false `zbuf` beacon, `zc` with its trailing 0, and set
  off a zbuf reload that could beat the handler's own recovery and skip its `bootMark('ctxlost')` and lite bookkeeping.
  iOS takes the GPU back from a page in the background routinely, so Mike's iPhone was the likely victim: every load for
  a fortnight on log depth. Now nothing is judged on a lost context (`zrevLost`): `zrevFail` does nothing there, and the
  scene target's, the phone target's, the mirror's and the occlusion copy's checks and the blit's return before they
  record a status, so `zc` carries no 0. The same repro on this build: no crumb, no reload scheduled, no warning, `zc`
  `rev.111.p` and `rev.111.d`. `tests/test_zbuf.py` runs `zrevFail` on a lost context (no crumb, no beacon, no reload,
  no sessionStorage mark) and holds every check's guard in place.
- The phone's blit is checked at once. Its first present was the first frame's, and the frame loop starts after the
  whole build (the build's renders into the phone's own target are never shown), so a canvas that took neither blit
  reloaded onto log depth only after a full phone build. The new target is now presented once at once, during the
  build's first render behind the veil (an empty frame: WebGL zeroes a new renderbuffer), `zrevPresent(true)`. With the
  review's injected blit failure the reload came 2.8 s into the load, at 'Raising the Outer Districts, 33%', against
  20.6 s, after Enter, on the commit before; the second load came up on log depth through the crumb (`logc.111.-`) both
  times. A normal phone load: the check at 2.25 s, `ready` at 19.3 s, the direct blit, `rev.111.d`.
- The mirror's sprite twins are built behind the veil. They compiled in flight: the review's hitch run counted 20
  programs on the first night frame that showed the river against main's 15 (25 against 20 across the night), and the
  wet air's halo's twin on a rainy night's second frame (350 ms against the build's steady 150). On the second frame
  (the halo is made on the first) `mirzWarm` draws every Points object the mirror may draw through its twin into a 4 by 4
  scratch target, with the mirror's own lights and settings, the points alone on layer 30, each forced visible and
  unculled for the one draw and everything put back: ten points, eight programs, 24 to 28 ms. The same hitch run on this
  build: the first night frame compiles 15 (main 15) in 152 ms (main 278), the night 20 (main 20), the rain 3 (main 3),
  and `MIRZ.made` stays at the warm's count through the night water poses.
- `zc`'s `p` read `ZREV.sub`, the throwaway context's float answer, where the real context's post pipeline is what draws:
  it is now the blit that ran, else `p` whenever the real context's post pipeline is on (cosmetic: where the two disagree
  the composite draws to the canvas itself).
- The 250 ms rule on a paced phone (it was asked for the Mac, and runs everywhere): kept, with the test the review asked
  for (The Mac's resolution controller, above): first-flight compile clusters move nothing on a phone held back by
  geometry.
- Parity method, in the handoff and the capture skill's new 7d: traffic, ships and flights off in parity poses (the
  traffic's reconcile runs on real time, so a faster build spawns cars elsewhere; ships still arrive over the WebSocket
  when `ais.json` is blocked; live aircraft and their pins were every top difference block of this round's general
  set), storms with `?bolts=0`, a cloud-switch pose held relative to the current drop (presets ease, tau 1.8 s), and a
  second main run taken in the same session (this round's phone set caught a main run whose live weather landed
  differently: a mean of 21 to 33 levels at night, main against main).
- Not taken: gating the 250 ms rule to `!PACE.on` (the test shows no need); the VDEPTH look and the Android hold, which
  are Mike's (The depth mode, Not done); a Windows measurement (no machine here).
- Parity, this build against main (twelve night water poses with traffic, ships and flights off but for the held
  helicopter, four arms): 0.012% to 0.171% of the pixels over 24 levels against a noise of 0.000% to 0.083%, the
  helicopter's lights in the Delaware 0.038% (noise 0.000; the review's 0.17%), Boathouse Row at 0.35 m 0.083%; the
  second B matches the first exactly, and the top blocks are the PATCO train's pin (its timetable runs on real time). The
  general set (24 poses): at the noise or within its pattern but for live flights. The phone path: the far mid-rises as
  before (745 m overcast 1.19%, Liberty 0.65%, the CTC 0.72%), the rest 0.07% to 0.36%. `?real=0` and the log fallback
  are untouched by this round's code (the warm needs the mirror, which needs the realistic look and reversed Z).
- Timing, interleaved A (main) and B (this build) blocks in one headless Chrome on Metal, minimum ms and B over A:
  Retina aerial 106 / 60 (0.56), sp90 122 / 56 (0.46), Broad 173 / 33 (0.19), Sansom 186 / 26 (0.14), Spruce 170 / 48
  (0.28), waterfront 65 / 46 (0.71), night aerial 113 / 63 (0.56), rain 123 / 56 (0.46), storm 97 / 59 (0.61), City Hall
  0.11 to 0.15, Glory 0.19 to 0.28, overcast sp90 0.50, the flight 0.40, the Delaware graze 0.53, Boathouse Row 0.46, the
  overcast sky 147 / 143 (0.98); 1 MP 0.27 to 0.83 (the overcast sky 0.99); the phone path 0.44 to 0.84. WebKit (the
  check's WKWebView, A and B interleaved): Retina 0.09 to 0.57 (aerial 115 / 65, Sansom 205 / 27, City Hall's market
  front 222 / 19), the phone path 0.41 to 0.84; `rev.111.p` with the warm's ten points and eight programs (34 ms), and
  `rev.111.d` with the direct blit checked 2.5 s into the load; no console messages. Draw calls and triangles match pose
  for pose, but where a run's earlier poses leave the two tabs in different states, as the review saw (Spruce at Retina
  507 calls and 7.88 M triangles in A against 672 and 10.42 M in B; the waterfront at 1 MP 538 against 425).
- Phone memory (measure.mjs, A B A B): GPU by the hook 873 / 906 / 930 MB in main and 886 / 919 / 943 here, live heap 126
  / 137 / 138 and 126 / 136 / 138, the padded-copy audit the same in both; peak live 279 and 279 in main, 278 and 298
  here, the 298 at 7 s ('Laying Out the Ground', before anything this round touches has run; 86 to 96 there in the
  other three runs), so noise.
- Tests: `tests/test_zbuf.py` 18 (a lost context leaves nothing; every check's guard; the phone target's at-once check
  and its place after the status; the warm's wiring, its layer and its restore; `zc`'s `p`), `tests/test_dpr_controller.py`
  21 (the paced phone through first-flight hitches, under the new rule and the old); the suite 856.
- Renders and data: scratchpad perf/phase1/fix2: work/cmp-nw (the twelve night water poses, A, B, a second B, a second
  A), work/cmp-gen and work/gen-tops.png (the general set, its top blocks all live flights), work/cmp-ph (the phone path),
  raw/cl-desk.json and raw/cl-phone.json (the context loss), raw/p-blitfail-after.json and raw/p-blitfail-prev.json (the
  blit), out/hitch-retina.json (the compiles), timing/ (Chrome Retina, 1 MP, the phone path and WebKit), mem/meas-f2*.json
  (phone memory), work/vdepth-decision-phone-ov745.png (for Mike), work/fl-lots-strip.png and work/crop-lots2.png (the
  stadium's bowl, from the review).

## Round 192, at the merge (Oct 14)

- Mike's answers to the plan's questions (asked with the investigation): sharpness over smoothness on both devices (the iPhone
  keeps Auto's 30 fps with headroom spent on resolution; a computer keeps full sharpness always), the city may open before the
  far ring is built, and the far city as a cached picture may be tried. So `GFX_PERF.desk`'s Auto and Sharper hold their top
  (min = top): the controller this round freed to count a slow frame never steps a computer down; Smoother keeps its ladder
  (`tests/test_gfx.py`, DeskSharpness).
- The phone's VDEPTH look: shipped as the review found it. Under reversed Z a phone's mid-rises 1 to 2 km out lose main's
  darker pilaster and floor lines and draw as a computer draws them (1.19% of pixels at 745 m); that matches the computer,
  so it was taken as the answer and named to Mike, who can ask for the old lines back.
- The last review's three robustness items, fixed at the merge: `zrevPresent` drains every error left from before (up to 8,
  as `zrevCheck` does) before it judges its first blit; `zrevFloatDepth` reads the renderbuffer's format back and answers -1
  when the float storage did not take (out of memory at full size left three's 24-bit depth in place, which completed);
  `zrevFail` with storage blocked reloads once onto `?zbuf=log` in the address instead of leaving a lost frame black.
- The Android hold stands (log depth on an Android phone until one is measured).

## Round 193 — the glass towers (Oct 14)

- Mike: "Can we also update the glass textures of the skyscrapers that are glass?" (after the storefronts: "it looks better,
  but it isn't where I want it to be"), with the frame rate under review in another workflow, so the new glass may not cost
  more GPU time than the glass it replaces. Built on `look/glass` from the round's survey and spec (renders of today, the
  references, today's measured cost).
- What was there: the researched glass towers drew a procedural curtain wall (`outerGlassMat`: a world-space grid of bright
  lines over a vertex colour) and most of them, under a Round 188 skin of a generated tile 12 cm in front whose glass was a
  photograph with the sky painted in; an unresearched tower whose tile was glass drew the fabric's whole facade under its
  skin. Every glass surface reflected refreshEnv's sky probe (a dome, a disc and nine boxes): no tower, street or river ever
  showed in a curtain wall. By day the walls read as graph paper on blue plastic, the skins as wallpaper; at night a QR-code
  speckle of white blocks on every tower with pure black between them.
- One draw per glass wall. Under `GLASS_ON` (REAL, WebGL 2, no `?glass=0`, 512 fragment uniform vectors) a researched glass
  wall lays no skin, and an unresearched tower whose cladding kind is one of the ten glass kinds (`skinKindOf`, the same draw
  factored out of `towerSkinNote`) puts its walls on the curtain-wall material as style 30 with its kind's system and its
  roof on the fabric chunk (`appendBuilding`'s new `capCh`: the roof art, snow, night glow and kit stay); on a computer so do
  the mid-rises the cladding would have dressed in glass or unitized panels (`midSkinKindOf`). Routed at load: 78 researched
  glass footprints, 197 generic towers, 234 mid-rises (a computer's), 51 OSM glass parts; 67 skins not laid. A pitched roof
  keeps the fabric and its skin; the far ring keeps its skins.
- Sixteen curtain-wall systems (`glass_systems.json`, each with its sources): bay, floor, module, F0, transmittance, coating,
  pane bow and roller wave, spandrel, frame (colour, metalness, roughness, whether the authored colour tints a one-material
  frame), rooms, an upper datum, low-iron corners, a lobby; F0 and transmittance from Vitro's data (modern low-e 0.07 to 0.12,
  the 1980s reflective coatings and Cira's silver 0.20 to 0.35). Every towers.json glass tower has its system and glass colour
  (in the towers' register, hex x 0.66); FMC's floor is its LED rings' 4.0, Comcast's its crown's 4.15, the CTC's its units'
  4.42. The system rides the aSFT floor byte as `-(sys + 1)` (`glassFh`): no new stream.
- The art (gpt-image-2, quality high, four at a time, every image read): sixteen straight-on elevations, one a system, the
  vision glass a flat chroma-key green and the spandrel or railing glass a flat magenta (all sixteen keyed cleanly the first
  time). `bake_glass_art.py` finds each one's repeat, aligns every repeat to their mean and folds them into one module (the
  model never draws two bays alike: a global period alone blurred every mullion by its drift), fills the keyed pixels from
  the frame round them, and packs ONE 2048 x 1024 atlas at 64 px/m with wrapped gutters: r the vision glass, g the spandrel
  glass, b the frame's detail as its luminance over twice the frame's mean (the shader multiplies the system's frame colour by
  twice it). The first cut carried an albedo atlas beside the mask; a fragment's second fetch was a cost the old procedural
  wall never paid, so it went. Eight rooms through `/v1/images/edits` on a one-point template: the model kept the view but not
  the back wall's size (an open office three widths deep, a bedroom one), so each back wall was read by eye off a grid (`BACK`)
  and the page projects through each cell's own scale and vanishing point. 510 KB of art (a phone loads 103 KB of it).
- The shader (`glassSysHook`, one program and the phone's vertex-depth twin): each wall a whole number of bays from a mullion,
  floors from the base, the lobby the clear system's tall panes, a short top floor a parapet; the frame from the atlas through
  textureGrad on the module's continuous coordinates (isotropic; its footprint held inside the gutter, the measured mean taken
  over as the hold bites, the means alone under three pixels a pane: no tiling, no shimmer); a pixel's frame and glass summed
  by area with metalness 0; each pane bowed its own way, a hair off true, a tempered pane's roller wave, the jagged system's
  facets, the vent sashes, folded into roughness as they shrink; the glass's F0 tinted by its coating, each pane a few percent
  its own; behind the vision glass a room, at night by the clock (offices in runs along each floor, homes and hotels room by
  room, a crown's plant rooms barely, the lobby always) with interior mapping into the room atlas within reach on a computer
  (lit rooms only), the cell's mean with a ceiling's brightness further out, blinds on three rooms in ten and curtains in a
  third of the homes, past two pixels a room the runs' true share under the pixel (`gRunCover`) and, for homes and hotels,
  blocks at half contrast round the share (`gFarBlocks`), past two pixels a floor bands of floors; the light blended finished
  (Round 159); by day the kind's mean room lit through its window at the fabric's numbers. A room's choices are fractions of
  one hash a room and an office floor's of one hash a floor. Nothing in it draws the theme.
- The city in the glass (`CITYENV`): a PMREM of a proxy built in 'Mirroring the city' (1,359 towers from 25 m, the Liberty
  Places, City Hall and the three towers as extruded footprints, the low city as a box a roof cell within 5 km, 3 on a phone,
  an 8 km ground disc with the street grid), lit as the main lights are, its floors lit by the clock's shares after dark, the
  themed crowns in the night's colour, the street lamps' lines, hazed into the horizon. Two fixed centres on a computer
  (Center City, University City: each fragment reads the nearer), one on a phone at 128, each centre without the towers within
  160 m (a tower that close filled half a cube face where the parallax looks a kilometre out); baked behind the veil and
  whenever refreshEnv bakes the sky's, a centre a frame, at most every 1.5 s on a computer and 10 s on a phone, a phone only
  when still. Bound as the glass's own envMap, never `scene.environment`; the reflection ray is carried to the probe's sphere
  and the ground before the fetch (`glassParallax`). The skins that stay (masonry, stone, the far ring's) take probe A for
  their windows, F0 0.08 on their glass and the painted glass at three tenths, with no new sampler.
- Found on the way: the second probe's sampler kept the disposed target after the first refresh (University City's glass
  black: re-pointed after every bake); a blended metalness turned every far wall to grey paint; the night rooms first came out
  19% over the old mean at the low flight and twice it at a distance (now 0.8 before the glass, a far room dimmed as the
  fabric's windows are). The GPU check pages `glass_optics_gpu.html`, `window_interiors_gpu.html` and `buildings_gpu.html` were
  already failing at HEAD (`REAL is not defined` since the realism pass); `tests/glass_systems_gpu.html` is the new glass's,
  passing in both depth modes.
- Measured on this Mac (M2 Max, headless Chrome on Metal, other workflows rendering at the same time, so every number moves
  about 30% run to run): the round's harness (the glass layer alone at three times the drawing buffer each way, less the same
  draw flat, the minimum of 8 blocks), before.html and after.html alternated three times, medians of the three, ms at 9x
  pixels. Computer: street-comcast-day 3.73 -> 4.06, mid-market-day 13.30 -> 10.59, lowflight-day 5.90 -> 5.07,
  schuylkill-skyline-day 3.67 -> 2.37, lowflight-night 6.38 -> 6.04, street-comcast-night 5.12 -> 6.85. Phone path (740 x
  360 at 1.25): 1.37 -> 1.93, 6.51 -> 5.15, 1.72 -> 1.26, 0.94 -> 0.97, 2.68 -> 1.91, 2.52 -> 2.62. The glass-alone figure
  counts a routed tower's whole wall after and only its skin before (the fabric wall under the skin goes uncounted), so the
  scene pass is the fair one: at 1x, the minima 22.1 -> 20.6, 30.7 -> 34.2, 32.1 -> 31.1, 40.0 -> 41.5, 35.8 -> 36.7, 21.5 ->
  19.9 on the computer and 5.7 -> 5.8, 11.6 -> 11.9, 17.0 -> 15.6, 22.4 -> 23.9, 18.4 -> 16.6, 5.6 -> 5.8 on the phone path:
  inside the noise everywhere. Over the spec's budget, said plainly: the street views' glass alone (the computer's night +34%,
  the phone's day +41%, 0.06 ms at 1x); the interiors' reach went from 20 to 40 pixels a pane after that run. The first cut
  stood at +50% (day) and +66% (night) at the street; what brought it down: one fetch (no albedo atlas), isotropic sampling,
  by day the room's mean only, interiors for lit rooms, one hash a room and a floor, no pane hash past three pixels.
- The probe: 2.3 to 2.6 ms a centre a bake on the computer (two centres on successive frames), the proxy 71 ms to build and
  123,560 triangles over both centres' geometry; the phone path's last bake was reported here as 21 ms, which the
  integration review corrected: 2.3 to 2.6 ms CPU and 0.74 to 1.0 ms GPU a bake on the phone path (the 21 ms included the
  probe program's first compile). Memory: the computer's frame atlas 11.2 MB, rooms 9.4, two
  probes 12.6, against only the fins tile (2.7 MB) no longer uploaded (the far ring and the masonry towers still wear the
  other nine glass kinds): +30.5 MB; the phone's half atlas 2.8 and its probe 1.6, less about 1.1 of fins: +3.3 MB. Samplers:
  the curtain wall 6 of 16 on the computer (the atlas, the rooms, two probes, two shadow maps), 3 on the phone path; the
  skins unchanged (6 and 4). No link failures; the console holds only the two "Unable to serialize Texture" warnings HEAD
  has too.
- The night glass's mean over a mask of its own pixels, as first reported here (lowflight-night -5%, mid-market-night
  -18%, south-night +54%, the skyline from the river +69%), was wrong in sign for the near views: the integration review
  measured the committed build at clock 1290 over its own glass mask, sRGB luminance before -> after, lowflight-night 32.2
  -> 40.1 (+25%), mid-market-night 25.7 -> 39.8 (+55%), south-night 29.4 -> 44.6 (+52%), schuylkill-skyline-night 31.4 ->
  45.2 (+44%), skyline-se-night 36.5 -> 40.9 (+12%), and by day the same mask 21 to 23% darker. The review's fixes below
  carry the current numbers. Flicker, three PNGs 0.5 m apart, pixels changing by more than 60: lowflight-day 177,396 -> 146,090,
  south-day 148,357 -> 146,967, lowflight-night 90,591 -> 74,311. The skyline lights (`lights('eagles')` at BNY from the
  west, the Liberty Places, the Logans, City Hall and the low flight): outside the glass's mask dilated 6 px a mean
  difference of 2.5 to 5.4 of 765, every crown, LED line, neon chevron and wash where it was.
- Renders (before, after, pairs; computer and phone, day, dusk and night) in the session's `scratchpad/glass/`.
- Open for Mike: the 1818 Market and Laurel reassignments; the University City probe (6.3 MB on a computer); IBX's F0 (the band
  system's 0.16, a seventeenth system would give it 0.20) and PNC's light grey spandrels; a real iPhone's check of the probe's
  bake (2.3 to 2.6 ms CPU and 0.74 to 1.0 ms GPU on the phone path, the integration review's measure; the 21 ms first
  given here included a compile) and of the glass's cost. Not done from the spec: the frame's bevel normal and relief
  shading on the glass, the fins' sun-aware reveal, the shadow box's parallax edge, blinds by day.

### Round 192, the review's fixes (Oct 14)

- Merged main first (Rounds 190 and 191: the pins' scale, City Hall and Glory rebuilt): the round renumbered 192 (191 is
  main's), `GLASS_ART` beside `CITYHALL_ART` and `GLORY_ART`, the art check's regex taking `glass`, and City Hall in the
  city probe's proxy moved onto the rebuilt block (18.5 m north, 144 by 149 m, the tower's base 27 m square to Penn's
  167).
- The main regression (must-fix 1): every glass tower was one flat colour past a block or two. The frame atlas held each
  cell's footprint inside its 8 px gutter, faded the whole frame to its mean as that hold bit (a module under 16 px) and
  cut to the mean under three pixels a pane on the pane's narrow side, so the floor lines went with the mullions while a
  floor was still 10 px tall; the procedural fallback did the same. The frames are now one strip of sixteen 256 px square
  tiles, a system a tile, each the bake's folded module resampled periodically (Lanczos over a 3 by 3 tiling), uploaded as
  a `DataArrayTexture` with REPEAT, a full chain of mips and 4x anisotropy, sampled on the module's continuous
  coordinates: the hardware filters each axis by its own footprint and a wall goes to its measured mean only as each
  feature drops under a pixel. The procedural frame (tier 2, `?glassart=0`, before the art lands) is the exact box filter
  of the vision band and the mullions per axis (`gBand`, the integral of a periodic interval over the pixel's footprint;
  tested against brute force). No isotropic footprint is left in the glass. The strip is 5.6 MB of GPU memory with its
  mips against the atlas's 11.2 (a phone's half strip 1.4 against 2.8), and 252 KB to download.
- Colour (must-fix 2): the first cut took every frame, spandrel back and proxy colour from sRGB to linear, but this scene
  runs the legacy pipeline (handoff gotcha 11: a hex is its own working value), so frames, shadow boxes and the whole
  mirrored city were drawn at about half the brightness of every other wall; the proxy's haze also took the dome's horizon
  to linear, a dark band where the sky should meet the city. Fixed at the root (`glassCol`, `lin2s` for the bake's linear
  means) rather than compensated. The proxy is lit as the scene is (the key, the hemisphere and the sky's own fill, which
  every facade takes through its probe at 0.9), its walls carry their storeys' windows (a band a floor, box filtered), the
  air between the centre and each wall takes the scene's own extinction toward the dome's horizon. The frames' diffuse
  fill is now the sky probe's (its dome over its street and boxes, two uniforms, no fetch), never the city probe's lit
  windows. Painted mullions and caps are paint (PVDF), so the systems' frame metalness went from 0.6 to 0.85 down to 0.25
  to 0.45; Comcast's flush joints are dark silicone and its shadow boxes' pans a lit mid grey (through the glass: 0.2 +
  0.7 of its transmittance, not 0.4 of a dark pan); Liberty's frame is painted to its glass's blue grey, its coating takes
  0.95 of its blue (F0 0.21); the CTC's caps a lighter grey; the residential wall's slab covers a weathered light grey
  rather than the art's white.
- A calibration test (`glass_calibrate.py` writes `tests/glass_calibration.json`, `tests/test_glass_calibration.py` checks
  it): each researched tower's glass over the mask at the standard noon poses against its reference swatch, CIE76 delta E
  at most 15, with a fingerprint of the glass's GLSL and systems so an unmeasured change fails. Measured on the final
  build (sRGB means over the tower's glass, delta E): Comcast 125,137,143 (skyline from the south-west, 10.1) and
  124,132,134 (the low flight, 12.9) against #8FA3AE; the CTC 140,148,151 (12.5) and 141,149,153 (from the south, 12.0)
  against #A9B6BA; One Liberty 127,145,157 (14.2) and 116,132,144 (12.6), Two Liberty 123,143,155 (12.9) and 110,128,140
  (11.6) against #5D7F9E; Cira 139,155,163 (10.2) against #A7B5C0; The Laurel 154,156,155 (8.0) and 152,150,145 (5.0)
  against #8E8A82. The first cut stood at Comcast 74,85,91 (dE about 35) and One Liberty 133,147,155 (20.5, B - R 14) on
  the same measure; One Liberty is now B - R 29. Over the whole glass mask by day, main -> the first cut -> now: the
  skyline 143,157,161 -> 110,120,126 -> 140,148,151; the low flight 141,153,155 -> 109,116,118 -> 139,144,145; the street
  at Comcast 101,119,129 -> 69,87,101 -> 91,106,117; from the south 123,137,140 -> 98,106,110 -> 128,134,136; the
  Schuylkill's west bank 105,113,114 -> 75,83,88 -> 106,113,116; mid-Market 126,136,137 -> 92,102,107 -> 116,124,127.
- The night far field (must-fix 3): no lit shape larger than a floor's run under two pixels a room. The glass's own blocks
  of rooms (`gFarBlocks`, 2^L rooms by 2^M floors) are gone: an office floor past half a pixel is the mean of three taps
  across the pixel's footprint, each its own floor's run (its true share along the wall, `gRunCover`) at its suite's
  level, so the strips stay a floor high until a floor is under a pixel and then give way to the share; a home's specks
  are the rooms at the pixel's four corners at each lamp's own level (the skew toward the dim: a far wall is a scatter of
  dim and bright specks, never a beige field), then the share; the far glow 0.08 a lit room's luminance on a computer,
  0.10 on a phone. A lobby is a band at 2.5 times it.
- Dusk (must-fix 4): the rooms' light is by the ambient light (`glassRoomLevel`: full from three degrees under the
  horizon, rising through the five degrees over it with the overcast advance), not the night term, which at 18:25 on Oct
  14 is 0.01; who is lit is the clock's occupancy, and the falling reflection reveals them.
- The probe (must-fix 5 and the integration review): it bakes on the frame refreshEnv asks (a three-degree sun step, a new
  clock, the weather's key), right after applyLighting and on every device, with no gap, no stillness rule and no bake in
  the build before the clock's lighting; between bakes it is scaled by the sky's light over its light at the bake
  (`uCityEnvK`, never over 1). Checked headless on the phone path: renders 1, 2, 3 across day, night and day poses; a
  `#t=...,1290` link's first frame baked at night (level 1, dark glass). A bake costs 2.6 to 4 ms on the phone path and
  2.6 ms a centre on the computer after the first (the first, with its compile, 12 to 21 ms behind the veil), not the 21
  ms the first report gave. The skins keep the sky probe for their walls' fill; a computer's skins read the city probe
  only for their windows' radiance within its sphere (`uCityEnvA`, one sampler more: 7 of 16), their painted glass at 0.6
  there and the Round 188 glass beyond it; a phone's skins are Round 188's exactly. The probe is off on the recovery tier,
  its proxy arrays are dropped on upload, and it holds no sun sprite: the glint is the key light's, sharp and broken pane
  by pane.
- The mirrored city (must-fix 6): the low city's boxes stand at their roof cell's height (to 40 m), 60 m wide, brick,
  stone and stucco at a block's mean with darker roofs and their storeys' windows, none within 350 m of a centre; a ray
  whose hit lies within about 80 m, and a low wall's level ray (the street's far side is tens of metres off, where the
  sphere puts a city a kilometre out), reads the probe blurred toward its mean. A fragment outside the sphere reads its
  ray as it is (the integration review's port: a sky ray 37 degrees up fetched the ground).
- The glint (must-fix 7): the folded roughness is capped at 0.095 (it reached 0.24 on a phone's small panes), each pane
  keeps its own tilt (8 to 22 mrad, wider where its bow is no longer drawn; the second review corrected the 4 mrad this
  line first said) and tint to about two pixels a pane on every device, and the probe's sun sprite is gone
  (blurred by the probe's mips it was a second, soft sun several degrees across).
- The Laurel and 1919 Market are residential towers and now wear the residential wall (homes lit room by room); the other
  towers on the unitized office system are offices or labs (3025 JFK is labs over flats: left on it).
- The review's other points: Comcast's low-iron corners are a paler, clearer band in the glass's own colour, their share
  under the pixel (no bright one-pixel line); 1818 Market's precast ribbons carry the concrete's grain and the dirt its
  sills wash down (near the eye, under 6 cm a pixel); the panes' own tint and tilt stay to about two pixels a pane; the
  rooms' pictures are decoded on the first dusk (a computer's 9.4 MB not held through a daylit session) and the unused
  half copy is no longer baked; a lit room's picture is sampled at the projection's own footprint with 2x anisotropy and
  only lit rooms pay the fetch.
- Declined or left: the frame's bevel normal, the fins' sun-aware reveal and the shadow box's parallax edge (unchanged
  from the first report); the University City probe (6.3 MB) stays for Mike's call.
- Cost, re-measured as the first report did (the glass layer alone at three times the drawing buffer each way, less the
  same draw flat, the minimum of 8 blocks; main's page and this one alternated three times, medians of the three; another
  workflow rendered on the GPU through some of it, so about 30% is noise): computer, ms at 9x, street-comcast-day 4.53 ->
  4.97 (+10%), mid-market-day 14.14 -> 11.93 (-16%), lowflight-day 5.72 -> 5.14 (-10%), schuylkill-skyline-day 2.66 ->
  3.27 (+23%), lowflight-night 6.56 -> 6.91 (+5%), street-comcast-night 5.45 -> 7.02 (+29%, about 0.17 ms at 1x: the near
  rooms' pictures; only a lit room fetches one now); the phone path 2.11 -> 1.65, 5.92 -> 3.42, 2.39 -> 1.60, 0.84 ->
  0.80, 2.12 -> 2.29, 2.60 -> 2.79. The scene pass at 1x, the fair comparison (it counts the fabric walls the routing took
  away), medians: 33.0 -> 28.9, 38.0 -> 36.8, 42.1 -> 44.6, 51.9 -> 55.7, 46.1 -> 49.0, 32.2 -> 30.4 on the computer and
  10.6 -> 8.2, 15.3 -> 17.3, 20.4 -> 24.8, 24.4 -> 25.5, 21.0 -> 23.6, 7.6 -> 8.8 on the phone path, inside the run-to-run
  noise. The frames' anisotropy is 4 (8 measured no different within the noise), the rooms' 2. Probe: 3.0 ms a centre a
  bake on the computer (3.9 averaged with the first, which compiles), 2.8 on the phone path (3.2 averaged); 123,100
  triangles over the computer's two centres, 37,025 on the phone, freed from the heap once uploaded. Memory: the frames'
  array 5.6 MB with its mips on a computer (the atlas was 11.2), 1.4 on a phone (2.8); the rooms' 9.4 MB only after the
  first dusk; the probes as before (12.6 and 1.6). Samplers: the curtain wall 6 of 16 on a computer (the frames, the
  rooms, two probes, two shadow maps), 3 on a phone; a computer's skins 7 (the probe for their windows), a phone's 4 as
  before. No link failures; no console errors on any run of the final build.
- Night and dusk over the glass's own mask, sRGB luminance, main's page -> this build, clock 1290 (dusk 1105 and 1112):
  the skyline from the south-west 33.6 -> 35.7 (+6%), from the Schuylkill 30.6 -> 37.8 (+24%), the low flight 31.8 -> 39.9
  (+26%), from the south 28.7 -> 38.4 (+34%), mid-Market among the towers 25.6 -> 43.8 (+71%), the Laurel from Rittenhouse
  28.1 -> 38.9 (+38%), the street at Comcast 54.2 -> 34.7 (-36%: main drew Comcast and the CTC under lit skins); dusk the
  skyline 45.4 -> 66.6 (+47%), the river 48.8 -> 67.9 (+39%), the low flight 44.5 -> 75.0 (+69%). The far skyline is
  inside the spec; nearer, the excess is the lit rooms of glass walls (two thirds of a curtain wall is vision glass
  against a third of a masonry front's windows, and the routed generic towers were masonry skins in main) and the glass's
  reflection of a lit city, not a slab: no lit shape is larger than a floor's run under two pixels a room. Homes' lamps
  are a third of an office's (the pale beige residential towers of the first pass). Flicker (three PNGs 0.5 m apart,
  pixels changing by more than 60, main -> this build, now that the patterns are back): lowflight-day 153,603 -> 188,302,
  south-day 130,594 -> 142,392, comcast-200m 304,615 -> 291,121, lowflight-night 95,710 -> 102,665, skyline-sw-night
  48,583 -> 47,686.
- The skyline lights on an Eagles night (`?lights=eagles`, the integration review's six poses): every crown, LED line, the
  Liberty neon, City Hall's wash and the CTC's blade where they were; what differs is the glass's own windows. `?real=0`
  against main's `?real=0`: identical glass, the only differing pixels the live flights' pins and the traffic.
- Renders: the session's `scratchpad/glass/fix1/final/` (the judged set and the reviews' views, computer and phone, before
  and after pairs in `pairs/`, the night sheet, the theme sheet, the flicker PNGs), the calibration's shots in
  `cal-final/`.
- Open for Mike: 1818 Market as white concrete ribbons and The Laurel as warm grey glass (the research's reassignments,
  kept); the night glass brighter than main nearer than the far skyline (a lit glass office is more lit glass than a
  masonry front; the numbers above), and the dusk lamps coming up ahead of the night term; the University City probe;
  IBX's F0 and PNC's spandrels; a real iPhone's check of the bake and the glass's cost.

### Round 192, the second review's fixes (Oct 14)

- The Liberty crowns (must-fix 1). `crown()` pushed every gable prism on the clear lantern system (`glassFh(5)`: #E8EAEA
  frames over a quarter of the module, 0.75 transmittance onto beige plant rooms), so both crowns read as a white lattice
  over tan where main and the photographs have blue glass with white edge trim. The prisms now take their tower's own
  system (`lFh`, `tFh`) and glass colour; a glazed crown (style 29, every tower's) is drawn in slim procedural mullions and
  transoms (the procedural frame's 7 cm mullion a bay, 16 cm of transom a floor), never its wall's tile (Liberty's
  granite bands and caps, the lantern's white frames), with plant behind it whatever its tower's rooms. The rows of dark
  dashes on the chevrons were the sloped glass carrying the wall's frame tile in its specular (its frame's F0 was never
  reset) and each pane's tint and roughness; sloped glass is now one sheet of its system's glass (no frame, no pane's
  tilt, tint or roughness), with twice a wall's grime and its coating's tint at 0.8 (it mirrors the sky above it).
  `glass_calibrate.py` measures the crown (`REGION`: One Liberty's box cut to 205 to 268 m, its colour picked at the
  crown's projected middle; the first try picked Comcast behind it from the box's top third) from the south at 130 m and
  from the south-west skyline.
- Comcast's graph paper (must-fix 2). (a) The frame and spandrel colours went in at their hex as an albedo, nearly four
  times the fabric's (a wall of hex X is drawn at X times FACADE_GAIN 0.27): Comcast's dark silicone (#3E4447) drew pale
  grey in the sun. Frame means and spandrel backs now go in at `GLASS_PAINT` (the fabric's 0.27, a literal beside
  FACADE_GAIN, which is declared later; the test holds them equal), the body's own spandrel at 0.41 (0.27 over the body's
  0.66), and a cap at the fabric's roof gain (0.236: ROOF_GAIN over the 0.72 a routed cap keeps its colour at). (b) The
  generated Comcast elevation had about 148 mm a vertical joint and 266 mm of opaque frame a floor: the bake now thins a
  system's joints to `frame.slim` (`slim`, the glass grown into the frame cyclically, each axis by its own radius; the
  cell records before and after): Comcast 148 -> 78 mm and 266 -> 141 mm, the generic unitized wall 133 -> 78 and 234 ->
  156; Comcast's frame share 16% -> 8%. (c) The shadow box is glass over a dark pan: the pan lit through the glass in and
  out of it and shaded by its own box (0.6 x transmittance squared, 0.12 for Comcast, against 0.2 + 0.7 x transmittance,
  0.52), its glass reflecting as the vision glass does. A pose 100 m off Comcast's south face at noon joins the
  calibration with a bound on the frames against the glass (`CONTRAST`: the 90th over the 10th percentile of the face's
  luminance at most 2): 1.63 now (the first cut 3.3).
- The homes' noise and shimmer (must-fix 3). An apartment is a unit of bays switched by one hash (homes 2 or 4 bays,
  3 or 6 m, by the wall's seed; a hotel room 2 or 3), its living room at its lamp, a second room at half in 55 units of 100
  and dark in the rest, blinds or curtains drawn across about two lit units in five (the glow through them 0.3). The far
  light is the units under the pixel's footprint box filtered (`gHomeBox`: each unit by its share of the pixel, exact
  while the footprint is under a unit each way and tested against brute force, continuous as the eye moves), the share's
  mean past two units a pixel; the near light is the rooms either side of the footprint along the wall, each by its share;
  the far light is evaluated only where the near does not cover it and the near only where it is seen. A home's lamp level
  is its own at every distance (under two pixels a room it had an office's). Flicker over the glass mask (three frames
  0.5 m apart, pixels changing by more than 40 in a channel and those swinging both ways, main -> the first fix -> now):
  The Laurel from 600 m at 21:30 32,609 / 3,735 -> 38,843 / 2,159 -> 21,480 / 1,307; the Arthaus from 500 m 8,112 / 495 ->
  9,491 / 322 -> 5,216 / 258; Comcast from 560 m at noon 40,520 / 6,613 -> 44,757 / 13,387 -> 19,558 / 3,310.
- The fill (must-fix 4). The probe holds the dome decoded (envSky draws `pFromSRGB(col)`), and the first fix built the
  frames' fill and the proxy's fill and haze from the dome's raw display uniforms. Now: `SKYIRR`, after each sky bake the
  probe read at roughness 1 along +x, -x, +y, -y, +z and -z (exactly what a wall's `getIBLIrradiance` reads there) into a
  6 x 1 half-float target, and the glass's fill an ambient cube of its six texels (`gIrrCube`: three `texelFetch`, no
  readback) at the fabric's 0.9 for frames and caps alike. Measured with the review's probe (a white Lambert plane lit only
  by `scene.environment`, read from a float target) against the texels read back: the ratio is 1.000 up and side at 780,
  1080 and 1290, on the computer and on the phone path. (The review's phone ratios, 13 to 110 at night, came from a plane
  drawn through the phone's tone curve: three tone maps every material into a render target there; with `toneMapped`
  false the phone's plane reads the probe exactly.) The proxy reads the sky probe itself for its fill
  (`textureCubeUV(envMap, n, 1.0)`, the sky probe's layout from `cubeUVDefines`), hazes with the city's own aerial
  perspective (fog_pars_fragment's layers and colour toward and away from the sun, `scene.fog.color`), and its colours are
  in the scene's register (walls at 0.27, glass towers' bodies at 0.41, the low city at 0.32, the ground at the city's
  mean from above, the street lamps' pools after dark). Measured against the city itself from one camera (the scene and
  the proxy rendered into float targets, the lower half's mean, `probe/proxy_eval.js`): from 700 m over South Philadelphia
  at noon the proxy reads 0.94 to 1.03 of the city (it was 0.84 with the register and the raw fill, and about three times
  over before), level from the probe's centre 0.87, the far skyline 0.88, level at night 1.05, from above at night 0.62
  (the city's orange pools are brighter than the proxy's street lamps). The pale glass roofs at night are gone (the low
  flight, BNY Mellon from the west, 1818 Market's ribbons dark at 21:30 on both devices).
- One glass program on a phone (must-fix 5). The phone's materials compiled against the 256 sky probe and again at the
  first bake against the 128 city probe, and r149 kept both. `glassSysMat` now binds an empty bake from the city probe's
  own generator before the first compile (disposed at the first real bake, the same size), and the phone's probe shares
  the water's 128 generator (`waterPmrem`: one ping-pong target for both). Headless: 2 glass programs on the phone path
  (the material and its vertex-depth twin), 1 on the computer; no link failures.
- The rooms at dusk (should-fix): the rooms come on with the street lamps' photocell (from 1.5 degrees over the horizon,
  full 4.5 under it, with the windows' overcast advance), so at 18:08 (the sun 2.5 degrees up) no room is lit and at 18:25
  a tenth are; the office suites' levels run 0.475 to 0.975 of the mean (from 0.35 to 1.1 neighbouring suites read as
  blocks). The west faces' sunset: the city probe's western horizon at 18:08 holds the University City towers lit by the
  low sun and the air's glow toward it (`probe/eq.png`; the band from the horizon to 10 degrees up averages 0.136 against
  the sky probe's 0.166 all round), so the west faces mirror a dim warm city under a blue sky; the brilliant orange of the
  photographs is the low sun's own glint, which the key light gives pane by pane where the geometry sends it, and the
  dome's own glow round the sun, which is the sky's and not touched here.
- From above, the CTC reads grey, not tan: the proxy's ground was a warm 0.3 albedo, three to four times the city's.
- The sun inside and the grime (the second review's darker register exposed them). With the frames at their real register
  and the mirrored city at the city's brightness, a curtain wall facing the sun drew as dark as one in shade. Two real
  terms: the rooms the sun shines into (the floor by the window, the ceiling's bounce, blinds lit through the glass),
  seen back out through it, `gSunInK` = 0.40 x transmittance squared in the glass's tint, added to the key light's own
  diffuse (`RE_Direct_Glass`, so a neighbour's shadow darkens it); and the glass's film of the city's grime, a diffuse
  albedo of 0.016 (twice that on a slope). The daylit room behind the reflection takes the glass's tint (in and back out
  through it: untinted, it turned every shaded tinted wall brown).
- The optics within their references: Comcast F0 0.11 -> 0.14 and its coating 0.45 -> 0.6 (Enclos: "lightly tinted and
  reflective"); Liberty F0 0.21 -> 0.28 and coating 0.95 -> 0.8 (the references give 25 to 35 per cent; at 0.95 the
  chevrons went navy), Liberty's frame #283542 -> #6E849B (its silver caps and blue-grey granite at their mean; the first
  review's dark blue had darkened a frame drawn at nearly four times its register).
- The calibration, the final build (sRGB means over each tower's glass, CIE76 delta E against its swatch, tolerance 15):
  Comcast 127,138,143 from the
  south-west skyline (10.1), 127,135,136 from the low flight (12.3) and 123,130,129 a hundred metres off its south face
  (14.4, the frames against the glass p90/p10 1.63, bound 2) against #8FA3AE; the CTC 155,161,160 (8.5) and 156,162,161
  (7.9) against #A9B6BA; One Liberty 106,124,136 (11.6) and 92,107,117 (14.8), Two Liberty 103,123,136 (11.0) and
  88,105,116 (14.7) against #5D7F9E; Cira 126,144,154 (14.3) against #A7B5C0; The Laurel 115,118,117 (9.5) and 137,134,125
  (1.7) against #8E8A82; One Liberty's crown 92,107,118 from the south (14.5) and 105,127,142 from the skyline (10.0).
  Every Liberty measure is B - R 25 or more; Comcast's means are all over 125. From the review's own pose north-east of
  the crown (its faces away from the sun) the crown is 71,90,106 against main's painted 96,118,130 through the same mask
  (delta E 17.1 against 12.0): a sunless face of blue glass mirrors the city's shaded side; it is blue, not the lattice.
- Declined, and why: the street canyon's near layer (a second probe level of the towers within 160 m, or a facade mean
  for level rays): no fragment knows whether a neighbour stands across its street or open air, so a mean blended into
  every level reflection would lighten the open views as much as the canyons, and a near probe level is a third cube on
  a computer (6.3 MB and a bake) for the street views alone; it stays open for Mike. CLAUDE.md: the rules this round
  needs are drafted below but not written into CLAUDE.md, whose changes a workflow cannot authorise; Mike, or the session
  he asks to merge this, adds them.
- Cost. GPU timing as the first report measured it (the glass layer alone at three times the drawing buffer each way,
  less the same draw flat, the minimum of 8 blocks; main's page and this one alternated three times, medians), with no
  other workflow on the GPU through the computer's runs: the scene pass at 1x, the frame's own cost (it counts the
  fabric walls the routing took away), medians main -> now on the computer: street-comcast-day 21.72 -> 21.05 ms,
  mid-market-day 23.13 -> 22.98, lowflight-day 30.62 -> 30.93, schuylkill-skyline-day 39.20 -> 40.05, lowflight-night
  34.27 -> 34.72, street-comcast-night 20.88 -> 20.68 (every pose within 3%); on the phone path (740x360 at 1.25) 5.17 ->
  5.22, 10.15 -> 10.60, 14.43 -> 14.63, 20.32 -> 19.60, 15.55 -> 15.18, 5.82 -> 5.65 (within 4%). The glass's shading
  alone, ms at 9x: computer 3.35 -> 4.70 (+40%), 18.35 -> 12.76 (-30%), 6.45 -> 6.99 (+8%), 2.84 -> 3.17 (+11%), 9.49 ->
  9.95 (+5%), 5.03 -> 7.58 (+51%); phone 1.27 -> 1.79 (+41%), 6.73 -> 5.08, 2.12 -> 1.15, 0.92 -> 0.67, 3.56 -> 4.38
  (+23%), 2.12 -> 2.58 (+22%). The close street views' excess (about 0.15 to 0.3 ms at 1x on the computer, 0.06 on the
  phone path) is the first cut's (the frames' fetch, the probe's parallax and the rooms' pictures), not this round's: the
  first fix's page measured in the same session, the same way, stood at 5.86 and 8.68 there against this build's 4.68
  and 8.15, and over it at every pose (lowflight-night 12.81 against 9.46). The far rooms are evaluated only where seen
  (`gHomeBox` past the rooms, the near rooms before them). No real iPhone was at hand: its check (the bake, the first
  frame's compile, the frame time) stays open.
- The probe: one bake a centre on each clock change that moves the sun (none for a minute's step); after the first
  (8 to 11 ms with the proxy's compile) 2.1 to 2.6 ms of CPU a bake on the computer and 2.1 to 2.5 on the phone path; the
  review's 13.7 ms average counted the first bake's compile among five. Memory, corrected: a probe target carries a depth
  renderbuffer as well (r149's fromScene sets `depthBuffer`), so a computer's two 256 probes are 2 x (6.3 + 3.1) = 18.9 MB
  (the reports said 12.6), and a phone's 128 probe 1.6 + 0.8 = 2.4 MB with no ping-pong target of its own now (it shares
  the water's: the first fix kept a second 1.6 MB one); SKYIRR's target is 48 bytes. Measured the way an iPhone counts it (the capture skill's WebGL hook on the
  phone path, swiftshader, after a forced GC), main -> now: 873 -> 874 MB of GPU at ready, 906 -> 909 after the first frames,
  930 -> 933 after the look round (the first fix measured 911 and 935), live heap 137 -> 138 MB, the load's peak 279 -> 285;
  2 glass programs (the first fix 3). Corrected by the third review, which measured this build the same way at 873 -> 874,
  906 -> 911 and 930 -> 935: +5 MB, not +3 (the frames 1.4 MB, the 128 probe 2.4 MB, the proxy's geometry the rest), still
  acceptable; this round's own measure is in its section below.
- Build time: 'Cladding the towers' 1,490 -> 1,649 ms and ready 24.8 -> 25.9 s on the computer, 698 -> 637 ms and
  19.8 -> 19.7 s on the phone path (single runs each, main -> now); 'Mirroring the city' 75 and 35 ms, 'Glazing the towers'
  4 and 2. The review's phone growth (1,189 -> 2,474 ms) was the second glass program's compile, gone with must-fix 5.
- Night and dusk over the glass's own mask (sRGB luminance, main -> now, the crowns' lights off): the skyline from the
  south-west 34.2 -> 25.4 (-26%), from the Schuylkill 31.4 -> 27.5 (-13%), the low flight 32.2 -> 22.0 (-32%), from the
  south 29.4 -> 27.8 (-5%), mid-Market among the towers 25.7 -> 24.0 (-6%), The Laurel from Rittenhouse 29.0 -> 21.3
  (-27%), the street at Comcast 53.9 -> 31.6 (-41%: main drew Comcast and the CTC under lit skins); dusk the skyline 45.9
  -> 38.2 (-17%), the river 48.6 -> 44.7 (-8%), the low flight 43.7 -> 34.4 (-21%). The first fix stood 6 to 71% over
  main; the excess was the raw fill (frames, ribbons and caps lit like dusk at night) and the homes' rooms a bay each,
  and with both gone the glass is darker than main's at night: main's curtain wall lit about half its windows white at
  every distance, this one lights the clock's share (a quarter of the offices at 21:30, the homes' units with a third of
  them behind blinds). A brighter far glow does not move it (0.08 -> 0.14: the skyline -26% -> -23%, the low flight -32% ->
  -31%): the near rooms carry the mean, and lighting them more is a look, so it is Mike's call.
- The skyline lights on an Eagles night and `?real=0`: on `?lights=eagles` every crown, LED line, the Liberty neon (on
  the crowns' new glass), City Hall's wash and the CTC's blade where main has them (`final/theme-sheet.jpg`); `?real=0` against main's `?real=0` at three poses, the only
  pixels differing by more than 12 levels (579 to 2,684 of 1,024,000) are the live flights' pins and the traffic
  (`final/real0-diff.jpg`).
- Renders: the session's `scratchpad/glass/fix2/` (`final/pairs` main, the first fix and now for the computer's views,
  `final/pairs-p` the phone's, `night-*`, `flk-*`, the calibration's shots in `cal-final/`, the probe panoramas in
  `probe/eq.png`, the proxy against the city in `probe/proxy-now3.png`).
- Tests: `tests/test_glass_towers.py` takes a `SecondReview` class (the crowns' system and slopes, the paint's register and
  the caps', Comcast's joints within a pixel of `frame.slim`, the fill and the sun inside, the homes' units and the box
  filter against brute force and its continuity) and its probe, dusk and sampler checks follow this round (the glass 7 of
  16 samplers on a computer with `uGlassIrr`, 4 on a phone); `tests/test_far_lit.py` the homes' far light;
  `tests/test_glass_calibration.py` the contrast bound and the crown. 868 tests, OK with the one expected failure;
  `tests/glass_systems_gpu.html` PASS in both depth modes (its sandbox now takes the SKYIRR block).
- The rules drafted for CLAUDE.md (a section 'The glass towers (Round 192)' before 'Where things are'):
  - A curtain-wall system rides the aSFT floor byte as `-(sys + 1)` (`glassFh`; style 30 is the generic curtain wall). Under
    `GLASS_ON` a glass wall never carries a skin. A glazed crown (style 29) wears its own tower's system in slim procedural
    frames with plant behind it; sloped glass takes no pane's tilt, tint or frame.
  - The frames are a texture array (a periodic tile per system, REPEAT, mips): never clamp the footprint or cut a wall to its
    mean. The procedural frame is box filtered per axis (`gBand`). A generated elevation's joints are thinned in the bake
    (`frame.slim`), never in the shader.
  - Glass colours are the scene's working values: never `convertSRGBToLinear`. Frame colours and spandrel backs are the colour a
    surface shows in the sun, drawn at the fabric's register (`GLASS_PAINT` = FACADE_GAIN); a cap at the roof's.
  - Every sky-derived term is the probe's decoded radiance, never the dome's raw uniforms (`cHorizon` and `cZenith` are display
    colours): the frames' and caps' fill is `SKYIRR` (the sky probe at roughness 1 along six axes, a 6 x 1 half-float target
    baked after each refreshEnv) at the fabric's 0.9; the proxy reads the sky probe for its fill and hazes with the city's own
    aerial perspective (`apU`, `scene.fog.color`), its colours in the scene's register.
  - The city probe (`CITYENV`) is the glass's own envMap, never `scene.environment`. It bakes on the frame refreshEnv asks, right
    after applyLighting, on every device, and holds no sun sprite. A phone's glass materials take a probe of its own size before
    their first compile (one program and its twin), and the phone's probe shares the water's 128 generator (`waterPmrem`).
  - A home is lit by its apartment (a unit of bays) and its far light is the units under the pixel box filtered (`gHomeBox`);
    offices are strips a floor high; never blocks of rooms, never point taps. The rooms come on with the lamps' photocell.
  - After any change to the glass's shaders, `glass_systems.json` or the proxy, run `python3 build.py && python3
    glass_calibrate.py`: `tests/test_glass_calibration.py` (each researched tower within delta E 15 of its swatch, Comcast's
    frames against its glass at 100 m under 2) fails otherwise, and so does deploy_philly3d.sh's test gate.
  - Escape hatches: `?glass=0` (the old paths exactly; `?real=0` too), `?glassart=0`, `?glassrooms=0`, `?cityenv=0|show`. Probe:
    `__dbg.glass()` (`u.uGlassK.z`: 3 the reflection alone, 4 the direct light alone, 5 each system a colour, 6 the glass as a
    mask; `u.uGlassL.z` the sun inside's share, `.w` the grime).

### Round 192, the third review's fixes (Oct 14)

- The sun inside (must-fix 1). The second fix's sun inside was a Lambert term on the pane (0.4 of the transmittance squared
  in the glass's hue), which no view changes: the CTC's south face at 100 m read 139,139,132 as drawn against 15,20,26 for
  its reflection alone, a beige panel with a grid, and Comcast's east face at 08:00 the tone of the masonry beside it. It is
  gone. The sunlit room is now drawn inside the room (`RE_Direct_Glass`): the floor by the window, lit by the sun through the
  vision glass at a carpet's or a slab's albedo (`uGlassL.z` 0.2) and seen back out through it only on the share of the
  pane where the eye's ray into the room lands on the patch the sun lights (the tangent of the ray's profile angle over the
  sun's: nothing from level or below, all of it from high over a face the sun shines steeply into), and the ceiling's
  bounce off that patch (a fifth of it), which every view sees. The daylit room (in the glass's hue alone: no beige from the
  rooms' cells) and that bounce together are held under a quarter of what the pane reflects at normal view (`gCapRef`, the
  sky's radiance along the normal from the fill's ambient cube); a neighbour's shadow takes both (the key light as it
  reaches the fragment).
- The calibration through the reflection (must-fixes 1 and 2). At the systems' own F0s (0.09 to 0.32) a glass reflected a
  tenth of the sky the probe holds (a mirror at the CTC's mid-level pose reads 160 to 199 over its upper face), and the
  swatches, which are photographs of glass mirroring a sky far brighter than the city under it, were out of reach without
  a diffuse floor. By day the reflectance is now the tower's photographed glass in linear light (its body, which is its
  swatch, over 0.66 to the 2.2) at `uGlassW.z` 2.0, its hue deepened to the 1.6 (`uGlassW.w`: a coated pane's colour is
  deepest at normal view, and Schlick's grazing white and the haze take it back), the system's F0 kept only as the share
  its low-iron corners, clear crown and lobby keep of the wall's; `coatSat` is 1 on every system (the body is the glass).
  The hue is taken to linear light before it tints anything (as a working value a blue #4E78A2 is 2.1 times as blue as
  red, as displayed 4.8). Four bodies now carry their calibration swatches (Cira #A7B5C0, Evo #4B5762, both Liberty Places
  #5D7F9E). After dark, as the rooms come on (`uGlassL.x`), the glass goes to its measured reflectance (as a near mirror of
  a lit city it stood up to two thirds over main's means among the towers at 21:30).
- The calibration (must-fix 2, should-fix 5). `glass_calibrate.py` now measures 28 towers (every researched glass tower
  with a reference colour at 100 m and up, the review's readings of the refs) at 21 poses: the review's eight, the CTC's
  south face at mid-level and its shaded north face from Market's north side, Comcast at 100 m off its south face, at 90 m
  across Market and on its shaded north-east face at 150 m, four at 60 m, five aimed at the lower towers, and One Liberty's
  crown. A tower is told from its neighbours by a code of its own (views 7 and 8: its body's bytes hashed, three bits a
  view, each channel full or dark, written after the fog so it survives the tone curve; the system colour, picked as the
  commonest in the box's top third, had measured One Liberty's glass for PNC and Two Penn) and its colour is its glass's
  alone (view 9, no frames). It is judged only where it stands in the open (400 pixels of its own glass, two fifths of its
  height, the eye no more than 20 m over its top: a wall reflects a ray on as far down as it came in, so from above a
  curtain wall mirrors the city under it and reads darker than its street photographs). The bounds: delta E 15 and b*
  within 6 (`HUE_B`) on each tower's median over its judged poses, every pose the review named for Comcast and the CTC
  within both individually. Results, median delta E and b* gap: Comcast 7.4 / -1.2 over 8 poses (100 m off its south face
  133,160,172, delta E 2.7; its shaded north-east face 117,144,159, 8.3; at 90 m 113,131,142, 12.0; the frames against
  the glass p90/p10 1.64), the CTC 7.2 / -2.1 over 12 (its south face at mid-level 151,172,178, 5.3; its shaded north face
  156,177,185, 4.1; the review had 30.4 and 19.4 there), One Liberty 7.0 / +0.9, Two Liberty 4.5 / +1.2, Cira 5.5 / +0.6,
  FMC 5.3 / +3.8, Evo 12.4 / -3.4, the Ritz 6.9 / +3.7 (its north face 98,131,154), 2116 Chestnut 7.4 / -5.9, IBX 14.4 /
  +0.1, Arthaus 4.2 / +2.7, PNC 8.5 / -2.8 (68,82,93 from Rittenhouse: dark glass, where it drew 129,149,163), 2000 Market
  5.2 / -3.7, 10 Rittenhouse 13.9 / +4.2, 1706 2.5 / -0.8, Ten Penn 10.7 / 0.0, 1650 Arch 9.1 / -3.0, 3025 JFK 4.3 / -2.1,
  The Alexander 14.1 / +1.5, CHOP 11.5 / +4.8, One Liberty's crown 6.5 / +1.1. Open, each held at its recorded gap by the
  test and said in `OPEN` for Mike: the W 10.9 / +10.5 (blue now, b* -13 to -19 against the review's -2 to -8, short of its
  photographed -27), Murano 13.8 / +13.4 (five of its seven poses see south faces mirroring the white sky round the sun at
  noon; its north faces keep its blue), The Laurel 9.5 / -6.9 (a warm glass mirroring a blue sky, one point past the
  bound), Eleven Penn 16.1 / +4.7 (its west face from 60 m mirrors the dark low city), the Honickman 16.9 / -0.3 (one pose,
  its south face toward the sun), Riverwalk 17.3 / +1.0 (seen among the towers it mirrors), 1818 Market 20.4 / -1.7 (its
  dark ribbons mirror the sky at the slant most poses see them) and Two Penn (no pose sees two fifths of it). From the
  low flight at 1.2 km the towers are blue, silver and grey again where the review measured one grey (`sheet-look3.jpg`).
- The glass at night (must-fix 3). The lit room's displayed light no longer falls with the transmittance itself, as a
  fabric's window never did: through a pane of 0.5 it is the fabric's lit window (`uGlassW.y` 0.6), through 0.22 about
  three quarters of it (`pow(gVLT / 0.5, 0.35)`: a lit office is far over the night's exposure behind any glass), and only
  what the pane reflects past normal view is taken from it. The offices' lit share is the fabric's (a floor on at 1.2 times
  the clock's share, its run 0.775 of it on average: it was 0.7 of the fabric's), and the far glow is about a near room's
  own light (`GLASS_FAR_LUM` 0.4, a phone's 0.5; at 0.08 the towers went dark as their rooms gave way to it). The brightest
  lit glass against the fabric's lit windows in the same frame (p99 of each, sRGB luminance): 191 against 190 at the
  review's Ritz dusk pose from 470 m (the review had 130,115,105 against 193,186,178 at the 95th), 183 against 203 for
  One Liberty and 1600 Market at 21:30. Night and dusk over the glass's own mask (sRGB luminance, main -> now, the crowns'
  lights off): the skyline from the south-west 36.9 -> 33.5 (-9%), from the Schuylkill 34.0 -> 38.0 (+12%), the low flight
  32.9 -> 31.0 (-6%), from the south 34.6 -> 33.6 (-3%), the street at Rittenhouse 29.0 -> 25.3 (-13%), the street at Comcast
  55.6 -> 46.6 (-16%), mid-Market among the towers 25.6 -> 39.8 (+55%: the offices lit at the clock's share in floor strips,
  where main lit about a sixth); dusk 47.9 -> 49.3 (+3%), 51.8 -> 60.8 (+17%), 44.6 -> 48.5 (+9%) (`night-final2.txt`). The second fix stood at
  -5% to -41% (night) and -8% to -21% (dusk). Five of the ten are within the review's tenth of main and five are not, two
  under and three over, so no one level moves them together: the street views are under because main's curtain wall lit
  about half its windows a cool white there and these are the clock's share, the homes' units warm and a third behind
  blinds (`pair3-street-*.jpg`), and the river's and mid-Market's are over because they see the offices' strips at the
  fabric's share where main lit a sixth. Left for Mike as a look, with the levels above. The skyline's lights are as they were (`chk-*` at 21:30 with the night's white).
- The curtain wall on evidence only (must-fix 4). An unresearched tower or mid-rise no longer goes onto the curtain wall by
  the cladding's lottery (197 towers and 234 mid-rises, the limestone former Main Post Office at 2970 Market among them):
  a wall is glass only when the research names it (`glass_systems.json`'s towers, the towers.json glass facades) or flags
  its part as glass (t 10, `pack_wide.py`'s, which keeps its cladding kind's system); every other wall keeps main's skin,
  main's mid-rise skin line restored exactly and `appendBuilding`'s cap-chunk argument gone with it. The post office from
  the river: main 115,113,107, the second fix 83,92,97, now 111,110,106. Draw calls (should-fix 6), the scene's own count:
  the low flight by day 634 (main) / 665 (the second fix) / 633 (now) on the computer and 601 / 622 / 601 on the phone path,
  every pose within a few calls of main's.
- The rain (should-fix 1): the key light's lobe on the glass widens as the deck closes (`uGlassW.x`, applyLighting's
  `glintK`: the roughness eases to 0.5), so a rain sky leaves no sparkle cluster on Comcast (`chk-*/rain-street-comcast`,
  both devices).
- Cira's cap at night (should-fix 2): measured, it is not the grime. The pale band over Cira's top from the review's pose is
  its top storeys' steep facets (the shader counts them as wall), and over the glass mask its light is its reflection alone
  (view 3 equals the full render there, 57 to 71): seen from above they mirror the lit city below at Cira's reference F0,
  not the sky, so a reflection darker than the sky behind it would be a mirror darker than what it mirrors. The sloped
  glass's doubled grime is halved (a true slope, the Liberty chevrons, takes a wall's). Declined beyond that.
- The proxy's walls (should-fix 3): piers or mullion pairs every 9 m along each wall and the window bays between them (box
  filtered: a far wall is its mean), each 40 m cell's wall a turn lighter or darker (its mean kept), its glass mirroring
  more sky the higher it stands; the near towers in Comcast's face read as walls with storeys, not cut-out shapes.
- Golden hour (should-fix 4): declined. The probe's western band is the city's own air (the proxy hazes with the scene's
  aerial perspective and reads 0.87 to 1.05 of the city); brightening it in the probe alone would make the west faces
  mirror a city brighter than the one they stand in. The glow the photographs show is the dome's and the air's, the sky
  and air workstream's.
- The time slider (should-fix 7): the city's bakes are at least 0.4 s apart (`CITYENV_GAP`): a request inside the gap waits
  for it, so a still clock's bake lands on the frame refreshEnv asks (its last was minutes ago), a dragged clock's at most
  every 0.4 s, and one more follows as it settles. Across the review's 70-frame scrub from noon to night and back (three scrubs a run, two runs each
  alternated with main on the phone path): the city baked 6 to 8 times a scrub (the second fix 44), the CPU summed 930 to
  1,064 ms against main's 822 to 967 (the second fix 1,070 to 1,246), its 90th percentile 16.8 to 18.3 ms against main's
  14.4 to 16.9 (19.1 to 21.8); on a computer 17 renders a scrub, both centres (56).
- The lights in the mirror (should-fix 8): `updateLightsTheme` asks for one bake as the theme settles after a retarget, so
  a theme landing the same day reaches the reflections with the crowns.
- The frames' fetch (should-fix 9): asked for as 'Cladding the towers' starts (`glassFramesFetch`), awaited in 'Glazing the
  towers', so it rides the cladding's round trips and artImage's retry overlaps the cladding.
- The memory figure (should-fix 10): the second review's section is corrected in place (+5 MB, not +3). This round, the same hook (the phone path, swiftshader, a forced GC), main -> now: 873 -> 875 MB of
  GPU at ready, 906 -> 911 after the first frames, 930 -> 935 after the look (+5 MB: the routing taken back neither costs
  nor saves), live heap 126 -> 126, 137 -> 138 and 138 -> 138 MB, the load's peak 281 -> 282; one glass program.
- Budgets. The scene pass (GPU, the minimum of 12 blocks, two runs alternated with main and the second fix, ms at
  1x): on the computer street-comcast-day 13.90 -> 14.23 (+2%), mid-market-day 20.51 -> 20.23, lowflight-day 23.85 ->
  24.22 (+2%), river-cira-day 16.40 -> 16.43, ctc-crown-day 18.37 -> 18.02, street-comcast-night 14.09 -> 14.36 (+2%; at 2x
  each way 46.33 -> 47.64, +3%), mid-market-night 22.93 -> 21.42, lowflight-night 24.08 -> 24.22; on the phone path
  (740 x 360 at 1.25) 3.36 -> 3.37, 7.40 -> 6.56, 9.70 -> 9.70, 4.75 -> 4.67, 6.67 -> 6.78, 3.56 -> 3.67 (+3%), 8.16 ->
  7.66, 9.86 -> 9.89: every pose within 3% of main or under it. The glass layer alone at 9x (the first report's measure, the
  minimum of two runs), main -> now: computer street-comcast-day 2.83 -> 5.31, street-comcast-night 3.87 -> 6.48,
  lowflight-day 4.02 -> 5.32, lowflight-night 5.03 -> 6.19, mid-market-day 12.18 -> 12.06, the Schuylkill skyline 1.85 ->
  2.94; phone path 1.20 -> 1.57, 1.76 -> 2.11, 1.17 -> 1.23, 1.61 -> 1.60, 4.62 -> 3.75, 0.62 -> 0.68. So the closest
  street views carry 0.25 to 0.3 ms more glass at 1x on a computer than main's (the second fix measured 0.15 to 0.3 the
  same way; this round's floor patch and cap are arithmetic, and the fill's ambient cube is now fetched once where the cap
  would have fetched it twice: the street at night 6.97 -> 6.48), the whole frame there 15.72 -> 16.10 (+2%) by day and
  15.75 -> 16.33 (+4%) at night, 4.58 -> 4.80 and 4.72 -> 4.78 on the phone path. Whole frames (one run each): the phone
  path's CPU medians 4.0 to 6.1 ms, main's 4.6 to 6.5, the second fix's 3.7 to 5.8 (within the runs' noise); a bake 2.2 to
  2.5 ms of CPU. Samplers unchanged (the glass 7 of 16 on a computer, 4 on a phone), one glass program on the phone path,
  no link failure and no console error in any run. Build: 'Glazing the towers' 2 -> 0 ms (its fetch rides the cladding's),
  'Cladding the towers' 1,359 -> 1,368 ms on the computer and 580 -> 590 on the phone path, ready 24.1 s (main), 25.5 (the
  second fix), 24.3 (now) on the computer and 19.1, 18.9, 19.0 on the phone path (single runs).
- Tests: `tests/test_glass_towers.py` takes a `ThirdReview` class (the sun inside from above and its cap, the daylit room's
  tint, the reflectance and hue, the night's level and share, the curtain wall on evidence, the glint under a deck, the
  probe's gap and the lights' bake, the frames' fetch, the proxy's rhythm, the calibration views and the chunk's colour
  bytes the codes assume); `tests/test_glass_calibration.py` is rewritten for the judged poses, the medians, the hue bound,
  the open towers and the named poses. The full suite: 883 tests, OK with the one expected failure; `docs_check.py` ok. `tests/glass_systems_gpu.html` PASS in both depth modes
  (its Fresnel check now at a low-e reflectance, `uGlassW.z` 0.3, and a check that the day reflectance follows the body).
- Renders: the session's `scratchpad/glass/fix3/` (`sheet-look1` and `sheet-look3` main, the second fix and now by day,
  `sheet-chk1` to `sheet-chk3` the rain, Comcast across the street, Cira, the post office, golden hour, Evo, Murano and
  Liberty from the street, Ritz at dusk, `sheet-ph1` and `sheet-ph2` the phone path, `sheet-night1` main against now at
  21:30, `cal-final2/` the calibration's shots, `night-final2/` the night means, `crop-*` the close-ups, `verify4-sheet.jpg`
  and `verify4-sheet2.jpg` main against the committed build: the CTC at mid-level, Comcast at 08:00, the core from 1.2 km,
  the post office from the river, the rain at Comcast's foot, the Liberty Places at 21:30 and the Ritz at dusk).
- The rules drafted for CLAUDE.md in the second review's section, as this round leaves them (still Mike's to put in):
  a wall goes onto the curtain wall only on evidence (the research's towers and glass facades, or a part flagged glass,
  t 10), never by the cladding's lottery; no light inside the glass that every view sees may be a Lambert term on the
  pane (the sun inside is the floor patch the eye's ray reaches from above, the daylit room and the ceiling's bounce
  under `gCapRef`); by day the reflectance is the tower's photographed glass in linear light (`uGlassW.z`, its hue to
  `uGlassW.w`), the references' F0 after dark; a body's hue goes to linear light before it tints a reflection; a lit
  room's displayed light falls with the transmittance only to the 0.35 and the offices' lit share is the fabric's; the
  city bakes never within `CITYENV_GAP` of each other and once more when the skyline lights settle; the glass's glint
  widens as the deck closes (`uGlassW.x` is glintK); `glass_calibrate.py --judge` when the poses or the routing change,
  each tower judged where it stands in the open, its median within delta E 15 and b* 6, `OPEN` for the ones left to
  Mike; the debug views 7 and 8 are each tower's code and 9 the glass alone as a mask.

## Round 194 — the Ryland in glass (Oct 14)

- Mike, after the glass towers: "Keep Penn as is, keep city hall as is. The Ryland needs the glass treatment. That entire
  building is glass." So Penn keeps Round 191's pose (the right arm out over the city, the charter in the left hand, as the
  photographs show it) and City Hall's plain night keeps Round 109's amber.
- The Ryland (1 Dock Street) is a core building built in 'Restoring the landmarks' as two offset blue bars with boxed
  mullions and spandrel bands on the core's own glass (rylandGlassMat), and Round 193's glass systems never reached it: the
  live build drew it as a pale flat slab. Under the systems (GLASS_ON) its two bars are laid in RYLAND_GLASS there, with no
  boxed mullions, and built in 'Raising the outer districts' on the glass chunks (`appendBuilding(getGlassChunk(...))`, the
  Liberty towers' route) in the residential window wall, system 8 (homes lit room by room, a 6 m lobby), in the blue the
  photographs read (#4F7BA1 in the towers' register). Its parapet screen and roof pergola stay on the core's pieces. Given in
  code, not in glass_systems.json, so the calibrated skyline is untouched (glass_calibrate.py's fingerprint). ?real=0 and
  ?glass=0 build the old bars. Rendered from Dock Street, a low flight, the river and at night: no link failures or console
  errors. `tests/test_ryland_glass.py`.

## Round 195, The Moshulu (Oct 14)

- Mike: "Remodel Liberty One, Liberty 2, The stadiums/arena, both Comcast towers, Battleship NJ, The Moshulu, and the
  bridges." This entry is the Moshulu's. Today's model drew her as a pale extruded slab 8.5 m high with a white band, four
  bare cylinders and twelve crossed boxes (about 400 triangles inside the museum ships' one merged draw), in a narrow slip
  with a 14 m strip of land on her river side, and nothing at night.
- The references (the session's `scratchpad/remodel/moshulu/refs/`, `SOURCES.txt`): Wikipedia's figures (121 m overall,
  109 m on deck, 14.3 m beam, 56 m from the main deck to the main truck), Commons' Penn's Landing photographs (2005 to May
  2024), the 2017 restaurant blog's deck and gangway pictures, and OSM. They settled one thing the brief had wrong: she is
  no longer white or black-and-white. From about 2016 she has been a deep navy hull with the red bottom showing at the
  waterline (Commons 20240529, the 2017 photographs); before that she was black with a white sheer band of painted ports over
  a white boot-top (Commons PA1, 2008 to 2013). She is drawn as she is now. Measured on the renders against the photographs:
  her hull at the marina pose reads #212843 to #1b2340 (Commons 20240529 overcast #1c1e32, the 2017 sun #242a47), the red
  band #782b28; the first cut's #273460 was too light and too royal and went down to the stored '#1f2748'.
- Her frame: s along the keel from the counter (0) to the stem head (Ld = 112.95 m, OSM way 170349587), t to starboard,
  y over the water; the bow is the outline's sharper end (north, a = (-0.006, -1)). The hull is lofted: 96 stations
  (cosine-spaced), each a section of 14 rows from the counter's or the stem's own profile (`yBot`, `sLo`/`sHi` inverted) or
  1.6 m under the water up to the sheer (7.8 m midships rising to 9.1 aft and 9.9 at the forecastle). Each row's waterplane
  is the deck plan drawn between the counter's knuckle and the raked stem, so the counter overhangs 7 m and the stem rakes
  2.6 m. The first cut ran the rows at fixed heights and the counter stepped where a row ran out of hull; the per-station
  bottoms made it smooth. Decks: the poop to 0.168 Ld and the forecastle from 0.875 Ld at the rail, the main deck 1.25 m
  under it, white breaks, the bulwarks' white insides and a white cap rail along the whole sheer. Masts at 0.13, 0.31,
  0.55 and 0.79 of the deck from the counter (the broadside photograph), trucks 38, 51.5, 54 and 53 m over the main deck;
  six yards a square mast at Hamilton's proportions, braced 20 degrees; the jigger's boom and two gaffs; the bowsprit
  steeved 22 degrees, 18.5 m. On deck: two black tented canopies with glass walls lit after dark, the Deck Bar's wooden
  pavilion on the poop with a lit soffit, eleven white market umbrellas and tables, a lifeboat a side in davits under a
  canvas cover, skylights, a windlass, cowl vents, fife rails.
- The paint, the plating and the teak are generated photographs (`fetch_moshulu_art.py`, gpt-image-2 high, two images;
  `bake_moshulu_art.py`): the hull's riveted strakes (cropped to three whole strakes from a seam, a tile 5.85 by 3.9 m) and
  the deck's planks (eighteen whole planks, 5.4 by 2.7 m); 91 and 163 KB, halves 21 and 34 KB. The hull's shader divides
  each picture's linear mean out (the paint keeps its calibrated colour), takes the plates' relief from the pictures' own
  luminance on a computer, and draws the boot-top (rising 0.45 m to the stem), the restaurant's 1.2 m windows along 27 to 84
  per cent of her length (lit after dark, 14 per cent dark, each its own warmth), three brass portholes a side under the
  poop and the two doors on her port side at OSM's gangways. The floodlights under each top wash her decks, bulwarks and
  cap after dark (`uMoMast`, pools of 9 m, 7 for the jigger). Her name is lettered by the page in gold on both bows and
  across the counter (the counter's board follows the curve, sampled densely where it turns: the first cut's chords cut
  inside her and split the name), and WELCOME ABOARD MOSHULU over the covered gangway.
- The rigging is one mesh of ribbons (1,511: shrouds, ratlines, topmast and topgallant shrouds, backstays, the stays,
  lifts, braces, footropes, the bowsprit's bobstays and shrouds, the jigger's lifts and vangs, pipe rails, davits, the
  gangway's and promenade's rails, mooring lines, the festoons' wires): a quad on each wire turned to the eye in the
  vertex shader, never under 0.6 px, its alpha the wire's own width over the ribbon's, so a far cable fades instead of
  breaking into dashes, lit by the day as a whole (`uMoDay`). Two traps found on the way: the ribbons wind away from the
  eye (the material is two-sided), and a masthead called without a side was NaN (one NaN made the whole mesh's bounding
  sphere NaN and none of it drew). After dark, 226 bulbs ride the festoons the photographs show, from the bowsprit's end
  over the four trucks to the taffrail, and four floodlight lamps, one Points draw on the photocell (`lampUniform`, as the
  bridge's nodes), postRaw and architectural bloom; the river's mirror draws them through its twins.
- The berth: her slip opens east through the hand-drawn bulkhead (`MOSHULU_SLIP`, the slip's fifth entry), the bulkhead's
  run inside it is cut (`shoreRun`, Liang-Barsky) and the slip's ends stop at the shore, and the riverfront promenade
  strip (`xShore - 11` to `xShore - 0.6`) is drawn in runs broken there: it lay over her water as a pale 10 m slab, which
  is what read as "a strip of land" in the first renders. OSM agrees: the water runs from the bulkhead at x 297 to the
  marina's floats at x 367 to 394. One more promenade draw call when both runs are in view. The covered gangway (black
  sides, glazed above, lit soffit) and the open aluminium one at OSM's two gangways, the promenade's rail along the slip,
  fender piles every 8.5 m, the head, stern and spring lines out to bollards.
- Levels: near under 420 m (260 on a phone, 12 per cent hysteresis): the hull program, the painted parts (vertex colours,
  their glass shining and lit after dark by an attribute), the names, the rigging. Far: one vertex-coloured mesh on the
  painted parts' program (the hull in three bands, the deck, the canopies, a window band lit after dark) and the spars as
  ribbons (58 triangles), which hold their 0.6 px from Camden where cylinders fell under a pixel. The rigging hides past
  600 m (450 on a phone), where a wire's coverage is under a twentieth.
- The budget, measured with a counting hook on her own draws over eight frames at each pose (the computer draws her mirror
  every fourth frame, so 1.25 draws an object a frame):
  computer near 5 draws and 18,165 triangles a frame (14,532 a pass: hull 6,384, painted 5,088, names 38, rigging 3,022),
  far 2.5 draws and 648 triangles, at night one more draw and 288 points; phone near 4 draws and 14,532 triangles, far 2
  and 518, night one more and 230 points. The city around her at those poses: 478 to 680 draws and 6.2 to 8.9 M triangles
  a frame on the computer, 321 to 544 and 3.2 to 6.5 M on the phone path. Shadow casters: hull and painted near, the far
  mesh far. Textures: on a computer the hull and deck at 1024 (11.2 MB with mips) and the names' 512 by 256 board (0.7 MB),
  11.9 MB; on a phone the halves (2.8 MB) and a 256 by 128 board, 3.0 MB, no relief; both loaded only within 800 m (450 on
  a phone), plain calibrated colours until then. Programs: four of hers (hull, painted, rigging, names) and the bulbs';
  246 programs on the computer and 142 on the phone path after the full set, no link failures and no console errors on
  either. Her build takes 18 to 23 ms. Every stream a Float32 stream (the painted colours go up packed by packResident),
  no 1- or 3-byte stream, no gl_FragDepth.
- ?real=0 keeps the old ship and the old berth (rendered against the committed build at the promenade and aerial poses:
  the same geometry, the differences cars, ripples and clouds); `?moshulu=0` draws the old ship and berth under the
  realistic look. The skyline lights unchanged: the bridge on an Eagles night against the committed build, 0.63 per cent
  of pixels over 24 levels, every one a flight pin.
- Renders, before and after at the same poses (`scratchpad/remodel/moshulu/before/`, `after/`, side by side in `pairs/`;
  poses `poses_pc.json` and `poses_phone.json` there): the promenade bow quarter, the marina, the river at 200 m, Camden at
  830 m, the aerial, over the stern, the stern from the promenade, the open deck at night, at 10:30 and 21:30 Oct 14, an
  Eagles night on the bridge and the ship; the phone at 740 by 360.
- Not done at the first pass: the hull took no light from the promenade's lamps; the canopies were plain black, without
  fabric; the running rigging is a selection (lifts, braces, footropes), not every buntline and clewline; the marina's
  floating piers (another landmark's ground) still stand at a fixed pier's height. `tests/test_remodel_moshulu.py` (12
  tests then) builds her under Node from her outline. The full suite: 920 tests, OK with the one expected failure.

### The review's fixes (the second pass, Oct 14)

- A shopfront was glued to her hull: a red-framed front with a navy awning, a 'Moshulu' board and a photographed dining
  room flat on her port side amidships (z 335 to 355), lit at night, in every promenade view. It was Round 189's panel for
  OSM's restaurant record (storefronts.b64 record 1038, x 310.6, z 345.2, facing west, 12 m wide), and `?real=0` showed
  the same panel on the old hull, so it predates the remodel. 'Dressing the storefronts' skips the ground the researched
  models and the rebuilds own, and her outline was in none of it: `moshuluBuild` now keeps her frame's box padded 2 m
  (`MOSHULU.own`) and the step adds it to that ground before either path tests a panel (outside the old step's bytes, which
  `test_realism_storefronts` holds). `__dbg.sf('list')` inside her slip: one panel before, none after; the new test decodes
  storefronts.b64 and puts every record in her slip inside her own ground.
- The restaurant's windows were a toy row: light frames, 1.2 by 0.8 m panes at an even 2.9 m pitch from 0.27 to 0.84 of
  her length. Remeasured on Commons PA1, a true broadside (read against her four masts, which the remodel had set from the
  same picture: jigger 0.13, mizzen 0.31, main 0.55, fore 0.79; a linear fit through the jigger and the fore lands the other
  two within 0.01): fifteen panes from 0.216 to 0.493 at a 2.2 m pitch under the after tented deck to the main mast, a pair
  at the main mast (0.5445 and 0.558), and eleven forward from 0.635 to 0.837 at 2.3 m, their centres climbing 4.3 to 5.6 m
  over the water; the panes 1.45 by 1.2 m (1.6 by 1.36 with the frame), the long run's centres 4.2 m up. The review's
  figures (0.40 to 0.72, 0.74, 0.80 to 0.92) were read off the May 2024 photograph, taken from nearer her counter: there the
  jigger stands taller than the fore and her forward half is foreshortened, so its fractions run about 0.2 forward of the
  broadside's; it shows the same openings (fifteen, a pair, eleven), so the runs are the broadside's. The frames are her
  navy greyed (#2b3040, under the plating's own detail), the glass dark and glossy, and a port pane whose centre stands
  within 1.75 m of a door gives way whole. After dark each lit pane shows its room: its ceiling's light at the head, the
  curtains drawn back to either side, warmer than before. The far level draws the same windows one by one (55 quads, 110
  triangles, lit by the same hash, `moWinLit`, in plain float steps so the GLSL agrees), so the switch at 470 m changes
  only the frames.
- The four floodlights were Points sprites: white moons at 480 m and half-black 'eyeballs' up close, cut by their own
  housings. Gone: each housing carries a lens plate on its underside facing down (in the painted parts, lit 3.0 after dark),
  seen only from below, as the lamp is.
- The festoons were neon tubes on a phone: bulbs every 0.75 m drawn 1.5 to 5.5 px, the pixel ratio frozen at the build.
  Each bulb now carries the step to the next along its swag (`aMoTan`), the vertex shader projects it and caps the point at
  0.55 of that step on the screen (a string seen along its length tightens too), floors it at 1.5 px and fades it by the
  share of the 1.5 px it would take; the gain is 0.95 of the bulb colour (it was 1.2, clamped); `moshuluStep` reads the
  pixel ratio and the drawing buffer every frame. Separate warm bulbs at 90 m on the phone and the computer, a thin amber
  line at 300 m, the swag still there from Camden at 830 m as a faint orange line (the fade is by width, not area, so a far
  string holds about half a bulb's light; by area it vanished from Camden).
- The tented decks' glass walls glowed as flat cream slabs. The painted parts' attribute is now four floats (lit, kind, and
  the part's own u and v in metres, from a frame each part may carry: `pp(g, c, e, k, fr)`); a glass wall on a room draws
  black mullions every 1.6 m, a transom at 1.95 m and a sill, the room brighter under its ceiling, the tables and diners
  breaking its lower third, at 0.55 of the old gain. The canopies are fabric (ribs of their frame every 1.5 m, the ridge
  capped, each panel sagging a little, a weave); the umbrellas a twelve-panel canvas drooping to its hem (a lathe) and
  matte; the lifeboats under a dark hood (Commons 20240529); the gangway's carpet takes its ceiling's light on its own colour.
- The covered gangway (blog b2): black side panels with a rail, open above between black frames every 1.9 m with a cross
  beam under the roof at each, a dark carpet lit from the ceiling, the fascia's box behind the WELCOME ABOARD MOSHULU board,
  now lettered in gold on black, and a red barrel awning over the door in her side, standing out over the gangway's roof
  (12 panels and a closed end). The door's frame takes the windows' dark frame.
- The bow (blog b1): gold trailboard scrollwork either side of the stem head, laid along her sheer on the names canvas (now
  four rows of a 1024 square: the gold name, the white name, the scroll, the board; 512 on a computer, 1.4 MB with mips, a
  phone's 256); a hawse pipe each bow (a rim and a dark mouth) with its anchor chain hanging from it up over the rail, each
  link pushed clear of her flare; and the big white MOSHULU high on her port side aft of the covered gangway (b2).
- The jigger's gaffs, measured on PA1's after half: the boom 15.5 m, level, 2.2 m over the poop; the lower gaff's heel 0.195
  of the way from the poop to the truck, 15.2 m at 23 degrees; the upper's at 0.42, 12.3 m at 41 degrees (they were at 0.42
  and 0.64 of the mast and the upper stood out of the topmast).
- The far spars were brighter and thicker than the near masts at the switch: unlit ribbons at the full buff and the tubes'
  largest radius. Now 0.52 of the colour and 0.75 of the radius (`MO_SPAR_FAR`). Measured at 465 and 475 m by day (masts
  against the sky): the summed excess over the sky was 13,345 far against 9,029 near (1.48 times); now 10,397 against 9,269.
- Her hull was pitch black beside the lit promenade. The lamp maps read nothing at her berth (`__dbg.lampAt` at eight points
  along her port side and the walk: zero; no pole stands on the promenade there), so sampling them would have changed
  nothing; the hull's own shader washes her port side warm after dark on the photocell, fading up her side from 1 to 8 m,
  a fifth of it on her river side, and not her glass.
- Budget, measured as before (a counting hook on her own draws, eight frames a pose): computer near 5 draws and 20,588
  triangles a frame (16,470 a pass: hull 6,384, painted 6,900, names 124, rigging 3,062), far 2.5 draws and 725 (the far
  mesh 522, the spars 58), at night one more draw and 283 points (226 bulbs; the four lamps' points are gone); phone near
  5.5 draws and 23,174 triangles at the promenade pose (its shadow pass drew the hull, the paint and the names 1.5 times a
  frame there), far 2 draws and 580, night one more and 226 points. The city around her: 473 to 750 draws and 6.6 to 10.2 M
  triangles a frame on the computer, 470 to 627 and 5.8 to 7.0 M on the phone path. Textures: the computer 12.6 MB (hull and
  deck 11.2, the names' 512 square 1.4), the phone 3.2 MB. Programs: 240 on the computer and 144 on the phone path after
  the full set (the same as the first pass), no link failures, no console errors on either, `PERF.failed` empty.
- Renders (the session's `scratchpad/remodel/moshulu/fix/`): before (the first pass's build, 7722666) and after at the same
  25 computer poses and 10 phone poses (`poses_final_pc.json`, `poses_final_phone.json`), side by side in `pairs/`, by day
  from 10:30 to 15:30, dusk 18:40, night 21:30, a red night and an Eagles night; the level switch at 465 and 475 m by day and at
  night (`f_sw_*`); measured crops of PA1 and the 2024 photograph in `refs/`.
- Still not done: the running rigging is a selection; the marina's floating piers stand at a fixed pier's height (another
  landmark's ground). The tests (`tests/test_remodel_moshulu.py`, 17 now) add the storefront check, the window runs and the
  far level's windows, the lenses and the bulbs' pitch, the tents' room glass and fabric, and the jigger's spars. The full
  suite: 925 tests, OK with the one expected failure; `docs_check.py` ok.
