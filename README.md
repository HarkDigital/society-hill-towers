# Society Hill Towers 3D

An interactive, single-file 3D model of Society Hill Towers (I.M. Pei, 1964) and its
Philadelphia surroundings — ~2,800 detailed Society Hill buildings plus ~108,000
simplified buildings across Center City, South Philadelphia, Northern Liberties and
Fishtown, with real terrain, the Delaware waterfront, the Benjamin Franklin and Walt
Whitman Bridges, the stadium complex, and a real solar clock.

**Live model:** https://harkdigital.github.io/society-hill-towers/

- **Orbit / Walk / Fly** navigation (keys 1/2/3). Walk the streets with WASD, or fly
  over the city — E/Q for altitude, shift to boost, scroll to set cruise speed.
- **Sun & sky** (T): any date and time of day, Philadelphia solar geometry, dusk/night
  with lit windows.
- Landmark labels (L), viewpoint jumps, and an About panel (I) with the towers' history.

## Build

No toolchain — plain Python 3 assembles the page:

```bash
cd 3d-model && python3 build.py
```

Open `3d-model/society-hill-towers.html` in any WebGL browser. Everything (Three.js,
data, styles) is inlined into that one ~7 MB file. See `handoff.md` for architecture
notes, data provenance, and the development log.

## Data & credits

- Building footprints, roads, and land use © [OpenStreetMap](https://www.openstreetmap.org/copyright)
  contributors, ODbL.
- Elevation from the USGS National Elevation Dataset (10 m).
- Rendering: [Three.js](https://threejs.org/) r149 (MIT), inlined.
- Landmark massing/colors researched from public photographs, Philadelphia OPA parcels,
  and 2017 city LiDAR.
