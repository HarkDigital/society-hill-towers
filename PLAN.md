# Philly3D: the working plan

This is the plan the project is working from now, and where it stands. Any session (any model) picking the work up
should read this file first, then `CLAUDE.md` for the rules and `devlog.md` for the round it is about to touch. Keep
this file current: when a round ships, move its line from "in flight" to "shipped" and correct anything it changed.

Last updated: Nov 10, 2026, after Round 230. Round 229 is built and merged on a branch but held (see "In flight").

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
- **How a round is built** (this worked for Rounds 225 to 228): a git worktree outside Dropbox per item, an implementer,
  an adversarial reviewer, a fix, a second reviewer; then the lead merges, builds, runs the whole suite, compares
  captures against main (`render.mjs --png` and a pixel compare, traffic off), writes the devlog, commits the built
  page, pushes with `git push gh-ssh main` and runs `3d-model/deploy_philly3d.sh` (which also ships a TestFlight
  build). Commit from worktrees with `git -c gc.auto=0 -c maintenance.auto=false` (two automatic repacks raced in the
  Dropbox-hosted object store on Nov 10). Server config edits need Mike's explicit go, each time.

## Status at a glance

| Stage | What | Status |
|---|---|---|
| 1 | Free seconds, missing numbers, no dead button (JavaScript and data only) | Batch one shipped (Round 225). Batch two (Round 229) is built, reviewed and merged on branch `round229`, and HELD for a regression. Remainder below. |
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
- **Round 227** (the people, a first look): three test figures walking, OFF by default. `?people=1`, or
  `?people=sharp` on a computer. See "The people" below.
- **Round 228**: the Vine Street Expressway's cut carried to the tunnel under 20th Street and the Parkway, a portal at
  each mouth (Mike's bug report; not part of the plan).
- **Round 230**: the last see-through slivers beside the expressway's west approach cuts closed (a floor and risers
  under the lawn laid over opened ground, `lawnUnder`; a pier at each end of each headwall).

## In flight (finish these first)

0. **Round 229 (Stage 1, batch two) is HELD, not shipped.** Branch `round229` holds main at Round 228 plus the batch:
   no program compiles twice (`wxHookAll` before the first compile); Enter lights only after the first drawn frame;
   `?veilcity=1` (off) lets a computer's veil show the city rising; measurement round two in the beacons; `?cold=<n>`
   and the link probe; Camden at its measured heights. Every package passed two adversarial reviews, and the merged
   build's phone and computer paths run clean. What holds it:
   - **Dark glass towers.** At the entry orbit by day (`orbit-e` in the parity poses) Center City's glass towers render
     dark where main renders them sky-blue: 6.3% of pixels, repeatable, and present in the first-frame branch alone
     (`s1b/first`), so it is the batch's and not the merge's. Lighting, environment and the glass uniforms read the same
     on both builds; the glass rooms being loaded is NOT the cause (main with rooms loaded is still blue). Bisect
     `s1b/first`'s commits, the weather hook (`a250f07`) first. The reviewers compared program sources, which are
     identical; this is state, not text.
   - `tests/test_measure_two.py` `test_the_frame` fails on the merge: Round 227's `peopleStep` line now sits between
     `updateTraffic` and the batch's `tj3` timer in `frame()`.
   - Its notes are written and waiting beside the research record: `.audit/2026-11-10-performance-and-realism/round229/`
     (`devlog229.md` for the devlog, `claude_md.txt` for CLAUDE.md's flags and rules, `open_items.md` for Mike's
     summary). They describe the batch as shipped; apply them when it is.
   - Camden has no flag: it ships with this deploy, so show Mike the before and after from Penn's Landing first if he
     wants a say.
1. (Done in Round 230: the slivers at the Vine cut's west approaches.)
2. **The people, after Mike's first look.** He has been asked to fly `philly3d.com/?people=sharp` on the Mac and
   `?people=1` in Safari on the iPhone, and to say whether to generate the full figure set. Do not generate it before he
   answers.
3. **Read the next real beacons** once Round 229 is out, against its predictions (`devlog229.md` lists the fields): the first frame
   after Ready on cold loads, programs linked per flush, the link probe's ratio by engine, the memory crumbs after
   Enter on the phone.

## Stage 1: what is left

- The entry orbit captures (eight azimuths, day and 21:30) and a retake of the day set, which predates Rounds 222 to 228.
- **Mike's first side-by-side page**, on a staged copy, never the live site: the light at fill 1.0, 1.2 and 1.8
  (`__dbg.keyLight`), roofs at roughness 0.65 toward the sun, the entry orbit's shadows with the far-map switch at
  360 m; and the `?veilcity=1` veil. This page decides what Stage 2 turns on.
- The service worker and the reload: Round 229's navigation fields must first confirm that a reload under the worker
  downloads the whole page again; only then let Chromium navigations bypass the relay in `sw.js`.
- The deploy's two verify lines for the server config (the art's cache header; gzip through a `Via` header).
- Round 229's open findings, once it ships (`devlog229.md` lists them): a computer's second and third frames still link programs
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
The light, riding at zero strength until his pick: the afternoon shade (a straighter day toe, the clear-sky fill handed
back toward Round 54's ratio; the W's glass calibration must not move), and materials that answer the sun.

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

## The people (Round 227): where it stands and what is next

Shipped, behind `?people=1` / `?people=sharp`, off by default, refused at tier 2:
- Walkers are slots on their own block graph, placed by `people_walk.b64` (the centreline-to-wall distance per way
  side), about 83% of ordinary-street kerb length walkable; three figures from one six-pose sheet each; a card, the
  figure's own sun shadow and a contact blob; two new programs made only under the flag.
- Standing cost with the flag off: about 92 KB of the page's gzip (the walk-line blob).

Known in the first look (devlog Round 227 has the detail):
- Inside about 10 m the walk is two poses flipping; figures walking toward the eye look into the lens; three figures
  means twins.
- From 25 to 55 m up the 150 m reach shows: people stop at the first crossing while cars run on.
- Narrow rowhouse streets carry nobody (drawn 7 m wide between rows 8 to 9 m apart: no room for a walk line).
- Walkers pass through each other, low tree crowns and poles; some feet float 10 to 17 cm; a walker turns round in one
  frame at a trail's end.
- Nobody has watched it on a real phone.

The next pass, once Mike has looked:
1. The full figure set (the plan said 12 figures in two wardrobes; about $12 at the quality that held one person
   across six poses), with four gait poses a view in place of two if the flip-book bothers him, and no figure looking
   at the lens.
2. A real height for the walk surface (the lift is a bias today), and a reach that grows with eye height.
3. Standers at SEPTA stops, shop doors, open markets and a short list of crowd points; tier 2 gets standers only.
4. The storefront density hook (`PEOPLE.boost`), wardrobes by season, dodging trees and poles.
5. Crossing at corners only after the junctions pick (signals) exists.

His decisions for the people: whether they stay at all after the first look; the narrow streets (draw them narrower, or
let people use the road's edge); the sharp atlas on a computer (15 MB for three figures; it scales with the count);
walkers on bare ground where no sidewalk is drawn; an About line saying the people are invented; a layer switch.

## Realism picks still to come (each its own round, in the order Mike chooses)

| Pick | What | Cost and effort |
|---|---|---|
| The city's real canopy | The land mask's two invented channels from measured 1 m land cover | Art +0.4 to 2.3 MB; medium to large; a citywide side by side |
| Junctions that work | The City's 16,992 intersection controls: signal heads, stop signs, queues | +45 to 90 KB; 6 to 9 days |
| A street pace | The flight slows in its last 12 m and comes down to eye level | Small; Mike's feel on the phone |
| The Art Museum's massing | A kit rebuild, then its walls and Rocky | Large, three to four review rounds |
| Twenty stone towers | Round 198's pipeline again in a second atlas | +55.9 MB on a computer; phones after ASTC |
| Street trees at measured height | The median tree is drawn 1.27 times too short | 0 bytes; the frame cost read first |
| The Schuylkill's pool | The river above Fairmount Dam at its surveyed level | Large; changes the river invariant's reference level |

## What is waiting on Mike

1. The people: his first look, then the list of decisions above.
2. Three minutes of flying the site on his Mac, then once with `?dpr=1` (Stage 6 cannot be planned without it).
3. May the beacon name the graphics chip on website computers (one sentence in the privacy policy)?
4. The veil: may a computer's veil show the city rising (`?veilcity=1`), may it name the compile wait, may the bar
   stand for time?
5. The side-by-side pages when they exist: roofs and the light by day; the night; the museum's wash.
6. May the model stage dated scenes (a game crowd, the holiday tree, fireworks)?
7. Other people's weak GPUs: does "never resolution" bind strangers' machines? It holds one measured 4K Windows laptop
   at 20 fps.
8. Camden (ships with Round 229): the before and after from Penn's Landing, and three port structures nobody has
   checked against imagery.
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
