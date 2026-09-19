# Philly3D model and lighting refresh

September 18, 2026. Implemented in the local source and rebuilt single-file page. This is an architectural approximation for a city-scale model, not a surveyed digital twin.

## South Philadelphia

**Citizens Bank Park** now has an open horseshoe grandstand, three stepped seating levels with blue seats, section aisles, suite glazing, brick concourse bays, patina canopies, exposed roof supports, and six lattice light standards. The playing surface has mowing stripes, foul lines, a warning track, bases, the mound, and an angular outfield wall. The left-field video board uses the current 152 by 86 foot proportions and faces home plate, with its steel frame rotated to match; right-center has a modeled neon Liberty Bell. Expanded blue outfield terraces follow the left- and right-field fence, with section aisles, rear promenades and railings, and a gap for the center-field batter's eye. Separate brick pavilions sit behind the stands.

**Lincoln Financial Field** now has terraced sideline and end-zone stands, openings for both video boards, club glazing, tapered sideline canopies with ribs and tiebacks, roof solar modules, and goalposts. Both video boards and their housings align with the end-zone stands and face the field. The field is 109.728 by 48.768 metres, oriented north eight degrees west using the project's field research. It includes ten-yard end zones, yard lines, numbers, hash marks, and simplified Eagles lettering. Building the decks segment by segment prevents disconnected end zones from being joined across the pitch.

**Xfinity Mobile Arena** has a rounded roof eyebrow, roof seams and service equipment, three entry canopies with glazing, three exterior screens facing northeast, northwest, and south, and four groups of corner light strips. The light strips sit outside the curved facade and follow the existing skyline color calendar. The old rectangular lighting box has been removed.

## Skyline and lighting

- The Comcast Technology Center's two broad office wings were imported at 142 metres, leaving an excessively narrow tower. They now use an estimated 213.5 metre terrace datum beneath the existing hotel volume. The 342 metre architectural top and imported horizontal plans are retained. Raised diagonal chevrons, vertical edges, and three-story belts distinguish its facade. The roof occlusion grid follows the raised wings.
- One and Two Liberty Place now use their silver-banded glass shader on their shafts as well as their crowns. Deeper blue glass and thinner crown trim give the stepped tops a clearer profile.
- The Comcast towers have more restrained blue-gray materials. Curtain-wall reflections are less overpowering, panel tints vary subtly, and occupied offices have coherent groups with a mix of warm and cool light. Generic facade windows also have a lower night intensity and occasional cooler lamps.
- Bloom has a soft threshold so bright details ease into a glow. Stadium lighting preserves the colors of the playing surfaces and seats instead of placing additive light sheets over the bowls. Field lighting remains neutral under a colored skyline theme.
- Stadium floodlight sprites are smaller. Parking paint is quieter by day and dims after dark, fixing the luminous white parking lots that competed with the venues.
- Explore has four additional viewpoints: Citizens Bank Park, Lincoln Financial Field, Xfinity Mobile Arena, and Above Center City.

The detailed venue/steel surfaces share one merged mesh; fields and displays use small procedural canvas textures. No downloaded imagery, new dependencies, framework, or external asset requests were added. Screens show fixed venue identities, not invented live scores.

## References and modeling limits

The existing `south_geometry_research.json`, `towers.json`, packed OSM plans, and Philadelphia height research remain the starting point. This pass also consulted:

- [EwingCole's Citizens Bank Park project](https://www.ewingcole.com/project/citizens-bank-park/) for the open seating bowl, cantilevered levels, and outfield character.
- [The Phillies' ballpark guide](https://www.mlb.com/phillies/ballpark/information/guide) for current PhanaVision dimensions.
- [Lincoln Financial Field's stadium facts](https://www.lincolnfinancialfield.com/stadium-facts/) for its structural arrangement and video-board proportions, alongside the field bearing recorded in the local research.
- [The arena's exterior renovation announcement](https://www.xfinitymobilearena.com/news/detail/new-wells-fargo-center-building-renderings) for the three displays, entry canopies, roof eyebrow lighting, and corner struts.
- [Enclos's Comcast Technology Center facade study and photographs](https://enclos.com/project/comcast-technology-center-1800-arch-st/) for chevron panels, curtain-wall rhythm, and the stepped tower profile.
- [Comcast's campus information](https://comcastcentercampus.com/campus/) and [Tillotson's lighting project](https://www.tillotsondesign.com/corporate/comcast-innovation-and-technology-center) for the tower's program, hotel, and three-story sky gardens.
- [RAMSA's Comcast Center project](https://www.ramsa.com/expertise/project/comcast-center) for the silvery glass treatment.

Seating sections, canopies, individual facade bays, signs, and logos are simplified. The CTC terrace datum is a visual estimate, not a newly surveyed elevation. Citizens Bank Park's real field is below street level; this pass keeps it above the existing terrain surface rather than cutting a new excavation into the city terrain. Floodlighting is an economical material response and bloom, not a simulation of every physical lamp.

## Validation

`tests/test_venues.py` runs the actual venue builders with the vendored Three.js under Node. It checks finite geometry, numerous distinct terrace heights, a bounded triangle count, correct football-field dimensions and bearing, clear space above five points on the playing field, valid ballpark texture coordinates, no overlapping baseball-field triangles, and flush, inward-facing football scoreboards and housings. The two venue detail batches total roughly 56,000 triangles, a small addition relative to the full city.

The browser review compares the original and revised skyline at the same pose, date, and time. Venue checks cover daylight and night, field markings, open bowls, visible displays, neutral field lighting under a green skyline theme, the arena's roof and corner strips, and the new Explore destinations. Console and shader errors are checked separately. Desktop rendering has been inspected; viewport checks do not substitute for a physical-device GPU benchmark.

Final checks: 107 tests, with one pre-existing expected failure; JavaScript syntax, build guards, documentation coverage, and whitespace checks pass. Built HTML: 27.45 MB. The final browser console reported no errors. The responsive override did not change this pane's reported viewport and was reset, so this pass does not claim new mobile GPU validation.

The blue-seat follow-up was rebuilt and checked with the four venue geometry tests, JavaScript syntax validation, an elevated ballpark view, and views from behind home plate in daylight and at night. The updated preview reports no browser errors.

The scoreboard/flicker follow-up uses the user's stadium photographs as visual references. The baseball surface now triangulates its concave outline instead of using an overlapping centroid fan, also correcting its face winding. The Linc's displays derive their rotation from the field axis. Two new regression tests failed on the previous geometry and pass with these fixes; all six venue tests and the rebuilt page pass.


## Transport and terrain follow-up

Streets, sidewalks, paths and road bends now follow the actual terrain across their
full widths, including slopes, partial terrain holes and boundaries between map
tiers. The core terrain boundary no longer overlaps its neighbour. Roads and grass
surfaces that extend outside the wide tier wait for the surrounding ground to be
built; this fixes the park surfaces that were hiding long stretches of road in
Fairmount Park. Rail beds check their full footprints, and moving trains share the
corrected grade. Elevated roads check between their existing sample points while
station portals and intentional tunnels retain their placement.

Six regression tests cover generated geometry on slopes, crests, holes and stepped
seams. The full suite runs 115 tests with one existing expected failure. A separate
instrumented city build found no buried samples among 16.93 million checks on
surface transport triangles against the actual ground meshes. This sampled audit
excludes intentionally covered station tracks and tunnels; visual checks also
cover the East Park grass overlays, the 30th Street rail approaches and the hillier
Roxborough Park routes. The page is rebuilt locally, without new dependencies.


The exact-view follow-up at `#p=-3744.1,166.8,-2508.3,-1.706,-0.552` exposed bend
geometry problems that the clearance audit alone could not detect. Roads and rails
now share their edges through bends, replacing independent rectangles and overlapping
rail fill fans. Rail visibility also includes the full surface segment up to a tunnel
entrance. Three added regressions cover overlap, matching edge coordinates and portal
endpoints. Before/after inspection at that viewpoint confirms continuous highway
edges; 118 tests run with one existing expected failure, and the repeated sampled
terrain audit remains clear. This is still a local preview, not a production deploy.

## Street-name clearance follow-up

Street names now follow the actual drawn road tops across their full length and
width, including sloping streets and custom bridge decks. A small shared grid
preserves the full text atlas, and triangle-intersection checks keep interior
crests from cutting through letters. The old downward slope clamp is removed.
Depth testing still lets buildings, cars and crossing structures occlude names.

All 3,774 baked placements were audited. The previous geometry intersected road or
ground at 336 labels; the updated geometry has no such intersections across
243,752 text triangles and 6,824,948 sample checks (minimum clearance 18 cm).
Thirteen placements without a corresponding drawn road surface use the terrain
fallback. The audit measures road/terrain clearance, not visibility through other
scene objects. The exact reported MLK Drive / Schuylkill Expressway view now shows
both names completely. Five new regression tests pass; the full suite has 123 tests
with one existing expected failure. Changes are in the local rebuilt preview.

## Pin visibility follow-up

Every pin family shares scene-depth rendering: buildings block badges, search pins,
and event connectors/anchors. This supersedes the earlier overlay treatment at the
user's request in Round 105. Pin click priority now excludes obstructed hits while
preserving transparent-corner rejection and bike-share atlas coordinates.

Six helper regressions cover the shared policy and picking. `tests/pins_gpu.html`
checks full and partial building occlusion, visible foreground pins, and recovery
when an obstruction moves away, with standard/logarithmic depth and bloom variants.

## Cloud elevation and smoothing follow-up

Clouds now have varied bases and depths in separate low and high banks, rather
than sharing the plane just above the flight ceiling. Lower banks can appear
beside or below the flying camera. World-space density preserves their placement
while moving around, and actual cloud depth keeps buildings correctly occluded.

Stable sampling, distance-filtered detail, rounded volume and softer lighting
reduce the old stippled appearance. Weather and wind still control coverage and
drift. A lighter sample budget is retained for touch devices. Clear and overcast
city views were checked; the GPU regression page passes all four desktop/touch
budget and depth-mode combinations. These are browser shader checks, not a test
on physical mobile hardware. The 129-test suite also passes with its existing
expected failure. Changes are in the local rebuilt preview.

## Building and skyline refresh

The building materials now share wall-local dimensions throughout the core, outer
city and surrounding towns. Windows fit each wall, top-floor openings stop below
its roof, and edge/cornice shading follows the building instead of a world grid.
The shared material pass softens frames, preserves sash and mullion detail, varies
blinds and glazing, and adds restrained coping, frieze and base shading. Taller
brick apartments have their own facade pattern and retain their mapped masonry
palette; industrial lofts retain industrial windows at greater heights.

The Center City pass adds:

- **One and Two Liberty Place:** recessed shaft corners, brighter central glass
  bays, finer chevron/eave/ridge trim, and enclosed mechanical crowns with subdued
  interiors so their nighttime outlines remain clear.
- **Comcast Center and Comcast Technology Center:** different curtain-wall rhythms,
  clearer corners, south-facing sky-atrium accents on Comcast Center, and mechanical
  bands/hotel differentiation on CTC. The prior researched massing remains intact.
- **BNY Mellon:** a solid glazed pyramid beneath the exposed ribs, additional
  horizontal framing, and a shorter apex. The existing themed crown wash remains.
- **Three Logan and Commerce Square:** more legible stone piers, coping and bands;
  Three Logan uses a quieter rose-gray granite palette, also saved in its generator.
- **FMC and Cira:** distinct glass treatments. Cira's former rectangular rooftop
  setback is replaced by a continuous, inward-leaning faceted body and sloping
  roofline, confined to its mapped footprint and 133 m model height.

The architectural references include [RAMSA's Comcast Center project](https://www.ramsa.com/expertise/project/comcast-center),
[Enclos's CTC facade study](https://enclos.com/project/comcast-technology-center-1800-arch-st/),
[One Liberty Place's official brochure](https://onelibertyplace.com/pdf/availabilities/2021-ONE-Liberty-Place-Brochure-r1.pdf),
and [Enclos's Cira Centre study and photographs](https://enclos.com/project/cira-centre/).
Facade proportions, atrium placement and the Cira taper are visual approximations,
not a reconstruction from construction drawings. Glazing combines the existing
sky environment with a restrained procedural reflection pattern; it does not
reflect the actual surrounding buildings.

Validation covers the full facade vocabulary (30 base styles) plus live views of
the downtown towers, Society Hill, South Philadelphia, University City, Old
Kensington and the outer district tier. The packed-geometry audit found no missing
wall metrics across 8,530,716 nonblank wall vertices. `tests/buildings_gpu.html`
passes all four desktop/touch detail-budget and standard/logarithmic-depth
combinations, including packed/core attribute agreement and night lighting.
`tests/test_architecture.py` adds seven geometry/material-selection regressions.
The full Python suite passes 136 tests with one pre-existing expected failure.
These are local browser checks, not a physical-phone benchmark or a manual review
of every individual building.

Details remain in existing batches, with no new downloaded assets or dependencies.
The compact wall measurements add four GPU bytes per packed facade vertex (about
59 MiB across this build); staging arrays are released after upload. The local
single-file preview is rebuilt. Publishing is unchanged.


## Road and landscape clearance follow-up

The Vine Street clipping came from raised grass strips covering intact pavement.
Those strips now follow the actual terrain; precise road-footprint subtraction
keeps them off road surfaces. The same protection covers rail portal grass,
incidental core park/path overlaps and the waterfront promenade. Intentional
park decks above I-95 remain intact.

A full-city sweep examined 2.28 million road/path triangles against the secondary
landscape geometry. The repaired road-cut and rail-cut grass have zero remaining
pavement intersections, and the promenade is clear too. The exact reported view
and additional expressway, riverfront and station views were inspected. Five new
geometry regressions protect narrow crossings, junctions, ramps, cross slopes,
bridge ground and intentional tunnel caps. Rebuilt in the local preview.


## Landmark reference-photo follow-up

Comcast Center's new upper assembly has a deep physical recess with side piers,
back wall and lintel. Its nighttime crown and the Technology Center's lantern
support broad horizontal bands or a solid color. The Technology Center's office
bracing is slimmer and no longer repeats oversized V shapes on every return.

City Hall's floodlights now color the actual facade shading, emphasizing the
tower and pavilions while retaining windows, cornice relief and dark slate roofs.
Eleven mapped Boathouse Row clubhouses have varied rooflines, arched boat doors,
half-timber detailing, balconies, landings and theme-responsive outline lights.
These are photo-informed architectural approximations, not measured replicas.

Sun & Sky exposes the lighting themes, custom 1–4 colors and crown patterns.
Manual palettes are carried in share links. Day/night browser checks cover both
Comcast towers, City Hall and Boathouse Row; the four added geometry/palette
regressions bring the suite to 145 tests with one existing expected failure.
