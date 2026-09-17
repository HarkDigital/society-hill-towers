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

## Probes worth knowing

These answer questions faster than any screenshot, and they answer them for the
whole city rather than one frame.

| Call | Returns |
|------|---------|
| `__dbg.groundAt(x, z)` | `{mesh, dem, river, beyondDem, south, east}` at a point |
| `__dbg.railSnap(x, z, r)` | `[x, z, dx, dz, y, flags]` for the nearest track |
| `__dbg.rail()` | the corridor's under / float / grade extremes with locations |
| `__dbg.colStats()` | per-tier means of wall and roof colours handed to the builders |
| `__dbg.towers().log` | every researched tower spec match in the wide loop |
| `__dbg.amtrak()` | the live train list with positions and fix ages |
| `__dbg.perf()` | per-step build ms, frame p50/p95, renderer.info, heap |

A grid of `railSnap` against `groundAt().mesh` is a one-second citywide survey of
buried or floating track. Reach for that shape of check whenever a question is
"is this wrong anywhere else", because a survey settles it and six screenshots do
not. Round 85 used a 5,328-sample sweep that way.
