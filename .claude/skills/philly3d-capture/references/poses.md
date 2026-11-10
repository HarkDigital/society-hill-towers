# Camera poses and clock control

## Conventions

`__dbg.goFly(x, y, z, yaw, pitch)` places the eye at the world point and looks
along `(sin yaw, -cos yaw)`, so `yaw = atan2(dx, -dz)`:

| yaw   | facing |
|-------|--------|
| 0     | north  |
| 1.57  | east   |
| -1.57 | west   |
| 3.14  | south  |

World frame: x = east, z = south, y = up, metres, origin at the towers' centroid
(39.94547 N, 75.14475 W). City Hall is at (-1603, -802), 30th Street Station at
(-3197, -1158).

`__dbg.setClock(year, month, day, minuteOfDay)` pins the model clock. Night is
what the skyline lights need; 1290 (21:30) is the usual choice. The clock can also
be pinned in the hash as `t=yyyymmdd,minutes`, alongside a camera as
`#p=x,y,z,yaw,pitch`, which is the reproducible way to hand a view to someone else.

## Day poses

| Name              | x, y, z              | yaw, pitch      | Shows |
|-------------------|----------------------|-----------------|-------|
| skyline           | -300, 240, 900       | -0.653, -0.12   | the Center City cluster from the south east |
| waterfront        | 1100, 140, 250       | -1.347, -0.10   | the Delaware, the piers, the ships |
| CTC crown         | -2100, 330, -900     | -0.57, 0.06     | the Comcast towers' crowns up close |
| Spruce St         | 60, 16, 120          | -1.6, -0.1      | street level in Society Hill |
| rowhouse close    | 40, 6, 108           | -1.9, 0.05      | facade texture, storefronts, awnings |
| towers and meadow | 70, 5, 100           | -0.9, 0.06      | the three towers, ground surface, tufts |

## Night poses for the skyline lights

| Name              | x, y, z              | yaw, pitch      | Shows |
|-------------------|----------------------|-----------------|-------|
| BNY from the west | -2400, 230, -904     | 1.5708, 0.02    | the BNY Mellon crown |
| the Liberty Places| -1700, 240, -500     | -0.847, -0.02   | both chevron gable ends |
| the Logans from NE| -1800, 200, -1350    | -2.32, -0.05    | the Logan Square towers |
| City Hall         | -1450, 120, -600     | -1.2, -0.08     | the whole block washed, William Penn |
| bridge from river | 880, 90, -520        | 0.15, -0.06     | the Ben Franklin cable strings |
| along the span    | 330, 62, -955        | 1.35, -0.02     | deck nodes, tower wash, walkway lamps |

`__dbg.lights('eagles' | 'off' | 'pink,blue')` lands a theme at once without
waiting for a scoreboard fetch. `?lights=<team|colour|hex|off>` does the same from
the URL.

## The entry orbit (the first view)

What every visitor sees first, and until Round 225 no pose table held it. After Enter
the camera circles City Hall: the orbit's target is (-1603, 78, -802), and Enter sets
`orbit.goalR = 700` at polar angle `goalPhi` 1.22 from +y (app.js, the `orbit` object
and the `btnEnter` handler). So the eye rides a ring 700 sin 1.22 = 657.4 m out
horizontally at y = 78 + 700 cos 1.22 = 318.6 (240.6 m over the target), looking down
20.1 degrees at the target. The azimuth is measured on xz from +x (east) toward +z
(south), and the circle turns that way at 0.045 rad a second (a lap in about 140 s).
It starts from azimuth 30 degrees (`goalTheta` 0.52) and already turns behind the
veil (`introSpin`), so where a visitor enters depends on how long the build took:
any of the eight can be the first view.

| Name      | Azimuth | Eye stands | pos x, y, z               |
|-----------|---------|------------|---------------------------|
| orbit-000 | 0       | east       | -945.6, 318.6, -802.0     |
| orbit-045 | 45      | south east | -1138.2, 318.6, -337.2    |
| orbit-090 | 90      | south      | -1603.0, 318.6, -144.6    |
| orbit-135 | 135     | south west | -2067.8, 318.6, -337.2    |
| orbit-180 | 180     | west       | -2260.4, 318.6, -802.0    |
| orbit-225 | 225     | north west | -2067.8, 318.6, -1266.8   |
| orbit-270 | 270     | north      | -1603.0, 318.6, -1459.4   |
| orbit-315 | 315     | north east | -1138.2, 318.6, -1266.8   |

Aim each with `"look": [-1603, 78, -802]` in a `poses.json` rather than a yaw and a
pitch (`render.mjs` works them out), and take every azimuth twice: by day and at 21:30
(clock minutes 1290).

```json
{ "name": "orbit-000-day",   "pos": [-945.6, 318.6, -802.0], "look": [-1603, 78, -802], "clock": [2026, 10, 12, 780] },
{ "name": "orbit-000-night", "pos": [-945.6, 318.6, -802.0], "look": [-1603, 78, -802], "clock": [2026, 10, 12, 1290] }
```

The staged plan (Round 225 on) asks for every look change's side by side at these
poses as well as the older ones. If the orbit's constants change in app.js, recompute
the table: x = -1603 + h cos a, z = -802 + h sin a, with h = goalR sin goalPhi.

## Probes worth knowing

These answer questions faster than any screenshot, and they answer them for the
whole city rather than one frame.

| Call | Returns |
|------|---------|
| `__dbg.groundAt(x, z)` | `{mesh, dem, river, beyondDem, south, east}` at a point |
| `__dbg.railSnap(x, z, r, prefer, margin)` | `[x, z, dx, dz, y, flags, chain]` for the nearest track; `prefer` biases toward a chain |
| `__dbg.railWalk(x, z, dx, dz, dist, chain)` | walks the rails and returns `[x, z, dx, dz, y, flags, chain]`; articulate a consist with it and compare `[6]` per car to prove the train stays on one track |
| `__dbg.rail()` | the corridor's under / float / grade extremes with locations |
| `__dbg.riverCheck()` | the Schuylkill's centreline against the water sheet: every sample where the DRAWN ground rides above the water, which is what a "strip of land in the river" is. Use this instead of rolling your own: a per-row minimum finds the carved trough and HIDES the ridge beside it, and the sheet sits at -7.34 in model units, not near zero. Both mistakes cost Round 89 an afternoon |
| `__dbg.trafficChurn(reset)` | car births and deaths a second by cause, age at death, and how many the viewer could see |
| `__dbg.colStats()` | per-tier means of wall and roof colours handed to the builders |
| `__dbg.towers().log` | every researched tower spec match in the wide loop |
| `__dbg.amtrak()` | the live train list with positions and fix ages |
| `__dbg.perf()` | per-step build ms, frame p50/p95, renderer.info, heap |
| `__dbg.roads()` | the strips draped on the ground against the flat fallbacks, the bend discs, road triangles, the decks lifted and by how much, the wide segments indexed for the seam, the lamp term and the glint term (Round 88) |
| `__dbg.drape(ring, yOff)` | runs `drapeConvex` on a convex ring and returns its triangles; `__dbg.gridAt(x, z)` the registered ground grid there, `__dbg.landY(x, z)` the road loops' ground read |

`renderer.info` with `autoReset = false` is also the only honest way to price a
change: Round 87 priced three tree LODs that way in three builds (18.0 M triangles
a frame for the full-detail crown citywide against 13.4 M for the phone crown)
rather than arguing about it.

A grid of `railSnap` against `groundAt().mesh` is a one-second citywide survey of
buried or floating track. Reach for that shape of check whenever a question is
"is this wrong anywhere else", because a survey settles it and six screenshots do
not. Round 85 used a 5,328-sample sweep that way.
