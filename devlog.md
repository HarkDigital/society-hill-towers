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

### Facade-accuracy plan status

**The LiDAR true-massing pass and Tier 1 of the facade-accuracy plan are done.**
Tier 2 (parametric storefront/signage kit from OSM shop names) and Tier 3 (photo-built
fronts like Rotten Ralph's/Glory) are the remaining rungs; `lidar-massing-plan.md`'s
option 2 (OPA join) is now executed as part of Tier 1.

Data © OpenStreetMap contributors (ODbL) — the credit link in the About panel must stay.
