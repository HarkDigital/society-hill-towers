# Philly3D: the working plan

This is the plan the project is working from now, and where it stands. Any session (any model) picking the work up
should read this file first, then `CLAUDE.md` for the rules and `devlog.md` for the round it is about to touch. Keep
this file current: when a round ships, move its line from "in flight" to "shipped" and correct anything it changed.

Last updated: Nov 12, 2026, after Round 241 (no street name in a junction).

## The ask

Mike, Nov 9, 2026: "I want you to come up with ways to improve the performance and loading of this app. I also want you
to delve into how to make it more realistic looking. I am open to all ideas." He approved a six-stage roadmap on Nov 10.

His decisions on Nov 9, which shape every stage:
1. Priority: the public's first visit, ahead of his own Mac and iPhone.
2. Realism: all four areas are wanted (light and shadow, the aerial view, street life, landmarks and night).
3. Four standing rules may be reopened where the numbers justify it, each still his own decision before it ships: files
   beside the page, a patch to three.js r149, entering before everything is built, and slow public PCs shedding distant
   detail (never resolution, never on his Mac or in Sharper).
4. People on the sidewalks: yes, walking. On Nov 10 he moved them to the front: "People next".

## Where the research is

The plan came from eleven research lenses (79 proposals, each read against the code by two adversarial verifiers), two
ranked syntheses and a critique. That record is NOT in git (the folder is ignored); it is in the checkout on disk:

`.audit/2026-11-10-performance-and-realism/`
- `PLAN.md`: the approved plan as written on Nov 10 (the measured table, every stage's items, what still needs Mike).
- `lens-*.md`: every proposal with both verdicts. **Read the lens file before building its item: the verifiers'
  amendments are the spec.** Its app.js line numbers are stale by a few thousand lines now; grep for names.
- `synthesis-performance.md`, `synthesis-realism.md`, `critique.md`.

## What the real devices said (measured from the site's own beacons, Oct 26 to Nov 9)

- Public Windows PCs reach Ready in 66 to 103 s. 12 to 57 s of that is compiling shaders one program at a time; 40 to
  50 s is JavaScript; 9 to 21 s is unexplained between steps.
- Apple devices with an empty shader cache: 45 to 59 s, 32 to 34 s of it compiling 138 programs. Warm, the same work
  is about 1 s.
- Mike's iPhone app, warm: 11.2 to 12.6 s. It lives on tier 1 (822 to 858 MB of GPU memory after its first frames);
  tier 0 died about 6 s after Enter from 871 MB.
- Mike's Mac: 26.9 s in October; no pass timings from it yet (he has been asked for a three-minute flight).
- Headline: on a first visit, and whenever a device's shader cache is empty, compiling shaders is the largest single
  cost on every platform.

## The rules the plan runs by

- **One shader train.** A release that changes shared shader text makes every device compile those programs again
  once (30 to 57 s on a cold public PC). Stage 1 changes no shader text. Every shader edit after it ships in ONE batched
  deploy (Stage 2), with new looks behind uniforms or flags. A NEW program under a flag (the people's two) is fine.
- **Two ledgers.** Every item carries its measured frame milliseconds (Mac and iPhone) and phone megabytes before it is
  on by default. The ASTC saving is spent once, on memory or on sharpness, as Mike picks.
- **One vertex layout.** The roofs' new bits (Stage 2) and the walls' records (Stage 4) are laid out together.
- **Every look change** ships behind a flag and goes to Mike as a private side by side (the entry orbit included, see
  the capture skill's `references/poses.md`). Nothing is on by default until he says.
- **How a round is built** (this worked for Rounds 225 to 231): a git worktree outside Dropbox per item, an implementer,
  an adversarial reviewer, a fix, a second reviewer; then the lead merges, builds, runs the whole suite, compares
  captures against main himself (`render.mjs --png` and a pixel compare, traffic off; twice on Nov 10 this caught what
  both reviewers missed: a tree renumbering and the dark glass), writes the devlog, commits the built
  page, pushes with `git push gh-ssh main` and runs `3d-model/deploy_philly3d.sh` (which also ships a TestFlight
  build). Commit from worktrees with `git -c gc.auto=0 -c maintenance.auto=false` (two automatic repacks raced in the
  Dropbox-hosted object store on Nov 10). Server config edits need Mike's explicit go, each time.

## Status at a glance

| Stage | What | Status |
|---|---|---|
| 1 | Free seconds, missing numbers, no dead button (JavaScript and data only) | Batches one and two shipped (Rounds 225, 229, and Camden's heights as 231). Remainder below. |
| 2 | The shader train: program diet, roofs by photograph, lit floors, floodlights, snow that stays, the light | Not started. Needs the two side-by-side pages first. |
| 3 | Link ahead (the cold load's main fix) | Not started. Built only for an engine where Round 229's probe shows batched linking under half of serial. |
| 4 | The phone holds the whole city (walls as instance records, ASTC, building shadows) | Not started. |
| 5 | Repeat launches, and Ready on the near city | Not started. |
| 6 | The Mac's frame | Waits on Mike's flight on the Mac, then once with `?dpr=1`. |
| Picks | People walking, canopy, junctions, street pace, the Art Museum, twenty towers, tree heights, the Schuylkill's pool | People: first look shipped behind a flag (Round 227). The rest not started. |

## What has shipped under this plan

- **Round 225** (Stage 1, batch one): the river's edge search gated (`schEdges`), the roof-kit masks by scanline, the
  traffic's once-a-second stall gone, the Art Museum and Liberty Place solid to the flight, the deploy sends art once,
  the app carries only the art a phone can ask for. Headless on an M2 Max: Ready 35 s to 26 s. Coda: the server caches
  art for a year and gives the gzip page to visitors behind a proxy.
- **Round 226**: the pins draw from half a mile again (Mike's call; not part of the plan).
- **Round 227** (the people, a first look): three test figures walking, OFF by default. `?people=1`. Round 237 gave
  them four poses a step; Round 242 thirty figures, eight pictures a step, dressed by the temperature. See "The people"
  below.
- **Round 228**: the Vine Street Expressway's cut carried to the tunnel under 20th Street and the Parkway, a portal at
  each mouth (Mike's bug report; not part of the plan).
- **Round 230**: the last see-through slivers beside the expressway's west approach cuts closed (a floor and risers
  under the lawn laid over opened ground, `lawnUnder`; a pier at each end of each headwall).

- **Round 229** (Stage 1, batch two, without Camden): no program compiles twice (`wxHookAll` before the first compile);
  Enter lights only after the first drawn frame; `?veilcity=1` (off) lets a computer's veil show the city rising;
  measurement round two in the beacons; `?cold=<n>` and the link probe. The merge found and fixed a Round 192 bug the
  batch exposed (the city probe's second cube wiped a pending request: dark glass towers in any capture after dark).

- **Round 231** (Stage 1, the batch's fourth package): Camden at its measured heights, shipped at Mike's word after
  the before and after.

- **Round 232** (Mike's ask, outside the stages): the green berm on the Society Hill Towers' north lawn by Dock Street is
  no longer drawn; its spot still keeps the trees off, so no tree moved.
- **Round 233** (Mike's ask, outside the stages: "parked cars clogging up many streets ... cars need to be scaled down
  in size a bit"): every car drawn at 88% of its real size (`CAR_K`, `?carscale`), and the parking rules redone (PARK2,
  `?parked=old` keeps Round 188's): each car its own flank off the kerb, a moving van always 0.3 m clear of a parked one,
  a fill per block side, a 6.5 m pitch. Mike picked the fuller column of his side-by-side page
  (https://claude.ai/artifact/Ubu7Mfhyobf1cTi4McvbBy): every narrow block on both kerbs and the fills 1.25 times the
  plan's means, about 82% of the cars there were. JavaScript only; no shader text changed.
- **Round 236** (Mike's ask, outside the stages: "Parked cars in the middle of city streets is not [natural]"): the
  two one-way halves of a divided street no longer park their inner kerbs (Columbus Boulevard, Girard Avenue, South
  Broad Street, Spring Garden Street): 272 km of the city's 5,309 km of parking kerb, `?parkmid=1` the old rows.
  JavaScript only; no shader text changed. Traffic queueing at junctions stays as it is (Mike: natural).
- **Round 238** (Mike: "Draw the median on South Broad so the cars come back"): from Washington to Oregon the two
  halves of South Broad are painted from a flush median between two double yellows, laid as its own strip broken at
  all 21 crossing streets, with a row of about 300 slots parked down it at the kerbs' fills. `?broadmed=0` draws the
  stretch as Round 236 did. JavaScript only; no shader text, no new mesh.
- **Round 239** (Mike: "The traffic lights look really bad. Can we remodel those to be the ones that hang over the
  street"): every signalised junction is one record (OSM's approach nodes merged), its streets strips at their drawn
  widths (a divided street one wide street), a black mast pole on each approach's far right corner with its arm and a
  yellow head over each moving lane, one on the pole, a post on the other corners and pedestrian heads on all. No pole on
  a drawn street or median anywhere in the city (surveyed: `__dbg.signals('survey')`). `?signals=old` keeps the old
  poles. Phone: +3 draw calls, +0.2k to 2.4k triangles, +0.1 MB GPU, frame time in the noise. JavaScript only; no
  shader text, no new program.
- **Round 240** (Mike: "I am still seeing lots of parked cars blocking intersections"): a parked row was kept off a
  junction only at its traffic run's listed ends, so it ran through every crossing a run is not cut at (37,190 slots
  in a junction box or on a zebra citywide, 86% in a run's middle). Each run now finds the drawn streets that cross it
  and parks 6 m clear of their kerb lines, with a per-car backstop for the streets that never meet its centre line:
  9 left citywide, 7% of the slots gone, about 0.8 ms more a fresh lay on a computer. `?parkjx=0` the old rows.
  JavaScript only.
- **Round 241** (Mike: "the street names are now intersecting in the intersection. i dont want that to happen in any
  intersection"): 1,832 of 3,774 baked names crossed a junction box or a zebra. The bake now slides each along its
  street to a block it fits in, else letters it at 0.75, 0.6 or 0.45 of its height: none in a junction, 3,655 names,
  fifteen tiny streets without one. Data and twelve text heights in the page; the atlas unchanged.
- **Round 243** (Mike: "I see this texture a lot on the ground floor of large buildings. It is not good"): the street
  floors' window masks were salt and pepper on nine of sixteen pictures, so lobby glass drew as patches of reflection
  and matte black (14,293 street floors laid, 1,573 under the big buildings). Behind `?streetfloor=`, off by default:
  `clean` (the masks as whole panes, data only) and `lit` (and four big-building lobbies made again with clear glass onto
  a lit lobby, a shader variant only under the flag). Side by side sent to Mike.

## In flight (finish these first)

1. **The first side-by-side page has his picks** (https://claude.ai/artifact/RKJaq5QkvXZt11PkuWnMdX, private): the clear
   sky's fill at 1.2 (said in chat) and the city behind the loading screen (saved on the page) shipped as Round 234. He
   made no pick on the roofs' sheen or the far-map switch, so both stay as they were. Still to do from it: the light's
   other half (the straighter day toe, shader text, Stage 2), shown on a test build first; the yellow-green haze toward a
   low sun at 16:10, seen in every variant, not yet looked into. (The glass calibration it moved was re-measured as
   Round 235.)
2. **The people, after Mike's second look.** He found the walk disjointed (Nov 11; Round 237, four poses a step) and then
   asked for smoother still, many more people and clothes for the season (Nov 12): Round 242 made thirty figures, eight
   pictures a step, in three wardrobes chosen by the temperature. He is to fly `philly3d.com/?people=1` on the Mac and the
   iPhone and say what is next (see "The people" below).
3. **Read the next real beacons** against Round 229's predictions (its devlog entry lists the fields): the first frame
   after Ready on cold loads, programs linked per flush, the link probe's ratio by engine, the memory crumbs after
   Enter on the phone.

## Stage 1: what is left

- The entry orbit captures (eight azimuths, day and 21:30) and a retake of the day set, which predates Rounds 222 to 228.
- **Mike's first side-by-side page** (published Nov 11, picked; Round 234 shipped his picks), on a staged copy, never the live site: the light at fill 1.0, 1.2 and 1.8
  (`__dbg.keyLight`), roofs at roughness 0.65 toward the sun, the entry orbit's shadows with the far-map switch at
  360 m; and the `?veilcity=1` veil. This page decides what Stage 2 turns on.
- The service worker and the reload: Round 229's navigation fields must first confirm that a reload under the worker
  downloads the whole page again; only then let Chromium navigations bypass the relay in `sw.js`.
- ~~The glass calibration had drifted on main~~ Re-measured as Round 235 (Nov 11): nothing in the glass broke. The Oct 14
  merge brought in the Liberty remodel (both towers about 5 levels brighter, within bounds) and Round 198's One Parkway,
  which stood in front of pose `twopenn-50` (moved 70 m west); Round 234's fill lifted every glass 1 to 3 L*. The file
  is current on Round 234's page, DiBona (1901 Market) joins the open towers and Two Penn left the swatches (not glass
  since Round 198). The calibration's fingerprint sees only the glass's shaders and systems, so re-run
  `glass_calibrate.py` after any change to the towers round the swatched ones too, or to the light.
- The deploy's two verify lines for the server config (the art's cache header; gzip through a `Via` header).
- Round 229's open findings (its devlog entry lists them under "Known, open"): a computer's second and third frames still link programs
  under a lit button; tier 2 still links about ten weather programs in its first frame; `beacons.py`'s engine line
  leaves out probes that produced no ratio.

## Stage 2: the shader train (one deploy; each look behind a flag or at zero strength)

Performance, no look change: the program diet (about 31 fewer of about 140: one facade program with its gains in a
uniform, the Fishtown stations' four identical hooks under one key, venue boards, lamp lenses, water, the roof kit 8 to
2, the rebuilds folded into one family); the sky dome and apron drawn last; the cloud shadow's gate.
The first view by day (side-by-side page one): each flat roof takes its kind from its own photograph; the far ring keeps
its measured roof forms; crisp shadows in the entry orbit.
The night and winter (page two): lit floors on masonry and skinned towers; floodlights on the Art Museum, Independence
Hall and Founder's Hall; generated fronts and skins answering the clock and the weather; door lamps and light out of
open shops; snow that lies as long as the real snow.
The light: the clear-sky fill is already 1.2 (Round 234, his pick); what is left is the straighter day toe, shown on a
test build first. Materials that answer the sun: he made no pick on the first page, where the sheen washed out South
Philadelphia's roofs toward the sun; not on the train unless he asks again.

## Stages 3 to 6, in one line each

- **3, link ahead:** issue every new material's program early and never wait on one link at a time (a shim on r149's
  program list, or three build-time substitutions to the inlined copy, which is the reopened three.js rule and goes to
  Mike with the probe's numbers). A Windows first visit from about 100 s toward 40 to 60 s. The least-checked large
  number in the plan.
- **4, the phone holds the whole city:** masks in the channels they use, merged flats indexed, walls as 40-byte
  instance records (tier 0 from 871 MB toward 680 at Ready; gate: pins through buildings stays 0), ASTC art in the app,
  sidewalks back on tiers 1 and 2, building shadows on a phone from the collision columns.
- **5, repeat launches and entering sooner:** the street lettering's fit trimmed and then kept on the device; Ready on
  the near city on computers, with far buildings arriving after, nearest first (his side by side of the interim look).
- **6, the Mac's frame:** one unbroken multisampled pass, four hardware shadow lookups for sixteen, the cloud deck's
  pre-march, pin reads spaced, and for slow public machines only the pieces that touch no rule.

## The people (Rounds 227, 237, 242): where it stands and what is next

Shipped, behind `?people=1` (`?people=sharp` is the same since Round 242), off by default, refused at tier 2:
- Walkers are slots on their own block graph, placed by `people_walk.b64` (the centreline-to-wall distance per way
  side), about 83% of ordinary-street kerb length walkable; a card, the figure's own sun shadow and a contact blob; two
  new programs made only under the flag.
- Round 242: thirty figures (gpt-image-2.6 strips, eight pictures of a step in each of three views), ten a wardrobe
  (cold, cool, warm) by the live temperature or the date's normal, one atlas on the GPU at a time: 50.1 MB on a
  computer, 12.5 MB on a phone (7.5 and 1.9 before).
- Standing cost with the flag off: about 92 KB of the page's gzip (the walk-line blob).

Known in the first look (devlog Round 227 has the detail):
- The walk: eight pictures a step since Round 242 (about fourteen a second at a walk), the body held still on its card.
  Feet still slide a little within a picture. Figures walking toward the eye face the lens.
- From 25 to 55 m up the 150 m reach shows: people stop at the first crossing while cars run on.
- Narrow rowhouse streets carry nobody (drawn 7 m wide between rows 8 to 9 m apart: no room for a walk line).
- Walkers pass through each other, low tree crowns and poles; some feet float 10 to 17 cm; a walker turns round in one
  frame at a trail's end.
- Nobody has watched it on a real phone.

The next pass, once Mike has looked:
1. Done in Round 242 (thirty figures, three wardrobes). Open: rain gear and umbrellas (not mirror-safe as drawn), and a
   phone memory check of the 12.5 MB atlas on the real device.
2. A real height for the walk surface (the lift is a bias today), and a reach that grows with eye height.
3. Standers at SEPTA stops, shop doors, open markets and a short list of crowd points; tier 2 gets standers only.
4. The storefront density hook (`PEOPLE.boost`), dodging trees and poles.
5. Crossing at corners only after the junctions pick (signals) exists.

His decisions for the people: whether they stay at all after the first look; the narrow streets (draw them narrower, or
let people use the road's edge); walkers on bare ground where no sidewalk is drawn; an About line saying the people
are invented; a layer switch; the wardrobe hand-overs (50 and 70 F today).

## Realism picks still to come (each its own round, in the order Mike chooses)

| Pick | What | Cost and effort |
|---|---|---|
| The city's real canopy | The land mask's two invented channels from measured 1 m land cover | Art +0.4 to 2.3 MB; medium to large; a citywide side by side |
| Junctions that work | The City's 16,992 intersection controls: stop signs and queues (the signals' look is Round 239's mast arms) | +45 to 90 KB; 6 to 9 days |
| A street pace | The flight slows in its last 12 m and comes down to eye level | Small; Mike's feel on the phone |
| The Art Museum's massing | A kit rebuild, then its walls and Rocky | Large, three to four review rounds |
| Twenty stone towers | Round 198's pipeline again in a second atlas | +55.9 MB on a computer; phones after ASTC |
| Street trees at measured height | The median tree is drawn 1.27 times too short | 0 bytes; the frame cost read first |
| The Schuylkill's pool | The river above Fairmount Dam at its surveyed level | Large; changes the river invariant's reference level |

## What is waiting on Mike

1. The people: his look at Round 242's thirty, then the list of decisions above.
1b. The street floors (Round 243): `old`, `clean` or `lit` by default? `lit` changes one program's text, so it rides
    the shader train once picked; `clean` is data only.
2. Three minutes of flying the site on his Mac, then once with `?dpr=1` (Stage 6 cannot be planned without it).
3. May the beacon name the graphics chip on website computers (one sentence in the privacy policy)?
4. The veil: a computer's veil shows the city rising since Round 234 (his pick). Still his: may it name the compile wait,
   may the bar stand for time, and should it be drawn from the first view's camera so the view does not jump at Ready?
5. The side-by-side pages when they exist: roofs and the light by day; the night; the museum's wash.
6. May the model stage dated scenes (a game crowd, the holiday tree, fireworks)?
7. Other people's weak GPUs: does "never resolution" bind strangers' machines? It holds one measured 4K Windows laptop
   at 20 fps.
8. Camden (shipped, Round 231): three port structures nobody has checked against imagery, Camden City Hall's shape
   (still a 13 m box), and whether to stream the LiDAR tiles east of the river for the 420 buildings still at 10.5 m.
9. Housekeeping: about 59 MB of orphaned pack files in `.git/objects/pack` from the Nov 10 repack race (nothing lost;
   left for his say).
Later, each with its evidence in hand: the three.js substitutions (Stage 3); ASTC spent on memory or sharpness; sidewalks
on tiers 1 and 2; far streets and towns arriving after Enter; the El; sound; the river's pool level.

## Declined or refuted (do not re-propose without a new reason)

Entering on stand-in materials while programs link; web workers for the build loops; the page split into a shell and
files, binary blobs or brotli (about 1 s on any measured visit); a compact vertex that moves a building's base height; the
far ring back on the lite tiers before Stage 4; a physically based sky table; the orthophoto as far-field colour;
street-level culling from the collision columns; painted parked cars at distance; a three.js upgrade; a warmer, paler low
haze (dropped by Mike on Oct 25).

## Verification, every round

```bash
cd 3d-model
node --check app.js && python3 build.py && python3 -m unittest discover -s tests && python3 docs_check.py
```

Then the capture skill (`.claude/skills/philly3d-capture/`): headless captures from a worktree outside Dropbox at the
day, night and entry-orbit poses on the computer and phone paths; pixel parity against main for every no-look item;
the memory tool at tiers 0, 1 and 2; `__dbg.riverCheck()`, `bankCheck()` and `collide()` reading as before. The suite
carries wall-clock assertions: rerun a failing test alone before believing it, and do not run two suites at once.
