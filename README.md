<p align="center"><img src="3d-model/brand/dist/lockup.png" alt="Philly3D" width="440"></p>

A living, single-file 3D model of Philadelphia: every block of the city at its true
measured height, from the detailed Society Hill core (including Society Hill Towers,
I.M. Pei, 1964) out to the full city fabric, with real terrain, the Delaware
waterfront, the bridges, live SEPTA vehicles, flights and ships, and a real solar
clock over it all.

**Live model:** https://philly3d.com/
(fallback copy: https://harkdigital.github.io/society-hill-towers/)

- **Fly.** Drag, scroll, or press W A S D; E/Q for altitude, shift to boost, scroll
  sets cruise speed. Any first touch takes off.
- **Sun and sky** (T): any date and time of day with real Philadelphia solar
  geometry, dusk and night with lit windows, and the real moon.
- **Layers** (F): live SEPTA vehicles, Indego bike share, flights, ships, typical
  traffic, street names, landmark labels, and neighborhood names.

## Build

No toolchain, plain Python 3 assembles the page:

```bash
cd 3d-model && python3 build.py
```

Open `3d-model/society-hill-towers.html` in any WebGL browser. Everything
(Three.js, data, styles, icons) is inlined into that one ~20 MB file. See
`handoff.md` for architecture notes, data provenance, and the development log.
Brand assets live in `3d-model/brand/`; `make_brand.py` regenerates `brand/dist/`.

## Data & credits

- Building footprints, roads, and land use © [OpenStreetMap](https://www.openstreetmap.org/copyright)
  contributors, ODbL.
- Elevation from the USGS National Elevation Dataset (10 m).
- Street trees: Philadelphia Parks & Recreation Tree Inventory 2025; neighborhoods:
  City of Philadelphia via OpenDataPhilly (CC-BY); traffic volumes: PennDOT RMSTRAFFIC.
- Rendering: [Three.js](https://threejs.org/) r149 (MIT), inlined.
- Landmark massing and colors researched from public photographs, Philadelphia OPA
  parcels, and 2017 city LiDAR.
