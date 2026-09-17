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
